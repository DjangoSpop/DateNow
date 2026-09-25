import { create } from 'zustand';

import * as endpoints from '@/api/endpoints';
import { ApiError, isApiError } from '@/api/errors';
import { apiClient } from '@/api/instance';
import type { Me, Onboarding, TokenPair } from '@/api/types';
import { tokenStore } from './tokenStorage';

export type AuthStatus = 'booting' | 'signedOut' | 'signedIn';

export interface AuthState {
  status: AuthStatus;
  me: Me | null;
  /** Set when a stored session exists but couldn't be verified (e.g. offline at launch). */
  bootError: ApiError | null;
  /** Short explanation shown on the sign-in screen after an involuntary sign-out. */
  signOutReason: string | null;

  bootstrap(): Promise<void>;
  login(email: string, password: string): Promise<void>;
  register(email: string, password: string): Promise<void>;
  logout(): Promise<void>;
  /** Re-fetch `/users/me` (e.g. after onboarding steps). Returns the fresh user or null on failure. */
  refreshMe(): Promise<Me | null>;
  /**
   * Apply a known onboarding change locally (e.g. right after creating the profile) so routing
   * guards don't bounce the user if the follow-up `/users/me` fetch is slow or fails.
   */
  patchOnboarding(patch: Partial<Onboarding>): void;
}

export const normalizeEmail = (email: string) => email.trim().toLowerCase();

let bootInFlight: Promise<void> | null = null;

export const useAuthStore = create<AuthState>()((set, get) => {
  const signedOut = (reason: string | null = null) =>
    set({ status: 'signedOut', me: null, bootError: null, signOutReason: reason });

  // The API client calls this when refresh fails: tokens are already cleared by then.
  apiClient.setAuthFailureHandler(() => {
    if (get().status !== 'signedOut') {
      signedOut('Your session has ended. Please sign in again.');
    }
  });

  async function startSession(pair: TokenPair): Promise<void> {
    await tokenStore.saveTokens({ accessToken: pair.access_token, refreshToken: pair.refresh_token });
    try {
      const me = await endpoints.getMe();
      set({ status: 'signedIn', me, bootError: null, signOutReason: null });
    } catch (e) {
      // Don't leave a half-started session behind: the user simply tries again.
      await tokenStore.clearTokens();
      if (get().status !== 'signedOut') signedOut();
      throw e;
    }
  }

  return {
    status: 'booting',
    me: null,
    bootError: null,
    signOutReason: null,

    bootstrap() {
      if (bootInFlight) return bootInFlight;
      bootInFlight = (async () => {
        set({ status: 'booting', bootError: null });
        const tokens = await tokenStore.loadTokens();
        if (!tokens) {
          signedOut();
          return;
        }
        try {
          // The client performs the refresh-once dance if the stored access token has expired.
          const me = await endpoints.getMe();
          set({ status: 'signedIn', me, bootError: null, signOutReason: null });
        } catch (e) {
          if (isApiError(e) && e.isTransient) {
            // Keep the stored session; the splash screen offers "Try again".
            set({ status: 'booting', bootError: e });
            return;
          }
          // Auth failures were already handled by the client (tokens cleared). Anything else
          // (e.g. ACCOUNT_DISABLED) also means we can't continue this session.
          await tokenStore.clearTokens();
          signedOut(
            isApiError(e) && e.code === 'ACCOUNT_DISABLED'
              ? 'This account has been disabled.'
              : 'Please sign in again.',
          );
        }
      })().finally(() => {
        bootInFlight = null;
      });
      return bootInFlight;
    },

    async login(email, password) {
      const pair = await endpoints.login({ email: normalizeEmail(email), password });
      await startSession(pair);
    },

    async register(email, password) {
      const pair = await endpoints.register({ email: normalizeEmail(email), password });
      await startSession(pair);
    },

    async logout() {
      await tokenStore.clearTokens();
      signedOut();
    },

    async refreshMe() {
      try {
        const me = await endpoints.getMe();
        set({ me });
        return me;
      } catch {
        return null;
      }
    },

    patchOnboarding(patch) {
      const me = get().me;
      if (!me) return;
      const onboarding = { ...me.onboarding, ...patch };
      onboarding.complete = onboarding.profile_complete && onboarding.questionnaire_complete;
      set({ me: { ...me, onboarding } });
    },
  };
});
