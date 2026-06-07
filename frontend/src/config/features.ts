/**
 * Feature flags for celestial bodies Three.js rendering
 * These flags control whether 3D scene objects are created/updated in the visualizer.
 * The UI carousel and info panels always expose all celestial bodies regardless of flags.
 * Flags are primarily useful for testing and debugging scene performance.
 */

export const FEATURE_FLAGS = {
  // Celestial body visibility flags
  SUN_ENABLED: true,
  MOON_ENABLED: true,
  VENUS_ENABLED: true,
};
