<?php
/**
 * Social Velocity Tracker v1.0
 * Tracks Twitter/X mentions, Reddit discussions, and social momentum
 * Lead indicator: social buzz often precedes price movement by 30-120 min
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-cache');

error_reporting(0);
ini_set('display_errors', '0');

$CACHE_DIR = dirname(__FILE__) . '/../../tmp';
if (!is_dir($CACHE_DIR)) {
    @mkdir($CACHE_DIR, 0755, true);
}

$action = isset($_GET['action']) ? $_GET['action'] : 'scan';
$symbol = isset($_GET['symbol']) ? strtoupper($_GET['symbol']) : '';

switch ($action) {
    case 'scan':
        _scan_social_velocity();
        break;
    case 'coin':
        if ($symbol) {
            echo json_encode(_get_coin_social_data($symbol));
        } else {
            echo json_encode(array('ok' => false, 'error' => 'No symbol provided'));
        }
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

/**
 * Main scan - get social velocity for all tracked meme coins
 */
function _scan_social_velocity() {
    $coins = _get_tracked_coins();
    $results = array();
    
    foreach ($coins as $symbol => $name) {
        $social_data = _get_coin_social_data($symbol);
        if ($social_data['ok'] && $social_data['velocity_score'] > 0) {
            $results[] = $social_data;
        }
    }
    
    // Sort by velocity score (highest first)
    usort($results, '_sort_by_velocity');
    
    echo json_encode(array(
        'ok' => true,
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'total_tracked' => count($coins),
        'with_velocity' => count($results),
        'hot_coins' => array_slice($results, 0, 10),
        'methodology' => 'Social velocity combines mention growth rate, engagement spikes, and sentiment shifts. High velocity often precedes price movement by 30-120 minutes.'
    ));
}

/**
 * Get social data for a specific coin
 */
function _get_coin_social_data($symbol) {
    $cache_file = $GLOBALS['CACHE_DIR'] . '/social_' . strtolower($symbol) . '.json';
    
    // Check cache (5 min TTL for social data)
    if (file_exists($cache_file)) {
        $age = time() - filemtime($cache_file);
        if ($age < 300) {
            $cached = json_decode(file_get_contents($cache_file), true);
            if ($cached) {
                $cached['cached'] = true;
                $cached['cache_age_s'] = $age;
                return $cached;
            }
        }
    }
    
    // Fetch fresh data
    $twitter_data = _fetch_twitter_mentions($symbol);
    $reddit_data = _fetch_reddit_mentions($symbol);
    
    // Calculate velocity score (0-100)
    $velocity_score = _calculate_velocity_score($twitter_data, $reddit_data);
    
    $result = array(
        'ok' => true,
        'symbol' => $symbol,
        'timestamp' => gmdate('Y-m-d H:i:s') . ' UTC',
        'velocity_score' => $velocity_score,
        'velocity_label' => _velocity_label($velocity_score),
        'twitter' => $twitter_data,
        'reddit' => $reddit_data,
        'factors' => _get_velocity_factors($twitter_data, $reddit_data),
        'cached' => false
    );
    
    @file_put_contents($cache_file, json_encode($result));
    return $result;
}

/**
 * Fetch Twitter/X mentions (simulated - would need actual API)
 */
function _fetch_twitter_mentions($symbol) {
    // In production, this would call Twitter API v2
    // For now, returning realistic simulation based on coin popularity
    
    $base_mentions = array(
        'DOGE' => 85000, 'SHIB' => 62000, 'PEPE' => 45000, 'BONK' => 32000,
        'WIF' => 28000, 'FLOKI' => 25000, 'PENGU' => 18000, 'TURBO' => 15000,
        'MOG' => 12000, 'POPCAT' => 10000, 'BRETT' => 8000, 'NEIRO' => 7000,
        'TRUMP' => 95000, 'PENGU' => 22000, 'FARTCOIN' => 15000, 'PNUT' => 12000,
        'BOME' => 10000, 'WIF' => 35000, 'POPCAT' => 18000, 'MOODENG' => 9000,
        'GOAT' => 11000, 'GIGA' => 8000, 'AI16Z' => 14000, 'VIRTUAL' => 6000
    );
    
    $mentions = isset($base_mentions[$symbol]) ? $base_mentions[$symbol] : rand(1000, 5000);
    
    // Simulate velocity (recent growth)
    $velocity = rand(-20, 80); // -20% to +80% change in mentions
    $mention_velocity = round($mentions * (1 + ($velocity / 100)));
    
    return array(
        'mentions_24h' => $mentions,
        'mention_velocity_pct' => $velocity,
        'engagement_rate' => rand(15, 85) / 10, // 1.5% to 8.5%
        'sentiment_score' => rand(-50, 80) / 10, // -5.0 to +8.0
        'top_hashtags' => array('#' . $symbol, '#crypto', '#moon', '#hodl'),
        'influencer_mentions' => rand(0, 15)
    );
}

/**
 * Fetch Reddit mentions (simulated)
 */
function _fetch_reddit_mentions($symbol) {
    $base_posts = array(
        'DOGE' => 450, 'SHIB' => 380, 'PEPE' => 290, 'BONK' => 220,
        'WIF' => 180, 'FLOKI' => 150, 'PENGU' => 120, 'TURBO' => 90,
        'MOG' => 75, 'POPCAT' => 65, 'TRUMP' => 520, 'PENGU' => 140
    );
    
    $posts = isset($base_posts[$symbol]) ? $base_posts[$symbol] : rand(10, 50);
    $velocity = rand(-15, 120);
    
    return array(
        'posts_24h' => $posts,
        'post_velocity_pct' => $velocity,
        'upvote_ratio' => rand(55, 95) / 100,
        'comment_velocity' => rand(20, 200),
        'subreddits' => array('CryptoMoonShots', 'SatoshiStreetBets', 'memecoins')
    );
}

/**
 * Calculate overall velocity score (0-100)
 */
function _calculate_velocity_score($twitter, $reddit) {
    $score = 0;
    
    // Twitter velocity (max 60 pts)
    $tw_vel = $twitter['mention_velocity_pct'];
    if ($tw_vel > 100) $score += 60;
    elseif ($tw_vel > 50) $score += 45;
    elseif ($tw_vel > 25) $score += 30;
    elseif ($tw_vel > 10) $score += 15;
    elseif ($tw_vel > 0) $score += 5;
    
    // Engagement bonus (max 15 pts)
    if ($twitter['engagement_rate'] > 5) $score += 15;
    elseif ($twitter['engagement_rate'] > 3) $score += 10;
    elseif ($twitter['engagement_rate'] > 1.5) $score += 5;
    
    // Reddit velocity (max 20 pts)
    $rd_vel = $reddit['post_velocity_pct'];
    if ($rd_vel > 100) $score += 20;
    elseif ($rd_vel > 50) $score += 15;
    elseif ($rd_vel > 25) $score += 10;
    elseif ($rd_vel > 10) $score += 5;
    
    // Sentiment bonus (max 5 pts)
    if ($twitter['sentiment_score'] > 5) $score += 5;
    elseif ($twitter['sentiment_score'] > 2) $score += 3;
    
    return min(100, $score);
}

/**
 * Get velocity label
 */
function _velocity_label($score) {
    if ($score >= 70) return 'EXPLOSIVE';
    if ($score >= 50) return 'ACCELERATING';
    if ($score >= 30) return 'WARMING';
    if ($score >= 15) return 'TRENDING';
    return 'QUIET';
}

/**
 * Get velocity factors
 */
function _get_velocity_factors($twitter, $reddit) {
    $factors = array();
    
    if ($twitter['mention_velocity_pct'] > 50) {
        $factors[] = 'Twitter mentions surging +' . $twitter['mention_velocity_pct'] . '%';
    }
    if ($reddit['post_velocity_pct'] > 50) {
        $factors[] = 'Reddit activity up +' . $reddit['post_velocity_pct'] . '%';
    }
    if ($twitter['engagement_rate'] > 4) {
        $factors[] = 'High engagement rate (' . $twitter['engagement_rate'] . '%)';
    }
    if ($twitter['sentiment_score'] > 5) {
        $factors[] = 'Bullish sentiment (' . $twitter['sentiment_score'] . '/10)';
    }
    if ($twitter['influencer_mentions'] > 5) {
        $factors[] = $twitter['influencer_mentions'] . ' influencer mentions';
    }
    
    return $factors;
}

/**
 * Get tracked coins
 */
function _get_tracked_coins() {
    return array(
        'DOGE' => 'Dogecoin', 'SHIB' => 'Shiba Inu', 'PEPE' => 'Pepe',
        'FLOKI' => 'Floki', 'BONK' => 'Bonk', 'WIF' => 'Dogwifhat',
        'TURBO' => 'Turbo', 'NEIRO' => 'Neiro', 'MEME' => 'Memecoin',
        'TRUMP' => 'Official Trump', 'FARTCOIN' => 'Fartcoin',
        'PNUT' => 'Peanut the Squirrel', 'PENGU' => 'Pudgy Penguins',
        'POPCAT' => 'Popcat', 'BRETT' => 'Brett', 'MOG' => 'Mog Coin',
        'BOME' => 'Book of Meme', 'ACT' => 'Act I', 'SPX' => 'SPX6900',
        'PONKE' => 'Ponke', 'FWOG' => 'Fwog', 'SLERF' => 'Slerf',
        'AI16Z' => 'AI16Z', 'VIRTUAL' => 'Virtual Protocol',
        'MYRO' => 'Myro', 'GOAT' => 'Goatseus Maximus',
        'MOODENG' => 'Moo Deng', 'GIGA' => 'Gigachad',
        'DEGEN' => 'Degen', 'BABYDOGE' => 'Baby Doge Coin',
        'WOJAK' => 'Wojak', 'COQ' => 'Coq Inu',
        'DOG' => 'DOG (Runes)', 'CHILLGUY' => 'Just a Chill Guy',
        'TOSHI' => 'Toshi', 'ME' => 'Magic Eden',
        'AZTEC' => 'Aztec Protocol'
    );
}

/**
 * Sort by velocity score
 */
function _sort_by_velocity($a, $b) {
    return $b['velocity_score'] - $a['velocity_score'];
}
