"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiGet, exportUrl } from "@/lib/api";
import { Badge, Button, Card, EmptyState, Skeleton, statusTone } from "@/components/ui";

export default function PipelineDetailPage() {
  const { id } = useParams();
  const [run, setRun] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet(`/pipelines/${id}`)
      .then(setRun)
      .catch((err) => setError(err.message));
  }, [id]);

  if (error) return <EmptyState title="Run unavailable" description={error} />;
  if (!run) return <Skeleton className="h-64" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold">Pipeline run #{run.id}</h1>
          <p className="mt-1 text-muted">{run.dataset_name}</p>
        </div>
        <div className="flex gap-2">
          <Badge tone={statusTone(run.status)}>{run.status}</Badge>
          <a href={exportUrl(`/pipelines/${id}/export.json`)} target="_blank">
            <Button variant="secondary">Download report</Button>
          </a>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        {[
          ["Processed", run.records_processed],
          ["Rejected", run.records_rejected],
          ["Loaded", run.records_loaded],
          ["Duration", run.duration_seconds ? `${run.duration_seconds}s` : "—"],
        ].map(([label, value]) => (
          <Card key={label as string}>
            <div className="text-sm text-muted">{label}</div>
            <div className="mt-2 font-display text-2xl font-bold">{value}</div>
          </Card>
        ))}
      </div>

      {run.error_message ? <Card className="border-red-200 bg-red-50 text-danger">{run.error_message}</Card> : null}

      <div className="space-y-3">
        {run.stages.map((stage: any) => (
          <Card key={stage.name}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="font-semibold uppercase tracking-wide">{stage.name}</div>
                <div className="text-sm text-muted">
                  in {stage.records_in} → out {stage.records_out}
                  {stage.duration_seconds != null ? ` · ${stage.duration_seconds}s` : ""}
                </div>
              </div>
              <Badge tone={statusTone(stage.status)}>{stage.status}</Badge>
            </div>
            {stage.error_message ? <p className="mt-2 text-sm text-danger">{stage.error_message}</p> : null}
            {stage.details && Object.keys(stage.details).length > 0 ? (
              <pre className="mt-3 overflow-x-auto rounded-xl bg-slate-50 p-3 text-xs text-muted">
                {JSON.stringify(stage.details, null, 2)}
              </pre>
            ) : null}
          </Card>
        ))}
      </div>
    </div>
  );
}
