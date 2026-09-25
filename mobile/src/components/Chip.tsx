import { Pressable, StyleSheet, Text } from 'react-native';

import { colors, radius, spacing, touchTarget } from '@/theme';

interface Props {
  label: string;
  selected: boolean;
  onPress: () => void;
  /** 'checkbox' for multi-select groups, 'radio' for single-select. */
  role?: 'checkbox' | 'radio';
}

/** Selectable pill used for enum choices. */
export function Chip({ label, selected, onPress, role = 'radio' }: Props) {
  return (
    <Pressable
      accessibilityRole={role}
      accessibilityLabel={label}
      accessibilityState={role === 'checkbox' ? { checked: selected } : { selected }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.chip,
        selected && styles.selected,
        pressed && styles.pressed,
      ]}
    >
      <Text style={[styles.text, selected && styles.selectedText]}>
        {selected ? '✓ ' : ''}
        {label}
      </Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    minHeight: touchTarget,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderRadius: radius.pill,
    borderWidth: 2,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    justifyContent: 'center',
  },
  selected: { borderColor: colors.primary500, backgroundColor: colors.primary50 },
  pressed: { opacity: 0.85 },
  text: { fontSize: 15, color: colors.text },
  selectedText: { color: colors.primary700, fontWeight: '600' },
});
