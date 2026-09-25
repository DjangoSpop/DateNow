import { forwardRef, useState } from 'react';
import { StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';

import { colors, radius, spacing, touchTarget, typography } from '@/theme';

interface Props extends Omit<TextInputProps, 'style'> {
  label: string;
  error?: string;
  hint?: string;
  /** Allows a compact field inside a row (e.g. date parts). */
  flex?: number;
}

export const TextField = forwardRef<TextInput, Props>(function TextField(
  { label, error, hint, flex, onFocus, onBlur, ...inputProps },
  ref,
) {
  const [focused, setFocused] = useState(false);
  const describedBy = error ?? hint;
  return (
    <View style={[styles.wrapper, flex !== undefined && { flex }]}>
      <Text style={typography.label}>{label}</Text>
      <TextInput
        ref={ref}
        accessibilityLabel={label}
        accessibilityHint={describedBy}
        placeholderTextColor={colors.textSubtle}
        style={[styles.input, focused && styles.focused, !!error && styles.errored]}
        onFocus={(e) => {
          setFocused(true);
          onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          onBlur?.(e);
        }}
        {...inputProps}
      />
      {error ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {error}
        </Text>
      ) : hint ? (
        <Text style={typography.small}>{hint}</Text>
      ) : null}
    </View>
  );
});

const styles = StyleSheet.create({
  wrapper: { gap: spacing.xs },
  input: {
    minHeight: touchTarget,
    borderWidth: 2,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    fontSize: 16,
    color: colors.text,
    backgroundColor: colors.surface,
  },
  focused: { borderColor: colors.primary400 },
  errored: { borderColor: colors.danger600 },
  error: { fontSize: 14, color: colors.danger700 },
});
