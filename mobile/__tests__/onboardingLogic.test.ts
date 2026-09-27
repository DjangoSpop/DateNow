import { ApiError, apiErrorFromResponse } from '../src/api/errors';
import type { OnboardingState, QuestionnaireDefinition } from '../src/api/types';
import {
  allMissingRequiredIds,
  firstSectionIndexContaining,
  invalidQuestionIdsFromError,
  resolveResumeState,
  sanitizeAnswers,
  validateAnswer,
} from '../src/onboarding/logic';

const def: QuestionnaireDefinition = {
  version: '2026.1',
  sections: [
    {
      id: 'personality',
      title: 'Personality',
      description: '',
      questions: [
        {
          id: 'bf_1',
          text: 'I am the life of the party',
          type: 'scale',
          required: true,
          options: null,
          scale: { min: 1, max: 5, min_label: 'Strongly disagree', max_label: 'Strongly agree' },
          max_length: null,
        },
        {
          id: 'bf_2',
          text: 'I plan ahead',
          type: 'scale',
          required: true,
          options: null,
          scale: { min: 1, max: 5, min_label: 'Never', max_label: 'Always' },
          max_length: null,
        },
      ],
    },
    {
      id: 'communication',
      title: 'Communication',
      description: '',
      questions: [
        {
          id: 'comm_1',
          text: 'Style',
          type: 'single_choice',
          required: true,
          options: ['direct', 'diplomatic'],
          scale: null,
          max_length: null,
        },
        {
          id: 'hob_1',
          text: 'Hobbies',
          type: 'multiple_choice',
          required: false,
          options: ['music', 'hiking'],
          scale: null,
          max_length: null,
        },
      ],
    },
    {
      id: 'verification',
      title: 'Verification',
      description: '',
      questions: [
        { id: 'ver_1', text: 'Why?', type: 'text', required: true, options: null, scale: null, max_length: 10 },
      ],
    },
  ],
};

const server = (partial: Partial<OnboardingState>): OnboardingState => ({
  status: 'in_progress',
  current_section: null,
  answers: {},
  questionnaire_version: '2026.1',
  updated_at: null,
  completed_at: null,
  ...partial,
});

describe('onboarding logic', () => {
  it('resumes at the server current_section with server answers', () => {
    const r = resolveResumeState(def, server({ current_section: 'communication', answers: { bf_1: 4 } }), null);
    expect(r).toEqual({ answers: { bf_1: 4 }, sectionIndex: 1, pendingSync: false });
  });

  it('starts at the first section when nothing is saved', () => {
    const r = resolveResumeState(def, server({ status: 'not_started' }), null);
    expect(r.sectionIndex).toBe(0);
    expect(r.answers).toEqual({});
  });

  it('layers unsynced local answers over the server draft', () => {
    const r = resolveResumeState(
      def,
      server({ current_section: 'personality', answers: { bf_1: 2 } }),
      { answers: { bf_1: 5, bf_2: 3 }, currentSection: 'communication', pendingSync: true, savedAt: 'x' },
    );
    expect(r).toEqual({ answers: { bf_1: 5, bf_2: 3 }, sectionIndex: 1, pendingSync: true });
  });

  it('ignores synced local drafts in favour of the server', () => {
    const r = resolveResumeState(def, server({ answers: { bf_1: 2 } }), {
      answers: { bf_1: 5 },
      currentSection: 'verification',
      pendingSync: false,
      savedAt: 'x',
    });
    expect(r.answers).toEqual({ bf_1: 2 });
    expect(r.sectionIndex).toBe(0);
  });

  it('drops unknown ids, invalid values and empty answers', () => {
    expect(
      sanitizeAnswers(def, { bf_1: 9, bf_2: 3, nope: 1, comm_1: 'other', hob_1: [], ver_1: '   ' }),
    ).toEqual({ bf_2: 3 });
  });

  it('validates text length and required-ness (whitespace counts as missing)', () => {
    const ver = def.sections[2].questions[0];
    expect(validateAnswer(ver, '  ')).toMatch(/answer/);
    expect(validateAnswer(ver, '12345678901')).toMatch(/10 characters/);
    expect(validateAnswer(ver, 'ok')).toBeNull();
  });

  it('lists missing required ids across sections (optional excluded)', () => {
    expect(allMissingRequiredIds(def, { bf_1: 3 })).toEqual(['bf_2', 'comm_1', 'ver_1']);
  });

  it('extracts invalid ids from the questionnaire 422 shape and finds the first section', () => {
    const err = apiErrorFromResponse(422, {
      detail: [
        { question_id: 'ver_1', message: 'Required' },
        { question_id: 'comm_1', message: 'Invalid option' },
      ],
    });
    const ids = invalidQuestionIdsFromError(def, err);
    expect(ids).toEqual(['comm_1', 'ver_1']); // catalog order
    expect(firstSectionIndexContaining(def, ids)).toBe(1);
  });

  it('extracts ids from FastAPI loc arrays and from message text', () => {
    const fromLoc = apiErrorFromResponse(422, {
      detail: [{ loc: ['body', 'answers', 'bf_2'], msg: 'out of range', type: 'x' }],
    });
    expect(invalidQuestionIdsFromError(def, fromLoc)).toEqual(['bf_2']);

    const fromText = new ApiError({ status: 422, code: 'validation', message: 'Missing answers: bf_1, ver_1' });
    expect(invalidQuestionIdsFromError(def, fromText)).toEqual(['bf_1', 'ver_1']);
  });
});
