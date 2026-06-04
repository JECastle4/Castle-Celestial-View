import { config } from '@vue/test-utils'
import { i18n } from './i18n'
import { vi } from 'vitest'

// Mock feature flags - baseline configuration (can be overridden per test)
export const testFeatureFlags = {
  SUN_ENABLED: true,
  MOON_ENABLED: true,
  VENUS_ENABLED: false,  // Disabled by default to avoid carousel rendering issues
  VENUS_UI_ENABLED: false,
}

vi.mock('@/config/features', () => ({
  FEATURE_FLAGS: testFeatureFlags
}))

// Helper to temporarily override feature flags for a test
export function setFeatureFlags(flags: Partial<typeof testFeatureFlags>): void {
  Object.assign(testFeatureFlags, flags);
}

// Helper to reset to baseline
export function resetFeatureFlags(): void {
  Object.assign(testFeatureFlags, {
    SUN_ENABLED: true,
    MOON_ENABLED: true,
    VENUS_ENABLED: false,
    VENUS_UI_ENABLED: false,
  });
}

// Mock Label3D for tests - minimal implementation for test environment
vi.mock('./three/objects/Label3D', () => {
  return {
    Label3D: class {
      public mesh: any;

      constructor(text: string, _options?: any) {
        // Create minimal mock without THREE.js dependencies
        this.mesh = {
          name: `label-${text}`,
          position: { copy: (_p: any) => {}, y: 0 },
          quaternion: { copy: (_q: any) => {} },
          visible: true,
        };
      }

      positionRelativeTo(_position: any, _offset: number): void {
        // No-op in test environment
      }

      updateBillboard(_camera: any): void {
        // No-op in test environment
      }

      setVisible(_visible: boolean): void {
        // No-op in test environment
      }

      getMesh(): any {
        return this.mesh;
      }

      dispose(): void {
        // No-op in test environment
      }
    }
  }
})

config.global.plugins = [i18n]

// Suppress Three.js warnings about mock objects in tests
// The Label3D mock in tests isn't a true THREE.Object3D, which causes console warnings
// but doesn't affect test functionality
const originalError = console.error;
console.error = function(...args: any[]) {
  // Suppress THREE.Object3D.add warnings for mock objects
  if (args[0]?.toString?.().includes('THREE.Object3D.add')) {
    return;
  }
  originalError.apply(console, args);
};

// Handle unhandled promise rejections from Vue component rendering
// These occur in happy-dom environment when Vue components try to access
// WebGL/GPU features that aren't available in test environment
if (typeof process !== 'undefined' && process.on) {
  process.on('unhandledRejection', (reason: any) => {
    // Suppress errors related to DOM/WebGL that don't affect test outcomes
    if (reason?.message?.includes?.('nextSibling') || 
        reason?.message?.includes?.('reading property')) {
      return;
    }
    // Let other rejections be handled normally
    console.error('Unhandled Rejection:', reason);
  });
}
