# Config Model

## Why configuration is central

This project treats configuration as a product capability, not just a developer convenience.

The main idea is:

- users should be able to create different analysis agents
- different agents should share one runtime framework
- the differences between agents should mostly live in structured configuration

## What is configurable

The current model is centered on three config layers:

### Agent Definition

Defines the agent itself:

- name
- description
- supported file types
- default flow
- clarification policy

### Semantic Config

Defines how the data should be interpreted:

- field catalog
- header mapping hints
- ambiguity rules
- metric definitions
- filter rules
- exclusion rules
- text semantic rules
- clarification cards

### Report Templates

Defines how results should be structured for output tasks such as monthly reports.

## Config Studio direction

The UI is intentionally a hybrid model:

- structured editable configuration
- natural-language assistant as a helper

Natural language is not the final storage format.

Instead, user input is translated into draft configuration that can be edited, saved, and versioned.

## What configuration can change

Within the current prototype direction, configuration is expected to handle:

- field meaning
- metric formulas
- filtering logic
- sample handling rules
- clarification prompts
- report templates

That makes the advertising-data agent a reusable template rather than a hardcoded one-off workflow.
