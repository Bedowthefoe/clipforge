"""Generate .ass subtitle file from transcript segments with remapped timestamps."""

import datetime
import os
import ass as ass_lib

from .config import ClipforgeConfig


def _position_y(cfg, height: int) -> int:
    """Compute keyword overlay Y position from config."""
    pos = cfg.keywords.position_y
    if pos == "top_third":
        return height // 4
    elif pos == "center":
        return height // 2
    elif pos == "bottom_third":
        return (height * 3) // 4
    else:
        try:
            return int(pos)
        except ValueError:
            return height // 4


def make_ass(segments: list[dict], video_path: str,
             cfg: ClipforgeConfig, out_path: str) -> str:
    """
    Generate .ass subtitle file from segments with remapped output timestamps.
    segments: list of {"start", "end", "text"} in SOURCE video time.
    Timestamps are remapped so segment[0] starts at t=0 in the output.
    """
    import subprocess, json
    probe = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "v:0", video_path
    ], capture_output=True, text=True)
    stream = json.loads(probe.stdout)["streams"][0]
    width, height = stream["width"], stream["height"]

    doc = ass_lib.Document()
    doc.play_res_x = width
    doc.play_res_y = height

    font_size = cfg.subtitles.font_size or max(32, height // 22)
    margin_v  = cfg.subtitles.margin_bottom

    style = ass_lib.Style()
    style.name          = "Default"
    style.fontname      = cfg.subtitles.font
    style.fontsize      = font_size
    style.primary_color = ass_lib.data.Color(r=255, g=255, b=255, a=0)
    style.outline_color = ass_lib.data.Color(r=0,   g=0,   b=0,   a=0)
    style.back_color    = ass_lib.data.Color(r=0,   g=0,   b=0,   a=160)
    style.bold          = True
    style.outline       = cfg.subtitles.outline_width
    style.shadow        = cfg.subtitles.shadow
    style.alignment     = 8 if cfg.subtitles.position == "top" else 2
    style.margin_v      = margin_v
    doc.styles.append(style)

    # Remap timestamps: each segment placed sequentially in output
    cursor = 0.0
    for seg in segments:
        if not seg.get("text"):
            continue
        dur = seg["end"] - seg["start"]
        event = ass_lib.Dialogue()
        event.start = datetime.timedelta(seconds=cursor)
        event.end   = datetime.timedelta(seconds=cursor + dur)
        event.style = "Default"
        event.text  = seg["text"]
        doc.events.append(event)
        cursor += dur

    with open(out_path, "w", encoding="utf-8-sig") as f:
        doc.dump_file(f)

    return out_path


def keyword_drawtext_filters(keyword_events: list[dict], cfg, height: int) -> list[str]:
    """
    Build FFmpeg drawtext filter strings for keyword overlays.
    keyword_events: [{"text", "start", "end", "size"}] — already in OUTPUT timeline.
    """
    if not cfg.keywords.enabled:
        return []

    y_pos = _position_y(cfg, height)
    filters = []
    for kw in keyword_events:
        txt = kw["text"].replace("'", "\\'").replace(":", "\\:")
        size = kw.get("size", cfg.keywords.font_size)
        filters.append(
            f"drawtext=text='{txt}':"
            f"fontsize={size}:"
            f"fontcolor={cfg.keywords.color}:"
            f"borderw={cfg.keywords.border_width}:"
            f"bordercolor={cfg.keywords.border_color}:"
            f"x=(w-tw)/2:"
            f"y={y_pos}:"
            f"enable='between(t,{kw['start']:.3f},{kw['end']:.3f})'"
        )
    return filters
