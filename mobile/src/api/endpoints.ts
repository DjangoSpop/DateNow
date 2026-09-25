/**
 * Typed functions for every Sprint 1 endpoint in docs/API_CONTRACT.md.
 * Auth endpoints are called with `auth: false` (no bearer header, no refresh-on-401).
 */
import { apiClient } from './instance';
import type {
  Answers,
  Credentials,
  Me,
  Profile,
  ProfileCreate,
  ProfileUpdate,
  PsychologicalProfile,
  Questionnaire,
  QuestionnaireState,
  TokenPair,
} from './types';

// ---- Auth ----
export const register = (body: Credentials) =>
  apiClient.request<TokenPair>('/auth/register', { method: 'POST', body, auth: false });

export const login = (body: Credentials) =>
  apiClient.request<TokenPair>('/auth/login', { method: 'POST', body, auth: false });

// `/auth/refresh` is handled inside the client (single-flight); no public wrapper on purpose.

// ---- Current user ----
export const getMe = () => apiClient.request<Me>('/users/me');

// ---- Profile ----
export const getProfile = () => apiClient.request<Profile>('/users/me/profile');

export const createProfile = (body: ProfileCreate) =>
  apiClient.request<Profile>('/users/me/profile', { method: 'POST', body });

export const updateProfile = (body: ProfileUpdate) =>
  apiClient.request<Profile>('/users/me/profile', { method: 'PATCH', body });

// ---- Questionnaire ----
export const getQuestionnaire = () => apiClient.request<Questionnaire>('/questionnaire');

export const getQuestionnaireState = () =>
  apiClient.request<QuestionnaireState>('/users/me/questionnaire');

export const saveAnswers = (answers: Answers) =>
  apiClient.request<QuestionnaireState>('/users/me/questionnaire/answers', {
    method: 'PUT',
    body: { answers },
  });

export const submitQuestionnaire = () =>
  apiClient.request<PsychologicalProfile>('/users/me/questionnaire/submit', { method: 'POST' });

export const getPsychologicalProfile = () =>
  apiClient.request<PsychologicalProfile>('/users/me/psychological-profile');
