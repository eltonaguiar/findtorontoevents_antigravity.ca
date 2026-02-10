<?php
/**
 * GOLDMINE_CURSOR — Track Record API
 * Public read-only endpoint for the verified prediction ledger.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=summary          — Overall stats across all asset classes
 *   ?action=predictions       — Paginated prediction list (filterable)
 *   ?action=equity_curve      — Cumulative P/L over time
 *   ?action=algo_ranking      — Algorithms ranked by profit factor
 *   ?action=asset_breakdown   — Performance by asset class
 *   ?action=hidden_winners    — Algorithms flagged as hidden winners
 *   ?action=needs_review      — Algorithms flagged for review
 *   ?action=regime_performance— Performance segmented by market regime
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'summary';

$response = array('ok' => true, 'action' => $action);

// ─────────────────────────────
//  Helper: safe int
// ─────────────────────────────
function gc_safe_int($val, $default) {
    $v = isset($val) ? intval($val) : $default;
    return ($v > 0) ? $v : $default;
}

// ═══════════════════════════════════════════
//  SUMMARY — Overall system performance
// ═══════════════════════════════════════════
if ($action === 'summary') {

    // Total predictions
    $r = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status='lost' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_count,
        SUM(CASE WHEN status='expired' THEN 1 ELSE 0 END) as expired,
        AVG(CASE WHEN status='won' THEN pnl_pct ELSE NULL END) as avg_win,
        AVG(CASE WHEN status='lost' THEN pnl_pct ELSE NULL END) as avg_loss,
        AVG(CASE WHEN status IN ('won','lost') THEN pnl_pct ELSE NULL END) as avg_return,
        SUM(CASE WHEN status IN ('won','lost') THEN pnl_pct ELSE 0 END) as total_pnl,
        MIN(logged_at) as first_prediction,
        MAX(logged_at) as last_prediction,
        COUNT(DISTINCT algorithm) as unique_algos,
        COUNT(DISTINCT asset_class) as unique_assets
    FROM goldmine_cursor_predictions");

    if ($r && $row = $r->fetch_assoc()) {
        $resolved = intval($row['wins']) + intval($row['losses']);
        $win_rate = ($resolved > 0) ? round(floatval($row['wins']) / $resolved * 100, 2) : 0;

        $gross_profit = 0;
        $gross_loss = 0;
        $r2 = $conn->query("SELECT
            SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) as gp,
            SUM(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) ELSE 0 END) as gl
            FROM goldmine_cursor_predictions WHERE status IN ('won','lost')");
        if ($r2 && $r2row = $r2->fetch_assoc()) {
            $gross_profit = floatval($r2row['gp']);
            $gross_loss = floatval($r2row['gl']);
        }

        $profit_factor = ($gross_loss > 0) ? round($gross_profit / $gross_loss, 2) : 0;
        $expectancy = ($resolved > 0) ? round(floatval($row['total_pnl']) / $resolved, 4) : 0;

        $response['summary'] = array(
            'total_predictions' => intval($row['total']),
            'open' => intval($row['open_count']),
            'resolved' => $resolved,
            'wins' => intval($row['wins']),
            'losses' => intval($row['losses']),
            'expired' => intval($row['expired']),
            'win_rate' => $win_rate,
            'avg_win_pct' => round(floatval($row['avg_win']), 2),
            'avg_loss_pct' => round(floatval($row['avg_loss']), 2),
            'avg_return_pct' => round(floatval($row['avg_return']), 2),
            'total_pnl_pct' => round(floatval($row['total_pnl']), 2),
            'profit_factor' => $profit_factor,
            'expectancy' => $expectancy,
            'unique_algorithms' => intval($row['unique_algos']),
            'unique_asset_classes' => intval($row['unique_assets']),
            'first_prediction' => $row['first_prediction'],
            'last_prediction' => $row['last_prediction']
        );
    } else {
        $response['summary'] = array('total_predictions' => 0, 'note' => 'No data yet. Run harvest to ingest predictions.');
    }

// ═══════════════════════════════════════════
//  PREDICTIONS — Paginated, filterable list
// ═══════════════════════════════════════════
} elseif ($action === 'predictions') {

    $page = gc_safe_int(isset($_GET['page']) ? $_GET['page'] : 1, 1);
    $per_page = gc_safe_int(isset($_GET['per_page']) ? $_GET['per_page'] : 50, 50);
    if ($per_page > 200) { $per_page = 200; }
    $offset = ($page - 1) * $per_page;

    $where = array('1=1');
    $asset = isset($_GET['asset_class']) ? $conn->real_escape_string(trim($_GET['asset_class'])) : '';
    if ($asset !== '') { $where[] = "asset_class = '$asset'"; }

    $algo = isset($_GET['algorithm']) ? $conn->real_escape_string(trim($_GET['algorithm'])) : '';
    if ($algo !== '') { $where[] = "algorithm = '$algo'"; }

    $status_f = isset($_GET['status']) ? $conn->real_escape_string(trim($_GET['status'])) : '';
    if ($status_f !== '') { $where[] = "status = '$status_f'"; }

    $w = implode(' AND ', $where);

    // Count
    $r = $conn->query("SELECT COUNT(*) as cnt FROM goldmine_cursor_predictions WHERE $w");
    $total = ($r && $row = $r->fetch_assoc()) ? intval($row['cnt']) : 0;

    // Fetch page
    $r = $conn->query("SELECT * FROM goldmine_cursor_predictions WHERE $w ORDER BY logged_at DESC LIMIT $offset, $per_page");
    $picks = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $picks[] = $row;
        }
    }

    $response['total'] = $total;
    $response['page'] = $page;
    $response['per_page'] = $per_page;
    $response['predictions'] = $picks;

// ═══════════════════════════════════════════
//  EQUITY CURVE — Cumulative P/L over time
// ═══════════════════════════════════════════
} elseif ($action === 'equity_curve') {

    $asset = isset($_GET['asset_class']) ? $conn->real_escape_string(trim($_GET['asset_class'])) : '';
    $where_asset = ($asset !== '') ? "AND asset_class = '$asset'" : '';

    $r = $conn->query("SELECT DATE(resolved_at) as rdate,
        SUM(pnl_pct) as daily_pnl,
        COUNT(*) as trades
        FROM goldmine_cursor_predictions
        WHERE status IN ('won','lost') $where_asset
        GROUP BY DATE(resolved_at)
        ORDER BY rdate ASC");

    $curve = array();
    $cumulative = 0;
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $cumulative = $cumulative + floatval($row['daily_pnl']);
            $curve[] = array(
                'date' => $row['rdate'],
                'daily_pnl' => round(floatval($row['daily_pnl']), 4),
                'cumulative_pnl' => round($cumulative, 4),
                'trades' => intval($row['trades'])
            );
        }
    }
    $response['curve'] = $curve;

// ═══════════════════════════════════════════
//  ALGO RANKING — By profit factor
// ═══════════════════════════════════════════
} elseif ($action === 'algo_ranking') {

    $r = $conn->query("SELECT algorithm, asset_class,
        COUNT(*) as total,
        SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status='lost' THEN 1 ELSE 0 END) as losses,
        AVG(CASE WHEN status='won' THEN pnl_pct ELSE NULL END) as avg_win,
        AVG(CASE WHEN status='lost' THEN pnl_pct ELSE NULL END) as avg_loss,
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) as gross_profit,
        SUM(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) ELSE 0 END) as gross_loss,
        SUM(pnl_pct) as total_pnl,
        AVG(benchmark_return_pct) as avg_benchmark
        FROM goldmine_cursor_predictions
        WHERE status IN ('won','lost')
        GROUP BY algorithm, asset_class
        HAVING (wins + losses) >= 5
        ORDER BY gross_profit / GREATEST(gross_loss, 0.01) DESC");

    $ranking = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $resolved = intval($row['wins']) + intval($row['losses']);
            $gl = floatval($row['gross_loss']);
            $gp = floatval($row['gross_profit']);
            $pf = ($gl > 0) ? round($gp / $gl, 2) : 999;
            $wr = ($resolved > 0) ? round(floatval($row['wins']) / $resolved * 100, 2) : 0;
            $exp = ($resolved > 0) ? round(floatval($row['total_pnl']) / $resolved, 4) : 0;
            $alpha = round(floatval($row['total_pnl']) - floatval($row['avg_benchmark']) * $resolved, 2);

            $verdict = 'neutral';
            if ($wr > 55 && $pf > 1.5) { $verdict = 'hidden_winner'; }
            elseif ($wr > 50 && $pf > 1.2) { $verdict = 'strong'; }
            elseif ($wr < 40 || $pf < 0.8) { $verdict = 'needs_review'; }

            $ranking[] = array(
                'algorithm' => $row['algorithm'],
                'asset_class' => $row['asset_class'],
                'total_resolved' => $resolved,
                'wins' => intval($row['wins']),
                'losses' => intval($row['losses']),
                'win_rate' => $wr,
                'avg_win_pct' => round(floatval($row['avg_win']), 2),
                'avg_loss_pct' => round(floatval($row['avg_loss']), 2),
                'profit_factor' => $pf,
                'expectancy' => $exp,
                'total_pnl_pct' => round(floatval($row['total_pnl']), 2),
                'alpha_vs_benchmark' => $alpha,
                'verdict' => $verdict
            );
        }
    }
    $response['ranking'] = $ranking;

// ═══════════════════════════════════════════
//  HIDDEN WINNERS
// ═══════════════════════════════════════════
} elseif ($action === 'hidden_winners') {

    $r = $conn->query("SELECT algorithm, asset_class, verdict, win_rate, profit_factor, expectancy, alpha_pct, total_picks, wins, losses
        FROM goldmine_cursor_algo_scorecard
        WHERE verdict = 'hidden_winner'
        ORDER BY profit_factor DESC");

    $winners = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) { $winners[] = $row; }
    }
    $response['hidden_winners'] = $winners;

// ═══════════════════════════════════════════
//  NEEDS REVIEW
// ═══════════════════════════════════════════
} elseif ($action === 'needs_review') {

    $r = $conn->query("SELECT algorithm, asset_class, verdict, win_rate, profit_factor, expectancy, alpha_pct, total_picks, wins, losses
        FROM goldmine_cursor_algo_scorecard
        WHERE verdict = 'needs_review'
        ORDER BY profit_factor ASC");

    $review = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) { $review[] = $row; }
    }
    $response['needs_review'] = $review;

// ═══════════════════════════════════════════
//  ASSET BREAKDOWN
// ═══════════════════════════════════════════
} elseif ($action === 'asset_breakdown') {

    $r = $conn->query("SELECT asset_class,
        COUNT(*) as total,
        SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status='lost' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_count,
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) as gross_profit,
        SUM(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) ELSE 0 END) as gross_loss,
        SUM(pnl_pct) as total_pnl
        FROM goldmine_cursor_predictions
        GROUP BY asset_class
        ORDER BY total DESC");

    $breakdown = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $resolved = intval($row['wins']) + intval($row['losses']);
            $gl = floatval($row['gross_loss']);
            $gp = floatval($row['gross_profit']);
            $row['win_rate'] = ($resolved > 0) ? round(floatval($row['wins']) / $resolved * 100, 2) : 0;
            $row['profit_factor'] = ($gl > 0) ? round($gp / $gl, 2) : 0;
            $row['resolved'] = $resolved;
            $breakdown[] = $row;
        }
    }
    $response['breakdown'] = $breakdown;

// ═══════════════════════════════════════════
//  REGIME PERFORMANCE
// ═══════════════════════════════════════════
} elseif ($action === 'regime_performance') {

    $r = $conn->query("SELECT market_regime,
        COUNT(*) as total,
        SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN status='lost' THEN 1 ELSE 0 END) as losses,
        SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) as gross_profit,
        SUM(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) ELSE 0 END) as gross_loss,
        SUM(pnl_pct) as total_pnl
        FROM goldmine_cursor_predictions
        WHERE status IN ('won','lost')
        GROUP BY market_regime
        ORDER BY total DESC");

    $regimes = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $resolved = intval($row['wins']) + intval($row['losses']);
            $gl = floatval($row['gross_loss']);
            $gp = floatval($row['gross_profit']);
            $row['win_rate'] = ($resolved > 0) ? round(floatval($row['wins']) / $resolved * 100, 2) : 0;
            $row['profit_factor'] = ($gl > 0) ? round($gp / $gl, 2) : 0;
            $regimes[] = $row;
        }
    }
    $response['regimes'] = $regimes;

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action: ' . $action;
}

$conn->close();
echo json_encode($response);
?>
