<?php
/**
 * Track Portfolio API - Daily portfolio performance tracker.
 * Called by GitHub Actions to update prices, check SL/TP, record equity snapshots.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET track_portfolio.php?key=stocksrefresh2026
 *   GET track_portfolio.php?key=stocksrefresh2026&portfolio_id=1  (track single portfolio)
 */
require_once dirname(__FILE__) . '/db_connect.php';

$auth_key = isset($_GET['key']) ? trim($_GET['key']) : '';
$single_id = isset($_GET['portfolio_id']) ? (int)$_GET['portfolio_id'] : 0;
$now = date('Y-m-d H:i:s');
$today = date('Y-m-d');

if ($auth_key !== 'stocksrefresh2026') {
    header('HTTP/1.0 403 Forbidden');
    echo json_encode(array('ok' => false, 'error' => 'Invalid auth key'));
    $conn->close();
    exit;
}

// ─── Helper: get latest price ───
function _tp_latest_price($conn, $ticker) {
    $safe = $conn->real_escape_string($ticker);
    $res = $conn->query("SELECT close_price, high_price, low_price, trade_date FROM daily_prices WHERE ticker='$safe' ORDER BY trade_date DESC LIMIT 1");
    if ($res && $row = $res->fetch_assoc()) return $row;
    return null;
}

// ─── Get active portfolios ───
$where = "status='active'";
if ($single_id > 0) {
    $where .= " AND id=" . (int)$single_id;
}
$portfolios_res = $conn->query("SELECT * FROM saved_portfolios WHERE $where");
if (!$portfolios_res || $portfolios_res->num_rows === 0) {
    echo json_encode(array('ok' => true, 'portfolios_tracked' => 0, 'message' => 'No active portfolios to track'));
    $conn->close();
    exit;
}

$portfolios_tracked = 0;
$positions_checked = 0;
$positions_closed = 0;
$close_reasons = array('stop_loss' => 0, 'take_profit' => 0, 'max_hold' => 0);
$errors = array();

while ($portfolio = $portfolios_res->fetch_assoc()) {
    $pid = (int)$portfolio['id'];
    $tp_pct = (float)$portfolio['take_profit_pct'];
    $sl_pct = (float)$portfolio['stop_loss_pct'];
    $max_hold = (int)$portfolio['max_hold_days'];
    $init_cap = (float)$portfolio['initial_capital'];

    // Get open positions
    $pos_res = $conn->query("SELECT * FROM portfolio_positions WHERE portfolio_id=$pid AND status='open'");
    if (!$pos_res) {
        $errors[] = "Portfolio $pid: failed to query positions";
        continue;
    }

    $total_market_value = 0;
    $open_count = 0;

    while ($pos = $pos_res->fetch_assoc()) {
        $pos_id = (int)$pos['id'];
        $ticker = $pos['ticker'];
        $entry_price = (float)$pos['entry_price'];
        $shares = (float)$pos['shares'];
        $entry_date = $pos['entry_date'];
        $positions_checked++;

        // Get latest price
        $latest = _tp_latest_price($conn, $ticker);
        if (!$latest) {
            // Keep old price
            $total_market_value += (float)$pos['current_price'] * $shares;
            $open_count++;
            continue;
        }

        $current_price = (float)$latest['close_price'];
        $day_high = (float)$latest['high_price'];
        $day_low = (float)$latest['low_price'];

        // Calculate targets
        $tp_price = $entry_price * (1 + $tp_pct / 100);
        $sl_price = $entry_price * (1 - $sl_pct / 100);

        // Days held
        $days_held = max(1, (int)((time() - strtotime($entry_date)) / 86400));

        // Check SL/TP/max_hold
        $should_close = false;
        $exit_reason = '';
        $exit_price = $current_price;

        // Stop loss (check against day low for intraday trigger)
        if ($sl_pct < 999 && ($day_low <= $sl_price || $current_price <= $sl_price)) {
            $should_close = true;
            $exit_reason = 'stop_loss';
            $exit_price = min($current_price, $sl_price);
        }
        // Take profit (check against day high for intraday trigger)
        elseif ($tp_pct < 999 && ($day_high >= $tp_price || $current_price >= $tp_price)) {
            $should_close = true;
            $exit_reason = 'take_profit';
            $exit_price = max($current_price, $tp_price);
        }
        // Max hold days
        elseif ($max_hold < 999 && $days_held >= $max_hold) {
            $should_close = true;
            $exit_reason = 'max_hold';
            $exit_price = $current_price;
        }

        if ($should_close) {
            $realized = round(($exit_price - $entry_price) * $shares, 2);
            $conn->query("UPDATE portfolio_positions SET status='closed', exit_date='$today', exit_price=$exit_price, realized_pnl=$realized, exit_reason='$exit_reason', current_price=$current_price WHERE id=$pos_id");
            $positions_closed++;
            if (isset($close_reasons[$exit_reason])) {
                $close_reasons[$exit_reason]++;
            }
        } else {
            // Update current price and unrealized P&L
            $unrealized = round(($current_price - $entry_price) * $shares, 2);
            $conn->query("UPDATE portfolio_positions SET current_price=$current_price, unrealized_pnl=$unrealized WHERE id=$pos_id");
            $total_market_value += $current_price * $shares;
            $open_count++;
        }
    }

    // Calculate total equity
    // Cash = initial capital minus all allocated amounts for OPEN positions plus realized P&L from CLOSED
    $alloc_res = $conn->query("SELECT COALESCE(SUM(allocated_amount), 0) as total_allocated FROM portfolio_positions WHERE portfolio_id=$pid AND status='open'");
    $total_allocated = 0;
    if ($alloc_res && $arow = $alloc_res->fetch_assoc()) {
        $total_allocated = (float)$arow['total_allocated'];
    }

    $realized_res = $conn->query("SELECT COALESCE(SUM(realized_pnl), 0) as total_realized FROM portfolio_positions WHERE portfolio_id=$pid AND status='closed'");
    $total_realized = 0;
    if ($realized_res && $rrow = $realized_res->fetch_assoc()) {
        $total_realized = (float)$rrow['total_realized'];
    }

    $cash_balance = round($init_cap - $total_allocated + $total_realized, 2);
    $equity_value = round($cash_balance + $total_market_value, 2);

    // Get previous equity for daily return
    $prev_res = $conn->query("SELECT equity_value FROM portfolio_daily_equity WHERE portfolio_id=$pid ORDER BY snapshot_date DESC LIMIT 1");
    $prev_equity = $init_cap;
    if ($prev_res && $prow = $prev_res->fetch_assoc()) {
        $prev_equity = (float)$prow['equity_value'];
    }
    $daily_return = ($prev_equity > 0) ? round(($equity_value - $prev_equity) / $prev_equity * 100, 4) : 0;
    $cum_return = ($init_cap > 0) ? round(($equity_value - $init_cap) / $init_cap * 100, 4) : 0;

    // Calculate max drawdown
    $peak_res = $conn->query("SELECT MAX(equity_value) as peak FROM portfolio_daily_equity WHERE portfolio_id=$pid");
    $peak = $init_cap;
    if ($peak_res && $pkrow = $peak_res->fetch_assoc()) {
        $peak = max($init_cap, (float)$pkrow['peak']);
    }
    if ($equity_value > $peak) $peak = $equity_value;
    $max_dd = ($peak > 0) ? round(($peak - $equity_value) / $peak * 100, 4) : 0;

    // Get prev max_dd
    $prev_dd_res = $conn->query("SELECT max_drawdown_pct FROM portfolio_daily_equity WHERE portfolio_id=$pid ORDER BY snapshot_date DESC LIMIT 1");
    $prev_dd = 0;
    if ($prev_dd_res && $ddrow = $prev_dd_res->fetch_assoc()) {
        $prev_dd = (float)$ddrow['max_drawdown_pct'];
    }
    if ($max_dd < $prev_dd) $max_dd = $prev_dd; // Max drawdown only increases

    // SPY benchmark
    $spy_latest = _tp_latest_price($conn, 'SPY');
    $spy_close = ($spy_latest) ? (float)$spy_latest['close_price'] : 0;

    // Insert or update daily equity snapshot
    $conn->query("DELETE FROM portfolio_daily_equity WHERE portfolio_id=$pid AND snapshot_date='$today'");
    $conn->query("INSERT INTO portfolio_daily_equity (portfolio_id, snapshot_date, equity_value, cash_balance, open_positions, daily_return_pct, cumulative_return_pct, max_drawdown_pct, spy_close)
                  VALUES ($pid, '$today', $equity_value, $cash_balance, $open_count, $daily_return, $cum_return, $max_dd, $spy_close)");

    // Update portfolio current equity
    $conn->query("UPDATE saved_portfolios SET current_equity=$equity_value, updated_at='$now' WHERE id=$pid");

    // If no open positions remain, mark portfolio as completed
    if ($open_count === 0) {
        $conn->query("UPDATE saved_portfolios SET status='completed', updated_at='$now' WHERE id=$pid");
    }

    $portfolios_tracked++;
}

// Audit log
$ip = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : 'unknown';
$safe_ip = $conn->real_escape_string($ip);
$details = "Tracked $portfolios_tracked portfolios, $positions_checked positions, $positions_closed closed";
$safe_details = $conn->real_escape_string($details);
$conn->query("INSERT INTO audit_log (action_type, details, ip_address, created_at) VALUES ('track_portfolio', '$safe_details', '$safe_ip', '$now')");

echo json_encode(array(
    'ok' => true,
    'portfolios_tracked' => $portfolios_tracked,
    'positions_checked' => $positions_checked,
    'positions_closed' => $positions_closed,
    'close_reasons' => $close_reasons,
    'snapshots_saved' => $portfolios_tracked,
    'errors' => $errors
));
$conn->close();
?>
