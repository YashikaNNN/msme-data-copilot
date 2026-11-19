"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { apiGet, Dataset } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Badge, Button, Card, EmptyState, Skeleton, statusTone } from "@/components/ui";

const RevenueChart = dynamic(() => import("@/components/RevenueChart"), { ssr: false });

type Dashboard = {
  business: { business_name: string; owner_name: string };
  total_datasets: number;
  total_records: number;
  quality_score: number | null;
  quality_note: string | null;
  pipeline_runs: number;
  successful_runs: number;
  failed_runs: number;
  partial_runs: number;
  recent_datasets: Dataset[];
  recent_activity: { id: number; message: string; created_at: string; action: string }[];
  business_metrics: Record<string, any>;
  revenue_by_month: { month: string; revenue: number | null; orders: number }[];
  workflow: {
    uploaded: boolean;
    quality_checked: boolean;
    cleaned: boolean;
    analytics_ready: boolean;
  };
};

const WORKFLOW = [
  { key: "uploaded", label: "1. Upload dataset", href: "/app/upload" },
  { key: "quality_checked", label: "2. Check quality", href: "/app/quality" },
  { key: "cleaned", label: "3. Clean & validate", href: "/app/datasets" },
  { key: "analytics_ready", label: "4. View insights", href: "/app/analytics" },
] as const;

export default function DashboardPage() {
  const { business } = useAuth();
  const [data, setData] = useState<Dashboard | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet<Dashboard>("/dashboard")
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return <EmptyState title="Dashboard unavailable" description={error} />;
  }
  if (!data) {
    return (
      <div className="grid gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28" />
        ))}
      </div>
    );
  }

  const cards = [
    { label: "Datasets", value: data.total_datasets },
    { label: "Records", value: data.total_records },
    {
      label: "Avg quality",
      value: data.quality_score === null ? "—" : `${data.quality_score}%`,
      note: data.quality_note,
    },
    {
      label: "Processing runs",
      value: data.pipeline_runs,
      note: `${data.successful_runs} success · ${data.failed_runs} failed`,
    },
  ];

  const chartData = (data.revenue_by_month || []).filter((row) => row.revenue !== null);
  const metrics = data.business_metrics || {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold">
            {business?.business_name || data.business.business_name} dashboard
          </h1>
          <p className="mt-1 text-muted">Your private workspace for clean business data and insights.</p>
        </div>
        <div className="flex gap-2">
          <Link href="/app/samples">
            <Button variant="secondary">Try sample data</Button>
          </Link>
          <Link href="/app/upload">
            <Button>Upload dataset</Button>
          </Link>
        </div>
      </div>

      <Card>
        <h2 className="font-display text-lg font-semibold">Your workflow</h2>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          {WORKFLOW.map((step) => {
            const done = data.workflow?.[step.key];
            return (
              <Link
                key={step.key}
                href={step.href}
                className={`rounded-xl border px-4 py-3 ${done ? "border-emerald-200 bg-emerald-50" : "border-line bg-slate-50"}`}
              >
                <div className="text-sm font-semibold">{step.label}</div>
                <div className="mt-1 text-xs text-muted">{done ? "Done" : "Next up"}</div>
              </Link>
            );
          })}
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <Card key={card.label}>
            <div className="text-sm text-muted">{card.label}</div>
            <div className="mt-2 font-display text-3xl font-bold">{card.value}</div>
            {card.note ? <p className="mt-2 text-xs text-muted">{card.note}</p> : null}
          </Card>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="font-display text-lg font-semibold">Revenue by month</h2>
          {chartData.length === 0 ? (
            <div className="mt-4">
              <EmptyState
                title="No revenue chart yet"
                description="Upload a sales file, clean it, then run processing to load trusted amounts and dates."
              />
            </div>
          ) : (
            <div className="mt-4 h-64">
              <RevenueChart data={chartData} />
            </div>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-lg font-semibold">Business snapshot</h2>
          <div className="mt-4 space-y-3">
            {[
              ["Sales", metrics.sales],
              ["Customers", metrics.customers],
              ["Inventory", metrics.inventory],
              ["Expenses", metrics.expenses],
            ].map(([label, report]: any) => (
              <div key={label} className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                <div>
                  <div className="text-sm font-semibold">{label}</div>
                  <div className="text-xs text-muted">
                    {report?.available
                      ? report.revenue !== undefined
                        ? `Revenue ${report.revenue ?? "unavailable"}`
                        : report.total_customers !== undefined
                          ? `${report.total_customers} customers`
                          : report.inventory_value !== undefined
                            ? `Value ${report.inventory_value ?? "unavailable"}`
                            : `Total ${report.total ?? "unavailable"}`
                      : report?.reason || "Not available yet"}
                  </div>
                </div>
                <Badge tone={report?.available ? "ok" : "neutral"}>
                  {report?.available ? "ready" : "waiting"}
                </Badge>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-display text-lg font-semibold">Recent datasets</h2>
            <Link href="/app/datasets" className="text-sm font-semibold text-accent">
              View all
            </Link>
          </div>
          {data.recent_datasets.length === 0 ? (
            <EmptyState
              title="No datasets yet"
              description="Upload your first file or load the labelled sample business data."
            />
          ) : (
            <div className="space-y-3">
              {data.recent_datasets.map((dataset) => (
                <Link
                  key={dataset.id}
                  href={`/app/datasets/${dataset.id}`}
                  className="flex items-center justify-between rounded-xl border border-line px-4 py-3 hover:bg-slate-50"
                >
                  <div>
                    <div className="font-semibold">{dataset.name}</div>
                    <div className="text-xs text-muted">
                      {dataset.row_count} rows · {dataset.category}
                      {dataset.quality_score != null ? ` · quality ${dataset.quality_score}%` : ""}
                    </div>
                  </div>
                  <Badge tone={statusTone(dataset.status)}>{dataset.status}</Badge>
                </Link>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-lg font-semibold">Recent activity</h2>
          {data.recent_activity.length === 0 ? (
            <div className="mt-4">
              <EmptyState title="No activity yet" description="Uploads, cleaning, and processing will appear here." />
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              {data.recent_activity.map((item) => (
                <div key={item.id} className="rounded-xl bg-slate-50 px-4 py-3">
                  <div className="text-sm font-medium">{item.message}</div>
                  <div className="mt-1 text-xs text-muted">
                    {new Date(item.created_at).toLocaleString()}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
