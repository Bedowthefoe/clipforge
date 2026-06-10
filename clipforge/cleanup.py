"""Claude-based Thai transcript cleanup.

Whisper large-v3 produces ~5–10% character-error-rate on fast colloquial Thai.
Most errors are: tone-mark mistakes, sound-alike consonants, sara-am decomposition,
and English loan-word mis-spellings. This module asks Claude (via `claude -p`)
to identify and correct those errors, given:

  - the persistent rule set (clipforge/cleanup_rules.md)
  - lessons learned from past runs (clipforge/cleanup_memory.md)
  - topic context from config (e.g. "Thai fitness instruction")
  - the numbered transcript

Returns a corrected copy of the segments — timestamps and word arrays are NEVER
modified, only the `text` field. Each correction carries a confidence label so
the caller can threshold (apply only high/medium-confidence by default).
"""

import json
import os
import re
import subprocess
import time
from typing import Optional

from .config import ClipforgeConfig

RULES_PATH  = os.path.join(os.path.dirname(__file__), "cleanup_rules.md")
MEMORY_PATH = os.path.join(os.path.dirname(__file__), "cleanup_memory.md")

CONFIDENCE_RANK = {"low": 0, "medium": 1, "high": 2}


def _load_doc(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def _call_claude(prompt: str, timeout: int = 120) -> str:
    r = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True, text=True, timeout=timeout,
    )
    if r.returncode != 0:
        raise RuntimeError(f"claude -p failed (exit {r.returncode}):\n{r.stderr[:400]}")
    outer = json.loads(r.stdout)
    result = outer.get("result", r.stdout)
    return re.sub(r"```json\s*|\s*```", "", result).strip()


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise RuntimeError(f"No JSON object found in Claude response:\n{text[:400]}")
        return json.loads(match.group())


def _normalize_sara_am(text: str) -> str:
    """Recombine decomposed Sara Am (NIKHAHIT + SARA AA) into the precomposed form.
    Whisper sometimes outputs 'ทํา' instead of 'ทำ'. Deterministic fix — apply
    before sending to Claude so the agent doesn't waste turns on this."""
    # U+0E4D NIKHAHIT followed by U+0E32 SARA AA -> U+0E33 SARA AM
    return text.replace("ํา", "ำ")


def clean_transcript(segments: list[dict],
                     cfg: ClipforgeConfig,
                     topic_hint: Optional[str] = None,
                     min_confidence: str = "medium") -> dict:
    """
    Run the Claude cleanup pass.

    Returns: {
      "segments": corrected segments (text only, same length, same timestamps),
      "corrections": [{index, original, corrected, confidence, reason, applied}],
      "notes": str,
      "raw_response": str (for audit),
    }

    Corrections are only APPLIED when their confidence ≥ min_confidence.
    Other corrections are returned for audit but the segment text is unchanged.
    """
    if not segments:
        return {"segments": segments, "corrections": [], "notes": "", "raw_response": ""}

    # Step 1 — deterministic Sara Am normalisation (no Claude call needed)
    norm_segments = []
    sara_am_count = 0
    for seg in segments:
        new_seg = dict(seg)
        original = seg.get("text", "")
        normalized = _normalize_sara_am(original)
        if normalized != original:
            sara_am_count += 1
        new_seg["text"] = normalized
        norm_segments.append(new_seg)
    if sara_am_count:
        print(f"  → Normalised Sara Am in {sara_am_count} segments (ทํา → ทำ etc.)")

    # Step 2 — Claude pass
    rules  = _load_doc(RULES_PATH)
    memory = _load_doc(MEMORY_PATH)
    topic  = topic_hint or "Thai fitness instructional video"

    numbered = "\n".join(
        f"[{i}] {s['start']:.1f}s : {s['text']}" for i, s in enumerate(norm_segments)
    )

    prompt = f"""You are a Thai transcription proofreader for a short-form fitness video.
The transcript below was produced by Whisper large-v3 (open-source STT) and
contains the usual Thai STT error patterns: wrong tone marks, sound-alike
consonants, mis-spelled English loan words, etc.

--- RULES (read carefully, follow exactly) ---
{rules}

--- LESSONS LEARNED FROM PAST RUNS ---
{memory}

--- TOPIC CONTEXT ---
{topic}

--- TRANSCRIPT (numbered) ---
{numbered}

Apply the rules above to identify and correct obvious errors. Be conservative —
when uncertain, leave the original text. Output ONLY the JSON object described
in the Output Contract section of the rules, nothing else."""

    print(f"  → Calling claude -p (cleanup pass)...")
    t0 = time.time()
    response = _call_claude(prompt)
    print(f"  → Response in {time.time()-t0:.1f}s")

    try:
        result = _parse_json(response)
    except Exception as e:
        print(f"  → Cleanup response not parseable: {e}")
        return {
            "segments":     norm_segments,
            "corrections":  [],
            "notes":        f"parse error: {e}",
            "raw_response": response,
        }

    corrections = result.get("corrections", []) or []
    notes       = result.get("notes", "")

    # Apply corrections by index, gated on confidence.
    # Claude returns just the substring that changed — we splice it back into
    # the full segment text. This preserves all surrounding speech so that
    # subtitle timing (driven by char count) stays in sync with the audio.
    threshold = CONFIDENCE_RANK.get(min_confidence.lower(), 1)
    out_segments = [dict(s) for s in norm_segments]
    applied = 0
    for c in corrections:
        try:
            idx = int(c["index"])
            original_substr  = str(c["original"])
            corrected_substr = str(c["corrected"])
            confidence       = str(c.get("confidence", "low")).lower()
        except (KeyError, ValueError, TypeError):
            c["applied"] = False
            c["apply_method"] = "skipped (parse error)"
            continue
        if not (0 <= idx < len(out_segments)):
            c["applied"] = False
            c["apply_method"] = "skipped (index OOB)"
            continue
        rank = CONFIDENCE_RANK.get(confidence, 0)
        if rank < threshold:
            c["applied"] = False
            c["apply_method"] = f"skipped (confidence {confidence} < {min_confidence})"
            continue

        # Surgical substring replace — does NOT touch text outside the correction
        current_text = out_segments[idx]["text"]
        if original_substr and original_substr in current_text:
            out_segments[idx]["text"] = current_text.replace(original_substr, corrected_substr, 1)
            c["applied"] = True
            c["apply_method"] = "substring replace"
            applied += 1
        elif not original_substr or original_substr.strip() == "":
            # Claude omitted the original; safest fallback is to skip
            c["applied"] = False
            c["apply_method"] = "skipped (no original substring)"
        else:
            # Original substring not found in current segment text. Could be:
            #   (a) Sara Am normalisation already changed the text and Claude's
            #       "original" no longer matches verbatim — try a normalised match.
            #   (b) Claude hallucinated the location — skip.
            normalised_original  = _normalize_sara_am(original_substr)
            normalised_corrected = _normalize_sara_am(corrected_substr)
            if normalised_original and normalised_original in current_text:
                out_segments[idx]["text"] = current_text.replace(
                    normalised_original, normalised_corrected, 1
                )
                c["applied"] = True
                c["apply_method"] = "substring replace (sara-am normalised)"
                applied += 1
            else:
                c["applied"] = False
                c["apply_method"] = "skipped (original substring not found)"

    print(f"  → Corrections proposed: {len(corrections)} | applied: {applied} "
          f"(threshold={min_confidence})")
    if notes:
        print(f"  → Notes: {notes}")

    return {
        "segments":     out_segments,
        "corrections":  corrections,
        "notes":        notes,
        "raw_response": response,
    }
