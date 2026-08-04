<template>
  <li class="event-item">
    <button
      v-if="eclipseOccurs"
      type="button"
      class="event-summary"
      :aria-expanded="expanded"
      :aria-controls="detailsId"
      @click="expanded = !expanded"
    >
      <span class="event-date">{{ formattedDate }}</span>
      <span class="event-type">{{ eventType }}</span>
      <i class="fa" :class="expanded ? 'fa-chevron-up' : 'fa-chevron-down'" aria-hidden="true"></i>
    </button>
    <div v-else class="event-summary event-summary-static">
      <span class="event-date">{{ formattedDate }}</span>
      <span class="event-type">{{ eventType }}</span>
    </div>
    <div v-if="eclipseOccurs && expanded" :id="detailsId" class="event-details">
      <slot />
    </div>
  </li>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import type { AstronomicalEventType } from '@/types/api.types';

let instanceCounter = 0;

const props = defineProps<{
  date: string;
  eventType: AstronomicalEventType;
  eclipseOccurs: boolean;
}>();

const { locale } = useI18n();
const expanded = ref(false);
const detailsId = `event-details-${++instanceCounter}`;

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

.event-summary:hover {
  background: #262626;
}

.event-summary-static {
  cursor: default;
}

.event-summary-static:hover {
  background: none;
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

.event-details {
  padding: 0 1rem 1rem 1rem;
  border-top: 1px solid #333;
  font-size: 0.9rem;
}
</style>
