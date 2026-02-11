<?php
/**
 * penny_stock_picks.php — Daily penny stock picks API.
 * Stores and serves scored penny stock picks from the Python engine.
 *
 * Actions:
 *   picks       — GET latest daily picks (public)
 *   history     — GET pick history with performance (public)
 *   detail      — GET detailed scoring for a ticker (public)
 *   performance — GET aggregate performance stats (public)
 *   store_picks — POST daily picks from Python engine (admin key required)
 *   track       — POST update pick tracking/performance (admin key required)
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

// ── DB connection ──
$servername = 'mysql.50webs.com';
$username   = 'ejaguiar1_stocks';
$password   = 'stocks';
$dbname     = 'ejaguiar1_stocks';

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

// ── Schema (auto-create tables) ──
$conn->query("CREATE TABLE IF NOT EXISTS penny_picks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pick_date DATE NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    name VARCHAR(200) NOT NULL DEFAULT '',
    price DECIMAL(10,4) NOT NULL DEFAULT 0,
    composite_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    rating VARCHAR(20) NOT NULL DEFAULT 'HOLD',
    market_cap BIGINT NOT NULL DEFAULT 0,
    exchange_name VARCHAR(30) NOT NULL DEFAULT '',
    country VARCHAR(5) NOT NULL DEFAULT '',
    rrsp_eligible TINYINT NOT NULL DEFAULT 0,
    avg_volume INT NOT NULL DEFAULT 0,
    stop_loss_pct DECIMAL(5,2) NOT NULL DEFAULT 15,
    take_profit_pct DECIMAL(5,2) NOT NULL DEFAULT 30,
    max_hold_days INT NOT NULL DEFAULT 90,
    position_size_pct DECIMAL(5,2) NOT NULL DEFAULT 1.5,
    health_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    momentum_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    volume_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    technical_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    earnings_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    smart_money_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    quality_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    z_score DECIMAL(6,2) NOT NULL DEFAULT 0,
    f_score INT NOT NULL DEFAULT 0,
    current_ratio DECIMAL(6,2) NOT NULL DEFAULT 0,
    rsi DECIMAL(5,1) NOT NULL DEFAULT 50,
    ema_alignment INT NOT NULL DEFAULT 0,
    rvol DECIMAL(6,2) NOT NULL DEFAULT 1,
    mom_3m DECIMAL(8,2) NOT NULL DEFAULT 0,
    mom_6m DECIMAL(8,2) NOT NULL DEFAULT 0,
    inst_pct DECIMAL(5,1) NOT NULL DEFAULT 0,
    short_pct DECIMAL(5,1) NOT NULL DEFAULT 0,
    ann_volatility DECIMAL(6,1) NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    current_price DECIMAL(10,4) NOT NULL DEFAULT 0,
    current_return_pct DECIMAL(8,2) NOT NULL DEFAULT 0,
    exit_price DECIMAL(10,4) NOT NULL DEFAULT 0,
    exit_date DATE DEFAULT NULL,
    exit_reason VARCHAR(50) NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL,
    KEY idx_date (pick_date),
    KEY idx_symbol (symbol),
    KEY idx_score (composite_score),
    KEY idx_rating (rating),
    KEY idx_status (status)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS penny_picks_daily (
    id INT AUTO_INCREMENT PRIMARY KEY,
    snap_date DATE NOT NULL,
    total_scored INT NOT NULL DEFAULT 0,
    top_picks_count INT NOT NULL DEFAULT 0,
    avg_score DECIMAL(5,2) NOT NULL DEFAULT 0,
    buy_count INT NOT NULL DEFAULT 0,
    strong_buy_count INT NOT NULL DEFAULT 0,
    active_picks INT NOT NULL DEFAULT 0,
    closed_picks INT NOT NULL DEFAULT 0,
    win_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    avg_return_pct DECIMAL(8,2) NOT NULL DEFAULT 0,
    total_return_pct DECIMAL(8,2) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    KEY idx_date (snap_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ── Admin key check ──
$admin_key = 'livetrader2026';

function _pp_require_admin() {
    global $admin_key;
    $key = isset($_GET['key']) ? $_GET['key'] : '';
    if ($key !== $admin_key) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid admin key'));
        exit;
    }
}

// ── Action routing ──
$action = isset($_GET['action']) ? $_GET['action'] : 'picks';

// ===========================================================================
// ACTION: picks — Get latest daily picks
// ===========================================================================
if ($action === 'picks') {
    $date = isset($_GET['date']) ? $conn->real_escape_string($_GET['date']) : '';
    $country = isset($_GET['country']) ? $conn->real_escape_string(strtoupper($_GET['country'])) : '';
    $min_score = isset($_GET['min_score']) ? floatval($_GET['min_score']) : 0;
    $limit = isset($_GET['limit']) ? min(50, max(1, intval($_GET['limit']))) : 20;

    // Get the most recent pick date if not specified
    if ($date === '') {
        $r = $conn->query("SELECT MAX(pick_date) as d FROM penny_picks");
        if ($r && $row = $r->fetch_assoc()) {
            $date = $row['d'];
        }
        if (!$date) {
            echo json_encode(array('ok' => true, 'picks' => array(), 'message' => 'No picks available yet'));
            exit;
        }
    }

    $where = "pick_date = '" . $conn->real_escape_string($date) . "'";
    if ($country !== '' && $country !== 'ALL') {
        $where .= " AND country = '" . $conn->real_escape_string($country) . "'";
    }
    if ($min_score > 0) {
        $where .= " AND composite_score >= " . floatval($min_score);
    }

    $sql = "SELECT * FROM penny_picks WHERE $where ORDER BY composite_score DESC LIMIT $limit";
    $r = $conn->query($sql);

    $picks = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $picks[] = array(
                'id'               => intval($row['id']),
                'pick_date'        => $row['pick_date'],
                'symbol'           => $row['symbol'],
                'name'             => $row['name'],
                'price'            => floatval($row['price']),
                'composite_score'  => floatval($row['composite_score']),
                'rating'           => $row['rating'],
                'market_cap'       => intval($row['market_cap']),
                'exchange'         => $row['exchange_name'],
                'country'          => $row['country'],
                'rrsp_eligible'    => intval($row['rrsp_eligible']) === 1,
                'avg_volume'       => intval($row['avg_volume']),
                'stop_loss_pct'    => floatval($row['stop_loss_pct']),
                'take_profit_pct'  => floatval($row['take_profit_pct']),
                'max_hold_days'    => intval($row['max_hold_days']),
                'position_size_pct'=> floatval($row['position_size_pct']),
                'factor_scores' => array(
                    'health'     => floatval($row['health_score']),
                    'momentum'   => floatval($row['momentum_score']),
                    'volume'     => floatval($row['volume_score']),
                    'technical'  => floatval($row['technical_score']),
                    'earnings'   => floatval($row['earnings_score']),
                    'smart_money'=> floatval($row['smart_money_score']),
                    'quality'    => floatval($row['quality_score']),
                ),
                'metrics' => array(
                    'z_score'        => floatval($row['z_score']),
                    'f_score'        => intval($row['f_score']),
                    'current_ratio'  => floatval($row['current_ratio']),
                    'rsi'            => floatval($row['rsi']),
                    'ema_alignment'  => intval($row['ema_alignment']),
                    'rvol'           => floatval($row['rvol']),
                    'mom_3m'         => floatval($row['mom_3m']),
                    'mom_6m'         => floatval($row['mom_6m']),
                    'inst_pct'       => floatval($row['inst_pct']),
                    'short_pct'      => floatval($row['short_pct']),
                    'volatility'     => floatval($row['ann_volatility']),
                ),
                'status'             => $row['status'],
                'current_price'      => floatval($row['current_price']),
                'current_return_pct' => floatval($row['current_return_pct']),
                'exit_price'         => floatval($row['exit_price']),
                'exit_date'          => $row['exit_date'],
                'exit_reason'        => $row['exit_reason'],
            );
        }
    }

    echo json_encode(array(
        'ok'        => true,
        'date'      => $date,
        'count'     => count($picks),
        'picks'     => $picks,
        'timestamp' => date('Y-m-d H:i:s')
    ));
    exit;
}

// ===========================================================================
// ACTION: history — Get pick history with performance
// ===========================================================================
if ($action === 'history') {
    $days = isset($_GET['days']) ? min(90, max(1, intval($_GET['days']))) : 30;
    $symbol = isset($_GET['symbol']) ? $conn->real_escape_string($_GET['symbol']) : '';

    $where = "pick_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)";
    if ($symbol !== '') {
        $where .= " AND symbol = '" . $conn->real_escape_string($symbol) . "'";
    }

    $sql = "SELECT symbol, name, pick_date, price, composite_score, rating, status,
                   current_price, current_return_pct, exit_price, exit_date, exit_reason,
                   exchange_name, country
            FROM penny_picks WHERE $where ORDER BY pick_date DESC, composite_score DESC";
    $r = $conn->query($sql);

    $history = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $history[] = array(
                'symbol'         => $row['symbol'],
                'name'           => $row['name'],
                'pick_date'      => $row['pick_date'],
                'entry_price'    => floatval($row['price']),
                'score'          => floatval($row['composite_score']),
                'rating'         => $row['rating'],
                'status'         => $row['status'],
                'current_price'  => floatval($row['current_price']),
                'return_pct'     => floatval($row['current_return_pct']),
                'exit_price'     => floatval($row['exit_price']),
                'exit_date'      => $row['exit_date'],
                'exit_reason'    => $row['exit_reason'],
                'exchange'       => $row['exchange_name'],
                'country'        => $row['country'],
            );
        }
    }

    echo json_encode(array(
        'ok'      => true,
        'days'    => $days,
        'count'   => count($history),
        'history' => $history,
    ));
    exit;
}

// ===========================================================================
// ACTION: performance — Aggregate performance stats
// ===========================================================================
if ($action === 'performance') {
    $days = isset($_GET['days']) ? min(365, max(7, intval($_GET['days']))) : 30;

    // Overall stats
    $sql = "SELECT
                COUNT(*) as total_picks,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active,
                SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed,
                SUM(CASE WHEN status = 'closed' AND current_return_pct > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN status = 'closed' AND current_return_pct <= 0 THEN 1 ELSE 0 END) as losses,
                AVG(CASE WHEN status = 'closed' THEN current_return_pct ELSE NULL END) as avg_return,
                SUM(CASE WHEN status = 'closed' THEN current_return_pct ELSE 0 END) as total_return,
                MAX(CASE WHEN status = 'closed' THEN current_return_pct ELSE NULL END) as best_return,
                MIN(CASE WHEN status = 'closed' THEN current_return_pct ELSE NULL END) as worst_return,
                AVG(composite_score) as avg_score
            FROM penny_picks
            WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)";
    $r = $conn->query($sql);
    $stats = $r ? $r->fetch_assoc() : array();

    $closed = intval($stats['closed']);
    $wins = intval($stats['wins']);
    $win_rate = $closed > 0 ? round($wins / $closed * 100, 1) : 0;

    // By rating
    $sql2 = "SELECT rating,
                COUNT(*) as cnt,
                AVG(current_return_pct) as avg_ret,
                SUM(CASE WHEN current_return_pct > 0 THEN 1 ELSE 0 END) as w
             FROM penny_picks
             WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)
                   AND status = 'closed'
             GROUP BY rating ORDER BY avg_ret DESC";
    $r2 = $conn->query($sql2);
    $by_rating = array();
    if ($r2) {
        while ($row = $r2->fetch_assoc()) {
            $cnt = intval($row['cnt']);
            $by_rating[] = array(
                'rating'   => $row['rating'],
                'count'    => $cnt,
                'avg_return' => round(floatval($row['avg_ret']), 2),
                'win_rate' => $cnt > 0 ? round(intval($row['w']) / $cnt * 100, 1) : 0,
            );
        }
    }

    // Daily snapshots
    $sql3 = "SELECT * FROM penny_picks_daily
             WHERE snap_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)
             ORDER BY snap_date DESC LIMIT 30";
    $r3 = $conn->query($sql3);
    $daily = array();
    if ($r3) {
        while ($row = $r3->fetch_assoc()) {
            $daily[] = array(
                'date'        => $row['snap_date'],
                'total'       => intval($row['total_scored']),
                'picks'       => intval($row['top_picks_count']),
                'avg_score'   => floatval($row['avg_score']),
                'win_rate'    => floatval($row['win_rate']),
                'avg_return'  => floatval($row['avg_return_pct']),
            );
        }
    }

    echo json_encode(array(
        'ok'         => true,
        'days'       => $days,
        'stats' => array(
            'total_picks'  => intval($stats['total_picks']),
            'active'       => intval($stats['active']),
            'closed'       => $closed,
            'wins'         => $wins,
            'losses'       => intval($stats['losses']),
            'win_rate'     => $win_rate,
            'avg_return'   => round(floatval($stats['avg_return']), 2),
            'total_return'  => round(floatval($stats['total_return']), 2),
            'best_return'  => round(floatval($stats['best_return']), 2),
            'worst_return' => round(floatval($stats['worst_return']), 2),
            'avg_score'    => round(floatval($stats['avg_score']), 1),
        ),
        'by_rating'  => $by_rating,
        'daily'      => $daily,
    ));
    exit;
}

// ===========================================================================
// ACTION: detail — Detailed scoring for a specific ticker
// ===========================================================================
if ($action === 'detail') {
    $symbol = isset($_GET['symbol']) ? $conn->real_escape_string(strtoupper($_GET['symbol'])) : '';
    if ($symbol === '') {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'symbol required'));
        exit;
    }

    $sql = "SELECT * FROM penny_picks WHERE symbol = '$symbol' ORDER BY pick_date DESC LIMIT 10";
    $r = $conn->query($sql);

    $entries = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $entries[] = array(
                'pick_date'       => $row['pick_date'],
                'price'           => floatval($row['price']),
                'composite_score' => floatval($row['composite_score']),
                'rating'          => $row['rating'],
                'status'          => $row['status'],
                'current_return'  => floatval($row['current_return_pct']),
                'factor_scores' => array(
                    'health'     => floatval($row['health_score']),
                    'momentum'   => floatval($row['momentum_score']),
                    'volume'     => floatval($row['volume_score']),
                    'technical'  => floatval($row['technical_score']),
                    'earnings'   => floatval($row['earnings_score']),
                    'smart_money'=> floatval($row['smart_money_score']),
                    'quality'    => floatval($row['quality_score']),
                ),
                'metrics' => array(
                    'z_score'       => floatval($row['z_score']),
                    'f_score'       => intval($row['f_score']),
                    'current_ratio' => floatval($row['current_ratio']),
                    'rsi'           => floatval($row['rsi']),
                    'mom_3m'        => floatval($row['mom_3m']),
                    'mom_6m'        => floatval($row['mom_6m']),
                    'volatility'    => floatval($row['ann_volatility']),
                ),
            );
        }
    }

    echo json_encode(array(
        'ok'      => true,
        'symbol'  => $symbol,
        'entries' => $entries,
    ));
    exit;
}

// ===========================================================================
// ACTION: store_picks — Store daily picks from Python engine (admin)
// ===========================================================================
if ($action === 'store_picks') {
    _pp_require_admin();

    $input = json_decode(file_get_contents('php://input'), true);
    if (!$input || !isset($input['picks']) || !is_array($input['picks'])) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Invalid input: picks array required'));
        exit;
    }

    $date = isset($input['date']) ? $conn->real_escape_string($input['date']) : date('Y-m-d');
    $total_scored = isset($input['total_scored']) ? intval($input['total_scored']) : 0;
    $now = date('Y-m-d H:i:s');
    $stored = 0;
    $errors = 0;

    foreach ($input['picks'] as $p) {
        $symbol = $conn->real_escape_string($p['symbol']);
        $name   = $conn->real_escape_string(substr($p['name'], 0, 200));

        // Check if already exists for this date + symbol
        $check = $conn->query("SELECT id FROM penny_picks WHERE pick_date = '$date' AND symbol = '$symbol'");
        if ($check && $check->num_rows > 0) {
            // Update existing
            $row = $check->fetch_assoc();
            $id = intval($row['id']);
            $sql = "UPDATE penny_picks SET
                composite_score = " . floatval($p['composite_score']) . ",
                rating = '" . $conn->real_escape_string($p['rating']) . "',
                price = " . floatval($p['price']) . ",
                name = '$name',
                market_cap = " . intval($p['market_cap']) . ",
                exchange_name = '" . $conn->real_escape_string($p['exchange']) . "',
                country = '" . $conn->real_escape_string($p['country']) . "',
                rrsp_eligible = " . (isset($p['rrsp_eligible']) && $p['rrsp_eligible'] ? 1 : 0) . ",
                avg_volume = " . intval($p['avg_volume']) . ",
                health_score = " . floatval($p['health_score']) . ",
                momentum_score = " . floatval($p['momentum_score']) . ",
                volume_score = " . floatval($p['volume_score']) . ",
                technical_score = " . floatval($p['technical_score']) . ",
                earnings_score = " . floatval($p['earnings_score']) . ",
                smart_money_score = " . floatval($p['smart_money_score']) . ",
                quality_score = " . floatval($p['quality_score']) . ",
                z_score = " . floatval($p['z_score']) . ",
                f_score = " . intval($p['f_score']) . ",
                current_ratio = " . floatval($p['current_ratio']) . ",
                rsi = " . floatval($p['rsi']) . ",
                ema_alignment = " . intval($p['ema_alignment']) . ",
                rvol = " . floatval($p['rvol']) . ",
                mom_3m = " . floatval($p['mom_3m']) . ",
                mom_6m = " . floatval($p['mom_6m']) . ",
                inst_pct = " . floatval($p['inst_pct']) . ",
                short_pct = " . floatval($p['short_pct']) . ",
                ann_volatility = " . floatval($p['ann_volatility']) . "
                WHERE id = $id";
        } else {
            // Insert new
            $sql = "INSERT INTO penny_picks (
                pick_date, symbol, name, price, composite_score, rating,
                market_cap, exchange_name, country, rrsp_eligible, avg_volume,
                stop_loss_pct, take_profit_pct, max_hold_days, position_size_pct,
                health_score, momentum_score, volume_score, technical_score,
                earnings_score, smart_money_score, quality_score,
                z_score, f_score, current_ratio, rsi, ema_alignment, rvol,
                mom_3m, mom_6m, inst_pct, short_pct, ann_volatility,
                status, created_at
            ) VALUES (
                '$date', '$symbol', '$name',
                " . floatval($p['price']) . ", " . floatval($p['composite_score']) . ",
                '" . $conn->real_escape_string($p['rating']) . "',
                " . intval($p['market_cap']) . ",
                '" . $conn->real_escape_string($p['exchange']) . "',
                '" . $conn->real_escape_string($p['country']) . "',
                " . (isset($p['rrsp_eligible']) && $p['rrsp_eligible'] ? 1 : 0) . ",
                " . intval($p['avg_volume']) . ",
                " . floatval(isset($p['stop_loss_pct']) ? $p['stop_loss_pct'] : 15) . ",
                " . floatval(isset($p['take_profit_pct']) ? $p['take_profit_pct'] : 30) . ",
                " . intval(isset($p['max_hold_days']) ? $p['max_hold_days'] : 90) . ",
                " . floatval(isset($p['position_size_pct']) ? $p['position_size_pct'] : 1.5) . ",
                " . floatval($p['health_score']) . ",
                " . floatval($p['momentum_score']) . ",
                " . floatval($p['volume_score']) . ",
                " . floatval($p['technical_score']) . ",
                " . floatval($p['earnings_score']) . ",
                " . floatval($p['smart_money_score']) . ",
                " . floatval($p['quality_score']) . ",
                " . floatval($p['z_score']) . ",
                " . intval($p['f_score']) . ",
                " . floatval($p['current_ratio']) . ",
                " . floatval($p['rsi']) . ",
                " . intval($p['ema_alignment']) . ",
                " . floatval($p['rvol']) . ",
                " . floatval($p['mom_3m']) . ",
                " . floatval($p['mom_6m']) . ",
                " . floatval($p['inst_pct']) . ",
                " . floatval($p['short_pct']) . ",
                " . floatval($p['ann_volatility']) . ",
                'active', '$now'
            )";
        }

        if ($conn->query($sql)) {
            $stored++;
        } else {
            $errors++;
        }
    }

    // Update daily snapshot
    $buy_count = 0;
    $strong_buy_count = 0;
    $avg_score = 0;
    $score_sum = 0;
    foreach ($input['picks'] as $p) {
        $score_sum += floatval($p['composite_score']);
        if ($p['rating'] === 'BUY') $buy_count++;
        if ($p['rating'] === 'STRONG_BUY') $strong_buy_count++;
    }
    $pick_count = count($input['picks']);
    $avg_score = $pick_count > 0 ? round($score_sum / $pick_count, 2) : 0;

    // Get current active/closed stats
    $sr = $conn->query("SELECT
        SUM(CASE WHEN status='active' THEN 1 ELSE 0 END) as active,
        SUM(CASE WHEN status='closed' THEN 1 ELSE 0 END) as closed,
        AVG(CASE WHEN status='closed' THEN current_return_pct ELSE NULL END) as avg_ret
        FROM penny_picks WHERE pick_date >= DATE_SUB('$date', INTERVAL 30 DAY)");
    $srow = $sr ? $sr->fetch_assoc() : array('active' => 0, 'closed' => 0, 'avg_ret' => 0);

    $closed = intval($srow['closed']);
    $wr = $conn->query("SELECT COUNT(*) as w FROM penny_picks
                         WHERE pick_date >= DATE_SUB('$date', INTERVAL 30 DAY)
                         AND status='closed' AND current_return_pct > 0");
    $wins = 0;
    if ($wr) { $wrow = $wr->fetch_assoc(); $wins = intval($wrow['w']); }
    $win_rate = $closed > 0 ? round($wins / $closed * 100, 1) : 0;

    // Upsert daily snapshot
    $conn->query("DELETE FROM penny_picks_daily WHERE snap_date = '$date'");
    $conn->query("INSERT INTO penny_picks_daily (
        snap_date, total_scored, top_picks_count, avg_score,
        buy_count, strong_buy_count, active_picks, closed_picks,
        win_rate, avg_return_pct, total_return_pct, created_at
    ) VALUES (
        '$date', $total_scored, $pick_count, $avg_score,
        $buy_count, $strong_buy_count,
        " . intval($srow['active']) . ", $closed,
        $win_rate, " . floatval($srow['avg_ret']) . ", 0,
        '$now'
    )");

    echo json_encode(array(
        'ok'      => true,
        'stored'  => $stored,
        'errors'  => $errors,
        'date'    => $date,
        'message' => "Stored $stored picks ($errors errors)"
    ));
    exit;
}

// ===========================================================================
// ACTION: track — Update pick tracking with current prices (admin)
// ===========================================================================
if ($action === 'track') {
    _pp_require_admin();

    $input = json_decode(file_get_contents('php://input'), true);
    if (!$input || !isset($input['updates']) || !is_array($input['updates'])) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Invalid input: updates array required'));
        exit;
    }

    $updated = 0;
    $now = date('Y-m-d');

    foreach ($input['updates'] as $u) {
        $symbol = $conn->real_escape_string($u['symbol']);
        $current_price = floatval($u['current_price']);

        // Get all active picks for this symbol
        $r = $conn->query("SELECT id, price, stop_loss_pct, take_profit_pct, max_hold_days, pick_date
                           FROM penny_picks WHERE symbol = '$symbol' AND status = 'active'");
        if (!$r) continue;

        while ($row = $r->fetch_assoc()) {
            $id = intval($row['id']);
            $entry = floatval($row['price']);
            $sl_pct = floatval($row['stop_loss_pct']);
            $tp_pct = floatval($row['take_profit_pct']);
            $max_hold = intval($row['max_hold_days']);
            $pick_date = $row['pick_date'];

            $return_pct = $entry > 0 ? round(($current_price - $entry) / $entry * 100, 2) : 0;

            // Check exit conditions
            $exit_reason = '';
            $status = 'active';

            if ($return_pct <= -$sl_pct) {
                $exit_reason = 'stop_loss';
                $status = 'closed';
            } elseif ($return_pct >= $tp_pct) {
                $exit_reason = 'take_profit';
                $status = 'closed';
            } else {
                // Check max hold
                $days_held = (strtotime($now) - strtotime($pick_date)) / 86400;
                if ($days_held >= $max_hold) {
                    $exit_reason = 'max_hold';
                    $status = 'closed';
                }
            }

            $sql = "UPDATE penny_picks SET
                current_price = $current_price,
                current_return_pct = $return_pct,
                status = '$status'";
            if ($status === 'closed') {
                $sql .= ", exit_price = $current_price,
                           exit_date = '$now',
                           exit_reason = '$exit_reason'";
            }
            $sql .= " WHERE id = $id";

            if ($conn->query($sql)) $updated++;
        }
    }

    echo json_encode(array(
        'ok'      => true,
        'updated' => $updated,
    ));
    exit;
}

// ── Unknown action ──
header('HTTP/1.0 400 Bad Request');
echo json_encode(array(
    'ok' => false,
    'error' => 'Unknown action: ' . $action,
    'available' => array('picks', 'history', 'performance', 'detail', 'store_picks', 'track')
));
