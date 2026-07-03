import { useMutation, useQuery } from "@tanstack/react-query";

import { createReportCompareJob, getReportCompareJob } from "./api";
import type {
  ReportCompareJobCreateRequest,
  ReportCompareJobResponse,
} from "./types";

export function useCreateReportCompareJob(threadId: string) {
  return useMutation<
    ReportCompareJobResponse,
    Error,
    ReportCompareJobCreateRequest
  >({
    mutationFn: (body) => createReportCompareJob(threadId, body),
  });
}

export function useReportCompareJob(threadId: string, jobId?: string) {
  return useQuery({
    queryKey: ["report-compare", threadId, jobId],
    queryFn: () => getReportCompareJob(threadId, jobId ?? ""),
    enabled: !!threadId && !!jobId,
  });
}
