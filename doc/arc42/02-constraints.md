# 2. Constraints

**Purpose:** Non-negotiable boundaries every design decision has to fit within.
**Last Updated:** 2026-06-09

---

## Technical Constraints

| # | Constraint | Origin | Implication |
|---|---|---|---|
| TC-1 | Single Ubuntu host, no GPU | Operator's hardware (60GB RAM, CPU-only) | All ML inference must run on CPU. Whisper uses `int8` quantization. ~10 min/min audio. |
| TC-2 | Python 3.12 | Operator's system Python; matches other projects | All code is Python; dependencies are `pip install --break-system-packages` (no venv adopted yet) |
| TC-3 | No paid APIs beyond Pro plan | Cost goal (QG-3) | Whisper local, Claude via `claude -p` subprocess on Pro Agent SDK credits |
| TC-4 | FFmpeg subprocess for video | Reliability of filter graphs | `ffmpeg-python` is dead since 2019 — banned. We shell out to `ffmpeg` directly. |
| TC-5 | Output must be H.264 + AAC mp4 | Compatible with target platforms (TikTok, Reels, Shorts) | libx264 + AAC, `yuv420p`, ≤9:16 portrait |

## Organisational Constraints

| # | Constraint | Origin | Implication |
|---|---|---|---|
| OC-1 | Operator is a Solution Architect, not a developer | Self-described | Clear, named modules; readable code over clever. Heavy use of config.yaml for tuning. |
| OC-2 | Queue-based latency is acceptable | Client confirmed "10 min wait is fine" | Pipeline can take minutes per video — no need to optimize for sub-minute turnaround |
| OC-3 | Client-style sign-off via reference videos | The client edits manually today | We compare against client-provided target samples and adopt their style measurably |

## Conventions

| # | Constraint | Origin | Implication |
|---|---|---|---|
| CV-1 | Outputs never overwrite | Audit/incident learning | Timestamp every output: `{base}_{YYYYMMDD_HHMMSS}.mp4` + sidecar `_analysis.json` |
| CV-2 | No emojis in code or docs unless asked | Operator preference (global CLAUDE.md) | Clean ASCII-friendly markdown |
| CV-3 | No `Co-Authored-By: Claude` in commits | Operator preference (global CLAUDE.md) | Commits look like the operator's work |

---

## Banned Tools (Production Hazards)

These produce broken or unmaintainable output — do NOT use them:

| Tool | Why banned | Use instead |
|---|---|---|
| `ffmpeg-python` | Unmaintained since 2019; known bugs in filter expressions | `subprocess.run(["ffmpeg", ...])` directly |
| WhisperX for Thai | Upstream wav2vec2 Thai alignment model broken (issue #737) | `faster-whisper` with `word_timestamps=True` |
| `drawtext` for Thai text | FreeType without HarfBuzz → missing glyphs as boxes | libass `.ass` files (HarfBuzz shaping) |
| Prompt font (cadsondemak GitHub) for Thai subs | Only 5 GPOS lookups — tone marks collide with vowels | IBM Plex Sans Thai (15 GPOS lookups) — see ADR-009 |
| `claude -p` without `--output-format json` | Stdout drift, trailing text breaks JSON parse | Always `--output-format json` + regex fallback for robustness |

---

## libass + ffmpeg specifics

- libass on this host is ≥ 0.17.0 with `libunibreak` — `wrap_unicode` option works but we don't rely on it (Unicode line-break for Thai breaks anywhere; PyThaiNLP gives semantic breaks).
- libass uses HarfBuzz complex shaping by default — Thai mark stacking is correct as long as the font's GPOS tables are well-defined.
- FFmpeg subtitles filter: `subtitles=path.ass:fontsdir=/usr/share/fonts`. Fonts in `~/.fonts/` are picked up via fontconfig (libass falls back to it).
