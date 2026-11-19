"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { Button, Card, EmptyState, Skeleton } from "@/components/ui";

const DEFAULT_OPS = [
  { type: "trim_strings" },
  { type: "normalize_ids" },
  { type: "normalize_dates" },
  { type: "coerce_numbers" },
  { type: "standardize_categories" },
  { type: "drop_duplicates" },
];

export default function CleaningPage() {
  const { id } = useParams();
  const [preview, setPreview] = useState<any>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    apiGet(`/datasets/${id}/cleaning/operations`).catch((err) => setError(err.message));
  }, [id]);

  async function runPreview() {
    setBusy("Previewing…");
    setError("");
    try {
      setPreview(await apiPost(`/datasets/${id}/cleaning/preview`, { operations: DEFAULT_OPS }));
      setMessage("Preview ready. Original bronze rows are unchanged.");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function apply() {
    setBusy("Applying…");
    try {
      const result = await apiPost<any>(`/datasets/${id}/cleaning/apply`, { operations: DEFAULT_OPS });
      setMessage(`Saved silver copy. ${result.cells_changed} cells changed. Bronze untouched.`);
      setPreview(result);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function reject() {
    setBusy("Rejecting…");
    try {
      await apiPost(`/datasets/${id}/cleaning/reject`);
      setMessage("Cleaned copy removed. Original upload remains.");
      setPreview(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Cleaning workspace</h1>
        <p className="mt-1 text-muted">Preview first. Apply writes Silver only. Reject discards the cleaned copy.</p>
      </div>

      <Card>
        <h2 className="font-display text-lg font-semibold">Standard recipe</h2>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-muted">
          {DEFAULT_OPS.map((op) => (
            <li key={op.type}>{op.type.replaceAll("_", " ")}</li>
          ))}
        </ul>
        <div className="mt-5 flex flex-wrap gap-2">
          <Button onClick={runPreview} disabled={!!busy}>{busy || "Preview changes"}</Button>
          <Button variant="secondary" onClick={apply} disabled={!!busy}>Apply cleaning</Button>
          <Button variant="danger" onClick={reject} disabled={!!busy}>Reject cleaned copy</Button>
        </div>
        {message ? <p className="mt-4 rounded-xl bg-teal-50 px-4 py-3 text-sm text-accent-2">{message}</p> : null}
        {error ? <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p> : null}
      </Card>

      {!preview ? (
        <EmptyState title="No preview yet" description="Run preview to see cell-level changes before saving Silver." />
      ) : (
        <Card>
          <h2 className="font-display text-lg font-semibold">Change summary</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-4 text-sm">
            <div className="rounded-xl bg-slate-50 p-3">Rows before: {preview.rows_before}</div>
            <div className="rounded-xl bg-slate-50 p-3">Rows after: {preview.rows_after}</div>
            <div className="rounded-xl bg-slate-50 p-3">Removed: {preview.rows_removed}</div>
            <div className="rounded-xl bg-slate-50 p-3">Cells changed: {preview.cells_changed}</div>
          </div>
          <div className="mt-5 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="text-muted">
                <tr>
                  <th className="pb-2 pr-3">Row</th>
                  <th className="pb-2 pr-3">Column</th>
                  <th className="pb-2 pr-3">Before</th>
                  <th className="pb-2">After</th>
                </tr>
              </thead>
              <tbody>
                {(preview.changed_cells || []).map((change: any, index: number) => (
                  <tr key={index} className="border-t border-line">
                    <td className="py-2 pr-3">{change.row}</td>
                    <td className="py-2 pr-3">{change.column}</td>
                    <td className="py-2 pr-3">{String(change.before)}</td>
                    <td className="py-2">{String(change.after)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
