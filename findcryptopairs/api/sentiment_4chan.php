<?php
/**
 * 4chan /biz/ Sentiment Scraper for Cryptocurrency Analysis
 * Scrapes 4chan's Business & Finance board for crypto sentiment
 * 
 * API Endpoints:
 *   ?action=sentiment&symbol=DOGE       - Get sentiment for specific symbol
 *   ?action=mentions&symbol=DOGE        - Get mention stats
 *   ?action=threads&limit=50            - Get active threads
 *   ?action=trending&limit=20           - Get trending coins
 *   ?action=health                      - Health check
 *
 * PHP 5.2 compatible
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

// Configuration
$CACHE_DIR = dirname(__FILE__) . '/../../cache/4chan_sentiment/';
$CACHE_TTL = 300; // 5 minutes
$ADMIN_KEY = '4chan2026';

// 4chan API endpoints
$API_CATALOG = 'https://a.4cdn.org/biz/catalog.json';
$API_THREAD = 'https://a.4cdn.org/biz/thread/';

// Bullish keywords with weights
$BULLISH_KEYWORDS = array(
    'moon' => 2,
    'pump' => 2,
    'bullish' => 2,
    'buy' => 1,
    'gem' => 2,
    '100x' => 3,
    '1000x' => 3,
    'make it' => 2,
    'wagmi' => 2,
    'early' => 1,
    'accumulate' => 1,
    'hodl' => 1,
    'diamond hands' => 2,
    'rocket' => 2,
    'explode' => 2,
    ' ATH' => 2,
    'breakout' => 2,
    'gains' => 1,
    'profit' => 1,
    'rich' => 1,
    'wealth' => 1
);

// Bearish keywords with weights
$BEARISH_KEYWORDS = array(
    'rug' => 3,
    'scam' => 3,
    'dump' => 2,
    'bearish' => 2,
    'sell' => 1,
    'crash' => 2,
    'ponzi' => 3,
    'avoid' => 2,
    'jeet' => 2,
    'pajeet' => 2,
    'shitcoin' => 2,
    'dead' => 2,
    'exit' => 1,
    'bagholder' => 2,
    'rekt' => 2,
    'ngmi' => 2,
    'dumping' => 2,
    'correction' => 1,
    'bear' => 1,
    'short' => 1
);

// Ensure cache directory exists
if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

$action = isset($_GET['action']) ? $_GET['action'] : 'sentiment';
$key = isset($_GET['key']) ? $_GET['key'] : '';

$scraper = new FourChanSentimentScraper($CACHE_DIR, $CACHE_TTL);

switch ($action) {
    case 'sentiment':
        $symbol = isset($_GET['symbol']) ? strtoupper(trim($_GET['symbol'])) : '';
        if (empty($symbol)) {
            echo json_encode(array('ok' => false, 'error' => 'Symbol parameter required'));
            exit;
        }
        $result = $scraper->getSentiment($symbol);
        echo json_encode($result);
        break;
        
    case 'mentions':
        $symbol = isset($_GET['symbol']) ? strtoupper(trim($_GET['symbol'])) : '';
        if (empty($symbol)) {
            echo json_encode(array('ok' => false, 'error' => 'Symbol parameter required'));
            exit;
        }
        $hours = isset($_GET['hours']) ? intval($_GET['hours']) : 24;
        $result = $scraper->getMentions($symbol, $hours);
        echo json_encode($result);
        break;
        
    case 'threads':
        $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 50;
        if ($limit > 100) $limit = 100;
        $result = $scraper->getActiveThreads($limit);
        echo json_encode($result);
        break;
        
    case 'trending':
        $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 20;
        if ($limit > 100) $limit = 100;
        $result = $scraper->getTrendingCoins($limit);
        echo json_encode($result);
        break;
        
    case 'health':
        $result = $scraper->healthCheck();
        echo json_encode($result);
        break;
        
    case 'flush':
        if ($key !== $ADMIN_KEY) {
            echo json_encode(array('ok' => false, 'error' => 'Unauthorized'));
            exit;
        }
        $result = $scraper->flushCache();
        echo json_encode($result);
        break;
        
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

/**
 * 4chan /biz/ Sentiment Scraper Class
 */
class FourChanSentimentScraper {
    private $cacheDir;
    private $cacheTtl;
    private $userAgent;
    private $bullishKeywords;
    private $bearishKeywords;
    
    // Meme coins to track for trending
    private $trackedSymbols = array(
        'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'TURBO', 'NEIRO',
        'BRETT', 'MOG', 'POPCAT', 'MYRO', 'SLERF', 'BOME', 'WOJAK',
        'PNUT', 'GOAT', 'ACT', 'CHILLGUY', 'SPX', 'GIGA', 'PONKE',
        'TRUMP', 'FWOG', 'MICHI', 'DEGEN', 'CHAD', 'COQ', 'TOSHI',
        'SATS', 'ORDI', 'CATE', 'NEKO', 'HAMSTER', 'BABYDOGE',
        'VIRTUAL', 'AI16Z', 'FARTCOIN', 'PENGU', 'MOODENG',
        'BTC', 'ETH', 'SOL', 'XRP', 'ADA', 'LINK', 'AVAX', 'MATIC'
    );
    
    public function __construct($cacheDir = './cache/', $cacheTtl = 300) {
        $this->cacheDir = $cacheDir;
        $this->cacheTtl = $cacheTtl;
        $this->userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0';
        
        global $BULLISH_KEYWORDS, $BEARISH_KEYWORDS;
        $this->bullishKeywords = $BULLISH_KEYWORDS;
        $this->bearishKeywords = $BEARISH_KEYWORDS;
    }
    
    /**
     * Get comprehensive sentiment analysis for a symbol
     */
    public function getSentiment($symbol) {
        $cacheKey = 'sentiment_' . strtolower($symbol);
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        // Fetch catalog and active threads
        $catalog = $this->fetchCatalog();
        if ($catalog === null) {
            return $this->getFallbackSentiment($symbol);
        }
        
        // Analyze threads for symbol mentions
        $mentions = $this->analyzeCatalogForSymbol($catalog, $symbol);
        
        // Calculate sentiment
        $sentimentData = $this->calculateSentiment($mentions['posts']);
        
        // Calculate metrics
        $replyVelocity = $this->calculateReplyVelocity($mentions['threads']);
        $uniquePosters = $this->countUniquePosters($mentions['posts']);
        
        // Build result
        $result = array(
            'ok' => true,
            'symbol' => strtoupper($symbol),
            'source' => '4chan',
            'board' => '/biz/',
            'mentions_24h' => $mentions['count'],
            'active_threads' => count($mentions['threads']),
            'unique_posters' => $uniquePosters,
            'sentiment_score' => round($sentimentData['score'], 2),
            'sentiment_label' => $sentimentData['label'],
            'reply_velocity' => round($replyVelocity, 1),
            'bullish_keywords' => $sentimentData['bullish_counts'],
            'bearish_keywords' => $sentimentData['bearish_counts'],
            'total_bullish_score' => $sentimentData['bullish_score'],
            'total_bearish_score' => $sentimentData['bearish_score'],
            'top_posts' => $this->extractTopPosts($mentions['posts'], 5),
            'timestamp' => time(),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Get mention statistics for a symbol
     */
    public function getMentions($symbol, $hours = 24) {
        $cacheKey = 'mentions_' . strtolower($symbol) . '_' . $hours;
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        $catalog = $this->fetchCatalog();
        if ($catalog === null) {
            return array(
                'ok' => false,
                'error' => 'Failed to fetch catalog',
                'symbol' => strtoupper($symbol)
            );
        }
        
        $mentions = $this->analyzeCatalogForSymbol($catalog, $symbol);
        $cutoffTime = time() - ($hours * 3600);
        
        // Filter posts by time
        $recentPosts = array();
        foreach ($mentions['posts'] as $post) {
            $postTime = isset($post['time']) ? intval($post['time']) : 0;
            if ($postTime >= $cutoffTime) {
                $recentPosts[] = $post;
            }
        }
        
        // Hourly breakdown
        $hourlyBreakdown = array();
        for ($i = 0; $i < $hours; $i++) {
            $hourStart = time() - (($i + 1) * 3600);
            $hourEnd = time() - ($i * 3600);
            $hourCount = 0;
            foreach ($recentPosts as $post) {
                $postTime = isset($post['time']) ? intval($post['time']) : 0;
                if ($postTime >= $hourStart && $postTime < $hourEnd) {
                    $hourCount++;
                }
            }
            $hourlyBreakdown[] = array(
                'hour' => $i,
                'mentions' => $hourCount,
                'timestamp' => $hourStart
            );
        }
        
        $result = array(
            'ok' => true,
            'symbol' => strtoupper($symbol),
            'hours' => $hours,
            'total_mentions' => count($recentPosts),
            'active_threads' => count($mentions['threads']),
            'hourly_breakdown' => $hourlyBreakdown,
            'timestamp' => time(),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Get active threads from /biz/
     */
    public function getActiveThreads($limit = 50) {
        $cacheKey = 'threads_' . $limit;
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        $catalog = $this->fetchCatalog();
        if ($catalog === null) {
            return array(
                'ok' => false,
                'error' => 'Failed to fetch catalog'
            );
        }
        
        $threads = array();
        $count = 0;
        
        foreach ($catalog as $page) {
            if (!isset($page['threads'])) continue;
            
            foreach ($page['threads'] as $thread) {
                if ($count >= $limit) break 2;
                
                $threads[] = array(
                    'no' => isset($thread['no']) ? $thread['no'] : 0,
                    'sub' => isset($thread['sub']) ? substr($thread['sub'], 0, 150) : '',
                    'com' => isset($thread['com']) ? substr(strip_tags($thread['com']), 0, 300) : '',
                    'replies' => isset($thread['replies']) ? $thread['replies'] : 0,
                    'images' => isset($thread['images']) ? $thread['images'] : 0,
                    'time' => isset($thread['time']) ? $thread['time'] : 0,
                    'last_modified' => isset($thread['last_modified']) ? $thread['last_modified'] : 0
                );
                $count++;
            }
        }
        
        $result = array(
            'ok' => true,
            'threads' => $threads,
            'total' => $count,
            'timestamp' => time(),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Get trending coins based on mentions
     */
    public function getTrendingCoins($limit = 20) {
        $cacheKey = 'trending_' . $limit;
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        $catalog = $this->fetchCatalog();
        if ($catalog === null) {
            return array(
                'ok' => false,
                'error' => 'Failed to fetch catalog'
            );
        }
        
        // Analyze each tracked symbol
        $symbolData = array();
        foreach ($this->trackedSymbols as $symbol) {
            $mentions = $this->analyzeCatalogForSymbol($catalog, $symbol);
            if ($mentions['count'] > 0) {
                $sentiment = $this->calculateSentiment($mentions['posts']);
                $symbolData[$symbol] = array(
                    'symbol' => $symbol,
                    'mentions' => $mentions['count'],
                    'active_threads' => count($mentions['threads']),
                    'sentiment_score' => $sentiment['score'],
                    'sentiment_label' => $sentiment['label'],
                    'trending_score' => $mentions['count'] * max(0, $sentiment['score'] + 1)
                );
            }
        }
        
        // Sort by trending score
        uasort($symbolData, array($this, 'sortByTrendingScore'));
        
        $trending = array_slice($symbolData, 0, $limit, true);
        
        $result = array(
            'ok' => true,
            'trending_coins' => array_values($trending),
            'total_scanned' => count($symbolData),
            'timestamp' => time(),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Health check endpoint
     */
    public function healthCheck() {
        $start = microtime(true);
        $catalog = $this->fetchCatalog();
        $latency = round((microtime(true) - $start) * 1000, 2);
        
        if ($catalog === null) {
            return array(
                'ok' => false,
                'status' => 'unhealthy',
                'error' => 'Cannot reach 4chan API',
                'latency_ms' => $latency
            );
        }
        
        // Count total threads
        $totalThreads = 0;
        foreach ($catalog as $page) {
            if (isset($page['threads'])) {
                $totalThreads += count($page['threads']);
            }
        }
        
        return array(
            'ok' => true,
            'status' => 'healthy',
            'latency_ms' => $latency,
            'total_threads' => $totalThreads,
            'pages' => count($catalog),
            'timestamp' => time()
        );
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
    
    /**
     * Fetch catalog from 4chan API
     */
    private function fetchCatalog() {
        global $API_CATALOG;
        
        $cacheKey = 'catalog';
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            return $cached;
        }
        
        $ch = curl_init($API_CATALOG);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, $this->userAgent);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'Accept: application/json'
        ));
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($httpCode !== 200 || empty($response)) {
            return null;
        }
        
        $data = json_decode($response, true);
        if (!is_array($data)) {
            return null;
        }
        
        // Cache for 2 minutes
        $this->setCache($cacheKey, $data, 120);
        return $data;
    }
    
    /**
     * Fetch specific thread data
     */
    private function fetchThread($threadId) {
        global $API_THREAD;
        
        $cacheKey = 'thread_' . $threadId;
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            return $cached;
        }
        
        $url = $API_THREAD . $threadId . '.json';
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, $this->userAgent);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($httpCode !== 200 || empty($response)) {
            return null;
        }
        
        $data = json_decode($response, true);
        if (!is_array($data)) {
            return null;
        }
        
        // Cache for 5 minutes
        $this->setCache($cacheKey, $data, 300);
        return $data;
    }
    
    /**
     * Analyze catalog for symbol mentions
     */
    private function analyzeCatalogForSymbol($catalog, $symbol) {
        $count = 0;
        $matchedThreads = array();
        $allPosts = array();
        
        $symbolLower = strtolower($symbol);
        $symbolUpper = strtoupper($symbol);
        
        // Common variations
        $variations = array(
            $symbolLower,
            $symbolUpper,
            '$' . $symbolUpper,
            '#' . $symbolUpper
        );
        
        foreach ($catalog as $page) {
            if (!isset($page['threads'])) continue;
            
            foreach ($page['threads'] as $thread) {
                $sub = isset($thread['sub']) ? strtolower($thread['sub']) : '';
                $com = isset($thread['com']) ? strtolower(strip_tags($thread['com'])) : '';
                $combined = $sub . ' ' . $com;
                
                $mentioned = false;
                foreach ($variations as $variation) {
                    if (strpos($combined, strtolower($variation)) !== false) {
                        $mentioned = true;
                        break;
                    }
                }
                
                // Check word boundaries
                if (!$mentioned) {
                    if (preg_match('/\b' . preg_quote($symbolLower, '/') . '\b/', $combined)) {
                        $mentioned = true;
                    }
                }
                
                if ($mentioned) {
                    $count++;
                    $threadId = isset($thread['no']) ? $thread['no'] : 0;
                    $matchedThreads[$threadId] = $thread;
                    
                    $allPosts[] = array(
                        'no' => $threadId,
                        'sub' => isset($thread['sub']) ? $thread['sub'] : '',
                        'com' => isset($thread['com']) ? strip_tags($thread['com']) : '',
                        'time' => isset($thread['time']) ? $thread['time'] : 0,
                        'replies' => isset($thread['replies']) ? $thread['replies'] : 0,
                        'name' => isset($thread['name']) ? $thread['name'] : 'Anonymous'
                    );
                    
                    // Fetch thread details for more posts
                    $threadData = $this->fetchThread($threadId);
                    if ($threadData !== null && isset($threadData['posts'])) {
                        foreach ($threadData['posts'] as $post) {
                            $postCom = isset($post['com']) ? strtolower(strip_tags($post['com'])) : '';
                            
                            $postMentioned = false;
                            foreach ($variations as $variation) {
                                if (strpos($postCom, strtolower($variation)) !== false) {
                                    $postMentioned = true;
                                    break;
                                }
                            }
                            
                            if ($postMentioned) {
                                $count++;
                                $allPosts[] = array(
                                    'no' => isset($post['no']) ? $post['no'] : 0,
                                    'com' => isset($post['com']) ? strip_tags($post['com']) : '',
                                    'time' => isset($post['time']) ? $post['time'] : 0,
                                    'name' => isset($post['name']) ? $post['name'] : 'Anonymous'
                                );
                            }
                        }
                    }
                }
            }
        }
        
        return array(
            'count' => $count,
            'threads' => $matchedThreads,
            'posts' => $allPosts
        );
    }
    
    /**
     * Calculate sentiment from posts
     */
    private function calculateSentiment($posts) {
        $bullishScore = 0;
        $bearishScore = 0;
        $bullishCounts = array();
        $bearishCounts = array();
        
        foreach ($posts as $post) {
            $text = '';
            if (isset($post['sub'])) $text .= ' ' . strtolower($post['sub']);
            if (isset($post['com'])) $text .= ' ' . strtolower(strip_tags($post['com']));
            
            // Check bullish keywords
            foreach ($this->bullishKeywords as $keyword => $weight) {
                $count = substr_count($text, strtolower($keyword));
                if ($count > 0) {
                    $bullishScore += $count * $weight;
                    if (!isset($bullishCounts[$keyword])) {
                        $bullishCounts[$keyword] = 0;
                    }
                    $bullishCounts[$keyword] += $count;
                }
            }
            
            // Check bearish keywords
            foreach ($this->bearishKeywords as $keyword => $weight) {
                $count = substr_count($text, strtolower($keyword));
                if ($count > 0) {
                    $bearishScore += $count * $weight;
                    if (!isset($bearishCounts[$keyword])) {
                        $bearishCounts[$keyword] = 0;
                    }
                    $bearishCounts[$keyword] += $count;
                }
            }
        }
        
        // Calculate normalized sentiment score (-1 to +1)
        $totalScore = $bullishScore + $bearishScore;
        if ($totalScore == 0) {
            $sentimentScore = 0;
            $label = 'neutral';
        } else {
            $sentimentScore = ($bullishScore - $bearishScore) / $totalScore;
            if ($sentimentScore > 0.3) {
                $label = 'bullish';
            } elseif ($sentimentScore < -0.3) {
                $label = 'bearish';
            } else {
                $label = 'neutral';
            }
        }
        
        $sentimentScore = max(-1, min(1, $sentimentScore));
        
        return array(
            'score' => $sentimentScore,
            'label' => $label,
            'bullish_score' => $bullishScore,
            'bearish_score' => $bearishScore,
            'bullish_counts' => $bullishCounts,
            'bearish_counts' => $bearishCounts
        );
    }
    
    /**
     * Calculate reply velocity
     */
    private function calculateReplyVelocity($threads) {
        $totalReplies = 0;
        $oldestTime = time();
        $newestTime = 0;
        
        foreach ($threads as $thread) {
            $replies = isset($thread['replies']) ? intval($thread['replies']) : 0;
            $time = isset($thread['time']) ? intval($thread['time']) : 0;
            
            $totalReplies += $replies;
            
            if ($time > 0) {
                if ($time < $oldestTime) $oldestTime = $time;
                if ($time > $newestTime) $newestTime = $time;
            }
        }
        
        $timeSpan = $newestTime - $oldestTime;
        if ($timeSpan <= 0) return 0;
        
        $hours = $timeSpan / 3600;
        if ($hours <= 0) return 0;
        
        return $totalReplies / $hours;
    }
    
    /**
     * Count unique posters
     */
    private function countUniquePosters($posts) {
        $names = array();
        foreach ($posts as $post) {
            $name = isset($post['name']) ? $post['name'] : 'Anonymous';
            $names[$name] = true;
        }
        return count($names);
    }
    
    /**
     * Extract top posts
     */
    private function extractTopPosts($posts, $limit = 5) {
        // Sort by time (most recent first)
        usort($posts, array($this, 'sortByTime'));
        
        $topPosts = array();
        $count = 0;
        
        foreach ($posts as $post) {
            if ($count >= $limit) break;
            
            $topPosts[] = array(
                'no' => isset($post['no']) ? $post['no'] : 0,
                'sub' => isset($post['sub']) ? substr($post['sub'], 0, 150) : '',
                'com' => isset($post['com']) ? substr(strip_tags($post['com']), 0, 300) : '',
                'time' => isset($post['time']) ? intval($post['time']) : 0,
                'name' => isset($post['name']) ? $post['name'] : 'Anonymous'
            );
            $count++;
        }
        
        return $topPosts;
    }
    
    /**
     * Get fallback sentiment when API fails
     */
    private function getFallbackSentiment($symbol) {
        return array(
            'ok' => true,
            'symbol' => strtoupper($symbol),
            'source' => '4chan',
            'board' => '/biz/',
            'mentions_24h' => 0,
            'active_threads' => 0,
            'unique_posters' => 0,
            'sentiment_score' => 0,
            'sentiment_label' => 'neutral',
            'reply_velocity' => 0,
            'bullish_keywords' => array(),
            'bearish_keywords' => array(),
            'total_bullish_score' => 0,
            'total_bearish_score' => 0,
            'top_posts' => array(),
            'timestamp' => time(),
            'cached' => false,
            'fallback' => true,
            'error' => 'API unavailable - using fallback'
        );
    }
    
    /**
     * Get data from cache
     */
    private function getCache($key) {
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
    
    /**
     * Sort posts by time (descending)
     */
    private function sortByTime($a, $b) {
        $timeA = isset($a['time']) ? intval($a['time']) : 0;
        $timeB = isset($b['time']) ? intval($b['time']) : 0;
        
        if ($timeA == $timeB) return 0;
        return ($timeA > $timeB) ? -1 : 1;
    }
    
    /**
     * Sort coins by trending score (descending)
     */
    private function sortByTrendingScore($a, $b) {
        if ($a['trending_score'] == $b['trending_score']) return 0;
        return ($a['trending_score'] > $b['trending_score']) ? -1 : 1;
    }
}
?>
