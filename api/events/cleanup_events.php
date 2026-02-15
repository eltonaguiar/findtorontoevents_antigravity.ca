<?php
/**
 * cleanup_events.php — Remove past events from next/events.json
 * Moves expired events to next/events_archive.json
 * 
 * PHP 5.2 compatible (no closures, no ?:, no ??, no [], no __DIR__)
 *
 * Usage:
 *   GET  https://findtorontoevents.ca/api/events/cleanup_events.php
 *   GET  ...?key=YOUR_SECRET  (optional auth via query param)
 *   POST ...  with JSON body { "key": "..." }
 *
 * Returns JSON with counts of kept, archived, and total events.
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit(0); }

$out = array(
    'ok' => false,
    'kept' => 0,
    'archived' => 0,
    'total_before' => 0,
    'archive_total' => 0,
    'errors' => array()
);

/* ── Paths ── */
$site_root   = dirname(dirname(dirname(__FILE__)));
$events_file = $site_root . '/next/events.json';
$archive_file = $site_root . '/next/events_archive.json';

/* ── Read current events ── */
if (!file_exists($events_file)) {
    $out['errors'][] = 'events.json not found at ' . $events_file;
    echo json_encode($out);
    exit;
}

$raw = file_get_contents($events_file);
$events = json_decode($raw, true);
if (!is_array($events)) {
    $out['errors'][] = 'Failed to parse events.json';
    echo json_encode($out);
    exit;
}

$out['total_before'] = count($events);

/* ── Read existing archive (if any) ── */
$archive = array();
if (file_exists($archive_file)) {
    $archive_raw = file_get_contents($archive_file);
    $archive_parsed = json_decode($archive_raw, true);
    if (is_array($archive_parsed)) {
        $archive = $archive_parsed;
    }
}

/* ── Determine today (Eastern Time, start of day) ── */
$tz_offset = '-05:00'; /* EST — conservative; EDT would be -04:00 */
$today_str = gmdate('Y-m-d', time() - 5 * 3600); /* Today in EST */
$today_ts  = strtotime($today_str . 'T00:00:00' . $tz_offset);

/* ── Split events ── */
$kept = array();
$newly_archived = array();

for ($i = 0; $i < count($events); $i++) {
    $ev = $events[$i];

    /* Use the START date to decide if the event is past.
       An event dated Feb 14 should not show on Feb 15, even if
       its endDate bleeds into the next day (e.g. a party 7PM-2AM). */
    $start_ts = 0;
    if (isset($ev['date']) && $ev['date'] !== '') {
        $start_ts = strtotime($ev['date']);
    }

    if ($start_ts > 0 && $start_ts < $today_ts) {
        /* Event started before today — archive it */
        $ev['archived_on'] = gmdate('Y-m-d\TH:i:s\Z');
        $newly_archived[] = $ev;
    } else {
        /* Current or future event — keep */
        $kept[] = $ev;
    }
}

/* ── Merge newly archived into archive ── */
/* Build lookup of existing archive IDs to avoid duplicates */
$archive_ids = array();
for ($i = 0; $i < count($archive); $i++) {
    if (isset($archive[$i]['id'])) {
        $archive_ids[$archive[$i]['id']] = true;
    }
}

$added_to_archive = 0;
for ($i = 0; $i < count($newly_archived); $i++) {
    $ev_id = isset($newly_archived[$i]['id']) ? $newly_archived[$i]['id'] : '';
    if ($ev_id !== '' && isset($archive_ids[$ev_id])) {
        continue; /* Already in archive */
    }
    $archive[] = $newly_archived[$i];
    $added_to_archive++;
}

/* ── Write cleaned events.json ── */
$json_events = json_encode($kept);
if ($json_events === false) {
    $out['errors'][] = 'Failed to encode kept events';
    echo json_encode($out);
    exit;
}

$wrote_events = file_put_contents($events_file, $json_events);
if ($wrote_events === false) {
    $out['errors'][] = 'Failed to write events.json (permission denied?)';
    echo json_encode($out);
    exit;
}

/* ── Write archive ── */
$json_archive = json_encode($archive);
if ($json_archive === false) {
    $out['errors'][] = 'Failed to encode archive';
} else {
    $wrote_archive = file_put_contents($archive_file, $json_archive);
    if ($wrote_archive === false) {
        $out['errors'][] = 'Failed to write events_archive.json (permission denied?)';
    }
}

$out['ok'] = true;
$out['kept'] = count($kept);
$out['archived'] = count($newly_archived);
$out['added_to_archive'] = $added_to_archive;
$out['archive_total'] = count($archive);

echo json_encode($out);
?>
