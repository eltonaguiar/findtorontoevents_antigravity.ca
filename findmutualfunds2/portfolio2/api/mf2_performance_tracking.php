<?php
/**
 * Mutual Funds Forward Performance Tracking API
 * Tracks MF algorithm pick outcomes honestly, self-learns patterns.
 * Modeled after findstocks consensus_performance.php.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   track           - (admin) Import picks, update NAVs, check exits, record daily snapshot
 *   dashboard       - Performance summary stats + chart data (public)
 *   positions       - Open positions + recent closed (public)
 *   close_position  - (admin) Manually close a position by id
 *
 * Usage:
 *   GET .../mf2_performance_tracking.php?action=track&key=livetrader2026
 *   GET .../mf2_performance_tracking.php?action=dashboard
 *   GET .../mf2_performance_tracking.php?action=positions
 *   GET .../mf2_performance_tracking.php?action=close_position&id=42&key=livetrader2026
 */
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/mf2_performance_tracking_schema.php';

// Ensure tables exist
mf2_ensure_tracking_schema($conn);

$action = isset($_GET['action']) ? trim($_GET['action']) : 'dashboard';
$admin_key = 'livetrader2026';
$is_admin = (isset($_GET['key']) && $_GET['key'] === $admin_key);

// ── Exit condition thresholds for mutual funds ──
$tp_pct = 5.0;     // Take profit at +5%
$sl_pct = 3.0;     // Stop loss at -3%
$max_hold = 90;     // Max hold 90 days (MFs are slower-moving)


// ═══════════════════════════════════════════
// TRACK — Import, update NAVs, check exits (admin)
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
    $imported = 0;
    $updated = 0;
    $closed = 0;

    // ── Step 1: Import open picks from mf2_fund_picks not already tracked ──
    $picks_res = $conn->query(
        "SELECT fp.symbol, fp.algorithm_name, fp.pick_date, fp.entry_nav, fp.score, fp.rating
         FROM mf2_fund_picks fp
         LEFT JOIN mf2_tracked_picks tp
           ON tp.symbol = fp.symbol
           AND tp.algorithm_name = fp.algorithm_name
           AND tp.pick_date = fp.pick_date
         WHERE tp.id IS NULL
           AND fp.entry_nav > 0
         ORDER BY fp.pick_date DESC"
    );
    if ($picks_res) {
        while ($row = $picks_res->fetch_assoc()) {
            $safe_sym  = $conn->real_escape_string($row['symbol']);
            $safe_algo = $conn->real_escape_string($row['algorithm_name']);
            $safe_date = $conn->real_escape_string($row['pick_date']);
            $entry_nav = (float)$row['entry_nav'];
            $score     = round((float)$row['score'], 2);
            $rating    = $conn->real_escape_string($row['rating']);

            $sql = "INSERT INTO mf2_tracked_picks
                (symbol, algorithm_name, pick_date, entry_nav, current_nav,
                 current_return_pct, status, peak_nav, trough_nav,
                 hold_days, score, rating, created_at)
                VALUES
                ('$safe_sym', '$safe_algo', '$safe_date', $entry_nav, $entry_nav,
                 0, 'open', $entry_nav, $entry_nav,
                 0, $score, '$rating', '$now')";
            if ($conn->query($sql)) {
                $imported++;
            }
            // Silently skip duplicates (UNIQUE key prevents double-insert)
        }
    }

    // ── Step 2: Update all open positions with latest NAV ──
    $open_res = $conn->query(
        "SELECT id, symbol, entry_nav, pick_date, peak_nav, trough_nav
         FROM mf2_tracked_picks
         WHERE status = 'open'"
    );
    if ($open_res) {
        while ($row = $open_res->fetch_assoc()) {
            $pos_id    = (int)$row['id'];
            $symbol    = $row['symbol'];
            $entry_nav = (float)$row['entry_nav'];
            $pick_date = $row['pick_date'];
            $peak_nav  = (float)$row['peak_nav'];
            $trough_nav = (float)$row['trough_nav'];

            $safe_sym = $conn->real_escape_string($symbol);

            // Get latest NAV from mf2_nav_history
            $latest_nav = 0;
            $nav_res = $conn->query(
                "SELECT nav FROM mf2_nav_history WHERE symbol = '$safe_sym' ORDER BY nav_date DESC LIMIT 1"
            );
            if ($nav_res && $nav_res->num_rows > 0) {
                $nav_row = $nav_res->fetch_assoc();
                $latest_nav = (float)$nav_row['nav'];
            }

            // Skip if no NAV data available yet
            if ($latest_nav <= 0) {
                continue;
            }

            // Calculate return
            $return_pct = 0;
            if ($entry_nav > 0) {
                $return_pct = round(($latest_nav - $entry_nav) / $entry_nav * 100, 4);
            }

            // Update peak and trough
            if ($latest_nav > $peak_nav) {
                $peak_nav = $latest_nav;
            }
            if ($trough_nav <= 0 || $latest_nav < $trough_nav) {
                $trough_nav = $latest_nav;
            }

            // Calculate hold days
            $hold_days = max(0, (int)((time() - strtotime($pick_date)) / 86400));

            // ── Step 3: Check exit conditions ──
            $exit_reason = '';
            if ($return_pct >= $tp_pct) {
                $exit_reason = 'tp_hit';
            } elseif ($return_pct <= -$sl_pct) {
                $exit_reason = 'sl_hit';
            } elseif ($hold_days >= $max_hold) {
                $exit_reason = 'max_hold';
            }

            if ($exit_reason !== '') {
                // ── Step 4: Close position ──
                $safe_reason = $conn->real_escape_string($exit_reason);
                $conn->query("UPDATE mf2_tracked_picks SET
                    current_nav = $latest_nav,
                    current_return_pct = $return_pct,
                    peak_nav = $peak_nav,
                    trough_nav = $trough_nav,
                    hold_days = $hold_days,
                    status = 'closed',
                    exit_date = '$today',
                    exit_nav = $latest_nav,
                    exit_reason = '$safe_reason',
                    final_return_pct = $return_pct
                    WHERE id = $pos_id");
                $closed++;
            } else {
                // Update open position
                $conn->query("UPDATE mf2_tracked_picks SET
                    current_nav = $latest_nav,
                    current_return_pct = $return_pct,
                    peak_nav = $peak_nav,
                    trough_nav = $trough_nav,
                    hold_days = $hold_days
                    WHERE id = $pos_id");
                $updated++;
            }
        }
    }

    // ── Step 5: Record daily snapshot ──
    $snapshot = _mf2_record_daily_snapshot($conn, $today, $now);

    // ── Step 6: Run pattern detection (if 5+ closed trades) ──
    $lessons_detected = _mf2_detect_lessons($conn, $today, $now);

    echo json_encode(array(
        'ok' => true,
        'action' => 'track',
        'imported' => $imported,
        'updated' => $updated,
        'closed' => $closed,
        'lessons_detected' => $lessons_detected,
        'snapshot' => $snapshot,
        'tracked_at' => $now
    ));


// ═══════════════════════════════════════════
// DASHBOARD — Performance summary (public)
// ═══════════════════════════════════════════
} elseif ($action === 'dashboard') {

    // Overall stats
    $total_open = 0;
    $total_closed = 0;
    $total_wins = 0;
    $total_losses = 0;

    $r = $conn->query("SELECT COUNT(*) AS cnt FROM mf2_tracked_picks WHERE status = 'open'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $total_open = (int)$row['cnt']; }

    $r = $conn->query("SELECT COUNT(*) AS cnt FROM mf2_tracked_picks WHERE status = 'closed'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $total_closed = (int)$row['cnt']; }

    $r = $conn->query("SELECT COUNT(*) AS cnt FROM mf2_tracked_picks WHERE status = 'closed' AND final_return_pct > 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $total_wins = (int)$row['cnt']; }

    $r = $conn->query("SELECT COUNT(*) AS cnt FROM mf2_tracked_picks WHERE status = 'closed' AND final_return_pct <= 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $total_losses = (int)$row['cnt']; }

    $win_rate = ($total_closed > 0) ? round($total_wins / $total_closed * 100, 1) : 0;

    // Avg returns
    $avg_win = 0;
    $avg_loss = 0;
    $avg_return = 0;

    $r = $conn->query("SELECT AVG(final_return_pct) AS avg_r FROM mf2_tracked_picks WHERE status = 'closed' AND final_return_pct > 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_win = round((float)$row['avg_r'], 2); }

    $r = $conn->query("SELECT AVG(final_return_pct) AS avg_r FROM mf2_tracked_picks WHERE status = 'closed' AND final_return_pct <= 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_loss = round((float)$row['avg_r'], 2); }

    $r = $conn->query("SELECT AVG(final_return_pct) AS avg_r FROM mf2_tracked_picks WHERE status = 'closed'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_return = round((float)$row['avg_r'], 2); }

    // Avg hold days
    $avg_hold = 0;
    $r = $conn->query("SELECT AVG(hold_days) AS avg_h FROM mf2_tracked_picks WHERE status = 'closed'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_hold = round((float)$row['avg_h'], 1); }

    // Best and worst closed fund
    $best = array('symbol' => '-', 'return_pct' => 0);
    $worst = array('symbol' => '-', 'return_pct' => 0);

    $r = $conn->query("SELECT symbol, final_return_pct FROM mf2_tracked_picks WHERE status = 'closed' ORDER BY final_return_pct DESC LIMIT 1");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $best = array('symbol' => $row['symbol'], 'return_pct' => (float)$row['final_return_pct']); }

    $r = $conn->query("SELECT symbol, final_return_pct FROM mf2_tracked_picks WHERE status = 'closed' ORDER BY final_return_pct ASC LIMIT 1");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $worst = array('symbol' => $row['symbol'], 'return_pct' => (float)$row['final_return_pct']); }

    // Profit factor
    $sum_wins = 0;
    $sum_losses = 0;
    $r = $conn->query("SELECT SUM(final_return_pct) AS s FROM mf2_tracked_picks WHERE status = 'closed' AND final_return_pct > 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sum_wins = (float)$row['s']; }
    $r = $conn->query("SELECT SUM(ABS(final_return_pct)) AS s FROM mf2_tracked_picks WHERE status = 'closed' AND final_return_pct <= 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sum_losses = (float)$row['s']; }
    $profit_factor = ($sum_losses > 0) ? round($sum_wins / $sum_losses, 2) : 0;

    // Exit reason distribution
    $exit_reasons = array();
    $r = $conn->query("SELECT exit_reason, COUNT(*) AS cnt, AVG(final_return_pct) AS avg_ret
                       FROM mf2_tracked_picks WHERE status = 'closed' AND exit_reason IS NOT NULL
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

    // Recent lessons (last 5)
    $recent_lessons = array();
    $r = $conn->query("SELECT lesson_date, lesson_type, lesson_title, lesson_text, confidence
                       FROM mf2_tracking_lessons
                       ORDER BY lesson_date DESC, confidence DESC LIMIT 5");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $recent_lessons[] = $row;
        }
    }

    // Daily snapshots (last 30 days) for charting
    $daily_snapshots = array();
    $r = $conn->query("SELECT track_date, open_positions, total_closed, total_wins, total_losses,
                              win_rate, avg_win_pct, avg_loss_pct, avg_return_pct,
                              best_symbol, worst_symbol, avg_hold_days
                       FROM mf2_tracking_daily
                       ORDER BY track_date DESC LIMIT 30");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $daily_snapshots[] = array(
                'date' => $row['track_date'],
                'open_positions' => (int)$row['open_positions'],
                'total_closed' => (int)$row['total_closed'],
                'total_wins' => (int)$row['total_wins'],
                'total_losses' => (int)$row['total_losses'],
                'win_rate' => (float)$row['win_rate'],
                'avg_win_pct' => (float)$row['avg_win_pct'],
                'avg_loss_pct' => (float)$row['avg_loss_pct'],
                'avg_return_pct' => (float)$row['avg_return_pct'],
                'best_symbol' => $row['best_symbol'],
                'worst_symbol' => $row['worst_symbol'],
                'avg_hold_days' => (float)$row['avg_hold_days']
            );
        }
    }

    // Algorithm breakdown for open positions
    $algo_breakdown = array();
    $r = $conn->query("SELECT algorithm_name, COUNT(*) AS cnt,
                              AVG(current_return_pct) AS avg_ret,
                              AVG(hold_days) AS avg_hold
                       FROM mf2_tracked_picks WHERE status = 'open'
                       GROUP BY algorithm_name ORDER BY avg_ret DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $algo_breakdown[] = array(
                'algorithm' => $row['algorithm_name'],
                'open_positions' => (int)$row['cnt'],
                'avg_current_return' => round((float)$row['avg_ret'], 2),
                'avg_hold_days' => round((float)$row['avg_hold'], 1)
            );
        }
    }

    echo json_encode(array(
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
            'avg_return_pct' => $avg_return,
            'profit_factor' => $profit_factor,
            'avg_hold_days' => $avg_hold,
            'best_fund' => $best,
            'worst_fund' => $worst
        ),
        'exit_reasons' => $exit_reasons,
        'algo_breakdown' => $algo_breakdown,
        'recent_lessons' => $recent_lessons,
        'daily_snapshots' => $daily_snapshots,
        'generated_at' => date('Y-m-d H:i:s')
    ));


// ═══════════════════════════════════════════
// POSITIONS — All tracked picks with status (public)
// ═══════════════════════════════════════════
} elseif ($action === 'positions') {
    $status_filter = isset($_GET['status']) ? $_GET['status'] : 'all';

    // Open positions sorted by current return DESC
    $open = array();
    $r = $conn->query("SELECT id, symbol, algorithm_name, pick_date, entry_nav, current_nav,
                              current_return_pct, peak_nav, trough_nav, hold_days, score, rating,
                              created_at
                       FROM mf2_tracked_picks
                       WHERE status = 'open'
                       ORDER BY current_return_pct DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $open[] = array(
                'id' => (int)$row['id'],
                'symbol' => $row['symbol'],
                'algorithm_name' => $row['algorithm_name'],
                'pick_date' => $row['pick_date'],
                'entry_nav' => (float)$row['entry_nav'],
                'current_nav' => ($row['current_nav'] !== null) ? (float)$row['current_nav'] : null,
                'current_return_pct' => ($row['current_return_pct'] !== null) ? (float)$row['current_return_pct'] : null,
                'peak_nav' => ($row['peak_nav'] !== null) ? (float)$row['peak_nav'] : null,
                'trough_nav' => ($row['trough_nav'] !== null) ? (float)$row['trough_nav'] : null,
                'hold_days' => (int)$row['hold_days'],
                'score' => ($row['score'] !== null) ? (float)$row['score'] : null,
                'rating' => $row['rating'],
                'status' => 'open',
                'created_at' => $row['created_at']
            );
        }
    }

    // Closed positions (recent, limited)
    $closed = array();
    $limit = isset($_GET['limit']) ? max(1, min(100, (int)$_GET['limit'])) : 30;
    $r = $conn->query("SELECT id, symbol, algorithm_name, pick_date, entry_nav, current_nav,
                              current_return_pct, exit_date, exit_nav, exit_reason,
                              final_return_pct, peak_nav, trough_nav, hold_days, score, rating,
                              created_at
                       FROM mf2_tracked_picks
                       WHERE status = 'closed'
                       ORDER BY exit_date DESC, id DESC LIMIT $limit");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $closed[] = array(
                'id' => (int)$row['id'],
                'symbol' => $row['symbol'],
                'algorithm_name' => $row['algorithm_name'],
                'pick_date' => $row['pick_date'],
                'entry_nav' => (float)$row['entry_nav'],
                'exit_date' => $row['exit_date'],
                'exit_nav' => ($row['exit_nav'] !== null) ? (float)$row['exit_nav'] : null,
                'exit_reason' => $row['exit_reason'],
                'final_return_pct' => ($row['final_return_pct'] !== null) ? (float)$row['final_return_pct'] : null,
                'peak_nav' => ($row['peak_nav'] !== null) ? (float)$row['peak_nav'] : null,
                'trough_nav' => ($row['trough_nav'] !== null) ? (float)$row['trough_nav'] : null,
                'hold_days' => (int)$row['hold_days'],
                'score' => ($row['score'] !== null) ? (float)$row['score'] : null,
                'rating' => $row['rating'],
                'status' => 'closed',
                'created_at' => $row['created_at']
            );
        }
    }

    // Filter output if requested
    $result_open = $open;
    $result_closed = $closed;
    if ($status_filter === 'open') {
        $result_closed = array();
    } elseif ($status_filter === 'closed') {
        $result_open = array();
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'positions',
        'open' => $result_open,
        'open_count' => count($result_open),
        'closed' => $result_closed,
        'closed_count' => count($result_closed)
    ));


// ═══════════════════════════════════════════
// CLOSE_POSITION — Manually close by id (admin)
// ═══════════════════════════════════════════
} elseif ($action === 'close_position') {
    if (!$is_admin) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Admin key required'));
        $conn->close();
        exit;
    }

    $pos_id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    if ($pos_id <= 0) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing or invalid id parameter'));
        $conn->close();
        exit;
    }

    $now = date('Y-m-d H:i:s');
    $today = date('Y-m-d');

    // Fetch the position
    $r = $conn->query("SELECT id, symbol, entry_nav, pick_date, current_nav, current_return_pct, status
                       FROM mf2_tracked_picks WHERE id = $pos_id LIMIT 1");
    if (!$r || $r->num_rows == 0) {
        header('HTTP/1.0 404 Not Found');
        echo json_encode(array('ok' => false, 'error' => 'Position not found'));
        $conn->close();
        exit;
    }

    $pos = $r->fetch_assoc();
    if ($pos['status'] === 'closed') {
        echo json_encode(array('ok' => false, 'error' => 'Position already closed'));
        $conn->close();
        exit;
    }

    $entry_nav = (float)$pos['entry_nav'];
    $current_nav = (float)$pos['current_nav'];
    $return_pct = ($pos['current_return_pct'] !== null) ? (float)$pos['current_return_pct'] : 0;
    $hold_days = max(0, (int)((time() - strtotime($pos['pick_date'])) / 86400));

    // If we have a current NAV, use it; otherwise try to get latest
    if ($current_nav <= 0) {
        $safe_sym = $conn->real_escape_string($pos['symbol']);
        $nav_res = $conn->query("SELECT nav FROM mf2_nav_history WHERE symbol = '$safe_sym' ORDER BY nav_date DESC LIMIT 1");
        if ($nav_res && $nav_res->num_rows > 0) {
            $nav_row = $nav_res->fetch_assoc();
            $current_nav = (float)$nav_row['nav'];
            if ($entry_nav > 0 && $current_nav > 0) {
                $return_pct = round(($current_nav - $entry_nav) / $entry_nav * 100, 4);
            }
        }
    }

    $conn->query("UPDATE mf2_tracked_picks SET
        status = 'closed',
        exit_date = '$today',
        exit_nav = $current_nav,
        exit_reason = 'manual',
        final_return_pct = $return_pct,
        current_nav = $current_nav,
        current_return_pct = $return_pct,
        hold_days = $hold_days
        WHERE id = $pos_id");

    echo json_encode(array(
        'ok' => true,
        'action' => 'close_position',
        'id' => $pos_id,
        'symbol' => $pos['symbol'],
        'exit_nav' => $current_nav,
        'final_return_pct' => $return_pct,
        'hold_days' => $hold_days,
        'exit_reason' => 'manual',
        'closed_at' => $now
    ));


// ═══════════════════════════════════════════
// UNKNOWN ACTION
// ═══════════════════════════════════════════
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action. Use: track, dashboard, positions, close_position'));
}

$conn->close();


// ═══════════════════════════════════════════════════════════════
// HELPER: Record daily performance snapshot
// ═══════════════════════════════════════════════════════════════
function _mf2_record_daily_snapshot($conn, $today, $now) {
    $open = 0;
    $closed_total = 0;
    $wins = 0;
    $losses = 0;

    $r = $conn->query("SELECT COUNT(*) AS c FROM mf2_tracked_picks WHERE status = 'open'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $open = (int)$row['c']; }

    $r = $conn->query("SELECT COUNT(*) AS c FROM mf2_tracked_picks WHERE status = 'closed'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $closed_total = (int)$row['c']; }

    $r = $conn->query("SELECT COUNT(*) AS c FROM mf2_tracked_picks WHERE status = 'closed' AND final_return_pct > 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $wins = (int)$row['c']; }

    $r = $conn->query("SELECT COUNT(*) AS c FROM mf2_tracked_picks WHERE status = 'closed' AND final_return_pct <= 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $losses = (int)$row['c']; }

    $wr = ($closed_total > 0) ? round($wins / $closed_total * 100, 2) : 0;

    $avg_win = 0;
    $avg_loss = 0;
    $avg_return = 0;
    $avg_hold = 0;

    $r = $conn->query("SELECT AVG(final_return_pct) AS a FROM mf2_tracked_picks WHERE status = 'closed' AND final_return_pct > 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_win = round((float)$row['a'], 4); }

    $r = $conn->query("SELECT AVG(final_return_pct) AS a FROM mf2_tracked_picks WHERE status = 'closed' AND final_return_pct <= 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_loss = round((float)$row['a'], 4); }

    $r = $conn->query("SELECT AVG(final_return_pct) AS a FROM mf2_tracked_picks WHERE status = 'closed'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_return = round((float)$row['a'], 4); }

    $r = $conn->query("SELECT AVG(hold_days) AS a FROM mf2_tracked_picks WHERE status = 'closed'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $avg_hold = round((float)$row['a'], 1); }

    // Best/worst closed fund
    $best_sym = '';
    $worst_sym = '';
    $r = $conn->query("SELECT symbol FROM mf2_tracked_picks WHERE status = 'closed' ORDER BY final_return_pct DESC LIMIT 1");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $best_sym = $row['symbol']; }
    $r = $conn->query("SELECT symbol FROM mf2_tracked_picks WHERE status = 'closed' ORDER BY final_return_pct ASC LIMIT 1");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $worst_sym = $row['symbol']; }

    $safe_best = $conn->real_escape_string($best_sym);
    $safe_worst = $conn->real_escape_string($worst_sym);

    $conn->query("INSERT INTO mf2_tracking_daily
        (track_date, open_positions, total_closed, total_wins, total_losses,
         win_rate, avg_win_pct, avg_loss_pct, avg_return_pct,
         best_symbol, worst_symbol, avg_hold_days, created_at)
        VALUES ('$today', $open, $closed_total, $wins, $losses,
         $wr, $avg_win, $avg_loss, $avg_return,
         '$safe_best', '$safe_worst', $avg_hold, '$now')
        ON DUPLICATE KEY UPDATE
         open_positions = $open, total_closed = $closed_total,
         total_wins = $wins, total_losses = $losses,
         win_rate = $wr, avg_win_pct = $avg_win,
         avg_loss_pct = $avg_loss, avg_return_pct = $avg_return,
         best_symbol = '$safe_best', worst_symbol = '$safe_worst',
         avg_hold_days = $avg_hold");

    return array(
        'date' => $today,
        'open_positions' => $open,
        'total_closed' => $closed_total,
        'total_wins' => $wins,
        'total_losses' => $losses,
        'win_rate' => $wr,
        'avg_win_pct' => $avg_win,
        'avg_loss_pct' => $avg_loss,
        'avg_return_pct' => $avg_return,
        'best_symbol' => $best_sym,
        'worst_symbol' => $worst_sym,
        'avg_hold_days' => $avg_hold
    );
}


// ═══════════════════════════════════════════════════════════════
// HELPER: Self-learning — detect patterns from closed trades
// ═══════════════════════════════════════════════════════════════
function _mf2_detect_lessons($conn, $today, $now) {
    $lessons_added = 0;
    $min_samples = 5;

    // Check if we have enough closed trades
    $r = $conn->query("SELECT COUNT(*) AS c FROM mf2_tracked_picks WHERE status = 'closed'");
    if (!$r || $r->num_rows == 0) return 0;
    $row = $r->fetch_assoc();
    $total_closed = (int)$row['c'];
    if ($total_closed < $min_samples) return 0;

    // ── Pattern 1: Algorithm Win Rate Patterns ──
    // Which algorithms produce the best mutual fund results?
    $algo_stats = array();
    $r = $conn->query("SELECT algorithm_name,
                              COUNT(*) AS cnt,
                              AVG(final_return_pct) AS avg_ret,
                              SUM(CASE WHEN final_return_pct > 0 THEN 1 ELSE 0 END) AS wins
                       FROM mf2_tracked_picks WHERE status = 'closed'
                       GROUP BY algorithm_name HAVING cnt >= 3
                       ORDER BY avg_ret DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $algo_stats[] = array(
                'algorithm' => $row['algorithm_name'],
                'trades' => (int)$row['cnt'],
                'avg_return' => round((float)$row['avg_ret'], 2),
                'win_rate' => round((int)$row['wins'] / (int)$row['cnt'] * 100, 1)
            );
        }
    }
    if (count($algo_stats) >= 2) {
        $best_algo = $algo_stats[0];
        $worst_algo = $algo_stats[count($algo_stats) - 1];

        $title = 'Best MF algorithm: ' . $best_algo['algorithm'];
        $text = $best_algo['algorithm'] . ' leads with ' . $best_algo['win_rate'] . '% win rate and '
              . $best_algo['avg_return'] . '% avg return across ' . $best_algo['trades'] . ' closed trades. ';
        if ($worst_algo['win_rate'] < 40) {
            $text .= 'Consider reducing weight for ' . $worst_algo['algorithm']
                   . ' (' . $worst_algo['win_rate'] . '% WR, ' . $worst_algo['avg_return'] . '% avg).';
        }
        $conf = min(85, 30 + count($algo_stats) * 5);
        _mf2_store_lesson($conn, $today, $now, 'pattern', $title, $text, $conf, json_encode($algo_stats));
        $lessons_added++;
    }

    // ── Pattern 2: Holding Period Patterns ──
    // Early exits vs full hold — which works better for MFs?
    $by_hold = array();
    $r = $conn->query("SELECT
                         CASE WHEN hold_days <= 14 THEN '1-14d'
                              WHEN hold_days <= 30 THEN '15-30d'
                              WHEN hold_days <= 60 THEN '31-60d'
                              ELSE '60d+' END AS bucket,
                         COUNT(*) AS cnt,
                         AVG(final_return_pct) AS avg_ret,
                         SUM(CASE WHEN final_return_pct > 0 THEN 1 ELSE 0 END) AS wins
                       FROM mf2_tracked_picks WHERE status = 'closed'
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
        $title = 'Best MF hold period: ' . $best_hold['bucket'];
        $text = 'Mutual fund positions held for ' . $best_hold['bucket'] . ' average '
              . $best_hold['avg_return'] . '% return with ' . $best_hold['win_rate']
              . '% win rate (' . $best_hold['trades'] . ' trades). ';
        if ($best_hold['bucket'] === '60d+') {
            $text .= 'Patience pays off with mutual funds — longer holds tend to work better.';
        } elseif ($best_hold['bucket'] === '1-14d') {
            $text .= 'Surprisingly, short-term MF trading is working. This may indicate strong momentum signals.';
        }
        $conf = min(80, 30 + $best_hold['trades'] * 3);
        _mf2_store_lesson($conn, $today, $now, 'insight', $title, $text, $conf, json_encode($by_hold));
        $lessons_added++;
    }

    // ── Pattern 3: NAV Trend Patterns ──
    // Do picks work better when NAV was rising or falling at entry?
    $nav_trend = array();
    $r = $conn->query("SELECT
                         CASE WHEN peak_nav > entry_nav THEN 'rising'
                              WHEN trough_nav < entry_nav THEN 'falling'
                              ELSE 'flat' END AS trend,
                         COUNT(*) AS cnt,
                         AVG(final_return_pct) AS avg_ret,
                         SUM(CASE WHEN final_return_pct > 0 THEN 1 ELSE 0 END) AS wins
                       FROM mf2_tracked_picks WHERE status = 'closed'
                         AND peak_nav IS NOT NULL AND trough_nav IS NOT NULL
                       GROUP BY trend HAVING cnt >= 3");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $nav_trend[] = array(
                'trend' => $row['trend'],
                'trades' => (int)$row['cnt'],
                'avg_return' => round((float)$row['avg_ret'], 2),
                'win_rate' => round((int)$row['wins'] / (int)$row['cnt'] * 100, 1)
            );
        }
    }
    if (count($nav_trend) >= 2) {
        $best_trend = $nav_trend[0];
        foreach ($nav_trend as $nt) {
            if ($nt['win_rate'] > $best_trend['win_rate']) $best_trend = $nt;
        }
        $title = 'NAV trend insight: ' . $best_trend['trend'] . ' NAV picks perform best';
        $text = 'Picks where NAV was ' . $best_trend['trend'] . ' show '
              . $best_trend['win_rate'] . '% win rate (avg ' . $best_trend['avg_return']
              . '%) across ' . $best_trend['trades'] . ' trades. ';
        if ($best_trend['trend'] === 'rising') {
            $text .= 'Momentum is key — buying into rising NAV trends works for mutual funds.';
        } elseif ($best_trend['trend'] === 'falling') {
            $text .= 'Contrarian entries into falling NAVs show mean-reversion potential.';
        }
        $conf = min(75, 25 + $best_trend['trades'] * 3);
        _mf2_store_lesson($conn, $today, $now, 'insight', $title, $text, $conf, json_encode($nav_trend));
        $lessons_added++;
    }

    // ── Pattern 4: Exit Reason Analysis ──
    $by_exit = array();
    $r = $conn->query("SELECT exit_reason, COUNT(*) AS cnt, AVG(final_return_pct) AS avg_ret,
                              SUM(CASE WHEN final_return_pct > 0 THEN 1 ELSE 0 END) AS wins
                       FROM mf2_tracked_picks WHERE status = 'closed' AND exit_reason IS NOT NULL AND exit_reason != ''
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
            $text .= 'Stop-loss exits are protective — consider if SL threshold (-3%) is too tight for mutual funds.';
        } elseif ($worst_exit['reason'] === 'max_hold') {
            $text .= 'Max-hold exits (90 days) suggest the thesis went stale. Consider adjusting hold period.';
        }
        $conf = min(80, 30 + count($by_exit) * 10);
        _mf2_store_lesson($conn, $today, $now, 'warning', $title, $text, $conf, json_encode($by_exit));
        $lessons_added++;
    }

    // ── Pattern 5: Score Bracket Effect ──
    $by_score = array();
    $r = $conn->query("SELECT
                         CASE WHEN score < 30 THEN 'low (<30)'
                              WHEN score < 60 THEN 'medium (30-60)'
                              WHEN score < 80 THEN 'high (60-80)'
                              ELSE 'very high (80+)' END AS bracket,
                         COUNT(*) AS cnt,
                         AVG(final_return_pct) AS avg_ret,
                         SUM(CASE WHEN final_return_pct > 0 THEN 1 ELSE 0 END) AS wins
                       FROM mf2_tracked_picks WHERE status = 'closed' AND score IS NOT NULL
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
        $title = 'Optimal pick score: ' . $best_score['bracket'];
        $text = 'Picks with score ' . $best_score['bracket'] . ' show '
              . $best_score['win_rate'] . '% win rate (avg ' . $best_score['avg_return']
              . '% return) across ' . $best_score['trades'] . ' trades.';
        $conf = min(80, 30 + $best_score['trades'] * 3);
        _mf2_store_lesson($conn, $today, $now, 'pattern', $title, $text, $conf, json_encode($by_score));
        $lessons_added++;
    }

    // ── Pattern 6: Overall System Performance Summary ──
    $r = $conn->query("SELECT COUNT(*) AS c, AVG(final_return_pct) AS avg_r,
                              SUM(CASE WHEN final_return_pct > 0 THEN 1 ELSE 0 END) AS w
                       FROM mf2_tracked_picks WHERE status = 'closed'");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $tc = (int)$row['c'];
        $tr = round((float)$row['avg_r'], 2);
        $tw = ($tc > 0) ? round((int)$row['w'] / $tc * 100, 1) : 0;

        if ($tc >= $min_samples) {
            $title = 'MF tracking: ' . $tw . '% win rate across ' . $tc . ' trades';
            $text = 'Mutual fund performance tracking shows ' . $tw . '% win rate with '
                  . $tr . '% average return per trade across ' . $tc . ' closed positions. ';
            if ($tw >= 60) {
                $text .= 'The MF algorithm system is performing well. Fund selection criteria are solid.';
            } elseif ($tw >= 45) {
                $text .= 'Performance is moderate. Consider tightening entry criteria or adjusting TP/SL thresholds.';
            } else {
                $text .= 'Performance below expectations. Review algorithm weights and consider filtering low-confidence picks.';
            }
            $conf = min(95, 50 + $tc);
            _mf2_store_lesson($conn, $today, $now, 'insight', $title, $text, $conf, null);
            $lessons_added++;
        }
    }

    return $lessons_added;
}


// ═══════════════════════════════════════════════════════════════
// HELPER: Store or update a lesson (upserts by date + type)
// ═══════════════════════════════════════════════════════════════
function _mf2_store_lesson($conn, $today, $now, $type, $title, $text, $confidence, $data_json) {
    $safe_type  = $conn->real_escape_string($type);
    $safe_title = $conn->real_escape_string($title);
    $safe_text  = $conn->real_escape_string($text);
    $safe_data  = ($data_json !== null) ? $conn->real_escape_string($data_json) : '';
    $conf       = round((float)$confidence, 2);

    // Check if lesson of this type already exists for today
    $r = $conn->query("SELECT id FROM mf2_tracking_lessons WHERE lesson_date = '$today' AND lesson_type = '$safe_type' LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $conn->query("UPDATE mf2_tracking_lessons SET
            lesson_title = '$safe_title',
            lesson_text = '$safe_text',
            confidence = $conf,
            supporting_data = '$safe_data'
            WHERE id = " . (int)$row['id']);
    } else {
        $conn->query("INSERT INTO mf2_tracking_lessons
            (lesson_date, lesson_type, lesson_title, lesson_text, confidence, supporting_data, created_at)
            VALUES ('$today', '$safe_type', '$safe_title', '$safe_text', $conf, '$safe_data', '$now')");
    }
}
?>
