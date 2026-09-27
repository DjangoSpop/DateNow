import { apiClient, type ApiClient } from './client';
import type { Profile, ProfileCreate, ProfileUpdate, PsychologicalProfile } from './types';

export function profileApi(client: ApiClient = apiClient) {
  return {
    /** GET /users/me/profile → 200 Profile | 404 (not created yet). */
    get: (signal?: AbortSignal) => client.request<Profile>('/users/me/profile', { signal }),
    /** POST /users/me/profile → 201 Profile | 400 if exists | 422 invalid (incl. under 18). */
    create: (body: ProfileCreate) =>
      client.request<Profile>('/users/me/profile', { method: 'POST', body }),
    /** PATCH /users/me/profile → 200 Profile | 404. */
    update: (body: ProfileUpdate) =>
      client.request<Profile>('/users/me/profile', { method: 'PATCH', body }),
    /** GET /users/me/psychological-profile → 200 | 404 (onboarding not completed). */
    getPsychological: (signal?: AbortSignal) =>
      client.request<PsychologicalProfile>('/users/me/psychological-profile', { signal }),
  };
}

export const profile = profileApi();
