// Playwright smoke test for https://findtorontoevents.ca/audit/
// Collects console errors/warnings, network failures, unhandled rejections,
// pageerror events, and attempts to click visible tab buttons.
import { chromium } from 'playwright';

const URL = 'https://findtorontoevents.ca/audit/';

const consoleMsgs = [];   // {type, text, location}
const networkFails = [];  // {url, status, errorText, method}
const pageErrors = [];    // {message, stack}
const unhandled = [];     // page emits 'pageerror' for uncaught; rejections via window hook
const tabClickErrors = [];

(async () => {
  const t0 = Date.now();
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();

  page.on('console', (msg) => {
    const type = msg.type();
    if (type === 'error' || type === 'warning') {
      const loc = msg.location();
      consoleMsgs.push({
        type,
        text: msg.text(),
        location: loc ? `${loc.url}:${loc.lineNumber}` : '',
      });
    }
  });

  page.on('pageerror', (err) => {
    pageErrors.push({ message: err.message, stack: (err.stack || '').split('\n').slice(0, 3).join(' | ') });
  });

  page.on('requestfailed', (req) => {
    const f = req.failure();
    networkFails.push({
      url: req.url(),
      method: req.method(),
      errorText: f ? f.errorText : 'unknown',
      status: null,
    });
  });

  page.on('response', (resp) => {
    const s = resp.status();
    if (s >= 400) {
      networkFails.push({
        url: resp.url(),
        method: resp.request().method(),
        status: s,
        errorText: `HTTP ${s}`,
      });
    }
  });

  // Capture unhandledrejection from the page
  await page.addInitScript(() => {
    window.addEventListener('unhandledrejection', (e) => {
      // eslint-disable-next-line no-console
      console.error('[unhandledrejection] ' + (e.reason && e.reason.message ? e.reason.message : String(e.reason)));
    });
  });

  let httpStatus = null;
  let networkidleReached = false;
  let loadErr = null;
  try {
    const resp = await page.goto(URL, { waitUntil: 'domcontentloaded', timeout: 30000 });
    httpStatus = resp ? resp.status() : null;
    try {
      await page.waitForLoadState('networkidle', { timeout: 20000 });
      networkidleReached = true;
    } catch (e) {
      networkidleReached = false;
    }
  } catch (e) {
    loadErr = e.message;
  }

  // Click tab buttons if present
  const tabSelectors = [
    '.tab-btn[data-tab="smart"]',
    '.tab-btn[data-tab="warnings"]',
    '.tab-btn[data-tab="high-conviction"]',
    '.tab-btn[data-tab="crypto"]',
    '.tab-btn[data-tab="stocks"]',
    '[data-tab="overview"]',
    '[data-tab="performance"]',
  ];
  for (const sel of tabSelectors) {
    try {
      const el = await page.$(sel);
      if (el) {
        await el.click({ timeout: 3000 });
        await page.waitForTimeout(5000);
      }
    } catch (e) {
      tabClickErrors.push({ selector: sel, error: e.message.split('\n')[0] });
    }
  }

  const loadMs = Date.now() - t0;

  // Dedupe helpers
  const distinct = (arr, keyFn) => {
    const seen = new Map();
    for (const x of arr) {
      const k = keyFn(x);
      seen.set(k, (seen.get(k) || 0) + 1);
    }
    return [...seen.entries()].map(([k, count]) => ({ key: k, count }));
  };

  const summary = {
    url: URL,
    httpStatus,
    loadMs,
    networkidleReached,
    loadError: loadErr,
    consoleErrorCount: consoleMsgs.filter(m => m.type === 'error').length,
    consoleWarnCount: consoleMsgs.filter(m => m.type === 'warning').length,
    distinctConsole: distinct(consoleMsgs, m => `${m.type}: ${m.text.slice(0, 200)}`),
    pageErrors,
    networkFailCount: networkFails.length,
    distinctNetwork: distinct(networkFails, n => `${n.errorText} :: ${n.url.slice(0, 180)}`),
    tabClickErrors,
  };

  console.log(JSON.stringify(summary, null, 2));
  await browser.close();
})().catch((e) => {
  console.error('FATAL:', e);
  process.exit(2);
});
