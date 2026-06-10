# ADR-007 — Per-line Whisper-word start-time anchoring (Option E)

**Status:** Accepted
**Date:** 2026-06-07
**Deciders:** Operator

---

## Context

After ADR-006, Option D produces Netflix-compliant durations and predictable pacing — but **anchors only at segment boundaries** (every 2-5 seconds). Within a segment, lines flow at fixed reading-rate cadence from `seg_start`, ignoring whether the host accelerates or pauses mid-segment. Result: subs can drift from actual speech by up to ~1 second within a segment.

The operator observed this: "we still have issues with the text aligning to the user's voice; can we review the alignment points and make them more often?"

Options to add more alignment points:

| Option | Idea |
|---|---|
| Per-line Whisper-word START anchoring | Use Whisper word `start` (not `end`) as anchor for each line. End comes from clamped reading-rate. |
| Audio silence detection | Run FFmpeg silencedetect, identify speech bursts, anchor each line to its burst. |
| Word-level forced alignment | Use Montreal Forced Aligner or similar — heavy dep. |

## Decision

Add **Option E: per-line Whisper-word start-time anchoring** on top of Option D. Each subtitle line's start time is anchored to the Whisper word containing its first character.

```python
# Build (cumulative_char_offset → word.start) anchor table from whisper_words.
# For each line, look up the anchor at its first-char offset.
if anchor > cumulative_start:
    gap = min(anchor - cumulative_start, max_drift_correction)
    line_start = cumulative_start + gap   # honor host pause
else:
    line_start = cumulative_start          # speech faster than CPS; stay cumulative
```

New config:
```yaml
subtitles:
  anchor_to_whisper_words: true
  max_drift_correction: 1.0   # cap seconds of silence inserted at an anchor
```

## Why

- **Whisper word START times are accurate** — only `end` times are silence-biased.
- **Anchor points multiply from ~15 per video (per segment) to ~42 per video (per line)** — much tighter sync.
- **Drift cap honors host pauses up to 1 second** — beyond that we accept the pause is too long to fill, sub goes silent, host's silence is honored.
- **Falls back gracefully** when Whisper word array isn't reliable (e.g. cleanup pass shifted text length by >10%).

## Consequences

- v17 results vs v15:
  - 42 events, durations still in 0.83-1.28s range (Netflix compliant)
  - 1 detected real pause at 0.34s before "เห็นใครมีปัญหา..."
  - Several micro-anchor adjustments visible in 0.12-0.17s gap variations
- The anchoring only shifts START times — duration is still purely from `chars / target_cps`. So we don't get faster events even when the host speaks fast; we just get more accurate START alignment.
- Tunable via `max_drift_correction`: raise to honor longer pauses; lower to prevent any anchored gaps.

## Edge cases

- **Cleanup changes text length** — if `abs(whisper_chars - segment_chars) > 10%`, we skip anchoring for that segment and fall back to pure cumulative timing.
- **Whisper words missing** — `whisper_words` empty → anchor lookup returns `None` → cumulative timing only.
- **Anchor in the past** — if Whisper word start is earlier than `cumulative_start` (host speaks faster than CPS), we stay on cumulative. We never push events earlier than the previous event's end + inter_gap.

## Revisit triggers

- If `max_drift_correction: 1.0` consistently produces too-short or too-long honored gaps — make it content-dependent.
- If a future ADR adds silence detection (Option C), anchoring may become redundant. Re-evaluate.
- If we move to a word-level Thai aligner — anchoring could go from per-PyThaiNLP-word to per-syllable.
