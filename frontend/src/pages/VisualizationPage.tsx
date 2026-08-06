import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type Analysis, type Dataset } from "../api/client";
import { Card, EmptyState, ErrorBanner, Spinner } from "../components/ui/ui";
import PlotlyChart from "../components/charts/PlotlyChart";
import NetworkGraph from "../components/charts/NetworkGraph";
import SankeyChart from "../components/charts/SankeyChart";

const PRESET_GENES = ["APP", "BACE1", "PSEN1", "APOE", "TREM2", "TYROBP", "IL1B", "TNF", "IL6", "MAPT", "GSK3B", "CLU", "SORL1", "PICALM", "MTOR", "BECN1", "HMOX1", "NFE2L2", "GFAP", "CSF1R"];

export default function VisualizationPage() {
  const { id } = useParams<{ id: string }>();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [geneList, setGeneList] = useState(PRESET_GENES.join(", "));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [volcano, setVolcano] = useState<any>(null);
  const [network, setNetwork] = useState<any>(null);
  const [sankey, setSankey] = useState<any>(null);

  useEffect(() => {
    if (!id) return;
    api.datasets(id).then(setDatasets);
    api.analyses(id).then(setAnalyses);
  }, [id]);

  const runDE = async () => {
    const ds = datasets[0];
    if (!ds) {
      setError("No datasets in this project — upload data first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await api.differentialExpression({ dataset_id: ds.id, case_group: "AD", control_group: "CN" });
      setVolcano(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const runNetwork = async () => {
    setLoading(true);
    setError("");
    try {
      const genes = geneList.split(",").map((g) => g.trim().toUpperCase()).filter(Boolean);
      const res = await api.network({ gene_list: genes });
      setNetwork(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const runSankey = async () => {
    setLoading(true);
    setError("");
    try {
      const genes = geneList.split(",").map((g) => g.trim().toUpperCase()).filter(Boolean);
      const res = await api.drugTargetMap({ gene_list: genes });
      setSankey(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-extrabold text-white">Visualization studio</h1>
        <p className="text-sm text-slate-400">Interactive volcano plots, PPI networks and drug-target flows (300–600 dpi static exports available in Reports).</p>
      </header>

      {error && <ErrorBanner error={error} />}
      {loading && <Spinner label="Computing…" />}

      <Card>
        <h2 className="mb-3 font-bold text-slate-100">Gene set</h2>
        <div className="flex flex-col gap-3 md:flex-row">
          <input className="input font-mono text-xs" value={geneList} onChange={(e) => setGeneList(e.target.value)} />
          <div className="flex flex-wrap gap-2">
            <button className="btn-primary" onClick={runNetwork} disabled={loading}>🕸 Network</button>
            <button className="btn-ghost" onClick={runSankey} disabled={loading}>💊 Drug map</button>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {PRESET_GENES.slice(0, 12).map((g) => (
            <button key={g} className="badge-slate font-mono hover:bg-teal-500/20" onClick={() => setGeneList(g)}>{g}</button>
          ))}
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <div className="mb-2 flex items-center justify-between">
            <h3 className="font-bold text-slate-100">Volcano plot (DE)</h3>
            <button className="btn-ghost px-3 py-1 text-xs" onClick={runDE} disabled={loading}>
              {datasets.length ? "Run on first dataset" : "No dataset"}
            </button>
          </div>
          {volcano?.table ? (
            <PlotlyChart
              data={[
                {
                  type: "scattergl", mode: "markers",
                  x: volcano.table.map((r: any) => r.log2fc),
                  y: volcano.table.map((r: any) => -Math.log10(Math.max(r.pvalue, 1e-300))),
                  text: volcano.table.map((r: any) => r.gene),
                  marker: { color: volcano.table.map((r: any) => (r.sig ? (r.log2fc > 0 ? "#d62728" : "#1f77b4") : "#64748b")), size: 6 },
                },
              ]}
              layout={{ xaxis: { title: "log₂FC" }, yaxis: { title: "−log₁₀(p)" } }}
              title={`Volcano · ${volcano.summary?.significant || 0} significant`}
              height={360}
            />
          ) : (
            <EmptyState icon="🌋" title="No volcano yet" hint="Click 'Run on first dataset'." />
          )}
        </Card>

        <Card>
          <h3 className="mb-2 font-bold text-slate-100">PPI network</h3>
          {network?.metrics ? (
            <NetworkGraph
              nodes={network.metrics.map((m: any) => ({ id: m.node, hub: m.hub, module: m.module }))}
              edges={(network.metrics || []).flatMap((m: any, i: number) =>
                network.metrics.slice(i + 1).filter((o: any) => o.node && m.node).map((o: any) => ({ source: m.node, target: o.node, weight: 0.5 }))
              ).slice(0, 400)}
              height={380}
            />
          ) : (
            <EmptyState icon="🕸" title="No network yet" hint="Enter a gene set and click Network." />
          )}
        </Card>
      </div>

      <Card>
        <h3 className="mb-2 font-bold text-slate-100">Drug–target interaction map</h3>
        {sankey?.sankey ? (
          <SankeyChart sankey={sankey.sankey} title={`${sankey.n_drugs} drugs targeting the gene set`} />
        ) : (
          <EmptyState icon="💊" title="No drug map yet" hint="Click 'Drug map' to build the Sankey flow." />
        )}
      </Card>

      {analyses.length > 0 && (
        <Card>
          <h3 className="mb-2 font-bold text-slate-100">Completed analyses with figures</h3>
          <div className="flex flex-wrap gap-2">
            {analyses.filter((a) => a.status === "completed").map((a) => (
              <a key={a.id} href={`/analyses/${a.id}`} className="badge-teal">{a.name}</a>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}
