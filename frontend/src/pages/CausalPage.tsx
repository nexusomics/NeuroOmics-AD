import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { Badge, Card, EmptyState, ErrorBanner, Spinner, StatCard } from "../components/ui/ui";
import PlotlyChart from "../components/charts/PlotlyChart";
import NetworkGraph from "../components/charts/NetworkGraph";

interface Resource {
  accession: string; name: string; cohort: string; modalities: string[];
  ancestries: string[]; brain_regions: string[]; biofluids: string[];
  phenotypes: string[]; n_samples: number; citation: string; mined_depth: string;
}

export default function CausalPage() {
  const { id } = useParams<{ id: string }>();
  const [resources, setResources] = useState<Resource[] | null>(null);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);
  const [query, setQuery] = useState({ ancestries: "", modalities: "", biofluids: "", diagnosis: "" });
  const [qResult, setQResult] = useState<any>(null);
  const [pipe, setPipe] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .raw("/causal/resources")
      .then((r: any) => { setResources(r.resources); setStats(r.stats); })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runQuery = async () => {
    setBusy(true); setError("");
    try {
      const params = new URLSearchParams();
      if (query.ancestries) params.set("ancestries", query.ancestries);
      if (query.modalities) params.set("modalities", query.modalities);
      if (query.biofluids) params.set("biofluids", query.biofluids);
      if (query.diagnosis) params.set("diagnosis", query.diagnosis);
      const r: any = await api.raw(`/causal/query?${params.toString()}`);
      setQResult(r);
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };

  const runPipeline = async (mode: string) => {
    setBusy(true); setError("");
    try {
      const r: any = await api.raw("/causal/pipeline", {
        method: "POST",
        body: JSON.stringify({
          mode,
          options: { latent_method: "mofa", n_factors: 5, n_subtypes: 3, n_boot: 12, n_per_ancestry: 80 },
          ...(mode === "catalog" && query.ancestries ? { ancestries: query.ancestries.split(",").map((s) => s.trim()) } : {}),
        }),
      });
      setPipe(r);
    } catch (e: any) { setError(e.message); } finally { setBusy(false); }
  };

  const causalEdges = pipe?.causal?.notears?.edges || [];
  const causalNodes = Array.from(new Set(causalEdges.flatMap((e: [string, string]) => e))).map((n: any) => ({ id: n, hub: String(n).split(":")[1] === "PROT1" }));
  const gtEdges = pipe?.ground_truth?.edges || [];
  const gtSet = new Set(gtEdges.map((e: [string, string]) => `${e[0]}|${e[1]}`));
  const meta = pipe?.meta_analysis || {};

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-extrabold text-white">🧬 Causal multi-omics discovery</h1>
        <p className="text-sm text-slate-400">
          Harmonized Knight-ADRC · ADSP R4 · AMP-AD multi-ethnic · plasma multi-omics across ancestries —
          QC → latent fusion → causal inference → ancestry-stratified meta → subtypes.
        </p>
      </header>
      {error && <ErrorBanner error={error} />}
      {busy && <Spinner label="Running…" />}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2 className="mb-2 font-bold text-slate-100">Harmonized resource catalog</h2>
          {!resources ? <Spinner /> : (
            <table className="table-data">
              <thead><tr><th>Accession</th><th>Resource</th><th>Modalities</th><th>Ancestries</th><th>Samples</th><th>Mined</th></tr></thead>
              <tbody>
                {resources.map((r) => (
                  <tr key={r.accession}>
                    <td className="font-mono text-xs text-teal-300">{r.accession}</td>
                    <td className="max-w-[220px] text-xs">
                      <div className="font-medium text-slate-200">{r.name}</div>
                      <div className="text-[10px] text-slate-500">{r.citation}</div>
                    </td>
                    <td className="text-xs">{r.modalities.slice(0, 3).join(", ")}{r.modalities.length > 3 ? "…" : ""}</td>
                    <td className="text-xs">{r.ancestries.join("/")}</td>
                    <td className="font-mono text-xs">{r.n_samples.toLocaleString()}</td>
                    <td><Badge tone={r.mined_depth === "extensive" ? "amber" : r.mined_depth === "not-yet-mined" ? "rose" : "cyan"}>{r.mined_depth}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
        <Card>
          <h2 className="mb-2 font-bold text-slate-100">Index stats</h2>
          {stats && (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Resources</span><span className="font-mono">{String(stats.n_resources)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Indexed samples</span><span className="font-mono">{(stats.n_indexed_samples as number).toLocaleString()}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Modalities</span><span className="text-xs">{(stats.modalities as string[]).join(", ")}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Ancestries</span><span className="text-xs">{(stats.ancestries as string[]).join(", ")}</span></div>
            </div>
          )}
          <h3 className="mb-1 mt-4 font-bold text-slate-100">Query builder</h3>
          <input className="input mb-2 text-xs" placeholder="Ancestries (e.g. AA,LA)" value={query.ancestries} onChange={(e) => setQuery({ ...query, ancestries: e.target.value })} />
          <input className="input mb-2 text-xs" placeholder="Modalities (e.g. proteomics,transcriptomics)" value={query.modalities} onChange={(e) => setQuery({ ...query, modalities: e.target.value })} />
          <input className="input mb-2 text-xs" placeholder="Biofluids (e.g. plasma,CSF)" value={query.biofluids} onChange={(e) => setQuery({ ...query, biofluids: e.target.value })} />
          <input className="input mb-2 text-xs" placeholder="Diagnosis (AD/MCI/CN)" value={query.diagnosis} onChange={(e) => setQuery({ ...query, diagnosis: e.target.value })} />
          <button className="btn-primary w-full" onClick={runQuery} disabled={busy}>Run query</button>
          {qResult && (
            <div className="mt-3 rounded-lg bg-ink-900/60 p-3 text-xs">
              <div className="flex justify-between"><span className="text-slate-500">Samples</span><span className="font-mono text-teal-300">{qResult.n_samples.toLocaleString()}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Datasets</span><span className="font-mono">{qResult.n_datasets}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Query time</span><span className="font-mono">{qResult.query_time_ms} ms</span></div>
            </div>
          )}
          <div className="mt-3 grid grid-cols-2 gap-2">
            <button className="btn-ghost px-2 py-1.5 text-xs" onClick={() => runPipeline("synthetic")} disabled={busy}>▶ Synthetic (ground truth)</button>
            <button className="btn-ghost px-2 py-1.5 text-xs" onClick={() => runPipeline("catalog")} disabled={busy}>▶ Catalog subset</button>
          </div>
        </Card>
      </div>

      {pipe && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Layers" value={pipe.summary?.n_layers} accent="text-cyan-300" />
            <StatCard label="Causal edges" value={pipe.summary?.causal_edges_n} accent="text-teal-300" />
            <StatCard label="Meta sig. features" value={meta.n_significant} accent="text-emerald-300" />
            <StatCard label="Ancestry-specific" value={meta.n_ancestry_specific} accent="text-amber-300" />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <h3 className="mb-2 font-bold text-slate-100">Causal graph (NOTEARS DAG · h={pipe.causal?.notears?.h ? pipe.causal.notears.h.toFixed(4) : "—"})</h3>
              {causalEdges.length ? (
                <>
                  <NetworkGraph nodes={causalNodes} edges={causalEdges.map(([s, t]: [string, string]) => ({ source: s, target: t }))} height={380} />
                  <div className="mt-2 text-[11px] text-slate-500">
                    Green-highlighted = recovered ground-truth edges (synthetic mode):{" "}
                    {causalEdges.filter(([s, t]: [string, string]) => gtSet.has(`${s.split(":")[1]}|${t.split(":")[1]}`)).length}/{gtEdges.length} of {gtEdges.length}
                  </div>
                </>
              ) : <EmptyState icon="🕸" title="No edges" hint="Run the pipeline." />}
            </Card>
            <Card>
              <h3 className="mb-2 font-bold text-slate-100">Meta-analysis: top features</h3>
              {meta.meta?.length ? (
                <PlotlyChart
                  data={[{
                    type: "bar", orientation: "h",
                    y: meta.meta.slice(0, 12).map((m: any) => m.feature),
                    x: meta.meta.slice(0, 12).map((m: any) => -Math.log10(Math.max(m.pvalue, 1e-300))),
                    marker: { color: meta.meta.slice(0, 12).map((m: any) => (m.ancestry_specific ? "#fbbf24" : "#14b8a6")) },
                  }]}
                  layout={{ xaxis: { title: "−log₁₀(p)" }, yaxis: { autorange: "reversed" } }}
                  title="Trans-ethnic meta (amber = ancestry-specific)"
                  height={380}
                />
              ) : <EmptyState icon="📊" title="No meta results" />}
            </Card>
          </div>

          {pipe.subtypes?.labels && (
            <Card>
              <h3 className="mb-2 font-bold text-slate-100">Multi-omics subtypes (silhouette {pipe.subtypes.silhouette?.toFixed(3)})</h3>
              <div className="flex flex-wrap gap-2">
                {Object.entries(pipe.subtypes.labels as Record<string, string>).slice(0, 40).map(([s, st]) => (
                  <span key={s} className={`badge-${st === "ST1" ? "rose" : st === "ST2" ? "cyan" : "emerald"} font-mono text-[10px]`}>{s} → {st}</span>
                ))}
                <span className="text-xs text-slate-500">… (all samples)</span>
              </div>
              {pipe.subtypes.outcome?.available && (
                <p className="mt-2 text-xs text-slate-400">
                  Subtype association with rate of decline: F={pipe.subtypes.outcome.f.toFixed(2)}, p={pipe.subtypes.outcome.pvalue.toExponential(2)}
                </p>
              )}
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
