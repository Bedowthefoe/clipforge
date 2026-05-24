#!/usr/bin/env python3
"""
Clipforge — AI video editing pipeline
Usage:
  python main.py input.mp4
  python main.py input.mp4 --config custom.yaml
  python main.py input.mp4 --transcript existing.json   # skip Whisper
  python main.py input.mp4 --output out/final.mp4
"""

import argparse
import json
import os
import sys
import tempfile
import time

RESET = "\033[0m"; BOLD = "\033[1m"; GREEN = "\033[92m"
YELLOW = "\033[93m"; CYAN = "\033[96m"

def step(n, total, msg):
    print(f"\n{BOLD}{CYAN}[{n}/{total}] {msg}{RESET}")

def main():
    parser = argparse.ArgumentParser(description="Clipforge AI video editor")
    parser.add_argument("video",       help="Input video file")
    parser.add_argument("--config",    default="config.yaml", help="Config file (default: config.yaml)")
    parser.add_argument("--transcript",help="Existing transcript JSON (skips Whisper)")
    parser.add_argument("--output",    help="Output path (default: test/<input>_edited.mp4)")
    args = parser.parse_args()

    if not os.path.exists(args.video):
        print(f"Error: video not found: {args.video}")
        sys.exit(1)

    # ── Load config ──
    from clipforge.config import load as load_config
    cfg = load_config(args.config)

    # ── Setup paths ──
    video_path = os.path.abspath(args.video)
    base_name  = os.path.splitext(os.path.basename(video_path))[0]
    out_dir    = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test")
    os.makedirs(out_dir, exist_ok=True)
    run_id     = time.strftime("%Y%m%d_%H%M%S")
    output     = args.output or os.path.join(out_dir, f"{base_name}_{run_id}.mp4")
    tmp_dir    = tempfile.mkdtemp(prefix=f"clipforge_{run_id}_")

    import subprocess
    probe = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path
    ], capture_output=True, text=True)
    duration = float(__import__("json").loads(probe.stdout)["format"]["duration"])

    print(f"\n{BOLD}Clipforge{RESET}")
    print(f"  Input:    {video_path} ({duration:.0f}s)")
    print(f"  Config:   {args.config}")
    print(f"  Output:   {output}")
    print(f"  Target:   ~{cfg.output.target_duration}s highlight reel")
    print(f"  Tmp:      {tmp_dir}")

    t_total = time.time()

    # ── Step 1: Transcribe ──
    from clipforge import transcribe
    step(1, 4, "Transcribe")
    transcript = transcribe.run(video_path, cfg, tmp_dir, args.transcript)

    # ── Step 2: Select highlights ──
    from clipforge import highlight
    step(2, 4, "Select highlights")
    analysis = highlight.run(transcript, duration, cfg)

    # Save analysis alongside output for audit trail
    analysis_path = output.replace(".mp4", "_analysis.json")
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump({
            "run_id":    run_id,
            "input":     video_path,
            "config":    args.config,
            "transcript": args.transcript,
            **analysis
        }, f, ensure_ascii=False, indent=2)
    # Also keep a copy in tmp
    with open(os.path.join(tmp_dir, "analysis.json"), "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)

    # ── Step 3 + 4: Edit ──
    from clipforge import editor
    step(3, 4, "Cut & assemble")
    editor.run(video_path, transcript, analysis, cfg, tmp_dir, output)

    step(4, 4, "Done")
    elapsed = time.time() - t_total
    print(f"\n{BOLD}{GREEN}✓ Finished in {elapsed/60:.1f} minutes{RESET}")
    print(f"  Output:   {output}")
    print(f"  Analysis: {os.path.join(tmp_dir, 'analysis.json')}\n")


if __name__ == "__main__":
    main()
