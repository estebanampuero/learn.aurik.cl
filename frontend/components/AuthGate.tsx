"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";

export default function AuthGate() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [goals, setGoals] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (mode === "login") await login(email.trim(), password);
      else await register(email.trim(), password, name.trim(), goals.trim());
    } catch (e: any) {
      setErr(e.message || "Error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card glass">
        <div className="auth-brand">
          <span className="auth-logo">🗣️</span>
          <h1>Sona</h1>
          <p>Tu tutor de idiomas con voz — alemán e inglés.</p>
        </div>

        <div className="seg auth-seg glass">
          <button className={"seg-btn" + (mode === "login" ? " on" : "")} onClick={() => setMode("login")}>Entrar</button>
          <button className={"seg-btn" + (mode === "register" ? " on" : "")} onClick={() => setMode("register")}>Crear cuenta</button>
        </div>

        <form onSubmit={submit} className="auth-form">
          {mode === "register" && (
            <input className="field" placeholder="Tu nombre" value={name} onChange={(e) => setName(e.target.value)} />
          )}
          <input className="field" type="email" placeholder="Email" value={email} required
                 onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          <input className="field" type="password" placeholder="Contraseña" value={password} required
                 onChange={(e) => setPassword(e.target.value)} autoComplete={mode === "login" ? "current-password" : "new-password"} />
          {mode === "register" && (
            <textarea className="field" placeholder="¿Tu objetivo? (ej. trabajar en Alemania, viajar…)"
                      value={goals} onChange={(e) => setGoals(e.target.value)} rows={2} />
          )}
          {err && <div className="auth-err">{err}</div>}
          <button className="btn-primary" type="submit" disabled={busy}>
            {busy ? "…" : mode === "login" ? "Entrar" : "Crear cuenta"}
          </button>
        </form>
      </div>
    </div>
  );
}
