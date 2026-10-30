import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { useAstronomicalEvents } from './useAstronomicalEvents';
import { fetchContactTimesInQueue } from './useContactTimesQueue';
import { ApiError } from '@/services/api';
import { getCurrentLocale, setCurrentLocale } from '@/i18n';
import type { AstronomicalEvent, EclipseContactTimesResponse } from '@/types/api.types';

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

const date = '2025-09-07';
const response = { contact_times: { p1: 'first contact' } };
const eclipse = () => ({ date, is_lunar: true, contact_times: null }) as AstronomicalEvent;

const unhandledRejection = vi.fn();
beforeEach(() => {
  unhandledRejection.mockClear();
  process.on('unhandledRejection', unhandledRejection);
});
afterEach(async () => {
  vi.useRealTimers();
  await flushPromises();
  process.removeListener('unhandledRejection', unhandledRejection);
  expect(unhandledRejection).not.toHaveBeenCalled();
});

function setup() {
  const requests: Array<ReturnType<typeof deferred<EclipseContactTimesResponse>>> = [];
  const signals: AbortSignal[] = [];
  const api = {
    getAstronomicalEvents: vi.fn(),
    getBatchEarthObservations: vi.fn(),
    getContactTimesForEvent: vi.fn((_date: string, _isLunar: boolean, signal?: AbortSignal) => {
      const request = deferred<EclipseContactTimesResponse>();
      requests.push(request);
      signals.push(signal!);
      return request.promise;
    }),
  };
  const state = useAstronomicalEvents(api);
  state.events.value = [eclipse()];
  state.allSseEvents.value = [eclipse()];
  return { ...state, api, requests, signals };
}

describe('contact time subscriber cancellation', () => {
  it('does not start or join work for a pre-aborted subscriber', async () => {
    const state = setup();
    const controller = new AbortController();
    controller.abort();
    await expect(state.fetchContactTimesForEvent(date, true, controller.signal))
      .rejects.toMatchObject({ name: 'AbortError' });
    expect(state.api.getContactTimesForEvent).not.toHaveBeenCalled();
  });

  it('leaves other subscribers running when one cancels', async () => {
    const state = setup();
    const first = new AbortController();
    const second = new AbortController();
    const cancelled = state.fetchContactTimesForEvent(date, true, first.signal);
    const assertion = expect(cancelled).rejects.toMatchObject({ name: 'AbortError' });
    const remaining = state.fetchContactTimesForEvent(date, true, second.signal);
    await flushPromises();
    first.abort();
    await assertion;
    expect(state.signals[0].aborted).toBe(false);
    state.requests[0].resolve(response);
    await remaining;
    expect(state.api.getContactTimesForEvent).toHaveBeenCalledTimes(1);
    expect(state.events.value[0].contact_times).toEqual(response.contact_times);
    expect(state.allSseEvents.value[0].contact_times).toEqual(response.contact_times);
  });

  it.each([true, false])('pins a request with an unsignalled subscriber until settlement (unsignalled first: %s)', async (unsignalledFirst) => {
    const state = setup();
    const controller = new AbortController();
    const first = unsignalledFirst ? state.fetchContactTimesForEvent(date, true) : null;
    const cancelled = state.fetchContactTimesForEvent(date, true, controller.signal);
    const assertion = expect(cancelled).rejects.toMatchObject({ name: 'AbortError' });
    const pinned = first ?? state.fetchContactTimesForEvent(date, true);
    await flushPromises();
    controller.abort();
    await assertion;
    expect(state.signals[0].aborted).toBe(false);
    state.requests[0].resolve(response);
    await pinned;
    const next = state.fetchContactTimesForEvent(date, true);
    await flushPromises();
    expect(state.api.getContactTimesForEvent).toHaveBeenCalledTimes(2);
    state.requests[1].resolve(response);
    await next;
  });

  it.each(['resolve', 'reject'] as const)('removes abandoned work immediately and guards replacement against late %s', async (outcome) => {
    const state = setup();
    const controller = new AbortController();
    const old = state.fetchContactTimesForEvent(date, true, controller.signal);
    const assertion = expect(old).rejects.toMatchObject({ name: 'AbortError' });
    await flushPromises();
    controller.abort();
    await assertion;
    expect(state.signals[0].aborted).toBe(true);

    const replacement = state.fetchContactTimesForEvent(date, true);
    await flushPromises();
    expect(state.api.getContactTimesForEvent).toHaveBeenCalledTimes(2);
    if (outcome === 'resolve') state.requests[0].resolve(response);
    else state.requests[0].reject(new Error('Late failure after cancellation'));
    await flushPromises();
    expect(state.events.value[0].contact_times).toBeNull();
    expect(state.allSseEvents.value[0].contact_times).toBeNull();

    const joined = state.fetchContactTimesForEvent(date, true);
    await flushPromises();
    expect(state.api.getContactTimesForEvent).toHaveBeenCalledTimes(2);
    state.requests[1].resolve({ contact_times: { p1: 'replacement' } });
    await Promise.all([replacement, joined]);
    expect(state.events.value[0].contact_times).toEqual({ p1: 'replacement' });
  });

  it('aborts only after the last signalled subscriber cancels', async () => {
    const state = setup();
    const controllers = [new AbortController(), new AbortController()];
    const assertions = controllers.map((controller) =>
      expect(state.fetchContactTimesForEvent(date, true, controller.signal))
        .rejects.toMatchObject({ name: 'AbortError' }));
    await flushPromises();
    controllers[0].abort();
    expect(state.signals[0].aborted).toBe(false);
    controllers[1].abort();
    expect(state.signals[0].aborted).toBe(true);
    await Promise.all(assertions);
    state.requests[0].reject(new Error('Late failure'));
    await flushPromises();
  });

  it('observes a rejection when the API aborts the subscriber synchronously during invocation', async () => {
    const state = setup();
    const controller = new AbortController();
    state.api.getContactTimesForEvent.mockImplementationOnce(() => {
      controller.abort();
      return Promise.reject(new Error('Failure after synchronous cancellation'));
    });
    const assertion = expect(state.fetchContactTimesForEvent(date, true, controller.signal))
      .rejects.toMatchObject({ name: 'AbortError' });
    await assertion;
    await flushPromises();
    expect(state.events.value[0].contact_times).toBeNull();
  });

  it('does not apply an old result to new search results or abort on a new search', async () => {
    const state = setup();
    const old = state.fetchContactTimesForEvent(date, true);
    await flushPromises();
    state.api.getAstronomicalEvents.mockResolvedValue({
      events: [eclipse()], pagination: null,
    });
    await state.fetchEvents({ start_date: '2025-01-01', end_date: '2025-12-31' });
    expect(state.signals[0].aborted).toBe(false);
    state.requests[0].resolve(response);
    await old;
    expect(state.events.value[0].contact_times).toBeNull();
  });

  it('separates locales and ignores old locale results without aborting them', async () => {
    const previous = getCurrentLocale();
    const next = previous === 'en-US' ? 'en-UK' : 'en-US';
    const state = setup();
    try {
      const old = state.fetchContactTimesForEvent(date, true);
      await flushPromises();
      setCurrentLocale(next);
      state.api.getAstronomicalEvents.mockResolvedValue({
        events: [eclipse()], pagination: null,
      });

      await state.fetchEvents({ start_date: '2025-01-01', end_date: '2025-12-31' });
      const current = state.fetchContactTimesForEvent(date, true);
      await flushPromises();
      expect(state.api.getContactTimesForEvent).toHaveBeenCalledTimes(2);
      expect(state.signals[0].aborted).toBe(false);
      state.requests[0].resolve(response);
      await old;
      expect(state.events.value[0].contact_times).toBeNull();
      state.requests[1].resolve({ contact_times: { p1: 'new locale' } });
      await current;
      expect(state.events.value[0].contact_times).toEqual({ p1: 'new locale' });
    } finally {
      setCurrentLocale(previous);
    }
  });

  it('uses the deduplication locale when invoking the API even if locale changes in the same turn', async () => {
    const previous = getCurrentLocale();
    const next = previous === 'en-US' ? 'en-UK' : 'en-US';
    const state = setup();
    const requestedLocales: string[] = [];
    state.api.getContactTimesForEvent.mockImplementation(() => {
      requestedLocales.push(getCurrentLocale());
      return Promise.resolve(response);
    });
    try {
      const old = state.fetchContactTimesForEvent(date, true);
      setCurrentLocale(next);
      const current = state.fetchContactTimesForEvent(date, true);
      await Promise.all([old, current]);
      expect(requestedLocales).toEqual([previous, next]);
    } finally {
      setCurrentLocale(previous);
    }
  });

  it('releases failed shared requests and preserves 503 errors for all subscribers', async () => {
    const state = setup();
    const first = state.fetchContactTimesForEvent(date, true);
    const second = state.fetchContactTimesForEvent(date, true, new AbortController().signal);
    const failure = new ApiError(503, 'Unavailable', 'Unavailable');
    const assertions = [expect(first).rejects.toBe(failure), expect(second).rejects.toBe(failure)];
    await flushPromises();
    state.requests[0].reject(failure);
    await Promise.all(assertions);
    const retry = state.fetchContactTimesForEvent(date, true);
    await flushPromises();
    expect(state.requests).toHaveLength(2);
    state.requests[1].resolve(response);
    await retry;
  });
});

describe('queue cancellation races', () => {
  it.each([false, true])('observes a rejecting promise returned after synchronous abort (retry: %s)', async (retry) => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const onProgress = vi.fn();
    const fetchFn = vi.fn();
    if (retry) fetchFn.mockRejectedValueOnce(new ApiError(429, 'Rate limit', '{"retry_after": 1}'));
    fetchFn.mockImplementationOnce((_date, _isLunar, signal) => {
      expect(signal).toBe(controller.signal);
      controller.abort();
      return Promise.reject(new Error('Synchronous abort followed by rejection'));
    });
    const queue = fetchContactTimesInQueue([{ date, is_lunar: true }], fetchFn, onProgress, controller.signal);
    await vi.runAllTimersAsync();
    await expect(queue).resolves.toEqual([]);
    expect(fetchFn).toHaveBeenCalledTimes(retry ? 2 : 1);
    expect(onProgress).not.toHaveBeenCalled();
    expect(vi.getTimerCount()).toBe(0);
  });

  it('returns partial results and observes late rejection without progress or more work', async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const pending = deferred<void>();
    const fetchFn = vi.fn().mockResolvedValueOnce(undefined).mockReturnValueOnce(pending.promise);
    const onProgress = vi.fn();
    const queue = fetchContactTimesInQueue([
      { date: 'first', is_lunar: true }, { date: 'second', is_lunar: true }, { date: 'third', is_lunar: true },
    ], fetchFn, onProgress, controller.signal);
    await vi.advanceTimersByTimeAsync(2500);
    expect(fetchFn).toHaveBeenLastCalledWith('second', true, controller.signal);
    controller.abort();
    await expect(queue).resolves.toEqual([{ success: true, date: 'first' }]);
    pending.reject(new ApiError(429, 'Rate limit', '{"retry_after": 1}'));
    await vi.runAllTimersAsync();
    expect(fetchFn).toHaveBeenCalledTimes(2);
    expect(onProgress).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('does not retry 503 failures and continues pacing subsequent work', async () => {
    vi.useFakeTimers();
    const failure = new ApiError(503, 'Unavailable', 'Contact time capacity exhausted');
    const fetchFn = vi.fn().mockRejectedValueOnce(failure).mockResolvedValueOnce(undefined);
    const queue = fetchContactTimesInQueue([
      { date: 'first', is_lunar: true }, { date: 'second', is_lunar: true },
    ], fetchFn);
    await vi.advanceTimersByTimeAsync(2499);
    expect(fetchFn).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    await expect(queue).resolves.toEqual([
      { success: false, date: 'first', error: failure },
      { success: true, date: 'second' },
    ]);
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it('does not report progress if cancellation occurs before a resolved request resumes', async () => {
    const controller = new AbortController();
    const task = deferred<void>();
    const onProgress = vi.fn();
    const queue = fetchContactTimesInQueue([{ date, is_lunar: true }], () => task.promise, onProgress, controller.signal);
    task.resolve();
    controller.abort();
    await expect(queue).resolves.toEqual([]);
    expect(onProgress).not.toHaveBeenCalled();
  });
});
