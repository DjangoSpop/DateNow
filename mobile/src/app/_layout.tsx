import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';

import { useAuthStore } from '@/auth/authStore';
import { BootScreen } from '@/features/boot/BootScreen';
import { colors } from '@/theme';

/**
 * Root: restore the session once, show the boot screen until the auth state is known, then hand
 * over to the router. Group layouts `(auth)` and `(app)` enforce the actual access rules, so deep
 * links can't bypass sign-in or onboarding.
 */
export default function RootLayout() {
  const status = useAuthStore((s) => s.status);
  const bootstrap = useAuthStore((s) => s.bootstrap);

  useEffect(() => {
    void bootstrap();
  }, [bootstrap]);

  return (
    <>
      <StatusBar style="dark" />
      {status === 'booting' ? (
        <BootScreen />
      ) : (
        <Stack
          screenOptions={{
            headerShown: false,
            contentStyle: { backgroundColor: colors.background },
          }}
        />
      )}
    </>
  );
}
