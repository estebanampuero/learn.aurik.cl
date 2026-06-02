"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import type { Conversation } from "@/lib/types";

export default function Perfil() {
  const { user, logout } = useAuth();
  const [convs, setConvs] = useState<Conversation[]>([]);

  useEffect(() => { api.conversations().then((d) => setConvs(d.conversations)).catch(() => {}); }, []);

  return (
    <div className="perfil">
      <h2 className="view-title">Perfil</h2>
      <section className="card glass">
        <div className="profile-head">
          <div className="profile-av">{(user?.name || user?.email || "?")[0].toUpperCase()}</div>
          <div>
            <div className="profile-name">{user?.name || "Sin nombre"}</div>
            <div className="profile-email">{user?.email}</div>
          </div>
        </div>
        <div className="profile-levels">
          <span className="lvl">🇩🇪 {user?.level_de}</span><span className="lvl">🇬🇧 {user?.level_en}</span>
        </div>
        {user?.goals && <div className="profile-goals"><b>Objetivo:</b> {user.goals}</div>}
        <button className="btn-ghost danger" onClick={logout}>Cerrar sesión</button>
      </section>

      <section className="card glass">
        <h3>Historial de conversaciones</h3>
        {convs.length === 0 ? <p className="muted">Aún no tienes conversaciones.</p> :
          <div className="conv-history">
            {convs.map((c) => (
              <div className="conv-row" key={c.id}>
                <span className="conv-flag">{c.lang === "de" ? "🇩🇪" : "🇬🇧"}</span>
                <span className="conv-title">{c.title}</span>
                <span className="conv-date">{c.updated_at ? new Date(c.updated_at).toLocaleDateString() : ""}</span>
              </div>
            ))}
          </div>}
      </section>
    </div>
  );
}
