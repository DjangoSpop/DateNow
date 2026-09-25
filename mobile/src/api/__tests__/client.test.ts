import { createApiClient } from '../client';
import { ApiError } from '../errors';
import type { StoredTokens, TokenStore } from '@/auth/tokenStorage';
import { envelope, makeFetch, type FakeHandler } from '@/testing/fakeFetch';

const ROOT = 'http://api.test/api/v1';

function memoryTokenStore(initial: StoredTokens | null): TokenStore & { current: () => StoredTokens | null } {
  let tokens = initial;
  return {
    getTokens: () => tokens,
    loadTokens: async () => tokens,
    saveTokens: async (t) => {
      tokens = t;
      return true;
    },
    clearTokens: async () => {
      tokens = null;
    },
    current: () => tokens,
  };
}

function setup(handler: FakeHandler, tokens: StoredTokens | null = { accessToken: 'A1', refreshToken: 'R1' }) {
  const fetchImpl = makeFetch(handler);
  const store = memoryTokenStore(tokens);
  const client = createApiClient({ apiRoot: ROOT, tokenStore: store, fetchImpl, timeoutMs: 1000 });
  const onAuthFailure = jest.fn();
  client.setAuthFailureHandler(onAuthFailure);
  return { client, store, fetchImpl, onAuthFailure };
}

async function catchError(p: Promise<unknown>): Promise<ApiError> {
  try {
    await p;
  } catch (e) {
    expect(e).toBeInstanceOf(ApiError);
    return e as ApiError;
  }
  throw new Error('expected rejection');
}

describe('api client: responses and errors', () => {
  it('parses JSON success bodies and injects the bearer token', async () => {
    const { client, fetchImpl } = setup(() => ({ status: 200, body: { id: 1 } }));
    await expect(client.request('/users/me')).resolves.toEqual({ id: 1 });
    const init = fetchImpl.mock.calls[0]![1]!;
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer A1');
    expect(fetchImpl.mock.calls[0]![0]).toBe(`${ROOT}/users/me`);
  });

  it('parses the contract error envelope into ApiError {status, code, message, fields}', async () => {
    const { client } = setup(() => ({
      status: 422,
      body: envelope('VALIDATION_ERROR', 'Invalid body', { date_of_birth: 'must be 18+' }),
    }));
    const err = await catchError(client.request('/users/me/profile', { method: 'POST', body: {} }));
    expect(err.status).toBe(422);
    expect(err.code).toBe('VALIDATION_ERROR');
    expect(err.message).toBe('Invalid body');
    expect(err.fields).toEqual({ date_of_birth: 'must be 18+' });
  });

  it('falls back on status when the body is not an envelope', async () => {
    const { client } = setup(() => ({ status: 500, body: '<html>oops</html>' }));
    const err = await catchError(client.request('/users/me'));
    expect(err.status).toBe(500);
    expect(err.code).toBe('INTERNAL_ERROR');
    expect(err.isTransient).toBe(true);
  });

  it('maps a network failure to NETWORK_ERROR', async () => {
    const fetchImpl = jest.fn(async () => {
      throw new TypeError('Network request failed');
    });
    const client = createApiClient({
      apiRoot: ROOT,
      tokenStore: memoryTokenStore(null),
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    const err = await catchError(client.request('/auth/login', { method: 'POST', auth: false, body: {} }));
    expect(err.code).toBe('NETWORK_ERROR');
    expect(err.status).toBe(0);
  });

  it('aborts after the timeout and maps it to TIMEOUT', async () => {
    const fetchImpl = jest.fn(
      (_url: RequestInfo | URL, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => reject(new Error('aborted')));
        }),
    );
    const client = createApiClient({
      apiRoot: ROOT,
      tokenStore: memoryTokenStore(null),
      fetchImpl: fetchImpl as unknown as typeof fetch,
    });
    const err = await catchError(
      client.request('/questionnaire', { auth: false, timeoutMs: 20 }),
    );
    expect(err.code).toBe('TIMEOUT');
  });

  it('defaults to a 15s timeout', async () => {
    jest.useFakeTimers();
    try {
      let aborted = false;
      const fetchImpl = jest.fn(
        (_url: RequestInfo | URL, init?: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            init?.signal?.addEventListener('abort', () => {
              aborted = true;
              reject(new Error('aborted'));
            });
          }),
      );
      const client = createApiClient({
        apiRoot: ROOT,
        tokenStore: memoryTokenStore(null),
        fetchImpl: fetchImpl as unknown as typeof fetch,
      });
      const p = client.request('/questionnaire', { auth: false });
      const assertion = expect(p).rejects.toMatchObject({ code: 'TIMEOUT' });
      jest.advanceTimersByTime(14_999);
      expect(aborted).toBe(false);
      jest.advanceTimersByTime(1);
      await assertion;
    } finally {
      jest.useRealTimers();
    }
  });
});

describe('api client: auth endpoints', () => {
  it('never sends Authorization on auth endpoints and never refreshes on their 401', async () => {
    const { client, fetchImpl, onAuthFailure, store } = setup(() => ({
      status: 401,
      body: envelope('INVALID_CREDENTIALS'),
    }));
    const err = await catchError(
      client.request('/auth/login', { method: 'POST', body: { email: 'a@b.com', password: 'x' }, auth: false }),
    );
    expect(err.code).toBe('INVALID_CREDENTIALS');
    expect(fetchImpl).toHaveBeenCalledTimes(1);
    const headers = fetchImpl.mock.calls[0]![1]!.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
    expect(onAuthFailure).not.toHaveBeenCalled();
    expect(store.current()).not.toBeNull();
  });
});

describe('api client: 401 → refresh once → retry once', () => {
  it('refreshes with a single shared request for concurrent 401s and retries each once', async () => {
    let refreshCalls = 0;
    const handler: FakeHandler = async (req) => {
      if (req.path === '/auth/refresh') {
        refreshCalls += 1;
        expect(req.body).toEqual({ refresh_token: 'R1' });
        expect(req.headers.Authorization).toBeUndefined();
        await new Promise((r) => setTimeout(r, 10));
        return {
          status: 200,
          body: { access_token: 'A2', refresh_token: 'R2', token_type: 'bearer', expires_in: 1800 },
        };
      }
      if (req.headers.Authorization === 'Bearer A2') return { status: 200, body: { path: req.path } };
      return { status: 401, body: envelope('TOKEN_EXPIRED') };
    };
    const { client, store, fetchImpl, onAuthFailure } = setup(handler);

    const results = await Promise.all([
      client.request('/users/me'),
      client.request('/users/me/profile'),
      client.request('/users/me/questionnaire'),
    ]);

    expect(results).toEqual([
      { path: '/users/me' },
      { path: '/users/me/profile' },
      { path: '/users/me/questionnaire' },
    ]);
    expect(refreshCalls).toBe(1);
    expect(store.current()).toEqual({ accessToken: 'A2', refreshToken: 'R2' });
    // 3 originals + 1 refresh + 3 retries
    expect(fetchImpl).toHaveBeenCalledTimes(7);
    expect(onAuthFailure).not.toHaveBeenCalled();
  });

  it('also refreshes on INVALID_TOKEN', async () => {
    const handler: FakeHandler = (req) => {
      if (req.path === '/auth/refresh') {
        return {
          status: 200,
          body: { access_token: 'A2', refresh_token: 'R2', token_type: 'bearer', expires_in: 1800 },
        };
      }
      return req.headers.Authorization === 'Bearer A2'
        ? { status: 200, body: { ok: true } }
        : { status: 401, body: envelope('INVALID_TOKEN') };
    };
    const { client } = setup(handler);
    await expect(client.request('/users/me')).resolves.toEqual({ ok: true });
  });

  it('retries only once: a second 401 after refresh signs out without another refresh', async () => {
    let refreshCalls = 0;
    const handler: FakeHandler = (req) => {
      if (req.path === '/auth/refresh') {
        refreshCalls += 1;
        return {
          status: 200,
          body: { access_token: 'A2', refresh_token: 'R2', token_type: 'bearer', expires_in: 1800 },
        };
      }
      return { status: 401, body: envelope('TOKEN_EXPIRED') };
    };
    const { client, store, fetchImpl, onAuthFailure } = setup(handler);
    const err = await catchError(client.request('/users/me'));
    expect(err.status).toBe(401);
    expect(refreshCalls).toBe(1);
    expect(fetchImpl).toHaveBeenCalledTimes(3);
    expect(store.current()).toBeNull();
    expect(onAuthFailure).toHaveBeenCalledTimes(1);
  });

  it('clears tokens and signals logout when refresh is rejected', async () => {
    const handler: FakeHandler = (req) =>
      req.path === '/auth/refresh'
        ? { status: 401, body: envelope('TOKEN_EXPIRED') }
        : { status: 401, body: envelope('TOKEN_EXPIRED') };
    const { client, store, onAuthFailure, fetchImpl } = setup(handler);
    const [a, b] = await Promise.all([
      catchError(client.request('/users/me')),
      catchError(client.request('/users/me/profile')),
    ]);
    expect(a.code).toBe('TOKEN_EXPIRED');
    expect(b.code).toBe('TOKEN_EXPIRED');
    expect(store.current()).toBeNull();
    expect(onAuthFailure).toHaveBeenCalled();
    // 2 originals + exactly 1 shared refresh, no retries
    expect(fetchImpl.mock.calls.filter((c) => String(c[0]).endsWith('/auth/refresh'))).toHaveLength(1);
    expect(fetchImpl).toHaveBeenCalledTimes(3);
  });

  it('keeps the session when refresh fails for a transient reason (offline)', async () => {
    const handler: FakeHandler = (req) => {
      if (req.path === '/auth/refresh') throw new TypeError('Network request failed');
      return { status: 401, body: envelope('TOKEN_EXPIRED') };
    };
    const fetchImpl = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith('/auth/refresh')) throw new TypeError('Network request failed');
      return makeFetch(handler)(input, init);
    });
    const store = memoryTokenStore({ accessToken: 'A1', refreshToken: 'R1' });
    const client = createApiClient({ apiRoot: ROOT, tokenStore: store, fetchImpl: fetchImpl as unknown as typeof fetch });
    const onAuthFailure = jest.fn();
    client.setAuthFailureHandler(onAuthFailure);
    const err = await catchError(client.request('/users/me'));
    expect(err.code).toBe('NETWORK_ERROR');
    expect(store.current()).toEqual({ accessToken: 'A1', refreshToken: 'R1' });
    expect(onAuthFailure).not.toHaveBeenCalled();
  });

  it('does not refresh on NOT_AUTHENTICATED or non-auth errors', async () => {
    const { client, fetchImpl } = setup(() => ({ status: 401, body: envelope('NOT_AUTHENTICATED') }));
    await catchError(client.request('/users/me'));
    expect(fetchImpl).toHaveBeenCalledTimes(1);
  });

  it('signals logout without calling the network when there are no tokens', async () => {
    const { client, fetchImpl, onAuthFailure } = setup(() => ({ status: 200, body: {} }), null);
    const err = await catchError(client.request('/users/me'));
    expect(err.code).toBe('NOT_AUTHENTICATED');
    expect(fetchImpl).not.toHaveBeenCalled();
    expect(onAuthFailure).toHaveBeenCalledTimes(1);
  });
});
