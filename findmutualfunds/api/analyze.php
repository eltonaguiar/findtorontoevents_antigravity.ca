<?php
/**
 * Per-strategy analysis for mutual funds.
 * Runs backtest with different scenarios for each strategy and aggregates.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/db_connect.php';

$now = date('Y-m-d H:i:s');

// Get all strategies that have selections
$strats = array();
$r = $conn->query("SELECT DISTINCT strategy_name FROM mf_selections WHERE nav_at_select > 0");
if ($r) { while ($row = $r->fetch_assoc()) $strats[] = $row['strategy_name']; }

if (count($strats) === 0) {
    echo json_encode(array('ok' => false, 'error' => 'No strategies with selections. Run import_funds first.'));
    $conn->close();
    exit;
}

// Scenarios to test — using Questrade $9.95/trade for mutual funds
$scenarios = array(
    array('name' => 'Conservative 90-day (Questrade)', 'hold' => 90, 'tp' => 8,   'sl' => 5,   'comm' => 9.95),
    array('name' => 'Conservative 90-day (No fees)',    'hold' => 90, 'tp' => 8,   'sl' => 5,   'comm' => 0),
    array('name' => 'Moderate 180-day (Questrade)',     'hold' => 180, 'tp' => 12,  'sl' => 8,   'comm' => 9.95),
    array('name' => 'Aggressive 90-day (Questrade)',    'hold' => 90,  'tp' => 20,  'sl' => 15,  'comm' => 9.95),
    array('name' => 'Buy & Hold 1yr (Questrade)',       'hold' => 365, 'tp' => 999, 'sl' => 999, 'comm' => 9.95),
    array('name' => 'Buy & Hold 1yr (No fees)',         'hold' => 365, 'tp' => 999, 'sl' => 999, 'comm' => 0)
);

$results = array();
$per_strategy = array();

foreach ($scenarios as $sc) {
    // Load all selections with NAV history
    $sql = "SELECT ms.*, mf.expense_ratio, mf.front_load_pct, mf.back_load_pct
            FROM mf_selections ms
            LEFT JOIN mf_funds mf ON ms.ticker = mf.ticker
            WHERE ms.nav_at_select > 0
            ORDER BY ms.select_date ASC";
    $res = $conn->query($sql);

    $cap = 10000; $peak = 10000;
    $total_trades = 0; $wins = 0; $losses = 0;
    $max_dd = 0; $total_comm = 0; $total_exp = 0;
    $strat_trades = array();

    if ($res) {
        while ($pick = $res->fetch_assoc()) {
            $ticker = $pick['ticker'];
            $entry_nav = (float)$pick['nav_at_select'];
            if ($entry_nav <= 0) continue;

            $safe_t = $conn->real_escape_string($ticker);
            $safe_d = $conn->real_escape_string($pick['select_date']);
            $exp_ratio = (float)$pick['expense_ratio'];
            $front_load = (float)$pick['front_load_pct'];

            $eff_entry = $entry_nav * (1 + $front_load / 100);
            $pos_value = $cap * 0.10;
            if ($pos_value < $eff_entry + $sc['comm']) continue;
            $shares = ($pos_value - $sc['comm']) / $eff_entry;

            // Fetch NAV
            $nav_res = $conn->query("SELECT nav_date, adj_nav FROM mf_nav_history WHERE ticker='$safe_t' AND nav_date >= '$safe_d' ORDER BY nav_date ASC LIMIT " . ($sc['hold'] + 30));

            $exit_nav = $entry_nav; $exit_date = $pick['select_date']; $exit_reason = 'end_of_data'; $day_count = 0;
            if ($nav_res) {
                while ($day = $nav_res->fetch_assoc()) {
                    $day_count++;
                    $cur_nav = (float)$day['adj_nav'];
                    $cur_date = $day['nav_date'];
                    $ret = ($eff_entry > 0) ? (($cur_nav - $eff_entry) / $eff_entry) * 100 : 0;

                    if ($sc['sl'] < 999 && $ret <= -$sc['sl']) {
                        $exit_nav = $cur_nav; $exit_date = $cur_date; $exit_reason = 'stop_loss'; break;
                    }
                    if ($sc['tp'] < 999 && $ret >= $sc['tp']) {
                        $exit_nav = $cur_nav; $exit_date = $cur_date; $exit_reason = 'target_reached'; break;
                    }
                    $dh = (int)((strtotime($cur_date) - strtotime($pick['select_date'])) / 86400);
                    if ($dh >= $sc['hold']) {
                        $exit_nav = $cur_nav; $exit_date = $cur_date; $exit_reason = 'hold_period'; break;
                    }
                    $exit_nav = $cur_nav; $exit_date = $cur_date;
                }
            }

            $actual_days = max(1, (int)((strtotime($exit_date) - strtotime($pick['select_date'])) / 86400));
            $exp_cost = $exp_ratio > 0 ? round($shares * $eff_entry * $exp_ratio * ($actual_days / 365), 2) : 0;
            $gross = ($exit_nav - $eff_entry) * $shares;
            $comm_total = $sc['comm'] * 2;
            $net = $gross - $comm_total - $exp_cost;

            $total_trades++; $total_comm += $comm_total; $total_exp += $exp_cost;
            $cap += $net;
            if ($net > 0) $wins++; else $losses++;
            if ($cap > $peak) $peak = $cap;
            $dd = ($peak > 0) ? (($peak - $cap) / $peak) * 100 : 0;
            if ($dd > $max_dd) $max_dd = $dd;

            // Track per-strategy
            $sn = $pick['strategy_name'];
            if (!isset($strat_trades[$sn])) $strat_trades[$sn] = array('trades' => 0, 'wins' => 0, 'pnl' => 0);
            $strat_trades[$sn]['trades']++;
            if ($net > 0) $strat_trades[$sn]['wins']++;
            $strat_trades[$sn]['pnl'] += $net;
        }
    }

    $wr = ($total_trades > 0) ? round($wins / $total_trades * 100, 2) : 0;
    $tr = round(($cap - 10000) / 10000 * 100, 4);

    $results[] = array(
        'scenario' => $sc['name'],
        'initial_capital' => 10000,
        'final_value' => round($cap, 2),
        'total_return_pct' => $tr,
        'total_trades' => $total_trades,
        'win_rate' => $wr,
        'max_drawdown_pct' => round($max_dd, 4),
        'total_commissions' => round($total_comm, 2),
        'total_expenses' => round($total_exp, 2),
        'hold_days' => $sc['hold'],
        'tp' => $sc['tp'], 'sl' => $sc['sl'],
        'per_strategy' => $strat_trades
    );
}

// Build per-strategy summary
$all_strats = array();
foreach ($results as $r) {
    if (isset($r['per_strategy'])) {
        foreach ($r['per_strategy'] as $sn => $sd) {
            if (!isset($all_strats[$sn])) $all_strats[$sn] = array('total_trades' => 0, 'total_wins' => 0, 'total_pnl' => 0, 'scenarios' => 0);
            $all_strats[$sn]['total_trades'] += $sd['trades'];
            $all_strats[$sn]['total_wins'] += $sd['wins'];
            $all_strats[$sn]['total_pnl'] += $sd['pnl'];
            $all_strats[$sn]['scenarios']++;
        }
    }
}
$per_strategy_agg = array();
foreach ($all_strats as $sn => $sd) {
    $wr = ($sd['total_trades'] > 0) ? round($sd['total_wins'] / $sd['total_trades'] * 100, 2) : 0;
    $per_strategy_agg[] = array('strategy' => $sn, 'total_trades' => $sd['total_trades'], 'win_rate' => $wr, 'total_pnl' => round($sd['total_pnl'], 2));
}

// Audit
$ip = isset($_SERVER['REMOTE_ADDR']) ? $conn->real_escape_string($_SERVER['REMOTE_ADDR']) : 'unknown';
$conn->query("INSERT INTO mf_audit_log (action_type, details, ip_address, created_at) VALUES ('analyze', 'Analyzed " . count($strats) . " strategies x " . count($scenarios) . " scenarios', '$ip', '$now')");

echo json_encode(array(
    'ok' => true,
    'strategies_analyzed' => count($strats),
    'scenarios' => $results,
    'per_strategy' => $per_strategy_agg
));
$conn->close();
?>
