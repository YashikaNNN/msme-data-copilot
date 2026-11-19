"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiDelete, apiGet, apiPost } from "@/lib/api";
import { Badge, Button, Card, EmptyState, Input, Skeleton, statusTone } from "@/components/ui";

export default function DatasetDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const [dataset, setDataset] = useState<any>(null);
  const [records, setRecords] = useState<any>(null);
  const [layer, setLayer] = useState("bronze");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  async function load() {
    try {
      const detail = await apiGet(`/datasets/${id}`);
      setDataset(detail);
      const rows = await apiGet(`/datasets/${id}/records?layer=${layer}&page=${page}&page_size=10&q=${encodeURIComponent(q)}`);
      setRecords(rows);
    } catch (err: any) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, [id, layer, page]);

  async function runPipeline() {
    setBusy("Running pipeline…");
    try {
      const run = await apiPost<any>(`/datasets/${id}/pipeline/run`);
      router.push(`/app/pipelines/${run.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function remove() {
    if (!confirm("Delete this dataset and its stored copies?")) return;
    await apiDelete(`/datasets/${id}`);
    router.push("/app/datasets");
  }

  if (error && !dataset) return <EmptyState title="Dataset unavailable" description={error} />;
  if (!dataset) return <Skeleton className="h-64" />;

  const bronzeColumns = (dataset.columns || []).filter((c: any) => c.layer === "bronze");

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold">{dataset.name}</h1>
          <p className="mt-1 text-muted">{dataset.description || "No description"}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge tone={statusTone(dataset.status)}>{dataset.status}</Badge>
            <Badge tone="accent">{dataset.category}</Badge>
            {dataset.is_sample ? <Badge>sample data</Badge> : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href={`/app/quality/${id}`}><Button variant="secondary">Check quality</Button></Link>
          <Link href={`/app/cleaning/${id}`}><Button variant="secondary">Clean data</Button></Link>
          <Link href={`/app/validation/${id}`}><Button variant="secondary">Validate</Button></Link>
          <Button onClick={runPipeline} disabled={!!busy}>{busy || "Process for insights"}</Button>
          <Button variant="danger" onClick={remove}>Delete</Button>
        </div>
      </div>

      {error ? <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p> : null}

      {(dataset.next_steps || []).length ? (
        <Card>
          <h2 className="font-display text-lg font-semibold">Recommended next steps</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-4">
            {dataset.next_steps.map((step: any) => (
              <Link
                key={step.key}
                href={step.href}
                className={`rounded-xl border px-4 py-3 text-sm ${step.done ? "border-emerald-200 bg-emerald-50" : "border-line bg-slate-50"}`}
              >
                <div className="font-semibold">{step.label}</div>
                <div className="mt-1 text-xs text-muted">{step.done ? "Done" : "Todo"}</div>
              </Link>
            ))}
          </div>
        </Card>
      ) : null}

      <div className="grid gap-4 md:grid-cols-4">
        {[
          ["Rows", dataset.row_count],
          ["Columns", dataset.column_count],
          ["Quality", dataset.quality_score === null ? "—" : `${dataset.quality_score}%`],
          ["Silver rows", dataset.silver_rows],
        ].map(([label, value]) => (
          <Card key={label as string}>
            <div className="text-sm text-muted">{label}</div>
            <div className="mt-2 font-display text-2xl font-bold">{value}</div>
          </Card>
        ))}
      </div>

      <Card>
        <h2 className="font-display text-lg font-semibold">Schema & profile</h2>
        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="text-muted">
              <tr>
                <th className="pb-2 pr-4">Column</th>
                <th className="pb-2 pr-4">Type</th>
                <th className="pb-2 pr-4">Nulls</th>
                <th className="pb-2 pr-4">Unique</th>
                <th className="pb-2 pr-4">Mapped to</th>
                <th className="pb-2">Samples</th>
              </tr>
            </thead>
            <tbody>
              {bronzeColumns.map((column: any) => (
                <tr key={column.name} className="border-t border-line">
                  <td className="py-3 pr-4 font-medium">{column.name}</td>
                  <td className="py-3 pr-4">{column.inferred_type}</td>
                  <td className="py-3 pr-4">{column.null_count}</td>
                  <td className="py-3 pr-4">{column.unique_count}</td>
                  <td className="py-3 pr-4">{dataset.suggested_mapping?.[column.name] || "—"}</td>
                  <td className="py-3 text-muted">{(column.sample_values || []).join(", ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card>
        <div className="flex flex-wrap items-end gap-3">
          <div>
            <h2 className="font-display text-lg font-semibold">Records</h2>
            <p className="text-sm text-muted">Searchable, paginated table of stored rows.</p>
          </div>
          <select
            className="rounded-xl border border-line px-3 py-2 text-sm"
            value={layer}
            onChange={(e) => {
              setPage(1);
              setLayer(e.target.value);
            }}
          >
            <option value="bronze">Bronze (original)</option>
            <option value="silver">Silver (cleaned)</option>
          </select>
          <Input
            className="max-w-xs"
            placeholder="Search rows"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                setPage(1);
                load();
              }
            }}
          />
          <Button
            variant="secondary"
            onClick={() => {
              setPage(1);
              load();
            }}
          >
            Search
          </Button>
        </div>

        {!records ? (
          <Skeleton className="mt-4 h-40" />
        ) : records.items.length === 0 ? (
          <div className="mt-4">
            <EmptyState title="No rows in this layer" description="Upload data or apply cleaning to create a silver copy." />
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <th className="pb-2 pr-3">#</th>
                  {Object.keys(records.items[0].data || {}).map((key) => (
                    <th key={key} className="pb-2 pr-3">
                      {key}
                    </th>
                  ))}
                  <th className="pb-2">Flags</th>
                </tr>
              </thead>
              <tbody>
                {records.items.map((row: any) => (
                  <tr key={row.row_index} className="border-t border-line align-top">
                    <td className="py-3 pr-3">{row.row_index + 1}</td>
                    {Object.keys(records.items[0].data || {}).map((key) => (
                      <td key={key} className="py-3 pr-3">
                        {row.data?.[key] ?? "—"}
                      </td>
                    ))}
                    <td className="py-3">
                      {row.quarantined ? <Badge tone="warn">{row.quarantine_reason || "quarantined"}</Badge> : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="mt-4 flex items-center justify-between text-sm">
              <span className="text-muted">
                Page {records.page} · {records.total} rows
              </span>
              <div className="flex gap-2">
                <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  disabled={page * records.page_size >= records.total}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
