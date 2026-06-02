"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { LangCode, SavedWord } from "@/lib/types";

export default function Vocabulario({ lang }: { lang: LangCode }) {
  const [words, setWords] = useState<SavedWord[]>([]);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    try { setWords((await api.vocab(lang)).vocab); } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [lang]);

  async function remove(id: number) {
    await api.deleteWord(id);
    setWords((w) => w.filter((x) => x.id !== id));
  }

  return (
    <div className="vview">
      <h2 className="view-title">Vocabulario guardado <span className="count">{words.length}</span></h2>
      <p className="view-sub">Tu biblioteca personal. Guarda palabras con ⭐ al conversar y repásalas en Flashcards.</p>
      {loading ? <div className="center-pad"><span className="spinner big" /></div> :
        words.length === 0 ? <div className="empty glass">Aún no guardas palabras. Toca una palabra al conversar y pulsa ⭐.</div> :
        <div className="word-list">
          {words.map((w) => (
            <div className="word-row glass" key={w.id}>
              <div className="wr-main">
                <span className="wr-word">{w.word}</span>
                {w.pos && <span className="wr-pos">{w.pos}</span>}
                {w.ipa && <span className="wr-ipa">{w.ipa}</span>}
              </div>
              <div className="wr-tr">{w.translation_es}</div>
              {w.example_de && <div className="wr-ex">{w.example_de} <span className="ex-es">· {w.example_es}</span></div>}
              <div className="wr-foot">
                <span className="wr-date">{new Date(w.learned_at).toLocaleDateString()}</span>
                <button className="wr-del" onClick={() => remove(w.id)} aria-label="Eliminar">🗑</button>
              </div>
            </div>
          ))}
        </div>}
    </div>
  );
}
