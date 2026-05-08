<template>
  <div class="ol-map-wrapper">
    <span :id="`${instanceId}-desc`" class="sr-only">{{ mapDescText }}</span>
    <span :id="`${instanceId}-announce`" class="sr-only" aria-live="polite" aria-atomic="true">{{ mapAnnounceText }}</span>
    <div
      ref="mapContainer"
      class="ol-map"
      role="application"
      :aria-label="t('map.ariaLabel')"
      :aria-describedby="`${instanceId}-desc`"
      tabindex="0"
    ></div>
    <div ref="crosshairOverlay" class="map-crosshair" aria-hidden="true"></div>
  </div>
</template>

<script setup>
// Custom OpenLayers control for pin tool
import Control from 'ol/control/Control'

function createPinToolControl(onClick, { buttonTitle } = {}) {
  const img = document.createElement('img')
  img.src = '/map-pin.png'
  img.alt = ''
  img.setAttribute('aria-hidden', 'true')
  img.width = 20
  img.height = 20
  const button = document.createElement('button')
  button.appendChild(img)
  button.title = buttonTitle ?? 'Place Pin'
  button.setAttribute('aria-label', buttonTitle ?? 'Place Pin')
  button.setAttribute('aria-pressed', 'false')
  button.style.padding = '0px'
  button.style.background = '#fff'
  button.style.border = '0px solid #ccc'
  button.style.borderRadius = '0px'
  button.style.marginTop = '0px'
  button.style.cursor = 'pointer'
  button.addEventListener('click', onClick)
  const element = document.createElement('div')
  element.className = 'ol-control ol-pin-tool'
  element.appendChild(button)
  return { control: new Control({ element }), img, button }
}
import { onMounted, ref, computed, watch, onBeforeUnmount, useId } from 'vue'
import { useI18n } from 'vue-i18n'
import 'ol/ol.css'
import Map from 'ol/Map'
import View from 'ol/View'
import TileLayer from 'ol/layer/Tile'
import OSM from 'ol/source/OSM'
import Zoom from 'ol/control/Zoom'
import Attribution from 'ol/control/Attribution'
import { fromLonLat, toLonLat } from 'ol/proj'
import Feature from 'ol/Feature'
import Point from 'ol/geom/Point'
import VectorSource from 'ol/source/Vector'
import VectorLayer from 'ol/layer/Vector'
import Style from 'ol/style/Style'
import Icon from 'ol/style/Icon'

const props = defineProps({
  enablePinTool: { type: Boolean, default: false }
})
const emit = defineEmits(['pin-placed'])

const { t } = useI18n()
const instanceId = `map-${useId()}`

const mapContainer = ref(null)
const crosshairOverlay = ref(null)
const pinModeActive = ref(false)
const announceKey = ref('')
const pinButtonTitle = computed(() => t('map.pinTool.buttonTitle'))
const mapDescText = computed(() =>
  pinModeActive.value ? t('map.pinTool.activeDescription') : t('map.description')
)
const mapAnnounceText = computed(() =>
  announceKey.value ? t(`map.pinTool.${announceKey.value}`) : ''
)
let mapInstance = null
let pinLayer = null
let pinSource = null
let keydownHandler = null
let pinToolImg = null
let pinToolButton = null

watch(pinButtonTitle, (newTitle) => {
  if (pinToolButton) {
    pinToolButton.setAttribute('aria-label', newTitle)
    pinToolButton.title = newTitle
  }
})

onMounted(() => {
      // Ensure map resizes after mount
      setTimeout(() => {
        if (mapInstance) mapInstance.updateSize();
      }, 0);

    function activatePinMode() {
      pinModeActive.value = true
      if (pinToolImg) pinToolImg.src = '/map-pin-selected.png'
      if (pinToolButton) pinToolButton.setAttribute('aria-pressed', 'true')
      mapContainer.value.style.cursor = 'crosshair'
      if (crosshairOverlay.value) crosshairOverlay.value.style.display = 'block'
      announceKey.value = 'activeDescription'
      mapContainer.value.focus()
    }

    function deactivatePinMode(reason = 'cancelled') {
      pinModeActive.value = false
      if (pinToolImg) pinToolImg.src = '/map-pin.png'
      if (pinToolButton) pinToolButton.setAttribute('aria-pressed', 'false')
      mapContainer.value.style.cursor = ''
      if (crosshairOverlay.value) crosshairOverlay.value.style.display = 'none'
      announceKey.value = reason === 'placed' ? 'placed' : 'cancelled'
    }

  mapInstance = new Map({
    target: mapContainer.value,
    layers: [
      new TileLayer({
        source: new OSM(),
      }),
    ],
    view: new View({
      center: [0, 0], // [lon, lat] in EPSG:3857
      zoom: 2,
    }),
    controls: [
      new Zoom(),
      ...(props.enablePinTool ? (() => {
        const { control, img, button } = createPinToolControl(() => {
          if (pinModeActive.value) {
            deactivatePinMode('cancelled')
          } else {
            activatePinMode()
          }
        }, { buttonTitle: pinButtonTitle.value })
        pinToolImg = img
        pinToolButton = button
        return [control]
      })() : []),
      new Attribution({
        collapsible: false,
        className: 'ol-attribution bottom-left',
      }),
    ],
  })

  // Pin tool setup
  if (props.enablePinTool) {
    pinSource = new VectorSource()
    pinLayer = new VectorLayer({
      source: pinSource,
      style: new Style({
        image: new Icon({
          src: '/map-pin-selected.png',
          anchor: [0.5, 1],
          scale: 1.2
        })
      })
    })
    mapInstance.addLayer(pinLayer)

    function placePinAt(coords) {
      pinSource.clear()
      const feature = new Feature({
        geometry: new Point(coords)
      })
      pinSource.addFeature(feature)
      const [lon, lat] = toLonLat(coords)
      emit('pin-placed', { lat, lon })
      deactivatePinMode('placed')
    }

    mapInstance.on('click', function (evt) {
      if (!pinModeActive.value) return
      placePinAt(evt.coordinate)
    })

    keydownHandler = function (e) {
      if (!pinModeActive.value) return
      if (e.key === 'Escape') {
        deactivatePinMode()
        e.stopPropagation()
      } else if (e.key === 'Enter' && e.target === mapContainer.value) {
        const center = mapInstance.getView().getCenter()
        placePinAt(center)
        e.preventDefault()
        e.stopPropagation()
      }
    }
    mapContainer.value.addEventListener('keydown', keydownHandler)
  }
})

onBeforeUnmount(() => {
  if (keydownHandler && mapContainer.value) {
    mapContainer.value.removeEventListener('keydown', keydownHandler)
    keydownHandler = null
  }
  if (mapInstance) {
    mapInstance.setTarget(null)
    mapInstance = null
    if (pinLayer && mapInstance) {
      mapInstance.removeLayer(pinLayer)
      pinLayer = null
      pinSource = null
    }
  }
})
</script>

<style scoped>
.ol-map-wrapper {
  position: relative;
}

.map-crosshair {
  display: none;
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 999;
}

.map-crosshair::before,
.map-crosshair::after {
  content: '';
  position: absolute;
  background: rgba(220, 50, 50, 0.85);
}

/* Horizontal line */
.map-crosshair::before {
  top: 50%;
  left: 0;
  right: 0;
  height: 1px;
  transform: translateY(-50%);
}

/* Vertical line */
.map-crosshair::after {
  left: 50%;
  top: 0;
  bottom: 0;
  width: 1px;
  transform: translateX(-50%);
}

.ol-pin-tool {
  position: absolute;
  left: 8px;
  top: 72px;
  z-index: 1001;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.ol-map {
  width: 100%;
  height: 100%;
  min-height: 400px;
  border: 1px solid #ccc;
  :deep(.ol-viewport) {
    height: 400px !important;
    min-height: 400px !important;
  }

  :global(.ol-pin-tool) {
    position: absolute;
    left: 8px;
    top: 72px;
    z-index: 1001;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
  }
  right: auto !important;
  bottom: 8px !important;
  top: auto !important;
  background: rgba(255,255,255,0.9);
  color: #333;
  font-size: 0.85em;
  border-radius: 4px;
  padding: 2px 8px;
  z-index: 1000 !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  display: block !important;
}
/* Ensure OpenLayers attribution is always visible */
.ol-attribution {
  opacity: 1 !important;
  visibility: visible !important;
  z-index: 1000 !important;
}

/* Ensure zoom buttons meet WCAG 2.5.8 touch target minimum (24×24px) */
:deep(.ol-zoom-in),
:deep(.ol-zoom-out) {
  width: 24px !important;
  height: 24px !important;
  line-height: 24px !important;
  font-size: 16px !important;
}

:deep(.ol-zoom-out) {
  margin-top: 4px !important;
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
