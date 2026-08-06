import { useEffect, useState } from "react";
import { api, type User } from "../api/client";
import { Badge, Card, Spinner, StatCard } from "../components/ui/ui";

export default function AdminPage() {
  const [users, setUsers] = useState<User[] | null>(null);
  const [stats, setStats] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    api.adminUsers().then(setUsers);
    api.adminStats().then(setStats);
  }, []);

  if (!users || !stats) return <Spinner />;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-extrabold text-white">Administration</h1>
        <p className="text-sm text-slate-400">Platform users, roles, and system statistics.</p>
      </header>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard label="Users" value={stats.users as number} accent="text-teal-300" />
        <StatCard label="Projects" value={stats.projects as number} accent="text-cyan-300" />
        <StatCard label="Datasets" value={stats.datasets as number} accent="text-emerald-300" />
        <StatCard label="Analyses" value={stats.analyses as number} accent="text-amber-300" />
      </div>

      <Card>
        <h2 className="mb-3 font-bold text-slate-100">Users</h2>
        <table className="table-data">
          <thead>
            <tr><th>Name</th><th>Email</th><th>Role</th><th>Organization</th><th>Verified</th></tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td className="font-medium text-slate-200">{u.full_name}</td>
                <td>{u.email}</td>
                <td><Badge tone={u.role === "admin" ? "rose" : u.role === "reviewer" ? "amber" : "teal"}>{u.role}</Badge></td>
                <td className="text-xs">{u.organization}</td>
                <td>{u.is_verified ? "✓" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
