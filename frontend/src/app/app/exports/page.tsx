"use client";

import { useEffect, useState } from "react";
import { apiGet, Dataset, downloadAuthenticated } from "@/lib/api";
import { Button, Card, EmptyState, Select, Skeleton } from "@/components/ui";

export default function ExportsPage() {
  const [datasets, setDatasets] = useState<Dataset[] | null>(null);
  const [datasetId, setDatasetId] = useState("");
  const [pipelines, setPipelines] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([apiGet<{ items: Dataset[] }>("/datasets"), apiGet<{ items: any[] }>("/pipelines")])
      .then(([ds, runs]) => {
        setDatasets(ds.items);
        if (ds.items[0]) setDatasetId(String(ds.items[0].id));
        setPipelines(runs.items);
      })
      .catch((err) => setError(err.message));
  }, []);

  async function download(path: string, name: string) {
    try {
      setMessage("");
      setError("");
      await downloadAuthenticated(path, name);
      setMessage(`Downloaded ${name}`);
    } catch (err: any) {
      setError(err.message || "Download failed");
    }
  }

  if (error && !datasets) return <EmptyState title="Downloads unavailable" description={error} />;
  if (!datasets) return <Skeleton className="h-48" />;

  const kinds = [
    ["raw.csv", "Original uploaded file", "original.csv"],
    ["cleaned.csv", "Cleaned & validated CSV", "cleaned.csv"],
    ["cleaned.xlsx", "Cleaned & validated Excel", "cleaned.xlsx"],
    ["quarantine.csv", "Rejected / quarantined rows", "quarantine.csv"],
    ["quality.csv", "Quality issue report", "quality.csv"],
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Downloads</h1>
        <p className="mt-1 text-muted">
          Download your original files, cleaned datasets, quarantine lists, and analytics summaries.
        </p>
      </div>

      {message ? <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm text-accent-2">{message}</p> : null}
      {error ? <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p> : null}

      <Card>
        <h2 className="font-display text-lg font-semibold">Dataset downloads</h2>
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
                    {dataset.name} · {dataset.status}
                  </option>
                ))}
              </Select>
            </label>
            <div className="flex flex-wrap gap-2">
              {kinds.map(([kind, label, filename]) => (
                <Button
                  key={kind}
                  variant="secondary"
                  onClick={() => download(`/datasets/${datasetId}/export/${kind}`, filename)}
                >
                  {label}
                </Button>
              ))}
            </div>
            <p className="text-xs text-muted">
              Cleaned downloads require a successful processing run so quarantined rows stay out of the file.
            </p>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="font-display text-lg font-semibold">Analytics summary</h2>
        <p className="mt-1 text-sm text-muted">Current calculated KPIs for your business. Missing metrics stay blank.</p>
        <div className="mt-4">
          <Button onClick={() => download("/analytics/export.csv", "analytics-summary.csv")}>
            Download analytics CSV
          </Button>
        </div>
      </Card>

      <Card>
        <h2 className="font-display text-lg font-semibold">Processing reports</h2>
        {pipelines.length === 0 ? (
          <div className="mt-4">
            <EmptyState title="No processing runs" description="Process a dataset to export execution details." />
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
                <Button
                  variant="secondary"
                  onClick={() => download(`/pipelines/${run.id}/export.json`, `pipeline-${run.id}.json`)}
                >
                  Download JSON
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
