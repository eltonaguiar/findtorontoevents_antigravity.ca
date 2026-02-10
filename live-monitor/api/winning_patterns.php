<?php
/**
 * Winning Trade Patterns Analysis — Live Trading Monitor
 * Analyzes closed trades to find patterns: time-of-day, algorithm, asset class,
 * market session, and conditions that produce winning trades.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=overview          — Overall winning pattern summary (public)
 *   ?action=time_analysis     — Win rate by hour-of-day and day-of-week (public)
 *   ?action=algorithm_matrix  — Algorithm performance matrix by asset class (public)
 *   ?action=best_setups       — Top winning trade setups (public)
 *   ?action=session_analysis  — Win rate by market session (public)
 *   ?action=streak_analysis   — Win/loss streak patterns (public)
 *   ?action=full_report       — All analyses combined (public)
 */
require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'overview';
$asset_filter = isset($_GET['asset']) ? strtoupper(trim($_GET['asset'])) : '';
$days = isset($_GET['days']) ? max(1, min(365, (int)$_GET['days'])) : 30;

// ─── Route action ─────────────────────────────────────────────────
if ($action === 'overview') {
    _wp_overview($conn, $asset_filter, $days);
} elseif ($action === 'time_analysis') {
    _wp_time_analysis($conn, $asset_filter, $days);
} elseif ($action === 'algorithm_matrix') {
    _wp_algorithm_matrix($conn, $asset_filter, $days);
} elseif ($action === 'best_setups') {
    _wp_best_setups($conn, $asset_filter, $days);
} elseif ($action === 'session_analysis') {
    _wp_session_analysis($conn, $asset_filter, $days);
} elseif ($action === 'streak_analysis') {
    _wp_streak_analysis($conn, $asset_filter, $days);
} elseif ($action === 'full_report') {
    _wp_full_report($conn, $asset_filter, $days);
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;

// ═══════════════════════════════════════════════════════════════════
// OVERVIEW — key stats, best algorithm, best time, best asset
// ═══════════════════════════════════════════════════════════════════
function _wp_overview($conn, $asset_filter, $days) {
    $since = date('Y-m-d H:i:s', time() - ($days * 86400));
    $where = "status = 'closed' AND exit_time >= '" . $conn->real_escape_string($since) . "'";
    if ($asset_filter) $where .= " AND asset_class = '" . $conn->real_escape_string($asset_filter) . "'";

    // Overall stats
    $r = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN realized_pnl_usd <= 0 THEN 1 ELSE 0 END) as losses,
        ROUND(AVG(CASE WHEN realized_pnl_usd > 0 THEN realized_pct ELSE NULL END), 2) as avg_win_pct,
        ROUND(AVG(CASE WHEN realized_pnl_usd <= 0 THEN realized_pct ELSE NULL END), 2) as avg_loss_pct,
        ROUND(SUM(realized_pnl_usd), 2) as total_pnl,
        ROUND(AVG(hold_hours), 1) as avg_hold_hours,
        ROUND(AVG(realized_pnl_usd), 2) as avg_pnl_per_trade
    FROM lm_trades WHERE $where");
    $stats = $r ? $r->fetch_assoc() : array();
    $total = isset($stats['total']) ? (int)$stats['total'] : 0;
    $wins = isset($stats['wins']) ? (int)$stats['wins'] : 0;
    $win_rate = $total > 0 ? round($wins / $total * 100, 1) : 0;

    // Best algorithm
    $best_algo = array('name' => 'N/A', 'win_rate' => 0, 'trades' => 0);
    $r2 = $conn->query("SELECT algorithm_name,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as wr
    FROM lm_trades WHERE $where AND algorithm_name != ''
    GROUP BY algorithm_name HAVING trades >= 3 ORDER BY wr DESC, trades DESC LIMIT 1");
    if ($r2 && $row = $r2->fetch_assoc()) {
        $best_algo = array('name' => $row['algorithm_name'], 'win_rate' => floatval($row['wr']), 'trades' => (int)$row['trades']);
    }

    // Best hour (UTC)
    $best_hour = array('hour' => 'N/A', 'win_rate' => 0, 'trades' => 0);
    $r3 = $conn->query("SELECT HOUR(entry_time) as hr,
        COUNT(*) as trades,
        ROUND(SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as wr
    FROM lm_trades WHERE $where
    GROUP BY hr HAVING trades >= 3 ORDER BY wr DESC, trades DESC LIMIT 1");
    if ($r3 && $row = $r3->fetch_assoc()) {
        $h = (int)$row['hr'];
        $est = ($h - 5 + 24) % 24;
        $best_hour = array('hour_utc' => $h, 'hour_est' => $est, 'label' => sprintf('%d:00-%d:00 EST', $est, ($est + 1) % 24), 'win_rate' => floatval($row['wr']), 'trades' => (int)$row['trades']);
    }

    // Best asset class
    $best_asset = array('class' => 'N/A', 'win_rate' => 0, 'trades' => 0);
    $r4 = $conn->query("SELECT asset_class,
        COUNT(*) as trades,
        ROUND(SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as wr,
        ROUND(SUM(realized_pnl_usd), 2) as pnl
    FROM lm_trades WHERE $where
    GROUP BY asset_class ORDER BY wr DESC LIMIT 1");
    if ($r4 && $row = $r4->fetch_assoc()) {
        $best_asset = array('class' => $row['asset_class'], 'win_rate' => floatval($row['wr']), 'trades' => (int)$row['trades'], 'pnl' => floatval($row['pnl']));
    }

    // Profit factor
    $r5 = $conn->query("SELECT
        ROUND(SUM(CASE WHEN realized_pnl_usd > 0 THEN realized_pnl_usd ELSE 0 END), 2) as gross_profit,
        ROUND(ABS(SUM(CASE WHEN realized_pnl_usd < 0 THEN realized_pnl_usd ELSE 0 END)), 2) as gross_loss
    FROM lm_trades WHERE $where");
    $pf_row = $r5 ? $r5->fetch_assoc() : array();
    $gross_profit = isset($pf_row['gross_profit']) ? floatval($pf_row['gross_profit']) : 0;
    $gross_loss = isset($pf_row['gross_loss']) ? floatval($pf_row['gross_loss']) : 0.01;
    $profit_factor = $gross_loss > 0 ? round($gross_profit / $gross_loss, 2) : 0;

    echo json_encode(array(
        'ok' => true,
        'action' => 'overview',
        'days' => $days,
        'asset_filter' => $asset_filter ? $asset_filter : 'all',
        'total_trades' => $total,
        'wins' => $wins,
        'losses' => $total - $wins,
        'win_rate' => $win_rate,
        'avg_win_pct' => isset($stats['avg_win_pct']) ? floatval($stats['avg_win_pct']) : 0,
        'avg_loss_pct' => isset($stats['avg_loss_pct']) ? floatval($stats['avg_loss_pct']) : 0,
        'total_pnl' => isset($stats['total_pnl']) ? floatval($stats['total_pnl']) : 0,
        'avg_pnl_per_trade' => isset($stats['avg_pnl_per_trade']) ? floatval($stats['avg_pnl_per_trade']) : 0,
        'avg_hold_hours' => isset($stats['avg_hold_hours']) ? floatval($stats['avg_hold_hours']) : 0,
        'profit_factor' => $profit_factor,
        'best_algorithm' => $best_algo,
        'best_hour' => $best_hour,
        'best_asset_class' => $best_asset
    ));
}

// ═══════════════════════════════════════════════════════════════════
// TIME ANALYSIS — win rate by hour and day of week
// ═══════════════════════════════════════════════════════════════════
function _wp_time_analysis($conn, $asset_filter, $days) {
    $since = date('Y-m-d H:i:s', time() - ($days * 86400));
    $where = "status = 'closed' AND exit_time >= '" . $conn->real_escape_string($since) . "'";
    if ($asset_filter) $where .= " AND asset_class = '" . $conn->real_escape_string($asset_filter) . "'";

    // By hour (UTC, convert to EST display)
    $hourly = array();
    $r = $conn->query("SELECT HOUR(entry_time) as hr,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(realized_pnl_usd), 2) as pnl,
        ROUND(AVG(realized_pct), 2) as avg_return
    FROM lm_trades WHERE $where GROUP BY hr ORDER BY hr");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $h = (int)$row['hr'];
            $est = ($h - 5 + 24) % 24;
            $trades = (int)$row['trades'];
            $wins = (int)$row['wins'];
            $hourly[] = array(
                'hour_utc' => $h,
                'hour_est' => $est,
                'label' => sprintf('%02d:00 EST', $est),
                'trades' => $trades,
                'wins' => $wins,
                'win_rate' => $trades > 0 ? round($wins / $trades * 100, 1) : 0,
                'pnl' => floatval($row['pnl']),
                'avg_return' => floatval($row['avg_return'])
            );
        }
    }

    // By day of week
    $daily = array();
    $day_names = array('Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat');
    $r2 = $conn->query("SELECT DAYOFWEEK(entry_time) as dow,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(realized_pnl_usd), 2) as pnl
    FROM lm_trades WHERE $where GROUP BY dow ORDER BY dow");
    if ($r2) {
        while ($row = $r2->fetch_assoc()) {
            $d = (int)$row['dow'];
            $trades = (int)$row['trades'];
            $wins = (int)$row['wins'];
            $daily[] = array(
                'day' => isset($day_names[$d - 1]) ? $day_names[$d - 1] : '?',
                'day_num' => $d,
                'trades' => $trades,
                'wins' => $wins,
                'win_rate' => $trades > 0 ? round($wins / $trades * 100, 1) : 0,
                'pnl' => floatval($row['pnl'])
            );
        }
    }

    // Best time slot (combined hour + asset)
    $best_slots = array();
    $r3 = $conn->query("SELECT asset_class, HOUR(entry_time) as hr,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(realized_pnl_usd), 2) as pnl
    FROM lm_trades WHERE $where
    GROUP BY asset_class, hr HAVING trades >= 2
    ORDER BY (wins / trades) DESC, pnl DESC LIMIT 10");
    if ($r3) {
        while ($row = $r3->fetch_assoc()) {
            $h = (int)$row['hr'];
            $est = ($h - 5 + 24) % 24;
            $trades = (int)$row['trades'];
            $wins = (int)$row['wins'];
            $best_slots[] = array(
                'asset_class' => $row['asset_class'],
                'hour_est' => $est,
                'label' => $row['asset_class'] . ' @ ' . sprintf('%02d:00 EST', $est),
                'trades' => $trades,
                'wins' => $wins,
                'win_rate' => round($wins / $trades * 100, 1),
                'pnl' => floatval($row['pnl'])
            );
        }
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'time_analysis',
        'days' => $days,
        'hourly' => $hourly,
        'daily' => $daily,
        'best_time_slots' => $best_slots
    ));
}

// ═══════════════════════════════════════════════════════════════════
// ALGORITHM MATRIX — performance breakdown by algo x asset class
// ═══════════════════════════════════════════════════════════════════
function _wp_algorithm_matrix($conn, $asset_filter, $days) {
    $since = date('Y-m-d H:i:s', time() - ($days * 86400));
    $where = "status = 'closed' AND exit_time >= '" . $conn->real_escape_string($since) . "' AND algorithm_name != ''";
    if ($asset_filter) $where .= " AND asset_class = '" . $conn->real_escape_string($asset_filter) . "'";

    $matrix = array();
    $r = $conn->query("SELECT algorithm_name, asset_class,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(realized_pnl_usd), 2) as pnl,
        ROUND(AVG(realized_pct), 2) as avg_return,
        ROUND(AVG(hold_hours), 1) as avg_hold,
        ROUND(MAX(realized_pct), 2) as best_trade,
        ROUND(MIN(realized_pct), 2) as worst_trade
    FROM lm_trades WHERE $where
    GROUP BY algorithm_name, asset_class
    ORDER BY algorithm_name, asset_class");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $trades = (int)$row['trades'];
            $wins = (int)$row['wins'];
            $matrix[] = array(
                'algorithm' => $row['algorithm_name'],
                'asset_class' => $row['asset_class'],
                'trades' => $trades,
                'wins' => $wins,
                'win_rate' => $trades > 0 ? round($wins / $trades * 100, 1) : 0,
                'pnl' => floatval($row['pnl']),
                'avg_return' => floatval($row['avg_return']),
                'avg_hold_hours' => floatval($row['avg_hold']),
                'best_trade' => floatval($row['best_trade']),
                'worst_trade' => floatval($row['worst_trade'])
            );
        }
    }

    // Algorithm rankings (all asset classes combined)
    $rankings = array();
    $r2 = $conn->query("SELECT algorithm_name,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(realized_pnl_usd), 2) as pnl,
        ROUND(AVG(realized_pct), 2) as avg_return,
        ROUND(SUM(CASE WHEN realized_pnl_usd > 0 THEN realized_pnl_usd ELSE 0 END), 2) as gross_win,
        ROUND(ABS(SUM(CASE WHEN realized_pnl_usd < 0 THEN realized_pnl_usd ELSE 0 END)), 2) as gross_loss
    FROM lm_trades WHERE $where
    GROUP BY algorithm_name HAVING trades >= 2
    ORDER BY pnl DESC");
    if ($r2) {
        while ($row = $r2->fetch_assoc()) {
            $trades = (int)$row['trades'];
            $wins = (int)$row['wins'];
            $gl = floatval($row['gross_loss']);
            $rankings[] = array(
                'algorithm' => $row['algorithm_name'],
                'trades' => $trades,
                'wins' => $wins,
                'win_rate' => $trades > 0 ? round($wins / $trades * 100, 1) : 0,
                'pnl' => floatval($row['pnl']),
                'avg_return' => floatval($row['avg_return']),
                'profit_factor' => $gl > 0 ? round(floatval($row['gross_win']) / $gl, 2) : 0
            );
        }
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'algorithm_matrix',
        'days' => $days,
        'matrix' => $matrix,
        'rankings' => $rankings
    ));
}

// ═══════════════════════════════════════════════════════════════════
// BEST SETUPS — top winning algo+asset+hour combinations
// ═══════════════════════════════════════════════════════════════════
function _wp_best_setups($conn, $asset_filter, $days) {
    $since = date('Y-m-d H:i:s', time() - ($days * 86400));
    $where = "status = 'closed' AND exit_time >= '" . $conn->real_escape_string($since) . "' AND algorithm_name != ''";
    if ($asset_filter) $where .= " AND asset_class = '" . $conn->real_escape_string($asset_filter) . "'";

    // Best algo + asset + hour combos
    $setups = array();
    $r = $conn->query("SELECT algorithm_name, asset_class, HOUR(entry_time) as hr,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(realized_pnl_usd), 2) as pnl,
        ROUND(AVG(realized_pct), 2) as avg_return,
        ROUND(AVG(hold_hours), 1) as avg_hold
    FROM lm_trades WHERE $where
    GROUP BY algorithm_name, asset_class, hr
    HAVING trades >= 2
    ORDER BY (wins / trades) DESC, pnl DESC LIMIT 20");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $h = (int)$row['hr'];
            $est = ($h - 5 + 24) % 24;
            $trades = (int)$row['trades'];
            $wins = (int)$row['wins'];

            // Determine market session
            $session = 'Off-Hours';
            if ($est >= 0 && $est < 7) $session = 'Asia (Pre-Market)';
            elseif ($est >= 7 && $est < 9) $session = 'Europe/Pre-Market';
            elseif ($est >= 9 && $est < 12) $session = 'US Morning';
            elseif ($est >= 12 && $est < 16) $session = 'US Afternoon';
            elseif ($est >= 16 && $est < 20) $session = 'US After-Hours';
            elseif ($est >= 20) $session = 'Asia Session';

            $setups[] = array(
                'algorithm' => $row['algorithm_name'],
                'asset_class' => $row['asset_class'],
                'hour_est' => $est,
                'session' => $session,
                'trades' => $trades,
                'wins' => $wins,
                'win_rate' => round($wins / $trades * 100, 1),
                'pnl' => floatval($row['pnl']),
                'avg_return' => floatval($row['avg_return']),
                'avg_hold_hours' => floatval($row['avg_hold']),
                'description' => $row['algorithm_name'] . ' on ' . $row['asset_class'] . ' at ' . sprintf('%02d:00 EST', $est) . ' (' . $session . ')'
            );
        }
    }

    // Best symbols
    $symbols = array();
    $r2 = $conn->query("SELECT symbol, asset_class,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(realized_pnl_usd), 2) as pnl,
        ROUND(AVG(realized_pct), 2) as avg_return
    FROM lm_trades WHERE $where
    GROUP BY symbol, asset_class HAVING trades >= 2
    ORDER BY pnl DESC LIMIT 15");
    if ($r2) {
        while ($row = $r2->fetch_assoc()) {
            $trades = (int)$row['trades'];
            $wins = (int)$row['wins'];
            $symbols[] = array(
                'symbol' => $row['symbol'],
                'asset_class' => $row['asset_class'],
                'trades' => $trades,
                'wins' => $wins,
                'win_rate' => round($wins / $trades * 100, 1),
                'pnl' => floatval($row['pnl']),
                'avg_return' => floatval($row['avg_return'])
            );
        }
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'best_setups',
        'days' => $days,
        'top_setups' => $setups,
        'top_symbols' => $symbols
    ));
}

// ═══════════════════════════════════════════════════════════════════
// SESSION ANALYSIS — win rate by market session
// ═══════════════════════════════════════════════════════════════════
function _wp_session_analysis($conn, $asset_filter, $days) {
    $since = date('Y-m-d H:i:s', time() - ($days * 86400));
    $where = "status = 'closed' AND exit_time >= '" . $conn->real_escape_string($since) . "'";
    if ($asset_filter) $where .= " AND asset_class = '" . $conn->real_escape_string($asset_filter) . "'";

    // Classify trades by market session (EST times)
    $sessions = array(
        'asia_pre' => array('name' => 'Asia / Pre-Market', 'hours' => '0-7 EST', 'trades' => 0, 'wins' => 0, 'pnl' => 0),
        'europe' => array('name' => 'Europe / Pre-Market', 'hours' => '7-9 EST', 'trades' => 0, 'wins' => 0, 'pnl' => 0),
        'us_morning' => array('name' => 'US Morning', 'hours' => '9:30-12 EST', 'trades' => 0, 'wins' => 0, 'pnl' => 0),
        'us_afternoon' => array('name' => 'US Afternoon', 'hours' => '12-16 EST', 'trades' => 0, 'wins' => 0, 'pnl' => 0),
        'us_after_hours' => array('name' => 'US After-Hours', 'hours' => '16-20 EST', 'trades' => 0, 'wins' => 0, 'pnl' => 0),
        'asia_evening' => array('name' => 'Asia Evening', 'hours' => '20-24 EST', 'trades' => 0, 'wins' => 0, 'pnl' => 0)
    );

    $r = $conn->query("SELECT HOUR(entry_time) as hr,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(realized_pnl_usd), 2) as pnl
    FROM lm_trades WHERE $where GROUP BY hr");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $h_utc = (int)$row['hr'];
            $h_est = ($h_utc - 5 + 24) % 24;
            $key = 'asia_pre';
            if ($h_est >= 0 && $h_est < 7) $key = 'asia_pre';
            elseif ($h_est >= 7 && $h_est < 9) $key = 'europe';
            elseif ($h_est >= 9 && $h_est < 12) $key = 'us_morning';
            elseif ($h_est >= 12 && $h_est < 16) $key = 'us_afternoon';
            elseif ($h_est >= 16 && $h_est < 20) $key = 'us_after_hours';
            else $key = 'asia_evening';

            $sessions[$key]['trades'] += (int)$row['trades'];
            $sessions[$key]['wins'] += (int)$row['wins'];
            $sessions[$key]['pnl'] += floatval($row['pnl']);
        }
    }

    $result = array();
    foreach ($sessions as $key => $s) {
        $s['key'] = $key;
        $s['win_rate'] = $s['trades'] > 0 ? round($s['wins'] / $s['trades'] * 100, 1) : 0;
        $s['pnl'] = round($s['pnl'], 2);
        $result[] = $s;
    }

    // By asset class per session
    $by_asset = array();
    $r2 = $conn->query("SELECT asset_class, HOUR(entry_time) as hr,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(realized_pnl_usd), 2) as pnl
    FROM lm_trades WHERE $where GROUP BY asset_class, hr");
    if ($r2) {
        $grouped = array();
        while ($row = $r2->fetch_assoc()) {
            $ac = $row['asset_class'];
            $h_utc = (int)$row['hr'];
            $h_est = ($h_utc - 5 + 24) % 24;
            $key = 'asia_pre';
            if ($h_est >= 7 && $h_est < 9) $key = 'europe';
            elseif ($h_est >= 9 && $h_est < 12) $key = 'us_morning';
            elseif ($h_est >= 12 && $h_est < 16) $key = 'us_afternoon';
            elseif ($h_est >= 16 && $h_est < 20) $key = 'us_after_hours';
            elseif ($h_est >= 20) $key = 'asia_evening';

            $gk = $ac . '|' . $key;
            if (!isset($grouped[$gk])) $grouped[$gk] = array('asset' => $ac, 'session' => $key, 'trades' => 0, 'wins' => 0, 'pnl' => 0);
            $grouped[$gk]['trades'] += (int)$row['trades'];
            $grouped[$gk]['wins'] += (int)$row['wins'];
            $grouped[$gk]['pnl'] += floatval($row['pnl']);
        }
        foreach ($grouped as $g) {
            $g['win_rate'] = $g['trades'] > 0 ? round($g['wins'] / $g['trades'] * 100, 1) : 0;
            $g['pnl'] = round($g['pnl'], 2);
            $by_asset[] = $g;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'session_analysis',
        'days' => $days,
        'sessions' => $result,
        'by_asset_session' => $by_asset
    ));
}

// ═══════════════════════════════════════════════════════════════════
// STREAK ANALYSIS — win/loss streak patterns
// ═══════════════════════════════════════════════════════════════════
function _wp_streak_analysis($conn, $asset_filter, $days) {
    $since = date('Y-m-d H:i:s', time() - ($days * 86400));
    $where = "status = 'closed' AND exit_time >= '" . $conn->real_escape_string($since) . "'";
    if ($asset_filter) $where .= " AND asset_class = '" . $conn->real_escape_string($asset_filter) . "'";

    // Get all closed trades in order
    $trades = array();
    $r = $conn->query("SELECT id, symbol, asset_class, algorithm_name, realized_pnl_usd, realized_pct, entry_time, exit_time, hold_hours
    FROM lm_trades WHERE $where ORDER BY exit_time ASC");
    if ($r) {
        while ($row = $r->fetch_assoc()) $trades[] = $row;
    }

    $max_win_streak = 0;
    $max_loss_streak = 0;
    $current_streak = 0;
    $streak_type = '';
    $streaks = array();

    foreach ($trades as $t) {
        $is_win = floatval($t['realized_pnl_usd']) > 0;
        $type = $is_win ? 'win' : 'loss';

        if ($type === $streak_type) {
            $current_streak++;
        } else {
            if ($current_streak >= 3) {
                $streaks[] = array('type' => $streak_type, 'length' => $current_streak);
            }
            $streak_type = $type;
            $current_streak = 1;
        }

        if ($is_win && $current_streak > $max_win_streak) $max_win_streak = $current_streak;
        if (!$is_win && $current_streak > $max_loss_streak) $max_loss_streak = $current_streak;
    }
    if ($current_streak >= 3) {
        $streaks[] = array('type' => $streak_type, 'length' => $current_streak);
    }

    // After-loss recovery: win rate on trade immediately after a loss
    $after_loss_total = 0;
    $after_loss_wins = 0;
    $prev_was_loss = false;
    foreach ($trades as $t) {
        $is_win = floatval($t['realized_pnl_usd']) > 0;
        if ($prev_was_loss) {
            $after_loss_total++;
            if ($is_win) $after_loss_wins++;
        }
        $prev_was_loss = !$is_win;
    }

    // Exit reason analysis
    $exit_reasons = array();
    $r2 = $conn->query("SELECT exit_reason,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(AVG(realized_pct), 2) as avg_return,
        ROUND(SUM(realized_pnl_usd), 2) as pnl
    FROM lm_trades WHERE $where AND exit_reason != ''
    GROUP BY exit_reason ORDER BY trades DESC");
    if ($r2) {
        while ($row = $r2->fetch_assoc()) {
            $trades_count = (int)$row['trades'];
            $wins_count = (int)$row['wins'];
            $exit_reasons[] = array(
                'reason' => $row['exit_reason'],
                'trades' => $trades_count,
                'wins' => $wins_count,
                'win_rate' => $trades_count > 0 ? round($wins_count / $trades_count * 100, 1) : 0,
                'avg_return' => floatval($row['avg_return']),
                'pnl' => floatval($row['pnl'])
            );
        }
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'streak_analysis',
        'days' => $days,
        'total_trades' => count($trades),
        'max_win_streak' => $max_win_streak,
        'max_loss_streak' => $max_loss_streak,
        'notable_streaks' => $streaks,
        'after_loss_recovery' => array(
            'total' => $after_loss_total,
            'wins' => $after_loss_wins,
            'recovery_rate' => $after_loss_total > 0 ? round($after_loss_wins / $after_loss_total * 100, 1) : 0
        ),
        'exit_reasons' => $exit_reasons
    ));
}

// ═══════════════════════════════════════════════════════════════════
// FULL REPORT — all analyses combined
// ═══════════════════════════════════════════════════════════════════
function _wp_full_report($conn, $asset_filter, $days) {
    $since = date('Y-m-d H:i:s', time() - ($days * 86400));
    $where_base = "status = 'closed' AND exit_time >= '" . $conn->real_escape_string($since) . "'";
    if ($asset_filter) $where_base .= " AND asset_class = '" . $conn->real_escape_string($asset_filter) . "'";

    // Capture individual action outputs via buffer
    ob_start();
    _wp_overview($conn, $asset_filter, $days);
    $overview = json_decode(ob_get_clean(), true);

    ob_start();
    _wp_time_analysis($conn, $asset_filter, $days);
    $time = json_decode(ob_get_clean(), true);

    ob_start();
    _wp_algorithm_matrix($conn, $asset_filter, $days);
    $algo = json_decode(ob_get_clean(), true);

    ob_start();
    _wp_best_setups($conn, $asset_filter, $days);
    $setups = json_decode(ob_get_clean(), true);

    ob_start();
    _wp_session_analysis($conn, $asset_filter, $days);
    $sessions = json_decode(ob_get_clean(), true);

    ob_start();
    _wp_streak_analysis($conn, $asset_filter, $days);
    $streaks = json_decode(ob_get_clean(), true);

    // Generate insights
    $insights = array();

    // Best time insight
    if (isset($overview['best_hour']['label']) && $overview['best_hour']['label'] !== 'N/A') {
        $insights[] = 'Best trading hour: ' . $overview['best_hour']['label'] . ' (' . $overview['best_hour']['win_rate'] . '% WR, ' . $overview['best_hour']['trades'] . ' trades)';
    }
    // Best algo insight
    if (isset($overview['best_algorithm']['name']) && $overview['best_algorithm']['name'] !== 'N/A') {
        $insights[] = 'Top algorithm: ' . $overview['best_algorithm']['name'] . ' (' . $overview['best_algorithm']['win_rate'] . '% WR)';
    }
    // Best asset insight
    if (isset($overview['best_asset_class']['class']) && $overview['best_asset_class']['class'] !== 'N/A') {
        $insights[] = 'Best asset class: ' . $overview['best_asset_class']['class'] . ' ($' . $overview['best_asset_class']['pnl'] . ' P&L)';
    }
    // Session insight
    if (isset($sessions['sessions'])) {
        $best_sess = null;
        foreach ($sessions['sessions'] as $s) {
            if ($s['trades'] >= 3 && (!$best_sess || $s['win_rate'] > $best_sess['win_rate'])) {
                $best_sess = $s;
            }
        }
        if ($best_sess) {
            $insights[] = 'Most profitable session: ' . $best_sess['name'] . ' (' . $best_sess['win_rate'] . '% WR, $' . $best_sess['pnl'] . ')';
        }
    }
    // Streak insight
    if (isset($streaks['max_win_streak']) && $streaks['max_win_streak'] >= 3) {
        $insights[] = 'Longest win streak: ' . $streaks['max_win_streak'] . ' consecutive wins';
    }
    // Recovery insight
    if (isset($streaks['after_loss_recovery']['recovery_rate'])) {
        $rr = $streaks['after_loss_recovery']['recovery_rate'];
        if ($rr >= 50) {
            $insights[] = 'Good loss recovery: ' . $rr . '% win rate after a losing trade';
        } else {
            $insights[] = 'Loss recovery needs work: only ' . $rr . '% win rate after losses';
        }
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'full_report',
        'days' => $days,
        'asset_filter' => $asset_filter ? $asset_filter : 'all',
        'generated_at' => date('Y-m-d H:i:s'),
        'insights' => $insights,
        'overview' => $overview,
        'time_analysis' => $time,
        'algorithm_matrix' => $algo,
        'best_setups' => $setups,
        'session_analysis' => $sessions,
        'streak_analysis' => $streaks
    ));
}

?>
