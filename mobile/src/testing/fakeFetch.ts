/**
 * Test-only helpers: a minimal fetch stand-in and an in-memory fake of the Sprint 1 auth/user
 * endpoints. Not imported by app code.
 */

export interface FakeRequest {
  url: string;
  path: string;
  method: string;
  headers: Record<string, string>;
  body: unknown;
}

export interface FakeResponse {
  status: number;
  body?: unknown;
}

export type FakeHandler = (req: FakeRequest) => FakeResponse | Promise<FakeResponse>;

export function toResponse({ status, body }: FakeResponse): Response {
  const text = body === undefined ? '' : typeof body === 'string' ? body : JSON.stringify(body);
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => text,
  } as unknown as Response;
}

export function makeFetch(handler: FakeHandler) {
  return jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const path = url.replace(/^https?:\/\/[^/]+\/api\/v1/, '');
    const req: FakeRequest = {
      url,
      path,
      method: init?.method ?? 'GET',
      headers: (init?.headers as Record<string, string>) ?? {},
      body: typeof init?.body === 'string' ? JSON.parse(init.body) : undefined,
    };
    return toResponse(await handler(req));
  });
}

export const envelope = (code: string, message = code, fields?: Record<string, string>) => ({
  error: { code, message, ...(fields ? { fields } : {}) },
});

/** In-memory backend for auth + /users/me, enough to exercise session restore end-to-end. */
export function createFakeBackend() {
  let seq = 0;
  const users = new Map<string, { id: number; password: string }>();
  const access = new Map<string, number>(); // token -> user id
  const refresh = new Map<string, number>();
  const onboarding = {
    profile_complete: true,
    questionnaire_complete: false,
    questionnaire_answered: 17,
    questionnaire_total: 71,
    questionnaire_version: 'ipip-v1',
    complete: false,
  };
  const calls: string[] = [];

  function issue(userId: number) {
    seq += 1;
    const pair = {
      access_token: `access-${seq}`,
      refresh_token: `refresh-${seq}`,
      token_type: 'bearer',
      expires_in: 1800,
    };
    access.set(pair.access_token, userId);
    refresh.set(pair.refresh_token, userId);
    return pair;
  }

  const handler: FakeHandler = (req) => {
    calls.push(`${req.method} ${req.path}`);
    const body = req.body as Record<string, string> | undefined;
    if (req.path === '/auth/register' && req.method === 'POST') {
      const email = body!.email!;
      if (users.has(email)) return { status: 409, body: envelope('EMAIL_TAKEN') };
      const id = users.size + 1;
      users.set(email, { id, password: body!.password! });
      return { status: 201, body: issue(id) };
    }
    if (req.path === '/auth/login' && req.method === 'POST') {
      const u = users.get(body!.email!);
      if (!u || u.password !== body!.password) {
        return { status: 401, body: envelope('INVALID_CREDENTIALS') };
      }
      return { status: 200, body: issue(u.id) };
    }
    if (req.path === '/auth/refresh' && req.method === 'POST') {
      const uid = refresh.get(body!.refresh_token!);
      if (uid === undefined) return { status: 401, body: envelope('INVALID_TOKEN') };
      return { status: 200, body: issue(uid) };
    }
    const auth = req.headers.Authorization;
    if (!auth) return { status: 401, body: envelope('NOT_AUTHENTICATED') };
    const token = auth.replace(/^Bearer /, '');
    const uid = access.get(token);
    if (uid === undefined) return { status: 401, body: envelope('TOKEN_EXPIRED') };
    if (req.path === '/users/me') {
      const email = [...users.entries()].find(([, u]) => u.id === uid)?.[0] ?? 'x@example.com';
      return {
        status: 200,
        body: {
          id: uid,
          email,
          is_verified: false,
          created_at: '2026-09-25T10:00:00+00:00',
          onboarding: { ...onboarding },
        },
      };
    }
    return { status: 404, body: envelope('NOT_FOUND') };
  };

  return {
    handler,
    calls,
    onboarding,
    addUser(email: string, password: string) {
      users.set(email, { id: users.size + 1, password });
    },
    /** Simulate every outstanding access token expiring. */
    expireAccessTokens() {
      access.clear();
    },
    revokeRefreshTokens() {
      refresh.clear();
    },
  };
}
