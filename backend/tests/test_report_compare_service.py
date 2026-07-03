from __future__ import annotations

import json
import zipfile
from pathlib import Path

from app.gateway.report_compare.analyzer import build_deterministic_result, build_summary_markdown
from app.gateway.report_compare.html_renderer import render_html
from app.gateway.report_compare.locator import locate_reports
from app.gateway.report_compare.models import ReportCompareInput
from app.gateway.report_compare.parser import parse_report
from deerflow.config.paths import Paths


def _write_report(report_dir: Path, *, name: str, failed: bool = False) -> None:
    screenshots = report_dir / "screenshots"
    screenshots.mkdir(parents=True, exist_ok=True)
    (screenshots / "shot-1.png").write_bytes(b"png")
    tasks = [
        {
            "taskId": "plan-1",
            "type": "Planning",
            "subType": "Plan",
            "status": "finished",
            "param": {"userInstruction": "打开设置页"},
            "thought": "计划进入设置页",
            "uiContext": {
                "screenshot": {
                    "type": "midscene_screenshot_ref",
                    "id": "shot-1",
                    "capturedAt": 1,
                    "mimeType": "image/png",
                    "storage": "file",
                    "path": "./screenshots/shot-1.png",
                }
            },
        },
        {
            "taskId": "action-1",
            "type": "Action Space",
            "subType": "Tap",
            "status": "failed" if failed else "finished",
            "param": {"locate": {"center": [20, 30]}, "locatedPixelBbox": [10, 10, 20, 20]},
            "errorMessage": "locate bbox mismatch" if failed else None,
        },
    ]
    payload = {
        "sdkVersion": "1.0.0",
        "executions": [
            {
                "id": name,
                "name": name,
                "tasks": tasks,
            }
        ],
    }
    (report_dir / "1.execution.json").write_text(json.dumps(payload), encoding="utf-8")


def test_locate_parse_and_render_report_compare_from_directory(tmp_path, monkeypatch):
    paths = Paths(tmp_path)
    monkeypatch.setattr("app.gateway.report_compare.locator.get_paths", lambda: paths)
    thread_id = "thread1"
    user_id = "user1"
    compare_dir = paths.sandbox_uploads_dir(thread_id, user_id=user_id) / "case"
    _write_report(compare_dir / "success", name="success")
    _write_report(compare_dir / "failure", name="failure", failed=True)

    work_dir = paths.sandbox_outputs_dir(thread_id, user_id=user_id) / "report-compare" / "job1"
    located = locate_reports(
        thread_id,
        ReportCompareInput(compare_dir="/mnt/user-data/uploads/case"),
        user_id=user_id,
        work_dir=work_dir,
        max_search_depth=3,
    )

    success = parse_report(located.success)
    failure = parse_report(located.failure)
    result = build_deterministic_result(success, failure, located.source_notes)
    summary = build_summary_markdown(result, html_path="/mnt/user-data/outputs/report-compare/job1/report-compare.html")
    html_path = work_dir / "report-compare.html"
    render_html(result, html_path)

    assert success.total_tasks == 2
    assert failure.failed_tasks == 1
    assert result.root_cause == "定位坐标偏移导致操作目标错误"
    assert "## 分叉点分析" in summary
    assert "Midscene Report Compare" in html_path.read_text(encoding="utf-8")


def test_locate_reports_from_compare_archive(tmp_path, monkeypatch):
    paths = Paths(tmp_path)
    monkeypatch.setattr("app.gateway.report_compare.locator.get_paths", lambda: paths)
    thread_id = "thread1"
    user_id = "user1"
    source_dir = tmp_path / "source"
    _write_report(source_dir / "success", name="success")
    _write_report(source_dir / "failure", name="failure", failed=True)

    uploads = paths.sandbox_uploads_dir(thread_id, user_id=user_id)
    uploads.mkdir(parents=True, exist_ok=True)
    archive_path = uploads / "compare.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for path in source_dir.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(source_dir))

    work_dir = paths.sandbox_outputs_dir(thread_id, user_id=user_id) / "report-compare" / "job2"
    located = locate_reports(
        thread_id,
        ReportCompareInput(compare_archive="/mnt/user-data/uploads/compare.zip"),
        user_id=user_id,
        work_dir=work_dir,
        max_search_depth=3,
    )

    assert located.success.json_path.name == "1.execution.json"
    assert located.failure.json_path.name == "1.execution.json"
    assert "Extracted compare archive" in located.source_notes[0]
