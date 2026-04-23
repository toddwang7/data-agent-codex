# Architecture Overview

## Core runtime flow

The prototype follows one primary flow:

1. file intake
2. field recognition
3. clarification
4. plan generation
5. execution
6. report output

This structure is shared by both monthly-report requests and general analysis questions.

## Main runtime modules

### File Intake

Reads uploaded workbooks or CSV files, extracts headers, samples rows, and identifies likely reporting-month candidates.

### Semantic Resolver

Maps raw headers into normalized field semantics based on config, instead of relying on free-form model guessing.

### Clarification Engine

Builds confirmation cards for decisions that should not be guessed, such as reporting month or special sample handling.

### Planner

Turns the user request plus clarification context into a structured plan. The plan is shown before final report generation.

### Executor

Runs the configured analysis logic:

- filtering
- sample exclusion
- metric recomputation
- grouped aggregation

### Report / Response Layer

Uses execution output to populate the right-side report panel. When LLM generation is available, it also produces a more natural summary response.

## Local app structure

The prototype is split across:

- `prototype/`: browser UI
- `src/data_agent_codex/`: Python runtime
- `config/`: agent and semantic config

This keeps product behavior, execution logic, and business configuration separate.

## Why this architecture matters

The system is intentionally not built as "one giant prompt".

Instead, it separates:

- deterministic configuration
- execution rules
- conversation flow
- LLM-generated presentation

That separation is what makes the prototype more reusable across future analysis agents.
