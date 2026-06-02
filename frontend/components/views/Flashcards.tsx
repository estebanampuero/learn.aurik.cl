"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Flashcard, LangCode } from "@/lib/types";

export default function Flashcards({ lang }: { lang: LangCode }) {
  const [cards, setCards] = useState<Flashcard[]>([]);
  const [i, setI] = useState(0);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<null | boolean>(null);
  const [done, setDone] = useState({ correct: 0, total: 0 });

  async function load() {
    setLoading(true);
    try { setCards((await api.flashcards(lang)).flashcards); setI(0); reset(); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [lang]);

  function reset() { setRevealed(false); setAnswer(""); setResult(null); }

  async function generate() {
    setBusy(true);
    try { await api.generateFlashcards(lang); await load(); }
    catch (e: any) { alert(e.message); }
    finally { setBusy(false); }
  }

  const card = cards[i];

  function check(correct: boolean) { setResult(correct); setRevealed(true); }

  function checkText() {
    if (!card) return;
    const ok = answer.trim().toLowerCase() === card.back.trim().toLowerCase();
    check(ok);
  }
  function checkOption(opt: string) {
    if (!card) return;
    setAnswer(opt);
    check(opt.trim().toLowerCase() === card.back.trim().toLowerCase());
  }

  async function next() {
    if (!card || result === null) return;
    await api.reviewFlashcard(card.id, result);
    setDone((d) => ({ correct: d.correct + (result ? 1 : 0), total: d.total + 1 }));
    if (i + 1 < cards.length) { setI(i + 1); reset(); }
    else { setCards([]); }  // sesión terminada
  }

  if (loading) return <div className="center-pad"><span className="spinner big" /></div>;

  if (cards.length === 0) {
    return (
      <div className="fc-empty">
        <h2 className="view-title">Flashcards</h2>
        {done.total > 0
          ? <div className="empty glass">✅ Sesión completa: {done.correct}/{done.total} correctas. <br />Vuelve más tarde o genera nuevas.</div>
          : <p className="view-sub">La IA genera tarjetas desde tu vocabulario y tus errores frecuentes, en 3 modos.</p>}
        <button className="btn-primary" onClick={generate} disabled={busy}>{busy ? "Generando…" : "✨ Generar flashcards"}</button>
      </div>
    );
  }

  const modeLabel = { multiple_choice: "Opción múltiple", fill_blank: "Completa la frase", reverse: "Traducción inversa" }[card.mode];

  return (
    <div className="fc-view">
      <div className="fc-progress">Tarjeta {i + 1}/{cards.length} · {modeLabel}</div>
      <div className="fc-card glass">
        <div className="fc-front">{card.front}</div>
        {card.hint && !revealed && <div className="fc-hint">💡 {card.hint}</div>}

        {card.mode === "multiple_choice" && !revealed && (
          <div className="fc-options">
            {card.options.map((o, k) => <button key={k} className="fc-opt" onClick={() => checkOption(o)}>{o}</button>)}
          </div>
        )}
        {(card.mode === "fill_blank" || card.mode === "reverse") && !revealed && (
          <div className="fc-input-row">
            <input className="field" value={answer} onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") checkText(); }} placeholder="Tu respuesta…" autoFocus />
            <button className="btn-primary" onClick={checkText}>Comprobar</button>
          </div>
        )}

        {revealed && (
          <div className={"fc-result " + (result ? "ok" : "no")}>
            <div className="fc-verdict">{result ? "✅ ¡Correcto!" : "❌ Casi"}</div>
            <div className="fc-answer">Respuesta: <b>{card.back}</b></div>
            <button className="btn-primary" onClick={next}>Siguiente →</button>
          </div>
        )}
      </div>
      <button className="btn-ghost" onClick={generate} disabled={busy}>{busy ? "…" : "✨ Generar más"}</button>
    </div>
  );
}
