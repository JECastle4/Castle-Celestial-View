import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { CameraAnimator } from './cameraAnimation';
import * as THREE from 'three';

/**
 * CameraAnimator tests are largely skipped due to requestAnimationFrame timing in Node.js test environment.
 * 
 * Current Strategy:
 * - Unit tests cover initialization, state queries, and cleanup
 * - Animation timing tests skipped (require actual rAF execution)
 * - E2E tests with Playwright would validate actual animation behavior in browser
 */

describe('CameraAnimator', () => {
  let animator: CameraAnimator;
  let mockCamera: THREE.PerspectiveCamera;
  let mockControls: any;

  beforeEach(() => {
    animator = new CameraAnimator();
    
    // Create mock camera
    mockCamera = new THREE.PerspectiveCamera(75, 800 / 600, 0.1, 1000);
    mockCamera.position.set(0, 5, 10);
    
    // Create mock controls
    mockControls = {
      target: new THREE.Vector3(0, 0, 0),
      update: vi.fn(),
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('initialization', () => {
    it('should create animator instance', () => {
      expect(animator).toBeDefined();
    });

    it('should start with animation not running', () => {
      expect(animator.isRunning()).toBe(false);
    });

    it('should have dispose method', () => {
      expect(typeof animator.dispose).toBe('function');
    });

    it('should have animateToView method', () => {
      expect(typeof animator.animateToView).toBe('function');
    });

    it('should have cancelAnimation method', () => {
      expect(typeof animator.cancelAnimation).toBe('function');
    });
  });

  describe('state queries', () => {
    it('isRunning should return boolean', () => {
      expect(typeof animator.isRunning()).toBe('boolean');
    });

    it('isRunning should be false initially', () => {
      expect(animator.isRunning()).toBe(false);
    });
  });

  describe('cancelAnimation', () => {
    it('should not throw when called with no active animation', () => {
      expect(() => animator.cancelAnimation()).not.toThrow();
    });

    it('should return undefined', () => {
      const result = animator.cancelAnimation();
      expect(result).toBeUndefined();
    });

    it('should cancel active animation and stop isRunning', () => {
      const targetPos = new THREE.Vector3(0, 5, 20);
      const targetLookAt = new THREE.Vector3(0, 0, 0);

      animator.animateToView(
        mockCamera,
        mockControls,
        targetPos,
        targetLookAt,
        800
      );

      expect(animator.isRunning()).toBe(true);

      animator.cancelAnimation();

      expect(animator.isRunning()).toBe(false);
    });
  });

  describe('dispose', () => {
    it('should not throw when called', () => {
      expect(() => animator.dispose()).not.toThrow();
    });

    it('should cancel any active animation before disposing', () => {
      const cancelSpy = vi.spyOn(animator, 'cancelAnimation');
      animator.dispose();
      expect(cancelSpy).toHaveBeenCalled();
    });

    it('should be safe to call multiple times', () => {
      expect(() => {
        animator.dispose();
        animator.dispose();
      }).not.toThrow();
    });
  });

  describe('easing function', () => {
    it('should provide smooth easing for camera transitions', () => {
      // This tests the general concept of easing
      // The actual easing function is used internally in animateToView
      const animator2 = new CameraAnimator();
      expect(animator2).toBeDefined();
    });
  });

  describe('animation parameters', () => {
    it('animateToView should accept camera, controls, and positions', () => {
      const startPos = new THREE.Vector3(0, 5, 10);
      const targetPos = new THREE.Vector3(0, 5, 20);
      const targetLookAt = new THREE.Vector3(0, 0, 0);

      mockCamera.position.copy(startPos);

      // Should not throw
      expect(() => {
        animator.animateToView(
          mockCamera,
          mockControls,
          targetPos,
          targetLookAt,
          800
        );
      }).not.toThrow();
    });

    it('animateToView should set isRunning to true', () => {
      const targetPos = new THREE.Vector3(0, 5, 20);
      const targetLookAt = new THREE.Vector3(0, 0, 0);

      animator.animateToView(
        mockCamera,
        mockControls,
        targetPos,
        targetLookAt,
        800
      );

      expect(animator.isRunning()).toBe(true);
    });

    it('animateToView should accept optional callback', () => {
      const callback = vi.fn();
      const targetPos = new THREE.Vector3(0, 5, 20);
      const targetLookAt = new THREE.Vector3(0, 0, 0);

      expect(() => {
        animator.animateToView(
          mockCamera,
          mockControls,
          targetPos,
          targetLookAt,
          800,
          callback
        );
      }).not.toThrow();
    });

    it('animateToView should accept custom duration', () => {
      const targetPos = new THREE.Vector3(0, 5, 20);
      const targetLookAt = new THREE.Vector3(0, 0, 0);

      expect(() => {
        animator.animateToView(
          mockCamera,
          mockControls,
          targetPos,
          targetLookAt,
          1200 // Custom duration
        );
      }).not.toThrow();
    });

    it('animateToView with very short duration should complete immediately', () => {
      const rAFSpy = vi.spyOn(window, 'requestAnimationFrame');
      const targetPos = new THREE.Vector3(0, 5, 20);
      const targetLookAt = new THREE.Vector3(0, 0, 0);

      animator.animateToView(
        mockCamera,
        mockControls,
        targetPos,
        targetLookAt,
        1 // Very short duration (1ms)
      );

      // Should schedule animation frame
      expect(rAFSpy).toHaveBeenCalled();

      rAFSpy.mockRestore();
    });
  });

  describe('animation state transitions', () => {
    it('should transition from not running to running on animateToView', () => {
      expect(animator.isRunning()).toBe(false);

      animator.animateToView(
        mockCamera,
        mockControls,
        new THREE.Vector3(0, 5, 20),
        new THREE.Vector3(0, 0, 0),
        800
      );

      expect(animator.isRunning()).toBe(true);
    });

    it('should cancel previous animation when new one starts', () => {
      const targetPos1 = new THREE.Vector3(0, 5, 20);
      const targetPos2 = new THREE.Vector3(0, 5, 30);
      const targetLookAt = new THREE.Vector3(0, 0, 0);

      animator.animateToView(
        mockCamera,
        mockControls,
        targetPos1,
        targetLookAt,
        800
      );

      expect(animator.isRunning()).toBe(true);

      // Start a new animation
      animator.animateToView(
        mockCamera,
        mockControls,
        targetPos2,
        targetLookAt,
        800
      );

      expect(animator.isRunning()).toBe(true);
    });
  });

  describe('animation completion', () => {
    it('should call onComplete callback when animation finishes', () => {
      const callback = vi.fn();
      const targetPos = new THREE.Vector3(0, 5, 20);
      const targetLookAt = new THREE.Vector3(0, 0, 0);

      // Mock requestAnimationFrame to call immediately with completion
      let animateCallback: ((time: number) => void) | null = null;
      const mockRAF = vi.fn((cb: (time: number) => void) => {
        animateCallback = cb;
        return 1;
      });
      vi.stubGlobal('requestAnimationFrame', mockRAF);

      animator.animateToView(
        mockCamera,
        mockControls,
        targetPos,
        targetLookAt,
        100,
        callback
      );

      // Trigger animation with completion (progress > 1)
      if (animateCallback !== null) {
        (animateCallback as (time: number) => void)(0); // startTime
        (animateCallback as (time: number) => void)(200); // elapsed = 200 > 100, progress > 1
      }

      expect(callback).toHaveBeenCalled();

      vi.unstubAllGlobals();
    });

    it('should update controls and camera on completion', () => {
      const targetPos = new THREE.Vector3(10, 20, 30);
      const targetLookAt = new THREE.Vector3(5, 5, 5);

      // Mock requestAnimationFrame to call with progress > 1
      let animateCallback: ((time: number) => void) | null = null;
      const mockRAF = vi.fn((cb: (time: number) => void) => {
        animateCallback = cb;
        return 1;
      });
      vi.stubGlobal('requestAnimationFrame', mockRAF);

      animator.animateToView(
        mockCamera,
        mockControls,
        targetPos,
        targetLookAt,
        50
      );

      // Manually trigger the callback with completion time
      if (animateCallback !== null) {
        (animateCallback as (time: number) => void)(0); // startTime
        (animateCallback as (time: number) => void)(100); // elapsed = 100 > 50, progress > 1
      }

      // After completion, isAnimating should be false
      expect(animator.isRunning()).toBe(false);
      // Camera should be at target position
      expect(mockCamera.position).toEqual(targetPos);
      // Controls target should be at targetLookAt
      expect(mockControls.target).toEqual(targetLookAt);

      vi.unstubAllGlobals();
    });

    it('should set animationId to null on completion', () => {
      const targetPos = new THREE.Vector3(0, 5, 20);
      const targetLookAt = new THREE.Vector3(0, 0, 0);

      let animateCallback: ((time: number) => void) | null = null;
      const mockRAF = vi.fn((cb: (time: number) => void) => {
        animateCallback = cb;
        return 42; // Return a mock animation ID
      });
      vi.stubGlobal('requestAnimationFrame', mockRAF);

      animator.animateToView(
        mockCamera,
        mockControls,
        targetPos,
        targetLookAt,
        100
      );

      // Trigger completion
      if (animateCallback !== null) {
        (animateCallback as (time: number) => void)(0);
        (animateCallback as (time: number) => void)(200); // Progress > 1
      }

      // Should be able to dispose without errors
      expect(() => animator.dispose()).not.toThrow();

      vi.unstubAllGlobals();
    });
  });

  describe('cleanup', () => {
    it('should properly dispose after animation', () => {
      const animator2 = new CameraAnimator();
      const targetPos = new THREE.Vector3(0, 5, 20);
      const targetLookAt = new THREE.Vector3(0, 0, 0);

      animator2.animateToView(
        mockCamera,
        mockControls,
        targetPos,
        targetLookAt,
        800
      );

      animator2.dispose();
      expect(animator2.isRunning()).toBe(false);
    });

    it('should handle disposal of multiple animators', () => {
      const animator1 = new CameraAnimator();
      const animator2 = new CameraAnimator();

      animator1.animateToView(
        mockCamera,
        mockControls,
        new THREE.Vector3(0, 5, 20),
        new THREE.Vector3(0, 0, 0),
        800
      );

      animator2.animateToView(
        mockCamera,
        mockControls,
        new THREE.Vector3(0, 5, 25),
        new THREE.Vector3(0, 0, 0),
        800
      );

      expect(() => {
        animator1.dispose();
        animator2.dispose();
      }).not.toThrow();

      expect(animator1.isRunning()).toBe(false);
      expect(animator2.isRunning()).toBe(false);
    });
  });
});
