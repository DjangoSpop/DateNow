import type { FastApiErrorBody, FastApiValidationItem, QuestionnaireValidationItem } from './types';

export type ApiErrorCode =
  | 'network'
  | 'timeout'
  | 'unauthorized'
  | 'validation'
  | 'conflict'
  | 'not_found'
  | 'server'
  | 'unknown';

export interface ValidationIssue {
  /** Full FastAPI location, e.g. ["body", "answers", "bf_1"]. */
  loc: (string | number)[];
  msg: string;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  /** Field name (last string segment of `loc`, "body" excluded) → message. */
  readonly fieldErrors?: Record<string, string>;
  /** Raw validation items, kept for callers that need the full `loc` path. */
  readonly issues?: ValidationIssue[];

  constructor(params: {
    status: number;
    code: ApiErrorCode;
    message: string;
    fieldErrors?: Record<string, string>;
    issues?: ValidationIssue[];
  }) {
    super(params.message);
    this.name = 'ApiError';
    this.status = params.status;
    this.code = params.code;
    this.fieldErrors = params.fieldErrors;
    this.issues = params.issues;
  }
}

export function isApiError(e: unknown): e is ApiError {
  return e instanceof ApiError;
}

export function codeForStatus(status: number): ApiErrorCode {
  if (status === 401 || status === 403) return 'unauthorized';
  if (status === 400 || status === 422) return 'validation';
  if (status === 404) return 'not_found';
  if (status === 409) return 'conflict';
  if (status >= 500) return 'server';
  return 'unknown';
}

const DEFAULT_MESSAGES: Record<ApiErrorCode, string> = {
  network: "We couldn't reach DateNow. Check your connection and try again.",
  timeout: 'The request took too long. Please try again.',
  unauthorized: 'Your session has ended. Please sign in again.',
  validation: 'Some information needs another look.',
  conflict: 'That conflicts with existing data.',
  not_found: 'Not found.',
  server: 'Something went wrong on our side. Please try again shortly.',
  unknown: 'Something unexpected happened.',
};

export function defaultMessage(code: ApiErrorCode): string {
  return DEFAULT_MESSAGES[code];
}

/** Picks the most specific field name from a FastAPI `loc` (skips "body"/"query"/"path" and indices). */
export function fieldNameFromLoc(loc: (string | number)[]): string | null {
  const strings = loc.filter((p): p is string => typeof p === 'string');
  const meaningful = strings.filter((p) => !['body', 'query', 'path', 'header'].includes(p));
  return meaningful.length ? meaningful[meaningful.length - 1] : null;
}

function isValidationItem(v: unknown): v is FastApiValidationItem {
  return (
    typeof v === 'object' &&
    v !== null &&
    Array.isArray((v as FastApiValidationItem).loc) &&
    typeof (v as FastApiValidationItem).msg === 'string'
  );
}

const ALL_QUESTIONS = '__all__';

function isQuestionItem(v: unknown): v is QuestionnaireValidationItem {
  return (
    typeof v === 'object' &&
    v !== null &&
    typeof (v as QuestionnaireValidationItem).question_id === 'string' &&
    typeof (v as QuestionnaireValidationItem).message === 'string'
  );
}

/** Strips pydantic's "Value error, " prefix for display. */
function cleanMsg(msg: string): string {
  return msg.replace(/^Value error,\s*/i, '');
}

/** Builds an ApiError from an HTTP status + parsed JSON body (FastAPI `{detail}` shape). */
export function apiErrorFromResponse(status: number, body: unknown): ApiError {
  const code = codeForStatus(status);
  const detail = (body as FastApiErrorBody | null)?.detail;

  if (typeof detail === 'string' && detail.trim()) {
    return new ApiError({ status, code, message: detail });
  }

  if (Array.isArray(detail)) {
    const fieldErrors: Record<string, string> = {};
    const issues: ValidationIssue[] = [];
    for (const item of detail as unknown[]) {
      if (isValidationItem(item)) {
        issues.push({ loc: item.loc, msg: cleanMsg(item.msg) });
      } else if (isQuestionItem(item)) {
        // Questionnaire endpoints: {question_id, message}; "__all__" is a whole-body error.
        issues.push({
          loc: item.question_id === ALL_QUESTIONS ? ['body'] : ['body', 'answers', item.question_id],
          msg: item.message,
        });
      }
    }
    for (const issue of issues) {
      const field = fieldNameFromLoc(issue.loc);
      if (field && !fieldErrors[field]) fieldErrors[field] = issue.msg;
    }
    const message = issues.length === 1 ? issues[0].msg : defaultMessage(code);
    return new ApiError({
      status,
      code,
      message,
      fieldErrors: Object.keys(fieldErrors).length ? fieldErrors : undefined,
      issues,
    });
  }

  return new ApiError({ status, code, message: defaultMessage(code) });
}
