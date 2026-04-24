# data-agent-codex
<img width="2874" height="1478" alt="image" src="https://github.com/user-attachments/assets/8ddf0090-f7a9-46da-a9ab-d0680ee6869a" />

A local-first, configurable data analysis agent prototype.

Current public demo status:
- the interactive demo is currently Chinese-only
- example workflows and UI copy are optimized for the Chinese ad-analysis scenario first

This repo focuses on:
- file upload intake (`xlsx`/`csv`)
- structured clarification -> plan -> execution flow
- monthly-report and free-form QA entry points
  <img width="1050" height="1462" alt="image" src="https://github.com/user-attachments/assets/217c65f2-7be7-4568-8b09-fcafc91d5ab4" />

- configurable agent semantics (fields, rules, templates)
  <img width="2876" height="1464" alt="image" src="https://github.com/user-attachments/assets/2adb3ec4-83f0-4260-82d9-a6ee5049e151" />

- local web UI + Python execution pipeline

## Current scope (v0.7.0)

- Multi-step workflow: upload -> clarification card -> plan review -> report
- Session records with isolated session state
- Config Studio with editable draft fields and local draft save
- Natural-language assistant input in Config Studio (parse/apply to draft)
- GLM-compatible LLM integration for final response generation
- Execution fallback visuals (charts/tables) even when LLM fails
- LLM-first query planning for free-form QA, with rule fallback only as backup
- Query plan / result / clarification / trace rendered directly in chat
- Clickable lightweight clarification options and follow-up suggestions
- Context-aware multi-turn QA memory across session history

## Project structure

- `src/data_agent_codex/`: Python workflow, planner, executor, web app, LLM client
- `prototype/`: frontend prototype (`index.html`, `app.js`, `styles.css`)
- `config/`: schemas + ad-analysis runtime config
- `docs/`: product and implementation design notes
- `tests/`: workflow tests

## Quick start

1. (Optional) create and activate a virtualenv.
2. Configure local env:
```bash
cp .env.example .env.local
```
3. Start the local web app:
```bash
PYTHONPATH=src python3 -m data_agent_codex.webapp
```
4. Open:
```bash
http://127.0.0.1:8765
```

## CLI usage

Run intake + planning:
```bash
PYTHONPATH=src python3 -m data_agent_codex.cli /path/to/file.xlsx
```

Run with execution preview:
```bash
PYTHONPATH=src python3 -m data_agent_codex.cli --execute /path/to/file.xlsx
```

## Environment variables

Configure in `.env.local`:
- `GLM_API_KEY`
- `GLM_MODEL` (example: `glm-4.5-air`)
- `GLM_BASE_URL` (optional; defaults to official endpoint)

See `.env.example` for template values.

## Notes

- Access the app through the web server URL; do not open `prototype/index.html` directly for full functionality.
- This is a prototype repository intended for iteration and portfolio demonstration.
- The current public demo is Chinese-only. Multi-language UX is not finished in this version.

## GitHub publishing

This project is suitable for GitHub-first sharing without deployment.

- use the repo as a local-first demo and portfolio project
- keep secrets in `.env.local` only
- publish iterative versions through commits and tags

See `RELEASE.md` for a simple first-publish flow.

## Docs

For a cleaner public reading path, start with:

- `docs/product-overview.md`
- `docs/architecture-overview.md`
- `docs/config-model.md`
- `docs/reporting-overview.md`
