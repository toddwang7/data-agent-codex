from __future__ import annotations

from typing import Any

from .config_loader import AgentRuntimeConfig


def _select_report_template(
    report_templates: list[dict[str, Any]],
    dataset_count: int,
) -> dict[str, Any] | None:
    for template in report_templates:
        applicability = template.get("applicability", {})
        if "month_count" in applicability and dataset_count == applicability["month_count"]:
            return template
        if "month_count_min" in applicability and dataset_count >= applicability["month_count_min"]:
            return template
    return None


def _build_confirmation_items(clarification_cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for card in clarification_cards:
        items.append(
            {
                "card_id": card["card_id"],
                "title": card["title"],
                "required": card.get("required", False),
                "options": card.get("options", []),
            }
        )
    return items


def generate_plan(
    runtime_config: AgentRuntimeConfig,
    datasets: list[dict[str, Any]],
    clarification_cards: list[dict[str, Any]],
    task_type: str = "monthly_report",
    user_request: str | None = None,
) -> dict[str, Any]:
    dataset_count = len(datasets)
    required_confirmations = _build_confirmation_items(clarification_cards)

    if task_type == "monthly_report":
        template = _select_report_template(runtime_config.report_templates, dataset_count)
        template_id = template["template_id"] if template else None
        report_variant = "multi_month" if dataset_count >= 2 else "single_month"
        steps = [
            "确认本次报告月份、费用口径和特殊样本处理规则",
            "读取上传文件并校验核心字段映射是否完整",
            "解析投放时间区间并确定本次报告的数据范围",
            "应用 URL 过滤、FREE 点位处理和不可监测样本处理规则",
            "按当前口径重算成本和转化链路指标",
            "输出媒体、点位、车型和趋势拆解结果",
            "生成结构化月报内容并映射到右侧报告面板",
        ]
        if template:
            section_titles = [section["title"] for section in template.get("sections", [])]
        else:
            section_titles = []
        return {
            "task_type": "monthly_report",
            "task_variant": report_variant,
            "status": "plan_pending_confirmation" if required_confirmations else "ready_to_execute",
            "selected_template_id": template_id,
            "summary": user_request
            or (
                "基于上传的广告 rawdata 生成结构化月报"
                if report_variant == "single_month"
                else "基于上传的多月广告 rawdata 生成跨月对比月报"
            ),
            "steps": steps,
            "target_sections": section_titles,
            "needs_confirmation": required_confirmations,
            "assumptions": [
                "源表中的率和成本字段不直接作为最终结果，分析阶段按当前口径重算",
                "文件名月份和投放时间区间可能不一致，月报月份以用户最终确认结果为准",
            ],
        }

    qa_steps = [
        "确认当前数据集和必要分析口径",
        "识别问题涉及的指标、维度和时间范围",
        "应用过滤规则并重算相关派生指标",
        "输出指标结果、洞察摘要和必要图表",
    ]
    return {
        "task_type": "question_answering",
        "task_variant": "ad_hoc_analysis",
        "status": "plan_pending_confirmation" if required_confirmations else "ready_to_execute",
        "selected_template_id": None,
        "summary": user_request or "基于当前广告数据执行一次自然语言分析问答",
        "steps": qa_steps,
        "target_sections": [],
        "needs_confirmation": required_confirmations,
        "assumptions": [
            "点位拆解默认以点位类型为主字段，如后续业务变化再扩展配置",
            "如果问题涉及成本和转化率，则使用重算后的派生指标而不是源表现成值",
        ],
    }
