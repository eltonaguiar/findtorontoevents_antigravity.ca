<?php
/**
 * Odds API proxy + lm_sports_odds read/write.
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/sports_db.php';
require_once dirname(__FILE__) . '/odds_api_fetch.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'get';

function sports_odds_key_ok($k) {
    // Resolve admin key. 50webs shared hosting cannot set custom PHP env vars
    // (getenv returns false), so we accept three sources, in order:
    //   1. getenv('ADMIN_API_KEY')   — works in CI / self-hosted runners
    //   2. db_config.php $ADMIN_API_KEY var if present
    //   3. hardcoded constant below — matches the value baked into every
    //      scraper (live-monitor/*_odds_scraper.py, multi_source_odds_fallback.py
    //      and the sports-betting-refresh.yml workflow).
    $expected = getenv('ADMIN_API_KEY');
    if ($expected === false || $expected === '') {
        // db_config.php may define $ADMIN_API_KEY; pull it into local scope.
        global $ADMIN_API_KEY;
        if (isset($ADMIN_API_KEY) && $ADMIN_API_KEY !== '') {
            $expected = $ADMIN_API_KEY;
        }
    }
    if ($expected === false || $expected === '') {
        $expected = 'livetrader2026'; // hardcoded fallback for 50webs shared host
    }
    return ($k === $expected);
}

/** The Odds API uses string team names; normalize if an object/array ever appears. PHP 5.2. */
function sports_odds_norm_team($t) {
    if (is_array($t)) {
        if (isset($t['name'])) {
            return (string) $t['name'];
        }
        if (isset($t['title'])) {
            return (string) $t['title'];
        }
        return '';
    }
    if ($t === null) {
        return '';
    }
    return (string) $t;
}

$SPORT_TARGETS = array(
    array('key' => 'basketball_nba', 'short' => 'NBA', 'title' => 'NBA'),
    array('key' => 'basketball_wnba', 'short' => 'WNBA', 'title' => 'WNBA'),
    array('key' => 'basketball_ncaab', 'short' => 'NCAAB', 'title' => 'NCAAB'),
    array('key' => 'icehockey_nhl', 'short' => 'NHL', 'title' => 'NHL'),
    array('key' => 'americanfootball_nfl', 'short' => 'NFL', 'title' => 'NFL'),
    array('key' => 'baseball_mlb', 'short' => 'MLB', 'title' => 'MLB'),
    array('key' => 'soccer_usa_mls', 'short' => 'MLS', 'title' => 'MLS'),
    array('key' => 'americanfootball_cfl', 'short' => 'CFL', 'title' => 'CFL'),
    array('key' => 'americanfootball_ncaaf', 'short' => 'NCAAF', 'title' => 'NCAAF'),
    array('key' => 'soccer_epl', 'short' => 'EPL', 'title' => 'English Premier League'),
    array('key' => 'soccer_spain_la_liga', 'short' => 'La Liga', 'title' => 'La Liga'),
    array('key' => 'tennis_atp', 'short' => 'ATP', 'title' => 'ATP Tennis'),
    array('key' => 'tennis_wta', 'short' => 'WTA', 'title' => 'WTA Tennis'),
);

function sports_odds_ca_flag($bookKey) {
    $k = strtolower($bookKey);
    $ca = array('fanduel', 'draftkings', 'betmgm', 'betrivers', 'espnbet', 'pinnacle', 'coolbet', 'betway', 'unibet', 'ballybet', 'leovegas', 'thescore');
    for ($i = 0; $i < count($ca); $i++) {
        if (strpos($k, $ca[$i]) !== false) {
            return true;
        }
    }
    return false;
}

if ($action === 'sports') {
    $active = array();
    for ($i = 0; $i < count($SPORT_TARGETS); $i++) {
        $active[] = array('short_name' => $SPORT_TARGETS[$i]['short'], 'title' => $SPORT_TARGETS[$i]['title']);
    }
    echo json_encode(array('ok' => true, 'active_sports' => $active, 'all_target' => count($SPORT_TARGETS)));
    $sports_mysqli->close();
    exit;
}

if ($action === 'credit_usage') {
    $lim = 500;
    $used = 0;
    $r = $sports_mysqli->query("SELECT COALESCE(SUM(credits_used),0) AS u FROM lm_sports_credit_usage WHERE request_time >= DATE_FORMAT(NOW(), '%Y-%m-01 00:00:00')");
    if ($r && ($row = $r->fetch_assoc())) {
        $used = intval($row['u']);
    }
    $rem = $lim - $used;
    if ($rem < 0) {
        $rem = 0;
    }
    $lastRem = null;
    $r2 = $sports_mysqli->query("SELECT credits_remaining FROM lm_sports_credit_usage ORDER BY id DESC LIMIT 1");
    if ($r2 && ($row2 = $r2->fetch_assoc()) && $row2['credits_remaining'] !== null) {
        $lastRem = intval($row2['credits_remaining']);
    }
    echo json_encode(array(
        'ok' => true,
        'monthly_used' => $used,
        'monthly_limit' => $lim,
        'monthly_remaining' => $rem,
        'credits_remaining' => $lastRem,
        'pct_used' => ($lim > 0) ? round(100.0 * $used / $lim, 1) : 0,
    ));
    $sports_mysqli->close();
    exit;
}

if ($action === 'get') {
    $hours = isset($_GET['hours']) ? intval($_GET['hours']) : 48;
    if ($hours < 1) {
        $hours = 48;
    }
    if ($hours > 168) {
        $hours = 168;
    }
    $sportFilter = isset($_GET['sport']) ? $_GET['sport'] : 'all';
    $cut = time() + $hours * 3600;
    $where = "commence_time <= FROM_UNIXTIME(" . intval($cut) . ") AND commence_time >= NOW()";
    if ($sportFilter !== '' && $sportFilter !== 'all') {
        $sp = $sports_mysqli->real_escape_string(strtolower($sportFilter));
        if ($sportFilter === 'NBA') {
            $where .= " AND sport LIKE '%basketball_nba%'";
        } else if ($sportFilter === 'NHL') {
            $where .= " AND sport LIKE '%icehockey_nhl%'";
        } else if ($sportFilter === 'NFL') {
            $where .= " AND sport LIKE '%americanfootball_nfl%'";
        } else if ($sportFilter === 'MLB') {
            $where .= " AND sport LIKE '%baseball_mlb%'";
        } else if ($sportFilter === 'MLS') {
            $where .= " AND sport LIKE '%soccer_usa_mls%'";
        } else if ($sportFilter === 'NCAAB') {
            $where .= " AND sport LIKE '%basketball_ncaab%'";
        } else if ($sportFilter === 'WNBA') {
            $where .= " AND sport LIKE '%basketball_wnba%'";
        } else {
            $where .= " AND sport = '" . $sp . "'";
        }
    }

    $r = $sports_mysqli->query("SELECT * FROM lm_sports_odds WHERE " . $where . " ORDER BY commence_time ASC LIMIT 8000");
    $byEvent = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $eid = $row['event_id'];
            if (!isset($byEvent[$eid])) {
                $byEvent[$eid] = array(
                    'event_id' => $eid,
                    'sport' => $row['sport'],
                    'sport_short' => '',
                    'home_team' => $row['home_team'],
                    'away_team' => $row['away_team'],
                    'commence_time' => $row['commence_time'],
                    'game_date' => substr($row['commence_time'], 0, 10),
                    'bookmakers' => array(),
                );
            }
            $bk = $row['bookmaker_key'];
            if (!isset($byEvent[$eid]['bookmakers'][$bk])) {
                $byEvent[$eid]['bookmakers'][$bk] = array(
                    'key' => $bk,
                    'name' => $row['bookmaker'],
                    'is_canadian' => sports_odds_ca_flag($bk),
                    'markets' => array(),
                );
            }
            $mkey = $row['market'];
            if (!isset($byEvent[$eid]['bookmakers'][$bk]['markets'][$mkey])) {
                $byEvent[$eid]['bookmakers'][$bk]['markets'][$mkey] = array('key' => $mkey, 'outcomes' => array());
            }
            $byEvent[$eid]['bookmakers'][$bk]['markets'][$mkey]['outcomes'][] = array(
                'name' => $row['outcome_name'],
                'price' => floatval($row['outcome_price']),
                'point' => $row['outcome_point'],
            );
        }
    }

    $events = array();
    foreach ($byEvent as $eid => $ev) {
        $bks = array();
        foreach ($ev['bookmakers'] as $bk => $bm) {
            $mkts = array();
            foreach ($bm['markets'] as $mk => $m) {
                $mkts[] = $m;
            }
            $bm['markets'] = $mkts;
            $bks[] = $bm;
        }
        $ev['bookmakers'] = $bks;
        $events[] = $ev;
    }

    echo json_encode(array('ok' => true, 'events' => $events));
    $sports_mysqli->close();
    exit;
}

if ($action === 'inject_fallback') {
    // Accepts JSON body: {"rows": [...]} where each row matches lm_sports_odds columns.
    // Used by live-monitor/nhl_nba_odds_fallback.py to insert ESPN-derived fair-odds
    // estimates when The Odds API returns sparse data for NBA/NHL.
    if (!sports_odds_key_ok(isset($_GET['key']) ? $_GET['key'] : '')) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        $sports_mysqli->close();
        exit;
    }
    $raw = file_get_contents('php://input');
    $payload = @json_decode($raw, true);
    $rows = (isset($payload['rows']) && is_array($payload['rows'])) ? $payload['rows'] : array();
    if (count($rows) === 0) {
        echo json_encode(array('ok' => false, 'error' => 'no rows'));
        $sports_mysqli->close();
        exit;
    }
    $inserted = 0;
    $skipped  = 0;
    foreach ($rows as $row) {
        $eid   = $sports_mysqli->real_escape_string(isset($row['event_id'])    ? $row['event_id']    : '');
        $sport = $sports_mysqli->real_escape_string(isset($row['sport'])       ? $row['sport']       : '');
        $bk    = $sports_mysqli->real_escape_string(isset($row['bookmaker'])   ? $row['bookmaker']   : '');
        $mkey  = $sports_mysqli->real_escape_string(isset($row['market'])      ? $row['market']      : 'h2h');
        $oname = $sports_mysqli->real_escape_string(isset($row['outcome_name'])? $row['outcome_name']: '');
        $price = floatval(isset($row['outcome_price']) ? $row['outcome_price'] : 0);
        $home  = $sports_mysqli->real_escape_string(isset($row['home_team'])   ? $row['home_team']   : '');
        $away  = $sports_mysqli->real_escape_string(isset($row['away_team'])   ? $row['away_team']   : '');
        $ct    = $sports_mysqli->real_escape_string(isset($row['commence_time'])? $row['commence_time']: '');
        if ($eid === '' || $sport === '' || $price <= 0) { $skipped++; continue; }
        // INSERT IGNORE is idempotent and race-condition-safe — no pre-check SELECT
        // needed (that SELECT-then-INSERT had a TOCTOU race between concurrent calls).
        // Duplicate-key collisions are silently skipped, counted as skipped.
        $ok = $sports_mysqli->query("INSERT IGNORE INTO lm_sports_odds (sport, event_id, home_team, away_team, commence_time, bookmaker, bookmaker_key, market, outcome_name, outcome_price) VALUES ('".$sport."','".$eid."','".$home."','".$away."','".$ct."','".$bk."','".$bk."','".$mkey."','".$oname."','".floatval($price)."')");
        if ($ok) { $inserted++; } else { $skipped++; }
    }
    echo json_encode(array('ok' => true, 'inserted' => $inserted, 'skipped' => $skipped));
    $sports_mysqli->close();
    exit;
}

if ($action === 'fetch') {
    if (!sports_odds_key_ok(isset($_GET['key']) ? $_GET['key'] : '')) {
        echo json_encode(array('ok' => false, 'error' => 'unauthorized'));
        $sports_mysqli->close();
        exit;
    }

    require_once dirname(__FILE__) . '/db_config.php';
    $apiKey = isset($THE_ODDS_API_KEY) ? $THE_ODDS_API_KEY : '';
    $secondaryApiKey = isset($ODDS_API_IO_KEY) ? $ODDS_API_IO_KEY : '';
    if ($apiKey === '' && $secondaryApiKey === '') {
        echo json_encode(array('ok' => false, 'error' => 'missing THE_ODDS_API_KEY and ODDS_API_IO_KEY'));
        $sports_mysqli->close();
        exit;
    }

    $preCu = $sports_mysqli->query("SELECT COALESCE(SUM(credits_used),0) AS u FROM lm_sports_credit_usage WHERE request_time >= DATE_FORMAT(NOW(), '%Y-%m-01 00:00:00')");
    $preUsed = 0;
    if ($preCu && ($preRow = $preCu->fetch_assoc())) {
        $preUsed = intval($preRow['u']);
    }
    $preRem = 500 - $preUsed;
    if ($preRem <= 20) {
        echo json_encode(array(
            'ok' => false,
            'error' => 'monthly_budget_exhausted',
            'monthly_used' => $preUsed,
            'monthly_limit' => 500,
            'monthly_remaining' => ($preRem > 0 ? $preRem : 0),
            'hint' => 'Budget buffer (20 credits) reached; fetch skipped. Resets on 1st of month.',
        ));
        $sports_mysqli->close();
        exit;
    }

    $budget = isset($_GET['budget_safe']) ? true : false;
    $indices = array();
    $budgetRotationGroup = null;
    if ($budget) {
        $dayRuns = 0;
        $rSlot = $sports_mysqli->query("SELECT COUNT(*) AS c FROM lm_sports_credit_usage WHERE request_time >= CURDATE()");
        if ($rSlot && ($row = $rSlot->fetch_assoc())) {
            $dayRuns = intval($row['c']);
        }
        // Always include NBA + NHL so core markets get odds every run; rotate the other two slots (4 credits).
        $slot = $dayRuns % 3;
        if ($slot === 0) {
            $indices = array(0, 2, 1, 3);  // NBA, NHL, NCAAB, NFL
        } else if ($slot === 1) {
            $indices = array(0, 2, 4, 5);  // NBA, NHL, MLB, MLS
        } else {
            $indices = array(0, 2, 6, 7);  // NBA, NHL, CFL, NCAAF
        }
        $budgetRotationGroup = $slot;
    } else {
        for ($ij = 0; $ij < count($SPORT_TARGETS); $ij++) {
            $indices[] = $ij;
        }
    }

    $rowsTotal = 0;
    $eventsCached = 0;
    $details = array();
    $creditsThisRun = 0;

    for ($ii = 0; $ii < count($indices); $ii++) {
        $si = $indices[$ii];
        $sk = $SPORT_TARGETS[$si]['key'];
        $fr = odds_api_get_events_with_failover($sk, $apiKey, $secondaryApiKey);
        $data = isset($fr['events']) ? $fr['events'] : array();

        if (!is_array($data) || count($data) === 0) {
            $details[] = array(
                'short_name' => $SPORT_TARGETS[$si]['short'],
                'events' => 0,
                'odds_rows' => 0,
                'error' => (isset($fr['errors']) && count($fr['errors']) > 0) ? implode('|', $fr['errors']) : 'no_events',
                'source' => isset($fr['source']) ? $fr['source'] : 'none',
                'url' => isset($fr['url_used']) ? $fr['url_used'] : '',
                'candidates_tried' => isset($fr['candidates_tried']) ? $fr['candidates_tried'] : 0,
            );
            continue;
        }

        $eventsCached += count($data);
        $rowsSport = 0;
        if (isset($fr['credits_charged']) && $fr['credits_charged']) {
            $creditsThisRun += 1;
        }

        // Clear upcoming rows for this sport BEFORE insert. Only do this when we
        // actually have events — if The Odds API returned 0 (budget rotation gap,
        // API outage, or sport was skipped), the existing rows are still valid and
        // should not be wiped. Previously we DELETE'd unconditionally, which left
        // the table empty for sports that The Odds API skipped that rotation slot.
        $skEsc = $sports_mysqli->real_escape_string($sk);
        if (is_array($data) && count($data) > 0) {
            $sports_mysqli->query("DELETE FROM lm_sports_odds WHERE sport = '" . $skEsc . "' AND commence_time >= NOW()");
        } else {
            // No new events from The Odds API this slot. Keep existing rows.
            // This prevents the table going empty when a sport is skipped in
            // the budget rotation. The existing rows remain queryable.
            $details[] = array(
                'short_name' => $SPORT_TARGETS[$si]['short'],
                'events' => 0,
                'odds_rows' => 0,
                'source' => 'skipped_no_events',
                'note' => 'No events returned (budget rotation gap or API outage). Existing rows preserved.',
            );
            continue;
        }

        $insertFailures = 0;
        $firstSqlError = '';
        for ($ei = 0; $ei < count($data); $ei++) {
            $ev = $data[$ei];
            $eid = isset($ev['id']) ? $ev['id'] : '';
            $ht = sports_odds_norm_team(isset($ev['home_team']) ? $ev['home_team'] : '');
            $at = sports_odds_norm_team(isset($ev['away_team']) ? $ev['away_team'] : '');
            $ct = isset($ev['commence_time']) ? $ev['commence_time'] : '';
            $ctSql = str_replace('T', ' ', substr($ct, 0, 19));
            $bms = isset($ev['bookmakers']) ? $ev['bookmakers'] : array();
            for ($bi = 0; $bi < count($bms); $bi++) {
                $bm = $bms[$bi];
                $bkey = isset($bm['key']) ? $bm['key'] : '';
                $bname = isset($bm['title']) ? $bm['title'] : $bkey;
                $mkts = isset($bm['markets']) ? $bm['markets'] : array();
                for ($mi = 0; $mi < count($mkts); $mi++) {
                    $m = $mkts[$mi];
                    $mkey = isset($m['key']) ? $m['key'] : '';
                    $ocs = isset($m['outcomes']) ? $m['outcomes'] : array();
                    for ($oi = 0; $oi < count($ocs); $oi++) {
                        $oc = $ocs[$oi];
                        $on = isset($oc['name']) ? $oc['name'] : '';
                        if (is_array($on)) {
                            if (isset($on['name'])) {
                                $on = (string) $on['name'];
                            } else {
                                $on = '';
                            }
                        }
                        $pr = isset($oc['price']) ? floatval($oc['price']) : 0;
                        $pt = null;
                        if (isset($oc['point'])) {
                            $pt = floatval($oc['point']);
                        }
                        // INSERT IGNORE is idempotent — safe against concurrent cron overlaps
                        // and duplicate keys from overlapping fetch runs. Duplicates are
                        // silently skipped (no MySQL error), which is the correct behaviour.
                        $ins = "INSERT IGNORE INTO lm_sports_odds (sport, event_id, home_team, away_team, commence_time, bookmaker, bookmaker_key, market, outcome_name, outcome_price, outcome_point, last_updated) VALUES ('"
                            . $sports_mysqli->real_escape_string($sk) . "','"
                            . $sports_mysqli->real_escape_string($eid) . "','"
                            . $sports_mysqli->real_escape_string($ht) . "','"
                            . $sports_mysqli->real_escape_string($at) . "','"
                            . $sports_mysqli->real_escape_string($ctSql) . "','"
                            . $sports_mysqli->real_escape_string($bname) . "','"
                            . $sports_mysqli->real_escape_string($bkey) . "','"
                            . $sports_mysqli->real_escape_string($mkey) . "','"
                            . $sports_mysqli->real_escape_string($on) . "',"
                            . $pr . ",";
                        if ($pt === null) {
                            $ins .= "NULL,NOW())";
                        } else {
                            $ins .= $pt . ",NOW())";
                        }
                        $ok = $sports_mysqli->query($ins);
                        if ($ok) {
                            $rowsSport++;
                            // Mercury feedback PR 1 — Phase 1 item 1: rolling odds history.
                            // Always append a snapshot row even if the lm_sports_odds row was
                            // a duplicate-ignore: the history table is append-only and has its
                            // own AUTO_INCREMENT id, so duplicates here are expected.
                            // Failures are silent — never block the primary write path.
                            $hist = "INSERT INTO lm_sports_odds_history (sport, event_id, home_team, away_team, commence_time, bookmaker, bookmaker_key, market, outcome_name, outcome_price, outcome_point, last_updated, snapshot_at) VALUES ('"
                                . $sports_mysqli->real_escape_string($sk) . "','"
                                . $sports_mysqli->real_escape_string($eid) . "','"
                                . $sports_mysqli->real_escape_string($ht) . "','"
                                . $sports_mysqli->real_escape_string($at) . "','"
                                . $sports_mysqli->real_escape_string($ctSql) . "','"
                                . $sports_mysqli->real_escape_string($bname) . "','"
                                . $sports_mysqli->real_escape_string($bkey) . "','"
                                . $sports_mysqli->real_escape_string($mkey) . "','"
                                . $sports_mysqli->real_escape_string($on) . "',"
                                . $pr . ",";
                            if ($pt === null) {
                                $hist .= "NULL,NOW(),NOW())";
                            } else {
                                $hist .= $pt . ",NOW(),NOW())";
                            }
                            @$sports_mysqli->query($hist);
                        } else {
                            $err = $sports_mysqli->error;
                            // INSERT IGNORE returns false only on real errors (not dup keys).
                            // Duplicate-key is silent in IGNORE mode — not counted as failure.
                            if (strpos($err, 'Duplicate entry') === false) {
                                $insertFailures++;
                                if ($firstSqlError === '') { $firstSqlError = $err; }
                            }
                        }
                    }
                }
            }
        }

        $rowsTotal += $rowsSport;

        if (isset($fr['credits_charged']) && $fr['credits_charged']) {
            $cu = $sports_mysqli->query("SELECT COALESCE(SUM(credits_used),0) AS u FROM lm_sports_credit_usage WHERE request_time >= DATE_FORMAT(NOW(), '%Y-%m-01 00:00:00')");
            $monthSoFar = 0;
            if ($cu && ($crow = $cu->fetch_assoc())) {
                $monthSoFar = intval($crow['u']);
            }
            $newMonthTotal = $monthSoFar + 1;
            $remAfter = 500 - $newMonthTotal;
            if ($remAfter < 0) {
                $remAfter = 0;
            }
            $sports_mysqli->query("INSERT INTO lm_sports_credit_usage (request_time, sport, credits_used, credits_remaining) VALUES (NOW(), '" . $sports_mysqli->real_escape_string($sk) . "', 1, " . intval($remAfter) . ")");
        }

        $drow = array(
            'short_name' => $SPORT_TARGETS[$si]['short'],
            'events' => count($data),
            'odds_rows' => $rowsSport,
            'source' => isset($fr['source']) ? $fr['source'] : 'unknown',
            'region_profile' => isset($fr['region_profile']) ? $fr['region_profile'] : '',
            'url' => isset($fr['url_used']) ? $fr['url_used'] : '',
            'candidates_tried' => isset($fr['candidates_tried']) ? $fr['candidates_tried'] : 0,
            'fallback_errors' => isset($fr['errors']) ? $fr['errors'] : array(),
        );
        if ($insertFailures > 0) {
            $drow['insert_failures'] = $insertFailures;
        }
        if ($firstSqlError !== '') {
            $drow['first_mysql_error'] = $firstSqlError;
        }
        if ($rowsSport === 0 && count($data) > 0) {
            $bms0 = isset($data[0]['bookmakers']) ? $data[0]['bookmakers'] : array();
            $drow['first_event_bookmakers'] = is_array($bms0) ? count($bms0) : 0;
        }
        $details[] = $drow;
    }

    $cu2 = $sports_mysqli->query("SELECT COALESCE(SUM(credits_used),0) AS u FROM lm_sports_credit_usage WHERE request_time >= DATE_FORMAT(NOW(), '%Y-%m-01 00:00:00')");
    $monthUsed = 0;
    if ($cu2 && ($cr2 = $cu2->fetch_assoc())) {
        $monthUsed = intval($cr2['u']);
    }
    $monthRem = 500 - $monthUsed;
    if ($monthRem < 0) {
        $monthRem = 0;
    }
    $lr = $sports_mysqli->query("SELECT credits_remaining FROM lm_sports_credit_usage ORDER BY id DESC LIMIT 1");
    $creditsRem = $monthRem;
    if ($lr && ($lrow = $lr->fetch_assoc()) && $lrow['credits_remaining'] !== null) {
        $creditsRem = intval($lrow['credits_remaining']);
    }

    $outFetch = array(
        'ok' => true,
        'sports_fetched' => count($indices),
        'events_cached' => $eventsCached,
        'odds_rows' => $rowsTotal,
        'credits_used' => $creditsThisRun,
        'credits_remaining' => $creditsRem,
        'monthly_used' => $monthUsed,
        'monthly_remaining' => $monthRem,
        'sport_details' => $details,
    );
    if ($budgetRotationGroup !== null) {
        $outFetch['budget_rotation_group'] = $budgetRotationGroup;
        $outFetch['budget_indices'] = $indices;
    }

    echo json_encode($outFetch);
    $sports_mysqli->close();
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'unknown action'));
$sports_mysqli->close();
