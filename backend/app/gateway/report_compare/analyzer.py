from __future__ import annotations

import json

from langchain_core.messages import HumanMessage, SystemMessage

import deerflow.utils.llm_text as llm_text
from deerflow.config.app_config import AppConfig
from deerflow.models import create_chat_model

from .models import DivergenceSummary, ExecutionSummary, ReportCompareMetrics, ReportCompareResult


def _task_signature(task) -> str:
    parts = [task.type or "", task.sub_type or "", task.status or "", task.param or "", task.thought or "", task.error_message or ""]
    return "|".join(parts)


def find_first_divergence(success: ExecutionSummary, failure: ExecutionSummary) -> DivergenceSummary:
    max_len = max(len(success.tasks), len(failure.tasks))
    for index in range(max_len):
        left = success.tasks[index] if index < len(success.tasks) else None
        right = failure.tasks[index] if index < len(failure.tasks) else None
        if left is None or right is None:
            return DivergenceSummary(index=index, title="Task count diverged", success="No matching task" if left is None else _task_signature(left), failure="No matching task" if right is None else _task_signature(right))
        if _task_signature(left) != _task_signature(right):
            return DivergenceSummary(index=index, title=f"First divergence at task {index}", success=_task_signature(left), failure=_task_signature(right))
    return DivergenceSummary(index=None, title="No semantic divergence found", success="Task sequences are aligned.", failure="Task sequences are aligned.")


def _failed_step(failure: ExecutionSummary) -> str:
    for task in failure.tasks:
        if task.error_message:
            return task.param or task.thought or task.error_message
    for task in reversed(failure.tasks):
        if task.status in {"failed", "cancelled"}:
            return task.param or task.thought or task.sub_type or "Unknown failed task"
    return failure.execution_name or "Unknown failed step"


def _root_cause(success: ExecutionSummary, failure: ExecutionSummary, divergence: DivergenceSummary) -> str:
    failure_text = " ".join(part for task in failure.tasks for part in [task.error_message, task.hit_by_from, task.param, task.thought] if part).lower()
    if "cache" in failure_text:
        return "失败侧命中缓存导致上下文漂移"
    if "bbox" in failure_text or "locate" in failure_text or "center" in failure_text:
        return "定位坐标偏移导致操作目标错误"
    if failure.planning_tasks > success.planning_tasks:
        return "失败侧重复规划累积导致动作漂移"
    if divergence.index is not None:
        return "首个分叉动作改变了后续路径"
    return "未发现明确分叉，需要补齐报告证据"


def _suggestions(root_cause: str) -> list[str]:
    if "缓存" in root_cause:
        return ["禁用失败步骤的缓存命中，或将页面状态纳入缓存 key。", "在 cache hit 后补充截图一致性校验。", "失败重试时强制重新规划关键定位步骤。"]
    if "坐标" in root_cause or "定位" in root_cause:
        return ["记录并校验 locate 的 logical bbox、pixel bbox 和 center。", "对关键点击前增加目标元素二次确认。", "扩大/约束 deepLocate 搜索区域，避免命中相邻元素。"]
    if "重复规划" in root_cause:
        return ["收敛 replanningCycleLimit，并把失败反馈压缩成明确子目标。", "在连续 replanning 前复用上一轮稳定动作链。", "为关键步骤增加硬断言，提前暴露漂移。"]
    return ["补齐 success/failure 截图目录后重新对比。", "提供更精确的成功/失败 execution JSON。", "优先查看首个任务差异而不是最终断言。"]


def build_metrics(success: ExecutionSummary, failure: ExecutionSummary) -> ReportCompareMetrics:
    return ReportCompareMetrics(
        success_total_tasks=success.total_tasks,
        failure_total_tasks=failure.total_tasks,
        success_planning_tasks=success.planning_tasks,
        failure_planning_tasks=failure.planning_tasks,
        success_action_tasks=success.action_tasks,
        failure_action_tasks=failure.action_tasks,
        success_failed_tasks=success.failed_tasks,
        failure_failed_tasks=failure.failed_tasks,
        dominant_action_types=sorted(set(success.dominant_action_types + failure.dominant_action_types)),
        missing_screenshots=sorted(set(success.missing_screenshots + failure.missing_screenshots)),
    )


def build_deterministic_result(success: ExecutionSummary, failure: ExecutionSummary, source_notes: tuple[str, ...]) -> ReportCompareResult:
    divergence = find_first_divergence(success, failure)
    root_cause = _root_cause(success, failure, divergence)
    data_notes = list(source_notes)
    if success.missing_screenshots or failure.missing_screenshots:
        data_notes.append("Some screenshot references are missing; visual conclusions are lower confidence.")
    else:
        data_notes.append("Screenshot references resolved or no screenshot references were found.")
    return ReportCompareResult(
        failed_step=_failed_step(failure),
        root_cause=root_cause[:50],
        repair_suggestions=_suggestions(root_cause),
        divergence=divergence,
        data_notes=data_notes,
        success=success,
        failure=failure,
        metrics=build_metrics(success, failure),
    )


def build_summary_markdown(result: ReportCompareResult, *, html_path: str | None = None) -> str:
    html_line = f"- Generated: `{html_path}`" if html_path else "- Generated: not requested"
    suggestions = "\n".join(f"- {item}" for item in result.repair_suggestions)
    data_notes = "\n".join(f"- {item}" for item in result.data_notes)
    return f"""## Summary

Failed step: {result.failed_step}
Root cause: {result.root_cause}

## Repair Suggestions

{suggestions}

## 分叉点分析

- Original step: {result.failed_step}
- Divergence point: {result.divergence.title}
- Success after divergence: {result.divergence.success}
- Failure after divergence: {result.divergence.failure}

## Data Notes

{data_notes}

## HTML Report

{html_line}
"""


async def refine_with_model(result: ReportCompareResult, *, app_config: AppConfig, model_name: str | None) -> ReportCompareResult:
    payload = result.model_dump(exclude={"success": {"tasks": {"__all__": {"screenshots"}}}, "failure": {"tasks": {"__all__": {"screenshots"}}}})
    system = "You are a Midscene report comparison expert. Improve the diagnosis using the structured data. Return concise Chinese text. Keep root_cause <= 50 Chinese characters. Do not invent evidence."
    user = "Structured comparison data:\n" + json.dumps(payload, ensure_ascii=False)[:20000]
    model = create_chat_model(name=model_name, thinking_enabled=False, app_config=app_config, attach_tracing=False)
    response = await model.ainvoke([SystemMessage(content=system), HumanMessage(content=user)], config={"run_name": "midscene_report_compare"})
    result.model_analysis = llm_text.extract_response_text(response.content).strip()[:4000]
    return result
