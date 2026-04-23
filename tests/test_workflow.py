from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

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
        self.assertEqual(month_metrics["pv"], 1000.0)
        self.assertAlmostEqual(month_metrics["ctr"], 0.1)


if __name__ == "__main__":
    unittest.main()
