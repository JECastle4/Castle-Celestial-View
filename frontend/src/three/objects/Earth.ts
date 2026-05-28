import * as THREE from 'three';

/**
 * Earth (observer) representation at origin
 */
export class Earth {
  public mesh: THREE.Mesh;
  private gridHelper: THREE.GridHelper;
  private axesHelper: THREE.AxesHelper;
  private hemisphereGrid: THREE.Group;

  constructor() {
    // Create small earth at origin (observer position)
    const geometry = new THREE.SphereGeometry(0.3, 32, 32);
    const material = new THREE.MeshStandardMaterial({
      color: 0x2233ff,
      roughness: 0.7,
      metalness: 0.3,
    });

    this.mesh = new THREE.Mesh(geometry, material);
    this.mesh.name = 'earth';

    // Add grid helper to show ground plane
    this.gridHelper = new THREE.GridHelper(20, 20, 0x444444, 0x222222);
    this.gridHelper.position.y = -0.2;

    // Add axes helper for orientation
    this.axesHelper = new THREE.AxesHelper(2);
    
    // Create hemisphere grid for sky view
    this.hemisphereGrid = this.createHemisphereGrid();
    this.hemisphereGrid.visible = false;
  }
  
  private createHemisphereGrid(): THREE.Group {
    const group = new THREE.Group();
    const radius = 10;
    const segments = 24;
    
    // Create altitude circles (elevation rings)
    for (let alt = 0; alt <= 90; alt += 15) {
      const r = radius * Math.sin((90 - alt) * Math.PI / 180);
      const y = radius * Math.cos((90 - alt) * Math.PI / 180);
      
      const curve = new THREE.EllipseCurve(0, 0, r, r, 0, 2 * Math.PI, false, 0);
      const points = curve.getPoints(segments);
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const material = new THREE.LineBasicMaterial({ color: 0x444444 });
      const circle = new THREE.Line(geometry, material);
      circle.rotation.x = Math.PI / 2;
      circle.position.y = y;
      group.add(circle);
    }
    
    // Create azimuth lines (compass bearings)
    for (let az = 0; az < 360; az += 30) {
      const azRad = az * Math.PI / 180;
      const points = [];
      for (let alt = 0; alt <= 90; alt += 5) {
        const zenithAngle = (90 - alt) * Math.PI / 180;
        const r = radius * Math.sin(zenithAngle);
        const y = radius * Math.cos(zenithAngle);
        points.push(new THREE.Vector3(
          r * Math.sin(azRad),
          y,
          -r * Math.cos(azRad)
        ));
      }
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const material = new THREE.LineBasicMaterial({ color: 0x444444 });
      const line = new THREE.Line(geometry, material);
      group.add(line);
    }
    
    // Add horizon circle (emphasized)
    const horizonCurve = new THREE.EllipseCurve(0, 0, radius, radius, 0, 2 * Math.PI, false, 0);
    const horizonPoints = horizonCurve.getPoints(segments);
    const horizonGeometry = new THREE.BufferGeometry().setFromPoints(horizonPoints);
    const horizonMaterial = new THREE.LineBasicMaterial({ color: 0x888888, linewidth: 2 });
    const horizon = new THREE.Line(horizonGeometry, horizonMaterial);
    horizon.rotation.x = Math.PI / 2;
    group.add(horizon);
    
    return group;
  }

  public setViewMode(mode: '3D' | 'SKY'): void {
    if (mode === '3D') {
      this.mesh.visible = true;
      this.gridHelper.visible = true;
      this.axesHelper.visible = true;
      this.hemisphereGrid.visible = false;
    } else {
      this.mesh.visible = false;
      this.gridHelper.visible = false;
      this.axesHelper.visible = false;
      this.hemisphereGrid.visible = true;
    }
  }

  public addToScene(scene: THREE.Scene): void {
    scene.add(this.mesh);
    scene.add(this.gridHelper);
    scene.add(this.axesHelper);
    scene.add(this.hemisphereGrid);
  }

  public removeFromScene(scene: THREE.Scene): void {
    scene.remove(this.mesh);
    scene.remove(this.gridHelper);
    scene.remove(this.axesHelper);
    scene.remove(this.hemisphereGrid);
  }
  // Public getters for test access
  public getGridHelper(): THREE.GridHelper {
    return this.gridHelper;
  }
  public getAxesHelper(): THREE.AxesHelper {
    return this.axesHelper;
  }
  public getHemisphereGrid(): THREE.Group {
    return this.hemisphereGrid;
  }
}
