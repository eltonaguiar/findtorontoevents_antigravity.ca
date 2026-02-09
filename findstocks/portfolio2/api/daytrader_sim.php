<?php
/**
 * $500/Day Daytrader Simulation Engine
 * Simulates a daytrader starting with $500 each day, using top picks.
 * Compares original algo params vs self-learned revised params.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   dashboard       — Full dashboard data (equity curve, stats, recent trades)
 *   simulate_day    — Run simulation for a specific date
 *   backfill        — Simulate all historical trading days
 *   today           — Today's picks preview
 *
 * Usage:
 *   GET .../daytrader_sim.php?action=dashboard
 *   GET .../daytrader_sim.php?action=simulate_day&date=2026-02-07&key=stocksrefresh2026
 *   GET .../daytrader_sim.php?action=backfill&key=stocksrefresh2026
 *   GET .../daytrader_sim.php?action=today
 */
require_once dirname(__FILE__) . '/db_connect.php';

// Auto-create tables
$conn->query("CREATE TABLE IF NOT EXISTS daytrader_sim_days (
    id INT AUTO_INCREMENT PRIMARY KEY, sim_date DATE NOT NULL, budget DECIMAL(12,2) NOT NULL DEFAULT 500.00,
    picks_used INT NOT NULL DEFAULT 0, total_invested DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_pnl DECIMAL(12,2) NOT NULL DEFAULT 0, return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    wins INT NOT NULL DEFAULT 0, losses INT NOT NULL DEFAULT 0,
    best_pick_ticker VARCHAR(10) NOT NULL DEFAULT '', best_pick_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    worst_pick_ticker VARCHAR(10) NOT NULL DEFAULT '', worst_pick_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    algo_version VARCHAR(20) NOT NULL DEFAULT 'original', cumulative_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_date_version (sim_date, algo_version), KEY idx_date (sim_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");
$conn->query("CREATE TABLE IF NOT EXISTS daytrader_sim_trades (
    id INT AUTO_INCREMENT PRIMARY KEY, sim_date DATE NOT NULL, ticker VARCHAR(10) NOT NULL,
    strategy_name VARCHAR(100) NOT NULL DEFAULT '', source_table VARCHAR(30) NOT NULL DEFAULT '',
    entry_price DECIMAL(12,4) NOT NULL DEFAULT 0, exit_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    shares INT NOT NULL DEFAULT 0, invested DECIMAL(12,2) NOT NULL DEFAULT 0,
    pnl DECIMAL(12,2) NOT NULL DEFAULT 0, return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(50) NOT NULL DEFAULT '', algo_version VARCHAR(20) NOT NULL DEFAULT 'original',
    created_at DATETIME NOT NULL,
    KEY idx_date (sim_date), KEY idx_ticker (ticker), KEY idx_version (algo_version)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? trim($_GET['action']) : 'dashboard';
$response = array('ok' => true, 'action' => $action);
$admin_key = 'stocksrefresh2026';
$is_admin = (isset($_GET['key']) && $_GET['key'] === $admin_key);

$BUDGET = 500.00;
$MAX_POSITIONS = 5;

// ─── Simulate one day for one algo version ───
function _sim_day($conn, $sim_date, $algo_version, $budget, $max_pos) {
    $safe_date = $conn->real_escape_string($sim_date);

    // Get top day-trade picks (from miracle_picks2 + miracle_picks3, short hold)
    $picks = array();

    // miracle_picks3 first (Claude-generated, has direction field)
    $r3 = $conn->query("SELECT ticker, strategy_name, entry_price, score, stop_loss_pct, take_profit_pct,
                                'miracle_picks3' AS source_table
                         FROM miracle_picks3
                         WHERE scan_date = '$safe_date' AND entry_price > 0 AND score >= 50
                         ORDER BY score DESC LIMIT 10");
    if ($r3) { while ($row = $r3->fetch_assoc()) $picks[] = $row; }

    // miracle_picks2
    $r2 = $conn->query("SELECT ticker, strategy_name, entry_price, score, stop_loss_pct, take_profit_pct,
                                'miracle_picks2' AS source_table
                         FROM miracle_picks2
                         WHERE scan_date = '$safe_date' AND entry_price > 0 AND score >= 50
                         ORDER BY score DESC LIMIT 10");
    if ($r2) { while ($row = $r2->fetch_assoc()) $picks[] = $row; }

    // Deduplicate by ticker (keep highest score)
    $seen = array();
    $unique_picks = array();
    foreach ($picks as $p) {
        $t = $p['ticker'];
        if (!isset($seen[$t]) || (int)$p['score'] > $seen[$t]) {
            $seen[$t] = (int)$p['score'];
            $unique_picks[$t] = $p;
        }
    }

    // Sort by score desc, take top N
    usort($unique_picks, create_function('$a,$b', 'return (int)$b["score"] - (int)$a["score"];'));
    $unique_picks = array_slice($unique_picks, 0, $max_pos);

    if (count($unique_picks) === 0) {
        return array('picks_used' => 0, 'total_pnl' => 0, 'trades' => array());
    }

    // Position sizing: Kelly version uses fractional Kelly, others use equal weight
    $per_position = $budget / count($unique_picks);
    $trades = array();
    $total_pnl = 0;
    $wins = 0; $losses = 0;
    $best_pct = -999; $best_ticker = '';
    $worst_pct = 999; $worst_ticker = '';

    // For each pick, look at next trading day's price to resolve
    foreach ($unique_picks as $pick) {
        $ticker = $pick['ticker'];
        $safe_t = $conn->real_escape_string($ticker);
        $entry = (float)$pick['entry_price'];

        // Get the TP/SL percentages based on algo_version
        if ($algo_version === 'revised' || $algo_version === 'kelly') {
            // Use current (learned) strategy params
            $tp_pct = (float)$pick['take_profit_pct'];
            $sl_pct = (float)$pick['stop_loss_pct'];
        } else {
            // Original defaults: 5% TP, 3% SL (standard day trade params)
            $tp_pct = 5.0;
            $sl_pct = 3.0;
        }
        if ($tp_pct <= 0) $tp_pct = 5.0;
        if ($sl_pct <= 0) $sl_pct = 3.0;

        // Kelly position sizing: compute per-strategy Kelly fraction
        if ($algo_version === 'kelly') {
            $strat_name = isset($pick['strategy_name']) ? $pick['strategy_name'] : '';
            $src = isset($pick['source_table']) ? $pick['source_table'] : 'miracle_picks3';
            $safe_strat = $conn->real_escape_string($strat_name);
            $safe_src = $conn->real_escape_string($src);
            $kr = $conn->query("SELECT recommended_pct FROM kelly_sizing_log
                                WHERE source_table='$safe_src' AND algorithm_name='$safe_strat'
                                ORDER BY calc_date DESC LIMIT 1");
            if ($kr && $kr->num_rows > 0) {
                $krow = $kr->fetch_assoc();
                $kelly_frac = (float)$krow['recommended_pct'];
                if ($kelly_frac > 0) {
                    $per_position = $budget * $kelly_frac;
                    // Cap at 20% of budget
                    if ($per_position > $budget * 0.20) $per_position = $budget * 0.20;
                    // Floor at 5% of budget
                    if ($per_position < $budget * 0.05) $per_position = $budget * 0.05;
                }
            }
        }

        $tp_price = $entry * (1 + $tp_pct / 100);
        $sl_price = $entry * (1 - $sl_pct / 100);

        // Get next day's OHLC data
        $pr = $conn->query("SELECT high_price, low_price, close_price FROM daily_prices
                            WHERE ticker='$safe_t' AND trade_date > '$safe_date'
                            ORDER BY trade_date ASC LIMIT 1");
        $exit_price = $entry; // default: no change
        $exit_reason = 'no_data';

        if ($pr && $pr->num_rows > 0) {
            $day = $pr->fetch_assoc();
            $high = (float)$day['high_price'];
            $low = (float)$day['low_price'];
            $close = (float)$day['close_price'];

            // Check SL hit first (worse case for daytrader)
            if ($low <= $sl_price) {
                $exit_price = $sl_price;
                $exit_reason = 'stop_loss';
            } elseif ($high >= $tp_price) {
                $exit_price = $tp_price;
                $exit_reason = 'take_profit';
            } else {
                // Close at EOD
                $exit_price = $close;
                $exit_reason = 'eod_close';
            }
        }

        $shares = ($entry > 0) ? max(1, (int)floor($per_position / $entry)) : 0;
        $invested = $shares * $entry;
        $pnl = $shares * ($exit_price - $entry);
        $ret_pct = ($entry > 0) ? round(($exit_price - $entry) / $entry * 100, 4) : 0;

        if ($pnl > 0) $wins++; else $losses++;
        $total_pnl += $pnl;

        if ($ret_pct > $best_pct) { $best_pct = $ret_pct; $best_ticker = $ticker; }
        if ($ret_pct < $worst_pct) { $worst_pct = $ret_pct; $worst_ticker = $ticker; }

        $trades[] = array(
            'ticker' => $ticker,
            'strategy' => $pick['strategy_name'],
            'source' => $pick['source_table'],
            'entry_price' => $entry,
            'exit_price' => round($exit_price, 4),
            'shares' => $shares,
            'invested' => round($invested, 2),
            'pnl' => round($pnl, 2),
            'return_pct' => $ret_pct,
            'exit_reason' => $exit_reason,
            'tp_pct' => $tp_pct,
            'sl_pct' => $sl_pct
        );
    }

    return array(
        'picks_used' => count($unique_picks),
        'total_invested' => round(array_sum(array_map(create_function('$t', 'return $t["invested"];'), $trades)), 2),
        'total_pnl' => round($total_pnl, 2),
        'return_pct' => ($budget > 0) ? round($total_pnl / $budget * 100, 4) : 0,
        'wins' => $wins,
        'losses' => $losses,
        'best_ticker' => $best_ticker,
        'best_pct' => $best_pct,
        'worst_ticker' => $worst_ticker,
        'worst_pct' => $worst_pct,
        'trades' => $trades
    );
}

// ═══════════════════════════════════════════
// DASHBOARD — Full stats
// ═══════════════════════════════════════════
if ($action === 'dashboard') {
    // Get all sim days
    $original_days = array();
    $revised_days = array();

    $r = $conn->query("SELECT * FROM daytrader_sim_days WHERE algo_version='original' ORDER BY sim_date ASC");
    if ($r) { while ($row = $r->fetch_assoc()) $original_days[] = $row; }
    $r = $conn->query("SELECT * FROM daytrader_sim_days WHERE algo_version='revised' ORDER BY sim_date ASC");
    if ($r) { while ($row = $r->fetch_assoc()) $revised_days[] = $row; }
    $kelly_days = array();
    $r = $conn->query("SELECT * FROM daytrader_sim_days WHERE algo_version='kelly' ORDER BY sim_date ASC");
    if ($r) { while ($row = $r->fetch_assoc()) $kelly_days[] = $row; }

    // Compute aggregate stats
    $stats = array();
    foreach (array('original' => $original_days, 'revised' => $revised_days, 'kelly' => $kelly_days) as $ver => $days) {
        $total_pnl = 0; $total_wins = 0; $total_losses = 0;
        $total_days = count($days); $profitable_days = 0;
        $max_dd = 0; $peak = 0; $returns = array();

        foreach ($days as $d) {
            $pnl = (float)$d['total_pnl'];
            $total_pnl += $pnl;
            $total_wins += (int)$d['wins'];
            $total_losses += (int)$d['losses'];
            if ($pnl > 0) $profitable_days++;
            $returns[] = (float)$d['return_pct'];
            if ($total_pnl > $peak) $peak = $total_pnl;
            $dd = ($peak > 0) ? ($peak - $total_pnl) / $peak * 100 : 0;
            if ($dd > $max_dd) $max_dd = $dd;
        }

        $total_trades = $total_wins + $total_losses;
        $win_rate = ($total_trades > 0) ? round($total_wins / $total_trades * 100, 2) : 0;
        $avg_daily_pnl = ($total_days > 0) ? round($total_pnl / $total_days, 2) : 0;

        // Sharpe (daily)
        $sharpe = 0;
        if (count($returns) > 1) {
            $mean = array_sum($returns) / count($returns);
            $var = 0;
            foreach ($returns as $rv) $var += ($rv - $mean) * ($rv - $mean);
            $std = sqrt($var / count($returns));
            if ($std > 0) $sharpe = round($mean / $std, 4);
        }

        $stats[$ver] = array(
            'total_days' => $total_days,
            'total_trades' => $total_trades,
            'total_pnl' => round($total_pnl, 2),
            'avg_daily_pnl' => $avg_daily_pnl,
            'win_rate' => $win_rate,
            'profitable_days' => $profitable_days,
            'profitable_day_rate' => ($total_days > 0) ? round($profitable_days / $total_days * 100, 2) : 0,
            'max_drawdown_pct' => round($max_dd, 2),
            'sharpe_ratio' => $sharpe
        );
    }

    // Equity curve data
    $equity_original = array();
    $cum = 0;
    foreach ($original_days as $d) {
        $cum += (float)$d['total_pnl'];
        $equity_original[] = array('date' => $d['sim_date'], 'equity' => round($cum, 2));
    }
    $equity_revised = array();
    $cum = 0;
    foreach ($revised_days as $d) {
        $cum += (float)$d['total_pnl'];
        $equity_revised[] = array('date' => $d['sim_date'], 'equity' => round($cum, 2));
    }

    // Recent trades
    $recent = array();
    $r = $conn->query("SELECT * FROM daytrader_sim_trades ORDER BY sim_date DESC, id DESC LIMIT 50");
    if ($r) { while ($row = $r->fetch_assoc()) $recent[] = $row; }

    $response['stats'] = $stats;
    $response['equity_original'] = $equity_original;
    $response['equity_revised'] = $equity_revised;
    $response['recent_trades'] = $recent;
    $response['budget_per_day'] = $BUDGET;
    $response['max_positions'] = $MAX_POSITIONS;
    $response['generated_at'] = date('Y-m-d H:i:s');
    echo json_encode($response);

// ═══════════════════════════════════════════
// SIMULATE DAY — Run sim for a specific date
// ═══════════════════════════════════════════
} elseif ($action === 'simulate_day') {
    if (!$is_admin) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Admin key required'));
        $conn->close(); exit;
    }

    $date = isset($_GET['date']) ? trim($_GET['date']) : date('Y-m-d');
    $safe_date = $conn->real_escape_string($date);
    $now = date('Y-m-d H:i:s');

    $results = array();
    foreach (array('original', 'revised', 'kelly') as $version) {
        $sim = _sim_day($conn, $date, $version, $BUDGET, $MAX_POSITIONS);

        if ($sim['picks_used'] > 0) {
            // Get cumulative PnL
            $cum_r = $conn->query("SELECT SUM(total_pnl) as cum FROM daytrader_sim_days WHERE algo_version='" . $conn->real_escape_string($version) . "' AND sim_date < '$safe_date'");
            $prev_cum = 0;
            if ($cum_r && $cum_r->num_rows > 0) { $cr = $cum_r->fetch_assoc(); $prev_cum = (float)$cr['cum']; }
            $new_cum = $prev_cum + $sim['total_pnl'];

            // Insert/update day record
            $conn->query("DELETE FROM daytrader_sim_days WHERE sim_date='$safe_date' AND algo_version='$version'");
            $conn->query("INSERT INTO daytrader_sim_days (sim_date, budget, picks_used, total_invested, total_pnl, return_pct, wins, losses, best_pick_ticker, best_pick_pct, worst_pick_ticker, worst_pick_pct, algo_version, cumulative_pnl, created_at)
                          VALUES ('$safe_date', $BUDGET, " . $sim['picks_used'] . ", " . $sim['total_invested'] . ", " . $sim['total_pnl'] . ", " . $sim['return_pct'] . ", " . $sim['wins'] . ", " . $sim['losses'] . ", '" . $conn->real_escape_string($sim['best_ticker']) . "', " . $sim['best_pct'] . ", '" . $conn->real_escape_string($sim['worst_ticker']) . "', " . $sim['worst_pct'] . ", '$version', $new_cum, '$now')");

            // Insert trade records
            $conn->query("DELETE FROM daytrader_sim_trades WHERE sim_date='$safe_date' AND algo_version='$version'");
            foreach ($sim['trades'] as $t) {
                $conn->query("INSERT INTO daytrader_sim_trades (sim_date, ticker, strategy_name, source_table, entry_price, exit_price, shares, invested, pnl, return_pct, exit_reason, algo_version, created_at)
                              VALUES ('$safe_date', '" . $conn->real_escape_string($t['ticker']) . "', '" . $conn->real_escape_string($t['strategy']) . "', '" . $conn->real_escape_string($t['source']) . "', " . $t['entry_price'] . ", " . $t['exit_price'] . ", " . $t['shares'] . ", " . $t['invested'] . ", " . $t['pnl'] . ", " . $t['return_pct'] . ", '" . $conn->real_escape_string($t['exit_reason']) . "', '$version', '$now')");
            }
        }

        $results[$version] = $sim;
    }

    $response['date'] = $date;
    $response['results'] = $results;
    echo json_encode($response);

// ═══════════════════════════════════════════
// BACKFILL — Simulate all historical days
// ═══════════════════════════════════════════
} elseif ($action === 'backfill') {
    if (!$is_admin) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Admin key required'));
        $conn->close(); exit;
    }

    // Get all unique scan dates that have picks
    $dates = array();
    $r = $conn->query("SELECT DISTINCT scan_date FROM miracle_picks3 WHERE entry_price > 0 ORDER BY scan_date ASC");
    if ($r) { while ($row = $r->fetch_assoc()) $dates[] = $row['scan_date']; }
    $r = $conn->query("SELECT DISTINCT scan_date FROM miracle_picks2 WHERE entry_price > 0 ORDER BY scan_date ASC");
    if ($r) { while ($row = $r->fetch_assoc()) { if (!in_array($row['scan_date'], $dates)) $dates[] = $row['scan_date']; } }
    sort($dates);

    $simulated = 0;
    $skipped = 0;
    $now = date('Y-m-d H:i:s');

    foreach ($dates as $date) {
        $safe_date = $conn->real_escape_string($date);
        // Check if already simulated
        $check = $conn->query("SELECT id FROM daytrader_sim_days WHERE sim_date='$safe_date' AND algo_version='original' LIMIT 1");
        if ($check && $check->num_rows > 0) { $skipped++; continue; }

        foreach (array('original', 'revised', 'kelly') as $version) {
            $sim = _sim_day($conn, $date, $version, $BUDGET, $MAX_POSITIONS);
            if ($sim['picks_used'] === 0) continue;

            // Cumulative
            $cum_r = $conn->query("SELECT SUM(total_pnl) as cum FROM daytrader_sim_days WHERE algo_version='$version' AND sim_date < '$safe_date'");
            $prev_cum = 0; if ($cum_r && $cum_r->num_rows > 0) { $_tmp = $cum_r->fetch_assoc(); $prev_cum = (float)$_tmp['cum']; }

            $conn->query("INSERT INTO daytrader_sim_days (sim_date, budget, picks_used, total_invested, total_pnl, return_pct, wins, losses, best_pick_ticker, best_pick_pct, worst_pick_ticker, worst_pick_pct, algo_version, cumulative_pnl, created_at)
                          VALUES ('$safe_date', $BUDGET, " . $sim['picks_used'] . ", " . $sim['total_invested'] . ", " . $sim['total_pnl'] . ", " . $sim['return_pct'] . ", " . $sim['wins'] . ", " . $sim['losses'] . ", '" . $conn->real_escape_string($sim['best_ticker']) . "', " . $sim['best_pct'] . ", '" . $conn->real_escape_string($sim['worst_ticker']) . "', " . $sim['worst_pct'] . ", '$version', " . ($prev_cum + $sim['total_pnl']) . ", '$now')");

            foreach ($sim['trades'] as $t) {
                $conn->query("INSERT INTO daytrader_sim_trades (sim_date, ticker, strategy_name, source_table, entry_price, exit_price, shares, invested, pnl, return_pct, exit_reason, algo_version, created_at)
                              VALUES ('$safe_date', '" . $conn->real_escape_string($t['ticker']) . "', '" . $conn->real_escape_string($t['strategy']) . "', '" . $conn->real_escape_string($t['source']) . "', " . $t['entry_price'] . ", " . $t['exit_price'] . ", " . $t['shares'] . ", " . $t['invested'] . ", " . $t['pnl'] . ", " . $t['return_pct'] . ", '" . $conn->real_escape_string($t['exit_reason']) . "', '$version', '$now')");
            }
        }
        $simulated++;
    }

    $response['simulated_days'] = $simulated;
    $response['skipped_days'] = $skipped;
    $response['total_dates'] = count($dates);
    echo json_encode($response);

// ═══════════════════════════════════════════
// TODAY — Preview today's picks
// ═══════════════════════════════════════════
} elseif ($action === 'today') {
    $today = date('Y-m-d');
    $safe = $conn->real_escape_string($today);

    $picks = array();
    $r = $conn->query("SELECT ticker, strategy_name, entry_price, score, stop_loss_pct, take_profit_pct, confidence, 'miracle_picks3' AS src
                       FROM miracle_picks3 WHERE scan_date='$safe' AND entry_price > 0 ORDER BY score DESC LIMIT 10");
    if ($r) { while ($row = $r->fetch_assoc()) $picks[] = $row; }
    $r = $conn->query("SELECT ticker, strategy_name, entry_price, score, stop_loss_pct, take_profit_pct, confidence, 'miracle_picks2' AS src
                       FROM miracle_picks2 WHERE scan_date='$safe' AND entry_price > 0 ORDER BY score DESC LIMIT 10");
    if ($r) { while ($row = $r->fetch_assoc()) $picks[] = $row; }

    // Deduplicate
    $seen = array();
    $unique = array();
    foreach ($picks as $p) {
        if (!isset($seen[$p['ticker']])) { $seen[$p['ticker']] = true; $unique[] = $p; }
    }
    $unique = array_slice($unique, 0, $MAX_POSITIONS);

    $per_pos = (count($unique) > 0) ? $BUDGET / count($unique) : 0;
    foreach ($unique as &$p) {
        $ep = (float)$p['entry_price'];
        $p['shares'] = ($ep > 0) ? max(1, (int)floor($per_pos / $ep)) : 0;
        $p['allocated'] = round($p['shares'] * $ep, 2);
    }
    unset($p);

    $response['date'] = $today;
    $response['picks'] = $unique;
    $response['budget'] = $BUDGET;
    $response['per_position'] = round($per_pos, 2);
    echo json_encode($response);

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action. Use: dashboard, simulate_day, backfill, today';
    echo json_encode($response);
}

$conn->close();
?>
