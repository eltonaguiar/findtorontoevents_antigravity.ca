/**
 * Ensure no JavaScript errors on the page (SyntaxError, uncaught exceptions, etc.).
 * Run: npx playwright test tests/no_js_errors.spec.ts
 *
 * Root cause of "Unexpected token '('" (see syntax_error_root_cause.md.resolved):
 * The browser is receiving non-JS (HTML 404, "denied by modsecurity", or PHP source).
 * Fix: use python tools/serve_local.py — never python -m http.server.
 */
import { test, expect } from '@playwright/test';

const BASE = process.env.BASE_URL || 'http://localhost:5173';
const CHUNK_PATH = '/next/_next/static/chunks/a2ac3a6616d60872.js';

test('page loads with zero JavaScript errors', async ({ page, request }) => {
  // Ensure chunk URL returns real JS (not HTML/PHP/modsecurity text)
  const chunkUrl = new URL(CHUNK_PATH, BASE).toString();
  const chunkRes = await request.get(chunkUrl);
  expect(chunkRes.ok(), `Chunk must return 200 (got ${chunkRes.status()}). Use: python tools/serve_local.py`).toBe(true);
  const body = await chunkRes.text();
  expect(
    body.startsWith('(globalThis.TURBOPACK') || body.startsWith('(globalThis.TURBOPACK='),
    `Chunk must be JavaScript (starts with (globalThis.TURBOPACK...). Got: ${body.slice(0, 80)}...`
  ).toBe(true);

  const errors: string[] = [];
  const criticalPatterns = [
    'SyntaxError',
    'Unexpected token',
    'ChunkLoadError',
    'Loading chunk',
    'denied by modsecurity',
    'Uncaught ',
    'ReferenceError',
    'TypeError',
  ];

  page.on('pageerror', (err) => {
    // React #418 = hydration mismatch (server HTML vs client); common in static export, not a syntax/load error
    if (/Minified React error #418|418.*HTML/.test(err.message)) return;
    const stack = err.stack || '';
    const fromChunk = /a2ac3a6616d60872\.js/.test(stack) || /chunks.*\.js/.test(stack);
    errors.push(`PageError: ${err.message}${fromChunk ? ' (from nav chunk)' : ''}\n${stack.slice(0, 500)}`);
  });

  page.on('console', (msg) => {
    const type = msg.type();
    const text = msg.text();
    if (type === 'error' && criticalPatterns.some((p) => text.includes(p))) {
      errors.push(`ConsoleError: ${text}`);
    }
  });

  await page.goto(BASE + '/', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  expect(
    errors,
    errors.length ? `JS errors:\n${errors.join('\n')}` : undefined
  ).toHaveLength(0);
});
