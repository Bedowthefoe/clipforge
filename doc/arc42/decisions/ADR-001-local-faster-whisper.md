# ADR-001 — Local faster-whisper large-v3 for transcription

**Status:** Accepted
**Date:** 2026-05-24
**Deciders:** Operator

---

## Context

We need word-level Thai transcription with start/end timestamps to drive subtitle generation. Options considered:

| Option | Pros | Cons |
|---|---|---|
| Groq Whisper API (large-v3-turbo) | Fast (~real-time), accurate | Per-call cost; cloud dependency |
| OpenAI Whisper API | Most accurate | Cost; cloud dependency |
| WhisperX (with wav2vec2 alignment) | Tighter word timestamps | **Thai alignment model is broken** (upstream #737) |
| faster-whisper local large-v3 (int8) | Free; works on CPU; word timestamps | Slow (~10 min per min audio) |
| Thai-fine-tuned Whisper (e.g. biodatlab/whisper-th-large-v3) | Potentially more accurate for Thai | Untested; bigger memory footprint |

## Decision

Use **`faster-whisper` with `WhisperModel("large-v3", device="cpu", compute_type="int8")`** for transcription. Set `word_timestamps=True`. Cache transcripts to JSON for re-use across renders.

## Why

- **Zero per-call cost** (TC-3, QG-3). The operator's Pro plan covers Claude; Whisper has no API budget allocated.
- **No GPU available** (TC-1). int8 quantization makes large-v3 CPU-feasible (~3-4 GB RAM, ~10 min per minute audio).
- **Operator accepts the latency**: "10 min wait is fine for an influencer queue."
- **Best open-source Thai accuracy** at the size; ~95% CER on typical fitness speech.
- **WhisperX is banned** because the wav2vec2 Thai alignment model is broken — faster-whisper's word timestamps are sub-syllabic but reliable enough for anchoring (ADR-007).

## Consequences

- Whisper segment boundaries are silence-biased — Whisper extends the last token of a segment through pauses. This forced design choices in Stage 4 timing (Option D: ignore Whisper word END times).
- Initial run downloads ~1.5GB to `~/.cache/huggingface/hub/`. Subsequent runs reuse.
- Tone mark + sound-alike errors on ~5-10% of fast colloquial speech. Mitigated by ADR-005 (Claude cleanup pass).
- `--transcript existing.json` flag lets us skip Whisper for iteration on later stages (saves 10 min per attempt).

## Revisit triggers

- If we get a GPU host: switch to `device="cuda"`, drop `compute_type="int8"`. 100× speedup.
- If a Thai-fine-tuned faster-whisper-compatible model lands publicly with measurably better Thai CER: A/B test it.
- If Pro plan changes to include free STT: reconsider.
