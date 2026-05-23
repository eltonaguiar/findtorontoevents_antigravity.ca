#!/usr/bin/env node
/**
 * Standalone Full Page Test runner using Playwright (no config file needed).
 *
 * Crawls a website starting from a base URL, visits every internal link up to
 * a configurable depth, and reports:
 *   - HTTP status of each page
 *   - JavaScript errors on each page
 *   - Blank/empty pages
 *   - Broken links
 *
 * Usage:
 *   node .cursor/skills/full-page-test/scripts/run-full-page-test.js
 *   node .cursor/skills/full-page-test/scripts/run-full-page-test.js --url https://findtorontoevents.ca
 *   node .cursor/skills/full-page-test/scripts/run-full-page-test.js --url http://localhost:5173 --depth 3
 *
 * Options:
 *   --url <url>         Base URL to test (default: http://localhost:5173)
 *   --depth <n>         Max crawl depth (default: 2)
 *   --timeout <ms>      Per-page timeout in ms (default: 15000)
 *   --no-same-origin    Follow cross-origin links too
 *   --ignore <patterns> Comma-separated URL substrings to skip
 *   --headless false    Run in headed mode (visible browser)
 *   --browser <name>    Browser to use: chromium, firefox, webkit (default: chromium)
 *   --json              Output results as JSON
 *   --output <file>     Save report to file
 */

const { chromium, firefox, webkit } = require('playwright');

// ---------------------------------------------------------------------------
// Parse CLI args
// ---------------------------------------------------------------------------
const args = process.argv.slice(2);
function getArg(name, defaultValue) {
  const idx = args.indexOf(name);
  if (idx === -1) return defaultValue;
  return args[idx + 1] || defaultValue;
}
function hasFlag(name) {
  return args.includes(name);
}

const BASE_URL = getArg('--url', process.env.FULL_TEST_URL || 'http://localhost:5173');
const MAX_DEPTH = parseInt(getArg('--depth', process.env.FULL_TEST_DEPTH || '2'), 10);
const PAGE_TIMEOUT = parseInt(getArg('--timeout', process.env.FULL_TEST_TIMEOUT || '15000'), 10);
const SAME_ORIGIN = !hasFlag('--no-same-origin');
const IGNORE_PATTERNS = (getArg('--ignore', process.env.FULL_TEST_IGNORE || ''))
  .split(',').map(s => s.trim()).filter(Boolean);
const HEADLESS = getArg('--headless', 'true') !== 'false';
const BROWSER_NAME = getArg('--browser', 'chromium');
const JSON_OUTPUT = hasFlag('--json');
const OUTPUT_FILE = getArg('--output', null);

// ---------------------------------------------------------------------------
// Error pattern config
// ---------------------------------------------------------------------------
const CRITICAL_JS_PATTERNS = [
  'SyntaxError', 'Unexpected token', 'ChunkLoadError', 'Loading chunk',
  'denied by modsecurity', 'ReferenceError', 'TypeError', 'Uncaught ',
  'EvalError', 'URIError', 'InternalError',
];

const IGNORE_ERROR_PATTERNS = [
  /Minified React error #418/, /418.*HTML/, /hydration/i,
  /favicon\.ico/, /google.*analytics/i, /googletagmanager/i,
  /gtag/i, /doubleclick/i, /adsbygoogle/i, /fbevents/i, /hotjar/i,
  /ResizeObserver loop/i, /Non-Error promise rejection/i,
];

const SKIP_URL_PATTERNS = [
  /^mailto:/i, /^tel:/i, /^javascript:/i, /^data:/i, /^blob:/i, /^#/,
  /\.pdf$/i, /\.zip$/i, /\.exe$/i, /\.dmg$/i,
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function normalizeUrl(href, base) {
  try {
    const url = new URL(href, base);
    url.hash = '';
    return url.toString();
  } catch {
    return null;
  }
}

function shouldSkipUrl(url) {
  if (SKIP_URL_PATTERNS.some(p => p.test(url))) return true;
  if (IGNORE_PATTERNS.some(p => url.includes(p))) return true;
  return false;
}

function isSameOrigin(url, base) {
  try { return new URL(url).origin === new URL(base).origin; }
  catch { return false; }
}

function isIgnoredError(text) {
  return IGNORE_ERROR_PATTERNS.some(p => p.test(text));
}

function isCriticalError(text) {
  return CRITICAL_JS_PATTERNS.some(p => text.includes(p));
}

// ---------------------------------------------------------------------------
// Visit a single page
// ---------------------------------------------------------------------------
async function visitPage(page, url) {
  const jsErrors = [];
  const discoveredLinks = [];
  const start = Date.now();

  const onPageError = (err) => {
    const msg = err.message || String(err);
    if (!isIgnoredError(msg) && !isIgnoredError(err.stack || '')) {
      jsErrors.push(`PageError: ${msg}`);
    }
  };

  const onConsole = (consoleMsg) => {
    const type = consoleMsg.type();
    const text = consoleMsg.text();
    if (type === 'error' && isCriticalError(text) && !isIgnoredError(text)) {
      jsErrors.push(`ConsoleError: ${text.slice(0, 300)}`);
    }
  };

  page.on('pageerror', onPageError);
  page.on('console', onConsole);

  let status = null;
  let isBlank = false;
  let redirectedTo = null;

  try {
    let response;
    try {
      response = await page.goto(url, { waitUntil: 'networkidle', timeout: PAGE_TIMEOUT });
    } catch {
      response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: PAGE_TIMEOUT });
    }

    status = response?.status() ?? null;
    const finalUrl = page.url();
    if (finalUrl !== url) {
      try {
        if (new URL(finalUrl).pathname !== new URL(url).pathname) {
          redirectedTo = finalUrl;
        }
      } catch { /* ignore */ }
    }

    await page.waitForTimeout(1500);

    isBlank = await page.evaluate(() => {
      const body = document.body;
      if (!body) return true;
      const text = body.innerText?.trim() || '';
      return text.length === 0 && body.children.length <= 1;
    });

    const links = await page.evaluate(() =>
      Array.from(document.querySelectorAll('a[href]'))
        .map(a => a.href)
        .filter(h => h && h.startsWith('http'))
    );

    for (const link of links) {
      const normalized = normalizeUrl(link, url);
      if (normalized && !shouldSkipUrl(normalized)) {
        if (!SAME_ORIGIN || isSameOrigin(normalized, BASE_URL)) {
          discoveredLinks.push(normalized);
        }
      }
    }
  } catch (err) {
    jsErrors.push(`NavigationError: ${(err.message || String(err)).slice(0, 300)}`);
  }

  page.removeListener('pageerror', onPageError);
  page.removeListener('console', onConsole);

  return {
    result: {
      url,
      status,
      jsErrors,
      isBlank,
      redirectedTo,
      loadTimeMs: Date.now() - start,
      linksFound: discoveredLinks.length,
    },
    discoveredLinks,
  };
}

// ---------------------------------------------------------------------------
// BFS Crawl
// ---------------------------------------------------------------------------
async function crawlSite(page) {
  const visited = new Set();
  const queued = new Set();
  const queue = [{ url: BASE_URL, depth: 0 }];
  const results = [];

  const nb = normalizeUrl(BASE_URL, BASE_URL);
  if (nb) queued.add(nb);

  while (queue.length > 0) {
    const { url, depth } = queue.shift();
    const normalized = normalizeUrl(url, BASE_URL);
    if (!normalized) continue;
    if (visited.has(normalized)) continue;
    visited.add(normalized);

    const prefix = `[${results.length + 1}] [depth=${depth}]`;
    process.stdout.write(`${prefix} ${normalized} ... `);

    const { result, discoveredLinks } = await visitPage(page, normalized);
    results.push(result);

    const statusIcon = result.status >= 200 && result.status < 400 ? '\u2705' : '\u274C';
    const jsIcon = result.jsErrors.length === 0 ? '\u2705' : `\u274C(${result.jsErrors.length})`;
    console.log(`HTTP:${statusIcon}${result.status} JS:${jsIcon} ${result.loadTimeMs}ms links:${result.linksFound}`);

    if (depth < MAX_DEPTH) {
      for (const link of discoveredLinks) {
        const normLink = normalizeUrl(link, BASE_URL);
        if (normLink && !queued.has(normLink)) {
          queued.add(normLink);
          queue.push({ url: normLink, depth: depth + 1 });
        }
      }
    }
  }

  const failed = results.filter(
    r => (r.status !== null && (r.status < 200 || r.status >= 400)) ||
      r.jsErrors.length > 0 || r.isBlank
  );

  return { totalPages: results.length, passed: results.length - failed.length, failed: failed.length, results };
}

// ---------------------------------------------------------------------------
// Report
// ---------------------------------------------------------------------------
function printReport(summary) {
  const line = '='.repeat(70);
  console.log(`\n${line}`);
  console.log('FULL PAGE TEST REPORT');
  console.log(`Base: ${BASE_URL} | Depth: ${MAX_DEPTH} | Same-origin: ${SAME_ORIGIN}`);
  console.log(line);
  console.log(`Total pages: ${summary.totalPages}`);
  console.log(`Passed: ${summary.passed}`);
  console.log(`Failed: ${summary.failed}`);
  console.log(line);

  for (const r of summary.results) {
    const ok = r.status >= 200 && r.status < 400 && r.jsErrors.length === 0 && !r.isBlank;
    const tag = ok ? 'PASS' : 'FAIL';
    const statusStr = r.status !== null ? String(r.status) : 'N/A';
    console.log(`\n  ${tag} ${r.url}`);
    console.log(`       HTTP: ${statusStr} | JS errors: ${r.jsErrors.length} | Blank: ${r.isBlank} | ${r.loadTimeMs}ms | ${r.linksFound} links`);
    if (r.redirectedTo) console.log(`       Redirected to: ${r.redirectedTo}`);
    for (const err of r.jsErrors) {
      console.log(`       >> ${err}`);
    }
  }

  console.log(`\n${line}`);
  if (summary.failed === 0) {
    console.log('\u2705 ALL PAGES PASSED');
  } else {
    console.log(`\u274C ${summary.failed} PAGE(S) FAILED`);
  }
  console.log(line);
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
async function main() {
  console.log(`\nFull Page Test`);
  console.log(`URL: ${BASE_URL}`);
  console.log(`Depth: ${MAX_DEPTH} | Timeout: ${PAGE_TIMEOUT}ms | Same-origin: ${SAME_ORIGIN}`);
  console.log(`Browser: ${BROWSER_NAME} | Headless: ${HEADLESS}\n`);

  const browsers = { chromium, firefox, webkit };
  const browserType = browsers[BROWSER_NAME];
  if (!browserType) {
    console.error(`Unknown browser: ${BROWSER_NAME}. Use: chromium, firefox, webkit`);
    process.exit(1);
  }

  const browser = await browserType.launch({ headless: HEADLESS });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    ignoreHTTPSErrors: true,
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  });
  const page = await context.newPage();

  try {
    const summary = await crawlSite(page);

    if (JSON_OUTPUT) {
      const json = JSON.stringify(summary, null, 2);
      if (OUTPUT_FILE) {
        require('fs').writeFileSync(OUTPUT_FILE, json, 'utf-8');
        console.log(`JSON report saved to ${OUTPUT_FILE}`);
      } else {
        console.log(json);
      }
    } else {
      printReport(summary);
      if (OUTPUT_FILE) {
        // Save text report
        const lines = [];
        lines.push(`Full Page Test Report — ${new Date().toISOString()}`);
        lines.push(`Base: ${BASE_URL} | Depth: ${MAX_DEPTH}`);
        lines.push(`Total: ${summary.totalPages} | Passed: ${summary.passed} | Failed: ${summary.failed}`);
        for (const r of summary.results) {
          const ok = r.status >= 200 && r.status < 400 && r.jsErrors.length === 0 && !r.isBlank;
          lines.push(`${ok ? 'PASS' : 'FAIL'} ${r.url} HTTP:${r.status} JS:${r.jsErrors.length} Blank:${r.isBlank}`);
          for (const err of r.jsErrors) lines.push(`  >> ${err}`);
        }
        require('fs').writeFileSync(OUTPUT_FILE, lines.join('\n'), 'utf-8');
        console.log(`Report saved to ${OUTPUT_FILE}`);
      }
    }

    process.exitCode = summary.failed > 0 ? 1 : 0;
  } finally {
    await browser.close();
  }
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(2);
});
