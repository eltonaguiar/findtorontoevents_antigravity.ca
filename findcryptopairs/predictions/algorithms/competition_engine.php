<?php
/**
 * Algorithm Competition Engine
 * Runs 10 competing algorithms + my KIMI-MTF algorithm
 * PHP 5.2 Compatible
 */

header('Content-Type: application/json');

// Fetch current prices
function getPrices() {
    $url = "https://api.coingecko.com/api/v3/simple/price?ids=popcat,pudgy-penguins,dogecoin,bitcoin&vs_currencies=usd&include_24hr_change=true";
    $response = @file_get_contents($url);
    if (!$response) return null;
    
    $data = json_decode($response, true);
    return array(
        'POPCAT' => array('price' => $data['popcat']['usd'], 'change_24h' => $data['popcat']['usd_24h_change']),
        'PENGU' => array('price' => $data['pudgy-penguins']['usd'], 'change_24h' => $data['pudgy-penguins']['usd_24h_change']),
        'DOGE' => array('price' => $data['dogecoin']['usd'], 'change_24h' => $data['dogecoin']['usd_24h_change']),
        'BTC' => array('price' => $data['bitcoin']['usd'], 'change_24h' => $data['bitcoin']['usd_24h_change'])
    );
}

// Fetch historical data
function getHistoricalData($symbol, $days = 90) {
    $idMap = array(
        'POPCAT' => 'popcat',
        'PENGU' => 'pudgy-penguins', 
        'DOGE' => 'dogecoin',
        'BTC' => 'bitcoin'
    );
    $id = isset($idMap[$symbol]) ? $idMap[$symbol] : strtolower($symbol);
    $url = "https://api.coingecko.com/api/v3/coins/$id/market_chart?vs_currency=usd&days=$days";
    $response = @file_get_contents($url);
    return $response ? json_decode($response, true) : null;
}

// Calculate RSI
function calculateRSI($prices, $period = 14) {
    if (count($prices) < $period + 1) return 50;
    $gains = 0; $losses = 0;
    for ($i = count($prices) - $period; $i < count($prices); $i++) {
        $change = $prices[$i] - $prices[$i - 1];
        if ($change > 0) $gains += $change;
        else $losses -= $change;
    }
    $avgGain = $gains / $period;
    $avgLoss = $losses / $period;
    if ($avgLoss == 0) return 100;
    $rs = $avgGain / $avgLoss;
    return 100 - (100 / (1 + $rs));
}

// Calculate EMA
function calculateEMA($prices, $period) {
    if (count($prices) < $period) return end($prices);
    $multiplier = 2 / ($period + 1);
    $ema = array_sum(array_slice($prices, 0, $period)) / $period;
    for ($i = $period; $i < count($prices); $i++) {
        $ema = ($prices[$i] - $ema) * $multiplier + $ema;
    }
    return $ema;
}

// Calculate MACD
function calculateMACD($prices) {
    $ema12 = calculateEMA($prices, 12);
    $ema26 = calculateEMA($prices, 26);
    $macd = $ema12 - $ema26;
    return array('macd' => $macd, 'histogram' => $macd * 0.1);
}

// Calculate VWAP
function calculateVWAP($prices, $volumes) {
    $tpv = 0; $cumVol = 0;
    for ($i = 0; $i < count($prices); $i++) {
        $tpv += $prices[$i] * $volumes[$i];
        $cumVol += $volumes[$i];
    }
    return $cumVol > 0 ? $tpv / $cumVol : end($prices);
}

// MY ALGORITHM: KIMI-MTF
function algoKIMI_MTF($symbol, $data, $currentPrice) {
    $prices = array();
    foreach ($data['prices'] as $p) $prices[] = $p[1];
    if (count($prices) < 24) return array('algorithm' => 'KIMI-MTF', 'signal' => 'NEUTRAL', 'confidence' => 'LOW');
    
    $momentum1h = ($prices[count($prices)-1] - $prices[count($prices)-2]) / $prices[count($prices)-2] * 100;
    $momentum4h = count($prices) > 4 ? ($prices[count($prices)-1] - $prices[count($prices)-5]) / $prices[count($prices)-5] * 100 : 0;
    $momentum24h = ($prices[count($prices)-1] - $prices[count($prices)-24]) / $prices[count($prices)-24] * 100;
    
    $score = 0;
    if ($momentum1h > 0 && $momentum4h > 0 && $momentum24h > 0) $score += 40;
    if ($momentum1h >= 1) $score += 30; elseif ($momentum1h >= 0.5) $score += 15;
    
    $rsi = calculateRSI($prices);
    if ($rsi >= 45 && $rsi <= 75) $score += 30;
    
    $signal = $score >= 70 ? 'BUY' : ($score <= 30 ? 'SELL' : 'NEUTRAL');
    return array('algorithm' => 'KIMI-MTF', 'signal' => $signal, 'confidence' => $score >= 70 ? 'HIGH' : 'MEDIUM', 'score' => $score);
}

// A1: Time-Series Momentum
function algoA1_TimeSeriesMomentum($symbol, $data, $currentPrice) {
    $prices = array(); foreach ($data['prices'] as $p) $prices[] = $p[1];
    $momentum7d = (count($prices) > 7) ? ($prices[count($prices)-1] - $prices[count($prices)-8]) / $prices[count($prices)-8] * 100 : 0;
    $momentum30d = (count($prices) > 30) ? ($prices[count($prices)-1] - $prices[count($prices)-31]) / $prices[count($prices)-31] * 100 : 0;
    $signal = ($momentum7d > 0 && $momentum30d > 0) ? 'BUY' : (($momentum7d < 0 && $momentum30d < 0) ? 'SELL' : 'NEUTRAL');
    return array('algorithm' => 'A1-TimeSeriesMomentum', 'signal' => $signal, 'confidence' => abs($momentum7d) > 5 ? 'HIGH' : 'MEDIUM');
}

// A2: Pairs Trading
function algoA2_PairsTrading($symbol, $data, $currentPrice, $btcData) {
    if ($symbol == 'BTC') return array('algorithm' => 'A2-PairsTrading', 'signal' => 'NEUTRAL', 'confidence' => 'LOW');
    $symbolPrices = array(); foreach ($data['prices'] as $p) $symbolPrices[] = $p[1];
    $btcPrices = array(); foreach ($btcData['prices'] as $p) $btcPrices[] = $p[1];
    if (count($symbolPrices) < 20 || count($btcPrices) < 20) return array('algorithm' => 'A2-PairsTrading', 'signal' => 'NEUTRAL', 'confidence' => 'LOW');
    
    $spreads = array(); $minLen = min(count($symbolPrices), count($btcPrices));
    for ($i = $minLen - 20; $i < $minLen; $i++) $spreads[] = $symbolPrices[$i] / $btcPrices[$i];
    $meanSpread = array_sum($spreads) / count($spreads);
    $currentSpread = end($symbolPrices) / end($btcPrices);
    $stdDev = 0; foreach ($spreads as $s) $stdDev += pow($s - $meanSpread, 2);
    $stdDev = sqrt($stdDev / count($spreads));
    $zScore = $stdDev > 0 ? ($currentSpread - $meanSpread) / $stdDev : 0;
    $signal = $zScore > 2 ? 'SELL' : ($zScore < -2 ? 'BUY' : 'NEUTRAL');
    return array('algorithm' => 'A2-PairsTrading', 'signal' => $signal, 'confidence' => abs($zScore) > 2.5 ? 'HIGH' : 'MEDIUM', 'zScore' => round($zScore, 2));
}

// A3: Simplified ML
function algoA3_SimplifiedML($symbol, $data, $currentPrice) {
    $prices = array(); foreach ($data['prices'] as $p) $prices[] = $p[1];
    if (count($prices) < 14) return array('algorithm' => 'A3-SimplifiedML', 'signal' => 'NEUTRAL', 'confidence' => 'LOW');
    $ma7 = array_sum(array_slice($prices, -7)) / 7;
    $ma14 = array_sum(array_slice($prices, -14)) / 14;
    $mom7 = count($prices) > 7 ? ($prices[count($prices)-1] - $prices[count($prices)-8]) / $prices[count($prices)-8] : 0;
    $score = 0; if ($currentPrice > $ma7) $score += 25; if ($currentPrice > $ma14) $score += 25; if ($mom7 > 0) $score += 50;
    $signal = $score >= 75 ? 'BUY' : ($score <= 25 ? 'SELL' : 'NEUTRAL');
    return array('algorithm' => 'A3-SimplifiedML', 'signal' => $signal, 'confidence' => $score >= 75 ? 'HIGH' : 'MEDIUM', 'score' => $score);
}

// A4: Opening Range Breakout
function algoA4_OpeningRangeBreakout($symbol, $currentPrice, $change24h) {
    $signal = abs($change24h) > 3 ? ($change24h > 0 ? 'BUY' : 'SELL') : 'NEUTRAL';
    return array('algorithm' => 'A4-OpeningRangeBreakout', 'signal' => $signal, 'confidence' => abs($change24h) > 5 ? 'HIGH' : 'MEDIUM');
}

// A5: VWAP
function algoA5_VWAP($symbol, $data, $currentPrice) {
    $prices = array(); $volumes = array();
    foreach ($data['prices'] as $p) $prices[] = $p[1];
    foreach ($data['total_volumes'] as $v) $volumes[] = $v[1];
    if (count($prices) < 20 || count($volumes) < 20) return array('algorithm' => 'A5-VWAP', 'signal' => 'NEUTRAL', 'confidence' => 'LOW');
    $vwap = calculateVWAP(array_slice($prices, -20), array_slice($volumes, -20));
    $deviation = (($currentPrice - $vwap) / $vwap) * 100;
    $signal = $deviation < -2 ? 'BUY' : ($deviation > 2 ? 'SELL' : 'NEUTRAL');
    return array('algorithm' => 'A5-VWAP', 'signal' => $signal, 'confidence' => abs($deviation) > 3 ? 'HIGH' : 'MEDIUM', 'deviation' => round($deviation, 2));
}

// S1: 5-Minute Macro
function algoS1_FiveMinuteMacro($symbol, $currentPrice, $change24h) {
    $signal = $change24h > 2 ? 'BUY' : ($change24h < -2 ? 'SELL' : 'NEUTRAL');
    return array('algorithm' => 'S1-5MinMacro', 'signal' => $signal, 'confidence' => abs($change24h) > 5 ? 'HIGH' : 'MEDIUM');
}

// S2: RSI+MACD Divergence
function algoS2_RSIMACD($symbol, $data, $currentPrice) {
    $prices = array(); foreach ($data['prices'] as $p) $prices[] = $p[1];
    if (count($prices) < 26) return array('algorithm' => 'S2-RSIMACD', 'signal' => 'NEUTRAL', 'confidence' => 'LOW');
    $rsi = calculateRSI($prices);
    $macd = calculateMACD($prices);
    $signal = ($rsi < 35 && $macd['histogram'] > 0) ? 'BUY' : (($rsi > 65 && $macd['histogram'] < 0) ? 'SELL' : 'NEUTRAL');
    return array('algorithm' => 'S2-RSIMACD', 'signal' => $signal, 'confidence' => ($rsi < 30 || $rsi > 70) ? 'HIGH' : 'MEDIUM', 'rsi' => round($rsi, 1));
}

// S3: Whale Shadow
function algoS3_WhaleShadow($symbol, $currentPrice, $change24h) {
    $signal = abs($change24h) > 8 ? ($change24h > 0 ? 'BUY' : 'SELL') : 'NEUTRAL';
    return array('algorithm' => 'S3-WhaleShadow', 'signal' => $signal, 'confidence' => abs($change24h) > 15 ? 'HIGH' : 'MEDIUM');
}

// S4: Narrative Velocity
function algoS4_NarrativeVelocity($symbol, $currentPrice, $change24h) {
    $signal = $change24h > 5 ? 'BUY' : ($change24h < -5 ? 'SELL' : 'NEUTRAL');
    return array('algorithm' => 'S4-NarrativeVelocity', 'signal' => $signal, 'confidence' => abs($change24h) > 10 ? 'HIGH' : 'MEDIUM');
}

// S5: Portfolio Spray
function algoS5_PortfolioSpray($symbol, $currentPrice, $change24h) {
    $signal = $change24h < -20 ? 'BUY' : 'NEUTRAL';
    return array('algorithm' => 'S5-PortfolioSpray', 'signal' => $signal, 'confidence' => $change24h < -30 ? 'HIGH' : 'MEDIUM');
}

// MAIN EXECUTION
$prices = getPrices();
if (!$prices) { echo json_encode(array('error' => 'Failed to fetch prices')); exit; }

$btcData = getHistoricalData('BTC', 90);
$results = array('timestamp' => date('c'), 'competition_round' => 1, 'predictions' => array());
$symbols = array('POPCAT', 'PENGU', 'DOGE', 'BTC');

foreach ($symbols as $symbol) {
    $currentPrice = $prices[$symbol]['price'];
    $change24h = $prices[$symbol]['change_24h'];
    $data = getHistoricalData($symbol, 90);
    if (!$data) continue;
    
    $symbolPredictions = array('symbol' => $symbol, 'current_price' => $currentPrice, 'change_24h' => round($change24h, 2), 'algorithms' => array());
    $symbolPredictions['algorithms'][] = algoKIMI_MTF($symbol, $data, $currentPrice);
    $symbolPredictions['algorithms'][] = algoA1_TimeSeriesMomentum($symbol, $data, $currentPrice);
    $symbolPredictions['algorithms'][] = algoA2_PairsTrading($symbol, $data, $currentPrice, $btcData);
    $symbolPredictions['algorithms'][] = algoA3_SimplifiedML($symbol, $data, $currentPrice);
    $symbolPredictions['algorithms'][] = algoA4_OpeningRangeBreakout($symbol, $currentPrice, $change24h);
    $symbolPredictions['algorithms'][] = algoA5_VWAP($symbol, $data, $currentPrice);
    $symbolPredictions['algorithms'][] = algoS1_FiveMinuteMacro($symbol, $currentPrice, $change24h);
    $symbolPredictions['algorithms'][] = algoS2_RSIMACD($symbol, $data, $currentPrice);
    $symbolPredictions['algorithms'][] = algoS3_WhaleShadow($symbol, $currentPrice, $change24h);
    $symbolPredictions['algorithms'][] = algoS4_NarrativeVelocity($symbol, $currentPrice, $change24h);
    $symbolPredictions['algorithms'][] = algoS5_PortfolioSpray($symbol, $currentPrice, $change24h);
    
    $results['predictions'][] = $symbolPredictions;
}

echo json_encode($results, JSON_PRETTY_PRINT);
