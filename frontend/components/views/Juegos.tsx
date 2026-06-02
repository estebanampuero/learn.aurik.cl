"use client";

import { useState } from "react";
import type { LangCode } from "@/lib/types";
import JuegoVoz from "@/components/views/games/JuegoVoz";
import JuegoListening from "@/components/views/games/JuegoListening";
import JuegoFrase from "@/components/views/games/JuegoFrase";
import JuegoMatch from "@/components/views/games/JuegoMatch";
import Flashcards from "@/components/views/Flashcards";

type GameId = "voz" | "listening" | "frase" | "match" | "flashcards";

const GAMES: { id: GameId; emoji: string; title: string; desc: string }[] = [
  { id: "voz", emoji: "🎙️", title: "Reto de voz", desc: "Lee la frase en voz alta y gana puntos por tu pronunciación." },
  { id: "listening", emoji: "👂", title: "¿Qué escuchaste?", desc: "Escucha el audio y elige la traducción correcta." },
  { id: "frase", emoji: "🧩", title: "Arma la frase", desc: "Ordena las palabras para formar la frase correcta." },
  { id: "match", emoji: "🃏", title: "Memoria / Match", desc: "Empareja cada palabra con su traducción." },
  { id: "flashcards", emoji: "⚡", title: "Flashcards", desc: "Repaso inteligente de tu vocabulario (SRS)." },
];

export default function Juegos({ lang }: { lang: LangCode }) {
  const [active, setActive] = useState<GameId | null>(null);

  if (active) {
    return (
      <div className="game-host">
        <button className="btn-ghost back" onClick={() => setActive(null)}>← Juegos</button>
        {active === "voz" && <JuegoVoz lang={lang} />}
        {active === "listening" && <JuegoListening lang={lang} />}
        {active === "frase" && <JuegoFrase lang={lang} />}
        {active === "match" && <JuegoMatch lang={lang} />}
        {active === "flashcards" && <Flashcards lang={lang} />}
      </div>
    );
  }

  return (
    <div className="juegos">
      <h2 className="view-title">Juegos 🎮</h2>
      <p className="view-sub">Practica jugando: pronunciación, escucha, gramática y vocabulario. Cada partida suma XP.</p>
      <div className="games-grid">
        {GAMES.map((g) => (
          <button key={g.id} className="game-card glass" onClick={() => setActive(g.id)}>
            <span className="game-emoji">{g.emoji}</span>
            <span className="game-title">{g.title}</span>
            <span className="game-desc">{g.desc}</span>
            <span className="game-go">Jugar →</span>
          </button>
        ))}
      </div>
    </div>
  );
}
