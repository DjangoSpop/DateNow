import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { describeError } from '@/api/errors';
import { useAuthStore } from '@/auth/authStore';
import { Button } from '@/components/Button';
import { colors, spacing, typography } from '@/theme';

/** Shown while the stored session is being restored (or couldn't be verified). */
export function BootScreen() {
  const bootError = useAuthStore((s) => s.bootError);
  const bootstrap = useAuthStore((s) => s.bootstrap);
  const logout = useAuthStore((s) => s.logout);

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.center}>
        <Text style={styles.brand} accessibilityRole="header">
          DateNow
        </Text>
        <Text style={styles.tagline}>Meaningful connections, at your pace.</Text>
        {bootError ? (
          <View style={styles.errorBox}>
            <Text style={[typography.body, styles.textCenter]} accessibilityLiveRegion="polite">
              {describeError(bootError)}
            </Text>
            <Button label="Try again" onPress={() => void bootstrap()} />
            <Button label="Sign out" variant="ghost" onPress={() => void logout()} />
          </View>
        ) : (
          <ActivityIndicator
            size="large"
            color={colors.primary500}
            accessibilityLabel="Restoring your session"
          />
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing.xl, padding: spacing.xl },
  brand: { fontSize: 40, fontWeight: '800', color: colors.primary600, letterSpacing: -0.5 },
  tagline: { ...typography.body, color: colors.textMuted, textAlign: 'center' },
  errorBox: { gap: spacing.md, alignSelf: 'stretch', maxWidth: 420, width: '100%', alignItems: 'stretch' },
  textCenter: { textAlign: 'center' },
});
