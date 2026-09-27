import { createApiClient } from '../src/api/client';
import { ApiError } from '../src/api/errors';
import { createSession, type Session } from '../src/auth/session';
import { createMemoryTokenStorage, type TokenStorage } from '../src/auth/tokenStorage';

const BASE = 'http://api.test/api/v1';

type Handler = (url: string, init: RequestInit) => Promise<FakeResponse> | FakeResponse;

interface FakeResponse {
  status: number;
  ok: boolean;
  text: () => Promise<string>;
}

function json(status: number, body: unknown): FakeResponse {
  return { status, ok: status >= 200 && status < 300, text: async () => JSON.stringify(body) };
}

function authHeader(init: RequestInit): string | undefined {
  return (init.headers as Record<string, string>)?.Authorization;
}

async function setup(handler: Handler, opts: { timeoutMs?: number } = {}) {
  const storage: TokenStorage = createMemoryTokenStorage();
  const session: Session = createSession(storage);
  await session.setTokens({ access_token: 'a1', refresh_token: 'r1', token_type: 'bearer' });
  const fetchMock = jest.fn((url: string, init: RequestInit) => Promise.resolve(handler(url, init)));
  const onSessionExpired = jest.fn();
  const client = createApiClient({
    getBaseUrl: () => BASE,
    session,
    fetchImpl: fetchMock as unknown as typeof fetch,
    timeoutMs: opts.timeoutMs,
    onSessionExpired,
  });
  return { client, session, storage, fetchMock, onSessionExpired };
}

const refreshCalls = (fetchMock: jest.Mock) =>
  fetchMock.mock.calls.filter(([url]) => String(url).endsWith('/auth/refresh'));

describe('api client', () => {
  it('injects the bearer token and JSON headers on authenticated requests', async () => {
    const { client, fetchMock } = await setup(() => json(200, { ok: true }));
    await client.request('/auth/me');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`${BASE}/auth/me`);
    expect(authHeader(init)).toBe('Bearer a1');
    expect((init.headers as Record<string, string>).Accept).toBe('application/json');
  });

  it('does not send Authorization on unauthenticated requests and serialises the JSON body', async () => {
    const { client, fetchMock } = await setup(() =>
      json(200, { access_token: 'x', refresh_token: 'y', token_type: 'bearer' }),
    );
    await client.request('/auth/login', { method: 'POST', body: { email: 'a@b.com', password: 'p' }, auth: false });
    const init = fetchMock.mock.calls[0][1] as RequestInit;
    expect(authHeader(init)).toBeUndefined();
    expect(init.method).toBe('POST');
    expect((init.headers as Record<string, string>)['Content-Type']).toBe('application/json');
    expect(JSON.parse(init.body as string)).toEqual({ email: 'a@b.com', password: 'p' });
  });

  it('turns a timeout into ApiError{code:"timeout"} via AbortController', async () => {
    jest.useFakeTimers();
    try {
      const { client } = await setup(
        (_url, init) =>
          new Promise<FakeResponse>((_resolve, reject) => {
            init.signal?.addEventListener('abort', () => {
              const err = new Error('Aborted');
              err.name = 'AbortError';
              reject(err);
            });
          }),
        { timeoutMs: 5000 },
      );
      const p = client.request('/auth/me');
      const assertion = expect(p).rejects.toMatchObject({ code: 'timeout', status: 0 });
      jest.advanceTimersByTime(5000);
      await assertion;
    } finally {
      jest.useRealTimers();
    }
  });

  it('turns a fetch failure into ApiError{code:"network"}', async () => {
    const { client } = await setup(() => {
      throw new TypeError('Network request failed');
    });
    await expect(client.request('/auth/me')).rejects.toMatchObject({ code: 'network', status: 0 });
  });

  it('parses FastAPI 422 validation errors into fieldErrors', async () => {
    const { client } = await setup(() =>
      json(422, {
        detail: [
          { loc: ['body', 'date_of_birth'], msg: 'Value error, You must be at least 18', type: 'value_error' },
          { loc: ['body', 'age_preference_min'], msg: 'Input should be >= 18', type: 'greater_than_equal' },
        ],
      }),
    );
    const err = (await client.request('/users/me/profile', { method: 'POST', body: {} }).catch((e) => e)) as ApiError;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(422);
    expect(err.code).toBe('validation');
    expect(err.fieldErrors).toEqual({
      date_of_birth: 'You must be at least 18',
      age_preference_min: 'Input should be >= 18',
    });
    expect(err.issues).toHaveLength(2);
  });

  it('parses the questionnaire 422 shape [{question_id, message}] including "__all__"', async () => {
    const { client } = await setup(() =>
      json(422, {
        detail: [
          { question_id: 'bf_3', message: 'Required' },
          { question_id: '__all__', message: 'Computed fields are not allowed' },
        ],
      }),
    );
    const err = (await client.request('/questionnaire/submit', { method: 'POST', body: {} }).catch((e) => e)) as ApiError;
    expect(err.code).toBe('validation');
    expect(err.fieldErrors).toEqual({ bf_3: 'Required' });
    expect(err.issues?.map((i) => i.loc)).toEqual([['body', 'answers', 'bf_3'], ['body']]);
  });

  it('maps string details and statuses to codes', async () => {
    const statuses: [number, string][] = [
      [409, 'conflict'],
      [404, 'not_found'],
      [400, 'validation'],
      [500, 'server'],
      [418, 'unknown'],
    ];
    for (const [status, code] of statuses) {
      const { client } = await setup(() => json(status, { detail: 'Email already registered' }));
      await expect(client.request('/x', { auth: false })).rejects.toMatchObject({
        status,
        code,
        message: 'Email already registered',
      });
    }
  });

  it('on 401 refreshes once via POST /auth/refresh and retries with the new token', async () => {
    const { client, fetchMock, session, storage } = await setup((url, init) => {
      if (url.endsWith('/auth/refresh')) {
        expect(JSON.parse(init.body as string)).toEqual({ refresh_token: 'r1' });
        return json(200, { access_token: 'a2', refresh_token: 'r2', token_type: 'bearer' });
      }
      return authHeader(init) === 'Bearer a2' ? json(200, { id: 1 }) : json(401, { detail: 'expired' });
    });
    await expect(client.request('/auth/me')).resolves.toEqual({ id: 1 });
    expect(refreshCalls(fetchMock)).toHaveLength(1);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(session.getAccessToken()).toBe('a2');
    expect(await storage.load()).toEqual({ accessToken: 'a2', refreshToken: 'r2' });
  });

  it('clears the session and notifies when refresh is rejected', async () => {
    const { client, session, storage, onSessionExpired } = await setup((url) =>
      url.endsWith('/auth/refresh') ? json(401, { detail: 'invalid refresh' }) : json(401, { detail: 'expired' }),
    );
    await expect(client.request('/auth/me')).rejects.toMatchObject({ code: 'unauthorized', status: 401 });
    expect(session.getAccessToken()).toBeNull();
    expect(session.getRefreshToken()).toBeNull();
    expect(await storage.load()).toBeNull();
    expect(onSessionExpired).toHaveBeenCalledTimes(1);
  });

  it('clears the session if the retried request is still 401', async () => {
    const { client, storage, onSessionExpired, fetchMock } = await setup((url) =>
      url.endsWith('/auth/refresh')
        ? json(200, { access_token: 'a2', refresh_token: 'r2', token_type: 'bearer' })
        : json(401, { detail: 'nope' }),
    );
    await expect(client.request('/auth/me')).rejects.toMatchObject({ code: 'unauthorized' });
    expect(refreshCalls(fetchMock)).toHaveLength(1); // no refresh loop
    expect(await storage.load()).toBeNull();
    expect(onSessionExpired).toHaveBeenCalledTimes(1);
  });

  it('keeps the session when refresh fails because the network is down', async () => {
    const { client, session, onSessionExpired } = await setup((url) => {
      if (url.endsWith('/auth/refresh')) throw new TypeError('Network request failed');
      return json(401, { detail: 'expired' });
    });
    await expect(client.request('/auth/me')).rejects.toMatchObject({ code: 'network' });
    expect(session.getRefreshToken()).toBe('r1');
    expect(onSessionExpired).not.toHaveBeenCalled();
  });

  it('single-flights concurrent refreshes', async () => {
    let releaseRefresh: () => void = () => {};
    const refreshGate = new Promise<void>((r) => {
      releaseRefresh = r;
    });
    const { client, fetchMock } = await setup(async (url, init) => {
      if (url.endsWith('/auth/refresh')) {
        await refreshGate;
        return json(200, { access_token: 'a2', refresh_token: 'r2', token_type: 'bearer' });
      }
      return authHeader(init) === 'Bearer a2' ? json(200, { url }) : json(401, { detail: 'expired' });
    });

    const all = Promise.all([
      client.request('/auth/me'),
      client.request('/onboarding'),
      client.request('/questionnaire'),
    ]);
    // Let all three hit 401 and queue on the same refresh.
    await new Promise((r) => setTimeout(r, 10));
    releaseRefresh();
    const results = await all;

    expect(results).toHaveLength(3);
    expect(refreshCalls(fetchMock)).toHaveLength(1);
  });

  it('does not attempt a refresh for unauthenticated endpoints (e.g. bad login)', async () => {
    const { client, fetchMock } = await setup(() => json(401, { detail: 'Incorrect email or password' }));
    await expect(
      client.request('/auth/login', { method: 'POST', body: {}, auth: false }),
    ).rejects.toMatchObject({ code: 'unauthorized', message: 'Incorrect email or password' });
    expect(refreshCalls(fetchMock)).toHaveLength(0);
  });
});
