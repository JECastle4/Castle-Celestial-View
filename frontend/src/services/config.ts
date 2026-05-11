import type { ApiConfig } from '@/types/api.types';

/**
 * API Configuration
 * Uses environment variables for different deployment environments.
 *
 * In development and preview mode the Vite proxy forwards /api/* to the backend,
 * so baseUrl should be '' (relative paths). Set VITE_API_BASE_URL only when the
 * API is hosted on a different origin (e.g. production deployments).
 */
const baseUrl = import.meta.env.VITE_API_BASE_URL || '';

// Validate configuration in production mode
if (!import.meta.env.DEV) {
  if (!import.meta.env.VITE_API_BASE_URL) {
    console.warn(
      '⚠️ PRODUCTION WARNING: VITE_API_BASE_URL not set. Using relative paths via proxy. ' +
      'Set VITE_API_BASE_URL in .env.production for deployments where the API is on a different origin.'
    );
  }
  if (baseUrl.startsWith('http://')) {
    console.warn(
      '⚠️ SECURITY WARNING: API base URL uses insecure http protocol in production! ' +
      `Current URL: ${baseUrl}. Use https for production deployments.`
    );
  }
}

export const API_CONFIG: ApiConfig = {
  baseUrl,
  timeout: 30000,
};

// API Endpoints
export const API_ENDPOINTS = {
  batchEarthObservations: '/api/v1/batch-earth-observations',
  sunPosition: '/api/v1/sun-position',
  moonPosition: '/api/v1/moon-position',
  moonPhase: '/api/v1/moon-phase',
} as const;
