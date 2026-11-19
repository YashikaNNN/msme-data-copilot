"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiGet, exportUrl } from "@/lib/api";
import { money } from "@/lib/format";
import { Button, Card, EmptyState, Skeleton } from "@/components/ui";

export default function AnalyticsPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    apiGet("/analytics/overview")
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <EmptyState title="Analytics unavailable" description={error} />;
  if (!data) return <Skeleton className="h-64" />;

  const sales = data.sales;
  const customers = data.customers;
  const inventory = data.inventory;
  const expenses = data.expenses;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold">Business intelligence</h1>
          <p className="mt-1 text-muted">Metrics come from Gold rows only. Missing fields are explained, not invented.</p>
        </div>
        <a href={exportUrl("/analytics/export.csv")}>
          <Button variant="secondary">Export summary CSV</Button>
        </a>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="font-display text-lg font-semibold">Sales</h2>
          {!sales.available ? (
            <div className="mt-4"><EmptyState title="Sales unavailable" description={sales.reason} /></div>
          ) : (
            <>
              <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                <div className="rounded-xl bg-slate-50 p-3"><div className="text-muted">Revenue</div><div className="text-xl font-bold">{money(sales.revenue)}</div></div>
                <div className="rounded-xl bg-slate-50 p-3"><div className="text-muted">Orders</div><div className="text-xl font-bold">{sales.orders}</div></div>
                <div className="rounded-xl bg-slate-50 p-3"><div className="text-muted">AOV</div><div className="text-xl font-bold">{money(sales.average_order_value)}</div></div>
              </div>
              <div className="mt-4 h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={(sales.by_month || []).filter((row: any) => row.revenue !== null)}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="revenue" stroke="#0f766e" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              {(sales.notes || []).map((note: string) => (
                <p key={note} className="mt-2 text-xs text-muted">{note}</p>
              ))}
            </>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-lg font-semibold">Top products</h2>
          {!sales.available || !(sales.products || []).length ? (
            <div className="mt-4"><EmptyState title="No product performance" description="Need sales with product and amount fields." /></div>
          ) : (
            <div className="mt-4 space-y-2">
              {sales.products.slice(0, 8).map((item: any) => (
                <div key={item.name} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm">
                  <span>{item.name}</span>
                  <span className="font-semibold">{item.revenue == null ? "amount missing" : money(item.revenue)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-lg font-semibold">Customers</h2>
          {!customers.available ? (
            <div className="mt-4"><EmptyState title="Customers unavailable" description={customers.reason} /></div>
          ) : (
            <>
              <p className="mt-3 text-sm text-muted">{customers.total_customers} customers · {customers.customers_with_purchases} with purchases</p>
              <div className="mt-4 space-y-2">
                {(customers.top_customers || []).slice(0, 6).map((item: any) => (
                  <div key={item.customer_id} className="flex justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm">
                    <span>{item.name || item.customer_id}</span>
                    <span className="font-semibold">{money(item.revenue)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-lg font-semibold">Inventory</h2>
          {!inventory.available ? (
            <div className="mt-4"><EmptyState title="Inventory unavailable" description={inventory.reason} /></div>
          ) : (
            <>
              <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-xl bg-slate-50 p-3">Value: {money(inventory.inventory_value)}</div>
                <div className="rounded-xl bg-slate-50 p-3">Low stock: {(inventory.low_stock || []).length}</div>
              </div>
              <div className="mt-4 space-y-2">
                {(inventory.high_stock_low_sales || []).slice(0, 5).map((item: any) => (
                  <div key={item.product_id} className="rounded-xl bg-amber-50 px-3 py-2 text-sm text-warn">
                    {item.product_name || item.product_id}: {item.stock_qty} in stock, {item.units_sold} sold
                  </div>
                ))}
              </div>
            </>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="font-display text-lg font-semibold">Expenses & profitability</h2>
          {!expenses.available ? (
            <div className="mt-4"><EmptyState title="Expenses unavailable" description={expenses.reason} /></div>
          ) : (
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={expenses.by_category || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="category" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="amount" fill="#115e59" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={expenses.revenue_vs_expenses || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="revenue" stroke="#0f766e" />
                    <Line type="monotone" dataKey="expenses" stroke="#b45309" />
                    <Line type="monotone" dataKey="profit" stroke="#047857" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
