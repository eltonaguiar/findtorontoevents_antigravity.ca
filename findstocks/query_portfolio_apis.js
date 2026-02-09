/**
 * Query stock portfolio APIs and output structured report.
 * Run: node findstocks/query_portfolio_apis.js
 */
const https = require('https');

function fetchJson(url, timeoutMs) {
  timeoutMs = timeoutMs || 15000;
  return new Promise((resolve, reject) => {
    const req = https.get(url, { timeout: timeoutMs }, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          reject(new Error('Invalid JSON: ' + e.message));
        }
      });
    });
    req.on('error', reject);
    req.on('timeout', () => { req.destroy(); reject(new Error('Timeout')); });
    req.setTimeout(timeoutMs);
  });
}

async function main() {
  const base = 'https://findtorontoevents.ca/findstocks/api';

  // 1. Backtest
  const backtestUrl = base + '/backtest.php?take_profit=999&stop_loss=999&max_hold_days=999&fee_model=zero';
  let backtest;
  try {
    backtest = await fetchJson(backtestUrl, 60000);
  } catch (e) {
    console.error('Backtest fetch failed:', e.message);
    backtest = null;
  }

  const out = {
    backtest: null,
    optimal_finder_top25_sharpe: null,
    optimal_finder_blue_chip_top5_return: null
  };

  if (backtest && backtest.ok && Array.isArray(backtest.trades)) {
    const trades = backtest.trades;
    const byAlgo = {};
    const byTicker = {};
    for (const t of trades) {
      const algo = t.algorithm || t.algorithm_name || '(unknown)';
      if (!byAlgo[algo]) byAlgo[algo] = { total: 0, wins: 0, losses: 0 };
      byAlgo[algo].total++;
      if ((t.return_pct || 0) > 0) byAlgo[algo].wins++;
      else byAlgo[algo].losses++;

      const ticker = t.ticker || '';
      if (!ticker) continue;
      if (!byTicker[ticker]) byTicker[ticker] = { count: 0, sumReturn: 0 };
      byTicker[ticker].count++;
      byTicker[ticker].sumReturn += Number(t.return_pct) || 0;
    }

    const algoTable = Object.entries(byAlgo).map(([name, v]) => ({
      algorithm_name: name,
      total_trades: v.total,
      winning_trades: v.wins,
      losing_trades: v.losses
    }));

    const tickerTable = Object.entries(byTicker).map(([t, v]) => ({
      ticker: t,
      count: v.count,
      avg_return_pct: v.count ? Math.round((v.sumReturn / v.count) * 10000) / 10000 : 0
    }));

    const sortedByCount = [...tickerTable].sort((a, b) => b.count - a.count);
    const top20Tickers = sortedByCount.slice(0, 20).map((x) => ({
      ticker: x.ticker,
      pick_count: x.count,
      avg_return_pct: x.avg_return_pct
    }));

    out.backtest = {
      summary_from_api: backtest.summary,
      params: backtest.params,
      by_algorithm: algoTable,
      by_ticker: tickerTable,
      top_20_most_picked_tickers: top20Tickers
    };
  }

  // 2. Optimal finder — top 25 by Sharpe
  try {
    const of1 = await fetchJson(base + '/optimal_finder.php?quick=1&top=25&sort_by=sharpe_ratio', 120000);
    out.optimal_finder_top25_sharpe = of1;
  } catch (e) {
    out.optimal_finder_top25_sharpe = { error: e.message };
  }

  // 3. Optimal finder — Blue Chip Growth, top 5 by total return
  try {
    const of2 = await fetchJson(
      base + '/optimal_finder.php?algorithms=Blue%20Chip%20Growth&quick=1&top=5&sort_by=total_return_pct',
      120000
    );
    out.optimal_finder_blue_chip_top5_return = of2;
  } catch (e) {
    out.optimal_finder_blue_chip_top5_return = { error: e.message };
  }

  console.log(JSON.stringify(out, null, 2));
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
