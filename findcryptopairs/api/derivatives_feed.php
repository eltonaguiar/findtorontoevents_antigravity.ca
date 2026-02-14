<?php
/**
 * Derivatives Data Feed v1.0
 * Fetches real funding rates, open interest, and long/short ratios from Binance Futures API.
 * Also computes Supertrend indicator from OHLCV data.
 *
 * Actions:
 *   all      — Full derivatives snapshot for all assets (default)
 *   funding  — Funding rates only
 *   oi       — Open interest only
 *   lsratio  — Long/short ratio only
 *   super    — Supertrend signals only
 *
 * PHP 5.2 compatible.  Free Binance endpoints, no API key needed.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

error_reporting(0);
ini_set('display_errors', '0');

$ASSETS = array(
    'BTC'  => array('binance' => 'BTCUSDT',  'kraken' => 'XXBTZUSD'),
    'ETH'  => array('binance' => 'ETHUSDT',  'kraken' => 'XETHZUSD'),
    'AVAX' => array('binance' => 'AVAXUSDT', 'kraken' => 'AVAXUSD')
);

$action = isset($_GET['action']) ? $_GET['action'] : 'all';

$result = array('ok' => true, 'timestamp' => date('Y-m-d H:i:s T'));
$start  = microtime(true);

switch ($action) {
    case 'funding':
        $result['funding'] = _fetch_all_funding();
        break;
    case 'oi':
        $result['open_interest'] = _fetch_all_oi();
        break;
    case 'lsratio':
        $result['long_short_ratio'] = _fetch_all_ls();
        break;
    case 'super':
        $result['supertrend'] = _fetch_all_supertrend();
        break;
    case 'all':
    default:
        $result['funding']          = _fetch_all_funding();
        $result['open_interest']    = _fetch_all_oi();
        $result['long_short_ratio'] = _fetch_all_ls();
        $result['supertrend']       = _fetch_all_supertrend();
        $result['risk_scores']      = _compute_risk_scores($result);
        break;
}

$result['latency_ms'] = round((microtime(true) - $start) * 1000);
echo json_encode($result);

// ═══════════════════════════════════════════════════════════════════════
//  FUNDING RATES — from Binance Futures (free, no key)
// ═══════════════════════════════════════════════════════════════════════
function _fetch_all_funding()
{
    global $ASSETS;
    $out = array();
    foreach ($ASSETS as $name => $pair) {
        $url = 'https://fapi.binance.com/fapi/v1/fundingRate?symbol=' . $pair['binance'] . '&limit=10';
        $data = _curl_json($url);
        if ($data && is_array($data) && count($data) > 0) {
            $latest   = $data[0];
            $rate     = floatval($latest['fundingRate']);
            $annual   = $rate * 3 * 365; // 3 funding periods per day

            // Calculate average over last 10 readings
            $sum = 0;
            foreach ($data as $d) { $sum += floatval($d['fundingRate']); }
            $avg = $sum / count($data);

            // Extreme detection
            $extreme = 'NEUTRAL';
            if ($rate > 0.001)      $extreme = 'HIGH_POSITIVE';   // Crowded longs
            elseif ($rate > 0.0005) $extreme = 'POSITIVE';
            elseif ($rate < -0.001) $extreme = 'HIGH_NEGATIVE';   // Crowded shorts
            elseif ($rate < -0.0005) $extreme = 'NEGATIVE';

            $out[$name] = array(
                'current_rate'    => $rate,
                'annualized'      => round($annual * 100, 2) . '%',
                'avg_10_readings' => round($avg, 6),
                'extreme'         => $extreme,
                'contrarian_signal' => ($extreme === 'HIGH_POSITIVE') ? 'BEARISH' : (($extreme === 'HIGH_NEGATIVE') ? 'BULLISH' : 'NONE'),
                'raw_data_count'  => count($data)
            );
        } else {
            $out[$name] = array('error' => 'fetch_failed');
        }
    }
    return $out;
}

// ═══════════════════════════════════════════════════════════════════════
//  OPEN INTEREST — from Binance Futures
// ═══════════════════════════════════════════════════════════════════════
function _fetch_all_oi()
{
    global $ASSETS;
    $out = array();
    foreach ($ASSETS as $name => $pair) {
        $url = 'https://fapi.binance.com/fapi/v1/openInterest?symbol=' . $pair['binance'];
        $data = _curl_json($url);
        if ($data && isset($data['openInterest'])) {
            $oi = floatval($data['openInterest']);

            // Also get historical OI for trend detection
            $hist_url = 'https://fapi.binance.com/futures/data/openInterestHist?symbol=' . $pair['binance'] . '&period=1d&limit=14';
            $hist = _curl_json($hist_url);
            $oi_trend = 'UNKNOWN';
            $oi_change_pct = 0;

            if ($hist && is_array($hist) && count($hist) >= 7) {
                $recent = floatval($hist[count($hist) - 1]['sumOpenInterest']);
                $week_ago = floatval($hist[count($hist) - 7]['sumOpenInterest']);
                if ($week_ago > 0) {
                    $oi_change_pct = round((($recent - $week_ago) / $week_ago) * 100, 2);
                    if ($oi_change_pct > 10)     $oi_trend = 'SURGING';
                    elseif ($oi_change_pct > 3)   $oi_trend = 'RISING';
                    elseif ($oi_change_pct < -10)  $oi_trend = 'COLLAPSING';
                    elseif ($oi_change_pct < -3)   $oi_trend = 'DECLINING';
                    else                           $oi_trend = 'STABLE';
                }
            }

            $out[$name] = array(
                'open_interest'  => $oi,
                'oi_trend_7d'    => $oi_trend,
                'oi_change_7d'   => $oi_change_pct . '%',
                'signal' => ($oi_trend === 'SURGING') ? 'HIGH_LEVERAGE' : (($oi_trend === 'COLLAPSING') ? 'DELEVERAGING' : 'NORMAL')
            );
        } else {
            $out[$name] = array('error' => 'fetch_failed');
        }
    }
    return $out;
}

// ═══════════════════════════════════════════════════════════════════════
//  LONG/SHORT RATIO — from Binance Futures
// ═══════════════════════════════════════════════════════════════════════
function _fetch_all_ls()
{
    global $ASSETS;
    $out = array();
    foreach ($ASSETS as $name => $pair) {
        $url = 'https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=' . $pair['binance'] . '&period=1d&limit=5';
        $data = _curl_json($url);
        if ($data && is_array($data) && count($data) > 0) {
            $latest = $data[0];
            $ratio  = floatval($latest['longShortRatio']);

            $extreme = 'BALANCED';
            if ($ratio > 3.0)      $extreme = 'EXTREME_LONG';   // Very crowded longs
            elseif ($ratio > 2.0)  $extreme = 'LONGS_HEAVY';
            elseif ($ratio < 0.5)  $extreme = 'EXTREME_SHORT';  // Crowded shorts
            elseif ($ratio < 0.8)  $extreme = 'SHORTS_HEAVY';

            $out[$name] = array(
                'ratio'             => round($ratio, 3),
                'long_pct'          => round(floatval($latest['longAccount']) * 100, 1) . '%',
                'short_pct'         => round(floatval($latest['shortAccount']) * 100, 1) . '%',
                'positioning'       => $extreme,
                'contrarian_signal' => ($extreme === 'EXTREME_LONG') ? 'BEARISH' : (($extreme === 'EXTREME_SHORT') ? 'BULLISH' : 'NONE')
            );
        } else {
            $out[$name] = array('error' => 'fetch_failed');
        }
    }
    return $out;
}

// ═══════════════════════════════════════════════════════════════════════
//  SUPERTREND — Calculated from Binance daily klines
// ═══════════════════════════════════════════════════════════════════════
function _fetch_all_supertrend()
{
    global $ASSETS;
    $out = array();
    foreach ($ASSETS as $name => $pair) {
        // Fetch 100 daily candles
        $url = 'https://api.binance.com/api/v3/klines?symbol=' . $pair['binance'] . '&interval=1d&limit=100';
        $candles = _curl_json($url);
        if (!$candles || !is_array($candles) || count($candles) < 20) {
            $out[$name] = array('error' => 'insufficient_data');
            continue;
        }

        $highs  = array();
        $lows   = array();
        $closes = array();
        foreach ($candles as $c) {
            $highs[]  = floatval($c[2]);
            $lows[]   = floatval($c[3]);
            $closes[] = floatval($c[4]);
        }

        $st = _supertrend($highs, $lows, $closes, 10, 3.0);
        $n  = count($st['trend']);
        $current_trend = $st['trend'][$n - 1];
        $prev_trend    = ($n > 1) ? $st['trend'][$n - 2] : $current_trend;

        // Detect crossover (signal change)
        $crossover = ($current_trend !== $prev_trend) ? true : false;
        $signal    = ($current_trend === 1) ? 'BULLISH' : 'BEARISH';

        // Count consecutive bars in current direction
        $streak = 0;
        for ($i = $n - 1; $i >= 0; $i--) {
            if ($st['trend'][$i] === $current_trend) $streak++;
            else break;
        }

        $out[$name] = array(
            'signal'       => $signal,
            'supertrend'   => round($st['supertrend'][$n - 1], 2),
            'price'        => round($closes[$n - 1], 2),
            'crossover'    => $crossover,
            'streak_bars'  => $streak,
            'distance_pct' => round(abs(($closes[$n - 1] - $st['supertrend'][$n - 1]) / $closes[$n - 1]) * 100, 2) . '%'
        );
    }
    return $out;
}

// ═══════════════════════════════════════════════════════════════════════
//  Supertrend calculation (period=10, factor=3.0)
// ═══════════════════════════════════════════════════════════════════════
function _supertrend($highs, $lows, $closes, $period, $factor)
{
    $n = count($closes);

    // Calculate ATR
    $tr = array();
    $tr[0] = $highs[0] - $lows[0];
    for ($i = 1; $i < $n; $i++) {
        $hl = $highs[$i] - $lows[$i];
        $hc = abs($highs[$i] - $closes[$i - 1]);
        $lc = abs($lows[$i]  - $closes[$i - 1]);
        $tr[$i] = max($hl, $hc, $lc);
    }

    // ATR using SMA
    $atr = array();
    for ($i = 0; $i < $n; $i++) {
        if ($i < $period - 1) {
            $atr[$i] = 0;
        } else {
            $sum = 0;
            for ($j = $i - $period + 1; $j <= $i; $j++) { $sum += $tr[$j]; }
            $atr[$i] = $sum / $period;
        }
    }

    // Supertrend bands
    $upper = array();
    $lower = array();
    $st    = array();
    $trend = array(); // 1 = bullish, -1 = bearish

    for ($i = 0; $i < $n; $i++) {
        $mid = ($highs[$i] + $lows[$i]) / 2;
        $basic_upper = $mid + $factor * $atr[$i];
        $basic_lower = $mid - $factor * $atr[$i];

        if ($i === 0) {
            $upper[$i] = $basic_upper;
            $lower[$i] = $basic_lower;
            $trend[$i] = ($closes[$i] > $basic_upper) ? 1 : -1;
            $st[$i] = ($trend[$i] === 1) ? $lower[$i] : $upper[$i];
            continue;
        }

        // Upper band: only moves down
        $upper[$i] = ($basic_upper < $upper[$i - 1] || $closes[$i - 1] > $upper[$i - 1])
            ? $basic_upper
            : $upper[$i - 1];

        // Lower band: only moves up
        $lower[$i] = ($basic_lower > $lower[$i - 1] || $closes[$i - 1] < $lower[$i - 1])
            ? $basic_lower
            : $lower[$i - 1];

        // Determine trend
        if ($trend[$i - 1] === 1) {
            $trend[$i] = ($closes[$i] < $lower[$i]) ? -1 : 1;
        } else {
            $trend[$i] = ($closes[$i] > $upper[$i]) ? 1 : -1;
        }

        $st[$i] = ($trend[$i] === 1) ? $lower[$i] : $upper[$i];
    }

    return array('supertrend' => $st, 'trend' => $trend);
}

// ═══════════════════════════════════════════════════════════════════════
//  RISK SCORES — Combined risk assessment from all derivatives data
// ═══════════════════════════════════════════════════════════════════════
function _compute_risk_scores($data)
{
    global $ASSETS;
    $scores = array();
    foreach (array_keys($ASSETS) as $name) {
        $score    = 0;  // -100 (max bearish) to +100 (max bullish)
        $factors  = array();
        $warnings = array();

        // Funding rate factor (-30 to +30)
        if (isset($data['funding'][$name]) && !isset($data['funding'][$name]['error'])) {
            $f = $data['funding'][$name];
            if ($f['extreme'] === 'HIGH_POSITIVE') {
                $score -= 25;
                $factors[] = 'Funding HIGH_POS (contrarian bearish)';
                $warnings[] = 'Crowded longs — high liquidation risk';
            } elseif ($f['extreme'] === 'HIGH_NEGATIVE') {
                $score += 25;
                $factors[] = 'Funding HIGH_NEG (contrarian bullish)';
            } elseif ($f['extreme'] === 'POSITIVE') {
                $score -= 10;
                $factors[] = 'Funding slightly positive';
            } elseif ($f['extreme'] === 'NEGATIVE') {
                $score += 10;
                $factors[] = 'Funding slightly negative';
            }
        }

        // Open interest factor (-20 to +20)
        if (isset($data['open_interest'][$name]) && !isset($data['open_interest'][$name]['error'])) {
            $oi = $data['open_interest'][$name];
            if ($oi['signal'] === 'HIGH_LEVERAGE') {
                $score -= 15;
                $factors[] = 'OI surging — high leverage risk';
                $warnings[] = 'Excessive leverage building — potential cascade';
            } elseif ($oi['signal'] === 'DELEVERAGING') {
                $score += 10;
                $factors[] = 'OI declining — healthier market';
            }
        }

        // Long/Short ratio factor (-25 to +25)
        if (isset($data['long_short_ratio'][$name]) && !isset($data['long_short_ratio'][$name]['error'])) {
            $ls = $data['long_short_ratio'][$name];
            if ($ls['positioning'] === 'EXTREME_LONG') {
                $score -= 25;
                $factors[] = 'L/S ratio extreme long (contrarian bearish)';
                $warnings[] = 'Extreme long positioning — squeeze likely';
            } elseif ($ls['positioning'] === 'EXTREME_SHORT') {
                $score += 25;
                $factors[] = 'L/S ratio extreme short (contrarian bullish)';
            } elseif ($ls['positioning'] === 'LONGS_HEAVY') {
                $score -= 10;
                $factors[] = 'L/S ratio longs heavy';
            } elseif ($ls['positioning'] === 'SHORTS_HEAVY') {
                $score += 10;
                $factors[] = 'L/S ratio shorts heavy';
            }
        }

        // Supertrend factor (-25 to +25)
        if (isset($data['supertrend'][$name]) && !isset($data['supertrend'][$name]['error'])) {
            $st = $data['supertrend'][$name];
            if ($st['signal'] === 'BULLISH') {
                $score += 20;
                $factors[] = 'Supertrend BULLISH (' . $st['streak_bars'] . ' bars)';
                if ($st['crossover']) {
                    $score += 5;
                    $factors[] = 'Supertrend FRESH CROSSOVER (buy signal)';
                }
            } else {
                $score -= 20;
                $factors[] = 'Supertrend BEARISH (' . $st['streak_bars'] . ' bars)';
                if ($st['crossover']) {
                    $score -= 5;
                    $factors[] = 'Supertrend FRESH CROSSOVER (sell signal)';
                }
            }
        }

        // Clamp to -100..+100
        $score = max(-100, min(100, $score));

        // Overall assessment
        $assessment = 'NEUTRAL';
        if ($score >= 50)       $assessment = 'STRONG_BULLISH';
        elseif ($score >= 20)   $assessment = 'BULLISH';
        elseif ($score >= 5)    $assessment = 'LEAN_BULLISH';
        elseif ($score <= -50)  $assessment = 'STRONG_BEARISH';
        elseif ($score <= -20)  $assessment = 'BEARISH';
        elseif ($score <= -5)   $assessment = 'LEAN_BEARISH';

        $scores[$name] = array(
            'risk_score'  => $score,
            'assessment'  => $assessment,
            'factors'     => $factors,
            'warnings'    => $warnings
        );
    }
    return $scores;
}

// ═══════════════════════════════════════════════════════════════════════
//  cURL helper
// ═══════════════════════════════════════════════════════════════════════
function _curl_json($url)
{
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'DerivativesFeed/1.0');
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp) return null;
    return json_decode($resp, true);
}
?>