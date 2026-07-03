from __future__ import annotations

import html
import json
from pathlib import Path

from .models import ReportCompareResult


def _e(value: object) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def render_html(result: ReportCompareResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suggestions = "".join(f"<li>{_e(item)}</li>" for item in result.repair_suggestions)
    notes = "".join(f"<li>{_e(item)}</li>" for item in result.data_notes)
    model_analysis = f"<section><h2>Model Analysis</h2><pre>{_e(result.model_analysis)}</pre></section>" if result.model_analysis else ""
    metrics_rows = "".join(f"<tr><th>{_e(key)}</th><td>{_e(value)}</td></tr>" for key, value in result.metrics.model_dump().items())
    payload = _e(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
    output_path.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Midscene Report Compare</title>
  <style>
    :root {{ color-scheme: light; --ink:#18202f; --muted:#5d6678; --line:#d9dde7; --accent:#0f766e; --danger:#b42318; --warn:#a15c00; }}
    body {{ margin:0; font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:#f7f8fb; }}
    header {{ position:sticky; top:0; z-index:1; display:flex; gap:16px; align-items:center; padding:14px 24px; background:#ffffffee; border-bottom:1px solid var(--line); backdrop-filter:blur(8px); }}
    main {{ max-width:1160px; margin:0 auto; padding:24px; }}
    section {{ margin:0 0 18px; padding:18px; background:white; border:1px solid var(--line); border-radius:8px; }}
    h1 {{ margin:0; font-size:18px; }}
    h2 {{ margin:0 0 12px; font-size:16px; color:var(--accent); }}
    .root {{ padding:14px; border-left:5px solid var(--danger); background:#fff2f0; font-weight:700; font-size:18px; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }}
    .card {{ padding:12px; border:1px solid var(--line); border-radius:8px; background:#fbfcff; }}
    .label {{ display:block; color:var(--muted); font-size:12px; }}
    table {{ width:100%; border-collapse:collapse; }}
    th,td {{ text-align:left; vertical-align:top; padding:8px 10px; border-bottom:1px solid var(--line); }}
    th {{ width:220px; color:var(--muted); font-weight:600; }}
    pre {{ white-space:pre-wrap; overflow:auto; background:#0f172a; color:#e2e8f0; padding:12px; border-radius:6px; }}
    @media (max-width: 760px) {{ .grid {{ grid-template-columns:1fr; }} main {{ padding:14px; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Midscene Report Compare</h1>
    <span>Root cause: {_e(result.root_cause)}</span>
  </header>
  <main>
    <section>
      <h2>Executive Summary</h2>
      <div class="grid">
        <div class="card"><span class="label">Failed step</span>{_e(result.failed_step)}</div>
        <div class="card"><span class="label">Confidence</span>{"Lower: missing screenshots" if result.metrics.missing_screenshots else "Normal"}</div>
        <div class="card"><span class="label">Divergence</span>{_e(result.divergence.title)}</div>
      </div>
      <p class="root">{_e(result.root_cause)}</p>
    </section>
    <section>
      <h2>Repair Suggestions</h2>
      <ul>{suggestions}</ul>
    </section>
    <section>
      <h2>分叉点分析</h2>
      <table>
        <tr><th>Divergence point</th><td>{_e(result.divergence.title)}</td></tr>
        <tr><th>Success</th><td>{_e(result.divergence.success)}</td></tr>
        <tr><th>Failure</th><td>{_e(result.divergence.failure)}</td></tr>
      </table>
    </section>
    {model_analysis}
    <section>
      <h2>Data And Key Metrics</h2>
      <ul>{notes}</ul>
      <table>{metrics_rows}</table>
    </section>
    <section>
      <h2>Raw Structured Result</h2>
      <pre>{payload}</pre>
    </section>
  </main>
</body>
</html>
""",
        encoding="utf-8",
    )
