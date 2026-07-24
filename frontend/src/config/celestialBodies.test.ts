import { describe, it, expect } from 'vitest';
import { CELESTIAL_BODIES, getBodyConfig, getBodyById } from './celestialBodies';

describe('celestialBodies', () => {
  describe('CELESTIAL_BODIES array', () => {
    it('should have 6 celestial bodies', () => {
      expect(CELESTIAL_BODIES).toHaveLength(6);
    });

    it('should have sun as first body', () => {
      expect(CELESTIAL_BODIES[0].id).toBe('sun');
      expect(CELESTIAL_BODIES[0].order).toBe(0);
      expect(CELESTIAL_BODIES[0].hasPhase).toBe(false);
    });

    it('should have mercury as second body', () => {
      expect(CELESTIAL_BODIES[1].id).toBe('mercury');
      expect(CELESTIAL_BODIES[1].order).toBe(1);
      expect(CELESTIAL_BODIES[1].hasPhase).toBe(true);
    });

    it('should have venus as third body', () => {
      expect(CELESTIAL_BODIES[2].id).toBe('venus');
      expect(CELESTIAL_BODIES[2].order).toBe(2);
      expect(CELESTIAL_BODIES[2].hasPhase).toBe(true);
    });

    it('should have earth as fourth body (disabled)', () => {
      expect(CELESTIAL_BODIES[3].id).toBe('earth');
      expect(CELESTIAL_BODIES[3].order).toBe(3);
      expect(CELESTIAL_BODIES[3].enabled).toBe(false);
    });
  });

  describe('getBodyConfig', () => {
    it('should return sun config when given "sun"', () => {
      const config = getBodyConfig('sun');
      expect(config).toBeDefined();
      expect(config?.id).toBe('sun');
      expect(config?.name).toBe('Sun');
      expect(config?.hasPhase).toBe(false);
    });

    it('should return moon config when given "moon"', () => {
      const config = getBodyConfig('moon');
      expect(config).toBeDefined();
      expect(config?.id).toBe('moon');
      expect(config?.name).toBe('Moon');
      expect(config?.hasPhase).toBe(true);
      expect(config?.hasIllumination).toBe(true);
    });

    it('should return venus config when given "venus"', () => {
      const config = getBodyConfig('venus');
      expect(config).toBeDefined();
      expect(config?.id).toBe('venus');
      expect(config?.name).toBe('Venus');
      expect(config?.hasPhase).toBe(true);
      expect(config?.hasNakedEyeVisibility).toBe(true);
    });

    it('should return mercury config when given "mercury"', () => {
      const config = getBodyConfig('mercury');
      expect(config).toBeDefined();
      expect(config?.id).toBe('mercury');
      expect(config?.name).toBe('Mercury');
      expect(config?.hasPhase).toBe(true);
      expect(config?.hasNakedEyeVisibility).toBe(true);
    });

    it('should return undefined for invalid body id', () => {
      const config = getBodyConfig('invalid');
      expect(config).toBeUndefined();
    });
  });

  describe('getBodyById', () => {
    it('should return sun config when given "sun"', () => {
      const config = getBodyById('sun');
      expect(config).toBeDefined();
      expect(config?.id).toBe('sun');
    });

    it('should return moon config when given "moon"', () => {
      const config = getBodyById('moon');
      expect(config).toBeDefined();
      expect(config?.id).toBe('moon');
    });

    it('should return venus config when given "venus"', () => {
      const config = getBodyById('venus');
      expect(config).toBeDefined();
      expect(config?.id).toBe('venus');
    });

    it('should return undefined for invalid body id', () => {
      const config = getBodyById('invalid');
      expect(config).toBeUndefined();
    });
  });
});
