<?php
/**
 * strategy_arena.php — Rapid Strategy Tournament for Sports Betting
 * PHP 5.2 compatible. No short arrays, no closures, no ?:, no ??, no __DIR__.
 *
 * Runs 25 distinct betting strategies in parallel, each with its own $1000
 * virtual bankroll. Filters the same value bets through different lenses,
 * auto-places virtual bets, auto-settles via scores, and produces a live
 * leaderboard so you can see within days/weeks which approach actually works.
 *
 * Actions:
 *   ?action=init&key=...           — Initialize strategies + tables (admin, idempotent)
 *   ?action=run&key=...            — Full cycle: filter → place → settle (admin)
 *   ?action=leaderboard            — Ranked strategies by ROI (public)
 *   ?action=strategy&id=X          — Detail for one strategy (public)
 *   ?action=history&id=X[&limit=N] — Bet history for one strategy (public)
 *   ?action=eliminate&key=...      — Auto-eliminate statistical losers (admin)
 *   ?action=snapshot&key=...       — Take daily performance snapshot (admin)
 *   ?action=status                 — Arena health check (public)
 *   ?action=reset&key=...&confirm=yes — Nuclear reset (admin)
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';
require_once dirname(__FILE__) . '/sports_scores.php';

$ADMIN_KEY = isset($SPORTS_ADMIN_KEY) ? $SPORTS_ADMIN_KEY : 'livetrader2026';

// ════════════════════════════════════════════════════════════
//  Schema — auto-create tables
// ════════════════════════════════════════════════════════════

$conn->query("CREATE TABLE IF NOT EXISTS lm_arena_strategies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(40) NOT NULL,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(40) NOT NULL DEFAULT 'general',
    description TEXT,
    filters_json TEXT,
    sizing_method VARCHAR(30) NOT NULL DEFAULT 'quarter_kelly',
    sizing_param DECIMAL(6,4) NOT NULL DEFAULT 0.25,
    flat_amount DECIMAL(8,2) NOT NULL DEFAULT 25.00,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL,
    eliminated_at DATETIME DEFAULT NULL,
    elimination_reason TEXT,
    UNIQUE KEY idx_slug (slug)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS lm_arena_bankrolls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id INT NOT NULL,
    bankroll DECIMAL(12,2) NOT NULL DEFAULT 1000.00,
    initial_bankroll DECIMAL(12,2) NOT NULL DEFAULT 1000.00,
    total_bets INT NOT NULL DEFAULT 0,
    total_wins INT NOT NULL DEFAULT 0,
    total_losses INT NOT NULL DEFAULT 0,
    total_pushes INT NOT NULL DEFAULT 0,
    total_wagered DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    total_pnl DECIMAL(12,2) NOT NULL DEFAULT 0.00,
    roi_pct DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    win_rate DECIMAL(6,2) NOT NULL DEFAULT 0.00,
    peak_bankroll DECIMAL(12,2) NOT NULL DEFAULT 1000.00,
    trough_bankroll DECIMAL(12,2) NOT NULL DEFAULT 1000.00,
    max_drawdown_pct DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    current_streak INT NOT NULL DEFAULT 0,
    best_streak INT NOT NULL DEFAULT 0,
    worst_streak INT NOT NULL DEFAULT 0,
    avg_odds DECIMAL(8,4) NOT NULL DEFAULT 0.0000,
    avg_ev DECIMAL(8,4) NOT NULL DEFAULT 0.0000,
    avg_bet_size DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    last_bet_at DATETIME DEFAULT NULL,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_strat (strategy_id)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS lm_arena_bets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id INT NOT NULL,
    event_id VARCHAR(100) NOT NULL,
    sport VARCHAR(50) NOT NULL DEFAULT '',
    home_team VARCHAR(100) NOT NULL DEFAULT '',
    away_team VARCHAR(100) NOT NULL DEFAULT '',
    commence_time DATETIME DEFAULT NULL,
    market VARCHAR(20) NOT NULL DEFAULT 'h2h',
    pick VARCHAR(100) NOT NULL DEFAULT '',
    pick_point DECIMAL(6,2) DEFAULT NULL,
    bookmaker VARCHAR(60) NOT NULL DEFAULT '',
    odds DECIMAL(10,4) NOT NULL DEFAULT 0.0000,
    implied_prob DECIMAL(6,4) NOT NULL DEFAULT 0.0000,
    ev_pct DECIMAL(6,2) NOT NULL DEFAULT 0.00,
    bet_amount DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    potential_payout DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    rating_grade VARCHAR(5) NOT NULL DEFAULT '',
    rating_score INT NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result VARCHAR(20) DEFAULT NULL,
    pnl DECIMAL(10,2) DEFAULT NULL,
    actual_home_score INT DEFAULT NULL,
    actual_away_score INT DEFAULT NULL,
    placed_at DATETIME NOT NULL,
    settled_at DATETIME DEFAULT NULL,
    KEY idx_strat_status (strategy_id, status),
    KEY idx_event (event_id),
    KEY idx_placed (placed_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS lm_arena_snapshots (
    id INT AUTO_INCREMENT PRIMARY KEY,
    strategy_id INT NOT NULL,
    snapshot_date DATE NOT NULL,
    bankroll DECIMAL(12,2) NOT NULL DEFAULT 1000.00,
    total_bets INT NOT NULL DEFAULT 0,
    roi_pct DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    win_rate DECIMAL(6,2) NOT NULL DEFAULT 0.00,
    sharpe_ratio DECIMAL(8,4) DEFAULT NULL,
    max_drawdown_pct DECIMAL(8,2) NOT NULL DEFAULT 0.00,
    UNIQUE KEY idx_strat_date (strategy_id, snapshot_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");


// ════════════════════════════════════════════════════════════
//  Action routing
// ════════════════════════════════════════════════════════════

header('Content-Type: application/json');
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'leaderboard';

if ($action === 'init')        { _arena_init($conn); }
elseif ($action === 'run')     { _arena_run($conn); }
elseif ($action === 'leaderboard') { _arena_leaderboard($conn); }
elseif ($action === 'strategy')    { _arena_strategy_detail($conn); }
elseif ($action === 'history')     { _arena_bet_history($conn); }
elseif ($action === 'eliminate')   { _arena_eliminate($conn); }
elseif ($action === 'snapshot')    { _arena_snapshot($conn); }
elseif ($action === 'status')      { _arena_status($conn); }
elseif ($action === 'reset')       { _arena_reset($conn); }
else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;


// ════════════════════════════════════════════════════════════
//  STRATEGY DEFINITIONS (25 strategies across 8 categories)
// ════════════════════════════════════════════════════════════

function _arena_get_strategy_defs() {
    return array(
        // ── Category 1: EV Threshold Variants ──
        array(
            'slug' => 'ev_loose',
            'name' => 'EV Loose (>1%)',
            'category' => 'ev_threshold',
            'description' => 'Accept any value bet with EV above 1%. High volume, lower selectivity.',
            'filters' => array('min_ev' => 1.0),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'ev_standard',
            'name' => 'EV Standard (>2%)',
            'category' => 'ev_threshold',
            'description' => 'Current default: EV above 2%. Baseline comparison.',
            'filters' => array('min_ev' => 2.0),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'ev_strict',
            'name' => 'EV Strict (>4%)',
            'category' => 'ev_threshold',
            'description' => 'Only higher-edge bets with EV above 4%.',
            'filters' => array('min_ev' => 4.0),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'ev_elite',
            'name' => 'EV Elite (>6%)',
            'category' => 'ev_threshold',
            'description' => 'Only the highest EV bets. Low volume but potentially high edge.',
            'filters' => array('min_ev' => 6.0),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),

        // ── Category 2: Market Specialists ──
        array(
            'slug' => 'moneyline_only',
            'name' => 'Moneyline Only',
            'category' => 'market',
            'description' => 'Only bet on h2h (moneyline) markets. Most straightforward.',
            'filters' => array('min_ev' => 2.0, 'markets' => array('h2h')),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'spread_only',
            'name' => 'Spreads Only',
            'category' => 'market',
            'description' => 'Only bet on point spreads. Tests spread-specific edge.',
            'filters' => array('min_ev' => 2.0, 'markets' => array('spreads')),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'totals_only',
            'name' => 'Totals Only',
            'category' => 'market',
            'description' => 'Only bet on over/under totals.',
            'filters' => array('min_ev' => 2.0, 'markets' => array('totals')),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),

        // ── Category 3: Sport Specialists ──
        array(
            'slug' => 'nba_specialist',
            'name' => 'NBA Specialist',
            'category' => 'sport',
            'description' => 'Only NBA games. Tests if NBA-specific edge exists.',
            'filters' => array('min_ev' => 2.0, 'sports' => array('basketball_nba')),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'nhl_specialist',
            'name' => 'NHL Specialist',
            'category' => 'sport',
            'description' => 'Only NHL games. Hockey-specific testing.',
            'filters' => array('min_ev' => 2.0, 'sports' => array('icehockey_nhl')),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'ncaab_specialist',
            'name' => 'NCAAB Specialist',
            'category' => 'sport',
            'description' => 'Only college basketball. Often has more inefficient lines.',
            'filters' => array('min_ev' => 2.0, 'sports' => array('basketball_ncaab')),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'mlb_specialist',
            'name' => 'MLB Specialist',
            'category' => 'sport',
            'description' => 'Only MLB games. Baseball moneyline/totals focus.',
            'filters' => array('min_ev' => 2.0, 'sports' => array('baseball_mlb')),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),

        // ── Category 4: Consensus/Sharp Filters ──
        array(
            'slug' => 'high_consensus',
            'name' => 'High Consensus (10+ books)',
            'category' => 'consensus',
            'description' => 'Only bets where 10+ bookmakers offer odds. Strong market consensus.',
            'filters' => array('min_ev' => 2.0, 'min_books' => 10),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'canadian_only',
            'name' => 'Canadian Books Only',
            'category' => 'consensus',
            'description' => 'Only picks available at Canadian-legal sportsbooks.',
            'filters' => array('min_ev' => 2.0, 'canadian_book_required' => true),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),

        // ── Category 5: Sizing Variants ──
        array(
            'slug' => 'half_kelly',
            'name' => 'Half Kelly (aggressive)',
            'category' => 'sizing',
            'description' => 'Same filters as standard but double the bet sizing. Tests aggressive Kelly.',
            'filters' => array('min_ev' => 2.0),
            'sizing' => 'half_kelly', 'sizing_param' => 0.50
        ),
        array(
            'slug' => 'eighth_kelly',
            'name' => 'Eighth Kelly (conservative)',
            'category' => 'sizing',
            'description' => 'Same filters as standard but half the bet sizing. Tests conservative Kelly.',
            'filters' => array('min_ev' => 2.0),
            'sizing' => 'eighth_kelly', 'sizing_param' => 0.125
        ),
        array(
            'slug' => 'flat_25',
            'name' => 'Flat $25 Bets',
            'category' => 'sizing',
            'description' => 'Fixed $25 per bet regardless of edge. Tests unit betting vs Kelly.',
            'filters' => array('min_ev' => 2.0),
            'sizing' => 'flat', 'sizing_param' => 0.0, 'flat_amount' => 25.00
        ),
        array(
            'slug' => 'flat_50',
            'name' => 'Flat $50 Bets',
            'category' => 'sizing',
            'description' => 'Fixed $50 per bet. Higher risk flat betting.',
            'filters' => array('min_ev' => 2.0),
            'sizing' => 'flat', 'sizing_param' => 0.0, 'flat_amount' => 50.00
        ),

        // ── Category 6: Rating / ML Filtered ──
        array(
            'slug' => 'a_grade_plus',
            'name' => 'A Grade+ Only',
            'category' => 'rating',
            'description' => 'Only A or A+ rated bets (score >= 80). Quality over quantity.',
            'filters' => array('min_ev' => 2.0, 'min_rating_score' => 80),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'strong_take',
            'name' => 'STRONG TAKE Only',
            'category' => 'rating',
            'description' => 'Only bets rated STRONG TAKE (score >= 80). Most selective rating filter.',
            'filters' => array('min_ev' => 2.0, 'min_rating_score' => 80, 'recommendation' => 'STRONG TAKE'),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'b_plus_up',
            'name' => 'B+ and Above',
            'category' => 'rating',
            'description' => 'B+ or better rated bets (score >= 70). Moderate selectivity.',
            'filters' => array('min_ev' => 2.0, 'min_rating_score' => 70),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),

        // ── Category 7: Timing / Situation ──
        array(
            'slug' => 'early_line',
            'name' => 'Early Lines (12h+ out)',
            'category' => 'timing',
            'description' => 'Only bet on games 12+ hours away. Avoids late line moves.',
            'filters' => array('min_ev' => 2.0, 'min_hours_to_game' => 12),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'underdog_value',
            'name' => 'Underdog Value',
            'category' => 'situation',
            'description' => 'Only underdogs (odds > 2.20) with EV. Tests underdog bias theory.',
            'filters' => array('min_ev' => 2.0, 'min_odds' => 2.20),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'favorite_grind',
            'name' => 'Favorite Grind',
            'category' => 'situation',
            'description' => 'Only favorites (odds < 2.00) with EV. Low-odds high win-rate approach.',
            'filters' => array('min_ev' => 2.0, 'max_odds' => 2.00),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),

        // ── Category 8: Combo Strategies (best of multiple filters) ──
        array(
            'slug' => 'premium_combo',
            'name' => 'Premium Combo',
            'category' => 'combo',
            'description' => 'EV>3% + A-grade+ + Canadian book available. The "best of everything" filter.',
            'filters' => array(
                'min_ev' => 3.0,
                'min_rating_score' => 80,
                'canadian_book_required' => true
            ),
            'sizing' => 'quarter_kelly', 'sizing_param' => 0.25
        ),
        array(
            'slug' => 'volume_grind',
            'name' => 'Volume Grind',
            'category' => 'combo',
            'description' => 'EV>1% + flat $15 bets + any market. Maximum volume, minimum risk per bet.',
            'filters' => array('min_ev' => 1.0),
            'sizing' => 'flat', 'sizing_param' => 0.0, 'flat_amount' => 15.00
        )
    );
}


// ════════════════════════════════════════════════════════════
//  ACTION: init — Seed strategies into DB (idempotent)
// ════════════════════════════════════════════════════════════

function _arena_init($conn) {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $defs = _arena_get_strategy_defs();
    $created = 0;
    $existing = 0;
    $now = gmdate('Y-m-d H:i:s');

    foreach ($defs as $d) {
        $slug = $conn->real_escape_string($d['slug']);

        // Check if exists
        $check = $conn->query("SELECT id FROM lm_arena_strategies WHERE slug='" . $slug . "'");
        if ($check && $check->num_rows > 0) {
            $existing++;
            continue;
        }

        $filters_json = $conn->real_escape_string(json_encode($d['filters']));
        $flat = isset($d['flat_amount']) ? (float)$d['flat_amount'] : 25.00;

        $conn->query("INSERT INTO lm_arena_strategies (slug, name, category, description, filters_json, sizing_method, sizing_param, flat_amount, status, created_at) VALUES ("
            . "'" . $slug . "', "
            . "'" . $conn->real_escape_string($d['name']) . "', "
            . "'" . $conn->real_escape_string($d['category']) . "', "
            . "'" . $conn->real_escape_string($d['description']) . "', "
            . "'" . $filters_json . "', "
            . "'" . $conn->real_escape_string($d['sizing']) . "', "
            . (float)$d['sizing_param'] . ", "
            . $flat . ", "
            . "'active', "
            . "'" . $now . "')");

        $strat_id = $conn->insert_id;

        // Create bankroll record
        $conn->query("INSERT INTO lm_arena_bankrolls (strategy_id, bankroll, initial_bankroll, updated_at) VALUES ("
            . $strat_id . ", 1000.00, 1000.00, '" . $now . "')");

        $created++;
    }

    echo json_encode(array(
        'ok' => true,
        'created' => $created,
        'existing' => $existing,
        'total_strategies' => $created + $existing
    ));
}


// ════════════════════════════════════════════════════════════
//  ACTION: run — Full cycle: filter → place → settle
// ════════════════════════════════════════════════════════════

function _arena_run($conn) {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $results = array(
        'settled' => _arena_settle_bets($conn),
        'placed'  => _arena_place_bets($conn)
    );

    echo json_encode(array(
        'ok' => true,
        'cycle' => $results,
        'ran_at' => gmdate('Y-m-d H:i:s') . ' UTC'
    ));
}


// ────────────────────────────────────────────────────────────
//  Place bets: fetch value bets, apply each strategy's filter
// ────────────────────────────────────────────────────────────

function _arena_place_bets($conn) {
    // Fetch active value bets (upcoming games only)
    $vb_q = $conn->query("SELECT * FROM lm_sports_value_bets WHERE status='active' AND commence_time > NOW() AND ev_pct >= 1.0 ORDER BY ev_pct DESC LIMIT 100");
    if (!$vb_q) return array('error' => 'Value bets query failed');

    $value_bets = array();
    while ($row = $vb_q->fetch_assoc()) {
        // Parse all_odds JSON for book count
        $all_odds = json_decode($row['all_odds'], true);
        $row['book_count'] = is_array($all_odds) ? count($all_odds) : 0;
        $row['all_odds_parsed'] = $all_odds;

        // Check Canadian book availability
        $canadian_books = array('bet365', 'fanduel', 'draftkings', 'betmgm', 'pointsbetus', 'williamhill_us', 'betrivers', 'espnbet', 'fanatics');
        $has_canadian = false;
        if (is_array($all_odds)) {
            foreach ($all_odds as $book_info) {
                $bk = isset($book_info['bookmaker_key']) ? $book_info['bookmaker_key'] : '';
                if (in_array($bk, $canadian_books)) {
                    $has_canadian = true;
                    break;
                }
            }
        }
        $row['has_canadian_book'] = $has_canadian;

        // Calculate hours to game
        $commence_ts = strtotime($row['commence_time']);
        $row['hours_to_game'] = ($commence_ts > 0) ? ($commence_ts - time()) / 3600.0 : 0;

        // Apply rating score inline
        _arena_apply_rating($row);

        $value_bets[] = $row;
    }

    if (count($value_bets) === 0) {
        return array('value_bets_available' => 0, 'bets_placed' => 0);
    }

    // Fetch active strategies + bankrolls
    $strat_q = $conn->query("SELECT s.*, b.bankroll, b.total_bets FROM lm_arena_strategies s "
        . "JOIN lm_arena_bankrolls b ON b.strategy_id = s.id "
        . "WHERE s.status='active'");
    if (!$strat_q) return array('error' => 'Strategy query failed');

    $total_placed = 0;
    $total_skipped = 0;
    $by_strategy = array();

    while ($strat = $strat_q->fetch_assoc()) {
        $strat_id = (int)$strat['id'];
        $bankroll = (float)$strat['bankroll'];
        $filters = json_decode($strat['filters_json'], true);
        if (!is_array($filters)) $filters = array();

        $placed = 0;
        $skipped = 0;
        $max_bets_per_run = 5;

        foreach ($value_bets as $vb) {
            if ($placed >= $max_bets_per_run) break;

            // Check if already bet on this event for this strategy
            $dup_q = $conn->query("SELECT id FROM lm_arena_bets WHERE strategy_id=" . $strat_id
                . " AND event_id='" . $conn->real_escape_string($vb['event_id']) . "'"
                . " AND market='" . $conn->real_escape_string($vb['market']) . "'"
                . " AND pick='" . $conn->real_escape_string($vb['outcome_name']) . "'");
            if ($dup_q && $dup_q->num_rows > 0) {
                continue;
            }

            // Apply strategy filters
            if (!_arena_passes_filter($vb, $filters)) {
                $skipped++;
                continue;
            }

            // Calculate bet amount
            $bet_amount = _arena_calc_bet_size($vb, $strat, $bankroll);
            if ($bet_amount < 5.0 || $bet_amount > $bankroll * 0.10) {
                $skipped++;
                continue;
            }

            // Place the virtual bet
            $odds = (float)$vb['best_odds'];
            $payout = $bet_amount * $odds;
            $ip = ($odds > 0) ? 1.0 / $odds : 0;
            $now = gmdate('Y-m-d H:i:s');
            $pp = isset($vb['outcome_point']) ? (float)$vb['outcome_point'] : 0;

            $conn->query("INSERT INTO lm_arena_bets "
                . "(strategy_id, event_id, sport, home_team, away_team, commence_time, "
                . "market, pick, pick_point, bookmaker, odds, implied_prob, ev_pct, "
                . "bet_amount, potential_payout, rating_grade, rating_score, status, placed_at) VALUES ("
                . $strat_id . ", "
                . "'" . $conn->real_escape_string($vb['event_id']) . "', "
                . "'" . $conn->real_escape_string($vb['sport']) . "', "
                . "'" . $conn->real_escape_string($vb['home_team']) . "', "
                . "'" . $conn->real_escape_string($vb['away_team']) . "', "
                . "'" . $conn->real_escape_string($vb['commence_time']) . "', "
                . "'" . $conn->real_escape_string($vb['market']) . "', "
                . "'" . $conn->real_escape_string($vb['outcome_name']) . "', "
                . ($pp != 0 ? $pp : 'NULL') . ", "
                . "'" . $conn->real_escape_string($vb['best_book']) . "', "
                . $odds . ", "
                . round($ip, 4) . ", "
                . (float)$vb['ev_pct'] . ", "
                . round($bet_amount, 2) . ", "
                . round($payout, 2) . ", "
                . "'" . $conn->real_escape_string(isset($vb['rating_grade']) ? $vb['rating_grade'] : '') . "', "
                . (int)(isset($vb['rating_score']) ? $vb['rating_score'] : 0) . ", "
                . "'pending', "
                . "'" . $now . "')");

            $placed++;
            $total_placed++;
        }

        $total_skipped += $skipped;
        if ($placed > 0) {
            $by_strategy[] = array('strategy' => $strat['slug'], 'placed' => $placed, 'skipped' => $skipped);
        }
    }

    return array(
        'value_bets_available' => count($value_bets),
        'bets_placed' => $total_placed,
        'bets_skipped' => $total_skipped,
        'by_strategy' => $by_strategy
    );
}


// ────────────────────────────────────────────────────────────
//  Settle bets: match completed games to pending bets
// ────────────────────────────────────────────────────────────

function _arena_settle_bets($conn) {
    // Fetch pending bets where game should be over
    $pending_q = $conn->query("SELECT * FROM lm_arena_bets WHERE status='pending' AND commence_time < DATE_SUB(NOW(), INTERVAL 3 HOUR) ORDER BY commence_time ASC LIMIT 200");
    if (!$pending_q) return array('error' => 'Pending bets query failed');

    $pending = array();
    while ($row = $pending_q->fetch_assoc()) {
        $pending[] = $row;
    }

    if (count($pending) === 0) {
        return array('pending_checked' => 0, 'settled' => 0);
    }

    // Group by sport for score fetching
    $by_sport = array();
    foreach ($pending as $bet) {
        $sport = $bet['sport'];
        if (!isset($by_sport[$sport])) $by_sport[$sport] = array();
        $by_sport[$sport][] = $bet;
    }

    // Fetch scores
    $all_scores = array();
    foreach (array_keys($by_sport) as $sport) {
        if (function_exists('_scores_fetch_all')) {
            $scores = _scores_fetch_all($sport, 3);
            if (is_array($scores)) {
                foreach ($scores as $sc) {
                    $key = $sc['home_team'] . ' vs ' . $sc['away_team'];
                    $all_scores[$key] = $sc;
                    // Also index by event_id if available
                    if (isset($sc['event_id'])) {
                        $all_scores[$sc['event_id']] = $sc;
                    }
                }
            }
        }
    }

    $settled = 0;
    $won = 0;
    $lost = 0;
    $push = 0;
    $voided = 0;
    $now = gmdate('Y-m-d H:i:s');

    foreach ($pending as $bet) {
        $bet_id = (int)$bet['id'];
        $strat_id = (int)$bet['strategy_id'];

        // Try to find score
        $score = null;
        if (isset($all_scores[$bet['event_id']])) {
            $score = $all_scores[$bet['event_id']];
        }

        // Fuzzy match by team names
        if (!$score) {
            foreach ($all_scores as $sc) {
                if (_arena_team_match($bet['home_team'], isset($sc['home_team']) ? $sc['home_team'] : '')
                    && _arena_team_match($bet['away_team'], isset($sc['away_team']) ? $sc['away_team'] : '')) {
                    $score = $sc;
                    break;
                }
            }
        }

        if (!$score || !isset($score['home_score']) || !isset($score['away_score'])) {
            // Void bets older than 48h that can't be settled
            $ct = strtotime($bet['commence_time']);
            if ($ct && (time() - $ct) > 48 * 3600) {
                $conn->query("UPDATE lm_arena_bets SET status='voided', settled_at='" . $now . "' WHERE id=" . $bet_id);
                $voided++;
            }
            continue;
        }

        $home_score = (int)$score['home_score'];
        $away_score = (int)$score['away_score'];
        $result = _arena_determine_result($bet, $home_score, $away_score);

        $pnl = 0.0;
        $bet_amount = (float)$bet['bet_amount'];
        $odds = (float)$bet['odds'];

        if ($result === 'won') {
            $pnl = ($odds - 1) * $bet_amount;
            $won++;
        } elseif ($result === 'lost') {
            $pnl = -$bet_amount;
            $lost++;
        } else {
            $pnl = 0.0;
            $push++;
        }

        // Update bet
        $conn->query("UPDATE lm_arena_bets SET status='settled', result='" . $conn->real_escape_string($result) . "', "
            . "pnl=" . round($pnl, 2) . ", "
            . "actual_home_score=" . $home_score . ", actual_away_score=" . $away_score . ", "
            . "settled_at='" . $now . "' WHERE id=" . $bet_id);

        // Update bankroll
        _arena_update_bankroll($conn, $strat_id, $result, $pnl, $bet_amount, $odds, (float)$bet['ev_pct']);

        $settled++;
    }

    return array(
        'pending_checked' => count($pending),
        'settled' => $settled,
        'won' => $won,
        'lost' => $lost,
        'push' => $push,
        'voided' => $voided,
        'scores_found' => count($all_scores)
    );
}


// ────────────────────────────────────────────────────────────
//  Filter logic: does a value bet pass a strategy's filters?
// ────────────────────────────────────────────────────────────

function _arena_passes_filter($vb, $filters) {
    // Min EV
    $min_ev = isset($filters['min_ev']) ? (float)$filters['min_ev'] : 2.0;
    if ((float)$vb['ev_pct'] < $min_ev) return false;

    // Market filter
    if (isset($filters['markets']) && is_array($filters['markets'])) {
        if (!in_array($vb['market'], $filters['markets'])) return false;
    }

    // Sport filter
    if (isset($filters['sports']) && is_array($filters['sports'])) {
        if (!in_array($vb['sport'], $filters['sports'])) return false;
    }

    // Min books
    if (isset($filters['min_books'])) {
        if ($vb['book_count'] < (int)$filters['min_books']) return false;
    }

    // Canadian book required
    if (isset($filters['canadian_book_required']) && $filters['canadian_book_required']) {
        if (!$vb['has_canadian_book']) return false;
    }

    // Min rating score
    if (isset($filters['min_rating_score'])) {
        $rs = isset($vb['rating_score']) ? (int)$vb['rating_score'] : 0;
        if ($rs < (int)$filters['min_rating_score']) return false;
    }

    // Recommendation filter
    if (isset($filters['recommendation'])) {
        $rec = isset($vb['recommendation']) ? $vb['recommendation'] : '';
        if ($rec !== $filters['recommendation']) return false;
    }

    // Hours to game
    if (isset($filters['min_hours_to_game'])) {
        if ($vb['hours_to_game'] < (float)$filters['min_hours_to_game']) return false;
    }

    // Odds range
    if (isset($filters['min_odds'])) {
        if ((float)$vb['best_odds'] < (float)$filters['min_odds']) return false;
    }
    if (isset($filters['max_odds'])) {
        if ((float)$vb['best_odds'] > (float)$filters['max_odds']) return false;
    }

    return true;
}


// ────────────────────────────────────────────────────────────
//  Bet sizing
// ────────────────────────────────────────────────────────────

function _arena_calc_bet_size($vb, $strat, $bankroll) {
    $method = $strat['sizing_method'];
    $param = (float)$strat['sizing_param'];

    if ($method === 'flat') {
        return (float)$strat['flat_amount'];
    }

    // Kelly-based sizing
    $ev_pct = (float)$vb['ev_pct'];
    $odds = (float)$vb['best_odds'];
    if ($odds <= 1.0) return 0;

    $kelly = ($ev_pct / 100.0) / ($odds - 1.0);
    $fractional_kelly = $kelly * $param;
    $bet = $bankroll * $fractional_kelly;

    // Clamp
    $min_bet = 5.0;
    $max_bet = $bankroll * 0.05; // 5% max per bet
    if ($bet < $min_bet) $bet = $min_bet;
    if ($bet > $max_bet) $bet = $max_bet;

    return round($bet, 2);
}


// ────────────────────────────────────────────────────────────
//  Determine bet result
// ────────────────────────────────────────────────────────────

function _arena_determine_result($bet, $home_score, $away_score) {
    $market = $bet['market'];
    $pick = $bet['pick'];
    $pick_point = isset($bet['pick_point']) ? (float)$bet['pick_point'] : 0;

    if ($market === 'h2h') {
        // Moneyline
        $winner = ($home_score > $away_score) ? $bet['home_team'] : $bet['away_team'];
        if ($home_score === $away_score) return 'push';
        return _arena_team_match($pick, $winner) ? 'won' : 'lost';
    }

    if ($market === 'spreads') {
        // Spread: pick is team name, pick_point is the spread
        $is_home = _arena_team_match($pick, $bet['home_team']);
        $pick_score = $is_home ? $home_score : $away_score;
        $opp_score = $is_home ? $away_score : $home_score;
        $adjusted = $pick_score + $pick_point;
        if ($adjusted > $opp_score) return 'won';
        if ($adjusted < $opp_score) return 'lost';
        return 'push';
    }

    if ($market === 'totals') {
        $total = $home_score + $away_score;
        $line = $pick_point;
        if (stripos($pick, 'Over') !== false) {
            if ($total > $line) return 'won';
            if ($total < $line) return 'lost';
            return 'push';
        } else {
            if ($total < $line) return 'won';
            if ($total > $line) return 'lost';
            return 'push';
        }
    }

    return 'lost'; // Unknown market type
}


// ────────────────────────────────────────────────────────────
//  Update bankroll after settlement
// ────────────────────────────────────────────────────────────

function _arena_update_bankroll($conn, $strat_id, $result, $pnl, $bet_amount, $odds, $ev_pct) {
    $now = gmdate('Y-m-d H:i:s');

    // Fetch current bankroll record
    $br_q = $conn->query("SELECT * FROM lm_arena_bankrolls WHERE strategy_id=" . (int)$strat_id);
    if (!$br_q || $br_q->num_rows === 0) return;
    $br = $br_q->fetch_assoc();

    $new_bankroll = (float)$br['bankroll'] + $pnl;
    $total_bets = (int)$br['total_bets'] + 1;
    $total_wins = (int)$br['total_wins'] + ($result === 'won' ? 1 : 0);
    $total_losses = (int)$br['total_losses'] + ($result === 'lost' ? 1 : 0);
    $total_pushes = (int)$br['total_pushes'] + ($result === 'push' ? 1 : 0);
    $total_wagered = (float)$br['total_wagered'] + $bet_amount;
    $total_pnl = (float)$br['total_pnl'] + $pnl;

    $decided = $total_wins + $total_losses;
    $win_rate = ($decided > 0) ? round(($total_wins / $decided) * 100, 2) : 0;
    $roi = ($total_wagered > 0) ? round(($total_pnl / $total_wagered) * 100, 2) : 0;

    $peak = max((float)$br['peak_bankroll'], $new_bankroll);
    $trough = min((float)$br['trough_bankroll'], $new_bankroll);
    $dd = ($peak > 0) ? round((($peak - $trough) / $peak) * 100, 2) : 0;

    // Streak tracking
    $streak = (int)$br['current_streak'];
    if ($result === 'won') {
        $streak = ($streak > 0) ? $streak + 1 : 1;
    } elseif ($result === 'lost') {
        $streak = ($streak < 0) ? $streak - 1 : -1;
    }
    $best_streak = max((int)$br['best_streak'], $streak);
    $worst_streak = min((int)$br['worst_streak'], $streak);

    // Running averages
    $n = $total_bets;
    $avg_odds = (($n - 1) * (float)$br['avg_odds'] + $odds) / $n;
    $avg_ev = (($n - 1) * (float)$br['avg_ev'] + $ev_pct) / $n;
    $avg_bet = (($n - 1) * (float)$br['avg_bet_size'] + $bet_amount) / $n;

    $conn->query("UPDATE lm_arena_bankrolls SET "
        . "bankroll=" . round($new_bankroll, 2) . ", "
        . "total_bets=" . $total_bets . ", "
        . "total_wins=" . $total_wins . ", "
        . "total_losses=" . $total_losses . ", "
        . "total_pushes=" . $total_pushes . ", "
        . "total_wagered=" . round($total_wagered, 2) . ", "
        . "total_pnl=" . round($total_pnl, 2) . ", "
        . "roi_pct=" . $roi . ", "
        . "win_rate=" . $win_rate . ", "
        . "peak_bankroll=" . round($peak, 2) . ", "
        . "trough_bankroll=" . round($trough, 2) . ", "
        . "max_drawdown_pct=" . $dd . ", "
        . "current_streak=" . $streak . ", "
        . "best_streak=" . $best_streak . ", "
        . "worst_streak=" . $worst_streak . ", "
        . "avg_odds=" . round($avg_odds, 4) . ", "
        . "avg_ev=" . round($avg_ev, 4) . ", "
        . "avg_bet_size=" . round($avg_bet, 2) . ", "
        . "last_bet_at='" . $now . "', "
        . "updated_at='" . $now . "' "
        . "WHERE strategy_id=" . (int)$strat_id);
}


// ════════════════════════════════════════════════════════════
//  ACTION: leaderboard — Ranked strategies
// ════════════════════════════════════════════════════════════

function _arena_leaderboard($conn) {
    $sort = isset($_GET['sort']) ? strtolower(trim($_GET['sort'])) : 'roi';
    $valid_sorts = array('roi' => 'b.roi_pct', 'winrate' => 'b.win_rate', 'pnl' => 'b.total_pnl',
        'bets' => 'b.total_bets', 'bankroll' => 'b.bankroll', 'drawdown' => 'b.max_drawdown_pct');
    $order_col = isset($valid_sorts[$sort]) ? $valid_sorts[$sort] : 'b.roi_pct';
    $order_dir = ($sort === 'drawdown') ? 'ASC' : 'DESC';

    $q = $conn->query("SELECT s.*, b.* FROM lm_arena_strategies s "
        . "JOIN lm_arena_bankrolls b ON b.strategy_id = s.id "
        . "ORDER BY " . $order_col . " " . $order_dir);

    $strategies = array();
    $active_count = 0;
    $total_bets_all = 0;
    if ($q) {
        while ($row = $q->fetch_assoc()) {
            $decided = (int)$row['total_wins'] + (int)$row['total_losses'];

            // Statistical confidence (z-score for win rate vs 50%)
            $confidence = 'collecting';
            $p_value = 1.0;
            if ($decided >= 10) {
                $p = (float)$row['win_rate'] / 100.0;
                $z = ($p - 0.5) / sqrt(0.25 / $decided);
                $p_value = round(2 * (1 - _arena_normal_cdf(abs($z))), 4);
                if ($decided >= 50 && $p_value < 0.05) {
                    $confidence = ($p > 0.5) ? 'statistically_winning' : 'statistically_losing';
                } elseif ($decided >= 30) {
                    $confidence = ($p > 0.5) ? 'promising' : 'concerning';
                } else {
                    $confidence = 'early_data';
                }
            }

            $row['decided_bets'] = $decided;
            $row['confidence'] = $confidence;
            $row['p_value'] = $p_value;
            $row['filters'] = json_decode($row['filters_json'], true);
            unset($row['filters_json']);

            $strategies[] = $row;
            if ($row['status'] === 'active') $active_count++;
            $total_bets_all += (int)$row['total_bets'];
        }
    }

    // Summary stats
    $best_roi = 0;
    $worst_roi = 0;
    $best_name = '';
    $worst_name = '';
    foreach ($strategies as $s) {
        if ((float)$s['roi_pct'] > $best_roi || $best_name === '') {
            $best_roi = (float)$s['roi_pct'];
            $best_name = $s['name'];
        }
        if ((float)$s['roi_pct'] < $worst_roi || $worst_name === '') {
            $worst_roi = (float)$s['roi_pct'];
            $worst_name = $s['name'];
        }
    }

    echo json_encode(array(
        'ok' => true,
        'strategies' => $strategies,
        'summary' => array(
            'total_strategies' => count($strategies),
            'active' => $active_count,
            'total_bets_placed' => $total_bets_all,
            'best_strategy' => $best_name,
            'best_roi' => $best_roi,
            'worst_strategy' => $worst_name,
            'worst_roi' => $worst_roi,
            'sort' => $sort
        ),
        'generated_at' => gmdate('Y-m-d H:i:s') . ' UTC'
    ));
}


// ════════════════════════════════════════════════════════════
//  ACTION: strategy — Detail for one strategy
// ════════════════════════════════════════════════════════════

function _arena_strategy_detail($conn) {
    $id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    if ($id <= 0) {
        echo json_encode(array('ok' => false, 'error' => 'Missing strategy id'));
        return;
    }

    $q = $conn->query("SELECT s.*, b.* FROM lm_arena_strategies s "
        . "JOIN lm_arena_bankrolls b ON b.strategy_id = s.id "
        . "WHERE s.id=" . $id);

    if (!$q || $q->num_rows === 0) {
        echo json_encode(array('ok' => false, 'error' => 'Strategy not found'));
        return;
    }

    $strat = $q->fetch_assoc();
    $strat['filters'] = json_decode($strat['filters_json'], true);

    // Recent bets
    $bets_q = $conn->query("SELECT * FROM lm_arena_bets WHERE strategy_id=" . $id . " ORDER BY placed_at DESC LIMIT 20");
    $recent = array();
    if ($bets_q) {
        while ($row = $bets_q->fetch_assoc()) {
            $recent[] = $row;
        }
    }

    // Performance by sport
    $sport_q = $conn->query("SELECT sport, COUNT(*) as total, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "SUM(CASE WHEN result IS NOT NULL THEN pnl ELSE 0 END) as pnl "
        . "FROM lm_arena_bets WHERE strategy_id=" . $id . " AND status='settled' GROUP BY sport");

    $by_sport = array();
    if ($sport_q) {
        while ($row = $sport_q->fetch_assoc()) {
            $decided = (int)$row['wins'] + (int)$row['losses'];
            $row['win_rate'] = ($decided > 0) ? round((int)$row['wins'] / $decided * 100, 1) : 0;
            $by_sport[] = $row;
        }
    }

    // Performance by market
    $mkt_q = $conn->query("SELECT market, COUNT(*) as total, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "SUM(CASE WHEN result IS NOT NULL THEN pnl ELSE 0 END) as pnl "
        . "FROM lm_arena_bets WHERE strategy_id=" . $id . " AND status='settled' GROUP BY market");

    $by_market = array();
    if ($mkt_q) {
        while ($row = $mkt_q->fetch_assoc()) {
            $decided = (int)$row['wins'] + (int)$row['losses'];
            $row['win_rate'] = ($decided > 0) ? round((int)$row['wins'] / $decided * 100, 1) : 0;
            $by_market[] = $row;
        }
    }

    // Snapshots (equity curve)
    $snap_q = $conn->query("SELECT * FROM lm_arena_snapshots WHERE strategy_id=" . $id . " ORDER BY snapshot_date ASC");
    $snapshots = array();
    if ($snap_q) {
        while ($row = $snap_q->fetch_assoc()) $snapshots[] = $row;
    }

    echo json_encode(array(
        'ok' => true,
        'strategy' => $strat,
        'recent_bets' => $recent,
        'by_sport' => $by_sport,
        'by_market' => $by_market,
        'equity_curve' => $snapshots
    ));
}


// ════════════════════════════════════════════════════════════
//  ACTION: history — Bet history for one strategy
// ════════════════════════════════════════════════════════════

function _arena_bet_history($conn) {
    $id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    $limit = isset($_GET['limit']) ? (int)$_GET['limit'] : 50;
    if ($limit > 200) $limit = 200;
    $page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
    if ($page < 1) $page = 1;
    $offset = ($page - 1) * $limit;

    $where = ($id > 0) ? "WHERE strategy_id=" . $id : "";

    $total_q = $conn->query("SELECT COUNT(*) as cnt FROM lm_arena_bets " . $where);
    $total = 0;
    if ($total_q && $row = $total_q->fetch_assoc()) $total = (int)$row['cnt'];

    $q = $conn->query("SELECT ab.*, s.slug, s.name as strategy_name FROM lm_arena_bets ab "
        . "JOIN lm_arena_strategies s ON s.id = ab.strategy_id "
        . ($where ? $where : "") . " ORDER BY placed_at DESC LIMIT " . $limit . " OFFSET " . $offset);

    $bets = array();
    if ($q) {
        while ($row = $q->fetch_assoc()) $bets[] = $row;
    }

    echo json_encode(array(
        'ok' => true,
        'bets' => $bets,
        'total' => $total,
        'page' => $page,
        'pages' => ceil($total / $limit)
    ));
}


// ════════════════════════════════════════════════════════════
//  ACTION: eliminate — Auto-eliminate statistical losers
// ════════════════════════════════════════════════════════════

function _arena_eliminate($conn) {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $min_bets = isset($_GET['min_bets']) ? (int)$_GET['min_bets'] : 50;
    $max_dd = isset($_GET['max_dd']) ? (float)$_GET['max_dd'] : 30.0;

    $q = $conn->query("SELECT s.id, s.slug, s.name, b.* FROM lm_arena_strategies s "
        . "JOIN lm_arena_bankrolls b ON b.strategy_id = s.id "
        . "WHERE s.status='active'");

    $eliminated = array();
    $now = gmdate('Y-m-d H:i:s');

    if ($q) {
        while ($row = $q->fetch_assoc()) {
            $decided = (int)$row['total_wins'] + (int)$row['total_losses'];
            if ($decided < $min_bets) continue;

            $reason = '';

            // Eliminate if ROI is significantly negative
            if ((float)$row['roi_pct'] < -10.0) {
                $reason = 'ROI below -10% after ' . $decided . ' bets';
            }

            // Eliminate if max drawdown exceeds threshold
            if ((float)$row['max_drawdown_pct'] > $max_dd) {
                $reason = 'Max drawdown ' . $row['max_drawdown_pct'] . '% exceeds ' . $max_dd . '% limit';
            }

            // Eliminate if win rate is statistically significantly below 50%
            if ($decided >= $min_bets) {
                $p = (float)$row['win_rate'] / 100.0;
                $z = ($p - 0.5) / sqrt(0.25 / $decided);
                if ($z < -1.96) {
                    $reason = 'Win rate ' . $row['win_rate'] . '% is statistically below 50% (z=' . round($z, 2) . ', p<0.05)';
                }
            }

            if ($reason) {
                $conn->query("UPDATE lm_arena_strategies SET status='eliminated', "
                    . "eliminated_at='" . $now . "', "
                    . "elimination_reason='" . $conn->real_escape_string($reason) . "' "
                    . "WHERE id=" . (int)$row['id']);

                $eliminated[] = array(
                    'slug' => $row['slug'],
                    'name' => $row['name'],
                    'reason' => $reason,
                    'final_roi' => (float)$row['roi_pct'],
                    'final_win_rate' => (float)$row['win_rate'],
                    'total_bets' => $decided
                );
            }
        }
    }

    echo json_encode(array(
        'ok' => true,
        'eliminated' => $eliminated,
        'eliminated_count' => count($eliminated),
        'min_bets_threshold' => $min_bets,
        'max_drawdown_threshold' => $max_dd
    ));
}


// ════════════════════════════════════════════════════════════
//  ACTION: snapshot — Save daily performance snapshot
// ════════════════════════════════════════════════════════════

function _arena_snapshot($conn) {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $today = gmdate('Y-m-d');
    $q = $conn->query("SELECT s.id, b.* FROM lm_arena_strategies s "
        . "JOIN lm_arena_bankrolls b ON b.strategy_id = s.id");

    $saved = 0;
    if ($q) {
        while ($row = $q->fetch_assoc()) {
            $sid = (int)$row['id'];
            $conn->query("INSERT INTO lm_arena_snapshots (strategy_id, snapshot_date, bankroll, total_bets, roi_pct, win_rate, max_drawdown_pct) VALUES ("
                . $sid . ", '" . $today . "', "
                . (float)$row['bankroll'] . ", "
                . (int)$row['total_bets'] . ", "
                . (float)$row['roi_pct'] . ", "
                . (float)$row['win_rate'] . ", "
                . (float)$row['max_drawdown_pct'] . ") "
                . "ON DUPLICATE KEY UPDATE bankroll=" . (float)$row['bankroll'] . ", "
                . "total_bets=" . (int)$row['total_bets'] . ", "
                . "roi_pct=" . (float)$row['roi_pct'] . ", "
                . "win_rate=" . (float)$row['win_rate'] . ", "
                . "max_drawdown_pct=" . (float)$row['max_drawdown_pct']);
            $saved++;
        }
    }

    echo json_encode(array('ok' => true, 'snapshots_saved' => $saved, 'date' => $today));
}


// ════════════════════════════════════════════════════════════
//  ACTION: status — Arena health check
// ════════════════════════════════════════════════════════════

function _arena_status($conn) {
    $strat_q = $conn->query("SELECT COUNT(*) as total, SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as active, SUM(CASE WHEN status='eliminated' THEN 1 ELSE 0 END) as eliminated FROM lm_arena_strategies");
    $strats = array('total' => 0, 'active' => 0, 'eliminated' => 0);
    if ($strat_q && $row = $strat_q->fetch_assoc()) {
        $strats = array('total' => (int)$row['total'], 'active' => (int)$row['active'], 'eliminated' => (int)$row['eliminated']);
    }

    $bets_q = $conn->query("SELECT COUNT(*) as total, SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending, SUM(CASE WHEN status='settled' THEN 1 ELSE 0 END) as settled FROM lm_arena_bets");
    $bets = array('total' => 0, 'pending' => 0, 'settled' => 0);
    if ($bets_q && $row = $bets_q->fetch_assoc()) {
        $bets = array('total' => (int)$row['total'], 'pending' => (int)$row['pending'], 'settled' => (int)$row['settled']);
    }

    $latest_q = $conn->query("SELECT placed_at FROM lm_arena_bets ORDER BY placed_at DESC LIMIT 1");
    $latest_bet = null;
    if ($latest_q && $row = $latest_q->fetch_assoc()) $latest_bet = $row['placed_at'];

    $latest_settle_q = $conn->query("SELECT settled_at FROM lm_arena_bets WHERE status='settled' ORDER BY settled_at DESC LIMIT 1");
    $latest_settle = null;
    if ($latest_settle_q && $row = $latest_settle_q->fetch_assoc()) $latest_settle = $row['settled_at'];

    echo json_encode(array(
        'ok' => true,
        'strategies' => $strats,
        'bets' => $bets,
        'latest_bet' => $latest_bet,
        'latest_settlement' => $latest_settle,
        'initialized' => $strats['total'] > 0
    ));
}


// ════════════════════════════════════════════════════════════
//  ACTION: reset — Nuclear reset
// ════════════════════════════════════════════════════════════

function _arena_reset($conn) {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    $confirm = isset($_GET['confirm']) ? trim($_GET['confirm']) : '';
    if ($key !== $ADMIN_KEY || $confirm !== 'yes') {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Requires key and confirm=yes'));
        return;
    }

    $conn->query("TRUNCATE TABLE lm_arena_bets");
    $conn->query("TRUNCATE TABLE lm_arena_bankrolls");
    $conn->query("TRUNCATE TABLE lm_arena_snapshots");
    $conn->query("TRUNCATE TABLE lm_arena_strategies");

    echo json_encode(array('ok' => true, 'message' => 'Arena completely reset. Run init to re-seed strategies.'));
}


// ════════════════════════════════════════════════════════════
//  Helpers
// ════════════════════════════════════════════════════════════

function _arena_team_match($a, $b) {
    $a = strtolower(trim($a));
    $b = strtolower(trim($b));
    if ($a === $b) return true;
    if (strpos($a, $b) !== false || strpos($b, $a) !== false) return true;
    // Last word match (city name vs full name)
    $a_parts = explode(' ', $a);
    $b_parts = explode(' ', $b);
    $a_last = end($a_parts);
    $b_last = end($b_parts);
    if (strlen($a_last) > 3 && $a_last === $b_last) return true;
    return false;
}

function _arena_apply_rating(&$vb) {
    $score = 0;
    $ev = (float)$vb['ev_pct'];
    $score += min(50, $ev * 5);
    $score += min(20, $vb['book_count'] * 2);
    $market = isset($vb['market']) ? $vb['market'] : '';
    if ($market === 'h2h') $score += 15;
    elseif ($market === 'spreads') $score += 10;
    elseif ($market === 'totals') $score += 5;
    if ($vb['has_canadian_book']) $score += 10;
    $htg = $vb['hours_to_game'];
    if ($htg > 12) $score += 5;
    elseif ($htg > 3) $score += 3;
    elseif ($htg > 0.5) $score += 1;
    else $score -= 5;

    $vb['rating_score'] = (int)$score;
    if ($score >= 90)      $vb['rating_grade'] = 'A+';
    elseif ($score >= 80)  $vb['rating_grade'] = 'A';
    elseif ($score >= 70)  $vb['rating_grade'] = 'B+';
    elseif ($score >= 60)  $vb['rating_grade'] = 'B';
    elseif ($score >= 50)  $vb['rating_grade'] = 'C+';
    elseif ($score >= 40)  $vb['rating_grade'] = 'C';
    else                   $vb['rating_grade'] = 'D';

    if ($score >= 80) $vb['recommendation'] = 'STRONG TAKE';
    elseif ($score >= 65) $vb['recommendation'] = 'TAKE';
    elseif ($score >= 50) $vb['recommendation'] = 'LEAN';
    elseif ($score >= 35) $vb['recommendation'] = 'WAIT';
    else                  $vb['recommendation'] = 'SKIP';
}

function _arena_normal_cdf($x) {
    // Abramowitz and Stegun approximation
    $a1 = 0.254829592;
    $a2 = -0.284496736;
    $a3 = 1.421413741;
    $a4 = -1.453152027;
    $a5 = 1.061405429;
    $p = 0.3275911;
    $sign = ($x < 0) ? -1 : 1;
    $x = abs($x) / sqrt(2.0);
    $t = 1.0 / (1.0 + $p * $x);
    $y = 1.0 - ((((($a5 * $t + $a4) * $t) + $a3) * $t + $a2) * $t + $a1) * $t * exp(-$x * $x);
    return 0.5 * (1.0 + $sign * $y);
}
