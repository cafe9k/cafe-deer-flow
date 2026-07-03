export interface ReportCompareInput {
  compare_dir?: string;
  success_dir?: string;
  failure_dir?: string;
  success_json?: string;
  failure_json?: string;
  compare_archive?: string;
  success_archive?: string;
  failure_archive?: string;
}

export interface ReportCompareOptions {
  run_model_analysis: boolean;
  generate_html: boolean;
  max_search_depth: number;
  model_name?: string;
}

export interface TaskSummary {
  index: number;
  task_id?: string;
  type?: string;
  sub_type?: string;
  status?: string;
  thought?: string;
  param?: string;
  response?: string;
  result?: string;
  error_message?: string;
  hit_by_from?: string;
  bbox?: string;
  located_pixel_bbox?: string;
  locate_center?: string;
  screenshots: string[];
}

export interface ExecutionSummary {
  label: "success" | "failure";
  report_dir: string;
  json_path: string;
  screenshots_dir?: string;
  execution_name?: string;
  execution_id?: string;
  sdk_version?: string;
  total_tasks: number;
  planning_tasks: number;
  action_tasks: number;
  failed_tasks: number;
  cancelled_tasks: number;
  dominant_action_types: string[];
  missing_screenshots: string[];
  tasks: TaskSummary[];
}

export interface DivergenceSummary {
  index?: number | null;
  title: string;
  success: string;
  failure: string;
}

export interface ReportCompareMetrics {
  parsed_dump_count: number;
  execution_count: number;
  success_total_tasks: number;
  failure_total_tasks: number;
  success_planning_tasks: number;
  failure_planning_tasks: number;
  success_action_tasks: number;
  failure_action_tasks: number;
  success_failed_tasks: number;
  failure_failed_tasks: number;
  dominant_action_types: string[];
  missing_screenshots: string[];
}

export interface ReportCompareResult {
  failed_step: string;
  root_cause: string;
  repair_suggestions: string[];
  divergence: DivergenceSummary;
  data_notes: string[];
  success: ExecutionSummary;
  failure: ExecutionSummary;
  metrics: ReportCompareMetrics;
  model_analysis?: string;
}

export interface ReportCompareJobCreateRequest {
  input: ReportCompareInput;
  options: ReportCompareOptions;
}

export interface ReportCompareJobResponse {
  job_id: string;
  status: "completed" | "failed";
  summary_markdown: string;
  result_path?: string;
  html_path?: string;
  html_artifact_url?: string;
  error?: string;
  result?: ReportCompareResult;
}
