#!/usr/bin/env python3
"""
demo.py — End-to-end Clipforge demo
Transcribes → analyses → edits a raw video with all effects.

Usage: python demo.py <input_video.mp4>
Output: test/demo_output.mp4
"""

import sys, os, json, subprocess, tempfile, datetime, shutil, time, re
import ass as ass_lib

# ─── Config ───────────────────────────────────────────────────────────────────

VIDEO     = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else None
OUT_DIR   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
OUTPUT    = os.path.join(OUT_DIR, "demo_output.mp4")
TMP       = tempfile.mkdtemp(prefix="clipforge_demo_")
FONT_DIR  = "/usr/share/fonts"
THAI_FONT = "Noto Sans Thai"

RESET = "\033[0m"; BOLD = "\033[1m"; GREEN = "\033[92m"
YELLOW = "\033[93m"; CYAN = "\033[96m"

def log(msg):   print(f"  {YELLOW}→{RESET}  {msg}")
def ok(msg):    print(f"  {GREEN}✓{RESET}  {msg}")
def step(msg):  print(f"\n{BOLD}{CYAN}▶  {msg}{RESET}")


# ─── Step 1: Transcribe ───────────────────────────────────────────────────────

def transcribe(video_path):
    step("Step 1/4 — Transcribing with faster-whisper large-v3")

    # Extract audio
    audio = os.path.join(TMP, "audio.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-ar", "16000", "-ac", "1", "-f", "wav", audio
    ], capture_output=True, check=True)
    log("Audio extracted (16kHz mono WAV)")

    from faster_whisper import WhisperModel
    log("Loading model (cached after first run)...")
    t0 = time.time()
    model = WhisperModel("large-v3", device="cpu", compute_type="int8")
    log(f"Model loaded in {time.time()-t0:.1f}s")

    log("Transcribing full video...")
    t0 = time.time()
    segments, info = model.transcribe(audio, word_timestamps=True, language=None)
    segments = list(segments)
    elapsed = time.time() - t0

    log(f"Language: {info.language} ({info.language_probability:.0%} confidence)")
    log(f"Transcription: {elapsed:.0f}s ({len(segments)} segments)")

    data = []
    for seg in segments:
        words = [{"word": w.word, "start": round(w.start, 3), "end": round(w.end, 3)}
                 for w in (seg.words or [])]
        data.append({
            "start": round(seg.start, 3),
            "end":   round(seg.end, 3),
            "text":  seg.text.strip(),
            "words": words
        })

    path = os.path.join(TMP, "transcript.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    ok(f"Transcript saved — {len(data)} segments")
    return data


# ─── Step 2: Claude analysis ──────────────────────────────────────────────────

def analyse(transcript, video_duration):
    step("Step 2/4 — Analysing with Claude (keywords + zoom moments)")

    text_summary = "\n".join(
        f"[{s['start']:.1f}s-{s['end']:.1f}s] {s['text']}" for s in transcript
    )

    prompt = f"""You are an expert short-form video editor for Thai fitness content.

Video duration: {video_duration:.1f} seconds
Transcript (Thai fitness video, timestamps in seconds):
{text_summary}

Return ONLY a JSON object with exactly this structure — no explanation, no markdown:
{{
  "keywords": [
    {{"text": "English term", "start": 0.0, "end": 0.0, "size": 60}},
    ...
  ],
  "zoom_moments": [
    {{"start": 0.0, "end": 0.0, "direction": "in"}},
    ...
  ],
  "summary": "one sentence English description of this video"
}}

Rules:
- keywords: 4-6 English fitness/exercise terms that match what is being said (e.g. "Side Squat", "Inner Thigh", "Glutes", "Hip Hinge"). Pick timestamps that match the spoken moment. Duration 1.5-2.5s each.
- zoom_moments: exactly 2 moments, each 2.5s long. Pick the most energetic or key demonstration moments. Alternate direction: first "in", second "out".
- All timestamps must be within 0 and {video_duration:.1f}
- zoom end = zoom start + 2.5"""

    log("Calling claude -p...")
    t0 = time.time()
    r = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True, text=True, timeout=90
    )
    log(f"Claude responded in {time.time()-t0:.1f}s")

    if r.returncode != 0:
        raise RuntimeError(f"claude -p failed: {r.stderr[:200]}")

    outer = json.loads(r.stdout)
    result_text = outer.get("result", r.stdout)

    # Strip markdown fences if present
    result_text = re.sub(r"```json\s*|\s*```", "", result_text).strip()
    analysis = json.loads(result_text)

    path = os.path.join(TMP, "analysis.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    ok(f"Keywords: {[k['text'] for k in analysis['keywords']]}")
    ok(f"Zoom moments: {[(z['start'], z['end'], z['direction']) for z in analysis['zoom_moments']]}")
    ok(f"Summary: {analysis['summary']}")
    return analysis


# ─── Step 3: Generate .ass subtitles ──────────────────────────────────────────

def make_subtitles(transcript, video_path):
    step("Step 3/4 — Generating Thai subtitles (.ass)")

    # Get video resolution
    probe = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "v:0", video_path
    ], capture_output=True, text=True)
    streams = json.loads(probe.stdout)["streams"]
    width  = streams[0]["width"]
    height = streams[0]["height"]

    doc = ass_lib.Document()
    doc.play_res_x = width
    doc.play_res_y = height

    # Main subtitle style
    style = ass_lib.Style()
    style.name          = "Default"
    style.fontname      = THAI_FONT
    style.fontsize      = max(32, height // 22)
    style.primary_color = ass_lib.data.Color(r=255, g=255, b=255, a=0)
    style.outline_color = ass_lib.data.Color(r=0,   g=0,   b=0,   a=0)
    style.back_color    = ass_lib.data.Color(r=0,   g=0,   b=0,   a=160)
    style.bold          = True
    style.outline       = 2
    style.shadow        = 1
    style.alignment     = 2   # bottom-center
    style.margin_v      = 40
    doc.styles.append(style)

    # One dialogue event per segment
    for seg in transcript:
        if not seg["text"]:
            continue
        event = ass_lib.Dialogue()
        event.start = datetime.timedelta(seconds=seg["start"])
        event.end   = datetime.timedelta(seconds=seg["end"])
        event.style = "Default"
        event.text  = seg["text"]
        doc.events.append(event)

    ass_path = os.path.join(TMP, "subs.ass")
    with open(ass_path, "w", encoding="utf-8-sig") as f:
        doc.dump_file(f)

    ok(f"Subtitles: {len(doc.events)} events → {ass_path}")
    return ass_path


# ─── Step 4: FFmpeg render ────────────────────────────────────────────────────

def render(video_path, analysis, ass_path, video_duration):
    step("Step 4/4 — Rendering with FFmpeg")
    os.makedirs(OUT_DIR, exist_ok=True)

    # Probe video resolution + fps
    probe = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "v:0", video_path
    ], capture_output=True, text=True)
    stream = json.loads(probe.stdout)["streams"][0]
    width  = stream["width"]
    height = stream["height"]
    fps_raw = stream.get("r_frame_rate", "30/1")
    fps_num, fps_den = map(int, fps_raw.split("/"))
    fps = fps_num / fps_den
    log(f"Video: {width}×{height} @ {fps:.1f}fps")

    zoom_moments = analysis.get("zoom_moments", [])
    keywords     = analysis.get("keywords", [])

    # ── Strategy: segment-based zoom (fast) ──
    # Split video into segments, apply zoompan only to zoom windows,
    # copy the rest. Then concat + overlay drawtext + subtitles.

    # Build timeline: list of (start, end, apply_zoom, zoom_direction)
    events = sorted(zoom_moments, key=lambda z: z["start"])
    timeline = []
    cursor = 0.0
    for z in events:
        zs, ze = max(cursor, z["start"]), min(z["end"], video_duration)
        if zs > cursor:
            timeline.append((cursor, zs, False, None))
        timeline.append((zs, ze, True, z["direction"]))
        cursor = ze
    if cursor < video_duration:
        timeline.append((cursor, video_duration, False, None))

    # Render each segment
    log(f"Rendering {len(timeline)} segments (zoom applied only to {len(zoom_moments)} windows)...")
    segment_files = []
    for i, (start, end, do_zoom, direction) in enumerate(timeline):
        seg_out = os.path.join(TMP, f"seg_{i:03d}.mp4")
        duration = end - start

        if do_zoom:
            if direction == "in":
                z_expr = f"min(pzoom+0.004,1.3)"
            else:
                z_expr = f"if(eq(on,1),1.3,max(pzoom-0.004,1.0))"

            vf = (
                f"zoompan="
                f"z='{z_expr}':"
                f"d=1:"
                f"x='iw/2-(iw/zoom/2)':"
                f"y='ih/2-(ih/zoom/2)':"
                f"fps={fps:.3f}:"
                f"s={width}x{height}"
            )
            log(f"  Segment {i}: zoom-{direction} [{start:.1f}s→{end:.1f}s] ({duration:.1f}s)")
        else:
            vf = "copy"
            log(f"  Segment {i}: copy [{start:.1f}s→{end:.1f}s] ({duration:.1f}s)")

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start), "-i", video_path, "-t", str(duration),
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-ar", "44100",
            seg_out
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"Segment {i} failed:\n{r.stderr[-400:]}")
        segment_files.append(seg_out)

    # ── Concat segments ──
    log("Concatenating segments...")
    concat_list = os.path.join(TMP, "concat.txt")
    with open(concat_list, "w") as f:
        for sf in segment_files:
            f.write(f"file '{sf}'\n")

    concat_out = os.path.join(TMP, "concat.mp4")
    r = subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list, "-c", "copy", concat_out
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Concat failed:\n{r.stderr[-400:]}")
    ok("Segments concatenated")

    # ── Build drawtext chain for keywords ──
    drawtext_filters = []
    for kw in keywords:
        txt   = kw["text"].replace("'", "\\'").replace(":", "\\:")
        start = kw["start"]
        end   = kw["end"]
        size  = kw.get("size", 60)
        # White bold text with black outline, centered top-third
        y_pos = height // 4
        dt = (
            f"drawtext=text='{txt}':"
            f"fontsize={size}:"
            f"fontcolor=white:"
            f"borderw=3:"
            f"bordercolor=black:"
            f"x=(w-tw)/2:"
            f"y={y_pos}:"
            f"enable='between(t,{start},{end})'"
        )
        drawtext_filters.append(dt)

    # ── Final pass: drawtext + subtitles ──
    log("Applying keyword overlays + Thai subtitles...")

    # Escape ass path for FFmpeg
    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")

    vf_parts = drawtext_filters + [f"subtitles={ass_escaped}:fontsdir={FONT_DIR}"]
    vf_chain = ",".join(vf_parts)

    r = subprocess.run([
        "ffmpeg", "-y", "-i", concat_out,
        "-vf", vf_chain,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "copy",
        OUTPUT
    ], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Final render failed:\n{r.stderr[-600:]}")

    size_mb = os.path.getsize(OUTPUT) / (1024 * 1024)
    ok(f"Output: {OUTPUT} ({size_mb:.1f}MB)")
    return OUTPUT


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not VIDEO or not os.path.exists(VIDEO):
        print("Usage: python demo.py <input_video.mp4>")
        sys.exit(1)

    print(f"\n{BOLD}Clipforge Demo Pipeline{RESET}")
    print(f"Input:  {VIDEO}")
    print(f"Output: {OUTPUT}")
    print(f"Tmp:    {TMP}")

    # Get video duration
    probe = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", VIDEO
    ], capture_output=True, text=True)
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    log(f"Duration: {duration:.1f}s")

    t_total = time.time()

    transcript = transcribe(VIDEO)
    analysis   = analyse(transcript, duration)
    ass_path   = make_subtitles(transcript, VIDEO)
    output     = render(VIDEO, analysis, ass_path, duration)

    elapsed = time.time() - t_total
    print(f"\n{BOLD}{GREEN}✓ Done in {elapsed/60:.1f} minutes{RESET}")
    print(f"  Output: {output}\n")


if __name__ == "__main__":
    main()
