#!/usr/bin/env node
/**
 * Verify remote site (findtorontoevents.ca). Tries Playwright first; on failure
 * or if Playwright unavailable, runs HTTP-only fallback.
 *
 * Environment:
 *   VERIFY_REMOTE_URL  Base URL (default https://findtorontoevents.ca)
 *   VERIFY_REMOTE      1 or true to skip local webServer when running Playwright
 *   FTP_SERVER, FTP_USER, FTP_PASS  Not used for verification; use for deploy scripts
 *
 * Usage:
 *   node tools/verify_remote_site.js
 *   npm run verify:remote
 */

const { spawn } = require('child_process');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const REMOTE_SPEC = 'tests/verify_remote_site.spec.ts';
const FALLBACK_SCRIPT = path.join(__dirname, 'verify_remote_site_fallback.js');

function runPlaywright() {
  return new Promise((resolve) => {
    const env = {
      ...process.env,
      VERIFY_REMOTE: '1',
    };
    if (!env.VERIFY_REMOTE_URL) env.VERIFY_REMOTE_URL = 'https://findtorontoevents.ca';
    let child;
    try {
      child = spawn(
        process.platform === 'win32' ? 'npx.cmd' : 'npx',
        ['playwright', 'test', REMOTE_SPEC, '--reporter=line'],
        {
          cwd: ROOT,
          env,
          stdio: 'inherit',
        }
      );
    } catch (err) {
      console.warn('Playwright spawn failed:', err.message || err.code);
      resolve(false);
      return;
    }
    child.on('error', (err) => {
      console.warn('Playwright error:', err.message || err.code);
      resolve(false);
    });
    child.on('close', (code) => resolve(code === 0));
  });
}

function runFallback() {
  return new Promise((resolve) => {
    const child = spawn('node', [FALLBACK_SCRIPT], {
      cwd: ROOT,
      env: process.env,
      stdio: 'inherit',
    });
    child.on('close', (code) => resolve(code === 0));
  });
}

async function main() {
  const base = process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca';
  console.log('Verifying remote site:', base);
  console.log('');

  const pwOk = await runPlaywright();
  if (pwOk) {
    console.log('');
    console.log('Remote verification PASSED (Playwright).');
    process.exit(0);
  }

  console.log('');
  console.log('Playwright run failed or skipped. Trying HTTP fallback...');
  const fallbackOk = await runFallback();
  if (fallbackOk) {
    console.log('');
    console.log('Remote verification PASSED (fallback).');
    process.exit(0);
  }

  console.error('');
  console.error('Remote verification FAILED (Playwright and fallback).');
  process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
