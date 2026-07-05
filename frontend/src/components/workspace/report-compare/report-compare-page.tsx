"use client";

import {
  DownloadIcon,
  FileArchiveIcon,
  FileSearchIcon,
  PlayIcon,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  WorkspaceBody,
  WorkspaceContainer,
  WorkspaceHeader,
} from "@/components/workspace/workspace-container";
import { useI18n } from "@/core/i18n/hooks";
import {
  resolveReportCompareArtifactURL,
  useCreateReportCompareJob,
  type ReportCompareInput,
  type ReportCompareJobResponse,
} from "@/core/report-compare";
import { uploadFiles } from "@/core/uploads";
import { cn } from "@/lib/utils";

function createLocalThreadId() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return `report-compare-${crypto.randomUUID()}`;
  }
  return `report-compare-${Date.now()}`;
}

export function ReportComparePage() {
  const { t } = useI18n();
  const [threadId] = useState(createLocalThreadId);
  const [successArchive, setSuccessArchive] = useState<File | null>(null);
  const [failureArchive, setFailureArchive] = useState<File | null>(null);
  const [result, setResult] = useState<ReportCompareJobResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const createJob = useCreateReportCompareJob(threadId);
  const busy = createJob.isPending;

  useEffect(() => {
    document.title = `${t.reportCompare.title} - ${t.pages.appName}`;
  }, [t.reportCompare.title, t.pages.appName]);

  const canSubmit = useMemo(
    () => !!successArchive && !!failureArchive,
    [successArchive, failureArchive],
  );

  async function handleSubmit() {
    setError(null);
    setResult(null);
    try {
      const input: ReportCompareInput = {};
      if (successArchive && failureArchive) {
        const uploaded = await uploadFiles(threadId, [
          successArchive,
          failureArchive,
        ]);
        input.success_archive = uploaded.files[0]?.virtual_path;
        input.failure_archive = uploaded.files[1]?.virtual_path;
      }

      const response = await createJob.mutateAsync({
        input,
        options: {
          run_model_analysis: true,
          generate_html: true,
          max_search_depth: 3,
        },
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  return (
    <WorkspaceContainer>
      <WorkspaceHeader />
      <WorkspaceBody>
        <div className="flex size-full flex-col overflow-auto">
          <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-5 p-4 md:p-6">
            <section className="flex flex-col gap-2 border-b pb-4">
              <div className="flex items-center gap-2">
                <FileSearchIcon className="text-primary size-5" />
                <h1 className="text-xl font-semibold">
                  {t.reportCompare.title}
                </h1>
              </div>
              <p className="text-muted-foreground max-w-3xl text-sm">
                {t.reportCompare.description}
              </p>
            </section>

            <section className="flex flex-col gap-4">
              <div className="bg-background flex flex-col gap-4 rounded-lg border p-4">
                <div className="flex items-center gap-2">
                  <FileArchiveIcon className="size-4" />
                  <h2 className="text-sm font-semibold">
                    {t.reportCompare.inputTitle}
                  </h2>
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <FileInput
                    label={t.reportCompare.successArchive}
                    file={successArchive}
                    onFile={setSuccessArchive}
                  />
                  <FileInput
                    label={t.reportCompare.failureArchive}
                    file={failureArchive}
                    onFile={setFailureArchive}
                  />
                </div>
              </div>

              <div className="flex flex-col justify-end">
                <Button onClick={handleSubmit} disabled={!canSubmit || busy}>
                  <PlayIcon />
                  {busy ? t.reportCompare.running : t.reportCompare.start}
                </Button>
              </div>
            </section>

            {error && (
              <Alert variant="destructive">
                <AlertTitle>{t.reportCompare.failed}</AlertTitle>
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {result && <ReportCompareResultView result={result} />}
          </main>
        </div>
      </WorkspaceBody>
    </WorkspaceContainer>
  );
}

function FileInput({
  label,
  file,
  onFile,
  disabled,
}: {
  label: string;
  file: File | null;
  onFile: (file: File | null) => void;
  disabled?: boolean;
}) {
  return (
    <label
      className={cn(
        "flex min-h-28 cursor-pointer flex-col justify-center gap-2 rounded-lg border border-dashed p-3 text-sm",
        disabled && "cursor-not-allowed opacity-50",
      )}
    >
      <span className="font-medium">{label}</span>
      <span className="text-muted-foreground text-xs">
        {file ? file.name : "ZIP"}
      </span>
      <Input
        className="sr-only"
        type="file"
        accept=".zip,application/zip"
        disabled={disabled}
        onChange={(event) => onFile(event.target.files?.[0] ?? null)}
      />
    </label>
  );
}

function ReportCompareResultView({
  result,
}: {
  result: ReportCompareJobResponse;
}) {
  const { t } = useI18n();
  const compare = result.result;
  if (!compare) {
    return null;
  }
  const htmlURL = result.html_artifact_url
    ? resolveReportCompareArtifactURL(result.html_artifact_url)
    : null;
  return (
    <section className="flex flex-col gap-4">
      <div className="bg-background rounded-lg border p-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="secondary">{result.status}</Badge>
          <span className="text-muted-foreground text-sm">{result.job_id}</span>
          {htmlURL && (
            <Button size="sm" variant="outline" asChild className="ml-auto">
              <a href={htmlURL} target="_blank" rel="noreferrer">
                <DownloadIcon />
                {t.reportCompare.downloadHtml}
              </a>
            </Button>
          )}
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-3">
          <Metric
            label={t.reportCompare.failedStep}
            value={compare.failed_step}
          />
          <Metric
            label={t.reportCompare.rootCause}
            value={compare.root_cause}
          />
          <Metric
            label={t.reportCompare.divergence}
            value={compare.divergence.title}
          />
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <ResultSection title={t.reportCompare.repairSuggestions}>
          <ul className="space-y-2 text-sm">
            {compare.repair_suggestions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </ResultSection>
        <ResultSection title={t.reportCompare.dataMetrics}>
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <MetricLine
              label="success tasks"
              value={compare.metrics.success_total_tasks}
            />
            <MetricLine
              label="failure tasks"
              value={compare.metrics.failure_total_tasks}
            />
            <MetricLine
              label="success planning"
              value={compare.metrics.success_planning_tasks}
            />
            <MetricLine
              label="failure planning"
              value={compare.metrics.failure_planning_tasks}
            />
          </dl>
        </ResultSection>
      </div>

      <ResultSection title={t.reportCompare.divergenceAnalysis}>
        <div className="grid gap-3 text-sm md:grid-cols-2">
          <div>
            <div className="mb-1 font-medium">Success</div>
            <Textarea readOnly value={compare.divergence.success} rows={6} />
          </div>
          <div>
            <div className="mb-1 font-medium">Failure</div>
            <Textarea readOnly value={compare.divergence.failure} rows={6} />
          </div>
        </div>
      </ResultSection>

      {compare.model_analysis && (
        <ResultSection title={t.reportCompare.modelAnalysisResult}>
          <Textarea readOnly value={compare.model_analysis} rows={8} />
        </ResultSection>
      )}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-muted/30 rounded-lg border p-3">
      <div className="text-muted-foreground text-xs">{label}</div>
      <div className="mt-1 line-clamp-3 text-sm font-medium">{value}</div>
    </div>
  );
}

function MetricLine({ label, value }: { label: string; value: number }) {
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium">{value}</dd>
    </>
  );
}

function ResultSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-background rounded-lg border p-4">
      <h2 className="mb-3 text-sm font-semibold">{title}</h2>
      {children}
    </section>
  );
}
