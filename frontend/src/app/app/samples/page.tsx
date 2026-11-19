"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost, exportUrl } from "@/lib/api";
import { Badge, Button, Card, EmptyState, Skeleton } from "@/components/ui";

export default function SamplesPage() {
  const [items, setItems] = useState<any[] | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    apiGet<{ items: any[] }>("/samples")
      .then((data) => setItems(data.items))
      .catch((err) => setError(err.message));
  }, []);

  async function loadWorkspace() {
    setBusy(true);
    setError("");
    try {
      const result = await apiPost<any>("/samples/load?run_pipeline=true");
      const lines = (result.processed || [])
        .map((item: any) => `${item.name}: ${item.status} (loaded ${item.loaded}, rejected ${item.rejected})`)
        .join(" · ");
      setMessage(lines || "Sample datasets loaded.");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (error && !items) return <EmptyState title="Sample data unavailable" description={error} />;
  if (!items) return <Skeleton className="h-48" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold">Sample business data</h1>
          <p className="mt-1 text-muted">
            Explicitly labelled demo files with missing values, duplicates, bad dates, and inconsistent IDs.
          </p>
        </div>
        <Button onClick={loadWorkspace} disabled={busy}>
          {busy ? "Loading sample workspace…" : "Load sample workspace"}
        </Button>
      </div>

      {message ? <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm text-accent-2">{message}</p> : null}
      {error ? <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p> : null}

      <div className="grid gap-4 md:grid-cols-2">
        {items.map((item) => (
          <Card key={item.filename}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-display text-lg font-semibold">{item.name}</h2>
                <p className="mt-1 text-sm text-muted">{item.description}</p>
              </div>
              <Badge tone="accent">{item.category}</Badge>
            </div>
            <div className="mt-4 flex items-center justify-between text-sm">
              <span className="text-muted">
                {item.filename} · {(item.size_bytes / 1024).toFixed(1)} KB
              </span>
              <a href={exportUrl(`/samples/${item.filename}`)}>
                <Button variant="secondary">Download</Button>
              </a>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
