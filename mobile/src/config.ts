import Constants from 'expo-constants';
import { Platform } from 'react-native';

export type AppEnv = 'development' | 'production';

export interface AppConfig {
  appEnv: AppEnv;
  /** Server origin without the `/api/v1` prefix, e.g. `http://localhost:8000`. */
  apiBaseUrl: string;
  /** Fully-qualified API root, e.g. `http://localhost:8000/api/v1`. */
  apiRoot: string;
  requestTimeoutMs: number;
}

interface ExtraConfig {
  appEnv?: unknown;
  apiUrl?: unknown;
}

const nonEmptyString = (v: unknown): string | undefined =>
  typeof v === 'string' && v.trim() !== '' ? v.trim() : undefined;

/**
 * Local backend defaults for development. The Android emulator cannot reach the host machine via
 * `localhost` — it exposes the host as `10.0.2.2`. Physical devices need your machine's LAN IP,
 * set via EXPO_PUBLIC_API_URL.
 */
const DEV_DEFAULT_URL = Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000';

function stripTrailingSlash(url: string): string {
  return url.replace(/\/+$/, '');
}

export function resolveConfig(
  extra: ExtraConfig | undefined,
  envUrl: string | undefined,
): AppConfig {
  const appEnv: AppEnv = extra?.appEnv === 'production' ? 'production' : 'development';
  const fromExtra = nonEmptyString(extra?.apiUrl);
  const fromEnv = nonEmptyString(envUrl);
  const chosen = fromExtra || fromEnv || (appEnv === 'development' ? DEV_DEFAULT_URL : undefined);
  if (!chosen) {
    // app.config.ts refuses to build a production bundle without a URL, so this is defensive.
    throw new Error('API base URL is not configured (set EXPO_PUBLIC_API_URL).');
  }
  const apiBaseUrl = stripTrailingSlash(chosen);
  return {
    appEnv,
    apiBaseUrl,
    apiRoot: `${apiBaseUrl}/api/v1`,
    requestTimeoutMs: 15_000,
  };
}

export const config: AppConfig = resolveConfig(
  Constants.expoConfig?.extra as ExtraConfig | undefined,
  process.env.EXPO_PUBLIC_API_URL,
);
