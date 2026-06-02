"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { LangCode, SentenceRound } from "@/lib/types";

export default function JuegoFrase({ lang }: { lang: LangCode }) {
  const [rounds, setRounds] = useState<SentenceRound[]>([]);
  const [i, setI] = useState(0);
  const [loading, setLoading] = useState(true);
  const [pool, setPool] = useState<string[]>([]);
  const [built, setBuilt] = useState<string[]>([]);
  const [checked, setChecked] = useState<null | boolean>(null);
  const [correct, setCorrect] = useState(0);
  const [done, setDone] = useState(false);
  const [xp, setXp] = useState(0);

  async function load() {
    setLoading(true); setDone(false); setI(0); setCorrect(0);
    try {
      const r = (await api.gameSentence(lang)).rounds;
      setRounds(r); setupRound(r, 0);
    } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [lang]);

  function setupRound(r: SentenceRound[], idx: number) {
    setPool(r[idx]?.tokens || []); setBuilt([]); setChecked(null);
  }

  const round = rounds[i];

  function take(k: number) {
    if (checked !== null) return;
    setBuilt((b) => [...b, pool[k]]);
    setPool((p) => p.filter((_, j) => j !== k));
  }
  function undo(k: number) {
    if (checked !== null) return;
    const w = built[k];
    setBuilt((b) => b.filter((_, j) => j !== k));
    setPool((p) => [...p, w]);
  }

  function check() {
    const ok = built.join(" ").toLowerCase() === round.answer.toLowerCase();
    setChecked(ok);
    if (ok) setCorrect((c) => c + 1);
  }

  async function next() {
    if (i + 1 < rounds.length) { setI(i + 1); setupRound(rounds, i + 1); }
    else {
      const r = await api.gameScore({ game: "sentence", correct, total: rounds.length });
      setXp(r.xp); setDone(true);
    }
  }

  if (loading) return <div className="center-pad"><span className="spinner big" /></div>;
  if (done) return (
    <div className="game-end glass">
      <div className="ge-emoji">🧩</div><div className="ge-title">¡Completado!</div>
      <div className="ge-score">{correct}/{rounds.length} correctas</div>
      <div className="ge-xp">+{xp} XP</div>
      <button className="btn-primary" onClick={load}>Jugar otra vez</button>
    </div>
  );

  return (
    <div className="game">
      <div className="game-hud"><span>{i + 1}/{rounds.length}</span><span>✅ {correct}</span></div>
      <div className="game-card glass">
        <div className="gf-trans">“{round.translation_es}”</div>
        <div className="gf-built">
          {built.map((w, k) => <button key={k} className="tile built" onClick={() => undo(k)}>{w}</button>)}
          {built.length === 0 && <span className="gf-hint">Toca las palabras en orden…</span>}
        </div>
        <div className="gf-pool">
          {pool.map((w, k) => <button key={k} className="tile" onClick={() => take(k)}>{w}</button>)}
        </div>
        {checked === null ? (
          <button className="btn-primary" onClick={check} disabled={pool.length > 0}>Comprobar</button>
        ) : (
          <div className={"gf-res " + (checked ? "ok" : "no")}>
            <div className="gf-verdict">{checked ? "✅ ¡Correcto!" : "❌ Casi"}</div>
            {!checked && <div className="gf-answer">{round.answer}</div>}
            <button className="btn-primary" onClick={next}>Siguiente →</button>
          </div>
        )}
      </div>
    </div>
  );
}
