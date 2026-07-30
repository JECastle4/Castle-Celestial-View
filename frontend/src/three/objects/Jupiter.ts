import * as THREE from 'three';
import { Label3D } from './Label3D';

/**
 * Jupiter object for the scene
 * Radius 3.3 scene units (69911 km / 6371 km × 0.3 ≈ 3.3) - uncompressed, same formula as rocky planets
 * 3D orbit distance 52 — beyond Mars (25.4)
 * Color: Golden/tan (#C88B3A) - cloud bands
 */
export class Jupiter {
  public mesh: THREE.Mesh;
  private skyViewGeometry: THREE.SphereGeometry;
  private defaultGeometry: THREE.SphereGeometry;
  private label: Label3D;
  private labelOffset: number = 4.3;

  constructor() {
    // 3D view: proportional to Earth (69911 km / 6371 km × 0.3 ≈ 3.3)
    this.defaultGeometry = new THREE.SphereGeometry(3.3, 32, 32);
    // Sky view: Jupiter's angular diameter (~50 arcsec max) requires reasonable size
    const domeRadius = 10;
    const jupiterAngularDiameterRad = 0.0002423; // ~50 arcsec max in radians
    let jupiterDiskRadius = domeRadius * Math.tan(jupiterAngularDiameterRad / 2) * 4;
    if (jupiterDiskRadius < 0.2) jupiterDiskRadius = 0.2;
    this.skyViewGeometry = new THREE.SphereGeometry(jupiterDiskRadius, 32, 32);

    // Jupiter golden/tan color - distinctive cloud bands (#C88B3A)
    const material = new THREE.MeshStandardMaterial({
      color: 0xc88b3a, // Jupiter golden/tan
      roughness: 0.8,
      metalness: 0.1,
    });
    this.mesh = new THREE.Mesh(this.defaultGeometry, material);
    this.mesh.name = 'jupiter';

    this.label = new Label3D('Jupiter', {
      fontSize: 32,
      fontColor: '#c88b3a',
      width: 128,
      height: 64,
    });
    this.label.setVisible(false);
  }

  setViewMode(mode: '3d' | 'sky') {
    if (mode === 'sky') {
      this.mesh.geometry = this.skyViewGeometry;
      this.labelOffset = 0.3;
      this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    } else {
      this.mesh.geometry = this.defaultGeometry;
      this.labelOffset = 4.3;
      this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    }
  }

  public updatePosition(azimuth: number, altitude: number, isVisible: boolean = true, viewMode: '3D' | 'SKY' = '3D'): void {
    const azimuthRad = THREE.MathUtils.degToRad(azimuth);
    const altitudeRad = THREE.MathUtils.degToRad(altitude);

    if (viewMode === '3D') {
      // Distance scaled with square root compression: √(5.2² × 100) ≈ 52 (Sun-Jupiter AU scaled)
      const distance = 52;
      this.mesh.position.x = distance * Math.cos(altitudeRad) * Math.sin(azimuthRad);
      this.mesh.position.y = distance * Math.sin(altitudeRad);
      this.mesh.position.z = -distance * Math.cos(altitudeRad) * Math.cos(azimuthRad);
    } else {
      const radius = 10;
      if (altitude < 0) {
        this.mesh.position.y = 0;
        this.mesh.position.x = radius * Math.sin(azimuthRad);
        this.mesh.position.z = -radius * Math.cos(azimuthRad);
      } else {
        const horizontalDistance = radius * Math.cos(altitudeRad);
        this.mesh.position.x = horizontalDistance * Math.sin(azimuthRad);
        this.mesh.position.y = radius * Math.sin(altitudeRad);
        this.mesh.position.z = -horizontalDistance * Math.cos(azimuthRad);
      }
    }

    this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    this.mesh.visible = isVisible;
    this.label.setVisible(isVisible);
  }

  public updateLabelBillboard(camera: THREE.Camera): void {
    this.label.updateBillboard(camera);
  }

  public addToScene(scene: THREE.Scene): void {
    scene.add(this.mesh);
    scene.add(this.label.getMesh());
  }

  public removeFromScene(scene: THREE.Scene): void {
    scene.remove(this.mesh);
    scene.remove(this.label.getMesh());
    this.label.dispose();
  }

  public dispose(): void {
    // Dispose the geometry not currently in the mesh
    if (this.mesh.geometry === this.defaultGeometry) {
      this.skyViewGeometry.dispose();
    } else {
      this.defaultGeometry.dispose();
    }
    // Dispose the geometry currently in the mesh
    this.mesh.geometry.dispose();
    (this.mesh.material as THREE.Material).dispose();
    this.label.dispose();
  }
}
