/**
 * Full Page Test — Crawl all navigation paths and verify:
 *   1. Every page returns HTTP 2xx
 *   2. Zero JavaScript errors on every page
 *   3. Every page renders content (not blank)
 *   4. All internal links are reachable
 *
 * Usage:
 *   npx playwright test tests/full_page_test.spec.ts --project="Desktop Chrome"
 *
 * Remote:
 *   VERIFY_REMOTE=1 npx playwright test tests/full_page_test.spec.ts --project="Desktop Chrome"
 *
 * Options (env vars):
 *   FULL_TEST_URL      — base URL (default: http://localhost:5173 or remote)
 *   FULL_TEST_DEPTH    — max crawl depth (default: 2)
 *   FULL_TEST_TIMEOUT  — per-page timeout ms (default: 15000)
 *   FULL_TEST_IGNORE   — comma-separated URL substrings to skip
 */

import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const isRemote =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

const BASE_URL =
  process.env.FULL_TEST_URL ||
  (isRemote
    ? process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca'
    : 'http://localhost:5173');

const MAX_DEPTH = parseInt(process.env.FULL_TEST_DEPTH || '2', 10);
const PAGE_TIMEOUT = parseInt(process.env.FULL_TEST_TIMEOUT || '15000', 10);
const SAME_ORIGIN = process.env.FULL_TEST_SAME_ORIGIN !== 'false';
const IGNORE_PATTERNS = (process.env.FULL_TEST_IGNORE || '')
  .split(',')
  .map((s) => s.trim())
  .filter(Boolean);

// JS error patterns that constitute a failure
const CRITICAL_JS_PATTERNS = [
  'SyntaxError',
  'Unexpected token',
  'ChunkLoadError',
  'Loading chunk',
  'denied by modsecurity',
  'ReferenceError',
  'TypeError',
  'Uncaught ',
  'EvalError',
  'URIError',
  'InternalError',
];

// Patterns to ignore (not failures)
const IGNORE_ERROR_PATTERNS = [
  /Minified React error #418/,
  /418.*HTML/,
  /hydration/i,
  /favicon\.ico/,
  /google.*analytics/i,
  /googletagmanager/i,
  /gtag/i,
  /doubleclick/i,
  /adsbygoogle/i,
  /fbevents/i,
  /hotjar/i,
  // Common third-party noise
  /ResizeObserver loop/i,
  /Non-Error promise rejection/i,
];

// URL patterns to skip entirely
const SKIP_URL_PATTERNS = [
  /^mailto:/i,
  /^tel:/i,
  /^javascript:/i,
  /^data:/i,
  /^blob:/i,
  /^#/,
  /\.pdf$/i,
  /\.zip$/i,
  /\.exe$/i,
  /\.dmg$/i,
  /\.apk$/i,
  /\.ipa$/i,
];

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface PageResult {
  url: string;
  status: number | null;
  jsErrors: string[];
  isBlank: boolean;
  redirectedTo: string | null;
  loadTimeMs: number;
  linksFound: number;
}

interface CrawlSummary {
  totalPages: number;
  passed: number;
  failed: number;
  results: PageResult[];
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalizeUrl(href: string, baseUrl: string): string | null {
  try {
    const url = new URL(href, baseUrl);
    // Remove hash
    url.hash = '';
    // Remove trailing slash inconsistency
    let normalized = url.toString();
    // Don't double-add trailing slash for root, but normalize paths
    if (url.pathname !== '/' && normalized.endsWith('/')) {
      // Keep trailing slash — many servers require it
    }
    return normalized;
  } catch {
    return null;
  }
}

function shouldSkipUrl(url: string): boolean {
  if (SKIP_URL_PATTERNS.some((p) => p.test(url))) return true;
  if (IGNORE_PATTERNS.some((p) => url.includes(p))) return true;
  return false;
}

function isSameOrigin(url: string, base: string): boolean {
  try {
    return new URL(url).origin === new URL(base).origin;
  } catch {
    return false;
  }
}

function isIgnoredError(text: string): boolean {
  return IGNORE_ERROR_PATTERNS.some((p) => p.test(text));
}

function isCriticalError(text: string): boolean {
  return CRITICAL_JS_PATTERNS.some((p) => text.includes(p));
}

// ---------------------------------------------------------------------------
// Core: visit a single page, collect errors, discover links
// ---------------------------------------------------------------------------

async function visitPage(
  page: Page,
  url: string
): Promise<{ result: PageResult; discoveredLinks: string[] }> {
  const jsErrors: string[] = [];
  const discoveredLinks: string[] = [];
  const start = Date.now();

  // Listen for JS errors
  const onPageError = (err: Error) => {
    const msg = err.message || String(err);
    const stack = err.stack || '';
    if (isIgnoredError(msg) || isIgnoredError(stack)) return;
    jsErrors.push(`PageError: ${msg}`);
  };

  const onConsole = (consoleMsg: { type: () => string; text: () => string }) => {
    const type = consoleMsg.type();
    const text = consoleMsg.text();
    if (type === 'error' && isCriticalError(text) && !isIgnoredError(text)) {
      jsErrors.push(`ConsoleError: ${text.slice(0, 300)}`);
    }
  };

  page.on('pageerror', onPageError);
  page.on('console', onConsole);

  let status: number | null = null;
  let isBlank = false;
  let redirectedTo: string | null = null;

  try {
    // Try networkidle first, fall back to domcontentloaded
    let response;
    try {
      response = await page.goto(url, {
        waitUntil: 'networkidle',
        timeout: PAGE_TIMEOUT,
      });
    } catch {
      // Timeout on networkidle — retry with domcontentloaded
      response = await page.goto(url, {
        waitUntil: 'domcontentloaded',
        timeout: PAGE_TIMEOUT,
      });
    }

    status = response?.status() ?? null;
    const finalUrl = page.url();
    if (finalUrl !== url && new URL(finalUrl).pathname !== new URL(url).pathname) {
      redirectedTo = finalUrl;
    }

    // Wait a moment for any deferred JS to execute
    await page.waitForTimeout(1500);

    // Check if page is blank
    isBlank = await page.evaluate(() => {
      const body = document.body;
      if (!body) return true;
      const text = body.innerText?.trim() || '';
      const children = body.children.length;
      return text.length === 0 && children <= 1; // allow a single empty wrapper
    });

    // Discover internal links
    const links = await page.evaluate(() => {
      return Array.from(document.querySelectorAll('a[href]'))
        .map((a) => (a as HTMLAnchorElement).href)
        .filter((h) => h && h.startsWith('http'));
    });

    for (const link of links) {
      const normalized = normalizeUrl(link, url);
      if (normalized && !shouldSkipUrl(normalized)) {
        if (!SAME_ORIGIN || isSameOrigin(normalized, BASE_URL)) {
          discoveredLinks.push(normalized);
        }
      }
    }
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err);
    jsErrors.push(`NavigationError: ${errMsg.slice(0, 300)}`);
  }

  // Cleanup listeners
  page.removeListener('pageerror', onPageError);
  page.removeListener('console', onConsole);

  const loadTimeMs = Date.now() - start;

  return {
    result: {
      url,
      status,
      jsErrors,
      isBlank,
      redirectedTo,
      loadTimeMs,
      linksFound: discoveredLinks.length,
    },
    discoveredLinks,
  };
}

// ---------------------------------------------------------------------------
// Core: BFS crawl
// ---------------------------------------------------------------------------

async function crawlSite(page: Page): Promise<CrawlSummary> {
  const visited = new Set<string>();
  const queue: { url: string; depth: number }[] = [{ url: BASE_URL, depth: 0 }];
  const results: PageResult[] = [];

  // Normalize the base URL itself
  const normalizedBase = normalizeUrl(BASE_URL, BASE_URL);
  if (normalizedBase) visited.add(normalizedBase);

  while (queue.length > 0) {
    const { url, depth } = queue.shift()!;

    // Skip if already visited (after normalization)
    const normalized = normalizeUrl(url, BASE_URL);
    if (!normalized) continue;
    if (visited.has(normalized) && results.length > 0) continue;
    visited.add(normalized);

    console.log(`[depth=${depth}] Testing: ${normalized}`);

    const { result, discoveredLinks } = await visitPage(page, normalized);
    results.push(result);

    // Queue discovered links at next depth
    if (depth < MAX_DEPTH) {
      for (const link of discoveredLinks) {
        const normLink = normalizeUrl(link, BASE_URL);
        if (normLink && !visited.has(normLink)) {
          visited.add(normLink); // mark as queued
          queue.push({ url: normLink, depth: depth + 1 });
        }
      }
    }
  }

  const failed = results.filter(
    (r) =>
      (r.status !== null && (r.status < 200 || r.status >= 400)) ||
      r.jsErrors.length > 0 ||
      r.isBlank
  );

  return {
    totalPages: results.length,
    passed: results.length - failed.length,
    failed: failed.length,
    results,
  };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe(`Full Page Test: ${BASE_URL}`, () => {
  // Increase overall test timeout for crawling multiple pages
  test.setTimeout(isRemote ? 180000 : 120000);

  test('crawl all navigation paths — zero JS errors, all pages load', async ({
    page,
  }) => {
    const summary = await crawlSite(page);

    // Build report
    const report: string[] = [];
    report.push(`\n${'='.repeat(70)}`);
    report.push(`FULL PAGE TEST REPORT`);
    report.push(`Base: ${BASE_URL} | Depth: ${MAX_DEPTH} | Same-origin: ${SAME_ORIGIN}`);
    report.push(`${'='.repeat(70)}`);
    report.push(`Total pages tested: ${summary.totalPages}`);
    report.push(`Passed: ${summary.passed}`);
    report.push(`Failed: ${summary.failed}`);
    report.push(`${'='.repeat(70)}\n`);

    for (const r of summary.results) {
      const statusBadge =
        r.status !== null && r.status >= 200 && r.status < 400 ? 'OK' : `FAIL(${r.status})`;
      const jsBadge = r.jsErrors.length === 0 ? 'OK' : `${r.jsErrors.length} ERROR(S)`;
      const blankBadge = r.isBlank ? 'BLANK' : 'OK';
      const hasIssue =
        statusBadge !== 'OK' || jsBadge !== 'OK' || blankBadge !== 'OK';

      report.push(
        `${hasIssue ? 'FAIL' : 'PASS'} | ${r.url}`
      );
      report.push(
        `       HTTP: ${statusBadge} | JS: ${jsBadge} | Content: ${blankBadge} | ${r.loadTimeMs}ms | ${r.linksFound} links`
      );
      if (r.redirectedTo) {
        report.push(`       Redirected to: ${r.redirectedTo}`);
      }
      if (r.jsErrors.length > 0) {
        for (const err of r.jsErrors) {
          report.push(`       >> ${err}`);
        }
      }
      report.push('');
    }

    console.log(report.join('\n'));

    // Assertions
    const failedPages = summary.results.filter(
      (r) =>
        (r.status !== null && (r.status < 200 || r.status >= 400)) ||
        r.jsErrors.length > 0 ||
        r.isBlank
    );

    if (failedPages.length > 0) {
      const failDetails = failedPages
        .map((r) => {
          const issues: string[] = [];
          if (r.status !== null && (r.status < 200 || r.status >= 400))
            issues.push(`HTTP ${r.status}`);
          if (r.jsErrors.length > 0)
            issues.push(`JS errors: ${r.jsErrors.join('; ')}`);
          if (r.isBlank) issues.push('Blank page');
          return `  ${r.url}\n    ${issues.join('\n    ')}`;
        })
        .join('\n');

      expect(
        failedPages.length,
        `${failedPages.length} page(s) failed:\n${failDetails}`
      ).toBe(0);
    }
  });

  test('homepage loads and has no JS errors', async ({ page }) => {
    const { result } = await visitPage(page, BASE_URL);

    expect(
      result.status,
      `Homepage should return 200 (got ${result.status})`
    ).toBe(200);

    expect(
      result.jsErrors,
      result.jsErrors.length
        ? `JS errors on homepage:\n${result.jsErrors.join('\n')}`
        : undefined
    ).toHaveLength(0);

    expect(result.isBlank, 'Homepage should not be blank').toBe(false);
  });

  test('all internal links return 2xx (link checker)', async ({ request }) => {
    // Fetch homepage, extract all links, HEAD-check each one
    const res = await request.get(BASE_URL + '/');
    expect(res.ok()).toBeTruthy();
    const html = await res.text();

    // Parse href values from HTML
    const hrefRegex = /href=["']([^"']+)["']/g;
    const links = new Set<string>();
    let match;
    while ((match = hrefRegex.exec(html)) !== null) {
      const href = match[1];
      const normalized = normalizeUrl(href, BASE_URL);
      if (
        normalized &&
        !shouldSkipUrl(href) &&
        isSameOrigin(normalized, BASE_URL)
      ) {
        links.add(normalized);
      }
    }

    const broken: { url: string; status: number }[] = [];
    for (const link of links) {
      try {
        // Skip anchors within the same page
        if (new URL(link).pathname === '/' && new URL(link).hash) continue;
        // Skip known file extensions that might not serve HTML
        if (/\.(js|css|woff2?|ttf|png|jpg|svg|ico|json)$/i.test(link)) continue;

        const r = await request.get(link, { timeout: 10000 });
        if (!r.ok()) {
          broken.push({ url: link, status: r.status() });
        }
      } catch {
        broken.push({ url: link, status: 0 });
      }
    }

    if (broken.length > 0) {
      const details = broken
        .map((b) => `  ${b.url} → ${b.status || 'timeout/error'}`)
        .join('\n');
      expect(
        broken.length,
        `${broken.length} broken link(s):\n${details}`
      ).toBe(0);
    }
  });

  test('Quick Nav menu links are all valid', async ({ page }) => {
    await page.goto(BASE_URL + '/', { waitUntil: 'networkidle', timeout: PAGE_TIMEOUT });

    // Try to open Quick Nav
    const quickNavButton = page.getByTitle('Quick Navigation');
    const hasQuickNav = await quickNavButton.isVisible().catch(() => false);
    if (!hasQuickNav) {
      console.log('No Quick Navigation button found — skipping Quick Nav link test');
      return;
    }

    await quickNavButton.click();
    await page.waitForTimeout(800);

    // Get all links inside the Quick Nav dropdown
    const navLinks = await page.locator('[class*="nav"] a[href], [id*="nav"] a[href], [role="navigation"] a[href]').all();
    if (navLinks.length === 0) {
      // Broader search — any dropdown/menu that appeared
      const allVisibleLinks = await page.locator('a[href]:visible').all();
      console.log(`Quick Nav: found ${allVisibleLinks.length} visible links on page`);
      return;
    }

    const errors: string[] = [];
    for (const link of navLinks) {
      const href = await link.getAttribute('href');
      if (!href || href === '#' || href.startsWith('javascript:')) continue;

      const fullUrl = normalizeUrl(href, BASE_URL);
      if (!fullUrl || !isSameOrigin(fullUrl, BASE_URL)) continue;

      try {
        const res = await page.request.get(fullUrl, { timeout: 10000 });
        if (!res.ok()) {
          const label = await link.textContent();
          errors.push(`"${label?.trim()}" → ${href} → HTTP ${res.status()}`);
        }
      } catch (err) {
        const label = await link.textContent();
        errors.push(`"${label?.trim()}" → ${href} → error`);
      }
    }

    expect(
      errors,
      errors.length ? `Broken Quick Nav links:\n${errors.join('\n')}` : undefined
    ).toHaveLength(0);
  });
});
