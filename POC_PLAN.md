# Clipforge — AI Video Editing Shell App
**Purpose:** POC plan and scope alignment
**Last Updated:** 2026-05-24
**Status:** Active — POC Phase

---

## What Was Originally Requested (Remote Conversation)

User "C" requested a fully automated video editing pipeline with these capabilities:

| # | Feature | Detail |
|---|---|---|
| 1 | Auto highlight trimming | Cut raw video to short-form highlights automatically |
| 2 | Zoom effects + keyword overlay | Zoom in/out synced with speech; pop-up keywords matching spoken words |
| 3 | Thai subtitles + EN technical terms | Thai subtitle track, English-only for domain-specific words |
| 4 | Sound effects | User has SFX library; system should choose and mix automatically |
| 5 | HeyGen integration | AI avatar or lip-sync via HeyGen API |
| 6 | One-shot pipeline | Upload raw video → receive finished video, no manual steps |
| 7 | n8n / Google Drive workflow | Drop file in Drive folder → n8n orchestrates → finished video returned |
| 8 | Multi-AI collaboration | System coordinates Whisper, Claude, HeyGen, FFmpeg automatically |

---

## POC Scope (One Day)

**Goal:** Prove the core editing pipeline works end-to-end on a local video file.

### In Scope

| # | Feature | Approach | Status |
|---|---|---|---|
| 1 | Transcription (Thai + EN) | Groq Whisper large-v3-turbo API (word-level timestamps) | Planned |
| 2 | Highlight selection | Groq LLaMA 3.3-70B scores transcript segments, picks best 60–90s | Planned |
| 3 | Video trim + concat | FFmpeg via subprocess, trim by timestamp pairs | Planned |
| 4 | Zoom effect | FFmpeg zoompan filter, triggered on highlight moments | Planned |
| 5 | EN keyword overlays | FFmpeg drawtext with `enable='between(t,X,Y)'` per word | Planned |
| 6 | Thai subtitles | libass `.ass` format, Sarabun font, burned via FFmpeg | Planned |

### Explicitly Out of Scope for POC

| Feature | Reason | When |
|---|---|---|
| Sound effects mixing | Needs SFX library mapping logic | Phase 2 |
| HeyGen / avatar | Enterprise API cost; not core to editing | Phase 3 |
| Google Drive integration | Infrastructure, not editing logic | Phase 2 |
| n8n workflow | Orchestration layer, builds on top of proven core | Phase 2 |
| One-shot cloud pipeline | Requires Phase 2 + Phase 3 complete first | Phase 3 |
| UI of any kind | Shell app only for POC | Post-POC |

---

## Architecture

```
input.mp4
    │
    ├─ [Groq Whisper API] ──────→ transcript.json
    │                              (word + timestamps, Thai + EN)
    │
    ├─ [Groq LLaMA 3.3-70B] ───→ highlight_segments.json
    │                              ([{start, end, reason}])
    │
    ├─ [python-ass] ────────────→ subs.ass
    │                              (Thai subtitles from transcript)
    │
    └─ [FFmpeg subprocess]
           trim clips by segments
           concat trimmed clips
           zoompan on peak moment
           drawtext keyword overlays (EN)
           burn subs.ass (Thai, Sarabun font)
                │
                ▼
         output_edited.mp4
```

---

## Stack Decisions

| Layer | Tool | Cost | Reason |
|---|---|---|---|
| Transcription | Groq Whisper large-v3-turbo | ~$0.00067/min or free tier | No GPU on machine; Groq is near-instant |
| LLM highlight scoring | Groq LLaMA 3.3-70B | Free tier | No Anthropic API credits; Groq free covers POC |
| Video processing | FFmpeg (subprocess) | Free | Most reliable for filter-graph ops |
| Subtitle format | `.ass` + libass | Free | Only format with correct Thai rendering |
| Thai font | Sarabun (fonts-thai-tlwg) | Free | Full Thai glyph coverage with libass |
| Python libs | `groq`, `python-ass` | Free | Thin wrappers, well-maintained |

**Avoided:**
- `ffmpeg-python` — unmaintained since 2019
- WhisperX — Thai alignment is broken (GitHub issue #737)
- `drawtext` for Thai — FreeType only, no HarfBuzz, boxes instead of glyphs
- Local Whisper — CPU-only machine, large-v3 would take 30–100 min per 10-min video

---

## File Structure

```
clipforge/
├── POC_PLAN.md          ← this file
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── clipforge/
│   ├── __init__.py
│   ├── transcribe.py    ← Groq Whisper → transcript.json
│   ├── highlight.py     ← Groq LLaMA → highlight segments
│   ├── subtitle.py      ← transcript → .ass file
│   └── edit.py          ← FFmpeg pipeline orchestrator
└── main.py              ← entry point: python main.py input.mp4
```

---

## Pass/Fail Criteria for POC

| Test | Pass Condition |
|---|---|
| Thai transcript quality | >80% of words recognizable by ear |
| Highlight selection | At least 3 of 5 picked segments are genuinely engaging |
| Thai subtitle rendering | No missing glyphs (boxes); correct position |
| Zoom effect | Smooth, no jitter, timing matches highlight peak |
| Keyword overlay | EN words appear within 200ms of being spoken |
| Pipeline runtime | <3x video duration on CPU (FFmpeg only, Groq is instant) |
| End-to-end | `python main.py input.mp4` produces watchable `output_edited.mp4` |

---

## Phase Roadmap

```
Phase 1 — POC (today)
  Core pipeline: transcribe → select → edit → output

Phase 2 — Production Shell App
  + Sound effects library mapping
  + Google Drive input/output
  + Batch processing

Phase 3 — Orchestration
  + n8n / Make.com workflow
  + LINE / webhook notifications
  + HeyGen avatar (optional)
```

---

## Prerequisites

```bash
# System
sudo apt install ffmpeg fonts-thai-tlwg fonts-noto

# Python
pip install groq python-ass

# Verify libass
ffmpeg -filters | grep subtitles

# API Keys needed
GROQ_API_KEY=  # console.groq.com — free tier sufficient for POC
```
