# Clipforge Roadmap

**Purpose:** Where we are, where we're going, what's in scope per phase.
**Last Updated:** 2026-06-09

---

## Phase 0 — POC Foundation (DONE)

**Goal:** Prove each component capacity individually before integrating.

| Milestone | Status |
|---|---|
| Whisper local Thai transcription works at acceptable speed/accuracy | ✅ Done |
| `claude -p` subprocess returns parseable JSON | ✅ Done |
| FFmpeg renders portrait Thai subtitle output without box-glyph failure | ✅ Done |
| python-ass generates valid .ass with two styles | ✅ Done |
| 4-stage end-to-end pipeline runs from raw mp4 to edited mp4 | ✅ Done |

Exit: validated capabilities documented in [arc42/02-constraints.md](../arc42/02-constraints.md). Pipeline ran on `20260401_084849.mp4` in May 2026.

---

## Phase 1 — Reference Match (DONE)

**Goal:** Produce output that matches client's reference target on measured axes.

| Milestone | Status |
|---|---|
| Quantitative analysis of client target sample | ✅ Done — framing, font, line distribution, popup density measured |
| Match framing: 55% subject vertical fill via baseline crop | ✅ Done — 1.48× crop centered at y=0.56 |
| Match subtitle style: white + drop shadow, no outline | ✅ Done — IBM Plex Sans Thai, shadow=10 |
| Match Thai mark stacking (no tone/vowel collisions) | ✅ Done via [ADR-009](../arc42/decisions/ADR-009-ibm-plex-sans-thai-font.md) |
| Word-aware Thai line wrapping | ✅ Done via [ADR-004](../arc42/decisions/ADR-004-pythainlp-newmm-wrapping.md) |
| Netflix-compliant timing (0.83-2.5s, no flicker) | ✅ Done via [ADR-006](../arc42/decisions/ADR-006-reading-rate-timing.md) |
| Per-line speech anchoring | ✅ Done via [ADR-007](../arc42/decisions/ADR-007-whisper-word-anchoring.md) |
| STT cleanup pass to fix Thai transcription errors | ✅ Done via [ADR-005](../arc42/decisions/ADR-005-claude-cleanup-pass.md) |
| Pink keyword popups at topic shifts | ✅ Done — 3 Claude-selected Thai phrases |
| Audit-trail JSON per run + timestamped outputs | ✅ Done |

Exit: v17 `new-test-RAW-0601_20260607_112348.mp4` ships matched-style output. Client review pending.

---

## Phase 2 — Production Hardening (NEXT)

**Goal:** Make the pipeline reliable, configurable per content type, and ready for batch use.

| Milestone | Status |
|---|---|
| Real-content test set (5+ creator videos across content types) | ⬜ Pending |
| Per-creator config profiles (different speech speeds, framing, popup style) | ⬜ Pending |
| Robustness: handle videos with no speech / heavy music / off-camera dialogue | ⬜ Pending |
| Resegment improvements: snap pause cuts to PyThaiNLP word boundaries | ⬜ Pending — see [debt 003](../debt/003-resegment-bisects-thai-words.md) |
| Cleanup memory promotion workflow (operator confirms → memory file grows) | ⬜ Pending |
| Pause-detection on raw audio (Option C) for tighter sync | ⬜ Pending — see [feature-pipeline.md](feature-pipeline.md) |
| Production-mode confidence threshold default = "high" | ⬜ Pending |

Exit criteria: 5 creator videos render acceptably without manual config tuning.

---

## Phase 3 — Workflow Integration (LATER)

**Goal:** Move from CLI to a queued workflow.

| Milestone | Notes |
|---|---|
| Google Drive input/output integration | Watch folder → process → return |
| Batch processing | Queue raw videos, process serially overnight |
| n8n / Make.com orchestration | Trigger renders from external events |
| LINE / webhook notifications | "Your video is ready" alerts |

Exit criteria: client drops raw video into a Drive folder, gets edited video back the next day with no manual operator action.

---

## Phase 4 — Production Features (LATER)

**Goal:** Match the features in the original creator request (POC was a subset).

| Feature | Source |
|---|---|
| Sound effects mixing | Original request item 4 |
| HeyGen / AI avatar | Original request item 5 — needs Enterprise API |
| Multi-AI orchestration polish | Original request item 8 |
| Web UI (creator self-serve) | Beyond original — emerges if client wants |

---

## Currently DEFERRED (not roadmapped)

- Multi-language support beyond Thai+EN
- Real-time / live streaming
- Cloud-native (Kubernetes, AWS, etc.) deployment
- Mobile app

These would need a separate strategy discussion before committing.
