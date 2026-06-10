# Feature Pipeline

**Purpose:** Pre-ADR feature exploration. Each entry covers one feature: what it is, why we need it, open questions, proposed approach. When a feature is ready for an architectural decision, it graduates to an ADR in [arc42/09-decisions.md](../arc42/09-decisions.md).
**Last Updated:** 2026-06-09

---

## In design

### F-001 — Cleanup memory promotion workflow

**Status:** Active exploration
**Owner:** Operator + assistant

**What:**
After each render, the assistant proposes corrections in `analysis.json`. Operator reviews and confirms which are right. Confirmed corrections should be appended to `clipforge/cleanup_memory.md` so future runs apply them deterministically.

**Why:**
Right now `cleanup_memory.md` is empty. The same Whisper STT errors recur across the creator's videos (e.g. `ยอด→ย่อ`, `บ่ายเจ็บ→ปวดเจ็บ`). Each new render asks Claude to find them again — wasteful + non-deterministic per-call.

**Open questions:**
- Should promotion be CLI-driven (`python tools/confirm_cleanup.py --run YYYYMMDD_HHMMSS`)?
- Or in-session via a slash command?
- How do we structure entries in `cleanup_memory.md` for Claude to read? Key-value pairs? Free text?
- Should confirmed corrections also be applied **deterministically** by `cleanup.py` (before the Claude call), so cleanup catches new errors instead of re-finding old ones?

**Proposed approach:**
1. Add a CLI tool `tools/confirm_cleanup.py` that reads the latest `_analysis.json`, presents each correction with original/corrected/reason, prompts y/n/skip.
2. Confirmed entries get appended to `cleanup_memory.md` in a structured "## Confirmed corrections" section.
3. `cleanup.py` reads the memory file and applies known corrections as deterministic substring replaces BEFORE the Claude call, so Claude can focus on new errors.

**Graduates to ADR when:** operator approves the structured-memory format and the deterministic-pre-pass behaviour.

---

### F-002 — Per-creator config profiles

**Status:** Idea
**Owner:** TBD

**What:**
Different creators have different speech rates, framing reference styles, popup densities, body-part vocabulary. Currently `config.yaml` is single-tenant.

**Why:**
Phase 2 needs to handle multiple creators without per-creator hand-tuning every time.

**Open questions:**
- Naming convention: `config.creator-a.yaml`? Or a `profiles/` dir?
- Inheritance: should profiles inherit from a base, or be standalone?
- CLI flag to select profile: `--profile creator-a`?
- Does `cleanup_topic_hint` move to per-profile?
- Same for `keyword_style` instruction (different creators emphasize different cues)?

---

### F-003 — Audio silence detection (Option C from the timing menu)

**Status:** Deferred (Option D + E covered the immediate need)
**Owner:** TBD

**What:**
Run FFmpeg `silencedetect` filter on the audio before Whisper. Use detected silence boundaries (>= 0.3s pauses) to override Whisper segment boundaries.

**Why:**
ADR-007 (Whisper-word anchoring) achieves most of what silence-detection would, at much lower complexity. Defer until measured need.

**Open questions:**
- What silence threshold matches Thai speech rhythm? (default -30dB / 0.3s might cut too fine)
- Does silence detection improve sync measurably over Option E? — needs A/B test.
- Should this replace or complement the pause-based resegmenter in `transcribe.py`?

---

### F-004 — Snap pause cuts to PyThaiNLP word boundaries

**Status:** Idea (resolves debt 003)
**Owner:** TBD

**What:**
`_resegment_at_pauses` in `transcribe.py` splits at Whisper sub-syllabic boundaries. Sometimes that splits a PyThaiNLP word in half (e.g. `แถม` → `แ` + `ถม`). Cosmetic bug.

**Why:**
Visible as orphan single-character events at certain segment boundaries (event 21 in v17: " แ").

**Proposed approach:**
After choosing a pause-based split point in the Whisper word array, search forward/backward for the nearest PyThaiNLP word boundary in the segment text. Snap the split there. Reduces or eliminates orphan-character events.

**Graduates to ADR when:** approach validated on test data, no regressions in segment count or text fidelity.

---

### F-005 — In-subtitle word emphasis (kinetic typography)

**Status:** Idea (mentioned by operator earlier)
**Owner:** TBD

**What:**
TikTok-style: highlight specific words IN each subtitle line (color change, bold pop, size bump) when the speaker says them.

**Why:**
Adds visual energy on top of plain subs. Common in 2026 short-form creator content.

**Open questions:**
- Which words to emphasize? Claude pass? Configured keyword list? Speech-prosody driven?
- ASS supports inline color/size override via `{\c}{\fs}` tags — implementation overhead.
- Risks: too much emphasis = busy/distracting. Need a "max N emphasized words per line" cap.

**Defer until:** operator validates current pipeline output with a real audience.

---

## Recently graduated to ADR

| Feature → ADR | Date |
|---|---|
| Reading-rate uniform pacing → [ADR-006](../arc42/decisions/ADR-006-reading-rate-timing.md) | 2026-06-04 |
| Per-line Whisper anchoring → [ADR-007](../arc42/decisions/ADR-007-whisper-word-anchoring.md) | 2026-06-07 |
| IBM Plex font choice → [ADR-009](../arc42/decisions/ADR-009-ibm-plex-sans-thai-font.md) | 2026-06-07 |
