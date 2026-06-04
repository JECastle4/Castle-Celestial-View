import * as THREE from 'three';

/**
 * 3D Text Label using Canvas Texture
 * Creates a billboard-style label that always faces the camera
 */
export class Label3D {
  public mesh: THREE.Mesh;
  private canvas: HTMLCanvasElement;
  private texture: THREE.CanvasTexture;

  constructor(text: string, options?: {
    fontSize?: number;
    fontColor?: string;
    backgroundColor?: string;
    width?: number;
    height?: number;
  }) {
    const {
      fontSize = 32,
      fontColor = '#ffffff',
      backgroundColor = 'rgba(0, 0, 0, 0)',
      width = 256,
      height = 128,
    } = options || {};

    // Create canvas
    this.canvas = document.createElement('canvas');
    this.canvas.width = width;
    this.canvas.height = height;

    // Get 2D context and draw text
    const ctx = this.canvas.getContext('2d')!;
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, width, height);

    // Set up text rendering
    ctx.fillStyle = fontColor;
    ctx.font = `bold ${fontSize}px Arial`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    // Center text on canvas
    const textX = width / 2;
    const textY = height / 2;

    ctx.fillText(text, textX, textY);

    // Create texture from canvas
    this.texture = new THREE.CanvasTexture(this.canvas);
    this.texture.minFilter = THREE.LinearFilter;
    this.texture.magFilter = THREE.LinearFilter;

    // Create material and mesh
    const material = new THREE.MeshBasicMaterial({
      map: this.texture,
      side: THREE.DoubleSide,
      transparent: true,
    });

    // Calculate aspect ratio to maintain proportions
    const aspectRatio = width / height;
    const labelGeometry = new THREE.PlaneGeometry(1 * aspectRatio, 1);
    this.mesh = new THREE.Mesh(labelGeometry, material);
    this.mesh.name = `label-${text}`;
  }

  /**
   * Position label relative to a celestial body
   * @param position Position of the celestial body
   * @param offset Offset from the body center (usually radius + small distance)
   */
  public positionRelativeTo(position: THREE.Vector3, offset: number = 0.5): void {
    // Position label along the radial direction from Earth center
    // This ensures labels appear near their respective celestial bodies,
    // not just displaced vertically
    if (position.length() === 0) {
      // Avoid division by zero for objects at Earth's center
      this.mesh.position.set(offset, 0, 0);
    } else {
      // Normalize position vector and scale by (distance + offset)
      const direction = position.clone().normalize();
      const distance = position.length();
      const labelDistance = distance + offset;
      this.mesh.position.copy(direction.multiplyScalar(labelDistance));
    }
  }

  /**
   * Update the label to face the camera (billboard behavior)
   * Call this in the animation loop
   * @param camera The Three.js camera
   */
  public updateBillboard(camera: THREE.Camera): void {
    this.mesh.quaternion.copy(camera.quaternion);
  }

  /**
   * Set label visibility
   */
  public setVisible(visible: boolean): void {
    this.mesh.visible = visible;
  }

  /**
   * Get the mesh (for adding to scene)
   */
  public getMesh(): THREE.Mesh {
    return this.mesh;
  }

  /**
   * Dispose resources
   */
  public dispose(): void {
    this.texture.dispose();
    (this.mesh.material as THREE.Material).dispose();
    this.mesh.geometry.dispose();
  }
}
