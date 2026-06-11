import * as THREE from 'three';
import { Label3D } from './Label3D';

/**
 * Mercury object for the scene.
 * Radius 0.115 scene units (2440 / 6371 × Earth's 0.3).
 * 3D orbit distance 10 — between Moon (8) and Venus (11).
 */
export class Mercury {
  public mesh: THREE.Mesh;
  private skyViewGeometry: THREE.SphereGeometry;
  private defaultGeometry: THREE.SphereGeometry;
  private label: Label3D;
  private labelOffset: number = 0.2;

  constructor() {
    // 3D view: proportional to Earth (2440 km / 6371 km × 0.3)
    this.defaultGeometry = new THREE.SphereGeometry(0.115, 32, 32);
    // Sky view: Mercury's angular diameter (~13 arcsec max) is well below the 0.2 floor
    const domeRadius = 10;
    const mercuryAngularDiameterRad = 0.000063;
    let mercuryDiskRadius = domeRadius * Math.tan(mercuryAngularDiameterRad / 2) * 4;
    if (mercuryDiskRadius < 0.2) mercuryDiskRadius = 0.2;
    this.skyViewGeometry = new THREE.SphereGeometry(mercuryDiskRadius, 32, 32);
    // Dark grey — low-albedo rocky surface, visually distinct from Moon's lighter grey
    const material = new THREE.MeshStandardMaterial({
      color: 0x909090,
      roughness: 0.9,
      metalness: 0.1,
    });
    this.mesh = new THREE.Mesh(this.defaultGeometry, material);
    this.mesh.name = 'mercury';

    this.label = new Label3D('Mercury', {
      fontSize: 32,
      fontColor: '#909090',
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
      this.labelOffset = 0.2;
      this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    }
  }

  public updatePosition(azimuth: number, altitude: number, isVisible: boolean = true, viewMode: '3D' | 'SKY' = '3D'): void {
    const azimuthRad = THREE.MathUtils.degToRad(azimuth);
    const altitudeRad = THREE.MathUtils.degToRad(altitude);

    if (viewMode === '3D') {
      // Distance scaled with square root compression: √150.6 ≈ 12.3 (Sun-Mercury AU scaled)
      const distance = 12.3;
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
}
