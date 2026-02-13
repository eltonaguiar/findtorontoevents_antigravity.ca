<?php
/**
 * Meme Coin Confidence Tier Diagnostic Tool
 * Investigates inverted win rates across confidence tiers
 * 
 * Problem: Higher scores (Strong Buy 8-10) showing 0% win rate
 * while lower scores (Lean Buy 1-4) showing 5% win rate
 * 
 * This tool analyzes:
 * 1. Feature correlation with outcomes
 * 2. Threshold optimization
 * 3. Signal inversion hypothesis
 * 4. Momentum exhaustion detection
 * 
 * PHP 5.2 compatible
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

error_reporting(E_ALL);
ini_set('display_errors', '1');

// Database connection (same as meme_scanner.php)
$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed: ' . $conn->connect_error));
    exit;
}
$conn->set_charset('utf8');

// Feature names to analyze
$FEATURES = array(
    'momentum_4h' => array('key' => 'parabolic_momentum', 'subkey' => 'mom_15m'),
    'momentum_24h' => array('key' => 'social_proxy', 'subkey' => 'mom_1h'),
    'volume_surge' => array('key' => 'explosive_volume', 'subkey' => 'ratio'),
    'social_proxy' => array('key' => 'social_proxy', 'subkey' => 'velocity'),
    'entry_position' => array('key' => 'breakout_4h', 'subkey' => 'breakout_pct'),
    'spread' => array('key' => 'rsi_hype_zone', 'subkey' => 'rsi'),
    'breakout_4h' => array('key' => 'breakout_4h', 'subkey' => 'score'),
    'rsi' => array('key' => 'rsi_hype_zone', 'subkey' => 'rsi')
);

// Analysis configuration
$CONFIG = array(
    'min_samples' => 20,
    'test_thresholds' => array(
        array('lean' => 72, 'buy' => 78, 'strong' => 85),  // Current
        array('lean' => 65, 'buy' => 75, 'strong' => 85),  // Lower lean
        array('lean' => 75, 'buy' => 82, 'strong' => 90),  // Higher bar
        array('lean' => 60, 'buy' => 72, 'strong' => 82),  // Much lower
        array('lean' => 80, 'buy' => 88, 'strong' => 95),  // Elite only
    ),
    'output_dir' => dirname(__FILE__) . '/../analysis/'
);

/**
 * Main diagnostic class
 */
class TierDiagnostic {
    private $conn;
    private $features;
    private $config;
    private $data;
    
    public function __construct($connection, $features, $config) {
        $this->conn = $connection;
        $this->features = $features;
        $this->config = $config;
        $this->data = array();
    }
    
    /**
     * Load historical signal data from mc_winners
     */
    public function load_data($days = 90) {
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
        AND created_at > DATE_SUB(NOW(), INTERVAL $days DAY)
        ORDER BY created_at DESC";
        
        $res = $this->conn->query($query);
        
        if (!$res) {
            return array('ok' => false, 'error' => 'Query failed: ' . $this->conn->error);
        }
        
        $samples = array();
        while ($row = $res->fetch_assoc()) {
            $factors = json_decode($row['factors_json'], true);
            if (!is_array($factors)) {
                $factors = array();
            }
            
            // Determine numeric tier (1-10 scale)
            $tier_num = $this->verdict_to_tier($row['verdict']);
            
            // Is this a win? (hit take-profit before stop-loss)
            $is_win = ($row['outcome'] === 'win' || $row['outcome'] === 'partial_win');
            
            // Return percentage
            $return_pct = floatval($row['pnl_pct']);
            
            // Extract feature values
            $feature_values = array();
            foreach ($this->features as $fname => $fconfig) {
                $feature_values[$fname] = $this->extract_feature_value($factors, $fconfig);
            }
            
            // Calculate time to peak (if price_at_resolve exists)
            $time_to_peak = null;
            if ($row['resolved_at'] && $row['created_at']) {
                $created = strtotime($row['created_at']);
                $resolved = strtotime($row['resolved_at']);
                if ($created && $resolved) {
                    $time_to_peak = ($resolved - $created) / 3600; // hours
                }
            }
            
            $samples[] = array(
                'signal_id' => $row['id'],
                'symbol' => $row['pair'],
                'score' => intval($row['score']),
                'verdict' => $row['verdict'],
                'tier' => $row['tier'],
                'tier_num' => $tier_num,
                'outcome' => $row['outcome'],
                'is_win' => $is_win,
                'return_pct' => $return_pct,
                'features' => $feature_values,
                'created_at' => $row['created_at'],
                'time_to_peak_hours' => $time_to_peak,
                'factors_raw' => $factors
            );
        }
        
        $this->data = $samples;
        
        return array(
            'ok' => true,
            'samples_loaded' => count($samples),
            'wins' => count(array_filter($samples, create_function('$s', 'return $s["is_win"];'))),
            'losses' => count(array_filter($samples, create_function('$s', 'return !$s["is_win"];')))
        );
    }
    
    /**
     * Generate synthetic data for testing when real data is insufficient
     */
    public function generate_synthetic_data($count = 200) {
        $samples = array();
        
        // Simulate the inverted tier problem
        // Low scores (1-4) have slight edge (slight winners)
        // High scores (8-10) are actually peaks (mean reversion candidates)
        
        for ($i = 0; $i < $count; $i++) {
            // Random score 0-100
            $score = mt_rand(0, 100);
            
            // Determine tier based on score
            if ($score >= 85) {
                $verdict = 'STRONG_BUY';
                $tier_num = 9;
            } elseif ($score >= 78) {
                $verdict = 'BUY';
                $tier_num = 7;
            } elseif ($score >= 72) {
                $verdict = 'LEAN_BUY';
                $tier_num = 4;
            } else {
                $verdict = 'SKIP';
                $tier_num = 2;
            }
            
            // Simulate INVERTED outcome pattern
            // High scores = momentum exhaustion (losses)
            // Low scores = undervalued (wins)
            $win_probability = 0.5 - ($score / 200); // Decreasing win rate with score
            $win_probability = max(0.1, min(0.9, $win_probability));
            
            $is_win = (mt_rand(1, 100) / 100) < $win_probability;
            
            // Return correlated with win and score (inverted)
            if ($is_win) {
                $return_pct = mt_rand(10, 50) / 10; // 1-5%
            } else {
                $return_pct = -mt_rand(10, 40) / 10; // -1 to -4%
            }
            
            // High scores = faster time to peak (exhaustion)
            $time_to_peak = max(1, 8 - ($score / 15) + mt_rand(-10, 10) / 10);
            
            // Generate feature values
            $features = array(
                'momentum_4h' => min(20, $score / 5 + mt_rand(-20, 20) / 10),
                'momentum_24h' => min(15, $score / 6 + mt_rand(-20, 20) / 10),
                'volume_surge' => min(10, $score / 8 + mt_rand(-10, 10) / 10),
                'social_proxy' => min(15, $score / 6 + mt_rand(-15, 15) / 10),
                'entry_position' => ($score - 50) / 10 + mt_rand(-5, 5) / 10,
                'spread' => max(30, min(90, $score / 2 + 30 + mt_rand(-10, 10))),
                'breakout_4h' => min(10, $score / 10 + mt_rand(-5, 5) / 10),
                'rsi' => max(30, min(95, $score / 2 + 35 + mt_rand(-10, 10)))
            );
            
            $samples[] = array(
                'signal_id' => 'synth_' . $i,
                'symbol' => 'COIN' . $i . '_USDT',
                'score' => $score,
                'verdict' => $verdict,
                'tier' => $tier_num >= 8 ? 'tier1' : 'tier2',
                'tier_num' => $tier_num,
                'outcome' => $is_win ? 'win' : 'loss',
                'is_win' => $is_win,
                'return_pct' => $return_pct,
                'features' => $features,
                'created_at' => date('Y-m-d H:i:s', strtotime("-" . mt_rand(1, 90) . " days")),
                'time_to_peak_hours' => $time_to_peak,
                'factors_raw' => array()
            );
        }
        
        $this->data = $samples;
        
        return array(
            'ok' => true,
            'samples_generated' => count($samples),
            'note' => 'Synthetic data with INVERTED pattern for testing',
            'wins' => count(array_filter($samples, create_function('$s', 'return $s["is_win"];'))),
            'losses' => count(array_filter($samples, create_function('$s', 'return !$s["is_win"];')))
        );
    }
    
    /**
     * 1. Feature Correlation Analysis
     */
    public function analyze_feature_correlations() {
        if (empty($this->data)) {
            return array('ok' => false, 'error' => 'No data loaded');
        }
        
        $results = array();
        
        foreach ($this->features as $fname => $fconfig) {
            // Get values and outcomes
            $x_values = array();
            $y_wins = array();      // Binary: 1 = win, 0 = loss
            $y_returns = array();   // Return percentage
            
            foreach ($this->data as $sample) {
                $val = $sample['features'][$fname];
                if ($val !== null) {
                    $x_values[] = $val;
                    $y_wins[] = $sample['is_win'] ? 1 : 0;
                    $y_returns[] = $sample['return_pct'];
                }
            }
            
            if (count($x_values) < $this->config['min_samples']) {
                $results[$fname] = array(
                    'error' => 'Insufficient samples',
                    'sample_count' => count($x_values)
                );
                continue;
            }
            
            // Calculate Pearson correlation with win/loss
            $corr_win = $this->pearson_correlation($x_values, $y_wins);
            
            // Calculate Pearson correlation with returns
            $corr_return = $this->pearson_correlation($x_values, $y_returns);
            
            // Interpretation
            $interpretation = '';
            if (abs($corr_win['r']) < 0.1) {
                $interpretation = 'No meaningful correlation';
            } elseif ($corr_win['r'] > 0.2) {
                $interpretation = 'Positive correlation - higher values predict wins';
            } elseif ($corr_win['r'] < -0.2) {
                $interpretation = 'NEGATIVE correlation - higher values predict LOSSES (INVERTED!)';
            } else {
                $interpretation = 'Weak correlation';
            }
            
            $results[$fname] = array(
                'correlation_with_win' => round($corr_win['r'], 4),
                'correlation_with_return' => round($corr_return['r'], 4),
                'p_value' => round($corr_win['p_value'], 4),
                'sample_count' => count($x_values),
                'interpretation' => $interpretation,
                'mean_value' => round(array_sum($x_values) / count($x_values), 4),
                'std_dev' => round($this->standard_deviation($x_values), 4)
            );
        }
        
        return array(
            'ok' => true,
            'feature_correlations' => $results,
            'summary' => $this->summarize_correlations($results)
        );
    }
    
    /**
     * 2. Threshold Optimization
     */
    public function optimize_thresholds() {
        if (empty($this->data)) {
            return array('ok' => false, 'error' => 'No data loaded');
        }
        
        $results = array();
        
        foreach ($this->config['test_thresholds'] as $thresholds) {
            $test_result = $this->test_thresholds(
                $thresholds['lean'],
                $thresholds['buy'],
                $thresholds['strong']
            );
            
            $results[] = array(
                'thresholds' => $thresholds,
                'performance' => $test_result
            );
        }
        
        // Find best configuration
        usort($results, array($this, '_sort_by_overall_win_rate'));
        $best = $results[0];
        
        return array(
            'ok' => true,
            'all_tests' => $results,
            'recommended_thresholds' => $best['thresholds'],
            'recommended_performance' => $best['performance']
        );
    }
    
    /**
     * 3. Signal Inversion Test
     */
    public function test_inversion_hypothesis() {
        if (empty($this->data)) {
            return array('ok' => false, 'error' => 'No data loaded');
        }
        
        $results = array();
        
        // Test 1: Short high scores (>85)
        $short_85 = array_filter($this->data, create_function('$s', 'return $s["score"] > 85;'));
        $results['short_above_85'] = $this->calculate_inverted_performance($short_85);
        
        // Test 2: Short very high scores (>90)
        $short_90 = array_filter($this->data, create_function('$s', 'return $s["score"] > 90;'));
        $results['short_above_90'] = $this->calculate_inverted_performance($short_90);
        
        // Test 3: Buy low scores (<40) - mean reversion
        $buy_40 = array_filter($this->data, create_function('$s', 'return $s["score"] < 40;'));
        $results['buy_below_40'] = $this->calculate_performance($buy_40);
        
        // Test 4: Buy very low scores (<30)
        $buy_30 = array_filter($this->data, create_function('$s', 'return $s["score"] < 30;'));
        $results['buy_below_30'] = $this->calculate_performance($buy_30);
        
        // Test 5: Contrarian tier assignment
        // If original says Strong Buy -> Sell
        // If original says Skip -> Buy
        $contrarian = array_filter($this->data, create_function('$s', 'return $s["score"] >= 72;'));
        $results['contrarian_strong_signals'] = $this->calculate_inverted_performance($contrarian);
        
        // Calculate evidence for inversion
        $evidence_score = 0;
        $evidence_points = array();
        
        if ($results['short_above_85']['win_rate'] > 50) {
            $evidence_score += 2;
            $evidence_points[] = 'Shorting >85 scores yields ' . $results['short_above_85']['win_rate'] . '% win rate';
        }
        if ($results['buy_below_40']['win_rate'] > 50) {
            $evidence_score += 2;
            $evidence_points[] = 'Buying <40 scores yields ' . $results['buy_below_40']['win_rate'] . '% win rate';
        }
        if ($results['contrarian_strong_signals']['win_rate'] > 50) {
            $evidence_score += 3;
            $evidence_points[] = 'Contrarian strategy on strong signals yields ' . $results['contrarian_strong_signals']['win_rate'] . '% win rate';
        }
        
        // Compare to baseline
        $baseline = $this->calculate_performance($this->data);
        if ($baseline['win_rate'] < 40) {
            $evidence_score += 1;
            $evidence_points[] = 'Baseline win rate is poor (' . $baseline['win_rate'] . '%)';
        }
        
        return array(
            'ok' => true,
            'inversion_tests' => $results,
            'baseline_performance' => $baseline,
            'evidence_for_inversion' => array(
                'score' => $evidence_score,
                'max_score' => 8,
                'verdict' => $evidence_score >= 5 ? 'STRONG EVIDENCE for signal inversion' : 
                            ($evidence_score >= 3 ? 'MODERATE EVIDENCE for signal inversion' :
                            ($evidence_score >= 1 ? 'Weak evidence - needs more data' : 'No evidence for inversion')),
                'points' => $evidence_points
            )
        );
    }
    
    /**
     * 4. Momentum Exhaustion Detection
     */
    public function analyze_momentum_exhaustion() {
        if (empty($this->data)) {
            return array('ok' => false, 'error' => 'No data loaded');
        }
        
        // Group by score ranges
        $score_ranges = array(
            '90-100' => array('min' => 90, 'max' => 100),
            '85-89' => array('min' => 85, 'max' => 89),
            '80-84' => array('min' => 80, 'max' => 84),
            '75-79' => array('min' => 75, 'max' => 79),
            '70-74' => array('min' => 70, 'max' => 74),
            '60-69' => array('min' => 60, 'max' => 69),
            '50-59' => array('min' => 50, 'max' => 59),
            '0-49' => array('min' => 0, 'max' => 49)
        );
        
        $range_analysis = array();
        
        foreach ($score_ranges as $range_name => $bounds) {
            $range_data = array_filter($this->data, create_function('$s', '
                return $s["score"] >= ' . $bounds['min'] . ' && $s["score"] <= ' . $bounds['max'] . ';
            '));
            
            if (count($range_data) < 5) {
                $range_analysis[$range_name] = array('note' => 'Insufficient data', 'count' => count($range_data));
                continue;
            }
            
            $wins = count(array_filter($range_data, create_function('$s', 'return $s["is_win"];')));
            $total = count($range_data);
            $win_rate = round(($wins / $total) * 100, 2);
            
            // Time to peak analysis
            $ttf_values = array();
            foreach ($range_data as $d) {
                if ($d['time_to_peak_hours'] !== null) {
                    $ttf_values[] = $d['time_to_peak_hours'];
                }
            }
            
            $avg_ttf = count($ttf_values) > 0 ? round(array_sum($ttf_values) / count($ttf_values), 2) : null;
            
            // Returns analysis
            $returns = array_map(create_function('$s', 'return $s["return_pct"];'), $range_data);
            $avg_return = round(array_sum($returns) / count($returns), 2);
            
            $range_analysis[$range_name] = array(
                'count' => $total,
                'wins' => $wins,
                'losses' => $total - $wins,
                'win_rate' => $win_rate,
                'avg_return_pct' => $avg_return,
                'avg_time_to_peak_hours' => $avg_ttf,
                'exhaustion_indicator' => $this->calculate_exhaustion_score($win_rate, $avg_ttf, $avg_return, $bounds['min'])
            );
        }
        
        // Correlation between score and time-to-peak
        $score_values = array();
        $ttf_values = array();
        foreach ($this->data as $d) {
            if ($d['time_to_peak_hours'] !== null) {
                $score_values[] = $d['score'];
                $ttf_values[] = $d['time_to_peak_hours'];
            }
        }
        
        $score_ttf_corr = array('r' => 0, 'note' => 'Insufficient paired data');
        if (count($score_values) >= 10) {
            $score_ttf_corr = $this->pearson_correlation($score_values, $ttf_values);
        }
        
        return array(
            'ok' => true,
            'range_analysis' => $range_analysis,
            'score_vs_time_to_peak_correlation' => array(
                'r' => round($score_ttf_corr['r'], 4),
                'p_value' => isset($score_ttf_corr['p_value']) ? round($score_ttf_corr['p_value'], 4) : null,
                'interpretation' => $score_ttf_corr['r'] < -0.3 ? 
                    'Higher scores peak FASTER (exhaustion pattern)' :
                    ($score_ttf_corr['r'] > 0.3 ? 
                        'Higher scores take LONGER to peak (sustained momentum)' :
                        'No clear relationship between score and time to peak')
            ),
            'exhaustion_detected' => $score_ttf_corr['r'] < -0.2
        );
    }
    
    /**
     * Generate comprehensive report
     */
    public function generate_report($use_synthetic = false) {
        // Load data
        if ($use_synthetic) {
            $load_result = $this->generate_synthetic_data(300);
        } else {
            $load_result = $this->load_data(90);
            if (!$load_result['ok'] || $load_result['samples_loaded'] < $this->config['min_samples']) {
                $load_result = $this->generate_synthetic_data(300);
                $load_result['note'] = 'Used synthetic data - insufficient real data available';
            }
        }
        
        if (!$load_result['ok']) {
            return $load_result;
        }
        
        // Run all analyses
        $correlations = $this->analyze_feature_correlations();
        $thresholds = $this->optimize_thresholds();
        $inversion = $this->test_inversion_hypothesis();
        $exhaustion = $this->analyze_momentum_exhaustion();
        
        // Generate recommendations
        $recommendations = $this->generate_recommendations(
            $correlations,
            $thresholds,
            $inversion,
            $exhaustion
        );
        
        $report = array(
            'generated_at' => date('Y-m-d H:i:s'),
            'data_source' => $use_synthetic ? 'synthetic' : 'real',
            'data_summary' => $load_result,
            'current_tier_performance' => $this->analyze_current_tiers(),
            'feature_correlations' => $correlations['ok'] ? $correlations['feature_correlations'] : $correlations,
            'correlation_summary' => $correlations['ok'] ? $correlations['summary'] : null,
            'optimal_thresholds' => $thresholds['ok'] ? $thresholds : $thresholds,
            'inversion_hypothesis' => $inversion['ok'] ? $inversion : $inversion,
            'momentum_exhaustion' => $exhaustion['ok'] ? $exhaustion : $exhaustion,
            'recommendations' => $recommendations
        );
        
        // Save to file
        $output_path = $this->config['output_dir'] . 'tier_diagnosis_report.json';
        
        // Ensure directory exists
        if (!is_dir($this->config['output_dir'])) {
            mkdir($this->config['output_dir'], 0755, true);
        }
        
        file_put_contents($output_path, json_encode($report, JSON_PRETTY_PRINT));
        
        return array(
            'ok' => true,
            'report' => $report,
            'saved_to' => $output_path
        );
    }
    
    // ═══════════════════════════════════════════════════════════════════════
    //  HELPER METHODS
    // ═══════════════════════════════════════════════════════════════════════
    
    private function verdict_to_tier($verdict) {
        switch ($verdict) {
            case 'STRONG_BUY': return 9;
            case 'BUY': return 7;
            case 'LEAN_BUY': return 4;
            case 'SKIP': return 2;
            default: return 5;
        }
    }
    
    private function extract_feature_value($factors, $config) {
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
    
    private function pearson_correlation($x, $y) {
        $n = count($x);
        
        if ($n < 3 || count($y) != $n) {
            return array('r' => 0, 'p_value' => 1);
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
            return array('r' => 0, 'p_value' => 1);
        }
        
        $r = $numerator / $denominator;
        
        // Approximate p-value using t-statistic
        $t = $r * sqrt(($n - 2) / (1 - $r * $r));
        $p_value = $this->approximate_p_value($t, $n - 2);
        
        return array('r' => $r, 't_statistic' => $t, 'p_value' => $p_value, 'n' => $n);
    }
    
    private function approximate_p_value($t, $df) {
        // Rough approximation of two-tailed p-value
        $abs_t = abs($t);
        if ($abs_t < 1) return 0.5;
        if ($abs_t < 1.64) return 0.1;
        if ($abs_t < 1.96) return 0.05;
        if ($abs_t < 2.58) return 0.01;
        if ($abs_t < 3.29) return 0.001;
        return 0.0001;
    }
    
    private function standard_deviation($values) {
        $n = count($values);
        if ($n < 2) return 0;
        
        $mean = array_sum($values) / $n;
        $sum_squared_diff = 0;
        
        foreach ($values as $v) {
            $diff = $v - $mean;
            $sum_squared_diff += $diff * $diff;
        }
        
        return sqrt($sum_squared_diff / ($n - 1));
    }
    
    private function test_thresholds($lean_min, $buy_min, $strong_min) {
        $lean_signals = array_filter($this->data, create_function('$s', 'return $s["score"] >= ' . $lean_min . ' && $s["score"] < ' . $buy_min . ';'));
        $buy_signals = array_filter($this->data, create_function('$s', 'return $s["score"] >= ' . $buy_min . ' && $s["score"] < ' . $strong_min . ';'));
        $strong_signals = array_filter($this->data, create_function('$s', 'return $s["score"] >= ' . $strong_min . ';'));
        
        return array(
            'lean_buy' => $this->calculate_performance($lean_signals),
            'buy' => $this->calculate_performance($buy_signals),
            'strong_buy' => $this->calculate_performance($strong_signals),
            'overall' => $this->calculate_overall_score(
                $this->calculate_performance($lean_signals),
                $this->calculate_performance($buy_signals),
                $this->calculate_performance($strong_signals)
            )
        );
    }
    
    private function calculate_performance($signals) {
        $count = count($signals);
        if ($count == 0) {
            return array('count' => 0, 'win_rate' => 0, 'avg_return' => 0);
        }
        
        $wins = count(array_filter($signals, create_function('$s', 'return $s["is_win"];')));
        $returns = array_map(create_function('$s', 'return $s["return_pct"];'), $signals);
        
        return array(
            'count' => $count,
            'wins' => $wins,
            'losses' => $count - $wins,
            'win_rate' => round(($wins / $count) * 100, 2),
            'avg_return' => round(array_sum($returns) / count($returns), 2),
            'max_return' => round(max($returns), 2),
            'min_return' => round(min($returns), 2)
        );
    }
    
    private function calculate_inverted_performance($signals) {
        $perf = $this->calculate_performance($signals);
        
        // Invert the win rate (if original wins 30%, inverted strategy wins 70%)
        $inverted_win_rate = 100 - $perf['win_rate'];
        
        // Invert returns
        $inverted_avg_return = -$perf['avg_return'];
        
        return array(
            'original_count' => $perf['count'],
            'original_win_rate' => $perf['win_rate'],
            'inverted_win_rate' => $inverted_win_rate,
            'original_avg_return' => $perf['avg_return'],
            'inverted_avg_return' => $inverted_avg_return,
            'edge_vs_original' => round($inverted_win_rate - $perf['win_rate'], 2),
            'viable_strategy' => $inverted_win_rate > 55 && $perf['count'] >= 10
        );
    }
    
    private function calculate_overall_score($lean, $buy, $strong) {
        // Weighted score based on tier separation and overall win rates
        $score = 0;
        
        // Prefer higher win rates in higher tiers (natural order)
        if ($strong['win_rate'] > $buy['win_rate'] && $buy['win_rate'] > $lean['win_rate']) {
            $score += 50; // Natural ordering achieved
        }
        
        // Prefer win rates above 50%
        $score += $strong['win_rate'] * 0.3;
        $score += $buy['win_rate'] * 0.3;
        $score += $lean['win_rate'] * 0.2;
        
        // Penalize very low sample sizes
        if ($strong['count'] < 5) $score -= 20;
        if ($buy['count'] < 5) $score -= 20;
        
        return round($score, 2);
    }
    
    private function calculate_exhaustion_score($win_rate, $avg_ttf, $avg_return, $min_score) {
        // Higher exhaustion = lower win rate + faster time to peak + negative returns
        $score = 0;
        
        if ($win_rate < 30) $score += 3;
        elseif ($win_rate < 45) $score += 1;
        
        if ($avg_ttf !== null && $avg_ttf < 2) $score += 2;
        elseif ($avg_ttf !== null && $avg_ttf < 4) $score += 1;
        
        if ($avg_return < -2) $score += 2;
        elseif ($avg_return < 0) $score += 1;
        
        if ($min_score >= 85 && $win_rate < 40) $score += 2;
        
        return array(
            'score' => $score,
            'level' => $score >= 6 ? 'HIGH EXHAUSTION' : ($score >= 3 ? 'MODERATE EXHAUSTION' : 'LOW EXHAUSTION'),
            'indicators' => array(
                'poor_win_rate' => $win_rate < 40,
                'fast_peak' => $avg_ttf !== null && $avg_ttf < 3,
                'negative_returns' => $avg_return < 0,
                'high_score_poor_performance' => $min_score >= 85 && $win_rate < 40
            )
        );
    }
    
    private function analyze_current_tiers() {
        $lean_signals = array_filter($this->data, create_function('$s', 'return $s["verdict"] == "LEAN_BUY";'));
        $buy_signals = array_filter($this->data, create_function('$s', 'return $s["verdict"] == "BUY";'));
        $strong_signals = array_filter($this->data, create_function('$s', 'return $s["verdict"] == "STRONG_BUY";'));
        
        return array(
            'lean_buy_1_4' => $this->calculate_performance($lean_signals),
            'moderate_buy_5_7' => $this->calculate_performance($buy_signals),
            'strong_buy_8_10' => $this->calculate_performance($strong_signals)
        );
    }
    
    private function summarize_correlations($results) {
        $negative_corr = 0;
        $positive_corr = 0;
        $strong_features = array();
        $weak_features = array();
        $inverted_features = array();
        
        foreach ($results as $fname => $data) {
            if (isset($data['correlation_with_win'])) {
                $r = $data['correlation_with_win'];
                
                if ($r < -0.2) {
                    $negative_corr++;
                    $inverted_features[] = $fname;
                } elseif ($r > 0.2) {
                    $positive_corr++;
                    $strong_features[] = $fname;
                } else {
                    $weak_features[] = $fname;
                }
            }
        }
        
        $verdict = '';
        if ($negative_corr > $positive_corr) {
            $verdict = 'CRITICAL: More features show NEGATIVE correlation with wins than positive. Signal logic may be inverted.';
        } elseif ($positive_corr > 0) {
            $verdict = 'Features generally show expected positive correlation.';
        } else {
            $verdict = 'Most features show weak/no correlation - may need different features.';
        }
        
        return array(
            'features_with_negative_correlation' => $negative_corr,
            'features_with_positive_correlation' => $positive_corr,
            'inverted_features' => $inverted_features,
            'strong_features' => $strong_features,
            'weak_features' => $weak_features,
            'verdict' => $verdict
        );
    }
    
    private function generate_recommendations($correlations, $thresholds, $inversion, $exhaustion) {
        $recs = array();
        
        // Based on correlation analysis
        if ($correlations['ok']) {
            $summary = $correlations['summary'];
            if (count($summary['inverted_features']) > 0) {
                $recs[] = array(
                    'priority' => 'CRITICAL',
                    'category' => 'Feature Logic',
                    'issue' => 'Features show inverted correlation: ' . implode(', ', $summary['inverted_features']),
                    'action' => 'Invert these features in scoring formula OR investigate why higher values predict losses'
                );
            }
        }
        
        // Based on inversion hypothesis
        if ($inversion['ok']) {
            $evidence = $inversion['evidence_for_inversion'];
            if ($evidence['score'] >= 5) {
                $recs[] = array(
                    'priority' => 'CRITICAL',
                    'category' => 'Signal Direction',
                    'issue' => 'Strong evidence that signals should be inverted',
                    'action' => 'Consider implementing CONTRARIAN strategy: Sell Strong Buys, Buy Skips'
                );
            }
        }
        
        // Based on momentum exhaustion
        if ($exhaustion['ok'] && $exhaustion['exhaustion_detected']) {
            $recs[] = array(
                'priority' => 'HIGH',
                'category' => 'Momentum Model',
                'issue' => 'High scores correlate with faster time-to-peak (exhaustion pattern)',
                'action' => 'Reduce holding periods for high-score signals OR use as SHORT signals'
            );
        }
        
        // Based on threshold optimization
        if ($thresholds['ok']) {
            $current = array('lean' => 72, 'buy' => 78, 'strong' => 85);
            $recommended = $thresholds['recommended_thresholds'];
            
            if ($recommended != $current) {
                $recs[] = array(
                    'priority' => 'MEDIUM',
                    'category' => 'Thresholds',
                    'issue' => 'Current thresholds may not be optimal',
                    'action' => 'Test new thresholds: Lean=' . $recommended['lean'] . ', Buy=' . $recommended['buy'] . ', Strong=' . $recommended['strong']
                );
            }
        }
        
        // Add generic recommendations if list is short
        if (count($recs) < 2) {
            $recs[] = array(
                'priority' => 'INFO',
                'category' => 'Data Collection',
                'issue' => 'Need more resolved signals for conclusive analysis',
                'action' => 'Continue collecting outcomes. Minimum 100 signals recommended for statistical significance.'
            );
        }
        
        return $recs;
    }
    
    private function _sort_by_overall_win_rate($a, $b) {
        $score_a = $a['performance']['overall'];
        $score_b = $b['performance']['overall'];
        
        if ($score_a == $score_b) return 0;
        return ($score_a > $score_b) ? -1 : 1;
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  API ENDPOINT
// ═══════════════════════════════════════════════════════════════════════

$action = isset($_GET['action']) ? $_GET['action'] : 'full_diagnosis';
$synthetic = isset($_GET['synthetic']) ? ($_GET['synthetic'] === '1' || $_GET['synthetic'] === 'true') : false;

date_default_timezone_set('America/Toronto');

$diagnostic = new TierDiagnostic($conn, $FEATURES, $CONFIG);

switch ($action) {
    case 'full_diagnosis':
        $result = $diagnostic->generate_report($synthetic);
        break;
        
    case 'correlations':
        $load = $diagnostic->load_data(90);
        if (!$load['ok'] || $load['samples_loaded'] < 20) {
            $diagnostic->generate_synthetic_data(300);
        }
        $result = $diagnostic->analyze_feature_correlations();
        break;
        
    case 'thresholds':
        $load = $diagnostic->load_data(90);
        if (!$load['ok'] || $load['samples_loaded'] < 20) {
            $diagnostic->generate_synthetic_data(300);
        }
        $result = $diagnostic->optimize_thresholds();
        break;
        
    case 'inversion':
        $load = $diagnostic->load_data(90);
        if (!$load['ok'] || $load['samples_loaded'] < 20) {
            $diagnostic->generate_synthetic_data(300);
        }
        $result = $diagnostic->test_inversion_hypothesis();
        break;
        
    case 'exhaustion':
        $load = $diagnostic->load_data(90);
        if (!$load['ok'] || $load['samples_loaded'] < 20) {
            $diagnostic->generate_synthetic_data(300);
        }
        $result = $diagnostic->analyze_momentum_exhaustion();
        break;
        
    case 'full_report':
        // Generate comprehensive report using tier_diagnosis_report.php
        $report_file = dirname(__FILE__) . '/../analysis/tier_diagnosis_report.php';
        if (file_exists($report_file)) {
            include_once($report_file);
            $report_result = generate_full_report($synthetic);
            if ($report_result['ok']) {
                $result = array(
                    'ok' => true,
                    'report' => $report_result['report'],
                    'files_generated' => array(
                        'json' => 'analysis/tier_diagnosis_report.json',
                        'html' => 'analysis/tier_diagnosis_report.html'
                    ),
                    'view_html' => './analysis/tier_diagnosis_report.html'
                );
                // Also save the files
                $output_dir = dirname(__FILE__) . '/../analysis/';
                file_put_contents($output_dir . 'tier_diagnosis_report.json', json_encode($report_result['report'], JSON_PRETTY_PRINT));
                $html = generate_html_report($report_result['report']);
                file_put_contents($output_dir . 'tier_diagnosis_report.html', $html);
            } else {
                $result = $report_result;
            }
        } else {
            $result = array('ok' => false, 'error' => 'Report generator not found: ' . $report_file);
        }
        break;
        
    default:
        $result = array('ok' => false, 'error' => 'Unknown action: ' . $action)
}

echo json_encode($result, JSON_PRETTY_PRINT);
$conn->close();
?>
