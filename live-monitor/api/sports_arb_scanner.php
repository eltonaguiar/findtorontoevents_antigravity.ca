<?php
/**
 * Arbitrage scanner — Mercury feedback PR 1 (Phase 1 item 3).
 *
 * Iterates the latest lm_sports_odds rows per (event_id, market, point) and
 * emits two-leg arbitrage opportunities where:
 *   1/leg_a_odds + 1/leg_b_odds < 1.0 - fees_pct
 *
 * Writes each opportunity to lm_sports_arbs (status='open'). Existing open
 * rows whose underlying line moved out of arbitrage are marked status='closed'.
 *
 * Reuses sports_value_quote_usable() from sports_value_analyze_lib.php to
 * filter out exchange/outlier prices that would produce false positives.
 *
 * CLI usage:
 *   php /path/to/sports_arb_scanner.php [--fees-pct=0.005] [--min-edge=0.005]
 *
 * Web usage:
 *   GET /live-monitor/api/sports_arb_scanner.php?action=run&key=livetrader2026
 *
 * PHP 5.2 compatible.
 */

require_once dirname(__FILE__) . '/sports_db.php';
require_once dirname(__FILE__) . '/sports_value_analyze_lib.php';

function sas_arg($argv, $name, $default) {
    if (!is_array($argv)) { return $default; }
    for ($i = 1; $i < count($argv); $i++) {
        $a = $argv[$i];
        if (strpos($a, '--' . $name . '=') === 0) {
            return substr($a, strlen('--' . $name . '='));
        }
    }
    return $default;
}

function sas_param($name, $default) {
    return isset($_GET[$name]) ? $_GET[$name] : $default;
}

$isCli = (php_sapi_name() === 'cli');
if ($isCli) {
    $feesPct = floatval(sas_arg($argv, 'fees-pct', '0.005'));
    $minEdge = floatval(sas_arg($argv, 'min-edge', '0.005'));
} else {
    $_sas_admin_key = getenv('ADMIN_API_KEY');
    if ($_sas_admin_key === false || $_sas_admin_key === '' || sas_param('key', '') !== $_sas_admin_key) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        exit;
    }
    $feesPct = floatval(sas_param('fees_pct', 0.005));
    $minEdge = floatval(sas_param('min_edge', 0.005));
}
if ($feesPct < 0) { $feesPct = 0.005; }
if ($feesPct > 0.1) { $feesPct = 0.1; }
if ($minEdge < 0) { $minEdge = 0.005; }
if ($minEdge > 0.5) { $minEdge = 0.5; }

// Pull current upcoming odds across all books/markets. Only look at events
// commencing in the next 7 days to bound the scan.
$sql = "SELECT event_id, sport, home_team, away_team, commence_time, bookmaker, bookmaker_key, market, outcome_name, outcome_price, outcome_point "
     . "FROM lm_sports_odds "
     . "WHERE commence_time >= NOW() AND commence_time <= NOW() + INTERVAL 7 DAY "
     . "ORDER BY event_id, market, outcome_point, outcome_name";

$r = $sports_mysqli->query($sql);
if (!$r) {
    $msg = 'odds query failed: ' . $sports_mysqli->error;
    if ($isCli) { fwrite(STDERR, $msg . "\n"); exit(1); }
    echo json_encode(array('ok' => false, 'error' => $msg)); exit;
}

// Group: (event_id, market, point) -> outcome_name -> list of {book, key, price}
$groups = array();
$evMeta = array();
while ($row = $r->fetch_assoc()) {
    $eid = $row['event_id'];
    $market = $row['market'];
    if ($market !== 'h2h' && $market !== 'spreads' && $market !== 'totals') {
        continue;
    }
    $price = floatval($row['outcome_price']);
    $bk = $row['bookmaker_key'] !== '' ? $row['bookmaker_key'] : $row['bookmaker'];
    if (!sports_value_quote_usable($bk, $price)) {
        continue;
    }
    $point = $row['outcome_point'];
    $pointKey = ($point === null || $point === '') ? '' : sprintf('%.2f', floatval($point));
    // For spreads, the two legs sit on opposite signed points (+3.5 vs -3.5) but
    // we want them matched. Group by absolute point and let the outcome_name
    // disambiguate.
    if ($market === 'spreads' && $pointKey !== '') {
        $pointKey = sprintf('%.2f', abs(floatval($point)));
    }
    $gkey = $eid . '|' . $market . '|' . $pointKey;
    if (!isset($groups[$gkey])) {
        $groups[$gkey] = array();
        $evMeta[$gkey] = array(
            'event_id' => $eid,
            'sport' => $row['sport'],
            'home_team' => $row['home_team'],
            'away_team' => $row['away_team'],
            'commence_time' => $row['commence_time'],
            'market' => $market,
            'point' => ($point === null || $point === '') ? null : floatval($point),
        );
    }
    $on = $row['outcome_name'];
    if (!isset($groups[$gkey][$on])) {
        $groups[$gkey][$on] = array();
    }
    $groups[$gkey][$on][] = array(
        'book' => $row['bookmaker'],
        'book_key' => $bk,
        'price' => $price,
        'point' => ($point === null || $point === '') ? null : floatval($point),
    );
}

$emitted = 0;
$inspected = 0;
$openIdsKept = array();

foreach ($groups as $gkey => $outcomes) {
    $inspected++;
    $names = array_keys($outcomes);
    if (count($names) < 2) { continue; }
    // Best price per outcome
    $best = array();
    foreach ($outcomes as $on => $quotes) {
        $bestQ = null;
        for ($i = 0; $i < count($quotes); $i++) {
            if ($bestQ === null || $quotes[$i]['price'] > $bestQ['price']) {
                $bestQ = $quotes[$i];
            }
        }
        if ($bestQ !== null) { $best[$on] = $bestQ; }
    }
    // For h2h with a draw outcome (3-way soccer), arb requires all 3 legs.
    // For now scan only 2-way pairs; 3-way handled as TODO.
    if (count($best) < 2) { continue; }

    // Try every 2-outcome pair
    $ks = array_keys($best);
    for ($a = 0; $a < count($ks); $a++) {
        for ($b = $a + 1; $b < count($ks); $b++) {
            $aQ = $best[$ks[$a]];
            $bQ = $best[$ks[$b]];
            // Don't pair the same book on both legs unless we have to.
            if ($aQ['book_key'] === $bQ['book_key']) { continue; }
            // For totals (Over/Under) pair only Over vs Under
            $meta = $evMeta[$gkey];
            if ($meta['market'] === 'totals') {
                $a_lc = strtolower($ks[$a]);
                $b_lc = strtolower($ks[$b]);
                $aOver = (strpos($a_lc, 'over') !== false);
                $bOver = (strpos($b_lc, 'over') !== false);
                if ($aOver === $bOver) { continue; }
            }
            $invSum = (1.0 / $aQ['price']) + (1.0 / $bQ['price']);
            if ($invSum >= 1.0) { continue; }
            $grossSpread = 1.0 - $invSum;
            $netEdge = $grossSpread - $feesPct;
            if ($netEdge < $minEdge) { continue; }

            $eventId = $sports_mysqli->real_escape_string($meta['event_id']);
            $marketEsc = $sports_mysqli->real_escape_string($meta['market']);
            $aOn = $sports_mysqli->real_escape_string($ks[$a]);
            $bOn = $sports_mysqli->real_escape_string($ks[$b]);
            $aBk = $sports_mysqli->real_escape_string($aQ['book']);
            $aBkK = $sports_mysqli->real_escape_string($aQ['book_key']);
            $bBk = $sports_mysqli->real_escape_string($bQ['book']);
            $bBkK = $sports_mysqli->real_escape_string($bQ['book_key']);

            // Check if we already have an open arb for this (event, market, point, leg-a-book, leg-b-book) pair —
            // if so, just refresh detected_at and net_edge_pct (and keep the original id alive). Otherwise insert new.
            $pointWhere = ($meta['point'] === null) ? "AND point IS NULL" : ("AND ABS(COALESCE(point,0) - " . sprintf('%.2f', $meta['point']) . ") < 0.001");
            $existing = $sports_mysqli->query("SELECT id FROM lm_sports_arbs WHERE event_id='" . $eventId . "' AND market='" . $marketEsc . "' " . $pointWhere
                . " AND leg_a_book_key='" . $aBkK . "' AND leg_b_book_key='" . $bBkK . "' AND status='open' LIMIT 1");
            if ($existing && $existing->num_rows > 0) {
                $erow = $existing->fetch_assoc();
                $sports_mysqli->query("UPDATE lm_sports_arbs SET leg_a_odds=" . sprintf('%.4f', $aQ['price'])
                    . ", leg_b_odds=" . sprintf('%.4f', $bQ['price'])
                    . ", gross_spread=" . sprintf('%.4f', $grossSpread)
                    . ", net_edge_pct=" . sprintf('%.4f', $netEdge)
                    . ", detected_at=NOW() WHERE id=" . intval($erow['id']));
                $openIdsKept[intval($erow['id'])] = true;
                continue;
            }

            $sportEsc = $sports_mysqli->real_escape_string($meta['sport']);
            $homeEsc = $sports_mysqli->real_escape_string($meta['home_team']);
            $awayEsc = $sports_mysqli->real_escape_string($meta['away_team']);
            $ctEsc = $sports_mysqli->real_escape_string($meta['commence_time']);
            $pointSql = ($meta['point'] === null) ? 'NULL' : sprintf('%.2f', $meta['point']);

            $ins = "INSERT INTO lm_sports_arbs (event_id, sport, home_team, away_team, commence_time, market, point, leg_a_outcome, leg_a_book, leg_a_book_key, leg_a_odds, leg_b_outcome, leg_b_book, leg_b_book_key, leg_b_odds, gross_spread, fees_pct, net_edge_pct, source, status, detected_at) VALUES ('"
                . $eventId . "','" . $sportEsc . "','" . $homeEsc . "','" . $awayEsc . "','" . $ctEsc . "','"
                . $marketEsc . "'," . $pointSql . ",'"
                . $aOn . "','" . $aBk . "','" . $aBkK . "'," . sprintf('%.4f', $aQ['price']) . ",'"
                . $bOn . "','" . $bBk . "','" . $bBkK . "'," . sprintf('%.4f', $bQ['price']) . ","
                . sprintf('%.4f', $grossSpread) . "," . sprintf('%.4f', $feesPct) . "," . sprintf('%.4f', $netEdge)
                . ",'odds_api','open',NOW())";
            if ($sports_mysqli->query($ins)) {
                $emitted++;
                $openIdsKept[$sports_mysqli->insert_id] = true;
            }
        }
    }
}

// Close open arbs that no longer appear in this scan (line moved out).
$closed = 0;
$openR = $sports_mysqli->query("SELECT id FROM lm_sports_arbs WHERE status='open' AND source='odds_api' AND detected_at < NOW() - INTERVAL 5 MINUTE");
if ($openR) {
    $stale = array();
    while ($row = $openR->fetch_assoc()) {
        if (!isset($openIdsKept[intval($row['id'])])) {
            $stale[] = intval($row['id']);
        }
    }
    if (count($stale) > 0) {
        $sports_mysqli->query("UPDATE lm_sports_arbs SET status='closed', closed_at=NOW() WHERE id IN (" . implode(',', $stale) . ")");
        $closed = count($stale);
    }
}

$out = array(
    'ok' => true,
    'inspected_groups' => $inspected,
    'emitted' => $emitted,
    'closed' => $closed,
    'fees_pct' => $feesPct,
    'min_edge' => $minEdge,
    'run_at' => date('Y-m-d H:i:s'),
);
echo json_encode($out);
if ($isCli) { echo "\n"; }
$sports_mysqli->close();
