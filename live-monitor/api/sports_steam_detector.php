<?php
/**
 * Steam-move detector — Mercury feedback PR 1 (Phase 1 item 2).
 *
 * Scans the last `window_minutes` of lm_sports_odds_history per
 * (event_id, market, outcome_name) and flags coordinated line moves where
 * >=`min_books` distinct bookmakers shifted price the same direction by at
 * least `min_magnitude` (decimal-odds units; for spread/total markets we
 * compare outcome_point shifts in the same way).
 *
 * Writes one row to lm_sports_steam_moves per detection.
 *
 * CLI usage (cron, every minute on a paid Odds API tier; every 5 min on free):
 *   php /path/to/sports_steam_detector.php [--window=15] [--min-books=3]
 *                                          [--min-magnitude=0.05] [--key=...]
 *
 * Web usage is gated on a shared key (action=run&key=livetrader2026) so the
 * job can be invoked by the failover cron without exposing it to scrapers.
 *
 * PHP 5.2 compatible.
 */

require_once dirname(__FILE__) . '/sports_db.php';

function ssd_arg($argv, $name, $default) {
    if (!is_array($argv)) {
        return $default;
    }
    for ($i = 1; $i < count($argv); $i++) {
        $a = $argv[$i];
        if (strpos($a, '--' . $name . '=') === 0) {
            return substr($a, strlen('--' . $name . '='));
        }
    }
    return $default;
}

function ssd_param($name, $default) {
    if (isset($_GET[$name])) {
        return $_GET[$name];
    }
    return $default;
}

function ssd_is_cli() {
    return (php_sapi_name() === 'cli');
}

$isCli = ssd_is_cli();

if ($isCli) {
    $windowMin    = intval(ssd_arg($argv, 'window', '15'));
    $minBooks     = intval(ssd_arg($argv, 'min-books', '3'));
    $minMagnitude = floatval(ssd_arg($argv, 'min-magnitude', '0.05'));
} else {
    $key = ssd_param('key', '');
    $_ssd_admin_key = getenv('ADMIN_API_KEY');
    if ($_ssd_admin_key === false || $_ssd_admin_key === '' || $key !== $_ssd_admin_key) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        exit;
    }
    $windowMin    = intval(ssd_param('window', 15));
    $minBooks     = intval(ssd_param('min_books', 3));
    $minMagnitude = floatval(ssd_param('min_magnitude', 0.05));
}

if ($windowMin < 1) { $windowMin = 15; }
if ($windowMin > 240) { $windowMin = 240; }
if ($minBooks < 2) { $minBooks = 3; }
if ($minMagnitude < 0.001) { $minMagnitude = 0.05; }

$detected = 0;
$inspected = 0;
$now = date('Y-m-d H:i:s');

// Pull last 2 * windowMin worth of history. We need an "early" snapshot
// (older than windowMin) to compare against the latest snapshot per book.
$lookback = 2 * $windowMin;
$sql = "SELECT event_id, sport, home_team, away_team, commence_time, bookmaker, bookmaker_key, market, outcome_name, outcome_price, outcome_point, snapshot_at "
     . "FROM lm_sports_odds_history "
     . "WHERE snapshot_at >= NOW() - INTERVAL " . intval($lookback) . " MINUTE "
     . "  AND commence_time >= NOW() - INTERVAL 6 HOUR "
     . "ORDER BY event_id, market, outcome_name, bookmaker_key, snapshot_at ASC";
$r = $sports_mysqli->query($sql);
if (!$r) {
    $msg = 'history query failed: ' . $sports_mysqli->error;
    if ($isCli) { fwrite(STDERR, $msg . "\n"); exit(1); }
    echo json_encode(array('ok' => false, 'error' => $msg));
    exit;
}

// Group by (event_id, market, outcome_name) — for each group we look at every
// book, and for each book we compare the earliest "old" snapshot (snapshot_at
// older than now-windowMin) to the latest "new" snapshot. A book "moved" iff
// the price (or point, for spreads/totals) shifted by >= minMagnitude in a
// consistent direction.
$buckets = array();
$cutoff = time() - ($windowMin * 60);
while ($row = $r->fetch_assoc()) {
    $inspected++;
    $key = $row['event_id'] . '|' . $row['market'] . '|' . $row['outcome_name'];
    if (!isset($buckets[$key])) {
        $buckets[$key] = array(
            'event_id' => $row['event_id'],
            'sport' => $row['sport'],
            'home_team' => $row['home_team'],
            'away_team' => $row['away_team'],
            'commence_time' => $row['commence_time'],
            'market' => $row['market'],
            'outcome_name' => $row['outcome_name'],
            'books' => array(),
        );
    }
    $bk = $row['bookmaker_key'] !== '' ? $row['bookmaker_key'] : $row['bookmaker'];
    if (!isset($buckets[$key]['books'][$bk])) {
        $buckets[$key]['books'][$bk] = array('book_name' => $row['bookmaker'], 'old' => null, 'new' => null);
    }
    $snapTs = strtotime($row['snapshot_at']);
    $sample = array('price' => floatval($row['outcome_price']), 'point' => $row['outcome_point'] === null ? null : floatval($row['outcome_point']), 'ts' => $snapTs);
    if ($snapTs <= $cutoff) {
        // older sample — keep the most recent "old" sample
        if ($buckets[$key]['books'][$bk]['old'] === null || $snapTs > $buckets[$key]['books'][$bk]['old']['ts']) {
            $buckets[$key]['books'][$bk]['old'] = $sample;
        }
    } else {
        // newer sample — always overwrite (we want the freshest)
        $buckets[$key]['books'][$bk]['new'] = $sample;
    }
}

foreach ($buckets as $bk_key => $b) {
    $marketIsLineBased = ($b['market'] === 'spreads' || $b['market'] === 'totals');
    $up = 0; $down = 0;
    $magUp = 0.0; $magDown = 0.0;
    $movedBooks = array();
    foreach ($b['books'] as $bookKey => $samples) {
        if ($samples['old'] === null || $samples['new'] === null) {
            continue;
        }
        if ($marketIsLineBased && $samples['old']['point'] !== null && $samples['new']['point'] !== null) {
            $delta = $samples['new']['point'] - $samples['old']['point'];
            // For totals/spreads, magnitude threshold is in points (default 0.5
            // when minMagnitude is the price-default 0.05 we map it up).
            $thresh = max($minMagnitude, 0.5);
            if ($delta >= $thresh) {
                $up++; $magUp += $delta; $movedBooks[] = array('book' => $bookKey, 'name' => $samples['book_name'], 'delta' => $delta, 'unit' => 'pts');
            } else if ($delta <= -$thresh) {
                $down++; $magDown += abs($delta); $movedBooks[] = array('book' => $bookKey, 'name' => $samples['book_name'], 'delta' => $delta, 'unit' => 'pts');
            }
        } else {
            $delta = $samples['new']['price'] - $samples['old']['price'];
            if ($delta >= $minMagnitude) {
                $up++; $magUp += $delta; $movedBooks[] = array('book' => $bookKey, 'name' => $samples['book_name'], 'delta' => $delta, 'unit' => 'odds');
            } else if ($delta <= -$minMagnitude) {
                $down++; $magDown += abs($delta); $movedBooks[] = array('book' => $bookKey, 'name' => $samples['book_name'], 'delta' => $delta, 'unit' => 'odds');
            }
        }
    }
    $direction = '';
    $count = 0;
    $magSum = 0.0;
    if ($up >= $minBooks && $up > $down) {
        $direction = 'up'; $count = $up; $magSum = $magUp;
    } else if ($down >= $minBooks && $down > $up) {
        $direction = 'down'; $count = $down; $magSum = $magDown;
    } else {
        continue;
    }
    $avgMag = ($count > 0) ? ($magSum / $count) : 0.0;

    // Suppress duplicates: if we already wrote a steam_move for this
    // (event_id, market, outcome_name, direction) within the last windowMin,
    // skip. This prevents the cron from re-firing on the same group every run.
    $eidEsc = $sports_mysqli->real_escape_string($b['event_id']);
    $mEsc = $sports_mysqli->real_escape_string($b['market']);
    $onEsc = $sports_mysqli->real_escape_string($b['outcome_name']);
    $dirEsc = $sports_mysqli->real_escape_string($direction);
    $dq = $sports_mysqli->query("SELECT id FROM lm_sports_steam_moves WHERE event_id='" . $eidEsc . "' AND market='" . $mEsc . "' AND outcome_name='" . $onEsc . "' AND direction='" . $dirEsc . "' AND detected_at >= NOW() - INTERVAL " . intval($windowMin) . " MINUTE LIMIT 1");
    if ($dq && $dq->num_rows > 0) {
        continue;
    }

    $booksJson = $sports_mysqli->real_escape_string(json_encode(array_values($movedBooks)));
    $sportEsc = $sports_mysqli->real_escape_string($b['sport']);
    $homeEsc = $sports_mysqli->real_escape_string($b['home_team']);
    $awayEsc = $sports_mysqli->real_escape_string($b['away_team']);
    $ctEsc = $sports_mysqli->real_escape_string($b['commence_time']);

    $insSql = "INSERT INTO lm_sports_steam_moves (event_id, sport, home_team, away_team, commence_time, market, outcome_name, direction, books_moved, magnitude, window_minutes, books_json, detected_at) VALUES ('"
        . $eidEsc . "','" . $sportEsc . "','" . $homeEsc . "','" . $awayEsc . "','" . $ctEsc . "','"
        . $mEsc . "','" . $onEsc . "','" . $dirEsc . "',"
        . intval($count) . "," . sprintf('%.4f', $avgMag) . "," . intval($windowMin) . ",'"
        . $booksJson . "',NOW())";
    if ($sports_mysqli->query($insSql)) {
        $detected++;
    }
}

$out = array(
    'ok' => true,
    'inspected' => $inspected,
    'detected' => $detected,
    'window_minutes' => $windowMin,
    'min_books' => $minBooks,
    'min_magnitude' => $minMagnitude,
    'run_at' => $now,
);
if ($isCli) {
    echo json_encode($out) . "\n";
} else {
    echo json_encode($out);
}
$sports_mysqli->close();
