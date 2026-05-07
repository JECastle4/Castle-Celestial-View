import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
// xx-reverse is imported only in dev. Vite resolves import.meta.env.DEV at build
// time, so the ternary below tree-shakes this locale out of production bundles.
import xxReverse from './locales/xx-reverse.json'

export const i18n = createI18n({
  legacy: false,
  locale: 'en',        // router.beforeEach updates this from the URL
  fallbackLocale: 'en',
  messages: import.meta.env.DEV /* c8 ignore next */
    ? { en, 'xx-reverse': xxReverse }
    : /* c8 ignore next */ { en },
})
