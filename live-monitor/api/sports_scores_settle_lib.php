<?php
/**
 * The Odds API /scores response → completed-game map + h2h/spreads/totals grading.
 * Shared by sports_bets.php (settle_by_scores) and sports_picks.php (settle_picks).
 * PHP 5.2 compatible.
 */
require_once dirname(__FILE__) . '/odds_api_fetch.php';

/**
 * @param string $name
 * @return array
 */
function sports_scores_team_aliases($name) {
    $aliases = array();
    $base = strtolower(trim($name));
    $base = preg_replace('/[^a-z0-9 ]+/', ' ', $base);
    $base = preg_replace('/\s+/', ' ', $base);
    $base = trim($base);
    if ($base === '') {
        return array();
    }
    $aliases[$base] = true;
    if (strpos($base, 'la ') === 0) {
        $aliases['los angeles ' . substr($base, 3)] = true;
    }
    if (strpos($base, 'los angeles ') === 0) {
        $aliases['la ' . substr($base, 12)] = true;
    }
    if (strpos($base, 'ny ') === 0) {
        $aliases['new york ' . substr($base, 3)] = true;
    }
    if (strpos($base, 'new york ') === 0) {
        $aliases['ny ' . substr($base, 9)] = true;
    }
    if (strpos($base, 'st ') === 0) {
        $aliases['saint ' . substr($base, 3)] = true;
    }
    if (strpos($base, 'saint ') === 0) {
        $aliases['st ' . substr($base, 6)] = true;
    }
    $parts = explode(' ', $base);
    if (count($parts) >= 2) {
        $aliases[$parts[count($parts) - 2] . ' ' . $parts[count($parts) - 1]] = true;
    }
    if (count($parts) >= 1) {
        $aliases[$parts[count($parts) - 1]] = true;
    }
    // MLS / club names: "Vancouver Whitecaps FC" vs "Vancouver Whitecaps" in scores API
    $suff = array(' fc', ' sc', ' cf', ' afc');
    for ($si = 0; $si < count($suff); $si++) {
        $s = $suff[$si];
        if (strlen($base) > strlen($s) && substr($base, -strlen($s)) === $s) {
            $aliases[trim(substr($base, 0, -strlen($s)))] = true;
        }
    }
    // Picks use short name; The Odds API scores may use "… FC" / club suffix
    if (strlen($base) > 0) {
        $aliases[$base . ' fc'] = true;
    }
    return array_keys($aliases);
}

function sports_scores_date_key($dt) {
    if ($dt === null) {
        return '';
    }
    $txt = trim(strval($dt));
    if ($txt === '') {
        return '';
    }
    return substr($txt, 0, 10);
}

function sports_scores_match_alias_keys($sport, $homeTeam, $awayTeam, $commenceTime) {
    $keys = array();
    $dateKey = sports_scores_date_key($commenceTime);
    if ($dateKey === '') {
        return $keys;
    }
    $sportKey = strtolower(trim($sport));
    $homeAliases = sports_scores_team_aliases($homeTeam);
    $awayAliases = sports_scores_team_aliases($awayTeam);
    for ($hi = 0; $hi < count($homeAliases); $hi++) {
        for ($ai = 0; $ai < count($awayAliases); $ai++) {
            $keys[] = $sportKey . '|' . $dateKey . '|' . $homeAliases[$hi] . '|' . $awayAliases[$ai];
        }
    }
    return array_values(array_unique($keys));
}

function sports_scores_add_alias(&$aliasMap, $key, $scoreRow) {
    if ($key === '') {
        return;
    }
    if (!isset($aliasMap[$key])) {
        $aliasMap[$key] = $scoreRow;
        return;
    }
    if (!is_array($aliasMap[$key])) {
        return;
    }
    if ($aliasMap[$key]['event_id'] !== $scoreRow['event_id']) {
        $aliasMap[$key] = false;
    }
}

/**
 * @param string $sport Odds API sport key
 * @param array $games decoded JSON array from /scores
 * @return array array('by_event'=>..., 'by_alias'=>...)
 */
function sports_scores_map_from_games_array($sport, $games) {
    $scoreMap = array('by_event' => array(), 'by_alias' => array());
    if (!is_array($games)) {
        return $scoreMap;
    }
    for ($gi = 0; $gi < count($games); $gi++) {
        $g = $games[$gi];
        if (!isset($g['completed']) || $g['completed'] !== true) {
            continue;
        }
        if (!isset($g['scores']) || !is_array($g['scores']) || count($g['scores']) < 2) {
            continue;
        }
        $homeScore = null;
        $awayScore = null;
        $homeName = isset($g['home_team']) ? $g['home_team'] : '';
        $awayName = isset($g['away_team']) ? $g['away_team'] : '';
        for ($si = 0; $si < count($g['scores']); $si++) {
            $nm = isset($g['scores'][$si]['name']) ? $g['scores'][$si]['name'] : '';
            $sc = isset($g['scores'][$si]['score']) ? intval($g['scores'][$si]['score']) : null;
            if ($nm === $homeName) {
                $homeScore = $sc;
            } else if ($nm === $awayName) {
                $awayScore = $sc;
            }
        }
        if ($homeScore === null || $awayScore === null) {
            continue;
        }
        if (!isset($g['id'])) {
            continue;
        }
        $scoreRow = array(
            'event_id' => $g['id'],
            'home' => $homeScore,
            'away' => $awayScore,
            'home_name' => $homeName,
            'away_name' => $awayName,
            'commence_time' => isset($g['commence_time']) ? $g['commence_time'] : '',
        );
        $scoreMap['by_event'][$g['id']] = $scoreRow;
        $aliasKeys = sports_scores_match_alias_keys($sport, $homeName, $awayName, isset($g['commence_time']) ? $g['commence_time'] : '');
        for ($ki = 0; $ki < count($aliasKeys); $ki++) {
            sports_scores_add_alias($scoreMap['by_alias'], $aliasKeys[$ki], $scoreRow);
        }
    }
    return $scoreMap;
}

/**
 * @param string $sport Odds API sport key
 * @param string $apiKey
 * @param int $daysFrom 1–3 (Odds API limit)
 * @param int $creditsUsed incremented by 2 on attempt
 * @return array|null score index or null if HTTP/JSON failure
 */
function sports_scores_fetch_score_map($sport, $apiKey, $daysFrom, &$creditsUsed) {
    $creditsUsed += 2;
    $scoresUrl = 'https://api.the-odds-api.com/v4/sports/' . urlencode($sport) . '/scores/?daysFrom=' . intval($daysFrom) . '&apiKey=' . urlencode($apiKey);
    $raw = odds_api_http_get($scoresUrl);
    if ($raw === false) {
        return null;
    }
    $games = json_decode($raw, true);
    if (!is_array($games)) {
        return null;
    }
    return sports_scores_map_from_games_array($sport, $games);
}

function sports_scores_completed_count($scoreMap) {
    if (!is_array($scoreMap) || !isset($scoreMap['by_event']) || !is_array($scoreMap['by_event'])) {
        return 0;
    }
    return count($scoreMap['by_event']);
}

function sports_scores_find_match($scoreMap, $sport, $eventId, $homeTeam, $awayTeam, $commenceTime) {
    if (is_array($scoreMap) && isset($scoreMap['by_event']) && $eventId !== '' && isset($scoreMap['by_event'][$eventId])) {
        return $scoreMap['by_event'][$eventId];
    }
    if (!is_array($scoreMap) || !isset($scoreMap['by_alias']) || !is_array($scoreMap['by_alias'])) {
        return null;
    }
    $aliasKeys = sports_scores_match_alias_keys($sport, $homeTeam, $awayTeam, $commenceTime);
    for ($i = 0; $i < count($aliasKeys); $i++) {
        $k = $aliasKeys[$i];
        if (isset($scoreMap['by_alias'][$k]) && is_array($scoreMap['by_alias'][$k])) {
            return $scoreMap['by_alias'][$k];
        }
    }
    return null;
}

/**
 * Grade one ticket given final scores map row (decimal odds).
 *
 * @param array $sm one entry from score map
 * @param string $market h2h|spreads|totals
 * @param string $pick team name or Over/Under
 * @param float|null $pickPoint spread/total line
 * @param float $odds decimal odds
 * @param float $stake
 * @return array|null array('result'=>won|lost|push, 'pnl'=>float) or null if ungraded
 */
function sports_scores_grade_ticket($sm, $market, $pick, $pickPoint, $odds, $stake) {
    $hs = $sm['home'];
    $as = $sm['away'];
    $m = strtolower($market);
    $result = null;
    $pt = ($pickPoint === null || $pickPoint === '') ? null : floatval($pickPoint);
    if ($m === 'h2h') {
        if ($pick === $sm['home_name']) {
            $result = ($hs > $as) ? 'won' : (($hs < $as) ? 'lost' : 'push');
        } else if ($pick === $sm['away_name']) {
            $result = ($as > $hs) ? 'won' : (($as < $hs) ? 'lost' : 'push');
        }
    } else if ($m === 'spreads') {
        if ($pt === null) {
            return null;
        }
        if ($pick === $sm['home_name']) {
            $adj = $hs + $pt;
            $result = ($adj > $as) ? 'won' : (($adj < $as) ? 'lost' : 'push');
        } else if ($pick === $sm['away_name']) {
            $adj = $as + $pt;
            $result = ($adj > $hs) ? 'won' : (($adj < $hs) ? 'lost' : 'push');
        }
    } else if ($m === 'totals') {
        if ($pt === null) {
            return null;
        }
        $sum = $hs + $as;
        $pickLower = strtolower($pick);
        if ($pickLower === 'over') {
            $result = ($sum > $pt) ? 'won' : (($sum < $pt) ? 'lost' : 'push');
        } else if ($pickLower === 'under') {
            $result = ($sum < $pt) ? 'won' : (($sum > $pt) ? 'lost' : 'push');
        }
    }
    if ($result === null) {
        return null;
    }
    $pnl = 0.0;
    if ($result === 'won') {
        $pnl = round(($odds - 1.0) * $stake, 2);
    } else if ($result === 'lost') {
        $pnl = -1 * round($stake, 2);
    }
    return array('result' => $result, 'pnl' => $pnl);
}
