import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Saturn } from './Saturn';
import * as THREE from 'three';

describe('Saturn', () => {
  let saturn: Saturn;
  const DISTANCE = 95;

  beforeEach(() => {
    saturn = new Saturn();
  });

  describe('initialization', () => {
    it('should create a mesh with correct geometry', () => {
      expect(saturn.mesh).toBeInstanceOf(THREE.Mesh);
      expect(saturn.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });

    it('should have correct mesh name', () => {
      expect(saturn.mesh.name).toBe('saturn');
    });

    it('should have correct default radius', () => {
      const geometry = saturn.mesh.geometry as THREE.SphereGeometry;
      expect(geometry.parameters.radius).toBe(2.84);
    });

    it('should have pale gold saturn material color', () => {
      const material = saturn.mesh.material as THREE.MeshStandardMaterial;
      expect(material.color.getHex()).toBe(0xf4d89f);
      expect(material).toBeInstanceOf(THREE.MeshStandardMaterial);
    });

    it('should have correct roughness and metalness', () => {
      const material = saturn.mesh.material as THREE.MeshStandardMaterial;
      expect(material.roughness).toBe(0.8);
      expect(material.metalness).toBe(0.1);
    });

    it('should be visible by default', () => {
      expect(saturn.mesh.visible).toBe(true);
    });
  });

  describe('3D view positioning', () => {
    it('should position at zenith (altitude 90°, any azimuth)', () => {
      saturn.updatePosition(0, 90, true, '3D');

      expect(saturn.mesh.position.y).toBeCloseTo(DISTANCE, 1);
      expect(Math.abs(saturn.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(saturn.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at horizon north (azimuth 0°, altitude 0°)', () => {
      saturn.updatePosition(0, 0, true, '3D');

      expect(Math.abs(saturn.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(saturn.mesh.position.y)).toBeLessThan(0.1);
      expect(saturn.mesh.position.z).toBeCloseTo(-DISTANCE, 1);
    });

    it('should position at horizon east (azimuth 90°, altitude 0°)', () => {
      saturn.updatePosition(90, 0, true, '3D');

      expect(saturn.mesh.position.x).toBeCloseTo(DISTANCE, 1);
      expect(Math.abs(saturn.mesh.position.y)).toBeLessThan(0.1);
      expect(Math.abs(saturn.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should place all cardinal directions at orbit distance', () => {
      [0, 90, 180, 270].forEach(azimuth => {
        saturn.updatePosition(azimuth, 30, true, '3D');
        const distance = Math.sqrt(
          saturn.mesh.position.x ** 2 +
          saturn.mesh.position.y ** 2 +
          saturn.mesh.position.z ** 2
        );
        expect(distance).toBeCloseTo(DISTANCE, 0);
      });
    });
  });

  describe('SKY view positioning', () => {
    it('should position at zenith on hemisphere', () => {
      saturn.updatePosition(0, 90, true, 'SKY');

      expect(Math.abs(saturn.mesh.position.x)).toBeLessThan(0.1);
      expect(saturn.mesh.position.y).toBeCloseTo(10, 1);
      expect(Math.abs(saturn.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position below horizon when altitude is negative', () => {
      saturn.updatePosition(0, -10, true, 'SKY');
      expect(saturn.mesh.position.y).toBe(0);
    });
  });

  describe('visibility control', () => {
    it('should hide mesh when isVisible is false', () => {
      saturn.updatePosition(0, 45, false, '3D');
      expect(saturn.mesh.visible).toBe(false);
    });

    it('should show mesh when isVisible is true', () => {
      saturn.updatePosition(0, 45, true, '3D');
      expect(saturn.mesh.visible).toBe(true);
    });
  });

  describe('view mode switching', () => {
    it('should switch to sky view geometry', () => {
      const initialGeometry = saturn.mesh.geometry;
      saturn.setViewMode('sky');
      expect(saturn.mesh.geometry).not.toBe(initialGeometry);
    });

    it('should switch back to 3D view geometry', () => {
      const defaultGeometry = saturn.mesh.geometry;
      saturn.setViewMode('sky');
      saturn.setViewMode('3d');
      expect(saturn.mesh.geometry).toBe(defaultGeometry);
    });
  });

  describe('sky view disk radius', () => {
    it('should use minimum disk radius (angular diameter too small)', () => {
      const geometry = (saturn as any)['skyViewGeometry'];
      expect((geometry as THREE.SphereGeometry).parameters.radius).toBe(0.2);
    });
  });

  describe('scene management', () => {
    it('should add mesh and label to scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      saturn.addToScene(mockScene as any);
      expect(mockScene.add).toHaveBeenCalledWith(saturn.mesh);
      expect(mockScene.add).toHaveBeenCalledTimes(2);
    });

    it('should remove mesh and label from scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      saturn.removeFromScene(mockScene as any);
      expect(mockScene.remove).toHaveBeenCalledWith(saturn.mesh);
      expect(mockScene.remove).toHaveBeenCalledTimes(2);
    });
  });

  describe('label billboard', () => {
    it('should update label billboard without throwing', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      camera.position.set(5, 5, 5);
      saturn.updatePosition(45, 45, true, '3D');
      expect(() => saturn.updateLabelBillboard(camera)).not.toThrow();
    });
  });

  describe('dispose', () => {
    it('should not throw when disposing', () => {
      expect(() => saturn.dispose()).not.toThrow();
    });

    it('should not throw when disposing after switching view mode', () => {
      saturn.setViewMode('sky');
      expect(() => saturn.dispose()).not.toThrow();
    });
  });
});
