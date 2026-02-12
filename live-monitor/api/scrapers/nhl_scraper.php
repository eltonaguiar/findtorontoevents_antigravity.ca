<?php
/**
 * NHL Comprehensive Scraper
 * Fetches odds, stats, injuries, and game data from multiple sources
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

class NHLScraper {
    private $conn;
    private $errors = array();
    
    public function __construct($connection) {
        $this->conn = $connection;
        $this->_ensure_tables();
    }
    
    public function scrape_all() {
        $results = array(
            'odds' => $this->scrape_odds(),
            'stats' => $this->scrape_stats(),
            'injuries' => $this->scrape_injuries(),
            'schedule' => $this->scrape_schedule(),
            'timestamp' => gmdate('Y-m-d H:i:s')
        );
        $results['errors'] = $this->errors;
        return $results;
    }
    
    public function scrape_odds() {
        $odds = array();
        $espn = $this->_scrape_espn_lines();
        if ($espn) $odds['espn'] = $espn;
        $this->_store_odds($odds);
        return $odds;
    }
    
    public function scrape_stats() {
        $stats = array();
        $espn = $this->_fetch_espn_standings();
        if ($espn) $stats = $espn;
        $this->_store_stats($stats);
        return $stats;
    }
    
    public function scrape_injuries() {
        $injuries = array();
        $espn = $this->_scrape_espn_injuries();
        if ($espn) $injuries = $espn;
        $this->_store_injuries($injuries);
        return $injuries;
    }
    
    public function scrape_schedule() {
        $games = array();
        $espn = $this->_fetch_espn_scoreboard();
        if ($espn) $games = $espn;
        $this->_store_schedule($games);
        return $games;
    }
    
    private function _http_get($url, $timeout = 10) {
        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
            $body = curl_exec($ch);
            $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            if ($body !== false && $code >= 200 && $code < 300) return $body;
            return null;
        }
        $ctx = stream_context_create(array(
            'http' => array('method' => 'GET', 'timeout' => $timeout, 'header' => "User-Agent: Mozilla/5.0\r\n"),
            'ssl' => array('verify_peer' => false)
        ));
        $body = @file_get_contents($url, false, $ctx);
        return ($body === false) ? null : $body;
    }
    
    private function _scrape_espn_lines() {
        $url = 'https://www.espn.com/nhl/lines';
        $body = $this->_http_get($url);
        if (!$body) { $this->errors[] = 'ESPN lines failed'; return null; }
        $games = array();
        preg_match_all('/<div[^>]*class="[^"]*game-line[^"]*"[^>]*>(.*?)<\/div>/s', $body, $matches);
        foreach ($matches[1] as $game_html) {
            $game = array('away_team' => '', 'home_team' => '', 'puck_line' => '', 'total' => '', 'bookmaker' => 'ESPN');
            if (preg_match('/<span[^>]*class="[^"]*team-name[^"]*"[^>]*>(.*?)<\/span>/', $game_html, $tm)) {
                $game['away_team'] = trim(strip_tags($tm[1]));
            }
            if (preg_match('/<td[^>]*class="[^"]*line-cell[^"]*"[^>]*>(.*?)<\/td>/', $game_html, $pl)) {
                $game['puck_line'] = trim(strip_tags($pl[1]));
            }
            if (preg_match('/Total[^>]*>([^<]+)/', $game_html, $tot)) {
                $game['total'] = trim($tot[1]);
            }
            if (!empty($game['away_team']) && !empty($game['home_team'])) $games[] = $game;
        }
        return count($games) > 0 ? $games : null;
    }
    
    private function _fetch_espn_standings() {
        $url = 'https://site.api.espn.com/apis/v2/sports/hockey/nhl/standings';
        $body = $this->_http_get($url);
        if (!$body) return null;
        $data = json_decode($body, true);
        if (!$data || !isset($data['children'])) return null;
        $teams = array();
        foreach ($data['children'] as $div) {
            if (!isset($div['standings']['entries'])) continue;
            $div_name = isset($div['name']) ? $div['name'] : '';
            foreach ($div['standings']['entries'] as $entry) {
                if (!isset($entry['team'])) continue;
                $team = $entry['team'];
                $stats = array();
                if (isset($entry['stats'])) {
                    foreach ($entry['stats'] as $s) {
                        $stats[$s['name']] = isset($s['displayValue']) ? $s['displayValue'] : $s['value'];
                    }
                }
                $wins = isset($stats['wins']) ? (int)$stats['wins'] : 0;
                $losses = isset($stats['losses']) ? (int)$stats['losses'] : 0;
                $otl = isset($stats['overtimeLosses']) ? (int)$stats['overtimeLosses'] : 0;
                $points = ($wins * 2) + $otl;
                $teams[] = array(
                    'name' => isset($team['displayName']) ? $team['displayName'] : '',
                    'abbreviation' => isset($team['abbreviation']) ? $team['abbreviation'] : '',
                    'division' => $div_name,
                    'wins' => $wins,
                    'losses' => $losses,
                    'otl' => $otl,
                    'points' => $points,
                    'win_pct' => isset($stats['winPercent']) ? (float)$stats['winPercent'] : (($wins + $losses + $otl) > 0 ? round($wins / ($wins + $losses + $otl), 3) : 0),
                    'gf' => isset($stats['pointsFor']) ? (int)$stats['pointsFor'] : 0,
                    'ga' => isset($stats['pointsAgainst']) ? (int)$stats['pointsAgainst'] : 0,
                    'streak' => isset($stats['streak']) ? $stats['streak'] : ''
                );
            }
        }
        return count($teams) > 0 ? $teams : null;
    }
    
    private function _scrape_espn_injuries() {
        $url = 'https://www.espn.com/nhl/injuries';
        $body = $this->_http_get($url);
        if (!$body) return null;
        $injuries = array();
        preg_match_all('/<tr[^>]*>(.*?)<\/tr>/s', $body, $rows);
        foreach ($rows[1] as $row) {
            preg_match_all('/<td[^>]*>(.*?)<\/td>/s', $row, $cells);
            if (count($cells[1]) >= 3) {
                $injuries[] = array(
                    'player' => trim(strip_tags($cells[1][0])),
                    'team' => trim(strip_tags($cells[1][1])),
                    'status' => trim(strip_tags($cells[1][2])),
                    'source' => 'ESPN'
                );
            }
        }
        return count($injuries) > 0 ? $injuries : null;
    }
    
    private function _fetch_espn_scoreboard() {
        $url = 'https://site.api.espn.com/apis/site/v2/sports/hockey/nhl/scoreboard';
        $body = $this->_http_get($url);
        if (!$body) return null;
        $data = json_decode($body, true);
        if (!$data || !isset($data['events'])) return null;
        $games = array();
        foreach ($data['events'] as $event) {
            if (!isset($event['competitions'])) continue;
            foreach ($event['competitions'] as $comp) {
                $game = array(
                    'game_id' => isset($event['id']) ? $event['id'] : '',
                    'date' => isset($event['date']) ? $event['date'] : '',
                    'status' => isset($comp['status']['type']['description']) ? $comp['status']['type']['description'] : ''
                );
                if (isset($comp['competitors'])) {
                    foreach ($comp['competitors'] as $team) {
                        $name = isset($team['team']['displayName']) ? $team['team']['displayName'] : '';
                        $is_home = isset($team['homeAway']) && $team['homeAway'] === 'home';
                        if ($is_home) {
                            $game['home_team'] = $name;
                            $game['home_score'] = isset($team['score']) ? $team['score'] : '';
                            $game['home_shots'] = isset($team['statistics'][0]['displayValue']) ? $team['statistics'][0]['displayValue'] : '';
                        } else {
                            $game['away_team'] = $name;
                            $game['away_score'] = isset($team['score']) ? $team['score'] : '';
                            $game['away_shots'] = isset($team['statistics'][0]['displayValue']) ? $team['statistics'][0]['displayValue'] : '';
                        }
                    }
                }
                $games[] = $game;
            }
        }
        return count($games) > 0 ? $games : null;
    }
    
    private function _ensure_tables() {
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_nhl_odds (
            id INT AUTO_INCREMENT PRIMARY KEY, game_date DATETIME, away_team VARCHAR(100), home_team VARCHAR(100),
            puck_line VARCHAR(20), total VARCHAR(20), away_ml VARCHAR(10), home_ml VARCHAR(10), bookmaker VARCHAR(50),
            recorded_at DATETIME DEFAULT NOW(), INDEX idx_teams (away_team, home_team), INDEX idx_date (game_date)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_nhl_team_stats (
            id INT AUTO_INCREMENT PRIMARY KEY, team_name VARCHAR(100), abbreviation VARCHAR(10), division VARCHAR(50),
            wins INT, losses INT, otl INT, points INT, win_pct DECIMAL(4,3), gf INT, ga INT, streak VARCHAR(20),
            updated_at DATETIME DEFAULT NOW(), UNIQUE KEY idx_team (team_name), INDEX idx_div (division)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_nhl_injuries (
            id INT AUTO_INCREMENT PRIMARY KEY, player VARCHAR(100), team VARCHAR(100), position VARCHAR(20),
            status VARCHAR(100), source VARCHAR(50), reported_at DATETIME DEFAULT NOW(),
            INDEX idx_team (team), INDEX idx_player (player)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
        
        $this->conn->query("CREATE TABLE IF NOT EXISTS lm_nhl_schedule (
            id INT AUTO_INCREMENT PRIMARY KEY, game_id VARCHAR(50), game_date DATETIME, away_team VARCHAR(100),
            home_team VARCHAR(100), away_score INT, home_score INT, away_shots INT, home_shots INT,
            status VARCHAR(50), updated_at DATETIME DEFAULT NOW(), UNIQUE KEY idx_game (game_id), INDEX idx_date (game_date)
        ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    }
    
    private function _store_odds($odds) {
        foreach ($odds as $source => $games) {
            if (!is_array($games)) continue;
            foreach ($games as $game) {
                $away = isset($game['away_team']) ? $this->conn->real_escape_string($game['away_team']) : '';
                $home = isset($game['home_team']) ? $this->conn->real_escape_string($game['home_team']) : '';
                $pl = isset($game['puck_line']) ? $this->conn->real_escape_string($game['puck_line']) : '';
                $total = isset($game['total']) ? $this->conn->real_escape_string($game['total']) : '';
                $book = isset($game['bookmaker']) ? $this->conn->real_escape_string($game['bookmaker']) : $source;
                $query = "INSERT INTO lm_nhl_odds (away_team, home_team, puck_line, total, bookmaker, recorded_at) 
                          VALUES ('$away', '$home', '$pl', '$total', '$book', NOW())";
                $this->conn->query($query);
            }
        }
    }
    
    private function _store_stats($stats) {
        foreach ($stats as $team) {
            $name = isset($team['name']) ? $this->conn->real_escape_string($team['name']) : '';
            $abbr = isset($team['abbreviation']) ? $this->conn->real_escape_string($team['abbreviation']) : '';
            $div = isset($team['division']) ? $this->conn->real_escape_string($team['division']) : '';
            $wins = isset($team['wins']) ? (int)$team['wins'] : 0;
            $losses = isset($team['losses']) ? (int)$team['losses'] : 0;
            $otl = isset($team['otl']) ? (int)$team['otl'] : 0;
            $points = isset($team['points']) ? (int)$team['points'] : 0;
            $win_pct = isset($team['win_pct']) ? $team['win_pct'] : 0;
            $gf = isset($team['gf']) ? (int)$team['gf'] : 0;
            $ga = isset($team['ga']) ? (int)$team['ga'] : 0;
            $streak = isset($team['streak']) ? $this->conn->real_escape_string($team['streak']) : '';
            $query = "INSERT INTO lm_nhl_team_stats (team_name, abbreviation, division, wins, losses, otl, points, win_pct, gf, ga, streak, updated_at)
                      VALUES ('$name', '$abbr', '$div', $wins, $losses, $otl, $points, $win_pct, $gf, $ga, '$streak', NOW())
                      ON DUPLICATE KEY UPDATE wins=VALUES(wins), losses=VALUES(losses), otl=VALUES(otl), points=VALUES(points),
                      win_pct=VALUES(win_pct), gf=VALUES(gf), ga=VALUES(ga), streak=VALUES(streak), updated_at=NOW()";
            $this->conn->query($query);
        }
    }
    
    private function _store_injuries($injuries) {
        $this->conn->query("DELETE FROM lm_nhl_injuries WHERE reported_at < DATE_SUB(NOW(), INTERVAL 7 DAY)");
        foreach ($injuries as $injury) {
            $player = isset($injury['player']) ? $this->conn->real_escape_string($injury['player']) : '';
            $team = isset($injury['team']) ? $this->conn->real_escape_string($injury['team']) : '';
            $status = isset($injury['status']) ? $this->conn->real_escape_string($injury['status']) : '';
            $source = isset($injury['source']) ? $this->conn->real_escape_string($injury['source']) : '';
            $query = "INSERT INTO lm_nhl_injuries (player, team, status, source, reported_at)
                      VALUES ('$player', '$team', '$status', '$source', NOW())
                      ON DUPLICATE KEY UPDATE status=VALUES(status), reported_at=NOW()";
            $this->conn->query($query);
        }
    }
    
    private function _store_schedule($games) {
        foreach ($games as $game) {
            $game_id = isset($game['game_id']) ? $this->conn->real_escape_string($game['game_id']) : '';
            $date = isset($game['date']) ? $this->conn->real_escape_string($game['date']) : '';
            $away = isset($game['away_team']) ? $this->conn->real_escape_string($game['away_team']) : '';
            $home = isset($game['home_team']) ? $this->conn->real_escape_string($game['home_team']) : '';
            $away_score = isset($game['away_score']) && $game['away_score'] !== '' ? (int)$game['away_score'] : 'NULL';
            $home_score = isset($game['home_score']) && $game['home_score'] !== '' ? (int)$game['home_score'] : 'NULL';
            $status = isset($game['status']) ? $this->conn->real_escape_string($game['status']) : '';
            $query = "INSERT INTO lm_nhl_schedule (game_id, game_date, away_team, home_team, away_score, home_score, status, updated_at)
                      VALUES ('$game_id', '$date', '$away', '$home', $away_score, $home_score, '$status', NOW())
                      ON DUPLICATE KEY UPDATE away_score=VALUES(away_score), home_score=VALUES(home_score), status=VALUES(status), updated_at=NOW()";
            $this->conn->query($query);
        }
    }
}

// API Endpoint
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'scrape';
$scraper = new NHLScraper($conn);

if ($action === 'scrape') {
    $results = $scraper->scrape_all();
    echo json_encode(array('ok' => true, 'sport' => 'NHL', 'data' => $results, 'timestamp' => gmdate('Y-m-d H:i:s')));
} elseif ($action === 'odds') {
    echo json_encode(array('ok' => true, 'odds' => $scraper->scrape_odds()));
} elseif ($action === 'stats') {
    echo json_encode(array('ok' => true, 'stats' => $scraper->scrape_stats()));
} elseif ($action === 'injuries') {
    echo json_encode(array('ok' => true, 'injuries' => $scraper->scrape_injuries()));
} elseif ($action === 'schedule') {
    echo json_encode(array('ok' => true, 'schedule' => $scraper->scrape_schedule()));
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}
$conn->close();
?>
