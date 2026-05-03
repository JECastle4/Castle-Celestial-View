import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import xxReverse from './locales/xx-reverse.json'

// Check if we should use reversed locale for testing
// Enable with: URL param ?i18n-debug=reverse OR localStorage.setItem('i18n-debug', 'reverse')
const debugMode = new URLSearchParams(window.location.search).get('i18n-debug') === 'reverse' ||
                  localStorage.getItem('i18n-debug') === 'reverse'

const initialLocale = debugMode ? 'xx-reverse' : 'en'

export const i18n = createI18n({
  legacy: false,
  locale: initialLocale,
  fallbackLocale: 'en',
  messages: { en, 'xx-reverse': xxReverse },
})

// Helper to toggle reversed locale for testing
export function toggleDebugLocale() {
  const isDebugMode = localStorage.getItem('i18n-debug') === 'reverse'
  if (isDebugMode) {
    localStorage.removeItem('i18n-debug')
    console.log('Debug locale disabled. Reload page to see English.')
  } else {
    localStorage.setItem('i18n-debug', 'reverse')
    console.log('Debug locale enabled. Reload page to see reversed strings.')
  }
}
