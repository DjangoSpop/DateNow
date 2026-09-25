import { createApiClient } from './client';
import { tokenStore } from '@/auth/tokenStorage';
import { config } from '@/config';

/** The app-wide API client. Endpoint modules call through this. */
export const apiClient = createApiClient({
  apiRoot: config.apiRoot,
  tokenStore,
  timeoutMs: config.requestTimeoutMs,
});
