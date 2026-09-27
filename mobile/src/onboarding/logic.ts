/**
 * Pure onboarding helpers. The server owns the questions and ALL scoring; nothing here computes
 * traits or scores. These helpers only handle navigation, draft merging and basic input checks
 * (so the user gets immediate feedback; the server re-validates everything).
 */
import type { ApiError } from '../api/errors';
import type {
  AnswerValue,
  Answers,
  OnboardingState,
  Question,
  QuestionnaireDefinition,
  QuestionnaireSection,
} from '../api/types';
import type { LocalDraft } from './draftStorage';

export function questionIndex(def: QuestionnaireDefinition): Map<string, Question> {
  const map = new Map<string, Question>();
  for (const s of def.sections) for (const q of s.questions) map.set(q.id, q);
  return map;
}

export function isAnswered(question: Question, value: AnswerValue | undefined): boolean {
  if (value === undefined || value === null) return false;
  switch (question.type) {
    case 'scale':
      return typeof value === 'number';
    case 'single_choice':
      return typeof value === 'string' && value.length > 0;
    case 'multiple_choice':
      return Array.isArray(value) && value.length > 0;
    case 'text':
      return typeof value === 'string' && value.trim().length > 0;
    default:
      return false;
  }
}

/** Returns a user-facing problem with a value, or null if it looks acceptable. */
export function validateAnswer(question: Question, value: AnswerValue | undefined): string | null {
  if (!isAnswered(question, value)) {
    return question.required ? 'Please answer this question.' : null;
  }
  switch (question.type) {
    case 'scale': {
      const n = value as number;
      const min = question.scale?.min ?? 1;
      const max = question.scale?.max ?? 5;
      if (!Number.isInteger(n) || n < min || n > max) return `Choose a value from ${min} to ${max}.`;
      return null;
    }
    case 'single_choice':
      if (question.options && !question.options.includes(value as string)) return 'Choose one of the options.';
      return null;
    case 'multiple_choice':
      if (question.options && (value as string[]).some((v) => !question.options!.includes(v))) {
        return 'Choose from the listed options.';
      }
      return null;
    case 'text':
      if (question.max_length != null && (value as string).length > question.max_length) {
        return `Please keep this under ${question.max_length} characters.`;
      }
      return null;
    default:
      return null;
  }
}

/**
 * Keeps only answers for known question ids whose value is answered and structurally valid.
 * Prevents stale local drafts (e.g. after a catalog version bump) from causing endless 422s.
 */
export function sanitizeAnswers(def: QuestionnaireDefinition, answers: Answers): Answers {
  const index = questionIndex(def);
  const out: Answers = {};
  for (const [id, value] of Object.entries(answers ?? {})) {
    const q = index.get(id);
    if (!q) continue;
    if (!isAnswered(q, value)) continue;
    if (validateAnswer(q, value) !== null) continue;
    out[id] = value;
  }
  return out;
}

export function sectionIndexById(def: QuestionnaireDefinition, id: string | null | undefined): number {
  if (!id) return -1;
  return def.sections.findIndex((s) => s.id === id);
}

export interface ResumeState {
  answers: Answers;
  sectionIndex: number;
  /** Local changes still need to be pushed to the server. */
  pendingSync: boolean;
}

/**
 * Decides where to resume. Server state is the source of truth, except that unsynced local
 * changes (pendingSync) are layered on top so offline progress is not lost.
 */
export function resolveResumeState(
  def: QuestionnaireDefinition,
  server: OnboardingState | null,
  local: LocalDraft | null,
): ResumeState {
  let answers: Answers = { ...(server?.answers ?? {}) };
  let sectionId = server?.current_section ?? null;
  let pendingSync = false;

  if (local && local.pendingSync) {
    answers = { ...answers, ...local.answers };
    sectionId = local.currentSection ?? sectionId;
    pendingSync = true;
  } else if (!server && local) {
    answers = { ...local.answers };
    sectionId = local.currentSection;
  }

  const clean = sanitizeAnswers(def, answers);
  const idx = sectionIndexById(def, sectionId);
  return {
    answers: clean,
    sectionIndex: idx >= 0 ? idx : 0,
    pendingSync,
  };
}

export function missingRequiredIds(section: QuestionnaireSection, answers: Answers): string[] {
  return section.questions.filter((q) => validateAnswer(q, answers[q.id]) !== null).map((q) => q.id);
}

export function allMissingRequiredIds(def: QuestionnaireDefinition, answers: Answers): string[] {
  return def.sections.flatMap((s) => missingRequiredIds(s, answers));
}

/**
 * Extracts question ids referenced by a submit/draft 422. The contract says the 422 "lists
 * missing/invalid question ids" without pinning the exact shape, so we look in every place a
 * FastAPI error can carry them: `loc` segments, field-error keys, and the message text.
 */
export function invalidQuestionIdsFromError(def: QuestionnaireDefinition, error: ApiError): string[] {
  const known = questionIndex(def);
  const found = new Set<string>();
  const consider = (s: string) => {
    if (known.has(s)) found.add(s);
  };

  for (const issue of error.issues ?? []) {
    for (const part of issue.loc) if (typeof part === 'string') consider(part);
    scanText(issue.msg, known, found);
  }
  for (const key of Object.keys(error.fieldErrors ?? {})) consider(key);
  scanText(error.message, known, found);

  // Preserve catalog order.
  const ordered: string[] = [];
  for (const s of def.sections) for (const q of s.questions) if (found.has(q.id)) ordered.push(q.id);
  return ordered;
}

function scanText(text: string | undefined, known: Map<string, Question>, found: Set<string>) {
  if (!text) return;
  const tokens = text.match(/[A-Za-z0-9_\-.]+/g) ?? [];
  for (const t of tokens) if (known.has(t)) found.add(t);
}

export function firstSectionIndexContaining(def: QuestionnaireDefinition, ids: string[]): number {
  if (!ids.length) return -1;
  const set = new Set(ids);
  return def.sections.findIndex((s) => s.questions.some((q) => set.has(q.id)));
}

export function progressFraction(def: QuestionnaireDefinition, answers: Answers): number {
  const all = def.sections.flatMap((s) => s.questions);
  if (!all.length) return 0;
  const done = all.filter((q) => isAnswered(q, answers[q.id])).length;
  return done / all.length;
}
