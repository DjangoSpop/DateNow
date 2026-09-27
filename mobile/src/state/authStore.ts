import { create } from 'zustand';

import { auth } from '../api/auth';
import { apiClient } from '../api/client';
import { ApiError, isApiError } from '../api/errors';
import type { Me, RegisterRequest } from '../api/types';
import { session } from '../auth/session';
import { resolveBootRoute, type BootRoute } from '../navigation/bootRoute';
import { clearAllLocalDrafts } from '../onboarding/draftStorage';

export type AuthStatus = 'booting' | 'boot_error' | 'ready';

interface AuthState {
  status: AuthStatus;
  bootError: ApiError | null;
  hasSession: boolean;
  me: Me | null;

  boot(): Promise<void>;
  login(email: string, password: string): Promise<void>;
  register(body: RegisterRequest): Promise<void>;
  /** Re-fetches /auth/me (e.g. after profile creation or onboarding submit) so guards re-route. */
  refreshMe(): Promise<Me>;
  logout(): Promise<void>;
  /** Called by the API client when refresh fails; tokens are already cleared. */
  handleSessionExpired(): void;
}

function toApiError(e: unknown): ApiError {
  if (isApiError(e)) return e;
  return new ApiError({ status: 0, code: 'unknown', message: 'Something unexpected happened.' });
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  status: 'booting',
  bootError: null,
  hasSession: false,
  me: null,

  async boot() {
    set({ status: 'booting', bootError: null });
    let tokens = null;
    try {
      tokens = await session.load();
    } catch {
      tokens = null;
    }
    if (!tokens) {
      set({ status: 'ready', hasSession: false, me: null });
      return;
    }
    try {
      // The client refreshes once on 401; if that fails it clears the session.
      const me = await auth.me();
      set({ status: 'ready', hasSession: true, me });
    } catch (e) {
      const err = toApiError(e);
      if (err.code === 'unauthorized') {
        await session.clear();
        set({ status: 'ready', hasSession: false, me: null });
      } else {
        // Offline / server down: keep the tokens and offer a retry instead of logging out.
        set({ status: 'boot_error', bootError: err });
      }
    }
  },

  async login(email, password) {
    const token = await auth.login({ email: email.trim(), password });
    await session.setTokens(token);
    try {
      const me = await auth.me();
      set({ status: 'ready', hasSession: true, me, bootError: null });
    } catch (e) {
      await session.clear();
      throw toApiError(e);
    }
  },

  async register(body) {
    const token = await auth.register({ ...body, email: body.email.trim() });
    await session.setTokens(token);
    try {
      const me = await auth.me();
      set({ status: 'ready', hasSession: true, me, bootError: null });
    } catch (e) {
      await session.clear();
      throw toApiError(e);
    }
  },

  async refreshMe() {
    const me = await auth.me();
    if (get().hasSession) set({ me });
    return me;
  },

  async logout() {
    // No server logout endpoint in the Sprint 1 contract: logout is purely local.
    await session.clear();
    await clearAllLocalDrafts();
    set({ status: 'ready', hasSession: false, me: null, bootError: null });
  },

  handleSessionExpired() {
    set({ status: 'ready', hasSession: false, me: null });
  },
}));

apiClient.setSessionExpiredHandler(() => useAuthStore.getState().handleSessionExpired());

export function selectBootRoute(state: Pick<AuthState, 'hasSession' | 'me'>): BootRoute {
  return resolveBootRoute({ hasTokens: state.hasSession }, state.me);
}
