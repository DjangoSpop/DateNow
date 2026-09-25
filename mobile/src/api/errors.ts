import type { ApiErrorCode } from './types';

/**
 * Every failure surfaced by the API layer is an ApiError. Screens branch on `code`, never `message`.
 * `status` is 0 for failures that never produced an HTTP response (network, timeout, abort).
 */
export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode | (string & {});
  readonly fields: Record<string, string> | undefined;

  constructor(
    status: number,
    code: ApiErrorCode | (string & {}),
    message: string,
    fields?: Record<string, string>,
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fields = fields;
  }

  /** True when retrying later might succeed without the user changing anything. */
  get isTransient(): boolean {
    return (
      this.code === 'NETWORK_ERROR' ||
      this.code === 'TIMEOUT' ||
      this.status >= 500 ||
      this.status === 0
    );
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

function isRecordOfStrings(v: unknown): v is Record<string, string> {
  return (
    typeof v === 'object' &&
    v !== null &&
    !Array.isArray(v) &&
    Object.values(v).every((x) => typeof x === 'string')
  );
}

function fallbackCode(status: number): ApiErrorCode {
  if (status === 422) return 'VALIDATION_ERROR';
  if (status === 404) return 'NOT_FOUND';
  if (status === 401) return 'NOT_AUTHENTICATED';
  if (status >= 500) return 'INTERNAL_ERROR';
  return 'UNKNOWN_ERROR';
}

/** Parse the contract error envelope; tolerate anything else by falling back on the status. */
export function errorFromResponseBody(status: number, body: unknown): ApiError {
  if (typeof body === 'object' && body !== null && 'error' in body) {
    const err = (body as { error: unknown }).error;
    if (typeof err === 'object' && err !== null) {
      const { code, message, fields } = err as Record<string, unknown>;
      if (typeof code === 'string' && code.length > 0) {
        return new ApiError(
          status,
          code,
          typeof message === 'string' ? message : 'Request failed',
          isRecordOfStrings(fields) ? fields : undefined,
        );
      }
    }
  }
  return new ApiError(status, fallbackCode(status), `Request failed (HTTP ${status})`);
}

/** Friendly, non-technical copy for errors that aren't mapped onto a specific field. */
export function describeError(e: unknown): string {
  if (!isApiError(e)) return 'Something went wrong. Please try again.';
  switch (e.code) {
    case 'NETWORK_ERROR':
      return "We couldn't reach DateNow. Check your connection and try again.";
    case 'TIMEOUT':
      return 'This is taking longer than usual. Please try again.';
    case 'INVALID_CREDENTIALS':
      return "That email and password don't match. Please try again.";
    case 'ACCOUNT_DISABLED':
      return 'This account has been disabled. Please contact support.';
    case 'EMAIL_TAKEN':
      return 'An account with this email already exists. Try signing in instead.';
    case 'INTERNAL_ERROR':
      return 'Something went wrong on our side. Please try again in a moment.';
    case 'VALIDATION_ERROR':
      return 'Some details need another look.';
    default:
      return e.message || 'Something went wrong. Please try again.';
  }
}
