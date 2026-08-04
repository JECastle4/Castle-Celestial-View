<template>
  <div class="events-view">
    <AppHeader
      :hasData="false"
      selectedBody=""
      currentMode="eclipses"
      @select-mode="onSelectMode"
    />
    <div class="events-content">
      <h1>{{ t('events.title') }}</h1>
      <p class="events-description">{{ t('events.description') }}</p>

      <DateRangePicker
        class="date-range-panel"
        :initialStartDate="startDate"
        :initialEndDate="endDate"
        @update:dates="onDateRangeSelected"
      />

      <button type="button" class="search-btn" :disabled="loading" @click="search">
        <i class="fa fa-magnifying-glass" aria-hidden="true" style="margin-right: 0.5em;"></i>
        {{ t('events.search') }}
      </button>

      <div v-if="loading" class="loading">
        <div class="progress-label">
          <i class="fa fa-spinner fa-spin" aria-hidden="true" style="margin-right: 0.5em;"></i>
          {{ t('events.searching') }} {{ t('events.eventsReceived', { count: sseEventCount }) }}
        </div>
        <button type="button" class="cancel-btn" @click="cancelSSE">
          <i class="fa fa-circle-xmark" aria-hidden="true" style="margin-right: 0.5em;"></i>
          {{ t('buttons.cancel') }}
        </button>
      </div>
      <div v-if="error" class="error">{{ error }}</div>

      <template v-if="!loading && !error">
        <ul v-if="events.length" class="event-list">
          <EventListItem
            v-for="ev in events"
            :key="ev.date"
            :date="ev.date"
            :eventType="ev.event_type"
            :eclipseType="ev.eclipse_type"
            :eclipseOccurs="ev.eclipse_occurs"
          >
            <LunarEclipseDetails v-if="ev.event_type === 'full_moon'" :event="ev" />
            <SolarEclipseDetails v-else :event="ev" />
          </EventListItem>
        </ul>
        <p v-else-if="hasSearched" class="empty-state">{{ t('events.noResults') }}</p>
      </template>

      <div v-if="pagination && pagination.total_pages > 1" class="pagination">
        <button
          type="button"
          :disabled="pagination.page <= 1 || loading"
          @click="goToPage(pagination.page - 1)"
        >
          {{ t('buttons.previous') }}
        </button>
        <span class="pagination-info">
          {{ t('events.pageOf', { page: pagination.page, total: pagination.total_pages }) }}
        </span>
        <button
          type="button"
          :disabled="pagination.page >= pagination.total_pages || loading"
          @click="goToPage(pagination.page + 1)"
        >
          {{ t('buttons.next') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, defineAsyncComponent } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useAstronomicalEvents } from '@/composables/useAstronomicalEvents';
import AppHeader from '@/components/Header.vue';
import EventListItem from '@/components/events/EventListItem.vue';
import LunarEclipseDetails from '@/components/events/LunarEclipseDetails.vue';
import SolarEclipseDetails from '@/components/events/SolarEclipseDetails.vue';

const DateRangePicker = defineAsyncComponent(() => import('@/components/DateRangePicker.vue'));

const { t, locale } = useI18n();
const router = useRouter();
const { events, pagination, loading, error, hasSearched, fetchEventsSSE, cancelSSE, goToPage, sseEventCount } = useAstronomicalEvents();

const PAGE_SIZE = 10;

const today = new Date();
const oneYearFromToday = new Date(today);
oneYearFromToday.setFullYear(today.getFullYear() + 1);
const startDate = ref(toDateString(today));
const endDate = ref(toDateString(oneYearFromToday));

function toDateString(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function onDateRangeSelected(dates: { start: Date; end: Date }) {
  startDate.value = toDateString(dates.start);
  endDate.value = toDateString(dates.end);
}

function onSelectMode(mode: 'solarSystem' | 'eclipses') {
  if (mode === 'solarSystem') {
    router.push(`/${locale.value}/`);
  }
}

function search() {
  fetchEventsSSE({
    start_date: startDate.value,
    end_date: endDate.value,
    page_size: PAGE_SIZE,
  });
}
</script>

<style scoped>
.events-view {
  display: flex;
  flex-direction: column;
  width: 100vw;
  min-height: 100dvh;
  background: #121212;
  color: #fff;
}

.events-content {
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 1rem 3rem 1rem;
}

.events-description {
  color: #aaa;
  margin-bottom: 1.5rem;
}

.search-btn {
  padding: 0.6rem 1.5rem;
  margin: 1rem 0 1.5rem 0;
  background: #004FA3;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
}

.search-btn:hover:not(:disabled) {
  background: #003d82;
}

.search-btn:disabled {
  background: #555;
  cursor: not-allowed;
}

.loading {
  padding: 10px;
  background: rgba(255, 165, 0, 0.2);
  border-radius: 4px;
  margin-bottom: 10px;
}

.progress-label {
  margin-bottom: 10px;
}

.cancel-btn {
  padding: 0.5rem 1.5rem;
  background: #004FA3;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
}

.cancel-btn:hover {
  background: #003d82;
}

.error {
  padding: 10px;
  background: rgba(255, 0, 0, 0.2);
  border: 1px solid #ff0000;
  border-radius: 4px;
  margin-bottom: 10px;
}

.empty-state {
  color: #aaa;
  padding: 1rem 0;
}

.event-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}

.pagination button {
  padding: 0.5rem 1rem;
  background: #004FA3;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.pagination button:disabled {
  background: #555;
  cursor: not-allowed;
}

.pagination-info {
  color: #ccc;
}
</style>
