import { describe, it, expect } from 'vitest'
import { normalizeLocaleForIntl } from './locale'

describe('normalizeLocaleForIntl', () => {
  it('maps en-UK to en-GB', () => {
    expect(normalizeLocaleForIntl('en-UK')).toBe('en-GB')
  })

  it('maps xx-reverse (dev-only) to en-GB', () => {
    expect(normalizeLocaleForIntl('xx-reverse')).toBe('en-GB')
  })

  it('passes through valid BCP-47 locales unchanged', () => {
    expect(normalizeLocaleForIntl('en-US')).toBe('en-US')
    expect(normalizeLocaleForIntl('en')).toBe('en')
    expect(normalizeLocaleForIntl('fr')).toBe('fr')
    expect(normalizeLocaleForIntl('de-DE')).toBe('de-DE')
  })

  it('passes through unknown locales unchanged (for future extensibility)', () => {
    expect(normalizeLocaleForIntl('unknown-locale')).toBe('unknown-locale')
  })
})
