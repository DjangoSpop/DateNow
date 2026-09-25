import { create } from 'zustand';

import * as endpoints from '@/api/endpoints';
import { ApiError, isApiError } from '@/api/errors';
import type { AnswerValue, Answers, Questionnaire, QuestionnaireState } from '@/api/types';
import { useAuthStore } from '@/auth/authStore';
import { AutosaveQueue, type SaveSnapshot } from './autosaveQueue';

type LoadStatus = 'idle' | 'loading' | 'ready' | 'error';

interface QuestionnaireStore {
  definition: Questionnaire | null;
  serverState: QuestionnaireState | null;
  loadStatus: LoadStatus;
  loadError: ApiError | null;
  /** What the user sees: server answers overlaid with everything entered this session. */
  answers: Answers;
  save: SaveSnapshot;

  load(): Promise<void>;
  answer(questionId: string, value: AnswerValue): void;
  /** Push unsaved answers now; true when the server has everything. */
  flush(): Promise<boolean>;
  reset(): void;
}

const initialSave: SaveSnapshot = { status: 'idle', pending: 0, rejected: {} };

/**
 * Lives for the whole app session (not per screen) so answers survive navigating away and back.
 * Cleared when the user signs out.
 */
export const useQuestionnaireStore = create<QuestionnaireStore>()((set, get) => {
  const makeQueue = () =>
    new AutosaveQueue({
      save: async (batch) => {
        const state = await endpoints.saveAnswers(batch);
        set({ serverState: state });
        return state;
      },
      onChange: (snapshot) => {
        const prev = get().save;
        // Revert answers the server rejected so the user is prompted to answer them again.
        const newlyRejected = Object.keys(snapshot.rejected).filter((id) => !(id in prev.rejected));
        if (newlyRejected.length > 0) {
          const answers = { ...get().answers };
          const server = get().serverState?.answers ?? {};
          for (const id of newlyRejected) {
            if (id in server) answers[id] = server[id]!;
            else delete answers[id];
          }
          set({ answers, save: snapshot });
        } else {
          set({ save: snapshot });
        }
      },
    });

  let queue = makeQueue();

  return {
    definition: null,
    serverState: null,
    loadStatus: 'idle',
    loadError: null,
    answers: {},
    save: initialSave,

    async load() {
      set({ loadStatus: 'loading', loadError: null });
      try {
        const [definition, serverState] = await Promise.all([
          endpoints.getQuestionnaire(),
          endpoints.getQuestionnaireState(),
        ]);
        set({
          definition,
          serverState,
          // Local answers from this session win: they may not have reached the server yet.
          answers: { ...serverState.answers, ...get().answers },
          loadStatus: 'ready',
        });
      } catch (e) {
        set({
          loadStatus: 'error',
          loadError: isApiError(e) ? e : new ApiError(0, 'UNKNOWN_ERROR', String(e)),
        });
      }
    },

    answer(questionId, value) {
      set({ answers: { ...get().answers, [questionId]: value } });
      queue.enqueue(questionId, value);
    },

    flush() {
      return queue.flush();
    },

    reset() {
      queue.dispose();
      queue = makeQueue();
      set({
        definition: null,
        serverState: null,
        loadStatus: 'idle',
        loadError: null,
        answers: {},
        save: initialSave,
      });
    },
  };
});

// Never carry one user's answers into another user's session.
useAuthStore.subscribe((state, prev) => {
  if (state.status === 'signedOut' && prev.status !== 'signedOut') {
    useQuestionnaireStore.getState().reset();
  }
});
