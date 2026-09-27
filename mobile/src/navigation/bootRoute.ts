import type { Me } from '../api/types';

export type BootRoute = 'auth' | 'profile-setup' | 'onboarding' | 'home';

export interface SessionSnapshot {
  hasTokens: boolean;
}

/**
 * Pure routing decision used by the root layout guards.
 *
 *   no session / unknown user          → auth (login/register)
 *   session, no profile                → profile-setup
 *   profile, onboarding not completed  → onboarding (resumes where saved)
 *   onboarding completed               → home
 *
 * Network failures while fetching /auth/me are NOT represented here: the boot state machine keeps
 * the user on a retry screen instead of logging them out (see state/authStore.ts).
 */
export function resolveBootRoute(session: SessionSnapshot | null, me: Me | null): BootRoute {
  if (!session || !session.hasTokens) return 'auth';
  if (!me || !me.is_active) return 'auth';
  if (!me.has_profile) return 'profile-setup';
  if (me.onboarding_status !== 'completed') return 'onboarding';
  return 'home';
}

export const ROUTE_HREF = {
  auth: '/login',
  'profile-setup': '/profile-setup',
  onboarding: '/onboarding',
  home: '/home',
} as const satisfies Record<BootRoute, string>;
