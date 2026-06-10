# Product Strategy Framework

**Purpose:** Define what clipforge ships — pipeline modes, target style anchors, content type assumptions. The architecture in [arc42/](../arc42/) defines HOW; this file defines WHAT.
**Last Updated:** 2026-06-09

---

## Product positioning

Clipforge is an **AI video editor for Thai fitness creators** that turns one raw take into a finished short-form clip without any manual editing or operator intervention.

**Not what it is:**
- Not a general-purpose editor
- Not a multi-language tool
- Not a real-time / live tool
- Not a UI / app — CLI-driven for the foreseeable future

---

## Pipeline modes (production strategies)

The pipeline has two named modes selected via `cfg.mode`. Pick by content type.

### `overlay_only` — DEFAULT

**Use when:** raw clip is <60s and already tells a coherent story (one demonstration take).

**Pipeline produces:**
- The full raw video at original duration
- Baseline crop (`framing.baseline_zoom: 1.48`) to match the client's tighter framing target
- Continuous Thai speech subtitles (white + drop shadow, bottom)
- 3 Thai keyword popups (white + pink outline, top, italic) at AI-selected topic shifts
- No content cuts

**Visual reference:** [`test/output-sample-quality-0317.mp4`](../../test/) (client provided)

**Style targets:**
- Subject vertical fill: ~55% of frame
- Subtitle line count: 1 (per ASS Dialogue)
- Subtitle character count: ~20 Thai chars per line
- Subtitle event duration: 0.83–2.5s (Netflix-compliant)
- Popup count: 3 per ~45s video
- Popup duration: 2.5s each

→ [ADR-008](../arc42/decisions/ADR-008-overlay-only-default-mode.md) for rationale.

---

### `highlight_reel` — LEGACY (maintained)

**Use when:** raw footage is longer (5+ min) and you genuinely need to pick the best ~45-90s.

**Pipeline produces:**
- A trimmed video cutting only the highest-value speech segments
- Concatenated highlights with optional zoom on selected moments
- Subtitles remapped to the concat'd timeline
- English keyword popups (or Thai, configurable)

**Status:** Functional but rarely tested. Risk of bit-rot — see [debt 002](../debt/002-highlight-reel-mode-bitrot-risk.md). Re-validate when next used.

---

## Content type assumptions

Clipforge is tuned for **Thai bodyweight-exercise instructional content**. Key assumptions baked into defaults:

| Assumption | Where it shows up |
|---|---|
| Single host, talking + demoing | `cfg.ai.cleanup_topic_hint`; `keyword_style` |
| Indoor or outdoor static-camera footage | `framing.baseline_zoom` and `crop_center_y: 0.56` (subject slightly lower than dead center) |
| 9:16 portrait | All defaults; baseline crop math |
| 4K source (2160×3840) | `font_size: 0` auto-scales to `height // 14` ≈ 275px |
| ~16-18 Thai chars/sec speech rate | `target_cps: 18` |
| 3 thematic chapters per ~45s video | `keywords.count: 3` |
| Fitness vocabulary | `cleanup_rules.md` body-part list; `keyword_style` examples |

**When these assumptions break,** the operator tunes config OR (Phase 2) we add per-creator profiles.

---

## Target style anchors

The defaults match the client's reference output measured quantitatively:

| Aspect | Measured Target | Clipforge default | Match |
|---|---|---|---|
| Subject vertical fill | 55.5% | 54.0% | ✓ |
| Subtitle row count (median) | 2 | 1 (each ASS event = 1 line) | n/a (different representation) |
| Subtitle row width (median) | 68% frame | ~60% frame | close |
| Popup count per video | 3 | 3 | ✓ |
| Popup style | white + pink outline, top | white + pink outline, top | ✓ |
| Speech sub style | white + drop shadow, bottom (per font sample) | white + drop shadow, bottom | ✓ |
| Font style | bold, loopless modern | IBM Plex Sans Thai Bold | ✓ |

---

## What clipforge will NEVER do (product-level decisions)

These aren't "deferred to a later phase" — they're explicitly out of scope for clipforge's positioning:

- **Lie about timing.** If the host pauses mid-sentence, the subs go silent. We never pad-extend a sub to fill silence.
- **Invent text.** Cleanup only corrects with high confidence. Memory file requires operator confirmation. No hallucinated subtitles.
- **Translate.** Thai stays Thai. English loanwords stay as the speaker said them.
- **Edit for the speaker.** We don't drop "ครับ"/"นะครับ" filler particles — they're part of natural speech. We don't reorder clauses. We don't change content.
- **Make creative judgments beyond the rules.** Keyword popup selection follows `cfg.ai.keyword_style`. Operator owns the rule.
