import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

// Mirrors the backend policy (schemas/auth.py): min 10 + lower/upper/digit/symbol.
const RULES: { label: string; test: (p: string) => boolean }[] = [
  { label: "At least 10 characters", test: (p) => p.length >= 10 },
  { label: "A lowercase letter", test: (p) => /[a-z]/.test(p) },
  { label: "An uppercase letter", test: (p) => /[A-Z]/.test(p) },
  { label: "A digit", test: (p) => /\d/.test(p) },
  { label: "A symbol", test: (p) => /[^A-Za-z0-9]/.test(p) },
];

function serverError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as
      | { message?: string; messages?: Record<string, string[]> }
      | undefined;
    if (d?.message) return d.message;
    if (d?.messages) {
      const first = Object.values(d.messages)[0];
      if (Array.isArray(first)) return String(first[0]);
    }
  }
  return "Something went wrong. Please try again.";
}

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const checks = RULES.map((r) => ({ label: r.label, ok: r.test(password) }));
  const passwordValid = checks.every((c) => c.ok);
  const confirmValid = confirm.length > 0 && confirm === password;
  const canSubmit = email.length > 0 && passwordValid && confirmValid && !loading;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await register(email, password); // backend auto-logs-in
      navigate("/");
    } catch (err) {
      setError(serverError(err));
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={submit}>
        <h1>Media Vault</h1>
        <h2>Create account</h2>

        <input
          type="email"
          placeholder="Email"
          value={email}
          required
          autoFocus
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          required
          onChange={(e) => setPassword(e.target.value)}
        />

        <ul className="password-rules">
          {checks.map((c) => (
            <li key={c.label} className={c.ok ? "ok" : "todo"}>
              {c.ok ? "✓" : "○"} {c.label}
            </li>
          ))}
        </ul>

        <input
          type="password"
          placeholder="Confirm password"
          value={confirm}
          required
          onChange={(e) => setConfirm(e.target.value)}
        />
        {confirm.length > 0 && !confirmValid && (
          <p className="error">Passwords don’t match.</p>
        )}

        <button type="submit" disabled={!canSubmit}>
          {loading ? "Creating…" : "Create account"}
        </button>

        {error && <p className="error">{error}</p>}
        <p className="switch">
          Already have an account? <Link to="/login">Sign in</Link>
        </p>
      </form>
    </div>
  );
}
