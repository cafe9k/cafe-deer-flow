from __future__ import annotations

import asyncio
import uuid

from deerflow.config.app_config import AppConfig
from deerflow.runtime.user_context import get_effective_user_id

from .analyzer import build_deterministic_result, build_summary_markdown, refine_with_model
from .html_renderer import render_html
from .job_store import read_job, write_job
from .locator import locate_reports, output_dir_for_job
from .models import ReportCompareJobCreateRequest, ReportCompareJobResponse
from .parser import parse_report


async def create_report_compare_job(thread_id: str, request: ReportCompareJobCreateRequest, *, app_config: AppConfig) -> ReportCompareJobResponse:
    user_id = get_effective_user_id()
    job_id = str(uuid.uuid4())
    output_dir, output_virtual_dir = output_dir_for_job(thread_id, job_id, user_id=user_id)

    try:
        located = await asyncio.to_thread(
            locate_reports,
            thread_id,
            request.input,
            user_id=user_id,
            work_dir=output_dir,
            max_search_depth=request.options.max_search_depth,
        )
        success = await asyncio.to_thread(parse_report, located.success)
        failure = await asyncio.to_thread(parse_report, located.failure)
        result = build_deterministic_result(success, failure, located.source_notes)
        if request.options.run_model_analysis:
            try:
                result = await refine_with_model(result, app_config=app_config, model_name=request.options.model_name)
            except Exception as exc:
                result.data_notes.append(f"Model analysis failed, deterministic analysis was used: {exc}")

        result_path = f"{output_virtual_dir}/result.json"
        html_path = f"{output_virtual_dir}/report-compare.html" if request.options.generate_html else None

        (output_dir / "result.json").write_text(result.model_dump_json(indent=2), encoding="utf-8")
        summary_markdown = build_summary_markdown(result, html_path=html_path)
        (output_dir / "summary.md").write_text(summary_markdown, encoding="utf-8")
        if html_path:
            await asyncio.to_thread(render_html, result, output_dir / "report-compare.html")

        job = ReportCompareJobResponse(
            job_id=job_id,
            status="completed",
            summary_markdown=summary_markdown,
            result_path=result_path,
            html_path=html_path,
            html_artifact_url=f"/api/threads/{thread_id}/artifacts{html_path}?download=true" if html_path else None,
            result=result,
        )
    except Exception as exc:
        job = ReportCompareJobResponse(job_id=job_id, status="failed", summary_markdown="", error=str(exc))

    await asyncio.to_thread(write_job, job, output_dir)
    return job


async def get_report_compare_job(thread_id: str, job_id: str) -> ReportCompareJobResponse:
    user_id = get_effective_user_id()
    output_dir, _ = output_dir_for_job(thread_id, job_id, user_id=user_id)
    return await asyncio.to_thread(read_job, output_dir, job_id)
