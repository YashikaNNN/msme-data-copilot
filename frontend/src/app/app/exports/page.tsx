"use client";

import { useEffect, useState } from "react";
import { apiGet, Dataset, exportUrl } from "@/lib/api";
import { Button, Card, EmptyState, Select, Skeleton } from "@/components/ui";

export default function ExportsPage() {
  const [datasets, setDatasets] = useState<Dataset[] | null>(null);
  const [datasetId, setDatasetId] = useState("");
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([apiGet<{ items: Dataset[] }>("/datasets"), apiGet<{ items: any[] }>("/pipelines")])
      .then(([ds, runs]) => {
        setDatasets(ds.items);
        if (ds.items[0]) setDatasetId(String(ds.items[0].id));
        setPipelines(runs.items);
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <EmptyState title="Exports unavailable" description={error} />;
  if (!datasets) return <Skeleton className="h-48" />;

  const kinds = [
    ["raw.csv", "Original CSV (bronze)"],
    ["cleaned.csv", "Trusted cleaned CSV"],
    ["cleaned.xlsx", "Trusted cleaned Excel"],
    ["quarantine.csv", "Quarantined rows"],
    ["quality.csv", "Quality issue report"],
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Exports & reports</h1>
        <p className="mt-1 text-muted">Download originals, trusted cleaned files, quality reports, and analytics summaries.</p>
      </div>

      <Card>
        <h2 className="font-display text-lg font-semibold">Dataset exports</h2>
        {datasets.length === 0 ? (
          <div className="mt-4">
            <EmptyState title="No datasets" description="Upload or load sample data before exporting." />
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            <label className="block max-w-md space-y-2 text-sm">
              <span className="font-semibold">Choose dataset</span>
              <Select value={datasetId} onChange={(e) => setDatasetId(e.target.value)}>
                {datasets.map((dataset) => (
                  <option key={dataset.id} value={dataset.id}>
                    {dataset.name}
                  </option>
                ))}
              </Select>
            </label>
            <div className="flex flex-wrap gap-2">
              {kinds.map(([kind, label]) => (
                <a key={kind} href={exportUrl(`/datasets/${datasetId}/export/${kind}`)}>
                  <Button variant="secondary">{label}</Button>
                </a>
              ))}
            </div>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="font-display text-lg font-semibold">Analytics summary</h2>
        <p className="mt-1 text-sm text-muted">Exports current calculated KPIs. Missing metrics stay blank with notes.</p>
        <div className="mt-4">
          <a href={exportUrl("/analytics/export.csv")}>
            <Button>Download analytics CSV</Button>
          </a>
        </div>
      </Card>

      <Card>
        <h2 className="font-display text-lg font-semibold">Pipeline reports</h2>
        {pipelines.length === 0 ? (
          <div className="mt-4">
            <EmptyState title="No pipeline runs" description="Run a pipeline to export execution details." />
          </div>
        ) : (
          <div className="mt-4 space-y-2">
            {pipelines.slice(0, 8).map((run) => (
              <div key={run.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl bg-slate-50 px-4 py-3">
                <div className="text-sm">
                  <div className="font-semibold">{run.dataset_name}</div>
                  <div className="text-muted">
                    Run #{run.id} · {run.status}
                  </div>
                </div>
                <a href={exportUrl(`/pipelines/${run.id}/export.json`)}>
                  <Button variant="secondary">Download JSON</Button>
                </a>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
