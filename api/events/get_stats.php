<?php
/**
 * Get events statistics for the stats page.
 * Returns JSON with event counts, pull history, and source breakdown.
 * 
 * GET: https://findtorontoevents.ca/api/events/get_stats.php
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Cache-Control: public, max-age=60');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

$out = array(
    'ok' => false,
    'stats' => array(),
    'recent_pulls' => array(),
    'sources' => array(),
    'categories' => array()
);

require_once dirname(__FILE__) . '/db_config.php';
$conn = @new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    $out['error'] = 'Database connection failed: ' . $conn->connect_error;
    echo json_encode($out);
    exit;
}

// Get summary stats
$stats = array();
$r = $conn->query("SELECT stat_name, stat_value, stat_text FROM stats_summary");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $stats[$row['stat_name']] = array(
            'value' => (int)$row['stat_value'],
            'description' => $row['stat_text']
        );
    }
}
$out['stats'] = $stats;

// Get total events (direct count)
$r = $conn->query("SELECT COUNT(*) as cnt FROM events_log");
if ($r) {
    $row = $r->fetch_assoc();
    $out['total_events'] = (int)$row['cnt'];
}

// Get recent pulls (last 10)
$recent_pulls = array();
$r = $conn->query("SELECT id, pull_timestamp, events_count, source, status, notes FROM event_pulls ORDER BY pull_timestamp DESC LIMIT 10");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $recent_pulls[] = array(
            'id' => (int)$row['id'],
            'timestamp' => $row['pull_timestamp'],
            'events_count' => (int)$row['events_count'],
            'source' => $row['source'],
            'status' => $row['status'],
            'notes' => $row['notes']
        );
    }
}
$out['recent_pulls'] = $recent_pulls;

// Get source breakdown
$sources = array();
$r = $conn->query("SELECT source, COUNT(*) as cnt FROM events_log GROUP BY source ORDER BY cnt DESC");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $sources[] = array(
            'source' => $row['source'],
            'count' => (int)$row['cnt']
        );
    }
}
$out['sources'] = $sources;

// Get category breakdown
$categories = array();
$r = $conn->query("SELECT categories, COUNT(*) as cnt FROM events_log WHERE categories != '' AND categories IS NOT NULL GROUP BY categories ORDER BY cnt DESC LIMIT 20");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $cat = $row['categories'];
        // Try to decode JSON categories
        $decoded = json_decode($cat, true);
        if (is_array($decoded)) {
            foreach ($decoded as $c) {
                if (!isset($categories[$c])) $categories[$c] = 0;
                $categories[$c] += (int)$row['cnt'];
            }
        } else {
            if (!isset($categories[$cat])) $categories[$cat] = 0;
            $categories[$cat] += (int)$row['cnt'];
        }
    }
}
// Sort by count and convert to array
arsort($categories);
$cat_array = array();
foreach ($categories as $name => $count) {
    $cat_array[] = array('category' => $name, 'count' => $count);
}
$out['categories'] = array_slice($cat_array, 0, 15);

// Get upcoming events count
$r = $conn->query("SELECT COUNT(*) as cnt FROM events_log WHERE event_date >= NOW()");
if ($r) {
    $row = $r->fetch_assoc();
    $out['upcoming_events'] = (int)$row['cnt'];
}

// Get past events count
$r = $conn->query("SELECT COUNT(*) as cnt FROM events_log WHERE event_date < NOW()");
if ($r) {
    $row = $r->fetch_assoc();
    $out['past_events'] = (int)$row['cnt'];
}

// Get free events count
$r = $conn->query("SELECT COUNT(*) as cnt FROM events_log WHERE is_free = 1");
if ($r) {
    $row = $r->fetch_assoc();
    $out['free_events'] = (int)$row['cnt'];
}

// Get last sync time
$r = $conn->query("SELECT pull_timestamp, events_count FROM event_pulls ORDER BY pull_timestamp DESC LIMIT 1");
if ($r && $r->num_rows > 0) {
    $row = $r->fetch_assoc();
    $out['last_sync'] = array(
        'timestamp' => $row['pull_timestamp'],
        'events_count' => (int)$row['events_count']
    );
}

$out['ok'] = true;
echo json_encode($out, JSON_PRETTY_PRINT);
$conn->close();
?>
