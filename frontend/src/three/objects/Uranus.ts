import * as THREE from 'three';
import { Label3D } from './Label3D';

/**
 * Uranus object for the scene
 * Radius 1.19 scene units (25362 km / 6371 km × 0.3 ≈ 1.19) - uncompressed, same formula as rocky planets
 * 3D orbit distance 192 — beyond Saturn (95)
 * Color: Cyan/turquoise (#4FD0E7) - methane atmosphere
 */
export class Uranus {
  public mesh: THREE.Mesh;
  private skyViewGeometry: THREE.SphereGeometry;
  private defaultGeometry: THREE.SphereGeometry;
  private label: Label3D;
  private labelOffset: number = 1.5;

  constructor() {
    // 3D view: proportional to Earth (25362 km / 6371 km × 0.3 ≈ 1.19)
    this.defaultGeometry = new THREE.SphereGeometry(1.19, 32, 32);
    // Sky view: Uranus's angular diameter (~4.1 arcsec max) requires reasonable size
    const domeRadius = 10;
    const uranusAngularDiameterRad = 0.0000199; // ~4.1 arcsec max in radians
    let uranusDiskRadius = domeRadius * Math.tan(uranusAngularDiameterRad / 2) * 4;
    if (uranusDiskRadius < 0.2) uranusDiskRadius = 0.2;
    this.skyViewGeometry = new THREE.SphereGeometry(uranusDiskRadius, 32, 32);

    // Uranus cyan/turquoise color - methane atmosphere (#4FD0E7)
    const material = new THREE.MeshStandardMaterial({
      color: 0x4fd0e7, // Uranus cyan/turquoise
      roughness: 0.8,
      metalness: 0.1,
    });
    this.mesh = new THREE.Mesh(this.defaultGeometry, material);
    this.mesh.name = 'uranus';

    this.label = new Label3D('Uranus', {
      fontSize: 32,
      fontColor: '#4fd0e7',
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
      this.labelOffset = 1.5;
      this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    }
  }

  public updatePosition(azimuth: number, altitude: number, isVisible: boolean = true, viewMode: '3D' | 'SKY' = '3D'): void {
    const azimuthRad = THREE.MathUtils.degToRad(azimuth);
    const altitudeRad = THREE.MathUtils.degToRad(altitude);

    if (viewMode === '3D') {
      // Distance scaled with square root compression: √(19.2² × 100) ≈ 192 (Sun-Uranus AU scaled)
      const distance = 192;
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
