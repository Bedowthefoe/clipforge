# ADR-009 — IBM Plex Sans Thai for subtitle rendering

**Status:** Accepted
**Date:** 2026-06-07
**Deciders:** Operator

---

## Context

The client wants **modern loopless** Thai fonts ("not old-school Thai with little buckles") that match Tahoma's metrics. Iteration history:

| Font tried | Loops? | Thai mark stacking | Verdict |
|---|---|---|---|
| Noto Sans Thai | Slightly looped | Good | Original POC default; client wanted more modern |
| Sarabun | Yes (traditional loops) | Excellent (8 GPOS lookups) | Client: "those little buckles, very old school Thai, not for new generation" |
| Tahoma (Microsoft) | No (loopless) | — | Not in `ttf-mscorefonts-installer`; need separate license |
| Prompt (cadsondemak GitHub) | No (loopless) | **Poor** — tone marks collide with vowels (only 5 GPOS lookups) | Client: stacked marks render wrong |
| IBM Plex Sans Thai | No (loopless) | **Excellent** (15 GPOS lookups) | Accepted |

The failure mode of Prompt was visible at 4K resolution: the mai-tho tone mark (`้`) sat too low on top of sara-a (`ั`), nearly touching it. Cause: Prompt's GPOS table only defines 5 lookups for the entire font, leaving very few for Thai mark-to-mark positioning. Sarabun has 8, IBM Plex Sans Thai has 15.

## Decision

Use **IBM Plex Sans Thai** (the **loopless** variant, not the `IBM Plex Sans Thai Looped` variant) as the default subtitle font for both Speech and KeywordPop styles.

```yaml
subtitles:
  font: "IBM Plex Sans Thai"
```

Installed via apt:
```
sudo apt-get install -y fonts-ibm-plex
```

Lives at `/usr/share/fonts/truetype/ibm-plex/IBMPlexSansThai-{Regular,Bold,Italic,...}.ttf`. Resolved by libass via fontconfig.

## Why

- **Loopless modern** — matches client's preference and 2026 Thai design trends.
- **15 GPOS lookups** for Thai mark positioning — measurably better than Prompt's 5. Tone marks stack cleanly above vowels without collision.
- **Free + SIL Open Font License** — no license issue (vs Tahoma which is licensed by Microsoft).
- **In Ubuntu apt repository** — single `apt install` for all variants. No GitHub downloads, no version drift.
- **Designed by IBM with full Thai script support** — used in major Thai tech UI.
- **Family includes Bold, Medium, SemiBold, Italic, Thin, ExtraLight** — full weight range for future style needs.

## Consequences

- Subtitles render with correct Thai mark stacking even at 4K.
- The `char_width_ratio: 0.32` default in `auto_max_chars` was empirically tuned to IBM Plex Thai glyphs. Different fonts may need re-tuning.
- The popup style currently uses `italic: True` — IBM Plex Sans Thai has proper italic glyphs (not faked).
- Adds `fonts-ibm-plex` as a system dependency. Documented in [02-constraints.md](../02-constraints.md) and the project README.

## Diagnostic tool

`fonttools` can be used to verify any candidate font's Thai stacking support:
```python
from fontTools.ttLib import TTFont
f = TTFont(font_path)
gpos = f['GPOS'].table
print('GPOS lookups:', len(gpos.LookupList.Lookup))
print('Features:', sorted(set(fr.FeatureTag for fr in gpos.FeatureList.FeatureRecord)))
# Want >= 10 lookups and ['kern', 'mark', 'mkmk'] features
```

Heuristic: **≥10 GPOS lookups + `mark` + `mkmk` features** → likely good Thai stacking.

## Revisit triggers

- If client requests a specific brand font (e.g. their own brand identity font) — verify GPOS quality before adopting.
- If IBM Plex Sans Thai gains a measurably better variant (e.g. v6.2) — re-install.
- If we need a different feel (more humanist, more geometric) — Anuphan, K2D, or Bai Jamjuree by Cadson Demak are alternatives worth testing.
