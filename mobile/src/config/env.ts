import Constants from 'expo-constants';
import { Platform } from 'react-native';

export type AppEnv = 'development' | 'preview' | 'production';

export const API_PREFIX = '/api/v1';
export const DEFAULT_TIMEOUT_MS = 15_000;

export interface ResolveApiBaseUrlInput {
  /** Origin from app.config.ts `extra.apiUrl` or EXPO_PUBLIC_API_URL (no /api/v1 suffix). */
  configured: string | null | undefined;
  appEnv: AppEnv;
  platform: string;
}

/**
 * Pure resolver for the API base URL (origin + /api/v1).
 *
 * - development/preview without a configured URL fall back to the local backend on :8000.
 *   The Android emulator cannot reach the host's `localhost`; it must use 10.0.2.2.
 * - production REQUIRES a configured https URL (throws otherwise).
 */
export function resolveApiBaseUrl({ configured, appEnv, platform }: ResolveApiBaseUrlInput): string {
  let origin = configured?.trim() || '';

  if (!origin) {
    if (appEnv === 'production') {
      throw new Error('API URL is not configured for production (set EXPO_PUBLIC_API_URL).');
    }
    origin = platform === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';
  }

  if (!/^https?:\/\//.test(origin)) {
    throw new Error(`API URL must start with http:// or https:// (got "${origin}")`);
  }
  if (appEnv === 'production' && !origin.startsWith('https://')) {
    throw new Error('Production API URL must use https://');
  }

  origin = origin.replace(/\/+$/, '');
  if (origin.endsWith(API_PREFIX)) {
    return origin;
  }
  return `${origin}${API_PREFIX}`;
}

function readExtra(): { appEnv?: AppEnv; apiUrl?: string } {
  const extra = (Constants.expoConfig?.extra ?? {}) as Record<string, unknown>;
  const appEnv = extra.appEnv;
  return {
    appEnv: appEnv === 'development' || appEnv === 'preview' || appEnv === 'production' ? appEnv : undefined,
    // Defensive: only accept a real string (serialized configs can turn null into {}).
    apiUrl: typeof extra.apiUrl === 'string' ? extra.apiUrl : undefined,
  };
}

export function getAppEnv(): AppEnv {
  return readExtra().appEnv ?? 'development';
}

let cachedBaseUrl: string | null = null;

export function getApiBaseUrl(): string {
  if (cachedBaseUrl) return cachedBaseUrl;
  const extra = readExtra();
  cachedBaseUrl = resolveApiBaseUrl({
    configured: extra.apiUrl ?? process.env.EXPO_PUBLIC_API_URL,
    appEnv: extra.appEnv ?? 'development',
    platform: Platform.OS,
  });
  return cachedBaseUrl;
}
