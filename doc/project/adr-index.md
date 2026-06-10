# ADR Index

**Purpose:** Quick-scan register of all architecture decisions. Full text in [arc42/09-decisions.md](../arc42/09-decisions.md) and individual files in [arc42/decisions/](../arc42/decisions/).
**Last Updated:** 2026-06-09

---

| ADR | Title | Status | Date | One-liner |
|---|---|---|---|---|
| [001](../arc42/decisions/ADR-001-local-faster-whisper.md) | Local faster-whisper large-v3 | ✅ Accepted | 2026-05-24 | CPU int8 quantization; ~10 min/min audio; zero per-call cost |
| [002](../arc42/decisions/ADR-002-claude-p-subprocess.md) | `claude -p` subprocess for LLM passes | ✅ Accepted | 2026-05-24 | Uses Pro plan Agent SDK credit; no API key |
| [003](../arc42/decisions/ADR-003-libass-thai-rendering.md) | libass + .ass for Thai subtitles | ✅ Accepted | 2026-05-24 | drawtext is structurally incapable of Thai; HarfBuzz required |
| [004](../arc42/decisions/ADR-004-pythainlp-newmm-wrapping.md) | PyThaiNLP newmm for line wrapping | ✅ Accepted | 2026-06-01 | Thai has no inter-word spaces; libass can't auto-wrap semantically |
| [005](../arc42/decisions/ADR-005-claude-cleanup-pass.md) | Claude transcript cleanup pass | ✅ Accepted | 2026-06-03 | Rules+memory pattern; surgical substring replace; confidence-gated |
| [006](../arc42/decisions/ADR-006-reading-rate-timing.md) | Reading-rate uniform pacing (Option D) | ✅ Accepted | 2026-06-04 | Whisper end times silence-biased; clamp every line to [0.83, 2.5]s |
| [007](../arc42/decisions/ADR-007-whisper-word-anchoring.md) | Per-line Whisper-word anchoring (Option E) | ✅ Accepted | 2026-06-07 | Multiply alignment points; honor pauses up to 1s |
| [008](../arc42/decisions/ADR-008-overlay-only-default-mode.md) | overlay_only as default mode | ✅ Accepted | 2026-06-01 | Target reference has no cuts; <60s clips ship full content + overlays |
| [009](../arc42/decisions/ADR-009-ibm-plex-sans-thai-font.md) | IBM Plex Sans Thai default font | ✅ Accepted | 2026-06-07 | Loopless modern + 15 GPOS lookups; proper Thai mark stacking |

---

## Status legend

- ✅ **Accepted** — implementation built around it
- 🟡 **Proposed** — drafted, not yet committed
- 🔴 **Deprecated** — no longer applies but kept for history
- ➡ **Superseded by ADR-NNN** — replaced
