<template>
  <div class="app-layout">
    <main>
      <AstronomyScene />
    </main>
    <footer class="app-footer">
      <div class="footer-lang-menu" ref="langMenuRef">
        <button
          class="footer-lang-btn"
          :aria-label="locale === 'en-UK' ? 'Current language: English (UK)' : 'Current language: English (US)'"
          @click="showLangMenu = !showLangMenu; console.log(showLangMenu); console.log(langOptions);"
        >
          <span :class="['fi', locale === 'en-UK' ? 'fi-gb' : 'fi-us']" style="margin-right: 0.3em;"></span>
        </button>
        <div v-if="showLangMenu" class="footer-lang-dropdown">
          <button
            v-for="opt in langOptions"
            :key="opt.value"
            class="footer-lang-option"
            :disabled="opt.value === locale"
            @click="switchLocale(opt.value)"
          >
            <span :class="['fi', opt.flag]" style="margin-right: 0.3em;"></span>
            {{ opt.label }}
          </button>
        </div>
      </div>
      <small>{{ t('app.copyright') }}</small>
      <RouterLink :to="`/${locale}/about`" class="footer-about-link">{{ t('app.about') }}</RouterLink>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, watchEffect, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import { RouterLink, useRouter, useRoute } from 'vue-router';
import AstronomyScene from '@/components/AstronomyScene.vue';

const { t, locale } = useI18n();
const router = useRouter();
const route = useRoute();
const showLangMenu = ref(false);
const langMenuRef = ref<HTMLElement | null>(null);
const langOptions = [
  { value: 'en-UK', label: 'English (UK)', flag: 'fi-gb' },
  { value: 'en-US', label: 'English (US)', flag: 'fi-us' },
];
if (import.meta.env.DEV) {
  langOptions.push({ value: 'xx-reverse', label: 'Reverse EN (dev only)', flag: 'fi-gb' });
}

function switchLocale(newLocale: string) {
  if (newLocale === locale.value) {
    showLangMenu.value = false;
    return;
  }
  // Build new path with the new locale, preserving the current subpath if possible
  let newPath = route.fullPath.replace(/^\/(en-UK|en-US|xx-reverse)/, '/' + newLocale);
  if (!newPath.startsWith('/' + newLocale)) {
    newPath = `/${newLocale}/`;
  }
  showLangMenu.value = false;
  router.push(newPath);
}

function handleClickOutside(event: MouseEvent) {
  if (showLangMenu.value && langMenuRef.value && !langMenuRef.value.contains(event.target as Node)) {
    showLangMenu.value = false;
  }
}

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside);
});
onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleClickOutside);
});

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
  background: #111;
  color: #bbb;
  font-size: 0.7rem;
  position: relative;
}

.footer-lang-menu {
  position: relative;
  display: flex;
  align-items: center;
}
.footer-lang-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: background 0.2s;
  color: inherit;
  font-size: 1.1em;
  display: flex;
  align-items: center;
}
.footer-lang-btn:focus {
  outline: 2px solid #888;
}
.footer-lang-dropdown {
  position: absolute;
  left: 0;
  bottom: 120%;
  background: #222;
  border: 1px solid #444;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.2);
  z-index: 10;
  min-width: 120px;
  padding: 4px 0;
  display: flex;
  flex-direction: column;
}
.footer-lang-option {
  background: none;
  border: none;
  color: #eee;
  text-align: left;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 1em;
  display: flex;
  align-items: center;
  gap: 0.5em;
  transition: background 0.2s;
}
.footer-lang-option:disabled {
  color: #888;
  cursor: default;
}
.footer-lang-option:not(:disabled):hover {
  background: #333;
}

.footer-about-link {
  color: #bbb;
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
