import { ApiError, errorFromResponseBody } from './errors';
import type { TokenPair } from './types';
import type { StoredTokens, TokenStore } from '@/auth/tokenStorage';

export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

export interface RequestOptions {
  method?: HttpMethod;
  body?: unknown;
  /** Attach the bearer token and apply the 401 → refresh → retry-once rule. Default true. */
  auth?: boolean;
  timeoutMs?: number;
  signal?: AbortSignal;
}

export interface ApiClientDeps {
  /** API root including `/api/v1`, no trailing slash. */
  apiRoot: string;
  tokenStore: TokenStore;
  timeoutMs?: number;
  fetchImpl?: typeof fetch;
}

export interface ApiClient {
  request<T>(path: string, options?: RequestOptions): Promise<T>;
  /** Registers the handler invoked when the session is unrecoverable (refresh failed). */
  setAuthFailureHandler(handler: (() => void) | null): void;
}

const DEFAULT_TIMEOUT_MS = 15_000;
const REFRESH_PATH = '/auth/refresh';
/** 401 codes that mean "your access token is no good" and are worth a refresh attempt. */
const REFRESHABLE_CODES = new Set(['TOKEN_EXPIRED', 'INVALID_TOKEN']);

export function createApiClient(deps: ApiClientDeps): ApiClient {
  const { apiRoot, tokenStore } = deps;
  const defaultTimeout = deps.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const doFetch: typeof fetch = (...args) => (deps.fetchImpl ?? globalThis.fetch)(...args);

  let onAuthFailure: (() => void) | null = null;
  let refreshInFlight: Promise<StoredTokens> | null = null;

  /** One HTTP round-trip: timeout, JSON in/out, envelope → ApiError. No auth logic here. */
  async function send<T>(path: string, opts: RequestOptions, accessToken: string | null): Promise<T> {
    const controller = new AbortController();
    let timedOut = false;
    const timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, opts.timeoutMs ?? defaultTimeout);
    const onOuterAbort = () => controller.abort();
    opts.signal?.addEventListener('abort', onOuterAbort);

    const headers: Record<string, string> = { Accept: 'application/json' };
    if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

    let response: Response;
    try {
      response = await doFetch(`${apiRoot}${path}`, {
        method: opts.method ?? 'GET',
        headers,
        body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
        signal: controller.signal,
      });
    } catch {
      if (timedOut) throw new ApiError(0, 'TIMEOUT', 'The request timed out');
      if (opts.signal?.aborted) throw new ApiError(0, 'ABORTED', 'The request was cancelled');
      throw new ApiError(0, 'NETWORK_ERROR', 'Network request failed');
    } finally {
      clearTimeout(timer);
      opts.signal?.removeEventListener('abort', onOuterAbort);
    }

    let parsed: unknown = undefined;
    let text = '';
    try {
      text = await response.text();
    } catch {
      throw new ApiError(response.status, 'NETWORK_ERROR', 'Connection lost while reading response');
    }
    if (text.length > 0) {
      try {
        parsed = JSON.parse(text);
      } catch {
        if (response.ok) {
          throw new ApiError(response.status, 'INVALID_RESPONSE', 'Server returned invalid JSON');
        }
      }
    }
    if (!response.ok) throw errorFromResponseBody(response.status, parsed);
    return parsed as T;
  }

  async function signalAuthFailure(): Promise<void> {
    await tokenStore.clearTokens();
    onAuthFailure?.();
  }

  /** Single-flight refresh: concurrent callers share one `/auth/refresh` request. */
  function refreshTokens(): Promise<StoredTokens> {
    if (!refreshInFlight) {
      refreshInFlight = (async () => {
        const current = tokenStore.getTokens();
        if (!current) {
          throw new ApiError(401, 'NOT_AUTHENTICATED', 'Not signed in');
        }
        const pair = await send<TokenPair>(
          REFRESH_PATH,
          { method: 'POST', body: { refresh_token: current.refreshToken }, auth: false },
          null,
        );
        const next = { accessToken: pair.access_token, refreshToken: pair.refresh_token };
        await tokenStore.saveTokens(next);
        return next;
      })().finally(() => {
        refreshInFlight = null;
      });
    }
    return refreshInFlight;
  }

  /**
   * Refresh; on an auth rejection clear tokens and signal logout. Transient failures (network,
   * timeout, 5xx) propagate WITHOUT logging out — a flaky connection must not end the session.
   */
  async function refreshOrLogout(): Promise<StoredTokens> {
    try {
      return await refreshTokens();
    } catch (e) {
      if (e instanceof ApiError && !e.isTransient) {
        await signalAuthFailure();
      }
      throw e;
    }
  }

  async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const auth = options.auth ?? true;
    if (!auth) return send<T>(path, options, null);

    let tokens = tokenStore.getTokens();
    if (!tokens) {
      await signalAuthFailure();
      throw new ApiError(401, 'NOT_AUTHENTICATED', 'Not signed in');
    }

    try {
      return await send<T>(path, options, tokens.accessToken);
    } catch (e) {
      if (!(e instanceof ApiError) || e.status !== 401 || !REFRESHABLE_CODES.has(e.code)) throw e;
    }

    // 401 TOKEN_EXPIRED / INVALID_TOKEN. If another request already rotated the tokens while this
    // one was in flight, just retry with the new access token instead of refreshing again.
    const latest = tokenStore.getTokens();
    if (latest && latest.accessToken !== tokens.accessToken) {
      tokens = latest;
    } else {
      tokens = await refreshOrLogout();
    }

    // Retry exactly once. A second auth failure means the session is unusable.
    try {
      return await send<T>(path, options, tokens.accessToken);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) await signalAuthFailure();
      throw e;
    }
  }

  return {
    request,
    setAuthFailureHandler(handler) {
      onAuthFailure = handler;
    },
  };
}
