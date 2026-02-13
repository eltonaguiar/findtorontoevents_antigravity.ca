<?php
/**
 * ML Prediction API for Meme Coin Trading
 * Loads trained XGBoost model and returns predictions
 * 
 * Endpoints:
 *   ?action=predict&symbol=DOGE&entry=0.15&tp=0.18&sl=0.13
 *   ?action=predict&symbol=DOGE (uses current market price)
 *   ?action=batch&symbols=DOGE,SHIB,PEPE
 *   ?action=health - Check model health
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
$MODELS_DIR = dirname(__FILE__) . '/models/';
$DATA_DIR = dirname(__FILE__) . '/data/';
$FEATURES_API = dirname(__FILE__) . '/features.php';

// Default model version
$DEFAULT_MODEL_VERSION = 'v1.0.0';

// Confidence thresholds
$CONFIDENCE_THRESHOLDS = array(
    'strong' => 0.75,
    'moderate' => 0.60,
    'lean' => 0.50
);

// ═══════════════════════════════════════════════════════════════════════
//  ML Predictor Class
// ═══════════════════════════════════════════════════════════════════════
class MemeMLPredictor {
    private $modelsDir;
    private $dataDir;
    private $currentModel;
    private $modelVersion;
    private $featureCache;
    
    public function __construct($modelsDir, $dataDir) {
        $this->modelsDir = $modelsDir;
        $this->dataDir = $dataDir;
        $this->featureCache = array();
        $this->loadModel();
    }
    
    /**
     * Load the latest trained model
     */
    private function loadModel() {
        // Try to load latest model
        $latestFile = $this->modelsDir . 'latest_model.txt';
        
        if (file_exists($latestFile)) {
            $modelName = trim(file_get_contents($latestFile));
            $modelPath = $this->modelsDir . $modelName . '.json';
            $metadataPath = $this->modelsDir . $modelName . '_metadata.json';
            
            if (file_exists($modelPath) && file_exists($metadataPath)) {
                $this->currentModel = $modelPath;
                $metadata = json_decode(file_get_contents($metadataPath), true);
                $this->modelVersion = isset($metadata['version']) ? $metadata['version'] : 'unknown';
                return true;
            }
        }
        
        // Try to find any model file
        $modelFiles = glob($this->modelsDir . 'meme_xgb_*.json');
        if (!empty($modelFiles)) {
            // Sort by modification time (newest first)
            usort($modelFiles, array($this, 'sortByMtime'));
            $this->currentModel = $modelFiles[0];
            
            // Extract version from filename
            if (preg_match('/meme_xgb_v[\d\.]+/', $this->currentModel, $matches)) {
                $this->modelVersion = str_replace('meme_xgb_', '', $matches[0]);
            } else {
                $this->modelVersion = 'unknown';
            }
            return true;
        }
        
        return false;
    }
    
    /**
     * Sort files by modification time (newest first)
     */
    private function sortByMtime($a, $b) {
        return filemtime($b) - filemtime($a);
    }
    
    /**
     * Load specific model version (for A/B testing)
     */
    public function loadSpecificModel($version) {
        $pattern = $this->modelsDir . 'meme_xgb_' . $version . '_*.json';
        $files = glob($pattern);
        
        if (!empty($files)) {
            usort($files, array($this, 'sortByMtime'));
            $this->currentModel = $files[0];
            $this->modelVersion = $version;
            return true;
        }
        
        return false;
    }
    
    /**
     * Make prediction for a symbol
     * 
     * @param string $symbol Coin symbol (e.g., DOGE)
     * @param float $entryPrice Entry price (optional, uses current if not provided)
     * @param float $takeProfit Take profit price (optional)
     * @param float $stopLoss Stop loss price (optional)
     * @return array Prediction result
     */
    public function predict($symbol, $entryPrice = null, $takeProfit = null, $stopLoss = null) {
        $symbol = strtoupper(trim($symbol));
        
        // Get features
        $features = $this->getFeatures($symbol);
        if (!$features || !isset($features['ok']) || !$features['ok']) {
            return array(
                'ok' => false,
                'error' => 'Failed to extract features for ' . $symbol,
                'symbol' => $symbol
            );
        }
        
        // Get current price if not provided
        if ($entryPrice === null) {
            $entryPrice = $this->getCurrentPrice($symbol);
        }
        
        // Calculate default TP/SL if not provided (based on volatility)
        if ($takeProfit === null || $stopLoss === null) {
            $targets = $this->calculateTargets($entryPrice, $features['features']);
            $takeProfit = $takeProfit !== null ? $takeProfit : $targets['tp'];
            $stopLoss = $stopLoss !== null ? $stopLoss : $targets['sl'];
        }
        
        // Calculate risk/reward
        $risk = $entryPrice - $stopLoss;
        $reward = $takeProfit - $entryPrice;
        $riskReward = $risk > 0 ? $reward / $risk : 0;
        
        // Make prediction using Python bridge or fallback
        $prediction = $this->runPrediction($features['feature_vector']);
        
        // Determine recommendation
        $recommendation = $this->determineRecommendation(
            $prediction['probability'],
            $prediction['confidence'],
            $riskReward,
            $features['features']
        );
        
        // Calculate expected return
        $expectedReturn = $this->calculateExpectedReturn(
            $prediction['probability'],
            $entryPrice,
            $takeProfit,
            $stopLoss
        );
        
        return array(
            'ok' => true,
            'symbol' => $symbol,
            'prediction' => $recommendation['action'],
            'probability' => round($prediction['probability'], 4),
            'confidence_tier' => $prediction['confidence_tier'],
            'expected_return' => round($expectedReturn, 4),
            'risk_reward' => round($riskReward, 2),
            'entry_price' => $entryPrice,
            'target_price' => $takeProfit,
            'stop_price' => $stopLoss,
            'features_used' => array_keys($features['feature_vector']),
            'feature_values' => $features['feature_vector'],
            'model_version' => $this->modelVersion,
            'model_loaded' => $this->currentModel !== null,
            'prediction_method' => $prediction['method'],
            'timestamp' => time()
        );
    }
    
    /**
     * Batch prediction for multiple symbols
     */
    public function batchPredict($symbols) {
        $results = array();
        $ranked = array();
        
        foreach ($symbols as $symbol) {
            $symbol = strtoupper(trim($symbol));
            $pred = $this->predict($symbol);
            $results[$symbol] = $pred;
            
            if ($pred['ok']) {
                $ranked[] = array(
                    'symbol' => $symbol,
                    'probability' => $pred['probability'],
                    'expected_return' => $pred['expected_return'],
                    'confidence_tier' => $pred['confidence_tier'],
                    'prediction' => $pred['prediction']
                );
            }
        }
        
        // Sort by probability (highest first)
        usort($ranked, array($this, 'sortByProbability'));
        
        return array(
            'ok' => true,
            'count' => count($results),
            'results' => $results,
            'ranked' => $ranked,
            'model_version' => $this->modelVersion,
            'timestamp' => time()
        );
    }
    
    /**
     * Get features from features.php API
     */
    private function getFeatures($symbol) {
        $cacheKey = 'features_' . strtolower($symbol);
        
        if (isset($this->featureCache[$cacheKey])) {
            return $this->featureCache[$cacheKey];
        }
        
        // Call features.php API
        $url = $this->getBaseUrl() . '/features.php?action=features&symbol=' . urlencode($symbol);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        
        $resp = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($httpCode !== 200 || !$resp) {
            // Return fallback features
            return $this->getFallbackFeatures($symbol);
        }
        
        $data = json_decode($resp, true);
        if (!$data || !isset($data['ok']) || !$data['ok']) {
            return $this->getFallbackFeatures($symbol);
        }
        
        $this->featureCache[$cacheKey] = $data;
        return $data;
    }
    
    /**
     * Get fallback features when API fails
     */
    private function getFallbackFeatures($symbol) {
        return array(
            'ok' => true,
            'symbol' => $symbol,
            'features' => array(
                'return_5m' => 0,
                'return_15m' => 0,
                'return_1h' => 0,
                'return_4h' => 0,
                'return_24h' => 0,
                'volatility_24h' => 0.05,
                'volume_ratio' => 1.0,
                'reddit_velocity' => 10,
                'trends_velocity' => 1.0,
                'sentiment_correlation' => 0.5,
                'btc_trend_4h' => 0,
                'btc_trend_24h' => 0,
                'hour' => intval(date('G')),
                'day_of_week' => intval(date('w')),
                'is_weekend' => (date('w') === '0' || date('w') === '6') ? 1 : 0
            ),
            'feature_vector' => array(
                'return_5m' => 0,
                'return_15m' => 0,
                'return_1h' => 0,
                'return_4h' => 0,
                'return_24h' => 0,
                'volatility_24h' => 0.05,
                'volume_ratio' => 1.0,
                'reddit_velocity' => 10,
                'trends_velocity' => 1.0,
                'sentiment_correlation' => 0.5,
                'btc_trend_4h' => 0,
                'btc_trend_24h' => 0,
                'hour' => intval(date('G')),
                'day_of_week' => intval(date('w')),
                'is_weekend' => (date('w') === '0' || date('w') === '6') ? 1 : 0
            ),
            'fallback' => true
        );
    }
    
    /**
     * Run prediction using available methods
     */
    private function runPrediction($featureVector) {
        // Try Python bridge first
        $pythonResult = $this->predictWithPython($featureVector);
        if ($pythonResult !== null) {
            return array(
                'probability' => $pythonResult['probability'],
                'confidence' => $pythonResult['probability'],
                'confidence_tier' => $this->getConfidenceTier($pythonResult['probability']),
                'method' => 'xgboost_python'
            );
        }
        
        // Fallback to rule-based prediction
        return $this->predictWithRules($featureVector);
    }
    
    /**
     * Predict using Python XGBoost model
     */
    private function predictWithPython($featureVector) {
        if (!$this->currentModel || !file_exists($this->currentModel)) {
            return null;
        }
        
        // Create temporary input file
        $inputFile = $this->dataDir . 'predict_input_' . uniqid() . '.json';
        $outputFile = $this->dataDir . 'predict_output_' . uniqid() . '.json';
        
        $inputData = array(
            'model_path' => $this->currentModel,
            'features' => array_values($featureVector)
        );
        
        file_put_contents($inputFile, json_encode($inputData));
        
        // Run Python prediction script
        $pythonScript = dirname(__FILE__) . '/predict_bridge.py';
        $cmd = "python " . escapeshellarg($pythonScript) . " " . 
               escapeshellarg($inputFile) . " " . escapeshellarg($outputFile) . " 2>&1";
        
        exec($cmd, $output, $returnCode);
        
        // Clean up input file
        @unlink($inputFile);
        
        if ($returnCode !== 0 || !file_exists($outputFile)) {
            return null;
        }
        
        $result = json_decode(file_get_contents($outputFile), true);
        @unlink($outputFile);
        
        if (!$result || !isset($result['probability'])) {
            return null;
        }
        
        return $result;
    }
    
    /**
     * Fallback rule-based prediction
     */
    private function predictWithRules($featureVector) {
        $fv = $featureVector;
        
        // Simple rule-based scoring (0-1 range)
        $score = 0.5; // Neutral start
        
        // Price momentum (positive = bullish)
        if ($fv['return_1h'] > 2) $score += 0.15;
        elseif ($fv['return_1h'] > 0) $score += 0.05;
        elseif ($fv['return_1h'] < -2) $score -= 0.15;
        else $score -= 0.05;
        
        if ($fv['return_4h'] > 5) $score += 0.1;
        elseif ($fv['return_4h'] < -5) $score -= 0.1;
        
        // Sentiment
        if ($fv['reddit_velocity'] > 20) $score += 0.1;
        if ($fv['trends_velocity'] > 1.3) $score += 0.1;
        if ($fv['sentiment_correlation'] > 0.6) $score += 0.1;
        
        // Market context
        if ($fv['btc_trend_4h'] > 1) $score += 0.05;
        elseif ($fv['btc_trend_4h'] < -1) $score -= 0.05;
        
        // Volatility (moderate is good)
        if ($fv['volatility_24h'] > 0.02 && $fv['volatility_24h'] < 0.1) $score += 0.05;
        elseif ($fv['volatility_24h'] > 0.15) $score -= 0.1;
        
        // Clamp to 0-1 range
        $probability = max(0, min(1, $score));
        
        return array(
            'probability' => $probability,
            'confidence' => $probability,
            'confidence_tier' => $this->getConfidenceTier($probability),
            'method' => 'rule_based_fallback'
        );
    }
    
    /**
     * Determine trading recommendation
     */
    private function determineRecommendation($probability, $confidence, $riskReward, $features) {
        $action = 'hold';
        $reason = '';
        
        // Base decision on probability
        if ($probability >= 0.70 && $riskReward >= 1.5) {
            $action = 'buy';
            $reason = 'High probability with good R/R';
        } elseif ($probability >= 0.60 && $riskReward >= 2.0) {
            $action = 'buy';
            $reason = 'Moderate probability with excellent R/R';
        } elseif ($probability <= 0.30 && $riskReward < 1.0) {
            $action = 'sell';
            $reason = 'Low probability, poor R/R';
        } elseif ($probability < 0.45) {
            $action = 'avoid';
            $reason = 'Probability too low';
        }
        
        // Override based on market conditions
        if ($features['btc_trend_24h'] < -5 && $action === 'buy') {
            $action = 'hold';
            $reason = 'Bearish BTC market - caution advised';
        }
        
        if ($features['volatility_24h'] > 0.2 && $action === 'buy') {
            $action = 'lean_buy';
            $reason = 'High volatility environment';
        }
        
        return array(
            'action' => $action,
            'reason' => $reason,
            'probability' => $probability,
            'risk_reward' => $riskReward
        );
    }
    
    /**
     * Calculate expected return
     */
    private function calculateExpectedReturn($probability, $entry, $tp, $sl) {
        $winAmount = $tp - $entry;
        $lossAmount = $entry - $sl;
        
        $expectedValue = ($probability * $winAmount) - ((1 - $probability) * $lossAmount);
        
        // Return as percentage
        return $entry > 0 ? ($expectedValue / $entry) * 100 : 0;
    }
    
    /**
     * Calculate take-profit and stop-loss based on volatility
     */
    private function calculateTargets($entryPrice, $features) {
        $volatility = isset($features['volatility_24h']) ? $features['volatility_24h'] : 0.05;
        
        // Target: 1.5x to 2x daily volatility
        $targetPct = min(20, max(3, $volatility * 150));
        $stopPct = min(10, max(2, $volatility * 75));
        
        $tp = $entryPrice * (1 + $targetPct / 100);
        $sl = $entryPrice * (1 - $stopPct / 100);
        
        return array('tp' => $tp, 'sl' => $sl);
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
     * Get confidence tier from probability
     */
    private function getConfidenceTier($probability) {
        global $CONFIDENCE_THRESHOLDS;
        
        $distanceFrom50 = abs($probability - 0.5) * 2; // Scale to 0-1
        
        if ($distanceFrom50 >= $CONFIDENCE_THRESHOLDS['strong']) {
            return 'strong';
        } elseif ($distanceFrom50 >= $CONFIDENCE_THRESHOLDS['moderate']) {
            return 'moderate';
        } else {
            return 'lean';
        }
    }
    
    /**
     * Get base URL for API calls
     */
    private function getBaseUrl() {
        $protocol = isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on' ? 'https' : 'http';
        $host = $_SERVER['HTTP_HOST'];
        $dir = dirname($_SERVER['SCRIPT_NAME']);
        return $protocol . '://' . $host . $dir;
    }
    
    /**
     * Sort by probability (descending)
     */
    private function sortByProbability($a, $b) {
        if ($a['probability'] == $b['probability']) return 0;
        return ($a['probability'] > $b['probability']) ? -1 : 1;
    }
    
    /**
     * Get model health status
     */
    public function getHealth() {
        $modelExists = $this->currentModel && file_exists($this->currentModel);
        $modelAge = $modelExists ? time() - filemtime($this->currentModel) : null;
        
        $status = 'healthy';
        $issues = array();
        
        if (!$modelExists) {
            $status = 'critical';
            $issues[] = 'No trained model found';
        } elseif ($modelAge > 7 * 24 * 3600) {
            $status = 'warning';
            $issues[] = 'Model is older than 7 days';
        }
        
        // Check features API
        $featuresHealthy = file_exists($this->getBaseUrl() . '/features.php');
        
        return array(
            'ok' => true,
            'status' => $status,
            'model_loaded' => $modelExists,
            'model_version' => $this->modelVersion,
            'model_path' => $this->currentModel,
            'model_age_hours' => $modelAge ? round($modelAge / 3600, 1) : null,
            'features_api_available' => $featuresHealthy,
            'issues' => $issues,
            'timestamp' => time()
        );
    }
    
    /**
     * Get available model versions for A/B testing
     */
    public function getAvailableModels() {
        $models = array();
        $files = glob($this->modelsDir . 'meme_xgb_*.json');
        
        foreach ($files as $file) {
            $basename = basename($file, '.json');
            if (preg_match('/meme_xgb_(v[\d\.]+)_(\d{8}_\d{6})/', $basename, $matches)) {
                $models[] = array(
                    'name' => $basename,
                    'version' => $matches[1],
                    'timestamp' => $matches[2],
                    'created' => date('Y-m-d H:i:s', filemtime($file)),
                    'size_mb' => round(filesize($file) / 1048576, 2)
                );
            }
        }
        
        // Sort by timestamp (newest first)
        usort($models, array($this, 'sortByTimestamp'));
        
        return $models;
    }
    
    private function sortByTimestamp($a, $b) {
        return strcmp($b['timestamp'], $a['timestamp']);
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  API Endpoint Handler
// ═══════════════════════════════════════════════════════════════════════

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'predict';
$modelVersion = isset($_GET['model_version']) ? $_GET['model_version'] : null;

$predictor = new MemeMLPredictor($MODELS_DIR, $DATA_DIR);

// Load specific model version if requested (A/B testing)
if ($modelVersion !== null) {
    $predictor->loadSpecificModel($modelVersion);
}

switch ($action) {
    case 'predict':
        $symbol = isset($_GET['symbol']) ? trim($_GET['symbol']) : '';
        $entry = isset($_GET['entry']) ? floatval($_GET['entry']) : null;
        $tp = isset($_GET['tp']) ? floatval($_GET['tp']) : null;
        $sl = isset($_GET['sl']) ? floatval($_GET['sl']) : null;
        
        if (empty($symbol)) {
            echo json_encode(array(
                'ok' => false,
                'error' => 'Symbol parameter required. Usage: ?action=predict&symbol=DOGE&entry=0.15&tp=0.18&sl=0.13'
            ));
            break;
        }
        
        $result = $predictor->predict($symbol, $entry, $tp, $sl);
        echo json_encode($result);
        break;
        
    case 'batch':
        $symbols = isset($_GET['symbols']) ? explode(',', $_GET['symbols']) : array();
        
        if (empty($symbols)) {
            echo json_encode(array(
                'ok' => false,
                'error' => 'Symbols parameter required. Usage: ?action=batch&symbols=DOGE,SHIB,PEPE'
            ));
            break;
        }
        
        $result = $predictor->batchPredict($symbols);
        echo json_encode($result);
        break;
        
    case 'health':
        $result = $predictor->getHealth();
        echo json_encode($result);
        break;
        
    case 'models':
        $models = $predictor->getAvailableModels();
        echo json_encode(array(
            'ok' => true,
            'models' => $models,
            'count' => count($models)
        ));
        break;
        
    default:
        echo json_encode(array(
            'ok' => false,
            'error' => 'Unknown action: ' . $action,
            'available_actions' => array('predict', 'batch', 'health', 'models'),
            'usage' => array(
                'predict' => '?action=predict&symbol=DOGE&entry=0.15&tp=0.18&sl=0.13',
                'batch' => '?action=batch&symbols=DOGE,SHIB,PEPE',
                'health' => '?action=health',
                'models' => '?action=models'
            )
        ));
}
?>
