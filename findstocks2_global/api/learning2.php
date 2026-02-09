<?php
/**
 * DayTrades Miracle Claude — Self-Learning Algorithm
 * Analyzes past pick outcomes, adjusts strategy weights & parameters,
 * and improves accuracy day by day.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET .../learning2.php?action=analyze              — analyze all resolved picks, generate insights
 *   GET .../learning2.php?action=adjust               — auto-adjust strategy parameters based on performance
 *   GET .../learning2.php?action=report               — full learning report
 *   GET .../learning2.php?action=score_history         — score calibration analysis
 *   GET .../learning2.php?action=ticker_performance    — per-ticker win rates
 *   GET .../learning2.php?action=recommendations       — AI-generated recommendations
 */
require_once dirname(__FILE__) . '/db_connect2.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'report';

$output = array('ok' => true, 'action' => $action);

// ─── Helper: Calculate win rate for a given WHERE clause ───
function lr_win_rate($conn, $where) {
    $res = $conn->query("SELECT COUNT(*) as total,
                                SUM(CASE WHEN outcome='winner' THEN 1 ELSE 0 END) as wins
                         FROM miracle_picks2 WHERE $where AND outcome IN ('winner','loser','expired')");
    if (!$res) return array('total' => 0, 'wins' => 0, 'rate' => 0);
    $r = $res->fetch_assoc();
    $total = (int)$r['total'];
    $wins = (int)$r['wins'];
    $rate = ($total > 0) ? round(($wins / $total) * 100, 2) : 0;
    return array('total' => $total, 'wins' => $wins, 'rate' => $rate);
}

// ─── ANALYZE: Deep performance analysis ───
if ($action === 'analyze' || $action === 'report') {

    // 1. Per-strategy performance
    $strategies = array();
    $res = $conn->query("SELECT strategy_name,
                                COUNT(*) as total,
                                SUM(CASE WHEN outcome='winner' THEN 1 ELSE 0 END) as wins,
                                SUM(CASE WHEN outcome='loser' THEN 1 ELSE 0 END) as losses,
                                AVG(CASE WHEN outcome='winner' THEN outcome_pct ELSE NULL END) as avg_win,
                                AVG(CASE WHEN outcome='loser' THEN outcome_pct ELSE NULL END) as avg_loss,
                                AVG(score) as avg_score,
                                AVG(risk_reward_ratio) as avg_rr,
                                MIN(outcome_pct) as worst_pct,
                                MAX(outcome_pct) as best_pct
                         FROM miracle_picks2
                         WHERE outcome IN ('winner','loser','expired')
                         GROUP BY strategy_name
                         ORDER BY wins DESC");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $total = (int)$row['total'];
            $wins = (int)$row['wins'];
            $row['win_rate'] = ($total > 0) ? round(($wins / $total) * 100, 2) : 0;
            $row['avg_win'] = round((float)$row['avg_win'], 4);
            $row['avg_loss'] = round((float)$row['avg_loss'], 4);
            $row['avg_score'] = round((float)$row['avg_score'], 1);
            $row['avg_rr'] = round((float)$row['avg_rr'], 2);

            // Expectancy
            $w_rate = $wins / max($total, 1);
            $l_rate = (int)$row['losses'] / max($total, 1);
            $row['expectancy'] = round(($w_rate * abs((float)$row['avg_win'])) - ($l_rate * abs((float)$row['avg_loss'])), 4);

            // Grade (A-F)
            if ($row['win_rate'] >= 65 && $row['expectancy'] > 1) $row['grade'] = 'A';
            elseif ($row['win_rate'] >= 55 && $row['expectancy'] > 0.5) $row['grade'] = 'B';
            elseif ($row['win_rate'] >= 45 && $row['expectancy'] > 0) $row['grade'] = 'C';
            elseif ($row['win_rate'] >= 35) $row['grade'] = 'D';
            else $row['grade'] = 'F';

            $strategies[] = $row;
        }
    }
    $output['strategy_analysis'] = $strategies;

    // 2. Score calibration: do higher scores actually predict better outcomes?
    $score_bands = array();
    $bands = array(
        array('label' => '90-100', 'min' => 90, 'max' => 100),
        array('label' => '75-89',  'min' => 75, 'max' => 89),
        array('label' => '60-74',  'min' => 60, 'max' => 74),
        array('label' => '45-59',  'min' => 45, 'max' => 59),
        array('label' => '0-44',   'min' => 0,  'max' => 44)
    );
    foreach ($bands as $band) {
        $wr = lr_win_rate($conn, "score >= {$band['min']} AND score <= {$band['max']}");
        $wr['band'] = $band['label'];
        $score_bands[] = $wr;
    }
    $output['score_calibration'] = $score_bands;

    // 3. CDR vs non-CDR comparison
    $cdr_perf = lr_win_rate($conn, "is_cdr = 1");
    $noncdr_perf = lr_win_rate($conn, "is_cdr = 0");
    $output['cdr_vs_noncdr'] = array(
        'cdr'     => $cdr_perf,
        'non_cdr' => $noncdr_perf
    );

    // 4. Day-of-week analysis
    $dow_perf = array();
    $dow_names = array('Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday');
    for ($d = 0; $d <= 6; $d++) {
        $wr = lr_win_rate($conn, "DAYOFWEEK(scan_date) = " . ($d + 1));
        if ($wr['total'] > 0) {
            $dow_perf[] = array('day' => $dow_names[$d], 'total' => $wr['total'], 'wins' => $wr['wins'], 'win_rate' => $wr['rate']);
        }
    }
    $output['day_of_week'] = $dow_perf;

    // 5. Confidence level accuracy
    $conf_levels = array('high', 'medium', 'low');
    $conf_perf = array();
    foreach ($conf_levels as $cl) {
        $wr = lr_win_rate($conn, "confidence = '$cl'");
        $conf_perf[] = array('confidence' => $cl, 'total' => $wr['total'], 'wins' => $wr['wins'], 'win_rate' => $wr['rate']);
    }
    $output['confidence_accuracy'] = $conf_perf;
}

// ─── ADJUST: Auto-adjust strategy parameters based on performance ───
if ($action === 'adjust' || $action === 'report') {
    $adjustments = array();
    $min_samples = 10; // Need at least 10 resolved picks to adjust

    $res = $conn->query("SELECT strategy_name,
                                COUNT(*) as total,
                                SUM(CASE WHEN outcome='winner' THEN 1 ELSE 0 END) as wins,
                                SUM(CASE WHEN outcome='loser' THEN 1 ELSE 0 END) as losses,
                                AVG(CASE WHEN outcome='winner' THEN outcome_pct ELSE NULL END) as avg_win,
                                AVG(CASE WHEN outcome='loser' THEN outcome_pct ELSE NULL END) as avg_loss,
                                AVG(take_profit_pct) as avg_tp_set,
                                AVG(stop_loss_pct) as avg_sl_set
                         FROM miracle_picks2
                         WHERE outcome IN ('winner','loser','expired')
                         GROUP BY strategy_name
                         HAVING COUNT(*) >= $min_samples");

    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $sname = $row['strategy_name'];
            $total = (int)$row['total'];
            $wins = (int)$row['wins'];
            $losses = (int)$row['losses'];
            $win_rate = round(($wins / $total) * 100, 2);
            $avg_win = abs((float)$row['avg_win']);
            $avg_loss = abs((float)$row['avg_loss']);
            $avg_tp = (float)$row['avg_tp_set'];
            $avg_sl = (float)$row['avg_sl_set'];

            $adj = array(
                'strategy' => $sname,
                'samples'  => $total,
                'current_win_rate' => $win_rate,
                'adjustments' => array()
            );

            // If win rate < 40%, tighten TP (takes profits earlier) or widen SL
            if ($win_rate < 40 && $avg_tp > 3) {
                $new_tp = round($avg_tp * 0.8, 2);
                $adj['adjustments'][] = array(
                    'param' => 'take_profit_pct',
                    'old'   => $avg_tp,
                    'new'   => $new_tp,
                    'reason'=> 'Win rate below 40%: tighten TP to lock in gains earlier'
                );

                if ($action === 'adjust') {
                    $safe_name = $conn->real_escape_string($sname);
                    $conn->query("UPDATE miracle_strategies2 SET default_tp_pct = $new_tp WHERE name = '$safe_name'");
                }
            }

            // If win rate > 65%, widen TP (let winners run more)
            if ($win_rate > 65 && $avg_tp < 15) {
                $new_tp = round($avg_tp * 1.2, 2);
                $adj['adjustments'][] = array(
                    'param' => 'take_profit_pct',
                    'old'   => $avg_tp,
                    'new'   => $new_tp,
                    'reason'=> 'Win rate above 65%: widen TP to let winners run'
                );

                if ($action === 'adjust') {
                    $safe_name = $conn->real_escape_string($sname);
                    $conn->query("UPDATE miracle_strategies2 SET default_tp_pct = $new_tp WHERE name = '$safe_name'");
                }
            }

            // If avg_loss > avg_win * 1.5, tighten SL (losses too large)
            if ($avg_loss > $avg_win * 1.5 && $avg_sl > 2) {
                $new_sl = round($avg_sl * 0.8, 2);
                $adj['adjustments'][] = array(
                    'param' => 'stop_loss_pct',
                    'old'   => $avg_sl,
                    'new'   => $new_sl,
                    'reason'=> 'Average loss exceeds average win by 50%+: tighten SL'
                );

                if ($action === 'adjust') {
                    $safe_name = $conn->real_escape_string($sname);
                    $conn->query("UPDATE miracle_strategies2 SET default_sl_pct = $new_sl WHERE name = '$safe_name'");
                }
            }

            // If strategy consistently underperforms (win_rate < 25% with 20+ samples), disable it
            if ($win_rate < 25 && $total >= 20) {
                $adj['adjustments'][] = array(
                    'param' => 'enabled',
                    'old'   => 1,
                    'new'   => 0,
                    'reason'=> 'Win rate below 25% with 20+ samples: auto-disabled'
                );

                if ($action === 'adjust') {
                    $safe_name = $conn->real_escape_string($sname);
                    $conn->query("UPDATE miracle_strategies2 SET enabled = 0 WHERE name = '$safe_name'");
                }
            }

            // If strategy has very good risk/reward but low win rate, adjust score weight
            if ($avg_win > $avg_loss * 2 && $win_rate < 45) {
                $adj['adjustments'][] = array(
                    'param' => 'note',
                    'old'   => '',
                    'new'   => 'Good R:R but low win rate — keep running but reduce position size',
                    'reason'=> 'Asymmetric payoff profile: large wins, frequent small losses'
                );
            }

            if (count($adj['adjustments']) > 0) {
                $adjustments[] = $adj;
            }
        }
    }

    $output['adjustments'] = $adjustments;

    // Log adjustments
    if ($action === 'adjust' && count($adjustments) > 0) {
        $now = date('Y-m-d H:i:s');
        $ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
        $detail = 'Auto-adjusted ' . count($adjustments) . ' strategies';
        $detail = $conn->real_escape_string($detail);
        $conn->query("INSERT INTO miracle_audit2 (action_type, details, ip_address, created_at) VALUES ('learning_adjust', '$detail', '$ip', '$now')");
    }
}

// ─── SCORE HISTORY: Track how scoring accuracy evolves over time ───
if ($action === 'score_history' || $action === 'report') {
    $sql = "SELECT scan_date,
                   AVG(score) as avg_score,
                   COUNT(*) as total,
                   SUM(CASE WHEN outcome='winner' THEN 1 ELSE 0 END) as wins,
                   AVG(CASE WHEN outcome IN ('winner','loser','expired') THEN outcome_pct ELSE NULL END) as avg_return
            FROM miracle_picks2
            WHERE outcome IN ('winner','loser','expired')
            GROUP BY scan_date
            ORDER BY scan_date DESC
            LIMIT 30";
    $res = $conn->query($sql);
    $history = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $total = (int)$row['total'];
            $row['win_rate'] = ($total > 0) ? round(((int)$row['wins'] / $total) * 100, 2) : 0;
            $row['avg_score'] = round((float)$row['avg_score'], 1);
            $row['avg_return'] = round((float)$row['avg_return'], 4);
            $history[] = $row;
        }
    }
    $output['score_history'] = $history;
}

// ─── TICKER PERFORMANCE: Which tickers are most profitable? ───
if ($action === 'ticker_performance' || $action === 'report') {
    $sql = "SELECT ticker,
                   COUNT(*) as total,
                   SUM(CASE WHEN outcome='winner' THEN 1 ELSE 0 END) as wins,
                   AVG(outcome_pct) as avg_return,
                   SUM(outcome_pct) as total_return,
                   MAX(outcome_pct) as best,
                   MIN(outcome_pct) as worst,
                   is_cdr
            FROM miracle_picks2
            WHERE outcome IN ('winner','loser','expired')
            GROUP BY ticker
            HAVING COUNT(*) >= 3
            ORDER BY total_return DESC
            LIMIT 30";
    $res = $conn->query($sql);
    $ticker_perf = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $total = (int)$row['total'];
            $row['win_rate'] = ($total > 0) ? round(((int)$row['wins'] / $total) * 100, 2) : 0;
            $row['avg_return'] = round((float)$row['avg_return'], 4);
            $row['total_return'] = round((float)$row['total_return'], 4);
            $ticker_perf[] = $row;
        }
    }
    $output['ticker_performance'] = $ticker_perf;
}

// ─── RECOMMENDATIONS: AI-generated improvement suggestions ───
if ($action === 'recommendations' || $action === 'report') {
    $recs = array();

    // Check overall win rate
    $overall = lr_win_rate($conn, "1=1");
    if ($overall['total'] >= 10) {
        if ($overall['rate'] < 40) {
            $recs[] = array('priority' => 'high', 'area' => 'Overall', 'recommendation' => 'Overall win rate is ' . $overall['rate'] . '%. Consider tightening take-profit targets or adding stronger confirmation signals. Run learning2.php?action=adjust to auto-tune.');
        } elseif ($overall['rate'] > 60) {
            $recs[] = array('priority' => 'low', 'area' => 'Overall', 'recommendation' => 'Excellent win rate of ' . $overall['rate'] . '%. Consider widening take-profit targets to capture larger moves.');
        }
    }

    // Check CDR advantage
    $cdr = lr_win_rate($conn, "is_cdr=1");
    $noncdr = lr_win_rate($conn, "is_cdr=0");
    if ($cdr['total'] >= 5 && $noncdr['total'] >= 5) {
        if ($cdr['rate'] > $noncdr['rate'] + 10) {
            $recs[] = array('priority' => 'medium', 'area' => 'CDR', 'recommendation' => 'CDR stocks outperform non-CDR by ' . round($cdr['rate'] - $noncdr['rate'], 1) . '%. Consider increasing CDR weighting in portfolios.');
        }
    }

    // Check for underperforming strategies
    $res = $conn->query("SELECT strategy_name, COUNT(*) as total,
                                SUM(CASE WHEN outcome='winner' THEN 1 ELSE 0 END) as wins
                         FROM miracle_picks2
                         WHERE outcome IN ('winner','loser','expired')
                         GROUP BY strategy_name HAVING COUNT(*) >= 5");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $wr = round(((int)$row['wins'] / (int)$row['total']) * 100, 1);
            if ($wr < 30) {
                $recs[] = array('priority' => 'high', 'area' => $row['strategy_name'], 'recommendation' => 'Strategy "' . $row['strategy_name'] . '" has only ' . $wr . '% win rate (' . $row['total'] . ' trades). Consider disabling or adjusting parameters.');
            }
        }
    }

    // Check score-to-outcome correlation
    $high_score_wr = lr_win_rate($conn, "score >= 70");
    $low_score_wr = lr_win_rate($conn, "score < 50");
    if ($high_score_wr['total'] >= 5 && $low_score_wr['total'] >= 5) {
        if ($low_score_wr['rate'] >= $high_score_wr['rate']) {
            $recs[] = array('priority' => 'high', 'area' => 'Scoring', 'recommendation' => 'Score system is not predictive: low-score picks (' . $low_score_wr['rate'] . '%) win as often as high-score (' . $high_score_wr['rate'] . '%). Scoring formula needs recalibration.');
        }
    }

    // Check for over-trading specific tickers
    $res = $conn->query("SELECT ticker, COUNT(*) as picks FROM miracle_picks2 WHERE scan_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY) GROUP BY ticker HAVING COUNT(*) > 5 ORDER BY picks DESC LIMIT 5");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $recs[] = array('priority' => 'low', 'area' => 'Diversification', 'recommendation' => $row['ticker'] . ' has ' . $row['picks'] . ' picks in the last 7 days. Consider limiting per-ticker frequency.');
        }
    }

    $output['recommendations'] = $recs;
}

echo json_encode($output);
$conn->close();
?>
