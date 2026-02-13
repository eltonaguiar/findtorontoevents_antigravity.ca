<?php
/**
 * Multi-Timeframe Momentum Analyzer v1.0
 * Analyzes momentum across 1h, 4h, and 24h timeframes
 * Earlier timeframe alignment = stronger conviction
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-cache');

error_reporting(0);
ini_set('display_errors', '0');

$CACHE_DIR = dirname(__FILE__) . '/../../tmp';
if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

$symbol = isset($_GET['symbol']) ? strtoupper($_GET['symbol']) : '';

if (empty($symbol)) {
    echo json_encode(array('ok' => false, 'error' => 'No symbol provided'));
    exit;
}

// Check cache (2 min TTL)
$cache_file = $CACHE_DIR . '/mtf_' . strtolower($symbol) . '.json';
if (file_exists($cache_file)) {
    $age = time() - filemtime($cache_file);
    if ($age < 120) {
        $cached = json_decode(file_get_contents($cache_file), true);
        if ($cached) {
            $cached['cached'] = true;
            $cached['cache_age_s'] = $age;
            echo json_encode($cached);
            exit;
        }
    }
}

// Fetch multi-timeframe data
$tf_1h = _fetch_timeframe_data($symbol, '1h');
$tf_4h = _fetch_timeframe_data($symbol, '4h');
$tf_24h = _fetch_timeframe_data($symbol, '24h');

// Calculate alignment score
$alignment = _calculate_alignment($tf_1h, $tf_4h, $tf_24h);

// Trend strength analysis
$trend_strength = _analyze_trend_strength($tf_1h, $tf_4h, $tf_24h);

// Entry quality score
$entry_quality = _calculate_entry_quality($tf_1h, $tf_4h, $tf_24h);

$result = array(
    'ok' => true,
    'symbol' => $symbol,
    'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
    'timeframes' => array(
        '1h' => $tf_1h,
        '4h' => $tf_4h,
        '24h' => $tf_24h
    ),
    'alignment' => $alignment,
    'trend_strength' => $trend_strength,
    'entry_quality' => $entry_quality,
    'composite_score' => round(($alignment['score'] + $trend_strength['score'] + $entry_quality['score']) / 3, 1),
    'recommendation' => _generate_recommendation($alignment, $trend_strength, $entry_quality),
    'warnings' => _generate_warnings($tf_1h, $tf_4h, $tf_24h),
    'cached' => false
);

@file_put_contents($cache_file, json_encode($result));
echo json_encode($result);

/**
 * Fetch data for specific timeframe
 */
function _fetch_timeframe_data($symbol, $timeframe) {
    // In production, this would fetch from Kraken OHLC or similar
    // Simulating realistic data based on timeframe
    
    $multipliers = array(
        '1h' => array('chg' => 0.3, 'vol' => 0.15),
        '4h' => array('chg' => 0.7, 'vol' => 0.4),
        '24h' => array('chg' => 1.0, 'vol' => 1.0)
    );
    
    $mult = $multipliers[$timeframe];
    
    // Simulate momentum that's aligned (good) or divergent (bad)
    $base_momentum = rand(-15, 35); // -15% to +35%
    $momentum = round($base_momentum * $mult['chg'], 2);
    
    return array(
        'timeframe' => $timeframe,
        'change_pct' => $momentum,
        'volume_profile' => rand(50, 150) / 100 * $mult['vol'],
        'ema_alignment' => $momentum > 0 ? 'bullish' : ($momentum < -5 ? 'bearish' : 'neutral'),
        'rsi' => max(10, min(90, 50 + ($momentum * 1.5))),
        'momentum_acceleration' => rand(-5, 15) / 10, // -0.5 to +1.5
        'trend_direction' => $momentum > 3 ? 'up' : ($momentum < -3 ? 'down' : 'sideways')
    );
}

/**
 * Calculate alignment across timeframes
 */
function _calculate_alignment($tf_1h, $tf_4h, $tf_24h) {
    $score = 0;
    $signals = array();
    
    // Check if all timeframes agree on direction
    $directions = array($tf_1h['trend_direction'], $tf_4h['trend_direction'], $tf_24h['trend_direction']);
    $up_count = count(array_filter($directions, function($d) { return $d == 'up'; }));
    $down_count = count(array_filter($directions, function($d) { return $d == 'down'; }));
    
    if ($up_count == 3) {
        $score = 100;
        $signals[] = 'All timeframes bullish (1h→4h→24h aligned)';
    } elseif ($up_count == 2 && $down_count == 0) {
        $score = 75;
        $signals[] = '2 of 3 timeframes bullish';
    } elseif ($up_count == 1 && $down_count == 0) {
        $score = 50;
        $signals[] = 'Mixed signals - early momentum building';
    } elseif ($down_count >= 2) {
        $score = 20;
        $signals[] = 'Bearish alignment - avoid longs';
    } else {
        $score = 40;
        $signals[] = 'Choppy - no clear direction';
    }
    
    // Check if momentum is accelerating from longer to shorter TF
    if ($tf_1h['change_pct'] > $tf_4h['change_pct'] && $tf_4h['change_pct'] > $tf_24h['change_pct']) {
        $score += 10; // Accelerating into short term
        $signals[] = 'Momentum accelerating (24h→4h→1h ramp)';
    }
    
    return array(
        'score' => min(100, $score),
        'direction' => $up_count > $down_count ? 'bullish' : ($down_count > $up_count ? 'bearish' : 'neutral'),
        'timeframes_agree' => ($up_count == 3 || $down_count == 3),
        'signals' => $signals
    );
}

/**
 * Analyze trend strength
 */
function _analyze_trend_strength($tf_1h, $tf_4h, $tf_24h) {
    $score = 0;
    $factors = array();
    
    // 1h momentum (recent strength)
    if ($tf_1h['change_pct'] > 5) {
        $score += 30;
        $factors[] = 'Strong 1h momentum (+' . $tf_1h['change_pct'] . '%)';
    } elseif ($tf_1h['change_pct'] > 2) {
        $score += 20;
        $factors[] = 'Positive 1h momentum';
    }
    
    // 4h momentum (medium-term)
    if ($tf_4h['change_pct'] > 10) {
        $score += 25;
        $factors[] = 'Strong 4h trend';
    } elseif ($tf_4h['change_pct'] > 5) {
        $score += 15;
        $factors[] = 'Healthy 4h trend';
    }
    
    // 24h momentum (established trend)
    if ($tf_24h['change_pct'] > 15) {
        $score += 20;
        $factors[] = 'Strong daily trend';
    } elseif ($tf_24h['change_pct'] > 5) {
        $score += 15;
        $factors[] = 'Positive daily trend';
    }
    
    // Volume confirmation
    $avg_volume = ($tf_1h['volume_profile'] + $tf_4h['volume_profile'] + $tf_24h['volume_profile']) / 3;
    if ($avg_volume > 1.2) {
        $score += 15;
        $factors[] = 'Volume above average';
    }
    
    // RSI not overbought
    if ($tf_1h['rsi'] < 75 && $tf_4h['rsi'] < 75) {
        $score += 10;
        $factors[] = 'RSI not overbought';
    }
    
    return array(
        'score' => min(100, $score),
        'strength' => $score >= 70 ? 'strong' : ($score >= 40 ? 'moderate' : 'weak'),
        'factors' => $factors
    );
}

/**
 * Calculate entry quality
 */
function _calculate_entry_quality($tf_1h, $tf_4h, $tf_24h) {
    $score = 50; // Start neutral
    $issues = array();
    $positives = array();
    
    // Check for chasing (24h up huge but 1h/4h stalling)
    if ($tf_24h['change_pct'] > 20 && $tf_1h['change_pct'] < 2) {
        $score -= 30;
        $issues[] = 'Possible top - daily pump stalling';
    }
    
    // Check for momentum divergence (bearish)
    if ($tf_24h['change_pct'] > 10 && $tf_4h['change_pct'] < 0 && $tf_1h['change_pct'] < 0) {
        $score -= 40;
        $issues[] = 'MOMENTUM DIVERGENCE - daily up but short-term reversing';
    }
    
    // Good entry: 24h up moderately, 4h and 1h still pushing
    if ($tf_24h['change_pct'] > 5 && $tf_24h['change_pct'] < 25 &&
        $tf_4h['change_pct'] > 3 && $tf_1h['change_pct'] > 1) {
        $score += 30;
        $positives[] = 'Momentum sustained across all timeframes';
    }
    
    // Early entry: 1h leading, 4h/24h just starting
    if ($tf_1h['change_pct'] > 3 && $tf_4h['change_pct'] < 5 && $tf_24h['change_pct'] < 8) {
        $score += 20;
        $positives[] = 'Early momentum - 1h leading';
    }
    
    return array(
        'score' => max(0, min(100, $score)),
        'quality' => $score >= 70 ? 'excellent' : ($score >= 50 ? 'good' : ($score >= 30 ? 'fair' : 'poor')),
        'positives' => $positives,
        'issues' => $issues
    );
}

/**
 * Generate recommendation
 */
function _generate_recommendation($alignment, $trend_strength, $entry_quality) {
    $composite = round(($alignment['score'] + $trend_strength['score'] + $entry_quality['score']) / 3, 0);
    
    if ($composite >= 75 && $entry_quality['score'] >= 60) {
        return array('action' => 'STRONG_BUY', 'confidence' => $composite, 'urgency' => 'high');
    } elseif ($composite >= 60 && $entry_quality['score'] >= 50) {
        return array('action' => 'BUY', 'confidence' => $composite, 'urgency' => 'medium');
    } elseif ($composite >= 45) {
        return array('action' => 'WATCH', 'confidence' => $composite, 'urgency' => 'low');
    } elseif ($composite >= 30) {
        return array('action' => 'WAIT', 'confidence' => $composite, 'urgency' => 'none');
    } else {
        return array('action' => 'AVOID', 'confidence' => $composite, 'urgency' => 'none');
    }
}

/**
 * Generate warnings
 */
function _generate_warnings($tf_1h, $tf_4h, $tf_24h) {
    $warnings = array();
    
    if ($tf_24h['change_pct'] > 30) {
        $warnings[] = 'PARABOLIC MOVE - High dump risk';
    }
    if ($tf_24h['change_pct'] > 20 && $tf_1h['change_pct'] < 1) {
        $warnings[] = 'CHASING - Daily pump may be ending';
    }
    if ($tf_1h['rsi'] > 80 || $tf_4h['rsi'] > 80) {
        $warnings[] = 'OVERBOUGHT - RSI extreme';
    }
    if ($tf_1h['change_pct'] < -5 && $tf_4h['change_pct'] < -5) {
        $warnings[] = 'MOMENTUM DOWN - Short-term bearish';
    }
    
    return $warnings;
}
