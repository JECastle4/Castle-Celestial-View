/**
 * Celestial Bodies Configuration
 * Defines the manifest of observable celestial bodies with display metadata
 */

export interface CelestialBodyConfig {
  id: string;
  name: string;
  order: number;
  hasPhase: boolean;
  hasIllumination: boolean;
  hasNakedEyeVisibility: boolean;
  icon: string;
}

export const CELESTIAL_BODIES: CelestialBodyConfig[] = [
  {
    id: 'sun',
    name: 'Sun',
    order: 0,
    hasPhase: false,
    hasIllumination: false,
    hasNakedEyeVisibility: false,
    icon: 'fa-sun'
  },
  {
    id: 'moon',
    name: 'Moon',
    order: 1,
    hasPhase: true,
    hasIllumination: true,
    hasNakedEyeVisibility: false,
    icon: 'fa-moon'
  },
  {
    id: 'venus',
    name: 'Venus',
    order: 2,
    hasPhase: true,
    hasIllumination: true,
    hasNakedEyeVisibility: true,
    icon: 'fa-star'
  }
];

export const getBodyConfig = (bodyId: string): CelestialBodyConfig | undefined => {
  return CELESTIAL_BODIES.find(body => body.id === bodyId);
};

export const getBodyById = (bodyId: string): CelestialBodyConfig | undefined => {
  return CELESTIAL_BODIES.find(body => body.id === bodyId);
};
