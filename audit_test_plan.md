# Playwright Test Plan – findtorontoevents.ca/audit (Crypto Prediction Data)

## 1. Objective
Validate the end‑to‑end functionality of the **Audit Dashboard** for crypto prediction picks, covering:
- Page load & asset fetching
- Data integrity of crypto rows
- UI interactions (filters, sorting, pagination)
- Edge‑case handling (empty data, API errors)
- Performance & security basics

## 2. Test Matrix
| # | Scenario | Steps | Expected Outcome |
|---|----------|-------|------------------|
| 1 | **Page Load** | `await page.goto('https://findtorontoevents.ca/audit')` | HTTP 200, no console errors, `<title>` contains “Audit Dashboard” |
| 2 | **Payload Fetch** | Intercept `dashboard_payload.json` request → `await page.waitForResponse(url => url.includes('dashboard_payload.json'))` | Response 200, `Content‑Type: application/json`, JSON schema contains `picks.active` array |
| 3 | **Crypto Rows Presence** | After payload load, query `tr[data-asset="CRYPTO"]` | At least one row, each row shows `symbol`, `WR%`, `sampleSize` |
| 4 | **Verified‑Alpha Filter** | Click `#btn-verified-alpha` | Table updates to show only rows with `verifiedAlpha===true`; URL hash changes to `#verified` |
| 5 | **Sorting** | Click column header `WR%` twice (asc → desc) | Row order matches sorted `wr_pct` values from payload
| 6 | **Pagination** | Set `#page-size` to 20, navigate to page 2 | Row count = 20, rows correspond to slice `[20:40]` of payload
| 7 | **Empty State** | Mock payload with `picks.active=[]` via route.fulfill → reload | UI shows “No audit events found.” message, no table rows
| 8 | **Network Error** | Force 500 on `dashboard_payload.json` → reload | UI displays error banner with class `.perf-alert.sev-CRITICAL`
| 9 | **Performance** | Measure `performance.timing.loadEventEnd‑navigationStart` | < 2 s on a typical network (assert via `page.evaluate`)
|10 | **Security** | Verify CSP header exists & no inline scripts | `Content‑Security‑Policy` present, `script-src` does not contain `'unsafe-inline'`

## 3. Playwright Implementation Sketch
```ts
import { test, expect } from '@playwright/test';

test.describe('Audit Dashboard – Crypto', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('https://findtorontoevents.ca/audit');
    await page.waitForResponse(r => r.url().includes('dashboard_payload.json') && r.status() === 200);
  });

  test('loads page and payload', async ({ page }) => {
    await expect(page).toHaveTitle(/Audit Dashboard/);
    const payload = await page.evaluate(() => window['__AUDIT_PAYLOAD__']); // expose via script tag
    expect(payload).toHaveProperty('picks.active');
  });

  test('crypto rows rendered', async ({ page }) => {
    const cryptoRows = await page.$$('tr[data-asset="CRYPTO"]');
    expect(cryptoRows.length).toBeGreaterThan(0);
    for (const row of cryptoRows) {
      const wr = await row.$eval('.wr', el => el.textContent?.trim());
      expect(parseFloat(wr!)).toBeGreaterThanOrEqual(0);
    }
  });

  test('verified‑alpha filter works', async ({ page }) => {
    await page.click('#btn-verified-alpha');
    await page.waitForTimeout(500); // debounce
    const rows = await page.$$('tr[data-verified="true"]');
    expect(rows.length).toBeGreaterThan(0);
  });

  test('sorting by WR', async ({ page }) => {
    await page.click('th[data-key="wr_pct"]'); // asc
    const first = await page.textContent('tr:first-child .wr');
    const second = await page.textContent('tr:nth-child(2) .wr');
    expect(parseFloat(first!)).toBeLessThanOrEqual(parseFloat(second!));
    await page.click('th[data-key="wr_pct"]'); // desc
    const firstDesc = await page.textContent('tr:first-child .wr');
    const secondDesc = await page.textContent('tr:nth-child(2) .wr');
    expect(parseFloat(firstDesc!)).toBeGreaterThanOrEqual(parseFloat(secondDesc!));
  });

  // …additional tests for pagination, error handling, performance, CSP…
});
```
*All tests live under `tests/audit/` and are bundled into the CI pipeline (`npm test`).*

## 4. Data‑Flow Verification
1. **Static JSON** – `https://raw.githubusercontent.com/.../audit_trail/data/dashboard_payload.json`.
2. **Client‑side parsing** – `fetch(PAYLOAD_URL).then(r=>r.json())` → `window.__AUDIT_PAYLOAD__` (exposed for testing).
3. **Render pipeline** – `buildTable(payload.picks.active)` → rows with `data-asset` attribute.
4. **Filters** – UI toggles modify a local `filters` object, then `applyFilters()` re‑draws the table.
5. **Sorting** – `payload.picks.active.sort((a,b)=>a.wr_pct-b.wr_pct)` based on UI state.
6. **Pagination** – Slice `payload.picks.active.slice(start, end)`.
The Playwright tests will assert each transformation by reading the DOM and comparing against the raw payload.

## 5. CI Integration
- Add a **Playwright** job to `.github/workflows/audit-tests.yml`.
- Run `npm ci && npm run test:audit` on `ubuntu‑latest` with `PLAYWRIGHT_BROWSERS_PATH=0`.
- Fail the build if any test exceeds the performance threshold or if the critical‑severity banner appears.

## 6. Reporting & Artifacts
- Generate an HTML report (`npx playwright show-report`).
- Upload screenshots on failure as CI artifacts.
- Emit a JSON summary (`--reporter=json`) for downstream dashboards.

---
*Prepared for the Antigravity team – ready to be added to the repository.*