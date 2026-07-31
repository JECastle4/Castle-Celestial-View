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

// Dev-only: register xx-reverse debug locale
// Loaded synchronously using import.meta.glob with eager: true
// Excluded from production builds via tree-shaking of import.meta.env.DEV block
// c8 ignore start - dev-only code path excluded from production
if (import.meta.env.DEV) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const modules = import.meta.glob<any>('../dev-locales/xx-reverse.json', { eager: true })
  const xxReverseModule = Object.values(modules)[0]
  if (xxReverseModule?.default) {
    const devLocale = 'x' + 'x' + '-' + 'reverse'
    i18n.global.setLocaleMessage(devLocale, xxReverseModule.default)
  }
}
// c8 ignore end

export function getCurrentLocale(): string {
  return (i18n.global.locale as unknown as Ref<string>).value
}

export function setCurrentLocale(locale: string): void {
  ;(i18n.global.locale as unknown as Ref<string>).value = locale
}
