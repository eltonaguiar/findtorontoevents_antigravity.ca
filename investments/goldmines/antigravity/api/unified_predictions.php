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

// Database connection (update with your credentials)
$conn = new mysqli('localhost', 'root', '', 'predictions_unified');
if ($conn->connect_error) {
    die(json_encode(['ok' => false, 'error' => 'Database connection failed']));
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

    $where = "total_trades >= $min_trades";
    if ($system_filter)
        $where .= " AND system = '$system_filter'";

    $result = $conn->query("SELECT * FROM v_algorithm_leaderboard WHERE $where ORDER BY sharpe_ratio DESC LIMIT 50");

    $leaderboard = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $leaderboard[] = $row;
        }
    }

    echo json_encode([
        'ok' => true,
        'leaderboard' => $leaderboard,
        'count' => count($leaderboard),
        'filters' => ['min_trades' => $min_trades, 'system' => $system_filter]
    ]);
}

// ═══════════════════════════════════════════════════════════════
// ACTION: hidden_winners - Elite performers
// ═══════════════════════════════════════════════════════════════
elseif ($action === 'hidden_winners') {
    $result = $conn->query("SELECT * FROM v_hidden_winners ORDER BY sharpe_ratio DESC");

    $winners = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $winners[] = $row;
        }
    }

    echo json_encode([
        'ok' => true,
        'hidden_winners' => $winners,
        'count' => count($winners),
        'criteria' => 'Sharpe >= 1.0, Min 30 trades'
    ]);
}

// ═══════════════════════════════════════════════════════════════
// ACTION: system_summary - Performance by system
// ═══════════════════════════════════════════════════════════════
elseif ($action === 'system_summary') {
    $result = $conn->query("SELECT * FROM v_system_performance ORDER BY sharpe_ratio DESC");

    $systems = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $systems[] = $row;
        }
    }

    echo json_encode([
        'ok' => true,
        'systems' => $systems,
        'count' => count($systems)
    ]);
}

// ═══════════════════════════════════════════════════════════════
// ACTION: recent - Recent predictions (last 24h)
// ═══════════════════════════════════════════════════════════════
elseif ($action === 'recent') {
    $hours = isset($_GET['hours']) ? (int) $_GET['hours'] : 24;
    if ($hours > 168)
        $hours = 168; // max 1 week

    $result = $conn->query("
        SELECT * FROM unified_predictions 
        WHERE entry_timestamp >= DATE_SUB(NOW(), INTERVAL $hours HOUR)
        ORDER BY entry_timestamp DESC 
        LIMIT 100
    ");

    $predictions = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $predictions[] = $row;
        }
    }

    echo json_encode([
        'ok' => true,
        'predictions' => $predictions,
        'count' => count($predictions),
        'hours' => $hours
    ]);
}

// ═══════════════════════════════════════════════════════════════
// ACTION: add_prediction - Add new prediction (admin only)
// ═══════════════════════════════════════════════════════════════
elseif ($action === 'add_prediction') {
    if ($key !== $ADMIN_KEY) {
        echo json_encode(['ok' => false, 'error' => 'Unauthorized']);
        exit;
    }

    // Required fields
    $system = isset($_POST['system']) ? $conn->real_escape_string($_POST['system']) : '';
    $algorithm = isset($_POST['algorithm']) ? $conn->real_escape_string($_POST['algorithm']) : '';
    $asset = isset($_POST['asset']) ? $conn->real_escape_string($_POST['asset']) : '';
    $entry_price = isset($_POST['entry_price']) ? (float) $_POST['entry_price'] : 0;
    $entry_signal = isset($_POST['entry_signal']) ? $conn->real_escape_string($_POST['entry_signal']) : 'buy';

    // Optional fields
    $algorithm_family = isset($_POST['algorithm_family']) ? $conn->real_escape_string($_POST['algorithm_family']) : NULL;
    $asset_type = isset($_POST['asset_type']) ? $conn->real_escape_string($_POST['asset_type']) : NULL;
    $confidence = isset($_POST['confidence']) ? $conn->real_escape_string($_POST['confidence']) : NULL;
    $score = isset($_POST['score']) ? (int) $_POST['score'] : NULL;
    $is_backtest = isset($_POST['is_backtest']) ? (int) $_POST['is_backtest'] : 0;

    if (!$system || !$algorithm || !$asset) {
        echo json_encode(['ok' => false, 'error' => 'Missing required fields']);
        exit;
    }

    $sql = "INSERT INTO unified_predictions 
            (system, algorithm, algorithm_family, asset, asset_type, entry_timestamp, entry_price, 
             entry_signal, confidence, score, is_backtest) 
            VALUES 
            ('$system', '$algorithm', " . ($algorithm_family ? "'$algorithm_family'" : "NULL") . ", 
             '$asset', " . ($asset_type ? "'$asset_type'" : "NULL") . ", NOW(), $entry_price, 
             '$entry_signal', " . ($confidence ? "'$confidence'" : "NULL") . ", 
             " . ($score ? $score : "NULL") . ", $is_backtest)";

    if ($conn->query($sql)) {
        echo json_encode([
            'ok' => true,
            'prediction_id' => $conn->insert_id,
            'message' => 'Prediction added successfully'
        ]);
    } else {
        echo json_encode(['ok' => false, 'error' => $conn->error]);
    }
}

// ═══════════════════════════════════════════════════════════════
// ACTION: update_outcome - Update prediction outcome (admin only)
// ═══════════════════════════════════════════════════════════════
elseif ($action === 'update_outcome') {
    if ($key !== $ADMIN_KEY) {
        echo json_encode(['ok' => false, 'error' => 'Unauthorized']);
        exit;
    }

    $id = isset($_POST['id']) ? (int) $_POST['id'] : 0;
    $exit_price = isset($_POST['exit_price']) ? (float) $_POST['exit_price'] : 0;
    $outcome = isset($_POST['outcome']) ? $conn->real_escape_string($_POST['outcome']) : 'pending';
    $exit_reason = isset($_POST['exit_reason']) ? $conn->real_escape_string($_POST['exit_reason']) : 'manual';

    if (!$id || !$exit_price) {
        echo json_encode(['ok' => false, 'error' => 'Missing required fields']);
        exit;
    }

    // Get entry price to calculate P&L
    $result = $conn->query("SELECT entry_price, entry_timestamp FROM unified_predictions WHERE id = $id");
    if (!$result || $result->num_rows === 0) {
        echo json_encode(['ok' => false, 'error' => 'Prediction not found']);
        exit;
    }

    $row = $result->fetch_assoc();
    $entry_price = (float) $row['entry_price'];
    $entry_timestamp = $row['entry_timestamp'];

    // Calculate P&L
    $pnl_pct = (($exit_price - $entry_price) / $entry_price) * 100;

    // Calculate hold duration
    $hold_duration = (strtotime('now') - strtotime($entry_timestamp)) / 3600; // hours

    $sql = "UPDATE unified_predictions SET 
            exit_timestamp = NOW(),
            exit_price = $exit_price,
            exit_reason = '$exit_reason',
            outcome = '$outcome',
            pnl_pct = $pnl_pct,
            hold_duration_hours = $hold_duration
            WHERE id = $id";

    if ($conn->query($sql)) {
        echo json_encode([
            'ok' => true,
            'prediction_id' => $id,
            'pnl_pct' => round($pnl_pct, 4),
            'hold_duration_hours' => round($hold_duration, 2),
            'message' => 'Outcome updated successfully'
        ]);
    } else {
        echo json_encode(['ok' => false, 'error' => $conn->error]);
    }
}

// ═══════════════════════════════════════════════════════════════
// PHASE 4: ADVANCED ANALYTICS ENDPOINTS
// ═══════════════════════════════════════════════════════════════

// ACTION: risk_dashboard - Comprehensive risk metrics
elseif ($action === 'risk_dashboard') {
    $result = $conn->query("SELECT * FROM v_risk_dashboard ORDER BY sharpe_ratio DESC LIMIT 50");

    $dashboard = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $dashboard[] = $row;
        }
    }

    echo json_encode([
        'ok' => true,
        'risk_dashboard' => $dashboard,
        'count' => count($dashboard)
    ]);
}

// ACTION: drawdown - Drawdown analysis
elseif ($action === 'drawdown') {
    $by = isset($_GET['by']) ? $_GET['by'] : 'system';

    if ($by === 'algorithm') {
        $result = $conn->query("SELECT * FROM v_max_drawdown_by_algorithm ORDER BY max_drawdown_pct ASC LIMIT 50");
    } else {
        $result = $conn->query("SELECT * FROM v_max_drawdown_by_system ORDER BY max_drawdown_pct ASC");
    }

    $drawdowns = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $drawdowns[] = $row;
        }
    }

    echo json_encode([
        'ok' => true,
        'drawdowns' => $drawdowns,
        'by' => $by,
        'count' => count($drawdowns)
    ]);
}

// ACTION: correlation - Cross-system correlation matrix
elseif ($action === 'correlation') {
    $result = $conn->query("SELECT * FROM v_system_correlation ORDER BY correlation DESC");

    $correlations = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $correlations[] = $row;
        }
    }

    echo json_encode([
        'ok' => true,
        'correlations' => $correlations,
        'count' => count($correlations)
    ]);
}

// ACTION: backtest_vs_live - Performance comparison
elseif ($action === 'backtest_vs_live') {
    $result = $conn->query("SELECT * FROM v_backtest_vs_live ORDER BY performance_degradation_pct DESC LIMIT 50");

    $comparisons = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $comparisons[] = $row;
        }
    }

    echo json_encode([
        'ok' => true,
        'comparisons' => $comparisons,
        'count' => count($comparisons)
    ]);
}

// ACTION: streaks - Win/loss streak analysis
elseif ($action === 'streaks') {
    $result = $conn->query("SELECT * FROM v_win_loss_streaks ORDER BY max_win_streak DESC LIMIT 50");

    $streaks = [];
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $streaks[] = $row;
        }
    }

    echo json_encode([
        'ok' => true,
        'streaks' => $streaks,
        'count' => count($streaks)
    ]);
} else {
    echo json_encode(['ok' => false, 'error' => 'Unknown action']);
}

$conn->close();
?>