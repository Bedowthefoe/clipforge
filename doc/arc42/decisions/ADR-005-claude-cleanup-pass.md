# ADR-005 — Claude transcript cleanup pass with rules + memory

**Status:** Accepted
**Date:** 2026-06-03
**Deciders:** Operator

---

## Context

Whisper large-v3 produces ~5–10% character-error-rate on fast colloquial Thai fitness speech. Common error patterns:
- Wrong tone marks (`เนี้ย` vs `เนี่ย`, `ยอด` vs `ย่อ`)
- Sound-alike consonant substitutions (`บ่ายเจ็บ` should be `ปวดเจ็บ`)
- English loan word mis-spellings (`ฟังชันอล` should be `ฟังก์ชันนัล`)
- Sara Am decomposition (`ทํา` should be `ทำ`)
- Sometimes whole-word confusions (`เสือ` "tiger" should be `เสื่อ` "mat" — disambiguated by fitness context)

Options:

| Option | Pros | Cons |
|---|---|---|
| Live with errors | Cheapest | Subtitles have visible mistakes |
| Thai spell-check (libthai-data dictionary) | Local, fast | Rule-based; doesn't disambiguate by context |
| Larger Whisper / different STT | Possible accuracy gain | Significant cost or compute increase |
| Claude post-edit pass with fitness context | Catches context-dependent errors (เสือ→เสื่อ) | Per-run cost (~$0.01 Pro plan); requires curated guidelines |

## Decision

Add a **Claude proofreading pass** as Stage 2 of the pipeline. The agent reads:
1. **`clipforge/cleanup_rules.md`** — static guidelines (immutable from run-to-run)
2. **`clipforge/cleanup_memory.md`** — lessons learned (grows when operator confirms corrections)
3. **`cfg.ai.cleanup_topic_hint`** — domain context for THIS video (e.g. "Thai fitness instructional video")
4. **The numbered Whisper transcript**

Returns `{corrections: [{index, original, corrected, confidence, reason}], notes}`. Apply via **surgical substring replace** (NOT full-segment overwrite — see [debt 001](../../debt/001-cleanup-bug-fixed.md)). Gate on `cfg.ai.cleanup_min_confidence` (high/medium/low).

```python
# Step 1: deterministic Sara Am normalisation (ทํา → ทำ)
# Step 2: claude -p prompt assembled from rules + memory + topic + transcript
# Step 3: substring replace per correction, gated by confidence threshold
```

## Why

- **Whisper alone is not good enough for Thai fitness speech.** Confirmed in real test on `new-test-RAW-0601.mp4`: cleanup fixed 5 high-confidence errors including the semantically critical `เสือ→เสื่อ` (tiger → mat).
- **Rules-as-prompt-input is auditable and tunable** — operator can edit `cleanup_rules.md` and immediately change agent behaviour.
- **Memory file makes the agent learn** — once an operator confirms a correction is right, that pattern moves from `corrections[]` log to `cleanup_memory.md`, ensuring future runs apply it deterministically.
- **Confidence threshold gives a safety valve** — `min_confidence: high` for production, `medium` for current development.
- **Pro plan covers the cost** (~$0.005 per call typical).

## Consequences

- Adds ~60s to pipeline runtime per video (one `claude -p` call).
- Audit JSON sidecar records all corrections + `apply_method` per correction (substring-replace, sara-am-normalised, skipped-OOB, etc.). Operator can review and curate `cleanup_memory.md` post-hoc.
- Initial implementation had a critical bug: `out_segments[idx]["text"] = corrected` overwrote full segments with just the corrected substring, causing massive timing artifacts. Fixed by switching to substring-replace. Bug + fix documented in [debt 001](../../debt/001-cleanup-bug-fixed.md).
- Cleanup is opt-out via `cfg.ai.cleanup_enabled: false` for measurement runs.

## Revisit triggers

- If we get a Thai-fine-tuned STT model with materially lower CER — measure if cleanup is still worth its cost.
- If the rules file grows past ~10KB — consider splitting it into rule categories (tone marks, loan words, etc.) or moving older lessons to memory.
- If Claude API pricing or Pro plan economics change — re-evaluate per-call cost.
