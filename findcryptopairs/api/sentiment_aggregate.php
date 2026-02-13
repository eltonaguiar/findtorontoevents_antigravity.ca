<?php
/**
 * Unified Sentiment Aggregator
 * Combines data from multiple sources (Reddit, Google Trends, 4chan, Nitter) into a single consensus score
 * 
 * API Endpoints:
 *   ?action=sentiment&symbol=DOGE          - Get aggregated sentiment
 *   ?action=detailed&symbol=DOGE           - Get raw source data + consensus
 *   ?action=batch&symbols=DOGE,SHIB,PEPE   - Batch processing
 *   ?action=trending&limit=20              - Get trending across all sources
 *   ?action=health                         - Health check
 *
 * PHP 5.2+ compatible
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

error_reporting(0);
ini_set('display_errors', '0');

// ═══════════════════════════════════════════════════════════════════════════════
// Configuration
// ═══════════════════════════════════════════════════════════════════════════════
$CACHE_DIR = dirname(__FILE__) . '/../../cache/sentiment_aggregate/';
$CACHE_TTL_AGGREGATE = 120; // 2 minutes for aggregated results
$CACHE_TTL_HEALTH = 60;     // 1 minute for health check
$ADMIN_KEY = 'aggregate2026';

// Source weights and reliability scores
$SOURCE_CONFIG = array(
    'reddit' => array(
        'weight' => 0.30,
        'confidence' => 0.80,
        'reliability' => 0.85,
        'endpoint' => 'sentiment_reddit.php'
    ),
    'trends' => array(
        'weight' => 0.25,
        'confidence' => 0.90,
        'reliability' => 0.90,
        'endpoint' => 'sentiment_trends.php'
    ),
    'fourchan' => array(
        'weight' => 0.20,
        'confidence' => 0.60,
        'reliability' => 0.65,
        'endpoint' => 'sentiment_4chan.php'
    ),
    'nitter' => array(
        'weight' => 0.25,
        'confidence' => 0.70,
        'reliability' => 0.75,
        'endpoint' => 'sentiment_nitter.php'
    )
);

// Ensure cache directory exists
if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main Router
// ═══════════════════════════════════════════════════════════════════════════════
$action = isset($_GET['action']) ? $_GET['action'] : 'sentiment';
$key = isset($_GET['key']) ? $_GET['key'] : '';

$aggregator = new SentimentAggregator($CACHE_DIR, $CACHE_TTL_AGGREGATE, $SOURCE_CONFIG);

switch ($action) {
    case 'sentiment':
        $symbol = isset($_GET['symbol']) ? strtoupper(trim($_GET['symbol'])) : '';
        if (empty($symbol)) {
            echo json_encode(array('ok' => false, 'error' => 'Symbol parameter required. Usage: ?action=sentiment&symbol=DOGE'));
            exit;
        }
        $result = $aggregator->getAggregatedSentiment($symbol);
        echo json_encode($result);
        break;
        
    case 'detailed':
        $symbol = isset($_GET['symbol']) ? strtoupper(trim($_GET['symbol'])) : '';
        if (empty($symbol)) {
            echo json_encode(array('ok' => false, 'error' => 'Symbol parameter required'));
            exit;
        }
        $result = $aggregator->getDetailedSentiment($symbol);
        echo json_encode($result);
        break;
        
    case 'batch':
        $symbols = isset($_GET['symbols']) ? explode(',', $_GET['symbols']) : array();
        if (empty($symbols)) {
            echo json_encode(array('ok' => false, 'error' => 'Symbols parameter required. Usage: ?action=batch&symbols=DOGE,SHIB,PEPE'));
            exit;
        }
        $result = $aggregator->getBatchSentiment($symbols);
        echo json_encode($result);
        break;
        
    case 'trending':
        $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 20;
        if ($limit > 50) $limit = 50;
        $result = $aggregator->getTrendingCoins($limit);
        echo json_encode($result);
        break;
        
    case 'health':
        $result = $aggregator->healthCheck();
        echo json_encode($result);
        break;
        
    case 'flush':
        if ($key !== $ADMIN_KEY) {
            echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
            exit;
        }
        $result = $aggregator->flushCache();
        echo json_encode($result);
        break;
        
    default:
        echo json_encode(array(
            'ok' => false,
            'error' => 'Unknown action: ' . $action,
            'available_actions' => array('sentiment', 'detailed', 'batch', 'trending', 'health', 'flush')
        ));
}

// ═══════════════════════════════════════════════════════════════════════════════
// Sentiment Aggregator Class
// ═══════════════════════════════════════════════════════════════════════════════
class SentimentAggregator {
    private $cacheDir;
    private $cacheTtl;
    private $sourceConfig;
    private $apiBaseUrl;
    
    public function __construct($cacheDir, $cacheTtl, $sourceConfig) {
        $this->cacheDir = $cacheDir;
        $this->cacheTtl = $cacheTtl;
        $this->sourceConfig = $sourceConfig;
        $this->apiBaseUrl = dirname(__FILE__);
    }
    
    /**
     * Get aggregated sentiment for a symbol
     */
    public function getAggregatedSentiment($symbol) {
        $cacheKey = 'agg_' . strtolower($symbol);
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        // Fetch data from all sources
        $sources = $this->fetchAllSources($symbol);
        
        // Calculate consensus
        $consensus = $this->calculateConsensus($sources);
        
        // Calculate advanced metrics
        $advancedMetrics = $this->calculateAdvancedMetrics($sources, $consensus);
        
        // Generate alerts
        $alerts = $this->generateAlerts($sources, $consensus, $advancedMetrics);
        
        // Build result
        $result = array(
            'ok' => true,
            'symbol' => strtoupper($symbol),
            'timestamp' => time(),
            'consensus' => $consensus,
            'advanced_metrics' => $advancedMetrics,
            'alerts' => $alerts,
            'sources_used' => count(array_filter($sources, array($this, 'isSourceValid'))),
            'sources_total' => count($sources),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Get detailed sentiment with raw source data
     */
    public function getDetailedSentiment($symbol) {
        $cacheKey = 'detailed_' . strtolower($symbol);
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        // Fetch data from all sources
        $sources = $this->fetchAllSources($symbol);
        
        // Format sources for output
        $formattedSources = $this->formatSourcesForOutput($sources);
        
        // Calculate consensus
        $consensus = $this->calculateConsensus($sources);
        
        // Calculate advanced metrics
        $advancedMetrics = $this->calculateAdvancedMetrics($sources, $consensus);
        
        // Generate alerts
        $alerts = $this->generateAlerts($sources, $consensus, $advancedMetrics);
        
        $result = array(
            'ok' => true,
            'symbol' => strtoupper($symbol),
            'timestamp' => time(),
            'consensus' => $consensus,
            'sources' => $formattedSources,
            'advanced_metrics' => $advancedMetrics,
            'alerts' => $alerts,
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Get batch sentiment for multiple symbols
     */
    public function getBatchSentiment($symbols) {
        // Limit to 10 symbols per batch
        $symbols = array_slice($symbols, 0, 10);
        
        $results = array();
        $latencyMs = 0;
        $start = microtime(true);
        
        foreach ($symbols as $symbol) {
            $symbol = strtoupper(trim($symbol));
            if (empty($symbol)) continue;
            
            $results[$symbol] = $this->getAggregatedSentiment($symbol);
        }
        
        $latencyMs = round((microtime(true) - $start) * 1000, 1);
        
        return array(
            'ok' => true,
            'symbols' => $symbols,
            'results' => $results,
            'count' => count($results),
            'latency_ms' => $latencyMs,
            'timestamp' => time()
        );
    }
    
    /**
     * Get trending coins across all sources
     */
    public function getTrendingCoins($limit = 20) {
        $cacheKey = 'trending_' . $limit;
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        // Fetch trending from each source
        $allTrending = array();
        
        foreach ($this->sourceConfig as $source => $config) {
            $trending = $this->fetchSourceTrending($source, $limit);
            if ($trending !== null) {
                foreach ($trending as $coin) {
                    $symbol = isset($coin['symbol']) ? $coin['symbol'] : '';
                    if (empty($symbol)) continue;
                    
                    if (!isset($allTrending[$symbol])) {
                        $allTrending[$symbol] = array(
                            'symbol' => $symbol,
                            'sources' => array(),
                            'total_mentions' => 0,
                            'weighted_score' => 0
                        );
                    }
                    
                    $allTrending[$symbol]['sources'][$source] = $coin;
                    $allTrending[$symbol]['total_mentions'] += isset($coin['mentions']) ? $coin['mentions'] : 0;
                    $allTrending[$symbol]['weighted_score'] += isset($coin['trending_score']) ? $coin['trending_score'] * $config['weight'] : 0;
                }
            }
        }
        
        // Sort by weighted score
        uasort($allTrending, array($this, 'sortByWeightedScore'));
        
        // Take top N
        $trending = array_slice($allTrending, 0, $limit, true);
        
        // Add aggregated sentiment for each
        foreach ($trending as $symbol => &$data) {
            $agg = $this->getAggregatedSentiment($symbol);
            if ($agg['ok']) {
                $data['consensus_score'] = $agg['consensus']['score'];
                $data['consensus_label'] = $agg['consensus']['label'];
                $data['confidence'] = $agg['consensus']['confidence'];
            }
        }
        
        $result = array(
            'ok' => true,
            'trending_coins' => array_values($trending),
            'total_found' => count($allTrending),
            'sources_checked' => count($this->sourceConfig),
            'timestamp' => time(),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Health check for all sources
     */
    public function healthCheck() {
        $cacheKey = 'health';
        $cached = $this->getCache($cacheKey, 60); // 1 minute TTL for health
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        $sources = array();
        $healthy = 0;
        $total = 0;
        
        foreach ($this->sourceConfig as $source => $config) {
            $total++;
            $health = $this->checkSourceHealth($source);
            $sources[$source] = $health;
            
            if ($health['ok']) {
                $healthy++;
            }
        }
        
        $result = array(
            'ok' => $healthy > 0,
            'status' => $healthy === $total ? 'healthy' : ($healthy > 0 ? 'degraded' : 'unhealthy'),
            'sources_healthy' => $healthy,
            'sources_total' => $total,
            'sources' => $sources,
            'timestamp' => time(),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result, 60);
        return $result;
    }
    
    /**
     * Flush all cached data
     */
    public function flushCache() {
        $count = 0;
        if (is_dir($this->cacheDir)) {
            $files = glob($this->cacheDir . '*.cache');
            if (is_array($files)) {
                foreach ($files as $file) {
                    if (@unlink($file)) {
                        $count++;
                    }
                }
            }
        }
        return array('ok' => true, 'flushed' => $count);
    }
    
    // ═══════════════════════════════════════════════════════════════════════════
    // Private Helper Methods
    // ═══════════════════════════════════════════════════════════════════════════
    
    /**
     * Fetch data from all sources
     */
    private function fetchAllSources($symbol) {
        $sources = array();
        
        foreach ($this->sourceConfig as $source => $config) {
            $sources[$source] = $this->fetchSourceData($source, $symbol);
        }
        
        return $sources;
    }
    
    /**
     * Fetch data from a single source
     */
    private function fetchSourceData($source, $symbol) {
        $config = isset($this->sourceConfig[$source]) ? $this->sourceConfig[$source] : null;
        if ($config === null) {
            return $this->createErrorSource($source, 'Source not configured');
        }
        
        $endpoint = $this->apiBaseUrl . '/' . $config['endpoint'];
        $url = $endpoint . '?action=sentiment&symbol=' . urlencode($symbol);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $error = curl_error($ch);
        curl_close($ch);
        
        if ($httpCode !== 200 || empty($response)) {
            return $this->createErrorSource($source, 'HTTP ' . $httpCode . ': ' . $error);
        }
        
        $data = json_decode($response, true);
        if (!is_array($data) || !isset($data['ok'])) {
            return $this->createErrorSource($source, 'Invalid response');
        }
        
        if (!$data['ok']) {
            return $this->createErrorSource($source, isset($data['error']) ? $data['error'] : 'Unknown error');
        }
        
        // Normalize the score to -1 to +1 range
        $score = $this->normalizeScore($source, $data);
        
        return array(
            'source' => $source,
            'ok' => true,
            'score' => $score,
            'raw_data' => $data,
            'last_updated' => isset($data['timestamp']) ? $data['timestamp'] : time(),
            'status' => 'ok'
        );
    }
    
    /**
     * Normalize score from different sources to -1 to +1 range
     */
    private function normalizeScore($source, $data) {
        switch ($source) {
            case 'reddit':
                return isset($data['sentiment_score']) ? floatval($data['sentiment_score']) : 0;
                
            case 'trends':
                // Convert velocity to sentiment (-1 to +1)
                $velocity = isset($data['interest_velocity']) ? floatval($data['interest_velocity']) : 1.0;
                // Normalize: 0.5 to 2.0 velocity maps to -1 to +1
                return max(-1, min(1, ($velocity - 1) * 2));
                
            case 'fourchan':
                return isset($data['sentiment_score']) ? floatval($data['sentiment_score']) : 0;
                
            case 'nitter':
                return isset($data['sentiment_score']) ? floatval($data['sentiment_score']) : 0;
                
            default:
                return 0;
        }
    }
    
    /**
     * Calculate consensus score across sources
     */
    private function calculateConsensus($sources) {
        $validSources = array_filter($sources, array($this, 'isSourceValid'));
        
        if (empty($validSources)) {
            return array(
                'score' => 0,
                'label' => 'neutral',
                'confidence' => 0,
                'sources_agree' => 0
            );
        }
        
        $weightedSum = 0;
        $weightSum = 0;
        $bullishCount = 0;
        $bearishCount = 0;
        $neutralCount = 0;
        
        foreach ($validSources as $source => $data) {
            $config = $this->sourceConfig[$source];
            $score = $data['score'];
            $weight = $config['weight'];
            $confidence = $config['confidence'];
            
            // Apply recency adjustment (sources with newer data get slight boost)
            $age = time() - $data['last_updated'];
            $recencyFactor = max(0.5, 1 - ($age / 3600)); // Decay over 1 hour
            
            $effectiveWeight = $weight * $confidence * $recencyFactor;
            $weightedSum += $score * $effectiveWeight;
            $weightSum += $effectiveWeight;
            
            // Count sentiment labels
            if ($score > 0.3) {
                $bullishCount++;
            } elseif ($score < -0.3) {
                $bearishCount++;
            } else {
                $neutralCount++;
            }
        }
        
        // Calculate weighted average
        $consensusScore = $weightSum > 0 ? $weightedSum / $weightSum : 0;
        $consensusScore = max(-1, min(1, $consensusScore));
        
        // Determine label
        if ($consensusScore > 0.3) {
            $label = 'bullish';
        } elseif ($consensusScore < -0.3) {
            $label = 'bearish';
        } else {
            $label = 'neutral';
        }
        
        // Calculate confidence based on agreement
        $totalSources = count($validSources);
        $agreement = max($bullishCount, $bearishCount, $neutralCount) / $totalSources;
        $confidence = $agreement * (0.5 + 0.5 * min(1, $totalSources / 4)); // More sources = higher confidence
        
        return array(
            'score' => round($consensusScore, 2),
            'label' => $label,
            'confidence' => round($confidence, 2),
            'sources_agree' => ($label === 'bullish') ? $bullishCount : (($label === 'bearish') ? $bearishCount : $neutralCount),
            'total_sources' => $totalSources,
            'breakdown' => array(
                'bullish' => $bullishCount,
                'bearish' => $bearishCount,
                'neutral' => $neutralCount
            )
        );
    }
    
    /**
     * Calculate advanced metrics
     */
    private function calculateAdvancedMetrics($sources, $consensus) {
        $validSources = array_filter($sources, array($this, 'isSourceValid'));
        
        // Calculate volatility (standard deviation of scores)
        $scores = array();
        foreach ($validSources as $data) {
            $scores[] = $data['score'];
        }
        $volatility = $this->calculateStdDev($scores);
        
        // Calculate velocity and acceleration from historical data if available
        $velocity = $this->calculateVelocity($consensus);
        $acceleration = $this->calculateAcceleration($consensus);
        
        // Social heatmap based on activity levels
        $activityLevel = $this->calculateActivityLevel($validSources);
        
        // Early detection signal
        $earlyDetection = $this->detectEarlyPhase($validSources, $consensus);
        
        // Viral probability
        $viralProbability = $this->calculateViralProbability($validSources, $consensus);
        
        // Price-sentiment divergence detection
        $divergence = $this->detectDivergence($consensus);
        
        return array(
            'velocity' => round($velocity, 3),
            'acceleration' => round($acceleration, 3),
            'volatility' => round($volatility, 2),
            'divergence' => $divergence,
            'social_heatmap' => $activityLevel,
            'early_detection' => $earlyDetection,
            'viral_probability' => round($viralProbability, 2)
        );
    }
    
    /**
     * Generate alerts based on sentiment analysis
     */
    private function generateAlerts($sources, $consensus, $advancedMetrics) {
        $alerts = array();
        
        // Sentiment surge alert
        if ($advancedMetrics['velocity'] > 0.3) {
            $alerts[] = 'Sentiment surging: +' . round($advancedMetrics['velocity'] * 100) . '% velocity';
        } elseif ($advancedMetrics['velocity'] < -0.3) {
            $alerts[] = 'Sentiment declining: ' . round($advancedMetrics['velocity'] * 100) . '% velocity';
        }
        
        // Source alignment alert
        $validSources = array_filter($sources, array($this, 'isSourceValid'));
        $bullishSources = 0;
        $bearishSources = 0;
        
        foreach ($validSources as $data) {
            if ($data['score'] > 0.3) $bullishSources++;
            elseif ($data['score'] < -0.3) $bearishSources++;
        }
        
        if ($bullishSources >= 3) {
            $alerts[] = 'Multiple sources aligned bullish (' . $bullishSources . '/' . count($validSources) . ')';
        } elseif ($bearishSources >= 3) {
            $alerts[] = 'Multiple sources aligned bearish (' . $bearishSources . '/' . count($validSources) . ')';
        }
        
        // High confidence alert
        if ($consensus['confidence'] > 0.8) {
            $alerts[] = 'High confidence consensus: ' . ucfirst($consensus['label']);
        }
        
        // Early detection alert
        if ($advancedMetrics['early_detection'] && $consensus['score'] > 0.3) {
            $alerts[] = 'Early bullish signal detected - possible breakout candidate';
        }
        
        // Viral probability alert
        if ($advancedMetrics['viral_probability'] > 0.7) {
            $alerts[] = 'High viral probability - social momentum building';
        }
        
        // Volatility alert
        if ($advancedMetrics['volatility'] > 0.5) {
            $alerts[] = 'High disagreement between sources - exercise caution';
        }
        
        return $alerts;
    }
    
    /**
     * Format sources for detailed output
     */
    private function formatSourcesForOutput($sources) {
        $formatted = array();
        
        foreach ($sources as $source => $data) {
            $formatted[$source] = array(
                'score' => isset($data['score']) ? round($data['score'], 2) : 0,
                'raw_data' => isset($data['raw_data']) ? $data['raw_data'] : array(),
                'last_updated' => isset($data['last_updated']) ? $data['last_updated'] : 0,
                'status' => isset($data['status']) ? $data['status'] : 'error'
            );
        }
        
        return $formatted;
    }
    
    /**
     * Fetch trending from a specific source
     */
    private function fetchSourceTrending($source, $limit) {
        $config = isset($this->sourceConfig[$source]) ? $this->sourceConfig[$source] : null;
        if ($config === null) return null;
        
        $endpoint = $this->apiBaseUrl . '/' . $config['endpoint'];
        $url = $endpoint . '?action=trending&limit=' . intval($limit);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        
        $response = curl_exec($ch);
        curl_close($ch);
        
        if (empty($response)) return null;
        
        $data = json_decode($response, true);
        if (!is_array($data) || !$data['ok']) return null;
        
        return isset($data['trending_coins']) ? $data['trending_coins'] : null;
    }
    
    /**
     * Check health of a specific source
     */
    private function checkSourceHealth($source) {
        $config = isset($this->sourceConfig[$source]) ? $this->sourceConfig[$source] : null;
        if ($config === null) {
            return array('ok' => false, 'error' => 'Not configured');
        }
        
        $endpoint = $this->apiBaseUrl . '/' . $config['endpoint'];
        $url = $endpoint . '?action=health';
        
        $start = microtime(true);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        $latency = round((microtime(true) - $start) * 1000, 2);
        
        if ($httpCode !== 200 || empty($response)) {
            return array(
                'ok' => false,
                'status' => 'unhealthy',
                'latency_ms' => $latency,
                'error' => 'HTTP ' . $httpCode
            );
        }
        
        $data = json_decode($response, true);
        if (!is_array($data) || !isset($data['ok'])) {
            return array(
                'ok' => false,
                'status' => 'unhealthy',
                'latency_ms' => $latency,
                'error' => 'Invalid response'
            );
        }
        
        return array(
            'ok' => $data['ok'],
            'status' => isset($data['status']) ? $data['status'] : ($data['ok'] ? 'healthy' : 'unhealthy'),
            'latency_ms' => $latency,
            'details' => $data
        );
    }
    
    /**
     * Create error source structure
     */
    private function createErrorSource($source, $error) {
        return array(
            'source' => $source,
            'ok' => false,
            'score' => 0,
            'raw_data' => array(),
            'last_updated' => 0,
            'status' => 'error: ' . $error
        );
    }
    
    /**
     * Check if source data is valid
     */
    private function isSourceValid($data) {
        return is_array($data) && isset($data['ok']) && $data['ok'] === true;
    }
    
    /**
     * Calculate standard deviation
     */
    private function calculateStdDev($values) {
        if (empty($values) || count($values) < 2) return 0;
        
        $mean = array_sum($values) / count($values);
        $variance = 0;
        
        foreach ($values as $val) {
            $variance += pow($val - $mean, 2);
        }
        
        return sqrt($variance / count($values));
    }
    
    /**
     * Calculate velocity (placeholder - would use historical data)
     */
    private function calculateVelocity($consensus) {
        // In a full implementation, this would compare with historical consensus
        // For now, use a simulated value based on current score
        return $consensus['score'] * 0.2; // Simulated
    }
    
    /**
     * Calculate acceleration (placeholder - would use historical data)
     */
    private function calculateAcceleration($consensus) {
        // In a full implementation, this would compare velocity over time
        return 0; // Simulated
    }
    
    /**
     * Calculate activity level
     */
    private function calculateActivityLevel($sources) {
        $totalMentions = 0;
        
        foreach ($sources as $source => $data) {
            if (isset($data['raw_data']['mentions_24h'])) {
                $totalMentions += intval($data['raw_data']['mentions_24h']);
            }
        }
        
        if ($totalMentions > 1000) return 'extreme';
        if ($totalMentions > 500) return 'very_high';
        if ($totalMentions > 200) return 'high';
        if ($totalMentions > 50) return 'moderate';
        if ($totalMentions > 10) return 'low';
        return 'minimal';
    }
    
    /**
     * Detect early phase signal
     */
    private function detectEarlyPhase($sources, $consensus) {
        // Early phase: moderate activity, positive sentiment, not extreme yet
        $activity = $this->calculateActivityLevel($sources);
        $score = $consensus['score'];
        
        return ($activity === 'moderate' || $activity === 'low') && 
               $score > 0.3 && 
               $consensus['confidence'] > 0.5;
    }
    
    /**
     * Calculate viral probability
     */
    private function calculateViralProbability($sources, $consensus) {
        $activity = $this->calculateActivityLevel($sources);
        $score = abs($consensus['score']);
        $confidence = $consensus['confidence'];
        
        // Higher probability with increasing activity and strong sentiment
        $baseProb = 0;
        
        switch ($activity) {
            case 'extreme': $baseProb = 0.9; break;
            case 'very_high': $baseProb = 0.75; break;
            case 'high': $baseProb = 0.6; break;
            case 'moderate': $baseProb = 0.4; break;
            default: $baseProb = 0.1;
        }
        
        // Adjust by sentiment strength and confidence
        return min(1, $baseProb * (0.5 + 0.5 * $score) * (0.5 + 0.5 * $confidence));
    }
    
    /**
     * Detect price-sentiment divergence (placeholder)
     */
    private function detectDivergence($consensus) {
        // Would require price data to implement fully
        return false;
    }
    
    /**
     * Sort by weighted score
     */
    private function sortByWeightedScore($a, $b) {
        $scoreA = isset($a['weighted_score']) ? $a['weighted_score'] : 0;
        $scoreB = isset($b['weighted_score']) ? $b['weighted_score'] : 0;
        
        if ($scoreA == $scoreB) return 0;
        return ($scoreA > $scoreB) ? -1 : 1;
    }
    
    /**
     * Get data from cache
     */
    private function getCache($key, $ttl = null) {
        $file = $this->cacheDir . $key . '.cache';
        
        if (!file_exists($file)) {
            return null;
        }
        
        $data = @unserialize(@file_get_contents($file));
        if (!is_array($data) || !isset($data['expires']) || !isset($data['value'])) {
            return null;
        }
        
        if (time() > $data['expires']) {
            @unlink($file);
            return null;
        }
        
        return $data['value'];
    }
    
    /**
     * Save data to cache
     */
    private function setCache($key, $value, $ttl = null) {
        $file = $this->cacheDir . $key . '.cache';
        $data = array(
            'expires' => time() + ($ttl !== null ? $ttl : $this->cacheTtl),
            'value' => $value
        );
        
        return @file_put_contents($file, serialize($data)) !== false;
    }
}
?>
