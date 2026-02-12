<?php
/**
 * populate_sample_data.php — Insert sample data into Live Monitor tables for testing.
 * PHP 5.2 compatible.
 *
 * WARNING: This inserts TEST data for lm_market_regime only.
 * Trade and signal tables are managed by their respective APIs.
 */

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/live_monitor_schema.php';

function _lm_populate_samples($conn) {
    // Ensure extra schema (lm_market_regime)
    _lm_ensure_extra_schema($conn);

    // Sample data for lm_market_regime (from HMM detection)
    $regime_samples = array(
        array('2026-02-01', 'bull', 0.05, 15.2, 0.85),
        array('2026-02-02', 'bear', -0.03, 25.1, 0.92),
        array('2026-02-03', 'chop', 0.01, 18.5, 0.78),
    );
    foreach ($regime_samples as $sample) {
        $conn->query("INSERT IGNORE INTO lm_market_regime (regime_date, regime, spy_ret, vix_value, confidence, created_at)
            VALUES ('$sample[0]', '$sample[1]', $sample[2], $sample[3], $sample[4], NOW())");
    }

    echo json_encode(array('ok' => true, 'message' => 'Sample regime data populated'));
}

// Run if called directly
if (basename(__FILE__) == basename($_SERVER['SCRIPT_FILENAME'])) {
    _lm_populate_samples($conn);
}

?>
