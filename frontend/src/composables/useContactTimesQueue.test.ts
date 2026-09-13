import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchContactTimesInQueue } from './useContactTimesQueue';
import { ApiError } from '@/services/api';

describe('useContactTimesQueue', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  describe('fetchContactTimesInQueue', () => {
    it('should process successful requests sequentially', async () => {
      const fetchFn = vi.fn().mockResolvedValue(undefined);
      const onProgress = vi.fn();
      const eclipses = [
        { date: '2025-01-01', is_lunar: false },
        { date: '2025-06-01', is_lunar: true },
      ];

      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn, onProgress);
      
      // Simulate time progression through the queue
      await vi.runAllTimersAsync();
      const results = await resultsPromise;

      expect(results).toHaveLength(2);
      expect(results[0]).toEqual({ success: true, date: '2025-01-01' });
      expect(results[1]).toEqual({ success: true, date: '2025-06-01' });
      expect(fetchFn).toHaveBeenCalledTimes(2);
      expect(onProgress).toHaveBeenCalledWith(1, 2);
      expect(onProgress).toHaveBeenCalledWith(2, 2);
    });

    it('should handle 429 rate limit error with retry-after in response', async () => {
      const fetchFn = vi.fn();
      fetchFn.mockRejectedValueOnce(
        new ApiError(429, 'Too Many Requests', '{"retry_after": 3}')
      );
      fetchFn.mockResolvedValueOnce(undefined);

      const eclipses = [{ date: '2025-01-01', is_lunar: false }];
      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);

      await vi.runAllTimersAsync();
      const results = await resultsPromise;

      expect(results[0].success).toBe(true);
      expect(fetchFn).toHaveBeenCalledTimes(2);
    });

    it('should handle 429 rate limit error with default retry-after on JSON parse failure', async () => {
      const fetchFn = vi.fn();
      fetchFn.mockRejectedValueOnce(
        new ApiError(429, 'Too Many Requests', 'invalid json')
      );
      fetchFn.mockResolvedValueOnce(undefined);

      const eclipses = [{ date: '2025-01-01', is_lunar: false }];
      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);

      await vi.runAllTimersAsync();
      const results = await resultsPromise;

      expect(results[0].success).toBe(true);
      expect(fetchFn).toHaveBeenCalledTimes(2);
    });

    it('should handle 429 error with retry_after as non-number', async () => {
      const fetchFn = vi.fn();
      fetchFn.mockRejectedValueOnce(
        new ApiError(429, 'Too Many Requests', '{"retry_after": "not-a-number"}')
      );
      fetchFn.mockResolvedValueOnce(undefined);

      const eclipses = [{ date: '2025-01-01', is_lunar: false }];
      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);

      await vi.runAllTimersAsync();
      const results = await resultsPromise;

      expect(results[0].success).toBe(true);
    });

    it('should record failure after failed retry on 429', async () => {
      const fetchFn = vi.fn();
      fetchFn.mockRejectedValueOnce(
        new ApiError(429, 'Too Many Requests', '{"retry_after": 1}')
      );
      fetchFn.mockRejectedValueOnce(new Error('Still failing'));

      const eclipses = [{ date: '2025-01-01', is_lunar: false }];
      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);

      await vi.runAllTimersAsync();
      const results = await resultsPromise;

      expect(results[0].success).toBe(false);
      expect(results[0].error?.message).toBe('Still failing');
      expect(fetchFn).toHaveBeenCalledTimes(2);
    });

    it('should handle non-429 API errors', async () => {
      const fetchFn = vi.fn();
      fetchFn.mockRejectedValueOnce(
        new ApiError(500, 'Internal Server Error', 'Server error')
      );

      const eclipses = [{ date: '2025-01-01', is_lunar: false }];
      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);

      await vi.runAllTimersAsync();
      const results = await resultsPromise;

      expect(results[0].success).toBe(false);
      expect(results[0].error?.message).toBe('Server error');
      expect(fetchFn).toHaveBeenCalledTimes(1);
    });

    it('should handle non-Error exceptions', async () => {
      const fetchFn = vi.fn();
      fetchFn.mockRejectedValueOnce('string error');

      const eclipses = [{ date: '2025-01-01', is_lunar: false }];
      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);

      await vi.runAllTimersAsync();
      const results = await resultsPromise;

      expect(results[0].success).toBe(false);
      expect(results[0].error?.message).toBe('string error');
    });

    it('should not call onProgress when callback is not provided', async () => {
      const fetchFn = vi.fn().mockResolvedValue(undefined);
      const eclipses = [{ date: '2025-01-01', is_lunar: false }];

      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);
      await vi.runAllTimersAsync();
      await resultsPromise;

      // Should not throw error even without onProgress callback
      expect(fetchFn).toHaveBeenCalledTimes(1);
    });

    it('should pace requests with 2500ms delay between them', async () => {
      const fetchFn = vi.fn().mockResolvedValue(undefined);
      const eclipses = [
        { date: '2025-01-01', is_lunar: false },
        { date: '2025-02-01', is_lunar: false },
      ];

      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);
      
      // Progress through first request
      await vi.advanceTimersByTimeAsync(1);
      expect(fetchFn).toHaveBeenCalledTimes(1);
      
      // Progress through delay between requests
      await vi.advanceTimersByTimeAsync(2500);
      expect(fetchFn).toHaveBeenCalledTimes(2);
      
      // Finish remaining operations
      await vi.runAllTimersAsync();
      const results = await resultsPromise;

      expect(results).toHaveLength(2);
      expect(results.every(r => r.success)).toBe(true);
    });

    it('should not delay after last request', async () => {
      const fetchFn = vi.fn().mockResolvedValue(undefined);
      const delays: number[] = [];
      
      // Track setTimeout calls
      const originalSetTimeout = global.setTimeout;
      vi.spyOn(global, 'setTimeout').mockImplementation((cb, delay) => {
        if (typeof delay === 'number') {
          delays.push(delay);
        }
        return originalSetTimeout(cb, delay) as any;
      });

      const eclipses = [{ date: '2025-01-01', is_lunar: false }];
      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);

      await vi.runAllTimersAsync();
      await resultsPromise;

      // Should only have delays for 429 retries, not for pacing after last request
      const pacingDelays = delays.filter(d => d === 2500);
      expect(pacingDelays).toHaveLength(0);
    });

    it('should handle mixed success and failure results', async () => {
      const fetchFn = vi.fn();
      fetchFn.mockResolvedValueOnce(undefined); // First request succeeds
      fetchFn.mockRejectedValueOnce(new Error('Network error')); // Second request fails
      fetchFn.mockResolvedValueOnce(undefined); // Third request succeeds

      const eclipses = [
        { date: '2025-01-01', is_lunar: false },
        { date: '2025-02-01', is_lunar: false },
        { date: '2025-03-01', is_lunar: false },
      ];

      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);
      await vi.runAllTimersAsync();
      const results = await resultsPromise;

      expect(results).toHaveLength(3);
      expect(results[0].success).toBe(true);
      expect(results[1].success).toBe(false);
      expect(results[2].success).toBe(true);
    });

    it('should call fetchFn with correct date and is_lunar values', async () => {
      const fetchFn = vi.fn().mockResolvedValue(undefined);
      const eclipses = [
        { date: '2025-01-15', is_lunar: true },
        { date: '2025-07-15', is_lunar: false },
      ];

      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn);
      await vi.runAllTimersAsync();
      await resultsPromise;

      expect(fetchFn).toHaveBeenCalledWith('2025-01-15', true);
      expect(fetchFn).toHaveBeenCalledWith('2025-07-15', false);
    });

    it('should handle empty eclipses array', async () => {
      const fetchFn = vi.fn();
      const onProgress = vi.fn();

      const resultsPromise = fetchContactTimesInQueue([], fetchFn, onProgress);
      await vi.runAllTimersAsync();
      const results = await resultsPromise;

      expect(results).toHaveLength(0);
      expect(fetchFn).not.toHaveBeenCalled();
      expect(onProgress).not.toHaveBeenCalled();
    });

    it('should track progress for each completed request', async () => {
      const fetchFn = vi.fn().mockResolvedValue(undefined);
      const progressUpdates: Array<[number, number]> = [];
      const onProgress = vi.fn((completed, total) => {
        progressUpdates.push([completed, total]);
      });

      const eclipses = [
        { date: '2025-01-01', is_lunar: false },
        { date: '2025-02-01', is_lunar: false },
        { date: '2025-03-01', is_lunar: false },
      ];

      const resultsPromise = fetchContactTimesInQueue(eclipses, fetchFn, onProgress);
      await vi.runAllTimersAsync();
      await resultsPromise;

      expect(progressUpdates).toEqual([
        [1, 3],
        [2, 3],
        [3, 3],
      ]);
    });
  });
});
