<?php
/**
 * Questrade Canada Fee Model — DayTraders Miracle Edition
 * Realistic commission and fee calculation for Canadian brokerage.
 * PHP 5.2 compatible.
 *
 * Fee structure (2025/2026):
 *   - Stocks/ETFs: $0 commission (self-directed)
 *   - CDRs (Canadian Depositary Receipts): $0 commission, trades in CAD on NEO Exchange
 *   - US stocks without CDR: $0 commission + 1.75% forex conversion fee on trade value
 *   - ECN fees: $0.0035/share (US orders, typically negligible)
 *   - SEC fee: 0.00278% of sell value (US sells only)
 *   - Mutual funds: $9.95 per trade
 *
 * CDR hedge cost: up to 0.60% annually (built into CDR price, not a per-trade fee)
 */

$QUESTRADE_CDR_TICKERS = array(
    'AAPL', 'AMD', 'AMZN', 'CSCO', 'CRM', 'GOOG', 'GOOGL', 'IBM', 'INTC',
    'META', 'MSFT', 'NFLX', 'NVDA',
    'COST', 'DIS', 'HD', 'MCD', 'NKE', 'SBUX', 'TSLA', 'WMT',
    'ABBV', 'CVS', 'JNJ', 'PFE', 'UNH',
    'BAC', 'BRK.B', 'CITI', 'GS', 'JPM', 'MA', 'PYPL', 'V',
    'BA', 'CVX', 'XOM', 'HON', 'UPS',
    'KO', 'VZ', 'UBER'
);

$QUESTRADE_TSX_SUFFIXES = array('.TO', '.V', '.CN', '-T', '-X');

$QUESTRADE_FOREX_MARKUP_PCT = 1.75;
$QUESTRADE_ECN_PER_SHARE   = 0.0035;
$QUESTRADE_SEC_FEE_PCT     = 0.00278;
$QUESTRADE_CDR_HEDGE_ANNUAL = 0.60;
$QUESTRADE_MF_COMMISSION    = 9.95;

function questrade_calc_fees2($ticker, $trade_value, $shares, $is_sell, $fee_model) {
    global $QUESTRADE_CDR_TICKERS, $QUESTRADE_TSX_SUFFIXES;
    global $QUESTRADE_FOREX_MARKUP_PCT, $QUESTRADE_ECN_PER_SHARE, $QUESTRADE_SEC_FEE_PCT;

    $result = array(
        'commission'    => 0,
        'forex_fee'     => 0,
        'ecn_fee'       => 0,
        'sec_fee'       => 0,
        'total_fee'     => 0,
        'is_cdr'        => false,
        'is_canadian'   => false,
        'fee_breakdown' => ''
    );

    if ($fee_model === 'flat_10') {
        $result['commission'] = 10.00;
        $result['total_fee'] = 10.00;
        $result['fee_breakdown'] = 'Flat $10 commission';
        return $result;
    }

    if ($fee_model === 'zero') {
        $result['fee_breakdown'] = 'No fees';
        return $result;
    }

    $upper = strtoupper(trim($ticker));

    $is_canadian = false;
    foreach ($QUESTRADE_TSX_SUFFIXES as $suffix) {
        if (_qt2_str_ends($upper, strtoupper($suffix))) {
            $is_canadian = true;
            break;
        }
    }

    $is_cdr = in_array($upper, $QUESTRADE_CDR_TICKERS);
    $base_ticker = preg_replace('/\.(TO|V|CN)$/', '', $upper);
    if (!$is_cdr) $is_cdr = in_array($base_ticker, $QUESTRADE_CDR_TICKERS);

    $result['is_cdr'] = $is_cdr;
    $result['is_canadian'] = $is_canadian;
    $result['commission'] = 0;

    if ($is_cdr) {
        $result['fee_breakdown'] = 'CDR (commission-free, CAD)';
    } elseif ($is_canadian) {
        $result['fee_breakdown'] = 'TSX (commission-free, CAD)';
    } else {
        $forex = round($trade_value * ($QUESTRADE_FOREX_MARKUP_PCT / 100), 2);
        $result['forex_fee'] = $forex;

        $ecn = round($shares * $QUESTRADE_ECN_PER_SHARE, 2);
        $result['ecn_fee'] = $ecn;

        $sec = 0;
        if ($is_sell) {
            $sec = round($trade_value * ($QUESTRADE_SEC_FEE_PCT / 10000), 2);
            if ($sec < 0.01) $sec = 0.01;
        }
        $result['sec_fee'] = $sec;

        $parts = array();
        $parts[] = 'Forex 1.75%: $' . number_format($forex, 2);
        if ($ecn > 0) $parts[] = 'ECN: $' . number_format($ecn, 2);
        if ($sec > 0) $parts[] = 'SEC: $' . number_format($sec, 2);
        $result['fee_breakdown'] = 'US stock — ' . implode(', ', $parts);
    }

    $result['total_fee'] = round($result['commission'] + $result['forex_fee'] + $result['ecn_fee'] + $result['sec_fee'], 2);
    return $result;
}

function questrade_has_cdr2($ticker) {
    global $QUESTRADE_CDR_TICKERS;
    $upper = strtoupper(trim($ticker));
    $base = preg_replace('/\.(TO|V|CN)$/', '', $upper);
    return in_array($upper, $QUESTRADE_CDR_TICKERS) || in_array($base, $QUESTRADE_CDR_TICKERS);
}

function questrade_round_trip_fee2($ticker, $entry_price, $shares) {
    $trade_val = $entry_price * $shares;
    $buy_fees  = questrade_calc_fees2($ticker, $trade_val, $shares, false, 'questrade');
    $sell_fees = questrade_calc_fees2($ticker, $trade_val, $shares, true, 'questrade');
    return round($buy_fees['total_fee'] + $sell_fees['total_fee'], 2);
}

function _qt2_str_ends($haystack, $needle) {
    $len = strlen($needle);
    if ($len === 0) return true;
    return (substr($haystack, -$len) === $needle);
}
?>
