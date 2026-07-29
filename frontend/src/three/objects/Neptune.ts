import * as THREE from 'three';
import { Label3D } from './Label3D';

/**
 * Neptune object for the scene
 * Radius 1.16 scene units (24622 km / 6371 km × 0.3 ≈ 1.16) - uncompressed, same formula as rocky planets
 * 3D orbit distance 301 — beyond Uranus (192)
 * Color: Deep blue (#4166F5) - methane atmosphere
 */
export class Neptune {
  public mesh: THREE.Mesh;
  private skyViewGeometry: THREE.SphereGeometry;
  private defaultGeometry: THREE.SphereGeometry;
  private label: Label3D;
  private labelOffset: number = 1.5;

  constructor() {
    // 3D view: proportional to Earth (24622 km / 6371 km × 0.3 ≈ 1.16)
    this.defaultGeometry = new THREE.SphereGeometry(1.16, 32, 32);
    // Sky view: Neptune's angular diameter (~2.4 arcsec max) requires reasonable size
    const domeRadius = 10;
    const neptuneAngularDiameterRad = 0.0000116; // ~2.4 arcsec max in radians
    let neptuneDiskRadius = domeRadius * Math.tan(neptuneAngularDiameterRad / 2) * 4;
    if (neptuneDiskRadius < 0.2) neptuneDiskRadius = 0.2;
    this.skyViewGeometry = new THREE.SphereGeometry(neptuneDiskRadius, 32, 32);

    // Neptune deep blue color - methane atmosphere (#4166F5)
    const material = new THREE.MeshStandardMaterial({
      color: 0x4166f5, // Neptune deep blue
      roughness: 0.8,
      metalness: 0.1,
    });
    this.mesh = new THREE.Mesh(this.defaultGeometry, material);
    this.mesh.name = 'neptune';

    this.label = new Label3D('Neptune', {
      fontSize: 32,
      fontColor: '#4166f5',
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
      // Distance scaled with square root compression: √(30.1² × 100) ≈ 301 (Sun-Neptune AU scaled)
      const distance = 301;
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
