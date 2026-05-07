import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { i18n } from './i18n'

// xx-reverse is a dev-only debug locale — excluded from production bundles
// import.meta.env.DEV is resolved at build time, so the locale and its route
// are tree-shaken out in production builds.
const PROD_LOCALES = ['en'] as const
export const SUPPORTED_LOCALES: readonly string[] = import.meta.env.DEV
  ? [...PROD_LOCALES, 'xx-reverse']
  : PROD_LOCALES

const localePattern = SUPPORTED_LOCALES.join('|')

const routes: RouteRecordRaw[] = [
  // Redirect bare root to English
  {
    path: '/',
    redirect: '/en/',
  },
  // Main app under locale prefix
  {
    path: `/:locale(${localePattern})/`,
    component: () => import('./App.vue'),
  },
  // Catch-all: redirect unknown paths to English
  {
    path: '/:pathMatch(.*)*',
    redirect: '/en/',
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
    ;(i18n.global.locale as unknown as { value: string }).value = locale
  }
})

export default router
