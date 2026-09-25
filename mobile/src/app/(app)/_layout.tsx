import { Redirect, Stack, useSegments } from 'expo-router';

import { useAuthStore } from '@/auth/authStore';
import { isAppRoute, onboardingRedirect } from '@/auth/routing';
import { colors } from '@/theme';

/**
 * Authenticated group. Guards (in order): must be signed in; the requested screen must fit the
 * onboarding state from `/users/me` (e.g. no home before the questionnaire is done).
 */
export default function AppLayout() {
  const status = useAuthStore((s) => s.status);
  const me = useAuthStore((s) => s.me);
  const segments = useSegments();

  if (status !== 'signedIn' || !me) return <Redirect href="/login" />;

  const leaf = segments[segments.length - 1];
  if (isAppRoute(leaf)) {
    const target = onboardingRedirect(leaf, me.onboarding);
    if (target) return <Redirect href={target} />;
  }

  return (
    <Stack
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
        headerTintColor: colors.primary600,
        headerStyle: { backgroundColor: colors.background },
        headerShadowVisible: false,
      }}
    >
      <Stack.Screen name="profile-edit" options={{ headerShown: true, title: 'Edit profile' }} />
    </Stack>
  );
}
