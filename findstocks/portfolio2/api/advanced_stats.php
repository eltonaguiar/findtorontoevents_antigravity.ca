<?php
/**
 * Advanced Stats / Pro Analytics Endpoint
 * Mirrors top stock website metrics (Yahoo Finance, Morningstar, Finviz, TradingView).
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ticker_profile     — Per-stock deep analysis (52wk range, RSI, SMA, volume, volatility)
 *   portfolio_analytics — Full portfolio analytics (Sharpe, Sortino, Calmar, Alpha, Beta, VaR)
 *   algorithm_report    — Algorithm-level performance report
 *   risk_report         — Risk analysis (drawdowns, tail risk, stress tests)
 *   leaderboard         — Best algorithms/scenarios ranked by multiple metrics
 *   walk_forward        — Walk-forward validation results
 *   regime_analysis     — Performance by market regime (bull/bear/high-vol/low-vol)
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'leaderboard';
$response = array('ok' => true, 'action' => $action);

// ═══════════════════════════════════════════
// TICKER PROFILE — Deep per-stock analysis
// ═══════════════════════════════════════════
if ($action === 'ticker_profile') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    if ($ticker === '') {
        $response['ok'] = false;
        $response['error'] = 'ticker parameter required';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $safe = $conn->real_escape_string($ticker);

    // Basic info
    $res = $conn->query("SELECT * FROM stocks WHERE ticker='$safe'");
    $stock_info = ($res && $res->num_rows > 0) ? $res->fetch_assoc() : array('ticker' => $ticker);

    // Price data (last 252 trading days = ~1 year)
    $res = $conn->query("SELECT trade_date, open_price, high_price, low_price, close_price, volume
                          FROM daily_prices WHERE ticker='$safe'
                          ORDER BY trade_date DESC LIMIT 252");
    $prices = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $prices[] = $row;
        }
    }

    if (count($prices) === 0) {
        $response['ok'] = false;
        $response['error'] = 'No price data for ' . $ticker;
        echo json_encode($response);
        $conn->close();
        exit;
    }

    // Reverse for chronological order
    $prices = array_reverse($prices);
    $n = count($prices);
    $latest = $prices[$n - 1];
    $current_price = (float)$latest['close_price'];

    // 52-Week High/Low
    $high_52w = 0;
    $low_52w = 999999;
    foreach ($prices as $p) {
        $h = (float)$p['high_price'];
        $l = (float)$p['low_price'];
        if ($h > $high_52w) $high_52w = $h;
        if ($l < $low_52w && $l > 0) $low_52w = $l;
    }
    $pct_from_high = ($high_52w > 0) ? round(($current_price - $high_52w) / $high_52w * 100, 2) : 0;
    $pct_from_low = ($low_52w > 0) ? round(($current_price - $low_52w) / $low_52w * 100, 2) : 0;

    // Moving Averages
    $closes = array();
    foreach ($prices as $p) $closes[] = (float)$p['close_price'];

    $sma_20 = ($n >= 20) ? round(array_sum(array_slice($closes, -20)) / 20, 4) : 0;
    $sma_50 = ($n >= 50) ? round(array_sum(array_slice($closes, -50)) / 50, 4) : 0;
    $sma_200 = ($n >= 200) ? round(array_sum(array_slice($closes, -200)) / 200, 4) : 0;

    // SMA signals
    $sma_signal = 'neutral';
    if ($sma_20 > 0 && $sma_50 > 0) {
        if ($current_price > $sma_20 && $sma_20 > $sma_50) $sma_signal = 'bullish';
        elseif ($current_price < $sma_20 && $sma_20 < $sma_50) $sma_signal = 'bearish';
    }
    $golden_cross = ($sma_50 > 0 && $sma_200 > 0 && $sma_50 > $sma_200);
    $death_cross = ($sma_50 > 0 && $sma_200 > 0 && $sma_50 < $sma_200);

    // RSI (14-period)
    $rsi = 0;
    if ($n >= 15) {
        $gains = 0;
        $losses_r = 0;
        for ($i = $n - 14; $i < $n; $i++) {
            $change = $closes[$i] - $closes[$i - 1];
            if ($change > 0) $gains += $change;
            else $losses_r += abs($change);
        }
        $avg_gain = $gains / 14;
        $avg_loss_r = $losses_r / 14;
        if ($avg_loss_r > 0) {
            $rs = $avg_gain / $avg_loss_r;
            $rsi = round(100 - (100 / (1 + $rs)), 2);
        } else {
            $rsi = 100;
        }
    }
    $rsi_signal = 'neutral';
    if ($rsi > 70) $rsi_signal = 'overbought';
    elseif ($rsi < 30) $rsi_signal = 'oversold';

    // Volatility (20-day annualized)
    $vol_20d = 0;
    if ($n >= 21) {
        $log_returns = array();
        for ($i = $n - 20; $i < $n; $i++) {
            if ($closes[$i - 1] > 0) {
                $log_returns[] = log($closes[$i] / $closes[$i - 1]);
            }
        }
        if (count($log_returns) > 1) {
            $mean_lr = array_sum($log_returns) / count($log_returns);
            $var_lr = 0;
            foreach ($log_returns as $lr) $var_lr += ($lr - $mean_lr) * ($lr - $mean_lr);
            $vol_20d = round(sqrt($var_lr / count($log_returns)) * sqrt(252) * 100, 2);
        }
    }

    // Average Volume (20-day)
    $vol_data = array();
    for ($i = max(0, $n - 20); $i < $n; $i++) {
        $vol_data[] = (float)$prices[$i]['volume'];
    }
    $avg_volume_20d = (count($vol_data) > 0) ? round(array_sum($vol_data) / count($vol_data)) : 0;
    $latest_volume = (float)$latest['volume'];
    $volume_ratio = ($avg_volume_20d > 0) ? round($latest_volume / $avg_volume_20d, 2) : 0;

    // Returns at various timeframes
    $return_1d = ($n >= 2) ? round(($closes[$n-1] - $closes[$n-2]) / $closes[$n-2] * 100, 2) : 0;
    $return_5d = ($n >= 6) ? round(($closes[$n-1] - $closes[$n-6]) / $closes[$n-6] * 100, 2) : 0;
    $return_20d = ($n >= 21) ? round(($closes[$n-1] - $closes[$n-21]) / $closes[$n-21] * 100, 2) : 0;
    $return_60d = ($n >= 61) ? round(($closes[$n-1] - $closes[$n-61]) / $closes[$n-61] * 100, 2) : 0;
    $return_ytd = ($n >= 2) ? round(($closes[$n-1] - $closes[0]) / $closes[0] * 100, 2) : 0;

    // ATR (14-period Average True Range)
    $atr = 0;
    if ($n >= 15) {
        $tr_sum = 0;
        for ($i = $n - 14; $i < $n; $i++) {
            $h = (float)$prices[$i]['high_price'];
            $l = (float)$prices[$i]['low_price'];
            $pc = (float)$prices[$i-1]['close_price'];
            $tr1 = $h - $l;
            $tr2 = abs($h - $pc);
            $tr3 = abs($l - $pc);
            $tr = max($tr1, $tr2, $tr3);
            $tr_sum += $tr;
        }
        $atr = round($tr_sum / 14, 4);
    }
    $atr_pct = ($current_price > 0) ? round($atr / $current_price * 100, 2) : 0;

    // Bollinger Bands (20-day, 2 std dev)
    $bb_upper = 0;
    $bb_lower = 0;
    $bb_pct = 0;
    if ($n >= 20) {
        $slice = array_slice($closes, -20);
        $bb_mean = array_sum($slice) / 20;
        $bb_var = 0;
        foreach ($slice as $sv) $bb_var += ($sv - $bb_mean) * ($sv - $bb_mean);
        $bb_std = sqrt($bb_var / 20);
        $bb_upper = round($bb_mean + 2 * $bb_std, 4);
        $bb_lower = round($bb_mean - 2 * $bb_std, 4);
        $bb_width = $bb_upper - $bb_lower;
        $bb_pct = ($bb_width > 0) ? round(($current_price - $bb_lower) / $bb_width * 100, 2) : 50;
    }

    // MACD (12, 26, 9)
    $macd = 0;
    $macd_signal_line = 0;
    $macd_histogram = 0;
    if ($n >= 26) {
        // Simple EMA approximation using SMA
        $ema12 = array_sum(array_slice($closes, -12)) / 12;
        $ema26 = array_sum(array_slice($closes, -26)) / 26;
        $macd = round($ema12 - $ema26, 4);
        $macd_signal_line = round($macd * 0.8, 4); // approximation
        $macd_histogram = round($macd - $macd_signal_line, 4);
    }

    // Pick history from algorithms
    $res = $conn->query("SELECT algorithm_name, pick_date, entry_price, score, rating, risk_level
                          FROM stock_picks WHERE ticker='$safe'
                          ORDER BY pick_date DESC LIMIT 20");
    $pick_history = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) $pick_history[] = $row;
    }

    // Technical verdict
    $bull_signals = 0;
    $bear_signals = 0;
    if ($current_price > $sma_20) $bull_signals++; else $bear_signals++;
    if ($current_price > $sma_50) $bull_signals++; else $bear_signals++;
    if ($current_price > $sma_200) $bull_signals++; else $bear_signals++;
    if ($rsi > 50 && $rsi < 70) $bull_signals++;
    if ($rsi < 50 && $rsi > 30) $bear_signals++;
    if ($rsi > 70) $bear_signals++;
    if ($rsi < 30) $bull_signals++;
    if ($golden_cross) $bull_signals += 2;
    if ($death_cross) $bear_signals += 2;
    if ($macd > 0) $bull_signals++; else $bear_signals++;
    if ($volume_ratio > 1.5) $bull_signals++;

    $total_signals = $bull_signals + $bear_signals;
    $bull_pct = ($total_signals > 0) ? round($bull_signals / $total_signals * 100) : 50;
    if ($bull_pct >= 70) $overall_signal = 'Strong Buy';
    elseif ($bull_pct >= 55) $overall_signal = 'Buy';
    elseif ($bull_pct >= 45) $overall_signal = 'Neutral';
    elseif ($bull_pct >= 30) $overall_signal = 'Sell';
    else $overall_signal = 'Strong Sell';

    $response['ticker'] = $ticker;
    $response['stock'] = $stock_info;
    $response['price'] = array(
        'current' => $current_price,
        'date' => $latest['trade_date'],
        'open' => (float)$latest['open_price'],
        'high' => (float)$latest['high_price'],
        'low' => (float)$latest['low_price'],
        'volume' => (int)$latest['volume']
    );
    $response['range_52w'] = array(
        'high' => $high_52w, 'low' => $low_52w,
        'pct_from_high' => $pct_from_high, 'pct_from_low' => $pct_from_low
    );
    $response['moving_averages'] = array(
        'sma_20' => $sma_20, 'sma_50' => $sma_50, 'sma_200' => $sma_200,
        'signal' => $sma_signal, 'golden_cross' => $golden_cross, 'death_cross' => $death_cross
    );
    $response['volume'] = array(
        'latest' => $latest_volume, 'avg_20d' => $avg_volume_20d, 'ratio' => $volume_ratio
    );
    $response['returns'] = array(
        '1d' => $return_1d, '5d' => $return_5d, '1m' => $return_20d, '3m' => $return_60d, 'ytd' => $return_ytd
    );
    // ── Stochastic RSI (14-period) ──
    $stoch_rsi = 0;
    $stoch_rsi_signal = 'neutral';
    if ($n >= 28) {
        // Calculate RSI series for last 14 days to get stochastic of RSI
        $rsi_vals = array();
        for ($j = $n - 28; $j < $n; $j++) {
            $g2 = 0; $l2 = 0;
            for ($k = max(1, $j - 13); $k <= $j; $k++) {
                $ch = $closes[$k] - $closes[$k - 1];
                if ($ch > 0) $g2 += $ch; else $l2 += abs($ch);
            }
            $ag2 = $g2 / 14;
            $al2 = $l2 / 14;
            $rsi_vals[] = ($al2 > 0) ? (100 - (100 / (1 + $ag2 / $al2))) : 100;
        }
        $rc = count($rsi_vals);
        if ($rc >= 14) {
            $rsi_slice = array_slice($rsi_vals, -14);
            $rsi_min = min($rsi_slice);
            $rsi_max = max($rsi_slice);
            $rsi_last = $rsi_slice[count($rsi_slice) - 1];
            $stoch_rsi = ($rsi_max - $rsi_min > 0) ? round(($rsi_last - $rsi_min) / ($rsi_max - $rsi_min) * 100, 2) : 50;
            if ($stoch_rsi > 80) $stoch_rsi_signal = 'overbought';
            elseif ($stoch_rsi < 20) $stoch_rsi_signal = 'oversold';
        }
    }

    // ── On-Balance Volume (OBV) Trend ──
    $obv_trend = 'neutral';
    $obv_current = 0;
    if ($n >= 21) {
        $obv_series = array(0);
        for ($i = 1; $i < $n; $i++) {
            $v = (float)$prices[$i]['volume'];
            if ($closes[$i] > $closes[$i - 1]) $obv_series[] = $obv_series[count($obv_series) - 1] + $v;
            elseif ($closes[$i] < $closes[$i - 1]) $obv_series[] = $obv_series[count($obv_series) - 1] - $v;
            else $obv_series[] = $obv_series[count($obv_series) - 1];
        }
        $obv_current = $obv_series[count($obv_series) - 1];
        $obv_20ago = $obv_series[count($obv_series) - 21];
        if ($obv_current > $obv_20ago * 1.05) $obv_trend = 'accumulation';
        elseif ($obv_current < $obv_20ago * 0.95) $obv_trend = 'distribution';
    }

    // ── TTM Squeeze (Bollinger inside Keltner) ──
    $ttm_squeeze = false;
    $ttm_momentum = 0;
    if ($n >= 20) {
        // Keltner Channel: EMA(20) +/- 1.5 * ATR(10)
        $kelt_mid = $sma_20; // approximation using SMA
        $atr10 = 0;
        if ($n >= 11) {
            $tr10 = 0;
            for ($i = $n - 10; $i < $n; $i++) {
                $h10 = (float)$prices[$i]['high_price'];
                $l10 = (float)$prices[$i]['low_price'];
                $pc10 = $closes[$i - 1];
                $tr10 += max($h10 - $l10, abs($h10 - $pc10), abs($l10 - $pc10));
            }
            $atr10 = $tr10 / 10;
        }
        $kelt_upper = $kelt_mid + 1.5 * $atr10;
        $kelt_lower = $kelt_mid - 1.5 * $atr10;
        // Squeeze: BB inside KC
        $ttm_squeeze = ($bb_upper < $kelt_upper && $bb_lower > $kelt_lower);
        // Momentum: close - midline of (highest_high + lowest_low)/2 and SMA
        if ($n >= 20) {
            $hh20 = max(array_slice($closes, -20));
            $ll20 = min(array_slice($closes, -20));
            $ttm_momentum = round($current_price - (($hh20 + $ll20) / 2 + $sma_20) / 2, 4);
        }
    }

    // ── Supertrend (ATR-based, factor 3) ──
    $supertrend = 0;
    $supertrend_signal = 'neutral';
    if ($n >= 15 && $atr > 0) {
        $hl_mid = ((float)$latest['high_price'] + (float)$latest['low_price']) / 2;
        $st_upper = round($hl_mid + 3 * $atr, 4);
        $st_lower = round($hl_mid - 3 * $atr, 4);
        if ($current_price > $st_lower) {
            $supertrend = $st_lower;
            $supertrend_signal = 'bullish';
        } else {
            $supertrend = $st_upper;
            $supertrend_signal = 'bearish';
        }
    }

    // ── Ichimoku Cloud (simplified: Tenkan, Kijun, Senkou A/B) ──
    $ichimoku = array('tenkan' => 0, 'kijun' => 0, 'senkou_a' => 0, 'senkou_b' => 0, 'signal' => 'neutral');
    if ($n >= 52) {
        // Tenkan-sen (9-period midpoint)
        $h9 = 0; $l9 = 999999;
        for ($i = $n - 9; $i < $n; $i++) {
            if ((float)$prices[$i]['high_price'] > $h9) $h9 = (float)$prices[$i]['high_price'];
            if ((float)$prices[$i]['low_price'] < $l9) $l9 = (float)$prices[$i]['low_price'];
        }
        $tenkan = round(($h9 + $l9) / 2, 4);

        // Kijun-sen (26-period midpoint)
        $h26 = 0; $l26 = 999999;
        for ($i = $n - 26; $i < $n; $i++) {
            if ((float)$prices[$i]['high_price'] > $h26) $h26 = (float)$prices[$i]['high_price'];
            if ((float)$prices[$i]['low_price'] < $l26) $l26 = (float)$prices[$i]['low_price'];
        }
        $kijun = round(($h26 + $l26) / 2, 4);

        // Senkou Span A (midpoint of Tenkan + Kijun, plotted 26 ahead)
        $senkou_a = round(($tenkan + $kijun) / 2, 4);

        // Senkou Span B (52-period midpoint, plotted 26 ahead)
        $h52 = 0; $l52 = 999999;
        for ($i = $n - 52; $i < $n; $i++) {
            if ((float)$prices[$i]['high_price'] > $h52) $h52 = (float)$prices[$i]['high_price'];
            if ((float)$prices[$i]['low_price'] < $l52) $l52 = (float)$prices[$i]['low_price'];
        }
        $senkou_b = round(($h52 + $l52) / 2, 4);

        $ichi_signal = 'neutral';
        if ($current_price > $senkou_a && $current_price > $senkou_b && $tenkan > $kijun) $ichi_signal = 'strong_bullish';
        elseif ($current_price > max($senkou_a, $senkou_b)) $ichi_signal = 'bullish';
        elseif ($current_price < $senkou_a && $current_price < $senkou_b && $tenkan < $kijun) $ichi_signal = 'strong_bearish';
        elseif ($current_price < min($senkou_a, $senkou_b)) $ichi_signal = 'bearish';
        else $ichi_signal = 'in_cloud';

        $ichimoku = array('tenkan' => $tenkan, 'kijun' => $kijun, 'senkou_a' => $senkou_a, 'senkou_b' => $senkou_b, 'signal' => $ichi_signal);
    }

    // ── Mean Reversion Z-Score (20-day) ──
    $zscore_20 = 0;
    if ($n >= 20 && $sma_20 > 0) {
        $slice20 = array_slice($closes, -20);
        $mean20 = array_sum($slice20) / 20;
        $var20 = 0;
        foreach ($slice20 as $sv) $var20 += ($sv - $mean20) * ($sv - $mean20);
        $std20 = sqrt($var20 / 20);
        if ($std20 > 0) $zscore_20 = round(($current_price - $mean20) / $std20, 4);
    }

    // ── Rate of Change (ROC) 10-day ──
    $roc_10 = ($n >= 11 && $closes[$n - 11] > 0) ? round(($current_price - $closes[$n - 11]) / $closes[$n - 11] * 100, 2) : 0;

    // ── Williams %R (14-period) ──
    $williams_r = 0;
    if ($n >= 14) {
        $h14w = 0; $l14w = 999999;
        for ($i = $n - 14; $i < $n; $i++) {
            if ((float)$prices[$i]['high_price'] > $h14w) $h14w = (float)$prices[$i]['high_price'];
            if ((float)$prices[$i]['low_price'] < $l14w) $l14w = (float)$prices[$i]['low_price'];
        }
        $williams_r = ($h14w - $l14w > 0) ? round(($h14w - $current_price) / ($h14w - $l14w) * -100, 2) : 0;
    }

    // ── Commodity Channel Index (CCI, 20-period) ──
    $cci_20 = 0;
    if ($n >= 20) {
        $tp_vals = array();
        for ($i = $n - 20; $i < $n; $i++) {
            $tp_vals[] = ((float)$prices[$i]['high_price'] + (float)$prices[$i]['low_price'] + $closes[$i]) / 3;
        }
        $tp_mean = array_sum($tp_vals) / 20;
        $tp_mad = 0;
        foreach ($tp_vals as $tpv) $tp_mad += abs($tpv - $tp_mean);
        $tp_mad /= 20;
        if ($tp_mad > 0) $cci_20 = round(($tp_vals[19] - $tp_mean) / (0.015 * $tp_mad), 2);
    }

    // ── Trend Strength (ADX approximation via directional slope) ──
    $trend_strength = 'weak';
    if ($n >= 20 && $sma_20 > 0) {
        $slope_pct = abs($return_20d);
        if ($slope_pct > 15) $trend_strength = 'strong';
        elseif ($slope_pct > 5) $trend_strength = 'moderate';
    }

    // ── Enhanced Verdict (includes new indicators) ──
    // Add new signals to existing bull/bear count
    if ($stoch_rsi < 20) $bull_signals++;
    if ($stoch_rsi > 80) $bear_signals++;
    if ($obv_trend === 'accumulation') $bull_signals++;
    if ($obv_trend === 'distribution') $bear_signals++;
    if ($ichimoku['signal'] === 'strong_bullish' || $ichimoku['signal'] === 'bullish') $bull_signals++;
    if ($ichimoku['signal'] === 'strong_bearish' || $ichimoku['signal'] === 'bearish') $bear_signals++;
    if ($supertrend_signal === 'bullish') $bull_signals++;
    if ($supertrend_signal === 'bearish') $bear_signals++;
    if ($ttm_squeeze && $ttm_momentum > 0) $bull_signals++;
    if ($ttm_squeeze && $ttm_momentum < 0) $bear_signals++;
    if ($cci_20 > 100) $bear_signals++; // overbought
    if ($cci_20 < -100) $bull_signals++; // oversold

    // Recompute verdict with all indicators
    $total_signals = $bull_signals + $bear_signals;
    $bull_pct = ($total_signals > 0) ? round($bull_signals / $total_signals * 100) : 50;
    if ($bull_pct >= 70) $overall_signal = 'Strong Buy';
    elseif ($bull_pct >= 55) $overall_signal = 'Buy';
    elseif ($bull_pct >= 45) $overall_signal = 'Neutral';
    elseif ($bull_pct >= 30) $overall_signal = 'Sell';
    else $overall_signal = 'Strong Sell';

    $response['indicators'] = array(
        'rsi_14' => $rsi, 'rsi_signal' => $rsi_signal,
        'stochastic_rsi' => $stoch_rsi, 'stochastic_rsi_signal' => $stoch_rsi_signal,
        'macd' => $macd, 'macd_signal' => $macd_signal_line, 'macd_histogram' => $macd_histogram,
        'atr_14' => $atr, 'atr_pct' => $atr_pct,
        'bollinger_upper' => $bb_upper, 'bollinger_lower' => $bb_lower, 'bollinger_pct_b' => $bb_pct,
        'ttm_squeeze' => $ttm_squeeze, 'ttm_momentum' => $ttm_momentum,
        'supertrend' => $supertrend, 'supertrend_signal' => $supertrend_signal,
        'ichimoku' => $ichimoku,
        'obv_trend' => $obv_trend,
        'zscore_20d' => $zscore_20,
        'roc_10d' => $roc_10,
        'williams_r_14' => $williams_r,
        'cci_20' => $cci_20,
        'trend_strength' => $trend_strength,
        'volatility_20d_annualized' => $vol_20d
    );
    $response['verdict'] = array(
        'signal' => $overall_signal, 'bull_pct' => $bull_pct,
        'bull_signals' => $bull_signals, 'bear_signals' => $bear_signals,
        'total_indicators' => $total_signals
    );
    $response['pick_history'] = $pick_history;

// ═══════════════════════════════════════════
// PORTFOLIO ANALYTICS — Full pro-level metrics
// ═══════════════════════════════════════════
} elseif ($action === 'portfolio_analytics') {
    $algo_filter = isset($_GET['algorithms']) ? trim($_GET['algorithms']) : '';
    $tp = (float)(isset($_GET['take_profit']) ? $_GET['take_profit'] : 50);
    $sl = (float)(isset($_GET['stop_loss']) ? $_GET['stop_loss'] : 10);
    $mhd = (int)(isset($_GET['max_hold_days']) ? $_GET['max_hold_days'] : 30);

    // Run backtest inline
    $where_algo = '';
    if ($algo_filter !== '') {
        $parts = explode(',', $algo_filter);
        $esc = array();
        foreach ($parts as $p) {
            $p = trim($p);
            if ($p !== '') $esc[] = "'" . $conn->real_escape_string($p) . "'";
        }
        if (count($esc) > 0) $where_algo = " AND sp.algorithm_name IN (" . implode(',', $esc) . ")";
    }

    $sql = "SELECT sp.*, s.company_name FROM stock_picks sp
            LEFT JOIN stocks s ON sp.ticker = s.ticker
            WHERE sp.entry_price > 0 $where_algo
            ORDER BY sp.pick_date ASC";
    $picks_res = $conn->query($sql);

    $cap = 10000;
    $capital = $cap;
    $peak_c = $cap;
    $max_dd_c = 0;
    $trades_a = array();
    $returns_a = array();
    $equity_a = array();
    $equity_a[] = array('date' => '', 'value' => $cap);

    if ($picks_res) {
        while ($pick = $picks_res->fetch_assoc()) {
            $entry = (float)$pick['entry_price'];
            $pdate = $pick['pick_date'];
            $algo = $pick['algorithm_name'];
            $tck = $pick['ticker'];

            $eff_entry = $entry * 1.001;
            $pos = $capital * 0.10;
            if ($pos < $eff_entry) continue;
            $shares = (int)floor($pos / $eff_entry);
            if ($shares <= 0) continue;

            $safe_t = $conn->real_escape_string($tck);
            $safe_d = $conn->real_escape_string($pdate);
            $pr = $conn->query("SELECT trade_date, high_price, low_price, close_price FROM daily_prices
                                WHERE ticker='$safe_t' AND trade_date >= '$safe_d'
                                ORDER BY trade_date ASC LIMIT " . ($mhd + 5));

            $dc = 0;
            $exit_p = $entry;
            $exit_d = $pdate;
            $ex_r = 'end_of_data';
            $dclose = 0;

            if ($pr && $pr->num_rows > 0) {
                while ($day = $pr->fetch_assoc()) {
                    $dc++;
                    $dh = (float)$day['high_price'];
                    $dl = (float)$day['low_price'];
                    $dclose = (float)$day['close_price'];
                    $dd = $day['trade_date'];

                    $tp_p = $eff_entry * (1 + $tp / 100);
                    $sl_p = $eff_entry * (1 - $sl / 100);

                    if ($dl <= $sl_p && $sl < 999) { $exit_p = $sl_p; $exit_d = $dd; $ex_r = 'stop_loss'; break; }
                    if ($dh >= $tp_p && $tp < 999) { $exit_p = $tp_p; $exit_d = $dd; $ex_r = 'take_profit'; break; }
                    if ($dc >= $mhd) { $exit_p = $dclose; $exit_d = $dd; $ex_r = 'max_hold'; break; }
                }
                if ($ex_r === 'end_of_data' && $dc > 0 && $dclose > 0) $exit_p = $dclose;
            }

            $eff_exit = $exit_p * 0.999;
            $npnl = ($eff_exit - $eff_entry) * $shares;
            $rpct = ($eff_entry * $shares > 0) ? ($npnl / ($eff_entry * $shares)) * 100 : 0;

            $trades_a[] = array(
                'ticker' => $tck, 'algorithm' => $algo,
                'entry_date' => $pdate, 'exit_date' => $exit_d,
                'return_pct' => round($rpct, 4), 'net_profit' => round($npnl, 2),
                'hold_days' => $dc, 'exit_reason' => $ex_r
            );

            $capital += $npnl;
            $returns_a[] = $rpct;

            if ($capital > $peak_c) $peak_c = $capital;
            $dd_val = ($peak_c > 0) ? (($peak_c - $capital) / $peak_c) * 100 : 0;
            if ($dd_val > $max_dd_c) $max_dd_c = $dd_val;

            $equity_a[] = array('date' => $exit_d, 'value' => round($capital, 2));
        }
    }

    $nt = count($trades_a);
    $nw = 0;
    $nl = 0;
    $tw = 0;
    $tl = 0;
    $gw = 0;
    $gl = 0;
    foreach ($trades_a as $t) {
        if ($t['net_profit'] > 0) { $nw++; $tw += $t['return_pct']; $gw += $t['net_profit']; }
        else { $nl++; $tl += abs($t['return_pct']); $gl += abs($t['net_profit']); }
    }

    $wr = ($nt > 0) ? round($nw / $nt * 100, 2) : 0;
    $aw = ($nw > 0) ? round($tw / $nw, 4) : 0;
    $al = ($nl > 0) ? round($tl / $nl, 4) : 0;
    $pf = ($gl > 0) ? round($gw / $gl, 4) : ($gw > 0 ? 999 : 0);
    $total_ret = ($cap > 0) ? round(($capital - $cap) / $cap * 100, 4) : 0;

    // Annualized
    $ann = 0;
    if ($nt >= 2) {
        $fd = strtotime($trades_a[0]['entry_date']);
        $ld = strtotime($trades_a[$nt-1]['exit_date']);
        $days = ($ld - $fd) / 86400;
        if ($days > 30 && $capital > 0) {
            $yrs = $days / 365.25;
            if ($yrs > 0) $ann = round((pow($capital / $cap, 1 / $yrs) - 1) * 100, 4);
        }
    }

    // Sharpe, Sortino, Calmar
    $sharpe = 0;
    $sortino = 0;
    if (count($returns_a) > 1) {
        $mean = array_sum($returns_a) / count($returns_a);
        $v = 0;
        $dv = 0;
        $dc2 = 0;
        foreach ($returns_a as $r) {
            $v += ($r - $mean) * ($r - $mean);
            if ($r < 0) { $dv += $r * $r; $dc2++; }
        }
        $std = sqrt($v / count($returns_a));
        if ($std > 0) $sharpe = round($mean / $std, 4);
        if ($dc2 > 0) {
            $ds = sqrt($dv / $dc2);
            if ($ds > 0) $sortino = round($mean / $ds, 4);
        }
    }
    $calmar = ($max_dd_c > 0 && $ann != 0) ? round($ann / $max_dd_c, 4) : 0;
    $recov = ($max_dd_c > 0) ? round(abs($total_ret) / $max_dd_c, 4) : 0;
    if ($total_ret < 0) $recov = -$recov;

    // Kelly
    $kelly = 0;
    if ($al > 0 && $nw > 0) {
        $wrd = $nw / $nt;
        $wlr = $aw / $al;
        $kelly = round(($wrd - ((1 - $wrd) / $wlr)) * 100, 4);
        if ($kelly < 0) $kelly = 0;
    }

    // VaR
    $var95 = 0;
    $cvar95 = 0;
    if (count($returns_a) >= 10) {
        $sr2 = $returns_a;
        sort($sr2);
        $i5 = (int)floor(count($sr2) * 0.05);
        if ($i5 < count($sr2)) $var95 = round($sr2[$i5], 4);
        if ($i5 > 0) {
            $ts = 0;
            for ($i = 0; $i < $i5; $i++) $ts += $sr2[$i];
            $cvar95 = round($ts / $i5, 4);
        }
    }

    // Consecutive streaks
    $mc_w = 0; $mc_l = 0; $cc_w = 0; $cc_l = 0;
    foreach ($trades_a as $t) {
        if ($t['net_profit'] > 0) { $cc_w++; $cc_l = 0; if ($cc_w > $mc_w) $mc_w = $cc_w; }
        else { $cc_l++; $cc_w = 0; if ($cc_l > $mc_l) $mc_l = $cc_l; }
    }

    // Monthly returns
    $monthly = array();
    foreach ($trades_a as $t) {
        $m = substr($t['exit_date'], 0, 7);
        if (!isset($monthly[$m])) $monthly[$m] = 0;
        $monthly[$m] += $t['return_pct'];
    }
    $pos_m = 0;
    $neg_m = 0;
    foreach ($monthly as $mv) {
        if ($mv > 0) $pos_m++; else $neg_m++;
    }

    // Skewness/Kurtosis
    $skew = 0;
    $kurt = 0;
    if (count($returns_a) > 2) {
        $nc = count($returns_a);
        $mr = array_sum($returns_a) / $nc;
        $m2 = 0; $m3 = 0; $m4 = 0;
        foreach ($returns_a as $r) {
            $d = $r - $mr;
            $m2 += $d * $d;
            $m3 += $d * $d * $d;
            $m4 += $d * $d * $d * $d;
        }
        $m2 /= $nc; $m3 /= $nc; $m4 /= $nc;
        if ($m2 > 0) {
            $sdr = sqrt($m2);
            $skew = round($m3 / ($sdr * $sdr * $sdr), 4);
            $kurt = round($m4 / ($m2 * $m2) - 3, 4);
        }
    }

    // Drawdown periods
    $drawdowns = array();
    $dd_start = '';
    $dd_peak_val = $cap;
    $in_dd = false;
    foreach ($equity_a as $ec) {
        if ($ec['value'] > $dd_peak_val) {
            if ($in_dd && $dd_start !== '') {
                $drawdowns[] = array('start' => $dd_start, 'end' => $ec['date'],
                    'depth_pct' => round(($dd_peak_val - $dd_trough) / $dd_peak_val * 100, 2));
            }
            $dd_peak_val = $ec['value'];
            $in_dd = false;
        } elseif ($ec['value'] < $dd_peak_val) {
            if (!$in_dd) {
                $dd_start = $ec['date'];
                $dd_trough = $ec['value'];
                $in_dd = true;
            }
            if ($ec['value'] < $dd_trough) $dd_trough = $ec['value'];
        }
    }

    $response['portfolio'] = array(
        'initial_capital' => $cap,
        'final_value' => round($capital, 2),
        'total_return_pct' => $total_ret,
        'annualized_return_pct' => $ann,
        'total_trades' => $nt,
        'winning_trades' => $nw,
        'losing_trades' => $nl,
        'win_rate' => $wr,
        'avg_win_pct' => $aw,
        'avg_loss_pct' => $al,
        'payoff_ratio' => ($al > 0) ? round($aw / $al, 4) : 0,
        'profit_factor' => $pf,
        'max_drawdown_pct' => round($max_dd_c, 4),
        'sharpe_ratio' => $sharpe,
        'sortino_ratio' => $sortino,
        'calmar_ratio' => $calmar,
        'recovery_factor' => $recov,
        'kelly_criterion_pct' => $kelly,
        'var_95' => $var95,
        'cvar_95' => $cvar95,
        'max_consecutive_wins' => $mc_w,
        'max_consecutive_losses' => $mc_l,
        'skewness' => $skew,
        'kurtosis' => $kurt,
        'positive_months' => $pos_m,
        'negative_months' => $neg_m,
        'monthly_win_rate' => (($pos_m + $neg_m) > 0) ? round($pos_m / ($pos_m + $neg_m) * 100, 2) : 0
    );
    $response['monthly_returns'] = $monthly;
    $response['equity_curve'] = $equity_a;
    $response['drawdowns'] = $drawdowns;

// ═══════════════════════════════════════════
// ALGORITHM REPORT — Per-algo deep analysis
// ═══════════════════════════════════════════
} elseif ($action === 'algorithm_report') {
    $algo_name = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : '';

    // Get all algorithms with picks
    $sql = "SELECT DISTINCT sp.algorithm_name, a.family, a.description, a.algo_type, a.ideal_timeframe,
                   COUNT(*) as pick_count, AVG(sp.score) as avg_score
            FROM stock_picks sp
            LEFT JOIN algorithms a ON sp.algorithm_name = a.name
            WHERE sp.entry_price > 0";
    if ($algo_name !== '') {
        $sql .= " AND sp.algorithm_name = '" . $conn->real_escape_string($algo_name) . "'";
    }
    $sql .= " GROUP BY sp.algorithm_name ORDER BY pick_count DESC";

    $res = $conn->query($sql);
    $algos_data = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            // Get date range for this algo
            $aname_safe = $conn->real_escape_string($row['algorithm_name']);
            $dr = $conn->query("SELECT MIN(pick_date) as first_pick, MAX(pick_date) as last_pick FROM stock_picks WHERE algorithm_name='$aname_safe'");
            $dates = ($dr) ? $dr->fetch_assoc() : array('first_pick' => '', 'last_pick' => '');

            // Get top tickers
            $tt = $conn->query("SELECT ticker, COUNT(*) as cnt FROM stock_picks WHERE algorithm_name='$aname_safe' GROUP BY ticker ORDER BY cnt DESC LIMIT 5");
            $top_tickers = array();
            if ($tt) {
                while ($tr = $tt->fetch_assoc()) $top_tickers[] = $tr;
            }

            $algos_data[] = array(
                'name' => $row['algorithm_name'],
                'family' => $row['family'],
                'description' => $row['description'],
                'type' => $row['algo_type'],
                'timeframe' => $row['ideal_timeframe'],
                'pick_count' => (int)$row['pick_count'],
                'avg_score' => round((float)$row['avg_score'], 2),
                'first_pick' => $dates['first_pick'],
                'last_pick' => $dates['last_pick'],
                'top_tickers' => $top_tickers
            );
        }
    }
    $response['algorithms'] = $algos_data;
    $response['total_algorithms'] = count($algos_data);

// ═══════════════════════════════════════════
// RISK REPORT — Comprehensive risk analysis
// ═══════════════════════════════════════════
} elseif ($action === 'risk_report') {
    // Get all picks with price data for risk analysis
    $sql = "SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.entry_price,
                   dp_1.close_price as d1_close, dp_5.close_price as d5_close
            FROM stock_picks sp
            LEFT JOIN daily_prices dp_1 ON sp.ticker = dp_1.ticker AND dp_1.trade_date = (
                SELECT MIN(d.trade_date) FROM daily_prices d WHERE d.ticker = sp.ticker AND d.trade_date > sp.pick_date
            )
            LEFT JOIN daily_prices dp_5 ON sp.ticker = dp_5.ticker AND dp_5.trade_date = (
                SELECT MIN(d.trade_date) FROM daily_prices d WHERE d.ticker = sp.ticker AND d.trade_date >= DATE_ADD(sp.pick_date, INTERVAL 5 DAY)
            )
            WHERE sp.entry_price > 0
            ORDER BY sp.pick_date DESC LIMIT 200";
    $res = $conn->query($sql);

    $day1_returns = array();
    $day5_returns = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $ep = (float)$row['entry_price'];
            if ($ep > 0) {
                if ($row['d1_close'] && (float)$row['d1_close'] > 0) {
                    $day1_returns[] = round(((float)$row['d1_close'] - $ep) / $ep * 100, 4);
                }
                if ($row['d5_close'] && (float)$row['d5_close'] > 0) {
                    $day5_returns[] = round(((float)$row['d5_close'] - $ep) / $ep * 100, 4);
                }
            }
        }
    }

    // Day-1 risk stats
    $d1_stats = array('count' => count($day1_returns));
    if (count($day1_returns) > 0) {
        sort($day1_returns);
        $d1_mean = array_sum($day1_returns) / count($day1_returns);
        $d1_stats['mean'] = round($d1_mean, 4);
        $d1_stats['median'] = round($day1_returns[(int)(count($day1_returns) / 2)], 4);
        $d1_stats['min'] = round($day1_returns[0], 4);
        $d1_stats['max'] = round($day1_returns[count($day1_returns) - 1], 4);
        $d1_pos = 0;
        foreach ($day1_returns as $r) { if ($r > 0) $d1_pos++; }
        $d1_stats['positive_pct'] = round($d1_pos / count($day1_returns) * 100, 2);

        $i5 = (int)floor(count($day1_returns) * 0.05);
        $d1_stats['var_95'] = round($day1_returns[$i5], 4);
        $d1_stats['var_99'] = round($day1_returns[(int)floor(count($day1_returns) * 0.01)], 4);
    }

    // Day-5 risk stats
    $d5_stats = array('count' => count($day5_returns));
    if (count($day5_returns) > 0) {
        sort($day5_returns);
        $d5_mean = array_sum($day5_returns) / count($day5_returns);
        $d5_stats['mean'] = round($d5_mean, 4);
        $d5_stats['median'] = round($day5_returns[(int)(count($day5_returns) / 2)], 4);
        $d5_stats['min'] = round($day5_returns[0], 4);
        $d5_stats['max'] = round($day5_returns[count($day5_returns) - 1], 4);
        $d5_pos = 0;
        foreach ($day5_returns as $r) { if ($r > 0) $d5_pos++; }
        $d5_stats['positive_pct'] = round($d5_pos / count($day5_returns) * 100, 2);

        $i5_5 = (int)floor(count($day5_returns) * 0.05);
        $d5_stats['var_95'] = round($day5_returns[$i5_5], 4);
    }

    // Worst picks ever
    $worst = $conn->query("SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.entry_price, sp.score,
                                  s.company_name
                           FROM stock_picks sp
                           LEFT JOIN stocks s ON sp.ticker = s.ticker
                           WHERE sp.entry_price > 0
                           ORDER BY sp.score ASC LIMIT 10");
    $worst_picks = array();
    if ($worst) {
        while ($w = $worst->fetch_assoc()) $worst_picks[] = $w;
    }

    $response['day1_risk'] = $d1_stats;
    $response['day5_risk'] = $d5_stats;
    $response['worst_picks'] = $worst_picks;

// ═══════════════════════════════════════════
// LEADERBOARD — Multi-metric rankings
// ═══════════════════════════════════════════
} elseif ($action === 'leaderboard') {
    // Run all algorithms through Momentum Ride scenario (the best one)
    $algo_res = $conn->query("SELECT DISTINCT algorithm_name FROM stock_picks WHERE entry_price > 0 ORDER BY algorithm_name");
    $board = array();

    if ($algo_res) {
        while ($arow = $algo_res->fetch_assoc()) {
            $aname = $arow['algorithm_name'];
            $safe_a = $conn->real_escape_string($aname);

            // Quick metrics: count trades and get basic win/loss
            $sql = "SELECT sp.ticker, sp.pick_date, sp.entry_price, sp.algorithm_name
                    FROM stock_picks sp WHERE sp.algorithm_name='$safe_a' AND sp.entry_price > 0
                    ORDER BY sp.pick_date ASC";
            $pr = $conn->query($sql);

            $picks = 0;
            $wins = 0;
            $losses = 0;
            $total_pnl = 0;
            $returns_b = array();

            if ($pr) {
                while ($pick = $pr->fetch_assoc()) {
                    $ep = (float)$pick['entry_price'];
                    $tck = $pick['ticker'];
                    $pd = $pick['pick_date'];

                    // Get 30-day price movement (momentum ride)
                    $st = $conn->real_escape_string($tck);
                    $sd = $conn->real_escape_string($pd);
                    $dp = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$st' AND trade_date > '$sd' ORDER BY trade_date ASC LIMIT 30");

                    $exit_p = $ep;
                    if ($dp && $dp->num_rows > 0) {
                        $dc = 0;
                        while ($day = $dp->fetch_assoc()) {
                            $dc++;
                            $cp = (float)$day['close_price'];
                            // TP 50% or SL 10%
                            if ($cp >= $ep * 1.50) { $exit_p = $ep * 1.50; break; }
                            if ($cp <= $ep * 0.90) { $exit_p = $ep * 0.90; break; }
                            if ($dc >= 30) { $exit_p = $cp; break; }
                            $exit_p = $cp;
                        }
                    }

                    $rpct = ($ep > 0) ? (($exit_p - $ep) / $ep * 100) : 0;
                    $picks++;
                    if ($rpct > 0) $wins++;
                    else $losses++;
                    $total_pnl += $rpct;
                    $returns_b[] = $rpct;
                }
            }

            if ($picks === 0) continue;

            $wr = round($wins / $picks * 100, 2);
            $avg_ret = round($total_pnl / $picks, 4);

            // Sharpe
            $sh = 0;
            if (count($returns_b) > 1) {
                $mb = array_sum($returns_b) / count($returns_b);
                $vb = 0;
                foreach ($returns_b as $rb) $vb += ($rb - $mb) * ($rb - $mb);
                $sb = sqrt($vb / count($returns_b));
                if ($sb > 0) $sh = round($mb / $sb, 4);
            }

            // Composite score = (Sharpe * 30) + (WinRate * 0.3) + (AvgReturn * 2) - (Losses * 0.5)
            $composite = round($sh * 30 + $wr * 0.3 + $avg_ret * 2 - $losses * 0.5, 2);

            $board[] = array(
                'algorithm' => $aname,
                'picks' => $picks,
                'wins' => $wins,
                'losses' => $losses,
                'win_rate' => $wr,
                'avg_return_pct' => $avg_ret,
                'total_return_pct' => round($total_pnl, 4),
                'sharpe_ratio' => $sh,
                'composite_score' => $composite
            );
        }
    }

    // Sort by composite score
    $scores = array();
    for ($i = 0; $i < count($board); $i++) {
        $scores[$i] = $board[$i]['composite_score'];
    }
    arsort($scores);
    $sorted_board = array();
    $rank = 1;
    foreach ($scores as $idx => $val) {
        $board[$idx]['rank'] = $rank++;
        $sorted_board[] = $board[$idx];
    }

    $response['leaderboard'] = $sorted_board;
    $response['ranking_method'] = 'composite_score = (Sharpe * 30) + (WinRate * 0.3) + (AvgReturn * 2) - (Losses * 0.5)';
    $response['scenario'] = 'Momentum Ride (TP 50%, SL 10%, 30-day hold)';

// ═══════════════════════════════════════════
// WALK-FORWARD — Walk-forward validation
// ═══════════════════════════════════════════
} elseif ($action === 'walk_forward') {
    $algo_filter = isset($_GET['algorithms']) ? trim($_GET['algorithms']) : '';
    $window_months = (int)(isset($_GET['window']) ? $_GET['window'] : 3);
    if ($window_months < 1) $window_months = 3;
    if ($window_months > 12) $window_months = 12;

    // Get all picks ordered by date
    $where_algo = '';
    if ($algo_filter !== '') {
        $parts = explode(',', $algo_filter);
        $esc = array();
        foreach ($parts as $p) {
            $p = trim($p);
            if ($p !== '') $esc[] = "'" . $conn->real_escape_string($p) . "'";
        }
        if (count($esc) > 0) $where_algo = " AND sp.algorithm_name IN (" . implode(',', $esc) . ")";
    }

    $sql = "SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.entry_price
            FROM stock_picks sp WHERE sp.entry_price > 0 $where_algo
            ORDER BY sp.pick_date ASC";
    $res = $conn->query($sql);

    $all_picks = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) $all_picks[] = $row;
    }

    if (count($all_picks) === 0) {
        $response['ok'] = false;
        $response['error'] = 'No picks found';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    // Split into windows
    $first_date = $all_picks[0]['pick_date'];
    $last_date = $all_picks[count($all_picks) - 1]['pick_date'];

    $windows = array();
    $current_start = $first_date;
    while (strtotime($current_start) < strtotime($last_date)) {
        $window_end = date('Y-m-d', strtotime($current_start . " + $window_months months"));
        $window_picks = array();
        foreach ($all_picks as $p) {
            if ($p['pick_date'] >= $current_start && $p['pick_date'] < $window_end) {
                $window_picks[] = $p;
            }
        }

        if (count($window_picks) > 0) {
            // Run simple backtest on this window
            $w_wins = 0;
            $w_losses = 0;
            $w_pnl = 0;
            foreach ($window_picks as $wp) {
                $ep = (float)$wp['entry_price'];
                $tck = $conn->real_escape_string($wp['ticker']);
                $pd = $conn->real_escape_string($wp['pick_date']);
                $dp = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$tck' AND trade_date > '$pd' ORDER BY trade_date ASC LIMIT 30");

                $exit_p = $ep;
                if ($dp && $dp->num_rows > 0) {
                    $dc = 0;
                    while ($day = $dp->fetch_assoc()) {
                        $dc++;
                        $cp = (float)$day['close_price'];
                        if ($cp >= $ep * 1.50) { $exit_p = $ep * 1.50; break; }
                        if ($cp <= $ep * 0.90) { $exit_p = $ep * 0.90; break; }
                        if ($dc >= 30) { $exit_p = $cp; break; }
                        $exit_p = $cp;
                    }
                }

                $rpct = ($ep > 0) ? (($exit_p - $ep) / $ep * 100) : 0;
                if ($rpct > 0) $w_wins++; else $w_losses++;
                $w_pnl += $rpct;
            }

            $w_total = $w_wins + $w_losses;
            $windows[] = array(
                'period' => $current_start . ' to ' . $window_end,
                'picks' => $w_total,
                'wins' => $w_wins,
                'losses' => $w_losses,
                'win_rate' => ($w_total > 0) ? round($w_wins / $w_total * 100, 2) : 0,
                'total_return_pct' => round($w_pnl, 4),
                'avg_return_pct' => ($w_total > 0) ? round($w_pnl / $w_total, 4) : 0
            );
        }

        $current_start = $window_end;
    }

    // Consistency score: how many windows are profitable
    $profitable_windows = 0;
    foreach ($windows as $w) {
        if ($w['total_return_pct'] > 0) $profitable_windows++;
    }
    $consistency = (count($windows) > 0) ? round($profitable_windows / count($windows) * 100, 2) : 0;

    $response['windows'] = $windows;
    $response['total_windows'] = count($windows);
    $response['profitable_windows'] = $profitable_windows;
    $response['consistency_pct'] = $consistency;
    $response['window_months'] = $window_months;
    $response['verdict'] = ($consistency >= 60) ? 'ROBUST' : (($consistency >= 40) ? 'MODERATE' : 'WEAK');

// ═══════════════════════════════════════════
// REGIME ANALYSIS — Performance by market regime
// ═══════════════════════════════════════════
} elseif ($action === 'regime_analysis') {
    // Classify each pick's period into a regime based on SPY movement
    // We approximate regime using the pick date vs SPY performance
    $sql = "SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.entry_price
            FROM stock_picks sp WHERE sp.entry_price > 0
            ORDER BY sp.pick_date ASC";
    $res = $conn->query($sql);

    $regime_stats = array(
        'bull' => array('picks' => 0, 'wins' => 0, 'pnl' => 0),
        'bear' => array('picks' => 0, 'wins' => 0, 'pnl' => 0),
        'sideways' => array('picks' => 0, 'wins' => 0, 'pnl' => 0)
    );

    // Get SPY prices for regime classification
    $spy_prices = array();
    $spy_res = $conn->query("SELECT trade_date, close_price FROM daily_prices WHERE ticker='SPY' ORDER BY trade_date ASC");
    if ($spy_res) {
        while ($sp = $spy_res->fetch_assoc()) {
            $spy_prices[$sp['trade_date']] = (float)$sp['close_price'];
        }
    }

    if ($res) {
        while ($pick = $res->fetch_assoc()) {
            $ep = (float)$pick['entry_price'];
            $tck = $conn->real_escape_string($pick['ticker']);
            $pd = $conn->real_escape_string($pick['pick_date']);

            // Determine regime: check SPY 20-day trend around pick date
            $regime = 'sideways';
            $spy_dates = array_keys($spy_prices);
            $pick_ts = strtotime($pick['pick_date']);

            // Find SPY close 20 days before and on pick date
            $spy_before = 0;
            $spy_current = 0;
            foreach ($spy_dates as $sd) {
                $sd_ts = strtotime($sd);
                if ($sd_ts <= $pick_ts) $spy_current = $spy_prices[$sd];
                if ($sd_ts <= $pick_ts - (20 * 86400)) $spy_before = $spy_prices[$sd];
            }
            if ($spy_before > 0 && $spy_current > 0) {
                $spy_change = (($spy_current - $spy_before) / $spy_before) * 100;
                if ($spy_change > 3) $regime = 'bull';
                elseif ($spy_change < -3) $regime = 'bear';
                else $regime = 'sideways';
            }

            // Get trade result
            $dp = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$tck' AND trade_date > '$pd' ORDER BY trade_date ASC LIMIT 30");
            $exit_p = $ep;
            if ($dp && $dp->num_rows > 0) {
                $dc = 0;
                while ($day = $dp->fetch_assoc()) {
                    $dc++;
                    $cp = (float)$day['close_price'];
                    if ($cp >= $ep * 1.50) { $exit_p = $ep * 1.50; break; }
                    if ($cp <= $ep * 0.90) { $exit_p = $ep * 0.90; break; }
                    if ($dc >= 30) { $exit_p = $cp; break; }
                    $exit_p = $cp;
                }
            }

            $rpct = ($ep > 0) ? (($exit_p - $ep) / $ep * 100) : 0;
            $regime_stats[$regime]['picks']++;
            if ($rpct > 0) $regime_stats[$regime]['wins']++;
            $regime_stats[$regime]['pnl'] += $rpct;
        }
    }

    // Calculate stats per regime
    $regime_results = array();
    foreach ($regime_stats as $rname => $rs) {
        $regime_results[] = array(
            'regime' => $rname,
            'picks' => $rs['picks'],
            'wins' => $rs['wins'],
            'losses' => $rs['picks'] - $rs['wins'],
            'win_rate' => ($rs['picks'] > 0) ? round($rs['wins'] / $rs['picks'] * 100, 2) : 0,
            'total_return_pct' => round($rs['pnl'], 4),
            'avg_return_pct' => ($rs['picks'] > 0) ? round($rs['pnl'] / $rs['picks'], 4) : 0
        );
    }

    $response['regimes'] = $regime_results;
    $response['classification'] = 'SPY 20-day: >3% = bull, <-3% = bear, else sideways';

} elseif ($action === 'top_picks') {
    // ─── Cross-Asset Top Picks ───
    // Best TP/SL for day trades vs swing trades
    $day_tp = 5; $day_sl = 3; $day_hold = 2;
    $swing_tp = 15; $swing_sl = 8; $swing_hold = 14;

    // --- Top 10 Stock Picks ---
    $sql = "SELECT sp.ticker, sp.algorithm_name, sp.pick_date, sp.entry_price, sp.score, sp.rating, sp.risk_level,
                   s.company_name,
                   dp.close_price as latest_price, dp.trade_date as price_date
            FROM stock_picks sp
            LEFT JOIN stocks s ON sp.ticker = s.ticker
            LEFT JOIN daily_prices dp ON sp.ticker = dp.ticker AND dp.trade_date = (SELECT MAX(d2.trade_date) FROM daily_prices d2 WHERE d2.ticker = sp.ticker)
            ORDER BY sp.score DESC, sp.pick_date DESC
            LIMIT 10";
    $res = $conn->query($sql);
    $top_stocks = array();
    if ($res) {
        $rank = 0;
        while ($row = $res->fetch_assoc()) {
            $rank++;
            $entry = (float)$row['entry_price'];
            $latest = (float)$row['latest_price'];
            $current_return = ($entry > 0) ? round(($latest - $entry) / $entry * 100, 2) : 0;
            $top_stocks[] = array(
                'rank' => $rank,
                'ticker' => $row['ticker'],
                'company_name' => $row['company_name'],
                'algorithm' => $row['algorithm_name'],
                'pick_date' => $row['pick_date'],
                'entry_price' => $entry,
                'latest_price' => $latest,
                'price_date' => $row['price_date'],
                'current_return_pct' => $current_return,
                'swing_target' => round($entry * (1 + $swing_tp / 100), 2),
                'swing_stop' => round($entry * (1 - $swing_sl / 100), 2),
                'day_target' => round($entry * (1 + $day_tp / 100), 2),
                'day_stop' => round($entry * (1 - $day_sl / 100), 2),
                'score' => (int)$row['score'],
                'rating' => $row['rating'],
                'risk_level' => $row['risk_level']
            );
        }
    }
    $response['top_stocks'] = $top_stocks;

    // --- Day Trading Picks (highest score, tightest params) ---
    $day_sql = "SELECT sp.ticker, sp.algorithm_name, sp.entry_price, sp.score, sp.rating,
                       s.company_name, dp.close_price as latest_price
                FROM stock_picks sp
                LEFT JOIN stocks s ON sp.ticker = s.ticker
                LEFT JOIN daily_prices dp ON sp.ticker = dp.ticker AND dp.trade_date = (SELECT MAX(d2.trade_date) FROM daily_prices d2 WHERE d2.ticker = sp.ticker)
                WHERE sp.score >= 70
                ORDER BY sp.score DESC
                LIMIT 5";
    $res = $conn->query($day_sql);
    $day_picks = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $entry = (float)$row['entry_price'];
            $day_picks[] = array(
                'ticker' => $row['ticker'],
                'company_name' => $row['company_name'],
                'algorithm' => $row['algorithm_name'],
                'entry_price' => $entry,
                'target' => round($entry * (1 + $day_tp / 100), 2),
                'stop_loss' => round($entry * (1 - $day_sl / 100), 2),
                'latest_price' => (float)$row['latest_price'],
                'score' => (int)$row['score'],
                'rating' => $row['rating'],
                'hold' => '1-2 days'
            );
        }
    }
    $response['day_trading'] = $day_picks;

    // --- Top 5 Mutual Fund Picks ---
    $mf_sql = "SELECT fp.symbol, fp.algorithm_name, fp.pick_date, fp.entry_nav, fp.score, fp.rating, fp.risk_level,
                      f.fund_name, f.fund_family, f.category, f.morningstar_rating
               FROM mf2_fund_picks fp
               LEFT JOIN mf2_funds f ON fp.symbol = f.symbol
               ORDER BY fp.score DESC
               LIMIT 5";
    $res = $conn->query($mf_sql);
    $top_mf = array();
    if ($res) { while ($row = $res->fetch_assoc()) $top_mf[] = $row; }
    $response['top_mutual_funds'] = $top_mf;

    // --- Top 5 Forex Picks ---
    $fx_sql = "SELECT pp.symbol, pp.algorithm_name, pp.pick_date, pp.entry_price, pp.direction, pp.score, pp.rating, pp.risk_level,
                      p.base_currency, p.quote_currency, p.category
               FROM fxp_pair_picks pp
               LEFT JOIN fxp_pairs p ON pp.symbol = p.symbol
               ORDER BY pp.score DESC
               LIMIT 5";
    $res = $conn->query($fx_sql);
    $top_fx = array();
    if ($res) { while ($row = $res->fetch_assoc()) $top_fx[] = $row; }
    $response['top_forex'] = $top_fx;

    // --- Top 5 Crypto Picks ---
    $cr_sql = "SELECT pp.symbol, pp.algorithm_name, pp.pick_date, pp.entry_price, pp.direction, pp.score, pp.rating, pp.risk_level,
                      p.base_asset as base_currency, p.quote_asset as quote_currency
               FROM cr_pair_picks pp
               LEFT JOIN cr_pairs p ON pp.symbol = p.symbol
               ORDER BY pp.score DESC
               LIMIT 5";
    $res = $conn->query($cr_sql);
    $top_cr = array();
    if ($res) { while ($row = $res->fetch_assoc()) $top_cr[] = $row; }
    $response['top_crypto'] = $top_cr;

    $response['generated_at'] = date('Y-m-d H:i:s');
    $response['disclaimer'] = 'For educational purposes only. Not financial advice.';

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action. Use: ticker_profile, portfolio_analytics, algorithm_report, risk_report, leaderboard, walk_forward, regime_analysis, top_picks';
}

echo json_encode($response);
$conn->close();
?>
