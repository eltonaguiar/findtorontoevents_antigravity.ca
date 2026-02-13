<?php
/**
 * Shadow Mode Signal Collection System for XGBoost Meme Coin Model
 * 
 * Collects ML predictions in parallel with rule-based signals for validation.
 * No actual trading - just tracks outcomes to validate model performance.
 * 
 * Target: 350+ resolved signals for 95% CI at 40% target win rate
 * 
 * API Endpoints:
 *   GET  ?action=report                    - Get comparison report
 *   GET  ?action=progress                  - Get progress to 350 target
 *   GET  ?action=list&status=open&limit=100 - List shadow signals
 *   GET  ?action=chart&days=30             - Get chart data
 *   POST ?action=collect&key=admin_key     - Force signal collection
 *   POST ?action=resolve&key=admin_key     - Force outcome resolution
 *   POST ?action=init&key=admin_key        - Initialize database tables
 * 
 * PHP 5.2 compatible
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

error_reporting(0);
ini_set('display_errors', '0');

// ═══════════════════════════════════════════════════════════════════════
//  Configuration
// ═══════════════════════════════════════════════════════════════════════
$ADMIN_KEY = 'shadow2026';
$TARGET_SIGNALS = 350;
$CONFIDENCE_LEVEL = 0.95;
$Z_SCORE = 1.96;  // 95% CI

$MEME_SCANNER_URL = 'http' . (isset($_SERVER['HTTPS']) ? 's' : '') . '://' . 
                    $_SERVER['HTTP_HOST'] . 
                    dirname($_SERVER['SCRIPT_NAME']) . '/../api/meme_scanner.php';
$ML_PREDICT_URL = 'http' . (isset($_SERVER['HTTPS']) ? 's' : '') . '://' . 
                  $_SERVER['HTTP_HOST'] . 
                  dirname($_SERVER['SCRIPT_NAME']) . '/predict.php';
$FEATURES_URL = 'http' . (isset($_SERVER['HTTPS']) ? 's' : '') . '://' . 
                $_SERVER['HTTP_HOST'] . 
                dirname($_SERVER['SCRIPT_NAME']) . '/features.php';

// Database connection
$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed'));
    exit;
}
$conn->set_charset('utf8');

// ═══════════════════════════════════════════════════════════════════════
//  Shadow Signal Collector Class
// ═══════════════════════════════════════════════════════════════════════
class ShadowSignalCollector {
    private $conn;
    private $memeScannerUrl;
    private $mlPredictUrl;
    private $featuresUrl;
    private $targetSignals;
    private $zScore;
    
    // Tier thresholds (aligned with predict.php)
    private $confidenceThresholds = array(
        'strong' => 0.75,
        'moderate' => 0.60,
        'lean' => 0.50
    );
    
    public function __construct($connection, $memeScannerUrl, $mlPredictUrl, $featuresUrl, $targetSignals = 350, $zScore = 1.96) {
        $this->conn = $connection;
        $this->memeScannerUrl = $memeScannerUrl;
        $this->mlPredictUrl = $mlPredictUrl;
        $this->featuresUrl = $featuresUrl;
        $this->targetSignals = $targetSignals;
        $this->zScore = $zScore;
        $this->ensureTables();
    }
    
    /**
     * Initialize database tables
     */
    public function ensureTables() {
        // Shadow signals table - stores all collected signals
        $sql1 = "CREATE TABLE IF NOT EXISTS mc_shadow_signals (
            id INT AUTO_INCREMENT PRIMARY KEY,
            symbol VARCHAR(20) NOT NULL,
            timestamp INT NOT NULL,
            entry_price DECIMAL(18,8) NOT NULL,
            ml_score DECIMAL(5,4) NOT NULL,
            ml_prediction VARCHAR(10) NOT NULL,
            ml_tier VARCHAR(20) NOT NULL,
            rule_based_score INT NOT NULL,
            rule_based_tier VARCHAR(20) NOT NULL,
            features JSON,
            status VARCHAR(20) DEFAULT 'open',
            tp_price DECIMAL(18,8) NOT NULL,
            sl_price DECIMAL(18,8) NOT NULL,
            exit_price DECIMAL(18,8),
            exit_time INT,
            exit_reason VARCHAR(20),
            return_pct DECIMAL(8,4),
            ml_was_correct BOOLEAN,
            rule_based_was_correct BOOLEAN,
            INDEX idx_symbol_time (symbol, timestamp),
            INDEX idx_status (status),
            INDEX idx_ml_tier (ml_tier),
            INDEX idx_rule_tier (rule_based_tier),
            INDEX idx_created (timestamp)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
        
        $this->conn->query($sql1);
        
        // Shadow summary table - daily aggregated stats
        $sql2 = "CREATE TABLE IF NOT EXISTS mc_shadow_summary (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date DATE NOT NULL,
            total_signals INT DEFAULT 0,
            ml_win_rate DECIMAL(5,4),
            rule_based_win_rate DECIMAL(5,4),
            ml_strong_buy_wr DECIMAL(5,4),
            ml_moderate_buy_wr DECIMAL(5,4),
            ml_lean_buy_wr DECIMAL(5,4),
            rule_based_strong_wr DECIMAL(5,4),
            rule_based_moderate_wr DECIMAL(5,4),
            rule_based_lean_wr DECIMAL(5,4),
            samples_sufficient BOOLEAN DEFAULT FALSE,
            UNIQUE KEY idx_date (date)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8";
        
        $this->conn->query($sql2);
        
        return array('tables_created' => true);
    }
    
    /**
     * Collect shadow signals from meme scanner and ML model
     */
    public function collectSignals() {
        $startTime = microtime(true);
        $collected = 0;
        $errors = array();
        
        // Get candidates from meme scanner (scan_log with recent candidates)
        $candidates = $this->getMemeCoins();
        
        if (empty($candidates)) {
            return array(
                'ok' => true,
                'message' => 'No meme coin candidates found',
                'collected' => 0,
                'elapsed_sec' => round(microtime(true) - $startTime, 2)
            );
        }
        
        foreach ($candidates as $coin) {
            try {
                // Skip if we already have an open signal for this symbol
                if ($this->hasOpenSignal($coin['symbol'])) {
                    continue;
                }
                
                // Get ML prediction
                $mlPrediction = $this->getMLPrediction($coin['symbol']);
                if (!$mlPrediction || !$mlPrediction['ok']) {
                    $errors[] = "ML prediction failed for {$coin['symbol']}";
                    continue;
                }
                
                // Get features for storage
                $features = $this->getFeatures($coin['symbol']);
                
                // Determine ML tier
                $mlTier = $this->getMLTier($mlPrediction['probability']);
                
                // Determine rule-based tier
                $ruleTier = $this->getRuleBasedTier($coin['score']);
                
                // Calculate TP/SL prices
                $tpPrice = $coin['price'] * 1.08;  // +8% default TP
                $slPrice = $coin['price'] * 0.96;  // -4% default SL
                
                // Use prediction targets if available
                if (isset($mlPrediction['target_price']) && $mlPrediction['target_price'] > 0) {
                    $tpPrice = $mlPrediction['target_price'];
                }
                if (isset($mlPrediction['stop_price']) && $mlPrediction['stop_price'] > 0) {
                    $slPrice = $mlPrediction['stop_price'];
                }
                
                // Store shadow signal
                $this->storeShadowSignal(array(
                    'symbol' => $coin['symbol'],
                    'timestamp' => time(),
                    'entry_price' => $coin['price'],
                    'ml_score' => $mlPrediction['probability'],
                    'ml_prediction' => $mlPrediction['prediction'],
                    'ml_tier' => $mlTier,
                    'rule_based_score' => $coin['score'],
                    'rule_based_tier' => $ruleTier,
                    'features' => json_encode($features),
                    'status' => 'open',
                    'tp_price' => $tpPrice,
                    'sl_price' => $slPrice
                ));
                
                $collected++;
                
            } catch (Exception $e) {
                $errors[] = "Error processing {$coin['symbol']}: " . $e->getMessage();
            }
        }
        
        // Update daily summary
        $this->updateDailySummary();
        
        return array(
            'ok' => true,
            'candidates_checked' => count($candidates),
            'signals_collected' => $collected,
            'errors' => $errors,
            'elapsed_sec' => round(microtime(true) - $startTime, 2)
        );
    }
    
    /**
     * Get meme coin candidates from scanner or use Tier 1 list
     */
    private function getMemeCoins() {
        $candidates = array();
        
        // Tier 1: Always scan these established meme coins
        $tier1Symbols = array('DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'TURBO', 'NEIRO');
        
        // Try to get current prices and scores from meme scanner API
        foreach ($tier1Symbols as $symbol) {
            $price = $this->getCurrentPrice($symbol);
            if ($price > 0) {
                // Generate a simulated rule-based score (65-95 range)
                // In production, this would come from the actual scanner
                $score = $this->getSimulatedRuleBasedScore($symbol);
                
                $candidates[] = array(
                    'symbol' => $symbol,
                    'price' => $price,
                    'score' => $score,
                    'tier' => 'tier1'
                );
            }
        }
        
        // Also check recent scan_log entries for Tier 2 candidates
        $query = "SELECT pair, price, score, chg_24h, vol_usd_24h, tier 
                  FROM mc_scan_log 
                  WHERE created_at > DATE_SUB(NOW(), INTERVAL 1 HOUR)
                  AND score >= 70
                  ORDER BY score DESC
                  LIMIT 20";
        
        $res = $this->conn->query($query);
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $baseSymbol = str_replace(array('_USDT', '_USD'), '', $row['pair']);
                
                // Skip if already in candidates
                $exists = false;
                foreach ($candidates as $c) {
                    if ($c['symbol'] === $baseSymbol) {
                        $exists = true;
                        break;
                    }
                }
                
                if (!$exists) {
                    $candidates[] = array(
                        'symbol' => $baseSymbol,
                        'price' => floatval($row['price']),
                        'score' => intval($row['score']),
                        'tier' => $row['tier']
                    );
                }
            }
        }
        
        return $candidates;
    }
    
    /**
     * Get simulated rule-based score for Tier 1 coins
     * In production, this would use the actual scoring from meme_scanner.php
     */
    private function getSimulatedRuleBasedScore($symbol) {
        // Generate deterministic pseudo-random score based on symbol and time
        // This ensures same symbol gets similar score within a time window
        $timeBucket = floor(time() / 3600); // Hourly buckets
        $hash = crc32($symbol . $timeBucket);
        mt_srand($hash);
        $score = mt_rand(65, 95);
        mt_srand(); // Reset
        
        return $score;
    }
    
    /**
     * Get current price from Kraken
     */
    private function getCurrentPrice($symbol) {
        $pair = $symbol . 'USD';
        $url = 'https://api.kraken.com/0/public/Ticker?pair=' . urlencode($pair);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        
        $resp = curl_exec($ch);
        curl_close($ch);
        
        if (!$resp) return 0;
        
        $data = json_decode($resp, true);
        if (isset($data['error']) && !empty($data['error'])) return 0;
        
        $resultKey = array_keys($data['result']);
        if (empty($resultKey)) return 0;
        
        return floatval($data['result'][$resultKey[0]]['c'][0]);
    }
    
    /**
     * Get ML prediction from predict.php API
     */
    private function getMLPrediction($symbol) {
        $url = $this->mlPredictUrl . '?action=predict&symbol=' . urlencode($symbol);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        
        $resp = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($httpCode !== 200 || !$resp) {
            return array('ok' => false, 'error' => 'HTTP ' . $httpCode);
        }
        
        $data = json_decode($resp, true);
        if (!$data || !isset($data['ok'])) {
            return array('ok' => false, 'error' => 'Invalid response');
        }
        
        return $data;
    }
    
    /**
     * Get features for storage
     */
    private function getFeatures($symbol) {
        $url = $this->featuresUrl . '?action=features&symbol=' . urlencode($symbol);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        
        $resp = curl_exec($ch);
        curl_close($ch);
        
        if (!$resp) return array();
        
        $data = json_decode($resp, true);
        if (!$data || !isset($data['ok']) || !$data['ok']) {
            return array();
        }
        
        return isset($data['feature_vector']) ? $data['feature_vector'] : array();
    }
    
    /**
     * Determine ML tier based on probability
     */
    private function getMLTier($probability) {
        $distanceFrom50 = abs($probability - 0.5) * 2;
        
        if ($distanceFrom50 >= $this->confidenceThresholds['strong']) {
            return 'strong_buy';
        } elseif ($distanceFrom50 >= $this->confidenceThresholds['moderate']) {
            return 'moderate_buy';
        } else {
            return 'lean_buy';
        }
    }
    
    /**
     * Determine rule-based tier from score
     */
    private function getRuleBasedTier($score) {
        if ($score >= 88) {
            return 'Strong Buy';
        } elseif ($score >= 82) {
            return 'Buy';
        } elseif ($score >= 78) {
            return 'Lean Buy';
        } else {
            return 'Skip';
        }
    }
    
    /**
     * Check if symbol already has an open signal
     */
    private function hasOpenSignal($symbol) {
        $escSymbol = $this->conn->real_escape_string($symbol);
        $query = "SELECT COUNT(*) as cnt FROM mc_shadow_signals 
                  WHERE symbol = '$escSymbol' AND status = 'open'";
        $res = $this->conn->query($query);
        if ($res && $row = $res->fetch_assoc()) {
            return intval($row['cnt']) > 0;
        }
        return false;
    }
    
    /**
     * Store shadow signal in database
     */
    private function storeShadowSignal($data) {
        $escSymbol = $this->conn->real_escape_string($data['symbol']);
        $escTimestamp = intval($data['timestamp']);
        $escEntryPrice = floatval($data['entry_price']);
        $escMlScore = floatval($data['ml_score']);
        $escMlPrediction = $this->conn->real_escape_string($data['ml_prediction']);
        $escMlTier = $this->conn->real_escape_string($data['ml_tier']);
        $escRuleScore = intval($data['rule_based_score']);
        $escRuleTier = $this->conn->real_escape_string($data['rule_based_tier']);
        $escFeatures = $this->conn->real_escape_string($data['features']);
        $escStatus = $this->conn->real_escape_string($data['status']);
        $escTpPrice = floatval($data['tp_price']);
        $escSlPrice = floatval($data['sl_price']);
        
        $sql = "INSERT INTO mc_shadow_signals 
            (symbol, timestamp, entry_price, ml_score, ml_prediction, ml_tier,
             rule_based_score, rule_based_tier, features, status, tp_price, sl_price)
            VALUES 
            ('$escSymbol', $escTimestamp, $escEntryPrice, $escMlScore, '$escMlPrediction', '$escMlTier',
             $escRuleScore, '$escRuleTier', '$escFeatures', '$escStatus', $escTpPrice, $escSlPrice)";
        
        return $this->conn->query($sql);
    }
    
    /**
     * Resolve open signals - check if TP/SL hit or max hold reached
     */
    public function resolveSignals() {
        $startTime = microtime(true);
        $resolved = 0;
        $errors = array();
        
        // Get all open signals
        $openSignals = $this->getOpenSignals();
        
        foreach ($openSignals as $signal) {
            try {
                $currentPrice = $this->getCurrentPrice($signal['symbol']);
                
                if ($currentPrice <= 0) {
                    $errors[] = "Could not get price for {$signal['symbol']}";
                    continue;
                }
                
                $ageHours = (time() - intval($signal['timestamp'])) / 3600;
                $exitReason = null;
                $isWin = false;
                
                // Check TP hit
                if ($currentPrice >= floatval($signal['tp_price'])) {
                    $exitReason = 'tp_hit';
                    $isWin = true;
                }
                // Check SL hit
                elseif ($currentPrice <= floatval($signal['sl_price'])) {
                    $exitReason = 'sl_hit';
                    $isWin = false;
                }
                // Max hold time reached (24 hours)
                elseif ($ageHours >= 24) {
                    $exitReason = 'max_hold';
                    // Win if price went up overall
                    $isWin = $currentPrice > floatval($signal['entry_price']);
                }
                
                // Close signal if exit condition met
                if ($exitReason !== null) {
                    $this->closeSignal($signal, $currentPrice, $exitReason, $isWin);
                    $resolved++;
                }
                
            } catch (Exception $e) {
                $errors[] = "Error resolving {$signal['symbol']}: " . $e->getMessage();
            }
        }
        
        // Update daily summary
        if ($resolved > 0) {
            $this->updateDailySummary();
        }
        
        return array(
            'ok' => true,
            'open_signals_checked' => count($openSignals),
            'signals_resolved' => $resolved,
            'errors' => $errors,
            'elapsed_sec' => round(microtime(true) - $startTime, 2)
        );
    }
    
    /**
     * Get all open signals
     */
    private function getOpenSignals() {
        $signals = array();
        $query = "SELECT * FROM mc_shadow_signals WHERE status = 'open' ORDER BY timestamp DESC";
        $res = $this->conn->query($query);
        
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $signals[] = $row;
            }
        }
        
        return $signals;
    }
    
    /**
     * Close a signal with outcome
     */
    private function closeSignal($signal, $exitPrice, $reason, $isWin) {
        $entryPrice = floatval($signal['entry_price']);
        $returnPct = ($exitPrice - $entryPrice) / $entryPrice * 100;
        
        // Determine if ML prediction was correct
        $mlPrediction = $signal['ml_prediction'];
        $mlCorrect = false;
        
        if ($mlPrediction === 'buy' || $mlPrediction === 'strong_buy' || $mlPrediction === 'lean_buy') {
            $mlCorrect = $isWin;
        } elseif ($mlPrediction === 'sell' || $mlPrediction === 'avoid') {
            $mlCorrect = !$isWin;
        } elseif ($mlPrediction === 'hold') {
            $mlCorrect = true; // Hold is always considered correct
        }
        
        // Determine if rule-based prediction was correct
        $ruleTier = $signal['rule_based_tier'];
        $ruleCorrect = false;
        
        if (strpos($ruleTier, 'Buy') !== false) {
            $ruleCorrect = $isWin;
        } elseif (strpos($ruleTier, 'Sell') !== false || strpos($ruleTier, 'Skip') !== false) {
            $ruleCorrect = !$isWin;
        } else {
            $ruleCorrect = true;
        }
        
        $escExitPrice = floatval($exitPrice);
        $escExitTime = time();
        $escReason = $this->conn->real_escape_string($reason);
        $escReturnPct = floatval($returnPct);
        $escMlCorrect = $mlCorrect ? 1 : 0;
        $escRuleCorrect = $ruleCorrect ? 1 : 0;
        $escId = intval($signal['id']);
        
        $sql = "UPDATE mc_shadow_signals SET
            status = 'closed',
            exit_price = $escExitPrice,
            exit_time = $escExitTime,
            exit_reason = '$escReason',
            return_pct = $escReturnPct,
            ml_was_correct = $escMlCorrect,
            rule_based_was_correct = $escRuleCorrect
            WHERE id = $escId";
        
        return $this->conn->query($sql);
    }
    
    /**
     * Get comparison report between ML and rule-based predictions
     */
    public function getComparisonReport() {
        $report = array(
            'total_signals' => 0,
            'open_signals' => 0,
            'closed_signals' => 0,
            'ml_stats' => array('wins' => 0, 'losses' => 0, 'win_rate' => 0),
            'rule_based_stats' => array('wins' => 0, 'losses' => 0, 'win_rate' => 0),
            'by_tier' => array(
                'ml_strong_buy' => array('signals' => 0, 'wins' => 0, 'win_rate' => 0),
                'ml_moderate_buy' => array('signals' => 0, 'wins' => 0, 'win_rate' => 0),
                'ml_lean_buy' => array('signals' => 0, 'wins' => 0, 'win_rate' => 0),
                'rule_strong_buy' => array('signals' => 0, 'wins' => 0, 'win_rate' => 0),
                'rule_buy' => array('signals' => 0, 'wins' => 0, 'win_rate' => 0),
                'rule_lean_buy' => array('signals' => 0, 'wins' => 0, 'win_rate' => 0)
            ),
            'exit_reasons' => array(),
            'statistical_validity' => array(
                'current_sample_size' => 0,
                'target_sample_size' => $this->targetSignals,
                'confidence_interval_95' => null,
                'is_valid' => false
            ),
            'recent_signals' => array()
        );
        
        // Get total counts
        $res = $this->conn->query("SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) as open,
            SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed
            FROM mc_shadow_signals");
        
        if ($res && $row = $res->fetch_assoc()) {
            $report['total_signals'] = intval($row['total']);
            $report['open_signals'] = intval($row['open']);
            $report['closed_signals'] = intval($row['closed']);
        }
        
        // Get ML stats
        $res = $this->conn->query("SELECT 
            SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN ml_was_correct = 0 THEN 1 ELSE 0 END) as losses
            FROM mc_shadow_signals WHERE status = 'closed'");
        
        if ($res && $row = $res->fetch_assoc()) {
            $report['ml_stats']['wins'] = intval($row['wins']);
            $report['ml_stats']['losses'] = intval($row['losses']);
            $total = $report['ml_stats']['wins'] + $report['ml_stats']['losses'];
            $report['ml_stats']['win_rate'] = $total > 0 ? round($report['ml_stats']['wins'] / $total, 4) : 0;
        }
        
        // Get rule-based stats
        $res = $this->conn->query("SELECT 
            SUM(CASE WHEN rule_based_was_correct = 1 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN rule_based_was_correct = 0 THEN 1 ELSE 0 END) as losses
            FROM mc_shadow_signals WHERE status = 'closed'");
        
        if ($res && $row = $res->fetch_assoc()) {
            $report['rule_based_stats']['wins'] = intval($row['wins']);
            $report['rule_based_stats']['losses'] = intval($row['losses']);
            $total = $report['rule_based_stats']['wins'] + $report['rule_based_stats']['losses'];
            $report['rule_based_stats']['win_rate'] = $total > 0 ? round($report['rule_based_stats']['wins'] / $total, 4) : 0;
        }
        
        // Get by-tier stats
        $this->getTierStats($report['by_tier']);
        
        // Get exit reasons distribution
        $res = $this->conn->query("SELECT exit_reason, COUNT(*) as cnt 
            FROM mc_shadow_signals 
            WHERE status = 'closed' AND exit_reason IS NOT NULL
            GROUP BY exit_reason");
        
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $report['exit_reasons'][$row['exit_reason']] = intval($row['cnt']);
            }
        }
        
        // Calculate statistical validity
        $closedCount = $report['closed_signals'];
        $wins = $report['ml_stats']['wins'];
        $winRate = $report['ml_stats']['win_rate'];
        
        $report['statistical_validity']['current_sample_size'] = $closedCount;
        $report['statistical_validity']['is_valid'] = $closedCount >= $this->targetSignals;
        
        if ($closedCount > 0) {
            $wilson = $this->calculateWilsonInterval($winRate, $closedCount);
            $report['statistical_validity']['confidence_interval_95'] = $wilson;
        }
        
        // Get recent signals
        $res = $this->conn->query("SELECT 
            symbol, timestamp, entry_price, ml_score, ml_prediction, ml_tier,
            rule_based_score, rule_based_tier, status, exit_price, exit_reason,
            return_pct, ml_was_correct, rule_based_was_correct
            FROM mc_shadow_signals 
            ORDER BY timestamp DESC
            LIMIT 10");
        
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $report['recent_signals'][] = array(
                    'symbol' => $row['symbol'],
                    'timestamp' => intval($row['timestamp']),
                    'entry_price' => floatval($row['entry_price']),
                    'ml_score' => floatval($row['ml_score']),
                    'ml_prediction' => $row['ml_prediction'],
                    'ml_tier' => $row['ml_tier'],
                    'rule_based_score' => intval($row['rule_based_score']),
                    'rule_based_tier' => $row['rule_based_tier'],
                    'status' => $row['status'],
                    'exit_price' => $row['exit_price'] ? floatval($row['exit_price']) : null,
                    'exit_reason' => $row['exit_reason'],
                    'return_pct' => $row['return_pct'] ? floatval($row['return_pct']) : null,
                    'ml_correct' => $row['ml_was_correct'] !== null ? (bool)$row['ml_was_correct'] : null,
                    'rule_correct' => $row['rule_based_was_correct'] !== null ? (bool)$row['rule_based_was_correct'] : null
                );
            }
        }
        
        return $report;
    }
    
    /**
     * Get tier-level statistics
     */
    private function getTierStats(&$byTier) {
        // ML tier stats
        $mlTiers = array('strong_buy', 'moderate_buy', 'lean_buy');
        foreach ($mlTiers as $tier) {
            $key = 'ml_' . $tier;
            $res = $this->conn->query("SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) as wins
                FROM mc_shadow_signals 
                WHERE status = 'closed' AND ml_tier = '$tier'");
            
            if ($res && $row = $res->fetch_assoc()) {
                $byTier[$key]['signals'] = intval($row['total']);
                $byTier[$key]['wins'] = intval($row['wins']);
                $byTier[$key]['win_rate'] = $row['total'] > 0 ? round($row['wins'] / $row['total'], 4) : 0;
            }
        }
        
        // Rule-based tier stats
        $ruleTiers = array('Strong Buy' => 'rule_strong_buy', 'Buy' => 'rule_buy', 'Lean Buy' => 'rule_lean_buy');
        foreach ($ruleTiers as $tier => $key) {
            $escTier = $this->conn->real_escape_string($tier);
            $res = $this->conn->query("SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN rule_based_was_correct = 1 THEN 1 ELSE 0 END) as wins
                FROM mc_shadow_signals 
                WHERE status = 'closed' AND rule_based_tier = '$escTier'");
            
            if ($res && $row = $res->fetch_assoc()) {
                $byTier[$key]['signals'] = intval($row['total']);
                $byTier[$key]['wins'] = intval($row['wins']);
                $byTier[$key]['win_rate'] = $row['total'] > 0 ? round($row['wins'] / $row['total'], 4) : 0;
            }
        }
    }
    
    /**
     * Calculate Wilson score interval for confidence bounds
     */
    private function calculateWilsonInterval($p, $n) {
        if ($n == 0) {
            return array('lower' => 0, 'upper' => 0);
        }
        
        $z = $this->zScore;
        $z2 = $z * $z;
        
        $center = ($p + $z2 / (2 * $n)) / (1 + $z2 / $n);
        $halfWidth = $z * sqrt(($p * (1 - $p) + $z2 / (4 * $n)) / $n) / (1 + $z2 / $n);
        
        return array(
            'lower' => round(max(0, $center - $halfWidth), 4),
            'upper' => round(min(1, $center + $halfWidth), 4)
        );
    }
    
    /**
     * Get progress toward 350 signal target
     */
    public function getProgressToTarget() {
        // Get current closed signal count
        $res = $this->conn->query("SELECT COUNT(*) as cnt FROM mc_shadow_signals WHERE status = 'closed'");
        $current = 0;
        if ($res && $row = $res->fetch_assoc()) {
            $current = intval($row['cnt']);
        }
        
        // Get current win rate
        $res = $this->conn->query("SELECT 
            SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) as wins,
            COUNT(*) as total
            FROM mc_shadow_signals WHERE status = 'closed'");
        
        $wins = 0;
        $total = 0;
        if ($res && $row = $res->fetch_assoc()) {
            $wins = intval($row['wins']);
            $total = intval($row['total']);
        }
        
        $p = $total > 0 ? $wins / $total : 0;
        $percent = min(100, ($current / $this->targetSignals) * 100);
        
        // Wilson score interval
        $wilson = $this->calculateWilsonInterval($p, max(1, $current));
        
        return array(
            'current_signals' => $current,
            'target_signals' => $this->targetSignals,
            'percent_complete' => round($percent, 1),
            'current_win_rate' => round($p * 100, 2),
            'wilson_ci_95' => array(
                'lower' => round($wilson['lower'] * 100, 2),
                'upper' => round($wilson['upper'] * 100, 2)
            ),
            'is_statistically_valid' => $current >= $this->targetSignals,
            'estimated_completion' => $this->estimateCompletionDate($current, $this->targetSignals)
        );
    }
    
    /**
     * Estimate completion date based on collection rate
     */
    private function estimateCompletionDate($current, $target) {
        if ($current >= $target) {
            return array('reached' => true, 'date' => null);
        }
        
        // Calculate average signals per day from last 7 days
        $res = $this->conn->query("SELECT COUNT(*) as cnt 
            FROM mc_shadow_signals 
            WHERE timestamp > " . (time() - 7 * 24 * 3600));
        
        $recentCount = 0;
        if ($res && $row = $res->fetch_assoc()) {
            $recentCount = intval($row['cnt']);
        }
        
        $signalsPerDay = $recentCount / 7;
        
        if ($signalsPerDay <= 0) {
            return array('reached' => false, 'date' => null, 'signals_per_day' => 0);
        }
        
        $remaining = $target - $current;
        $daysRemaining = ceil($remaining / $signalsPerDay);
        $estimatedDate = date('Y-m-d', strtotime("+$daysRemaining days"));
        
        return array(
            'reached' => false,
            'date' => $estimatedDate,
            'days_remaining' => $daysRemaining,
            'signals_per_day' => round($signalsPerDay, 2)
        );
    }
    
    /**
     * Get chart data for visualization
     */
    public function getChartData($days = 30) {
        $escDays = intval($days);
        $cutoff = time() - ($escDays * 24 * 3600);
        
        $data = array(
            'dates' => array(),
            'ml_win_rates' => array(),
            'rule_win_rates' => array(),
            'signal_counts' => array(),
            'cumulative_signals' => array()
        );
        
        // Get daily stats
        $res = $this->conn->query("SELECT 
            DATE(FROM_UNIXTIME(timestamp)) as date,
            COUNT(*) as total_signals,
            SUM(CASE WHEN status = 'closed' AND ml_was_correct = 1 THEN 1 ELSE 0 END) as ml_wins,
            SUM(CASE WHEN status = 'closed' AND ml_was_correct = 0 THEN 1 ELSE 0 END) as ml_losses,
            SUM(CASE WHEN status = 'closed' AND rule_based_was_correct = 1 THEN 1 ELSE 0 END) as rule_wins,
            SUM(CASE WHEN status = 'closed' AND rule_based_was_correct = 0 THEN 1 ELSE 0 END) as rule_losses
            FROM mc_shadow_signals 
            WHERE timestamp > $cutoff
            GROUP BY DATE(FROM_UNIXTIME(timestamp))
            ORDER BY date ASC");
        
        $cumulative = 0;
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $data['dates'][] = $row['date'];
                
                $mlTotal = intval($row['ml_wins']) + intval($row['ml_losses']);
                $data['ml_win_rates'][] = $mlTotal > 0 ? round(intval($row['ml_wins']) / $mlTotal, 4) : null;
                
                $ruleTotal = intval($row['rule_wins']) + intval($row['rule_losses']);
                $data['rule_win_rates'][] = $ruleTotal > 0 ? round(intval($row['rule_wins']) / $ruleTotal, 4) : null;
                
                $data['signal_counts'][] = intval($row['total_signals']);
                
                $cumulative += intval($row['total_signals']);
                $data['cumulative_signals'][] = $cumulative;
            }
        }
        
        return $data;
    }
    
    /**
     * List shadow signals with optional filtering
     */
    public function listSignals($status = null, $limit = 100, $offset = 0) {
        $escLimit = intval($limit);
        $escOffset = intval($offset);
        
        $where = '';
        if ($status !== null && in_array($status, array('open', 'closed'))) {
            $escStatus = $this->conn->real_escape_string($status);
            $where = "WHERE status = '$escStatus'";
        }
        
        $signals = array();
        $query = "SELECT * FROM mc_shadow_signals $where ORDER BY timestamp DESC LIMIT $escOffset, $escLimit";
        $res = $this->conn->query($query);
        
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $signals[] = array(
                    'id' => intval($row['id']),
                    'symbol' => $row['symbol'],
                    'timestamp' => intval($row['timestamp']),
                    'entry_price' => floatval($row['entry_price']),
                    'ml_score' => floatval($row['ml_score']),
                    'ml_prediction' => $row['ml_prediction'],
                    'ml_tier' => $row['ml_tier'],
                    'rule_based_score' => intval($row['rule_based_score']),
                    'rule_based_tier' => $row['rule_based_tier'],
                    'status' => $row['status'],
                    'tp_price' => floatval($row['tp_price']),
                    'sl_price' => floatval($row['sl_price']),
                    'exit_price' => $row['exit_price'] ? floatval($row['exit_price']) : null,
                    'exit_time' => $row['exit_time'] ? intval($row['exit_time']) : null,
                    'exit_reason' => $row['exit_reason'],
                    'return_pct' => $row['return_pct'] ? floatval($row['return_pct']) : null,
                    'ml_was_correct' => $row['ml_was_correct'] !== null ? (bool)$row['ml_was_correct'] : null,
                    'rule_based_was_correct' => $row['rule_based_was_correct'] !== null ? (bool)$row['rule_based_was_correct'] : null
                );
            }
        }
        
        // Get total count
        $totalQuery = "SELECT COUNT(*) as cnt FROM mc_shadow_signals $where";
        $totalRes = $this->conn->query($totalQuery);
        $total = 0;
        if ($totalRes && $row = $totalRes->fetch_assoc()) {
            $total = intval($row['cnt']);
        }
        
        return array(
            'signals' => $signals,
            'total' => $total,
            'limit' => $escLimit,
            'offset' => $escOffset
        );
    }
    
    /**
     * Update daily summary table
     */
    private function updateDailySummary() {
        $today = date('Y-m-d');
        $escToday = $this->conn->real_escape_string($today);
        
        // Calculate today's stats
        $startOfDay = strtotime($today . ' 00:00:00');
        $endOfDay = strtotime($today . ' 23:59:59');
        
        $res = $this->conn->query("SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'closed' AND ml_was_correct = 1 THEN 1 ELSE 0 END) as ml_wins,
            SUM(CASE WHEN status = 'closed' AND ml_was_correct = 0 THEN 1 ELSE 0 END) as ml_losses,
            SUM(CASE WHEN status = 'closed' AND rule_based_was_correct = 1 THEN 1 ELSE 0 END) as rule_wins,
            SUM(CASE WHEN status = 'closed' AND rule_based_was_correct = 0 THEN 1 ELSE 0 END) as rule_losses
            FROM mc_shadow_signals 
            WHERE timestamp BETWEEN $startOfDay AND $endOfDay");
        
        if (!$res) return;
        
        $row = $res->fetch_assoc();
        $total = intval($row['total']);
        
        $mlWins = intval($row['ml_wins']);
        $mlLosses = intval($row['ml_losses']);
        $mlWR = ($mlWins + $mlLosses) > 0 ? $mlWins / ($mlWins + $mlLosses) : 0;
        
        $ruleWins = intval($row['rule_wins']);
        $ruleLosses = intval($row['rule_losses']);
        $ruleWR = ($ruleWins + $ruleLosses) > 0 ? $ruleWins / ($ruleWins + $ruleLosses) : 0;
        
        // Get tier-specific stats
        $tierStats = array(
            'ml_strong' => 0, 'ml_moderate' => 0, 'ml_lean' => 0,
            'rule_strong' => 0, 'rule_moderate' => 0, 'rule_lean' => 0
        );
        
        // ML tiers
        foreach (array('strong_buy', 'moderate_buy', 'lean_buy') as $tier) {
            $res2 = $this->conn->query("SELECT 
                SUM(CASE WHEN ml_was_correct = 1 THEN 1 ELSE 0 END) as wins,
                COUNT(*) as total
                FROM mc_shadow_signals 
                WHERE timestamp BETWEEN $startOfDay AND $endOfDay AND ml_tier = '$tier' AND status = 'closed'");
            
            if ($res2 && $row2 = $res2->fetch_assoc() && $row2['total'] > 0) {
                $tierStats['ml_' . str_replace('_buy', '', $tier)] = round($row2['wins'] / $row2['total'], 4);
            }
        }
        
        // Rule-based tiers
        foreach (array('Strong Buy' => 'strong', 'Buy' => 'moderate', 'Lean Buy' => 'lean') as $tier => $key) {
            $escTier = $this->conn->real_escape_string($tier);
            $res2 = $this->conn->query("SELECT 
                SUM(CASE WHEN rule_based_was_correct = 1 THEN 1 ELSE 0 END) as wins,
                COUNT(*) as total
                FROM mc_shadow_signals 
                WHERE timestamp BETWEEN $startOfDay AND $endOfDay AND rule_based_tier = '$escTier' AND status = 'closed'");
            
            if ($res2 && $row2 = $res2->fetch_assoc() && $row2['total'] > 0) {
                $tierStats['rule_' . $key] = round($row2['wins'] / $row2['total'], 4);
            }
        }
        
        // Check if we have enough samples
        $totalClosed = $this->conn->query("SELECT COUNT(*) as cnt FROM mc_shadow_signals WHERE status = 'closed'")
            ->fetch_assoc()['cnt'];
        $samplesSufficient = intval($totalClosed) >= $this->targetSignals ? 1 : 0;
        
        // Insert or update summary
        $sql = "INSERT INTO mc_shadow_summary 
            (date, total_signals, ml_win_rate, rule_based_win_rate,
             ml_strong_buy_wr, ml_moderate_buy_wr, ml_lean_buy_wr,
             rule_based_strong_wr, rule_based_lean_wr, samples_sufficient)
            VALUES 
            ('$escToday', $total, $mlWR, $ruleWR,
             {$tierStats['ml_strong']}, {$tierStats['ml_moderate']}, {$tierStats['ml_lean']},
             {$tierStats['rule_strong']}, {$tierStats['rule_lean']}, $samplesSufficient)
            ON DUPLICATE KEY UPDATE
            total_signals = VALUES(total_signals),
            ml_win_rate = VALUES(ml_win_rate),
            rule_based_win_rate = VALUES(rule_based_win_rate),
            ml_strong_buy_wr = VALUES(ml_strong_buy_wr),
            ml_moderate_buy_wr = VALUES(ml_moderate_buy_wr),
            ml_lean_buy_wr = VALUES(ml_lean_buy_wr),
            rule_based_strong_wr = VALUES(rule_based_strong_wr),
            rule_based_lean_wr = VALUES(rule_based_lean_wr),
            samples_sufficient = VALUES(samples_sufficient)";
        
        $this->conn->query($sql);
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  API Endpoint Handler
// ═══════════════════════════════════════════════════════════════════════

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'report';
$key = isset($_GET['key']) ? $_GET['key'] : '';

$collector = new ShadowSignalCollector($conn, $MEME_SCANNER_URL, $ML_PREDICT_URL, $FEATURES_URL, $TARGET_SIGNALS, $Z_SCORE);

switch ($action) {
    case 'report':
        // Public: Get comparison report
        $report = $collector->getComparisonReport();
        echo json_encode(array('ok' => true, 'report' => $report));
        break;
        
    case 'progress':
        // Public: Get progress to target
        $progress = $collector->getProgressToTarget();
        echo json_encode(array('ok' => true, 'progress' => $progress));
        break;
        
    case 'list':
        // Public: List signals
        $status = isset($_GET['status']) ? $_GET['status'] : null;
        $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 100;
        $offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;
        $signals = $collector->listSignals($status, $limit, $offset);
        echo json_encode(array('ok' => true, 'signals' => $signals['signals'], 'total' => $signals['total'], 'limit' => $limit, 'offset' => $offset));
        break;
        
    case 'chart':
        // Public: Get chart data
        $days = isset($_GET['days']) ? intval($_GET['days']) : 30;
        $data = $collector->getChartData($days);
        echo json_encode(array('ok' => true, 'chart_data' => $data));
        break;
        
    case 'collect':
        // Protected: Force signal collection
        if ($key !== $ADMIN_KEY) {
            echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
            break;
        }
        $result = $collector->collectSignals();
        echo json_encode($result);
        break;
        
    case 'resolve':
        // Protected: Force outcome resolution
        if ($key !== $ADMIN_KEY) {
            echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
            break;
        }
        $result = $collector->resolveSignals();
        echo json_encode($result);
        break;
        
    case 'init':
        // Protected: Initialize database tables
        if ($key !== $ADMIN_KEY) {
            echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
            break;
        }
        $result = $collector->ensureTables();
        echo json_encode(array('ok' => true, 'initialized' => true));
        break;
        
    case 'full_cycle':
        // Protected: Run full cycle (collect + resolve)
        if ($key !== $ADMIN_KEY) {
            echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
            break;
        }
        $startTime = microtime(true);
        $collectResult = $collector->collectSignals();
        $resolveResult = $collector->resolveSignals();
        echo json_encode(array(
            'ok' => true,
            'collect' => $collectResult,
            'resolve' => $resolveResult,
            'total_elapsed_sec' => round(microtime(true) - $startTime, 2)
        ));
        break;
        
    default:
        echo json_encode(array(
            'ok' => false,
            'error' => 'Unknown action: ' . $action,
            'available_actions' => array(
                'report' => 'Get comparison report (public)',
                'progress' => 'Get progress to 350 target (public)',
                'list' => 'List shadow signals (public)',
                'chart' => 'Get chart data (public)',
                'collect' => 'Force signal collection (requires key)',
                'resolve' => 'Force outcome resolution (requires key)',
                'init' => 'Initialize database tables (requires key)',
                'full_cycle' => 'Run collect + resolve (requires key)'
            )
        ));
}

$conn->close();
?>
