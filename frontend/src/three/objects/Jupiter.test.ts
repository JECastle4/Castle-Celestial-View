import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Jupiter } from './Jupiter';
import * as THREE from 'three';

describe('Jupiter', () => {
  let jupiter: Jupiter;
  const DISTANCE = 52;

  beforeEach(() => {
    jupiter = new Jupiter();
  });

  describe('initialization', () => {
    it('should create a mesh with correct geometry', () => {
      expect(jupiter.mesh).toBeInstanceOf(THREE.Mesh);
      expect(jupiter.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });

    it('should have correct mesh name', () => {
      expect(jupiter.mesh.name).toBe('jupiter');
    });

    it('should have correct default radius', () => {
      const geometry = jupiter.mesh.geometry as THREE.SphereGeometry;
      expect(geometry.parameters.radius).toBe(3.3);
    });

    it('should have golden/tan jupiter material color', () => {
      const material = jupiter.mesh.material as THREE.MeshStandardMaterial;
      expect(material.color.getHex()).toBe(0xc88b3a);
      expect(material).toBeInstanceOf(THREE.MeshStandardMaterial);
    });

    it('should have correct roughness and metalness', () => {
      const material = jupiter.mesh.material as THREE.MeshStandardMaterial;
      expect(material.roughness).toBe(0.8);
      expect(material.metalness).toBe(0.1);
    });

    it('should be visible by default', () => {
      expect(jupiter.mesh.visible).toBe(true);
    });
  });

  describe('3D view positioning', () => {
    it('should position at zenith (altitude 90°, any azimuth)', () => {
      jupiter.updatePosition(0, 90, true, '3D');

      expect(jupiter.mesh.position.y).toBeCloseTo(DISTANCE, 1);
      expect(Math.abs(jupiter.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(jupiter.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at horizon north (azimuth 0°, altitude 0°)', () => {
      jupiter.updatePosition(0, 0, true, '3D');

      expect(Math.abs(jupiter.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(jupiter.mesh.position.y)).toBeLessThan(0.1);
      expect(jupiter.mesh.position.z).toBeCloseTo(-DISTANCE, 1);
    });

    it('should position at horizon east (azimuth 90°, altitude 0°)', () => {
      jupiter.updatePosition(90, 0, true, '3D');

      expect(jupiter.mesh.position.x).toBeCloseTo(DISTANCE, 1);
      expect(Math.abs(jupiter.mesh.position.y)).toBeLessThan(0.1);
      expect(Math.abs(jupiter.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should place all cardinal directions at orbit distance', () => {
      [0, 90, 180, 270].forEach(azimuth => {
        jupiter.updatePosition(azimuth, 30, true, '3D');
        const distance = Math.sqrt(
          jupiter.mesh.position.x ** 2 +
          jupiter.mesh.position.y ** 2 +
          jupiter.mesh.position.z ** 2
        );
        expect(distance).toBeCloseTo(DISTANCE, 0);
      });
    });
  });

  describe('SKY view positioning', () => {
    it('should position at zenith on hemisphere', () => {
      jupiter.updatePosition(0, 90, true, 'SKY');

      expect(Math.abs(jupiter.mesh.position.x)).toBeLessThan(0.1);
      expect(jupiter.mesh.position.y).toBeCloseTo(10, 1);
      expect(Math.abs(jupiter.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position below horizon when altitude is negative', () => {
      jupiter.updatePosition(0, -10, true, 'SKY');
      expect(jupiter.mesh.position.y).toBe(0);
    });
  });

  describe('visibility control', () => {
    it('should hide mesh when isVisible is false', () => {
      jupiter.updatePosition(0, 45, false, '3D');
      expect(jupiter.mesh.visible).toBe(false);
    });

    it('should show mesh when isVisible is true', () => {
      jupiter.updatePosition(0, 45, true, '3D');
      expect(jupiter.mesh.visible).toBe(true);
    });
  });

  describe('view mode switching', () => {
    it('should switch to sky view geometry', () => {
      const initialGeometry = jupiter.mesh.geometry;
      jupiter.setViewMode('sky');
      expect(jupiter.mesh.geometry).not.toBe(initialGeometry);
    });

    it('should switch back to 3D view geometry', () => {
      const defaultGeometry = jupiter.mesh.geometry;
      jupiter.setViewMode('sky');
      jupiter.setViewMode('3d');
      expect(jupiter.mesh.geometry).toBe(defaultGeometry);
    });
  });

  describe('sky view disk radius', () => {
    it('should use minimum disk radius (angular diameter too small)', () => {
      const geometry = (jupiter as any)['skyViewGeometry'];
      expect((geometry as THREE.SphereGeometry).parameters.radius).toBe(0.2);
    });
  });

  describe('scene management', () => {
    it('should add mesh and label to scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      jupiter.addToScene(mockScene as any);
      expect(mockScene.add).toHaveBeenCalledWith(jupiter.mesh);
      expect(mockScene.add).toHaveBeenCalledTimes(2);
    });

    it('should remove mesh and label from scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      jupiter.removeFromScene(mockScene as any);
      expect(mockScene.remove).toHaveBeenCalledWith(jupiter.mesh);
      expect(mockScene.remove).toHaveBeenCalledTimes(2);
    });
  });

  describe('label billboard', () => {
    it('should update label billboard without throwing', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      camera.position.set(5, 5, 5);
      jupiter.updatePosition(45, 45, true, '3D');
      expect(() => jupiter.updateLabelBillboard(camera)).not.toThrow();
    });
  });

  describe('dispose', () => {
    it('should not throw when disposing', () => {
      expect(() => jupiter.dispose()).not.toThrow();
    });

    it('should not throw when disposing after switching view mode', () => {
      jupiter.setViewMode('sky');
      expect(() => jupiter.dispose()).not.toThrow();
    });
  });
});
