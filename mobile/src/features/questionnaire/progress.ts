import type { AnswerValue, Answers, Question, Questionnaire, QuestionnaireSection } from '@/api/types';

export interface FlatQuestion {
  question: Question;
  section: QuestionnaireSection;
  sectionIndex: number;
  /** Position within its section (0-based). */
  indexInSection: number;
}

/** Questions in presentation order (sections, then questions), as the contract specifies. */
export function flattenQuestions(q: Questionnaire): FlatQuestion[] {
  return q.sections.flatMap((section, sectionIndex) =>
    section.questions.map((question, indexInSection) => ({
      question,
      section,
      sectionIndex,
      indexInSection,
    })),
  );
}

/** Is `value` a valid answer for `question` per the contract's value rules? */
export function isValidAnswer(question: Question, value: AnswerValue | undefined): boolean {
  if (value === undefined) return false;
  if (question.type === 'scale') {
    return (
      typeof value === 'number' &&
      Number.isInteger(value) &&
      value >= question.scale.min &&
      value <= question.scale.max
    );
  }
  return typeof value === 'string' && question.options.some((o) => o.value === value);
}

/**
 * Resume point: index of the first required question without a valid answer, in presentation
 * order. Returns -1 when every required question is answered (→ go to the review step).
 */
export function firstMissingIndex(flat: FlatQuestion[], answers: Answers): number {
  return flat.findIndex(
    ({ question }) => question.required && !isValidAnswer(question, answers[question.id]),
  );
}

/** First index (presentation order) among the given question ids; -1 if none are known. */
export function firstIndexOfIds(flat: FlatQuestion[], ids: Iterable<string>): number {
  const wanted = new Set(ids);
  return flat.findIndex(({ question }) => wanted.has(question.id));
}

export function countAnsweredRequired(flat: FlatQuestion[], answers: Answers) {
  let answered = 0;
  let total = 0;
  for (const { question } of flat) {
    if (!question.required) continue;
    total += 1;
    if (isValidAnswer(question, answers[question.id])) answered += 1;
  }
  return { answered, total };
}
