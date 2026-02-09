<?php
/**
 * Learning Dashboard API — Aggregated Self-Learning Data
 * Pulls learning results from all 6 portfolio systems.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   overview        — Summary of all learning systems
 *   history         — Parameter change timeline for a system
 *   heatmap         — Grid search TP% vs SL% heatmap data
 *   is_improving    — Track whether learning is actually improving
 *
 * Usage:
 *   GET .../learning_dashboard.php?action=overview
 *   GET .../learning_dashboard.php?action=history&system=miracle_v3
 *   GET .../learning_dashboard.php?action=heatmap&system=miracle_v3&strategy=Gap+Up+Momentum
 *   GET .../learning_dashboard.php?action=is_improving
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'overview';
$response = array('ok' => true, 'action' => $action);

// ═══════════════════════════════════════════
// OVERVIEW — Summary of all learning systems
// ═══════════════════════════════════════════
if ($action === 'overview') {
    $systems = array();

    // 1. Stocks Portfolio v1 (learning.php -> algorithm_performance + audit_log)
    $sys = array('id' => 'stocks_v1', 'name' => 'Stock Portfolio Algorithms', 'page' => '/findstocks/portfolio2/stats/');
    $r = $conn->query("SELECT COUNT(*) as cnt FROM algorithm_performance");
    if ($r && $r->num_rows > 0) { $_tmp = $r->fetch_assoc(); $sys['algorithms_tracked'] = (int)$_tmp['cnt']; } else { $sys['algorithms_tracked'] = 0; }
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(created_at) as latest FROM audit_log WHERE action_type='learning'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sys['adjustments_made'] = (int)$row['cnt']; $sys['last_run'] = $row['latest']; }
    else { $sys['adjustments_made'] = 0; $sys['last_run'] = null; }
    // Best algorithm
    $r = $conn->query("SELECT algorithm_name, win_rate FROM algorithm_performance ORDER BY win_rate DESC LIMIT 1");
    $sys['best_algo'] = ($r && $r->num_rows > 0) ? $r->fetch_assoc() : null;
    $r = $conn->query("SELECT algorithm_name, win_rate FROM algorithm_performance WHERE win_rate > 0 ORDER BY win_rate ASC LIMIT 1");
    $sys['worst_algo'] = ($r && $r->num_rows > 0) ? $r->fetch_assoc() : null;
    $systems[] = $sys;

    // 2. Miracle v2 (learning2.php -> miracle_results2 + miracle_audit2)
    $sys = array('id' => 'miracle_v2', 'name' => 'DayTrades Miracle v2', 'page' => '/findstocks2_global/miracle.html');
    $r = $conn->query("SELECT COUNT(DISTINCT strategy_name) as cnt FROM miracle_picks2");
    if ($r && $r->num_rows > 0) { $_tmp = $r->fetch_assoc(); $sys['algorithms_tracked'] = (int)$_tmp['cnt']; } else { $sys['algorithms_tracked'] = 0; }
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(created_at) as latest FROM miracle_audit2 WHERE action_type='learning_adjust'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sys['adjustments_made'] = (int)$row['cnt']; $sys['last_run'] = $row['latest']; }
    else { $sys['adjustments_made'] = 0; $sys['last_run'] = null; }
    // Picks freshness — fall back to latest pick date if no learning runs
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(scan_date) as latest FROM miracle_picks2 WHERE entry_price > 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sys['total_picks'] = (int)$row['cnt']; $sys['latest_pick_date'] = $row['latest']; }
    else { $sys['total_picks'] = 0; $sys['latest_pick_date'] = null; }
    if (!$sys['last_run'] && $sys['latest_pick_date']) { $sys['last_run'] = $sys['latest_pick_date']; }
    $r = $conn->query("SELECT strategy_name, win_rate FROM miracle_results2 WHERE period='daily' ORDER BY win_rate DESC LIMIT 1");
    if (!$r || $r->num_rows === 0) { $r = $conn->query("SELECT strategy_name, win_rate FROM miracle_results2 WHERE win_rate > 0 ORDER BY win_rate DESC LIMIT 1"); }
    $sys['best_algo'] = ($r && $r->num_rows > 0) ? $r->fetch_assoc() : null;
    $systems[] = $sys;

    // 3. Miracle v3 (learning3.php -> miracle_learning3 + miracle_audit3)
    $sys = array('id' => 'miracle_v3', 'name' => 'DayTraders Miracle v3 (Claude)', 'page' => '/findstocks_global/miracle.html');
    $r = $conn->query("SELECT COUNT(DISTINCT strategy_name) as cnt FROM miracle_picks3");
    if ($r && $r->num_rows > 0) { $_tmp = $r->fetch_assoc(); $sys['algorithms_tracked'] = (int)$_tmp['cnt']; } else { $sys['algorithms_tracked'] = 0; }
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(created_at) as latest FROM miracle_learning3");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sys['adjustments_made'] = (int)$row['cnt']; $sys['last_run'] = $row['latest']; }
    else { $sys['adjustments_made'] = 0; $sys['last_run'] = null; }
    // Picks freshness — fall back to latest pick date if no learning runs
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(scan_date) as latest FROM miracle_picks3 WHERE entry_price > 0");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sys['total_picks'] = (int)$row['cnt']; $sys['latest_pick_date'] = $row['latest']; }
    else { $sys['total_picks'] = 0; $sys['latest_pick_date'] = null; }
    if (!$sys['last_run'] && $sys['latest_pick_date']) { $sys['last_run'] = $sys['latest_pick_date']; }
    $r = $conn->query("SELECT strategy_name, win_rate FROM miracle_results3 WHERE period='daily' ORDER BY win_rate DESC LIMIT 1");
    if (!$r || $r->num_rows === 0) { $r = $conn->query("SELECT strategy_name, win_rate FROM miracle_results3 WHERE win_rate > 0 ORDER BY win_rate DESC LIMIT 1"); }
    $sys['best_algo'] = ($r && $r->num_rows > 0) ? $r->fetch_assoc() : null;
    $systems[] = $sys;

    // 4. Mutual Funds v2
    $sys = array('id' => 'mutualfunds', 'name' => 'Mutual Fund Algorithms', 'page' => '/findmutualfunds2/portfolio2/');
    $r = $conn->query("SELECT COUNT(DISTINCT algorithm_name) as cnt FROM mf2_fund_picks");
    if ($r && $r->num_rows > 0) { $_tmp = $r->fetch_assoc(); $sys['algorithms_tracked'] = (int)$_tmp['cnt']; } else { $sys['algorithms_tracked'] = 0; }
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(created_at) as latest FROM mf2_audit_log WHERE action_type='learning'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sys['adjustments_made'] = (int)$row['cnt']; $sys['last_run'] = $row['latest']; }
    else { $sys['adjustments_made'] = 0; $sys['last_run'] = null; }
    $systems[] = $sys;

    // 5. Forex
    $sys = array('id' => 'forex', 'name' => 'Forex Algorithms', 'page' => '/findforex2/portfolio/');
    $r = $conn->query("SELECT COUNT(DISTINCT algorithm_name) as cnt FROM fxp_pair_picks");
    if ($r && $r->num_rows > 0) { $_tmp = $r->fetch_assoc(); $sys['algorithms_tracked'] = (int)$_tmp['cnt']; } else { $sys['algorithms_tracked'] = 0; }
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(created_at) as latest FROM fxp_audit_log WHERE action_type='learning'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sys['adjustments_made'] = (int)$row['cnt']; $sys['last_run'] = $row['latest']; }
    else { $sys['adjustments_made'] = 0; $sys['last_run'] = null; }
    $systems[] = $sys;

    // 6. Crypto
    $sys = array('id' => 'crypto', 'name' => 'Crypto Algorithms', 'page' => '/findcryptopairs/portfolio/');
    $r = $conn->query("SELECT COUNT(DISTINCT algorithm_name) as cnt FROM cr_pair_picks");
    if ($r && $r->num_rows > 0) { $_tmp = $r->fetch_assoc(); $sys['algorithms_tracked'] = (int)$_tmp['cnt']; } else { $sys['algorithms_tracked'] = 0; }
    $r = $conn->query("SELECT COUNT(*) as cnt, MAX(created_at) as latest FROM cr_audit_log WHERE action_type='learning'");
    if ($r && $r->num_rows > 0) { $row = $r->fetch_assoc(); $sys['adjustments_made'] = (int)$row['cnt']; $sys['last_run'] = $row['latest']; }
    else { $sys['adjustments_made'] = 0; $sys['last_run'] = null; }
    $systems[] = $sys;

    $response['systems'] = $systems;
    $response['total_systems'] = count($systems);
    $total_adjustments = 0;
    foreach ($systems as $s) $total_adjustments += $s['adjustments_made'];
    $response['total_adjustments'] = $total_adjustments;
    $response['generated_at'] = date('Y-m-d H:i:s');
    echo json_encode($response);

// ═══════════════════════════════════════════
// HISTORY — Parameter change timeline
// ═══════════════════════════════════════════
} elseif ($action === 'history') {
    $system = isset($_GET['system']) ? trim($_GET['system']) : 'miracle_v3';
    $limit = isset($_GET['limit']) ? max(1, min(200, (int)$_GET['limit'])) : 50;
    $response['system'] = $system;
    $history = array();

    if ($system === 'miracle_v3') {
        // miracle_learning3 has explicit old/new values
        $r = $conn->query("SELECT * FROM miracle_learning3 ORDER BY created_at DESC LIMIT $limit");
        if ($r) { while ($row = $r->fetch_assoc()) $history[] = $row; }
    } elseif ($system === 'miracle_v2') {
        // miracle_audit2 with learning actions
        $r = $conn->query("SELECT * FROM miracle_audit2 WHERE action_type LIKE '%learn%' ORDER BY created_at DESC LIMIT $limit");
        if ($r) { while ($row = $r->fetch_assoc()) $history[] = $row; }
    } elseif ($system === 'stocks_v1') {
        $r = $conn->query("SELECT * FROM audit_log WHERE action_type='learning' ORDER BY created_at DESC LIMIT $limit");
        if ($r) { while ($row = $r->fetch_assoc()) $history[] = $row; }
    } elseif ($system === 'mutualfunds') {
        $r = $conn->query("SELECT * FROM mf2_audit_log WHERE action_type='learning' ORDER BY created_at DESC LIMIT $limit");
        if ($r) { while ($row = $r->fetch_assoc()) $history[] = $row; }
    } elseif ($system === 'forex') {
        $r = $conn->query("SELECT * FROM fxp_audit_log WHERE action_type='learning' ORDER BY created_at DESC LIMIT $limit");
        if ($r) { while ($row = $r->fetch_assoc()) $history[] = $row; }
    } elseif ($system === 'crypto') {
        $r = $conn->query("SELECT * FROM cr_audit_log WHERE action_type='learning' ORDER BY created_at DESC LIMIT $limit");
        if ($r) { while ($row = $r->fetch_assoc()) $history[] = $row; }
    }

    $response['history'] = $history;
    $response['count'] = count($history);
    echo json_encode($response);

// ═══════════════════════════════════════════
// HEATMAP — Grid search TP% vs SL% visualization
// ═══════════════════════════════════════════
} elseif ($action === 'heatmap') {
    $system = isset($_GET['system']) ? trim($_GET['system']) : 'stocks_v1';
    $strategy = isset($_GET['strategy']) ? trim($_GET['strategy']) : '';
    $response['system'] = $system;
    $response['strategy'] = $strategy;

    $heatmap = array();

    if ($system === 'stocks_v1') {
        // Use backtest_results which stores different TP/SL combinations
        $safe_strat = $conn->real_escape_string($strategy);
        $where = ($strategy !== '') ? "AND (algorithm_filter LIKE '%$safe_strat%' OR strategy_type LIKE '%$safe_strat%')" : '';
        $r = $conn->query("SELECT params_json, total_return_pct, win_rate, sharpe_ratio
                           FROM backtest_results WHERE total_trades > 0 $where ORDER BY total_return_pct DESC LIMIT 500");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $params = json_decode($row['params_json'], true);
                if (!$params) continue;
                $tp = isset($params['take_profit']) ? (float)$params['take_profit'] : 0;
                $sl = isset($params['stop_loss']) ? (float)$params['stop_loss'] : 0;
                if ($tp <= 0 || $sl <= 0) continue;
                $heatmap[] = array(
                    'tp_pct' => $tp,
                    'sl_pct' => $sl,
                    'return_pct' => (float)$row['total_return_pct'],
                    'win_rate' => (float)$row['win_rate'],
                    'sharpe' => (float)$row['sharpe_ratio']
                );
            }
        }
    } elseif ($system === 'miracle_v3') {
        // Try miracle_results3 or the learning table
        $r = $conn->query("SELECT strategy_name, win_rate, avg_gain_pct, avg_loss_pct, total_picks
                           FROM miracle_results3 WHERE total_picks > 0 ORDER BY win_rate DESC LIMIT 200");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $heatmap[] = array(
                    'strategy' => $row['strategy_name'],
                    'win_rate' => (float)$row['win_rate'],
                    'avg_gain' => (float)$row['avg_gain_pct'],
                    'avg_loss' => (float)$row['avg_loss_pct'],
                    'picks' => (int)$row['total_picks']
                );
            }
        }
    }

    $response['heatmap'] = $heatmap;
    $response['data_points'] = count($heatmap);
    echo json_encode($response);

// ═══════════════════════════════════════════
// IS IMPROVING — Compare old vs new performance
// ═══════════════════════════════════════════
} elseif ($action === 'is_improving') {
    $improvements = array();

    // GitHub workflow info per system
    $github_info = array(
        'miracle_v3' => array('workflow' => 'daily-stock-refresh.yml', 'job' => 'Daily Stock Refresh'),
        'miracle_v2' => array('workflow' => 'daily-stock-refresh.yml', 'job' => 'Daily Stock Refresh'),
        'stocks_v1'  => array('workflow' => 'refresh-stocks-portfolio.yml', 'job' => 'Refresh Stocks & Portfolio')
    );

    // Miracle v3: compare first 30 resolved trades vs last 30 resolved trades
    $first_30 = array('wins' => 0, 'total' => 0);
    $last_30 = array('wins' => 0, 'total' => 0);

    // Total picks (including unresolved) for context
    $total_picks_v3 = 0;
    $r = $conn->query("SELECT COUNT(*) as cnt FROM miracle_picks3 WHERE entry_price > 0");
    if ($r && $row = $r->fetch_assoc()) $total_picks_v3 = (int)$row['cnt'];

    $r = $conn->query("SELECT outcome FROM miracle_picks3 WHERE outcome IN ('won','lost') ORDER BY scan_date ASC LIMIT 100");
    if ($r) {
        $all = array();
        while ($row = $r->fetch_assoc()) $all[] = $row['outcome'];
        $cnt = count($all);
        for ($i = 0; $i < min(30, $cnt); $i++) { $first_30['total']++; if ($all[$i] === 'won') $first_30['wins']++; }
        for ($i = max(0, $cnt - 30); $i < $cnt; $i++) { $last_30['total']++; if ($all[$i] === 'won') $last_30['wins']++; }
    }

    // Last run date for miracle v3
    $last_run_v3 = null;
    $r = $conn->query("SELECT MAX(created_at) as latest FROM miracle_learning3");
    if ($r && $row = $r->fetch_assoc()) $last_run_v3 = $row['latest'];
    if (!$last_run_v3) {
        $r = $conn->query("SELECT MAX(scan_date) as latest FROM miracle_picks3 WHERE entry_price > 0");
        if ($r && $row = $r->fetch_assoc()) $last_run_v3 = $row['latest'];
    }

    $wr_first = ($first_30['total'] > 0) ? round($first_30['wins'] / $first_30['total'] * 100, 2) : 0;
    $wr_last = ($last_30['total'] > 0) ? round($last_30['wins'] / $last_30['total'] * 100, 2) : 0;
    $improvements[] = array(
        'system' => 'miracle_v3',
        'name' => 'DayTraders Miracle v3',
        'first_30_win_rate' => $wr_first,
        'first_30_trades' => $first_30['total'],
        'last_30_win_rate' => $wr_last,
        'last_30_trades' => $last_30['total'],
        'total_picks' => $total_picks_v3,
        'improvement_pct' => round($wr_last - $wr_first, 2),
        'is_improving' => ($wr_last > $wr_first),
        'last_run' => $last_run_v3,
        'github' => $github_info['miracle_v3']
    );

    // Miracle v2
    $first_30 = array('wins' => 0, 'total' => 0);
    $last_30 = array('wins' => 0, 'total' => 0);

    $total_picks_v2 = 0;
    $r = $conn->query("SELECT COUNT(*) as cnt FROM miracle_picks2 WHERE entry_price > 0");
    if ($r && $row = $r->fetch_assoc()) $total_picks_v2 = (int)$row['cnt'];

    $r = $conn->query("SELECT outcome FROM miracle_picks2 WHERE outcome IN ('won','lost') ORDER BY scan_date ASC LIMIT 100");
    if ($r) {
        $all = array();
        while ($row = $r->fetch_assoc()) $all[] = $row['outcome'];
        $cnt = count($all);
        for ($i = 0; $i < min(30, $cnt); $i++) { $first_30['total']++; if ($all[$i] === 'won') $first_30['wins']++; }
        for ($i = max(0, $cnt - 30); $i < $cnt; $i++) { $last_30['total']++; if ($all[$i] === 'won') $last_30['wins']++; }
    }

    $last_run_v2 = null;
    $r = $conn->query("SELECT MAX(created_at) as latest FROM miracle_audit2 WHERE action_type='learning_adjust'");
    if ($r && $row = $r->fetch_assoc()) $last_run_v2 = $row['latest'];
    if (!$last_run_v2) {
        $r = $conn->query("SELECT MAX(scan_date) as latest FROM miracle_picks2 WHERE entry_price > 0");
        if ($r && $row = $r->fetch_assoc()) $last_run_v2 = $row['latest'];
    }

    $wr_first = ($first_30['total'] > 0) ? round($first_30['wins'] / $first_30['total'] * 100, 2) : 0;
    $wr_last = ($last_30['total'] > 0) ? round($last_30['wins'] / $last_30['total'] * 100, 2) : 0;
    $improvements[] = array(
        'system' => 'miracle_v2',
        'name' => 'DayTrades Miracle v2',
        'first_30_win_rate' => $wr_first,
        'first_30_trades' => $first_30['total'],
        'last_30_win_rate' => $wr_last,
        'last_30_trades' => $last_30['total'],
        'total_picks' => $total_picks_v2,
        'improvement_pct' => round($wr_last - $wr_first, 2),
        'is_improving' => ($wr_last > $wr_first),
        'last_run' => $last_run_v2,
        'github' => $github_info['miracle_v2']
    );

    // Stock portfolio — use backtest_results chronological
    $r = $conn->query("SELECT total_return_pct, win_rate, created_at FROM backtest_results ORDER BY created_at ASC");
    if ($r && $r->num_rows > 0) {
        $all = array();
        while ($row = $r->fetch_assoc()) $all[] = $row;
        $cnt = count($all);
        $first_avg = 0; $last_avg = 0;
        $fcount = min(10, $cnt); $lcount = min(10, $cnt);
        for ($i = 0; $i < $fcount; $i++) $first_avg += (float)$all[$i]['win_rate'];
        for ($i = max(0, $cnt - $lcount); $i < $cnt; $i++) $last_avg += (float)$all[$i]['win_rate'];
        $first_avg = ($fcount > 0) ? round($first_avg / $fcount, 2) : 0;
        $last_avg = ($lcount > 0) ? round($last_avg / $lcount, 2) : 0;

        $last_run_stocks = null;
        if ($cnt > 0) $last_run_stocks = $all[$cnt - 1]['created_at'];

        $improvements[] = array(
            'system' => 'stocks_v1',
            'name' => 'Stock Portfolio Algorithms',
            'first_backtests_win_rate' => $first_avg,
            'last_backtests_win_rate' => $last_avg,
            'improvement_pct' => round($last_avg - $first_avg, 2),
            'is_improving' => ($last_avg > $first_avg),
            'total_backtests' => $cnt,
            'last_run' => $last_run_stocks,
            'github' => $github_info['stocks_v1']
        );
    }

    $response['improvements'] = $improvements;
    $any_improving = false;
    foreach ($improvements as $imp) { if (isset($imp['is_improving']) && $imp['is_improving']) $any_improving = true; }
    $response['overall_improving'] = $any_improving;
    $response['generated_at'] = date('Y-m-d H:i:s');
    echo json_encode($response);

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action. Use: overview, history, heatmap, is_improving';
    echo json_encode($response);
}

$conn->close();
?>
