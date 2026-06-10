# Debt 001 — Cleanup overwrote full segments with correction substrings

**Status:** ✅ Fixed (2026-06-07)
**Severity (when live):** Critical — broke subtitle timing on every run with cleanup enabled

---

## What it was

`clipforge/cleanup.py` originally applied each Claude-returned correction with:

```python
out_segments[idx]["text"] = corrected   # WRONG — overwrites the entire segment
```

But Claude's `corrected` value is just the substring that changed, not the full segment text. Example:

- Original segment 0 text: `การตื่นมาแล้วทำท่าง่าย ๆ อย่างเช่นการก้าวยืนขึ้นเรายอดลงเนี่ยนะครับ` (67 chars)
- Claude correction: `{original: "เรายอดลงเนี่ยนะครับ", corrected: "เราย่อลงเนี่ยนะครับ"}` — just the substring
- Bug result: full segment overwritten with the 19-char correction → 67 chars of speech became 4-6 chars on screen

## Visible symptom

Subtitle events showed **one syllable held for 0.83s followed by 2-3 second silent gaps** even while the host was talking. Diagnosed by dumping the rendered `.ass` and comparing to the full transcript.

## Root cause

Bad assumption in the cleanup module design. The Claude prompt asked for "corrections" — naturally Claude returned the changed substring, not the rewritten full segment. Code expected the full segment.

## Fix

Switch to **surgical substring replace**:

```python
current_text = out_segments[idx]["text"]
if original_substr in current_text:
    out_segments[idx]["text"] = current_text.replace(original_substr, corrected_substr, 1)
    c["apply_method"] = "substring replace"
else:
    # Fallback: try Sara Am normalised match
    normalised = _normalize_sara_am(original_substr)
    if normalised in current_text:
        out_segments[idx]["text"] = current_text.replace(normalised, normalised_corrected, 1)
        c["apply_method"] = "substring replace (sara-am normalised)"
    else:
        c["applied"] = False
        c["apply_method"] = "skipped (original substring not found)"
```

Now each correction is applied as a targeted substring replace within the segment text. Full segment text is preserved; only the wrong substring changes. Each correction's `apply_method` is logged for audit.

## How we verified the fix

After the fix, ran the same input + cached transcript → output had all 67-char segments intact, subtitle timing distribution returned to Netflix-compliant range (0.83-1.28s), no big silent gaps.

## Lesson carried

Logged in [project/learnings.md](../project/learnings.md): **Surgical substring replace > full-segment overwrite when applying LLM-suggested corrections.**
