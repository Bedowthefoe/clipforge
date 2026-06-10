# 11. Risks and Technical Debt

**Purpose:** Things we accepted to ship the POC + things we should watch.
**Last Updated:** 2026-06-09

---

## Technical Debt

| # | Title | Status | Impact | When to pay down |
|---|---|---|---|---|
| [001](../debt/001-cleanup-bug-fixed.md) | Cleanup overwrote full segments with correction substrings | ✅ Fixed | Was: massive timing artifacts. Now: surgical substring replace | Phase 1 — fixed during SESSION-04 |
| [002](../debt/002-highlight-reel-mode-bitrot-risk.md) | `highlight_reel` mode rarely exercised | 🟡 Live debt | Code paths could break silently | Phase 2 — re-validate when next used |
| [003](../debt/003-resegment-bisects-thai-words.md) | Pause-based resegment splits PyThaiNLP words | 🟡 Live debt | Orphan single-character events (e.g. ` แ`) at some boundaries | Phase 2 — implement F-004 |
| 004 | `/tmp/clipforge_*` tmp dirs never cleaned up | 🟡 Live debt | Disk grows over many runs | Add cleanup or use `tempfile.TemporaryDirectory` |
| 005 | Module-level `print()` for progress instead of logging | 🟡 Live debt | Can't easily redirect/filter; no severity levels | Phase 2 — switch to `logging` |
| 006 | No requirements.txt pin / no venv | 🟡 Live debt | System Python + `--break-system-packages` — fragile if any global update | Phase 2 — adopt uv venv |
| 007 | `cleanup_memory.md` empty and unused | 🟡 Live debt | Same Whisper errors get re-found every run | Phase 2 — implement F-001 |

---

## Risks (not yet realized issues)

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R-1 | `claude -p` CLI changes output format | Medium | High — breaks both cleanup + highlight passes | `--output-format json` + regex fallback; pinned by Anthropic |
| R-2 | PyThaiNLP newmm dictionary update changes word boundaries | Low | Medium — subtle subtitle layout drift | Pin pythainlp version in requirements.txt when we adopt it |
| R-3 | `claude -p` Pro plan credit budget exhausted mid-day | Low | Medium — pipeline blocks until next cycle | Monitor usage; consider parallel API tier if needed |
| R-4 | New Whisper version changes word-timestamp semantics | Low | Medium — Option E anchoring may misalign | Pin faster-whisper version; integration tests on every upgrade |
| R-5 | Client wants a creative effect we can't deliver (e.g. animated text, transitions) | Medium | Medium — scope grows | Document creative scope in product/strategy-framework.md; align early on each new content type |
| R-6 | Multiple creators want their own style profiles | Medium | Low (just config work) | F-002 in feature-pipeline.md |
| R-7 | Video gets uploaded with no speech / heavy music | High | Low (graceful fallback ok) | Phase 2 hardening: detect empty Whisper output, skip cleanup/highlight, render with no subs |
| R-8 | Tmp dir grows past disk limits | Medium | Medium — pipeline fails ungracefully | Add cron cleanup or fix in code (debt 004) |

---

## Operational Concerns

- **No automated tests** beyond the original validation script that proves capabilities work. Adding tests for the timing logic (`split_into_timed_lines`, `reconcile_event_timing`) would be high-value — these are pure functions with measurable outputs.
- **No CI.** Phase 2 should add at least a unit-test job for the deterministic stages (textwrap_th, cleanup substring logic, subtitle generation).
- **No version pinning in requirements.txt.** Will bite us when something upstream changes.
