import { StyleSheet, Text, View } from 'react-native';

import * as endpoints from '@/api/endpoints';
import { isApiError } from '@/api/errors';
import type { ProfileCreate } from '@/api/types';
import { useAuthStore } from '@/auth/authStore';
import { Button } from '@/components/Button';
import { Screen } from '@/components/Screen';
import { ProfileForm } from '@/features/profile/ProfileForm';
import { emptyProfileForm, toCreateBody } from '@/features/profile/validation';
import { colors, spacing, typography } from '@/theme';

export default function ProfileSetupScreen() {
  const patchOnboarding = useAuthStore((s) => s.patchOnboarding);
  const refreshMe = useAuthStore((s) => s.refreshMe);
  const logout = useAuthStore((s) => s.logout);

  async function create(payload: ProfileCreate) {
    try {
      await endpoints.createProfile(toCreateBody(payload));
    } catch (e) {
      // A profile already exists (e.g. created from another device): just move on.
      if (!(isApiError(e) && e.code === 'PROFILE_EXISTS')) throw e;
    }
    // The (app) layout guard moves the user on to the questionnaire once this flips.
    patchOnboarding({ profile_complete: true });
    void refreshMe();
  }

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={styles.step}>Step 1 of 2</Text>
        <Text style={typography.title} accessibilityRole="header">
          Let&apos;s set up your profile
        </Text>
        <Text style={styles.subtitle}>
          Only the basics for now. You can change any of this later.
        </Text>
      </View>
      <ProfileForm
        initialValues={emptyProfileForm}
        submitLabel="Save and continue"
        onSubmit={create}
      />
      <Button label="Sign out" variant="ghost" onPress={() => void logout()} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: spacing.sm },
  step: { fontSize: 14, fontWeight: '600', color: colors.accent600 },
  subtitle: { ...typography.body, color: colors.textMuted },
});
