<template>
  <div class="app-layout">
    <main>
      <AstronomyScene />
    </main>
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import { watchEffect } from 'vue';
import { useI18n } from 'vue-i18n';
import AstronomyScene from '@/components/AstronomyScene.vue';
import AppFooter from '@/components/Footer.vue';

const { t } = useI18n();

watchEffect(() => { document.title = t('app.title'); });
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

html {
  scrollbar-gutter: stable;
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

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

</style>
