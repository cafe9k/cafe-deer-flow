from __future__ import annotations

import os
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

from deerflow.config.paths import get_paths

from .models import ReportCompareInput

_SUCCESS_LABELS = ("success", "passed", "pass", "ok", "成功")
_FAILURE_LABELS = ("fail", "failure", "failed", "error", "失败")
_REPORT_PRIORITY_NAMES = ("success.json", "fail.json", "failure.json")
_MAX_ARCHIVE_BYTES = 500 * 1024 * 1024


@dataclass(frozen=True)
class ReportCandidate:
    label: str
    report_dir: Path
    json_path: Path
    screenshots_dir: Path | None


@dataclass(frozen=True)
class LocatedReports:
    success: ReportCandidate
    failure: ReportCandidate
    source_notes: tuple[str, ...] = ()


def resolve_virtual_path(thread_id: str, virtual_path: str, *, user_id: str) -> Path:
    return get_paths().resolve_virtual_path(thread_id, virtual_path, user_id=user_id)


def output_dir_for_job(thread_id: str, job_id: str, *, user_id: str) -> tuple[Path, str]:
    root = get_paths().sandbox_outputs_dir(thread_id, user_id=user_id) / "report-compare" / job_id
    root.mkdir(parents=True, exist_ok=True)
    return root, f"/mnt/user-data/outputs/report-compare/{job_id}"


def _safe_extract_zip(archive_path: Path, target_dir: Path) -> None:
    if not archive_path.is_file():
        raise ValueError(f"Archive not found: {archive_path}")
    if archive_path.suffix.lower() != ".zip":
        raise ValueError(f"Only .zip archives are supported: {archive_path.name}")

    target_dir.mkdir(parents=True, exist_ok=True)
    target_root = target_dir.resolve()
    total_size = 0
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            total_size += info.file_size
            if total_size > _MAX_ARCHIVE_BYTES:
                raise ValueError("Report archive is too large.")
            destination = (target_root / info.filename).resolve()
            try:
                destination.relative_to(target_root)
            except ValueError as exc:
                raise ValueError("Archive contains unsafe paths.") from exc
            destination.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as src, destination.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def _is_midscene_report_json(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() != ".json":
        return False
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    sample = text[:8192]
    return any(key in sample for key in ('"executions"', '"tasks"', '"sdkVersion"', '"groupName"'))


def find_report_json(report_dir: Path) -> Path:
    if report_dir.is_file():
        if _is_midscene_report_json(report_dir):
            return report_dir
        raise ValueError(f"Not a Midscene report JSON: {report_dir}")

    execution_jsons = sorted(report_dir.glob("*.execution.json"))
    if execution_jsons:
        return execution_jsons[0]

    for filename in _REPORT_PRIORITY_NAMES:
        candidate = report_dir / filename
        if _is_midscene_report_json(candidate):
            return candidate

    jsons = sorted(path for path in report_dir.glob("*.json") if _is_midscene_report_json(path))
    if len(jsons) == 1:
        return jsons[0]
    if not jsons:
        raise ValueError(f"No Midscene report JSON found under {report_dir}")
    raise ValueError(f"Multiple report JSON files found under {report_dir}; provide an explicit JSON path.")


def _candidate_from_path(path: Path, label: str) -> ReportCandidate:
    json_path = find_report_json(path)
    report_dir = json_path.parent
    screenshots_dir = report_dir / "screenshots"
    return ReportCandidate(
        label=label,
        report_dir=report_dir,
        json_path=json_path,
        screenshots_dir=screenshots_dir if screenshots_dir.is_dir() else None,
    )


def _label_for_path(path: Path) -> str | None:
    haystack = " ".join(part.lower() for part in path.parts[-4:])
    if any(label in haystack for label in _SUCCESS_LABELS):
        return "success"
    if any(label in haystack for label in _FAILURE_LABELS):
        return "failure"
    return None


def _depth(root: Path, path: Path) -> int:
    try:
        return len(path.relative_to(root).parts)
    except ValueError:
        return 999


def _discover_candidates(compare_dir: Path, max_depth: int) -> list[ReportCandidate]:
    candidates: list[ReportCandidate] = []
    for current_root, dir_names, file_names in os.walk(compare_dir):
        current = Path(current_root)
        if _depth(compare_dir, current) > max_depth:
            dir_names[:] = []
            continue
        if "screenshots" in current.parts:
            dir_names[:] = []
            continue
        has_json = any(name.endswith(".json") for name in file_names)
        has_screenshots = (current / "screenshots").is_dir()
        if not has_json or not has_screenshots:
            continue
        label = _label_for_path(current)
        if label is None:
            continue
        try:
            candidates.append(_candidate_from_path(current, label))
        except ValueError:
            continue
    return candidates


def _choose_labeled(candidates: list[ReportCandidate], label: str) -> ReportCandidate:
    matches = [candidate for candidate in candidates if candidate.label == label]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise ValueError(f"Could not find a {label} report in the compare directory.")
    paths = ", ".join(str(candidate.json_path) for candidate in matches)
    raise ValueError(f"Multiple {label} reports found; provide explicit paths: {paths}")


def locate_reports(
    thread_id: str,
    body: ReportCompareInput,
    *,
    user_id: str,
    work_dir: Path,
    max_search_depth: int,
) -> LocatedReports:
    notes: list[str] = []

    if body.compare_archive:
        archive = resolve_virtual_path(thread_id, body.compare_archive, user_id=user_id)
        compare_dir = work_dir / "input" / "compare"
        _safe_extract_zip(archive, compare_dir)
        notes.append(f"Extracted compare archive: {body.compare_archive}")
        candidates = _discover_candidates(compare_dir, max_search_depth)
        return LocatedReports(success=_choose_labeled(candidates, "success"), failure=_choose_labeled(candidates, "failure"), source_notes=tuple(notes))

    if body.success_archive and body.failure_archive:
        success_dir = work_dir / "input" / "success"
        failure_dir = work_dir / "input" / "failure"
        _safe_extract_zip(resolve_virtual_path(thread_id, body.success_archive, user_id=user_id), success_dir)
        _safe_extract_zip(resolve_virtual_path(thread_id, body.failure_archive, user_id=user_id), failure_dir)
        notes.append(f"Extracted success archive: {body.success_archive}")
        notes.append(f"Extracted failure archive: {body.failure_archive}")
        return LocatedReports(success=_candidate_from_path(success_dir, "success"), failure=_candidate_from_path(failure_dir, "failure"), source_notes=tuple(notes))

    if body.compare_dir:
        compare_dir = resolve_virtual_path(thread_id, body.compare_dir, user_id=user_id)
        candidates = _discover_candidates(compare_dir, max_search_depth)
        return LocatedReports(success=_choose_labeled(candidates, "success"), failure=_choose_labeled(candidates, "failure"), source_notes=tuple(notes))

    if (body.success_dir or body.success_json) and (body.failure_dir or body.failure_json):
        success_path = resolve_virtual_path(thread_id, body.success_json or body.success_dir or "", user_id=user_id)
        failure_path = resolve_virtual_path(thread_id, body.failure_json or body.failure_dir or "", user_id=user_id)
        return LocatedReports(success=_candidate_from_path(success_path, "success"), failure=_candidate_from_path(failure_path, "failure"), source_notes=tuple(notes))

    raise ValueError("Provide compare_dir, compare_archive, success/failure directories, success/failure JSON files, or success/failure archives.")
