import { useState, type FormEvent } from "react";
import { api, authStore } from "../api/client";
import { useAuth } from "../store/AuthContext";
import { Badge, Card, ErrorBanner, Spinner } from "../components/ui/ui";

export default function AccountPage() {
  const { user, refreshUser } = useAuth();
  const [form, setForm] = useState({ full_name: user?.full_name || "", organization: user?.organization || "" });
  const [pw, setPw] = useState({ old_password: "", new_password: "", confirm: "" });
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");
  const [pwMsg, setPwMsg] = useState("");
  const [pwError, setPwError] = useState("");

  if (!user) return <Spinner />;

  const saveProfile = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    setMsg("");
    try {
      const updated = await api.updateMe({ full_name: form.full_name, organization: form.organization });
      await refreshUser();
      setForm({ full_name: updated.full_name, organization: updated.organization });
      setMsg("Profile updated ✓");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setPwError("");
    setPwMsg("");
    if (pw.new_password.length < 8) {
      setPwError("New password must be at least 8 characters.");
      setSaving(false);
      return;
    }
    if (pw.new_password !== pw.confirm) {
      setPwError("New passwords do not match.");
      setSaving(false);
      return;
    }
    try {
      await api.changePassword({ old_password: pw.old_password, new_password: pw.new_password });
      setPw({ old_password: "", new_password: "", confirm: "" });
      setPwMsg("Password changed ✓");
    } catch (err: any) {
      setPwError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <h1 className="text-2xl font-extrabold text-white">Account settings</h1>
        <p className="text-sm text-slate-400">Manage your profile and password.</p>
      </header>

      <Card>
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-ink-700 text-lg font-bold text-teal-300">
            {user.full_name?.[0]?.toUpperCase() || "?"}
          </div>
          <div>
            <div className="font-bold text-slate-100">{user.full_name}</div>
            <div className="text-sm text-slate-500">{user.email}</div>
            <div className="mt-1">
              <Badge tone={user.role === "admin" ? "rose" : user.role === "reviewer" ? "amber" : "teal"}>{user.role}</Badge>
            </div>
          </div>
        </div>
        <dl className="grid grid-cols-2 gap-3 rounded-lg bg-ink-900/50 p-4 text-sm">
          <div><dt className="text-slate-500">Email</dt><dd className="font-medium text-slate-200">{user.email}</dd></div>
          <div><dt className="text-slate-500">Role</dt><dd className="font-medium text-slate-200 capitalize">{user.role}</dd></div>
          <div><dt className="text-slate-500">Organization</dt><dd className="font-medium text-slate-200">{user.organization || "—"}</dd></div>
          <div><dt className="text-slate-500">Member since</dt><dd className="font-medium text-slate-200">{user.created_at ? new Date(user.created_at).toLocaleDateString() : "—"}</dd></div>
        </dl>
      </Card>

      <Card>
        <h2 className="mb-3 font-bold text-slate-100">Edit profile</h2>
        {error && <ErrorBanner error={error} />}
        {msg && <div className="mb-3 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">{msg}</div>}
        <form onSubmit={saveProfile} className="space-y-3">
          <div>
            <label className="label">Full name</label>
            <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
          </div>
          <div>
            <label className="label">Organization</label>
            <input className="input" value={form.organization} onChange={(e) => setForm({ ...form, organization: e.target.value })} />
          </div>
          <button className="btn-primary" disabled={saving}>{saving ? "Saving…" : "Save changes"}</button>
        </form>
      </Card>

      <Card>
        <h2 className="mb-3 font-bold text-slate-100">Change password</h2>
        {pwError && <ErrorBanner error={pwError} />}
        {pwMsg && <div className="mb-3 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-300">{pwMsg}</div>}
        <form onSubmit={changePassword} className="space-y-3">
          <div>
            <label className="label">Current password</label>
            <input className="input" type="password" value={pw.old_password} onChange={(e) => setPw({ ...pw, old_password: e.target.value })} required />
          </div>
          <div>
            <label className="label">New password (min 8 chars)</label>
            <input className="input" type="password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} required />
          </div>
          <div>
            <label className="label">Confirm new password</label>
            <input className="input" type="password" value={pw.confirm} onChange={(e) => setPw({ ...pw, confirm: e.target.value })} required />
          </div>
          <button className="btn-primary" disabled={saving}>{saving ? "Updating…" : "Update password"}</button>
        </form>
      </Card>

      <Card className="text-sm text-slate-400">
        <h2 className="mb-2 font-bold text-slate-100">Session</h2>
        <div className="flex items-center justify-between">
          <span>Signed in as <span className="text-slate-200">{user.email}</span></span>
          <button
            className="btn-danger px-3 py-1.5 text-xs"
            onClick={() => {
              authStore.clear();
              window.location.hash = "#/login";
            }}
          >
            Sign out
          </button>
        </div>
      </Card>
    </div>
  );
}
