"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Button, Card, Input } from "@/components/ui";

export default function RegisterPage() {
  const { register, business, loading } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    business_name: "",
    owner_name: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && business) router.replace("/app");
  }, [business, loading, router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await register(form);
      router.replace("/app");
    } catch (err: any) {
      setError(err.message || "Could not create account.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-screen max-w-lg items-center px-5 py-10">
      <Card className="w-full">
        <h1 className="font-display text-3xl font-bold">Create business account</h1>
        <p className="mt-2 text-sm text-muted">
          Register once. Your datasets, quality reports, and analytics stay private to your business.
        </p>
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Business name</label>
            <Input
              value={form.business_name}
              onChange={(e) => setForm({ ...form, business_name: e.target.value })}
              placeholder="e.g. Himalaya Retail"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Owner name</label>
            <Input
              value={form.owner_name}
              onChange={(e) => setForm({ ...form, owner_name: e.target.value })}
              placeholder="Your full name"
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <Input
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Password</label>
            <Input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              minLength={8}
              placeholder="At least 8 characters"
              required
            />
          </div>
          {error ? <p className="text-sm text-danger">{error}</p> : null}
          <Button type="submit" disabled={busy} className="w-full">
            {busy ? "Creating account…" : "Create account"}
          </Button>
        </form>
        <p className="mt-4 text-sm text-muted">
          Already registered?{" "}
          <Link href="/login" className="font-semibold text-accent">
            Sign in
          </Link>
        </p>
      </Card>
    </div>
  );
}
