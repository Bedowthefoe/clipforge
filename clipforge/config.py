"""Load and validate config.yaml. Provides typed access to all settings."""

import os
import yaml
from dataclasses import dataclass, field

DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")


@dataclass
class OutputConfig:
    target_duration: int = 45
    format: str = "mp4"
    quality_crf: int = 23
    preset: str = "fast"


@dataclass
class FramingConfig:
    enabled: bool = True
    baseline_zoom: float = 1.48
    crop_center_y: float = 0.56
    crop_center_x: float = 0.50


@dataclass
class SubtitleConfig:
    enabled: bool = True
    font: str = "Noto Sans Thai"
    font_size: int = 0
    color_primary: str = "white"
    color_outline: str = "white"
    outline_width: int = 0
    shadow: int = 10
    shadow_color: str = "000000"
    shadow_alpha: int = 60
    position: str = "bottom"
    margin_bottom: int = 400
    margin_horizontal: int = 50
    max_chars_per_line: int = 0
    max_lines: int = 1
    # ── Industry-standard timing (Netflix / TikTok short-form) ──
    min_event_duration: float = 0.83     # Netflix minimum: 5/6 s
    max_event_duration: float = 2.5      # short-form sweet-spot ceiling
    target_cps: float = 18.0             # Thai chars/sec — matches typical Thai speech rate
    inter_event_gap: float = 0.08        # ~2 frames @ 25fps — prevents flicker
    lead_time: float = 0.0               # show subs N seconds before speech (0 = aligned)
    # Option E: per-line anchoring to Whisper word START times for tighter speech sync.
    # When a line's anchor lands after the cumulative cursor, honor the gap (host paused).
    # Cap that gap at max_drift_correction so we don't open giant silent windows.
    anchor_to_whisper_words: bool = True
    max_drift_correction: float = 1.0    # max seconds of silence we'll insert at an anchor


@dataclass
class KeywordConfig:
    enabled: bool = True
    count: int = 3
    language: str = "th"
    display_duration: float = 2.5
    # popup style
    popup_font_size: int = 90
    popup_color: str = "white"
    popup_outline_color: str = "FF1493"
    popup_outline_width: int = 8
    popup_position: str = "top"
    popup_margin_top: int = 350
    # legacy fields kept for highlight_reel mode
    font_size: int = 64
    color: str = "white"
    border_width: int = 3
    border_color: str = "black"
    position_y: str = "top_third"


@dataclass
class ZoomConfig:
    enabled: bool = False
    count: int = 2
    duration: float = 2.5
    max_scale: float = 1.3
    speed: float = 0.004


@dataclass
class CuttingConfig:
    min_segment_duration: float = 1.0
    merge_gap: float = 0.4
    incomplete_opener_max_duration: float = 3.0
    # pause-based re-segmentation (overlay_only mode)
    resegment_max_duration: float = 5.0       # split any segment longer than this
    resegment_pause_gap: float = 0.4          # gap between tokens that triggers a split
    resegment_silent_token_dur: float = 1.0   # a single held token longer than this = silence
    resegment_min_duration: float = 0.4       # drop sub-segments shorter than this


@dataclass
class AIConfig:
    content_selection: str = "Select segments where the host is actively speaking."
    keyword_style: str = "Short Thai phrases (2-4 words) summarizing key moments."
    content_language: str = "thai"
    keyword_language: str = "thai"
    # ── Transcript cleanup pass (Claude proofreads Whisper output) ──
    cleanup_enabled: bool = True
    cleanup_topic_hint: str = "Thai fitness instructional video — bodyweight exercises, form cues, and technique tips."
    cleanup_min_confidence: str = "medium"  # high | medium | low


@dataclass
class ClipforgeConfig:
    mode: str = "overlay_only"
    output: OutputConfig = field(default_factory=OutputConfig)
    framing: FramingConfig = field(default_factory=FramingConfig)
    subtitles: SubtitleConfig = field(default_factory=SubtitleConfig)
    keywords: KeywordConfig = field(default_factory=KeywordConfig)
    zoom: ZoomConfig = field(default_factory=ZoomConfig)
    cutting: CuttingConfig = field(default_factory=CuttingConfig)
    ai: AIConfig = field(default_factory=AIConfig)


def load(path: str = DEFAULT_CONFIG) -> ClipforgeConfig:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found: {path}")

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    def section(cls, key):
        return cls(**{k: v for k, v in raw.get(key, {}).items()
                      if k in cls.__dataclass_fields__})

    return ClipforgeConfig(
        mode      = raw.get("mode", "overlay_only"),
        output    = section(OutputConfig,    "output"),
        framing   = section(FramingConfig,   "framing"),
        subtitles = section(SubtitleConfig,  "subtitles"),
        keywords  = section(KeywordConfig,   "keywords"),
        zoom      = section(ZoomConfig,      "zoom"),
        cutting   = section(CuttingConfig,   "cutting"),
        ai        = section(AIConfig,        "ai"),
    )
