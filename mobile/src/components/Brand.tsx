import { StyleSheet, Text, View } from 'react-native';

import { colors, spacing, type } from '../theme';

export function Brand({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <View style={styles.container}>
      <View style={styles.logo} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
        <Text style={styles.logoText}>♥</Text>
      </View>
      <Text style={[type.title, styles.center]} accessibilityRole="header">
        {title}
      </Text>
      {subtitle ? <Text style={[type.body, styles.center, styles.subtitle]}>{subtitle}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', gap: spacing.sm, marginTop: spacing.xl, marginBottom: spacing.md },
  logo: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.accent50,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing.sm,
  },
  logoText: { fontSize: 32, color: colors.accent500 },
  center: { textAlign: 'center' },
  subtitle: { color: colors.gray500 },
});
