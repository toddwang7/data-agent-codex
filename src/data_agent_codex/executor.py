from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
from typing import Any

from .config_loader import AgentRuntimeConfig
from .intake import classify_special_samples, extract_row_dicts
from .llm import llm_is_configured, plan_query_with_llm


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


def _build_default_metrics(entry: dict[str, Any]) -> list[str]:
    metrics = []
    if entry.get("high_intent_cost") is not None:
        metrics.append(f"高意向成本 {entry['high_intent_cost']:.2f}")
    if entry.get("valid_visitor_cost") is not None:
        metrics.append(f"有效访客成本 {entry['valid_visitor_cost']:.2f}")
    if entry.get("ctr") is not None:
        metrics.append(f"点击率 {entry['ctr'] * 100:.2f}%")
    return metrics


def _finalize_mapping(source: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
    return {key: _finalize_metrics(value) for key, value in sorted(source.items())}


def _contains_any(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _infer_metric_key(question: str) -> tuple[str, str]:
    if _contains_any(question, ["高意向成本", "高意向访客成本", "成本"]):
        return "high_intent_cost", "高意向成本"
    if _contains_any(question, ["有效访客成本"]):
        return "valid_visitor_cost", "有效访客成本"
    if _contains_any(question, ["点击率", "ctr"]):
        return "ctr", "点击率"
    if _contains_any(question, ["cpm"]):
        return "cpm", "CPM"
    if _contains_any(question, ["cpc"]):
        return "cpc", "CPC"
    if _contains_any(question, ["曝光", "pv"]):
        return "pv", "曝光PV"
    if _contains_any(question, ["点击", "click"]):
        return "click", "点击"
    return "high_intent_cost", "高意向成本"


def _question_mentions_metric(question: str) -> bool:
    return _contains_any(
        question,
        [
            "高意向成本",
            "高意向访客成本",
            "成本",
            "有效访客成本",
            "点击率",
            "ctr",
            "cpm",
            "cpc",
            "曝光",
            "pv",
            "点击",
            "click",
        ],
    )


def _metric_display(value: Any, metric_label: str) -> str:
    if value is None:
        return "暂无可用值"
    if metric_label == "点击率":
        return f"{value * 100:.2f}%"
    return f"{value:.2f}" if isinstance(value, float) else str(value)


def _extract_dimension_term(question: str, candidates: list[str]) -> str | None:
    for candidate in sorted(candidates, key=len, reverse=True):
        if candidate and candidate in question:
            return candidate
    return None


def _extract_month(question: str, available_months: list[str]) -> str | None:
    match = re.search(r"(20\d{2}-\d{2})", question)
    if match and match.group(1) in available_months:
        return match.group(1)
    return None


def _infer_query_goal(question: str) -> tuple[str, str]:
    normalized = question.strip()
    if _contains_any(normalized, ["有没有", "是否", "有无", "有投", "投没投", "有没有投"]):
        return "confirm_presence", "确认某个范围内是否存在投放或数据"
    if _contains_any(normalized, ["最高", "最低", "最好", "最差", "对比", "比较", "排行", "排名"]):
        return "compare_entities", "比较不同对象在某个指标上的表现"
    if _contains_any(normalized, ["哪些", "分别", "表现", "分布", "拆解", "构成", "明细"]):
        return "inspect_breakdown", "查看某个范围内按维度拆解后的表现"
    if _contains_any(normalized, ["多少", "是多少", "几", "多高", "多低"]):
        return "retrieve_value", "获取一个明确指标值"
    return "retrieve_value", "获取当前范围下的关键指标值"


def _goal_description(goal: str) -> str:
    mapping = {
        "confirm_presence": "确认某个范围内是否存在投放或数据",
        "compare_entities": "比较不同对象在某个指标上的表现",
        "inspect_breakdown": "查看某个范围内按维度拆解后的表现",
        "retrieve_value": "获取一个明确指标值",
    }
    return mapping.get(goal, "获取当前范围下的关键指标值")


def _infer_requested_dimensions(question: str, filters: dict[str, Any]) -> list[str]:
    mentions_media = _contains_any(question, ["媒体", "渠道"])
    mentions_placement = _contains_any(question, ["点位", "点位类型"])
    mentions_vehicle = _contains_any(question, ["车型"])
    mentions_month = _contains_any(question, ["月份", "月"])

    requested_dimensions: list[str] = []
    if mentions_month and not filters["month"]:
        requested_dimensions.append("month")
    if mentions_vehicle and not filters["vehicle"]:
        requested_dimensions.append("vehicle")
    if mentions_media and not filters["media"]:
        requested_dimensions.append("media")
    if mentions_placement and not filters["placement"]:
        requested_dimensions.append("placement")
    return requested_dimensions


def _drop_inherited_filters_for_requested_dimensions(
    filters: dict[str, Any],
    requested_dimensions: list[str],
) -> dict[str, Any]:
    adjusted = dict(filters)
    for dimension in requested_dimensions:
        # 如果当前追问是在切换分析维度，例如“按媒体呢”，
        # 就不应继续沿用同维度的旧过滤条件。
        if dimension in adjusted:
            adjusted[dimension] = None
    return adjusted


def _infer_requested_limit(question: str) -> int:
    match = re.search(r"(?:top|TOP|前)(\d+)", question)
    if match:
        try:
            return max(1, min(int(match.group(1)), 20))
        except ValueError:
            return 8
    cn_match = re.search(r"前([一二两三四五六七八九十])(?:个|名)?", question)
    if cn_match:
        cn_map = {
            "一": 1,
            "二": 2,
            "两": 2,
            "三": 3,
            "四": 4,
            "五": 5,
            "六": 6,
            "七": 7,
            "八": 8,
            "九": 9,
            "十": 10,
        }
        return cn_map.get(cn_match.group(1), 8)
    if _contains_any(question, ["第一", "第一个", "倒数第一"]):
        return 1
    return 8


def _infer_sort_direction(question: str) -> str:
    if _contains_any(question, ["最低", "最差", "最小", "倒数"]):
        return "asc"
    return "desc"


def _is_follow_up_question(question: str) -> bool:
    stripped = question.strip()
    return (
        len(stripped) <= 14
        or stripped.startswith(("那", "那么", "那如果", "那再", "那这个", "那"))
        or stripped.endswith(("呢", "吗"))
    )


def _infer_query_spec(
    user_request: str | None,
    query_context: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if not user_request:
        return None
    question = user_request.strip()
    if not question:
        return None

    metric_key, metric_label = _infer_metric_key(question)
    months = query_context.get("months", [])
    vehicles = query_context.get("vehicles", [])
    medias = query_context.get("medias", [])
    placements = query_context.get("placements", [])

    filters = {
        "month": _extract_month(question, months),
        "vehicle": _extract_dimension_term(question, vehicles),
        "media": _extract_dimension_term(question, medias),
        "placement": _extract_dimension_term(question, placements),
    }

    goal, goal_description = _infer_query_goal(question)
    requested_dimensions = _infer_requested_dimensions(question, filters)
    sort_direction = _infer_sort_direction(question)
    limit = _infer_requested_limit(question)

    prior_user_messages = [
        item.get("text", "")
        for item in (conversation_history or [])
        if item.get("role") == "user" and item.get("text")
    ]
    if prior_user_messages:
        previous_question = prior_user_messages[-1]
        previous_spec = _infer_query_spec(previous_question, query_context, None)
    else:
        previous_spec = None

    if previous_spec and _is_follow_up_question(question):
        if not _question_mentions_metric(question):
            metric_key = previous_spec["metric_key"]
            metric_label = previous_spec["metric_label"]
        for key in filters:
            if not filters[key]:
                filters[key] = previous_spec.get("filters", {}).get(key)
        if not requested_dimensions:
            requested_dimensions = previous_spec.get("requested_dimensions", [])
        else:
            filters = _drop_inherited_filters_for_requested_dimensions(filters, requested_dimensions)
        if goal == "retrieve_value" and previous_spec.get("goal") in {"inspect_breakdown", "compare_entities"}:
            goal = previous_spec["goal"]
            goal_description = _goal_description(goal)
        if goal == "compare_entities" and not requested_dimensions:
            requested_dimensions = previous_spec.get("requested_dimensions", [])
        if "前" not in question and not re.search(r"(?:top|TOP)\d+", question) and previous_spec.get("limit"):
            limit = previous_spec["limit"] if goal == previous_spec.get("goal") else limit
        if sort_direction == "desc" and _contains_any(question, ["哪个", "哪个更高", "哪个更低", "谁更高", "谁更低"]):
            sort_direction = previous_spec.get("sort_direction", sort_direction)

    group_by = requested_dimensions[0] if requested_dimensions else None
    secondary_group_by = requested_dimensions[1] if len(requested_dimensions) > 1 else None
    intent = {
        "confirm_presence": "existence",
        "inspect_breakdown": "breakdown",
        "compare_entities": "comparison",
        "retrieve_value": "value",
    }[goal]

    interpretation_parts = []
    if any(filters.values()):
        interpretation_parts.append(
            "筛选范围：" + " / ".join([value for value in filters.values() if value])
        )
    if requested_dimensions:
        interpretation_parts.append(
            "关注维度：" + " + ".join(requested_dimensions)
        )
    interpretation_parts.append(f"分析目标：{goal_description}")

    return {
        "question": question,
        "goal": goal,
        "intent": intent,
        "metric_key": metric_key,
        "metric_label": metric_label,
        "filters": filters,
        "group_by": group_by,
        "secondary_group_by": secondary_group_by,
        "requested_dimensions": requested_dimensions,
        "sort_direction": sort_direction,
        "limit": limit,
        "interpretation": "；".join(interpretation_parts),
    }


def _filter_cube_rows(cube_rows: list[dict[str, Any]], query_spec: dict[str, Any]) -> list[dict[str, Any]]:
    filters = query_spec.get("filters", {})
    filtered = cube_rows
    for key in ("month", "vehicle", "media", "placement"):
        value = filters.get(key)
        if value:
            filtered = [row for row in filtered if row.get(key) == value]
    return filtered


def _aggregate_cube_rows(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not rows:
        return None
    agg = _empty_agg()
    for row in rows:
        for key in agg:
            agg[key] += row.get(key, 0.0)
    return _finalize_metrics(agg)


def _group_cube_rows(rows: list[dict[str, Any]], group_by: str) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, float]] = defaultdict(_empty_agg)
    for row in rows:
        label = str(row.get(group_by) or "未识别")
        for key in grouped[label]:
            grouped[label][key] += row.get(key, 0.0)
    return [
        {
            "label": label,
            **_finalize_metrics(value),
        }
        for label, value in sorted(grouped.items(), key=lambda item: item[1]["effective_cost"], reverse=True)
    ]


def _group_cube_rows_nested(
    rows: list[dict[str, Any]],
    primary_group_by: str,
    secondary_group_by: str,
) -> list[dict[str, Any]]:
    primary_entries = _group_cube_rows(rows, primary_group_by)
    nested_entries = []
    for primary in primary_entries:
        primary_label = primary["label"]
        child_rows = [row for row in rows if str(row.get(primary_group_by) or "未识别") == primary_label]
        children = _group_cube_rows(child_rows, secondary_group_by)[:8]
        nested_entries.append(
            {
                **primary,
                "children": children,
            }
        )
    return nested_entries


def _build_scope_title(query_spec: dict[str, Any]) -> str:
    filters = query_spec.get("filters", {})
    labels = [filters.get("month"), filters.get("vehicle"), filters.get("media"), filters.get("placement")]
    joined = " / ".join([label for label in labels if label])
    return joined or "当前筛选范围"


def _sort_breakdown_entries(
    entries: list[dict[str, Any]],
    metric_key: str,
    goal: str,
    sort_direction: str,
) -> list[dict[str, Any]]:
    if goal != "compare_entities":
        return entries

    def _sort_value(entry: dict[str, Any]) -> float:
        value = entry.get(metric_key)
        return float(value) if isinstance(value, (int, float)) and value is not None else -1.0

    return sorted(entries, key=_sort_value, reverse=(sort_direction != "asc"))


def _execute_query_spec(
    query_spec: dict[str, Any] | None,
    cube_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if not query_spec:
        return None

    filtered_rows = _filter_cube_rows(cube_rows, query_spec)
    metric_key = query_spec["metric_key"]
    metric_label = query_spec["metric_label"]
    scope_title = _build_scope_title(query_spec)
    result_limit = query_spec.get("limit", 8)
    trace_steps = [
        {"step": "理解问题", "detail": query_spec.get("interpretation", "已解析问题意图。")},
        {"step": "筛选数据", "detail": f"命中过滤后的组合行数：{len(filtered_rows)}"},
    ]

    if query_spec.get("needs_clarification"):
        clarification_question = query_spec.get("clarification_question") or "当前问题还需要进一步确认。"
        return {
            "mode": "clarification_needed",
            "title": "需要进一步确认",
            "answer_text": clarification_question,
            "metric_key": metric_key,
            "metric_label": metric_label,
            "entries": [],
            "clarification_options": query_spec.get("clarification_options", []),
            "trace_steps": trace_steps + [{"step": "等待确认", "detail": clarification_question}],
            "query_spec": query_spec,
        }

    if query_spec["intent"] == "existence":
        exists = len(filtered_rows) > 0
        answer_text = f"{scope_title}存在相关投放数据。" if exists else f"{scope_title}没有匹配到相关投放数据。"
        return {
            "mode": "existence",
            "title": f"{scope_title} 是否存在",
            "answer_text": answer_text,
            "metric_key": metric_key,
            "metric_label": metric_label,
            "entries": [],
            "exists": exists,
            "trace_steps": trace_steps + [{"step": "存在性判断", "detail": "已根据当前过滤范围判断是否存在相关数据。"}],
            "query_spec": query_spec,
        }

    if query_spec["intent"] == "comparison" and query_spec.get("group_by"):
        if query_spec.get("secondary_group_by"):
            entries = _group_cube_rows_nested(
                filtered_rows,
                query_spec["group_by"],
                query_spec["secondary_group_by"],
            )
        else:
            entries = _group_cube_rows(filtered_rows, query_spec["group_by"])
        entries = _sort_breakdown_entries(
            entries,
            metric_key,
            query_spec.get("goal", ""),
            query_spec.get("sort_direction", "desc"),
        )[:result_limit]
        if not entries:
            return {
                "mode": "empty",
                "title": f"{scope_title} 对比结果",
                "answer_text": f"{scope_title}没有匹配到可比较的数据。",
                "metric_key": metric_key,
                "metric_label": metric_label,
                "entries": [],
                "query_spec": query_spec,
            }
        top_entry = entries[0]
        return {
            "mode": "comparison",
            "title": f"{scope_title} 按{query_spec['group_by']}对比",
            "answer_text": (
                f"{scope_title}按{query_spec['group_by']}对比后，{top_entry['label']}"
                f"{'当前最低' if query_spec.get('sort_direction') == 'asc' else '当前最突出'}，"
                f"{metric_label}为 {_metric_display(top_entry.get(metric_key), metric_label)}。"
            ),
            "metric_key": metric_key,
            "metric_label": metric_label,
            "entries": entries,
            "trace_steps": trace_steps + [{
                "step": "生成对比",
                "detail": f"按 {query_spec['group_by']} 聚合，并按 {metric_label} 做 {'升序' if query_spec.get('sort_direction') == 'asc' else '降序'}排序。",
            }],
            "query_spec": query_spec,
        }

    if query_spec.get("group_by"):
        if query_spec.get("secondary_group_by"):
            entries = _group_cube_rows_nested(
                filtered_rows,
                query_spec["group_by"],
                query_spec["secondary_group_by"],
            )[:result_limit]
        else:
            entries = _group_cube_rows(filtered_rows, query_spec["group_by"])[:result_limit]
        if not entries:
            return {
                "mode": "empty",
                "title": f"{scope_title} 查询结果",
                "answer_text": f"{scope_title}没有匹配到可用数据。",
                "metric_key": metric_key,
                "metric_label": metric_label,
                "entries": [],
                "query_spec": query_spec,
            }
        top_entry = entries[0]
        if query_spec.get("secondary_group_by"):
            answer_text = (
                f"{scope_title}先按{query_spec['group_by']}拆解，再看{query_spec['secondary_group_by']}细分，"
                f"{top_entry['label']}最值得关注，{metric_label}为 {_metric_display(top_entry.get(metric_key), metric_label)}。"
            )
        else:
            answer_text = (
                f"{scope_title}按{query_spec['group_by']}拆解后，{top_entry['label']}最值得关注，"
                f"{metric_label}为 {_metric_display(top_entry.get(metric_key), metric_label)}。"
            )
        return {
            "mode": "breakdown",
            "title": (
                f"{scope_title} 按{query_spec['group_by']}与{query_spec['secondary_group_by']}拆解"
                if query_spec.get("secondary_group_by")
                else f"{scope_title} 按{query_spec['group_by']}拆解"
            ),
            "answer_text": answer_text,
            "metric_key": metric_key,
            "metric_label": metric_label,
            "entries": entries,
            "trace_steps": trace_steps + [{
                "step": "拆解维度",
                "detail": (
                    f"先按 {query_spec['group_by']} 聚合"
                    + (
                        f"，再按 {query_spec['secondary_group_by']} 继续细分。"
                        if query_spec.get("secondary_group_by")
                        else "。"
                    )
                ),
            }],
            "query_spec": query_spec,
        }

    aggregated = _aggregate_cube_rows(filtered_rows)
    if not aggregated:
        return {
            "mode": "empty",
            "title": f"{scope_title} 查询结果",
            "answer_text": f"{scope_title}没有匹配到可用数据。",
            "metric_key": metric_key,
            "metric_label": metric_label,
            "entries": [],
            "query_spec": query_spec,
        }
    answer_text = f"{scope_title}的{metric_label}是 {_metric_display(aggregated.get(metric_key), metric_label)}。"
    return {
        "mode": "single_value",
        "title": f"{scope_title} 表现",
        "answer_text": answer_text,
        "metric_key": metric_key,
        "metric_label": metric_label,
        "entries": [{"label": scope_title, **aggregated}],
        "trace_steps": trace_steps + [{"step": "计算结果", "detail": f"按当前过滤范围重算 {metric_label}。"}],
        "query_spec": query_spec,
    }


def _derive_query_followups(query_result: dict[str, Any] | None) -> list[str]:
    if not query_result:
        return []
    query_spec = query_result.get("query_spec", {}) or {}
    metric_label = query_result.get("metric_label") or "高意向成本"
    rows = query_result.get("entries", []) or []
    suggestions: list[str] = []
    filters = query_spec.get("filters", {}) or {}

    def _scope_prefix(exclude: set[str] | None = None) -> str:
        exclude = exclude or set()
        parts = []
        if filters.get("month") and "month" not in exclude:
            parts.append(str(filters["month"]))
        if filters.get("vehicle") and "vehicle" not in exclude:
            parts.append(str(filters["vehicle"]))
        if filters.get("media") and "media" not in exclude:
            parts.append(str(filters["media"]))
        if filters.get("placement") and "placement" not in exclude:
            parts.append(str(filters["placement"]))
        return " / ".join(parts)

    def _join_scope_with_prompt(prompt: str, exclude: set[str] | None = None) -> str:
        prefix = _scope_prefix(exclude)
        return f"{prefix} / {prompt}" if prefix else prompt

    if query_result.get("mode") == "comparison":
        top_label = rows[0]["label"] if rows else None
        if top_label:
            suggestions.append(_join_scope_with_prompt(f"{top_label}的{metric_label}是多少？"))
        group_by = query_spec.get("group_by")
        if group_by == "media":
            suggestions.append(_join_scope_with_prompt("按点位看看呢？", {"media"}))
        elif group_by == "vehicle":
            suggestions.append(_join_scope_with_prompt("按媒体看看呢？", {"vehicle"}))
        suggestions.append("生成一个简短分析结论")

    if query_result.get("mode") == "breakdown":
        top_label = rows[0]["label"] if rows else None
        if top_label:
            suggestions.append(_join_scope_with_prompt(f"{top_label}的{metric_label}是多少？"))
        if query_spec.get("secondary_group_by") is None:
            if query_spec.get("group_by") == "media":
                suggestions.append(_join_scope_with_prompt("按点位继续拆解", {"media"}))
            elif query_spec.get("group_by") == "vehicle":
                suggestions.append(_join_scope_with_prompt("按媒体继续拆解", {"vehicle"}))
        suggestions.append("生成一个简短分析结论")

    if query_result.get("mode") == "single_value":
        if filters.get("vehicle"):
            suggestions.append(_join_scope_with_prompt("按媒体看看呢？", {"media"}))
        if filters.get("media"):
            suggestions.append(_join_scope_with_prompt("按车型看看呢？", {"vehicle"}))
        if filters.get("month"):
            suggestions.append(_join_scope_with_prompt("和其他月份对比看看？", {"month"}))
        suggestions.append("生成一个简短分析结论")

    deduped = []
    seen = set()
    for item in suggestions:
        if item and item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped[:3]


def _sanitize_llm_query_spec(
    llm_query_spec: dict[str, Any] | None,
    fallback_query_spec: dict[str, Any] | None,
    query_context: dict[str, Any],
) -> dict[str, Any] | None:
    if not fallback_query_spec:
        return llm_query_spec
    if not llm_query_spec:
        return fallback_query_spec

    allowed_goals = {"confirm_presence", "retrieve_value", "inspect_breakdown", "compare_entities"}
    allowed_dimensions = {"month", "vehicle", "media", "placement"}
    merged = dict(fallback_query_spec)

    goal = llm_query_spec.get("goal")
    if goal in allowed_goals:
        merged["goal"] = goal
        merged["intent"] = {
            "confirm_presence": "existence",
            "inspect_breakdown": "breakdown",
            "compare_entities": "comparison",
            "retrieve_value": "value",
        }[goal]

    if llm_query_spec.get("metric_key"):
        merged["metric_key"] = llm_query_spec["metric_key"]
    if llm_query_spec.get("metric_label"):
        merged["metric_label"] = llm_query_spec["metric_label"]

    merged_filters = dict(merged.get("filters", {}))
    llm_filters = llm_query_spec.get("filters", {}) or {}
    valid_lookup = {
        "month": set(query_context.get("months", [])),
        "vehicle": set(query_context.get("vehicles", [])),
        "media": set(query_context.get("medias", [])),
        "placement": set(query_context.get("placements", [])),
    }
    for key in ("month", "vehicle", "media", "placement"):
        value = llm_filters.get(key)
        if value is None:
            merged_filters[key] = None if key in (llm_query_spec.get("requested_dimensions") or []) else merged_filters.get(key)
        elif value in valid_lookup[key]:
            merged_filters[key] = value
    merged["filters"] = merged_filters

    requested_dimensions = [
        item for item in (llm_query_spec.get("requested_dimensions") or [])
        if item in allowed_dimensions
    ]
    if requested_dimensions:
        merged["requested_dimensions"] = requested_dimensions
        merged["group_by"] = requested_dimensions[0]
        merged["secondary_group_by"] = requested_dimensions[1] if len(requested_dimensions) > 1 else None

    if llm_query_spec.get("sort_direction") in {"asc", "desc"}:
        merged["sort_direction"] = llm_query_spec["sort_direction"]
    if isinstance(llm_query_spec.get("limit"), int):
        merged["limit"] = max(1, min(llm_query_spec["limit"], 20))
    if llm_query_spec.get("interpretation"):
        merged["interpretation"] = str(llm_query_spec["interpretation"])
    if isinstance(llm_query_spec.get("needs_clarification"), bool):
        merged["needs_clarification"] = llm_query_spec["needs_clarification"]
    if llm_query_spec.get("clarification_question"):
        merged["clarification_question"] = str(llm_query_spec["clarification_question"])
    if isinstance(llm_query_spec.get("clarification_options"), list):
        merged["clarification_options"] = [
            str(item) for item in llm_query_spec["clarification_options"][:3] if str(item).strip()
        ]
    return merged


def _derive_clarification_options(
    query_spec: dict[str, Any] | None,
    query_context: dict[str, Any],
) -> list[str]:
    if not query_spec or not query_spec.get("needs_clarification"):
        return []
    existing = query_spec.get("clarification_options") or []
    if existing:
        return existing[:3]

    filters = query_spec.get("filters", {})
    requested_dimensions = query_spec.get("requested_dimensions", [])
    candidates: list[str] = []

    if not filters.get("vehicle") and "vehicle" not in requested_dimensions:
        candidates.extend(query_context.get("vehicles", [])[:3])
    elif not filters.get("media") and "media" not in requested_dimensions:
        candidates.extend(query_context.get("medias", [])[:3])
    elif not filters.get("month") and "month" not in requested_dimensions:
        candidates.extend(query_context.get("months", [])[:3])

    deduped = []
    seen = set()
    for item in candidates:
        if item and item not in seen:
            deduped.append(item)
            seen.add(item)
    return deduped[:3]


def _plan_query_spec(
    user_request: str | None,
    query_context: dict[str, Any],
    conversation_history: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    fallback_query_spec = _infer_query_spec(user_request, query_context, conversation_history)
    if not user_request or not llm_is_configured():
        if fallback_query_spec is not None:
            fallback_query_spec["planner_source"] = "rules_fallback"
        return fallback_query_spec
    try:
        llm_query_spec = plan_query_with_llm(
            user_request=user_request,
            conversation_history=conversation_history,
            query_context=query_context,
        )
    except Exception:
        if fallback_query_spec is not None:
            fallback_query_spec["planner_source"] = "rules_fallback"
        return fallback_query_spec
    planned = _sanitize_llm_query_spec(llm_query_spec, fallback_query_spec, query_context)
    if planned is not None:
        planned["planner_source"] = "llm_planner"
        planned["clarification_options"] = _derive_clarification_options(planned, query_context)
    return planned


def _execute_aggregations(
    runtime_config: AgentRuntimeConfig,
    workflow_output: dict[str, Any],
    confirmation_state: dict[str, Any],
) -> dict[str, Any]:
    plan = workflow_output["plan"]
    selected_months = set(confirmation_state.get("reporting_month", []))
    placement_choice = confirmation_state.get("placement_dimension_choice", "点位类型")

    semantic_config = runtime_config.semantic_config
    text_rule = semantic_config.get("text_semantic_rules", [{}])[0]
    mapping_hints = semantic_config.get("header_mapping_hints", [])

    by_month: dict[str, dict[str, float]] = defaultdict(_empty_agg)
    by_vehicle: dict[str, dict[str, float]] = defaultdict(_empty_agg)
    by_media: dict[str, dict[str, float]] = defaultdict(_empty_agg)
    by_placement: dict[str, dict[str, float]] = defaultdict(_empty_agg)
    by_vehicle_media: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(_empty_agg))
    by_vehicle_placement: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(_empty_agg))
    query_cube: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(_empty_agg)

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
            vehicle_key = str(row.get("vehicle_model") or "未填写车型")
            media_key = str(row.get("media_name") or "未识别媒体")
            placement_key = _group_key(row, placement_choice)

            group_targets = [
                by_month[dataset_month],
                by_vehicle[vehicle_key],
                by_media[media_key],
                by_placement[placement_key],
                by_vehicle_media[vehicle_key][media_key],
                by_vehicle_placement[vehicle_key][placement_key],
                query_cube[(dataset_month, vehicle_key, media_key, placement_key)],
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

    overview = {
        "by_month": _finalize_mapping(by_month),
        "by_vehicle": _finalize_mapping(by_vehicle),
        "top_media": {
            key: _finalize_metrics(value)
            for key, value in sorted(by_media.items(), key=lambda item: item[1]["effective_cost"], reverse=True)[:10]
        },
        "top_placements": {
            key: _finalize_metrics(value)
            for key, value in sorted(by_placement.items(), key=lambda item: item[1]["effective_cost"], reverse=True)[:10]
        },
    }
    nested = {
        "vehicle_media": {
            vehicle: {
                key: _finalize_metrics(value)
                for key, value in sorted(media_map.items(), key=lambda item: item[1]["effective_cost"], reverse=True)
            }
            for vehicle, media_map in by_vehicle_media.items()
        },
        "vehicle_placement": {
            vehicle: {
                key: _finalize_metrics(value)
                for key, value in sorted(placement_map.items(), key=lambda item: item[1]["effective_cost"], reverse=True)
            }
            for vehicle, placement_map in by_vehicle_placement.items()
        },
    }
    cube_rows = [
        {
            "month": month,
            "vehicle": vehicle,
            "media": media,
            "placement": placement,
            **value,
            **_finalize_metrics(value),
        }
        for (month, vehicle, media, placement), value in query_cube.items()
    ]
    query_context = {
        "months": sorted({row["month"] for row in cube_rows}),
        "vehicles": sorted({row["vehicle"] for row in cube_rows}),
        "medias": sorted({row["media"] for row in cube_rows}),
        "placements": sorted({row["placement"] for row in cube_rows}),
    }
    return {
        "assumed_confirmations": confirmation_state,
        "included_files": included_files,
        "row_stats": {
            "total_rows_scanned": total_rows,
            "rows_after_filters": included_rows,
        },
        "overview": overview,
        "nested": nested,
        "cube_rows": cube_rows,
        "query_context": query_context,
        "notes": execution_notes,
    }


def execute_monthly_report(
    runtime_config: AgentRuntimeConfig,
    workflow_output: dict[str, Any],
    confirmation_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    plan = workflow_output["plan"]
    clarification_cards = workflow_output["clarification_cards"]
    confirmation_state = _resolve_confirmation_state(plan, clarification_cards, confirmation_state)
    execution = _execute_aggregations(runtime_config, workflow_output, confirmation_state)
    return {
        "status": "executed_preview",
        **execution,
    }


def execute_question_answering(
    runtime_config: AgentRuntimeConfig,
    workflow_output: dict[str, Any],
    confirmation_state: dict[str, Any] | None = None,
    user_request: str | None = None,
) -> dict[str, Any]:
    plan = workflow_output["plan"]
    clarification_cards = workflow_output["clarification_cards"]
    confirmation_state = _resolve_confirmation_state(plan, clarification_cards, confirmation_state)
    execution = _execute_aggregations(runtime_config, workflow_output, confirmation_state)
    query_spec = _plan_query_spec(
        user_request,
        execution["query_context"],
        workflow_output.get("conversation_history"),
    )
    query_result = _execute_query_spec(query_spec, execution["cube_rows"])
    if query_result is not None:
        query_result["follow_up_options"] = _derive_query_followups(query_result)
    return {
        "status": "answered",
        **execution,
        "query_spec": query_spec,
        "query_result": query_result,
    }
