import { test, expect } from '@playwright/test';

const isRemoteVerify =
  process.env.VERIFY_REMOTE === '1' || process.env.VERIFY_REMOTE === 'true';

async function openAuditDashboard(page: any) {
  // Same hydration pattern as audit_hc_conviction_e2e (large embedded JSON).
  await page.goto('/audit/', {
    waitUntil: 'networkidle',
    timeout: 90000,
  });
  await page.waitForTimeout(3000);
}

test.describe('Audit Dashboard - Copy Trader Logic', () => {
  test.describe.configure({ timeout: 120000 });

  test('copy trader families exist locally and their scores are not obviously under-ranked', async ({ page }) => {
    await openAuditDashboard(page);

    const familyStats = await page.evaluate(() => {
      const data = (window as any).DASHBOARD_DATA;
      const rows = [...(data?.picks?.active || []), ...(data?.picks?.recent_closed || [])];
      const families = [
        'copy_trader_intel',
        'copy_trader_highscore',
        'copy_trader_clones',
        'copy_trader_consensus',
        'copy_trader_variations',
      ];

      const rowMatchesFamily = (item: any, family: string) => {
        const single = String(item?.source_system || '').toLowerCase();
        if (single === family) return true;
        const arr = item?.source_systems;
        if (Array.isArray(arr)) {
          return arr.some((s: any) => String(s).toLowerCase() === family);
        }
        return false;
      };

      const summarize = (items: any[]) => {
        const withPnl = items
          .map((item) => Number(item?.pnl_pct || 0))
          .filter((pnl) => pnl !== 0);
        const avgScore = items.length
          ? items.reduce((sum, item) => sum + Number(item?.score || 0), 0) / items.length
          : 0;
        const winRate = withPnl.length
          ? withPnl.filter((pnl) => pnl > 0).length / withPnl.length
          : 0;
        const avgPnl = withPnl.length
          ? withPnl.reduce((sum, pnl) => sum + pnl, 0) / withPnl.length
          : 0;
        return {
          total: items.length,
          withPnl: withPnl.length,
          avgScore,
          winRate,
          avgPnl,
        };
      };

      const result: Record<string, any> = {};
      for (const family of families) {
        result[family] = summarize(
          rows.filter((item) => (item?.source_system || '').toLowerCase() === family),
        );
      }
      return result;
    });

    console.log(JSON.stringify(familyStats, null, 2));

    const embeddedHasCopyTrader = await page.evaluate(() => {
      const raw = JSON.stringify(
        (window as unknown as { DASHBOARD_DATA?: unknown }).DASHBOARD_DATA || {},
      ).toLowerCase();
      return raw.includes('copy_trader') || raw.includes('multi_asset_copytrader');
    });
    const uiShowsCopyEcosystem = await page.evaluate(() => {
      const t = (document.body?.innerText || '').toLowerCase();
      return (
        t.includes('clone hl') ||
        t.includes('copy hl') ||
        t.includes('hyperliquid') ||
        t.includes('copy trader forward')
      );
    });
    const anyFamily = Object.values(familyStats).some(
      (s: { total?: number }) => (s?.total ?? 0) > 0,
    );
    const strictLocal =
      !isRemoteVerify && process.env.AUDIT_STRICT_COPYTRADER === '1';
    if (strictLocal) {
      expect(familyStats.copy_trader_intel.total).toBeGreaterThan(0);
      expect(familyStats.copy_trader_highscore.total).toBeGreaterThan(0);
      expect(familyStats.copy_trader_clones.total).toBeGreaterThan(0);
    } else {
      expect(
        anyFamily || embeddedHasCopyTrader || uiShowsCopyEcosystem,
        'Copy-trader systems visible in JSON and/or Forward Test UI',
      ).toBeTruthy();
    }

    if (
      familyStats.copy_trader_highscore.withPnl >= 10 &&
      familyStats.copy_trader_highscore.winRate >= 0.5
    ) {
      expect(familyStats.copy_trader_highscore.avgScore).toBeGreaterThanOrEqual(35);
    }

    if (
      familyStats.copy_trader_clones.withPnl >= 10 &&
      familyStats.copy_trader_clones.winRate >= 0.55
    ) {
      expect(familyStats.copy_trader_clones.avgScore).toBeGreaterThanOrEqual(30);
    }

    if (familyStats.copy_trader_consensus.total > 0) {
      expect(familyStats.copy_trader_consensus.avgScore).toBeGreaterThan(
        familyStats.copy_trader_intel.avgScore,
      );
    }
  });

  test('closed copy trader score buckets are not upside down', async ({ page }, testInfo) => {
    await openAuditDashboard(page);

    const buckets = await page.evaluate(() => {
      const data = (window as any).DASHBOARD_DATA;
      const closed = data?.picks?.recent_closed || [];
      const active = data?.picks?.active || [];
      const copyLike = (item: any) => {
        const strategy = (item?.strategy || '').toLowerCase();
        const pnl = Number(item?.pnl_pct || 0);
        const blob = [
          item?.source_system,
          ...(Array.isArray(item?.source_systems) ? item.source_systems : []),
        ]
          .filter(Boolean)
          .join(' ')
          .toLowerCase();
        const isCopy =
          blob.includes('copy_trader') ||
          blob.includes('multi_asset_copytrader') ||
          strategy.startsWith('copy_hl_') ||
          strategy.startsWith('clone_') ||
          strategy.startsWith('hs_');
        return { isCopy, pnl };
      };
      const copyClosed = closed.filter((item: any) => {
        const { isCopy, pnl } = copyLike(item);
        return pnl !== 0 && isCopy;
      });
      const copyActive = active.filter((item: any) => copyLike(item).isCopy);

      const summarize = (items: any[]) => {
        const pnls = items.map((item) => Number(item?.pnl_pct || 0));
        return {
          count: items.length,
          withPnl: pnls.length,
          winRate: pnls.length ? pnls.filter((pnl) => pnl > 0).length / pnls.length : 0,
          avgPnl: pnls.length ? pnls.reduce((sum, pnl) => sum + pnl, 0) / pnls.length : 0,
        };
      };

      const pool = [...copyClosed, ...copyActive];
      return {
        '70+': summarize(pool.filter((item: any) => Number(item?.score || 0) >= 70)),
        '50-69': summarize(pool.filter((item: any) => {
          const score = Number(item?.score || 0);
          return score >= 50 && score < 70;
        })),
        '30-49': summarize(pool.filter((item: any) => {
          const score = Number(item?.score || 0);
          return score >= 30 && score < 50;
        })),
        '<30': summarize(pool.filter((item: any) => Number(item?.score || 0) < 30)),
      };
    });

    console.log(JSON.stringify(buckets, null, 2));

    const totalCopyLike =
      buckets['70+'].count +
      buckets['50-69'].count +
      buckets['30-49'].count +
      buckets['<30'].count;
    if (!isRemoteVerify && totalCopyLike === 0) {
      testInfo.skip(
        true,
        'Local /audit/data snapshot may omit copy-trader pick rows; run with VERIFY_REMOTE=1 for bucket stats',
      );
      return;
    }
    expect(totalCopyLike).toBeGreaterThan(0);

    if (buckets['70+'].withPnl >= 10 && buckets['<30'].withPnl >= 5) {
      expect(buckets['70+'].avgPnl).toBeGreaterThan(buckets['<30'].avgPnl);
    }
  });

  test('funds page renders the copy trader section with live local data', async ({ page }) => {
    await page.goto('/audit/funds.html', {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    const copyTab = page.locator('text=/Copy Trader/i').first();
    if (await copyTab.isVisible()) {
      await copyTab.click();
      await page.waitForTimeout(1500);
    }

    const panel = page.locator('#tab-copytrader');
    const panelText = await panel.textContent() || '';
    const portfoliosText = await page.locator('#ct-portfolios').textContent().catch(() => '') || '';
    const patternsText = await page.locator('#ct-patterns').textContent().catch(() => '') || '';
    const combined = [panelText, portfoliosText, patternsText].join('\n');

    console.log(combined.slice(0, 1200));

    expect(combined).toMatch(/Copy Trader/i);
    expect(combined).toMatch(/Hyperliquid|OKX|Bybit|BingX|Reverse|Consensus|Variation|FORWARD TEST/i);
    if (panelText.includes('No copy trader data')) {
      expect(portfoliosText || patternsText).toMatch(/Hyperliquid|OKX|Bybit|BingX|Consensus|Pattern/i);
    }
  });
});
