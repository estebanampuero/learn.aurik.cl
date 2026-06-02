"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import type { Conversation, LangCode } from "@/lib/types";
import Conversar from "@/components/views/Conversar";
import Vocabulario from "@/components/views/Vocabulario";
import Escenarios from "@/components/views/Escenarios";
import Juegos from "@/components/views/Juegos";
import Examen from "@/components/views/Examen";
import Progreso from "@/components/views/Progreso";
import Perfil from "@/components/views/Perfil";

type View = "conversar" | "vocabulario" | "juegos" | "lecciones" | "roleplay" | "examen" | "progreso" | "perfil";

const NAV: { id: View; label: string; icon: string }[] = [
  { id: "conversar", label: "Conversar", icon: "💬" },
  { id: "lecciones", label: "Aprender", icon: "📚" },
  { id: "roleplay", label: "Roleplay", icon: "🎭" },
  { id: "juegos", label: "Juegos", icon: "🎮" },
  { id: "examen", label: "Examen", icon: "📜" },
  { id: "progreso", label: "Progreso", icon: "📊" },
  { id: "vocabulario", label: "Vocabulario", icon: "⭐" },
  { id: "perfil", label: "Perfil", icon: "👤" },
];

export default function AppShell() {
  const { user } = useAuth();
  const [view, setView] = useState<View>("conversar");
  const [lang, setLang] = useState<LangCode>("de");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  // Conversación a abrir en la vista Conversar (al iniciar lección/roleplay/examen o continuar historial).
  const [pending, setPending] = useState<Conversation | null>(null);

  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);

  function openConversation(conv: Conversation) {
    setPending(conv);
    setView("conversar");
  }

  return (
    <div className="shell">
      {/* Barra superior */}
      <header className="topbar glass">
        <div className="brand">🗣️ <b>Sona</b></div>
        <div className="topbar-right">
          <div className="seg lang-seg glass">
            {(["de", "en"] as LangCode[]).map((l) => (
              <button key={l} className={"seg-btn" + (lang === l ? " on" : "")} onClick={() => setLang(l)}>
                {l === "de" ? "🇩🇪 DE" : "🇬🇧 EN"}
              </button>
            ))}
          </div>
          <button className="icon-btn" onClick={() => setTheme(theme === "light" ? "dark" : "light")} aria-label="Tema">
            {theme === "light" ? "🌙" : "☀️"}
          </button>
        </div>
      </header>

      <div className="shell-body">
        {/* Navegación lateral (desktop) */}
        <nav className="sidenav glass">
          {NAV.map((n) => (
            <button key={n.id} className={"nav-item" + (view === n.id ? " on" : "")} onClick={() => setView(n.id)}>
              <span className="nav-ic">{n.icon}</span><span className="nav-lb">{n.label}</span>
            </button>
          ))}
        </nav>

        {/* Vista activa */}
        <main className="view">
          {view === "conversar" && (
            <Conversar lang={lang} pending={pending} onConsumePending={() => setPending(null)} />
          )}
          {view === "vocabulario" && <Vocabulario lang={lang} />}
          {view === "juegos" && <Juegos lang={lang} />}
          {view === "lecciones" && <Escenarios kind="lesson" lang={lang} onOpen={openConversation} />}
          {view === "roleplay" && <Escenarios kind="roleplay" lang={lang} onOpen={openConversation} />}
          {view === "examen" && <Examen lang={lang} />}
          {view === "progreso" && <Progreso lang={lang} />}
          {view === "perfil" && <Perfil />}
        </main>
      </div>

      {/* Navegación inferior (móvil) */}
      <nav className="bottomnav glass">
        {NAV.slice(0, 5).map((n) => (
          <button key={n.id} className={"bn-item" + (view === n.id ? " on" : "")} onClick={() => setView(n.id)}>
            <span className="bn-ic">{n.icon}</span><span className="bn-lb">{n.label}</span>
          </button>
        ))}
        <button className={"bn-item" + (["progreso", "perfil", "vocabulario"].includes(view) ? " on" : "")}
                onClick={() => setView("progreso")}>
          <span className="bn-ic">📊</span><span className="bn-lb">Más</span>
        </button>
      </nav>
    </div>
  );
}
