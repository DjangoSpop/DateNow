import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import * as endpoints from '@/api/endpoints';
import { describeError, isApiError } from '@/api/errors';
import type { Profile, PsychologicalProfile } from '@/api/types';
import { useAuthStore } from '@/auth/authStore';
import { Button } from '@/components/Button';
import { Banner, Card, ErrorState, LoadingState } from '@/components/feedback';
import { Screen } from '@/components/Screen';
import { PersonalitySnapshot } from '@/features/home/PersonalitySnapshot';
import { GENDER_LABELS, GOAL_LABELS, LOOKING_FOR_LABELS } from '@/features/profile/labels';
import { colors, radius, spacing, typography } from '@/theme';

type HomeData = { profile: Profile; psych: PsychologicalProfile | null };
type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; message: string }
  | { kind: 'ready'; data: HomeData };

function greeting(now: Date): string {
  const h = now.getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export default function HomeScreen() {
  const logout = useAuthStore((s) => s.logout);
  const refreshMe = useAuthStore((s) => s.refreshMe);
  const [state, setState] = useState<LoadState>({ kind: 'loading' });
  const [loggingOut, setLoggingOut] = useState(false);

  const load = useCallback(async () => {
    setState((prev) => (prev.kind === 'ready' ? prev : { kind: 'loading' }));
    try {
      const [profile, psych] = await Promise.all([
        endpoints.getProfile(),
        endpoints.getPsychologicalProfile().catch((e: unknown) => {
          if (isApiError(e) && e.code === 'PSYCH_PROFILE_NOT_FOUND') return null;
          throw e;
        }),
      ]);
      setState({ kind: 'ready', data: { profile, psych } });
    } catch (e) {
      setState({ kind: 'error', message: describeError(e) });
    }
  }, []);

  // Reload whenever Home regains focus (e.g. after editing the profile or retaking answers).
  useFocusEffect(
    useCallback(() => {
      void load();
      void refreshMe();
    }, [load, refreshMe]),
  );

  if (state.kind === 'loading') return <LoadingState label="Loading your home…" />;
  if (state.kind === 'error') return <ErrorState message={state.message} onRetry={load} />;

  const { profile, psych } = state.data;

  return (
    <Screen>
      <View style={styles.header}>
        <Text style={typography.title} accessibilityRole="header">
          {greeting(new Date())}, {profile.first_name}
        </Text>
        <Text style={styles.muted}>Here&apos;s where things stand.</Text>
      </View>

      <Card>
        <Text style={typography.heading} accessibilityRole="header">
          Your profile
        </Text>
        <Row label="About you" value={`${profile.age} · ${GENDER_LABELS[profile.gender]}`} />
        <Row
          label="Interested in"
          value={profile.looking_for_gender.map((g) => LOOKING_FOR_LABELS[g]).join(', ')}
        />
        <Row
          label="Age range"
          value={`${profile.age_preference_min}–${profile.age_preference_max}`}
        />
        <Row label="Looking for" value={GOAL_LABELS[profile.relationship_goal]} />
        {profile.city || profile.country ? (
          <Row label="Location" value={[profile.city, profile.country].filter(Boolean).join(', ')} />
        ) : null}
        {profile.bio ? <Text style={typography.body}>{profile.bio}</Text> : null}
        <Button
          label="Edit profile"
          variant="secondary"
          onPress={() => router.push('/profile-edit')}
        />
      </Card>

      {psych ? (
        <PersonalitySnapshot profile={psych} />
      ) : (
        <Banner tone="info">
          Your personality snapshot isn&apos;t ready yet. Finish the questionnaire to see it.
        </Banner>
      )}
      <Button
        label={psych ? 'Review or change my answers' : 'Continue questionnaire'}
        variant="secondary"
        onPress={() => router.push('/questionnaire')}
      />

      <View style={styles.soon} accessible accessibilityLabel="Coming soon: matching arrives in a later update.">
        <Text style={styles.soonBadge}>COMING SOON</Text>
        <Text style={typography.heading}>Matching arrives in a later update</Text>
        <Text style={styles.muted}>
          We&apos;re building thoughtful, compatibility-based introductions. There are no matches to
          show yet — we&apos;ll let you know when it&apos;s ready.
        </Text>
      </View>

      <Button
        label="Sign out"
        variant="danger"
        loading={loggingOut}
        onPress={async () => {
          setLoggingOut(true);
          await logout();
        }}
      />
    </Screen>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={styles.rowValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { gap: spacing.xs },
  muted: { ...typography.body, color: colors.textMuted },
  row: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', gap: spacing.sm },
  rowLabel: { fontSize: 15, color: colors.textSubtle },
  rowValue: { fontSize: 15, color: colors.text, fontWeight: '600', flexShrink: 1, textAlign: 'right' },
  soon: {
    borderRadius: radius.xl,
    borderWidth: 2,
    borderStyle: 'dashed',
    borderColor: colors.accent100,
    backgroundColor: colors.accent50,
    padding: spacing.xl,
    gap: spacing.sm,
  },
  soonBadge: { fontSize: 12, fontWeight: '700', letterSpacing: 1, color: colors.accent600 },
});
