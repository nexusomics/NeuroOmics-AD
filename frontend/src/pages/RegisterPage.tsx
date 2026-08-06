import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../store/AuthContext";
import { ErrorBanner } from "../components/ui/ui";

export default function RegisterPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "", full_name: "", organization: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.register(form);
      await login(form.email, form.password);
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Registration failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-extrabold text-white">Create your account</h1>
          <p className="mt-1 text-sm text-slate-400">Start a secure research workspace</p>
        </div>
        <form onSubmit={submit} className="card space-y-4 p-6">
          {error && <ErrorBanner error={error} />}
          <div>
            <label className="label">Full name</label>
            <input className="input" value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} required />
          </div>
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required />
          </div>
          <div>
            <label className="label">Organization</label>
            <input className="input" value={form.organization} onChange={(e) => setForm({ ...form, organization: e.target.value })} />
          </div>
          <div>
            <label className="label">Password (min 8 chars)</label>
            <input className="input" type="password" minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          </div>
          <button className="btn-primary w-full" disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
          <div className="text-center text-xs text-slate-500">
            Already registered?{" "}
            <Link className="text-teal-400 hover:underline" to="/login">
              Sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
