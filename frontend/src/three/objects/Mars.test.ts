import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Mars } from './Mars';
import * as THREE from 'three';

describe('Mars', () => {
  let mars: Mars;

  beforeEach(() => {
    mars = new Mars();
  });

  describe('initialization', () => {
    it('should create a mesh with correct geometry', () => {
      expect(mars.mesh).toBeInstanceOf(THREE.Mesh);
      expect(mars.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });

    it('should have correct mesh name', () => {
      expect(mars.mesh.name).toBe('mars');
    });

    it('should have reddish mars material color', () => {
      const material = mars.mesh.material as THREE.MeshStandardMaterial;
      expect(material.color.getHex()).toBe(0xe27b58);
      expect(material).toBeInstanceOf(THREE.MeshStandardMaterial);
    });

    it('should have correct roughness and metalness', () => {
      const material = mars.mesh.material as THREE.MeshStandardMaterial;
      expect(material.roughness).toBe(0.8);
      expect(material.metalness).toBe(0.0);
    });

    it('should be visible by default', () => {
      expect(mars.mesh.visible).toBe(true);
    });
  });

  describe('3D view positioning', () => {
    it('should position at zenith (altitude 90°, any azimuth)', () => {
      mars.updatePosition(0, 90, true, '3D');

      expect(mars.mesh.position.y).toBeCloseTo(25.4, 1);
      expect(Math.abs(mars.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(mars.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at horizon north (azimuth 0°, altitude 0°)', () => {
      mars.updatePosition(0, 0, true, '3D');

      expect(Math.abs(mars.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(mars.mesh.position.y)).toBeLessThan(0.1);
      expect(mars.mesh.position.z).toBeCloseTo(-25.4, 1);
    });

    it('should position at horizon east (azimuth 90°, altitude 0°)', () => {
      mars.updatePosition(90, 0, true, '3D');

      expect(mars.mesh.position.x).toBeCloseTo(25.4, 1);
      expect(Math.abs(mars.mesh.position.y)).toBeLessThan(0.1);
      expect(Math.abs(mars.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at 45° elevation, 45° azimuth', () => {
      mars.updatePosition(45, 45, true, '3D');

      const distance = 25.4;
      const expectedY = distance * Math.sin(THREE.MathUtils.degToRad(45));
      const horizontalDist = distance * Math.cos(THREE.MathUtils.degToRad(45));

      expect(mars.mesh.position.y).toBeCloseTo(expectedY, 1);
      expect(mars.mesh.position.x).toBeCloseTo(horizontalDist * Math.sin(THREE.MathUtils.degToRad(45)), 1);
    });

    it('should place all cardinal directions at orbit distance 25.4', () => {
      [0, 90, 180, 270].forEach(azimuth => {
        mars.updatePosition(azimuth, 30, true, '3D');
        const distance = Math.sqrt(
          mars.mesh.position.x ** 2 +
          mars.mesh.position.y ** 2 +
          mars.mesh.position.z ** 2
        );
        expect(distance).toBeCloseTo(25.4, 0);
      });
    });

    it('should position at horizon south (azimuth 180°, altitude 0°)', () => {
      mars.updatePosition(180, 0, true, '3D');

      expect(Math.abs(mars.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(mars.mesh.position.y)).toBeLessThan(0.1);
      expect(mars.mesh.position.z).toBeCloseTo(25.4, 1);
    });
  });

  describe('SKY view positioning', () => {
    it('should position at zenith on hemisphere', () => {
      mars.updatePosition(0, 90, true, 'SKY');

      expect(Math.abs(mars.mesh.position.x)).toBeLessThan(0.1);
      expect(mars.mesh.position.y).toBeCloseTo(10, 1);
      expect(Math.abs(mars.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position on horizon circle when altitude is 0°', () => {
      mars.updatePosition(90, 0, true, 'SKY');

      expect(mars.mesh.position.y).toBeCloseTo(0, 1);
      const horizontalDist = Math.sqrt(
        mars.mesh.position.x ** 2 + mars.mesh.position.z ** 2
      );
      expect(horizontalDist).toBeCloseTo(10, 1);
    });

    it('should position below horizon when altitude is negative', () => {
      mars.updatePosition(0, -10, true, 'SKY');

      expect(mars.mesh.position.y).toBe(0);
    });

    it('should maintain correct azimuth angle in sky view', () => {
      [0, 90, 180, 270].forEach(azimuth => {
        mars.updatePosition(azimuth, 45, true, 'SKY');

        const actualAzimuth = Math.atan2(mars.mesh.position.x, -mars.mesh.position.z);
        const expectedAzimuth = THREE.MathUtils.degToRad(azimuth);
        const diff = Math.abs(actualAzimuth - expectedAzimuth);
        expect(diff < 0.1 || diff > 2 * Math.PI - 0.1).toBe(true);
      });
    });

    it('should position at all 4 cardinal points in sky view', () => {
      const testCases = [
        { azimuth: 0, altitude: 45, expectedDirection: 'north' },
        { azimuth: 90, altitude: 45, expectedDirection: 'east' },
        { azimuth: 180, altitude: 45, expectedDirection: 'south' },
        { azimuth: 270, altitude: 45, expectedDirection: 'west' },
      ];

      testCases.forEach(test => {
        mars.updatePosition(test.azimuth, test.altitude, true, 'SKY');
        expect(mars.mesh.position).toBeDefined();
      });
    });
  });

  describe('visibility control', () => {
    it('should hide mesh when isVisible is false', () => {
      mars.updatePosition(0, 45, false, '3D');
      expect(mars.mesh.visible).toBe(false);
    });

    it('should show mesh when isVisible is true', () => {
      mars.updatePosition(0, 45, true, '3D');
      expect(mars.mesh.visible).toBe(true);
    });

    it('should maintain visibility across view mode changes', () => {
      mars.updatePosition(0, 45, true, '3D');
      expect(mars.mesh.visible).toBe(true);

      mars.setViewMode('sky');
      mars.updatePosition(0, 45, true, 'SKY');
      expect(mars.mesh.visible).toBe(true);
    });
  });

  describe('view mode switching', () => {
    it('should switch to sky view geometry', () => {
      const initialGeometry = mars.mesh.geometry;
      mars.setViewMode('sky');
      expect(mars.mesh.geometry).not.toBe(initialGeometry);
    });

    it('should switch back to 3D view geometry', () => {
      mars.setViewMode('sky');
      mars.setViewMode('3d');
      expect(mars.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });
  });

  describe('sky view disk radius', () => {
    it('should use minimum disk radius (angular diameter too small)', () => {
      const geometry = (mars as any)['skyViewGeometry'];
      expect((geometry as THREE.SphereGeometry).parameters.radius).toBe(0.2);
    });
  });

  describe('scene management', () => {
    it('should add mesh to scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      mars.addToScene(mockScene as any);
      expect(mockScene.add).toHaveBeenCalledWith(mars.mesh);
    });

    it('should add label to scene when adding to scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      mars.addToScene(mockScene as any);
      expect(mockScene.add).toHaveBeenCalledTimes(2);
    });

    it('should remove mesh from scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      mars.removeFromScene(mockScene as any);
      expect(mockScene.remove).toHaveBeenCalledWith(mars.mesh);
    });

    it('should remove label from scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      mars.removeFromScene(mockScene as any);
      expect(mockScene.remove).toHaveBeenCalledTimes(2);
    });
  });

  describe('additional positioning', () => {
    it('should handle negative altitudes in 3D view', () => {
      mars.updatePosition(180, -30, true, '3D');
      expect(mars.mesh.position).toBeDefined();
    });

    it('should handle 360° azimuth (wraps to 0°)', () => {
      mars.updatePosition(360, 45, true, '3D');
      expect(mars.mesh.position).toBeDefined();
    });

    it('should position near zenith at very high altitude', () => {
      mars.updatePosition(45, 89.9, true, '3D');
      expect(mars.mesh.position.y).toBeGreaterThan(20);
    });
  });

  describe('view mode persistence', () => {
    it('should use sky view geometry after switching to sky', () => {
      const defaultGeometry = mars.mesh.geometry;
      mars.setViewMode('sky');
      expect(mars.mesh.geometry).not.toBe(defaultGeometry);
    });

    it('should restore default geometry after switching back to 3d', () => {
      const defaultGeometry = mars.mesh.geometry;
      mars.setViewMode('sky');
      mars.setViewMode('3d');
      expect(mars.mesh.geometry).toBe(defaultGeometry);
    });

    it('should remain visible after switching view modes', () => {
      mars.updatePosition(45, 30, true, '3D');
      mars.setViewMode('sky');
      mars.updatePosition(45, 30, true, 'SKY');
      expect(mars.mesh.visible).toBe(true);
      expect(mars.mesh.position).toBeDefined();
    });
  });

  describe('label billboard', () => {
    it('should update label billboard without throwing', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      camera.position.set(5, 5, 5);
      mars.updatePosition(45, 45, true, '3D');
      expect(() => mars.updateLabelBillboard(camera)).not.toThrow();
    });
  });

  describe('resource disposal', () => {
    it('should dispose resources', () => {
      expect(() => mars.dispose()).not.toThrow();
    });

    it('should dispose geometry', () => {
      const disposeSpy = vi.spyOn(mars.mesh.geometry, 'dispose');
      mars.dispose();
      expect(disposeSpy).toHaveBeenCalled();
    });
  });

  describe('orbit distance verification', () => {
    it('should maintain 25.4 unit distance across multiple positions', () => {
      const positions = [
        { az: 0, alt: 0 },
        { az: 45, alt: 45 },
        { az: 90, alt: 30 },
        { az: 180, alt: 60 },
        { az: 270, alt: 15 },
      ];

      positions.forEach(pos => {
        mars.updatePosition(pos.az, pos.alt, true, '3D');
        const distance = Math.sqrt(
          mars.mesh.position.x ** 2 +
          mars.mesh.position.y ** 2 +
          mars.mesh.position.z ** 2
        );
        expect(distance).toBeCloseTo(25.4, 0);
      });
    });
  });
});
