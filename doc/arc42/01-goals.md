# 1. Introduction and Goals

**Purpose:** Establish what clipforge exists to do and how we judge whether it's doing it well.
**Last Updated:** 2026-06-09

---

## What Clipforge Is

A command-line video editor that turns a raw Thai-language fitness video into a finished short-form clip with **zero manual editing**:

```
raw.mp4 → clipforge → edited.mp4 (Thai subtitles + keyword popups + tight framing)
```

Target user: an **influencer / content creator** who records raw exercise demos and wants finished short-form (TikTok, Reels, Shorts) without a video editor in the loop.

---

## Functional Goals

| # | Goal | How we measure |
|---|---|---|
| FG-1 | Accurate Thai transcription with corrected STT errors | Whisper output + Claude cleanup pass; <5% character-level error rate after cleanup on typical fitness content |
| FG-2 | Subtitles that match the target creator's visual style | Side-by-side comparison with `target-font-screenshot.jpg`; subjective sign-off by client |
| FG-3 | Subtitle timing that follows the host's actual speech rhythm | Per-line Whisper-word anchoring; events shown 0.83s–2.5s each (Netflix-compliant) |
| FG-4 | Word-aware Thai line wrapping (no mid-word breaks) | PyThaiNLP newmm tokenization + `\N` line breaks |
| FG-5 | Topical keyword popups that highlight key moments | 3 AI-selected popups per ~45s video, Thai phrases, ~2.5s each |
| FG-6 | Subject-tight framing matching target reference | Programmatic skin-bbox measurement: subject fills ~55% of frame vertical |
| FG-7 | Full audit trail per run | Timestamped output + `_analysis.json` with all AI decisions and cleanup corrections |

---

## Quality Goals

| Priority | Quality | Concrete scenario |
|---|---|---|
| 1 | **Reproducibility** | Same input + same config + same prompts = same output. Outputs are timestamped, no overwrites. |
| 2 | **Local-first execution** | Runs on a single Ubuntu host with no cloud dependency for transcription or rendering. Internet only for `claude -p` (subscription bills). |
| 3 | **Cost predictability** | Zero per-job API spend beyond the existing Pro plan Agent SDK budget. No surprise GPU/cloud bills. |
| 4 | **Config-driven** | Editing parameters (font sizes, timing thresholds, AI prompts) live in `config.yaml` — client can tune without code changes. |
| 5 | **Honest output** | If the host paused mid-sentence, the subs go silent. We never invent text. Cleanup confidence is gated. |
| 6 | **Fail loud** | Wrong input or broken assumption → process exits non-zero with a clear message. No silent fallback to broken renders. |

---

## Stakeholders

| Role | Cares about | Concerns |
|---|---|---|
| **Creator (client "C")** | FG-1, FG-2, FG-3, FG-5, FG-6 | Output matches the style they manually edit today; one-shot workflow |
| **Operator (Nalloo)** | All FGs + all QGs | Reliability, no surprise costs, ability to iterate per-content-type |
| **Future viewers** | FG-1, FG-3 | Readable subs, accurate transcription, no flicker, sync with audio |

---

## What clipforge is NOT

- Not a general-purpose video editor — we optimize hard for Thai fitness short-form
- Not a cloud SaaS — local CLI tool for the foreseeable future
- Not a multilingual subtitle generator — Thai+EN loanwords only; the cleanup rules are Thai-fitness-specific
- Not a perfect lip-syncing renderer — text follows speech to the nearest Whisper word, not phoneme
