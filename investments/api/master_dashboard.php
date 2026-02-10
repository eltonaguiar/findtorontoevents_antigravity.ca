<?php
/**
 * Master Dashboard API - Unified Prediction Systems Performance
 * Aggregates stats from all 7 prediction systems
 * 
 * Actions:
 *   overview    - High-level stats across all systems
 *   by_system   - Detailed breakdown by asset class
 *   top_algos   - Best performing algorithms across all systems
 *   recent      - Recent picks from all systems (last 24h)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// Database connections for each system
$connections = [];

// Crypto Scanner
try {
    $connections['crypto'] = new mysqli('mysql.50webs.com', 'ejaguiar1_crypto', 'testing123', 'ejaguiar1_crypto');
    if ($connections['crypto']->connect_error)
        $connections['crypto'] = null;
} catch (Exception $e) {
    $connections['crypto'] = null;
}

// Meme Scanner
try {
    $connections['meme'] = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
    if ($connections['meme']->connect_error)
        $connections['meme'] = null;
} catch (Exception $e) {
    $connections['meme'] = null;
}

// Note: You'll need to update these with your actual credentials
// For now, using placeholder connections
$connections['sports'] = null;  // Live monitor DB
$connections['stocks'] = null;  // Main stocks DB
$connections['forex'] = null;   // Forex DB
$connections['mutual_funds'] = null; // Mutual funds DB

$action = isset($_GET['action']) ? $_GET['action'] : 'overview';

// ═══════════════════════════════════════════════════════════════
// OVERVIEW - High-level stats
// ═══════════════════════════════════════════════════════════════
if ($action === 'overview') {
    $systems = [];

    // Crypto Scanner
    if ($connections['crypto']) {
        $crypto_stats = get_crypto_stats($connections['crypto']);
        $systems[] = $crypto_stats;
    }

    // Meme Scanner
    if ($connections['meme']) {
        $meme_stats = get_meme_stats($connections['meme']);
        $systems[] = $meme_stats;
    }

    // Sports (placeholder - needs actual connection)
    $systems[] = [
        'name' => 'Sports Betting',
        'asset_class' => 'sports',
        'status' => 'needs_connection',
        'signals_30d' => 0,
        'win_rate' => 0,
        'avg_pnl' => 0
    ];

    // Stocks (placeholder)
    $systems[] = [
        'name' => 'Stock Intelligence',
        'asset_class' => 'stocks',
        'status' => 'needs_connection',
        'signals_30d' => 0,
        'win_rate' => 0,
        'avg_pnl' => 0
    ];

    // Calculate overall stats
    $total_signals = 0;
    $total_wins = 0;
    $total_trades = 0;
    $best_system = null;
    $best_win_rate = 0;

    foreach ($systems as $sys) {
        if ($sys['status'] === 'active') {
            $total_signals += $sys['signals_30d'];
            if (isset($sys['wins_30d'])) {
                $total_wins += $sys['wins_30d'];
                $total_trades += $sys['trades_30d'];
            }
            if ($sys['win_rate'] > $best_win_rate) {
                $best_win_rate = $sys['win_rate'];
                $best_system = $sys['name'];
            }
        }
    }

    $overall_win_rate = ($total_trades > 0) ? round(($total_wins / $total_trades) * 100, 1) : 0;

    echo json_encode([
        'ok' => true,
        'generated_at' => date('Y-m-d H:i:s'),
        'overall' => [
            'total_signals_30d' => $total_signals,
            'overall_win_rate' => $overall_win_rate,
            'best_system' => $best_system,
            'best_win_rate' => $best_win_rate,
            'active_systems' => count(array_filter($systems, function ($s) {
                return $s['status'] === 'active'; })),
            'total_systems' => count($systems)
        ],
        'systems' => $systems
    ]);
}

// ═══════════════════════════════════════════════════════════════
// Helper Functions
// ═══════════════════════════════════════════════════════════════

function get_crypto_stats($conn)
{
    $stats = [
        'name' => 'Crypto Winner Scanner',
        'asset_class' => 'crypto',
        'status' => 'active'
    ];

    // Total signals in last 30 days
    $result = $conn->query("SELECT COUNT(*) as cnt FROM cw_winners WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)");
    $stats['signals_30d'] = ($result) ? $result->fetch_assoc()['cnt'] : 0;

    // Win rate (resolved trades only)
    $result = $conn->query("SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN outcome IN ('win', 'partial_win') THEN 1 ELSE 0 END) as wins,
        AVG(pnl_pct) as avg_pnl
        FROM cw_winners 
        WHERE outcome IS NOT NULL 
        AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)");

    if ($result && $row = $result->fetch_assoc()) {
        $stats['trades_30d'] = (int) $row['total'];
        $stats['wins_30d'] = (int) $row['wins'];
        $stats['win_rate'] = ($row['total'] > 0) ? round(($row['wins'] / $row['total']) * 100, 1) : 0;
        $stats['avg_pnl'] = round((float) $row['avg_pnl'], 2);
    } else {
        $stats['trades_30d'] = 0;
        $stats['wins_30d'] = 0;
        $stats['win_rate'] = 0;
        $stats['avg_pnl'] = 0;
    }

    // Last update
    $result = $conn->query("SELECT MAX(created_at) as last_update FROM cw_winners");
    if ($result && $row = $result->fetch_assoc()) {
        $stats['last_update'] = $row['last_update'];
        $hours_ago = (time() - strtotime($row['last_update'])) / 3600;
        $stats['hours_since_update'] = round($hours_ago, 1);
        $stats['is_stale'] = ($hours_ago > 24);
    }

    return $stats;
}

function get_meme_stats($conn)
{
    $stats = [
        'name' => 'Meme Coin Scanner',
        'asset_class' => 'meme',
        'status' => 'active'
    ];

    // Total signals in last 30 days
    $result = $conn->query("SELECT COUNT(*) as cnt FROM mc_winners WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)");
    $stats['signals_30d'] = ($result) ? $result->fetch_assoc()['cnt'] : 0;

    // Win rate
    $result = $conn->query("SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN outcome IN ('win', 'partial_win') THEN 1 ELSE 0 END) as wins,
        AVG(pnl_pct) as avg_pnl
        FROM mc_winners 
        WHERE outcome IS NOT NULL 
        AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)");

    if ($result && $row = $result->fetch_assoc()) {
        $stats['trades_30d'] = (int) $row['total'];
        $stats['wins_30d'] = (int) $row['wins'];
        $stats['win_rate'] = ($row['total'] > 0) ? round(($row['wins'] / $row['total']) * 100, 1) : 0;
        $stats['avg_pnl'] = round((float) $row['avg_pnl'], 2);
    } else {
        $stats['trades_30d'] = 0;
        $stats['wins_30d'] = 0;
        $stats['win_rate'] = 0;
        $stats['avg_pnl'] = 0;
    }

    // Last update
    $result = $conn->query("SELECT MAX(created_at) as last_update FROM mc_winners");
    if ($result && $row = $result->fetch_assoc()) {
        $stats['last_update'] = $row['last_update'];
        $hours_ago = (time() - strtotime($row['last_update'])) / 3600;
        $stats['hours_since_update'] = round($hours_ago, 1);
        $stats['is_stale'] = ($hours_ago > 24);
    }

    return $stats;
}

// Close all connections
foreach ($connections as $conn) {
    if ($conn)
        $conn->close();
}
