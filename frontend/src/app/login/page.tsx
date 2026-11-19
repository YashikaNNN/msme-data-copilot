"use client";

import Link from "next/link";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Button, Card, Input, Skeleton } from "@/components/ui";

function LoginForm() {
  const { login, business, loading } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && business) {
      router.replace(params.get("next") || "/app");
    }
  }, [business, loading, params, router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email.trim(), password);
      router.replace(params.get("next") || "/app");
    } catch (err: any) {
      setError(err.message || "Could not sign in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card className="w-full">
      <h1 className="font-display text-3xl font-bold">Sign in</h1>
      <p className="mt-2 text-sm text-muted">Access your private business workspace.</p>
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <div>
          <label className="mb-1 block text-sm font-medium">Email</label>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label className="mb-1 block text-sm font-medium">Password</label>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        {error ? <p className="text-sm text-danger">{error}</p> : null}
        <Button type="submit" disabled={busy} className="w-full">
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <p className="mt-4 text-sm text-muted">
        New here?{" "}
        <Link href="/register" className="font-semibold text-accent">
          Create a business account
        </Link>
      </p>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <div className="mx-auto flex min-h-screen max-w-lg items-center px-5 py-10">
      <Suspense fallback={<Skeleton className="h-80 w-full" />}>
        <LoginForm />
      </Suspense>
    </div>
  );
}
