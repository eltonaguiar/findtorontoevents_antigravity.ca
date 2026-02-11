<?php
/**
 * GOLDMINE_CURSOR — Harvest Predictions from All Source Systems
 * Pulls new predictions from stocks, crypto, forex, sports, mutual funds
 * into the unified goldmine_cursor_predictions ledger.
 * PHP 5.2 compatible.
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

// Debug: check what tables exist
if ($debug) {
    $r = $conn->query("SHOW TABLES");
    $tables = array();
    if ($r) { while ($row = $r->fetch_row()) { $tables[] = $row[0]; } }
    $debug_info['all_tables'] = $tables;

    $r2 = $conn->query("SELECT COUNT(*) as cnt, MAX(pick_date) as latest, MIN(pick_date) as earliest FROM stock_picks");
    if ($r2 && $row = $r2->fetch_assoc()) { $debug_info['stock_picks_stats'] = $row; }
    else { $debug_info['stock_picks_stats'] = 'query failed: ' . $conn->error; }

    $r3 = $conn->query("SELECT COUNT(*) as cnt, MAX(pick_date) as latest FROM stock_picks WHERE pick_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY) AND entry_price > 0");
    if ($r3 && $row = $r3->fetch_assoc()) { $debug_info['stock_picks_90d'] = $row; }
    else { $debug_info['stock_picks_90d_error'] = $conn->error; }
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

// ═══════════════════════════════════════════
//  HARVEST: Stock picks
// ═══════════════════════════════════════════
if ($source_filter === 'all' || $source_filter === 'stocks') {
    $new_count = 0;
    $resolve_count = 0;

    // Pull from stock_picks table
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

    // Resolve open stock predictions using daily_prices
    $r = $conn->query("SELECT p.id, p.ticker, p.entry_price, p.target_price, p.stop_loss, p.logged_at,
        dp.close_price, dp.high_price, dp.low_price, dp.trade_date
        FROM goldmine_cursor_predictions p
        JOIN daily_prices dp ON dp.ticker = p.ticker
            AND dp.trade_date > DATE(p.logged_at)
            AND dp.trade_date <= DATE_ADD(DATE(p.logged_at), INTERVAL 30 DAY)
        WHERE p.status = 'open' AND p.asset_class = 'stocks'
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

        // Expire picks older than 30 days still open
        $conn->query("UPDATE goldmine_cursor_predictions SET
            status = 'expired',
            resolved_at = NOW()
            WHERE status = 'open' AND asset_class = 'stocks'
            AND logged_at < DATE_SUB(NOW(), INTERVAL 30 DAY)");
    }

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
    $chk = $conn->query("SHOW TABLES LIKE 'lm_sports_daily_picks'");
    if ($chk && $chk->num_rows > 0) {
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
    }

    // Sync settled status from source
    $chk2 = $conn->query("SHOW TABLES LIKE 'lm_sports_daily_picks'");
    if ($chk2 && $chk2->num_rows > 0) {
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
//  HARVEST: Crypto picks
// ═══════════════════════════════════════════
if ($source_filter === 'all' || $source_filter === 'crypto') {
    $new_count = 0;

    // Pull from crypto picks table (if exists in this DB)
    $chk = $conn->query("SHOW TABLES LIKE 'crypto_picks'");
    if ($chk && $chk->num_rows > 0) {
        $r = $conn->query("SELECT * FROM crypto_picks
            WHERE pick_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            ORDER BY pick_date DESC LIMIT 300");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $pid = gc_pred_id('findcryptopairs', $row['algorithm_name'], $row['pair'], $row['pick_date']);
                $entry = floatval($row['entry_price']);
                $tp_pct = isset($row['target_tp_pct']) ? floatval($row['target_tp_pct']) : 5;
                $sl_pct = isset($row['target_sl_pct']) ? floatval($row['target_sl_pct']) : 3;

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'crypto',
                    'ticker' => $row['pair'],
                    'algorithm' => $row['algorithm_name'],
                    'direction' => isset($row['direction']) ? $row['direction'] : 'long',
                    'entry_price' => $entry,
                    'target_price' => round($entry * (1 + $tp_pct / 100), 6),
                    'stop_loss' => round($entry * (1 - $sl_pct / 100), 6),
                    'confidence_score' => isset($row['score']) ? intval($row['score']) : 50,
                    'source_system' => 'findcryptopairs',
                    'logged_at' => $row['pick_date'] . ' 00:00:00',
                    'market_regime' => 'unknown',
                    'status' => 'open'
                );
                if (gc_insert_prediction($conn, $data)) { $new_count++; }
            }
        }
    }

    $results['crypto'] = array('new' => $new_count, 'resolved' => 0);
    $total_new = $total_new + $new_count;
}

// ═══════════════════════════════════════════
//  HARVEST: Forex picks
// ═══════════════════════════════════════════
if ($source_filter === 'all' || $source_filter === 'forex') {
    $new_count = 0;

    $chk = $conn->query("SHOW TABLES LIKE 'forex_picks'");
    if ($chk && $chk->num_rows > 0) {
        $r = $conn->query("SELECT * FROM forex_picks
            WHERE pick_date >= DATE_SUB(NOW(), INTERVAL 90 DAY)
            ORDER BY pick_date DESC LIMIT 300");
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $pid = gc_pred_id('findforex2', $row['algorithm_name'], $row['pair'], $row['pick_date']);
                $entry = floatval($row['entry_price']);
                $tp_pct = isset($row['target_tp_pct']) ? floatval($row['target_tp_pct']) : 2;
                $sl_pct = isset($row['target_sl_pct']) ? floatval($row['target_sl_pct']) : 1;

                $data = array(
                    'prediction_id' => $pid,
                    'asset_class' => 'forex',
                    'ticker' => $row['pair'],
                    'algorithm' => $row['algorithm_name'],
                    'direction' => isset($row['direction']) ? $row['direction'] : 'long',
                    'entry_price' => $entry,
                    'target_price' => round($entry * (1 + $tp_pct / 100), 6),
                    'stop_loss' => round($entry * (1 - $sl_pct / 100), 6),
                    'confidence_score' => isset($row['score']) ? intval($row['score']) : 50,
                    'source_system' => 'findforex2',
                    'logged_at' => $row['pick_date'] . ' 00:00:00',
                    'market_regime' => 'unknown',
                    'status' => 'open'
                );
                if (gc_insert_prediction($conn, $data)) { $new_count++; }
            }
        }
    }

    $results['forex'] = array('new' => $new_count, 'resolved' => 0);
    $total_new = $total_new + $new_count;
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
