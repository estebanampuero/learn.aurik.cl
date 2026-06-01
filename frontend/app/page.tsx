"use client";

import { useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Vocab = { de: string; es: string };
type TutorTurn = {
  user_text: string;
  reply_de: string;
  correction: string | null;
  explanation_es: string;
  new_vocab: Vocab[];
  pronunciation_tip: string | null;
};
type WordPop = {
  word: string;
  translation_es?: string;
  synonyms_de?: string[];
  loading: boolean;
};

export default function Page() {
  const [turns, setTurns] = useState<TutorTurn[]>([]);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [wp, setWp] = useState<WordPop | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const historyRef = useRef<{ role: string; content: string }[]>([]);

  async function startRec() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const rec = new MediaRecorder(stream);
    chunksRef.current = [];
    rec.ondataavailable = (e) => chunksRef.current.push(e.data);
    rec.onstop = () => send(new Blob(chunksRef.current, { type: "audio/webm" }));
    recRef.current = rec;
    rec.start();
    setRecording(true);
  }

  function stopRec() {
    recRef.current?.stop();
    recRef.current?.stream.getTracks().forEach((t) => t.stop());
    setRecording(false);
  }

  async function send(blob: Blob) {
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append("audio", blob, "speech.webm");
      fd.append("history", JSON.stringify(historyRef.current));
      const res = await fetch(`${API}/api/chat`, { method: "POST", body: fd });
      const data = await res.json();
      if (data.error) { alert(data.error); return; }
      historyRef.current.push({ role: "user", content: data.user_text });
      historyRef.current.push({ role: "assistant", content: data.reply_de });
      setTurns((t) => [...t, data]);
      if (data.audio_b64) new Audio("data:audio/wav;base64," + data.audio_b64).play();
    } catch {
      alert("Error de conexión con el servidor.");
    } finally {
      setBusy(false);
    }
  }

  async function clickWord(raw: string, context: string) {
    const w = raw.replace(/[.,!?;:„""»«()¿¡…]/g, "").trim();
    if (!w) return;
    setWp({ word: w, loading: true });
    try {
      const res = await fetch(`${API}/api/word`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word: w, context }),
      });
      const d = await res.json();
      setWp({ word: w, translation_es: d.translation_es, synonyms_de: d.synonyms_de, loading: false });
    } catch {
      setWp({ word: w, translation_es: "(error de conexión)", synonyms_de: [], loading: false });
    }
  }

  // Renderiza un texto alemán con cada palabra clickeable.
  function clickable(text: string) {
    return text.split(/(\s+)/).map((tok, i) =>
      /^\s+$/.test(tok) ? (
        tok
      ) : (
        <span key={i} className="word" onClick={() => clickWord(tok, text)}>
          {tok}
        </span>
      )
    );
  }

  return (
    <div className="wrap">
      <h1>🇩🇪 Deutsch-Tutor</h1>
      <p className="sub">Habla en alemán → te corrijo y respondo con voz. Toca cualquier palabra alemana para ver su traducción y sinónimos.</p>

      {turns.map((t, i) => (
        <div key={i}>
          <div className="msg user">
            <div className="label">Du (lo que dijiste)</div>
            <div>{t.user_text}</div>
            {t.correction && (
              <div className="correction">✏️ {clickable(t.correction)}<br /><small>{t.explanation_es}</small></div>
            )}
          </div>
          <div className="msg tutor">
            <div className="label">Tutor</div>
            <div className="de">{clickable(t.reply_de)}</div>
            {t.new_vocab?.length > 0 && (
              <div className="vocab">
                {t.new_vocab.map((v, j) => (
                  <span className="chip" key={j} onClick={() => clickWord(v.de, t.reply_de)}>{v.de} — {v.es}</span>
                ))}
              </div>
            )}
            {t.pronunciation_tip && <div className="hint">🔊 {t.pronunciation_tip}</div>}
          </div>
        </div>
      ))}

      {wp && (
        <div className="wordpop" onClick={() => setWp(null)}>
          <div className="wordpop-inner" onClick={(e) => e.stopPropagation()}>
            <button className="wordpop-x" onClick={() => setWp(null)}>×</button>
            <div className="wordpop-w">{wp.word}</div>
            {wp.loading ? (
              <div className="wordpop-loading">buscando…</div>
            ) : (
              <>
                <div className="wordpop-tr">🇪🇸 {wp.translation_es}</div>
                {wp.synonyms_de && wp.synonyms_de.length > 0 && (
                  <div className="wordpop-syn">
                    <span className="label">Sinónimos</span>
                    <div className="vocab">
                      {wp.synonyms_de.map((s, k) => (
                        <span className="chip" key={k} onClick={() => clickWord(s, "")}>{s}</span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      <button
        className={"mic" + (recording ? " rec" : "")}
        disabled={busy}
        onClick={recording ? stopRec : startRec}
      >
        {busy ? "…" : recording ? "■" : "🎤"}
      </button>
      <p className="hint">{busy ? "Procesando…" : recording ? "Grabando… toca para enviar" : "Toca el micrófono y habla en alemán"}</p>
    </div>
  );
}
