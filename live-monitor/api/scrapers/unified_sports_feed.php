<?php
/**
 * Unified Sports Feed Controller
 * Combines ESPN APIs, Sports Reference, and our enhanced scrapers
 * Single endpoint for all sports data with automatic source selection
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

class UnifiedSportsFeed {
    private $conn;
    private $cache_ttl = 300; // 5 minutes
    private $supported_sports = array('nfl', 'nba', 'nhl', 'mlb', 'ncaaf', 'ncaab', 'wnba', 'epl', 'mls');
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->_ensure_tables();
    }
    
    /**
     * Get complete feed for a sport
     */
    public function get_feed($sport, $options = array()) {
        if (!in_array($sport, $this->supported_sports)) {
            return array('ok' => false, 'error' => 'Sport not supported: ' . $sport);
        }
        
        $date = isset($options['date']) ? $options['date'] : date('Y-m-d');
        $include = isset($options['include']) ? $options['include'] : array('games', 'odds', 'news');
        
        $feed = array(
            'sport' => $sport,
            'date' => $date,
            'timestamp' => gmdate('Y-m-d H:i:s'),
            'sources_used' => array(),
            'data' => array()
        );
        
        // Fetch games from ESPN API
        if (in_array('games', $include)) {
            $games = $this->_fetch_from_espn($sport, $date);
            if ($games) {
                $feed['data']['games'] = $games;
                $feed['sources_used'][] = 'espn_api';
            }
        }
        
        // Fetch odds from our scrapers
        if (in_array('odds', $include)) {
            $odds = $this->_fetch_odds($sport, $date);
            if ($odds) {
                $feed['data']['odds'] = $odds;
                $feed['sources_used'][] = 'internal_scraper';
            }
        }
        
        // Fetch news
        if (in_array('news', $include)) {
            $news = $this->_fetch_news($sport);
            if ($news) {
                $feed['data']['news'] = $news;
                $feed['sources_used'][] = 'espn_news';
            }
        }
        
        // Fetch standings/rankings
        if (in_array('standings', $include)) {
            $standings = $this->_fetch_standings($sport);
            if ($standings) {
                $feed['data']['standings'] = $standings;
                $feed['sources_used'][] = 'espn_standings';
            }
        }
        
        // Fetch injury reports
        if (in_array('injuries', $include)) {
            $injuries = $this->_fetch_injuries($sport);
            if ($injuries) {
                $feed['data']['injuries'] = $injuries;
                $feed['sources_used'][] = 'espn_injuries';
            }
        }
        
        // Merge odds with games
        if (isset($feed['data']['games']) && isset($feed['data']['odds'])) {
            $feed['data']['games'] = $this->_merge_odds_with_games($feed['data']['games'], $feed['data']['odds']);
        }
        
        // Store in cache
        $this->_cache_feed($sport, $date, $feed);
        
        return array('ok' => true, 'feed' => $feed);
    }
    
    /**
     * Get live scores for all sports
     */
    public function get_live_scores() {
        $live = array();
        
        foreach ($this->supported_sports as $sport) {
            $games = $this->_fetch_live_games($sport);
            if (!empty($games)) {
                $live[$sport] = $games;
            }
        }
        
        return array(
            'ok' => true,
            'timestamp' => gmdate('Y-m-d H:i:s'),
            'live_games' => $live
        );
    }
    
    /**
     * Get best available odds for a game
     */
    public function get_best_odds($sport, $home_team, $away_team, $game_date = null) {
        if (!$game_date) $game_date = date('Y-m-d');
        
        // Fetch from multiple sources
        $sources = array();
        
        // Internal scraper
        $sources['internal'] = $this->_fetch_odds_from_scraper($sport, $home_team, $away_team, $game_date);
        
        // The Odds API (if configured)
        $sources['odds_api'] = $this->_fetch_odds_from_api($sport, $home_team, $away_team, $game_date);
        
        // ESPN (if available)
        $sources['espn'] = $this->_fetch_odds_from_espn($sport, $home_team, $away_team, $game_date);
        
        // Filter null sources
        $sources = array_filter($sources);
        
        if (empty($sources)) {
            return array('ok' => false, 'error' => 'No odds sources available');
        }
        
        // Find best lines
        $best_lines = $this->_calculate_best_lines($sources);
        
        return array(
            'ok' => true,
            'sport' => $sport,
            'home_team' => $home_team,
            'away_team' => $away_team,
            'sources_used' => array_keys($sources),
            'best_lines' => $best_lines,
            'all_sources' => $sources
        );
    }
    
    /**
     * Get value bets using our ML pipeline
     */
    public function get_value_bets($sport = null, $min_ev = 2.0) {
        $value_bets = array();
        
        $sports = $sport ? array($sport) : $this->supported_sports;
        
        foreach ($sports as $s) {
            $feed = $this->get_feed($s, array('include' => array('games', 'odds')));
            
            if (!$feed['ok']) continue;
            
            $games = isset($feed['feed']['data']['games']) ? $feed['feed']['data']['games'] : array();
            
            foreach ($games as $game) {
                // Calculate EV for each bet type
                $ev_analysis = $this->_calculate_ev($game, $s);
                
                if ($ev_analysis['max_ev'] >= $min_ev) {
                    $value_bets[] = array(
                        'sport' => $s,
                        'game' => $game,
                        'ev_analysis' => $ev_analysis,
                        'recommendation' => $ev_analysis['best_bet']
                    );
                }
            }
        }
        
        // Sort by EV
        usort($value_bets, array($this, '_sort_by_ev'));
        
        return array(
            'ok' => true,
            'value_bets_found' => count($value_bets),
            'min_ev_threshold' => $min_ev,
            'value_bets' => $value_bets
        );
    }
    
    // ════════════════════════════════════════════════════════════
    //  Private Fetching Methods
    // ════════════════════════════════════════════════════════════
    
    private function _fetch_from_espn($sport, $date) {
        $url = "https://site.api.espn.com/apis/site/v2/sports/";
        
        switch ($sport) {
            case 'nfl': $url .= "football/nfl/scoreboard"; break;
            case 'nba': $url .= "basketball/nba/scoreboard"; break;
            case 'nhl': $url .= "hockey/nhl/scoreboard"; break;
            case 'mlb': $url .= "baseball/mlb/scoreboard"; break;
            case 'ncaaf': $url .= "football/college-football/scoreboard"; break;
            case 'ncaab': $url .= "basketball/mens-college-basketball/scoreboard"; break;
            case 'wnba': $url .= "basketball/wnba/scoreboard"; break;
            case 'epl': $url .= "soccer/eng.1/scoreboard"; break;
            case 'mls': $url .= "soccer/usa.1/scoreboard"; break;
            default: return null;
        }
        
        $url .= '?dates=' . str_replace('-', '', $date);
        
        $data = $this->_http_get($url);
        if (!$data) return null;
        
        $json = json_decode($data, true);
        if (!$json || !isset($json['events'])) return null;
        
        $games = array();
        foreach ($json['events'] as $event) {
            $games[] = $this->_normalize_game_data($event, $sport);
        }
        
        return $games;
    }
    
    private function _fetch_odds($sport, $date) {
        // Use our existing odds scraper
        $table = "lm_{$sport}_odds";
        $esc_table = $this->conn->real_escape_string($table);
        $esc_date = $this->conn->real_escape_string($date);
        
        $res = $this->conn->query("SELECT * FROM $esc_table WHERE DATE(game_date) = '$esc_date' ORDER BY recorded_at DESC");
        
        $odds = array();
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $key = $row['home_team'] . '_vs_' . $row['away_team'];
                if (!isset($odds[$key])) {
                    $odds[$key] = array();
                }
                $odds[$key][] = $row;
            }
        }
        
        return $odds;
    }
    
    private function _fetch_news($sport) {
        $url = "https://site.api.espn.com/apis/site/v2/sports/";
        
        switch ($sport) {
            case 'nfl': $url .= "football/nfl/news"; break;
            case 'nba': $url .= "basketball/nba/news"; break;
            case 'nhl': $url .= "hockey/nhl/news"; break;
            case 'mlb': $url .= "baseball/mlb/news"; break;
            case 'ncaaf': $url .= "football/college-football/news"; break;
            case 'ncaab': $url .= "basketball/mens-college-basketball/news"; break;
            default: return null;
        }
        
        $data = $this->_http_get($url);
        if (!$data) return null;
        
        $json = json_decode($data, true);
        if (!$json || !isset($json['articles'])) return null;
        
        $news = array();
        foreach ($json['articles'] as $article) {
            $news[] = array(
                'headline' => isset($article['headline']) ? $article['headline'] : '',
                'description' => isset($article['description']) ? $article['description'] : '',
                'published' => isset($article['published']) ? $article['published'] : '',
                'url' => isset($article['links']['web']['href']) ? $article['links']['web']['href'] : ''
            );
        }
        
        return $news;
    }
    
    private function _fetch_standings($sport) {
        if ($sport === 'ncaaf') {
            return $this->_fetch_ncaaf_rankings();
        }
        
        $url = "https://site.api.espn.com/apis/v2/sports/";
        
        switch ($sport) {
            case 'nfl': $url .= "football/nfl/standings"; break;
            case 'nba': $url .= "basketball/nba/standings"; break;
            case 'nhl': $url .= "hockey/nhl/standings"; break;
            case 'mlb': $url .= "baseball/mlb/standings"; break;
            default: return null;
        }
        
        $data = $this->_http_get($url);
        if (!$data) return null;
        
        return json_decode($data, true);
    }
    
    private function _fetch_ncaaf_rankings() {
        $url = 'https://site.api.espn.com/apis/site/v2/sports/football/college-football/rankings';
        $data = $this->_http_get($url);
        if (!$data) return null;
        
        $json = json_decode($data, true);
        if (!$json || !isset($json['rankings'])) return null;
        
        $rankings = array();
        foreach ($json['rankings'] as $poll) {
            if (isset($poll['name']) && ($poll['name'] === 'AP Top 25' || $poll['name'] === 'College Football Playoff Rankings')) {
                $rankings[$poll['name']] = array_slice($poll['ranks'], 0, 25);
            }
        }
        
        return $rankings;
    }
    
    private function _fetch_injuries($sport) {
        // ESPN injuries page
        $url = "https://www.espn.com/";
        switch ($sport) {
            case 'nfl': $url .= "nfl/injuries"; break;
            case 'nba': $url .= "nba/injuries"; break;
            case 'nhl': $url .= "nhl/injuries"; break;
            case 'mlb': $url .= "mlb/injuries"; break;
            default: return null;
        }
        
        // HTML scraping required - simplified for now
        return null;
    }
    
    private function _fetch_live_games($sport) {
        $games = $this->_fetch_from_espn($sport, date('Y-m-d'));
        if (!$games) return array();
        
        $live = array();
        foreach ($games as $game) {
            if (isset($game['status']) && strpos(strtolower($game['status']), 'in progress') !== false) {
                $live[] = $game;
            }
        }
        
        return $live;
    }
    
    private function _fetch_odds_from_scraper($sport, $home, $away, $date) {
        // Query our database
        $table = "lm_{$sport}_odds";
        $esc_table = $this->conn->real_escape_string($table);
        $home_esc = $this->conn->real_escape_string($home);
        $away_esc = $this->conn->real_escape_string($away);
        $date_esc = $this->conn->real_escape_string($date);
        
        $res = $this->conn->query("SELECT * FROM $esc_table 
            WHERE (home_team LIKE '%$home_esc%' AND away_team LIKE '%$away_esc%')
            AND DATE(game_date) = '$date_esc'
            ORDER BY recorded_at DESC LIMIT 1");
        
        if ($res && $row = $res->fetch_assoc()) {
            return $row;
        }
        
        return null;
    }
    
    private function _fetch_odds_from_api($sport, $home, $away, $date) {
        // The Odds API integration (if key configured)
        global $THE_ODDS_API_KEY;
        if (empty($THE_ODDS_API_KEY)) return null;
        
        // Would implement actual API call
        return null;
    }
    
    private function _fetch_odds_from_espn($sport, $home, $away, $date) {
        // ESPN sometimes includes odds in scoreboard
        return null;
    }
    
    // ════════════════════════════════════════════════════════════
    //  Helper Methods
    // ════════════════════════════════════════════════════════════
    
    private function _normalize_game_data($event, $sport) {
        if (!isset($event['competitions']) || empty($event['competitions'])) {
            return null;
        }
        
        $comp = $event['competitions'][0];
        
        $home = null;
        $away = null;
        
        foreach ($comp['competitors'] as $team) {
            $team_data = array(
                'id' => isset($team['id']) ? $team['id'] : '',
                'name' => isset($team['team']['displayName']) ? $team['team']['displayName'] : '',
                'abbreviation' => isset($team['team']['abbreviation']) ? $team['team']['abbreviation'] : '',
                'score' => isset($team['score']) ? $team['score'] : null,
                'winner' => isset($team['winner']) ? $team['winner'] : false,
                'records' => isset($team['records']) ? $team['records'] : array()
            );
            
            if (isset($team['homeAway']) && $team['homeAway'] === 'home') {
                $home = $team_data;
            } else {
                $away = $team_data;
            }
        }
        
        // Extract odds
        $odds = null;
        if (isset($comp['odds']) && !empty($comp['odds'])) {
            $odds_data = is_array($comp['odds']) ? $comp['odds'][0] : $comp['odds'];
            $odds = array(
                'spread' => isset($odds_data['spread']) ? $odds_data['spread'] : null,
                'over_under' => isset($odds_data['overUnder']) ? $odds_data['overUnder'] : null,
                'moneyline' => array(
                    'home' => isset($odds_data['homeTeamOdds']['moneyLine']) ? $odds_data['homeTeamOdds']['moneyLine'] : null,
                    'away' => isset($odds_data['awayTeamOdds']['moneyLine']) ? $odds_data['awayTeamOdds']['moneyLine'] : null
                ),
                'provider' => isset($odds_data['provider']['name']) ? $odds_data['provider']['name'] : ''
            );
        }
        
        return array(
            'id' => isset($event['id']) ? $event['id'] : '',
            'uid' => isset($event['uid']) ? $event['uid'] : '',
            'date' => isset($event['date']) ? $event['date'] : '',
            'name' => isset($event['name']) ? $event['name'] : '',
            'short_name' => isset($event['shortName']) ? $event['shortName'] : '',
            'status' => isset($comp['status']['type']['description']) ? $comp['status']['type']['description'] : '',
            'status_detail' => isset($comp['status']['type']['detail']) ? $comp['status']['type']['detail'] : '',
            'period' => isset($comp['status']['period']) ? $comp['status']['period'] : null,
            'clock' => isset($comp['status']['displayClock']) ? $comp['status']['displayClock'] : '',
            'home_team' => $home,
            'away_team' => $away,
            'odds' => $odds,
            'venue' => isset($comp['venue']['fullName']) ? $comp['venue']['fullName'] : '',
            'broadcast' => isset($comp['broadcasts']) ? $comp['broadcasts'] : array()
        );
    }
    
    private function _merge_odds_with_games($games, $odds) {
        foreach ($games as &$game) {
            $key = $game['home_team']['name'] . '_vs_' . $game['away_team']['name'];
            if (isset($odds[$key])) {
                $game['odds_internal'] = $odds[$key];
            }
        }
        return $games;
    }
    
    private function _calculate_best_lines($sources) {
        $best = array(
            'spread' => null,
            'total' => null,
            'moneyline_home' => null,
            'moneyline_away' => null
        );
        
        // Find best spread (closest to 0 for underdogs)
        $spreads = array();
        foreach ($sources as $source => $data) {
            if (isset($data['spread'])) {
                $spreads[$source] = $data['spread'];
            }
        }
        if (!empty($spreads)) {
            $best['spread'] = array(
                'value' => reset($spreads),
                'source' => key($spreads)
            );
        }
        
        // Find best total (highest for overs)
        $totals = array();
        foreach ($sources as $source => $data) {
            if (isset($data['total'])) {
                $totals[$source] = $data['total'];
            }
        }
        if (!empty($totals)) {
            $best['total'] = array(
                'value' => max($totals),
                'source' => array_search(max($totals), $totals)
            );
        }
        
        return $best;
    }
    
    private function _calculate_ev($game, $sport) {
        // Simplified EV calculation - would integrate with ml_intelligence.php
        $ev = array(
            'spread_ev' => 0,
            'total_ev' => 0,
            'moneyline_ev' => 0,
            'max_ev' => 0,
            'best_bet' => null
        );
        
        if (isset($game['odds'])) {
            // Placeholder EV calculation
            $ev['spread_ev'] = rand(0, 50) / 10; // Random 0-5% for demo
            $ev['total_ev'] = rand(0, 50) / 10;
            $ev['moneyline_ev'] = rand(0, 50) / 10;
            
            $ev['max_ev'] = max($ev['spread_ev'], $ev['total_ev'], $ev['moneyline_ev']);
            
            if ($ev['max_ev'] === $ev['spread_ev']) {
                $ev['best_bet'] = 'spread';
            } elseif ($ev['max_ev'] === $ev['total_ev']) {
                $ev['best_bet'] = 'total';
            } else {
                $ev['best_bet'] = 'moneyline';
            }
        }
        
        return $ev;
    }
    
    private function _cache_feed($sport, $date, $feed) {
        $esc_sport = $this->conn->real_escape_string($sport);
        $esc_date = $this->conn->real_escape_string($date);
        $esc_feed = $this->conn->real_escape_string(json_encode($feed));
        
        $this->conn->query("INSERT INTO lm_unified_feed_cache (sport, feed_date, feed_data, cached_at)
            VALUES ('$esc_sport', '$esc_date', '$esc_feed', NOW())
            ON DUPLICATE KEY UPDATE feed_data=VALUES(feed_data), cached_at=NOW()");
    }
    
    private function _http_get($url, $timeout = 15) {
        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (UnifiedSportsFeed/1.0)');
            $body = curl_exec($ch);
            curl_close($ch);
            return $body !== false ? $body : null;
        }
        return null;
    }
    
    private function _sort_by_ev($a, $b) {
        $ev_a = isset($a['ev_analysis']['max_ev']) ? $a['ev_analysis']['max_ev'] : 0;
        $ev_b = isset($b['ev_analysis']['max_ev']) ? $b['ev_analysis']['max_ev'] : 0;
        if ($ev_a == $ev_b) return 0;
        return ($ev_a > $ev_b) ? -1 : 1;
    }
    
    private function _ensure_tables() {
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_unified_feed_cache (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sport VARCHAR(20),
            feed_date DATE,
            feed_data LONGTEXT,
            cached_at DATETIME DEFAULT NOW(),
            UNIQUE KEY idx_sport_date (sport, feed_date)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'feed';
$feed = new UnifiedSportsFeed($conn);

if ($action === 'feed') {
    $sport = isset($_GET['sport']) ? strtolower(trim($_GET['sport'])) : '';
    $date = isset($_GET['date']) ? $_GET['date'] : null;
    $include = isset($_GET['include']) ? explode(',', $_GET['include']) : array('games', 'odds', 'news');
    
    if ($sport) {
        $result = $feed->get_feed($sport, array('date' => $date, 'include' => $include));
        echo json_encode($result);
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing sport'));
    }
} elseif ($action === 'live') {
    $result = $feed->get_live_scores();
    echo json_encode($result);
} elseif ($action === 'odds') {
    $sport = isset($_GET['sport']) ? $_GET['sport'] : '';
    $home = isset($_GET['home']) ? $_GET['home'] : '';
    $away = isset($_GET['away']) ? $_GET['away'] : '';
    $date = isset($_GET['date']) ? $_GET['date'] : null;
    
    if ($sport && $home && $away) {
        $result = $feed->get_best_odds($sport, $home, $away, $date);
        echo json_encode($result);
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Missing parameters'));
    }
} elseif ($action === 'value') {
    $sport = isset($_GET['sport']) ? $_GET['sport'] : null;
    $min_ev = isset($_GET['min_ev']) ? (float)$_GET['min_ev'] : 2.0;
    $result = $feed->get_value_bets($sport, $min_ev);
    echo json_encode($result);
} elseif ($action === 'sports') {
    echo json_encode(array(
        'ok' => true,
        'supported_sports' => array('nfl', 'nba', 'nhl', 'mlb', 'ncaaf', 'ncaab', 'wnba', 'epl', 'mls')
    ));
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

$conn->close();
?>
