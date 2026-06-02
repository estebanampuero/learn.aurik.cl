export type LangCode = "de" | "en";

export type Lang = {
  code: LangCode; label: string; flag: string; name_es: string;
  tutor: string; glyph: string; greeting: string; voices: string[];
};

export type Tutor = {
  id: string; name: string; lang: LangCode; avatar: string; glyph: string;
  gender: "f" | "m"; specialty: string; specialty_es: string; flag: string;
  lang_label: string; greeting: string;
};

export type Scenario = { id: string; kind: string; title: string; emoji: string; desc: string };

export type Vocab = { de: string; es: string };
export type CorrectionItem = { wrong: string; right: string; category?: string };
export type Grammar = { tag: string; title: string; rule: string; example: string };

export type TutorTurn = {
  user_text?: string;
  reply: string;
  reply_translation_es?: string;
  correction?: string | null;
  correction_items?: CorrectionItem[];
  explanation_es?: string;
  similar_examples?: string[];
  grammar?: Grammar | null;
  new_vocab?: Vocab[];
  pronunciation_tip?: string | null;
  level_estimate?: string | null;
  audio_b64?: string;
  xp?: number;
  streak?: number;
  level?: string;
  new_achievements?: Achievement[];
};

export type Message = { role: "user" | "assistant"; content: string; payload?: any };

export type Conversation = {
  id: number; lang: LangCode; tutor_id?: string; tutor?: Tutor; mode: string;
  scenario_id: string; title: string; updated_at?: string;
  greeting?: string; messages?: Message[];
};

export type SavedWord = {
  id: number; lang: LangCode; word: string; pos: string; ipa: string;
  translation_es: string; synonyms: string[]; example_de: string; example_es: string;
  learned_at: string;
};

export type Flashcard = {
  id: number; lang: LangCode; mode: "multiple_choice" | "fill_blank" | "reverse";
  front: string; back: string; options: string[]; hint: string;
};

export type Achievement = {
  code: string; emoji: string; title: string; desc: string;
  unlocked?: boolean; unlocked_at?: string | null;
};

export type WordInfo = {
  word: string; pos: string; ipa: string; translation_es: string;
  synonyms: string[]; example_de: string; example_es: string;
};

export type Dashboard = {
  hours_studied: number; conversations: number; words_learned: number;
  avg_pronunciation: number; level_de: string; level_en: string;
  streak: number; longest_streak: number; xp: number;
};

export type Stats = {
  skills: { skill: string; score: number }[];
  strengths: { skill: string; score: number }[];
  weaknesses: { skill: string; score: number }[];
  frequent_error_categories: { category: string; count: number }[];
};

export type User = { id: number; email: string; name: string; goals: string; level_de: string; level_en: string };
