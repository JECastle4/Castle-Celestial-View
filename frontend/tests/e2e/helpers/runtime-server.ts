import { expect, type APIRequestContext, type TestInfo } from '@playwright/test';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

export function isExpectedRuntimeExit(
  code: number | null,
  signal: NodeJS.Signals | null,
  platform: NodeJS.Platform,
  terminationRequested: boolean,
  forcedKill: boolean,
) {
  if (!terminationRequested || forcedKill) return false;
  if (platform === 'win32') return signal === null && (code === 0 || code === 1);
  return (code === 0 && signal === null) || (code === null && signal === 'SIGTERM');
}

export async function withRuntimeServer(
  request: APIRequestContext,
  testInfo: TestInfo,
  environment: Record<string, string>,
  run: (origin: string) => Promise<void>,
) {
  const root = fileURLToPath(new URL('../../../../', import.meta.url));
  const listener = createServer();
  await new Promise<void>((resolve, reject) => {
    listener.once('error', reject);
    listener.listen(0, '127.0.0.1', resolve);
  });
  const address = listener.address();
  if (!address || typeof address === 'string') throw new Error('No runtime test port');
  const port = address.port;
  await new Promise<void>((resolve, reject) => {
    listener.close((error) => error ? reject(error) : resolve());
  });
  const python = process.env.CI ? 'python' : process.platform === 'win32'
    ? join(root, '.venv', 'Scripts', 'python.exe')
    : join(root, '.venv', 'bin', 'python');
  const child = spawn(python, [
    '-m', 'uvicorn', 'runtime_app:app', '--app-dir', 'tests',
    '--host', '127.0.0.1', '--port', String(port), '--no-proxy-headers',
  ], {
    cwd: root,
    env: {
      ...process.env, RATE_LIMIT_ENABLED: 'false',
      TEST_RUNTIME_BLOCK_CONTACT: 'false', TEST_RUNTIME_BLOCK_STREAM: 'false',
      TEST_RUNTIME_DELAY: '0', TEST_RUNTIME_BUDGET: '10', ...environment,
    },
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  let serverLog = '';
  let spawnError: Error | undefined;
  let closed = false;
  let exited = false;
  let exitCode: number | null = null;
  let exitSignal: NodeJS.Signals | null = null;
  child.stdout.on('data', (data) => { serverLog += data.toString(); });
  child.stderr.on('data', (data) => { serverLog += data.toString(); });
  child.once('error', (error) => { spawnError = error; });
  child.once('exit', (code, signal) => {
    exited = true;
    exitCode = code;
    exitSignal = signal;
  });
  child.once('close', (code) => {
    closed = true;
    if (!exited) exitCode = code;
  });
  const origin = `http://127.0.0.1:${port}`;
  let ready = false;
  let terminationRequested = false;
  let forcedKill = false;
  const assertHealthy = async () => {
    if (spawnError) throw spawnError;
    if (exited) {
      throw new Error(
        `Runtime server exited unexpectedly (code ${exitCode}, signal ${exitSignal}):\n${serverLog}`,
      );
    }
    const response = await request.get(`${origin}/health`, { timeout: 1000 });
    expect(response.ok(), `Runtime server health check failed:\n${serverLog}`).toBe(true);
  };
  try {
    await expect.poll(async () => {
      if (spawnError) throw spawnError;
      if (exited || closed) {
        throw new Error(
          `Runtime server exited before readiness (code ${exitCode}, signal ${exitSignal}):\n${serverLog}`,
        );
      }
      try {
        ready = (await request.get(`${origin}/health`, { timeout: 1000 })).ok();
      } catch (error) {
        if (!(error instanceof Error) || !error.message.includes('ECONNREFUSED')) throw error;
      }
      return ready;
    }, { timeout: 15000, message: 'Runtime server must become responsive' }).toBe(true);
    await run(origin);
    await assertHealthy();
  } finally {
    try {
      if (ready && !exited) {
        const released = await request.post(`${origin}/__test/release`, { timeout: 2000 });
        expect(released.ok()).toBe(true);
      }
    } finally {
      try {
        if (!exited) terminationRequested = child.kill('SIGTERM');
        try {
          await expect.poll(() => closed, { timeout: 8000 }).toBe(true);
        } finally {
          if (!closed) {
            forcedKill = child.kill('SIGKILL');
            await expect.poll(() => closed, { timeout: 3000 }).toBe(true);
          }
        }
      } finally {
        try {
          expect(
            isExpectedRuntimeExit(
              exitCode, exitSignal, process.platform, terminationRequested, forcedKill,
            ),
            `Runtime server exited unexpectedly (code ${exitCode}, signal ${exitSignal}):\n${serverLog}`,
          ).toBe(true);
        } finally {
          await testInfo.attach('runtime-server.log', {
            body: serverLog, contentType: 'text/plain',
          });
        }
      }
    }
  }
}
