<?php
/**
 * Kelly Criterion Position Sizing API
 * Calculates mathematically optimal position sizes based on each algorithm's
 * win rate and risk/reward ratio. Uses quarter-Kelly for conservative sizing.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   calculate  — Compute Kelly fraction for a specific algorithm
 *   portfolio  — Kelly-weighted position sizes for current top picks
 *   all        — Kelly fractions for all algorithms
 *   history    — Track Kelly recommendations over time
 *
 * Usage:
 *   GET .../kelly_sizing.php?action=calculate&source=stock_picks&algorithm=CAN+SLIM
 *   GET .../kelly_sizing.php?action=portfolio
 *   GET .../kelly_sizing.php?action=all
 *   GET .../kelly_sizing.php?action=history&algorithm=CAN+SLIM
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'all';
$response = array('ok' => true, 'action' => $action);
$admin_key = 'stocksrefresh2026';
$is_admin = (isset($_GET['key']) && $_GET['key'] === $admin_key);

// ═══════════════════════════════════════════════
// Auto-create table
// ═══════════════════════════════════════════════
$conn->query("CREATE TABLE IF NOT EXISTS kelly_sizing_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_table VARCHAR(30) NOT NULL DEFAULT 'stock_picks',
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    calc_date DATE NOT NULL,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_win_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_loss_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    full_kelly DECIMAL(8,4) NOT NULL DEFAULT 0,
    half_kelly DECIMAL(8,4) NOT NULL DEFAULT 0,
    quarter_kelly DECIMAL(8,4) NOT NULL DEFAULT 0,
    recommended_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    trades_used INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_algo_date (source_table, algorithm_name, calc_date),
    KEY idx_date (calc_date),
    KEY idx_algo (algorithm_name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ═══════════════════════════════════════════════
// Core Kelly Formula
// ═══════════════════════════════════════════════
// f* = (p * b - q) / b
// where p = win probability, q = 1-p, b = avg_win / avg_loss
function _kelly_fraction($win_rate_pct, $avg_win_pct, $avg_loss_pct) {
    $p = $win_rate_pct / 100;
    $q = 1 - $p;
    if ($p <= 0 || $p >= 1) return array('full' => 0, 'half' => 0, 'quarter' => 0, 'recommended' => 0);

    $avg_loss_abs = abs($avg_loss_pct);
    if ($avg_loss_abs <= 0) $avg_loss_abs = 0.01; // prevent division by zero
    $b = $avg_win_pct / $avg_loss_abs; // payoff ratio

    $full_kelly = ($p * $b - $q) / $b;

    // Kelly can be negative (meaning don't bet). Clamp to 0.
    if ($full_kelly < 0) $full_kelly = 0;
    // Cap at 25% max position size
    if ($full_kelly > 0.25) $full_kelly = 0.25;

    $half = round($full_kelly * 0.5, 4);
    $quarter = round($full_kelly * 0.25, 4);

    // Recommended = quarter-Kelly (conservative, avoids ruin)
    $recommended = $quarter;

    // Minimum floor: if Kelly says bet, at least 2% of portfolio
    if ($full_kelly > 0 && $recommended < 0.02) $recommended = 0.02;
    // Maximum cap: never more than 20% of portfolio
    if ($recommended > 0.20) $recommended = 0.20;

    return array(
        'full' => round($full_kelly, 4),
        'half' => $half,
        'quarter' => $quarter,
        'recommended' => round($recommended, 4),
        'payoff_ratio' => round($b, 4),
        'edge' => round(($p * $b - $q), 4) // positive = we have an edge
    );
}

// ═══════════════════════════════════════════════
// Helper: Get algo performance stats from rolling_perf or direct query
// ═══════════════════════════════════════════════
function _kelly_get_stats($conn, $source, $algo) {
    $safe_src = $conn->real_escape_string($source);
    $safe_algo = $conn->real_escape_string($algo);

    // Try rolling_perf first (most recent)
    $rp = $conn->query("SELECT win_rate, avg_win_pct, avg_loss_pct, resolved_picks
                         FROM algorithm_rolling_perf
                         WHERE source_table='$safe_src' AND algorithm_name='$safe_algo' AND period='30d'
                         ORDER BY calc_date DESC LIMIT 1");
    if ($rp && $rp->num_rows > 0) {
        $row = $rp->fetch_assoc();
        if ((int)$row['resolved_picks'] >= 5) {
            return array(
                'win_rate' => (float)$row['win_rate'],
                'avg_win' => (float)$row['avg_win_pct'],
                'avg_loss' => (float)$row['avg_loss_pct'],
                'trades' => (int)$row['resolved_picks'],
                'data_source' => 'rolling_30d'
            );
        }
    }

    // Fallback: compute from raw picks
    if ($source === 'stock_picks') {
        $res = $conn->query("SELECT sp.entry_price, sp.pick_date, sp.ticker
                             FROM stock_picks sp WHERE sp.algorithm_name='$safe_algo' AND sp.entry_price > 0
                             ORDER BY sp.pick_date DESC LIMIT 100");
        if (!$res || $res->num_rows === 0) return null;

        $wins = 0;
        $losses = 0;
        $total_gain = 0;
        $total_loss_amt = 0;
        while ($pick = $res->fetch_assoc()) {
            $entry = (float)$pick['entry_price'];
            $st = $conn->real_escape_string($pick['ticker']);
            $sd = $conn->real_escape_string($pick['pick_date']);
            $pr = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$st' AND trade_date > '$sd' ORDER BY trade_date DESC LIMIT 1");
            if ($pr && $pr->num_rows > 0) {
                $latest = (float)$pr->fetch_assoc();
                if (is_array($latest)) $latest = (float)$latest['close_price'];
                if ($latest > 0 && $entry > 0) {
                    $ret = (($latest - $entry) / $entry) * 100;
                    if ($ret > 0) { $wins++; $total_gain += $ret; }
                    else { $losses++; $total_loss_amt += abs($ret); }
                }
            }
        }

        $total = $wins + $losses;
        if ($total < 3) return null;
        return array(
            'win_rate' => round($wins / $total * 100, 2),
            'avg_win' => ($wins > 0) ? round($total_gain / $wins, 4) : 0,
            'avg_loss' => ($losses > 0) ? round($total_loss_amt / $losses, 4) : 0,
            'trades' => $total,
            'data_source' => 'direct_query'
        );
    } else {
        $table = ($source === 'miracle_picks3') ? 'miracle_picks3' : 'miracle_picks2';
        $res = $conn->query("SELECT outcome, outcome_pct FROM $table
                             WHERE strategy_name='$safe_algo' AND outcome IN ('won','lost') AND entry_price > 0
                             ORDER BY scan_date DESC LIMIT 100");
        if (!$res || $res->num_rows === 0) return null;

        $wins = 0;
        $losses = 0;
        $total_gain = 0;
        $total_loss_amt = 0;
        while ($row = $res->fetch_assoc()) {
            $pct = (float)$row['outcome_pct'];
            if ($row['outcome'] === 'won') { $wins++; $total_gain += abs($pct); }
            else { $losses++; $total_loss_amt += abs($pct); }
        }

        $total = $wins + $losses;
        if ($total < 3) return null;
        return array(
            'win_rate' => round($wins / $total * 100, 2),
            'avg_win' => ($wins > 0) ? round($total_gain / $wins, 4) : 0,
            'avg_loss' => ($losses > 0) ? round($total_loss_amt / $losses, 4) : 0,
            'trades' => $total,
            'data_source' => 'direct_query'
        );
    }
}

// ═══════════════════════════════════════════════
// ACTION: calculate — Kelly for one algorithm
// ═══════════════════════════════════════════════
if ($action === 'calculate') {
    $source = isset($_GET['source']) ? trim($_GET['source']) : 'stock_picks';
    $algorithm = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';

    if ($algorithm === '') {
        $response['ok'] = false;
        $response['error'] = 'Missing algorithm parameter';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $stats = _kelly_get_stats($conn, $source, $algorithm);
    if (!$stats) {
        $response['ok'] = false;
        $response['error'] = 'Insufficient data for ' . $algorithm;
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $kelly = _kelly_fraction($stats['win_rate'], $stats['avg_win'], $stats['avg_loss']);

    $response['source'] = $source;
    $response['algorithm'] = $algorithm;
    $response['stats'] = $stats;
    $response['kelly'] = $kelly;
    $response['interpretation'] = ($kelly['edge'] > 0)
        ? 'Positive edge detected. Recommended position size: ' . round($kelly['recommended'] * 100, 1) . '% of portfolio per trade.'
        : 'No edge detected (Kelly <= 0). This algorithm should not be allocated capital.';

} elseif ($action === 'all') {
    // ═══════════════════════════════════════════════
    // ACTION: all — Kelly fractions for all algorithms
    // ═══════════════════════════════════════════════
    $results = array();
    $today = date('Y-m-d');
    $now = date('Y-m-d H:i:s');

    // stock_picks
    $ar = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE entry_price > 0");
    if ($ar) {
        while ($row = $ar->fetch_assoc()) {
            $algo = $row['algorithm_name'];
            $stats = _kelly_get_stats($conn, 'stock_picks', $algo);
            if (!$stats) continue;

            $kelly = _kelly_fraction($stats['win_rate'], $stats['avg_win'], $stats['avg_loss']);
            $entry = array(
                'source' => 'stock_picks',
                'algorithm' => $algo,
                'win_rate' => $stats['win_rate'],
                'avg_win' => $stats['avg_win'],
                'avg_loss' => $stats['avg_loss'],
                'trades' => $stats['trades'],
                'full_kelly' => $kelly['full'],
                'recommended_pct' => round($kelly['recommended'] * 100, 1),
                'edge' => $kelly['edge'],
                'has_edge' => ($kelly['edge'] > 0)
            );
            $results[] = $entry;

            // Store to log if admin
            if ($is_admin) {
                $safe_algo = $conn->real_escape_string($algo);
                $conn->query("REPLACE INTO kelly_sizing_log
                    (source_table, algorithm_name, calc_date, win_rate, avg_win_pct, avg_loss_pct,
                     full_kelly, half_kelly, quarter_kelly, recommended_pct, trades_used, created_at)
                    VALUES ('stock_picks', '$safe_algo', '$today',
                    {$stats['win_rate']}, {$stats['avg_win']}, {$stats['avg_loss']},
                    {$kelly['full']}, {$kelly['half']}, {$kelly['quarter']}, {$kelly['recommended']},
                    {$stats['trades']}, '$now')");
            }
        }
    }

    // miracle_picks3
    $sr = $conn->query("SELECT DISTINCT strategy_name FROM miracle_picks3 WHERE entry_price > 0 AND outcome IN ('won','lost')");
    if ($sr) {
        while ($row = $sr->fetch_assoc()) {
            $strat = $row['strategy_name'];
            $stats = _kelly_get_stats($conn, 'miracle_picks3', $strat);
            if (!$stats) continue;

            $kelly = _kelly_fraction($stats['win_rate'], $stats['avg_win'], $stats['avg_loss']);
            $results[] = array(
                'source' => 'miracle_picks3',
                'algorithm' => $strat,
                'win_rate' => $stats['win_rate'],
                'avg_win' => $stats['avg_win'],
                'avg_loss' => $stats['avg_loss'],
                'trades' => $stats['trades'],
                'full_kelly' => $kelly['full'],
                'recommended_pct' => round($kelly['recommended'] * 100, 1),
                'edge' => $kelly['edge'],
                'has_edge' => ($kelly['edge'] > 0)
            );

            if ($is_admin) {
                $safe_strat = $conn->real_escape_string($strat);
                $conn->query("REPLACE INTO kelly_sizing_log
                    (source_table, algorithm_name, calc_date, win_rate, avg_win_pct, avg_loss_pct,
                     full_kelly, half_kelly, quarter_kelly, recommended_pct, trades_used, created_at)
                    VALUES ('miracle_picks3', '$safe_strat', '$today',
                    {$stats['win_rate']}, {$stats['avg_win']}, {$stats['avg_loss']},
                    {$kelly['full']}, {$kelly['half']}, {$kelly['quarter']}, {$kelly['recommended']},
                    {$stats['trades']}, '$now')");
            }
        }
    }

    // Sort by edge descending
    $edge_arr = array();
    for ($i = 0; $i < count($results); $i++) $edge_arr[$i] = $results[$i]['edge'];
    arsort($edge_arr);
    $sorted = array();
    foreach ($edge_arr as $idx => $val) $sorted[] = $results[$idx];

    $response['algorithms'] = $sorted;
    $response['count'] = count($sorted);
    $with_edge = 0;
    foreach ($sorted as $s) { if ($s['has_edge']) $with_edge++; }
    $response['with_edge'] = $with_edge;
    $response['without_edge'] = count($sorted) - $with_edge;

} elseif ($action === 'portfolio') {
    // ═══════════════════════════════════════════════
    // ACTION: portfolio — Kelly-weighted sizes for current top picks
    // ═══════════════════════════════════════════════
    $capital = isset($_GET['capital']) ? max(100, (float)$_GET['capital']) : 10000;
    $max_positions = isset($_GET['max_pos']) ? max(1, min(20, (int)$_GET['max_pos'])) : 5;

    // Get today's top consensus picks
    $picks = array();
    $pr = $conn->query("SELECT ticker, algorithm_name AS source_algo, entry_price, score,
                                'stock_picks' AS source_table
                         FROM stock_picks
                         WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL 3 DAY)
                           AND entry_price > 0
                         ORDER BY score DESC LIMIT 20");
    if ($pr) { while ($row = $pr->fetch_assoc()) $picks[] = $row; }

    $pr2 = $conn->query("SELECT ticker, strategy_name AS source_algo, entry_price, score,
                                 'miracle_picks3' AS source_table
                          FROM miracle_picks3
                          WHERE scan_date >= DATE_SUB(CURDATE(), INTERVAL 3 DAY)
                            AND entry_price > 0
                          ORDER BY score DESC LIMIT 20");
    if ($pr2) { while ($row = $pr2->fetch_assoc()) $picks[] = $row; }

    // Deduplicate by ticker, keep highest score
    $seen = array();
    $unique = array();
    foreach ($picks as $p) {
        $t = strtoupper(trim($p['ticker']));
        if (!isset($seen[$t]) || (int)$p['score'] > $seen[$t]) {
            $seen[$t] = (int)$p['score'];
            $unique[$t] = $p;
        }
    }

    // Sort by score descending and take top N
    $score_arr = array();
    $tickers = array_keys($unique);
    for ($i = 0; $i < count($tickers); $i++) $score_arr[$i] = (int)$unique[$tickers[$i]]['score'];
    arsort($score_arr);

    $portfolio = array();
    $total_allocated = 0;
    $pos_count = 0;
    foreach ($score_arr as $idx => $sc) {
        if ($pos_count >= $max_positions) break;
        $t = $tickers[$idx];
        $p = $unique[$t];

        // Get Kelly sizing for this algo
        $stats = _kelly_get_stats($conn, $p['source_table'], $p['source_algo']);
        $kelly_pct = 0.10; // default 10%
        $kelly_info = array('full' => 0, 'recommended' => 0.10, 'edge' => 0);
        if ($stats) {
            $kelly_info = _kelly_fraction($stats['win_rate'], $stats['avg_win'], $stats['avg_loss']);
            if ($kelly_info['recommended'] > 0) {
                $kelly_pct = $kelly_info['recommended'];
            }
        }

        $position_value = round($capital * $kelly_pct, 2);
        $entry_price = (float)$p['entry_price'];
        $shares = ($entry_price > 0) ? (int)floor($position_value / $entry_price) : 0;

        $portfolio[] = array(
            'ticker' => $t,
            'algorithm' => $p['source_algo'],
            'source' => $p['source_table'],
            'score' => (int)$p['score'],
            'entry_price' => $entry_price,
            'kelly_pct' => round($kelly_pct * 100, 1),
            'position_value' => $position_value,
            'shares' => $shares,
            'edge' => $kelly_info['edge'],
            'has_edge' => ($kelly_info['edge'] > 0)
        );
        $total_allocated += $position_value;
        $pos_count++;
    }

    $response['capital'] = $capital;
    $response['positions'] = $portfolio;
    $response['position_count'] = count($portfolio);
    $response['total_allocated'] = round($total_allocated, 2);
    $response['cash_remaining'] = round($capital - $total_allocated, 2);
    $response['allocation_pct'] = round(($total_allocated / $capital) * 100, 1);

} elseif ($action === 'history') {
    // ═══════════════════════════════════════════════
    // ACTION: history — Historical Kelly recommendations
    // ═══════════════════════════════════════════════
    $algorithm = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';
    $limit = isset($_GET['limit']) ? max(1, min(90, (int)$_GET['limit'])) : 30;

    $where = '';
    if ($algorithm !== '') {
        $where = " WHERE algorithm_name='" . $conn->real_escape_string($algorithm) . "'";
    }

    $history = array();
    $hr = $conn->query("SELECT * FROM kelly_sizing_log $where ORDER BY calc_date DESC LIMIT $limit");
    if ($hr) {
        while ($row = $hr->fetch_assoc()) {
            $row['full_kelly'] = (float)$row['full_kelly'];
            $row['recommended_pct'] = (float)$row['recommended_pct'];
            $history[] = $row;
        }
    }

    $response['history'] = $history;
    $response['count'] = count($history);
}

echo json_encode($response);
$conn->close();
