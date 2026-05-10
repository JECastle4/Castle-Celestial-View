<template>
  <div class="about-page" role="main">
    <div class="about-card">
      <img src="/logo.png" alt="Castle Celestial View eclipse logo" class="about-logo" />
      <h1>{{ t('about.title') }}</h1>
      <p class="copyright">{{ t('about.copyright') }}</p>
      <p class="version">{{ t('about.version', { version: appVersion }) }}</p>
      <p class="license">{{ t('about.license') }}</p>

      <section class="attributions" aria-labelledby="attributions-heading">
        <h2 id="attributions-heading">{{ t('about.attributionsTitle') }}</h2>
        <ul class="attribution-list">
          <li v-for="lib in libraries" :key="lib.name">
            <a :href="lib.url" target="_blank" rel="noopener noreferrer">{{ lib.name }}</a>
            <span class="lib-license">{{ lib.license }}</span>
          </li>
        </ul>
      </section>

      <section class="project-links" aria-label="Project links">
        <a href="https://github.com/JECastle4/Castle-Celestial-View" target="_blank" rel="noopener noreferrer">{{ t('about.sourceCode') }}</a>
        <a href="https://github.com/JECastle4/Castle-Celestial-View/issues" target="_blank" rel="noopener noreferrer">{{ t('about.reportIssue') }}</a>
      </section>

      <RouterLink :to="`/${locale}/`" class="close-link">
        ← {{ t('about.close') }}
      </RouterLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import { RouterLink } from 'vue-router';

const { t, locale } = useI18n();
declare const __APP_VERSION__: string;
const appVersion = __APP_VERSION__;

const libraries = [
  { name: 'Vue',                   license: 'MIT',          url: 'https://github.com/vuejs/core/blob/main/LICENSE' },
  { name: 'Vue Router',            license: 'MIT',          url: 'https://github.com/vuejs/router/blob/main/LICENSE' },
  { name: 'Vue I18n',              license: 'MIT',          url: 'https://github.com/intlify/vue-i18n/blob/master/LICENSE' },
  { name: 'vue-toast-notification', license: 'MIT',         url: 'https://github.com/ankurk91/vue-toast-notification/blob/master/LICENSE' },
  { name: 'OpenLayers',            license: 'BSD-2-Clause', url: 'https://github.com/openlayers/openlayers/blob/main/LICENSE.md' },
  { name: 'Three.js',              license: 'MIT',          url: 'https://github.com/mrdoob/three.js/blob/dev/LICENSE' },
  { name: 'Astropy',               license: 'BSD-3-Clause', url: 'https://github.com/astropy/astropy/blob/main/LICENSE.rst' },
  { name: 'NumPy',                 license: 'BSD-3-Clause', url: 'https://github.com/numpy/numpy/blob/main/LICENSE.txt' },
  { name: 'Matplotlib',            license: 'BSD-compatible', url: 'https://github.com/matplotlib/matplotlib/blob/main/LICENSE/LICENSE' },
  { name: 'PyOpenGL',              license: 'BSD-3-Clause', url: 'https://github.com/mcfletch/pyopengl/blob/master/license.txt' },
  { name: 'PyOpenGL-accelerate',   license: 'BSD-3-Clause', url: 'https://github.com/mcfletch/pyopengl/blob/master/license.txt' },
  { name: 'FastAPI',               license: 'MIT',          url: 'https://github.com/fastapi/fastapi/blob/master/LICENSE' },
  { name: 'Uvicorn',               license: 'BSD-3-Clause', url: 'https://github.com/encode/uvicorn/blob/master/LICENSE.md' },
  { name: 'Pydantic',              license: 'MIT',          url: 'https://github.com/pydantic/pydantic/blob/main/LICENSE' },
  { name: 'Pillow',                license: 'HPND',         url: 'https://github.com/python-pillow/Pillow/blob/main/LICENSE' },
  { name: 'Pygments',              license: 'BSD-2-Clause', url: 'https://github.com/pygments/pygments/blob/master/LICENSE' },
  { name: 'python-dotenv',         license: 'BSD-3-Clause', url: 'https://github.com/theskumar/python-dotenv/blob/main/LICENSE' },
  { name: 'Requests',              license: 'Apache-2.0',   url: 'https://github.com/psf/requests/blob/main/LICENSE' },
  { name: 'HTTPX',                 license: 'BSD-3-Clause', url: 'https://github.com/encode/httpx/blob/master/LICENSE.md' },
];
</script>

<style scoped>
.about-page {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  background: #05050f;
  padding: 2rem 1rem;
  box-sizing: border-box;
}

.about-card {
  max-width: 560px;
  width: 100%;
  color: #ccc;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  text-align: center;
}

.about-logo {
  width: 96px;
  height: 96px;
  border-radius: 50%;
}

h1 {
  font-size: 1.4rem;
  font-weight: 500;
  color: #eee;
  margin: 0;
}

.copyright {
  margin: 0;
  font-size: 0.9rem;
  color: #aaa;
}

.version {
  margin: 0;
  font-size: 0.8rem;
  color: #666;
}

.license {
  margin: 0;
  font-size: 0.85rem;
  color: #777;
}

.attributions {
  width: 100%;
  margin-top: 1rem;
  text-align: left;
}

h2 {
  font-size: 0.9rem;
  font-weight: 600;
  color: #999;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 0.75rem;
}

.attribution-list {
  list-style: none;
  margin: 0;
  padding: 0 0.75rem 0 0;
  border-top: 1px solid #1e1e2e;
  max-height: 180px;
  overflow-y: auto;
}

.attribution-list li {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.55rem 0;
  border-bottom: 1px solid #1e1e2e;
  font-size: 0.9rem;
}

.attribution-list a {
  color: #7eb8f7;
  text-decoration: none;
}

.attribution-list a:hover {
  text-decoration: underline;
}

.lib-license {
  font-size: 0.75rem;
  color: #666;
}

.close-link {
  margin-top: 1.5rem;
  font-size: 0.85rem;
  color: #7eb8f7;
  text-decoration: none;
}

.project-links {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.project-links a {
  color: #7eb8f7;
  text-decoration: none;
  font-size: 0.85rem;
}

.project-links a:hover {
  text-decoration: underline;
}

.close-link:hover {
  text-decoration: underline;
}
</style>
