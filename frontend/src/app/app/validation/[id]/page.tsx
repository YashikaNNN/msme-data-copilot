"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiGet, apiPatch, apiPost } from "@/lib/api";
import { Badge, Button, Card, EmptyState, Skeleton, statusTone } from "@/components/ui";

export default function ValidationPage() {
  const { id } = useParams();
  const [rules, setRules] = useState<any>(null);
  const [results, setResults] = useState<any[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  async function load() {
    try {
      const ruleData = await apiGet<any>(`/datasets/${id}/rules`);
      setRules(ruleData);
      const validation = await apiGet<{ items: any[] }>(`/datasets/${id}/validation`);
      setResults(validation.items);
    } catch (err: any) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, [id]);

  async function validate() {
    setBusy("Validating…");
    try {
      const response = await apiPost<{ results: any[] }>(`/datasets/${id}/validate`);
      setResults(response.results);
      await apiPost("/validation/references");
      await load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  async function toggle(rule: any) {
    await apiPatch(`/rules/${rule.id}`, { enabled: !rule.enabled });
    await load();
  }

  if (error && !rules) return <EmptyState title="Validation unavailable" description={error} />;
  if (!rules) return <Skeleton className="h-48" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold">Validation rules</h1>
          <p className="mt-1 text-muted">Blocking failures quarantine rows out of Gold analytics.</p>
        </div>
        <Button onClick={validate} disabled={!!busy}>{busy || "Run validation"}</Button>
      </div>

      <Card>
        <h2 className="font-display text-lg font-semibold">Configured rules</h2>
        <div className="mt-4 space-y-3">
          {rules.items.map((rule: any) => (
            <div key={rule.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-line px-4 py-3">
              <div>
                <div className="font-semibold">{rule.name}</div>
                <div className="text-sm text-muted">
                  {rule.column_name} · {rule.rule_type}
                  {rule.blocks_load ? " · blocks load" : " · warning only"}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge tone={rule.enabled ? "ok" : "neutral"}>{rule.enabled ? "enabled" : "disabled"}</Badge>
                <Button variant="secondary" onClick={() => toggle(rule)}>
                  {rule.enabled ? "Disable" : "Enable"}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h2 className="font-display text-lg font-semibold">Latest results</h2>
        {results.length === 0 ? (
          <div className="mt-4">
            <EmptyState title="No validation history" description="Run validation after cleaning or as part of the pipeline." />
          </div>
        ) : (
          <div className="mt-4 space-y-3">
            {results.map((item, index) => (
              <div key={item.id || index} className="rounded-xl bg-slate-50 px-4 py-3">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge tone={statusTone(item.status)}>{item.status}</Badge>
                  <span className="font-semibold">{item.rule_name}</span>
                  <span className="text-sm text-muted">{item.affected_count} rows</span>
                </div>
                <p className="mt-1 text-sm text-muted">{item.message}</p>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
