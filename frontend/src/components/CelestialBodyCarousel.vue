<template>
  <div class="celestial-carousel">
    <div class="carousel-nav">
      <button 
        @click="previousBody" 
        class="nav-btn prev-btn"
        :aria-label="t('buttons.previous')"
        :title="t('buttons.previous')"
      >
        <i class="fa fa-chevron-left" aria-hidden="true"></i>
      </button>
      
      <div class="body-tabs">
        <button
          v-for="body in CELESTIAL_BODIES"
          :key="body.id"
          @click="selectBody(body.id)"
          :class="{ active: selectedBodyId === body.id }"
          class="body-tab"
          :aria-label="body.name"
          :title="body.name"
        >
          <i :class="`fa ${body.icon}`" aria-hidden="true"></i>
          <span class="body-name">{{ body.name }}</span>
        </button>
      </div>
      
      <button 
        @click="nextBody"
        class="nav-btn next-btn"
        :aria-label="t('buttons.next')"
        :title="t('buttons.next')"
      >
        <i class="fa fa-chevron-right" aria-hidden="true"></i>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { CELESTIAL_BODIES } from '@/config/celestialBodies';

const { t } = useI18n();

const emit = defineEmits<{
  'update:selectedBody': [bodyId: string];
}>();

const props = defineProps<{
  selectedBody: string;
}>();

const selectedBodyId = ref(props.selectedBody || 'sun');

watch(() => props.selectedBody, (newVal) => {
  selectedBodyId.value = newVal;
});

const selectBody = (bodyId: string) => {
  selectedBodyId.value = bodyId;
  emit('update:selectedBody', bodyId);
};

const nextBody = () => {
  const currentIndex = CELESTIAL_BODIES.findIndex(b => b.id === selectedBodyId.value);
  const nextIndex = (currentIndex + 1) % CELESTIAL_BODIES.length;
  selectBody(CELESTIAL_BODIES[nextIndex].id);
};

const previousBody = () => {
  const currentIndex = CELESTIAL_BODIES.findIndex(b => b.id === selectedBodyId.value);
  const prevIndex = (currentIndex - 1 + CELESTIAL_BODIES.length) % CELESTIAL_BODIES.length;
  selectBody(CELESTIAL_BODIES[prevIndex].id);
};
</script>

<style scoped>
.celestial-carousel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  background: linear-gradient(135deg, rgba(10, 10, 40, 0.8), rgba(20, 20, 60, 0.8));
  border-radius: 8px;
  border: 1px solid rgba(100, 150, 200, 0.3);
}

.carousel-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: space-between;
}

.body-tabs {
  display: flex;
  gap: 0.5rem;
  flex: 1;
  justify-content: center;
  overflow-x: auto;
  flex-wrap: wrap;
}

.body-tab {
  padding: 0.5rem 1rem;
  background: rgba(50, 100, 150, 0.3);
  border: 1px solid rgba(100, 150, 200, 0.3);
  border-radius: 4px;
  color: #a0d8ff;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
  white-space: nowrap;
}

.body-tab:hover {
  background: rgba(50, 100, 150, 0.5);
  border-color: rgba(150, 200, 255, 0.5);
  transform: translateY(-2px);
}

.body-tab.active {
  background: rgba(100, 150, 255, 0.6);
  border-color: rgba(200, 255, 255, 0.8);
  color: #ffffff;
  box-shadow: 0 0 15px rgba(100, 150, 255, 0.4);
}

.nav-btn {
  padding: 0.5rem 0.75rem;
  background: rgba(50, 100, 150, 0.3);
  border: 1px solid rgba(100, 150, 200, 0.3);
  border-radius: 4px;
  color: #a0d8ff;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-btn:hover {
  background: rgba(100, 150, 255, 0.4);
  border-color: rgba(150, 200, 255, 0.5);
  transform: scale(1.1);
}

.nav-btn:active {
  transform: scale(0.95);
}

.body-name {
  display: inline;
}

@media (max-width: 768px) {
  .body-tab {
    padding: 0.4rem 0.8rem;
    font-size: 0.85rem;
  }

  .body-name {
    display: none;
  }
}
</style>
