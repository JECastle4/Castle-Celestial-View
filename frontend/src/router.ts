import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { setCurrentLocale } from './i18n'

const PROD_LOCALES = ['en-UK', 'en-US'] as const

// Include xx-reverse in dev mode so router accepts /xx-reverse/ URLs
// The string is tree-shaken from production builds
export const SUPPORTED_LOCALES: readonly string[] = import.meta.env.DEV
  ? [...PROD_LOCALES, 'x' + 'x' + '-reverse']
  : PROD_LOCALES

const localePattern = SUPPORTED_LOCALES.join('|')

const routes: RouteRecordRaw[] = [
  // Redirect bare root to English
  {
    path: '/',
    redirect: '/en-UK/',
  },
  // Main app under locale prefix
  {
    path: `/:locale(${localePattern})/`,
    component: () => import('./App.vue'),
  },
  // About page under locale prefix
  {
    path: `/:locale(${localePattern})/about`,
    component: () => import('./views/AboutView.vue'),
  },
  // Astronomical events (eclipses, oppositions, transits) under locale prefix
  {
    path: `/:locale(${localePattern})/events`,
    component: () => import('./views/EventsView.vue'),
  },
  // Catch-all: redirect unknown paths to English
  {
    path: '/:pathMatch(.*)*',
    redirect: '/en-UK',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Set i18n locale from the URL before each navigation
router.beforeEach((to) => {
  const locale = to.params.locale as string | undefined
  if (locale && SUPPORTED_LOCALES.includes(locale)) {
    setCurrentLocale(locale)
  }
})

export default router
