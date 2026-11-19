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

  if (error) return <EmptyState title="Data journey unavailable" description={error} />;
  if (!datasets) return <Skeleton className="h-48" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Data journey</h1>
        <p className="mt-1 text-muted">
          See where each file came from and how it moved through upload → quality → cleaning → validation → insights.
        </p>
      </div>
      {datasets.length === 0 ? (
        <EmptyState
          title="No journey recorded yet"
          description="Upload a dataset and run processing to see how your data was prepared."
        />
      ) : (
        <div className="space-y-4">
          {datasets.map((dataset) => (
            <Card key={dataset.id}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="font-display text-lg font-semibold">{dataset.name}</h2>
                  <p className="text-sm text-muted">
                    {dataset.category} · status: {dataset.status}
                  </p>
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
                        Step: {edge.stage}. {edge.description}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="mt-4 text-sm text-muted">
                  This file is uploaded, but processing has not recorded a journey yet. Open the dataset and run
                  processing.
                </p>
              )}
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
