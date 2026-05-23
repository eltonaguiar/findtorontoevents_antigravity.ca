<?php
/**
 * NHL goalie overlay (Phase 2) — reads live-monitor/data/nhl_goalies_today.json
 * (produced by tools/scrapers/nhl_goalie_scraper.py via the daily
 * `sports-data-snapshots.yml` GHA workflow + FTP upload) and applies a small
 * GSAx/60-driven probability shift to NHL h2h 2-way buckets.
 *
 * Spec: updates/2026-04-26-nhl-goalie-overlay-wiring-plan.md
 *
 * Gate (must ALL be true to apply):
 *   - sport == icehockey_nhl
 *   - both home & away starters are confirmed
 *   - both goalies have season GP >= 10
 *
 * Formula (v1):
 *   delta = home.gsax_per60 - away.gsax_per60
 *   shift_pp = clamp(delta * 5.0, -5.0, +5.0)        // 0.5pp / 0.1 GSAx delta, ±5pp cap
 *   if home_goalie.rest_days === 0: shift_pp -= 1.0  // B2B penalty
 *   if away_goalie.rest_days === 0: shift_pp += 1.0
 *   p_home_adj = clamp(p_home + shift_pp/100, 0.01, 0.99)
 *
 * Graceful degrade: missing JSON / stale (>24h) / no match -> overlay returns false.
 *
 * PHP 5.2 compatible — stdlib only, no extensions.
 */

if (!defined('SPORTS_VALUE_NHL_GOALIE_STALE_SECS')) {
    // 24h staleness guard. The scraper runs daily; older data should not anchor live picks.
    define('SPORTS_VALUE_NHL_GOALIE_STALE_SECS', 24 * 3600);
}

/**
 * Load and index the newest nhl_goalies_today.json. Static-cached per request.
 * Returns an indexed map keyed by lower(home_abbrev)|lower(away_abbrev) AND
 * also by lower(home_name)|lower(away_name) so callers can match either way.
 *
 * @return array map of "h|a" => game record, plus a special '_meta' entry.
 */
function sports_value_nhl_goalie_load_today() {
    static $cache = null;
    if ($cache !== null) {
        return $cache;
    }
    $cache = array();
    $path = __DIR__ . '/../../live-monitor/data/nhl_goalies_today.json';
    // sports_value_*.php live at live-monitor/api/, so the data dir is one up.
    $alt = __DIR__ . '/../data/nhl_goalies_today.json';
    if (is_file($alt)) {
        $path = $alt;
    }
    if (!is_file($path)) {
        return $cache;
    }
    $mtime = @filemtime($path);
    if (!$mtime || (time() - $mtime) > SPORTS_VALUE_NHL_GOALIE_STALE_SECS) {
        return $cache;
    }
    $raw = @file_get_contents($path);
    if (!$raw) {
        return $cache;
    }
    $data = json_decode($raw, true);
    if (!is_array($data) || !isset($data['games']) || !is_array($data['games'])) {
        return $cache;
    }
    foreach ($data['games'] as $g) {
        if (!is_array($g)) {
            continue;
        }
        $hAbbr = isset($g['home_abbrev']) ? strtolower(strval($g['home_abbrev'])) : '';
        $aAbbr = isset($g['away_abbrev']) ? strtolower(strval($g['away_abbrev'])) : '';
        $hName = isset($g['home']) ? strtolower(strval($g['home'])) : '';
        $aName = isset($g['away']) ? strtolower(strval($g['away'])) : '';
        if ($hAbbr && $aAbbr) {
            $cache[$hAbbr . '|' . $aAbbr] = $g;
        }
        if ($hName && $aName) {
            $cache[$hName . '|' . $aName] = $g;
        }
    }
    return $cache;
}

/**
 * Match a bucket to a goalie record. Returns null when sport != icehockey_nhl
 * or no entry matches. Otherwise returns:
 *   { home_goalie, away_goalie, both_confirmed, applied_reason }
 *
 * @param array $bucket expects keys: sport, home_team, away_team
 * @return array|null
 */
function sports_value_nhl_goalie_lookup_for_bucket($bucket) {
    if (!is_array($bucket)) {
        return null;
    }
    $sport = isset($bucket['sport']) ? strval($bucket['sport']) : '';
    if (strpos($sport, 'icehockey_nhl') === false) {
        return null;
    }
    $home = isset($bucket['home_team']) ? strtolower(strval($bucket['home_team'])) : '';
    $away = isset($bucket['away_team']) ? strtolower(strval($bucket['away_team'])) : '';
    if ($home === '' || $away === '') {
        return null;
    }
    $idx = sports_value_nhl_goalie_load_today();
    if (!$idx) {
        return null;
    }
    $key = $home . '|' . $away;
    $game = isset($idx[$key]) ? $idx[$key] : null;
    if ($game === null) {
        // Fallback: substring match by city/abbrev token. Bucket home_team is
        // typically the full name; abbrev keys won't hit but full-name keys
        // may differ in punctuation.
        foreach ($idx as $k => $g) {
            $parts = explode('|', $k);
            if (count($parts) !== 2) {
                continue;
            }
            if (strpos($parts[0], $home) !== false && strpos($parts[1], $away) !== false) {
                $game = $g;
                break;
            }
            if (strpos($home, $parts[0]) !== false && strpos($away, $parts[1]) !== false) {
                $game = $g;
                break;
            }
        }
    }
    if (!is_array($game)) {
        return null;
    }
    $hg = isset($game['home_goalie']) && is_array($game['home_goalie']) ? $game['home_goalie'] : null;
    $ag = isset($game['away_goalie']) && is_array($game['away_goalie']) ? $game['away_goalie'] : null;
    $both = ($hg !== null && $ag !== null
        && !empty($hg['confirmed']) && !empty($ag['confirmed']));
    return array(
        'home_goalie' => $hg,
        'away_goalie' => $ag,
        'both_confirmed' => $both ? true : false,
        'applied_reason' => $both ? 'both_confirmed' : 'unconfirmed_or_missing',
    );
}

/**
 * Apply the goalie overlay to the home-team probability for a 2-way bucket.
 * Returns array($p_home_adj, $shift_pp, $applied_bool).
 *
 * Caller is responsible for renormalizing the away side: $p_away = 1 - $p_home_adj.
 *
 * @param float $p_home  pre-overlay home win probability (Shin/Jensen output)
 * @param array $bucket  bucket meta (sport/home_team/away_team)
 * @return array [float $p_home_adj, float $shift_pp, bool $applied]
 */
function sports_value_nhl_goalie_apply_overlay($p_home, $bucket) {
    $p_home = floatval($p_home);
    $info = sports_value_nhl_goalie_lookup_for_bucket($bucket);
    if ($info === null || empty($info['both_confirmed'])) {
        return array($p_home, 0.0, false);
    }
    $hg = $info['home_goalie'];
    $ag = $info['away_goalie'];
    // Both goalies must have GP >= 10 to use season-to-date GSAx/60.
    $hgp = isset($hg['gp']) ? intval($hg['gp']) : 0;
    $agp = isset($ag['gp']) ? intval($ag['gp']) : 0;
    if ($hgp < 10 || $agp < 10) {
        return array($p_home, 0.0, false);
    }
    // gsax_per60 may be null if MoneyPuck join failed — bail rather than guess.
    if (!isset($hg['gsax_per60']) || $hg['gsax_per60'] === null) {
        return array($p_home, 0.0, false);
    }
    if (!isset($ag['gsax_per60']) || $ag['gsax_per60'] === null) {
        return array($p_home, 0.0, false);
    }
    $hGsax = floatval($hg['gsax_per60']);
    $aGsax = floatval($ag['gsax_per60']);
    $delta = $hGsax - $aGsax;
    $shift_pp = $delta * 5.0;
    if ($shift_pp > 5.0) { $shift_pp = 5.0; }
    if ($shift_pp < -5.0) { $shift_pp = -5.0; }
    // B2B (rest_days === 0) penalties. Missing rest_days -> no penalty.
    if (isset($hg['rest_days']) && intval($hg['rest_days']) === 0) {
        $shift_pp -= 1.0;
    }
    if (isset($ag['rest_days']) && intval($ag['rest_days']) === 0) {
        $shift_pp += 1.0;
    }
    $p_adj = $p_home + ($shift_pp / 100.0);
    if ($p_adj < 0.01) { $p_adj = 0.01; }
    if ($p_adj > 0.99) { $p_adj = 0.99; }
    return array($p_adj, $shift_pp, true);
}
