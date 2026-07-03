from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReportCompareInput(BaseModel):
    compare_dir: str | None = Field(default=None, description="Virtual directory containing success/failure split reports.")
    success_dir: str | None = Field(default=None, description="Virtual directory containing the successful split report.")
    failure_dir: str | None = Field(default=None, description="Virtual directory containing the failed split report.")
    success_json: str | None = Field(default=None, description="Virtual path to a successful execution JSON file.")
    failure_json: str | None = Field(default=None, description="Virtual path to a failed execution JSON file.")
    compare_archive: str | None = Field(default=None, description="Virtual path to a zip archive containing success/failure reports.")
    success_archive: str | None = Field(default=None, description="Virtual path to a zip archive containing the successful report.")
    failure_archive: str | None = Field(default=None, description="Virtual path to a zip archive containing the failed report.")


class ReportCompareOptions(BaseModel):
    run_model_analysis: bool = Field(default=True, description="Use the configured model to refine the root-cause analysis.")
    generate_html: bool = Field(default=True, description="Generate a static HTML report artifact.")
    max_search_depth: int = Field(default=3, ge=1, le=6, description="Maximum recursive depth for report discovery.")
    model_name: str | None = Field(default=None, description="Optional configured DeerFlow model name.")


class ReportCompareJobCreateRequest(BaseModel):
    input: ReportCompareInput
    options: ReportCompareOptions = Field(default_factory=ReportCompareOptions)


class TaskSummary(BaseModel):
    index: int
    task_id: str | None = None
    type: str | None = None
    sub_type: str | None = None
    status: str | None = None
    thought: str | None = None
    param: str | None = None
    response: str | None = None
    result: str | None = None
    error_message: str | None = None
    hit_by_from: str | None = None
    bbox: str | None = None
    located_pixel_bbox: str | None = None
    locate_center: str | None = None
    screenshots: list[str] = Field(default_factory=list)


class ExecutionSummary(BaseModel):
    label: Literal["success", "failure"]
    report_dir: str
    json_path: str
    screenshots_dir: str | None = None
    execution_name: str | None = None
    execution_id: str | None = None
    sdk_version: str | None = None
    total_tasks: int = 0
    planning_tasks: int = 0
    action_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    dominant_action_types: list[str] = Field(default_factory=list)
    missing_screenshots: list[str] = Field(default_factory=list)
    tasks: list[TaskSummary] = Field(default_factory=list)


class DivergenceSummary(BaseModel):
    index: int | None = None
    title: str
    success: str
    failure: str


class ReportCompareMetrics(BaseModel):
    parsed_dump_count: int = 2
    execution_count: int = 2
    success_total_tasks: int = 0
    failure_total_tasks: int = 0
    success_planning_tasks: int = 0
    failure_planning_tasks: int = 0
    success_action_tasks: int = 0
    failure_action_tasks: int = 0
    success_failed_tasks: int = 0
    failure_failed_tasks: int = 0
    dominant_action_types: list[str] = Field(default_factory=list)
    missing_screenshots: list[str] = Field(default_factory=list)


class ReportCompareResult(BaseModel):
    failed_step: str
    root_cause: str
    repair_suggestions: list[str]
    divergence: DivergenceSummary
    data_notes: list[str]
    success: ExecutionSummary
    failure: ExecutionSummary
    metrics: ReportCompareMetrics
    model_analysis: str | None = None


class ReportCompareJobResponse(BaseModel):
    job_id: str
    status: Literal["completed", "failed"]
    summary_markdown: str
    result_path: str | None = None
    html_path: str | None = None
    html_artifact_url: str | None = None
    error: str | None = None
    result: ReportCompareResult | None = None
