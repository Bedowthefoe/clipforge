# ADR-002 — `claude -p` subprocess for LLM passes

**Status:** Accepted
**Date:** 2026-05-24
**Deciders:** Operator

---

## Context

We need an LLM for two distinct passes:
1. **Cleanup** — proofread Whisper Thai transcript, fix obvious STT errors
2. **Highlight** — pick 3 Thai keyword popups + their timestamps

Both need cloud-scale models. The operator has an **Anthropic Pro plan** (not API credit). Options:

| Option | Pros | Cons |
|---|---|---|
| `ANTHROPIC_API_KEY` + Python SDK | Standard; tooling rich | Bills against API credit, not Pro plan |
| Local LLM via Ollama / llama.cpp | No cost | No model is good enough at Thai colloquial proofreading at our budget; would need ~70B+ |
| `claude -p` subprocess | Uses Pro plan Agent SDK credit; no API key needed | Stdout parsing; per-call latency includes process startup |
| Skip LLM, use heuristics | Simple | Insufficient for cleanup quality and popup phrasing |

## Decision

Call **`claude -p PROMPT --output-format json`** as a Python subprocess. Parse `outer["result"]` for the model's text, then `json.loads` it (with regex fallback for trailing text). Use timeouts (~120s default).

```python
r = subprocess.run(
    ["claude", "-p", prompt, "--output-format", "json"],
    capture_output=True, text=True, timeout=timeout,
)
outer = json.loads(r.stdout)
result = outer.get("result", r.stdout)
return re.sub(r"```json\s*|\s*```", "", result).strip()
```

## Why

- **Bills against Pro plan Agent SDK credit budget** — no separate API spend (TC-3, QG-3).
- **No API key management** — `claude` CLI handles auth.
- **Stable contract** — JSON-mode output is reliable across model versions.
- **Self-contained agent prompts** — each call is fully specified by its prompt; no SDK state.

## Consequences

- Per-call latency is dominated by model thinking time (25-60s), with ~1-2s process startup overhead.
- Stdout robustness: Claude sometimes appends trailing text after JSON → we use a regex fallback to extract the first `{...}` block.
- No streaming, no tool-use loops — each call is one prompt → one JSON. Acceptable for current scope.
- If the CLI changes its output format we'd need to update parsing. Mitigated by `--output-format json` flag (stable since 2025).

## Revisit triggers

- If Anthropic introduces a "Pro plan API key" — switch to SDK for cleaner integration.
- If we need streaming or multi-turn agent loops (e.g. Claude calling tools mid-pass) — re-evaluate.
- If `claude -p` latency becomes a bottleneck for batch processing — consider running calls in parallel via subprocess pool.
