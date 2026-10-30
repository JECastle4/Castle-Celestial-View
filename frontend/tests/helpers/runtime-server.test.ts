import { describe, expect, it } from 'vitest';
import { isExpectedRuntimeExit } from '../../tests/e2e/helpers/runtime-server';

describe('runtime E2E server teardown', () => {
  it.each([
    [0, null, 'linux', true, false, true],
    [null, 'SIGTERM', 'linux', true, false, true],
    [1, null, 'win32', true, false, true],
    [0, null, 'win32', true, false, true],
    [1, null, 'linux', true, false, false],
    [null, 'SIGKILL', 'linux', true, true, false],
    [0, null, 'linux', false, false, false],
    [1, null, 'win32', false, false, false],
  ] as const)(
    'classifies code=%s signal=%s platform=%s termination=%s forcedKill=%s',
    (code, signal, platform, terminationRequested, forcedKill, expected) => {
      expect(isExpectedRuntimeExit(
        code, signal, platform, terminationRequested, forcedKill,
      )).toBe(expected);
    },
  );
});
