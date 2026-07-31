import { describe, it, expect } from 'vitest'
import { normalizeLocaleForIntl } from './locale'

describe('normalizeLocaleForIntl', () => {
  it('maps en-UK to en-GB', () => {
    expect(normalizeLocaleForIntl('en-UK')).toBe('en-GB')
  })

  it('maps xx-reverse (dev-only) to en-GB', () => {
    expect(normalizeLocaleForIntl('xx-reverse')).toBe('en-GB')
  })

  it('maps constructed xx-reverse string to en-GB', () => {
    // Test with constructed string to ensure obfuscation works
    const devLocale = 'x' + 'x' + '-' + 'reverse'
    expect(normalizeLocaleForIntl(devLocale)).toBe('en-GB')
  })

  it('returns en-US unchanged', () => {
    expect(normalizeLocaleForIntl('en-US')).toBe('en-US')
  })

  it('returns generic en unchanged', () => {
    expect(normalizeLocaleForIntl('en')).toBe('en')
  })

  it('returns other language codes unchanged', () => {
    expect(normalizeLocaleForIntl('fr')).toBe('fr')
    expect(normalizeLocaleForIntl('de-DE')).toBe('de-DE')
  })

  it('passes through unknown locales unchanged (for future extensibility)', () => {
    expect(normalizeLocaleForIntl('unknown-locale')).toBe('unknown-locale')
  })
})
