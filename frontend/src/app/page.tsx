import Link from "next/link";
import { ArrowRight, CheckCircle2, Database, ShieldCheck, Sparkles } from "lucide-react";

const FEATURES = [
  {
    title: "Upload messy files",
    body: "CSV, Excel, and JSON with schema detection and safe storage.",
    icon: Database,
  },
  {
    title: "Diagnose data quality",
    body: "Real scores for completeness, validity, uniqueness, and consistency.",
    icon: ShieldCheck,
  },
  {
    title: "Ask evidence-based questions",
    body: "The AI Copilot answers from calculated metrics, not invented numbers.",
    icon: Sparkles,
  },
];

const STEPS = [
  "Upload sales, customers, inventory, or expense files",
  "Profile and score quality issues automatically",
  "Preview cleaning, validate, then load trusted rows",
  "Explore analytics and ask the business copilot",
];

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-6xl px-5 py-10 lg:py-16">
      <div className="overflow-hidden rounded-[2rem] border border-line bg-panel shadow-soft">
        <div className="grid gap-8 bg-[linear-gradient(135deg,#0f766e_0%,#115e59_45%,#0f172a_100%)] px-8 py-12 text-white lg:grid-cols-[1.2fr_0.8fr] lg:px-12 lg:py-16">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-teal-100">MSME Data Copilot</p>
            <h1 className="mt-4 font-display text-4xl font-bold leading-tight lg:text-5xl">
              From messy business data to trusted intelligence
            </h1>
            <p className="mt-4 max-w-xl text-base text-teal-50/90 lg:text-lg">
              Upload spreadsheets, diagnose quality problems, clean and validate them, then explore revenue,
              customers, inventory, and expenses with an AI copilot grounded in your loaded data.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/app"
                className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-semibold text-accent-2"
              >
                Open dashboard <ArrowRight size={16} />
              </Link>
              <Link
                href="/app/upload"
                className="inline-flex items-center gap-2 rounded-xl border border-white/30 px-5 py-3 text-sm font-semibold text-white"
              >
                Upload dataset
              </Link>
            </div>
          </div>
          <div className="rounded-3xl border border-white/15 bg-white/10 p-6 backdrop-blur">
            <p className="text-sm font-semibold text-teal-100">How it works</p>
            <ol className="mt-4 space-y-3">
              {STEPS.map((step, index) => (
                <li key={step} className="flex gap-3 text-sm text-white/90">
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white/15 text-xs font-bold">
                    {index + 1}
                  </span>
                  {step}
                </li>
              ))}
            </ol>
          </div>
        </div>

        <div className="grid gap-4 p-6 md:grid-cols-3 lg:p-8">
          {FEATURES.map((feature) => {
            const Icon = feature.icon;
            return (
              <div key={feature.title} className="rounded-2xl border border-line bg-slate-50 p-5">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-50 text-accent">
                  <Icon size={18} />
                </div>
                <h2 className="mt-4 font-display text-lg font-semibold">{feature.title}</h2>
                <p className="mt-2 text-sm text-muted">{feature.body}</p>
              </div>
            );
          })}
        </div>

        <div className="border-t border-line px-6 py-6 lg:px-8">
          <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
            <CheckCircle2 size={16} className="text-ok" />
            Original uploads stay in Bronze. Cleaning writes Silver. Analytics read Gold only.
          </div>
        </div>
      </div>
    </div>
  );
}
