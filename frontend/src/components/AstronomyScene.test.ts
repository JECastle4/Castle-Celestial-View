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

describe('AstronomyScene - Animation Controls', () => {
  let wrapper: ReturnType<typeof mount>;

  beforeEach(() => {
    resetFeatureFlags();
    mockLoading.value = false;
    mockError.value = null;
    mockData.value = null;
    mockHasData.value = false;
    
    wrapper = mount(AstronomyScene);
  });

  describe('Animation state properties', () => {
    it('should have isAnimating ref that defaults to false', () => {
      const vm = wrapper.vm as any;
      expect(vm.isAnimating).toBe(false);
    });

    it('should have animationSpeed ref that defaults to 1.0', () => {
      const vm = wrapper.vm as any;
      expect(vm.animationSpeed).toBe(1.0);
    });

    it('should have currentIndex ref that defaults to 0', () => {
      const vm = wrapper.vm as any;
      expect(vm.currentIndex).toBe(0);
    });

    it('should have viewMode ref that defaults to 3D', () => {
      const vm = wrapper.vm as any;
      expect(vm.viewMode).toBe('3D');
    });
  });

  describe('Frame data access', () => {
    it('should return null for currentFrame when no data is loaded', () => {
      const vm = wrapper.vm as any;
      expect(vm.currentFrame).toBeNull();
    });

    it('should return current frame when data is available', async () => {
      mockData.value = {
        frames: withMoonPhase([
          {
            datetime: '2023-01-01T00:00:00Z',
            sun: { altitude: 45, azimuth: 90, is_visible: true, ra_degrees: 0, dec_degrees: 0 },
            moon: { altitude: 30, azimuth: 180, is_visible: true, ra_degrees: 0, dec_degrees: 0 },
            venus: { altitude: 10, azimuth: 120, is_visible: true, ra_degrees: 0, dec_degrees: 0 },
            mercury: { altitude: 5, azimuth: 150, is_visible: true, ra_degrees: 0, dec_degrees: 0 },
          },
        ]),
      };
      mockHasData.value = true;
      
      const vm = wrapper.vm as any;
      vm.currentIndex = 0;
      await wrapper.vm.$nextTick();
      
      expect(vm.currentFrame).not.toBeNull();
      expect(vm.currentFrame?.datetime).toBe('2023-01-01T00:00:00Z');
    });

    it('should return null for currentFrame when index exceeds frames length', async () => {
      mockData.value = {
        frames: withMoonPhase([
          {
            datetime: '2023-01-01T00:00:00Z',
            sun: { altitude: 45, azimuth: 90, is_visible: true, ra_degrees: 0, dec_degrees: 0 },
            moon: { altitude: 30, azimuth: 180, is_visible: true, ra_degrees: 0, dec_degrees: 0 },
          },
        ]),
      };
      mockHasData.value = true;
      
      const vm = wrapper.vm as any;
      vm.currentIndex = 999; // Index out of bounds
      await wrapper.vm.$nextTick();
      
      expect(vm.currentFrame).toBeNull();
    });
  });
});

