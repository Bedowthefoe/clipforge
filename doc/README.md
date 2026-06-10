# Documentation

**[← Back to project root](../README.md)**

---

## Architecture (`arc42/`)

arc42 is a lightweight, structured format for architecture documentation. Each section has a specific role — don't add content to a section that belongs elsewhere.

→ [Browse arc42 documentation](arc42/README.md)

---

## Project Tracking (`project/`)

Living documents that track the current state of the project — what's decided, what's in progress, what's open.

→ [Browse project tracking](project/README.md)

---

## Product (`product/`)

Canonical definitions of the pipeline modes, target style, and content type assumptions. These define WHAT clipforge is supposed to produce — the architecture in `arc42/` defines HOW.

| File | Status |
|---|---|
| [strategy-framework.md](product/strategy-framework.md) | ✅ Active — overlay-only vs highlight-reel mode definitions |

---

## Session Logs (`sessions/`)

One file per working session — theme, what was done, decisions made, where session ended. New session = new file. Sessions are immutable once closed; carry-forward state lives in [HANDOFF.md](../HANDOFF.md).

→ [Browse sessions](sessions/)

---

## Technical Debt (`debt/`)

Known issues + workarounds we accepted to ship. Each file = one piece of debt with: what it is, why we accepted it, what's blocked by it, how to pay it down.
