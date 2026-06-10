# ADR-006 — Reading-rate uniform pacing (Option D)

**Status:** Accepted
**Date:** 2026-06-04
**Deciders:** Operator

---

## Context

Per-line subtitle event timing using Whisper's sub-syllabic word `start`/`end` timestamps produced wildly uneven durations:

| v13 actual distribution |
|---|
| min event: **0.12s** (subliminal flash, violates Netflix 0.83s floor) |
| max event: **4.44s** (one word "เสื่อ" held while host pauses) |
| median: 0.88s |

Root cause: Whisper extends the last token of a segment through silence. A pythainlp word that happens to be the last word of a "speech burst" gets a multi-second end time, regardless of how long it was actually spoken.

Options considered:

| Option | Idea |
|---|---|
| A. Pure proportional | Ignore Whisper word stamps. Distribute segment duration across lines proportional to char count. |
| B. Whisper + clamp | Keep current logic, clamp every event to [min, max]. |
| **C. Audio silence-detect re-segment** | Run FFmpeg silencedetect, ignore Whisper segment boundaries. |
| **D. Reading-rate uniform per segment** | For each segment: duration per line = `chars / target_cps`, then clamp. Cumulative start times. |

Industry standards research:

| Source | Min duration | Max duration | Reading speed |
|---|---|---|---|
| Netflix (adult) | 5/6 s (≈0.83s) | 7s | 17-20 CPS Latin |
| Netflix (kids) | 5/6 s | 7s | 13-17 CPS |
| BBC | ~1.0s | — | ~15 CPS (160-180 WPM) |
| TikTok / Reels short-form | 1-2s typical | ~2.5s | 15-20 CPS |

Plus: 2-frame inter-event gap required to prevent flicker (Netflix).

## Decision

Implement **Option D: reading-rate uniform pacing per segment**, with industry-aligned defaults:

```yaml
subtitles:
  target_cps: 18              # Thai chars/sec — matches typical speech rate
  min_event_duration: 0.83    # Netflix minimum
  max_event_duration: 2.5     # short-form ceiling
  inter_event_gap: 0.08       # ~2 frames @ 25fps
```

Algorithm in `split_into_timed_lines`:
```python
for each line in pythainlp-packed lines:
    n_chars = len(line.replace(" ", ""))
    natural_dur = n_chars / target_cps
    duration = clamp(natural_dur, min_event_duration, max_event_duration)
cumulative starts from seg_start, separated by inter_event_gap
```

Across segments, `reconcile_event_timing` enforces no-overlap + min duration.

## Why

- **Whisper word end times are silence-biased** — using them produces 4-second events for single syllables. Option D ignores them.
- **Predictable, even pacing beats precise word-sync** for sound-off short-form viewing (TikTok/Reels best practice).
- **Each line gets a duration proportional to its text length** — long lines (`น้ำหนักให้ถูกต้องสำคัญ`, 22 chars) get more time than short ones (`มาก ๆ`, 5 chars).
- **Floors and ceilings are universal best practice** — Netflix 0.83s min prevents flicker; 2.5s max prevents hold-on-one-word.

## Consequences

- **No flicker** — every event ≥ 0.83s.
- **No long holds** — every event ≤ 2.5s.
- **Subs don't precisely lip-sync to specific words** — they follow the segment-level rhythm. This is acceptable for sound-off viewing where readability matters more than exact sync.
- We added Option E on top (ADR-007) to multiply alignment points from per-segment to per-line.
- Tuning `target_cps` is content-dependent. Fast speakers need higher CPS; slow speakers lower. Default 18 matches the test creator's pace.

## Initial bug + fix

First v14 run had all events at 0.83s (every line hit the minimum floor) because target_cps was 30 (Latin equiv). Switched to 18 (Thai-matched) and bumped `max_chars_per_line` from 17 to ~23 by lowering `char_width_ratio` to 0.32 (matched IBM Plex Thai glyphs). Result: durations 0.83-1.28s, span exactly matches video duration.

## Revisit triggers

- If we add content types with different reading speeds (e.g. fast-talking comedy creators) — make `target_cps` per-job in `config.yaml`.
- If a real silence-detection pass (Option C) becomes important for sync — would add an FFmpeg silencedetect pre-pass.
