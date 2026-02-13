<?php
/**
 * ML Feature Engineering Module for Meme Coin Price Prediction
 * Extracts features from multiple data sources for XGBoost model
 * 
 * Endpoints:
 *   ?action=features&symbol=DOGE     - Get features for symbol
 *   ?action=batch&symbols=DOGE,SHIB  - Get features for multiple symbols
 *   ?action=history&symbol=DOGE      - Get historical features with labels
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

// Database configuration
require_once dirname(__FILE__) . '/../api/db_config.php';

// ═══════════════════════════════════════════════════════════════════════
//  Configuration
// ═══════════════════════════════════════════════════════════════════════
$CACHE_DIR = dirname(__FILE__) . '/data/cache/';
$CACHE_TTL = 60; // 1 minute for real-time data

if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

// Connect to databases
$meme_conn = new mysqli($servername, 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($meme_conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Meme DB connection failed'));
    exit;
}
$meme_conn->set_charset('utf8');

// ═══════════════════════════════════════════════════════════════════════
//  Feature Extractor Class
// ═══════════════════════════════════════════════════════════════════════
class MemeFeatureExtractor {
    private $memeConn;
    private $cacheDir;
    private $cacheTtl;
    
    public function __construct($memeConn, $cacheDir, $cacheTtl = 60) {
        $this->memeConn = $memeConn;
        $this->cacheDir = $cacheDir;
        $this->cacheTtl = $cacheTtl;
    }
    
    /**
     * Extract all features for a symbol
     * 
     * @param string $symbol The crypto symbol (e.g., DOGE, SHIB)
     * @return array Feature vector
     */
    public function extractFeatures($symbol) {
        $symbol = strtoupper(trim($symbol));
        $cacheKey = 'features_' . strtolower($symbol);
        
        // Check cache
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        $features = array();
        
        // 1. Price Features
        $priceFeatures = $this->extractPriceFeatures($symbol);
        $features = array_merge($features, $priceFeatures);
        
        // 2. Sentiment Features
        $sentimentFeatures = $this->extractSentimentFeatures($symbol);
        $features = array_merge($features, $sentimentFeatures);
        
        // 3. Market Features
        $marketFeatures = $this->extractMarketFeatures();
        $features = array_merge($features, $marketFeatures);
        
        // 4. Time Features
        $timeFeatures = $this->extractTimeFeatures();
        $features = array_merge($features, $timeFeatures);
        
        $result = array(
            'ok' => true,
            'symbol' => $symbol,
            'features' => $features,
            'feature_vector' => $this->buildFeatureVector($features),
            'timestamp' => time(),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Extract price-based features
     */
    private function extractPriceFeatures($symbol) {
        $features = array();
        
        // Get OHLC data from Kraken
        $ohlc = $this->fetchKrakenOHLC($symbol . 'USD', 5); // 5-minute intervals
        
        if ($ohlc === null || empty($ohlc)) {
            // Return default values if no data
            return array(
                'return_5m' => 0,
                'return_15m' => 0,
                'return_1h' => 0,
                'return_4h' => 0,
                'return_24h' => 0,
                'volatility_24h' => 0,
                'volume_ratio' => 1.0,
                'price_momentum' => 0,
                'price_acceleration' => 0
            );
        }
        
        $candles = $ohlc;
        $n = count($candles);
        
        // Current price
        $currentPrice = floatval($candles[$n - 1][4]);
        
        // Returns over different timeframes
        $price5mAgo = $n >= 2 ? floatval($candles[$n - 2][4]) : $currentPrice;
        $price15mAgo = $n >= 4 ? floatval($candles[$n - 4][4]) : $price5mAgo;
        $price1hAgo = $n >= 12 ? floatval($candles[$n - 12][4]) : $price15mAgo;
        $price4hAgo = $n >= 48 ? floatval($candles[$n - 48][4]) : $price1hAgo;
        $price24hAgo = $n >= 288 ? floatval($candles[0][4]) : ($n > 0 ? floatval($candles[0][4]) : $currentPrice);
        
        $features['return_5m'] = $this->calculateReturn($currentPrice, $price5mAgo);
        $features['return_15m'] = $this->calculateReturn($currentPrice, $price15mAgo);
        $features['return_1h'] = $this->calculateReturn($currentPrice, $price1hAgo);
        $features['return_4h'] = $this->calculateReturn($currentPrice, $price4hAgo);
        $features['return_24h'] = $this->calculateReturn($currentPrice, $price24hAgo);
        
        // Volatility (standard deviation of returns over last 24h)
        $returns = array();
        $startIdx = max(0, $n - 288); // Last 24h (288 5-min candles)
        for ($i = $startIdx + 1; $i < $n; $i++) {
            $prev = floatval($candles[$i - 1][4]);
            $curr = floatval($candles[$i][4]);
            if ($prev > 0) {
                $returns[] = ($curr - $prev) / $prev;
            }
        }
        $features['volatility_24h'] = $this->calculateVolatility($returns);
        
        // Volume profile (current vs 24h average)
        $currentVolume = floatval($candles[$n - 1][6]);
        $totalVolume = 0;
        for ($i = $startIdx; $i < $n; $i++) {
            $totalVolume += floatval($candles[$i][6]);
        }
        $avgVolume = ($n - $startIdx) > 0 ? $totalVolume / ($n - $startIdx) : $currentVolume;
        $features['volume_ratio'] = $avgVolume > 0 ? $currentVolume / $avgVolume : 1.0;
        
        // Price momentum (rate of change)
        $features['price_momentum'] = $features['return_1h'];
        
        // Price acceleration (change in momentum)
        $features['price_acceleration'] = $features['return_5m'] - ($n >= 3 ? 
            $this->calculateReturn(floatval($candles[$n - 2][4]), floatval($candles[$n - 3][4])) : 0);
        
        return $features;
    }
    
    /**
     * Extract sentiment features from Reddit and Google Trends
     */
    private function extractSentimentFeatures($symbol) {
        $features = array();
        
        // 1. Reddit sentiment
        $redditData = $this->fetchRedditSentiment($symbol);
        $features['reddit_velocity'] = isset($redditData['comment_velocity']) ? $redditData['comment_velocity'] : 0;
        $features['reddit_sentiment'] = isset($redditData['sentiment_score']) ? $redditData['sentiment_score'] : 0;
        $features['reddit_mentions'] = isset($redditData['mentions_24h']) ? $redditData['mentions_24h'] : 0;
        
        // 2. Google Trends velocity
        $trendsData = $this->fetchTrendsData($symbol);
        $features['trends_velocity'] = isset($trendsData['interest_velocity']) ? $trendsData['interest_velocity'] : 1.0;
        $features['trends_current'] = isset($trendsData['current_interest']) ? $trendsData['current_interest'] : 50;
        
        // 3. Cross-platform sentiment correlation
        // Correlation between Reddit sentiment and Google Trends
        $redditNorm = ($features['reddit_sentiment'] + 1) / 2; // Normalize to 0-1
        $trendsNorm = $features['trends_current'] / 100; // Normalize to 0-1
        $features['sentiment_correlation'] = $redditNorm * $trendsNorm;
        
        // 4. Sentiment acceleration (change in velocity)
        // Calculate by comparing current to historical
        $historicalSentiment = $this->fetchHistoricalSentiment($symbol, 6); // 6 hours ago
        $features['sentiment_acceleration'] = $features['reddit_velocity'] - $historicalSentiment['velocity_6h_ago'];
        
        // 5. Social momentum composite
        $features['social_momentum'] = (
            $features['reddit_velocity'] * 0.4 +
            ($features['trends_velocity'] - 1) * 0.3 +
            $features['reddit_sentiment'] * 0.3
        );
        
        return $features;
    }
    
    /**
     * Extract market-wide features
     */
    private function extractMarketFeatures() {
        $features = array();
        
        // BTC trend as market regime indicator
        $btcOhlc = $this->fetchKrakenOHLC('BTCUSD', 60); // 1h intervals
        
        if ($btcOhlc !== null && count($btcOhlc) >= 24) {
            $n = count($btcOhlc);
            $btcCurrent = floatval($btcOhlc[$n - 1][4]);
            $btc4hAgo = floatval($btcOhlc[max(0, $n - 5)][4]);
            $btc24hAgo = floatval($btcOhlc[0][4]);
            
            $features['btc_trend_4h'] = $this->calculateReturn($btcCurrent, $btc4hAgo);
            $features['btc_trend_24h'] = $this->calculateReturn($btcCurrent, $btc24hAgo);
        } else {
            $features['btc_trend_4h'] = 0;
            $features['btc_trend_24h'] = 0;
        }
        
        // Market fear/greed proxy (based on BTC volatility and trend)
        $btcReturns = array();
        for ($i = 1; $i < count($btcOhlc); $i++) {
            $prev = floatval($btcOhlc[$i - 1][4]);
            $curr = floatval($btcOhlc[$i][4]);
            if ($prev > 0) {
                $btcReturns[] = ($curr - $prev) / $prev;
            }
        }
        $btcVolatility = $this->calculateVolatility($btcReturns);
        
        // Fear when high volatility + negative trend
        $fearIndicator = ($btcVolatility * 100) * (1 - ($features['btc_trend_4h'] > 0 ? 0.5 : 1));
        $features['market_fear_proxy'] = min(100, max(0, $fearIndicator));
        
        // Market regime (bull/bear/sideways)
        if ($features['btc_trend_24h'] > 5) {
            $features['market_regime'] = 1; // Bull
        } elseif ($features['btc_trend_24h'] < -5) {
            $features['market_regime'] = -1; // Bear
        } else {
            $features['market_regime'] = 0; // Sideways
        }
        
        return $features;
    }
    
    /**
     * Extract time-based features
     */
    private function extractTimeFeatures() {
        $features = array();
        
        $now = time();
        
        // Hour of day (0-23)
        $features['hour'] = intval(date('G', $now));
        
        // Day of week (0-6, 0 = Sunday)
        $features['day_of_week'] = intval(date('w', $now));
        
        // Weekend flag
        $features['is_weekend'] = ($features['day_of_week'] === 0 || $features['day_of_week'] === 6) ? 1 : 0;
        
        // Session (0=Asia, 1=Europe, 2=US)
        if ($features['hour'] >= 0 && $features['hour'] < 8) {
            $features['session'] = 0; // Asia
        } elseif ($features['hour'] >= 8 && $features['hour'] < 16) {
            $features['session'] = 1; // Europe
        } else {
            $features['session'] = 2; // US
        }
        
        // Crypto market hours (higher volatility periods)
        // Higher activity during US market hours (9:30 AM - 4:00 PM EST = 14:30-21:00 UTC)
        $features['us_market_hours'] = ($features['hour'] >= 14 && $features['hour'] <= 21) ? 1 : 0;
        
        return $features;
    }
    
    /**
     * Build ordered feature vector for ML model
     */
    private function buildFeatureVector($features) {
        // Order must match the training script feature order
        $vector = array(
            'return_5m' => $features['return_5m'],
            'return_15m' => $features['return_15m'],
            'return_1h' => $features['return_1h'],
            'return_4h' => $features['return_4h'],
            'return_24h' => $features['return_24h'],
            'volatility_24h' => $features['volatility_24h'],
            'volume_ratio' => $features['volume_ratio'],
            'reddit_velocity' => $features['reddit_velocity'],
            'trends_velocity' => $features['trends_velocity'],
            'sentiment_correlation' => $features['sentiment_correlation'],
            'btc_trend_4h' => $features['btc_trend_4h'],
            'btc_trend_24h' => $features['btc_trend_24h'],
            'hour' => $features['hour'],
            'day_of_week' => $features['day_of_week'],
            'is_weekend' => $features['is_weekend']
        );
        
        return $vector;
    }
    
    /**
     * Get historical features with labels for training
     */
    public function getHistoricalFeatures($symbol, $days = 30) {
        $symbol = strtoupper(trim($symbol));
        
        // Query mc_winners for historical signals with outcomes
        $query = "SELECT 
            id,
            pair,
            score,
            entry_price,
            target_price,
            stop_price,
            outcome,
            pnl_pct,
            created_at,
            resolved_at
        FROM mc_winners
        WHERE pair LIKE '%{$symbol}%'
        AND created_at > DATE_SUB(NOW(), INTERVAL {$days} DAY)
        AND outcome IS NOT NULL
        ORDER BY created_at DESC";
        
        $res = $this->memeConn->query($query);
        
        $samples = array();
        while ($res && $row = $res->fetch_assoc()) {
            // Reconstruct features for this historical point
            $timestamp = strtotime($row['created_at']);
            
            // Get features that would have been available at signal time
            $historicalFeatures = $this->reconstructHistoricalFeatures($row['pair'], $timestamp);
            
            $samples[] = array(
                'signal_id' => $row['id'],
                'symbol' => $symbol,
                'features' => $historicalFeatures,
                'feature_vector' => array_values($this->buildFeatureVector($historicalFeatures)),
                'target' => ($row['outcome'] === 'win' || $row['outcome'] === 'partial_win') ? 1 : 0,
                'outcome' => $row['outcome'],
                'pnl_pct' => floatval($row['pnl_pct']),
                'timestamp' => $timestamp
            );
        }
        
        return array(
            'ok' => true,
            'symbol' => $symbol,
            'samples' => $samples,
            'count' => count($samples)
        );
    }
    
    /**
     * Reconstruct features for a historical timestamp
     * This simulates what features would have been available at that time
     */
    private function reconstructHistoricalFeatures($pair, $timestamp) {
        // Default features (in production, would query historical data)
        return array(
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
            'hour' => intval(date('G', $timestamp)),
            'day_of_week' => intval(date('w', $timestamp)),
            'is_weekend' => (date('w', $timestamp) === '0' || date('w', $timestamp) === '6') ? 1 : 0
        );
    }
    
    /**
     * Fetch OHLC data from Kraken
     */
    private function fetchKrakenOHLC($pair, $interval = 5) {
        $cacheKey = 'kraken_ohlc_' . strtolower($pair) . '_' . $interval;
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            return $cached;
        }
        
        $url = 'https://api.kraken.com/0/public/OHLC?pair=' . urlencode($pair) . '&interval=' . intval($interval);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'MemeML/1.0');
        
        $resp = curl_exec($ch);
        curl_close($ch);
        
        if (!$resp) {
            return null;
        }
        
        $data = json_decode($resp, true);
        if (isset($data['error']) && !empty($data['error'])) {
            return null;
        }
        
        $resultKey = array_keys($data['result']);
        if (empty($resultKey)) {
            return null;
        }
        
        $ohlc = $data['result'][$resultKey[0]];
        $this->setCache($cacheKey, $ohlc);
        
        return $ohlc;
    }
    
    /**
     * Fetch Reddit sentiment data
     */
    private function fetchRedditSentiment($symbol) {
        $cacheKey = 'reddit_' . strtolower($symbol);
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            return $cached;
        }
        
        // Call sentiment_reddit.php API
        $url = 'http' . (isset($_SERVER['HTTPS']) ? 's' : '') . '://' . $_SERVER['HTTP_HOST'] . 
               dirname($_SERVER['SCRIPT_NAME']) . '/../api/sentiment_reddit.php?action=sentiment&symbol=' . urlencode($symbol);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        
        $resp = curl_exec($ch);
        curl_close($ch);
        
        if (!$resp) {
            return array(
                'sentiment_score' => 0,
                'comment_velocity' => 0,
                'mentions_24h' => 0
            );
        }
        
        $data = json_decode($resp, true);
        if (!$data || !isset($data['ok']) || !$data['ok']) {
            return array(
                'sentiment_score' => 0,
                'comment_velocity' => 0,
                'mentions_24h' => 0
            );
        }
        
        $this->setCache($cacheKey, $data);
        return $data;
    }
    
    /**
     * Fetch Google Trends data
     */
    private function fetchTrendsData($symbol) {
        $cacheKey = 'trends_' . strtolower($symbol);
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            return $cached;
        }
        
        // Call sentiment_trends.php API
        $url = 'http' . (isset($_SERVER['HTTPS']) ? 's' : '') . '://' . $_SERVER['HTTP_HOST'] . 
               dirname($_SERVER['SCRIPT_NAME']) . '/../api/sentiment_trends.php?action=sentiment&symbol=' . urlencode($symbol);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        
        $resp = curl_exec($ch);
        curl_close($ch);
        
        if (!$resp) {
            return array(
                'current_interest' => 50,
                'interest_velocity' => 1.0
            );
        }
        
        $data = json_decode($resp, true);
        if (!$data || !isset($data['ok']) || !$data['ok']) {
            return array(
                'current_interest' => 50,
                'interest_velocity' => 1.0
            );
        }
        
        $this->setCache($cacheKey, $data);
        return $data;
    }
    
    /**
     * Fetch historical sentiment for acceleration calculation
     */
    private function fetchHistoricalSentiment($symbol, $hoursAgo) {
        // Simplified - in production would query historical cache or database
        return array(
            'velocity_6h_ago' => 5 // Default assumption
        );
    }
    
    /**
     * Calculate percentage return
     */
    private function calculateReturn($current, $previous) {
        if ($previous <= 0) return 0;
        return (($current - $previous) / $previous) * 100;
    }
    
    /**
     * Calculate volatility (standard deviation)
     */
    private function calculateVolatility($returns) {
        if (count($returns) < 2) return 0;
        
        $mean = array_sum($returns) / count($returns);
        $sumSquaredDiff = 0;
        foreach ($returns as $r) {
            $sumSquaredDiff += pow($r - $mean, 2);
        }
        $variance = $sumSquaredDiff / (count($returns) - 1);
        return sqrt($variance);
    }
    
    /**
     * Get from cache
     */
    private function getCache($key) {
        $file = $this->cacheDir . $key . '.json';
        if (file_exists($file)) {
            $age = time() - filemtime($file);
            if ($age < $this->cacheTtl) {
                $content = @file_get_contents($file);
                if ($content !== false) {
                    return json_decode($content, true);
                }
            }
        }
        return null;
    }
    
    /**
     * Save to cache
     */
    private function setCache($key, $data) {
        $file = $this->cacheDir . $key . '.json';
        @file_put_contents($file, json_encode($data));
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  API Endpoint Handler
// ═══════════════════════════════════════════════════════════════════════

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'features';
$extractor = new MemeFeatureExtractor($meme_conn, $CACHE_DIR, $CACHE_TTL);

switch ($action) {
    case 'features':
        $symbol = isset($_GET['symbol']) ? trim($_GET['symbol']) : '';
        if (empty($symbol)) {
            echo json_encode(array('ok' => false, 'error' => 'Symbol parameter required'));
            break;
        }
        $result = $extractor->extractFeatures($symbol);
        echo json_encode($result);
        break;
        
    case 'batch':
        $symbols = isset($_GET['symbols']) ? explode(',', $_GET['symbols']) : array();
        if (empty($symbols)) {
            echo json_encode(array('ok' => false, 'error' => 'Symbols parameter required (comma-separated)'));
            break;
        }
        
        $results = array();
        foreach ($symbols as $sym) {
            $sym = trim($sym);
            if (!empty($sym)) {
                $results[$sym] = $extractor->extractFeatures($sym);
            }
        }
        
        echo json_encode(array(
            'ok' => true,
            'count' => count($results),
            'results' => $results
        ));
        break;
        
    case 'history':
        $symbol = isset($_GET['symbol']) ? trim($_GET['symbol']) : '';
        $days = isset($_GET['days']) ? intval($_GET['days']) : 30;
        
        if (empty($symbol)) {
            echo json_encode(array('ok' => false, 'error' => 'Symbol parameter required'));
            break;
        }
        
        $result = $extractor->getHistoricalFeatures($symbol, $days);
        echo json_encode($result);
        break;
        
    default:
        echo json_encode(array(
            'ok' => false,
            'error' => 'Unknown action: ' . $action,
            'available_actions' => array('features', 'batch', 'history')
        ));
}

$meme_conn->close();
?>
