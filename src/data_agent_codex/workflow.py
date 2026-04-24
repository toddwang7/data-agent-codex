from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from .config_loader import AgentRuntimeConfig
from .executor import execute_monthly_report, execute_question_answering
from .intake import (
    classify_special_samples,
    extract_row_dicts,
    infer_reporting_months,
    inspect_workbook,
    map_headers,
    parse_date_range,
)
from .planner import generate_plan


def _header_index(headers: list[str]) -> dict[str, int]:
    return {header: index for index, header in enumerate(headers)}


def _build_clarification_cards(
    semantic_config: dict[str, Any],
    present_target_fields: set[str],
    reporting_months: dict[str, Any],
    special_samples: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    card_lookup = {card["card_id"]: dict(card) for card in semantic_config.get("clarification_cards", [])}

    reporting_month_card = card_lookup.get("reporting_month")
    if reporting_month_card:
        reporting_month_card["default_value"] = reporting_months.get("default")
        reporting_month_card["options"] = reporting_months.get("options", [])

    special_sample_card = card_lookup.get("special_sample_handling")
    if special_sample_card:
        special_sample_card["items"] = special_samples

    cards = []
    for step in sorted(semantic_config.get("clarification_flow", []), key=lambda item: item["step"]):
        card = card_lookup.get(step["card_id"])
        if not card:
            continue
        cards.append({"step": step["step"], **card})
    return cards


def run_intake_workflow(
    agent_config: AgentRuntimeConfig,
    file_paths: list[Path],
    task_type: str = "monthly_report",
    user_request: str | None = None,
    execute: bool = False,
    confirmation_state: dict[str, Any] | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    semantic_config = agent_config.semantic_config
    datasets = []
    overall_present_fields: set[str] = set()
    overall_special_samples: list[dict[str, Any]] = []
    month_candidates = []

    for file_path in file_paths:
        snapshot = inspect_workbook(file_path)
        mapping = map_headers(snapshot.headers, semantic_config.get("header_mapping_hints", []))
        _, row_dicts = extract_row_dicts(
            file_path,
            semantic_config.get("header_mapping_hints", []),
            limit=200,
        )

        parsed_ranges = []
        for row in row_dicts:
            parsed = parse_date_range(row.get("date"))
            if parsed:
                parsed_ranges.append(parsed)

        reporting_months = infer_reporting_months(file_path, parsed_ranges)
        month_candidates.extend(reporting_months["candidates"])

        present_fields = {item["target_field"] for item in mapping["recognized"]}
        overall_present_fields |= present_fields

        text_rule = semantic_config.get("text_semantic_rules", [{}])[0]
        special_samples = classify_special_samples(row_dicts, text_rule)
        overall_special_samples.extend(special_samples)

        datasets.append(
            {
                "file_name": file_path.name,
                "file_path": str(file_path),
                "sheet_name": "raw_data",
                "row_count": snapshot.max_row - 1,
                "column_count": snapshot.max_col,
                "header_mapping": mapping,
                "reporting_months": reporting_months,
                "parsed_time_range_examples": parsed_ranges[:5],
                "special_samples_preview": special_samples[:5],
            }
        )

    deduped_special_samples = []
    seen = set()
    for item in overall_special_samples:
        key = (item.get("classification"), item.get("adcode"), item.get("adslot"))
        if key in seen:
            continue
        seen.add(key)
        deduped_special_samples.append(item)

    unique_month_values = []
    seen_month_values = set()
    deduped_month_candidates = []
    seen_candidate_keys = set()
    for candidate in month_candidates:
        candidate_key = (candidate.get("source"), candidate.get("value"))
        if candidate_key not in seen_candidate_keys:
            deduped_month_candidates.append(candidate)
            seen_candidate_keys.add(candidate_key)
        value = candidate.get("value")
        if value and value not in seen_month_values:
            unique_month_values.append(value)
            seen_month_values.add(value)
    reporting_month_summary = {
        "default": unique_month_values[0] if len(unique_month_values) == 1 else None,
        "options": unique_month_values,
        "candidates": deduped_month_candidates,
    }

    clarification_cards = _build_clarification_cards(
        semantic_config=semantic_config,
        present_target_fields=overall_present_fields,
        reporting_months=reporting_month_summary,
        special_samples=deduped_special_samples[:10],
    )

    plan = generate_plan(
        runtime_config=agent_config,
        datasets=datasets,
        clarification_cards=clarification_cards,
        task_type=task_type,
        user_request=user_request,
    )

    result = {
        "agent_id": agent_config.agent["agent_id"],
        "task_flow": agent_config.agent["default_task_flow"],
        "datasets": datasets,
        "clarification_cards": clarification_cards,
        "plan": plan,
        "conversation_history": conversation_history or [],
    }
    if execute:
        if task_type == "question_answering":
            result["execution"] = execute_question_answering(
                runtime_config=agent_config,
                workflow_output=result,
                confirmation_state=confirmation_state,
                user_request=user_request,
            )
        else:
            result["execution"] = execute_monthly_report(
                runtime_config=agent_config,
                workflow_output=result,
                confirmation_state=confirmation_state,
            )
    return result
