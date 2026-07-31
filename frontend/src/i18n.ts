import type { Ref } from 'vue'
import enUK from './locales/en-UK.json'
import enUS from './locales/en-US.json'
import { createI18n } from 'vue-i18n'

// Initialize i18n with production locales
export const i18n = createI18n({
  legacy: false,
  locale: 'en-UK',        // router.beforeEach updates this from the URL
  fallbackLocale: 'en-UK',
  messages: { 'en-UK': enUK, 'en-US': enUS },
})

// Dev-only: load and register xx-reverse debug locale after initialization
// xx-reverse is stored outside src/ to prevent bundling into production
if (import.meta.env.DEV) {
  ;(async () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const xxReverseModule = await import('../dev-locales/xx-reverse.json')
    i18n.global.setLocaleMessage('xx-reverse', xxReverseModule.default)
  })()
}

export function getCurrentLocale(): string {
  return (i18n.global.locale as unknown as Ref<string>).value
}

export function setCurrentLocale(locale: string): void {
  ;(i18n.global.locale as unknown as Ref<string>).value = locale
}
