import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type Analysis } from "../api/client";
import { Card, EmptyState, ErrorBanner, Spinner } from "../components/ui/ui";

const FORMATS = [
  { key: "pdf", label: "📕 PDF", desc: "Publication-ready via ReportLab" },
  { key: "docx", label: "📘 Word (.docx)", desc: "Editable manuscript-style" },
  { key: "pptx", label: "📙 PowerPoint", desc: "Slide deck of results" },
  { key: "xlsx", label: "📗 Excel (.xlsx)", desc: "Multi-sheet tables" },
  { key: "csv", label: "📄 CSV", desc: "Raw tables" },
  { key: "html", label: "🌐 HTML", desc: "Interactive, embeddable" },
];

export default function ReportsPage() {
  const { id } = useParams<{ id: string }>();
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [formats, setFormats] = useState<string[]>(["pdf", "docx"]);
  const [dpi, setDpi] = useState(300);
  const [generating, setGenerating] = useState(false);
  const [files, setFiles] = useState<Record<string, string> | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    api.analyses(id).then((a) => {
      setAnalyses(a);
      setSelected(a.filter((x) => x.status === "completed").map((x) => x.id));
    });
  }, [id]);

  const generate = async () => {
    if (!selected.length) {
      setError("Select at least one completed analysis.");
      return;
    }
    setGenerating(true);
    setError("");
    try {
      const res = (await api.generateReport({ analysis_ids: selected, formats, title: "NeuroOmics-AD Analysis Report", dpi })) as any;
      setFiles(res.files);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-extrabold text-white">Reports</h1>
        <p className="text-sm text-slate-400">Automatic multi-format reports with methods, results, figures, tables, interpretation and references.</p>
      </header>

      {error && <ErrorBanner error={error} />}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2 className="mb-3 font-bold text-slate-100">1 · Select analyses</h2>
          {analyses.length === 0 ? (
            <EmptyState icon="📄" title="No analyses" hint="Run analyses first." />
          ) : (
            <div className="space-y-1.5">
              {analyses.map((a) => (
                <label key={a.id} className="flex cursor-pointer items-center gap-3 rounded-lg border border-ink-700/60 bg-ink-900/40 px-3 py-2 hover:bg-ink-700/30">
                  <input
                    type="checkbox"
                    checked={selected.includes(a.id)}
                    disabled={a.status !== "completed"}
                    onChange={() =>
                      setSelected((prev) => (prev.includes(a.id) ? prev.filter((x) => x !== a.id) : [...prev, a.id]))
                    }
                    className="accent-teal-500"
                  />
                  <span className="text-sm text-slate-300">{a.name}</span>
                  <span className="ml-auto text-xs text-slate-500">{a.status}</span>
                </label>
              ))}
            </div>
          )}
        </Card>

        <div className="space-y-4">
          <Card>
            <h2 className="mb-3 font-bold text-slate-100">2 · Formats</h2>
            <div className="space-y-2">
              {FORMATS.map((f) => (
                <label key={f.key} className="flex cursor-pointer items-center gap-2 rounded-lg border border-ink-700/60 px-3 py-2 hover:bg-ink-700/30">
                  <input
                    type="checkbox"
                    checked={formats.includes(f.key)}
                    onChange={() =>
                      setFormats((prev) => (prev.includes(f.key) ? prev.filter((x) => x !== f.key) : [...prev, f.key]))
                    }
                    className="accent-teal-500"
                  />
                  <div>
                    <div className="text-sm text-slate-200">{f.label}</div>
                    <div className="text-[11px] text-slate-500">{f.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </Card>
          <Card>
            <label className="label">Figure resolution (DPI)</label>
            <select className="input" value={dpi} onChange={(e) => setDpi(Number(e.target.value))}>
              {[150, 300, 600].map((d) => (
                <option key={d} value={d}>{d} dpi {d === 300 ? "(journal standard)" : d === 600 ? "(print)" : ""}</option>
              ))}
            </select>
            <button className="btn-primary mt-3 w-full" onClick={generate} disabled={generating}>
              {generating ? "Generating…" : "⚡ Generate report"}
            </button>
          </Card>
        </div>
      </div>

      {generating && <Spinner label="Composing PDF / Word / Excel / PPT / HTML…" />}

      {files && !generating && (
        <Card>
          <h2 className="mb-3 font-bold text-slate-100">Download</h2>
          <div className="grid gap-2 md:grid-cols-3">
            {Object.entries(files).map(([fmt, path]) => (
              <a
                key={fmt}
                className="flex items-center justify-between rounded-lg border border-teal-500/40 bg-teal-500/10 px-4 py-3 text-sm font-semibold text-teal-300 transition hover:bg-teal-500/20"
                href={api.reportUrl(selected[0], path.split("/").pop()!)}
                download
              >
                <span>{FORMATS.find((f) => f.key === fmt)?.label || fmt}</span>
                <span>↓</span>
              </a>
            ))}
          </div>
          <p className="mt-3 text-xs text-slate-500">
            Files: {Object.values(files).filter(Boolean).length} of {formats.length} formats produced in <code>{selected[0]}</code>'s artifact store.
          </p>
        </Card>
      )}
    </div>
  );
}
