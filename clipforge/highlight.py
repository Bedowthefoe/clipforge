"""Use claude -p to select highlight segments and pick keyword popups."""

import json
import re
import subprocess
import time

from .config import ClipforgeConfig


def _merge_adjacent(segments: list[dict], gap: float) -> list[list[dict]]:
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


def _parse_json(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise RuntimeError(f"No JSON object found in Claude response:\n{text[:400]}")
        return json.loads(match.group())


# ────────────────────────────────────────────────────────────────────────
# Overlay-only mode: ask Claude for keyword popups only
# ────────────────────────────────────────────────────────────────────────
def run_overlay(transcript: list[dict], video_duration: float,
                cfg: ClipforgeConfig) -> dict:
    """
    Return {"keyword_popups": [{"text", "start", "duration"}, ...], "edit_note": str}.
    No content cutting — the full video is kept.
    """
    if not cfg.keywords.enabled or cfg.keywords.count <= 0:
        return {"keyword_popups": [], "edit_note": "keywords disabled"}

    numbered = "\n".join(
        f"[{i}] {s['start']:.1f}s-{s['end']:.1f}s : {s['text']}"
        for i, s in enumerate(transcript)
    )

    lang_label = "Thai" if cfg.keywords.language.lower().startswith("th") else "English"

    prompt = f"""You are a short-form video editor adding pop-up keyword overlays to a fitness video.

Video: {video_duration:.0f}s total, content language: {cfg.ai.content_language}
The full video will be kept as-is. You are ONLY choosing pop-up keyword overlays.

--- KEYWORD INSTRUCTIONS ---
{cfg.ai.keyword_style.strip()}
Keyword language: {lang_label}
Pick exactly {cfg.keywords.count} popups, spread roughly evenly across the video.
Each popup appears for ~{cfg.keywords.display_duration}s.

--- TRANSCRIPT (numbered segments with source timestamps) ---
{numbered}

--- OUTPUT FORMAT ---
Return ONLY valid JSON, no markdown fences, no explanation:
{{
  "keyword_popups": [
    {{"text": "...", "start": 0.0, "duration": {cfg.keywords.display_duration}}},
    ...
  ],
  "edit_note": "one sentence describing the choices"
}}

Rules:
- "text" is the {lang_label} keyword phrase (short — 2-4 words).
- "start" is the source-video timestamp (seconds) when the popup should appear.
- "start" values must be in ascending order.
- All "start" + "duration" must fit within the video duration ({video_duration:.1f}s).
- Choose moments that match a topic shift, technique introduction, or key tip in the transcript."""

    print(f"  → Calling claude -p (overlay mode)...")
    t0 = time.time()
    result_text = _call_claude(prompt)
    print(f"  → Response in {time.time()-t0:.1f}s")

    analysis = _parse_json(result_text)
    popups = analysis.get("keyword_popups", [])

    # Validate / clamp
    cleaned = []
    for p in popups:
        try:
            start = max(0.0, float(p["start"]))
            dur   = float(p.get("duration", cfg.keywords.display_duration))
            txt   = str(p["text"]).strip()
        except (KeyError, ValueError, TypeError):
            continue
        if not txt:
            continue
        if start + dur > video_duration:
            dur = max(0.5, video_duration - start)
        cleaned.append({"text": txt, "start": round(start, 3), "duration": round(dur, 3)})

    cleaned = cleaned[: cfg.keywords.count]
    print(f"  → Keyword popups: {[k['text'] for k in cleaned]}")
    print(f"  → Edit note: {analysis.get('edit_note', '')}")
    return {"keyword_popups": cleaned, "edit_note": analysis.get("edit_note", "")}


# ────────────────────────────────────────────────────────────────────────
# Highlight-reel mode (legacy): pick segments + zoom + keywords-on-segments
# ────────────────────────────────────────────────────────────────────────
def run(transcript: list[dict], video_duration: float,
        cfg: ClipforgeConfig) -> dict:
    """Dispatch on cfg.mode."""
    if getattr(cfg, "mode", "overlay_only") == "overlay_only":
        return run_overlay(transcript, video_duration, cfg)
    return run_highlight_reel(transcript, video_duration, cfg)


def run_highlight_reel(transcript: list[dict], video_duration: float,
                       cfg: ClipforgeConfig) -> dict:
    """Legacy: returns selected[]/keywords[]/zoom_moments[]."""
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

    print(f"  → Calling claude -p (highlight-reel mode)...")
    t0 = time.time()
    result_text = _call_claude(prompt)
    print(f"  → Response in {time.time()-t0:.1f}s")

    analysis = _parse_json(result_text)

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
