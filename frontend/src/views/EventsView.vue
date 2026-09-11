<template>
  <main class="events-view">
    <AppHeader
      :hasData="false"
      selectedBody=""
      currentMode="eclipses"
      @select-mode="onSelectMode"
    />
    <section class="events-content">
      <h1>{{ t('events.title') }}</h1>
      <p class="events-description">{{ t('events.description') }}</p>

      <div class="search-container">
        <div class="search-left">
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
        </div>

        <div class="search-right">
          <div class="parameters-panel">
            <h2>{{ t('events.searchParameters') }}</h2>
            <div class="parameter-item">
              <span class="parameter-label">{{ t('forms.labels.startDate') }}:</span>
              <span class="parameter-value">{{ formatDisplayDate(startDate) }}</span>
            </div>
            <div class="parameter-item">
              <span class="parameter-label">{{ t('forms.labels.endDate') }}:</span>
              <span class="parameter-value">{{ formatDisplayDate(endDate) }}</span>
            </div>
            <div v-if="hasSearched" class="parameter-item">
              <span class="parameter-label">{{ t('events.resultsFound') }}:</span>
              <span class="parameter-value">{{ pagination?.total_events || 0 }}</span>
            </div>
          </div>
        </div>
      </div>

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
        <div v-if="events.length" class="events-table-header">
          <div class="header-row">
            <p class="utc-notice">{{ t('events.allTimesLocal') }}</p>
            <div class="export-controls">
              <button
                type="button"
                class="export-btn"
                :title="t('buttons.downloadAsCSV')"
                @click="handleExport('csv')"
                :disabled="!events.length || isPreparingExport"
              >
                <i class="fa fa-download" aria-hidden="true"></i>
                CSV
              </button>
              <button
                type="button"
                class="export-btn"
                :title="t('buttons.downloadAsJSON')"
                @click="handleExport('json')"
                :disabled="!events.length || isPreparingExport"
              >
                <i class="fa fa-download" aria-hidden="true"></i>
                JSON
              </button>
            </div>
          </div>
          <div v-if="exportMessage" role="status" class="export-message" :class="{ 'export-success': exportStatus === 'success', 'export-error': exportStatus === 'error', 'export-warning': exportStatus === 'warning' }">
            {{ exportMessage }}
          </div>
        </div>
        <ul v-if="events.length" class="event-list">
          <EventListItem
            v-for="ev in events"
            :key="ev.date"
            :date="ev.date"
            :eventType="ev.event_type"
            :eclipseOccurs="ev.eclipse_occurs"
            :event="ev"
            @load-contact-times="loadContactTimesForEvent"
          >
            <LunarEclipseDetails 
              v-if="ev.is_lunar" 
              :event="ev"
              :loading="loadingEventDates.has(ev.date)"
              :error="contactTimesErrors[ev.date] || null"
            />
            <SolarEclipseDetails 
              v-else 
              :event="ev"
              :loading="loadingEventDates.has(ev.date)"
              :error="contactTimesErrors[ev.date] || null"
            />
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
    </section>
    <AppFooter />
  </main>
</template>

<script setup lang="ts">
import { ref, defineAsyncComponent } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useAstronomicalEvents } from '@/composables/useAstronomicalEvents';
import { exportContactTimesToCSV, exportContactTimesToJSON, generateFilename } from '@/services/export';
import AppHeader from '@/components/Header.vue';
import AppFooter from '@/components/Footer.vue';
import EventListItem from '@/components/events/EventListItem.vue';
import LunarEclipseDetails from '@/components/events/LunarEclipseDetails.vue';
import SolarEclipseDetails from '@/components/events/SolarEclipseDetails.vue';

const DateRangePicker = defineAsyncComponent(() => import('@/components/DateRangePicker.vue'));

const { t, locale } = useI18n();
const router = useRouter();
const { events, pagination, loading, error, hasSearched, fetchEventsSSE, cancelSSE, goToPage, sseEventCount, fetchContactTimesForEvent } = useAstronomicalEvents();

const PAGE_SIZE = 10;
const loadingEventDates = ref<Set<string>>(new Set());
const contactTimesErrors = ref<Record<string, string>>({});

const today = new Date();
const oneYearFromToday = new Date(today);
oneYearFromToday.setFullYear(today.getFullYear() + 1);
const startDate = ref(toDateString(today));
const endDate = ref(toDateString(oneYearFromToday));
const isPreparingExport = ref(false);
const exportMessage = ref<string | null>(null);
const exportStatus = ref<'success' | 'error' | 'warning' | null>(null);

function toDateString(date: Date): string {
  return date.toISOString().slice(0, 10);
}

function formatDisplayDate(dateString: string): string {
  try {
    const date = new Date(dateString + 'T00:00:00Z');
    return date.toLocaleDateString(locale.value, { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return dateString;
  }
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
    include_contact_times: false,  // Load contact times on-demand, not upfront
  }).catch(() => {
    // Composable updates error state; rejection handled here to prevent unhandled rejection.
  });
}

async function loadContactTimesForEvent(event: any) {
  // Only fetch if it's an eclipse and we don't already have contact times
  if (!event.eclipse_occurs || event.contact_times) {
    return;
  }

  const dateStr = event.date;
  
  try {
    loadingEventDates.value = new Set(loadingEventDates.value).add(dateStr);
    delete contactTimesErrors.value[dateStr];
    
    await fetchContactTimesForEvent(dateStr, event.is_lunar);
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : t('errors.unknown');
    contactTimesErrors.value[dateStr] = errorMsg;
  } finally {
    const newSet = new Set(loadingEventDates.value);
    newSet.delete(dateStr);
    loadingEventDates.value = newSet;
  }
}

function handleExport(format: 'csv' | 'json') {
  if (!events.value || events.value.length === 0) {
    exportMessage.value = t('events.noDataToExport');
    exportStatus.value = 'error';
    return;
  }

  // Check if any eclipse events are missing contact times
  const eclipsesNeedingContactTimes = events.value.filter(
    (ev: any) => ev.eclipse_occurs && !ev.contact_times
  );

  if (eclipsesNeedingContactTimes.length > 0) {
    exportMessage.value = t('events.loadingContactTimesForExport');
    exportStatus.value = null;  // Loading state, no styling
    isPreparingExport.value = true;

    // Fetch all missing contact times before export, tracking success/failure for each
    Promise.all(
      eclipsesNeedingContactTimes.map((ev: any) =>
        fetchContactTimesForEvent(ev.date, ev.is_lunar)
          .then(() => ({ success: true, date: ev.date }))
          .catch((err) => ({ success: false, date: ev.date, error: err }))
      )
    )
      .then((results) => {
        // Check if any fetches failed
        const failures = results.filter((r: any) => !r.success);
        
        exportMessage.value = null;
        exportStatus.value = null;
        const exportSuccess = performExport(format);
        
        // Display appropriate message after export (but don't overwrite if export failed)
        if (!exportSuccess) {
          // performExport already set the error message and status, don't overwrite it
          return;
        }
        
        if (failures.length > 0) {
          const failureCount = failures.length;
          const totalCount = eclipsesNeedingContactTimes.length;
          exportMessage.value = t('events.partialExportWarning', { 
            failed: failureCount, 
            total: totalCount 
          });
          exportStatus.value = 'warning';
          setTimeout(() => {
            exportMessage.value = null;
            exportStatus.value = null;
          }, 5000);
        } else {
          exportMessage.value = t('events.exportSuccess');
          exportStatus.value = 'success';
          setTimeout(() => {
            exportMessage.value = null;
            exportStatus.value = null;
          }, 3000);
        }
      })
      .catch((err) => {
        const errorMsg = err instanceof Error ? err.message : t('errors.unknown');
        exportMessage.value = t('events.exportError', { error: errorMsg });
        exportStatus.value = 'error';
      })
      .finally(() => {
        isPreparingExport.value = false;
      });
  } else {
    // All contact times available, proceed with export
    exportMessage.value = null;
    exportStatus.value = null;
    const exportSuccess = performExport(format);
    
    // Only show success message if export actually succeeded
    if (!exportSuccess) {
      // performExport already set the error message and status, no need to show success
      return;
    }
    
    exportMessage.value = t('events.exportSuccess');
    exportStatus.value = 'success';
    setTimeout(() => {
      exportMessage.value = null;
      exportStatus.value = null;
    }, 3000);
  }
}

function performExport(format: 'csv' | 'json') {
  if (!events.value || events.value.length === 0) {
    return false;
  }

  const filename = generateFilename(format);

  try {
    if (format === 'csv') {
      exportContactTimesToCSV(events.value, filename);
    } else {
      exportContactTimesToJSON(events.value, filename);
    }
    return true;
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : t('errors.unknown');
    console.error('Export error:', errorMsg);
    exportMessage.value = t('events.exportError', { error: errorMsg });
    exportStatus.value = 'error';
    return false;
  }
}

</script>

<style scoped>
.events-view {
  display: flex;
  flex-direction: column;
  width: 100%;
  min-height: 100vh;
  background: #121212;
  color: #fff;
}

.events-content {
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 1rem 1.5rem 1rem;
  flex: 1;
  overflow-y: auto;
}

.events-description {
  color: #aaa;
  margin-bottom: 1.5rem;
}

.search-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  margin-bottom: 2rem;
  align-items: start;
}

.search-left {
  display: flex;
  flex-direction: column;
}

.date-range-panel {
  margin-bottom: 1rem;
}

.search-right {
  display: flex;
  flex-direction: column;
}

.parameters-panel {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  padding: 1rem;
  color: #ddd;
}

.parameters-panel h2 {
  margin: 0 0 1rem 0;
  font-size: 0.95em;
  color: #fff;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.parameter-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  font-size: 0.9em;
}

.parameter-item:last-child {
  margin-bottom: 0;
}

.parameter-label {
  color: #aaa;
  margin-right: 1rem;
}

.parameter-value {
  color: #fff;
  font-weight: 500;
  text-align: right;
}

@media (max-width: 960px) {
  .search-container {
    grid-template-columns: 1fr;
    gap: 1rem;
  }
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

.events-table-header {
  margin-bottom: 1rem;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.utc-notice {
  color: #d4d4d4;
  font-size: 0.9em;
  margin: 0;
  padding: 0;
  flex: 1;
}

.export-controls {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
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

.export-btn {
  padding: 0.5rem 1rem;
  background: #004FA3;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  display: flex;
  align-items: center;
  gap: 0.5em;
  white-space: nowrap;
}

.export-btn:hover:not(:disabled) {
  background: #003d82;
}

.export-btn:disabled {
  background: #555;
  cursor: not-allowed;
  opacity: 0.6;
}

.export-message {
  margin-top: 0.75rem;
  padding: 0.75rem;
  border-radius: 4px;
  font-size: 0.9em;
  background: rgba(255, 193, 7, 0.2);
  border: 1px solid rgba(255, 193, 7, 0.5);
  color: #ffc107;
}

.export-message.export-success {
  background: rgba(76, 175, 80, 0.2);
  border: 1px solid rgba(76, 175, 80, 0.5);
  color: #4caf50;
}

.export-message.export-warning {
  background: rgba(255, 193, 7, 0.2);
  border: 1px solid rgba(255, 193, 7, 0.5);
  color: #ffc107;
}

.export-message.export-error {
  background: rgba(255, 0, 0, 0.2);
  border: 1px solid rgba(255, 0, 0, 0.5);
  color: #ff0000;
}
</style>
