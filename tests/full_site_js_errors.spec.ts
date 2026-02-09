/**
 * Full-Site JS Error Check — Explicitly tests EVERY known production page.
 *
 * Unlike the BFS crawl in full_page_test.spec.ts, this test has an explicit
 * manifest of all deployed pages so nothing is missed.
 *
 * Checks per page:
 *   1. HTTP 2xx status
 *   2. Zero critical JavaScript errors (SyntaxError, ReferenceError, TypeError, etc.)
 *   3. Page not blank
 *
 * Usage:
 *   VERIFY_REMOTE=1 npx playwright test tests/full_site_js_errors.spec.ts --project="Desktop Chrome"
 */

import { test, expect, Page } from '@playwright/test';

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const isRemote =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

const BASE =
  process.env.FULL_TEST_URL ||
  (isRemote
    ? process.env.VERIFY_REMOTE_URL || 'https://findtorontoevents.ca'
    : 'http://localhost:5173');

const PAGE_TIMEOUT = isRemote ? 20000 : 12000;

// Critical JS error patterns
const CRITICAL_PATTERNS = [
  'SyntaxError',
  'Unexpected token',
  'ChunkLoadError',
  'Loading chunk',
  'ReferenceError',
  'TypeError',
  'Uncaught ',
  'EvalError',
  'URIError',
  'InternalError',
  'denied by modsecurity',
];

// Errors to ignore (third-party noise, known benign)
const IGNORE_PATTERNS = [
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
  /ResizeObserver loop/i,
  /Non-Error promise rejection/i,
  /net::ERR_/,
  /Failed to load resource.*fonts/i,
  /Failed to load resource.*analytics/i,
  /the server responded with a status of 404.*favicon/i,
  /A-Frame/i, // A-Frame VR framework warnings
  /THREE\..*deprecated/i, // Three.js deprecation warnings
  /WebGL/i, // WebGL context warnings in headless
  /vignette/i, // Google AdSense vignette ad noise
  /interstitial/i, // Ad interstitial API noise
];

// ---------------------------------------------------------------------------
// COMPLETE manifest of every known production page
// ---------------------------------------------------------------------------

interface PageEntry {
  path: string;
  name: string;
  module: string;
  /** if true, page may load WebGL/A-Frame which can fail in headless — softer check */
  isWebGL?: boolean;
}

const ALL_PAGES: PageEntry[] = [
  // ── Root ──
  { path: '/', name: 'Homepage (Toronto Events)', module: 'root' },
  { path: '/404.html', name: '404 Page', module: 'root' },

  // ── FavCreators ──
  { path: '/fc/', name: 'FavCreators App', module: 'favcreators' },

  // ── FindStocks ──
  { path: '/findstocks/', name: 'Stock Finder Main', module: 'findstocks' },
  { path: '/findstocks/portfolio/', name: 'Portfolio Tracker', module: 'findstocks' },
  { path: '/findstocks/portfolio/stats.html', name: 'Portfolio Stats', module: 'findstocks' },
  { path: '/findstocks/portfolio/report.html', name: 'Portfolio Report', module: 'findstocks' },
  { path: '/findstocks/portfolio2/', name: 'Portfolio V2', module: 'findstocks' },
  { path: '/findstocks/portfolio2/hub.html', name: 'Portfolio Hub', module: 'findstocks' },
  { path: '/findstocks/portfolio2/stats/', name: 'Portfolio V2 Stats', module: 'findstocks' },
  { path: '/findstocks/portfolio2/picks.html', name: 'Top Picks Dashboard', module: 'findstocks' },
  { path: '/findstocks/portfolio2/leaderboard.html', name: 'Algorithm Leaderboard', module: 'findstocks' },
  { path: '/findstocks/research/', name: 'Stock Research', module: 'findstocks' },

  // ── FindStocks Global ──
  { path: '/findstocks2_global/', name: 'Global Stock Finder', module: 'findstocks_global' },
  { path: '/findstocks_global/miracle.html', name: 'DayTraders Miracle Scanner', module: 'findstocks_global' },

  // ── Mutual Funds V2 Portfolio ──
  { path: '/findmutualfunds2/portfolio2/', name: 'MF Portfolio V2', module: 'mutualfunds' },

  // ── Forex Portfolio ──
  { path: '/findforex2/portfolio/', name: 'Forex Portfolio', module: 'forex' },

  // ── Crypto Portfolio ──
  { path: '/findcryptopairs/portfolio/', name: 'Crypto Portfolio', module: 'crypto' },

  // ── MOVIESHOWS ──
  { path: '/MOVIESHOWS/', name: 'Movie Showtimes', module: 'movieshows' },

  // ── WINDOWSFIXER ──
  { path: '/WINDOWSFIXER/', name: 'Windows Fixer', module: 'windowsfixer' },

  // ── FIGHTGAME ──
  { path: '/FIGHTGAME/', name: 'Fight Game', module: 'fightgame' },

  // ── VR Hub ──
  { path: '/vr/', name: 'VR Hub', module: 'vr', isWebGL: true },
  { path: '/vr/mobile-index.html', name: 'VR Mobile', module: 'vr', isWebGL: true },
  { path: '/vr/movies.html', name: 'VR Movies', module: 'vr', isWebGL: true },
  { path: '/vr/movies-tiktok.html', name: 'VR Movies TikTok', module: 'vr', isWebGL: true },
  { path: '/vr/creators.html', name: 'VR Creators', module: 'vr', isWebGL: true },
  { path: '/vr/stocks-zone.html', name: 'VR Stocks Zone', module: 'vr', isWebGL: true },
  { path: '/vr/weather-zone.html', name: 'VR Weather Zone', module: 'vr', isWebGL: true },
  { path: '/vr/tictactoe.html', name: 'VR Tic-Tac-Toe', module: 'vr', isWebGL: true },

  // ── VR Game Arena ──
  { path: '/vr/game-arena/', name: 'Game Arena Hub', module: 'vr-games', isWebGL: true },
  { path: '/vr/game-arena/fighting-arena.html', name: 'Fighting Arena', module: 'vr-games', isWebGL: true },
  { path: '/vr/game-arena/soccer-shootout.html', name: 'Soccer Shootout', module: 'vr-games', isWebGL: true },
  { path: '/vr/game-arena/tic-tac-toe.html', name: 'Tic-Tac-Toe', module: 'vr-games', isWebGL: true },
  { path: '/vr/game-arena/fps-arena.html', name: 'FPS Arena', module: 'vr-games', isWebGL: true },

  // ── FPS V5 ──
  { path: '/vr/game-arena/fps-v5/', name: 'FPS V5', module: 'vr-games', isWebGL: true },

  // ── Investments / Mutual Funds ──
  { path: '/findmutualfunds/', name: 'Mutual Fund Finder', module: 'findmutualfunds' },

  // ── Crypto ──
  { path: '/findcryptopairs/', name: 'Crypto Pair Finder', module: 'findcryptopairs' },

  // ── Forex ──
  { path: '/findforex2/', name: 'Forex Finder', module: 'findforex2' },

];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function isCritical(text: string): boolean {
  return CRITICAL_PATTERNS.some((p) => text.includes(p));
}

function isIgnored(text: string): boolean {
  return IGNORE_PATTERNS.some((p) => p.test(text));
}

interface VisitResult {
  url: string;
  name: string;
  module: string;
  status: number | null;
  jsErrors: string[];
  isBlank: boolean;
  loadTimeMs: number;
  isWebGL: boolean;
}

async function checkPage(page: Page, entry: PageEntry): Promise<VisitResult> {
  const url = BASE + entry.path;
  const jsErrors: string[] = [];
  const start = Date.now();

  const onPageError = (err: Error) => {
    const msg = err.message || String(err);
    const stack = err.stack || '';
    if (isIgnored(msg) || isIgnored(stack)) return;
    jsErrors.push(`PageError: ${msg.slice(0, 300)}`);
  };

  const onConsole = (consoleMsg: { type: () => string; text: () => string }) => {
    if (consoleMsg.type() === 'error') {
      const text = consoleMsg.text();
      if (isCritical(text) && !isIgnored(text)) {
        jsErrors.push(`ConsoleError: ${text.slice(0, 300)}`);
      }
    }
  };

  page.on('pageerror', onPageError);
  page.on('console', onConsole);

  let status: number | null = null;
  let isBlank = false;

  try {
    let response;
    try {
      response = await page.goto(url, { waitUntil: 'networkidle', timeout: PAGE_TIMEOUT });
    } catch {
      response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: PAGE_TIMEOUT });
    }

    status = response?.status() ?? null;
    await page.waitForTimeout(1500);

    isBlank = await page.evaluate(() => {
      const body = document.body;
      if (!body) return true;
      const text = body.innerText?.trim() || '';
      const children = body.children.length;
      return text.length === 0 && children <= 1;
    });
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err);
    jsErrors.push(`NavigationError: ${errMsg.slice(0, 300)}`);
  }

  page.removeListener('pageerror', onPageError);
  page.removeListener('console', onConsole);

  return {
    url,
    name: entry.name,
    module: entry.module,
    status,
    jsErrors,
    isBlank,
    loadTimeMs: Date.now() - start,
    isWebGL: !!entry.isWebGL,
  };
}

// ---------------------------------------------------------------------------
// Tests — each module gets its own describe block
// ---------------------------------------------------------------------------

// Group pages by module
const moduleGroups = new Map<string, PageEntry[]>();
for (const p of ALL_PAGES) {
  if (!moduleGroups.has(p.module)) moduleGroups.set(p.module, []);
  moduleGroups.get(p.module)!.push(p);
}

for (const [moduleName, pages] of moduleGroups) {
  test.describe(`[${moduleName}] JS error check`, () => {
    test.setTimeout(isRemote ? 60000 : 30000);

    for (const entry of pages) {
      test(`${entry.name} (${entry.path}) — zero JS errors`, async ({ page }) => {
        const result = await checkPage(page, entry);

        // Log for visibility
        const statusStr = result.status ?? 'null';
        const errCount = result.jsErrors.length;
        console.log(
          `${errCount === 0 ? 'PASS' : 'FAIL'} | ${result.name} | HTTP ${statusStr} | ${result.loadTimeMs}ms | ${errCount} error(s)`
        );

        // HTTP status check — allow 200-399 (redirects ok)
        if (result.status !== null) {
          expect(
            result.status,
            `${result.name} returned HTTP ${result.status}`
          ).toBeGreaterThanOrEqual(200);
          expect(
            result.status,
            `${result.name} returned HTTP ${result.status}`
          ).toBeLessThan(400);
        }

        // JS error check — WebGL pages get a softer check (only SyntaxError/ReferenceError)
        if (result.isWebGL) {
          const hardErrors = result.jsErrors.filter(
            (e) =>
              e.includes('SyntaxError') ||
              e.includes('ReferenceError') ||
              e.includes('Unexpected token')
          );
          expect(
            hardErrors,
            hardErrors.length
              ? `Hard JS errors on ${result.name}:\n${hardErrors.join('\n')}`
              : undefined
          ).toHaveLength(0);
        } else {
          expect(
            result.jsErrors,
            result.jsErrors.length
              ? `JS errors on ${result.name}:\n${result.jsErrors.join('\n')}`
              : undefined
          ).toHaveLength(0);
        }

        // Blank check — skip for 404 page
        if (!entry.path.includes('404')) {
          expect(result.isBlank, `${result.name} should not be blank`).toBe(false);
        }
      });
    }
  });
}

// ---------------------------------------------------------------------------
// Summary test — runs ALL pages and prints a consolidated report
// ---------------------------------------------------------------------------

test.describe('Full site summary', () => {
  test.setTimeout(isRemote ? 600000 : 300000);

  test('consolidated report of all pages', async ({ page }) => {
    const results: VisitResult[] = [];

    for (const entry of ALL_PAGES) {
      const result = await checkPage(page, entry);
      results.push(result);
    }

    // Print report
    const lines: string[] = [];
    lines.push(`\n${'='.repeat(80)}`);
    lines.push(`FULL SITE JS ERROR REPORT — ${BASE}`);
    lines.push(`Pages tested: ${results.length}`);
    lines.push(`${'='.repeat(80)}`);

    let totalErrors = 0;
    let totalFailed = 0;

    for (const r of results) {
      const ok = r.status !== null && r.status >= 200 && r.status < 400;
      const hasErrors = r.jsErrors.length > 0;
      const passed = ok && !hasErrors && !r.isBlank;

      if (!passed) totalFailed++;
      totalErrors += r.jsErrors.length;

      const badge = passed ? 'PASS' : 'FAIL';
      lines.push(
        `${badge} | [${r.module}] ${r.name}`
      );
      lines.push(
        `       ${r.url} | HTTP ${r.status} | ${r.loadTimeMs}ms | ${r.jsErrors.length} error(s)${r.isBlank ? ' | BLANK' : ''}`
      );
      for (const err of r.jsErrors) {
        lines.push(`       >> ${err}`);
      }
    }

    lines.push(`\n${'='.repeat(80)}`);
    lines.push(`TOTAL: ${results.length} pages | ${results.length - totalFailed} passed | ${totalFailed} failed | ${totalErrors} JS error(s)`);
    lines.push(`${'='.repeat(80)}\n`);

    console.log(lines.join('\n'));

    // Final assertion
    expect(
      totalFailed,
      `${totalFailed} page(s) failed. See report above.`
    ).toBe(0);
  });
});
