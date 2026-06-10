# Clipforge

AI-powered shell app for automatic video editing of Thai fitness short-form content. One raw take in, one finished mp4 out: word-accurate Thai subtitles, AI-selected pink keyword popups, baseline framing crop, drop-shadow type, no manual editing.

## Quick Start

```bash
python main.py input.mp4
# → test/<input>_<YYYYMMDD_HHMMSS>.mp4 + sidecar _analysis.json
```

Skip the 10-minute Whisper step with a cached transcript:

```bash
python main.py input.mp4 --transcript test/analysis/raw_xxx_transcript.json
```

## System Prerequisites

```bash
sudo apt install ffmpeg fonts-ibm-plex fonts-thai-tlwg fonts-noto
pip install --break-system-packages faster-whisper python-ass pythainlp pyyaml
```

`claude -p` CLI must be authenticated. Uses Pro plan Agent SDK credit.

## Documentation

- **[doc/](doc/)** — architecture, project tracking, product strategy, session logs
  - [arc42/](doc/arc42/) — architecture decisions, building blocks, runtime view
  - [project/ROADMAP.md](doc/project/ROADMAP.md) — phases + milestones
  - [project/learnings.md](doc/project/learnings.md) — reusable insights
- **[HANDOFF.md](HANDOFF.md)** — cross-session state, what's next, how to iterate
- [CLAUDE.md](CLAUDE.md) — assistant context for this project
- [POC_PLAN.md](POC_PLAN.md) — original POC scope (historical; superseded by `doc/`)

## Status

**Phase 1 — Reference Match: substantially complete.** Output matches client target on framing (~54% subject vertical fill), font style (IBM Plex Sans Thai loopless + drop shadow), subtitle timing (Netflix-compliant 0.83-2.5s, per-line speech-anchored), and Thai mark stacking.

**Phase 2 — Production Hardening: next.** See [HANDOFF.md](HANDOFF.md) for the pick-up-here list.
