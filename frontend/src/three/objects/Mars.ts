import * as THREE from 'three';
import { Label3D } from './Label3D';

/**
 * Mars object for the scene
 * Radius 0.15 scene units (3389.5 km / 6371 km × 0.3)
 * 3D orbit distance 25.4 — beyond Venus (16.8) and Mercury (12.3)
 * Color: Reddish (#E27B58) - distinctive iron oxide surface
 */
export class Mars {
  public mesh: THREE.Mesh;
  private skyViewGeometry: THREE.SphereGeometry;
  private defaultGeometry: THREE.SphereGeometry;
  private label: Label3D;
  private labelOffset: number = 0.25;

  constructor() {
    // 3D view: proportional to Earth (3389.5 km / 6371 km × 0.3 ≈ 0.16)
    this.defaultGeometry = new THREE.SphereGeometry(0.16, 32, 32);
    // Sky view: Mars's angular diameter (~25 arcsec max) requires reasonable size
    const domeRadius = 10;
    const marsAngularDiameterRad = 0.0001217; // ~25 arcsec max in radians
    let marsDiskRadius = domeRadius * Math.tan(marsAngularDiameterRad / 2) * 4;
    if (marsDiskRadius < 0.2) marsDiskRadius = 0.2;
    this.skyViewGeometry = new THREE.SphereGeometry(marsDiskRadius, 32, 32);

    // Mars red/rusty color - distinctive iron oxide surface (#E27B58)
    const material = new THREE.MeshStandardMaterial({
      color: 0xe27b58, // Mars red
      roughness: 0.8,
      metalness: 0.0,
    });
    this.mesh = new THREE.Mesh(this.defaultGeometry, material);
    this.mesh.name = 'mars';

    this.label = new Label3D('Mars', {
      fontSize: 32,
      fontColor: '#e27b58',
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
      this.labelOffset = 0.25;
      this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    }
  }

  public updatePosition(azimuth: number, altitude: number, isVisible: boolean = true, viewMode: '3D' | 'SKY' = '3D'): void {
    const azimuthRad = THREE.MathUtils.degToRad(azimuth);
    const altitudeRad = THREE.MathUtils.degToRad(altitude);

    if (viewMode === '3D') {
      // Distance scaled with square root compression: √645.6 ≈ 25.4 (Sun-Mars AU scaled)
      const distance = 25.4;
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
    this.defaultGeometry.dispose();
    this.skyViewGeometry.dispose();
    (this.mesh.material as THREE.Material).dispose();
    this.mesh.geometry.dispose();
    this.label.dispose();
  }
}
