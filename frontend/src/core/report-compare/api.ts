import { fetch } from "@/core/api/fetcher";
import { getBackendBaseURL } from "@/core/config";

import type {
  ReportCompareJobCreateRequest,
  ReportCompareJobResponse,
} from "./types";

async function readErrorDetail(response: Response): Promise<string> {
  const data = (await response.json().catch(() => ({}))) as {
    detail?: string;
  };
  return data.detail ?? `HTTP ${response.status}: ${response.statusText}`;
}

export async function createReportCompareJob(
  threadId: string,
  body: ReportCompareJobCreateRequest,
): Promise<ReportCompareJobResponse> {
  const response = await fetch(
    `${getBackendBaseURL()}/api/threads/${threadId}/report-compare/jobs`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    },
  );

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json();
}

export async function getReportCompareJob(
  threadId: string,
  jobId: string,
): Promise<ReportCompareJobResponse> {
  const response = await fetch(
    `${getBackendBaseURL()}/api/threads/${threadId}/report-compare/jobs/${jobId}`,
  );

  if (!response.ok) {
    throw new Error(await readErrorDetail(response));
  }

  return response.json();
}

export function resolveReportCompareArtifactURL(path: string): string {
  if (path.startsWith("http://") || path.startsWith("https://")) {
    return path;
  }
  return `${getBackendBaseURL()}${path}`;
}
