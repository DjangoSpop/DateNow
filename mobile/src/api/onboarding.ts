import { apiClient, type ApiClient } from './client';
import type { OnboardingDraftRequest, OnboardingState } from './types';

export function onboardingApi(client: ApiClient = apiClient) {
  return {
    /** GET /onboarding → 200 OnboardingState (never 404; `not_started` if nothing saved). */
    get: (signal?: AbortSignal) => client.request<OnboardingState>('/onboarding', { signal }),
    /**
     * PUT /onboarding → 200 OnboardingState. `answers` are MERGED server-side into the draft.
     * 422 on unknown id / wrong type / out of range, 409 if onboarding already completed.
     */
    saveDraft: (body: OnboardingDraftRequest) =>
      client.request<OnboardingState>('/onboarding', { method: 'PUT', body }),
  };
}

export const onboarding = onboardingApi();
