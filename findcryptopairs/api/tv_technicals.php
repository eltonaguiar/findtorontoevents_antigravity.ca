<?php
/**
 * TV Technicals Engine — TradingView-Style Technical Ratings + Short-Term Pattern Detection
 *
 * Calculates 11 oscillators + 15 moving averages per pair (matching TradingView's methodology),
 * then detects high-probability short-term confluence patterns for quick buy/sell signals.
 *
 * Actions: scan, signals, monitor, patterns
 * PHP 5.2 compatible
 */
error_reporting(0);
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) { echo json_encode(array('ok' => false, 'error' => 'DB error')); exit; }
$conn->set_charset('utf8');

// Ensure tables
$conn->query("CREATE TABLE IF NOT EXISTS tv_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(30),
    direction VARCHAR(10),
    pattern_name VARCHAR(100),
    pattern_detail TEXT,
    entry_price DECIMAL(20,10),
    tp_price DECIMAL(20,10),
    sl_price DECIMAL(20,10),
    confidence DECIMAL(5,2),
    osc_rating VARCHAR(20),
    ma_rating VARCHAR(20),
    summary_rating VARCHAR(20),
    osc_score DECIMAL(5,2),
    ma_score DECIMAL(5,2),
    summary_score DECIMAL(5,2),
    indicators_json TEXT,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    current_price DECIMAL(20,10),
    pnl_pct DECIMAL(8,4),
    exit_reason VARCHAR(30),
    created_at DATETIME,
    resolved_at DATETIME,
    INDEX(pair), INDEX(status), INDEX(created_at)
) ENGINE=InnoDB");

$action = isset($_GET['action']) ? $_GET['action'] : 'scan';
switch ($action) {
    case 'scan':     action_scan($conn); break;
    case 'signals':  action_signals($conn); break;
    case 'monitor':  action_monitor($conn); break;
    case 'ratings':  action_ratings($conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}
$conn->close();

// ═══════════════════════════════════════════════════════════════
//  PAIRS
// ═══════════════════════════════════════════════════════════════
function get_pairs() {
    return array(
        // Majors
        'XXBTZUSD','XETHZUSD','SOLUSD','XXRPZUSD','ADAUSD','AVAXUSD',
        'DOTUSD','LINKUSD','NEARUSD','SUIUSD','INJUSD',
        'LTCUSD','XDGUSD','XXLMZUSD','ATOMUSD',
        // Meme coins (previously missing — caused blind spot on 10%+ movers)
        'PEPEUSD','BONKUSD','FLOKIUSD','WIFUSD','SHIBUSD','TRUMPUSD',
        'PENGUUSD','FARTCOINUSD','VIRTUALUSD','SPXUSD','TURBOUSD',
        // DeFi / Mid-caps
        'AAVEUSD','COMPUSD','CRVUSD','DYDXUSD','OPUSD','FETUSD',
        'APTUSD','BCHUSD','XZECZUSD','XXMRZUSD'
    );
}

// ═══════════════════════════════════════════════════════════════
//  SCAN — Calculate all TradingView-style technicals + detect patterns
// ═══════════════════════════════════════════════════════════════
function action_scan($conn) {
    $start = microtime(true);
    $pairs = get_pairs();
    // Fetch 4H candles (short-term focus)
    $all_ohlcv = fetch_ohlcv_batch($pairs, 240);
    $now = date('Y-m-d H:i:s');
    $signals = array();
    $ratings = array();

    foreach ($pairs as $pair) {
        if (!isset($all_ohlcv[$pair]) || count($all_ohlcv[$pair]) < 60) continue;
        $candles = $all_ohlcv[$pair];
        $ind = compute_all_indicators($candles);
        if (!$ind) continue;

        // Calculate TradingView-style ratings
        $osc = rate_oscillators($ind);
        $ma = rate_moving_averages($ind);
        $summary = rate_summary($osc, $ma);

        $ratings[$pair] = array(
            'pair' => $pair,
            'price' => $ind['close_last'],
            'osc_rating' => $osc['rating'],
            'osc_score' => $osc['score'],
            'osc_buy' => $osc['buy'],
            'osc_sell' => $osc['sell'],
            'osc_neutral' => $osc['neutral'],
            'ma_rating' => $ma['rating'],
            'ma_score' => $ma['score'],
            'ma_buy' => $ma['buy'],
            'ma_sell' => $ma['sell'],
            'ma_neutral' => $ma['neutral'],
            'summary_rating' => $summary['rating'],
            'summary_score' => $summary['score'],
            'indicators' => $ind['snapshot']
        );

        // Detect short-term patterns
        $patterns = detect_patterns($ind, $pair);
        foreach ($patterns as $pat) {
            $entry = $ind['close_last'];
            $atr = $ind['atr_last'];
            if ($pat['dir'] === 'LONG') {
                $tp = $entry + ($atr * $pat['tp_mult']);
                $sl = $entry - ($atr * $pat['sl_mult']);
            } else {
                $tp = $entry - ($atr * $pat['tp_mult']);
                $sl = $entry + ($atr * $pat['sl_mult']);
            }
            // Check if similar signal exists (same pair+pattern within 8h)
            $check = $conn->query(sprintf(
                "SELECT id FROM tv_signals WHERE pair='%s' AND pattern_name='%s' AND status='ACTIVE' AND created_at > DATE_SUB(NOW(), INTERVAL 8 HOUR)",
                $conn->real_escape_string($pair), $conn->real_escape_string($pat['name'])
            ));
            if ($check && $check->num_rows > 0) continue;

            $conn->query(sprintf(
                "INSERT INTO tv_signals (pair,direction,pattern_name,pattern_detail,entry_price,tp_price,sl_price,confidence,osc_rating,ma_rating,summary_rating,osc_score,ma_score,summary_score,indicators_json,status,created_at) VALUES('%s','%s','%s','%s','%.10f','%.10f','%.10f','%.2f','%s','%s','%s','%.2f','%.2f','%.2f','%s','ACTIVE','%s')",
                $conn->real_escape_string($pair),
                $conn->real_escape_string($pat['dir']),
                $conn->real_escape_string($pat['name']),
                $conn->real_escape_string($pat['detail']),
                $entry, $tp, $sl,
                $pat['confidence'],
                $conn->real_escape_string($osc['rating']),
                $conn->real_escape_string($ma['rating']),
                $conn->real_escape_string($summary['rating']),
                $osc['score'], $ma['score'], $summary['score'],
                $conn->real_escape_string(json_encode($ind['snapshot'])),
                $now
            ));
            $signals[] = array(
                'pair' => $pair, 'direction' => $pat['dir'], 'pattern' => $pat['name'],
                'detail' => $pat['detail'], 'confidence' => $pat['confidence'],
                'entry' => $entry, 'tp' => $tp, 'sl' => $sl,
                'osc' => $osc['rating'], 'ma' => $ma['rating'], 'summary' => $summary['rating']
            );
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array('ok' => true, 'signals' => $signals, 'ratings' => $ratings,
        'pairs_scanned' => count($ratings), 'new_signals' => count($signals), 'elapsed_ms' => $elapsed));
}

// ═══════════════════════════════════════════════════════════════
//  RATINGS — Just return current technical ratings (no DB write)
// ═══════════════════════════════════════════════════════════════
function action_ratings($conn) {
    $start = microtime(true);
    $pairs = get_pairs();
    $all_ohlcv = fetch_ohlcv_batch($pairs, 240);
    $ratings = array();

    foreach ($pairs as $pair) {
        if (!isset($all_ohlcv[$pair]) || count($all_ohlcv[$pair]) < 60) continue;
        $ind = compute_all_indicators($all_ohlcv[$pair]);
        if (!$ind) continue;
        $osc = rate_oscillators($ind);
        $ma = rate_moving_averages($ind);
        $summary = rate_summary($osc, $ma);
        $ratings[$pair] = array(
            'pair' => $pair, 'price' => $ind['close_last'],
            'osc' => $osc, 'ma' => $ma, 'summary' => $summary,
            'indicators' => $ind['snapshot']
        );
    }
    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array('ok' => true, 'ratings' => $ratings, 'elapsed_ms' => $elapsed));
}

// ═══════════════════════════════════════════════════════════════
//  SIGNALS — Return active + history
// ═══════════════════════════════════════════════════════════════
function action_signals($conn) {
    $active = array(); $history = array();
    $res = $conn->query("SELECT * FROM tv_signals WHERE status='ACTIVE' ORDER BY confidence DESC");
    if ($res) { while ($r = $res->fetch_assoc()) { $active[] = $r; } }
    $res2 = $conn->query("SELECT * FROM tv_signals WHERE status='RESOLVED' ORDER BY resolved_at DESC LIMIT 50");
    if ($res2) { while ($r = $res2->fetch_assoc()) { $history[] = $r; } }
    $wins = 0; $losses = 0; $pnl = 0;
    foreach ($history as $h) { $p = floatval($h['pnl_pct']); $pnl += $p; if ($p > 0) $wins++; else $losses++; }
    $wr = ($wins + $losses > 0) ? round($wins / ($wins + $losses) * 100, 1) : 0;
    // Live stats from active
    $live_pnl = 0; $live_green = 0; $live_red = 0;
    foreach ($active as $a) {
        $lp = floatval(isset($a['pnl_pct']) ? $a['pnl_pct'] : 0);
        $live_pnl += $lp;
        if ($lp > 0) $live_green++;
        elseif ($lp < 0) $live_red++;
    }
    echo json_encode(array('ok' => true, 'active' => $active, 'history' => $history,
        'stats' => array('win_rate' => $wr, 'total_pnl' => round($pnl, 2), 'wins' => $wins, 'losses' => $losses,
            'live_pnl' => round($live_pnl, 2), 'live_green' => $live_green, 'live_red' => $live_red,
            'active_count' => count($active))));
}

// ═══════════════════════════════════════════════════════════════
//  MONITOR — Check TP/SL/expiry on active signals
// ═══════════════════════════════════════════════════════════════
function action_monitor($conn) {
    $res = $conn->query("SELECT * FROM tv_signals WHERE status='ACTIVE'");
    if (!$res || $res->num_rows == 0) { echo json_encode(array('ok' => true, 'checked' => 0, 'resolved' => 0)); return; }
    $sigs = array(); $pairs_map = array();
    while ($r = $res->fetch_assoc()) { $sigs[] = $r; $pairs_map[$r['pair']] = true; }
    $tickers = fetch_tickers(array_keys($pairs_map));
    $now = date('Y-m-d H:i:s'); $resolved = 0;
    foreach ($sigs as $sig) {
        $cur = isset($tickers[$sig['pair']]) ? $tickers[$sig['pair']] : 0;
        if ($cur <= 0) continue;
        $entry = floatval($sig['entry_price']);
        $dir = $sig['direction'];
        $pnl = ($entry > 0) ? (($dir === 'LONG') ? ($cur - $entry) / $entry * 100 : ($entry - $cur) / $entry * 100) : 0;
        $done = false; $reason = '';
        if ($dir === 'LONG') {
            if ($cur >= floatval($sig['tp_price'])) { $done = true; $reason = 'TP_HIT'; }
            elseif ($cur <= floatval($sig['sl_price'])) { $done = true; $reason = 'SL_HIT'; }
        } else {
            if ($cur <= floatval($sig['tp_price'])) { $done = true; $reason = 'TP_HIT'; }
            elseif ($cur >= floatval($sig['sl_price'])) { $done = true; $reason = 'SL_HIT'; }
        }
        $hours = (time() - strtotime($sig['created_at'])) / 3600;
        if (!$done && $hours >= 48) { $done = true; $reason = 'EXPIRED_48H'; }
        if ($done) {
            $conn->query(sprintf("UPDATE tv_signals SET status='RESOLVED',current_price='%.10f',pnl_pct='%.4f',exit_reason='%s',resolved_at='%s' WHERE id=%d",
                $cur, $pnl, $conn->real_escape_string($reason), $now, intval($sig['id'])));
            $resolved++;
        } else {
            $conn->query(sprintf("UPDATE tv_signals SET current_price='%.10f',pnl_pct='%.4f' WHERE id=%d", $cur, $pnl, intval($sig['id'])));
        }
    }
    echo json_encode(array('ok' => true, 'checked' => count($sigs), 'resolved' => $resolved));
}

// ═══════════════════════════════════════════════════════════════
//  INDICATOR CALCULATIONS (TradingView-matching)
// ═══════════════════════════════════════════════════════════════
function compute_all_indicators($candles) {
    $o = array(); $h = array(); $l = array(); $c = array(); $v = array();
    foreach ($candles as $cd) {
        $o[] = floatval($cd[1]); $h[] = floatval($cd[2]);
        $l[] = floatval($cd[3]); $c[] = floatval($cd[4]); $v[] = floatval($cd[6]);
    }
    $n = count($c);
    if ($n < 60) return null;

    // Core indicators
    $rsi14 = calc_rsi($c, 14);
    $rsi7 = calc_rsi($c, 7);
    $stoch = calc_stoch($h, $l, $c, 14, 3);
    $cci20 = calc_cci($h, $l, $c, 20);
    $adx = calc_adx($h, $l, $c, 14);
    $ao = calc_ao($h, $l);
    $mom10 = calc_momentum($c, 10);
    $macd = calc_macd($c);
    $stoch_rsi = calc_stoch_rsi($c, 14, 3, 3);
    $wr14 = calc_williams_r($h, $l, $c, 14);
    $bbp = calc_bull_bear_power($h, $l, $c, 13);
    $uo = calc_ultimate_osc($h, $l, $c, 7, 14, 28);

    // Moving averages
    $ema10 = calc_ema($c, 10); $sma10 = calc_sma($c, 10);
    $ema20 = calc_ema($c, 20); $sma20 = calc_sma($c, 20);
    $ema30 = calc_ema($c, 30); $sma30 = calc_sma($c, 30);
    $ema50 = calc_ema($c, 50); $sma50 = calc_sma($c, 50);
    $ema100 = calc_ema($c, 100); $sma100 = calc_sma($c, 100);
    $ema200 = calc_ema($c, 200); $sma200 = calc_sma($c, 200);
    $hma9 = calc_hma($c, 9);
    $vwma20 = calc_vwma($c, $v, 20);

    // Extras
    $atr14 = calc_atr($h, $l, $c, 14);
    $bb = calc_bb($c, 20, 2.0);
    $obv = calc_obv($c, $v);

    $last = $n - 1;
    $prev = $n - 2;

    return array(
        'close' => $c, 'high' => $h, 'low' => $l, 'open' => $o, 'volume' => $v,
        'close_last' => $c[$last], 'atr_last' => $atr14[$last],
        'rsi14' => $rsi14, 'rsi14_last' => $rsi14[$last], 'rsi14_prev' => $rsi14[$prev],
        'rsi7_last' => $rsi7[$last],
        'stoch_k' => $stoch['k'], 'stoch_d' => $stoch['d'],
        'stoch_k_last' => $stoch['k'][$last], 'stoch_d_last' => $stoch['d'][$last],
        'stoch_k_prev' => $stoch['k'][$prev], 'stoch_d_prev' => $stoch['d'][$prev],
        'cci20_last' => $cci20[$last],
        'adx_last' => $adx['adx'][$last], 'pdi_last' => $adx['pdi'][$last], 'mdi_last' => $adx['mdi'][$last],
        'ao_last' => $ao[$last], 'ao_prev' => $ao[$prev],
        'mom10_last' => $mom10[$last],
        'macd_line' => $macd['l'][$last], 'macd_signal' => $macd['s'][$last], 'macd_hist' => $macd['h'][$last],
        'macd_hist_prev' => $macd['h'][$prev],
        'stoch_rsi_k' => $stoch_rsi['k'][$last], 'stoch_rsi_d' => $stoch_rsi['d'][$last],
        'wr14_last' => $wr14[$last],
        'bbp_last' => $bbp[$last],
        'uo_last' => $uo[$last],
        'ema10' => $ema10[$last], 'sma10' => $sma10[$last],
        'ema20' => $ema20[$last], 'sma20' => $sma20[$last],
        'ema30' => $ema30[$last], 'sma30' => $sma30[$last],
        'ema50' => $ema50[$last], 'sma50' => $sma50[$last],
        'ema100' => $ema100[$last], 'sma100' => $sma100[$last],
        'ema200' => $ema200[$last], 'sma200' => $sma200[$last],
        'hma9' => $hma9[$last], 'hma9_prev' => $hma9[$prev],
        'vwma20' => $vwma20[$last],
        'atr14' => $atr14, 'bb_u' => $bb['u'][$last], 'bb_m' => $bb['m'][$last], 'bb_l' => $bb['l'][$last],
        'bb_width' => ($bb['m'][$last] > 0) ? ($bb['u'][$last] - $bb['l'][$last]) / $bb['m'][$last] * 100 : 0,
        'obv' => $obv,
        'snapshot' => array(
            'rsi14' => round($rsi14[$last], 2), 'stoch_k' => round($stoch['k'][$last], 2),
            'cci20' => round($cci20[$last], 2), 'adx' => round($adx['adx'][$last], 2),
            'ao' => round($ao[$last], 4), 'mom10' => round($mom10[$last], 4),
            'macd_hist' => round($macd['h'][$last], 6), 'stoch_rsi_k' => round($stoch_rsi['k'][$last], 2),
            'wr14' => round($wr14[$last], 2), 'bbp' => round($bbp[$last], 4), 'uo' => round($uo[$last], 2),
            'ema10' => round($ema10[$last], 4), 'sma10' => round($sma10[$last], 4),
            'ema20' => round($ema20[$last], 4), 'sma20' => round($sma20[$last], 4),
            'ema50' => round($ema50[$last], 4), 'sma50' => round($sma50[$last], 4),
            'ema200' => round($ema200[$last], 4), 'sma200' => round($sma200[$last], 4),
            'hma9' => round($hma9[$last], 4), 'vwma20' => round($vwma20[$last], 4),
            'atr' => round($atr14[$last], 6), 'bb_width' => round(($bb['u'][$last] - $bb['l'][$last]) / max(0.0001, $bb['m'][$last]) * 100, 2),
            'price' => round($c[$last], 6)
        )
    );
}

// ═══════════════════════════════════════════════════════════════
//  TRADINGVIEW-STYLE RATING SYSTEM
// ═══════════════════════════════════════════════════════════════
function rate_oscillators($ind) {
    $buy = 0; $sell = 0; $neutral = 0;

    // RSI(14): <30=buy, >70=sell, else neutral
    if ($ind['rsi14_last'] < 30) $buy++; elseif ($ind['rsi14_last'] > 70) $sell++; else $neutral++;
    // Stoch %K: <20=buy, >80=sell
    if ($ind['stoch_k_last'] < 20) $buy++; elseif ($ind['stoch_k_last'] > 80) $sell++; else $neutral++;
    // CCI: <-100=buy, >100=sell
    if ($ind['cci20_last'] < -100) $buy++; elseif ($ind['cci20_last'] > 100) $sell++; else $neutral++;
    // ADX: >20 trending, +DI > -DI = buy
    if ($ind['adx_last'] > 20) { if ($ind['pdi_last'] > $ind['mdi_last']) $buy++; else $sell++; } else $neutral++;
    // AO: >0 and increasing = buy
    if ($ind['ao_last'] > 0 && $ind['ao_last'] > $ind['ao_prev']) $buy++;
    elseif ($ind['ao_last'] < 0 && $ind['ao_last'] < $ind['ao_prev']) $sell++;
    else $neutral++;
    // Momentum: >0=buy
    if ($ind['mom10_last'] > 0) $buy++; elseif ($ind['mom10_last'] < 0) $sell++; else $neutral++;
    // MACD: histogram > 0 = buy
    if ($ind['macd_hist'] > 0) $buy++; elseif ($ind['macd_hist'] < 0) $sell++; else $neutral++;
    // Stoch RSI: <20=buy, >80=sell
    if ($ind['stoch_rsi_k'] < 20) $buy++; elseif ($ind['stoch_rsi_k'] > 80) $sell++; else $neutral++;
    // Williams %R: <-80=buy, >-20=sell
    if ($ind['wr14_last'] < -80) $buy++; elseif ($ind['wr14_last'] > -20) $sell++; else $neutral++;
    // Bull Bear Power: >0=buy
    if ($ind['bbp_last'] > 0) $buy++; elseif ($ind['bbp_last'] < 0) $sell++; else $neutral++;
    // Ultimate Osc: <30=buy, >70=sell
    if ($ind['uo_last'] < 30) $buy++; elseif ($ind['uo_last'] > 70) $sell++; else $neutral++;

    $total = $buy + $sell + $neutral;
    $score = ($total > 0) ? round(($buy - $sell) / $total * 100, 2) : 0;
    $rating = 'NEUTRAL';
    if ($score >= 50) $rating = 'STRONG_BUY';
    elseif ($score >= 15) $rating = 'BUY';
    elseif ($score <= -50) $rating = 'STRONG_SELL';
    elseif ($score <= -15) $rating = 'SELL';

    return array('rating' => $rating, 'score' => $score, 'buy' => $buy, 'sell' => $sell, 'neutral' => $neutral);
}

function rate_moving_averages($ind) {
    $buy = 0; $sell = 0; $neutral = 0;
    $price = $ind['close_last'];
    // Each MA: price above = buy, below = sell
    $mas = array('ema10','sma10','ema20','sma20','ema30','sma30','ema50','sma50','ema100','sma100','ema200','sma200','hma9','vwma20');
    foreach ($mas as $k) {
        $mv = $ind[$k];
        if ($price > $mv * 1.001) $buy++;
        elseif ($price < $mv * 0.999) $sell++;
        else $neutral++;
    }
    $total = $buy + $sell + $neutral;
    $score = ($total > 0) ? round(($buy - $sell) / $total * 100, 2) : 0;
    $rating = 'NEUTRAL';
    if ($score >= 50) $rating = 'STRONG_BUY';
    elseif ($score >= 15) $rating = 'BUY';
    elseif ($score <= -50) $rating = 'STRONG_SELL';
    elseif ($score <= -15) $rating = 'SELL';

    return array('rating' => $rating, 'score' => $score, 'buy' => $buy, 'sell' => $sell, 'neutral' => $neutral);
}

function rate_summary($osc, $ma) {
    $total_buy = $osc['buy'] + $ma['buy'];
    $total_sell = $osc['sell'] + $ma['sell'];
    $total_neutral = $osc['neutral'] + $ma['neutral'];
    $total = $total_buy + $total_sell + $total_neutral;
    $score = ($total > 0) ? round(($total_buy - $total_sell) / $total * 100, 2) : 0;
    $rating = 'NEUTRAL';
    if ($score >= 50) $rating = 'STRONG_BUY';
    elseif ($score >= 15) $rating = 'BUY';
    elseif ($score <= -50) $rating = 'STRONG_SELL';
    elseif ($score <= -15) $rating = 'SELL';

    return array('rating' => $rating, 'score' => $score, 'buy' => $total_buy, 'sell' => $total_sell, 'neutral' => $total_neutral);
}

// ═══════════════════════════════════════════════════════════════
//  SHORT-TERM PATTERN DETECTION (The Strategy)
// ═══════════════════════════════════════════════════════════════
function detect_patterns($ind, $pair) {
    $patterns = array();
    $price = $ind['close_last'];

    // PATTERN 1: Triple Oversold Snap — RSI + Stoch + Williams %R all oversold
    // Historically: when RSI<30, Stoch<20, WR<-80 simultaneously on 4H, mean-reversion bounce within 4-12h
    if ($ind['rsi14_last'] < 33 && $ind['stoch_k_last'] < 25 && $ind['wr14_last'] < -75) {
        $conf = 60 + min(20, (30 - $ind['rsi14_last']) + (20 - $ind['stoch_k_last']) * 0.5);
        $patterns[] = array(
            'name' => 'Triple Oversold Snap',
            'dir' => 'LONG',
            'confidence' => min(90, $conf),
            'tp_mult' => 1.8, 'sl_mult' => 1.2,
            'detail' => sprintf('RSI(14)=%.1f + Stoch K=%.1f + WR=%.1f — all oversold on 4H. Mean reversion expected within 4-12h. TP at 1.8x ATR, SL at 1.2x ATR.', $ind['rsi14_last'], $ind['stoch_k_last'], $ind['wr14_last'])
        );
    }

    // PATTERN 2: Triple Overbought Fade — RSI + Stoch + WR all overbought
    if ($ind['rsi14_last'] > 67 && $ind['stoch_k_last'] > 75 && $ind['wr14_last'] > -25) {
        $conf = 55 + min(20, ($ind['rsi14_last'] - 70) + ($ind['stoch_k_last'] - 80) * 0.5);
        $patterns[] = array(
            'name' => 'Triple Overbought Fade',
            'dir' => 'SHORT',
            'confidence' => min(85, $conf),
            'tp_mult' => 1.5, 'sl_mult' => 1.2,
            'detail' => sprintf('RSI(14)=%.1f + Stoch K=%.1f + WR=%.1f — all overbought on 4H. Reversal likely. TP at 1.5x ATR, SL at 1.2x ATR.', $ind['rsi14_last'], $ind['stoch_k_last'], $ind['wr14_last'])
        );
    }

    // PATTERN 3: MACD Bullish Cross + Momentum Shift
    // MACD histogram crosses from negative to positive AND Momentum(10) turns positive
    if ($ind['macd_hist'] > 0 && $ind['macd_hist_prev'] <= 0 && $ind['mom10_last'] > 0) {
        $conf = 55 + min(15, abs($ind['macd_hist']) * 10000);
        $patterns[] = array(
            'name' => 'MACD Bullish Cross + Momentum',
            'dir' => 'LONG',
            'confidence' => min(80, $conf),
            'tp_mult' => 2.0, 'sl_mult' => 1.5,
            'detail' => sprintf('MACD histogram crossed bullish (%.6f) + Momentum(10) positive (%.4f). Trend continuation signal. TP at 2x ATR.', $ind['macd_hist'], $ind['mom10_last'])
        );
    }

    // PATTERN 4: MACD Bearish Cross + Momentum
    if ($ind['macd_hist'] < 0 && $ind['macd_hist_prev'] >= 0 && $ind['mom10_last'] < 0) {
        $conf = 55 + min(15, abs($ind['macd_hist']) * 10000);
        $patterns[] = array(
            'name' => 'MACD Bearish Cross + Momentum',
            'dir' => 'SHORT',
            'confidence' => min(80, $conf),
            'tp_mult' => 2.0, 'sl_mult' => 1.5,
            'detail' => sprintf('MACD histogram crossed bearish (%.6f) + Momentum(10) negative (%.4f). Trend reversal signal.', $ind['macd_hist'], $ind['mom10_last'])
        );
    }

    // PATTERN 5: BB Squeeze Breakout + ADX Trend Confirmation
    // Bollinger Bands compressed (width < 5%) + ADX rising > 20 = imminent breakout
    if ($ind['bb_width'] < 5 && $ind['adx_last'] > 18) {
        $dir = ($price > $ind['bb_m']) ? 'LONG' : 'SHORT';
        $patterns[] = array(
            'name' => 'BB Squeeze Breakout',
            'dir' => $dir,
            'confidence' => 60 + min(15, $ind['adx_last'] - 18),
            'tp_mult' => 2.5, 'sl_mult' => 1.0,
            'detail' => sprintf('BB width compressed to %.1f%% (squeeze). ADX=%.1f confirms trend strength. Price %s mid-band — %s breakout expected.', $ind['bb_width'], $ind['adx_last'], ($dir === 'LONG' ? 'above' : 'below'), $dir)
        );
    }

    // PATTERN 6: Stochastic Bullish Cross from Oversold
    // K crosses above D while both < 25
    if ($ind['stoch_k_last'] > $ind['stoch_d_last'] && $ind['stoch_k_prev'] <= $ind['stoch_d_prev'] && $ind['stoch_k_last'] < 35) {
        $patterns[] = array(
            'name' => 'Stoch Bullish Cross (Oversold)',
            'dir' => 'LONG',
            'confidence' => 55 + min(15, (30 - $ind['stoch_k_last'])),
            'tp_mult' => 1.5, 'sl_mult' => 1.0,
            'detail' => sprintf('Stochastic K(%.1f) crossed above D(%.1f) from oversold zone. Short-term bounce likely.', $ind['stoch_k_last'], $ind['stoch_d_last'])
        );
    }

    // PATTERN 7: CCI Extreme Reversal
    // CCI drops below -200 then starts rising — extreme oversold reversal
    if ($ind['cci20_last'] < -150 && $ind['rsi14_last'] < 35) {
        $patterns[] = array(
            'name' => 'CCI Extreme Reversal',
            'dir' => 'LONG',
            'confidence' => 65,
            'tp_mult' => 2.0, 'sl_mult' => 1.5,
            'detail' => sprintf('CCI(20)=%.1f extreme oversold + RSI(14)=%.1f. Deep mean reversion setup. Historical 65%% bounce rate.', $ind['cci20_last'], $ind['rsi14_last'])
        );
    }

    // PATTERN 8: MA Ribbon Alignment — All short MAs above all long MAs (strong trend)
    if ($ind['ema10'] > $ind['ema20'] && $ind['ema20'] > $ind['ema50'] && $ind['ema50'] > $ind['sma100'] && $ind['adx_last'] > 22) {
        $patterns[] = array(
            'name' => 'MA Ribbon Bullish Alignment',
            'dir' => 'LONG',
            'confidence' => 60 + min(15, $ind['adx_last'] - 20),
            'tp_mult' => 2.5, 'sl_mult' => 1.5,
            'detail' => sprintf('EMA10>EMA20>EMA50>SMA100 + ADX=%.1f. Full bullish ribbon. Ride the trend with wide TP.', $ind['adx_last'])
        );
    }

    // PATTERN 9: HMA Direction Change — Hull MA flip (fast trend detection)
    if ($ind['hma9'] > $ind['hma9_prev'] && $price > $ind['hma9'] && $ind['mom10_last'] > 0) {
        $patterns[] = array(
            'name' => 'HMA Bullish Flip',
            'dir' => 'LONG',
            'confidence' => 55,
            'tp_mult' => 1.5, 'sl_mult' => 1.0,
            'detail' => sprintf('Hull MA(9) turned upward (%.4f > prev %.4f) + price above HMA + positive momentum. Quick trend entry.', $ind['hma9'], $ind['hma9_prev'])
        );
    }

    return $patterns;
}

// ═══════════════════════════════════════════════════════════════
//  MATH FUNCTIONS (TradingView-compatible)
// ═══════════════════════════════════════════════════════════════
function calc_ema($d,$p){$n=count($d);if($n<$p)return array_fill(0,$n,isset($d[$n-1])?$d[$n-1]:0);$k=2.0/($p+1);$e=array_fill(0,$p-1,0);$s=array_sum(array_slice($d,0,$p))/$p;$e[$p-1]=$s;for($i=$p;$i<$n;$i++){$e[$i]=($d[$i]*$k)+($e[$i-1]*(1-$k));}for($i=0;$i<$p-1;$i++){$e[$i]=$e[$p-1];}return $e;}

function calc_sma($d,$p){$n=count($d);$r=array_fill(0,$n,0);for($i=$p-1;$i<$n;$i++){$r[$i]=array_sum(array_slice($d,$i-$p+1,$p))/$p;}for($i=0;$i<$p-1;$i++){$r[$i]=$r[$p-1];}return $r;}

function calc_rsi($c,$p){$n=count($c);$r=array_fill(0,$n,50);if($n<$p+1)return $r;$g=array(0);$lo=array(0);for($i=1;$i<$n;$i++){$d=$c[$i]-$c[$i-1];$g[$i]=($d>0)?$d:0;$lo[$i]=($d<0)?abs($d):0;}$ag=0;$al=0;for($i=1;$i<=$p;$i++){$ag+=$g[$i];$al+=$lo[$i];}$ag/=$p;$al/=$p;$r[$p]=($al==0)?100:100-(100/(1+$ag/$al));for($i=$p+1;$i<$n;$i++){$ag=(($ag*($p-1))+$g[$i])/$p;$al=(($al*($p-1))+$lo[$i])/$p;$r[$i]=($al==0)?100:100-(100/(1+$ag/$al));}return $r;}

function calc_stoch($h,$l,$c,$kp,$dp){$n=count($c);$k=array_fill(0,$n,50);for($i=$kp-1;$i<$n;$i++){$hh=max(array_slice($h,$i-$kp+1,$kp));$ll=min(array_slice($l,$i-$kp+1,$kp));$k[$i]=($hh-$ll>0)?(($c[$i]-$ll)/($hh-$ll)*100):50;}$d=calc_sma($k,$dp);return array('k'=>$k,'d'=>$d);}

function calc_cci($h,$l,$c,$p){$n=count($c);$r=array_fill(0,$n,0);for($i=$p-1;$i<$n;$i++){$tp=array();for($j=$i-$p+1;$j<=$i;$j++){$tp[]=($h[$j]+$l[$j]+$c[$j])/3;}$avg=array_sum($tp)/$p;$md=0;foreach($tp as $v){$md+=abs($v-$avg);}$md/=$p;$r[$i]=($md>0)?(($tp[$p-1]-$avg)/(0.015*$md)):0;}return $r;}

function calc_adx($h,$l,$c,$p){$n=count($c);$pdi=array_fill(0,$n,0);$mdi=array_fill(0,$n,0);$adx=array_fill(0,$n,0);if($n<$p+1)return array('adx'=>$adx,'pdi'=>$pdi,'mdi'=>$mdi);$pdm=array(0);$mdm=array(0);$tr=array(0);for($i=1;$i<$n;$i++){$up=$h[$i]-$h[$i-1];$dn=$l[$i-1]-$l[$i];$pdm[$i]=($up>$dn&&$up>0)?$up:0;$mdm[$i]=($dn>$up&&$dn>0)?$dn:0;$tr[$i]=max($h[$i]-$l[$i],abs($h[$i]-$c[$i-1]),abs($l[$i]-$c[$i-1]));}$atr=0;$apdm=0;$amdm=0;for($i=1;$i<=$p;$i++){$atr+=$tr[$i];$apdm+=$pdm[$i];$amdm+=$mdm[$i];}for($i=$p+1;$i<$n;$i++){$atr=($atr*($p-1)+$tr[$i])/$p;$apdm=($apdm*($p-1)+$pdm[$i])/$p;$amdm=($amdm*($p-1)+$mdm[$i])/$p;$pdi[$i]=($atr>0)?($apdm/$atr*100):0;$mdi[$i]=($atr>0)?($amdm/$atr*100):0;$dx=($pdi[$i]+$mdi[$i]>0)?abs($pdi[$i]-$mdi[$i])/($pdi[$i]+$mdi[$i])*100:0;$adx[$i]=($i==$p+1)?$dx:(($adx[$i-1]*($p-1)+$dx)/$p);}return array('adx'=>$adx,'pdi'=>$pdi,'mdi'=>$mdi);}

function calc_ao($h,$l){$n=count($h);$r=array_fill(0,$n,0);$mp=array();for($i=0;$i<$n;$i++){$mp[$i]=($h[$i]+$l[$i])/2;}$sma5=calc_sma($mp,5);$sma34=calc_sma($mp,34);for($i=0;$i<$n;$i++){$r[$i]=$sma5[$i]-$sma34[$i];}return $r;}

function calc_momentum($c,$p){$n=count($c);$r=array_fill(0,$n,0);for($i=$p;$i<$n;$i++){$r[$i]=$c[$i]-$c[$i-$p];}return $r;}

function calc_macd($c){$n=count($c);$e12=calc_ema($c,12);$e26=calc_ema($c,26);$ml=array_fill(0,$n,0);for($i=0;$i<$n;$i++){$ml[$i]=$e12[$i]-$e26[$i];}$sig=calc_ema($ml,9);$h=array_fill(0,$n,0);for($i=0;$i<$n;$i++){$h[$i]=$ml[$i]-$sig[$i];}return array('l'=>$ml,'s'=>$sig,'h'=>$h);}

function calc_stoch_rsi($c,$rsi_p,$k_p,$d_p){$rsi=calc_rsi($c,$rsi_p);$n=count($rsi);$k=array_fill(0,$n,50);for($i=$rsi_p-1;$i<$n;$i++){$sl=array_slice($rsi,max(0,$i-$rsi_p+1),$rsi_p);$mn=min($sl);$mx=max($sl);$k[$i]=($mx-$mn>0)?(($rsi[$i]-$mn)/($mx-$mn)*100):50;}$d=calc_sma($k,$d_p);return array('k'=>$k,'d'=>$d);}

function calc_williams_r($h,$l,$c,$p){$n=count($c);$r=array_fill(0,$n,-50);for($i=$p-1;$i<$n;$i++){$hh=max(array_slice($h,$i-$p+1,$p));$ll=min(array_slice($l,$i-$p+1,$p));$r[$i]=($hh-$ll>0)?(($hh-$c[$i])/($hh-$ll)*-100):-50;}return $r;}

function calc_bull_bear_power($h,$l,$c,$p){$n=count($c);$r=array_fill(0,$n,0);$ema=calc_ema($c,$p);for($i=0;$i<$n;$i++){$bull=$h[$i]-$ema[$i];$bear=$l[$i]-$ema[$i];$r[$i]=$bull+$bear;}return $r;}

function calc_ultimate_osc($h,$l,$c,$p1,$p2,$p3){$n=count($c);$r=array_fill(0,$n,50);if($n<$p3+1)return $r;$bp=array(0);$tr=array(0);for($i=1;$i<$n;$i++){$bp[$i]=$c[$i]-min($l[$i],$c[$i-1]);$tr[$i]=max($h[$i],$c[$i-1])-min($l[$i],$c[$i-1]);}for($i=$p3;$i<$n;$i++){$s1=0;$t1=0;for($j=$i-$p1+1;$j<=$i;$j++){$s1+=$bp[$j];$t1+=$tr[$j];}$s2=0;$t2=0;for($j=$i-$p2+1;$j<=$i;$j++){$s2+=$bp[$j];$t2+=$tr[$j];}$s3=0;$t3=0;for($j=$i-$p3+1;$j<=$i;$j++){$s3+=$bp[$j];$t3+=$tr[$j];}$a1=($t1>0)?$s1/$t1:0;$a2=($t2>0)?$s2/$t2:0;$a3=($t3>0)?$s3/$t3:0;$r[$i]=100*(4*$a1+2*$a2+$a3)/7;}return $r;}

function calc_hma($c,$p){$n=count($c);if($n<$p)return array_fill(0,$n,isset($c[$n-1])?$c[$n-1]:0);$half=(int)floor($p/2);$sqp=(int)floor(sqrt($p));$wma_half=calc_wma($c,$half);$wma_full=calc_wma($c,$p);$diff=array_fill(0,$n,0);for($i=0;$i<$n;$i++){$diff[$i]=2*$wma_half[$i]-$wma_full[$i];}return calc_wma($diff,$sqp);}

function calc_wma($d,$p){$n=count($d);$r=array_fill(0,$n,0);$w=($p*($p+1))/2;for($i=$p-1;$i<$n;$i++){$s=0;for($j=0;$j<$p;$j++){$s+=$d[$i-$p+1+$j]*($j+1);}$r[$i]=$s/$w;}for($i=0;$i<$p-1;$i++){$r[$i]=$r[$p-1];}return $r;}

function calc_vwma($c,$v,$p){$n=count($c);$r=array_fill(0,$n,0);for($i=$p-1;$i<$n;$i++){$spv=0;$sv=0;for($j=$i-$p+1;$j<=$i;$j++){$spv+=$c[$j]*$v[$j];$sv+=$v[$j];}$r[$i]=($sv>0)?$spv/$sv:$c[$i];}for($i=0;$i<$p-1;$i++){$r[$i]=$r[$p-1];}return $r;}

function calc_atr($h,$l,$c,$p){$n=count($c);$a=array_fill(0,$n,0);if($n<$p+1)return $a;$t=array(0);for($i=1;$i<$n;$i++){$t[$i]=max($h[$i]-$l[$i],abs($h[$i]-$c[$i-1]),abs($l[$i]-$c[$i-1]));}$s=0;for($i=1;$i<=$p;$i++){$s+=$t[$i];}$a[$p]=$s/$p;for($i=$p+1;$i<$n;$i++){$a[$i]=(($a[$i-1]*($p-1))+$t[$i])/$p;}for($i=0;$i<$p;$i++){$a[$i]=$a[$p];}return $a;}

function calc_bb($c,$p,$m){$n=count($c);$u=array_fill(0,$n,0);$mid=array_fill(0,$n,0);$lo=array_fill(0,$n,0);for($i=$p-1;$i<$n;$i++){$sl=array_slice($c,$i-$p+1,$p);$mn=array_sum($sl)/$p;$sq=0;foreach($sl as $v){$sq+=($v-$mn)*($v-$mn);}$sd=sqrt($sq/$p);$mid[$i]=$mn;$u[$i]=$mn+($m*$sd);$lo[$i]=$mn-($m*$sd);}return array('u'=>$u,'m'=>$mid,'l'=>$lo);}

function calc_obv($c,$v){$n=count($c);$o=array_fill(0,$n,0);for($i=1;$i<$n;$i++){if($c[$i]>$c[$i-1])$o[$i]=$o[$i-1]+$v[$i];elseif($c[$i]<$c[$i-1])$o[$i]=$o[$i-1]-$v[$i];else $o[$i]=$o[$i-1];}return $o;}

// ═══════════════════════════════════════════════════════════════
//  DATA FETCHING
// ═══════════════════════════════════════════════════════════════
function fetch_ohlcv_batch($pairs, $interval) {
    $results = array();
    $batches = array_chunk($pairs, 5);
    foreach ($batches as $batch) {
        $mh = curl_multi_init();
        $handles = array();
        foreach ($batch as $pair) {
            $ch = curl_init('https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=' . $interval);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 10);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_USERAGENT, 'TVTechnicals/1.0');
            curl_multi_add_handle($mh, $ch);
            $handles[$pair] = $ch;
        }
        $running = null;
        do { curl_multi_exec($mh, $running); curl_multi_select($mh, 1); } while ($running > 0);
        foreach ($handles as $pair => $ch) {
            $resp = curl_multi_getcontent($ch);
            curl_multi_remove_handle($mh, $ch); curl_close($ch);
            if ($resp) {
                $data = json_decode($resp, true);
                if ($data && isset($data['result'])) {
                    foreach ($data['result'] as $k => $vv) { if ($k !== 'last') { $results[$pair] = $vv; break; } }
                }
            }
        }
        curl_multi_close($mh);
    }
    return $results;
}

function fetch_tickers($pairs) {
    $ch = curl_init('https://api.kraken.com/0/public/Ticker?pair=' . implode(',', $pairs));
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'TVTechnicals/1.0');
    $resp = curl_exec($ch); curl_close($ch);
    if (!$resp) return array();
    $data = json_decode($resp, true);
    if (!$data || !isset($data['result'])) return array();
    $out = array();
    foreach ($data['result'] as $k => $vv) { $out[$k] = floatval($vv['c'][0]); }
    return $out;
}
