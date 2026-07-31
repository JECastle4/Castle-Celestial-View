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

// Dev-only: register xx-reverse debug locale synchronously
// xx-reverse is stored outside src/ to prevent bundling into production
if (import.meta.env.DEV) {
  try {
    // Use import.meta.glob to load the dev locale at module init time
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const modules = import.meta.glob<any>('../dev-locales/xx-reverse.json', { eager: true })
    const xxReverseModule = Object.values(modules)[0]
    if (xxReverseModule?.default) {
      const devLocale = 'x' + 'x' + '-reverse'
      i18n.global.setLocaleMessage(devLocale, xxReverseModule.default)
    }
  } catch {
    // Silently fail if dev locale can't load; dev-only feature
  }
}

export function getCurrentLocale(): string {
  return (i18n.global.locale as unknown as Ref<string>).value
}

export function setCurrentLocale(locale: string): void {
  ;(i18n.global.locale as unknown as Ref<string>).value = locale
}
