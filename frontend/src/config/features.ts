/**
 * Feature flags for celestial bodies visibility
 * Individual flags allow testing different combinations and selective rendering
 */

export const FEATURE_FLAGS = {
  // Celestial body visibility flags
  SUN_ENABLED: true,
  MOON_ENABLED: true,
  VENUS_ENABLED: true,
  
  // Legacy flag for backward compatibility - enabled if Venus is enabled
  VENUS_UI_ENABLED: true,
} as const;
