from __future__ import annotations

import json
from pathlib import Path

from .models import ReportCompareJobResponse


def write_job(job: ReportCompareJobResponse, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "job.json").write_text(job.model_dump_json(indent=2), encoding="utf-8")


def read_job(output_dir: Path, job_id: str) -> ReportCompareJobResponse:
    path = output_dir / "job.json"
    if not path.is_file():
        raise FileNotFoundError(job_id)
    return ReportCompareJobResponse.model_validate(json.loads(path.read_text(encoding="utf-8")))
