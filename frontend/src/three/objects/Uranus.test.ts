import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Uranus } from './Uranus';
import * as THREE from 'three';

describe('Uranus', () => {
  let uranus: Uranus;
  const DISTANCE = 192;

  beforeEach(() => {
    uranus = new Uranus();
  });

  describe('initialization', () => {
    it('should create a mesh with correct geometry', () => {
      expect(uranus.mesh).toBeInstanceOf(THREE.Mesh);
      expect(uranus.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });

    it('should have correct mesh name', () => {
      expect(uranus.mesh.name).toBe('uranus');
    });

    it('should have correct default radius', () => {
      const geometry = uranus.mesh.geometry as THREE.SphereGeometry;
      expect(geometry.parameters.radius).toBe(1.19);
    });

    it('should have cyan/turquoise uranus material color', () => {
      const material = uranus.mesh.material as THREE.MeshStandardMaterial;
      expect(material.color.getHex()).toBe(0x4fd0e7);
      expect(material).toBeInstanceOf(THREE.MeshStandardMaterial);
    });

    it('should have correct roughness and metalness', () => {
      const material = uranus.mesh.material as THREE.MeshStandardMaterial;
      expect(material.roughness).toBe(0.8);
      expect(material.metalness).toBe(0.1);
    });

    it('should be visible by default', () => {
      expect(uranus.mesh.visible).toBe(true);
    });
  });

  describe('3D view positioning', () => {
    it('should position at zenith (altitude 90°, any azimuth)', () => {
      uranus.updatePosition(0, 90, true, '3D');

      expect(uranus.mesh.position.y).toBeCloseTo(DISTANCE, 1);
      expect(Math.abs(uranus.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(uranus.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at horizon north (azimuth 0°, altitude 0°)', () => {
      uranus.updatePosition(0, 0, true, '3D');

      expect(Math.abs(uranus.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(uranus.mesh.position.y)).toBeLessThan(0.1);
      expect(uranus.mesh.position.z).toBeCloseTo(-DISTANCE, 1);
    });

    it('should position at horizon east (azimuth 90°, altitude 0°)', () => {
      uranus.updatePosition(90, 0, true, '3D');

      expect(uranus.mesh.position.x).toBeCloseTo(DISTANCE, 1);
      expect(Math.abs(uranus.mesh.position.y)).toBeLessThan(0.1);
      expect(Math.abs(uranus.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should place all cardinal directions at orbit distance', () => {
      [0, 90, 180, 270].forEach(azimuth => {
        uranus.updatePosition(azimuth, 30, true, '3D');
        const distance = Math.sqrt(
          uranus.mesh.position.x ** 2 +
          uranus.mesh.position.y ** 2 +
          uranus.mesh.position.z ** 2
        );
        expect(distance).toBeCloseTo(DISTANCE, 0);
      });
    });
  });

  describe('SKY view positioning', () => {
    it('should position at zenith on hemisphere', () => {
      uranus.updatePosition(0, 90, true, 'SKY');

      expect(Math.abs(uranus.mesh.position.x)).toBeLessThan(0.1);
      expect(uranus.mesh.position.y).toBeCloseTo(10, 1);
      expect(Math.abs(uranus.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position below horizon when altitude is negative', () => {
      uranus.updatePosition(0, -10, true, 'SKY');
      expect(uranus.mesh.position.y).toBe(0);
    });
  });

  describe('visibility control', () => {
    it('should hide mesh when isVisible is false', () => {
      uranus.updatePosition(0, 45, false, '3D');
      expect(uranus.mesh.visible).toBe(false);
    });

    it('should show mesh when isVisible is true', () => {
      uranus.updatePosition(0, 45, true, '3D');
      expect(uranus.mesh.visible).toBe(true);
    });
  });

  describe('view mode switching', () => {
    it('should switch to sky view geometry', () => {
      const initialGeometry = uranus.mesh.geometry;
      uranus.setViewMode('sky');
      expect(uranus.mesh.geometry).not.toBe(initialGeometry);
    });

    it('should switch back to 3D view geometry', () => {
      const defaultGeometry = uranus.mesh.geometry;
      uranus.setViewMode('sky');
      uranus.setViewMode('3d');
      expect(uranus.mesh.geometry).toBe(defaultGeometry);
    });
  });

  describe('sky view disk radius', () => {
    it('should use minimum disk radius (angular diameter too small)', () => {
      const geometry = (uranus as any)['skyViewGeometry'];
      expect((geometry as THREE.SphereGeometry).parameters.radius).toBe(0.2);
    });
  });

  describe('scene management', () => {
    it('should add mesh and label to scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      uranus.addToScene(mockScene as any);
      expect(mockScene.add).toHaveBeenCalledWith(uranus.mesh);
      expect(mockScene.add).toHaveBeenCalledTimes(2);
    });

    it('should remove mesh and label from scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      uranus.removeFromScene(mockScene as any);
      expect(mockScene.remove).toHaveBeenCalledWith(uranus.mesh);
      expect(mockScene.remove).toHaveBeenCalledTimes(2);
    });
  });

  describe('label billboard', () => {
    it('should update label billboard without throwing', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      camera.position.set(5, 5, 5);
      uranus.updatePosition(45, 45, true, '3D');
      expect(() => uranus.updateLabelBillboard(camera)).not.toThrow();
    });
  });

  describe('dispose', () => {
    it('should not throw when disposing', () => {
      expect(() => uranus.dispose()).not.toThrow();
    });

    it('should not throw when disposing after switching view mode', () => {
      uranus.setViewMode('sky');
      expect(() => uranus.dispose()).not.toThrow();
    });
  });
});
