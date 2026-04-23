from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import ssl
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_GLM_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"
DEFAULT_GLM_MODEL = "glm-5.1"


def load_local_env(project_root: Path) -> None:
    env_path = project_root / ".env.local"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def llm_is_configured() -> bool:
    return bool(os.environ.get("GLM_API_KEY"))


def _extract_json(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    if candidate.startswith("```"):
        parts = candidate.split("```")
        for part in parts:
            stripped = part.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                candidate = stripped
                break
            if "\n" in stripped:
                maybe_json = stripped.split("\n", 1)[1].strip()
                if maybe_json.startswith("{") and maybe_json.endswith("}"):
                    candidate = maybe_json
                    break
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _build_ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl._create_unverified_context()


def _condense_execution(execution: dict[str, Any]) -> dict[str, Any]:
    overview = execution.get("overview", {})
    return {
        "row_stats": execution.get("row_stats", {}),
        "notes": execution.get("notes", []),
        "by_month": overview.get("by_month", {}),
        "top_media": dict(list((overview.get("top_media") or {}).items())[:5]),
        "top_placements": dict(list((overview.get("top_placements") or {}).items())[:5]),
        "by_vehicle": dict(list((overview.get("by_vehicle") or {}).items())[:5]),
    }


def generate_llm_response(
    *,
    user_request: str | None,
    conversation_history: list[dict[str, Any]] | None,
    plan: dict[str, Any],
    datasets: list[dict[str, Any]],
    clarification_cards: list[dict[str, Any]],
    execution: dict[str, Any],
) -> dict[str, Any]:
    api_key = os.environ.get("GLM_API_KEY")
    if not api_key:
        raise RuntimeError("GLM_API_KEY is not configured.")

    base_url = os.environ.get("GLM_BASE_URL", DEFAULT_GLM_BASE_URL).rstrip("/")
    model = os.environ.get("GLM_MODEL", DEFAULT_GLM_MODEL)

    context_payload = {
        "request": user_request,
        "conversation_history": conversation_history or [],
        "plan": {
            "task_type": plan.get("task_type"),
            "task_variant": plan.get("task_variant"),
            "summary": plan.get("summary"),
            "steps": plan.get("steps", []),
            "target_sections": plan.get("target_sections", []),
        },
        "datasets": [
            {
                "file_name": dataset.get("file_name"),
                "row_count": dataset.get("row_count"),
                "reporting_months": dataset.get("reporting_months", {}),
            }
            for dataset in datasets
        ],
        "clarification_cards": [
            {
                "card_id": card.get("card_id"),
                "title": card.get("title"),
                "required": card.get("required"),
                "options": card.get("options", []),
            }
            for card in clarification_cards
        ],
        "execution": _condense_execution(execution),
    }

    prompt = (
        "你是一个广告数据分析智能体，正在直接回复产品中的最终用户。"
        "请基于提供的结构化上下文输出严格 JSON，不要输出 JSON 之外的任何文字。"
        '格式为 {"assistant_message": string, "report_sections": [{"title": string, "text": string, "bullets": [string]}], '
        '"follow_up_suggestions": [string] }。'
        "要求："
        "1. assistant_message 要直接回答用户当前问题，中文，简洁但有分析感。"
        "2. 如果还有待确认项，要明确说清楚哪些确认项阻碍进一步分析。"
        "3. report_sections 最多 6 段，贴合月报/分析报告口吻。"
        "4. bullets 每段最多 3 条。"
        "5. 不要编造上下文中没有的数据。"
    )

    body = {
        "model": model,
        "temperature": 0.3,
        "stream": False,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": json.dumps(context_payload, ensure_ascii=False)},
        ],
    }

    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    payload = None
    last_timeout_error: Exception | None = None
    for timeout_seconds in (90, 180):
        try:
            with urlopen(request, timeout=timeout_seconds, context=_build_ssl_context()) as response:
                payload = json.loads(response.read().decode("utf-8"))
            break
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"GLM HTTP {exc.code}: {detail}") from exc
        except TimeoutError as exc:
            last_timeout_error = exc
            continue
        except socket.timeout as exc:
            last_timeout_error = exc
            continue
        except URLError as exc:
            if "timed out" in str(exc).lower():
                last_timeout_error = exc
                continue
            raise RuntimeError(f"GLM network error: {exc}") from exc

    if payload is None:
        raise RuntimeError(f"The read operation timed out: {last_timeout_error}")

    text = (
        payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
    )
    parsed = _extract_json(text)
    if not parsed:
        return {
            "assistant_message": text or "模型已返回，但结果格式不符合预期。",
            "report_sections": [],
            "follow_up_suggestions": [],
            "raw_content": text,
        }
    return {
        "assistant_message": parsed.get("assistant_message") or "",
        "report_sections": parsed.get("report_sections") or [],
        "follow_up_suggestions": parsed.get("follow_up_suggestions") or [],
    }
