# CLAUDE.md — Car Search Notification App

This file is the source of truth for how Claude (or any AI assistant) should behave when working on this project. Read it fully before making any changes.

---

## Project Overview

A personal Streamlit app that monitors car listings via SerpAPI, compares results against user-defined criteria, and sends notifications when matches are found. Single user, no authentication. Full spec is in [STREAMLIT.md](STREAMLIT.md).

---

## Rule 1 — Always Update STREAMLIT.md

When any requirement is added, changed, or removed:

1. **Prepend a new row** to the changelog table at the top of `STREAMLIT.md` (newest entry first) with: date, bumped version number, plain-English summary of what changed and why.
2. **Update the relevant section(s)** in the spec body in place so the file always reflects current intended behavior.

Never leave the spec stale. Do this before or immediately after implementing the change — not as an afterthought.

---

## Rule 2 — Atomic Design: Scan Before You Build

All UI components live in `components/`. Before writing any UI element:

1. **Scan `components/` first.** Check if a valid component already exists that covers the need.
2. **Use it if it exists.** Never inline equivalent markup elsewhere in the codebase.
3. **Ask before creating.** If no suitable component exists, confirm with the user before writing a new one.

This keeps the component library DRY and prevents the UI from drifting inconsistently.

---

## Rule 3 — Color & Styling Constraints

| Role | Color | Hex |
|---|---|---|
| Accent / CTA | Teal | `#009688` |
| Accent hover | Dark Teal | `#00796B` |
| Background | White | `#FFFFFF` |
| Surface / Card | Light Gray | `#F5F5F5` |
| Border | Medium Gray | `#E0E0E0` |
| Body text | Dark Gray | `#212121` |
| Secondary text | Medium Gray | `#757575` |
| **Success** | Green | `#4CAF50` — status only |
| **Warning** | Amber | `#FFC107` — status only |
| **Error** | Red | `#F44336` — status only |

**Red, amber, and green are reserved exclusively for success/warning/error indicators.** They must not appear anywhere else — not in buttons, backgrounds, accents, charts, or decorative elements.

---

## Rule 4 — Security Practices

- **No secrets in code.** API keys (SerpAPI, Pushover) live in `data/settings.json` which is gitignored. Never hardcode keys anywhere.
- **`data/settings.json` is gitignored.** `data/settings.example.json` (with empty strings) is the committed template.
- **HTTPS only.** All outbound requests use HTTPS. Never disable SSL certificate validation.
- **No `eval` or dynamic code execution.**
- **Input sanitization.** Strip and validate all user inputs before writing to JSON or building query strings.
- **File locking.** Use `filelock` for all JSON reads/writes to prevent race conditions between the APScheduler background thread and the Streamlit UI thread.
- **Logging.** Use Python's `logging` module with a rotating file handler (`logs/app.log`). Never log API keys, tokens, or user-identifiable data. Never use `print` for operational output.
- **Dependency audits.** Run `pip-audit` before any release or significant dependency change.

---

## Rule 5 — Python Best Practices

- **Python 3.11+.**
- **Type hints** on all function signatures.
- **Pydantic v2 models** for all JSON schema objects (Criterion, Match, Schedule, Settings). Validate on load.
- **No silent failures.** Wrap all network calls (SerpAPI, Pushover) in try/except. Surface errors to the user via the `StatusIndicator` component (red state). Never crash the UI on an API failure.
- **No comments that explain what the code does** — only add a comment when the *why* is non-obvious (a hidden constraint, a workaround, a subtle invariant).
- **No unused imports, dead code, or backwards-compatibility shims.**

---

## Key Files

| Path | Purpose |
|---|---|
| `STREAMLIT.md` | Full app spec + changelog |
| `CLAUDE.md` | This file — AI working rules |
| `app.py` | Entry point, sidebar nav, scheduler boot |
| `components/` | Atomic reusable UI widgets |
| `pages/home.py` | Home page |
| `pages/criteria.py` | Search Criteria page |
| `services/search.py` | SerpAPI integration & batching |
| `services/filter.py` | Local filter engine |
| `services/notify.py` | Pushover + in-app badge |
| `services/scheduler.py` | APScheduler setup |
| `services/storage.py` | JSON read/write helpers |
| `data/settings.json` | Secrets — **gitignored** |
| `.streamlit/config.toml` | Streamlit theme config |
