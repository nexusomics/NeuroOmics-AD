import { useState } from "react";
import { useParams } from "react-router-dom";
import { api, type DrugCandidate, type Sankey } from "../api/client";
import { Badge, Card, EmptyState, ErrorBanner, Spinner } from "../components/ui/ui";
import SankeyChart from "../components/charts/SankeyChart";

const DEFAULT_GENES = "APP, BACE1, PSEN1, APOE, TREM2, TYROBP, IL1B, TNF, IL6, MAPT, GSK3B, CLU, SORL1, PICALM, MTOR, BECN1, HMOX1, NFE2L2";

const CRITERIA = [
  { key: "score_network", label: "Network proximity", tone: "teal" as const },
  { key: "score_pathway_reversal", label: "Pathway reversal", tone: "cyan" as const },
  { key: "score_target_overlap", label: "Target overlap", tone: "emerald" as const },
  { key: "score_bbb", label: "BBB", tone: "amber" as const },
  { key: "score_admet", label: "ADMET", tone: "slate" as const },
  { key: "score_clinical", label: "Clinical", tone: "rose" as const },
];

export default function DrugsPage() {
  const { id } = useParams<{ id: string }>();
  const [geneList, setGeneList] = useState(DEFAULT_GENES);
  const [candidates, setCandidates] = useState<any[] | null>(null);
  const [combinations, setCombinations] = useState<any[]>([]);
  const [sankey, setSankey] = useState<Sankey | null>(null);
  const [saved, setSaved] = useState<DrugCandidate[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const run = async () => {
    const genes = geneList.split(",").map((g) => g.trim().toUpperCase()).filter(Boolean);
    setLoading(true);
    setError("");
    try {
      const res = (await api.drugPipeline({ gene_list: genes, max_candidates: 15 })) as any;
      setCandidates(res.candidates);
      setCombinations(res.combinations || []);
      setSankey(res.sankey || null);
      if (id) {
        const savedRes = await api.saveDrugPipeline(id, { gene_list: genes, max_candidates: 15 });
        api.drugCandidates(id).then(setSaved);
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-extrabold text-white">AI drug repurposing</h1>
        <p className="text-sm text-slate-400">
          Ranking by network proximity · pathway reversal (CMap/LINCS) · target overlap · BBB · ADMET · clinical evidence — powered by DrugBank/ChEMBL/DGIdb/Open Targets knowledge.
        </p>
      </header>

      {error && <ErrorBanner error={error} />}

      <Card>
        <label className="label">Disease genes (prioritized targets)</label>
        <div className="flex flex-col gap-2 md:flex-row">
          <input className="input font-mono text-xs" value={geneList} onChange={(e) => setGeneList(e.target.value)} />
          <button className="btn-primary whitespace-nowrap" onClick={run} disabled={loading}>
            {loading ? "Screening…" : "▶ Run repurposing pipeline"}
          </button>
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Sources: curated DrugBank/ChEMBL/DGIdb/OpenTargets knowledge base + LINCS/CMap signature concepts (live API queries optional via <code>DRUG_ENABLE_LIVE_API=true</code>).
        </p>
      </Card>

      {loading && <Spinner label="Scoring candidates across six criteria…" />}

      {candidates && !loading && (
        <>
          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <Card>
                <h2 className="mb-3 font-bold text-slate-100">Ranked candidates</h2>
                <div className="space-y-2">
                  {candidates.map((c) => (
                    <div key={c.drug_name} className="rounded-lg border border-ink-700/60 bg-ink-900/40 p-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-500">#{c.rank}</span>
                            <span className="font-bold text-slate-100">{c.drug_name}</span>
                            <Badge tone={c.fda_status === "Approved" ? "emerald" : c.fda_status === "Investigational" ? "amber" : "slate"}>
                              {c.fda_status}
                            </Badge>
                          </div>
                          <div className="mt-1 text-xs text-slate-400">{c.mechanism}</div>
                          <div className="mt-1 text-[11px] text-slate-500">
                            Targets: {c.targets.join(", ")}
                          </div>
                          {c.evidence?.slice(0, 3).map((e: string, i: number) => (
                            <div key={i} className="mt-1 text-[11px] text-teal-300/80">✓ {e}</div>
                          ))}
                        </div>
                        <div className="shrink-0 text-right">
                          <div className="text-2xl font-extrabold text-teal-300">{c.composite_score.toFixed(3)}</div>
                          <div className="text-[10px] text-slate-500">composite</div>
                        </div>
                      </div>
                      <div className="mt-2 grid grid-cols-6 gap-1.5">
                        {CRITERIA.map((cr) => (
                          <div key={cr.key} className="rounded bg-ink-950/60 p-1.5 text-center">
                            <div className="text-[9px] uppercase text-slate-500">{cr.label}</div>
                            <div className="font-mono text-xs" style={{ color: ["#2dd4bf", "#22d3ee", "#34d399", "#fbbf24", "#94a3b8", "#fb7185"][CRITERIA.indexOf(cr)] }}>
                              {c[cr.key]?.toFixed(2)}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </Card>
            </div>

            <div className="space-y-4">
              <Card>
                <h2 className="mb-2 font-bold text-slate-100">Combination suggestions</h2>
                {combinations.length === 0 ? (
                  <p className="text-sm text-slate-500">No combinations inferred.</p>
                ) : (
                  <div className="space-y-2">
                    {combinations.map((cb, i) => (
                      <div key={i} className="rounded-lg bg-ink-900/50 p-2.5 text-xs">
                        <span className="font-semibold text-teal-300">{cb.drug_a}</span>
                        <span className="mx-1 text-slate-500">+</span>
                        <span className="font-semibold text-cyan-300">{cb.drug_b}</span>
                        <div className="mt-1 text-[11px] text-slate-500">{cb.rationale}</div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
              <Card>
                <h2 className="mb-2 font-bold text-slate-100">Weights</h2>
                {[
                  ["Network", 0.25], ["Pathway reversal", 0.20], ["Target overlap", 0.20],
                  ["BBB", 0.10], ["ADMET", 0.10], ["Clinical", 0.15],
                ].map(([l, w]) => (
                  <div key={String(l)} className="flex items-center justify-between py-1 text-xs">
                    <span className="text-slate-400">{l}</span>
                    <span className="font-mono text-slate-200">{w}</span>
                  </div>
                ))}
              </Card>
              {saved.length > 0 && (
                <Card>
                  <h2 className="mb-2 font-bold text-slate-100">Saved to project</h2>
                  <div className="text-xs text-slate-400">{saved.length} candidates persisted in the project's drug table.</div>
                </Card>
              )}
            </div>
          </div>

          <Card>
            <h2 className="mb-2 font-bold text-slate-100">Drug–target flow (Sankey)</h2>
            {sankey ? <SankeyChart sankey={sankey} title="Disease module → targets → candidate drugs" /> : <EmptyState icon="💊" title="No flow data" />}
          </Card>
        </>
      )}

      {!candidates && !loading && (
        <EmptyState icon="💊" title="Run the pipeline" hint="Enter disease genes and click 'Run repurposing pipeline' to rank ~60 curated AD-relevant drugs." />
      )}
    </div>
  );
}
