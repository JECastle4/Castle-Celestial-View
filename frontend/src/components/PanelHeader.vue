<template>
  <div class="panel-header">
    <div class="header-content">
      <div class="frame-info">
        <span class="frame-counter">
          {{ t('astronomy.frame') }}: <strong>{{ currentFrameIndex + 1 }} / {{ totalFrames }}</strong>
        </span>
      </div>

      <div class="datetime-info">
        <i class="fa fa-calendar" aria-hidden="true"></i>
        <span>{{ formattedDateTime }}</span>
      </div>

      <div class="location-info">
        <i class="fa fa-location-dot" aria-hidden="true"></i>
        <span>{{ formattedLocation }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import type { LocationModel } from '@/types/api.types';
import { normalizeLocaleForIntl } from '@/utils/locale';

const { t, locale } = useI18n();

const props = defineProps<{
  currentFrameIndex: number;
  totalFrames: number;
  datetime: string;
  location: LocationModel;
}>();

const formattedDateTime = computed(() => {
  // Parse ISO datetime format: 2026-02-01T12:00:00Z (API always includes 'Z' for UTC)
  try {
    const date = new Date(props.datetime);
    // Normalize app locale to valid BCP-47 tag before calling toLocaleString,
    // since some app locales (e.g., en-UK, xx-reverse) are non-standard and not
    // recognized by Intl APIs. Ensures consistent formatting and prevents Playwright
    // screenshot drift from fallback to raw ISO strings.
    const intlLocale = normalizeLocaleForIntl(locale.value);
    return date.toLocaleString(intlLocale, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      timeZone: 'UTC'
    });
  } catch {
    return props.datetime;
  }
});

const formattedLocation = computed(() => {
  const lat = props.location.latitude >= 0 ? 'N' : 'S';
  const lon = props.location.longitude >= 0 ? 'E' : 'W';
  return `${Math.abs(props.location.latitude).toFixed(2)}°${lat}, ${Math.abs(props.location.longitude).toFixed(2)}°${lon}`;
});
</script>

<style scoped>
.panel-header {
  padding: 0.75rem 1rem;
  background: linear-gradient(135deg, rgba(10, 10, 40, 0.9), rgba(20, 20, 60, 0.9));
  border-radius: 6px 6px 0 0;
  border: 1px solid rgba(100, 150, 200, 0.4);
  border-bottom: 2px solid rgba(100, 150, 200, 0.6);
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.frame-info,
.datetime-info,
.location-info {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  color: #90d9ff;
}

.frame-counter {
  font-family: 'Courier New', monospace;
}

.frame-counter strong {
  color: #ffffff;
  font-weight: 600;
}

@media (max-width: 768px) {
  .panel-header {
    padding: 0.5rem 0.75rem;
  }

  .frame-info,
  .datetime-info,
  .location-info {
    font-size: 0.85rem;
  }

  .header-content {
    gap: 0.35rem;
  }
}
</style>
