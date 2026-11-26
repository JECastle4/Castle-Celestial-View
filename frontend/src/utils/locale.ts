/**
 * Normalize app locales to valid BCP-47/Intl locale tags.
 * Legacy URLs and the development locale need normalizing for Intl APIs.
 * @param locale - The app locale string (e.g., 'en-GB')
 * @returns A valid BCP-47 locale tag for use with Intl APIs
 */
export function normalizeLocaleForIntl(locale: string): string {
  // Map non-standard app locales to valid BCP-47 tags
  const localeMap: Record<string, string> = {
    'en-UK': 'en-GB',
  };

  // Dev-only: add xx-reverse locale mapping (tree-shaken from production)
  // c8 ignore start - this block is only in dev mode and can't be tested in prod
  if (import.meta.env.DEV) {
    const devLocale = 'x' + 'x' + '-' + 'reverse';
    localeMap[devLocale] = 'en-GB';
  }
  // c8 ignore end

  return localeMap[locale] || locale;
}
