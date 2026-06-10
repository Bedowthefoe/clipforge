# Open Questions

**Purpose:** Design questions not yet resolved. When a question gets resolved, move it to the appropriate ADR + delete from this file.
**Last Updated:** 2026-06-09

---

## Currently open

### Q-001 — How should `cleanup_memory.md` structure correction entries?

**Context:** F-001 — cleanup memory promotion workflow.
**Why it matters:** Determines whether confirmed corrections can be applied deterministically vs only fed to Claude as guidance.
**Options:**
- A. Free text (current empty placeholder)
- B. YAML/JSON code blocks with `{original, corrected, context_hint}` triples
- C. Structured markdown table

**Need:** Operator's preference + first batch of confirmed corrections to validate format.

### Q-002 — Should cleanup memory be applied deterministically before the Claude call?

**Context:** F-001.
**Why it matters:** Determinism + speed vs flexibility. If we apply known corrections deterministically, Claude focuses on new errors. But Claude may flag context where a known correction shouldn't apply.
**Options:**
- A. Apply all confirmed-correct entries verbatim, then Claude reviews unchanged segments
- B. Show Claude both original + memory entries, let it decide
- C. Mix: high-confidence entries auto-apply, low-confidence go through Claude

### Q-003 — `target_cps: 18` default — is this right for all creators?

**Context:** [ADR-006](../arc42/decisions/ADR-006-reading-rate-timing.md).
**Why it matters:** Different creators speak at different rates. 18 was tuned to one test video.
**Resolution path:** Measure CPS across 3-5 creator videos; if variance > ±3, make this per-job (config or computed from transcript).

### Q-004 — Should subtitles lead speech by 50-100ms?

**Context:** TikTok/Reels best practice — "show subs slightly before speech so viewer's eye is ready" (relevant for sound-off viewing).
**Why it matters:** Currently `lead_time: 0`. A 100ms lead may noticeably improve UX.
**Resolution path:** A/B test with creator on real content. If preferred, set `lead_time: 0.1` as default.

### Q-005 — Should we add a `creator_profile` concept?

**Context:** F-002 — per-creator config profiles.
**Why it matters:** Phase 2 hardening assumes we'll handle multiple creators. Profile structure is open.
**Options:**
- A. Profile dir per creator (`profiles/creator-a/config.yaml`)
- B. Single config with `creator: name` flag + profile section in YAML
- C. Defer until we actually have a 2nd creator
**Lean:** C — premature otherwise.

### Q-006 — `max_drift_correction: 1.0` — is 1 second the right cap?

**Context:** [ADR-007](../arc42/decisions/ADR-007-whisper-word-anchoring.md).
**Why it matters:** Determines how long a "honored pause" can be in subs before we accept the sub goes silent.
**Resolution path:** Watch v17 output; if a 1.5s pause feels right and we cap it at 1.0s, raise to 1.5. If 1.0 introduces over-long silent gaps, lower.

---

## Resolved (moved to ADR)

| Q | Resolution | When |
|---|---|---|
| Should subtitle font be Tahoma? | Sarabun, then Prompt, then IBM Plex Sans Thai (loopless modern, 15 GPOS lookups) | 2026-06-07 → [ADR-009](../arc42/decisions/ADR-009-ibm-plex-sans-thai-font.md) |
| Should we trust Whisper word END times for sub end timing? | No — silence-biased; use reading-rate clamp instead | 2026-06-04 → [ADR-006](../arc42/decisions/ADR-006-reading-rate-timing.md) |
| Should default mode be overlay_only or highlight_reel? | overlay_only — matches client target reference | 2026-06-01 → [ADR-008](../arc42/decisions/ADR-008-overlay-only-default-mode.md) |
| What library for Thai word tokenization? | PyThaiNLP newmm — industry standard, dict-based, fast | 2026-06-03 → [ADR-004](../arc42/decisions/ADR-004-pythainlp-newmm-wrapping.md) |
| How to bill LLM passes? | `claude -p` subprocess against Pro plan Agent SDK credit | 2026-05-24 → [ADR-002](../arc42/decisions/ADR-002-claude-p-subprocess.md) |
