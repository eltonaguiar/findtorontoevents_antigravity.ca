<?php
/**
 * DayTrades Miracle Claude — Dashboard & Stats API
 * Strategy leaderboard, win rates, P&L tracking.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET .../dashboard2.php                      — full dashboard stats
 *   GET .../dashboard2.php?action=leaderboard   — strategy leaderboard
 *   GET .../dashboard2.php?action=summary       — overall summary
 *   GET .../dashboard2.php?action=portfolios    — portfolio performance
 *   GET .../dashboard2.php?action=recent        — last 20 resolved picks
 *   GET .../dashboard2.php?action=streaks       — win/loss streak tracking
 *   GET .../dashboard2.php?action=best_worst    — best and worst picks all time
 */
require_once dirname(__FILE__) . '/db_connect2.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'summary';

$output = array('ok' => true);

if ($action === 'summary' || $action === 'full') {
    // Overall stats
    $total = 0;
    $res = $conn->query("SELECT COUNT(*) as c FROM miracle_picks2");
    if ($res) { $r = $res->fetch_assoc(); $total = (int)$r['c']; }

    $today_count = 0;
    $res = $conn->query("SELECT COUNT(*) as c FROM miracle_picks2 WHERE scan_date = CURDATE()");
    if ($res) { $r = $res->fetch_assoc(); $today_count = (int)$r['c']; }

    $winners = 0;
    $res = $conn->query("SELECT COUNT(*) as c FROM miracle_picks2 WHERE outcome='winner'");
    if ($res) { $r = $res->fetch_assoc(); $winners = (int)$r['c']; }

    $losers = 0;
    $res = $conn->query("SELECT COUNT(*) as c FROM miracle_picks2 WHERE outcome='loser'");
    if ($res) { $r = $res->fetch_assoc(); $losers = (int)$r['c']; }

    $expired = 0;
    $res = $conn->query("SELECT COUNT(*) as c FROM miracle_picks2 WHERE outcome='expired'");
    if ($res) { $r = $res->fetch_assoc(); $expired = (int)$r['c']; }

    $pending = 0;
    $res = $conn->query("SELECT COUNT(*) as c FROM miracle_picks2 WHERE outcome='pending'");
    if ($res) { $r = $res->fetch_assoc(); $pending = (int)$r['c']; }

    $resolved = $winners + $losers + $expired;
    $win_rate = ($resolved > 0) ? round(($winners / $resolved) * 100, 2) : 0;

    $avg_gain = 0;
    $res = $conn->query("SELECT AVG(outcome_pct) as a FROM miracle_picks2 WHERE outcome='winner'");
    if ($res) { $r = $res->fetch_assoc(); $avg_gain = round((float)$r['a'], 4); }

    $avg_loss = 0;
    $res = $conn->query("SELECT AVG(outcome_pct) as a FROM miracle_picks2 WHERE outcome='loser'");
    if ($res) { $r = $res->fetch_assoc(); $avg_loss = round((float)$r['a'], 4); }

    $total_pnl = 0;
    $res = $conn->query("SELECT SUM(outcome_pct) as s FROM miracle_picks2 WHERE outcome IN ('winner','loser','expired')");
    if ($res) { $r = $res->fetch_assoc(); $total_pnl = round((float)$r['s'], 4); }

    // Profit factor
    $gross_wins = 0;
    $res = $conn->query("SELECT SUM(outcome_pct) as s FROM miracle_picks2 WHERE outcome='winner'");
    if ($res) { $r = $res->fetch_assoc(); $gross_wins = (float)$r['s']; }
    $gross_losses = 0;
    $res = $conn->query("SELECT SUM(ABS(outcome_pct)) as s FROM miracle_picks2 WHERE outcome='loser'");
    if ($res) { $r = $res->fetch_assoc(); $gross_losses = (float)$r['s']; }
    $profit_factor = ($gross_losses > 0) ? round($gross_wins / $gross_losses, 4) : 0;

    // Expectancy
    $expectancy = 0;
    if ($resolved > 0) {
        $w_rate = $winners / $resolved;
        $l_rate = $losers / $resolved;
        $expectancy = round(($w_rate * $avg_gain) - ($l_rate * abs($avg_loss)), 4);
    }

    // CDR vs non-CDR performance
    $cdr_wins = 0;
    $cdr_total = 0;
    $res = $conn->query("SELECT COUNT(*) as c FROM miracle_picks2 WHERE is_cdr=1 AND outcome IN ('winner','loser','expired')");
    if ($res) { $r = $res->fetch_assoc(); $cdr_total = (int)$r['c']; }
    $res = $conn->query("SELECT COUNT(*) as c FROM miracle_picks2 WHERE is_cdr=1 AND outcome='winner'");
    if ($res) { $r = $res->fetch_assoc(); $cdr_wins = (int)$r['c']; }
    $cdr_win_rate = ($cdr_total > 0) ? round(($cdr_wins / $cdr_total) * 100, 2) : 0;

    $output['summary'] = array(
        'total_picks'    => $total,
        'today_picks'    => $today_count,
        'winners'        => $winners,
        'losers'         => $losers,
        'expired'        => $expired,
        'pending'        => $pending,
        'resolved'       => $resolved,
        'win_rate'       => $win_rate,
        'avg_gain_pct'   => $avg_gain,
        'avg_loss_pct'   => $avg_loss,
        'total_pnl_pct'  => $total_pnl,
        'profit_factor'  => $profit_factor,
        'expectancy'     => $expectancy,
        'cdr_win_rate'   => $cdr_win_rate,
        'cdr_resolved'   => $cdr_total
    );
}

if ($action === 'leaderboard' || $action === 'full') {
    // Per-strategy performance
    $sql = "SELECT strategy_name,
                   COUNT(*) as total,
                   SUM(CASE WHEN outcome='winner' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN outcome='loser' THEN 1 ELSE 0 END) as losses,
                   SUM(CASE WHEN outcome='expired' THEN 1 ELSE 0 END) as expired,
                   SUM(CASE WHEN outcome='pending' THEN 1 ELSE 0 END) as pending,
                   AVG(score) as avg_score,
                   AVG(CASE WHEN outcome='winner' THEN outcome_pct ELSE NULL END) as avg_win,
                   AVG(CASE WHEN outcome='loser' THEN outcome_pct ELSE NULL END) as avg_loss,
                   SUM(CASE WHEN outcome IN ('winner','loser','expired') THEN outcome_pct ELSE 0 END) as total_pnl,
                   AVG(risk_reward_ratio) as avg_rr,
                   AVG(questrade_fee) as avg_fee
            FROM miracle_picks2
            GROUP BY strategy_name
            ORDER BY wins DESC, avg_score DESC";
    $res = $conn->query($sql);
    $leaderboard = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $resolved = (int)$row['wins'] + (int)$row['losses'] + (int)$row['expired'];
            $row['win_rate'] = ($resolved > 0) ? round(((int)$row['wins'] / $resolved) * 100, 2) : 0;
            $row['avg_score'] = round((float)$row['avg_score'], 1);
            $row['avg_win'] = round((float)$row['avg_win'], 4);
            $row['avg_loss'] = round((float)$row['avg_loss'], 4);
            $row['total_pnl'] = round((float)$row['total_pnl'], 4);
            $row['avg_rr'] = round((float)$row['avg_rr'], 2);
            $row['avg_fee'] = round((float)$row['avg_fee'], 2);
            $leaderboard[] = $row;
        }
    }
    $output['leaderboard'] = $leaderboard;
}

if ($action === 'portfolios' || $action === 'full') {
    $res = $conn->query("SELECT * FROM miracle_portfolios2 ORDER BY name");
    $portfolios = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $portfolios[] = $row;
        }
    }
    $output['portfolios'] = $portfolios;
}

if ($action === 'recent' || $action === 'full') {
    $res = $conn->query("SELECT * FROM miracle_picks2 WHERE outcome != 'pending' ORDER BY outcome_date DESC, id DESC LIMIT 20");
    $recent = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $row['signals_json'] = json_decode($row['signals_json'], true);
            $recent[] = $row;
        }
    }
    $output['recent'] = $recent;
}

if ($action === 'best_worst' || $action === 'full') {
    // Top 10 best picks
    $best = array();
    $res = $conn->query("SELECT ticker, strategy_name, scan_date, entry_price, outcome_price, outcome_pct, outcome FROM miracle_picks2 WHERE outcome='winner' ORDER BY outcome_pct DESC LIMIT 10");
    if ($res) { while ($row = $res->fetch_assoc()) $best[] = $row; }

    // Top 10 worst picks
    $worst = array();
    $res = $conn->query("SELECT ticker, strategy_name, scan_date, entry_price, outcome_price, outcome_pct, outcome FROM miracle_picks2 WHERE outcome IN ('loser','expired') ORDER BY outcome_pct ASC LIMIT 10");
    if ($res) { while ($row = $res->fetch_assoc()) $worst[] = $row; }

    $output['best_picks'] = $best;
    $output['worst_picks'] = $worst;
}

if ($action === 'streaks' || $action === 'full') {
    // Calculate current win/loss streak
    $res = $conn->query("SELECT outcome FROM miracle_picks2 WHERE outcome IN ('winner','loser') ORDER BY outcome_date DESC, id DESC LIMIT 50");
    $streak_type = '';
    $streak_count = 0;
    $max_win_streak = 0;
    $max_loss_streak = 0;
    $cur_type = '';
    $cur_count = 0;

    if ($res) {
        while ($row = $res->fetch_assoc()) {
            if ($streak_type === '') {
                $streak_type = $row['outcome'];
                $streak_count = 1;
            } elseif ($row['outcome'] === $streak_type && $streak_count > 0) {
                $streak_count++;
            }

            if ($cur_type === '' || $row['outcome'] === $cur_type) {
                $cur_type = $row['outcome'];
                $cur_count++;
            } else {
                if ($cur_type === 'winner' && $cur_count > $max_win_streak) $max_win_streak = $cur_count;
                if ($cur_type === 'loser' && $cur_count > $max_loss_streak) $max_loss_streak = $cur_count;
                $cur_type = $row['outcome'];
                $cur_count = 1;
            }
        }
        if ($cur_type === 'winner' && $cur_count > $max_win_streak) $max_win_streak = $cur_count;
        if ($cur_type === 'loser' && $cur_count > $max_loss_streak) $max_loss_streak = $cur_count;
    }

    $output['streaks'] = array(
        'current_type'    => $streak_type === 'winner' ? 'winning' : ($streak_type === 'loser' ? 'losing' : 'none'),
        'current_count'   => $streak_count,
        'max_win_streak'  => $max_win_streak,
        'max_loss_streak' => $max_loss_streak
    );
}

if ($action === 'strategies') {
    $res = $conn->query("SELECT * FROM miracle_strategies2 ORDER BY name");
    $strats = array();
    if ($res) { while ($row = $res->fetch_assoc()) $strats[] = $row; }
    $output['strategies'] = $strats;
}

if ($action === 'watchlist') {
    $res = $conn->query("SELECT * FROM miracle_watchlist2 WHERE active=1 ORDER BY is_cdr DESC, ticker ASC");
    $wl = array();
    if ($res) { while ($row = $res->fetch_assoc()) $wl[] = $row; }
    $output['watchlist'] = $wl;
}

echo json_encode($output);
$conn->close();
?>
