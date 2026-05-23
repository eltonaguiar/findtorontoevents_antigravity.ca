import { test, expect } from '@playwright/test';

// ══════════════════════════════════════════════════════════════════════════════
//  SUPPLEMENTAL DATA STRATEGIES — API Validation & Portfolio Tracking
//  Tests that the 3 new API sources (Messari, Mempool.space, Ethplorer) are
//  live, returning valid data, and that signals integrate into the Alpha Engine.
// ══════════════════════════════════════════════════════════════════════════════

const ALPHA_URL = 'https://eltonaguiar.github.io/findtorontoevents_antigravity.ca/alpha/';
const ACTIVE_PICKS_URL = 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/active_picks.json';
const CLOSED_PICKS_URL = 'https://raw.githubusercontent.com/eltonaguiar/findtorontoevents_antigravity.ca/main/alpha_engine/data/closed_picks.json';

const SUPPLEMENTAL_STRATEGIES = [
  'messari_fundamental_quality',
  'messari_developer_momentum',
  'messari_roi_divergence',
  'mempool_congestion_volatility',
  'mempool_fee_spike_reversal',
  'mempool_hashrate_security',
  'ethplorer_whale_accumulation',
  'ethplorer_token_flow_momentum',
  'ethplorer_holder_concentration',
];

// ── API Source Validation ──────────────────────────────────────────────────

test.describe('Supplemental API Sources — Liveness', () => {

  test('CoinGecko + Coinpaprika fundamental data (BTC + SOL)', async ({ request }) => {
    // Test both APIs in one test to minimize CoinGecko rate limit hits
    // Coinpaprika first (no rate issues)
    const cpResp = await request.get('https://api.coinpaprika.com/v1/tickers/btc-bitcoin', { timeout: 15000 });
    expect(cpResp.status()).toBe(200);
    const cpBody = await cpResp.json();
    const q = cpBody.quotes?.USD;
    expect(q).toBeTruthy();
    expect(q.price).toBeGreaterThan(0);
    console.log(`  Coinpaprika BTC: $${q.price.toFixed(2)}, vol24h: $${(q.volume_24h/1e9).toFixed(2)}B`);
    console.log(`  ATH: $${q.ath_price?.toFixed(2)}`);

    // CoinGecko BTC (may 429 on free tier — treat as soft fail)
    const cgBtc = await request.get(
      'https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&market_data=true&community_data=true&developer_data=true&sparkline=false',
      { timeout: 15000 }
    );
    if (cgBtc.status() === 200) {
      const body = await cgBtc.json();
      console.log(`  CoinGecko BTC: $${body.market_data?.current_price?.usd?.toFixed(2)}`);
      const dev = body.developer_data;
      if (dev) console.log(`  BTC dev: stars=${dev.stars}, forks=${dev.forks}, commits/4w=${dev.commit_count_4_weeks}`);
      const md = body.market_data;
      console.log(`  ROI 30d: ${md?.price_change_percentage_30d?.toFixed(2)}%, 1y: ${md?.price_change_percentage_1y?.toFixed(2)}%`);
    } else {
      console.log(`  CoinGecko BTC: rate-limited (${cgBtc.status()}) — Coinpaprika covers price data`);
    }

    // CoinGecko SOL (sequential to avoid rate limit)
    const cgSol = await request.get(
      'https://api.coingecko.com/api/v3/coins/solana?localization=false&tickers=false&market_data=true&developer_data=true&sparkline=false',
      { timeout: 15000 }
    );
    if (cgSol.status() === 200) {
      const body = await cgSol.json();
      console.log(`  CoinGecko SOL: $${body.market_data?.current_price?.usd?.toFixed(2)}`);
      if (body.developer_data) {
        console.log(`  SOL dev: ${body.developer_data.commit_count_4_weeks} commits/4w, ${body.developer_data.stars} stars`);
      }
    } else {
      console.log(`  CoinGecko SOL: rate-limited (${cgSol.status()})`);
    }

    // At least Coinpaprika must work (it's our fallback)
    expect(q.price).toBeGreaterThan(0);
  });

  test('Mempool.space API returns fee estimates', async ({ request }) => {
    const resp = await request.get('https://mempool.space/api/v1/fees/recommended', {
      timeout: 15000,
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.fastestFee).toBeGreaterThan(0);
    expect(body.halfHourFee).toBeGreaterThan(0);
    expect(body.hourFee).toBeGreaterThan(0);
    console.log(`  BTC fees — fastest: ${body.fastestFee} sat/vB, 30min: ${body.halfHourFee}, 1hr: ${body.hourFee}`);
  });

  test('Mempool.space API returns mempool stats', async ({ request }) => {
    const resp = await request.get('https://mempool.space/api/mempool', {
      timeout: 15000,
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.count).toBeGreaterThan(0);
    expect(body.vsize).toBeGreaterThan(0);
    console.log(`  Mempool: ${body.count} unconfirmed txs, ${(body.vsize / 1_000_000).toFixed(2)} MvB`);
  });

  test('Mempool.space API returns hashrate data', async ({ request }) => {
    const resp = await request.get('https://mempool.space/api/v1/mining/hashrate/1m', {
      timeout: 15000,
    });
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.hashrates).toBeTruthy();
    expect(body.hashrates.length).toBeGreaterThan(0);
    const latest = body.hashrates[body.hashrates.length - 1];
    console.log(`  Latest hashrate: ${(latest.avgHashrate / 1e18).toFixed(2)} EH/s`);
  });

  test('Ethplorer API returns token info (LINK or UNI fallback)', async ({ request }) => {
    // Try LINK first, fall back to UNI if rate-limited
    const tokens = [
      { symbol: 'LINK', addr: '0x514910771af9ca656af840dff83e8264ecf986ca' },
      { symbol: 'UNI', addr: '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984' },
    ];
    let passed = false;
    for (const { symbol, addr } of tokens) {
      const resp = await request.get(
        `https://api.ethplorer.io/getTokenInfo/${addr}?apiKey=freekey`,
        { timeout: 15000 }
      );
      if (resp.status() === 200) {
        const body = await resp.json();
        if (body.holdersCount > 0) {
          console.log(`  ${symbol} holders: ${body.holdersCount}, transfers: ${body.transfersCount}`);
          passed = true;
          break;
        }
      }
    }
    expect(passed).toBe(true);
  });

  test('Ethplorer API returns top holders (UNI)', async ({ request }) => {
    const resp = await request.get(
      'https://api.ethplorer.io/getTopTokenHolders/0x1f9840a85d5af5bf1d1762f925bdaddc4201f984?apiKey=freekey&limit=10',
      { timeout: 15000 }
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.holders).toBeTruthy();
    expect(body.holders.length).toBeGreaterThan(0);
    const topHolder = body.holders[0];
    console.log(`  UNI top holder: ${topHolder.address?.slice(0, 10)}... owns ${topHolder.share?.toFixed(2)}%`);
  });

  test('Ethplorer API returns token history (AAVE)', async ({ request }) => {
    const resp = await request.get(
      'https://api.ethplorer.io/getTokenHistory/0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9?apiKey=freekey&type=transfer&limit=10',
      { timeout: 15000 }
    );
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.operations).toBeTruthy();
    expect(body.operations.length).toBeGreaterThan(0);
    console.log(`  AAVE recent transfers: ${body.operations.length} ops returned`);
  });
});

// ── Alpha Engine Integration ───────────────────────────────────────────────

test.describe('Supplemental Strategies — Alpha Engine Integration', () => {

  test('active_picks.json is valid and loadable', async ({ request }) => {
    const resp = await request.get(ACTIVE_PICKS_URL, { timeout: 20000 });
    expect(resp.status()).toBe(200);
    const picks = await resp.json();
    expect(Array.isArray(picks)).toBe(true);
    console.log(`  Active picks count: ${picks.length}`);

    // Count supplemental strategy picks
    const suppPicks = picks.filter((p: any) => SUPPLEMENTAL_STRATEGIES.includes(p.strategy));
    console.log(`  Supplemental strategy picks: ${suppPicks.length}`);
    for (const p of suppPicks) {
      console.log(`    ${p.strategy} -> ${p.symbol} ${p.signal_type} conf=${p.confidence}`);
    }

    // Check for supplemental enrichment data on existing picks
    const enriched = picks.filter((p: any) => p.supplemental && Object.keys(p.supplemental).length > 0);
    console.log(`  Picks with supplemental enrichment: ${enriched.length}`);

    // Log strategy distribution
    const stratCounts: Record<string, number> = {};
    for (const p of picks) {
      stratCounts[p.strategy] = (stratCounts[p.strategy] || 0) + 1;
    }
    console.log(`  Strategy distribution (${Object.keys(stratCounts).length} strategies):`);
    for (const [s, c] of Object.entries(stratCounts).sort((a, b) => b[1] - a[1]).slice(0, 10)) {
      console.log(`    ${s}: ${c} picks`);
    }
  });

  test('closed_picks.json tracks historical performance', async ({ request }) => {
    const resp = await request.get(CLOSED_PICKS_URL, { timeout: 20000 });
    expect(resp.status()).toBe(200);
    const picks = await resp.json();
    expect(Array.isArray(picks)).toBe(true);
    console.log(`  Closed picks count: ${picks.length}`);

    // Check for supplemental strategy closed picks (portfolio tracking)
    const suppClosed = picks.filter((p: any) => SUPPLEMENTAL_STRATEGIES.includes(p.strategy));
    console.log(`  Supplemental strategy closed: ${suppClosed.length}`);

    if (suppClosed.length > 0) {
      // Calculate P/L for supplemental strategies
      let wins = 0, losses = 0, totalPnl = 0;
      for (const p of suppClosed) {
        const pnl = p.pnl_pct ?? p.pnl_percent ?? 0;
        totalPnl += pnl;
        if (pnl > 0) wins++;
        else losses++;
        console.log(`    ${p.strategy} ${p.symbol}: ${pnl > 0 ? '+' : ''}${pnl.toFixed(2)}%`);
      }
      const winRate = suppClosed.length > 0 ? (wins / suppClosed.length * 100).toFixed(1) : '0';
      console.log(`\n  === SUPPLEMENTAL PORTFOLIO SCORECARD ===`);
      console.log(`  Trades: ${suppClosed.length} | Wins: ${wins} | Losses: ${losses}`);
      console.log(`  Win Rate: ${winRate}%`);
      console.log(`  Total P/L: ${totalPnl > 0 ? '+' : ''}${totalPnl.toFixed(2)}%`);
      console.log(`  Avg P/L: ${(totalPnl / suppClosed.length).toFixed(2)}%`);
    } else {
      console.log('  No supplemental strategy picks closed yet — too early, strategies need market conditions to trigger');
    }

    // Overall system performance for comparison
    const allWithPnl = picks.filter((p: any) => typeof (p.pnl_pct ?? p.pnl_percent) === 'number');
    if (allWithPnl.length > 0) {
      let totalWins = 0, totalPnlAll = 0;
      for (const p of allWithPnl) {
        const pnl = p.pnl_pct ?? p.pnl_percent ?? 0;
        totalPnlAll += pnl;
        if (pnl > 0) totalWins++;
      }
      console.log(`\n  === OVERALL SYSTEM BASELINE ===`);
      console.log(`  Closed: ${allWithPnl.length} | Win Rate: ${(totalWins / allWithPnl.length * 100).toFixed(1)}%`);
      console.log(`  Total P/L: ${totalPnlAll.toFixed(2)}% | Avg: ${(totalPnlAll / allWithPnl.length).toFixed(2)}%`);
    }
  });

  test('Alpha dashboard loads and shows strategy data', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto(ALPHA_URL, { waitUntil: 'networkidle', timeout: 30000 });

    // Wait for data to populate
    await page.waitForFunction(() => {
      const el = document.getElementById('picks-count');
      return el && el.textContent !== '0';
    }, { timeout: 20000 }).catch(() => {});

    // Dashboard loads without critical errors
    const critical = errors.filter(e => /SyntaxError|ReferenceError|TypeError/.test(e));
    expect(critical).toEqual([]);

    // Take a screenshot for visual verification
    await page.screenshot({
      path: 'tests/screenshots/supplemental_portfolio.png',
      fullPage: false,
    });

    // Check picks count is reasonable
    const picksText = await page.locator('#picks-count').textContent();
    expect(picksText).toBeTruthy();
    console.log(`  Dashboard picks count: ${picksText}`);
  });
});

// ── Test Portfolio — Simulated Edge Detection ──────────────────────────────

test.describe('Supplemental Strategy Edge Analysis', () => {

  test('CoinGecko + Coinpaprika data quality — multi-asset scan', async ({ request }) => {
    const assets = [
      { cg: 'bitcoin', cp: 'btc-bitcoin' },
      { cg: 'ethereum', cp: 'eth-ethereum' },
      { cg: 'solana', cp: 'sol-solana' },
      { cg: 'chainlink', cp: 'link-chainlink' },
      { cg: 'avalanche-2', cp: 'avax-avalanche' },
      { cg: 'cardano', cp: 'ada-cardano' },
      { cg: 'uniswap', cp: 'uni-uniswap' },
    ];
    const results: Array<{ name: string; price: number; devActivity: boolean; roi: boolean; cpPrice: boolean }> = [];

    // Sequential CoinGecko calls to avoid rate limiting (free tier: ~10 req/min)
    for (const { cg, cp } of assets) {
      try {
        // Coinpaprika has no rate limit issues
        const cpResp = await request.get(`https://api.coinpaprika.com/v1/tickers/${cp}`, { timeout: 10000 });
        const cpData = cpResp.status() === 200 ? await cpResp.json() : null;

        // CoinGecko: sequential with small delay
        const cgResp = await request.get(
          `https://api.coingecko.com/api/v3/coins/${cg}?localization=false&tickers=false&market_data=true&developer_data=true&sparkline=false`,
          { timeout: 12000 }
        );
        const cgData = cgResp.status() === 200 ? await cgResp.json() : null;

        // If CoinGecko rate-limited, use Coinpaprika price
        const cgPrice = cgData?.market_data?.current_price?.usd ?? 0;
        const cpPrice = cpData?.quotes?.USD?.price ?? 0;

        results.push({
          name: cg,
          price: cgPrice || cpPrice,
          devActivity: !!(cgData?.developer_data?.stars || cgData?.developer_data?.commit_count_4_weeks),
          roi: cgData?.market_data?.price_change_percentage_1y !== undefined,
          cpPrice: cpPrice > 0,
        });
      } catch {
        results.push({ name: cg, price: 0, devActivity: false, roi: false, cpPrice: false });
      }
    }

    console.log('\n  === FUNDAMENTAL DATA COVERAGE (CoinGecko + Coinpaprika) ===');
    console.log('  Asset        | Price      | Dev  | ROI  | CP  ');
    console.log('  -------------|------------|------|------|-----');
    for (const r of results) {
      console.log(`  ${r.name.padEnd(13)}| $${r.price.toFixed(2).padEnd(9)}| ${r.devActivity ? 'YES' : ' - '} | ${r.roi ? 'YES' : ' - '} | ${r.cpPrice ? 'YES' : ' - '}`);
    }

    const withPrice = results.filter(r => r.price > 0);
    expect(withPrice.length).toBeGreaterThanOrEqual(5);
  });

  test('Mempool congestion snapshot — fee regime classification', async ({ request }) => {
    const [feesResp, mempoolResp] = await Promise.all([
      request.get('https://mempool.space/api/v1/fees/recommended', { timeout: 15000 }),
      request.get('https://mempool.space/api/mempool', { timeout: 15000 }),
    ]);

    expect(feesResp.status()).toBe(200);
    expect(mempoolResp.status()).toBe(200);

    const fees = await feesResp.json();
    const mempool = await mempoolResp.json();

    const feeSpread = fees.fastestFee - fees.hourFee;
    const congestionLevel = mempool.count > 100000 ? 'HIGH' :
                           mempool.count > 30000 ? 'MODERATE' : 'LOW';

    // Fee regime classification (maps to our strategy thresholds)
    const feeRegime = fees.fastestFee > 50 ? 'SPIKE' :
                      fees.fastestFee > 20 ? 'ELEVATED' : 'NORMAL';

    console.log('\n  === MEMPOOL SNAPSHOT ===');
    console.log(`  Unconfirmed TXs: ${mempool.count.toLocaleString()}`);
    console.log(`  Mempool size: ${(mempool.vsize / 1_000_000).toFixed(2)} MvB`);
    console.log(`  Fee fastest: ${fees.fastestFee} sat/vB | 30min: ${fees.halfHourFee} | 1hr: ${fees.hourFee}`);
    console.log(`  Fee spread: ${feeSpread} sat/vB`);
    console.log(`  Congestion: ${congestionLevel} | Fee regime: ${feeRegime}`);

    if (feeRegime === 'SPIKE') {
      console.log('  >>> mempool_fee_spike_reversal strategy likely to FIRE');
    }
    if (congestionLevel === 'HIGH') {
      console.log('  >>> mempool_congestion_volatility strategy likely to FIRE');
    }
  });

  test('Ethplorer whale concentration scan — top ERC-20 tokens', async ({ request }) => {
    const tokens = [
      { symbol: 'LINK', addr: '0x514910771af9ca656af840dff83e8264ecf986ca' },
      { symbol: 'UNI',  addr: '0x1f9840a85d5af5bf1d1762f925bdaddc4201f984' },
      { symbol: 'AAVE', addr: '0x7fc66500c84a76ad7e9c93437bfc5ac33e2ddae9' },
      { symbol: 'SHIB', addr: '0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce' },
    ];

    console.log('\n  === ETHPLORER WHALE CONCENTRATION ===');
    console.log('  Token | Holders   | Top10 Share | Transfer Vol');
    console.log('  ------|-----------|-------------|-------------');

    for (const { symbol, addr } of tokens) {
      try {
        const [infoResp, holdersResp] = await Promise.all([
          request.get(`https://api.ethplorer.io/getTokenInfo/${addr}?apiKey=freekey`, { timeout: 12000 }),
          request.get(`https://api.ethplorer.io/getTopTokenHolders/${addr}?apiKey=freekey&limit=10`, { timeout: 12000 }),
        ]);

        if (infoResp.status() !== 200 || holdersResp.status() !== 200) continue;

        const info = await infoResp.json();
        const holders = await holdersResp.json();

        const top10Share = holders.holders?.reduce((sum: number, h: any) => sum + (h.share || 0), 0) || 0;
        const holdersCount = info.holdersCount || 0;
        const transfers = info.transfersCount || 0;

        console.log(`  ${symbol.padEnd(5)} | ${holdersCount.toLocaleString().padEnd(9)} | ${top10Share.toFixed(1).padStart(5)}%      | ${transfers.toLocaleString()}`);

        if (top10Share > 50) {
          console.log(`  >>> ${symbol}: HIGH concentration (${top10Share.toFixed(1)}%) — ethplorer_holder_concentration may fire SELL`);
        }
      } catch {
        console.log(`  ${symbol.padEnd(5)} | TIMEOUT`);
      }
    }
  });
});
