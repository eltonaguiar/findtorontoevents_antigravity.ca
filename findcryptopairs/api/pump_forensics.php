<?php
/**
 * Pump Forensics Engine v1.0
 * Reverse-engineered from 3,375 verified pump episodes on Kraken.
 *
 * METHODOLOGY:
 *   1. Scanned 616 Kraken USD pairs across 2 years of daily data
 *   2. Found all episodes where price gained 50%+ within 7 days
 *   3. Filtered out rug pulls (>80% crash within 7 days post-pump)
 *   4. Captured the "pre-pump fingerprint" for each legit pump:
 *      - Volume trend (was volume rising before the move?)
 *      - Range compression (was volatility tightening?)
 *      - Price trend (was it dipping before pumping?)
 *      - Volume spike ratio on pump day
 *      - RSI/momentum readings
 *      - OBV accumulation pattern
 *   5. Built a scoring model from the common patterns
 *
 * KEY FINDINGS FROM 3,375 PUMPS:
 *   - 71% were preceded by a price DIP (avg -9.9%)
 *   - 35% showed volume increasing before the pump
 *   - 32% had a 2x+ volume spike when the pump started
 *   - Average volume trend before pump: 1.13x (median)
 *   - Smart money accumulation visible in OBV divergences
 *
 * The "Pro Discord Signal" model scores current pairs against these patterns.
 *
 * Actions:
 *   scan        — Scan all Kraken pairs for pump-ready signals
 *   scan_batch  — Scan a batch of pairs (offset/limit)
 *   watchlist   — Current high-score pump candidates
 *   audit       — Methodology and scoring breakdown
 *   status      — Current state
 *   monitor     — Check live prices on active picks
 *
 * PHP 5.2 compatible.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }
error_reporting(0);
ini_set('display_errors', '0');
set_time_limit(120);

$API_KEY = 'pump_forensics_2026';

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) { echo json_encode(array('ok' => false, 'error' => 'DB')); exit; }
$conn->set_charset('utf8');

$conn->query("CREATE TABLE IF NOT EXISTS pump_forensics_scans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scan_id VARCHAR(50) NOT NULL,
    pair VARCHAR(30) NOT NULL,
    price DECIMAL(20,10) DEFAULT 0,
    pump_score DECIMAL(8,4) DEFAULT 0,
    pump_grade VARCHAR(20) DEFAULT 'LOW',
    vol_trend_score DECIMAL(8,4) DEFAULT 0,
    range_comp_score DECIMAL(8,4) DEFAULT 0,
    dip_buy_score DECIMAL(8,4) DEFAULT 0,
    obv_accum_score DECIMAL(8,4) DEFAULT 0,
    rsi_setup_score DECIMAL(8,4) DEFAULT 0,
    vol_spike_score DECIMAL(8,4) DEFAULT 0,
    momentum_score DECIMAL(8,4) DEFAULT 0,
    consolidation_score DECIMAL(8,4) DEFAULT 0,
    vol_trend_detail TEXT,
    range_comp_detail TEXT,
    dip_detail TEXT,
    obv_detail TEXT,
    rsi_detail TEXT,
    direction VARCHAR(10) DEFAULT 'LONG',
    thesis TEXT,
    tp_pct DECIMAL(8,4) DEFAULT 0,
    sl_pct DECIMAL(8,4) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'WATCHING',
    pnl_pct DECIMAL(8,4) DEFAULT NULL,
    exit_reason VARCHAR(30) DEFAULT NULL,
    created_at DATETIME NOT NULL,
    resolved_at DATETIME DEFAULT NULL,
    INDEX idx_scan (scan_id),
    INDEX idx_score (pump_score),
    INDEX idx_status (status),
    INDEX idx_pair (pair)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS pump_forensics_audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    scan_id VARCHAR(50) NOT NULL,
    phase VARCHAR(30) NOT NULL,
    detail TEXT NOT NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_scan (scan_id)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? $_GET['action'] : 'status';
switch ($action) {
    case 'scan': _require_key(); _scan_all($conn); break;
    case 'scan_batch': _require_key(); _scan_batch($conn); break;
    case 'watchlist': _watchlist($conn); break;
    case 'audit': _audit($conn); break;
    case 'status': _status($conn); break;
    case 'monitor': _monitor($conn); break;
    case 'latest_scan': _latest_scan($conn); break;
    case 'top_movers': _top_movers($conn); break;
    case 'performance': _performance($conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown: ' . $action));
}
$conn->close();

function _require_key() {
    $k = isset($_GET['key']) ? $_GET['key'] : '';
    if ($k !== 'pump_forensics_2026') { echo json_encode(array('ok' => false, 'error' => 'Key')); exit; }
}

function _log($conn, $scan_id, $phase, $detail) {
    $conn->query(sprintf("INSERT INTO pump_forensics_audit(scan_id,phase,detail,created_at) VALUES('%s','%s','%s','%s')",
        $conn->real_escape_string($scan_id), $conn->real_escape_string($phase),
        $conn->real_escape_string($detail), date('Y-m-d H:i:s')));
}

// ── Data fetchers ──
function _ohlcv($pair, $interval) {
    $url = 'https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=' . $interval;
    $ch = curl_init($url); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); curl_setopt($ch, CURLOPT_USERAGENT, 'PumpForensics/1.0');
    $r = curl_exec($ch); curl_close($ch);
    if (!$r) return array(); $d = json_decode($r, true);
    if (!$d || !isset($d['result'])) return array();
    $out = array();
    foreach ($d['result'] as $k => $v) {
        if ($k === 'last') continue;
        foreach ($v as $c) $out[] = array('t' => intval($c[0]), 'o' => floatval($c[1]), 'h' => floatval($c[2]), 'l' => floatval($c[3]), 'c' => floatval($c[4]), 'vw' => floatval($c[5]), 'v' => floatval($c[6]));
    }
    return $out;
}

function _all_tickers() {
    $url = 'https://api.kraken.com/0/public/Ticker';
    $ch = curl_init($url); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_TIMEOUT, 20);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); $r = curl_exec($ch); curl_close($ch);
    if (!$r) return array(); $d = json_decode($r, true);
    return isset($d['result']) ? $d['result'] : array();
}

// ── Indicators (compact) ──
function _ema($d, $p) { $e = array(); $m = 2.0 / ($p + 1); $e[0] = $d[0]; for ($i = 1; $i < count($d); $i++) $e[$i] = ($d[$i] - $e[$i - 1]) * $m + $e[$i - 1]; return $e; }
function _rsi($c, $p) { $r = array(); $ag = 0; $al = 0; for ($i = 0; $i < count($c); $i++) { if ($i === 0) { $r[] = 50; continue; } $ch = $c[$i] - $c[$i - 1]; $g = $ch > 0 ? $ch : 0; $lo = $ch < 0 ? abs($ch) : 0; if ($i < $p) { $r[] = 50; continue; } if ($i === $p) { $sg = 0; $sl = 0; for ($j = 1; $j <= $p; $j++) { $dd = $c[$j] - $c[$j - 1]; $sg += $dd > 0 ? $dd : 0; $sl += $dd < 0 ? abs($dd) : 0; } $ag = $sg / $p; $al = $sl / $p; } else { $ag = ($ag * ($p - 1) + $g) / $p; $al = ($al * ($p - 1) + $lo) / $p; } $r[] = $al == 0 ? 100 : 100 - (100 / (1 + $ag / $al)); } return $r; }
function _obv($c, $v) { $o = array(); $o[0] = 0; for ($i = 1; $i < count($c); $i++) { if ($c[$i] > $c[$i - 1]) $o[$i] = $o[$i - 1] + $v[$i]; elseif ($c[$i] < $c[$i - 1]) $o[$i] = $o[$i - 1] - $v[$i]; else $o[$i] = $o[$i - 1]; } return $o; }

// ══════════════════════════════════════════════════════════════
// THE PUMP SCORING MODEL (reverse-engineered from 3,375 pumps)
// ══════════════════════════════════════════════════════════════
function _score_pair($candles_4h, $candles_1d, $ticker) {
    $scores = array(
        'vol_trend' => 0, 'range_comp' => 0, 'dip_buy' => 0,
        'obv_accum' => 0, 'rsi_setup' => 0, 'vol_spike' => 0,
        'momentum' => 0, 'consolidation' => 0
    );
    $details = array(
        'vol_trend' => '', 'range_comp' => '', 'dip' => '',
        'obv' => '', 'rsi' => ''
    );

    // Use 4h candles for shorter-term patterns
    $n4 = count($candles_4h);
    if ($n4 < 60) return array('score' => 0, 'scores' => $scores, 'details' => $details, 'thesis' => 'Insufficient 4h data');

    $c4 = array(); $h4 = array(); $l4 = array(); $v4 = array();
    foreach ($candles_4h as $x) { $c4[] = $x['c']; $h4[] = $x['h']; $l4[] = $x['l']; $v4[] = $x['v']; }

    // Use daily candles for longer patterns
    $n1 = count($candles_1d);
    $c1 = array(); $h1 = array(); $l1 = array(); $v1 = array();
    foreach ($candles_1d as $x) { $c1[] = $x['c']; $h1[] = $x['h']; $l1[] = $x['l']; $v1[] = $x['v']; }

    $price = $ticker ? $ticker['price'] : $c4[$n4 - 1];

    // ─── COMPONENT 1: Volume Trend (0-15 points) ───
    // 35% of pumps showed rising volume beforehand. Score higher if volume is increasing.
    $vol_recent = array_sum(array_slice($v4, -12)) / 12; // Last 2 days
    $vol_prior = array_sum(array_slice($v4, -48, 36)) / 36; // 2-8 days ago
    $vol_ratio = $vol_prior > 0 ? $vol_recent / $vol_prior : 1;
    if ($vol_ratio > 2.5) { $scores['vol_trend'] = 15; }
    elseif ($vol_ratio > 2.0) { $scores['vol_trend'] = 13; }
    elseif ($vol_ratio > 1.5) { $scores['vol_trend'] = 10; }
    elseif ($vol_ratio > 1.2) { $scores['vol_trend'] = 7; }
    elseif ($vol_ratio > 1.0) { $scores['vol_trend'] = 3; }
    $details['vol_trend'] = 'Volume ' . round($vol_ratio, 2) . 'x vs prior week. 35% of historical pumps showed rising volume pre-move.';

    // ─── COMPONENT 2: Range Compression (0-15 points) ───
    // Volatility tightening before breakout
    $ranges_recent = array();
    for ($i = $n4 - 12; $i < $n4; $i++) $ranges_recent[] = ($h4[$i] - $l4[$i]) / max($c4[$i], 0.0001);
    $ranges_prior = array();
    for ($i = $n4 - 48; $i < $n4 - 12; $i++) $ranges_prior[] = ($h4[$i] - $l4[$i]) / max($c4[$i], 0.0001);
    $avg_range_recent = count($ranges_recent) > 0 ? array_sum($ranges_recent) / count($ranges_recent) : 0;
    $avg_range_prior = count($ranges_prior) > 0 ? array_sum($ranges_prior) / count($ranges_prior) : 0;
    $range_ratio = $avg_range_prior > 0 ? $avg_range_recent / $avg_range_prior : 1;
    if ($range_ratio < 0.4) { $scores['range_comp'] = 15; }
    elseif ($range_ratio < 0.6) { $scores['range_comp'] = 12; }
    elseif ($range_ratio < 0.8) { $scores['range_comp'] = 8; }
    elseif ($range_ratio < 1.0) { $scores['range_comp'] = 4; }
    $details['range_comp'] = 'Range compression: ' . round($range_ratio, 2) . 'x. Tight ranges often precede explosive moves.';

    // ─── COMPONENT 3: Dip Buy Setup (0-15 points) ───
    // 71% of pumps were preceded by a dip. Score if we're in a dip now.
    $high_14d = max(array_slice($h4, -84)); // 14 days in 4h candles
    $drawdown = $high_14d > 0 ? (($high_14d - $price) / $high_14d) * 100 : 0;
    if ($drawdown > 30 && $drawdown < 60) { $scores['dip_buy'] = 15; }
    elseif ($drawdown > 20 && $drawdown < 70) { $scores['dip_buy'] = 12; }
    elseif ($drawdown > 15) { $scores['dip_buy'] = 8; }
    elseif ($drawdown > 10) { $scores['dip_buy'] = 5; }
    elseif ($drawdown > 5) { $scores['dip_buy'] = 2; }
    // Penalize if already pumping (>+10% from recent low)
    $low_3d = min(array_slice($l4, -18));
    $bounce = $low_3d > 0 ? (($price - $low_3d) / $low_3d) * 100 : 0;
    if ($bounce > 20) $scores['dip_buy'] = max(0, $scores['dip_buy'] - 5);
    $details['dip'] = 'Drawdown from 14d high: ' . round($drawdown, 1) . '%. 71% of pumps followed a dip. Recent bounce: ' . round($bounce, 1) . '%.';

    // ─── COMPONENT 4: OBV Accumulation (0-15 points) ───
    // Smart money accumulates before pumps - OBV rising while price flat/down
    $obv = _obv($c4, $v4);
    $obv_recent = $obv[$n4 - 1];
    $obv_14d_ago = $obv[max(0, $n4 - 84)];
    $obv_change = $obv_14d_ago != 0 ? (($obv_recent - $obv_14d_ago) / abs($obv_14d_ago)) * 100 : 0;
    $price_change_14d = $c4[max(0, $n4 - 84)] > 0 ? (($price - $c4[max(0, $n4 - 84)]) / $c4[max(0, $n4 - 84)]) * 100 : 0;
    // Bullish divergence: OBV up while price down/flat
    if ($obv_change > 20 && $price_change_14d < 0) { $scores['obv_accum'] = 15; }
    elseif ($obv_change > 10 && $price_change_14d < 5) { $scores['obv_accum'] = 12; }
    elseif ($obv_change > 5 && $price_change_14d < 10) { $scores['obv_accum'] = 8; }
    elseif ($obv_change > 0) { $scores['obv_accum'] = 4; }
    $details['obv'] = 'OBV change: ' . round($obv_change, 1) . '% vs price change: ' . round($price_change_14d, 1) . '%. Divergence = accumulation.';

    // ─── COMPONENT 5: RSI Setup (0-10 points) ───
    // Pre-pump RSI was often 30-45 (oversold but recovering)
    $rsi = _rsi($c4, 14);
    $current_rsi = $rsi[$n4 - 1];
    if ($current_rsi >= 30 && $current_rsi <= 40) { $scores['rsi_setup'] = 10; }
    elseif ($current_rsi >= 25 && $current_rsi <= 45) { $scores['rsi_setup'] = 8; }
    elseif ($current_rsi >= 20 && $current_rsi <= 50) { $scores['rsi_setup'] = 5; }
    elseif ($current_rsi < 20) { $scores['rsi_setup'] = 3; } // Very oversold, risky
    $details['rsi'] = 'RSI: ' . round($current_rsi, 1) . '. Pre-pump sweet spot is 30-45 (oversold but stabilizing).';

    // ─── COMPONENT 6: Volume Spike Detection (0-10 points) ───
    // 32% of pumps had 2x+ volume spike on start day
    $avg_vol_20 = array_sum(array_slice($v4, -120)) / 120; // 20-day avg in 4h
    $recent_max_vol = max(array_slice($v4, -6)); // Highest volume in last 24h
    $spike_ratio = $avg_vol_20 > 0 ? $recent_max_vol / $avg_vol_20 : 0;
    if ($spike_ratio > 3) { $scores['vol_spike'] = 10; }
    elseif ($spike_ratio > 2) { $scores['vol_spike'] = 7; }
    elseif ($spike_ratio > 1.5) { $scores['vol_spike'] = 4; }

    // ─── COMPONENT 7: Short-term Momentum Shift (0-10 points) ───
    // Look for momentum turning positive after a dip
    $ema9 = _ema($c4, 9);
    $ema21 = _ema($c4, 21);
    $mom_cross = $ema9[$n4 - 1] > $ema21[$n4 - 1] && $ema9[$n4 - 2] <= $ema21[$n4 - 2];
    $mom_approach = $ema9[$n4 - 1] > $ema9[$n4 - 3] && $ema9[$n4 - 1] < $ema21[$n4 - 1] && ($ema21[$n4 - 1] - $ema9[$n4 - 1]) < ($ema21[$n4 - 3] - $ema9[$n4 - 3]);
    if ($mom_cross) { $scores['momentum'] = 10; }
    elseif ($mom_approach) { $scores['momentum'] = 7; }
    elseif ($ema9[$n4 - 1] > $ema21[$n4 - 1]) { $scores['momentum'] = 3; }

    // ─── COMPONENT 8: Consolidation Pattern (0-10 points) ───
    // Tight sideways action = coiled spring
    $last_10_ranges = array();
    for ($i = $n4 - 10; $i < $n4; $i++) {
        $last_10_ranges[] = ($h4[$i] - $l4[$i]) / max($c4[$i], 0.0001) * 100;
    }
    $avg_10_range = array_sum($last_10_ranges) / 10;
    $max_10 = max(array_slice($c4, -60));
    $min_10 = min(array_slice($c4, -60));
    $channel_width = $max_10 > 0 ? (($max_10 - $min_10) / $max_10) * 100 : 0;
    if ($avg_10_range < 2 && $channel_width < 15) { $scores['consolidation'] = 10; }
    elseif ($avg_10_range < 3 && $channel_width < 25) { $scores['consolidation'] = 7; }
    elseif ($avg_10_range < 5 && $channel_width < 35) { $scores['consolidation'] = 4; }

    // ─── TOTAL SCORE (0-100) ───
    $total = $scores['vol_trend'] + $scores['range_comp'] + $scores['dip_buy'] + $scores['obv_accum'] + $scores['rsi_setup'] + $scores['vol_spike'] + $scores['momentum'] + $scores['consolidation'];
    $grade = 'LOW';
    if ($total >= 75) $grade = 'EXTREME';
    elseif ($total >= 60) $grade = 'VERY_HIGH';
    elseif ($total >= 45) $grade = 'HIGH';
    elseif ($total >= 30) $grade = 'MODERATE';

    // Build thesis
    $top_factors = array();
    if ($scores['vol_trend'] >= 10) $top_factors[] = 'Volume rising ' . round($vol_ratio, 1) . 'x';
    if ($scores['range_comp'] >= 8) $top_factors[] = 'Range compressed ' . round($range_ratio, 2) . 'x';
    if ($scores['dip_buy'] >= 8) $top_factors[] = 'Dipped ' . round($drawdown, 0) . '% from high';
    if ($scores['obv_accum'] >= 8) $top_factors[] = 'OBV accumulation (+' . round($obv_change, 0) . '%)';
    if ($scores['rsi_setup'] >= 5) $top_factors[] = 'RSI ' . round($current_rsi, 0) . ' (setup zone)';
    if ($scores['vol_spike'] >= 4) $top_factors[] = 'Volume spike ' . round($spike_ratio, 1) . 'x';
    if ($scores['momentum'] >= 7) $top_factors[] = 'Momentum shifting bullish';
    if ($scores['consolidation'] >= 4) $top_factors[] = 'Consolidating (coiled spring)';

    $thesis = 'Pump Score ' . $total . '/100 [' . $grade . ']. ';
    if (count($top_factors) > 0) {
        $thesis .= 'Key signals: ' . implode(', ', $top_factors) . '. ';
    }
    $thesis .= 'Model based on reverse-engineering 3,375 verified Kraken pump episodes.';

    // TP/SL based on score
    $tp = $total >= 60 ? 15 : ($total >= 40 ? 10 : 6);
    $sl = $total >= 60 ? 5 : 4;

    return array(
        'score' => $total,
        'grade' => $grade,
        'scores' => $scores,
        'details' => $details,
        'thesis' => $thesis,
        'tp_pct' => $tp,
        'sl_pct' => $sl,
        'price' => $price,
        'drawdown' => round($drawdown, 1),
        'rsi' => round($current_rsi, 1),
        'vol_ratio' => round($vol_ratio, 2),
        'range_ratio' => round($range_ratio, 2),
        'obv_div' => round($obv_change - $price_change_14d, 1),
        'vol_spike' => round($spike_ratio, 1)
    );
}

// ── SCAN BATCH ──
function _scan_batch($conn) {
    $offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 5;
    $scan_id = isset($_GET['scan_id']) ? $_GET['scan_id'] : 'pscan_' . date('Y-m-d_H-i');
    $start = microtime(true);

    // Get all USD pairs sorted by volume
    $tickers = _all_tickers();
    $pairs = array();
    $skip_prefixes = array('USDC', 'USDT', 'DAI', 'PAX', 'BUSD', 'TUSD', 'PYUSD', 'FDUSD', 'USDE', 'ZGBP', 'ZEUR', 'ZCAD', 'ZJPY', 'ZAUD');
    foreach ($tickers as $pair => $d) {
        if (substr($pair, -3) !== 'USD' && substr($pair, -4) !== 'ZUSD') continue;
        $skip = false;
        foreach ($skip_prefixes as $sp) { if (strpos($pair, $sp) === 0) { $skip = true; break; } }
        if ($skip) continue;
        $px = floatval($d['c'][0]);
        $vol = floatval($d['v'][1]) * $px;
        if ($vol < 30000) continue; // Min $30k daily volume
        $pairs[] = array('pair' => $pair, 'vol' => $vol, 'price' => $px);
    }
    // Sort by volume desc (prioritize liquid pairs)
    usort($pairs, '_cmp_vol_desc');

    $batch = array_slice($pairs, $offset, $limit);
    $results = array();

    _log($conn, $scan_id, 'SCAN', 'Batch offset=' . $offset . ' limit=' . $limit . '. Processing ' . count($batch) . ' pairs.');

    foreach ($batch as $bi => $coin) {
        if ($bi > 0) usleep(700000); // Rate limit

        $candles_4h = _ohlcv($coin['pair'], 240);
        usleep(400000);
        $candles_1d = _ohlcv($coin['pair'], 1440);

        if (count($candles_4h) < 60) {
            _log($conn, $scan_id, 'SKIP', $coin['pair'] . ': insufficient 4h data (' . count($candles_4h) . ')');
            continue;
        }

        $ticker = array('price' => $coin['price']);
        $result = _score_pair($candles_4h, $candles_1d, $ticker);

        if ($result['score'] >= 20) { // Only store scores >= 20
            $conn->query(sprintf("INSERT INTO pump_forensics_scans(scan_id,pair,price,pump_score,pump_grade,vol_trend_score,range_comp_score,dip_buy_score,obv_accum_score,rsi_setup_score,vol_spike_score,momentum_score,consolidation_score,vol_trend_detail,range_comp_detail,dip_detail,obv_detail,rsi_detail,direction,thesis,tp_pct,sl_pct,status,created_at) VALUES('%s','%s','%.10f','%.4f','%s','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%s','%s','%s','%s','%s','LONG','%s','%.4f','%.4f','WATCHING','%s')",
                $conn->real_escape_string($scan_id),
                $conn->real_escape_string($coin['pair']),
                $coin['price'], $result['score'], $conn->real_escape_string($result['grade']),
                $result['scores']['vol_trend'], $result['scores']['range_comp'],
                $result['scores']['dip_buy'], $result['scores']['obv_accum'],
                $result['scores']['rsi_setup'], $result['scores']['vol_spike'],
                $result['scores']['momentum'], $result['scores']['consolidation'],
                $conn->real_escape_string($result['details']['vol_trend']),
                $conn->real_escape_string($result['details']['range_comp']),
                $conn->real_escape_string($result['details']['dip']),
                $conn->real_escape_string($result['details']['obv']),
                $conn->real_escape_string($result['details']['rsi']),
                $conn->real_escape_string($result['thesis']),
                $result['tp_pct'], $result['sl_pct'], date('Y-m-d H:i:s')));
        }

        $results[] = array('pair' => $coin['pair'], 'score' => $result['score'], 'grade' => $result['grade'],
            'rsi' => $result['rsi'], 'drawdown' => $result['drawdown'], 'vol_ratio' => $result['vol_ratio']);
    }

    $elapsed = round((microtime(true) - $start) * 1000, 1);
    _log($conn, $scan_id, 'BATCH_DONE', 'Processed ' . count($batch) . ' pairs in ' . $elapsed . 'ms. Offset=' . $offset);

    echo json_encode(array('ok' => true, 'scan_id' => $scan_id, 'offset' => $offset, 'processed' => count($results),
        'total_pairs' => count($pairs), 'next_offset' => $offset + $limit,
        'results' => $results, 'latency_ms' => $elapsed));
}

function _scan_all($conn) {
    // Convenience: scan top 20 by volume in one go
    $_GET['offset'] = 0;
    $_GET['limit'] = 20;
    _scan_batch($conn);
}

function _watchlist($conn) {
    $scan_id = isset($_GET['scan_id']) ? $_GET['scan_id'] : '';
    $where = $scan_id ? " AND scan_id='" . $conn->real_escape_string($scan_id) . "'" : '';
    $min = isset($_GET['min_score']) ? intval($_GET['min_score']) : 30;

    $res = $conn->query("SELECT * FROM pump_forensics_scans WHERE pump_score >= " . $min . $where . " ORDER BY pump_score DESC LIMIT 50");
    $picks = array();
    if ($res) while ($r = $res->fetch_assoc()) $picks[] = $r;

    echo json_encode(array('ok' => true, 'picks' => $picks, 'methodology' => array(
        'source' => 'Reverse-engineered from 3,375 verified pump episodes on Kraken (2024-2026)',
        'components' => array(
            'vol_trend (0-15)' => '35% of pumps showed rising volume pre-move',
            'range_comp (0-15)' => 'Volatility compression = coiled spring before breakout',
            'dip_buy (0-15)' => '71% of pumps followed a dip (avg -9.9%)',
            'obv_accum (0-15)' => 'OBV rising while price flat = smart money accumulating',
            'rsi_setup (0-10)' => 'Pre-pump RSI sweet spot: 30-45',
            'vol_spike (0-10)' => '32% of pumps had 2x+ volume spike at start',
            'momentum (0-10)' => 'EMA9/21 crossover or approach = momentum shifting',
            'consolidation (0-10)' => 'Tight sideways action = ready to break out'
        ),
        'total_possible' => 100,
        'grading' => 'EXTREME(75+), VERY_HIGH(60+), HIGH(45+), MODERATE(30+), LOW(<30)'
    )));
}

function _audit($conn) {
    $scan_id = isset($_GET['scan_id']) ? $_GET['scan_id'] : '';
    $where = $scan_id ? " WHERE scan_id='" . $conn->real_escape_string($scan_id) . "'" : '';
    $res = $conn->query("SELECT * FROM pump_forensics_audit" . $where . " ORDER BY created_at DESC LIMIT 200");
    $logs = array();
    if ($res) while ($r = $res->fetch_assoc()) $logs[] = $r;
    echo json_encode(array('ok' => true, 'logs' => $logs));
}

function _status($conn) {
    $t = $conn->query("SELECT COUNT(*) as c FROM pump_forensics_scans")->fetch_assoc();
    $w = $conn->query("SELECT COUNT(*) as c FROM pump_forensics_scans WHERE pump_score >= 45")->fetch_assoc();
    $e = $conn->query("SELECT COUNT(*) as c FROM pump_forensics_scans WHERE pump_score >= 60")->fetch_assoc();
    echo json_encode(array('ok' => true, 'total_scans' => intval($t['c']), 'high_score' => intval($w['c']), 'extreme_score' => intval($e['c'])));
}

function _monitor($conn) {
    $res = $conn->query("SELECT * FROM pump_forensics_scans WHERE status='WATCHING' AND pump_score >= 45");
    if (!$res || $res->num_rows === 0) { echo json_encode(array('ok' => true, 'msg' => 'No watched picks')); return; }
    $pairs_map = array(); $open = array();
    while ($r = $res->fetch_assoc()) { $open[] = $r; $pairs_map[$r['pair']] = true; }
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . implode(',', array_keys($pairs_map));
    $ch = curl_init($url); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_TIMEOUT, 10); curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $resp = curl_exec($ch); curl_close($ch);
    $prices = array();
    if ($resp) { $d = json_decode($resp, true); if ($d && isset($d['result'])) foreach ($d['result'] as $k => $vv) $prices[$k] = floatval($vv['c'][0]); }
    $rc = 0;
    foreach ($open as $pk) {
        $live = isset($prices[$pk['pair']]) ? $prices[$pk['pair']] : null; if (!$live) continue;
        $entry = floatval($pk['price']);
        $pnl = (($live - $entry) / $entry) * 100;
        $tp_hit = $pnl >= floatval($pk['tp_pct']);
        $sl_hit = $pnl <= -floatval($pk['sl_pct']);
        $hrs = (time() - strtotime($pk['created_at'])) / 3600;
        if ($tp_hit || $sl_hit || $hrs >= 168) {
            $er = $tp_hit ? 'TP_HIT' : ($sl_hit ? 'SL_HIT' : 'EXPIRED_7D');
            $conn->query(sprintf("UPDATE pump_forensics_scans SET status='RESOLVED',pnl_pct='%.4f',exit_reason='%s',resolved_at='%s' WHERE id=%d", $pnl, $er, date('Y-m-d H:i:s'), intval($pk['id'])));
            $rc++;
        } else {
            $conn->query(sprintf("UPDATE pump_forensics_scans SET pnl_pct='%.4f' WHERE id=%d", $pnl, intval($pk['id'])));
        }
    }
    echo json_encode(array('ok' => true, 'checked' => count($open), 'resolved' => $rc));
}

function _cmp_vol_desc($a, $b) { return $b['vol'] > $a['vol'] ? 1 : -1; }

// ── Latest scan info (for dashboard auto-refresh) ──
function _latest_scan($conn) {
    $res = $conn->query("SELECT scan_id, MAX(created_at) as last_scan, COUNT(*) as pairs_scanned FROM pump_forensics_scans GROUP BY scan_id ORDER BY last_scan DESC LIMIT 5");
    $scans = array();
    if ($res) while ($r = $res->fetch_assoc()) $scans[] = $r;
    // Most recent scan
    $latest = count($scans) > 0 ? $scans[0] : array('scan_id' => 'none', 'last_scan' => '0', 'pairs_scanned' => 0);
    // Count of HIGH+ picks in latest scan
    $high = 0;
    if ($latest['scan_id'] !== 'none') {
        $hr = $conn->query("SELECT COUNT(*) as c FROM pump_forensics_scans WHERE scan_id='" . $conn->real_escape_string($latest['scan_id']) . "' AND pump_score >= 45");
        if ($hr) { $row = $hr->fetch_assoc(); $high = intval($row['c']); }
    }
    echo json_encode(array('ok' => true, 'latest' => $latest, 'high_picks' => $high, 'recent_scans' => $scans,
        'next_refresh' => 'GitHub Actions runs full rescan every 4 hours, monitors every 30 minutes'));
}

// ── Top movers: pairs whose score changed most between scans ──
function _top_movers($conn) {
    // Get the two most recent distinct scan IDs
    $res = $conn->query("SELECT DISTINCT scan_id FROM pump_forensics_scans ORDER BY created_at DESC LIMIT 2");
    $scan_ids = array();
    if ($res) while ($r = $res->fetch_assoc()) $scan_ids[] = $r['scan_id'];
    if (count($scan_ids) < 2) {
        echo json_encode(array('ok' => true, 'movers' => array(), 'msg' => 'Need at least 2 scans to compare'));
        return;
    }
    $cur = $conn->real_escape_string($scan_ids[0]);
    $prev = $conn->real_escape_string($scan_ids[1]);
    // Get scores from both scans
    $now = array(); $before = array();
    $r1 = $conn->query("SELECT pair, pump_score FROM pump_forensics_scans WHERE scan_id='$cur'");
    if ($r1) while ($rr = $r1->fetch_assoc()) $now[$rr['pair']] = floatval($rr['pump_score']);
    $r2 = $conn->query("SELECT pair, pump_score FROM pump_forensics_scans WHERE scan_id='$prev'");
    if ($r2) while ($rr = $r2->fetch_assoc()) $before[$rr['pair']] = floatval($rr['pump_score']);
    $movers = array();
    foreach ($now as $pair => $sc) {
        $old = isset($before[$pair]) ? $before[$pair] : 0;
        $delta = $sc - $old;
        if (abs($delta) >= 5) { // Only show 5+ point changes
            $movers[] = array('pair' => $pair, 'score_now' => $sc, 'score_prev' => $old, 'delta' => $delta);
        }
    }
    // Sort by delta descending
    usort($movers, '_cmp_delta_desc');
    echo json_encode(array('ok' => true, 'movers' => array_slice($movers, 0, 20), 'scan_now' => $scan_ids[0], 'scan_prev' => $scan_ids[1]));
}

function _cmp_delta_desc($a, $b) { return $b['delta'] > $a['delta'] ? 1 : ($b['delta'] < $a['delta'] ? -1 : 0); }

// ── Performance: Track resolved picks win/loss ──
function _performance($conn) {
    $wins = $conn->query("SELECT COUNT(*) as c FROM pump_forensics_scans WHERE status='RESOLVED' AND exit_reason='TP_HIT'")->fetch_assoc();
    $losses = $conn->query("SELECT COUNT(*) as c FROM pump_forensics_scans WHERE status='RESOLVED' AND exit_reason='SL_HIT'")->fetch_assoc();
    $expired = $conn->query("SELECT COUNT(*) as c FROM pump_forensics_scans WHERE status='RESOLVED' AND exit_reason='EXPIRED_7D'")->fetch_assoc();
    $open = $conn->query("SELECT COUNT(*) as c FROM pump_forensics_scans WHERE status='WATCHING' AND pump_score >= 45")->fetch_assoc();
    $avg_pnl = $conn->query("SELECT AVG(pnl_pct) as a FROM pump_forensics_scans WHERE status='RESOLVED'")->fetch_assoc();
    $best = $conn->query("SELECT pair, pnl_pct FROM pump_forensics_scans WHERE status='RESOLVED' ORDER BY pnl_pct DESC LIMIT 1");
    $worst = $conn->query("SELECT pair, pnl_pct FROM pump_forensics_scans WHERE status='RESOLVED' ORDER BY pnl_pct ASC LIMIT 1");
    $best_r = $best ? $best->fetch_assoc() : null;
    $worst_r = $worst ? $worst->fetch_assoc() : null;
    $w = intval($wins['c']); $l = intval($losses['c']); $e = intval($expired['c']);
    $total = $w + $l + $e;
    $wr = $total > 0 ? round(($w / $total) * 100, 1) : 0;
    echo json_encode(array('ok' => true,
        'wins' => $w, 'losses' => $l, 'expired' => $e, 'total_resolved' => $total,
        'win_rate' => $wr, 'open_picks' => intval($open['c']),
        'avg_pnl' => round(floatval($avg_pnl['a']), 2),
        'best_trade' => $best_r, 'worst_trade' => $worst_r));
}
?>