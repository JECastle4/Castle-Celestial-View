import * as THREE from 'three';
import { Label3D } from './Label3D';

/**
 * Venus object for the scene
 */
export class Venus {
  public mesh: THREE.Mesh;
  private skyViewGeometry: THREE.SphereGeometry;
  private defaultGeometry: THREE.SphereGeometry;
  private label: Label3D;
  private labelOffset: number = 0.35; // Current label offset based on view mode

  constructor() {
    // Default size for 3D view (95% of Earth's radius, slightly smaller)
    this.defaultGeometry = new THREE.SphereGeometry(0.275, 32, 32);
    // Sky view size (exaggerated for visibility)
    const domeRadius = 10;
    const venusAngularDiameterRad = 0.008; // ~0.45 degrees in radians
    let venusDiskRadius = domeRadius * Math.tan(venusAngularDiameterRad / 2) * 4; // exaggerate by 4x
    if (venusDiskRadius < 0.2) venusDiskRadius = 0.2;
    this.skyViewGeometry = new THREE.SphereGeometry(venusDiskRadius, 32, 32);
    // Venus is brightest planet - white/pale yellow color
    const material = new THREE.MeshStandardMaterial({ 
      color: 0xffffff,  // white (as observed in night sky)
      roughness: 0.7, 
      metalness: 0.2,
      emissive: 0xcccccc,  // slight emissive glow for visibility
      emissiveIntensity: 0.5
    });
    this.mesh = new THREE.Mesh(this.defaultGeometry, material);
    this.mesh.name = 'venus';
    
    // Create label
    this.label = new Label3D('Venus', {
      fontSize: 32,
      fontColor: '#ffffff',
      width: 128,
      height: 64,
    });
    // Initialize label as hidden until first updatePosition sets it based on real data
    this.label.setVisible(false);
  }

  setViewMode(mode: '3d' | 'sky') {
    if (mode === 'sky') {
      this.mesh.geometry = this.skyViewGeometry;
      // Position label closer to venus in sky view (smaller sphere)
      this.labelOffset = 0.3;
      this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    } else {
      this.mesh.geometry = this.defaultGeometry;
      // Position label farther in 3D view (larger sphere)
      this.labelOffset = 0.35;
      this.label.positionRelativeTo(this.mesh.position, this.labelOffset);
    }
  }

  /**
   * Update Venus position based on spherical coordinates
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
      const distance = 11;
      this.mesh.position.x = distance * Math.cos(altitudeRad) * Math.sin(azimuthRad);
      this.mesh.position.y = distance * Math.sin(altitudeRad);
      this.mesh.position.z = -distance * Math.cos(altitudeRad) * Math.cos(azimuthRad);
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
}
