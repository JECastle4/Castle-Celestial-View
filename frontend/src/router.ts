import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { setCurrentLocale } from './i18n'
import { PRODUCTION_LOCALES, updatePageMetadata } from './metadata'

// Include xx-reverse in dev mode so router accepts /xx-reverse/ URLs
// The string is tree-shaken from production builds
export const SUPPORTED_LOCALES: readonly string[] = import.meta.env.DEV
  ? [...PRODUCTION_LOCALES, 'x' + 'x' + '-reverse']
  : PRODUCTION_LOCALES

const localePattern = SUPPORTED_LOCALES.join('|')

const routes: RouteRecordRaw[] = [
  {
    path: '/en-UK/:pathMatch(.*)*',
    redirect: (to) => ({
      path: to.path.replace(/^\/en-UK(?=\/|$)/i, '/en-GB'),
      query: to.query,
      hash: to.hash,
    }),
  },
  // Redirect bare root to English
  {
    path: '/',
    redirect: '/en-GB/',
  },
  // Main app under locale prefix
  {
    path: `/:locale(${localePattern})/`,
    name: 'home',
    component: () => import('./App.vue'),
  },
  // About page under locale prefix
  {
    path: `/:locale(${localePattern})/about`,
    name: 'about',
    component: () => import('./views/AboutView.vue'),
  },
  // Astronomical events (eclipses, oppositions, transits) under locale prefix
  {
    path: `/:locale(${localePattern})/events`,
    name: 'events',
    component: () => import('./views/EventsView.vue'),
  },
  // Catch-all: redirect unknown paths to English
  {
    path: '/:pathMatch(.*)*',
    redirect: '/en-GB/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Set i18n locale from the URL before each navigation
router.beforeEach((to) => {
  const locale = to.params.locale
  if (typeof locale !== 'string') return
  const canonicalLocale = SUPPORTED_LOCALES.find(language => language.toLowerCase() === locale.toLowerCase())
  if (canonicalLocale && canonicalLocale !== locale) {
    return {
      path: `/${canonicalLocale}${to.path.slice(locale.length + 1)}`,
      query: to.query,
      hash: to.hash,
      replace: true,
    }
  }
  if (canonicalLocale) {
    setCurrentLocale(canonicalLocale)
  }
})

router.afterEach((to, _from, failure) => {
  if (!failure && (to.name === 'home' || to.name === 'events' || to.name === 'about')) {
    updatePageMetadata(to.name, String(to.params.locale))
  }
})

export default router
