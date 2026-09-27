/**
 * Live vertical-slice test against a running backend (skipped unless E2E_API_URL is set):
 *
 *   E2E_API_URL=http://127.0.0.1:8000 npx jest __tests__/e2e.live.test.ts
 *
 * Uses the app's real API client, session, auth store and boot routing. SecureStore is
 * replaced by an in-memory map that survives `jest.resetModules()`, which simulates an
 * app restart (all JS state is discarded; only the secure store persists).
 */
const API_URL = process.env.E2E_API_URL;
const describeLive = API_URL ? describe : describe.skip;

type SecureMap = Map<string, string>;
const g = globalThis as unknown as { __secureStore?: SecureMap; __asyncStore?: SecureMap };
g.__secureStore = new Map();

jest.mock('expo-secure-store', () => {
  const store = () => (globalThis as unknown as { __secureStore: Map<string, string> }).__secureStore;
  return {
    AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY: 'x',
    getItemAsync: async (k: string) => store().get(k) ?? null,
    setItemAsync: async (k: string, v: string) => {
      store().set(k, v);
    },
    deleteItemAsync: async (k: string) => {
      store().delete(k);
    },
  };
});

jest.mock('../src/config/env', () => {
  const actual = jest.requireActual('../src/config/env');
  return {
    ...actual,
    getApiBaseUrl: () =>
      actual.resolveApiBaseUrl({ configured: process.env.E2E_API_URL, appEnv: 'development', platform: 'ios' }),
  };
});

// jest-expo replaces fetch with a stub; this minimal fetch over node:http goes to the real server.
function nodeFetch(url: string, init: { method?: string; headers?: Record<string, string>; body?: string } = {}) {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const http = require('node:http');
  return new Promise((resolve, reject) => {
    const req = http.request(url, { method: init.method ?? 'GET', headers: init.headers }, (res: {
      statusCode: number; setEncoding: (e: string) => void; on: (e: string, cb: (c?: string) => void) => void;
    }) => {
      let text = '';
      res.setEncoding('utf8');
      res.on('data', (c) => {
        text += c;
      });
      res.on('end', () => {
        resolve({ status: res.statusCode, ok: res.statusCode >= 200 && res.statusCode < 300, text: async () => text });
      });
    });
    req.on('error', reject);
    if (init.body) req.write(init.body);
    req.end();
  });
}

// Fresh copies of every app module, as after a cold start.
function launchApp() {
  jest.resetModules();
  /* eslint-disable @typescript-eslint/no-require-imports */
  const { useAuthStore, selectBootRoute } = require('../src/state/authStore');
  const { profile } = require('../src/api/profile');
  const { questionnaire } = require('../src/api/questionnaire');
  const { onboarding } = require('../src/api/onboarding');
  /* eslint-enable @typescript-eslint/no-require-imports */
  return { useAuthStore, selectBootRoute, profile, questionnaire, onboarding };
}

function answerFor(q: { type: string; options: string[] | null; scale: { min: number; max: number } | null }, i: number) {
  if (q.type === 'scale') return ((i % 5) + 1);
  if (q.type === 'text') return 'I enjoy long walks and honest conversations.';
  if (q.type === 'multiple_choice') return [q.options![0]];
  return q.options![0];
}

describeLive('live vertical slice: register → profile → onboarding → restart → restore', () => {
  jest.setTimeout(60_000);
  const email = `e2e+${Date.now()}@example.com`;
  const password = 'correct-horse-battery';

  beforeAll(() => {
    (globalThis as unknown as { fetch: unknown }).fetch = nodeFetch;
  });

  it('completes the Sprint 1 flow and restores state after restarts', async () => {
    // --- first launch: no session ---
    let app = launchApp();
    await app.useAuthStore.getState().boot();
    expect(app.selectBootRoute(app.useAuthStore.getState())).toBe('auth');

    // --- register ---
    await app.useAuthStore.getState().register({ email, password, first_name: 'Ada', last_name: 'Lovelace' });
    let state = app.useAuthStore.getState();
    expect(state.me.email).toBe(email);
    expect(app.selectBootRoute(state)).toBe('profile-setup');
    // Tokens persisted only in the secure store.
    expect([...g.__secureStore!.keys()].sort()).toEqual(['datenow.accessToken', 'datenow.refreshToken']);

    // --- restart before profile: session restored, still needs profile ---
    app = launchApp();
    await app.useAuthStore.getState().boot();
    expect(app.selectBootRoute(app.useAuthStore.getState())).toBe('profile-setup');

    // --- logout + login ---
    await app.useAuthStore.getState().logout();
    expect(g.__secureStore!.size).toBe(0);
    expect(app.selectBootRoute(app.useAuthStore.getState())).toBe('auth');
    await app.useAuthStore.getState().login(email, password);

    // --- profile ---
    const created = await app.profile.create({
      first_name: 'Ada', last_name: 'Lovelace', date_of_birth: '1995-04-12', gender: 'female',
      looking_for_gender: ['male'], age_preference_min: 25, age_preference_max: 38,
      distance_preference_km: 40, relationship_goal: 'serious', city: 'London', country: 'UK',
    });
    expect(created.first_name).toBe('Ada');
    await app.useAuthStore.getState().refreshMe();
    expect(app.selectBootRoute(app.useAuthStore.getState())).toBe('onboarding');

    // --- onboarding: answer half, save draft ---
    const def = await app.questionnaire.get();
    const questions = def.sections.flatMap((s: { questions: unknown[] }) => s.questions);
    const all: Record<string, unknown> = {};
    questions.forEach((q: never, i: number) => {
      all[(q as { id: string }).id] = answerFor(q, i);
    });
    const firstHalf = Object.fromEntries(Object.entries(all).slice(0, 40));
    await app.onboarding.saveDraft({ current_section: def.sections[1].id, answers: firstHalf });

    // --- restart mid-onboarding: draft and position restored from server ---
    app = launchApp();
    await app.useAuthStore.getState().boot();
    expect(app.selectBootRoute(app.useAuthStore.getState())).toBe('onboarding');
    const resumed = await app.onboarding.get();
    expect(resumed.status).toBe('in_progress');
    expect(resumed.current_section).toBe(def.sections[1].id);
    expect(resumed.answers).toEqual(firstHalf);

    // --- submit remaining raw answers; server scores ---
    const rest = Object.fromEntries(Object.entries(all).slice(40));
    const psych = await app.questionnaire.submit(rest);
    for (const k of ['openness', 'conscientiousness', 'extraversion', 'agreeableness', 'neuroticism']) {
      expect(psych[k]).toBeGreaterThanOrEqual(0);
      expect(psych[k]).toBeLessThanOrEqual(100);
    }
    await app.useAuthStore.getState().refreshMe();
    expect(app.selectBootRoute(app.useAuthStore.getState())).toBe('home');

    // --- final restart: lands on home with profile + psych profile restored ---
    app = launchApp();
    await app.useAuthStore.getState().boot();
    state = app.useAuthStore.getState();
    expect(app.selectBootRoute(state)).toBe('home');
    expect(state.me.onboarding_status).toBe('completed');
    expect((await app.profile.get()).city).toBe('London');
    expect(await app.profile.getPsychological()).toEqual(psych);

    // --- an invalidated access token is refreshed transparently ---
    g.__secureStore!.set('datenow.accessToken', 'garbage');
    app = launchApp();
    await app.useAuthStore.getState().boot();
    expect(app.selectBootRoute(app.useAuthStore.getState())).toBe('home');
    expect(g.__secureStore!.get('datenow.accessToken')).not.toBe('garbage');
  });
});
