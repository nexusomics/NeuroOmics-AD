import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, type Dataset, type MLResult } from "../api/client";
import { Badge, Card, EmptyState, ErrorBanner, Spinner } from "../components/ui/ui";
import PlotlyChart from "../components/charts/PlotlyChart";

const ALGO_META: Record<string, { label: string; desc: string }> = {
  random_forest: { label: "Random Forest", desc: "Ensemble of decision trees; robust to interactions & noise." },
  xgboost: { label: "XGBoost", desc: "Gradient-boosted trees; strong tabular benchmark performance." },
  svm: { label: "SVM (RBF)", desc: "Support vector machine; effective in small-sample settings." },
  dnn: { label: "Deep NN", desc: "Multi-layer perceptron with dropout; captures non-linearities." },
  gnn: { label: "GNN (GCN)", desc: "Graph convolutional network for gene prioritization over the PPI graph." },
};

export default function MLPage() {
  const { id } = useParams<{ id: string }>();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [algorithms, setAlgorithms] = useState<string[]>(["random_forest", "xgboost", "svm", "dnn", "gnn"]);
  const [result, setResult] = useState<{ results: MLResult[]; best_model?: string; classes?: string[] } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    api.datasets(id).then((ds) => {
      setDatasets(ds);
      setSelected(ds[0]?.id || "");
    });
  }, [id]);

  const train = async () => {
    if (!selected) {
      setError("Select a dataset with a 'group' column in metadata first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = (await api.trainML({
        dataset_id: selected, label_column: "group", algorithms, cv_folds: 3, top_features: 100, gnn: true,
      })) as any;
      setResult(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-extrabold text-white">Machine learning</h1>
        <p className="text-sm text-slate-400">Biomarker discovery & disease-stage classification — Random Forest, XGBoost, SVM, DNN, GNN.</p>
      </header>

      {error && <ErrorBanner error={error} />}

      <Card>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="label">Dataset</label>
            <select className="input" value={selected} onChange={(e) => setSelected(e.target.value)}>
              {datasets.map((d) => (
                <option key={d.id} value={d.id}>{d.name} ({d.omics_type})</option>
              ))}
            </select>
          </div>
          <div className="md:col-span-2">
            <label className="label">Algorithms</label>
            <div className="flex flex-wrap gap-2">
              {Object.keys(ALGO_META).map((a) => (
                <button
                  key={a}
                  onClick={() =>
                    setAlgorithms((prev) => (prev.includes(a) ? prev.filter((x) => x !== a) : [...prev, a]))
                  }
                  className={`rounded-lg border px-3 py-1.5 text-xs font-semibold transition ${
                    algorithms.includes(a)
                      ? "border-teal-500/60 bg-teal-500/15 text-teal-300"
                      : "border-ink-600 bg-ink-900/50 text-slate-400"
                  }`}
                >
                  {ALGO_META[a].label}
                </button>
              ))}
            </div>
          </div>
        </div>
        <button className="btn-primary mt-4" onClick={train} disabled={loading}>
          {loading ? "Training…" : "▶ Train models"}
        </button>
      </Card>

      {loading && <Spinner label="Training models (RF, XGB, SVM, DNN, GNN)…" />}

      {result && !loading && (
        <div className="space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            {result.results.map((m) => (
              <Card key={m.key} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-slate-100">{ALGO_META[m.algorithm]?.label || m.algorithm}</span>
                  {result.best_model === m.key && <Badge tone="teal">best</Badge>}
                </div>
                <div className="text-2xl font-extrabold text-teal-300">{(m.metrics.roc_auc || 0).toFixed(3)}</div>
                <div className="text-xs text-slate-500">ROC-AUC</div>
                <div className="text-xs text-slate-400">
                  acc {(m.metrics.accuracy || 0).toFixed(3)} · F1 {(m.metrics.macro_f1 || 0).toFixed(3)}
                </div>
                {m.note && <div className="text-[10px] text-slate-500">{m.note}</div>}
              </Card>
            ))}
          </div>

          <Card>
            <h3 className="mb-2 font-bold text-slate-100">Model comparison</h3>
            <PlotlyChart
              data={[
                {
                  type: "bar",
                  x: result.results.map((m) => ALGO_META[m.algorithm]?.label || m.algorithm),
                  y: result.results.map((m) => m.metrics.roc_auc || 0),
                  marker: { color: result.results.map((_, i) => `hsl(${160 + i * 28}, 65%, 55%)`) },
                  text: result.results.map((m) => (m.metrics.roc_auc || 0).toFixed(3)),
                  textposition: "outside",
                },
              ]}
              layout={{ yaxis: { title: "ROC-AUC", range: [0, 1.05] } }}
              title="Classifier performance (test set)"
            />
          </Card>

          {result.results[0]?.feature_importance?.length > 0 && (
            <Card>
              <h3 className="mb-2 font-bold text-slate-100">Top biomarkers (permutation importance)</h3>
              <PlotlyChart
                data={[
                  {
                    type: "bar", orientation: "h",
                    y: result.results[0].feature_importance.slice(0, 20).map((f) => f.feature).reverse(),
                    x: result.results[0].feature_importance.slice(0, 20).map((f) => f.importance).reverse(),
                    marker: { color: "#2dd4bf" },
                  },
                ]}
                layout={{ xaxis: { title: "importance" } }}
                title={`${ALGO_META[result.results[0].algorithm]?.label || result.results[0].algorithm} feature importance`}
              />
            </Card>
          )}

          {result.results.find((m) => m.algorithm === "gnn") && (
            <Card>
              <h3 className="mb-2 font-bold text-slate-100">GNN-prioritized genes</h3>
              <div className="flex flex-wrap gap-2">
                {(result.results.find((m) => m.algorithm === "gnn")?.top_prioritized_genes || []).map((g) => (
                  <span key={g} className="badge-rose font-mono">{g}</span>
                ))}
              </div>
            </Card>
          )}
        </div>
      )}

      {!result && !loading && (
        <EmptyState icon="🤖" title="No trained models yet" hint="Select a dataset (needs 'group' labels in metadata) and train." />
      )}
    </div>
  );
}
