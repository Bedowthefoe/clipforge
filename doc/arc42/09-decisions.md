# 9. Architecture Decisions (ADRs)

**Purpose:** Each accepted ADR captures one significant architectural decision with full context. Quick-scan register in [project/adr-index.md](../project/adr-index.md).
**Last Updated:** 2026-06-09

---

## How ADRs work here

Each ADR is one markdown file in `decisions/`. The file is **immutable** once Accepted — to revise, write a new ADR that supersedes the old (link both ways). ADRs that are still being shaped live in [features in design](../project/feature-pipeline.md) until they're ready to lock in.

### Status values

| Status | Meaning |
|---|---|
| Proposed | Drafted, not yet locked in |
| Accepted | Locked in, implementation built around it |
| Deprecated | No longer applies but kept for history |
| Superseded by ADR-NNN | Replaced by a new ADR |

---

## ADR Index

| ADR | Title | Status | Date |
|---|---|---|---|
| [001](decisions/ADR-001-local-faster-whisper.md) | Local faster-whisper large-v3 for transcription | ✅ Accepted | 2026-05-24 |
| [002](decisions/ADR-002-claude-p-subprocess.md) | `claude -p` subprocess for LLM passes | ✅ Accepted | 2026-05-24 |
| [003](decisions/ADR-003-libass-thai-rendering.md) | libass + .ass for Thai subtitle rendering | ✅ Accepted | 2026-05-24 |
| [004](decisions/ADR-004-pythainlp-newmm-wrapping.md) | PyThaiNLP newmm for word-aware line wrapping | ✅ Accepted | 2026-06-01 |
| [005](decisions/ADR-005-claude-cleanup-pass.md) | Claude transcript cleanup pass with rules+memory | ✅ Accepted | 2026-06-03 |
| [006](decisions/ADR-006-reading-rate-timing.md) | Reading-rate uniform pacing (Option D) | ✅ Accepted | 2026-06-04 |
| [007](decisions/ADR-007-whisper-word-anchoring.md) | Per-line Whisper-word start-time anchoring (Option E) | ✅ Accepted | 2026-06-07 |
| [008](decisions/ADR-008-overlay-only-default-mode.md) | overlay_only as default pipeline mode | ✅ Accepted | 2026-06-01 |
| [009](decisions/ADR-009-ibm-plex-sans-thai-font.md) | IBM Plex Sans Thai for subtitle rendering | ✅ Accepted | 2026-06-07 |
