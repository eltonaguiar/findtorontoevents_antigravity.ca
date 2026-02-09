<?php
/**
 * Volatility Filter Helper
 * Determines whether a given trade date falls in a high-volatility period.
 * Used by backtest.php and analyze.php to skip trades during volatile markets.
 * PHP 5.2 compatible.
 *
 * Volatility levels (based on VIX):
 *   calm       — VIX < 16   (historically low, very safe to trade)
 *   normal     — VIX 16-20  (typical conditions)
 *   elevated   — VIX 20-25  (caution, may want reduced position sizes)
 *   high       — VIX 25-35  (high volatility, consider sitting out)
 *   extreme    — VIX > 35   (crisis-level, definitely sit out)
 *
 * Filter modes:
 *   'off'          — no filtering (trade always)
 *   'skip_high'    — skip when VIX >= 25 (skip high + extreme)
 *   'skip_elevated'— skip when VIX >= 20 (skip elevated + high + extreme)
 *   'calm_only'    — only trade when VIX < 16 (most conservative)
 *   'custom'       — use max_vix parameter
 */

/**
 * Load VIX data from market_regimes into a date->vix_close lookup array.
 * Call this once per backtest run to avoid repeated DB queries.
 */
function vol_load_vix_data($conn) {
    $vix_data = array();
    $r = $conn->query("SELECT trade_date, vix_close, regime FROM market_regimes WHERE vix_close > 0 ORDER BY trade_date ASC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $vix_data[$row['trade_date']] = array(
                'vix' => (float)$row['vix_close'],
                'regime' => $row['regime']
            );
        }
    }
    return $vix_data;
}

/**
 * Get the VIX level for a specific date.
 * If exact date not found, looks back up to 5 days (weekends/holidays).
 */
function vol_get_vix($vix_data, $date) {
    if (isset($vix_data[$date])) return $vix_data[$date]['vix'];

    // Look back up to 5 days for weekends/holidays
    for ($i = 1; $i <= 5; $i++) {
        $prev = date('Y-m-d', strtotime($date) - ($i * 86400));
        if (isset($vix_data[$prev])) return $vix_data[$prev]['vix'];
    }
    return -1; // No VIX data available
}

/**
 * Get the regime for a specific date.
 */
function vol_get_regime($vix_data, $date) {
    if (isset($vix_data[$date])) return $vix_data[$date]['regime'];

    for ($i = 1; $i <= 5; $i++) {
        $prev = date('Y-m-d', strtotime($date) - ($i * 86400));
        if (isset($vix_data[$prev])) return $vix_data[$prev]['regime'];
    }
    return 'unknown';
}

/**
 * Should this trade be skipped based on volatility?
 *
 * @param array  $vix_data     Loaded VIX data from vol_load_vix_data()
 * @param string $date         The trade date (pick_date)
 * @param string $filter_mode  'off'|'skip_high'|'skip_elevated'|'calm_only'|'custom'
 * @param float  $max_vix      Custom max VIX threshold (only used when filter_mode='custom')
 * @return array  ('skip'=>bool, 'vix'=>float, 'regime'=>string, 'reason'=>string)
 */
function vol_should_skip($vix_data, $date, $filter_mode, $max_vix) {
    $result = array('skip' => false, 'vix' => 0, 'regime' => 'unknown', 'reason' => '');

    if ($filter_mode === 'off') return $result;

    $vix = vol_get_vix($vix_data, $date);
    $regime = vol_get_regime($vix_data, $date);
    $result['vix'] = $vix;
    $result['regime'] = $regime;

    // No VIX data: don't skip (can't judge)
    if ($vix < 0) {
        $result['reason'] = 'no_vix_data';
        return $result;
    }

    $threshold = 999;
    if ($filter_mode === 'skip_high') $threshold = 25;
    elseif ($filter_mode === 'skip_elevated') $threshold = 20;
    elseif ($filter_mode === 'calm_only') $threshold = 16;
    elseif ($filter_mode === 'custom') $threshold = ($max_vix > 0) ? $max_vix : 25;

    if ($vix >= $threshold) {
        $result['skip'] = true;
        $result['reason'] = 'VIX ' . $vix . ' >= ' . $threshold . ' (' . $filter_mode . ')';
    }

    return $result;
}

/**
 * Get a human-readable label for the volatility filter mode.
 */
function vol_filter_label($mode, $max_vix) {
    if ($mode === 'off') return 'No volatility filter';
    if ($mode === 'skip_high') return 'Skip when VIX >= 25';
    if ($mode === 'skip_elevated') return 'Skip when VIX >= 20';
    if ($mode === 'calm_only') return 'Only trade when VIX < 16';
    if ($mode === 'custom') return 'Skip when VIX >= ' . $max_vix;
    return $mode;
}

/**
 * Classify a VIX value into a human-readable volatility level.
 */
function vol_classify_vix($vix) {
    if ($vix < 0) return 'unknown';
    if ($vix < 16) return 'calm';
    if ($vix < 20) return 'normal';
    if ($vix < 25) return 'elevated';
    if ($vix < 35) return 'high';
    return 'extreme';
}
?>
