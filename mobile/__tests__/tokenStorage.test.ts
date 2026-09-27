import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';

import {
  ACCESS_TOKEN_KEY,
  REFRESH_TOKEN_KEY,
  createSecureTokenStorage,
  isSecureTokenStorageSupported,
  tokenStorage,
} from '../src/auth/tokenStorage';

jest.mock('expo-secure-store', () => {
  const store = new Map<string, string>();
  return {
    AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY: 'AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY',
    getItemAsync: jest.fn(async (k: string) => store.get(k) ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => {
      store.set(k, v);
    }),
    deleteItemAsync: jest.fn(async (k: string) => {
      store.delete(k);
    }),
  };
});

const mocked = SecureStore as jest.Mocked<typeof SecureStore>;

describe('tokenStorage', () => {
  it('uses SecureStore on native platforms (jest-expo runs as ios)', () => {
    expect(isSecureTokenStorageSupported).toBe(true);
  });

  it('persists tokens only through expo-secure-store', async () => {
    const setItemSpy = jest.spyOn(AsyncStorage, 'setItem');
    await tokenStorage.save({ accessToken: 'acc', refreshToken: 'ref' });

    expect(mocked.setItemAsync).toHaveBeenCalledWith(
      ACCESS_TOKEN_KEY,
      'acc',
      expect.objectContaining({ keychainAccessible: 'AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY' }),
    );
    expect(mocked.setItemAsync).toHaveBeenCalledWith(REFRESH_TOKEN_KEY, 'ref', expect.any(Object));
    expect(setItemSpy).not.toHaveBeenCalled();

    await expect(tokenStorage.load()).resolves.toEqual({ accessToken: 'acc', refreshToken: 'ref' });
    expect(mocked.getItemAsync).toHaveBeenCalledWith(ACCESS_TOKEN_KEY, expect.any(Object));
  });

  it('clear() deletes both keys and load() then returns null', async () => {
    const storage = createSecureTokenStorage(mocked);
    await storage.save({ accessToken: 'a', refreshToken: 'r' });
    await storage.clear();
    expect(mocked.deleteItemAsync).toHaveBeenCalledWith(ACCESS_TOKEN_KEY, expect.any(Object));
    expect(mocked.deleteItemAsync).toHaveBeenCalledWith(REFRESH_TOKEN_KEY, expect.any(Object));
    await expect(storage.load()).resolves.toBeNull();
  });

  it('treats a half-written pair as no session', async () => {
    const storage = createSecureTokenStorage(mocked);
    await storage.clear();
    await mocked.setItemAsync(ACCESS_TOKEN_KEY, 'only-access');
    await expect(storage.load()).resolves.toBeNull();
  });
});
