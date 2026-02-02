<?php
/**
 * Sync events from events.json to the database.
 * POST to this endpoint to sync events, or GET to sync from local events.json
 * 
 * GET: https://findtorontoevents.ca/api/events/sync_events.php
 * POST: Send JSON body with events array
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

$out = array(
    'ok' => false,
    'pull_id' => null,
    'events_synced' => 0,
    'events_updated' => 0,
    'events_inserted' => 0,
    'errors' => array()
);

require_once dirname(__FILE__) . '/db_config.php';
$conn = @new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    $out['error'] = 'Database connection failed: ' . $conn->connect_error;
    echo json_encode($out);
    exit;
}

// Get events data
$events = array();
$source = 'manual';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Read from POST body
    $input = file_get_contents('php://input');
    $data = json_decode($input, true);
    if (isset($data['events']) && is_array($data['events'])) {
        $events = $data['events'];
        $source = isset($data['source']) ? $data['source'] : 'api_post';
    } else if (is_array($data)) {
        // Assume the entire body is an array of events
        $events = $data;
        $source = 'api_post';
    }
} else {
    // Try to read from local events.json file
    $events_file = dirname(dirname(dirname(__FILE__))) . '/events.json';
    if (file_exists($events_file)) {
        $raw = file_get_contents($events_file);
        $events = json_decode($raw, true);
        if (!is_array($events)) $events = array();
        $source = 'events.json';
    }
}

if (count($events) === 0) {
    $out['error'] = 'No events to sync';
    echo json_encode($out);
    $conn->close();
    exit;
}

// Create a pull record
$source_escaped = $conn->real_escape_string($source);
$events_count = count($events);
$insert_pull = $conn->query("INSERT INTO event_pulls (events_count, source, status) VALUES ($events_count, '$source_escaped', 'processing')");

if (!$insert_pull) {
    $out['error'] = 'Failed to create pull record: ' . $conn->error;
    echo json_encode($out);
    $conn->close();
    exit;
}

$pull_id = $conn->insert_id;
$out['pull_id'] = $pull_id;

// Sync each event
$inserted = 0;
$updated = 0;

foreach ($events as $event) {
    if (!isset($event['id']) || !isset($event['title'])) {
        $out['errors'][] = 'Event missing id or title';
        continue;
    }
    
    $event_id = $conn->real_escape_string($event['id']);
    $title = $conn->real_escape_string($event['title']);
    
    // Parse date
    $event_date = null;
    if (isset($event['date'])) {
        $ts = strtotime($event['date']);
        if ($ts !== false) {
            $event_date = date('Y-m-d H:i:s', $ts);
        }
    }
    $event_date_sql = $event_date ? "'$event_date'" : 'NULL';
    
    $location = isset($event['location']) ? $conn->real_escape_string($event['location']) : '';
    $source_name = isset($event['source']) ? $conn->real_escape_string($event['source']) : '';
    $host = isset($event['host']) ? $conn->real_escape_string($event['host']) : '';
    $url = isset($event['url']) ? $conn->real_escape_string($event['url']) : '';
    $price = isset($event['price']) ? $conn->real_escape_string($event['price']) : '';
    $price_amount = isset($event['priceAmount']) ? (float)$event['priceAmount'] : 0;
    $is_free = isset($event['isFree']) ? (int)(bool)$event['isFree'] : 0;
    $description = isset($event['description']) ? $conn->real_escape_string($event['description']) : '';
    $status = isset($event['status']) ? $conn->real_escape_string($event['status']) : 'UPCOMING';
    
    $categories = '';
    if (isset($event['categories'])) {
        $categories = is_array($event['categories']) ? $conn->real_escape_string(json_encode($event['categories'])) : $conn->real_escape_string($event['categories']);
    }
    
    $tags = '';
    if (isset($event['tags'])) {
        $tags = is_array($event['tags']) ? $conn->real_escape_string(json_encode($event['tags'])) : $conn->real_escape_string($event['tags']);
    }
    
    // Check if event exists
    $check = $conn->query("SELECT id FROM events_log WHERE event_id = '$event_id'");
    if ($check && $check->num_rows > 0) {
        // Update existing event
        $sql = "UPDATE events_log SET 
            pull_id = $pull_id,
            title = '$title',
            event_date = $event_date_sql,
            location = '$location',
            source = '$source_name',
            host = '$host',
            url = '$url',
            price = '$price',
            price_amount = $price_amount,
            is_free = $is_free,
            description = '$description',
            categories = '$categories',
            status = '$status',
            tags = '$tags',
            last_updated = NOW()
            WHERE event_id = '$event_id'";
        if ($conn->query($sql)) {
            $updated++;
        } else {
            $out['errors'][] = "Update failed for $event_id: " . $conn->error;
        }
    } else {
        // Insert new event
        $sql = "INSERT INTO events_log (event_id, pull_id, title, event_date, location, source, host, url, price, price_amount, is_free, description, categories, status, tags)
            VALUES ('$event_id', $pull_id, '$title', $event_date_sql, '$location', '$source_name', '$host', '$url', '$price', $price_amount, $is_free, '$description', '$categories', '$status', '$tags')";
        if ($conn->query($sql)) {
            $inserted++;
        } else {
            $out['errors'][] = "Insert failed for $event_id: " . $conn->error;
        }
    }
}

$out['events_synced'] = $inserted + $updated;
$out['events_inserted'] = $inserted;
$out['events_updated'] = $updated;

// Update pull record with final status
$status = count($out['errors']) > 0 ? 'partial' : 'success';
$notes = $conn->real_escape_string("Inserted: $inserted, Updated: $updated, Errors: " . count($out['errors']));
$conn->query("UPDATE event_pulls SET status = '$status', notes = '$notes' WHERE id = $pull_id");

// Update stats_summary
$total_events = 0;
$r = $conn->query("SELECT COUNT(*) as cnt FROM events_log");
if ($r) { $row = $r->fetch_assoc(); $total_events = (int)$row['cnt']; }

$total_pulls = 0;
$r = $conn->query("SELECT COUNT(*) as cnt FROM event_pulls");
if ($r) { $row = $r->fetch_assoc(); $total_pulls = (int)$row['cnt']; }

$upcoming_events = 0;
$r = $conn->query("SELECT COUNT(*) as cnt FROM events_log WHERE event_date >= NOW()");
if ($r) { $row = $r->fetch_assoc(); $upcoming_events = (int)$row['cnt']; }

$free_events = 0;
$r = $conn->query("SELECT COUNT(*) as cnt FROM events_log WHERE is_free = 1");
if ($r) { $row = $r->fetch_assoc(); $free_events = (int)$row['cnt']; }

$conn->query("UPDATE stats_summary SET stat_value = $total_events WHERE stat_name = 'total_events'");
$conn->query("UPDATE stats_summary SET stat_value = $total_pulls WHERE stat_name = 'total_pulls'");
$conn->query("UPDATE stats_summary SET stat_value = $events_count WHERE stat_name = 'last_pull_count'");
$conn->query("UPDATE stats_summary SET stat_value = $upcoming_events WHERE stat_name = 'upcoming_events'");
$conn->query("UPDATE stats_summary SET stat_value = $free_events WHERE stat_name = 'free_events'");

$out['ok'] = true;
$out['stats'] = array(
    'total_events' => $total_events,
    'total_pulls' => $total_pulls,
    'upcoming_events' => $upcoming_events,
    'free_events' => $free_events
);

echo json_encode($out, JSON_PRETTY_PRINT);
$conn->close();
?>
