// Helper to ensure all frames have a moon_phase property
function withMoonPhase(frames: any[]): any[] {
  return frames.map(frame => ({
    ...frame,
    moon_phase: frame.moon_phase || { phase_name: 'Full Moon', illumination: 1.0, phase_angle: 0 },
  }));
}
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import AstronomyScene from './AstronomyScene.vue';
import { resetFeatureFlags } from '../test-setup';

// Mock Three.js modules to avoid WebGL context errors
vi.mock('@/three/scene', () => ({
  SceneManager: class MockSceneManager {
    scene = { add: vi.fn(), remove: vi.fn() };
    camera = {};
    renderer = {};
    controls = {};
    addObject = vi.fn();
    removeObject = vi.fn();
    render = vi.fn();
    setViewMode = vi.fn();
    resize = vi.fn();
    dispose = vi.fn();
    startAnimation = vi.fn();
    stopAnimation = vi.fn();
  },
}));

vi.mock('@/three/objects/Sun', () => ({
  Sun: class MockSun {
    mesh = { visible: true };
    getLight = () => ({ visible: true });
    addToScene = vi.fn();
    update = vi.fn();
    updatePosition = vi.fn(); // Added for test compatibility
    updateLabelBillboard = vi.fn(); // Added for label support
    setViewMode = vi.fn(); // Added for view mode support
  },
}));

vi.mock('@/three/objects/Moon', () => ({
  Moon: class MockMoon {
    mesh = { visible: true };
    addToScene = vi.fn();
    update = vi.fn();
    updatePosition = vi.fn();
    updatePhase = vi.fn(); // Added for test compatibility
    updateLabelBillboard = vi.fn(); // Added for label support
    setViewMode = vi.fn(); // Added for view mode support
  },
}));

vi.mock('@/three/objects/Venus', () => ({
  Venus: class MockVenus {
    mesh = { visible: true };
    addToScene = vi.fn();
    update = vi.fn();
    updatePosition = vi.fn();
    setViewMode = vi.fn();
    updateLabelBillboard = vi.fn(); // Added for label support
  },
}));

vi.mock('@/three/objects/Mercury', () => ({
  Mercury: class MockMercury {
    mesh = { visible: true };
    addToScene = vi.fn();
    update = vi.fn();
    updatePosition = vi.fn();
    setViewMode = vi.fn();
    updateLabelBillboard = vi.fn();
  },
}));

vi.mock('@/three/objects/Earth', () => ({
  Earth: class MockEarth {
    mesh = { visible: true };
    getGridHelper = () => ({ visible: true });
    getAxesHelper = () => ({ visible: true });
    getHemisphereGrid = () => ({ visible: true });
    addToScene = vi.fn();
    update = vi.fn();
    setViewMode = vi.fn(); // Added for view mode support
  },
}));

// Mock composable - will be customized per test
import { ref } from 'vue';
let mockFetchBatchObservations = vi.fn();
let mockFetchBatchObservationsSSE = vi.fn();
let mockDismissSuccessToast = vi.fn();
let mockLoading = ref(false);
let mockError = ref<string | null>(null);
let mockData = ref<any>(null);
let mockHasData = ref(false);
let mockFrameCount = ref(24);
let mockClearData = vi.fn();
let mockSseFrames = ref([]);
let mockSseExpectedFrameCount = ref(0);

vi.mock('@/composables/useAstronomyData', () => ({
  useAstronomyData: vi.fn(() => ({
    loading: mockLoading,
    error: mockError,
    data: mockData,
    fetchBatchObservations: mockFetchBatchObservations,
    fetchBatchObservationsSSE: mockFetchBatchObservationsSSE,
    cancelSSE: vi.fn(),
    dismissSuccessToast: mockDismissSuccessToast,
    hasData: mockHasData,
    frameCount: mockFrameCount,
    clearData: mockClearData,
    sseFrames: mockSseFrames,
    sseExpectedFrameCount: mockSseExpectedFrameCount,
    sseProgress: ref(0),
  })),
}));

describe('AstronomyScene - Form Validation', () => {
  let wrapper: ReturnType<typeof mount>;

  beforeEach(() => {
    resetFeatureFlags();
    // Reset mock state
    mockFetchBatchObservations = vi.fn();
    mockFetchBatchObservationsSSE = vi.fn();
    mockDismissSuccessToast = vi.fn();
    mockLoading.value = false;
    mockError.value = null;
    mockData.value = null;
    mockHasData.value = false;
    mockFrameCount.value = 24;
    mockSseFrames.value = [];
    mockSseExpectedFrameCount.value = 0;
    
    wrapper = mount(AstronomyScene);
  });

  describe('isLatitudeValid', () => {
    it('should accept valid latitude values at boundaries', () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = -90;
      expect(vm.isLatitudeValid).toBe(true);
      vm.params.latitude = 0;
      expect(vm.isLatitudeValid).toBe(true);
      vm.params.latitude = 90;
      expect(vm.isLatitudeValid).toBe(true);
    });

    it('should reject latitude values below -90', () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = -91;
      expect(vm.isLatitudeValid).toBe(false);
    });

    it('should reject latitude values above 90', () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = 91;
      expect(vm.isLatitudeValid).toBe(false);
    });

    it('should reject NaN values (empty input)', () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = NaN;
      expect(vm.isLatitudeValid).toBe(false);
    });

    it('should reject Infinity values', () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = Infinity;
      expect(vm.isLatitudeValid).toBe(false);
    });
  });

  describe('isLongitudeValid', () => {
    it('should accept valid longitude values', () => {
      const testCases = [-180, -90, 0, 90, 180];
      
      for (const lon of testCases) {
        const vm = wrapper.vm as any;
        vm.params.longitude = lon;
        expect(vm.isLongitudeValid).toBe(true);
      }
    });

    it('should reject longitude values below -180', () => {
      const vm = wrapper.vm as any;
      vm.params.longitude = -181;
      expect(vm.isLongitudeValid).toBe(false);
    });

    it('should reject longitude values above 180', () => {
      const vm = wrapper.vm as any;
      vm.params.longitude = 181;
      expect(vm.isLongitudeValid).toBe(false);
    });

    it('should reject NaN values (empty input)', () => {
      const vm = wrapper.vm as any;
      vm.params.longitude = NaN;
      expect(vm.isLongitudeValid).toBe(false);
    });

    it('should reject Infinity values', () => {
      const vm = wrapper.vm as any;
      vm.params.longitude = -Infinity;
      expect(vm.isLongitudeValid).toBe(false);
    });
  });

  describe('isFrameCountValid', () => {
    it('should accept valid frame count values', () => {
      const testCases = [2, 10, 100, 1000, 5000, 10000];
      
      for (const count of testCases) {
        const vm = wrapper.vm as any;
        vm.params.frame_count = count;
        expect(vm.isFrameCountValid).toBe(true);
      }
    });

    it('should reject frame count below 2', () => {
      const vm = wrapper.vm as any;
      vm.params.frame_count = 1;
      expect(vm.isFrameCountValid).toBe(false);
    });

    it('should reject frame count above 10000', () => {
      const vm = wrapper.vm as any;
      vm.params.frame_count = 10001;
      expect(vm.isFrameCountValid).toBe(false);
    });

    it('should reject non-integer values', () => {
      const vm = wrapper.vm as any;
      vm.params.frame_count = 10.5;
      expect(vm.isFrameCountValid).toBe(false);
    });

    it('should reject NaN values (empty input)', () => {
      const vm = wrapper.vm as any;
      vm.params.frame_count = NaN;
      expect(vm.isFrameCountValid).toBe(false);
    });

    it('should reject Infinity values', () => {
      const vm = wrapper.vm as any;
      vm.params.frame_count = Infinity;
      expect(vm.isFrameCountValid).toBe(false);
    });
  });

  describe('isFormValid', () => {
    it('should be true when all fields are valid', () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = 51.5;
      vm.params.longitude = -0.1;
      vm.params.frame_count = 100;
      expect(vm.isFormValid).toBe(true);
    });

    it('should be false when latitude is invalid', () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = 100;
      vm.params.longitude = -0.1;
      vm.params.frame_count = 100;
      expect(vm.isFormValid).toBe(false);
    });

    it('should be false when longitude is invalid', () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = 51.5;
      vm.params.longitude = 200;
      vm.params.frame_count = 100;
      expect(vm.isFormValid).toBe(false);
    });

    it('should be false when frame count is invalid', () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = 51.5;
      vm.params.longitude = -0.1;
      vm.params.frame_count = 1;
      expect(vm.isFormValid).toBe(false);
    });

    it('should be false when any field is NaN', () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = NaN;
      vm.params.longitude = -0.1;
      vm.params.frame_count = 100;
      expect(vm.isFormValid).toBe(false);
    });
  });

  describe('Button disabled state', () => {
    it('should compute isFormValid as false when form is invalid', async () => {
      const vm = wrapper.vm as any;
      // Mutate the ref's properties directly to trigger reactivity
      vm.params.latitude = 100; // Invalid - outside -90 to 90 range
      vm.params.longitude = -0.1;
      vm.params.frame_count = 24;
      await flushPromises();
      await wrapper.vm.$nextTick();
      
      // Verify computed properties correctly determine validation state
      expect(vm.isLatitudeValid).toBe(false);
      expect(vm.isLongitudeValid).toBe(true);
      expect(vm.isFrameCountValid).toBe(true);
      expect(vm.isFormValid).toBe(false);
    });

    it('should compute isFormValid as true when all fields are valid', async () => {
      const vm = wrapper.vm as any;
      vm.params.latitude = 51.5;
      vm.params.longitude = -0.1;
      vm.params.frame_count = 100;
      await wrapper.vm.$nextTick();
      
      // Verify all validation computed properties return true
      expect(vm.isLatitudeValid).toBe(true);
      expect(vm.isLongitudeValid).toBe(true);
      expect(vm.isFrameCountValid).toBe(true);
      expect(vm.isFormValid).toBe(true);
    });
  });
});

describe('AstronomyScene - Data Loading', () => {
  let wrapper: ReturnType<typeof mount>;

  beforeEach(() => {
    resetFeatureFlags();
    mockFetchBatchObservations = vi.fn();
    mockDismissSuccessToast = vi.fn();
    mockLoading.value = false;
    mockError.value = null;
    mockData.value = null;
    mockHasData.value = false;
    
    wrapper = mount(AstronomyScene);
  });

  it('should display loading state', async () => {
    mockLoading.value = true;
    await wrapper.vm.$nextTick();
    
    expect(wrapper.text()).toContain('Loading');
  });

  it('should display error message when error occurs', async () => {
    mockError.value = 'Failed to load data';
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Failed to load data');
  });

});

describe('AstronomyScene - With Data Loaded', () => {
  let wrapper: ReturnType<typeof mount>;

  beforeEach(() => {
    resetFeatureFlags();
    mockFetchBatchObservations = vi.fn();
    mockLoading.value = false;
    mockError.value = null;
    mockData.value = {
      frames: withMoonPhase([
        {
          datetime: '2026-02-02T00:00:00Z',
          sun: { altitude: 15.5, azimuth: 120.0, is_visible: true, ra_degrees: 140.5, dec_degrees: 15.2 },
          moon: { altitude: 45.2, azimuth: 230.5, is_visible: true, ra_degrees: 210.3, dec_degrees: -5.8 },
          moon_phase: { illumination: 0.75, phase_angle: 90.0, phase_name: 'Waxing Gibbous' },
          venus: { altitude: 8.5, azimuth: 100.0, is_visible: true, ra_degrees: 45.6, dec_degrees: 10.2 },
          venus_phase: { illumination: 0.95, phase_angle: 10.0 },
        },
        {
          datetime: '2026-02-02T01:00:00Z',
          sun: { altitude: 20.0, azimuth: 125.0, is_visible: true, ra_degrees: 141.8, dec_degrees: 15.4 },
          moon: { altitude: 40.0, azimuth: 235.0, is_visible: true, ra_degrees: 211.5, dec_degrees: -6.1 },
          moon_phase: { illumination: 0.76, phase_angle: 91.0, phase_name: 'Waxing Gibbous' },
          venus: { altitude: 10.0, azimuth: 105.0, is_visible: true, ra_degrees: 46.8, dec_degrees: 10.5 },
          venus_phase: { illumination: 0.94, phase_angle: 12.0 },
        },
      ]),
      metadata: {
        location: { latitude: 51.5, longitude: -0.1, elevation: 0 },
        frame_count: 2,
        start_datetime: '2026-02-02T00:00:00Z',
        end_datetime: '2026-02-02T01:00:00Z',
        time_span_hours: 1.0,
      },
    };
    mockHasData.value = true;
    
    wrapper = mount(AstronomyScene);
  });

  it('should show animation controls when data is loaded', async () => {
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.animation-controls').exists()).toBe(true);
  });

  it('should display frame count', async () => {
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Frames:');
  });

  it('should have view toggle buttons', async () => {
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Solar System View');
    expect(wrapper.text()).toContain('Sky View');
  });

  it('should have play/pause button', async () => {
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toMatch(/Play|Pause/);
  });

  it('should have restart button', async () => {
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Restart');
  });
  it('should have recentre button', async () => {
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Recentre');
  });

});

describe('AstronomyScene - Frame Interval Calculation', () => {
  let wrapper: ReturnType<typeof mount>;

  beforeEach(() => {
    resetFeatureFlags();
    // Reset mock state
    mockFetchBatchObservations = vi.fn();
    mockDismissSuccessToast = vi.fn();
    mockLoading.value = false;
    mockError.value = null;
    mockData.value = null;
    mockHasData.value = false;
    
    wrapper = mount(AstronomyScene);
  });

  describe('calculateFrameInterval with valid data', () => {
    it('should calculate interval correctly for 1-hour spacing', async () => {
      const vm = wrapper.vm as any;
      
      // Set up data with 1-hour interval (2023-01-01 00:00:00 to 01:00:00)
      mockData.value = {
        frames: withMoonPhase([
          { datetime: '2023-01-01T00:00:00Z', sun: {}, moon: {} },
          { datetime: '2023-01-01T01:00:00Z', sun: {}, moon: {} },
        ]),
      };
      mockHasData.value = true;
      
      // Trigger the calculation
      vm.calculateFrameInterval();
      
      // 1 hour = 3600000ms, scaled down by (1000/3600000) = 1 second
      expect(vm.frameIntervalMs).toBe(1000);
    });

    it('should calculate interval correctly for 30-minute spacing', async () => {
      const vm = wrapper.vm as any;
      
      mockData.value = {
        frames: withMoonPhase([
          { datetime: '2023-01-01T00:00:00Z', sun: {}, moon: {} },
          { datetime: '2023-01-01T00:30:00Z', sun: {}, moon: {} },
        ]),
      };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      // 30 minutes = 1800000ms, scaled down = 500ms
      expect(vm.frameIntervalMs).toBe(500);
    });

    it('should calculate interval correctly for 24-hour spacing', async () => {
      const vm = wrapper.vm as any;
      
      mockData.value = {
        frames: withMoonPhase([
          { datetime: '2023-01-01T00:00:00Z', sun: {}, moon: {} },
          { datetime: '2023-01-02T00:00:00Z', sun: {}, moon: {} },
        ]),
      };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      // 24 hours = 86400000ms, scaled down = 24000ms (24 seconds)
      expect(vm.frameIntervalMs).toBe(24000);
    });

    it('should enforce minimum interval of 50ms for very short time spans', async () => {
      const vm = wrapper.vm as any;
      
      // Set up data with 1-minute interval (which scales to ~16.67ms, below minimum)
      mockData.value = {
        frames: withMoonPhase([
          { datetime: '2023-01-01T00:00:00Z', sun: {}, moon: {} },
          { datetime: '2023-01-01T00:01:00Z', sun: {}, moon: {} },
        ]),
      };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      // Should be clamped to minimum of 50ms
      expect(vm.frameIntervalMs).toBe(50);
    });
  });

  describe('calculateFrameInterval with invalid data', () => {
    it('should use default interval when data is null', () => {
      const vm = wrapper.vm as any;
      
      mockData.value = null;
      mockHasData.value = false;
      
      vm.calculateFrameInterval();
      
      expect(vm.frameIntervalMs).toBe(1000);
    });

    it('should use default interval when frames array is empty', () => {
      const vm = wrapper.vm as any;
      
      mockData.value = { frames: withMoonPhase([]) };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      expect(vm.frameIntervalMs).toBe(1000);
    });

    it('should use default interval when only one frame exists', () => {
      const vm = wrapper.vm as any;
      
      mockData.value = {
        frames: withMoonPhase([
          { datetime: '2023-01-01T00:00:00Z', sun: {}, moon: {} },
        ]),
      };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      expect(vm.frameIntervalMs).toBe(1000);
    });

    it('should handle malformed datetime strings gracefully', () => {
      const vm = wrapper.vm as any;
      
      // Use strings that will definitely create invalid dates
      mockData.value = {
        frames: withMoonPhase([
          { datetime: '', sun: {}, moon: {} },
          { datetime: 'not-a-valid-date-format', sun: {}, moon: {} },
        ]),
      };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      // Should fall back to default interval
      expect(vm.frameIntervalMs).toBe(1000);
    });

    it('should handle partially invalid datetime strings', () => {
      const vm = wrapper.vm as any;
      
      mockData.value = {
        frames: withMoonPhase([
          { datetime: '2023-01-01T00:00:00Z', sun: {}, moon: {} },
          { datetime: 'not-a-valid-date', sun: {}, moon: {} },
        ]),
      };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      // Should fall back to default interval
      expect(vm.frameIntervalMs).toBe(1000);
    });
  });

  describe('calculateFrameInterval with timestamp ordering issues', () => {
    it('should handle frames with identical timestamps', () => {
      const vm = wrapper.vm as any;
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      mockData.value = {
        frames: withMoonPhase([
          { datetime: '2023-01-01T00:00:00Z', sun: {}, moon: {} },
          { datetime: '2023-01-01T00:00:00Z', sun: {}, moon: {} },
        ]),
      };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      // Should fall back to default interval and log warning
      expect(vm.frameIntervalMs).toBe(1000);
      expect(consoleSpy).toHaveBeenCalledWith(
        'Frame timestamps are not in chronological order or are identical. Using default interval.'
      );
      
      consoleSpy.mockRestore();
    });

    it('should handle frames in reverse chronological order', () => {
      const vm = wrapper.vm as any;
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      mockData.value = {
        frames: withMoonPhase([
          { datetime: '2023-01-01T02:00:00Z', sun: {}, moon: {} },
          { datetime: '2023-01-01T01:00:00Z', sun: {}, moon: {} }, // Earlier than first
        ]),
      };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      // Should fall back to default interval and log warning
      expect(vm.frameIntervalMs).toBe(1000);
      expect(consoleSpy).toHaveBeenCalledWith(
        'Frame timestamps are not in chronological order or are identical. Using default interval.'
      );
      
      consoleSpy.mockRestore();
    });
  });

  describe('calculateFrameInterval scale factor verification', () => {
    it('should correctly apply scale factor (1 real hour = 1 animation second)', () => {
      const vm = wrapper.vm as any;
      
      mockData.value = {
        frames: withMoonPhase([
          { datetime: '2023-01-01T00:00:00Z', sun: {}, moon: {} },
          { datetime: '2023-01-01T01:00:00Z', sun: {}, moon: {} },
        ]),
      };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      // 1 hour (3600000ms) / scale factor (3600000/1000) = 1000ms (1 second)
      const MILLISECONDS_PER_SECOND = 1000;
      const MILLISECONDS_PER_HOUR = 60 * 60 * 1000;
      const expectedInterval = (MILLISECONDS_PER_HOUR * MILLISECONDS_PER_SECOND) / MILLISECONDS_PER_HOUR;
      
      expect(vm.frameIntervalMs).toBe(expectedInterval);
    });

    it('should scale 6 hours to 6 seconds', () => {
      const vm = wrapper.vm as any;
      
      mockData.value = {
        frames: withMoonPhase([
          {
            datetime: '2023-01-01T00:00:00Z',
            sun: {},
            moon: {},
            moon_phase: { phase_name: 'Full Moon', illumination: 1.0 }
          },
          {
            datetime: '2023-01-01T06:00:00Z',
            sun: {},
            moon: {},
            moon_phase: { phase_name: 'Full Moon', illumination: 1.0 }
          },
        ]),
      };
      mockHasData.value = true;
      
      vm.calculateFrameInterval();
      
      // 6 hours = 21600000ms, scaled down = 6000ms (6 seconds)
      expect(vm.frameIntervalMs).toBe(6000);
    });
  });

  describe('calculateFrameInterval integration with loadData', () => {
    it('should calculate correct interval when data is loaded', async () => {
      const vm = wrapper.vm as any;
      
      // Set up the mock to simulate successful data fetch
      mockFetchBatchObservations.mockResolvedValue(undefined);
      
      // Initially, frameIntervalMs should be the default
      expect(vm.frameIntervalMs).toBe(1000);
      
      // Update mock data to simulate data being loaded
      mockData.value = {
        frames: withMoonPhase([
          {
            datetime: '2023-01-01T00:00:00Z',
            sun: { az: 0, alt: 0 },
            moon: { az: 0, alt: 0 },
            moon_phase: { phase_name: 'Full Moon', illumination: 1.0 }
          },
          {
            datetime: '2023-01-01T02:00:00Z',
            sun: { az: 0, alt: 0 },
            moon: { az: 0, alt: 0 },
            moon_phase: { phase_name: 'Full Moon', illumination: 1.0 }
          },
        ]),
      };
      mockHasData.value = true;
      
      await vm.loadData();
      await wrapper.vm.$nextTick();
      
      // After loading 2-hour interval data, should be 2000ms (2 hours scaled to 2 seconds)
      expect(vm.frameIntervalMs).toBe(2000);
      // Success toast should be dismissed during scene transition
      expect(mockDismissSuccessToast).toHaveBeenCalled();
    });
  });
});

