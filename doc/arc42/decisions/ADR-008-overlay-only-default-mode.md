# ADR-008 — overlay_only as default pipeline mode

**Status:** Accepted
**Date:** 2026-06-01
**Deciders:** Operator

---

## Context

The client provided a reference target video `output-sample-quality-0317.mp4`. Quantitative analysis vs the raw input:

- Target keeps **all 52 seconds** of source content (no cuts)
- Target adds: continuous subtitles + 3 pink-outlined Thai keyword popups + baseline crop
- Subject framing: target fills 55% of vertical frame; raw fills 37% (1.48× crop needed)

Originally we built a `highlight_reel` mode that picks "best" segments and concatenates them. But for <60s creator clips, the target shows we **shouldn't be cutting content** — we should be **overlaying production polish on full takes**.

Options:

| Option | Idea |
|---|---|
| Keep cutting + AI segment selection (legacy) | Original `highlight_reel` mode |
| Always full-video overlay (new) | Skip Claude's `selected[]` choices; render the whole video |
| Mode flag in config | Both modes available; default per content type |

## Decision

Add a `cfg.mode` flag with values `overlay_only` (default) and `highlight_reel` (maintained but de-prioritised). All shipped configs use `overlay_only`.

```yaml
mode: overlay_only            # vs highlight_reel
```

Both modes share Stages 1 (Transcribe) and 5 (Edit) skeleton. They differ in:

| Stage | `overlay_only` | `highlight_reel` |
|---|---|---|
| Transcribe | Full transcript; pause-based resegmentation | Drop incomplete/fragment segments |
| Highlight | Claude returns `keyword_popups: [...]` only | Claude returns `selected[]`, `zoom_moments[]`, `keywords[]` |
| Subtitle | Generate full-length subs with two styles | Remap timestamps to concat'd timeline; single style |
| Edit | Single ffmpeg pass: crop → libass burn | Multi-pass: cut clips → concat → final overlay |

## Why

- **The target reference is the source of truth.** The client edits like this manually today; clipforge should match it.
- **Most short-form (<60s) is one-take.** Cutting destroys narrative flow that the host already plans.
- **Overlay-only is simpler + faster** — single FFmpeg pass per render.
- **Legacy mode kept** because long-form footage (5+ min raw) will still benefit from cutting later.

## Consequences

- Default behaviour matches the client target — minimal surprise.
- `highlight_reel` code path still exists but is rarely tested. Risk of bit-rot. Documented in [debt 002](../../debt/002-highlight-reel-mode-bitrot-risk.md).
- The cleanup pass + popup selection both operate on the FULL transcript, not a curated subset. Slightly larger prompts. Acceptable.

## Revisit triggers

- If a creator brings 5+ min raw footage that does need trimming — re-enable `highlight_reel` and verify it still works.
- If we decide to introduce a third mode (e.g. "speed_ramp" for time-lapse demos) — refactor the dispatcher.
