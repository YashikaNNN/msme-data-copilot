"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { Badge, Card, EmptyState, Skeleton } from "@/components/ui";

export default function QualityOverviewPage() {
  const [items, setItems] = useState<any[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<{ items: any[] }>("/quality/overview")
      .then((data) => setItems(data.items))
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <EmptyState title="Quality center unavailable" description={error} />;
  if (!items) return <Skeleton className="h-48" />;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Data Quality Center</h1>
        <p className="mt-1 text-muted">Scores are calculated from uploaded rows. Nothing here is hard-coded.</p>
      </div>
      {items.length === 0 ? (
        <EmptyState title="No quality reports" description="Upload a dataset to generate a real quality score." />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {items.map((item) => (
            <Link key={item.id} href={`/app/quality/${item.id}`}>
              <Card className="h-full hover:border-accent/40">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="font-display text-lg font-semibold">{item.name}</h2>
                    <p className="mt-1 text-sm text-muted">{item.row_count} records · {item.issue_count} issues</p>
                  </div>
                  <Badge tone="accent">{item.quality_score ?? "—"}%</Badge>
                </div>
                {item.dimensions ? (
                  <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
                    {Object.entries(item.dimensions).map(([key, value]) => (
                      <div key={key} className="rounded-xl bg-slate-50 px-3 py-2">
                        <div className="text-xs uppercase tracking-wide text-muted">{key}</div>
                        <div className="font-semibold">{String(value)}%</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-4 text-sm text-muted">Profile not available yet.</p>
                )}
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
