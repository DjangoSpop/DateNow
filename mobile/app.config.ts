import type { ConfigContext, ExpoConfig } from 'expo/config';

/**
 * Build-time app config. Two profiles, chosen with APP_ENV:
 *   APP_ENV=development (default) — API defaults to a local backend.
 *   APP_ENV=production            — EXPO_PUBLIC_API_URL is required and must be https.
 * Nothing secret belongs here: everything in `extra` ships inside the app bundle.
 */
type AppEnv = 'development' | 'production';

function resolveAppEnv(): AppEnv {
  const raw = process.env.APP_ENV ?? 'development';
  if (raw !== 'development' && raw !== 'production') {
    throw new Error(`APP_ENV must be "development" or "production" (got "${raw}")`);
  }
  return raw;
}

function resolveApiUrl(appEnv: AppEnv): string | null {
  const explicit = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (appEnv === 'production') {
    if (!explicit) {
      throw new Error('EXPO_PUBLIC_API_URL is required when APP_ENV=production');
    }
    if (!explicit.startsWith('https://')) {
      throw new Error('EXPO_PUBLIC_API_URL must use https:// in production');
    }
  }
  return explicit ? explicit.replace(/\/+$/, '') : null;
}

export default ({ config }: ConfigContext): ExpoConfig => {
  const appEnv = resolveAppEnv();
  const apiUrl = resolveApiUrl(appEnv);
  return {
    ...config,
    name: appEnv === 'production' ? 'DateNow' : 'DateNow (Dev)',
    slug: 'datenow',
    scheme: 'datenow',
    version: '1.0.0',
    orientation: 'portrait',
    icon: './assets/icon.png',
    userInterfaceStyle: 'light',
    ios: {
      supportsTablet: true,
      bundleIdentifier: appEnv === 'production' ? 'app.datenow' : 'app.datenow.dev',
    },
    android: {
      package: appEnv === 'production' ? 'app.datenow' : 'app.datenow.dev',
      adaptiveIcon: {
        backgroundColor: '#E6F4FF',
        foregroundImage: './assets/android-icon-foreground.png',
        backgroundImage: './assets/android-icon-background.png',
        monochromeImage: './assets/android-icon-monochrome.png',
      },
      predictiveBackGestureEnabled: false,
    },
    web: { favicon: './assets/favicon.png' },
    plugins: ['expo-router', 'expo-secure-store'],
    extra: {
      ...config.extra,
      appEnv,
      // Omitted (not null) when unset: the app then picks a platform-appropriate local default.
      ...(apiUrl ? { apiUrl } : {}),
    },
  };
};
