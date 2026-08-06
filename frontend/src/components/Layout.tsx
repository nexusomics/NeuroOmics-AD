import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../store/AuthContext";

const NAV = [
  { to: "/", label: "Dashboard", icon: "◈", end: true },
  { to: "/projects", label: "Projects", icon: "▤" },
];

const OMICS_TOOLS = [
  { to: "/upload", label: "Data Upload" },
  { to: "/analyses", label: "Analyses" },
  { to: "/visualization", label: "Visualization" },
  { to: "/ml", label: "ML Models" },
  { to: "/drugs", label: "Drug Repurposing" },
  { to: "/reports", label: "Reports" },
  { to: "/assistant", label: "AI Assistant" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const projectId = location.pathname.split("/")[2] || "";

  const toolLinks = OMICS_TOOLS.map((t) => ({
    ...t,
    to: projectId ? `/projects/${projectId}${t.to}` : `/projects${t.to}`,
  }));

  return (
    <div className="flex min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-30 flex w-60 flex-col border-r border-ink-700/60 bg-ink-900/80">
        <div className="flex items-center gap-2 border-b border-ink-700/60 px-4 py-4">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-cyan-500 text-lg font-black text-ink-950">
            🧠
          </div>
          <div>
            <div className="text-sm font-bold text-white">NeuroOmics-AD</div>
            <div className="text-[10px] uppercase tracking-widest text-teal-400">multi-omics · AI · drug repurposing</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive ? "bg-teal-500/15 text-teal-300" : "text-slate-400 hover:bg-ink-700/40 hover:text-slate-200"
                }`
              }
            >
              <span className="w-4">{n.icon}</span> {n.label}
            </NavLink>
          ))}
          {projectId && (
            <div className="pt-3">
              <div className="px-3 pb-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">Project tools</div>
              {toolLinks.map((t) => (
                <NavLink
                  key={t.to}
                  to={t.to}
                  className={({ isActive }) =>
                    `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition ${
                      isActive ? "bg-cyan-500/10 text-cyan-300" : "text-slate-400 hover:bg-ink-700/40 hover:text-slate-200"
                    }`
                  }
                >
                  {t.label}
                </NavLink>
              ))}
            </div>
          )}
          {user?.role === "admin" && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition ${
                  isActive ? "bg-teal-500/15 text-teal-300" : "text-slate-400 hover:bg-ink-700/40 hover:text-slate-200"
                }`
              }
            >
              <span className="w-4">⚙</span> Administration
            </NavLink>
          )}
        </nav>
        <div className="border-t border-ink-700/60 p-3">
          <div className="mb-2 flex items-center gap-2 px-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-ink-700 text-xs font-bold text-teal-300">
              {user?.full_name?.[0]?.toUpperCase() || "?"}
            </div>
            <div className="min-w-0">
              <div className="truncate text-xs font-semibold text-slate-200">{user?.full_name}</div>
              <div className="truncate text-[10px] text-slate-500">{user?.email}</div>
            </div>
          </div>
          <button
            className="w-full rounded-lg border border-ink-600 px-3 py-1.5 text-xs font-semibold text-slate-400 hover:bg-ink-700/50"
            onClick={() => {
              logout();
              navigate("/login");
            }}
          >
            Sign out
          </button>
        </div>
      </aside>
      <main className="ml-60 flex-1 px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
