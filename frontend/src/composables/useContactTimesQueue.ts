/**
 * Composable for processing eclipse contact time requests sequentially
 * with rate limiting and automatic retry on 429 errors
 */

import { ApiError } from '@/services/api';

export interface QueueResult {
  success: boolean;
  date: string;
  error?: Error;
}

function runWithAbort<T>(
  task: Promise<T>,
  signal?: AbortSignal
): Promise<{ aborted: true } | { aborted: false; value: T }> {
  if (!signal) {
    return task.then((value) => ({ aborted: false, value }));
  }
  if (signal.aborted) {
    return Promise.resolve({ aborted: true });
  }

  return new Promise((resolve, reject) => {
    const onAbort = () => {
      signal.removeEventListener('abort', onAbort);
      resolve({ aborted: true });
    };
    signal.addEventListener('abort', onAbort, { once: true });
    task.then(
      (value) => resolve({ aborted: false, value }),
      reject
    ).finally(() => signal.removeEventListener('abort', onAbort));
  });
}

function waitForDelay(delayMs: number, signal?: AbortSignal): Promise<boolean> {
  if (signal?.aborted) {
    return Promise.resolve(false);
  }

  return new Promise((resolve) => {
    let timeoutId: ReturnType<typeof setTimeout>;
    const onAbort = () => {
      clearTimeout(timeoutId);
      signal?.removeEventListener('abort', onAbort);
      resolve(false);
    };
    timeoutId = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve(true);
    }, delayMs);
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

/**
 * Process eclipse contact time requests sequentially with rate limiting
 * @param eclipsesToFetch - Array of eclipses to fetch contact times for
 * @param fetchFn - Function to call for each eclipse (should accept date and is_lunar)
 * @param onProgress - Optional callback for progress updates (completed, total)
 * @returns Array of results with success/failure status
 */
export async function fetchContactTimesInQueue(
  eclipsesToFetch: Array<{ date: string; is_lunar: boolean }>,
  fetchFn: (date: string, is_lunar: boolean) => Promise<void>,
  onProgress?: (completed: number, total: number) => void,
  signal?: AbortSignal
): Promise<QueueResult[]> {
  const results: QueueResult[] = [];
  let completed = 0;

  // Process requests sequentially with rate limit awareness
  for (const eclipse of eclipsesToFetch) {
    if (signal?.aborted) {
      break;
    }

    try {
      const attempt = await runWithAbort(fetchFn(eclipse.date, eclipse.is_lunar), signal);
      if (attempt.aborted) {
        break;
      }
      results.push({ success: true, date: eclipse.date });
    } catch (err) {
      if (signal?.aborted) {
        break;
      }

      // Check if error is a 429 rate limit error
      if (err instanceof ApiError && err.status === 429) {
        // Extract retry-after value from JSON response body
        let retryAfter = 2000; // Default to 2 seconds
        try {
          const responseBody = JSON.parse(err.message);
          if (responseBody.retry_after && typeof responseBody.retry_after === 'number') {
            retryAfter = responseBody.retry_after * 1000; // Convert seconds to milliseconds
          }
        } catch {
          // If JSON parsing fails, use default retry-after
        }
        
        // Wait before retrying this request
        if (!(await waitForDelay(retryAfter, signal))) {
          break;
        }
        
        try {
          // Retry once
          const retry = await runWithAbort(fetchFn(eclipse.date, eclipse.is_lunar), signal);
          if (retry.aborted) {
            break;
          }
          results.push({ success: true, date: eclipse.date });
        } catch (retryErr) {
          if (signal?.aborted) {
            break;
          }
          results.push({ 
            success: false, 
            date: eclipse.date, 
            error: retryErr instanceof Error ? retryErr : new Error(String(retryErr)) 
          });
        }
      } else {
        results.push({ 
          success: false, 
          date: eclipse.date, 
          error: err instanceof Error ? err : new Error(String(err)) 
        });
      }
    }
    
    completed++;
    onProgress?.(completed, eclipsesToFetch.length);
    
    // Pace requests to stay within server limit: LIMIT_CONTACT_TIMES default is 30/min,
    // so 2000ms between requests = 30 req/min (at limit). Using 2500ms for safe headroom.
    if (completed < eclipsesToFetch.length) {
      if (!(await waitForDelay(2500, signal))) {
        break;
      }
    }
  }

  return results;
}
