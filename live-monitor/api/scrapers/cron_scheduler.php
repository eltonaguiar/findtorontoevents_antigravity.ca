<?php
/**
 * Sports Scraper Cron Scheduler
 * Designed to be called via cron every 5-15 minutes
 * PHP 5.2 compatible
 * 
 * Recommended cron schedule:
 * */5 * * * * php /path/to/cron_scheduler.php  # Every 5 minutes during games
 * 0 */2 * * * php /path/to/cron_scheduler.php stats  # Every 2 hours for stats
 */

require_once dirname(dirname(__FILE__)) . '/sports_db_connect.php';

// Determine what to run based on arguments or time
$mode = isset($argv[1]) ? $argv[1] : 'auto';

// Auto-detect what to scrape based on time and season
if ($mode === 'auto') {
    $hour = (int)gmdate('H');
    $month = (int)gmdate('n');
    
    // Define active seasons (approximate)
    $nba_active = ($month >= 10 || $month <= 4);  // Oct-Apr
    $nhl_active = ($month >= 10 || $month <= 4);  // Oct-Apr
    $nfl_active = ($month >= 9 || $month <= 2);   // Sep-Feb
    $mlb_active = ($month >= 3 && $month <= 10);  // Mar-Oct
    
    // Scrape odds more frequently during game hours (12PM-12AM ET = 17:00-05:00 UTC)
    $is_game_time = ($hour >= 17 || $hour <= 5);
    
    $to_scrape = array();
    if ($nba_active && $is_game_time) $to_scrape[] = 'nba';
    if ($nhl_active && $is_game_time) $to_scrape[] = 'nhl';
    if ($nfl_active && ($hour >= 17 || $hour <= 23)) $to_scrape[] = 'nfl'; // NFL mostly weekends
    if ($mlb_active && $is_game_time) $to_scrape[] = 'mlb';
    
} elseif ($mode === 'all') {
    $to_scrape = array('nba', 'nhl', 'nfl', 'mlb');
} elseif ($mode === 'stats') {
    // Stats-only mode - run less frequently
    $to_scrape = array('nba', 'nhl', 'nfl', 'mlb');
    $scrape_type = 'stats';
} else {
    $to_scrape = array($mode);
}

$scrape_type = isset($scrape_type) ? $scrape_type : 'scrape';
$results = array();
$success_count = 0;

foreach ($to_scrape as $sport) {
    $endpoint = dirname(__FILE__) . '/' . $sport . '_scraper.php';
    
    if (!file_exists($endpoint)) {
        $results[$sport] = array('ok' => false, 'error' => 'File not found: ' . $endpoint);
        continue;
    }
    
    // Build URL
    $protocol = isset($_SERVER['HTTPS']) ? 'https' : 'http';
    $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER['HTTP_HOST'] : 'localhost';
    $url = $protocol . '://' . $host . '/live-monitor/api/scrapers/' . $sport . '_scraper.php?action=' . $scrape_type;
    
    // Execute scraper
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 60);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($response && $http_code === 200) {
        $data = json_decode($response, true);
        if ($data && isset($data['ok']) && $data['ok']) {
            $results[$sport] = array('ok' => true, 'data' => $data);
            $success_count++;
        } else {
            $results[$sport] = array('ok' => false, 'error' => 'Invalid response', 'response' => substr($response, 0, 200));
        }
    } else {
        $results[$sport] = array('ok' => false, 'error' => 'HTTP ' . $http_code);
    }
}

// Log results
_log_run($conn, $mode, $to_scrape, $results, $success_count);

// Output for cron logging
$output = array(
    'timestamp' => gmdate('Y-m-d H:i:s'),
    'mode' => $mode,
    'scraped' => $to_scrape,
    'success_count' => $success_count,
    'total_count' => count($to_scrape)
);

echo json_encode($output) . "\n";
$conn->close();
exit($success_count === count($to_scrape) ? 0 : 1);

function _log_run($conn, $mode, $sports, $results, $success_count) {
    $conn->query("CREATE TABLE IF NOT EXISTS lm_cron_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        mode VARCHAR(20),
        sports TEXT,
        success_count INT,
        total_count INT,
        details TEXT,
        run_at DATETIME DEFAULT NOW()
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
    
    $mode_esc = $conn->real_escape_string($mode);
    $sports_esc = $conn->real_escape_string(implode(',', $sports));
    $details_esc = $conn->real_escape_string(json_encode($results));
    $total = count($sports);
    
    $conn->query("INSERT INTO lm_cron_log (mode, sports, success_count, total_count, details, run_at) 
                  VALUES ('$mode_esc', '$sports_esc', $success_count, $total, '$details_esc', NOW())");
}
?>
