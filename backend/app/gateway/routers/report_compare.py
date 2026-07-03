from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.gateway.authz import require_permission
from app.gateway.deps import get_config
from app.gateway.report_compare import create_report_compare_job, get_report_compare_job
from app.gateway.report_compare.models import ReportCompareJobCreateRequest, ReportCompareJobResponse
from deerflow.config.app_config import AppConfig

router = APIRouter(prefix="/api/threads/{thread_id}/report-compare", tags=["report-compare"])


@router.post("/jobs", response_model=ReportCompareJobResponse, summary="Create Midscene Report Compare Job")
@require_permission("threads", "write", owner_check=True, require_existing=False)
async def create_job(
    thread_id: str,
    body: ReportCompareJobCreateRequest,
    request: Request,
    config: AppConfig = Depends(get_config),
) -> ReportCompareJobResponse:
    job = await create_report_compare_job(thread_id, body, app_config=config)
    if job.status == "failed":
        raise HTTPException(status_code=400, detail=job.error or "Report compare failed")
    return job


@router.get("/jobs/{job_id}", response_model=ReportCompareJobResponse, summary="Get Midscene Report Compare Job")
@require_permission("threads", "read", owner_check=True, require_existing=False)
async def get_job(thread_id: str, job_id: str, request: Request) -> ReportCompareJobResponse:
    try:
        return await get_report_compare_job(thread_id, job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Report compare job {job_id} not found") from None
