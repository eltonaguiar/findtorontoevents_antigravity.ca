<?php
/**
 * Behavioral / Emotional Circuit Breaker API
 * Rule-based guardrails to prevent catastrophic losses during drawdowns.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   check    — Evaluate all circuit breaker conditions
 *   history  — Log of all activations
 *   status   — Current active breakers
 *
 * Usage:
 *   GET .../circuit_breaker.php?action=check&key=stocksrefresh2026
 *   GET .../circuit_breaker.php?action=history
 *   GET .../circuit_breaker.php?action=status
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'status';
$response = array('ok' => true, 'action' => $action);
$admin_key = 'stocksrefresh2026';
$is_admin = (isset($_GET['key']) && $_GET['key'] === $admin_key);

// ═══════════════════════════════════════════════
// Auto-create table
// ═══════════════════════════════════════════════
$conn->query("CREATE TABLE IF NOT EXISTS circuit_breaker_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trigger_date DATE NOT NULL,
    breaker_type VARCHAR(50) NOT NULL,
    trigger_value VARCHAR(200) NOT NULL DEFAULT '',
    threshold VARCHAR(100) NOT NULL DEFAULT '',
    action_taken VARCHAR(200) NOT NULL DEFAULT '',
    is_active TINYINT NOT NULL DEFAULT 1,
    expires_at DATETIME,
    resolved_at DATETIME,
    created_at DATETIME NOT NULL,
    KEY idx_date (trigger_date),
    KEY idx_type (breaker_type),
    KEY idx_active (is_active)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ═══════════════════════════════════════════════
// Circuit Breaker Rules
// ═══════════════════════════════════════════════
$BREAKER_RULES = array(
    'drawdown' => array(
        'threshold' => 15,         // % drawdown from peak
        'action' => 'Reduce position size to 50% for 5 trading days',
        'cooldown_days' => 5
    ),
    'loss_streak' => array(
        'threshold' => 5,          // consecutive losses
        'action' => 'Pause new entries for 2 trading days',
        'cooldown_days' => 2
    ),
    'overtrading' => array(
        'threshold' => 10,         // trades per day
        'action' => 'Block additional entries for today',
        'cooldown_days' => 1
    ),
    'regime_mismatch' => array(
        'threshold' => 'risk_off',  // block momentum during risk_off
        'action' => 'Block momentum entries or downsize to 25%',
        'cooldown_days' => 0       // lasts while regime persists
    ),
    'concentration' => array(
        'threshold' => 30,         // % of portfolio in one ticker
        'action' => 'Block additional entries in concentrated ticker',
        'cooldown_days' => 0
    )
);

// ═══════════════════════════════════════════════
// Helper: Check drawdown breaker
// ═══════════════════════════════════════════════
function _cb_check_drawdown($conn, $threshold) {
    // Get peak equity and current from paper_portfolio_daily
    $r = $conn->query("SELECT cumulative_realized_pnl, peak_equity, current_drawdown_pct, max_drawdown_pct
                        FROM paper_portfolio_daily ORDER BY snapshot_date DESC LIMIT 1");
    if (!$r || $r->num_rows === 0) return array('triggered' => false);

    $row = $r->fetch_assoc();
    $drawdown = abs((float)$row['current_drawdown_pct']);
    $peak = (float)$row['peak_equity'];
    $current = (float)$row['cumulative_realized_pnl'];

    if ($drawdown >= $threshold) {
        return array(
            'triggered' => true,
            'value' => round($drawdown, 2) . '% drawdown from peak',
            'threshold' => $threshold . '% max drawdown',
            'details' => array('peak' => $peak, 'current' => $current, 'drawdown_pct' => round($drawdown, 2))
        );
    }
    return array('triggered' => false, 'current_drawdown' => round($drawdown, 2));
}

// ═══════════════════════════════════════════════
// Helper: Check loss streak breaker
// ═══════════════════════════════════════════════
function _cb_check_loss_streak($conn, $threshold) {
    // Count consecutive losses from most recent closed trades
    $r = $conn->query("SELECT return_pct FROM paper_trades WHERE status='closed'
                        ORDER BY exit_date DESC, id DESC LIMIT 20");
    if (!$r || $r->num_rows === 0) return array('triggered' => false);

    $streak = 0;
    while ($row = $r->fetch_assoc()) {
        if ((float)$row['return_pct'] <= 0) {
            $streak++;
        } else {
            break; // streak broken
        }
    }

    if ($streak >= $threshold) {
        return array(
            'triggered' => true,
            'value' => $streak . ' consecutive losses',
            'threshold' => $threshold . ' consecutive losses'
        );
    }
    return array('triggered' => false, 'current_streak' => $streak);
}

// ═══════════════════════════════════════════════
// Helper: Check overtrading breaker
// ═══════════════════════════════════════════════
function _cb_check_overtrading($conn, $threshold) {
    $today = date('Y-m-d');
    $r = $conn->query("SELECT COUNT(*) as cnt FROM paper_trades WHERE enter_date='$today'");
    $count = ($r && $r->num_rows > 0) ? (int)$r->fetch_assoc() : 0;
    if (is_array($count)) $count = (int)$count['cnt'];

    if ($count >= $threshold) {
        return array(
            'triggered' => true,
            'value' => $count . ' trades today',
            'threshold' => $threshold . ' max trades/day'
        );
    }
    return array('triggered' => false, 'trades_today' => $count);
}

// ═══════════════════════════════════════════════
// Helper: Check regime mismatch breaker
// ═══════════════════════════════════════════════
function _cb_check_regime_mismatch($conn) {
    $r = $conn->query("SELECT regime FROM market_regimes ORDER BY trade_date DESC LIMIT 1");
    $regime = 'unknown';
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $regime = $row['regime'] ? $row['regime'] : 'unknown';
    }

    // Check if any open positions are momentum-type during risk_off
    if ($regime === 'risk_off' || $regime === 'high' || $regime === 'extreme') {
        // Check for momentum-type open positions
        $momentum_algos = array('Momentum', 'Technical Momentum', 'Breakout', 'Gap Up', 'MACD Crossover');
        $open = $conn->query("SELECT algorithm_name FROM paper_trades WHERE status='open'");
        $mismatches = array();
        if ($open) {
            while ($row = $open->fetch_assoc()) {
                foreach ($momentum_algos as $ma) {
                    if (stripos($row['algorithm_name'], $ma) !== false) {
                        $mismatches[] = $row['algorithm_name'];
                        break;
                    }
                }
            }
        }

        if (count($mismatches) > 0) {
            return array(
                'triggered' => true,
                'value' => 'Regime: ' . $regime . ', ' . count($mismatches) . ' momentum positions open',
                'threshold' => 'No momentum during risk_off',
                'mismatched_algos' => $mismatches
            );
        }
    }

    return array('triggered' => false, 'current_regime' => $regime);
}

// ═══════════════════════════════════════════════
// Helper: Check concentration breaker
// ═══════════════════════════════════════════════
function _cb_check_concentration($conn, $threshold) {
    $open = $conn->query("SELECT ticker, COUNT(*) as cnt FROM paper_trades
                           WHERE status='open' GROUP BY ticker ORDER BY cnt DESC");
    $total_r = $conn->query("SELECT COUNT(*) as total FROM paper_trades WHERE status='open'");
    $total = ($total_r && $total_r->num_rows > 0) ? (int)$total_r->fetch_assoc() : 0;
    if (is_array($total)) $total = (int)$total['total'];

    if ($total === 0) return array('triggered' => false);

    $concentrated = array();
    if ($open) {
        while ($row = $open->fetch_assoc()) {
            $pct = round(((int)$row['cnt'] / $total) * 100, 1);
            if ($pct >= $threshold) {
                $concentrated[] = array('ticker' => $row['ticker'], 'pct' => $pct, 'positions' => (int)$row['cnt']);
            }
        }
    }

    if (count($concentrated) > 0) {
        return array(
            'triggered' => true,
            'value' => count($concentrated) . ' tickers over ' . $threshold . '% concentration',
            'threshold' => $threshold . '% max per ticker',
            'concentrated_tickers' => $concentrated
        );
    }
    return array('triggered' => false);
}

// ═══════════════════════════════════════════════
// ACTION: check — Evaluate all circuit breakers
// ═══════════════════════════════════════════════
if ($action === 'check') {
    $today = date('Y-m-d');
    $now = date('Y-m-d H:i:s');
    $results = array();
    $active_breakers = 0;

    // 1. Drawdown breaker
    $dd = _cb_check_drawdown($conn, $BREAKER_RULES['drawdown']['threshold']);
    $dd['rule'] = 'drawdown';
    $dd['action_if_triggered'] = $BREAKER_RULES['drawdown']['action'];
    $results[] = $dd;
    if ($dd['triggered']) {
        $active_breakers++;
        if ($is_admin) {
            $conn->query("INSERT INTO circuit_breaker_log
                (trigger_date, breaker_type, trigger_value, threshold, action_taken,
                 is_active, expires_at, created_at)
                VALUES ('$today', 'drawdown',
                '" . $conn->real_escape_string($dd['value']) . "',
                '" . $conn->real_escape_string($dd['threshold']) . "',
                '" . $conn->real_escape_string($BREAKER_RULES['drawdown']['action']) . "',
                1, DATE_ADD('$now', INTERVAL " . $BREAKER_RULES['drawdown']['cooldown_days'] . " DAY), '$now')");
        }
    }

    // 2. Loss streak breaker
    $ls = _cb_check_loss_streak($conn, $BREAKER_RULES['loss_streak']['threshold']);
    $ls['rule'] = 'loss_streak';
    $ls['action_if_triggered'] = $BREAKER_RULES['loss_streak']['action'];
    $results[] = $ls;
    if ($ls['triggered']) {
        $active_breakers++;
        if ($is_admin) {
            $conn->query("INSERT INTO circuit_breaker_log
                (trigger_date, breaker_type, trigger_value, threshold, action_taken,
                 is_active, expires_at, created_at)
                VALUES ('$today', 'loss_streak',
                '" . $conn->real_escape_string($ls['value']) . "',
                '" . $conn->real_escape_string($ls['threshold']) . "',
                '" . $conn->real_escape_string($BREAKER_RULES['loss_streak']['action']) . "',
                1, DATE_ADD('$now', INTERVAL " . $BREAKER_RULES['loss_streak']['cooldown_days'] . " DAY), '$now')");
        }
    }

    // 3. Overtrading breaker
    $ot = _cb_check_overtrading($conn, $BREAKER_RULES['overtrading']['threshold']);
    $ot['rule'] = 'overtrading';
    $ot['action_if_triggered'] = $BREAKER_RULES['overtrading']['action'];
    $results[] = $ot;
    if ($ot['triggered']) { $active_breakers++; }

    // 4. Regime mismatch breaker
    $rm = _cb_check_regime_mismatch($conn);
    $rm['rule'] = 'regime_mismatch';
    $rm['action_if_triggered'] = $BREAKER_RULES['regime_mismatch']['action'];
    $results[] = $rm;
    if ($rm['triggered']) { $active_breakers++; }

    // 5. Concentration breaker
    $cn = _cb_check_concentration($conn, $BREAKER_RULES['concentration']['threshold']);
    $cn['rule'] = 'concentration';
    $cn['action_if_triggered'] = $BREAKER_RULES['concentration']['action'];
    $results[] = $cn;
    if ($cn['triggered']) { $active_breakers++; }

    // Expire old breakers
    if ($is_admin) {
        $conn->query("UPDATE circuit_breaker_log SET is_active=0, resolved_at='$now'
                       WHERE is_active=1 AND expires_at IS NOT NULL AND expires_at <= '$now'");
    }

    $response['breakers'] = $results;
    $response['active_count'] = $active_breakers;
    $response['all_clear'] = ($active_breakers === 0);
    $response['recommendation'] = ($active_breakers === 0)
        ? 'All clear. Normal trading conditions.'
        : $active_breakers . ' circuit breaker(s) active. Reduce exposure or pause trading.';

} elseif ($action === 'history') {
    // ═══════════════════════════════════════════════
    // ACTION: history — Historical breaker activations
    // ═══════════════════════════════════════════════
    $limit = isset($_GET['limit']) ? max(1, min(200, (int)$_GET['limit'])) : 50;

    $history = array();
    $hr = $conn->query("SELECT * FROM circuit_breaker_log ORDER BY created_at DESC LIMIT $limit");
    if ($hr) {
        while ($row = $hr->fetch_assoc()) {
            $row['is_active'] = (int)$row['is_active'];
            $history[] = $row;
        }
    }

    $response['history'] = $history;
    $response['count'] = count($history);

    // Summary by type
    $by_type = array();
    $tr = $conn->query("SELECT breaker_type, COUNT(*) as cnt FROM circuit_breaker_log GROUP BY breaker_type ORDER BY cnt DESC");
    if ($tr) {
        while ($row = $tr->fetch_assoc()) $by_type[] = $row;
    }
    $response['by_type'] = $by_type;

} elseif ($action === 'status') {
    // ═══════════════════════════════════════════════
    // ACTION: status — Currently active breakers
    // ═══════════════════════════════════════════════
    $now = date('Y-m-d H:i:s');

    $active = array();
    $ar = $conn->query("SELECT * FROM circuit_breaker_log
                         WHERE is_active=1 AND (expires_at IS NULL OR expires_at > '$now')
                         ORDER BY created_at DESC");
    if ($ar) {
        while ($row = $ar->fetch_assoc()) {
            $row['is_active'] = (int)$row['is_active'];
            $active[] = $row;
        }
    }

    $response['active_breakers'] = $active;
    $response['count'] = count($active);
    $response['all_clear'] = (count($active) === 0);
}

echo json_encode($response);
$conn->close();
