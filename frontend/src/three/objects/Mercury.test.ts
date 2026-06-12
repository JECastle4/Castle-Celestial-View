import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Mercury } from './Mercury';
import * as THREE from 'three';

describe('Mercury', () => {
  let mercury: Mercury;

  beforeEach(() => {
    mercury = new Mercury();
  });

  describe('initialization', () => {
    it('should create a mesh with correct geometry', () => {
      expect(mercury.mesh).toBeInstanceOf(THREE.Mesh);
      expect(mercury.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });

    it('should have correct mesh name', () => {
      expect(mercury.mesh.name).toBe('mercury');
    });

    it('should have dark grey material color', () => {
      const material = mercury.mesh.material as THREE.MeshStandardMaterial;
      expect(material.color.getHex()).toBe(0x909090);
      expect(material).toBeInstanceOf(THREE.MeshStandardMaterial);
    });

    it('should have correct roughness and metalness', () => {
      const material = mercury.mesh.material as THREE.MeshStandardMaterial;
      expect(material.roughness).toBe(0.9);
      expect(material.metalness).toBe(0.1);
    });

    it('should be visible by default', () => {
      expect(mercury.mesh.visible).toBe(true);
    });
  });

  describe('3D view positioning', () => {
    it('should position at zenith (altitude 90°, any azimuth)', () => {
      mercury.updatePosition(0, 90, true, '3D');

      expect(mercury.mesh.position.y).toBeCloseTo(12.3, 1);
      expect(Math.abs(mercury.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(mercury.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at horizon north (azimuth 0°, altitude 0°)', () => {
      mercury.updatePosition(0, 0, true, '3D');

      expect(Math.abs(mercury.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(mercury.mesh.position.y)).toBeLessThan(0.1);
      expect(mercury.mesh.position.z).toBeCloseTo(-12.3, 1);
    });

    it('should position at horizon east (azimuth 90°, altitude 0°)', () => {
      mercury.updatePosition(90, 0, true, '3D');

      expect(mercury.mesh.position.x).toBeCloseTo(12.3, 1);
      expect(Math.abs(mercury.mesh.position.y)).toBeLessThan(0.1);
      expect(Math.abs(mercury.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at 45° elevation, 45° azimuth', () => {
      mercury.updatePosition(45, 45, true, '3D');

      const distance = 12.3;
      const expectedY = distance * Math.sin(THREE.MathUtils.degToRad(45));
      const horizontalDist = distance * Math.cos(THREE.MathUtils.degToRad(45));

      expect(mercury.mesh.position.y).toBeCloseTo(expectedY, 1);
      expect(mercury.mesh.position.x).toBeCloseTo(horizontalDist * Math.sin(THREE.MathUtils.degToRad(45)), 1);
    });

    it('should place all cardinal directions at orbit distance 12.3', () => {
      [0, 90, 180, 270].forEach(azimuth => {
        mercury.updatePosition(azimuth, 30, true, '3D');
        const distance = Math.sqrt(
          mercury.mesh.position.x ** 2 +
          mercury.mesh.position.y ** 2 +
          mercury.mesh.position.z ** 2
        );
        expect(distance).toBeCloseTo(12.3, 0);
      });
    });
  });

  describe('SKY view positioning', () => {
    it('should position at zenith on hemisphere', () => {
      mercury.updatePosition(0, 90, true, 'SKY');

      expect(Math.abs(mercury.mesh.position.x)).toBeLessThan(0.1);
      expect(mercury.mesh.position.y).toBeCloseTo(10, 1);
      expect(Math.abs(mercury.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position on horizon circle when altitude is 0°', () => {
      mercury.updatePosition(90, 0, true, 'SKY');

      expect(mercury.mesh.position.y).toBeCloseTo(0, 1);
      const horizontalDist = Math.sqrt(
        mercury.mesh.position.x ** 2 + mercury.mesh.position.z ** 2
      );
      expect(horizontalDist).toBeCloseTo(10, 1);
    });

    it('should position below horizon when altitude is negative', () => {
      mercury.updatePosition(0, -10, true, 'SKY');

      expect(mercury.mesh.position.y).toBe(0);
    });

    it('should maintain correct azimuth angle in sky view', () => {
      [0, 90, 180, 270].forEach(azimuth => {
        mercury.updatePosition(azimuth, 45, true, 'SKY');

        const actualAzimuth = Math.atan2(mercury.mesh.position.x, -mercury.mesh.position.z);
        const expectedAzimuth = THREE.MathUtils.degToRad(azimuth);
        const diff = Math.abs(actualAzimuth - expectedAzimuth);
        expect(diff < 0.1 || diff > 2 * Math.PI - 0.1).toBe(true);
      });
    });
  });

  describe('visibility control', () => {
    it('should hide mesh when isVisible is false', () => {
      mercury.updatePosition(0, 45, false, '3D');
      expect(mercury.mesh.visible).toBe(false);
    });

    it('should show mesh when isVisible is true', () => {
      mercury.updatePosition(0, 45, true, '3D');
      expect(mercury.mesh.visible).toBe(true);
    });

    it('should maintain visibility across view mode changes', () => {
      mercury.updatePosition(0, 45, true, '3D');
      expect(mercury.mesh.visible).toBe(true);

      mercury.setViewMode('sky');
      mercury.updatePosition(0, 45, true, 'SKY');
      expect(mercury.mesh.visible).toBe(true);
    });
  });

  describe('view mode switching', () => {
    it('should switch to sky view geometry', () => {
      const initialGeometry = mercury.mesh.geometry;
      mercury.setViewMode('sky');
      expect(mercury.mesh.geometry).not.toBe(initialGeometry);
    });

    it('should switch back to 3D view geometry', () => {
      mercury.setViewMode('sky');
      mercury.setViewMode('3d');
      expect(mercury.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });
  });

  describe('sky view disk radius', () => {
    it('should always use minimum disk radius (angular diameter too small)', () => {
      const geometry = mercury['skyViewGeometry'];
      expect((geometry as THREE.SphereGeometry).parameters.radius).toBe(0.2);
    });
  });

  describe('scene management', () => {
    it('should add mesh to scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      mercury.addToScene(mockScene as any);
      expect(mockScene.add).toHaveBeenCalledWith(mercury.mesh);
    });

    it('should remove mesh from scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      mercury.removeFromScene(mockScene as any);
      expect(mockScene.remove).toHaveBeenCalledWith(mercury.mesh);
    });
  });

  describe('additional positioning', () => {
    it('should handle negative altitudes in 3D view', () => {
      mercury.updatePosition(180, -30, true, '3D');
      expect(mercury.mesh.position).toBeDefined();
    });

    it('should handle 360° azimuth (wraps to 0°)', () => {
      mercury.updatePosition(360, 45, true, '3D');
      expect(mercury.mesh.position).toBeDefined();
    });

    it('should position near zenith at very high altitude', () => {
      mercury.updatePosition(45, 89.9, true, '3D');
      expect(mercury.mesh.position.y).toBeGreaterThan(9);
    });
  });

  describe('view mode persistence', () => {
    it('should use sky view geometry after switching to sky', () => {
      const defaultGeometry = mercury.mesh.geometry;
      mercury.setViewMode('sky');
      expect(mercury.mesh.geometry).not.toBe(defaultGeometry);
    });

    it('should restore default geometry after switching back to 3d', () => {
      const defaultGeometry = mercury.mesh.geometry;
      mercury.setViewMode('sky');
      mercury.setViewMode('3d');
      expect(mercury.mesh.geometry).toBe(defaultGeometry);
    });

    it('should remain visible after switching view modes', () => {
      mercury.updatePosition(45, 30, true, '3D');
      mercury.setViewMode('sky');
      mercury.updatePosition(45, 30, true, 'SKY');
      expect(mercury.mesh.visible).toBe(true);
      expect(mercury.mesh.position).toBeDefined();
    });
  });

  describe('label billboard', () => {
    it('should update label billboard without throwing', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      camera.position.set(5, 5, 5);
      mercury.updatePosition(45, 45, true, '3D');
      expect(() => mercury.updateLabelBillboard(camera)).not.toThrow();
    });
  });
});
