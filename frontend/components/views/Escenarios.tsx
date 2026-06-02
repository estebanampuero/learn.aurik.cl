"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Conversation, LangCode, Scenario, Tutor } from "@/lib/types";

const META: Record<string, { title: string; sub: string; mode: string }> = {
  lesson: { title: "Lecciones temáticas", sub: "Conversaciones guiadas sobre un tema. Tu tutor lleva el hilo.", mode: "lesson" },
  roleplay: { title: "Simulaciones (roleplay)", sub: "Situaciones reales: el tutor interpreta un papel y tú respondes.", mode: "roleplay" },
  exam: { title: "Modo examen", sub: "Práctica con criterios de examen oficial y feedback de nivel.", mode: "exam" },
};

export default function Escenarios({ kind, lang, onOpen }: {
  kind: "lesson" | "roleplay" | "exam"; lang: LangCode; onOpen: (c: Conversation) => void;
}) {
  const [items, setItems] = useState<Scenario[]>([]);
  const [tutors, setTutors] = useState<Tutor[]>([]);
  const [tutorId, setTutorId] = useState<string>("");
  const [busy, setBusy] = useState<string>("");

  useEffect(() => {
    const fetcher = kind === "lesson" ? api.lessons : kind === "roleplay" ? api.roleplays : api.exams;
    fetcher().then((d: any) => setItems(d.lessons || d.roleplays || d.exams)).catch(() => {});
    api.tutors(lang).then((d) => { setTutors(d.tutors); setTutorId(d.tutors[0]?.id || ""); }).catch(() => {});
  }, [kind, lang]);

  async function start(s: Scenario) {
    setBusy(s.id);
    try {
      const c = await api.startConversation({ lang, tutor_id: tutorId, mode: META[kind].mode, scenario_id: s.id });
      onOpen(c);
    } catch (e: any) { alert(e.message); } finally { setBusy(""); }
  }

  const m = META[kind];
  return (
    <div className="scn-view">
      <h2 className="view-title">{m.title}</h2>
      <p className="view-sub">{m.sub}</p>

      <div className="tutor-pills">
        <span className="tp-label">Tutor:</span>
        {tutors.map((t) => (
          <button key={t.id} className={"tp" + (tutorId === t.id ? " on" : "")} onClick={() => setTutorId(t.id)}>
            {t.name} · {t.specialty_es}
          </button>
        ))}
      </div>

      <div className="scn-grid">
        {items.map((s) => (
          <button key={s.id} className="scn-card glass" onClick={() => start(s)} disabled={!!busy}>
            <span className="scn-emoji">{s.emoji}</span>
            <span className="scn-title">{s.title}</span>
            <span className="scn-desc">{s.desc}</span>
            <span className="scn-go">{busy === s.id ? "Iniciando…" : "Empezar →"}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
