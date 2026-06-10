# Clipforge Handoff

**Purpose:** Cross-session state. What just happened, what's the project status now, what to pick up next. Updated at the end of every working session.
**Last Updated:** 2026-06-09

---

## TL;DR for the next session

**Phase 1 — Reference Match is substantially complete.** v17 produces output matching the client's reference target on every measured axis (framing, font, timing, mark stacking, cleanup, wrapping, popups).

We just finished adopting the arc42 + project + product + sessions + debt documentation pattern (mirroring Kairos / Nexus / Aegis). The doc tree is fully populated.

**Next session focus:** brainstorm Phase 2 (production hardening) — industry standards research, target design for multi-creator support, and extended roadmap.

---

## What just changed (last session)

1. Subtitle timing rebuilt around industry standards:
   - Option D (reading-rate uniform pacing) → [ADR-006](doc/arc42/decisions/ADR-006-reading-rate-timing.md)
   - Option E (per-line Whisper-word anchoring) → [ADR-007](doc/arc42/decisions/ADR-007-whisper-word-anchoring.md)
2. Critical cleanup bug fixed — surgical substring replace instead of full-segment overwrite. See [debt 001](doc/debt/001-cleanup-bug-fixed.md).
3. Font switched to **IBM Plex Sans Thai** for clean Thai mark stacking → [ADR-009](doc/arc42/decisions/ADR-009-ibm-plex-sans-thai-font.md).
4. Full doc strategy adopted — see [`doc/`](doc/).

Latest output: `test/new-test-RAW-0601_20260607_112348.mp4` (v17).

---

## Pipeline status

| Stage | Status | Notes |
|---|---|---|
| Transcribe | ✅ Working | faster-whisper large-v3 CPU int8; pause-based resegmentation; cleanup pass |
| Cleanup | ✅ Working | Surgical substring replace; confidence-gated; rules.md + memory.md |
| Highlight | ✅ Working | 3 Thai keyword popups per video |
| Subtitle | ✅ Working | Two ASS styles; Option D+E timing; word-aware wrapping |
| Edit | ✅ Working | Single FFmpeg pass: crop → libass burn; H.264 + AAC mp4 |

Mode: `overlay_only` is default. `highlight_reel` still exists but has bit-rot risk — see [debt 002](doc/debt/002-highlight-reel-mode-bitrot-risk.md).

---

## Open work (highest priority first)

| # | Item | Where to find it | Phase |
|---|---|---|---|
| 1 | **Brainstorm Phase 2 design** — industry standards, target design, roadmap | New session topic | Phase 2 |
| 2 | F-001 — cleanup memory promotion workflow | [feature-pipeline](doc/project/feature-pipeline.md#f-001) | Phase 2 |
| 3 | F-002 — per-creator config profiles | [feature-pipeline](doc/project/feature-pipeline.md#f-002) | Phase 2 |
| 4 | F-004 — snap pause cuts to PyThaiNLP word boundaries | [feature-pipeline](doc/project/feature-pipeline.md#f-004) + [debt 003](doc/debt/003-resegment-bisects-thai-words.md) | Phase 2 |
| 5 | Real-content test set (5+ creator videos) | [ROADMAP Phase 2](doc/project/ROADMAP.md#phase-2--production-hardening-next) | Phase 2 |
| 6 | Client review of v17 output | Manual | Phase 1 close |
| 7 | requirements.txt + venv adoption | [risks-debt](doc/arc42/11-risks-debt.md) item 006 | Phase 2 |

---

## Open questions to resolve

See [open-questions.md](doc/project/open-questions.md) for the active list. Top of the list:

- Q-001: cleanup_memory.md correction-entry structure
- Q-002: deterministic-pre-pass vs Claude-only for known corrections
- Q-003: `target_cps: 18` default — generalize per creator?
- Q-006: `max_drift_correction: 1.0` — right cap?

---

## How to iterate quickly

To re-render with a config change without re-running Whisper (saves 10 minutes):

```bash
python main.py test/new-test-RAW-0601.mp4 \
  --transcript test/analysis/raw_0601_transcript.json
```

The cached transcript at `test/analysis/raw_0601_transcript.json` is the post-resegmentation post-completeness-annotation output from Whisper. Loading it skips Stage 1.

For visual frame comparison: `ffmpeg -y -i test/<output>.mp4 -vf "fps=1,scale=540:-2" test/analysis/output_frames_vN/o_%03d.jpg`

---

## Files to know about

| Path | Purpose |
|---|---|
| `config.yaml` | All tunable parameters. Operator-edited. |
| `clipforge/cleanup_rules.md` | Static Thai STT cleanup guidelines. Read every run. |
| `clipforge/cleanup_memory.md` | Empty placeholder. Grows when operator confirms corrections. |
| `test/analysis/raw_0601_transcript.json` | Cached Whisper output — use with `--transcript` to skip Whisper |
| `test/output-sample-quality-0317.mp4` | Client's reference target (measured quantitatively, defaults derived) |
| `target-font-screenshot.jpg` | Client's font sample — drove style choice (white + drop shadow) |
| `doc/` | All architecture + project + product + session docs |
| `HANDOFF.md` | This file. |

---

## Recent commits to be aware of

Run `git log --oneline -20` to see the latest. As of this session's end the working tree may have uncommitted changes for the doc tree adoption — commit when you're ready.
