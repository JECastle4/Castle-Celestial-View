import type { Ref } from 'vue'
import enUK from './locales/en-UK.json'
import enUS from './locales/en-US.json'
import xxReverse from './locales/xx-reverse.json'
import { createI18n } from 'vue-i18n'

export const i18n = createI18n({
  legacy: false,
  locale: 'en-UK',        // router.beforeEach updates this from the URL
  fallbackLocale: 'en-UK',
  messages: 
    import.meta.env.DEV /* c8 ignore next */
    ? {  'en-UK': enUK, 'en-US': enUS, 'xx-reverse': xxReverse }
    : { 'en-UK': enUK, 'en-US': enUS }
});

export function getCurrentLocale(): string {
  return (i18n.global.locale as unknown as Ref<string>).value
}

export function setCurrentLocale(locale: string): void {
  ;(i18n.global.locale as unknown as Ref<string>).value = locale
}
