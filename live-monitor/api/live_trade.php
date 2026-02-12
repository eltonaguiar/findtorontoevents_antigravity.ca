<?php
/**
 * Paper Trading Engine for Live Trading Monitor
 * PHP 5.2 compatible — no short arrays, no http_response_code(), no spread operator
 *
 * Actions:
 *   enter      — open a new position (admin key required)
 *   track      — update all open positions, check exits (admin key required)
 *   close      — manually close a position (admin key required)
 *   positions  — list positions (public)
 *   dashboard  — overall stats (public)
 *   history    — paginated trade history (public)
 */

require_once dirname(__FILE__) . '/db_connect.php';

// ─── Constants ───────────────────────────────────────────────────────
$ADMIN_KEY            = 'livetrader2026';
$INITIAL_CAPITAL      = 10000;
$MAX_POSITIONS        = 10;
$DEFAULT_POSITION_PCT = 5;   // 5% base — adjusted by volatility (Kimi: dynamic sizing)
$MIN_POSITION_PCT     = 3;   // Floor: never smaller than 3%
$MAX_POSITION_PCT     = 7;   // Ceiling: never larger than 7%
$TRAILING_ACTIVATE    = 0.50; // Activate trailing stop at 50% of TP reached
$TRAILING_FACTOR      = 0.60; // Trail at 60% of SL below highest_price (tighter than original SL)

// ─── Per-asset-class position limits (Feb 11, 2026) ─────────────────
// Reduces concentration: crypto max 5, stock max 5, forex max 3
$MAX_POSITIONS_PER_ASSET = array(
    'CRYPTO' => 5,
    'STOCK'  => 5,
    'FOREX'  => 3
);

// ─── Crypto execution optimization (Feb 11, 2026) ──────────────────
// Only these algorithms are allowed to open crypto paper trades.
// Based on Goldmine tracker proven win rates:
//   Momentum Burst (100%), Alpha Predator (87%), StochRSI Crossover (81%),
//   Ichimoku Cloud (80%), RSI(2) Scalp (75%)
// All other crypto algorithms have < 70% WR and are excluded from execution.
$CRYPTO_PREFERRED_ALGOS = array(
    'Momentum Burst',
    'Alpha Predator',
    'StochRSI Crossover',
    'Ichimoku Cloud',
    'RSI(2) Scalp'
);

// ─── Crypto TP floor (Feb 11, 2026) ────────────────────────────────
// Crypto signals often have TP too tight after regime scaling.
// Minimum 3% TP for crypto to allow natural price movement.
$CRYPTO_MIN_TP_PCT = 3.0;

// ─── Per-asset R:R minimum (Feb 12, 2026) ─────────────────────────
// Stocks/Forex have tighter natural moves than crypto.
// At 80% WR you only need R:R > 0.25, at 60% WR you need > 0.67.
// Our top algos run 75-85% WR, so lower R:R is safe for proven algos.
$MIN_RR_RATIO = array(
    'CRYPTO' => 1.5,  // Crypto: wider swings, keep strict
    'STOCK'  => 1.2,  // Stocks: tighter moves, was blocking at 1.36
    'FOREX'  => 1.0   // Forex: tight spreads, low R:R is normal
);

// ─── Max hold cap (Feb 12, 2026) ──────────────────────────────────
// Prevents any algorithm from holding >72h. Challenger Bot was using
// 168h (7 days), blocking 4 of 10 position slots for a full week.
$MAX_HOLD_CAP = array(
    'CRYPTO' => 24,   // Crypto: 24/7 market, fast moves
    'STOCK'  => 72,   // Stocks: max 3 trading days
    'FOREX'  => 48    // Forex: max 2 days
);

// ─── Sector/Group mapping for correlation guard ─────────────────────
// Prevents over-concentration: max 2 positions per sector group
$SECTOR_GROUPS = array(
    // Tech mega-caps (highly correlated)
    'AAPL' => 'tech', 'MSFT' => 'tech', 'GOOGL' => 'tech', 'META' => 'tech',
    'AMZN' => 'tech_consumer', 'NVDA' => 'tech_semi', 'NFLX' => 'tech_consumer',
    // Financials
    'JPM' => 'finance', 'BAC' => 'finance',
    // Consumer/Energy
    'WMT' => 'consumer', 'XOM' => 'energy', 'JNJ' => 'healthcare',
    // Crypto groups (BTC-correlated)
    'BTCUSD' => 'crypto_major', 'ETHUSD' => 'crypto_major',
    'SOLUSD' => 'crypto_alt_l1', 'AVAXUSD' => 'crypto_alt_l1', 'ADAUSD' => 'crypto_alt_l1',
    'DOTUSD' => 'crypto_alt_l1', 'NEARUSD' => 'crypto_alt_l1', 'APTUSD' => 'crypto_alt_l1',
    'SUIUSD' => 'crypto_alt_l1',
    'BNBUSD' => 'crypto_exchange', 'UNIUSD' => 'crypto_defi', 'AAVEUSD' => 'crypto_defi',
    'LINKUSD' => 'crypto_infra', 'ARBUSD' => 'crypto_l2', 'OPUSD' => 'crypto_l2',
    'XRPUSD' => 'crypto_payment', 'LTCUSD' => 'crypto_payment',
    'DOGEUSD' => 'crypto_meme', 'SHIBUSD' => 'crypto_meme',
    'PEPEUSD' => 'crypto_meme', 'FLOKIUSD' => 'crypto_meme',
    // Forex groups (USD pairs)
    'EURUSD' => 'fx_major', 'GBPUSD' => 'fx_major',
    'USDJPY' => 'fx_jpy', 'USDCAD' => 'fx_cad', 'USDCHF' => 'fx_chf',
    'AUDUSD' => 'fx_commodity', 'NZDUSD' => 'fx_commodity',
    'EURGBP' => 'fx_cross'
);
$MAX_PER_SECTOR = 2;  // Max 2 positions in any single sector group

// ─── Auto-create tables ─────────────────────────────────────────────
$conn->query("
CREATE TABLE IF NOT EXISTS lm_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset_class VARCHAR(10) NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    signal_id INT NOT NULL DEFAULT 0,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    entry_time DATETIME NOT NULL,
    entry_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    position_size_units DECIMAL(18,8) NOT NULL DEFAULT 0,
    position_value_usd DECIMAL(12,2) NOT NULL DEFAULT 0,
    target_tp_pct DECIMAL(6,2) NOT NULL DEFAULT 5,
    target_sl_pct DECIMAL(6,2) NOT NULL DEFAULT 3,
    max_hold_hours INT NOT NULL DEFAULT 24,
    current_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    unrealized_pnl_usd DECIMAL(12,2) NOT NULL DEFAULT 0,
    unrealized_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    highest_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    lowest_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    exit_time DATETIME,
    exit_price DECIMAL(18,8) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(50) NOT NULL DEFAULT '',
    realized_pnl_usd DECIMAL(12,2) NOT NULL DEFAULT 0,
    realized_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    fees_usd DECIMAL(8,2) NOT NULL DEFAULT 0,
    hold_hours DECIMAL(8,2) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    KEY idx_status (status),
    KEY idx_asset (asset_class),
    KEY idx_symbol (symbol),
    KEY idx_entry (entry_time),
    KEY idx_signal (signal_id)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

$conn->query("
CREATE TABLE IF NOT EXISTS lm_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_time DATETIME NOT NULL,
    total_value_usd DECIMAL(12,2) NOT NULL DEFAULT 10000,
    cash_usd DECIMAL(12,2) NOT NULL DEFAULT 10000,
    invested_usd DECIMAL(12,2) NOT NULL DEFAULT 0,
    open_positions INT NOT NULL DEFAULT 0,
    unrealized_pnl_usd DECIMAL(12,2) NOT NULL DEFAULT 0,
    realized_pnl_today DECIMAL(12,2) NOT NULL DEFAULT 0,
    cumulative_pnl_usd DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_trades INT NOT NULL DEFAULT 0,
    total_wins INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    peak_value DECIMAL(12,2) NOT NULL DEFAULT 10000,
    drawdown_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    KEY idx_time (snapshot_time)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");


// ─── Helper: calculate fees ─────────────────────────────────────────
// Crypto: 0.20% per side (NDAX flat rate — more realistic than 0.1%)
// Forex: spread already priced in (0 explicit fee)
// Stocks: US$0.0099/share, min US$1.99 per side (Moomoo model)
function _lt_calc_fees($asset_class, $entry_price, $exit_price, $units) {
    if ($asset_class === 'CRYPTO') {
        $entry_fee = $entry_price * $units * 0.002; // 0.20% per side (NDAX)
        $exit_fee  = $exit_price  * $units * 0.002;
        return round($entry_fee + $exit_fee, 2);
    }
    if ($asset_class === 'STOCK') {
        // Moomoo: US$0.0099/share, min US$1.99 per side
        $shares = abs($units);
        $entry_fee = max(1.99, $shares * 0.0099);
        $exit_fee  = max(1.99, $shares * 0.0099);
        return round($entry_fee + $exit_fee, 2);
    }
    return 0; // forex spread already priced in
}


// ─── Helper: volatility-adjusted position size (Kimi recommendation) ─
// Uses recent price volatility from lm_price_cache to adjust position %
// High vol → smaller position (down to MIN), low vol → larger (up to MAX)
function _lt_vol_adjusted_position_pct($conn, $symbol, $asset_class) {
    global $DEFAULT_POSITION_PCT, $MIN_POSITION_PCT, $MAX_POSITION_PCT;
    $safe = $conn->real_escape_string($symbol);

    // Get last 20 price updates to calculate volatility
    $r = $conn->query("SELECT price FROM lm_price_cache
        WHERE symbol = '$safe'
        ORDER BY updated_at DESC LIMIT 20");
    if (!$r || $r->num_rows < 5) return $DEFAULT_POSITION_PCT;

    $prices = array();
    while ($row = $r->fetch_assoc()) {
        $prices[] = (float)$row['price'];
    }
    $r->free();

    // Calculate returns volatility
    $returns = array();
    for ($i = 0; $i < count($prices) - 1; $i++) {
        if ($prices[$i + 1] > 0) {
            $returns[] = abs(($prices[$i] - $prices[$i + 1]) / $prices[$i + 1]);
        }
    }
    if (count($returns) < 3) return $DEFAULT_POSITION_PCT;

    $avg_vol = array_sum($returns) / count($returns);

    // Volatility thresholds by asset class
    if ($asset_class === 'CRYPTO') {
        // Crypto is naturally more volatile
        if ($avg_vol > 0.04)  return $MIN_POSITION_PCT;  // >4% avg move = reduce
        if ($avg_vol < 0.015) return $MAX_POSITION_PCT;  // <1.5% = increase
    } elseif ($asset_class === 'STOCK') {
        if ($avg_vol > 0.025) return $MIN_POSITION_PCT;  // >2.5% avg move
        if ($avg_vol < 0.008) return $MAX_POSITION_PCT;  // <0.8%
    } else {
        // Forex
        if ($avg_vol > 0.012) return $MIN_POSITION_PCT;  // >1.2%
        if ($avg_vol < 0.004) return $MAX_POSITION_PCT;  // <0.4%
    }
    return $DEFAULT_POSITION_PCT;
}

// ─── World-Class: Half-Kelly position sizing ─────────────────────────
// Science: Kelly (1956), Thorp (1962)
// Uses per-algorithm win rate and payoff ratio to size positions optimally
// Half-Kelly captures ~75% of optimal growth with ~50% less drawdown
function _lt_kelly_position_pct($conn, $algorithm_name, $asset_class, $vol_pct) {
    // Try to get Kelly fraction from pre-computed table
    $safe_algo  = $conn->real_escape_string($algorithm_name);
    $safe_asset = $conn->real_escape_string($asset_class);

    $r = $conn->query("SELECT half_kelly, sample_size FROM lm_kelly_fractions
        WHERE algorithm_name='$safe_algo'
        AND (asset_class='$safe_asset' OR asset_class='ALL')
        ORDER BY CASE WHEN asset_class='$safe_asset' THEN 0 ELSE 1 END
        LIMIT 1");

    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $r->free();
        $half_kelly = (float)$row['half_kelly'];
        $sample_size = (int)$row['sample_size'];

        // Only use Kelly if we have enough samples (>= 20 trades)
        if ($sample_size >= 20 && $half_kelly > 0) {
            // Convert Kelly fraction to percentage (cap at 15%)
            $kelly_pct = min(15.0, max(1.0, $half_kelly * 100));

            // Blend with vol-adjusted: use Kelly when confident, vol otherwise
            // Confidence increases with sample size
            $confidence = min(1.0, ($sample_size - 20) / 80.0); // 0-1 ramp from 20 to 100 trades
            $blended = ($kelly_pct * $confidence) + ($vol_pct * (1 - $confidence));

            return round($blended, 2);
        }
    }

    // Fallback: use volatility-adjusted sizing
    return $vol_pct;
}

// ─── World-Class: Drawdown-based position scaling ────────────────────
// Science: Optimal-f theory (Vince 1990), risk parity (Bridgewater)
// When portfolio is in drawdown, reduce position sizes to preserve capital.
// At max acceptable drawdown (10%), positions are halved.
// This prevents ruin during losing streaks — every MOTHERLOAD recommended this.
function _lt_drawdown_scale($conn) {
    global $INITIAL_CAPITAL;
    $portfolio = _lt_get_portfolio_value($conn);
    $drawdown_pct = 0;

    // Get peak from snapshots
    $r = $conn->query("SELECT MAX(total_value_usd) AS peak FROM lm_snapshots");
    $peak = (float) $INITIAL_CAPITAL;
    if ($r) {
        $row = $r->fetch_assoc();
        if ($row && $row['peak'] !== null && (float) $row['peak'] > $peak) {
            $peak = (float) $row['peak'];
        }
        $r->free();
    }

    if ($peak > 0 && $portfolio < $peak) {
        $drawdown_pct = (($peak - $portfolio) / $peak) * 100;
    }

    // Scale factor: 1.0 at 0% DD, 0.5 at 10% DD, 0.25 at 20% DD
    // Formula: scale = 1 / (1 + DD%/10)
    if ($drawdown_pct <= 0) return 1.0;
    $scale = 1.0 / (1.0 + $drawdown_pct / 10.0);
    return round(max(0.25, min(1.0, $scale)), 4);
}


// ─── World-Class: Signal cooldown ────────────────────────────────────
// Prevents re-entering the same symbol shortly after a stop-loss exit.
// If a symbol was stopped out in the last N hours, skip it.
// Science: Behavioral finance — revenge trading is the #1 retail killer.
function _lt_check_cooldown($conn, $symbol, $cooldown_hours) {
    $safe_sym = $conn->real_escape_string($symbol);
    $cutoff = date('Y-m-d H:i:s', time() - ($cooldown_hours * 3600));
    $r = $conn->query("SELECT id FROM lm_trades
        WHERE symbol = '$safe_sym'
        AND status = 'closed'
        AND exit_reason = 'stop_loss'
        AND exit_time >= '$cutoff'
        LIMIT 1");
    if ($r) {
        $has_recent_sl = ($r->num_rows > 0);
        $r->free();
        return $has_recent_sl; // true = on cooldown, skip this symbol
    }
    return false;
}


// ─── World-Class: Slippage estimation ────────────────────────────────
// Estimates execution slippage based on position size and asset type
// Science: Market microstructure — larger positions = more impact
function _lt_estimate_slippage_bps($asset_class, $position_value_usd) {
    // Base slippage by asset class (in basis points)
    if ($asset_class === 'CRYPTO') {
        $base_bps = 15; // 0.15% base (wider spreads)
        $impact_threshold = 5000; // Impact starts above $5K
    } elseif ($asset_class === 'FOREX') {
        $base_bps = 3;  // 0.03% base (tight spreads)
        $impact_threshold = 50000;
    } else {
        $base_bps = 5;  // 0.05% base (moderate spreads)
        $impact_threshold = 10000;
    }

    // Market impact: increases linearly above threshold
    $impact_bps = 0;
    if ($position_value_usd > $impact_threshold) {
        $excess = $position_value_usd - $impact_threshold;
        $impact_bps = ($excess / $impact_threshold) * 10; // 10bps per $threshold
    }

    return round($base_bps + $impact_bps, 2);
}


// ─── World-Class: Python-computed position sizing from lm_position_sizing ─
// Reads the pre-computed final_size_pct from the position_sizer.py output.
// Python computes: Half-Kelly + EWMA vol + regime modifier + alpha decay weight.
// This is more sophisticated than the PHP-only sizing because it has access to
// full numpy/scipy capabilities for EWMA, PCA factor budgeting, and CVaR.
// Falls back to 0 (meaning "use PHP sizing") if no data available.
function _lt_python_position_pct($conn, $algorithm_name) {
    $safe_algo = $conn->real_escape_string($algorithm_name);

    // Check if lm_position_sizing table exists
    $table_check = $conn->query("SHOW TABLES LIKE 'lm_position_sizing'");
    if (!$table_check || $table_check->num_rows == 0) {
        return 0;
    }

    // Get the latest Python-computed sizing for this algorithm
    // Only use data from the last 24 hours (stale data is worse than no data)
    $r = $conn->query("SELECT final_size_pct, is_decaying, algo_sharpe_30d,
            regime_modifier, decay_weight
        FROM lm_position_sizing
        WHERE algorithm_name = '$safe_algo'
        AND date >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
        ORDER BY id DESC LIMIT 1");

    if (!$r || $r->num_rows == 0) {
        return 0; // No recent Python sizing, fall back to PHP
    }

    $row = $r->fetch_assoc();
    $r->free();

    $final_pct = (float)$row['final_size_pct'];
    $is_decaying = (int)$row['is_decaying'];

    // Sanity bounds: Python should produce 1-15%, reject outliers
    if ($final_pct < 0.5 || $final_pct > 20) {
        return 0; // Reject unreasonable values
    }

    // If algorithm is flagged as decaying, cap at 3%
    if ($is_decaying && $final_pct > 3) {
        $final_pct = 3.0;
    }

    return round($final_pct, 2);
}


// ─── Helper: trailing stop calculation (Kimi recommendation) ─────────
// Returns adjusted SL pct when trailing is active, or 0 if not triggered
function _lt_trailing_stop_pct($pos, $current_price) {
    global $TRAILING_ACTIVATE, $TRAILING_FACTOR;

    $tp       = (float)$pos['target_tp_pct'];
    $sl       = (float)$pos['target_sl_pct'];
    $entry    = (float)$pos['entry_price'];
    $highest  = (float)$pos['highest_price'];
    $direction = $pos['direction'];

    if ($tp <= 0 || $entry <= 0 || $highest <= 0) return 0;

    // Calculate how far we've moved toward TP
    if ($direction === 'LONG') {
        $max_gain_pct = (($highest - $entry) / $entry) * 100;
    } else {
        $max_gain_pct = (($entry - (float)$pos['lowest_price']) / $entry) * 100;
    }

    // Only activate trailing after reaching 50% of TP
    if ($max_gain_pct < $tp * $TRAILING_ACTIVATE) return 0;

    // Trailing stop: from highest price, trail back by a fraction of the SL
    $trail_dist_pct = $sl * $TRAILING_FACTOR;

    if ($direction === 'LONG') {
        // Trailing: highest_price * (1 - trail%) is the floor
        $trail_floor = $highest * (1 - $trail_dist_pct / 100);
        if ($current_price <= $trail_floor) return -1; // Signal exit
    } else {
        // SHORT: lowest price * (1 + trail%) is the ceiling
        $lowest = (float)$pos['lowest_price'];
        if ($lowest > 0) {
            $trail_ceiling = $lowest * (1 + $trail_dist_pct / 100);
            if ($current_price >= $trail_ceiling) return -1;
        }
    }

    return 0; // Trailing active but not yet hit
}


// ─── Helper: get portfolio value ────────────────────────────────────
function _lt_get_portfolio_value($conn) {
    global $INITIAL_CAPITAL;

    $value = (float) $INITIAL_CAPITAL;

    // Add cumulative realized P&L from all closed trades
    $r = $conn->query("SELECT SUM(realized_pnl_usd) AS total_rpnl FROM lm_trades WHERE status='closed'");
    if ($r) {
        $row = $r->fetch_assoc();
        if ($row && $row['total_rpnl'] !== null) {
            $value += (float) $row['total_rpnl'];
        }
        $r->free();
    }

    // Add unrealized P&L from open positions
    $r2 = $conn->query("SELECT SUM(unrealized_pnl_usd) AS total_upnl FROM lm_trades WHERE status='open'");
    if ($r2) {
        $row2 = $r2->fetch_assoc();
        if ($row2 && $row2['total_upnl'] !== null) {
            $value += (float) $row2['total_upnl'];
        }
        $r2->free();
    }

    // Subtract total fees
    $r3 = $conn->query("SELECT SUM(fees_usd) AS total_fees FROM lm_trades");
    if ($r3) {
        $row3 = $r3->fetch_assoc();
        if ($row3 && $row3['total_fees'] !== null) {
            $value -= (float) $row3['total_fees'];
        }
        $r3->free();
    }

    return round($value, 2);
}


// ─── Helper: take equity snapshot ───────────────────────────────────
function _lt_take_snapshot($conn) {
    global $INITIAL_CAPITAL;

    $now = date('Y-m-d H:i:s');
    $total_value = _lt_get_portfolio_value($conn);

    // Open positions
    $r = $conn->query("SELECT COUNT(*) AS cnt, COALESCE(SUM(position_value_usd),0) AS invested, COALESCE(SUM(unrealized_pnl_usd),0) AS upnl FROM lm_trades WHERE status='open'");
    $open_cnt   = 0;
    $invested   = 0;
    $upnl       = 0;
    if ($r) {
        $row = $r->fetch_assoc();
        $open_cnt = (int) $row['cnt'];
        $invested = (float) $row['invested'];
        $upnl     = (float) $row['upnl'];
        $r->free();
    }

    $cash = $total_value - $invested - $upnl;

    // Cumulative realized P&L
    $cum_pnl = 0;
    $r2 = $conn->query("SELECT COALESCE(SUM(realized_pnl_usd),0) AS rpnl FROM lm_trades WHERE status='closed'");
    if ($r2) {
        $row2 = $r2->fetch_assoc();
        $cum_pnl = (float) $row2['rpnl'];
        $r2->free();
    }

    // Today's realized P&L
    $today = date('Y-m-d');
    $today_pnl = 0;
    $r3 = $conn->query("SELECT COALESCE(SUM(realized_pnl_usd),0) AS rpnl FROM lm_trades WHERE status='closed' AND exit_time >= '" . $conn->real_escape_string($today) . " 00:00:00'");
    if ($r3) {
        $row3 = $r3->fetch_assoc();
        $today_pnl = (float) $row3['rpnl'];
        $r3->free();
    }

    // Total trades and wins
    $total_trades = 0;
    $total_wins   = 0;
    $r4 = $conn->query("SELECT COUNT(*) AS cnt FROM lm_trades WHERE status='closed'");
    if ($r4) {
        $row4 = $r4->fetch_assoc();
        $total_trades = (int) $row4['cnt'];
        $r4->free();
    }
    $r5 = $conn->query("SELECT COUNT(*) AS cnt FROM lm_trades WHERE status='closed' AND realized_pnl_usd > 0");
    if ($r5) {
        $row5 = $r5->fetch_assoc();
        $total_wins = (int) $row5['cnt'];
        $r5->free();
    }
    $win_rate = ($total_trades > 0) ? round(($total_wins / $total_trades) * 100, 2) : 0;

    // Peak value from previous snapshots
    $peak = (float) $INITIAL_CAPITAL;
    $r6 = $conn->query("SELECT MAX(total_value_usd) AS peak_val FROM lm_snapshots");
    if ($r6) {
        $row6 = $r6->fetch_assoc();
        if ($row6 && $row6['peak_val'] !== null && (float) $row6['peak_val'] > $peak) {
            $peak = (float) $row6['peak_val'];
        }
        $r6->free();
    }
    if ($total_value > $peak) {
        $peak = $total_value;
    }

    $drawdown = ($peak > 0) ? round((($peak - $total_value) / $peak) * 100, 4) : 0;

    $conn->query("INSERT INTO lm_snapshots (snapshot_time, total_value_usd, cash_usd, invested_usd, open_positions, unrealized_pnl_usd, realized_pnl_today, cumulative_pnl_usd, total_trades, total_wins, win_rate, peak_value, drawdown_pct) VALUES (
        '" . $conn->real_escape_string($now) . "',
        " . (float) $total_value . ",
        " . (float) $cash . ",
        " . (float) $invested . ",
        " . (int) $open_cnt . ",
        " . (float) $upnl . ",
        " . (float) $today_pnl . ",
        " . (float) $cum_pnl . ",
        " . (int) $total_trades . ",
        " . (int) $total_wins . ",
        " . (float) $win_rate . ",
        " . (float) $peak . ",
        " . (float) $drawdown . "
    )");

    return array(
        'snapshot_time'      => $now,
        'total_value_usd'    => $total_value,
        'cash_usd'           => round($cash, 2),
        'invested_usd'       => round($invested, 2),
        'open_positions'     => $open_cnt,
        'unrealized_pnl_usd' => round($upnl, 2),
        'realized_pnl_today' => round($today_pnl, 2),
        'cumulative_pnl_usd' => round($cum_pnl, 2),
        'total_trades'       => $total_trades,
        'total_wins'         => $total_wins,
        'win_rate'           => $win_rate,
        'peak_value'         => round($peak, 2),
        'drawdown_pct'       => $drawdown
    );
}


// ─── Helper: close a position ───────────────────────────────────────
function _lt_close_position($conn, $position, $exit_price, $reason) {
    $now        = date('Y-m-d H:i:s');
    $entry_ts   = strtotime($position['entry_time']);
    $hold_hours = round((time() - $entry_ts) / 3600, 2);

    $entry_price = (float) $position['entry_price'];
    $units       = (float) $position['position_size_units'];
    $pos_value   = (float) $position['position_value_usd'];
    $direction   = $position['direction'];

    // Calculate realized P&L
    if ($direction === 'LONG') {
        $pnl_pct = (($exit_price - $entry_price) / $entry_price) * 100;
    } else {
        $pnl_pct = (($entry_price - $exit_price) / $entry_price) * 100;
    }
    $gross_pnl = $pos_value * $pnl_pct / 100;

    // Calculate fees
    $fees = _lt_calc_fees($position['asset_class'], $entry_price, $exit_price, $units);

    // Net P&L
    $net_pnl = round($gross_pnl - $fees, 2);
    $net_pct = round($pnl_pct - ($fees / $pos_value * 100), 4);

    $id = (int) $position['id'];
    $conn->query("UPDATE lm_trades SET
        status            = 'closed',
        exit_time         = '" . $conn->real_escape_string($now) . "',
        exit_price        = " . (float) $exit_price . ",
        exit_reason       = '" . $conn->real_escape_string($reason) . "',
        realized_pnl_usd  = " . (float) $net_pnl . ",
        realized_pct      = " . (float) $net_pct . ",
        fees_usd          = " . (float) $fees . ",
        hold_hours        = " . (float) $hold_hours . ",
        current_price     = " . (float) $exit_price . ",
        unrealized_pnl_usd = 0,
        unrealized_pct     = 0
    WHERE id = " . $id);

    // Auto-recompute Kelly fraction for this algorithm+asset class
    // This keeps Half-Kelly sizing data fresh without external scripts
    _lt_update_kelly($conn, $position['algorithm_name'], $position['asset_class']);

    return array(
        'id'              => $id,
        'symbol'          => $position['symbol'],
        'direction'       => $direction,
        'entry_price'     => $entry_price,
        'exit_price'      => $exit_price,
        'exit_reason'     => $reason,
        'realized_pnl_usd' => $net_pnl,
        'realized_pct'    => $net_pct,
        'fees_usd'        => $fees,
        'hold_hours'      => $hold_hours
    );
}


// ─── Auto-compute Kelly fraction for an algorithm ────────────────────
// Called after every trade close to keep Half-Kelly sizing data fresh.
// Kelly criterion: f* = p - q/b where p=win_rate, q=1-p, b=avg_win/avg_loss
function _lt_update_kelly($conn, $algorithm_name, $asset_class) {
    if ($algorithm_name === '') return;
    $safe_algo  = $conn->real_escape_string($algorithm_name);
    $safe_asset = $conn->real_escape_string($asset_class);

    // Get stats for this algorithm+asset
    $r = $conn->query("SELECT
        COUNT(*) AS sample_size,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) AS wins,
        AVG(CASE WHEN realized_pnl_usd > 0 THEN realized_pct ELSE NULL END) AS avg_win_pct,
        AVG(CASE WHEN realized_pnl_usd <= 0 THEN ABS(realized_pct) ELSE NULL END) AS avg_loss_pct
    FROM lm_trades
    WHERE algorithm_name = '$safe_algo'
    AND asset_class = '$safe_asset'
    AND status = 'closed'");

    if (!$r) return;
    $row = $r->fetch_assoc();
    $r->free();

    $sample = (int) $row['sample_size'];
    if ($sample < 5) return; // Need minimum 5 trades

    $wins     = (int) $row['wins'];
    $win_rate = $wins / $sample;
    $avg_win  = ($row['avg_win_pct'] !== null) ? (float) $row['avg_win_pct'] : 0;
    $avg_loss = ($row['avg_loss_pct'] !== null) ? (float) $row['avg_loss_pct'] : 0;

    if ($avg_loss <= 0) $avg_loss = 0.01; // Prevent division by zero
    $odds = $avg_win / $avg_loss; // b = avg_win / avg_loss

    // Kelly fraction: f* = p - q/b = win_rate - (1-win_rate) / odds
    $full_kelly = $win_rate - ((1 - $win_rate) / $odds);
    $half_kelly = $full_kelly / 2;

    // Clamp: negative Kelly = don't trade, cap at 25%
    if ($half_kelly < 0) $half_kelly = 0;
    if ($half_kelly > 0.25) $half_kelly = 0.25;

    $now = date('Y-m-d H:i:s');

    // Create table if not exists
    $conn->query("CREATE TABLE IF NOT EXISTS lm_kelly_fractions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        algorithm_name VARCHAR(100) NOT NULL,
        asset_class VARCHAR(10) NOT NULL DEFAULT 'ALL',
        win_rate DECIMAL(8,4) NOT NULL DEFAULT 0,
        avg_win_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
        avg_loss_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
        full_kelly DECIMAL(8,4) NOT NULL DEFAULT 0,
        half_kelly DECIMAL(8,4) NOT NULL DEFAULT 0,
        sample_size INT NOT NULL DEFAULT 0,
        updated_at DATETIME NOT NULL,
        KEY idx_algo (algorithm_name),
        KEY idx_asset (asset_class)
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");

    // Upsert: delete old + insert new
    $conn->query("DELETE FROM lm_kelly_fractions
        WHERE algorithm_name = '$safe_algo' AND asset_class = '$safe_asset'");
    $conn->query("INSERT INTO lm_kelly_fractions
        (algorithm_name, asset_class, win_rate, avg_win_pct, avg_loss_pct,
         full_kelly, half_kelly, sample_size, updated_at)
        VALUES ('$safe_algo', '$safe_asset',
         " . round($win_rate, 4) . ", " . round($avg_win, 4) . ", " . round($avg_loss, 4) . ",
         " . round($full_kelly, 4) . ", " . round($half_kelly, 4) . ",
         $sample, '$now')");
}


// ─── Helper: check admin key ────────────────────────────────────────
function _lt_check_admin($key) {
    global $ADMIN_KEY;
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        exit;
    }
}


// ─── Helper: fetch a single row as assoc array ──────────────────────
function _lt_fetch_row($result) {
    if (!$result) {
        return null;
    }
    $row = $result->fetch_assoc();
    $result->free();
    return $row;
}


// ─── Helper: fetch all rows as array of assoc arrays ────────────────
function _lt_fetch_all($result) {
    $rows = array();
    if (!$result) {
        return $rows;
    }
    while ($row = $result->fetch_assoc()) {
        $rows[] = $row;
    }
    $result->free();
    return $rows;
}


// ─── Route action ───────────────────────────────────────────────────
$action = isset($_GET['action']) ? $_GET['action'] : (isset($_POST['action']) ? $_POST['action'] : '');

switch ($action) {

// =====================================================================
// ACTION: enter — Open new position
// =====================================================================
case 'enter':
    _lt_check_admin(isset($_POST['key']) ? $_POST['key'] : (isset($_GET['key']) ? $_GET['key'] : ''));

    $signal_id  = isset($_REQUEST['signal_id'])  ? (int) $_REQUEST['signal_id'] : 0;
    $symbol     = '';
    $asset_class = '';
    $direction  = 'LONG';
    $algorithm  = '';
    $tp_pct     = 5;
    $sl_pct     = 3;
    $max_hold   = 24;

    // If signal_id provided, look up signal from lm_signals
    if ($signal_id > 0) {
        $sig_r = $conn->query("SELECT * FROM lm_signals WHERE id = " . $signal_id);
        $sig = _lt_fetch_row($sig_r);
        if (!$sig) {
            header('HTTP/1.0 404 Not Found');
            echo json_encode(array('ok' => false, 'error' => 'Signal not found: ' . $signal_id));
            exit;
        }
        $symbol      = $sig['symbol'];
        $asset_class = $sig['asset_class'];
        $direction   = isset($sig['direction']) ? $sig['direction'] : 'LONG';
        $algorithm   = isset($sig['algorithm_name']) ? $sig['algorithm_name'] : '';
        $tp_pct      = isset($sig['target_tp_pct']) ? (float) $sig['target_tp_pct'] : 5;
        $sl_pct      = isset($sig['target_sl_pct']) ? (float) $sig['target_sl_pct'] : 3;
        $max_hold    = isset($sig['max_hold_hours']) ? (int) $sig['max_hold_hours'] : 24;
    } else {
        // Manual entry
        $symbol      = isset($_REQUEST['symbol'])      ? trim($_REQUEST['symbol']) : '';
        $asset_class = isset($_REQUEST['asset_class'])  ? strtoupper(trim($_REQUEST['asset_class'])) : '';
        $direction   = isset($_REQUEST['direction'])    ? strtoupper(trim($_REQUEST['direction'])) : 'LONG';
        $algorithm   = isset($_REQUEST['algorithm'])    ? trim($_REQUEST['algorithm']) : '';
        $tp_pct      = isset($_REQUEST['tp_pct'])       ? (float) $_REQUEST['tp_pct'] : 5;
        $sl_pct      = isset($_REQUEST['sl_pct'])       ? (float) $_REQUEST['sl_pct'] : 3;
        $max_hold    = isset($_REQUEST['max_hold_hours']) ? (int) $_REQUEST['max_hold_hours'] : 24;
    }

    if ($symbol === '' || $asset_class === '') {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'symbol and asset_class are required'));
        exit;
    }

    if ($direction !== 'LONG' && $direction !== 'SHORT') {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'direction must be LONG or SHORT'));
        exit;
    }

    // Check circuit breaker
    $breaker_r = $conn->query("SELECT id, reason FROM lm_breaker_log WHERE active = 1 ORDER BY id DESC LIMIT 1");
    if ($breaker_r) {
        $breaker = $breaker_r->fetch_assoc();
        $breaker_r->free();
        if ($breaker) {
            header('HTTP/1.0 403 Forbidden');
            echo json_encode(array('ok' => false, 'error' => 'Circuit breaker active: ' . $breaker['reason']));
            exit;
        }
    }

    // Check max concurrent open positions (global limit)
    $open_r = $conn->query("SELECT COUNT(*) AS cnt FROM lm_trades WHERE status='open'");
    $open_row = _lt_fetch_row($open_r);
    $open_count = $open_row ? (int) $open_row['cnt'] : 0;

    if ($open_count >= $MAX_POSITIONS) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Max concurrent positions reached (' . $MAX_POSITIONS . ')'));
        exit;
    }

    // Per-asset-class position limit (Feb 11, 2026)
    if (isset($MAX_POSITIONS_PER_ASSET[$asset_class])) {
        $asset_max = $MAX_POSITIONS_PER_ASSET[$asset_class];
        $asset_r = $conn->query("SELECT COUNT(*) AS cnt FROM lm_trades WHERE status='open' AND asset_class='" . $conn->real_escape_string($asset_class) . "'");
        $asset_row = _lt_fetch_row($asset_r);
        $asset_count = $asset_row ? (int) $asset_row['cnt'] : 0;
        if ($asset_count >= $asset_max) {
            header('HTTP/1.0 400 Bad Request');
            echo json_encode(array('ok' => false, 'error' => 'Max ' . $asset_class . ' positions reached (' . $asset_max . ')'));
            exit;
        }
    }

    // Crypto algorithm filter — only preferred algos can open crypto trades (Feb 11, 2026)
    if ($asset_class === 'CRYPTO' && $algorithm !== '' && !in_array($algorithm, $CRYPTO_PREFERRED_ALGOS)) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Algorithm ' . $algorithm . ' not in crypto preferred list'));
        exit;
    }

    // Get current price from lm_price_cache
    $safe_sym = $conn->real_escape_string($symbol);
    $safe_ac  = $conn->real_escape_string($asset_class);
    $price_r  = $conn->query("SELECT price FROM lm_price_cache WHERE symbol = '" . $safe_sym . "' AND asset_class = '" . $safe_ac . "' ORDER BY last_updated DESC LIMIT 1");
    $price_row = _lt_fetch_row($price_r);
    if (!$price_row || (float) $price_row['price'] <= 0) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'No price available for ' . $symbol . ' (' . $asset_class . ')'));
        exit;
    }
    $entry_price = (float) $price_row['price'];

    // Crypto TP floor: enforce minimum 3% TP to avoid premature exits (Feb 11, 2026)
    if ($asset_class === 'CRYPTO' && $tp_pct < $CRYPTO_MIN_TP_PCT) {
        $tp_pct = $CRYPTO_MIN_TP_PCT;
    }

    // Minimum SL floor: with 30-min tracking interval, SLs below 1.5% are unrealistic.
    // Price can easily move 1-2% between checks, making tight SLs meaningless and
    // causing exits far worse than the target (e.g. -12% exit on -3% SL target).
    // Per-asset floors: Crypto 2%, Stock 1.5%, Forex 1%
    $SL_FLOORS = array('CRYPTO' => 2.0, 'STOCK' => 1.5, 'FOREX' => 1.0);
    $sl_floor = isset($SL_FLOORS[$asset_class]) ? $SL_FLOORS[$asset_class] : 1.5;
    if ($sl_pct < $sl_floor) {
        $sl_pct = $sl_floor;
    }

    // Max hold cap: prevent week-long positions blocking slots (Feb 12, 2026)
    $hold_cap = isset($MAX_HOLD_CAP[$asset_class]) ? $MAX_HOLD_CAP[$asset_class] : 72;
    if ($max_hold > $hold_cap) {
        $max_hold = $hold_cap;
    }

    // Calculate position size: Python-computed (preferred) or PHP Half-Kelly fallback
    $portfolio_value = _lt_get_portfolio_value($conn);

    // Step 0: Check for Python-computed position sizing from lm_position_sizing.
    // Python position_sizer.py computes: Half-Kelly + EWMA vol + regime + alpha decay.
    // This is more accurate than PHP-only sizing — uses full numpy/scipy capabilities.
    $python_pct = _lt_python_position_pct($conn, $algorithm);

    if ($python_pct > 0) {
        // Use Python-computed sizing (already includes vol, regime, decay adjustments)
        $kelly_pct = $python_pct;
        $dd_scale = _lt_drawdown_scale($conn); // Still apply PHP drawdown guard
    } else {
        // Fallback: PHP-only sizing (original World-Class upgrade path)
        // Step 1: Volatility-adjusted base (Kimi)
        $vol_pct = _lt_vol_adjusted_position_pct($conn, $symbol, $asset_class);
        // Step 2: Half-Kelly override when sufficient trade history exists
        $kelly_pct = _lt_kelly_position_pct($conn, $algorithm, $asset_class, $vol_pct);
        // Step 3: Drawdown scaling
        $dd_scale = _lt_drawdown_scale($conn);
    }

    // Step 4: Estimate slippage and calculate final position value
    $raw_position    = round($portfolio_value * ($kelly_pct / 100) * $dd_scale, 2);
    $slippage_bps    = _lt_estimate_slippage_bps($asset_class, $raw_position);
    $position_value  = $raw_position;
    $units           = $position_value / $entry_price;

    // Calculate entry fees (matching _lt_calc_fees model)
    $entry_fee = 0;
    if ($asset_class === 'CRYPTO') {
        $entry_fee = round($entry_price * $units * 0.002, 2); // 0.20% per side (NDAX)
    } elseif ($asset_class === 'STOCK') {
        $entry_shares = abs((int) $units);
        $entry_fee = max(1.99, $entry_shares * 0.0099); // Moomoo: $0.0099/share, min $1.99
    }

    $now = date('Y-m-d H:i:s');

    $conn->query("INSERT INTO lm_trades (
        asset_class, symbol, algorithm_name, signal_id, direction,
        entry_time, entry_price, position_size_units, position_value_usd,
        target_tp_pct, target_sl_pct, max_hold_hours,
        current_price, highest_price, lowest_price,
        status, fees_usd, created_at
    ) VALUES (
        '" . $safe_ac . "',
        '" . $safe_sym . "',
        '" . $conn->real_escape_string($algorithm) . "',
        " . (int) $signal_id . ",
        '" . $conn->real_escape_string($direction) . "',
        '" . $conn->real_escape_string($now) . "',
        " . (float) $entry_price . ",
        " . (float) $units . ",
        " . (float) $position_value . ",
        " . (float) $tp_pct . ",
        " . (float) $sl_pct . ",
        " . (int) $max_hold . ",
        " . (float) $entry_price . ",
        " . (float) $entry_price . ",
        " . (float) $entry_price . ",
        'open',
        " . (float) $entry_fee . ",
        '" . $conn->real_escape_string($now) . "'
    )");

    $new_id = $conn->insert_id;

    // Mark signal as executed if signal_id provided
    if ($signal_id > 0) {
        $conn->query("UPDATE lm_signals SET status = 'executed' WHERE id = " . (int) $signal_id);
    }

    echo json_encode(array(
        'ok'       => true,
        'action'   => 'enter',
        'trade_id' => $new_id,
        'position' => array(
            'id'                  => $new_id,
            'symbol'              => $symbol,
            'asset_class'         => $asset_class,
            'direction'           => $direction,
            'algorithm_name'      => $algorithm,
            'signal_id'           => $signal_id,
            'entry_time'          => $now,
            'entry_price'         => $entry_price,
            'position_size_units' => round($units, 8),
            'position_value_usd'  => $position_value,
            'target_tp_pct'       => $tp_pct,
            'target_sl_pct'       => $sl_pct,
            'max_hold_hours'      => $max_hold,
            'entry_fee'           => $entry_fee,
            'portfolio_value'     => $portfolio_value
        )
    ));
    break;


// =====================================================================
// ACTION: track — Update all open positions
// =====================================================================
case 'track':
    _lt_check_admin(isset($_POST['key']) ? $_POST['key'] : (isset($_GET['key']) ? $_GET['key'] : ''));

    $positions = _lt_fetch_all($conn->query("SELECT * FROM lm_trades WHERE status='open'"));

    $tracked = 0;
    $closed_list = array();
    $still_open  = 0;

    foreach ($positions as $pos) {
        $tracked++;
        $sym = $conn->real_escape_string($pos['symbol']);
        $ac  = $conn->real_escape_string($pos['asset_class']);
        $pid = (int) $pos['id'];

        // Get latest price
        $pr = $conn->query("SELECT price FROM lm_price_cache WHERE symbol = '" . $sym . "' AND asset_class = '" . $ac . "' ORDER BY last_updated DESC LIMIT 1");
        $pr_row = _lt_fetch_row($pr);
        if (!$pr_row) {
            $still_open++;
            continue; // no price available, skip
        }
        $current_price = (float) $pr_row['price'];

        $entry_price = (float) $pos['entry_price'];
        $units       = (float) $pos['position_size_units'];
        $pos_value   = (float) $pos['position_value_usd'];
        $direction   = $pos['direction'];

        // Calculate unrealized P&L
        if ($direction === 'LONG') {
            $pnl_pct = (($current_price - $entry_price) / $entry_price) * 100;
        } else {
            $pnl_pct = (($entry_price - $current_price) / $entry_price) * 100;
        }
        $pnl_usd = round($pos_value * $pnl_pct / 100, 2);
        $pnl_pct = round($pnl_pct, 4);

        // Track highest / lowest
        $highest = (float) $pos['highest_price'];
        $lowest  = (float) $pos['lowest_price'];
        if ($current_price > $highest) {
            $highest = $current_price;
        }
        if ($lowest <= 0 || $current_price < $lowest) {
            $lowest = $current_price;
        }

        // Check hold time
        $entry_ts   = strtotime($pos['entry_time']);
        $hold_hours = (time() - $entry_ts) / 3600;

        $tp  = (float) $pos['target_tp_pct'];
        $sl  = (float) $pos['target_sl_pct'];
        $mhh = (int) $pos['max_hold_hours'];

        // Retroactive max_hold cap: enforce per-asset cap on legacy positions (Feb 12, 2026)
        $pos_ac = $pos['asset_class'];
        $hold_cap = isset($MAX_HOLD_CAP[$pos_ac]) ? $MAX_HOLD_CAP[$pos_ac] : 72;
        if ($mhh > $hold_cap) {
            $mhh = $hold_cap;
            // Update DB so dashboard shows correct cap
            $conn->query("UPDATE lm_trades SET max_hold_hours = " . $hold_cap . " WHERE id = " . $pid);
        }

        $exit_reason = '';

        // Exit conditions (checked in order, with trailing stop — Kimi enhancement)
        if ($pnl_pct <= -$sl) {
            $exit_reason = 'stop_loss';
        } elseif ($pnl_pct >= $tp) {
            $exit_reason = 'take_profit';
        } elseif (_lt_trailing_stop_pct($pos, $current_price) == -1) {
            $exit_reason = 'trailing_stop';
        } elseif ($hold_hours >= $mhh) {
            $exit_reason = 'max_hold';
        }

        if ($exit_reason !== '') {
            // Close the position
            $closed = _lt_close_position($conn, $pos, $current_price, $exit_reason);
            $closed_list[] = $closed;
        } else {
            // Update unrealized P&L and hold_hours for still-open position
            $conn->query("UPDATE lm_trades SET
                current_price       = " . (float) $current_price . ",
                unrealized_pnl_usd  = " . (float) $pnl_usd . ",
                unrealized_pct      = " . (float) $pnl_pct . ",
                highest_price       = " . (float) $highest . ",
                lowest_price        = " . (float) $lowest . ",
                hold_hours          = " . round($hold_hours, 2) . "
            WHERE id = " . $pid);
            $still_open++;
        }
    }

    // Take portfolio snapshot
    $snapshot = _lt_take_snapshot($conn);

    echo json_encode(array(
        'ok'         => true,
        'action'     => 'track',
        'tracked'    => $tracked,
        'closed'     => count($closed_list),
        'still_open' => $still_open,
        'closed_positions' => $closed_list,
        'snapshot'   => $snapshot
    ));
    break;


// =====================================================================
// ACTION: close — Manually close a position
// =====================================================================
case 'close':
    _lt_check_admin(isset($_POST['key']) ? $_POST['key'] : (isset($_GET['key']) ? $_GET['key'] : ''));

    $trade_id = isset($_REQUEST['id']) ? (int) $_REQUEST['id'] : 0;
    if ($trade_id <= 0) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'id parameter required'));
        exit;
    }

    $pos_r = $conn->query("SELECT * FROM lm_trades WHERE id = " . $trade_id . " AND status = 'open'");
    $pos = _lt_fetch_row($pos_r);
    if (!$pos) {
        header('HTTP/1.0 404 Not Found');
        echo json_encode(array('ok' => false, 'error' => 'Open position not found with id ' . $trade_id));
        exit;
    }

    // Get current price
    $sym = $conn->real_escape_string($pos['symbol']);
    $ac  = $conn->real_escape_string($pos['asset_class']);
    $pr  = $conn->query("SELECT price FROM lm_price_cache WHERE symbol = '" . $sym . "' AND asset_class = '" . $ac . "' ORDER BY last_updated DESC LIMIT 1");
    $pr_row = _lt_fetch_row($pr);

    if (!$pr_row || (float) $pr_row['price'] <= 0) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'No price available for ' . $pos['symbol']));
        exit;
    }

    $exit_price = (float) $pr_row['price'];
    $closed = _lt_close_position($conn, $pos, $exit_price, 'manual');

    echo json_encode(array(
        'ok'       => true,
        'action'   => 'close',
        'position' => $closed
    ));
    break;


// =====================================================================
// ACTION: positions — List positions (public)
// =====================================================================
case 'positions':
    $status      = isset($_GET['status'])      ? trim($_GET['status']) : 'open';
    $asset_filter = isset($_GET['asset_class']) ? strtoupper(trim($_GET['asset_class'])) : '';
    $limit       = isset($_GET['limit'])        ? (int) $_GET['limit'] : 50;
    if ($limit < 1)   $limit = 1;
    if ($limit > 200)  $limit = 200;

    $where = array();
    if ($status !== 'all') {
        $where[] = "status = '" . $conn->real_escape_string($status) . "'";
    }
    if ($asset_filter !== '') {
        $where[] = "asset_class = '" . $conn->real_escape_string($asset_filter) . "'";
    }

    $sql = "SELECT * FROM lm_trades";
    if (count($where) > 0) {
        $sql .= " WHERE " . implode(' AND ', $where);
    }
    $sql .= " ORDER BY entry_time DESC LIMIT " . (int) $limit;

    $rows = _lt_fetch_all($conn->query($sql));

    echo json_encode(array(
        'ok'        => true,
        'action'    => 'positions',
        'status'    => $status,
        'count'     => count($rows),
        'positions' => $rows
    ));
    break;


// =====================================================================
// ACTION: dashboard — Overall stats (public)
// =====================================================================
case 'dashboard':
    // Closed trade stats
    $stats = array(
        'total_trades'    => 0,
        'wins'            => 0,
        'losses'          => 0,
        'win_rate'        => 0,
        'avg_return_pct'  => 0,
        'avg_win_pct'     => 0,
        'avg_loss_pct'    => 0,
        'total_pnl_usd'   => 0,
        'profit_factor'   => 0,
        'avg_hold_hours'  => 0
    );

    // Total trades
    $r = $conn->query("SELECT COUNT(*) AS cnt FROM lm_trades WHERE status='closed'");
    $row = _lt_fetch_row($r);
    $stats['total_trades'] = $row ? (int) $row['cnt'] : 0;

    // Wins
    $r = $conn->query("SELECT COUNT(*) AS cnt FROM lm_trades WHERE status='closed' AND realized_pnl_usd > 0");
    $row = _lt_fetch_row($r);
    $stats['wins'] = $row ? (int) $row['cnt'] : 0;

    // Losses
    $stats['losses'] = $stats['total_trades'] - $stats['wins'];

    // Win rate
    $stats['win_rate'] = ($stats['total_trades'] > 0) ? round(($stats['wins'] / $stats['total_trades']) * 100, 2) : 0;

    // Average return %
    $r = $conn->query("SELECT AVG(realized_pct) AS avg_ret FROM lm_trades WHERE status='closed'");
    $row = _lt_fetch_row($r);
    $stats['avg_return_pct'] = ($row && $row['avg_ret'] !== null) ? round((float) $row['avg_ret'], 4) : 0;

    // Average win %
    $r = $conn->query("SELECT AVG(realized_pct) AS avg_win FROM lm_trades WHERE status='closed' AND realized_pnl_usd > 0");
    $row = _lt_fetch_row($r);
    $stats['avg_win_pct'] = ($row && $row['avg_win'] !== null) ? round((float) $row['avg_win'], 4) : 0;

    // Average loss %
    $r = $conn->query("SELECT AVG(realized_pct) AS avg_loss FROM lm_trades WHERE status='closed' AND realized_pnl_usd <= 0");
    $row = _lt_fetch_row($r);
    $stats['avg_loss_pct'] = ($row && $row['avg_loss'] !== null) ? round((float) $row['avg_loss'], 4) : 0;

    // Total P&L
    $r = $conn->query("SELECT COALESCE(SUM(realized_pnl_usd), 0) AS total_pnl FROM lm_trades WHERE status='closed'");
    $row = _lt_fetch_row($r);
    $stats['total_pnl_usd'] = ($row) ? round((float) $row['total_pnl'], 2) : 0;

    // Profit factor = sum of wins / abs(sum of losses)
    $sum_wins = 0;
    $sum_losses = 0;
    $r = $conn->query("SELECT COALESCE(SUM(realized_pnl_usd), 0) AS sw FROM lm_trades WHERE status='closed' AND realized_pnl_usd > 0");
    $row = _lt_fetch_row($r);
    if ($row) $sum_wins = (float) $row['sw'];

    $r = $conn->query("SELECT COALESCE(SUM(realized_pnl_usd), 0) AS sl FROM lm_trades WHERE status='closed' AND realized_pnl_usd <= 0");
    $row = _lt_fetch_row($r);
    if ($row) $sum_losses = abs((float) $row['sl']);

    $stats['profit_factor'] = ($sum_losses > 0) ? round($sum_wins / $sum_losses, 4) : (($sum_wins > 0) ? 999.99 : 0);

    // Average hold hours
    $r = $conn->query("SELECT AVG(hold_hours) AS avg_hh FROM lm_trades WHERE status='closed'");
    $row = _lt_fetch_row($r);
    $stats['avg_hold_hours'] = ($row && $row['avg_hh'] !== null) ? round((float) $row['avg_hh'], 2) : 0;

    // By-algorithm breakdown
    $algo_stats = array();
    $r = $conn->query("SELECT algorithm_name,
        COUNT(*) AS total_trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) AS wins,
        SUM(CASE WHEN realized_pnl_usd <= 0 THEN 1 ELSE 0 END) AS losses,
        AVG(realized_pct) AS avg_return_pct,
        SUM(realized_pnl_usd) AS total_pnl_usd,
        AVG(hold_hours) AS avg_hold_hours
    FROM lm_trades WHERE status='closed' GROUP BY algorithm_name ORDER BY total_pnl_usd DESC");
    if ($r) {
        while ($arow = $r->fetch_assoc()) {
            $atotal = (int) $arow['total_trades'];
            $awins  = (int) $arow['wins'];
            $algo_stats[] = array(
                'algorithm_name'  => $arow['algorithm_name'],
                'total_trades'    => $atotal,
                'wins'            => $awins,
                'losses'          => (int) $arow['losses'],
                'win_rate'        => ($atotal > 0) ? round(($awins / $atotal) * 100, 2) : 0,
                'avg_return_pct'  => round((float) $arow['avg_return_pct'], 4),
                'total_pnl_usd'   => round((float) $arow['total_pnl_usd'], 2),
                'avg_hold_hours'  => round((float) $arow['avg_hold_hours'], 2)
            );
        }
        $r->free();
    }

    // Open positions summary
    $open_positions = _lt_fetch_all($conn->query("SELECT id, symbol, asset_class, direction, algorithm_name, entry_price, current_price, unrealized_pnl_usd, unrealized_pct, entry_time FROM lm_trades WHERE status='open' ORDER BY entry_time DESC"));

    // Latest snapshot
    $snapshot = _lt_fetch_row($conn->query("SELECT * FROM lm_snapshots ORDER BY id DESC LIMIT 1"));

    // Current portfolio value
    $portfolio_value = _lt_get_portfolio_value($conn);

    echo json_encode(array(
        'ok'              => true,
        'action'          => 'dashboard',
        'portfolio_value' => $portfolio_value,
        'stats'           => $stats,
        'by_algorithm'    => $algo_stats,
        'open_positions'  => $open_positions,
        'latest_snapshot' => $snapshot
    ));
    break;


// =====================================================================
// ACTION: history — Paginated trade history (public)
// =====================================================================
case 'history':
    $page      = isset($_GET['page'])        ? max(1, (int) $_GET['page']) : 1;
    $per_page  = isset($_GET['per_page'])     ? (int) $_GET['per_page'] : 20;
    if ($per_page < 1)   $per_page = 1;
    if ($per_page > 100) $per_page = 100;

    $asset_filter = isset($_GET['asset_class']) ? strtoupper(trim($_GET['asset_class'])) : '';
    $algo_filter  = isset($_GET['algorithm'])   ? trim($_GET['algorithm']) : '';

    $where = array("status = 'closed'");
    if ($asset_filter !== '') {
        $where[] = "asset_class = '" . $conn->real_escape_string($asset_filter) . "'";
    }
    if ($algo_filter !== '') {
        $where[] = "algorithm_name = '" . $conn->real_escape_string($algo_filter) . "'";
    }

    $where_sql = implode(' AND ', $where);

    // Count total
    $count_r = $conn->query("SELECT COUNT(*) AS cnt FROM lm_trades WHERE " . $where_sql);
    $count_row = _lt_fetch_row($count_r);
    $total = $count_row ? (int) $count_row['cnt'] : 0;

    $total_pages = ($per_page > 0) ? (int) ceil($total / $per_page) : 1;
    $offset = ($page - 1) * $per_page;

    $rows = _lt_fetch_all($conn->query("SELECT * FROM lm_trades WHERE " . $where_sql . " ORDER BY exit_time DESC LIMIT " . (int) $per_page . " OFFSET " . (int) $offset));

    echo json_encode(array(
        'ok'         => true,
        'action'     => 'history',
        'trades'     => $rows,
        'pagination' => array(
            'page'        => $page,
            'per_page'    => $per_page,
            'total'       => $total,
            'total_pages' => $total_pages
        )
    ));
    break;


// =====================================================================
// ACTION: auto_execute — Auto-enter positions from high-strength signals
// Bridges the gap between signal generation and trade execution.
// Only enters signals above a configurable strength threshold.
// =====================================================================
case 'auto_execute':
    _lt_check_admin(isset($_POST['key']) ? $_POST['key'] : (isset($_GET['key']) ? $_GET['key'] : ''));

    $min_strength = isset($_GET['min_strength']) ? (int) $_GET['min_strength'] : 70;
    $max_entries  = isset($_GET['max_entries'])  ? (int) $_GET['max_entries']  : 3;
    if ($min_strength < 30)  $min_strength = 30;
    if ($min_strength > 100) $min_strength = 100;
    if ($max_entries < 1)    $max_entries = 1;
    if ($max_entries > 5)    $max_entries = 5;

    $now = date('Y-m-d H:i:s');

    // Get active signals above threshold, sorted by strength descending
    $sig_sql = "SELECT * FROM lm_signals
        WHERE status = 'active'
        AND expires_at > '" . $conn->real_escape_string($now) . "'
        AND signal_strength >= " . (int) $min_strength . "
        ORDER BY signal_strength DESC
        LIMIT 20";
    $sig_res = $conn->query($sig_sql);

    $candidates = array();
    if ($sig_res) {
        while ($srow = $sig_res->fetch_assoc()) {
            $candidates[] = $srow;
        }
        $sig_res->free();
    }

    // Check current open positions count
    $open_r = $conn->query("SELECT COUNT(*) AS cnt FROM lm_trades WHERE status='open'");
    $open_row = _lt_fetch_row($open_r);
    $open_count = $open_row ? (int) $open_row['cnt'] : 0;

    // Check per-asset open counts
    $asset_counts = array('CRYPTO' => 0, 'STOCK' => 0, 'FOREX' => 0);
    $ac_r = $conn->query("SELECT asset_class, COUNT(*) AS cnt FROM lm_trades WHERE status='open' GROUP BY asset_class");
    if ($ac_r) {
        while ($ac_row = $ac_r->fetch_assoc()) {
            $asset_counts[$ac_row['asset_class']] = (int) $ac_row['cnt'];
        }
        $ac_r->free();
    }

    // Check circuit breaker
    $breaker_active = false;
    $breaker_r = $conn->query("SELECT id FROM lm_breaker_log WHERE active = 1 LIMIT 1");
    if ($breaker_r) {
        $breaker_active = ($breaker_r->num_rows > 0);
        $breaker_r->free();
    }

    // Get open symbols to prevent duplicate positions on same symbol
    $open_symbols = array();
    $os_r = $conn->query("SELECT CONCAT(symbol, '_', direction) AS sym_dir FROM lm_trades WHERE status='open'");
    if ($os_r) {
        while ($os_row = $os_r->fetch_assoc()) {
            $open_symbols[] = $os_row['sym_dir'];
        }
        $os_r->free();
    }

    $entered   = array();
    $skipped   = array();
    $portfolio_value = _lt_get_portfolio_value($conn);

    foreach ($candidates as $sig) {
        if (count($entered) >= $max_entries) break;
        if ($breaker_active) {
            $skipped[] = array('symbol' => $sig['symbol'], 'reason' => 'circuit_breaker');
            continue;
        }

        $sig_ac  = $sig['asset_class'];
        $sig_sym = $sig['symbol'];
        $sig_dir = (isset($sig['signal_type']) && ($sig['signal_type'] === 'SHORT' || $sig['signal_type'] === 'STRONG_SHORT')) ? 'SHORT' : 'LONG';

        // Skip if already have an open position on this symbol+direction
        $sym_dir_key = $sig_sym . '_' . $sig_dir;
        if (in_array($sym_dir_key, $open_symbols)) {
            $skipped[] = array('symbol' => $sig_sym, 'reason' => 'duplicate_position');
            continue;
        }

        // Global position limit
        if ($open_count >= $MAX_POSITIONS) {
            $skipped[] = array('symbol' => $sig_sym, 'reason' => 'max_positions');
            break;
        }

        // Per-asset limit
        if (isset($MAX_POSITIONS_PER_ASSET[$sig_ac])) {
            $asset_max = $MAX_POSITIONS_PER_ASSET[$sig_ac];
            $cur_asset_count = isset($asset_counts[$sig_ac]) ? $asset_counts[$sig_ac] : 0;
            if ($cur_asset_count >= $asset_max) {
                $skipped[] = array('symbol' => $sig_sym, 'reason' => 'max_' . strtolower($sig_ac) . '_positions');
                continue;
            }
        }

        // Crypto algorithm filter
        $sig_algo = isset($sig['algorithm_name']) ? $sig['algorithm_name'] : '';
        if ($sig_ac === 'CRYPTO' && $sig_algo !== '' && !in_array($sig_algo, $CRYPTO_PREFERRED_ALGOS)) {
            $skipped[] = array('symbol' => $sig_sym, 'reason' => 'algo_not_preferred_crypto');
            continue;
        }

        // Signal cooldown: skip symbols that were stopped out recently
        // Prevents revenge trading — 6h cooldown after a stop-loss exit
        if (_lt_check_cooldown($conn, $sig_sym, 6)) {
            $skipped[] = array('symbol' => $sig_sym, 'reason' => 'cooldown_after_stoploss');
            continue;
        }

        // Sector correlation guard: max 2 open positions per sector group
        // Prevents over-concentration in correlated assets (e.g., 3 tech stocks)
        if (isset($SECTOR_GROUPS[$sig_sym])) {
            $sig_sector = $SECTOR_GROUPS[$sig_sym];
            $sector_count = 0;
            $sec_r = $conn->query("SELECT symbol FROM lm_trades WHERE status='open'");
            if ($sec_r) {
                while ($sec_row = $sec_r->fetch_assoc()) {
                    $open_sym = $sec_row['symbol'];
                    if (isset($SECTOR_GROUPS[$open_sym]) && $SECTOR_GROUPS[$open_sym] === $sig_sector) {
                        $sector_count++;
                    }
                }
                $sec_r->free();
            }
            if ($sector_count >= $MAX_PER_SECTOR) {
                $skipped[] = array('symbol' => $sig_sym, 'reason' => 'sector_concentration_' . $sig_sector);
                continue;
            }
        }

        // Get current price from cache
        $safe_sym = $conn->real_escape_string($sig_sym);
        $safe_ac  = $conn->real_escape_string($sig_ac);
        $price_r  = $conn->query("SELECT price FROM lm_price_cache WHERE symbol = '" . $safe_sym . "' AND asset_class = '" . $safe_ac . "' ORDER BY last_updated DESC LIMIT 1");
        $price_row = _lt_fetch_row($price_r);
        if (!$price_row || (float) $price_row['price'] <= 0) {
            $skipped[] = array('symbol' => $sig_sym, 'reason' => 'no_price');
            continue;
        }
        $entry_price = (float) $price_row['price'];

        // TP/SL from signal
        $tp_pct  = isset($sig['target_tp_pct']) ? (float) $sig['target_tp_pct'] : 5;
        $sl_pct  = isset($sig['target_sl_pct']) ? (float) $sig['target_sl_pct'] : 3;
        $max_hold = isset($sig['max_hold_hours']) ? (int) $sig['max_hold_hours'] : 24;

        // Crypto TP floor
        if ($sig_ac === 'CRYPTO' && $tp_pct < $CRYPTO_MIN_TP_PCT) {
            $tp_pct = $CRYPTO_MIN_TP_PCT;
        }

        // Min hold time by asset class: prevents premature max-hold exits
        // Crypto: min 4h (24/7, fast moves), Forex: min 6h, Stock: min 12h
        $HOLD_FLOORS = array('CRYPTO' => 4, 'STOCK' => 12, 'FOREX' => 6);
        $hold_floor = isset($HOLD_FLOORS[$sig_ac]) ? $HOLD_FLOORS[$sig_ac] : 6;
        if ($max_hold < $hold_floor) {
            $max_hold = $hold_floor;
        }

        // Max hold cap: prevent algorithms from holding too long (Feb 12, 2026)
        // Challenger Bot was using 168h (7 days), blocking position slots for a week.
        $hold_cap = isset($MAX_HOLD_CAP[$sig_ac]) ? $MAX_HOLD_CAP[$sig_ac] : 72;
        if ($max_hold > $hold_cap) {
            $max_hold = $hold_cap;
        }

        // Per-asset SL floor: with 30-min tracking, tight SLs are unrealistic
        // Crypto 2%, Stock 1.5%, Forex 1% (same as enter action)
        $SL_FLOORS = array('CRYPTO' => 2.0, 'STOCK' => 1.5, 'FOREX' => 1.0);
        $sl_floor = isset($SL_FLOORS[$sig_ac]) ? $SL_FLOORS[$sig_ac] : 1.5;
        if ($sl_pct < $sl_floor) {
            $sl_pct = $sl_floor;
        }

        // R:R ratio enforcement: per-asset-class minimums (Feb 12, 2026)
        // Crypto keeps strict 1.5, stocks lowered to 1.2, forex to 1.0
        // Science: at 80% WR, R:R > 0.25 is profitable. Our top algos run 75-85%.
        $rr_ratio = ($sl_pct > 0) ? ($tp_pct / $sl_pct) : 0;
        $rr_min = isset($MIN_RR_RATIO[$sig_ac]) ? $MIN_RR_RATIO[$sig_ac] : 1.5;
        if ($rr_ratio < $rr_min) {
            $skipped[] = array('symbol' => $sig_sym, 'reason' => 'rr_ratio_too_low_' . round($rr_ratio, 2));
            continue;
        }

        // Position sizing: Python-computed (preferred) or PHP Half-Kelly fallback
        $python_pct = _lt_python_position_pct($conn, $sig_algo);
        if ($python_pct > 0) {
            $kelly_pct = $python_pct;
            $dd_scale = _lt_drawdown_scale($conn);
        } else {
            $vol_pct   = _lt_vol_adjusted_position_pct($conn, $sig_sym, $sig_ac);
            $kelly_pct = _lt_kelly_position_pct($conn, $sig_algo, $sig_ac, $vol_pct);
            $dd_scale  = _lt_drawdown_scale($conn);
        }
        $position_value = round($portfolio_value * ($kelly_pct / 100) * $dd_scale, 2);
        $units = $position_value / $entry_price;

        // Entry fees
        $entry_fee = 0;
        if ($sig_ac === 'CRYPTO') {
            $entry_fee = round($entry_price * $units * 0.002, 2);
        } elseif ($sig_ac === 'STOCK') {
            $shares = abs((int) $units);
            $entry_fee = max(1.99, $shares * 0.0099);
        }

        $entry_now = date('Y-m-d H:i:s');

        $conn->query("INSERT INTO lm_trades (
            asset_class, symbol, algorithm_name, signal_id, direction,
            entry_time, entry_price, position_size_units, position_value_usd,
            target_tp_pct, target_sl_pct, max_hold_hours,
            current_price, highest_price, lowest_price,
            status, fees_usd, created_at
        ) VALUES (
            '" . $safe_ac . "',
            '" . $safe_sym . "',
            '" . $conn->real_escape_string($sig_algo) . "',
            " . (int) $sig['id'] . ",
            '" . $conn->real_escape_string($sig_dir) . "',
            '" . $conn->real_escape_string($entry_now) . "',
            " . (float) $entry_price . ",
            " . (float) $units . ",
            " . (float) $position_value . ",
            " . (float) $tp_pct . ",
            " . (float) $sl_pct . ",
            " . (int) $max_hold . ",
            " . (float) $entry_price . ",
            " . (float) $entry_price . ",
            " . (float) $entry_price . ",
            'open',
            " . (float) $entry_fee . ",
            '" . $conn->real_escape_string($entry_now) . "'
        )");

        $new_id = $conn->insert_id;

        // Mark signal as executed
        $conn->query("UPDATE lm_signals SET status = 'executed' WHERE id = " . (int) $sig['id']);

        $entered[] = array(
            'trade_id'        => $new_id,
            'signal_id'       => (int) $sig['id'],
            'symbol'          => $sig_sym,
            'asset_class'     => $sig_ac,
            'direction'       => $sig_dir,
            'algorithm'       => $sig_algo,
            'signal_strength' => (int) $sig['signal_strength'],
            'entry_price'     => $entry_price,
            'position_value'  => $position_value,
            'tp_pct'          => $tp_pct,
            'sl_pct'          => $sl_pct,
            'max_hold_hours'  => $max_hold
        );

        $open_count++;
        if (isset($asset_counts[$sig_ac])) {
            $asset_counts[$sig_ac]++;
        }
        $open_symbols[] = $sym_dir_key;
    }

    echo json_encode(array(
        'ok'              => true,
        'action'          => 'auto_execute',
        'min_strength'    => $min_strength,
        'candidates'      => count($candidates),
        'entered'         => count($entered),
        'skipped'         => count($skipped),
        'positions_open'  => $open_count,
        'portfolio_value' => $portfolio_value,
        'entered_details' => $entered,
        'skipped_details' => array_slice($skipped, 0, 10)
    ));
    break;


// =====================================================================
// ACTION: recalculate_kelly — Bulk recompute Kelly fractions for all algos
// Run periodically or after importing historical trade data.
// =====================================================================
case 'recalculate_kelly':
    _lt_check_admin(isset($_POST['key']) ? $_POST['key'] : (isset($_GET['key']) ? $_GET['key'] : ''));

    // Get all unique algorithm+asset_class combos from closed trades
    $combos = array();
    $r = $conn->query("SELECT DISTINCT algorithm_name, asset_class FROM lm_trades WHERE status='closed' AND algorithm_name != ''");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $combos[] = $row;
        }
        $r->free();
    }

    $results = array();
    foreach ($combos as $combo) {
        _lt_update_kelly($conn, $combo['algorithm_name'], $combo['asset_class']);
        $results[] = $combo['algorithm_name'] . '/' . $combo['asset_class'];
    }

    // Read back computed Kelly fractions
    $kelly_data = array();
    $kr = $conn->query("SELECT algorithm_name, asset_class, win_rate, avg_win_pct, avg_loss_pct, full_kelly, half_kelly, sample_size, updated_at FROM lm_kelly_fractions ORDER BY half_kelly DESC");
    if ($kr) {
        while ($krow = $kr->fetch_assoc()) {
            $kelly_data[] = $krow;
        }
        $kr->free();
    }

    echo json_encode(array(
        'ok'          => true,
        'action'      => 'recalculate_kelly',
        'recomputed'  => count($combos),
        'algorithms'  => $results,
        'kelly_data'  => $kelly_data
    ));
    break;


// =====================================================================
// Unknown or missing action
// =====================================================================
default:
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array(
        'ok'    => false,
        'error' => 'Unknown or missing action. Valid: enter, track, close, positions, dashboard, history, auto_execute, recalculate_kelly'
    ));
    break;
}

$conn->close();
?>
