import type { Questionnaire } from '@/api/types';
import {
  countAnsweredRequired,
  firstIndexOfIds,
  firstMissingIndex,
  flattenQuestions,
  isValidAnswer,
} from '../progress';

const scale = { min: 1, max: 5, labels: { '1': 'Not important', '5': 'Very important' } };

const q: Questionnaire = {
  version: 'ipip-v1',
  sections: [
    {
      id: 'personality',
      title: 'Your Personality',
      description: '',
      estimated_minutes: 6,
      questions: [
        { id: 'bf_1', text: 'a', type: 'scale', required: true, scale },
        { id: 'bf_2', text: 'b', type: 'scale', required: true, scale },
        { id: 'opt_1', text: 'c', type: 'scale', required: false, scale },
      ],
    },
    {
      id: 'communication',
      title: 'Communication',
      description: '',
      estimated_minutes: 2,
      questions: [
        {
          id: 'comm_1',
          text: 'd',
          type: 'single_choice',
          required: true,
          options: [
            { value: 'direct', label: 'Direct and straightforward' },
            { value: 'diplomatic', label: 'Diplomatic' },
          ],
        },
      ],
    },
  ],
};

const flat = flattenQuestions(q);

describe('questionnaire progress', () => {
  it('flattens in presentation order with section positions', () => {
    expect(flat.map((f) => f.question.id)).toEqual(['bf_1', 'bf_2', 'opt_1', 'comm_1']);
    expect(flat[3]).toMatchObject({ sectionIndex: 1, indexInSection: 0 });
  });

  it('resumes at the first unanswered required question', () => {
    expect(firstMissingIndex(flat, {})).toBe(0);
    expect(firstMissingIndex(flat, { bf_1: 3 })).toBe(1);
    // Optional questions are skipped when resuming.
    expect(firstMissingIndex(flat, { bf_1: 3, bf_2: 4 })).toBe(3);
    // Order follows presentation, not answer insertion order.
    expect(firstMissingIndex(flat, { comm_1: 'direct', bf_2: 1 })).toBe(0);
  });

  it('returns -1 when everything required is answered (→ review)', () => {
    expect(firstMissingIndex(flat, { bf_1: 1, bf_2: 5, comm_1: 'diplomatic' })).toBe(-1);
  });

  it('treats invalid or stale answers as missing', () => {
    expect(firstMissingIndex(flat, { bf_1: 9, bf_2: 2, comm_1: 'direct' })).toBe(0);
    expect(firstMissingIndex(flat, { bf_1: 1, bf_2: 2, comm_1: 'Direct and straightforward' })).toBe(3);
    expect(isValidAnswer(flat[0]!.question, 2.5)).toBe(false);
    expect(isValidAnswer(flat[0]!.question, '3')).toBe(false);
  });

  it('maps QUESTIONNAIRE_INCOMPLETE field ids to the earliest question', () => {
    expect(firstIndexOfIds(flat, ['comm_1', 'bf_2'])).toBe(1);
    expect(firstIndexOfIds(flat, ['unknown'])).toBe(-1);
  });

  it('counts answered required questions', () => {
    expect(countAnsweredRequired(flat, { bf_1: 2, opt_1: 3 })).toEqual({ answered: 1, total: 3 });
  });
});
