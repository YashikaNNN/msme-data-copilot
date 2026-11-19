"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { UploadCloud } from "lucide-react";
import { apiPost } from "@/lib/api";
import { Button, Card, Input, Select, Textarea } from "@/components/ui";

const CATEGORIES = ["sales", "customers", "products", "inventory", "expenses", "orders", "other"];
const MAX_MB = 20;

export default function UploadPage() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("sales");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [drag, setDrag] = useState(false);

  function validate(selected: File | null) {
    if (!selected) return "Choose a CSV, XLSX, or JSON file.";
    const ext = selected.name.split(".").pop()?.toLowerCase();
    if (!ext || !["csv", "xlsx", "json"].includes(ext)) return "Only CSV, XLSX, and JSON are allowed.";
    if (selected.size > MAX_MB * 1024 * 1024) return `File must be under ${MAX_MB} MB.`;
    return "";
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const problem = validate(file);
    if (problem) {
      setError(problem);
      return;
    }
    if (!name.trim()) {
      setError("Give the dataset a name.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", file!);
      form.append("name", name.trim());
      form.append("category", category);
      form.append("description", description);
      const dataset = await apiPost<{ id: number }>("/datasets/upload", form);
      router.push(`/app/datasets/${dataset.id}`);
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Upload dataset</h1>
        <p className="mt-1 text-muted">Files are stored safely. The original copy is never overwritten by cleaning.</p>
      </div>

      <Card>
        <form className="space-y-5" onSubmit={onSubmit}>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              const next = e.dataTransfer.files?.[0] || null;
              setFile(next);
              if (next && !name) setName(next.name.replace(/\.[^.]+$/, ""));
              setError(validate(next));
            }}
            className={`rounded-2xl border-2 border-dashed px-6 py-10 text-center ${
              drag ? "border-accent bg-teal-50" : "border-line bg-slate-50"
            }`}
          >
            <UploadCloud className="mx-auto text-accent" />
            <p className="mt-3 font-semibold">Drag and drop a file here</p>
            <p className="mt-1 text-sm text-muted">CSV, XLSX, or JSON · max {MAX_MB} MB</p>
            <label className="mt-4 inline-flex cursor-pointer rounded-xl bg-white px-4 py-2 text-sm font-semibold text-accent shadow-sm">
              Choose file
              <input
                type="file"
                accept=".csv,.xlsx,.json,application/json,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                className="hidden"
                onChange={(e) => {
                  const next = e.target.files?.[0] || null;
                  setFile(next);
                  if (next && !name) setName(next.name.replace(/\.[^.]+$/, ""));
                  setError(validate(next));
                }}
              />
            </label>
            {file ? <p className="mt-3 text-sm text-ink">{file.name} · {(file.size / 1024).toFixed(1)} KB</p> : null}
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <label className="space-y-2 text-sm">
              <span className="font-semibold">Dataset name</span>
              <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="January sales" />
            </label>
            <label className="space-y-2 text-sm">
              <span className="font-semibold">Category</span>
              <Select value={category} onChange={(e) => setCategory(e.target.value)}>
                {CATEGORIES.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </Select>
            </label>
          </div>

          <label className="block space-y-2 text-sm">
            <span className="font-semibold">Description</span>
            <Textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Optional notes about this file"
            />
          </label>

          {error ? <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p> : null}

          <Button type="submit" disabled={loading}>
            {loading ? "Uploading…" : "Upload and profile"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
