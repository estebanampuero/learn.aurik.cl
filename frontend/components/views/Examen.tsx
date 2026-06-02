"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ExamGrade, ExamMeta, ExamTask, LangCode } from "@/lib/types";

export default function Examen({ lang }: { lang: LangCode }) {
  const [catalog, setCatalog] = useState<ExamMeta[]>([]);
  const [exam, setExam] = useState<ExamMeta | null>(null);
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [tasks, setTasks] = useState<ExamTask[]>([]);
  const [answers, setAnswers] = useState<string[]>([]);
  const [i, setI] = useState(0);
  const [loading, setLoading] = useState(false);
  const [grading, setGrading] = useState(false);
  const [result, setResult] = useState<ExamGrade | null>(null);

  useEffect(() => { api.exams(lang).then((d) => setCatalog(d.exams)).catch(() => {}); setExam(null); setResult(null); setSessionId(null); }, [lang]);

  async function start(e: ExamMeta) {
    setLoading(true); setExam(e); setResult(null);
    try {
      const d = await api.startExam({ exam_id: e.id, lang });
      setSessionId(d.session_id); setTasks(d.tasks); setAnswers(new Array(d.tasks.length).fill("")); setI(0);
    } catch (err: any) { alert(err.message); setExam(null); } finally { setLoading(false); }
  }

  function setAnswer(v: string) { setAnswers((a) => a.map((x, k) => (k === i ? v : x))); }

  async function submit() {
    if (sessionId == null) return;
    setGrading(true);
    try { setResult((await api.gradeExam(sessionId, answers)).result); }
    catch (e: any) { alert(e.message); } finally { setGrading(false); }
  }

  // ── Catálogo ──
  if (!exam) {
    return (
      <div className="exam-view">
        <h2 className="view-title">Modo examen 📜</h2>
        <p className="view-sub">Tests de nivel CEFR (A1–C1) estilo {lang === "de" ? "Goethe-Zertifikat" : "IELTS"}: lectura, audio, escritura y expresión oral, con resultado certificado.</p>
        <div className="exam-grid">
          {catalog.map((e) => (
            <button key={e.id} className="exam-card glass" onClick={() => start(e)} disabled={loading}>
              <span className="exam-emoji">{e.emoji}</span>
              <span className="exam-title">{e.title} {e.premium && <span className="badge-prem">💎</span>}</span>
              <span className="exam-sub">{e.subtitle}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  if (loading) return <div className="center-pad"><span className="spinner big" /><p className="muted">Generando tu examen…</p></div>;

  // ── Resultado ──
  if (result) {
    return (
      <div className="exam-result">
        <div className="cert glass">
          <div className="cert-band">{exam.cert === "ielts" ? "IELTS" : exam.cert === "goethe" ? "Goethe-Zertifikat" : "Test de nivel"}</div>
          <div className={"cert-level " + (result.passed ? "pass" : "")}>{result.cefr_level}</div>
          <div className="cert-score">{result.band || `${result.score}/100`}</div>
          <div className={"cert-verdict " + (result.passed ? "ok" : "no")}>
            {result.passed ? "✅ Aprobado" : exam.cert === "placement" ? "Nivel estimado" : "Sigue practicando"}
          </div>
          <div className="cert-skills">
            {result.per_skill.map((s) => (
              <div className="skill" key={s.skill}>
                <div className="skill-top"><span>{s.skill}</span><span>{s.score}%</span></div>
                <div className="bar"><div className="bar-fill" style={{ width: `${s.score}%` }} /></div>
              </div>
            ))}
          </div>
          <p className="cert-feedback">{result.feedback}</p>
          {!!result.recommendations?.length && <ul className="cert-recs">{result.recommendations.map((r, k) => <li key={k}>{r}</li>)}</ul>}
          <button className="btn-primary" onClick={() => { setExam(null); setResult(null); }}>Volver a exámenes</button>
        </div>
      </div>
    );
  }

  // ── Flujo tarea-a-tarea ──
  const task = tasks[i];
  const last = i === tasks.length - 1;
  return (
    <div className="exam-run">
      <div className="exam-head glass">
        <button className="btn-ghost" onClick={() => setExam(null)}>← Salir</button>
        <span className="exam-prog">{exam.title} · Tarea {i + 1}/{tasks.length}</span>
        <span className="exam-skill">{task.skill}</span>
      </div>

      <div className="task-card glass">
        <ExamTaskView task={task} lang={lang} value={answers[i]} onChange={setAnswer} />
      </div>

      <div className="exam-nav">
        {i > 0 && <button className="btn-ghost" onClick={() => setI(i - 1)}>← Anterior</button>}
        {!last
          ? <button className="btn-primary" onClick={() => setI(i + 1)}>Siguiente →</button>
          : <button className="btn-primary" onClick={submit} disabled={grading}>{grading ? "Evaluando…" : "Finalizar examen"}</button>}
      </div>
    </div>
  );
}

function ExamTaskView({ task, lang, value, onChange }: {
  task: ExamTask; lang: LangCode; value: string; onChange: (v: string) => void;
}) {
  const [rec, setRec] = useState(false);
  const [busy, setBusy] = useState(false);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);

  function playAudio() {
    if (!task.audio_b64) return;
    new Audio("data:audio/wav;base64," + task.audio_b64).play().catch(() => {});
  }

  async function toggleRec() {
    if (rec) { recRef.current?.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const r = new MediaRecorder(stream);
      chunks.current = [];
      r.ondataavailable = (e) => e.data.size && chunks.current.push(e.data);
      r.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop()); setRec(false); setBusy(true);
        const fd = new FormData();
        fd.append("audio", new Blob(chunks.current, { type: "audio/webm" }), "a.webm");
        fd.append("lang", lang);
        try { onChange((await api.transcribe(fd)).text); } catch { /* ignore */ } finally { setBusy(false); }
      };
      recRef.current = r; r.start(); setRec(true);
    } catch { alert("No pude acceder al micrófono."); }
  }

  return (
    <>
      <div className="task-prompt">{task.prompt}</div>
      {task.type === "reading_mc" && task.passage && <div className="task-passage">{task.passage}</div>}
      {task.type === "listening_mc" && (
        <button className="play-big" onClick={playAudio}>🔊 Reproducir audio</button>
      )}

      {(task.type === "reading_mc" || task.type === "listening_mc") && (
        <div className="task-options">
          {(task.options || []).map((o, k) => (
            <button key={k} className={"task-opt" + (value === o ? " on" : "")} onClick={() => onChange(o)}>{o}</button>
          ))}
        </div>
      )}
      {task.type === "writing" && (
        <textarea className="field" rows={5} value={value} onChange={(e) => onChange(e.target.value)} placeholder="Escribe tu respuesta…" />
      )}
      {task.type === "speaking" && (
        <div className="task-speak">
          <button className={"btn-primary" + (rec ? " recording" : "")} onClick={toggleRec} disabled={busy}>
            {busy ? "Transcribiendo…" : rec ? "⏹ Detener" : "● Responder hablando"}
          </button>
          {value && <div className="task-transcript">Tu respuesta: “{value}”</div>}
        </div>
      )}
    </>
  );
}
