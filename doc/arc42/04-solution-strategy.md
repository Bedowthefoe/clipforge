# 4. Solution Strategy

**Purpose:** The high-level approach — the few big choices that shape everything else.
**Last Updated:** 2026-06-09

---

## Strategy in One Paragraph

Clipforge is a **synchronous, single-shot, locally-orchestrated CPU pipeline**. A raw video flows through five named stages — Transcribe → Cleanup → Highlight → Subtitle → Edit — each producing a typed artifact the next stage consumes. AI capabilities (Whisper for STT, Claude for proofreading and keyword selection) are called as subprocess steps with idempotent prompts; nothing runs in the background, nothing is queued internally. The whole pipeline is **config-driven**: prompt text, style parameters, timing thresholds, and mode selection all live in `config.yaml`.

The architecture is dictated by three operating realities:

1. **Local CPU only** (TC-1) → Whisper large-v3 with int8 quantization, no GPU layers anywhere
2. **No paid APIs** (TC-3) → `claude -p` subprocess, billed against Pro plan Agent SDK credit
3. **Editor's eye matters more than ML accuracy** → cleanup pass + reference-video-derived defaults > raw Whisper output

---

## The Five Stages

| # | Stage | Module | Input | Output | AI? |
|---|---|---|---|---|---|
| 1 | Transcribe | `clipforge/transcribe.py` | `raw.mp4` | List of segments `{start, end, text, words}` | Whisper (local) |
| 2 | Cleanup | `clipforge/cleanup.py` | Segments + rules + memory | Corrected segments + correction log | Claude (cloud) |
| 3 | Highlight | `clipforge/highlight.py` | Corrected segments | `{keyword_popups: [{text, start, duration}]}` | Claude (cloud) |
| 4 | Subtitle | `clipforge/subtitle.py` | Corrected segments + popups + cfg | `subs.ass` (libass file with two styles) | Pure code |
| 5 | Edit | `clipforge/editor.py` | `raw.mp4` + `subs.ass` + cfg | `edited.mp4` | Pure code (FFmpeg) |

Stages are pure functions of their inputs (no global state). They are sequenced from `main.py`. Each stage can be re-run independently using `--transcript` flag (which skips the 10-minute Whisper step).

---

## Mode Dispatch — overlay_only vs highlight_reel

`cfg.mode` switches between two pipeline philosophies:

| | `overlay_only` (default) | `highlight_reel` (legacy) |
|---|---|---|
| **What it does** | Keep the full input, add overlays | Cut speech to target_duration, glue together |
| **Best for** | <60s creator clips (matches client reference) | Long-form footage that needs trimming |
| **Cleanup** | Full transcript preserved | Incomplete-sentence segments dropped |
| **Highlight** | Returns `keyword_popups` only | Returns `selected[]`, `zoom_moments[]`, `keywords[]` |
| **Editor** | Single FFmpeg pass | Multi-pass cut → concat → overlay |
| **Status** | Active default | Maintained but de-prioritised |

Decision rationale: see [ADR-008](decisions/ADR-008-overlay-only-default-mode.md).

---

## Subtitle Timing Strategy (Option D + E)

Independent of the rest of the pipeline, subtitle event timing is its own design domain. Industry-standard reading-rate uniform pacing with per-line Whisper-word anchoring:

- **Each line duration** = clamp(chars / target_cps, min_event_duration, max_event_duration)
- **Each line start** = anchor to Whisper-word containing first character (Option E)
- **Floors**: min_event_duration 0.83s (Netflix standard); max 2.5s (short-form ceiling); inter_event_gap 0.08s (~2 frames)
- **Drift cap**: honored anchor pauses capped at max_drift_correction (1.0s)

See [ADR-006](decisions/ADR-006-reading-rate-timing.md), [ADR-007](decisions/ADR-007-whisper-word-anchoring.md).

---

## What this strategy gives up

| Trade-off | Cost | Why we accept it |
|---|---|---|
| 10 minutes per minute of audio (Whisper CPU) | Slow turnaround | Cost goal (QG-3); operator confirmed queue-acceptable |
| Whisper Thai accuracy is ~95% | Some words wrong | Cleanup pass catches most; remaining 1-2% acceptable |
| Per-line micro-anchoring vs precise word-sync | Subs may lead/lag by ~100ms | Predictability + readability win for sound-off viewing |
| Subprocess to `claude -p` is sequential | Each call costs ~25-60s | Total spend acceptable on 44s test video; future async if needed |
| No retry, no resume | Crash mid-run loses ~10 min | Acceptable for POC; runs are short; resume = re-run with `--transcript` |
