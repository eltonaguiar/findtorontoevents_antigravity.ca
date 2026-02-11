<?php
/**
 * Sports Paper Betting Tracker — Bankroll management + auto-settlement
 * PHP 5.2 compatible (no short arrays, no http_response_code, no spread operator)
 *
 * Mirrors live_trade.php pattern for paper trading.
 * Uses The Odds API scores endpoint (free, 0 credits) for auto-settlement.
 *
 * Actions:
 *   ?action=place&key=...    — Place a paper bet (admin)
 *   ?action=active           — List pending bets (public)
 *   ?action=settle&key=...   — Auto-settle completed bets using scores (admin)
 *   ?action=history          — Past bets with filters (public)
 *   ?action=dashboard        — Bankroll + stats (public)
 *   ?action=leaderboard      — Algorithm performance ranked by ROI (public)
 *   ?action=reset&key=...    — Truncate tables, start fresh (admin)
 */

require_once dirname(__FILE__) . '/sports_db_connect.php';

// ────────────────────────────────────────────────────────────
//  Auto-create tables
// ────────────────────────────────────────────────────────────

$conn->query("CREATE TABLE IF NOT EXISTS lm_sports_bets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_id VARCHAR(100) NOT NULL,
    sport VARCHAR(50) NOT NULL,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    commence_time DATETIME NOT NULL,
    game_date DATE DEFAULT NULL,
    bet_type VARCHAR(30) NOT NULL DEFAULT 'moneyline',
    market VARCHAR(20) NOT NULL DEFAULT 'h2h',
    pick VARCHAR(100) NOT NULL,
    pick_point DECIMAL(6,2) DEFAULT NULL,
    bookmaker VARCHAR(50) NOT NULL,
    bookmaker_key VARCHAR(50) NOT NULL DEFAULT '',
    odds DECIMAL(10,4) NOT NULL DEFAULT 0,
    implied_prob DECIMAL(6,4) NOT NULL DEFAULT 0,
    bet_amount DECIMAL(10,2) NOT NULL DEFAULT 0,
    potential_payout DECIMAL(10,2) NOT NULL DEFAULT 0,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'value_bet',
    ev_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    result VARCHAR(20) DEFAULT NULL,
    pnl DECIMAL(10,2) DEFAULT NULL,
    settled_at DATETIME DEFAULT NULL,
    actual_home_score INT DEFAULT NULL,
    actual_away_score INT DEFAULT NULL,
    placed_at DATETIME NOT NULL,
    KEY idx_status (status),
    KEY idx_sport (sport),
    KEY idx_algorithm (algorithm),
    KEY idx_placed (placed_at),
    KEY idx_event (event_id),
    KEY idx_game_date (game_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// Add game_date column if missing (for existing tables)
$col_check = $conn->query("SHOW COLUMNS FROM lm_sports_bets LIKE 'game_date'");
if ($col_check && $col_check->num_rows === 0) {
    $conn->query("ALTER TABLE lm_sports_bets ADD COLUMN game_date DATE DEFAULT NULL AFTER commence_time");
    $conn->query("ALTER TABLE lm_sports_bets ADD KEY idx_game_date (game_date)");
    // Backfill from commence_time (UTC -> EST)
    $conn->query("UPDATE lm_sports_bets SET game_date = DATE(DATE_SUB(commence_time, INTERVAL 5 HOUR)) WHERE game_date IS NULL AND commence_time IS NOT NULL");
}

$conn->query("CREATE TABLE IF NOT EXISTS lm_sports_bankroll (
    id INT AUTO_INCREMENT PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    bankroll DECIMAL(10,2) NOT NULL DEFAULT 1000,
    total_bets INT NOT NULL DEFAULT 0,
    total_wins INT NOT NULL DEFAULT 0,
    total_losses INT NOT NULL DEFAULT 0,
    total_pushes INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    total_wagered DECIMAL(10,2) NOT NULL DEFAULT 0,
    total_pnl DECIMAL(10,2) NOT NULL DEFAULT 0,
    roi_pct DECIMAL(6,2) NOT NULL DEFAULT 0,
    UNIQUE KEY idx_date (snapshot_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ────────────────────────────────────────────────────────────
//  Constants
// ────────────────────────────────────────────────────────────

$ADMIN_KEY = 'livetrader2026';
$INITIAL_BANKROLL = 1000.00;
$MAX_ACTIVE_BETS = 20;
$MIN_BET = 5.00;
$MAX_BET_PCT = 0.05; // 5% of bankroll

$API_BASE = 'https://api.the-odds-api.com/v4';

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

// ────────────────────────────────────────────────────────────
//  HTTP helper
// ────────────────────────────────────────────────────────────

function _sb_http_get($url) {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept: application/json'
        ));
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($body !== false && $code >= 200 && $code < 300) return $body;
        return null;
    }
    $ctx = stream_context_create(array(
        'http' => array('method' => 'GET', 'timeout' => 15, 'header' => "User-Agent: Mozilla/5.0\r\nAccept: application/json\r\n"),
        'ssl' => array('verify_peer' => false)
    ));
    $body = @file_get_contents($url, false, $ctx);
    return ($body === false) ? null : $body;
}

// ────────────────────────────────────────────────────────────
//  Helper: get current bankroll
// ────────────────────────────────────────────────────────────

function _sb_get_bankroll($conn) {
    global $INITIAL_BANKROLL;
    $r = $conn->query("SELECT COALESCE(SUM(pnl), 0) as total_pnl FROM lm_sports_bets WHERE result IS NOT NULL");
    if ($r && $row = $r->fetch_assoc()) {
        return $INITIAL_BANKROLL + (float)$row['total_pnl'];
    }
    return $INITIAL_BANKROLL;
}

// ────────────────────────────────────────────────────────────
//  Helper: take bankroll snapshot
// ────────────────────────────────────────────────────────────

function _sb_snapshot($conn) {
    global $INITIAL_BANKROLL;

    $bankroll = _sb_get_bankroll($conn);

    $stats = $conn->query("SELECT COUNT(*) as total, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "SUM(CASE WHEN result='push' THEN 1 ELSE 0 END) as pushes, "
        . "COALESCE(SUM(bet_amount), 0) as wagered, "
        . "COALESCE(SUM(pnl), 0) as pnl "
        . "FROM lm_sports_bets WHERE result IS NOT NULL");

    $total = 0; $wins = 0; $losses = 0; $pushes = 0; $wagered = 0; $pnl = 0;
    if ($stats && $row = $stats->fetch_assoc()) {
        $total = (int)$row['total'];
        $wins = (int)$row['wins'];
        $losses = (int)$row['losses'];
        $pushes = (int)$row['pushes'];
        $wagered = (float)$row['wagered'];
        $pnl = (float)$row['pnl'];
    }

    $win_rate = $total > 0 ? round(($wins / $total) * 100, 2) : 0;
    $roi = $wagered > 0 ? round(($pnl / $wagered) * 100, 2) : 0;

    $conn->query("REPLACE INTO lm_sports_bankroll (snapshot_date, bankroll, total_bets, total_wins, total_losses, total_pushes, win_rate, total_wagered, total_pnl, roi_pct) VALUES ("
        . "CURDATE(), " . (float)$bankroll . ", " . $total . ", " . $wins . ", " . $losses . ", " . $pushes . ", "
        . $win_rate . ", " . (float)$wagered . ", " . (float)$pnl . ", " . $roi . ")");
}

// ────────────────────────────────────────────────────────────
//  Action routing
// ────────────────────────────────────────────────────────────

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'dashboard';

if ($action === 'place') {
    _sb_action_place($conn);
} elseif ($action === 'active') {
    _sb_action_active($conn);
} elseif ($action === 'settle') {
    _sb_action_settle($conn);
} elseif ($action === 'history') {
    _sb_action_history($conn);
} elseif ($action === 'dashboard') {
    _sb_action_dashboard($conn);
} elseif ($action === 'leaderboard') {
    _sb_action_leaderboard($conn);
} elseif ($action === 'reset') {
    _sb_action_reset($conn);
} else {
    header('HTTP/1.0 400 Bad Request');
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;

// ════════════════════════════════════════════════════════════
//  ACTION: place — Place a paper bet
// ════════════════════════════════════════════════════════════

function _sb_action_place($conn) {
    global $ADMIN_KEY, $MAX_ACTIVE_BETS, $MIN_BET, $MAX_BET_PCT;

    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    // Required params
    $event_id   = isset($_GET['event_id']) ? trim($_GET['event_id']) : '';
    $sport      = isset($_GET['sport']) ? trim($_GET['sport']) : '';
    $market     = isset($_GET['market']) ? trim($_GET['market']) : 'h2h';
    $pick       = isset($_GET['pick']) ? trim($_GET['pick']) : '';
    $bookmaker  = isset($_GET['bookmaker']) ? trim($_GET['bookmaker']) : '';
    $bm_key     = isset($_GET['bookmaker_key']) ? trim($_GET['bookmaker_key']) : '';
    $odds       = isset($_GET['odds']) ? (float)$_GET['odds'] : 0;
    $algorithm  = isset($_GET['algorithm']) ? trim($_GET['algorithm']) : 'value_bet';
    $ev_pct     = isset($_GET['ev_pct']) ? (float)$_GET['ev_pct'] : 0;
    $pick_point = isset($_GET['pick_point']) ? (float)$_GET['pick_point'] : null;

    if (!$event_id || !$sport || !$pick || $odds <= 1.0) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing required params: event_id, sport, pick, odds (>1.0)'));
        return;
    }

    // Check active bet limit
    $active_q = $conn->query("SELECT COUNT(*) as cnt FROM lm_sports_bets WHERE status='pending'");
    if ($active_q && $row = $active_q->fetch_assoc()) {
        if ((int)$row['cnt'] >= $MAX_ACTIVE_BETS) {
            echo json_encode(array('ok' => false, 'error' => 'Max active bets reached (' . $MAX_ACTIVE_BETS . ')'));
            return;
        }
    }

    // Get bankroll for sizing
    $bankroll = _sb_get_bankroll($conn);

    // Bet amount: use provided or Kelly
    $bet_amount = isset($_GET['bet_amount']) ? (float)$_GET['bet_amount'] : 0;
    if ($bet_amount <= 0) {
        // Quarter-Kelly sizing
        if ($ev_pct > 0 && $odds > 1.0) {
            $ev_decimal = $ev_pct / 100.0;
            $kelly = $ev_decimal / ($odds - 1.0);
            $quarter_kelly = $kelly / 4.0;
            $bet_amount = round($bankroll * min($quarter_kelly, $MAX_BET_PCT), 2);
        } else {
            // Default 2% of bankroll
            $bet_amount = round($bankroll * 0.02, 2);
        }
    }
    $bet_amount = max($MIN_BET, min($bet_amount, $bankroll * $MAX_BET_PCT));

    if ($bet_amount > $bankroll) {
        echo json_encode(array('ok' => false, 'error' => 'Insufficient bankroll: $' . round($bankroll, 2)));
        return;
    }

    // Lookup event details
    $home_team = '';
    $away_team = '';
    $commence = '2026-01-01 00:00:00';
    $ev_q = $conn->query("SELECT home_team, away_team, commence_time FROM lm_sports_odds WHERE event_id='"
        . $conn->real_escape_string($event_id) . "' LIMIT 1");
    if ($ev_q && $row = $ev_q->fetch_assoc()) {
        $home_team = $row['home_team'];
        $away_team = $row['away_team'];
        $commence = $row['commence_time'];
    }

    $implied_prob = ($odds > 0) ? round(1.0 / $odds, 4) : 0;
    $potential_payout = round($bet_amount * $odds, 2);

    $bet_type = 'moneyline';
    if ($market === 'spreads') $bet_type = 'spread';
    if ($market === 'totals') $bet_type = 'total';

    $sql = "INSERT INTO lm_sports_bets (event_id, sport, home_team, away_team, commence_time, game_date, "
        . "bet_type, market, pick, pick_point, bookmaker, bookmaker_key, odds, implied_prob, "
        . "bet_amount, potential_payout, algorithm, ev_pct, status, placed_at) VALUES ("
        . "'" . $conn->real_escape_string($event_id) . "', "
        . "'" . $conn->real_escape_string($sport) . "', "
        . "'" . $conn->real_escape_string($home_team) . "', "
        . "'" . $conn->real_escape_string($away_team) . "', "
        . "'" . $conn->real_escape_string($commence) . "', "
        . "DATE(DATE_SUB('" . $conn->real_escape_string($commence) . "', INTERVAL 5 HOUR)), "
        . "'" . $conn->real_escape_string($bet_type) . "', "
        . "'" . $conn->real_escape_string($market) . "', "
        . "'" . $conn->real_escape_string($pick) . "', "
        . ($pick_point !== null ? (float)$pick_point : "NULL") . ", "
        . "'" . $conn->real_escape_string($bookmaker) . "', "
        . "'" . $conn->real_escape_string($bm_key) . "', "
        . (float)$odds . ", " . (float)$implied_prob . ", "
        . (float)$bet_amount . ", " . (float)$potential_payout . ", "
        . "'" . $conn->real_escape_string($algorithm) . "', "
        . (float)$ev_pct . ", 'pending', NOW())";

    $conn->query($sql);
    $bet_id = $conn->insert_id;

    echo json_encode(array(
        'ok'               => true,
        'bet_id'           => $bet_id,
        'event'            => $away_team . ' @ ' . $home_team,
        'pick'             => $pick,
        'market'           => $market,
        'bookmaker'        => $bookmaker,
        'odds'             => $odds,
        'bet_amount'       => $bet_amount,
        'potential_payout' => $potential_payout,
        'game_date'        => date('Y-m-d', strtotime($commence . ' -5 hours')),
        'bankroll_after'   => round($bankroll - $bet_amount, 2)
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: active — List pending bets
// ════════════════════════════════════════════════════════════

function _sb_action_active($conn) {
    global $SPORT_SHORT;

    $result = $conn->query("SELECT * FROM lm_sports_bets WHERE status='pending' ORDER BY commence_time ASC");
    $bets = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $row['sport_short'] = isset($SPORT_SHORT[$row['sport']]) ? $SPORT_SHORT[$row['sport']] : $row['sport'];
            $bets[] = $row;
        }
    }

    echo json_encode(array(
        'ok'    => true,
        'bets'  => $bets,
        'count' => count($bets)
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: settle — Auto-settle completed bets using scores API
// ════════════════════════════════════════════════════════════

function _sb_action_settle($conn) {
    global $ADMIN_KEY, $API_BASE, $THE_ODDS_API_KEY;

    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    // Get pending bets grouped by sport
    $pending_q = $conn->query("SELECT DISTINCT sport FROM lm_sports_bets WHERE status='pending'");
    if (!$pending_q || $pending_q->num_rows === 0) {
        echo json_encode(array('ok' => true, 'settled' => 0, 'message' => 'No pending bets'));
        return;
    }

    $sports = array();
    while ($row = $pending_q->fetch_assoc()) {
        $sports[] = $row['sport'];
    }

    $settled = 0;
    $won = 0;
    $lost = 0;
    $push = 0;
    $net_pnl = 0;
    $details = array();

    foreach ($sports as $sport) {
        // Fetch scores from The Odds API (free, 0 credits)
        $scores_url = $API_BASE . '/sports/' . $sport . '/scores/?apiKey=' . $THE_ODDS_API_KEY . '&daysFrom=3&dateFormat=iso';
        $body = _sb_http_get($scores_url);
        if ($body === null) continue;

        $scores = json_decode($body, true);
        if (!is_array($scores)) continue;

        // Build score map: event_id → {completed, home_score, away_score}
        $score_map = array();
        foreach ($scores as $game) {
            $gid = isset($game['id']) ? $game['id'] : '';
            $completed = isset($game['completed']) && $game['completed'];
            if (!$gid || !$completed) continue;

            $home_score = null;
            $away_score = null;
            $home_team = isset($game['home_team']) ? $game['home_team'] : '';
            $away_team = isset($game['away_team']) ? $game['away_team'] : '';

            if (isset($game['scores']) && is_array($game['scores'])) {
                foreach ($game['scores'] as $sc) {
                    $name = isset($sc['name']) ? $sc['name'] : '';
                    $score = isset($sc['score']) ? (int)$sc['score'] : 0;
                    if ($name === $home_team) $home_score = $score;
                    if ($name === $away_team) $away_score = $score;
                }
            }

            if ($home_score !== null && $away_score !== null) {
                $score_map[$gid] = array(
                    'home_score' => $home_score,
                    'away_score' => $away_score,
                    'home_team'  => $home_team,
                    'away_team'  => $away_team
                );
            }
        }

        // Settle pending bets for this sport
        $bets_q = $conn->query("SELECT * FROM lm_sports_bets WHERE status='pending' AND sport='"
            . $conn->real_escape_string($sport) . "'");
        if (!$bets_q) continue;

        while ($bet = $bets_q->fetch_assoc()) {
            $eid = $bet['event_id'];
            if (!isset($score_map[$eid])) continue;

            $sc = $score_map[$eid];
            $result = _sb_determine_result($bet, $sc['home_score'], $sc['away_score'], $sc['home_team'], $sc['away_team']);

            if ($result === null) continue;

            $pnl = 0;
            if ($result === 'won') {
                $pnl = round((float)$bet['potential_payout'] - (float)$bet['bet_amount'], 2);
                $won++;
            } elseif ($result === 'lost') {
                $pnl = -1 * (float)$bet['bet_amount'];
                $lost++;
            } else {
                // push
                $pnl = 0;
                $push++;
            }

            $conn->query("UPDATE lm_sports_bets SET "
                . "status='settled', result='" . $conn->real_escape_string($result) . "', "
                . "pnl=" . (float)$pnl . ", "
                . "actual_home_score=" . (int)$sc['home_score'] . ", "
                . "actual_away_score=" . (int)$sc['away_score'] . ", "
                . "settled_at=NOW() "
                . "WHERE id=" . (int)$bet['id']);

            $settled++;
            $net_pnl += $pnl;

            $details[] = array(
                'bet_id' => (int)$bet['id'],
                'event'  => $bet['away_team'] . ' @ ' . $bet['home_team'],
                'pick'   => $bet['pick'],
                'result' => $result,
                'pnl'    => $pnl,
                'score'  => $sc['away_score'] . '-' . $sc['home_score']
            );
        }
    }

    // Void bets pending > 7 days
    $voided = 0;
    $void_q = $conn->query("UPDATE lm_sports_bets SET status='settled', result='void', pnl=0, settled_at=NOW() WHERE status='pending' AND placed_at < DATE_SUB(NOW(), INTERVAL 7 DAY)");
    if ($void_q) {
        $voided = $conn->affected_rows;
    }

    // Take snapshot
    _sb_snapshot($conn);

    echo json_encode(array(
        'ok'       => true,
        'settled'  => $settled,
        'won'      => $won,
        'lost'     => $lost,
        'push'     => $push,
        'voided'   => $voided,
        'net_pnl'  => round($net_pnl, 2),
        'bankroll' => _sb_get_bankroll($conn),
        'details'  => $details
    ));
}

// ────────────────────────────────────────────────────────────
//  Helper: determine bet result from scores
// ────────────────────────────────────────────────────────────

function _sb_determine_result($bet, $home_score, $away_score, $home_team, $away_team) {
    $market = $bet['market'];
    $pick = $bet['pick'];
    $pick_point = $bet['pick_point'] !== null ? (float)$bet['pick_point'] : null;

    if ($market === 'h2h') {
        // Moneyline — who won?
        if ($home_score === $away_score) return 'push'; // Tie (rare in most sports)
        $winner = ($home_score > $away_score) ? $home_team : $away_team;
        // Draw case for soccer
        if ($pick === 'Draw' || $pick === 'draw') {
            return ($home_score === $away_score) ? 'won' : 'lost';
        }
        return ($pick === $winner) ? 'won' : 'lost';

    } elseif ($market === 'spreads') {
        // Spread — pick team + point spread
        if ($pick_point === null) return null;

        // Determine pick's score
        $pick_score = 0;
        $opp_score = 0;
        if ($pick === $home_team) {
            $pick_score = $home_score;
            $opp_score = $away_score;
        } elseif ($pick === $away_team) {
            $pick_score = $away_score;
            $opp_score = $home_score;
        } else {
            return null; // Can't match pick to team
        }

        // Adjusted score = pick's score + spread
        $adjusted = $pick_score + $pick_point;
        if ($adjusted > $opp_score) return 'won';
        if ($adjusted < $opp_score) return 'lost';
        return 'push'; // Exact push

    } elseif ($market === 'totals') {
        // Over/Under — combined score vs line
        if ($pick_point === null) return null;
        $total_score = $home_score + $away_score;

        if (strtolower($pick) === 'over') {
            if ($total_score > $pick_point) return 'won';
            if ($total_score < $pick_point) return 'lost';
            return 'push';
        } elseif (strtolower($pick) === 'under') {
            if ($total_score < $pick_point) return 'won';
            if ($total_score > $pick_point) return 'lost';
            return 'push';
        }
    }

    return null;
}

// ════════════════════════════════════════════════════════════
//  ACTION: history — Settled bets
// ════════════════════════════════════════════════════════════

function _sb_action_history($conn) {
    global $SPORT_SHORT;

    $sport = isset($_GET['sport']) ? $conn->real_escape_string(trim($_GET['sport'])) : '';
    $algorithm = isset($_GET['algorithm']) ? $conn->real_escape_string(trim($_GET['algorithm'])) : '';
    $page = isset($_GET['page']) ? max(1, (int)$_GET['page']) : 1;
    $per_page = 50;
    $offset = ($page - 1) * $per_page;

    $where = "result IS NOT NULL";
    if ($sport) $where .= " AND sport='" . $sport . "'";
    if ($algorithm) $where .= " AND algorithm='" . $algorithm . "'";

    // Count total
    $cnt_q = $conn->query("SELECT COUNT(*) as total FROM lm_sports_bets WHERE " . $where);
    $total = 0;
    if ($cnt_q && $row = $cnt_q->fetch_assoc()) $total = (int)$row['total'];

    $result = $conn->query("SELECT * FROM lm_sports_bets WHERE " . $where . " ORDER BY settled_at DESC LIMIT " . $per_page . " OFFSET " . $offset);

    $bets = array();
    $running_pnl = 0;
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $row['sport_short'] = isset($SPORT_SHORT[$row['sport']]) ? $SPORT_SHORT[$row['sport']] : $row['sport'];
            $running_pnl += (float)$row['pnl'];
            $row['running_pnl'] = round($running_pnl, 2);
            $bets[] = $row;
        }
    }

    echo json_encode(array(
        'ok'       => true,
        'bets'     => $bets,
        'count'    => count($bets),
        'total'    => $total,
        'page'     => $page,
        'pages'    => ceil($total / $per_page),
        'filters'  => array('sport' => $sport, 'algorithm' => $algorithm)
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: dashboard — Bankroll + comprehensive stats
// ════════════════════════════════════════════════════════════

function _sb_action_dashboard($conn) {
    global $INITIAL_BANKROLL, $SPORT_SHORT;

    $bankroll = _sb_get_bankroll($conn);

    // Overall stats
    $stats = $conn->query("SELECT COUNT(*) as total, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "SUM(CASE WHEN result='push' THEN 1 ELSE 0 END) as pushes, "
        . "SUM(CASE WHEN result='void' THEN 1 ELSE 0 END) as voided, "
        . "COALESCE(SUM(bet_amount), 0) as wagered, "
        . "COALESCE(SUM(pnl), 0) as pnl, "
        . "COALESCE(MAX(pnl), 0) as best_bet, "
        . "COALESCE(MIN(pnl), 0) as worst_bet "
        . "FROM lm_sports_bets WHERE result IS NOT NULL");

    $total = 0; $wins = 0; $losses = 0; $pushes = 0; $voided = 0;
    $wagered = 0; $pnl = 0; $best_bet = 0; $worst_bet = 0;
    if ($stats && $row = $stats->fetch_assoc()) {
        $total = (int)$row['total'];
        $wins = (int)$row['wins'];
        $losses = (int)$row['losses'];
        $pushes = (int)$row['pushes'];
        $voided = (int)$row['voided'];
        $wagered = (float)$row['wagered'];
        $pnl = (float)$row['pnl'];
        $best_bet = (float)$row['best_bet'];
        $worst_bet = (float)$row['worst_bet'];
    }

    $win_rate = ($wins + $losses) > 0 ? round(($wins / ($wins + $losses)) * 100, 1) : 0;
    $roi = $wagered > 0 ? round(($pnl / $wagered) * 100, 2) : 0;

    // Active bets
    $active_q = $conn->query("SELECT COUNT(*) as cnt, COALESCE(SUM(bet_amount), 0) as reserved FROM lm_sports_bets WHERE status='pending'");
    $active_count = 0; $reserved = 0;
    if ($active_q && $row = $active_q->fetch_assoc()) {
        $active_count = (int)$row['cnt'];
        $reserved = (float)$row['reserved'];
    }

    // By sport breakdown
    $sport_q = $conn->query("SELECT sport, COUNT(*) as bets, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "COALESCE(SUM(pnl), 0) as pnl, "
        . "COALESCE(SUM(bet_amount), 0) as wagered "
        . "FROM lm_sports_bets WHERE result IS NOT NULL GROUP BY sport ORDER BY pnl DESC");

    $by_sport = array();
    if ($sport_q) {
        while ($row = $sport_q->fetch_assoc()) {
            $row['sport_short'] = isset($SPORT_SHORT[$row['sport']]) ? $SPORT_SHORT[$row['sport']] : $row['sport'];
            $w = (int)$row['wins'];
            $l = (int)$row['losses'];
            $row['win_rate'] = ($w + $l) > 0 ? round(($w / ($w + $l)) * 100, 1) : 0;
            $row['roi'] = (float)$row['wagered'] > 0 ? round(((float)$row['pnl'] / (float)$row['wagered']) * 100, 2) : 0;
            $by_sport[] = $row;
        }
    }

    // By algorithm breakdown
    $algo_q = $conn->query("SELECT algorithm, COUNT(*) as bets, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "COALESCE(SUM(pnl), 0) as pnl, "
        . "COALESCE(SUM(bet_amount), 0) as wagered "
        . "FROM lm_sports_bets WHERE result IS NOT NULL GROUP BY algorithm ORDER BY pnl DESC");

    $by_algorithm = array();
    if ($algo_q) {
        while ($row = $algo_q->fetch_assoc()) {
            $w = (int)$row['wins'];
            $l = (int)$row['losses'];
            $row['win_rate'] = ($w + $l) > 0 ? round(($w / ($w + $l)) * 100, 1) : 0;
            $row['roi'] = (float)$row['wagered'] > 0 ? round(((float)$row['pnl'] / (float)$row['wagered']) * 100, 2) : 0;
            $by_algorithm[] = $row;
        }
    }

    // Bankroll history (last 30 snapshots)
    $hist_q = $conn->query("SELECT * FROM lm_sports_bankroll ORDER BY snapshot_date DESC LIMIT 30");
    $bankroll_history = array();
    if ($hist_q) {
        while ($row = $hist_q->fetch_assoc()) {
            $bankroll_history[] = $row;
        }
    }
    $bankroll_history = array_reverse($bankroll_history);

    // Recent bets
    $recent_q = $conn->query("SELECT * FROM lm_sports_bets ORDER BY placed_at DESC LIMIT 10");
    $recent = array();
    if ($recent_q) {
        while ($row = $recent_q->fetch_assoc()) {
            $row['sport_short'] = isset($SPORT_SHORT[$row['sport']]) ? $SPORT_SHORT[$row['sport']] : $row['sport'];
            $recent[] = $row;
        }
    }

    echo json_encode(array(
        'ok'                => true,
        'bankroll'          => round($bankroll, 2),
        'initial_bankroll'  => $INITIAL_BANKROLL,
        'bankroll_change'   => round($bankroll - $INITIAL_BANKROLL, 2),
        'total_bets'        => $total,
        'total_wins'        => $wins,
        'total_losses'      => $losses,
        'total_pushes'      => $pushes,
        'total_voided'      => $voided,
        'win_rate'          => $win_rate,
        'total_wagered'     => round($wagered, 2),
        'total_pnl'         => round($pnl, 2),
        'roi_pct'           => $roi,
        'best_bet'          => $best_bet,
        'worst_bet'         => $worst_bet,
        'active_bets'       => $active_count,
        'reserved_amount'   => round($reserved, 2),
        'available_bankroll' => round($bankroll - $reserved, 2),
        'by_sport'          => $by_sport,
        'by_algorithm'      => $by_algorithm,
        'bankroll_history'  => $bankroll_history,
        'recent_bets'       => $recent
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: leaderboard — Algorithm performance
// ════════════════════════════════════════════════════════════

function _sb_action_leaderboard($conn) {
    $result = $conn->query("SELECT algorithm, COUNT(*) as bets, "
        . "SUM(CASE WHEN result='won' THEN 1 ELSE 0 END) as wins, "
        . "SUM(CASE WHEN result='lost' THEN 1 ELSE 0 END) as losses, "
        . "SUM(CASE WHEN result='push' THEN 1 ELSE 0 END) as pushes, "
        . "COALESCE(SUM(pnl), 0) as total_pnl, "
        . "COALESCE(SUM(bet_amount), 0) as total_wagered, "
        . "COALESCE(AVG(CASE WHEN result='won' THEN pnl ELSE NULL END), 0) as avg_win, "
        . "COALESCE(AVG(CASE WHEN result='lost' THEN pnl ELSE NULL END), 0) as avg_loss "
        . "FROM lm_sports_bets WHERE result IS NOT NULL GROUP BY algorithm HAVING bets >= 1 ORDER BY total_pnl DESC");

    $algos = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $w = (int)$row['wins'];
            $l = (int)$row['losses'];
            $row['win_rate'] = ($w + $l) > 0 ? round(($w / ($w + $l)) * 100, 1) : 0;
            $row['roi'] = (float)$row['total_wagered'] > 0 ? round(((float)$row['total_pnl'] / (float)$row['total_wagered']) * 100, 2) : 0;
            $algos[] = $row;
        }
    }

    echo json_encode(array(
        'ok'          => true,
        'algorithms'  => $algos,
        'count'       => count($algos)
    ));
}

// ════════════════════════════════════════════════════════════
//  ACTION: reset — Truncate tables
// ════════════════════════════════════════════════════════════

function _sb_action_reset($conn) {
    global $ADMIN_KEY;

    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        return;
    }

    $confirm = isset($_GET['confirm']) ? trim($_GET['confirm']) : '';
    if ($confirm !== 'yes') {
        echo json_encode(array('ok' => false, 'error' => 'Add &confirm=yes to confirm reset'));
        return;
    }

    $conn->query("TRUNCATE TABLE lm_sports_bets");
    $conn->query("TRUNCATE TABLE lm_sports_bankroll");

    echo json_encode(array('ok' => true, 'message' => 'Paper betting data reset. Bankroll back to $1000.'));
}

?>
