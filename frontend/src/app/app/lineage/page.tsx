"use client";

import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { Badge, Card, EmptyState, Skeleton } from "@/components/ui";

export default function LineagePage() {
  const [datasets, setDatasets] = useState<any[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<{ datasets: any[] }>("/lineage")
      .then((data) => setDatasets(data.datasets))
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <EmptyState title="Lineage unavailable" description={error} />;
  if (!datasets) return <Skeleton className="h-48" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Data lineage</h1>
        <p className="mt-1 text-muted">How each file moves from upload → bronze → silver → validated → gold.</p>
      </div>
      {datasets.length === 0 ? (
        <EmptyState title="No lineage yet" description="Run a pipeline on a dataset to record lineage edges." />
      ) : (
        <div className="space-y-4">
          {datasets.map((dataset) => (
            <Card key={dataset.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="font-display text-lg font-semibold">{dataset.name}</h2>
                  <p className="text-sm text-muted">{dataset.category} · {dataset.status}</p>
                </div>
                {dataset.is_sample ? <Badge tone="accent">sample</Badge> : null}
              </div>
              {dataset.edges?.length ? (
                <div className="mt-4 space-y-3">
                  {dataset.edges.map((edge: any, index: number) => (
                    <div key={index} className="rounded-xl bg-slate-50 px-4 py-3 text-sm">
                      <div className="font-semibold">
                        {edge.source} → {edge.target}
                      </div>
                      <div className="mt-1 text-muted">
                        Stage: {edge.stage}. {edge.description}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted">No pipeline lineage recorded for this dataset yet.</p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
