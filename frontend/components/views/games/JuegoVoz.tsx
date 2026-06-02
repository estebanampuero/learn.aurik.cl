"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { LangCode } from "@/lib/types";

export default function JuegoVoz({ lang }: { lang: LangCode }) {
  const [phrases, setPhrases] = useState<string[]>([]);
  const [i, setI] = useState(0);
  const [loading, setLoading] = useState(true);
  const [rec, setRec] = useState(false);
  const [busy, setBusy] = useState(false);
  const [score, setScore] = useState(0);
  const [combo, setCombo] = useState(0);
  const [last, setLast] = useState<any>(null);
  const [done, setDone] = useState(false);
  const [xp, setXp] = useState(0);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const startT = useRef(0);

  async function load() {
    setLoading(true); setDone(false); setI(0); setScore(0); setCombo(0); setLast(null);
    try { setPhrases((await api.gameVoice(lang)).phrases); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [lang]);

  async function toggle() {
    if (busy || done) return;
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
        fd.append("target", phrases[i]); fd.append("lang", lang); fd.append("duration", String(dur));
        try {
          const res = await api.pronunciation(fd);
          setLast(res);
          const good = res.overall >= 70;
          setScore((s) => s + res.overall);
          setCombo((c) => (good ? c + 1 : 0));
        } catch { setLast({ overall: 0, tips: "No se entendió, intenta de nuevo." }); }
        finally { setBusy(false); }
      };
      recRef.current = r; r.start(); setRec(true);
    } catch { alert("No pude acceder al micrófono."); }
  }

  async function next() {
    setLast(null);
    if (i + 1 < phrases.length) setI(i + 1);
    else {
      const avg = Math.round(score / Math.max(1, phrases.length));
      const r = await api.gameScore({ game: "voice", correct: avg, total: 100 });
      setXp(r.xp); setDone(true);
    }
  }

  if (loading) return <div className="center-pad"><span className="spinner big" /></div>;
  if (done) return (
    <div className="game-end glass">
      <div className="ge-emoji">🎙️</div>
      <div className="ge-title">¡Buen trabajo!</div>
      <div className="ge-score">Promedio: {Math.round(score / Math.max(1, phrases.length))}%</div>
      <div className="ge-xp">+{xp} XP</div>
      <button className="btn-primary" onClick={load}>Jugar otra vez</button>
    </div>
  );

  return (
    <div className="game">
      <div className="game-hud"><span>{i + 1}/{phrases.length}</span><span className="combo">🔥 {combo}</span></div>
      <div className="game-card glass">
        <div className="gv-label">Di en voz alta:</div>
        <div className="gv-phrase">{phrases[i]}</div>
        {last ? (
          <div className="gv-res">
            <div className={"gv-score " + (last.overall >= 70 ? "ok" : "no")}>{last.overall}%</div>
            {last.tips && <div className="gv-tip">💡 {last.tips}</div>}
            <button className="btn-primary" onClick={next}>Siguiente →</button>
          </div>
        ) : (
          <button className={"btn-primary" + (rec ? " recording" : "")} onClick={toggle} disabled={busy}>
            {busy ? "Evaluando…" : rec ? "⏹ Detener" : "● Grabar"}
          </button>
        )}
      </div>
    </div>
  );
}
