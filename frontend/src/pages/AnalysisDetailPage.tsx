import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type Analysis, type Artifact } from "../api/client";
import { Badge, Card, EmptyState, ErrorBanner, Progress, Spinner } from "../components/ui/ui";
import PlotlyChart from "../components/charts/PlotlyChart";

function ResultView({ result, analysis }: { result: any; analysis: Analysis }) {
  if (!result) return <EmptyState icon="◌" title="No structured result" hint="This analysis stored no JSON payload." />;

  if (analysis.analysis_type === "differential_expression" && result.table) {
    const table = result.table.slice(0, 25);
    return (
      <div className="space-y-4">
        <Card>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
            {[
              ["Tested genes", result.summary?.tested_genes],
              ["Significant", result.summary?.significant],
              ["Up", result.summary?.upregulated],
              ["Down", result.summary?.downregulated],
              ["Method", result.summary?.method],
            ].map(([l, v]) => (
              <div key={String(l)} className="rounded-lg bg-ink-900/50 p-3">
                <div className="text-[10px] font-bold uppercase text-slate-500">{l}</div>
                <div className="mt-0.5 truncate text-sm font-semibold text-slate-200">{String(v ?? "—")}</div>
              </div>
            ))}
          </div>
        </Card>
        <Card>
          <h3 className="mb-2 font-bold text-slate-100">Volcano plot</h3>
          <PlotlyChart
            data={[
              {
                type: "scattergl", mode: "markers",
                x: table.map((r: any) => r.log2fc), y: table.map((r: any) => -Math.log10(Math.max(r.pvalue, 1e-300))),
                text: table.map((r: any) => r.gene),
                marker: { color: table.map((r: any) => (r.sig ? (r.log2fc > 0 ? "#d62728" : "#1f77b4") : "#64748b")), size: 6 },
              },
            ]}
            layout={{ xaxis: { title: "log₂ fold change" }, yaxis: { title: "−log₁₀(p)" } }}
            title="Differential expression"
          />
        </Card>
        <Card>
          <h3 className="mb-2 font-bold text-slate-100">Top differentially expressed genes</h3>
          <table className="table-data">
            <thead><tr><th>Gene</th><th>log₂FC</th><th>p-value</th><th>FDR</th><th>Direction</th></tr></thead>
            <tbody>
              {table.map((r: any) => (
                <tr key={r.gene}>
                  <td className="font-mono font-medium text-slate-200">{r.gene}</td>
                  <td className="font-mono">{r.log2fc.toFixed(3)}</td>
                  <td className="font-mono">{r.pvalue.toExponential(2)}</td>
                  <td className="font-mono">{r.fdr.toExponential(2)}</td>
                  <td><Badge tone={r.log2fc > 0 ? "rose" : "cyan"}>{r.log2fc > 0 ? "up" : "down"}</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>
    );
  }

  if (analysis.analysis_type === "enrichment" && result.table) {
    return (
      <Card>
        <h3 className="mb-2 font-bold text-slate-100">Pathway enrichment</h3>
        <PlotlyChart
          data={[
            {
              type: "bar", orientation: "h",
              y: result.table.slice(0, 12).map((r: any) => r.pathway.slice(0, 60)),
              x: result.table.slice(0, 12).map((r: any) => -Math.log10(Math.max(r.fdr, 1e-300))),
              marker: { color: "#14b8a6" },
            },
          ]}
          layout={{ xaxis: { title: "−log₁₀(FDR)" }, yaxis: { autorange: "reversed" } }}
          title="Enriched pathways"
        />
      </Card>
    );
  }

  if (analysis.analysis_type === "network" && result.hub_genes) {
    return (
      <Card>
        <h3 className="mb-2 font-bold text-slate-100">Hub genes</h3>
        <div className="flex flex-wrap gap-2">
          {result.hub_genes.map((g: string) => (
            <span key={g} className="badge-rose font-mono">{g}</span>
          ))}
        </div>
      </Card>
    );
  }

  if (analysis.analysis_type === "ml" && result.results) {
    return (
      <Card>
        <h3 className="mb-2 font-bold text-slate-100">Model performance</h3>
        <PlotlyChart
          data={[
            {
              type: "bar",
              x: result.results.map((m: any) => m.algorithm),
              y: result.results.map((m: any) => m.metrics?.roc_auc || 0),
              marker: { color: result.results.map((_: any, i: number) => `hsl(${170 + i * 24}, 60%, 55%)`) },
              text: result.results.map((m: any) => `AUC ${(m.metrics?.roc_auc || 0).toFixed(3)}`),
            },
          ]}
          layout={{ yaxis: { title: "ROC-AUC", range: [0, 1] } }}
          title="ML model comparison"
        />
      </Card>
    );
  }

  if (analysis.analysis_type === "drug_repurposing" && result.candidates) {
    return (
      <Card>
        <h3 className="mb-2 font-bold text-slate-100">Top candidates</h3>
        <table className="table-data">
          <thead><tr><th>#</th><th>Drug</th><th>Mechanism</th><th>FDA</th><th>Composite</th></tr></thead>
          <tbody>
            {result.candidates.slice(0, 10).map((c: any) => (
              <tr key={c.drug_name}>
                <td>{c.rank}</td>
                <td className="font-medium text-slate-200">{c.drug_name}</td>
                <td className="max-w-[280px] text-xs">{c.mechanism}</td>
                <td><Badge tone={c.fda_status === "Approved" ? "emerald" : "amber"}>{c.fda_status}</Badge></td>
                <td className="font-mono">{c.composite_score.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    );
  }

  return (
    <Card>
      <pre className="max-h-[480px] overflow-auto rounded-lg bg-ink-900/60 p-4 text-xs text-slate-300">
        {JSON.stringify(result, null, 2).slice(0, 12000)}
      </pre>
    </Card>
  );
}

export default function AnalysisDetailPage() {
  const { id: analysisId } = useParams<{ id: string }>();
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [result, setResult] = useState<any>(null);

  const load = useCallback(() => {
    if (!analysisId) return;
    api.analysis(analysisId).then((a) => {
      setAnalysis(a);
      if (a.status === "completed") {
        api.analysisResult(analysisId).then(setResult).catch(() => setResult(null));
        api.artifacts(analysisId).then(setArtifacts).catch(() => setArtifacts([]));
      }
    });
  }, [analysisId]);

  useEffect(load, [load]);

  if (!analysis) return <Spinner label="Loading analysis…" />;

  const figures = artifacts.filter((a) => a.kind === "figure");

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-white">{analysis.name}</h1>
          <p className="text-sm text-slate-400">
            {analysis.analysis_type} · created {analysis.created_at ? new Date(analysis.created_at).toLocaleString() : ""}
          </p>
        </div>
        <Badge tone={analysis.status === "completed" ? "emerald" : analysis.status === "failed" ? "rose" : "amber"}>{analysis.status}</Badge>
      </header>

      {analysis.status === "failed" && <ErrorBanner error={analysis.error_message || "Analysis failed"} />}
      {(analysis.status === "queued" || analysis.status === "running") && (
        <Card>
          <div className="mb-1 flex justify-between text-sm">
            <span className="text-slate-300">Analysis in progress</span>
            <span className="font-mono text-teal-300">{analysis.progress}%</span>
          </div>
          <Progress value={analysis.progress} />
          <button className="btn-ghost mt-3 text-xs" onClick={load}>Refresh</button>
        </Card>
      )}

      {analysis.status === "completed" && (
        <>
          <ResultView result={result} analysis={analysis} />
          {figures.length > 0 && (
            <Card>
              <h3 className="mb-3 font-bold text-slate-100">Figures & artifacts</h3>
              <div className="grid gap-4 md:grid-cols-2">
                {figures.map((f) => (
                  <div key={f.id} className="rounded-lg border border-ink-700/60 bg-ink-900/40 p-3">
                    <div className="mb-2 text-sm font-semibold text-slate-200">{f.name}</div>
                    <img src={api.artifactUrl(analysis.id, f.id)} alt={f.name} className="w-full rounded-md" />
                    <a className="mt-2 inline-block text-xs text-teal-400 hover:underline" href={api.artifactUrl(analysis.id, f.id)} download>
                      ↓ Download {f.format} ({f.size_bytes} B)
                    </a>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
