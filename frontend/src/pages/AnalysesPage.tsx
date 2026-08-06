import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Analysis, type Dataset } from "../api/client";
import { Badge, Card, EmptyState, ErrorBanner, Spinner } from "../components/ui/ui";

const ANALYSIS_TYPES: Record<string, { label: string; desc: string }> = {
  differential_expression: { label: "🔬 Differential expression", desc: "Case vs control (limma/DESeq2-style)" },
  preprocessing: { label: "🛠 Data harmonization & QC", desc: "Normalize, batch-correct, impute, remove outliers" },
  meta_analysis: { label: "🧮 Cross-cohort meta-analysis", desc: "Combine ≥2 cohorts (fixed/random effects)" },
  deconvolution: { label: "🧫 Cell-type deconvolution", desc: "CIBERSORT-style fractions from bulk data" },
  enrichment: { label: "🧬 Pathway enrichment", desc: "GO / KEGG / Reactome hypergeometric enrichment" },
  network: { label: "🕸 PPI network & hub genes", desc: "Network construction, centrality, modules" },
  integration: { label: "🧩 Multi-omics integration", desc: "Fusion of multiple omics datasets" },
  ml: { label: "🤖 Machine learning", desc: "RF / XGBoost / SVM / DNN / GNN training" },
  single_cell: { label: "🔬 Single-cell analysis", desc: "QC, clustering, UMAP, markers" },
  genomics: { label: "🧩 GWAS / genomics", desc: "Summary-stat QC, λ, significant loci" },
  epigenomics: { label: "🧫 Epigenomics", desc: "Differential methylation (DMPs)" },
  clinical: { label: "🩺 Clinical analysis", desc: "Survival, stratification, subgroup tests" },
  drug_repurposing: { label: "💊 Drug repurposing", desc: "Full repurposing pipeline" },
};

export default function AnalysesPage() {
  const { id } = useParams<{ id: string }>();
  const [analyses, setAnalyses] = useState<Analysis[] | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [form, setForm] = useState({ name: "", analysis_type: "differential_expression", dataset_id: "", case_group: "AD", control_group: "CN" });
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);

  const load = () => {
    if (!id) return;
    api.analyses(id).then(setAnalyses);
    api.datasets(id).then(setDatasets);
  };
  useEffect(load, [id]);

  const create = async () => {
    if (!id) return;
    setCreating(true);
    setError("");
    const config: Record<string, unknown> = { case_group: form.case_group, control_group: form.control_group };
    if (form.dataset_id) config.dataset_id = form.dataset_id;
    if (form.analysis_type === "meta_analysis") {
      config.dataset_ids = datasets.slice(0, 3).map((d) => d.id);
    }
    if (form.analysis_type === "enrichment" || form.analysis_type === "network") {
      config.gene_list = ["APP", "BACE1", "APOE", "TREM2", "TYROBP", "IL1B", "TNF", "IL6", "MAPT", "GSK3B", "MTOR", "BECN1", "HMOX1", "CLU", "SORL1"];
    }
    if (form.analysis_type === "ml") {
      config.label_column = "group";
      config.algorithms = ["random_forest", "xgboost", "svm", "dnn", "gnn"];
      config.cv_folds = 3;
    }
    try {
      await api.createAnalysis(id, { name: form.name || ANALYSIS_TYPES[form.analysis_type].label, analysis_type: form.analysis_type, config });
      setForm({ ...form, name: "" });
      load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  if (!analyses) return <Spinner />;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-extrabold text-white">Analyses</h1>
        <p className="text-sm text-slate-400">Create reproducible analysis runs — executed on Celery workers with progress tracking.</p>
      </header>

      {error && <ErrorBanner error={error} />}

      <Card>
        <h2 className="mb-3 font-bold text-slate-100">New analysis</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="label">Analysis type</label>
            <select className="input" value={form.analysis_type} onChange={(e) => setForm({ ...form, analysis_type: e.target.value })}>
              {Object.entries(ANALYSIS_TYPES).map(([k, v]) => (
                <option key={k} value={k}>{v.label}</option>
              ))}
            </select>
            <p className="mt-1 text-xs text-slate-500">{ANALYSIS_TYPES[form.analysis_type]?.desc}</p>
          </div>
          <div>
            <label className="label">Name (optional)</label>
            <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Auto-generated" />
          </div>
          <div>
            <label className="label">Dataset</label>
            <select className="input" value={form.dataset_id} onChange={(e) => setForm({ ...form, dataset_id: e.target.value })}>
              <option value="">— none —</option>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.omics_type})</option>
              ))}
            </select>
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <button className="btn-primary" onClick={create} disabled={creating}>
            {creating ? "Launching…" : "▶ Launch analysis"}
          </button>
        </div>
      </Card>

      {analyses.length === 0 ? (
        <EmptyState icon="🔬" title="No analyses yet" hint="Launch your first analysis above." />
      ) : (
        <Card>
          <table className="table-data">
            <thead>
              <tr><th>Name</th><th>Type</th><th>Status</th><th>Progress</th><th>Created</th></tr>
            </thead>
            <tbody>
              {analyses.map((a) => (
                <tr key={a.id}>
                  <td className="font-medium text-slate-200"><Link className="hover:text-teal-300" to={`/analyses/${a.id}`}>{a.name}</Link></td>
                  <td>{ANALYSIS_TYPES[a.analysis_type]?.label || a.analysis_type}</td>
                  <td><Badge tone={a.status === "completed" ? "emerald" : a.status === "failed" ? "rose" : "amber"}>{a.status}</Badge></td>
                  <td>{a.progress}%</td>
                  <td className="text-xs text-slate-500">{a.created_at ? new Date(a.created_at).toLocaleString() : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
