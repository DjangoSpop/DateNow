import type { Me } from '../src/api/types';
import { ROUTE_HREF, resolveBootRoute } from '../src/navigation/bootRoute';

const baseMe: Me = {
  id: 1,
  email: 'a@b.com',
  first_name: 'Ada',
  last_name: 'L',
  is_active: true,
  is_verified: false,
  created_at: '2026-01-01T00:00:00Z',
  has_profile: false,
  onboarding_status: 'not_started',
};

const session = { hasTokens: true };

describe('resolveBootRoute', () => {
  it('no session → auth', () => {
    expect(resolveBootRoute(null, null)).toBe('auth');
    expect(resolveBootRoute({ hasTokens: false }, baseMe)).toBe('auth');
  });

  it('session but no user loaded → auth', () => {
    expect(resolveBootRoute(session, null)).toBe('auth');
  });

  it('inactive user → auth', () => {
    expect(resolveBootRoute(session, { ...baseMe, is_active: false })).toBe('auth');
  });

  it('session and no profile → profile-setup (regardless of onboarding status)', () => {
    expect(resolveBootRoute(session, baseMe)).toBe('profile-setup');
    expect(resolveBootRoute(session, { ...baseMe, onboarding_status: 'in_progress' })).toBe('profile-setup');
  });

  it('profile and onboarding not started / in progress → onboarding', () => {
    expect(resolveBootRoute(session, { ...baseMe, has_profile: true })).toBe('onboarding');
    expect(resolveBootRoute(session, { ...baseMe, has_profile: true, onboarding_status: 'in_progress' })).toBe(
      'onboarding',
    );
  });

  it('onboarding completed → home', () => {
    expect(resolveBootRoute(session, { ...baseMe, has_profile: true, onboarding_status: 'completed' })).toBe('home');
  });

  it('every route has an href', () => {
    expect(ROUTE_HREF).toEqual({
      auth: '/login',
      'profile-setup': '/profile-setup',
      onboarding: '/onboarding',
      home: '/home',
    });
  });
});
