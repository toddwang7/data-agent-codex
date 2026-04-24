from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

from data_agent_codex.config_loader import AgentRuntimeConfig
from data_agent_codex.workflow import run_intake_workflow


def _write_workbook(path: Path) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "raw_data"
    worksheet.append(
        [
            "adcode",
            "媒体名称",
            "点位类型",
            "点位名称",
            "广告页落地页URL",
            "投放时间",
            "车型",
            "备注",
            "adslot",
            "广告类型",
            "净总价",
            "总成本",
            "PV",
            "CLICK",
            "官网到达",
            "有效访客",
            "高意向访客",
            "是否接受DMP曝光监测",
            "是否接受DMP点击监测",
        ]
    )
    worksheet.append(
        [
            "abc-1",
            "测试媒体",
            "信息流/开屏",
            "RTB找回投放",
            "https://www.ghac.cn/",
            "2025-02-01至2025-02-28",
            "BRE",
            "补量样本",
            "定向说明",
            "CPM",
            100,
            80,
            1000,
            100,
            10,
            3,
            1,
            "是",
            "是",
        ]
    )
    worksheet.append(
        [
            "abc-2",
            "今日头条",
            "视频流",
            "品牌放量",
            "https://www.ghac.cn/model",
            "2025-02-01至2025-02-28",
            "BRE",
            "",
            "常规投放",
            "CPM",
            200,
            200,
            2000,
            50,
            20,
            10,
            1,
            "是",
            "是",
        ]
    )
    workbook.save(path)


def _load_fixture_config() -> AgentRuntimeConfig:
    project_root = Path(__file__).resolve().parents[1]
    with (project_root / "config/agents/ad-analysis/agent.json").open("r", encoding="utf-8") as file:
        agent = json.load(file)
    with (project_root / "config/agents/ad-analysis/semantic-config.json").open("r", encoding="utf-8") as file:
        semantic = json.load(file)
    templates = []
    for ref in agent["template_refs"]:
        with (project_root / "config/agents/ad-analysis" / ref).open("r", encoding="utf-8") as file:
            templates.append(json.load(file))
    return AgentRuntimeConfig(agent=agent, semantic_config=semantic, report_templates=templates)


class WorkflowTests(unittest.TestCase):
    def test_intake_workflow_generates_reporting_month_and_cards(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(config, [workbook_path])

        self.assertEqual(result["agent_id"], "ad-analysis")
        self.assertEqual(result["datasets"][0]["reporting_months"]["default"], "2025-02")
        card_ids = [card["card_id"] for card in result["clarification_cards"]]
        self.assertIn("reporting_month", card_ids)
        self.assertIn("special_sample_handling", card_ids)
        self.assertEqual(result["plan"]["task_type"], "monthly_report")
        self.assertEqual(result["plan"]["task_variant"], "single_month")
        self.assertEqual(result["plan"]["selected_template_id"], "ad-monthly-report-single-month-v1")

    def test_execution_preview_returns_aggregates(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="monthly_report",
                execute=True,
                confirmation_state={
                    "reporting_month": ["2025-02"],
                },
            )

        execution = result["execution"]
        self.assertEqual(execution["status"], "executed_preview")
        self.assertIn("2025-02", execution["overview"]["by_month"])
        self.assertIn("信息流/开屏", execution["overview"]["top_placements"])
        month_metrics = execution["overview"]["by_month"]["2025-02"]
        self.assertEqual(month_metrics["pv"], 3000.0)
        self.assertAlmostEqual(month_metrics["ctr"], 0.05)

    def test_question_answering_returns_structured_query_result(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="BRE这个车型的媒体点位表现怎么样？",
                execute=True,
            )

        execution = result["execution"]
        self.assertEqual(execution["status"], "answered")
        self.assertIsNotNone(execution["query_result"])
        self.assertEqual(execution["query_result"]["mode"], "breakdown")
        self.assertIn("测试媒体", [item["label"] for item in execution["query_result"]["entries"]])

    def test_question_answering_supports_combined_filters(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="2025-02 BRE在测试媒体的高意向成本是多少？",
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "single_value")
        self.assertIn("2025-02", query_result["title"])
        self.assertEqual(query_result["entries"][0]["label"], "2025-02 / BRE / 测试媒体")

    def test_question_answering_supports_existence_check(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="BRE有没有投测试媒体？",
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "existence")
        self.assertTrue(query_result["exists"])

    def test_question_answering_infers_goal_and_interpretation(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="BRE这个车型的媒体点位表现怎么样？",
                execute=True,
            )

        query_spec = result["execution"]["query_result"]["query_spec"]
        self.assertEqual(query_spec["goal"], "inspect_breakdown")
        self.assertEqual(query_spec["requested_dimensions"], ["media", "placement"])
        self.assertIn("分析目标", query_spec["interpretation"])

    def test_question_answering_supports_comparison_intent(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="哪个媒体的高意向成本最高？",
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "comparison")
        self.assertEqual(query_result["query_spec"]["goal"], "compare_entities")
        self.assertEqual(query_result["entries"][0]["label"], "今日头条")

    def test_question_answering_supports_lowest_and_top_n(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="高意向成本最低的前1个媒体是哪个？",
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "comparison")
        self.assertEqual(query_result["query_spec"]["sort_direction"], "asc")
        self.assertEqual(query_result["query_spec"]["limit"], 1)
        self.assertEqual(len(query_result["entries"]), 1)
        self.assertEqual(query_result["entries"][0]["label"], "测试媒体")

    def test_question_answering_supports_follow_up_context(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="那2025-02呢？",
                conversation_history=[
                    {"role": "user", "text": "BRE的高意向成本是多少？"},
                ],
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "single_value")
        self.assertEqual(query_result["query_spec"]["filters"]["vehicle"], "BRE")
        self.assertEqual(query_result["query_spec"]["filters"]["month"], "2025-02")
        self.assertEqual(query_result["query_spec"]["metric_key"], "high_intent_cost")

    def test_question_answering_supports_follow_up_dimension_refinement(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="那今日头条呢？",
                conversation_history=[
                    {"role": "user", "text": "BRE的高意向成本是多少？"},
                ],
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "single_value")
        self.assertEqual(query_result["query_spec"]["filters"]["vehicle"], "BRE")
        self.assertEqual(query_result["query_spec"]["filters"]["media"], "今日头条")
        self.assertEqual(query_result["entries"][0]["label"], "BRE / 今日头条")

    def test_question_answering_supports_chinese_top_n_expression(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="高意向成本最低的前一个媒体是哪个？",
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "comparison")
        self.assertEqual(query_result["query_spec"]["limit"], 1)
        self.assertEqual(query_result["entries"][0]["label"], "测试媒体")

    def test_question_answering_supports_follow_up_comparison_intent(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="哪个最低？",
                conversation_history=[
                    {"role": "user", "text": "按媒体比较高意向成本"},
                ],
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "comparison")
        self.assertEqual(query_result["query_spec"]["requested_dimensions"], ["media"])
        self.assertEqual(query_result["query_spec"]["sort_direction"], "asc")
        self.assertEqual(query_result["entries"][0]["label"], "测试媒体")

    def test_question_answering_returns_trace_steps(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="按媒体比较高意向成本",
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertTrue(query_result["trace_steps"])
        self.assertEqual(query_result["trace_steps"][0]["step"], "理解问题")

    def test_question_answering_returns_follow_up_options(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="按媒体比较高意向成本",
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertTrue(query_result["follow_up_options"])

    def test_question_answering_follow_up_options_keep_scope(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="BRE的高意向成本是多少？",
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertTrue(any("BRE" in item for item in query_result["follow_up_options"]))

    def test_question_answering_month_scope_suggests_cross_month_followup(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="2025-02 BRE的高意向成本是多少？",
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertTrue(any("其他月份" in item for item in query_result["follow_up_options"]))

    def test_question_answering_supports_follow_up_dimension_switch(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            result = run_intake_workflow(
                config,
                [workbook_path],
                task_type="question_answering",
                user_request="按媒体呢？",
                conversation_history=[
                    {"role": "user", "text": "BRE在今日头条的高意向成本是多少？"},
                ],
                execute=True,
            )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "breakdown")
        self.assertEqual(query_result["query_spec"]["filters"]["vehicle"], "BRE")
        self.assertIsNone(query_result["query_spec"]["filters"]["media"])
        self.assertEqual(query_result["query_spec"]["requested_dimensions"], ["media"])
        self.assertGreaterEqual(len(query_result["entries"]), 2)

    def test_question_answering_supports_llm_clarification_result(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            with patch("data_agent_codex.executor.llm_is_configured", return_value=True), patch(
                "data_agent_codex.executor.plan_query_with_llm",
                return_value={
                    "goal": "retrieve_value",
                    "metric_key": "high_intent_cost",
                    "metric_label": "高意向成本",
                    "filters": {"month": None, "vehicle": None, "media": None, "placement": None},
                    "requested_dimensions": [],
                    "sort_direction": "desc",
                    "limit": 8,
                    "needs_clarification": True,
                    "clarification_question": "你是想看 BRE 还是所有车型？",
                    "clarification_options": ["看 BRE", "看所有车型"],
                    "interpretation": "用户想查成本，但对象还不明确。",
                },
            ):
                result = run_intake_workflow(
                    config,
                    [workbook_path],
                    task_type="question_answering",
                    user_request="高意向成本是多少？",
                    execute=True,
                )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "clarification_needed")
        self.assertIn("BRE", query_result["answer_text"])
        self.assertEqual(query_result["clarification_options"], ["看 BRE", "看所有车型"])

    def test_question_answering_derives_clarification_options_from_context(self) -> None:
        config = _load_fixture_config()
        with tempfile.TemporaryDirectory() as temp_dir:
            workbook_path = Path(temp_dir) / "rawdata202502.xlsx"
            _write_workbook(workbook_path)
            with patch("data_agent_codex.executor.llm_is_configured", return_value=True), patch(
                "data_agent_codex.executor.plan_query_with_llm",
                return_value={
                    "goal": "retrieve_value",
                    "metric_key": "high_intent_cost",
                    "metric_label": "高意向成本",
                    "filters": {"month": None, "vehicle": None, "media": None, "placement": None},
                    "requested_dimensions": [],
                    "sort_direction": "desc",
                    "limit": 8,
                    "needs_clarification": True,
                    "clarification_question": "你是想看哪个对象？",
                    "clarification_options": [],
                    "interpretation": "对象还不明确。",
                },
            ):
                result = run_intake_workflow(
                    config,
                    [workbook_path],
                    task_type="question_answering",
                    user_request="高意向成本是多少？",
                    execute=True,
                )

        query_result = result["execution"]["query_result"]
        self.assertEqual(query_result["mode"], "clarification_needed")
        self.assertIn("BRE", query_result["clarification_options"])


if __name__ == "__main__":
    unittest.main()
