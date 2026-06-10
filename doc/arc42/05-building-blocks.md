# 5. Building Block View

**Purpose:** Static decomposition — what's in the codebase and what each piece is responsible for.
**Last Updated:** 2026-06-09

---

## Level 1 — Top Level

```
clipforge/
├── main.py                  ← orchestrator (CLI entry point + stage dispatch)
├── config.yaml              ← all tunable parameters (operator-edited)
└── clipforge/               ← pipeline modules
    ├── config.py            ← dataclasses + YAML loader
    ├── transcribe.py        ← Whisper + pause-based resegmentation
    ├── cleanup.py           ← Claude transcript proofreader
    ├── cleanup_rules.md     ← static guidelines fed into cleanup prompt
    ├── cleanup_memory.md    ← confirmed corrections, grows over runs
    ├── highlight.py         ← Claude keyword popup selector
    ├── subtitle.py          ← .ass generation (two styles)
    ├── textwrap_th.py       ← PyThaiNLP wrap + Option D/E timing
    └── editor.py            ← FFmpeg pipeline
```

---

## Module Responsibilities

### `main.py` — orchestrator

- Parses CLI args (`input.mp4`, `--config`, `--transcript`, `--output`)
- Loads `config.yaml` via `config.py`
- Sequences the five stages in order
- Saves audit-trail JSON next to the output mp4
- Uses timestamped output paths to preserve audit history (no overwrites)

### `clipforge/config.py` — typed config

- Dataclasses per section: `OutputConfig`, `FramingConfig`, `SubtitleConfig`, `KeywordConfig`, `ZoomConfig`, `CuttingConfig`, `AIConfig`, `ClipforgeConfig`
- `load(path)` returns a fully-typed `ClipforgeConfig`
- Unknown keys in YAML are silently ignored (forward-compatible)
- Defaults baked in so missing keys never crash

### `clipforge/transcribe.py` — STT + resegmentation

- `run(...)` extracts audio (16kHz mono WAV), invokes `faster_whisper.WhisperModel("large-v3", "cpu", "int8")`
- Returns `[{start, end, text, words, complete}]` per segment
- Post-processing:
  - `_annotate_completeness(...)` — flags Thai sentence-opener fragments (`ถ้า`, `แต่`, ...) and dangling endings
  - `_filter_and_reindex(...)` — `highlight_reel` mode only: drop incomplete segments
  - `_resegment_at_pauses(...)` — `overlay_only` mode only: split long segments at word-level pauses ≥ 0.4s OR token-held-for-silence ≥ 1.0s
- Supports `--transcript existing.json` to skip the ~10-min Whisper step

### `clipforge/cleanup.py` — Thai STT proofreader

- `clean_transcript(segments, cfg, topic_hint, min_confidence)` → corrected segments + correction log
- Step 1 (deterministic): Sara Am normalisation (`ทํา → ทำ`)
- Step 2 (Claude): builds prompt from `cleanup_rules.md` + `cleanup_memory.md` + topic + numbered transcript; expects `{corrections: [{index, original, corrected, confidence, reason}], notes}`
- Applies corrections via **surgical substring replace** (not full-segment overwrite — see ADR fix log in SESSION-04 / debt 001)
- Confidence-gated: only applies corrections ≥ `min_confidence` threshold
- Logs `apply_method` per correction for audit (substring-replace, sara-am-normalised, skipped-OOB, skipped-not-found, etc.)

### `clipforge/highlight.py` — popup selector

- `run(transcript, video_duration, cfg)` dispatches on `cfg.mode`
- `run_overlay(...)` — calls `claude -p` with `keyword_style` instruction + numbered transcript; expects `{keyword_popups: [{text, start, duration}], edit_note}`
- `run_highlight_reel(...)` — legacy path returning `selected[]` / `zoom_moments[]` / `keywords[]`
- Validates and clamps timestamps to within video duration

### `clipforge/subtitle.py` — .ass generation

- `make_overlay_ass(segments, popups, video_path, cfg, out_path)` — single .ass file with TWO styles:
  - `Speech` — white fill + drop-shadow, bottom, no outline (matches target font screenshot)
  - `KeywordPop` — white fill + pink (`#FF1493`) outline, top, italic, larger
- Each speech segment is split into N single-line events via `split_into_timed_lines`
- Cross-segment cleanup via `reconcile_event_timing` (prevents overlap, preserves min duration)
- Font resolved by libass via fontconfig (currently `IBM Plex Sans Thai`)

### `clipforge/textwrap_th.py` — Thai wrap + timing core

- `wrap_thai(text, max_chars_per_line, max_lines)` — PyThaiNLP newmm tokenize + greedy pack + `\N` insert
- `auto_max_chars(font_size, frame_width, margin_horizontal, char_width_ratio)` — chars/line estimator (defaults: 0.32 ratio for IBM Plex Thai)
- `split_into_timed_lines(text, whisper_words, seg_start, seg_end, max_chars_per_line, target_cps, min_dur, max_dur, inter_gap, anchor_to_whisper_words, max_drift_correction)`:
  1. Pythainlp tokenize + pack into lines ≤ max_chars
  2. Per-line duration = clamp(chars / target_cps, min, max)
  3. Per-line start = anchor to Whisper-word containing first char (if enabled)
  4. Honor anchored pauses up to max_drift_correction; otherwise stay on cumulative cursor
- `reconcile_event_timing(events, inter_gap, min_dur)` — final pass: no overlaps, respect inter_event_gap

### `clipforge/editor.py` — FFmpeg pipeline

- `run(video, transcript, analysis, cfg, tmp_dir, output)` dispatches on `cfg.mode`
- `run_overlay_only(...)` — single FFmpeg pass:
  1. `_baseline_crop_filter(...)` — crop to `1/baseline_zoom` of frame centered at `(crop_center_x, crop_center_y)`, then scale back to full res. Matches client reference's tighter framing (~55% subject vertical fill vs raw's ~37%).
  2. Subtitles filter burns the `.ass` (libass + fontconfig)
- `run_highlight_reel(...)` — legacy multi-pass: cut → concat → final overlay
- Output is `libx264 + AAC`, CRF + preset from config

---

## Module Dependency Graph

```
            main.py
              │
              ├── config.py
              │
              ├── transcribe.py ──► (faster-whisper)
              │
              ├── cleanup.py    ──► (claude -p)
              │       │
              │       └── reads cleanup_rules.md + cleanup_memory.md
              │
              ├── highlight.py  ──► (claude -p)
              │
              └── editor.py
                      │
                      └── subtitle.py
                              │
                              └── textwrap_th.py ──► (pythainlp)
```

No cycles. `main.py` is the only orchestrator. Modules don't call each other directly — they communicate via dataclass payloads passed by `main.py`.

---

## External Code We Depend On

| Library | Purpose | Why this one |
|---|---|---|
| `faster_whisper` | Local Whisper inference | int8 quantization → CPU-feasible |
| `pythainlp` | Thai word tokenization | de facto standard; newmm engine is dict-based + fast |
| `ass` (python-ass) | .ass file generation | Clean API for libass subtitle format |
| `pyyaml` | Config loading | Standard |
| `fonttools` | Inspecting font GPOS tables (dev only) | Used to diagnose font shaping quality |
