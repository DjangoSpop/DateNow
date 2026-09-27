import { apiClient, type ApiClient } from './client';
import type { Answers, PsychologicalProfile, QuestionnaireDefinition } from './types';

export function questionnaireApi(client: ApiClient = apiClient) {
  return {
    /** GET /questionnaire → server-owned question catalog. */
    get: (signal?: AbortSignal) =>
      client.request<QuestionnaireDefinition>('/questionnaire', { signal }),
    /**
     * POST /questionnaire/submit → 201 PsychologicalProfile.
     * Sends RAW answers only; the server computes every score. 422 lists missing/invalid ids,
     * 409 if already completed.
     */
    submit: (answers: Answers) =>
      client.request<PsychologicalProfile>('/questionnaire/submit', {
        method: 'POST',
        body: { answers },
        // Scoring can take a little longer than a plain CRUD call.
        timeoutMs: 30_000,
      }),
  };
}

export const questionnaire = questionnaireApi();
