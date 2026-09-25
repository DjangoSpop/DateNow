import * as SecureStore from 'expo-secure-store';

/**
 * Access + refresh tokens live ONLY in expo-secure-store (iOS Keychain / Android Keystore-backed
 * encrypted storage). Never AsyncStorage or any plaintext store.
 *
 * An in-memory copy avoids a Keychain round-trip on every API call; SecureStore is the source of
 * truth on cold start (`load`). SecureStore failures never throw out of this module: a failed read
 * is treated as "no session", a failed write keeps the in-memory session for this app run.
 */

export interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

export const ACCESS_TOKEN_KEY = 'datenow.access_token';
export const REFRESH_TOKEN_KEY = 'datenow.refresh_token';

const OPTIONS: SecureStore.SecureStoreOptions = {
  // Not synced to other devices / backups; readable once the device has been unlocked after boot.
  keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
};

let memory: StoredTokens | null = null;

function warn(action: string, e: unknown): void {
  // Never log token values, only the failure.
  const msg = e instanceof Error ? e.message : String(e);
  console.warn(`[tokenStorage] ${action} failed: ${msg}`);
}

/** Current tokens held in memory (synchronous; populated by `load` or `save`). */
export function getTokens(): StoredTokens | null {
  return memory;
}

/** Read tokens from SecureStore into memory. Returns null if absent, partial or unreadable. */
export async function loadTokens(): Promise<StoredTokens | null> {
  try {
    const [accessToken, refreshToken] = await Promise.all([
      SecureStore.getItemAsync(ACCESS_TOKEN_KEY, OPTIONS),
      SecureStore.getItemAsync(REFRESH_TOKEN_KEY, OPTIONS),
    ]);
    if (accessToken && refreshToken) {
      memory = { accessToken, refreshToken };
      return memory;
    }
    if (accessToken || refreshToken) {
      // A half-written pair can't be trusted; start clean.
      await clearTokens();
    }
    memory = null;
    return null;
  } catch (e) {
    warn('load', e);
    memory = null;
    return null;
  }
}

/** Persist a token pair. Returns false if SecureStore rejected the write (session stays in memory). */
export async function saveTokens(tokens: StoredTokens): Promise<boolean> {
  memory = tokens;
  try {
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, tokens.accessToken, OPTIONS);
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, tokens.refreshToken, OPTIONS);
    return true;
  } catch (e) {
    warn('save', e);
    return false;
  }
}

/** Remove tokens from memory and SecureStore. Never throws. */
export async function clearTokens(): Promise<void> {
  memory = null;
  const results = await Promise.allSettled([
    SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY, OPTIONS),
    SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY, OPTIONS),
  ]);
  for (const r of results) {
    if (r.status === 'rejected') warn('clear', r.reason);
  }
}

export interface TokenStore {
  getTokens: typeof getTokens;
  loadTokens: typeof loadTokens;
  saveTokens: typeof saveTokens;
  clearTokens: typeof clearTokens;
}

export const tokenStore: TokenStore = { getTokens, loadTokens, saveTokens, clearTokens };
