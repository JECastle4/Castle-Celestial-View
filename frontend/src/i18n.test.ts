import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import type { Ref } from 'vue';

function setLocale(i18n: { global: { locale: unknown } }, locale: string) {
  (i18n.global.locale as unknown as Ref<string>).value = locale;
}

describe('i18n module', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
    vi.resetModules();
  });

  it('creates an i18n instance with en as default locale', async () => {
    const { i18n } = await import('@/i18n');
    expect((i18n.global.locale as unknown as Ref<string>).value).toBe('en');
  });

  it('includes xx-reverse messages in dev mode', async () => {
    // import.meta.env.DEV is true in vitest
    const { i18n } = await import('@/i18n');
    const messages = i18n.global.getLocaleMessage('xx-reverse') as Record<string, unknown>;
    expect(Object.keys(messages).length).toBeGreaterThan(0);
  });

  it('can switch locale to xx-reverse', async () => {
    const { i18n } = await import('@/i18n');
    setLocale(i18n, 'xx-reverse');
    expect((i18n.global.locale as unknown as Ref<string>).value).toBe('xx-reverse');
    setLocale(i18n, 'en');
  });

  it('translates a key correctly in en', async () => {
    const { i18n } = await import('@/i18n');
    setLocale(i18n, 'en');
    expect(i18n.global.t('astronomy.dayNames.sunday')).toBe('Sunday');
  });

  it('translates a key correctly in xx-reverse', async () => {
    const { i18n } = await import('@/i18n');
    setLocale(i18n, 'xx-reverse');
    expect(i18n.global.t('astronomy.dayNames.sunday')).toBe('yadnuS');
    setLocale(i18n, 'en');
  });
});
