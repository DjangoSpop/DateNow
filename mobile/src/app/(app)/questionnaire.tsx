import { router } from 'expo-router';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Animated, StyleSheet, Text, View } from 'react-native';

import * as endpoints from '@/api/endpoints';
import { describeError, isApiError } from '@/api/errors';
import type { AnswerValue } from '@/api/types';
import { useAuthStore } from '@/auth/authStore';
import { Button } from '@/components/Button';
import { Banner, Card, ErrorState, LoadingState, ProgressBar } from '@/components/feedback';
import { Screen } from '@/components/Screen';
import {
  countAnsweredRequired,
  firstIndexOfIds,
  firstMissingIndex,
  flattenQuestions,
  isValidAnswer,
  type FlatQuestion,
} from '@/features/questionnaire/progress';
import { QuestionView } from '@/features/questionnaire/QuestionView';
import { useQuestionnaireStore } from '@/features/questionnaire/questionnaireStore';
import { SaveIndicator } from '@/features/questionnaire/SaveIndicator';
import { colors, spacing, typography } from '@/theme';

type Step = { kind: 'question'; index: number } | { kind: 'review' };

const AUTO_ADVANCE_MS = 350;

export default function QuestionnaireScreen() {
  const definition = useQuestionnaireStore((s) => s.definition);
  const loadStatus = useQuestionnaireStore((s) => s.loadStatus);
  const loadError = useQuestionnaireStore((s) => s.loadError);
  const answers = useQuestionnaireStore((s) => s.answers);
  const save = useQuestionnaireStore((s) => s.save);
  const load = useQuestionnaireStore((s) => s.load);
  const answer = useQuestionnaireStore((s) => s.answer);
  const flush = useQuestionnaireStore((s) => s.flush);

  const [chosenStep, setStep] = useState<Step | null>(null);

  useEffect(() => {
    void load();
  }, [load]);

  const flat = useMemo(() => (definition ? flattenQuestions(definition) : []), [definition]);

  // Resume at the first unanswered required question (or the review step). Computed from the
  // answers known when the definition arrives; after that the user's navigation takes over.
  const resumeStep = useMemo<Step | null>(() => {
    if (flat.length === 0) return null;
    const idx = firstMissingIndex(flat, useQuestionnaireStore.getState().answers);
    return idx === -1 ? { kind: 'review' } : { kind: 'question', index: idx };
  }, [flat]);
  const step = chosenStep ?? resumeStep;

  if (loadStatus === 'error' && !definition) {
    return (
      <ErrorState message={describeError(loadError)} onRetry={() => void load()} />
    );
  }
  if (!definition || (loadStatus !== 'ready' && step === null)) {
    return <LoadingState label="Loading your questionnaire…" />;
  }
  if (flat.length === 0 || step === null) {
    return <ErrorState message="The questionnaire is empty right now. Please try again later." onRetry={() => void load()} />;
  }

  const progress = countAnsweredRequired(flat, answers);

  if (step.kind === 'review') {
    return (
      <ReviewStep
        flat={flat}
        progress={progress}
        onJump={(index) => setStep({ kind: 'question', index })}
        flush={flush}
        saveIndicator={<SaveIndicator save={save} />}
      />
    );
  }

  return (
    <QuestionStep
      flat={flat}
      index={step.index}
      value={answers[flat[step.index]!.question.id]}
      progress={progress}
      rejectedMessage={save.rejected[flat[step.index]!.question.id]}
      saveIndicator={<SaveIndicator save={save} />}
      onAnswer={(v) => answer(flat[step.index]!.question.id, v)}
      onBack={() => setStep(step.index > 0 ? { kind: 'question', index: step.index - 1 } : step)}
      onNext={() =>
        setStep(
          step.index < flat.length - 1
            ? { kind: 'question', index: step.index + 1 }
            : { kind: 'review' },
        )
      }
      onReview={() => setStep({ kind: 'review' })}
    />
  );
}

function QuestionStep({
  flat,
  index,
  value,
  progress,
  rejectedMessage,
  saveIndicator,
  onAnswer,
  onBack,
  onNext,
  onReview,
}: {
  flat: FlatQuestion[];
  index: number;
  value: AnswerValue | undefined;
  progress: { answered: number; total: number };
  rejectedMessage: string | undefined;
  saveIndicator: ReactNode;
  onAnswer: (v: AnswerValue) => void;
  onBack: () => void;
  onNext: () => void;
  onReview: () => void;
}) {
  const item = flat[index]!;
  const { question, section, sectionIndex, indexInSection } = item;
  const answered = isValidAnswer(question, value);
  const canContinue = answered || !question.required;
  const [fade] = useState(() => new Animated.Value(0));
  const advanceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Gentle fade between questions.
  useEffect(() => {
    fade.setValue(0);
    Animated.timing(fade, { toValue: 1, duration: 220, useNativeDriver: true }).start();
    return () => {
      if (advanceTimer.current) clearTimeout(advanceTimer.current);
    };
  }, [index, fade]);

  const handleAnswer = (v: AnswerValue) => {
    const firstTime = !answered;
    onAnswer(v);
    // Only auto-advance on a first answer; changing an answer lets the user stay and review.
    if (firstTime) {
      if (advanceTimer.current) clearTimeout(advanceTimer.current);
      advanceTimer.current = setTimeout(onNext, AUTO_ADVANCE_MS);
    }
  };

  return (
    <Screen
      footer={
        <View style={styles.nav}>
          <View style={styles.navButton}>
            <Button label="Back" variant="secondary" onPress={onBack} disabled={index === 0} />
          </View>
          <View style={styles.navButton}>
            <Button
              label={index === flat.length - 1 ? 'Review' : 'Next'}
              onPress={onNext}
              disabled={!canContinue}
              accessibilityHint={canContinue ? undefined : 'Choose an answer first'}
            />
          </View>
        </View>
      }
    >
      <View style={styles.topRow}>
        <Text style={styles.section}>
          {section.title} · {indexInSection + 1}/{section.questions.length}
        </Text>
        {saveIndicator}
      </View>
      <ProgressBar
        value={progress.total ? progress.answered / progress.total : 0}
        label={`${progress.answered} of ${progress.total} answered`}
      />
      <Text style={typography.small}>
        {progress.answered} of {progress.total} answered · Question {index + 1} of {flat.length}
      </Text>

      {indexInSection === 0 ? (
        <Card>
          <Text style={typography.heading}>{section.title}</Text>
          {section.description ? <Text style={styles.muted}>{section.description}</Text> : null}
          <Text style={typography.small}>
            Part {sectionIndex + 1} · about {section.estimated_minutes} min. There are no right or
            wrong answers.
          </Text>
        </Card>
      ) : null}

      <Animated.View style={{ opacity: fade }}>
        <QuestionView question={question} value={value} onAnswer={handleAnswer} />
      </Animated.View>

      {rejectedMessage ? (
        <Banner tone="error">That answer couldn&apos;t be saved ({rejectedMessage}). Please answer again.</Banner>
      ) : null}

      <Button label="Jump to review" variant="ghost" onPress={onReview} />
    </Screen>
  );
}

function ReviewStep({
  flat,
  progress,
  onJump,
  flush,
  saveIndicator,
}: {
  flat: FlatQuestion[];
  progress: { answered: number; total: number };
  onJump: (index: number) => void;
  flush: () => Promise<boolean>;
  saveIndicator: ReactNode;
}) {
  const answers = useQuestionnaireStore((s) => s.answers);
  const patchOnboarding = useAuthStore((s) => s.patchOnboarding);
  const refreshMe = useAuthStore((s) => s.refreshMe);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sections = useMemo(() => {
    const out: { title: string; firstIndex: number; answered: number; required: number; firstMissing: number }[] = [];
    flat.forEach((f, i) => {
      let s = out[f.sectionIndex];
      if (!s) {
        s = { title: f.section.title, firstIndex: i, answered: 0, required: 0, firstMissing: -1 };
        out[f.sectionIndex] = s;
      }
      if (f.question.required) {
        s.required += 1;
        if (isValidAnswer(f.question, answers[f.question.id])) s.answered += 1;
        else if (s.firstMissing === -1) s.firstMissing = i;
      }
    });
    return out;
  }, [flat, answers]);

  const missingIndex = firstMissingIndex(flat, answers);

  async function submit() {
    setError(null);
    if (missingIndex !== -1) {
      onJump(missingIndex);
      return;
    }
    setSubmitting(true);
    try {
      const saved = await flush();
      if (!saved) {
        setError(
          "Some answers haven't been saved yet. Check your connection — we'll keep retrying, and nothing you've entered is lost.",
        );
        return;
      }
      await endpoints.submitQuestionnaire();
      patchOnboarding({ questionnaire_complete: true });
      void refreshMe();
      router.replace('/home');
    } catch (e) {
      if (isApiError(e) && e.code === 'QUESTIONNAIRE_INCOMPLETE') {
        const idx = firstIndexOfIds(flat, Object.keys(e.fields ?? {}));
        const target = idx !== -1 ? idx : firstMissingIndex(flat, answers);
        if (target !== -1) {
          onJump(target);
          return;
        }
      }
      setError(describeError(e));
    } finally {
      setSubmitting(false);
    }
  }

  const complete = missingIndex === -1;

  return (
    <Screen
      footer={
        <Button
          label={complete ? 'See my results' : 'Continue where I left off'}
          onPress={() => void submit()}
          loading={submitting}
        />
      }
    >
      <View style={styles.topRow}>
        <Text style={typography.title} accessibilityRole="header">
          Review
        </Text>
        {saveIndicator}
      </View>
      <ProgressBar
        value={progress.total ? progress.answered / progress.total : 0}
        label={`${progress.answered} of ${progress.total} answered`}
      />
      <Text style={styles.muted}>
        {complete
          ? 'You’ve answered everything. You can revisit any part before seeing your results.'
          : `${progress.total - progress.answered} questions left. Pick up where you left off whenever you're ready.`}
      </Text>
      {error ? <Banner tone="error">{error}</Banner> : null}

      {sections.map((s) => (
        <Card key={s.title}>
          <Text style={typography.heading}>{s.title}</Text>
          <Text style={styles.muted}>
            {s.answered} of {s.required} answered
          </Text>
          <Button
            label={s.firstMissing !== -1 ? 'Continue this part' : 'Revisit answers'}
            variant="secondary"
            onPress={() => onJump(s.firstMissing !== -1 ? s.firstMissing : s.firstIndex)}
            accessibilityLabel={`${s.firstMissing !== -1 ? 'Continue' : 'Revisit'} ${s.title}`}
          />
        </Card>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: spacing.sm,
  },
  section: { fontSize: 14, fontWeight: '600', color: colors.accent600, flexShrink: 1 },
  muted: { ...typography.body, color: colors.textMuted },
  nav: { flexDirection: 'row', gap: spacing.md },
  navButton: { flex: 1 },
});
