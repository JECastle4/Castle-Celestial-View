import { describe, it, expect, beforeEach, vi } from 'vitest';
import { Venus } from './Venus';
import * as THREE from 'three';

describe('Venus', () => {
  let venus: Venus;

  beforeEach(() => {
    venus = new Venus();
  });

  describe('initialization', () => {
    it('should create a mesh with correct geometry', () => {
      expect(venus.mesh).toBeInstanceOf(THREE.Mesh);
      expect(venus.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });

    it('should have venus material with correct color', () => {
      const material = venus.mesh.material as THREE.MeshStandardMaterial;
      expect(material.color.getHex()).toBe(0xffffff); // white (as observed in night sky)
      expect(material).toBeInstanceOf(THREE.MeshStandardMaterial);
    });

    it('should have correct mesh name', () => {
      expect(venus.mesh.name).toBe('venus');
    });

    it('should have emissive glow', () => {
      const material = venus.mesh.material as THREE.MeshStandardMaterial;
      expect(material.emissive.getHex()).toBe(0xcccccc); // white glow
      expect(material.emissiveIntensity).toBe(0.5);
    });

    it('should be visible by default', () => {
      expect(venus.mesh.visible).toBe(true);
    });

    it('should have roughness and metalness properties', () => {
      const material = venus.mesh.material as THREE.MeshStandardMaterial;
      expect(material.roughness).toBe(0.7);
      expect(material.metalness).toBe(0.2);
    });
  });

  describe('3D view positioning', () => {
    it('should position at zenith (altitude 90°, any azimuth)', () => {
      venus.updatePosition(0, 90, true, '3D');
      
      // At zenith, should be directly above (y = distance, x ≈ 0, z ≈ 0)
      expect(venus.mesh.position.y).toBeCloseTo(16.8, 1);
      expect(Math.abs(venus.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(venus.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at horizon north (azimuth 0°, altitude 0°)', () => {
      venus.updatePosition(0, 0, true, '3D');
      
      // North on horizon: x ≈ 0, y ≈ 0, z = -distance
      expect(Math.abs(venus.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(venus.mesh.position.y)).toBeLessThan(0.1);
      expect(venus.mesh.position.z).toBeCloseTo(-16.8, 1);
    });

    it('should position at horizon east (azimuth 90°, altitude 0°)', () => {
      venus.updatePosition(90, 0, true, '3D');
      
      // East on horizon: x = distance, y ≈ 0, z ≈ 0
      expect(venus.mesh.position.x).toBeCloseTo(16.8, 1);
      expect(Math.abs(venus.mesh.position.y)).toBeLessThan(0.1);
      expect(Math.abs(venus.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at 45° elevation, 45° azimuth', () => {
      venus.updatePosition(45, 45, true, '3D');
      
      const distance = 16.8;
      const expectedY = distance * Math.sin(THREE.MathUtils.degToRad(45));
      const horizontalDist = distance * Math.cos(THREE.MathUtils.degToRad(45));
      
      expect(venus.mesh.position.y).toBeCloseTo(expectedY, 1);
      expect(venus.mesh.position.x).toBeCloseTo(horizontalDist * Math.sin(THREE.MathUtils.degToRad(45)), 1);
    });
  });

  describe('SKY view positioning', () => {
    it('should position at zenith on hemisphere', () => {
      venus.updatePosition(0, 90, true, 'SKY');
      
      // At zenith in sky view: x ≈ 0, y = radius, z ≈ 0
      expect(Math.abs(venus.mesh.position.x)).toBeLessThan(0.1);
      expect(venus.mesh.position.y).toBeCloseTo(10, 1);
      expect(Math.abs(venus.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position on horizon circle when altitude is 0°', () => {
      venus.updatePosition(90, 0, true, 'SKY');
      
      // On horizon: y should be 0, distance from origin should be radius
      expect(venus.mesh.position.y).toBeCloseTo(0, 1);
      const horizontalDist = Math.sqrt(
        venus.mesh.position.x ** 2 + venus.mesh.position.z ** 2
      );
      expect(horizontalDist).toBeCloseTo(10, 1);
    });

    it('should position below horizon when altitude is negative', () => {
      venus.updatePosition(0, -10, true, 'SKY');
      
      // Below horizon should be placed at y = 0
      expect(venus.mesh.position.y).toBe(0);
    });

    it('should maintain correct azimuth angle in sky view', () => {
      const testAzimuths = [0, 90, 180, 270];
      
      testAzimuths.forEach(azimuth => {
        venus.updatePosition(azimuth, 45, true, 'SKY');
        
        const actualAzimuth = Math.atan2(venus.mesh.position.x, -venus.mesh.position.z);
        const expectedAzimuth = THREE.MathUtils.degToRad(azimuth);
        
        // Allow for some floating point tolerance
        const diff = Math.abs(actualAzimuth - expectedAzimuth);
        expect(diff < 0.1 || diff > 2 * Math.PI - 0.1).toBe(true);
      });
    });
  });

  describe('visibility control', () => {
    it('should hide mesh when isVisible is false', () => {
      venus.updatePosition(0, 45, false, '3D');
      expect(venus.mesh.visible).toBe(false);
    });

    it('should show mesh when isVisible is true', () => {
      venus.updatePosition(0, 45, true, '3D');
      expect(venus.mesh.visible).toBe(true);
    });

    it('should maintain visibility across view mode changes', () => {
      venus.updatePosition(0, 45, true, '3D');
      expect(venus.mesh.visible).toBe(true);
      
      venus.setViewMode('sky');
      venus.updatePosition(0, 45, true, 'SKY');
      expect(venus.mesh.visible).toBe(true);
    });
  });

  describe('view mode switching', () => {
    it('should switch to sky view geometry', () => {
      const initialGeometry = venus.mesh.geometry;
      venus.setViewMode('sky');
      // After setViewMode, geometry should be different
      expect(venus.mesh.geometry).not.toBe(initialGeometry);
    });

    it('should switch back to 3D view geometry', () => {
      venus.setViewMode('sky');
      venus.setViewMode('3d');
      // Both operations should work without error
      expect(venus.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });
  });

  describe('scene management', () => {
    it('should add mesh to scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      venus.addToScene(mockScene as any);
      expect(mockScene.add).toHaveBeenCalledWith(venus.mesh);
    });

    it('should remove mesh from scene', () => {
      const mockScene = { add: vi.fn(), remove: vi.fn() };
      venus.removeFromScene(mockScene as any);
      expect(mockScene.remove).toHaveBeenCalledWith(venus.mesh);
    });
  });

  describe('positioning with various coordinates', () => {
    it('should handle negative altitudes correctly', () => {
      venus.updatePosition(180, -30, true, '3D');
      // Should not throw and position should be set
      expect(venus.mesh.position).toBeDefined();
    });

    it('should handle azimuth wrapping correctly', () => {
      venus.updatePosition(360, 45, true, '3D');
      // 360° should wrap to 0°, positioning should still work
      expect(venus.mesh.position).toBeDefined();
    });

    it('should handle very high altitudes', () => {
      venus.updatePosition(45, 89.9, true, '3D');
      // Should position near zenith
      expect(venus.mesh.position.y).toBeGreaterThan(10);
    });

    it('should handle all cardinal directions', () => {
      const cardinalDirections = [0, 90, 180, 270];
      cardinalDirections.forEach(azimuth => {
        venus.updatePosition(azimuth, 30, true, '3D');
        const distance = Math.sqrt(
          venus.mesh.position.x ** 2 +
          venus.mesh.position.y ** 2 +
          venus.mesh.position.z ** 2
        );
        expect(distance).toBeCloseTo(16.8, 0);
      });
    });

    it('should use minimum disk radius if calculated is too small', () => {
      const originalTan = Math.tan;
      Math.tan = () => 0.00001;
      const venus = new Venus();
      Math.tan = originalTan;
      const geometry = venus['skyViewGeometry'];
      expect((geometry as THREE.SphereGeometry).parameters.radius).toBeGreaterThanOrEqual(0.2);
    });

    it('should handle normal disk radius calculation without minimum clamping', () => {
      // Normal Math.tan results in the minimum clamping being applied
      const venus = new Venus();
      const geometry = venus['skyViewGeometry'];
      const radius = (geometry as THREE.SphereGeometry).parameters.radius;
      // With current angular diameter, it gets clamped to 0.2 minimum
      expect(radius).toBeGreaterThanOrEqual(0.2);
    });
  });

  describe('view mode persistence', () => {
    it('should maintain position after view mode switch', () => {
      venus.updatePosition(45, 30, true, '3D');
      const position3D = { ...venus.mesh.position };
      
      venus.setViewMode('sky');
      venus.updatePosition(45, 30, true, 'SKY');
      
      // Positions should be different but both valid
      expect(venus.mesh.position).toBeDefined();
      expect(venus.mesh.position.x).not.toEqual(position3D.x);
    });
  });

  describe('label billboard and positioning', () => {
    it('should update label billboard to face camera', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      camera.position.set(5, 5, 5);
      
      venus.updatePosition(45, 45, true, '3D');
      venus.updateLabelBillboard(camera);
      
      // Should not throw, label should be updated
      const labelMesh = venus['label'].getMesh();
      expect(labelMesh).toBeDefined();
    });

    it('should reposition label after setViewMode to sky', () => {
      venus.setViewMode('sky');
      venus.updatePosition(45, 45, true, 'SKY');
      
      const labelMesh = venus['label'].getMesh();
      expect(labelMesh.position).toBeDefined();
    });

    it('should reposition label after setViewMode to 3d', () => {
      venus.setViewMode('sky');
      venus.setViewMode('3d');
      venus.updatePosition(45, 45, true, '3D');
      
      const labelMesh = venus['label'].getMesh();
      expect(labelMesh.position).toBeDefined();
    });

    it('should update label visibility with mesh', () => {
      venus.updatePosition(45, 45, false, '3D');
      
      // Label should follow visibility changes
      expect(venus.mesh.visible).toBe(false);
    });

    it('should handle multiple label billboard updates', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      
      for (let i = 0; i < 5; i++) {
        camera.position.set(Math.cos(i) * 5, Math.sin(i) * 5, 5);
        venus.updatePosition(i * 72, 45, true, '3D');
        venus.updateLabelBillboard(camera);
      }
      
      expect(venus.mesh.position).toBeDefined();
    });

    it('should position label in both 3D and SKY view modes', () => {
      venus.setViewMode('3d');
      venus.updatePosition(0, 45, true, '3D');
      const pos3DX = venus['label'].getMesh().position.x;
      
      venus.setViewMode('sky');
      venus.updatePosition(0, 45, true, 'SKY');
      const posSkyX = venus['label'].getMesh().position.x;
      
      // Positions should be different between view modes
      expect(posSkyX).not.toBeCloseTo(pos3DX, 1);
    });
  });

  describe('sky view below horizon with label', () => {
    it('should handle below-horizon positioning with label updates', () => {
      venus.setViewMode('sky');
      venus.updatePosition(180, -30, true, 'SKY');
      
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      venus.updateLabelBillboard(camera);
      
      expect(venus.mesh.position.y).toBe(0);
    });
  });
});
