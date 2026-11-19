"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiGet, Dataset } from "@/lib/api";
import { Badge, Card, EmptyState, Skeleton, statusTone } from "@/components/ui";

type Dashboard = {
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
  business: Record<string, any>;
  revenue_by_month: { month: string; revenue: number | null; orders: number }[];
};

export default function DashboardPage() {
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
    { label: "Records processed", value: data.total_records },
    {
      label: "Quality score",
      value: data.quality_score === null ? "—" : `${data.quality_score}%`,
      note: data.quality_note,
    },
    {
      label: "Pipeline runs",
      value: data.pipeline_runs,
      note: `${data.successful_runs} success · ${data.failed_runs} failed · ${data.partial_runs} partial`,
    },
  ];

  const chartData = (data.revenue_by_month || []).filter((row) => row.revenue !== null);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Operations dashboard</h1>
        <p className="mt-1 text-muted">Live counts from uploaded and processed datasets only.</p>
      </div>

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
                title="No revenue trend yet"
                description="Load and process a sales dataset with valid dates and amounts."
              />
            </div>
          ) : (
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Bar dataKey="revenue" fill="#0f766e" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-lg font-semibold">Business snapshot</h2>
          <div className="mt-4 space-y-3">
            {[
              ["Sales", data.business?.sales],
              ["Customers", data.business?.customers],
              ["Inventory", data.business?.inventory],
              ["Expenses", data.business?.expenses],
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
                      : report?.reason || "Not available"}
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
            <EmptyState title="No datasets yet" description="Upload a file or load the labelled sample workspace." />
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
                      {dataset.row_count} rows · {dataset.column_count} columns
                      {dataset.is_sample ? " · sample" : ""}
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
              <EmptyState title="No activity yet" description="Uploads, cleaning, and pipeline runs will appear here." />
            </div>
          ) : (
            <div className="mt-4 space-y-3">
              {data.recent_activity.map((item) => (
                <div key={item.id} className="rounded-xl bg-slate-50 px-4 py-3">
                  <div className="text-sm font-medium">{item.message}</div>
                  <div className="mt-1 text-xs text-muted">
                    {item.action} · {new Date(item.created_at).toLocaleString()}
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
