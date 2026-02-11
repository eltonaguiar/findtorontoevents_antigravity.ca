<?php
/**
 * GOLDMINE_CURSOR — Harvest Predictions from All Source Systems
 * Pulls new predictions from stocks, crypto, forex, sports, mutual funds
 * into the unified goldmine_cursor_predictions ledger.
 * PHP 5.2 compatible.
 *
 * Sources harvested:
 *   stocks      — stock_picks + lm_signals(STOCK) + lm_trades(STOCK)
 *   crypto      — cp_signals + lm_signals(CRYPTO) + lm_trades(CRYPTO)
 *   forex       — fx_signals + lm_signals(FOREX) + lm_trades(FOREX)
 *   mutualfunds — mf_selections + mf2_fund_picks
 *   sports      — lm_sports_daily_picks
 *
 * Usage: GET /goldmine_cursor/api/harvest.php?key=goldmine2026[&source=stocks]
 *
 * This is INSERT-only for new predictions. Existing predictions
 * are only updated to resolve (set exit_price, pnl_pct, status).
 */
require_once dirname(__FILE__) . '/db_connect.php';

$key = isset($_GET['key']) ? $_GET['key'] : '';
if ($key !== 'goldmine2026') {
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    $conn->close();
    exit;
}

$source_filter = isset($_GET['source']) ? trim($_GET['source']) : 'all';
$debug = isset($_GET['debug']) ? true : false;
$results = array();
$total_new = 0;
$total_resolved = 0;
$debug_info = array();

// ─────────────────────────────────────────
//  Helper: Check if a table exists
// ─────────────────────────────────────────
function gc_table_exists($conn, $table) {
    $safe = $conn->real_escape_string($table);
    $chk = $conn->query("SHOW TABLES LIKE '$safe'");
    return ($chk && $chk->num_rows > 0);
}

// Debug: check what tables exist
if ($debug) {
    $r = $conn->query("SHOW TABLES");
    $tables = array();
    if ($r) { while ($row = $r->fetch_row()) { $tables[] = $row[0]; } }
    $debug_info['all_tables'] = $tables;

    $check_tables = array('stock_picks', 'cp_signals', 'fx_signals', 'mf_selections', 'mf2_fund_picks', 'lm_signals', 'lm_trades', 'lm_price_cache', 'lm_sports_daily_picks', 'daily_prices');
    foreach ($check_tables as $t) {
        if (gc_table_exists($conn, $t)) {
            $r2 = $conn->query("SELECT COUNT(*) as cnt FROM `$t`");
            if ($r2 && $row = $r2->fetch_assoc()) { $debug_info[$t . '_count'] = $row['cnt']; }
        } else {
            $debug_info[$t . '_count'] = 'TABLE NOT FOUND';
        }
    }
}

// ─────────────────────────────────────────
//  Helper: Generate unique prediction ID
// ─────────────────────────────────────────
function gc_pred_id($source, $algo, $ticker, $date) {
    return md5($source . '|' . $algo . '|' . $ticker . '|' . $date);
}

// ─────────────────────────────────────────
//  Helper: Insert prediction (skip if exists)
// ─────────────────────────────────────────
function gc_insert_prediction($conn, $data) {
    $pid = $conn->real_escape_string($data['prediction_id']);

    // Check if already exists
    $chk = $conn->query("SELECT id FROM goldmine_cursor_predictions WHERE prediction_id = '$pid' LIMIT 1");
    if ($chk && $chk->num_rows > 0) {
        return false; // already ingested
    }

    $fields = array(
        'prediction_id', 'asset_class', 'ticker', 'algorithm', 'direction',
        'entry_price', 'target_price', 'stop_loss', 'confidence_score',
        'source_system', 'logged_at', 'market_regime', 'status'
    );

    $vals = array();
    foreach ($fields as $f) {
        $v = isset($data[$f]) ? $data[$f] : '';
        $vals[] = "'" . $conn->real_escape_string($v) . "'";
    }

    $sql = "INSERT INTO goldmine_cursor_predictions (" . implode(',', $fields) . ") VALUES (" . implode(',', $vals) . ")";
    return $conn->query($sql);
}

// ─────────────────────────────────────────
//  Helper: Resolve predictions using lm_trades
// ─────────────────────────────────────────
function gc_resolve_from_lm_trades($conn, $asset_class, $lm_asset_class) {
    $resolve_count = 0;
    if (!gc_table_exists($conn, 'lm_trades')) { return 0; }

    $esc_ac = $conn->real_escape_string($asset_class);
    $esc_lm = $conn->real_escape_string($lm_asset_class);

    // Match open goldmine predictions to closed lm_trades by symbol + algorithm
    $r = $conn->query("SELECT p.id, p.entry_price, t.exit_price, t.realized_pct, t.exit_reason, t.exit_time, t.hold_hours
        FROM goldmine_cursor_predictions p
        JOIN lm_trades t ON t.symbol = p.ticker AND t.algorithm_name = p.algorithm
            AND t.asset_class = '$esc_lm'
            AND t.status = 'closed'
            AND t.exit_time >= p.logged_at
        WHERE p.status = 'open' AND p.asset_class = '$esc_ac'
        AND p.source_system = 'live-monitor'
        ORDER BY p.id, t.exit_time ASC");

    if ($r) {
        $resolved_ids = array();
        while ($row = $r->fetch_assoc()) {
            $id = intval($row['id']);
            if (isset($resolved_ids[$id])) { continue; }

            $pnl = floatval($row['realized_pct']);
            $status = ($pnl >= 0) ? 'won' : 'lost';
            $exit_price = floatval($row['exit_price']);
            $hold_days = round(floatval($row['hold_hours']) / 24, 1);
            $exit_time = $conn->real_escape_string($row['exit_time']);

            $conn->query("UPDATE goldmine_cursor_predictions SET
                status = '$status',
                exit_price = $exit_price,
                exit_date = '$exit_time',
                pnl_pct = $pnl,
                hold_days = $hold_days,
                resolved_at = NOW()
                WHERE id = $id AND status = 'open'");

            $resolved_ids[$id] = true;
            $resolve_count++;
        }
    }

    return $resolve_count;
}

// ─────────────────────────────────────────
//  Helper: Resolve predictions using lm_price_cache (current price vs TP/SL)
// ─────────────────────────────────────────
function gc_resolve_from_price_cache($conn, $asset_class) {
    $resolve_count = 0;
    if (!gc_table_exists($conn, 'lm_price_cache')) { return 0; }

    $esc_ac = $conn->real_escape_string($asset_class);

    $r = $conn->query("SELECT p.id, p.entry_price, p.target_price, p.stop_loss, p.logged_at,
        pc.price, pc.high_24h, pc.low_24h
        FROM goldmine_cursor_predictions p
        JOIN lm_price_cache pc ON pc.symbol = p.ticker
        WHERE p.status = 'open' AND p.asset_class = '$esc_ac'
        AND p.target_price > 0 AND p.stop_loss > 0");

    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $id = intval($row['id']);
            $entry = floatval($row['entry_price']);
            $tp = floatval($row['target_price']);
            $sl = floatval($row['stop_loss']);
            $high = floatval($row['high_24h']);
            $low = floatval($row['low_24h']);
            $current = floatval($row['price']);

            $hit_tp = ($high >= $tp || $current >= $tp);
            $hit_sl = ($low <= $sl || $current <= $sl);

            if ($hit_tp || $hit_sl) {
                $exit_price = $hit_tp ? $tp : $sl;
                $pnl = round(($exit_price - $entry) / $entry * 100, 4);
                $status = ($pnl >= 0) ? 'won' : 'lost';
                $hold = round((time() - strtotime($row['logged_at'])) / 86400, 1);

                $conn->query("UPDATE goldmine_cursor_predictions SET
                    status = '$status',
                    exit_price = $exit_price,
                    exit_date = NOW(),
                    pnl_pct = $pnl,
                    hold_days = $hold,
                    resolved_at = NOW()
                    WHERE id = $id AND status = 'open'");

                $resolve_count++;
            }
        }
    }

    return $resolve_count;
}


// ═══════════════════════════════════════════
//  HARVEST: Stock picks (stock_picks + lm_signals STOCK)
// ═══════════════════════════════════════════
if ($source_filter === 'all' || $source_filter === 'stocks') {
    $new_count = 0;
    $resolve_count = 0;

    // ── Source 1: stock_picks table (findstocks algorithms) ──
    if (gc_table_exists($conn, 'stock_picks')) {
        $r = $conn->query("SELECT *
            FROM stock_picks
            WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            AND entry_price > 0
            ORDER BY pick_date DESC
            LIMIT 500");

        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $pid = gc_pred_id('findstocks', $row['algorithm_name'], $row['ticker'], $row['pick_date']);
                $tp_pct = isset($row['target_tp_pct']) ? floatval($row['target_tp_pct']) : 5;
                $sl_pct = isset($row['target_sl_pct']) ? floatval($row['target_sl_pct']) : 3;
                $entry = floatval($row['entry_price']);

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'stocks',
                    'ticker' => $row['ticker'],
                    'algorithm' => $row['algorithm_name'],
                    'direction' => 'long',
                    'entry_price' => $entry,
                    'target_price' => round($entry * (1 + $tp_pct / 100), 6),
                    'stop_loss' => round($entry * (1 - $sl_pct / 100), 6),
                    'confidence_score' => isset($row['score']) ? intval($row['score']) : 50,
                    'source_system' => 'findstocks',
                    'logged_at' => $row['pick_date'] . ' 16:00:00',
                    'market_regime' => 'unknown',
                    'status' => 'open'
                );

                if (gc_insert_prediction($conn, $data)) {
                    $new_count++;
                }
            }
        }
    }

    // ── Source 2: lm_signals WHERE asset_class = 'STOCK' (live-monitor individual algos) ──
    if (gc_table_exists($conn, 'lm_signals')) {
        $r = $conn->query("SELECT * FROM lm_signals
            WHERE asset_class = 'STOCK'
            AND signal_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            AND entry_price > 0
            ORDER BY signal_time DESC LIMIT 500");

        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $pid = gc_pred_id('live-monitor', $row['algorithm_name'], $row['symbol'], substr($row['signal_time'], 0, 10));
                $entry = floatval($row['entry_price']);
                $tp_pct = floatval($row['target_tp_pct']);
                $sl_pct = floatval($row['target_sl_pct']);
                $dir = (strtoupper($row['signal_type']) === 'SELL') ? 'short' : 'long';

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'stocks',
                    'ticker' => $row['symbol'],
                    'algorithm' => $row['algorithm_name'],
                    'direction' => $dir,
                    'entry_price' => $entry,
                    'target_price' => ($dir === 'short') ? round($entry * (1 - $tp_pct / 100), 6) : round($entry * (1 + $tp_pct / 100), 6),
                    'stop_loss' => ($dir === 'short') ? round($entry * (1 + $sl_pct / 100), 6) : round($entry * (1 - $sl_pct / 100), 6),
                    'confidence_score' => intval($row['signal_strength']),
                    'source_system' => 'live-monitor',
                    'logged_at' => $row['signal_time'],
                    'market_regime' => 'unknown',
                    'status' => ($row['status'] === 'expired') ? 'expired' : 'open'
                );

                if (gc_insert_prediction($conn, $data)) {
                    $new_count++;
                }
            }
        }
    }

    // ── Resolve open stock predictions using daily_prices ──
    if (gc_table_exists($conn, 'daily_prices')) {
        $r = $conn->query("SELECT p.id, p.ticker, p.entry_price, p.target_price, p.stop_loss, p.logged_at,
            dp.close_price, dp.high_price, dp.low_price, dp.trade_date
            FROM goldmine_cursor_predictions p
            JOIN daily_prices dp ON dp.ticker = p.ticker
                AND dp.trade_date > DATE(p.logged_at)
                AND dp.trade_date <= DATE_ADD(DATE(p.logged_at), INTERVAL 30 DAY)
            WHERE p.status = 'open' AND p.asset_class = 'stocks'
            AND p.source_system = 'findstocks'
            ORDER BY p.id, dp.trade_date ASC");

        if ($r) {
            $resolved_ids = array();
            while ($row = $r->fetch_assoc()) {
                $id = intval($row['id']);
                if (isset($resolved_ids[$id])) { continue; }

                $high = floatval($row['high_price']);
                $low = floatval($row['low_price']);
                $tp = floatval($row['target_price']);
                $sl = floatval($row['stop_loss']);
                $entry = floatval($row['entry_price']);

                $hit_tp = ($high >= $tp);
                $hit_sl = ($low <= $sl);

                if ($hit_tp || $hit_sl) {
                    $exit_price = $hit_tp ? $tp : $sl;
                    $pnl = round(($exit_price - $entry) / $entry * 100, 4);
                    $status = ($pnl >= 0) ? 'won' : 'lost';
                    $hold = round((strtotime($row['trade_date']) - strtotime($row['logged_at'])) / 86400);

                    $conn->query("UPDATE goldmine_cursor_predictions SET
                        status = '$status',
                        exit_price = $exit_price,
                        exit_date = '" . $conn->real_escape_string($row['trade_date']) . " 16:00:00',
                        pnl_pct = $pnl,
                        hold_days = $hold,
                        resolved_at = NOW()
                        WHERE id = $id AND status = 'open'");

                    $resolved_ids[$id] = true;
                    $resolve_count++;
                }
            }
        }
    }

    // ── Resolve live-monitor stock signals from lm_trades ──
    $resolve_count += gc_resolve_from_lm_trades($conn, 'stocks', 'STOCK');

    // Expire picks older than 30 days still open
    $conn->query("UPDATE goldmine_cursor_predictions SET
        status = 'expired',
        resolved_at = NOW()
        WHERE status = 'open' AND asset_class = 'stocks'
        AND logged_at < DATE_SUB(NOW(), INTERVAL 30 DAY)");

    $results['stocks'] = array('new' => $new_count, 'resolved' => $resolve_count);
    $total_new = $total_new + $new_count;
    $total_resolved = $total_resolved + $resolve_count;
}

// ═══════════════════════════════════════════
//  HARVEST: Sports betting picks
// ═══════════════════════════════════════════
if ($source_filter === 'all' || $source_filter === 'sports') {
    $new_count = 0;
    $resolve_count = 0;

    // Pull from lm_sports_daily_picks
    if (gc_table_exists($conn, 'lm_sports_daily_picks')) {
        $r = $conn->query("SELECT * FROM lm_sports_daily_picks
            WHERE pick_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            ORDER BY pick_date DESC LIMIT 500");

        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $matchup = isset($row['home_team']) ? $row['away_team'] . ' @ ' . $row['home_team'] : $row['matchup'];
                $pid = gc_pred_id('live-monitor', isset($row['algorithm']) ? $row['algorithm'] : 'value_bet', $matchup, $row['pick_date']);

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'sports',
                    'ticker' => $matchup,
                    'algorithm' => isset($row['algorithm']) ? $row['algorithm'] : 'value_bet',
                    'direction' => isset($row['pick']) ? $row['pick'] : 'unknown',
                    'entry_price' => isset($row['best_odds']) ? floatval($row['best_odds']) : 0,
                    'target_price' => 0,
                    'stop_loss' => 0,
                    'confidence_score' => isset($row['confidence']) ? intval($row['confidence']) : 50,
                    'source_system' => 'live-monitor',
                    'logged_at' => isset($row['generated_at']) ? $row['generated_at'] : $row['pick_date'] . ' 12:00:00',
                    'market_regime' => 'unknown',
                    'status' => 'open'
                );

                // If already settled in source
                if (isset($row['result']) && $row['result'] !== '' && $row['result'] !== 'pending') {
                    $data['status'] = ($row['result'] === 'won') ? 'won' : 'lost';
                }

                if (gc_insert_prediction($conn, $data)) {
                    $new_count++;
                }
            }
        }

        // Sync settled status from source
        $r = $conn->query("SELECT p.id, dp.result, dp.pnl
            FROM goldmine_cursor_predictions p
            JOIN lm_sports_daily_picks dp ON dp.pick_date = DATE(p.logged_at)
            WHERE p.status = 'open' AND p.asset_class = 'sports'
            AND dp.result IN ('won','lost','push')");

        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $st = ($row['result'] === 'won') ? 'won' : 'lost';
                $pnl = isset($row['pnl']) ? floatval($row['pnl']) : 0;
                $id = intval($row['id']);
                $conn->query("UPDATE goldmine_cursor_predictions SET
                    status = '$st', pnl_pct = $pnl, resolved_at = NOW()
                    WHERE id = $id AND status = 'open'");
                $resolve_count++;
            }
        }
    }

    $results['sports'] = array('new' => $new_count, 'resolved' => $resolve_count);
    $total_new = $total_new + $new_count;
    $total_resolved = $total_resolved + $resolve_count;
}

// ═══════════════════════════════════════════
//  HARVEST: Crypto signals (cp_signals + lm_signals CRYPTO)
// ═══════════════════════════════════════════
if ($source_filter === 'all' || $source_filter === 'crypto') {
    $new_count = 0;
    $resolve_count = 0;

    // ── Source 1: cp_signals (findcryptopairs signals) ──
    if (gc_table_exists($conn, 'cp_signals')) {
        $r = $conn->query("SELECT * FROM cp_signals
            WHERE signal_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            AND entry_price > 0
            ORDER BY signal_date DESC LIMIT 500");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $pid = gc_pred_id('findcryptopairs', $row['strategy_name'], $row['pair'], $row['signal_date']);
                $entry = floatval($row['entry_price']);
                $tp = isset($row['take_profit_price']) ? floatval($row['take_profit_price']) : round($entry * 1.05, 8);
                $sl = isset($row['stop_loss_price']) ? floatval($row['stop_loss_price']) : round($entry * 0.97, 8);

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'crypto',
                    'ticker' => $row['pair'],
                    'algorithm' => $row['strategy_name'],
                    'direction' => isset($row['direction']) ? $row['direction'] : 'long',
                    'entry_price' => $entry,
                    'target_price' => $tp,
                    'stop_loss' => $sl,
                    'confidence_score' => isset($row['score']) ? intval($row['score']) : 50,
                    'source_system' => 'findcryptopairs',
                    'logged_at' => $row['signal_date'] . ' 00:00:00',
                    'market_regime' => 'unknown',
                    'status' => 'open'
                );
                if (gc_insert_prediction($conn, $data)) { $new_count++; }
            }
        }
    }

    // ── Source 2: lm_signals WHERE asset_class = 'CRYPTO' (live-monitor algos) ──
    if (gc_table_exists($conn, 'lm_signals')) {
        $r = $conn->query("SELECT * FROM lm_signals
            WHERE asset_class = 'CRYPTO'
            AND signal_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            AND entry_price > 0
            ORDER BY signal_time DESC LIMIT 500");

        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $pid = gc_pred_id('live-monitor-crypto', $row['algorithm_name'], $row['symbol'], substr($row['signal_time'], 0, 10));
                $entry = floatval($row['entry_price']);
                $tp_pct = floatval($row['target_tp_pct']);
                $sl_pct = floatval($row['target_sl_pct']);
                $dir = (strtoupper($row['signal_type']) === 'SELL') ? 'short' : 'long';

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'crypto',
                    'ticker' => $row['symbol'],
                    'algorithm' => $row['algorithm_name'],
                    'direction' => $dir,
                    'entry_price' => $entry,
                    'target_price' => ($dir === 'short') ? round($entry * (1 - $tp_pct / 100), 8) : round($entry * (1 + $tp_pct / 100), 8),
                    'stop_loss' => ($dir === 'short') ? round($entry * (1 + $sl_pct / 100), 8) : round($entry * (1 - $sl_pct / 100), 8),
                    'confidence_score' => intval($row['signal_strength']),
                    'source_system' => 'live-monitor',
                    'logged_at' => $row['signal_time'],
                    'market_regime' => 'unknown',
                    'status' => ($row['status'] === 'expired') ? 'expired' : 'open'
                );

                if (gc_insert_prediction($conn, $data)) { $new_count++; }
            }
        }
    }

    // ── Resolve crypto from lm_trades ──
    $resolve_count += gc_resolve_from_lm_trades($conn, 'crypto', 'CRYPTO');

    // ── Resolve crypto from price cache (TP/SL check) ──
    $resolve_count += gc_resolve_from_price_cache($conn, 'crypto');

    // Expire crypto picks older than 14 days still open
    $conn->query("UPDATE goldmine_cursor_predictions SET
        status = 'expired', resolved_at = NOW()
        WHERE status = 'open' AND asset_class = 'crypto'
        AND logged_at < DATE_SUB(NOW(), INTERVAL 14 DAY)");

    $results['crypto'] = array('new' => $new_count, 'resolved' => $resolve_count);
    $total_new = $total_new + $new_count;
    $total_resolved = $total_resolved + $resolve_count;
}

// ═══════════════════════════════════════════
//  HARVEST: Forex signals (fx_signals + lm_signals FOREX)
// ═══════════════════════════════════════════
if ($source_filter === 'all' || $source_filter === 'forex') {
    $new_count = 0;
    $resolve_count = 0;

    // ── Source 1: fx_signals (findforex2 signals) ──
    if (gc_table_exists($conn, 'fx_signals')) {
        $r = $conn->query("SELECT * FROM fx_signals
            WHERE signal_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            AND entry_price > 0
            ORDER BY signal_date DESC LIMIT 500");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $pid = gc_pred_id('findforex2', $row['strategy_name'], $row['pair'], $row['signal_date']);
                $entry = floatval($row['entry_price']);
                $tp = isset($row['take_profit_price']) ? floatval($row['take_profit_price']) : round($entry * 1.02, 6);
                $sl = isset($row['stop_loss_price']) ? floatval($row['stop_loss_price']) : round($entry * 0.99, 6);

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'forex',
                    'ticker' => $row['pair'],
                    'algorithm' => $row['strategy_name'],
                    'direction' => isset($row['direction']) ? $row['direction'] : 'long',
                    'entry_price' => $entry,
                    'target_price' => $tp,
                    'stop_loss' => $sl,
                    'confidence_score' => isset($row['score']) ? intval($row['score']) : 50,
                    'source_system' => 'findforex2',
                    'logged_at' => $row['signal_date'] . ' 00:00:00',
                    'market_regime' => 'unknown',
                    'status' => 'open'
                );
                if (gc_insert_prediction($conn, $data)) { $new_count++; }
            }
        }
    }

    // ── Source 2: lm_signals WHERE asset_class = 'FOREX' (live-monitor algos) ──
    if (gc_table_exists($conn, 'lm_signals')) {
        $r = $conn->query("SELECT * FROM lm_signals
            WHERE asset_class = 'FOREX'
            AND signal_time >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            AND entry_price > 0
            ORDER BY signal_time DESC LIMIT 500");

        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $pid = gc_pred_id('live-monitor-forex', $row['algorithm_name'], $row['symbol'], substr($row['signal_time'], 0, 10));
                $entry = floatval($row['entry_price']);
                $tp_pct = floatval($row['target_tp_pct']);
                $sl_pct = floatval($row['target_sl_pct']);
                $dir = (strtoupper($row['signal_type']) === 'SELL') ? 'short' : 'long';

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'forex',
                    'ticker' => $row['symbol'],
                    'algorithm' => $row['algorithm_name'],
                    'direction' => $dir,
                    'entry_price' => $entry,
                    'target_price' => ($dir === 'short') ? round($entry * (1 - $tp_pct / 100), 6) : round($entry * (1 + $tp_pct / 100), 6),
                    'stop_loss' => ($dir === 'short') ? round($entry * (1 + $sl_pct / 100), 6) : round($entry * (1 - $sl_pct / 100), 6),
                    'confidence_score' => intval($row['signal_strength']),
                    'source_system' => 'live-monitor',
                    'logged_at' => $row['signal_time'],
                    'market_regime' => 'unknown',
                    'status' => ($row['status'] === 'expired') ? 'expired' : 'open'
                );

                if (gc_insert_prediction($conn, $data)) { $new_count++; }
            }
        }
    }

    // ── Resolve forex from lm_trades ──
    $resolve_count += gc_resolve_from_lm_trades($conn, 'forex', 'FOREX');

    // ── Resolve forex from price cache ──
    $resolve_count += gc_resolve_from_price_cache($conn, 'forex');

    // Expire forex picks older than 14 days still open
    $conn->query("UPDATE goldmine_cursor_predictions SET
        status = 'expired', resolved_at = NOW()
        WHERE status = 'open' AND asset_class = 'forex'
        AND logged_at < DATE_SUB(NOW(), INTERVAL 14 DAY)");

    $results['forex'] = array('new' => $new_count, 'resolved' => $resolve_count);
    $total_new = $total_new + $new_count;
    $total_resolved = $total_resolved + $resolve_count;
}

// ═══════════════════════════════════════════
//  HARVEST: Mutual fund picks (mf_selections + mf2_fund_picks)
// ═══════════════════════════════════════════
if ($source_filter === 'all' || $source_filter === 'mutualfunds') {
    $new_count = 0;
    $resolve_count = 0;

    // ── Source 1: mf_selections (findmutualfunds v1) ──
    if (gc_table_exists($conn, 'mf_selections')) {
        $r = $conn->query("SELECT * FROM mf_selections
            WHERE select_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            AND nav_at_select > 0
            ORDER BY select_date DESC LIMIT 500");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $pid = gc_pred_id('findmutualfunds', $row['strategy_name'], $row['ticker'], $row['select_date']);
                $entry = floatval($row['nav_at_select']);
                // Mutual funds: conservative TP 3%, SL 2%
                $tp = round($entry * 1.03, 4);
                $sl = round($entry * 0.98, 4);

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'mutualfunds',
                    'ticker' => $row['ticker'],
                    'algorithm' => $row['strategy_name'],
                    'direction' => 'long',
                    'entry_price' => $entry,
                    'target_price' => $tp,
                    'stop_loss' => $sl,
                    'confidence_score' => isset($row['morningstar_rating']) ? intval($row['morningstar_rating']) * 20 : 50,
                    'source_system' => 'findmutualfunds',
                    'logged_at' => $row['select_date'] . ' 16:00:00',
                    'market_regime' => 'unknown',
                    'status' => 'open'
                );
                if (gc_insert_prediction($conn, $data)) { $new_count++; }
            }
        }
    }

    // ── Source 2: mf2_fund_picks (findmutualfunds2 v2) ──
    if (gc_table_exists($conn, 'mf2_fund_picks')) {
        $r = $conn->query("SELECT * FROM mf2_fund_picks
            WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            AND entry_nav > 0
            ORDER BY pick_date DESC LIMIT 500");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $pid = gc_pred_id('findmutualfunds2', $row['algorithm_name'], $row['symbol'], $row['pick_date']);
                $entry = floatval($row['entry_nav']);
                $tp = round($entry * 1.03, 4);
                $sl = round($entry * 0.98, 4);

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'mutualfunds',
                    'ticker' => $row['symbol'],
                    'algorithm' => $row['algorithm_name'],
                    'direction' => 'long',
                    'entry_price' => $entry,
                    'target_price' => $tp,
                    'stop_loss' => $sl,
                    'confidence_score' => isset($row['score']) ? intval($row['score']) : 50,
                    'source_system' => 'findmutualfunds2',
                    'logged_at' => $row['pick_date'] . ' 16:00:00',
                    'market_regime' => 'unknown',
                    'status' => 'open'
                );
                if (gc_insert_prediction($conn, $data)) { $new_count++; }
            }
        }
    }

    // ── Resolve mutual fund picks using mf_nav_history or mf2_nav_history ──
    // Try mf2_nav_history first (v2 has better data)
    if (gc_table_exists($conn, 'mf2_nav_history')) {
        $r = $conn->query("SELECT p.id, p.ticker, p.entry_price, p.target_price, p.stop_loss, p.logged_at,
            n.nav, n.nav_date
            FROM goldmine_cursor_predictions p
            JOIN mf2_nav_history n ON n.symbol = p.ticker
                AND n.nav_date > DATE(p.logged_at)
                AND n.nav_date <= DATE_ADD(DATE(p.logged_at), INTERVAL 90 DAY)
            WHERE p.status = 'open' AND p.asset_class = 'mutualfunds'
            ORDER BY p.id, n.nav_date ASC");

        if ($r) {
            $resolved_ids = array();
            while ($row = $r->fetch_assoc()) {
                $id = intval($row['id']);
                if (isset($resolved_ids[$id])) { continue; }

                $nav = floatval($row['nav']);
                $tp = floatval($row['target_price']);
                $sl = floatval($row['stop_loss']);
                $entry = floatval($row['entry_price']);

                $hit_tp = ($nav >= $tp);
                $hit_sl = ($nav <= $sl);

                if ($hit_tp || $hit_sl) {
                    $exit_price = $hit_tp ? $tp : $sl;
                    $pnl = round(($exit_price - $entry) / $entry * 100, 4);
                    $status = ($pnl >= 0) ? 'won' : 'lost';
                    $hold = round((strtotime($row['nav_date']) - strtotime($row['logged_at'])) / 86400);

                    $conn->query("UPDATE goldmine_cursor_predictions SET
                        status = '$status',
                        exit_price = $exit_price,
                        exit_date = '" . $conn->real_escape_string($row['nav_date']) . " 16:00:00',
                        pnl_pct = $pnl,
                        hold_days = $hold,
                        resolved_at = NOW()
                        WHERE id = $id AND status = 'open'");

                    $resolved_ids[$id] = true;
                    $resolve_count++;
                }
            }
        }
    } elseif (gc_table_exists($conn, 'mf_nav_history')) {
        $r = $conn->query("SELECT p.id, p.ticker, p.entry_price, p.target_price, p.stop_loss, p.logged_at,
            n.nav, n.nav_date
            FROM goldmine_cursor_predictions p
            JOIN mf_nav_history n ON n.ticker = p.ticker
                AND n.nav_date > DATE(p.logged_at)
                AND n.nav_date <= DATE_ADD(DATE(p.logged_at), INTERVAL 90 DAY)
            WHERE p.status = 'open' AND p.asset_class = 'mutualfunds'
            ORDER BY p.id, n.nav_date ASC");

        if ($r) {
            $resolved_ids = array();
            while ($row = $r->fetch_assoc()) {
                $id = intval($row['id']);
                if (isset($resolved_ids[$id])) { continue; }

                $nav = floatval($row['nav']);
                $tp = floatval($row['target_price']);
                $sl = floatval($row['stop_loss']);
                $entry = floatval($row['entry_price']);

                if ($nav >= $tp || $nav <= $sl) {
                    $exit_price = ($nav >= $tp) ? $tp : $sl;
                    $pnl = round(($exit_price - $entry) / $entry * 100, 4);
                    $status = ($pnl >= 0) ? 'won' : 'lost';
                    $hold = round((strtotime($row['nav_date']) - strtotime($row['logged_at'])) / 86400);

                    $conn->query("UPDATE goldmine_cursor_predictions SET
                        status = '$status', exit_price = $exit_price,
                        exit_date = '" . $conn->real_escape_string($row['nav_date']) . " 16:00:00',
                        pnl_pct = $pnl, hold_days = $hold, resolved_at = NOW()
                        WHERE id = $id AND status = 'open'");

                    $resolved_ids[$id] = true;
                    $resolve_count++;
                }
            }
        }
    }

    // Expire mutual fund picks older than 90 days still open
    $conn->query("UPDATE goldmine_cursor_predictions SET
        status = 'expired', resolved_at = NOW()
        WHERE status = 'open' AND asset_class = 'mutualfunds'
        AND logged_at < DATE_SUB(NOW(), INTERVAL 90 DAY)");

    $results['mutualfunds'] = array('new' => $new_count, 'resolved' => $resolve_count);
    $total_new = $total_new + $new_count;
    $total_resolved = $total_resolved + $resolve_count;
}

$conn->close();

$out = array(
    'ok' => true,
    'action' => 'harvest',
    'source_filter' => $source_filter,
    'total_new_predictions' => $total_new,
    'total_resolved' => $total_resolved,
    'by_source' => $results,
    'timestamp' => gmdate('Y-m-d H:i:s')
);
if ($debug && count($debug_info) > 0) {
    $out['debug'] = $debug_info;
}
echo json_encode($out);
?>
