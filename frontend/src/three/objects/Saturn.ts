import * as THREE from 'three';
import { Label3D } from './Label3D';

/**
 * Saturn object for the scene
 * Radius 2.84 scene units (58232 km / 6371 km × 0.3 ≈ 2.84) - uncompressed, same formula as rocky planets
 * 3D orbit distance 95 — beyond Jupiter (52)
 * Color: Pale gold (#F4D89F) - pale gold atmosphere
 */
export class Saturn {
  public mesh: THREE.Mesh;
  private skyViewGeometry: THREE.SphereGeometry;
  private defaultGeometry: THREE.SphereGeometry;
  private label: Label3D;
  private labelOffset: number = 3.7;

  constructor() {
    // 3D view: proportional to Earth (58232 km / 6371 km × 0.3 ≈ 2.84)
    this.defaultGeometry = new THREE.SphereGeometry(2.84, 32, 32);
    // Sky view: Saturn's angular diameter (~20 arcsec max, excluding rings) requires reasonable size
    const domeRadius = 10;
    const saturnAngularDiameterRad = 0.000097; // ~20 arcsec max in radians
    let saturnDiskRadius = domeRadius * Math.tan(saturnAngularDiameterRad / 2) * 4;
    if (saturnDiskRadius < 0.2) saturnDiskRadius = 0.2;
    this.skyViewGeometry = new THREE.SphereGeometry(saturnDiskRadius, 32, 32);

    // Saturn pale gold color - pale gold atmosphere (#F4D89F)
    const material = new THREE.MeshStandardMaterial({
      color: 0xf4d89f, // Saturn pale gold
      roughness: 0.8,
      metalness: 0.1,
    });
    this.mesh = new THREE.Mesh(this.defaultGeometry, material);
    this.mesh.name = 'saturn';

    this.label = new Label3D('Saturn', {
      fontSize: 32,
      fontColor: '#f4d89f',
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
      this.labelOffset = 3.7;
      this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    }
  }

  public updatePosition(azimuth: number, altitude: number, isVisible: boolean = true, viewMode: '3D' | 'SKY' = '3D'): void {
    const azimuthRad = THREE.MathUtils.degToRad(azimuth);
    const altitudeRad = THREE.MathUtils.degToRad(altitude);

    if (viewMode === '3D') {
      // Distance scaled with square root compression: √(9.5² × 100) ≈ 95 (Sun-Saturn AU scaled)
      const distance = 95;
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
