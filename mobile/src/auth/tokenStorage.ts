import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

/**
 * Persistent storage for the access + refresh tokens.
 *
 * SECURITY RULES
 * - Native (iOS/Android): tokens live ONLY in expo-secure-store (iOS Keychain / values encrypted with an Android Keystore key).
 *   Never AsyncStorage, never logged.
 * - Web: expo-secure-store is not available. We deliberately DO NOT fall back to localStorage;
 *   tokens are kept in memory only, so a web session ends on reload. Web is a dev convenience,
 *   not a supported production target for auth.
 */

export interface StoredTokens {
  accessToken: string;
  refreshToken: string;
}

export interface TokenStorage {
  load(): Promise<StoredTokens | null>;
  save(tokens: StoredTokens): Promise<void>;
  clear(): Promise<void>;
}

export const ACCESS_TOKEN_KEY = 'datenow.accessToken';
export const REFRESH_TOKEN_KEY = 'datenow.refreshToken';

const SECURE_OPTIONS: SecureStore.SecureStoreOptions = {
  // Readable after first unlock (so background refresh works), never migrated to another device.
  keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
};

export function createSecureTokenStorage(store: typeof SecureStore = SecureStore): TokenStorage {
  return {
    async load() {
      const [accessToken, refreshToken] = await Promise.all([
        store.getItemAsync(ACCESS_TOKEN_KEY, SECURE_OPTIONS),
        store.getItemAsync(REFRESH_TOKEN_KEY, SECURE_OPTIONS),
      ]);
      if (!accessToken || !refreshToken) return null;
      return { accessToken, refreshToken };
    },
    async save(tokens) {
      await store.setItemAsync(ACCESS_TOKEN_KEY, tokens.accessToken, SECURE_OPTIONS);
      await store.setItemAsync(REFRESH_TOKEN_KEY, tokens.refreshToken, SECURE_OPTIONS);
    },
    async clear() {
      await Promise.all([
        store.deleteItemAsync(ACCESS_TOKEN_KEY, SECURE_OPTIONS),
        store.deleteItemAsync(REFRESH_TOKEN_KEY, SECURE_OPTIONS),
      ]);
    },
  };
}

/** In-memory storage: used on web (documented degradation) and in tests. */
export function createMemoryTokenStorage(): TokenStorage {
  let tokens: StoredTokens | null = null;
  return {
    async load() {
      return tokens ? { ...tokens } : null;
    },
    async save(next) {
      tokens = { ...next };
    },
    async clear() {
      tokens = null;
    },
  };
}

export const isSecureTokenStorageSupported = Platform.OS === 'ios' || Platform.OS === 'android';

export const tokenStorage: TokenStorage = isSecureTokenStorageSupported
  ? createSecureTokenStorage()
  : createMemoryTokenStorage();
