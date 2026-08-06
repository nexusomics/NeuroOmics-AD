import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type Analysis } from "../api/client";
import { Badge, Card, Spinner } from "../components/ui/ui";

interface ChatMsg {
  role: "user" | "assistant";
  content: string;
}

export default function AssistantPage() {
  const { id } = useParams<{ id: string }>();
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [selectedAnalyses, setSelectedAnalyses] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [mode, setMode] = useState("local");
  const [busy, setBusy] = useState(false);
  const [manuscript, setManuscript] = useState<Record<string, string> | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!id) return;
    api.analyses(id).then((a) => {
      const done = a.filter((x) => x.status === "completed");
      setAnalyses(a);
      setSelectedAnalyses(done.map((x) => x.id));
    });
    api.assistantChat({ message: "" }).then((r) => setMode(r.mode)).catch(() => {});
  }, [id]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    try {
      const res = await api.assistantChat({ message: text, project_id: id, analysis_ids: selectedAnalyses });
      setMessages((m) => [...m, { role: "assistant", content: res.reply }]);
      setMode(res.mode);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `⚠ ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  };

  const draftManuscript = async () => {
    setBusy(true);
    try {
      const ms = (await api.manuscript({ analysis_ids: selectedAnalyses, include_discussion: true, include_methods: true })) as Record<string, string>;
      setManuscript(ms);
    } catch (e: any) {
      setMessages((m) => [...m, { role: "assistant", content: `⚠ ${e.message}` }]);
    } finally {
      setBusy(false);
    }
  };

  const md = (content: string) => (
    <div className="space-y-2">
      {content.split("\n\n").map((p, i) => (
        <p key={i} className="text-sm leading-relaxed">
          {p.split("**").map((part, j) =>
            j % 2 === 1 ? <strong key={j} className="text-slate-100">{part}</strong> : part
          )}
        </p>
      ))}
    </div>
  );

  const suggestions = [
    "Which genes are most differentially expressed and what do they mean?",
    "Interpret the enriched pathways in the context of AD biology.",
    "What are the top drug repurposing candidates and why?",
    "Recommend a drug combination targeting complementary mechanisms.",
    "Draft the Results section for my analyses.",
  ];

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-white">AI research assistant</h1>
          <p className="text-sm text-slate-400">Interprets your analyses, explains biological significance, recommends targets & drug combinations.</p>
        </div>
        <Badge tone={mode === "llm" ? "emerald" : "cyan"}>{mode === "llm" ? "LLM mode" : "Local interpretation engine"}</Badge>
      </header>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2 flex flex-col">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-bold text-slate-100">Conversation</h2>
            <button className="btn-ghost px-3 py-1 text-xs" onClick={() => setMessages([])}>Clear</button>
          </div>
          <div className="max-h-[420px] flex-1 space-y-3 overflow-y-auto pr-1">
            {messages.length === 0 && (
              <div className="space-y-2">
                <p className="text-sm text-slate-400">Ask anything about your project's analyses, or try:</p>
                {suggestions.map((s) => (
                  <button key={s} className="block w-full rounded-lg border border-ink-700/60 bg-ink-900/40 px-3 py-2 text-left text-xs text-slate-300 hover:border-teal-500/50" onClick={() => setInput(s)}>
                    “{s}”
                  </button>
                ))}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`rounded-xl px-4 py-3 ${m.role === "user" ? "ml-10 bg-teal-500/15 text-teal-100" : "mr-6 bg-ink-900/70 text-slate-300"}`}>
                {md(m.content)}
              </div>
            ))}
            {busy && <div className="text-sm text-slate-500"><Spinner label="Thinking…" /></div>}
            <div ref={bottomRef} />
          </div>
          <div className="mt-3 flex gap-2">
            <input
              className="input"
              placeholder="Ask about genes, pathways, hubs, drugs, combinations…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
            />
            <button className="btn-primary whitespace-nowrap" onClick={send} disabled={busy}>Send</button>
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <h2 className="mb-2 font-bold text-slate-100">Context</h2>
            <label className="label">Project</label>
            <div className="mb-3 rounded-lg bg-ink-900/50 px-3 py-2 text-sm text-slate-300">Current project</div>
            <label className="label">Include analyses</label>
            <div className="max-h-48 space-y-1 overflow-y-auto">
              {analyses.map((a) => (
                <label key={a.id} className="flex cursor-pointer items-center gap-2 text-xs text-slate-400">
                  <input
                    type="checkbox"
                    checked={selectedAnalyses.includes(a.id)}
                    disabled={a.status !== "completed"}
                    onChange={() =>
                      setSelectedAnalyses((prev) => (prev.includes(a.id) ? prev.filter((x) => x !== a.id) : [...prev, a.id]))
                    }
                    className="accent-teal-500"
                  />
                  <span className="truncate">{a.name}</span>
                </label>
              ))}
            </div>
          </Card>
          <Card>
            <h2 className="mb-2 font-bold text-slate-100">Manuscript assistant</h2>
            <p className="mb-3 text-xs text-slate-500">Generate manuscript-ready Results, Discussion and Methods from selected analyses.</p>
            <button className="btn-primary w-full" onClick={draftManuscript} disabled={busy || !selectedAnalyses.length}>
              ✍ Draft Results & Discussion
            </button>
          </Card>
        </div>
      </div>

      {manuscript && (
        <Card>
          <h2 className="mb-3 font-bold text-slate-100">Manuscript draft</h2>
          <div className="grid gap-4 lg:grid-cols-2">
            {[["results", "Results"], ["discussion", "Discussion"], ["methods", "Methods"]].map(([key, label]) =>
              manuscript[key] ? (
                <div key={key}>
                  <h3 className="mb-1 text-sm font-bold uppercase tracking-wide text-teal-400">{label}</h3>
                  <div className="space-y-2 rounded-lg bg-ink-900/60 p-3 text-sm leading-relaxed text-slate-300">
                    {manuscript[key].split("\n\n").map((p, i) => (
                      <p key={i}>{p}</p>
                    ))}
                  </div>
                </div>
              ) : null
            )}
          </div>
        </Card>
      )}
    </div>
  );
}
