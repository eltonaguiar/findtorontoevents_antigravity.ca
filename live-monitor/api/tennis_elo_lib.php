<?php
/**
 * Tennis ELO overlay — reads live-monitor/data/tennis_elo_ratings.json
 * produced by live-monitor/tennis_elo_engine.py (data from
 * github.com/JeffSackmann/tennis_atp, MIT license).
 *
 * Provides:
 *   tennis_elo_win_prob($ra, $rb) -> float [0,1]
 *   tennis_elo_lookup($name)      -> array|null (player record)
 *   sports_picks_annotate_tennis_elo(&$vb) -> void (mutates pick)
 *
 * Gate (must ALL be true to annotate):
 *   - sport contains 'tennis'
 *   - market is 'h2h' (moneyline)
 *   - both players found in ratings with >= 30 matches
 *
 * Composite-score nudge: up to +5 pts when ELO win prob diverges from
 * book implied probability by >= 5 percentage points in favour of the
 * picked side (same pattern as NHL goalie overlay). EV%, grade, Kelly
 * and recommendation are not changed.
 *
 * PHP 5.2 compatible.
 */

function _tennis_elo_load() {
    static $cache = null;
    if ($cache !== null) {
        return $cache;
    }
    $candidates = array(
        dirname(__FILE__) . '/../data/tennis_elo_ratings.json',
        dirname(__FILE__) . '/../../live-monitor/data/tennis_elo_ratings.json',
    );
    for ($i = 0; $i < count($candidates); $i++) {
        $p = $candidates[$i];
        if (!file_exists($p)) {
            continue;
        }
        $raw = @file_get_contents($p);
        if ($raw === false || $raw === '') {
            continue;
        }
        $obj = @json_decode($raw, true);
        if (!is_array($obj) || !isset($obj['players']) || !is_array($obj['players'])) {
            continue;
        }
        $cache = $obj['players'];
        return $cache;
    }
    $cache = array();
    return $cache;
}

/**
 * Compute ELO win probability for player A vs player B.
 * Returns probability in [0,1] that A beats B.
 */
function tennis_elo_win_prob($ratingA, $ratingB) {
    $diff = floatval($ratingB) - floatval($ratingA);
    return 1.0 / (1.0 + pow(10.0, $diff / 400.0));
}

/**
 * Return the surface-specific ELO from a player record.
 * Falls back to overall ELO if surface-specific is missing.
 */
function tennis_elo_surface_rating($entry, $surface) {
    if ($surface === 'clay' && isset($entry['elo_clay'])) {
        return floatval($entry['elo_clay']);
    }
    if ($surface === 'grass' && isset($entry['elo_grass'])) {
        return floatval($entry['elo_grass']);
    }
    if ($surface === 'hard' && isset($entry['elo_hard'])) {
        return floatval($entry['elo_hard']);
    }
    return isset($entry['elo']) ? floatval($entry['elo']) : 1500.0;
}

/**
 * Look up a player by name in the ratings JSON.
 * Tries exact match, then case-insensitive match, then last-name fuzzy match.
 * Returns the player record array or null.
 */
function tennis_elo_lookup($playerName) {
    $players = _tennis_elo_load();
    if (empty($players)) {
        return null;
    }
    $name = trim(strval($playerName));
    if ($name === '') {
        return null;
    }

    // Exact match
    if (isset($players[$name])) {
        return $players[$name];
    }

    // Case-insensitive exact
    $nameLower = strtolower($name);
    foreach ($players as $k => $v) {
        if (strtolower($k) === $nameLower) {
            return $v;
        }
    }

    // Last-name fuzzy: take highest-ELO candidate to minimise false positives
    $parts = preg_split('/\s+/', $name);
    $lastName = strtolower($parts[count($parts) - 1]);
    if (strlen($lastName) < 4) {
        return null; // too short to be uniquely identifying
    }
    $bestElo = -1.0;
    $bestEntry = null;
    foreach ($players as $k => $v) {
        $kParts = preg_split('/\s+/', strtolower($k));
        if ($kParts[count($kParts) - 1] === $lastName) {
            $e = isset($v['elo']) ? floatval($v['elo']) : 0.0;
            if ($e > $bestElo) {
                $bestElo = $e;
                $bestEntry = $v;
            }
        }
    }
    return $bestEntry;
}

/**
 * Seasonal surface heuristic (ATP tour calendar):
 *   Jan-Feb  -> hard  (AO + hard-court swing)
 *   Mar-Jun  -> clay  (Monte Carlo, Madrid, Rome, Roland Garros)
 *   Jun-Jul  -> grass (Queen's, Wimbledon)
 *   Aug-Dec  -> hard  (US Open series, indoor season)
 *
 * Returns 'hard', 'clay', or 'grass'.
 */
function _tennis_elo_guess_surface($commenceTime) {
    if (!$commenceTime) {
        return 'hard';
    }
    $ts = strtotime($commenceTime);
    if ($ts === false || $ts <= 0) {
        return 'hard';
    }
    $m = intval(date('n', $ts));
    if ($m >= 3 && $m <= 5) {
        return 'clay';
    }
    if ($m == 6 || $m == 7) {
        return 'grass';
    }
    return 'hard';
}

/**
 * Annotate a tennis pick with ELO-derived win probability and composite nudge.
 * Mutates $vb in place. No-op for non-tennis sports, non-h2h markets,
 * or when either player is not found in the ratings with sufficient history.
 */
function sports_picks_annotate_tennis_elo(&$vb) {
    $sport = isset($vb['sport']) ? strval($vb['sport']) : '';
    if (strpos($sport, 'tennis') === false) {
        return;
    }

    $mkt = isset($vb['market']) ? strtolower(strval($vb['market'])) : '';
    // Empty market is treated the same as 'h2h' (tennis odds API returns h2h
    // moneylines; an empty market key means no market filter was set, so we
    // apply the overlay). Skip totals/spreads which have no player winner field.
    if ($mkt !== '' && $mkt !== 'h2h') {
        return;
    }

    $home = isset($vb['home_team']) ? strval($vb['home_team']) : '';
    $away = isset($vb['away_team']) ? strval($vb['away_team']) : '';
    if ($home === '' || $away === '') {
        return;
    }

    $he = tennis_elo_lookup($home);
    $ae = tennis_elo_lookup($away);
    if ($he === null || $ae === null) {
        return;
    }

    $hMatches = isset($he['matches']) ? intval($he['matches']) : 0;
    $aMatches = isset($ae['matches']) ? intval($ae['matches']) : 0;
    if ($hMatches < 30 || $aMatches < 30) {
        return;
    }

    $surface = _tennis_elo_guess_surface(
        isset($vb['commence_time']) ? $vb['commence_time'] : ''
    );
    $hRating = tennis_elo_surface_rating($he, $surface);
    $aRating = tennis_elo_surface_rating($ae, $surface);

    $eloWinProbHome = tennis_elo_win_prob($hRating, $aRating);

    // Book's implied probability for this outcome
    $bestOdds = isset($vb['best_odds']) ? floatval($vb['best_odds']) : 0.0;
    $bookImplied = ($bestOdds > 1.01) ? (1.0 / $bestOdds) : 0.5;

    // Determine if the picked outcome is the home player
    $outcomeName = isset($vb['outcome_name']) ? strtolower(strval($vb['outcome_name'])) : '';
    $homeLower = strtolower($home);
    // Home pick if outcome name contains the home player's last name or full name
    $homeParts = preg_split('/\s+/', $homeLower);
    $homeLastName = $homeParts[count($homeParts) - 1];
    $isHomePick = (
        strpos($outcomeName, $homeLastName) !== false
        || strpos($outcomeName, $homeLower) !== false
    );

    $eloPickProb = $isHomePick ? $eloWinProbHome : (1.0 - $eloWinProbHome);
    $gap_pp = ($eloPickProb - $bookImplied) * 100.0; // >0 means ELO more bullish than book

    // Serve dominance info for context
    $hServeDom = isset($he['serve_dominance']) ? round(floatval($he['serve_dominance']), 1) : null;
    $aServeDom = isset($ae['serve_dominance']) ? round(floatval($ae['serve_dominance']), 1) : null;

    $vb['tennis_elo_applied'] = true;
    $vb['tennis_elo_surface'] = $surface;
    $vb['tennis_elo_home_rating'] = round($hRating, 0);
    $vb['tennis_elo_away_rating'] = round($aRating, 0);
    $vb['tennis_elo_win_prob_home'] = round($eloWinProbHome, 4);
    $vb['tennis_elo_gap_pp'] = round($gap_pp, 2);
    if ($hServeDom !== null) {
        $vb['tennis_elo_home_serve_dom'] = $hServeDom;
    }
    if ($aServeDom !== null) {
        $vb['tennis_elo_away_serve_dom'] = $aServeDom;
    }

    $ratingReason = 'ELO (' . $surface . '): '
        . $home . ' ' . round($hRating, 0)
        . ' vs ' . $away . ' ' . round($aRating, 0)
        . ' → pick win prob ' . round($eloPickProb * 100.0, 1) . '%';
    if (!isset($vb['rating_reasons'])) {
        $vb['rating_reasons'] = array();
    }
    $vb['rating_reasons'][] = $ratingReason;

    // Composite-score nudge when ELO confirms the pick with >= 5pp edge
    if ($gap_pp >= 5.0) {
        $nudge = min(5, intval(floor($gap_pp / 3.0)));
        if (!isset($vb['composite_score'])) {
            $vb['composite_score'] = 50;
        }
        $vb['composite_score'] = min(100, intval($vb['composite_score']) + $nudge);
        $vb['tennis_elo_score_boost'] = $nudge;
    }
}
