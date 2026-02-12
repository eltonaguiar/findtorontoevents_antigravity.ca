<?php
/**
 * Meme Coin Machine Learning Engine
 * Adaptive scoring system that learns from historical signal outcomes
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/../live-monitor/api/sports_db_connect.php';

class MemeMLEngine {
    private $conn;
    private $feature_names = array(
        'explosive_volume',
        'parabolic_momentum', 
        'rsi_hype_zone',
        'social_momentum_proxy',
        'volume_concentration',
        'breakout_4h',
        'low_market_cap_bonus'
    );
    
    // Default weights (will be overridden by learned weights)
    private $default_weights = array(
        'explosive_volume' => 0.25,
        'parabolic_momentum' => 0.20,
        'rsi_hype_zone' => 0.15,
        'social_momentum_proxy' => 0.15,
        'volume_concentration' => 0.10,
        'breakout_4h' => 0.10,
        'low_market_cap_bonus' => 0.05
    );
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->_ensure_tables();
    }
    
    /**
     * Train the ML model on historical signal data
     */
    public function train_model($min_samples = 50) {
        // Get historical signals with known outcomes
        $query = "SELECT 
            s.signal_id,
            s.coin_symbol,
            s.explosive_volume,
            s.parabolic_momentum,
            s.rsi_hype_zone,
            s.social_momentum_proxy,
            s.volume_concentration,
            s.breakout_4h,
            s.low_market_cap_bonus,
            s.total_score,
            s.tier,
            r.outcome,
            r.profit_loss_pct,
            r.max_profit_pct,
            r.max_loss_pct,
            r.resolved_at
        FROM meme_signals s
        JOIN meme_signal_results r ON s.signal_id = r.signal_id
        WHERE r.outcome IS NOT NULL
        AND s.created_at > DATE_SUB(NOW(), INTERVAL 90 DAY)
        ORDER BY s.created_at DESC
        LIMIT 1000";
        
        $res = $this->conn->query($query);
        if (!$res || $res->num_rows < $min_samples) {
            return array(
                'ok' => false,
                'error' => 'Insufficient training data. Need ' . $min_samples . ' samples, found ' . ($res ? $res->num_rows : 0),
                'recommendation' => 'Continue collecting signal data. Current model will use default weights.'
            );
        }
        
        $samples = array();
        $winners = 0;
        $losers = 0;
        
        while ($row = $res->fetch_assoc()) {
            $features = array(
                'explosive_volume' => (float)$row['explosive_volume'],
                'parabolic_momentum' => (float)$row['parabolic_momentum'],
                'rsi_hype_zone' => (float)$row['rsi_hype_zone'],
                'social_momentum_proxy' => (float)$row['social_momentum_proxy'],
                'volume_concentration' => (float)$row['volume_concentration'],
                'breakout_4h' => (float)$row['breakout_4h'],
                'low_market_cap_bonus' => (float)$row['low_market_cap_bonus'],
                'tier' => $row['tier'] === 'tier1' ? 1 : 2
            );
            
            $outcome = $row['outcome'] === 'win' ? 1 : 0;
            if ($outcome === 1) $winners++;
            else $losers++;
            
            $samples[] = array(
                'features' => $features,
                'outcome' => $outcome,
                'profit_loss' => (float)$row['profit_loss_pct'],
                'coin' => $row['coin_symbol']
            );
        }
        
        // Calculate feature importance using correlation analysis
        $feature_importance = $this->_calculate_feature_importance($samples);
        
        // Optimize weights using gradient descent approximation
        $optimized_weights = $this->_optimize_weights($samples, $feature_importance);
        
        // Calculate model performance metrics
        $metrics = $this->_calculate_metrics($samples, $optimized_weights);
        
        // Store the trained model
        $model_id = $this->_save_model($optimized_weights, $feature_importance, $metrics, count($samples));
        
        return array(
            'ok' => true,
            'model_id' => $model_id,
            'samples_used' => count($samples),
            'winners' => $winners,
            'losers' => $losers,
            'base_win_rate' => round($winners / count($samples) * 100, 2),
            'optimized_weights' => $optimized_weights,
            'feature_importance' => $feature_importance,
            'metrics' => $metrics
        );
    }
    
    /**
     * Predict win probability for a new signal
     */
    public function predict($signal_data) {
        // Get latest model weights
        $weights = $this->_get_latest_weights();
        
        // Normalize features to 0-1 scale
        $normalized = $this->_normalize_features($signal_data);
        
        // Calculate weighted score
        $ml_score = 0;
        $feature_contributions = array();
        
        foreach ($this->feature_names as $feature) {
            $weight = isset($weights[$feature]) ? $weights[$feature] : $this->default_weights[$feature];
            $value = isset($normalized[$feature]) ? $normalized[$feature] : 0;
            $contribution = $weight * $value;
            $ml_score += $contribution;
            $feature_contributions[$feature] = array(
                'raw_value' => $signal_data[$feature],
                'normalized' => $value,
                'weight' => $weight,
                'contribution' => $contribution
            );
        }
        
        // Convert to probability using sigmoid function
        $win_probability = $this->_sigmoid($ml_score * 10 - 5); // Scale to 0-1 range
        
        // Get confidence interval based on training data
        $confidence = $this->_calculate_confidence($ml_score);
        
        // Determine recommendation
        $recommendation = $this->_get_recommendation($win_probability, $confidence);
        
        // Find similar historical signals
        $similar_signals = $this->_find_similar_signals($normalized, 5);
        
        return array(
            'ok' => true,
            'ml_score' => round($ml_score * 100, 2),
            'win_probability' => round($win_probability * 100, 2),
            'confidence' => $confidence,
            'recommendation' => $recommendation,
            'feature_contributions' => $feature_contributions,
            'similar_signals' => $similar_signals,
            'model_version' => $weights['model_id']
        );
    }
    
    /**
     * Batch predict for multiple signals
     */
    public function batch_predict($signals) {
        $predictions = array();
        
        foreach ($signals as $signal) {
            $pred = $this->predict($signal);
            $predictions[] = array(
                'coin' => $signal['coin_symbol'],
                'prediction' => $pred
            );
        }
        
        // Sort by win probability
        usort($predictions, array($this, '_sort_by_probability'));
        
        return array(
            'ok' => true,
            'count' => count($predictions),
            'predictions' => $predictions
        );
    }
    
    /**
     * Get model performance over time
     */
    public function get_model_performance($model_id = null) {
        if (!$model_id) {
            // Get latest model
            $res = $this->conn->query("SELECT model_id FROM meme_ml_models ORDER BY created_at DESC LIMIT 1");
            if ($res && $row = $res->fetch_assoc()) {
                $model_id = $row['model_id'];
            } else {
                return array('ok' => false, 'error' => 'No trained models found');
            }
        }
        
        $esc_id = $this->conn->real_escape_string($model_id);
        
        // Get model details
        $res = $this->conn->query("SELECT * FROM meme_ml_models WHERE model_id = '$esc_id'");
        if (!$res || $res->num_rows === 0) {
            return array('ok' => false, 'error' => 'Model not found');
        }
        
        $model = $res->fetch_assoc();
        
        // Get predictions made by this model
        $res = $this->conn->query("SELECT 
            COUNT(*) as total_predictions,
            SUM(CASE WHEN actual_outcome = 1 THEN 1 ELSE 0 END) as correct_predictions,
            AVG(CASE WHEN actual_outcome = 1 THEN predicted_probability ELSE NULL END) as avg_prob_correct,
            AVG(CASE WHEN actual_outcome = 0 THEN predicted_probability ELSE NULL END) as avg_prob_incorrect
        FROM meme_ml_predictions
        WHERE model_id = '$esc_id'
        AND actual_outcome IS NOT NULL");
        
        $performance = $res ? $res->fetch_assoc() : array();
        
        return array(
            'ok' => true,
            'model' => $model,
            'performance' => $performance
        );
    }
    
    /**
     * Compare ML predictions vs rule-based scores
     */
    public function compare_methods($days = 30) {
        $esc_days = (int)$days;
        
        $query = "SELECT 
            s.signal_id,
            s.total_score as rule_based_score,
            p.predicted_probability as ml_probability,
            r.outcome,
            r.profit_loss_pct
        FROM meme_signals s
        JOIN meme_ml_predictions p ON s.signal_id = p.signal_id
        JOIN meme_signal_results r ON s.signal_id = r.signal_id
        WHERE s.created_at > DATE_SUB(NOW(), INTERVAL $esc_days DAY)
        AND r.outcome IS NOT NULL
        ORDER BY s.created_at DESC";
        
        $res = $this->conn->query($query);
        
        $comparison = array(
            'rule_based' => array('wins' => 0, 'losses' => 0, 'avg_pl' => 0),
            'ml_based' => array('wins' => 0, 'losses' => 0, 'avg_pl' => 0),
            'both_agree' => array('wins' => 0, 'losses' => 0),
            'disagree' => array('wins' => 0, 'losses' => 0)
        );
        
        $rule_pl = array();
        $ml_pl = array();
        
        while ($res && $row = $res->fetch_assoc()) {
            $rule_win = $row['rule_based_score'] >= 70; // Traditional threshold
            $ml_win = $row['ml_probability'] >= 0.5;
            $actual_win = $row['outcome'] === 'win';
            
            if ($rule_win) {
                if ($actual_win) $comparison['rule_based']['wins']++;
                else $comparison['rule_based']['losses']++;
                $rule_pl[] = $row['profit_loss_pct'];
            }
            
            if ($ml_win) {
                if ($actual_win) $comparison['ml_based']['wins']++;
                else $comparison['ml_based']['losses']++;
                $ml_pl[] = $row['profit_loss_pct'];
            }
            
            if ($rule_win === $ml_win) {
                if ($actual_win) $comparison['both_agree']['wins']++;
                else $comparison['both_agree']['losses']++;
            } else {
                if ($actual_win) $comparison['disagree']['wins']++;
                else $comparison['disagree']['losses']++;
            }
        }
        
        $comparison['rule_based']['avg_pl'] = !empty($rule_pl) ? round(array_sum($rule_pl) / count($rule_pl), 2) : 0;
        $comparison['ml_based']['avg_pl'] = !empty($ml_pl) ? round(array_sum($ml_pl) / count($ml_pl), 2) : 0;
        $comparison['rule_based']['win_rate'] = ($comparison['rule_based']['wins'] + $comparison['rule_based']['losses']) > 0 
            ? round($comparison['rule_based']['wins'] / ($comparison['rule_based']['wins'] + $comparison['rule_based']['losses']) * 100, 2)
            : 0;
        $comparison['ml_based']['win_rate'] = ($comparison['ml_based']['wins'] + $comparison['ml_based']['losses']) > 0
            ? round($comparison['ml_based']['wins'] / ($comparison['ml_based']['wins'] + $comparison['ml_based']['losses']) * 100, 2)
            : 0;
        
        return array('ok' => true, 'comparison' => $comparison, 'total_signals' => count($rule_pl) + count($ml_pl));
    }
    
    /**
     * Auto-retrain model on schedule
     */
    public function auto_retrain() {
        // Check if we need to retrain (every 7 days or 50 new signals)
        $res = $this->conn->query("SELECT 
            MAX(created_at) as last_train,
            COUNT(*) as models
        FROM meme_ml_models");
        
        $last_train = null;
        if ($res && $row = $res->fetch_assoc()) {
            $last_train = $row['last_train'];
        }
        
        // Count new signals since last train
        $new_signals = 0;
        if ($last_train) {
            $esc_date = $this->conn->real_escape_string($last_train);
            $res = $this->conn->query("SELECT COUNT(*) as cnt 
                FROM meme_signal_results 
                WHERE resolved_at > '$esc_date' 
                AND outcome IS NOT NULL");
            if ($res && $row = $res->fetch_assoc()) {
                $new_signals = $row['cnt'];
            }
        }
        
        $should_retrain = false;
        $reason = '';
        
        if (!$last_train) {
            $should_retrain = true;
            $reason = 'No existing model';
        } elseif ($new_signals >= 50) {
            $should_retrain = true;
            $reason = "50+ new signals ($new_signals)";
        } else {
            $days_since = floor((time() - strtotime($last_train)) / 86400);
            if ($days_since >= 7) {
                $should_retrain = true;
                $reason = "$days_since days since last training";
            }
        }
        
        if ($should_retrain) {
            $result = $this->train_model(30);
            $result['retrain_triggered'] = true;
            $result['retrain_reason'] = $reason;
            return $result;
        }
        
        return array(
            'ok' => true,
            'retrain_triggered' => false,
            'last_train' => $last_train,
            'new_signals_since' => $new_signals,
            'message' => 'Model is current, no retraining needed'
        );
    }
    
    // ════════════════════════════════════════════════════════════
    //  Private ML Methods
    // ════════════════════════════════════════════════════════════
    
    private function _calculate_feature_importance($samples) {
        $importance = array();
        
        foreach ($this->feature_names as $feature) {
            // Calculate correlation with outcome
            $sum_x = 0;
            $sum_y = 0;
            $sum_xy = 0;
            $sum_x2 = 0;
            $sum_y2 = 0;
            $n = count($samples);
            
            foreach ($samples as $sample) {
                $x = $sample['features'][$feature];
                $y = $sample['outcome'];
                $sum_x += $x;
                $sum_y += $y;
                $sum_xy += $x * $y;
                $sum_x2 += $x * $x;
                $sum_y2 += $y * $y;
            }
            
            // Pearson correlation coefficient
            $numerator = $n * $sum_xy - $sum_x * $sum_y;
            $denominator = sqrt(($n * $sum_x2 - $sum_x * $sum_x) * ($n * $sum_y2 - $sum_y * $sum_y));
            
            $correlation = $denominator != 0 ? $numerator / $denominator : 0;
            $importance[$feature] = abs($correlation);
        }
        
        // Normalize to sum to 1
        $total = array_sum($importance);
        if ($total > 0) {
            foreach ($importance as $feature => $value) {
                $importance[$feature] = round($value / $total, 4);
            }
        }
        
        return $importance;
    }
    
    private function _optimize_weights($samples, $feature_importance) {
        // Start with feature importance as base weights
        $weights = $feature_importance;
        
        // Simple gradient descent to optimize
        $learning_rate = 0.01;
        $iterations = 100;
        
        for ($i = 0; $i < $iterations; $i++) {
            $gradients = array();
            
            foreach ($this->feature_names as $feature) {
                $gradient = 0;
                
                foreach ($samples as $sample) {
                    $prediction = $this->_predict_with_weights($sample['features'], $weights);
                    $error = $prediction - $sample['outcome'];
                    $gradient += $error * $sample['features'][$feature];
                }
                
                $gradients[$feature] = $gradient / count($samples);
            }
            
            // Update weights
            foreach ($this->feature_names as $feature) {
                $weights[$feature] -= $learning_rate * $gradients[$feature];
                // Keep weights positive
                $weights[$feature] = max(0.01, $weights[$feature]);
            }
            
            // Normalize
            $total = array_sum($weights);
            foreach ($weights as $feature => $value) {
                $weights[$feature] = round($value / $total, 4);
            }
        }
        
        return $weights;
    }
    
    private function _predict_with_weights($features, $weights) {
        $score = 0;
        foreach ($features as $feature => $value) {
            if (isset($weights[$feature])) {
                $score += $weights[$feature] * $value;
            }
        }
        return $this->_sigmoid($score * 10 - 5);
    }
    
    private function _sigmoid($x) {
        return 1 / (1 + exp(-$x));
    }
    
    private function _calculate_metrics($samples, $weights) {
        $predictions = array();
        $correct = 0;
        $true_positives = 0;
        $false_positives = 0;
        $true_negatives = 0;
        $false_negatives = 0;
        
        foreach ($samples as $sample) {
            $pred_prob = $this->_predict_with_weights($sample['features'], $weights);
            $pred_class = $pred_prob >= 0.5 ? 1 : 0;
            $actual = $sample['outcome'];
            
            $predictions[] = $pred_prob;
            
            if ($pred_class === $actual) $correct++;
            if ($pred_class === 1 && $actual === 1) $true_positives++;
            if ($pred_class === 1 && $actual === 0) $false_positives++;
            if ($pred_class === 0 && $actual === 0) $true_negatives++;
            if ($pred_class === 0 && $actual === 1) $false_negatives++;
        }
        
        $n = count($samples);
        $accuracy = $n > 0 ? $correct / $n : 0;
        
        $precision = ($true_positives + $false_positives) > 0 
            ? $true_positives / ($true_positives + $false_positives) 
            : 0;
        $recall = ($true_positives + $false_negatives) > 0
            ? $true_positives / ($true_positives + $false_negatives)
            : 0;
        $f1 = ($precision + $recall) > 0
            ? 2 * ($precision * $recall) / ($precision + $recall)
            : 0;
        
        return array(
            'accuracy' => round($accuracy, 4),
            'precision' => round($precision, 4),
            'recall' => round($recall, 4),
            'f1_score' => round($f1, 4),
            'samples' => $n
        );
    }
    
    private function _normalize_features($signal_data) {
        $normalized = array();
        
        // Max values for normalization (based on scoring system)
        $max_values = array(
            'explosive_volume' => 25,
            'parabolic_momentum' => 20,
            'rsi_hype_zone' => 15,
            'social_momentum_proxy' => 15,
            'volume_concentration' => 10,
            'breakout_4h' => 10,
            'low_market_cap_bonus' => 5
        );
        
        foreach ($this->feature_names as $feature) {
            $raw = isset($signal_data[$feature]) ? (float)$signal_data[$feature] : 0;
            $max = isset($max_values[$feature]) ? $max_values[$feature] : 1;
            $normalized[$feature] = min(1, max(0, $raw / $max));
        }
        
        return $normalized;
    }
    
    private function _calculate_confidence($ml_score) {
        // Confidence based on distance from decision boundary
        $distance = abs($ml_score - 0.5);
        
        if ($distance >= 0.3) return 'high';
        if ($distance >= 0.15) return 'medium';
        return 'low';
    }
    
    private function _get_recommendation($probability, $confidence) {
        if ($probability >= 75 && $confidence === 'high') {
            return array('action' => 'strong_buy', 'probability' => $probability);
        } elseif ($probability >= 60) {
            return array('action' => 'buy', 'probability' => $probability);
        } elseif ($probability >= 45) {
            return array('action' => 'lean_buy', 'probability' => $probability);
        } else {
            return array('action' => 'skip', 'probability' => $probability);
        }
    }
    
    private function _find_similar_signals($features, $limit = 5) {
        // Find historically similar signals
        $query = "SELECT 
            s.signal_id,
            s.coin_symbol,
            s.total_score,
            r.outcome,
            r.profit_loss_pct
        FROM meme_signals s
        JOIN meme_signal_results r ON s.signal_id = r.signal_id
        WHERE r.outcome IS NOT NULL
        ORDER BY s.created_at DESC
        LIMIT 100";
        
        $res = $this->conn->query($query);
        $similar = array();
        
        while ($res && $row = $res->fetch_assoc()) {
            $similar[] = array(
                'coin' => $row['coin_symbol'],
                'score' => (int)$row['total_score'],
                'outcome' => $row['outcome'],
                'pl' => (float)$row['profit_loss_pct']
            );
        }
        
        return array_slice($similar, 0, $limit);
    }
    
    private function _get_latest_weights() {
        $res = $this->conn->query("SELECT * FROM meme_ml_models ORDER BY created_at DESC LIMIT 1");
        if ($res && $row = $res->fetch_assoc()) {
            $weights = json_decode($row['weights_json'], true);
            $weights['model_id'] = $row['model_id'];
            return $weights;
        }
        return array_merge($this->default_weights, array('model_id' => 'default'));
    }
    
    private function _save_model($weights, $feature_importance, $metrics, $sample_count) {
        $model_id = 'meme_ml_' . date('Ymd_His');
        $esc_id = $this->conn->real_escape_string($model_id);
        $esc_weights = $this->conn->real_escape_string(json_encode($weights));
        $esc_importance = $this->conn->real_escape_string(json_encode($feature_importance));
        $esc_metrics = $this->conn->real_escape_string(json_encode($metrics));
        
        $query = "INSERT INTO meme_ml_models 
            (model_id, weights_json, feature_importance_json, metrics_json, sample_count, created_at)
            VALUES ('$esc_id', '$esc_weights', '$esc_importance', '$esc_metrics', $sample_count, NOW())";
        
        $this->conn->query($query);
        return $model_id;
    }
    
    private function _sort_by_probability($a, $b) {
        $prob_a = isset($a['prediction']['win_probability']) ? $a['prediction']['win_probability'] : 0;
        $prob_b = isset($b['prediction']['win_probability']) ? $b['prediction']['win_probability'] : 0;
        if ($prob_a == $prob_b) return 0;
        return ($prob_a > $prob_b) ? -1 : 1;
    }
    
    private function _ensure_tables() {
        $this->conn->query("CREATE TABLE IF NOT EXISTS meme_ml_models (
            id INT AUTO_INCREMENT PRIMARY KEY,
            model_id VARCHAR(50) UNIQUE,
            weights_json TEXT,
            feature_importance_json TEXT,
            metrics_json TEXT,
            sample_count INT,
            created_at DATETIME DEFAULT NOW()
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->conn->query("CREATE TABLE IF NOT EXISTS meme_ml_predictions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            signal_id VARCHAR(50),
            model_id VARCHAR(50),
            predicted_probability DECIMAL(5,4),
            predicted_outcome TINYINT,
            actual_outcome TINYINT DEFAULT NULL,
            feature_values_json TEXT,
            created_at DATETIME DEFAULT NOW(),
            INDEX idx_signal (signal_id),
            INDEX idx_model (model_id)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'predict';
$ml = new MemeMLEngine($conn);

if ($action === 'train') {
    $min_samples = isset($_GET['min_samples']) ? (int)$_GET['min_samples'] : 50;
    $result = $ml->train_model($min_samples);
    echo json_encode($result);
} elseif ($action === 'predict') {
    $signal_json = isset($_POST['signal']) ? $_POST['signal'] : (isset($_GET['signal']) ? $_GET['signal'] : '');
    $signal = json_decode($signal_json, true);
    if ($signal) {
        $result = $ml->predict($signal);
        echo json_encode($result);
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Invalid signal data'));
    }
} elseif ($action === 'batch') {
    $signals_json = isset($_POST['signals']) ? $_POST['signals'] : '';
    $signals = json_decode($signals_json, true);
    if (is_array($signals)) {
        $result = $ml->batch_predict($signals);
        echo json_encode($result);
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Invalid signals array'));
    }
} elseif ($action === 'performance') {
    $model_id = isset($_GET['model_id']) ? $_GET['model_id'] : null;
    $result = $ml->get_model_performance($model_id);
    echo json_encode($result);
} elseif ($action === 'compare') {
    $days = isset($_GET['days']) ? (int)$_GET['days'] : 30;
    $result = $ml->compare_methods($days);
    echo json_encode($result);
} elseif ($action === 'retrain') {
    $result = $ml->auto_retrain();
    echo json_encode($result);
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
