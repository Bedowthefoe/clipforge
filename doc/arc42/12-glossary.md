# 12. Glossary

**Purpose:** Quick reference for domain terms — Thai script, libass/ASS, font internals, project-specific concepts.
**Last Updated:** 2026-06-09

---

## Thai script

| Term | Meaning |
|---|---|
| **Consonant** | Base character (ก, ข, ค, ส, …). The "spine" letters that hold vowels and tones. |
| **Above-base vowel** | Combining mark above a consonant (◌ิ ◌ี ◌ึ ◌ื). Stacks visually on the consonant. |
| **Below-base vowel** | Combining mark below a consonant (◌ุ ◌ู). |
| **Tone mark** | Combining mark above the vowel (◌่ mai ek, ◌้ mai tho, ◌๊ mai tri, ◌๋ mai chattawa). Stacks above the above-base vowel — requires mark-to-mark anchoring. |
| **Mai ek (◌่)** | "First" tone mark. The low/falling tone in modern usage. |
| **Mai tho (◌้)** | "Second" tone mark. The high/falling tone in modern usage. |
| **Sara Am (ำ)** | A precomposed vowel sound "am" — can be decomposed as Nikhahit ◌ํ + Sara Aa า. Whisper sometimes emits the decomposed form; we normalise it. |
| **Loop / Head-loop (หัวกลม)** | The small circular shape at the top of traditional Thai consonants (ก, ถ, ส, …). Modern "loopless" Thai fonts omit them. |
| **Looped vs Loopless** | Style families. Traditional/legal/print → looped (Sarabun, Noto Sans Thai). Modern/digital → loopless (IBM Plex Sans Thai, Prompt, Anuphan). |
| **Filler particle** | Function words like ครับ, นะครับ, ค่ะ, น่ะ, เลย. Part of natural speech; we preserve them. |
| **PyThaiNLP** | The standard Python library for Thai NLP. We use the `newmm` engine (dict-based maximal matching) for word tokenization. |

## ASS subtitle format + libass

| Term | Meaning |
|---|---|
| **`.ass`** | Advanced SubStation Alpha — subtitle format originating from Aegisub. Supports styled events, multi-style files, fades, positioning. |
| **`Dialogue`** | One subtitle event in an `.ass` file — has start time, end time, style name, text. |
| **`Style`** | Reusable style definition in an `.ass` file — font, size, primary color, outline color, back color (shadow), alignment, margins. |
| **`\N`** | ASS escape for hard line break inside a `Dialogue` text. We insert these via `wrap_thai()` after PyThaiNLP tokenization. |
| **libass** | C library that renders `.ass` subtitle files. Used internally by FFmpeg's `subtitles` filter. Calls HarfBuzz for complex-script shaping. |
| **HarfBuzz** | The complex-text-shaping library. Handles Thai mark stacking, Arabic, Devanagari, etc. — anything that needs OpenType GPOS/GSUB tables. |
| **`subtitles` filter (FFmpeg)** | The filter we use to burn `.ass` into video. `-vf "subtitles=path.ass:fontsdir=/usr/share/fonts"`. |
| **`drawtext` filter (FFmpeg)** | A simpler text-overlay filter — banned for Thai because it doesn't use HarfBuzz. |
| **`wrap_unicode`** | Optional libass filter param that uses libunibreak for Unicode-line-break-aware wrapping. Available in our libass 0.17+, but breaks Thai anywhere — we don't use it. |

## Font internals

| Term | Meaning |
|---|---|
| **GPOS** | OpenType "Glyph Positioning" table inside a font. Defines mark anchors, kerning, etc. Essential for Thai mark stacking. |
| **GSUB** | OpenType "Glyph Substitution" table. Less critical for Thai. |
| **`mark` feature** | GPOS feature that positions a combining mark relative to a base glyph. Required for vowel-above-consonant placement. |
| **`mkmk` feature** | GPOS feature that positions a combining mark relative to another combining mark. Required for tone-mark-above-vowel placement. |
| **GPOS lookups** | Atomic positioning rules inside the GPOS table. More lookups → more granular positioning. We use this as a quality proxy: ≥10 lookups indicates good Thai support. |
| **fontconfig** | Linux font-resolution library. libass uses it to find fonts by name. `~/.fonts/` + `~/.local/share/fonts/` + `/usr/share/fonts/` are scanned. |

## Subtitle timing

| Term | Meaning |
|---|---|
| **CPS** | Characters per second — reading speed unit. Netflix uses 17-20 for Latin. Thai equivalent is ~30 chars/sec because diacritics inflate `len()`. We use 18 because it matches actual Thai speech rates better. |
| **Inter-event gap** | Required pause between consecutive subtitle events. Netflix: 2 frames @ 24fps = 0.083s. We use 0.08s. |
| **Reading-rate uniform pacing (Option D)** | Each subtitle event's duration = `clamp(chars / target_cps, min, max)`. Ignores Whisper word end times (silence-biased). → [ADR-006](decisions/ADR-006-reading-rate-timing.md) |
| **Per-line anchoring (Option E)** | Each subtitle line's start time is anchored to the Whisper word that contains its first character. Duration is still reading-rate. → [ADR-007](decisions/ADR-007-whisper-word-anchoring.md) |
| **`max_drift_correction`** | Cap on how long an honored pause can be. Default 1.0s — beyond that, accept that no sub is shown. |
| **Lead time** | Seconds to show a subtitle BEFORE its speech actually starts. TikTok best practice for sound-off viewing. We default to 0 (aligned). |

## Project-specific

| Term | Meaning |
|---|---|
| **overlay_only** | The default pipeline mode — keep full video, overlay subs + popups. |
| **highlight_reel** | Legacy mode — cut speech segments to a target duration, glue back together. |
| **Cleanup pass** | Stage 2 of the pipeline. Claude reads the Whisper transcript + rules + memory + topic, returns corrections. |
| **Baseline crop** | A static crop+scale applied to the entire video to match the target reference's tighter framing. Driven by `framing.baseline_zoom` and `framing.crop_center_y`. |
| **Keyword popup** | Pink-outlined Thai phrase at top of frame, 3 per video, ~2.5s each. Chosen by Claude during the Highlight stage. |
| **Speech subtitle** | White + drop-shadow Thai line at bottom of frame, one per pythainlp-packed line, Netflix-compliant timing. |
| **Resegmentation** | Pause-based splitting of long Whisper segments using word-level timestamps. Active in `overlay_only` mode only. |
