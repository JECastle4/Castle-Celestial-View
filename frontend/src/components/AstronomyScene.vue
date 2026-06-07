<template>
  <div class="astronomy-scene">
    <div class="scene-layout">
      <div class="map-and-date-container">
        <div class="map-container">
          <BaseMap v-if="!hasData" class="map-panel" :enablePinTool="true" @pin-placed="onPinPlaced" />
          <canvas v-if="hasData" ref="canvasRef" class="canvas-panel" />
        </div>
        <div v-if="!hasData" class="date-range-centered">
          <DateRangePicker
            class="date-range-panel date-range-bordered"
            :initialStartDate="params.start_date"
            :initialEndDate="params.end_date"
            @update:dates="onDateRangeSelected"
          />
        </div>
      </div>
      <div class="controls-panel">
      <h1 class="page-heading">{{ t('app.title') }}</h1>
      
      <div v-if="loading" class="loading">
        <div class="progress-bar-container">
          <div class="progress-bar" :style="{ width: (sseProgress * 100).toFixed(1) + '%' }"></div>
          <span class="progress-text" v-if="sseExpectedFrameCount > 0">
            {{ sseFrames.length }}/{{ sseExpectedFrameCount }}
          </span>
        </div>
        <div class="progress-label">
          {{ t('ui.status.loading') }} <span v-if="sseExpectedFrameCount > 0">{{ Math.round(sseProgress * 100) }}%</span>
        </div>
        <button class="cancel-btn" @click="cancelSSE" type="button">
          <i class="fa fa-circle-xmark" aria-hidden="true" style="margin-right: 0.5em;"></i>
          {{ t('buttons.cancel') }}
        </button>
      </div>
      
      <div v-if="error" class="error">
        {{ error }}
      </div>
      
      <div v-if="!hasData" class="input-form">
        <div class="form-group">
          <label for="latitude">{{ t('forms.labels.latitude') }}:</label>
          <input 
            id="latitude"
            v-model.number="params.latitude" 
            type="number" 
              step="0.1"
            min="-90"
            max="90"
            required
            :class="{ invalid: !isLatitudeValid }"
          />
          <span v-if="!isLatitudeValid" class="error-message">
            {{ t('validation.latitudeRange') }}
          </span>
        </div>
        
        <div class="form-group">
          <label for="longitude">{{ t('forms.labels.longitude') }}:</label>
          <input 
            id="longitude"
            v-model.number="params.longitude" 
            type="number" 
            step="0.1"
            min="-180"
            max="180"
            required
            :class="{ invalid: !isLongitudeValid }"
          />
          <span v-if="!isLongitudeValid" class="error-message">
            {{ t('validation.longitudeRange') }}
          </span>
        </div>
        
        <div class="form-group">
          <label for="start-date">{{ t('forms.labels.startDate') }}:</label>
          <input id="start-date" v-model="params.start_date" type="date" />
        </div>
        
        <div class="form-group">
          <label for="start-time">{{ t('forms.labels.startTime') }}:</label>
          <input id="start-time" v-model="params.start_time" type="time" step="1" />
        </div>
        
        <div class="form-group">
          <label for="end-date">{{ t('forms.labels.endDate') }}:</label>
          <input id="end-date" v-model="params.end_date" type="date" />
        </div>
        
      
        <div class="form-group">
          <label for="end-time">{{ t('forms.labels.endTime') }}:</label>
          <input id="end-time" v-model="params.end_time" type="time" step="1" />
        </div>
        
        <div class="form-group frames-per-day-group">
          <label for="frames-per-day">{{ t('forms.labels.framesPerDay') }}:</label>
          <input
            id="frames-per-day"
            v-model.number="framesPerDay"
            type="range"
            min="1"
            max="1440"
            step="1"
          />
          <span>{{ framesPerDay }} {{ t('ui.units.framesPerDay') }}</span>
        </div>

        <div class="form-group">
          <label for="frame-count">{{ t('forms.labels.frameCount') }}:</label>
          <input
            id="frame-count"
            v-model.number="params.frame_count"
            type="number"
            min="1"
            required
            readonly
          />
          <span>{{ params.frame_count }} {{ t('ui.units.totalFrames') }}</span>
        </div>
        
        <button @click="loadData" :disabled="loading || !isFormValid">
          <i class="fa fa-play" aria-hidden="true" style="margin-right: 0.5em; color: #28a745;"></i>
          {{ t('buttons.loadData') }}
        </button>
      </div>
      
      <div v-if="hasData" class="animation-controls">
        <p>{{ t('astronomy.frames') }}: {{ frameCount }}</p>
        
        <div class="view-toggle">
          <button @click="setViewMode('3D')" :class="{ active: viewMode === '3D' }">
            <i class="fa fa-sun" aria-hidden="true" style="margin-right: 0.5em;"></i>
            {{ t('views.solar3d') }}
          </button>
          <button @click="setViewMode('SKY')" :class="{ active: viewMode === 'SKY' }">
            <i class="fa fa-globe" aria-hidden="true" style="margin-right: 0.5em;"></i>
            {{ t('views.sky') }}
          </button>
        </div>
        
        <button @click="toggleAnimation">
          <template v-if="!isAnimating">
            <i class="fa fa-play" aria-hidden="true" style="margin-right: 0.5em;"></i>
            {{ t('buttons.play') }}
          </template>
          <template v-else>
            {{ t('buttons.pause') }}
          </template>
        </button>
        <button
          @click="resetAnimation"
          class="restart-btn"
          :title="$t('buttons.restartTooltip')"
          :aria-label="$t('buttons.restartAria')"
        >
          <i class="fa fa-film" aria-hidden="true" style="margin-right: 0.5em;"></i>
          {{ $t('buttons.restart') }}
        </button>
        <button
          @click="recentreCamera"
          :title="t('buttons.recentreTooltip')"
          :aria-label="t('buttons.recentreAria')"
          class="recentre-btn"
        >
          <i class="fa fa-camera" aria-hidden="true" style="margin-right: 0.5em;"></i>
          {{ t('buttons.recentre') }}
        </button>
        <button @click="clearData">
          <i class="fa fa-arrow-rotate-left" aria-hidden="true" style="margin-right: 0.5em;"></i>
          {{ t('buttons.newQuery') }}
        </button>
        
        <div class="form-group">
          <label for="animation-speed">{{ t('forms.labels.animationSpeed') }}:</label>
          <input id="animation-speed" v-model.number="animationSpeed" type="range" min="0.1" max="5" step="0.1" />
          <span>{{ animationSpeed.toFixed(1) }}x</span>
        </div>
        
        <div v-if="currentFrame" class="celestial-panel">
          <PanelHeader
            :currentFrameIndex="currentIndex"
            :totalFrames="frameCount"
            :datetime="currentFrame.datetime"
            :location="params"
          />
          
          <CelestialBodyCarousel
            :selectedBody="selectedBodyId"
            @update:selectedBody="(bodyId) => selectedBodyId = bodyId"
          />
          
          <BodyInfoPanel
            :bodyId="selectedBodyId"
            :bodyData="selectedBodyId === 'sun' ? currentFrame.sun : selectedBodyId === 'moon' ? currentFrame.moon : currentFrame.venus"
            :moonPhaseData="selectedBodyId === 'moon' ? currentFrame.moon_phase : undefined"
            :venusPhaseData="selectedBodyId === 'venus' ? currentFrame.venus_phase : undefined"
          />
        </div>
      </div>
    </div>
  </div>
</div>  
</template>


<style scoped>
.astronomy-scene {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100dvh;
}

/* Layout for full-width map and fixed right panel */
.scene-layout {
  display: flex;
  flex-direction: row;
  flex: 1 1 auto;
  min-height: 0;
  width: 100vw;
  position: relative;
}
.map-and-date-container {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
}
.map-container {
  flex: 1 1 auto;
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  display: flex;
}
.map-panel {
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  margin: 0;
  border-radius: 0;
  box-shadow: none;
}
.date-range-centered {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: flex-start;
  width: 420px;
  max-width: 90vw;
  margin-top: 0;
  min-height: 0;
  max-height: 100%;
}
.date-range-bordered {
  border: 2px solid #b0b0b0;
  border-radius: 8px;
  padding: 16px 12px 6px 12px;
  background: #fafbfc;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  margin-bottom: 10px;
}
.controls-panel {
  position: relative;
  width: 340px;
  min-width: 280px;
  max-width: 400px;
  flex-shrink: 0;
  margin: 0;
  background: #181818;
  color: #fff;
  padding: 24px 18px 18px 18px;
  border-radius: 0 0 0 8px;
  height: 100vh;
  overflow-y: auto;
  font-size: 1em;
}
</style>

<script setup lang="ts">
import '@fortawesome/fontawesome-free/css/all.min.css';
import { ref, computed, watch, nextTick, onMounted, onUnmounted, defineAsyncComponent } from 'vue';
import { useToast } from '@/composables/useToast';
import { useI18n } from 'vue-i18n';
import { useAstronomyData } from '@/composables/useAstronomyData';
import { SceneManager } from '@/three/scene';
import { Sun } from '@/three/objects/Sun';
import { Moon } from '@/three/objects/Moon';
import { Venus } from '@/three/objects/Venus';
import { Earth } from '@/three/objects/Earth';
import { FEATURE_FLAGS } from '@/config/features';
import type { ObservationFrame } from '@/types/api.types';
import CelestialBodyCarousel from './CelestialBodyCarousel.vue';
import BodyInfoPanel from './BodyInfoPanel.vue';
import PanelHeader from './PanelHeader.vue';

const BaseMap = defineAsyncComponent(() => import('./BaseMap.vue'));
const DateRangePicker = defineAsyncComponent(() => import('./DateRangePicker.vue'));

const { t } = useI18n();
const toast = useToast();

// Form parameters with defaults
const today = new Date();
const yyyy = today.getFullYear();
const mm = String(today.getMonth() + 1).padStart(2, '0');
const dd = String(today.getDate()).padStart(2, '0');
const startDate = `${yyyy}-${mm}-${dd}`;
const endDate = `${yyyy}-${mm}-${dd}`;

const params = ref({
  latitude: 51.5,
  longitude: -0.1,
  elevation: 0,
  start_date: startDate,
  start_time: '00:00:00',
  end_date: endDate,
  end_time: '23:59:59',
  frame_count: 48,
});

const framesPerDay = ref(48);

// Celestial body carousel state
const selectedBodyId = ref('sun');

// Canvas reference
const canvasRef = ref<HTMLCanvasElement | null>(null);
// API data
const { data, loading, error, hasData, frameCount, fetchBatchObservationsSSE, cancelSSE, clearData: clearApiData, sseProgress, sseExpectedFrameCount, sseFrames, dismissSuccessToast } = useAstronomyData();
  // Animation state
let sceneManager: SceneManager | null = null;
let sun: Sun | null = null;
let moon: Moon | null = null;
let venus: Venus | null = null;
let earth: Earth | null = null;

const isAnimating = ref(false);
const animationSpeed = ref(1.0);
const currentIndex = ref(0);
const viewMode = ref<'3D' | 'SKY'>('3D');
const lastTime = ref(0);
const frameIntervalMs = ref(1000); // Time between frames in milliseconds

function calculateDaysInRange() {
  const start = new Date(params.value.start_date);
  const end = new Date(params.value.end_date);

  // Form parameters with defaults
  const msPerDay = 24 * 60 * 60 * 1000;
  return Math.floor((end.getTime() - start.getTime()) / msPerDay) + 1;
}

function updateFrameCount() {
  const days = calculateDaysInRange();
  params.value.frame_count = days * framesPerDay.value;
}

// Watch for changes in date range or framesPerDay
watch([
  () => params.value.start_date,
  () => params.value.end_date,
  framesPerDay
], updateFrameCount, { immediate: true });

// Track whether the pin tool is open (for future extensibility)
const pinToolOpen = ref(false);

function onPinPlaced({ lat, lon }: { lat: number; lon: number }) {
  // Always update the main view's coordinates immediately
  params.value.latitude = lat;
  params.value.longitude = lon;
  // Close the pin tool if open (future extensibility)
  pinToolOpen.value = false;
}

function onDateRangeSelected(dates: { start: Date, end: Date }) {
  // Format as YYYY-MM-DD for params
  params.value.start_date = dates.start.toISOString().slice(0, 10);
  params.value.end_date = dates.end.toISOString().slice(0, 10);
}

// Current frame
const currentFrame = computed<ObservationFrame | null>(() => {
  if (!data.value || currentIndex.value >= data.value.frames.length) {
    return null;
  }
  return data.value.frames[currentIndex.value];
});

// Form validation
const isLatitudeValid = computed(() => {
  const lat = params.value.latitude;
  return Number.isFinite(lat) && lat >= -90 && lat <= 90;
});

const isLongitudeValid = computed(() => {
  const lon = params.value.longitude;
  return Number.isFinite(lon) && lon >= -180 && lon <= 180;
});

const isFrameCountValid = computed(() => {
  const count = params.value.frame_count;
  return Number.isFinite(count) && count >= 2 && count <= 10000 && Number.isInteger(count);
});

const isFormValid = computed(() => {
  return isLatitudeValid.value && isLongitudeValid.value && isFrameCountValid.value;
});


const initializeObjects = () => {
  if (!canvasRef.value) return;
  if (!earth || !sun || !moon || (FEATURE_FLAGS.VENUS_ENABLED && !venus) || !sceneManager) {
    sceneManager = new SceneManager(canvasRef.value);
    earth = new Earth();
    sun = new Sun();
    moon = new Moon();
    if (FEATURE_FLAGS.VENUS_ENABLED) {
      venus = new Venus();
    }
    earth.addToScene(sceneManager.scene);
    sun.addToScene(sceneManager.scene);
    moon.addToScene(sceneManager.scene);
    if (venus) {
      venus.addToScene(sceneManager.scene);
    }
    // Hide objects until data is loaded
    if (earth && earth.mesh && earth.getGridHelper() && earth.getAxesHelper() && earth.getHemisphereGrid()) {
      earth.mesh.visible = false;
      earth.getGridHelper().visible = false;
      earth.getAxesHelper().visible = false;
      earth.getHemisphereGrid().visible = false;
    }
    if (sun && sun.mesh && sun.getLight()) {
      sun.mesh.visible = false;
      sun.getLight().visible = false;
    }
    if (moon && moon.mesh) {
      moon.mesh.visible = false;
    }
    if (FEATURE_FLAGS.VENUS_ENABLED && venus && venus.mesh) {
      venus.mesh.visible = false;
    }
    sceneManager.startAnimation(updateAnimation);
  }
};

// Initialize Three.js scene when canvas is available (hasData becomes true)
watch(
  () => hasData.value,
  (newVal) => {
    if (newVal) {
      nextTick(() => {
        // Vue will set canvasRef.value after DOM update
        if (canvasRef.value) {
          initializeObjects();
        } else {
          // If still not set, try again on next tick
          nextTick(() => {
            if (canvasRef.value) {
              initializeObjects();
            }
          });
        }
      });
    }
  }
);

// Add window resize event listener on mount
onMounted(() => {
  window.addEventListener('resize', handleResize);
});

// Cleanup
onUnmounted(() => {
  if (sceneManager) {
    sceneManager.dispose();
  }
  // Remove window resize event listener
  window.removeEventListener('resize', handleResize);
});

// Load data from API
async function loadData() {
  await fetchBatchObservationsSSE(params.value);
  // Dismiss success toast before scene transition for consistent Playwright screenshots
  dismissSuccessToast();
  if (hasData.value) {
    if (!canvasRef.value) {
      await nextTick();
      // If still not set, manually query the DOM for the canvas
      if (!canvasRef.value) {
        const domCanvas = document.querySelector('.canvas-panel');
        if (domCanvas instanceof HTMLCanvasElement) {
          canvasRef.value = domCanvas;
        }
      }
    }
    if (!sun || !moon || !earth || (FEATURE_FLAGS.VENUS_ENABLED && !venus) || !sceneManager) {
      initializeObjects();
    }
    currentIndex.value = 0;
    calculateFrameInterval();
    updatePositions();
    // Set visibility for first frame from API data
    const frame = currentFrame.value;
    if (frame) {
      if (earth) {
        earth.mesh.visible = true;
        earth.getGridHelper().visible = true;
        earth.getAxesHelper().visible = true;
        earth.getHemisphereGrid().visible = false;
      }
      if (sun) {
        sun.mesh.visible = frame.sun.is_visible;
        sun.getLight().visible = frame.sun.is_visible;
      }
      if (moon) {
        moon.mesh.visible = frame.moon.is_visible;
      }
      if (venus && frame.venus) {
        venus.mesh.visible = frame.venus.is_visible;
      }
    }
  }
}

// Debug: Watch for changes in loading, sseFrames, sseExpectedFrameCount
watch([loading, sseFrames, sseExpectedFrameCount], ([loadingVal, framesVal, expectedVal]) => {
  const debugLoggingEnabled = false; // Set to true to enable detailed logging
  if (debugLoggingEnabled) {
    console.log('[watch] loading:', loadingVal, 'sseFrames.length:', framesVal.length, 'sseExpectedFrameCount:', expectedVal);
  }
});

// Calculate the time interval between frames based on actual datetime values
// Fixes #11: Animation now respects the actual time intervals in the data
// rather than using a fixed frame rate
function calculateFrameInterval() {
  if (!data.value || data.value.frames.length < 2) {
    frameIntervalMs.value = 1000; // Default to 1 second if we can't calculate
    return;
  }
  
  // Parse the first two frame datetimes to calculate the real-time interval
  const firstFrame = new Date(data.value.frames[0].datetime);
  const secondFrame = new Date(data.value.frames[1].datetime);
  
  // Validate that the dates are valid
  if (!isFinite(firstFrame.getTime()) || !isFinite(secondFrame.getTime())) {
    frameIntervalMs.value = 1000; // Fall back to default if dates are invalid
    return;
  }
  
  // Calculate the time difference in milliseconds
  const realTimeDiffMs = secondFrame.getTime() - firstFrame.getTime();
  
  // Validate that the time difference is positive
  if (realTimeDiffMs <= 0) {
    console.warn('Frame timestamps are not in chronological order or are identical. Using default interval.');
    frameIntervalMs.value = 1000; // Fall back to default if frames are out of order
    return;
  }
  
  // Scale to a reasonable animation speed (e.g., 1 real hour = 1 second of animation)
  // This gives us a base speed that makes sense for visualization
  const MILLISECONDS_PER_SECOND = 1000;
  const MILLISECONDS_PER_HOUR = 60 * 60 * 1000;
  const scaleFactor = MILLISECONDS_PER_SECOND / MILLISECONDS_PER_HOUR;
  frameIntervalMs.value = realTimeDiffMs * scaleFactor;
  
  // Ensure a minimum interval to prevent too-fast animations
  frameIntervalMs.value = Math.max(frameIntervalMs.value, 50);
}

// Update celestial object positions
function updatePositions() {
  const frame = currentFrame.value;
  if (!frame || !sun || !moon || !earth) return;
  
  // Update visibility based on frame data
  if (sun) {
    sun.mesh.visible = frame.sun.is_visible;
    sun.getLight().visible = frame.sun.is_visible;
  }
  if (moon) {
    moon.mesh.visible = frame.moon.is_visible;
  }
  if (venus && frame.venus) {
    venus.mesh.visible = frame.venus.is_visible;
  }
  if (earth) {
    // Earth is always visible during animation
    earth.mesh.visible = true;
    earth.getGridHelper().visible = true;
    earth.getAxesHelper().visible = true;
    earth.getHemisphereGrid().visible = (viewMode.value === 'SKY');
  }

  sun.updatePosition(
    frame.sun.azimuth,
    frame.sun.altitude,
    frame.sun.is_visible,
    viewMode.value
  );

  moon.updatePosition(
    frame.moon.azimuth,
    frame.moon.altitude,
    frame.moon.is_visible,
    viewMode.value
  );

  if (FEATURE_FLAGS.VENUS_ENABLED && frame.venus && venus) {
    venus.updatePosition(
      frame.venus.azimuth,
      frame.venus.altitude,
      frame.venus.is_visible,
      viewMode.value
    );
  }

  moon.updatePhase(frame.moon_phase.illumination * 100);
  
  // Update label billboard orientations to face camera
  if (sceneManager) {
    sun.updateLabelBillboard(sceneManager.camera);
    moon.updateLabelBillboard(sceneManager.camera);
    if (FEATURE_FLAGS.VENUS_ENABLED && venus) {
      venus.updateLabelBillboard(sceneManager.camera);
    }
  }
}

// Switch view mode
function setViewMode(mode: '3D' | 'SKY') {
  viewMode.value = mode;
  if (sceneManager && earth && sun && moon) {
    sceneManager.setViewMode(mode);
    earth.setViewMode(mode);
    sun.setViewMode(mode.toLowerCase() as 'sky' | '3d');
    moon.setViewMode(mode.toLowerCase() as 'sky' | '3d');
    if (venus) {
      venus.setViewMode(mode.toLowerCase() as 'sky' | '3d');
    }
    updatePositions();
  }
}

// Animation loop callback
function updateAnimation() {
  if (!isAnimating.value || !data.value) return;
  
  const now = Date.now();
  const delta = now - lastTime.value;
  
  // Use calculated frame interval scaled by animation speed
  // Higher speed = shorter interval = faster animation
  const interval = frameIntervalMs.value / animationSpeed.value;
  
  if (delta > interval) {
    lastTime.value = now;
    currentIndex.value++;
    
    if (currentIndex.value >= data.value.frames.length) {
      currentIndex.value = 0; // Loop animation
    }
    
    updatePositions();
  }
}

function toggleAnimation() {
  isAnimating.value = !isAnimating.value;
  if (isAnimating.value) {
    lastTime.value = Date.now();
  }
}

function resetAnimation() {
  isAnimating.value = false;
  currentIndex.value = 0;
  // Reset camera to initial position for current view mode
  if (sceneManager) {
    sceneManager.resetCamera();
  }
  // Update all objects to match frame 1's state (positions, visibility, etc)
  updatePositions();
  toast.info(t('ui.status.animationReset'), 3000);
}
function recentreCamera() {
  if (sceneManager) {
    sceneManager.resetCamera();
  }
}

function clearData() {
  isAnimating.value = false;
  currentIndex.value = 0;
  clearApiData();
  // Dispose and null out scene objects so they are recreated on next load
  if (sceneManager) {
    sceneManager.dispose();
    sceneManager = null;
  }
  sun = null;
  moon = null;
  earth = null;
}

// Window resize event handler
function handleResize() {
  const canvas = canvasRef.value;
  if (!canvas) return;
  const parent = canvas.parentElement;
  const dpr = window.devicePixelRatio || 1;
  const width = (parent?.clientWidth || window.innerWidth);
  const height = (parent?.clientHeight || window.innerHeight);
  // Set canvas rendering size for high-DPI
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  // Set CSS size
  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';
  // Update Three.js renderer and camera if available
  if (sceneManager) {
    sceneManager.renderer.setSize(width, height, false);
    sceneManager.camera.aspect = width / height;
    sceneManager.camera.updateProjectionMatrix();
  }
}

// --- Responsive canvas sizing ---
let resizeObserver: ResizeObserver | null = null;

// Initialize Three.js scene and observe canvas size
watch(
  () => hasData.value,
  (newVal) => {
    if (newVal) {
      nextTick(() => {
        if (canvasRef.value) {
          initializeObjects();
          // Set up ResizeObserver to keep canvas and renderer sized to container
          if (resizeObserver) resizeObserver.disconnect();
          resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
              const canvas = entry.target as HTMLCanvasElement;
              const parent = canvas.parentElement;
              if (parent) {
                const width = parent.clientWidth;
                const height = parent.clientHeight;
                if (canvas.width !== width || canvas.height !== height) {
                  canvas.width = width;
                  canvas.height = height;
                  if (sceneManager && sceneManager.renderer) {
                    sceneManager.renderer.setSize(width, height, false);
                  }
                }
              }
            }
          });
          resizeObserver.observe(canvasRef.value);
        } else {
          nextTick(() => {
            if (canvasRef.value) {
              initializeObjects();
              if (resizeObserver) resizeObserver.disconnect();
              resizeObserver = new ResizeObserver(entries => {
                for (const entry of entries) {
                  const canvas = entry.target as HTMLCanvasElement;
                  const parent = canvas.parentElement;
                  if (parent) {
                    const width = parent.clientWidth;
                    const height = parent.clientHeight;
                    if (canvas.width !== width || canvas.height !== height) {
                      canvas.width = width;
                      canvas.height = height;
                      if (sceneManager && sceneManager.renderer) {
                        sceneManager.renderer.setSize(width, height, false);
                      }
                    }
                  }
                }
              });
              resizeObserver.observe(canvasRef.value);
            }
          });
        }
      });
    } else {
      if (resizeObserver) resizeObserver.disconnect();
    }
  }
);

onUnmounted(() => {
  if (sceneManager) {
    sceneManager.dispose();
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  window.removeEventListener('resize', handleResize);
});
</script>

<style scoped>

.astronomy-scene {
  position: relative;
  overflow: hidden;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-size: 0.9em;
}

.form-group input {
  width: 100%;
  padding: 8px;
  border: 1px solid #555;
  border-radius: 4px;
  background: #222;
  color: white;
  font-size: 0.9em;
}

/* Hide the native calendar picker button on the side-panel date inputs.
   The DateRangePicker on the map panel is the intended date-entry point. */
.controls-panel input[type="date"]::-webkit-calendar-picker-indicator,
.controls-panel input[type="time"]::-webkit-calendar-picker-indicator {
  display: none;
}

.form-group input.invalid {
  border-color: #ff4444;
  background: #331111;
}

.error-message {
  display: block;
  color: #ff4444;
  font-size: 0.8em;
  margin-top: 4px;
}

button {
  width: 100%;
  padding: 10px;
  margin-bottom: 10px;
  background: #004FA3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
}

.view-toggle {
  display: flex;
  gap: 5px;
  margin-bottom: 15px;
}

.view-toggle button {
  flex: 1;
  margin-bottom: 0;
  background: #333;
}

.view-toggle button.active {
  background: #004FA3;
  font-weight: bold;
}

.view-toggle button:hover:not(.active) {
  background: #444;
}

button:hover:not(:disabled) {
  background: #003d82;
}

button:disabled {
  background: #555;
  cursor: not-allowed;
}

.loading {
  padding: 10px;
  background: rgba(255, 165, 0, 0.2);
  border-radius: 4px;
  margin-bottom: 10px;
}

.error {
  padding: 10px;
  background: rgba(255, 0, 0, 0.2);
  border: 1px solid #ff0000;
  border-radius: 4px;
  margin-bottom: 10px;
  font-size: 0.9em;
}

.date-range-row {
  margin-top: 12px;
  width: 100%;
  display: flex;
  justify-content: flex-start;
}

.page-heading {
  margin: 0 0 12px 0;
  font-size: 1.2rem;
  font-weight: 700;
  color: #ffffff;
}

.date-range-panel {
  min-width: 220px;
  max-width: 350px;
  width: 100%;
}

.progress-bar-container {
  width: 100%;
  height: 24px;
  background: #eee;
  border-radius: 12px;
  overflow: hidden;
  margin-bottom: 6px;
  position: relative;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #4caf50 0%, #2196f3 100%);
  transition: width 0.3s;
  position: absolute;
  left: 0;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: bold;
  font-size: 1em;
}
.progress-text {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-weight: bold;
  font-size: 1em;
  color: #000;
  background: transparent;
  z-index: 2;
  pointer-events: none;
}

button {
  width: 100%;
  padding: 10px;
  margin-bottom: 10px;
  background: #004FA3;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
}

.celestial-panel {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin-top: 15px;
  padding: 0;
  border-top: 1px solid #555;
  font-size: 0.85em;
}

/* Ensure canvas always fills its parent container */
.canvas-panel {
  width: 100%;
  height: 100%;
  display: block;
  min-width: 0;
  min-height: 0;
  box-sizing: border-box;
}
</style>