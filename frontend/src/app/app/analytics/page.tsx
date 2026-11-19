"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { apiGet, downloadAuthenticated } from "@/lib/api";
import { money } from "@/lib/format";
import { Button, Card, EmptyState, Skeleton } from "@/components/ui";

const SalesTrendChart = dynamic(
  () => import("@/components/AnalyticsCharts").then((m) => m.SalesTrendChart),
  { ssr: false },
);
const ExpenseCategoryChart = dynamic(
  () => import("@/components/AnalyticsCharts").then((m) => m.ExpenseCategoryChart),
  { ssr: false },
);
const ProfitTrendChart = dynamic(
  () => import("@/components/AnalyticsCharts").then((m) => m.ProfitTrendChart),
  { ssr: false },
);

export default function AnalyticsPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");
  const [exportError, setExportError] = useState("");

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
  const salesTrend = (sales.by_month || []).filter((row: any) => row.revenue !== null);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-bold">Business insights</h1>
          <p className="mt-1 text-muted">
            Charts and totals come only from cleaned, validated data. Missing fields are explained, not invented.
          </p>
        </div>
        <Button
          variant="secondary"
          onClick={async () => {
            try {
              setExportError("");
              await downloadAuthenticated("/analytics/export.csv", "analytics-summary.csv");
            } catch (err: any) {
              setExportError(err.message || "Export failed");
            }
          }}
        >
          Download summary CSV
        </Button>
      </div>
      {exportError ? <p className="text-sm text-danger">{exportError}</p> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="font-display text-lg font-semibold">Sales</h2>
          {!sales.available ? (
            <div className="mt-4">
              <EmptyState title="Sales unavailable" description={sales.reason} />
            </div>
          ) : (
            <>
              <div className="mt-4 grid grid-cols-3 gap-3 text-sm">
                <div className="rounded-xl bg-slate-50 p-3">
                  <div className="text-muted">Revenue</div>
                  <div className="text-xl font-bold">{money(sales.revenue)}</div>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <div className="text-muted">Orders</div>
                  <div className="text-xl font-bold">{sales.orders}</div>
                </div>
                <div className="rounded-xl bg-slate-50 p-3">
                  <div className="text-muted">Avg order</div>
                  <div className="text-xl font-bold">{money(sales.average_order_value)}</div>
                </div>
              </div>
              {salesTrend.length ? (
                <div className="mt-4 h-56">
                  <SalesTrendChart data={salesTrend} />
                </div>
              ) : (
                <div className="mt-4 space-y-2 text-sm text-muted">
                  <p>Need dated sales amounts before a trend chart can appear.</p>
                  {(sales.orders || 0) > 0 && sales.revenue == null ? (
                    <p className="rounded-xl bg-amber-50 px-3 py-2 text-warn">
                      Orders were loaded, but revenue amounts are still empty. Open the sales dataset and click{" "}
                      <strong>Process for insights</strong> again, then refresh this page.
                    </p>
                  ) : null}
                </div>
              )}
              {(sales.notes || []).map((note: string) => (
                <p key={note} className="mt-2 text-xs text-muted">
                  {note}
                </p>
              ))}
            </>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-lg font-semibold">Top products</h2>
          {!sales.available || !(sales.products || []).length ? (
            <div className="mt-4">
              <EmptyState title="No product performance" description="Need sales with product and amount fields." />
            </div>
          ) : (
            <div className="mt-4 space-y-2">
              {sales.products.slice(0, 8).map((item: any) => (
                <div key={item.name} className="flex items-center justify-between rounded-xl bg-slate-50 px-3 py-2 text-sm">
                  <span>{item.name}</span>
                  <span className="font-semibold">
                    {item.revenue == null ? "amount missing" : money(item.revenue)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <h2 className="font-display text-lg font-semibold">Customers</h2>
          {!customers.available ? (
            <div className="mt-4">
              <EmptyState title="Customers unavailable" description={customers.reason} />
            </div>
          ) : (
            <>
              <p className="mt-3 text-sm text-muted">
                {customers.total_customers} customers · {customers.customers_with_purchases} with purchases
              </p>
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
            <div className="mt-4">
              <EmptyState title="Inventory unavailable" description={inventory.reason} />
            </div>
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
                {(inventory.high_stock_low_sales || []).length === 0 ? (
                  <p className="text-sm text-muted">No high-stock, low-sales products detected yet.</p>
                ) : null}
              </div>
            </>
          )}
        </Card>

        <Card className="lg:col-span-2">
          <h2 className="font-display text-lg font-semibold">Expenses & profitability</h2>
          {!expenses.available ? (
            <div className="mt-4">
              <EmptyState title="Expenses unavailable" description={expenses.reason} />
            </div>
          ) : (
            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              {(expenses.by_category || []).length ? (
                <div className="h-56">
                  <ExpenseCategoryChart data={expenses.by_category || []} />
                </div>
              ) : (
                <EmptyState title="No expense categories" description="Expense amounts are needed for this chart." />
              )}
              {(expenses.revenue_vs_expenses || []).length ? (
                <div className="h-56">
                  <ProfitTrendChart data={expenses.revenue_vs_expenses || []} />
                </div>
              ) : (
                <EmptyState
                  title="Profit trend waiting"
                  description="Load both sales and expenses with dates to compare months."
                />
              )}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
