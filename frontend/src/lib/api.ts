/**
 * Centralized API client for the web client.
 *
 * Contract: docs/API_CONTRACT.md. Tokens are kept in sessionStorage (cleared when
 * the tab closes) and wiped on logout or on a failed refresh. The mobile app uses
 * the platform secure store instead; a cookie-based web session is a later sprint.
 */
import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ACCESS_KEY = 'datenow.access_token';
const REFRESH_KEY = 'datenow.refresh_token';

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export const tokenStorage = {
  getAccessToken: (): string | null => sessionStorage.getItem(ACCESS_KEY),
  getRefreshToken: (): string | null => sessionStorage.getItem(REFRESH_KEY),
  set(tokens: TokenPair) {
    sessionStorage.setItem(ACCESS_KEY, tokens.access_token);
    sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  },
  clear() {
    sessionStorage.removeItem(ACCESS_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  },
};

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Single-flight refresh: concurrent 401s share one refresh request.
let refreshPromise: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) return null;
  try {
    const { data } = await axios.post<TokenPair>(
      `${API_URL}/api/v1/auth/refresh`,
      { refresh_token: refreshToken },
      { timeout: 15000 },
    );
    tokenStorage.set(data);
    return data.access_token;
  } catch {
    tokenStorage.clear();
    return null;
  }
}

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean };

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const config = error.config as RetriableConfig | undefined;
    const isAuthCall = config?.url?.startsWith('/auth/') && !config.url.startsWith('/auth/me');
    if (error.response?.status !== 401 || !config || config._retried || isAuthCall) {
      throw error;
    }
    config._retried = true;
    refreshPromise ??= refreshAccessToken().finally(() => {
      refreshPromise = null;
    });
    const newToken = await refreshPromise;
    if (!newToken) {
      throw error;
    }
    config.headers.Authorization = `Bearer ${newToken}`;
    return api(config);
  },
);

export const authApi = {
  register: (body: { email: string; password: string; first_name: string; last_name?: string }) =>
    api.post<TokenPair>('/auth/register', body),
  login: (body: { email: string; password: string }) => api.post<TokenPair>('/auth/login', body),
  me: () => api.get('/auth/me'),
  logout: () => {
    tokenStorage.clear();
  },
};
