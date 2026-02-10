<?php
/**
 * Cost/Tax Modeling API for Canadian Investors
 * Extends Questrade fee model with capital gains tax impact.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   estimate        — Tax impact for a set of trades
 *   wash_sale_check — Flag re-buys within 30 days of a loss
 *   annual_summary  — Tax-year realized gains/losses
 *   cost_adjusted   — Backtest returns adjusted for fees + taxes
 *
 * Usage:
 *   GET .../tax_model.php?action=estimate&gain=1000&marginal_rate=30&account=taxable
 *   GET .../tax_model.php?action=wash_sale_check
 *   GET .../tax_model.php?action=annual_summary&year=2026
 *   GET .../tax_model.php?action=cost_adjusted
 */
require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(dirname(dirname(__FILE__))) . '/api/questrade_fees.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'estimate';
$response = array('ok' => true, 'action' => $action);

// ═══════════════════════════════════════════════
// Canadian Tax Constants
// ═══════════════════════════════════════════════
$CAN_CAPITAL_GAINS_INCLUSION = 0.50;  // 50% of capital gains are taxable
$CAN_TFSA_TAX_RATE = 0;               // TFSA = tax free
$CAN_RRSP_TAX_RATE = 0;               // RRSP = tax deferred

// ═══════════════════════════════════════════════
// Tax estimation helper
// ═══════════════════════════════════════════════
function _tax_estimate_cg($realized_gain, $marginal_rate_pct, $account_type) {
    global $CAN_CAPITAL_GAINS_INCLUSION;

    if ($account_type === 'tfsa' || $account_type === 'rrsp') {
        return array('taxable_gain' => 0, 'tax_owed' => 0, 'effective_rate' => 0, 'note' => 'Tax-sheltered account');
    }

    // Canadian capital gains: 50% inclusion rate
    $taxable = $realized_gain * $CAN_CAPITAL_GAINS_INCLUSION;
    $tax = round($taxable * ($marginal_rate_pct / 100), 2);

    // Losses create tax credits
    if ($realized_gain < 0) {
        $tax_credit = round(abs($taxable) * ($marginal_rate_pct / 100), 2);
        return array(
            'taxable_gain' => round($taxable, 2),
            'tax_credit' => $tax_credit,
            'tax_owed' => 0,
            'effective_rate' => 0,
            'note' => 'Capital loss: can offset other capital gains'
        );
    }

    $effective = ($realized_gain > 0) ? round(($tax / $realized_gain) * 100, 2) : 0;

    return array(
        'taxable_gain' => round($taxable, 2),
        'tax_owed' => $tax,
        'effective_rate' => $effective,
        'note' => $CAN_CAPITAL_GAINS_INCLUSION * 100 . '% inclusion rate at ' . $marginal_rate_pct . '% marginal rate'
    );
}

// ═══════════════════════════════════════════════
// ACTION: estimate — Tax impact for given parameters
// ═══════════════════════════════════════════════
if ($action === 'estimate') {
    $gain = isset($_GET['gain']) ? (float)$_GET['gain'] : 0;
    $marginal = isset($_GET['marginal_rate']) ? (float)$_GET['marginal_rate'] : 30;
    $account = isset($_GET['account']) ? trim($_GET['account']) : 'taxable';

    $tax = _tax_estimate_cg($gain, $marginal, $account);

    // Also calculate Questrade fees for context
    $trade_value = isset($_GET['trade_value']) ? (float)$_GET['trade_value'] : 0;
    $ticker = isset($_GET['ticker']) ? trim($_GET['ticker']) : '';
    $shares = isset($_GET['shares']) ? (int)$_GET['shares'] : 0;

    $fees = array('total_fee' => 0);
    if ($trade_value > 0 && $ticker !== '') {
        $buy_fees = questrade_calc_fees($ticker, $trade_value, $shares, false, 'questrade');
        $sell_fees = questrade_calc_fees($ticker, $trade_value, $shares, true, 'questrade');
        $fees = array(
            'buy_fees' => $buy_fees['total_fee'],
            'sell_fees' => $sell_fees['total_fee'],
            'total_fees' => round($buy_fees['total_fee'] + $sell_fees['total_fee'], 2),
            'is_cdr' => $buy_fees['is_cdr'],
            'forex_fee' => $buy_fees['forex_fee']
        );
    }

    $response['gain'] = $gain;
    $response['marginal_rate'] = $marginal;
    $response['account'] = $account;
    $response['tax'] = $tax;
    $response['fees'] = $fees;

    $net_gain = $gain - $tax['tax_owed'] - $fees['total_fee'];
    $response['net_gain'] = round($net_gain, 2);
    $response['total_cost'] = round($tax['tax_owed'] + $fees['total_fee'], 2);

} elseif ($action === 'wash_sale_check') {
    // ═══════════════════════════════════════════════
    // ACTION: wash_sale_check — Flag re-buys within 30 days of loss
    // ═══════════════════════════════════════════════
    // Note: Canada doesn't have a formal "wash sale" rule like the US,
    // but CRA can deny "superficial losses" (re-buy within 30 days)

    $days = isset($_GET['days']) ? max(1, min(365, (int)$_GET['days'])) : 90;

    // Find closed paper trades that were losses
    $losses = array();
    $lr = $conn->query("SELECT id, ticker, exit_date, return_pct, entry_price, exit_price
                         FROM paper_trades
                         WHERE status='closed' AND return_pct < 0
                           AND exit_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)
                         ORDER BY exit_date DESC");
    if ($lr) {
        while ($row = $lr->fetch_assoc()) $losses[] = $row;
    }

    $warnings = array();
    foreach ($losses as $loss) {
        $ticker = $loss['ticker'];
        $exit_date = $loss['exit_date'];
        $safe_t = $conn->real_escape_string($ticker);
        $safe_d = $conn->real_escape_string($exit_date);

        // Check if re-bought within 30 days
        $rebuy = $conn->query("SELECT id, enter_date, entry_price FROM paper_trades
                               WHERE ticker='$safe_t' AND enter_date > '$safe_d'
                                 AND enter_date <= DATE_ADD('$safe_d', INTERVAL 30 DAY)
                               LIMIT 1");
        if ($rebuy && $rebuy->num_rows > 0) {
            $rb = $rebuy->fetch_assoc();
            $warnings[] = array(
                'ticker' => $ticker,
                'loss_exit_date' => $exit_date,
                'loss_pct' => round((float)$loss['return_pct'], 2),
                'rebuy_date' => $rb['enter_date'],
                'days_between' => (int)((strtotime($rb['enter_date']) - strtotime($exit_date)) / 86400),
                'warning' => 'Superficial loss: CRA may deny this capital loss deduction'
            );
        }
    }

    $response['warnings'] = $warnings;
    $response['count'] = count($warnings);
    $response['note'] = 'Under CRA rules, a capital loss is denied if the same security is re-acquired within 30 days before or after the sale.';

} elseif ($action === 'annual_summary') {
    // ═══════════════════════════════════════════════
    // ACTION: annual_summary — Tax-year realized gains/losses
    // ═══════════════════════════════════════════════
    $year = isset($_GET['year']) ? (int)$_GET['year'] : (int)date('Y');
    $marginal = isset($_GET['marginal_rate']) ? (float)$_GET['marginal_rate'] : 30;
    $account = isset($_GET['account']) ? trim($_GET['account']) : 'taxable';

    $year_start = $year . '-01-01';
    $year_end = $year . '-12-31';

    // Realized trades in this tax year
    $gains = 0;
    $loss_total = 0;
    $trade_count = 0;
    $total_fees = 0;

    $tr = $conn->query("SELECT ticker, entry_price, exit_price, return_pct, exit_date
                         FROM paper_trades
                         WHERE status='closed'
                           AND exit_date >= '$year_start' AND exit_date <= '$year_end'
                         ORDER BY exit_date");
    $trades = array();
    if ($tr) {
        while ($row = $tr->fetch_assoc()) {
            $trade_count++;
            $ret = (float)$row['return_pct'];
            $entry = (float)$row['entry_price'];

            // Estimate dollar gain (assume $1000 position)
            $dollar_gain = round(1000 * ($ret / 100), 2);

            if ($ret > 0) { $gains += $dollar_gain; }
            else { $loss_total += abs($dollar_gain); }

            // Estimate trading fees
            $fees = questrade_calc_fees($row['ticker'], 1000, (int)(1000 / max(1, $entry)), false, 'questrade');
            $total_fees += $fees['total_fee'] * 2; // buy + sell

            $trades[] = array(
                'ticker' => $row['ticker'],
                'exit_date' => $row['exit_date'],
                'return_pct' => round($ret, 2),
                'estimated_dollar_gain' => $dollar_gain
            );
        }
    }

    $net_gain = round($gains - $loss_total, 2);
    $tax = _tax_estimate_cg($net_gain, $marginal, $account);

    $response['year'] = $year;
    $response['account_type'] = $account;
    $response['marginal_rate'] = $marginal;
    $response['trade_count'] = $trade_count;
    $response['total_gains'] = round($gains, 2);
    $response['total_losses'] = round($loss_total, 2);
    $response['net_gain'] = $net_gain;
    $response['tax'] = $tax;
    $response['estimated_fees'] = round($total_fees, 2);
    $response['after_tax_and_fees'] = round($net_gain - $tax['tax_owed'] - $total_fees, 2);
    $response['trades'] = $trades;

} elseif ($action === 'cost_adjusted') {
    // ═══════════════════════════════════════════════
    // ACTION: cost_adjusted — Backtest returns with fee + tax drag
    // ═══════════════════════════════════════════════
    $marginal = isset($_GET['marginal_rate']) ? (float)$_GET['marginal_rate'] : 30;
    $account = isset($_GET['account']) ? trim($_GET['account']) : 'taxable';

    // Get paper trade stats (or backtest results)
    $pre_tax = array('win_rate' => 0, 'avg_return' => 0, 'trades' => 0);
    $pr = $conn->query("SELECT COUNT(*) as cnt, AVG(return_pct) as avg_ret,
                         SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END) as wins
                        FROM paper_trades WHERE status='closed'");
    if ($pr && $pr->num_rows > 0) {
        $row = $pr->fetch_assoc();
        $cnt = (int)$row['cnt'];
        $pre_tax = array(
            'win_rate' => ($cnt > 0) ? round((int)$row['wins'] / $cnt * 100, 2) : 0,
            'avg_return' => round((float)$row['avg_ret'], 4),
            'trades' => $cnt
        );
    }

    // Tax drag on average return
    $avg_ret = $pre_tax['avg_return'];
    if ($avg_ret > 0 && $account === 'taxable') {
        $tax_drag = $avg_ret * $CAN_CAPITAL_GAINS_INCLUSION * ($marginal / 100);
        $after_tax_ret = round($avg_ret - $tax_drag, 4);
    } else {
        $tax_drag = 0;
        $after_tax_ret = $avg_ret;
    }

    // Typical fee drag (assume $5000 position, $25 avg price, buy+sell)
    $sample_fees = questrade_calc_fees('AAPL', 5000, 200, false, 'questrade');
    $fee_pct = ($sample_fees['total_fee'] * 2 / 5000) * 100; // round-trip as % of position

    $response['pre_tax'] = $pre_tax;
    $response['tax_drag_pct'] = round($tax_drag, 4);
    $response['fee_drag_pct'] = round($fee_pct, 4);
    $response['after_costs_return'] = round($after_tax_ret - $fee_pct, 4);
    $response['account_type'] = $account;
    $response['marginal_rate'] = $marginal;
    $response['breakeven_win_rate'] = 'Requires avg_return > ' . round($tax_drag + $fee_pct, 2) . '% per trade to be profitable after costs';
}

echo json_encode($response);
$conn->close();
