<?php
/**
 * ML / heuristic status bridge for sports-betting.html.
 * Reads lm_sports_ml_* and settled bet metrics. PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/sports_db.php';
require_once dirname(__FILE__) . '/sports_metrics_lib.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'status';

function sports_ml_fetch_bets_for_metrics($mysqli) {
    $q = "SELECT b.*, c.closing_price AS closing_odds FROM lm_sports_bets b
          LEFT JOIN lm_sports_clv c ON b.event_id = c.event_id AND b.bookmaker_key = c.bookmaker_key
          AND b.market = c.market AND b.pick = c.outcome_name";
    $r = $mysqli->query($q);
    $rows = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $rows[] = sports_bet_row_to_metric_array($row);
        }
    }
    return $rows;
}

if ($action === 'status') {
    $rows = sports_ml_fetch_bets_for_metrics($sports_mysqli);
    $m = sports_compute_settled_metrics($rows);
    $settled = $m['wins'] + $m['losses'] + $m['pushes'] + $m['voids'];
    $vb = 0;
    $vr = $sports_mysqli->query("SELECT COUNT(*) AS c FROM lm_sports_value_bets WHERE status = 'active'");
    if ($vr && ($vrow = $vr->fetch_assoc())) {
        $vb = intval($vrow['c']);
    }
    $predN = 0;
    $pr = $sports_mysqli->query("SELECT COUNT(*) AS c FROM lm_sports_ml_predictions");
    if ($pr && ($prow = $pr->fetch_assoc())) {
        $predN = intval($prow['c']);
    }
    $trainN = 0;
    $mr = $sports_mysqli->query("SELECT n_training_bets FROM lm_sports_ml_metrics ORDER BY metric_date DESC, id DESC LIMIT 1");
    if ($mr && ($mrow = $mr->fetch_assoc())) {
        $trainN = intval($mrow['n_training_bets']);
    }
    $minTrain = 20;
    // Synthetic bets from the historical backtest harness count toward the
    // ensemble-activation training threshold but NOT toward the user-facing
    // "Settled bets / win rate / ROI" honesty banner. Source of truth:
    // live-monitor/sportsbetting_lib/backtest_runner.py + sports_value_analyze_cli.php.
    //
    // Aggregate across ALL finished runs so an operator running multiple sport-
    // scoped backtests (e.g. NBA 2023, then NHL 2024) sees the union counted —
    // not just the most recent run's contribution. Assumes runs use compatible
    // devig methodology, which is true today since the CLI wrapper calls the
    // same sports_value_analyze_run() as production.
    $synthN = 0;
    $synthLatestRun = '';
    $sr = $sports_mysqli->query("SELECT run_id FROM lm_sports_backtest_runs WHERE finished_at IS NOT NULL ORDER BY finished_at DESC LIMIT 1");
    if ($sr && ($srow = $sr->fetch_assoc())) {
        $synthLatestRun = $srow['run_id'];
    }
    $sq = $sports_mysqli->query(
        "SELECT COUNT(*) AS c FROM lm_sports_synthetic_bets "
        . "WHERE backtest_run_id IN (SELECT run_id FROM lm_sports_backtest_runs WHERE finished_at IS NOT NULL) "
        . "AND actual_outcome IN ('win','loss','push')"
    );
    if ($sq && ($srow2 = $sq->fetch_assoc())) {
        $synthN = intval($srow2['c']);
    }
    $trainingPool = $settled + $synthN;
    $trained = ($trainN >= $minTrain) || ($predN >= 50 && $trainingPool >= $minTrain);
    $INITIAL = 1000.0;
    $pnlRow = $sports_mysqli->query("SELECT COALESCE(SUM(pnl),0) AS tp FROM lm_sports_bets WHERE result IS NOT NULL AND result != ''");
    $br = $INITIAL;
    if ($pnlRow && ($pr2 = $pnlRow->fetch_assoc())) {
        $br += floatval($pr2['tp']);
    }
    echo json_encode(array(
        'ok' => true,
        'status' => array(
            'ml_model_trained' => $trained,
            'settled_bets' => $settled,
            'pending_value_bets' => $vb,
            'min_training_bets' => $minTrain,
            'win_rate' => $m['win_rate_pct'],
            'roi_pct' => $m['roi_pct'],
            'bankroll' => round($br, 2),
            'ml_predictions_rows' => $predN,
            'ml_metrics_train_n' => $trainN,
            'synthetic_bets_in_pool' => $synthN,
            'synthetic_run_id' => $synthLatestRun,
            'training_pool_size' => $trainingPool,
        ),
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'clv') {
    $avgPct = null;
    $posPct = null;
    $n = 0;
    $cr = $sports_mysqli->query("SELECT COUNT(*) AS c, AVG(clv_pct) AS a,
        100.0 * SUM(CASE WHEN clv_pct > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0) AS pos
        FROM lm_sports_clv WHERE closing_price IS NOT NULL AND closing_price > 0");
    if ($cr && ($crow = $cr->fetch_assoc())) {
        $n = intval($crow['c']);
        if ($crow['a'] !== null) {
            $avgPct = round(floatval($crow['a']), 3);
        }
        if ($crow['pos'] !== null) {
            $posPct = round(floatval($crow['pos']), 2);
        }
    }
    $interp = 'Closing-line value (CLV) from lm_sports_clv. +CLV means entry beat the close on average.';
    if ($n < 1) {
        $interp = 'No CLV rows with closing prices yet. Odds snapshots populate lm_sports_clv over time.';
    }

    // 12-week trend. Tries `settled_at`, then falls back to `created_at` if the
    // column is absent (older schema variants). Empty array on any failure so
    // the frontend hides the chart cleanly.
    $trend = array();
    $tsCols = array('settled_at', 'created_at');
    foreach ($tsCols as $col) {
        $sql = "SELECT DATE_SUB(DATE(`$col`), INTERVAL WEEKDAY(`$col`) DAY) AS week_start,
                       COUNT(*) AS events,
                       AVG(clv_pct) AS avg_clv_pct,
                       100.0 * SUM(CASE WHEN clv_pct > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0) AS positive_clv_pct
                FROM lm_sports_clv
                WHERE closing_price IS NOT NULL AND closing_price > 0
                  AND `$col` IS NOT NULL
                  AND `$col` >= DATE_SUB(CURDATE(), INTERVAL 12 WEEK)
                GROUP BY week_start
                ORDER BY week_start ASC
                LIMIT 12";
        $tr = @$sports_mysqli->query($sql);
        if ($tr) {
            while ($trow = $tr->fetch_assoc()) {
                $trend[] = array(
                    'week_start' => $trow['week_start'],
                    'events' => intval($trow['events']),
                    'avg_clv_pct' => ($trow['avg_clv_pct'] !== null) ? round(floatval($trow['avg_clv_pct']), 3) : null,
                    'positive_clv_pct' => ($trow['positive_clv_pct'] !== null) ? round(floatval($trow['positive_clv_pct']), 2) : null,
                );
            }
            break; // success: stop trying alternate columns
        }
    }

    echo json_encode(array(
        'ok' => true,
        'clv' => array(
            'avg_clv_pct' => ($avgPct !== null) ? $avgPct : '--',
            'positive_clv_pct' => ($posPct !== null) ? $posPct : '--',
            'total_events' => $n,
            'interpretation' => $interp,
            'clv_weekly_trend' => $trend,
        ),
    ));
    $sports_mysqli->close();
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'unknown action'));
$sports_mysqli->close();
