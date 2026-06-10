# ADR-004 — PyThaiNLP newmm for word-aware line wrapping

**Status:** Accepted
**Date:** 2026-06-01
**Deciders:** Operator

---

## Context

Whisper produces long sentence-level Thai segments (e.g. 67 characters in 3 seconds). When rendered as subtitles:
- A single ASS line of 67 Thai chars overflows the frame horizontally — even at 90% width.
- libass cannot semantically wrap Thai because **Thai has no inter-word spaces** to break on.
- libass's `wrap_unicode` (libunibreak) wraps at *any* Thai grapheme — semantically wrong for subtitle quality (industry consensus: break at word boundaries).

Options:

| Option | Pros | Cons |
|---|---|---|
| libass `wrap_unicode=1` | Built-in; no Python dep | Breaks anywhere in Thai → unreadable subs |
| PyThaiNLP `newmm` (dict-based maximal matching) | Industry standard; fast; no ML deps | Lower theoretical accuracy than learned tokenizers |
| PyThaiNLP `attacut` (neural) | Slightly better accuracy | ~6× slower; requires PyTorch |
| ICU BreakIterator (PyICU) | Standard | Heavy install; less Thai-tuned than newmm |
| BudouX / Google segmenter | Modern | Less Thai support |

## Decision

Use **PyThaiNLP `newmm`** for word tokenization. Insert `\N` (ASS hard line break) between greedy-packed groups of tokens that fit within `max_chars_per_line`.

```python
from pythainlp.tokenize import word_tokenize
tokens = word_tokenize(text, engine="newmm", keep_whitespace=True)
```

For overlay_only mode with single-line events (`max_lines: 1`), we don't insert `\N` — instead `split_into_timed_lines` emits one Dialogue per packed line (see ADR-006).

## Why

- **newmm is the de facto Python Thai tokenizer** — used by major Thai NLP projects.
- **Dict-based, no ML dependency** — pip install is ~5MB, instant tokenization.
- **Good enough for subtitle word boundaries** — the consequence of a wrong split is a slightly awkward line wrap, not loss of meaning.
- **Speed matters** — we tokenize every segment; attacut at 6× slower wouldn't change output quality enough to justify.
- libass `wrap_unicode` was tested and rejected: it broke characters in the middle of compound Thai words.

## Consequences

- Adds `pythainlp` to deps (`pip install --break-system-packages pythainlp`, ~5MB).
- Resegmentation in transcribe.py uses Whisper sub-syllabic word boundaries (not PyThaiNLP), which sometimes splits a PyThaiNLP word across two sub-segments (e.g. "แ" / "ถม" instead of "แถม"). Known cosmetic debt — see [debt 003](../../debt/003-resegment-bisects-thai-words.md).
- `char_width_ratio` tuning (default 0.32 for IBM Plex Thai) is empirical — different fonts may need different ratios. Documented in `auto_max_chars`.

## Revisit triggers

- If attacut accuracy materially improves subtitle quality on representative content — A/B test.
- If we need handling for non-Thai scripts in the same pipeline — generalise to per-language tokenizers.
- If a PyThaiNLP newmm dictionary update breaks word boundaries — pin pythainlp version in requirements.txt.
