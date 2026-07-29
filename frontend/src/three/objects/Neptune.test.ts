import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Neptune } from './Neptune';
import * as THREE from 'three';

describe('Neptune', () => {
  let neptune: Neptune;
  const DISTANCE = 301;

  beforeEach(() => {
    neptune = new Neptune();
  });

  describe('initialization', () => {
    it('should create a mesh with correct geometry', () => {
      expect(neptune.mesh).toBeInstanceOf(THREE.Mesh);
      expect(neptune.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });

    it('should have correct mesh name', () => {
      expect(neptune.mesh.name).toBe('neptune');
    });

    it('should have correct default radius', () => {
      const geometry = neptune.mesh.geometry as THREE.SphereGeometry;
      expect(geometry.parameters.radius).toBe(1.16);
    });

    it('should have deep blue neptune material color', () => {
      const material = neptune.mesh.material as THREE.MeshStandardMaterial;
      expect(material.color.getHex()).toBe(0x4166f5);
      expect(material).toBeInstanceOf(THREE.MeshStandardMaterial);
    });

    it('should have correct roughness and metalness', () => {
      const material = neptune.mesh.material as THREE.MeshStandardMaterial;
      expect(material.roughness).toBe(0.8);
      expect(material.metalness).toBe(0.1);
    });

    it('should be visible by default', () => {
      expect(neptune.mesh.visible).toBe(true);
    });
  });

  describe('3D view positioning', () => {
    it('should position at zenith (altitude 90°, any azimuth)', () => {
      neptune.updatePosition(0, 90, true, '3D');

      expect(neptune.mesh.position.y).toBeCloseTo(DISTANCE, 1);
      expect(Math.abs(neptune.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(neptune.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at horizon north (azimuth 0°, altitude 0°)', () => {
      neptune.updatePosition(0, 0, true, '3D');

      expect(Math.abs(neptune.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(neptune.mesh.position.y)).toBeLessThan(0.1);
      expect(neptune.mesh.position.z).toBeCloseTo(-DISTANCE, 1);
    });

    it('should position at horizon east (azimuth 90°, altitude 0°)', () => {
      neptune.updatePosition(90, 0, true, '3D');

      expect(neptune.mesh.position.x).toBeCloseTo(DISTANCE, 1);
      expect(Math.abs(neptune.mesh.position.y)).toBeLessThan(0.1);
      expect(Math.abs(neptune.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should place all cardinal directions at orbit distance', () => {
      [0, 90, 180, 270].forEach(azimuth => {
        neptune.updatePosition(azimuth, 30, true, '3D');
        const distance = Math.sqrt(
          neptune.mesh.position.x ** 2 +
          neptune.mesh.position.y ** 2 +
          neptune.mesh.position.z ** 2
        );
        expect(distance).toBeCloseTo(DISTANCE, 0);
      });
    });
  });

  describe('SKY view positioning', () => {
    it('should position at zenith on hemisphere', () => {
      neptune.updatePosition(0, 90, true, 'SKY');

      expect(Math.abs(neptune.mesh.position.x)).toBeLessThan(0.1);
      expect(neptune.mesh.position.y).toBeCloseTo(10, 1);
      expect(Math.abs(neptune.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position below horizon when altitude is negative', () => {
      neptune.updatePosition(0, -10, true, 'SKY');
      expect(neptune.mesh.position.y).toBe(0);
    });
  });

  describe('visibility control', () => {
    it('should hide mesh when isVisible is false', () => {
      neptune.updatePosition(0, 45, false, '3D');
      expect(neptune.mesh.visible).toBe(false);
    });

    it('should show mesh when isVisible is true', () => {
      neptune.updatePosition(0, 45, true, '3D');
      expect(neptune.mesh.visible).toBe(true);
    });
  });

  describe('view mode switching', () => {
    it('should switch to sky view geometry', () => {
      const initialGeometry = neptune.mesh.geometry;
      neptune.setViewMode('sky');
      expect(neptune.mesh.geometry).not.toBe(initialGeometry);
    });

    it('should switch back to 3D view geometry', () => {
      const defaultGeometry = neptune.mesh.geometry;
      neptune.setViewMode('sky');
      neptune.setViewMode('3d');
      expect(neptune.mesh.geometry).toBe(defaultGeometry);
    });
  });

  describe('sky view disk radius', () => {
    it('should use minimum disk radius (angular diameter too small)', () => {
      const geometry = (neptune as any)['skyViewGeometry'];
      expect((geometry as THREE.SphereGeometry).parameters.radius).toBe(0.2);
    });
  });

  describe('scene management', () => {
    it('should add mesh and label to scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      neptune.addToScene(mockScene as any);
      expect(mockScene.add).toHaveBeenCalledWith(neptune.mesh);
      expect(mockScene.add).toHaveBeenCalledTimes(2);
    });

    it('should remove mesh and label from scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      neptune.removeFromScene(mockScene as any);
      expect(mockScene.remove).toHaveBeenCalledWith(neptune.mesh);
      expect(mockScene.remove).toHaveBeenCalledTimes(2);
    });
  });

  describe('label billboard', () => {
    it('should update label billboard without throwing', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      camera.position.set(5, 5, 5);
      neptune.updatePosition(45, 45, true, '3D');
      expect(() => neptune.updateLabelBillboard(camera)).not.toThrow();
    });
  });

  describe('dispose', () => {
    it('should not throw when disposing', () => {
      expect(() => neptune.dispose()).not.toThrow();
    });

    it('should not throw when disposing after switching view mode', () => {
      neptune.setViewMode('sky');
      expect(() => neptune.dispose()).not.toThrow();
    });
  });
});
