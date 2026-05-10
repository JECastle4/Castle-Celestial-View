<template>
  <div class="app-layout">
    <main>
      <AstronomyScene />
    </main>
    <footer class="app-footer">
      <small>{{ t('app.copyright') }}</small>
      <RouterLink :to="`/${locale}/about`" class="footer-about-link">{{ t('app.about') }}</RouterLink>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { watchEffect } from 'vue';
import { useI18n } from 'vue-i18n';
import { RouterLink } from 'vue-router';
import AstronomyScene from '@/components/AstronomyScene.vue';

const { t, locale } = useI18n();
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
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  padding: 4px 12px;
  background: rgba(0, 0, 0, 0.6);
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.7rem;
}

.footer-about-link {
  color: rgba(255, 255, 255, 0.5);
  text-decoration: none;
  font-size: 0.7rem;
}

.footer-about-link:hover {
  color: rgba(255, 255, 255, 0.9);
  text-decoration: underline;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen,
    Ubuntu, Cantarell, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

</style>
