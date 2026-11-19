"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { UploadCloud, X } from "lucide-react";
import { apiPost } from "@/lib/api";
import { Button, Card, Input, Select, Textarea } from "@/components/ui";

const CATEGORIES = ["sales", "customers", "products", "inventory", "expenses", "orders", "other"];
const MAX_MB = 20;

type QueuedFile = {
  file: File;
  name: string;
  category: string;
  description: string;
};

function guessCategory(filename: string): string {
  const lower = filename.toLowerCase();
  if (lower.includes("sale") || lower.includes("order")) return "sales";
  if (lower.includes("customer")) return "customers";
  if (lower.includes("product")) return "products";
  if (lower.includes("invent") || lower.includes("stock")) return "inventory";
  if (lower.includes("expense")) return "expenses";
  return "other";
}

export default function UploadPage() {
  const router = useRouter();
  const [queue, setQueue] = useState<QueuedFile[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState("");
  const [drag, setDrag] = useState(false);

  function validate(selected: File) {
    const ext = selected.name.split(".").pop()?.toLowerCase();
    if (!ext || !["csv", "xlsx", "json"].includes(ext)) return "Only CSV, XLSX, and JSON are allowed.";
    if (selected.size > MAX_MB * 1024 * 1024) return `Each file must be under ${MAX_MB} MB.`;
    return "";
  }

  function addFiles(list: FileList | File[]) {
    const next: QueuedFile[] = [];
    for (const file of Array.from(list)) {
      const problem = validate(file);
      if (problem) {
        setError(problem);
        return;
      }
      next.push({
        file,
        name: file.name.replace(/\.[^.]+$/, ""),
        category: guessCategory(file.name),
        description: "",
      });
    }
    setError("");
    setQueue((prev) => [...prev, ...next]);
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (queue.length === 0) {
      setError("Add at least one file.");
      return;
    }
    if (queue.some((item) => !item.name.trim())) {
      setError("Every dataset needs a name.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      let lastId = 0;
      for (let index = 0; index < queue.length; index += 1) {
        const item = queue[index];
        setProgress(`Uploading ${index + 1} of ${queue.length}: ${item.name}`);
        const form = new FormData();
        form.append("file", item.file);
        form.append("name", item.name.trim());
        form.append("category", item.category);
        form.append("description", item.description);
        const dataset = await apiPost<{ id: number }>("/datasets/upload", form);
        lastId = dataset.id;
      }
      router.push(queue.length === 1 ? `/app/datasets/${lastId}` : "/app/datasets");
    } catch (err: any) {
      setError(err.message || "Upload failed");
    } finally {
      setLoading(false);
      setProgress("");
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold">Upload datasets</h1>
        <p className="mt-1 text-muted">
          Upload one or many CSV/XLSX/JSON files. Originals stay in Bronze and are never overwritten by cleaning.
        </p>
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
              if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
            }}
            className={`rounded-2xl border-2 border-dashed px-6 py-10 text-center ${
              drag ? "border-accent bg-teal-50" : "border-line bg-slate-50"
            }`}
          >
            <UploadCloud className="mx-auto text-accent" />
            <p className="mt-3 font-semibold">Drag and drop files here</p>
            <p className="mt-1 text-sm text-muted">CSV, XLSX, or JSON · max {MAX_MB} MB each · multiple allowed</p>
            <label className="mt-4 inline-flex cursor-pointer rounded-xl bg-white px-4 py-2 text-sm font-semibold text-accent shadow-sm">
              Choose files
              <input
                type="file"
                multiple
                accept=".csv,.xlsx,.json,application/json,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.length) addFiles(e.target.files);
                  e.target.value = "";
                }}
              />
            </label>
          </div>

          {queue.length > 0 ? (
            <div className="space-y-4">
              {queue.map((item, index) => (
                <div key={`${item.file.name}-${index}`} className="rounded-2xl border border-line p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="font-semibold">{item.file.name}</div>
                      <div className="text-xs text-muted">{(item.file.size / 1024).toFixed(1)} KB</div>
                    </div>
                    <button
                      type="button"
                      className="rounded-lg p-1 text-muted hover:bg-slate-100 hover:text-ink"
                      onClick={() => setQueue((prev) => prev.filter((_, i) => i !== index))}
                    >
                      <X size={16} />
                    </button>
                  </div>
                  <div className="mt-3 grid gap-3 md:grid-cols-2">
                    <label className="space-y-1 text-sm">
                      <span className="font-semibold">Dataset name</span>
                      <Input
                        value={item.name}
                        onChange={(e) =>
                          setQueue((prev) =>
                            prev.map((row, i) => (i === index ? { ...row, name: e.target.value } : row)),
                          )
                        }
                      />
                    </label>
                    <label className="space-y-1 text-sm">
                      <span className="font-semibold">Category</span>
                      <Select
                        value={item.category}
                        onChange={(e) =>
                          setQueue((prev) =>
                            prev.map((row, i) => (i === index ? { ...row, category: e.target.value } : row)),
                          )
                        }
                      >
                        {CATEGORIES.map((category) => (
                          <option key={category} value={category}>
                            {category}
                          </option>
                        ))}
                      </Select>
                    </label>
                  </div>
                  <label className="mt-3 block space-y-1 text-sm">
                    <span className="font-semibold">Description</span>
                    <Textarea
                      rows={2}
                      value={item.description}
                      onChange={(e) =>
                        setQueue((prev) =>
                          prev.map((row, i) => (i === index ? { ...row, description: e.target.value } : row)),
                        )
                      }
                    />
                  </label>
                </div>
              ))}
            </div>
          ) : null}

          {progress ? <p className="rounded-xl bg-teal-50 px-4 py-3 text-sm text-accent-2">{progress}</p> : null}
          {error ? <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p> : null}

          <Button type="submit" disabled={loading || queue.length === 0}>
            {loading ? progress || "Uploading…" : `Upload and profile (${queue.length})`}
          </Button>
        </form>
      </Card>
    </div>
  );
}
