"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Achievement, Dashboard, LangCode, Quest, Stats } from "@/lib/types";

export default function Progreso({ lang }: { lang: LangCode }) {
  const [dash, setDash] = useState<Dashboard | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [achs, setAchs] = useState<Achievement[]>([]);
  const [quests, setQuests] = useState<Quest[]>([]);
  const [plan, setPlan] = useState<any>(null);
  const [report, setReport] = useState<any>(null);
  const [busy, setBusy] = useState("");

  async function loadAll() {
    const [d, s, a, q, p, r] = await Promise.allSettled([
      api.dashboard(), api.stats(lang), api.achievements(), api.quests(), api.studyPlan(), api.reports(),
    ]);
    if (d.status === "fulfilled") setDash(d.value);
    if (s.status === "fulfilled") setStats(s.value);
    if (a.status === "fulfilled") setAchs(a.value.achievements);
    if (q.status === "fulfilled") setQuests(q.value.quests);
    if (p.status === "fulfilled") setPlan(p.value.plan);
    if (r.status === "fulfilled") setReport(r.value.reports?.[0]?.content || null);
  }
  useEffect(() => { loadAll(); }, [lang]);

  async function genPlan() { setBusy("plan"); try { setPlan((await api.makeStudyPlan(lang)).plan); } finally { setBusy(""); } }
  async function genReport() { setBusy("report"); try { setReport((await api.makeWeeklyReport(lang)).report); } finally { setBusy(""); } }

  return (
    <div className="prog-view">
      <h2 className="view-title">Tu progreso</h2>

      {/* Nivel / rango + misiones diarias */}
      {dash?.level_info && (
        <div className="level-row">
          <div className="level-card glass">
            <div className="level-ring" style={{ ["--p" as any]: `${Math.round((dash.level_info.xp_in_level / Math.max(1, dash.level_info.xp_to_next)) * 100)}%` }}>
              <div className="level-num">{dash.level_info.level}</div>
            </div>
            <div className="level-meta">
              <div className="level-rank">{dash.level_info.rank}</div>
              <div className="level-xp">{dash.level_info.xp_in_level} / {dash.level_info.xp_to_next} XP al nivel {dash.level_info.level + 1}</div>
            </div>
          </div>
          <div className="quests-card glass">
            <div className="quests-title">🎯 Misiones de hoy</div>
            {quests.map((q) => (
              <div className={"quest" + (q.done ? " done" : "")} key={q.id}>
                <span className="q-ic">{q.done ? "✅" : q.icon}</span>
                <span className="q-title">{q.title}</span>
                <span className="q-prog">{q.progress}/{q.goal}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Dashboard */}
      {dash && (
        <div className="kpi-grid">
          <Kpi icon="🔥" label="Racha" value={`${dash.streak} días`} sub={`máx ${dash.longest_streak}`} />
          <Kpi icon="⭐" label="XP" value={String(dash.xp)} />
          <Kpi icon="💬" label="Conversaciones" value={String(dash.conversations)} />
          <Kpi icon="📚" label="Palabras" value={String(dash.words_learned)} />
          <Kpi icon="🎙️" label="Pronunciación" value={`${dash.avg_pronunciation}%`} />
          <Kpi icon="🇩🇪" label="Nivel DE" value={dash.level_de} />
          <Kpi icon="🇬🇧" label="Nivel EN" value={dash.level_en} />
          <Kpi icon="⏱️" label="Horas (est.)" value={String(dash.hours_studied)} />
        </div>
      )}

      {/* Estadísticas */}
      {stats && (
        <section className="card glass">
          <h3>Estadísticas ({lang === "de" ? "alemán" : "inglés"})</h3>
          <div className="skills">
            {stats.skills.map((s) => (
              <div className="skill" key={s.skill}>
                <div className="skill-top"><span>{s.skill}</span><span>{s.score}%</span></div>
                <div className="bar"><div className="bar-fill" style={{ width: `${s.score}%` }} /></div>
              </div>
            ))}
          </div>
          <div className="sw-grid">
            <div><div className="sw-h ok">Fortalezas</div>{stats.strengths.length ? stats.strengths.map((s) => <span className="sw-chip ok" key={s.skill}>{s.skill} {s.score}%</span>) : <span className="muted">—</span>}</div>
            <div><div className="sw-h no">A mejorar</div>{stats.weaknesses.length ? stats.weaknesses.map((s) => <span className="sw-chip no" key={s.skill}>{s.skill} {s.score}%</span>) : <span className="muted">—</span>}</div>
          </div>
        </section>
      )}

      {/* Pronunciación */}
      <PronunciationCard lang={lang} onScored={loadAll} />

      {/* Logros */}
      <section className="card glass">
        <h3>Logros</h3>
        <div className="ach-grid">
          {achs.map((a) => (
            <div className={"ach" + (a.unlocked ? " on" : "")} key={a.code} title={a.desc}>
              <span className="ach-em">{a.emoji}</span><span className="ach-t">{a.title}</span>
            </div>
          ))}
        </div>
      </section>

      {/* Plan de estudio */}
      <section className="card glass">
        <div className="card-head"><h3>Plan de estudio</h3><button className="btn-ghost" onClick={genPlan} disabled={busy === "plan"}>{busy === "plan" ? "…" : plan ? "Regenerar" : "✨ Crear plan"}</button></div>
        {plan ? (
          <div className="plan">
            <div className="plan-obj"><b>Objetivos:</b> {(plan.objectives || []).join(" · ")}</div>
            <div className="plan-week">
              {(plan.weekly_schedule || []).map((d: any, k: number) => (
                <div className="plan-day" key={k}><b>{d.day}</b><span>{d.focus}</span><small>{d.activity}</small></div>
              ))}
            </div>
            <div className="plan-topics">{(plan.topics || []).map((t: string, k: number) => <span className="chip" key={k}>{t}</span>)}</div>
          </div>
        ) : <p className="muted">Genera un plan personalizado según tu nivel y debilidades.</p>}
      </section>

      {/* Informe semanal */}
      <section className="card glass">
        <div className="card-head"><h3>Informe semanal</h3><button className="btn-ghost" onClick={genReport} disabled={busy === "report"}>{busy === "report" ? "…" : "✨ Generar"}</button></div>
        {report ? (
          <div className="report">
            <p className="report-sum">{report.summary}</p>
            {!!report.frequent_errors?.length && <div><b>Errores frecuentes:</b> {report.frequent_errors.join(" · ")}</div>}
            {!!report.new_words?.length && <div><b>Palabras nuevas:</b> {report.new_words.join(", ")}</div>}
            {!!report.recommendations?.length && <ul>{report.recommendations.map((r: string, k: number) => <li key={k}>{r}</li>)}</ul>}
          </div>
        ) : <p className="muted">Genera un resumen de tus avances, errores y recomendaciones de la semana.</p>}
      </section>
    </div>
  );
}

function Kpi({ icon, label, value, sub }: { icon: string; label: string; value: string; sub?: string }) {
  return (
    <div className="kpi glass">
      <div className="kpi-ic">{icon}</div>
      <div className="kpi-v">{value}</div>
      <div className="kpi-l">{label}{sub && <span className="kpi-sub"> · {sub}</span>}</div>
    </div>
  );
}

function PronunciationCard({ lang, onScored }: { lang: LangCode; onScored: () => void }) {
  const SAMPLES: Record<string, string[]> = {
    de: ["Ich möchte einen Kaffee, bitte.", "Wie komme ich zum Bahnhof?", "Es freut mich, dich kennenzulernen."],
    en: ["I would like a coffee, please.", "How do I get to the station?", "It's a pleasure to meet you."],
  };
  const [target, setTarget] = useState(SAMPLES[lang][0]);
  const [rec, setRec] = useState(false);
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<any>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const startT = useRef(0);

  useEffect(() => { setTarget(SAMPLES[lang][0]); setRes(null); }, [lang]);

  async function toggle() {
    if (rec) { recRef.current?.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const r = new MediaRecorder(stream);
      chunks.current = []; startT.current = Date.now();
      r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      r.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRec(false); setBusy(true);
        const dur = (Date.now() - startT.current) / 1000;
        const fd = new FormData();
        fd.append("audio", new Blob(chunks.current, { type: "audio/webm" }), "p.webm");
        fd.append("target", target); fd.append("lang", lang); fd.append("duration", String(dur));
        try { setRes(await api.pronunciation(fd)); onScored(); }
        catch (e: any) { alert(e.message); } finally { setBusy(false); }
      };
      recRef.current = r; r.start(); setRec(true);
    } catch { alert("No pude acceder al micrófono."); }
  }

  return (
    <section className="card glass">
      <h3>Evalúa tu pronunciación 🎙️</h3>
      <p className="muted">Lee la frase en voz alta y obtén tu puntaje.</p>
      <div className="pron-target">
        <select className="field" value={target} onChange={(e) => { setTarget(e.target.value); setRes(null); }}>
          {SAMPLES[lang].map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <button className={"btn-primary" + (rec ? " recording" : "")} onClick={toggle} disabled={busy}>
        {busy ? "Evaluando…" : rec ? "⏹ Detener" : "● Grabar y evaluar"}
      </button>
      {res && (
        <div className="pron-res">
          <div className="pron-overall">{res.overall}%</div>
          <div className="pron-bars">
            <PB label="Precisión" v={res.accuracy} /><PB label="Entonación" v={res.intonation} /><PB label="Fluidez" v={res.fluency} />
          </div>
          {res.transcript && <div className="pron-heard">Se entendió: <i>“{res.transcript}”</i></div>}
          {res.tips && <div className="pron-tips">💡 {res.tips}</div>}
        </div>
      )}
    </section>
  );
}

function PB({ label, v }: { label: string; v: number }) {
  return (
    <div className="pb"><div className="pb-top"><span>{label}</span><span>{v}%</span></div>
      <div className="bar"><div className="bar-fill" style={{ width: `${v}%` }} /></div></div>
  );
}
