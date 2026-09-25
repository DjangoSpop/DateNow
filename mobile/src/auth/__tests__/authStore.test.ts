/**
 * Auth store bootstrap + a simulated app restart. The SecureStore mock is backed by a Map that
 * lives outside the module registry, so a freshly required store (jest.isolateModules) sees the
 * same "device keychain" — exactly like a cold start.
 */
import { createFakeBackend, makeFetch } from '@/testing/fakeFetch';
import type { AuthState } from '../authStore';
import type { StoreApi, UseBoundStore } from 'zustand';

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

type AuthStore = UseBoundStore<StoreApi<AuthState>>;

/** Require a brand-new copy of the app modules (new token memory, new client, new store). */
function launchApp(): AuthStore {
  let store: AuthStore | undefined;
  jest.isolateModules(() => {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    store = require('../authStore').useAuthStore as AuthStore;
  });
  return store!;
}

let backend: ReturnType<typeof createFakeBackend>;

beforeEach(() => {
  mockSecure.clear();
  backend = createFakeBackend();
  globalThis.fetch = makeFetch(backend.handler) as unknown as typeof fetch;
});

describe('auth store bootstrap', () => {
  it('no stored tokens → signedOut without calling the API', async () => {
    const store = launchApp();
    expect(store.getState().status).toBe('booting');
    await store.getState().bootstrap();
    expect(store.getState().status).toBe('signedOut');
    expect(store.getState().me).toBeNull();
    expect(backend.calls).toEqual([]);
  });

  it('valid stored tokens → signedIn with /users/me', async () => {
    backend.addUser('sam@example.com', 'password123');
    const first = launchApp();
    await first.getState().login('sam@example.com', 'password123');

    const store = launchApp();
    await store.getState().bootstrap();
    expect(store.getState().status).toBe('signedIn');
    expect(store.getState().me?.email).toBe('sam@example.com');
  });

  it('expired access + valid refresh → refreshes, persists new pair, then signedIn', async () => {
    backend.addUser('sam@example.com', 'password123');
    await launchApp().getState().login('sam@example.com', 'password123');
    const before = new Map(mockSecure);
    backend.expireAccessTokens();
    backend.calls.length = 0;

    const store = launchApp();
    await store.getState().bootstrap();

    expect(store.getState().status).toBe('signedIn');
    expect(backend.calls).toEqual(['GET /users/me', 'POST /auth/refresh', 'GET /users/me']);
    // Rotated tokens were written back to SecureStore.
    expect(mockSecure.get('datenow.access_token')).not.toBe(before.get('datenow.access_token'));
    expect(mockSecure.get('datenow.refresh_token')).not.toBe(before.get('datenow.refresh_token'));
  });

  it('expired access + rejected refresh → tokens cleared, signedOut', async () => {
    backend.addUser('sam@example.com', 'password123');
    await launchApp().getState().login('sam@example.com', 'password123');
    backend.expireAccessTokens();
    backend.revokeRefreshTokens();

    const store = launchApp();
    await store.getState().bootstrap();
    expect(store.getState().status).toBe('signedOut');
    expect(mockSecure.size).toBe(0);
  });

  it('offline at launch → keeps tokens and exposes a retryable boot error', async () => {
    mockSecure.set('datenow.access_token', 'a');
    mockSecure.set('datenow.refresh_token', 'r');
    globalThis.fetch = jest.fn(async () => {
      throw new TypeError('Network request failed');
    }) as unknown as typeof fetch;
    const store = launchApp();
    await store.getState().bootstrap();
    expect(store.getState().status).toBe('booting');
    expect(store.getState().bootError?.code).toBe('NETWORK_ERROR');
    expect(mockSecure.size).toBe(2);
  });

  it('SIMULATED RESTART: login, kill the app, relaunch → session and onboarding restored', async () => {
    backend.addUser('sam@example.com', 'password123');
    backend.onboarding.profile_complete = true;
    backend.onboarding.questionnaire_complete = false;
    backend.onboarding.questionnaire_answered = 17;

    // First launch: user signs in.
    const firstRun = launchApp();
    await firstRun.getState().bootstrap();
    expect(firstRun.getState().status).toBe('signedOut');
    await firstRun.getState().login('  Sam@Example.com ', 'password123');
    expect(firstRun.getState().status).toBe('signedIn');
    expect(mockSecure.has('datenow.access_token')).toBe(true);
    expect(mockSecure.has('datenow.refresh_token')).toBe(true);

    // "Restart": a completely fresh module graph; only the SecureStore contents survive.
    const secondRun = launchApp();
    expect(secondRun).not.toBe(firstRun);
    expect(secondRun.getState().status).toBe('booting');
    expect(secondRun.getState().me).toBeNull();
    await secondRun.getState().bootstrap();

    const { status, me } = secondRun.getState();
    expect(status).toBe('signedIn');
    expect(me?.email).toBe('sam@example.com');
    expect(me?.onboarding).toEqual({
      profile_complete: true,
      questionnaire_complete: false,
      questionnaire_answered: 17,
      questionnaire_total: 71,
      questionnaire_version: 'ipip-v1',
      complete: false,
    });
  });

  it('logout clears SecureStore so the next launch is signed out', async () => {
    backend.addUser('sam@example.com', 'password123');
    const run = launchApp();
    await run.getState().login('sam@example.com', 'password123');
    await run.getState().logout();
    expect(run.getState().status).toBe('signedOut');
    expect(mockSecure.size).toBe(0);

    const next = launchApp();
    await next.getState().bootstrap();
    expect(next.getState().status).toBe('signedOut');
  });

  it('register surfaces EMAIL_TAKEN as an ApiError and stays signed out', async () => {
    backend.addUser('sam@example.com', 'password123');
    const run = launchApp();
    await run.getState().bootstrap();
    await expect(run.getState().register('sam@example.com', 'password123')).rejects.toMatchObject({
      code: 'EMAIL_TAKEN',
      status: 409,
    });
    expect(run.getState().status).toBe('signedOut');
    expect(mockSecure.size).toBe(0);
  });
});
