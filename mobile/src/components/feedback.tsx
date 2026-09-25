import type { ReactNode } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { Button } from './Button';
import { colors, radius, shadow, spacing, typography } from '@/theme';

export function Card({ children }: { children: ReactNode }) {
  return <View style={styles.card}>{children}</View>;
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <View style={styles.center} accessibilityRole="progressbar" accessibilityLabel={label}>
      <ActivityIndicator size="large" color={colors.primary500} />
      <Text style={styles.muted}>{label}</Text>
    </View>
  );
}

export function ErrorState({
  message,
  onRetry,
  retrying = false,
}: {
  message: string;
  onRetry?: () => void;
  retrying?: boolean;
}) {
  return (
    <View style={styles.center}>
      <Text style={typography.heading} accessibilityRole="header">
        Something didn&apos;t load
      </Text>
      <Text style={[styles.muted, styles.textCenter]} accessibilityLiveRegion="polite">
        {message}
      </Text>
      {onRetry ? <Button label="Try again" onPress={onRetry} loading={retrying} /> : null}
    </View>
  );
}

type BannerTone = 'info' | 'error' | 'warning' | 'success';

export function Banner({ tone = 'info', children }: { tone?: BannerTone; children: ReactNode }) {
  const t = tones[tone];
  return (
    <View
      style={[styles.banner, { backgroundColor: t.bg }]}
      accessibilityLiveRegion="polite"
      accessibilityRole={tone === 'error' ? 'alert' : 'text'}
    >
      <Text style={[styles.bannerText, { color: t.fg }]}>{children}</Text>
    </View>
  );
}

export function ProgressBar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(1, value));
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityLabel={label}
      accessibilityValue={{ min: 0, max: 100, now: Math.round(pct * 100) }}
      style={styles.track}
    >
      <View style={[styles.fill, { width: `${pct * 100}%` }]} />
    </View>
  );
}

const tones: Record<BannerTone, { bg: string; fg: string }> = {
  info: { bg: colors.primary50, fg: colors.primary700 },
  error: { bg: colors.danger50, fg: colors.danger700 },
  warning: { bg: colors.warn50, fg: colors.warn700 },
  success: { bg: colors.trust50, fg: colors.trust700 },
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.xl,
    padding: spacing.xl,
    gap: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    ...shadow.card,
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.lg,
    padding: spacing.xl,
  },
  muted: { ...typography.body, color: colors.textMuted },
  textCenter: { textAlign: 'center' },
  banner: { borderRadius: radius.md, padding: spacing.md },
  bannerText: { fontSize: 15, lineHeight: 21 },
  track: {
    height: 8,
    borderRadius: radius.pill,
    backgroundColor: colors.primary50,
    overflow: 'hidden',
  },
  fill: { height: '100%', borderRadius: radius.pill, backgroundColor: colors.primary500 },
});
