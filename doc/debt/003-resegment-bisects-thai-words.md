# Debt 003 — Pause-based resegment splits PyThaiNLP words

**Status:** 🟡 Live debt
**Severity:** Low — cosmetic, no semantic loss

---

## What it is

`clipforge/transcribe.py::_resegment_at_pauses` splits long Whisper segments at pause boundaries using Whisper's word-level timestamps. But Whisper "words" for Thai are **sub-syllabic** (single characters or grapheme clusters), so the split point doesn't always align with a PyThaiNLP word boundary.

Visible example (v15 transcript, event 21):
```
20  20.80  21.69   แถมพอวางเข่านี่ก็จะนิ่ม
21  21.77  22.60   กับเข่ามากมาก แ                ← single "แ" stranded
22  22.68  23.80   ถมพอวางเข่าก็จะ support       ← "ถม" stranded
```

The split happened between Whisper sub-syllabic tokens that together form `แถม`. PyThaiNLP would have grouped them as one word.

## Why it happens

`_resegment_at_pauses` walks the Whisper `words` array looking for gaps `>= pause_gap` (0.4s) or single tokens held `>= silent_token_dur` (1.0s). It splits the segment at those Whisper-word indices. When the split lands inside a PyThaiNLP word, that word gets bisected.

## Impact

- Visible orphan single-character subtitles at some boundaries
- ~1-3% of events in typical content
- No semantic data loss — text is preserved across the split, just shown awkwardly

## Why we're not fixing it now

- Cosmetic, not functional
- Phase 1's exit criteria didn't require it
- Fix has design questions (see F-004 in feature-pipeline.md):
  - Snap to nearest PyThaiNLP boundary forward, backward, or whichever is closer?
  - What if the nearest boundary is too far away (would extend the over-long segment)?

## How to fix (F-004 plan)

1. After choosing a Whisper-word-index split, look up the corresponding char offset in the segment text
2. Tokenize the segment with PyThaiNLP newmm
3. Find the nearest PyThaiNLP word boundary (by char offset) to the chosen split point
4. If the nearest boundary is within ±10 characters, snap the split there
5. Re-compute sub-segment text + timestamps (preserve original Whisper word arrays per sub-segment)
6. Test on `raw_0601_transcript.json` — verify orphan events disappear
