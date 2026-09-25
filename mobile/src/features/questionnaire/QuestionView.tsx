import { Pressable, StyleSheet, Text, View } from 'react-native';

import type { AnswerValue, Question, ScaleQuestion, SingleChoiceQuestion } from '@/api/types';
import { colors, radius, spacing, touchTarget, typography } from '@/theme';

interface Props {
  question: Question;
  value: AnswerValue | undefined;
  onAnswer: (value: AnswerValue) => void;
}

export function QuestionView({ question, value, onAnswer }: Props) {
  return (
    <View style={styles.wrap}>
      <Text style={styles.prompt} accessibilityRole="header">
        {question.text}
      </Text>
      {question.type === 'scale' ? (
        <ScaleInput question={question} value={value} onAnswer={onAnswer} />
      ) : (
        <ChoiceInput question={question} value={value} onAnswer={onAnswer} />
      )}
      {!question.required ? <Text style={typography.small}>Optional</Text> : null}
    </View>
  );
}

function ScaleInput({
  question,
  value,
  onAnswer,
}: {
  question: ScaleQuestion;
  value: AnswerValue | undefined;
  onAnswer: (v: number) => void;
}) {
  const { min, max, labels } = question.scale;
  const points = Array.from({ length: max - min + 1 }, (_, i) => min + i);
  // Labels always come from the definition: they are not necessarily agree/disagree.
  const minLabel = labels[String(min)];
  const maxLabel = labels[String(max)];
  const hasInnerLabels = points.some((p) => p !== min && p !== max && labels[String(p)]);

  return (
    <View style={styles.scaleWrap} accessibilityRole="radiogroup">
      <View style={styles.scaleRow}>
        {points.map((p) => {
          const selected = value === p;
          const label = labels[String(p)];
          return (
            <Pressable
              key={p}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              accessibilityLabel={`${p} of ${max}${label ? `, ${label}` : ''}`}
              onPress={() => onAnswer(p)}
              style={({ pressed }) => [
                styles.scaleButton,
                selected && styles.selected,
                pressed && styles.pressed,
              ]}
            >
              <Text style={[styles.scaleNumber, selected && styles.selectedText]}>{p}</Text>
            </Pressable>
          );
        })}
      </View>
      {minLabel || maxLabel ? (
        <View style={styles.scaleEnds} importantForAccessibility="no-hide-descendants">
          <Text style={[typography.small, styles.endLeft]}>{minLabel ?? ''}</Text>
          <Text style={[typography.small, styles.endRight]}>{maxLabel ?? ''}</Text>
        </View>
      ) : null}
      {hasInnerLabels && typeof value === 'number' && labels[String(value)] ? (
        <Text style={[typography.small, styles.current]}>{labels[String(value)]}</Text>
      ) : null}
    </View>
  );
}

function ChoiceInput({
  question,
  value,
  onAnswer,
}: {
  question: SingleChoiceQuestion;
  value: AnswerValue | undefined;
  onAnswer: (v: string) => void;
}) {
  return (
    <View style={styles.choices} accessibilityRole="radiogroup">
      {question.options.map((o) => {
        const selected = value === o.value;
        return (
          <Pressable
            key={o.value}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            accessibilityLabel={o.label}
            // Send the option `value`, never the label.
            onPress={() => onAnswer(o.value)}
            style={({ pressed }) => [
              styles.choice,
              selected && styles.selected,
              pressed && styles.pressed,
            ]}
          >
            <View style={[styles.radio, selected && styles.radioOn]} />
            <Text style={[styles.choiceText, selected && styles.selectedText]}>{o.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.xl },
  prompt: { fontSize: 22, lineHeight: 30, fontWeight: '600', color: colors.text },
  scaleWrap: { gap: spacing.sm },
  scaleRow: { flexDirection: 'row', gap: spacing.sm },
  scaleButton: {
    flex: 1,
    minHeight: touchTarget + 8,
    borderRadius: radius.lg,
    borderWidth: 2,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scaleNumber: { fontSize: 20, fontWeight: '600', color: colors.textMuted },
  scaleEnds: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.lg },
  endLeft: { flex: 1, textAlign: 'left' },
  endRight: { flex: 1, textAlign: 'right' },
  current: { textAlign: 'center', color: colors.primary700 },
  choices: { gap: spacing.md },
  choice: {
    minHeight: touchTarget,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    padding: spacing.lg,
    borderRadius: radius.lg,
    borderWidth: 2,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  choiceText: { flex: 1, fontSize: 16, lineHeight: 22, color: colors.text },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.borderStrong,
  },
  radioOn: { borderColor: colors.primary500, backgroundColor: colors.primary500 },
  selected: { borderColor: colors.primary500, backgroundColor: colors.primary50 },
  selectedText: { color: colors.primary700, fontWeight: '600' },
  pressed: { opacity: 0.85 },
});
