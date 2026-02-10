<?php
/**
 * Circuit Breakers for Hour-Trade Live Monitoring
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator).
 *
 * Actions:
 *   ?action=check   — Evaluate all 5 breaker conditions. Admin key to log triggers.
 *   ?action=status  — Show currently active breakers (public).
 *   ?action=history — Historical breaker activations (public). &limit=50
 */
require_once dirname(__FILE__) . '/db_connect.php';

// ─── Constants ───────────────────────────────────────────────────────
$BL_ADMIN_KEY = 'livetrader2026';

$BREAKER_RULES = array(
    'rapid_loss' => array(
        'threshold' => -5,
        'description' => 'Portfolio lost more than 5% in the last hour',
        'action' => 'Block new entries for 2 hours',
        'cooldown_hours' => 2
    ),
    'drawdown' => array(
        'threshold' => -10,
        'description' => 'Portfolio drawdown exceeds 10% from peak',
        'action' => 'Reduce position size to 50% for 4 hours',
        'cooldown_hours' => 4
    ),
    'overtrading' => array(
        'threshold' => 5,
        'description' => 'More than 5 trades opened in the last hour',
        'action' => 'Block new entries for 1 hour',
        'cooldown_hours' => 1
    ),
    'loss_streak' => array(
        'threshold' => 5,
        'description' => '5 or more consecutive losing trades',
        'action' => 'Pause all trading for 3 hours',
        'cooldown_hours' => 3
    ),
    'volatile_market' => array(
        'threshold' => 5,
        'description' => 'BTC moved more than 5% in the last hour',
        'action' => 'Reduce position size to 25% for 2 hours',
        'cooldown_hours' => 2
    )
);

// ─── Auto-create table ──────────────────────────────────────────────
$conn->query("CREATE TABLE IF NOT EXISTS lm_breaker_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trigger_time DATETIME NOT NULL,
    breaker_type VARCHAR(50) NOT NULL,
    trigger_value VARCHAR(200) NOT NULL DEFAULT '',
    threshold VARCHAR(100) NOT NULL DEFAULT '',
    action_taken VARCHAR(200) NOT NULL DEFAULT '',
    is_active TINYINT NOT NULL DEFAULT 1,
    expires_at DATETIME,
    resolved_at DATETIME,
    created_at DATETIME NOT NULL,
    KEY idx_time (trigger_time),
    KEY idx_type (breaker_type),
    KEY idx_active (is_active)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ─── Route action ────────────────────────────────────────────────────
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'check';

if ($action === 'check') {
    _bl_action_check($conn, $BL_ADMIN_KEY, $BREAKER_RULES);
} elseif ($action === 'status') {
    _bl_action_status($conn);
} elseif ($action === 'history') {
    _bl_action_history($conn);
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;


// =====================================================================
//  ACTION: check — Evaluate all 5 circuit breaker conditions
// =====================================================================
function _bl_action_check($conn, $admin_key, $rules) {
    // Determine if caller is admin (can log triggers)
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key === '') {
        $key = isset($_POST['key']) ? trim($_POST['key']) : '';
    }
    $is_admin = ($key === $admin_key);

    // If admin, expire old breakers first
    if ($is_admin) {
        $conn->query("UPDATE lm_breaker_log SET is_active=0, resolved_at=NOW() WHERE is_active=1 AND expires_at <= NOW()");
    }

    $breakers = array();
    $active_count = 0;

    // Evaluate each rule
    foreach ($rules as $rule_name => $rule) {
        $result = null;

        if ($rule_name === 'rapid_loss') {
            $result = _bl_check_rapid_loss($conn, $rule['threshold']);
        } elseif ($rule_name === 'drawdown') {
            $result = _bl_check_drawdown($conn, $rule['threshold']);
        } elseif ($rule_name === 'overtrading') {
            $result = _bl_check_overtrading($conn, $rule['threshold']);
        } elseif ($rule_name === 'loss_streak') {
            $result = _bl_check_loss_streak($conn, $rule['threshold']);
        } elseif ($rule_name === 'volatile_market') {
            $result = _bl_check_volatile_market($conn, $rule['threshold']);
        }

        if ($result === null) {
            $result = array('triggered' => false, 'value' => 'N/A', 'threshold' => $rule['threshold']);
        }

        $breaker_entry = array(
            'rule' => $rule_name,
            'triggered' => $result['triggered'],
            'current_value' => $result['value'],
            'threshold' => $result['threshold'],
            'description' => $rule['description'],
            'action_if_triggered' => $rule['action']
        );

        if ($result['triggered']) {
            $active_count++;

            // If admin, log the trigger to the database
            if ($is_admin) {
                _bl_log_trigger($conn, $rule_name, $result, $rule);
            }
        }

        $breakers[] = $breaker_entry;
    }

    $all_clear = ($active_count === 0);
    $recommendation = '';
    if ($all_clear) {
        $recommendation = 'All clear. No circuit breakers active.';
    } else {
        $recommendation = $active_count . ' circuit breaker(s) active. Trading restricted.';
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'check',
        'breakers' => $breakers,
        'active_count' => $active_count,
        'all_clear' => $all_clear,
        'recommendation' => $recommendation,
        'is_admin' => $is_admin,
        'server_time' => date('Y-m-d H:i:s')
    ));
}


// =====================================================================
//  ACTION: status — Show currently active breakers
// =====================================================================
function _bl_action_status($conn) {
    // Expire old breakers first
    $conn->query("UPDATE lm_breaker_log SET is_active=0, resolved_at=NOW() WHERE is_active=1 AND expires_at <= NOW()");

    $res = $conn->query("SELECT * FROM lm_breaker_log WHERE is_active=1 AND (expires_at IS NULL OR expires_at > NOW()) ORDER BY trigger_time DESC");

    if (!$res) {
        header('HTTP/1.0 500 Internal Server Error');
        echo json_encode(array('ok' => false, 'error' => 'Query failed'));
        return;
    }

    $active = array();
    $now = time();
    while ($row = $res->fetch_assoc()) {
        $remaining_seconds = 0;
        if ($row['expires_at'] !== null && $row['expires_at'] !== '') {
            $expires_ts = strtotime($row['expires_at']);
            $remaining_seconds = $expires_ts - $now;
            if ($remaining_seconds < 0) $remaining_seconds = 0;
        }

        $active[] = array(
            'id' => (int)$row['id'],
            'breaker_type' => $row['breaker_type'],
            'trigger_value' => $row['trigger_value'],
            'threshold' => $row['threshold'],
            'action_taken' => $row['action_taken'],
            'trigger_time' => $row['trigger_time'],
            'expires_at' => $row['expires_at'],
            'remaining_seconds' => $remaining_seconds,
            'created_at' => $row['created_at']
        );
    }

    $all_clear = (count($active) === 0);

    echo json_encode(array(
        'ok' => true,
        'action' => 'status',
        'active_breakers' => $active,
        'active_count' => count($active),
        'all_clear' => $all_clear,
        'server_time' => date('Y-m-d H:i:s')
    ));
}


// =====================================================================
//  ACTION: history — Historical breaker activations
// =====================================================================
function _bl_action_history($conn) {
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;
    if ($limit < 1) $limit = 1;
    if ($limit > 500) $limit = 500;

    // Recent activations
    $res = $conn->query("SELECT * FROM lm_breaker_log ORDER BY created_at DESC LIMIT " . $limit);

    if (!$res) {
        header('HTTP/1.0 500 Internal Server Error');
        echo json_encode(array('ok' => false, 'error' => 'Query failed'));
        return;
    }

    $entries = array();
    while ($row = $res->fetch_assoc()) {
        $entries[] = array(
            'id' => (int)$row['id'],
            'breaker_type' => $row['breaker_type'],
            'trigger_value' => $row['trigger_value'],
            'threshold' => $row['threshold'],
            'action_taken' => $row['action_taken'],
            'is_active' => (int)$row['is_active'],
            'trigger_time' => $row['trigger_time'],
            'expires_at' => $row['expires_at'],
            'resolved_at' => $row['resolved_at'],
            'created_at' => $row['created_at']
        );
    }

    // Summary by type
    $summary = array();
    $res2 = $conn->query("SELECT breaker_type, COUNT(*) as cnt FROM lm_breaker_log GROUP BY breaker_type ORDER BY cnt DESC");
    if ($res2) {
        while ($row = $res2->fetch_assoc()) {
            $summary[] = array(
                'breaker_type' => $row['breaker_type'],
                'total_activations' => (int)$row['cnt']
            );
        }
    }

    // Total count
    $total = 0;
    $res3 = $conn->query("SELECT COUNT(*) as cnt FROM lm_breaker_log");
    if ($res3 && $row3 = $res3->fetch_assoc()) {
        $total = (int)$row3['cnt'];
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'history',
        'total_entries' => $total,
        'showing' => count($entries),
        'limit' => $limit,
        'entries' => $entries,
        'summary_by_type' => $summary,
        'server_time' => date('Y-m-d H:i:s')
    ));
}


// =====================================================================
//  CHECKER: rapid_loss — Portfolio lost more than X% in the last hour
// =====================================================================
function _bl_check_rapid_loss($conn, $threshold) {
    // Get sum of realized PnL from trades closed in the last hour
    $hourly_pnl = 0;
    $res = $conn->query("SELECT SUM(realized_pnl_usd) as total_pnl FROM lm_trades WHERE status='closed' AND exit_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)");
    if ($res && $row = $res->fetch_assoc()) {
        $hourly_pnl = ($row['total_pnl'] !== null) ? (float)$row['total_pnl'] : 0;
    }

    // Get portfolio value from latest snapshot
    $portfolio_value = 0;
    $res2 = $conn->query("SELECT total_value_usd FROM lm_snapshots ORDER BY snapshot_time DESC LIMIT 1");
    if ($res2 && $row2 = $res2->fetch_assoc()) {
        $portfolio_value = (float)$row2['total_value_usd'];
    }

    // Calculate hourly loss percentage
    $hourly_loss_pct = 0;
    if ($portfolio_value > 0) {
        $hourly_loss_pct = round(($hourly_pnl / $portfolio_value) * 100, 2);
    }

    $triggered = ($hourly_loss_pct <= $threshold);

    return array(
        'triggered' => $triggered,
        'value' => $hourly_loss_pct,
        'threshold' => $threshold,
        'detail' => 'Hourly PnL: $' . number_format($hourly_pnl, 2) . ' / Portfolio: $' . number_format($portfolio_value, 2)
    );
}


// =====================================================================
//  CHECKER: drawdown — Portfolio drawdown exceeds X% from peak
// =====================================================================
function _bl_check_drawdown($conn, $threshold) {
    $peak_value = 0;
    $total_value = 0;

    $res = $conn->query("SELECT peak_value, total_value_usd FROM lm_snapshots ORDER BY snapshot_time DESC LIMIT 1");
    if ($res && $row = $res->fetch_assoc()) {
        $peak_value = (float)$row['peak_value'];
        $total_value = (float)$row['total_value_usd'];
    }

    $drawdown_pct = 0;
    if ($peak_value > 0) {
        $drawdown_pct = round((($total_value - $peak_value) / $peak_value) * 100, 2);
    }

    $triggered = ($drawdown_pct <= $threshold);

    return array(
        'triggered' => $triggered,
        'value' => $drawdown_pct,
        'threshold' => $threshold,
        'detail' => 'Peak: $' . number_format($peak_value, 2) . ' / Current: $' . number_format($total_value, 2)
    );
}


// =====================================================================
//  CHECKER: overtrading — More than X trades opened in the last hour
// =====================================================================
function _bl_check_overtrading($conn, $threshold) {
    $trade_count = 0;

    $res = $conn->query("SELECT COUNT(*) as cnt FROM lm_trades WHERE entry_time >= DATE_SUB(NOW(), INTERVAL 1 HOUR)");
    if ($res && $row = $res->fetch_assoc()) {
        $trade_count = (int)$row['cnt'];
    }

    $triggered = ($trade_count >= $threshold);

    return array(
        'triggered' => $triggered,
        'value' => $trade_count,
        'threshold' => $threshold,
        'detail' => $trade_count . ' trades in last hour (limit: ' . $threshold . ')'
    );
}


// =====================================================================
//  CHECKER: loss_streak — X or more consecutive losing trades
// =====================================================================
function _bl_check_loss_streak($conn, $threshold) {
    $streak = 0;

    $res = $conn->query("SELECT realized_pnl_usd FROM lm_trades WHERE status='closed' ORDER BY exit_time DESC LIMIT 20");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $pnl = (float)$row['realized_pnl_usd'];
            if ($pnl < 0) {
                $streak++;
            } else {
                break; // streak broken
            }
        }
    }

    $triggered = ($streak >= $threshold);

    return array(
        'triggered' => $triggered,
        'value' => $streak . ' consecutive losses',
        'threshold' => $threshold . ' consecutive losses',
        'detail' => 'Current losing streak: ' . $streak
    );
}


// =====================================================================
//  CHECKER: volatile_market — BTC moved more than X% in the last hour
// =====================================================================
function _bl_check_volatile_market($conn, $threshold) {
    $change_1h = 0;

    $res = $conn->query("SELECT change_1h_pct FROM lm_price_cache WHERE symbol='BTCUSD' LIMIT 1");
    if ($res && $row = $res->fetch_assoc()) {
        $change_1h = (float)$row['change_1h_pct'];
    }

    $abs_change = abs($change_1h);
    $triggered = ($abs_change >= $threshold);

    return array(
        'triggered' => $triggered,
        'value' => $change_1h,
        'threshold' => $threshold,
        'detail' => 'BTC 1h change: ' . $change_1h . '% (abs: ' . $abs_change . '%)'
    );
}


// =====================================================================
//  HELPER: Log a breaker trigger to the database
// =====================================================================
function _bl_log_trigger($conn, $rule_name, $result, $rule) {
    $now = date('Y-m-d H:i:s');
    $cooldown_hours = isset($rule['cooldown_hours']) ? (int)$rule['cooldown_hours'] : 1;

    // Check if this breaker type is already active (avoid duplicate logging)
    $type_esc = $conn->real_escape_string($rule_name);
    $res = $conn->query("SELECT id FROM lm_breaker_log WHERE breaker_type='" . $type_esc . "' AND is_active=1 AND (expires_at IS NULL OR expires_at > NOW()) LIMIT 1");
    if ($res && $res->fetch_assoc()) {
        // Already an active breaker of this type, skip logging
        return;
    }

    // Build trigger_value string
    $trigger_value = '';
    if (is_array($result['value'])) {
        $trigger_value = json_encode($result['value']);
    } else {
        $trigger_value = (string)$result['value'];
    }

    // Build threshold string
    $threshold_str = '';
    if (is_array($result['threshold'])) {
        $threshold_str = json_encode($result['threshold']);
    } else {
        $threshold_str = (string)$result['threshold'];
    }

    $trigger_value_esc = $conn->real_escape_string($trigger_value);
    $threshold_esc = $conn->real_escape_string($threshold_str);
    $action_esc = $conn->real_escape_string($rule['action']);

    $expires_at = date('Y-m-d H:i:s', strtotime('+' . $cooldown_hours . ' hours'));

    $sql = "INSERT INTO lm_breaker_log (trigger_time, breaker_type, trigger_value, threshold, action_taken, is_active, expires_at, created_at)"
         . " VALUES ('" . $now . "', '" . $type_esc . "', '" . $trigger_value_esc . "', '" . $threshold_esc . "', '" . $action_esc . "', 1, '" . $conn->real_escape_string($expires_at) . "', '" . $now . "')";

    $conn->query($sql);
}
?>
