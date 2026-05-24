"""Load and validate config.yaml. Provides typed access to all settings."""

import os
import yaml
from dataclasses import dataclass, field
from typing import Literal

DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")


@dataclass
class OutputConfig:
    target_duration: int = 45
    format: str = "mp4"
    quality_crf: int = 23
    preset: str = "fast"


@dataclass
class SubtitleConfig:
    enabled: bool = True
    font: str = "Noto Sans Thai"
    font_size: int = 48
    color_primary: str = "white"
    color_outline: str = "black"
    outline_width: int = 2
    shadow: int = 1
    position: str = "bottom"
    margin_bottom: int = 40


@dataclass
class KeywordConfig:
    enabled: bool = True
    count: int = 5
    font_size: int = 64
    color: str = "white"
    border_width: int = 3
    border_color: str = "black"
    position_y: str = "top_third"
    display_duration: float = 2.5


@dataclass
class ZoomConfig:
    enabled: bool = True
    count: int = 2
    duration: float = 2.5
    max_scale: float = 1.3
    speed: float = 0.004


@dataclass
class CuttingConfig:
    min_segment_duration: float = 1.0
    merge_gap: float = 0.4


@dataclass
class AIConfig:
    content_selection: str = "Select segments where the host is actively speaking."
    keyword_style: str = "English fitness terminology, 1-3 words each."
    content_language: str = "thai"
    keyword_language: str = "english"


@dataclass
class ClipforgeConfig:
    output: OutputConfig = field(default_factory=OutputConfig)
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
        output    = section(OutputConfig,   "output"),
        subtitles = section(SubtitleConfig, "subtitles"),
        keywords  = section(KeywordConfig,  "keywords"),
        zoom      = section(ZoomConfig,     "zoom"),
        cutting   = section(CuttingConfig,  "cutting"),
        ai        = section(AIConfig,       "ai"),
    )
