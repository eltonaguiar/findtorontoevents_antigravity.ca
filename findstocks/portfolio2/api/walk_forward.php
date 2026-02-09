<?php
/**
 * Walk-Forward Validation Engine
 * Replaces naive "test all data at once" grid search with rolling train/test windows
 * to prevent overfitting. Measures out-of-sample (OOS) performance vs in-sample (IS).
 * PHP 5.2 compatible.
 *
 * Actions:
 *   validate      — Walk-forward validation for one algorithm/strategy
 *   validate_all  — Batch validate all algorithms (for GitHub Actions)
 *   compare       — Compare WF OOS results vs naive grid search results
 *   results       — Fetch stored walk-forward results
 *
 * Usage:
 *   GET .../walk_forward.php?action=validate&source=stock_picks&algorithm=CAN+SLIM
 *   GET .../walk_forward.php?action=validate&source=miracle_picks3&strategy=Gap+Up+Momentum
 *   GET .../walk_forward.php?action=validate_all&key=stocksrefresh2026
 *   GET .../walk_forward.php?action=compare&source=stock_picks&algorithm=CAN+SLIM
 *   GET .../walk_forward.php?action=results&source=stock_picks
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'validate';
$response = array('ok' => true, 'action' => $action);
$admin_key = 'stocksrefresh2026';
$is_admin = (isset($_GET['key']) && $_GET['key'] === $admin_key);

// ═══════════════════════════════════════════════
// Auto-create tables
// ═══════════════════════════════════════════════
$conn->query("CREATE TABLE IF NOT EXISTS walk_forward_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_table VARCHAR(30) NOT NULL DEFAULT 'stock_picks',
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    strategy_name VARCHAR(100) NOT NULL DEFAULT '',
    fold_num INT NOT NULL DEFAULT 0,
    total_folds INT NOT NULL DEFAULT 0,
    train_start DATE NOT NULL,
    train_end DATE NOT NULL,
    test_start DATE NOT NULL,
    test_end DATE NOT NULL,
    train_picks INT NOT NULL DEFAULT 0,
    test_picks INT NOT NULL DEFAULT 0,
    is_best_tp DECIMAL(6,2) NOT NULL DEFAULT 0,
    is_best_sl DECIMAL(6,2) NOT NULL DEFAULT 0,
    is_best_hold INT NOT NULL DEFAULT 0,
    is_win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    is_avg_return DECIMAL(10,4) NOT NULL DEFAULT 0,
    is_profit_factor DECIMAL(8,4) NOT NULL DEFAULT 0,
    oos_win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    oos_avg_return DECIMAL(10,4) NOT NULL DEFAULT 0,
    oos_profit_factor DECIMAL(8,4) NOT NULL DEFAULT 0,
    oos_trades INT NOT NULL DEFAULT 0,
    wf_efficiency DECIMAL(8,4) NOT NULL DEFAULT 0,
    regime_at_test VARCHAR(20) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    KEY idx_source (source_table),
    KEY idx_algo (algorithm_name),
    KEY idx_strat (strategy_name),
    KEY idx_date (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ═══════════════════════════════════════════════
// Summary table for overall WF efficiency per algo
// ═══════════════════════════════════════════════
$conn->query("CREATE TABLE IF NOT EXISTS walk_forward_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_table VARCHAR(30) NOT NULL DEFAULT 'stock_picks',
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    strategy_name VARCHAR(100) NOT NULL DEFAULT '',
    total_folds INT NOT NULL DEFAULT 0,
    avg_wf_efficiency DECIMAL(8,4) NOT NULL DEFAULT 0,
    avg_oos_win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_oos_return DECIMAL(10,4) NOT NULL DEFAULT 0,
    avg_is_win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_is_return DECIMAL(10,4) NOT NULL DEFAULT 0,
    best_robust_tp DECIMAL(6,2) NOT NULL DEFAULT 0,
    best_robust_sl DECIMAL(6,2) NOT NULL DEFAULT 0,
    best_robust_hold INT NOT NULL DEFAULT 0,
    overfitting_flag TINYINT NOT NULL DEFAULT 0,
    naive_is_return DECIMAL(10,4) NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_src_algo (source_table, algorithm_name, strategy_name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ═══════════════════════════════════════════════
// BACKTEST: Date-filtered version for stock_picks (uses daily_prices OHLC)
// ═══════════════════════════════════════════════
function _wf_backtest_stocks($conn, $algo, $tp, $sl, $mhd, $date_from, $date_to) {
    $safe_algo = $conn->real_escape_string($algo);
    $safe_from = $conn->real_escape_string($date_from);
    $safe_to = $conn->real_escape_string($date_to);

    $sql = "SELECT sp.entry_price, sp.pick_date, sp.ticker
            FROM stock_picks sp
            WHERE sp.entry_price > 0
              AND sp.algorithm_name = '$safe_algo'
              AND sp.pick_date >= '$safe_from'
              AND sp.pick_date <= '$safe_to'
            ORDER BY sp.pick_date ASC";
    $res = $conn->query($sql);
    if (!$res || $res->num_rows === 0) {
        return array('trades' => 0, 'wins' => 0, 'losses' => 0, 'win_rate' => 0,
                     'avg_return' => 0, 'total_return' => 0, 'profit_factor' => 0);
    }

    $trades = 0;
    $wins = 0;
    $total_gain = 0;
    $total_loss = 0;
    $total_return = 0;

    while ($pick = $res->fetch_assoc()) {
        $entry = (float)$pick['entry_price'];
        $ticker = $pick['ticker'];
        $pdate = $pick['pick_date'];
        if ($entry <= 0) continue;

        $st = $conn->real_escape_string($ticker);
        $sd = $conn->real_escape_string($pdate);
        $pr = $conn->query("SELECT high_price, low_price, close_price FROM daily_prices
                            WHERE ticker='$st' AND trade_date > '$sd'
                            ORDER BY trade_date ASC LIMIT $mhd");

        $dc = 0;
        $exit_pct = 0;
        $sold = false;
        if ($pr && $pr->num_rows > 0) {
            while ($d = $pr->fetch_assoc()) {
                $dc++;
                $dh = (float)$d['high_price'];
                $dl = (float)$d['low_price'];
                $dclose = (float)$d['close_price'];
                $tp_p = $entry * (1 + $tp / 100);
                $sl_p = $entry * (1 - $sl / 100);

                if ($dl > 0 && $dl <= $sl_p) { $exit_pct = -$sl; $sold = true; break; }
                if ($dh > 0 && $dh >= $tp_p) { $exit_pct = $tp; $sold = true; break; }
                if ($dc >= $mhd && $dclose > 0) {
                    $exit_pct = (($dclose - $entry) / $entry) * 100;
                    $sold = true;
                    break;
                }
            }
            if (!$sold && $dc > 0 && $dclose > 0) {
                $exit_pct = (($dclose - $entry) / $entry) * 100;
            }
        }

        $trades++;
        $total_return += $exit_pct;
        if ($exit_pct > 0) {
            $wins++;
            $total_gain += $exit_pct;
        } else {
            $total_loss += abs($exit_pct);
        }
    }

    $losses = $trades - $wins;
    $wr = ($trades > 0) ? round($wins / $trades * 100, 2) : 0;
    $avg_ret = ($trades > 0) ? round($total_return / $trades, 4) : 0;
    $pf = ($total_loss > 0) ? round($total_gain / $total_loss, 4) : ($total_gain > 0 ? 99.99 : 0);

    return array(
        'trades' => $trades, 'wins' => $wins, 'losses' => $losses,
        'win_rate' => $wr, 'avg_return' => $avg_ret,
        'total_return' => round($total_return, 4), 'profit_factor' => $pf
    );
}

// ═══════════════════════════════════════════════
// BACKTEST: Date-filtered version for miracle_picks3 (uses outcome_pct)
// ═══════════════════════════════════════════════
function _wf_backtest_miracle3($conn, $strategy, $tp, $sl, $date_from, $date_to) {
    $safe = $conn->real_escape_string($strategy);
    $safe_from = $conn->real_escape_string($date_from);
    $safe_to = $conn->real_escape_string($date_to);

    $sql = "SELECT entry_price, outcome_pct, outcome FROM miracle_picks3
            WHERE strategy_name='$safe' AND outcome IN ('won','lost') AND entry_price > 0
              AND scan_date >= '$safe_from' AND scan_date <= '$safe_to'";
    $res = $conn->query($sql);
    if (!$res || $res->num_rows === 0) {
        return array('trades' => 0, 'wins' => 0, 'losses' => 0, 'win_rate' => 0,
                     'avg_return' => 0, 'total_return' => 0, 'profit_factor' => 0);
    }

    $trades = 0;
    $wins = 0;
    $total_gain = 0;
    $total_loss = 0;
    $total_return = 0;

    while ($pick = $res->fetch_assoc()) {
        $actual_pct = (float)$pick['outcome_pct'];
        $trades++;

        if ($actual_pct >= $tp) {
            $wins++;
            $total_gain += $tp;
            $total_return += $tp;
        } elseif ($actual_pct <= -$sl) {
            $total_loss += $sl;
            $total_return += (-$sl);
        } else {
            if ($actual_pct > 0) { $wins++; $total_gain += $actual_pct; }
            else { $total_loss += abs($actual_pct); }
            $total_return += $actual_pct;
        }
    }

    $losses = $trades - $wins;
    $wr = ($trades > 0) ? round($wins / $trades * 100, 2) : 0;
    $avg_ret = ($trades > 0) ? round($total_return / $trades, 4) : 0;
    $pf = ($total_loss > 0) ? round($total_gain / $total_loss, 4) : ($total_gain > 0 ? 99.99 : 0);

    return array(
        'trades' => $trades, 'wins' => $wins, 'losses' => $losses,
        'win_rate' => $wr, 'avg_return' => $avg_ret,
        'total_return' => round($total_return, 4), 'profit_factor' => $pf
    );
}

// ═══════════════════════════════════════════════
// BACKTEST: Date-filtered version for miracle_picks2
// ═══════════════════════════════════════════════
function _wf_backtest_miracle2($conn, $strategy, $tp, $sl, $date_from, $date_to) {
    $safe = $conn->real_escape_string($strategy);
    $safe_from = $conn->real_escape_string($date_from);
    $safe_to = $conn->real_escape_string($date_to);

    $sql = "SELECT entry_price, outcome_pct, outcome FROM miracle_picks2
            WHERE strategy_name='$safe' AND outcome IN ('won','lost') AND entry_price > 0
              AND scan_date >= '$safe_from' AND scan_date <= '$safe_to'";
    $res = $conn->query($sql);
    if (!$res || $res->num_rows === 0) {
        return array('trades' => 0, 'wins' => 0, 'losses' => 0, 'win_rate' => 0,
                     'avg_return' => 0, 'total_return' => 0, 'profit_factor' => 0);
    }

    $trades = 0;
    $wins = 0;
    $total_gain = 0;
    $total_loss = 0;
    $total_return = 0;

    while ($pick = $res->fetch_assoc()) {
        $actual_pct = (float)$pick['outcome_pct'];
        $trades++;

        if ($actual_pct >= $tp) {
            $wins++;
            $total_gain += $tp;
            $total_return += $tp;
        } elseif ($actual_pct <= -$sl) {
            $total_loss += $sl;
            $total_return += (-$sl);
        } else {
            if ($actual_pct > 0) { $wins++; $total_gain += $actual_pct; }
            else { $total_loss += abs($actual_pct); }
            $total_return += $actual_pct;
        }
    }

    $losses = $trades - $wins;
    $wr = ($trades > 0) ? round($wins / $trades * 100, 2) : 0;
    $avg_ret = ($trades > 0) ? round($total_return / $trades, 4) : 0;
    $pf = ($total_loss > 0) ? round($total_gain / $total_loss, 4) : ($total_gain > 0 ? 99.99 : 0);

    return array(
        'trades' => $trades, 'wins' => $wins, 'losses' => $losses,
        'win_rate' => $wr, 'avg_return' => $avg_ret,
        'total_return' => round($total_return, 4), 'profit_factor' => $pf
    );
}

// ═══════════════════════════════════════════════
// GRID SEARCH: Find best TP/SL params on a date range
// ═══════════════════════════════════════════════
function _wf_grid_search($conn, $source, $name, $date_from, $date_to) {
    // Grid parameters
    $tp_grid = array(3, 5, 7, 10, 15, 20, 30, 50);
    $sl_grid = array(2, 3, 5, 7, 10, 15);
    $hold_grid = array(5, 7, 14, 30); // only for stock_picks

    $best_score = -9999;
    $best_params = array('tp' => 10, 'sl' => 5, 'hold' => 7);
    $best_perf = array('trades' => 0, 'win_rate' => 0, 'avg_return' => 0, 'profit_factor' => 0);

    if ($source === 'stock_picks') {
        foreach ($tp_grid as $tp) {
            foreach ($sl_grid as $sl) {
                foreach ($hold_grid as $hold) {
                    $r = _wf_backtest_stocks($conn, $name, $tp, $sl, $hold, $date_from, $date_to);
                    if ($r['trades'] >= 2) {
                        $score = $r['win_rate'] * 0.3 + $r['avg_return'] * 5 + $r['profit_factor'] * 10;
                        if ($score > $best_score) {
                            $best_score = $score;
                            $best_params = array('tp' => $tp, 'sl' => $sl, 'hold' => $hold);
                            $best_perf = $r;
                        }
                    }
                }
            }
        }
    } else {
        // miracle_picks2 or miracle_picks3
        foreach ($tp_grid as $tp) {
            foreach ($sl_grid as $sl) {
                if ($source === 'miracle_picks3') {
                    $r = _wf_backtest_miracle3($conn, $name, $tp, $sl, $date_from, $date_to);
                } else {
                    $r = _wf_backtest_miracle2($conn, $name, $tp, $sl, $date_from, $date_to);
                }
                if ($r['trades'] >= 2) {
                    $score = $r['win_rate'] * 0.3 + $r['avg_return'] * 5 + $r['profit_factor'] * 10;
                    if ($score > $best_score) {
                        $best_score = $score;
                        $best_params = array('tp' => $tp, 'sl' => $sl, 'hold' => 0);
                        $best_perf = $r;
                    }
                }
            }
        }
    }

    return array('params' => $best_params, 'perf' => $best_perf, 'score' => round($best_score, 4));
}

// ═══════════════════════════════════════════════
// Get current regime from market_regimes table
// ═══════════════════════════════════════════════
function _wf_get_regime_at($conn, $date) {
    $safe = $conn->real_escape_string($date);
    $r = $conn->query("SELECT regime FROM market_regimes WHERE trade_date <= '$safe' ORDER BY trade_date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        return $row['regime'] ? $row['regime'] : 'unknown';
    }
    return 'unknown';
}

// ═══════════════════════════════════════════════
// WALK-FORWARD: Core rolling window validation
// ═══════════════════════════════════════════════
function _wf_run_validation($conn, $source, $name, $train_days, $test_days) {
    // Get date range of available picks
    if ($source === 'stock_picks') {
        $safe_name = $conn->real_escape_string($name);
        $dr = $conn->query("SELECT MIN(pick_date) as min_d, MAX(pick_date) as max_d
                            FROM stock_picks WHERE entry_price > 0 AND algorithm_name='$safe_name'");
    } elseif ($source === 'miracle_picks3') {
        $safe_name = $conn->real_escape_string($name);
        $dr = $conn->query("SELECT MIN(scan_date) as min_d, MAX(scan_date) as max_d
                            FROM miracle_picks3 WHERE entry_price > 0 AND outcome IN ('won','lost')
                            AND strategy_name='$safe_name'");
    } else {
        $safe_name = $conn->real_escape_string($name);
        $dr = $conn->query("SELECT MIN(scan_date) as min_d, MAX(scan_date) as max_d
                            FROM miracle_picks2 WHERE entry_price > 0 AND outcome IN ('won','lost')
                            AND strategy_name='$safe_name'");
    }

    if (!$dr || $dr->num_rows === 0) {
        return array('folds' => array(), 'error' => 'No data found');
    }
    $drow = $dr->fetch_assoc();
    $min_date = $drow['min_d'];
    $max_date = $drow['max_d'];

    if (!$min_date || !$max_date) {
        return array('folds' => array(), 'error' => 'No date range');
    }

    $min_ts = strtotime($min_date);
    $max_ts = strtotime($max_date);
    $total_days = (int)(($max_ts - $min_ts) / 86400);

    // Need at least train + test days of data
    if ($total_days < ($train_days + $test_days)) {
        return array('folds' => array(), 'error' => 'Insufficient data: ' . $total_days . ' days available, need ' . ($train_days + $test_days));
    }

    $folds = array();
    $fold_num = 0;
    $cursor_ts = $min_ts;

    while (true) {
        $train_start = date('Y-m-d', $cursor_ts);
        $train_end_ts = $cursor_ts + ($train_days * 86400);
        $train_end = date('Y-m-d', $train_end_ts);

        $test_start_ts = $train_end_ts + 86400;
        $test_start = date('Y-m-d', $test_start_ts);
        $test_end_ts = $test_start_ts + ($test_days * 86400);
        $test_end = date('Y-m-d', $test_end_ts);

        // Stop if test period goes beyond available data
        if ($test_end_ts > $max_ts) break;

        $fold_num++;

        // Phase 1: Grid search on training data (in-sample)
        $is_result = _wf_grid_search($conn, $source, $name, $train_start, $train_end);

        // Phase 2: Test those params on out-of-sample data
        $best_tp = $is_result['params']['tp'];
        $best_sl = $is_result['params']['sl'];
        $best_hold = $is_result['params']['hold'];

        if ($source === 'stock_picks') {
            $oos_result = _wf_backtest_stocks($conn, $name, $best_tp, $best_sl, $best_hold, $test_start, $test_end);
        } elseif ($source === 'miracle_picks3') {
            $oos_result = _wf_backtest_miracle3($conn, $name, $best_tp, $best_sl, $test_start, $test_end);
        } else {
            $oos_result = _wf_backtest_miracle2($conn, $name, $best_tp, $best_sl, $test_start, $test_end);
        }

        // Calculate walk-forward efficiency
        $is_ret = $is_result['perf']['avg_return'];
        $oos_ret = $oos_result['avg_return'];
        $wf_eff = ($is_ret != 0) ? round($oos_ret / $is_ret, 4) : 0;

        // Get regime at test period
        $regime = _wf_get_regime_at($conn, $test_start);

        // Count picks in each period
        if ($source === 'stock_picks') {
            $safe_name2 = $conn->real_escape_string($name);
            $tc = $conn->query("SELECT COUNT(*) as cnt FROM stock_picks WHERE algorithm_name='$safe_name2' AND entry_price>0 AND pick_date>='$train_start' AND pick_date<='$train_end'");
            $train_picks = ($tc && $tc->num_rows > 0) ? (int)$tc->fetch_assoc() : 0;
            if (is_array($train_picks)) $train_picks = $train_picks['cnt'];
        } else {
            $date_col = 'scan_date';
            $table = ($source === 'miracle_picks3') ? 'miracle_picks3' : 'miracle_picks2';
            $name_col = 'strategy_name';
            $safe_name2 = $conn->real_escape_string($name);
            $tc = $conn->query("SELECT COUNT(*) as cnt FROM $table WHERE $name_col='$safe_name2' AND entry_price>0 AND outcome IN ('won','lost') AND $date_col>='$train_start' AND $date_col<='$train_end'");
            $train_picks = ($tc && $tc->num_rows > 0) ? (int)$tc->fetch_assoc() : 0;
            if (is_array($train_picks)) $train_picks = $train_picks['cnt'];
        }

        $fold = array(
            'fold' => $fold_num,
            'train_start' => $train_start,
            'train_end' => $train_end,
            'test_start' => $test_start,
            'test_end' => $test_end,
            'train_picks' => $train_picks,
            'is_best_tp' => $best_tp,
            'is_best_sl' => $best_sl,
            'is_best_hold' => $best_hold,
            'is_win_rate' => $is_result['perf']['win_rate'],
            'is_avg_return' => $is_ret,
            'is_profit_factor' => $is_result['perf']['profit_factor'],
            'oos_trades' => $oos_result['trades'],
            'oos_win_rate' => $oos_result['win_rate'],
            'oos_avg_return' => $oos_ret,
            'oos_profit_factor' => $oos_result['profit_factor'],
            'wf_efficiency' => $wf_eff,
            'regime' => $regime
        );
        $folds[] = $fold;

        // Slide window forward by test_days (non-overlapping test windows)
        $cursor_ts += ($test_days * 86400);
    }

    return array('folds' => $folds, 'total_folds' => $fold_num);
}

// ═══════════════════════════════════════════════
// ACTION: validate — Run walk-forward for one algo/strategy
// ═══════════════════════════════════════════════
if ($action === 'validate') {
    $source = isset($_GET['source']) ? trim($_GET['source']) : 'stock_picks';
    $algorithm = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';
    $strategy = isset($_GET['strategy']) ? trim($_GET['strategy']) : '';
    $train_days = isset($_GET['train_days']) ? max(14, min(180, (int)$_GET['train_days'])) : 60;
    $test_days = isset($_GET['test_days']) ? max(7, min(60, (int)$_GET['test_days'])) : 20;

    $name = ($source === 'stock_picks') ? $algorithm : $strategy;
    if ($name === '') {
        $response['ok'] = false;
        $response['error'] = 'Missing algorithm or strategy parameter';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $result = _wf_run_validation($conn, $source, $name, $train_days, $test_days);

    if (isset($result['error'])) {
        $response['error'] = $result['error'];
        $response['folds'] = array();
    } else {
        $folds = $result['folds'];
        $response['source'] = $source;
        $response['name'] = $name;
        $response['train_days'] = $train_days;
        $response['test_days'] = $test_days;
        $response['total_folds'] = $result['total_folds'];
        $response['folds'] = $folds;

        // Calculate aggregate metrics
        $total_oos_ret = 0;
        $total_is_ret = 0;
        $total_oos_wr = 0;
        $total_is_wr = 0;
        $total_oos_trades = 0;
        $valid_folds = 0;

        foreach ($folds as $f) {
            if ($f['oos_trades'] > 0) {
                $valid_folds++;
                $total_oos_ret += $f['oos_avg_return'];
                $total_is_ret += $f['is_avg_return'];
                $total_oos_wr += $f['oos_win_rate'];
                $total_is_wr += $f['is_win_rate'];
                $total_oos_trades += $f['oos_trades'];
            }
        }

        $avg_oos_ret = ($valid_folds > 0) ? round($total_oos_ret / $valid_folds, 4) : 0;
        $avg_is_ret = ($valid_folds > 0) ? round($total_is_ret / $valid_folds, 4) : 0;
        $avg_oos_wr = ($valid_folds > 0) ? round($total_oos_wr / $valid_folds, 2) : 0;
        $avg_is_wr = ($valid_folds > 0) ? round($total_is_wr / $valid_folds, 2) : 0;
        $avg_wf_eff = ($avg_is_ret != 0) ? round($avg_oos_ret / $avg_is_ret, 4) : 0;

        // Overfitting flag: WF efficiency < 0.5 = likely overfitting
        $overfitting = ($avg_wf_eff < 0.5 && $valid_folds >= 2) ? true : false;

        // Find most common best params across folds (robust params)
        $tp_counts = array();
        $sl_counts = array();
        $hold_counts = array();
        foreach ($folds as $f) {
            $tk = (string)$f['is_best_tp'];
            $sk = (string)$f['is_best_sl'];
            $hk = (string)$f['is_best_hold'];
            $tp_counts[$tk] = isset($tp_counts[$tk]) ? $tp_counts[$tk] + 1 : 1;
            $sl_counts[$sk] = isset($sl_counts[$sk]) ? $sl_counts[$sk] + 1 : 1;
            $hold_counts[$hk] = isset($hold_counts[$hk]) ? $hold_counts[$hk] + 1 : 1;
        }
        arsort($tp_counts);
        arsort($sl_counts);
        arsort($hold_counts);
        $robust_tp_keys = array_keys($tp_counts);
        $robust_sl_keys = array_keys($sl_counts);
        $robust_hold_keys = array_keys($hold_counts);
        $robust_tp = (float)$robust_tp_keys[0];
        $robust_sl = (float)$robust_sl_keys[0];
        $robust_hold = (int)$robust_hold_keys[0];

        $response['summary'] = array(
            'valid_folds' => $valid_folds,
            'total_oos_trades' => $total_oos_trades,
            'avg_oos_win_rate' => $avg_oos_wr,
            'avg_oos_return' => $avg_oos_ret,
            'avg_is_win_rate' => $avg_is_wr,
            'avg_is_return' => $avg_is_ret,
            'avg_wf_efficiency' => $avg_wf_eff,
            'overfitting_flag' => $overfitting,
            'robust_params' => array('tp' => $robust_tp, 'sl' => $robust_sl, 'hold' => $robust_hold),
            'param_stability' => array(
                'tp_most_common' => $robust_tp,
                'tp_frequency' => $tp_counts[(string)$robust_tp] . '/' . count($folds),
                'sl_most_common' => $robust_sl,
                'sl_frequency' => $sl_counts[(string)$robust_sl] . '/' . count($folds)
            )
        );

        // Store results if admin key provided
        if ($is_admin && $valid_folds > 0) {
            // Clear old results for this algo
            $safe_src = $conn->real_escape_string($source);
            $safe_nm = $conn->real_escape_string($name);
            $algo_col = ($source === 'stock_picks') ? 'algorithm_name' : 'strategy_name';
            $conn->query("DELETE FROM walk_forward_results WHERE source_table='$safe_src' AND $algo_col='$safe_nm'");

            $now = date('Y-m-d H:i:s');
            foreach ($folds as $f) {
                $vals = array(
                    "'" . $safe_src . "'",
                    "'" . (($source === 'stock_picks') ? $safe_nm : '') . "'",
                    "'" . (($source !== 'stock_picks') ? $safe_nm : '') . "'",
                    (int)$f['fold'],
                    (int)$result['total_folds'],
                    "'" . $conn->real_escape_string($f['train_start']) . "'",
                    "'" . $conn->real_escape_string($f['train_end']) . "'",
                    "'" . $conn->real_escape_string($f['test_start']) . "'",
                    "'" . $conn->real_escape_string($f['test_end']) . "'",
                    (int)$f['train_picks'],
                    (int)$f['oos_trades'],
                    (float)$f['is_best_tp'],
                    (float)$f['is_best_sl'],
                    (int)$f['is_best_hold'],
                    (float)$f['is_win_rate'],
                    (float)$f['is_avg_return'],
                    (float)$f['is_profit_factor'],
                    (float)$f['oos_win_rate'],
                    (float)$f['oos_avg_return'],
                    (float)$f['oos_profit_factor'],
                    (int)$f['oos_trades'],
                    (float)$f['wf_efficiency'],
                    "'" . $conn->real_escape_string($f['regime']) . "'",
                    "'" . $now . "'"
                );
                $conn->query("INSERT INTO walk_forward_results (source_table, algorithm_name, strategy_name,
                    fold_num, total_folds, train_start, train_end, test_start, test_end,
                    train_picks, test_picks, is_best_tp, is_best_sl, is_best_hold,
                    is_win_rate, is_avg_return, is_profit_factor,
                    oos_win_rate, oos_avg_return, oos_profit_factor, oos_trades,
                    wf_efficiency, regime_at_test, created_at)
                    VALUES (" . implode(',', $vals) . ")");
            }

            // Update summary
            $conn->query("DELETE FROM walk_forward_summary WHERE source_table='$safe_src' AND algorithm_name='" . (($source === 'stock_picks') ? $safe_nm : '') . "' AND strategy_name='" . (($source !== 'stock_picks') ? $safe_nm : '') . "'");
            $conn->query("INSERT INTO walk_forward_summary (source_table, algorithm_name, strategy_name,
                total_folds, avg_wf_efficiency, avg_oos_win_rate, avg_oos_return,
                avg_is_win_rate, avg_is_return, best_robust_tp, best_robust_sl, best_robust_hold,
                overfitting_flag, updated_at)
                VALUES ('$safe_src', '" . (($source === 'stock_picks') ? $safe_nm : '') . "',
                '" . (($source !== 'stock_picks') ? $safe_nm : '') . "',
                $valid_folds, $avg_wf_eff, $avg_oos_wr, $avg_oos_ret,
                $avg_is_wr, $avg_is_ret, $robust_tp, $robust_sl, $robust_hold,
                " . ($overfitting ? 1 : 0) . ", '$now')");

            $response['stored'] = true;
        }
    }

} elseif ($action === 'validate_all') {
    // ═══════════════════════════════════════════════
    // ACTION: validate_all — Batch validate all algos (GitHub Actions)
    // ═══════════════════════════════════════════════
    if (!$is_admin) {
        $response['ok'] = false;
        $response['error'] = 'Admin key required';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $train_days = isset($_GET['train_days']) ? max(14, min(180, (int)$_GET['train_days'])) : 60;
    $test_days = isset($_GET['test_days']) ? max(7, min(60, (int)$_GET['test_days'])) : 20;
    $max_algos = isset($_GET['limit']) ? max(1, min(20, (int)$_GET['limit'])) : 10;

    $results = array();
    $processed = 0;

    // 1. stock_picks algorithms
    $ar = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE entry_price > 0 ORDER BY algorithm_name LIMIT $max_algos");
    if ($ar) {
        while ($row = $ar->fetch_assoc()) {
            $algo = $row['algorithm_name'];
            $r = _wf_run_validation($conn, 'stock_picks', $algo, $train_days, $test_days);

            $folds = isset($r['folds']) ? $r['folds'] : array();
            $valid = 0;
            $sum_oos_ret = 0;
            $sum_is_ret = 0;
            foreach ($folds as $f) {
                if ($f['oos_trades'] > 0) {
                    $valid++;
                    $sum_oos_ret += $f['oos_avg_return'];
                    $sum_is_ret += $f['is_avg_return'];
                }
            }
            $avg_oos = ($valid > 0) ? round($sum_oos_ret / $valid, 4) : 0;
            $avg_is = ($valid > 0) ? round($sum_is_ret / $valid, 4) : 0;
            $wfe = ($avg_is != 0) ? round($avg_oos / $avg_is, 4) : 0;

            $results[] = array(
                'source' => 'stock_picks',
                'name' => $algo,
                'folds' => $valid,
                'avg_oos_return' => $avg_oos,
                'avg_is_return' => $avg_is,
                'wf_efficiency' => $wfe,
                'overfitting' => ($wfe < 0.5 && $valid >= 2)
            );

            // Store summary
            $safe_src = 'stock_picks';
            $safe_nm = $conn->real_escape_string($algo);
            $now = date('Y-m-d H:i:s');
            $conn->query("REPLACE INTO walk_forward_summary (source_table, algorithm_name, strategy_name,
                total_folds, avg_wf_efficiency, avg_oos_win_rate, avg_oos_return,
                avg_is_win_rate, avg_is_return, overfitting_flag, updated_at)
                VALUES ('$safe_src', '$safe_nm', '', $valid, $wfe, 0, $avg_oos, 0, $avg_is,
                " . (($wfe < 0.5 && $valid >= 2) ? 1 : 0) . ", '$now')");

            $processed++;
        }
    }

    // 2. miracle_picks3 strategies
    $sr = $conn->query("SELECT DISTINCT strategy_name FROM miracle_picks3 WHERE entry_price > 0 AND outcome IN ('won','lost') ORDER BY strategy_name LIMIT $max_algos");
    if ($sr) {
        while ($row = $sr->fetch_assoc()) {
            $strat = $row['strategy_name'];
            $r = _wf_run_validation($conn, 'miracle_picks3', $strat, $train_days, $test_days);

            $folds = isset($r['folds']) ? $r['folds'] : array();
            $valid = 0;
            $sum_oos_ret = 0;
            $sum_is_ret = 0;
            foreach ($folds as $f) {
                if ($f['oos_trades'] > 0) {
                    $valid++;
                    $sum_oos_ret += $f['oos_avg_return'];
                    $sum_is_ret += $f['is_avg_return'];
                }
            }
            $avg_oos = ($valid > 0) ? round($sum_oos_ret / $valid, 4) : 0;
            $avg_is = ($valid > 0) ? round($sum_is_ret / $valid, 4) : 0;
            $wfe = ($avg_is != 0) ? round($avg_oos / $avg_is, 4) : 0;

            $results[] = array(
                'source' => 'miracle_picks3',
                'name' => $strat,
                'folds' => $valid,
                'avg_oos_return' => $avg_oos,
                'avg_is_return' => $avg_is,
                'wf_efficiency' => $wfe,
                'overfitting' => ($wfe < 0.5 && $valid >= 2)
            );

            $safe_nm = $conn->real_escape_string($strat);
            $now = date('Y-m-d H:i:s');
            $conn->query("REPLACE INTO walk_forward_summary (source_table, algorithm_name, strategy_name,
                total_folds, avg_wf_efficiency, avg_oos_win_rate, avg_oos_return,
                avg_is_win_rate, avg_is_return, overfitting_flag, updated_at)
                VALUES ('miracle_picks3', '', '$safe_nm', $valid, $wfe, 0, $avg_oos, 0, $avg_is,
                " . (($wfe < 0.5 && $valid >= 2) ? 1 : 0) . ", '$now')");

            $processed++;
        }
    }

    $response['processed'] = $processed;
    $response['results'] = $results;

    // Sort by WF efficiency descending
    $wfe_arr = array();
    for ($i = 0; $i < count($results); $i++) $wfe_arr[$i] = $results[$i]['wf_efficiency'];
    arsort($wfe_arr);
    $sorted = array();
    foreach ($wfe_arr as $idx => $val) $sorted[] = $results[$idx];
    $response['results'] = $sorted;

    // Count overfitting algos
    $overfit_count = 0;
    foreach ($results as $r) { if ($r['overfitting']) $overfit_count++; }
    $response['overfitting_count'] = $overfit_count;
    $response['robust_count'] = $processed - $overfit_count;

} elseif ($action === 'compare') {
    // ═══════════════════════════════════════════════
    // ACTION: compare — WF results vs naive grid search
    // ═══════════════════════════════════════════════
    $source = isset($_GET['source']) ? trim($_GET['source']) : 'stock_picks';
    $algorithm = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';
    $strategy = isset($_GET['strategy']) ? trim($_GET['strategy']) : '';
    $name = ($source === 'stock_picks') ? $algorithm : $strategy;

    if ($name === '') {
        $response['ok'] = false;
        $response['error'] = 'Missing algorithm or strategy parameter';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    // Naive grid search (all data at once)
    if ($source === 'stock_picks') {
        $safe_nm = $conn->real_escape_string($name);
        $dr = $conn->query("SELECT MIN(pick_date) as min_d, MAX(pick_date) as max_d
                            FROM stock_picks WHERE entry_price>0 AND algorithm_name='$safe_nm'");
    } else {
        $table = ($source === 'miracle_picks3') ? 'miracle_picks3' : 'miracle_picks2';
        $safe_nm = $conn->real_escape_string($name);
        $dr = $conn->query("SELECT MIN(scan_date) as min_d, MAX(scan_date) as max_d
                            FROM $table WHERE entry_price>0 AND outcome IN ('won','lost') AND strategy_name='$safe_nm'");
    }

    $naive_result = array('params' => array(), 'perf' => array(), 'score' => 0);
    if ($dr && $dr->num_rows > 0) {
        $drow = $dr->fetch_assoc();
        if ($drow['min_d'] && $drow['max_d']) {
            $naive_result = _wf_grid_search($conn, $source, $name, $drow['min_d'], $drow['max_d']);
        }
    }

    // Walk-forward results from DB
    $safe_src = $conn->real_escape_string($source);
    $safe_nm2 = $conn->real_escape_string($name);
    $col = ($source === 'stock_picks') ? 'algorithm_name' : 'strategy_name';
    $wf_summary = null;
    $wr = $conn->query("SELECT * FROM walk_forward_summary WHERE source_table='$safe_src' AND $col='$safe_nm2' LIMIT 1");
    if ($wr && $wr->num_rows > 0) {
        $wf_summary = $wr->fetch_assoc();
    }

    $response['source'] = $source;
    $response['name'] = $name;
    $response['naive_grid_search'] = array(
        'best_params' => $naive_result['params'],
        'performance' => $naive_result['perf'],
        'score' => $naive_result['score'],
        'note' => 'Optimized on ALL data at once (in-sample only, overfitting risk)'
    );
    $response['walk_forward'] = $wf_summary ? array(
        'robust_params' => array('tp' => (float)$wf_summary['best_robust_tp'], 'sl' => (float)$wf_summary['best_robust_sl'], 'hold' => (int)$wf_summary['best_robust_hold']),
        'avg_oos_return' => (float)$wf_summary['avg_oos_return'],
        'avg_is_return' => (float)$wf_summary['avg_is_return'],
        'wf_efficiency' => (float)$wf_summary['avg_wf_efficiency'],
        'overfitting_flag' => (int)$wf_summary['overfitting_flag'],
        'folds' => (int)$wf_summary['total_folds'],
        'note' => 'Out-of-sample validated (robust params)'
    ) : array('note' => 'No walk-forward results yet. Run validate first.');

    $response['recommendation'] = $wf_summary ? (
        (int)$wf_summary['overfitting_flag']
            ? 'WARNING: Naive grid search is likely overfitting. Use walk-forward robust params instead.'
            : 'Grid search params appear robust (WF efficiency >= 0.5). Either params set is acceptable.'
    ) : 'Run walk-forward validation first to compare.';

} elseif ($action === 'results') {
    // ═══════════════════════════════════════════════
    // ACTION: results — Fetch stored walk-forward results
    // ═══════════════════════════════════════════════
    $source = isset($_GET['source']) ? trim($_GET['source']) : '';

    $where = '';
    if ($source !== '') {
        $where = " WHERE source_table='" . $conn->real_escape_string($source) . "'";
    }

    $summaries = array();
    $sr = $conn->query("SELECT * FROM walk_forward_summary $where ORDER BY avg_wf_efficiency DESC");
    if ($sr) {
        while ($row = $sr->fetch_assoc()) {
            $row['overfitting_flag'] = (int)$row['overfitting_flag'];
            $row['avg_wf_efficiency'] = (float)$row['avg_wf_efficiency'];
            $row['avg_oos_return'] = (float)$row['avg_oos_return'];
            $row['avg_is_return'] = (float)$row['avg_is_return'];
            $summaries[] = $row;
        }
    }

    $response['summaries'] = $summaries;
    $response['count'] = count($summaries);
    $overfit = 0;
    foreach ($summaries as $s) { if ($s['overfitting_flag']) $overfit++; }
    $response['overfitting_count'] = $overfit;
    $response['robust_count'] = count($summaries) - $overfit;
}

echo json_encode($response);
$conn->close();
