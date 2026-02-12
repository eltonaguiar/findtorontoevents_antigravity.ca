<?php
/**
 * ml_intelligence.php — World-class ML tracking and status API
 *
 * Actions:
 *   schema     — Create all ML tables
 *   status     — Per asset class ML readiness status
 *   refresh    — Recalculate ML status from live trade data
 *   evolution  — Parameter evolution timeline per algorithm
 *   gaps       — Identify missing ML capabilities per asset class
 *   bridge     — Show daily picks bridge status (backtested->live overlap)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/ml_intelligence_schema.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'status';
$asset  = isset($_GET['asset'])  ? strtoupper($conn->real_escape_string($_GET['asset'])) : null;

// ─── SCHEMA ─────────────────────────────────────────────────────────────────
if ($action === 'schema') {
    _ml_ensure_schema($conn);
    echo json_encode(array('ok' => true, 'action' => 'schema', 'message' => 'ML intelligence tables created'));
    exit;
}

// ─── REFRESH — Recalculate ML status from live trading data ─────────────────
if ($action === 'refresh') {
    _ml_ensure_schema($conn);

    // Gather all algorithms with closed trades from lm_trades
    $sql = "SELECT algorithm_name, asset_class,
                   COUNT(*) as closed_trades,
                   SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
                   AVG(realized_pct) as avg_return,
                   SUM(realized_pnl_usd) as total_pnl,
                   AVG(target_tp_pct) as avg_tp,
                   AVG(target_sl_pct) as avg_sl,
                   AVG(max_hold_hours) as avg_hold
            FROM lm_trades
            WHERE status = 'closed' AND algorithm_name != ''
            GROUP BY algorithm_name, asset_class";
    $result = $conn->query($sql);

    $updated = 0;
    $now = date('Y-m-d H:i:s');

    if ($result && $result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $algo  = $conn->real_escape_string($row['algorithm_name']);
            $ac    = $conn->real_escape_string($row['asset_class']);
            $ct    = intval($row['closed_trades']);
            $wr    = $ct > 0 ? round(intval($row['wins']) / $ct * 100, 2) : 0;
            $ready = $ct >= 20 ? 1 : 0;
            $pf    = 0;
            $pnl   = round(floatval($row['total_pnl']), 2);
            $tp    = round(floatval($row['avg_tp']), 2);
            $sl    = round(floatval($row['avg_sl']), 2);
            $hold  = intval($row['avg_hold']);

            // Calculate profit factor
            $pf_sql = "SELECT
                        SUM(CASE WHEN realized_pnl_usd > 0 THEN realized_pnl_usd ELSE 0 END) as gross_wins,
                        ABS(SUM(CASE WHEN realized_pnl_usd < 0 THEN realized_pnl_usd ELSE 0 END)) as gross_losses
                       FROM lm_trades WHERE status='closed' AND algorithm_name='".$algo."' AND asset_class='".$ac."'";
            $pf_r = $conn->query($pf_sql);
            if ($pf_r && $pf_row = $pf_r->fetch_assoc()) {
                $gl = floatval($pf_row['gross_losses']);
                $pf = $gl > 0 ? round(floatval($pf_row['gross_wins']) / $gl, 3) : 0;
            }

            $status = 'collecting_data';
            $reason = 'Need ' . (20 - $ct) . ' more trades for grid search optimization';
            if ($ct >= 20) {
                $status = 'ready';
                $reason = 'Sufficient data for grid search. Awaiting optimization run.';
            }
            if ($ct >= 20 && $wr >= 55) {
                $status = 'performing';
                $reason = 'Algorithm is profitable with learned parameters.';
            }

            // Check for backtest data
            $bt_sharpe = 'NULL';
            $bt_grade  = 'NULL';
            $bt_trades = 0;

            // Upsert
            $upsert = "INSERT INTO lm_ml_status
                (algorithm_name, asset_class, closed_trades, ml_ready,
                 current_tp, current_sl, current_hold, param_source,
                 current_win_rate, current_pf, total_pnl,
                 status, status_reason, updated_at, created_at)
                VALUES ('".$algo."', '".$ac."', ".$ct.", ".$ready.",
                        ".$tp.", ".$sl.", ".$hold.", 'learned',
                        ".$wr.", ".$pf.", ".$pnl.",
                        '".$status."', '".$conn->real_escape_string($reason)."',
                        '".$now."', '".$now."')
                ON DUPLICATE KEY UPDATE
                    closed_trades = ".$ct.",
                    ml_ready = ".$ready.",
                    current_tp = ".$tp.",
                    current_sl = ".$sl.",
                    current_hold = ".$hold.",
                    current_win_rate = ".$wr.",
                    current_pf = ".$pf.",
                    total_pnl = ".$pnl.",
                    status = '".$status."',
                    status_reason = '".$conn->real_escape_string($reason)."',
                    updated_at = '".$now."'";
            $conn->query($upsert);
            $updated++;
        }
    }

    // Add backtested-only algorithms (no live trades)
    $backtested_algos = array(
        array('Cursor Genius',       'STOCK',  5.271,  'A+', 302),
        array('ETF Masters',         'STOCK',  2.053,  'A',  411),
        array('Sector Momentum',     'STOCK',  2.118,  'A',  80),
        array('Sector Rotation',     'STOCK',  0.966,  'C',  265),
        array('Blue Chip Growth',    'STOCK',  -0.739, 'D',  334),
        array('Technical Momentum',  'STOCK',  -3.090, 'D',  12),
        array('Composite Rating',    'STOCK',  -3.355, 'D',  12),
        array('Trend Following',     'CRYPTO', 4.449,  'A+', 84),
        array('Mean Reversion',      'CRYPTO', -1.557, 'D',  90),
        array('Trend Following',     'FOREX',  2.415,  'A',  211),
        array('Mean Reversion',      'FOREX',  2.285,  'A',  338)
    );

    foreach ($backtested_algos as $bt) {
        $algo_name = $conn->real_escape_string($bt[0]);
        $ac = $conn->real_escape_string($bt[1]);
        $sharpe = $bt[2];
        $grade = $conn->real_escape_string($bt[3]);
        $trades = $bt[4];

        // Check if already exists with live trades
        $check = $conn->query("SELECT id, closed_trades FROM lm_ml_status WHERE algorithm_name='".$algo_name."' AND asset_class='".$ac."'");
        if ($check && $check->num_rows > 0) {
            // Update backtest info
            $conn->query("UPDATE lm_ml_status SET backtest_sharpe=".$sharpe.",
                          backtest_grade='".$grade."', backtest_trades=".$trades.",
                          forward_backtest_overlap=1, updated_at='".$now."'
                          WHERE algorithm_name='".$algo_name."' AND asset_class='".$ac."'");
        } else {
            // Insert backtest-only entry
            $conn->query("INSERT INTO lm_ml_status
                (algorithm_name, asset_class, closed_trades, ml_ready,
                 param_source, backtest_sharpe, backtest_grade, backtest_trades,
                 forward_backtest_overlap,
                 status, status_reason, updated_at, created_at)
                VALUES ('".$algo_name."', '".$ac."', 0, 0,
                        'default', ".$sharpe.", '".$grade."', ".$trades.",
                        0,
                        'backtest_only', 'Algorithm has backtest data but is not deployed to live trading.',
                        '".$now."', '".$now."')
                ON DUPLICATE KEY UPDATE
                    backtest_sharpe=".$sharpe.",
                    backtest_grade='".$grade."',
                    backtest_trades=".$trades.",
                    updated_at='".$now."'");
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'refresh', 'updated' => $updated,
        'backtested_synced' => count($backtested_algos)));
    exit;
}

// ─── STATUS — Per asset class ML readiness ──────────────────────────────────
if ($action === 'status') {
    _ml_ensure_schema($conn);

    $where = $asset ? " WHERE asset_class = '".$asset."'" : "";
    $sql = "SELECT * FROM lm_ml_status" . $where . " ORDER BY asset_class, current_win_rate DESC";
    $result = $conn->query($sql);

    $by_asset = array();
    $algorithms = array();

    if ($result && $result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $ac = $row['asset_class'];
            if (!isset($by_asset[$ac])) {
                $by_asset[$ac] = array(
                    'total_algos' => 0,
                    'ml_ready' => 0,
                    'collecting' => 0,
                    'backtest_only' => 0,
                    'total_closed_trades' => 0,
                    'avg_win_rate' => 0,
                    'algorithms' => array()
                );
            }
            $by_asset[$ac]['total_algos']++;
            $by_asset[$ac]['total_closed_trades'] += intval($row['closed_trades']);
            if ($row['ml_ready']) $by_asset[$ac]['ml_ready']++;
            if ($row['status'] === 'collecting_data') $by_asset[$ac]['collecting']++;
            if ($row['status'] === 'backtest_only') $by_asset[$ac]['backtest_only']++;

            $entry = array(
                'algorithm' => $row['algorithm_name'],
                'closed_trades' => intval($row['closed_trades']),
                'min_needed' => intval($row['min_trades_needed']),
                'ml_ready' => intval($row['ml_ready']),
                'trades_remaining' => max(0, intval($row['min_trades_needed']) - intval($row['closed_trades'])),
                'param_source' => $row['param_source'],
                'current_tp' => $row['current_tp'],
                'current_sl' => $row['current_sl'],
                'current_hold' => $row['current_hold'],
                'win_rate' => $row['current_win_rate'],
                'sharpe' => $row['current_sharpe'],
                'profit_factor' => $row['current_pf'],
                'total_pnl' => $row['total_pnl'],
                'backtest_sharpe' => $row['backtest_sharpe'],
                'backtest_grade' => $row['backtest_grade'],
                'backtest_trades' => intval($row['backtest_trades']),
                'forward_backtest_overlap' => intval($row['forward_backtest_overlap']),
                'status' => $row['status'],
                'status_reason' => $row['status_reason'],
                'last_optimization' => $row['last_optimization'],
                'optimization_count' => intval($row['optimization_count']),
                'updated_at' => $row['updated_at']
            );
            $by_asset[$ac]['algorithms'][] = $entry;
            $algorithms[] = $entry;
        }
    }

    // Compute per-asset averages
    foreach ($by_asset as $ac => $data) {
        $total_wr = 0; $wr_count = 0;
        foreach ($data['algorithms'] as $a) {
            if ($a['win_rate'] !== null && $a['closed_trades'] > 0) {
                $total_wr += floatval($a['win_rate']);
                $wr_count++;
            }
        }
        $by_asset[$ac]['avg_win_rate'] = $wr_count > 0 ? round($total_wr / $wr_count, 2) : null;
    }

    // Summary
    $total_algos = count($algorithms);
    $total_ready = 0;
    $total_overlap = 0;
    foreach ($algorithms as $a) {
        if ($a['ml_ready']) $total_ready++;
        if ($a['forward_backtest_overlap']) $total_overlap++;
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'status',
        'summary' => array(
            'total_algorithms' => $total_algos,
            'ml_ready' => $total_ready,
            'forward_backtest_overlap' => $total_overlap,
            'overlap_pct' => $total_algos > 0 ? round($total_overlap / $total_algos * 100, 1) : 0
        ),
        'by_asset_class' => $by_asset,
        'timestamp' => date('Y-m-d H:i:s')
    ));
    exit;
}

// ─── EVOLUTION — Parameter evolution timeline ───────────────────────────────
if ($action === 'evolution') {
    $algo = isset($_GET['algorithm']) ? $conn->real_escape_string($_GET['algorithm']) : null;
    $where = '';
    if ($algo) $where .= " AND algorithm_name = '".$algo."'";
    if ($asset) $where .= " AND asset_class = '".$asset."'";

    $sql = "SELECT * FROM lm_model_versions WHERE 1=1 " . $where . " ORDER BY deployed_at DESC LIMIT 100";
    $result = $conn->query($sql);

    $versions = array();
    if ($result && $result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $versions[] = $row;
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'evolution', 'count' => count($versions), 'versions' => $versions));
    exit;
}

// ─── GAPS — ML capabilities missing per asset class ─────────────────────────
if ($action === 'gaps') {
    _ml_ensure_schema($conn);

    $gaps = array(
        'STOCK' => array(
            'asset_class' => 'STOCK',
            'backtested_algos' => 7,
            'live_algos' => 2,
            'overlap' => 0,
            'ml_status' => 'partial',
            'gaps' => array(
                array('severity' => 'critical', 'gap' => 'Zero forward/backtest overlap',
                      'detail' => 'Cursor Genius (A+), ETF Masters (A), Sector Momentum (A) not deployed to live trading. Live uses Challenger Bot and VAM only.',
                      'fix' => 'Deploy backtested algorithms to live signal engine via picks bridge.',
                      'eta' => '1-2 weeks'),
                array('severity' => 'critical', 'gap' => 'D-grade algorithms still active in daily picks',
                      'detail' => 'Blue Chip Growth (D), Technical Momentum (D), Composite Rating (D) still generating picks.',
                      'fix' => 'Add algorithm-level disable flag to pick generator.',
                      'eta' => 'Immediate'),
                array('severity' => 'high', 'gap' => 'No walk-forward validation',
                      'detail' => 'Backtests use full 2-year window. No train/test split to detect overfitting.',
                      'fix' => 'Implement walk-forward validation with 80/20 time-series splits.',
                      'eta' => '2-3 weeks'),
                array('severity' => 'medium', 'gap' => 'No ensemble weighting',
                      'detail' => 'All algorithms contribute equally. No Sharpe-weighted or information-ratio-weighted combination.',
                      'fix' => 'Calculate per-algorithm ensemble weights based on rolling Sharpe and correlation.',
                      'eta' => '3-4 weeks'),
                array('severity' => 'medium', 'gap' => 'No feature importance tracking',
                      'detail' => 'Cannot identify which indicators drive each algorithm. Limits interpretability.',
                      'fix' => 'Add feature importance calculation to grid search pipeline.',
                      'eta' => '4 weeks'),
                array('severity' => 'low', 'gap' => 'No prediction calibration',
                      'detail' => 'Signal confidence scores not validated against actual outcomes.',
                      'fix' => 'Build calibration curve after 100+ trades per confidence bucket.',
                      'eta' => '6-8 weeks')
            )
        ),
        'CRYPTO' => array(
            'asset_class' => 'CRYPTO',
            'backtested_algos' => 2,
            'live_algos' => 3,
            'overlap' => 0,
            'ml_status' => 'partial',
            'gaps' => array(
                array('severity' => 'critical', 'gap' => 'Trend Following (A+) not deployed to live',
                      'detail' => 'Best backtested crypto algo (Sharpe 4.45) not in live trading. Live uses Ichimoku/StochRSI instead.',
                      'fix' => 'Deploy via picks bridge or add to live signal engine.',
                      'eta' => '1-2 weeks'),
                array('severity' => 'critical', 'gap' => 'Mean Reversion (D) still active in backtest',
                      'detail' => 'Sharpe -1.56, 29% WR. Mean reversion fails in trending crypto markets.',
                      'fix' => 'Disable Mean Reversion for crypto. Keep for forex only.',
                      'eta' => 'Immediate'),
                array('severity' => 'high', 'gap' => 'Insufficient closed trades for grid search',
                      'detail' => 'Ichimoku has 5, StochRSI has 4 closed trades. Need 20 each.',
                      'fix' => 'Continue trading. Grid search will auto-trigger at 20 trades.',
                      'eta' => '5-7 days'),
                array('severity' => 'medium', 'gap' => 'No cross-exchange arbitrage',
                      'detail' => 'Top crypto funds use latency arbitrage. We have no such capability.',
                      'fix' => 'Requires exchange API integration beyond current scope.',
                      'eta' => 'Long-term')
            )
        ),
        'FOREX' => array(
            'asset_class' => 'FOREX',
            'backtested_algos' => 2,
            'live_algos' => 2,
            'overlap' => 0,
            'ml_status' => 'failing',
            'gaps' => array(
                array('severity' => 'critical', 'gap' => 'WRONG algorithms deployed to live trading',
                      'detail' => 'A-grade Trend Following (Sharpe 2.42) and Mean Reversion (Sharpe 2.29) not deployed. Live uses Consensus (0% WR) and RSI Reversal (0% WR).',
                      'fix' => 'Deploy Trend Following and Mean Reversion to live signal engine. Disable Consensus for forex.',
                      'eta' => '1-2 weeks — HIGHEST PRIORITY'),
                array('severity' => 'high', 'gap' => 'Insufficient live data for ML',
                      'detail' => 'Only 3 closed forex trades, all losses. Cannot run grid search.',
                      'fix' => 'Deploy correct algorithms first, then accumulate trades.',
                      'eta' => '3-4 weeks after deployment'),
                array('severity' => 'medium', 'gap' => 'No carry trade component',
                      'detail' => 'Forex markets offer interest rate differential alpha. Not captured.',
                      'fix' => 'Add carry trade scoring as supplemental dimension.',
                      'eta' => '4-6 weeks')
            )
        )
    );

    echo json_encode(array('ok' => true, 'action' => 'gaps', 'gaps' => $gaps, 'timestamp' => date('Y-m-d H:i:s')));
    exit;
}

// ─── BRIDGE — Daily picks bridge status ─────────────────────────────────────
if ($action === 'bridge') {
    _ml_ensure_schema($conn);

    $sql = "SELECT source_table, algorithm_name, status, COUNT(*) as cnt,
                   MIN(pick_date) as earliest, MAX(pick_date) as latest
            FROM lm_picks_bridge
            GROUP BY source_table, algorithm_name, status
            ORDER BY source_table, algorithm_name";
    $result = $conn->query($sql);

    $bridge = array();
    if ($result && $result->num_rows > 0) {
        while ($row = $result->fetch_assoc()) {
            $bridge[] = $row;
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'bridge', 'count' => count($bridge), 'entries' => $bridge));
    exit;
}

// Default
echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action,
    'valid_actions' => array('schema', 'status', 'refresh', 'evolution', 'gaps', 'bridge')));
?>
