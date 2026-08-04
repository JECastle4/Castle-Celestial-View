<template>
  <dl class="eclipse-details">
    <div v-if="event.greatest_eclipse_time" class="detail-row">
      <dt>{{ t('events.lunar.greatestEclipse') }}</dt>
      <dd>{{ formatTime(event.greatest_eclipse_time) }}</dd>
    </div>
    <div v-if="event.umbral_magnitude != null" class="detail-row">
      <dt>{{ t('events.lunar.umbralMagnitude') }}</dt>
      <dd>{{ event.umbral_magnitude.toFixed(4) }}</dd>
    </div>
    <div v-if="event.penumbral_magnitude != null" class="detail-row">
      <dt>{{ t('events.lunar.penumbralMagnitude') }}</dt>
      <dd>{{ event.penumbral_magnitude.toFixed(4) }}</dd>
    </div>

    <template v-if="event.contact_times">
      <h3 class="details-heading">{{ t('events.lunar.contactTimes') }}</h3>
      <div v-for="key in contactKeys" :key="key" class="detail-row">
        <dt>{{ t(`events.lunar.${key}`) }}</dt>
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

// Ordered so contact times display chronologically (P1 -> U1 -> U2 -> U3 -> U4 -> P4)
const CONTACT_ORDER = ['p1', 'u1', 'u2', 'u3', 'u4', 'p4'];

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
