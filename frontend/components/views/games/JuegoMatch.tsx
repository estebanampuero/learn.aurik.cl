"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { LangCode } from "@/lib/types";

type Card = { id: number; pair: number; text: string; side: "w" | "es"; matched: boolean };

export default function JuegoMatch({ lang }: { lang: LangCode }) {
  const [cards, setCards] = useState<Card[]>([]);
  const [loading, setLoading] = useState(true);
  const [flipped, setFlipped] = useState<number[]>([]);
  const [moves, setMoves] = useState(0);
  const [done, setDone] = useState(false);
  const [xp, setXp] = useState(0);
  const [lock, setLock] = useState(false);

  async function load() {
    setLoading(true); setDone(false); setMoves(0); setFlipped([]);
    try {
      const pairs = (await api.gameMatch(lang)).pairs.slice(0, 6);
      const cs: Card[] = [];
      pairs.forEach((p, idx) => {
        cs.push({ id: idx * 2, pair: idx, text: p.word, side: "w", matched: false });
        cs.push({ id: idx * 2 + 1, pair: idx, text: p.es, side: "es", matched: false });
      });
      for (let k = cs.length - 1; k > 0; k--) { const j = Math.floor(Math.random() * (k + 1)); [cs[k], cs[j]] = [cs[j], cs[k]]; }
      setCards(cs);
    } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [lang]);

  function flip(idx: number) {
    if (lock) return;
    const c = cards[idx];
    if (c.matched || flipped.includes(idx)) return;
    const nf = [...flipped, idx];
    setFlipped(nf);
    if (nf.length === 2) {
      setMoves((m) => m + 1);
      setLock(true);
      const [a, b] = nf;
      if (cards[a].pair === cards[b].pair) {
        setTimeout(() => {
          setCards((cs) => cs.map((x, k) => (k === a || k === b ? { ...x, matched: true } : x)));
          setFlipped([]); setLock(false);
        }, 450);
      } else {
        setTimeout(() => { setFlipped([]); setLock(false); }, 900);
      }
    }
  }

  const allMatched = cards.length > 0 && cards.every((c) => c.matched);
  useEffect(() => {
    if (allMatched && !done) {
      (async () => {
        const r = await api.gameScore({ game: "match", correct: cards.length / 2, total: moves });
        setXp(r.xp); setDone(true);
      })();
    }
  }, [allMatched]);

  if (loading) return <div className="center-pad"><span className="spinner big" /></div>;
  if (done) return (
    <div className="game-end glass">
      <div className="ge-emoji">🃏</div><div className="ge-title">¡Todo emparejado!</div>
      <div className="ge-score">{moves} intentos</div>
      <div className="ge-xp">+{xp} XP</div>
      <button className="btn-primary" onClick={load}>Jugar otra vez</button>
    </div>
  );

  return (
    <div className="game">
      <div className="game-hud"><span>Intentos: {moves}</span></div>
      <div className="match-grid">
        {cards.map((c, idx) => {
          const open = c.matched || flipped.includes(idx);
          return (
            <button key={c.id} className={"mcard" + (open ? " open" : "") + (c.matched ? " matched" : "")} onClick={() => flip(idx)}>
              {open ? <span className={"mc-text " + c.side}>{c.text}</span> : <span className="mc-back">?</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
