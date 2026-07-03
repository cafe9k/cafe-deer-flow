from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .locator import ReportCandidate
from .models import ExecutionSummary, TaskSummary

_MAX_TEXT = 320


def _compact(value: Any, *, max_len: int = _MAX_TEXT) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value
    else:
        try:
            text = json.dumps(value, ensure_ascii=False, default=str)
        except TypeError:
            text = str(value)
    text = " ".join(text.split())
    if not text:
        return None
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def _get_nested(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _collect_screenshot_refs(value: Any) -> list[str]:
    refs: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if node.get("type") == "midscene_screenshot_ref":
                path = node.get("path")
                screenshot_id = node.get("id")
                if isinstance(path, str):
                    refs.append(path)
                elif isinstance(screenshot_id, str):
                    refs.append(screenshot_id)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return refs


def _screenshot_exists(report_dir: Path, ref: str) -> bool:
    if ref.startswith("data:"):
        return True
    candidates: list[Path] = []
    if ref.startswith(".") or "/" in ref:
        candidates.append((report_dir / ref).resolve())
    else:
        candidates.extend(
            [
                report_dir / "screenshots" / f"{ref}.png",
                report_dir / "screenshots" / f"{ref}.jpeg",
                report_dir / "screenshots" / f"{ref}.jpg",
            ]
        )
    return any(path.exists() for path in candidates)


def _load_execution(json_path: Path) -> tuple[dict[str, Any], str | None]:
    data = json.loads(json_path.read_text(encoding="utf-8"))
    sdk_version = data.get("sdkVersion") if isinstance(data, dict) else None
    if isinstance(data, dict) and isinstance(data.get("executions"), list) and data["executions"]:
        execution = data["executions"][0]
        if isinstance(execution, dict):
            return execution, sdk_version
    if isinstance(data, dict) and isinstance(data.get("tasks"), list):
        return data, sdk_version
    raise ValueError(f"Report JSON does not contain an execution: {json_path}")


def parse_report(candidate: ReportCandidate) -> ExecutionSummary:
    execution, sdk_version = _load_execution(candidate.json_path)
    raw_tasks = execution.get("tasks") or []
    if not isinstance(raw_tasks, list):
        raw_tasks = []

    tasks: list[TaskSummary] = []
    missing_screenshots: list[str] = []
    action_types: Counter[str] = Counter()

    for index, raw_task in enumerate(raw_tasks):
        if not isinstance(raw_task, dict):
            continue
        task_type = raw_task.get("type")
        sub_type = raw_task.get("subType")
        if task_type == "Action Space":
            action_types[str(sub_type or "Action")] += 1

        screenshot_refs = _collect_screenshot_refs(
            {
                "uiContext": raw_task.get("uiContext"),
                "recorder": raw_task.get("recorder"),
            }
        )
        for ref in screenshot_refs:
            if not _screenshot_exists(candidate.report_dir, ref):
                missing_screenshots.append(ref)

        param = raw_task.get("param") if isinstance(raw_task.get("param"), dict) else {}
        output = raw_task.get("output") if isinstance(raw_task.get("output"), dict) else raw_task.get("output")
        tasks.append(
            TaskSummary(
                index=index,
                task_id=_compact(raw_task.get("taskId"), max_len=120),
                type=_compact(task_type, max_len=80),
                sub_type=_compact(sub_type, max_len=80),
                status=_compact(raw_task.get("status"), max_len=80),
                thought=_compact(raw_task.get("thought") or raw_task.get("reasoning_content")),
                param=_compact(raw_task.get("param")),
                response=_compact(raw_task.get("response") or _get_nested(output, "response") or output),
                result=_compact(raw_task.get("result") or _get_nested(output, "result")),
                error_message=_compact(raw_task.get("errorMessage") or raw_task.get("error")),
                hit_by_from=_compact(_get_nested(raw_task, "hitBy", "from"), max_len=80),
                bbox=_compact(_get_nested(param, "bbox"), max_len=160),
                located_pixel_bbox=_compact(_get_nested(param, "locatedPixelBbox"), max_len=160),
                locate_center=_compact(_get_nested(param, "locate", "center"), max_len=160),
                screenshots=screenshot_refs,
            )
        )

    return ExecutionSummary(
        label="success" if candidate.label == "success" else "failure",
        report_dir=str(candidate.report_dir),
        json_path=str(candidate.json_path),
        screenshots_dir=str(candidate.screenshots_dir) if candidate.screenshots_dir else None,
        execution_name=_compact(execution.get("name"), max_len=160),
        execution_id=_compact(execution.get("id"), max_len=160),
        sdk_version=_compact(sdk_version, max_len=80),
        total_tasks=len(tasks),
        planning_tasks=sum(1 for task in tasks if task.type == "Planning"),
        action_tasks=sum(1 for task in tasks if task.type == "Action Space"),
        failed_tasks=sum(1 for task in tasks if task.status == "failed" or bool(task.error_message)),
        cancelled_tasks=sum(1 for task in tasks if task.status == "cancelled"),
        dominant_action_types=[name for name, _ in action_types.most_common(5)],
        missing_screenshots=sorted(set(missing_screenshots)),
        tasks=tasks,
    )
