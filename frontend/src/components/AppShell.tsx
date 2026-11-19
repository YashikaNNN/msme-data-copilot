"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Bot,
  Database,
  Download,
  FileUp,
  GitBranch,
  LayoutDashboard,
  LineChart,
  LogOut,
  PackageOpen,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui";

const NAV = [
  { href: "/app", label: "Dashboard", icon: LayoutDashboard },
  { href: "/app/upload", label: "Upload", icon: FileUp },
  { href: "/app/datasets", label: "Datasets", icon: Database },
  { href: "/app/quality", label: "Data Quality", icon: ShieldCheck },
  { href: "/app/pipelines", label: "Processing", icon: Workflow },
  { href: "/app/analytics", label: "Analytics", icon: LineChart },
  { href: "/app/copilot", label: "Ask AI", icon: Bot },
  { href: "/app/lineage", label: "Data Journey", icon: GitBranch },
  { href: "/app/exports", label: "Downloads", icon: Download },
  { href: "/app/samples", label: "Try Sample Data", icon: PackageOpen },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { business, logout } = useAuth();

  async function onLogout() {
    await logout();
    router.push("/login");
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[250px_1fr]">
      <aside className="border-b border-line bg-panel/90 backdrop-blur lg:border-b-0 lg:border-r">
        <div className="px-5 py-5">
          <Link href="/app" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-accent text-white">
              <Sparkles size={18} />
            </div>
            <div>
              <div className="font-display text-sm font-bold tracking-tight">MSME Data Copilot</div>
              <div className="truncate text-xs text-muted">{business?.business_name || "Your workspace"}</div>
            </div>
          </Link>
        </div>
        <nav className="flex gap-1 overflow-x-auto px-3 pb-4 lg:flex-col">
          {NAV.map((item) => {
            const active = pathname === item.href || (item.href !== "/app" && pathname.startsWith(item.href));
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium whitespace-nowrap ${
                  active ? "bg-teal-50 text-accent" : "text-muted hover:bg-slate-50 hover:text-ink"
                }`}
              >
                <Icon size={16} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>
      <div className="min-w-0">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line bg-panel/70 px-5 py-4 backdrop-blur">
          <div>
            <div className="text-sm font-semibold text-ink">
              Welcome{business?.owner_name ? `, ${business.owner_name}` : ""}
            </div>
            <div className="text-xs text-muted">
              Upload → Check quality → Clean & validate → View insights
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/app/upload" className="rounded-xl bg-accent px-3 py-2 text-sm font-semibold text-white">
              Upload dataset
            </Link>
            <Button variant="ghost" onClick={onLogout} className="text-muted">
              <LogOut size={16} /> Sign out
            </Button>
          </div>
        </header>
        <main className="px-5 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
