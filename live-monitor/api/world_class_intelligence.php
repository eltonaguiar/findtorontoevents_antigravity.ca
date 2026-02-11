<?php
/**
 * World-Class Intelligence API
 * Stores and serves advanced trading intelligence from Python ML scripts
 * PHP 5.2 compatible — no short arrays, no http_response_code()
 *
 * Actions:
 *   store       — store a metric (admin key required)
 *   store_batch — store multiple metrics (admin key required)
 *   get         — get a single metric (public)
 *   regime      — get current regime state for all asset classes (public)
 *   hurst       — get current Hurst values (public)
 *   macro       — get macro regime overlay (public)
 *   meta_label  — get meta-label predictions for pending signals (public)
 *   dashboard   — full intelligence dashboard (public)
 *   kelly       — get per-algorithm Kelly fractions (public)
 *   algo_health — get alpha decay / online learning weights (public)
 */

require_once dirname(__FILE__) . '/db_connect.php';

$ADMIN_KEY = 'livetrader2026';

// ─── Auto-create intelligence tables ──────────────────────────────────
$conn->query("
CREATE TABLE IF NOT EXISTS lm_intelligence (
    id INT AUTO_INCREMENT PRIMARY KEY,
    metric_name VARCHAR(100) NOT NULL,
    asset_class VARCHAR(20) NOT NULL DEFAULT 'ALL',
    symbol VARCHAR(30) NOT NULL DEFAULT '',
    metric_value DECIMAL(18,8) NOT NULL DEFAULT 0,
    metric_label VARCHAR(100) NOT NULL DEFAULT '',
    metadata TEXT,
    updated_at DATETIME NOT NULL,
    KEY idx_metric (metric_name),
    KEY idx_asset (asset_class),
    KEY idx_symbol (symbol),
    KEY idx_updated (updated_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// Kelly fractions per algorithm
$conn->query("
CREATE TABLE IF NOT EXISTS lm_kelly_fractions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    algorithm_name VARCHAR(100) NOT NULL,
    asset_class VARCHAR(20) NOT NULL DEFAULT 'ALL',
    win_rate DECIMAL(6,4) NOT NULL DEFAULT 0,
    avg_win_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    avg_loss_pct DECIMAL(8,4) NOT NULL DEFAULT 0,
    full_kelly DECIMAL(8,6) NOT NULL DEFAULT 0,
    half_kelly DECIMAL(8,6) NOT NULL DEFAULT 0,
    sample_size INT NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_algo_asset (algorithm_name, asset_class)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// Meta-label predictions
$conn->query("
CREATE TABLE IF NOT EXISTS lm_meta_labels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    signal_id INT NOT NULL DEFAULT 0,
    algorithm_name VARCHAR(100) NOT NULL,
    symbol VARCHAR(30) NOT NULL,
    prediction DECIMAL(6,4) NOT NULL DEFAULT 0,
    confidence DECIMAL(6,4) NOT NULL DEFAULT 0,
    features TEXT,
    created_at DATETIME NOT NULL,
    KEY idx_signal (signal_id),
    KEY idx_created (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// Algorithm health / alpha decay tracking
$conn->query("
CREATE TABLE IF NOT EXISTS lm_algo_health (
    id INT AUTO_INCREMENT PRIMARY KEY,
    algorithm_name VARCHAR(100) NOT NULL,
    asset_class VARCHAR(20) NOT NULL DEFAULT 'ALL',
    rolling_sharpe_30d DECIMAL(8,4) NOT NULL DEFAULT 0,
    rolling_win_rate_30d DECIMAL(6,4) NOT NULL DEFAULT 0,
    rolling_pnl_30d DECIMAL(12,4) NOT NULL DEFAULT 0,
    online_weight DECIMAL(8,6) NOT NULL DEFAULT 1.0,
    decay_status VARCHAR(20) NOT NULL DEFAULT 'healthy',
    trades_30d INT NOT NULL DEFAULT 0,
    consecutive_losses INT NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL,
    UNIQUE KEY idx_algo_asset (algorithm_name, asset_class)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

// ─── CORS ──────────────────────────────────────────────────────────────
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

$action = isset($_GET['action']) ? $_GET['action'] : (isset($_POST['action']) ? $_POST['action'] : '');

// ─── Helper: verify admin key ──────────────────────────────────────────
function _wci_check_key() {
    global $ADMIN_KEY;
    $key = isset($_GET['key']) ? $_GET['key'] : (isset($_POST['key']) ? $_POST['key'] : '');
    return ($key === $ADMIN_KEY);
}

// ─── Helper: current UTC datetime ──────────────────────────────────────
function _wci_now() {
    return gmdate('Y-m-d H:i:s');
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: store — Store a single intelligence metric
// ════════════════════════════════════════════════════════════════════════
if ($action === 'store') {
    if (!_wci_check_key()) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }

    $metric  = isset($_POST['metric_name'])  ? $conn->real_escape_string($_POST['metric_name']) : '';
    $asset   = isset($_POST['asset_class'])   ? $conn->real_escape_string($_POST['asset_class']) : 'ALL';
    $symbol  = isset($_POST['symbol'])        ? $conn->real_escape_string($_POST['symbol']) : '';
    $value   = isset($_POST['metric_value'])  ? floatval($_POST['metric_value']) : 0;
    $label   = isset($_POST['metric_label'])  ? $conn->real_escape_string($_POST['metric_label']) : '';
    $meta    = isset($_POST['metadata'])      ? $conn->real_escape_string($_POST['metadata']) : '';
    $now     = _wci_now();

    if (!$metric) {
        echo json_encode(array('ok' => false, 'error' => 'metric_name required'));
        exit;
    }

    // Upsert: delete old + insert new (PHP 5.2 friendly)
    $conn->query("DELETE FROM lm_intelligence
        WHERE metric_name='$metric' AND asset_class='$asset' AND symbol='$symbol'");

    $conn->query("INSERT INTO lm_intelligence
        (metric_name, asset_class, symbol, metric_value, metric_label, metadata, updated_at)
        VALUES ('$metric', '$asset', '$symbol', $value, '$label', '$meta', '$now')");

    echo json_encode(array('ok' => true, 'stored' => $metric));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: store_batch — Store multiple metrics at once
// ════════════════════════════════════════════════════════════════════════
if ($action === 'store_batch') {
    if (!_wci_check_key()) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }

    $raw = isset($_POST['metrics']) ? $_POST['metrics'] : '';
    $metrics = json_decode($raw, true);
    if (!is_array($metrics)) {
        echo json_encode(array('ok' => false, 'error' => 'metrics must be JSON array'));
        exit;
    }

    $stored = 0;
    $now = _wci_now();
    foreach ($metrics as $m) {
        $metric = $conn->real_escape_string($m['metric_name']);
        $asset  = isset($m['asset_class']) ? $conn->real_escape_string($m['asset_class']) : 'ALL';
        $symbol = isset($m['symbol'])      ? $conn->real_escape_string($m['symbol']) : '';
        $value  = isset($m['metric_value']) ? floatval($m['metric_value']) : 0;
        $label  = isset($m['metric_label']) ? $conn->real_escape_string($m['metric_label']) : '';
        $meta   = isset($m['metadata'])     ? $conn->real_escape_string(json_encode($m['metadata'])) : '';

        $conn->query("DELETE FROM lm_intelligence
            WHERE metric_name='$metric' AND asset_class='$asset' AND symbol='$symbol'");

        $conn->query("INSERT INTO lm_intelligence
            (metric_name, asset_class, symbol, metric_value, metric_label, metadata, updated_at)
            VALUES ('$metric', '$asset', '$symbol', $value, '$label', '$meta', '$now')");
        $stored++;
    }

    echo json_encode(array('ok' => true, 'stored' => $stored));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: store_kelly — Store Kelly fractions for algorithms
// ════════════════════════════════════════════════════════════════════════
if ($action === 'store_kelly') {
    if (!_wci_check_key()) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }

    $raw = isset($_POST['kelly_data']) ? $_POST['kelly_data'] : '';
    $data = json_decode($raw, true);
    if (!is_array($data)) {
        echo json_encode(array('ok' => false, 'error' => 'kelly_data must be JSON array'));
        exit;
    }

    $stored = 0;
    $now = _wci_now();
    foreach ($data as $k) {
        $algo  = $conn->real_escape_string($k['algorithm_name']);
        $asset = isset($k['asset_class']) ? $conn->real_escape_string($k['asset_class']) : 'ALL';
        $wr    = floatval($k['win_rate']);
        $aw    = floatval($k['avg_win_pct']);
        $al    = floatval($k['avg_loss_pct']);
        $fk    = floatval($k['full_kelly']);
        $hk    = floatval($k['half_kelly']);
        $ss    = intval($k['sample_size']);

        $conn->query("DELETE FROM lm_kelly_fractions
            WHERE algorithm_name='$algo' AND asset_class='$asset'");

        $conn->query("INSERT INTO lm_kelly_fractions
            (algorithm_name, asset_class, win_rate, avg_win_pct, avg_loss_pct,
             full_kelly, half_kelly, sample_size, updated_at)
            VALUES ('$algo', '$asset', $wr, $aw, $al, $fk, $hk, $ss, '$now')");
        $stored++;
    }

    echo json_encode(array('ok' => true, 'stored' => $stored));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: store_algo_health — Store alpha decay + online learning weights
// ════════════════════════════════════════════════════════════════════════
if ($action === 'store_algo_health') {
    if (!_wci_check_key()) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }

    $raw = isset($_POST['health_data']) ? $_POST['health_data'] : '';
    $data = json_decode($raw, true);
    if (!is_array($data)) {
        echo json_encode(array('ok' => false, 'error' => 'health_data must be JSON array'));
        exit;
    }

    $stored = 0;
    $now = _wci_now();
    foreach ($data as $h) {
        $algo   = $conn->real_escape_string($h['algorithm_name']);
        $asset  = isset($h['asset_class']) ? $conn->real_escape_string($h['asset_class']) : 'ALL';
        $sharpe = floatval($h['rolling_sharpe_30d']);
        $wr     = floatval($h['rolling_win_rate_30d']);
        $pnl    = floatval($h['rolling_pnl_30d']);
        $weight = floatval($h['online_weight']);
        $status = $conn->real_escape_string($h['decay_status']);
        $trades = intval($h['trades_30d']);
        $consec = intval($h['consecutive_losses']);

        $conn->query("DELETE FROM lm_algo_health
            WHERE algorithm_name='$algo' AND asset_class='$asset'");

        $conn->query("INSERT INTO lm_algo_health
            (algorithm_name, asset_class, rolling_sharpe_30d, rolling_win_rate_30d,
             rolling_pnl_30d, online_weight, decay_status, trades_30d,
             consecutive_losses, updated_at)
            VALUES ('$algo', '$asset', $sharpe, $wr, $pnl, $weight, '$status',
                    $trades, $consec, '$now')");
        $stored++;
    }

    echo json_encode(array('ok' => true, 'stored' => $stored));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: get — Get a specific metric
// ════════════════════════════════════════════════════════════════════════
if ($action === 'get') {
    $metric = isset($_GET['metric_name']) ? $conn->real_escape_string($_GET['metric_name']) : '';
    $asset  = isset($_GET['asset_class']) ? $conn->real_escape_string($_GET['asset_class']) : '';
    $symbol = isset($_GET['symbol'])      ? $conn->real_escape_string($_GET['symbol']) : '';

    $where = "WHERE metric_name='$metric'";
    if ($asset)  $where .= " AND asset_class='$asset'";
    if ($symbol) $where .= " AND symbol='$symbol'";

    $r = $conn->query("SELECT * FROM lm_intelligence $where ORDER BY updated_at DESC LIMIT 10");
    $results = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $results[] = $row;
        }
        $r->free();
    }

    echo json_encode(array('ok' => true, 'results' => $results));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: regime — Current regime state for all asset classes
// ════════════════════════════════════════════════════════════════════════
if ($action === 'regime') {
    $regimes = array();

    // HMM regime (from Python ML)
    $r = $conn->query("SELECT * FROM lm_intelligence
        WHERE metric_name='hmm_regime'
        ORDER BY updated_at DESC LIMIT 10");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $regimes[$row['asset_class']] = array(
                'hmm_state' => $row['metric_label'],
                'hmm_value' => floatval($row['metric_value']),
                'updated' => $row['updated_at']
            );
        }
        $r->free();
    }

    // Hurst exponent
    $r = $conn->query("SELECT * FROM lm_intelligence
        WHERE metric_name='hurst_exponent'
        ORDER BY updated_at DESC LIMIT 10");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $key = $row['asset_class'];
            if (!isset($regimes[$key])) $regimes[$key] = array();
            $regimes[$key]['hurst'] = floatval($row['metric_value']);
            $regimes[$key]['hurst_regime'] = $row['metric_label'];
        }
        $r->free();
    }

    // Macro regime
    $r = $conn->query("SELECT * FROM lm_intelligence
        WHERE metric_name='macro_regime'
        ORDER BY updated_at DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $regimes['MACRO'] = array(
            'score' => floatval($row['metric_value']),
            'label' => $row['metric_label'],
            'updated' => $row['updated_at']
        );
        $r->free();
    }

    // VIX term structure
    $r = $conn->query("SELECT * FROM lm_intelligence
        WHERE metric_name='vix_term_structure'
        ORDER BY updated_at DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $regimes['VIX'] = array(
            'structure' => $row['metric_label'],
            'm1_m2_ratio' => floatval($row['metric_value']),
            'updated' => $row['updated_at']
        );
        $r->free();
    }

    echo json_encode(array('ok' => true, 'regimes' => $regimes));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: kelly — Per-algorithm Kelly fractions
// ════════════════════════════════════════════════════════════════════════
if ($action === 'kelly') {
    $algo = isset($_GET['algorithm']) ? $conn->real_escape_string($_GET['algorithm']) : '';

    $where = '';
    if ($algo) $where = " WHERE algorithm_name='$algo'";

    $r = $conn->query("SELECT * FROM lm_kelly_fractions $where ORDER BY algorithm_name");
    $results = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $results[] = $row;
        }
        $r->free();
    }

    echo json_encode(array('ok' => true, 'kelly_fractions' => $results));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: algo_health — Alpha decay & online learning weights
// ════════════════════════════════════════════════════════════════════════
if ($action === 'algo_health') {
    $r = $conn->query("SELECT * FROM lm_algo_health ORDER BY online_weight DESC");
    $results = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $results[] = $row;
        }
        $r->free();
    }

    echo json_encode(array('ok' => true, 'algo_health' => $results));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: dashboard — Full intelligence dashboard
// ════════════════════════════════════════════════════════════════════════
if ($action === 'dashboard') {
    $dashboard = array();

    // All intelligence metrics
    $r = $conn->query("SELECT * FROM lm_intelligence ORDER BY metric_name, asset_class");
    $metrics = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $metrics[] = $row;
        }
        $r->free();
    }
    $dashboard['intelligence'] = $metrics;

    // Kelly fractions
    $r = $conn->query("SELECT * FROM lm_kelly_fractions ORDER BY half_kelly DESC");
    $kelly = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $kelly[] = $row;
        }
        $r->free();
    }
    $dashboard['kelly_fractions'] = $kelly;

    // Algo health
    $r = $conn->query("SELECT * FROM lm_algo_health ORDER BY online_weight DESC");
    $health = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $health[] = $row;
        }
        $r->free();
    }
    $dashboard['algo_health'] = $health;

    // Meta-label stats (last 24h)
    $r = $conn->query("SELECT algorithm_name,
        COUNT(*) as total,
        SUM(CASE WHEN prediction > 0.5 THEN 1 ELSE 0 END) as approved,
        AVG(confidence) as avg_confidence
        FROM lm_meta_labels
        WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
        GROUP BY algorithm_name");
    $meta_stats = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $meta_stats[] = $row;
        }
        $r->free();
    }
    $dashboard['meta_label_stats'] = $meta_stats;

    echo json_encode(array('ok' => true, 'dashboard' => $dashboard));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: compute_kelly — Calculate Kelly fractions from trade history
// ════════════════════════════════════════════════════════════════════════
if ($action === 'compute_kelly') {
    if (!_wci_check_key()) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }

    // Get per-algorithm win/loss stats from closed trades
    $r = $conn->query("SELECT algorithm_name, asset_class,
        COUNT(*) as total_trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        AVG(CASE WHEN realized_pnl_usd > 0 THEN realized_pct ELSE NULL END) as avg_win_pct,
        AVG(CASE WHEN realized_pnl_usd <= 0 THEN ABS(realized_pct) ELSE NULL END) as avg_loss_pct
        FROM lm_trades
        WHERE status = 'closed' AND algorithm_name != ''
        GROUP BY algorithm_name, asset_class
        HAVING total_trades >= 5");

    $kelly_data = array();
    $now = _wci_now();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $total = intval($row['total_trades']);
            $wins  = intval($row['wins']);
            $wr    = ($total > 0) ? $wins / $total : 0;
            $aw    = floatval($row['avg_win_pct']);
            $al    = floatval($row['avg_loss_pct']);

            // Kelly formula: f* = (p*b - q) / b where b = avg_win/avg_loss
            $fk = 0;
            $hk = 0;
            if ($al > 0 && $aw > 0) {
                $b = $aw / $al;
                $fk = ($wr * $b - (1 - $wr)) / $b;
                $fk = max(0, min($fk, 0.25)); // Cap at 25%
                $hk = $fk * 0.5;              // Half-Kelly
                $hk = max(0, min($hk, 0.15)); // Cap half-Kelly at 15%
            }

            $algo  = $conn->real_escape_string($row['algorithm_name']);
            $asset = $conn->real_escape_string($row['asset_class']);

            $conn->query("DELETE FROM lm_kelly_fractions
                WHERE algorithm_name='$algo' AND asset_class='$asset'");
            $conn->query("INSERT INTO lm_kelly_fractions
                (algorithm_name, asset_class, win_rate, avg_win_pct, avg_loss_pct,
                 full_kelly, half_kelly, sample_size, updated_at)
                VALUES ('$algo', '$asset', $wr, $aw, $al, $fk, $hk, $total, '$now')");

            $kelly_data[] = array(
                'algorithm' => $row['algorithm_name'],
                'asset' => $row['asset_class'],
                'win_rate' => round($wr, 4),
                'avg_win' => round($aw, 4),
                'avg_loss' => round($al, 4),
                'full_kelly' => round($fk, 6),
                'half_kelly' => round($hk, 6),
                'sample_size' => $total
            );
        }
        $r->free();
    }

    echo json_encode(array('ok' => true, 'computed' => count($kelly_data), 'kelly_data' => $kelly_data));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  ACTION: compute_algo_health — Calculate alpha decay + online weights
// ════════════════════════════════════════════════════════════════════════
if ($action === 'compute_algo_health') {
    if (!_wci_check_key()) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }

    $now = _wci_now();
    $health = array();

    // Get 30-day rolling stats per algorithm
    $r = $conn->query("SELECT algorithm_name, asset_class,
        COUNT(*) as trades_30d,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins_30d,
        SUM(realized_pct) as total_pnl_pct,
        AVG(realized_pct) as avg_pnl_pct,
        STDDEV(realized_pct) as stddev_pnl
        FROM lm_trades
        WHERE status = 'closed'
        AND exit_time > DATE_SUB(NOW(), INTERVAL 30 DAY)
        AND algorithm_name != ''
        GROUP BY algorithm_name, asset_class");

    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $algo   = $row['algorithm_name'];
            $asset  = $row['asset_class'];
            $trades = intval($row['trades_30d']);
            $wins   = intval($row['wins_30d']);
            $wr     = ($trades > 0) ? $wins / $trades : 0;
            $pnl    = floatval($row['total_pnl_pct']);
            $avg    = floatval($row['avg_pnl_pct']);
            $std    = floatval($row['stddev_pnl']);

            // Sharpe ratio (annualized from 30-day)
            $sharpe = ($std > 0) ? ($avg / $std) * sqrt(252) : 0;

            // Online learning weight: exponential decay
            // Good performance → weight stays high, bad → decays
            $weight = 1.0;
            if ($trades >= 5) {
                // Base weight on win rate and Sharpe
                $weight = 0.5 + ($wr * 0.3) + (min(1, max(0, $sharpe / 2)) * 0.2);
                $weight = max(0.1, min(1.5, $weight)); // Bound 0.1 to 1.5
            }

            // Consecutive losses
            $safe_algo = $conn->real_escape_string($algo);
            $safe_asset = $conn->real_escape_string($asset);
            $lr = $conn->query("SELECT realized_pnl_usd FROM lm_trades
                WHERE algorithm_name='$safe_algo' AND asset_class='$safe_asset' AND status='closed'
                ORDER BY exit_time DESC LIMIT 10");
            $consec = 0;
            if ($lr) {
                while ($lrow = $lr->fetch_assoc()) {
                    if (floatval($lrow['realized_pnl_usd']) <= 0) {
                        $consec++;
                    } else {
                        break;
                    }
                }
                $lr->free();
            }

            // Decay status
            $status = 'healthy';
            if ($sharpe < -0.5 || $consec >= 5) {
                $status = 'decayed';
                $weight *= 0.5; // Penalize decayed algos
            } elseif ($sharpe < 0 || $consec >= 3) {
                $status = 'warning';
                $weight *= 0.75;
            } elseif ($sharpe > 1.0 && $wr > 0.5) {
                $status = 'strong';
                $weight = min(1.5, $weight * 1.1);
            }

            // Store
            $conn->query("DELETE FROM lm_algo_health
                WHERE algorithm_name='$safe_algo' AND asset_class='$safe_asset'");
            $conn->query("INSERT INTO lm_algo_health
                (algorithm_name, asset_class, rolling_sharpe_30d, rolling_win_rate_30d,
                 rolling_pnl_30d, online_weight, decay_status, trades_30d,
                 consecutive_losses, updated_at)
                VALUES ('$safe_algo', '$safe_asset',
                    " . round($sharpe, 4) . ", " . round($wr, 4) . ",
                    " . round($pnl, 4) . ", " . round($weight, 6) . ",
                    '$status', $trades, $consec, '$now')");

            $health[] = array(
                'algorithm' => $algo,
                'asset' => $asset,
                'sharpe_30d' => round($sharpe, 4),
                'win_rate_30d' => round($wr, 4),
                'pnl_30d' => round($pnl, 4),
                'weight' => round($weight, 6),
                'status' => $status,
                'trades' => $trades,
                'consec_losses' => $consec
            );
        }
        $r->free();
    }

    echo json_encode(array('ok' => true, 'computed' => count($health), 'health' => $health));
    exit;
}

// ════════════════════════════════════════════════════════════════════════
//  Default: list available actions
// ════════════════════════════════════════════════════════════════════════
echo json_encode(array(
    'ok' => true,
    'api' => 'World-Class Intelligence',
    'actions' => array(
        'store' => 'Store a metric (POST, admin key)',
        'store_batch' => 'Store multiple metrics (POST, admin key)',
        'store_kelly' => 'Store Kelly fractions (POST, admin key)',
        'store_algo_health' => 'Store algo health data (POST, admin key)',
        'get' => 'Get a metric (GET, public)',
        'regime' => 'Current regime state (GET, public)',
        'kelly' => 'Kelly fractions per algorithm (GET, public)',
        'algo_health' => 'Alpha decay & online learning (GET, public)',
        'compute_kelly' => 'Calculate Kelly from trade history (GET, admin key)',
        'compute_algo_health' => 'Calculate alpha decay from trades (GET, admin key)',
        'dashboard' => 'Full intelligence dashboard (GET, public)'
    )
));
