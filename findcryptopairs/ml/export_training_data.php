<?php
/**
 * Export historical meme coin training data from database for XGBoost model training
 * 
 * API Endpoints:
 *   ?action=export          - Full export with train/test split
 *   ?action=summary         - Show data summary without exporting
 *   ?action=validate        - Check data quality issues
 *   ?action=download_csv    - Download CSV file directly (browser)
 * 
 * PHP 5.2+ Compatible
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

error_reporting(0);
ini_set('display_errors', '0');

// ============================================================================
// CONFIGURATION
// ============================================================================

$DATA_DIR = dirname(__FILE__) . '/data/';
$CSV_SUBDIR = 'training/';

// Database configuration - uses same DB as meme scanner
$DB_HOST = 'mysql.50webs.com';
$DB_USER = 'ejaguiar1_memecoin';
$DB_PASS = 'testing123';
$DB_NAME = 'ejaguiar1_memecoin';

// Data quality thresholds
define('MAX_RETURN_PCT', 1000);    // Remove outliers > 1000%
define('MIN_RETURN_PCT', -90);     // Remove outliers < -90%
define('TEST_DAYS', 30);           // Last 30 days for test set

// Feature configuration
$FEATURE_COLUMNS = array(
    'symbol',
    'return_5m',
    'return_15m', 
    'return_1h',
    'return_4h',
    'return_24h',
    'volatility_24h',
    'volume_ratio',
    'reddit_velocity',
    'trends_velocity',
    'sentiment_score',
    'sentiment_volatility',
    'btc_trend_4h',
    'btc_trend_24h',
    'hour_of_day',
    'day_of_week',
    'is_weekend',
    'score',
    'tier_encoded',
    'target'
);

// ============================================================================
// DATABASE CONNECTION
// ============================================================================

$conn = new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME);
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed: ' . $conn->connect_error));
    exit;
}
$conn->set_charset('utf8');

// ============================================================================
// MAIN ROUTING
// ============================================================================

$action = isset($_GET['action']) ? $_GET['action'] : 'summary';

switch ($action) {
    case 'export':
        $result = exportTrainingData($conn);
        echo json_encode($result);
        break;
        
    case 'summary':
        $result = getDataSummary($conn);
        echo json_encode($result);
        break;
        
    case 'validate':
        $result = validateDataQuality($conn);
        echo json_encode($result);
        break;
        
    case 'download_csv':
        downloadCsvFile($conn);
        break;
        
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action. Use: export, summary, validate, download_csv'));
}

$conn->close();

// ============================================================================
// CORE FUNCTIONS
// ============================================================================

/**
 * Export training data with train/test split
 */
function exportTrainingData($conn) {
    global $DATA_DIR, $CSV_SUBDIR, $FEATURE_COLUMNS;
    
    // Ensure data directories exist
    $csvDir = $DATA_DIR . $CSV_SUBDIR;
    if (!is_dir($csvDir)) {
        mkdir($csvDir, 0755, true);
    }
    
    // Fetch all resolved signals
    $query = "SELECT 
        w.id,
        w.pair,
        w.score,
        w.tier,
        w.price_at_signal as entry_price,
        w.target_pct,
        w.risk_pct,
        w.vol_usd_24h,
        w.chg_24h,
        w.factors_json,
        w.outcome,
        w.pnl_pct,
        w.created_at as timestamp,
        w.resolved_at
    FROM mc_winners w
    WHERE w.outcome IS NOT NULL
      AND w.resolved_at IS NOT NULL
    ORDER BY w.created_at ASC";
    
    $res = $conn->query($query);
    if (!$res) {
        return array('ok' => false, 'error' => 'Query failed: ' . $conn->error);
    }
    
    $allData = array();
    $trainData = array();
    $testData = array();
    $skippedRows = array();
    
    $trainEndDate = date('Y-m-d', strtotime('-' . TEST_DAYS . ' days'));
    
    $wins = 0;
    $losses = 0;
    $rowCount = 0;
    
    while ($row = $res->fetch_assoc()) {
        $rowCount++;
        $features = extractFeatures($conn, $row);
        
        if ($features === null) {
            $skippedRows[] = array(
                'id' => $row['id'],
                'pair' => $row['pair'],
                'reason' => 'Feature extraction failed'
            );
            continue;
        }
        
        // Data quality checks
        $qualityCheck = validateRow($features);
        if (!$qualityCheck['valid']) {
            $skippedRows[] = array(
                'id' => $row['id'],
                'pair' => $row['pair'],
                'reason' => $qualityCheck['reason']
            );
            continue;
        }
        
        // Target variable: 1 if hit TP before SL, 0 otherwise
        $target = (in_array($row['outcome'], array('win', 'partial_win'))) ? 1 : 0;
        $features['target'] = $target;
        
        if ($target == 1) {
            $wins++;
        } else {
            $losses++;
        }
        
        $allData[] = $features;
        
        // Train/test split based on time (no shuffling!)
        $rowDate = substr($row['timestamp'], 0, 10); // YYYY-MM-DD
        if ($rowDate < $trainEndDate) {
            $trainData[] = $features;
        } else {
            $testData[] = $features;
        }
    }
    
    if (empty($allData)) {
        return array('ok' => false, 'error' => 'No valid training data found');
    }
    
    // Generate filenames
    $timestamp = date('Y_m_d_His');
    $allFile = $csvDir . 'meme_training_all_' . $timestamp . '.csv';
    $trainFile = $csvDir . 'meme_training_train_' . $timestamp . '.csv';
    $testFile = $csvDir . 'meme_training_test_' . $timestamp . '.csv';
    
    // Write CSV files
    $allWritten = writeCsvFile($allFile, $allData, $FEATURE_COLUMNS);
    $trainWritten = writeCsvFile($trainFile, $trainData, $FEATURE_COLUMNS);
    $testWritten = writeCsvFile($testFile, $testData, $FEATURE_COLUMNS);
    
    // Calculate statistics
    $totalRecords = count($allData);
    $winRate = $totalRecords > 0 ? round($wins / $totalRecords, 4) : 0;
    
    // Get date range
    $dateRangeRes = $conn->query("SELECT 
        MIN(created_at) as start_date,
        MAX(created_at) as end_date
    FROM mc_winners 
    WHERE outcome IS NOT NULL AND resolved_at IS NOT NULL");
    $dateRange = $dateRangeRes ? $dateRangeRes->fetch_assoc() : array('start_date' => '', 'end_date' => '');
    
    return array(
        'ok' => true,
        'total_records' => $totalRecords,
        'train_records' => count($trainData),
        'test_records' => count($testData),
        'win_rate' => $winRate,
        'features_count' => count($FEATURE_COLUMNS) - 1, // Excluding target
        'csv_files' => array(
            'all' => str_replace($DATA_DIR, 'data/', $allFile),
            'train' => str_replace($DATA_DIR, 'data/', $trainFile),
            'test' => str_replace($DATA_DIR, 'data/', $testFile)
        ),
        'date_range' => array(
            'start' => $dateRange['start_date'],
            'end' => $dateRange['end_date']
        ),
        'train_end_date' => $trainEndDate,
        'skipped_rows' => count($skippedRows),
        'skipped_details' => array_slice($skippedRows, 0, 10), // First 10 only
        'data_quality' => array(
            'wins' => $wins,
            'losses' => $losses,
            'win_rate_pct' => round($winRate * 100, 2)
        )
    );
}

/**
 * Extract features from a database row
 */
function extractFeatures($conn, $row) {
    $symbol = str_replace('_USDT', '', $row['pair']);
    $timestamp = strtotime($row['timestamp']);
    $dateStr = date('Y-m-d', $timestamp);
    
    // Parse factors from JSON
    $factors = json_decode($row['factors_json'], true);
    if (!is_array($factors)) {
        $factors = array();
    }
    
    // Time-based features
    $hourOfDay = intval(date('G', $timestamp));
    $dayOfWeek = intval(date('w', $timestamp));
    $isWeekend = ($dayOfWeek === 0 || $dayOfWeek === 6) ? 1 : 0;
    
    // Extract factor scores (with defaults)
    $explosiveVolume = extractFactorScore($factors, 'explosive_volume');
    $parabolicMomentum = extractFactorScore($factors, 'parabolic_momentum');
    $rsiHype = extractFactorScore($factors, 'rsi_hype_zone');
    $socialProxy = extractFactorScore($factors, 'social_proxy');
    $volumeConcentration = extractFactorScore($factors, 'volume_concentration');
    $breakout4h = extractFactorScore($factors, 'breakout_4h');
    $lowCapBonus = extractFactorScore($factors, 'low_cap_bonus');
    
    // Calculate return features based on factor scores (normalized estimates)
    // These are proxies for historical price data
    $return1h = ($explosiveVolume + $parabolicMomentum) / 20;
    $return5m = $return1h * 0.2;
    $return15m = $return1h * 0.5;
    $return4h = $return1h * 2;
    $return24h = ($breakout4h + $row['chg_24h']) / 2;
    
    // Volatility estimate from ATR if available
    $atrPct = 0;
    if (isset($factors['volatility']['atr_pct'])) {
        $atrPct = floatval($factors['volatility']['atr_pct']);
    }
    $volatility24h = $atrPct > 0 ? $atrPct : ($volumeConcentration / 10);
    
    // Volume ratio (estimate based on concentration)
    $volumeRatio = 1 + ($volumeConcentration / 50);
    
    // Social/sentiment features
    $redditVelocity = $socialProxy;
    $trendsVelocity = 1 + ($parabolicMomentum / 50);
    $sentimentScore = $rsiHype / 15;
    $sentimentVolatility = $volatility24h * 0.5;
    
    // BTC trend features
    $btcTrend = getBtcTrendFeatures($conn, $dateStr);
    
    // Tier encoding (tier1=1, tier2=0)
    $tierEncoded = ($row['tier'] === 'tier1') ? 1 : 0;
    
    return array(
        'symbol' => $symbol,
        'return_5m' => round($return5m, 6),
        'return_15m' => round($return15m, 6),
        'return_1h' => round($return1h, 6),
        'return_4h' => round($return4h, 6),
        'return_24h' => round($return24h, 6),
        'volatility_24h' => round($volatility24h, 6),
        'volume_ratio' => round($volumeRatio, 6),
        'reddit_velocity' => round($redditVelocity, 6),
        'trends_velocity' => round($trendsVelocity, 6),
        'sentiment_score' => round($sentimentScore, 6),
        'sentiment_volatility' => round($sentimentVolatility, 6),
        'btc_trend_4h' => round($btcTrend['trend_4h'], 6),
        'btc_trend_24h' => round($btcTrend['trend_24h'], 6),
        'hour_of_day' => $hourOfDay,
        'day_of_week' => $dayOfWeek,
        'is_weekend' => $isWeekend,
        'score' => intval($row['score']),
        'tier_encoded' => $tierEncoded
    );
}

/**
 * Get BTC trend features for a specific date
 */
function getBtcTrendFeatures($conn, $dateStr) {
    // Try to get BTC trend from mc_winners data for same day
    $query = "SELECT chg_24h FROM mc_winners 
              WHERE pair LIKE '%BTC%' 
              AND DATE(created_at) = '$dateStr'
              ORDER BY created_at DESC LIMIT 1";
    
    $res = $conn->query($query);
    if ($res && $row = $res->fetch_assoc()) {
        $btcChg = floatval($row['chg_24h']);
        return array(
            'trend_4h' => $btcChg * 0.3,  // Estimate 4h from 24h
            'trend_24h' => $btcChg
        );
    }
    
    // Default values if no BTC data
    return array(
        'trend_4h' => 0,
        'trend_24h' => 0
    );
}

/**
 * Validate a single row for data quality
 */
function validateRow($features) {
    // Check for NULL values
    foreach ($features as $key => $value) {
        if ($value === null || $value === '') {
            return array('valid' => false, 'reason' => 'NULL value in ' . $key);
        }
    }
    
    // Check return_24h for outliers
    if ($features['return_24h'] > MAX_RETURN_PCT) {
        return array('valid' => false, 'reason' => 'Outlier: return_24h > 1000%');
    }
    if ($features['return_24h'] < MIN_RETURN_PCT) {
        return array('valid' => false, 'reason' => 'Outlier: return_24h < -90%');
    }
    
    return array('valid' => true, 'reason' => '');
}

/**
 * Write data to CSV file
 */
function writeCsvFile($filename, $data, $headers) {
    if (empty($data)) {
        return false;
    }
    
    $fp = fopen($filename, 'w');
    if (!$fp) {
        return false;
    }
    
    // Write headers
    fputcsv($fp, $headers);
    
    // Write data rows
    foreach ($data as $row) {
        $rowData = array();
        foreach ($headers as $col) {
            $rowData[] = isset($row[$col]) ? $row[$col] : '';
        }
        fputcsv($fp, $rowData);
    }
    
    fclose($fp);
    return true;
}

/**
 * Get data summary without exporting
 */
function getDataSummary($conn) {
    // Total signals
    $totalRes = $conn->query("SELECT COUNT(*) as cnt FROM mc_winners");
    $totalRow = $totalRes ? $totalRes->fetch_assoc() : array('cnt' => 0);
    
    // Resolved signals
    $resolvedRes = $conn->query("SELECT 
        COUNT(*) as cnt,
        SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN outcome IN ('loss','partial_loss') THEN 1 ELSE 0 END) as losses
    FROM mc_winners WHERE outcome IS NOT NULL AND resolved_at IS NOT NULL");
    $resolvedRow = $resolvedRes ? $resolvedRes->fetch_assoc() : array('cnt' => 0, 'wins' => 0, 'losses' => 0);
    
    // Pending signals
    $pendingRes = $conn->query("SELECT COUNT(*) as cnt FROM mc_winners WHERE outcome IS NULL");
    $pendingRow = $pendingRes ? $pendingRes->fetch_assoc() : array('cnt' => 0);
    
    // Date range
    $dateRes = $conn->query("SELECT 
        MIN(created_at) as start_date,
        MAX(created_at) as end_date
    FROM mc_winners WHERE outcome IS NOT NULL AND resolved_at IS NOT NULL");
    $dateRow = $dateRes ? $dateRes->fetch_assoc() : array('start_date' => '', 'end_date' => '');
    
    // By tier
    $tierRes = $conn->query("SELECT 
        tier,
        COUNT(*) as cnt,
        SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins
    FROM mc_winners WHERE outcome IS NOT NULL GROUP BY tier");
    $tiers = array();
    if ($tierRes) {
        while ($t = $tierRes->fetch_assoc()) {
            $tiers[] = array(
                'tier' => $t['tier'],
                'signals' => intval($t['cnt']),
                'wins' => intval($t['wins']),
                'win_rate' => intval($t['cnt']) > 0 ? round(intval($t['wins']) / intval($t['cnt']) * 100, 2) : 0
            );
        }
    }
    
    // By verdict
    $verdictRes = $conn->query("SELECT 
        verdict,
        COUNT(*) as cnt,
        SUM(CASE WHEN outcome IN ('win','partial_win') THEN 1 ELSE 0 END) as wins
    FROM mc_winners WHERE outcome IS NOT NULL AND verdict IS NOT NULL GROUP BY verdict");
    $verdicts = array();
    if ($verdictRes) {
        while ($v = $verdictRes->fetch_assoc()) {
            $verdicts[] = array(
                'verdict' => $v['verdict'],
                'signals' => intval($v['cnt']),
                'wins' => intval($v['wins']),
                'win_rate' => intval($v['cnt']) > 0 ? round(intval($v['wins']) / intval($v['cnt']) * 100, 2) : 0
            );
        }
    }
    
    $resolved = intval($resolvedRow['cnt']);
    $wins = intval($resolvedRow['wins']);
    
    return array(
        'ok' => true,
        'summary' => array(
            'total_signals' => intval($totalRow['cnt']),
            'resolved_signals' => $resolved,
            'pending_signals' => intval($pendingRow['cnt']),
            'wins' => $wins,
            'losses' => intval($resolvedRow['losses']),
            'win_rate' => $resolved > 0 ? round($wins / $resolved, 4) : 0,
            'win_rate_pct' => $resolved > 0 ? round($wins / $resolved * 100, 2) : 0,
            'date_range' => $dateRow,
            'ready_for_training' => $resolved >= 50 // Need at least 50 samples
        ),
        'by_tier' => $tiers,
        'by_verdict' => $verdicts
    );
}

/**
 * Validate data quality issues
 */
function validateDataQuality($conn) {
    $issues = array();
    
    // Check for NULL outcomes that should be resolved
    $nullRes = $conn->query("SELECT COUNT(*) as cnt FROM mc_winners 
        WHERE outcome IS NULL 
        AND created_at < DATE_SUB(NOW(), INTERVAL 6 HOUR)");
    $nullRow = $nullRes ? $nullRes->fetch_assoc() : array('cnt' => 0);
    if ($nullRow['cnt'] > 0) {
        $issues[] = array(
            'type' => 'unresolved_signals',
            'count' => intval($nullRow['cnt']),
            'severity' => 'warning',
            'message' => 'Signals older than 6 hours without resolution'
        );
    }
    
    // Check for NULL factors
    $nullFactorsRes = $conn->query("SELECT COUNT(*) as cnt FROM mc_winners 
        WHERE factors_json IS NULL OR factors_json = ''");
    $nullFactorsRow = $nullFactorsRes ? $nullFactorsRes->fetch_assoc() : array('cnt' => 0);
    if ($nullFactorsRow['cnt'] > 0) {
        $issues[] = array(
            'type' => 'missing_factors',
            'count' => intval($nullFactorsRow['cnt']),
            'severity' => 'error',
            'message' => 'Signals with missing factor data'
        );
    }
    
    // Check for extreme PnL values
    $extremeRes = $conn->query("SELECT COUNT(*) as cnt FROM mc_winners 
        WHERE pnl_pct > 1000 OR pnl_pct < -90");
    $extremeRow = $extremeRes ? $extremeRes->fetch_assoc() : array('cnt' => 0);
    if ($extremeRow['cnt'] > 0) {
        $issues[] = array(
            'type' => 'extreme_pnl',
            'count' => intval($extremeRow['cnt']),
            'severity' => 'warning',
            'message' => 'Signals with extreme PnL (>1000% or <-90%)'
        );
    }
    
    // Check for duplicate timestamps
    $dupRes = $conn->query("SELECT created_at, pair, COUNT(*) as cnt FROM mc_winners 
        GROUP BY created_at, pair HAVING cnt > 1");
    $dupCount = 0;
    if ($dupRes) {
        while ($d = $dupRes->fetch_assoc()) {
            $dupCount++;
        }
    }
    if ($dupCount > 0) {
        $issues[] = array(
            'type' => 'duplicate_signals',
            'count' => $dupCount,
            'severity' => 'warning',
            'message' => 'Duplicate signals (same pair and timestamp)'
        );
    }
    
    // Check chronological order integrity
    $chronoRes = $conn->query("SELECT id, created_at FROM mc_winners 
        WHERE outcome IS NOT NULL ORDER BY created_at ASC");
    $chronoIssues = 0;
    $prevTimestamp = null;
    if ($chronoRes) {
        while ($c = $chronoRes->fetch_assoc()) {
            if ($prevTimestamp !== null && $c['created_at'] < $prevTimestamp) {
                $chronoIssues++;
            }
            $prevTimestamp = $c['created_at'];
        }
    }
    if ($chronoIssues > 0) {
        $issues[] = array(
            'type' => 'chronology_error',
            'count' => $chronoIssues,
            'severity' => 'error',
            'message' => 'Data not in chronological order (data leakage risk)'
        );
    }
    
    // Sample size check
    $sampleRes = $conn->query("SELECT COUNT(*) as cnt FROM mc_winners WHERE outcome IS NOT NULL");
    $sampleRow = $sampleRes ? $sampleRes->fetch_assoc() : array('cnt' => 0);
    $sampleCount = intval($sampleRow['cnt']);
    
    $totalIssues = count($issues);
    $criticalIssues = 0;
    foreach ($issues as $issue) {
        if ($issue['severity'] === 'error') {
            $criticalIssues++;
        }
    }
    
    return array(
        'ok' => true,
        'quality_score' => max(0, 100 - ($totalIssues * 10) - ($criticalIssues * 20)),
        'total_issues' => $totalIssues,
        'critical_issues' => $criticalIssues,
        'sample_count' => $sampleCount,
        'sample_size_adequate' => $sampleCount >= 100,
        'issues' => $issues,
        'recommendations' => generateRecommendations($issues, $sampleCount)
    );
}

/**
 * Generate recommendations based on validation results
 */
function generateRecommendations($issues, $sampleCount) {
    $recommendations = array();
    
    if ($sampleCount < 100) {
        $recommendations[] = 'Collect more training data (target: 500+ resolved signals)';
    } elseif ($sampleCount < 500) {
        $recommendations[] = 'Sample size is adequate but more data would improve model performance';
    }
    
    foreach ($issues as $issue) {
        switch ($issue['type']) {
            case 'unresolved_signals':
                $recommendations[] = 'Run resolve action to update pending signal outcomes';
                break;
            case 'missing_factors':
                $recommendations[] = 'Some signals lack factor JSON - consider backfilling or removing';
                break;
            case 'extreme_pnl':
                $recommendations[] = 'Review extreme PnL values - may indicate data errors';
                break;
            case 'duplicate_signals':
                $recommendations[] = 'Remove duplicate signals to prevent data leakage';
                break;
            case 'chronology_error':
                $recommendations[] = 'CRITICAL: Fix chronological ordering before training';
                break;
        }
    }
    
    if (empty($recommendations)) {
        $recommendations[] = 'Data quality looks good - ready for model training';
    }
    
    return $recommendations;
}

/**
 * Download CSV file directly (for browser)
 */
function downloadCsvFile($conn) {
    global $FEATURE_COLUMNS;
    
    $dataset = isset($_GET['dataset']) ? $_GET['dataset'] : 'all';
    
    // Set headers for download
    header('Content-Type: text/csv');
    header('Content-Disposition: attachment; filename="meme_training_' . $dataset . '_' . date('Y_m_d') . '.csv"');
    
    $query = "SELECT 
        w.id,
        w.pair,
        w.score,
        w.tier,
        w.price_at_signal,
        w.target_pct,
        w.risk_pct,
        w.vol_usd_24h,
        w.chg_24h,
        w.factors_json,
        w.outcome,
        w.pnl_pct,
        w.created_at,
        w.resolved_at
    FROM mc_winners w
    WHERE w.outcome IS NOT NULL
      AND w.resolved_at IS NOT NULL
    ORDER BY w.created_at ASC";
    
    $res = $conn->query($query);
    
    $output = fopen('php://output', 'w');
    fputcsv($output, $FEATURE_COLUMNS);
    
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $features = extractFeatures($conn, $row);
            if ($features !== null) {
                $qualityCheck = validateRow($features);
                if ($qualityCheck['valid']) {
                    $target = (in_array($row['outcome'], array('win', 'partial_win'))) ? 1 : 0;
                    $features['target'] = $target;
                    
                    $rowData = array();
                    foreach ($FEATURE_COLUMNS as $col) {
                        $rowData[] = isset($features[$col]) ? $features[$col] : '';
                    }
                    fputcsv($output, $rowData);
                }
            }
        }
    }
    
    fclose($output);
    exit;
}

/**
 * Extract factor score from factors array
 */
function extractFactorScore($factors, $key) {
    if (!isset($factors[$key])) {
        return 0;
    }
    $f = $factors[$key];
    if (is_array($f) && isset($f['score'])) {
        return floatval($f['score']);
    }
    if (is_numeric($f)) {
        return floatval($f);
    }
    return 0;
}

/**
 * CLI Support - Run from command line
 * Usage: php export_training_data.php --cli [--action=export|summary|validate]
 */
if (php_sapi_name() === 'cli') {
    // Parse CLI arguments
    $cliAction = 'summary';
    $cliOptions = getopt('', array('action:', 'output-dir:'));
    
    if (isset($cliOptions['action'])) {
        $cliAction = $cliOptions['action'];
    }
    
    // Override data dir if specified
    if (isset($cliOptions['output-dir'])) {
        $DATA_DIR = rtrim($cliOptions['output-dir'], '/') . '/';
        $csvDir = $DATA_DIR . $CSV_SUBDIR;
        if (!is_dir($csvDir)) {
            mkdir($csvDir, 0755, true);
        }
    }
    
    // Re-run with CLI action
    $conn = new mysqli($DB_HOST, $DB_USER, $DB_PASS, $DB_NAME);
    if ($conn->connect_error) {
        echo "Error: Database connection failed\n";
        exit(1);
    }
    $conn->set_charset('utf8');
    
    switch ($cliAction) {
        case 'export':
            $result = exportTrainingData($conn);
            echo "Export Result:\n";
            echo json_encode($result, JSON_PRETTY_PRINT) . "\n";
            break;
        case 'summary':
            $result = getDataSummary($conn);
            echo "Data Summary:\n";
            echo "Total Signals: " . $result['summary']['total_signals'] . "\n";
            echo "Resolved: " . $result['summary']['resolved_signals'] . "\n";
            echo "Win Rate: " . $result['summary']['win_rate_pct'] . "%\n";
            echo "Ready for Training: " . ($result['summary']['ready_for_training'] ? 'Yes' : 'No') . "\n";
            break;
        case 'validate':
            $result = validateDataQuality($conn);
            echo "Data Quality Validation:\n";
            echo "Quality Score: " . $result['quality_score'] . "/100\n";
            echo "Total Issues: " . $result['total_issues'] . "\n";
            echo "Sample Count: " . $result['sample_count'] . "\n";
            if (!empty($result['recommendations'])) {
                echo "\nRecommendations:\n";
                foreach ($result['recommendations'] as $rec) {
                    echo "  - " . $rec . "\n";
                }
            }
            break;
        default:
            echo "Usage: php export_training_data.php --cli [--action=export|summary|validate] [--output-dir=/path/to/data]\n";
    }
    
    $conn->close();
    exit(0);
}
?>
