import { isApiError } from '@/api/errors';
import type { AnswerValue, Answers } from '@/api/types';

export type SaveStatus = 'idle' | 'saving' | 'retrying' | 'error';

export interface SaveSnapshot {
  status: SaveStatus;
  /** Answers entered but not yet confirmed by the server. */
  pending: number;
  /** Question ids the server rejected (422), with its message. These are not retried. */
  rejected: Record<string, string>;
}

export interface AutosaveOptions {
  save: (answers: Answers) => Promise<unknown>;
  onChange?: (snapshot: SaveSnapshot) => void;
  debounceMs?: number;
  baseRetryMs?: number;
  maxRetryMs?: number;
}

/** Contract limit for one PUT /users/me/questionnaire/answers request. */
export const MAX_BATCH = 100;

/**
 * Optimistic answer autosave. Answers are queued immediately, sent in small debounced batches, and
 * kept until the server confirms them:
 * - network / timeout / 5xx → exponential backoff retry (status `retrying`), nothing dropped
 * - 422 with `fields` → only the offending ids are dropped (reported via `rejected`), rest retried
 * - anything else (e.g. session ended) → status `error`, answers kept; the next enqueue or
 *   `flush()` tries again
 * A newer answer for the same question always wins over an in-flight older one.
 */
export class AutosaveQueue {
  private pending = new Map<string, AnswerValue>();
  private rejected: Record<string, string> = {};
  private status: SaveStatus = 'idle';
  private timer: ReturnType<typeof setTimeout> | null = null;
  private inFlight: Promise<void> | null = null;
  private attempt = 0;
  private disposed = false;

  private readonly save: AutosaveOptions['save'];
  private readonly onChange: AutosaveOptions['onChange'];
  private readonly debounceMs: number;
  private readonly baseRetryMs: number;
  private readonly maxRetryMs: number;

  constructor(opts: AutosaveOptions) {
    this.save = opts.save;
    this.onChange = opts.onChange;
    this.debounceMs = opts.debounceMs ?? 400;
    this.baseRetryMs = opts.baseRetryMs ?? 2_000;
    this.maxRetryMs = opts.maxRetryMs ?? 30_000;
  }

  enqueue(questionId: string, value: AnswerValue): void {
    if (this.disposed) return;
    this.pending.set(questionId, value);
    if (questionId in this.rejected) {
      const rest = { ...this.rejected };
      delete rest[questionId];
      this.rejected = rest;
    }
    // While backing off, don't hammer the server; the retry timer will pick this up.
    if (this.status !== 'retrying') this.schedule(this.debounceMs);
    this.emit();
  }

  /** Send everything now. Resolves true when nothing is left pending. */
  async flush(): Promise<boolean> {
    this.clearTimer();
    // Keep going while progress is made (large queues need several batches).
    for (let guard = 0; guard < 50; guard += 1) {
      if (this.inFlight) await this.inFlight;
      if (this.pending.size === 0) return true;
      const before = this.pending.size;
      this.clearTimer();
      await this.run();
      if (this.status === 'retrying' || this.status === 'error') {
        if (this.pending.size >= before) {
          // Leave the automatic retry scheduled; report failure to the caller.
          return false;
        }
      }
    }
    return this.pending.size === 0;
  }

  snapshot(): SaveSnapshot {
    return { status: this.status, pending: this.pending.size, rejected: { ...this.rejected } };
  }

  hasPending(): boolean {
    return this.pending.size > 0;
  }

  dispose(): void {
    this.disposed = true;
    this.clearTimer();
    this.pending.clear();
  }

  private schedule(delay: number): void {
    this.clearTimer();
    this.timer = setTimeout(() => {
      this.timer = null;
      void this.run();
    }, delay);
  }

  private clearTimer(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  }

  private setStatus(status: SaveStatus): void {
    this.status = status;
    this.emit();
  }

  private emit(): void {
    this.onChange?.(this.snapshot());
  }

  private run(): Promise<void> {
    if (this.inFlight) return this.inFlight;
    if (this.disposed || this.pending.size === 0) {
      if (this.status !== 'error' || Object.keys(this.rejected).length === 0) {
        this.setStatus('idle');
      }
      return Promise.resolve();
    }
    const batch: Answers = {};
    for (const [id, value] of this.pending) {
      if (Object.keys(batch).length >= MAX_BATCH) break;
      batch[id] = value;
    }
    if (this.status !== 'retrying') this.setStatus('saving');

    this.inFlight = this.save(batch)
      .then(() => {
        for (const [id, value] of Object.entries(batch)) {
          // Only clear if the user hasn't changed the answer again meanwhile.
          if (this.pending.get(id) === value) this.pending.delete(id);
        }
        this.attempt = 0;
        if (this.pending.size > 0) {
          this.setStatus('saving');
          this.schedule(0);
        } else {
          this.setStatus(Object.keys(this.rejected).length > 0 ? 'error' : 'idle');
        }
      })
      .catch((e: unknown) => this.handleFailure(e, batch))
      .finally(() => {
        this.inFlight = null;
      });
    return this.inFlight;
  }

  private handleFailure(e: unknown, batch: Answers): void {
    if (this.disposed) return;
    if (isApiError(e) && e.status === 422 && e.fields && Object.keys(e.fields).length > 0) {
      const badIds = Object.keys(e.fields).filter((id) => id in batch);
      if (badIds.length > 0) {
        for (const id of badIds) {
          if (this.pending.get(id) === batch[id]) this.pending.delete(id);
          this.rejected = { ...this.rejected, [id]: e.fields[id] ?? 'Invalid answer' };
        }
        this.setStatus('error');
        if (this.pending.size > 0) this.schedule(0);
        return;
      }
    }
    if (isApiError(e) && e.isTransient) {
      this.attempt += 1;
      const delay = Math.min(this.baseRetryMs * 2 ** (this.attempt - 1), this.maxRetryMs);
      this.setStatus('retrying');
      this.schedule(delay);
      return;
    }
    // Non-retryable (e.g. session ended, unexpected 4xx): keep answers, stop auto-retrying.
    this.setStatus('error');
  }
}
