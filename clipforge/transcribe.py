"""Transcribe video audio using faster-whisper. Returns word-level segments."""

import os
import json
import subprocess
import time
from typing import Optional

from .config import ClipforgeConfig


def extract_audio(video_path: str, out_path: str) -> str:
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", out_path
    ], capture_output=True, check=True)
    return out_path


def run(video_path: str, cfg: ClipforgeConfig, tmp_dir: str,
        existing_transcript: Optional[str] = None) -> list[dict]:
    """
    Returns list of segments:
      [{"start": float, "end": float, "text": str, "words": [{"word", "start", "end"}]}]
    """
    cache_path = os.path.join(tmp_dir, "transcript.json")

    if existing_transcript and os.path.exists(existing_transcript):
        print(f"  → Loading transcript: {existing_transcript}")
        with open(existing_transcript, encoding="utf-8") as f:
            return json.load(f)

    audio_path = os.path.join(tmp_dir, "audio.wav")
    print(f"  → Extracting audio...")
    extract_audio(video_path, audio_path)

    from faster_whisper import WhisperModel
    print(f"  → Loading faster-whisper large-v3 (first run downloads ~1.5GB)...")
    t0 = time.time()
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    print(f"  → Model loaded in {time.time()-t0:.0f}s")

    print(f"  → Transcribing...")
    t0 = time.time()
    segments, info = model.transcribe(audio_path, word_timestamps=True, language=None)
    segments = list(segments)
    elapsed = time.time() - t0

    print(f"  → Language: {info.language} ({info.language_probability:.0%}) | "
          f"Time: {elapsed:.0f}s | Segments: {len(segments)}")

    data = [{
        "start": round(s.start, 3),
        "end":   round(s.end, 3),
        "text":  s.text.strip(),
        "words": [{"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)}
                  for w in (s.words or [])]
    } for s in segments if s.text.strip()]

    # Filter segments below minimum duration from config
    min_dur = cfg.cutting.min_segment_duration
    before = len(data)
    data = [s for s in data if (s["end"] - s["start"]) >= min_dur]
    if before != len(data):
        print(f"  → Dropped {before - len(data)} segments < {min_dur}s")

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  → Saved: {cache_path}")
    return data
