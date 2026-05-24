# Clipforge — AI Video Editing Shell App
**Purpose:** Project context, tech decisions, and development guidelines
**Last Updated:** 2026-05-24
**Status:** POC Phase

---

## What Is Clipforge

Shell app that takes a raw video file and outputs a finished short-form video automatically:
- Transcribes speech (Thai + English) with word-level timestamps
- Selects highlight segments using AI
- Trims and concatenates clips
- Applies zoom effects on highlight peaks
- Overlays English keyword pop-ups synced to speech
- Burns Thai subtitles (correct rendering via libass)

**Target user:** Influencers / content creators who want to queue raw footage and receive an edited clip without manual work.

---

## Current Phase: POC

**Goal:** Prove the core pipeline works end-to-end on a local video file.

**Entry point:**
```bash
python main.py input.mp4
# → output_edited.mp4
```

**Full scope and pass/fail criteria:** See [`POC_PLAN.md`](POC_PLAN.md)

---

## Tech Stack Decisions

| Layer | Tool | Reason |
|---|---|---|
| Transcription | **faster-whisper large-v3** (local, CPU) | 10-min processing wait acceptable for queue-based workflow; no API cost; Thai + EN in one pass |
| LLM highlight scoring | **`claude -p` subprocess** | Uses existing Pro subscription Agent SDK credits ($20/mo); no separate API key needed |
| Video processing | **FFmpeg via subprocess** | Most reliable for filter-graph ops; ffmpeg-python is dead (unmaintained since 2019) |
| Subtitle format | **`.ass` + libass** | Only correct path for Thai — `drawtext` uses FreeType only (no HarfBuzz, produces boxes) |
| Thai font | **Noto Sans Thai** (fonts-noto) | Full Thai glyph coverage confirmed with libass; Sarabun not in Ubuntu default packages |
| Subtitle generation | **python-ass** | Clean API to generate `.ass` files programmatically from timestamps |

### How `claude -p` works in this project

```python
import subprocess, json

result = subprocess.run(
    ["claude", "-p", "--output-format", "json", prompt],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
# data["result"] contains Claude's response
```

Billed against Pro plan's $20/month Agent SDK credit budget. No `ANTHROPIC_API_KEY` needed.

---

## Critical Technical Constraints

These are non-negotiable — violating them produces broken output:

1. **Never use `ffmpeg-python`** — unmaintained since 2019, known bugs with filter expressions; use `subprocess.run(["ffmpeg", ...])` directly

2. **Never use WhisperX for Thai** — the wav2vec2 alignment model for Thai is broken (upstream issue #737); use faster-whisper directly with `word_timestamps=True`

3. **Never use `drawtext` for Thai text** — FreeType without HarfBuzz = missing glyphs rendered as boxes; always use libass `.ass` files for Thai

4. **Always specify Thai font explicitly in `.ass` Style block** — use `Noto Sans Thai`; if unset, fontconfig may select a Latin font with no Thai glyphs

5. **FFmpeg zoompan gotchas:**
   - Set `d=1` to process every frame (not just the first)
   - Use `pzoom` (not `zoom`) when referencing previous zoom level in expressions
   - Use `enable='between(t,START,END)'` to scope zoom to specific moments

---

## File Structure

```
clipforge/
├── CLAUDE.md             ← this file
├── POC_PLAN.md           ← scope, roadmap, pass/fail criteria
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py               ← entry point: python main.py input.mp4
└── clipforge/
    ├── __init__.py
    ├── transcribe.py     ← faster-whisper → transcript.json
    ├── highlight.py      ← claude -p subprocess → highlight segments
    ├── subtitle.py       ← transcript → subs.ass
    └── edit.py           ← FFmpeg pipeline orchestrator
```

---

## System Prerequisites

```bash
# FFmpeg with libass support
sudo apt install ffmpeg fonts-thai-tlwg fonts-noto

# Verify libass is present
ffmpeg -filters | grep subtitles

# Python deps
pip install faster-whisper python-ass

# Whisper model download (happens automatically on first run, ~1.5GB)
# Model stored in ~/.cache/huggingface/hub/
```

---

## Development Guidelines

- **Follow global principles:** `~/.claude/CLAUDE.md` (session start protocol, execution protocol, permission boundaries)
- **Read complete files** before editing — no `limit`/`offset`
- **Align before implementing** — Analyze → Propose → Align → TODO → Confirm → Implement → Review
- **No ffmpeg-python, no WhisperX Thai, no drawtext for Thai** (see constraints above)
- **Test with a real video file** — do not claim success without running the pipeline end-to-end

---

## Roadmap

```
Phase 1 — POC (current)
  Core pipeline: transcribe → highlight → edit → subtitle → output

Phase 2 — Production Shell App
  + Sound effects library mapping and mixing
  + Google Drive input/output integration
  + Batch processing / job queue

Phase 3 — Orchestration
  + n8n / Make.com workflow
  + LINE / webhook notifications
  + HeyGen avatar (optional, Enterprise API required)
```
