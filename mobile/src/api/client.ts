import { session as defaultSession, type Session } from '../auth/session';
import { DEFAULT_TIMEOUT_MS, getApiBaseUrl } from '../config/env';
import { ApiError, apiErrorFromResponse, defaultMessage } from './errors';
import type { Token } from './types';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  /** Attach the bearer token and apply 401 → refresh → retry handling. Default true. */
  auth?: boolean;
  timeoutMs?: number;
  /** Caller-controlled cancellation (e.g. screen unmount). Aborting rejects with an AbortError. */
  signal?: AbortSignal;
}

export interface ApiClientOptions {
  getBaseUrl: () => string;
  session: Session;
  fetchImpl?: typeof fetch;
  timeoutMs?: number;
  onSessionExpired?: () => void;
}

export interface ApiClient {
  request<T>(path: string, options?: RequestOptions): Promise<T>;
  setSessionExpiredHandler(handler: (() => void) | undefined): void;
}

interface RawResponse {
  status: number;
  ok: boolean;
  body: unknown;
}

function parseBody(text: string): unknown {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function isAbortError(e: unknown): boolean {
  return typeof e === 'object' && e !== null && (e as { name?: string }).name === 'AbortError';
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const fetchImpl = options.fetchImpl ?? ((...args: Parameters<typeof fetch>) => fetch(...args));
  const defaultTimeout = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const { session } = options;
  let onSessionExpired = options.onSessionExpired;
  let refreshInFlight: Promise<string> | null = null;

  /** One HTTP round trip (including body read) bounded by a timeout. Never retries. */
  async function send(
    path: string,
    method: HttpMethod,
    body: unknown,
    accessToken: string | null,
    timeoutMs: number,
    externalSignal?: AbortSignal,
  ): Promise<RawResponse> {
    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
    const onExternalAbort = () => controller.abort();
    if (externalSignal) {
      if (externalSignal.aborted) controller.abort();
      else externalSignal.addEventListener('abort', onExternalAbort);
    }

    const headers: Record<string, string> = { Accept: 'application/json' };
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

    try {
      const res = await fetchImpl(`${options.getBaseUrl()}${path}`, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });
      const text = await res.text();
      return { status: res.status, ok: res.ok, body: parseBody(text) };
    } catch (e) {
      if (timedOut) {
        throw new ApiError({ status: 0, code: 'timeout', message: defaultMessage('timeout') });
      }
      if (externalSignal?.aborted && isAbortError(e)) {
        throw e;
      }
      throw new ApiError({ status: 0, code: 'network', message: defaultMessage('network') });
    } finally {
      clearTimeout(timer);
      externalSignal?.removeEventListener('abort', onExternalAbort);
    }
  }

  async function expireSession(): Promise<void> {
    await session.clear();
    onSessionExpired?.();
  }

  function unauthorized(message = defaultMessage('unauthorized')): ApiError {
    return new ApiError({ status: 401, code: 'unauthorized', message });
  }

  async function performRefresh(): Promise<string> {
    const refreshToken = session.getRefreshToken();
    if (!refreshToken) {
      await expireSession();
      throw unauthorized();
    }
    // Network / timeout errors propagate WITHOUT clearing the session: the user may simply be offline.
    const res = await send('/auth/refresh', 'POST', { refresh_token: refreshToken }, null, defaultTimeout);
    if (res.ok) {
      const token = res.body as Token;
      if (!token || typeof token.access_token !== 'string' || typeof token.refresh_token !== 'string') {
        await expireSession();
        throw unauthorized();
      }
      await session.setTokens(token);
      return token.access_token;
    }
    if (res.status >= 500) {
      throw apiErrorFromResponse(res.status, res.body);
    }
    // 400/401/403/422: the refresh token is invalid/expired → the session is over.
    await expireSession();
    throw unauthorized();
  }

  /** Single-flight refresh: concurrent 401s share one POST /auth/refresh. */
  function refreshAccessToken(staleToken: string | null): Promise<string> {
    const current = session.getAccessToken();
    if (current && current !== staleToken) {
      // Another request already refreshed while this one was in flight.
      return Promise.resolve(current);
    }
    if (!refreshInFlight) {
      refreshInFlight = performRefresh().finally(() => {
        refreshInFlight = null;
      });
    }
    return refreshInFlight;
  }

  async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
    const method = opts.method ?? 'GET';
    const auth = opts.auth ?? true;
    const timeoutMs = opts.timeoutMs ?? defaultTimeout;

    if (!auth) {
      const res = await send(path, method, opts.body, null, timeoutMs, opts.signal);
      if (!res.ok) throw apiErrorFromResponse(res.status, res.body);
      return res.body as T;
    }

    // If a refresh is already running, wait for it rather than sending a token we know is stale.
    let token = refreshInFlight ? await refreshInFlight : session.getAccessToken();
    if (!token) {
      if (session.getRefreshToken()) {
        token = await refreshAccessToken(null);
      } else {
        throw unauthorized();
      }
    }

    let res = await send(path, method, opts.body, token, timeoutMs, opts.signal);
    if (res.status === 401) {
      const fresh = await refreshAccessToken(token);
      res = await send(path, method, opts.body, fresh, timeoutMs, opts.signal);
      if (res.status === 401) {
        await expireSession();
        throw apiErrorFromResponse(401, res.body);
      }
    }
    if (!res.ok) throw apiErrorFromResponse(res.status, res.body);
    return res.body as T;
  }

  return {
    request,
    setSessionExpiredHandler(handler) {
      onSessionExpired = handler;
    },
  };
}

/** App-wide client. The auth store registers the session-expired handler at startup. */
export const apiClient: ApiClient = createApiClient({
  getBaseUrl: getApiBaseUrl,
  session: defaultSession,
});
