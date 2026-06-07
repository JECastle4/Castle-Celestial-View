import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { axe, toHaveNoViolations } from 'jest-axe';
import { ref } from 'vue';
import AstronomyScene from './AstronomyScene.vue';
import DateRangePicker from './DateRangePicker.vue';
import { resetFeatureFlags } from '../test-setup';

expect.extend(toHaveNoViolations);

// ── Mocks (same as AstronomyScene.test.ts) ────────────────────────────────────

vi.mock('@/three/scene', () => ({
  SceneManager: class {
    scene = {}; camera = {}; renderer = {}; controls = {};
    addObject = vi.fn(); removeObject = vi.fn(); render = vi.fn();
    setViewMode = vi.fn(); resize = vi.fn(); dispose = vi.fn();
    startAnimation = vi.fn(); stopAnimation = vi.fn();
  },
}));
vi.mock('@/three/objects/Sun', () => ({
  Sun: class {
    mesh = { visible: true };
    getLight = () => ({ visible: true });
    addToScene = vi.fn(); update = vi.fn(); updatePosition = vi.fn(); 
    updateLabelBillboard = vi.fn(); setViewMode = vi.fn();
  },
}));
vi.mock('@/three/objects/Moon', () => ({
  Moon: class {
    mesh = { visible: true };
    addToScene = vi.fn(); update = vi.fn(); updatePosition = vi.fn(); updatePhase = vi.fn();
    updateLabelBillboard = vi.fn(); setViewMode = vi.fn(); 
  },
}));
vi.mock('@/three/objects/Venus', () => ({
  Venus: class {
    mesh = { visible: true };
    label = { setVisible: vi.fn() };
    addToScene = vi.fn(); update = vi.fn(); updatePosition = vi.fn(); 
    updateLabelBillboard = vi.fn(); setViewMode = vi.fn(); removeFromScene = vi.fn();
  },
}));
vi.mock('@/three/objects/Earth', () => ({
  Earth: class {
    mesh = { visible: true };
    getGridHelper = () => ({ visible: true });
    getAxesHelper = () => ({ visible: true });
    getHemisphereGrid = () => ({ visible: true });
    addToScene = vi.fn(); update = vi.fn();
  },
}));

let mockLoading = ref(false);
let mockError = ref<string | null>(null);
let mockData = ref<any>(null);
let mockHasData = ref(false);
let mockFrameCount = ref(24);

vi.mock('@/composables/useAstronomyData', () => ({
  useAstronomyData: vi.fn(() => ({
    loading: mockLoading,
    error: mockError,
    data: mockData,
    fetchBatchObservations: vi.fn(),
    fetchBatchObservationsSSE: vi.fn(),
    cancelSSE: vi.fn(),
    dismissSuccessToast: vi.fn(),
    hasData: mockHasData,
    frameCount: mockFrameCount,
    clearData: vi.fn(),
    sseFrames: ref([]),
    sseExpectedFrameCount: ref(0),
    sseProgress: ref(0),
  })),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

function makeFrame() {
  return {
    datetime: '2026-01-01T00:00:00Z',
    sun: { altitude: 10, azimuth: 180, is_visible: true, ra_degrees: 0, dec_degrees: 0 },
    moon: { altitude: 5, azimuth: 90, is_visible: true, ra_degrees: 0, dec_degrees: 0 },
    moon_phase: { phase_name: 'Full Moon', illumination: 1.0, phase_angle: 0 },
  };
}

// ── AstronomyScene ─────────────────────────────────────────────────────────────

describe('Accessibility – AstronomyScene (form state)', () => {
  let wrapper: ReturnType<typeof mount>;

  beforeEach(() => {
    resetFeatureFlags();
    mockLoading.value = false;
    mockError.value = null;
    mockData.value = null;
    mockHasData.value = false;
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('has no axe violations in the input form state', async () => {
    wrapper = mount(AstronomyScene, { attachTo: document.body });
    await flushPromises();
    const results = await axe(wrapper.element);
    expect(results).toHaveNoViolations();
  });
});

describe('Accessibility – AstronomyScene (animation-controls state)', () => {
  let wrapper: ReturnType<typeof mount>;

  beforeEach(() => {
    resetFeatureFlags();
    mockLoading.value = false;
    mockError.value = null;
    mockHasData.value = true;
    mockFrameCount.value = 2;
    mockData.value = { frames: [makeFrame(), makeFrame()] };
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  it('has no axe violations in the animation controls state', async () => {
    wrapper = mount(AstronomyScene, { attachTo: document.body });
    await flushPromises();
    const results = await axe(wrapper.element);
    expect(results).toHaveNoViolations();
  });
});

// ── DateRangePicker ────────────────────────────────────────────────────────────

describe('Accessibility – DateRangePicker', () => {
  let wrapper: ReturnType<typeof mount>;

  afterEach(() => {
    wrapper?.unmount();
  });

  it('has no axe violations', async () => {
    wrapper = mount(DateRangePicker, {
      props: { initialStartDate: '2026-01-01', initialEndDate: '2026-01-07' },
      attachTo: document.body,
    });
    await flushPromises();
    const results = await axe(wrapper.element);
    expect(results).toHaveNoViolations();
  });
});
