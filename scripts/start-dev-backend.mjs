import { spawn } from 'node:child_process';

function run(command, args, options = {}) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      stdio: 'inherit',
      shell: true,
      env: process.env,
      ...options,
    });

    child.on('exit', (code) => {
      if (code === 0) {
        resolve();
        return;
      }
      reject(new Error(`${command} ${args.join(' ')} exited with code ${code ?? 1}`));
    });
  });
}

async function main() {
  process.stdout.write('[DEV] Applying backend migrations before startup...\n');
  await run('python', ['-m', 'alembic', '-c', 'alembic.ini', 'upgrade', 'head'], {
    cwd: 'backend',
  });

  process.stdout.write('[DEV] Backend schema is up to date. Starting uvicorn...\n');
  const server = spawn(
    'python',
    ['-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8124', '--app-dir', 'backend', '--reload'],
    {
      stdio: 'inherit',
      shell: true,
      env: process.env,
    }
  );

  server.on('exit', (code) => {
    process.exit(code ?? 0);
  });
}

main().catch((error) => {
  process.stderr.write(`[DEV] ${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
});
