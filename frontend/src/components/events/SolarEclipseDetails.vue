<template>
  <dl class="eclipse-details">
    <div v-if="event.greatest_eclipse_time" class="detail-row">
      <dt>{{ t('events.solar.greatestEclipse') }}</dt>
      <dd>{{ formatTime(event.greatest_eclipse_time) }}</dd>
    </div>
    <div v-if="event.size_ratio != null" class="detail-row">
      <dt>{{ t('events.solar.sizeRatio') }}</dt>
      <dd>{{ event.size_ratio.toFixed(4) }}</dd>
    </div>

    <template v-if="event.contact_times">
      <h3 class="details-heading">{{ t('events.solar.contactTimes') }}</h3>
      <div v-for="key in contactKeys" :key="key" class="detail-row">
        <dt>{{ t(`events.solar.${labelKey(key)}`) }}</dt>
        <dd>{{ formatTime(event.contact_times[key]) }}</dd>
      </div>
    </template>
  </dl>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useI18n } from 'vue-i18n';
import type { AstronomicalEvent } from '@/types/api.types';

const props = defineProps<{
  event: AstronomicalEvent;
}>();

const { t, locale } = useI18n();

// Ordered chronologically; keys match api.services.eclipse_contact_times output
const CONTACT_ORDER = [
  'eclipse_begins',
  'central_phase_begins',
  'central_phase_ends',
  'eclipse_ends',
];

const LABEL_KEYS: Record<string, string> = {
  eclipse_begins: 'eclipseBegins',
  central_phase_begins: 'centralPhaseBegins',
  central_phase_ends: 'centralPhaseEnds',
  eclipse_ends: 'eclipseEnds',
};

function labelKey(key: string): string {
  return LABEL_KEYS[key];
}

// Only rendered when the template's v-if="event.contact_times" is truthy.
const contactKeys = computed(() => {
  const times = props.event.contact_times!;
  return CONTACT_ORDER.filter((key) => times[key]);
});

function formatTime(value: string): string {
  // Backend returns astropy Time.iso strings: "YYYY-MM-DD HH:MM:SS.sss" (UTC, space-separated)
  const parsed = new Date(`${value.replace(' ', 'T')}Z`);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat(locale.value, { timeStyle: 'medium' }).format(parsed);
}
</script>

<style scoped>
.eclipse-details {
  margin: 0;
}

.details-heading {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #aaa;
  margin: 0.75rem 0 0.4rem 0;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.2rem 0;
  border-bottom: 1px dashed #333;
}

.detail-row dt {
  color: #aaa;
}

.detail-row dd {
  margin: 0;
  font-weight: 600;
  color: #fff;
}
</style>
