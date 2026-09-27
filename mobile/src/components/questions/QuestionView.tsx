import { Pressable, StyleSheet, Text, TextInput, View } from 'react-native';

import type { AnswerValue, Question } from '../../api/types';
import { colors, radius, spacing, type } from '../../theme';
import { Chip } from '../ui';

interface Props {
  question: Question;
  value: AnswerValue | undefined;
  onChange: (value: AnswerValue) => void;
  error?: string;
  number: number;
}

/** Renders one server-defined question. Knows nothing about scoring. */
export function QuestionView({ question, value, onChange, error, number }: Props) {
  return (
    <View style={styles.container}>
      <Text style={styles.text} accessibilityRole="header">
        {number}. {question.text}
        {question.required ? '' : ' (optional)'}
      </Text>
      {question.type === 'scale' && <ScaleInput question={question} value={value} onChange={onChange} />}
      {question.type === 'single_choice' && (
        <View style={styles.options} accessibilityRole="radiogroup" accessibilityLabel={question.text}>
          {(question.options ?? []).map((opt) => (
            <Chip key={opt} label={opt} selected={value === opt} onPress={() => onChange(opt)} />
          ))}
        </View>
      )}
      {question.type === 'multiple_choice' && (
        <View style={styles.options} accessibilityLabel={question.text}>
          {(question.options ?? []).map((opt) => {
            const selected = Array.isArray(value) && value.includes(opt);
            return (
              <Chip
                key={opt}
                multi
                label={opt}
                selected={selected}
                onPress={() => {
                  const current = Array.isArray(value) ? value : [];
                  onChange(selected ? current.filter((v) => v !== opt) : [...current, opt]);
                }}
              />
            );
          })}
        </View>
      )}
      {question.type === 'text' && (
        <View>
          <TextInput
            accessibilityLabel={question.text}
            multiline
            value={typeof value === 'string' ? value : ''}
            onChangeText={onChange}
            maxLength={question.max_length ?? undefined}
            placeholder="Type your answer"
            placeholderTextColor={colors.gray400}
            style={[styles.textInput, error ? styles.textInputError : null]}
          />
          {question.max_length ? (
            <Text style={[type.caption, styles.counter]}>
              {(typeof value === 'string' ? value.length : 0)}/{question.max_length}
            </Text>
          ) : null}
        </View>
      )}
      {error ? (
        <Text style={styles.error} accessibilityLiveRegion="polite">
          {error}
        </Text>
      ) : null}
    </View>
  );
}

function ScaleInput({
  question,
  value,
  onChange,
}: {
  question: Question;
  value: AnswerValue | undefined;
  onChange: (v: number) => void;
}) {
  const min = question.scale?.min ?? 1;
  const max = question.scale?.max ?? 5;
  const steps: number[] = [];
  for (let i = min; i <= max; i += 1) steps.push(i);

  return (
    <View accessibilityRole="radiogroup" accessibilityLabel={question.text}>
      <View style={styles.scaleRow}>
        {steps.map((n) => {
          const selected = value === n;
          const edgeLabel =
            n === min ? question.scale?.min_label : n === max ? question.scale?.max_label : undefined;
          return (
            <Pressable
              key={n}
              accessibilityRole="radio"
              accessibilityLabel={edgeLabel ? `${n}, ${edgeLabel}` : String(n)}
              accessibilityState={{ selected }}
              onPress={() => onChange(n)}
              style={[styles.scaleDot, selected && styles.scaleDotSelected]}
            >
              <Text style={[styles.scaleText, selected && styles.scaleTextSelected]}>{n}</Text>
            </Pressable>
          );
        })}
      </View>
      {question.scale ? (
        <View style={styles.scaleLabels}>
          <Text style={[type.caption, styles.scaleLabelLeft]}>{question.scale.min_label}</Text>
          <Text style={[type.caption, styles.scaleLabelRight]}>{question.scale.max_label}</Text>
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing.sm + 4, paddingVertical: spacing.sm },
  text: { ...type.body, fontWeight: '600', color: colors.gray800 },
  options: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  scaleRow: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.sm },
  scaleDot: {
    flex: 1,
    minHeight: 48,
    borderRadius: radius.md,
    borderWidth: 2,
    borderColor: colors.gray200,
    backgroundColor: colors.white,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scaleDotSelected: { borderColor: colors.primary500, backgroundColor: colors.primary500 },
  scaleText: { fontSize: 16, fontWeight: '600', color: colors.gray600 },
  scaleTextSelected: { color: colors.white },
  scaleLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: spacing.xs, gap: spacing.md },
  scaleLabelLeft: { flex: 1 },
  scaleLabelRight: { flex: 1, textAlign: 'right' },
  textInput: {
    borderWidth: 2,
    borderColor: colors.gray200,
    borderRadius: radius.md,
    padding: spacing.md,
    minHeight: 110,
    fontSize: 16,
    color: colors.gray800,
    backgroundColor: colors.white,
    textAlignVertical: 'top',
  },
  textInputError: { borderColor: colors.danger700 },
  counter: { textAlign: 'right', marginTop: spacing.xs },
  error: { color: colors.danger700, fontSize: 13 },
});
