import { StyleSheet, Text, View } from 'react-native';

import type { BigFive, PsychologicalProfile } from '@/api/types';
import { Card } from '@/components/feedback';
import { colors, radius, spacing, typography } from '@/theme';

/**
 * Plain-language, two-ended descriptions. Neither end is "better"; scores are tendencies from
 * one questionnaire, not measurements. Neuroticism is shown inverted as emotional steadiness.
 */
const TRAITS: { key: keyof BigFive; left: string; right: string; invert?: boolean }[] = [
  { key: 'extraversion', left: 'More reserved', right: 'More outgoing' },
  { key: 'openness', left: 'Enjoys the familiar', right: 'Seeks new experiences' },
  { key: 'conscientiousness', left: 'Spontaneous', right: 'Planful' },
  { key: 'agreeableness', left: 'Frank & challenging', right: 'Warm & accommodating' },
  { key: 'neuroticism', left: 'Feels things intensely', right: 'Even-keeled', invert: true },
];

const LOVE_LANGUAGE_LABELS: Record<string, string> = {
  words: 'kind words',
  acts: 'helpful actions',
  gifts: 'thoughtful gifts',
  time: 'quality time',
  touch: 'physical closeness',
};

const COMMUNICATION_LABELS: Record<string, string> = {
  direct: 'direct',
  diplomatic: 'diplomatic',
  emotional: 'expressive',
  logical: 'logical',
};

const CONFLICT_LABELS: Record<string, string> = {
  direct: 'address things head-on',
  reflective: 'take time to reflect first',
  collaborative: 'work it through together',
  avoidant: 'let things cool down before talking',
};

function topKey(scores: Record<string, number>): string | null {
  let best: string | null = null;
  for (const [k, v] of Object.entries(scores)) {
    if (best === null || v > (scores[best] ?? -Infinity)) best = k;
  }
  return best;
}

export function PersonalitySnapshot({ profile }: { profile: PsychologicalProfile }) {
  const love = topKey(profile.love_languages);
  const comm = COMMUNICATION_LABELS[profile.communication_style];
  const conflict = CONFLICT_LABELS[profile.conflict_resolution];

  return (
    <Card>
      <Text style={typography.heading} accessibilityRole="header">
        Your personality snapshot
      </Text>
      <Text style={typography.small}>
        Based on your answers — a rough sketch, not a verdict. People are more than five sliders,
        and your answers can change over time.
      </Text>

      <View style={styles.traits}>
        {TRAITS.map((t) => {
          const raw = profile.big_five[t.key];
          const value = Math.max(0, Math.min(100, t.invert ? 100 - raw : raw));
          const leaning =
            value >= 60 ? t.right.toLowerCase() : value <= 40 ? t.left.toLowerCase() : 'balanced';
          return (
            <View
              key={t.key}
              style={styles.trait}
              accessible
              accessibilityLabel={`${t.left} to ${t.right}: you lean ${leaning}`}
            >
              <View style={styles.track}>
                <View style={styles.midline} />
                <View style={[styles.marker, { left: `${value}%` }]} />
              </View>
              <View style={styles.ends}>
                <Text style={[styles.end, styles.left]}>{t.left}</Text>
                <Text style={[styles.end, styles.right]}>{t.right}</Text>
              </View>
            </View>
          );
        })}
      </View>

      {comm || conflict || love ? (
        <View style={styles.notes}>
          {comm ? (
            <Text style={typography.body}>• You tend to communicate in a {comm} way.</Text>
          ) : null}
          {conflict ? (
            <Text style={typography.body}>• In disagreements you often prefer to {conflict}.</Text>
          ) : null}
          {love && LOVE_LANGUAGE_LABELS[love] ? (
            <Text style={typography.body}>
              • You may especially value {LOVE_LANGUAGE_LABELS[love]}.
            </Text>
          ) : null}
        </View>
      ) : null}
    </Card>
  );
}

const MARKER = 18;

const styles = StyleSheet.create({
  traits: { gap: spacing.lg, marginTop: spacing.sm },
  trait: { gap: spacing.xs },
  track: {
    height: 10,
    borderRadius: radius.pill,
    backgroundColor: colors.primary50,
    justifyContent: 'center',
    marginHorizontal: MARKER / 2,
  },
  midline: {
    position: 'absolute',
    left: '50%',
    width: 2,
    height: 10,
    backgroundColor: colors.primary100,
  },
  marker: {
    position: 'absolute',
    width: MARKER,
    height: MARKER,
    marginLeft: -MARKER / 2,
    borderRadius: MARKER / 2,
    backgroundColor: colors.primary500,
    borderWidth: 3,
    borderColor: colors.white,
  },
  ends: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md },
  end: { flex: 1, fontSize: 13, color: colors.textMuted },
  left: { textAlign: 'left' },
  right: { textAlign: 'right' },
  notes: { gap: spacing.xs, marginTop: spacing.sm },
});
