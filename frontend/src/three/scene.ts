import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

/**
 * Three.js Scene Manager for Astronomy Animation
 */
export class SceneManager {
  public scene: THREE.Scene;
  public camera: THREE.PerspectiveCamera;
  public renderer: THREE.WebGLRenderer;
  public controls: OrbitControls;
  
  private animationId: number | null = null;
  private animationCallback?: () => void;
  private currentViewMode: '3D' | 'SKY' = '3D';
  private resizeHandler: () => void;

  constructor(canvas: HTMLCanvasElement) {
    // Create scene
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x000011);

    // Create camera
    this.camera = new THREE.PerspectiveCamera(
      75,
      canvas.clientWidth / canvas.clientHeight,
      0.1,
      1000
    );
    this.camera.position.set(0, 7, 14);

    // Create renderer
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
    });
    this.renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

    // Create controls
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.05;
    this.controls.minDistance = 2;
    this.controls.maxDistance = 50;

    // Add basic lighting
    this.setupLighting();

    // Handle window resize - store bound function to allow proper cleanup
    this.resizeHandler = this.onWindowResize.bind(this);
    window.addEventListener('resize', this.resizeHandler);
  }
  
  /**
   * Reset the camera to its default position and orientation for the current view mode.
   */
  public resetCamera(): void {
    this.setViewMode(this.currentViewMode);
  }

  private setupLighting(): void {
    // Ambient light for general illumination
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    this.scene.add(ambientLight);

    // Directional light from sun position (will be updated)
    const sunLight = new THREE.DirectionalLight(0xffffff, 1.0);
    sunLight.position.set(10, 0, 0);
    sunLight.name = 'sunLight';
    this.scene.add(sunLight);
  }

  private onWindowResize(): void {
    const canvas = this.renderer.domElement;
    const parent = canvas.parentElement;
    // Debug logging for app, scene, and canvas sizes
    const appDiv = document.getElementById('app');
    const sceneDiv = parent;
    const debugLoggingEnabled = false; // set to true to enable debug logging
    if (debugLoggingEnabled) {
      console.log('[Resize Debug]');
      if (appDiv) {
        console.log('  #app:', appDiv.clientWidth, 'x', appDiv.clientHeight);
      }
      if (sceneDiv) {
        console.log('  .astronomy-scene:', sceneDiv.clientWidth, 'x', sceneDiv.clientHeight);
      }
      console.log('  canvas:', canvas.width, 'x', canvas.height);
    }
    // Dynamically set canvas size to match parent/container
    if (parent) {
      canvas.width = parent.clientWidth;
      canvas.height = parent.clientHeight;
    }
    // Update renderer and camera aspect
    this.camera.aspect = canvas.clientWidth / canvas.clientHeight;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(canvas.clientWidth, canvas.clientHeight);
    // If in SKY view, recalculate camera position and controls
    if (this.currentViewMode === 'SKY') {
      this.setViewMode('SKY');
    }
  }

  public startAnimation(callback?: () => void): void {
    this.animationCallback = callback;
    this.animate();
  }

  public stopAnimation(): void {
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }
  }

  private animate(): void {
    this.animationId = requestAnimationFrame(this.animate.bind(this));

    // Update controls
    this.controls.update();

    // Call custom animation callback
    if (this.animationCallback) {
      this.animationCallback();
    }

    // Render scene
    this.renderer.render(this.scene, this.camera);
  }
  
  public setViewMode(mode: '3D' | 'SKY'): void {
    this.currentViewMode = mode;

    if (mode === '3D') {
      // 3D orbital view
      this.camera.position.set(0, 7, 14); // restore original camera position
      this.controls.target.set(0, 0, 0);
      this.controls.minDistance = 2;
      this.controls.maxDistance = 50;
      this.scene.background = new THREE.Color(0x000011);
      this.controls.update();
    } else {
      // Sky view: camera below dome, looking up, so full 360° dome is visible (responsive)
      const domeRadius = 30; // adjust if your dome is a different size
      const domeHeight = domeRadius; // for a hemisphere centered at (0, domeRadius, 0)
      const canvas = this.renderer.domElement;
      const aspect = canvas.clientWidth / canvas.clientHeight;
      const verticalFovRad = this.camera.fov * Math.PI / 180;
      const horizontalFovRad = 2 * Math.atan(Math.tan(verticalFovRad / 2) * aspect);
      const limitingFov = Math.min(verticalFovRad, horizontalFovRad);
      let distance = domeRadius / Math.tan(limitingFov / 2);
      distance *= 1.1; // safety margin

      var loggingEnabled = false; // set to true to enable debug logging
      if (loggingEnabled) {
        // Debug logging for geometry and camera setup
        console.log('[SkyView] domeRadius:', domeRadius);
        console.log('[SkyView] aspect:', aspect);
        console.log('[SkyView] verticalFovDeg:', this.camera.fov);
        console.log('[SkyView] verticalFovRad:', verticalFovRad);
        console.log('[SkyView] horizontalFovRad:', horizontalFovRad);
        console.log('[SkyView] calculated distance:', distance);
        console.log('[SkyView] camera.position:', { x: 0, y: domeHeight - distance, z: 0 });
        console.log('[SkyView] controls.target:', { x: 0, y: domeHeight, z: 0 });
        }
      
      // Place camera below the dome, looking up at the center
      this.camera.position.set(0, domeHeight - distance, 0);
      this.controls.target.set(0, domeHeight, 0);
      this.controls.minDistance = 1;
      this.controls.maxDistance = 2 * distance;
      this.controls.enablePan = true;
      this.scene.background = new THREE.Color(0x001133);
    }

    // Force controls to update with new limits and target
    this.controls.update();
  }
  
  public getViewMode(): '3D' | 'SKY' {
    return this.currentViewMode;
  }

  public dispose(): void {
    this.stopAnimation();
    window.removeEventListener('resize', this.resizeHandler);
    this.controls.dispose();
    this.renderer.dispose();
  }
}
