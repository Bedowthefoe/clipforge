# Learnings

**Purpose:** Reusable insights worth carrying across the project. One-line headline + short context. NOT a session log — for that see [`../sessions/`](../sessions/).
**Last Updated:** 2026-06-09

---

## Thai script + rendering

- **Thai has no inter-word spaces.** libass cannot semantically wrap Thai without a tokenizer. Industry-standard fix: PyThaiNLP newmm tokenize + insert `\N` (ASS hard line break). `wrap_unicode` (libunibreak) wraps at arbitrary graphemes — semantically wrong for subtitles. → [ADR-004](../arc42/decisions/ADR-004-pythainlp-newmm-wrapping.md)

- **Thai needs HarfBuzz shaping; FreeType alone produces empty boxes.** Banned: `drawtext` filter for Thai. Required: libass + `.ass` file. → [ADR-003](../arc42/decisions/ADR-003-libass-thai-rendering.md)

- **Thai font quality varies a lot in GPOS depth.** Diagnostic: `len(gpos.LookupList.Lookup)`. Prompt has 5 lookups → tone marks collide. IBM Plex Sans Thai has 15 → clean stacking. Heuristic: **≥10 GPOS lookups + `mark` + `mkmk` features** required for good Thai rendering at scale. → [ADR-009](../arc42/decisions/ADR-009-ibm-plex-sans-thai-font.md)

- **Modern Thai design is "loopless".** Traditional fonts (Sarabun, Noto Sans Thai Looped) keep the head-loops (หัวกลม) on consonants like ก, ถ, ส. Modern fonts (IBM Plex Sans Thai, Prompt, Anuphan) drop them. Creator audiences in 2026 prefer loopless.

- **Sara Am can be decomposed by Whisper.** Whisper sometimes outputs `ทํา` (Nikhahit + Sara Aa) instead of the precomposed `ทำ`. Deterministic fix: `text.replace("ํา", "ำ")` BEFORE any other processing. We do this in `cleanup.py` step 1.

- **Python `len()` over-counts Thai visual width.** Combining marks (vowels, tone marks) inflate `len()` without consuming horizontal space. The `char_width_ratio` to use in pixel estimates is **~0.32 for IBM Plex Thai Bold**, not the 0.7 you'd expect for Latin. Tune empirically per font.

## Whisper (faster-whisper)

- **Whisper extends the last token of a segment through silence.** A pythainlp word that's the last word of a "speech burst" gets a multi-second `end` time, regardless of actual spoken duration. Implication: **never trust Whisper word END times** for sub end timing. START times are reliable. → [ADR-006](../arc42/decisions/ADR-006-reading-rate-timing.md) + [ADR-007](../arc42/decisions/ADR-007-whisper-word-anchoring.md)

- **Whisper "words" for Thai are sub-syllabic.** Each entry in `segment.words` is a single character or small grapheme cluster, not a full word. Treat them as anchoring units, not as words.

- **Whisper Thai CER is ~5-10% on fast colloquial speech.** Common error classes: tone marks, sound-alike consonants, English loan word spelling, occasional content-disambiguation errors. → [ADR-005](../arc42/decisions/ADR-005-claude-cleanup-pass.md)

## Pipeline + AI design

- **Surgical substring replace > full-segment overwrite** when applying LLM-suggested corrections to a transcript. Earlier bug: `segments[idx]["text"] = corrected_substring` overwrote a 67-char segment with the 19-char correction, breaking everything downstream. → [debt 001](../debt/001-cleanup-bug-fixed.md)

- **Always cache intermediates with timestamped filenames.** No overwrites. Every render writes `{base}_{YYYYMMDD_HHMMSS}.mp4` + `_analysis.json`. Iteration loop = `--transcript cached.json` to skip Whisper.

- **Industry subtitle timing standards are well-defined.** Netflix: min 0.83s (5/6 of a second), max 7s long-form / 2.5s short-form. Reading speed: 17-20 CPS Latin (~30 Thai chars/sec). Inter-event gap: 2 frames @ 25fps (0.08s) to prevent flicker. **Use these as defaults; tune per content type.**

- **For Whisper Thai, target_cps should be ≈ speaker pace, not max-readable speed.** Default 18 chars/sec for typical creator fitness content. Latin equivalent is ~10 CPS — the inflation comes from Thai diacritics in `len()`.

- **The "rules + memory" agent pattern works well for proofreading tasks.** Static guidelines + growable lessons file + per-job context hint. Operator confirms corrections → memory grows → future runs benefit. → [ADR-005](../arc42/decisions/ADR-005-claude-cleanup-pass.md)

## Operating environment

- **`claude -p` works as a subprocess and bills against Pro plan Agent SDK credit.** No API key needed. Always pass `--output-format json` for stable parsing. Add regex fallback `re.search(r'\{.*\}', ...)` for occasional trailing text.

- **`pip install --break-system-packages` is the install pattern on this host.** No venv adopted. Watch out for: pythainlp, fonttools, faster-whisper, python-ass, pyyaml.

- **fontconfig is the right way to register custom fonts.** Drop `.ttf` in `~/.fonts/<family>/`, run `fc-cache -f`. libass + ffmpeg's `subtitles` filter pick them up automatically.
