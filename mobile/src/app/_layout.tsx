import { Stack, router } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useRef } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { Button, ErrorBanner } from '../components/ui';
import { ROUTE_HREF } from '../navigation/bootRoute';
import { selectBootRoute, useAuthStore } from '../state/authStore';
import { colors, spacing, type } from '../theme';

// Keep the native splash up until the boot decision is made → no flash of the wrong screen.
SplashScreen.preventAutoHideAsync().catch(() => {});

export default function RootLayout() {
  const status = useAuthStore((s) => s.status);
  const route = useAuthStore(selectBootRoute);
  const boot = useAuthStore((s) => s.boot);

  useEffect(() => {
    void boot();
  }, [boot]);

  useEffect(() => {
    if (status !== 'booting') {
      SplashScreen.hideAsync().catch(() => {});
    }
  }, [status]);

  // When the session/onboarding state changes after boot (login, profile created, submit,
  // logout, session expiry) move to the matching area. Guards below also block stale screens.
  const lastRoute = useRef<string | null>(null);
  useEffect(() => {
    if (status !== 'ready') return;
    if (lastRoute.current !== null && lastRoute.current !== route) {
      router.replace(ROUTE_HREF[route]);
    }
    lastRoute.current = route;
  }, [route, status]);

  return (
    <SafeAreaProvider>
      <StatusBar style="dark" />
      {status === 'booting' ? (
        <View style={styles.boot} accessibilityLabel="Loading DateNow" />
      ) : status === 'boot_error' ? (
        <BootError />
      ) : (
        <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.calm50 } }}>
          <Stack.Screen name="index" />
          <Stack.Protected guard={route === 'auth'}>
            <Stack.Screen name="(auth)" />
          </Stack.Protected>
          <Stack.Protected guard={route === 'profile-setup'}>
            <Stack.Screen name="profile-setup" />
          </Stack.Protected>
          <Stack.Protected guard={route === 'onboarding'}>
            <Stack.Screen name="onboarding" />
          </Stack.Protected>
          <Stack.Protected guard={route === 'home'}>
            <Stack.Screen name="home" />
          </Stack.Protected>
        </Stack>
      )}
    </SafeAreaProvider>
  );
}

function BootError() {
  const error = useAuthStore((s) => s.bootError);
  const boot = useAuthStore((s) => s.boot);
  const logout = useAuthStore((s) => s.logout);
  const offline = error?.code === 'network' || error?.code === 'timeout';
  return (
    <View style={styles.errorContainer}>
      <Text style={type.title} accessibilityRole="header">
        {offline ? "You're offline" : 'We hit a snag'}
      </Text>
      <ErrorBanner message={error?.message ?? 'Could not restore your session.'} />
      <Button label="Try again" onPress={() => void boot()} />
      <Button label="Sign out" variant="ghost" onPress={() => void logout()} />
    </View>
  );
}

const styles = StyleSheet.create({
  boot: { flex: 1, backgroundColor: colors.calm50 },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    padding: spacing.lg,
    gap: spacing.md,
    backgroundColor: colors.calm50,
  },
});
