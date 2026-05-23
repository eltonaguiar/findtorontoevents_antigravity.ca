<?php
/**
 * The Odds API (v4) — shared HTTP and fetch helpers for live-monitor sports.
 * Use this instead of raw file_get_contents so transient TLS/DNS blips and
 * allow_url_fopen quirks can fall back to cURL (when available).
 * Optional region-taper: only runs extra HTTP attempts when the prior attempt
 * returns no body (connection/empty failure), to reduce load on quota.
 * PHP 5.2 compatible.
 */

/**
 * GET a URL, preferring cURL when the extension is available.
 * Returns response body on any HTTP code with a non-empty body (callers parse JSON).
 * Returns false on hard transport failure.
 *
 * @param string $url
 * @return string|false
 */
function odds_api_http_get($url) {
    if (function_exists('curl_init')) {
        $ch = curl_init();
        if ($ch) {
            curl_setopt($ch, CURLOPT_URL, $url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 25);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_USERAGENT, 'FindTorontoEvents/1.0 (live-monitor; odds v4; findtorontoevents.ca)');
            $resp = curl_exec($ch);
            curl_close($ch);
            if ($resp !== false && $resp !== '') {
                return $resp;
            }
        }
    }
    $ctx = stream_context_create(array('http' => array(
        'timeout' => 25,
        'user_agent' => 'FindTorontoEvents/1.0 (live-monitor; odds v4; findtorontoevents.ca)',
    )));
    $r = @file_get_contents($url, false, $ctx);
    if ($r !== false && $r !== '') {
        return $r;
    }
    return false;
}

/**
 * Build candidate Odds /odds/ URLs: full regions, then us+us2, then us.
 * Stops on first non-empty response.
 *
 * @param string $sk Odds API sport key (e.g. basketball_nba)
 * @param string $apiKey
 * @return array with keys: raw, url_used, candidates_tried, region_profile
 */
/**
 * True if JSON body from /v4/sports/.../odds has at least one event with bookmakers.
 */
function odds_api_v4_response_has_any_bookmakers($raw) {
    if ($raw === false || $raw === '') {
        return false;
    }
    $data = json_decode($raw, true);
    if (is_array($data) && isset($data['data']) && is_array($data['data'])) {
        $data = $data['data'];
    }
    if (!is_array($data) || count($data) < 1) {
        return false;
    }
    for ($i = 0; $i < count($data); $i++) {
        $ev = $data[$i];
        if (!is_array($ev)) {
            continue;
        }
        $bks = isset($ev['bookmakers']) ? $ev['bookmakers'] : array();
        if (is_array($bks) && count($bks) > 0) {
            return true;
        }
    }
    return false;
}

function odds_api_v4_get_odds_raw($sk, $apiKey) {
    $out = array(
        'raw' => false,
        'url_used' => '',
        'candidates_tried' => 0,
        'region_profile' => '',
    );
    $apiEsc = urlencode($apiKey);
    $path = 'https://api.the-odds-api.com/v4/sports/' . $sk . '/odds/?regions=';
    $tail = '&markets=h2h,spreads,totals&oddsFormat=decimal&apiKey=' . $apiEsc;
    $regionSets = array('us,us2,uk,eu', 'us,us2', 'us', 'au', 'eu', 'uk');
    $lastRaw = false;
    for ($i = 0; $i < count($regionSets); $i++) {
        $url = $path . $regionSets[$i] . $tail;
        $out['candidates_tried'] = $i + 1;
        $out['url_used'] = $url;
        $raw = odds_api_http_get($url);
        if ($raw !== false && $raw !== '') {
            if (odds_api_v4_response_has_any_bookmakers($raw)) {
                $out['raw'] = $raw;
                $out['region_profile'] = $regionSets[$i];
                return $out;
            }
            $lastRaw = $raw;
        }
    }
    if ($lastRaw !== false) {
        $out['raw'] = $lastRaw;
        $out['region_profile'] = 'empty_bookmakers';
    }
    return $out;
}

/**
 * Same as odds_api_v4_get_odds_raw but retries with multiple API keys.
 *
 * @param string $sk
 * @param array $apiKeys
 * @return array
 */
function odds_api_v4_get_odds_raw_multi_key($sk, $apiKeys) {
    $out = array(
        'raw' => false,
        'url_used' => '',
        'candidates_tried' => 0,
        'region_profile' => '',
        'key_index_used' => -1,
    );
    for ($ki = 0; $ki < count($apiKeys); $ki++) {
        $k = isset($apiKeys[$ki]) ? trim($apiKeys[$ki]) : '';
        if ($k === '') {
            continue;
        }
        $res = odds_api_v4_get_odds_raw($sk, $k);
        $out['candidates_tried'] += intval($res['candidates_tried']);
        if ($res['raw'] !== false && $res['raw'] !== '') {
            $res['key_index_used'] = $ki;
            $res['candidates_tried'] = $out['candidates_tried'];
            return $res;
        }
        $out['url_used'] = $res['url_used'];
    }
    return $out;
}

function odds_api_espn_sport_path($sk) {
    if ($sk === 'basketball_nba') {
        return 'basketball/nba';
    }
    if ($sk === 'basketball_ncaab') {
        return 'basketball/mens-college-basketball';
    }
    if ($sk === 'icehockey_nhl') {
        return 'hockey/nhl';
    }
    if ($sk === 'americanfootball_nfl') {
        return 'football/nfl';
    }
    if ($sk === 'americanfootball_ncaaf') {
        return 'football/college-football';
    }
    if ($sk === 'baseball_mlb') {
        return 'baseball/mlb';
    }
    if ($sk === 'soccer_usa_mls') {
        return 'soccer/usa.1';
    }
    if ($sk === 'americanfootball_cfl') {
        return 'football/cfl';
    }
    return '';
}

function odds_api_american_to_decimal($v) {
    $a = floatval($v);
    if ($a === 0.0) {
        return 0;
    }
    if ($a > 0) {
        return round(1.0 + ($a / 100.0), 4);
    }
    return round(1.0 + (100.0 / abs($a)), 4);
}

/**
 * Pluck an American odds value (e.g. "+102", "-110") from a nested ESPN odds node.
 * Prefers close line, falls back to open line.
 * Returns '' if nothing usable found.
 */
function odds_api_espn_pluck_american($side) {
    if (!is_array($side)) {
        return '';
    }
    if (isset($side['close']) && is_array($side['close']) && isset($side['close']['odds'])) {
        return (string) $side['close']['odds'];
    }
    if (isset($side['open']) && is_array($side['open']) && isset($side['open']['odds'])) {
        return (string) $side['open']['odds'];
    }
    if (isset($side['odds'])) {
        return (string) $side['odds'];
    }
    return '';
}

/**
 * Pluck the spread line (e.g. "-1.5") from a nested ESPN pointSpread node.
 */
function odds_api_espn_pluck_spread_line($side) {
    if (!is_array($side)) {
        return null;
    }
    if (isset($side['close']) && is_array($side['close']) && isset($side['close']['line'])) {
        return $side['close']['line'];
    }
    if (isset($side['open']) && is_array($side['open']) && isset($side['open']['line'])) {
        return $side['open']['line'];
    }
    if (isset($side['line'])) {
        return $side['line'];
    }
    return null;
}

function odds_api_events_from_espn($sk, &$urlUsed, &$error) {
    $path = odds_api_espn_sport_path($sk);
    if ($path === '') {
        $error = 'espn_unsupported_sport';
        return array();
    }
    $url = 'https://site.api.espn.com/apis/site/v2/sports/' . $path . '/scoreboard';
    $urlUsed = $url;
    $raw = odds_api_http_get($url);
    if ($raw === false || $raw === '') {
        $error = 'espn_http_fail';
        return array();
    }
    $json = json_decode($raw, true);
    if (!is_array($json) || !isset($json['events']) || !is_array($json['events'])) {
        $error = 'espn_json_fail';
        return array();
    }

    $events = array();
    for ($i = 0; $i < count($json['events']); $i++) {
        $ev = $json['events'][$i];
        $competition = (isset($ev['competitions'][0]) && is_array($ev['competitions'][0])) ? $ev['competitions'][0] : array();
        $competitors = isset($competition['competitors']) ? $competition['competitors'] : array();

        $homeTeam = '';
        $awayTeam = '';
        for ($c = 0; $c < count($competitors); $c++) {
            $side = isset($competitors[$c]['homeAway']) ? $competitors[$c]['homeAway'] : '';
            $name = isset($competitors[$c]['team']['displayName']) ? $competitors[$c]['team']['displayName'] : '';
            if ($side === 'home') {
                $homeTeam = $name;
            } else if ($side === 'away') {
                $awayTeam = $name;
            }
        }
        if ($homeTeam === '' || $awayTeam === '') {
            continue;
        }

        // ESPN publishes odds at competitions[0].odds[], NOT events[].odds[].
        // The old parser read the wrong path and produced 0 events for every sport.
        $oddsList = isset($competition['odds']) && is_array($competition['odds']) ? $competition['odds'] : array();
        if (count($oddsList) === 0 && isset($ev['odds']) && is_array($ev['odds'])) {
            // Legacy path kept as last-resort fallback.
            $oddsList = $ev['odds'];
        }
        $odds0 = (isset($oddsList[0]) && is_array($oddsList[0])) ? $oddsList[0] : array();
        $providerName = 'ESPN API';
        if (isset($odds0['provider']['name']) && is_string($odds0['provider']['name'])) {
            $providerName = 'ESPN: ' . $odds0['provider']['name'];
        }

        $markets = array();

        // --- h2h (moneyline) from nested moneyline.home.close.odds / moneyline.away.close.odds
        $h2h = array();
        if (isset($odds0['moneyline']) && is_array($odds0['moneyline'])) {
            $mlHomeAm = isset($odds0['moneyline']['home']) ? odds_api_espn_pluck_american($odds0['moneyline']['home']) : '';
            $mlAwayAm = isset($odds0['moneyline']['away']) ? odds_api_espn_pluck_american($odds0['moneyline']['away']) : '';
            if ($mlHomeAm !== '' && $mlAwayAm !== '') {
                $homeDec = odds_api_american_to_decimal($mlHomeAm);
                $awayDec = odds_api_american_to_decimal($mlAwayAm);
                if ($homeDec > 1.0 && $awayDec > 1.0) {
                    $h2h[] = array('name' => $homeTeam, 'price' => $homeDec);
                    $h2h[] = array('name' => $awayTeam, 'price' => $awayDec);
                }
            }
        }
        if (count($h2h) > 0) {
            $markets[] = array('key' => 'h2h', 'outcomes' => $h2h);
        }

        // --- spreads from nested pointSpread.home.close.line + .odds (with opposite side)
        if (isset($odds0['pointSpread']) && is_array($odds0['pointSpread'])) {
            $psHome = isset($odds0['pointSpread']['home']) ? $odds0['pointSpread']['home'] : null;
            $psAway = isset($odds0['pointSpread']['away']) ? $odds0['pointSpread']['away'] : null;
            $lineHome = odds_api_espn_pluck_spread_line($psHome);
            $lineAway = odds_api_espn_pluck_spread_line($psAway);
            $oddsHomeAm = odds_api_espn_pluck_american($psHome);
            $oddsAwayAm = odds_api_espn_pluck_american($psAway);
            if ($lineHome !== null && is_numeric($lineHome) && $lineAway !== null && is_numeric($lineAway)) {
                $hDec = $oddsHomeAm !== '' ? odds_api_american_to_decimal($oddsHomeAm) : 1.91;
                $aDec = $oddsAwayAm !== '' ? odds_api_american_to_decimal($oddsAwayAm) : 1.91;
                if ($hDec <= 1.0) { $hDec = 1.91; }
                if ($aDec <= 1.0) { $aDec = 1.91; }
                $markets[] = array('key' => 'spreads', 'outcomes' => array(
                    array('name' => $homeTeam, 'price' => $hDec, 'point' => floatval($lineHome)),
                    array('name' => $awayTeam, 'price' => $aDec, 'point' => floatval($lineAway)),
                ));
            }
        }
        // Fallback: scalar spread + favorite flag on homeTeamOdds/awayTeamOdds (older ESPN shape).
        if (count($markets) < 2 && isset($odds0['spread']) && is_numeric($odds0['spread'])) {
            $sp = abs(floatval($odds0['spread']));
            $homeIsFav = false;
            if (isset($odds0['homeTeamOdds']['favorite']) && $odds0['homeTeamOdds']['favorite']) {
                $homeIsFav = true;
            }
            $homePt = $homeIsFav ? -$sp : $sp;
            $awayPt = $homeIsFav ? $sp : -$sp;
            $markets[] = array('key' => 'spreads', 'outcomes' => array(
                array('name' => $homeTeam, 'price' => 1.91, 'point' => $homePt),
                array('name' => $awayTeam, 'price' => 1.91, 'point' => $awayPt),
            ));
        }

        // --- totals: prefer nested total.over.close.odds / total.under.close.odds, else default -110 both sides
        if (isset($odds0['overUnder']) && is_numeric($odds0['overUnder'])) {
            $ou = floatval($odds0['overUnder']);
            $overDec = 1.91;
            $underDec = 1.91;
            if (isset($odds0['total']['over']) || isset($odds0['total']['under'])) {
                $ovAm = isset($odds0['total']['over']) ? odds_api_espn_pluck_american($odds0['total']['over']) : '';
                $unAm = isset($odds0['total']['under']) ? odds_api_espn_pluck_american($odds0['total']['under']) : '';
                if ($ovAm !== '') {
                    $d = odds_api_american_to_decimal($ovAm);
                    if ($d > 1.0) { $overDec = $d; }
                }
                if ($unAm !== '') {
                    $d = odds_api_american_to_decimal($unAm);
                    if ($d > 1.0) { $underDec = $d; }
                }
            }
            $markets[] = array('key' => 'totals', 'outcomes' => array(
                array('name' => 'Over', 'price' => $overDec, 'point' => $ou),
                array('name' => 'Under', 'price' => $underDec, 'point' => $ou),
            ));
        }

        if (count($markets) === 0) {
            continue;
        }

        $events[] = array(
            'id' => 'espn_' . (isset($ev['id']) ? $ev['id'] : md5($homeTeam . '_' . $awayTeam . '_' . $sk)),
            'home_team' => $homeTeam,
            'away_team' => $awayTeam,
            'commence_time' => isset($ev['date']) ? $ev['date'] : gmdate('c'),
            'bookmakers' => array(array(
                'key' => 'espn_api',
                'title' => $providerName,
                'markets' => $markets,
            )),
        );
    }

    if (count($events) === 0) {
        $error = 'espn_no_odds';
    }
    return $events;
}

function odds_api_events_from_nba_model(&$urlUsed, &$error) {
    $script = dirname(__FILE__) . '/../nba_odds_scraper.py';
    if (!file_exists($script)) {
        $error = 'nba_script_missing';
        return array();
    }
    $urlUsed = 'local_python_script';

    $cmd = 'python ' . escapeshellarg($script) . ' --predict 2>&1';
    $raw = @shell_exec($cmd);
    if ($raw === null || $raw === '') {
        $cmd2 = 'python3 ' . escapeshellarg($script) . ' --predict 2>&1';
        $raw = @shell_exec($cmd2);
    }
    if ($raw === null || $raw === '') {
        $error = 'nba_script_fail';
        return array();
    }

    $json = json_decode($raw, true);
    if (!is_array($json) || !isset($json['predictions']) || !is_array($json['predictions'])) {
        $error = 'nba_script_json_fail';
        return array();
    }

    $events = array();
    for ($i = 0; $i < count($json['predictions']); $i++) {
        $p = $json['predictions'][$i];
        $homeTeam = isset($p['home_team']) ? $p['home_team'] : '';
        $awayTeam = isset($p['away_team']) ? $p['away_team'] : '';
        $homeMl = isset($p['odds']['home_ml']) ? $p['odds']['home_ml'] : null;
        $awayMl = isset($p['odds']['away_ml']) ? $p['odds']['away_ml'] : null;
        $homeDec = ($homeMl !== null) ? odds_api_american_to_decimal($homeMl) : 0;
        $awayDec = ($awayMl !== null) ? odds_api_american_to_decimal($awayMl) : 0;
        if ($homeTeam === '' || $awayTeam === '' || $homeDec <= 0 || $awayDec <= 0) {
            continue;
        }
        $events[] = array(
            'id' => 'nba_model_' . (isset($p['game_id']) ? $p['game_id'] : md5($homeTeam . '_' . $awayTeam)),
            'home_team' => $homeTeam,
            'away_team' => $awayTeam,
            'commence_time' => isset($p['date']) ? $p['date'] : gmdate('c'),
            'bookmakers' => array(array(
                'key' => 'nba_model_fallback',
                'title' => 'NBA Model Fallback',
                'markets' => array(array(
                    'key' => 'h2h',
                    'outcomes' => array(
                        array('name' => $homeTeam, 'price' => $homeDec),
                        array('name' => $awayTeam, 'price' => $awayDec),
                    ),
                )),
            )),
        );
    }

    if (count($events) === 0) {
        $error = 'nba_script_no_events';
    }
    return $events;
}

/**
 * Bovada's public JSON catalog — no auth, returns real bookmaker prices for NBA/NHL.
 * Used as a second real-book source when The Odds API returns empty bookmakers
 * for playoff NBA/NHL (books post lines irregularly). Bovada's quotes qualify as
 * a normal bookmaker for consensus devig (unlike the ESPN synthetic fallback).
 */
function odds_api_bovada_sport_path($sk) {
    if ($sk === 'basketball_nba')       { return 'basketball/nba'; }
    if ($sk === 'icehockey_nhl')        { return 'hockey/nhl'; }
    if ($sk === 'americanfootball_nfl') { return 'football/nfl'; }
    if ($sk === 'baseball_mlb')         { return 'baseball/mlb'; }
    if ($sk === 'basketball_ncaab')     { return 'basketball/college-basketball'; }
    if ($sk === 'americanfootball_ncaaf') { return 'football/college-football'; }
    if ($sk === 'soccer_usa_mls')       { return 'soccer/mls'; }
    return '';
}

/**
 * Detect Bovada meta / prop-heading entries that leak into the catalog with
 * non-team competitor names (e.g. "Away Goals @ Home Goals", "Yes @ No").
 */
function odds_api_bovada_looks_like_prop_meta($home, $away) {
    $blocklist = array('goals', 'yes', 'no', 'over', 'under', 'odd', 'even');
    $sides = array(strtolower(trim($home)), strtolower(trim($away)));
    for ($i = 0; $i < count($sides); $i++) {
        $s = $sides[$i];
        if ($s === '') { return true; }
        $tokens = preg_split('/\s+/', $s);
        if (count($tokens) < 2) { return true; }
        for ($j = 0; $j < count($tokens); $j++) {
            if (in_array($tokens[$j], $blocklist, true)) { return true; }
        }
    }
    return false;
}

/**
 * Convert Bovada American-odds string like "-120", "+110", "EVEN" to decimal.
 */
function odds_api_bovada_american_to_decimal($v) {
    if ($v === null) { return 0; }
    $s = trim((string)$v);
    if ($s === '' || strtoupper($s) === 'EVEN') { return 2.00; }
    return odds_api_american_to_decimal($s);
}

function odds_api_events_from_bovada($sk, &$urlUsed, &$error) {
    $path = odds_api_bovada_sport_path($sk);
    if ($path === '') {
        $error = 'bovada_unsupported_sport';
        return array();
    }
    $url = 'https://www.bovada.lv/services/sports/event/v2/events/A/description/' . $path;
    $urlUsed = $url;

    // Bovada sometimes 403s on default UA; retry via a browser UA if cURL is available.
    $raw = odds_api_http_get($url);
    if (($raw === false || $raw === '') && function_exists('curl_init')) {
        $ch = curl_init();
        if ($ch) {
            curl_setopt($ch, CURLOPT_URL, $url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 20);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36');
            curl_setopt($ch, CURLOPT_HTTPHEADER, array('Accept: application/json, text/plain, */*', 'Accept-Language: en-US,en;q=0.9'));
            $raw = curl_exec($ch);
            curl_close($ch);
        }
    }
    if ($raw === false || $raw === '') {
        $error = 'bovada_http_fail';
        return array();
    }
    $json = json_decode($raw, true);
    if (!is_array($json) || count($json) === 0) {
        $error = 'bovada_json_fail';
        return array();
    }
    $container = $json[0];
    $evs = isset($container['events']) && is_array($container['events']) ? $container['events'] : array();

    $events = array();
    for ($i = 0; $i < count($evs); $i++) {
        $ev = $evs[$i];
        // Bovada description is "Away @ Home"; rely on competitors[] with home flag for accuracy.
        $comps = isset($ev['competitors']) && is_array($ev['competitors']) ? $ev['competitors'] : array();
        $homeTeam = '';
        $awayTeam = '';
        for ($c = 0; $c < count($comps); $c++) {
            $cmp = $comps[$c];
            $name = isset($cmp['name']) ? $cmp['name'] : '';
            $isHome = isset($cmp['home']) ? (bool)$cmp['home'] : false;
            if ($isHome) { $homeTeam = $name; } else { $awayTeam = $name; }
        }
        if ($homeTeam === '' || $awayTeam === '') { continue; }
        if (odds_api_bovada_looks_like_prop_meta($homeTeam, $awayTeam)) { continue; }

        // ISO commence_time from ms epoch
        $startMs = isset($ev['startTime']) ? intval($ev['startTime']) : 0;
        $ct = $startMs > 0 ? gmdate('c', intval($startMs / 1000)) : gmdate('c');

        // Bovada groups markets under displayGroups -> markets -> outcomes.
        // We only want Game Lines: Moneyline, Point Spread, Total (period="Game" or Match).
        $h2h = array();
        $spreadsHome = null; $spreadsAway = null;
        $spreadLineHome = null; $spreadLineAway = null;
        $totalPoint = null; $totalOver = null; $totalUnder = null;

        $groups = isset($ev['displayGroups']) && is_array($ev['displayGroups']) ? $ev['displayGroups'] : array();
        for ($g = 0; $g < count($groups); $g++) {
            $grp = $groups[$g];
            $grpDesc = strtolower(isset($grp['description']) ? $grp['description'] : '');
            if ($grpDesc !== 'game lines' && strpos($grpDesc, 'main') === false) { continue; }
            $mkts = isset($grp['markets']) ? $grp['markets'] : array();
            for ($m = 0; $m < count($mkts); $m++) {
                $mk = $mkts[$m];
                $mdesc = strtolower(isset($mk['description']) ? $mk['description'] : '');
                $pdesc = isset($mk['period']['description']) ? strtolower($mk['period']['description']) : '';
                // Only game/match period, not halves/quarters.
                if ($pdesc !== 'game' && $pdesc !== 'match' && $pdesc !== 'regulation' && $pdesc !== '') { continue; }
                $outs = isset($mk['outcomes']) ? $mk['outcomes'] : array();

                if (strpos($mdesc, 'moneyline') !== false && count($h2h) === 0) {
                    $tmp = array();
                    for ($o = 0; $o < count($outs); $o++) {
                        $oc = $outs[$o];
                        $ocName = isset($oc['description']) ? $oc['description'] : '';
                        $priceDec = 0;
                        if (isset($oc['price']['decimal'])) {
                            $priceDec = floatval($oc['price']['decimal']);
                        } else if (isset($oc['price']['american'])) {
                            $priceDec = odds_api_bovada_american_to_decimal($oc['price']['american']);
                        }
                        if ($priceDec > 1.0 && $ocName !== '') {
                            $tmp[] = array('name' => $ocName, 'price' => round($priceDec, 4));
                        }
                    }
                    if (count($tmp) >= 2) {
                        $h2h = $tmp;
                    }
                } else if (strpos($mdesc, 'point spread') !== false && $spreadsHome === null && $spreadsAway === null) {
                    for ($o = 0; $o < count($outs); $o++) {
                        $oc = $outs[$o];
                        $ocName = isset($oc['description']) ? $oc['description'] : '';
                        $priceDec = 0;
                        if (isset($oc['price']['decimal'])) {
                            $priceDec = floatval($oc['price']['decimal']);
                        } else if (isset($oc['price']['american'])) {
                            $priceDec = odds_api_bovada_american_to_decimal($oc['price']['american']);
                        }
                        $hcap = isset($oc['price']['handicap']) ? $oc['price']['handicap'] : null;
                        if (!is_numeric($hcap)) { continue; }
                        if ($ocName === $homeTeam) {
                            $spreadsHome = round($priceDec, 4);
                            $spreadLineHome = floatval($hcap);
                        } else if ($ocName === $awayTeam) {
                            $spreadsAway = round($priceDec, 4);
                            $spreadLineAway = floatval($hcap);
                        }
                    }
                } else if (strpos($mdesc, 'total') === 0 && $totalPoint === null) {
                    for ($o = 0; $o < count($outs); $o++) {
                        $oc = $outs[$o];
                        $ocName = strtolower(isset($oc['description']) ? $oc['description'] : '');
                        $priceDec = 0;
                        if (isset($oc['price']['decimal'])) {
                            $priceDec = floatval($oc['price']['decimal']);
                        } else if (isset($oc['price']['american'])) {
                            $priceDec = odds_api_bovada_american_to_decimal($oc['price']['american']);
                        }
                        $hcap = isset($oc['price']['handicap']) ? $oc['price']['handicap'] : null;
                        if (!is_numeric($hcap)) { continue; }
                        if (strpos($ocName, 'over') !== false) {
                            $totalOver = round($priceDec, 4);
                            $totalPoint = floatval($hcap);
                        } else if (strpos($ocName, 'under') !== false) {
                            $totalUnder = round($priceDec, 4);
                            if ($totalPoint === null) { $totalPoint = floatval($hcap); }
                        }
                    }
                }
            }
        }

        $markets = array();
        if (count($h2h) >= 2) {
            $markets[] = array('key' => 'h2h', 'outcomes' => $h2h);
        }
        if ($spreadsHome !== null && $spreadsAway !== null && $spreadLineHome !== null && $spreadLineAway !== null) {
            $markets[] = array('key' => 'spreads', 'outcomes' => array(
                array('name' => $homeTeam, 'price' => $spreadsHome, 'point' => $spreadLineHome),
                array('name' => $awayTeam, 'price' => $spreadsAway, 'point' => $spreadLineAway),
            ));
        }
        if ($totalPoint !== null && $totalOver !== null && $totalUnder !== null) {
            $markets[] = array('key' => 'totals', 'outcomes' => array(
                array('name' => 'Over',  'price' => $totalOver,  'point' => $totalPoint),
                array('name' => 'Under', 'price' => $totalUnder, 'point' => $totalPoint),
            ));
        }
        if (count($markets) === 0) { continue; }

        $events[] = array(
            'id' => 'bovada_' . (isset($ev['id']) ? $ev['id'] : md5($homeTeam . '_' . $awayTeam . '_' . $sk)),
            'home_team' => $homeTeam,
            'away_team' => $awayTeam,
            'commence_time' => $ct,
            'bookmakers' => array(array(
                'key' => 'bovada',
                'title' => 'Bovada',
                'markets' => $markets,
            )),
        );
    }

    if (count($events) === 0) {
        $error = 'bovada_no_odds';
    }
    return $events;
}

/**
 * Normalize a team name for cross-source matching (case, punctuation, whitespace).
 */
function odds_api_normalize_team_name($name) {
    $s = strtolower((string) $name);
    $s = preg_replace('/[^a-z0-9]+/', ' ', $s);
    $s = trim($s);
    return $s;
}

/**
 * Action Network's public scoreboard endpoint — no auth, aggregates 6+ real books
 * (FanDuel, BetMGM, Caesars, BetRivers, PointsBet, WynnBET, etc.) per game. This
 * is the consensus-diversity source: ESPN (Draft Kings) + Bovada alone price
 * similarly so the analyzer finds no edge. Action Network introduces the other
 * major US books with genuinely different lines, enabling real value-bet detection.
 */
function odds_api_action_network_sport_slug($sk) {
    if ($sk === 'basketball_nba')         { return 'nba'; }
    if ($sk === 'icehockey_nhl')          { return 'nhl'; }
    if ($sk === 'americanfootball_nfl')   { return 'nfl'; }
    if ($sk === 'baseball_mlb')           { return 'mlb'; }
    if ($sk === 'basketball_ncaab')       { return 'ncaab'; }
    if ($sk === 'americanfootball_ncaaf') { return 'ncaaf'; }
    return '';
}

function odds_api_action_network_book_name($bookId) {
    $bid = intval($bookId);
    if ($bid === 15)  { return array('key' => 'draftkings',   'title' => 'DraftKings'); }
    if ($bid === 30)  { return array('key' => 'fanduel',      'title' => 'FanDuel'); }
    if ($bid === 68)  { return array('key' => 'betmgm',       'title' => 'BetMGM'); }
    if ($bid === 69)  { return array('key' => 'caesars',      'title' => 'Caesars'); }
    if ($bid === 71)  { return array('key' => 'betrivers',    'title' => 'BetRivers'); }
    if ($bid === 75)  { return array('key' => 'pointsbet',    'title' => 'PointsBet'); }
    if ($bid === 76)  { return array('key' => 'wynnbet',      'title' => 'WynnBET'); }
    if ($bid === 79)  { return array('key' => 'wynnbet',      'title' => 'WynnBET'); }
    if ($bid === 21)  { return array('key' => 'williamhill',  'title' => 'William Hill'); }
    if ($bid === 59)  { return array('key' => 'fanatics',     'title' => 'Fanatics'); }
    if ($bid === 123) { return array('key' => 'unibet',       'title' => 'Unibet'); }
    if ($bid === 972) { return array('key' => 'espnbet',      'title' => 'ESPN BET'); }
    return array('key' => 'actionnet_' . $bid, 'title' => 'ActionNet ' . $bid);
}

function odds_api_events_from_action_network($sk, &$urlUsed, &$error) {
    $slug = odds_api_action_network_sport_slug($sk);
    if ($slug === '') {
        $error = 'actionnet_unsupported_sport';
        return array();
    }
    $bookIds = '30,68,69,71,75,79,123,972,59,21';
    $url = 'https://api.actionnetwork.com/web/v1/scoreboard/' . $slug . '?bookIds=' . $bookIds;
    $urlUsed = $url;
    $raw = odds_api_http_get($url);
    if (($raw === false || $raw === '') && function_exists('curl_init')) {
        $ch = curl_init();
        if ($ch) {
            curl_setopt($ch, CURLOPT_URL, $url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 20);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36');
            curl_setopt($ch, CURLOPT_HTTPHEADER, array('Accept: application/json, text/plain, */*'));
            $raw = curl_exec($ch);
            curl_close($ch);
        }
    }
    if ($raw === false || $raw === '') {
        $error = 'actionnet_http_fail';
        return array();
    }
    $json = json_decode($raw, true);
    if (!is_array($json) || !isset($json['games']) || !is_array($json['games'])) {
        $error = 'actionnet_json_fail';
        return array();
    }
    $events = array();
    for ($g = 0; $g < count($json['games']); $g++) {
        $game = $json['games'][$g];
        $homeId = isset($game['home_team_id']) ? intval($game['home_team_id']) : 0;
        $awayId = isset($game['away_team_id']) ? intval($game['away_team_id']) : 0;
        $teams  = isset($game['teams']) && is_array($game['teams']) ? $game['teams'] : array();
        $homeTeam = '';
        $awayTeam = '';
        for ($t = 0; $t < count($teams); $t++) {
            $tm = $teams[$t];
            $tid = isset($tm['id']) ? intval($tm['id']) : 0;
            $name = isset($tm['full_name']) ? $tm['full_name'] : (isset($tm['display_name']) ? $tm['display_name'] : '');
            if ($tid === $homeId) { $homeTeam = $name; }
            else if ($tid === $awayId) { $awayTeam = $name; }
        }
        if ($homeTeam === '' || $awayTeam === '') { continue; }
        $ct = isset($game['start_time']) ? $game['start_time'] : gmdate('c');
        $byBook = array();
        $oddsList = isset($game['odds']) && is_array($game['odds']) ? $game['odds'] : array();
        for ($oi = 0; $oi < count($oddsList); $oi++) {
            $row = $oddsList[$oi];
            if (isset($row['type']) && $row['type'] !== 'game') { continue; }
            $bid = isset($row['book_id']) ? intval($row['book_id']) : 0;
            if ($bid <= 0) { continue; }
            if (!isset($byBook[$bid])) { $byBook[$bid] = $row; }
        }
        $bookmakers = array();
        foreach ($byBook as $bid => $row) {
            $meta = odds_api_action_network_book_name($bid);
            $markets = array();
            $mlH = isset($row['ml_home']) ? $row['ml_home'] : null;
            $mlA = isset($row['ml_away']) ? $row['ml_away'] : null;
            if ($mlH !== null && $mlA !== null && is_numeric($mlH) && is_numeric($mlA)) {
                $homeDec = odds_api_american_to_decimal($mlH);
                $awayDec = odds_api_american_to_decimal($mlA);
                if ($homeDec > 1.0 && $awayDec > 1.0) {
                    $markets[] = array('key' => 'h2h', 'outcomes' => array(
                        array('name' => $homeTeam, 'price' => round($homeDec, 4)),
                        array('name' => $awayTeam, 'price' => round($awayDec, 4)),
                    ));
                }
            }
            // Action Network: spread_home = LINE (e.g. 1.5), spread_home_line = American ODDS (e.g. -112).
            $spLineH = isset($row['spread_home']) ? $row['spread_home'] : null;
            $spLineA = isset($row['spread_away']) ? $row['spread_away'] : null;
            $spOddsH = isset($row['spread_home_line']) ? $row['spread_home_line'] : null;
            $spOddsA = isset($row['spread_away_line']) ? $row['spread_away_line'] : null;
            if ($spLineH !== null && $spLineA !== null && $spOddsH !== null && $spOddsA !== null
                && is_numeric($spLineH) && is_numeric($spLineA) && is_numeric($spOddsH) && is_numeric($spOddsA)) {
                $hDec = odds_api_american_to_decimal($spOddsH);
                $aDec = odds_api_american_to_decimal($spOddsA);
                if ($hDec > 1.0 && $aDec > 1.0) {
                    $markets[] = array('key' => 'spreads', 'outcomes' => array(
                        array('name' => $homeTeam, 'price' => round($hDec, 4), 'point' => floatval($spLineH)),
                        array('name' => $awayTeam, 'price' => round($aDec, 4), 'point' => floatval($spLineA)),
                    ));
                }
            }
            $tot = isset($row['total']) ? $row['total'] : null;
            $ov  = isset($row['over'])  ? $row['over']  : null;
            $un  = isset($row['under']) ? $row['under'] : null;
            if ($tot !== null && $ov !== null && $un !== null && is_numeric($tot) && is_numeric($ov) && is_numeric($un)) {
                $ovDec = odds_api_american_to_decimal($ov);
                $unDec = odds_api_american_to_decimal($un);
                if ($ovDec > 1.0 && $unDec > 1.0) {
                    $markets[] = array('key' => 'totals', 'outcomes' => array(
                        array('name' => 'Over',  'price' => round($ovDec, 4), 'point' => floatval($tot)),
                        array('name' => 'Under', 'price' => round($unDec, 4), 'point' => floatval($tot)),
                    ));
                }
            }
            if (count($markets) === 0) { continue; }
            $bookmakers[] = array('key' => $meta['key'], 'title' => $meta['title'], 'markets' => $markets);
        }
        if (count($bookmakers) === 0) { continue; }
        $events[] = array(
            'id' => 'actionnet_' . (isset($game['id']) ? $game['id'] : md5($homeTeam . '_' . $awayTeam . '_' . $sk)),
            'home_team' => $homeTeam,
            'away_team' => $awayTeam,
            'commence_time' => $ct,
            'bookmakers' => $bookmakers,
        );
    }
    if (count($events) === 0) {
        $error = 'actionnet_no_odds';
    }
    return $events;
}

/**
 * Merge event lists from multiple sources by (home, away, commence-date). Each source's
 * bookmakers are UNION-ed into the output event. Event id is taken from the first source.
 */
function odds_api_merge_events_by_teams($sources) {
    $by = array();
    $keyOrder = array();
    for ($si = 0; $si < count($sources); $si++) {
        $evs = $sources[$si];
        if (!is_array($evs)) { continue; }
        for ($i = 0; $i < count($evs); $i++) {
            $e = $evs[$i];
            $ht = isset($e['home_team']) ? $e['home_team'] : '';
            $at = isset($e['away_team']) ? $e['away_team'] : '';
            $ct = isset($e['commence_time']) ? substr($e['commence_time'], 0, 10) : '';
            if ($ht === '' || $at === '') { continue; }
            $k = odds_api_normalize_team_name($ht) . '||' . odds_api_normalize_team_name($at) . '||' . $ct;
            if (!isset($by[$k])) {
                $by[$k] = $e;
                $keyOrder[] = $k;
            } else {
                $existing = $by[$k];
                $existingBks = isset($existing['bookmakers']) ? $existing['bookmakers'] : array();
                $newBks = isset($e['bookmakers']) ? $e['bookmakers'] : array();
                $by[$k]['bookmakers'] = array_merge($existingBks, $newBks);
            }
        }
    }
    $out = array();
    for ($i = 0; $i < count($keyOrder); $i++) {
        $out[] = $by[$keyOrder[$i]];
    }
    return $out;
}

/**
 * Unified failover chain for odds events:
 * 1) The Odds API (primary + optional secondary key)
 * 2) Bovada public JSON + ESPN scoreboard API (merged; both run when the-odds-api is empty)
 * 3) NBA model fallback (NBA only, last resort)
 *
 * @param string $sk
 * @param string $primaryApiKey
 * @param string $secondaryApiKey
 * @return array
 */
function odds_api_get_events_with_failover($sk, $primaryApiKey, $secondaryApiKey) {
    $out = array(
        'events' => array(),
        'source' => 'none',
        'url_used' => '',
        'candidates_tried' => 0,
        'region_profile' => '',
        'credits_charged' => false,
        'errors' => array(),
    );

    $keys = array();
    if (trim($primaryApiKey) !== '') {
        $keys[] = $primaryApiKey;
    }
    if (trim($secondaryApiKey) !== '' && $secondaryApiKey !== $primaryApiKey) {
        $keys[] = $secondaryApiKey;
    }

    if (count($keys) > 0) {
        $rawRes = odds_api_v4_get_odds_raw_multi_key($sk, $keys);
        $out['url_used'] = isset($rawRes['url_used']) ? $rawRes['url_used'] : '';
        $out['candidates_tried'] = isset($rawRes['candidates_tried']) ? intval($rawRes['candidates_tried']) : 0;
        $out['region_profile'] = isset($rawRes['region_profile']) ? $rawRes['region_profile'] : '';
        if ($rawRes['raw'] !== false && $rawRes['raw'] !== '') {
            $data = json_decode($rawRes['raw'], true);
            if (is_array($data) && isset($data['data']) && is_array($data['data'])) {
                $data = $data['data'];
            }
            if (is_array($data) && count($data) > 0) {
                $anyBooks = false;
                for ($di = 0; $di < count($data); $di++) {
                    $ev0 = $data[$di];
                    if (!is_array($ev0)) {
                        continue;
                    }
                    $bks = isset($ev0['bookmakers']) ? $ev0['bookmakers'] : array();
                    if (is_array($bks) && count($bks) > 0) {
                        $anyBooks = true;
                        break;
                    }
                }
                if ($anyBooks) {
                    $out['events'] = $data;
                    $out['source'] = 'the_odds_api';
                    $out['credits_charged'] = true;
                    return $out;
                }
                $out['errors'][] = 'the_odds_zero_bookmakers';
            } else {
                $out['errors'][] = 'the_odds_no_events';
            }
        } else {
            $out['errors'][] = 'the_odds_http_fail';
        }
    } else {
        $out['errors'][] = 'the_odds_key_missing';
    }

    // Run Bovada + ESPN in sequence and merge by (home, away, date) so the same game
    // gets multiple bookmakers — that's what the consensus devig needs. Bovada is a real
    // book (usable for picks); ESPN is a single-provider synthetic (usable for display,
    // excluded from consensus by sports_value_quote_usable).
    // Fan out to Action Network (6+ real books), Bovada, and ESPN. Merge by team pair +
    // date so the same game carries bookmakers from all three. Action Network is the
    // consensus-diversity source — without it, ESPN-DK + Bovada price too similarly to
    // produce value bets in efficient playoff markets.
    $actionUrl = '';
    $actionErr = '';
    $actionEvents = odds_api_events_from_action_network($sk, $actionUrl, $actionErr);

    $bovadaUrl = '';
    $bovadaErr = '';
    $bovadaEvents = odds_api_events_from_bovada($sk, $bovadaUrl, $bovadaErr);

    $espnUrl = '';
    $espnErr = '';
    $espnEvents = odds_api_events_from_espn($sk, $espnUrl, $espnErr);

    if (count($actionEvents) > 0 || count($bovadaEvents) > 0 || count($espnEvents) > 0) {
        $merged = odds_api_merge_events_by_teams(array($actionEvents, $bovadaEvents, $espnEvents));
        $sources = array();
        if (count($actionEvents) > 0) { $sources[] = 'action_network'; }
        if (count($bovadaEvents) > 0) { $sources[] = 'bovada'; }
        if (count($espnEvents) > 0)   { $sources[] = 'espn_scoreboard_api'; }
        $out['events'] = $merged;
        $out['source'] = implode('+', $sources);
        $out['url_used'] = count($actionEvents) > 0 ? $actionUrl : (count($bovadaEvents) > 0 ? $bovadaUrl : $espnUrl);
        return $out;
    }
    if ($actionErr !== '') { $out['errors'][] = $actionErr; }
    if ($bovadaErr !== '') { $out['errors'][] = $bovadaErr; }
    if ($espnErr !== '')   { $out['errors'][] = $espnErr; }

    if ($sk === 'basketball_nba') {
        $nbaUrl = '';
        $nbaErr = '';
        $nbaEvents = odds_api_events_from_nba_model($nbaUrl, $nbaErr);
        if (count($nbaEvents) > 0) {
            $out['events'] = $nbaEvents;
            $out['source'] = 'nba_model_fallback';
            $out['url_used'] = $nbaUrl;
            return $out;
        }
        if ($nbaErr !== '') {
            $out['errors'][] = $nbaErr;
        }
    }

    return $out;
}
