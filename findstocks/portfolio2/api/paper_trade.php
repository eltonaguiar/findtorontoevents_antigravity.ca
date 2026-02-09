<?php
/**
 * Live Out-of-Sample Paper Trading Engine
 * Records picks BEFORE outcomes are known, then resolves daily.
 * Creates a verifiable, uncontaminated forward-looking track record.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   enter      — Snapshot today's top picks as new paper trades
 *   track      — Update all open paper trades with latest prices
 *   dashboard  — Full paper trading performance dashboard
 *   compare    — Compare paper OOS results vs backtest predictions
 *   positions  — List open positions
 *   equity     — Equity curve data
 *
 * Usage:
 *   GET .../paper_trade.php?action=enter&key=stocksrefresh2026
 *   GET .../paper_trade.php?action=track&key=stocksrefresh2026
 *   GET .../paper_trade.php?action=dashboard
 *   GET .../paper_trade.php?action=compare
 *   GET .../paper_trade.php?action=positions
 *   GET .../paper_trade.php?action=equity
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'dashboard';
$response = array('ok' => true, 'action' => $action);
$admin_key = 'stocksrefresh2026';
$is_admin = (isset($_GET['key']) && $_GET['key'] === $admin_key);

// ═══════════════════════════════════════════════
// Auto-create tables
// ═══════════════════════════════════════════════
$conn->query("CREATE TABLE IF NOT EXISTS paper_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    enter_date DATE NOT NULL,
    ticker VARCHAR(10) NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL DEFAULT '',
    source_table VARCHAR(30) NOT NULL DEFAULT '',
    entry_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    target_tp_pct DECIMAL(6,2) NOT NULL DEFAULT 5,
    target_sl_pct DECIMAL(6,2) NOT NULL DEFAULT 3,
    max_hold_days INT NOT NULL DEFAULT 7,
    position_size_pct DECIMAL(6,2) NOT NULL DEFAULT 10,
    kelly_fraction DECIMAL(8,4) NOT NULL DEFAULT 0,
    regime_at_entry VARCHAR(20) NOT NULL DEFAULT '',
    score INT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    current_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    unrealized_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    exit_date DATE,
    exit_price DECIMAL(12,4) NOT NULL DEFAULT 0,
    exit_reason VARCHAR(50) NOT NULL DEFAULT '',
    return_pct DECIMAL(10,4) NOT NULL DEFAULT 0,
    hold_days INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    resolved_at DATETIME,
    KEY idx_status (status),
    KEY idx_date (enter_date),
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS paper_portfolio_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    open_positions INT NOT NULL DEFAULT 0,
    total_invested DECIMAL(12,2) NOT NULL DEFAULT 0,
    unrealized_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    realized_pnl_today DECIMAL(12,2) NOT NULL DEFAULT 0,
    cumulative_realized_pnl DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_trades INT NOT NULL DEFAULT 0,
    total_wins INT NOT NULL DEFAULT 0,
    total_losses INT NOT NULL DEFAULT 0,
    win_rate_to_date DECIMAL(5,2) NOT NULL DEFAULT 0,
    peak_equity DECIMAL(12,2) NOT NULL DEFAULT 0,
    current_drawdown_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    max_drawdown_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    regime VARCHAR(20) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_date (snapshot_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ═══════════════════════════════════════════════
// Helper: Get current regime
// ═══════════════════════════════════════════════
function _pt_get_regime($conn) {
    $r = $conn->query("SELECT regime FROM market_regimes ORDER BY trade_date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        return $row['regime'] ? $row['regime'] : 'unknown';
    }
    return 'unknown';
}

// ═══════════════════════════════════════════════
// Helper: Get Kelly fraction for an algorithm
// ═══════════════════════════════════════════════
function _pt_get_kelly($conn, $source, $algo) {
    $safe_src = $conn->real_escape_string($source);
    $safe_algo = $conn->real_escape_string($algo);
    $r = $conn->query("SELECT recommended_pct FROM kelly_sizing_log
                        WHERE source_table='$safe_src' AND algorithm_name='$safe_algo'
                        ORDER BY calc_date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        return (float)$row['recommended_pct'];
    }
    return 0.10; // default 10%
}

// ═══════════════════════════════════════════════
// Helper: Get latest price for a ticker
// ═══════════════════════════════════════════════
function _pt_get_price($conn, $ticker) {
    $safe = $conn->real_escape_string($ticker);
    $r = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$safe' ORDER BY trade_date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        return (float)$row['close_price'];
    }
    return 0;
}

// ═══════════════════════════════════════════════
// ACTION: enter — Record today's top picks as paper trades
// ═══════════════════════════════════════════════
if ($action === 'enter') {
    if (!$is_admin) {
        $response['ok'] = false;
        $response['error'] = 'Admin key required';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $today = date('Y-m-d');
    $now = date('Y-m-d H:i:s');
    $max_positions = isset($_GET['max_pos']) ? max(1, min(10, (int)$_GET['max_pos'])) : 5;

    // Check how many open positions we already have
    $open_r = $conn->query("SELECT COUNT(*) as cnt FROM paper_trades WHERE status='open'");
    $open_count = ($open_r && $open_r->num_rows > 0) ? (int)$open_r->fetch_assoc() : 0;
    if (is_array($open_count)) $open_count = (int)$open_count['cnt'];

    // Don't enter if we already maxed out
    $slots_available = $max_positions - $open_count;
    if ($slots_available <= 0) {
        $response['entered'] = 0;
        $response['message'] = 'Max positions reached (' . $open_count . '/' . $max_positions . ')';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    // Check if we already entered trades today
    $today_r = $conn->query("SELECT COUNT(*) as cnt FROM paper_trades WHERE enter_date='$today'");
    $today_count = ($today_r && $today_r->num_rows > 0) ? (int)$today_r->fetch_assoc() : 0;
    if (is_array($today_count)) $today_count = (int)$today_count['cnt'];
    if ($today_count > 0) {
        $response['entered'] = 0;
        $response['message'] = 'Already entered ' . $today_count . ' trades today';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $regime = _pt_get_regime($conn);

    // Gather top picks from all sources
    $picks = array();

    // stock_picks (today or yesterday)
    $sp = $conn->query("SELECT ticker, algorithm_name, entry_price, score, 'stock_picks' AS src
                         FROM stock_picks
                         WHERE pick_date >= DATE_SUB('$today', INTERVAL 1 DAY) AND entry_price > 0
                         ORDER BY score DESC LIMIT 15");
    if ($sp) { while ($row = $sp->fetch_assoc()) $picks[] = $row; }

    // miracle_picks3
    $mp3 = $conn->query("SELECT ticker, strategy_name AS algorithm_name, entry_price, score,
                                 take_profit_pct, stop_loss_pct, 'miracle_picks3' AS src
                          FROM miracle_picks3
                          WHERE scan_date >= DATE_SUB('$today', INTERVAL 1 DAY) AND entry_price > 0 AND outcome='pending'
                          ORDER BY score DESC LIMIT 15");
    if ($mp3) { while ($row = $mp3->fetch_assoc()) $picks[] = $row; }

    // Deduplicate by ticker
    $seen = array();
    $unique = array();
    foreach ($picks as $p) {
        $t = strtoupper(trim($p['ticker']));
        if (isset($seen[$t])) continue;

        // Skip if already have open position in this ticker
        $safe_t = $conn->real_escape_string($t);
        $ex = $conn->query("SELECT id FROM paper_trades WHERE ticker='$safe_t' AND status='open' LIMIT 1");
        if ($ex && $ex->num_rows > 0) continue;

        $seen[$t] = true;
        $unique[] = $p;
    }

    // Sort by score desc
    $scores = array();
    for ($i = 0; $i < count($unique); $i++) $scores[$i] = (int)$unique[$i]['score'];
    arsort($scores);

    $entered = 0;
    $trades_entered = array();
    foreach ($scores as $idx => $sc) {
        if ($entered >= $slots_available) break;
        $p = $unique[$idx];
        $ticker = strtoupper(trim($p['ticker']));
        $algo = $p['algorithm_name'];
        $src = $p['src'];
        $entry_price = (float)$p['entry_price'];
        $score = (int)$p['score'];

        // Get TP/SL from walk-forward robust params, or from pick itself, or defaults
        $tp = 5;
        $sl = 3;
        $hold = 7;
        if (isset($p['take_profit_pct']) && (float)$p['take_profit_pct'] > 0) {
            $tp = (float)$p['take_profit_pct'];
        }
        if (isset($p['stop_loss_pct']) && (float)$p['stop_loss_pct'] > 0) {
            $sl = (float)$p['stop_loss_pct'];
        }

        // Try walk-forward robust params
        $safe_algo = $conn->real_escape_string($algo);
        $col = ($src === 'stock_picks') ? 'algorithm_name' : 'strategy_name';
        $wf = $conn->query("SELECT best_robust_tp, best_robust_sl, best_robust_hold FROM walk_forward_summary
                            WHERE source_table='" . $conn->real_escape_string($src) . "' AND $col='$safe_algo' LIMIT 1");
        if ($wf && $wf->num_rows > 0) {
            $wfrow = $wf->fetch_assoc();
            if ((float)$wfrow['best_robust_tp'] > 0) $tp = (float)$wfrow['best_robust_tp'];
            if ((float)$wfrow['best_robust_sl'] > 0) $sl = (float)$wfrow['best_robust_sl'];
            if ((int)$wfrow['best_robust_hold'] > 0) $hold = (int)$wfrow['best_robust_hold'];
        }

        $kelly = _pt_get_kelly($conn, $src, $algo);

        $safe_ticker = $conn->real_escape_string($ticker);
        $safe_algo2 = $conn->real_escape_string($algo);
        $safe_src2 = $conn->real_escape_string($src);
        $safe_regime = $conn->real_escape_string($regime);

        $conn->query("INSERT INTO paper_trades
            (enter_date, ticker, algorithm_name, source_table, entry_price,
             target_tp_pct, target_sl_pct, max_hold_days,
             position_size_pct, kelly_fraction, regime_at_entry, score, status, created_at)
            VALUES ('$today', '$safe_ticker', '$safe_algo2', '$safe_src2', $entry_price,
                    $tp, $sl, $hold,
                    " . round($kelly * 100, 2) . ", $kelly, '$safe_regime', $score, 'open', '$now')");

        $trades_entered[] = array('ticker' => $ticker, 'algorithm' => $algo, 'entry_price' => $entry_price, 'tp' => $tp, 'sl' => $sl, 'hold' => $hold, 'kelly_pct' => round($kelly * 100, 1));
        $entered++;
    }

    $response['entered'] = $entered;
    $response['trades'] = $trades_entered;
    $response['regime'] = $regime;
    $response['date'] = $today;

} elseif ($action === 'track') {
    // ═══════════════════════════════════════════════
    // ACTION: track — Update open paper trades with latest prices
    // ═══════════════════════════════════════════════
    if (!$is_admin) {
        $response['ok'] = false;
        $response['error'] = 'Admin key required';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $today = date('Y-m-d');
    $now = date('Y-m-d H:i:s');

    // Get all open positions
    $open = $conn->query("SELECT * FROM paper_trades WHERE status='open' ORDER BY enter_date ASC");
    if (!$open || $open->num_rows === 0) {
        $response['tracked'] = 0;
        $response['message'] = 'No open positions';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $tracked = 0;
    $closed = 0;
    $close_reasons = array('take_profit' => 0, 'stop_loss' => 0, 'max_hold' => 0);
    $realized_today = 0;

    while ($trade = $open->fetch_assoc()) {
        $id = (int)$trade['id'];
        $ticker = $trade['ticker'];
        $entry = (float)$trade['entry_price'];
        $tp_pct = (float)$trade['target_tp_pct'];
        $sl_pct = (float)$trade['target_sl_pct'];
        $max_hold = (int)$trade['max_hold_days'];
        $enter_date = $trade['enter_date'];

        // Get latest price
        $latest = _pt_get_price($conn, $ticker);
        if ($latest <= 0) {
            $tracked++;
            continue;
        }

        // Calculate return
        $ret_pct = round((($latest - $entry) / $entry) * 100, 4);
        $hold_days = (int)((strtotime($today) - strtotime($enter_date)) / 86400);

        // Check exit conditions
        $exit_reason = '';
        $exit_price = 0;
        $final_ret = $ret_pct;

        // Check daily OHLC for TP/SL hits (more accurate)
        $safe_t = $conn->real_escape_string($ticker);
        $safe_d = $conn->real_escape_string($enter_date);
        $ohlc = $conn->query("SELECT high_price, low_price, close_price, trade_date FROM daily_prices
                              WHERE ticker='$safe_t' AND trade_date > '$safe_d'
                              ORDER BY trade_date ASC LIMIT " . ($max_hold + 3));

        $dc = 0;
        $hit = false;
        if ($ohlc && $ohlc->num_rows > 0) {
            while ($d = $ohlc->fetch_assoc()) {
                $dc++;
                $dh = (float)$d['high_price'];
                $dl = (float)$d['low_price'];
                $dclose = (float)$d['close_price'];
                $tp_price = $entry * (1 + $tp_pct / 100);
                $sl_price = $entry * (1 - $sl_pct / 100);

                if ($dl > 0 && $dl <= $sl_price) {
                    $exit_reason = 'stop_loss';
                    $exit_price = $sl_price;
                    $final_ret = -$sl_pct;
                    $hit = true;
                    break;
                }
                if ($dh > 0 && $dh >= $tp_price) {
                    $exit_reason = 'take_profit';
                    $exit_price = $tp_price;
                    $final_ret = $tp_pct;
                    $hit = true;
                    break;
                }
                if ($dc >= $max_hold) {
                    $exit_reason = 'max_hold';
                    $exit_price = $dclose;
                    $final_ret = round((($dclose - $entry) / $entry) * 100, 4);
                    $hit = true;
                    break;
                }
            }
        }

        if ($hit && $exit_reason !== '') {
            // Close the position
            $safe_reason = $conn->real_escape_string($exit_reason);
            $conn->query("UPDATE paper_trades SET
                status='closed', exit_date='$today', exit_price=$exit_price,
                exit_reason='$safe_reason', return_pct=$final_ret, hold_days=$dc,
                current_price=$exit_price, unrealized_pct=0, resolved_at='$now'
                WHERE id=$id");
            $closed++;
            $close_reasons[$exit_reason]++;
            $realized_today += $final_ret;
        } else {
            // Update unrealized P&L
            $conn->query("UPDATE paper_trades SET
                current_price=$latest, unrealized_pct=$ret_pct, hold_days=$hold_days
                WHERE id=$id");
        }
        $tracked++;
    }

    // Take daily snapshot
    $total_trades_r = $conn->query("SELECT COUNT(*) as cnt FROM paper_trades WHERE status='closed'");
    $total_trades = ($total_trades_r && $total_trades_r->num_rows > 0) ? (int)$total_trades_r->fetch_assoc() : 0;
    if (is_array($total_trades)) $total_trades = (int)$total_trades['cnt'];

    $wins_r = $conn->query("SELECT COUNT(*) as cnt FROM paper_trades WHERE status='closed' AND return_pct > 0");
    $total_wins = ($wins_r && $wins_r->num_rows > 0) ? (int)$wins_r->fetch_assoc() : 0;
    if (is_array($total_wins)) $total_wins = (int)$total_wins['cnt'];

    $total_losses = $total_trades - $total_wins;
    $wr = ($total_trades > 0) ? round($total_wins / $total_trades * 100, 2) : 0;

    // Cumulative realized PnL
    $cum_r = $conn->query("SELECT SUM(return_pct) as total FROM paper_trades WHERE status='closed'");
    $cum_pnl = ($cum_r && $cum_r->num_rows > 0) ? (float)$cum_r->fetch_assoc() : 0;
    if (is_array($cum_pnl)) $cum_pnl = (float)$cum_pnl['total'];

    // Open positions unrealized
    $ur = $conn->query("SELECT COUNT(*) as cnt, SUM(unrealized_pct) as total FROM paper_trades WHERE status='open'");
    $open_info = ($ur && $ur->num_rows > 0) ? $ur->fetch_assoc() : array('cnt' => 0, 'total' => 0);
    $open_count = (int)$open_info['cnt'];
    $unrealized = (float)$open_info['total'];

    // Peak and drawdown
    $peak_r = $conn->query("SELECT MAX(cumulative_realized_pnl) as peak FROM paper_portfolio_daily");
    $prev_peak = ($peak_r && $peak_r->num_rows > 0) ? (float)$peak_r->fetch_assoc() : 0;
    if (is_array($prev_peak)) $prev_peak = (float)$prev_peak['peak'];
    $peak = max($prev_peak, $cum_pnl);
    $drawdown = ($peak > 0) ? round((($cum_pnl - $peak) / $peak) * 100, 4) : 0;

    $max_dd_r = $conn->query("SELECT MIN(current_drawdown_pct) as mdd FROM paper_portfolio_daily");
    $prev_max_dd = ($max_dd_r && $max_dd_r->num_rows > 0) ? (float)$max_dd_r->fetch_assoc() : 0;
    if (is_array($prev_max_dd)) $prev_max_dd = (float)$prev_max_dd['mdd'];
    $max_dd = min($prev_max_dd, $drawdown);

    $regime = _pt_get_regime($conn);

    $conn->query("REPLACE INTO paper_portfolio_daily
        (snapshot_date, open_positions, total_invested, unrealized_pnl,
         realized_pnl_today, cumulative_realized_pnl,
         total_trades, total_wins, total_losses, win_rate_to_date,
         peak_equity, current_drawdown_pct, max_drawdown_pct, regime, created_at)
        VALUES ('$today', $open_count, 0, $unrealized,
                $realized_today, $cum_pnl,
                $total_trades, $total_wins, $total_losses, $wr,
                $peak, $drawdown, $max_dd, '" . $conn->real_escape_string($regime) . "', '$now')");

    $response['tracked'] = $tracked;
    $response['closed'] = $closed;
    $response['close_reasons'] = $close_reasons;
    $response['open_positions'] = $open_count;
    $response['win_rate'] = $wr;
    $response['cumulative_pnl_pct'] = round($cum_pnl, 2);

} elseif ($action === 'dashboard') {
    // ═══════════════════════════════════════════════
    // ACTION: dashboard — Full paper trading performance
    // ═══════════════════════════════════════════════

    // Overall stats
    $total_r = $conn->query("SELECT COUNT(*) as total,
                              SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) as closed,
                              SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_pos,
                              SUM(CASE WHEN status='closed' AND return_pct > 0 THEN 1 ELSE 0 END) as wins,
                              SUM(CASE WHEN status='closed' AND return_pct <= 0 THEN 1 ELSE 0 END) as losses,
                              AVG(CASE WHEN status='closed' THEN return_pct END) as avg_return,
                              AVG(CASE WHEN status='closed' AND return_pct > 0 THEN return_pct END) as avg_win,
                              AVG(CASE WHEN status='closed' AND return_pct <= 0 THEN return_pct END) as avg_loss,
                              SUM(CASE WHEN status='closed' THEN return_pct END) as total_return,
                              AVG(CASE WHEN status='closed' THEN hold_days END) as avg_hold
                             FROM paper_trades");

    $stats = array();
    if ($total_r && $total_r->num_rows > 0) {
        $row = $total_r->fetch_assoc();
        $total_closed = (int)$row['closed'];
        $wins = (int)$row['wins'];
        $losses = (int)$row['losses'];
        $avg_win = (float)$row['avg_win'];
        $avg_loss = abs((float)$row['avg_loss']);
        $pf = ($avg_loss > 0 && $losses > 0) ? round(($avg_win * $wins) / ($avg_loss * $losses), 4) : 0;

        $stats = array(
            'total_trades' => (int)$row['total'],
            'closed' => $total_closed,
            'open' => (int)$row['open_pos'],
            'wins' => $wins,
            'losses' => $losses,
            'win_rate' => ($total_closed > 0) ? round($wins / $total_closed * 100, 2) : 0,
            'avg_return' => round((float)$row['avg_return'], 4),
            'avg_win' => round($avg_win, 4),
            'avg_loss' => round((float)$row['avg_loss'], 4),
            'total_return_pct' => round((float)$row['total_return'], 2),
            'profit_factor' => $pf,
            'avg_hold_days' => round((float)$row['avg_hold'], 1)
        );
    }

    // By algorithm breakdown
    $algo_stats = array();
    $ar = $conn->query("SELECT algorithm_name, source_table,
                         COUNT(*) as trades,
                         SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) as wins,
                         AVG(return_pct) as avg_ret,
                         SUM(return_pct) as total_ret
                        FROM paper_trades WHERE status='closed'
                        GROUP BY algorithm_name, source_table
                        ORDER BY total_ret DESC");
    if ($ar) {
        while ($row = $ar->fetch_assoc()) {
            $row['trades'] = (int)$row['trades'];
            $row['wins'] = (int)$row['wins'];
            $row['win_rate'] = round($row['wins'] / max(1, $row['trades']) * 100, 2);
            $row['avg_ret'] = round((float)$row['avg_ret'], 4);
            $row['total_ret'] = round((float)$row['total_ret'], 2);
            $algo_stats[] = $row;
        }
    }

    // Latest snapshot
    $snap = null;
    $sr = $conn->query("SELECT * FROM paper_portfolio_daily ORDER BY snapshot_date DESC LIMIT 1");
    if ($sr && $sr->num_rows > 0) {
        $snap = $sr->fetch_assoc();
    }

    // Open positions
    $open_pos = array();
    $opr = $conn->query("SELECT ticker, algorithm_name, entry_price, current_price, unrealized_pct,
                                 enter_date, hold_days, target_tp_pct, target_sl_pct, score
                          FROM paper_trades WHERE status='open' ORDER BY unrealized_pct DESC");
    if ($opr) {
        while ($row = $opr->fetch_assoc()) {
            $row['unrealized_pct'] = round((float)$row['unrealized_pct'], 2);
            $open_pos[] = $row;
        }
    }

    $response['stats'] = $stats;
    $response['by_algorithm'] = $algo_stats;
    $response['latest_snapshot'] = $snap;
    $response['open_positions'] = $open_pos;
    $response['days_tracking'] = 0;
    $dr = $conn->query("SELECT DATEDIFF(MAX(enter_date), MIN(enter_date)) as days FROM paper_trades");
    if ($dr && $dr->num_rows > 0) {
        $drow = $dr->fetch_assoc();
        $response['days_tracking'] = (int)$drow['days'];
    }

} elseif ($action === 'compare') {
    // ═══════════════════════════════════════════════
    // ACTION: compare — Paper OOS vs backtest predictions
    // ═══════════════════════════════════════════════

    // Paper trading actual results
    $paper = array('win_rate' => 0, 'avg_return' => 0, 'trades' => 0);
    $pr = $conn->query("SELECT COUNT(*) as cnt,
                         AVG(return_pct) as avg_ret,
                         SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) as wins
                        FROM paper_trades WHERE status='closed'");
    if ($pr && $pr->num_rows > 0) {
        $row = $pr->fetch_assoc();
        $cnt = (int)$row['cnt'];
        $paper = array(
            'win_rate' => ($cnt > 0) ? round((int)$row['wins'] / $cnt * 100, 2) : 0,
            'avg_return' => round((float)$row['avg_ret'], 4),
            'trades' => $cnt
        );
    }

    // Backtest predictions (from backtest_results — latest run)
    $backtest = array('win_rate' => 0, 'avg_return' => 0);
    $br = $conn->query("SELECT win_rate, total_return_pct, total_trades
                         FROM backtest_results ORDER BY id DESC LIMIT 1");
    if ($br && $br->num_rows > 0) {
        $row = $br->fetch_assoc();
        $bt_trades = (int)$row['total_trades'];
        $backtest = array(
            'win_rate' => (float)$row['win_rate'],
            'avg_return' => ($bt_trades > 0) ? round((float)$row['total_return_pct'] / $bt_trades, 4) : 0,
            'total_trades' => $bt_trades
        );
    }

    $response['paper_trading'] = $paper;
    $response['backtest'] = $backtest;
    $response['gap'] = array(
        'win_rate_gap' => round($paper['win_rate'] - $backtest['win_rate'], 2),
        'return_gap' => round($paper['avg_return'] - $backtest['avg_return'], 4)
    );
    $response['interpretation'] = ($paper['trades'] < 10)
        ? 'Not enough paper trades yet (need 10+). Keep running for 2-4 weeks.'
        : (($paper['win_rate'] < $backtest['win_rate'] - 10)
            ? 'Paper trading significantly underperforms backtest. Likely overfitting in backtests.'
            : 'Paper trading results are within range of backtest predictions.');

} elseif ($action === 'positions') {
    // ═══════════════════════════════════════════════
    // ACTION: positions — List open positions
    // ═══════════════════════════════════════════════
    $status = isset($_GET['status']) ? trim($_GET['status']) : 'open';
    $safe_status = $conn->real_escape_string($status);
    $limit = isset($_GET['limit']) ? max(1, min(200, (int)$_GET['limit'])) : 50;

    $positions = array();
    $pr = $conn->query("SELECT * FROM paper_trades WHERE status='$safe_status' ORDER BY enter_date DESC LIMIT $limit");
    if ($pr) {
        while ($row = $pr->fetch_assoc()) {
            $row['return_pct'] = round((float)$row['return_pct'], 4);
            $row['unrealized_pct'] = round((float)$row['unrealized_pct'], 4);
            $positions[] = $row;
        }
    }

    $response['positions'] = $positions;
    $response['count'] = count($positions);

} elseif ($action === 'equity') {
    // ═══════════════════════════════════════════════
    // ACTION: equity — Equity curve data
    // ═══════════════════════════════════════════════
    $limit = isset($_GET['limit']) ? max(1, min(365, (int)$_GET['limit'])) : 90;

    $curve = array();
    $cr = $conn->query("SELECT snapshot_date, cumulative_realized_pnl, unrealized_pnl,
                                win_rate_to_date, current_drawdown_pct, max_drawdown_pct,
                                open_positions, total_trades, regime
                         FROM paper_portfolio_daily
                         ORDER BY snapshot_date ASC LIMIT $limit");
    if ($cr) {
        while ($row = $cr->fetch_assoc()) {
            $row['cumulative_realized_pnl'] = round((float)$row['cumulative_realized_pnl'], 2);
            $row['unrealized_pnl'] = round((float)$row['unrealized_pnl'], 2);
            $curve[] = $row;
        }
    }

    $response['equity_curve'] = $curve;
    $response['data_points'] = count($curve);
}

echo json_encode($response);
$conn->close();
