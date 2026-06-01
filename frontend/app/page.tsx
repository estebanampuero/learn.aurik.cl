"use client";

import { useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const LANGS = [
  { code: "de", label: "Deutsch", flag: "🇩🇪", name_es: "alemán" },
  { code: "en", label: "English", flag: "🇬🇧", name_es: "inglés" },
] as const;
type LangCode = (typeof LANGS)[number]["code"];
type Gender = "f" | "m";

type Vocab = { de: string; es: string };
type TutorTurn = {
  user_text: string;
  reply: string;
  correction: string | null;
  explanation_es: string;
  new_vocab: Vocab[];
  pronunciation_tip: string | null;
};
type WordPop = {
  word: string;
  translation_es?: string;
  synonyms?: string[];
  loading: boolean;
  x: number;
  y: number;
  above: boolean;
};

export default function Page() {
  const [lang, setLang] = useState<LangCode>("de");
  const [voice, setVoice] = useState<Gender>("f");
  const [turns, setTurns] = useState<TutorTurn[]>([]);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [wp, setWp] = useState<WordPop | null>(null);
  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const historyRef = useRef<{ role: string; content: string }[]>([]);

  const current = LANGS.find((l) => l.code === lang)!;

  // Cambiar de idioma reinicia la conversación (no mezclar idiomas en el historial).
  function switchLang(code: LangCode) {
    if (code === lang) return;
    setLang(code);
    setTurns([]);
    historyRef.current = [];
    setWp(null);
  }

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
      fd.append("lang", lang);
      fd.append("voice", voice);
      const res = await fetch(`${API}/api/chat`, { method: "POST", body: fd });
      const data = await res.json();
      if (data.error) { alert(data.error); return; }
      historyRef.current.push({ role: "user", content: data.user_text });
      historyRef.current.push({ role: "assistant", content: data.reply });
      setTurns((t) => [...t, data]);
      if (data.audio_b64) new Audio("data:audio/wav;base64," + data.audio_b64).play();
    } catch {
      alert("Error de conexión con el servidor.");
    } finally {
      setBusy(false);
    }
  }

  async function clickWord(raw: string, context: string, e?: React.MouseEvent) {
    const w = raw.replace(/[.,!?;:„""»«()¿¡…]/g, "").trim();
    if (!w) return;

    // Ancla la burbuja sobre (o bajo) la palabra tocada.
    let x = window.innerWidth / 2;
    let y = 120;
    let above = true;
    if (e) {
      const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
      x = Math.max(140, Math.min(window.innerWidth - 140, r.left + r.width / 2));
      above = r.top > 180; // si no hay espacio arriba, cae debajo
      y = above ? r.top : r.bottom;
    }
    setWp({ word: w, loading: true, x, y, above });

    try {
      const res = await fetch(`${API}/api/word`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ word: w, context, lang }),
      });
      const d = await res.json();
      setWp((p) =>
        p && p.word === w && p.loading
          ? { ...p, translation_es: d.translation_es, synonyms: d.synonyms, loading: false }
          : p
      );
    } catch {
      setWp((p) =>
        p && p.word === w && p.loading
          ? { ...p, translation_es: "(error de conexión)", synonyms: [], loading: false }
          : p
      );
    }
  }

  // Renderiza un texto alemán con cada palabra clickeable.
  function clickable(text: string) {
    return text.split(/(\s+)/).map((tok, i) =>
      /^\s+$/.test(tok) ? (
        tok
      ) : (
        <span key={i} className="word" onClick={(e) => clickWord(tok, text, e)}>
          {tok}
        </span>
      )
    );
  }

  return (
    <div className="wrap">
      <h1>{current.flag} Tutor de {current.name_es}</h1>
      <p className="sub">Habla en {current.name_es} → te corrijo y respondo con voz. Toca cualquier palabra para ver su traducción y sinónimos.</p>

      <div className="controls">
        <div className="seg" role="group" aria-label="Idioma">
          {LANGS.map((l) => (
            <button
              key={l.code}
              className={"seg-btn" + (l.code === lang ? " on" : "")}
              onClick={() => switchLang(l.code)}
            >
              {l.flag} {l.label}
            </button>
          ))}
        </div>
        <div className="seg" role="group" aria-label="Voz del tutor">
          <button className={"seg-btn" + (voice === "f" ? " on" : "")} onClick={() => setVoice("f")}>♀ Mujer</button>
          <button className={"seg-btn" + (voice === "m" ? " on" : "")} onClick={() => setVoice("m")}>♂ Hombre</button>
        </div>
      </div>

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
            <div className="de">{clickable(t.reply)}</div>
            {t.new_vocab?.length > 0 && (
              <div className="vocab">
                {t.new_vocab.map((v, j) => (
                  <span className="chip" key={j} onClick={(e) => clickWord(v.de, t.reply, e)}>{v.de} — {v.es}</span>
                ))}
              </div>
            )}
            {t.pronunciation_tip && <div className="hint">🔊 {t.pronunciation_tip}</div>}
          </div>
        </div>
      ))}

      {wp && (
        <>
          <div className="bubble-overlay" onClick={() => setWp(null)} />
          <div
            className={"bubble " + (wp.above ? "above" : "below")}
            style={{ left: wp.x, top: wp.y }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="bubble-w">{wp.word}</div>
            {wp.loading ? (
              <div className="bubble-loading"><span className="spinner" />buscando…</div>
            ) : (
              <>
                <div className="bubble-tr">🇪🇸 {wp.translation_es}</div>
                {wp.synonyms && wp.synonyms.length > 0 && (
                  <div className="bubble-syn">
                    <span className="label">Sinónimos</span>
                    <div className="vocab">
                      {wp.synonyms.map((s, k) => (
                        <span className="chip" key={k} onClick={(e) => clickWord(s, "", e)}>{s}</span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
            <span className="bubble-arrow" />
          </div>
        </>
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
