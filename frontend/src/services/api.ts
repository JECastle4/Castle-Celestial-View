import { API_CONFIG, API_ENDPOINTS } from './config';
export { API_CONFIG };
import type { AstronomicalEventsResponse, BatchEarthObservationsResponse, EclipseContactTimesResponse } from '@/types/api.types';
import { getCurrentLocale } from '@/i18n';

/**
 * API Client for astronomy data
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export interface BatchObservationsParams {
  latitude: number;
  longitude: number;
  start_date: string;
  start_time: string;
  end_date: string;
  end_time: string;
  frame_count: number;
  elevation?: number;
}

export interface AstronomicalEventsParams {
  start_date: string;
  end_date: string;
  page?: number;
  page_size?: number;
  include_contact_times?: boolean;
  event_types?: ('new_moon' | 'full_moon')[];
}

export class AstronomyApiClient {
  private baseUrl: string;
  private timeout: number;

  constructor() {
    this.baseUrl = API_CONFIG.baseUrl;
    this.timeout = API_CONFIG.timeout;
  }

  /**
   * Fetch batch earth observations for animation
   */
  async getBatchEarthObservations(
    params: BatchObservationsParams
  ): Promise<BatchEarthObservationsResponse> {
    const url = `${this.baseUrl}${API_ENDPOINTS.batchEarthObservations}?lang=${getCurrentLocale()}`;
    return this.postJson<BatchEarthObservationsResponse>(url, params);
  }

  /**
   * Find new/full moons in a date range and classify any eclipses
   */
  async getAstronomicalEvents(
    params: AstronomicalEventsParams
  ): Promise<AstronomicalEventsResponse> {
    const url = `${this.baseUrl}${API_ENDPOINTS.astronomicalEvents}?lang=${getCurrentLocale()}`;
    return this.postJson<AstronomicalEventsResponse>(url, params);
  }

  /**
   * Fetch contact times for a specific eclipse (lazy-loaded on demand)
   * Allows the backend's maximum adaptive timeout for CPU-bound computation.
   */
  async getContactTimesForEvent(
    eventDate: string,
    isLunar: boolean,
    signal?: AbortSignal
  ): Promise<EclipseContactTimesResponse> {
    const url = `${this.baseUrl}${API_ENDPOINTS.contactTimes}?lang=${getCurrentLocale()}`;
    const body = {
      event_date: eventDate,
      is_lunar: isLunar,
    };
    // The backend can grant expensive endpoints a 2x timeout multiplier.
    return this.postJson<EclipseContactTimesResponse>(url, body, 240000, signal);
  }

  private async postJson<T>(url: string, body: unknown, timeoutMs?: number, signal?: AbortSignal): Promise<T> {
    if (signal?.aborted) {
      throw new DOMException('The operation was aborted', 'AbortError');
    }
    const controller = new AbortController();
    const timeout = timeoutMs ?? this.timeout;
    let timedOut = false;
    const timeoutId = setTimeout(() => {
      if (controller.signal.aborted) return;
      timedOut = true;
      controller.abort();
    }, timeout);
    const onAbort = () => controller.abort();
    signal?.addEventListener('abort', onAbort, { once: true });

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new ApiError(
          response.status,
          response.statusText,
          errorText || `API request failed: ${response.statusText}`
        );
      }

      const result = await response.json();
      if (controller.signal.aborted) {
        throw new DOMException('The operation was aborted', 'AbortError');
      }
      return result;
    } catch (error) {
      if (controller.signal.aborted) {
        if (timedOut) throw new Error('Request timeout');
        throw new DOMException('The operation was aborted', 'AbortError');
      }

      if (error instanceof ApiError) {
        throw error;
      }

      if (error instanceof Error) {
        if (error.name === 'AbortError') {
          throw new Error('Request timeout');
        }
        throw new Error(`Network error: ${error.message}`);
      }

      throw new Error('Unknown error occurred');
    } finally {
      clearTimeout(timeoutId);
      signal?.removeEventListener('abort', onAbort);
    }
  }
}

export interface AstronomyApi {
  getBatchEarthObservations(params: BatchObservationsParams): Promise<BatchEarthObservationsResponse>;
  getAstronomicalEvents(params: AstronomicalEventsParams): Promise<AstronomicalEventsResponse>;
  getContactTimesForEvent(eventDate: string, isLunar: boolean, signal?: AbortSignal): Promise<EclipseContactTimesResponse>;
}

// Export singleton instance
export const astronomyApi = new AstronomyApiClient();
