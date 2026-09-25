import { ActivityIndicator, Pressable, StyleSheet, Text } from 'react-native';

import { colors, radius, spacing, touchTarget } from '@/theme';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

interface Props {
  label: string;
  onPress: () => void;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
  /** Screen-reader label when it should differ from the visible label. */
  accessibilityLabel?: string;
  accessibilityHint?: string;
}

export function Button({
  label,
  onPress,
  variant = 'primary',
  loading = false,
  disabled = false,
  accessibilityLabel,
  accessibilityHint,
}: Props) {
  const inactive = disabled || loading;
  const v = variants[variant];
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? label}
      accessibilityHint={accessibilityHint}
      accessibilityState={{ disabled: inactive, busy: loading }}
      disabled={inactive}
      onPress={onPress}
      style={({ pressed }) => [
        styles.base,
        v.container,
        pressed && !inactive && styles.pressed,
        inactive && styles.inactive,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={v.spinner} />
      ) : (
        <Text style={[styles.text, v.text]}>{label}</Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: touchTarget,
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.md,
    borderRadius: radius.lg,
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: { fontSize: 16, fontWeight: '600', textAlign: 'center' },
  pressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  inactive: { opacity: 0.5 },
});

const variants = {
  primary: {
    container: { backgroundColor: colors.primary500 },
    text: { color: colors.white },
    spinner: colors.white,
  },
  secondary: {
    container: {
      backgroundColor: colors.surface,
      borderWidth: 2,
      borderColor: colors.border,
    },
    text: { color: colors.text },
    spinner: colors.primary500,
  },
  ghost: {
    container: { backgroundColor: 'transparent' },
    text: { color: colors.primary600 },
    spinner: colors.primary500,
  },
  danger: {
    container: { backgroundColor: colors.surface, borderWidth: 2, borderColor: colors.danger50 },
    text: { color: colors.danger700 },
    spinner: colors.danger600,
  },
} as const;
