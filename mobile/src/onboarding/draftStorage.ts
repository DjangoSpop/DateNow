import AsyncStorage from '@react-native-async-storage/async-storage';

import type { Answers } from '../api/types';

/**
 * Local mirror of the onboarding draft so progress survives network failures / app kills.
 * NON-SENSITIVE cache only (questionnaire answers + section id). Tokens never go here.
 */
export interface LocalDraft {
  currentSection: string | null;
  answers: Answers;
  /** true when the local copy has changes the server has not acknowledged yet. */
  pendingSync: boolean;
  savedAt: string;
}

export const DRAFT_KEY_PREFIX = 'datenow.onboardingDraft.';

export const draftKey = (userId: number) => `${DRAFT_KEY_PREFIX}${userId}`;

export async function loadLocalDraft(userId: number): Promise<LocalDraft | null> {
  try {
    const raw = await AsyncStorage.getItem(draftKey(userId));
    if (!raw) return null;
    const parsed = JSON.parse(raw) as LocalDraft;
    if (typeof parsed !== 'object' || parsed === null || typeof parsed.answers !== 'object') return null;
    return parsed;
  } catch {
    return null;
  }
}

export async function saveLocalDraft(userId: number, draft: LocalDraft): Promise<void> {
  try {
    await AsyncStorage.setItem(draftKey(userId), JSON.stringify(draft));
  } catch {
    // Best effort: the server draft remains the source of truth.
  }
}

export async function clearLocalDraft(userId: number): Promise<void> {
  try {
    await AsyncStorage.removeItem(draftKey(userId));
  } catch {
    // ignore
  }
}

/** Removes every cached draft (all users) — used on logout. */
export async function clearAllLocalDrafts(): Promise<void> {
  try {
    const keys = await AsyncStorage.getAllKeys();
    const ours = keys.filter((k) => k.startsWith(DRAFT_KEY_PREFIX));
    if (ours.length) await AsyncStorage.multiRemove(ours);
  } catch {
    // ignore
  }
}
