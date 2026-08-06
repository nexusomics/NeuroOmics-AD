import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, type Project } from "../api/client";
import { Badge, Card, EmptyState, ErrorBanner, Spinner } from "../components/ui/ui";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", disease: "Alzheimer's disease" });
  const [error, setError] = useState("");

  const load = () => api.projects().then(setProjects);

  useEffect(() => {
    load();
  }, []);

  const create = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api.createProject(form);
      setShowCreate(false);
      setForm({ name: "", description: "", disease: "Alzheimer's disease" });
      load();
    } catch (err: any) {
      setError(err.message);
    }
  };

  if (!projects) return <Spinner />;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-extrabold text-white">Projects</h1>
          <p className="text-sm text-slate-400">Organize datasets, analyses, and drug candidates per study.</p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(!showCreate)}>
          + New project
        </button>
      </header>

      {error && <ErrorBanner error={error} />}

      {showCreate && (
        <Card>
          <form onSubmit={create} className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="label">Project name *</label>
              <input className="input" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required />
            </div>
            <div>
              <label className="label">Disease model</label>
              <select className="input" value={form.disease} onChange={(e) => setForm({ ...form, disease: e.target.value })}>
                {["Alzheimer's disease", "Parkinson's disease", "ALS", "Huntington's disease", "Cancer"].map((d) => (
                  <option key={d}>{d}</option>
                ))}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="label">Description</label>
              <textarea className="input" rows={2} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            </div>
            <div className="md:col-span-2 flex gap-2">
              <button className="btn-primary" type="submit">Create</button>
              <button className="btn-ghost" type="button" onClick={() => setShowCreate(false)}>Cancel</button>
            </div>
          </form>
        </Card>
      )}

      {projects.length === 0 ? (
        <EmptyState icon="▤" title="No projects yet" hint="Create a project to begin — upload omics data, run analyses, and screen drugs." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {projects.map((p) => (
            <Card key={p.id} className="flex flex-col gap-3 transition hover:border-teal-500/40">
              <div className="flex items-start justify-between">
                <div className="font-bold text-slate-100">{p.name}</div>
                <Badge tone={p.status === "active" ? "teal" : "slate"}>{p.status}</Badge>
              </div>
              <p className="line-clamp-2 min-h-[2.5rem] text-sm text-slate-400">{p.description || "No description"}</p>
              <div className="flex items-center justify-between text-xs text-slate-500">
                <span>{p.disease}</span>
                <span>{p.created_at ? new Date(p.created_at).toLocaleDateString() : ""}</span>
              </div>
              <Link to={`/projects/${p.id}`} className="btn-ghost w-full text-center">
                Open project →
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
