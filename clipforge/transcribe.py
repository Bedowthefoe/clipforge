"""Transcribe video audio using faster-whisper. Returns filtered, annotated segments."""

import os
import json
import subprocess
import time
from typing import Optional

from .config import ClipforgeConfig

# Thai words/particles that mark sentence-opening fragments when isolated.
# A segment starting with one of these and under a duration threshold is
# likely the tail of a previous sentence or an orphaned clause.
THAI_INCOMPLETE_OPENERS = [
    "ถ้า",    # if (conditional with no conclusion)
    "แต่",    # but (requires prior context)
    "เพราะ",  # because (subordinate clause)
    "เมื่อ",  # when (temporal clause)
    "ซึ่ง",   # which (relative clause)
    "โดย",    # by/through (adverbial opener)
    "และ",    # and (continuation without context)
]
# Segments ending with these suggest the host is pointing to something
# that happens AFTER the cut — visually incomplete even if grammatically ok
THAI_DANGLING_ENDINGS = [
    "ท่านี้", "ท่า นี้", "อันนี้", "อัน นี้", "แบบนี้", "แบบ นี้",
    "นี้เลย", "นี้ เลย", "ตรงนี้", "ตรง นี้",
]
THAI_FILLER_PHRASES = {
    "ไม่ต้อง เยอะ", "นะ", "นะครับ", "นะคะ", "ค่ะ", "ครับ",
}


def _annotate_completeness(segments: list[dict], min_dur: float) -> list[dict]:
    """
    Add a `complete` flag to each segment.
    complete=False means it is likely a fragment or dangling clause.
    """
    for seg in segments:
        text  = seg["text"].strip()
        dur   = seg["end"] - seg["start"]
        first = text.split()[0] if text.split() else ""

        text_nospace = text.replace(" ", "")
        starts_incomplete = any(text_nospace.startswith(op) for op in THAI_INCOMPLETE_OPENERS)
        ends_dangling     = any(text_nospace.endswith(e.replace(" ", "")) for e in THAI_DANGLING_ENDINGS)

        is_fragment = (
            dur < min_dur
            or text in THAI_FILLER_PHRASES
            or (starts_incomplete and dur < 3.0)
            or ends_dangling
        )
        seg["complete"] = not is_fragment

    return segments


def _filter_and_reindex(segments: list[dict], min_dur: float) -> list[dict]:
    """
    Remove segments that are too short or flagged incomplete.
    Preserves original source timestamps — indices are positional after filtering.
    """
    before = len(segments)
    segments = [s for s in segments if s["complete"] and (s["end"] - s["start"]) >= min_dur]
    dropped = before - len(segments)
    if dropped:
        print(f"  → Dropped {dropped} fragment/incomplete segments (min_dur={min_dur}s)")
    return segments


def _resegment_at_pauses(segments: list[dict],
                         max_dur: float = 5.0,
                         pause_gap: float = 0.4,
                         silent_token_dur: float = 1.0,
                         min_dur: float = 0.4) -> list[dict]:
    """
    Split long segments at word-level pauses using Whisper's word timestamps.

    Two pause signals (either triggers a split):
      a) gap >= pause_gap between consecutive tokens
      b) a single token whose duration >= silent_token_dur (Whisper extends the
         last token through silence — common when the host pauses to demo)

    Segments under max_dur pass through unchanged.
    Sub-segments shorter than min_dur are dropped.
    """
    result = []
    for seg in segments:
        words   = seg.get("words") or []
        seg_dur = seg["end"] - seg["start"]
        if not words or seg_dur <= max_dur:
            result.append(seg)
            continue

        # Find indices in `words` where a NEW sub-segment should start.
        splits = []
        for i in range(1, len(words)):
            prev = words[i - 1]
            gap  = words[i]["start"] - prev["end"]
            prev_dur = prev["end"] - prev["start"]
            if gap >= pause_gap or prev_dur >= silent_token_dur:
                splits.append(i)

        if not splits:
            # No clear pause, but segment is long — fall back to mid-point split.
            splits = [len(words) // 2]

        boundaries = [0] + splits + [len(words)]
        for j in range(len(boundaries) - 1):
            ws = words[boundaries[j]: boundaries[j + 1]]
            if not ws:
                continue
            sub_text = "".join(w["word"] for w in ws).strip()
            if not sub_text:
                continue
            sub_start = ws[0]["start"]
            sub_end   = ws[-1]["end"]
            if sub_end - sub_start < min_dur:
                continue
            result.append({
                "start":    round(sub_start, 3),
                "end":      round(sub_end, 3),
                "text":     sub_text,
                "words":    ws,
                "complete": seg.get("complete", True),
            })

    if len(result) != len(segments):
        print(f"  → Resegmented at pauses: {len(segments)} → {len(result)} segments")
    return result


def run(video_path: str, cfg: ClipforgeConfig, tmp_dir: str,
        existing_transcript: Optional[str] = None,
        filter_incomplete: bool = True,
        resegment_pauses: bool = False) -> list[dict]:
    """
    Returns annotated list of segments: [{"start", "end", "text", "words", "complete"}]

    filter_incomplete: drop fragments + reindex (highlight_reel mode).
    resegment_pauses:  split long segments at word-level pauses (overlay_only).
                       Produces shorter on-screen subtitle blocks that match
                       professional subtitle practice (~3-5s each).
    """
    min_dur = cfg.cutting.min_segment_duration

    def _postprocess(data: list[dict]) -> list[dict]:
        data = _annotate_completeness(data, min_dur)
        if filter_incomplete:
            data = _filter_and_reindex(data, min_dur)
        if resegment_pauses:
            data = _resegment_at_pauses(
                data,
                max_dur=cfg.cutting.resegment_max_duration,
                pause_gap=cfg.cutting.resegment_pause_gap,
                silent_token_dur=cfg.cutting.resegment_silent_token_dur,
                min_dur=cfg.cutting.resegment_min_duration,
            )
        return data

    if existing_transcript and os.path.exists(existing_transcript):
        print(f"  → Loading transcript: {existing_transcript}")
        with open(existing_transcript, encoding="utf-8") as f:
            data = json.load(f)
        data = _postprocess(data)
        print(f"  → {len(data)} segments after post-processing")
        return data

    audio_path = os.path.join(tmp_dir, "audio.wav")
    print(f"  → Extracting audio...")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", audio_path
    ], capture_output=True, check=True)

    from faster_whisper import WhisperModel
    print(f"  → Loading faster-whisper large-v3 (first run downloads ~1.5GB)...")
    t0 = time.time()
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    print(f"  → Model loaded in {time.time()-t0:.0f}s")

    print(f"  → Transcribing...")
    t0 = time.time()
    segments, info = model.transcribe(audio_path, word_timestamps=True, language=None)
    segments = list(segments)
    print(f"  → Language: {info.language} ({info.language_probability:.0%}) | "
          f"Time: {time.time()-t0:.0f}s | Raw segments: {len(segments)}")

    data = [{
        "start": round(s.start, 3),
        "end":   round(s.end, 3),
        "text":  s.text.strip(),
        "words": [{"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)}
                  for w in (s.words or [])]
    } for s in segments if s.text.strip()]

    data = _postprocess(data)
    print(f"  → {len(data)} segments after post-processing")

    cache_path = os.path.join(tmp_dir, "transcript.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → Saved: {cache_path} ({len(data)} segments)")
    return data
