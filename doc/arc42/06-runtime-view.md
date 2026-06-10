# 6. Runtime View

**Purpose:** What happens when a video is processed, end to end.
**Last Updated:** 2026-06-09

---

## Scenario 1 — Cold run, `overlay_only` mode

Operator: `python main.py test/raw.mp4`

```
┌─────────────────────────────────────────────────────────────────────────┐
│  STAGE          DURATION (44s video, CPU)        ARTIFACT                │
├─────────────────────────────────────────────────────────────────────────┤
│  1. Transcribe    ~10 min                       transcript.json          │
│       • extract 16kHz mono audio (~1s)                                   │
│       • faster-whisper large-v3 int8 (~9 min Whisper + ~1 min misc)      │
│       • annotate completeness flags                                      │
│       • pause-based resegmentation (15 → 16 segs typical)                │
│                                                                          │
│  2. Cleanup       ~1 min (claude -p)            corrected segments       │
│       • Sara Am normalisation (sync, deterministic)                      │
│       • Prompt assembled: rules.md + memory.md + topic + transcript      │
│       • claude -p call (~60s response)                                   │
│       • Surgical substring replace per correction, gated by confidence   │
│       • Audit log: applied/method/confidence per correction              │
│                                                                          │
│  3. Highlight     ~30s (claude -p)              {keyword_popups: [...]}  │
│       • Prompt: keyword_style + transcript                               │
│       • claude -p call (~25s response)                                   │
│       • Validate/clamp popup start times to video duration               │
│                                                                          │
│  4. Subtitle      <1s                           subs.ass                 │
│       • For each segment, split_into_timed_lines (Option D + E timing)   │
│       • reconcile_event_timing (no overlap, min duration)                │
│       • Emit .ass with Speech + KeywordPop styles                        │
│                                                                          │
│  5. Edit          ~1-2 min                      edited.mp4 + analysis    │
│       • _baseline_crop_filter: crop to 1/1.48 then scale (matches refs)  │
│       • libass burns subs.ass via FFmpeg subtitles filter                │
│       • libx264 CRF 23 preset=fast, AAC 192k                             │
│       • Probe output, log size + duration                                │
└─────────────────────────────────────────────────────────────────────────┘
                                                                          
   TOTAL    ~12-13 minutes
```

---

## Scenario 2 — Warm re-run with cached transcript

`python main.py test/raw.mp4 --transcript test/analysis/raw_0601_transcript.json`

Skips Stage 1's Whisper invocation; loads JSON, re-runs post-processing pipeline. Useful for iterating on cleanup rules, popup prompts, or subtitle style without paying the 10-min Whisper cost.

```
   STAGE          DURATION (44s video)
   1. Transcribe (cached)   <1s
   2. Cleanup               ~60s (claude -p)
   3. Highlight             ~25s (claude -p)
   4. Subtitle              <1s
   5. Edit                  ~90s
   
   TOTAL    ~3-4 minutes
```

This is the iteration loop we used through SESSION-04 (v1 → v17).

---

## Timing Sequence — Subtitle Event Generation (Stage 4 detail)

Per segment (`split_into_timed_lines`):

```
1. text = segment text (post-cleanup)
   whisper_words = segment word array (Whisper sub-syllabic tokens)
   
2. tokens = pythainlp.word_tokenize(text, engine="newmm", keep_whitespace=True)

3. Greedy-pack tokens into lines ≤ max_chars_per_line
   line_texts = ["...", "...", ...]

4. For each line:
      n_chars = len(line.replace(" ", ""))
      natural_dur = n_chars / target_cps
      duration = clamp(natural_dur, min_event_duration, max_event_duration)
   
5. Build per-line char offset (cumulative within whitespace-stripped text)

6. Build anchor_table from whisper_words: [(cum_char_offset, word.start), ...]
   (Only if `len(whisper_chars) ≈ len(segment_chars)` within 10% tolerance)

7. For each line (in order):
      cumulative_start = max(seg_start, prev.end + inter_gap)   for non-first
                       = seg_start - lead_time                  for first
      anchor = lookup_anchor(line_char_offset)
      
      if anchor > cumulative_start:
          gap = min(anchor - cumulative_start, max_drift_correction)
          line.start = cumulative_start + gap   # honor host pause
      else:
          line.start = cumulative_start          # no pause; continue cursor
      
      line.end = line.start + duration
```

Then `reconcile_event_timing` across all segments:
- If `events[i].start < events[i-1].end + inter_gap`: truncate prev event end
- If truncation would make prev shorter than min_event_duration: push current later instead

---

## Failure Modes (Observed)

| Where | Symptom | Cause | Mitigation |
|---|---|---|---|
| Stage 1 | Whisper produces 5s segment that contains 1 syllable | Whisper extends final token through silence | Resegment at pauses; Option D/E timing don't trust Whisper end times |
| Stage 2 | Cleanup replaces full segment with correction substring | Earlier bug: `out_segments[idx]["text"] = corrected` | Fixed: surgical substring replace (see [debt 001](../debt/001-cleanup-bug-fixed.md)) |
| Stage 4 | One-syllable event held 4+ seconds | Used Whisper word end times | Fixed by Option D — duration purely from char count |
| Stage 4 | Multi-second event timing exceeds video | min_event_duration cumulative overshoot | Allow overshoot past seg_end; truncate at video end naturally |
| Stage 5 | Thai tone marks colliding with vowels | Prompt font GPOS underdefined | Switched to IBM Plex Sans Thai (15 lookups vs Prompt's 5) — ADR-009 |
| Stage 5 | Long subtitle line overflowed frame | Thai has no inter-word spaces → libass can't auto-wrap | PyThaiNLP newmm + `\N` line breaks — ADR-004 |
