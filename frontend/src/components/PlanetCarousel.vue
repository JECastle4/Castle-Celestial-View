<template>
  <div class="planet-carousel">
    <button
      class="nav-btn"
      @click="prev"
      :aria-label="t('buttons.previous')"
      :title="t('buttons.previous')"
    >
      <i class="fa fa-chevron-left" aria-hidden="true"></i>
    </button>
    <div class="body-tabs">
      <button
        v-for="body in CELESTIAL_BODIES"
        :key="body.id"
        :class="['body-tab', { active: currentId === body.id, disabled: !body.enabled }]"
        @click="select(body.id)"
        :disabled="!body.enabled"
        :aria-label="t('buttons.selectBody', { body: t(body.labelKey) })"
        :title="t('buttons.selectBody', { body: t(body.labelKey) })"
        :aria-pressed="currentId === body.id"
      >
        <i :class="`fa ${body.icon}`" class="body-icon" aria-hidden="true"></i>
        <span class="body-name">{{ t(body.labelKey) }}</span>
      </button>
    </div>
    <button
      class="nav-btn"
      @click="next"
      :aria-label="t('buttons.next')"
      :title="t('buttons.next')"
    >
      <i class="fa fa-chevron-right" aria-hidden="true"></i>
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { CELESTIAL_BODIES } from '@/config/celestialBodies';

const { t } = useI18n();

const props = defineProps<{
  selectedBody: string;
}>();

const emit = defineEmits<{
  'update:selectedBody': [bodyId: string];
}>();

const currentId = ref(props.selectedBody || CELESTIAL_BODIES[0].id);

watch(() => props.selectedBody, (val) => {
  currentId.value = val;
});

function select(bodyId: string) {
  const body = CELESTIAL_BODIES.find(b => b.id === bodyId);
  // Only allow selecting enabled bodies
  if (body && body.enabled) {
    currentId.value = bodyId;
    emit('update:selectedBody', bodyId);
  }
}

function next() {
  let idx = CELESTIAL_BODIES.findIndex(b => b.id === currentId.value);
  if (idx < 0) idx = 0;
  
  // Find next enabled body
  let nextIdx = (idx + 1) % CELESTIAL_BODIES.length;
  let attempts = 0;
  while (!CELESTIAL_BODIES[nextIdx].enabled && attempts < CELESTIAL_BODIES.length) {
    nextIdx = (nextIdx + 1) % CELESTIAL_BODIES.length;
    attempts++;
  }
  
  if (CELESTIAL_BODIES[nextIdx].enabled) {
    select(CELESTIAL_BODIES[nextIdx].id);
  }
}

function prev() {
  let idx = CELESTIAL_BODIES.findIndex(b => b.id === currentId.value);
  if (idx < 0) idx = 0;
  
  // Find previous enabled body
  let prevIdx = (idx - 1 + CELESTIAL_BODIES.length) % CELESTIAL_BODIES.length;
  let attempts = 0;
  while (!CELESTIAL_BODIES[prevIdx].enabled && attempts < CELESTIAL_BODIES.length) {
    prevIdx = (prevIdx - 1 + CELESTIAL_BODIES.length) % CELESTIAL_BODIES.length;
    attempts++;
  }
  
  if (CELESTIAL_BODIES[prevIdx].enabled) {
    select(CELESTIAL_BODIES[prevIdx].id);
  }
}
</script>

<style scoped>
.planet-carousel {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.nav-btn {
  background: none;
  border: 1px solid rgba(144, 217, 255, 0.3);
  color: #90d9ff;
  width: 28px;
  height: 28px;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  flex-shrink: 0;
  transition: background 0.15s, border-color 0.15s;
}

.nav-btn:hover {
  background: rgba(144, 217, 255, 0.15);
  border-color: rgba(144, 217, 255, 0.7);
}

.body-tabs {
  display: flex;
  align-items: center;
  gap: 0.15rem;
}

.body-tab {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: #aaa;
  padding: 0.25rem 0.6rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85rem;
  white-space: nowrap;
  width: auto;
  margin-bottom: 0;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.body-tab.active {
  background: rgba(0, 79, 163, 0.6);
  border-color: rgba(0, 79, 163, 0.9);
  color: #ffffff;
  font-weight: 600;
}

.body-tab:hover:not(.active) {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.3);
  color: #ddd;
}

.body-icon {
  color: inherit;
  font-size: 0.85rem;
}

.body-name {
  font-weight: inherit;
}

.body-tab.disabled {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.08);
  color: #666;
  cursor: not-allowed;
  opacity: 0.5;
}

.body-tab.disabled:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.08);
  color: #666;
}
</style>
