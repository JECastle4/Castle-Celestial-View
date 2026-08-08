import { ref } from 'vue';
import { i18n, getCurrentLocale } from '@/i18n';
import { astronomyApi, ApiError } from '@/services/api';
import type { AstronomyApi, AstronomicalEventsParams } from '@/services/api';
import { API_CONFIG } from '@/services/config';
import type { AstronomicalEvent, PaginationInfo } from '@/types/api.types';

/**
 * Composable for fetching and managing paginated astronomical events (new/full
 * moons + eclipse classification)
 */
export function useAstronomicalEvents(api: AstronomyApi = astronomyApi) {
  const t = i18n.global.t;
  const events = ref<AstronomicalEvent[]>([]);
  const pagination = ref<PaginationInfo | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const hasSearched = ref(false);
  // Running count of events received so far during an in-progress SSE search
  // (total isn't known until the final metadata event arrives).
  const sseEventCount = ref(0);

  let currentEventSource: EventSource | null = null;
  // Rejects the in-flight fetchEventsSSE() promise; set while a search is
  // running so cancelSSE() can settle it instead of leaving it pending forever.
  let currentSseReject: ((reason: Error) => void) | null = null;
  // Full result set from the last SSE search, kept client-side so page
  // navigation after a search doesn't need another round trip.
  let allSseEvents: AstronomicalEvent[] = [];

  async function fetchEvents(params: AstronomicalEventsParams) {
    loading.value = true;
    error.value = null;

    try {
      const result = await api.getAstronomicalEvents(params);
      events.value = result.events;
      pagination.value = result.pagination;
    } catch (err) {
      events.value = [];
      pagination.value = null;
      if (err instanceof ApiError) {
        error.value = err.message;
      } else if (err instanceof Error) {
        error.value = err.message;
      } else {
        error.value = t('errors.unknown');
      }
    } finally {
      loading.value = false;
      hasSearched.value = true;
    }
  }

  /**
   * Search for events via Server-Sent Events. The backend streams results one
   * page at a time (each page built as it's computed) so callers can show
   * live progress instead of waiting for the whole date range to be searched.
   */
  async function fetchEventsSSE(params: Omit<AstronomicalEventsParams, 'page'>) {
    loading.value = true;
    error.value = null;
    events.value = [];
    pagination.value = null;
    sseEventCount.value = 0;
    allSseEvents = [];
    const pageSize = params.page_size ?? 10;

    return new Promise<void>((resolve, reject) => {
      currentSseReject = reject;
      const query = new URLSearchParams();
      query.set('start_date', params.start_date);
      query.set('end_date', params.end_date);
      query.set('page_size', String(pageSize));
      if (params.include_contact_times !== undefined) {
        query.set('include_contact_times', String(params.include_contact_times));
      }
      (params.event_types ?? []).forEach((eventType) => query.append('event_types', eventType));
      query.set('lang', getCurrentLocale());

      const url = `${API_CONFIG.baseUrl}/api/v1/astronomical-events-stream?${query.toString()}`;
      const eventSource = new EventSource(url);
      currentEventSource = eventSource;

      eventSource.addEventListener('page', (event: MessageEvent) => {
        const pageData = JSON.parse(event.data);
        allSseEvents = [...allSseEvents, ...pageData.events];
        sseEventCount.value = allSseEvents.length;
      });

      eventSource.addEventListener('metadata', (event: MessageEvent) => {
        const metadata = JSON.parse(event.data);
        events.value = allSseEvents.slice(0, pageSize);
        pagination.value = {
          page: 1,
          page_size: pageSize,
          total_events: metadata.total_events,
          total_pages: metadata.total_pages,
        };
        loading.value = false;
        hasSearched.value = true;
        eventSource.close();
        currentEventSource = null;
        currentSseReject = null;
        resolve();
      });

      eventSource.onerror = () => {
        error.value = t('errors.sseConnectionError');
        loading.value = false;
        hasSearched.value = true;
        eventSource.close();
        currentEventSource = null;
        currentSseReject = null;
        reject(new Error('SSE connection error'));
      };
    });
  }

  function cancelSSE() {
    if (currentEventSource) {
      currentEventSource.close();
      currentEventSource = null;
      loading.value = false;
      error.value = t('errors.cancelled');
      currentSseReject?.(new Error('Cancelled by user'));
      currentSseReject = null;
    }
  }

  /** Move to a different page of the last completed SSE search, client-side. */
  function goToPage(page: number) {
    if (!pagination.value) return;
    const { page_size: pageSize } = pagination.value;
    const start = (page - 1) * pageSize;
    events.value = allSseEvents.slice(start, start + pageSize);
    pagination.value = { ...pagination.value, page };
  }

  return {
    events,
    pagination,
    loading,
    error,
    hasSearched,
    fetchEvents,
    fetchEventsSSE,
    cancelSSE,
    goToPage,
    sseEventCount,
  };
}

