<?php
/**
 * Saved Portfolio API - CRUD operations for user-saved portfolios.
 * Portfolios are identified by IP + portfolio_key (stored in localStorage).
 * PHP 5.2 compatible.
 *
 * Actions:
 *   GET  ?action=list                                    — list portfolios for this IP/key
 *   GET  ?action=detail&id=1&key=abc                     — full portfolio detail
 *   GET  ?action=equity_curve&id=1                       — equity curve data for Chart.js
 *   POST ?action=create                                  — create portfolio from picks
 *   POST ?action=close_position&position_id=1&key=abc    — manually close a position
 *   POST ?action=delete&id=1&key=abc                     — delete a portfolio
 */
require_once dirname(__FILE__) . '/db_connect.php';

// Ensure portfolio tables exist (lightweight, uses IF NOT EXISTS)
$conn->query("CREATE TABLE IF NOT EXISTS saved_portfolios (id INT AUTO_INCREMENT PRIMARY KEY, portfolio_name VARCHAR(200) NOT NULL, portfolio_key VARCHAR(64) NOT NULL DEFAULT '', horizon VARCHAR(20) NOT NULL DEFAULT 'swing', initial_capital DECIMAL(12,2) NOT NULL DEFAULT 1000.00, current_equity DECIMAL(12,2) NOT NULL DEFAULT 0, take_profit_pct DECIMAL(5,2) NOT NULL DEFAULT 10.00, stop_loss_pct DECIMAL(5,2) NOT NULL DEFAULT 5.00, max_hold_days INT NOT NULL DEFAULT 30, status VARCHAR(20) NOT NULL DEFAULT 'active', ip_address VARCHAR(45) NOT NULL DEFAULT '', created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, KEY idx_status (status), KEY idx_ip (ip_address), KEY idx_key (portfolio_key)) ENGINE=MyISAM DEFAULT CHARSET=utf8");
$conn->query("CREATE TABLE IF NOT EXISTS portfolio_positions (id INT AUTO_INCREMENT PRIMARY KEY, portfolio_id INT NOT NULL, ticker VARCHAR(10) NOT NULL, company_name VARCHAR(200) NOT NULL DEFAULT '', algorithm_name VARCHAR(100) NOT NULL DEFAULT '', entry_date DATE NOT NULL, entry_price DECIMAL(12,4) NOT NULL DEFAULT 0, shares DECIMAL(12,4) NOT NULL DEFAULT 0, allocated_amount DECIMAL(12,2) NOT NULL DEFAULT 0, current_price DECIMAL(12,4) NOT NULL DEFAULT 0, unrealized_pnl DECIMAL(12,2) NOT NULL DEFAULT 0, exit_date DATE, exit_price DECIMAL(12,4) NOT NULL DEFAULT 0, realized_pnl DECIMAL(12,2) NOT NULL DEFAULT 0, exit_reason VARCHAR(50) NOT NULL DEFAULT '', status VARCHAR(20) NOT NULL DEFAULT 'open', KEY idx_portfolio (portfolio_id), KEY idx_status (status), KEY idx_ticker (ticker)) ENGINE=MyISAM DEFAULT CHARSET=utf8");
$conn->query("CREATE TABLE IF NOT EXISTS portfolio_daily_equity (id INT AUTO_INCREMENT PRIMARY KEY, portfolio_id INT NOT NULL, snapshot_date DATE NOT NULL, equity_value DECIMAL(12,2) NOT NULL DEFAULT 0, cash_balance DECIMAL(12,2) NOT NULL DEFAULT 0, open_positions INT NOT NULL DEFAULT 0, daily_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0, cumulative_return_pct DECIMAL(10,4) NOT NULL DEFAULT 0, max_drawdown_pct DECIMAL(10,4) NOT NULL DEFAULT 0, spy_close DECIMAL(10,2) NOT NULL DEFAULT 0, UNIQUE KEY idx_portfolio_date (portfolio_id, snapshot_date), KEY idx_date (snapshot_date)) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? trim($_GET['action']) : '';
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$safe_ip = $conn->real_escape_string($ip);
$now = date('Y-m-d H:i:s');
$today = date('Y-m-d');

if (!$action) {
    echo json_encode(array('ok' => false, 'error' => 'Missing action parameter. Use: list, detail, equity_curve, create, close_position, delete'));
    $conn->close();
    exit;
}

// ─── Helper: check portfolio ownership ───
function _sp_check_access($conn, $id, $ip, $key) {
    $safe_id = (int)$id;
    $safe_ip = $conn->real_escape_string($ip);
    $safe_key = $conn->real_escape_string($key);
    $res = $conn->query("SELECT id FROM saved_portfolios WHERE id=$safe_id AND (ip_address='$safe_ip' OR portfolio_key='$safe_key') LIMIT 1");
    return ($res && $res->num_rows > 0);
}

// ─── Helper: get latest price for ticker ───
function _sp_latest_price($conn, $ticker) {
    $safe = $conn->real_escape_string($ticker);
    $res = $conn->query("SELECT close_price, trade_date FROM daily_prices WHERE ticker='$safe' ORDER BY trade_date DESC LIMIT 1");
    if ($res && $row = $res->fetch_assoc()) return $row;
    return null;
}

// ─── ACTION: list ───
if ($action === 'list') {
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';
    $safe_key = $conn->real_escape_string($key);

    $where = "ip_address='$safe_ip'";
    if ($key) {
        $where = "(ip_address='$safe_ip' OR portfolio_key='$safe_key')";
    }

    $res = $conn->query("SELECT * FROM saved_portfolios WHERE $where ORDER BY created_at DESC LIMIT 50");
    $portfolios = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $pid = (int)$row['id'];
            // Count positions
            $pos_res = $conn->query("SELECT COUNT(*) as total, SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_count FROM portfolio_positions WHERE portfolio_id=$pid");
            $pos = ($pos_res && $prow = $pos_res->fetch_assoc()) ? $prow : array('total' => 0, 'open_count' => 0);

            $portfolios[] = array(
                'id'              => $pid,
                'name'            => $row['portfolio_name'],
                'portfolio_key'   => $row['portfolio_key'],
                'horizon'         => $row['horizon'],
                'initial_capital' => (float)$row['initial_capital'],
                'current_equity'  => (float)$row['current_equity'],
                'tp_pct'          => (float)$row['take_profit_pct'],
                'sl_pct'          => (float)$row['stop_loss_pct'],
                'max_hold_days'   => (int)$row['max_hold_days'],
                'status'          => $row['status'],
                'total_positions' => (int)$pos['total'],
                'open_positions'  => (int)$pos['open_count'],
                'return_pct'      => ((float)$row['initial_capital'] > 0) ? round(((float)$row['current_equity'] - (float)$row['initial_capital']) / (float)$row['initial_capital'] * 100, 2) : 0,
                'created_at'      => $row['created_at'],
                'updated_at'      => $row['updated_at']
            );
        }
    }

    echo json_encode(array('ok' => true, 'portfolios' => $portfolios, 'count' => count($portfolios)));
    $conn->close();
    exit;
}

// ─── ACTION: detail ───
if ($action === 'detail') {
    $id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';

    if ($id <= 0) {
        echo json_encode(array('ok' => false, 'error' => 'Missing id'));
        $conn->close();
        exit;
    }

    $safe_id = (int)$id;
    $res = $conn->query("SELECT * FROM saved_portfolios WHERE id=$safe_id LIMIT 1");
    if (!$res || $res->num_rows === 0) {
        echo json_encode(array('ok' => false, 'error' => 'Portfolio not found'));
        $conn->close();
        exit;
    }
    $portfolio = $res->fetch_assoc();

    // Open positions
    $open = array();
    $open_res = $conn->query("SELECT * FROM portfolio_positions WHERE portfolio_id=$safe_id AND status='open' ORDER BY entry_date ASC");
    if ($open_res) {
        while ($row = $open_res->fetch_assoc()) {
            $entry = (float)$row['entry_price'];
            $current = (float)$row['current_price'];
            $shares = (float)$row['shares'];
            $days_held = max(1, (int)((time() - strtotime($row['entry_date'])) / 86400));
            $unrealized = round(($current - $entry) * $shares, 2);
            $ret_pct = ($entry > 0) ? round(($current - $entry) / $entry * 100, 2) : 0;

            $tp_price = round($entry * (1 + (float)$portfolio['take_profit_pct'] / 100), 2);
            $sl_price = round($entry * (1 - (float)$portfolio['stop_loss_pct'] / 100), 2);

            $open[] = array(
                'id'             => (int)$row['id'],
                'ticker'         => $row['ticker'],
                'company_name'   => $row['company_name'],
                'algorithm'      => $row['algorithm_name'],
                'entry_date'     => $row['entry_date'],
                'entry_price'    => $entry,
                'current_price'  => $current,
                'shares'         => $shares,
                'allocated'      => (float)$row['allocated_amount'],
                'unrealized_pnl' => $unrealized,
                'return_pct'     => $ret_pct,
                'days_held'      => $days_held,
                'tp_target'      => $tp_price,
                'sl_target'      => $sl_price,
                'dist_to_tp'     => ($current > 0) ? round(($tp_price - $current) / $current * 100, 2) : 0,
                'dist_to_sl'     => ($current > 0) ? round(($current - $sl_price) / $current * 100, 2) : 0
            );
        }
    }

    // Closed positions
    $closed = array();
    $closed_res = $conn->query("SELECT * FROM portfolio_positions WHERE portfolio_id=$safe_id AND status='closed' ORDER BY exit_date DESC");
    if ($closed_res) {
        while ($row = $closed_res->fetch_assoc()) {
            $entry = (float)$row['entry_price'];
            $exit = (float)$row['exit_price'];
            $shares = (float)$row['shares'];
            $realized = round(($exit - $entry) * $shares, 2);
            $ret_pct = ($entry > 0) ? round(($exit - $entry) / $entry * 100, 2) : 0;
            $hold_days = max(1, (int)((strtotime($row['exit_date']) - strtotime($row['entry_date'])) / 86400));

            $closed[] = array(
                'id'            => (int)$row['id'],
                'ticker'        => $row['ticker'],
                'company_name'  => $row['company_name'],
                'algorithm'     => $row['algorithm_name'],
                'entry_date'    => $row['entry_date'],
                'exit_date'     => $row['exit_date'],
                'entry_price'   => $entry,
                'exit_price'    => $exit,
                'shares'        => $shares,
                'realized_pnl'  => $realized,
                'return_pct'    => $ret_pct,
                'exit_reason'   => $row['exit_reason'],
                'hold_days'     => $hold_days
            );
        }
    }

    // Compute metrics
    $init_cap = (float)$portfolio['initial_capital'];
    $cur_eq = (float)$portfolio['current_equity'];
    $total_return = ($init_cap > 0) ? round(($cur_eq - $init_cap) / $init_cap * 100, 2) : 0;

    $total_closed = count($closed);
    $wins = 0;
    $losses_count = 0;
    $sum_win = 0;
    $sum_loss = 0;
    $best = -999;
    $worst = 999;
    foreach ($closed as $c) {
        if ($c['return_pct'] >= 0) { $wins++; $sum_win += $c['return_pct']; }
        else { $losses_count++; $sum_loss += abs($c['return_pct']); }
        if ($c['return_pct'] > $best) $best = $c['return_pct'];
        if ($c['return_pct'] < $worst) $worst = $c['return_pct'];
    }
    $win_rate = ($total_closed > 0) ? round($wins / $total_closed * 100, 1) : 0;
    $avg_win = ($wins > 0) ? round($sum_win / $wins, 2) : 0;
    $avg_loss = ($losses_count > 0) ? round($sum_loss / $losses_count, 2) : 0;
    $profit_factor = ($sum_loss > 0) ? round($sum_win / $sum_loss, 2) : 0;

    // Max drawdown from equity curve
    $max_dd = 0;
    $eq_res = $conn->query("SELECT max_drawdown_pct FROM portfolio_daily_equity WHERE portfolio_id=$safe_id ORDER BY max_drawdown_pct DESC LIMIT 1");
    if ($eq_res && $erow = $eq_res->fetch_assoc()) {
        $max_dd = (float)$erow['max_drawdown_pct'];
    }

    $metrics = array(
        'total_return_pct'  => $total_return,
        'total_closed'      => $total_closed,
        'wins'              => $wins,
        'losses'            => $losses_count,
        'win_rate'          => $win_rate,
        'avg_win_pct'       => $avg_win,
        'avg_loss_pct'      => $avg_loss,
        'best_trade_pct'    => ($total_closed > 0) ? round($best, 2) : 0,
        'worst_trade_pct'   => ($total_closed > 0) ? round($worst, 2) : 0,
        'profit_factor'     => $profit_factor,
        'max_drawdown_pct'  => $max_dd
    );

    echo json_encode(array(
        'ok' => true,
        'portfolio' => array(
            'id'              => (int)$portfolio['id'],
            'name'            => $portfolio['portfolio_name'],
            'portfolio_key'   => $portfolio['portfolio_key'],
            'horizon'         => $portfolio['horizon'],
            'initial_capital' => $init_cap,
            'current_equity'  => $cur_eq,
            'tp_pct'          => (float)$portfolio['take_profit_pct'],
            'sl_pct'          => (float)$portfolio['stop_loss_pct'],
            'max_hold_days'   => (int)$portfolio['max_hold_days'],
            'status'          => $portfolio['status'],
            'created_at'      => $portfolio['created_at'],
            'updated_at'      => $portfolio['updated_at']
        ),
        'open_positions'   => $open,
        'closed_positions' => $closed,
        'metrics'          => $metrics
    ));
    $conn->close();
    exit;
}

// ─── ACTION: equity_curve ───
if ($action === 'equity_curve') {
    $id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    if ($id <= 0) {
        echo json_encode(array('ok' => false, 'error' => 'Missing id'));
        $conn->close();
        exit;
    }

    $safe_id = (int)$id;

    // Get portfolio info
    $p_res = $conn->query("SELECT initial_capital, created_at FROM saved_portfolios WHERE id=$safe_id LIMIT 1");
    if (!$p_res || $p_res->num_rows === 0) {
        echo json_encode(array('ok' => false, 'error' => 'Portfolio not found'));
        $conn->close();
        exit;
    }
    $pinfo = $p_res->fetch_assoc();
    $init_cap = (float)$pinfo['initial_capital'];

    // Get equity curve
    $eq_res = $conn->query("SELECT snapshot_date, equity_value, cash_balance, open_positions, daily_return_pct, cumulative_return_pct, max_drawdown_pct, spy_close FROM portfolio_daily_equity WHERE portfolio_id=$safe_id ORDER BY snapshot_date ASC");
    $curve = array();
    $spy_start = 0;
    if ($eq_res) {
        while ($row = $eq_res->fetch_assoc()) {
            if ($spy_start == 0 && (float)$row['spy_close'] > 0) {
                $spy_start = (float)$row['spy_close'];
            }
            // Normalize SPY to same starting capital
            $spy_normalized = ($spy_start > 0 && (float)$row['spy_close'] > 0)
                ? round($init_cap * (float)$row['spy_close'] / $spy_start, 2)
                : 0;

            $curve[] = array(
                'date'       => $row['snapshot_date'],
                'equity'     => (float)$row['equity_value'],
                'spy'        => $spy_normalized,
                'spy_raw'    => (float)$row['spy_close'],
                'drawdown'   => (float)$row['max_drawdown_pct'],
                'daily_ret'  => (float)$row['daily_return_pct'],
                'cum_ret'    => (float)$row['cumulative_return_pct']
            );
        }
    }

    // Compute overall metrics from curve
    $portfolio_return = 0;
    $spy_return = 0;
    $max_dd = 0;
    if (count($curve) > 0) {
        $last = $curve[count($curve) - 1];
        $portfolio_return = $last['cum_ret'];
        $spy_return = ($spy_start > 0) ? round(($last['spy_raw'] - $spy_start) / $spy_start * 100, 2) : 0;
        $max_dd = $last['drawdown'];
    }

    echo json_encode(array(
        'ok' => true,
        'portfolio_id' => $safe_id,
        'initial_capital' => $init_cap,
        'data_points' => count($curve),
        'curve' => $curve,
        'summary' => array(
            'portfolio_return_pct' => $portfolio_return,
            'spy_return_pct'       => $spy_return,
            'alpha'                => round($portfolio_return - $spy_return, 2),
            'max_drawdown_pct'     => $max_dd
        )
    ));
    $conn->close();
    exit;
}

// ─── ACTION: create (POST) ───
if ($action === 'create') {
    $name    = isset($_POST['name']) ? trim($_POST['name']) : '';
    $capital = isset($_POST['capital']) ? (float)$_POST['capital'] : 1000;
    $horizon = isset($_POST['horizon']) ? trim($_POST['horizon']) : 'swing';
    $tp_pct  = isset($_POST['tp_pct']) ? (float)$_POST['tp_pct'] : 10;
    $sl_pct  = isset($_POST['sl_pct']) ? (float)$_POST['sl_pct'] : 5;
    $max_hold = isset($_POST['max_hold_days']) ? (int)$_POST['max_hold_days'] : 30;
    $tickers_raw = isset($_POST['tickers']) ? trim($_POST['tickers']) : '';

    // Also accept GET params for easier testing
    if (!$name && isset($_GET['name'])) $name = trim($_GET['name']);
    if (!$tickers_raw && isset($_GET['tickers'])) $tickers_raw = trim($_GET['tickers']);
    if (isset($_GET['capital'])) $capital = (float)$_GET['capital'];
    if (isset($_GET['horizon'])) $horizon = trim($_GET['horizon']);
    if (isset($_GET['tp_pct'])) $tp_pct = (float)$_GET['tp_pct'];
    if (isset($_GET['sl_pct'])) $sl_pct = (float)$_GET['sl_pct'];
    if (isset($_GET['max_hold_days'])) $max_hold = (int)$_GET['max_hold_days'];

    if (!$name) $name = ucfirst($horizon) . ' Portfolio ' . date('M j');
    if (!$tickers_raw) {
        echo json_encode(array('ok' => false, 'error' => 'Missing tickers parameter (comma-separated)'));
        $conn->close();
        exit;
    }

    $tickers = array_map('trim', explode(',', $tickers_raw));
    $tickers = array_filter($tickers);
    $num_tickers = count($tickers);
    if ($num_tickers === 0) {
        echo json_encode(array('ok' => false, 'error' => 'No valid tickers provided'));
        $conn->close();
        exit;
    }

    // Generate portfolio key
    $pkey = md5($name . $now . $ip . mt_rand(1000, 9999));

    // Insert portfolio
    $safe_name = $conn->real_escape_string($name);
    $safe_pkey = $conn->real_escape_string($pkey);
    $safe_horizon = $conn->real_escape_string($horizon);

    $sql = "INSERT INTO saved_portfolios (portfolio_name, portfolio_key, horizon, initial_capital, current_equity, take_profit_pct, stop_loss_pct, max_hold_days, status, ip_address, created_at, updated_at)
            VALUES ('$safe_name', '$safe_pkey', '$safe_horizon', $capital, $capital, $tp_pct, $sl_pct, $max_hold, 'active', '$safe_ip', '$now', '$now')";

    if (!$conn->query($sql)) {
        echo json_encode(array('ok' => false, 'error' => 'Failed to create portfolio: ' . $conn->error));
        $conn->close();
        exit;
    }

    $portfolio_id = $conn->insert_id;
    $per_ticker = $capital / $num_tickers;
    $positions_created = 0;
    $position_errors = array();

    foreach ($tickers as $ticker) {
        $ticker = strtoupper(trim($ticker));
        if (!$ticker) continue;

        $latest = _sp_latest_price($conn, $ticker);
        if (!$latest || (float)$latest['close_price'] <= 0) {
            $position_errors[] = $ticker . ': no price data';
            continue;
        }

        $price = (float)$latest['close_price'];
        $shares = floor($per_ticker / $price);
        if ($shares <= 0) $shares = 1;
        $allocated = round($shares * $price, 2);

        // Get company name
        $safe_t = $conn->real_escape_string($ticker);
        $comp_res = $conn->query("SELECT company_name FROM stocks WHERE ticker='$safe_t' LIMIT 1");
        $company = ($comp_res && $crow = $comp_res->fetch_assoc()) ? $crow['company_name'] : '';
        $safe_comp = $conn->real_escape_string($company);

        // Get algorithm from most recent pick
        $algo_res = $conn->query("SELECT algorithm_name FROM stock_picks WHERE ticker='$safe_t' ORDER BY pick_date DESC LIMIT 1");
        $algo = ($algo_res && $arow = $algo_res->fetch_assoc()) ? $arow['algorithm_name'] : '';
        $safe_algo = $conn->real_escape_string($algo);

        $pos_sql = "INSERT INTO portfolio_positions (portfolio_id, ticker, company_name, algorithm_name, entry_date, entry_price, shares, allocated_amount, current_price, unrealized_pnl, status)
                    VALUES ($portfolio_id, '$safe_t', '$safe_comp', '$safe_algo', '$today', $price, $shares, $allocated, $price, 0, 'open')";

        if ($conn->query($pos_sql)) {
            $positions_created++;
        } else {
            $position_errors[] = $ticker . ': ' . $conn->error;
        }
    }

    // Create initial equity snapshot
    $spy_latest = _sp_latest_price($conn, 'SPY');
    $spy_close = ($spy_latest) ? (float)$spy_latest['close_price'] : 0;

    $conn->query("INSERT INTO portfolio_daily_equity (portfolio_id, snapshot_date, equity_value, cash_balance, open_positions, daily_return_pct, cumulative_return_pct, max_drawdown_pct, spy_close)
                  VALUES ($portfolio_id, '$today', $capital, " . round($capital - ($per_ticker * $positions_created), 2) . ", $positions_created, 0, 0, 0, $spy_close)");

    // Audit
    $conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('portfolio_create', 'Created portfolio $portfolio_id: $safe_name with $positions_created positions', '$safe_ip', '$now')");

    echo json_encode(array(
        'ok' => true,
        'portfolio_id' => $portfolio_id,
        'portfolio_key' => $pkey,
        'name' => $name,
        'positions_created' => $positions_created,
        'errors' => $position_errors
    ));
    $conn->close();
    exit;
}

// ─── ACTION: close_position (POST) ───
if ($action === 'close_position') {
    $pos_id = isset($_GET['position_id']) ? (int)$_GET['position_id'] : 0;
    if (!$pos_id && isset($_POST['position_id'])) $pos_id = (int)$_POST['position_id'];
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';

    if ($pos_id <= 0) {
        echo json_encode(array('ok' => false, 'error' => 'Missing position_id'));
        $conn->close();
        exit;
    }

    // Get position and portfolio
    $pos_res = $conn->query("SELECT * FROM portfolio_positions WHERE id=$pos_id AND status='open' LIMIT 1");
    if (!$pos_res || $pos_res->num_rows === 0) {
        echo json_encode(array('ok' => false, 'error' => 'Position not found or already closed'));
        $conn->close();
        exit;
    }
    $pos = $pos_res->fetch_assoc();
    $pid = (int)$pos['portfolio_id'];

    // Get latest price
    $latest = _sp_latest_price($conn, $pos['ticker']);
    $exit_price = ($latest) ? (float)$latest['close_price'] : (float)$pos['current_price'];
    $entry_price = (float)$pos['entry_price'];
    $shares = (float)$pos['shares'];
    $realized = round(($exit_price - $entry_price) * $shares, 2);
    $ret_pct = ($entry_price > 0) ? round(($exit_price - $entry_price) / $entry_price * 100, 2) : 0;

    $conn->query("UPDATE portfolio_positions SET status='closed', exit_date='$today', exit_price=$exit_price, realized_pnl=$realized, exit_reason='manual' WHERE id=$pos_id");

    echo json_encode(array(
        'ok' => true,
        'position_id' => $pos_id,
        'ticker' => $pos['ticker'],
        'exit_price' => $exit_price,
        'realized_pnl' => $realized,
        'return_pct' => $ret_pct
    ));
    $conn->close();
    exit;
}

// ─── ACTION: delete (POST) ───
if ($action === 'delete') {
    $id = isset($_GET['id']) ? (int)$_GET['id'] : 0;
    if (!$id && isset($_POST['id'])) $id = (int)$_POST['id'];
    $key = isset($_GET['key']) ? trim($_GET['key']) : '';

    if ($id <= 0) {
        echo json_encode(array('ok' => false, 'error' => 'Missing id'));
        $conn->close();
        exit;
    }

    $safe_id = (int)$id;
    $conn->query("DELETE FROM portfolio_positions WHERE portfolio_id=$safe_id");
    $conn->query("DELETE FROM portfolio_daily_equity WHERE portfolio_id=$safe_id");
    $conn->query("DELETE FROM saved_portfolios WHERE id=$safe_id");

    $conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('portfolio_delete', 'Deleted portfolio $safe_id', '$safe_ip', '$now')");

    echo json_encode(array('ok' => true, 'deleted_id' => $safe_id));
    $conn->close();
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
$conn->close();
?>
