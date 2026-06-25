import * as THREE from 'three';

/**
 * Camera preset configuration for 3D celestial body views
 * Each preset defines a frame that optimally shows the celestial body
 */

export interface CameraPreset {
  name: string;
  position: THREE.Vector3;
  target: THREE.Vector3;
  fov?: number; // optional; uses default if not specified
}

export const CAMERA_PRESETS: Record<string, CameraPreset> = {
  // Default view: framed to show all planets (calculated at runtime)
  default: {
    name: 'Default View',
    position: new THREE.Vector3(0, 12, 20),
    target: new THREE.Vector3(0, 0, 0),
  },

  // Single celestial body views
  earth: {
    name: 'Earth',
    position: new THREE.Vector3(0, 5, 12),
    target: new THREE.Vector3(0, 0, 0),
  },

  moon: {
    name: 'Moon',
    position: new THREE.Vector3(0, 5, 10),
    target: new THREE.Vector3(0, 0, 0),
  },

  mercury: {
    name: 'Mercury',
    position: new THREE.Vector3(0, 5, 14),
    target: new THREE.Vector3(12.3, 0, 0),
  },

  venus: {
    name: 'Venus',
    position: new THREE.Vector3(0, 5, 18),
    target: new THREE.Vector3(16.8, 0, 0),
  },

  sun: {
    name: 'Sun',
    position: new THREE.Vector3(0, 6, 22),
    target: new THREE.Vector3(19.7, 0, 0),
  },

  mars: {
    name: 'Mars',
    position: new THREE.Vector3(0, 5, 20),
    target: new THREE.Vector3(25.4, 0, 0),
  },

  // Special case: Earth and Moon subsystem view
  earthmoon: {
    name: 'Earth/Moon Subsystem',
    position: new THREE.Vector3(0, 4, 12),
    target: new THREE.Vector3(2, 0, 4), // midpoint between Earth and Moon with slight offset
  },
};

/**
 * Get a camera preset by name
 * @param presetName - The name of the preset (e.g., 'sun', 'mars')
 * @returns The camera preset, or default if not found
 */
export function getPreset(presetName: string): CameraPreset {
  const preset = CAMERA_PRESETS[presetName.toLowerCase()];
  return preset || CAMERA_PRESETS.default;
}

/**
 * Calculate an optimal view for the Earth-Moon subsystem
 * Ensures both bodies are clearly visible with appropriate separation and framing
 * @param earthPosition - Earth's position
 * @param moonPosition - Moon's position
 * @returns Camera preset optimized for Earth-Moon system
 */
export function calculateOptimalEarthMoonView(
  earthPosition: THREE.Vector3,
  moonPosition: THREE.Vector3
): CameraPreset {
  // Calculate separation between Earth and Moon
  const separation = moonPosition.distanceTo(earthPosition);

  // Calculate center of mass (weighted towards Earth as it's much more massive)
  const center = earthPosition.clone().add(moonPosition.clone().sub(earthPosition).multiplyScalar(0.12));

  // For the Earth-Moon system:
  // - We want enough distance to see both bodies clearly
  // - The Moon orbits at ~3.84 units from Earth
  // - We need ~1.2x the separation for comfortable viewing
  const viewDistance = separation * 1.5;

  // Position camera to view the Earth-Moon system at an angle
  // Slightly elevated and back, similar to viewing from the Sun's perspective
  const cameraPosition = new THREE.Vector3(
    center.x - viewDistance * 0.3, // slight horizontal offset
    center.y + viewDistance * 0.4, // elevated view
    center.z - viewDistance * 0.9 // primary distance back
  );

  return {
    name: 'Earth/Moon Subsystem',
    position: cameraPosition,
    target: center,
  };
}

/**
 * Calculate an optimal default view that frames all celestial bodies
 * @param bodies - Array of mesh objects with position and geometry
 * @returns Camera preset for optimal framing
 */
export function calculateOptimalDefaultView(
  bodyPositions: THREE.Vector3[]
): CameraPreset {
  if (bodyPositions.length === 0) {
    return CAMERA_PRESETS.default;
  }

  // Calculate bounding sphere of all bodies
  const center = new THREE.Vector3();
  bodyPositions.forEach((pos) => center.add(pos));
  center.divideScalar(bodyPositions.length);

  // Find the furthest body from center
  let maxDistance = 0;
  bodyPositions.forEach((pos) => {
    const distance = pos.distanceTo(center);
    maxDistance = Math.max(maxDistance, distance);
  });

  // Add body radii (approximate sum of all radii: 4.0 + 0.3 + 0.1 + 0.275 + 0.115 + 0.15 ≈ 5)
  const radiusBuffer = 5;
  const boundingSphereRadius = maxDistance + radiusBuffer;

  // Calculate camera distance using FOV formula
  const fov = 75; // degrees
  const fovRad = (fov * Math.PI) / 180;
  const cameraDistance = boundingSphereRadius / Math.tan(fovRad / 2) * 1.2; // 1.2x safety factor

  // Position camera above and behind, looking at center
  const cameraPosition = new THREE.Vector3(
    center.x,
    center.y + 5,
    center.z - cameraDistance
  );

  return {
    name: 'Optimal Default View',
    position: cameraPosition,
    target: center,
  };
}

/**
 * Calculate a dynamic camera view for a specific body at its current position
 * Used by zoom-to buttons to frame bodies correctly even when they've moved
 * @param bodyPosition - Current 3D position of the body
 * @param bodyName - Name of the body (sun, mars, earth, etc.)
 * @returns Camera preset optimized for viewing this body at its current location
 */
export function calculateBodyViewPreset(
  bodyPosition: THREE.Vector3,
  bodyName: string
): CameraPreset {
  // Define view distances for each body type
  const viewDistances: Record<string, number> = {
    sun: 25,
    mars: 22,
    mercury: 16,
    venus: 20,
    earth: 12,
    moon: 11,
  };

  const bodyNameLower = bodyName.toLowerCase();
  const viewDistance = viewDistances[bodyNameLower] || 15; // Default view distance

  // Position camera slightly elevated and back from the body
  // This provides a good viewing angle similar to the static presets
  const cameraPosition = new THREE.Vector3(
    bodyPosition.x,
    bodyPosition.y + viewDistance * 0.3, // Slight elevation
    bodyPosition.z - viewDistance * 0.85 // Primary distance back
  );

  // Capitalize first letter of body name for display
  const capitalizedName = bodyName.charAt(0).toUpperCase() + bodyName.slice(1);

  return {
    name: `${capitalizedName} View (Dynamic)`,
    position: cameraPosition,
    target: bodyPosition.clone(),
  };
}
