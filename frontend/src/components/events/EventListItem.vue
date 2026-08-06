<template>
  <li class="event-item">
    <button
      type="button"
      class="event-summary"
      :class="{ 'event-summary-static': !eclipseOccurs }"
      :aria-expanded="eclipseOccurs ? expanded : false"
      :aria-controls="eclipseOccurs ? detailsId : undefined"
      :aria-label="eclipseOccurs ? undefined : t('events.noEclipse')"
      @click="eclipseOccurs && (expanded = !expanded)"
    >
      <span class="event-date" :aria-label="formattedDate">{{ formattedDate }}</span>
      <span class="event-type">{{ eventType }}</span>
      <i
        v-if="eclipseOccurs"
        class="fa"
        :class="expanded ? 'fa-chevron-up' : 'fa-chevron-down'"
        aria-hidden="true"
      ></i>
      <i v-else class="fa fa-circle no-eclipse-indicator" aria-hidden="true"></i>
    </button>
    <div
      v-if="eclipseOccurs && expanded"
      ref="detailsRegion"
      :id="detailsId"
      class="event-details"
      role="region"
      aria-live="assertive"
      :aria-labelledby="`${detailsId}-heading`"
      tabindex="0"
    >
      <h2 :id="`${detailsId}-heading`">{{ t('events.eclipseDetails') }}</h2>
      <slot />
    </div>
  </li>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import type { AstronomicalEventType } from '@/types/api.types';

let instanceCounter = 0;

const props = defineProps<{
  date: string;
  eventType: AstronomicalEventType;
  eclipseOccurs: boolean;
}>();

const { locale, t } = useI18n();
const expanded = ref(false);
const detailsRegion = ref<HTMLDivElement | null>(null);
const detailsId = `event-details-${++instanceCounter}`;

// Focus the details region when the panel expands
watch(expanded, async (newValue) => {
  if (newValue) {
    await nextTick();
    detailsRegion.value?.focus();
  }
});

const formattedDate = computed(() => {
  // Backend returns astropy Time.iso strings: "YYYY-MM-DD HH:MM:SS.sss" (UTC, space-separated)
  const parsed = new Date(`${props.date.replace(' ', 'T')}Z`);
  if (Number.isNaN(parsed.getTime())) return props.date;
  return new Intl.DateTimeFormat(locale.value, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(parsed);
});
</script>

<style scoped>
.event-item {
  list-style: none;
  border: 1px solid #333;
  border-radius: 6px;
  margin-bottom: 0.75rem;
  background: #1e1e1e;
  overflow: hidden;
}

.event-summary {
  display: flex;
  align-items: center;
  gap: 1rem;
  width: 100%;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  color: #fff;
  font-size: 0.95rem;
  cursor: pointer;
  text-align: left;
}

.event-summary:not(.event-summary-static):hover {
  background: #262626;
}

.event-summary:focus-visible {
  outline: 2px solid #0078d4;
  outline-offset: -2px;
  background: #262626;
}

.event-summary-static {
  cursor: default;
}

.event-date {
  flex: 1 1 auto;
  font-weight: 600;
}

.event-type {
  flex: 0 0 auto;
  text-align: right;
  min-width: 120px;
  color: #aaa;
}

.no-eclipse-indicator {
  font-size: 0.6em;
  color: #888;
}

.event-details {
  padding: 0 1rem 1rem 1rem;
  border-top: 1px solid #333;
  font-size: 0.9rem;
}

.event-details:focus-visible {
  outline: 2px solid #0078d4;
  outline-offset: -2px;
}

.event-details h2 {
  font-size: 0.95rem;
  font-weight: 600;
  color: #fff;
  margin: 0.75rem 0 0.5rem 0;
  padding: 0;
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
  border-width: 0;
}
</style>
