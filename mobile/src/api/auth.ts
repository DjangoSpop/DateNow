import { apiClient, type ApiClient } from './client';
import type { LoginRequest, Me, RefreshRequest, RegisterRequest, Token } from './types';

export function authApi(client: ApiClient = apiClient) {
  return {
    /** POST /auth/register → 201 Token (409 if email exists, 422 invalid input). */
    register: (body: RegisterRequest) =>
      client.request<Token>('/auth/register', { method: 'POST', body, auth: false }),
    /** POST /auth/login → 200 Token (401 "Incorrect email or password"). */
    login: (body: LoginRequest) =>
      client.request<Token>('/auth/login', { method: 'POST', body, auth: false }),
    /**
     * POST /auth/refresh → 200 Token. Normally invoked by the client's 401 handling;
     * exposed for completeness.
     */
    refresh: (body: RefreshRequest) =>
      client.request<Token>('/auth/refresh', { method: 'POST', body, auth: false }),
    /** GET /auth/me → 200 Me. The boot call. */
    me: (signal?: AbortSignal) => client.request<Me>('/auth/me', { signal }),
  };
}

export const auth = authApi();
