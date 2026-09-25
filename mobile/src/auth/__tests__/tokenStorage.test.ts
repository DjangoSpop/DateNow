import * as SecureStore from 'expo-secure-store';

import {
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  clearTokens,
  getTokens,
  loadTokens,
  saveTokens,
} from '../tokenStorage';

const mockSecure = new Map<string, string>();

jest.mock('expo-secure-store', () => ({
  AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY: 1,
  getItemAsync: jest.fn(async (k: string) => mockSecure.get(k) ?? null),
  setItemAsync: jest.fn(async (k: string, v: string) => {
    mockSecure.set(k, v);
  }),
  deleteItemAsync: jest.fn(async (k: string) => {
    mockSecure.delete(k);
  }),
}));

const mocked = SecureStore as jest.Mocked<typeof SecureStore>;

beforeEach(async () => {
  mockSecure.clear();
  await clearTokens();
  jest.spyOn(console, 'warn').mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe('tokenStorage (expo-secure-store only)', () => {
  it('saves both tokens to SecureStore and keeps an in-memory copy', async () => {
    await expect(saveTokens({ accessToken: 'a', refreshToken: 'r' })).resolves.toBe(true);
    expect(mockSecure.get(ACCESS_TOKEN_KEY)).toBe('a');
    expect(mockSecure.get(REFRESH_TOKEN_KEY)).toBe('r');
    expect(getTokens()).toEqual({ accessToken: 'a', refreshToken: 'r' });
    // Stored with a device-only keychain accessibility option.
    expect(mocked.setItemAsync).toHaveBeenCalledWith(ACCESS_TOKEN_KEY, 'a', {
      keychainAccessible: SecureStore.AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY,
    });
  });

  it('loads tokens from SecureStore on a cold start', async () => {
    mockSecure.set(ACCESS_TOKEN_KEY, 'a');
    mockSecure.set(REFRESH_TOKEN_KEY, 'r');
    expect(getTokens()).toBeNull();
    await expect(loadTokens()).resolves.toEqual({ accessToken: 'a', refreshToken: 'r' });
    expect(getTokens()).toEqual({ accessToken: 'a', refreshToken: 'r' });
  });

  it('returns null when nothing is stored', async () => {
    await expect(loadTokens()).resolves.toBeNull();
  });

  it('discards a half-written pair', async () => {
    mockSecure.set(ACCESS_TOKEN_KEY, 'a');
    await expect(loadTokens()).resolves.toBeNull();
    expect(mockSecure.size).toBe(0);
  });

  it('treats a SecureStore read failure as "no session" without throwing', async () => {
    mocked.getItemAsync.mockRejectedValueOnce(new Error('keychain locked'));
    await expect(loadTokens()).resolves.toBeNull();
    expect(console.warn).toHaveBeenCalled();
  });

  it('keeps the in-memory session if a SecureStore write fails', async () => {
    mocked.setItemAsync.mockRejectedValueOnce(new Error('disk full'));
    await expect(saveTokens({ accessToken: 'a', refreshToken: 'r' })).resolves.toBe(false);
    expect(getTokens()).toEqual({ accessToken: 'a', refreshToken: 'r' });
  });

  it('clears memory and SecureStore, even if a delete fails', async () => {
    await saveTokens({ accessToken: 'a', refreshToken: 'r' });
    mocked.deleteItemAsync.mockRejectedValueOnce(new Error('boom'));
    await expect(clearTokens()).resolves.toBeUndefined();
    expect(getTokens()).toBeNull();
    expect(mockSecure.has(REFRESH_TOKEN_KEY)).toBe(false);
  });

  it('never logs token values', async () => {
    mocked.setItemAsync.mockRejectedValueOnce(new Error('disk full'));
    await saveTokens({ accessToken: 'secret-access', refreshToken: 'secret-refresh' });
    const logged = JSON.stringify((console.warn as jest.Mock).mock.calls);
    expect(logged).not.toContain('secret-access');
    expect(logged).not.toContain('secret-refresh');
  });
});
