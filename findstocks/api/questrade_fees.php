<?php
/**
 * Questrade Canada Fee Model
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

// ─── CDR tickers available on Cboe Canada (NEO) ───
// These can be traded commission-free in CAD, no forex fee
$QUESTRADE_CDR_TICKERS = array(
    // Technology
    'AAPL', 'AMD', 'AMZN', 'CSCO', 'CRM', 'GOOG', 'GOOGL', 'IBM', 'INTC',
    'META', 'MSFT', 'NFLX', 'NVDA',
    // Consumer
    'COST', 'DIS', 'HD', 'MCD', 'NKE', 'SBUX', 'TSLA', 'WMT',
    // Healthcare
    'ABBV', 'CVS', 'JNJ', 'PFE', 'UNH',
    // Financials
    'BAC', 'BRK.B', 'CITI', 'GS', 'JPM', 'MA', 'PYPL', 'V',
    // Energy & Industrials
    'BA', 'CVX', 'XOM', 'HON', 'UPS',
    // Telecom / Other
    'KO', 'VZ', 'UBER'
);

// ─── Canadian-listed tickers (TSX/TSX-V) — no forex needed ───
// These trade in CAD natively, $0 commission on Questrade
$QUESTRADE_TSX_SUFFIXES = array('.TO', '.V', '.CN', '-T', '-X');

// ─── Fee constants ───
$QUESTRADE_FOREX_MARKUP_PCT = 1.75;   // % added to Bank of Canada rate for USD/CAD
$QUESTRADE_ECN_PER_SHARE   = 0.0035;  // ECN fee per share (US orders)
$QUESTRADE_SEC_FEE_PCT     = 0.00278; // SEC fee % on US sells (0.00278%)
$QUESTRADE_CDR_HEDGE_ANNUAL = 0.60;   // Annual CDR hedge cost % (baked into NAV)
$QUESTRADE_MF_COMMISSION    = 9.95;   // Mutual fund commission per trade

/**
 * Calculate Questrade trading fees for a stock trade.
 *
 * @param string $ticker       Stock ticker symbol
 * @param float  $trade_value  Total trade value in USD (entry_price * shares)
 * @param int    $shares       Number of shares
 * @param bool   $is_sell      True if this is a sell order
 * @param string $fee_model    'questrade' (default), 'flat_10' (legacy $10), 'zero' (no fees)
 * @return array  ('commission'=>float, 'forex_fee'=>float, 'ecn_fee'=>float, 'sec_fee'=>float,
 *                 'total_fee'=>float, 'is_cdr'=>bool, 'is_canadian'=>bool, 'fee_breakdown'=>string)
 */
function questrade_calc_fees($ticker, $trade_value, $shares, $is_sell, $fee_model) {
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

    // Legacy flat fee model
    if ($fee_model === 'flat_10') {
        $result['commission'] = 10.00;
        $result['total_fee'] = 10.00;
        $result['fee_breakdown'] = 'Flat $10 commission';
        return $result;
    }

    // Zero fee model
    if ($fee_model === 'zero') {
        $result['fee_breakdown'] = 'No fees';
        return $result;
    }

    // ─── Questrade model ───
    $upper = strtoupper(trim($ticker));

    // Check if Canadian-listed (TSX, TSX-V, etc.)
    $is_canadian = false;
    foreach ($QUESTRADE_TSX_SUFFIXES as $suffix) {
        if (_qt_str_ends($upper, strtoupper($suffix))) {
            $is_canadian = true;
            break;
        }
    }

    // Check if CDR is available
    $is_cdr = in_array($upper, $QUESTRADE_CDR_TICKERS);
    // Also check without common suffixes
    $base_ticker = preg_replace('/\.(TO|V|CN)$/', '', $upper);
    if (!$is_cdr) $is_cdr = in_array($base_ticker, $QUESTRADE_CDR_TICKERS);

    $result['is_cdr'] = $is_cdr;
    $result['is_canadian'] = $is_canadian;

    // Commission: $0 for stocks/ETFs on Questrade
    $result['commission'] = 0;

    if ($is_cdr) {
        // CDR: trades in CAD, no forex, no ECN, commission-free
        $result['fee_breakdown'] = 'CDR (commission-free, CAD)';
        // CDR hedge cost is embedded in NAV, not per-trade
    } elseif ($is_canadian) {
        // Canadian stock: trades in CAD, no forex
        $result['fee_breakdown'] = 'TSX (commission-free, CAD)';
    } else {
        // US stock without CDR: forex conversion applies
        $forex = round($trade_value * ($QUESTRADE_FOREX_MARKUP_PCT / 100), 2);
        $result['forex_fee'] = $forex;

        // ECN fee (typically small)
        $ecn = round($shares * $QUESTRADE_ECN_PER_SHARE, 2);
        $result['ecn_fee'] = $ecn;

        // SEC fee on sells only
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

/**
 * Quick check: does a ticker have a CDR available?
 */
function questrade_has_cdr($ticker) {
    global $QUESTRADE_CDR_TICKERS;
    $upper = strtoupper(trim($ticker));
    $base = preg_replace('/\.(TO|V|CN)$/', '', $upper);
    return in_array($upper, $QUESTRADE_CDR_TICKERS) || in_array($base, $QUESTRADE_CDR_TICKERS);
}

/**
 * Get the fee model label for display.
 */
function questrade_fee_label($fee_model) {
    if ($fee_model === 'questrade') return 'Questrade Canada';
    if ($fee_model === 'flat_10') return 'Flat $10/trade';
    if ($fee_model === 'zero') return 'Zero fees';
    return $fee_model;
}

// PHP 5.2 compatible string ends-with
function _qt_str_ends($haystack, $needle) {
    $len = strlen($needle);
    if ($len === 0) return true;
    return (substr($haystack, -$len) === $needle);
}
?>
