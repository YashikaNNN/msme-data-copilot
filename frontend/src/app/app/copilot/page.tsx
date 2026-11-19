"use client";

import { useEffect, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";
import { Badge, Button, Card, EmptyState, Input, Skeleton } from "@/components/ui";

export default function CopilotPage() {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      apiGet<{ items: string[] }>("/copilot/suggestions"),
      apiGet<{ items: any[] }>("/copilot/sessions"),
    ])
      .then(([sugs, sess]) => {
        setSuggestions(sugs.items);
        setSessions(sess.items);
      })
      .catch((err) => setError(err.message));
  }, []);

  async function openSession(id: number) {
    const session = await apiGet<any>(`/copilot/sessions/${id}`);
    setSessionId(session.id);
    setMessages(session.messages || []);
  }

  async function ask(text: string) {
    if (!text.trim()) return;
    setBusy(true);
    setError("");
    try {
      const response = await apiPost<any>("/copilot/ask", {
        question: text,
        session_id: sessionId,
      });
      setSessionId(response.session_id);
      setQuestion("");
      setMessages((prev) => [
        ...prev,
        { role: "user", content: text },
        {
          role: "assistant",
          content: response.answer,
          payload: {
            metrics: response.metrics,
            sources: response.sources,
            llm_note: response.llm_note,
            llm_used: response.llm_used,
          },
        },
      ]);
      const sess = await apiGet<{ items: any[] }>("/copilot/sessions");
      setSessions(sess.items);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[240px_1fr]">
      <Card>
        <h2 className="font-display text-lg font-semibold">History</h2>
        <div className="mt-3 space-y-2">
          {sessions.length === 0 ? (
            <p className="text-sm text-muted">No conversations yet.</p>
          ) : (
            sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => openSession(session.id)}
                className={`w-full rounded-xl px-3 py-2 text-left text-sm ${
                  sessionId === session.id ? "bg-teal-50 text-accent" : "hover:bg-slate-50"
                }`}
              >
                {session.title}
              </button>
            ))
          )}
        </div>
      </Card>

      <div className="space-y-4">
        <div>
          <h1 className="font-display text-3xl font-bold">AI Business Copilot</h1>
          <p className="mt-1 text-muted">
            Answers use analytics functions first. LLM narration is optional and never invents numbers.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {suggestions.map((item) => (
            <button
              key={item}
              onClick={() => ask(item)}
              className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-medium hover:border-accent"
            >
              {item}
            </button>
          ))}
        </div>

        <Card className="min-h-[420px] space-y-4">
          {messages.length === 0 ? (
            <EmptyState
              title="Ask a business question"
              description="Try product revenue, inventory mismatches, expense increases, or data-quality problems."
            />
          ) : (
            messages.map((message, index) => (
              <div
                key={index}
                className={`rounded-2xl px-4 py-3 ${
                  message.role === "user" ? "ml-8 bg-accent text-white" : "mr-8 bg-slate-50"
                }`}
              >
                <div className="whitespace-pre-wrap text-sm">{message.content}</div>
                {message.payload?.metrics?.length ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {message.payload.metrics.map((metric: any) => (
                      <Badge key={metric.label} tone="accent">
                        {metric.label}: {metric.value}
                      </Badge>
                    ))}
                  </div>
                ) : null}
                {message.payload?.sources?.length ? (
                  <p className="mt-2 text-xs text-muted">Sources: {message.payload.sources.join(", ")}</p>
                ) : null}
                {message.payload?.llm_note ? (
                  <p className="mt-1 text-xs text-muted">{message.payload.llm_note}</p>
                ) : null}
              </div>
            ))
          )}
        </Card>

        {error ? <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-danger">{error}</p> : null}

        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
        >
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Which products generated the highest revenue?"
          />
          <Button type="submit" disabled={busy}>{busy ? "Thinking…" : "Ask"}</Button>
        </form>
      </div>
    </div>
  );
}
