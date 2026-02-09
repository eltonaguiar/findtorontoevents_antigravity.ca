<?php
/**
 * Per-Stock Intelligence API — Deep Dive
 * Aggregates technicals, fundamentals, earnings, dividends, consensus, analyst recs.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   full            — Complete intelligence package for a ticker
 *   technicals      — Technical analysis with horizon filter
 *   yahoo_refresh   — Refresh Yahoo Finance data (analyst recs, fundamentals)
 *
 * Usage:
 *   GET .../stock_intel.php?action=full&ticker=AAPL
 *   GET .../stock_intel.php?action=technicals&ticker=AAPL&horizon=day_trade
 *   GET .../stock_intel.php?action=yahoo_refresh&ticker=AAPL
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'full';
$ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
$response = array('ok' => true, 'action' => $action, 'ticker' => $ticker);

if ($ticker === '') {
    $response['ok'] = false;
    $response['error'] = 'ticker parameter required';
    echo json_encode($response);
    $conn->close();
    exit;
}

$safe = $conn->real_escape_string($ticker);

// Cache dir
$cache_dir = dirname(__FILE__) . '/cache';
if (!is_dir($cache_dir)) @mkdir($cache_dir, 0755, true);

// ═══════════════════════════════════════════
// TECHNICALS — Compute TA indicators from daily_prices
// ═══════════════════════════════════════════
function _compute_technicals($conn, $ticker, $horizon) {
    $safe = $conn->real_escape_string($ticker);
    $res = $conn->query("SELECT trade_date, open_price, high_price, low_price, close_price, volume
                         FROM daily_prices WHERE ticker='$safe'
                         ORDER BY trade_date DESC LIMIT 252");
    $prices = array();
    if ($res) { while ($row = $res->fetch_assoc()) $prices[] = $row; }
    if (count($prices) < 15) return array('error' => 'Insufficient price data (' . count($prices) . ' days)');

    $prices = array_reverse($prices);
    $n = count($prices);
    $closes = array();
    $highs = array();
    $lows = array();
    $volumes = array();
    foreach ($prices as $p) {
        $closes[] = (float)$p['close_price'];
        $highs[] = (float)$p['high_price'];
        $lows[] = (float)$p['low_price'];
        $volumes[] = (int)$p['volume'];
    }

    $current = $closes[$n - 1];
    $ta = array('current_price' => $current, 'data_points' => $n);

    // ── SMA ──
    $sma_20 = ($n >= 20) ? array_sum(array_slice($closes, -20)) / 20 : 0;
    $sma_50 = ($n >= 50) ? array_sum(array_slice($closes, -50)) / 50 : 0;
    $sma_200 = ($n >= 200) ? array_sum(array_slice($closes, -200)) / 200 : 0;
    $ta['sma_20'] = round($sma_20, 4);
    $ta['sma_50'] = round($sma_50, 4);
    $ta['sma_200'] = round($sma_200, 4);
    $ta['golden_cross'] = ($sma_50 > 0 && $sma_200 > 0 && $sma_50 > $sma_200);
    $ta['death_cross'] = ($sma_50 > 0 && $sma_200 > 0 && $sma_50 < $sma_200);
    $ta['price_above_sma20'] = ($current > $sma_20);
    $ta['price_above_sma50'] = ($current > $sma_50);
    $ta['price_above_sma200'] = ($current > $sma_200);

    // ── RSI (14-period) ──
    $rsi = 50;
    if ($n >= 15) {
        $gains = 0; $loss = 0;
        for ($i = $n - 14; $i < $n; $i++) {
            $ch = $closes[$i] - $closes[$i - 1];
            if ($ch > 0) $gains += $ch; else $loss += abs($ch);
        }
        $avg_gain = $gains / 14;
        $avg_loss = $loss / 14;
        $rsi = ($avg_loss > 0) ? round(100 - (100 / (1 + $avg_gain / $avg_loss)), 2) : 100;
    }
    $ta['rsi_14'] = $rsi;
    $ta['rsi_signal'] = ($rsi > 70) ? 'overbought' : (($rsi < 30) ? 'oversold' : 'neutral');

    // ── MACD (12, 26, 9) ──
    $ema_12 = _ema(array_slice($closes, -30), 12);
    $ema_26 = _ema(array_slice($closes, -40), 26);
    $macd_line = round($ema_12 - $ema_26, 4);
    $ta['macd_line'] = $macd_line;
    $ta['macd_signal'] = ($macd_line > 0) ? 'bullish' : 'bearish';

    // ── Bollinger Bands (20, 2) ──
    if ($n >= 20) {
        $bb_slice = array_slice($closes, -20);
        $bb_mean = array_sum($bb_slice) / 20;
        $bb_var = 0;
        foreach ($bb_slice as $v) $bb_var += ($v - $bb_mean) * ($v - $bb_mean);
        $bb_std = sqrt($bb_var / 20);
        $ta['bb_upper'] = round($bb_mean + 2 * $bb_std, 4);
        $ta['bb_lower'] = round($bb_mean - 2 * $bb_std, 4);
        $ta['bb_middle'] = round($bb_mean, 4);
        $ta['bb_pct_b'] = ($bb_std > 0) ? round(($current - $ta['bb_lower']) / (4 * $bb_std), 4) : 0.5;
        $ta['bb_signal'] = ($current > $ta['bb_upper']) ? 'overbought' : (($current < $ta['bb_lower']) ? 'oversold' : 'neutral');
    }

    // ── ATR (14-period) ──
    $atr = 0;
    if ($n >= 15) {
        $trs = array();
        for ($i = $n - 14; $i < $n; $i++) {
            $tr = max($highs[$i] - $lows[$i], abs($highs[$i] - $closes[$i - 1]), abs($lows[$i] - $closes[$i - 1]));
            $trs[] = $tr;
        }
        $atr = round(array_sum($trs) / count($trs), 4);
    }
    $ta['atr_14'] = $atr;
    $ta['atr_pct'] = ($current > 0) ? round($atr / $current * 100, 2) : 0;

    // ── Volume analysis ──
    if ($n >= 20) {
        $vol_20 = array_sum(array_slice($volumes, -20)) / 20;
        $vol_latest = $volumes[$n - 1];
        $ta['volume_latest'] = $vol_latest;
        $ta['volume_20d_avg'] = round($vol_20, 0);
        $ta['volume_ratio'] = ($vol_20 > 0) ? round($vol_latest / $vol_20, 2) : 0;
        $ta['volume_surge'] = ($ta['volume_ratio'] > 1.5);
    }

    // ── Stochastic RSI ──
    if ($n >= 14) {
        $rsi_vals = array();
        for ($k = $n - 14; $k < $n; $k++) {
            $g = 0; $l = 0;
            $start = max(0, $k - 13);
            for ($j = $start + 1; $j <= $k; $j++) {
                $ch = $closes[$j] - $closes[$j - 1];
                if ($ch > 0) $g += $ch; else $l += abs($ch);
            }
            $ag = $g / 14; $al = $l / 14;
            $rsi_vals[] = ($al > 0) ? 100 - (100 / (1 + $ag / $al)) : 100;
        }
        $rsi_max = max($rsi_vals);
        $rsi_min = min($rsi_vals);
        $ta['stoch_rsi'] = ($rsi_max != $rsi_min) ? round(($rsi - $rsi_min) / ($rsi_max - $rsi_min) * 100, 2) : 50;
    }

    // ── 52-Week High/Low ──
    $h52 = max($highs);
    $l52 = min(array_filter($lows, create_function('$v', 'return $v > 0;')));
    $ta['high_52w'] = round($h52, 4);
    $ta['low_52w'] = round($l52, 4);
    $ta['pct_from_52w_high'] = ($h52 > 0) ? round(($current - $h52) / $h52 * 100, 2) : 0;
    $ta['pct_from_52w_low'] = ($l52 > 0) ? round(($current - $l52) / $l52 * 100, 2) : 0;

    // ── Support/Resistance (pivot points) ──
    $last_h = $highs[$n - 1];
    $last_l = $lows[$n - 1];
    $pivot = ($last_h + $last_l + $current) / 3;
    $ta['pivot'] = round($pivot, 4);
    $ta['support_1'] = round(2 * $pivot - $last_h, 4);
    $ta['resistance_1'] = round(2 * $pivot - $last_l, 4);
    $ta['support_2'] = round($pivot - ($last_h - $last_l), 4);
    $ta['resistance_2'] = round($pivot + ($last_h - $last_l), 4);

    // ── Composite verdict ──
    $bull = 0; $bear = 0; $total_signals = 0;
    if ($rsi < 30) $bull++; elseif ($rsi > 70) $bear++; $total_signals++;
    if ($current > $sma_20) $bull++; else $bear++; $total_signals++;
    if ($current > $sma_50) $bull++; else $bear++; $total_signals++;
    if ($sma_50 > 0 && $sma_200 > 0) { if ($sma_50 > $sma_200) $bull++; else $bear++; $total_signals++; }
    if ($macd_line > 0) $bull++; else $bear++; $total_signals++;
    if (isset($ta['bb_pct_b'])) { if ($ta['bb_pct_b'] < 0.2) $bull++; elseif ($ta['bb_pct_b'] > 0.8) $bear++; $total_signals++; }
    if (isset($ta['volume_surge']) && $ta['volume_surge'] && $closes[$n - 1] > $closes[$n - 2]) $bull++;
    if (isset($ta['stoch_rsi']) && $ta['stoch_rsi'] < 20) $bull++; elseif (isset($ta['stoch_rsi']) && $ta['stoch_rsi'] > 80) $bear++;

    $ta['bull_signals'] = $bull;
    $ta['bear_signals'] = $bear;
    $ta['total_signals'] = max($total_signals, 1);
    $ta['bull_pct'] = round($bull / max($total_signals, 1) * 100, 1);
    $ta['verdict'] = ($bull > $bear + 1) ? 'BULLISH' : (($bear > $bull + 1) ? 'BEARISH' : 'NEUTRAL');

    // ── Horizon-specific filtering ──
    $horizon_indicators = array();
    if ($horizon === 'day_trade') {
        $horizon_indicators = array('rsi_14', 'rsi_signal', 'stoch_rsi', 'macd_line', 'macd_signal',
            'volume_ratio', 'volume_surge', 'atr_14', 'atr_pct', 'current_price');
    } elseif ($horizon === 'swing') {
        $horizon_indicators = array('rsi_14', 'macd_line', 'macd_signal', 'bb_upper', 'bb_lower', 'bb_pct_b', 'bb_signal',
            'sma_20', 'sma_50', 'price_above_sma20', 'price_above_sma50', 'volume_ratio',
            'support_1', 'resistance_1', 'pivot', 'current_price');
    } elseif ($horizon === 'long_term') {
        $horizon_indicators = array('sma_50', 'sma_200', 'golden_cross', 'death_cross',
            'price_above_sma200', 'high_52w', 'low_52w', 'pct_from_52w_high', 'pct_from_52w_low',
            'current_price');
    }

    if (!empty($horizon_indicators)) {
        $ta['horizon'] = $horizon;
        $ta['horizon_indicators'] = array();
        foreach ($horizon_indicators as $key) {
            if (isset($ta[$key])) $ta['horizon_indicators'][$key] = $ta[$key];
        }
    }

    return $ta;
}

function _ema($data, $period) {
    if (count($data) < $period) return 0;
    $k = 2.0 / ($period + 1);
    $ema = $data[0];
    for ($i = 1; $i < count($data); $i++) {
        $ema = $data[$i] * $k + $ema * (1 - $k);
    }
    return $ema;
}

// ═══════════════════════════════════════════
// FULL — Complete intelligence package
// ═══════════════════════════════════════════
if ($action === 'full') {
    // Check cache (6 hours)
    $cache_file = $cache_dir . '/intel_' . md5($ticker) . '.json';
    if (file_exists($cache_file) && (time() - filemtime($cache_file)) < 21600) {
        $cached = @file_get_contents($cache_file);
        if ($cached !== false) {
            $d = json_decode($cached, true);
            if ($d) { $d['from_cache'] = true; echo json_encode($d); $conn->close(); exit; }
        }
    }

    // Company info
    $company_name = '';
    $sr = $conn->query("SELECT * FROM stocks WHERE ticker='$safe'");
    $stock_info = ($sr && $sr->num_rows > 0) ? $sr->fetch_assoc() : array('ticker' => $ticker);
    if (isset($stock_info['company_name'])) $company_name = $stock_info['company_name'];
    if ($company_name === '') {
        $sr2 = $conn->query("SELECT company_name FROM miracle_picks3 WHERE ticker='$safe' AND company_name != '' LIMIT 1");
        if ($sr2 && $sr2->num_rows > 0) { $r = $sr2->fetch_assoc(); $company_name = $r['company_name']; }
    }
    $response['company_name'] = $company_name;
    $response['stock_info'] = $stock_info;

    // Technicals (all horizons)
    $response['technicals'] = _compute_technicals($conn, $ticker, 'all');

    // Fundamentals
    $fr = $conn->query("SELECT * FROM stock_fundamentals WHERE ticker='$safe' LIMIT 1");
    $response['fundamentals'] = ($fr && $fr->num_rows > 0) ? $fr->fetch_assoc() : null;

    // Earnings
    $earnings = array();
    $er = $conn->query("SELECT * FROM stock_earnings WHERE ticker='$safe' ORDER BY earnings_date DESC LIMIT 8");
    if ($er) { while ($row = $er->fetch_assoc()) $earnings[] = $row; }
    $response['earnings'] = $earnings;

    // Dividends
    $dividends = array();
    $dr = $conn->query("SELECT * FROM stock_dividends WHERE ticker='$safe' ORDER BY ex_date DESC LIMIT 12");
    if ($dr) { while ($row = $dr->fetch_assoc()) $dividends[] = $row; }
    $response['dividends'] = $dividends;

    // Analyst recs
    $recs = array();
    $ar = $conn->query("SELECT * FROM stock_analyst_recs WHERE ticker='$safe' ORDER BY period ASC");
    if ($ar) { while ($row = $ar->fetch_assoc()) $recs[] = $row; }
    $response['analyst_recs'] = $recs;

    // Consensus history
    $consensus = array();
    $cr = $conn->query("SELECT * FROM consensus_history WHERE ticker='$safe' ORDER BY consensus_date DESC LIMIT 30");
    if ($cr) { while ($row = $cr->fetch_assoc()) $consensus[] = $row; }
    $response['consensus_history'] = $consensus;

    // Picks from all tables
    $all_picks = array();
    $r1 = $conn->query("SELECT ticker, algorithm_name, pick_date, entry_price, score, rating, 'stock_picks' AS source FROM stock_picks WHERE ticker='$safe' ORDER BY pick_date DESC LIMIT 20");
    if ($r1) { while ($row = $r1->fetch_assoc()) $all_picks[] = $row; }
    $r2 = $conn->query("SELECT ticker, strategy_name AS algorithm_name, scan_date AS pick_date, entry_price, score, confidence AS rating, 'miracle_picks2' AS source FROM miracle_picks2 WHERE ticker='$safe' ORDER BY scan_date DESC LIMIT 20");
    if ($r2) { while ($row = $r2->fetch_assoc()) $all_picks[] = $row; }
    $r3 = $conn->query("SELECT ticker, strategy_name AS algorithm_name, scan_date AS pick_date, entry_price, score, confidence AS rating, 'miracle_picks3' AS source FROM miracle_picks3 WHERE ticker='$safe' ORDER BY scan_date DESC LIMIT 20");
    if ($r3) { while ($row = $r3->fetch_assoc()) $all_picks[] = $row; }
    $response['all_picks'] = $all_picks;

    // Price sparkline (last 90 days)
    $sparkline = array();
    $sp = $conn->query("SELECT trade_date, close_price FROM daily_prices WHERE ticker='$safe' ORDER BY trade_date DESC LIMIT 90");
    if ($sp) { while ($row = $sp->fetch_assoc()) $sparkline[] = $row; }
    $response['sparkline'] = array_reverse($sparkline);

    $response['generated_at'] = date('Y-m-d H:i:s');
    $response['disclaimer'] = 'For educational and research purposes only. Not financial advice.';

    // Cache result
    @file_put_contents($cache_file, json_encode($response));
    echo json_encode($response);

// ═══════════════════════════════════════════
// TECHNICALS — Horizon-specific TA
// ═══════════════════════════════════════════
} elseif ($action === 'technicals') {
    $horizon = isset($_GET['horizon']) ? trim($_GET['horizon']) : 'all';
    $ta = _compute_technicals($conn, $ticker, $horizon);
    $response['technicals'] = $ta;
    $response['generated_at'] = date('Y-m-d H:i:s');
    echo json_encode($response);

// ═══════════════════════════════════════════
// YAHOO REFRESH — Refresh analyst recs from Yahoo Finance
// ═══════════════════════════════════════════
} elseif ($action === 'yahoo_refresh') {
    // Reuse crumb auth pattern from fetch_dividends_earnings.php
    $cookie = '';
    $crumb = '';

    // Step 1: Get cookie
    $ctx1 = stream_context_create(array('http' => array(
        'method' => 'GET',
        'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n",
        'timeout' => 10, 'ignore_errors' => true
    )));
    @file_get_contents('https://fc.yahoo.com', false, $ctx1);
    if (isset($http_response_header)) {
        foreach ($http_response_header as $hdr) {
            if (stripos($hdr, 'Set-Cookie:') === 0) {
                $parts = explode(';', substr($hdr, 12));
                if ($cookie !== '') $cookie .= '; ';
                $cookie .= trim($parts[0]);
            }
        }
    }

    // Step 2: Get crumb
    if ($cookie !== '') {
        $ctx2 = stream_context_create(array('http' => array(
            'method' => 'GET',
            'header' => "User-Agent: Mozilla/5.0\r\nCookie: " . $cookie . "\r\n",
            'timeout' => 10, 'ignore_errors' => true
        )));
        $c = @file_get_contents('https://query2.finance.yahoo.com/v1/test/getcrumb', false, $ctx2);
        if ($c !== false && strlen($c) < 50 && strpos($c, '<') === false) $crumb = trim($c);
    }

    if ($crumb === '') {
        $response['ok'] = false;
        $response['error'] = 'Failed to get Yahoo Finance authentication';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    // Step 3: Fetch quoteSummary with recommendationTrend
    $modules = 'recommendationTrend,upgradeDowngradeHistory,earningsTrend,financialData,defaultKeyStatistics';
    $url = 'https://query2.finance.yahoo.com/v10/finance/quoteSummary/' . urlencode($ticker)
         . '?modules=' . $modules . '&crumb=' . urlencode($crumb);
    $ctx3 = stream_context_create(array('http' => array(
        'method' => 'GET',
        'header' => "User-Agent: Mozilla/5.0\r\nCookie: " . $cookie . "\r\n",
        'timeout' => 15, 'ignore_errors' => true
    )));
    $raw = @file_get_contents($url, false, $ctx3);
    if ($raw === false) {
        $response['ok'] = false;
        $response['error'] = 'Failed to fetch Yahoo Finance data';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $data = json_decode($raw, true);
    $result_obj = null;
    if (isset($data['quoteSummary']['result'][0])) {
        $result_obj = $data['quoteSummary']['result'][0];
    }

    if (!$result_obj) {
        $response['ok'] = false;
        $response['error'] = 'No Yahoo Finance data for ' . $ticker;
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $now = date('Y-m-d H:i:s');
    $stored_recs = 0;

    // Store analyst recommendation trends
    if (isset($result_obj['recommendationTrend']['trend'])) {
        $trends = $result_obj['recommendationTrend']['trend'];
        // Clear old data
        $conn->query("DELETE FROM stock_analyst_recs WHERE ticker='$safe'");
        foreach ($trends as $t) {
            $period = isset($t['period']) ? $conn->real_escape_string($t['period']) : '0m';
            $sb = isset($t['strongBuy']) ? (int)$t['strongBuy'] : 0;
            $b = isset($t['buy']) ? (int)$t['buy'] : 0;
            $h = isset($t['hold']) ? (int)$t['hold'] : 0;
            $s = isset($t['sell']) ? (int)$t['sell'] : 0;
            $ss = isset($t['strongSell']) ? (int)$t['strongSell'] : 0;
            $conn->query("INSERT INTO stock_analyst_recs (ticker, period, strong_buy, buy, hold_count, sell, strong_sell, updated_at)
                          VALUES ('$safe', '$period', $sb, $b, $h, $s, $ss, '$now')");
            $stored_recs++;
        }
    }

    $response['stored_recs'] = $stored_recs;
    $response['modules_fetched'] = array_keys($result_obj);
    $response['generated_at'] = $now;
    echo json_encode($response);

} else {
    $response['ok'] = false;
    $response['error'] = 'Unknown action. Use: full, technicals, yahoo_refresh';
    echo json_encode($response);
}

$conn->close();
?>
