import { spawn } from 'node:child_process';

const backendTarget = process.env.VITE_DEV_API_TARGET ?? 'http://127.0.0.1:8124';
const healthUrl = `${backendTarget.replace(/\/$/, '')}/health`;
const maxAttempts = 60;
const waitMs = 500;

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForBackend() {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await fetch(healthUrl);
      if (response.ok) {
        process.stdout.write(`[DEV] Backend ready at ${healthUrl}\n`);
        return;
      }
    } catch {
      // Backend is still starting up.
    }

    process.stdout.write(`[DEV] Waiting for backend (${attempt}/${maxAttempts})...\n`);
    await sleep(waitMs);
  }

  throw new Error(`Backend did not become ready at ${healthUrl}`);
}

async function main() {
  await waitForBackend();

  const child = spawn('npx', ['vite', '--host', '0.0.0.0', '--port', '5173'], {
    stdio: 'inherit',
    shell: true,
    env: process.env,
  });

  child.on('exit', (code) => {
    process.exit(code ?? 0);
  });
}

main().catch((error) => {
  process.stderr.write(`[DEV] ${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
});
