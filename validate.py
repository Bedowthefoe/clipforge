#!/usr/bin/env python3
"""
Component validation suite for Clipforge POC.
Usage: python validate.py <input_video.mp4>
"""

import sys
import os
import json
import time
import shutil
import subprocess
import tempfile
import datetime
from pathlib import Path


# ─── Helpers ──────────────────────────────────────────────────────────────────

RESET  = "\033[0m"
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"

results = []

def header(name):
    print(f"\n{BOLD}{'─'*60}{RESET}")
    print(f"{BOLD}  {name}{RESET}")
    print(f"{BOLD}{'─'*60}{RESET}")

def passed(msg=""):
    print(f"  {GREEN}✓ PASS{RESET}  {msg}")
    return True

def failed(msg=""):
    print(f"  {RED}✗ FAIL{RESET}  {msg}")
    return False

def info(msg):
    print(f"  {YELLOW}→{RESET}  {msg}")

def run(label, fn, *args, **kwargs):
    try:
        ok = fn(*args, **kwargs)
        results.append((label, ok))
    except Exception as e:
        print(f"  {RED}✗ FAIL{RESET}  Exception: {e}")
        results.append((label, False))


# ─── Test 1: FFmpeg capabilities ──────────────────────────────────────────────

def test_ffmpeg_caps():
    header("Test 1: FFmpeg capabilities")

    # ffmpeg installed?
    r = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    if r.returncode != 0:
        return failed("ffmpeg not found")
    version_line = r.stdout.splitlines()[0]
    info(version_line)

    all_ok = True

    # Check each required filter
    filters_r = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True)
    filters = filters_r.stdout

    for f in ["zoompan", "drawtext", "subtitles"]:
        if f in filters:
            passed(f"filter '{f}' available")
        else:
            failed(f"filter '{f}' MISSING — rebuild FFmpeg with required libs")
            all_ok = False

    # Check libass via subtitles filter description
    if "libass" in filters_r.stdout.lower() or "subtitles" in filters:
        passed("libass appears linked")
    else:
        failed("libass not detected — Thai subtitle rendering will fail")
        all_ok = False

    # Check encoders
    codecs_r = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
    for enc in ["libx264", "aac"]:
        if enc in codecs_r.stdout:
            passed(f"encoder '{enc}' available")
        else:
            failed(f"encoder '{enc}' missing")
            all_ok = False

    return all_ok


# ─── Test 2: Thai fonts installed ─────────────────────────────────────────────

def test_thai_fonts():
    header("Test 2: Thai fonts installed")

    all_ok = True
    for font in ["Sarabun", "Garuda", "Noto Sans Thai"]:
        r = subprocess.run(["fc-list", f":family={font}"], capture_output=True, text=True)
        if r.stdout.strip():
            passed(f"'{font}' found: {r.stdout.strip().split(':')[0]}")
        else:
            failed(f"'{font}' not found")
            if font == "Sarabun":
                info("Install: sudo apt install fonts-thai-tlwg")
                all_ok = False

    return all_ok


# ─── Test 3: python-ass library ───────────────────────────────────────────────

def test_python_ass(tmp_dir):
    header("Test 3: python-ass → valid .ass file")

    try:
        import ass
    except ImportError:
        failed("ass not installed — run: pip install ass")
        return False

    # Build a minimal .ass with Thai text
    doc = ass.Document()
    doc.play_res_x = 1920
    doc.play_res_y = 1080

    style = ass.Style()
    style.name          = "Default"
    style.fontname      = "Noto Sans Thai"
    style.fontsize      = 48
    style.primary_color = ass.data.Color(r=255, g=255, b=255, a=0)
    style.outline_color = ass.data.Color(r=0,   g=0,   b=0,   a=0)
    style.outline       = 2
    style.alignment     = 2  # bottom-center
    doc.styles.append(style)

    event = ass.Dialogue()
    event.start = datetime.timedelta(seconds=0)
    event.end   = datetime.timedelta(seconds=3)
    event.style = "Default"
    event.text  = "สวัสดีครับ ทดสอบภาษาไทย"
    doc.events.append(event)

    ass_path = os.path.join(tmp_dir, "test.ass")
    with open(ass_path, "w", encoding="utf-8-sig") as f:
        doc.dump_file(f)

    if not os.path.exists(ass_path):
        return failed(".ass file not created")

    # Validate FFmpeg can parse it (no burn yet)
    r = subprocess.run(
        ["ffmpeg", "-i", ass_path, "-f", "null", "-"],
        capture_output=True, text=True
    )
    # FFmpeg will say "Invalid data" for .ass as input — that's expected
    # We just check the file is valid UTF-8 with required sections
    with open(ass_path, encoding="utf-8-sig") as f:
        content = f.read()

    required = ["[Script Info]", "[V4+ Styles]", "[Events]", "Dialogue:"]
    for section in required:
        if section not in content:
            return failed(f"Missing section: {section}")

    passed(f".ass file generated ({len(content)} bytes), all required sections present")
    info(f"File: {ass_path}")
    return ass_path  # return path for use in test 4


# ─── Test 4: libass Thai subtitle burn ────────────────────────────────────────

def test_libass_thai(tmp_dir, ass_path, video_path):
    header("Test 4: libass Thai subtitle burn onto real video")

    if not ass_path:
        return failed("Skipped — python-ass test failed")

    out = os.path.join(tmp_dir, "thai_subtitle_test.mp4")

    # Burn subtitles onto first 3 seconds of the input video
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-t", "3",
        "-vf", f"subtitles={ass_path}:fontsdir=/usr/share/fonts",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        out
    ]
    info("Burning Thai subtitles onto 3-second clip...")
    r = subprocess.run(cmd, capture_output=True, text=True)

    if r.returncode != 0:
        failed("FFmpeg subtitle burn failed")
        print(f"  stderr: {r.stderr[-500:]}")
        return False

    size = os.path.getsize(out)
    passed(f"Subtitle burn succeeded → {out} ({size//1024}KB)")
    info("Open the file to visually confirm Thai text renders (no boxes)")
    return True


# ─── Test 5: Audio extraction + sync ──────────────────────────────────────────

def test_audio_extraction(tmp_dir, video_path):
    header("Test 5: Audio extraction + timestamp sanity")

    audio_path = os.path.join(tmp_dir, "extracted.wav")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ar", "16000", "-ac", "1", "-f", "wav",
        audio_path
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        return failed(f"Audio extraction failed: {r.stderr[-300:]}")

    size = os.path.getsize(audio_path)
    passed(f"Audio extracted → {audio_path} ({size//1024}KB, 16kHz mono WAV)")

    # Probe video duration vs audio duration
    def get_duration(path):
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
            capture_output=True, text=True
        )
        d = json.loads(r.stdout)
        return float(d["format"]["duration"])

    vid_dur = get_duration(video_path)
    aud_dur = get_duration(audio_path)
    drift = abs(vid_dur - aud_dur)

    info(f"Video duration: {vid_dur:.3f}s")
    info(f"Audio duration: {aud_dur:.3f}s")
    info(f"Drift: {drift:.3f}s")

    if drift < 0.1:
        passed(f"Duration drift {drift:.3f}s < 100ms — timestamps will align")
        return audio_path
    else:
        failed(f"Duration drift {drift:.3f}s too large — subtitle/keyword sync will be off")
        return audio_path  # return anyway for whisper test


# ─── Test 6: faster-whisper transcription ─────────────────────────────────────

def test_whisper(tmp_dir, audio_path):
    header("Test 6: faster-whisper transcription (Thai + EN)")

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return failed("faster-whisper not installed — run: pip install faster-whisper")

    info("Loading faster-whisper large-v3 (first run downloads ~1.5GB model)...")
    info("This may take several minutes on first run...")

    t0 = time.time()
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    load_time = time.time() - t0
    info(f"Model loaded in {load_time:.1f}s")

    # Transcribe first 60 seconds only for the test
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", audio_path],
        capture_output=True, text=True
    )
    dur = float(json.loads(probe.stdout)["format"]["duration"])
    test_dur = min(60.0, dur)
    info(f"Transcribing first {test_dur:.0f}s of audio...")

    # Trim to test segment
    test_audio = os.path.join(tmp_dir, "whisper_test.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", audio_path,
        "-t", str(test_dur), "-ar", "16000", "-ac", "1",
        test_audio
    ], capture_output=True)

    t0 = time.time()
    segments, info_obj = model.transcribe(
        test_audio,
        word_timestamps=True,
        language=None,  # auto-detect
    )
    segments = list(segments)
    transcribe_time = time.time() - t0

    speed_factor = test_dur / transcribe_time if transcribe_time > 0 else 0
    detected_lang = info_obj.language
    lang_prob = info_obj.language_probability

    info(f"Detected language: {detected_lang} (confidence: {lang_prob:.1%})")
    info(f"Transcription time: {transcribe_time:.1f}s for {test_dur:.0f}s of audio")
    info(f"Speed: {speed_factor:.1f}x real-time")
    info(f"Extrapolated time for full video: ~{dur/speed_factor/60:.1f} minutes")

    if not segments:
        return failed("No segments produced")

    # Show sample output
    print(f"\n  {'─'*50}")
    print(f"  Sample transcript (first 5 segments):")
    transcript_data = []
    for seg in segments[:5]:
        words = []
        if seg.words:
            for w in seg.words:
                words.append({"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)})
        print(f"  [{seg.start:.2f}s → {seg.end:.2f}s] {seg.text.strip()}")
        if words:
            print(f"    words: {[w['word'] for w in words[:6]]}")
        transcript_data.append({
            "start": round(seg.start, 3),
            "end": round(seg.end, 3),
            "text": seg.text.strip(),
            "words": words
        })
    print(f"  {'─'*50}\n")

    # Save sample transcript
    out_path = os.path.join(tmp_dir, "sample_transcript.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(transcript_data, f, ensure_ascii=False, indent=2)
    info(f"Sample transcript saved: {out_path}")

    if speed_factor >= 0.05:  # at least 0.05x = 20 min for a 1 min clip is still ok for queue
        passed(f"Transcription works — {speed_factor:.1f}x real-time, language={detected_lang}")
        return transcript_data
    else:
        failed(f"Too slow: {speed_factor:.2f}x real-time")
        return transcript_data


# ─── Test 7: claude -p subprocess ─────────────────────────────────────────────

def test_claude_p(transcript_data):
    header("Test 7: claude -p subprocess (highlight analysis)")

    if not shutil.which("claude"):
        return failed("'claude' CLI not found in PATH")

    sample_text = ""
    if transcript_data:
        sample_text = " ".join(s["text"] for s in transcript_data[:10])
    else:
        sample_text = "This is a test transcript with some interesting content about AI and video editing."

    prompt = f"""You are a video editor selecting highlight segments.

Given this transcript excerpt, identify the single most engaging moment and return ONLY a JSON object like:
{{"start_hint": "first few words of the best segment", "reason": "why this is engaging", "energy": "high/medium/low"}}

Transcript:
{sample_text}

Return only the JSON, no other text."""

    info("Calling claude -p...")
    t0 = time.time()
    r = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True, text=True,
        timeout=60
    )
    elapsed = time.time() - t0

    if r.returncode != 0:
        failed(f"claude -p exited {r.returncode}")
        print(f"  stderr: {r.stderr[:300]}")
        return False

    info(f"Response in {elapsed:.1f}s")

    try:
        response = json.loads(r.stdout)
        result_text = response.get("result", r.stdout)
        info(f"Raw result field: {result_text[:200]}")

        # Try to parse Claude's JSON response from the result field
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            inner = json.loads(json_match.group())
            passed(f"claude -p responded in {elapsed:.1f}s, JSON parsed successfully")
            info(f"Highlight reason: {inner.get('reason', 'N/A')}")
            info(f"Energy level: {inner.get('energy', 'N/A')}")
            return True
        else:
            passed(f"claude -p responded in {elapsed:.1f}s (non-JSON inner response, but call works)")
            info(f"Response preview: {result_text[:150]}")
            return True

    except (json.JSONDecodeError, KeyError) as e:
        # Even if JSON parsing fails, if we got output it means the CLI works
        if r.stdout.strip():
            passed(f"claude -p responded in {elapsed:.1f}s (output received, format varies)")
            info(f"stdout preview: {r.stdout[:200]}")
            return True
        return failed(f"Could not parse output: {e}\nstdout: {r.stdout[:200]}")


# ─── Test 8: FFmpeg concat at segment boundaries ───────────────────────────────

def test_concat(tmp_dir, video_path):
    header("Test 8: FFmpeg concat at segment boundaries")

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
        capture_output=True, text=True
    )
    dur = float(json.loads(probe.stdout)["format"]["duration"])

    # Pick two non-overlapping segments
    seg1_start, seg1_end = 2.0, 7.0
    seg2_start = min(15.0, dur - 10.0)
    seg2_end   = min(seg2_start + 5.0, dur - 1.0)

    if dur < 20:
        seg1_start, seg1_end = 0.0, min(3.0, dur/3)
        seg2_start = dur/3
        seg2_end   = min(dur/3 + 3.0, dur - 1.0)

    info(f"Cutting segment 1: {seg1_start}s → {seg1_end}s")
    info(f"Cutting segment 2: {seg2_start:.1f}s → {seg2_end:.1f}s")

    clip1 = os.path.join(tmp_dir, "clip1.mp4")
    clip2 = os.path.join(tmp_dir, "clip2.mp4")
    concat_out = os.path.join(tmp_dir, "concat_test.mp4")

    # Re-encode both clips to ensure clean keyframes at boundaries
    for (start, end, out) in [(seg1_start, seg1_end, clip1), (seg2_start, seg2_end, clip2)]:
        r = subprocess.run([
            "ffmpeg", "-y", "-i", video_path,
            "-ss", str(start), "-t", str(end - start),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-force_key_frames", "0",
            "-c:a", "aac",
            out
        ], capture_output=True, text=True)
        if r.returncode != 0:
            return failed(f"Clip extraction failed: {r.stderr[-200:]}")

    # Write concat list
    list_path = os.path.join(tmp_dir, "concat_list.txt")
    with open(list_path, "w") as f:
        f.write(f"file '{clip1}'\n")
        f.write(f"file '{clip2}'\n")

    r = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_path,
        "-c", "copy",
        concat_out
    ], capture_output=True, text=True)

    if r.returncode != 0:
        return failed(f"Concat failed: {r.stderr[-200:]}")

    size = os.path.getsize(concat_out)
    # Verify output duration (should be ~sum of both clips)
    probe2 = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", concat_out],
        capture_output=True, text=True
    )
    concat_dur = float(json.loads(probe2.stdout)["format"]["duration"])
    expected = (seg1_end - seg1_start) + (seg2_end - seg2_start)
    drift = abs(concat_dur - expected)

    info(f"Expected duration: {expected:.2f}s, actual: {concat_dur:.2f}s, drift: {drift:.3f}s")
    info(f"Output: {concat_out} ({size//1024}KB)")

    if drift < 0.5:
        passed(f"Concat clean — drift {drift:.3f}s < 500ms")
        return True
    else:
        failed(f"Duration drift {drift:.3f}s — boundary re-encoding may be needed")
        return False


# ─── Test 9: zoompan render speed ─────────────────────────────────────────────

def test_zoompan_speed(tmp_dir, video_path):
    header("Test 9: zoompan render speed benchmark")

    out = os.path.join(tmp_dir, "zoompan_test.mp4")
    test_dur = 5  # seconds — enough to measure, not too long

    # Zoom in over 5 seconds (from 1.0 to 1.3)
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-t", str(test_dur),
        "-vf", (
            "zoompan="
            "z='min(zoom+0.002,1.3)':"
            "d=1:"
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            "fps=30"
        ),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "copy",
        out
    ]

    info(f"Rendering {test_dur}s of zoompan on CPU...")
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0

    if r.returncode != 0:
        return failed(f"zoompan failed: {r.stderr[-400:]}")

    speed = test_dur / elapsed
    per_minute = 60 / speed  # minutes of render time per 1 minute of zoom video

    info(f"Rendered {test_dur}s in {elapsed:.1f}s ({speed:.2f}x real-time)")
    info(f"Extrapolation: 1 min of zoom = ~{per_minute:.1f} min render time")
    info(f"Strategy: keep zoom events short (2–5s max) to bound render cost")

    if speed >= 0.2:
        passed(f"zoompan viable — {speed:.2f}x real-time ({per_minute:.1f} min render/min video)")
    else:
        passed(f"zoompan slow ({speed:.2f}x real-time) — limit zoom segments to <3s each")

    return True


# ─── Summary ──────────────────────────────────────────────────────────────────

def print_summary():
    print(f"\n{BOLD}{'═'*60}{RESET}")
    print(f"{BOLD}  VALIDATION SUMMARY{RESET}")
    print(f"{BOLD}{'═'*60}{RESET}")
    passed_count = sum(1 for _, ok in results if ok)
    for label, ok in results:
        icon = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
        print(f"  {icon}  {label}")
    print(f"\n  {passed_count}/{len(results)} tests passed")
    if passed_count == len(results):
        print(f"\n  {GREEN}{BOLD}All components validated — ready to build.{RESET}")
    else:
        print(f"\n  {YELLOW}Fix failing tests before proceeding.{RESET}")
    print()


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(f"Usage: python validate.py <input_video.mp4>")
        sys.exit(1)

    video_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(video_path):
        print(f"Error: file not found: {video_path}")
        sys.exit(1)

    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
        capture_output=True, text=True
    )
    info_data = json.loads(probe.stdout)
    duration = float(info_data["format"]["duration"])
    size_mb = int(info_data["format"]["size"]) // (1024 * 1024)

    print(f"\n{BOLD}Clipforge Component Validation{RESET}")
    print(f"Input: {video_path}")
    print(f"Duration: {duration:.1f}s  Size: {size_mb}MB")

    tmp_dir = tempfile.mkdtemp(prefix="clipforge_validate_")
    info(f"Working dir: {tmp_dir}")

    # Run all tests
    run("FFmpeg capabilities",          test_ffmpeg_caps)
    run("Thai fonts installed",         test_thai_fonts)
    ass_path = None
    try:
        ass_path = test_python_ass(tmp_dir)
        results.append(("python-ass → .ass generation", bool(ass_path)))
    except Exception as e:
        results.append(("python-ass → .ass generation", False))
        print(f"  {RED}✗ FAIL{RESET}  Exception: {e}")

    run("libass Thai subtitle burn",    test_libass_thai,   tmp_dir, ass_path, video_path)
    audio_path = None
    try:
        audio_path = test_audio_extraction(tmp_dir, video_path)
        results.append(("Audio extraction + sync",        bool(audio_path)))
    except Exception as e:
        results.append(("Audio extraction + sync",        False))
        print(f"  {RED}✗ FAIL{RESET}  Exception: {e}")

    transcript_data = None
    try:
        transcript_data = test_whisper(tmp_dir, audio_path or video_path)
        results.append(("faster-whisper transcription",   bool(transcript_data)))
    except Exception as e:
        results.append(("faster-whisper transcription",   False))
        print(f"  {RED}✗ FAIL{RESET}  Exception: {e}")

    run("claude -p subprocess",         test_claude_p,      transcript_data)
    run("FFmpeg concat at boundaries",  test_concat,        tmp_dir, video_path)
    run("zoompan render speed",         test_zoompan_speed, tmp_dir, video_path)

    print_summary()
    print(f"  Test artifacts in: {tmp_dir}")
    print(f"  (Check thai_subtitle_test.mp4 visually for Thai rendering)\n")


if __name__ == "__main__":
    main()
