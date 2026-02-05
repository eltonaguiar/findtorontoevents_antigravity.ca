<?php
/**
 * Find and link duplicate events based on title similarity.
 * This scans events_log and creates links in event_sources for events
 * that appear to be the same event from different sources.
 * 
 * GET: https://findtorontoevents.ca/fc/api/events_find_duplicates.php
 * GET ?rebuild=1 - Rebuild the entire index
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

set_time_limit(120);

$out = array(
    'ok' => false,
    'indexed' => 0,
    'duplicates_found' => 0,
    'groups_created' => 0
);

require_once dirname(__FILE__) . '/events_db_config.php';
$conn = @new mysqli($events_servername, $events_username, $events_password, $events_dbname);
if ($conn->connect_error) {
    $out['error'] = 'Database connection failed: ' . $conn->connect_error;
    echo json_encode($out);
    exit;
}

// Helper function to normalize titles for comparison
function normalize_title($title) {
    // Lowercase
    $title = strtolower($title);
    // Remove common prefixes/suffixes
    $title = preg_replace('/^(the|a|an)\s+/i', '', $title);
    // Remove punctuation and extra whitespace
    $title = preg_replace('/[^\w\s]/', ' ', $title);
    $title = preg_replace('/\s+/', ' ', $title);
    $title = trim($title);
    return $title;
}

// Rebuild index if requested
$rebuild = isset($_GET['rebuild']) && $_GET['rebuild'] == '1';

if ($rebuild) {
    $conn->query("TRUNCATE TABLE event_title_index");
    $conn->query("TRUNCATE TABLE event_sources");
}

// Step 1: Build/update title index
$indexed = 0;
$r = $conn->query("SELECT event_id, title, event_date, source FROM events_log");
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $event_id = $conn->real_escape_string($row['event_id']);
        $normalized = $conn->real_escape_string(normalize_title($row['title']));
        $event_date = $row['event_date'] ? "'" . $conn->real_escape_string(substr($row['event_date'], 0, 10)) . "'" : 'NULL';
        $source = $conn->real_escape_string($row['source']);
        
        $sql = "INSERT INTO event_title_index (event_id, normalized_title, event_date, source) 
                VALUES ('$event_id', '$normalized', $event_date, '$source')
                ON DUPLICATE KEY UPDATE normalized_title = VALUES(normalized_title), event_date = VALUES(event_date), source = VALUES(source)";
        if ($conn->query($sql)) {
            $indexed++;
        }
    }
}
$out['indexed'] = $indexed;

// Step 2: Find duplicates based on normalized title (with or without date)
$duplicates_found = 0;
$groups_created = 0;

// Strategy 1: Exact title match (regardless of date)
$r = $conn->query("
    SELECT normalized_title, GROUP_CONCAT(DISTINCT event_id) as event_ids, 
           GROUP_CONCAT(DISTINCT source) as sources, COUNT(DISTINCT source) as source_cnt
    FROM event_title_index
    WHERE normalized_title != '' AND LENGTH(normalized_title) > 10
    GROUP BY normalized_title
    HAVING source_cnt > 1
    ORDER BY source_cnt DESC
    LIMIT 200
");

// Process exact title matches
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $event_ids = array_unique(explode(',', $row['event_ids']));
        if (count($event_ids) < 2) continue;
        
        $canonical_id = $event_ids[0];
        $canonical_escaped = $conn->real_escape_string($canonical_id);
        
        foreach ($event_ids as $eid) {
            $eid_escaped = $conn->real_escape_string($eid);
            $er = $conn->query("SELECT event_id, source, url, price FROM events_log WHERE event_id = '$eid_escaped'");
            if ($er && $er->num_rows > 0) {
                $event = $er->fetch_assoc();
                $source_name = $conn->real_escape_string($event['source']);
                $source_url = $conn->real_escape_string($event['url']);
                $price = $conn->real_escape_string($event['price'] ? $event['price'] : '');
                $is_primary = ($eid === $canonical_id) ? 1 : 0;
                
                $sql = "INSERT INTO event_sources (canonical_event_id, source_event_id, source_name, source_url, price, is_primary, match_confidence)
                        VALUES ('$canonical_escaped', '$eid_escaped', '$source_name', '$source_url', '$price', $is_primary, 100)
                        ON DUPLICATE KEY UPDATE source_name = VALUES(source_name), source_url = VALUES(source_url), price = VALUES(price)";
                if ($conn->query($sql)) {
                    $duplicates_found++;
                }
            }
        }
        $groups_created++;
    }
}

// Strategy 2: Find events with same date and similar first 30 chars of title (different sources)
$r = $conn->query("
    SELECT event_date, LEFT(normalized_title, 30) as title_prefix, 
           GROUP_CONCAT(DISTINCT event_id) as event_ids,
           GROUP_CONCAT(DISTINCT source) as sources, COUNT(DISTINCT source) as source_cnt
    FROM event_title_index
    WHERE normalized_title != '' AND event_date IS NOT NULL
    GROUP BY event_date, LEFT(normalized_title, 30)
    HAVING source_cnt > 1
    ORDER BY source_cnt DESC
    LIMIT 200
");

if ($r) {
    while ($row = $r->fetch_assoc()) {
        $event_ids = explode(',', $row['event_ids']);
        if (count($event_ids) < 2) continue;
        
        // Use the first event_id as canonical
        $canonical_id = $event_ids[0];
        $canonical_escaped = $conn->real_escape_string($canonical_id);
        
        // Get details for each event
        foreach ($event_ids as $eid) {
            $eid_escaped = $conn->real_escape_string($eid);
            
            // Get event details
            $er = $conn->query("SELECT event_id, source, url, price FROM events_log WHERE event_id = '$eid_escaped'");
            if ($er && $er->num_rows > 0) {
                $event = $er->fetch_assoc();
                $source_name = $conn->real_escape_string($event['source']);
                $source_url = $conn->real_escape_string($event['url']);
                $price = $conn->real_escape_string($event['price'] ? $event['price'] : '');
                $is_primary = ($eid === $canonical_id) ? 1 : 0;
                
                // Insert into event_sources
                $sql = "INSERT INTO event_sources (canonical_event_id, source_event_id, source_name, source_url, price, is_primary)
                        VALUES ('$canonical_escaped', '$eid_escaped', '$source_name', '$source_url', '$price', $is_primary)
                        ON DUPLICATE KEY UPDATE source_name = VALUES(source_name), source_url = VALUES(source_url), price = VALUES(price)";
                if ($conn->query($sql)) {
                    $duplicates_found++;
                }
            }
        }
        $groups_created++;
    }
}

$out['duplicates_found'] = $duplicates_found;
$out['groups_created'] = $groups_created;
$out['ok'] = true;

echo json_encode($out);
$conn->close();
?>
