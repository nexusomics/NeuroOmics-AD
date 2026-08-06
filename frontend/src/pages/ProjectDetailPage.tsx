import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type Analysis, type Dataset, type DrugCandidate } from "../api/client";
import { Badge, Card, EmptyState, ErrorBanner, Spinner, StatCard } from "../components/ui/ui";

const OMICS_OPTIONS = [
  { value: "transcriptomics", label: "🧬 Transcriptomics (RNA-seq)" },
  { value: "proteomics", label: "🧪 Proteomics" },
  { value: "metabolomics", label: "⚗️ Metabolomics" },
  { value: "genomics", label: "🧩 Genomics / GWAS" },
  { value: "epigenomics", label: "🧫 Epigenomics (methylation)" },
  { value: "single_cell", label: "🔬 Single-cell RNA-seq" },
  { value: "clinical", label: "🩺 Clinical" },
];

export default function ProjectDetailPage({ initialTab = "overview" }: { initialTab?: string }) {
  const { id } = useParams<{ id: string }>();
  const [tab, setTab] = useState(initialTab);
  const [datasets, setDatasets] = useState<Dataset[] | null>(null);
  const [analyses, setAnalyses] = useState<Analysis[] | null>(null);
  const [candidates, setCandidates] = useState<DrugCandidate[] | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [uploadForm, setUploadForm] = useState({ name: "", omics_type: "transcriptomics" });

  const load = () => {
    if (!id) return;
    api.datasets(id).then(setDatasets);
    api.analyses(id).then(setAnalyses);
    api.drugCandidates(id).then(setCandidates).catch(() => setCandidates([]));
  };

  useEffect(load, [id]);
  useEffect(() => setTab(initialTab), [initialTab]);

  const upload = async (file: File | null) => {
    if (!id || !file) return;
    setUploading(true);
    setUploadError("");
    try {
      await api.uploadDataset(id, uploadForm, file);
      setUploadForm({ name: "", omics_type: "transcriptomics" });
      load();
    } catch (err: any) {
      setUploadError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const tabs = [
    { key: "overview", label: "Overview" },
    { key: "upload", label: "Data upload" },
    { key: "datasets", label: `Datasets (${datasets?.length ?? 0})` },
    { key: "analyses", label: `Analyses (${analyses?.length ?? 0})` },
    { key: "drugs", label: `Drugs (${candidates?.length ?? 0})` },
  ];

  return (
    <div className="space-y-6">
      <header>
        <div className="text-xs text-slate-500">
          <Link to="/projects" className="hover:text-teal-400">Projects</Link> / <span className="text-slate-400">Project</span>
        </div>
        <div className="mt-1 flex items-center gap-3">
          <h1 className="text-2xl font-extrabold text-white">{datasets ? "Project workspace" : "Project"}</h1>
          <Badge tone="teal">AD</Badge>
        </div>
      </header>

      <div className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
              tab === t.key ? "bg-teal-500 text-ink-950" : "border border-ink-700 bg-ink-800/60 text-slate-300 hover:bg-ink-700/60"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <StatCard label="Datasets" value={datasets?.length ?? 0} accent="text-cyan-300" />
            <StatCard label="Analyses" value={analyses?.length ?? 0} accent="text-emerald-300" />
            <StatCard label="Drug candidates" value={candidates?.length ?? 0} accent="text-amber-300" />
            <StatCard label="Status" value={<Badge tone="teal">active</Badge>} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <h2 className="mb-3 font-bold text-slate-100">Quick links</h2>
              {[
                { label: "🔬 Differential expression & omics analyses", to: `/projects/${id}/analyses` },
                { label: "📊 Interactive visualizations", to: `/projects/${id}/visualization` },
                { label: "🤖 Machine-learning models", to: `/projects/${id}/ml` },
                { label: "💊 Drug repurposing", to: `/projects/${id}/drugs` },
                { label: "📄 Reports (PDF/Word/PPTX/Excel/HTML)", to: `/projects/${id}/reports` },
                { label: "✨ AI research assistant", to: `/projects/${id}/assistant` },
              ].map((l) => (
                <Link key={l.label} to={l.to} className="block rounded-lg border border-ink-700/60 bg-ink-900/40 px-4 py-2.5 text-sm text-slate-300 transition hover:border-teal-500/50 hover:text-white">
                  {l.label}
                </Link>
              ))}
            </Card>
            <Card>
              <h2 className="mb-3 font-bold text-slate-100">Recent analyses</h2>
              {!analyses?.length ? (
                <p className="text-sm text-slate-500">No analyses yet — start with differential expression.</p>
              ) : (
                <div className="space-y-2">
                  {analyses.slice(0, 6).map((a) => (
                    <Link key={a.id} to={`/analyses/${a.id}`} className="flex items-center justify-between rounded-lg bg-ink-900/40 px-3 py-2 text-sm hover:bg-ink-700/40">
                      <span className="text-slate-300">{a.name}</span>
                      <Badge tone={a.status === "completed" ? "emerald" : a.status === "failed" ? "rose" : "amber"}>{a.status}</Badge>
                    </Link>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>
      )}

      {tab === "upload" && (
        <Card className="space-y-4">
          <h2 className="font-bold text-slate-100">Upload a multi-omics dataset</h2>
          {uploadError && <ErrorBanner error={uploadError} />}
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="label">Dataset name</label>
              <input className="input" value={uploadForm.name} onChange={(e) => setUploadForm({ ...uploadForm, name: e.target.value })} placeholder="e.g. ADNI bulk RNA-seq" />
            </div>
            <div>
              <label className="label">Omics type</label>
              <select className="input" value={uploadForm.omics_type} onChange={(e) => setUploadForm({ ...uploadForm, omics_type: e.target.value })}>
                {OMICS_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>
          <div>
            <label className="label">File (CSV/TSV — genes × samples, or samples × genes)</label>
            <input
              type="file"
              accept=".csv,.tsv,.txt,.gct"
              disabled={uploading}
              onChange={(e) => upload(e.target.files?.[0] || null)}
              className="block w-full cursor-pointer rounded-lg border border-dashed border-ink-600 bg-ink-900/50 p-4 text-sm text-slate-400 file:mr-3 file:rounded-md file:border-0 file:bg-teal-500/20 file:px-3 file:py-1.5 file:text-teal-300"
            />
            <p className="mt-1 text-xs text-slate-500">
              Row names = genes/features, columns = samples. Attach sample metadata (group AD/CN, batch, covariates) as a second file by naming it <code>metadata.csv</code> and uploading a "clinical" dataset.
            </p>
          </div>
          {uploading && <Spinner label="Uploading & parsing…" />}
        </Card>
      )}

      {tab === "datasets" && (
        <Card>
          {!datasets?.length ? (
            <EmptyState icon="▤" title="No datasets" hint="Upload data via the Data upload tab." />
          ) : (
            <table className="table-data">
              <thead>
                <tr><th>Name</th><th>Type</th><th>Platform</th><th>Samples</th><th>Features</th><th>Status</th></tr>
              </thead>
              <tbody>
                {datasets.map((d) => (
                  <tr key={d.id}>
                    <td className="font-medium text-slate-200">{d.name}</td>
                    <td><Badge tone="cyan">{d.omics_type}</Badge></td>
                    <td className="text-xs">{d.platform}</td>
                    <td>{d.n_samples}</td>
                    <td>{d.n_features}</td>
                    <td><Badge tone={d.status === "ready" ? "emerald" : "amber"}>{d.status}</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === "analyses" && (
        <Card>
          {!analyses?.length ? (
            <EmptyState icon="🔬" title="No analyses" hint="Create one from the Analyses page." />
          ) : (
            <table className="table-data">
              <thead>
                <tr><th>Name</th><th>Type</th><th>Status</th><th>Progress</th><th>Created</th></tr>
              </thead>
              <tbody>
                {analyses.map((a) => (
                  <tr key={a.id}>
                    <td className="font-medium text-slate-200"><Link className="hover:text-teal-300" to={`/analyses/${a.id}`}>{a.name}</Link></td>
                    <td>{a.analysis_type}</td>
                    <td><Badge tone={a.status === "completed" ? "emerald" : a.status === "failed" ? "rose" : "amber"}>{a.status}</Badge></td>
                    <td>{a.progress}%</td>
                    <td className="text-xs text-slate-500">{a.created_at ? new Date(a.created_at).toLocaleString() : ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {tab === "drugs" && (
        <Card>
          {!candidates?.length ? (
            <EmptyState icon="💊" title="No drug candidates" hint="Run the drug repurposing pipeline from the Drugs page." />
          ) : (
            <table className="table-data">
              <thead>
                <tr><th>#</th><th>Drug</th><th>Mechanism</th><th>Targets</th><th>FDA</th><th>Composite</th></tr>
              </thead>
              <tbody>
                {candidates.slice(0, 15).map((c) => (
                  <tr key={c.id}>
                    <td>{c.rank}</td>
                    <td className="font-medium text-slate-200">{c.drug_name}</td>
                    <td className="max-w-[260px] text-xs">{c.mechanism}</td>
                    <td className="text-xs">{c.targets.slice(0, 4).join(", ")}</td>
                    <td><Badge tone={c.fda_status === "Approved" ? "emerald" : "amber"}>{c.fda_status}</Badge></td>
                    <td className="font-mono">{c.composite_score.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}
    </div>
  );
}
