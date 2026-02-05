<?php
/**
 * Get all source links for a specific event.
 * Returns alternate sources/ticket links for events found in multiple places.
 * 
 * GET: https://findtorontoevents.ca/fc/api/events_get_sources.php?event_id=xxx
 * GET: https://findtorontoevents.ca/fc/api/events_get_sources.php?all=1 (get all events with multiple sources)
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Cache-Control: public, max-age=300');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

$out = array('ok' => false, 'sources' => array());

require_once dirname(__FILE__) . '/events_db_config.php';
$conn = @new mysqli($events_servername, $events_username, $events_password, $events_dbname);
if ($conn->connect_error) {
    $out['error'] = 'Database connection failed: ' . $conn->connect_error;
    echo json_encode($out);
    exit;
}

$event_id = isset($_GET['event_id']) ? $_GET['event_id'] : '';
$get_all = isset($_GET['all']) && $_GET['all'] == '1';

if ($get_all) {
    // Return all events that have multiple sources (for frontend caching)
    $sources_map = array();
    
    // Get all canonical events with their sources
    $r = $conn->query("
        SELECT es.canonical_event_id, es.source_event_id, es.source_name, es.source_url, es.price, es.is_primary,
               el.title, el.event_date
        FROM event_sources es
        JOIN events_log el ON es.canonical_event_id = el.event_id
        ORDER BY es.canonical_event_id, es.is_primary DESC, es.source_name
    ");
    
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $cid = $row['canonical_event_id'];
            if (!isset($sources_map[$cid])) {
                $sources_map[$cid] = array(
                    'event_id' => $cid,
                    'title' => $row['title'],
                    'event_date' => $row['event_date'],
                    'sources' => array()
                );
            }
            $sources_map[$cid]['sources'][] = array(
                'source_event_id' => $row['source_event_id'],
                'source_name' => $row['source_name'],
                'source_url' => $row['source_url'],
                'price' => $row['price'],
                'is_primary' => (int)$row['is_primary']
            );
        }
    }
    
    // Filter to only events with 2+ sources
    $multi_source_events = array();
    foreach ($sources_map as $cid => $data) {
        if (count($data['sources']) >= 2) {
            $multi_source_events[$cid] = $data;
        }
    }
    
    $out['events'] = $multi_source_events;
    $out['count'] = count($multi_source_events);
    $out['ok'] = true;
    
} else if ($event_id !== '') {
    // Get sources for a specific event
    $eid_escaped = $conn->real_escape_string($event_id);
    
    // First check if this event_id is a canonical ID
    $r = $conn->query("
        SELECT es.source_event_id, es.source_name, es.source_url, es.price, es.is_primary
        FROM event_sources es
        WHERE es.canonical_event_id = '$eid_escaped'
        ORDER BY es.is_primary DESC, es.source_name
    ");
    
    $sources = array();
    if ($r && $r->num_rows > 0) {
        while ($row = $r->fetch_assoc()) {
            $sources[] = array(
                'source_event_id' => $row['source_event_id'],
                'source_name' => $row['source_name'],
                'source_url' => $row['source_url'],
                'price' => $row['price'],
                'is_primary' => (int)$row['is_primary']
            );
        }
    } else {
        // Check if this event_id is a source (not canonical)
        $r = $conn->query("SELECT canonical_event_id FROM event_sources WHERE source_event_id = '$eid_escaped' LIMIT 1");
        if ($r && $r->num_rows > 0) {
            $row = $r->fetch_assoc();
            $canonical_id = $conn->real_escape_string($row['canonical_event_id']);
            
            // Get all sources for this canonical ID
            $r = $conn->query("
                SELECT es.source_event_id, es.source_name, es.source_url, es.price, es.is_primary
                FROM event_sources es
                WHERE es.canonical_event_id = '$canonical_id'
                ORDER BY es.is_primary DESC, es.source_name
            ");
            
            if ($r) {
                while ($row = $r->fetch_assoc()) {
                    $sources[] = array(
                        'source_event_id' => $row['source_event_id'],
                        'source_name' => $row['source_name'],
                        'source_url' => $row['source_url'],
                        'price' => $row['price'],
                        'is_primary' => (int)$row['is_primary']
                    );
                }
            }
        }
    }
    
    $out['event_id'] = $event_id;
    $out['sources'] = $sources;
    $out['has_multiple_sources'] = count($sources) >= 2;
    $out['ok'] = true;
    
} else {
    $out['error'] = 'Missing event_id parameter. Use ?event_id=xxx or ?all=1';
}

echo json_encode($out);
$conn->close();
?>
