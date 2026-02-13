<?php
/**
 * Reddit Cryptocurrency Sentiment Scraper for Meme Coin Analysis
 * Scrapes Reddit for crypto sentiment data from meme coin focused subreddits
 * 
 * Endpoints:
 *   ?action=sentiment&symbol=DOGE       - Get sentiment for specific symbol
 *   ?action=mentions&symbol=DOGE&hours=24 - Get mention stats
 *   ?action=trending&limit=20           - Get trending coins
 *   ?action=flush                       - Clear cache (admin)
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
$CACHE_DIR = dirname(__FILE__) . '/../../cache/reddit_sentiment/';
$CACHE_TTL = 300; // 5 minutes
$ADMIN_KEY = 'reddit2026';

// Default subreddits to monitor
$DEFAULT_SUBREDDITS = array(
    'CryptoMoonShots',
    'SatoshiStreetBets',
    'CryptoCurrency',
    'memecoins'
);

// Bullish keywords with weights
$BULLISH_KEYWORDS = array(
    'moon' => 1,
    'diamond hands' => 2,
    'hodl' => 1,
    'pump' => 1,
    'bullish' => 2,
    'gain' => 1,
    'buy' => 1,
    'rocket' => 2,
    'gem' => 1,
    'next' => 1,
    'gem' => 2,
    '100x' => 3,
    '1000x' => 3,
    'gem' => 2,
    'early' => 1,
    'potential' => 1
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
    'red flag' => 2,
    'shitcoin' => 2,
    'dead' => 2,
    'exit' => 1
);

// Ensure cache directory exists
if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

$action = isset($_GET['action']) ? $_GET['action'] : 'sentiment';
$key = isset($_GET['key']) ? $_GET['key'] : '';

$scraper = new RedditSentimentScraper($CACHE_DIR, $CACHE_TTL);

switch ($action) {
    case 'sentiment':
        $symbol = isset($_GET['symbol']) ? strtoupper(trim($_GET['symbol'])) : '';
        if (empty($symbol)) {
            echo json_encode(array('ok' => false, 'error' => 'Symbol parameter required'));
            exit;
        }
        $subreddits = isset($_GET['subreddits']) ? explode(',', $_GET['subreddits']) : $DEFAULT_SUBREDDITS;
        $result = $scraper->getSentiment($symbol, $subreddits);
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
        
    case 'trending':
        $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 20;
        if ($limit > 100) $limit = 100;
        $result = $scraper->getTrendingCoins($limit);
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
 * Reddit Sentiment Scraper Class
 */
class RedditSentimentScraper {
    private $cacheDir;
    private $cacheTtl;
    private $userAgent;
    
    // Bullish keywords
    private $bullishKeywords = array(
        'moon' => 1,
        'diamond hands' => 2,
        'hodl' => 1,
        'pump' => 1,
        'bullish' => 2,
        'gain' => 1,
        'buy' => 1,
        'rocket' => 2,
        'gem' => 2,
        'next' => 1,
        '100x' => 3,
        '1000x' => 3,
        'early' => 1,
        'potential' => 1,
        'explode' => 2,
        'soaring' => 2,
        'breaking out' => 2
    );
    
    // Bearish keywords
    private $bearishKeywords = array(
        'rug' => 3,
        'scam' => 3,
        'dump' => 2,
        'bearish' => 2,
        'sell' => 1,
        'crash' => 2,
        'ponzi' => 3,
        'avoid' => 2,
        'red flag' => 2,
        'shitcoin' => 2,
        'dead' => 2,
        'exit' => 1,
        'dumping' => 2,
        'pullback' => 1,
        'correction' => 1
    );
    
    // Default subreddits
    private $defaultSubreddits = array(
        'CryptoMoonShots',
        'SatoshiStreetBets',
        'CryptoCurrency',
        'memecoins'
    );
    
    public function __construct($cacheDir = './cache/', $cacheTtl = 300) {
        $this->cacheDir = $cacheDir;
        $this->cacheTtl = $cacheTtl;
        $this->userAgent = 'CryptoSentimentBot/1.0 (Meme Coin Analysis)';
    }
    
    /**
     * Get comprehensive sentiment analysis for a symbol
     * 
     * @param string $symbol The crypto symbol (e.g., DOGE, SHIB)
     * @param array $subreddits List of subreddits to scan
     * @return array Sentiment analysis result
     */
    public function getSentiment($symbol, $subreddits = array()) {
        if (empty($subreddits)) {
            $subreddits = $this->defaultSubreddits;
        }
        
        $cacheKey = 'sentiment_' . strtolower($symbol) . '_' . md5(implode(',', $subreddits));
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        // Fetch posts from all subreddits
        $allPosts = array();
        foreach ($subreddits as $subreddit) {
            $posts = $this->fetchSubredditPosts($subreddit, 100);
            if (is_array($posts)) {
                $allPosts = array_merge($allPosts, $posts);
            }
        }
        
        // Analyze posts for symbol mentions
        $mentions = $this->analyzeMentions($allPosts, $symbol);
        
        // Calculate sentiment score
        $sentimentData = $this->calculateSentiment($mentions['matched_posts']);
        
        // Calculate comment velocity
        $commentVelocity = $this->calculateCommentVelocity($mentions['matched_posts']);
        
        // Get average upvote ratio
        $avgUpvoteRatio = $this->calculateAvgUpvoteRatio($mentions['matched_posts']);
        
        // Build top posts list
        $topPosts = $this->extractTopPosts($mentions['matched_posts'], 5);
        
        $result = array(
            'ok' => true,
            'symbol' => strtoupper($symbol),
            'mentions_24h' => $mentions['count'],
            'avg_upvote_ratio' => round($avgUpvoteRatio, 2),
            'sentiment_score' => round($sentimentData['score'], 2),
            'sentiment_label' => $sentimentData['label'],
            'comment_velocity' => round($commentVelocity, 1),
            'bullish_keywords' => $sentimentData['bullish_counts'],
            'bearish_keywords' => $sentimentData['bearish_counts'],
            'total_bullish_score' => $sentimentData['bullish_score'],
            'total_bearish_score' => $sentimentData['bearish_score'],
            'top_posts' => $topPosts,
            'subreddits_scanned' => count($subreddits),
            'posts_analyzed' => count($allPosts),
            'timestamp' => time(),
            'source' => 'reddit',
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Get mention statistics for a symbol over specified hours
     * 
     * @param string $symbol The crypto symbol
     * @param int $hours Number of hours to look back
     * @return array Mention statistics
     */
    public function getMentions($symbol, $hours = 24) {
        $cacheKey = 'mentions_' . strtolower($symbol) . '_' . $hours;
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        $allPosts = array();
        foreach ($this->defaultSubreddits as $subreddit) {
            $posts = $this->fetchSubredditPosts($subreddit, 100);
            if (is_array($posts)) {
                $allPosts = array_merge($allPosts, $posts);
            }
        }
        
        $cutoffTime = time() - ($hours * 3600);
        $recentPosts = array();
        foreach ($allPosts as $post) {
            $createdTime = isset($post['created_utc']) ? intval($post['created_utc']) : 0;
            if ($createdTime >= $cutoffTime) {
                $recentPosts[] = $post;
            }
        }
        
        $mentions = $this->analyzeMentions($recentPosts, $symbol);
        
        // Hourly breakdown
        $hourlyBreakdown = array();
        for ($i = 0; $i < $hours; $i++) {
            $hourStart = time() - (($i + 1) * 3600);
            $hourEnd = time() - ($i * 3600);
            $hourCount = 0;
            foreach ($mentions['matched_posts'] as $post) {
                $postTime = isset($post['created_utc']) ? intval($post['created_utc']) : 0;
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
            'total_mentions' => $mentions['count'],
            'posts_analyzed' => count($recentPosts),
            'hourly_breakdown' => $hourlyBreakdown,
            'unique_authors' => count($mentions['unique_authors']),
            'avg_score' => round($mentions['avg_score'], 1),
            'timestamp' => time(),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Get trending coins based on mention frequency and sentiment
     * 
     * @param int $limit Number of trending coins to return
     * @return array Trending coins list
     */
    public function getTrendingCoins($limit = 20) {
        $cacheKey = 'trending_' . $limit;
        $cached = $this->getCache($cacheKey);
        if ($cached !== null) {
            $cached['cached'] = true;
            return $cached;
        }
        
        // Common meme coins to track
        $trackedSymbols = array(
            'DOGE', 'SHIB', 'PEPE', 'FLOKI', 'BONK', 'WIF', 'TURBO', 'NEIRO',
            'BRETT', 'MOG', 'POPCAT', 'MYRO', 'SLERF', 'BOME', 'WOJAK',
            'PNUT', 'GOAT', 'ACT', 'CHILLGUY', 'SPX', 'GIGA', 'PONKE',
            'TRUMP', 'FWOG', 'MICHI', 'DEGEN', 'CHAD', 'COQ', 'TOSHI',
            'SATS', 'ORDI', 'CATE', 'NEKO', 'HAMSTER', 'BABYDOGE',
            'VIRTUAL', 'AI16Z', 'FARTCOIN', 'PENGU', 'MOODENG'
        );
        
        // Fetch all posts
        $allPosts = array();
        foreach ($this->defaultSubreddits as $subreddit) {
            $posts = $this->fetchSubredditPosts($subreddit, 100);
            if (is_array($posts)) {
                $allPosts = array_merge($allPosts, $posts);
            }
        }
        
        // Analyze each symbol
        $symbolData = array();
        foreach ($trackedSymbols as $symbol) {
            $mentions = $this->analyzeMentions($allPosts, $symbol);
            if ($mentions['count'] > 0) {
                $sentiment = $this->calculateSentiment($mentions['matched_posts']);
                $symbolData[$symbol] = array(
                    'symbol' => $symbol,
                    'mentions' => $mentions['count'],
                    'sentiment_score' => $sentiment['score'],
                    'sentiment_label' => $sentiment['label'],
                    'avg_upvotes' => round($mentions['avg_score'], 1),
                    'unique_authors' => count($mentions['unique_authors']),
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
            'posts_analyzed' => count($allPosts),
            'timestamp' => time(),
            'cached' => false
        );
        
        $this->setCache($cacheKey, $result);
        return $result;
    }
    
    /**
     * Flush all cached data
     * 
     * @return array Result of flush operation
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
     * Fetch posts from a subreddit
     * 
     * @param string $subreddit Subreddit name
     * @param int $limit Number of posts to fetch
     * @return array|null Posts data or null on error
     */
    private function fetchSubredditPosts($subreddit, $limit = 100) {
        $url = 'https://www.reddit.com/r/' . urlencode($subreddit) . '/new.json?limit=' . intval($limit);
        
        $ch = curl_init($url);
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
        if (!is_array($data) || !isset($data['data']['children'])) {
            return null;
        }
        
        $posts = array();
        foreach ($data['data']['children'] as $child) {
            if (isset($child['data'])) {
                $posts[] = $child['data'];
            }
        }
        
        return $posts;
    }
    
    /**
     * Analyze posts for mentions of a specific symbol
     * 
     * @param array $posts Posts to analyze
     * @param string $symbol Symbol to search for
     * @return array Mention analysis
     */
    private function analyzeMentions($posts, $symbol) {
        $count = 0;
        $matchedPosts = array();
        $uniqueAuthors = array();
        $totalScore = 0;
        
        $symbolLower = strtolower($symbol);
        $symbolUpper = strtoupper($symbol);
        
        // Common variations
        $variations = array(
            $symbolLower,
            $symbolUpper,
            '$' . $symbolUpper,
            '#' . $symbolUpper,
            $symbolUpper . 'COIN',
            $symbolLower . 'coin'
        );
        
        foreach ($posts as $post) {
            $title = isset($post['title']) ? strtolower($post['title']) : '';
            $selftext = isset($post['selftext']) ? strtolower($post['selftext']) : '';
            $combined = $title . ' ' . $selftext;
            
            $mentioned = false;
            foreach ($variations as $variation) {
                if (strpos($combined, strtolower($variation)) !== false) {
                    $mentioned = true;
                    break;
                }
            }
            
            // Also check for word boundaries to avoid false positives
            if (!$mentioned) {
                if (preg_match('/\b' . preg_quote($symbolLower, '/') . '\b/', $combined)) {
                    $mentioned = true;
                }
            }
            
            if ($mentioned) {
                $count++;
                $matchedPosts[] = $post;
                
                $author = isset($post['author']) ? $post['author'] : '';
                if (!empty($author)) {
                    $uniqueAuthors[$author] = true;
                }
                
                $score = isset($post['score']) ? intval($post['score']) : 0;
                $totalScore += $score;
            }
        }
        
        $avgScore = $count > 0 ? $totalScore / $count : 0;
        
        return array(
            'count' => $count,
            'matched_posts' => $matchedPosts,
            'unique_authors' => $uniqueAuthors,
            'avg_score' => $avgScore
        );
    }
    
    /**
     * Calculate sentiment from posts
     * 
     * @param array $posts Posts to analyze
     * @return array Sentiment data
     */
    private function calculateSentiment($posts) {
        $bullishScore = 0;
        $bearishScore = 0;
        $bullishCounts = array();
        $bearishCounts = array();
        
        foreach ($posts as $post) {
            $title = isset($post['title']) ? strtolower($post['title']) : '';
            $selftext = isset($post['selftext']) ? strtolower($post['selftext']) : '';
            $combined = $title . ' ' . $selftext;
            
            // Check bullish keywords
            foreach ($this->bullishKeywords as $keyword => $weight) {
                $count = substr_count($combined, strtolower($keyword));
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
                $count = substr_count($combined, strtolower($keyword));
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
        
        // Normalize to -1 to +1 range
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
     * Calculate comment velocity (comments per hour)
     * 
     * @param array $posts Posts to analyze
     * @return float Comments per hour
     */
    private function calculateCommentVelocity($posts) {
        $totalComments = 0;
        $oldestTime = time();
        $newestTime = 0;
        
        foreach ($posts as $post) {
            $numComments = isset($post['num_comments']) ? intval($post['num_comments']) : 0;
            $createdTime = isset($post['created_utc']) ? intval($post['created_utc']) : 0;
            
            $totalComments += $numComments;
            
            if ($createdTime > 0) {
                if ($createdTime < $oldestTime) {
                    $oldestTime = $createdTime;
                }
                if ($createdTime > $newestTime) {
                    $newestTime = $createdTime;
                }
            }
        }
        
        $timeSpan = $newestTime - $oldestTime;
        if ($timeSpan <= 0) {
            return 0;
        }
        
        $hours = $timeSpan / 3600;
        if ($hours <= 0) {
            return 0;
        }
        
        return $totalComments / $hours;
    }
    
    /**
     * Calculate average upvote ratio
     * 
     * @param array $posts Posts to analyze
     * @return float Average upvote ratio
     */
    private function calculateAvgUpvoteRatio($posts) {
        $totalRatio = 0;
        $count = 0;
        
        foreach ($posts as $post) {
            $upvoteRatio = isset($post['upvote_ratio']) ? floatval($post['upvote_ratio']) : 0;
            if ($upvoteRatio > 0) {
                $totalRatio += $upvoteRatio;
                $count++;
            }
        }
        
        return $count > 0 ? $totalRatio / $count : 0;
    }
    
    /**
     * Extract top posts summary
     * 
     * @param array $posts Posts to extract from
     * @param int $limit Number of posts to extract
     * @return array Top posts data
     */
    private function extractTopPosts($posts, $limit = 5) {
        // Sort by score
        usort($posts, array($this, 'sortByScore'));
        
        $topPosts = array();
        $count = 0;
        
        foreach ($posts as $post) {
            if ($count >= $limit) {
                break;
            }
            
            $topPosts[] = array(
                'title' => isset($post['title']) ? substr($post['title'], 0, 150) : '',
                'author' => isset($post['author']) ? $post['author'] : '',
                'score' => isset($post['score']) ? intval($post['score']) : 0,
                'upvote_ratio' => isset($post['upvote_ratio']) ? floatval($post['upvote_ratio']) : 0,
                'num_comments' => isset($post['num_comments']) ? intval($post['num_comments']) : 0,
                'subreddit' => isset($post['subreddit']) ? $post['subreddit'] : '',
                'permalink' => isset($post['permalink']) ? 'https://reddit.com' . $post['permalink'] : '',
                'created_utc' => isset($post['created_utc']) ? intval($post['created_utc']) : 0,
                'url' => isset($post['url']) ? $post['url'] : ''
            );
            
            $count++;
        }
        
        return $topPosts;
    }
    
    /**
     * Get data from cache
     * 
     * @param string $key Cache key
     * @return mixed|null Cached data or null
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
     * 
     * @param string $key Cache key
     * @param mixed $value Data to cache
     * @return bool Success
     */
    private function setCache($key, $value) {
        $file = $this->cacheDir . $key . '.cache';
        $data = array(
            'expires' => time() + $this->cacheTtl,
            'value' => $value
        );
        
        return @file_put_contents($file, serialize($data)) !== false;
    }
    
    /**
     * Sort posts by score (descending)
     */
    private function sortByScore($a, $b) {
        $scoreA = isset($a['score']) ? intval($a['score']) : 0;
        $scoreB = isset($b['score']) ? intval($b['score']) : 0;
        
        if ($scoreA == $scoreB) return 0;
        return ($scoreA > $scoreB) ? -1 : 1;
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
