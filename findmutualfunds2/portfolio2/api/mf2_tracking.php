<?php
/**
 * Mutual Funds Forward Performance Tracking API
 * Tracks pick outcomes, daily NAV refresh, exit rules, P&L.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=init_tracking   - Seed tracked picks from mf2_fund_picks
 *   ?action=refresh          - Refresh current NAVs & check exit rules
 *   ?action=dashboard        - Get tracking dashboard data
 *   ?action=close_position   - Manually close a position
 */
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/mf2_performance_tracking_schema.php';

// Ensure tables exist
mf2_ensure_tracking_schema($conn);

$action = isset($_GET['action']) ? trim($_GET['action']) : 'dashboard';
$response = array('ok' => true, 'action' => $action);

// ─── Exit rule defaults ───
$TP_SWING  = 8.0;   // Take profit % for swing picks
$TP_SHORT  = 5.0;   // Take profit % for short-term picks
$SL_SWING  = 4.0;   // Stop loss %
$SL_SHORT  = 3.0;
$MAX_HOLD  = 90;    // Max hold days for MF picks

// ─── ACTION: init_tracking ───
if ($action === 'init_tracking') {
    $imported = 0;
    $skipped = 0;
    $now = date('Y-m-d H:i:s');

    $sql = "SELECT fp.*, f.fund_name FROM mf2_fund_picks fp
            LEFT JOIN mf2_funds f ON fp.symbol = f.symbol
            WHERE fp.entry_nav > 0
            ORDER BY fp.pick_date ASC";
    $res = $conn->query($sql);
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $sym  = $conn->real_escape_string($row['symbol']);
            $algo = $conn->real_escape_string($row['algorithm_name']);
            $pd   = $conn->real_escape_string($row['pick_date']);
            $enav = (float)$row['entry_nav'];
            $score = (float)$row['score'];
            $rating = $conn->real_escape_string(isset($row['rating']) ? $row['rating'] : '');

            // Check duplicate
            $chk = $conn->query("SELECT id FROM mf2_tracked_picks WHERE symbol='$sym' AND algorithm_name='$algo' AND pick_date='$pd'");
            if ($chk && $chk->num_rows > 0) {
                $skipped++;
                continue;
            }

            $sql2 = "INSERT INTO mf2_tracked_picks
                     (symbol, algorithm_name, pick_date, entry_nav, current_nav, current_return_pct,
                      status, peak_nav, trough_nav, hold_days, score, rating, created_at)
                     VALUES ('$sym', '$algo', '$pd', $enav, $enav, 0,
                             'open', $enav, $enav, 0, $score, '$rating', '$now')";
            if ($conn->query($sql2)) {
                $imported++;
            }
        }
    }

    $response['imported'] = $imported;
    $response['skipped'] = $skipped;
    $response['message'] = 'Initialized ' . $imported . ' tracked positions (' . $skipped . ' already existed)';

// ─── ACTION: refresh ───
} elseif ($action === 'refresh') {
    $updated = 0;
    $closed = 0;
    $errors = array();
    $now = date('Y-m-d H:i:s');
    $today = date('Y-m-d');

    // Get all open positions
    $res = $conn->query("SELECT * FROM mf2_tracked_picks WHERE status='open' ORDER BY symbol");
    if (!$res || $res->num_rows === 0) {
        $response['message'] = 'No open positions to refresh';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $positions = array();
    while ($row = $res->fetch_assoc()) $positions[] = $row;

    foreach ($positions as $pos) {
        $sym = $conn->real_escape_string($pos['symbol']);
        $id = (int)$pos['id'];
        $entry_nav = (float)$pos['entry_nav'];
        $pick_date = $pos['pick_date'];

        // Get latest NAV from history
        $nav_res = $conn->query("SELECT nav, nav_date FROM mf2_nav_history WHERE symbol='$sym' ORDER BY nav_date DESC LIMIT 1");
        if (!$nav_res || $nav_res->num_rows === 0) continue;

        $nav_row = $nav_res->fetch_assoc();
        $current_nav = (float)$nav_row['nav'];
        $nav_date = $nav_row['nav_date'];

        // Calculate return
        $return_pct = ($entry_nav > 0) ? round(($current_nav - $entry_nav) / $entry_nav * 100, 4) : 0;

        // Calculate hold days
        $d1 = strtotime($pick_date);
        $d2 = strtotime($today);
        $hold_days = ($d2 > $d1) ? (int)(($d2 - $d1) / 86400) : 0;

        // Peak/trough
        $peak = (float)$pos['peak_nav'];
        $trough = (float)$pos['trough_nav'];
        if ($current_nav > $peak) $peak = $current_nav;
        if ($trough <= 0 || $current_nav < $trough) $trough = $current_nav;

        // Determine TP/SL based on timeframe
        $tf = isset($pos['rating']) ? $pos['rating'] : '';
        $tp = $TP_SWING;
        $sl = $SL_SWING;
        if (strpos(strtolower($tf), 'short') !== false || strpos(strtolower($tf), '1m') !== false || strpos(strtolower($tf), '3m') !== false) {
            $tp = $TP_SHORT;
            $sl = $SL_SHORT;
        }

        // Check exit conditions
        $exit_reason = '';
        if ($return_pct >= $tp) {
            $exit_reason = 'take_profit';
        } elseif ($return_pct <= -$sl) {
            $exit_reason = 'stop_loss';
        } elseif ($hold_days >= $MAX_HOLD) {
            $exit_reason = 'max_hold';
        }

        if ($exit_reason !== '') {
            // Close position
            $safe_reason = $conn->real_escape_string($exit_reason);
            $conn->query("UPDATE mf2_tracked_picks SET
                          current_nav=$current_nav, current_return_pct=$return_pct,
                          status='closed', exit_date='$today', exit_nav=$current_nav,
                          exit_reason='$safe_reason', final_return_pct=$return_pct,
                          peak_nav=$peak, trough_nav=$trough, hold_days=$hold_days
                          WHERE id=$id");
            $closed++;
        } else {
            // Update open position
            $conn->query("UPDATE mf2_tracked_picks SET
                          current_nav=$current_nav, current_return_pct=$return_pct,
                          peak_nav=$peak, trough_nav=$trough, hold_days=$hold_days
                          WHERE id=$id");
        }
        $updated++;
    }

    // Record daily snapshot
    $open_cnt = 0;
    $closed_cnt = 0;
    $wins = 0;
    $losses = 0;
    $avg_ret = 0;

    $sr = $conn->query("SELECT COUNT(*) as c FROM mf2_tracked_picks WHERE status='open'");
    if ($sr) { $r = $sr->fetch_assoc(); $open_cnt = (int)$r['c']; }

    $sr = $conn->query("SELECT COUNT(*) as c, SUM(CASE WHEN final_return_pct > 0 THEN 1 ELSE 0 END) as w,
                        SUM(CASE WHEN final_return_pct <= 0 THEN 1 ELSE 0 END) as l,
                        AVG(final_return_pct) as avg_ret FROM mf2_tracked_picks WHERE status='closed'");
    if ($sr) {
        $r = $sr->fetch_assoc();
        $closed_cnt = (int)$r['c'];
        $wins = (int)$r['w'];
        $losses = (int)$r['l'];
        $avg_ret = round((float)$r['avg_ret'], 4);
    }

    $wr = ($closed_cnt > 0) ? round($wins / $closed_cnt * 100, 2) : 0;

    $conn->query("INSERT INTO mf2_tracking_daily (track_date, open_positions, total_closed, total_wins, total_losses,
                  win_rate, avg_return_pct, created_at)
                  VALUES ('$today', $open_cnt, $closed_cnt, $wins, $losses, $wr, $avg_ret, '$now')
                  ON DUPLICATE KEY UPDATE open_positions=$open_cnt, total_closed=$closed_cnt,
                  total_wins=$wins, total_losses=$losses, win_rate=$wr, avg_return_pct=$avg_ret");

    $response['updated'] = $updated;
    $response['closed'] = $closed;
    $response['open_positions'] = $open_cnt;
    $response['total_closed'] = $closed_cnt;

// ─── ACTION: dashboard ───
} elseif ($action === 'dashboard') {
    // Summary stats
    $stats = array();

    $sr = $conn->query("SELECT COUNT(*) as c FROM mf2_tracked_picks WHERE status='open'");
    if ($sr) { $r = $sr->fetch_assoc(); $stats['open_positions'] = (int)$r['c']; }

    $sr = $conn->query("SELECT COUNT(*) as c, SUM(CASE WHEN final_return_pct > 0 THEN 1 ELSE 0 END) as w,
                        AVG(final_return_pct) as avg_ret, AVG(hold_days) as avg_hold
                        FROM mf2_tracked_picks WHERE status='closed'");
    if ($sr) {
        $r = $sr->fetch_assoc();
        $stats['total_closed'] = (int)$r['c'];
        $stats['total_wins'] = (int)$r['w'];
        $stats['total_losses'] = $stats['total_closed'] - $stats['total_wins'];
        $stats['win_rate'] = ($stats['total_closed'] > 0) ? round($stats['total_wins'] / $stats['total_closed'] * 100, 2) : 0;
        $stats['avg_return_pct'] = round((float)$r['avg_ret'], 4);
        $stats['avg_hold_days'] = round((float)$r['avg_hold'], 1);
    }

    // Open positions with current P&L
    $open = array();
    $sr = $conn->query("SELECT tp.*, f.fund_name, f.fund_family, f.category
                        FROM mf2_tracked_picks tp
                        LEFT JOIN mf2_funds f ON tp.symbol = f.symbol
                        WHERE tp.status='open'
                        ORDER BY tp.current_return_pct DESC");
    if ($sr) {
        while ($row = $sr->fetch_assoc()) $open[] = $row;
    }

    // Closed positions
    $closed = array();
    $sr = $conn->query("SELECT tp.*, f.fund_name, f.fund_family, f.category
                        FROM mf2_tracked_picks tp
                        LEFT JOIN mf2_funds f ON tp.symbol = f.symbol
                        WHERE tp.status='closed'
                        ORDER BY tp.exit_date DESC
                        LIMIT 50");
    if ($sr) {
        while ($row = $sr->fetch_assoc()) $closed[] = $row;
    }

    // Daily history
    $daily = array();
    $sr = $conn->query("SELECT * FROM mf2_tracking_daily ORDER BY track_date DESC LIMIT 30");
    if ($sr) {
        while ($row = $sr->fetch_assoc()) $daily[] = $row;
    }

    // Per-algo breakdown
    $algo_perf = array();
    $sr = $conn->query("SELECT algorithm_name,
                        COUNT(*) as total,
                        SUM(CASE WHEN status='closed' AND final_return_pct > 0 THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN status='closed' AND final_return_pct <= 0 THEN 1 ELSE 0 END) as losses,
                        SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_cnt,
                        AVG(CASE WHEN status='closed' THEN final_return_pct ELSE NULL END) as avg_closed_ret,
                        AVG(current_return_pct) as avg_current_ret
                        FROM mf2_tracked_picks
                        GROUP BY algorithm_name
                        ORDER BY avg_current_ret DESC");
    if ($sr) {
        while ($row = $sr->fetch_assoc()) $algo_perf[] = $row;
    }

    $response['stats'] = $stats;
    $response['open_positions'] = $open;
    $response['closed_positions'] = $closed;
    $response['daily_history'] = $daily;
    $response['algorithm_performance'] = $algo_perf;

// ─── ACTION: close_position ───
} elseif ($action === 'close_position') {
    $id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    $reason = isset($_GET['reason']) ? $conn->real_escape_string(trim($_GET['reason'])) : 'manual_close';
    $today = date('Y-m-d');
    $now = date('Y-m-d H:i:s');

    if ($id <= 0) {
        $response['ok'] = false;
        $response['error'] = 'id parameter required';
    } else {
        $res = $conn->query("SELECT * FROM mf2_tracked_picks WHERE id=$id AND status='open'");
        if (!$res || $res->num_rows === 0) {
            $response['ok'] = false;
            $response['error'] = 'Position not found or already closed';
        } else {
            $pos = $res->fetch_assoc();
            $current_nav = (float)$pos['current_nav'];
            $return_pct = (float)$pos['current_return_pct'];

            $conn->query("UPDATE mf2_tracked_picks SET
                          status='closed', exit_date='$today', exit_nav=$current_nav,
                          exit_reason='$reason', final_return_pct=$return_pct
                          WHERE id=$id");
            $response['message'] = 'Position closed: ' . $pos['symbol'] . ' at ' . $return_pct . '%';
        }
    }

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action. Use: init_tracking, refresh, dashboard, close_position';
}

echo json_encode($response);
$conn->close();
?>
