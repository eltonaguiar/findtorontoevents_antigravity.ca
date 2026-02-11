<?php
/**
 * Unified Predictions API - Phase 3 Implementation
 * Aggregates predictions from all systems into unified tracking
 * 
 * Actions:
 *   leaderboard    - Algorithm leaderboard with Sharpe ratios
 *   hidden_winners - Elite performers (Sharpe >= 1.0, 30+ trades)
 *   system_summary - Performance by system
 *   recent         - Recent predictions (last 24h)
 *   add_prediction - Add a new prediction (admin only)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Database connection - use stocks DB on production
$conn = @new mysqli('mysql.50webs.com', 'ejaguiar1_stocks', 'stocks', 'ejaguiar1_stocks');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed'));
    exit;
}

$action = isset($_GET['action']) ? $_GET['action'] : 'leaderboard';
$key = isset($_GET['key']) ? $_GET['key'] : '';
$ADMIN_KEY = 'antigravity2026';

// ═══════════════════════════════════════════════════════════════
// ACTION: leaderboard - Algorithm performance rankings
// ═══════════════════════════════════════════════════════════════
if ($action === 'leaderboard') {
    $min_trades = isset($_GET['min_trades']) ? (int) $_GET['min_trades'] : 10;
    $system_filter = isset($_GET['system']) ? $conn->real_escape_string($_GET['system']) : '';

    // Try the view first; if it doesn't exist, build from stock_picks
    $result = @$conn->query("SELECT * FROM v_algorithm_leaderboard WHERE total_trades >= " . $min_trades . " ORDER BY sharpe_ratio DESC LIMIT 50");

    if (!$result) {
        // Fallback: build leaderboard from stock_picks
        $where = "1=1";
        if ($system_filter) {
            $where .= " AND algorithm = '" . $conn->real_escape_string($system_filter) . "'";
        }

        $result = $conn->query("SELECT
            algorithm,
            COUNT(*) as total_trades,
            SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
            ROUND(SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN outcome IN ('win','loss') THEN 1 ELSE 0 END), 0) * 100, 1) as win_rate,
            ROUND(AVG(CASE WHEN outcome IN ('win','loss') THEN pnl_pct ELSE NULL END), 2) as avg_pnl,
            ROUND(SUM(CASE WHEN outcome IN ('win','loss') THEN pnl_pct ELSE 0 END), 2) as total_pnl,
            MAX(pick_date) as last_trade_date
            FROM stock_picks
            WHERE outcome IS NOT NULL AND outcome != 'pending' AND " . $where . "
            GROUP BY algorithm
            HAVING COUNT(*) >= " . $min_trades . "
            ORDER BY win_rate DESC
            LIMIT 50");
    }

    $leaderboard = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $leaderboard[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'leaderboard' => $leaderboard,
        'count' => count($leaderboard),
        'filters' => array('min_trades' => $min_trades, 'system' => $system_filter)
    ));
}

// ═══════════════════════════════════════════════════════════════
// ACTION: hidden_winners - Elite performers
// ═══════════════════════════════════════════════════════════════
elseif ($action === 'hidden_winners') {
    $result = @$conn->query("SELECT * FROM v_hidden_winners ORDER BY sharpe_ratio DESC");

    if (!$result) {
        // Fallback: algorithms with high win rate and sufficient trades
        $result = $conn->query("SELECT
            algorithm,
            COUNT(*) as total_trades,
            SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
            ROUND(SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN outcome IN ('win','loss') THEN 1 ELSE 0 END), 0) * 100, 1) as win_rate,
            ROUND(AVG(CASE WHEN outcome IN ('win','loss') THEN pnl_pct ELSE NULL END), 2) as avg_pnl,
            ROUND(SUM(CASE WHEN outcome IN ('win','loss') THEN pnl_pct ELSE 0 END), 2) as total_pnl
            FROM stock_picks
            WHERE outcome IS NOT NULL AND outcome != 'pending'
            GROUP BY algorithm
            HAVING COUNT(*) >= 30 AND win_rate >= 55
            ORDER BY win_rate DESC");
    }

    $winners = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $winners[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'hidden_winners' => $winners,
        'count' => count($winners),
        'criteria' => 'Win rate >= 55%, Min 30 trades'
    ));
}

// ═══════════════════════════════════════════════════════════════
// ACTION: system_summary - Performance by system
// ═══════════════════════════════════════════════════════════════
elseif ($action === 'system_summary') {
    $result = @$conn->query("SELECT * FROM v_system_performance ORDER BY sharpe_ratio DESC");

    if (!$result) {
        // Fallback: summarize from stock_picks by algorithm family
        $result = $conn->query("SELECT
            algorithm as system,
            COUNT(*) as total_trades,
            SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) as losses,
            ROUND(SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) / NULLIF(SUM(CASE WHEN outcome IN ('win','loss') THEN 1 ELSE 0 END), 0) * 100, 1) as win_rate,
            ROUND(AVG(CASE WHEN outcome IN ('win','loss') THEN pnl_pct ELSE NULL END), 2) as avg_pnl,
            MAX(pick_date) as last_trade_date
            FROM stock_picks
            WHERE outcome IS NOT NULL AND outcome != 'pending'
            GROUP BY algorithm
            ORDER BY win_rate DESC");
    }

    $systems = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $systems[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'systems' => $systems,
        'count' => count($systems)
    ));
}

// ═══════════════════════════════════════════════════════════════
// ACTION: recent - Recent predictions (last 24h)
// ═══════════════════════════════════════════════════════════════
elseif ($action === 'recent') {
    $hours = isset($_GET['hours']) ? (int) $_GET['hours'] : 24;
    if ($hours > 168) {
        $hours = 168; // max 1 week
    }

    // Try unified_predictions first, fall back to stock_picks
    $result = @$conn->query("SELECT * FROM unified_predictions 
        WHERE entry_timestamp >= DATE_SUB(NOW(), INTERVAL " . $hours . " HOUR)
        ORDER BY entry_timestamp DESC LIMIT 100");

    if (!$result) {
        $result = $conn->query("SELECT
            id, algorithm, ticker as asset, pick_date as entry_timestamp, 
            entry_price, outcome, pnl_pct, latest_price as exit_price
            FROM stock_picks
            WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL " . intval(ceil($hours / 24)) . " DAY)
            ORDER BY pick_date DESC
            LIMIT 100");
    }

    $predictions = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $predictions[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'predictions' => $predictions,
        'count' => count($predictions),
        'hours' => $hours
    ));
}

// ═══════════════════════════════════════════════════════════════
// PHASE 4: ADVANCED ANALYTICS ENDPOINTS
// ═══════════════════════════════════════════════════════════════

// ACTION: risk_dashboard - Comprehensive risk metrics
elseif ($action === 'risk_dashboard') {
    $result = @$conn->query("SELECT * FROM v_risk_dashboard ORDER BY sharpe_ratio DESC LIMIT 50");

    $dashboard = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $dashboard[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'risk_dashboard' => $dashboard,
        'count' => count($dashboard)
    ));
}

// ACTION: drawdown - Drawdown analysis
elseif ($action === 'drawdown') {
    $by = isset($_GET['by']) ? $_GET['by'] : 'system';

    if ($by === 'algorithm') {
        $result = @$conn->query("SELECT * FROM v_max_drawdown_by_algorithm ORDER BY max_drawdown_pct ASC LIMIT 50");
    } else {
        $result = @$conn->query("SELECT * FROM v_max_drawdown_by_system ORDER BY max_drawdown_pct ASC");
    }

    $drawdowns = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $drawdowns[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'drawdowns' => $drawdowns,
        'by' => $by,
        'count' => count($drawdowns)
    ));
}

// ACTION: correlation - Cross-system correlation matrix
elseif ($action === 'correlation') {
    $result = @$conn->query("SELECT * FROM v_system_correlation ORDER BY correlation DESC");

    $correlations = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $correlations[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'correlations' => $correlations,
        'count' => count($correlations)
    ));
}

// ACTION: backtest_vs_live - Performance comparison
elseif ($action === 'backtest_vs_live') {
    $result = @$conn->query("SELECT * FROM v_backtest_vs_live ORDER BY performance_degradation_pct DESC LIMIT 50");

    $comparisons = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $comparisons[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'comparisons' => $comparisons,
        'count' => count($comparisons)
    ));
}

// ACTION: streaks - Win/loss streak analysis
elseif ($action === 'streaks') {
    $result = @$conn->query("SELECT * FROM v_win_loss_streaks ORDER BY max_win_streak DESC LIMIT 50");

    $streaks = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $streaks[] = $row;
        }
    }

    echo json_encode(array(
        'ok' => true,
        'streaks' => $streaks,
        'count' => count($streaks)
    ));
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
