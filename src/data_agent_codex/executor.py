from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .config_loader import AgentRuntimeConfig
from .intake import classify_special_samples, extract_row_dicts


def _safe_number(value: Any) -> float:
    if value in (None, "", "/"):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _resolve_confirmation_state(
    plan: dict[str, Any],
    clarification_cards: list[dict[str, Any]],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overrides = overrides or {}
    state = dict(overrides)
    card_lookup = {card["card_id"]: card for card in clarification_cards}

    if "reporting_month" not in state and "reporting_month" in card_lookup:
        options = card_lookup["reporting_month"].get("options", [])
        default_value = card_lookup["reporting_month"].get("default_value")
        if plan.get("task_variant") == "multi_month":
            state["reporting_month"] = options
        elif default_value:
            state["reporting_month"] = [default_value]
        elif options:
            state["reporting_month"] = [options[0]]

    if "cost_rule_confirmation" not in state:
        state["cost_rule_confirmation"] = True
    if "free_slot_handling" not in state:
        state["free_slot_handling"] = True
    if "special_sample_handling" not in state:
        state["special_sample_handling"] = "keep_warnings_exclude_hard_excludes"

    return state


def _compute_effective_cost(row: dict[str, Any]) -> float:
    placement_type = str(row.get("placement_type") or "")
    if "百度品专" in placement_type:
        return _safe_number(row.get("total_cost"))
    return _safe_number(row.get("net_total_price"))


def _special_sample_lookup(
    rows: list[dict[str, Any]],
    text_rule: dict[str, Any],
) -> dict[tuple[Any, Any], str]:
    classified = classify_special_samples(rows, text_rule, limit=len(rows))
    lookup: dict[tuple[Any, Any], str] = {}
    for item in classified:
        key = (item.get("adcode"), item.get("adslot"))
        lookup[key] = item["classification"]
    return lookup


def _group_key(row: dict[str, Any], placement_choice: str) -> str:
    if placement_choice == "点位名称":
        return str(row.get("placement_name") or "未识别")
    if placement_choice == "两者都使用":
        return f"{row.get('placement_type') or '未识别'} | {row.get('placement_name') or '未识别'}"
    return str(row.get("placement_type") or "未识别")


def _finalize_metrics(agg: dict[str, float]) -> dict[str, float]:
    pv = agg["pv"]
    click = agg["click"]
    arrivals = agg["arrivals"]
    valid_visitors = agg["valid_visitors"]
    high_intent = agg["high_intent_visitors"]

    result = {
        "pv": round(pv, 4),
        "click": round(click, 4),
        "arrivals": round(arrivals, 4),
        "valid_visitors": round(valid_visitors, 4),
        "high_intent_visitors": round(high_intent, 4),
        "effective_cost": round(agg["effective_cost"], 4),
        "ctr": round(agg["ctr_click"] / agg["ctr_pv"], 6) if agg["ctr_pv"] > 0 else None,
        "arrival_rate": round(arrivals / click, 6) if click > 0 else None,
        "valid_visitor_rate": round(valid_visitors / arrivals, 6) if arrivals > 0 else None,
        "high_intent_rate": round(high_intent / valid_visitors, 6) if valid_visitors > 0 else None,
        "cpm": round(agg["cpm_cost"] / agg["cpm_pv"] * 1000, 6) if agg["cpm_pv"] > 0 else None,
        "cpc": round(agg["cpc_cost"] / agg["cpc_click"], 6) if agg["cpc_click"] > 0 else None,
        "valid_visitor_cost": round(agg["cost_metric_cost"] / agg["cost_metric_valid"], 6)
        if agg["cost_metric_valid"] > 0
        else None,
        "high_intent_cost": round(agg["cost_metric_cost"] / agg["cost_metric_high_intent"], 6)
        if agg["cost_metric_high_intent"] > 0
        else None,
    }
    return result


def _empty_agg() -> dict[str, float]:
    return {
        "pv": 0.0,
        "click": 0.0,
        "arrivals": 0.0,
        "valid_visitors": 0.0,
        "high_intent_visitors": 0.0,
        "effective_cost": 0.0,
        "ctr_click": 0.0,
        "ctr_pv": 0.0,
        "cpm_cost": 0.0,
        "cpm_pv": 0.0,
        "cpc_cost": 0.0,
        "cpc_click": 0.0,
        "cost_metric_cost": 0.0,
        "cost_metric_valid": 0.0,
        "cost_metric_high_intent": 0.0,
    }


def execute_monthly_report(
    runtime_config: AgentRuntimeConfig,
    workflow_output: dict[str, Any],
    confirmation_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = workflow_output["plan"]
    clarification_cards = workflow_output["clarification_cards"]
    confirmation_state = _resolve_confirmation_state(plan, clarification_cards, confirmation_state)
    selected_months = set(confirmation_state.get("reporting_month", []))
    placement_choice = confirmation_state.get("placement_dimension_choice", "点位类型")

    semantic_config = runtime_config.semantic_config
    text_rule = semantic_config.get("text_semantic_rules", [{}])[0]
    mapping_hints = semantic_config.get("header_mapping_hints", [])

    by_month: dict[str, dict[str, float]] = defaultdict(_empty_agg)
    by_vehicle: dict[str, dict[str, float]] = defaultdict(_empty_agg)
    by_media: dict[str, dict[str, float]] = defaultdict(_empty_agg)
    by_placement: dict[str, dict[str, float]] = defaultdict(_empty_agg)

    execution_notes = []
    included_files = []
    total_rows = 0
    included_rows = 0

    for dataset in workflow_output["datasets"]:
        dataset_month = dataset["reporting_months"]["default"]
        if selected_months and dataset_month not in selected_months:
            continue
        file_path = Path(dataset["file_path"])
        _, rows = extract_row_dicts(file_path, mapping_hints, limit=None)
        special_lookup = _special_sample_lookup(rows, text_rule)
        included_files.append({"file_name": dataset["file_name"], "reporting_month": dataset_month})

        for row in rows:
            total_rows += 1
            url = str(row.get("landing_page_url") or "")
            if not url.startswith("https://www.ghac"):
                continue

            special_class = special_lookup.get((row.get("adcode"), row.get("adslot")))
            if special_class == "exclude":
                continue
            if (
                confirmation_state.get("special_sample_handling") == "exclude_warned_samples"
                and special_class == "include_with_warning"
            ):
                continue

            effective_cost = _compute_effective_cost(row)
            ad_type = str(row.get("ad_type") or "")
            is_free = ad_type == "FREE" and bool(confirmation_state.get("free_slot_handling", True))
            no_exposure_tracking = str(row.get("accept_dmp_exposure") or "") == "否" and effective_cost > 0
            no_click_tracking = str(row.get("accept_dmp_click") or "") == "否" and effective_cost > 0

            pv = _safe_number(row.get("pv"))
            click = _safe_number(row.get("click"))
            arrivals = _safe_number(row.get("arrivals"))
            valid_visitors = _safe_number(row.get("valid_visitors"))
            high_intent = _safe_number(row.get("high_intent_visitors"))

            group_targets = [
                by_month[dataset_month],
                by_vehicle[str(row.get("vehicle_model") or "未填写车型")],
                by_media[str(row.get("media_name") or "未识别媒体")],
                by_placement[_group_key(row, placement_choice)],
            ]

            for agg in group_targets:
                agg["pv"] += pv
                agg["click"] += click
                agg["arrivals"] += arrivals
                agg["valid_visitors"] += valid_visitors
                agg["high_intent_visitors"] += high_intent
                agg["effective_cost"] += effective_cost

                if not no_exposure_tracking:
                    agg["ctr_click"] += click
                    agg["ctr_pv"] += pv
                if not no_exposure_tracking and not is_free:
                    agg["cpm_cost"] += effective_cost
                    agg["cpm_pv"] += pv
                if not no_click_tracking and not is_free:
                    agg["cpc_cost"] += effective_cost
                    agg["cpc_click"] += click
                if not is_free:
                    agg["cost_metric_cost"] += effective_cost
                    agg["cost_metric_valid"] += valid_visitors
                    agg["cost_metric_high_intent"] += high_intent

            included_rows += 1

    if any(item["reporting_month"] for item in included_files):
        execution_notes.append("执行阶段按已选报告月份对应的数据文件进行汇总。")
    execution_notes.append("已应用 GHAC URL 过滤规则。")
    execution_notes.append("成本和率类指标均按当前执行口径重算，未直接使用源表现成结果列。")
    if confirmation_state.get("free_slot_handling", True):
        execution_notes.append("FREE 点位已排除出成本相关指标，但仍保留在规模类指标统计中。")
    else:
        execution_notes.append("FREE 点位当前保留在成本相关指标中，本结果仅用于探索性预览。")
    if confirmation_state.get("special_sample_handling") == "exclude_warned_samples":
        execution_notes.append("当前已尽量排除 include_with_warning 类型的特殊样本。")

    return {
        "status": "executed_preview",
        "assumed_confirmations": confirmation_state,
        "included_files": included_files,
        "row_stats": {
            "total_rows_scanned": total_rows,
            "rows_after_filters": included_rows,
        },
        "overview": {
            "by_month": {key: _finalize_metrics(value) for key, value in sorted(by_month.items())},
            "by_vehicle": {key: _finalize_metrics(value) for key, value in sorted(by_vehicle.items())},
            "top_media": {
                key: _finalize_metrics(value)
                for key, value in sorted(
                    by_media.items(),
                    key=lambda item: item[1]["effective_cost"],
                    reverse=True,
                )[:10]
            },
            "top_placements": {
                key: _finalize_metrics(value)
                for key, value in sorted(
                    by_placement.items(),
                    key=lambda item: item[1]["effective_cost"],
                    reverse=True,
                )[:10]
            },
        },
        "notes": execution_notes,
    }
