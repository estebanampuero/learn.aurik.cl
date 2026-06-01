"use client";

import { useEffect, useRef, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const LANGS = [
  {
    code: "de", label: "Deutsch", flag: "🇩🇪", name_es: "alemán",
    tutor: "Lena", glyph: "DE", avatar: "/tutors/lena.png",
    greeting: "Hallo! Schön, dich zu sehen. Wie geht es dir heute?",
  },
  {
    code: "en", label: "English", flag: "🇬🇧", name_es: "inglés",
    tutor: "Emma", glyph: "EN", avatar: "/tutors/emma.png",
    greeting: "Hi! Great to see you. How are you doing today?",
  },
] as const;
type LangCode = (typeof LANGS)[number]["code"];
type Gender = "f" | "m";
type VoiceState = "idle" | "listening" | "thinking" | "speaking";

type Vocab = { de: string; es: string };
type CorrectionItem = { wrong: string; right: string };
type Grammar = { tag: string; title: string; rule: string; example: string };
type TutorTurn = {
  user_text: string;
  reply: string;
  reply_translation_es: string;
  correction: string | null;
  correction_items: CorrectionItem[];
  explanation_es: string;
  grammar: Grammar | null;
  new_vocab: Vocab[];
  pronunciation_tip: string | null;
  audio_b64?: string;
};
type WordPop = {
  word: string;
  pos?: string;
  ipa?: string;
  translation_es?: string;
  synonyms?: string[];
  example_de?: string;
  example_es?: string;
  loading: boolean;
  x: number;
  y: number;
  above: boolean;
};

export default function Page() {
  const [lang, setLang] = useState<LangCode>("de");
  const [voice, setVoice] = useState<Gender>("f");
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [turns, setTurns] = useState<TutorTurn[]>([]);
  const [state, setState] = useState<VoiceState>("idle");
  const [wp, setWp] = useState<WordPop | null>(null);
  const [langOpen, setLangOpen] = useState(false);
  const [showTrans, setShowTrans] = useState<Record<number, boolean>>({});
  const [openCorr, setOpenCorr] = useState<Record<number, boolean>>({});
  const [draft, setDraft] = useState("");

  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const heldRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const historyRef = useRef<{ role: string; content: string }[]>([]);
  const threadEndRef = useRef<HTMLDivElement | null>(null);

  const current = LANGS.find((l) => l.code === lang)!;
  const busy = state === "thinking";

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, state]);

  // Cambiar de idioma reinicia la conversación (no mezclar idiomas en el historial).
  function switchLang(code: LangCode) {
    setLangOpen(false);
    if (code === lang) return;
    stopAudio();
    setLang(code);
    setTurns([]);
    historyRef.current = [];
    setWp(null);
    setState("idle");
  }

  function stopAudio() {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
  }

  // ===== Push-to-talk =====
  async function pttDown() {
    if (state === "thinking") return;
    if (state === "speaking") { stopAudio(); setState("idle"); return; } // tap = interrumpir
    heldRef.current = true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!heldRef.current) { stream.getTracks().forEach((t) => t.stop()); return; } // soltó antes de tiempo
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size > 1200) sendAudio(blob);
        else setState("idle");
      };
      recRef.current = rec;
      rec.start();
      setState("listening");
    } catch {
      heldRef.current = false;
      setState("idle");
      alert("No pude acceder al micrófono. Usa el campo de texto de abajo.");
    }
  }

  function pttUp() {
    if (!heldRef.current) return;
    heldRef.current = false;
    const rec = recRef.current;
    if (rec && rec.state !== "inactive") {
      rec.stop();
      recRef.current = null;
      setState("thinking");
    } else {
      setState("idle");
    }
  }

  async function sendAudio(blob: Blob) {
    const fd = new FormData();
    fd.append("audio", blob, "speech.webm");
    await postChat(fd);
  }

  async function sendText() {
    const t = draft.trim();
    if (!t || busy) return;
    setDraft("");
    setState("thinking");
    const fd = new FormData();
    fd.append("text", t);
    await postChat(fd);
  }

  async function postChat(fd: FormData) {
    fd.append("history", JSON.stringify(historyRef.current));
    fd.append("lang", lang);
    fd.append("voice", voice);
    try {
      const res = await fetch(`${API}/api/chat`, { method: "POST", body: fd });
      const data: TutorTurn & { error?: string } = await res.json();
      if (data.error) { alert(data.error); setState("idle"); return; }
      historyRef.current.push({ role: "user", content: data.user_text });
      historyRef.current.push({ role: "assistant", content: data.reply });
      setTurns((t) => [...t, data]);
      playReply(data);
    } catch {
      alert("Error de conexión con el servidor.");
      setState("idle");
    }
  }

  function playReply(t: TutorTurn) {
    if (!t.audio_b64) { setState("idle"); return; }
    stopAudio();
    const a = new Audio("data:audio/wav;base64," + t.audio_b64);
    audioRef.current = a;
    setState("speaking");
    a.onended = () => { if (audioRef.current === a) { audioRef.current = null; setState("idle"); } };
    a.play().catch(() => setState("idle"));
  }

  async function clickWord(raw: string, context: string, e: React.MouseEvent) {
    const w = raw.replace(/[.,!?;:„""»«()¿¡…]/g, "").trim();
    if (!w) return;
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const x = Math.max(150, Math.min(window.innerWidth - 150, r.left + r.width / 2));
    const above = r.top > 240;
    const y = above ? r.top : r.bottom;
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
          ? { ...p, ...d, loading: false }
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

  // Renderiza un texto con cada palabra clickeable.
  function clickable(text: string, key: string) {
    return text.split(/(\s+)/).map((tok, i) =>
      /^\s+$/.test(tok) || !tok ? (
        tok
      ) : (
        <span key={key + i} className="word" onClick={(e) => clickWord(tok, text, e)}>
          {tok}
        </span>
      )
    );
  }

  const statusText: Record<VoiceState, string> = {
    idle: "En línea",
    listening: "Escuchando…",
    thinking: "Pensando…",
    speaking: `${current.tutor} está hablando`,
  };
  const dockHint: Record<VoiceState, string> = {
    idle: "Mantén pulsado el orbe para hablar",
    listening: "Suelta para enviar",
    thinking: "Procesando tu mensaje…",
    speaking: "Toca el orbe para interrumpir",
  };

  return (
    <>
      <div className="mesh-bg" />
      <div className="app">
        {/* ===== Cabecera ===== */}
        <header className="header glass">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="avatar" src={current.avatar} alt={current.tutor} />
          <div className="head-id">
            <span className="head-name">{current.tutor}</span>
            <span className="head-status">
              <span className={"dot " + (state === "idle" ? "" : state)} />
              {statusText[state]}
            </span>
          </div>

          <div className="head-controls">
            <div className="seg voice glass" role="group" aria-label="Voz del tutor">
              <button className={"seg-btn" + (voice === "f" ? " on" : "")} onClick={() => setVoice("f")} aria-pressed={voice === "f"}>♀</button>
              <button className={"seg-btn" + (voice === "m" ? " on" : "")} onClick={() => setVoice("m")} aria-pressed={voice === "m"}>♂</button>
            </div>

            <button className="icon-btn" onClick={() => setTheme(theme === "light" ? "dark" : "light")} aria-label="Cambiar tema">
              {theme === "light" ? "🌙" : "☀️"}
            </button>

            <div className="lang-menu">
              <button className="lang-trigger" onClick={() => setLangOpen((o) => !o)} aria-haspopup="listbox" aria-expanded={langOpen}>
                <span>{current.flag}</span> {current.label} <span aria-hidden>⌄</span>
              </button>
              {langOpen && (
                <div className="lang-pop glass" role="listbox">
                  {LANGS.map((l) => (
                    <button key={l.code} className="lang-opt" role="option" aria-selected={l.code === lang} onClick={() => switchLang(l.code)}>
                      <span className="o-flag">{l.flag}</span>
                      <span className="o-name">{l.label}</span>
                      <span className="o-tutor">{l.tutor}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </header>

        {/* ===== Hilo de conversación ===== */}
        <div className="thread">
          {turns.length === 0 ? (
            <div className="welcome">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img className="welcome-avatar" src={current.avatar} alt={current.tutor} />
              <h1>Hola, soy {current.tutor}</h1>
              <p className="lead">{clickable(current.greeting, "greet")}</p>
              <p>Soy tu tutor/a de {current.name_es}. Me adapto a tu nivel: mantén pulsado el orbe y háblame, o escríbeme abajo. Toca cualquier palabra para ver su traducción.</p>
            </div>
          ) : (
            <div className="daypill glass">Hoy · {current.tutor}</div>
          )}

          {turns.map((t, i) => (
            <div key={i}>
              {/* turno del usuario */}
              <div className="user">
                <div className="user-bubble">{t.user_text}</div>
                {t.correction && (
                  <div className="corr">
                    <button
                      className="corr-pill"
                      aria-expanded={!!openCorr[i]}
                      onClick={() => setOpenCorr((o) => ({ ...o, [i]: !o[i] }))}
                    >
                      ✏ {t.correction_items?.length || 1} {(t.correction_items?.length || 1) === 1 ? "corrección" : "correcciones"}
                      <span className="chev" aria-hidden>⌄</span>
                    </button>
                    {openCorr[i] && (
                      <div className="corr-card glass">
                        <div className="diff">
                          {(t.correction_items?.length
                            ? t.correction_items
                            : [{ wrong: t.user_text, right: t.correction }]
                          ).map((c, j) => (
                            <div className="diff-row" key={j}>
                              <span className="wrong">{c.wrong}</span>
                              <span className="arrow" aria-hidden>→</span>
                              <span className="right">{c.right}</span>
                            </div>
                          ))}
                        </div>
                        {t.explanation_es && <div className="corr-exp">{t.explanation_es}</div>}
                        {t.grammar && (
                          <div className="grammar">
                            <span className="grammar-tag">{t.grammar.tag}</span>
                            <span className="grammar-title">{t.grammar.title}</span>
                            <span className="grammar-rule">{t.grammar.rule}</span>
                            {t.grammar.example && <span className="grammar-ex">{t.grammar.example}</span>}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* turno del tutor */}
              <div className="ai">
                <div className="ai-top">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img className="ai-avatar" src={current.avatar} alt={current.tutor} />
                  <span className="ai-name">{current.tutor}</span>
                  {t.audio_b64 && (
                    <button className="ai-play" onClick={() => playReply(t)} aria-label="Reproducir de nuevo">▶</button>
                  )}
                </div>
                <div className="lead">{clickable(t.reply, `r${i}-`)}</div>
                <button className="ai-trans-btn" onClick={() => setShowTrans((s) => ({ ...s, [i]: !s[i] }))}>
                  {showTrans[i] ? "Ocultar traducción" : "Ver traducción"}
                </button>
                {showTrans[i] && <div className="ai-trans">{t.reply_translation_es}</div>}
                {t.new_vocab?.length > 0 && (
                  <>
                    <div className="vocab-label">Vocabulario nuevo</div>
                    <div className="vocab">
                      {t.new_vocab.map((v, j) => (
                        <span className="chip" key={j} onClick={(e) => clickWord(v.de, t.reply, e)}>
                          {v.de} <span className="c-es">· {v.es}</span>
                        </span>
                      ))}
                    </div>
                  </>
                )}
                {t.pronunciation_tip && <div className="hint">🔊 {t.pronunciation_tip}</div>}
              </div>
            </div>
          ))}
          <div ref={threadEndRef} />
        </div>

        {/* ===== Dock de voz (orbe PTT + fallback de texto) ===== */}
        <div className="dock">
          <div className={"dock-status" + (state !== "idle" ? " live" : "")}>{dockHint[state]}</div>

          <div className="orb-wrap">
            {state === "idle" && <div className="orb-halo" />}
            {state === "listening" && (
              <>
                <div className="orb-ring ping" />
                <div className="orb-ring ping2" />
              </>
            )}
            {state === "thinking" && <div className="orb-think" />}
            <button
              className="orb-btn"
              aria-label="Mantén pulsado para hablar"
              onContextMenu={(e) => e.preventDefault()}
              onPointerDown={(e) => { e.preventDefault(); pttDown(); }}
              onPointerUp={(e) => { e.preventDefault(); pttUp(); }}
              onPointerLeave={() => pttUp()}
              onPointerCancel={() => pttUp()}
            >
              <div className={"orb-core is-" + state}>
                {(state === "listening" || state === "speaking") ? (
                  <div className="orb-eq"><span /><span /><span /><span /><span /></div>
                ) : (
                  <span className="orb-glyph">{state === "thinking" ? "" : "🎙"}</span>
                )}
              </div>
            </button>
          </div>

          <div className="text-fallback glass">
            <input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") sendText(); }}
              placeholder={`Escribe en ${current.name_es}…`}
              disabled={busy}
            />
            <button className="send-btn" onClick={sendText} disabled={busy || !draft.trim()} aria-label="Enviar">↑</button>
          </div>
        </div>
      </div>

      {/* ===== Popover de palabra ===== */}
      {wp && (
        <>
          <div className="pop-overlay" onClick={() => setWp(null)} />
          <div
            className={"pop glass " + (wp.above ? "above" : "below")}
            style={{ left: wp.x, top: wp.y }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="pop-w">{wp.word}</div>
            {wp.loading ? (
              <div className="pop-loading"><span className="spinner" /> buscando…</div>
            ) : (
              <>
                {(wp.pos || wp.ipa) && (
                  <div className="pop-meta">
                    {wp.pos && <span className="pop-pos">{wp.pos}</span>}
                    {wp.ipa && <span className="pop-ipa">{wp.ipa}</span>}
                  </div>
                )}
                <div className="pop-tr"><span className="flag">🇪🇸</span>{wp.translation_es}</div>
                {wp.example_de && (
                  <div className="pop-ex">
                    <div className="ex-de">{wp.example_de}</div>
                    {wp.example_es && <div className="ex-es">{wp.example_es}</div>}
                  </div>
                )}
                {wp.synonyms && wp.synonyms.length > 0 && (
                  <>
                    <span className="pop-syn-label">Sinónimos</span>
                    <div className="vocab">
                      {wp.synonyms.map((s, k) => (
                        <span className="chip" key={k} onClick={(e) => clickWord(s, "", e)}>{s}</span>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        </>
      )}
    </>
  );
}
