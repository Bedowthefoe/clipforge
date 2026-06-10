# Debt 002 — `highlight_reel` mode bit-rot risk

**Status:** 🟡 Live debt
**Severity:** Medium — won't be noticed until someone tries to use it

---

## What it is

`cfg.mode: highlight_reel` is the legacy multi-stage pipeline that picks "best" speech segments, cuts them out, concatenates them, then overlays subs + optional zoompan.

After [ADR-008](../arc42/decisions/ADR-008-overlay-only-default-mode.md), `overlay_only` became the default and `highlight_reel` has been **untested for weeks**. Latest test was during the migration to dual-mode dispatch in early June. Since then we've changed:

- `clipforge/cleanup.py` — could shift transcript shape in ways `run_highlight_reel` doesn't expect
- `clipforge/textwrap_th.py` — added Option D/E timing; legacy mode uses different `make_ass`
- `clipforge/subtitle.py` — split into `make_ass` (legacy) + `make_overlay_ass` (new)

## Why we're carrying it

- It still implements a valid use case (long-form footage trimming)
- Ripping it out now removes optionality for Phase 4 content types
- The work to re-validate it is small (~1-2 hours)

## What breaks if we leave it

Nothing — until someone runs `cfg.mode: highlight_reel` and hits a regression. Possible breakage:

- `make_ass` (legacy subtitle generator) was last touched when we still used `font_size` from cfg — auto-scale fallback might differ from `make_overlay_ass`
- Cleanup pass's substring replace might behave differently when applied to filtered/reindexed segments
- The `selected[]` / `zoom_moments[]` schema from `run_highlight_reel` might no longer match what `editor.py::run_highlight_reel` expects

## How to pay it down

Phase 2 plan:
1. Run `cfg.mode: highlight_reel` on a longer (3+ min) test clip
2. Verify both Claude calls return valid schemas
3. Verify the cut → concat → overlay pipeline produces a watchable mp4
4. Add a smoke test that runs both modes on small fixture videos in CI
5. Decide if the mode stays alive or graduates to "removed" — if removed, write an ADR documenting the decision
