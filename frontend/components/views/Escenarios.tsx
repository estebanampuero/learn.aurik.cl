"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Conversation, LangCode, Scenario, Tutor } from "@/lib/types";

const META: Record<string, { title: string; sub: string; mode: string }> = {
  lesson: { title: "Aprender — lecciones guiadas", sub: "Cada lección tiene objetivos que vas cumpliendo al conversar. Completa todos para ganar estrellas y XP.", mode: "lesson" },
  roleplay: { title: "Simulaciones (roleplay)", sub: "Situaciones reales con una misión: el tutor interpreta un papel y tú cumples objetivos.", mode: "roleplay" },
};

export default function Escenarios({ kind, lang, onOpen }: {
  kind: "lesson" | "roleplay"; lang: LangCode; onOpen: (c: Conversation) => void;
}) {
  const [items, setItems] = useState<Scenario[]>([]);
  const [tutors, setTutors] = useState<Tutor[]>([]);
  const [tutorId, setTutorId] = useState<string>("");
  const [busy, setBusy] = useState<string>("");

  useEffect(() => {
    const fetcher = kind === "lesson" ? api.lessons : api.roleplays;
    fetcher().then((d: any) => setItems(d.lessons || d.roleplays)).catch(() => {});
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
            {!!s.objectives?.length && (
              <span className="scn-objs">🎯 {s.objectives.length} objetivos</span>
            )}
            <span className="scn-go">{busy === s.id ? "Iniciando…" : "Empezar →"}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
