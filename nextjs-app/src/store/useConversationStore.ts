import { create } from 'zustand';
import { Message, SessionStage, ReadinessResult } from '../types';

interface ConversationState {
  sessionId: string | null;
  matchId: string | null;
  stage: SessionStage;
  messages: Message[];
  isModeratorTyping: boolean;
  user1Ready: boolean;
  user2Ready: boolean;
  readinessResult: ReadinessResult | null;

  // Actions
  setSession: (sessionId: string, matchId: string) => void;
  setStage: (stage: SessionStage) => void;
  addMessage: (message: Message) => void;
  setTyping: (isTyping: boolean) => void;
  setReady: (userId: string, isReady: boolean) => void;
  setReadinessResult: (result: ReadinessResult) => void;
  resetSession: () => void;
}

export const useConversationStore = create<ConversationState>((set) => ({
  sessionId: null,
  matchId: null,
  stage: 'consent',
  messages: [],
  isModeratorTyping: false,
  user1Ready: false,
  user2Ready: false,
  readinessResult: null,

  setSession: (sessionId, matchId) => set({ sessionId, matchId }),
  setStage: (stage) => set({ stage }),
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  setTyping: (isTyping) => set({ isModeratorTyping: isTyping }),
  setReady: (userId, isReady) => set((state) => {
    // In a real app, logic would distinguish between user1 and user2
    // Here we use a placeholder logic
    return { user1Ready: isReady };
  }),
  setReadinessResult: (result) => set({ readinessResult: result }),
  resetSession: () => set({
    sessionId: null,
    matchId: null,
    stage: 'consent',
    messages: [],
    isModeratorTyping: false,
    user1Ready: false,
    user2Ready: false,
    readinessResult: null,
  }),
}));
