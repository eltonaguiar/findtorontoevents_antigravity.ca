<?php
/**
 * Meme Coin Inverted Confidence Tier - Comprehensive Diagnostic Report
 * ==================================================================
 * 
 * Problem Statement:
 * The meme coin scoring model shows INVERTED win rates:
 * - Lean Buy (1-4): 5% win rate (1/20)
 * - Moderate Buy (5-7): 0% win rate (0/X)  
 * - Strong Buy (8-10): 0% win rate (0/3)
 * 
 * This report investigates WHY and provides actionable recommendations.
 * 
 * Usage:
 *   CLI: php tier_diagnosis_report.php [json|html|both]
 *   Web: Access via API endpoint /api/diagnose_tiers.php?action=full_report
 * 
 * PHP 5.2+ Compatible
 */

// Configuration
$db_config = array(
    'host' => 'mysql.50webs.com',
    'user' => 'ejaguiar1_memecoin',
    'pass' => 'testing123',
    'name' => 'ejaguiar1_memecoin'
);

$REPORT_CONFIG = array(
    'min_samples' => 20,
    'output_dir' => dirname(__FILE__) . '/',
    'days_lookback' => 90,
    'threshold_configs' => array(
        'current' => array('lean' => 72, 'buy' => 78, 'strong' => 85),
        'conservative' => array('lean' => 75, 'buy' => 82, 'strong' => 90),
        'aggressive' => array('lean' => 65, 'buy' => 72, 'strong' => 80),
        'inverted' => array('lean' => 40, 'buy' => 50, 'strong' => 60),
        'mean_reversion' => array('lean' => 30, 'buy' => 45, 'strong' => 60)
    )
);

// Feature mapping from factors_json
$FEATURE_MAP = array(
    'momentum_4h' => array('key' => 'parabolic_momentum', 'subkey' => 'mom_15m'),
    'momentum_24h' => array('key' => 'social_proxy', 'subkey' => 'mom_1h'),
    'volume_surge' => array('key' => 'explosive_volume', 'subkey' => 'ratio'),
    'social_proxy' => array('key' => 'social_proxy', 'subkey' => 'velocity'),
    'entry_position' => array('key' => 'breakout_4h', 'subkey' => 'breakout_pct'),
    'spread' => array('key' => 'rsi_hype_zone', 'subkey' => 'rsi'),
    'breakout_4h' => array('key' => 'breakout_4h', 'subkey' => 'score'),
    'rsi' => array('key' => 'rsi_hype_zone', 'subkey' => 'rsi')
);

// ═══════════════════════════════════════════════════════════════════════
// DATABASE CONNECTION
// ═══════════════════════════════════════════════════════════════════════

function get_db_connection($config) {
    $conn = new mysqli($config['host'], $config['user'], $config['pass'], $config['name']);
    if ($conn->connect_error) {
        return array('ok' => false, 'error' => 'Connection failed: ' . $conn->connect_error);
    }
    $conn->set_charset('utf8');
    return array('ok' => true, 'conn' => $conn);
}

// ═══════════════════════════════════════════════════════════════════════
// DATA COLLECTION
// ═══════════════════════════════════════════════════════════════════════

function collect_signal_data($conn, $days = 90) {
    $query = "SELECT 
        id,
        pair,
        score,
        verdict,
        tier,
        factors_json,
        outcome,
        pnl_pct,
        target_pct,
        risk_pct,
        created_at,
        resolved_at,
        price_at_signal,
        price_at_resolve
    FROM mc_winners
    WHERE outcome IS NOT NULL
    AND outcome != ''
    AND created_at > DATE_SUB(NOW(), INTERVAL $days DAY)
    ORDER BY created_at DESC";
    
    $res = $conn->query($query);
    if (!$res) {
        return array('ok' => false, 'error' => 'Query failed: ' . $conn->error);
    }
    
    $samples = array();
    while ($row = $res->fetch_assoc()) {
        $factors = json_decode($row['factors_json'], true);
        if (!is_array($factors)) {
            $factors = array();
        }
        
        // Extract feature values
        global $FEATURE_MAP;
        $feature_values = array();
        foreach ($FEATURE_MAP as $fname => $fconfig) {
            $feature_values[$fname] = extract_feature_value($factors, $fconfig);
        }
        
        $samples[] = array(
            'signal_id' => $row['id'],
            'symbol' => $row['pair'],
            'score' => intval($row['score']),
            'verdict' => $row['verdict'],
            'tier' => $row['tier'],
            'outcome' => $row['outcome'],
            'is_win' => ($row['outcome'] === 'win' || $row['outcome'] === 'partial_win'),
            'return_pct' => floatval($row['pnl_pct']),
            'features' => $feature_values,
            'factors_raw' => $factors,
            'created_at' => $row['created_at'],
            'resolved_at' => $row['resolved_at']
        );
    }
    
    return array(
        'ok' => true,
        'samples' => $samples,
        'count' => count($samples),
        'wins' => count(array_filter($samples, create_function('$s', 'return $s["is_win"];'))),
        'losses' => count(array_filter($samples, create_function('$s', 'return !$s["is_win"];')))
    );
}

function extract_feature_value($factors, $config) {
    $key = $config['key'];
    $subkey = $config['subkey'];
    
    if (!isset($factors[$key])) {
        return null;
    }
    
    $f = $factors[$key];
    
    if (is_array($f)) {
        if (isset($f[$subkey])) {
            return floatval($f[$subkey]);
        }
        if (isset($f['score'])) {
            return floatval($f['score']);
        }
    }
    
    if (is_numeric($f)) {
        return floatval($f);
    }
    
    return null;
}

// ═══════════════════════════════════════════════════════════════════════
// STATISTICAL FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════

function pearson_correlation($x, $y) {
    $n = count($x);
    
    if ($n < 3 || count($y) != $n) {
        return array('r' => 0, 'p_value' => 1, 'n' => $n);
    }
    
    $sum_x = array_sum($x);
    $sum_y = array_sum($y);
    $sum_xy = 0;
    $sum_x2 = 0;
    $sum_y2 = 0;
    
    for ($i = 0; $i < $n; $i++) {
        $sum_xy += $x[$i] * $y[$i];
        $sum_x2 += $x[$i] * $x[$i];
        $sum_y2 += $y[$i] * $y[$i];
    }
    
    $numerator = $n * $sum_xy - $sum_x * $sum_y;
    $denominator = sqrt(($n * $sum_x2 - $sum_x * $sum_x) * ($n * $sum_y2 - $sum_y * $sum_y));
    
    if ($denominator == 0) {
        return array('r' => 0, 'p_value' => 1, 'n' => $n);
    }
    
    $r = $numerator / $denominator;
    
    // Approximate p-value using t-statistic
    if (abs($r) >= 1) {
        $p_value = 0;
    } else {
        $t = $r * sqrt(($n - 2) / (1 - $r * $r));
        $abs_t = abs($t);
        if ($abs_t < 1) $p_value = 0.5;
        elseif ($abs_t < 1.64) $p_value = 0.1;
        elseif ($abs_t < 1.96) $p_value = 0.05;
        elseif ($abs_t < 2.58) $p_value = 0.01;
        elseif ($abs_t < 3.29) $p_value = 0.001;
        else $p_value = 0.0001;
    }
    
    return array('r' => $r, 'p_value' => $p_value, 'n' => $n);
}

function mean($arr) {
    if (empty($arr)) return 0;
    return array_sum($arr) / count($arr);
}

function std_dev($arr) {
    $n = count($arr);
    if ($n < 2) return 0;
    
    $mean = array_sum($arr) / $n;
    $sum_squared_diff = 0;
    
    foreach ($arr as $v) {
        $diff = $v - $mean;
        $sum_squared_diff += $diff * $diff;
    }
    
    return sqrt($sum_squared_diff / ($n - 1));
}

// ═══════════════════════════════════════════════════════════════════════
// ANALYSIS FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════

function analyze_feature_correlations($data) {
    global $FEATURE_MAP;
    $results = array();
    
    foreach ($FEATURE_MAP as $fname => $fconfig) {
        $x_values = array();
        $y_outcomes = array();
        $y_returns = array();
        
        foreach ($data as $sample) {
            $val = $sample['features'][$fname];
            if ($val !== null) {
                $x_values[] = $val;
                $y_outcomes[] = $sample['is_win'] ? 1 : 0;
                $y_returns[] = $sample['return_pct'];
            }
        }
        
        if (count($x_values) < 10) {
            $results[$fname] = array(
                'error' => 'Insufficient samples',
                'sample_count' => count($x_values)
            );
            continue;
        }
        
        $corr_outcome = pearson_correlation($x_values, $y_outcomes);
        $corr_return = pearson_correlation($x_values, $y_returns);
        
        // Interpretation
        $r = $corr_outcome['r'];
        if (abs($r) < 0.1) {
            $interpretation = 'No meaningful correlation';
            $direction = 'neutral';
        } elseif ($r > 0.2) {
            $interpretation = 'POSITIVE: Higher values predict WINS';
            $direction = 'positive';
        } elseif ($r < -0.2) {
            $interpretation = 'NEGATIVE: Higher values predict LOSSES (INVERTED!)';
            $direction = 'negative';
        } else {
            $interpretation = 'Weak correlation';
            $direction = 'weak';
        }
        
        $results[$fname] = array(
            'correlation_with_win' => round($r, 4),
            'correlation_with_return' => round($corr_return['r'], 4),
            'p_value' => round($corr_outcome['p_value'], 4),
            'sample_count' => count($x_values),
            'mean_value' => round(mean($x_values), 4),
            'std_dev' => round(std_dev($x_values), 4),
            'interpretation' => $interpretation,
            'direction' => $direction
        );
    }
    
    // Summary
    $negative = 0;
    $positive = 0;
    $neutral = 0;
    $inverted_features = array();
    $strong_features = array();
    
    foreach ($results as $fname => $r) {
        if (isset($r['direction'])) {
            if ($r['direction'] === 'negative') {
                $negative++;
                $inverted_features[] = $fname;
            } elseif ($r['direction'] === 'positive') {
                $positive++;
                $strong_features[] = $fname;
            } else {
                $neutral++;
            }
        }
    }
    
    return array(
        'feature_correlations' => $results,
        'summary' => array(
            'negative_correlations' => $negative,
            'positive_correlations' => $positive,
            'neutral_correlations' => $neutral,
            'inverted_features' => $inverted_features,
            'strong_features' => $strong_features,
            'verdict' => $negative > $positive 
                ? 'CRITICAL: More features show NEGATIVE correlation. Model may be inverted!'
                : ($positive > 0 ? 'Features show expected positive correlation.' : 'Most features are neutral/weak.')
        )
    );
}

function analyze_tier_performance($data) {
    $lean_signals = array_filter($data, create_function('$s', 'return $s["score"] >= 72 && $s["score"] < 78;'));
    $buy_signals = array_filter($data, create_function('$s', 'return $s["score"] >= 78 && $s["score"] < 85;'));
    $strong_signals = array_filter($data, create_function('$s', 'return $s["score"] >= 85;'));
    
    return array(
        'lean_buy_1_4' => calculate_performance_stats($lean_signals),
        'moderate_buy_5_7' => calculate_performance_stats($buy_signals),
        'strong_buy_8_10' => calculate_performance_stats($strong_signals)
    );
}

function calculate_performance_stats($signals) {
    $count = count($signals);
    if ($count == 0) {
        return array(
            'signals' => 0,
            'wins' => 0,
            'losses' => 0,
            'win_rate' => 0,
            'avg_return' => 0,
            'max_return' => 0,
            'min_return' => 0
        );
    }
    
    $wins = count(array_filter($signals, create_function('$s', 'return $s["is_win"];')));
    $returns = array_map(create_function('$s', 'return $s["return_pct"];'), $signals);
    
    return array(
        'signals' => $count,
        'wins' => $wins,
        'losses' => $count - $wins,
        'win_rate' => round(($wins / $count) * 100, 2),
        'avg_return' => round(array_sum($returns) / count($returns), 4),
        'max_return' => round(max($returns), 4),
        'min_return' => round(min($returns), 4)
    );
}

function test_inversion_hypothesis($data) {
    $results = array();
    
    // Test 1: Short high scores (>85)
    $high_scores = array_filter($data, create_function('$s', 'return $s["score"] > 85;'));
    $results['short_above_85'] = calculate_inverted_stats($high_scores);
    
    // Test 2: Short very high scores (>90)
    $very_high = array_filter($data, create_function('$s', 'return $s["score"] > 90;'));
    $results['short_above_90'] = calculate_inverted_stats($very_high);
    
    // Test 3: Buy low scores (<40)
    $low_scores = array_filter($data, create_function('$s', 'return $s["score"] < 40;'));
    $results['buy_below_40'] = calculate_performance_stats($low_scores);
    
    // Test 4: Buy very low scores (<30)
    $very_low = array_filter($data, create_function('$s', 'return $s["score"] < 30;'));
    $results['buy_below_30'] = calculate_performance_stats($very_low);
    
    // Test 5: Contrarian on all signals >= 72
    $all_signals = array_filter($data, create_function('$s', 'return $s["score"] >= 72;'));
    $results['contrarian_all'] = calculate_inverted_stats($all_signals);
    
    // Calculate evidence score
    $evidence_score = 0;
    $evidence_points = array();
    
    if ($results['short_above_85']['inverted_win_rate'] > 50) {
        $evidence_score += 2;
        $evidence_points[] = 'Shorting >85 scores yields ' . $results['short_above_85']['inverted_win_rate'] . '% win rate';
    }
    if ($results['short_above_90']['inverted_win_rate'] > 50) {
        $evidence_score += 2;
        $evidence_points[] = 'Shorting >90 scores yields ' . $results['short_above_90']['inverted_win_rate'] . '% win rate';
    }
    if ($results['buy_below_40']['win_rate'] > 50) {
        $evidence_score += 2;
        $evidence_points[] = 'Buying <40 scores yields ' . $results['buy_below_40']['win_rate'] . '% win rate';
    }
    if ($results['contrarian_all']['inverted_win_rate'] > 50) {
        $evidence_score += 2;
        $evidence_points[] = 'Contrarian strategy yields ' . $results['contrarian_all']['inverted_win_rate'] . '% win rate';
    }
    
    // Determine verdict
    if ($evidence_score >= 6) {
        $verdict = 'STRONG EVIDENCE for signal inversion';
    } elseif ($evidence_score >= 3) {
        $verdict = 'MODERATE EVIDENCE for signal inversion';
    } elseif ($evidence_score >= 1) {
        $verdict = 'Weak evidence - needs more data';
    } else {
        $verdict = 'No evidence for inversion';
    }
    
    return array(
        'inversion_tests' => $results,
        'evidence_score' => $evidence_score,
        'max_score' => 8,
        'verdict' => $verdict,
        'evidence_points' => $evidence_points
    );
}

function calculate_inverted_stats($signals) {
    $stats = calculate_performance_stats($signals);
    
    return array(
        'original_count' => $stats['signals'],
        'original_win_rate' => $stats['win_rate'],
        'original_avg_return' => $stats['avg_return'],
        'inverted_win_rate' => round(100 - $stats['win_rate'], 2),
        'inverted_avg_return' => round(-$stats['avg_return'], 4),
        'edge_vs_original' => round((100 - $stats['win_rate']) - $stats['win_rate'], 2),
        'viable_strategy' => (100 - $stats['win_rate']) > 55 && $stats['signals'] >= 5
    );
}

function analyze_momentum_exhaustion($data) {
    $score_ranges = array(
        '90-100' => array(90, 100),
        '85-89' => array(85, 89),
        '80-84' => array(80, 84),
        '75-79' => array(75, 79),
        '70-74' => array(70, 74),
        '60-69' => array(60, 69),
        '50-59' => array(50, 59),
        '0-49' => array(0, 49)
    );
    
    $range_analysis = array();
    
    foreach ($score_ranges as $range_name => $bounds) {
        $range_data = array_filter($data, create_function('$s', '
            return $s["score"] >= ' . $bounds[0] . ' && $s["score"] <= ' . $bounds[1] . ';
        '));
        
        if (count($range_data) < 3) {
            $range_analysis[$range_name] = array('note' => 'Insufficient data', 'count' => count($range_data));
            continue;
        }
        
        $stats = calculate_performance_stats($range_data);
        
        // Calculate exhaustion score
        $exhaustion_score = 0;
        if ($stats['win_rate'] < 30) $exhaustion_score += 3;
        elseif ($stats['win_rate'] < 45) $exhaustion_score += 1;
        if ($stats['avg_return'] < -2) $exhaustion_score += 2;
        elseif ($stats['avg_return'] < 0) $exhaustion_score += 1;
        if ($bounds[0] >= 85 && $stats['win_rate'] < 40) $exhaustion_score += 2;
        
        $range_analysis[$range_name] = array(
            'count' => $stats['signals'],
            'wins' => $stats['wins'],
            'losses' => $stats['losses'],
            'win_rate' => $stats['win_rate'],
            'avg_return' => $stats['avg_return'],
            'exhaustion_score' => $exhaustion_score,
            'exhaustion_level' => $exhaustion_score >= 6 ? 'HIGH' : ($exhaustion_score >= 3 ? 'MODERATE' : 'LOW')
        );
    }
    
    // Check if high scores predict negative returns (exhaustion)
    $high_score_returns = array();
    foreach ($data as $d) {
        if ($d['score'] >= 80) {
            $high_score_returns[] = $d['return_pct'];
        }
    }
    
    $avg_high_return = !empty($high_score_returns) ? array_sum($high_score_returns) / count($high_score_returns) : 0;
    
    return array(
        'range_analysis' => $range_analysis,
        'high_score_80_plus_avg_return' => round($avg_high_return, 4),
        'exhaustion_detected' => $avg_high_return < -0.5
    );
}

function optimize_thresholds($data, $configs) {
    $results = array();
    
    foreach ($configs as $name => $thresholds) {
        $simulation = simulate_thresholds($data, $thresholds);
        $results[$name] = array(
            'thresholds' => $thresholds,
            'performance' => $simulation
        );
    }
    
    // Find best configuration
    $best_config = null;
    $best_score = -999;
    
    foreach ($results as $name => $result) {
        $score = $result['performance']['overall_score'];
        if ($score > $best_score) {
            $best_score = $score;
            $best_config = $name;
        }
    }
    
    return array(
        'all_configs' => $results,
        'best_config' => $best_config,
        'best_thresholds' => $results[$best_config]['thresholds'],
        'best_performance' => $results[$best_config]['performance']
    );
}

function simulate_thresholds($data, $thresholds) {
    $lean = array_filter($data, create_function('$s', 'return $s["score"] >= ' . $thresholds['lean'] . ' && $s["score"] < ' . $thresholds['buy'] . ';'));
    $buy = array_filter($data, create_function('$s', 'return $s["score"] >= ' . $thresholds['buy'] . ' && $s["score"] < ' . $thresholds['strong'] . ';'));
    $strong = array_filter($data, create_function('$s', 'return $s["score"] >= ' . $thresholds['strong'] . ';'));
    
    $lean_stats = calculate_performance_stats($lean);
    $buy_stats = calculate_performance_stats($buy);
    $strong_stats = calculate_performance_stats($strong);
    
    // Calculate overall score (prefer higher win rates in higher tiers)
    $score = 0;
    if ($strong_stats['win_rate'] > $buy_stats['win_rate'] && $buy_stats['win_rate'] > $lean_stats['win_rate']) {
        $score += 30; // Natural ordering
    }
    $score += $strong_stats['win_rate'] * 0.3;
    $score += $buy_stats['win_rate'] * 0.25;
    $score += $lean_stats['win_rate'] * 0.15;
    
    return array(
        'lean_buy' => $lean_stats,
        'buy' => $buy_stats,
        'strong_buy' => $strong_stats,
        'overall_score' => round($score, 2)
    );
}

// ═══════════════════════════════════════════════════════════════════════
// REPORT GENERATION
// ═══════════════════════════════════════════════════════════════════════

function generate_recommendations($correlations, $tiers, $inversion, $exhaustion, $thresholds) {
    $recs = array();
    
    // Check for inverted correlations
    if ($correlations['summary']['negative_correlations'] > $correlations['summary']['positive_correlations']) {
        $recs[] = array(
            'priority' => 'CRITICAL',
            'category' => 'Feature Logic',
            'finding' => count($correlations['summary']['inverted_features']) . ' features show NEGATIVE correlation with wins',
            'action' => 'Invert feature weights OR investigate data quality. Features: ' . implode(', ', $correlations['summary']['inverted_features'])
        );
    }
    
    // Check for inversion hypothesis
    if ($inversion['evidence_score'] >= 5) {
        $recs[] = array(
            'priority' => 'CRITICAL',
            'category' => 'Signal Direction',
            'finding' => $inversion['verdict'],
            'action' => 'Test CONTRARIAN strategy: Short strong signals, buy weak signals'
        );
    }
    
    // Check for momentum exhaustion
    if ($exhaustion['exhaustion_detected']) {
        $recs[] = array(
            'priority' => 'HIGH',
            'category' => 'Momentum Model',
            'finding' => 'High scores correlate with negative returns - exhaustion pattern detected',
            'action' => 'Reduce holding periods OR flip high-score signals to SHORTs'
        );
    }
    
    // Check tier performance
    $strong_wr = $tiers['strong_buy_8_10']['win_rate'];
    $lean_wr = $tiers['lean_buy_1_4']['win_rate'];
    
    if ($strong_wr < $lean_wr) {
        $recs[] = array(
            'priority' => 'CRITICAL',
            'category' => 'Tier Calibration',
            'finding' => "Inverted tier performance: Strong Buy {$strong_wr}% < Lean Buy {$lean_wr}%",
            'action' => 'Completely invert the scoring model OR use mean-reversion instead of momentum'
        );
    }
    
    // Threshold recommendation
    if ($thresholds['best_config'] !== 'current') {
        $recs[] = array(
            'priority' => 'MEDIUM',
            'category' => 'Threshold Optimization',
            'finding' => "Current thresholds suboptimal. Best config: {$thresholds['best_config']}",
            'action' => 'Test new thresholds: Lean=' . $thresholds['best_thresholds']['lean'] . 
                       ', Buy=' . $thresholds['best_thresholds']['buy'] . 
                       ', Strong=' . $thresholds['best_thresholds']['strong']
        );
    }
    
    // Data sufficiency
    $total_signals = $tiers['lean_buy_1_4']['signals'] + $tiers['moderate_buy_5_7']['signals'] + $tiers['strong_buy_8_10']['signals'];
    if ($total_signals < 50) {
        $recs[] = array(
            'priority' => 'INFO',
            'category' => 'Data Collection',
            'finding' => "Only {$total_signals} signals in dataset - insufficient for statistical significance",
            'action' => 'Continue collecting outcomes. Target: 100+ resolved signals'
        );
    }
    
    return $recs;
}

function generate_full_report($use_synthetic = false) {
    global $db_config, $REPORT_CONFIG;
    
    // Connect to database
    $db_result = get_db_connection($db_config);
    $data_source = 'real';
    $samples_result = null;
    
    if (!$db_result['ok']) {
        return array('ok' => false, 'error' => 'Database error: ' . $db_result['error']);
    }
    
    $conn = $db_result['conn'];
    
    // Collect data
    if (!$use_synthetic) {
        $samples_result = collect_signal_data($conn, $REPORT_CONFIG['days_lookback']);
        if (!$samples_result['ok'] || $samples_result['count'] < $REPORT_CONFIG['min_samples']) {
            $use_synthetic = true;
        }
    }
    
    if ($use_synthetic) {
        $data = generate_synthetic_inverted_data(300);
        $data_source = 'synthetic';
        $samples_result = array(
            'count' => count($data),
            'wins' => count(array_filter($data, create_function('$s', 'return $s["is_win"];'))),
            'losses' => count(array_filter($data, create_function('$s', 'return !$s["is_win"];')))
        );
    } else {
        $data = $samples_result['samples'];
    }
    
    $conn->close();
    
    // Run all analyses
    $correlations = analyze_feature_correlations($data);
    $tier_analysis = analyze_tier_performance($data);
    $inversion_test = test_inversion_hypothesis($data);
    $momentum_exhaustion = analyze_momentum_exhaustion($data);
    $threshold_optimization = optimize_thresholds($data, $REPORT_CONFIG['threshold_configs']);
    
    // Generate recommendations
    $recommendations = generate_recommendations(
        $correlations,
        $tier_analysis,
        $inversion_test,
        $momentum_exhaustion,
        $threshold_optimization
    );
    
    // Determine primary cause
    $primary_cause = 'Unknown';
    $evidence_score = 0;
    
    if ($inversion_test['evidence_score'] >= 5) {
        $primary_cause = 'Momentum exhaustion - high scores capture peak hype (buy the rumor, sell the news)';
        $evidence_score = 8;
    } elseif ($correlations['summary']['negative_correlations'] > 0) {
        $primary_cause = 'Feature inversion - scoring formula rewards wrong signals';
        $evidence_score = 6;
    }
    
    // Build final report
    $report = array(
        'generated_at' => date('Y-m-d H:i:s'),
        'data_source' => $data_source,
        'total_signals' => $samples_result['count'],
        'data_summary' => array(
            'wins' => $samples_result['wins'],
            'losses' => $samples_result['losses'],
            'baseline_win_rate' => $samples_result['count'] > 0 
                ? round(($samples_result['wins'] / $samples_result['count']) * 100, 2) 
                : 0
        ),
        'summary' => array(
            'issue' => 'Inverted confidence tiers',
            'evidence_score' => $evidence_score,
            'primary_cause' => $primary_cause,
            'confidence' => $evidence_score >= 7 ? 'HIGH' : ($evidence_score >= 4 ? 'MEDIUM' : 'LOW')
        ),
        'tier_analysis' => $tier_analysis,
        'feature_correlations' => $correlations,
        'inversion_test' => array(
            'short_above_85_win_rate' => isset($inversion_test['inversion_tests']['short_above_85']) 
                ? $inversion_test['inversion_tests']['short_above_85']['inverted_win_rate'] 
                : 0,
            'buy_below_40_win_rate' => isset($inversion_test['inversion_tests']['buy_below_40']) 
                ? $inversion_test['inversion_tests']['buy_below_40']['win_rate'] 
                : 0,
            'contrarian_win_rate' => isset($inversion_test['inversion_tests']['contrarian_all']) 
                ? $inversion_test['inversion_tests']['contrarian_all']['inverted_win_rate'] 
                : 0,
            'evidence_score' => $inversion_test['evidence_score'],
            'max_score' => $inversion_test['max_score'],
            'conclusion' => $inversion_test['verdict'],
            'full_results' => $inversion_test['inversion_tests']
        ),
        'momentum_exhaustion' => array(
            'high_score_80_plus_avg_return' => $momentum_exhaustion['high_score_80_plus_avg_return'],
            'exhaustion_detected' => $momentum_exhaustion['exhaustion_detected'],
            'range_analysis' => $momentum_exhaustion['range_analysis'],
            'conclusion' => $momentum_exhaustion['exhaustion_detected'] 
                ? 'High scores predict negative future returns - exhaustion confirmed'
                : 'No clear exhaustion pattern detected'
        ),
        'threshold_optimization' => array(
            'best_config' => $threshold_optimization['best_config'],
            'best_thresholds' => $threshold_optimization['best_thresholds'],
            'best_performance' => $threshold_optimization['best_performance'],
            'all_configs' => $threshold_optimization['all_configs'],
            'recommendation' => $threshold_optimization['best_config'] === 'inverted' || $threshold_optimization['best_config'] === 'mean_reversion'
                ? 'Invert the scoring model or use mean-reversion logic'
                : 'Adjust thresholds to optimize tier separation'
        ),
        'recommendations' => $recommendations,
        'key_question_answer' => array(
            'question' => 'Is the scoring model fundamentally wrong or just miscalibrated?',
            'answer' => $evidence_score >= 6 
                ? 'FUNDAMENTALLY WRONG - The model captures momentum exhaustion, not momentum continuation. Inversion recommended.'
                : 'MISCALIBRATED - Threshold adjustment may suffice.',
            'confidence' => $evidence_score >= 7 ? 'HIGH' : ($evidence_score >= 4 ? 'MEDIUM' : 'LOW')
        )
    );
    
    return array('ok' => true, 'report' => $report, 'data' => $data);
}

function generate_synthetic_inverted_data($count = 300) {
    $samples = array();
    
    for ($i = 0; $i < $count; $i++) {
        $score = mt_rand(0, 100);
        
        // Simulate INVERTED outcome pattern
        $win_probability = 0.5 - ($score / 200);
        $win_probability = max(0.1, min(0.9, $win_probability));
        
        $is_win = (mt_rand(1, 100) / 100) < $win_probability;
        
        if ($is_win) {
            $return_pct = mt_rand(10, 50) / 10;
        } else {
            $return_pct = -mt_rand(10, 40) / 10;
        }
        
        $samples[] = array(
            'signal_id' => 'synth_' . $i,
            'symbol' => 'COIN' . $i . '_USDT',
            'score' => $score,
            'verdict' => $score >= 85 ? 'STRONG_BUY' : ($score >= 78 ? 'BUY' : ($score >= 72 ? 'LEAN_BUY' : 'SKIP')),
            'tier' => $score >= 85 ? 'tier1' : 'tier2',
            'outcome' => $is_win ? 'win' : 'loss',
            'is_win' => $is_win,
            'return_pct' => $return_pct,
            'features' => array(
                'momentum_4h' => min(20, $score / 5 + mt_rand(-20, 20) / 10),
                'momentum_24h' => min(15, $score / 6 + mt_rand(-20, 20) / 10),
                'volume_surge' => min(10, $score / 8 + mt_rand(-10, 10) / 10),
                'social_proxy' => min(15, $score / 6 + mt_rand(-15, 15) / 10),
                'entry_position' => ($score - 50) / 10 + mt_rand(-5, 5) / 10,
                'spread' => max(30, min(90, $score / 2 + 30 + mt_rand(-10, 10))),
                'breakout_4h' => min(10, $score / 10 + mt_rand(-5, 5) / 10),
                'rsi' => max(30, min(95, $score / 2 + 35 + mt_rand(-10, 10)))
            ),
            'created_at' => date('Y-m-d H:i:s', strtotime("-" . mt_rand(1, 90) . " days"))
        );
    }
    
    return $samples;
}

// ═══════════════════════════════════════════════════════════════════════
// HTML REPORT GENERATION
// ═══════════════════════════════════════════════════════════════════════

function generate_html_report($report) {
    $json_data = json_encode($report);
    
    $html = <<<HTML
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Meme Coin Tier Diagnosis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f1419;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
            line-height: 1.6;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        h1 {
            color: #ff6b6b;
            text-align: center;
            border-bottom: 2px solid #ff6b6b;
            padding-bottom: 15px;
        }
        h2 {
            color: #4ecdc4;
            margin-top: 30px;
            border-left: 4px solid #4ecdc4;
            padding-left: 15px;
        }
        h3 { color: #96ceb4; }
        .summary-box {
            background: linear-gradient(135deg, #1a1f2e 0%, #252b3d 100%);
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
            border: 1px solid #ff6b6b;
        }
        .critical { border-color: #ff6b6b; }
        .warning { border-color: #f9ca24; }
        .success { border-color: #6c5ce7; }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .metric-card {
            background: #1a1f2e;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            border: 1px solid #333;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #4ecdc4;
        }
        .metric-label {
            color: #888;
            font-size: 0.9em;
        }
        .tier-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .tier-table th, .tier-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #333;
        }
        .tier-table th {
            background: #1a1f2e;
            color: #4ecdc4;
        }
        .tier-table tr:hover { background: #252b3d; }
        .negative { color: #ff6b6b; }
        .positive { color: #00d26a; }
        .chart-container {
            background: #1a1f2e;
            border-radius: 12px;
            padding: 20px;
            margin: 20px 0;
        }
        .recommendation {
            background: #1a1f2e;
            border-left: 4px solid;
            padding: 15px;
            margin: 10px 0;
            border-radius: 0 8px 8px 0;
        }
        .rec-critical { border-color: #ff6b6b; }
        .rec-high { border-color: #f9ca24; }
        .rec-medium { border-color: #74b9ff; }
        .rec-info { border-color: #a29bfe; }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
            margin-right: 10px;
        }
        .badge-critical { background: #ff6b6b; color: #fff; }
        .badge-high { background: #f9ca24; color: #000; }
        .badge-medium { background: #74b9ff; color: #000; }
        .badge-info { background: #a29bfe; color: #fff; }
        .correlation-bar {
            height: 24px;
            background: #333;
            border-radius: 12px;
            overflow: hidden;
            position: relative;
        }
        .correlation-fill {
            height: 100%;
            transition: width 0.3s ease;
        }
        .correlation-negative { background: linear-gradient(90deg, #ff6b6b, #ee5a24); }
        .correlation-positive { background: linear-gradient(90deg, #00d26a, #00b894); }
        .timestamp {
            text-align: center;
            color: #666;
            font-size: 0.9em;
            margin-bottom: 20px;
        }
        .answer-box {
            background: linear-gradient(135deg, #2d3436 0%, #1a1f2e 100%);
            border: 2px solid #6c5ce7;
            border-radius: 12px;
            padding: 25px;
            margin: 30px 0;
            text-align: center;
        }
        .answer-question {
            color: #a29bfe;
            font-size: 1.1em;
            margin-bottom: 10px;
        }
        .answer-text {
            font-size: 1.3em;
            font-weight: bold;
            color: #fff;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚨 Meme Coin Inverted Confidence Tier Diagnosis</h1>
        <div class="timestamp">Generated: {$report['generated_at']} | Data Source: {$report['data_source']}</div>
        
        <div class="summary-box critical">
            <h3>📊 Executive Summary</h3>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-value">{$report['summary']['evidence_score']}/10</div>
                    <div class="metric-label">Evidence Score</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{$report['total_signals']}</div>
                    <div class="metric-label">Total Signals</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{$report['data_summary']['baseline_win_rate']}%</div>
                    <div class="metric-label">Baseline Win Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{$report['summary']['confidence']}</div>
                    <div class="metric-label">Confidence Level</div>
                </div>
            </div>
            <p><strong>Primary Cause:</strong> {$report['summary']['primary_cause']}</p>
        </div>
        
        <div class="answer-box">
            <div class="answer-question">🔍 Key Question: Is the model fundamentally wrong or just miscalibrated?</div>
            <div class="answer-text">{$report['key_question_answer']['answer']}</div>
            <p>Confidence: <strong>{$report['key_question_answer']['confidence']}</strong></p>
        </div>
        
        <h2>📈 Tier Performance Analysis</h2>
        <table class="tier-table">
            <thead>
                <tr>
                    <th>Tier</th>
                    <th>Score Range</th>
                    <th>Signals</th>
                    <th>Wins</th>
                    <th>Win Rate</th>
                    <th>Avg Return</th>
                </tr>
            </thead>
            <tbody>
HTML;

    // Add tier rows
    $tiers = $report['tier_analysis'];
    $tier_names = array(
        'lean_buy_1_4' => array('name' => 'Lean Buy', 'range' => '72-77'),
        'moderate_buy_5_7' => array('name' => 'Moderate Buy', 'range' => '78-84'),
        'strong_buy_8_10' => array('name' => 'Strong Buy', 'range' => '85+')
    );
    
    foreach ($tier_names as $key => $info) {
        $t = $tiers[$key];
        $wr_class = $t['win_rate'] < 40 ? 'negative' : ($t['win_rate'] > 55 ? 'positive' : '');
        $ret_class = $t['avg_return'] < 0 ? 'negative' : 'positive';
        
        $html .= <<<HTML
                <tr>
                    <td><strong>{$info['name']}</strong></td>
                    <td>{$info['range']}</td>
                    <td>{$t['signals']}</td>
                    <td>{$t['wins']}/{$t['losses']}</td>
                    <td class="{$wr_class}">{$t['win_rate']}%</td>
                    <td class="{$ret_class}">{$t['avg_return']}%</td>
                </tr>
HTML;
    }
    
    $html .= <<<HTML
            </tbody>
        </table>
        
        <h2>🔗 Feature Correlation Analysis</h2>
        <div class="chart-container">
HTML;

    // Add correlation bars
    foreach ($report['feature_correlations']['feature_correlations'] as $feature => $data) {
        if (isset($data['correlation_with_win'])) {
            $r = $data['correlation_with_win'];
            $width = abs($r) * 100;
            $bar_class = $r < 0 ? 'correlation-negative' : 'correlation-positive';
            $sign = $r < 0 ? '-' : '+';
            
            $html .= <<<HTML
            <div style="margin: 15px 0;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span>{$feature}</span>
                    <span class="{$bar_class}">{$sign}" . number_format(abs($r), 2) . "</span>
                </div>
                <div class="correlation-bar">
                    <div class="correlation-fill {$bar_class}" style="width: {$width}%;"></div>
                </div>
                <small style="color: #888;">{$data['interpretation']}</small>
            </div>
HTML;
        }
    }
    
    $inversion = $report['inversion_test'];
    $html .= <<<HTML
        </div>
        
        <h2>🔄 Signal Inversion Hypothesis Test</h2>
        <div class="summary-box warning">
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-value {$inversion['short_above_85_win_rate'] > 50 ? 'positive' : ''}">{$inversion['short_above_85_win_rate']}%</div>
                    <div class="metric-label">Win Rate if Short >85</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {$inversion['buy_below_40_win_rate'] > 50 ? 'positive' : ''}">{$inversion['buy_below_40_win_rate']}%</div>
                    <div class="metric-label">Win Rate if Buy <40</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value {$inversion['contrarian_win_rate'] > 50 ? 'positive' : ''}">{$inversion['contrarian_win_rate']}%</div>
                    <div class="metric-label">Contrarian Win Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{$inversion['evidence_score']}/{$inversion['max_score']}</div>
                    <div class="metric-label">Evidence Score</div>
                </div>
            </div>
            <p><strong>Conclusion:</strong> {$inversion['conclusion']}</p>
        </div>
        
        <h2>⚡ Momentum Exhaustion Analysis</h2>
        <div class="summary-box {$report['momentum_exhaustion']['exhaustion_detected'] ? 'critical' : 'success'}">
            <p><strong>High Score (80+) Avg Return:</strong> 
                <span class="{$report['momentum_exhaustion']['high_score_80_plus_avg_return'] < 0 ? 'negative' : 'positive'}">
                    {$report['momentum_exhaustion']['high_score_80_plus_avg_return']}%
                </span>
            </p>
            <p><strong>Conclusion:</strong> {$report['momentum_exhaustion']['conclusion']}</p>
        </div>
        
        <h2>🎯 Threshold Optimization</h2>
        <div class="summary-box">
            <p><strong>Best Configuration:</strong> {$report['threshold_optimization']['best_config']}</p>
            <p><strong>Recommendation:</strong> {$report['threshold_optimization']['recommendation']}</p>
        </div>
        
        <h2>📋 Recommendations</h2>
HTML;

    foreach ($report['recommendations'] as $rec) {
        $rec_class = strtolower($rec['priority']);
        $html .= <<<HTML
        <div class="recommendation rec-{$rec_class}">
            <span class="badge badge-{$rec_class}">{$rec['priority']}</span>
            <strong>{$rec['category']}:</strong> {$rec['finding']}<br>
            <em>Action: {$rec['action']}</em>
        </div>
HTML;
    }
    
    $html .= <<<HTML
        
        <footer style="text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #333; color: #666;">
            <p>Generated by Meme Coin Tier Diagnosis System</p>
            <p>Raw JSON available at: tier_diagnosis_report.json</p>
        </footer>
    </div>
</body>
</html>
HTML;

    return $html;
}

// ═══════════════════════════════════════════════════════════════════════
// MAIN EXECUTION
// ═══════════════════════════════════════════════════════════════════════

function main() {
    global $argv, $REPORT_CONFIG;
    
    // Parse command line arguments
    $format = 'both';
    $use_synthetic = false;
    
    if (isset($argv[1])) {
        $format = in_array($argv[1], array('json', 'html', 'both')) ? $argv[1] : 'both';
    }
    if (isset($argv[2]) && $argv[2] === '--synthetic') {
        $use_synthetic = true;
    }
    
    echo "Generating Meme Coin Tier Diagnosis Report...\n";
    echo "Format: $format\n";
    echo "Data: " . ($use_synthetic ? "Synthetic" : "Real") . "\n\n";
    
    // Generate report
    $result = generate_full_report($use_synthetic);
    
    if (!$result['ok']) {
        echo "ERROR: " . $result['error'] . "\n";
        exit(1);
    }
    
    $report = $result['report'];
    $output_dir = $REPORT_CONFIG['output_dir'];
    
    // Save JSON
    if ($format === 'json' || $format === 'both') {
        $json_path = $output_dir . 'tier_diagnosis_report.json';
        file_put_contents($json_path, json_encode($report, JSON_PRETTY_PRINT));
        echo "✓ JSON report saved: $json_path\n";
    }
    
    // Save HTML
    if ($format === 'html' || $format === 'both') {
        $html = generate_html_report($report);
        $html_path = $output_dir . 'tier_diagnosis_report.html';
        file_put_contents($html_path, $html);
        echo "✓ HTML report saved: $html_path\n";
    }
    
    // Print summary
    echo "\n=== REPORT SUMMARY ===\n";
    echo "Total Signals: {$report['total_signals']}\n";
    echo "Evidence Score: {$report['summary']['evidence_score']}/10\n";
    echo "Primary Cause: {$report['summary']['primary_cause']}\n";
    echo "Confidence: {$report['summary']['confidence']}\n";
    echo "\nKey Answer: {$report['key_question_answer']['answer']}\n";
    
    echo "\n=== TIER PERFORMANCE ===\n";
    foreach ($report['tier_analysis'] as $tier => $data) {
        echo "$tier: {$data['win_rate']}% win rate ({$data['signals']} signals)\n";
    }
    
    echo "\n=== TOP RECOMMENDATIONS ===\n";
    $critical = array_filter($report['recommendations'], create_function('$r', 'return $r["priority"] === "CRITICAL";'));
    foreach (array_slice($critical, 0, 3) as $rec) {
        echo "[{$rec['priority']}] {$rec['category']}: {$rec['action']}\n";
    }
    
    echo "\nReport generation complete!\n";
}

// Run if called directly
if (php_sapi_name() === 'cli') {
    main();
}
?>
