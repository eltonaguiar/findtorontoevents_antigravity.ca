<?php
/**
 * Tracked Portfolios API - Save, load, and track quick pick portfolios.
 * Monitors daily performance against take profit and stop loss levels.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET  ?action=list                          — list all tracked portfolios
 *   GET  ?action=get&id=123                    — get a specific portfolio with live status
 *   POST ?action=save                          — save a new tracked portfolio (JSON body)
 *   GET  ?action=refresh&id=123                — refresh prices for a portfolio
 *   GET  ?action=refresh_all                   — refresh all active portfolios (for GitHub Actions)
 *   GET  ?action=setup                         — create/update database tables
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? trim($_GET['action']) : 'list';

$response = array('ok' => true, 'action' => $action);

// ─── Setup Tables ───
if ($action === 'setup') {
    $queries = array();

    $queries[] = "CREATE TABLE IF NOT EXISTS tracked_portfolios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(200) NOT NULL,
        strategy_type VARCHAR(50) NOT NULL DEFAULT 'custom',
        category VARCHAR(20) NOT NULL DEFAULT 'swing',
        initial_capital DECIMAL(12,2) NOT NULL DEFAULT 10000.00,
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        total_picks INT NOT NULL DEFAULT 0,
        tp_hits INT NOT NULL DEFAULT 0,
        sl_hits INT NOT NULL DEFAULT 0,
        active_picks INT NOT NULL DEFAULT 0,
        total_return_pct DECIMAL(10,4) DEFAULT 0,
        best_pick VARCHAR(20) DEFAULT NULL,
        worst_pick VARCHAR(20) DEFAULT NULL,
        last_refreshed DATETIME DEFAULT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8";

    $queries[] = "CREATE TABLE IF NOT EXISTS tracked_portfolio_picks (
        id INT AUTO_INCREMENT PRIMARY KEY,
        portfolio_id INT NOT NULL,
        ticker VARCHAR(20) NOT NULL,
        company_name VARCHAR(200) DEFAULT '',
        algorithm VARCHAR(100) DEFAULT '',
        entry_price DECIMAL(12,4) NOT NULL,
        current_price DECIMAL(12,4) DEFAULT NULL,
        take_profit DECIMAL(12,4) NOT NULL,
        stop_loss DECIMAL(12,4) NOT NULL,
        tp_pct DECIMAL(6,2) NOT NULL DEFAULT 10,
        sl_pct DECIMAL(6,2) NOT NULL DEFAULT 5,
        hold_days INT NOT NULL DEFAULT 7,
        status VARCHAR(20) NOT NULL DEFAULT 'active',
        current_return_pct DECIMAL(10,4) DEFAULT 0,
        peak_price DECIMAL(12,4) DEFAULT NULL,
        trough_price DECIMAL(12,4) DEFAULT NULL,
        exit_price DECIMAL(12,4) DEFAULT NULL,
        exit_date DATE DEFAULT NULL,
        exit_reason VARCHAR(50) DEFAULT NULL,
        entry_date DATE NOT NULL,
        days_held INT DEFAULT 0,
        last_price_date DATE DEFAULT NULL,
        created_at DATETIME NOT NULL,
        updated_at DATETIME NOT NULL,
        INDEX idx_portfolio (portfolio_id),
        INDEX idx_status (status),
        INDEX idx_ticker (ticker)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8";

    $errors = array();
    $successes = array();
    foreach ($queries as $q) {
        if ($conn->query($q)) {
            $successes[] = 'OK';
        } else {
            $errors[] = $conn->error;
        }
    }

    $response['tables_created'] = count($successes);
    $response['errors'] = $errors;
    echo json_encode($response);
    $conn->close();
    exit;
}

// ─── List All Tracked Portfolios ───
if ($action === 'list') {
    $sql = "SELECT * FROM tracked_portfolios ORDER BY created_at DESC LIMIT 50";
    $res = $conn->query($sql);

    if (!$res) {
        // Table might not exist yet
        $response['portfolios'] = array();
        $response['note'] = 'No tracked portfolios table. Call ?action=setup first.';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $portfolios = array();
    while ($row = $res->fetch_assoc()) {
        $portfolios[] = $row;
    }
    $response['portfolios'] = $portfolios;
    $response['count'] = count($portfolios);
    echo json_encode($response);
    $conn->close();
    exit;
}

// ─── Get Single Portfolio with Picks ───
if ($action === 'get') {
    $id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    if ($id <= 0) {
        $response['ok'] = false;
        $response['error'] = 'id parameter required';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $sql = "SELECT * FROM tracked_portfolios WHERE id=$id";
    $res = $conn->query($sql);
    if (!$res || $res->num_rows === 0) {
        $response['ok'] = false;
        $response['error'] = 'Portfolio not found';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $portfolio = $res->fetch_assoc();

    // Get picks
    $sql2 = "SELECT * FROM tracked_portfolio_picks WHERE portfolio_id=$id ORDER BY current_return_pct DESC";
    $res2 = $conn->query($sql2);
    $picks = array();
    if ($res2) {
        while ($row = $res2->fetch_assoc()) {
            $picks[] = $row;
        }
    }

    $portfolio['picks'] = $picks;
    $response['portfolio'] = $portfolio;
    echo json_encode($response);
    $conn->close();
    exit;
}

// ─── Save New Tracked Portfolio ───
if ($action === 'save') {
    // Accept JSON body or GET params
    $raw = file_get_contents('php://input');
    $body = json_decode($raw, true);

    if (!$body) {
        // Try GET params
        $body = array(
            'name' => isset($_GET['name']) ? $_GET['name'] : '',
            'category' => isset($_GET['category']) ? $_GET['category'] : 'swing',
            'picks' => array()
        );
    }

    $name = isset($body['name']) ? trim($body['name']) : '';
    $category = isset($body['category']) ? trim($body['category']) : 'swing';
    $picks = isset($body['picks']) ? $body['picks'] : array();

    if ($name === '') {
        $name = ucfirst($category) . ' Portfolio ' . date('M j');
    }

    if (count($picks) === 0) {
        $response['ok'] = false;
        $response['error'] = 'No picks provided. Send a JSON body with a picks array.';
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $now = date('Y-m-d H:i:s');
    $safe_name = $conn->real_escape_string($name);
    $safe_cat = $conn->real_escape_string($category);
    $capital = isset($body['initial_capital']) ? (float)$body['initial_capital'] : 10000;
    $total = count($picks);

    $sql = "INSERT INTO tracked_portfolios
            (name, strategy_type, category, initial_capital, status, total_picks, active_picks, created_at, updated_at)
            VALUES ('$safe_name', '$safe_cat', '$safe_cat', $capital, 'active', $total, $total, '$now', '$now')";

    if (!$conn->query($sql)) {
        $response['ok'] = false;
        $response['error'] = 'Failed to create portfolio: ' . $conn->error;
        echo json_encode($response);
        $conn->close();
        exit;
    }

    $portfolio_id = $conn->insert_id;

    // Insert picks
    $inserted = 0;
    foreach ($picks as $p) {
        $t_ticker = $conn->real_escape_string(isset($p['ticker']) ? $p['ticker'] : '');
        $t_company = $conn->real_escape_string(isset($p['company_name']) ? $p['company_name'] : '');
        $t_algo = $conn->real_escape_string(isset($p['algorithm']) ? $p['algorithm'] : '');
        $t_entry = (float)(isset($p['entry_price']) ? $p['entry_price'] : 0);
        $t_current = (float)(isset($p['current_price']) ? $p['current_price'] : $t_entry);
        $t_tp = (float)(isset($p['take_profit']) ? $p['take_profit'] : 0);
        $t_sl = (float)(isset($p['stop_loss']) ? $p['stop_loss'] : 0);
        $t_tp_pct = (float)(isset($p['tp_pct']) ? $p['tp_pct'] : 10);
        $t_sl_pct = (float)(isset($p['sl_pct']) ? $p['sl_pct'] : 5);
        $t_hold = (int)(isset($p['hold_days']) ? $p['hold_days'] : 7);
        $t_date = isset($p['entry_date']) ? $conn->real_escape_string($p['entry_date']) : date('Y-m-d');
        $t_ret = 0;
        if ($t_entry > 0) {
            $t_ret = round(($t_current - $t_entry) / $t_entry * 100, 4);
        }

        if ($t_ticker === '' || $t_entry <= 0) continue;

        $pick_sql = "INSERT INTO tracked_portfolio_picks
            (portfolio_id, ticker, company_name, algorithm, entry_price, current_price,
             take_profit, stop_loss, tp_pct, sl_pct, hold_days, status,
             current_return_pct, peak_price, trough_price, entry_date, days_held,
             created_at, updated_at)
            VALUES ($portfolio_id, '$t_ticker', '$t_company', '$t_algo', $t_entry, $t_current,
                    $t_tp, $t_sl, $t_tp_pct, $t_sl_pct, $t_hold, 'active',
                    $t_ret, $t_current, $t_current, '$t_date', 0,
                    '$now', '$now')";

        if ($conn->query($pick_sql)) {
            $inserted++;
        }
    }

    $response['portfolio_id'] = $portfolio_id;
    $response['picks_saved'] = $inserted;
    $response['name'] = $name;
    echo json_encode($response);
    $conn->close();
    exit;
}

// ─── Refresh a Single Portfolio ───
if ($action === 'refresh' || $action === 'refresh_all') {
    $portfolios_to_refresh = array();

    if ($action === 'refresh') {
        $id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
        if ($id <= 0) {
            $response['ok'] = false;
            $response['error'] = 'id parameter required';
            echo json_encode($response);
            $conn->close();
            exit;
        }
        $portfolios_to_refresh = array($id);
    } else {
        // Refresh all active portfolios
        $res = $conn->query("SELECT id FROM tracked_portfolios WHERE status='active'");
        if ($res) {
            while ($row = $res->fetch_assoc()) {
                $portfolios_to_refresh[] = (int)$row['id'];
            }
        }
    }

    $results = array();
    $now = date('Y-m-d H:i:s');
    $today = date('Y-m-d');

    foreach ($portfolios_to_refresh as $pid) {
        $port_result = array('portfolio_id' => $pid, 'picks_updated' => 0, 'tp_hits' => 0, 'sl_hits' => 0, 'expired' => 0);

        // Get all active picks for this portfolio
        $pick_sql = "SELECT * FROM tracked_portfolio_picks WHERE portfolio_id=$pid AND status='active'";
        $pick_res = $conn->query($pick_sql);
        if (!$pick_res) {
            $port_result['error'] = 'Failed to load picks';
            $results[] = $port_result;
            continue;
        }

        $total_return = 0;
        $pick_count = 0;
        $best_return = -999;
        $worst_return = 999;
        $best_ticker = '';
        $worst_ticker = '';
        $still_active = 0;

        while ($pick = $pick_res->fetch_assoc()) {
            $pick_id = (int)$pick['id'];
            $ticker = $pick['ticker'];
            $entry_price = (float)$pick['entry_price'];
            $tp_price = (float)$pick['take_profit'];
            $sl_price = (float)$pick['stop_loss'];
            $hold_max = (int)$pick['hold_days'];
            $entry_date = $pick['entry_date'];
            $peak = (float)$pick['peak_price'];
            $trough = (float)$pick['trough_price'];

            // Get latest price
            $safe_ticker = $conn->real_escape_string($ticker);
            $price_sql = "SELECT close_price, high_price, low_price, trade_date
                          FROM daily_prices WHERE ticker='$safe_ticker'
                          ORDER BY trade_date DESC LIMIT 1";
            $price_res = $conn->query($price_sql);

            if (!$price_res || $price_res->num_rows === 0) {
                $still_active++;
                continue;
            }

            $price_row = $price_res->fetch_assoc();
            $current_price = (float)$price_row['close_price'];
            $day_high = (float)$price_row['high_price'];
            $day_low = (float)$price_row['low_price'];
            $price_date = $price_row['trade_date'];

            // Update peak/trough
            if ($day_high > $peak || $peak <= 0) $peak = $day_high;
            if (($day_low < $trough || $trough <= 0) && $day_low > 0) $trough = $day_low;

            // Calculate return
            $ret_pct = 0;
            if ($entry_price > 0) {
                $ret_pct = round(($current_price - $entry_price) / $entry_price * 100, 4);
            }

            // Days held
            $days_held = (int)((strtotime($today) - strtotime($entry_date)) / 86400);
            if ($days_held < 0) $days_held = 0;

            // Check TP/SL/expiry
            $new_status = 'active';
            $exit_price = null;
            $exit_date = null;
            $exit_reason = null;

            if ($day_high >= $tp_price) {
                $new_status = 'tp_hit';
                $exit_price = $tp_price;
                $exit_date = $price_date;
                $exit_reason = 'take_profit';
                $ret_pct = round(($tp_price - $entry_price) / $entry_price * 100, 4);
                $port_result['tp_hits']++;
            } elseif ($day_low <= $sl_price) {
                $new_status = 'sl_hit';
                $exit_price = $sl_price;
                $exit_date = $price_date;
                $exit_reason = 'stop_loss';
                $ret_pct = round(($sl_price - $entry_price) / $entry_price * 100, 4);
                $port_result['sl_hits']++;
            } elseif ($days_held >= $hold_max) {
                $new_status = 'expired';
                $exit_price = $current_price;
                $exit_date = $price_date;
                $exit_reason = 'max_hold';
                $port_result['expired']++;
            } else {
                $still_active++;
            }

            // Update pick record
            $update_parts = array(
                "current_price=$current_price",
                "current_return_pct=$ret_pct",
                "peak_price=$peak",
                "trough_price=$trough",
                "days_held=$days_held",
                "last_price_date='$price_date'",
                "status='$new_status'",
                "updated_at='$now'"
            );

            if ($exit_price !== null) {
                $update_parts[] = "exit_price=$exit_price";
                $update_parts[] = "exit_date='$exit_date'";
                $update_parts[] = "exit_reason='$exit_reason'";
            }

            $update_sql = "UPDATE tracked_portfolio_picks SET " . implode(', ', $update_parts) . " WHERE id=$pick_id";
            $conn->query($update_sql);

            $total_return = $total_return + $ret_pct;
            $pick_count++;

            if ($ret_pct > $best_return) {
                $best_return = $ret_pct;
                $best_ticker = $ticker;
            }
            if ($ret_pct < $worst_return) {
                $worst_return = $ret_pct;
                $worst_ticker = $ticker;
            }

            $port_result['picks_updated']++;
        }

        // Also count already-closed picks for portfolio totals
        $closed_sql = "SELECT COUNT(*) as cnt, SUM(current_return_pct) as total_ret,
                        SUM(CASE WHEN status='tp_hit' THEN 1 ELSE 0 END) as tp_total,
                        SUM(CASE WHEN status='sl_hit' THEN 1 ELSE 0 END) as sl_total
                       FROM tracked_portfolio_picks WHERE portfolio_id=$pid";
        $closed_res = $conn->query($closed_sql);
        if ($closed_res && $crow = $closed_res->fetch_assoc()) {
            $all_count = (int)$crow['cnt'];
            $all_return = (float)$crow['total_ret'];
            $all_tp = (int)$crow['tp_total'];
            $all_sl = (int)$crow['sl_total'];

            $avg_return = ($all_count > 0) ? round($all_return / $all_count, 4) : 0;

            // Update portfolio summary
            $safe_best = $conn->real_escape_string($best_ticker);
            $safe_worst = $conn->real_escape_string($worst_ticker);
            $new_port_status = ($still_active > 0) ? 'active' : 'completed';
            $update_port = "UPDATE tracked_portfolios SET
                tp_hits=$all_tp,
                sl_hits=$all_sl,
                active_picks=$still_active,
                total_return_pct=$avg_return,
                best_pick='$safe_best',
                worst_pick='$safe_worst',
                last_refreshed='$now',
                status='$new_port_status',
                updated_at='$now'
                WHERE id=$pid";
            $conn->query($update_port);
        }

        $results[] = $port_result;
    }

    $response['refreshed'] = count($results);
    $response['results'] = $results;
    echo json_encode($response);
    $conn->close();
    exit;
}

// Unknown action
$response['ok'] = false;
$response['error'] = 'Unknown action. Use: list, get, save, refresh, refresh_all, setup';
echo json_encode($response);
$conn->close();
?>
