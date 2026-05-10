<template>
  <div class="app-layout">
    <main>
      <AstronomyScene />
    </main>
    <footer class="app-footer">
      <small>{{ t('app.copyright') }}</small>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import AstronomyScene from '@/components/AstronomyScene.vue';

const { t } = useI18n();
onMounted(() => { document.title = t('app.title'); });
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.app-layout {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.app-layout main {
  flex: 1;
  overflow: hidden;
}

.app-footer {
  flex-shrink: 0;
  text-align: center;
  padding: 4px 0;
  background: rgba(0, 0, 0, 0.6);
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.7rem;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

</style>
