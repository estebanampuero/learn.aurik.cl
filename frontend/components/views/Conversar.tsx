"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { Conversation, LangCode, Message, Tutor, TutorTurn, WordInfo } from "@/lib/types";

type VoiceState = "idle" | "listening" | "thinking" | "speaking";

type WordPop = (Partial<WordInfo> & {
  word: string; loading: boolean; x: number; y: number; above: boolean; saved?: boolean;
});

export default function Conversar({ lang, pending, onConsumePending }: {
  lang: LangCode; pending: Conversation | null; onConsumePending: () => void;
}) {
  const [tutors, setTutors] = useState<Tutor[]>([]);
  const [conv, setConv] = useState<Conversation | null>(null);
  const [tutor, setTutor] = useState<Tutor | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [state, setState] = useState<VoiceState>("idle");
  const [wp, setWp] = useState<WordPop | null>(null);
  const [draft, setDraft] = useState("");
  const [showTrans, setShowTrans] = useState<Record<number, boolean>>({});
  const [openCorr, setOpenCorr] = useState<Record<number, boolean>>({});
  const [toast, setToast] = useState<string>("");

  const recRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const heldRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const busy = state === "thinking";

  // Catálogo de tutores del idioma.
  useEffect(() => {
    api.tutors(lang).then((d) => setTutors(d.tutors)).catch(() => {});
  }, [lang]);

  // Abrir conversación pendiente (lección/roleplay/examen/continuar).
  useEffect(() => {
    if (pending) {
      loadConversation(pending.id);
      onConsumePending();
    }
  }, [pending]);

  // Si cambia el idioma y no hay conversación, limpia.
  useEffect(() => {
    if (!pending) { setConv(null); setMessages([]); setTutor(null); }
  }, [lang]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, state]);

  function flash(msg: string) { setToast(msg); setTimeout(() => setToast(""), 3500); }

  async function loadConversation(id: number) {
    const full = await api.conversation(id);
    setConv(full);
    setTutor(full.tutor || null);
    setMessages(full.messages || []);
    setState("idle");
  }

  async function startWith(t: Tutor) {
    const c = await api.startConversation({ lang, tutor_id: t.id, mode: "chat" });
    setConv(c);
    setTutor(t);
    setMessages([{ role: "assistant", content: c.greeting || "", payload: { reply: c.greeting } }]);
    setState("idle");
  }

  function stopAudio() { if (audioRef.current) { audioRef.current.pause(); audioRef.current = null; } }

  // ===== Push-to-talk =====
  async function pttDown() {
    if (!conv || state === "thinking") return;
    if (state === "speaking") { stopAudio(); setState("idle"); return; }
    heldRef.current = true;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!heldRef.current) { stream.getTracks().forEach((t) => t.stop()); return; }
      const rec = new MediaRecorder(stream);
      chunksRef.current = [];
      rec.ondataavailable = (e) => e.data.size && chunksRef.current.push(e.data);
      rec.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size > 1200) send({ audio: blob }); else setState("idle");
      };
      recRef.current = rec;
      rec.start();
      setState("listening");
    } catch {
      heldRef.current = false; setState("idle");
      flash("No pude acceder al micrófono. Usa el campo de texto.");
    }
  }
  function pttUp() {
    if (!heldRef.current) return;
    heldRef.current = false;
    const rec = recRef.current;
    if (rec && rec.state !== "inactive") { rec.stop(); recRef.current = null; setState("thinking"); }
    else setState("idle");
  }

  async function send({ audio, text }: { audio?: Blob; text?: string }) {
    if (!conv) return;
    setState("thinking");
    const fd = new FormData();
    fd.append("conversation_id", String(conv.id));
    if (audio) fd.append("audio", audio, "speech.webm");
    if (text) fd.append("text", text);
    try {
      const data = await api.chat(fd);
      if ((data as any).error) { flash((data as any).error); setState("idle"); return; }
      const turn = data as TutorTurn;
      setMessages((m) => [
        ...m,
        { role: "user", content: turn.user_text || text || "", payload: turn },
        { role: "assistant", content: turn.reply, payload: turn },
      ]);
      const bits: string[] = [`+${turn.xp ?? 0} XP`];
      if (turn.level) bits.push(`Nivel ${turn.level}`);
      if (turn.new_achievements?.length) bits.push("🏆 " + turn.new_achievements.map((a) => a.title).join(", "));
      flash(bits.join(" · "));
      playReply(turn);
    } catch (e: any) {
      flash(e.message || "Error de conexión."); setState("idle");
    }
  }

  function sendText() {
    const t = draft.trim();
    if (!t || busy || !conv) return;
    setDraft("");
    send({ text: t });
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
    const above = r.top > 260;
    setWp({ word: w, loading: true, x, y: above ? r.top : r.bottom, above });
    try {
      const d = await api.word({ word: w, context, lang });
      setWp((p) => (p && p.word === w && p.loading ? { ...p, ...d, loading: false } : p));
    } catch {
      setWp((p) => (p && p.word === w && p.loading ? { ...p, translation_es: "(error)", loading: false } : p));
    }
  }

  async function saveCurrentWord() {
    if (!wp || wp.loading) return;
    try {
      const r = await api.saveWord({
        lang, word: wp.word, pos: wp.pos, ipa: wp.ipa, translation_es: wp.translation_es,
        synonyms: wp.synonyms || [], example_de: wp.example_de, example_es: wp.example_es,
        source_conversation_id: conv?.id,
      });
      setWp((p) => (p ? { ...p, saved: true } : p));
      flash(r.saved ? "⭐ Palabra guardada" : "Ya estaba guardada");
    } catch { flash("No se pudo guardar."); }
  }

  function clickable(text: string, key: string) {
    return text.split(/(\s+)/).map((tok, i) =>
      /^\s+$/.test(tok) || !tok ? tok : (
        <span key={key + i} className="word" onClick={(e) => clickWord(tok, text, e)}>{tok}</span>
      ));
  }

  const statusText: Record<VoiceState, string> = {
    idle: "Mantén pulsado para hablar", listening: "Escuchando…",
    thinking: "Pensando…", speaking: `${tutor?.name || "Tutor"} está hablando`,
  };

  // ── Sin conversación: selección de tutor ──
  if (!conv) {
    return (
      <div className="picker">
        <h2 className="view-title">Elige tu tutor</h2>
        <p className="view-sub">Cada profesor tiene una especialidad. Puedes cambiar cuando quieras.</p>
        <div className="tutor-grid">
          {tutors.map((t) => (
            <button key={t.id} className="tutor-card glass" onClick={() => startWith(t)}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={t.avatar} alt={t.name} className="tutor-av" />
              <div className="tutor-name">{t.name}</div>
              <div className="tutor-spec">{t.specialty_es}</div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="conversar">
      {toast && <div className="toast glass">{toast}</div>}

      {/* Cabecera de conversación */}
      <div className="conv-head glass">
        {tutor && <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="avatar" src={tutor.avatar} alt={tutor.name} />
          <div className="head-id">
            <span className="head-name">{tutor.name} <span className="spec-badge">{tutor.specialty_es}</span></span>
            <span className="head-status"><span className={"dot " + (state === "idle" ? "" : state)} />{statusText[state]}</span>
          </div>
        </>}
        <div className="head-controls">
          {conv.scenario_id && <span className="scenario-chip">{conv.title}</span>}
          <button className="btn-ghost" onClick={() => { setConv(null); setMessages([]); }}>Nueva</button>
        </div>
      </div>

      {/* Hilo */}
      <div className="thread">
        {(() => {
          const out: any[] = [];
          messages.forEach((m, i) => {
            if (m.role === "assistant") {
              const t: TutorTurn = m.payload || { reply: m.content };
              out.push(
                <div className="ai" key={"a" + i}>
                  <div className="ai-top">
                    {tutor && /* eslint-disable-next-line @next/next/no-img-element */
                      <img className="ai-avatar" src={tutor.avatar} alt="" />}
                    <span className="ai-name">{tutor?.name}</span>
                    {t.level_estimate && <span className="level-badge">{t.level_estimate}</span>}
                    {t.audio_b64 && <button className="ai-play" onClick={() => playReply(t)}>▶</button>}
                  </div>
                  <div className="lead">{clickable(t.reply, `r${i}-`)}</div>
                  {t.reply_translation_es && <>
                    <button className="ai-trans-btn" onClick={() => setShowTrans((s) => ({ ...s, [i]: !s[i] }))}>
                      {showTrans[i] ? "Ocultar traducción" : "Ver traducción"}
                    </button>
                    {showTrans[i] && <div className="ai-trans">{t.reply_translation_es}</div>}
                  </>}
                  {!!t.new_vocab?.length && <>
                    <div className="vocab-label">Vocabulario nuevo</div>
                    <div className="vocab">
                      {t.new_vocab!.map((v, j) => (
                        <span className="chip" key={j} onClick={(e) => clickWord(v.de, t.reply, e)}>
                          {v.de} <span className="c-es">· {v.es}</span>
                        </span>
                      ))}
                    </div>
                  </>}
                  {t.pronunciation_tip && <div className="hint">🔊 {t.pronunciation_tip}</div>}
                </div>
              );
            } else {
              // correción viene en el siguiente assistant (payload de su turno)
              const next: TutorTurn | undefined = messages[i + 1]?.payload;
              out.push(
                <div className="user" key={"u" + i}>
                  <div className="user-bubble">{m.content}</div>
                  {next?.correction && (
                    <div className="corr">
                      <button className="corr-pill" aria-expanded={!!openCorr[i]} onClick={() => setOpenCorr((o) => ({ ...o, [i]: !o[i] }))}>
                        ✏ {(next.correction_items?.length || 1)} {(next.correction_items?.length || 1) === 1 ? "corrección" : "correcciones"} <span className="chev">⌄</span>
                      </button>
                      {openCorr[i] && (
                        <div className="corr-card glass">
                          <div className="diff">
                            {(next.correction_items?.length ? next.correction_items : [{ wrong: m.content, right: next.correction! }]).map((c, j) => (
                              <div className="diff-row" key={j}>
                                <span className="wrong">{c.wrong}</span><span className="arrow">→</span><span className="right">{c.right}</span>
                              </div>
                            ))}
                          </div>
                          {next.explanation_es && <div className="corr-exp">{next.explanation_es}</div>}
                          {!!next.similar_examples?.length && (
                            <div className="examples">
                              <span className="ex-label">Ejemplos similares</span>
                              {next.similar_examples!.map((ex, k) => <div className="ex-line" key={k}>{clickable(ex, `ex${i}-${k}-`)}</div>)}
                            </div>
                          )}
                          {next.grammar && (
                            <div className="grammar">
                              <span className="grammar-tag">{next.grammar.tag}</span>
                              <span className="grammar-title">{next.grammar.title}</span>
                              <span className="grammar-rule">{next.grammar.rule}</span>
                              {next.grammar.example && <span className="grammar-ex">{next.grammar.example}</span>}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            }
          });
          return out;
        })()}
        <div ref={endRef} />
      </div>

      {/* Dock */}
      <div className="dock">
        <div className={"dock-status" + (state !== "idle" ? " live" : "")}>{statusText[state]}</div>
        <div className="orb-wrap">
          {state === "idle" && <div className="orb-halo" />}
          {state === "listening" && <><div className="orb-ring ping" /><div className="orb-ring ping2" /></>}
          {state === "thinking" && <div className="orb-think" />}
          <button className="orb-btn" aria-label="Mantén pulsado para hablar"
            onContextMenu={(e) => e.preventDefault()}
            onPointerDown={(e) => { e.preventDefault(); pttDown(); }}
            onPointerUp={(e) => { e.preventDefault(); pttUp(); }}
            onPointerLeave={() => pttUp()} onPointerCancel={() => pttUp()}>
            <div className={"orb-core is-" + state}>
              {(state === "listening" || state === "speaking")
                ? <div className="orb-eq"><span /><span /><span /><span /><span /></div>
                : <span className="orb-glyph">{state === "thinking" ? "" : "🎙"}</span>}
            </div>
          </button>
        </div>
        <div className="text-fallback glass">
          <input value={draft} onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") sendText(); }}
            placeholder={`Escribe en ${lang === "de" ? "alemán" : "inglés"}…`} disabled={busy} />
          <button className="send-btn" onClick={sendText} disabled={busy || !draft.trim()}>↑</button>
        </div>
      </div>

      {/* Popover de palabra */}
      {wp && (
        <>
          <div className="pop-overlay" onClick={() => setWp(null)} />
          <div className={"pop glass " + (wp.above ? "above" : "below")} style={{ left: wp.x, top: wp.y }} onClick={(e) => e.stopPropagation()}>
            <div className="pop-w">{wp.word}</div>
            {wp.loading ? <div className="pop-loading"><span className="spinner" /> buscando…</div> : (
              <>
                {(wp.pos || wp.ipa) && <div className="pop-meta">{wp.pos && <span className="pop-pos">{wp.pos}</span>}{wp.ipa && <span className="pop-ipa">{wp.ipa}</span>}</div>}
                <div className="pop-tr"><span className="flag">🇪🇸</span>{wp.translation_es}</div>
                {wp.example_de && <div className="pop-ex"><div className="ex-de">{wp.example_de}</div>{wp.example_es && <div className="ex-es">{wp.example_es}</div>}</div>}
                {!!wp.synonyms?.length && <><span className="pop-syn-label">Sinónimos</span><div className="vocab">{wp.synonyms!.map((s, k) => <span className="chip" key={k} onClick={(e) => clickWord(s, "", e)}>{s}</span>)}</div></>}
                <button className="btn-save" onClick={saveCurrentWord} disabled={wp.saved}>{wp.saved ? "✓ Guardada" : "⭐ Guardar palabra"}</button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  );
}
