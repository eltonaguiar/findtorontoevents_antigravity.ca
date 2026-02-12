<?php
/**
 * Regime Detection API — Bridge between Python intelligence and live-monitor.
 * PHP 5.2 compatible — no short arrays, no http_response_code().
 *
 * Actions:
 *   ingest_regime   — POST regime data from Python regime_detector.py (admin key)
 *   get_regime      — GET current regime state (public)
 *   regime_history  — GET historical regime data (public)
 *   strategy_toggles — GET active strategy weights (public)
 *   update_position_sizing — POST position sizing from Python (admin key)
 *   get_position_sizing   — GET current sizing recommendations (public)
 *   update_meta_labeler   — POST meta-labeler training results (admin key)
 *   get_meta_labeler      — GET meta-labeler status (public)
 *   meta_label_training_data — GET training data for meta-labeler (admin key)
 */

require_once dirname(__FILE__) . '/db_connect.php';

$ADMIN_KEY = 'livetrader2026';

// ─── Auto-create tables ─────────────────────────────────────────────
$conn->query("
CREATE TABLE IF NOT EXISTS lm_market_regime (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATETIME NOT NULL,
    hmm_regime VARCHAR(20) NOT NULL DEFAULT 'sideways',
    hmm_confidence DECIMAL(6,4) NOT NULL DEFAULT 0.5,
    hmm_persistence DECIMAL(6,4) NOT NULL DEFAULT 0.5,
    hurst DECIMAL(6,4) NOT NULL DEFAULT 0.5,
    hurst_regime VARCHAR(20) NOT NULL DEFAULT 'random',
    ewma_vol DECIMAL(10,8) NOT NULL DEFAULT 0,
    vol_annualized DECIMAL(8,4) NOT NULL DEFAULT 0,
    composite_score DECIMAL(6,2) NOT NULL DEFAULT 50,
    strategy_toggles TEXT,
    vix_level DECIMAL(8,2),
    vix_regime VARCHAR(20) NOT NULL DEFAULT 'normal',
    yield_curve VARCHAR(20) NOT NULL DEFAULT 'normal',
    yield_spread DECIMAL(8,4),
    macro_score DECIMAL(6,2) NOT NULL DEFAULT 50,
    ticker_regimes TEXT,
    created_at DATETIME NOT NULL,
    KEY idx_date (date),
    KEY idx_hmm (hmm_regime)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

$conn->query("
CREATE TABLE IF NOT EXISTS lm_position_sizing (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATETIME NOT NULL,
    algorithm_name VARCHAR(100) NOT NULL,
    kelly_base DECIMAL(8,4) NOT NULL DEFAULT 0,
    vol_scalar DECIMAL(8,2) NOT NULL DEFAULT 1,
    regime_modifier DECIMAL(8,2) NOT NULL DEFAULT 1,
    decay_weight DECIMAL(8,2) NOT NULL DEFAULT 1,
    final_size_pct DECIMAL(8,2) NOT NULL DEFAULT 5,
    dollar_amount DECIMAL(12,2) NOT NULL DEFAULT 500,
    algo_sharpe_30d DECIMAL(8,3) NOT NULL DEFAULT 0,
    is_decaying TINYINT NOT NULL DEFAULT 0,
    regime_composite DECIMAL(6,2) NOT NULL DEFAULT 50,
    created_at DATETIME NOT NULL,
    KEY idx_date (date),
    KEY idx_algo (algorithm_name)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");

$conn->query("
CREATE TABLE IF NOT EXISTS lm_meta_labeler (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trained_at DATETIME NOT NULL,
    training_samples INT NOT NULL DEFAULT 0,
    positive_rate DECIMAL(6,4) NOT NULL DEFAULT 0,
    avg_precision DECIMAL(6,4) NOT NULL DEFAULT 0,
    avg_recall DECIMAL(6,4) NOT NULL DEFAULT 0,
    avg_f1 DECIMAL(6,4) NOT NULL DEFAULT 0,
    cv_results TEXT,
    top_features TEXT,
    created_at DATETIME NOT NULL,
    KEY idx_trained (trained_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8
");


// ─── Route ──────────────────────────────────────────────────────────
$action = isset($_GET['action']) ? $_GET['action'] : '';
$key    = isset($_GET['key'])    ? $_GET['key']    : '';

switch ($action) {

// ─── INGEST REGIME (admin, POST) ────────────────────────────────────
case 'ingest_regime':
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Forbidden'));
        exit;
    }

    $body = json_decode(file_get_contents('php://input'), true);
    if (!$body || !isset($body['market'])) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing market data'));
        exit;
    }

    $m = $body['market'];
    $mac = isset($body['macro']) ? $body['macro'] : array();
    $tickers = isset($body['tickers']) ? $body['tickers'] : array();

    $hmm_regime      = $conn->real_escape_string(isset($m['hmm_regime']) ? $m['hmm_regime'] : 'sideways');
    $hmm_confidence  = floatval(isset($m['hmm_confidence']) ? $m['hmm_confidence'] : 0.5);
    $hmm_persistence = floatval(isset($m['hmm_persistence']) ? $m['hmm_persistence'] : 0.5);
    $hurst           = floatval(isset($m['hurst']) ? $m['hurst'] : 0.5);
    $hurst_regime    = $conn->real_escape_string(isset($m['hurst_regime']) ? $m['hurst_regime'] : 'random');
    $ewma_vol        = floatval(isset($m['ewma_vol']) ? $m['ewma_vol'] : 0);
    $vol_ann         = floatval(isset($m['vol_annualized']) ? $m['vol_annualized'] : 0);
    $composite       = floatval(isset($m['composite_score']) ? $m['composite_score'] : 50);
    $toggles_json    = $conn->real_escape_string(json_encode(isset($m['strategy_toggles']) ? $m['strategy_toggles'] : array()));

    $vix_level    = isset($mac['vix_level']) ? floatval($mac['vix_level']) : 'NULL';
    $vix_regime   = $conn->real_escape_string(isset($mac['vix_regime']) ? $mac['vix_regime'] : 'unknown');
    $yield_curve  = $conn->real_escape_string(isset($mac['yield_curve']) ? $mac['yield_curve'] : 'unknown');
    $yield_spread = isset($mac['yield_spread']) ? floatval($mac['yield_spread']) : 'NULL';
    $macro_score  = floatval(isset($mac['macro_score']) ? $mac['macro_score'] : 50);
    $tickers_json = $conn->real_escape_string(json_encode($tickers));

    $vix_val    = ($vix_level === 'NULL') ? 'NULL' : $vix_level;
    $spread_val = ($yield_spread === 'NULL') ? 'NULL' : $yield_spread;

    $sql = "INSERT INTO lm_market_regime
        (date, hmm_regime, hmm_confidence, hmm_persistence, hurst, hurst_regime,
         ewma_vol, vol_annualized, composite_score, strategy_toggles,
         vix_level, vix_regime, yield_curve, yield_spread, macro_score,
         ticker_regimes, created_at)
        VALUES
        (NOW(), '$hmm_regime', $hmm_confidence, $hmm_persistence, $hurst, '$hurst_regime',
         $ewma_vol, $vol_ann, $composite, '$toggles_json',
         $vix_val, '$vix_regime', '$yield_curve', $spread_val, $macro_score,
         '$tickers_json', NOW())";

    if ($conn->query($sql)) {
        echo json_encode(array(
            'ok' => true,
            'regime' => $hmm_regime,
            'composite' => $composite,
            'hurst' => $hurst,
            'hurst_regime' => $hurst_regime
        ));
    } else {
        echo json_encode(array('ok' => false, 'error' => $conn->error));
    }
    break;


// ─── GET REGIME (public) ────────────────────────────────────────────
case 'get_regime':
    $r = $conn->query("SELECT * FROM lm_market_regime
        WHERE hmm_regime NOT IN ('bundle_update','worldquant_update','validation_update')
        ORDER BY date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $toggles = json_decode($row['strategy_toggles'], true);
        $tickers = json_decode($row['ticker_regimes'], true);

        echo json_encode(array(
            'ok' => true,
            'regime' => array(
                'market' => array(
                    'hmm_regime'       => $row['hmm_regime'],
                    'hmm_confidence'   => floatval($row['hmm_confidence']),
                    'hmm_persistence'  => floatval($row['hmm_persistence']),
                    'hurst'            => floatval($row['hurst']),
                    'hurst_regime'     => $row['hurst_regime'],
                    'ewma_vol'         => floatval($row['ewma_vol']),
                    'vol_annualized'   => floatval($row['vol_annualized']),
                    'composite_score'  => floatval($row['composite_score']),
                    'strategy_toggles' => $toggles ? $toggles : array()
                ),
                'macro' => array(
                    'vix_level'    => $row['vix_level'] ? floatval($row['vix_level']) : null,
                    'vix_regime'   => $row['vix_regime'],
                    'yield_curve'  => $row['yield_curve'],
                    'yield_spread' => $row['yield_spread'] ? floatval($row['yield_spread']) : null,
                    'macro_score'  => floatval($row['macro_score'])
                ),
                'tickers' => $tickers ? $tickers : array(),
                'updated_at' => $row['date']
            )
        ));
    } else {
        echo json_encode(array(
            'ok' => true,
            'regime' => null,
            'message' => 'No regime data yet'
        ));
    }
    break;


// ─── REGIME HISTORY (public) ────────────────────────────────────────
case 'regime_history':
    $days = isset($_GET['days']) ? intval($_GET['days']) : 30;
    $days = max(1, min($days, 365));

    $r = $conn->query("SELECT date, hmm_regime, hmm_confidence, hurst, hurst_regime,
                        composite_score, vix_level, vix_regime, macro_score
                        FROM lm_market_regime
                        WHERE date >= DATE_SUB(NOW(), INTERVAL $days DAY)
                        ORDER BY date ASC");

    $history = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $history[] = array(
                'date'            => $row['date'],
                'hmm_regime'      => $row['hmm_regime'],
                'hmm_confidence'  => floatval($row['hmm_confidence']),
                'hurst'           => floatval($row['hurst']),
                'hurst_regime'    => $row['hurst_regime'],
                'composite_score' => floatval($row['composite_score']),
                'vix_level'       => $row['vix_level'] ? floatval($row['vix_level']) : null,
                'vix_regime'      => $row['vix_regime'],
                'macro_score'     => floatval($row['macro_score'])
            );
        }
    }

    echo json_encode(array('ok' => true, 'history' => $history, 'count' => count($history)));
    break;


// ─── STRATEGY TOGGLES (public) ─────────────────────────────────────
case 'strategy_toggles':
    $r = $conn->query("SELECT strategy_toggles, composite_score, hmm_regime, hurst_regime
                        FROM lm_market_regime ORDER BY date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $toggles = json_decode($row['strategy_toggles'], true);
        echo json_encode(array(
            'ok' => true,
            'toggles' => $toggles ? $toggles : array(),
            'composite_score' => floatval($row['composite_score']),
            'hmm_regime' => $row['hmm_regime'],
            'hurst_regime' => $row['hurst_regime']
        ));
    } else {
        echo json_encode(array('ok' => true, 'toggles' => array(), 'message' => 'No data'));
    }
    break;


// ─── UPDATE POSITION SIZING (admin, POST) ───────────────────────────
case 'update_position_sizing':
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Forbidden'));
        exit;
    }

    $body = json_decode(file_get_contents('php://input'), true);
    if (!$body || !isset($body['sizing'])) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing sizing data'));
        exit;
    }

    $regime_composite = floatval(isset($body['regime_composite']) ? $body['regime_composite'] : 50);
    $inserted = 0;

    foreach ($body['sizing'] as $s) {
        $algo   = $conn->real_escape_string(isset($s['algorithm_name']) ? $s['algorithm_name'] : 'Unknown');
        $kelly  = floatval(isset($s['kelly_base']) ? $s['kelly_base'] : 0);
        $vol_s  = floatval(isset($s['vol_scalar']) ? $s['vol_scalar'] : 1);
        $reg_m  = floatval(isset($s['regime_modifier']) ? $s['regime_modifier'] : 1);
        $decay  = floatval(isset($s['decay_weight']) ? $s['decay_weight'] : 1);
        $final  = floatval(isset($s['final_size_pct']) ? $s['final_size_pct'] : 5);
        $dollar = floatval(isset($s['dollar_amount']) ? $s['dollar_amount'] : 500);
        $sharpe = floatval(isset($s['algo_sharpe_30d']) ? $s['algo_sharpe_30d'] : 0);
        $decay_flag = (isset($s['is_decaying']) && $s['is_decaying']) ? 1 : 0;

        $sql = "INSERT INTO lm_position_sizing
            (date, algorithm_name, kelly_base, vol_scalar, regime_modifier,
             decay_weight, final_size_pct, dollar_amount, algo_sharpe_30d,
             is_decaying, regime_composite, created_at)
            VALUES
            (NOW(), '$algo', $kelly, $vol_s, $reg_m, $decay, $final, $dollar,
             $sharpe, $decay_flag, $regime_composite, NOW())";

        if ($conn->query($sql)) {
            $inserted++;
        }
    }

    echo json_encode(array('ok' => true, 'inserted' => $inserted));
    break;


// ─── GET POSITION SIZING (public) ──────────────────────────────────
case 'get_position_sizing':
    // Get latest sizing for each algorithm
    $r = $conn->query("SELECT ps.* FROM lm_position_sizing ps
        INNER JOIN (
            SELECT algorithm_name, MAX(id) as max_id
            FROM lm_position_sizing
            GROUP BY algorithm_name
        ) latest ON ps.id = latest.max_id
        ORDER BY ps.final_size_pct DESC");

    $sizing = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $sizing[] = array(
                'algorithm_name'   => $row['algorithm_name'],
                'kelly_base'       => floatval($row['kelly_base']),
                'vol_scalar'       => floatval($row['vol_scalar']),
                'regime_modifier'  => floatval($row['regime_modifier']),
                'decay_weight'     => floatval($row['decay_weight']),
                'final_size_pct'   => floatval($row['final_size_pct']),
                'dollar_amount'    => floatval($row['dollar_amount']),
                'algo_sharpe_30d'  => floatval($row['algo_sharpe_30d']),
                'is_decaying'      => intval($row['is_decaying']),
                'regime_composite' => floatval($row['regime_composite']),
                'date'             => $row['date']
            );
        }
    }

    echo json_encode(array('ok' => true, 'sizing' => $sizing, 'count' => count($sizing)));
    break;


// ─── UPDATE META-LABELER (admin, POST) ──────────────────────────────
case 'update_meta_labeler':
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Forbidden'));
        exit;
    }

    $body = json_decode(file_get_contents('php://input'), true);
    if (!$body) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing data'));
        exit;
    }

    $samples   = intval(isset($body['training_samples']) ? $body['training_samples'] : 0);
    $pos_rate  = floatval(isset($body['positive_rate']) ? $body['positive_rate'] : 0);
    $precision = floatval(isset($body['avg_precision']) ? $body['avg_precision'] : 0);
    $recall    = floatval(isset($body['avg_recall']) ? $body['avg_recall'] : 0);
    $f1        = floatval(isset($body['avg_f1']) ? $body['avg_f1'] : 0);
    $cv_json   = $conn->real_escape_string(json_encode(isset($body['cv_results']) ? $body['cv_results'] : array()));
    $feat_json = $conn->real_escape_string(json_encode(isset($body['top_features']) ? $body['top_features'] : array()));

    $sql = "INSERT INTO lm_meta_labeler
        (trained_at, training_samples, positive_rate, avg_precision, avg_recall,
         avg_f1, cv_results, top_features, created_at)
        VALUES (NOW(), $samples, $pos_rate, $precision, $recall, $f1,
                '$cv_json', '$feat_json', NOW())";

    if ($conn->query($sql)) {
        echo json_encode(array('ok' => true, 'id' => $conn->insert_id));
    } else {
        echo json_encode(array('ok' => false, 'error' => $conn->error));
    }
    break;


// ─── GET META-LABELER STATUS (public) ───────────────────────────────
case 'get_meta_labeler':
    $r = $conn->query("SELECT * FROM lm_meta_labeler ORDER BY trained_at DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        echo json_encode(array(
            'ok' => true,
            'meta_labeler' => array(
                'trained_at'       => $row['trained_at'],
                'training_samples' => intval($row['training_samples']),
                'positive_rate'    => floatval($row['positive_rate']),
                'avg_precision'    => floatval($row['avg_precision']),
                'avg_recall'       => floatval($row['avg_recall']),
                'avg_f1'           => floatval($row['avg_f1']),
                'cv_results'       => json_decode($row['cv_results'], true),
                'top_features'     => json_decode($row['top_features'], true)
            )
        ));
    } else {
        echo json_encode(array('ok' => true, 'meta_labeler' => null, 'message' => 'Not trained yet'));
    }
    break;


// ─── META-LABEL TRAINING DATA (admin) ───────────────────────────────
case 'meta_label_training_data':
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Forbidden'));
        exit;
    }

    // Join signals with trade outcomes + regime data
    $sql = "SELECT
        t.symbol, t.asset_class, t.algorithm_name, t.direction,
        t.entry_time as signal_time, t.entry_price,
        t.target_tp_pct, t.target_sl_pct, t.max_hold_hours,
        t.exit_reason, t.realized_pct, t.hold_hours,
        t.position_value_usd,
        r.hmm_regime, r.hurst, r.composite_score, r.ewma_vol,
        r.vix_level, r.vix_regime
    FROM lm_trades t
    LEFT JOIN lm_market_regime r ON DATE(t.entry_time) = DATE(r.date)
    WHERE t.status = 'closed'
    AND t.entry_time > DATE_SUB(NOW(), INTERVAL 6 MONTH)
    ORDER BY t.entry_time ASC
    LIMIT 5000";

    $r = $conn->query($sql);
    $signals = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $signals[] = $row;
        }
    }

    echo json_encode(array('ok' => true, 'signals' => $signals, 'count' => count($signals)));
    break;


// ─── ALGO STATS (public) ───────────────────────────────────────────
case 'algo_stats':
    $sql = "SELECT
        algorithm_name,
        COUNT(*) as total_trades,
        SUM(CASE WHEN exit_reason = 'tp_hit' THEN 1 ELSE 0 END) as wins,
        ROUND(SUM(CASE WHEN exit_reason = 'tp_hit' THEN 1 ELSE 0 END) / COUNT(*) * 100, 1) as win_rate,
        ROUND(AVG(realized_pct), 2) as avg_pnl_pct,
        ROUND(MAX(realized_pct), 2) as best_trade_pct,
        ROUND(MIN(realized_pct), 2) as worst_trade_pct,
        ROUND(SUM(realized_pnl_usd), 2) as total_pnl_usd
    FROM lm_trades
    WHERE status = 'closed'
    AND entry_time > DATE_SUB(NOW(), INTERVAL 90 DAY)
    GROUP BY algorithm_name
    ORDER BY win_rate DESC";

    $r = $conn->query($sql);
    $algos = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $algos[] = $row;
        }
    }

    echo json_encode(array('ok' => true, 'algorithms' => $algos, 'count' => count($algos)));
    break;


// ─── INGEST WORLDQUANT (admin, POST) ────────────────────────────────
case 'ingest_worldquant':
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Forbidden'));
        exit;
    }

    $body = json_decode(file_get_contents('php://input'), true);
    if (!$body) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing data'));
        exit;
    }

    // Store as JSON blob in regime table (lightweight)
    $wq_json = $conn->real_escape_string(json_encode($body));
    $sql = "INSERT INTO lm_market_regime
        (date, hmm_regime, hmm_confidence, hmm_persistence, hurst, hurst_regime,
         ewma_vol, vol_annualized, composite_score, strategy_toggles,
         vix_level, vix_regime, yield_curve, yield_spread, macro_score,
         ticker_regimes, created_at)
        VALUES
        (NOW(), 'worldquant_update', 0, 0, 0, 'n/a',
         0, 0, 0, '$wq_json',
         NULL, 'n/a', 'n/a', NULL, 0,
         '$wq_json', NOW())";

    if ($conn->query($sql)) {
        echo json_encode(array('ok' => true, 'stored' => 'worldquant_alphas'));
    } else {
        echo json_encode(array('ok' => false, 'error' => $conn->error));
    }
    break;


// ─── UPDATE BUNDLES (admin, POST) ───────────────────────────────────
case 'update_bundles':
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Forbidden'));
        exit;
    }

    $body = json_decode(file_get_contents('php://input'), true);
    if (!$body) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing data'));
        exit;
    }

    $bundle_json = $conn->real_escape_string(json_encode($body));
    $sql = "INSERT INTO lm_market_regime
        (date, hmm_regime, hmm_confidence, hmm_persistence, hurst, hurst_regime,
         ewma_vol, vol_annualized, composite_score, strategy_toggles,
         vix_level, vix_regime, yield_curve, yield_spread, macro_score,
         ticker_regimes, created_at)
        VALUES
        (NOW(), 'bundle_update', 0, 0, 0, 'n/a',
         0, 0, 0, '$bundle_json',
         NULL, 'n/a', 'n/a', NULL, 0,
         '$bundle_json', NOW())";

    if ($conn->query($sql)) {
        echo json_encode(array('ok' => true, 'stored' => 'signal_bundles'));
    } else {
        echo json_encode(array('ok' => false, 'error' => $conn->error));
    }
    break;


// ─── UPDATE VALIDATION (admin, POST) ────────────────────────────────
case 'update_validation':
    if ($key !== $ADMIN_KEY) {
        header('HTTP/1.0 403 Forbidden');
        echo json_encode(array('ok' => false, 'error' => 'Forbidden'));
        exit;
    }

    $body = json_decode(file_get_contents('php://input'), true);
    if (!$body) {
        header('HTTP/1.0 400 Bad Request');
        echo json_encode(array('ok' => false, 'error' => 'Missing data'));
        exit;
    }

    $val_json = $conn->real_escape_string(json_encode($body));
    $sql = "INSERT INTO lm_market_regime
        (date, hmm_regime, hmm_confidence, hmm_persistence, hurst, hurst_regime,
         ewma_vol, vol_annualized, composite_score, strategy_toggles,
         vix_level, vix_regime, yield_curve, yield_spread, macro_score,
         ticker_regimes, created_at)
        VALUES
        (NOW(), 'validation_update', 0, 0, 0, 'n/a',
         0, 0, 0, '$val_json',
         NULL, 'n/a', 'n/a', NULL, 0,
         '$val_json', NOW())";

    if ($conn->query($sql)) {
        echo json_encode(array('ok' => true, 'stored' => 'validation_results'));
    } else {
        echo json_encode(array('ok' => false, 'error' => $conn->error));
    }
    break;


// ─── GET VALIDATION (public) ────────────────────────────────────────
case 'get_validation':
    $r = $conn->query("SELECT ticker_regimes FROM lm_market_regime
                        WHERE hmm_regime = 'validation_update'
                        ORDER BY date DESC LIMIT 1");
    if ($r && $r->num_rows > 0) {
        $row = $r->fetch_assoc();
        $val = json_decode($row['ticker_regimes'], true);
        echo json_encode(array('ok' => true, 'validation' => $val));
    } else {
        echo json_encode(array('ok' => true, 'validation' => null, 'message' => 'No validation data'));
    }
    break;


// ─── DEFAULT ────────────────────────────────────────────────────────
default:
    echo json_encode(array(
        'ok' => true,
        'api' => 'regime',
        'version' => '2.0',
        'actions' => array(
            'ingest_regime (POST, admin)',
            'get_regime',
            'regime_history?days=30',
            'strategy_toggles',
            'update_position_sizing (POST, admin)',
            'get_position_sizing',
            'update_meta_labeler (POST, admin)',
            'get_meta_labeler',
            'meta_label_training_data (admin)',
            'algo_stats',
            'ingest_worldquant (POST, admin)',
            'update_bundles (POST, admin)',
            'update_validation (POST, admin)',
            'get_validation'
        )
    ));
    break;
}
?>
