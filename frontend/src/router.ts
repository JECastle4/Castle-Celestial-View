import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { setCurrentLocale } from './i18n'

// Production locales only - dev-only xx-reverse is registered separately if needed
const PROD_LOCALES = ['en-UK', 'en-US'] as const
export const SUPPORTED_LOCALES: readonly string[] = PROD_LOCALES

// At runtime in dev mode, xx-reverse gets added to i18n after module loads,
// but the router pattern doesn't need to know about it
const localePattern = (PROD_LOCALES as readonly string[]).join('|')

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
