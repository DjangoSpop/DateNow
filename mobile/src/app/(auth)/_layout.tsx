import { Redirect, Stack } from 'expo-router';

import { useAuthStore } from '@/auth/authStore';
import { colors } from '@/theme';

/** Sign-in / sign-up group: only reachable while signed out. */
export default function AuthLayout() {
  const status = useAuthStore((s) => s.status);
  if (status === 'signedIn') return <Redirect href="/" />;
  return (
    <Stack
      screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}
    />
  );
}
