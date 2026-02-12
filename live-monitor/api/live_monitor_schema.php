<?php
/**
 * live_monitor_schema.php — Additional schema for Live Monitor features.
 *
 * NOTE: Core tables are auto-created by their respective APIs:
 *   - lm_trades → live_trade.php
 *   - lm_signals → live_signals.php
 *   - lm_kelly_fractions → live_trade.php (_lt_update_kelly)
 *   - lm_market_regime → worldclass regime detection system
 *
 * The lm_market_regime table already exists with columns:
 *   id, date, hmm_regime, hmm_confidence, hmm_persistence, hurst,
 *   hurst_regime, ewma_vol, vol_annualized, composite_score,
 *   strategy_toggles, vix_level, vix_regime, yield_curve,
 *   yield_spread, macro_score, ticker_regimes, created_at
 *
 * This file creates the table IF NOT EXISTS as a fallback only.
 * PHP 5.2 compatible.
 */

require_once dirname(__FILE__) . '/db_connect.php';

function _lm_ensure_extra_schema($conn) {

    // ── Market Regimes (rich schema from worldclass system) ──
    // This CREATE TABLE IF NOT EXISTS won't overwrite existing table
    $conn->query("CREATE TABLE IF NOT EXISTS lm_market_regime (
        id INT AUTO_INCREMENT PRIMARY KEY,
        date DATETIME NOT NULL,
        hmm_regime VARCHAR(20) NOT NULL DEFAULT 'sideways',
        hmm_confidence DECIMAL(6,4) NOT NULL DEFAULT 0.5000,
        hmm_persistence DECIMAL(6,4) NOT NULL DEFAULT 0.5000,
        hurst DECIMAL(6,4) NOT NULL DEFAULT 0.5000,
        hurst_regime VARCHAR(20) NOT NULL DEFAULT 'random',
        ewma_vol DECIMAL(10,8) NOT NULL DEFAULT 0.00000000,
        vol_annualized DECIMAL(8,4) NOT NULL DEFAULT 0.0000,
        composite_score DECIMAL(6,2) NOT NULL DEFAULT 50.00,
        strategy_toggles TEXT,
        vix_level DECIMAL(8,2) DEFAULT NULL,
        vix_regime VARCHAR(20) NOT NULL DEFAULT 'normal',
        yield_curve VARCHAR(20) NOT NULL DEFAULT 'normal',
        yield_spread DECIMAL(8,4) DEFAULT NULL,
        macro_score DECIMAL(6,2) NOT NULL DEFAULT 50.00,
        ticker_regimes TEXT,
        created_at DATETIME NOT NULL
    ) ENGINE=MyISAM DEFAULT CHARSET=utf8");
}

// Run schema creation if called directly (for setup)
if (basename(__FILE__) == basename($_SERVER['SCRIPT_FILENAME'])) {
    _lm_ensure_extra_schema($conn);
    echo json_encode(array('ok' => true, 'message' => 'Extra schema ensured (lm_market_regime)'));
}

?>
