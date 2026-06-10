"""Generate .ass subtitle files. Supports two modes:
- highlight_reel: remapped timestamps (segment[0] starts at t=0 in output)
- overlay_only:   source-time stamps, with Speech + KeywordPop styles in one file
"""

import datetime
import os
import subprocess
import json
import ass as ass_lib

from .config import ClipforgeConfig
from .textwrap_th import wrap_thai, auto_max_chars, split_into_timed_lines, reconcile_event_timing


# ── ASS alignment codes (numpad layout) ──
ALIGN_BOTTOM_CENTER = 2
ALIGN_TOP_CENTER    = 8
ALIGN_MIDDLE_CENTER = 5


def _probe_dims(video_path: str) -> tuple[int, int]:
    r = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-select_streams", "v:0", video_path
    ], capture_output=True, text=True)
    stream = json.loads(r.stdout)["streams"][0]
    return stream["width"], stream["height"]


def _hex_to_color(hex_rgb: str, alpha: int = 0) -> "ass_lib.data.Color":
    """Convert 'RRGGBB' (or '#RRGGBB') to an ass Color. alpha 0=opaque, 255=transparent."""
    h = hex_rgb.lstrip("#")
    if len(h) != 6:
        return ass_lib.data.Color(r=255, g=255, b=255, a=alpha)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return ass_lib.data.Color(r=r, g=g, b=b, a=alpha)


def _named_to_color(name: str, alpha: int = 0) -> "ass_lib.data.Color":
    table = {
        "white":   (255, 255, 255),
        "black":   (0, 0, 0),
        "yellow":  (255, 255, 0),
        "red":     (255, 0, 0),
        "magenta": (255, 0, 255),
        "pink":    (255, 20, 147),
    }
    r, g, b = table.get(name.lower(), (255, 255, 255))
    return ass_lib.data.Color(r=r, g=g, b=b, a=alpha)


def _color(spec: str, alpha: int = 0) -> "ass_lib.data.Color":
    """Accept either a named color or RRGGBB hex."""
    spec = (spec or "white").strip()
    if all(c in "0123456789abcdefABCDEF" for c in spec.lstrip("#")) and len(spec.lstrip("#")) == 6:
        return _hex_to_color(spec, alpha)
    return _named_to_color(spec, alpha)


# ────────────────────────────────────────────────────────────────────────
# Highlight-reel mode: remapped subtitles (existing behavior)
# ────────────────────────────────────────────────────────────────────────
def make_ass(segments: list[dict], video_path: str,
             cfg: ClipforgeConfig, out_path: str) -> str:
    """
    Generate .ass for highlight_reel mode.
    Timestamps are REMAPPED so segment[0] starts at t=0 in the output.
    """
    width, height = _probe_dims(video_path)

    doc = ass_lib.Document()
    doc.play_res_x = width
    doc.play_res_y = height

    font_size = cfg.subtitles.font_size or max(48, height // 14)

    style = ass_lib.Style()
    style.name          = "Default"
    style.fontname      = cfg.subtitles.font
    style.fontsize      = font_size
    style.primary_color = _color(cfg.subtitles.color_primary)
    style.outline_color = _color(cfg.subtitles.color_outline)
    style.back_color    = ass_lib.data.Color(r=0, g=0, b=0, a=160)
    style.bold          = True
    style.outline       = cfg.subtitles.outline_width
    style.shadow        = cfg.subtitles.shadow
    style.alignment     = ALIGN_TOP_CENTER if cfg.subtitles.position == "top" else ALIGN_BOTTOM_CENTER
    style.margin_v      = cfg.subtitles.margin_bottom
    doc.styles.append(style)

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


# ────────────────────────────────────────────────────────────────────────
# Overlay-only mode: source-time subtitles + keyword popups
# ────────────────────────────────────────────────────────────────────────
def make_overlay_ass(segments: list[dict], keyword_popups: list[dict],
                     video_path: str, cfg: ClipforgeConfig, out_path: str) -> str:
    """
    Generate .ass for overlay_only mode.
    - Speech subtitles use SOURCE timestamps (no remap — we keep full video).
    - Keyword popups overlay at given start/duration with pink-outline style.
    - Thai text is tokenized via PyThaiNLP newmm and wrapped at word boundaries.

    segments:        [{"start", "end", "text"}, ...] in source video time
    keyword_popups:  [{"text", "start", "duration"}, ...] in source video time
    """
    width, height = _probe_dims(video_path)

    doc = ass_lib.Document()
    doc.play_res_x = width
    doc.play_res_y = height

    # ── Speech style (white text + drop shadow, no outline — matches reference) ──
    speech_fontsize = cfg.subtitles.font_size or max(48, height // 14)
    sp = ass_lib.Style()
    sp.name          = "Speech"
    sp.fontname      = cfg.subtitles.font
    sp.fontsize      = speech_fontsize
    sp.primary_color = _color(cfg.subtitles.color_primary)
    sp.outline_color = _color(cfg.subtitles.color_outline)
    # back_color is the SHADOW color (ASS BorderStyle 1 uses BackColour for shadow)
    sp.back_color    = _color(cfg.subtitles.shadow_color, alpha=cfg.subtitles.shadow_alpha)
    sp.bold          = True
    sp.outline       = cfg.subtitles.outline_width
    sp.shadow        = cfg.subtitles.shadow
    sp.alignment     = ALIGN_TOP_CENTER if cfg.subtitles.position == "top" else ALIGN_BOTTOM_CENTER
    sp.margin_v      = cfg.subtitles.margin_bottom
    sp.margin_l      = cfg.subtitles.margin_horizontal
    sp.margin_r      = cfg.subtitles.margin_horizontal
    doc.styles.append(sp)

    # Compute wrap width for speech
    speech_max_chars = cfg.subtitles.max_chars_per_line or auto_max_chars(
        speech_fontsize, width, cfg.subtitles.margin_horizontal
    )

    # ── Keyword popup style (top, white + pink outline, larger) ──
    kp = ass_lib.Style()
    kp.name          = "KeywordPop"
    kp.fontname      = cfg.subtitles.font
    kp.fontsize      = cfg.keywords.popup_font_size
    kp.primary_color = _color(cfg.keywords.popup_color)
    kp.outline_color = _color(cfg.keywords.popup_outline_color)
    kp.back_color    = ass_lib.data.Color(r=0, g=0, b=0, a=255)
    kp.bold          = True
    kp.italic        = True
    kp.outline       = cfg.keywords.popup_outline_width
    kp.shadow        = 0
    kp.margin_l      = cfg.subtitles.margin_horizontal
    kp.margin_r      = cfg.subtitles.margin_horizontal
    if cfg.keywords.popup_position == "top":
        kp.alignment = ALIGN_TOP_CENTER
        kp.margin_v  = cfg.keywords.popup_margin_top
    elif cfg.keywords.popup_position == "bottom":
        kp.alignment = ALIGN_BOTTOM_CENTER
        kp.margin_v  = cfg.keywords.popup_margin_top
    else:
        kp.alignment = ALIGN_MIDDLE_CENTER
        kp.margin_v  = 0
    doc.styles.append(kp)

    # Compute wrap width for keyword popups (larger font → fewer chars per line)
    popup_max_chars = auto_max_chars(
        cfg.keywords.popup_font_size, width, cfg.subtitles.margin_horizontal
    )

    # ── Speech subtitles ──
    # max_lines == 1: single-line events with reading-rate uniform pacing
    #                 (Netflix min 0.83s / short-form max 2.5s / target_cps).
    # max_lines  > 1: multi-line wrap with \N (legacy behavior).
    if cfg.subtitles.enabled:
        if cfg.subtitles.max_lines == 1:
            raw_events: list[dict] = []
            for seg in segments:
                if not seg.get("text"):
                    continue
                lines = split_into_timed_lines(
                    seg["text"],
                    seg.get("words") or [],
                    seg["start"], seg["end"],
                    speech_max_chars,
                    target_cps=cfg.subtitles.target_cps,
                    min_dur  =cfg.subtitles.min_event_duration,
                    max_dur  =cfg.subtitles.max_event_duration,
                    inter_gap=cfg.subtitles.inter_event_gap,
                    lead_time=cfg.subtitles.lead_time,
                    anchor_to_whisper_words=cfg.subtitles.anchor_to_whisper_words,
                    max_drift_correction   =cfg.subtitles.max_drift_correction,
                )
                raw_events.extend(lines)
            # Cross-segment cleanup: prevent overlap between consecutive segments
            raw_events = reconcile_event_timing(
                raw_events,
                inter_gap=cfg.subtitles.inter_event_gap,
                min_dur  =cfg.subtitles.min_event_duration,
            )
            for ln in raw_events:
                ev = ass_lib.Dialogue()
                ev.start = datetime.timedelta(seconds=ln["start"])
                ev.end   = datetime.timedelta(seconds=ln["end"])
                ev.style = "Speech"
                ev.text  = ln["text"]
                doc.events.append(ev)
            doc._speech_event_count = len(raw_events)
        else:
            for seg in segments:
                if not seg.get("text"):
                    continue
                ev = ass_lib.Dialogue()
                ev.start = datetime.timedelta(seconds=seg["start"])
                ev.end   = datetime.timedelta(seconds=seg["end"])
                ev.style = "Speech"
                ev.text  = wrap_thai(
                    seg["text"], speech_max_chars, max_lines=cfg.subtitles.max_lines,
                )
                doc.events.append(ev)
            doc._speech_event_count = sum(1 for s in segments if s.get("text"))

    # ── Keyword popups (source time) ──
    if cfg.keywords.enabled:
        for kw in keyword_popups:
            txt = kw.get("text", "").strip()
            if not txt:
                continue
            start = float(kw["start"])
            dur   = float(kw.get("duration", cfg.keywords.display_duration))
            ev = ass_lib.Dialogue()
            ev.start = datetime.timedelta(seconds=start)
            ev.end   = datetime.timedelta(seconds=start + dur)
            ev.style = "KeywordPop"
            ev.text  = wrap_thai(txt, popup_max_chars, max_lines=2)
            doc.events.append(ev)

    with open(out_path, "w", encoding="utf-8-sig") as f:
        doc.dump_file(f)
    return out_path


# ────────────────────────────────────────────────────────────────────────
# Legacy: keyword drawtext (highlight_reel only)
# ────────────────────────────────────────────────────────────────────────
def _position_y(cfg, height: int) -> int:
    pos = cfg.keywords.position_y
    if pos == "top_third":   return height // 4
    if pos == "center":      return height // 2
    if pos == "bottom_third":return (height * 3) // 4
    try:                     return int(pos)
    except ValueError:       return height // 4


def keyword_drawtext_filters(keyword_events: list[dict], cfg, height: int) -> list[str]:
    """Build FFmpeg drawtext filter strings for keyword overlays (highlight_reel mode)."""
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
