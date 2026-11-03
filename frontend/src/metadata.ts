import enGB from './locales/en-GB.json'
import enUS from './locales/en-US.json'

export const PRODUCTION_LOCALES = ['en-GB', 'en-US'] as const
export type ProductionLocale = typeof PRODUCTION_LOCALES[number]
export type Page = 'home' | 'events' | 'about'

export const SITE_ORIGIN = 'https://castlecelestialview.net'

const messages = { 'en-GB': enGB, 'en-US': enUS }
const paths: Record<Page, string> = { home: '/', events: '/events', about: '/about' }

export function getPageMetadata(page: Page, locale: ProductionLocale) {
  const copy = messages[locale].metadata[page]
  const urlFor = (language: ProductionLocale) => `${SITE_ORIGIN}/${language}${paths[page]}`
  return {
    ...copy,
    language: locale,
    canonical: urlFor(locale),
    alternates: [
      ...PRODUCTION_LOCALES.map(language => ({ language, href: urlFor(language) })),
      { language: 'x-default', href: urlFor('en-GB') },
    ],
  }
}

export function updatePageMetadata(page: Page, locale: string) {
  const productionLocale = PRODUCTION_LOCALES.find(language => language === locale)
  const metadata = getPageMetadata(page, productionLocale ?? 'en-GB')
  document.title = metadata.title
  document.documentElement.lang = metadata.language

  let description = document.head.querySelector<HTMLMetaElement>('meta[name="description"]')
  if (!description) {
    description = document.createElement('meta')
    description.name = 'description'
    document.head.append(description)
  }
  description.content = metadata.description

  document.head.querySelectorAll('link[rel="canonical"], link[rel="alternate"][hreflang]')
    .forEach(element => element.remove())

  // The development pseudo-locale must not advertise production URLs.
  if (!productionLocale) return

  const canonical = document.createElement('link')
  canonical.rel = 'canonical'
  canonical.href = metadata.canonical
  document.head.append(canonical)

  for (const alternate of metadata.alternates) {
    const link = document.createElement('link')
    link.rel = 'alternate'
    link.hreflang = alternate.language
    link.href = alternate.href
    document.head.append(link)
  }
}
