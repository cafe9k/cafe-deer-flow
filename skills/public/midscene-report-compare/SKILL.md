---
name: midscene-report-compare
description: "Use when the user wants to compare two Midscene split reports for the same operation to identify planning drift, locate/bbox issues, cache drift, or execution differences."
---

# Midscene Report Comparison

Use this skill when the user asks to compare successful and failed Midscene reports, including requests such as:

- "对比这两份 Midscene 报告"
- "分析为什么这次失败了"
- "定位 planning drift"
- "同样操作成功和失败有什么不同"

## Preferred Workflow In DeerFlow

DeerFlow has a built-in Gateway report comparison API. Prefer calling it instead of manually parsing large JSON files in the conversation.

1. Make sure the reports are available in the current thread under `/mnt/user-data/uploads` or `/mnt/user-data/outputs`.
2. Accept one of these input shapes:
   - `compare_archive`: a zip containing success/failure report directories
   - `success_archive` and `failure_archive`: two separate zip files
   - `compare_dir`: one directory containing success/failure split reports
   - `success_dir` and `failure_dir`: explicit split report directories
   - `success_json` and `failure_json`: explicit execution JSON files
3. Call:

```http
POST /api/threads/{thread_id}/report-compare/jobs
```

4. Return the generated markdown summary and point the user to the HTML artifact path.

## Expected Report Shape

Prefer a compare directory like:

```text
compare/
├── success/
│   ├── 1.execution.json
│   └── screenshots/
└── failure/
    ├── 1.execution.json
    └── screenshots/
```

The Gateway also accepts `success.json`, `fail.json`, `failure.json`, or a single Midscene JSON file with `executions`, `tasks`, or `sdkVersion` keys.

## Output Requirements

The result should be root-cause first and include:

- failed step
- root cause within 50 Chinese characters
- repair suggestions
- first divergence analysis
- data notes and screenshot completeness
- generated HTML report path
