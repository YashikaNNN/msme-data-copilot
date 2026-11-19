"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet, Dataset } from "@/lib/api";
import { Badge, Card, EmptyState, Skeleton, statusTone } from "@/components/ui";

export default function DatasetsPage() {
  const [items, setItems] = useState<Dataset[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<{ items: Dataset[] }>("/datasets")
      .then((data) => setItems(data.items))
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <EmptyState title="Could not load datasets" description={error} />;
  if (!items) return <Skeleton className="h-40" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Datasets</h1>
        <p className="mt-1 text-muted">Browse uploaded files, profiles, and processing status.</p>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No datasets" description="Upload a file or load the labelled sample workspace." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {items.map((dataset) => (
            <Link key={dataset.id} href={`/app/datasets/${dataset.id}`}>
              <Card className="h-full transition hover:border-accent/40">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="font-display text-lg font-semibold">{dataset.name}</h2>
                    <p className="mt-1 text-sm text-muted">{dataset.description || "No description"}</p>
                  </div>
                  <Badge tone={statusTone(dataset.status)}>{dataset.status}</Badge>
                </div>
                <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted">
                  <Badge tone="accent">{dataset.category}</Badge>
                  <span>{dataset.row_count} rows</span>
                  <span>{dataset.column_count} columns</span>
                  <span>Quality {dataset.quality_score ?? "—"}%</span>
                  {dataset.is_sample ? <Badge>sample</Badge> : null}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
