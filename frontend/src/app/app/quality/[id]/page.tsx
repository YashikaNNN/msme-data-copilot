"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { apiGet } from "@/lib/api";
import { Badge, Card, EmptyState, Skeleton, statusTone } from "@/components/ui";

export default function QualityDetailPage() {
  const { id } = useParams();
  const [layer, setLayer] = useState("bronze");
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet(`/datasets/${id}/quality?layer=${layer}`)
      .then(setData)
      .catch((err) => setError(err.message));
  }, [id, layer]);

  if (error) return <EmptyState title="Quality report unavailable" description={error} />;
  if (!data) return <Skeleton className="h-64" />;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold">{data.dataset.name}</h1>
          <p className="mt-1 text-muted">Dataset health calculated from the {layer} layer.</p>
        </div>
        <select className="rounded-xl border border-line px-3 py-2 text-sm" value={layer} onChange={(e) => setLayer(e.target.value)}>
          <option value="bronze">Bronze</option>
          <option value="silver">Silver</option>
        </select>
      </div>

      {data.score === null ? (
        <EmptyState title="No score yet" description={data.note || "Profile this layer first."} />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-5">
            {[
              ["Quality score", `${data.score}%`],
              ["Completeness", `${data.completeness}%`],
              ["Validity", `${data.validity}%`],
              ["Uniqueness", `${data.uniqueness}%`],
              ["Consistency", `${data.consistency}%`],
            ].map(([label, value]) => (
              <Card key={label}>
                <div className="text-sm text-muted">{label}</div>
                <div className="mt-2 font-display text-2xl font-bold">{value}</div>
              </Card>
            ))}
          </div>

          <Card>
            <h2 className="font-display text-lg font-semibold">Issues</h2>
            {data.issues.length === 0 ? (
              <div className="mt-4">
                <EmptyState title="No issues found" description="This layer passed the current quality checks." />
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                {data.issues.map((issue: any) => (
                  <div key={issue.id} className="rounded-2xl border border-line p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      <Badge tone={statusTone(issue.severity)}>{issue.severity}</Badge>
                      <Badge>{issue.category}</Badge>
                      <span className="text-sm font-semibold">{issue.column_name || "rows"}</span>
                      <span className="text-sm text-muted">{issue.affected_count} affected</span>
                    </div>
                    <p className="mt-2 text-sm">{issue.explanation}</p>
                    <p className="mt-1 text-sm text-muted">{issue.suggested_resolution}</p>
                    <div className="mt-2 flex gap-2 text-xs">
                      <Badge tone={issue.auto_fixable ? "ok" : "neutral"}>
                        {issue.auto_fixable ? "auto-fix possible" : "manual fix"}
                      </Badge>
                      {issue.manual_review ? <Badge tone="warn">manual review</Badge> : null}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
