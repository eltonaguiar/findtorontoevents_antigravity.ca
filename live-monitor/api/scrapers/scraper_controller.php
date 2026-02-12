<?php
/**
 * Sports Scraper Controller
 * Unified endpoint for running all sport scrapers
 * PHP 5.2 compatible
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

header('Content-Type: application/json');

$ADMIN_KEY = isset($SPORTS_ADMIN_KEY) ? $SPORTS_ADMIN_KEY : 'livetrader2026';

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'status';
$sport = isset($_GET['sport']) ? strtolower(trim($_GET['sport'])) : 'all';
$key = isset($_GET['key']) ? trim($_GET['key']) : '';

if ($action === 'run' && $key !== $ADMIN_KEY) {
    echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
    exit;
}

$sports = array('nba', 'nhl', 'nfl', 'mlb');
$results = array();

switch ($action) {
    case 'status':
        // Check status of all scrapers
        foreach ($sports as $s) {
            $table_prefix = 'lm_' . $s;
            $status = array(
                'odds' => _check_table_status($conn, $table_prefix . '_odds'),
                'stats' => _check_table_status($conn, $table_prefix . '_team_stats'),
                'injuries' => _check_table_status($conn, $table_prefix . '_injuries'),
                'schedule' => _check_table_status($conn, $table_prefix . '_schedule')
            );
            $results[$s] = $status;
        }
        echo json_encode(array('ok' => true, 'status' => $results, 'timestamp' => gmdate('Y-m-d H:i:s')));
        break;
        
    case 'run':
        // Run scrapers
        if ($sport === 'all') {
            $to_run = $sports;
        } else {
            $to_run = in_array($sport, $sports) ? array($sport) : array();
        }
        
        foreach ($to_run as $s) {
            $file = dirname(__FILE__) . '/' . $s . '_scraper.php';
            if (file_exists($file)) {
                // Use cURL to call the scraper endpoint
                $url = 'http' . (isset($_SERVER['HTTPS']) ? 's' : '') . '://' . $_SERVER['HTTP_HOST'] . dirname($_SERVER['PHP_SELF']) . '/' . $s . '_scraper.php?action=scrape';
                $response = _http_get($url);
                if ($response) {
                    $data = json_decode($response, true);
                    $results[$s] = $data ? $data : array('ok' => false, 'error' => 'Invalid JSON response');
                } else {
                    $results[$s] = array('ok' => false, 'error' => 'HTTP request failed');
                }
            } else {
                $results[$s] = array('ok' => false, 'error' => 'Scraper file not found');
            }
        }
        
        // Log the run
        _log_scraper_run($conn, $to_run, $results);
        
        echo json_encode(array('ok' => true, 'results' => $results, 'timestamp' => gmdate('Y-m-d H:i:s')));
        break;
        
    case 'health':
        // Check data source health
        $sources = array(
            'ESPN API NBA' => 'https://site.api.espn.com/apis/v2/sports/basketball/nba/standings',
            'ESPN API NHL' => 'https://site.api.espn.com/apis/v2/sports/hockey/nhl/standings',
            'ESPN API NFL' => 'https://site.api.espn.com/apis/v2/sports/football/nfl/standings',
            'ESPN API MLB' => 'https://site.api.espn.com/apis/v2/sports/baseball/mlb/standings'
        );
        
        foreach ($sources as $name => $url) {
            $t0 = microtime(true);
            $response = _http_get($url);
            $t1 = microtime(true);
            $results[$name] = array(
                'ok' => ($response !== null),
                'ms' => round(($t1 - $t0) * 1000)
            );
        }
        
        echo json_encode(array('ok' => true, 'health' => $results, 'timestamp' => gmdate('Y-m-d H:i:s')));
        break;
        
    case 'last_run':
        // Get last run times
        $query = "SELECT * FROM lm_scraper_log ORDER BY run_at DESC LIMIT 10";
        $res = $conn->query($query);
        $logs = array();
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $logs[] = $row;
            }
        }
        echo json_encode(array('ok' => true, 'logs' => $logs));
        break;
        
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();

// Helper functions
function _check_table_status($conn, $table) {
    // First just get count (always works if table exists)
    $cnt_q = @$conn->query("SELECT COUNT(*) as count FROM `" . $table . "`");
    if (!$cnt_q) {
        return array('count' => 0, 'last_update' => null);
    }
    $cnt_row = $cnt_q->fetch_assoc();
    $count = (int)$cnt_row['count'];

    // Try common date columns for last_update
    $last_update = null;
    $date_cols = array('updated_at', 'reported_at', 'recorded_at', 'run_at');
    foreach ($date_cols as $dc) {
        $dq = @$conn->query("SELECT MAX(`" . $dc . "`) AS latest FROM `" . $table . "`");
        if ($dq && $dr = $dq->fetch_assoc()) {
            if ($dr['latest'] !== null) {
                $last_update = $dr['latest'];
                break;
            }
        }
    }

    return array('count' => $count, 'last_update' => $last_update);
}

function _http_get($url, $timeout = 30) {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, $timeout);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        $body = curl_exec($ch);
        curl_close($ch);
        return $body !== false ? $body : null;
    }
    $ctx = stream_context_create(array(
        'http' => array('method' => 'GET', 'timeout' => $timeout),
        'ssl' => array('verify_peer' => false)
    ));
    $body = @file_get_contents($url, false, $ctx);
    return ($body === false) ? null : $body;
}

function _log_scraper_run($conn, $sports, $results) {
    $conn->query("CREATE TABLE IF NOT EXISTS lm_scraper_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        sports TEXT,
        results TEXT,
        run_at DATETIME DEFAULT NOW()
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    
    $sports_str = $conn->real_escape_string(implode(',', $sports));
    $results_str = $conn->real_escape_string(json_encode($results));
    $conn->query("INSERT INTO lm_scraper_log (sports, results, run_at) VALUES ('$sports_str', '$results_str', NOW())");
}
?>
