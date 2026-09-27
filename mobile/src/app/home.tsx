import { useEffect, useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { ApiError, isApiError } from '../api/errors';
import { profile } from '../api/profile';
import type { PsychologicalProfile } from '../api/types';
import { Button, Card, ErrorBanner, Screen } from '../components/ui';
import { useAuthStore } from '../state/authStore';
import { colors, radius, spacing, type } from '../theme';

const BIG_FIVE: { key: keyof PsychologicalProfile; label: string }[] = [
  { key: 'openness', label: 'Openness' },
  { key: 'conscientiousness', label: 'Conscientiousness' },
  { key: 'extraversion', label: 'Extraversion' },
  { key: 'agreeableness', label: 'Agreeableness' },
  { key: 'neuroticism', label: 'Emotional sensitivity' },
];

function humanize(value: string): string {
  const s = value.replace(/_/g, ' ').trim();
  return s ? s[0].toUpperCase() + s.slice(1) : s;
}

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; error: ApiError }
  | { kind: 'ready'; data: PsychologicalProfile };

export default function HomeScreen() {
  const me = useAuthStore((s) => s.me);
  const logout = useAuthStore((s) => s.logout);
  const [state, setState] = useState<LoadState>({ kind: 'loading' });

  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    profile.getPsychological().then(
      (data) => {
        if (!cancelled) setState({ kind: 'ready', data });
      },
      (e: unknown) => {
        if (cancelled) return;
        setState({
          kind: 'error',
          error: isApiError(e)
            ? e
            : new ApiError({ status: 0, code: 'unknown', message: 'Something unexpected happened.' }),
        });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const retry = () => {
    setState({ kind: 'loading' });
    setAttempt((n) => n + 1);
  };

  return (
    <Screen>
      <Text style={type.title} accessibilityRole="header">
        Hi {me?.first_name ?? 'there'}
      </Text>
      <View style={styles.badge} accessibilityRole="text">
        <Text style={styles.badgeText}>✓ Onboarding complete</Text>
      </View>

      <Card style={styles.placeholder}>
        <Text style={type.heading}>DateNow is finding someone worth meeting</Text>
        <Text style={type.body}>
          We&apos;ll let you know when we have an introduction we believe in. Quality over quantity.
        </Text>
      </Card>

      <Card>
        <Text style={type.heading} accessibilityRole="header">
          Your personality snapshot
        </Text>
        {state.kind === 'loading' ? (
          <Text style={type.caption} accessibilityLiveRegion="polite">
            Loading your profile…
          </Text>
        ) : state.kind === 'error' ? (
          <ErrorBanner
            message={
              state.error.code === 'not_found'
                ? "Your profile isn't ready yet. Please try again in a moment."
                : state.error.message
            }
            onRetry={retry}
          />
        ) : (
          <>
            {BIG_FIVE.map(({ key, label }) => (
              <TraitBar key={key} label={label} value={Number(state.data[key]) || 0} />
            ))}
            <View style={styles.facts}>
              <Fact label="Communication" value={humanize(state.data.communication_style)} />
              <Fact label="Conflict style" value={humanize(state.data.conflict_resolution)} />
              <Fact label="Attachment" value={humanize(state.data.attachment_style)} />
            </View>
          </>
        )}
      </Card>

      <Button label="Sign out" variant="secondary" onPress={() => void logout()} />
    </Screen>
  );
}

function TraitBar({ label, value }: { label: string; value: number }) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <View
      style={styles.trait}
      accessible
      accessibilityRole="progressbar"
      accessibilityLabel={label}
      accessibilityValue={{ min: 0, max: 100, now: pct }}
    >
      <View style={styles.traitHeader}>
        <Text style={type.label}>{label}</Text>
        <Text style={type.caption}>{pct}</Text>
      </View>
      <View style={styles.track}>
        <View style={[styles.fill, { width: `${pct}%` }]} />
      </View>
    </View>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <View style={styles.fact}>
      <Text style={type.caption}>{label}</Text>
      <Text style={[type.body, styles.factValue]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    backgroundColor: colors.trust50,
    borderRadius: radius.pill,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2,
  },
  badgeText: { color: colors.trust500, fontWeight: '600' },
  placeholder: { backgroundColor: colors.accent50, borderColor: colors.accent100 },
  trait: { gap: spacing.xs },
  traitHeader: { flexDirection: 'row', justifyContent: 'space-between' },
  track: { height: 10, borderRadius: radius.pill, backgroundColor: colors.gray100, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: radius.pill, backgroundColor: colors.primary500 },
  facts: { gap: spacing.sm, marginTop: spacing.sm },
  fact: { gap: 2 },
  factValue: { fontWeight: '600', color: colors.gray800 },
});
