# Product Overview

## What this project is

Data Agent Codex is a local-first data analysis agent prototype.

It is designed around a simple product idea:

- users upload data files
- users ask for a monthly report or ask free-form questions
- the system does not jump straight into analysis
- it first clarifies scope, then proposes a plan, then produces output

## Current product shape

The current prototype uses a three-part workspace:

- left: agent and session navigation
- center: conversation and clarification flow
- right: report and result panel

This is not a generic chatbot shell. The product is organized as a task-oriented analysis workspace.

## Why it exists

The main problem it tries to solve is not "talking to a spreadsheet".

The real problem is:

- uploaded files often have ambiguous fields
- business rules are usually implicit
- users need confirmation before formal analysis
- reporting tasks and free-form QA should share one workflow

The prototype makes those hidden steps explicit.

## Current V1 scope

Included:

- file upload (`xlsx`, `xls`, `csv`)
- configurable analysis agent definition
- clarification cards before analysis
- structured plan review before report generation
- monthly-report and QA style entry points
- local Config Studio for editing draft configuration

Not included:

- database connections
- multi-tenant auth or permissions
- production deployment workflow
- full BI-style dashboard authoring

## First target scenario

The first concrete agent is an advertising-data analysis agent.

It supports:

- month-level reporting
- cross-month comparison
- cost and rate recalculation
- rule-driven filtering and sample handling

The design intentionally leaves room for other future agents such as sales, operations, or web behavior analysis.
