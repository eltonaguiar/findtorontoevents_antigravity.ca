<?php
/**
 * Build lm_sports_value_bets from lm_sports_odds (consensus devig + per-book +EV).
 * PHP 5.2 compatible.
 */

require_once dirname(__FILE__) . '/sports_value_nhl_goalie_lib.php';

function sports_value_line_key($market, $outcome_point) {
    $m = strtolower($market);
    if ($m === 'h2h') {
        return '';
    }
    $p = 0.0;
    if ($outcome_point !== null && $outcome_point !== '') {
        $p = abs(floatval($outcome_point));
    }
    return (string) $p;
}

function sports_value_fmt_point($pt) {
    if ($pt === null || $pt === '') {
        return '';
    }
    $x = floatval($pt);
    if (abs($x - round($x)) < 0.001) {
        return sprintf('%d.00', intval(round($x)));
    }
    return sprintf('%.2f', $x);
}

function sports_value_bet_type_label($market, $outcome_name, $pointRaw) {
    $m = strtolower($market);
    if ($m === 'h2h') {
        return $outcome_name . ' ML';
    }
    if ($m === 'totals') {
        return $outcome_name . ' ' . sports_value_fmt_point($pointRaw);
    }
    $x = floatval($pointRaw);
    $fp = sports_value_fmt_point($pointRaw);
    if ($x > 0) {
        return $outcome_name . ' +' . $fp;
    }
    return $outcome_name . ' ' . $fp;
}

function sports_value_book_is_canadian($bookKey) {
    $k = strtolower($bookKey);
    $ca = array('fanduel', 'draftkings', 'betmgm', 'betrivers', 'espnbet', 'pinnacle', 'coolbet', 'ballybet', 'hardrockbet', 'leovegas', 'thescore', 'betway', 'unibet', 'olg_prolineplus', 'olg', 'prolineplus');
    for ($i = 0; $i < count($ca); $i++) {
        if (strpos($k, $ca[$i]) !== false) {
            return true;
        }
    }
    return false;
}

function sports_value_all_odds_json($quotes) {
    $items = array();
    for ($a = 0; $a < count($quotes); $a++) {
        $items[] = array(
            'book_key' => $quotes[$a]['bookmaker_key'],
            'book_name' => $quotes[$a]['bookmaker'],
            'price' => $quotes[$a]['price'],
            'is_canadian' => sports_value_book_is_canadian($quotes[$a]['bookmaker_key']) ? 1 : 0,
        );
    }
    return json_encode($items);
}

function sports_value_sort_quotes_desc($qa, $qb) {
    if ($qa['price'] == $qb['price']) {
        return 0;
    }
    return ($qa['price'] > $qb['price']) ? -1 : 1;
}

/**
 * Skip exchange/outlier lines that break devig (e.g. Betfair decimal noise, bogus 300.0).
 */
function sports_value_quote_usable($bookKey, $price) {
    if ($price < 1.02 || $price > 80.0) {
        return false;
    }
    $k = strtolower($bookKey);
    if (strpos($k, 'betfair') !== false) {
        return false;
    }
    if (strpos($k, 'espnbet') !== false) {
        return false;
    }
    // NOTE: The old code filtered out 'espn_api' here, on the premise that the ESPN
    // scoreboard fallback returned synthetic 1.91 placeholder prices. That premise is
    // no longer true since PR #352's parser rewrite (reads real moneyline.home.close.odds
    // etc.) — the ESPN feed now delivers real Draft Kings prices. Letting them through
    // is what makes NBA/NHL playoff consensus work when Bovada + ESPN are both present
    // (the-odds-api lines are often empty for playoff markets). Keeping ESPN excluded
    // would leave us with <2 books after filtering and no picks generated.
    // If ESPN prices are ever found to be meaningfully stale, re-add an exclusion
    // that checks a staleness timestamp rather than the bookmaker key.
    return true;
}

/**
 * Pinnacle-quoted (sharp) line from The Odds API — use for anchor when present.
 */
function sports_value_book_is_pinnacle($bookKey) {
    if ($bookKey === null || $bookKey === '') {
        return false;
    }
    $k = strtolower($bookKey);
    return (strpos($k, 'pinnacle') !== false);
}

/**
 * Per-outcome mean(1/decimal_odds) over usable quotes, optionally excluding one book.
 * Normalized to a probability vector. Fixes Jensen: use E[1/price] not 1/E[price].
 * Returns null if any outcome has zero usable quotes (after exclude).
 * @return array|null
 */
function sports_value_truep_consensus_jensen($outList, $nOut, $excludeBookKey) {
    $cons = array();
    for ($oi = 0; $oi < $nOut; $oi++) {
        $qs = $outList[$oi]['quotes'];
        $sx = 0.0;
        $n = 0;
        for ($qj = 0; $qj < count($qs); $qj++) {
            $qk = $qs[$qj]['bookmaker_key'];
            if ($excludeBookKey !== null && $excludeBookKey !== '' && (strtolower($qk) === strtolower($excludeBookKey))) {
                continue;
            }
            if (!sports_value_quote_usable($qk, $qs[$qj]['price'])) {
                continue;
            }
            $sx += 1.0 / $qs[$qj]['price'];
            $n++;
        }
        if ($n < 1) {
            return null;
        }
        $cons[$oi] = $sx / $n;
    }
    $sum = 0.0;
    for ($oi = 0; $oi < $nOut; $oi++) {
        $sum += $cons[$oi];
    }
    if ($sum <= 0.00001) {
        return null;
    }
    $truep = array();
    for ($oi = 0; $oi < $nOut; $oi++) {
        $truep[$oi] = $cons[$oi] / $sum;
    }
    return $truep;
}

/**
 * Shin (1993) devig — finds insider-trader fraction z numerically and returns
 * fair probabilities. Tuned for sharp 2-way books like Pinnacle. Falls back to
 * proportional inverse-normalize when Shin numerics misbehave (no vig, n<2).
 *
 * @param float[] $prices decimal odds, indexed [0..n-1]
 * @return array|null fair probs same length, or null if input is invalid
 */
function sports_value_devig_shin($prices) {
    $n = count($prices);
    if ($n < 2) {
        return null;
    }
    $pi = array();
    $sumPi = 0.0;
    foreach ($prices as $p) {
        $p = floatval($p);
        if ($p < 1.01) {
            return null;
        }
        $inv = 1.0 / $p;
        $pi[] = $inv;
        $sumPi += $inv;
    }
    // No vig (or negative) — just normalize.
    if ($sumPi <= 1.0 + 1e-9) {
        $out = array();
        foreach ($pi as $v) {
            $out[] = ($sumPi > 0) ? ($v / $sumPi) : 0.0;
        }
        return $out;
    }
    // Bisect for z in [0, 0.5] where sum_i shin_p(z) = 1.
    $shinSum = function ($z) use ($pi, $sumPi) {
        $s = 0.0;
        $denom = 2.0 * (1.0 - $z);
        if ($denom <= 1e-9) {
            return PHP_FLOAT_MAX;
        }
        foreach ($pi as $piI) {
            $term = $piI * $piI / $sumPi;
            $s += (sqrt($z * $z + 4.0 * (1.0 - $z) * $term) - $z) / $denom;
        }
        return $s;
    };
    $lo = 0.0;
    $hi = 0.5;
    $fLo = $shinSum($lo) - 1.0; // = sumPi - 1 > 0
    $fHi = $shinSum($hi) - 1.0;
    if ($fLo * $fHi > 0) {
        // Should not normally happen for vigged 2-way book; fall back to multiplicative.
        $out = array();
        foreach ($pi as $v) {
            $out[] = $v / $sumPi;
        }
        return $out;
    }
    for ($i = 0; $i < 60; $i++) {
        $mid = 0.5 * ($lo + $hi);
        $fMid = $shinSum($mid) - 1.0;
        if ($fMid > 0) {
            $lo = $mid;
        } else {
            $hi = $mid;
        }
        if ($hi - $lo < 1e-10) {
            break;
        }
    }
    $z = 0.5 * ($lo + $hi);
    $out = array();
    $denom = 2.0 * (1.0 - $z);
    if ($denom <= 1e-9) {
        $out2 = array();
        foreach ($pi as $v) {
            $out2[] = $v / $sumPi;
        }
        return $out2;
    }
    foreach ($pi as $piI) {
        $term = $piI * $piI / $sumPi;
        $out[] = (sqrt($z * $z + 4.0 * (1.0 - $z) * $term) - $z) / $denom;
    }
    return $out;
}

/**
 * Load the newest Pinnacle scraper snapshot (data/pinnacle_snapshots/*.json),
 * keyed by lowercased "sport|home|away". Stale-protected (15 min). Used as a
 * secondary anchor source when Pinnacle is missing from the Odds-API feed for
 * a bucket. See tools/pinnacle_anchor_scrape.py.
 *
 * @return array map of "sport|home|away" => [home_dec, away_dec]
 */
function sports_value_load_pinnacle_snapshot() {
    static $cache = null;
    if ($cache !== null) {
        return $cache;
    }
    $cache = array();
    $dir = __DIR__ . '/../../data/pinnacle_snapshots';
    if (!is_dir($dir)) {
        return $cache;
    }
    $files = glob($dir . '/*.json');
    if (!$files) {
        return $cache;
    }
    $newest = null;
    $newestMtime = 0;
    foreach ($files as $f) {
        $m = @filemtime($f);
        if ($m && $m > $newestMtime) {
            $newest = $f;
            $newestMtime = $m;
        }
    }
    if (!$newest) {
        return $cache;
    }
    // 15-minute staleness guard; older snapshots are silently ignored so we
    // don't anchor to lines that have already moved.
    if (time() - $newestMtime > 900) {
        return $cache;
    }
    $raw = @file_get_contents($newest);
    if (!$raw) {
        return $cache;
    }
    $data = json_decode($raw, true);
    if (!is_array($data) || !isset($data['events']) || !is_array($data['events'])) {
        return $cache;
    }
    foreach ($data['events'] as $ev) {
        $sport = isset($ev['sport']) ? strtolower(strval($ev['sport'])) : '';
        $home = isset($ev['home']) ? strtolower(strval($ev['home'])) : '';
        $away = isset($ev['away']) ? strtolower(strval($ev['away'])) : '';
        $hd = isset($ev['home_decimal']) ? floatval($ev['home_decimal']) : 0.0;
        $ad = isset($ev['away_decimal']) ? floatval($ev['away_decimal']) : 0.0;
        if (!$sport || !$home || !$away || $hd < 1.01 || $ad < 1.01) {
            continue;
        }
        $cache[$sport . '|' . $home . '|' . $away] = array($hd, $ad);
    }
    return $cache;
}

/**
 * Resolve Pinnacle decimal prices for a bucket from the scraper snapshot.
 * Maps the analyzer's sport key (e.g. "basketball_nba") onto the scraper's
 * sport tag (e.g. "NBA"). Returns [$home_dec, $away_dec] when both are 2-way
 * matched; null otherwise.
 *
 * @return array|null
 */
function sports_value_pinnacle_snapshot_lookup_for_bucket($bucket) {
    if (!is_array($bucket)) {
        return null;
    }
    $sport = isset($bucket['sport']) ? strval($bucket['sport']) : '';
    $home = isset($bucket['home_team']) ? strtolower(strval($bucket['home_team'])) : '';
    $away = isset($bucket['away_team']) ? strtolower(strval($bucket['away_team'])) : '';
    if (!$sport || !$home || !$away) {
        return null;
    }
    // Scraper league_key is one of: nba, nhl, mlb, nfl (uppercased in JSON).
    $tag = '';
    if (strpos($sport, 'basketball_nba') !== false) {
        $tag = 'nba';
    } else if (strpos($sport, 'icehockey_nhl') !== false) {
        $tag = 'nhl';
    } else if (strpos($sport, 'baseball_mlb') !== false) {
        $tag = 'mlb';
    } else if (strpos($sport, 'americanfootball_nfl') !== false) {
        $tag = 'nfl';
    }
    if (!$tag) {
        return null;
    }
    $idx = sports_value_load_pinnacle_snapshot();
    $key = $tag . '|' . $home . '|' . $away;
    return isset($idx[$key]) ? $idx[$key] : null;
}

/**
 * If every outcome has a Pinnacle line (from the Odds-API feed) — or the
 * 2-way scraper snapshot has matching prices for this bucket — de-vig using
 * Shin (closed-form for 2-way, numerical otherwise). Falls back to the
 * proportional method on numerical degeneracy. Soft books are then compared
 * against this anchor in the caller.
 *
 * @param array      $outList outcomes for the bucket
 * @param int        $nOut    number of outcomes
 * @param array|null $bucket  bucket meta (sport/home_team/away_team) for snapshot fallback
 * @return array|null
 */
function sports_value_truep_pinnacle($outList, $nOut, $bucket = null) {
    $prices = array();
    $haveAll = true;
    for ($oi = 0; $oi < $nOut; $oi++) {
        $qs = $outList[$oi]['quotes'];
        $px = 0.0;
        for ($qj = 0; $qj < count($qs); $qj++) {
            if (sports_value_book_is_pinnacle($qs[$qj]['bookmaker_key'])) {
                if (sports_value_quote_usable($qs[$qj]['bookmaker_key'], $qs[$qj]['price'])) {
                    $px = floatval($qs[$qj]['price']);
                    break;
                }
            }
        }
        if ($px < 1.01) {
            $haveAll = false;
            break;
        }
        $prices[$oi] = $px;
    }
    // Fallback: 2-way scraper snapshot when the Odds-API feed lacks Pinnacle.
    if (!$haveAll && $nOut === 2 && $bucket !== null) {
        $snap = sports_value_pinnacle_snapshot_lookup_for_bucket($bucket);
        if ($snap !== null) {
            // Snapshot is keyed home/away; map to outList outcome order.
            $homeName = isset($bucket['home_team']) ? strtolower(strval($bucket['home_team'])) : '';
            $awayName = isset($bucket['away_team']) ? strtolower(strval($bucket['away_team'])) : '';
            $oc0 = strtolower(strval(isset($outList[0]['outcome_name']) ? $outList[0]['outcome_name'] : ''));
            $oc1 = strtolower(strval(isset($outList[1]['outcome_name']) ? $outList[1]['outcome_name'] : ''));
            $hd = $snap[0];
            $ad = $snap[1];
            if ($oc0 === $homeName && $oc1 === $awayName) {
                $prices = array($hd, $ad);
                $haveAll = true;
            } else if ($oc0 === $awayName && $oc1 === $homeName) {
                $prices = array($ad, $hd);
                $haveAll = true;
            }
        }
    }
    if (!$haveAll) {
        return null;
    }
    $shin = sports_value_devig_shin($prices);
    if ($shin !== null) {
        return $shin;
    }
    // Final fallback: proportional inverse-normalize (legacy behavior).
    $sum = 0.0;
    $inv = array();
    foreach ($prices as $px) {
        $inv[] = 1.0 / $px;
        $sum += 1.0 / $px;
    }
    if ($sum <= 0.00001) {
        return null;
    }
    $truep = array();
    foreach ($inv as $v) {
        $truep[] = $v / $sum;
    }
    return $truep;
}

/**
 * @param resource $mysqli
 * @param float $bankroll
 * @param float $min_ev_pct
 * @param string $sport_filter
 * @param string $asOfStr  Empty (default) = production: use NOW() and wall-clock detected_at.
 *                         Non-empty (e.g. '2024-03-15 18:00:00') = backtest: time-travel
 *                         the analyzer so commence_time comparisons + detected_at use this
 *                         instant. Used by sports_value_analyze_cli.php for retro-runs.
 * @param string $oddsTable        Default 'lm_sports_odds'. Backtest passes 'lm_sports_odds_historical'.
 * @param string $valueBetsTable   Default 'lm_sports_value_bets'. Backtest passes 'lm_sports_synthetic_bets'.
 *                                 When non-default, the expiry sweep + active_count/top queries
 *                                 are skipped (synthetic rows are scoped per backtest_run_id).
 * @param string $extraInsertCols  Optional comma-prefixed column list appended to the INSERT
 *                                 (e.g. ", as_of, is_synthetic, backtest_run_id").
 *                                 SECURITY: this fragment is interpolated into the INSERT
 *                                 verbatim. Callers MUST whitelist column names themselves.
 *                                 Today's only caller (sports_value_analyze_cli.php) passes
 *                                 a fixed string. Do NOT route user input here.
 * @param string $extraInsertVals  Optional comma-prefixed values list matching $extraInsertCols.
 *                                 SECURITY: same warning as $extraInsertCols. The CLI wrapper
 *                                 escapes its inputs via real_escape_string before passing.
 * @return array
 */
function sports_value_analyze_run($mysqli, $bankroll, $min_ev_pct, $sport_filter = '',
                                  $asOfStr = '', $oddsTable = 'lm_sports_odds',
                                  $valueBetsTable = 'lm_sports_value_bets',
                                  $extraInsertCols = '', $extraInsertVals = '') {
    // Defense-in-depth: $oddsTable and $valueBetsTable are interpolated into raw SQL,
    // so the only acceptable values are the two pairs we know about. The CLI wrapper
    // is operator-controlled, but a typo or future caller mistake should not be able
    // to point the analyzer at arbitrary tables.
    $allowedOddsTables = array('lm_sports_odds', 'lm_sports_odds_historical');
    $allowedBetsTables = array('lm_sports_value_bets', 'lm_sports_synthetic_bets');
    if (!in_array($oddsTable, $allowedOddsTables, true) ||
        !in_array($valueBetsTable, $allowedBetsTables, true)) {
        return array(
            'inserted' => 0, 'buckets' => 0, 'expired' => 0, 'active_count' => 0, 'top' => array(),
            'error' => 'disallowed_table_name',
            'odds_table_seen' => $oddsTable, 'bets_table_seen' => $valueBetsTable,
        );
    }
    $result = array(
        'inserted' => 0,
        'buckets' => 0,
        'expired' => 0,
        'active_count' => 0,
        'top' => array(),
    );
    if ($bankroll < 1.0) {
        $bankroll = 1000.0;
    }
    if ($min_ev_pct < 0.1) {
        $min_ev_pct = 1.5;
    }
    $sfEsc = ($sport_filter !== '') ? $mysqli->real_escape_string($sport_filter) : '';

    // Time-travel anchor: in production $asOfStr is empty -> use SQL NOW().
    // In backtest mode, substitute a quoted literal so commence_time comparisons
    // act as if the run is happening at $asOfStr.
    $asOfSql = ($asOfStr === '') ? 'NOW()' : ("'" . $mysqli->real_escape_string($asOfStr) . "'");
    $isBacktest = ($valueBetsTable !== 'lm_sports_value_bets');

    // Skip expiry sweep entirely in backtest mode: synthetic rows are scoped
    // per backtest_run_id and never aged out.
    if (!$isBacktest) {
        // Expire stale active rows whose game already started (past commence_time),
        // AND wipe current future-game active rows so fresh insert can repopulate.
        // Without the past-check, rows from prior refreshes stay "active" forever
        // once commence_time passes, polluting value_bets_found and top_bets.
        if ($sport_filter !== '') {
            // Sport-scoped expiry: only touch rows for this sport so other sports' active bets are unaffected.
            $mysqli->query("UPDATE " . $valueBetsTable . " SET status='expired' WHERE status='active' AND sport LIKE '%" . $sfEsc . "%' AND commence_time < " . $asOfSql);
            $result['expired'] = $mysqli->affected_rows;
            $mysqli->query("UPDATE " . $valueBetsTable . " SET status='expired' WHERE status='active' AND sport LIKE '%" . $sfEsc . "%' AND commence_time >= " . $asOfSql);
            $result['expired'] += $mysqli->affected_rows;
        } else {
            $mysqli->query("UPDATE " . $valueBetsTable . " SET status='expired' WHERE status='active' AND commence_time < " . $asOfSql);
            $result['expired'] = $mysqli->affected_rows;
            $mysqli->query("UPDATE " . $valueBetsTable . " SET status='expired' WHERE status='active' AND commence_time >= " . $asOfSql);
            $result['expired'] += $mysqli->affected_rows;
        }
    }

    $sportWhere = '';
    if ($sport_filter !== '') {
        $sportWhere = " AND sport LIKE '%" . $sfEsc . "%'";
    }
    $q = $mysqli->query(
        "SELECT id, sport, event_id, home_team, away_team, commence_time, bookmaker, bookmaker_key, market, outcome_name, outcome_price, outcome_point "
        . "FROM " . $oddsTable . " WHERE commence_time >= " . $asOfSql . " AND commence_time < DATE_ADD(" . $asOfSql . ", INTERVAL 14 DAY)" . $sportWhere . " ORDER BY id DESC"
    );
    $dedupe = array();
    if ($q) {
        while ($r = $q->fetch_assoc()) {
            $ptKey = '';
            if (isset($r['outcome_point']) && $r['outcome_point'] !== null && $r['outcome_point'] !== '') {
                $ptKey = (string) $r['outcome_point'];
            }
            $k2 = $r['event_id'] . "\x1f" . $r['market'] . "\x1f" . $r['outcome_name'] . "\x1f" . $ptKey . "\x1f" . $r['bookmaker_key'];
            if (isset($dedupe[$k2])) {
                continue;
            }
            $dedupe[$k2] = $r;
        }
    }
    $rows = array_values($dedupe);

    $buckets = array();
    for ($ri = 0; $ri < count($rows); $ri++) {
        $r = $rows[$ri];
        $eid = $r['event_id'];
        $market = $r['market'];
        $lk = sports_value_line_key($market, isset($r['outcome_point']) ? $r['outcome_point'] : null);
        $bk = $eid . "\x1f" . $market . "\x1f" . $lk;
        if (!isset($buckets[$bk])) {
            $buckets[$bk] = array(
                'event_id' => $eid,
                'sport' => $r['sport'],
                'home_team' => $r['home_team'],
                'away_team' => $r['away_team'],
                'commence_time' => $r['commence_time'],
                'market' => $market,
                'outcomes' => array(),
            );
        }
        $ptStr = '';
        if (isset($r['outcome_point']) && $r['outcome_point'] !== null && $r['outcome_point'] !== '') {
            $ptStr = (string) $r['outcome_point'];
        }
        $ok = $r['outcome_name'] . "\x1f" . $ptStr;
        if (!isset($buckets[$bk]['outcomes'][$ok])) {
            $buckets[$bk]['outcomes'][$ok] = array(
                'outcome_name' => $r['outcome_name'],
                'point' => $ptStr,
                'quotes' => array(),
            );
        }
        $price = floatval($r['outcome_price']);
        $bkr = isset($r['bookmaker_key']) ? $r['bookmaker_key'] : '';
        if (!sports_value_quote_usable($bkr, $price)) {
            continue;
        }
        $buckets[$bk]['outcomes'][$ok]['quotes'][] = array(
            'bookmaker' => $r['bookmaker'],
            'bookmaker_key' => $bkr,
            'price' => $price,
        );
    }

    $bucketKeys = array_keys($buckets);
    // In backtest mode anchor detected_at to the as-of instant so synthetic rows
    // reflect the simulated moment, not wall-clock at runner execution.
    $detected = ($asOfStr !== '') ? $asOfStr : date('Y-m-d H:i:s');
    for ($bi = 0; $bi < count($bucketKeys); $bi++) {
        $bkey = $bucketKeys[$bi];
        $bucket = $buckets[$bkey];
        $outcomes = $bucket['outcomes'];
        $outList = array_values($outcomes);
        if (count($outList) < 2) {
            continue;
        }
        $result['buckets']++;

        $nOut = count($outList);
        // Jensen fix: fair probabilities from E[1/odds], not 1/E[odds]. See sports_value_truep_consensus_jensen.
        $truepBase = sports_value_truep_consensus_jensen($outList, $nOut, null);
        if ($truepBase === null) {
            continue;
        }
        // When Pinnacle quotes every outcome, anchor "true" prob to sharp de-vig only (soft books vs Pinnacle).
        // Now applies Shin devig (sharper than proportional inverse) and falls back to the
        // tools/pinnacle_anchor_scrape.py snapshot for 2-way buckets when the Odds-API feed
        // lacks Pinnacle. See sports_value_truep_pinnacle / sports_value_devig_shin /
        // sports_value_load_pinnacle_snapshot above.
        $truepPin = sports_value_truep_pinnacle($outList, $nOut, $bucket);

        // NHL goalie overlay (Phase 2): for h2h 2-way buckets where both starters
        // are confirmed and have GP >= 10, shift the Shin/Jensen home prob by a
        // capped GSAx/60 delta. Graceful no-op when the JSON feed is missing or
        // outcome names don't map cleanly to home_team/away_team.
        // Spec: updates/2026-04-26-nhl-goalie-overlay-wiring-plan.md
        if ($truepPin !== null && $nOut === 2
                && strtolower(strval($bucket['market'])) === 'h2h'
                && strpos(strval($bucket['sport']), 'icehockey_nhl') !== false) {
            $oc0 = strtolower(strval(isset($outList[0]['outcome_name']) ? $outList[0]['outcome_name'] : ''));
            $oc1 = strtolower(strval(isset($outList[1]['outcome_name']) ? $outList[1]['outcome_name'] : ''));
            $homeName = strtolower(strval($bucket['home_team']));
            $awayName = strtolower(strval($bucket['away_team']));
            $homeIdx = -1;
            if ($oc0 === $homeName && $oc1 === $awayName) {
                $homeIdx = 0;
            } else if ($oc0 === $awayName && $oc1 === $homeName) {
                $homeIdx = 1;
            }
            if ($homeIdx >= 0) {
                $awayIdx = 1 - $homeIdx;
                $pHome = floatval($truepPin[$homeIdx]);
                $ov = sports_value_nhl_goalie_apply_overlay($pHome, $bucket);
                if (isset($ov[2]) && $ov[2]) {
                    $truepPin[$homeIdx] = floatval($ov[0]);
                    $truepPin[$awayIdx] = 1.0 - floatval($ov[0]);
                }
            }
        }

        $consImp = array();
        for ($oi = 0; $oi < $nOut; $oi++) {
            $qs = $outList[$oi]['quotes'];
            if (count($qs) < 1) {
                $consImp[$oi] = 0.0;
            } else {
                $sx = 0.0;
                $nu = 0;
                for ($qj = 0; $qj < count($qs); $qj++) {
                    if (!sports_value_quote_usable($qs[$qj]['bookmaker_key'], $qs[$qj]['price'])) {
                        continue;
                    }
                    $sx += 1.0 / $qs[$qj]['price'];
                    $nu++;
                }
                $consImp[$oi] = ($nu > 0) ? ($sx / $nu) : 0.0;
            }
        }

        for ($oi = 0; $oi < $nOut; $oi++) {
            $qs = $outList[$oi]['quotes'];
            // NBA/NHL: often only 2 books in time. CFL/MLS: thinner coverage — 2 books or we skip everything.
            $sportKey = isset($bucket['sport']) ? $bucket['sport'] : '';
            $minBooks = 3;
            if (strpos($sportKey, 'basketball_nba') !== false || strpos($sportKey, 'icehockey_nhl') !== false) {
                $minBooks = 2;
            } else if (strpos($sportKey, 'americanfootball_cfl') !== false || strpos($sportKey, 'soccer_usa_mls') !== false) {
                $minBooks = 2;
            }
            if (count($qs) < $minBooks) {
                continue;
            }
            $cq = $consImp[$oi];
            $quotesSorted = $qs;
            usort($quotesSorted, 'sports_value_sort_quotes_desc');
            $allJson = sports_value_all_odds_json($quotesSorted);

            for ($qj = 0; $qj < count($qs); $qj++) {
                $quote = $qs[$qj];
                $price = $quote['price'];
                if (!sports_value_quote_usable($quote['bookmaker_key'], $price)) {
                    continue;
                }
                $bk = $quote['bookmaker_key'];
                $p = 0.0;
                if ($truepPin !== null && !sports_value_book_is_pinnacle($bk)) {
                    $p = $truepPin[$oi];
                } else {
                    $tloo = sports_value_truep_consensus_jensen($outList, $nOut, $bk);
                    if ($tloo !== null) {
                        $p = $tloo[$oi];
                    } else {
                        $p = $truepBase[$oi];
                    }
                }
                $ev = ($p * $price - 1.0) * 100.0;
                if ($ev < $min_ev_pct) {
                    continue;
                }
                $edge = $ev;
                $denom = $price - 1.0;
                $kfull = 0.0;
                if ($denom > 0.00001) {
                    $kfull = ($p * $price - 1.0) / $denom;
                }
                if ($kfull < 0.0) {
                    $kfull = 0.0;
                }
                $kfrac = $kfull * 0.25;
                $kbet = round($kfrac * $bankroll, 2);
                if ($kbet > 50.0) {
                    $kbet = 50.0;
                }

                $ptRaw = $outList[$oi]['point'];
                $ptUse = ($ptRaw !== '') ? $ptRaw : null;
                $betType = sports_value_bet_type_label($bucket['market'], $outList[$oi]['outcome_name'], $ptUse);
                if (strlen($betType) > 50) {
                    $mshort = strtolower($bucket['market']);
                    if ($mshort === 'h2h') {
                        $on = $outList[$oi]['outcome_name'];
                        $suffix = ' ML';
                        $maxO = 50 - strlen($suffix);
                        if ($maxO < 10) {
                            $maxO = 10;
                        }
                        $betType = substr($on, 0, $maxO) . $suffix;
                    } else {
                        $betType = substr($betType, 0, 50);
                    }
                }

                $eidEsc = $mysqli->real_escape_string($bucket['event_id']);
                $statusCol = $isBacktest ? '' : ', status';
                $statusVal = $isBacktest ? '' : ",'active'";
                $ins = "INSERT INTO " . $valueBetsTable . " (event_id, sport, home_team, away_team, commence_time, market, bet_type, outcome_name, best_book, best_book_key, best_odds, consensus_implied_prob, true_prob, edge_pct, ev_pct, kelly_fraction, kelly_bet, all_odds, detected_at" . $statusCol . $extraInsertCols . ") VALUES ('"
                    . $eidEsc . "','"
                    . $mysqli->real_escape_string($bucket['sport']) . "','"
                    . $mysqli->real_escape_string($bucket['home_team']) . "','"
                    . $mysqli->real_escape_string($bucket['away_team']) . "','"
                    . $mysqli->real_escape_string($bucket['commence_time']) . "','"
                    . $mysqli->real_escape_string($bucket['market']) . "','"
                    . $mysqli->real_escape_string($betType) . "','"
                    . $mysqli->real_escape_string($outList[$oi]['outcome_name']) . "','"
                    . $mysqli->real_escape_string($quote['bookmaker']) . "','"
                    . $mysqli->real_escape_string($quote['bookmaker_key']) . "',"
                    . round($price, 4) . ","
                    . round($cq, 4) . ","
                    . round($p, 4) . ","
                    . round($edge, 2) . ","
                    . round($ev, 2) . ","
                    . round($kfrac, 4) . ","
                    . round($kbet, 2) . ",'"
                    . $mysqli->real_escape_string($allJson) . "','"
                    . $mysqli->real_escape_string($detected) . "'" . $statusVal . $extraInsertVals . ")";
                if ($mysqli->query($ins)) {
                    $result['inserted']++;
                }
            }
        }
    }

    // Skip status-based summary in backtest mode (synthetic table has no `status` col).
    if (!$isBacktest) {
        $nr = $mysqli->query("SELECT COUNT(*) AS c FROM " . $valueBetsTable . " WHERE status = 'active'");
        if ($nr && ($row = $nr->fetch_assoc())) {
            $result['active_count'] = intval($row['c']);
        }

        $tr = $mysqli->query("SELECT event_id, sport, bet_type, best_book, best_odds, ev_pct FROM " . $valueBetsTable . " WHERE status = 'active' ORDER BY ev_pct DESC LIMIT 8");
        if ($tr) {
            while ($trow = $tr->fetch_assoc()) {
                $result['top'][] = array(
                    'event_id' => $trow['event_id'],
                    'sport' => $trow['sport'],
                    'bet_type' => $trow['bet_type'],
                    'best_book' => $trow['best_book'],
                    'best_odds' => floatval($trow['best_odds']),
                    'ev_pct' => floatval($trow['ev_pct']),
                );
            }
        }
    }

    return $result;
}
