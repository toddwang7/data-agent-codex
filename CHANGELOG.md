# Changelog

## v0.7.0 - 2026-04-24

- Switched free-form QA to an LLM-first query planning flow with rule fallback.
- Added in-chat query plan rendering, structured result cards, lightweight clarification, and execution trace.
- Added clickable follow-up suggestions and clarification options in the QA flow.
- Improved multi-turn session memory by carrying agent-side structured understanding through conversation history.
- Extended QA test coverage for comparison, follow-up context, clarification, and contextual follow-up suggestions.

## v0.6.0 - 2026-04-23

- Added session records with isolated per-session state.
- Added staged report flow improvements and retry path for model failures.
- Added report-side visual blocks (charts/tables) from execution aggregates.
- Added collapsible process details in report metadata area.
- Added Config Studio editability, including draft fields, local draft persistence, and natural-language parse/apply controls.
- Added app version badge in sidebar brand area.
- Improved navigation behavior for sidebar and config module switching.

## v0.5.x

- Built the initial end-to-end local prototype: upload -> clarification -> plan -> execution preview.
- Connected local web UI with Python workflow runtime.
- Added GLM integration path for assistant/report generation.
