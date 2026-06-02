"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { LangCode, ListeningRound } from "@/lib/types";

export default function JuegoListening({ lang }: { lang: LangCode }) {
  const [rounds, setRounds] = useState<ListeningRound[]>([]);
  const [i, setI] = useState(0);
  const [loading, setLoading] = useState(true);
  const [picked, setPicked] = useState<string | null>(null);
  const [correct, setCorrect] = useState(0);
  const [done, setDone] = useState(false);
  const [xp, setXp] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  async function load() {
    setLoading(true); setDone(false); setI(0); setCorrect(0); setPicked(null);
    try { setRounds((await api.gameListening(lang)).rounds); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [lang]);

  const round = rounds[i];

  useEffect(() => { if (round) setTimeout(play, 350); }, [i, rounds.length]);

  function play() {
    if (!round) return;
    audioRef.current?.pause();
    const a = new Audio("data:audio/wav;base64," + round.audio_b64);
    audioRef.current = a; a.play().catch(() => {});
  }

  function pick(opt: string) {
    if (picked) return;
    setPicked(opt);
    if (opt === round.correct) setCorrect((c) => c + 1);
  }

  async function next() {
    setPicked(null);
    if (i + 1 < rounds.length) setI(i + 1);
    else {
      const r = await api.gameScore({ game: "listening", correct, total: rounds.length });
      setXp(r.xp); setDone(true);
    }
  }

  if (loading) return <div className="center-pad"><span className="spinner big" /></div>;
  if (done) return (
    <div className="game-end glass">
      <div className="ge-emoji">👂</div><div className="ge-title">¡Listo!</div>
      <div className="ge-score">{correct}/{rounds.length} correctas</div>
      <div className="ge-xp">+{xp} XP</div>
      <button className="btn-primary" onClick={load}>Jugar otra vez</button>
    </div>
  );

  return (
    <div className="game">
      <div className="game-hud"><span>{i + 1}/{rounds.length}</span><span>✅ {correct}</span></div>
      <div className="game-card glass">
        <button className="play-big" onClick={play}>🔊 Reproducir</button>
        <div className="gl-options">
          {round.options.map((o, k) => {
            const cls = picked ? (o === round.correct ? "gl-opt ok" : o === picked ? "gl-opt no" : "gl-opt") : "gl-opt";
            return <button key={k} className={cls} onClick={() => pick(o)}>{o}</button>;
          })}
        </div>
        {picked && (
          <div className="gl-after">
            <div className="gl-sentence">{round.sentence}</div>
            <button className="btn-primary" onClick={next}>Siguiente →</button>
          </div>
        )}
      </div>
    </div>
  );
}
