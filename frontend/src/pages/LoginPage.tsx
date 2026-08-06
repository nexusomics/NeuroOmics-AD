import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../store/AuthContext";
import { ErrorBanner } from "../components/ui/ui";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("demo@neuroomics.org");
  const [password, setPassword] = useState("demo12345");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      navigate("/");
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-500 to-cyan-500 text-3xl shadow-glow">🧠</div>
          <h1 className="text-2xl font-extrabold text-white">NeuroOmics-AD</h1>
          <p className="mt-1 text-sm text-slate-400">Multi-omics analysis & AI-driven drug repurposing for Alzheimer's disease</p>
        </div>
        <form onSubmit={submit} className="card space-y-4 p-6">
          <h2 className="text-lg font-bold text-slate-100">Sign in</h2>
          {error && <ErrorBanner error={error} />}
          <div>
            <label className="label">Email</label>
            <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="label">Password</label>
            <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button className="btn-primary w-full" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <div className="text-center text-xs text-slate-500">
            Demo credentials pre-filled ·{" "}
            <Link className="text-teal-400 hover:underline" to="/register">
              Create an account
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
