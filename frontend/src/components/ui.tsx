"use client";

import { ReactNode } from "react";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`card p-5 ${className}`}>{children}</div>;
}

export function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  disabled,
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  variant?: "primary" | "secondary" | "danger" | "ghost";
  disabled?: boolean;
  className?: string;
}) {
  const styles = {
    primary: "bg-accent text-white hover:bg-accent-2",
    secondary: "bg-white text-ink border border-line hover:bg-slate-50",
    danger: "bg-danger text-white hover:bg-red-800",
    ghost: "bg-transparent text-muted hover:text-ink hover:bg-slate-100",
  }[variant];
  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`inline-flex items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${styles} ${className}`}
    >
      {children}
    </button>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "danger" | "accent";
}) {
  const styles = {
    neutral: "bg-slate-100 text-slate-700",
    ok: "bg-emerald-50 text-ok",
    warn: "bg-amber-50 text-warn",
    danger: "bg-red-50 text-danger",
    accent: "bg-teal-50 text-accent",
  }[tone];
  return <span className={`badge ${styles}`}>{children}</span>;
}

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-2xl border border-dashed border-line bg-slate-50 px-6 py-10 text-center">
      <h3 className="font-display text-lg font-semibold text-ink">{title}</h3>
      <p className="mt-2 text-sm text-muted">{description}</p>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-xl bg-slate-200/80 ${className}`} />;
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm outline-none ring-accent focus:ring-2 ${props.className || ""}`}
    />
  );
}

export function Select(props: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm outline-none ring-accent focus:ring-2 ${props.className || ""}`}
    />
  );
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      {...props}
      className={`w-full rounded-xl border border-line bg-white px-3 py-2.5 text-sm outline-none ring-accent focus:ring-2 ${props.className || ""}`}
    />
  );
}

export function statusTone(status: string): "ok" | "warn" | "danger" | "neutral" | "accent" {
  const value = status.toLowerCase();
  if (["success", "loaded", "passed", "ok", "cleaned", "validated", "profiled"].includes(value)) return "ok";
  if (["running", "partial", "uploaded", "warning", "preview"].includes(value)) return "warn";
  if (["failed", "error", "rejected"].includes(value)) return "danger";
  if (["sample"].includes(value)) return "accent";
  return "neutral";
}
