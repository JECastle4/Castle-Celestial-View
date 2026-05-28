import * as THREE from 'three';

/**
 * Moon object for the scene
 */
export class Moon {
  public mesh: THREE.Mesh;
  private skyViewGeometry: THREE.SphereGeometry;
  private defaultGeometry: THREE.SphereGeometry;

  constructor() {
    // Default size for 3D view
    this.defaultGeometry = new THREE.SphereGeometry(0.1, 32, 32);
    // Sky view size (exaggerated for visibility)
    const domeRadius = 10;
    const moonAngularDiameterRad = 0.009; // ~0.5 degrees in radians
    let moonDiskRadius = domeRadius * Math.tan(moonAngularDiameterRad / 2) * 4; // exaggerate by 4x
    if (moonDiskRadius < 0.2) moonDiskRadius = 0.2;
    this.skyViewGeometry = new THREE.SphereGeometry(moonDiskRadius, 32, 32);
    // Use MeshStandardMaterial for test compatibility
    const material = new THREE.MeshStandardMaterial({ color: 0xcccccc, roughness: 0.9, metalness: 0.1 });
    this.mesh = new THREE.Mesh(this.defaultGeometry, material);
    this.mesh.name = 'moon';
  }

  setViewMode(mode: '3d' | 'sky') {
    if (mode === 'sky') {
      this.mesh.geometry = this.skyViewGeometry;
    } else {
      this.mesh.geometry = this.defaultGeometry;
    }
  }

  /**
   * Update moon position based on spherical coordinates
   * Supports both 3D orbital view and sky hemisphere view
   */
  public updatePosition(azimuth: number, altitude: number, isVisible: boolean = true, viewMode: '3D' | 'SKY' = '3D'): void {
    // Convert azimuth/altitude to Three.js coordinates
    const azimuthRad = THREE.MathUtils.degToRad(azimuth);
    const altitudeRad = THREE.MathUtils.degToRad(altitude);

    if (viewMode === '3D') {
      // 3D orbital view: position around Earth center
      const distance = 8;
      this.mesh.position.x = distance * Math.cos(altitudeRad) * Math.sin(azimuthRad);
      this.mesh.position.y = distance * Math.sin(altitudeRad);
      this.mesh.position.z = -distance * Math.cos(altitudeRad) * Math.cos(azimuthRad); // restore original sign for test compatibility
    } else {
      // Sky view: project onto hemisphere above observer
      const radius = 10;
      
      if (altitude < 0) {
        // Below horizon - position at horizon level but mark invisible
        this.mesh.position.y = 0;
        this.mesh.position.x = radius * Math.sin(azimuthRad);
        this.mesh.position.z = -radius * Math.cos(azimuthRad);
      } else {
        // Above horizon - position on hemisphere
        const elevationRad = altitudeRad;
        const horizontalDistance = radius * Math.cos(elevationRad);
        
        this.mesh.position.x = horizontalDistance * Math.sin(azimuthRad);
        this.mesh.position.y = radius * Math.sin(elevationRad);
        this.mesh.position.z = -horizontalDistance * Math.cos(azimuthRad);
      }
    }
    
    // Update visibility
    this.mesh.visible = isVisible;
  }

  /**
   * Update moon phase appearance
   */
  public updatePhase(illumination: number): void {
    // Adjust brightness based on phase
    const material = this.mesh.material as THREE.MeshStandardMaterial;
    material.emissive = new THREE.Color(0x444444);
    material.emissiveIntensity = illumination / 100;
  }

  public addToScene(scene: THREE.Scene): void {
    scene.add(this.mesh);
  }

  public removeFromScene(scene: THREE.Scene): void {
    scene.remove(this.mesh);
  }
}
