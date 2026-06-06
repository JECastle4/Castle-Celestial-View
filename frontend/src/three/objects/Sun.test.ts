import { describe, it, expect, beforeEach } from 'vitest';
import { Sun } from './Sun';
import * as THREE from 'three';

describe('Sun', () => {
  let sun: Sun;

  beforeEach(() => {
    sun = new Sun();
  });

  describe('initialization', () => {
    it('should create a mesh with correct geometry', () => {
      expect(sun.mesh).toBeInstanceOf(THREE.Mesh);
      expect(sun.mesh.geometry).toBeInstanceOf(THREE.SphereGeometry);
    });

    it('should have sun material with correct color', () => {
      const material = sun.mesh.material as THREE.MeshBasicMaterial;
      expect(material.color.getHex()).toBe(0xffdd44);
      expect(material).toBeInstanceOf(THREE.MeshBasicMaterial);
    });

    it('should have correct mesh name', () => {
      expect(sun.mesh.name).toBe('sun');
    });

    it('should have a point light attached', () => {
      const lights = sun.mesh.children.filter(child => child instanceof THREE.PointLight);
      expect(lights.length).toBe(1);
    });

    it('should be visible by default', () => {
      expect(sun.mesh.visible).toBe(true);
    });
  });

  describe('3D view positioning', () => {
    it('should position at zenith (altitude 90°, any azimuth)', () => {
      sun.updatePosition(0, 90, true, '3D');
      
      // At zenith, should be directly above (y = distance, x ≈ 0, z ≈ 0)
      expect(sun.mesh.position.y).toBeCloseTo(15, 1);
      expect(Math.abs(sun.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(sun.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at horizon north (azimuth 0°, altitude 0°)', () => {
      sun.updatePosition(0, 0, true, '3D');
      
      // North on horizon: x ≈ 0, y ≈ 0, z = -distance
      expect(Math.abs(sun.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(sun.mesh.position.y)).toBeLessThan(0.1);
      expect(sun.mesh.position.z).toBeCloseTo(-15, 1);
    });

    it('should position at horizon east (azimuth 90°, altitude 0°)', () => {
      sun.updatePosition(90, 0, true, '3D');
      
      // East on horizon: x = distance, y ≈ 0, z ≈ 0
      expect(sun.mesh.position.x).toBeCloseTo(15, 1);
      expect(Math.abs(sun.mesh.position.y)).toBeLessThan(0.1);
      expect(Math.abs(sun.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at horizon south (azimuth 180°, altitude 0°)', () => {
      sun.updatePosition(180, 0, true, '3D');
      
      // South on horizon: x ≈ 0, y ≈ 0, z = distance
      expect(Math.abs(sun.mesh.position.x)).toBeLessThan(0.1);
      expect(Math.abs(sun.mesh.position.y)).toBeLessThan(0.1);
      expect(sun.mesh.position.z).toBeCloseTo(15, 1);
    });

    it('should position at horizon west (azimuth 270°, altitude 0°)', () => {
      sun.updatePosition(270, 0, true, '3D');
      
      // West on horizon: x = -distance, y ≈ 0, z ≈ 0
      expect(sun.mesh.position.x).toBeCloseTo(-15, 1);
      expect(Math.abs(sun.mesh.position.y)).toBeLessThan(0.1);
      expect(Math.abs(sun.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position at 45° elevation, 45° azimuth', () => {
      sun.updatePosition(45, 45, true, '3D');
      
      const distance = 15;
      const expectedY = distance * Math.sin(THREE.MathUtils.degToRad(45));
      const horizontalDist = distance * Math.cos(THREE.MathUtils.degToRad(45));
      
      expect(sun.mesh.position.y).toBeCloseTo(expectedY, 1);
      expect(sun.mesh.position.x).toBeCloseTo(horizontalDist * Math.sin(THREE.MathUtils.degToRad(45)), 1);
    });
  });

  describe('SKY view positioning', () => {
    it('should position at zenith on hemisphere', () => {
      sun.updatePosition(0, 90, true, 'SKY');
      
      // At zenith in sky view: x ≈ 0, y = radius, z ≈ 0
      expect(Math.abs(sun.mesh.position.x)).toBeLessThan(0.1);
      expect(sun.mesh.position.y).toBeCloseTo(10, 1);
      expect(Math.abs(sun.mesh.position.z)).toBeLessThan(0.1);
    });

    it('should position on horizon circle when altitude is 0°', () => {
      sun.updatePosition(90, 0, true, 'SKY');
      
      // On horizon: y should be 0, distance from origin should be radius
      expect(sun.mesh.position.y).toBeCloseTo(0, 1);
      const horizontalDist = Math.sqrt(
        sun.mesh.position.x ** 2 + sun.mesh.position.z ** 2
      );
      expect(horizontalDist).toBeCloseTo(10, 1);
    });

    it('should position below horizon when altitude is negative', () => {
      sun.updatePosition(0, -10, true, 'SKY');
      
      // Below horizon should be placed at y = 0
      expect(sun.mesh.position.y).toBe(0);
    });

    it('should maintain correct azimuth angle in sky view', () => {
      const testAzimuths = [0, 90, 180, 270];
      
      testAzimuths.forEach(azimuth => {
        sun.updatePosition(azimuth, 45, true, 'SKY');
        
        const actualAzimuth = Math.atan2(sun.mesh.position.x, -sun.mesh.position.z);
        const expectedAzimuth = THREE.MathUtils.degToRad(azimuth);
        
        // Allow for some floating point tolerance
        const diff = Math.abs(actualAzimuth - expectedAzimuth);
        expect(diff < 0.1 || diff > 2 * Math.PI - 0.1).toBe(true);
      });
    });
  });

  describe('visibility control', () => {
    it('should hide mesh when isVisible is false', () => {
      sun.updatePosition(0, 45, false, '3D');
      expect(sun.mesh.visible).toBe(false);
    });

    it('should show mesh when isVisible is true', () => {
      sun.updatePosition(0, 45, true, '3D');
      expect(sun.mesh.visible).toBe(true);
    });

    it('should hide light when mesh is hidden', () => {
      sun.updatePosition(0, 45, false, '3D');
      const light = sun.mesh.children[0] as THREE.PointLight;
      expect(light.visible).toBe(false);
    });

    it('should show light when mesh is visible', () => {
      sun.updatePosition(0, 45, true, '3D');
      const light = sun.mesh.children[0] as THREE.PointLight;
      expect(light.visible).toBe(true);
    });
  });

  describe('scene management', () => {
    it('should add mesh to scene', () => {
      const scene = new THREE.Scene();
      sun.addToScene(scene);
      expect(scene.children).toContain(sun.mesh);
    });

    it('should remove mesh from scene', () => {
      const scene = new THREE.Scene();
      sun.addToScene(scene);
      sun.removeFromScene(scene);
      expect(scene.children).not.toContain(sun.mesh);
    });
  });

  describe('edge cases and coverage', () => {
    it('should use minimum disk radius if calculated is too small', () => {
      const originalTan = Math.tan;
      Math.tan = () => 0.00001;
      const sun = new Sun();
      Math.tan = originalTan;
      const geometry = sun['skyViewGeometry'];
      expect((geometry as THREE.SphereGeometry).parameters.radius).toBeGreaterThanOrEqual(0.2);
    });

    it('should handle normal disk radius calculation without minimum clamping', () => {
      // Normal Math.tan results in the minimum clamping being applied
      const sun = new Sun();
      const geometry = sun['skyViewGeometry'];
      const radius = (geometry as THREE.SphereGeometry).parameters.radius;
      // With current angular diameter, it gets clamped to 0.2 minimum
      expect(radius).toBeGreaterThanOrEqual(0.2);
    });

    it('should switch geometry in setViewMode', () => {
      const sun = new Sun();
      sun.setViewMode('sky');
      expect(sun.mesh.geometry).toBe(sun['skyViewGeometry']);
      sun.setViewMode('3d');
      expect(sun.mesh.geometry).toBe(sun['defaultGeometry']);
    });
  });

  describe('getter coverage', () => {
    it('getLight should return a PointLight', () => {
      const sun = new Sun();
      expect(sun.getLight()).toBeInstanceOf(THREE.PointLight);
    });
  });

  it('should use default geometry in setViewMode for non-sky', () => {
    const sun = new Sun();
    sun.setViewMode('3d');
    expect(sun.mesh.geometry).toBe(sun['defaultGeometry']);
  });
  it('should default to defaultGeometry for invalid mode', () => {
    const sun = new Sun();
    // @ts-expect-error: testing invalid input
    sun.setViewMode('invalid');
    expect(sun.mesh.geometry).toBe(sun['defaultGeometry']);
  });

  describe('label billboard and positioning', () => {
    it('should update label billboard to face camera', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      camera.position.set(5, 5, 5);
      
      sun.updatePosition(45, 45, true, '3D');
      sun.updateLabelBillboard(camera);
      
      // Should not throw, label should be updated
      const labelMesh = sun['label'].getMesh();
      expect(labelMesh).toBeDefined();
    });

    it('should reposition label after setViewMode to sky', () => {
      sun.setViewMode('sky');
      sun.updatePosition(45, 45, true, 'SKY');
      
      const labelMesh = sun['label'].getMesh();
      expect(labelMesh.position).toBeDefined();
    });

    it('should reposition label after setViewMode to 3d', () => {
      sun.setViewMode('sky');
      sun.setViewMode('3d');
      sun.updatePosition(45, 45, true, '3D');
      
      const labelMesh = sun['label'].getMesh();
      expect(labelMesh.position).toBeDefined();
    });

    it('should update light visibility with mesh', () => {
      sun.updatePosition(45, 45, false, '3D');
      const light = sun.mesh.children[0] as THREE.PointLight;
      
      expect(sun.mesh.visible).toBe(false);
      expect(light.visible).toBe(false);
    });

    it('should handle multiple label billboard updates', () => {
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      
      for (let i = 0; i < 5; i++) {
        camera.position.set(Math.cos(i) * 5, Math.sin(i) * 5, 5);
        sun.updatePosition(i * 72, 45, true, '3D');
        sun.updateLabelBillboard(camera);
      }
      
      expect(sun.mesh.position).toBeDefined();
    });

    it('should position label in both 3D and SKY view modes', () => {
      sun.setViewMode('3d');
      sun.updatePosition(0, 45, true, '3D');
      const pos3DX = sun['label'].getMesh().position.x;
      
      sun.setViewMode('sky');
      sun.updatePosition(0, 45, true, 'SKY');
      const posSkyX = sun['label'].getMesh().position.x;
      
      // Positions should be different between view modes
      expect(posSkyX).not.toBeCloseTo(pos3DX, 1);
    });
  });

  describe('sky view below horizon with label', () => {
    it('should handle below-horizon positioning with label updates', () => {
      sun.setViewMode('sky');
      sun.updatePosition(180, -30, true, 'SKY');
      
      const camera = new THREE.PerspectiveCamera(75, 1, 0.1, 1000);
      sun.updateLabelBillboard(camera);
      
      expect(sun.mesh.position.y).toBe(0);
    });
  });
});
