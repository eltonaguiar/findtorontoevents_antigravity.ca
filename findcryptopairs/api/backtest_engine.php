<?php
/**
 * Meme Coin Strategy Backtest Engine v1.0
 * Comprehensive backtesting with optimization and analytics
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

error_reporting(E_ALL);
ini_set('display_errors', '1');

$CACHE_DIR = dirname(__FILE__) . '/../../tmp/backtest';
if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

$action = isset($_GET['action']) ? $_GET['action'] : 'run';

switch ($action) {
    case 'run':
        runBacktest();
        break;
    case 'optimize':
        runOptimization();
        break;
    case 'analyze':
        analyzeStrategy();
        break;
    case 'compare':
        compareStrategies();
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

/**
 * Main backtest function
 */
function runBacktest() {
    $symbol = isset($_GET['symbol']) ? strtoupper($_GET['symbol']) : 'DOGE';
    $startDate = isset($_GET['start']) ? $_GET['start'] : date('Y-m-d', strtotime('-6 months'));
    $endDate = isset($_GET['end']) ? $_GET['end'] : date('Y-m-d');
    
    // Strategy parameters
    $params = array(
        'min1hChange' => isset($_GET['min1h']) ? floatval($_GET['min1h']) : 1.5,
        'min4hChange' => isset($_GET['min4h']) ? floatval($_GET['min4h']) : 2.5,
        'compositeThreshold' => isset($_GET['threshold']) ? intval($_GET['threshold']) : 65,
        'rsiOverbought' => isset($_GET['rsiHigh']) ? intval($_GET['rsiHigh']) : 75,
        'rsiMin' => isset($_GET['rsiLow']) ? intval($_GET['rsiLow']) : 35,
        'stopLossPct' => isset($_GET['sl']) ? floatval($_GET['sl']) : 3.5,
        'takeProfitPct' => isset($_GET['tp']) ? floatval($_GET['tp']) : 20.0,
        'trailingStopPct' => isset($_GET['trail']) ? floatval($_GET['trail']) : 12.0,
        'minVolumeUSD' => isset($_GET['minVol']) ? floatval($_GET['minVol']) : 500000,
        'tradeCooldown' => isset($_GET['cooldown']) ? intval($_GET['cooldown']) : 3,
        'requireAllTfPositive' => isset($_GET['allTf']) ? boolval($_GET['allTf']) : false
    );
    
    // Load historical data
    $ohlcvData = loadHistoricalData($symbol, $startDate, $endDate);
    
    if (empty($ohlcvData)) {
        echo json_encode(array('ok' => false, 'error' => 'No historical data available'));
        return;
    }
    
    // Run backtest simulation
    $results = simulateStrategy($ohlcvData, $params);
    
    // Calculate metrics
    $metrics = calculateMetrics($results['trades'], $results['equityCurve']);
    
    echo json_encode(array(
        'ok' => true,
        'symbol' => $symbol,
        'period' => array('start' => $startDate, 'end' => $endDate),
        'params' => $params,
        'metrics' => $metrics,
        'trades' => array_slice($results['trades'], -50), // Last 50 trades
        'equityCurve' => $results['equityCurve'],
        'signals' => $results['signals']
    ));
}

/**
 * Load historical OHLCV data (simulated - would fetch from Kraken API)
 */
function loadHistoricalData($symbol, $startDate, $endDate) {
    $cacheFile = $GLOBALS['CACHE_DIR'] . '/ohlcv_' . strtolower($symbol) . '_' . $startDate . '_' . $endDate . '.json';
    
    if (file_exists($cacheFile)) {
        $cached = json_decode(file_get_contents($cacheFile), true);
        if ($cached) return $cached;
    }
    
    // Generate realistic OHLCV data for testing
    // In production, this would fetch from Kraken API or database
    $data = generateSimulatedData($symbol, $startDate, $endDate);
    
    @file_put_contents($cacheFile, json_encode($data));
    return $data;
}

/**
 * Generate realistic simulated price data
 */
function generateSimulatedData($symbol, $startDate, $endDate) {
    $data = array();
    $current = strtotime($startDate);
    $end = strtotime($endDate);
    
    // Base price and volatility by symbol
    $basePrice = array(
        'DOGE' => 0.10, 'SHIB' => 0.00001, 'PEPE' => 0.000001,
        'BTC' => 45000, 'ETH' => 2800, 'SOL' => 120
    );
    $volatility = array(
        'DOGE' => 0.03, 'SHIB' => 0.05, 'PEPE' => 0.08,
        'BTC' => 0.015, 'ETH' => 0.02, 'SOL' => 0.03
    );
    
    $price = isset($basePrice[$symbol]) ? $basePrice[$symbol] : 0.10;
    $vol = isset($volatility[$symbol]) ? $volatility[$symbol] : 0.03;
    
    $trend = 0;
    $trendDuration = 0;
    
    while ($current <= $end) {
        // Generate trend changes
        if ($trendDuration <= 0) {
            $trend = (rand(-100, 100) / 100) * 0.01; // -1% to +1% bias
            $trendDuration = rand(24, 168); // 1-7 days in hours
        }
        $trendDuration--;
        
        // Random walk with trend
        $change = (rand(-100, 100) / 100) * $vol + $trend;
        $open = $price;
        $close = $price * (1 + $change);
        $high = max($open, $close) * (1 + (rand(0, 50) / 10000)); // 0-0.5% wick
        $low = min($open, $close) * (1 - (rand(0, 50) / 10000));
        $volume = rand(1000000, 10000000) * $price;
        
        $data[] = array(
            'timestamp' => $current,
            'datetime' => date('Y-m-d H:i:s', $current),
            'open' => $open,
            'high' => $high,
            'low' => $low,
            'close' => $close,
            'volume' => $volume
        );
        
        $price = $close;
        $current += 3600; // 1 hour intervals
    }
    
    return $data;
}

/**
 * Simulate strategy on historical data
 */
function simulateStrategy($data, $params) {
    $trades = array();
    $equityCurve = array();
    $signals = array();
    
    $initialCapital = 10000;
    $capital = $initialCapital;
    $position = null;
    $cooldown = 0;
    
    $lookback4h = 4;
    $lookback24h = 24;
    
    for ($i = $lookback24h; $i < count($data); $i++) {
        $current = $data[$i];
        
        // Calculate multi-timeframe data
        $change1h = (($current['close'] - $data[$i-1]['close']) / $data[$i-1]['close']) * 100;
        $change4h = (($current['close'] - $data[$i-$lookback4h]['close']) / $data[$i-$lookback4h]['close']) * 100;
        $change24h = (($current['close'] - $data[$i-$lookback24h]['close']) / $data[$i-$lookback24h]['close']) * 100;
        
        // Calculate RSI (simplified 14-period)
        $rsi = calculateRSI(array_slice($data, $i-14, 15));
        
        // Calculate EMA
        $ema12 = calculateEMA(array_slice($data, $i-12, 13), 12);
        $ema26 = calculateEMA(array_slice($data, $i-26, 27), 26);
        $trendBullish = $ema12 > $ema26;
        
        // Volume analysis
        $avgVolume = 0;
        for ($j = $i-20; $j < $i; $j++) {
            $avgVolume += $data[$j]['volume'];
        }
        $avgVolume /= 20;
        $volumeSpike = $current['volume'] > ($avgVolume * 1.3);
        $volume24h = $avgVolume * 24;
        
        // Calculate composite score
        $score1h = $change1h >= $params['min1hChange'] ? 25 : ($change1h > 0 ? ($change1h / $params['min1hChange']) * 20 : 0);
        $score4h = $change4h >= $params['min4hChange'] ? 25 : ($change4h > 0 ? ($change4h / $params['min4hChange']) * 20 : 0);
        $scoreDaily = $change24h > 0 ? 25 : max(0, 15 + ($change24h / 2));
        $rsiScore = ($rsi >= $params['rsiMin'] && $rsi <= 60) ? 25 : (($rsi > 60 && $rsi <= $params['rsiOverbought']) ? 20 : (($rsi > $params['rsiOverbought']) ? 5 : 10));
        $volumeScore = ($volumeSpike && $volume24h > $params['minVolumeUSD']) ? 15 : (($volume24h > $params['minVolumeUSD']) ? 10 : 0);
        $trendBonus = $trendBullish ? 10 : 0;
        
        $compositeScore = $score1h + $score4h + $scoreDaily + $rsiScore + $volumeScore + $trendBonus;
        
        // Pattern detection
        $allTfPositive = $change1h > 0 && $change4h > 0 && $change24h > 0;
        $breakoutPattern = $change1h > $params['min1hChange'] && $change4h > 0 && $change24h > -2;
        $continuationPattern = $change1h > 0.5 && $change4h > 2 && $change24h > 5;
        $earlyMomentum = $change1h > $params['min1hChange'] * 1.3 && $change4h < $params['min4hChange'] && $change24h > -3;
        $dipRecovery = $change1h > 1 && $change4h < 0 && $change4h > -5 && $change24h > 3;
        
        $hasValidPattern = $breakoutPattern || $continuationPattern || $earlyMomentum || $dipRecovery;
        
        // Risk filters
        $parabolicWarning = $change24h > 100 || ($change4h > 50 && $change1h < 1);
        $lowVolumeWarning = $volume24h < ($params['minVolumeUSD'] * 0.5);
        $chasingWarning = $change24h > 30 && $change1h < 2;
        
        // Update cooldown
        if ($cooldown > 0) $cooldown--;
        
        // Check for exit if in position
        if ($position) {
            $currentPnL = (($current['close'] - $position['entryPrice']) / $position['entryPrice']) * 100;
            
            // Stop loss
            if ($currentPnL <= -$params['stopLossPct']) {
                $trades[] = closeTrade($position, $current, 'STOP_LOSS', $capital);
                $capital = $trades[count($trades)-1]['exitValue'];
                $position = null;
                $cooldown = $params['tradeCooldown'];
                continue;
            }
            
            // Take profit
            if ($currentPnL >= $params['takeProfitPct']) {
                $trades[] = closeTrade($position, $current, 'TAKE_PROFIT', $capital);
                $capital = $trades[count($trades)-1]['exitValue'];
                $position = null;
                $cooldown = $params['tradeCooldown'];
                continue;
            }
            
            // Trailing stop
            $maxProfit = (($position['maxPrice'] - $position['entryPrice']) / $position['entryPrice']) * 100;
            if ($maxProfit > $params['trailingStopPct'] && $currentPnL <= ($maxProfit - $params['trailingStopPct'])) {
                $trades[] = closeTrade($position, $current, 'TRAILING_STOP', $capital);
                $capital = $trades[count($trades)-1]['exitValue'];
                $position = null;
                $cooldown = $params['tradeCooldown'];
                continue;
            }
            
            // Momentum reversal
            if ($change1h < -2 && $change4h < 0) {
                $trades[] = closeTrade($position, $current, 'MOMENTUM_REVERSAL', $capital);
                $capital = $trades[count($trades)-1]['exitValue'];
                $position = null;
                $cooldown = $params['tradeCooldown'];
                continue;
            }
            
            // Update max price for trailing stop
            if ($current['high'] > $position['maxPrice']) {
                $position['maxPrice'] = $current['high'];
            }
        }
        
        // Check for entry
        if (!$position && $cooldown == 0) {
            $entryCondition = $compositeScore >= $params['compositeThreshold'];
            $entryCondition = $entryCondition && !$parabolicWarning;
            $entryCondition = $entryCondition && !$lowVolumeWarning;
            $entryCondition = $entryCondition && !$chasingWarning;
            $entryCondition = $entryCondition && $trendBullish;
            $entryCondition = $entryCondition && $rsi >= $params['rsiMin'];
            $entryCondition = $entryCondition && $rsi <= $params['rsiOverbought'];
            $entryCondition = $entryCondition && $volume24h >= $params['minVolumeUSD'];
            $entryCondition = $entryCondition && $hasValidPattern;
            
            if ($params['requireAllTfPositive']) {
                $entryCondition = $entryCondition && $allTfPositive;
            }
            
            if ($entryCondition) {
                $position = array(
                    'entryTime' => $current['datetime'],
                    'entryPrice' => $current['close'],
                    'entryComposite' => $compositeScore,
                    'pattern' => $breakoutPattern ? 'BREAKOUT' : ($continuationPattern ? 'CONTINUATION' : ($earlyMomentum ? 'EARLY' : 'DIP')),
                    'maxPrice' => $current['high'],
                    'size' => $capital * 0.1 // 10% position size
                );
                
                $signals[] = array(
                    'time' => $current['datetime'],
                    'price' => $current['close'],
                    'type' => 'BUY',
                    'score' => $compositeScore,
                    'pattern' => $position['pattern']
                );
            }
        }
        
        // Record equity
        $equityValue = $capital;
        if ($position) {
            $unrealized = (($current['close'] - $position['entryPrice']) / $position['entryPrice']) * $position['size'];
            $equityValue += $unrealized;
        }
        
        if ($i % 24 == 0) { // Daily equity points
            $equityCurve[] = array(
                'date' => $current['datetime'],
                'equity' => $equityValue
            );
        }
    }
    
    // Close any open position
    if ($position) {
        $lastCandle = $data[count($data) - 1];
        $trades[] = closeTrade($position, $lastCandle, 'END_OF_TEST', $capital);
    }
    
    return array(
        'trades' => $trades,
        'equityCurve' => $equityCurve,
        'signals' => $signals
    );
}

/**
 * Close a trade and calculate results
 */
function closeTrade($position, $exitCandle, $reason, $capital) {
    $pnlPct = (($exitCandle['close'] - $position['entryPrice']) / $position['entryPrice']) * 100;
    $pnlAmount = $position['size'] * ($pnlPct / 100);
    $exitValue = $capital + $pnlAmount;
    
    return array(
        'entryTime' => $position['entryTime'],
        'exitTime' => $exitCandle['datetime'],
        'entryPrice' => $position['entryPrice'],
        'exitPrice' => $exitCandle['close'],
        'pattern' => $position['pattern'],
        'compositeScore' => $position['entryComposite'],
        'exitReason' => $reason,
        'pnlPct' => round($pnlPct, 2),
        'pnlAmount' => round($pnlAmount, 2),
        'exitValue' => round($exitValue, 2)
    );
}

/**
 * Calculate RSI
 */
function calculateRSI($data) {
    $gains = 0;
    $losses = 0;
    
    for ($i = 1; $i < count($data); $i++) {
        $change = $data[$i]['close'] - $data[$i-1]['close'];
        if ($change > 0) {
            $gains += $change;
        } else {
            $losses += abs($change);
        }
    }
    
    $avgGain = $gains / 14;
    $avgLoss = $losses / 14;
    
    if ($avgLoss == 0) return 100;
    
    $rs = $avgGain / $avgLoss;
    $rsi = 100 - (100 / (1 + $rs));
    
    return $rsi;
}

/**
 * Calculate EMA
 */
function calculateEMA($data, $period) {
    $multiplier = 2 / ($period + 1);
    $ema = $data[0]['close'];
    
    for ($i = 1; $i < count($data); $i++) {
        $ema = ($data[$i]['close'] - $ema) * $multiplier + $ema;
    }
    
    return $ema;
}

/**
 * Calculate strategy metrics
 */
function calculateMetrics($trades, $equityCurve) {
    if (empty($trades)) {
        return array(
            'totalTrades' => 0,
            'winRate' => 0,
            'profitFactor' => 0,
            'totalReturn' => 0,
            'maxDrawdown' => 0,
            'sharpeRatio' => 0
        );
    }
    
    $wins = 0;
    $losses = 0;
    $totalProfit = 0;
    $totalLoss = 0;
    $winningTrades = 0;
    $losingTrades = 0;
    
    foreach ($trades as $trade) {
        if ($trade['pnlAmount'] > 0) {
            $wins += $trade['pnlAmount'];
            $winningTrades++;
        } else {
            $losses += abs($trade['pnlAmount']);
            $losingTrades++;
        }
    }
    
    // Calculate max drawdown
    $maxDrawdown = 0;
    $peak = $equityCurve[0]['equity'];
    
    foreach ($equityCurve as $point) {
        if ($point['equity'] > $peak) {
            $peak = $point['equity'];
        }
        $drawdown = ($peak - $point['equity']) / $peak;
        if ($drawdown > $maxDrawdown) {
            $maxDrawdown = $drawdown;
        }
    }
    
    // Calculate Sharpe ratio (simplified)
    $returns = array();
    for ($i = 1; $i < count($equityCurve); $i++) {
        $returns[] = ($equityCurve[$i]['equity'] - $equityCurve[$i-1]['equity']) / $equityCurve[$i-1]['equity'];
    }
    
    $avgReturn = array_sum($returns) / count($returns);
    $stdDev = 0;
    foreach ($returns as $ret) {
        $stdDev += pow($ret - $avgReturn, 2);
    }
    $stdDev = sqrt($stdDev / count($returns));
    
    $sharpeRatio = $stdDev > 0 ? ($avgReturn / $stdDev) * sqrt(365) : 0; // Annualized
    
    $firstEquity = $equityCurve[0]['equity'];
    $lastEquity = $equityCurve[count($equityCurve) - 1]['equity'];
    $totalReturn = (($lastEquity - $firstEquity) / $firstEquity) * 100;
    
    return array(
        'totalTrades' => count($trades),
        'winningTrades' => $winningTrades,
        'losingTrades' => $losingTrades,
        'winRate' => round(($winningTrades / count($trades)) * 100, 2),
        'profitFactor' => $losses > 0 ? round($wins / $losses, 3) : ($wins > 0 ? 999 : 0),
        'totalReturn' => round($totalReturn, 2),
        'totalProfit' => round($wins, 2),
        'totalLoss' => round($losses, 2),
        'maxDrawdown' => round($maxDrawdown * 100, 2),
        'sharpeRatio' => round($sharpeRatio, 2),
        'avgWin' => $winningTrades > 0 ? round($wins / $winningTrades, 2) : 0,
        'avgLoss' => $losingTrades > 0 ? round($losses / $losingTrades, 2) : 0
    );
}

/**
 * Run parameter optimization
 */
function runOptimization() {
    $symbol = isset($_GET['symbol']) ? strtoupper($_GET['symbol']) : 'DOGE';
    
    // Parameter ranges to test
    $paramRanges = array(
        'min1hChange' => array(1.0, 1.5, 2.0, 2.5),
        'min4hChange' => array(2.0, 3.0, 4.0, 5.0),
        'compositeThreshold' => array(60, 65, 70, 75),
        'stopLossPct' => array(3.0, 3.5, 4.0),
        'takeProfitPct' => array(15.0, 20.0, 25.0)
    );
    
    $results = array();
    $bestResult = null;
    $bestScore = -999;
    
    foreach ($paramRanges['min1hChange'] as $min1h) {
        foreach ($paramRanges['min4hChange'] as $min4h) {
            foreach ($paramRanges['compositeThreshold'] as $threshold) {
                foreach ($paramRanges['stopLossPct'] as $sl) {
                    foreach ($paramRanges['takeProfitPct'] as $tp) {
                        $params = array(
                            'min1hChange' => $min1h,
                            'min4hChange' => $min4h,
                            'compositeThreshold' => $threshold,
                            'stopLossPct' => $sl,
                            'takeProfitPct' => $tp,
                            'rsiOverbought' => 75,
                            'rsiMin' => 35,
                            'trailingStopPct' => 10.0,
                            'minVolumeUSD' => 500000,
                            'tradeCooldown' => 3,
                            'requireAllTfPositive' => false
                        );
                        
                        $ohlcvData = loadHistoricalData($symbol, date('Y-m-d', strtotime('-3 months')), date('Y-m-d'));
                        $simResults = simulateStrategy($ohlcvData, $params);
                        $metrics = calculateMetrics($simResults['trades'], $simResults['equityCurve']);
                        
                        if ($metrics['totalTrades'] >= 10) {
                            $score = ($metrics['winRate'] * 0.3) + ($metrics['profitFactor'] * 20) + ($metrics['totalReturn'] * 0.5) - ($metrics['maxDrawdown'] * 2);
                            
                            $result = array(
                                'params' => $params,
                                'metrics' => $metrics,
                                'score' => round($score, 2)
                            );
                            
                            $results[] = $result;
                            
                            if ($score > $bestScore) {
                                $bestScore = $score;
                                $bestResult = $result;
                            }
                        }
                    }
                }
            }
        }
    }
    
    // Sort by score
    usort($results, function($a, $b) {
        return $b['score'] - $a['score'];
    });
    
    echo json_encode(array(
        'ok' => true,
        'symbol' => $symbol,
        'totalTested' => count($results),
        'bestResult' => $bestResult,
        'topResults' => array_slice($results, 0, 10)
    ));
}

/**
 * Analyze strategy performance
 */
function analyzeStrategy() {
    // Compare different strategies
    echo json_encode(array('ok' => true, 'message' => 'Analysis feature coming soon'));
}

/**
 * Compare multiple strategies
 */
function compareStrategies() {
    echo json_encode(array('ok' => true, 'message' => 'Comparison feature coming soon'));
}
