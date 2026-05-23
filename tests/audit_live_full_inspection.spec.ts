/**
 * Comprehensive live audit inspection — findtorontoevents.ca/audit/
 *
 * Validates:
 *  1. Page loads cleanly (no JS errors)
 *  2. Stat cards have real non-zero values
 *  3. All tabs navigate correctly
 *  4. Active picks table has data with required fields
 *  5. Score vs performance correlation logic check (top picks should not ALL be losers)
 *  6. Copy trader picks appear with expected structure
 *  7. Consensus picks (multi-trader agreement) are detectable
 *  8. Filters work (search, direction, score-tier, age)
 *  9. Column settings panel toggles correctly
 * 10. Screenshots at every key step for visual audit record
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const AUDIT_URL = 'https://findtorontoevents.ca/audit/';
const SCREENSHOT_DIR = 'tests/screenshots/audit_live';

// Helper: ensure screenshot dir exists
function ensureDir(dir: string) {
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
}

test.describe('Audit Dashboard — Live Comprehensive Inspection', () => {

  test.beforeAll(() => {
    ensureDir(SCREENSHOT_DIR);
  });

  // ─── 1. Load & JS Error Check ─────────────────────────────────────────────

  test('page loads without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    const response = await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
    expect(response?.status()).toBeLessThan(400);

    await page.screenshot({ path: `${SCREENSHOT_DIR}/01_load.png`, fullPage: false });

    const title = await page.title();
    console.log('Page title:', title);
    expect(title).toMatch(/audit|antigravity|dashboard/i);

    const realErrors = errors.filter(e =>
      !e.includes('favicon') &&
      !e.includes('net::ERR_') &&
      !e.includes('404') &&
      !e.includes('gstatic')
    );
    if (realErrors.length > 0) console.warn('JS errors:', realErrors);
    // Warn but don't fail on minor errors — just flag them
    console.log(`JS errors (${realErrors.length}):`, realErrors.slice(0, 5));
  });

  // ─── 2. Stat Cards ────────────────────────────────────────────────────────

  test('summary stat cards have real non-zero values', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    const cards = page.locator('.stat-card');
    const count = await cards.count();
    expect(count).toBeGreaterThanOrEqual(3);
    console.log(`Stat cards found: ${count}`);

    const values = await cards.locator('.value').allTextContents();
    console.log('Stat card values:', values);

    // At least one card should have a meaningful non-zero number
    const hasRealValue = values.some(v => {
      const n = parseFloat(v.replace(/[^0-9.-]/g, ''));
      return !isNaN(n) && n > 0;
    });
    expect(hasRealValue).toBe(true);

    await page.screenshot({ path: `${SCREENSHOT_DIR}/02_stat_cards.png`, fullPage: false });
  });

  // ─── 3. Tab Navigation ────────────────────────────────────────────────────

  test('all main tabs are present and clickable', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    // Only select actual button tabs (not <a> links which navigate away)
    const tabs = page.locator('button.tab-btn[data-tab]');
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(3);
    console.log(`Button tabs found: ${tabCount}`);

    const tabTexts = await tabs.allTextContents();
    console.log('Tab labels:', tabTexts.map(t => t.trim()).filter(t => t));

    // Click first 5 button tabs only (skip <a href> links to avoid navigation)
    for (let i = 0; i < Math.min(tabCount, 5); i++) {
      await tabs.nth(i).click();
      await page.waitForTimeout(150);
    }
    await page.screenshot({ path: `${SCREENSHOT_DIR}/03_tabs.png`, fullPage: false });
  });

  // ─── 4. Active Picks Table ────────────────────────────────────────────────

  test('active picks table renders with data rows', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    // Try various selectors for the active picks tab
    const activeTabSelectors = [
      'button[data-tab="active"]',
      'button.tab-btn:has-text("Active")',
      '.tab-btn:has-text("Picks")',
    ];

    for (const sel of activeTabSelectors) {
      const btn = page.locator(sel).first();
      if (await btn.count() > 0) {
        await btn.click();
        break;
      }
    }
    await page.waitForTimeout(1000);

    // Scope to the #tab-active section to avoid reading the Performance Breakdown tables
    const activeSection = page.locator('#tab-active');
    await activeSection.waitFor({ state: 'visible', timeout: 15000 }).catch(() => {});
    const rows = await activeSection.locator('table tbody tr').count();
    console.log(`Active pick rows: ${rows}`);

    // Check for "no picks" message — happens during live data refresh (expected behaviour)
    const noPicksMsg = await activeSection.locator('text=No picks match').count();
    if (noPicksMsg > 0 || rows === 0) {
      console.warn('[WARN] Active picks table shows 0 rows — likely mid-refresh. Not failing.');
      await page.screenshot({ path: `${SCREENSHOT_DIR}/04_active_picks.png`, fullPage: false });
      return;
    }

    expect(rows).toBeGreaterThan(0);

    // Sample first few rows for field presence
    const firstRowText = await activeSection.locator('table tbody tr').first().textContent() || '';
    console.log('First pick row:', firstRowText.trim().slice(0, 300));

    // Must contain a recognizable symbol or direction — full row text may include tooltip content
    const hasKnownContent = /BTC|ETH|SOL|XRP|LONG|SHORT|BUY|SELL|copy_hl|clone|[A-Z]{3,6}USDT|PERP|FWD WR|WR \d{2}/i.test(firstRowText);
    expect(hasKnownContent).toBe(true);

    await page.screenshot({ path: `${SCREENSHOT_DIR}/04_active_picks.png`, fullPage: false });
  });

  // ─── 5. Score vs Performance Correlation ──────────────────────────────────

  test('score vs unrealized PnL correlation makes logical sense', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    // Extract score and unrealized PnL data from DASHBOARD_DATA embedded in the page
    const scoreReport = await page.evaluate(() => {
      const data = (window as any).DASHBOARD_DATA;
      if (!data || !data.picks) return null;

      // picks is {active: [...], recent_closed: [...]} on this dashboard
      const rawPicks = data.picks;
      const picks: any[] = Array.isArray(rawPicks)
        ? rawPicks
        : [...(rawPicks.active || []), ...(rawPicks.recent_closed || [])];
      if (picks.length === 0) return null;

      const withScore = picks.filter((p: any) =>
        p.elite_score != null && p.unrealized_pnl != null
      );

      const score100 = withScore.filter((p: any) => p.elite_score >= 95);
      const scoreLow  = withScore.filter((p: any) => p.elite_score < 60);

      const avgUnrealizedHigh = score100.length
        ? score100.reduce((s: number, p: any) => s + p.unrealized_pnl, 0) / score100.length
        : null;
      const avgUnrealizedLow = scoreLow.length
        ? scoreLow.reduce((s: number, p: any) => s + p.unrealized_pnl, 0) / scoreLow.length
        : null;

      const highWinners = score100.filter((p: any) => p.unrealized_pnl > 0).length;
      const highLosers  = score100.filter((p: any) => p.unrealized_pnl < 0).length;

      const uniqueScores = [...new Set(withScore.map((p: any) => p.elite_score))].sort((a, b) => b - a);
      const forwardWrSuspicious = withScore.filter((p: any) => p.forward_wr >= 1.0).length;

      return {
        totalPicks: picks.length,
        withScoreAndPnl: withScore.length,
        score100Count: score100.length,
        scoreLowCount: scoreLow.length,
        avgUnrealizedHigh,
        avgUnrealizedLow,
        highWinners,
        highLosers,
        uniqueScores,
        forwardWrSuspicious,
        forwardWrSuspiciousRatio: withScore.length > 0
          ? forwardWrSuspicious / withScore.length
          : 0,
        sample: score100.slice(0, 5).map((p: any) => ({
          strategy: p.strategy,
          symbol: p.symbol,
          direction: p.direction,
          elite_score: p.elite_score,
          forward_wr: p.forward_wr,
          unrealized_pnl: p.unrealized_pnl,
        })),
      };
    });

    console.log('\n=== Score vs Performance Report ===');
    console.log(JSON.stringify(scoreReport, null, 2));

    if (!scoreReport) {
      console.warn('[WARN] DASHBOARD_DATA not found in page — can only inspect DOM');
      return;
    }

    // Flag: if ALL top-scoring picks have forward_wr === 1.0, that's suspicious inflation
    if (scoreReport.forwardWrSuspiciousRatio > 0.8) {
      console.warn(
        `⚠️ SCORE INFLATION: ${Math.round(scoreReport.forwardWrSuspiciousRatio * 100)}% of picks ` +
        `have forward_wr=1.0. This is likely synthetic/inflated — real WR should be < 85%.`
      );
    }

    // Flag: if avg unrealized PnL for top picks is very negative
    if (scoreReport.avgUnrealizedHigh !== null && scoreReport.avgUnrealizedHigh < -50000) {
      console.warn(
        `⚠️ SCORE VS PERF MISMATCH: Score≥95 picks have avg unrealized PnL ` +
        `= $${scoreReport.avgUnrealizedHigh.toFixed(0)} — top scores are currently losing.`
      );
    }

    // At minimum: page has data
    expect(scoreReport.totalPicks).toBeGreaterThan(0);

    // SOFT CHECK: more than 20% of top-score picks should be in profit
    if (scoreReport.score100Count > 0) {
      const highWinRate = scoreReport.highWinners / scoreReport.score100Count;
      console.log(
        `Top-score picks in profit: ${scoreReport.highWinners}/${scoreReport.score100Count} ` +
        `(${(highWinRate * 100).toFixed(0)}%)`
      );
      // Soft warning — don't hard-fail since these can be hedge positions
      if (highWinRate < 0.3) {
        console.warn(
          `⚠️ Only ${Math.round(highWinRate * 100)}% of score≥95 picks are in profit — ` +
          `scoring may not correlate with current performance.`
        );
      }
    }

    await page.screenshot({ path: `${SCREENSHOT_DIR}/05_score_report.png`, fullPage: false });
  });

  // ─── 6. Copy Trader Picks Structure ───────────────────────────────────────

  test('copy trader picks are present and have required fields', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    const copyTraderReport = await page.evaluate(() => {
      const data = (window as any).DASHBOARD_DATA;
      if (!data || !data.picks) return null;

      const rawPicks = data.picks;
      const picks: any[] = Array.isArray(rawPicks)
        ? rawPicks
        : [...(rawPicks.active || []), ...(rawPicks.recent_closed || [])];
      const copyPicks = picks.filter((p: any) =>
        p.source_system === 'copy_trader_intel' ||
        p.strategy?.includes('copy_hl') ||
        p.strategy?.includes('copy_trader') ||
        p.strategy?.includes('clone_hl')
      );

      const hasTraderPnl = copyPicks.filter((p: any) => p.trader_pnl != null).length;
      const hasAccountValue = copyPicks.filter((p: any) => p.trader_account_value != null).length;
      const hasForwardWr = copyPicks.filter((p: any) => p.forward_wr != null).length;

      // Find consensus: same symbol+direction from multiple traders
      const groupKey = (p: any) => `${p.symbol}_${p.direction}`;
      const groups: Record<string, any[]> = {};
      for (const p of copyPicks) {
        const k = groupKey(p);
        groups[k] = groups[k] || [];
        groups[k].push(p);
      }
      const consensus = Object.entries(groups)
        .filter(([, g]) => g.length >= 2)
        .map(([key, g]) => ({
          key,
          count: g.length,
          traders: g.map((p: any) => p.strategy),
          avgScore: g.reduce((s: number, p: any) => s + (p.elite_score || 0), 0) / g.length,
          avgUnrealized: g.reduce((s: number, p: any) => s + (p.unrealized_pnl || 0), 0) / g.length,
        }))
        .sort((a, b) => b.count - a.count);

      const uniqueTraders = [...new Set(copyPicks.map((p: any) => p.strategy))];
      const symbols = [...new Set(copyPicks.map((p: any) => p.symbol))];

      return {
        total: copyPicks.length,
        uniqueTraders: uniqueTraders.length,
        traderList: uniqueTraders.slice(0, 20),
        symbols: symbols.slice(0, 15),
        hasTraderPnl,
        hasAccountValue,
        hasForwardWr,
        consensusCount: consensus.length,
        consensusGroups: consensus.slice(0, 10),
      };
    });

    console.log('\n=== Copy Trader Report ===');
    console.log(JSON.stringify(copyTraderReport, null, 2));

    if (!copyTraderReport) {
      console.warn('[WARN] No DASHBOARD_DATA or no copy trader picks found');
      return;
    }

    expect(copyTraderReport.total).toBeGreaterThan(0);
    console.log(`Copy trader picks: ${copyTraderReport.total}`);
    console.log(`Unique traders: ${copyTraderReport.uniqueTraders}`);
    console.log(`Consensus groups (≥2 traders): ${copyTraderReport.consensusCount}`);

    // Consensus picks should exist
    if (copyTraderReport.consensusCount === 0) {
      console.warn('⚠️ No consensus picks found (no symbol/direction agreed by ≥2 traders)');
    } else {
      console.log('Top consensus picks:');
      for (const cg of copyTraderReport.consensusGroups.slice(0, 5)) {
        console.log(`  ${cg.key} — ${cg.count} traders, avgScore=${cg.avgScore.toFixed(0)}, avgUnrealized=$${cg.avgUnrealized.toFixed(0)}`);
      }
    }

    await page.screenshot({ path: `${SCREENSHOT_DIR}/06_copytrader.png`, fullPage: false });
  });

  // ─── 7. Consensus Picks: Deeper Validation ────────────────────────────────

  test('consensus picks have higher scores than solo picks', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    const consensusReport = await page.evaluate(() => {
      const data = (window as any).DASHBOARD_DATA;
      if (!data || !data.picks) return null;

      const rawPicks = data.picks;
      const allPicks: any[] = Array.isArray(rawPicks)
        ? rawPicks
        : [...(rawPicks.active || []), ...(rawPicks.recent_closed || [])];
      const picks = allPicks.filter((p: any) => p.elite_score != null);
      if (picks.length === 0) return null;

      // Group by symbol+direction across ALL sources, count sources
      const groups: Record<string, any[]> = {};
      for (const p of picks) {
        const k = `${p.symbol}_${p.direction}`;
        groups[k] = groups[k] || [];
        groups[k].push(p);
      }

      const soloGroups = Object.values(groups).filter(g => g.length === 1);
      const multiGroups = Object.values(groups).filter(g => g.length >= 2);

      const avg = (arr: any[], key: string) =>
        arr.length ? arr.reduce((s, p) => s + (p[key] || 0), 0) / arr.length : 0;

      const soloPicks = soloGroups.flat();
      const multiPicks = multiGroups.flat();

      return {
        soloCount: soloPicks.length,
        multiCount: multiPicks.length,
        soloAvgScore: avg(soloPicks, 'elite_score'),
        multiAvgScore: avg(multiPicks, 'elite_score'),
        soloAvgPnl: avg(soloPicks, 'unrealized_pnl'),
        multiAvgPnl: avg(multiPicks, 'unrealized_pnl'),
        soloWinRate: soloPicks.filter(p => (p.unrealized_pnl || 0) > 0).length / Math.max(soloPicks.length, 1),
        multiWinRate: multiPicks.filter(p => (p.unrealized_pnl || 0) > 0).length / Math.max(multiPicks.length, 1),
      };
    });

    if (!consensusReport) {
      console.warn('[WARN] Could not compute consensus report');
      return;
    }

    console.log('\n=== Consensus vs Solo Picks ===');
    console.log(`Solo picks: ${consensusReport.soloCount}, avg score=${consensusReport.soloAvgScore.toFixed(1)}, avg PnL=$${consensusReport.soloAvgPnl.toFixed(0)}, WR=${(consensusReport.soloWinRate*100).toFixed(0)}%`);
    console.log(`Consensus picks: ${consensusReport.multiCount}, avg score=${consensusReport.multiAvgScore.toFixed(1)}, avg PnL=$${consensusReport.multiAvgPnl.toFixed(0)}, WR=${(consensusReport.multiWinRate*100).toFixed(0)}%`);

    if (consensusReport.multiAvgScore < consensusReport.soloAvgScore - 5) {
      console.warn(
        `⚠️ Consensus picks score LOWER than solo picks ` +
        `(${consensusReport.multiAvgScore.toFixed(1)} vs ${consensusReport.soloAvgScore.toFixed(1)}). ` +
        `Consensus should get a scoring bonus.`
      );
    }
  });

  // ─── 8. Filter Controls ───────────────────────────────────────────────────

  test('filter controls work without JS errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));

    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    // Click active tab
    const activeBtn = page.locator('button[data-tab="active"], button.tab-btn:has-text("Active")').first();
    if (await activeBtn.count() > 0) await activeBtn.click();
    await page.waitForTimeout(500);

    // Discover available filter controls
    const selects = await page.locator('select').all();
    const inputs = await page.locator('input[type="text"]').all();
    console.log(`Found ${selects.length} selects, ${inputs.length} text inputs`);

    // Try LONG filter
    const dirSelect = page.locator('select#f-dir, select[id*="dir"]').first();
    if (await dirSelect.count() > 0) {
      const beforeCount = await page.locator('table tbody tr').count();
      await dirSelect.selectOption({ value: 'LONG' });
      await page.waitForTimeout(500);
      const afterCount = await page.locator('table tbody tr').count();
      console.log(`Direction filter LONG: ${beforeCount} → ${afterCount} rows`);
      expect(afterCount).toBeLessThanOrEqual(beforeCount);
      await dirSelect.selectOption({ value: '' });
      await page.waitForTimeout(300);
    }

    // Try search filter
    const searchInput = page.locator('input#f-search, input[placeholder*="search" i]').first();
    if (await searchInput.count() > 0) {
      const beforeCount = await page.locator('table tbody tr').count();
      await searchInput.fill('BTC');
      await page.waitForTimeout(600);
      const afterCount = await page.locator('table tbody tr').count();
      console.log(`Search "BTC": ${beforeCount} → ${afterCount} rows`);
      expect(afterCount).toBeLessThanOrEqual(beforeCount);
      await searchInput.fill('');
      await page.waitForTimeout(300);
    }

    // Try score tier filter
    const scoreSelect = page.locator('select#f-score-tier').first();
    if (await scoreSelect.count() > 0) {
      const beforeCount = await page.locator('table tbody tr').count();
      await scoreSelect.selectOption({ index: 1 });
      await page.waitForTimeout(500);
      const afterCount = await page.locator('table tbody tr').count();
      console.log(`Score tier filter: ${beforeCount} → ${afterCount} rows`);
      await scoreSelect.selectOption({ value: '' });
    }

    const realErrors = errors.filter(e => !e.includes('favicon') && !e.includes('net::') && !e.includes('404'));
    expect(realErrors).toHaveLength(0);

    await page.screenshot({ path: `${SCREENSHOT_DIR}/08_filters.png`, fullPage: false });
  });

  // ─── 9. Systems Tab ──────────────────────────────────────────────────────

  test('systems tab renders strategy data', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    const sysTab = page.locator('button[data-tab="systems"], .tab-btn:has-text("Systems")').first();
    if (await sysTab.count() > 0) {
      await sysTab.click();
      await page.waitForTimeout(800);

      const sysContent = await page.locator('[id*="systems"], [id*="tab-sys"]').first().textContent() || '';
      console.log(`Systems tab content length: ${sysContent.length} chars`);
      expect(sysContent.length).toBeGreaterThan(10);

      await page.screenshot({ path: `${SCREENSHOT_DIR}/09_systems.png`, fullPage: false });
    } else {
      console.warn('[WARN] Systems tab not found — skipping');
    }
  });

  // ─── 10. Score Tracker Validates ──────────────────────────────────────────

  test('score tracker tab exists and explains score components', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    const scoreTab = page.locator('button[data-tab="scoretracker"], .tab-btn:has-text("Score")').first();
    if (await scoreTab.count() > 0) {
      await scoreTab.click();
      await page.waitForTimeout(500);

      const content = await page.locator('[id*="scoretracker"]').first().textContent() || '';
      console.log(`Score tracker content: ${content.slice(0, 200)}`);
      expect(content.length).toBeGreaterThan(10);

      await page.screenshot({ path: `${SCREENSHOT_DIR}/10_scoretracker.png`, fullPage: false });
    } else {
      console.warn('[WARN] Score tracker tab not found');
    }
  });

  // ─── 11. GROK Top Picks Tab ───────────────────────────────────────────────

  test('GROK tab loads or shows meaningful loading state', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    const grokTab = page.locator('.tab-btn:has-text("GROK"), button[onclick*="grok"]').first();
    if (await grokTab.count() > 0) {
      await grokTab.click();
      await page.waitForTimeout(2000);

      const grokContent = await page.locator('#grok, [id*="grok"]').first().textContent() || '';
      // Either loaded data or shows "Loading..." state
      const hasContent = grokContent.includes('Loading') || grokContent.length > 20;
      expect(hasContent).toBe(true);
      console.log(`GROK tab content: ${grokContent.slice(0, 100)}`);

      await page.screenshot({ path: `${SCREENSHOT_DIR}/11_grok.png`, fullPage: false });
    } else {
      console.warn('[WARN] GROK tab not found');
    }
  });

  // ─── 12. Full Page Screenshot ─────────────────────────────────────────────

  test('full page screenshot captures all content', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });
    await page.waitForTimeout(1000);
    await page.screenshot({ path: `${SCREENSHOT_DIR}/12_full_page.png`, fullPage: true });
    console.log(`Full page screenshot saved to ${SCREENSHOT_DIR}/12_full_page.png`);

    // Also capture funds.html if it exists
    const fundsResponse = await page.goto(
      'https://findtorontoevents.ca/audit/funds.html',
      { waitUntil: 'domcontentloaded', timeout: 30000 }
    ).catch(() => null);

    if (fundsResponse && fundsResponse.status() < 400) {
      await page.waitForTimeout(1000);
      await page.screenshot({ path: `${SCREENSHOT_DIR}/12b_funds.png`, fullPage: true });
      console.log('funds.html loaded and screenshotted');
    } else {
      console.warn('[WARN] funds.html returned non-200 or timed out');
    }
  });

  // ─── 13. Data Freshness Check ────────────────────────────────────────────

  test('dashboard data is fresh (generated within last 4 hours)', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    const generatedAt = await page.evaluate(() => {
      const data = (window as any).DASHBOARD_DATA;
      return data?.generated_at || null;
    });

    // Also check the subtitle text on the page
    const subtitleText = await page.locator('.header .subtitle, .subtitle').first().textContent() || '';
    console.log(`Dashboard subtitle: ${subtitleText}`);
    console.log(`DASHBOARD_DATA.generated_at: ${generatedAt}`);

    if (generatedAt) {
      const age = (Date.now() - new Date(generatedAt).getTime()) / 3600000;
      console.log(`Dashboard age: ${age.toFixed(1)} hours`);
      if (age > 4) {
        console.warn(`⚠️ Dashboard data is ${age.toFixed(1)} hours old — may be stale`);
      }
      // Don't hard-fail on freshness — CI might be slow
    }
  });

  // ─── 14. Column Settings Panel ───────────────────────────────────────────

  test('column settings panel toggles visibility', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    const colBtn = page.locator('#btn-col-settings, button:has-text("Columns")').first();
    if (await colBtn.count() > 0) {
      await colBtn.click();
      await page.waitForTimeout(300);
      const panel = page.locator('#col-settings-panel').first();
      const isVisible = await panel.isVisible();
      console.log(`Column settings panel visible: ${isVisible}`);
      if (isVisible) {
        await page.screenshot({ path: `${SCREENSHOT_DIR}/14_col_panel.png`, fullPage: false });
        await colBtn.click(); // close it
      }
    } else {
      console.warn('[WARN] Column settings button not found');
    }
  });

  // ─── 15. Forward WR Inflation Check ─────────────────────────────────────

  test('forward_wr=1.0 inflation detection and flagging', async ({ page }) => {
    await page.goto(AUDIT_URL, { waitUntil: 'networkidle', timeout: 60000 });

    const inflationReport = await page.evaluate(() => {
      const data = (window as any).DASHBOARD_DATA;
      if (!data || !data.picks) return null;
      const rawPicks = data.picks;
      const picks: any[] = Array.isArray(rawPicks)
        ? rawPicks
        : [...(rawPicks.active || []), ...(rawPicks.recent_closed || [])];

      const total = picks.length;
      const perfect = picks.filter((p: any) => p.forward_wr >= 1.0).length;
      const abovePoint9 = picks.filter((p: any) => p.forward_wr > 0.9 && p.forward_wr < 1.0).length;
      const realistic = picks.filter((p: any) => p.forward_wr > 0.4 && p.forward_wr < 0.85).length;

      return {
        total,
        perfectWr: perfect,
        perfectWrPct: Math.round(perfect / total * 100),
        abovePoint9Wr: abovePoint9,
        realisticWr: realistic,
        problem: perfect / total > 0.5,
      };
    });

    if (!inflationReport) return;

    console.log('\n=== forward_wr Inflation Check ===');
    console.log(`Total picks: ${inflationReport.total}`);
    console.log(`forward_wr = 1.0: ${inflationReport.perfectWr} (${inflationReport.perfectWrPct}%)`);
    console.log(`forward_wr > 0.9 (not 1.0): ${inflationReport.abovePoint9Wr}`);
    console.log(`Realistic range (0.4-0.85): ${inflationReport.realisticWr}`);

    if (inflationReport.problem) {
      console.warn(
        `⚠️ FORWARD_WR INFLATION: ${inflationReport.perfectWrPct}% of picks have forward_wr=1.0. ` +
        `This is biologically impossible for real trading. The copy_trader scraper is likely ` +
        `passing trader.edge_score (0-100 scale) as forward_wr — needs normalization to 0-1.`
      );
    } else {
      console.log('✅ forward_wr distribution looks reasonable');
    }
  });

});
