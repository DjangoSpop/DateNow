import { useCallback, useEffect, useRef, useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { ApiError, isApiError } from '../api/errors';
import { onboarding } from '../api/onboarding';
import { questionnaire } from '../api/questionnaire';
import type { AnswerValue, Answers, QuestionnaireDefinition } from '../api/types';
import { QuestionView } from '../components/questions/QuestionView';
import { Button, Card, ErrorBanner, InfoBanner, LoadingView, ProgressBar, Screen } from '../components/ui';
import { clearLocalDraft, loadLocalDraft, saveLocalDraft } from '../onboarding/draftStorage';
import {
  allMissingRequiredIds,
  firstSectionIndexContaining,
  invalidQuestionIdsFromError,
  isAnswered,
  missingRequiredIds,
  progressFraction,
  resolveResumeState,
  sanitizeAnswers,
  validateAnswer,
} from '../onboarding/logic';
import { useAuthStore } from '../state/authStore';
import { colors, spacing, type } from '../theme';

const AUTOSAVE_DEBOUNCE_MS = 1500;

type LoadState =
  | { kind: 'loading' }
  | { kind: 'error'; error: ApiError }
  | { kind: 'ready'; def: QuestionnaireDefinition };

type SyncState = 'idle' | 'saving' | 'saved' | 'offline';

export default function OnboardingScreen() {
  const me = useAuthStore((s) => s.me);
  const refreshMe = useAuthStore((s) => s.refreshMe);
  const logout = useAuthStore((s) => s.logout);
  const userId = me?.id ?? 0;

  const [load, setLoad] = useState<LoadState>({ kind: 'loading' });
  const [answers, setAnswers] = useState<Answers>({});
  /** 0..sections-1 = a section; sections.length = final review. */
  const [index, setIndex] = useState(0);
  const [questionErrors, setQuestionErrors] = useState<Record<string, string>>({});
  const [sync, setSync] = useState<SyncState>('idle');
  const [banner, setBanner] = useState<{ message: string; retry?: () => void } | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const answersRef = useRef<Answers>({});
  const sectionIdRef = useRef<string | null>(null);
  const defRef = useRef<QuestionnaireDefinition | null>(null);
  const pendingRef = useRef(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const saveChain = useRef<Promise<void>>(Promise.resolve());
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const mirrorLocally = useCallback(
    (pendingSync: boolean) => {
      if (!userId) return;
      void saveLocalDraft(userId, {
        answers: answersRef.current,
        currentSection: sectionIdRef.current,
        pendingSync,
        savedAt: new Date().toISOString(),
      });
    },
    [userId],
  );

  const handleCompletedElsewhere = useCallback(async () => {
    if (userId) await clearLocalDraft(userId);
    try {
      await refreshMe();
    } catch {
      /* root layout keeps the user here; a retry banner is shown by the caller */
    }
  }, [refreshMe, userId]);

  /** PUT /onboarding with the current draft. Saves are serialized so section order is preserved. */
  const saveDraft = useCallback((): Promise<void> => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
      debounceRef.current = null;
    }
    const run = async () => {
      const def = defRef.current;
      if (!def) return;
      const body = {
        current_section: sectionIdRef.current,
        answers: sanitizeAnswers(def, answersRef.current),
      };
      if (mounted.current) setSync('saving');
      try {
        await onboarding.saveDraft(body);
        pendingRef.current = false;
        mirrorLocally(false);
        if (mounted.current) setSync('saved');
      } catch (e) {
        if (!mounted.current) return;
        if (!isApiError(e)) {
          setSync('offline');
          return;
        }
        if (e.code === 'network' || e.code === 'timeout' || e.code === 'server') {
          setSync('offline'); // kept locally with pendingSync=true; retried on the next save
        } else if (e.code === 'conflict') {
          await handleCompletedElsewhere();
        } else if (e.code === 'validation') {
          const ids = invalidQuestionIdsFromError(def, e);
          setQuestionErrors((prev) => {
            const next = { ...prev };
            for (const id of ids) next[id] = e.fieldErrors?.[id] ?? 'Please check this answer.';
            return next;
          });
          setSync('idle');
        } else {
          setSync('idle');
        }
      }
    };
    saveChain.current = saveChain.current.then(run, run);
    return saveChain.current;
  }, [handleCompletedElsewhere, mirrorLocally]);

  // Initial state is already 'loading'; retry() resets it before calling this again.
  const initialise = useCallback(async () => {
    try {
      const [def, server, local] = await Promise.all([
        questionnaire.get(),
        onboarding.get(),
        userId ? loadLocalDraft(userId) : Promise.resolve(null),
      ]);
      if (server.status === 'completed') {
        await handleCompletedElsewhere();
        return;
      }
      const resume = resolveResumeState(def, server, local);
      defRef.current = def;
      answersRef.current = resume.answers;
      sectionIdRef.current = def.sections[resume.sectionIndex]?.id ?? null;
      pendingRef.current = resume.pendingSync;
      setAnswers(resume.answers);
      setIndex(resume.sectionIndex);
      setLoad({ kind: 'ready', def });
      if (resume.pendingSync) void saveDraft();
    } catch (e) {
      setLoad({
        kind: 'error',
        error: isApiError(e)
          ? e
          : new ApiError({ status: 0, code: 'unknown', message: 'Something unexpected happened.' }),
      });
    }
  }, [handleCompletedElsewhere, saveDraft, userId]);

  useEffect(() => {
    void initialise();
  }, [initialise]);

  function onAnswer(questionId: string, value: AnswerValue) {
    const next = { ...answersRef.current, [questionId]: value };
    answersRef.current = next;
    pendingRef.current = true;
    setAnswers(next);
    if (questionErrors[questionId]) {
      setQuestionErrors((prev) => {
        const copy = { ...prev };
        delete copy[questionId];
        return copy;
      });
    }
    mirrorLocally(true);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => void saveDraft(), AUTOSAVE_DEBOUNCE_MS);
  }

  function goTo(nextIndex: number, def: QuestionnaireDefinition) {
    const clamped = Math.max(0, Math.min(def.sections.length, nextIndex));
    setIndex(clamped);
    // Review is not a section; keep pointing at the last section for resume purposes.
    sectionIdRef.current = def.sections[Math.min(clamped, def.sections.length - 1)]?.id ?? null;
    mirrorLocally(pendingRef.current);
    void saveDraft();
  }

  function onNext(def: QuestionnaireDefinition) {
    const section = def.sections[index];
    const missing = missingRequiredIds(section, answersRef.current);
    if (missing.length) {
      const errs: Record<string, string> = {};
      for (const id of missing) {
        const q = section.questions.find((x) => x.id === id)!;
        errs[id] = validateAnswer(q, answersRef.current[id]) ?? 'Please answer this question.';
      }
      setQuestionErrors((prev) => ({ ...prev, ...errs }));
      setBanner({ message: `Please answer the ${missing.length === 1 ? 'highlighted question' : `${missing.length} highlighted questions`} to continue.` });
      return;
    }
    setBanner(null);
    goTo(index + 1, def);
  }

  async function onSubmit(def: QuestionnaireDefinition) {
    const missing = allMissingRequiredIds(def, answersRef.current);
    if (missing.length) {
      jumpToIds(def, missing, 'A few questions still need an answer.');
      return;
    }
    setSubmitting(true);
    setBanner(null);
    try {
      if (debounceRef.current) clearTimeout(debounceRef.current);
      // Raw answers only — the server computes every score.
      await questionnaire.submit(sanitizeAnswers(def, answersRef.current));
      if (userId) await clearLocalDraft(userId);
      await refreshMe(); // onboarding_status → completed; root layout routes to home.
    } catch (e) {
      if (!isApiError(e)) {
        setBanner({ message: 'Something unexpected happened.', retry: () => void onSubmit(def) });
      } else if (e.code === 'validation') {
        const ids = invalidQuestionIdsFromError(def, e);
        if (ids.length) {
          const errs: Record<string, string> = {};
          for (const id of ids) errs[id] = e.fieldErrors?.[id] ?? 'Please check this answer.';
          setQuestionErrors((prev) => ({ ...prev, ...errs }));
          jumpToIds(def, ids, 'Some answers need another look.');
        } else {
          setBanner({ message: e.message });
        }
      } else if (e.code === 'conflict') {
        await handleCompletedElsewhere();
      } else {
        setBanner({ message: e.message, retry: () => void onSubmit(def) });
      }
    } finally {
      if (mounted.current) setSubmitting(false);
    }
  }

  function jumpToIds(def: QuestionnaireDefinition, ids: string[], message: string) {
    const target = firstSectionIndexContaining(def, ids);
    if (target >= 0) {
      const errs: Record<string, string> = {};
      for (const id of ids) errs[id] = questionErrors[id] ?? 'Please answer this question.';
      setQuestionErrors((prev) => ({ ...errs, ...prev }));
      setIndex(target);
      sectionIdRef.current = def.sections[target].id;
    }
    setBanner({ message });
  }

  if (load.kind === 'loading') return <LoadingView label="Preparing your questions" />;
  if (load.kind === 'error') {
    return (
      <Screen>
        <Text style={type.title} accessibilityRole="header">
          Let&apos;s get to know you
        </Text>
        <ErrorBanner
          message={load.error.message}
          onRetry={() => {
            setLoad({ kind: 'loading' });
            void initialise();
          }}
        />
        <Button label="Sign out" variant="ghost" onPress={() => void logout()} />
      </Screen>
    );
  }

  const { def } = load;
  const isReview = index >= def.sections.length;
  const section = isReview ? null : def.sections[index];
  const progress = progressFraction(def, answers);
  const questionOffset = def.sections.slice(0, index).reduce((n, s) => n + s.questions.length, 0);

  const footer = isReview ? (
    <>
      <Button label="Back" variant="secondary" onPress={() => goTo(index - 1, def)} style={styles.flex} />
      <Button label="Submit" onPress={() => void onSubmit(def)} loading={submitting} style={styles.flex2} />
    </>
  ) : (
    <>
      <Button
        label="Back"
        variant="secondary"
        onPress={() => goTo(index - 1, def)}
        disabled={index === 0}
        style={styles.flex}
      />
      <Button
        label={index === def.sections.length - 1 ? 'Review' : 'Next'}
        onPress={() => onNext(def)}
        style={styles.flex2}
      />
    </>
  );

  return (
    <Screen key={index} footer={footer}>
      <View style={styles.header}>
        <View style={styles.headerRow}>
          <Text style={type.caption}>
            {isReview ? 'Review' : `Section ${index + 1} of ${def.sections.length}`}
          </Text>
          <SyncIndicator state={sync} />
        </View>
        <ProgressBar value={progress} label={`Questionnaire ${Math.round(progress * 100)} percent answered`} />
      </View>

      {banner ? <ErrorBanner message={banner.message} onRetry={banner.retry} /> : null}
      {sync === 'offline' ? (
        <InfoBanner message="You seem to be offline. Your answers are saved on this device and will sync when you reconnect." />
      ) : null}

      {section ? (
        <>
          <Text style={type.title} accessibilityRole="header">
            {section.title}
          </Text>
          {section.description ? <Text style={type.body}>{section.description}</Text> : null}
          <Card>
            {section.questions.map((q, i) => (
              <QuestionView
                key={q.id}
                number={questionOffset + i + 1}
                question={q}
                value={answers[q.id]}
                onChange={(v) => onAnswer(q.id, v)}
                error={questionErrors[q.id]}
              />
            ))}
          </Card>
        </>
      ) : (
        <>
          <Text style={type.title} accessibilityRole="header">
            Almost there
          </Text>
          <Text style={type.body}>
            Review your progress. You can revisit any section before submitting. Your answers are private and are
            used to build your compatibility profile.
          </Text>
          <Card>
            {def.sections.map((s, i) => {
              const answered = s.questions.filter((q) => isAnswered(q, answers[q.id])).length;
              const hasErrors = s.questions.some((q) => questionErrors[q.id]);
              return (
                <Pressable
                  key={s.id}
                  accessibilityRole="button"
                  accessibilityLabel={`${s.title}: ${answered} of ${s.questions.length} answered. Edit section`}
                  onPress={() => goTo(i, def)}
                  style={styles.reviewRow}
                >
                  <Text style={[type.body, styles.flex]}>{s.title}</Text>
                  <Text
                    style={[
                      type.caption,
                      answered === s.questions.length && !hasErrors ? styles.complete : styles.incomplete,
                    ]}
                  >
                    {answered}/{s.questions.length}
                  </Text>
                </Pressable>
              );
            })}
          </Card>
        </>
      )}
      <Button label="Sign out" variant="ghost" onPress={() => void logout()} />
    </Screen>
  );
}

function SyncIndicator({ state }: { state: SyncState }) {
  const label =
    state === 'saving' ? 'Saving…' : state === 'saved' ? 'Saved' : state === 'offline' ? 'Saved on device' : '';
  if (!label) return null;
  return (
    <Text style={type.caption} accessibilityLiveRegion="polite">
      {label}
    </Text>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  flex2: { flex: 2 },
  header: { gap: spacing.sm },
  headerRow: { flexDirection: 'row', justifyContent: 'space-between' },
  reviewRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm + 4,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.gray200,
    minHeight: 44,
  },
  complete: { color: colors.trust500, fontWeight: '600' },
  incomplete: { color: colors.accent600, fontWeight: '600' },
});
