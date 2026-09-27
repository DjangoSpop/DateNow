import AsyncStorage from '@react-native-async-storage/async-storage';

import { auth } from '../src/api/auth';
import { ApiError } from '../src/api/errors';
import type { Me } from '../src/api/types';
import { session } from '../src/auth/session';
import { draftKey } from '../src/onboarding/draftStorage';
import { selectBootRoute, useAuthStore } from '../src/state/authStore';

jest.mock('expo-secure-store', () => {
  const store = new Map<string, string>();
  return {
    AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY: 'x',
    getItemAsync: jest.fn(async (k: string) => store.get(k) ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => {
      store.set(k, v);
    }),
    deleteItemAsync: jest.fn(async (k: string) => {
      store.delete(k);
    }),
  };
});

jest.mock('../src/api/auth', () => ({
  auth: { me: jest.fn(), login: jest.fn(), register: jest.fn(), refresh: jest.fn() },
}));

const mockedAuth = auth as jest.Mocked<typeof auth>;

const me: Me = {
  id: 7,
  email: 'a@b.com',
  first_name: 'Ada',
  last_name: null,
  is_active: true,
  is_verified: false,
  created_at: '2026-01-01T00:00:00Z',
  has_profile: true,
  onboarding_status: 'in_progress',
};

const tokens = { access_token: 'a', refresh_token: 'r', token_type: 'bearer' as const };

beforeEach(async () => {
  await session.clear();
  useAuthStore.setState({ status: 'booting', hasSession: false, me: null, bootError: null });
});

describe('auth store boot', () => {
  it('no stored tokens → ready, auth route, /auth/me not called', async () => {
    await useAuthStore.getState().boot();
    expect(useAuthStore.getState().status).toBe('ready');
    expect(selectBootRoute(useAuthStore.getState())).toBe('auth');
    expect(mockedAuth.me).not.toHaveBeenCalled();
  });

  it('stored tokens + /auth/me → routes by Me', async () => {
    await session.setTokens(tokens);
    mockedAuth.me.mockResolvedValueOnce(me);
    await useAuthStore.getState().boot();
    expect(selectBootRoute(useAuthStore.getState())).toBe('onboarding');
  });

  it('network failure keeps tokens and shows boot_error (no logout)', async () => {
    await session.setTokens(tokens);
    mockedAuth.me.mockRejectedValueOnce(new ApiError({ status: 0, code: 'network', message: 'offline' }));
    await useAuthStore.getState().boot();
    expect(useAuthStore.getState().status).toBe('boot_error');
    expect(session.getRefreshToken()).toBe('r');
  });

  it('unauthorized after refresh → cleared session, auth route', async () => {
    await session.setTokens(tokens);
    mockedAuth.me.mockRejectedValueOnce(new ApiError({ status: 401, code: 'unauthorized', message: 'x' }));
    await useAuthStore.getState().boot();
    expect(useAuthStore.getState().status).toBe('ready');
    expect(selectBootRoute(useAuthStore.getState())).toBe('auth');
    expect(session.hasTokens()).toBe(false);
  });

  it('logout clears tokens, in-memory user and cached drafts', async () => {
    await session.setTokens(tokens);
    useAuthStore.setState({ status: 'ready', hasSession: true, me });
    await AsyncStorage.setItem(draftKey(7), JSON.stringify({ answers: {} }));
    await AsyncStorage.setItem('unrelated', '1');

    await useAuthStore.getState().logout();

    expect(session.hasTokens()).toBe(false);
    expect(await session.load()).toBeNull();
    expect(useAuthStore.getState().me).toBeNull();
    expect(await AsyncStorage.getItem(draftKey(7))).toBeNull();
    expect(await AsyncStorage.getItem('unrelated')).toBe('1');
  });

  it('login stores tokens then loads Me', async () => {
    mockedAuth.login.mockResolvedValueOnce(tokens);
    mockedAuth.me.mockResolvedValueOnce({ ...me, has_profile: false });
    await useAuthStore.getState().login(' a@b.com ', 'password1');
    expect(mockedAuth.login).toHaveBeenCalledWith({ email: 'a@b.com', password: 'password1' });
    expect(session.getAccessToken()).toBe('a');
    expect(selectBootRoute(useAuthStore.getState())).toBe('profile-setup');
  });
});
