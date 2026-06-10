# arc42 Architecture Documentation

**[← Back to docs](../README.md)**

arc42 is a pragmatic template for software architecture documentation. Clipforge uses it as the durable record of architectural decisions and structure — separate from the ephemeral session state in [HANDOFF.md](../../HANDOFF.md).

---

## Sections

| § | Title | Status | Description |
|---|---|---|---|
| [1](01-goals.md) | Introduction and Goals | ✅ Done | Purpose, functional goals, quality goals, stakeholders |
| [2](02-constraints.md) | Constraints | ✅ Done | Local-first, no-GPU, Pro-plan-only — non-negotiables |
| [3](03-context-scope.md) | System Context and Scope | ✅ Done | Inputs (raw video), outputs (edited video + audit JSON), external actors |
| [4](04-solution-strategy.md) | Solution Strategy | ✅ Done | Pipeline approach, queue-based execution, AI division of labour |
| [5](05-building-blocks.md) | Building Block View | ✅ Done | Modules: transcribe, cleanup, highlight, subtitle, editor |
| [6](06-runtime-view.md) | Runtime View | ✅ Done | End-to-end pipeline flow + per-stage timing |
| 7 | Deployment | ⬜ Pending | Single-host local for POC; cloud/n8n later |
| 8 | Crosscutting Concepts | ⬜ Pending | Config-driven, audit-trailed, fail-loud |
| [9](09-decisions.md) | Architecture Decisions (ADRs) | ✅ Active | Full ADR text. See also [ADR index](../project/adr-index.md) for a quick-scan register. |
| 10 | Quality Requirements | ⬜ Pending | Quality scenarios for the goals in §1 |
| [11](11-risks-debt.md) | Risks and Technical Debt | ✅ Active | Known issues we accepted to ship |
| [12](12-glossary.md) | Glossary | ✅ Done | Thai script, libass, ASS, GPOS, CPS — domain terms |

Sections are written when they become relevant — not pre-filled with placeholders.

---

## ADR Summary

Full text in [§9 — Architecture Decisions](09-decisions.md). Quick-scan register in [ADR index](../project/adr-index.md).

| ADR | Title | Status |
|---|---|---|
| [001](decisions/ADR-001-local-faster-whisper.md) | Local faster-whisper large-v3 for transcription | ✅ Accepted |
| [002](decisions/ADR-002-claude-p-subprocess.md) | `claude -p` subprocess for LLM passes | ✅ Accepted |
| [003](decisions/ADR-003-libass-thai-rendering.md) | libass + .ass for Thai subtitle rendering | ✅ Accepted |
| [004](decisions/ADR-004-pythainlp-newmm-wrapping.md) | PyThaiNLP newmm for word-aware line wrapping | ✅ Accepted |
| [005](decisions/ADR-005-claude-cleanup-pass.md) | Claude transcript cleanup pass with rules+memory | ✅ Accepted |
| [006](decisions/ADR-006-reading-rate-timing.md) | Reading-rate uniform pacing (Option D) | ✅ Accepted |
| [007](decisions/ADR-007-whisper-word-anchoring.md) | Per-line Whisper-word start-time anchoring (Option E) | ✅ Accepted |
| [008](decisions/ADR-008-overlay-only-default-mode.md) | overlay_only as default pipeline mode | ✅ Accepted |
| [009](decisions/ADR-009-ibm-plex-sans-thai-font.md) | IBM Plex Sans Thai for subtitle rendering | ✅ Accepted |
