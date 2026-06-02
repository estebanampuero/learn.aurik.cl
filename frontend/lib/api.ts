// Cliente tipado del backend. Maneja el token JWT (localStorage) y FormData/JSON.
import type {
  Lang, Tutor, Scenario, Conversation, TutorTurn, SavedWord, Flashcard,
  Achievement, WordInfo, Dashboard, Stats, User, Quest, LevelInfo,
  ExamMeta, ExamTask, ExamGrade, ListeningRound, SentenceRound, MatchPair,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "sona_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}
export function setToken(t: string | null) {
  if (typeof window === "undefined") return;
  if (t) localStorage.setItem(TOKEN_KEY, t);
  else localStorage.removeItem(TOKEN_KEY);
}

async function req<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
  const headers = new Headers(opts.headers || {});
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.error || `Error ${res.status}`);
  return data as T;
}

function jsonReq<T = any>(path: string, method: string, body: any): Promise<T> {
  return req<T>(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export const api = {
  // auth
  register: (b: { email: string; password: string; name?: string; goals?: string }) =>
    jsonReq<{ token: string; user: User }>("/api/auth/register", "POST", b),
  login: (b: { email: string; password: string }) =>
    jsonReq<{ token: string; user: User }>("/api/auth/login", "POST", b),
  me: () => req<User>("/api/auth/me"),

  // catálogos
  langs: () => req<{ default: string; langs: Lang[] }>("/api/langs"),
  tutors: (lang: string) => req<{ tutors: Tutor[] }>(`/api/tutors?lang=${lang}`),
  lessons: () => req<{ lessons: Scenario[] }>("/api/lessons"),
  roleplays: () => req<{ roleplays: Scenario[] }>("/api/roleplays"),
  exams: (lang: string) => req<{ exams: ExamMeta[] }>(`/api/exams?lang=${lang}`),

  // conversaciones
  startConversation: (b: { lang: string; tutor_id?: string; mode?: string; scenario_id?: string }) =>
    jsonReq<Conversation>("/api/conversations", "POST", b),
  conversations: () => req<{ conversations: Conversation[] }>("/api/conversations"),
  conversation: (id: number) => req<Conversation>(`/api/conversations/${id}`),
  deleteConversation: (id: number) => req<{ ok: boolean }>(`/api/conversations/${id}`, { method: "DELETE" }),

  chat: (fd: FormData) => req<TutorTurn & { error?: string }>("/api/chat", { method: "POST", body: fd }),

  // palabra / traducción
  word: (b: { word: string; context?: string; lang: string }) => jsonReq<WordInfo>("/api/word", "POST", b),
  translate: (b: { text: string; mode: string; lang: string }) =>
    jsonReq<{ translation_es: string; note: string }>("/api/translate", "POST", b),

  // vocabulario
  saveWord: (b: any) => jsonReq<{ saved: boolean; id?: number; new_achievements?: Achievement[] }>("/api/vocab", "POST", b),
  vocab: (lang = "") => req<{ vocab: SavedWord[] }>(`/api/vocab${lang ? `?lang=${lang}` : ""}`),
  deleteWord: (id: number) => req<{ ok: boolean }>(`/api/vocab/${id}`, { method: "DELETE" }),

  // flashcards
  generateFlashcards: (lang: string) => req<{ generated: number }>(`/api/flashcards/generate?lang=${lang}`, { method: "POST" }),
  flashcards: (lang = "") => req<{ flashcards: Flashcard[] }>(`/api/flashcards${lang ? `?lang=${lang}` : ""}`),
  reviewFlashcard: (id: number, correct: boolean) =>
    jsonReq<{ ok: boolean; next_due_days: number; xp: number }>(`/api/flashcards/${id}/review`, "POST", { correct }),

  // pronunciación
  pronunciation: (fd: FormData) => req<any>("/api/pronunciation", { method: "POST", body: fd }),

  // progreso
  dashboard: () => req<Dashboard>("/api/dashboard"),
  stats: (lang: string) => req<Stats>(`/api/stats?lang=${lang}`),
  achievements: () => req<{ achievements: Achievement[] }>("/api/achievements"),
  streak: () => req<{ current: number; longest: number; last_active: string | null }>("/api/streak"),

  // premium
  makeStudyPlan: (lang: string) => req<{ plan: any }>(`/api/study-plan?lang=${lang}`, { method: "POST" }),
  studyPlan: () => req<{ plan: any }>("/api/study-plan"),
  makeWeeklyReport: (lang: string) => req<{ report: any }>(`/api/report/weekly?lang=${lang}`, { method: "POST" }),
  reports: () => req<{ reports: any[] }>("/api/reports"),

  // gamificación
  quests: () => req<{ quests: Quest[]; level_info: LevelInfo }>("/api/quests"),
  premium: () => req<{ is_premium: boolean; features: { key: string; title: string }[] }>("/api/premium"),

  // juegos
  gameVoice: (lang: string) => req<{ phrases: string[] }>(`/api/games/voice?lang=${lang}`),
  gameListening: (lang: string) => req<{ rounds: ListeningRound[] }>(`/api/games/listening?lang=${lang}`),
  gameSentence: (lang: string) => req<{ rounds: SentenceRound[] }>(`/api/games/sentence?lang=${lang}`),
  gameMatch: (lang: string) => req<{ pairs: MatchPair[] }>(`/api/games/match?lang=${lang}`),
  gameScore: (b: { game: string; correct: number; total: number }) =>
    jsonReq<{ xp: number; new_achievements: Achievement[] }>("/api/games/score", "POST", b),

  // examen CEFR
  startExam: (b: { exam_id: string; lang: string }) =>
    jsonReq<{ session_id: number; exam: ExamMeta; tasks: ExamTask[] }>("/api/exams/start", "POST", b),
  gradeExam: (sessionId: number, answers: string[]) =>
    jsonReq<{ result: ExamGrade; xp: number; new_achievements: Achievement[]; level: string }>(`/api/exams/${sessionId}/grade`, "POST", { answers }),
  transcribe: (fd: FormData) => req<{ text: string }>("/api/transcribe", { method: "POST", body: fd }),
};

export { BASE };
