/**
 * Sprint 1 vertical slice against a REAL backend (no fake fetch):
 * register → profile → questionnaire autosave → submit → app restart → session + onboarding restored.
 *
 * Opt-in: runs only when E2E_API_URL is set, e.g.
 *   E2E_API_URL=http://localhost:8765 npx jest src/__e2e__
 * The device keychain (expo-secure-store) is an in-memory Map that outlives module reloads, so a
 * fresh `jest.isolateModules` load behaves like a cold app start on the same device.
 */
import type { AuthState } from '@/auth/authStore';
import type * as Endpoints from '@/api/endpoints';
import type { StoreApi, UseBoundStore } from 'zustand';

const E2E_API_URL = process.env.E2E_API_URL;
const describeE2E = E2E_API_URL ? describe : describe.skip;

const mockKeychain = new Map<string, string>();
jest.mock('expo-secure-store', () => ({
  AFTER_FIRST_UNLOCK_THIS_DEVICE_ONLY: 1,
  getItemAsync: jest.fn(async (k: string) => mockKeychain.get(k) ?? null),
  setItemAsync: jest.fn(async (k: string, v: string) => {
    mockKeychain.set(k, v);
  }),
  deleteItemAsync: jest.fn(async (k: string) => {
    mockKeychain.delete(k);
  }),
}));

/**
 * The react-native jest preset replaces global fetch with a mock, so give the app a real HTTP
 * transport (node:http). It implements the subset of Response the API client uses.
 */
function nodeFetch(input: string | URL | Request, init: RequestInit = {}): Promise<Response> {
  // Minimal local typing: the app tsconfig deliberately has no Node types.
  interface IncomingMessage {
    statusCode?: number;
    setEncoding(enc: string): void;
    on(event: 'data', cb: (chunk: string) => void): void;
    on(event: 'end', cb: () => void): void;
  }
  interface ClientRequest {
    on(event: 'error', cb: (err: Error) => void): void;
    write(body: string): void;
    end(): void;
    destroy(err: Error): void;
  }
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const http = require('node:http') as {
    request(url: URL, opts: object, cb: (res: IncomingMessage) => void): ClientRequest;
  };
  const url = new URL(String(input));
  return new Promise((resolve, reject) => {
    const req = http.request(
      url,
      { method: init.method ?? 'GET', headers: init.headers as Record<string, string> },
      (res) => {
        let body = '';
        res.setEncoding('utf8');
        res.on('data', (chunk: string) => (body += chunk));
        res.on('end', () => {
          const status = res.statusCode ?? 0;
          resolve({ status, ok: status >= 200 && status < 300, text: async () => body } as Response);
        });
      },
    );
    req.on('error', reject);
    init.signal?.addEventListener('abort', () => req.destroy(new Error('aborted')));
    if (init.body) req.write(init.body as string);
    req.end();
  });
}

type AuthStore = UseBoundStore<StoreApi<AuthState>>;
interface App {
  store: AuthStore;
  api: typeof Endpoints;
}

/** A brand-new copy of the app's modules: new in-memory tokens, API client and store. */
function launchApp(): App {
  let app: App | undefined;
  jest.isolateModules(() => {
    /* eslint-disable @typescript-eslint/no-require-imports */
    app = {
      store: require('@/auth/authStore').useAuthStore as AuthStore,
      api: require('@/api/endpoints') as typeof Endpoints,
    };
    /* eslint-enable @typescript-eslint/no-require-imports */
  });
  return app!;
}

describeE2E('vertical slice against a live backend', () => {
  jest.setTimeout(60_000);
  const email = `e2e-${Date.now()}@example.com`;
  const password = 'correct-horse-battery';

  beforeAll(() => {
    process.env.EXPO_PUBLIC_API_URL = E2E_API_URL;
    globalThis.fetch = nodeFetch as typeof fetch;
    mockKeychain.clear();
  });

  it('register → profile → onboarding → restart → restore', async () => {
    // 1. Launch, nothing stored → signed out.
    let app = launchApp();
    await app.store.getState().bootstrap();
    expect(app.store.getState().status).toBe('signedOut');

    // 2. Register; tokens land in the keychain, never elsewhere.
    await app.store.getState().register(email, password);
    expect(app.store.getState().status).toBe('signedIn');
    expect([...mockKeychain.keys()].length).toBeGreaterThanOrEqual(1);
    expect(app.store.getState().me?.onboarding.profile_complete).toBe(false);

    // 3. Server-side 18+ rule is enforced, then a valid profile is created.
    const thisYear = new Date().getUTCFullYear();
    const base = {
      first_name: 'Sam',
      gender: 'female' as const,
      looking_for_gender: ['male' as const],
      age_preference_min: 27,
      age_preference_max: 38,
      relationship_goal: 'serious' as const,
    };
    await expect(
      app.api.createProfile({ ...base, date_of_birth: `${thisYear - 17}-01-01` }),
    ).rejects.toMatchObject({ status: 422, code: 'VALIDATION_ERROR' });
    const profile = await app.api.createProfile({ ...base, date_of_birth: '1995-04-02' });
    expect(profile.first_name).toBe('Sam');

    // 4. Questionnaire: fetch the server bank, autosave half, "crash", resume, finish, submit.
    const definition = await app.api.getQuestionnaire();
    const questions = definition.sections.flatMap((s) => s.questions);
    const answerFor = (q: (typeof questions)[number]) =>
      q.type === 'scale' ? 4 : q.options[0]!.value;
    const half = Object.fromEntries(questions.slice(0, 30).map((q) => [q.id, answerFor(q)]));
    const partial = await app.api.saveAnswers(half);
    expect(partial.answered).toBe(30);

    app = launchApp(); // app killed mid-questionnaire
    await app.store.getState().bootstrap();
    expect(app.store.getState().status).toBe('signedIn');
    const resumed = await app.api.getQuestionnaireState();
    expect(resumed.answers).toEqual(half);
    expect(resumed.missing[0]).toBe(questions[30]!.id);

    const rest = Object.fromEntries(questions.slice(30).map((q) => [q.id, answerFor(q)]));
    await app.api.saveAnswers(rest);
    const scored = await app.api.submitQuestionnaire();
    expect(scored.questionnaire_version).toBe(definition.version);
    expect(scored.big_five.openness).toBeGreaterThanOrEqual(0);

    // 5. Cold restart: session and completed onboarding are restored from keychain + server.
    app = launchApp();
    await app.store.getState().bootstrap();
    const me = app.store.getState().me!;
    expect(app.store.getState().status).toBe('signedIn');
    expect(me.email).toBe(email);
    expect(me.onboarding).toMatchObject({
      profile_complete: true,
      questionnaire_complete: true,
      complete: true,
      questionnaire_answered: questions.length,
    });
    expect((await app.api.getProfile()).date_of_birth).toBe('1995-04-02');
    expect(await app.api.getPsychologicalProfile()).toEqual(scored);

    // 6. Corrupted/expired access token on restart → client refreshes against the real server.
    const accessKey = [...mockKeychain.keys()].find((k) => /access/i.test(k));
    expect(accessKey).toBeDefined();
    mockKeychain.set(accessKey!, 'not-a-valid-jwt');
    app = launchApp();
    await app.store.getState().bootstrap();
    expect(app.store.getState().status).toBe('signedIn');
    expect(mockKeychain.get(accessKey!)).not.toBe('not-a-valid-jwt');

    // 7. Logout clears the keychain; next launch is signed out.
    await app.store.getState().logout();
    expect(mockKeychain.size).toBe(0);
    app = launchApp();
    await app.store.getState().bootstrap();
    expect(app.store.getState().status).toBe('signedOut');

    // 8. Login again restores everything.
    await app.store.getState().login(email.toUpperCase(), password);
    expect(app.store.getState().me?.onboarding.complete).toBe(true);
  });
});
