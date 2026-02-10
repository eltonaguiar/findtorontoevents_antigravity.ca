<?php
/**
 * Consensus Performance Tracking API
 * Tracks consensus pick outcomes honestly, self-learns patterns, runs $200/day challenge.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   track           — (admin) Record/update consensus picks as tracked positions
 *   dashboard       — Performance summary stats + chart data
 *   positions       — Open positions + recent closed
 *   lessons         — Self-learning insights
 *   challenge       — $200/day challenge results
 *   challenge_run   — (admin) Execute today's $200/day challenge
 */
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/consensus_performance_schema.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'dashboard';
$admin_key = 'stocksrefresh2026';
$is_admin = (isset($_GET['key']) && $_GET['key'] === $admin_key);

// ─── Cache helper ───
$cache_dir = dirname(__FILE__) . '/cache';
if (!is_dir($cache_dir)) @mkdir($cache_dir, 0755, true);

function _cp_cache_get($key, $ttl) {
    global $cache_dir;
    $file = $cache_dir . '/cp_' . md5($key) . '.json';
    if (file_exists($file) && (time() - filemtime($file)) < $ttl) {
        $data = @file_get_contents($file);
        if ($data !== false) return json_decode($data, true);
    }
    return false;
}

function _cp_cache_set($key, $data) {
    global $cache_dir;
    $file = $cache_dir . '/cp_' . md5($key) . '.json';
    @file_put_contents($file, json_encode($data));
}


// ═══════════════════════════════════════════
// TRACK — Record/update consensus picks (admin)
// ═══════════════════════════════════════════
if ($action === 'track') {
    if (!$is_admin) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Admin key required'));
        $conn->close();
        exit;
    }

    $now = date('Y-m-d H:i:s');
    $today = date('Y-m-d');
    $new_entries = 0;
    $updated = 0;
    $closed = 0;

    // ── Step 1: Get current consensus picks ──
    $days = 14;
    $min_consensus = 2;
    $all_picks = array();

    $res = $conn->query("SELECT ticker, algorithm_name AS source_algo, pick_date, entry_price, score,
                                'stock_picks' AS source_table
                         FROM stock_picks
                         WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) AND entry_price > 0");
    if ($res) { while ($row = $res->fetch_assoc()) $all_picks[] = $row; }

    $res = $conn->query("SELECT ticker, strategy_name AS source_algo, scan_date AS pick_date, entry_price, score,
                                'miracle_picks2' AS source_table
                         FROM miracle_picks2
                         WHERE scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) AND entry_price > 0");
    if ($res) { while ($row = $res->fetch_assoc()) $all_picks[] = $row; }

    $res = $conn->query("SELECT ticker, strategy_name AS source_algo, scan_date AS pick_date, entry_price, score,
                                'miracle_picks3' AS source_table
                         FROM miracle_picks3
                         WHERE scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) AND entry_price > 0");
    if ($res) { while ($row = $res->fetch_assoc()) $all_picks[] = $row; }

    // Group by ticker
    $by_ticker = array();
    foreach ($all_picks as $p) {
        $t = strtoupper(trim($p['ticker']));
        if ($t === '') continue;
        if (!isset($by_ticker[$t])) {
            $by_ticker[$t] = array('algos' => array(), 'entries' => array(), 'scores' => array(), 'all_algos' => array());
        }
        $algo_key = $p['source_table'] . ':' . $p['source_algo'];
        if (!in_array($algo_key, $by_ticker[$t]['algos'])) {
            $by_ticker[$t]['algos'][] = $algo_key;
        }
        $by_ticker[$t]['entries'][] = (float)$p['entry_price'];
        $by_ticker[$t]['scores'][] = (int)$p['score'];
        $by_ticker[$t]['all_algos'][] = $p['source_algo'];
    }

    // Filter to consensus picks only (2+ algos)
    $consensus_tickers = array();
    foreach ($by_ticker as $t => $data) {
        if (count($data['algos']) >= $min_consensus) {
            $consensus_tickers[$t] = $data;
        }
    }

    // ── Step 2: For each consensus pick, create/update tracked position ──
    foreach ($consensus_tickers as $t => $data) {
        $safe_t = $conn->real_escape_string($t);
        $cons_count = count($data['algos']);
        $cons_score = round(array_sum($data['scores']), 2);
        $avg_entry = round(array_sum($data['entries']) / count($data['entries']), 4);
        $algos_str = $conn->real_escape_string(implode(', ', array_unique($data['all_algos'])));

        // Get company name
        $company = '';
        $cr = $conn->query("SELECT company_name FROM stocks WHERE ticker='$safe_t' LIMIT 1");
        if ($cr && $cr->num_rows > 0) { $crow = $cr->fetch_assoc(); $company = $crow['company_name']; }
        if ($company === '') {
            $cr2 = $conn->query("SELECT company_name FROM miracle_picks3 WHERE ticker='$safe_t' AND company_name != '' LIMIT 1");
            if ($cr2 && $cr2->num_rows > 0) { $crow2 = $cr2->fetch_assoc(); $company = $crow2['company_name']; }
        }
        $safe_company = $conn->real_escape_string($company);

        // Get latest price
        $latest_price = 0;
        $pr = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$safe_t' ORDER BY trade_date DESC LIMIT 1");
        if ($pr && $pr->num_rows > 0) { $prow = $pr->fetch_assoc(); $latest_price = (float)$prow['close_price']; }

        // Check if already tracked (open position for this ticker)
        $existing = $conn->query("SELECT id, entry_price, entry_date, peak_price, trough_price, target_tp_pct, target_sl_pct, max_hold_days
                                  FROM consensus_tracked WHERE ticker='$safe_t' AND status='open' LIMIT 1");

        if ($existing && $existing->num_rows > 0) {
            // Update existing position
            $row = $existing->fetch_assoc();
            $entry_price = (float)$row['entry_price'];
            $peak = max((float)$row['peak_price'], $latest_price);
            $trough = (float)$row['trough_price'];
            if ($trough <= 0 || $latest_price < $trough) $trough = $latest_price;

            $return_pct = ($entry_price > 0 && $latest_price > 0)
                ? round(($latest_price - $entry_price) / $entry_price * 100, 4) : 0;

            $hold_days = max(0, (int)((time() - strtotime($row['entry_date'])) / 86400));
            $tp = (float)$row['target_tp_pct'];
            $sl = (float)$row['target_sl_pct'];
            $max_hold = (int)$row['max_hold_days'];

            // Check exit conditions
            $exit_reason = '';
            if ($return_pct >= $tp) {
                $exit_reason = 'tp_hit';
            } elseif ($return_pct <= -$sl) {
                $exit_reason = 'sl_hit';
            } elseif ($hold_days >= $max_hold) {
                $exit_reason = 'max_hold';
            }

            if ($exit_reason !== '') {
                // Close position
                $status = ($return_pct > 0) ? 'closed_win' : (($return_pct < 0) ? 'closed_loss' : 'closed_neutral');
                $conn->query("UPDATE consensus_tracked SET
                    current_price=$latest_price, current_return_pct=$return_pct,
                    peak_price=$peak, trough_price=$trough,
                    status='$status', exit_date='$today', exit_price=$latest_price,
                    exit_reason='$exit_reason', final_return_pct=$return_pct,
                    hold_days=$hold_days, updated_at='$now',
                    consensus_count=$cons_count, consensus_score=$cons_score
                    WHERE id=" . (int)$row['id']);
                $closed++;
            } else {
                // Update
                $conn->query("UPDATE consensus_tracked SET
                    current_price=$latest_price, current_return_pct=$return_pct,
                    peak_price=$peak, trough_price=$trough,
                    hold_days=$hold_days, updated_at='$now',
                    consensus_count=$cons_count, consensus_score=$cons_score,
                    source_algos='$algos_str'
                    WHERE id=" . (int)$row['id']);
                $updated++;
            }
        } else {
            // Check if there's no existing open OR recently closed position
            $recent = $conn->query("SELECT id FROM consensus_tracked
                                    WHERE ticker='$safe_t' AND entry_date='$today' LIMIT 1");
            if (!$recent || $recent->num_rows == 0) {
                // New entry
                $ep = ($latest_price > 0) ? $latest_price : $avg_entry;
                $conn->query("INSERT INTO consensus_tracked
                    (ticker, company_name, entry_date, entry_price, consensus_count, consensus_score,
                     direction, source_algos, current_price, current_return_pct,
                     peak_price, trough_price, status, created_at, updated_at)
                    VALUES ('$safe_t', '$safe_company', '$today', $ep, $cons_count, $cons_score,
                     'LONG', '$algos_str', $ep, 0, $ep, $ep, 'open', '$now', '$now')");
                $new_entries++;
            }
        }
    }

    // ── Step 3: Close positions where consensus dropped ──
    $open_res = $conn->query("SELECT id, ticker, entry_price, entry_date FROM consensus_tracked WHERE status='open'");
    if ($open_res) {
        while ($row = $open_res->fetch_assoc()) {
            $t = $row['ticker'];
            if (!isset($consensus_tickers[$t])) {
                // Consensus dropped — close this position
                $safe_t = $conn->real_escape_string($t);
                $lp = 0;
                $pr2 = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$safe_t' ORDER BY trade_date DESC LIMIT 1");
                if ($pr2 && $pr2->num_rows > 0) { $prow2 = $pr2->fetch_assoc(); $lp = (float)$prow2['close_price']; }
                $ep = (float)$row['entry_price'];
                $ret = ($ep > 0 && $lp > 0) ? round(($lp - $ep) / $ep * 100, 4) : 0;
                $hold = max(0, (int)((time() - strtotime($row['entry_date'])) / 86400));
                $status = ($ret > 0) ? 'closed_win' : (($ret < 0) ? 'closed_loss' : 'closed_neutral');

                $conn->query("UPDATE consensus_tracked SET
                    current_price=$lp, current_return_pct=$ret,
                    status='$status', exit_date='$today', exit_price=$lp,
                    exit_reason='consensus_dropped', final_return_pct=$ret,
                    hold_days=$hold, updated_at='$now'
                    WHERE id=" . (int)$row['id']);
                $closed++;
            }
        }
    }

    // ── Step 4: Performance daily snapshot ──
    _cp_record_daily_snapshot($conn, $today, $now);

    // ── Step 5: Self-learning analysis ──
    $lessons_detected = _cp_detect_lessons($conn, $today, $now);

    // ── Step 6: Run $200/day challenge ──
    $challenge_consensus = _cp_run_challenge($conn, $today, $now, 'consensus', $consensus_tickers);
    $challenge_ml = _cp_run_challenge($conn, $today, $now, 'ml', $consensus_tickers);

    // Clear caches so dashboard/challenge endpoints return fresh data
    $cache_glob = glob($cache_dir . '/cp_*.json');
    if ($cache_glob) { foreach ($cache_glob as $cf) @unlink($cf); }

    echo json_encode(array(
        'ok' => true,
        'action' => 'track',
        'new_entries' => $new_entries,
        'updated' => $updated,
        'closed' => $closed,
        'total_consensus_tickers' => count($consensus_tickers),
        'lessons_detected' => $lessons_detected,
        'challenge_consensus' => $challenge_consensus,
        'challenge_ml' => $challenge_ml,
        'tracked_at' => $now
    ));


// ═══════════════════════════════════════════
// DASHBOARD — Performance summary
// ═══════════════════════════════════════════
} elseif ($action === 'dashboard') {
    $cached = _cp_cache_get('dashboard', 600);
    if ($cached !== false && !$is_admin) {
        $cached['from_cache'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    // Overall stats
    $total_open = 0;
    $total_closed = 0;
    $total_wins = 0;
    $total_losses = 0;

    $r = $conn->query("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE status='open'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $total_open = (int)$row['cnt']; }

    $r = $conn->query("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE status LIKE 'closed%'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $total_closed = (int)$row['cnt']; }

    $r = $conn->query("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE status='closed_win'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $total_wins = (int)$row['cnt']; }

    $r = $conn->query("SELECT COUNT(*) as cnt FROM consensus_tracked WHERE status='closed_loss'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $total_losses = (int)$row['cnt']; }

    $win_rate = ($total_closed > 0) ? round($total_wins / $total_closed * 100, 1) : 0;

    // Avg returns
    $avg_win = 0;
    $avg_loss = 0;
    $total_return = 0;
    $r = $conn->query("SELECT AVG(final_return_pct) as avg_r FROM consensus_tracked WHERE status='closed_win'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_win = round((float)$row['avg_r'], 2); }
    $r = $conn->query("SELECT AVG(final_return_pct) as avg_r FROM consensus_tracked WHERE status='closed_loss'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_loss = round((float)$row['avg_r'], 2); }
    $r = $conn->query("SELECT SUM(final_return_pct) as sum_r FROM consensus_tracked WHERE status LIKE 'closed%'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $total_return = round((float)$row['sum_r'], 2); }

    // Avg hold days
    $avg_hold = 0;
    $r = $conn->query("SELECT AVG(hold_days) as avg_h FROM consensus_tracked WHERE status LIKE 'closed%'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_hold = round((float)$row['avg_h'], 1); }

    // Current streak
    $streak = _cp_calc_streak($conn);

    // Best and worst ever
    $best = array('ticker' => '-', 'return_pct' => 0);
    $worst = array('ticker' => '-', 'return_pct' => 0);
    $r = $conn->query("SELECT ticker, final_return_pct FROM consensus_tracked WHERE status LIKE 'closed%' ORDER BY final_return_pct DESC LIMIT 1");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $best = array('ticker' => $row['ticker'], 'return_pct' => (float)$row['final_return_pct']); }
    $r = $conn->query("SELECT ticker, final_return_pct FROM consensus_tracked WHERE status LIKE 'closed%' ORDER BY final_return_pct ASC LIMIT 1");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $worst = array('ticker' => $row['ticker'], 'return_pct' => (float)$row['final_return_pct']); }

    // Profit factor
    $sum_wins = 0;
    $sum_losses = 0;
    $r = $conn->query("SELECT SUM(final_return_pct) as s FROM consensus_tracked WHERE status='closed_win'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sum_wins = (float)$row['s']; }
    $r = $conn->query("SELECT SUM(ABS(final_return_pct)) as s FROM consensus_tracked WHERE status='closed_loss'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sum_losses = (float)$row['s']; }
    $profit_factor = ($sum_losses > 0) ? round($sum_wins / $sum_losses, 2) : 0;

    // Chart data (daily snapshots)
    $chart = array();
    $r = $conn->query("SELECT track_date, portfolio_value, win_rate, total_closed, open_positions, current_streak, total_pnl_pct
                       FROM consensus_performance_daily ORDER BY track_date ASC LIMIT 90");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $chart[] = array(
                'date' => $row['track_date'],
                'value' => (float)$row['portfolio_value'],
                'win_rate' => (float)$row['win_rate'],
                'total_closed' => (int)$row['total_closed'],
                'open' => (int)$row['open_positions'],
                'streak' => (int)$row['current_streak'],
                'pnl_pct' => (float)$row['total_pnl_pct']
            );
        }
    }

    // Exit reason distribution
    $exit_reasons = array();
    $r = $conn->query("SELECT exit_reason, COUNT(*) as cnt, AVG(final_return_pct) as avg_ret
                       FROM consensus_tracked WHERE status LIKE 'closed%'
                       GROUP BY exit_reason ORDER BY cnt DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $exit_reasons[] = array(
                'reason' => $row['exit_reason'],
                'count' => (int)$row['cnt'],
                'avg_return' => round((float)$row['avg_ret'], 2)
            );
        }
    }

    $result = array(
        'ok' => true,
        'action' => 'dashboard',
        'stats' => array(
            'total_tracked' => $total_open + $total_closed,
            'open_positions' => $total_open,
            'total_closed' => $total_closed,
            'total_wins' => $total_wins,
            'total_losses' => $total_losses,
            'win_rate' => $win_rate,
            'avg_win_pct' => $avg_win,
            'avg_loss_pct' => $avg_loss,
            'total_return_pct' => $total_return,
            'profit_factor' => $profit_factor,
            'avg_hold_days' => $avg_hold,
            'current_streak' => $streak,
            'best_pick' => $best,
            'worst_pick' => $worst
        ),
        'exit_reasons' => $exit_reasons,
        'chart' => $chart,
        'generated_at' => date('Y-m-d H:i:s')
    );

    _cp_cache_set('dashboard', $result);
    echo json_encode($result);


// ═══════════════════════════════════════════
// POSITIONS — Open + recent closed positions
// ═══════════════════════════════════════════
} elseif ($action === 'positions') {
    $status_filter = isset($_GET['status']) ? $_GET['status'] : 'all';

    $open = array();
    $r = $conn->query("SELECT * FROM consensus_tracked WHERE status='open' ORDER BY current_return_pct DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) $open[] = $row;
    }

    $closed = array();
    $limit = isset($_GET['limit']) ? max(1, min(100, (int)$_GET['limit'])) : 30;
    $r = $conn->query("SELECT * FROM consensus_tracked WHERE status LIKE 'closed%'
                       ORDER BY exit_date DESC, id DESC LIMIT $limit");
    if ($r) {
        while ($row = $r->fetch_assoc()) $closed[] = $row;
    }

    // Add auto-diagnostic notes for open positions
    $all_picks = _cp_get_consensus_with_returns($conn);
    $sector_perf = _cp_analyze_sectors($conn, $all_picks);
    $algo_perf = _cp_analyze_algos($conn, $all_picks);

    // Build lookup for diagnosed picks
    $diag_map = array();
    $diagnosed = _cp_generate_auto_notes($conn, $all_picks, $sector_perf, $algo_perf);
    foreach ($diagnosed as $dp) {
        $diag_map[$dp['ticker']] = $dp['diagnosis'];
    }

    // Attach diagnosis to open positions
    for ($i = 0; $i < count($open); $i++) {
        $t = $open[$i]['ticker'];
        $open[$i]['diagnosis'] = isset($diag_map[$t]) ? $diag_map[$t] : null;
        $open[$i]['sector'] = _cp_get_sector($t);
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'positions',
        'open' => $open,
        'open_count' => count($open),
        'closed' => $closed,
        'closed_count' => count($closed)
    ));


// ═══════════════════════════════════════════
// LESSONS — Self-learning insights
// ═══════════════════════════════════════════
} elseif ($action === 'lessons') {
    $type_filter = isset($_GET['type']) ? $conn->real_escape_string($_GET['type']) : '';
    $limit = isset($_GET['limit']) ? max(1, min(50, (int)$_GET['limit'])) : 20;

    $where = "1=1";
    if ($type_filter !== '') $where .= " AND lesson_type='$type_filter'";

    $lessons = array();
    $r = $conn->query("SELECT * FROM consensus_lessons WHERE $where ORDER BY lesson_date DESC, confidence DESC LIMIT $limit");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            if (isset($row['supporting_data']) && $row['supporting_data'] !== '') {
                $row['supporting_data'] = json_decode($row['supporting_data'], true);
            }
            $lessons[] = $row;
        }
    }

    // Summary: lesson types and counts
    $summary = array();
    $r = $conn->query("SELECT lesson_type, COUNT(*) as cnt, AVG(confidence) as avg_conf
                       FROM consensus_lessons GROUP BY lesson_type ORDER BY cnt DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $summary[] = array(
                'type' => $row['lesson_type'],
                'count' => (int)$row['cnt'],
                'avg_confidence' => round((float)$row['avg_conf'])
            );
        }
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'lessons',
        'lessons' => $lessons,
        'total' => count($lessons),
        'summary' => $summary
    ));


// ═══════════════════════════════════════════
// CHALLENGE — $200/day challenge results
// ═══════════════════════════════════════════
} elseif ($action === 'challenge') {
    $mode = isset($_GET['mode']) ? $_GET['mode'] : 'all';
    $days = isset($_GET['days']) ? max(1, min(90, (int)$_GET['days'])) : 30;

    $cached = _cp_cache_get('challenge_' . $mode . '_' . $days, 600);
    if ($cached !== false && !$is_admin) {
        $cached['from_cache'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    // Get daily results
    $where_mode = ($mode !== 'all') ? " AND mode='" . $conn->real_escape_string($mode) . "'" : '';
    $history = array();
    $r = $conn->query("SELECT * FROM challenge_200_days
                       WHERE challenge_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) $where_mode
                       ORDER BY challenge_date DESC, mode ASC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            if (isset($row['lessons_json']) && $row['lessons_json'] !== '') {
                $row['lessons'] = json_decode($row['lessons_json'], true);
            }
            unset($row['lessons_json']);
            $history[] = $row;
        }
    }

    // Summary per mode
    $mode_stats = array();
    $r = $conn->query("SELECT mode, COUNT(*) as days_tracked, SUM(daily_pnl) as total_pnl,
                              AVG(daily_return_pct) as avg_daily_return,
                              SUM(target_hit) as targets_hit, SUM(wins) as total_wins,
                              SUM(losses) as total_losses,
                              MAX(cumulative_pnl) as peak_pnl,
                              MIN(cumulative_pnl) as min_pnl
                       FROM challenge_200_days
                       WHERE challenge_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) $where_mode
                       GROUP BY mode");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $tw = (int)$row['total_wins'];
            $tl = (int)$row['total_losses'];
            $wr = ($tw + $tl > 0) ? round($tw / ($tw + $tl) * 100, 1) : 0;
            $mode_stats[] = array(
                'mode' => $row['mode'],
                'days_tracked' => (int)$row['days_tracked'],
                'total_pnl' => round((float)$row['total_pnl'], 2),
                'avg_daily_return' => round((float)$row['avg_daily_return'], 2),
                'target_hit_rate' => ((int)$row['days_tracked'] > 0)
                    ? round((int)$row['targets_hit'] / (int)$row['days_tracked'] * 100, 1) : 0,
                'win_rate' => $wr,
                'peak_pnl' => round((float)$row['peak_pnl'], 2),
                'max_drawdown' => round((float)$row['min_pnl'], 2)
            );
        }
    }

    // Latest day's trades
    $latest_trades = array();
    $r = $conn->query("SELECT * FROM challenge_200_trades
                       WHERE challenge_date = (SELECT MAX(challenge_date) FROM challenge_200_days)
                       ORDER BY mode ASC, return_pct DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) $latest_trades[] = $row;
    }

    $result = array(
        'ok' => true,
        'action' => 'challenge',
        'mode_stats' => $mode_stats,
        'history' => $history,
        'latest_trades' => $latest_trades,
        'generated_at' => date('Y-m-d H:i:s')
    );

    _cp_cache_set('challenge_' . $mode . '_' . $days, $result);
    echo json_encode($result);


// ═══════════════════════════════════════════
// DIAGNOSE — Auto-analyze why picks are winning/losing
// ═══════════════════════════════════════════
} elseif ($action === 'diagnose') {
    $cached = _cp_cache_get('diagnose', 300);
    if ($cached !== false && !$is_admin) {
        $cached['from_cache'] = true;
        echo json_encode($cached);
        $conn->close();
        exit;
    }

    // 1. Get all consensus picks with returns from consolidated_picks data
    $all_picks = _cp_get_consensus_with_returns($conn);

    // 2. Sector analysis
    $sector_perf = _cp_analyze_sectors($conn, $all_picks);

    // 3. Algorithm performance analysis
    $algo_perf = _cp_analyze_algos($conn, $all_picks);

    // 4. Generate per-pick auto-notes
    $diagnosed_picks = _cp_generate_auto_notes($conn, $all_picks, $sector_perf, $algo_perf);

    // 5. Generate market-level insights
    $market_notes = _cp_generate_market_notes($all_picks, $sector_perf, $algo_perf);

    // 6. Challenge diagnosis
    $challenge_notes = _cp_diagnose_challenge($conn);

    $result = array(
        'ok' => true,
        'action' => 'diagnose',
        'market_notes' => $market_notes,
        'sector_performance' => $sector_perf,
        'algo_performance' => $algo_perf,
        'losers' => array(),
        'winners' => array(),
        'challenge_diagnosis' => $challenge_notes,
        'total_picks' => count($all_picks),
        'diagnosed_at' => date('Y-m-d H:i:s')
    );

    // Split diagnosed picks into losers/winners
    foreach ($diagnosed_picks as $p) {
        if ($p['return_pct'] < -0.5) {
            $result['losers'][] = $p;
        } elseif ($p['return_pct'] > 0.5) {
            $result['winners'][] = $p;
        }
    }

    // Sort losers by worst first, winners by best first
    usort($result['losers'], create_function('$a,$b', 'if ($a["return_pct"] == $b["return_pct"]) return 0; return ($a["return_pct"] < $b["return_pct"]) ? -1 : 1;'));
    usort($result['winners'], create_function('$a,$b', 'if ($a["return_pct"] == $b["return_pct"]) return 0; return ($a["return_pct"] > $b["return_pct"]) ? -1 : 1;'));

    _cp_cache_set('diagnose', $result);
    echo json_encode($result);


// ═══════════════════════════════════════════
// UNKNOWN
// ═══════════════════════════════════════════
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action. Use: track, dashboard, positions, lessons, challenge, diagnose'));
}

$conn->close();


// ═══════════════════════════════════════════════════════════════
// HELPER: Record daily performance snapshot
// ═══════════════════════════════════════════════════════════════
function _cp_record_daily_snapshot($conn, $today, $now) {
    $open = 0;
    $closed_total = 0;
    $wins = 0;
    $losses = 0;

    $r = $conn->query("SELECT COUNT(*) as c FROM consensus_tracked WHERE status='open'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $open = (int)$row['c']; }

    $r = $conn->query("SELECT COUNT(*) as c FROM consensus_tracked WHERE status LIKE 'closed%'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $closed_total = (int)$row['c']; }

    $r = $conn->query("SELECT COUNT(*) as c FROM consensus_tracked WHERE status='closed_win'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $wins = (int)$row['c']; }

    $r = $conn->query("SELECT COUNT(*) as c FROM consensus_tracked WHERE status='closed_loss'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $losses = (int)$row['c']; }

    $wr = ($closed_total > 0) ? round($wins / $closed_total * 100, 2) : 0;

    $total_pnl = 0;
    $avg_win = 0;
    $avg_loss = 0;
    $avg_hold = 0;

    $r = $conn->query("SELECT SUM(final_return_pct) as s FROM consensus_tracked WHERE status LIKE 'closed%'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $total_pnl = round((float)$row['s'], 4); }

    $r = $conn->query("SELECT AVG(final_return_pct) as a FROM consensus_tracked WHERE status='closed_win'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_win = round((float)$row['a'], 4); }

    $r = $conn->query("SELECT AVG(final_return_pct) as a FROM consensus_tracked WHERE status='closed_loss'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_loss = round((float)$row['a'], 4); }

    $r = $conn->query("SELECT AVG(hold_days) as a FROM consensus_tracked WHERE status LIKE 'closed%'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_hold = round((float)$row['a'], 1); }

    // Best/worst closed
    $best_t = '';
    $best_r = 0;
    $worst_t = '';
    $worst_r = 0;
    $r = $conn->query("SELECT ticker, final_return_pct FROM consensus_tracked WHERE status LIKE 'closed%' ORDER BY final_return_pct DESC LIMIT 1");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $best_t = $row['ticker']; $best_r = (float)$row['final_return_pct']; }
    $r = $conn->query("SELECT ticker, final_return_pct FROM consensus_tracked WHERE status LIKE 'closed%' ORDER BY final_return_pct ASC LIMIT 1");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $worst_t = $row['ticker']; $worst_r = (float)$row['final_return_pct']; }

    $streak = _cp_calc_streak($conn);

    // Portfolio value: start at $10,000, compound returns
    $portfolio = 10000;
    $r = $conn->query("SELECT final_return_pct FROM consensus_tracked WHERE status LIKE 'closed%' ORDER BY exit_date ASC, id ASC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $ret = (float)$row['final_return_pct'];
            $portfolio = $portfolio * (1 + $ret / 100);
        }
    }
    $portfolio = round($portfolio, 2);

    $safe_best = $conn->real_escape_string($best_t);
    $safe_worst = $conn->real_escape_string($worst_t);

    $conn->query("INSERT INTO consensus_performance_daily
        (track_date, open_positions, total_closed, total_wins, total_losses, win_rate,
         total_pnl_pct, avg_win_pct, avg_loss_pct, best_ticker, best_return_pct,
         worst_ticker, worst_return_pct, avg_hold_days, current_streak, portfolio_value, created_at)
        VALUES ('$today', $open, $closed_total, $wins, $losses, $wr,
         $total_pnl, $avg_win, $avg_loss, '$safe_best', $best_r,
         '$safe_worst', $worst_r, $avg_hold, $streak, $portfolio, '$now')
        ON DUPLICATE KEY UPDATE
         open_positions=$open, total_closed=$closed_total, total_wins=$wins, total_losses=$losses,
         win_rate=$wr, total_pnl_pct=$total_pnl, avg_win_pct=$avg_win, avg_loss_pct=$avg_loss,
         best_ticker='$safe_best', best_return_pct=$best_r, worst_ticker='$safe_worst',
         worst_return_pct=$worst_r, avg_hold_days=$avg_hold, current_streak=$streak,
         portfolio_value=$portfolio");
}


// ═══════════════════════════════════════════════════════════════
// HELPER: Calculate current win/loss streak
// ═══════════════════════════════════════════════════════════════
function _cp_calc_streak($conn) {
    $streak = 0;
    $r = $conn->query("SELECT status FROM consensus_tracked WHERE status LIKE 'closed%'
                       ORDER BY exit_date DESC, id DESC LIMIT 50");
    if (!$r) return 0;

    $first = true;
    $dir = '';
    while ($row = $r->fetch_assoc()) {
        $is_win = ($row['status'] === 'closed_win');
        if ($first) {
            $dir = $is_win ? 'win' : 'loss';
            $streak = $is_win ? 1 : -1;
            $first = false;
        } else {
            if ($is_win && $dir === 'win') {
                $streak++;
            } elseif (!$is_win && $dir === 'loss') {
                $streak--;
            } else {
                break;
            }
        }
    }
    return $streak;
}


// ═══════════════════════════════════════════════════════════════
// HELPER: Self-learning — detect patterns from historical data
// ═══════════════════════════════════════════════════════════════
function _cp_detect_lessons($conn, $today, $now) {
    $lessons_added = 0;
    $min_samples = 5; // need at least 5 closed trades to detect patterns

    // Check if we have enough data
    $r = $conn->query("SELECT COUNT(*) as c FROM consensus_tracked WHERE status LIKE 'closed%'");
    if (!$r || $r->num_rows == 0) return 0;
    $row = $r->fetch_assoc();
    $total_closed = (int)$row['c'];
    if ($total_closed < $min_samples) return 0;

    // ── Pattern 1: Consensus Count Effect ──
    // Do picks with more algorithms agreeing perform better?
    $by_count = array();
    $r = $conn->query("SELECT consensus_count, COUNT(*) as cnt, AVG(final_return_pct) as avg_ret,
                              SUM(CASE WHEN status='closed_win' THEN 1 ELSE 0 END) as wins
                       FROM consensus_tracked WHERE status LIKE 'closed%'
                       GROUP BY consensus_count HAVING cnt >= 3 ORDER BY consensus_count");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $by_count[] = array(
                'consensus_count' => (int)$row['consensus_count'],
                'trades' => (int)$row['cnt'],
                'avg_return' => round((float)$row['avg_ret'], 2),
                'win_rate' => round((int)$row['wins'] / (int)$row['cnt'] * 100, 1)
            );
        }
    }
    if (count($by_count) >= 2) {
        $best_count = $by_count[0];
        foreach ($by_count as $bc) {
            if ($bc['win_rate'] > $best_count['win_rate']) $best_count = $bc;
        }
        $title = 'Optimal consensus count: ' . $best_count['consensus_count'] . '+ algorithms';
        $text = 'Picks with ' . $best_count['consensus_count'] . ' algorithms agreeing show '
              . $best_count['win_rate'] . '% win rate (avg return ' . $best_count['avg_return']
              . '%) across ' . $best_count['trades'] . ' trades.';
        $conf = min(90, 40 + $best_count['trades'] * 3);
        _cp_store_lesson($conn, $today, $now, 'consensus_strength', $title, $text, $conf, json_encode($by_count));
        $lessons_added++;
    }

    // ── Pattern 2: Hold Duration Effect ──
    $by_hold = array();
    $r = $conn->query("SELECT
                         CASE WHEN hold_days <= 3 THEN '1-3d'
                              WHEN hold_days <= 7 THEN '4-7d'
                              WHEN hold_days <= 14 THEN '8-14d'
                              ELSE '14d+' END AS bucket,
                         COUNT(*) as cnt, AVG(final_return_pct) as avg_ret,
                         SUM(CASE WHEN status='closed_win' THEN 1 ELSE 0 END) as wins
                       FROM consensus_tracked WHERE status LIKE 'closed%'
                       GROUP BY bucket HAVING cnt >= 3");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $by_hold[] = array(
                'bucket' => $row['bucket'],
                'trades' => (int)$row['cnt'],
                'avg_return' => round((float)$row['avg_ret'], 2),
                'win_rate' => round((int)$row['wins'] / (int)$row['cnt'] * 100, 1)
            );
        }
    }
    if (count($by_hold) >= 2) {
        $best_hold = $by_hold[0];
        foreach ($by_hold as $bh) {
            if ($bh['avg_return'] > $best_hold['avg_return']) $best_hold = $bh;
        }
        $title = 'Best hold period: ' . $best_hold['bucket'];
        $text = 'Positions held for ' . $best_hold['bucket'] . ' average '
              . $best_hold['avg_return'] . '% return with ' . $best_hold['win_rate']
              . '% win rate (' . $best_hold['trades'] . ' trades).';
        $conf = min(85, 35 + $best_hold['trades'] * 3);
        _cp_store_lesson($conn, $today, $now, 'timing', $title, $text, $conf, json_encode($by_hold));
        $lessons_added++;
    }

    // ── Pattern 3: Exit Reason Analysis ──
    $by_exit = array();
    $r = $conn->query("SELECT exit_reason, COUNT(*) as cnt, AVG(final_return_pct) as avg_ret,
                              SUM(CASE WHEN status='closed_win' THEN 1 ELSE 0 END) as wins
                       FROM consensus_tracked WHERE status LIKE 'closed%' AND exit_reason != ''
                       GROUP BY exit_reason HAVING cnt >= 3 ORDER BY avg_ret DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $by_exit[] = array(
                'reason' => $row['exit_reason'],
                'trades' => (int)$row['cnt'],
                'avg_return' => round((float)$row['avg_ret'], 2),
                'win_rate' => round((int)$row['wins'] / (int)$row['cnt'] * 100, 1)
            );
        }
    }
    if (count($by_exit) >= 2) {
        $best_exit = $by_exit[0];
        $worst_exit = $by_exit[count($by_exit) - 1];
        $title = 'Exit analysis: ' . $best_exit['reason'] . ' exits perform best';
        $text = $best_exit['reason'] . ' exits average ' . $best_exit['avg_return'] . '% ('
              . $best_exit['win_rate'] . '% WR), while ' . $worst_exit['reason'] . ' exits average '
              . $worst_exit['avg_return'] . '% (' . $worst_exit['win_rate'] . '% WR). ';
        if ($worst_exit['reason'] === 'sl_hit') {
            $text .= 'Consider tightening stop-loss to reduce losses.';
        } elseif ($worst_exit['reason'] === 'max_hold') {
            $text .= 'Positions reaching max hold suggest the thesis is stale — consider shorter hold periods.';
        } elseif ($worst_exit['reason'] === 'consensus_dropped') {
            $text .= 'When consensus drops, exiting quickly is correct behavior.';
        }
        $conf = min(80, 30 + count($by_exit) * 10);
        _cp_store_lesson($conn, $today, $now, 'risk', $title, $text, $conf, json_encode($by_exit));
        $lessons_added++;
    }

    // ── Pattern 4: Algorithm Performance Ranking ──
    // Which source algorithms appear most in winning trades?
    $algo_stats = array();
    $r = $conn->query("SELECT source_algos, status, final_return_pct FROM consensus_tracked WHERE status LIKE 'closed%'");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $algos = explode(', ', $row['source_algos']);
            foreach ($algos as $a) {
                $a = trim($a);
                if ($a === '') continue;
                if (!isset($algo_stats[$a])) {
                    $algo_stats[$a] = array('wins' => 0, 'losses' => 0, 'total_return' => 0, 'count' => 0);
                }
                $algo_stats[$a]['count']++;
                $algo_stats[$a]['total_return'] += (float)$row['final_return_pct'];
                if ($row['status'] === 'closed_win') {
                    $algo_stats[$a]['wins']++;
                } else {
                    $algo_stats[$a]['losses']++;
                }
            }
        }
    }

    // Filter to algos with 3+ appearances and rank
    $ranked_algos = array();
    foreach ($algo_stats as $name => $stats) {
        if ($stats['count'] < 3) continue;
        $wr = round($stats['wins'] / $stats['count'] * 100, 1);
        $avg_ret = round($stats['total_return'] / $stats['count'], 2);
        $ranked_algos[] = array(
            'algorithm' => $name,
            'trades' => $stats['count'],
            'wins' => $stats['wins'],
            'win_rate' => $wr,
            'avg_return' => $avg_ret
        );
    }

    if (count($ranked_algos) >= 3) {
        // Sort by win rate
        usort($ranked_algos, create_function('$a,$b', 'if ($a["win_rate"] == $b["win_rate"]) return 0; return ($a["win_rate"] > $b["win_rate"]) ? -1 : 1;'));
        $top3 = array_slice($ranked_algos, 0, 3);
        $bottom = array_slice($ranked_algos, -2);

        $title = 'Top algorithms: ' . $top3[0]['algorithm'] . ' leads';
        $parts = array();
        foreach ($top3 as $ta) {
            $parts[] = $ta['algorithm'] . ' (' . $ta['win_rate'] . '% WR, ' . $ta['avg_return'] . '% avg)';
        }
        $text = 'Best performing algorithms in consensus picks: ' . implode(', ', $parts) . '. ';
        if (count($bottom) > 0 && $bottom[0]['win_rate'] < 40) {
            $text .= 'Underperformers to downweight: ' . $bottom[0]['algorithm'] . ' (' . $bottom[0]['win_rate'] . '% WR).';
        }
        $conf = min(85, 30 + count($ranked_algos) * 5);
        _cp_store_lesson($conn, $today, $now, 'algo_insight', $title, $text, $conf, json_encode($ranked_algos));
        $lessons_added++;
    }

    // ── Pattern 5: Score Threshold Effect ──
    $by_score = array();
    $r = $conn->query("SELECT
                         CASE WHEN consensus_score < 50 THEN 'low (<50)'
                              WHEN consensus_score < 100 THEN 'medium (50-100)'
                              WHEN consensus_score < 200 THEN 'high (100-200)'
                              ELSE 'very high (200+)' END AS bracket,
                         COUNT(*) as cnt, AVG(final_return_pct) as avg_ret,
                         SUM(CASE WHEN status='closed_win' THEN 1 ELSE 0 END) as wins
                       FROM consensus_tracked WHERE status LIKE 'closed%'
                       GROUP BY bracket HAVING cnt >= 3");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $by_score[] = array(
                'bracket' => $row['bracket'],
                'trades' => (int)$row['cnt'],
                'avg_return' => round((float)$row['avg_ret'], 2),
                'win_rate' => round((int)$row['wins'] / (int)$row['cnt'] * 100, 1)
            );
        }
    }
    if (count($by_score) >= 2) {
        $best_score = $by_score[0];
        foreach ($by_score as $bs) {
            if ($bs['win_rate'] > $best_score['win_rate']) $best_score = $bs;
        }
        $title = 'Optimal consensus score: ' . $best_score['bracket'];
        $text = 'Picks with consensus score ' . $best_score['bracket'] . ' show '
              . $best_score['win_rate'] . '% win rate (avg ' . $best_score['avg_return']
              . '% return) across ' . $best_score['trades'] . ' trades.';
        $conf = min(80, 30 + $best_score['trades'] * 3);
        _cp_store_lesson($conn, $today, $now, 'pattern', $title, $text, $conf, json_encode($by_score));
        $lessons_added++;
    }

    // ── Pattern 6: Overall Performance Summary ──
    $total_closed_count = 0;
    $total_wr = 0;
    $total_ret = 0;
    $r = $conn->query("SELECT COUNT(*) as c, AVG(final_return_pct) as avg_r,
                              SUM(CASE WHEN status='closed_win' THEN 1 ELSE 0 END) as w
                       FROM consensus_tracked WHERE status LIKE 'closed%'");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $total_closed_count = (int)$row['c'];
        $total_ret = round((float)$row['avg_r'], 2);
        $total_wr = ($total_closed_count > 0) ? round((int)$row['w'] / $total_closed_count * 100, 1) : 0;
    }

    if ($total_closed_count >= $min_samples) {
        $title = 'System performance: ' . $total_wr . '% win rate across ' . $total_closed_count . ' trades';
        $text = 'Overall consensus tracking shows ' . $total_wr . '% win rate with '
              . $total_ret . '% average return per trade across ' . $total_closed_count . ' closed positions. ';
        if ($total_wr >= 60) {
            $text .= 'The system is performing well — continue current strategy.';
        } elseif ($total_wr >= 45) {
            $text .= 'Performance is moderate — consider tightening entry criteria or adjusting TP/SL.';
        } else {
            $text .= 'Performance below expectations — major parameter adjustments recommended.';
        }
        $conf = min(95, 50 + $total_closed_count);
        _cp_store_lesson($conn, $today, $now, 'improvement', $title, $text, $conf, null);
        $lessons_added++;
    }

    return $lessons_added;
}


// ═══════════════════════════════════════════════════════════════
// HELPER: Store a lesson (upserts by date + type)
// ═══════════════════════════════════════════════════════════════
function _cp_store_lesson($conn, $today, $now, $type, $title, $text, $confidence, $data_json) {
    $safe_type = $conn->real_escape_string($type);
    $safe_title = $conn->real_escape_string($title);
    $safe_text = $conn->real_escape_string($text);
    $safe_data = ($data_json !== null) ? $conn->real_escape_string($data_json) : '';

    // Check if lesson of this type already exists for today
    $r = $conn->query("SELECT id FROM consensus_lessons WHERE lesson_date='$today' AND lesson_type='$safe_type' LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $conn->query("UPDATE consensus_lessons SET
            lesson_title='$safe_title', lesson_text='$safe_text',
            confidence=$confidence, supporting_data='$safe_data'
            WHERE id=" . (int)$row['id']);
    } else {
        $conn->query("INSERT INTO consensus_lessons
            (lesson_date, lesson_type, lesson_title, lesson_text, confidence, supporting_data, created_at)
            VALUES ('$today', '$safe_type', '$safe_title', '$safe_text', $confidence, '$safe_data', '$now')");
    }
}


// ═══════════════════════════════════════════════════════════════
// HELPER: Run $200/day challenge for a given mode
// ═══════════════════════════════════════════════════════════════
function _cp_run_challenge($conn, $today, $now, $mode, $consensus_tickers) {
    $capital = 5000;
    $target = 200;
    $max_picks = 5;

    // Check if already run today for this mode
    $safe_mode = $conn->real_escape_string($mode);
    $r = $conn->query("SELECT id FROM challenge_200_days WHERE challenge_date='$today' AND mode='$safe_mode' LIMIT 1");
    if ($r && $r->num_rows > 0) {
        return array('already_run' => true, 'mode' => $mode);
    }

    // Build ranked pick list
    $ranked = array();
    foreach ($consensus_tickers as $t => $data) {
        $cons_count = count($data['algos']);
        $cons_score = array_sum($data['scores']);
        $avg_entry = (count($data['entries']) > 0) ? array_sum($data['entries']) / count($data['entries']) : 0;

        // Get latest price
        $safe_t = $conn->real_escape_string($t);
        $latest = 0;
        $pr = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$safe_t' ORDER BY trade_date DESC LIMIT 1");
        if ($pr && $pr->num_rows > 0) { $prow = $pr->fetch_assoc(); $latest = (float)$prow['close_price']; }
        if ($latest <= 0) continue;

        // Get company name
        $company = '';
        $cr = $conn->query("SELECT company_name FROM stocks WHERE ticker='$safe_t' LIMIT 1");
        if ($cr && $cr->num_rows > 0) { $crow = $cr->fetch_assoc(); $company = $crow['company_name']; }

        $score = $cons_score;

        if ($mode === 'ml') {
            // ML mode: Apply learned adjustments
            $score = _cp_ml_score($conn, $t, $cons_count, $cons_score, $latest, $avg_entry);
        }

        $ranked[] = array(
            'ticker' => $t,
            'company' => $company,
            'consensus_count' => $cons_count,
            'consensus_score' => $cons_score,
            'ml_score' => $score,
            'entry_price' => $avg_entry,
            'latest_price' => $latest
        );
    }

    // Sort by score (ml_score for ML, consensus_score for consensus)
    usort($ranked, create_function('$a,$b', 'if ($a["ml_score"] == $b["ml_score"]) return 0; return ($a["ml_score"] > $b["ml_score"]) ? -1 : 1;'));

    // Take top picks
    $picks = array_slice($ranked, 0, $max_picks);
    if (count($picks) === 0) {
        return array('mode' => $mode, 'no_picks' => true);
    }

    // Allocate capital equally
    $per_pick = $capital / count($picks);
    $total_pnl = 0;
    $total_invested = 0;
    $wins = 0;
    $losses = 0;
    $best_pick = '';
    $best_pct = -999;
    $worst_pick = '';
    $worst_pct = 999;
    $trade_notes = array();

    foreach ($picks as $p) {
        $safe_t = $conn->real_escape_string($p['ticker']);
        $safe_company = $conn->real_escape_string($p['company']);
        $entry = $p['latest_price']; // enter at latest known price
        $shares = ($entry > 0) ? round($per_pick / $entry, 4) : 0;
        $invested = round($shares * $entry, 2);

        // For the challenge, we use the current day's performance
        // Since we can't know the future, we use the return vs avg entry (consensus entry price)
        $exit_price = $entry; // same day — will be updated by next track run
        $pnl = 0;
        $ret_pct = 0;

        // If entry price differs from avg consensus entry, there's already a built-in return
        if ($p['entry_price'] > 0 && $entry > 0) {
            $ret_pct = round(($entry - $p['entry_price']) / $p['entry_price'] * 100, 4);
            $pnl = round($invested * $ret_pct / 100, 2);
        }

        $total_pnl += $pnl;
        $total_invested += $invested;
        if ($pnl > 0) $wins++;
        if ($pnl < 0) $losses++;
        if ($ret_pct > $best_pct) { $best_pct = $ret_pct; $best_pick = $p['ticker']; }
        if ($ret_pct < $worst_pct) { $worst_pct = $ret_pct; $worst_pick = $p['ticker']; }

        $notes = ($mode === 'ml') ? 'ML-adjusted score: ' . round($p['ml_score'], 1) : 'Consensus score: ' . $p['consensus_score'];
        $safe_notes = $conn->real_escape_string($notes);

        $conn->query("INSERT INTO challenge_200_trades
            (challenge_date, mode, ticker, company_name, direction, entry_price, exit_price,
             shares, invested, pnl, return_pct, consensus_count, consensus_score, exit_reason, algo_notes, created_at)
            VALUES ('$today', '$safe_mode', '$safe_t', '$safe_company', 'LONG', $entry, $exit_price,
             $shares, $invested, $pnl, $ret_pct, " . $p['consensus_count'] . ", " . $p['consensus_score'] . ",
             'day_close', '$safe_notes', '$now')");

        $trade_notes[] = $p['ticker'] . ': ' . ($ret_pct >= 0 ? '+' : '') . $ret_pct . '%';
    }

    $daily_return = ($total_invested > 0) ? round($total_pnl / $capital * 100, 4) : 0;
    $target_hit = ($total_pnl >= $target) ? 1 : 0;

    // Get cumulative from previous days
    $cum_pnl = $total_pnl;
    $cum_days = 1;
    $r = $conn->query("SELECT cumulative_pnl, cumulative_days FROM challenge_200_days
                       WHERE mode='$safe_mode' ORDER BY challenge_date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $cum_pnl = (float)$row['cumulative_pnl'] + $total_pnl;
        $cum_days = (int)$row['cumulative_days'] + 1;
    }

    // Calculate streak
    $streak = ($total_pnl >= 0) ? 1 : -1;
    $r = $conn->query("SELECT win_streak, daily_pnl FROM challenge_200_days
                       WHERE mode='$safe_mode' ORDER BY challenge_date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $prev_streak = (int)$row['win_streak'];
        $prev_pnl = (float)$row['daily_pnl'];
        if ($total_pnl >= 0 && $prev_pnl >= 0) {
            $streak = $prev_streak + 1;
        } elseif ($total_pnl < 0 && $prev_pnl < 0) {
            $streak = $prev_streak - 1;
        }
    }

    $safe_best = $conn->real_escape_string($best_pick);
    $safe_worst = $conn->real_escape_string($worst_pick);
    $lessons = implode('; ', $trade_notes);
    $safe_lessons = $conn->real_escape_string(json_encode(array('trades' => $trade_notes, 'mode' => $mode)));

    $conn->query("INSERT INTO challenge_200_days
        (challenge_date, mode, capital, picks_count, total_invested, daily_pnl, daily_return_pct,
         target_amount, target_hit, wins, losses, best_pick, best_pick_pct, worst_pick, worst_pick_pct,
         cumulative_pnl, cumulative_days, win_streak, lessons_json, created_at)
        VALUES ('$today', '$safe_mode', $capital, " . count($picks) . ", $total_invested, $total_pnl, $daily_return,
         $target, $target_hit, $wins, $losses, '$safe_best', $best_pct, '$safe_worst', $worst_pct,
         $cum_pnl, $cum_days, $streak, '$safe_lessons', '$now')");

    return array(
        'mode' => $mode,
        'picks' => count($picks),
        'total_pnl' => round($total_pnl, 2),
        'daily_return_pct' => $daily_return,
        'target_hit' => ($target_hit == 1),
        'cumulative_pnl' => round($cum_pnl, 2),
        'streak' => $streak
    );
}


// ═══════════════════════════════════════════════════════════════
// HELPER: ML-adjusted scoring for $200/day ML mode
// Uses learned lessons to boost/penalize picks
// ═══════════════════════════════════════════════════════════════
function _cp_ml_score($conn, $ticker, $cons_count, $cons_score, $latest_price, $avg_entry) {
    $score = (float)$cons_score;

    // ── Boost 1: Apply learned consensus count preference ──
    $r = $conn->query("SELECT supporting_data FROM consensus_lessons
                       WHERE lesson_type='consensus_strength' ORDER BY lesson_date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $data = json_decode($row['supporting_data'], true);
        if (is_array($data)) {
            $best_count = 2;
            $best_wr = 0;
            foreach ($data as $d) {
                if ((float)$d['win_rate'] > $best_wr) {
                    $best_wr = (float)$d['win_rate'];
                    $best_count = (int)$d['consensus_count'];
                }
            }
            // Boost picks matching optimal count
            if ($cons_count >= $best_count) {
                $score *= 1.3; // 30% boost
            } elseif ($cons_count < $best_count - 1) {
                $score *= 0.7; // 30% penalty
            }
        }
    }

    // ── Boost 2: Apply algorithm performance insights ──
    $safe_t = $conn->real_escape_string($ticker);
    $r = $conn->query("SELECT supporting_data FROM consensus_lessons
                       WHERE lesson_type='algo_insight' ORDER BY lesson_date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $data = json_decode($row['supporting_data'], true);
        if (is_array($data)) {
            // Build lookup of algo win rates
            $algo_wr = array();
            foreach ($data as $d) {
                $algo_wr[$d['algorithm']] = (float)$d['win_rate'];
            }

            // Check which algos are backing this ticker
            $tr = $conn->query("SELECT source_algos FROM consensus_tracked WHERE ticker='$safe_t' AND status='open' LIMIT 1");
            if ($tr && $tr->num_rows > 0) {
                $trow = $tr->fetch_assoc();
                $algos = explode(', ', $trow['source_algos']);
                $boost = 0;
                foreach ($algos as $a) {
                    $a = trim($a);
                    if (isset($algo_wr[$a])) {
                        if ($algo_wr[$a] >= 60) $boost += 0.15;
                        elseif ($algo_wr[$a] < 40) $boost -= 0.15;
                    }
                }
                $score *= (1 + $boost);
            }
        }
    }

    // ── Boost 3: Momentum — favor picks already showing gains ──
    if ($avg_entry > 0 && $latest_price > 0) {
        $current_ret = ($latest_price - $avg_entry) / $avg_entry * 100;
        if ($current_ret > 2) {
            $score *= 1.2; // momentum boost
        } elseif ($current_ret < -3) {
            $score *= 0.8; // falling knife penalty
        }
    }

    // ── Boost 4: Higher consensus count = higher confidence ──
    if ($cons_count >= 5) $score *= 1.25;
    elseif ($cons_count >= 3) $score *= 1.1;

    return round($score, 2);
}


// ═══════════════════════════════════════════════════════════════
// DIAGNOSE HELPERS: Auto-analysis engine
// ═══════════════════════════════════════════════════════════════

// Sector mapping for tickers
function _cp_get_sector($ticker) {
    $sectors = array(
        // Tech
        'AAPL' => 'Tech', 'MSFT' => 'Tech', 'GOOGL' => 'Tech', 'GOOG' => 'Tech',
        'META' => 'Tech', 'NVDA' => 'Tech', 'AMZN' => 'Tech', 'NFLX' => 'Tech',
        'CRM' => 'Tech', 'INTC' => 'Tech', 'CSCO' => 'Tech', 'SNAP' => 'Tech',
        'UBER' => 'Tech',
        // Finance
        'JPM' => 'Finance', 'BAC' => 'Finance', 'WFC' => 'Finance', 'GS' => 'Finance',
        'MS' => 'Finance', 'SCHW' => 'Finance',
        // Healthcare
        'JNJ' => 'Healthcare', 'PFE' => 'Healthcare', 'UNH' => 'Healthcare',
        'ABBV' => 'Healthcare', 'MRK' => 'Healthcare', 'LLY' => 'Healthcare', 'TMO' => 'Healthcare',
        // Energy
        'XOM' => 'Energy', 'CVX' => 'Energy', 'SLB' => 'Energy',
        // Consumer
        'WMT' => 'Consumer', 'COST' => 'Consumer', 'MCD' => 'Consumer', 'SBUX' => 'Consumer',
        'NKE' => 'Consumer', 'PG' => 'Consumer', 'KO' => 'Consumer', 'PEP' => 'Consumer', 'HD' => 'Consumer',
        // Industrial
        'CAT' => 'Industrial', 'HON' => 'Industrial', 'BA' => 'Industrial',
        'UPS' => 'Industrial', 'GE' => 'Industrial', 'RTX' => 'Industrial',
        // Auto
        'F' => 'Auto', 'GM' => 'Auto',
        // Real Estate
        'AMT' => 'Real Estate', 'PLD' => 'Real Estate',
        // Utilities
        'SO' => 'Utility',
        // ETFs
        'SPY' => 'ETF', 'QQQ' => 'ETF-Tech', 'XLK' => 'ETF-Tech', 'XLE' => 'ETF-Energy',
        'XLI' => 'ETF-Industrial', 'XLC' => 'ETF-Comms', 'XLP' => 'ETF-Staples', 'XLB' => 'ETF-Materials',
        // Meme/Speculative
        'GME' => 'Speculative'
    );
    return isset($sectors[$ticker]) ? $sectors[$ticker] : 'Other';
}

// Get consensus picks with current returns
function _cp_get_consensus_with_returns($conn) {
    $days = 14;
    $all_picks_raw = array();

    $res = $conn->query("SELECT ticker, algorithm_name AS algo, pick_date, entry_price, score,
                                'stock_picks' AS src FROM stock_picks
                         WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) AND entry_price > 0");
    if ($res) { while ($r = $res->fetch_assoc()) $all_picks_raw[] = $r; }

    $res = $conn->query("SELECT ticker, strategy_name AS algo, scan_date AS pick_date, entry_price, score,
                                'miracle_picks2' AS src FROM miracle_picks2
                         WHERE scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) AND entry_price > 0");
    if ($res) { while ($r = $res->fetch_assoc()) $all_picks_raw[] = $r; }

    $res = $conn->query("SELECT ticker, strategy_name AS algo, scan_date AS pick_date, entry_price, score,
                                'miracle_picks3' AS src FROM miracle_picks3
                         WHERE scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY) AND entry_price > 0");
    if ($res) { while ($r = $res->fetch_assoc()) $all_picks_raw[] = $r; }

    // Group by ticker
    $by_ticker = array();
    foreach ($all_picks_raw as $p) {
        $t = strtoupper(trim($p['ticker']));
        if ($t === '') continue;
        if (!isset($by_ticker[$t])) {
            $by_ticker[$t] = array('algos' => array(), 'algo_names' => array(), 'entries' => array(),
                                    'scores' => array(), 'pick_dates' => array(), 'sources' => array());
        }
        $key = $p['src'] . ':' . $p['algo'];
        if (!in_array($key, $by_ticker[$t]['algos'])) {
            $by_ticker[$t]['algos'][] = $key;
        }
        if (!in_array($p['algo'], $by_ticker[$t]['algo_names'])) {
            $by_ticker[$t]['algo_names'][] = $p['algo'];
        }
        if (!in_array($p['src'], $by_ticker[$t]['sources'])) {
            $by_ticker[$t]['sources'][] = $p['src'];
        }
        $by_ticker[$t]['entries'][] = (float)$p['entry_price'];
        $by_ticker[$t]['scores'][] = (int)$p['score'];
        $by_ticker[$t]['pick_dates'][] = $p['pick_date'];
    }

    // Filter to consensus (2+ algos) and compute returns
    $result = array();
    foreach ($by_ticker as $t => $data) {
        if (count($data['algos']) < 2) continue;
        $safe_t = $conn->real_escape_string($t);

        $avg_entry = array_sum($data['entries']) / count($data['entries']);
        $latest_price = 0;
        $price_date = '';
        $pr = $conn->query("SELECT close_price, trade_date FROM daily_prices WHERE ticker='$safe_t' ORDER BY trade_date DESC LIMIT 1");
        if ($pr && $pr->num_rows > 0) { $prow = $pr->fetch_assoc(); $latest_price = (float)$prow['close_price']; $price_date = $prow['trade_date']; }

        $return_pct = ($avg_entry > 0 && $latest_price > 0)
            ? round(($latest_price - $avg_entry) / $avg_entry * 100, 2) : 0;

        $price_age = ($price_date !== '') ? max(0, (int)((time() - strtotime($price_date)) / 86400)) : 99;

        sort($data['pick_dates']);
        $earliest = $data['pick_dates'][0];
        $latest_date = end($data['pick_dates']);
        $pick_age = max(0, (int)((time() - strtotime($earliest)) / 86400));

        $company = '';
        $cr = $conn->query("SELECT company_name FROM stocks WHERE ticker='$safe_t' LIMIT 1");
        if ($cr && $cr->num_rows > 0) { $crow = $cr->fetch_assoc(); $company = $crow['company_name']; }

        $result[] = array(
            'ticker' => $t,
            'company' => $company,
            'sector' => _cp_get_sector($t),
            'consensus_count' => count($data['algos']),
            'algo_names' => $data['algo_names'],
            'sources' => $data['sources'],
            'avg_entry' => round($avg_entry, 2),
            'latest_price' => $latest_price,
            'return_pct' => $return_pct,
            'price_date' => $price_date,
            'price_age_days' => $price_age,
            'earliest_pick' => $earliest,
            'latest_pick' => $latest_date,
            'pick_age_days' => $pick_age,
            'total_score' => array_sum($data['scores'])
        );
    }

    return $result;
}

// Analyze sector performance
function _cp_analyze_sectors($conn, $all_picks) {
    $sectors = array();
    foreach ($all_picks as $p) {
        $s = $p['sector'];
        if (!isset($sectors[$s])) {
            $sectors[$s] = array('picks' => 0, 'total_return' => 0, 'winners' => 0, 'losers' => 0, 'tickers' => array());
        }
        $sectors[$s]['picks']++;
        $sectors[$s]['total_return'] += $p['return_pct'];
        if ($p['return_pct'] > 0.5) $sectors[$s]['winners']++;
        if ($p['return_pct'] < -0.5) $sectors[$s]['losers']++;
        $sectors[$s]['tickers'][] = $p['ticker'];
    }

    $result = array();
    foreach ($sectors as $name => $data) {
        $avg = ($data['picks'] > 0) ? round($data['total_return'] / $data['picks'], 2) : 0;
        $result[] = array(
            'sector' => $name,
            'picks' => $data['picks'],
            'avg_return' => $avg,
            'winners' => $data['winners'],
            'losers' => $data['losers'],
            'status' => ($avg > 1) ? 'strong' : (($avg < -1) ? 'weak' : 'neutral'),
            'tickers' => $data['tickers']
        );
    }

    // Sort by avg return
    usort($result, create_function('$a,$b', 'if ($a["avg_return"] == $b["avg_return"]) return 0; return ($a["avg_return"] > $b["avg_return"]) ? -1 : 1;'));
    return $result;
}

// Analyze algorithm performance
function _cp_analyze_algos($conn, $all_picks) {
    $algos = array();
    foreach ($all_picks as $p) {
        foreach ($p['algo_names'] as $a) {
            if (!isset($algos[$a])) {
                $algos[$a] = array('picks' => 0, 'total_return' => 0, 'winners' => 0, 'losers' => 0);
            }
            $algos[$a]['picks']++;
            $algos[$a]['total_return'] += $p['return_pct'];
            if ($p['return_pct'] > 0.5) $algos[$a]['winners']++;
            if ($p['return_pct'] < -0.5) $algos[$a]['losers']++;
        }
    }

    $result = array();
    foreach ($algos as $name => $data) {
        $avg = ($data['picks'] > 0) ? round($data['total_return'] / $data['picks'], 2) : 0;
        $wr = ($data['winners'] + $data['losers'] > 0)
            ? round($data['winners'] / ($data['winners'] + $data['losers']) * 100, 1) : 0;
        $result[] = array(
            'algorithm' => $name,
            'picks' => $data['picks'],
            'avg_return' => $avg,
            'winners' => $data['winners'],
            'losers' => $data['losers'],
            'win_rate' => $wr,
            'grade' => ($avg > 1.5) ? 'A' : (($avg > 0.5) ? 'B' : (($avg > -0.5) ? 'C' : (($avg > -1.5) ? 'D' : 'F')))
        );
    }

    usort($result, create_function('$a,$b', 'if ($a["avg_return"] == $b["avg_return"]) return 0; return ($a["avg_return"] > $b["avg_return"]) ? -1 : 1;'));
    return $result;
}

// Generate auto-notes for each pick
function _cp_generate_auto_notes($conn, $all_picks, $sector_perf, $algo_perf) {
    // Build lookup maps
    $sector_map = array();
    foreach ($sector_perf as $s) { $sector_map[$s['sector']] = $s; }
    $algo_map = array();
    foreach ($algo_perf as $a) { $algo_map[$a['algorithm']] = $a; }

    $diagnosed = array();
    foreach ($all_picks as $p) {
        $notes = array();
        $severity = 'info'; // info, warning, danger

        // ── Note 1: Stale price data ──
        if ($p['price_age_days'] >= 3) {
            $notes[] = array(
                'type' => 'stale_data',
                'icon' => 'clock',
                'text' => 'Price data is ' . $p['price_age_days'] . ' days old. Return calculation may be inaccurate. Actual loss/gain could differ significantly.',
                'severity' => 'warning'
            );
            $severity = 'warning';
        }

        // ── Note 2: No price data ──
        if ($p['latest_price'] <= 0) {
            $notes[] = array(
                'type' => 'no_data',
                'icon' => 'alert',
                'text' => 'No pricing data available in our database. This ticker may be delisted, renamed, or not tracked by Yahoo Finance.',
                'severity' => 'danger'
            );
            $severity = 'danger';
        }

        // ── Note 3: Sector weakness ──
        $sec = isset($sector_map[$p['sector']]) ? $sector_map[$p['sector']] : null;
        if ($sec && $sec['avg_return'] < -1) {
            $notes[] = array(
                'type' => 'sector_weak',
                'icon' => 'trending-down',
                'text' => $p['sector'] . ' sector is underperforming (avg ' . $sec['avg_return'] . '%). '
                        . $sec['losers'] . ' of ' . $sec['picks'] . ' picks in this sector are losing. '
                        . 'Possible sector rotation away from ' . $p['sector'] . '.',
                'severity' => 'warning'
            );
            if ($severity !== 'danger') $severity = 'warning';
        } elseif ($sec && $sec['avg_return'] > 1) {
            $notes[] = array(
                'type' => 'sector_strong',
                'icon' => 'trending-up',
                'text' => $p['sector'] . ' sector is outperforming (avg +' . $sec['avg_return'] . '%). '
                        . $sec['winners'] . ' of ' . $sec['picks'] . ' picks are winning.',
                'severity' => 'info'
            );
        }

        // ── Note 4: Momentum divergence (high consensus but losing) ──
        if ($p['consensus_count'] >= 5 && $p['return_pct'] < -1) {
            $notes[] = array(
                'type' => 'momentum_lag',
                'icon' => 'disconnect',
                'text' => 'High consensus (' . $p['consensus_count'] . ' algos) but losing '
                        . $p['return_pct'] . '%. Multiple algorithms detected old momentum that has since reversed. '
                        . 'This is momentum lag — algos are reacting to PAST price action, not current trend.',
                'severity' => 'danger'
            );
            $severity = 'danger';
        }

        // ── Note 5: Algorithm quality check ──
        $good_algos = 0;
        $bad_algos = 0;
        $bad_names = array();
        foreach ($p['algo_names'] as $a) {
            if (isset($algo_map[$a])) {
                if ($algo_map[$a]['avg_return'] > 0.5) $good_algos++;
                if ($algo_map[$a]['avg_return'] < -0.5) {
                    $bad_algos++;
                    $bad_names[] = $a . ' (avg ' . $algo_map[$a]['avg_return'] . '%)';
                }
            }
        }
        if ($bad_algos > $good_algos && $bad_algos >= 2) {
            $notes[] = array(
                'type' => 'weak_algos',
                'icon' => 'warning',
                'text' => 'Supported by underperforming algorithms: ' . implode(', ', array_slice($bad_names, 0, 3))
                        . '. These algos have negative avg returns across all their picks.',
                'severity' => 'warning'
            );
            if ($severity !== 'danger') $severity = 'warning';
        }

        // ── Note 6: Pick age vs return (stagnant picks) ──
        if ($p['pick_age_days'] >= 7 && abs($p['return_pct']) < 1) {
            $notes[] = array(
                'type' => 'stagnant',
                'icon' => 'pause',
                'text' => 'Pick is ' . $p['pick_age_days'] . ' days old with only '
                        . ($p['return_pct'] >= 0 ? '+' : '') . $p['return_pct'] . '% return. '
                        . 'The thesis may be stale. Consider whether the catalysts that triggered this pick are still valid.',
                'severity' => 'info'
            );
        }

        // ── Note 7: Falling knife detection ──
        if ($p['return_pct'] < -5) {
            $notes[] = array(
                'type' => 'falling_knife',
                'icon' => 'alert-triangle',
                'text' => 'Down ' . $p['return_pct'] . '% — this is a significant loss. '
                        . 'The algorithms may be catching a falling knife. '
                        . 'Momentum reversal is not guaranteed; the drop may continue.',
                'severity' => 'danger'
            );
            $severity = 'danger';
        }

        // ── Note 8: Winner riding well ──
        if ($p['return_pct'] > 3) {
            $notes[] = array(
                'type' => 'strong_winner',
                'icon' => 'rocket',
                'text' => 'Up +' . $p['return_pct'] . '% — thesis is executing. '
                        . ($p['consensus_count'] >= 5 ? 'Strong consensus backing (' . $p['consensus_count'] . ' algos).' : '')
                        . ' Consider taking partial profits if near take-profit target.',
                'severity' => 'info'
            );
        }

        // ── Note 9: Low consensus warning ──
        if ($p['consensus_count'] <= 2 && $p['return_pct'] < 0) {
            $notes[] = array(
                'type' => 'low_consensus',
                'icon' => 'caution',
                'text' => 'Only ' . $p['consensus_count'] . ' algorithms agree on this pick and it\'s losing. '
                        . 'Low-consensus picks have higher uncertainty.',
                'severity' => 'warning'
            );
            if ($severity !== 'danger') $severity = 'warning';
        }

        // Build summary diagnosis
        $summary = '';
        if ($p['return_pct'] < -3) {
            $summary = 'Significant loss. ';
            if ($sec && $sec['avg_return'] < -1) $summary .= 'Sector rotation is the primary driver. ';
            if ($p['consensus_count'] >= 5) $summary .= 'Momentum lag — algos reacting to old signals. ';
            if ($p['price_age_days'] >= 3) $summary .= 'Stale price data may overstate the loss. ';
        } elseif ($p['return_pct'] < -1) {
            $summary = 'Moderate loss. ';
            if ($sec && $sec['avg_return'] < -1) $summary .= 'Sector headwinds contributing. ';
            if ($p['price_age_days'] >= 3) $summary .= 'Pending price update. ';
        } elseif ($p['return_pct'] < 0) {
            $summary = 'Slight loss — within normal range. Monitor for trend reversal.';
        } elseif ($p['return_pct'] > 3) {
            $summary = 'Strong performer. Thesis executing well.';
        } elseif ($p['return_pct'] > 0) {
            $summary = 'Slight gain — on track. ';
            if ($sec && $sec['avg_return'] > 1) $summary .= 'Sector tailwinds supporting. ';
        } else {
            $summary = 'Flat — no significant movement yet.';
        }

        $p['diagnosis'] = array(
            'notes' => $notes,
            'severity' => $severity,
            'summary' => trim($summary),
            'note_count' => count($notes)
        );
        $diagnosed[] = $p;
    }

    return $diagnosed;
}

// Generate market-level notes
function _cp_generate_market_notes($all_picks, $sector_perf, $algo_perf) {
    $notes = array();

    // Count overall
    $winners = 0;
    $losers = 0;
    $total_return = 0;
    foreach ($all_picks as $p) {
        if ($p['return_pct'] > 0.5) $winners++;
        if ($p['return_pct'] < -0.5) $losers++;
        $total_return += $p['return_pct'];
    }
    $total = count($all_picks);
    $avg_return = ($total > 0) ? round($total_return / $total, 2) : 0;

    // Market overview
    $notes[] = array(
        'type' => 'overview',
        'title' => 'Market Overview',
        'text' => $total . ' consensus picks tracked. ' . $winners . ' winning, ' . $losers . ' losing. '
                . 'Average return: ' . ($avg_return >= 0 ? '+' : '') . $avg_return . '%.',
        'severity' => ($avg_return >= 0.5) ? 'positive' : (($avg_return < -0.5) ? 'negative' : 'neutral')
    );

    // Sector rotation detection
    $strong_sectors = array();
    $weak_sectors = array();
    foreach ($sector_perf as $s) {
        if ($s['avg_return'] > 1) $strong_sectors[] = $s['sector'] . ' (+' . $s['avg_return'] . '%)';
        if ($s['avg_return'] < -1) $weak_sectors[] = $s['sector'] . ' (' . $s['avg_return'] . '%)';
    }

    if (count($weak_sectors) > 0 && count($strong_sectors) > 0) {
        $notes[] = array(
            'type' => 'sector_rotation',
            'title' => 'Sector Rotation Detected',
            'text' => 'Money flowing INTO: ' . implode(', ', $strong_sectors) . '. '
                    . 'Money flowing OUT OF: ' . implode(', ', $weak_sectors) . '. '
                    . 'Algorithms picking stocks in weak sectors will underperform until rotation reverses.',
            'severity' => 'warning'
        );
    }

    // Algorithm grading
    $f_algos = array();
    $a_algos = array();
    foreach ($algo_perf as $a) {
        if ($a['grade'] === 'F' && $a['picks'] >= 3) $f_algos[] = $a['algorithm'] . ' (' . $a['avg_return'] . '%)';
        if ($a['grade'] === 'A' && $a['picks'] >= 3) $a_algos[] = $a['algorithm'] . ' (+' . $a['avg_return'] . '%)';
    }

    if (count($f_algos) > 0) {
        $notes[] = array(
            'type' => 'algo_underperform',
            'title' => 'Underperforming Algorithms (Grade F)',
            'text' => 'These algorithms are consistently losing: ' . implode(', ', array_slice($f_algos, 0, 5))
                    . '. Consider reducing their weight in consensus scoring or filtering out their picks.',
            'severity' => 'danger'
        );
    }

    if (count($a_algos) > 0) {
        $notes[] = array(
            'type' => 'algo_outperform',
            'title' => 'Top Performing Algorithms (Grade A)',
            'text' => 'Reliable algorithms: ' . implode(', ', array_slice($a_algos, 0, 5))
                    . '. Consider increasing their weight in consensus scoring.',
            'severity' => 'positive'
        );
    }

    // Momentum lag warning
    $high_cons_losers = 0;
    foreach ($all_picks as $p) {
        if ($p['consensus_count'] >= 5 && $p['return_pct'] < -1) $high_cons_losers++;
    }
    if ($high_cons_losers >= 3) {
        $notes[] = array(
            'type' => 'momentum_lag',
            'title' => 'Momentum Lag Warning',
            'text' => $high_cons_losers . ' high-consensus picks (5+ algos) are losing more than 1%. '
                    . 'Multiple algorithms are detecting stale momentum signals. '
                    . 'The market may be turning — algorithmic consensus is a lagging indicator.',
            'severity' => 'danger'
        );
    }

    // Stale data warning
    $stale_count = 0;
    foreach ($all_picks as $p) {
        if ($p['price_age_days'] >= 3) $stale_count++;
    }
    if ($stale_count >= 5) {
        $notes[] = array(
            'type' => 'stale_data',
            'title' => 'Stale Price Data',
            'text' => $stale_count . ' picks have price data 3+ days old. '
                    . 'Returns may be significantly different once prices update. '
                    . 'Run the daily price refresh to get current data.',
            'severity' => 'warning'
        );
    }

    return $notes;
}

// Diagnose challenge performance
function _cp_diagnose_challenge($conn) {
    $notes = array();

    $r = $conn->query("SELECT mode, SUM(daily_pnl) as total_pnl, COUNT(*) as days,
                              SUM(wins) as wins, SUM(losses) as losses,
                              SUM(target_hit) as hits
                       FROM challenge_200_days GROUP BY mode");
    if (!$r) return $notes;

    while ($row = $r->fetch_assoc()) {
        $mode = $row['mode'];
        $pnl = round((float)$row['total_pnl'], 2);
        $days = (int)$row['days'];
        $wins = (int)$row['wins'];
        $losses = (int)$row['losses'];
        $hits = (int)$row['hits'];
        $wr = ($wins + $losses > 0) ? round($wins / ($wins + $losses) * 100, 1) : 0;
        $avg_daily = ($days > 0) ? round($pnl / $days, 2) : 0;

        $text = ucfirst($mode) . ' mode: ';
        if ($pnl < 0) {
            $text .= 'Net loss of $' . abs($pnl) . ' over ' . $days . ' day(s). ';
            $text .= $wr . '% trade win rate (' . $wins . 'W/' . $losses . 'L). ';
            if ($wr < 50) {
                $text .= 'More losing trades than winning — need better pick selection or tighter stops.';
            } else {
                $text .= 'Win rate is OK but losses are larger than wins — consider tighter stop-losses.';
            }
        } else {
            $text .= 'Net profit of $' . $pnl . ' over ' . $days . ' day(s). ';
            $text .= $wr . '% trade win rate. ';
            if ($hits > 0) {
                $text .= 'Hit $200 target ' . $hits . '/' . $days . ' days.';
            } else {
                $text .= 'Has not yet hit $200 target. Avg daily: $' . $avg_daily . '.';
            }
        }

        $notes[] = array(
            'mode' => $mode,
            'pnl' => $pnl,
            'days' => $days,
            'win_rate' => $wr,
            'avg_daily_pnl' => $avg_daily,
            'text' => $text,
            'severity' => ($pnl >= 0) ? 'positive' : 'negative'
        );
    }

    // Compare modes
    if (count($notes) >= 2) {
        $consensus_pnl = 0;
        $ml_pnl = 0;
        foreach ($notes as $n) {
            if ($n['mode'] === 'consensus') $consensus_pnl = $n['pnl'];
            if ($n['mode'] === 'ml') $ml_pnl = $n['pnl'];
        }
        $diff = round($ml_pnl - $consensus_pnl, 2);
        $comparison = 'ML mode is ' . ($diff > 0 ? 'outperforming' : 'underperforming')
                    . ' consensus by $' . abs($diff) . '. ';
        if ($diff > 0) {
            $comparison .= 'The self-learning adjustments are adding value — ML picks better stocks.';
        } else {
            $comparison .= 'The ML adjustments are not yet helping. More training data (closed trades) is needed.';
        }
        $notes[] = array(
            'mode' => 'comparison',
            'text' => $comparison,
            'severity' => ($diff > 0) ? 'positive' : 'negative',
            'ml_advantage' => $diff
        );
    }

    return $notes;
}
?>
