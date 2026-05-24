"""FFmpeg pipeline: cut segments, apply zoom, concat, overlay keywords + subtitles."""

import json
import os
import subprocess
from typing import Optional

from .config import ClipforgeConfig
from .subtitle import make_ass, keyword_drawtext_filters


def _probe_video(path: str) -> dict:
    r = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", "-select_streams", "v:0", path
    ], capture_output=True, text=True, check=True)
    data = json.loads(r.stdout)
    stream = data["streams"][0]
    fps_num, fps_den = map(int, stream.get("r_frame_rate", "30/1").split("/"))
    return {
        "width":    stream["width"],
        "height":   stream["height"],
        "fps":      fps_num / fps_den,
        "duration": float(data["format"]["duration"]),
    }


def _ffmpeg(args: list[str], label: str = ""):
    r = subprocess.run(["ffmpeg", "-y"] + args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"FFmpeg failed ({label}):\n{r.stderr[-600:]}")
    return r


def _cut_clip(video_path: str, start: float, duration: float,
              out_path: str, cfg: ClipforgeConfig,
              zoom: Optional[dict] = None, vinfo: Optional[dict] = None) -> str:
    """Cut a single segment. Optionally apply zoompan to a sub-window within it."""

    if zoom is None or not cfg.zoom.enabled:
        _ffmpeg([
            "-ss", str(start), "-i", video_path, "-t", str(duration),
            "-c:v", "libx264", "-preset", cfg.output.preset, "-crf", str(cfg.output.quality_crf),
            "-c:a", "aac", "-ar", "44100", out_path
        ], label=f"cut {start:.1f}s")
        return out_path

    # Zoom: split segment into pre / zoom-window / post, process separately, concat
    w, h, fps = vinfo["width"], vinfo["height"], vinfo["fps"]
    z_offset  = min(zoom.get("offset", 0.0), duration - 0.5)
    z_dur     = min(zoom.get("duration", cfg.zoom.duration), duration - z_offset)
    direction = zoom.get("direction", "in")
    speed     = cfg.zoom.speed
    max_scale = cfg.zoom.max_scale

    z_expr = (f"min(pzoom+{speed},{max_scale})" if direction == "in"
              else f"if(eq(on,1),{max_scale},max(pzoom-{speed},1.0))")
    zoompan_vf = (f"zoompan=z='{z_expr}':d=1:"
                  f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                  f"fps={fps:.3f}:s={w}x{h}")

    base = out_path.replace(".mp4", "")
    parts = []

    if z_offset > 0.05:
        pre = f"{base}_pre.mp4"
        _ffmpeg(["-ss", str(start), "-i", video_path, "-t", str(z_offset),
                 "-c:v", "libx264", "-preset", cfg.output.preset, "-crf", str(cfg.output.quality_crf),
                 "-c:a", "aac", "-ar", "44100", pre], label="zoom-pre")
        parts.append(pre)

    zm = f"{base}_zoom.mp4"
    _ffmpeg(["-ss", str(start + z_offset), "-i", video_path, "-t", str(z_dur),
             "-vf", zoompan_vf,
             "-c:v", "libx264", "-preset", cfg.output.preset, "-crf", str(cfg.output.quality_crf),
             "-c:a", "aac", "-ar", "44100", zm], label="zoom-render")
    parts.append(zm)

    after_start = z_offset + z_dur
    if after_start < duration - 0.05:
        post = f"{base}_post.mp4"
        _ffmpeg(["-ss", str(start + after_start), "-i", video_path,
                 "-t", str(duration - after_start),
                 "-c:v", "libx264", "-preset", cfg.output.preset, "-crf", str(cfg.output.quality_crf),
                 "-c:a", "aac", "-ar", "44100", post], label="zoom-post")
        parts.append(post)

    if len(parts) == 1:
        os.rename(parts[0], out_path)
        return out_path

    lst = f"{base}_list.txt"
    with open(lst, "w") as f:
        for p in parts:
            f.write(f"file '{p}'\n")
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out_path],
            label="zoom-concat")
    return out_path


def run(video_path: str, transcript: list[dict], analysis: dict,
        cfg: ClipforgeConfig, tmp_dir: str, output_path: str) -> str:
    """
    Full edit pipeline:
    1. Cut selected segments (with zoom on marked segments)
    2. Concat clips
    3. Generate .ass subtitles
    4. Final pass: keyword drawtext + subtitle burn
    """
    vinfo = _probe_video(video_path)
    selected_indices = analysis["selected"]
    selected_segs    = [transcript[i] for i in selected_indices]

    # Build zoom lookup: selected-list position → zoom config
    zoom_by_pos = {}
    for z in analysis.get("zoom_moments", []):
        try:
            pos = selected_indices.index(z["segment_index"])
            zoom_by_pos[pos] = z
        except ValueError:
            pass

    # ── 1. Cut clips ──
    print(f"  → Cutting {len(selected_segs)} segments...")
    clip_files = []
    for i, seg in enumerate(selected_segs):
        start = seg["start"]
        dur   = seg["end"] - seg["start"]
        out   = os.path.join(tmp_dir, f"clip_{i:03d}.mp4")
        zoom  = zoom_by_pos.get(i)
        direction = zoom["direction"] if zoom else ""
        marker = f" [zoom-{direction}]" if zoom else ""
        print(f"     clip {i}: {start:.1f}s → {seg['end']:.1f}s ({dur:.1f}s){marker}")
        _cut_clip(video_path, start, dur, out, cfg, zoom=zoom, vinfo=vinfo)
        clip_files.append(out)

    # ── 2. Concat ──
    print(f"  → Concatenating clips...")
    concat_list = os.path.join(tmp_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for cf in clip_files:
            f.write(f"file '{cf}'\n")

    concat_out = os.path.join(tmp_dir, "concat.mp4")
    _ffmpeg(["-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", concat_out],
            label="concat")

    concat_dur = _probe_video(concat_out)["duration"]
    print(f"  → Highlight reel: {concat_dur:.1f}s")

    # ── 3. Build remapped keyword timeline ──
    keyword_events = []
    if cfg.keywords.enabled:
        cursor = 0.0
        idx_to_pos = {idx: pos for pos, idx in enumerate(selected_indices)}
        for kw in analysis.get("keywords", []):
            pos = idx_to_pos.get(kw.get("segment_index"))
            if pos is None:
                continue
            seg = selected_segs[pos]
            seg_dur = seg["end"] - seg["start"]
            offset = sum(
                selected_segs[j]["end"] - selected_segs[j]["start"]
                for j in range(pos)
            )
            kw_start = offset
            kw_end   = min(offset + cfg.keywords.display_duration, offset + seg_dur)
            keyword_events.append({
                "text":  kw["text"],
                "start": kw_start,
                "end":   kw_end,
                "size":  kw.get("size", cfg.keywords.font_size),
            })

    # ── 4. Generate .ass ──
    ass_path = os.path.join(tmp_dir, "subs.ass")
    if cfg.subtitles.enabled:
        make_ass(selected_segs, video_path, cfg, ass_path)
        print(f"  → Subtitles: {len(selected_segs)} events")

    # ── 5. Final pass: keywords + subtitles ──
    print(f"  → Final render: keywords + subtitles...")
    vf_parts = keyword_drawtext_filters(keyword_events, cfg, vinfo["height"])

    if cfg.subtitles.enabled:
        ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
        vf_parts.append(f"subtitles={ass_escaped}:fontsdir=/usr/share/fonts")

    if vf_parts:
        _ffmpeg([
            "-i", concat_out,
            "-vf", ",".join(vf_parts),
            "-c:v", "libx264", "-preset", cfg.output.preset,
            "-crf", str(cfg.output.quality_crf),
            "-c:a", "copy", output_path
        ], label="final-render")
    else:
        import shutil
        shutil.copy(concat_out, output_path)

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  → Output: {output_path} ({size_mb:.1f}MB, {concat_dur:.1f}s)")
    return output_path
