import type { Onboarding } from '@/api/types';

/** Authenticated routes (file names under src/app/(app)). */
export type AppRoute = 'home' | 'profile-setup' | 'profile-edit' | 'questionnaire';

/** Where a signed-in user belongs, based on the server's onboarding object. */
export function homeFor(onboarding: Onboarding): `/${AppRoute}` {
  if (!onboarding.profile_complete) return '/profile-setup';
  if (!onboarding.questionnaire_complete) return '/questionnaire';
  return '/home';
}

/**
 * Onboarding guard for deep links: returns where to redirect, or null if `route` is allowed.
 * - profile-setup only while there is no profile
 * - profile-edit and questionnaire need a profile (questionnaire stays open for retakes)
 * - home needs onboarding complete
 */
export function onboardingRedirect(route: AppRoute, onboarding: Onboarding): `/${AppRoute}` | null {
  switch (route) {
    case 'profile-setup':
      return onboarding.profile_complete ? homeFor(onboarding) : null;
    case 'profile-edit':
    case 'questionnaire':
      return onboarding.profile_complete ? null : '/profile-setup';
    case 'home':
      return onboarding.complete ? null : homeFor(onboarding);
  }
}

export function isAppRoute(segment: string | undefined): segment is AppRoute {
  return (
    segment === 'home' ||
    segment === 'profile-setup' ||
    segment === 'profile-edit' ||
    segment === 'questionnaire'
  );
}
