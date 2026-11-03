import enGB from './locales/en-GB.json'
import enUS from './locales/en-US.json'

export const PRODUCTION_LOCALES = ['en-GB', 'en-US'] as const
export type ProductionLocale = typeof PRODUCTION_LOCALES[number]
export type Page = 'home' | 'events' | 'about'
export const PAGES: readonly Page[] = ['home', 'events', 'about']

export const SITE_ORIGIN = 'https://castlecelestialview.net'
export const SEARCH_PAGES: readonly Page[] = ['home', 'events']

const messages = { 'en-GB': enGB, 'en-US': enUS }
const paths: Record<Page, string> = { home: '/', events: '/events', about: '/about' }

export function getPagePath(page: Page, locale: ProductionLocale) {
  return `/${locale}${paths[page]}`
}

export function getLandingContent(page: Page, locale: ProductionLocale) {
  const copy = messages[locale]
  return {
    projectTitle: copy.app.title,
    heading: page === 'events' ? copy.events.title : page === 'about' ? copy.about.title : copy.app.title,
    introduction: page === 'events' ? copy.events.description
      : page === 'about' ? copy.metadata.about.description : copy.app.introduction,
    interactiveNotice: copy.app.interactiveNotice,
    startupError: copy.app.startupError,
    navigationLabel: copy.app.modes.ariaLabel,
    navigation: [
      { page: 'home', label: copy.app.modes.solarSystem, href: getPagePath('home', locale) },
      { page: 'events', label: copy.app.modes.eclipses, href: getPagePath('events', locale) },
      { page: 'about', label: copy.app.about, href: getPagePath('about', locale) },
    ],
    languages: PRODUCTION_LOCALES.map(language => ({
      language,
      label: language === 'en-GB' ? copy.lang.enGB : copy.lang.enUS,
      href: getPagePath(page, language),
    })),
  }
}

export function getPageMetadata(page: Page, locale: ProductionLocale) {
  const copy = messages[locale].metadata[page]
  const urlFor = (language: ProductionLocale) => `${SITE_ORIGIN}${getPagePath(page, language)}`
  const image = `${SITE_ORIGIN}/social/${page === 'events' ? 'events' : 'home'}-v1.png`
  return {
    ...copy,
    language: locale,
    canonical: urlFor(locale),
    socialTags: [
      { attribute: 'property', key: 'og:title', content: copy.title },
      { attribute: 'property', key: 'og:description', content: copy.description },
      { attribute: 'property', key: 'og:url', content: urlFor(locale) },
      { attribute: 'property', key: 'og:type', content: 'website' },
      { attribute: 'property', key: 'og:site_name', content: messages[locale].app.title },
      { attribute: 'property', key: 'og:locale', content: locale.replace('-', '_') },
      ...PRODUCTION_LOCALES.filter(language => language !== locale).map(language => ({
        attribute: 'property', key: 'og:locale:alternate', content: language.replace('-', '_'),
      })),
      { attribute: 'property', key: 'og:image', content: image },
      { attribute: 'property', key: 'og:image:type', content: 'image/png' },
      { attribute: 'property', key: 'og:image:width', content: '1200' },
      { attribute: 'property', key: 'og:image:height', content: '630' },
      { attribute: 'property', key: 'og:image:alt', content: copy.imageAlt },
      { attribute: 'name', key: 'twitter:card', content: 'summary_large_image' },
      { attribute: 'name', key: 'twitter:title', content: copy.title },
      { attribute: 'name', key: 'twitter:description', content: copy.description },
      { attribute: 'name', key: 'twitter:image', content: image },
      { attribute: 'name', key: 'twitter:image:alt', content: copy.imageAlt },
    ],
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
  document.head.querySelectorAll('meta[property^="og:"], meta[name^="twitter:"]')
    .forEach(element => element.remove())

  // The development pseudo-locale must not advertise production URLs.
  if (!productionLocale) return

  const canonical = document.createElement('link')
  canonical.rel = 'canonical'
  canonical.href = metadata.canonical
  document.head.append(canonical)

  for (const tag of metadata.socialTags) {
    const element = document.createElement('meta')
    element.setAttribute(tag.attribute, tag.key)
    element.content = tag.content
    document.head.append(element)
  }

  for (const alternate of metadata.alternates) {
    const link = document.createElement('link')
    link.rel = 'alternate'
    link.hreflang = alternate.language
    link.href = alternate.href
    document.head.append(link)
  }
}
