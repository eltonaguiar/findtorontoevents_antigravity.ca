<?php
/**
 * Nitter (Twitter/X) Sentiment Scraper for Cryptocurrency Analysis
 * Uses Nitter instances to scrape Twitter for crypto sentiment
 * 
 * API Endpoints:
 *   ?action=sentiment&symbol=DOGE       - Get sentiment for specific symbol
 *   ?action=mentions&symbol=DOGE        - Get mention stats
 *   ?action=search&q=bitcoin            - Search tweets
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
$CACHE_DIR = dirname(__FILE__) . '/../../cache/nitter_sentiment/';
$CACHE_TTL = 300; // 5 minutes
$ADMIN_KEY = 'nitter2026';

// Nitter instances to try (in order of preference)
$NITTER_INSTANCES = array(
    'https://nitter.net',
    'https://nitter.privacydev.net',
    'https://nitter.cz',
    'https://nitter.it',
    'https://nitter.poast.org',
    'https://nitter.datura.network',
    'https://nitter.projectsegfault.com'
);

// Bullish keywords with weights
$BULLISH_KEYWORDS = array(
    'moon' => 2,
    'pump' => 2,
    'bullish' => 2,
    'buy' => 1,
    'gem' => 2,
    '100x' => 3,
    '1000x' => 3,
    'early' => 1,
    'accumulate' => 1,
    'hodl' => 1,
    'diamond hands' => 2,
    'rocket' => 2,
    'explode' => 2,
    'ATH' => 2,
    'breakout' => 2,
    'gains' => 1,
    'profit' => 1,
    'long' => 1,
    'support' => 1,
    'bounce' => 1
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
    'shitcoin' => 2,
    'dead' => 2,
    'exit' => 1,
    'short' => 1,
    'resistance' => 1,
    'dumping' => 2,
    'correction' => 1,
    'bear' => 1,
    'liquidated' => 2,
    'rekt' => 2
);

// Ensure cache directory exists
if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

$action = isset($_GET['action']) ? $_GET['action'] : 'sentiment';
$key = isset($_GET['key']) ? $_GET['key'] : '';

$scraper = new NitterSentimentScraper($CACHE_DIR, $CACHE_TTL);

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
        
    case 'search':
        $query = isset($_GET['q']) ? trim($_GET['q']) : '';
        if (empty($query)) {
            echo json_encode(array('ok' => false, 'error' => 'Query parameter required'));
            exit;
        }
        $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 20;
        $result = $scraper->searchTweets($query, $limit);
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
 * Nitter (Twitter/X) Sentiment Scraper Class
 */
class NitterSentimentScraper {
    private $cacheDir;
    private $cacheTtl;
    private $userAgent;
    private $bullishKeywords;
    private $bearishKeywords;
    private $instances;
    private $workingInstance = null;
    
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
        $this->userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';
        
        global $BULLISH_KEYWORDS, $BEARISH_KEYWORDS, $NITTER_INSTANCES;
        $this->bullishKeywords = $BULLISH_KEYWORDS;
        $this->bearishKeywords = $BEARISH_KEYWORDS;
        $this->instances = $NITTER_INSTANCES;
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
        
        // Search for tweets mentioning the symbol
        $searchQuery = '$' . $symbol;
        $tweets = $this->searchTweetsInternal($searchQuery, 50);
        
        if ($tweets === null) {
            return $this->getFallbackSentiment($symbol);
        }
        
        // Calculate sentiment
        $sentimentData = $this->calculateSentiment($tweets);
        
        // Calculate engagement metrics
        $engagement = $this->calculateEngagement($tweets);
        
        // Calculate tweet velocity (tweets per hour)
        $velocity = $this->calculateTweetVelocity($tweets);
        
        // Build result
        $result = array(
            'ok' => true,
            'symbol' => strtoupper($symbol),
            'source' => 'nitter',
            'platform' => 'Twitter/X',
            'mentions_24h' => count($tweets),
            'sentiment_score' => round($sentimentData['score'], 2),
            'sentiment_label' => $sentimentData['label'],
            'tweet_velocity' => round($velocity, 1),
            'total_likes' => $engagement['likes'],
            'total_retweets' => $engagement['retweets'],
            'total_replies' => $engagement['replies'],
            'avg_engagement' => $engagement['avg_engagement'],
            'bullish_keywords' => $sentimentData['bullish_counts'],
            'bearish_keywords' => $sentimentData['bearish_counts'],
            'total_bullish_score' => $sentimentData['bullish_score'],
            'total_bearish_score' => $sentimentData['bearish_score'],
            'top_tweets' => $this->extractTopTweets($tweets, 5),
            'hashtags' => $this->extractHashtags($tweets),
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
        
        $searchQuery = '$' . $symbol;
        $tweets = $this->searchTweetsInternal($searchQuery, 100);
        
        if ($tweets === null) {
            return array(
                'ok' => false,
                'error' => 'Failed to fetch tweets',
                'symbol' => strtoupper($symbol)
            );
        }
        
        $cutoffTime = time() - ($hours * 3600);
        
        // Filter tweets by time
        $recentTweets = array();
        foreach ($tweets as $tweet) {
            $tweetTime = isset($tweet['timestamp']) ? intval($tweet['timestamp']) : 0;
            if ($tweetTime >= $cutoffTime) {
                $recentTweets[] = $tweet;
            }
        }
        
        // Hourly breakdown
        $hourlyBreakdown = array();
        for ($i = 0; $i < $hours; $i++) {
            $hourStart = time() - (($i + 1) * 3600);
            $hourEnd = time() - ($i * 3600);
            $hourCount = 0;
            foreach ($recentTweets as $tweet) {
                $tweetTime = isset($tweet['timestamp']) ? intval($tweet['timestamp']) : 0;
                if ($tweetTime >= $hourStart && $tweetTime < $hourEnd) {
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
            'total_mentions' => count($recentTweets),
            'hourly_breakdown' => $hourlyBreakdown,
            'timestamp' => time(),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Search tweets (public API)
     */
    public function searchTweets($query, $limit = 20) {
        $tweets = $this->searchTweetsInternal($query, $limit);
        
        if ($tweets === null) {
            return array(
                'ok' => false,
                'error' => 'Failed to search tweets'
            );
        }
        
        return array(
            'ok' => true,
            'query' => $query,
            'tweets' => $tweets,
            'count' => count($tweets),
            'timestamp' => time()
        );
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
        
        // Use crypto-related search to get general sentiment
        $tweets = $this->searchTweetsInternal('crypto OR cryptocurrency', 100);
        
        if ($tweets === null) {
            return array(
                'ok' => false,
                'error' => 'Failed to fetch tweets'
            );
        }
        
        // Analyze each tracked symbol
        $symbolData = array();
        foreach ($this->trackedSymbols as $symbol) {
            $mentions = $this->countSymbolMentions($tweets, $symbol);
            if ($mentions > 0) {
                // Get specific tweets for this symbol
                $symbolTweets = $this->searchTweetsInternal('$' . $symbol, 30);
                $sentiment = array('score' => 0, 'label' => 'neutral');
                
                if ($symbolTweets !== null && count($symbolTweets) > 0) {
                    $sentiment = $this->calculateSentiment($symbolTweets);
                }
                
                $symbolData[$symbol] = array(
                    'symbol' => $symbol,
                    'mentions' => $mentions,
                    'sentiment_score' => $sentiment['score'],
                    'sentiment_label' => $sentiment['label'],
                    'trending_score' => $mentions * max(0.1, $sentiment['score'] + 1)
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
        
        // Try to find a working instance
        $working = $this->findWorkingInstance();
        $latency = round((microtime(true) - $start) * 1000, 2);
        
        if ($working === null) {
            return array(
                'ok' => false,
                'status' => 'unhealthy',
                'error' => 'No working Nitter instance found',
                'latency_ms' => $latency,
                'instances_tried' => count($this->instances)
            );
        }
        
        return array(
            'ok' => true,
            'status' => 'healthy',
            'instance' => $working,
            'latency_ms' => $latency,
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
     * Search tweets using Nitter
     */
    private function searchTweetsInternal($query, $limit = 20) {
        $cacheKey = 'search_' . md5($query . $limit);
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            return $cached;
        }
        
        // Find a working instance
        $instance = $this->findWorkingInstance();
        if ($instance === null) {
            return null;
        }
        
        // Build search URL
        $url = $instance . '/search?f=tweets&q=' . urlencode($query);
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 20);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, $this->userAgent);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'Accept: text/html,application/xhtml+xml',
            'Accept-Language: en-US,en;q=0.9'
        ));
        
        $response = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($httpCode !== 200 || empty($response)) {
            // Mark this instance as potentially broken
            $this->workingInstance = null;
            return null;
        }
        
        // Parse tweets from HTML
        $tweets = $this->parseTweetsFromHtml($response, $limit);
        
        // Cache for 3 minutes
        $this->setCache($cacheKey, $tweets, 180);
        return $tweets;
    }
    
    /**
     * Parse tweets from Nitter HTML
     */
    private function parseTweetsFromHtml($html, $limit) {
        $tweets = array();
        
        // Use regex to extract tweet data
        // Nitter structure: .timeline-item
        preg_match_all('/<div class="timeline-item[^"]*"[^>]*>(.*?)<\/div>\s*<\/div>\s*<\/div>/s', $html, $matches, PREG_SET_ORDER);
        
        $count = 0;
        foreach ($matches as $match) {
            if ($count >= $limit) break;
            
            $item = $match[1];
            
            // Extract tweet data
            $tweet = $this->extractTweetData($item);
            if ($tweet !== null) {
                $tweets[] = $tweet;
                $count++;
            }
        }
        
        // Fallback: try alternative parsing if no tweets found
        if (empty($tweets)) {
            $tweets = $this->parseTweetsAlternative($html, $limit);
        }
        
        return $tweets;
    }
    
    /**
     * Extract tweet data from HTML item
     */
    private function extractTweetData($html) {
        // Extract username
        $username = '';
        if (preg_match('/<a[^>]*href="\/([^"]+)"[^>]*class="username[^"]*"[^>]*>/', $html, $match)) {
            $username = $match[1];
        } elseif (preg_match('/<div[^>]*class="tweet-name[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</s', $html, $match)) {
            $username = trim($match[1]);
        }
        
        // Extract content
        $content = '';
        if (preg_match('/<div[^>]*class="tweet-content[^"]*"[^>]*>(.*?)<\/div>/s', $html, $match)) {
            $content = $this->cleanHtml($match[1]);
        } elseif (preg_match('/<div[^>]*class="content[^"]*"[^>]*>(.*?)<\/div>/s', $html, $match)) {
            $content = $this->cleanHtml($match[1]);
        }
        
        // Extract timestamp
        $timestamp = 0;
        if (preg_match('/datetime="([^"]+)"/', $html, $match)) {
            $timestamp = strtotime($match[1]);
        } elseif (preg_match('/data-time="(\d+)"/', $html, $match)) {
            $timestamp = intval($match[1]);
        }
        
        // Extract engagement stats
        $likes = 0;
        $retweets = 0;
        $replies = 0;
        
        if (preg_match('/(\d+)\s*like/i', $html, $match)) {
            $likes = intval($match[1]);
        }
        if (preg_match('/(\d+)\s*retweet/i', $html, $match)) {
            $retweets = intval($match[1]);
        }
        if (preg_match('/(\d+)\s*repl/i', $html, $match)) {
            $replies = intval($match[1]);
        }
        
        // Extract tweet ID
        $tweetId = '';
        if (preg_match('/status\/(\d+)/', $html, $match)) {
            $tweetId = $match[1];
        }
        
        if (empty($content) || empty($username)) {
            return null;
        }
        
        return array(
            'id' => $tweetId,
            'username' => $username,
            'content' => $content,
            'timestamp' => $timestamp,
            'likes' => $likes,
            'retweets' => $retweets,
            'replies' => $replies,
            'engagement' => $likes + $retweets + $replies
        );
    }
    
    /**
     * Alternative tweet parsing method
     */
    private function parseTweetsAlternative($html, $limit) {
        $tweets = array();
        
        // Try different patterns
        // Pattern: tweet-body or similar classes
        preg_match_all('/<div[^>]*class="[^"]*tweet[^"]*"[^>]*>(.*?)<\/div>\s*<\/div>/s', $html, $matches, PREG_SET_ORDER);
        
        $count = 0;
        foreach ($matches as $match) {
            if ($count >= $limit) break;
            
            $itemHtml = $match[0];
            
            // Try to extract basic info
            $content = '';
            if (preg_match('/<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)<\/div>/s', $itemHtml, $contentMatch)) {
                $content = $this->cleanHtml($contentMatch[1]);
            }
            
            $username = 'unknown';
            if (preg_match('/@([a-zA-Z0-9_]+)/', $itemHtml, $userMatch)) {
                $username = $userMatch[1];
            }
            
            if (!empty($content)) {
                $tweets[] = array(
                    'id' => '',
                    'username' => $username,
                    'content' => $content,
                    'timestamp' => time(),
                    'likes' => 0,
                    'retweets' => 0,
                    'replies' => 0,
                    'engagement' => 0
                );
                $count++;
            }
        }
        
        return $tweets;
    }
    
    /**
     * Clean HTML content
     */
    private function cleanHtml($html) {
        // Remove HTML tags
        $text = strip_tags($html);
        // Decode HTML entities
        $text = html_entity_decode($text, ENT_QUOTES | ENT_HTML5, 'UTF-8');
        // Clean up whitespace
        $text = preg_replace('/\s+/', ' ', $text);
        return trim($text);
    }
    
    /**
     * Find a working Nitter instance
     */
    private function findWorkingInstance() {
        // Return cached working instance
        if ($this->workingInstance !== null) {
            return $this->workingInstance;
        }
        
        // Try each instance
        foreach ($this->instances as $instance) {
            $url = $instance . '/search?f=tweets&q=bitcoin';
            
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 10);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_USERAGENT, $this->userAgent);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_NOBODY, true); // HEAD request
            
            curl_exec($ch);
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            
            if ($httpCode === 200) {
                $this->workingInstance = $instance;
                return $instance;
            }
        }
        
        return null;
    }
    
    /**
     * Calculate sentiment from tweets
     */
    private function calculateSentiment($tweets) {
        $bullishScore = 0;
        $bearishScore = 0;
        $bullishCounts = array();
        $bearishCounts = array();
        
        foreach ($tweets as $tweet) {
            $text = isset($tweet['content']) ? strtolower($tweet['content']) : '';
            
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
     * Calculate engagement metrics
     */
    private function calculateEngagement($tweets) {
        $totalLikes = 0;
        $totalRetweets = 0;
        $totalReplies = 0;
        $totalEngagement = 0;
        
        foreach ($tweets as $tweet) {
            $likes = isset($tweet['likes']) ? intval($tweet['likes']) : 0;
            $retweets = isset($tweet['retweets']) ? intval($tweet['retweets']) : 0;
            $replies = isset($tweet['replies']) ? intval($tweet['replies']) : 0;
            
            $totalLikes += $likes;
            $totalRetweets += $retweets;
            $totalReplies += $replies;
            $totalEngagement += $likes + $retweets + $replies;
        }
        
        $count = count($tweets);
        $avgEngagement = $count > 0 ? round($totalEngagement / $count, 1) : 0;
        
        return array(
            'likes' => $totalLikes,
            'retweets' => $totalRetweets,
            'replies' => $totalReplies,
            'total' => $totalEngagement,
            'avg_engagement' => $avgEngagement
        );
    }
    
    /**
     * Calculate tweet velocity (tweets per hour)
     */
    private function calculateTweetVelocity($tweets) {
        if (empty($tweets)) return 0;
        
        $oldestTime = time();
        $newestTime = 0;
        
        foreach ($tweets as $tweet) {
            $timestamp = isset($tweet['timestamp']) ? intval($tweet['timestamp']) : 0;
            if ($timestamp > 0) {
                if ($timestamp < $oldestTime) $oldestTime = $timestamp;
                if ($timestamp > $newestTime) $newestTime = $timestamp;
            }
        }
        
        $timeSpan = $newestTime - $oldestTime;
        if ($timeSpan <= 0) return count($tweets); // All at once
        
        $hours = $timeSpan / 3600;
        if ($hours <= 0) return 0;
        
        return count($tweets) / $hours;
    }
    
    /**
     * Count symbol mentions in tweets
     */
    private function countSymbolMentions($tweets, $symbol) {
        $count = 0;
        $symbolLower = strtolower($symbol);
        $symbolUpper = strtoupper($symbol);
        
        foreach ($tweets as $tweet) {
            $text = isset($tweet['content']) ? strtolower($tweet['content']) : '';
            
            // Check for symbol variations
            if (strpos($text, $symbolLower) !== false ||
                strpos($text, $symbolUpper) !== false ||
                strpos($text, '$' . $symbolUpper) !== false ||
                strpos($text, '#' . $symbolUpper) !== false) {
                $count++;
            }
        }
        
        return $count;
    }
    
    /**
     * Extract top tweets by engagement
     */
    private function extractTopTweets($tweets, $limit = 5) {
        // Sort by engagement
        usort($tweets, array($this, 'sortByEngagement'));
        
        $topTweets = array();
        $count = 0;
        
        foreach ($tweets as $tweet) {
            if ($count >= $limit) break;
            
            $topTweets[] = array(
                'id' => isset($tweet['id']) ? $tweet['id'] : '',
                'username' => isset($tweet['username']) ? $tweet['username'] : '',
                'content' => isset($tweet['content']) ? substr($tweet['content'], 0, 280) : '',
                'timestamp' => isset($tweet['timestamp']) ? intval($tweet['timestamp']) : 0,
                'likes' => isset($tweet['likes']) ? $tweet['likes'] : 0,
                'retweets' => isset($tweet['retweets']) ? $tweet['retweets'] : 0,
                'replies' => isset($tweet['replies']) ? $tweet['replies'] : 0
            );
            $count++;
        }
        
        return $topTweets;
    }
    
    /**
     * Extract hashtags from tweets
     */
    private function extractHashtags($tweets) {
        $hashtags = array();
        
        foreach ($tweets as $tweet) {
            $text = isset($tweet['content']) ? $tweet['content'] : '';
            preg_match_all('/#(\w+)/', $text, $matches);
            
            foreach ($matches[1] as $tag) {
                $tagLower = strtolower($tag);
                if (!isset($hashtags[$tagLower])) {
                    $hashtags[$tagLower] = 0;
                }
                $hashtags[$tagLower]++;
            }
        }
        
        // Sort by frequency
        arsort($hashtags);
        
        // Return top 10
        return array_slice($hashtags, 0, 10, true);
    }
    
    /**
     * Get fallback sentiment when API fails
     */
    private function getFallbackSentiment($symbol) {
        return array(
            'ok' => true,
            'symbol' => strtoupper($symbol),
            'source' => 'nitter',
            'platform' => 'Twitter/X',
            'mentions_24h' => 0,
            'sentiment_score' => 0,
            'sentiment_label' => 'neutral',
            'tweet_velocity' => 0,
            'total_likes' => 0,
            'total_retweets' => 0,
            'total_replies' => 0,
            'avg_engagement' => 0,
            'bullish_keywords' => array(),
            'bearish_keywords' => array(),
            'total_bullish_score' => 0,
            'total_bearish_score' => 0,
            'top_tweets' => array(),
            'hashtags' => array(),
            'timestamp' => time(),
            'cached' => false,
            'fallback' => true,
            'error' => 'Nitter API unavailable - using fallback'
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
     * Sort tweets by engagement (descending)
     */
    private function sortByEngagement($a, $b) {
        $engagementA = isset($a['engagement']) ? intval($a['engagement']) : 0;
        $engagementB = isset($b['engagement']) ? intval($b['engagement']) : 0;
        
        if ($engagementA == $engagementB) return 0;
        return ($engagementA > $engagementB) ? -1 : 1;
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
