import { describe, it, expect } from 'vitest';
import { CAMERA_PRESETS, getPreset, calculateOptimalDefaultView, calculateOptimalEarthMoonView, calculateBodyViewPreset } from './cameraPresets';
import * as THREE from 'three';

describe('cameraPresets', () => {
  describe('CAMERA_PRESETS', () => {
    it('should have 8 presets defined', () => {
      expect(Object.keys(CAMERA_PRESETS)).toHaveLength(8);
    });

    it('should have default preset', () => {
      expect(CAMERA_PRESETS.default).toBeDefined();
      expect(CAMERA_PRESETS.default.name).toBe('Default View');
      expect(CAMERA_PRESETS.default.position).toBeInstanceOf(THREE.Vector3);
      expect(CAMERA_PRESETS.default.target).toBeInstanceOf(THREE.Vector3);
    });

    it('should have earth preset', () => {
      expect(CAMERA_PRESETS.earth).toBeDefined();
      expect(CAMERA_PRESETS.earth.name).toBe('Earth');
      expect(CAMERA_PRESETS.earth.position).toBeInstanceOf(THREE.Vector3);
      expect(CAMERA_PRESETS.earth.target).toBeInstanceOf(THREE.Vector3);
    });

    it('should have moon preset', () => {
      expect(CAMERA_PRESETS.moon).toBeDefined();
      expect(CAMERA_PRESETS.moon.name).toBe('Moon');
      expect(CAMERA_PRESETS.moon.position.z).toBe(10);
    });

    it('should have earthmoon preset for subsystem view', () => {
      expect(CAMERA_PRESETS.earthmoon).toBeDefined();
      expect(CAMERA_PRESETS.earthmoon.name).toBe('Earth/Moon Subsystem');
      expect(CAMERA_PRESETS.earthmoon.position).toBeInstanceOf(THREE.Vector3);
    });

    it('should have mercury preset', () => {
      expect(CAMERA_PRESETS.mercury).toBeDefined();
      expect(CAMERA_PRESETS.mercury.name).toBe('Mercury');
    });

    it('should have venus preset', () => {
      expect(CAMERA_PRESETS.venus).toBeDefined();
      expect(CAMERA_PRESETS.venus.name).toBe('Venus');
    });

    it('should have sun preset', () => {
      expect(CAMERA_PRESETS.sun).toBeDefined();
      expect(CAMERA_PRESETS.sun.name).toBe('Sun');
    });

    it('should have mars preset', () => {
      expect(CAMERA_PRESETS.mars).toBeDefined();
      expect(CAMERA_PRESETS.mars.name).toBe('Mars');
    });
  });

  describe('getPreset', () => {
    it('should return earth preset when given "earth"', () => {
      const preset = getPreset('earth');
      expect(preset).toBe(CAMERA_PRESETS.earth);
      expect(preset.name).toBe('Earth');
    });

    it('should return moon preset when given "moon"', () => {
      const preset = getPreset('moon');
      expect(preset).toBe(CAMERA_PRESETS.moon);
      expect(preset.name).toBe('Moon');
    });

    it('should return default preset when given unknown name', () => {
      const preset = getPreset('unknown' as any);
      expect(preset).toBe(CAMERA_PRESETS.default);
    });

    it('should return preset with correct position coordinates', () => {
      const earthPreset = getPreset('earth');
      expect(earthPreset.position.x).toBe(0);
      expect(earthPreset.position.y).toBe(5);
      expect(earthPreset.position.z).toBe(12);
    });

    it('should return preset with correct target coordinates', () => {
      const earthPreset = getPreset('earth');
      expect(earthPreset.target.x).toBe(0);
      expect(earthPreset.target.y).toBe(0);
      expect(earthPreset.target.z).toBe(0);
    });

    it('should have position and target as Vector3 instances', () => {
      const preset = getPreset('sun');
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toBeInstanceOf(THREE.Vector3);
    });
  });

  describe('calculateOptimalDefaultView', () => {
    it('should return a preset with position and target', () => {
      const positions: THREE.Vector3[] = [
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(10, 0, 0),
        new THREE.Vector3(20, 0, 0),
      ];

      const preset = calculateOptimalDefaultView(positions);
      expect(preset).toBeDefined();
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toBeInstanceOf(THREE.Vector3);
      expect(preset.name).toBe('Optimal Default View');
    });

    it('should position camera to see all bodies', () => {
      const positions: THREE.Vector3[] = [
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(5, 0, 0),
      ];

      const preset = calculateOptimalDefaultView(positions);
      expect(preset.position.length()).toBeGreaterThan(0);
    });

    it('should center target at bounding sphere center', () => {
      const positions: THREE.Vector3[] = [
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(10, 0, 0),
      ];

      const preset = calculateOptimalDefaultView(positions);
      // Target should be somewhere near the center of the bodies
      expect(preset.target.x).toBeGreaterThanOrEqual(0);
      expect(preset.target.x).toBeLessThanOrEqual(10);
    });

    it('should handle empty positions array', () => {
      const positions: THREE.Vector3[] = [];
      const preset = calculateOptimalDefaultView(positions);
      expect(preset).toBeDefined();
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
    });

    it('should position camera with proper distance for viewing', () => {
      const positions: THREE.Vector3[] = [
        new THREE.Vector3(0, 0, 0),
        new THREE.Vector3(3, 0, 0),
        new THREE.Vector3(7, 0, 0),
        new THREE.Vector3(10, 0, 0),
        new THREE.Vector3(15, 0, 0),
      ];

      const preset = calculateOptimalDefaultView(positions);
      // Distance should be enough to see all bodies
      expect(preset.position.length()).toBeGreaterThan(15);
    });
  });

  describe('preset properties', () => {
    it('all presets should have name property', () => {
      Object.values(CAMERA_PRESETS).forEach((preset) => {
        expect(preset.name).toBeDefined();
        expect(typeof preset.name).toBe('string');
      });
    });

    it('all presets should have position property', () => {
      Object.values(CAMERA_PRESETS).forEach((preset) => {
        expect(preset.position).toBeInstanceOf(THREE.Vector3);
      });
    });

    it('all presets should have target property', () => {
      Object.values(CAMERA_PRESETS).forEach((preset) => {
        expect(preset.target).toBeInstanceOf(THREE.Vector3);
      });
    });

    it('preset positions should not be origin for body-specific presets', () => {
      ['earth', 'moon', 'mercury', 'venus', 'mars', 'sun'].forEach((key) => {
        const preset = CAMERA_PRESETS[key as keyof typeof CAMERA_PRESETS];
        const positionLength = preset.position.length();
        expect(positionLength).toBeGreaterThan(0);
      });
    });

    it('mars preset should be further than earth preset', () => {
      const earthDist = CAMERA_PRESETS.earth.position.length();
      const marsDist = CAMERA_PRESETS.mars.position.length();
      expect(marsDist).toBeGreaterThan(earthDist);
    });
  });

  describe('calculateOptimalEarthMoonView', () => {
    it('should create a preset for Earth-Moon system', () => {
      const earthPosition = new THREE.Vector3(0, 0, 0);
      const moonPosition = new THREE.Vector3(0.38, 0, 0);

      const preset = calculateOptimalEarthMoonView(earthPosition, moonPosition);
      expect(preset).toBeDefined();
      expect(preset.name).toBe('Earth/Moon Subsystem');
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toBeInstanceOf(THREE.Vector3);
    });

    it('should position camera to view both Earth and Moon', () => {
      const earthPosition = new THREE.Vector3(0, 0, 0);
      const moonPosition = new THREE.Vector3(0.38, 0, 0);

      const preset = calculateOptimalEarthMoonView(earthPosition, moonPosition);
      // Camera should be positioned to see both bodies
      expect(preset.position.length()).toBeGreaterThan(0);
      expect(preset.position.length()).toBeLessThan(100); // reasonable camera distance
    });

    it('should handle large Earth-Moon separation', () => {
      const earthPosition = new THREE.Vector3(0, 0, 0);
      const moonPosition = new THREE.Vector3(4, 0, 0);

      const preset = calculateOptimalEarthMoonView(earthPosition, moonPosition);
      expect(preset).toBeDefined();
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toBeInstanceOf(THREE.Vector3);
    });

    it('should position target near Earth-Moon system center', () => {
      const earthPosition = new THREE.Vector3(0, 0, 0);
      const moonPosition = new THREE.Vector3(0.38, 0, 0);

      const preset = calculateOptimalEarthMoonView(earthPosition, moonPosition);
      // Target should be near the Earth-Moon system
      const targetDistance = preset.target.distanceTo(earthPosition);
      expect(targetDistance).toBeLessThan(2); // target should be close to the system
    });

    it('should have camera elevated above the system', () => {
      const earthPosition = new THREE.Vector3(0, 0, 0);
      const moonPosition = new THREE.Vector3(0.38, 0, 0);

      const preset = calculateOptimalEarthMoonView(earthPosition, moonPosition);
      // Camera should be elevated (positive Y component)
      expect(preset.position.y).toBeGreaterThan(0);
    });

    it('should scale camera distance with Earth-Moon separation', () => {
      const earthPosition = new THREE.Vector3(0, 0, 0);
      const moonPositionClose = new THREE.Vector3(0.1, 0, 0);
      const moonPositionFar = new THREE.Vector3(1.0, 0, 0);

      const presetClose = calculateOptimalEarthMoonView(earthPosition, moonPositionClose);
      const presetFar = calculateOptimalEarthMoonView(earthPosition, moonPositionFar);

      // Further separation should result in a more distant camera
      expect(presetFar.position.length()).toBeGreaterThan(presetClose.position.length());
    });

    it('should handle various orbital positions', () => {
      // Test with different Moon orbital positions
      const earthPosition = new THREE.Vector3(10, 5, 0);
      const moonPositions = [
        new THREE.Vector3(10.38, 5, 0), // East
        new THREE.Vector3(9.62, 5, 0),  // West
        new THREE.Vector3(10, 5.38, 0), // North
        new THREE.Vector3(10, 4.62, 0), // South
      ];

      moonPositions.forEach((moonPos) => {
        const preset = calculateOptimalEarthMoonView(earthPosition, moonPos);
        expect(preset).toBeDefined();
        expect(preset.position).toBeInstanceOf(THREE.Vector3);
        expect(preset.target).toBeInstanceOf(THREE.Vector3);
      });
    });
  });

  describe('calculateBodyViewPreset', () => {
    it('should calculate view preset for sun', () => {
      const bodyPosition = new THREE.Vector3(10, 0, 0);
      const preset = calculateBodyViewPreset(bodyPosition, 'sun');

      expect(preset).toBeDefined();
      expect(preset.name).toBe('Sun View (Dynamic)');
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toEqual(bodyPosition);
    });

    it('should calculate view preset for mars', () => {
      const bodyPosition = new THREE.Vector3(5, 2, 3);
      const preset = calculateBodyViewPreset(bodyPosition, 'mars');

      expect(preset).toBeDefined();
      expect(preset.name).toBe('Mars View (Dynamic)');
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toEqual(bodyPosition);
    });

    it('should calculate view preset for mercury', () => {
      const bodyPosition = new THREE.Vector3(2, 1, 1);
      const preset = calculateBodyViewPreset(bodyPosition, 'mercury');

      expect(preset).toBeDefined();
      expect(preset.name).toBe('Mercury View (Dynamic)');
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toEqual(bodyPosition);
    });

    it('should calculate view preset for venus', () => {
      const bodyPosition = new THREE.Vector3(3, 1, 2);
      const preset = calculateBodyViewPreset(bodyPosition, 'venus');

      expect(preset).toBeDefined();
      expect(preset.name).toBe('Venus View (Dynamic)');
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toEqual(bodyPosition);
    });

    it('should calculate view preset for earth', () => {
      const bodyPosition = new THREE.Vector3(0, 0, 0);
      const preset = calculateBodyViewPreset(bodyPosition, 'earth');

      expect(preset).toBeDefined();
      expect(preset.name).toBe('Earth View (Dynamic)');
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toEqual(bodyPosition);
    });

    it('should calculate view preset for moon', () => {
      const bodyPosition = new THREE.Vector3(0.38, 0, 0);
      const preset = calculateBodyViewPreset(bodyPosition, 'moon');

      expect(preset).toBeDefined();
      expect(preset.name).toBe('Moon View (Dynamic)');
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toEqual(bodyPosition);
    });

    it('should use default view distance for unknown body', () => {
      const bodyPosition = new THREE.Vector3(5, 0, 0);
      const preset = calculateBodyViewPreset(bodyPosition, 'unknown');

      expect(preset).toBeDefined();
      expect(preset.name).toBe('Unknown View (Dynamic)');
      expect(preset.position).toBeInstanceOf(THREE.Vector3);
      expect(preset.target).toEqual(bodyPosition);
      // Default view distance is 15
      expect(preset.position.z).toBeLessThan(bodyPosition.z); // Camera positioned back
    });

    it('should be case insensitive for body names', () => {
      const bodyPosition = new THREE.Vector3(5, 0, 0);
      const presetLower = calculateBodyViewPreset(bodyPosition, 'mars');
      const presetUpper = calculateBodyViewPreset(bodyPosition, 'MARS');
      const presetMixed = calculateBodyViewPreset(bodyPosition, 'MaRs');

      // All should have same distance calculations
      expect(presetLower.position.length()).toBeCloseTo(presetUpper.position.length(), 5);
      expect(presetLower.position.length()).toBeCloseTo(presetMixed.position.length(), 5);
    });

    it('should position camera with elevation and back offset', () => {
      const bodyPosition = new THREE.Vector3(0, 0, 0);
      const preset = calculateBodyViewPreset(bodyPosition, 'sun');

      // Camera should be elevated (y > 0) and back (z < 0)
      expect(preset.position.y).toBeGreaterThan(0);
      expect(preset.position.z).toBeLessThan(0);
    });

    it('should maintain correct distance for each body type', () => {
      const bodyPosition = new THREE.Vector3(0, 0, 0);
      
      const sunPreset = calculateBodyViewPreset(bodyPosition, 'sun');
      const moonPreset = calculateBodyViewPreset(bodyPosition, 'moon');
      
      // Sun should be further away than moon
      expect(sunPreset.position.length()).toBeGreaterThan(moonPreset.position.length());
    });
  });
});
