import type { Plugin } from 'vite'
import { getPagePath, PAGES, PRODUCTION_LOCALES } from '../src/metadata'
import { renderLandingPage } from '../src/landing'

export function landingPages(): Plugin {
  return {
    name: 'regional-landing-pages',
    generateBundle: {
      order: 'post',
      handler(_options, bundle) {
        const index = bundle['index.html']
        if (!index || index.type !== 'asset' || typeof index.source !== 'string') {
          throw new Error('Cannot generate landing pages: built index.html is missing')
        }
        const template = index.source
        for (const locale of PRODUCTION_LOCALES) {
          for (const page of PAGES) {
            const route = getPagePath(page, locale)
            const fileName = `${route.slice(1)}${page === 'home' ? 'index' : ''}.html`
            this.emitFile({
              type: 'asset',
              fileName,
              source: renderLandingPage(template, page, locale),
            })
          }
        }
        // The root stays usable without JavaScript until the server redirects it.
        index.source = renderLandingPage(template, 'home', 'en-GB')
      },
    },
    configurePreviewServer(server) {
      server.middlewares.use((request, _response, next) => {
        if (request.url) {
          const url = new URL(request.url, 'http://localhost')
          for (const locale of PRODUCTION_LOCALES) {
            for (const page of PAGES) {
              const route = getPagePath(page, locale)
              if (url.pathname === route) {
                request.url = `${route}${page === 'home' ? 'index' : ''}.html${url.search}`
              }
            }
          }
        }
        next()
      })
    },
  }
}
