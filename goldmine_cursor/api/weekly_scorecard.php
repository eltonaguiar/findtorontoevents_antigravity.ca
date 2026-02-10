<?php
/**
 * GOLDMINE_CURSOR — Weekly Scorecard Builder
 * Computes per-algorithm performance for the current week and stores snapshots.
 * Also runs circuit breaker checks and flags hidden winners / needs review.
 * PHP 5.2 compatible.
 *
 * Usage: GET /goldmine_cursor/api/weekly_scorecard.php?key=goldmine2026
 */
require_once dirname(__FILE__) . '/db_connect.php';

$key = isset($_GET['key']) ? $_GET['key'] : '';
if ($key !== 'goldmine2026') {
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    $conn->close();
    exit;
}

$now = gmdate('Y-m-d H:i:s');
// Week boundaries (Monday to Sunday)
$week_start = date('Y-m-d', strtotime('monday this week'));
$week_end = date('Y-m-d', strtotime('sunday this week'));

$algos_scored = 0;
$winners_found = 0;
$reviews_flagged = 0;
$breakers_triggered = 0;

// ═══════════════════════════════════════════
//  STEP 1: Compute per-algorithm stats
// ═══════════════════════════════════════════
$r = $conn->query("SELECT algorithm, asset_class,
    COUNT(*) as total,
    SUM(CASE WHEN status='won' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN status='lost' THEN 1 ELSE 0 END) as losses,
    AVG(CASE WHEN status='won' THEN pnl_pct ELSE NULL END) as avg_win,
    AVG(CASE WHEN status='lost' THEN pnl_pct ELSE NULL END) as avg_loss,
    SUM(CASE WHEN pnl_pct > 0 THEN pnl_pct ELSE 0 END) as gross_profit,
    SUM(CASE WHEN pnl_pct < 0 THEN ABS(pnl_pct) ELSE 0 END) as gross_loss,
    SUM(pnl_pct) as total_pnl,
    AVG(benchmark_return_pct) as avg_benchmark,
    MIN(pnl_pct) as worst_trade
    FROM goldmine_cursor_predictions
    WHERE status IN ('won','lost')
    GROUP BY algorithm, asset_class
    HAVING (wins + losses) >= 3");

if ($r) {
    while ($row = $r->fetch_assoc()) {
        $wins = intval($row['wins']);
        $losses = intval($row['losses']);
        $resolved = $wins + $losses;
        $gl = floatval($row['gross_loss']);
        $gp = floatval($row['gross_profit']);

        $win_rate = ($resolved > 0) ? round($wins / $resolved * 100, 2) : 0;
        $pf = ($gl > 0) ? round($gp / $gl, 4) : 0;
        $exp = ($resolved > 0) ? round(floatval($row['total_pnl']) / $resolved, 4) : 0;
        $avg_win = round(floatval($row['avg_win']), 4);
        $avg_loss = round(floatval($row['avg_loss']), 4);
        $total_pnl = round(floatval($row['total_pnl']), 4);
        $avg_bench = round(floatval($row['avg_benchmark']), 4);
        $alpha = round($total_pnl - $avg_bench * $resolved, 4);

        // Verdict
        $verdict = 'neutral';
        if ($win_rate > 55 && $pf > 1.5) { $verdict = 'hidden_winner'; $winners_found++; }
        elseif ($win_rate > 50 && $pf > 1.2) { $verdict = 'strong'; }
        elseif ($win_rate < 40 || $pf < 0.8) { $verdict = 'needs_review'; $reviews_flagged++; }

        // Sharpe estimate (simplified — stddev of returns)
        $sr = null;
        $r2 = $conn->query("SELECT STDDEV(pnl_pct) as sd FROM goldmine_cursor_predictions
            WHERE algorithm = '" . $conn->real_escape_string($row['algorithm']) . "'
            AND asset_class = '" . $conn->real_escape_string($row['asset_class']) . "'
            AND status IN ('won','lost')");
        if ($r2 && $srow = $r2->fetch_assoc()) {
            $sd = floatval($srow['sd']);
            if ($sd > 0) { $sr = round($exp / $sd, 4); }
        }

        // Sortino (downside deviation only)
        $sortino = null;
        $r2 = $conn->query("SELECT STDDEV(pnl_pct) as dsd FROM goldmine_cursor_predictions
            WHERE algorithm = '" . $conn->real_escape_string($row['algorithm']) . "'
            AND asset_class = '" . $conn->real_escape_string($row['asset_class']) . "'
            AND status IN ('won','lost') AND pnl_pct < 0");
        if ($r2 && $srow = $r2->fetch_assoc()) {
            $dsd = floatval($srow['dsd']);
            if ($dsd > 0) { $sortino = round($exp / $dsd, 4); }
        }

        // Max drawdown estimate (worst single trade as proxy)
        $max_dd = abs(floatval($row['worst_trade']));

        // Upsert scorecard
        $algo_safe = $conn->real_escape_string($row['algorithm']);
        $ac_safe = $conn->real_escape_string($row['asset_class']);

        // Delete existing for this week + algo + asset
        $conn->query("DELETE FROM goldmine_cursor_algo_scorecard
            WHERE week_start = '$week_start' AND algorithm = '$algo_safe' AND asset_class = '$ac_safe'");

        $conn->query("INSERT INTO goldmine_cursor_algo_scorecard
            (week_start, week_end, asset_class, algorithm, total_picks, wins, losses,
             win_rate, avg_gain_pct, avg_loss_pct, profit_factor, expectancy,
             sharpe_ratio, sortino_ratio, max_drawdown_pct, benchmark_return_pct,
             alpha_pct, verdict, snapshot_at)
            VALUES ('$week_start', '$week_end', '$ac_safe', '$algo_safe', $resolved, $wins, $losses,
                    $win_rate, $avg_win, $avg_loss, $pf, $exp,
                    " . ($sr !== null ? $sr : 'NULL') . ", " . ($sortino !== null ? $sortino : 'NULL') . ", $max_dd,
                    $avg_bench, $alpha, '$verdict', '$now')");

        $algos_scored++;

        // ═══ Circuit breaker check ═══
        if ($max_dd >= 15) {
            // Check if already triggered for this algo
            $cb = $conn->query("SELECT id FROM goldmine_cursor_circuit_breaker
                WHERE algorithm = '$algo_safe' AND asset_class = '$ac_safe' AND status = 'triggered' LIMIT 1");
            if (!$cb || $cb->num_rows === 0) {
                $conn->query("INSERT INTO goldmine_cursor_circuit_breaker
                    (algorithm, asset_class, triggered_at, drawdown_pct, threshold_pct, status, notes)
                    VALUES ('$algo_safe', '$ac_safe', '$now', $max_dd, 15.00, 'triggered',
                    'Auto-detected: worst trade was " . $max_dd . "% loss')");
                $breakers_triggered++;
            }
        }
    }
}

$conn->close();

echo json_encode(array(
    'ok' => true,
    'action' => 'weekly_scorecard',
    'week' => $week_start . ' to ' . $week_end,
    'algorithms_scored' => $algos_scored,
    'hidden_winners_found' => $winners_found,
    'needs_review_flagged' => $reviews_flagged,
    'circuit_breakers_triggered' => $breakers_triggered,
    'timestamp' => $now
));
?>
