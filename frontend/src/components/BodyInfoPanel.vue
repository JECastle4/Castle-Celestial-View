<template>
  <div class="body-info-panel">
    <template v-if="bodyData">
      <!-- Visibility Status -->
      <div class="info-section visibility-section">
        <div :class="['visibility-badge', { visible: bodyData.is_visible, hidden: !bodyData.is_visible }]">
          <i :class="`fa ${bodyData.is_visible ? 'fa-eye' : 'fa-eye-slash'}`" aria-hidden="true"></i>
          {{ t(bodyData.is_visible ? 'astronomy.yes' : 'astronomy.no') }}
        </div>
      </div>

      <!-- Celestial Coordinates (Primary) -->
      <div class="info-section coordinates-section">
        <h3 class="section-title">{{ t('astronomy.celestialCoordinates') }}</h3>
        <div class="coordinate-pair">
          <div class="coordinate-item">
            <span class="label">RA:</span>
            <span class="value">{{ formatRA(bodyData.ra_degrees) }}</span>
          </div>
          <div class="coordinate-item">
            <span class="label">Dec:</span>
            <span class="value">{{ formatDec(bodyData.dec_degrees) }}</span>
          </div>
        </div>
      </div>

      <!-- Horizontal Coordinates (Secondary) -->
      <div class="info-section coordinates-section">
        <h3 class="section-title">{{ t('astronomy.horizontalCoordinates') }}</h3>
        <div class="coordinate-pair">
          <div class="coordinate-item">
            <span class="label">{{ t('astronomy.altitude') }}:</span>
            <span class="value">{{ formatAltitude(bodyData.altitude) }}</span>
          </div>
          <div class="coordinate-item">
            <span class="label">{{ t('astronomy.azimuth') }}:</span>
            <span class="value">{{ formatAzimuth(bodyData.azimuth) }}</span>
          </div>
        </div>
      </div>

      <!-- Moon-specific Data -->
      <div v-if="bodyId === 'moon' && moonPhaseData" class="info-section moon-section">
        <h3 class="section-title">{{ t('astronomy.moonPhase') }}</h3>
        <div class="phase-info">
          <div class="phase-name">
            <span class="label">{{ t('astronomy.phase') }}:</span>
            <span class="value">{{ moonPhaseData.phase_name }}</span>
          </div>
          <div class="illumination">
            <span class="label">{{ t('astronomy.illumination') }}:</span>
            <span class="value">{{ formatPercentage(moonPhaseData.illumination) }}</span>
          </div>
          <div class="phase-angle">
            <span class="label">{{ t('astronomy.phaseAngle') }}:</span>
            <span class="value">{{ formatAngle(moonPhaseData.phase_angle) }}</span>
          </div>
        </div>
      </div>

      <!-- Venus-specific Data -->
      <div v-if="bodyId === 'venus' && venusPhasData" class="info-section venus-section">
        <h3 class="section-title">{{ t('astronomy.venusData') }}</h3>
        <div class="venus-info">
          <div class="phase-name">
            <span class="label">{{ t('astronomy.phase') }}:</span>
            <span class="value">{{ venusPhasData.phase_name }}</span>
          </div>
          <div class="illumination">
            <span class="label">{{ t('astronomy.illumination') }}:</span>
            <span class="value">{{ formatPercentage(venusPhasData.illumination) }}</span>
          </div>
          <div class="naked-eye">
            <span class="label">{{ t('astronomy.nakedEyeVisible') }}:</span>
            <span :class="['value', { yes: venusPhasData.naked_eye_visible, no: !venusPhasData.naked_eye_visible }]">
              {{ venusPhasData.naked_eye_visible ? t('astronomy.yes') : t('astronomy.no') }}
            </span>
          </div>
        </div>
      </div>
    </template>
    <template v-else>
      <div class="no-data">
        {{ t('ui.noData') }}
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import type { CelestialPosition, MoonPhaseData, VenusPhaseData } from '@/types/api.types';

const { t } = useI18n();

defineProps<{
  bodyId: string;
  bodyData?: CelestialPosition;
  moonPhaseData?: MoonPhaseData;
  venusPhasData?: VenusPhaseData;
}>();

const formatRA = (raDegrees: number): string => {
  // Format RA: degrees with 4 decimal places
  return `${raDegrees.toFixed(4)}°`;
};

const formatDec = (decDegrees: number): string => {
  // Format Dec: degrees with 4 decimal places (including sign)
  const sign = decDegrees >= 0 ? '+' : '';
  return `${sign}${decDegrees.toFixed(4)}°`;
};

const formatAltitude = (altitude: number): string => {
  return `${altitude.toFixed(2)}°`;
};

const formatAzimuth = (azimuth: number): string => {
  return `${azimuth.toFixed(2)}°`;
};

const formatAngle = (angle: number): string => {
  return `${angle.toFixed(2)}°`;
};

const formatPercentage = (value: number): string => {
  return `${(value * 100).toFixed(1)}%`;
};
</script>

<style scoped>
.body-info-panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, rgba(10, 10, 40, 0.8), rgba(20, 20, 60, 0.8));
  border-radius: 8px;
  border: 1px solid rgba(100, 150, 200, 0.3);
  min-height: 200px;
}

.no-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #a0d8ff;
  font-style: italic;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.section-title {
  margin: 0;
  font-size: 0.95rem;
  color: #90d9ff;
  font-weight: 600;
  border-bottom: 1px solid rgba(100, 150, 200, 0.3);
  padding-bottom: 0.5rem;
}

.visibility-section {
  display: flex;
  justify-content: center;
  padding: 0.5rem 0;
}

.visibility-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  border: 2px solid;
  font-size: 0.95rem;
}

.visibility-badge.visible {
  background: rgba(40, 167, 69, 0.2);
  border-color: rgba(40, 167, 69, 0.6);
  color: #66ff66;
}

.visibility-badge.hidden {
  background: rgba(220, 53, 69, 0.2);
  border-color: rgba(220, 53, 69, 0.6);
  color: #ff6666;
}

.coordinates-section {
  gap: 0.75rem;
}

.coordinate-pair {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}

.coordinate-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  padding: 0.75rem;
  background: rgba(50, 100, 150, 0.2);
  border-radius: 4px;
  border: 1px solid rgba(100, 150, 200, 0.2);
}

.label {
  font-size: 0.85rem;
  color: #90d9ff;
  font-weight: 500;
}

.value {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 1.1rem;
  color: #ffffff;
  font-weight: 600;
}

.moon-section,
.venus-section {
  gap: 0.5rem;
}

.phase-info,
.venus-info {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  background: rgba(50, 100, 150, 0.2);
  border-radius: 4px;
  border: 1px solid rgba(100, 150, 200, 0.2);
}

.phase-name,
.illumination,
.phase-angle,
.naked-eye {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.value.yes {
  color: #66ff66;
  font-weight: 600;
}

.value.no {
  color: #ff6666;
  font-weight: 600;
}

@media (max-width: 768px) {
  .body-info-panel {
    padding: 0.75rem;
    gap: 0.75rem;
  }

  .coordinate-pair {
    grid-template-columns: 1fr;
  }

  .coordinate-item {
    padding: 0.5rem;
  }

  .section-title {
    font-size: 0.9rem;
  }
}
</style>
