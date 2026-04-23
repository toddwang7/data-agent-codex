from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config_loader import load_agent_runtime_config
from .workflow import run_intake_workflow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the minimal intake workflow for Data Agent Codex."
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="One or more spreadsheet files to inspect.",
    )
    parser.add_argument(
        "--agent-dir",
        default="config/agents/ad-analysis",
        help="Agent configuration directory relative to the project root.",
    )
    parser.add_argument(
        "--task-type",
        default="monthly_report",
        choices=["monthly_report", "question_answering"],
        help="Planning mode for the generated output.",
    )
    parser.add_argument(
        "--user-request",
        default=None,
        help="Optional natural-language request used to summarize the generated plan.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run the minimal monthly-report execution preview after plan generation.",
    )
    parser.add_argument(
        "--confirm-reporting-month",
        action="append",
        default=None,
        help="Confirmed reporting month. Repeat for multi-month execution.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parents[2]
    agent_dir = project_root / args.agent_dir
    file_paths = [Path(file).expanduser().resolve() for file in args.files]

    config = load_agent_runtime_config(agent_dir)
    confirmation_state = {}
    if args.confirm_reporting_month:
        confirmation_state["reporting_month"] = args.confirm_reporting_month

    result = run_intake_workflow(
        config,
        file_paths,
        task_type=args.task_type,
        user_request=args.user_request,
        execute=args.execute,
        confirmation_state=confirmation_state or None,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
