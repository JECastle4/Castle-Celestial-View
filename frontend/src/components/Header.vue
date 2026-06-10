<template>
  <header class="app-header">
    <div class="header-title">
      <h1 class="app-title">{{ t('app.title') }}</h1>
    </div>
    <nav class="mode-switcher" :aria-label="t('app.modes.ariaLabel')">
      <button class="mode-btn active" aria-current="page">
        {{ t('app.modes.solarSystem') }}
      </button>
      <button class="mode-btn" disabled :title="t('app.modes.comingSoon')">
        {{ t('app.modes.eclipses') }}
      </button>
      <button class="mode-btn" disabled :title="t('app.modes.comingSoon')">
        {{ t('app.modes.transits') }}
      </button>
    </nav>
    <div class="header-right">
      <PlanetCarousel
        v-if="hasData"
        :selectedBody="selectedBody"
        @update:selectedBody="emit('update:selectedBody', $event)"
      />
    </div>
  </header>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import PlanetCarousel from './PlanetCarousel.vue';

const { t } = useI18n();

defineProps<{
  hasData: boolean;
  selectedBody: string;
}>();

const emit = defineEmits<{
  'update:selectedBody': [bodyId: string];
}>();
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #181818;
  border-bottom: 1px solid #333;
  padding: 0 1.25rem;
  height: 52px;
  flex-shrink: 0;
  gap: 1rem;
}

.header-title {
  flex: 0 0 auto;
}

.app-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: #ffffff;
  white-space: nowrap;
}

.mode-switcher {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex: 1 1 auto;
  justify-content: center;
}

.mode-btn {
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #aaa;
  padding: 0.3rem 0.75rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  white-space: nowrap;
  width: auto;
  margin-bottom: 0;
}

.mode-btn.active {
  background: rgba(0, 79, 163, 0.6);
  border-color: rgba(0, 79, 163, 0.9);
  color: #ffffff;
  font-weight: 600;
}

.mode-btn:disabled {
  cursor: not-allowed;
  opacity: 0.4;
  background: none;
}

.mode-btn:hover:not(:disabled):not(.active) {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.35);
  color: #ddd;
}

.header-right {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
}
</style>
