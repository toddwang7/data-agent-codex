# Reporting Overview

## Two output modes

The prototype supports two related but different output modes:

- monthly report generation
- free-form question answering

They share the same intake and clarification flow, but they do not have the same output requirements.

## Monthly report flow

A monthly report should not be generated immediately after the user types "generate report".

The intended sequence is:

1. user request
2. clarification card
3. plan confirmation
4. final report generation

This protects against silent assumptions in business-sensitive analysis.

## Report output shape

The right panel is treated as the final result area, not a running debug console.

Its role is to hold:

- structured report sections
- charts and tables from execution output
- process details that can be expanded if needed

The main content should stay focused on the final work product.

## Why execution visuals matter

The prototype now renders visuals from deterministic execution output, not only from LLM text.

That means the report panel can still show useful results when model generation fails or times out.

## Advertising-data reporting

For the first target agent, reporting emphasizes:

- month-level and cross-month comparison
- recomputed cost and rate metrics
- breakdown by vehicle, media, and placement type
- explicit treatment of special samples and non-monitorable rows

This is why reporting is modeled as a first-class task type rather than just another chat response style.
