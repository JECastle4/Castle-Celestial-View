import type { Ref } from 'vue'
import { createI18n } from 'vue-i18n'
import enUK from './locales/en-UK.json'
import enUS from './locales/en-US.json'
// xx-reverse is always imported, but Vite resolves import.meta.env.DEV at build
// time, so the ternary below tree-shakes this locale out of production bundles.
import xxReverse from './locales/xx-reverse.json'

export const i18n = createI18n({
  legacy: false,
  locale: 'en-UK',        // router.beforeEach updates this from the URL
  fallbackLocale: 'en-UK',
  messages: import.meta.env.DEV /* c8 ignore next */
    ? {  'en-UK': enUK, 'en-US': enUS, 'xx-reverse': xxReverse }
    : /* c8 ignore next */ { 'en-UK': enUK },
})

export function getCurrentLocale(): string {
  return (i18n.global.locale as unknown as Ref<string>).value
}

export function setCurrentLocale(locale: string): void {
  ;(i18n.global.locale as unknown as Ref<string>).value = locale
}
