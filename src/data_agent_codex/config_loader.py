from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AgentRuntimeConfig:
    agent: dict[str, Any]
    semantic_config: dict[str, Any]
    report_templates: list[dict[str, Any]]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_agent_runtime_config(agent_dir: Path) -> AgentRuntimeConfig:
    agent = load_json(agent_dir / "agent.json")
    report_templates = [
        load_json(agent_dir / template_ref)
        for template_ref in agent.get("template_refs", [])
    ]
    return AgentRuntimeConfig(
        agent=agent,
        semantic_config=load_json(agent_dir / "semantic-config.json"),
        report_templates=report_templates,
    )
