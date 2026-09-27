import type { ConfigContext, ExpoConfig } from 'expo/config';

/**
 * Build-time app configuration.
 *
 * Environment variables (read when Metro / EAS evaluates this file):
 *   APP_ENV              development | preview | production (default: development)
 *   EXPO_PUBLIC_API_URL  Backend origin, e.g. https://api.datenow.app (WITHOUT /api/v1).
 *
 * In production the API URL is REQUIRED and MUST be https: the config throws otherwise,
 * so a release binary can never be built to talk to the backend over cleartext HTTP.
 * (The runtime resolver in src/config/env.ts enforces the same rule a second time.)
 */
type AppEnv = 'development' | 'preview' | 'production';

const APP_ENV = (process.env.APP_ENV ?? 'development') as AppEnv;
const API_URL = process.env.EXPO_PUBLIC_API_URL?.trim() || undefined;

if (APP_ENV === 'production') {
  if (!API_URL) {
    throw new Error('EXPO_PUBLIC_API_URL is required when APP_ENV=production');
  }
  if (!API_URL.startsWith('https://')) {
    throw new Error(`EXPO_PUBLIC_API_URL must use https:// in production (got "${API_URL}")`);
  }
}

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'DateNow',
  slug: 'datenow',
  scheme: 'datenow',
  version: '0.1.0',
  orientation: 'portrait',
  icon: './assets/icon.png',
  userInterfaceStyle: 'light',
  ios: {
    supportsTablet: false,
    bundleIdentifier: 'ai.datenow.app',
  },
  android: {
    package: 'ai.datenow.app',
    adaptiveIcon: {
      backgroundColor: '#E6F4FF',
      foregroundImage: './assets/android-icon-foreground.png',
      backgroundImage: './assets/android-icon-background.png',
      monochromeImage: './assets/android-icon-monochrome.png',
    },
    predictiveBackGestureEnabled: false,
  },
  web: {
    favicon: './assets/favicon.png',
  },
  plugins: [
    'expo-router',
    'expo-secure-store',
    [
      'expo-splash-screen',
      {
        image: './assets/splash-icon.png',
        imageWidth: 160,
        resizeMode: 'contain',
        backgroundColor: '#F0F9FF',
      },
    ],
  ],
  extra: {
    ...config.extra,
    appEnv: APP_ENV,
    // Omitted (not null) when unset: Expo's config serializer turns null into {}.
    ...(API_URL ? { apiUrl: API_URL } : {}),
  },
});
