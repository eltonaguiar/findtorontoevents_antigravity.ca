<?php
/**
 * Sports Picks — Value Bet Finder + Line Shopping for Canadian Sportsbooks
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator)
 *
 * Algorithms:
 *   1. Value Bets — find +EV bets where a bookmaker offers better odds than consensus
 *   2. Line Shopping — find best odds across Canadian sportsbooks for each game
 *
 * Actions:
 *   ?action=analyze&key=livetrader2026  — Run algorithms, store value bets (admin)
 *   ?action=value_bets[&sport=X]        — Return active value bets (public)
 *   ?action=line_shop[&sport=X]         — Best/worst odds per game (public)
 *   ?action=today[&sport=X]             — Combined picks for next 24h (public)
 *   ?action=all[&sport=X]               — Full response (public)
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';

// ────────────────────────────────────────────────────────────
//  Auto-create table
// ────────────────────────────────────────────────────────────

$conn->query("CREATE TABLE IF NOT EXISTS lm_sports_value_bets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(100) NOT NULL,
    sport VARCHAR(50) NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    commence_time DATETIME NOT NULL,
    market VARCHAR(20) NOT NULL,
    bet_type VARCHAR(50) NOT NULL,
    outcome_name VARCHAR(100) NOT NULL DEFAULT '',
    best_book VARCHAR(50) NOT NULL,
    best_book_key VARCHAR(50) NOT NULL DEFAULT '',
    best_odds DECIMAL(10,4) NOT NULL DEFAULT 0,
    consensus_implied_prob DECIMAL(6,4) NOT NULL DEFAULT 0,
    true_prob DECIMAL(6,4) NOT NULL DEFAULT 0,
    edge_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    ev_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    kelly_fraction DECIMAL(6,4) NOT NULL DEFAULT 0,
    kelly_bet DECIMAL(10,2) NOT NULL DEFAULT 0,
    all_odds TEXT,
    detected_at DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    KEY idx_sport (sport),
    KEY idx_status (status),
    KEY idx_ev (ev_pct),
    KEY idx_event (event_id),
    KEY idx_commence (commence_time)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ────────────────────────────────────────────────────────────
//  Constants
// ────────────────────────────────────────────────────────────

$ADMIN_KEY = 'livetrader2026';

$CANADIAN_BOOKS = array('bet365', 'fanduel', 'draftkings', 'betmgm', 'pointsbetus', 'williamhill_us', 'betrivers', 'espnbet', 'fanatics');

$BOOK_DISPLAY = array(
    'fanduel'        => 'FanDuel',
    'draftkings'     => 'DraftKings',
    'betmgm'         => 'BetMGM',
    'bet365'         => 'bet365',
    'pointsbetus'    => 'PointsBet',
    'williamhill_us' => 'Caesars',
    'bovada'         => 'Bovada',
    'betonlineag'    => 'BetOnline',
    'betrivers'      => 'BetRivers',
    'unibet_us'      => 'Unibet',
    'mybookieag'     => 'MyBookie',
    'superbook'      => 'SuperBook',
    'lowvig'         => 'LowVig',
    'betus'          => 'BetUS',
    'pinnacle'       => 'Pinnacle',
    'espnbet'        => 'ESPN BET',
    'fliff'          => 'Fliff',
    'hardrockbet'    => 'Hard Rock',
    'fanatics'       => 'Fanatics'
);

$SPORT_SHORT = array(
    'icehockey_nhl'          => 'NHL',
    'basketball_nba'         => 'NBA',
    'americanfootball_nfl'   => 'NFL',
    'baseball_mlb'           => 'MLB',
    'americanfootball_cfl'   => 'CFL',
    'soccer_usa_mls'         => 'MLS',
    'americanfootball_ncaaf' => 'NCAAF',
    'basketball_ncaab'       => 'NCAAB'
);

// NFL key numbers for spread analysis
$NFL_KEY_NUMBERS = array(3, 7, 10, 14, 17, 21);

// ────────────────────────────────────────────────────────────
//  Auto-create daily picks table (timestamped historical picks)
// ────────────────────────────────────────────────────────────

$conn->query("CREATE TABLE IF NOT EXISTS lm_sports_daily_picks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pick_date DATE NOT NULL,
    generated_at DATETIME NOT NULL,
    sport VARCHAR(50) NOT NULL,
    event_id VARCHAR(100) NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    commence_time DATETIME NOT NULL,
    market VARCHAR(20) NOT NULL,
    pick_type VARCHAR(50) NOT NULL DEFAULT '',
    outcome_name VARCHAR(100) NOT NULL DEFAULT '',
    best_book VARCHAR(50) NOT NULL DEFAULT '',
    best_book_key VARCHAR(50) NOT NULL DEFAULT '',
    best_odds DECIMAL(10,4) NOT NULL DEFAULT 0,
    ev_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    kelly_bet DECIMAL(10,2) NOT NULL DEFAULT 0,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'value_bet',
    confidence VARCHAR(20) NOT NULL DEFAULT 'medium',
    result VARCHAR(20) DEFAULT NULL,
    pnl DECIMAL(10,2) DEFAULT NULL,
    all_odds TEXT,
    KEY idx_date (pick_date),
    KEY idx_sport (sport),
    KEY idx_event (event_id),
    KEY idx_result (result)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ────────────────────────────────────────────────────────────
//  Action routing
// ────────────────────────────────────────────────────────────

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'today';

if ($action === 'analyze') {
    _sp_action_analyze($conn);
} elseif ($action === 'value_bets') {
    _sp_action_value_bets($conn);
} elseif ($action === 'line_shop') {
    _sp_action_line_shop($conn);
} elseif ($action === 'today') {
    _sp_action_today($conn);
} elseif ($action === 'all') {
    _sp_action_all($conn);
} elseif ($action === 'daily_picks') {
    _sp_action_daily_picks($conn);
} elseif ($action === 'pick_history') {
    _sp_action_pick_history($conn);
} elseif ($action === 'performance') {
    _sp_action_performance($conn);
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;

// ════════════════════════════════════════════════════════════
//  ACTION: analyze — Run value bet + line shop algorithms, store results
// ════════════════════════════════════════════════════════════

function _sp_action_analyze($conn) {
    global $ADMIN_KEY;

    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    // Full refresh: clear stale data and re-scan from live odds cache
    $conn->query("DELETE FROM lm_sports_value_bets WHERE status='active'");

    // Find all value bets from cached odds
    $value_bets = _sp_find_value_bets($conn, '', '', 2.0);

    // Store new value bets
    $inserted = 0;
    foreach ($value_bets as $vb) {
        // Check if already exists (same event + market + outcome + book)
        $check = $conn->query("SELECT id FROM lm_sports_value_bets WHERE event_id='"
            . $conn->real_escape_string($vb['event_id']) . "' AND market='"
            . $conn->real_escape_string($vb['market']) . "' AND outcome_name='"
            . $conn->real_escape_string($vb['outcome_name']) . "' AND best_book_key='"
            . $conn->real_escape_string($vb['best_book_key']) . "' AND status='active'");

        if ($check && $check->num_rows > 0) {
            // Update existing
            $row = $check->fetch_assoc();
            $conn->query("UPDATE lm_sports_value_bets SET "
                . "best_odds=" . (float)$vb['best_odds'] . ", "
                . "ev_pct=" . (float)$vb['ev_pct'] . ", "
                . "edge_pct=" . (float)$vb['edge_pct'] . ", "
                . "kelly_fraction=" . (float)$vb['kelly_fraction'] . ", "
                . "kelly_bet=" . (float)$vb['kelly_bet'] . ", "
                . "true_prob=" . (float)$vb['true_prob'] . ", "
                . "all_odds='" . $conn->real_escape_string($vb['all_odds_json']) . "', "
                . "detected_at=NOW() "
                . "WHERE id=" . (int)$row['id']);
        } else {
            // Insert new
            $sql = "INSERT INTO lm_sports_value_bets "
                . "(event_id, sport, home_team, away_team, commence_time, market, bet_type, outcome_name, "
                . "best_book, best_book_key, best_odds, consensus_implied_prob, true_prob, edge_pct, ev_pct, "
                . "kelly_fraction, kelly_bet, all_odds, detected_at, status) VALUES ("
                . "'" . $conn->real_escape_string($vb['event_id']) . "', "
                . "'" . $conn->real_escape_string($vb['sport']) . "', "
                . "'" . $conn->real_escape_string($vb['home_team']) . "', "
                . "'" . $conn->real_escape_string($vb['away_team']) . "', "
                . "'" . $conn->real_escape_string($vb['commence_time']) . "', "
                . "'" . $conn->real_escape_string($vb['market']) . "', "
                . "'" . $conn->real_escape_string($vb['bet_type']) . "', "
                . "'" . $conn->real_escape_string($vb['outcome_name']) . "', "
                . "'" . $conn->real_escape_string($vb['best_book']) . "', "
                . "'" . $conn->real_escape_string($vb['best_book_key']) . "', "
                . (float)$vb['best_odds'] . ", "
                . (float)$vb['consensus_ip'] . ", "
                . (float)$vb['true_prob'] . ", "
                . (float)$vb['edge_pct'] . ", "
                . (float)$vb['ev_pct'] . ", "
                . (float)$vb['kelly_fraction'] . ", "
                . (float)$vb['kelly_bet'] . ", "
                . "'" . $conn->real_escape_string($vb['all_odds_json']) . "', "
                . "NOW(), 'active')";
            $conn->query($sql);
            $inserted++;
        }
    }

    // Top bets for response
    $top = array();
    $top_q = $conn->query("SELECT * FROM lm_sports_value_bets WHERE status='active' ORDER BY ev_pct DESC LIMIT 10");
    if ($top_q) {
        while ($row = $top_q->fetch_assoc()) {
            $top[] = $row;
        }
    }

    echo json_encode(array(
        'ok'                     => true,
        'value_bets_found'       => count($value_bets),
        'new_bets_inserted'      => $inserted,
        'top_bets'               => $top
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: value_bets — Return active value bets
// ════════════════════════════════════════════════════════════

function _sp_action_value_bets($conn) {
    global $SPORT_SHORT;

    $sport = isset($_GET['sport']) ? $conn->real_escape_string(trim($_GET['sport'])) : '';
    $market = isset($_GET['market']) ? $conn->real_escape_string(trim($_GET['market'])) : '';
    $min_ev = isset($_GET['min_ev']) ? (float)$_GET['min_ev'] : 2.0;

    $where = "status='active' AND commence_time > NOW()";
    if ($sport) $where .= " AND sport='" . $sport . "'";
    if ($market) $where .= " AND market='" . $market . "'";
    $where .= " AND ev_pct >= " . (float)$min_ev;

    $result = $conn->query("SELECT * FROM lm_sports_value_bets WHERE " . $where . " ORDER BY ev_pct DESC LIMIT 100");

    $bets = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $row['sport_short'] = isset($SPORT_SHORT[$row['sport']]) ? $SPORT_SHORT[$row['sport']] : $row['sport'];
            $row['is_canadian_book'] = in_array($row['best_book_key'], array('bet365', 'fanduel', 'draftkings', 'betmgm', 'pointsbetus', 'williamhill_us', 'betrivers', 'espnbet', 'fanatics')) ? 1 : 0;
            $row['all_odds_json'] = $row['all_odds']; // keep raw for rating
            $row['all_odds'] = json_decode($row['all_odds'], true);
            _sp_apply_rating($row);
            $bets[] = $row;
        }
    }

    echo json_encode(array(
        'ok'    => true,
        'bets'  => $bets,
        'count' => count($bets),
        'filters' => array('sport' => $sport, 'market' => $market, 'min_ev' => $min_ev)
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: line_shop — Best/worst odds across Canadian books
// ════════════════════════════════════════════════════════════

function _sp_action_line_shop($conn) {
    global $SPORT_SHORT, $CANADIAN_BOOKS, $BOOK_DISPLAY;

    $sport = isset($_GET['sport']) ? $conn->real_escape_string(trim($_GET['sport'])) : '';
    $hours = isset($_GET['hours']) ? (int)$_GET['hours'] : 48;
    if ($hours < 1) $hours = 1;
    if ($hours > 168) $hours = 168;

    $shops = _sp_compute_line_shop($conn, $sport, $hours);

    echo json_encode(array(
        'ok'    => true,
        'shops' => $shops,
        'count' => count($shops),
        'filters' => array('sport' => $sport, 'hours' => $hours)
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: today — Combined value bets + line shopping for next 24h
// ════════════════════════════════════════════════════════════

function _sp_action_today($conn) {
    global $SPORT_SHORT;

    $sport = isset($_GET['sport']) ? $conn->real_escape_string(trim($_GET['sport'])) : '';

    // Value bets
    $where_vb = "status='active' AND commence_time > NOW() AND commence_time < DATE_ADD(NOW(), INTERVAL 24 HOUR)";
    if ($sport) $where_vb .= " AND sport='" . $sport . "'";
    $where_vb .= " AND ev_pct >= 2.0";

    $vb_result = $conn->query("SELECT * FROM lm_sports_value_bets WHERE " . $where_vb . " ORDER BY ev_pct DESC LIMIT 50");
    $value_bets = array();
    $strong_takes = 0;
    $takes = 0;
    $waits = 0;
    if ($vb_result) {
        while ($row = $vb_result->fetch_assoc()) {
            $row['sport_short'] = isset($SPORT_SHORT[$row['sport']]) ? $SPORT_SHORT[$row['sport']] : $row['sport'];
            $row['is_canadian_book'] = in_array($row['best_book_key'], array('bet365', 'fanduel', 'draftkings', 'betmgm', 'pointsbetus', 'williamhill_us', 'betrivers', 'espnbet', 'fanatics')) ? 1 : 0;
            $row['all_odds_json'] = $row['all_odds']; // keep raw for rating
            $row['all_odds'] = json_decode($row['all_odds'], true);
            _sp_apply_rating($row);
            if ($row['recommendation'] === 'STRONG TAKE') $strong_takes++;
            elseif ($row['recommendation'] === 'TAKE') $takes++;
            elseif ($row['recommendation'] === 'WAIT' || $row['recommendation'] === 'SKIP') $waits++;
            $value_bets[] = $row;
        }
    }

    // Line shopping
    $line_shops = _sp_compute_line_shop($conn, $sport, 24);

    // Summary stats
    $canadian_picks = 0;
    $total_ev = 0;
    foreach ($value_bets as $vb) {
        if ($vb['is_canadian_book']) $canadian_picks++;
        $total_ev += (float)$vb['ev_pct'];
    }

    echo json_encode(array(
        'ok'              => true,
        'value_bets'      => $value_bets,
        'value_bet_count' => count($value_bets),
        'line_shops'      => $line_shops,
        'line_shop_count' => count($line_shops),
        'summary'         => array(
            'total_picks'    => count($value_bets),
            'canadian_picks' => $canadian_picks,
            'avg_ev_pct'     => count($value_bets) > 0 ? round($total_ev / count($value_bets), 2) : 0,
            'max_ev_pct'     => count($value_bets) > 0 ? (float)$value_bets[0]['ev_pct'] : 0,
            'strong_takes'   => $strong_takes,
            'takes'          => $takes,
            'waits'          => $waits
        ),
        'generated_at' => gmdate('Y-m-d H:i:s') . ' UTC'
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: all — Full combined response
// ════════════════════════════════════════════════════════════

function _sp_action_all($conn) {
    global $SPORT_SHORT;

    $sport = isset($_GET['sport']) ? $conn->real_escape_string(trim($_GET['sport'])) : '';

    // All active value bets
    $where = "status='active' AND commence_time > NOW()";
    if ($sport) $where .= " AND sport='" . $sport . "'";

    $vb_result = $conn->query("SELECT * FROM lm_sports_value_bets WHERE " . $where . " ORDER BY ev_pct DESC LIMIT 100");
    $value_bets = array();
    if ($vb_result) {
        while ($row = $vb_result->fetch_assoc()) {
            $row['sport_short'] = isset($SPORT_SHORT[$row['sport']]) ? $SPORT_SHORT[$row['sport']] : $row['sport'];
            $row['all_odds_json'] = $row['all_odds'];
            $row['all_odds'] = json_decode($row['all_odds'], true);
            _sp_apply_rating($row);
            $value_bets[] = $row;
        }
    }

    // Line shopping — 72h out
    $line_shops = _sp_compute_line_shop($conn, $sport, 72);

    // By-sport breakdown
    $sport_counts = array();
    foreach ($value_bets as $vb) {
        $sk = $vb['sport_short'];
        if (!isset($sport_counts[$sk])) $sport_counts[$sk] = 0;
        $sport_counts[$sk]++;
    }

    echo json_encode(array(
        'ok'              => true,
        'value_bets'      => $value_bets,
        'value_bet_count' => count($value_bets),
        'line_shops'      => $line_shops,
        'line_shop_count' => count($line_shops),
        'by_sport'        => $sport_counts,
        'generated_at'    => gmdate('Y-m-d H:i:s') . ' UTC'
    ));
}

// ════════════════════════════════════════════════════════════
//  CORE ALGORITHM: Value Bet Finder
// ════════════════════════════════════════════════════════════

function _sp_find_value_bets($conn, $sport_filter, $market_filter, $min_ev) {
    global $CANADIAN_BOOKS, $BOOK_DISPLAY;

    // Get all upcoming events from cached odds
    $where = "commence_time > NOW()";
    if ($sport_filter) $where .= " AND sport='" . $conn->real_escape_string($sport_filter) . "'";

    $events_q = $conn->query("SELECT DISTINCT event_id, sport, home_team, away_team, commence_time FROM lm_sports_odds WHERE " . $where . " ORDER BY commence_time");
    if (!$events_q) return array();

    $events = array();
    while ($row = $events_q->fetch_assoc()) {
        $events[] = $row;
    }

    $value_bets = array();

    foreach ($events as $ev) {
        $eid      = $ev['event_id'];
        $ev_sport = $ev['sport'];
        $ev_home  = $ev['home_team'];
        $ev_away  = $ev['away_team'];
        $ev_time  = $ev['commence_time'];

        // Get all markets for this event
        $markets_q = $conn->query("SELECT DISTINCT market FROM lm_sports_odds WHERE event_id='" . $conn->real_escape_string($eid) . "'");
        if (!$markets_q) continue;

        $markets = array();
        while ($mrow = $markets_q->fetch_assoc()) {
            $markets[] = $mrow['market'];
        }

        foreach ($markets as $mkt) {
            if ($market_filter && $mkt !== $market_filter) continue;

            // Get all outcomes for this event+market
            $outcomes_q = $conn->query("SELECT DISTINCT outcome_name FROM lm_sports_odds WHERE event_id='"
                . $conn->real_escape_string($eid) . "' AND market='" . $conn->real_escape_string($mkt) . "'");
            if (!$outcomes_q) continue;

            $outcome_names = array();
            while ($orow = $outcomes_q->fetch_assoc()) {
                $outcome_names[] = $orow['outcome_name'];
            }

            // For vig removal, we need ALL outcomes in this market
            // Collect implied probabilities for ALL outcomes across all books
            $all_outcome_avg_ip = array();

            foreach ($outcome_names as $oc_name) {
                $odds_q = $conn->query("SELECT bookmaker_key, bookmaker, outcome_price, outcome_point FROM lm_sports_odds WHERE event_id='"
                    . $conn->real_escape_string($eid) . "' AND market='" . $conn->real_escape_string($mkt)
                    . "' AND outcome_name='" . $conn->real_escape_string($oc_name) . "' AND outcome_price > 1.0");
                if (!$odds_q) continue;

                $book_odds = array();
                $ip_sum = 0;
                $ip_count = 0;
                while ($orow = $odds_q->fetch_assoc()) {
                    $price = (float)$orow['outcome_price'];
                    if ($price <= 1.0) continue;
                    $ip = 1.0 / $price;
                    $book_odds[] = array(
                        'book_key'  => $orow['bookmaker_key'],
                        'book_name' => $orow['bookmaker'],
                        'price'     => $price,
                        'point'     => $orow['outcome_point'],
                        'ip'        => $ip
                    );
                    $ip_sum += $ip;
                    $ip_count++;
                }

                if ($ip_count < 2) continue; // Need at least 2 books to compare

                $avg_ip = $ip_sum / $ip_count;
                $all_outcome_avg_ip[$oc_name] = array(
                    'avg_ip'    => $avg_ip,
                    'book_odds' => $book_odds
                );
            }

            // Calculate total overround (sum of average IPs for all outcomes)
            $total_avg_ip = 0;
            foreach ($all_outcome_avg_ip as $data) {
                $total_avg_ip += $data['avg_ip'];
            }
            if ($total_avg_ip <= 0) continue;

            // Now check each outcome for value
            foreach ($all_outcome_avg_ip as $oc_name => $data) {
                $true_prob = $data['avg_ip'] / $total_avg_ip; // Vig-removed probability

                foreach ($data['book_odds'] as $bo) {
                    // EV = (true_prob × decimal_odds) - 1
                    $ev = ($true_prob * $bo['price']) - 1.0;
                    $ev_pct = $ev * 100;

                    if ($ev_pct < $min_ev) continue;

                    // Kelly fraction = EV / (odds - 1)
                    $kelly = ($bo['price'] > 1.0) ? $ev / ($bo['price'] - 1.0) : 0;
                    $quarter_kelly = $kelly / 4.0;
                    $kelly_bet = round(1000.0 * min($quarter_kelly, 0.05), 2); // Based on $1000 bankroll

                    // Determine bet type description
                    $bet_type = $oc_name;
                    if ($mkt === 'h2h') {
                        $bet_type = $oc_name . ' ML';
                    } elseif ($mkt === 'spreads') {
                        $pt = $bo['point'] !== null ? $bo['point'] : '';
                        $bet_type = $oc_name . ' ' . ($pt >= 0 ? '+' : '') . $pt;
                    } elseif ($mkt === 'totals') {
                        $pt = $bo['point'] !== null ? $bo['point'] : '';
                        $bet_type = $oc_name . ' ' . $pt;
                    }

                    // Build all odds for this outcome
                    $all_odds_arr = array();
                    foreach ($data['book_odds'] as $ob) {
                        $bname = isset($BOOK_DISPLAY[$ob['book_key']]) ? $BOOK_DISPLAY[$ob['book_key']] : $ob['book_name'];
                        $all_odds_arr[] = array(
                            'book_key'  => $ob['book_key'],
                            'book_name' => $bname,
                            'price'     => $ob['price'],
                            'is_canadian' => in_array($ob['book_key'], $CANADIAN_BOOKS) ? 1 : 0
                        );
                    }

                    $value_bets[] = array(
                        'event_id'       => $eid,
                        'sport'          => $ev_sport,
                        'home_team'      => $ev_home,
                        'away_team'      => $ev_away,
                        'commence_time'  => $ev_time,
                        'market'         => $mkt,
                        'bet_type'       => $bet_type,
                        'outcome_name'   => $oc_name,
                        'best_book'      => $bo['book_name'],
                        'best_book_key'  => $bo['book_key'],
                        'best_odds'      => $bo['price'],
                        'consensus_ip'   => round($data['avg_ip'], 4),
                        'true_prob'      => round($true_prob, 4),
                        'edge_pct'       => round($ev_pct, 2),
                        'ev_pct'         => round($ev_pct, 2),
                        'kelly_fraction' => round($quarter_kelly, 4),
                        'kelly_bet'      => $kelly_bet,
                        'all_odds_json'  => json_encode($all_odds_arr)
                    );
                }
            }
        }
    }

    // Sort by EV descending
    usort($value_bets, '_sp_sort_ev_desc');

    return $value_bets;
}

function _sp_sort_ev_desc($a, $b) {
    if ((float)$a['ev_pct'] == (float)$b['ev_pct']) return 0;
    return ((float)$a['ev_pct'] > (float)$b['ev_pct']) ? -1 : 1;
}

// ════════════════════════════════════════════════════════════
//  RATING SYSTEM — Grade each pick A+ through D with take/wait recommendation
// ════════════════════════════════════════════════════════════

function _sp_rate_pick($vb) {
    $score = 0;
    $reasons = array();

    // ── EV% is the primary driver (0-50 points) ──
    $ev = (float)$vb['ev_pct'];
    if ($ev >= 10.0) {
        $score += 50;
        $reasons[] = 'Exceptional EV (' . round($ev, 1) . '%)';
    } elseif ($ev >= 7.0) {
        $score += 42;
        $reasons[] = 'Very strong EV (' . round($ev, 1) . '%)';
    } elseif ($ev >= 5.0) {
        $score += 35;
        $reasons[] = 'Strong EV (' . round($ev, 1) . '%)';
    } elseif ($ev >= 3.5) {
        $score += 27;
        $reasons[] = 'Good EV (' . round($ev, 1) . '%)';
    } elseif ($ev >= 2.5) {
        $score += 20;
        $reasons[] = 'Moderate EV (' . round($ev, 1) . '%)';
    } else {
        $score += 12;
        $reasons[] = 'Marginal EV (' . round($ev, 1) . '%)';
    }

    // ── Number of books offering odds (consensus strength, 0-20 points) ──
    $all_odds = $vb['all_odds_json'];
    if (is_string($all_odds)) {
        $all_odds = json_decode($all_odds, true);
    }
    $num_books = is_array($all_odds) ? count($all_odds) : 0;
    if ($num_books >= 6) {
        $score += 20;
        $reasons[] = $num_books . ' books agree (strong consensus)';
    } elseif ($num_books >= 4) {
        $score += 15;
        $reasons[] = $num_books . ' books (solid consensus)';
    } elseif ($num_books >= 3) {
        $score += 10;
        $reasons[] = $num_books . ' books (decent sample)';
    } else {
        $score += 5;
        $reasons[] = $num_books . ' books (limited data)';
    }

    // ── Market type reliability (0-15 points) ──
    $market = isset($vb['market']) ? $vb['market'] : '';
    if ($market === 'h2h') {
        $score += 15;
        $reasons[] = 'Moneyline (most reliable market)';
    } elseif ($market === 'spreads') {
        $score += 12;
        $reasons[] = 'Spread (reliable market)';
    } elseif ($market === 'totals') {
        $score += 8;
        $reasons[] = 'Totals (moderate reliability)';
    }

    // ── Canadian book availability (0-10 points) ──
    $ca_books = array('bet365', 'fanduel', 'draftkings', 'betmgm', 'pointsbetus', 'williamhill_us', 'betrivers', 'espnbet', 'fanatics');
    $best_is_ca = in_array($vb['best_book_key'], $ca_books) ? true : false;
    if ($best_is_ca) {
        $score += 10;
        $reasons[] = 'Best odds on a Canadian-legal book';
    } else {
        $score += 3;
        $reasons[] = 'Best odds on offshore book';
    }

    // ── Time until game (0-5 points bonus, or penalty) ──
    $commence = strtotime($vb['commence_time']);
    $hours_away = ($commence - time()) / 3600.0;
    if ($hours_away > 6) {
        $score += 5;
        // no reason needed, it's fine
    } elseif ($hours_away > 2) {
        $score += 3;
        // normal window
    } elseif ($hours_away > 0.5) {
        $score += 0;
        $reasons[] = 'Game starting soon — odds may shift';
    } else {
        $score -= 5;
        $reasons[] = 'Game imminent — odds likely stale';
    }

    // ── Kelly size confidence (0-5 bonus) ──
    $kelly = (float)$vb['kelly_bet'];
    if ($kelly >= 40) {
        $score += 5;
    } elseif ($kelly >= 25) {
        $score += 3;
    }

    // ── Clamp score 0-100 ──
    if ($score > 100) $score = 100;
    if ($score < 0) $score = 0;

    // ── Map score to letter grade ──
    if ($score >= 90)      $grade = 'A+';
    elseif ($score >= 80)  $grade = 'A';
    elseif ($score >= 70)  $grade = 'B+';
    elseif ($score >= 60)  $grade = 'B';
    elseif ($score >= 50)  $grade = 'C+';
    elseif ($score >= 40)  $grade = 'C';
    else                   $grade = 'D';

    // ── Take / Wait recommendation ──
    if ($score >= 80) {
        $action = 'STRONG TAKE';
        $action_detail = 'High confidence — place this bet now';
    } elseif ($score >= 65) {
        $action = 'TAKE';
        $action_detail = 'Good value — worth placing';
    } elseif ($score >= 50) {
        $action = 'LEAN';
        $action_detail = 'Slight edge — consider with smaller size';
    } elseif ($score >= 35) {
        $action = 'WAIT';
        $action_detail = 'Marginal value — wait for better odds or skip';
    } else {
        $action = 'SKIP';
        $action_detail = 'Too thin — not enough edge to justify risk';
    }

    return array(
        'score'         => $score,
        'grade'         => $grade,
        'action'        => $action,
        'action_detail' => $action_detail,
        'reasons'       => $reasons
    );
}

// Apply rating to a value bet row (from DB or from _sp_find_value_bets)
function _sp_apply_rating(&$row) {
    $rating = _sp_rate_pick($row);
    $row['rating_score']    = $rating['score'];
    $row['rating_grade']    = $rating['grade'];
    $row['recommendation']  = $rating['action'];
    $row['rec_detail']      = $rating['action_detail'];
    $row['rating_reasons']  = $rating['reasons'];

    // American odds for display
    $decimal = (float)$row['best_odds'];
    if ($decimal >= 2.0) {
        $row['american_odds'] = '+' . round(($decimal - 1) * 100);
    } else {
        $row['american_odds'] = round(-100 / ($decimal - 1));
    }
    // Win probability (vig-removed)
    $tp = isset($row['true_prob']) ? (float)$row['true_prob'] : 0;
    $row['win_probability'] = round($tp * 100, 1);
}

// ════════════════════════════════════════════════════════════
//  CORE ALGORITHM: Line Shopping
// ════════════════════════════════════════════════════════════

function _sp_compute_line_shop($conn, $sport_filter, $hours) {
    global $CANADIAN_BOOKS, $BOOK_DISPLAY, $NFL_KEY_NUMBERS, $SPORT_SHORT;

    $where = "commence_time > NOW() AND commence_time < DATE_ADD(NOW(), INTERVAL " . (int)$hours . " HOUR)";
    if ($sport_filter) $where .= " AND sport='" . $conn->real_escape_string($sport_filter) . "'";

    // Get all events
    $events_q = $conn->query("SELECT DISTINCT event_id, sport, home_team, away_team, commence_time FROM lm_sports_odds WHERE " . $where . " ORDER BY commence_time");
    if (!$events_q) return array();

    $shops = array();

    while ($ev = $events_q->fetch_assoc()) {
        $eid = $ev['event_id'];
        $sport_short = isset($SPORT_SHORT[$ev['sport']]) ? $SPORT_SHORT[$ev['sport']] : $ev['sport'];

        // Get all markets for this event
        $mkts_q = $conn->query("SELECT DISTINCT market FROM lm_sports_odds WHERE event_id='" . $conn->real_escape_string($eid) . "'");
        if (!$mkts_q) continue;

        $event_markets = array();

        while ($mrow = $mkts_q->fetch_assoc()) {
            $mkt = $mrow['market'];

            // Get all outcomes
            $oc_q = $conn->query("SELECT DISTINCT outcome_name FROM lm_sports_odds WHERE event_id='"
                . $conn->real_escape_string($eid) . "' AND market='" . $conn->real_escape_string($mkt) . "'");
            if (!$oc_q) continue;

            $market_outcomes = array();

            while ($orow = $oc_q->fetch_assoc()) {
                $oc_name = $orow['outcome_name'];

                // Only Canadian books for line shopping
                $ca_where = "";
                $ca_keys = array();
                foreach ($CANADIAN_BOOKS as $cb) {
                    $ca_keys[] = "'" . $conn->real_escape_string($cb) . "'";
                }
                $ca_in = implode(',', $ca_keys);

                $odds_q = $conn->query("SELECT bookmaker_key, bookmaker, outcome_price, outcome_point FROM lm_sports_odds WHERE event_id='"
                    . $conn->real_escape_string($eid) . "' AND market='" . $conn->real_escape_string($mkt)
                    . "' AND outcome_name='" . $conn->real_escape_string($oc_name)
                    . "' AND bookmaker_key IN (" . $ca_in . ") AND outcome_price > 1.0 ORDER BY outcome_price DESC");

                if (!$odds_q || $odds_q->num_rows < 2) continue;

                $books = array();
                $best = null;
                $worst = null;

                while ($brow = $odds_q->fetch_assoc()) {
                    $price = (float)$brow['outcome_price'];
                    $bname = isset($BOOK_DISPLAY[$brow['bookmaker_key']]) ? $BOOK_DISPLAY[$brow['bookmaker_key']] : $brow['bookmaker'];

                    $entry = array(
                        'book_key'  => $brow['bookmaker_key'],
                        'book_name' => $bname,
                        'price'     => $price,
                        'point'     => $brow['outcome_point'] !== null ? (float)$brow['outcome_point'] : null
                    );
                    $books[] = $entry;

                    if ($best === null || $price > $best['price']) $best = $entry;
                    if ($worst === null || $price < $worst['price']) $worst = $entry;
                }

                if ($best === null || $worst === null || $best['price'] <= $worst['price']) continue;

                // Savings calculation
                $best_payout = $best['price'] - 1.0; // Profit per $1 bet
                $worst_payout = $worst['price'] - 1.0;
                $savings_pct = $worst_payout > 0 ? (($best_payout - $worst_payout) / $worst_payout) * 100 : 0;

                // Key number detection for NFL spreads
                $key_number_alert = false;
                if ($mkt === 'spreads' && (strpos($ev['sport'], 'football') !== false)) {
                    $points_seen = array();
                    foreach ($books as $b) {
                        if ($b['point'] !== null) {
                            $points_seen[] = abs($b['point']);
                        }
                    }
                    $points_seen = array_unique($points_seen);
                    if (count($points_seen) > 1) {
                        foreach ($NFL_KEY_NUMBERS as $kn) {
                            $has_key = false;
                            $has_non_key = false;
                            foreach ($points_seen as $p) {
                                if ($p == $kn) $has_key = true;
                                if ($p != $kn && abs($p - $kn) <= 0.5) $has_non_key = true;
                            }
                            if ($has_key && $has_non_key) {
                                $key_number_alert = true;
                                break;
                            }
                        }
                    }
                }

                $market_outcomes[] = array(
                    'outcome_name'     => $oc_name,
                    'best_book'        => $best['book_name'],
                    'best_book_key'    => $best['book_key'],
                    'best_price'       => $best['price'],
                    'best_point'       => $best['point'],
                    'worst_book'       => $worst['book_name'],
                    'worst_price'      => $worst['price'],
                    'savings_pct'      => round($savings_pct, 1),
                    'key_number_alert' => $key_number_alert,
                    'all_books'        => $books
                );
            }

            if (count($market_outcomes) > 0) {
                $event_markets[] = array(
                    'market'   => $mkt,
                    'outcomes' => $market_outcomes
                );
            }
        }

        if (count($event_markets) > 0) {
            $shops[] = array(
                'event_id'      => $eid,
                'sport'         => $ev['sport'],
                'sport_short'   => $sport_short,
                'home_team'     => $ev['home_team'],
                'away_team'     => $ev['away_team'],
                'commence_time' => $ev['commence_time'],
                'markets'       => $event_markets
            );
        }
    }

    return $shops;
}

// ════════════════════════════════════════════════════════════
//  ACTION: daily_picks — Generate + store timestamped daily picks snapshot
//  Called by GitHub Actions or manually. Creates a permanent record.
// ════════════════════════════════════════════════════════════

function _sp_action_daily_picks($conn) {
    global $ADMIN_KEY, $SPORT_SHORT;

    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $today = gmdate('Y-m-d');
    $now = gmdate('Y-m-d H:i:s');

    // Run value bet analysis fresh
    $value_bets = _sp_find_value_bets($conn, '', '', 2.0);

    // Filter to games in next 24h
    $cutoff = time() + 86400;
    $todays_picks = array();
    foreach ($value_bets as $vb) {
        $ct = strtotime($vb['commence_time']);
        if ($ct !== false && $ct > time() && $ct < $cutoff) {
            $todays_picks[] = $vb;
        }
    }

    // Store each pick with timestamp
    $stored = 0;
    foreach ($todays_picks as $vb) {
        // Confidence level based on EV
        $ev = (float)$vb['ev_pct'];
        $confidence = 'low';
        if ($ev >= 5.0) $confidence = 'high';
        elseif ($ev >= 3.0) $confidence = 'medium';

        // Check if already stored for today + same event + outcome
        $dup = $conn->query("SELECT id FROM lm_sports_daily_picks WHERE pick_date='" . $conn->real_escape_string($today)
            . "' AND event_id='" . $conn->real_escape_string($vb['event_id'])
            . "' AND outcome_name='" . $conn->real_escape_string($vb['outcome_name'])
            . "' AND market='" . $conn->real_escape_string($vb['market']) . "'");
        if ($dup && $dup->num_rows > 0) {
            // Update existing
            $row = $dup->fetch_assoc();
            $conn->query("UPDATE lm_sports_daily_picks SET "
                . "best_odds=" . (float)$vb['best_odds'] . ", "
                . "ev_pct=" . (float)$vb['ev_pct'] . ", "
                . "kelly_bet=" . (float)$vb['kelly_bet'] . ", "
                . "best_book='" . $conn->real_escape_string($vb['best_book']) . "', "
                . "best_book_key='" . $conn->real_escape_string($vb['best_book_key']) . "', "
                . "confidence='" . $conn->real_escape_string($confidence) . "', "
                . "all_odds='" . $conn->real_escape_string($vb['all_odds_json']) . "', "
                . "generated_at='" . $conn->real_escape_string($now) . "' "
                . "WHERE id=" . (int)$row['id']);
            continue;
        }

        $conn->query("INSERT INTO lm_sports_daily_picks "
            . "(pick_date, generated_at, sport, event_id, home_team, away_team, commence_time, "
            . "market, pick_type, outcome_name, best_book, best_book_key, best_odds, ev_pct, "
            . "kelly_bet, algorithm, confidence, all_odds) VALUES ("
            . "'" . $conn->real_escape_string($today) . "', "
            . "'" . $conn->real_escape_string($now) . "', "
            . "'" . $conn->real_escape_string($vb['sport']) . "', "
            . "'" . $conn->real_escape_string($vb['event_id']) . "', "
            . "'" . $conn->real_escape_string($vb['home_team']) . "', "
            . "'" . $conn->real_escape_string($vb['away_team']) . "', "
            . "'" . $conn->real_escape_string($vb['commence_time']) . "', "
            . "'" . $conn->real_escape_string($vb['market']) . "', "
            . "'" . $conn->real_escape_string($vb['bet_type']) . "', "
            . "'" . $conn->real_escape_string($vb['outcome_name']) . "', "
            . "'" . $conn->real_escape_string($vb['best_book']) . "', "
            . "'" . $conn->real_escape_string($vb['best_book_key']) . "', "
            . (float)$vb['best_odds'] . ", "
            . (float)$vb['ev_pct'] . ", "
            . (float)$vb['kelly_bet'] . ", "
            . "'value_bet', "
            . "'" . $conn->real_escape_string($confidence) . "', "
            . "'" . $conn->real_escape_string($vb['all_odds_json']) . "')");
        $stored++;
    }

    // Sport breakdown
    $sport_counts = array();
    foreach ($todays_picks as $p) {
        $s = isset($SPORT_SHORT[$p['sport']]) ? $SPORT_SHORT[$p['sport']] : $p['sport'];
        if (!isset($sport_counts[$s])) $sport_counts[$s] = 0;
        $sport_counts[$s]++;
    }

    echo json_encode(array(
        'ok'              => true,
        'pick_date'       => $today,
        'generated_at'    => $now . ' UTC',
        'total_picks'     => count($todays_picks),
        'new_stored'      => $stored,
        'by_sport'        => $sport_counts,
        'picks'           => array_slice($todays_picks, 0, 20)
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: pick_history — View historical daily picks by date
// ════════════════════════════════════════════════════════════

function _sp_action_pick_history($conn) {
    global $SPORT_SHORT;

    $date = isset($_GET['date']) ? $conn->real_escape_string(trim($_GET['date'])) : '';
    $sport = isset($_GET['sport']) ? $conn->real_escape_string(trim($_GET['sport'])) : '';
    $days = isset($_GET['days']) ? (int)$_GET['days'] : 7;
    if ($days < 1) $days = 1;
    if ($days > 90) $days = 90;

    // If specific date given, return that day's picks
    if ($date) {
        $where = "pick_date='" . $date . "'";
        if ($sport) $where .= " AND sport='" . $sport . "'";

        $result = $conn->query("SELECT * FROM lm_sports_daily_picks WHERE " . $where . " ORDER BY ev_pct DESC");
        $picks = array();
        if ($result) {
            while ($row = $result->fetch_assoc()) {
                $row['sport_short'] = isset($SPORT_SHORT[$row['sport']]) ? $SPORT_SHORT[$row['sport']] : $row['sport'];
                $row['all_odds'] = json_decode($row['all_odds'], true);
                $picks[] = $row;
            }
        }

        echo json_encode(array(
            'ok'    => true,
            'date'  => $date,
            'picks' => $picks,
            'count' => count($picks)
        ));
        return;
    }

    // Otherwise return day-by-day summary for last N days
    $sum_where = "pick_date >= DATE_SUB(CURDATE(), INTERVAL " . $days . " DAY)";
    if ($sport) $sum_where .= " AND sport='" . $sport . "'";
    $summary_q = $conn->query("SELECT pick_date, COUNT(*) as total_picks, "
        . "MIN(generated_at) as first_generated, MAX(generated_at) as last_generated, "
        . "ROUND(AVG(ev_pct), 2) as avg_ev, "
        . "MAX(ev_pct) as max_ev, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "SUM(CASE WHEN result='push' THEN 1 ELSE 0 END) as pushes, "
        . "SUM(CASE WHEN result IS NULL THEN 1 ELSE 0 END) as pending, "
        . "COALESCE(SUM(pnl), 0) as total_pnl "
        . "FROM lm_sports_daily_picks WHERE " . $sum_where . " "
        . "GROUP BY pick_date ORDER BY pick_date DESC");

    $days_arr = array();
    if ($summary_q) {
        while ($row = $summary_q->fetch_assoc()) {
            $w = (int)$row['wins'];
            $l = (int)$row['losses'];
            $row['win_rate'] = ($w + $l) > 0 ? round(($w / ($w + $l)) * 100, 1) : null;
            $days_arr[] = $row;
        }
    }

    // Overall performance of daily picks
    $overall_q = $conn->query("SELECT COUNT(*) as total, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "COALESCE(SUM(pnl), 0) as total_pnl "
        . "FROM lm_sports_daily_picks WHERE result IS NOT NULL");
    $overall = array('total' => 0, 'wins' => 0, 'losses' => 0, 'total_pnl' => 0, 'win_rate' => 0);
    if ($overall_q && $row = $overall_q->fetch_assoc()) {
        $overall['total'] = (int)$row['total'];
        $overall['wins'] = (int)$row['wins'];
        $overall['losses'] = (int)$row['losses'];
        $overall['total_pnl'] = (float)$row['total_pnl'];
        $w = (int)$row['wins'];
        $l = (int)$row['losses'];
        $overall['win_rate'] = ($w + $l) > 0 ? round(($w / ($w + $l)) * 100, 1) : 0;
    }

    echo json_encode(array(
        'ok'        => true,
        'days'      => $days_arr,
        'day_count' => count($days_arr),
        'overall'   => $overall
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: performance — Deep analytics on pick accuracy
// ════════════════════════════════════════════════════════════

function _sp_action_performance($conn) {
    global $SPORT_SHORT;

    // By sport performance
    $sport_q = $conn->query("SELECT sport, COUNT(*) as total, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "COALESCE(SUM(pnl), 0) as pnl, "
        . "ROUND(AVG(ev_pct), 2) as avg_ev "
        . "FROM lm_sports_daily_picks WHERE result IS NOT NULL GROUP BY sport ORDER BY pnl DESC");
    $by_sport = array();
    if ($sport_q) {
        while ($row = $sport_q->fetch_assoc()) {
            $row['sport_short'] = isset($SPORT_SHORT[$row['sport']]) ? $SPORT_SHORT[$row['sport']] : $row['sport'];
            $w = (int)$row['wins'];
            $l = (int)$row['losses'];
            $row['win_rate'] = ($w + $l) > 0 ? round(($w / ($w + $l)) * 100, 1) : 0;
            $by_sport[] = $row;
        }
    }

    // By market type
    $market_q = $conn->query("SELECT market, COUNT(*) as total, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "COALESCE(SUM(pnl), 0) as pnl "
        . "FROM lm_sports_daily_picks WHERE result IS NOT NULL GROUP BY market ORDER BY pnl DESC");
    $by_market = array();
    if ($market_q) {
        while ($row = $market_q->fetch_assoc()) {
            $w = (int)$row['wins'];
            $l = (int)$row['losses'];
            $row['win_rate'] = ($w + $l) > 0 ? round(($w / ($w + $l)) * 100, 1) : 0;
            $by_market[] = $row;
        }
    }

    // By confidence level
    $conf_q = $conn->query("SELECT confidence, COUNT(*) as total, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "COALESCE(SUM(pnl), 0) as pnl "
        . "FROM lm_sports_daily_picks WHERE result IS NOT NULL GROUP BY confidence");
    $by_confidence = array();
    if ($conf_q) {
        while ($row = $conf_q->fetch_assoc()) {
            $w = (int)$row['wins'];
            $l = (int)$row['losses'];
            $row['win_rate'] = ($w + $l) > 0 ? round(($w / ($w + $l)) * 100, 1) : 0;
            $by_confidence[] = $row;
        }
    }

    // By bookmaker
    $book_q = $conn->query("SELECT best_book, best_book_key, COUNT(*) as total, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "COALESCE(SUM(pnl), 0) as pnl "
        . "FROM lm_sports_daily_picks WHERE result IS NOT NULL GROUP BY best_book, best_book_key ORDER BY pnl DESC");
    $by_book = array();
    if ($book_q) {
        while ($row = $book_q->fetch_assoc()) {
            $w = (int)$row['wins'];
            $l = (int)$row['losses'];
            $row['win_rate'] = ($w + $l) > 0 ? round(($w / ($w + $l)) * 100, 1) : 0;
            $by_book[] = $row;
        }
    }

    // EV bucket analysis: do higher EV picks actually win more?
    $ev_buckets = array();
    $buckets_def = array(
        array('min' => 2, 'max' => 3, 'label' => '2-3%'),
        array('min' => 3, 'max' => 5, 'label' => '3-5%'),
        array('min' => 5, 'max' => 8, 'label' => '5-8%'),
        array('min' => 8, 'max' => 100, 'label' => '8%+')
    );
    foreach ($buckets_def as $b) {
        $bq = $conn->query("SELECT COUNT(*) as total, "
            . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
            . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
            . "COALESCE(SUM(pnl), 0) as pnl "
            . "FROM lm_sports_daily_picks WHERE result IS NOT NULL AND ev_pct >= " . $b['min'] . " AND ev_pct < " . $b['max']);
        if ($bq && $row = $bq->fetch_assoc()) {
            $w = (int)$row['wins'];
            $l = (int)$row['losses'];
            $ev_buckets[] = array(
                'range'    => $b['label'],
                'total'    => (int)$row['total'],
                'wins'     => $w,
                'losses'   => $l,
                'win_rate' => ($w + $l) > 0 ? round(($w / ($w + $l)) * 100, 1) : 0,
                'pnl'      => (float)$row['pnl']
            );
        }
    }

    // Streak tracking
    $streak_q = $conn->query("SELECT result FROM lm_sports_daily_picks WHERE result IS NOT NULL AND result != 'push' ORDER BY id DESC LIMIT 50");
    $current_streak = 0;
    $streak_type = '';
    $longest_win = 0;
    $longest_loss = 0;
    $temp_streak = 0;
    $temp_type = '';
    $first = true;
    if ($streak_q) {
        while ($row = $streak_q->fetch_assoc()) {
            $r = $row['result'];
            if ($first) {
                $streak_type = $r;
                $current_streak = 1;
                $temp_type = $r;
                $temp_streak = 1;
                $first = false;
            } else {
                if ($r === $streak_type && $current_streak > 0) {
                    $current_streak++;
                } elseif ($current_streak > 0 && $r !== $streak_type) {
                    $current_streak = 0; // Streak broken, stop counting current
                }
                if ($r === $temp_type) {
                    $temp_streak++;
                } else {
                    $temp_type = $r;
                    $temp_streak = 1;
                }
            }
            if ($temp_type === 'won' && $temp_streak > $longest_win) $longest_win = $temp_streak;
            if ($temp_type === 'lost' && $temp_streak > $longest_loss) $longest_loss = $temp_streak;
        }
    }

    echo json_encode(array(
        'ok'             => true,
        'by_sport'       => $by_sport,
        'by_market'      => $by_market,
        'by_confidence'  => $by_confidence,
        'by_book'        => $by_book,
        'ev_buckets'     => $ev_buckets,
        'streaks'        => array(
            'current'      => $current_streak,
            'current_type' => $streak_type,
            'longest_win'  => $longest_win,
            'longest_loss' => $longest_loss
        ),
        'generated_at' => gmdate('Y-m-d H:i:s') . ' UTC'
    ));
}

?>
