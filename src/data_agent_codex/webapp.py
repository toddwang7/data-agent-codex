from __future__ import annotations

import cgi
import json
from pathlib import Path
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .config_loader import load_agent_runtime_config
from .llm import generate_llm_response, llm_is_configured, load_local_env
from .workflow import run_intake_workflow


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PROTOTYPE_DIR = PROJECT_ROOT / "prototype"
DEFAULT_AGENT_DIR = PROJECT_ROOT / "config/agents/ad-analysis"

load_local_env(PROJECT_ROOT)


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".html":
        return "text/html; charset=utf-8"
    if suffix == ".css":
        return "text/css; charset=utf-8"
    if suffix == ".js":
        return "application/javascript; charset=utf-8"
    if suffix == ".json":
        return "application/json; charset=utf-8"
    return "application/octet-stream"


def _build_config_summary(config: Any) -> dict[str, Any]:
    agent = config.agent
    semantic = config.semantic_config
    templates = config.report_templates

    return {
        "agent": {
            "agent_id": agent.get("agent_id"),
            "name": agent.get("name"),
            "description": agent.get("description"),
            "domain": agent.get("domain"),
            "supported_file_types": agent.get("supported_file_types", []),
            "capabilities": agent.get("capabilities", []),
            "default_task_flow": agent.get("default_task_flow", []),
        },
        "dataset_profile": agent.get("dataset_profile", {}),
        "fields": semantic.get("field_catalog", []),
        "metrics": semantic.get("metric_catalog", []),
        "filters": semantic.get("default_filters", []),
        "metric_specific_exclusions": semantic.get("metric_specific_exclusions", []),
        "clarification_policy": agent.get("clarification_policy", {}),
        "clarification_cards": semantic.get("clarification_cards", []),
        "clarification_flow": semantic.get("clarification_flow", []),
        "templates": [
            {
                "template_id": template.get("template_id"),
                "name": template.get("name"),
                "trigger_intents": template.get("trigger_intents", []),
                "sections": template.get("sections", []),
            }
            for template in templates
        ],
        "report_period_resolution": semantic.get("report_period_resolution", {}),
        "source_metric_trust_policy": semantic.get("source_metric_trust_policy", {}),
    }


class DataAgentHandler(BaseHTTPRequestHandler):
    server_version = "DataAgentCodex/0.1"

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        data = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self._send_cors_headers()
        self.send_header("Content-Type", _content_type(path))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/index.html"):
            self._send_file(PROTOTYPE_DIR / "index.html")
            return
        if parsed.path == "/api/health":
            self._send_json({"status": "ok", "llm_configured": llm_is_configured()})
            return
        if parsed.path == "/api/config-summary":
            config = load_agent_runtime_config(DEFAULT_AGENT_DIR)
            self._send_json(_build_config_summary(config))
            return

        normalized = parsed.path.lstrip("/")
        candidate = (PROTOTYPE_DIR / normalized).resolve()
        try:
            candidate.relative_to(PROTOTYPE_DIR.resolve())
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND, "Invalid path")
            return
        self._send_file(candidate)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/analyze":
            self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json(
                {"error": "Expected multipart/form-data request."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        environ = {
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": content_type,
        }
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ=environ)

        task_type = form.getfirst("task_type", "monthly_report")
        user_request = form.getfirst("user_request") or None
        conversation_history_raw = form.getfirst("conversation_history") or "[]"
        reporting_months = form.getlist("reporting_month")
        cost_rule_confirmation = form.getfirst("cost_rule_confirmation")
        free_slot_handling = form.getfirst("free_slot_handling")
        special_sample_handling = form.getfirst("special_sample_handling")

        uploaded_fields = form["files"] if "files" in form else []
        if not isinstance(uploaded_fields, list):
            uploaded_fields = [uploaded_fields]
        if not uploaded_fields:
            self._send_json(
                {"error": "Please upload at least one file."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        confirmation_state: dict[str, Any] = {}
        if reporting_months:
            confirmation_state["reporting_month"] = reporting_months
        if cost_rule_confirmation is not None:
            confirmation_state["cost_rule_confirmation"] = cost_rule_confirmation == "true"
        if free_slot_handling is not None:
            confirmation_state["free_slot_handling"] = free_slot_handling == "true"
        if special_sample_handling:
            confirmation_state["special_sample_handling"] = special_sample_handling

        try:
            conversation_history = json.loads(conversation_history_raw)
            if not isinstance(conversation_history, list):
                conversation_history = []
        except json.JSONDecodeError:
            conversation_history = []

        try:
            with tempfile.TemporaryDirectory(prefix="data-agent-codex-") as temp_dir:
                temp_paths = []
                for uploaded in uploaded_fields:
                    filename = Path(uploaded.filename or "upload.xlsx").name
                    destination = Path(temp_dir) / filename
                    with destination.open("wb") as file:
                        file.write(uploaded.file.read())
                    temp_paths.append(destination)

                config = load_agent_runtime_config(DEFAULT_AGENT_DIR)
                result = run_intake_workflow(
                    config,
                    temp_paths,
                    task_type=task_type,
                    user_request=user_request,
                    execute=True,
                    confirmation_state=confirmation_state or None,
                    conversation_history=conversation_history,
                )
                execution = result.get("execution", {})
                if llm_is_configured() and execution:
                    try:
                        result["llm"] = generate_llm_response(
                            user_request=user_request,
                            conversation_history=conversation_history,
                            plan=result.get("plan", {}),
                            datasets=result.get("datasets", []),
                            clarification_cards=result.get("clarification_cards", []),
                            execution=execution,
                        )
                    except Exception as llm_exc:
                        result["llm"] = {
                            "assistant_message": "",
                            "report_sections": [],
                            "follow_up_suggestions": [],
                            "error": str(llm_exc),
                        }
        except Exception as exc:  # pragma: no cover - runtime safety path
            self._send_json(
                {"error": f"Server failed to analyze files: {exc}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
            return

        self._send_json(result)


def run_server(host: str = "127.0.0.1", port: int = 8765) -> None:
    httpd = ThreadingHTTPServer((host, port), DataAgentHandler)
    print(f"Serving Data Agent Codex prototype at http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
