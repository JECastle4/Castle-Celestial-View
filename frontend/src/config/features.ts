/**
 * Feature flags for celestial bodies Three.js rendering
 * Currently only VENUS_ENABLED is wired up to control scene object creation/updates in AstronomyScene.vue.
 * SUN_ENABLED and MOON_ENABLED are not yet implemented; sun and moon objects are always created regardless.
 * The UI carousel and info panels always expose all celestial bodies regardless of flags.
 * Flags are useful for testing, debugging scene performance, and preparation for future toggleable bodies.
 */

export const FEATURE_FLAGS = {
  // Celestial body visibility flags
  SUN_ENABLED: true,
  MOON_ENABLED: true,
  VENUS_ENABLED: true,
  MERCURY_ENABLED: true,
  MARS_ENABLED: true,
};
