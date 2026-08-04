import { describe, it, expect, vi } from 'vitest';
import { useAstronomicalEvents } from '@/composables/useAstronomicalEvents';
import { ApiError } from '@/services/api';
import type { AstronomicalEventsResponse } from '@/types/api.types';

const mockResponse: AstronomicalEventsResponse = {
  events: [
    {
      event_type: 'Full Moon',
      date: '2025-09-07 18:11:42.600',
      julian_date: 2460925.257,
      moon_ecl_lat_deg: -0.1,
      eclipse_occurs: true,
      eclipse_type: 'Total',
      greatest_eclipse_time: '2025-09-07 18:11:42.600',
      umbral_magnitude: 1.36,
      penumbral_magnitude: 2.4,
      size_ratio: null,
      contact_times: {
        p1: '2025-09-07 15:29:50.911',
        u1: '2025-09-07 16:26:57.000',
        u2: '2025-09-07 17:30:41.000',
        u3: '2025-09-07 18:52:43.000',
        u4: '2025-09-07 19:56:27.000',
        p4: '2025-09-07 20:53:34.000',
      },
    },
  ],
  pagination: {
    page: 1,
    page_size: 10,
    total_events: 1,
    total_pages: 1,
  },
};

describe('useAstronomicalEvents', () => {
  it('starts with empty state', () => {
    const { events, pagination, loading, error, hasSearched } = useAstronomicalEvents();
    expect(events.value).toEqual([]);
    expect(pagination.value).toBeNull();
    expect(loading.value).toBe(false);
    expect(error.value).toBeNull();
    expect(hasSearched.value).toBe(false);
  });

  it('fetches events successfully', async () => {
    const mockApi = { getBatchEarthObservations: vi.fn(), getAstronomicalEvents: vi.fn().mockResolvedValueOnce(mockResponse) };
    const { events, pagination, loading, error, hasSearched, fetchEvents } = useAstronomicalEvents(mockApi);

    await fetchEvents({ start_date: '2025-01-01', end_date: '2025-12-31' });

    expect(loading.value).toBe(false);
    expect(error.value).toBeNull();
    expect(events.value).toEqual(mockResponse.events);
    expect(pagination.value).toEqual(mockResponse.pagination);
    expect(hasSearched.value).toBe(true);
    expect(mockApi.getAstronomicalEvents).toHaveBeenCalledWith({ start_date: '2025-01-01', end_date: '2025-12-31' });
  });

  it('handles ApiError correctly', async () => {
    const apiError = new ApiError(422, 'Unprocessable Entity', 'Invalid date range');
    const mockApi = { getBatchEarthObservations: vi.fn(), getAstronomicalEvents: vi.fn().mockRejectedValueOnce(apiError) };
    const { events, pagination, error, fetchEvents } = useAstronomicalEvents(mockApi);

    await fetchEvents({ start_date: '2025-12-31', end_date: '2025-01-01' });

    expect(error.value).toBe('Invalid date range');
    expect(events.value).toEqual([]);
    expect(pagination.value).toBeNull();
  });

  it('handles generic Error correctly', async () => {
    const mockApi = { getBatchEarthObservations: vi.fn(), getAstronomicalEvents: vi.fn().mockRejectedValueOnce(new Error('Network failure')) };
    const { error, fetchEvents } = useAstronomicalEvents(mockApi);

    await fetchEvents({ start_date: '2025-01-01', end_date: '2025-12-31' });

    expect(error.value).toBe('Network failure');
  });

  it('handles unknown error type', async () => {
    const mockApi = { getBatchEarthObservations: vi.fn(), getAstronomicalEvents: vi.fn().mockRejectedValueOnce('string error') };
    const { error, fetchEvents } = useAstronomicalEvents(mockApi);

    await fetchEvents({ start_date: '2025-01-01', end_date: '2025-12-31' });

    expect(error.value).toBe('An unknown error occurred');
  });
});

describe('useAstronomicalEvents SSE', () => {
  function installMockEventSource() {
    let pageListener: ((event: any) => void) | undefined;
    let metadataListener: ((event: any) => void) | undefined;
    let instance: any = null;
    let lastUrl = '';
    const close = vi.fn();
    const origEventSource = globalThis.EventSource;
    class MockEventSource {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSED = 2;
      close = close;
      onerror: ((event: any) => void) | null = null;
      addEventListener = (type: string, cb: (event: any) => void) => {
        if (type === 'page') pageListener = cb;
        if (type === 'metadata') metadataListener = cb;
      };
      constructor(url: string) {
        instance = this;
        lastUrl = url;
      }
    }
    globalThis.EventSource = MockEventSource as unknown as typeof EventSource;
    return {
      restore: () => { globalThis.EventSource = origEventSource; },
      emitPage: (events: unknown[]) => pageListener?.({ data: JSON.stringify({ page: 1, events }) }),
      emitMetadata: (metadata: unknown) => metadataListener?.({ data: JSON.stringify(metadata) }),
      emitError: () => instance?.onerror?.({}),
      getUrl: () => lastUrl,
      close,
    };
  }

  const eventA = { event_type: 'New Moon', date: '2025-01-01 00:00:00.000', julian_date: 1, moon_ecl_lat_deg: 1, eclipse_occurs: false, eclipse_type: 'No Eclipse', greatest_eclipse_time: null, umbral_magnitude: null, penumbral_magnitude: null, size_ratio: null, contact_times: null };
  const eventB = { ...eventA, date: '2025-02-01 00:00:00.000' };

  it('collects events across pages and resolves on metadata', async () => {
    const mock = installMockEventSource();
    const { events, pagination, loading, error, hasSearched, sseEventCount, fetchEventsSSE } = useAstronomicalEvents();

    const promise = fetchEventsSSE({ start_date: '2025-01-01', end_date: '2025-12-31', page_size: 1 });
    expect(loading.value).toBe(true);

    mock.emitPage([eventA]);
    expect(sseEventCount.value).toBe(1);
    mock.emitPage([eventB]);
    expect(sseEventCount.value).toBe(2);
    mock.emitMetadata({ page_size: 1, total_events: 2, total_pages: 2 });

    await promise;

    expect(loading.value).toBe(false);
    expect(error.value).toBeNull();
    expect(hasSearched.value).toBe(true);
    expect(events.value).toEqual([eventA]);
    expect(pagination.value).toEqual({ page: 1, page_size: 1, total_events: 2, total_pages: 2 });
    expect(mock.close).toHaveBeenCalled();

    mock.restore();
  });

  it('goToPage slices the collected SSE results client-side without a new request', async () => {
    const mock = installMockEventSource();
    const { events, pagination, fetchEventsSSE, goToPage } = useAstronomicalEvents();

    const promise = fetchEventsSSE({ start_date: '2025-01-01', end_date: '2025-12-31', page_size: 1 });
    mock.emitPage([eventA]);
    mock.emitPage([eventB]);
    mock.emitMetadata({ page_size: 1, total_events: 2, total_pages: 2 });
    await promise;

    goToPage(2);

    expect(events.value).toEqual([eventB]);
    expect(pagination.value?.page).toBe(2);

    mock.restore();
  });

  it('handles SSE connection errors', async () => {
    const mock = installMockEventSource();
    const { error, loading, fetchEventsSSE } = useAstronomicalEvents();

    const promise = fetchEventsSSE({ start_date: '2025-01-01', end_date: '2025-12-31' });
    await Promise.resolve();
    mock.emitError();

    await expect(promise).rejects.toThrow('SSE connection error');
    expect(error.value).toBe('SSE connection error');
    expect(loading.value).toBe(false);

    mock.restore();
  });

  it('cancelSSE closes the stream and sets the cancelled error', async () => {
    const mock = installMockEventSource();
    const { error, loading, fetchEventsSSE, cancelSSE } = useAstronomicalEvents();

    fetchEventsSSE({ start_date: '2025-01-01', end_date: '2025-12-31' });
    cancelSSE();

    expect(error.value).toBe('Loading cancelled by user.');
    expect(loading.value).toBe(false);
    expect(mock.close).toHaveBeenCalled();

    mock.restore();
  });

  it('cancelSSE is a no-op when nothing is in flight', () => {
    const { error, loading, cancelSSE } = useAstronomicalEvents();
    cancelSSE();
    expect(error.value).toBeNull();
    expect(loading.value).toBe(false);
  });

  it('goToPage is a no-op before any search has completed', () => {
    const { events, pagination, goToPage } = useAstronomicalEvents();
    goToPage(2);
    expect(events.value).toEqual([]);
    expect(pagination.value).toBeNull();
  });

  it('includes include_contact_times and event_types in the SSE request URL', async () => {
    const mock = installMockEventSource();
    const { fetchEventsSSE } = useAstronomicalEvents();

    const promise = fetchEventsSSE({
      start_date: '2025-01-01',
      end_date: '2025-12-31',
      include_contact_times: false,
      event_types: ['new_moon', 'full_moon'],
    });
    mock.emitMetadata({ page_size: 10, total_events: 0, total_pages: 1 });
    await promise;

    const url = mock.getUrl();
    expect(url).toContain('include_contact_times=false');
    expect(url).toContain('event_types=new_moon');
    expect(url).toContain('event_types=full_moon');

    mock.restore();
  });
});
