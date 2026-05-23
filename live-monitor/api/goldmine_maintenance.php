<?php
/**
 * Goldmine Maintenance Script
 * 
 * Fixes common issues in the goldmine tracking system:
 * 1. Expires sports bets past their hold period (games already played)
 * 2. Expires meme coin picks past their hold period (obscure tokens with no price feed)
 * 3. Deduplicates/resolves stale alerts (keeps only the latest per type+system)
 * 4. Triggers price update for consolidated stocks showing $0
 * 
 * PHP 5.2 compatible. Run via HTTP GET with ?action=run
 * 
 * Actions:
 *   ?action=run       - Run all maintenance tasks
 *   ?action=status    - Show current status (read-only)
 *   ?action=expire    - Only expire stale picks
 *   ?action=alerts    - Only clean up duplicate alerts
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

require_once dirname(__FILE__) . '/db_config.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'status';
$dry_run = isset($_GET['dry_run']) ? true : false;

$conn = new mysqli($servername, $username, $password, $dbname);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed: ' . $conn->connect_error));
    exit;
}
$conn->set_charset('utf8');

$results = array();

// ============================================================================
// STATUS - Show current state
// ============================================================================
if ($action === 'status' || $action === 'run') {
    $status = array();
    
    // Count open sports picks past hold period
    $sql = "SELECT COUNT(*) as cnt FROM gm_unified_picks 
            WHERE source_system = 'sports' AND status = 'open' 
            AND pick_time < DATE_SUB(NOW(), INTERVAL 24 HOUR)";
    $r = mysqli_query($conn, $sql);
    $row = mysqli_fetch_assoc($r);
    $status['stale_sports_picks'] = intval($row['cnt']);
    
    // Count open meme picks past hold period
    $sql = "SELECT COUNT(*) as cnt FROM gm_unified_picks 
            WHERE source_system = 'meme' AND status = 'open' 
            AND pick_time < DATE_SUB(NOW(), INTERVAL 4 HOUR)";
    $r = mysqli_query($conn, $sql);
    $row = mysqli_fetch_assoc($r);
    $status['stale_meme_picks'] = intval($row['cnt']);
    
    // Count open penny picks past hold period
    $sql = "SELECT COUNT(*) as cnt FROM gm_unified_picks 
            WHERE source_system = 'penny' AND status = 'open' 
            AND pick_time < DATE_SUB(NOW(), INTERVAL 336 HOUR)";
    $r = mysqli_query($conn, $sql);
    $row = mysqli_fetch_assoc($r);
    $status['stale_penny_picks'] = intval($row['cnt']);
    
    // Count consolidated picks with $0 current price
    $sql = "SELECT COUNT(*) as cnt FROM gm_unified_picks 
            WHERE source_system = 'consolidated' AND status = 'open' 
            AND (current_price = 0 OR current_price IS NULL)";
    $r = mysqli_query($conn, $sql);
    $row = mysqli_fetch_assoc($r);
    $status['consolidated_missing_price'] = intval($row['cnt']);
    
    // Count active alerts
    $sql = "SELECT COUNT(*) as cnt FROM gm_failure_alerts WHERE is_active = 1";
    $r = mysqli_query($conn, $sql);
    $row = mysqli_fetch_assoc($r);
    $status['active_alerts'] = intval($row['cnt']);
    
    // Count duplicate alerts (same source_system + alert_type on different dates)
    $sql = "SELECT COUNT(*) as cnt FROM gm_failure_alerts a
            WHERE is_active = 1 
            AND EXISTS (
                SELECT 1 FROM gm_failure_alerts b 
                WHERE b.source_system = a.source_system 
                AND b.alert_type = a.alert_type 
                AND b.is_active = 1 
                AND b.alert_date > a.alert_date
            )";
    $r = mysqli_query($conn, $sql);
    $row = mysqli_fetch_assoc($r);
    $status['duplicate_alerts'] = intval($row['cnt']);
    
    $results['status'] = $status;
}

// ============================================================================
// EXPIRE - Close stale picks that are past their hold period
// ============================================================================
if ($action === 'run' || $action === 'expire') {
    $expire_results = array();
    
    // 1. Expire sports bets: All games from Feb 11-12 are long over.
    //    Sports bets have 4-hour hold periods. Any open pick older than 24h is definitely expired.
    if (!$dry_run) {
        $sql = "UPDATE gm_unified_picks 
                SET status = 'expired', 
                    exit_reason = 'hold_period_expired',
                    exit_date = DATE_ADD(pick_time, INTERVAL GREATEST(hold_period_hours, 4) HOUR),
                    final_return_pct = 0,
                    updated_at = NOW()
                WHERE source_system = 'sports' 
                AND status = 'open'
                AND pick_time < DATE_SUB(NOW(), INTERVAL 24 HOUR)";
        mysqli_query($conn, $sql);
        $expire_results['sports_expired'] = mysqli_affected_rows($conn);
    } else {
        $expire_results['sports_would_expire'] = 'dry_run';
    }
    
    // 2. Expire meme picks: 2-hour hold period. Any open pick older than 4h is expired.
    //    These obscure tokens have no price feed, so they can never be resolved by price.
    if (!$dry_run) {
        $sql = "UPDATE gm_unified_picks 
                SET status = 'expired', 
                    exit_reason = 'hold_period_expired',
                    exit_date = DATE_ADD(pick_time, INTERVAL GREATEST(hold_period_hours, 2) HOUR),
                    final_return_pct = 0,
                    updated_at = NOW()
                WHERE source_system = 'meme' 
                AND status = 'open'
                AND pick_time < DATE_SUB(NOW(), INTERVAL 4 HOUR)";
        mysqli_query($conn, $sql);
        $expire_results['meme_expired'] = mysqli_affected_rows($conn);
    } else {
        $expire_results['meme_would_expire'] = 'dry_run';
    }
    
    // 3. Expire any other picks older than their hold_period + 50% buffer
    //    (safety net for picks the outcome checker missed)
    if (!$dry_run) {
        $sql = "UPDATE gm_unified_picks 
                SET status = 'expired',
                    exit_reason = 'hold_period_expired',
                    exit_date = DATE_ADD(pick_time, INTERVAL hold_period_hours HOUR),
                    updated_at = NOW()
                WHERE status = 'open'
                AND hold_period_hours > 0
                AND TIMESTAMPDIFF(HOUR, pick_time, NOW()) > (hold_period_hours * 1.5)
                AND source_system NOT IN ('consolidated')";
        mysqli_query($conn, $sql);
        $expire_results['other_expired'] = mysqli_affected_rows($conn);
    } else {
        $expire_results['other_would_expire'] = 'dry_run';
    }
    
    // 4. For consolidated stocks with $0 current_price but non-zero entry_price,
    //    mark them for review (don't expire, just note the issue)
    $sql = "SELECT id, ticker, entry_price, pick_date FROM gm_unified_picks 
            WHERE source_system = 'consolidated' AND status = 'open' 
            AND (current_price = 0 OR current_price IS NULL)
            AND entry_price > 0
            ORDER BY pick_date DESC LIMIT 30";
    $r = mysqli_query($conn, $sql);
    $missing_price = array();
    while ($row = mysqli_fetch_assoc($r)) {
        $missing_price[] = $row['ticker'] . ' (id:' . $row['id'] . ', entry:$' . $row['entry_price'] . ')';
    }
    $expire_results['consolidated_missing_prices'] = $missing_price;
    
    $results['expire'] = $expire_results;
}

// ============================================================================
// PRICE FIX - Update $0 prices for consolidated stocks
// ============================================================================
if ($action === 'run' || $action === 'prices') {
    $price_results = array();
    
    // Get consolidated picks with missing prices
    $sql = "SELECT id, ticker, entry_price, pick_date, target_price, stop_loss_price 
            FROM gm_unified_picks 
            WHERE source_system = 'consolidated' AND status = 'open' 
            AND (current_price = 0 OR current_price IS NULL)
            AND entry_price > 0
            ORDER BY pick_date DESC";
    $r = mysqli_query($conn, $sql);
    
    $fixed = 0;
    $failed = array();
    
    while ($row = mysqli_fetch_assoc($r)) {
        $ticker = $row['ticker'];
        $pick_id = $row['id'];
        $entry_price = floatval($row['entry_price']);
        $target_price = floatval($row['target_price']);
        $stop_loss_price = floatval($row['stop_loss_price']);
        
        // Try to fetch current price from Yahoo Finance
        $price = _fetch_stock_price($ticker);
        
        if ($price > 0 && !$dry_run) {
            $return_pct = (($price - $entry_price) / $entry_price) * 100;
            
            // Check if TP or SL hit
            $new_status = 'open';
            $exit_reason = '';
            $exit_date_sql = 'NULL';
            
            if ($target_price > 0 && $price >= $target_price) {
                $new_status = 'tp_hit';
                $exit_reason = 'target_price_hit';
                $exit_date_sql = 'NOW()';
            } elseif ($stop_loss_price > 0 && $price <= $stop_loss_price) {
                $new_status = 'sl_hit';
                $exit_reason = 'stop_loss_hit';
                $exit_date_sql = 'NOW()';
            }
            
            $return_str = number_format($return_pct, 4);
            $price_str = number_format($price, 2, '.', '');
            
            if ($new_status === 'open') {
                $upd = "UPDATE gm_unified_picks SET 
                    current_price = " . $price_str . ",
                    current_return_pct = " . $return_str . ",
                    final_return_pct = " . $return_str . ",
                    total_return_pct = " . $return_str . ",
                    peak_price = GREATEST(peak_price, " . $price_str . "),
                    trough_price = IF(trough_price = 0, " . $price_str . ", LEAST(trough_price, " . $price_str . ")),
                    updated_at = NOW()
                    WHERE id = " . intval($pick_id);
            } else {
                $upd = "UPDATE gm_unified_picks SET 
                    current_price = " . $price_str . ",
                    exit_price = " . $price_str . ",
                    current_return_pct = " . $return_str . ",
                    final_return_pct = " . $return_str . ",
                    total_return_pct = " . $return_str . ",
                    status = '" . mysqli_real_escape_string($conn, $new_status) . "',
                    exit_reason = '" . mysqli_real_escape_string($conn, $exit_reason) . "',
                    exit_date = " . $exit_date_sql . ",
                    peak_price = GREATEST(peak_price, " . $price_str . "),
                    trough_price = IF(trough_price = 0, " . $price_str . ", LEAST(trough_price, " . $price_str . ")),
                    updated_at = NOW()
                    WHERE id = " . intval($pick_id);
            }
            
            mysqli_query($conn, $upd);
            $fixed++;
            $price_results[] = array(
                'ticker' => $ticker,
                'price' => $price,
                'return_pct' => round($return_pct, 2),
                'status' => $new_status
            );
        } else {
            $failed[] = $ticker;
        }
    }
    
    $results['prices'] = array(
        'fixed' => $fixed,
        'failed' => $failed,
        'details' => $price_results
    );
}

// ============================================================================
// ALERTS - Deduplicate and clean up stale alerts
// ============================================================================
if ($action === 'run' || $action === 'alerts') {
    $alert_results = array();
    
    // 1. Resolve duplicate alerts: For each (source_system, alert_type) combo,
    //    keep only the most recent alert active, resolve older duplicates
    if (!$dry_run) {
        $sql = "UPDATE gm_failure_alerts a
                SET a.is_active = 0,
                    a.resolved_at = NOW()
                WHERE a.is_active = 1
                AND EXISTS (
                    SELECT 1 FROM (
                        SELECT source_system, alert_type, MAX(alert_date) as max_date
                        FROM gm_failure_alerts
                        WHERE is_active = 1
                        GROUP BY source_system, alert_type
                        HAVING COUNT(*) > 1
                    ) b
                    WHERE b.source_system = a.source_system
                    AND b.alert_type = a.alert_type
                    AND a.alert_date < b.max_date
                )";
        mysqli_query($conn, $sql);
        $alert_results['duplicates_resolved'] = mysqli_affected_rows($conn);
    } else {
        $alert_results['duplicates_would_resolve'] = 'dry_run';
    }
    
    // 2. Auto-resolve stale_data alerts for systems that just got updated
    //    (After expiring the picks, the "stale data" alert for sports/meme may
    //     still be correct since no NEW picks are being generated. But we should
    //     at least clear the old duplicates.)
    
    // 3. Count remaining active alerts
    $sql = "SELECT source_system, alert_type, severity, title, alert_date 
            FROM gm_failure_alerts 
            WHERE is_active = 1 
            ORDER BY severity DESC, alert_date DESC";
    $r = mysqli_query($conn, $sql);
    $remaining = array();
    while ($row = mysqli_fetch_assoc($r)) {
        $remaining[] = $row;
    }
    $alert_results['remaining_active'] = $remaining;
    $alert_results['remaining_count'] = count($remaining);
    
    $results['alerts'] = $alert_results;
}

// ============================================================================
// Output results
// ============================================================================
$results['ok'] = true;
$results['action'] = $action;
$results['dry_run'] = $dry_run;
$results['timestamp'] = date('Y-m-d H:i:s');

mysqli_close($conn);
echo json_encode($results);

// ============================================================================
// HELPER: Fetch stock price from Yahoo Finance v8 API
// ============================================================================
function _fetch_stock_price($ticker) {
    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/' . urlencode($ticker) . '?interval=1d&range=1d';
    
    $ctx = stream_context_create(array(
        'http' => array(
            'timeout' => 5,
            'header' => "User-Agent: Mozilla/5.0\r\n"
        )
    ));
    
    $json = @file_get_contents($url, false, $ctx);
    if ($json === false) return 0;
    
    $data = @json_decode($json, true);
    if (!$data) return 0;
    
    // Navigate: chart -> result[0] -> meta -> regularMarketPrice
    if (!isset($data['chart'])) return 0;
    if (!isset($data['chart']['result'])) return 0;
    if (!is_array($data['chart']['result'])) return 0;
    if (count($data['chart']['result']) === 0) return 0;
    
    $result = $data['chart']['result'][0];
    if (isset($result['meta']) && isset($result['meta']['regularMarketPrice'])) {
        return floatval($result['meta']['regularMarketPrice']);
    }
    
    return 0;
}
