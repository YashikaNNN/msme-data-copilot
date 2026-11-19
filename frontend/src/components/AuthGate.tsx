"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Skeleton } from "@/components/ui";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { business, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!loading && !business) {
      router.replace(`/login?next=${encodeURIComponent(pathname || "/app")}`);
    }
  }, [business, loading, pathname, router]);

  if (loading) {
    return (
      <div className="space-y-4 p-8">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (!business) return null;
  return <>{children}</>;
}
