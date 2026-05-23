<?php
/**
 * Steam-moves read endpoint — Mercury feedback PR 1.
 * Returns recent rows from lm_sports_steam_moves for the UI tab.
 *
 * GET /live-monitor/api/sports_steam.php?hours=24&sport=basketball_nba
 *
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/sports_db.php';

$hours = isset($_GET['hours']) ? intval($_GET['hours']) : 24;
if ($hours < 1) { $hours = 24; }
if ($hours > 168) { $hours = 168; }

$sport = isset($_GET['sport']) ? trim($_GET['sport']) : '';
$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 200;
if ($limit < 1) { $limit = 200; }
if ($limit > 1000) { $limit = 1000; }

$where = "detected_at >= NOW() - INTERVAL " . intval($hours) . " HOUR";
if ($sport !== '' && $sport !== 'all') {
    $sp = $sports_mysqli->real_escape_string($sport);
    $where .= " AND sport = '" . $sp . "'";
}

$sql = "SELECT id, event_id, sport, home_team, away_team, commence_time, market, outcome_name, direction, books_moved, magnitude, window_minutes, books_json, detected_at "
     . "FROM lm_sports_steam_moves WHERE " . $where
     . " ORDER BY detected_at DESC LIMIT " . intval($limit);

$rows = array();
$r = $sports_mysqli->query($sql);
if ($r) {
    while ($row = $r->fetch_assoc()) {
        $bj = $row['books_json'];
        $books = null;
        if ($bj !== null && $bj !== '') {
            $books = json_decode($bj, true);
        }
        $rows[] = array(
            'id' => intval($row['id']),
            'event_id' => $row['event_id'],
            'sport' => $row['sport'],
            'home_team' => $row['home_team'],
            'away_team' => $row['away_team'],
            'commence_time' => $row['commence_time'],
            'market' => $row['market'],
            'outcome_name' => $row['outcome_name'],
            'direction' => $row['direction'],
            'books_moved' => intval($row['books_moved']),
            'magnitude' => floatval($row['magnitude']),
            'window_minutes' => intval($row['window_minutes']),
            'books' => $books,
            'detected_at' => $row['detected_at'],
        );
    }
}

echo json_encode(array(
    'ok' => true,
    'count' => count($rows),
    'hours' => $hours,
    'sport' => $sport,
    'rows' => $rows,
));
$sports_mysqli->close();
