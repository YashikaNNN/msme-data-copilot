"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { Badge, Card, EmptyState, Skeleton, statusTone } from "@/components/ui";

export default function PipelinesPage() {
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<{ items: any[] }>("/pipelines")
      .then((data) => setItems(data.items))
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <EmptyState title="Pipelines unavailable" description={error} />;
  if (!items) return <Skeleton className="h-40" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Pipeline monitoring</h1>
        <p className="mt-1 text-muted">Extract → Profile → Clean → Validate → Transform → Load</p>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No pipeline runs" description="Open a dataset and click Run pipeline." />
      ) : (
        <div className="space-y-3">
          {items.map((run) => (
            <Link key={run.id} href={`/app/pipelines/${run.id}`}>
              <Card className="mb-3 hover:border-accent/40">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <div className="font-semibold">{run.dataset_name}</div>
                    <div className="text-sm text-muted">
                      Processed {run.records_processed} · Rejected {run.records_rejected} · Loaded {run.records_loaded}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={statusTone(run.status)}>{run.status}</Badge>
                    <span className="text-xs text-muted">
                      {run.started_at ? new Date(run.started_at).toLocaleString() : ""}
                    </span>
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
