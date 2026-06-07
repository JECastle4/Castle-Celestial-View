import * as THREE from 'three';
import { Label3D } from './Label3D';

/**
 * Sun object for the scene
 */
export class Sun {
  public mesh: THREE.Mesh;
  private light: THREE.PointLight;
  private skyViewGeometry: THREE.SphereGeometry;
  private defaultGeometry: THREE.SphereGeometry;
  private label: Label3D;
  private labelOffset: number = 5; // Current label offset based on view mode

  constructor() {
    // Default size for 3D view
    this.defaultGeometry = new THREE.SphereGeometry(4, 32, 32);
    // Sky view size (exaggerated for visibility)
    const domeRadius = 10;
    const sunAngularDiameterRad = 0.009; // ~0.5 degrees in radians
    let sunDiskRadius = domeRadius * Math.tan(sunAngularDiameterRad / 2) * 4; // exaggerate by 4x
    if (sunDiskRadius < 0.2) sunDiskRadius = 0.2;
    this.skyViewGeometry = new THREE.SphereGeometry(sunDiskRadius, 32, 32);
    const material = new THREE.MeshBasicMaterial({ color: 0xffdd44 });
    this.mesh = new THREE.Mesh(this.defaultGeometry, material);
    this.mesh.name = 'sun';
    this.light = new THREE.PointLight(0xffffdd, 2.0, 100);
    this.mesh.add(this.light);
    
    // Create label
    this.label = new Label3D('Sun', {
      fontSize: 32,
      fontColor: '#ffdd44',
      width: 128,
      height: 64,
    });
    // Initialize label as hidden until first updatePosition sets it based on real data
    this.label.setVisible(false);
  }

  setViewMode(mode: '3d' | 'sky') {
    if (mode === 'sky') {
      this.mesh.geometry = this.skyViewGeometry;
      // Position label closer to sun in sky view (smaller sphere)
      this.labelOffset = 0.3;
      this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    } else {
      this.mesh.geometry = this.defaultGeometry;
      // Position label farther in 3D view (larger sphere)
      this.labelOffset = 5;
      this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    }
  }

  /**
   * Update sun position based on spherical coordinates
   * Supports both 3D orbital view and sky hemisphere view
   */
  public updatePosition(azimuth: number, altitude: number, isVisible: boolean = true, viewMode: '3D' | 'SKY' = '3D'): void {
    // Convert azimuth/altitude to Three.js coordinates
    // Azimuth: 0° = North, 90° = East (clockwise from above)
    // Altitude: 0° = horizon, 90° = zenith
    
    const azimuthRad = THREE.MathUtils.degToRad(azimuth);
    const altitudeRad = THREE.MathUtils.degToRad(altitude);

    if (viewMode === '3D') {
      // 3D orbital view: position around Earth center
      const distance = 15;
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
        // Convert altitude to angle from horizon (0° = horizon, 90° = zenith)
        const elevationRad = altitudeRad;
        const horizontalDistance = radius * Math.cos(elevationRad);
        
        this.mesh.position.x = horizontalDistance * Math.sin(azimuthRad);
        this.mesh.position.y = radius * Math.sin(elevationRad);
        this.mesh.position.z = -horizontalDistance * Math.cos(azimuthRad);
      }
    }
    
    // Update label position to follow mesh
    this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    
    // Update visibility
    this.mesh.visible = isVisible;
    this.light.visible = isVisible;
    this.label.setVisible(isVisible);
  }

  /**
   * Update label billboard orientation to face camera
   */
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
  
  // Public getter for test access
  public getLight(): THREE.PointLight {
    return this.light;
  }
}
