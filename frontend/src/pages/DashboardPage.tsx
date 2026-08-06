import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, type Project } from "../api/client";
import { Card, EmptyState, Spinner, StatCard } from "../components/ui/ui";
import { useAuth } from "../store/AuthContext";

export default function DashboardPage() {
  const { user } = useAuth();
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [summaries, setSummaries] = useState<Record<string, { datasets: number; analyses: number; drug_candidates: number }>>({});

  useEffect(() => {
    api.projects().then(async (ps) => {
      setProjects(ps);
      const acc: typeof summaries = {};
      await Promise.all(
        ps.map(async (p) => {
          try {
            acc[p.id] = await api.projectSummary(p.id);
          } catch {
            acc[p.id] = { datasets: 0, analyses: 0, drug_candidates: 0 };
          }
        })
      );
      setSummaries(acc);
    });
  }, []);

  if (!projects) return <Spinner label="Loading workspace…" />;

  const totals = projects.reduce(
    (a, p) => ({
      datasets: a.datasets + (summaries[p.id]?.datasets || 0),
      analyses: a.analyses + (summaries[p.id]?.analyses || 0),
      drugs: a.drugs + (summaries[p.id]?.drug_candidates || 0),
    }),
    { datasets: 0, analyses: 0, drugs: 0 }
  );

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-extrabold text-white">Welcome back, {user?.full_name?.split(" ")[0]} 👋</h1>
        <p className="text-sm text-slate-400">
          Integrated multi-omics analysis, AI models and drug repurposing for Alzheimer's disease research.
        </p>
      </header>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Projects" value={projects.length} accent="text-teal-300" />
        <StatCard label="Datasets" value={totals.datasets} accent="text-cyan-300" />
        <StatCard label="Analyses" value={totals.analyses} accent="text-emerald-300" />
        <StatCard label="Drug candidates" value={totals.drugs} accent="text-amber-300" />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-bold text-slate-100">Your projects</h2>
            <Link to="/projects" className="text-xs font-semibold text-teal-400 hover:underline">
              View all →
            </Link>
          </div>
          {projects.length === 0 ? (
            <EmptyState
              icon="▤"
              title="No projects yet"
              hint="Create a project to start uploading multi-omics datasets and running analyses."
            />
          ) : (
            <div className="space-y-2">
              {projects.slice(0, 6).map((p) => (
                <Link
                  key={p.id}
                  to={`/projects/${p.id}`}
                  className="flex items-center justify-between rounded-lg border border-ink-700/60 bg-ink-900/40 px-4 py-3 transition hover:border-teal-500/50"
                >
                  <div>
                    <div className="font-semibold text-slate-100">{p.name}</div>
                    <div className="text-xs text-slate-500">{p.disease}</div>
                  </div>
                  <div className="flex gap-3 text-xs text-slate-400">
                    <span>{summaries[p.id]?.datasets || 0} datasets</span>
                    <span>{summaries[p.id]?.analyses || 0} analyses</span>
                    <span>{summaries[p.id]?.drug_candidates || 0} drugs</span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </Card>
        <Card>
          <h2 className="mb-3 font-bold text-slate-100">Quick actions</h2>
          <div className="space-y-2">
            {[
              { label: "⬆ Upload multi-omics data", to: projects[0] ? `/projects/${projects[0].id}/upload` : "/projects" },
              { label: "🔬 Run differential expression", to: projects[0] ? `/projects/${projects[0].id}/analyses` : "/projects" },
              { label: "💊 Drug repurposing pipeline", to: projects[0] ? `/projects/${projects[0].id}/drugs` : "/projects" },
              { label: "🤖 Ask the AI assistant", to: projects[0] ? `/projects/${projects[0].id}/assistant` : "/projects" },
              { label: "📄 Generate reports", to: projects[0] ? `/projects/${projects[0].id}/reports` : "/projects" },
            ].map((a) => (
              <Link key={a.label} to={a.to} className="block rounded-lg border border-ink-700/60 bg-ink-900/40 px-4 py-2.5 text-sm text-slate-300 transition hover:border-teal-500/50 hover:text-white">
                {a.label}
              </Link>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
