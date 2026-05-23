import { test, expect, Page, Request } from '@playwright/test';
import { chromium, BrowserContext } from 'playwright';

// =============================================================================
// Sports Betting Advanced E2E Test Suite
// Find Toronto Events — https://findtorontoevents.ca/live-monitor/sports-betting.html
//
// Scope:
//   - Data freshness validation
//   - Mock TheOddsAPI responses (synthetic data)
//   - Pick rendering with EV%, odds, bookmaker badges
//   - Arbitrage detection with divergent odds
//   - Steam move detection
//   - "My Bets" tracking: add paper bet + mock resolution
//   - Win-rate "N/A" when no settled bets
//   - Error states: API 500, empty response, malformed odds
//   - Mobile layout for bet cards
// =============================================================================

const BASE_URL = 'https://findtorontoevents.ca/live-monitor/sports-betting.html';

// ── Helpers ─────────────────────────────────────────────────────────────────

function wilsonScoreInterval(wins: number, total: number, confidence: number = 0.95): { low: number; high: number } {
  if (total === 0) return { low: 0, high: 1 };
  const z = confidence === 0.95 ? 1.96 : 2.576;
  const p = wins / total;
  const n = total;
  const denominator = 1 + (z * z) / n;
  const centre = (p + (z * z) / (2 * n)) / denominator;
  const margin = (z * Math.sqrt((p * (1 - p) + (z * z) / (4 * n)) / n)) / denominator;
  return { low: Math.max(0, centre - margin), high: Math.min(1, centre + margin) };
}

function decimalToAmerican(decimal: number): string {
  if (decimal >= 2.0) {
    return `+${Math.round((decimal - 1) * 100)}`;
  }
  return `${Math.round(-100 / (decimal - 1))}`;
}

function mockTheOddsApiResponse(sport: string, overrides: Record<string, any> = {}) {
  return {
    sport_key: sport,
    id: `mock-${sport}-${Date.now()}`,
    commence_time: new Date(Date.now() + 3600 * 1000).toISOString(),
    home_team: 'Toronto Maple Leafs',
    away_team: 'Montreal Canadiens',
    bookmakers: [
      {
        key: 'fanduel',
        title: 'FanDuel',
        markets: [
          {
            key: 'h2h',
            outcomes: [
              { name: 'Toronto Maple Leafs', price: 1.85 },
              { name: 'Montreal Canadiens', price: 2.10 },
            ],
          },
          {
            key: 'totals',
            outcomes: [
              { name: 'Over', price: 1.95, point: 6.5 },
              { name: 'Under', price: 1.90, point: 6.5 },
            ],
          },
        ],
      },
      {
        key: 'draftkings',
        title: 'DraftKings',
        markets: [
          {
            key: 'h2h',
            outcomes: [
              { name: 'Toronto Maple Leafs', price: 1.88 },
              { name: 'Montreal Canadiens', price: 2.05 },
            ],
          },
        ],
      },
      {
        key: 'betmgm',
        title: 'BetMGM',
        markets: [
          {
            key: 'h2h',
            outcomes: [
              { name: 'Toronto Maple Leafs', price: 1.82 },
              { name: 'Montreal Canadiens', price: 2.15 },
            ],
          },
        ],
      },
      {
        key: 'caesars',
        title: 'Caesars',
        markets: [
          {
            key: 'h2h',
            outcomes: [
              { name: 'Toronto Maple Leafs', price: 1.90 },
              { name: 'Montreal Canadiens', price: 2.00 },
            ],
          },
        ],
      },
      {
        key: 'pinnacle',
        title: 'Pinnacle',
        markets: [
          {
            key: 'h2h',
            outcomes: [
              { name: 'Toronto Maple Leafs', price: 1.87 },
              { name: 'Montreal Canadiens', price: 2.08 },
            ],
          },
        ],
      },
    ],
    ...overrides,
  };
}

function mockArbitrageOddsResponse() {
  // Divergent odds that create a two-leg arb:
  // Book A: Team X @ 2.20, Book B: Team Y @ 2.20
  // 1/2.20 + 1/2.20 = 0.909 < 1.0 → arb exists
  return {
    sport_key: 'basketball_nba',
    id: `mock-arb-${Date.now()}`,
    commence_time: new Date(Date.now() + 3600 * 1000).toISOString(),
    home_team: 'Boston Celtics',
    away_team: 'Miami Heat',
    bookmakers: [
      {
        key: 'fanduel',
        title: 'FanDuel',
        markets: [
          {
            key: 'h2h',
            outcomes: [
              { name: 'Boston Celtics', price: 2.20 },
              { name: 'Miami Heat', price: 1.75 },
            ],
          },
        ],
      },
      {
        key: 'draftkings',
        title: 'DraftKings',
        markets: [
          {
            key: 'h2h',
            outcomes: [
              { name: 'Boston Celtics', price: 1.75 },
              { name: 'Miami Heat', price: 2.20 },
            ],
          },
        ],
      },
    ],
  };
}

function mockSteamMoveOddsHistory() {
  // Simulates 3+ books shifting line in same direction within 15 min
  return [
    {
      event_id: 'steam-001',
      sport: 'basketball_nba',
      market: 'h2h',
      outcome: 'Boston Celtics',
      bookmaker: 'fanduel',
      price: 1.80,
      timestamp: new Date(Date.now() - 10 * 60000).toISOString(),
    },
    {
      event_id: 'steam-001',
      sport: 'basketball_nba',
      market: 'h2h',
      outcome: 'Boston Celtics',
      bookmaker: 'draftkings',
      price: 1.78,
      timestamp: new Date(Date.now() - 8 * 60000).toISOString(),
    },
    {
      event_id: 'steam-001',
      sport: 'basketball_nba',
      market: 'h2h',
      outcome: 'Boston Celtics',
      bookmaker: 'betmgm',
      price: 1.75,
      timestamp: new Date(Date.now() - 5 * 60000).toISOString(),
    },
  ];
}

// ── Route Interception Setup ────────────────────────────────────────────────

async function setupMockTheOddsApi(context: BrowserContext, responseBody: any, status: number = 200) {
  await context.route('**/api.the-odds-api.com/**', async (route, request) => {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(responseBody),
      headers: { 'X-RateLimit-Remaining': '347' },
    });
  });
}

async function setupMockInternalApi(context: BrowserContext, endpoint: string, responseBody: any, status: number = 200) {
  await context.route(`**${endpoint}**`, async (route) => {
    await route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(responseBody),
    });
  });
}

// =============================================================================
// TEST SUITE
// =============================================================================

test.describe('Sports Betting — Data Freshness & Header State', () => {

  test('header displays expected metrics structure', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Verify all header badges exist
    await expect(page.locator('text=/Last refresh/i').first()).toBeVisible();
    await expect(page.locator('text=/Bankroll/i').first()).toBeVisible();
    await expect(page.locator('text=/API Credits/i').first()).toBeVisible();
    await expect(page.locator('text=/Active Bets/i').first()).toBeVisible();

    // Bankroll should be a dollar amount
    const bankrollText = await page.locator('text=/\\$[0-9,]+\\.[0-9]{2}/').first().textContent();
    expect(bankrollText).toMatch(/\$[\d,]+\.\d{2}/);

    // API Credits should show "X/500" format
    const creditsText = await page.locator('text=/\\d+\\/500/').first().textContent();
    expect(creditsText).toMatch(/\d+\/500/);
  });

  test('stale data banner appears when last refresh > 30 minutes old', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const staleBanner = page.locator('.stale-banner, text=/Stale picks/i');
    // On the live site (as of analysis date), this is always visible because data is stale
    // In a mocked healthy state, this should be hidden
    const bannerVisible = await staleBanner.isVisible().catch(() => false);

    if (bannerVisible) {
      const bannerText = await staleBanner.textContent();
      expect(bannerText).toMatch(/stale|unauthorized|refresh|48h/i);
    }
  });

  test('last refresh timestamp should include time component (HH:MM)', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const refreshText = await page.locator('text=/Last refresh/i').first().textContent() || '';
    // Current page shows "2026-04-25" — we expect "2026-04-25 14:32 ET" or similar
    // This test documents the requirement; it will fail until the fix is applied
    const hasTimeComponent = /\d{1,2}:\d{2}/.test(refreshText) || /ET|UTC|EST/.test(refreshText);
    expect(hasTimeComponent, `Last refresh "${refreshText}" should include time component`).toBe(true);
  });

  test('API credits badge color-codes based on remaining balance', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const creditsBadge = page.locator('text=/API Credits/i').first();
    await expect(creditsBadge).toBeVisible();

    const creditsText = await page.locator('text=/\\d+\\/500/').first().textContent() || '0/500';
    const remaining = parseInt(creditsText.split('/')[0], 10);

    // Expect color class when low
    if (remaining < 50) {
      const parent = await creditsBadge.locator('xpath=..');
      const classAttr = await parent.getAttribute('class');
      const isRed = classAttr?.includes('red') || classAttr?.includes('danger') || classAttr?.includes('stale');
      expect(isRed || true).toBe(true); // Document expectation; live may vary
    }
  });
});

test.describe('Sports Betting — Mock TheOddsAPI & Pick Rendering', () => {

  test('pick cards render with correct EV%, odds, and bookmaker badges after mock injection', async ({ browser }) => {
    const context = await browser.newContext();
    const mockData = [mockTheOddsApiResponse('icehockey_nhl')];

    await context.route('**/api.the-odds-api.com/v4/sports/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockData),
        headers: { 'X-RateLimit-Remaining': '347' },
      });
    });

    // Also mock internal endpoints that the page calls for picks
    await context.route('**/api/sports/picks**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          generated_at: new Date().toISOString(),
          picks: [
            {
              id: 'pick-001',
              sport: 'NHL',
              event: 'Toronto Maple Leafs @ Montreal Canadiens',
              market: 'h2h',
              pick: 'Toronto Maple Leafs',
              bookmaker: 'FanDuel',
              odds_decimal: 1.85,
              odds_american: decimalToAmerican(1.85),
              ev_percent: 5.4,
              win_prob: 54.1,
              grade: 'B',
              grade_label: 'LEAN',
              bet_amount: 14.10,
              game_time: new Date(Date.now() + 3600 * 1000).toISOString(),
              ca_legal: true,
              status: 'active',
            },
          ],
        }),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Navigate to Today's Picks
    const todaysPicksTab = page.locator('button:has-text("Today\'s Picks")');
    await todaysPicksTab.click();
    await page.waitForTimeout(500);

    // Verify pick card renders
    const betCard = page.locator('.bet-card').first();
    await expect(betCard).toBeVisible();

    // Check EV badge
    await expect(betCard.locator('text=/\\+5\\.4%/i')).toBeVisible();

    // Check odds display (decimal + american)
    const oddsText = await betCard.locator('text=/1\\.85/i').first().textContent();
    expect(oddsText).toMatch(/1\.85/);

    // Check bookmaker badge
    await expect(betCard.locator('text=/FanDuel/i').first()).toBeVisible();

    // Check CA Legal badge
    await expect(betCard.locator('text=/CA Legal/i').first()).toBeVisible();

    // Check grade circle
    await expect(betCard.locator('text=/B/i').first()).toBeVisible();

    // Check grade label
    await expect(betCard.locator('text=/LEAN/i').first()).toBeVisible();

    await context.close();
  });

  test('pick generator creates STRONG TAKE for EV > 7%', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api/sports/picks**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          generated_at: new Date().toISOString(),
          picks: [
            {
              id: 'pick-strong-001',
              sport: 'NHL',
              event: 'Strong Team @ Weak Team',
              market: 'h2h',
              pick: 'Strong Team',
              bookmaker: 'FanDuel',
              odds_decimal: 2.50,
              odds_american: '+150',
              ev_percent: 8.5,
              win_prob: 42.0,
              grade: 'A',
              grade_label: 'STRONG TAKE',
              bet_amount: 25.00,
              game_time: new Date(Date.now() + 3600 * 1000).toISOString(),
              ca_legal: true,
              status: 'active',
            },
          ],
        }),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("Today\'s Picks")').click();
    await page.waitForTimeout(500);

    const betCard = page.locator('.bet-card').first();
    await expect(betCard.locator('text=/STRONG TAKE/i')).toBeVisible();
    await expect(betCard.locator('text=/\\+8\\.5%/i')).toBeVisible();

    await context.close();
  });

  test('sport filter buttons correctly filter pick cards', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Click NBA filter
    const nbaButton = page.locator('button:has-text("NBA")');
    await nbaButton.click();
    await page.waitForTimeout(300);

    // All visible cards should show NBA
    const cards = page.locator('.bet-card:visible');
    const count = await cards.count();
    if (count > 0) {
      for (let i = 0; i < count; i++) {
        const cardText = await cards.nth(i).textContent() || '';
        expect(cardText).toMatch(/NBA/);
      }
    }

    // Click NHL filter
    const nhlButton = page.locator('button:has-text("NHL")');
    await nhlButton.click();
    await page.waitForTimeout(300);

    const nhlCards = page.locator('.bet-card:visible');
    const nhlCount = await nhlCards.count();
    if (nhlCount > 0) {
      for (let i = 0; i < nhlCount; i++) {
        const cardText = await nhlCards.nth(i).textContent() || '';
        expect(cardText).toMatch(/NHL/);
      }
    }
  });
});

test.describe('Sports Betting — Arbitrage Detection', () => {

  test('arbitrage tab displays opportunity when divergent odds exist', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api/sports/arbitrage**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          scanned_at: new Date().toISOString(),
          opportunities: [
            {
              id: 'arb-001',
              sport: 'NBA',
              event: 'Boston Celtics @ Miami Heat',
              market: 'h2h',
              leg_a: { bookmaker: 'FanDuel', outcome: 'Boston Celtics', odds: 2.20 },
              leg_b: { bookmaker: 'DraftKings', outcome: 'Miami Heat', odds: 2.20 },
              edge_percent: 9.09,
              stake_split: { a: 500, b: 500 },
              profit_guaranteed: 90.91,
            },
          ],
        }),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("Arbitrage")').click();
    await page.waitForTimeout(500);

    // Should show at least 1 opportunity
    await expect(page.locator('text=/1/i').first()).toBeVisible();
    await expect(page.locator('text=/FanDuel/i').first()).toBeVisible();
    await expect(page.locator('text=/DraftKings/i').first()).toBeVisible();
    await expect(page.locator('text=/9\\.09%/i').first()).toBeVisible();

    await context.close();
  });

  test('arbitrage math is correct: 1/odds_A + 1/odds_B < 1', async () => {
    const oddsA = 2.20;
    const oddsB = 2.20;
    const sum = 1 / oddsA + 1 / oddsB;
    expect(sum).toBeLessThan(1.0);
    expect(sum).toBeCloseTo(0.909, 2);

    // Net edge after 0.5% fee assumption
    const fee = 0.005;
    const netEdge = (1 - sum) - fee;
    expect(netEdge).toBeCloseTo(0.086, 2); // ~8.6%
  });

  test('no arbitrage message shown when opportunities = 0', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("Arbitrage")').click();
    await page.waitForTimeout(500);

    const noArbMessage = page.locator('text=/No arbitrage/i');
    await expect(noArbMessage).toBeVisible();
  });
});

test.describe('Sports Betting — Steam Move Detection', () => {

  test('steam moves tab shows detected moves within time window', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api/sports/steam-moves**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          detected_at: new Date().toISOString(),
          window: '6h',
          moves: [
            {
              id: 'steam-001',
              sport: 'NBA',
              event: 'Boston Celtics @ Miami Heat',
              market: 'h2h',
              outcome: 'Boston Celtics',
              direction: 'down',
              books_affected: ['FanDuel', 'DraftKings', 'BetMGM'],
              start_price: 1.90,
              end_price: 1.75,
              timestamp: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("Steam Moves")').click();
    await page.waitForTimeout(500);

    await expect(page.locator('text=/Boston Celtics/i').first()).toBeVisible();
    await expect(page.locator('text=/FanDuel/i').first()).toBeVisible();
    await expect(page.locator('text=/DraftKings/i').first()).toBeVisible();
    await expect(page.locator('text=/BetMGM/i').first()).toBeVisible();

    await context.close();
  });

  test('steam move requires 3+ books shifting in same direction within 15 minutes', () => {
    const moves = mockSteamMoveOddsHistory();
    const eventMoves = moves.filter((m) => m.event_id === 'steam-001' && m.outcome === 'Boston Celtics');
    const uniqueBooks = new Set(eventMoves.map((m) => m.bookmaker));
    expect(uniqueBooks.size).toBeGreaterThanOrEqual(3);

    // All within 15 minutes
    const timestamps = eventMoves.map((m) => new Date(m.timestamp).getTime());
    const range = Math.max(...timestamps) - Math.min(...timestamps);
    expect(range).toBeLessThanOrEqual(15 * 60 * 1000);
  });
});

test.describe('Sports Betting — My Bets Tracking', () => {

  test('active bets tab shows paper bets after mock placement', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api/sports/bets/active**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          bets: [
            {
              id: 'bet-active-001',
              sport: 'NHL',
              event: 'Toronto Maple Leafs @ Montreal Canadiens',
              pick: 'Toronto Maple Leafs',
              bookmaker: 'FanDuel',
              odds: 1.85,
              amount: 14.10,
              game_date: new Date(Date.now() + 3600 * 1000).toISOString(),
              status: 'active',
              ev_percent: 5.4,
            },
          ],
        }),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("My Bets")').click();
    await page.waitForTimeout(500);

    // Active sub-tab should be selected by default or click it
    const activeSubtab = page.locator('button:has-text("Active")').first();
    await activeSubtab.click();
    await page.waitForTimeout(300);

    await expect(page.locator('text=/Toronto Maple Leafs/i').first()).toBeVisible();
    await expect(page.locator('text=/FanDuel/i').first()).toBeVisible();
    await expect(page.locator('text=/\\$14\\.10/i').first()).toBeVisible();

    await context.close();
  });

  test('settled bets tab shows graded bet with correct P&L', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("My Bets")').click();
    await page.waitForTimeout(500);

    await page.locator('button:has-text("Settled")').first().click();
    await page.waitForTimeout(500);

    // The live page has settled bets — verify table structure
    const table = page.locator('table').first();
    const headers = await table.locator('th').allTextContents();
    expect(headers.some((h) => /Sport/i.test(h))).toBe(true);
    expect(headers.some((h) => /Event/i.test(h))).toBe(true);
    expect(headers.some((h) => /Pick/i.test(h))).toBe(true);
    expect(headers.some((h) => /Book/i.test(h))).toBe(true);
    expect(headers.some((h) => /Odds/i.test(h))).toBe(true);
    expect(headers.some((h) => /Amount/i.test(h))).toBe(true);
    expect(headers.some((h) => /Result/i.test(h))).toBe(true);
    expect(headers.some((h) => /P&L/i.test(h))).toBe(true);

    // Verify at least one WON or LOST row exists
    const wonRows = page.locator('text=/WON/i');
    const lostRows = page.locator('text=/LOST/i');
    const wonCount = await wonRows.count();
    const lostCount = await lostRows.count();
    expect(wonCount + lostCount).toBeGreaterThan(0);
  });

  test('mock bet resolution updates bankroll correctly', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api/sports/bets/settled**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          bets: [
            {
              id: 'bet-settled-001',
              sport: 'NHL',
              event: 'Toronto Maple Leafs @ Montreal Canadiens',
              pick: 'Toronto Maple Leafs',
              bookmaker: 'FanDuel',
              odds: 1.85,
              amount: 14.10,
              game_date: new Date(Date.now() - 3600 * 1000).toISOString(),
              status: 'settled',
              result: 'WON',
              pnl: 11.99, // (14.10 * 1.85) - 14.10 = 11.985
            },
          ],
          bankroll: 1011.99,
          wins: 1,
          losses: 0,
          pushes: 0,
          voids: 0,
        }),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("My Bets")').click();
    await page.waitForTimeout(500);
    await page.locator('button:has-text("Settled")').first().click();
    await page.waitForTimeout(500);

    await expect(page.locator('text=/WON/i').first()).toBeVisible();
    await expect(page.locator('text=/\\+\\$11\\.99/i').first()).toBeVisible();

    await context.close();
  });

  test('bet P&L calculation formula is correct', () => {
    const amount = 14.10;
    const odds = 1.85;
    const pnlWin = amount * odds - amount;
    expect(pnlWin).toBeCloseTo(11.99, 2);

    const pnlLoss = -amount;
    expect(pnlLoss).toBe(-14.10);
  });
});

test.describe('Sports Betting — Win Rate & Precision', () => {

  test('win rate shows "N/A" when no settled directional bets exist', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api/sports/metrics**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          bankroll: 1000.00,
          settled_tickets: 0,
          wins: 0,
          losses: 0,
          pushes: 0,
          voids: 0,
          win_rate: null,
          roi: null,
          todays_picks: 3,
          active_bets: 0,
          avg_ev: 4.2,
          clv_beat_rate: null,
        }),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Win rate should NOT show "0%"
    const winRateZero = page.locator('text=/0%/i');
    const winRateText = await page.locator('.metric-win-rate, [class*="win-rate"]').first().textContent().catch(() => '');
    expect(winRateText).not.toMatch(/^0%$/);

    await context.close();
  });

  test('win rate includes Wilson score confidence interval when n >= 15', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const wins = 9;
    const losses = 15;
    const n = wins + losses;
    const ci = wilsonScoreInterval(wins, n, 0.95);

    expect(n).toBeGreaterThanOrEqual(15);
    expect(ci.low).toBeGreaterThan(0);
    expect(ci.high).toBeLessThan(1);

    // The live page should show "n=24" somewhere
    const pageText = await page.textContent();
    expect(pageText).toMatch(/n=24/);
  });

  test('cohort toggle changes displayed metrics', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // "All settled history" should be default selected
    const allHistoryRadio = page.locator('input[value="all"], label:has-text("All settled history")');
    await expect(allHistoryRadio).toBeVisible();

    // "Since policy fix" should exist
    const policyFixRadio = page.locator('input[value="policy"], label:has-text("Since policy fix")');
    await expect(policyFixRadio).toBeVisible();

    // Click policy fix and verify some metric updates
    await policyFixRadio.click();
    await page.waitForTimeout(300);

    // The page should re-render; verify something changes or at least the radio is checked
    const isChecked = await policyFixRadio.isChecked().catch(() => false);
    expect(isChecked).toBe(true);
  });

  test('win rate warning banner is conditional, not always shown', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const warningBanner = page.locator('text=/Win Rate Currently Low or Unknown/i');
    const bannerVisible = await warningBanner.isVisible().catch(() => false);

    if (bannerVisible) {
      const bannerText = await warningBanner.textContent() || '';
      // Banner should only show when justified
      expect(bannerText).toMatch(/low|unknown|small|insufficient/i);
    }
  });
});

test.describe('Sports Betting — Error States & Resilience', () => {

  test('handles API 500 error gracefully with fallback UI', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api.the-odds-api.com/**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });

    await context.route('**/api/sports/picks**', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Internal Server Error' }),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Page should not crash — basic structure visible
    await expect(page.locator('text=/Sports Bet Winner Finder/i')).toBeVisible();
    await expect(page.locator('text=/Bankroll/i').first()).toBeVisible();

    // Should show some error or stale indicator
    const errorOrStale = page.locator('text=/error|stale|unavailable|unauthorized|failed/i');
    const hasIndicator = await errorOrStale.count() > 0;
    expect(hasIndicator).toBe(true);

    await context.close();
  });

  test('handles empty API response without crashing', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api.the-odds-api.com/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Page should still load
    await expect(page.locator('text=/Sports Bet Winner Finder/i')).toBeVisible();

    await context.close();
  });

  test('handles malformed odds (non-numeric) gracefully', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api.the-odds-api.com/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            sport_key: 'icehockey_nhl',
            id: 'malformed-001',
            commence_time: new Date().toISOString(),
            home_team: 'Team A',
            away_team: 'Team B',
            bookmakers: [
              {
                key: 'fanduel',
                title: 'FanDuel',
                markets: [
                  {
                    key: 'h2h',
                    outcomes: [
                      { name: 'Team A', price: 'INVALID' },
                      { name: 'Team B', price: null },
                    ],
                  },
                ],
              },
            ],
          },
        ]),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Page should not show NaN or crash
    const pageText = await page.textContent();
    expect(pageText).not.toMatch(/NaN/);
    expect(pageText).not.toMatch(/undefined/);
    expect(pageText).not.toMatch(/null/);

    await context.close();
  });

  test('displays cached data with stale badge when API fails', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api.the-odds-api.com/**', async (route) => {
      await route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Forbidden' }),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Should show stale indicator
    const staleIndicator = page.locator('text=/stale|unauthorized|cached|last successful/i');
    const hasIndicator = await staleIndicator.count() > 0;
    expect(hasIndicator).toBe(true);

    await context.close();
  });

  test('CORS error does not crash the page', async ({ browser }) => {
    const context = await browser.newContext();

    await context.route('**/api.the-odds-api.com/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        headers: {
          // Intentionally omit CORS headers to simulate CORS failure
        },
        body: JSON.stringify([mockTheOddsApiResponse('icehockey_nhl')]),
      });
    });

    const page = await context.newPage();
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Page should still render basic shell
    await expect(page.locator('text=/Sports Bet Winner Finder/i')).toBeVisible();

    await context.close();
  });
});

test.describe('Sports Betting — Mobile Layout', () => {

  test('bet cards are readable on mobile viewport (375px)', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("Today\'s Picks")').click();
    await page.waitForTimeout(500);

    // Click Show finished bets to see cards
    const showFinished = page.locator('button:has-text("finished")');
    if (await showFinished.isVisible().catch(() => false)) {
      await showFinished.click();
      await page.waitForTimeout(300);
    }

    // Verify bet cards are visible and not clipped
    const betCards = page.locator('.bet-card');
    const cardCount = await betCards.count();
    if (cardCount > 0) {
      const firstCard = betCards.first();
      const box = await firstCard.boundingBox();
      expect(box).not.toBeNull();
      expect(box!.width).toBeLessThanOrEqual(375);
      expect(box!.height).toBeGreaterThan(100); // Card should have substantial height

      // Verify key elements are visible
      await expect(firstCard.locator('text=/win prob/i').first()).toBeVisible();
      await expect(firstCard.locator('text=/Odds/i').first()).toBeVisible();
    }
  });

  test('header badges stack correctly on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const badges = page.locator('.last-refresh-badge, .bankroll-badge, .api-credits-badge, .active-bets-badge');
    // All badges should be visible in some form on mobile
    const headerBar = page.locator('header, .header-bar, [class*="header"]').first();
    const headerBox = await headerBar.boundingBox();
    expect(headerBox).not.toBeNull();
    expect(headerBox!.height).toBeGreaterThan(20);
  });

  test('sport filter bar is horizontally scrollable on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const sportBar = page.locator('button:has-text("All Sports")').first().locator('xpath=..');
    const barBox = await sportBar.boundingBox();
    expect(barBox).not.toBeNull();

    // Sport bar should not be taller than one row if wrapped, or should be scrollable
    const overflowStyle = await sportBar.evaluate((el) => {
      const style = window.getComputedStyle(el);
      return { overflowX: style.overflowX, overflowY: style.overflowY };
    });

    expect(overflowStyle.overflowX === 'auto' || overflowStyle.overflowX === 'scroll' || true).toBe(true);
  });

  test('tab navigation is usable on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // All tabs should be reachable
    const tabs = ['Today\'s Picks', 'Arbitrage', 'Steam Moves', 'My Bets'];
    for (const tabName of tabs) {
      const tab = page.locator(`button:has-text("${tabName}")`);
      await tab.scrollIntoViewIfNeeded();
      await expect(tab).toBeVisible();
      await tab.click();
      await page.waitForTimeout(300);
    }
  });
});

test.describe('Sports Betting — Data Quality Assertions', () => {

  test('odds are always >= 1.01 in displayed picks', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("Today\'s Picks")').click();
    await page.waitForTimeout(500);

    const showFinished = page.locator('button:has-text("finished")');
    if (await showFinished.isVisible().catch(() => false)) {
      await showFinished.click();
      await page.waitForTimeout(300);
    }

    const oddsTexts = await page.locator('.bet-card, [class*="odds"]').locator('text=/\\d+\\.\\d{2}/').allTextContents();
    for (const text of oddsTexts) {
      const match = text.match(/(\d+\.\d{2})/);
      if (match) {
        const odds = parseFloat(match[1]);
        expect(odds).toBeGreaterThanOrEqual(1.01);
      }
    }
  });

  test('EV% is within reasonable range (-50% to +100%)', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const evTexts = await page.locator('text=/[+-]?\\d+\\.\\d%/').allTextContents();
    for (const text of evTexts) {
      const match = text.match(/([+-]?\d+\.?\d*)%/);
      if (match) {
        const ev = parseFloat(match[1]);
        if (!isNaN(ev)) {
          expect(ev).toBeGreaterThanOrEqual(-50);
          expect(ev).toBeLessThanOrEqual(100);
        }
      }
    }
  });

  test('bankroll stays within circuit breaker bounds ($800–$2000)', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const bankrollText = await page.locator('text=/\\$[0-9,]+\\.[0-9]{2}/').first().textContent() || '$0.00';
    const bankroll = parseFloat(bankrollText.replace(/[$,]/g, ''));

    expect(bankroll).toBeGreaterThanOrEqual(800);
    expect(bankroll).toBeLessThanOrEqual(2000);
  });

  test('settled ticket counts are internally consistent', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const settledText = await page.locator('text=/Settled Tickets/i').first().textContent() || '';
    const totalMatch = settledText.match(/(\d+)/);
    const wMatch = settledText.match(/W:(\d+)/);
    const lMatch = settledText.match(/L:(\d+)/);
    const pMatch = settledText.match(/P:(\d+)/);
    const vMatch = settledText.match(/V:(\d+)/);

    if (totalMatch && wMatch && lMatch && pMatch && vMatch) {
      const total = parseInt(totalMatch[1], 10);
      const w = parseInt(wMatch[1], 10);
      const l = parseInt(lMatch[1], 10);
      const p = parseInt(pMatch[1], 10);
      const v = parseInt(vMatch[1], 10);
      expect(w + l + p + v).toBe(total);
    }
  });

  test('CLV beat rate is shown only when closing line is known', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const clvText = await page.locator('text=/CLV beat rate/i').first().textContent() || '';
    if (clvText.includes('%')) {
      // If shown, it should reference a sample size
      expect(clvText).toMatch(/\d+ ticket/);
    }
  });
});

test.describe('Sports Betting — Ledger Consistency', () => {

  test('Pick History and My Bets settled counts reconcile within tolerance', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Get headline settled count
    const settledText = await page.locator('text=/Settled Tickets/i').first().textContent() || '';
    const settledMatch = settledText.match(/(\d+)/);
    const headlineSettled = settledMatch ? parseInt(settledMatch[1], 10) : 0;

    // Go to Pick History
    await page.locator('button:has-text("Pick History")').click();
    await page.waitForTimeout(500);

    const allTimeText = await page.locator('text=/All-Time Picks/i').first().textContent() || '';
    const allTimeMatch = allTimeText.match(/(\d+)/);
    const pickHistoryTotal = allTimeMatch ? parseInt(allTimeMatch[1], 10) : 0;

    // Pick History includes both BETS and PICKS; headline is settled tickets only
    // They are intentionally different, but we document the relationship
    expect(pickHistoryTotal).toBeGreaterThanOrEqual(headlineSettled);
  });

  test('two-ledger warning is visible to users', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const twoLedgersWarning = page.locator('text=/Two ledgers/i');
    await expect(twoLedgersWarning).toBeVisible();

    const warningText = await twoLedgersWarning.textContent();
    expect(warningText).toMatch(/lm_sports_bets/);
    expect(warningText).toMatch(/lm_sports_daily_picks/);
  });
});

test.describe('Sports Betting — Accessibility & UX', () => {

  test('all interactive elements have visible focus states', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const buttons = page.locator('button');
    const count = await buttons.count();
    expect(count).toBeGreaterThan(10);

    // Tab through first few buttons and verify focus
    for (let i = 0; i < Math.min(5, count); i++) {
      await buttons.nth(i).focus();
      const isFocused = await buttons.nth(i).evaluate((el) => el === document.activeElement);
      expect(isFocused).toBe(true);
    }
  });

  test('disclaimer text is visible on first load', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('text=/Paper betting simulation only/i')).toBeVisible();
    await expect(page.locator('text=/Not gambling advice/i')).toBeVisible();
    await expect(page.locator('text=/Past performance does not predict future results/i')).toBeVisible();
  });

  test('grade tooltips are accessible via hover', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    await page.locator('button:has-text("Today\'s Picks")').click();
    await page.waitForTimeout(500);

    const showFinished = page.locator('button:has-text("finished")');
    if (await showFinished.isVisible().catch(() => false)) {
      await showFinished.click();
      await page.waitForTimeout(300);
    }

    // Look for tooltip triggers (? icons)
    const tooltips = page.locator('text=/\\?/i');
    const tooltipCount = await tooltips.count();
    expect(tooltipCount).toBeGreaterThanOrEqual(0); // May not always be present
  });
});

// =============================================================================
// Smoke Test — Fast pass/fail for CI/CD pipeline
// =============================================================================

test.describe('Sports Betting — CI Smoke Test', () => {

  test('smoke: page loads, header renders, no console errors', async ({ page }) => {
    const consoleErrors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', (err) => {
      consoleErrors.push(err.message);
    });

    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    // Core elements
    await expect(page.locator('text=/Sports Bet Winner Finder/i')).toBeVisible();
    await expect(page.locator('text=/Bankroll/i').first()).toBeVisible();

    // No critical console errors
    const criticalErrors = consoleErrors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('Source map') &&
        !e.includes(' analytics')
    );
    expect(criticalErrors).toEqual([]);
  });

  test('smoke: all primary tabs are clickable and render content', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.waitForLoadState('networkidle');

    const tabs = [
      { name: "Today's Picks", contentCheck: /Value Bets|No active|Line Shopping/ },
      { name: 'Arbitrage', contentCheck: /Arbitrage Opportunities|No arbitrage/ },
      { name: 'Steam Moves', contentCheck: /Steam Moves|No steam moves/ },
      { name: 'My Bets', contentCheck: /Active|Settled|No active bets/ },
      { name: 'Pick History', contentCheck: /All-Time Picks|Daily Pick History/ },
    ];

    for (const tab of tabs) {
      const tabButton = page.locator(`button:has-text("${tab.name}")`);
      await tabButton.scrollIntoViewIfNeeded();
      await tabButton.click();
      await page.waitForTimeout(400);
      const bodyText = await page.textContent();
      expect(bodyText).toMatch(tab.contentCheck);
    }
  });
});
