<?php
/**
 * Rapid Signal Engine (RSE)
 * High-frequency signal generator for rapid strategy validation
 * PHP 5.2+ Compatible
 * 
 * Generates 100+ signals per hour across 50+ micro-strategies
 * Resolves within hours for rapid feedback
 */

header('Content-Type: application/json');
header('Cache-Control: no-cache');

// Configuration
define('DATA_DIR', __DIR__ . '/../data/');
define('STRATEGIES_FILE', __DIR__ . '/../strategies/micro_strategies.json');
define('MAX_ACTIVE_SIGNALS', 200);
define('SIGNAL_VALIDITY_MINUTES', 60);

// Kraken API pairs
$kraken_pairs = array(
    'BTC' => 'XBTUSD', 'ETH' => 'ETHUSD', 'SOL' => 'SOLUSD', 'XRP' => 'XRPUSD',
    'DOGE' => 'DOGEUSD', 'ADA' => 'ADAUSD', 'AVAX' => 'AVAXUSD', 'LINK' => 'LINKUSD',
    'DOT' => 'DOTUSD', 'MATIC' => 'MATICUSD', 'SHIB' => 'SHIBUSD',
    'PEPE' => 'PEPEUSD', 'FLOKI' => 'FLOKIUSD', 'BONK' => 'BONKUSD',
    'WIF' => 'WIFUSD', 'PENGU' => 'PENGUUSD', 'POPCAT' => 'POPCATUSD',
    'TRUMP' => 'TRUMPUSD', 'INJ' => 'INJUSD', 'RENDER' => 'RENDERUSD'
);

// Action handling
$action = isset($_GET['action']) ? $_GET['action'] : 'generate';

switch ($action) {
    case 'generate':
        generateSignals();
        break;
    case 'scan':
        scanMarkets();
        break;
    case 'stats':
        getEngineStats();
        break;
    case 'leaderboard':
        getStrategyLeaderboard();
        break;
    default:
        echo json_encode(array('error' => 'Unknown action'));
}

/**
 * Generate signals based on all active strategies
 */
function generateSignals() {
    global $kraken_pairs;
    
    $strategies = loadStrategies();
    $active_signals = loadActiveSignals();
    $new_signals = array();
    $timestamp = date('Y-m-d H:i:s');
    
    // Get market data for all pairs
    $market_data = fetchKrakenPrices(array_values($kraken_pairs));
    
    foreach ($strategies['strategies'] as $strategy) {
        // Determine which assets to scan
        $assets_to_scan = isset($strategy['assets_only']) 
            ? $strategy['assets_only'] 
            : $strategies['assets'];
        
        foreach ($assets_to_scan as $asset) {
            if (!isset($kraken_pairs[$asset])) continue;
            
            $pair = $kraken_pairs[$asset];
            
            // Skip if already have active signal for this strategy+asset
            if (hasActiveSignal($active_signals, $strategy['id'], $asset)) {
                continue;
            }
            
            // Check if strategy triggers
            $signal = checkStrategyTrigger($strategy, $asset, $pair, $market_data, $timestamp);
            
            if ($signal) {
                $new_signals[] = $signal;
                $active_signals[] = $signal;
                
                // Limit total active signals
                if (count($active_signals) >= MAX_ACTIVE_SIGNALS) {
                    break 2;
                }
            }
        }
    }
    
    // Save signals
    saveActiveSignals($active_signals);
    
    // Log generation
    logSignalGeneration(count($new_signals), $timestamp);
    
    echo json_encode(array(
        'ok' => true,
        'generated' => count($new_signals),
        'total_active' => count($active_signals),
        'new_signals' => $new_signals,
        'timestamp' => $timestamp
    ));
}

/**
 * Check if strategy triggers a signal
 */
function checkStrategyTrigger($strategy, $asset, $pair, $market_data, $timestamp) {
    // Get price data
    $price_data = isset($market_data[$pair]) ? $market_data[$pair] : null;
    if (!$price_data) return null;
    
    $current_price = $price_data['price'];
    
    // Get indicator data (simulated - in production fetch from your indicator API)
    $indicators = fetchIndicators($pair, $strategy['timeframe']);
    
    // Check entry rules (simplified - expand based on your indicator system)
    $triggered = evaluateEntryRules($strategy['entry_rules'], $indicators, $price_data);
    
    if (!$triggered) return null;
    
    // Create signal
    $signal_id = 'RSVE-' . uniqid();
    
    // Calculate TP/SL based on strategy
    $tp_pct = extractTpPct($strategy['exit_rules']);
    $sl_pct = extractSlPct($strategy['exit_rules']);
    
    $target_price = $current_price * (1 + ($tp_pct / 100));
    $stop_price = $current_price * (1 - ($sl_pct / 100));
    
    return array(
        'id' => $signal_id,
        'strategy_id' => $strategy['id'],
        'strategy_name' => $strategy['name'],
        'category' => $strategy['category'],
        'asset' => $asset,
        'pair' => $pair,
        'entry_price' => $current_price,
        'target_price' => $target_price,
        'stop_price' => $stop_price,
        'tp_pct' => $tp_pct,
        'sl_pct' => $sl_pct,
        'timeframe' => $strategy['timeframe'],
        'max_hold_minutes' => timeframeToMinutes($strategy['max_hold']),
        'signal_time' => $timestamp,
        'expires_at' => date('Y-m-d H:i:s', strtotime($timestamp . ' + ' . SIGNAL_VALIDITY_MINUTES . ' minutes')),
        'status' => 'ACTIVE',
        'outcome' => null,
        'pnl_pct' => null,
        'resolved_at' => null,
        'indicators_at_entry' => $indicators
    );
}

/**
 * Scan markets and resolve completed signals
 */
function scanMarkets() {
    global $kraken_pairs;
    
    $active_signals = loadActiveSignals();
    $resolved_count = 0;
    $wins = 0;
    $losses = 0;
    $expired = 0;
    
    $current_time = time();
    $market_data = fetchKrakenPrices(array_values($kraken_pairs));
    
    foreach ($active_signals as $key => $signal) {
        if ($signal['status'] !== 'ACTIVE') continue;
        
        $pair = $signal['pair'];
        $current_price = isset($market_data[$pair]) ? $market_data[$pair]['price'] : null;
        
        if (!$current_price) continue;
        
        $entry = $signal['entry_price'];
        $target = $signal['target_price'];
        $stop = $signal['stop_price'];
        $pnl_pct = (($current_price - $entry) / $entry) * 100;
        
        $outcome = null;
        $resolved = false;
        
        // Check TP hit
        if ($current_price >= $target) {
            $outcome = 'WIN';
            $resolved = true;
            $wins++;
        }
        // Check SL hit
        elseif ($current_price <= $stop) {
            $outcome = 'LOSS';
            $resolved = true;
            $losses++;
        }
        // Check max hold time
        elseif ($current_time > strtotime($signal['signal_time'] . ' + ' . $signal['max_hold_minutes'] . ' minutes')) {
            // Check if profitable or not
            if ($pnl_pct > 0) {
                $outcome = 'WIN';
                $wins++;
            } else {
                $outcome = 'LOSS';
                $losses++;
            }
            $resolved = true;
        }
        // Check expiry
        elseif ($current_time > strtotime($signal['expires_at'])) {
            $outcome = 'EXPIRED';
            $expired++;
            $resolved = true;
        }
        
        if ($resolved) {
            $active_signals[$key]['status'] = $outcome;
            $active_signals[$key]['outcome'] = $outcome;
            $active_signals[$key]['pnl_pct'] = round($pnl_pct, 4);
            $active_signals[$key]['resolved_price'] = $current_price;
            $active_signals[$key]['resolved_at'] = date('Y-m-d H:i:s');
            $resolved_count++;
            
            // Save to outcomes log
            logOutcome($active_signals[$key]);
        }
    }
    
    saveActiveSignals($active_signals);
    
    // Update strategy performance
    updateStrategyPerformance();
    
    echo json_encode(array(
        'ok' => true,
        'resolved' => $resolved_count,
        'wins' => $wins,
        'losses' => $losses,
        'expired' => $expired,
        'remaining_active' => count(array_filter($active_signals, function($s) { return $s['status'] === 'ACTIVE'; })),
        'timestamp' => date('Y-m-d H:i:s')
    ));
}

/**
 * Get engine statistics
 */
function getEngineStats() {
    $signals = loadActiveSignals();
    $outcomes = loadOutcomes();
    
    $total = count($outcomes);
    $wins = count(array_filter($outcomes, function($o) { return $o['outcome'] === 'WIN'; }));
    $losses = count(array_filter($outcomes, function($o) { return $o['outcome'] === 'LOSS'; }));
    $active = count(array_filter($signals, function($s) { return $s['status'] === 'ACTIVE'; }));
    
    $win_rate = $total > 0 ? round(($wins / $total) * 100, 2) : 0;
    
    // Calculate avg P&L
    $total_pnl = 0;
    foreach ($outcomes as $o) {
        $total_pnl += $o['pnl_pct'];
    }
    $avg_pnl = $total > 0 ? round($total_pnl / $total, 4) : 0;
    
    // Signals per hour
    $signals_last_hour = count(array_filter($outcomes, function($o) {
        return strtotime($o['resolved_at']) > strtotime('-1 hour');
    }));
    
    echo json_encode(array(
        'ok' => true,
        'total_signals' => $total,
        'wins' => $wins,
        'losses' => $losses,
        'win_rate' => $win_rate,
        'avg_pnl_pct' => $avg_pnl,
        'active_signals' => $active,
        'signals_last_hour' => $signals_last_hour,
        'timestamp' => date('Y-m-d H:i:s')
    ));
}

/**
 * Get strategy leaderboard
 */
function getStrategyLeaderboard() {
    $outcomes = loadOutcomes();
    $strategies = loadStrategies();
    
    $performance = array();
    
    // Initialize
    foreach ($strategies['strategies'] as $s) {
        $performance[$s['id']] = array(
            'id' => $s['id'],
            'name' => $s['name'],
            'category' => $s['category'],
            'trades' => 0,
            'wins' => 0,
            'losses' => 0,
            'win_rate' => 0,
            'total_pnl' => 0,
            'avg_pnl' => 0,
            'status' => 'TESTING'
        );
    }
    
    // Aggregate
    foreach ($outcomes as $o) {
        $sid = $o['strategy_id'];
        if (!isset($performance[$sid])) continue;
        
        $performance[$sid]['trades']++;
        if ($o['outcome'] === 'WIN') $performance[$sid]['wins']++;
        if ($o['outcome'] === 'LOSS') $performance[$sid]['losses']++;
        $performance[$sid]['total_pnl'] += $o['pnl_pct'];
    }
    
    // Calculate stats
    foreach ($performance as &$p) {
        if ($p['trades'] > 0) {
            $p['win_rate'] = round(($p['wins'] / $p['trades']) * 100, 2);
            $p['avg_pnl'] = round($p['total_pnl'] / $p['trades'], 4);
        }
        
        // Determine status
        if ($p['trades'] >= 20) {
            if ($p['win_rate'] >= 60 && $p['avg_pnl'] > 0) {
                $p['status'] = 'PROMOTED';
            } elseif ($p['win_rate'] < 45 || $p['avg_pnl'] < 0) {
                $p['status'] = 'ELIMINATED';
            } else {
                $p['status'] = 'UNDER_REVIEW';
            }
        }
    }
    
    // Sort by win rate
    usort($performance, function($a, $b) {
        return $b['win_rate'] - $a['win_rate'];
    });
    
    echo json_encode(array(
        'ok' => true,
        'strategies' => array_values($performance),
        'promoted' => count(array_filter($performance, function($p) { return $p['status'] === 'PROMOTED'; })),
        'eliminated' => count(array_filter($performance, function($p) { return $p['status'] === 'ELIMINATED'; })),
        'testing' => count(array_filter($performance, function($p) { return $p['status'] === 'TESTING'; })),
        'timestamp' => date('Y-m-d H:i:s')
    ));
}

/**
 * Update strategy performance and apply elimination
 */
function updateStrategyPerformance() {
    $strategies = loadStrategies();
    $outcomes = loadOutcomes();
    
    // This would update a strategy status file
    // marking which are eliminated, promoted, etc.
    // Implementation depends on your persistence layer
}

// Helper functions

function loadStrategies() {
    $json = file_get_contents(STRATEGIES_FILE);
    return json_decode($json, true);
}

function loadActiveSignals() {
    $file = DATA_DIR . 'active_signals.json';
    if (!file_exists($file)) return array();
    $json = file_get_contents($file);
    $data = json_decode($json, true);
    return isset($data['signals']) ? $data['signals'] : array();
}

function saveActiveSignals($signals) {
    $file = DATA_DIR . 'active_signals.json';
    file_put_contents($file, json_encode(array('signals' => $signals), JSON_PRETTY_PRINT));
}

function loadOutcomes() {
    $file = DATA_DIR . 'signal_outcomes.json';
    if (!file_exists($file)) return array();
    $json = file_get_contents($file);
    $data = json_decode($json, true);
    return isset($data['outcomes']) ? $data['outcomes'] : array();
}

function logOutcome($signal) {
    $file = DATA_DIR . 'signal_outcomes.json';
    $outcomes = loadOutcomes();
    $outcomes[] = $signal;
    file_put_contents($file, json_encode(array('outcomes' => $outcomes), JSON_PRETTY_PRINT));
}

function logSignalGeneration($count, $timestamp) {
    $file = DATA_DIR . 'generation_log.txt';
    $line = $timestamp . ' | Generated: ' . $count . " signals\n";
    file_put_contents($file, $line, FILE_APPEND);
}

function hasActiveSignal($signals, $strategy_id, $asset) {
    foreach ($signals as $s) {
        if ($s['strategy_id'] === $strategy_id && $s['asset'] === $asset && $s['status'] === 'ACTIVE') {
            return true;
        }
    }
    return false;
}

function fetchKrakenPrices($pairs) {
    // In production: Call Kraken API
    // For demo: Return simulated data
    $data = array();
    foreach ($pairs as $pair) {
        $data[$pair] = array(
            'price' => simulatePrice($pair),
            'volume' => rand(100000, 10000000),
            'change_24h' => (rand(-500, 500) / 100)
        );
    }
    return $data;
}

function simulatePrice($pair) {
    // Base prices for simulation
    $bases = array(
        'XBTUSD' => 97000, 'ETHUSD' => 2800, 'SOLUSD' => 200,
        'XRPUSD' => 2.80, 'DOGEUSD' => 0.35, 'ADAUSD' => 0.80,
        'AVAXUSD' => 38, 'LINKUSD' => 20, 'DOTUSD' => 6.5,
        'MATICUSD' => 0.45, 'SHIBUSD' => 0.000025,
        'PEPEUSD' => 0.000015, 'FLOKIUSD' => 0.00015,
        'BONKUSD' => 0.000035, 'WIFUSD' => 1.85,
        'PENGUUSD' => 0.007, 'POPCATUSD' => 0.52,
        'TRUMPUSD' => 18.5, 'INJUSD' => 22, 'RENDERUSD' => 7.5
    );
    
    $base = isset($bases[$pair]) ? $bases[$pair] : 1;
    $noise = (rand(-100, 100) / 10000); // ±1%
    return $base * (1 + $noise);
}

function fetchIndicators($pair, $timeframe) {
    // In production: Fetch from your technical indicator API
    // For demo: Return simulated indicators
    return array(
        'rsi' => rand(20, 80),
        'macd' => (rand(-100, 100) / 100),
        'ema_8' => 0,
        'ema_21' => 0,
        'bb_upper' => 0,
        'bb_lower' => 0,
        'bb_width' => rand(3, 15),
        'volume' => rand(1000000, 10000000),
        'volume_avg' => 5000000,
        'adx' => rand(10, 50)
    );
}

function evaluateEntryRules($rules, $indicators, $price_data) {
    // Simplified evaluation - expand with actual logic
    // For demo: Random trigger with higher probability for certain conditions
    $trigger_prob = 0.1; // 10% base chance
    
    // Increase probability based on indicator alignment
    if ($indicators['rsi'] < 35 || $indicators['rsi'] > 70) $trigger_prob += 0.15;
    if ($indicators['macd'] > 0.5 || $indicators['macd'] < -0.5) $trigger_prob += 0.1;
    if ($indicators['bb_width'] < 8) $trigger_prob += 0.1;
    
    return (rand(1, 100) / 100) < $trigger_prob;
}

function extractTpPct($rules) {
    foreach ($rules as $rule) {
        if (preg_match('/(\d+)% profit/', $rule, $m)) return intval($m[1]);
    }
    return 5; // default
}

function extractSlPct($rules) {
    foreach ($rules as $rule) {
        if (preg_match('/(\d+)% loss/', $rule, $m)) return intval($m[1]);
    }
    return 2; // default
}

function timeframeToMinutes($tf) {
    $map = array('10m' => 10, '15m' => 15, '20m' => 20, '30m' => 30, '1h' => 60, '2h' => 120, '3h' => 180, '4h' => 240, '6h' => 360);
    return isset($map[$tf]) ? $map[$tf] : 60;
}
