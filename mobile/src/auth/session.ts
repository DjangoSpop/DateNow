import type { Token } from '../api/types';
import { tokenStorage as defaultStorage, type StoredTokens, type TokenStorage } from './tokenStorage';

/**
 * In-memory cache of the current tokens, backed by TokenStorage (SecureStore on native).
 * The API client reads tokens from here so it does not hit the keychain on every request.
 */
export interface Session {
  load(): Promise<StoredTokens | null>;
  getAccessToken(): string | null;
  getRefreshToken(): string | null;
  hasTokens(): boolean;
  setTokens(token: Token): Promise<void>;
  clear(): Promise<void>;
}

export function createSession(storage: TokenStorage): Session {
  let current: StoredTokens | null = null;

  return {
    async load() {
      current = await storage.load();
      return current;
    },
    getAccessToken: () => current?.accessToken ?? null,
    getRefreshToken: () => current?.refreshToken ?? null,
    hasTokens: () => current !== null,
    async setTokens(token) {
      current = { accessToken: token.access_token, refreshToken: token.refresh_token };
      await storage.save(current);
    },
    async clear() {
      current = null;
      await storage.clear();
    },
  };
}

export const session = createSession(defaultStorage);
