import type { Plugin } from 'vite'
import { existsSync } from 'node:fs'
import { resolve } from 'node:path'
import { getPagePath, PAGES, PRODUCTION_LOCALES } from '../src/metadata'
import { renderLandingPage } from '../src/landing'
import { renderRobots, renderSitemap } from '../src/discovery'

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
        this.emitFile({ type: 'asset', fileName: 'robots.txt', source: renderRobots() })
        this.emitFile({ type: 'asset', fileName: 'sitemap.xml', source: renderSitemap() })
      },
    },
    configurePreviewServer(server) {
      server.middlewares.use((request, _response, next) => {
        if (request.url) {
          const url = new URL(request.url, 'http://localhost')
          if (url.pathname.startsWith('/social/') || ['/robots.txt', '/sitemap.xml'].includes(url.pathname)) {
            const allowed = /^\/social\/[a-z0-9-]+\.png$/.test(url.pathname)
              || ['/robots.txt', '/sitemap.xml'].includes(url.pathname)
            if (!allowed || !existsSync(resolve(server.config.root, server.config.build.outDir, `.${url.pathname}`))) {
              _response.statusCode = 404
              _response.end('Not found')
              return
            }
            return next()
          }
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
