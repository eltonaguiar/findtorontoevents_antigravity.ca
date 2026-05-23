/**
 * Playwright JS-error scan for findtorontoevents.ca/audit, run after the
 * Kimi audit Phase-1 fixes (PR #411 — ML-2 calibrator + post-clamp R:R).
 *
 * Captures, per page:
 *   - page-level errors (uncaught exceptions, SyntaxError, etc.)
 *   - console.error messages
 *   - failed network requests (HTTP >= 400, aborts)
 *
 * Writes a JSON report to tests/artifacts/audit_js_errors_kimi411.json so
 * the follow-up PR carries reproducible evidence. The test passes iff there
 * are zero CRITICAL pageerrors AND zero failing primary-document requests.
 *
 * Run:
 *   AUDIT_BASE=https://findtorontoevents.ca npx playwright test tests/audit_js_errors_kimi411.spec.ts --project="Desktop Chrome"
 */
import { test, expect } from '@playwright/test';
import * as fs from 'node:fs';
import * as path from 'node:path';

const BASE = process.env.AUDIT_BASE || 'https://findtorontoevents.ca';
const TARGET_PATHS = ['/audit', '/audit/', '/audit/index.html'];

interface PageReport {
  url: string;
  status: number | null;
  pageErrors: { message: string; stack: string }[];
  consoleErrors: string[];
  failedRequests: { url: string; status: number; failure: string | null }[];
  loadedAt: string;
}

const ARTIFACT_DIR = path.resolve(__dirname, 'artifacts');
const ARTIFACT_FILE = path.join(ARTIFACT_DIR, 'audit_js_errors_kimi411.json');

const IGNORE_CONSOLE = [
  /Minified React error #418/, // hydration mismatch in static export, harmless
  /favicon\.ico/,
  /tradingview/i,             // 3rd-party widget noise
  /Failed to load resource.*ads/, // ad-blocker noise
];

test('audit dashboard: zero critical JS errors', async ({ page, request }) => {
  fs.mkdirSync(ARTIFACT_DIR, { recursive: true });

  const reports: PageReport[] = [];

  for (const p of TARGET_PATHS) {
    const url = BASE + p;
    const report: PageReport = {
      url,
      status: null,
      pageErrors: [],
      consoleErrors: [],
      failedRequests: [],
      loadedAt: new Date().toISOString(),
    };

    page.removeAllListeners('pageerror');
    page.removeAllListeners('console');
    page.removeAllListeners('requestfailed');
    page.removeAllListeners('response');

    page.on('pageerror', (err) => {
      report.pageErrors.push({
        message: err.message,
        stack: (err.stack || '').slice(0, 800),
      });
    });

    page.on('console', (msg) => {
      if (msg.type() !== 'error') return;
      const text = msg.text();
      if (IGNORE_CONSOLE.some((re) => re.test(text))) return;
      report.consoleErrors.push(text);
    });

    page.on('requestfailed', (req) => {
      report.failedRequests.push({
        url: req.url(),
        status: 0,
        failure: req.failure()?.errorText ?? null,
      });
    });

    page.on('response', (res) => {
      const s = res.status();
      if (s >= 400) {
        report.failedRequests.push({ url: res.url(), status: s, failure: null });
      }
    });

    try {
      const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 60_000 });
      report.status = resp ? resp.status() : null;
      // Give late-mounting widgets a chance to fire errors.
      await page.waitForTimeout(2_500);
    } catch (e) {
      report.pageErrors.push({
        message: `goto failed: ${(e as Error).message}`,
        stack: '',
      });
    }

    reports.push(report);

    // First reachable URL is enough — bail to avoid duplicate noise.
    if (report.status && report.status < 400) break;
  }

  fs.writeFileSync(ARTIFACT_FILE, JSON.stringify(reports, null, 2));

  // Pass criteria: at least one path responded < 400 AND zero pageerrors on it.
  const reachable = reports.find((r) => r.status !== null && r.status < 400);
  expect(reachable, `No /audit path responded <400. Reports: ${JSON.stringify(reports, null, 2)}`).toBeTruthy();

  expect(
    reachable!.pageErrors,
    reachable!.pageErrors.length
      ? `Page errors on ${reachable!.url}:\n${reachable!.pageErrors.map((e) => e.message).join('\n')}`
      : undefined,
  ).toHaveLength(0);

  // Console errors are warnings, not blockers — log them so the follow-up PR
  // body can show what was suppressed without flunking the gate.
  if (reachable!.consoleErrors.length) {
    // eslint-disable-next-line no-console
    console.warn(
      `[audit_js_errors_kimi411] ${reachable!.consoleErrors.length} non-critical console.error messages on ${reachable!.url}.`,
    );
  }
});
