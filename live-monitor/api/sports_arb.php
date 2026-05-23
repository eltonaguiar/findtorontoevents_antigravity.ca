<?php
/**
 * Arbitrage opportunities read endpoint — Mercury feedback PR 1.
 * GET /live-monitor/api/sports_arb.php?status=open&hours=48&sport=...
 *
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/sports_db.php';

$status = isset($_GET['status']) ? trim($_GET['status']) : 'open';
if ($status !== 'open' && $status !== 'closed' && $status !== 'all' && $status !== 'taken') {
    $status = 'open';
}
$hours = isset($_GET['hours']) ? intval($_GET['hours']) : 48;
if ($hours < 1) { $hours = 48; }
if ($hours > 720) { $hours = 720; }
$sport = isset($_GET['sport']) ? trim($_GET['sport']) : '';
$limit = isset($_GET['limit']) ? intval($_GET['limit']) : 200;
if ($limit < 1) { $limit = 200; }
if ($limit > 1000) { $limit = 1000; }

$where = "detected_at >= NOW() - INTERVAL " . intval($hours) . " HOUR";
if ($status !== 'all') {
    $where .= " AND status='" . $sports_mysqli->real_escape_string($status) . "'";
}
if ($sport !== '' && $sport !== 'all') {
    $where .= " AND sport='" . $sports_mysqli->real_escape_string($sport) . "'";
}

$sql = "SELECT id, event_id, sport, home_team, away_team, commence_time, market, point, "
     . "leg_a_outcome, leg_a_book, leg_a_book_key, leg_a_odds, "
     . "leg_b_outcome, leg_b_book, leg_b_book_key, leg_b_odds, "
     . "gross_spread, fees_pct, net_edge_pct, source, status, detected_at, closed_at "
     . "FROM lm_sports_arbs WHERE " . $where
     . " ORDER BY (status='open') DESC, net_edge_pct DESC, detected_at DESC LIMIT " . intval($limit);

$rows = array();
$r = $sports_mysqli->query($sql);
if ($r) {
    while ($row = $r->fetch_assoc()) {
        // Compute suggested stake split for a $100 bankroll: leg_a_share = (1/oddsA) / invSum.
        $oa = floatval($row['leg_a_odds']);
        $ob = floatval($row['leg_b_odds']);
        $invSum = ($oa > 1 && $ob > 1) ? (1.0/$oa + 1.0/$ob) : 0;
        $aSharePct = ($invSum > 0) ? ((1.0/$oa) / $invSum) * 100.0 : 0;
        $bSharePct = ($invSum > 0) ? ((1.0/$ob) / $invSum) * 100.0 : 0;
        $rows[] = array(
            'id' => intval($row['id']),
            'event_id' => $row['event_id'],
            'sport' => $row['sport'],
            'home_team' => $row['home_team'],
            'away_team' => $row['away_team'],
            'commence_time' => $row['commence_time'],
            'market' => $row['market'],
            'point' => $row['point'] === null ? null : floatval($row['point']),
            'leg_a' => array(
                'outcome' => $row['leg_a_outcome'],
                'book' => $row['leg_a_book'],
                'book_key' => $row['leg_a_book_key'],
                'odds' => floatval($row['leg_a_odds']),
                'stake_share_pct' => round($aSharePct, 2),
            ),
            'leg_b' => array(
                'outcome' => $row['leg_b_outcome'],
                'book' => $row['leg_b_book'],
                'book_key' => $row['leg_b_book_key'],
                'odds' => floatval($row['leg_b_odds']),
                'stake_share_pct' => round($bSharePct, 2),
            ),
            'gross_spread' => floatval($row['gross_spread']),
            'fees_pct' => floatval($row['fees_pct']),
            'net_edge_pct' => floatval($row['net_edge_pct']),
            'source' => $row['source'],
            'status' => $row['status'],
            'detected_at' => $row['detected_at'],
            'closed_at' => $row['closed_at'],
        );
    }
}

echo json_encode(array(
    'ok' => true,
    'count' => count($rows),
    'status' => $status,
    'hours' => $hours,
    'sport' => $sport,
    'rows' => $rows,
));
$sports_mysqli->close();
