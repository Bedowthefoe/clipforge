# 3. System Context and Scope

**Purpose:** What's inside clipforge, what's outside, who talks to whom.
**Last Updated:** 2026-06-09

---

## System Boundary

```
                ┌──────────────────────────────────────────────────┐
                │                  clipforge                       │
                │                                                  │
   raw.mp4 ──→  │   transcribe → cleanup → highlight → editor      │ ──→ edited.mp4
                │       │           │          │           │       │ ──→ _analysis.json
                │       ↓           ↓          ↓           ↓       │
                │   Whisper    Claude        Claude     FFmpeg     │
                │   (local)    (cloud)       (cloud)    (local)    │
                │                                                  │
                │           config.yaml (read at boot)             │
                └──────────────────────────────────────────────────┘
```

Everything inside the box is clipforge code. Everything outside is an external service or operator concern.

---

## External Actors

| Actor | Direction | Channel | Purpose |
|---|---|---|---|
| **Operator (Nalloo)** | in | CLI `python main.py input.mp4 [...]` | Invoke a render |
| **Operator** | in | `config.yaml` | Tune subtitle style, AI prompts, timing thresholds |
| **Creator (client "C")** | in | Reference videos in `test/` | Provide target-style samples we compare against |
| **Creator** | out | `edited.mp4` | Final video for posting |
| **faster-whisper model files** | in | `~/.cache/huggingface/hub/` | ~1.5GB large-v3 weights, downloaded on first run |
| **Anthropic / `claude -p`** | both | subprocess over HTTPS | Cleanup transcript; pick keyword popups |
| **fontconfig + libass** | in | `/usr/share/fonts/`, `~/.fonts/` | Resolve font names (e.g. "IBM Plex Sans Thai") |

---

## Inputs

| Artifact | Source | Format | Notes |
|---|---|---|---|
| Raw video | Operator drops in `test/` | mp4 (H.264 / portrait 9:16 typically) | Currently 30–60s; longer videos untested |
| `config.yaml` | Operator-edited | YAML | Loaded by `clipforge/config.py` at boot |
| `cleanup_rules.md` | Curated | Markdown | Static guidance fed into cleanup-pass Claude prompt |
| `cleanup_memory.md` | Curated, grows over runs | Markdown | Confirmed lessons learned; user appends after review |
| `target-font-screenshot.jpg` | Client | jpeg | Reference for visual style judging |

## Outputs

| Artifact | Location | Format | Notes |
|---|---|---|---|
| Edited video | `test/{base}_{YYYYMMDD_HHMMSS}.mp4` | mp4 | Subs burned-in, popups burned-in, baseline crop applied |
| Analysis JSON | `test/{base}_{YYYYMMDD_HHMMSS}_analysis.json` | JSON | All AI decisions, cleanup corrections with confidence + apply_method, run metadata |
| Tmp artifacts | `/tmp/clipforge_{YYYYMMDD_HHMMSS}_*/` | various | Audio extract, generated `.ass`, intermediate clips. Not cleaned up automatically. |

---

## Scope Exclusions (Confirmed Out for POC)

- Sound effects mixing — needs SFX library + matching logic; deferred to Phase 2
- HeyGen / AI avatars — Enterprise API cost; deferred to Phase 3
- Google Drive / n8n / cloud orchestration — Phase 2
- Multi-language support beyond Thai (+ English loanwords as-is) — out of scope; cleanup rules are Thai-fitness-specific
- A user interface — CLI only forever (or until product calls for it)
- Real-time / live streaming — batch only

See [project/ROADMAP.md](../project/ROADMAP.md) for what's in each phase.
