import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

/**
 * Easing function for smooth camera transitions
 * easeInOutCubic provides a natural, smooth animation
 */
export function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/**
 * Camera animation controller for smooth transitions
 */
export class CameraAnimator {
  private animationId: number | null = null;
  private isAnimating = false;

  /**
   * Smoothly transition camera from current position to target position
   * @param camera - Three.js camera to animate
   * @param controls - OrbitControls instance to update
   * @param targetPosition - Target camera position (Vector3)
   * @param targetLookAt - Target look-at position (Vector3)
   * @param duration - Animation duration in milliseconds (default: 800ms)
   * @param onComplete - Optional callback when animation completes
   */
  public animateToView(
    camera: THREE.PerspectiveCamera,
    controls: OrbitControls,
    targetPosition: THREE.Vector3,
    targetLookAt: THREE.Vector3,
    duration: number = 800,
    onComplete?: () => void
  ): void {
    // Cancel any existing animation
    this.cancelAnimation();

    // Store starting values
    const startPosition = camera.position.clone();
    const startLookAt = controls.target.clone();

    // Animation start time
    let startTime: number | null = null;
    this.isAnimating = true;

    const animate = (currentTime: number) => {
      if (startTime === null) {
        startTime = currentTime;
      }

      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeProgress = easeInOutCubic(progress);

      // Interpolate camera position
      camera.position.lerpVectors(startPosition, targetPosition, easeProgress);

      // Interpolate controls target
      controls.target.lerpVectors(startLookAt, targetLookAt, easeProgress);

      // Update controls
      controls.update();

      if (progress < 1) {
        // Continue animation
        this.animationId = requestAnimationFrame(animate);
      } else {
        // Animation complete
        this.isAnimating = false;
        this.animationId = null;
        camera.position.copy(targetPosition);
        controls.target.copy(targetLookAt);
        controls.update();

        if (onComplete) {
          onComplete();
        }
      }
    };

    this.animationId = requestAnimationFrame(animate);
  }

  /**
   * Cancel the current animation
   */
  public cancelAnimation(): void {
    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
      this.isAnimating = false;
    }
  }

  /**
   * Check if an animation is currently running
   */
  public isRunning(): boolean {
    return this.isAnimating;
  }

  /**
   * Dispose resources (called on cleanup)
   */
  public dispose(): void {
    this.cancelAnimation();
  }
}
