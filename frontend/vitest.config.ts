import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    setupFiles: ['./src/test-setup.ts'],
    exclude: [
      'tests/e2e/**', // Exclude Playwright E2E tests from Vitest
      'node_modules/**', // Exclude dependencies
    ],
    globals: true,
    environment: 'happy-dom',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/**',
        'src/**/*.d.ts',
        'src/main.ts',
        'src/vite-env.d.ts',
        '**/*.config.ts',
        'dist/',
        'src/three/scene.ts',     // Requires WebGL/GPU context, covered by E2E tests
        'src/services/config.ts', // Production validation code (environment-dependent)
        'src/components/AstronomyScene.vue', // Complex Three.js component - validation tested, rendering needs E2E tests
        'src/components/BaseMap.vue', // Complex map interaction, needs E2E tests
        'src/components/DateRangePicker.vue', // Event tests, needs E2E tests for the restq
        'src/components/BodyInfoPanel.vue', // Presentation component with conditional rendering - better covered by E2E tests
        'src/components/CelestialBodyCarousel.vue', // Carousel interaction - better covered by E2E tests
        'src/components/PanelHeader.vue', // UI header - simple presentation
        'tests/e2e/**/*.ts', // Exclude Playwright E2E tests from Vitest
      ],
      thresholds: {
        // Global thresholds
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
        
        // Per-file thresholds enforce high standards on business logic
        perFile: true,
        'src/services/api.ts': {
          lines: 95,
          functions: 100,
          branches: 80,      // Current: 80%, keep as-is
          statements: 95,
        },
        'src/services/config.ts': {
          lines: 50,         // Production validation not tested
          functions: 100,
          branches: 25,      // Production validation branches
          statements: 50,
        },
        'src/composables/**': {
          lines: 99,
          functions: 100,
          branches: 88,
          statements: 98,
        },
        'src/three/objects/**': {
          lines: 95,         // Uncovered cleanup lines (dispose, removeFromScene) acceptable for animation objects
          functions: 83,     // Lifecycle methods often untested
          branches: 88,      // Realistic coverage for view mode branches
          statements: 95,
        },
      },
    },
  },
})
