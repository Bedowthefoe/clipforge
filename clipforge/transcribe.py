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


def run(video_path: str, cfg: ClipforgeConfig, tmp_dir: str,
        existing_transcript: Optional[str] = None) -> list[dict]:
    """
    Returns filtered, annotated list of segments:
      [{"start", "end", "text", "words", "complete"}]
    Indices are stable — filtering happens before returning so Claude's
    segment_index references always match the returned list.
    """
    min_dur = cfg.cutting.min_segment_duration

    if existing_transcript and os.path.exists(existing_transcript):
        print(f"  → Loading transcript: {existing_transcript}")
        with open(existing_transcript, encoding="utf-8") as f:
            data = json.load(f)
        data = _annotate_completeness(data, min_dur)
        data = _filter_and_reindex(data, min_dur)
        print(f"  → {len(data)} segments after filtering")
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

    data = _annotate_completeness(data, min_dur)
    data = _filter_and_reindex(data, min_dur)

    cache_path = os.path.join(tmp_dir, "transcript.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → Saved: {cache_path} ({len(data)} segments)")
    return data
