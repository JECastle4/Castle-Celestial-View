import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { astronomyApi, ApiError } from '@/services/api';
import type { AstronomyApi, BatchObservationsParams } from '@/services/api';
import { API_CONFIG } from '@/services/config';
import type { BatchEarthObservationsResponse, ObservationFrame } from '@/types/api.types';
import type { ActiveToast } from 'vue-toast-notification';
import { useToast } from './useToast';

/**
 * Composable for fetching and managing astronomy data
 */
export function useAstronomyData(api: AstronomyApi = astronomyApi) {
  const { t, tc } = useI18n();
  const data = ref<BatchEarthObservationsResponse | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const toast = useToast();

  const hasData = computed(() => data.value !== null);
  const frameCount = computed(() => data.value?.metadata.frame_count ?? 0);

  const sseFrames = ref<ObservationFrame[]>([]);
  const sseExpectedFrameCount = ref<number>(0);
  const sseProgress = computed(() => {
    if (sseExpectedFrameCount.value === 0) return 0;
    return sseFrames.value.length / sseExpectedFrameCount.value;
  });

  let currentEventSource: EventSource | null = null;
  let activeSuccessToast: ActiveToast | null = null;

  /**
   * Fetch batch earth observations via SSE
   */
  async function fetchBatchObservationsSSE(params: BatchObservationsParams) {
    dismissSuccessToast();
    loading.value = true;
    error.value = null;
    data.value = null;
    sseFrames.value = [];
    sseExpectedFrameCount.value = params.frame_count;
    let metadata: any = null;

    return new Promise<void>((resolve, reject) => {
      // Build query string for GET request
      const paramsObj = {
        start_date: params.start_date,
        start_time: params.start_time,
        end_date: params.end_date,
        end_time: params.end_time,
        frame_count: params.frame_count,
        latitude: params.latitude,
        longitude: params.longitude,
        elevation: params.elevation ?? 0.0,
      };
      const query = new URLSearchParams(paramsObj as any).toString();
      const url = `${API_CONFIG.baseUrl}/api/v1/batch-earth-observations-stream?${query}`;
      const eventSource = new EventSource(url);
      currentEventSource = eventSource;

      eventSource.onopen = null; // Remove POST fetch logic, not needed for GET

      eventSource.addEventListener('frame', (event: MessageEvent) => {
        const frame = JSON.parse(event.data);
        sseFrames.value = [...sseFrames.value, frame];
        checkCompletion();
      });

      eventSource.addEventListener('metadata', (event: MessageEvent) => {
        metadata = JSON.parse(event.data);
        sseExpectedFrameCount.value = metadata.frame_count;
        checkCompletion();
      });

      eventSource.onerror = (_event) => {
        error.value = t('errors.sseConnectionError');
        loading.value = false;
        eventSource.close();
        currentEventSource = null;
        const errorMsg = `${t('errors.loadingFailed')}: ${t('errors.connectionError')}`;
        toast.error(errorMsg);
        reject(new Error('SSE connection error'));
      };

      let completed = false;

      function checkCompletion() {
        if (completed) return;
        if (metadata && sseFrames.value.length === sseExpectedFrameCount.value) {
          completed = true;
          data.value = { frames: sseFrames.value, metadata };
          loading.value = false;
          eventSource.close();
          currentEventSource = null;
          const successMsg = tc('success.loaded', sseExpectedFrameCount.value, { count: sseExpectedFrameCount.value });
          activeSuccessToast = toast.success(successMsg);
          // Delay resolve to allow toast to display before scene transition (300ms)
          setTimeout(resolve, 300);
        }
      }
    });
  }

  function dismissSuccessToast() {
    activeSuccessToast?.dismiss();
    activeSuccessToast = null;
  }

  function cancelSSE() {
    dismissSuccessToast();
    if (currentEventSource) {
      currentEventSource.close();
      currentEventSource = null;
      loading.value = false;
      error.value = t('errors.cancelled');
    }
  }

  async function fetchBatchObservations(params: BatchObservationsParams) {
    dismissSuccessToast();
    loading.value = true;
    error.value = null;

    try {
      const response = await api.getBatchEarthObservations(params);
      data.value = response;
      const successMsg = tc('success.loaded', response.metadata.frame_count, { count: response.metadata.frame_count });
      toast.success(successMsg);
    } catch (err) {
      if (err instanceof ApiError) {
        error.value = `${t('errors.apiError', { status: err.status })}: ${err.message}`;
        toast.error(error.value);
      } else if (err instanceof Error) {
        error.value = err.message;
        const errorMsg = `${t('errors.loadingFailed')}: ${error.value}`;
        toast.error(errorMsg);
      } else {
        error.value = t('errors.unknown');
        toast.error(error.value);
      }
    } finally {
      loading.value = false;
    }
  }

  function clearData() {
    dismissSuccessToast();
    data.value = null;
    error.value = null;
  }

  return {
    data,
    loading,
    error,
    hasData,
    frameCount,
    fetchBatchObservations,
    fetchBatchObservationsSSE,
    cancelSSE,
    clearData,
    dismissSuccessToast,
    sseFrames,
    sseExpectedFrameCount,
    sseProgress,
  };
}
