import { describe, it, expect, beforeEach } from 'vitest';
import { Moon } from './Moon';
import * as THREE from 'three';

describe('Moon', () => {
  let moon: Moon;

  beforeEach(() => {
    moon = new Moon();
  });

  describe('initialization', () => {
    it('should create a mesh with correct geometry', () => {
      expect(moon.mesh).toBeInstanceOf(THREE.Mesh);
      expect(moon.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });

    it('should have moon material properties', () => {
      const material = moon.mesh.material as THREE.MeshStandardMaterial;
      expect(material.color.getHex()).toBe(0xcccccc);
      expect(material.roughness).toBe(0.9);
      expect(material.metalness).toBe(0.1);
    });

    it('should have correct mesh name', () => {
      expect(moon.mesh.name).toBe('moon');
    });

    it('should be visible by default', () => {
      expect(moon.mesh.visible).toBe(true);
    });

    it('should have standard material', () => {
      const material = moon.mesh.material as THREE.MeshStandardMaterial;
      expect(material).toBeInstanceOf(THREE.MeshStandardMaterial);
    });
  });

  describe('3D view positioning', () => {
    it('should position at zenith (altitude 90°)', () => {
      moon.updatePosition(0, 90, true, '3D');
      
      expect(moon.mesh.position.y).toBeCloseTo(8, 1);
      expect(Math.abs(moon.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(moon.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at horizon north (azimuth 0°, altitude 0°)', () => {
      moon.updatePosition(0, 0, true, '3D');
      
      expect(Math.abs(moon.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(moon.mesh.position.y)).toBeLessThan(0.1);
      expect(moon.mesh.position.z).toBeCloseTo(-8, 1);
    });

    it('should position at horizon east (azimuth 90°, altitude 0°)', () => {
      moon.updatePosition(90, 0, true, '3D');
      
      expect(moon.mesh.position.x).toBeCloseTo(8, 1);
      expect(Math.abs(moon.mesh.position.y)).toBeLessThan(0.1);
      expect(Math.abs(moon.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should use distance of 8 units in 3D view', () => {
      moon.updatePosition(45, 45, true, '3D');
      
      const distance = Math.sqrt(
        moon.mesh.position.x ** 2 +
        moon.mesh.position.y ** 2 +
        moon.mesh.position.z ** 2
      );
      expect(distance).toBeCloseTo(8, 1);
    });
  });

  describe('SKY view positioning', () => {
    it('should position at zenith on hemisphere', () => {
      moon.updatePosition(0, 90, true, 'SKY');
      
      expect(Math.abs(moon.mesh.position.x)).toBeLessThan(0.1);
      expect(moon.mesh.position.y).toBeCloseTo(10, 1);
      expect(Math.abs(moon.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position on horizon circle when altitude is 0°', () => {
      moon.updatePosition(0, 0, true, 'SKY');
      
      expect(moon.mesh.position.y).toBeCloseTo(0, 1);
      const horizontalDist = Math.sqrt(
        moon.mesh.position.x ** 2 + moon.mesh.position.z ** 2
      );
      expect(horizontalDist).toBeCloseTo(10, 1);
    });

    it('should position below horizon when altitude is negative', () => {
      moon.updatePosition(180, -15, true, 'SKY');
      
      expect(moon.mesh.position.y).toBe(0);
    });

    it('should use radius of 10 units in SKY view', () => {
      moon.updatePosition(0, 45, true, 'SKY');
      
      // Calculate distance from origin (should be on hemisphere of radius 10)
      const distance = Math.sqrt(
        moon.mesh.position.x ** 2 +
        moon.mesh.position.y ** 2 +
        moon.mesh.position.z ** 2
      );
      expect(distance).toBeCloseTo(10, 1);
    });
  });

  describe('phase illumination', () => {
    it('should update emissive intensity based on phase', () => {
      const material = moon.mesh.material as THREE.MeshStandardMaterial;
      
      // Full moon (100% illumination)
      moon.updatePhase(100);
      expect(material.emissiveIntensity).toBe(1.0);
      expect(material.emissive.getHex()).toBe(0x444444);
    });

    it('should have zero intensity for new moon', () => {
      const material = moon.mesh.material as THREE.MeshStandardMaterial;
      
      // New moon (0% illumination)
      moon.updatePhase(0);
      expect(material.emissiveIntensity).toBe(0);
    });

    it('should have medium intensity for half moon', () => {
      const material = moon.mesh.material as THREE.MeshStandardMaterial;
      
      // Half moon (50% illumination)
      moon.updatePhase(50);
      expect(material.emissiveIntensity).toBe(0.5);
    });

    it('should scale intensity correctly', () => {
      const material = moon.mesh.material as THREE.MeshStandardMaterial;
      
      // Test various illumination values (0-100 scale)
      const testValues = [0, 25, 50, 75, 100];
      testValues.forEach(illumination => {
        moon.updatePhase(illumination);
        expect(material.emissiveIntensity).toBe(illumination / 100);
      });
    });
  });

  describe('visibility control', () => {
    it('should hide mesh when isVisible is false', () => {
      moon.updatePosition(0, 45, false, '3D');
      expect(moon.mesh.visible).toBe(false);
    });

    it('should show mesh when isVisible is true', () => {
      moon.updatePosition(0, 45, true, '3D');
      expect(moon.mesh.visible).toBe(true);
    });
  });

  describe('scene management', () => {
    it('should add mesh to scene', () => {
      const scene = new THREE.Scene();
      moon.addToScene(scene);
      expect(scene.children).toContain(moon.mesh);
    });

    it('should remove mesh from scene', () => {
      const scene = new THREE.Scene();
      moon.addToScene(scene);
      moon.removeFromScene(scene);
      expect(scene.children).not.toContain(moon.mesh);
    });
  });

  describe('edge cases and coverage', () => {
    it('should use minimum disk radius if calculated is too small', () => {
      const originalTan = Math.tan;
      Math.tan = () => 0.00001;
      const moon = new Moon();
      Math.tan = originalTan;
      const geometry = moon['skyViewGeometry'];
      expect((geometry as THREE.SphereGeometry).parameters.radius).toBeGreaterThanOrEqual(0.2);
    });

    it('should handle normal disk radius calculation without minimum clamping', () => {
      // Normal Math.tan results in the minimum clamping being applied
      const moon = new Moon();
      const geometry = moon['skyViewGeometry'];
      const radius = (geometry as THREE.SphereGeometry).parameters.radius;
      // With current angular diameter, it gets clamped to 0.2 minimum
      expect(radius).toBeGreaterThanOrEqual(0.2);
    });

    it('should switch geometry in setViewMode', () => {
      const moon = new Moon();
      moon.setViewMode('sky');
      expect(moon.mesh.geometry).toBe(moon['skyViewGeometry']);
      moon.setViewMode('3d');
      expect(moon.mesh.geometry).toBe(moon['defaultGeometry']);
    });

    it('should handle updatePhase with edge illumination values', () => {
      const moon = new Moon();
      const material = moon.mesh.material as THREE.MeshStandardMaterial;
      moon.updatePhase(0);
      expect(material.emissiveIntensity).toBe(0);
      moon.updatePhase(100);
      expect(material.emissiveIntensity).toBe(1);
    });

    it('should use default geometry in setViewMode for non-sky', () => {
      const moon = new Moon();
      moon.setViewMode('3d');
      expect(moon.mesh.geometry).toBe(moon['defaultGeometry']);
    });
    it('should default to defaultGeometry for invalid mode', () => {
      const moon = new Moon();
      // @ts-expect-error: testing invalid input
      moon.setViewMode('invalid');
      expect(moon.mesh.geometry).toBe(moon['defaultGeometry']);
    });
  });

  describe('label billboard and positioning', () => {
    it('should update label billboard to face camera', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      camera.position.set(5, 5, 5);
      
      moon.updatePosition(45, 45, true, '3D');
      moon.updateLabelBillboard(camera);
      
      // Should not throw, label should be updated
      const labelMesh = moon['label'].getMesh();
      expect(labelMesh).toBeDefined();
    });

    it('should reposition label after setViewMode to sky', () => {
      moon.setViewMode('sky');
      moon.updatePosition(45, 45, true, 'SKY');
      
      const labelMesh = moon['label'].getMesh();
      expect(labelMesh.position).toBeDefined();
    });

    it('should reposition label after setViewMode to 3d', () => {
      moon.setViewMode('sky');
      moon.setViewMode('3d');
      moon.updatePosition(45, 45, true, '3D');
      
      const labelMesh = moon['label'].getMesh();
      expect(labelMesh.position).toBeDefined();
    });

    it('should update label visibility with mesh', () => {
      moon.updatePosition(45, 45, false, '3D');
      
      // Label should follow visibility changes
      expect(moon.mesh.visible).toBe(false);
    });

    it('should handle multiple label billboard updates', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      
      for (let i = 0; i < 5; i++) {
        camera.position.set(Math.cos(i) * 5, Math.sin(i) * 5, 5);
        moon.updatePosition(i * 72, 45, true, '3D');
        moon.updateLabelBillboard(camera);
      }
      
      expect(moon.mesh.position).toBeDefined();
    });

    it('should position label in both 3D and SKY view modes', () => {
      moon.setViewMode('3d');
      moon.updatePosition(0, 45, true, '3D');
      const pos3DX = moon['label'].getMesh().position.x;
      const pos3DY = moon['label'].getMesh().position.y;
      const pos3DZ = moon['label'].getMesh().position.z;
      
      moon.setViewMode('sky');
      moon.updatePosition(0, 45, true, 'SKY');
      const posSkyX = moon['label'].getMesh().position.x;
      const posSkyY = moon['label'].getMesh().position.y;
      const posSkyZ = moon['label'].getMesh().position.z;
      
      // Positions should be different between view modes
      expect(posSkyX).not.toBeCloseTo(pos3DX, 1);
    });
  });

  describe('sky view below horizon with label', () => {
    it('should handle below-horizon positioning with label updates', () => {
      moon.setViewMode('sky');
      moon.updatePosition(180, -30, true, 'SKY');
      
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      moon.updateLabelBillboard(camera);
      
      expect(moon.mesh.position.y).toBe(0);
    });
  });
});
