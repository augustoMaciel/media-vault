import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "../context/AuthContext";

function serverError(e: unknown): string {
  if (axios.isAxiosError(e)) {
    const d = e.response?.data as { message?: string } | undefined;
    if (d?.message) return d.message;
  }
  return "Something went wrong. Please try again.";
}

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email, password);
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
        <h2>Sign in</h2>

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

        <button type="submit" disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>

        {error && <p className="error">{error}</p>}
        <p className="switch">
          No account? <Link to="/register">Create one</Link>
        </p>
      </form>
    </div>
  );
}
