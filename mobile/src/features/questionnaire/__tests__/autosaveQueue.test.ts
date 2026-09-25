import { ApiError } from '@/api/errors';
import type { Answers } from '@/api/types';
import { AutosaveQueue, MAX_BATCH, type SaveSnapshot } from '../autosaveQueue';

/** Let pending promise callbacks run while fake timers are active. */
async function settle() {
  for (let i = 0; i < 5; i += 1) await Promise.resolve();
}

function setup(save: (a: Answers) => Promise<unknown>) {
  const snapshots: SaveSnapshot[] = [];
  const saveMock = jest.fn(save);
  const queue = new AutosaveQueue({
    save: saveMock,
    onChange: (s) => snapshots.push(s),
    debounceMs: 400,
    baseRetryMs: 2000,
    maxRetryMs: 8000,
  });
  const last = () => snapshots[snapshots.length - 1]!;
  return { queue, saveMock, snapshots, last };
}

beforeEach(() => jest.useFakeTimers());
afterEach(() => jest.useRealTimers());

describe('AutosaveQueue', () => {
  it('debounces answers into a single batched save', async () => {
    const { queue, saveMock, last } = setup(async () => ({}));
    queue.enqueue('bf_1', 4);
    queue.enqueue('bf_2', 2);
    queue.enqueue('bf_1', 5); // newer answer replaces the older one
    expect(saveMock).not.toHaveBeenCalled();
    expect(last().pending).toBe(2);

    jest.advanceTimersByTime(400);
    await settle();

    expect(saveMock).toHaveBeenCalledTimes(1);
    expect(saveMock).toHaveBeenCalledWith({ bf_1: 5, bf_2: 2 });
    expect(last()).toEqual({ status: 'idle', pending: 0, rejected: {} });
  });

  it('keeps answers and retries with backoff on network failure, never losing them', async () => {
    let online = false;
    const { queue, saveMock, last } = setup(async () => {
      if (!online) throw new ApiError(0, 'NETWORK_ERROR', 'offline');
      return {};
    });
    queue.enqueue('bf_1', 3);
    jest.advanceTimersByTime(400);
    await settle();
    expect(last().status).toBe('retrying');
    expect(last().pending).toBe(1);

    // Answer entered while offline joins the retry.
    queue.enqueue('bf_2', 1);
    expect(last().pending).toBe(2);

    jest.advanceTimersByTime(2000); // first backoff
    await settle();
    expect(saveMock).toHaveBeenCalledTimes(2);
    expect(last().status).toBe('retrying');

    online = true;
    jest.advanceTimersByTime(3999);
    await settle();
    expect(saveMock).toHaveBeenCalledTimes(2); // second backoff is 4s
    jest.advanceTimersByTime(1);
    await settle();

    expect(saveMock).toHaveBeenCalledTimes(3);
    expect(saveMock).toHaveBeenLastCalledWith({ bf_1: 3, bf_2: 1 });
    expect(last()).toEqual({ status: 'idle', pending: 0, rejected: {} });
  });

  it('retries on timeouts and 5xx too', async () => {
    const errors = [new ApiError(0, 'TIMEOUT', 't'), new ApiError(503, 'INTERNAL_ERROR', 'x')];
    const { queue, saveMock, last } = setup(async () => {
      const e = errors.shift();
      if (e) throw e;
      return {};
    });
    queue.enqueue('bf_1', 3);
    jest.advanceTimersByTime(400);
    await settle();
    jest.advanceTimersByTime(2000);
    await settle();
    jest.advanceTimersByTime(4000);
    await settle();
    expect(saveMock).toHaveBeenCalledTimes(3);
    expect(last().status).toBe('idle');
  });

  it('does not drop a newer answer that changed while the save was in flight', async () => {
    let resolveSave: () => void = () => {};
    const { queue, saveMock, last } = setup(
      () => new Promise<void>((r) => (resolveSave = r)),
    );
    queue.enqueue('bf_1', 2);
    jest.advanceTimersByTime(400);
    await settle();
    queue.enqueue('bf_1', 5); // changed mid-flight
    resolveSave();
    await settle();
    expect(last().pending).toBe(1);
    jest.advanceTimersByTime(400);
    await settle();
    expect(saveMock).toHaveBeenLastCalledWith({ bf_1: 5 });
  });

  it('drops only server-rejected ids (422) and saves the rest', async () => {
    const { queue, saveMock, last } = setup(async (batch) => {
      if ('bad' in batch) {
        throw new ApiError(422, 'VALIDATION_ERROR', 'invalid', { bad: 'unknown question' });
      }
      return {};
    });
    queue.enqueue('bf_1', 3);
    queue.enqueue('bad', 7);
    jest.advanceTimersByTime(400);
    await settle();
    jest.advanceTimersByTime(0);
    await settle();
    expect(saveMock).toHaveBeenLastCalledWith({ bf_1: 3 });
    expect(last().pending).toBe(0);
    expect(last().rejected).toEqual({ bad: 'unknown question' });
    expect(last().status).toBe('error');
  });

  it('keeps answers on non-retryable errors until the next attempt', async () => {
    let fail = true;
    const { queue, saveMock, last } = setup(async () => {
      if (fail) throw new ApiError(401, 'TOKEN_EXPIRED', 'expired');
      return {};
    });
    queue.enqueue('bf_1', 3);
    jest.advanceTimersByTime(400);
    await settle();
    expect(last()).toMatchObject({ status: 'error', pending: 1 });
    jest.advanceTimersByTime(60_000);
    await settle();
    expect(saveMock).toHaveBeenCalledTimes(1); // no auto-retry loop

    fail = false;
    await expect(queue.flush()).resolves.toBe(true);
    expect(saveMock).toHaveBeenLastCalledWith({ bf_1: 3 });
  });

  it('flush() reports failure while offline and success once back online', async () => {
    let online = false;
    const { queue } = setup(async () => {
      if (!online) throw new ApiError(0, 'NETWORK_ERROR', 'offline');
      return {};
    });
    queue.enqueue('bf_1', 3);
    await expect(queue.flush()).resolves.toBe(false);
    expect(queue.hasPending()).toBe(true);
    online = true;
    await expect(queue.flush()).resolves.toBe(true);
    expect(queue.hasPending()).toBe(false);
  });

  it(`splits large queues into batches of at most ${MAX_BATCH}`, async () => {
    const { queue, saveMock } = setup(async () => ({}));
    for (let i = 0; i < 150; i += 1) queue.enqueue(`q${i}`, 1);
    await expect(queue.flush()).resolves.toBe(true);
    expect(saveMock).toHaveBeenCalledTimes(2);
    expect(Object.keys(saveMock.mock.calls[0]![0])).toHaveLength(MAX_BATCH);
    expect(Object.keys(saveMock.mock.calls[1]![0])).toHaveLength(50);
  });
});
