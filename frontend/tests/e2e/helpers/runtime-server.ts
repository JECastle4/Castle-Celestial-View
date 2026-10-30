import { expect, type APIRequestContext, type TestInfo } from '@playwright/test';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

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
  let exitCode: number | null = null;
  child.stdout.on('data', (data) => { serverLog += data.toString(); });
  child.stderr.on('data', (data) => { serverLog += data.toString(); });
  child.once('error', (error) => { spawnError = error; });
  child.once('close', (code) => {
    closed = true;
    exitCode = code;
  });
  const origin = `http://127.0.0.1:${port}`;
  let ready = false;
  try {
    await expect.poll(async () => {
      if (spawnError) throw spawnError;
      if (closed) throw new Error(`Runtime server exited (${exitCode}):\n${serverLog}`);
      try {
        ready = (await request.get(`${origin}/health`, { timeout: 1000 })).ok();
      } catch (error) {
        if (!(error instanceof Error) || !error.message.includes('ECONNREFUSED')) throw error;
      }
      return ready;
    }, { timeout: 15000, message: 'Runtime server must become responsive' }).toBe(true);
    await run(origin);
  } finally {
    try {
      if (ready && !closed) {
        const released = await request.post(`${origin}/__test/release`, { timeout: 2000 });
        expect(released.ok()).toBe(true);
      }
    } finally {
      try {
        if (!closed) child.kill('SIGTERM');
        try {
          await expect.poll(() => closed, { timeout: 8000 }).toBe(true);
        } finally {
          if (!closed) {
            child.kill('SIGKILL');
            await expect.poll(() => closed, { timeout: 3000 }).toBe(true);
          }
        }
      } finally {
        await testInfo.attach('runtime-server.log', {
          body: serverLog, contentType: 'text/plain',
        });
      }
    }
  }
}
