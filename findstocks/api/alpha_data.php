<?php
/**
 * Alpha Suite - Read-Only Data API
 * Serves factor scores, picks, regime info, and status to the frontend.
 * No authentication required (read-only).
 * PHP 5.2 compatible.
 *
 * Usage:
 *   ?type=picks                  - Latest picks by strategy
 *   ?type=picks&strategy=X       - Picks for specific strategy
 *   ?type=factors                - Factor scores (latest)
 *   ?type=factors&sort=momentum  - Factor scores sorted by specific factor
 *   ?type=regime                 - Current market regime
 *   ?type=status                 - Last refresh info + timestamps
 *   ?type=universe               - Stock universe
 *   ?type=ticker&symbol=AAPL     - Single ticker deep dive
 *   ?type=history&ticker=AAPL    - Historical factor scores for ticker
 *   ?type=strategies             - Strategy summary
 */
require_once dirname(__FILE__) . '/db_connect.php';

$type   = isset($_GET['type']) ? $_GET['type'] : 'status';
$result = array('ok' => true, 'type' => $type, 'data' => array());

/* ─── STATUS ─── */
if ($type === 'status') {
    $sq = $conn->query("SELECT * FROM alpha_status WHERE id=1");
    if ($sq && $row = $sq->fetch_assoc()) {
        $result['data']['status'] = $row;
        if (isset($row['summary_json']) && $row['summary_json'] !== '') {
            $result['data']['summary'] = json_decode($row['summary_json'], true);
        }
    }

    // Counts
    $counts = array();
    $tables = array(
        'universe' => "SELECT COUNT(*) as c FROM alpha_universe WHERE active=1",
        'fundamentals' => "SELECT COUNT(*) as c FROM alpha_fundamentals",
        'earnings' => "SELECT COUNT(*) as c FROM alpha_earnings",
        'macro_days' => "SELECT COUNT(*) as c FROM alpha_macro",
        'factor_scores' => "SELECT COUNT(*) as c FROM alpha_factor_scores",
        'total_picks' => "SELECT COUNT(*) as c FROM alpha_picks"
    );
    foreach ($tables as $k => $sql) {
        $q = $conn->query($sql);
        if ($q && $row = $q->fetch_assoc()) {
            $counts[$k] = (int)$row['c'];
        } else {
            $counts[$k] = 0;
        }
    }
    $result['data']['counts'] = $counts;

    // Latest dates
    $dates = array();
    $dq = array(
        'last_fundamentals' => "SELECT MAX(fetch_date) as d FROM alpha_fundamentals",
        'last_earnings' => "SELECT MAX(fetch_date) as d FROM alpha_earnings",
        'last_macro' => "SELECT MAX(trade_date) as d FROM alpha_macro",
        'last_factors' => "SELECT MAX(score_date) as d FROM alpha_factor_scores",
        'last_picks' => "SELECT MAX(pick_date) as d FROM alpha_picks"
    );
    foreach ($dq as $k => $sql) {
        $q = $conn->query($sql);
        if ($q && $row = $q->fetch_assoc()) {
            $dates[$k] = $row['d'];
        } else {
            $dates[$k] = null;
        }
    }
    $result['data']['latest_dates'] = $dates;
}

/* ─── PICKS ─── */
if ($type === 'picks') {
    $strategy = isset($_GET['strategy']) ? $_GET['strategy'] : '';
    $where = "WHERE pick_date = (SELECT MAX(pick_date) FROM alpha_picks)";
    if ($strategy !== '') {
        $safe_strat = $conn->real_escape_string($strategy);
        $where .= " AND strategy='$safe_strat'";
    }

    $q = $conn->query("SELECT p.*, u.company_name, u.sector, u.industry
                       FROM alpha_picks p
                       LEFT JOIN alpha_universe u ON p.ticker = u.ticker
                       $where ORDER BY p.score DESC");
    $picks = array();
    if ($q) {
        while ($row = $q->fetch_assoc()) {
            $picks[] = $row;
        }
    }
    $result['data']['picks'] = $picks;
    $result['data']['count'] = count($picks);

    // Strategy list
    $sq = $conn->query("SELECT DISTINCT strategy, COUNT(*) as cnt FROM alpha_picks WHERE pick_date = (SELECT MAX(pick_date) FROM alpha_picks) GROUP BY strategy ORDER BY strategy");
    $strats = array();
    if ($sq) {
        while ($row = $sq->fetch_assoc()) {
            $strats[] = $row;
        }
    }
    $result['data']['strategies'] = $strats;
}

/* ─── FACTORS ─── */
if ($type === 'factors') {
    $sort = isset($_GET['sort']) ? $_GET['sort'] : 'composite';
    $order_col = 'composite_rank';
    $sort_map = array(
        'momentum' => 'momentum_score DESC',
        'quality' => 'quality_score DESC',
        'value' => 'value_score DESC',
        'earnings' => 'earnings_score DESC',
        'volatility' => 'vol_score DESC',
        'growth' => 'growth_score DESC',
        'composite' => 'composite_score DESC',
        'regime' => 'regime_adj_score DESC'
    );
    $order = isset($sort_map[$sort]) ? $sort_map[$sort] : 'composite_score DESC';

    $q = $conn->query("SELECT f.*, u.company_name, u.sector
                       FROM alpha_factor_scores f
                       LEFT JOIN alpha_universe u ON f.ticker = u.ticker
                       WHERE f.score_date = (SELECT MAX(score_date) FROM alpha_factor_scores)
                       ORDER BY $order");
    $factors = array();
    if ($q) {
        while ($row = $q->fetch_assoc()) {
            $factors[] = $row;
        }
    }
    $result['data']['factors'] = $factors;
    $result['data']['sort'] = $sort;
    $result['data']['count'] = count($factors);
}

/* ─── REGIME ─── */
if ($type === 'regime') {
    // Latest regime
    $q = $conn->query("SELECT * FROM alpha_macro ORDER BY trade_date DESC LIMIT 1");
    if ($q && $row = $q->fetch_assoc()) {
        $result['data']['current'] = $row;
    }

    // Regime history (last 30 days)
    $hq = $conn->query("SELECT trade_date, vix_close, spy_close, tnx_close, yield_spread, dxy_close, regime, regime_score
                        FROM alpha_macro ORDER BY trade_date DESC LIMIT 30");
    $history = array();
    if ($hq) {
        while ($row = $hq->fetch_assoc()) {
            $history[] = $row;
        }
    }
    $result['data']['history'] = $history;
}

/* ─── UNIVERSE ─── */
if ($type === 'universe') {
    $q = $conn->query("SELECT u.*, f.regular_market_price, f.market_cap, f.pe_trailing, f.dividend_yield
                       FROM alpha_universe u
                       LEFT JOIN alpha_fundamentals f ON u.ticker = f.ticker
                           AND f.fetch_date = (SELECT MAX(fetch_date) FROM alpha_fundamentals WHERE ticker = u.ticker)
                       WHERE u.active=1
                       ORDER BY u.sector, u.ticker");
    $stocks = array();
    if ($q) {
        while ($row = $q->fetch_assoc()) {
            $stocks[] = $row;
        }
    }
    $result['data']['universe'] = $stocks;
    $result['data']['count'] = count($stocks);

    // Sector breakdown
    $sq = $conn->query("SELECT sector, COUNT(*) as cnt FROM alpha_universe WHERE active=1 GROUP BY sector ORDER BY cnt DESC");
    $sectors = array();
    if ($sq) {
        while ($row = $sq->fetch_assoc()) {
            $sectors[] = $row;
        }
    }
    $result['data']['sectors'] = $sectors;
}

/* ─── SINGLE TICKER ─── */
if ($type === 'ticker') {
    $symbol = isset($_GET['symbol']) ? $_GET['symbol'] : '';
    if ($symbol === '') {
        $result['ok'] = false;
        $result['error'] = 'symbol parameter required';
    } else {
        $st = $conn->real_escape_string($symbol);

        // Universe info
        $q = $conn->query("SELECT * FROM alpha_universe WHERE ticker='$st'");
        if ($q && $row = $q->fetch_assoc()) $result['data']['info'] = $row;

        // Latest fundamentals
        $q = $conn->query("SELECT * FROM alpha_fundamentals WHERE ticker='$st' ORDER BY fetch_date DESC LIMIT 1");
        if ($q && $row = $q->fetch_assoc()) $result['data']['fundamentals'] = $row;

        // Earnings history
        $q = $conn->query("SELECT * FROM alpha_earnings WHERE ticker='$st' ORDER BY quarter_end DESC LIMIT 8");
        $earnings = array();
        if ($q) { while ($row = $q->fetch_assoc()) $earnings[] = $row; }
        $result['data']['earnings'] = $earnings;

        // Latest factor scores
        $q = $conn->query("SELECT * FROM alpha_factor_scores WHERE ticker='$st' ORDER BY score_date DESC LIMIT 1");
        if ($q && $row = $q->fetch_assoc()) $result['data']['factors'] = $row;

        // Recent picks for this ticker
        $q = $conn->query("SELECT * FROM alpha_picks WHERE ticker='$st' ORDER BY pick_date DESC LIMIT 20");
        $picks = array();
        if ($q) { while ($row = $q->fetch_assoc()) $picks[] = $row; }
        $result['data']['picks'] = $picks;

        // Recent prices
        $q = $conn->query("SELECT trade_date, close_price, volume FROM daily_prices WHERE ticker='$st' ORDER BY trade_date DESC LIMIT 60");
        $prices = array();
        if ($q) { while ($row = $q->fetch_assoc()) $prices[] = $row; }
        $result['data']['prices'] = $prices;
    }
}

/* ─── STRATEGIES SUMMARY ─── */
if ($type === 'strategies') {
    $q = $conn->query("SELECT strategy,
                              COUNT(*) as pick_count,
                              AVG(score) as avg_score,
                              MAX(pick_date) as last_pick_date
                       FROM alpha_picks
                       GROUP BY strategy
                       ORDER BY strategy");
    $strats = array();
    if ($q) {
        while ($row = $q->fetch_assoc()) {
            $strats[] = $row;
        }
    }
    $result['data']['strategies'] = $strats;
}

echo json_encode($result);
$conn->close();
?>
