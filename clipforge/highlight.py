"""Use claude -p to select highlight segments and identify keywords/zoom moments."""

import json
import re
import subprocess
import time

from .config import ClipforgeConfig


def _merge_adjacent(segments: list[dict], gap: float) -> list[list[dict]]:
    """Group segments that are within `gap` seconds of each other."""
    if not segments:
        return []
    groups = [[segments[0]]]
    for seg in segments[1:]:
        if seg["start"] - groups[-1][-1]["end"] <= gap:
            groups[-1].append(seg)
        else:
            groups.append([seg])
    return groups


def _call_claude(prompt: str, timeout: int = 120) -> str:
    r = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True, text=True, timeout=timeout
    )
    if r.returncode != 0:
        raise RuntimeError(f"claude -p failed (exit {r.returncode}):\n{r.stderr[:400]}")
    outer = json.loads(r.stdout)
    result = outer.get("result", r.stdout)
    return re.sub(r"```json\s*|\s*```", "", result).strip()


def run(transcript: list[dict], video_duration: float,
        cfg: ClipforgeConfig) -> dict:
    """
    Returns analysis dict:
    {
      "selected": [segment_index, ...],
      "keywords": [{"text", "segment_index", "size"}, ...],
      "zoom_moments": [{"segment_index", "offset", "duration", "direction"}, ...],
      "edit_note": str
    }
    """
    numbered = "\n".join(
        f"[{i}] {s['start']:.1f}s-{s['end']:.1f}s "
        f"{'⚠ FRAGMENT' if not s.get('complete', True) else ''}:"
        f" {s['text']}"
        for i, s in enumerate(transcript)
    )

    zoom_instruction = (
        f"exactly {cfg.zoom.count} zoom moments" if cfg.zoom.enabled
        else "an empty zoom_moments list []"
    )
    keyword_instruction = (
        f"{cfg.keywords.count} keyword overlays" if cfg.keywords.enabled
        else "an empty keywords list []"
    )

    prompt = f"""You are a professional short-form video editor.

Video: {video_duration:.0f}s total, content language: {cfg.ai.content_language}
Target output duration: {cfg.output.target_duration}s (±10s acceptable)

--- CONTENT SELECTION INSTRUCTIONS ---
{cfg.ai.content_selection.strip()}

--- KEYWORD INSTRUCTIONS ---
{cfg.ai.keyword_style.strip()}
Keyword language: {cfg.ai.keyword_language}

--- TRANSCRIPT (numbered segments) ---
{numbered}

--- OUTPUT FORMAT ---
Return ONLY valid JSON, no markdown fences, no explanation:
{{
  "selected": [0, 2, 4, ...],
  "keywords": [
    {{"text": "Keyword", "segment_index": 0, "size": {cfg.keywords.font_size}}},
    ...
  ],
  "zoom_moments": [
    {{"segment_index": 0, "offset": 0.5, "duration": {cfg.zoom.duration}, "direction": "in"}},
    ...
  ],
  "edit_note": "one sentence describing the edit logic"
}}

Rules:
- selected: indices in ascending order only (no going back in time)
- keywords: {keyword_instruction}, each tied to a segment_index in selected
- zoom_moments: {zoom_instruction}, tied to segment_index in selected; alternate in/out; offset = seconds into that segment to begin zoom
- All segment_index values must exist in selected[]"""

    print(f"  → Calling claude -p...")
    t0 = time.time()
    result_text = _call_claude(prompt)
    print(f"  → Response in {time.time()-t0:.1f}s")

    try:
        analysis = json.loads(result_text)
    except json.JSONDecodeError:
        # Claude sometimes appends text after the JSON — extract the first complete object
        match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if not match:
            raise RuntimeError(f"No JSON object found in Claude response:\n{result_text[:400]}")
        try:
            analysis = json.loads(match.group())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Claude returned invalid JSON:\n{result_text[:400]}\nError: {e}")

    # Validate and clamp segment indices
    max_idx = len(transcript) - 1
    analysis["selected"] = [i for i in analysis.get("selected", []) if 0 <= i <= max_idx]
    analysis["keywords"] = [k for k in analysis.get("keywords", [])
                            if k.get("segment_index") in analysis["selected"]]
    analysis["zoom_moments"] = [z for z in analysis.get("zoom_moments", [])
                                if z.get("segment_index") in analysis["selected"]]

    selected_segs = [transcript[i] for i in analysis["selected"]]
    total = sum(s["end"] - s["start"] for s in selected_segs)

    print(f"  → Selected {len(analysis['selected'])} segments → {total:.1f}s")
    print(f"  → Keywords: {[k['text'] for k in analysis['keywords']]}")
    print(f"  → Edit note: {analysis.get('edit_note', '')}")
    return analysis
