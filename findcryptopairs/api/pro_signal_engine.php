<?php
/**
 * Pro Signal Engine v1.0
 * ======================
 * 100 strategies backtested on volatile Kraken pairs.
 * Tournament elimination → survivors form a confluence scanner.
 * When multiple winning strategies agree → PRO SIGNAL.
 *
 * Actions:
 *   fetch_data    – Cache OHLCV from Kraken for top volatile pairs
 *   run_batch     – Run a batch of strategies (batch=1..10, 10 strats each)
 *   tournament    – Analyze all results, rank, eliminate losers
 *   live_scan     – Run winning strategies on current data → pro signals
 *   signals       – Get current active pro signals
 *   audit         – Full audit trail: strategy performance, elimination reasons
 *   status        – System overview (what's cached, what's been run)
 *   pairs         – List configured volatile pairs
 *
 * PHP 5.2 compatible. No short ternary, no ??, no [], no closures.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

error_reporting(0);
ini_set('display_errors', '0');
set_time_limit(120);

// ═══════════════════════════════════════════════════════════════════
//  DATABASE CONNECTION
// ═══════════════════════════════════════════════════════════════════
$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

// ═══════════════════════════════════════════════════════════════════
//  TABLE SETUP
// ═══════════════════════════════════════════════════════════════════
$conn->query("CREATE TABLE IF NOT EXISTS psi_ohlcv_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(30) NOT NULL,
    tf INT NOT NULL DEFAULT 60,
    t INT NOT NULL,
    o DECIMAL(20,10), h DECIMAL(20,10), l DECIMAL(20,10), c DECIMAL(20,10),
    vw DECIMAL(20,10), v DECIMAL(20,6), tc INT,
    fetched_at DATETIME,
    UNIQUE KEY uniq_c (pair, tf, t),
    INDEX idx_pt (pair, tf)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS psi_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sid INT NOT NULL,
    sname VARCHAR(60) NOT NULL,
    scat VARCHAR(30) NOT NULL,
    pair VARCHAR(30) NOT NULL,
    tf INT NOT NULL DEFAULT 240,
    trades INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    win_rate DECIMAL(6,2) DEFAULT 0,
    total_ret DECIMAL(10,4) DEFAULT 0,
    profit_factor DECIMAL(8,4) DEFAULT 0,
    sharpe DECIMAL(8,4) DEFAULT 0,
    max_dd DECIMAL(8,4) DEFAULT 0,
    avg_win DECIMAL(8,4) DEFAULT 0,
    avg_loss DECIMAL(8,4) DEFAULT 0,
    best_trade DECIMAL(8,4) DEFAULT 0,
    worst_trade DECIMAL(8,4) DEFAULT 0,
    avg_bars INT DEFAULT 0,
    trade_log TEXT,
    computed_at DATETIME,
    INDEX idx_sid (sid),
    INDEX idx_pair (pair),
    INDEX idx_wr (win_rate),
    INDEX idx_pf (profit_factor)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS psi_tournament (
    id INT AUTO_INCREMENT PRIMARY KEY,
    tid VARCHAR(50) NOT NULL,
    rnd INT NOT NULL,
    sid INT NOT NULL,
    sname VARCHAR(60) NOT NULL,
    action VARCHAR(20) NOT NULL,
    reason TEXT,
    score DECIMAL(10,4) DEFAULT 0,
    rnk INT DEFAULT 0,
    created_at DATETIME,
    INDEX idx_tid (tid),
    INDEX idx_rnd (rnd)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS psi_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sig_type VARCHAR(20) NOT NULL DEFAULT 'PRO',
    pair VARCHAR(30) NOT NULL,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    entry_price DECIMAL(20,10) NOT NULL,
    tp_price DECIMAL(20,10) NOT NULL,
    sl_price DECIMAL(20,10) NOT NULL,
    tp_pct DECIMAL(8,4) NOT NULL,
    sl_pct DECIMAL(8,4) NOT NULL,
    confidence INT NOT NULL DEFAULT 0,
    confluence INT NOT NULL DEFAULT 0,
    strats_agreed TEXT,
    reasoning TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    current_price DECIMAL(20,10) DEFAULT NULL,
    pnl_pct DECIMAL(8,4) DEFAULT NULL,
    peak_pnl DECIMAL(8,4) DEFAULT NULL,
    trough_pnl DECIMAL(8,4) DEFAULT NULL,
    exit_price DECIMAL(20,10) DEFAULT NULL,
    exit_reason VARCHAR(50) DEFAULT NULL,
    checks INT DEFAULT 0,
    created_at DATETIME NOT NULL,
    resolved_at DATETIME DEFAULT NULL,
    INDEX idx_status (status),
    INDEX idx_pair (pair),
    INDEX idx_conf (confidence)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ═══════════════════════════════════════════════════════════════════
//  TOP VOLATILE PAIRS (from our scan)
// ═══════════════════════════════════════════════════════════════════
$TOP_PAIRS = array(
    'SOLUSD', 'XETHZUSD', 'XXBTZUSD', 'SUIUSD', 'XXRPZUSD',
    'COMPUSD', 'AZTECUSD', 'SNXUSD', 'BCHUSD', 'LINKUSD',
    'ADAUSD', 'XDGUSD', 'FARTCOINUSD', 'MOODENGUSD', 'DASHUSD',
    'PEPEUSD', 'XZECZUSD', 'XXMRZUSD', 'XXLMZUSD', 'XLTCZUSD',
    'PENGUUSD', 'SPXUSD', 'UNIUSD', 'DOTUSD', 'AVAXUSD'
);

// ═══════════════════════════════════════════════════════════════════
//  ROUTING
// ═══════════════════════════════════════════════════════════════════
$action = isset($_GET['action']) ? $_GET['action'] : 'status';

switch ($action) {
    case 'fetch_data':
        action_fetch_data($conn);
        break;
    case 'run_batch':
        $batch = isset($_GET['batch']) ? intval($_GET['batch']) : 1;
        action_run_batch($conn, $batch);
        break;
    case 'tournament':
        action_tournament($conn);
        break;
    case 'live_scan':
        action_live_scan($conn);
        break;
    case 'signals':
        action_signals($conn);
        break;
    case 'monitor':
        action_monitor($conn);
        break;
    case 'audit':
        action_audit($conn);
        break;
    case 'status':
        action_status($conn);
        break;
    case 'pairs':
        action_pairs($conn);
        break;
    case 'run_all':
        action_run_all($conn);
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}
$conn->close();
exit;

// ═══════════════════════════════════════════════════════════════════
//  ACTION: FETCH DATA — Cache OHLCV from Kraken
// ═══════════════════════════════════════════════════════════════════
function action_fetch_data($conn)
{
    global $TOP_PAIRS;
    $start = microtime(true);
    $tf = isset($_GET['tf']) ? intval($_GET['tf']) : 240; // default 4h
    $results = array();
    $errors = array();

    // Fetch in parallel batches of 5
    $batches = array_chunk($TOP_PAIRS, 5);
    foreach ($batches as $batch) {
        $mh = curl_multi_init();
        $handles = array();
        foreach ($batch as $pair) {
            $url = 'https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=' . $tf;
            $ch = curl_init($url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 10);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_USERAGENT, 'ProSignalEngine/1.0');
            curl_multi_add_handle($mh, $ch);
            $handles[$pair] = $ch;
        }
        $running = null;
        do {
            curl_multi_exec($mh, $running);
            curl_multi_select($mh, 1);
        } while ($running > 0);

        foreach ($handles as $pair => $ch) {
            $resp = curl_multi_getcontent($ch);
            curl_multi_remove_handle($mh, $ch);
            curl_close($ch);
            if (!$resp) { $errors[] = $pair . ': no response'; continue; }
            $data = json_decode($resp, true);
            if (!$data || !isset($data['result'])) { $errors[] = $pair . ': bad json'; continue; }

            $candles = array();
            foreach ($data['result'] as $key => $val) {
                if ($key !== 'last') { $candles = $val; break; }
            }
            if (empty($candles)) { $errors[] = $pair . ': no candles'; continue; }

            // Upsert into cache
            $now = date('Y-m-d H:i:s');
            $inserted = 0;
            foreach ($candles as $c) {
                $sql = sprintf(
                    "INSERT INTO psi_ohlcv_cache (pair,tf,t,o,h,l,c,vw,v,tc,fetched_at) VALUES ('%s',%d,%d,'%.10f','%.10f','%.10f','%.10f','%.10f','%.6f',%d,'%s') ON DUPLICATE KEY UPDATE o=VALUES(o),h=VALUES(h),l=VALUES(l),c=VALUES(c),vw=VALUES(vw),v=VALUES(v),tc=VALUES(tc),fetched_at=VALUES(fetched_at)",
                    $conn->real_escape_string($pair), $tf,
                    intval($c[0]),
                    floatval($c[1]), floatval($c[2]), floatval($c[3]), floatval($c[4]),
                    floatval($c[5]), floatval($c[6]), intval($c[7]),
                    $now
                );
                if ($conn->query($sql)) $inserted++;
            }
            $results[] = array('pair' => $pair, 'candles' => count($candles), 'cached' => $inserted);
        }
        curl_multi_close($mh);
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'action' => 'fetch_data',
        'timeframe' => $tf,
        'pairs_fetched' => count($results),
        'results' => $results,
        'errors' => $errors,
        'elapsed_ms' => $elapsed
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  ACTION: RUN BATCH — Run 10 strategies on all cached pairs
// ═══════════════════════════════════════════════════════════════════
function action_run_batch($conn, $batch)
{
    global $TOP_PAIRS;
    $start = microtime(true);
    $tf = isset($_GET['tf']) ? intval($_GET['tf']) : 240;
    $pair_filter = isset($_GET['pair']) ? $_GET['pair'] : '';

    // Get strategy definitions for this batch (10 per batch)
    $all_strats = get_all_strategies();
    $offset = ($batch - 1) * 10;
    $batch_strats = array_slice($all_strats, $offset, 10);
    if (empty($batch_strats)) {
        echo json_encode(array('ok' => false, 'error' => 'No strategies in batch ' . $batch));
        return;
    }

    $pairs_to_run = ($pair_filter !== '') ? array($pair_filter) : $TOP_PAIRS;
    $results_summary = array();

    foreach ($pairs_to_run as $pair) {
        // Load OHLCV from cache
        $ohlcv = load_cached_ohlcv($conn, $pair, $tf);
        if (count($ohlcv) < 100) {
            $results_summary[] = array('pair' => $pair, 'error' => 'Insufficient data: ' . count($ohlcv) . ' candles');
            continue;
        }

        // Pre-compute all indicators
        $ind = precompute_indicators($ohlcv);

        // Run each strategy in the batch
        foreach ($batch_strats as $strat) {
            $bt = run_single_backtest($ohlcv, $ind, $strat);

            // Store results
            $trade_log_json = json_encode(array_slice($bt['trades'], -20));
            $sql = sprintf(
                "INSERT INTO psi_results (sid,sname,scat,pair,tf,trades,wins,losses,win_rate,total_ret,profit_factor,sharpe,max_dd,avg_win,avg_loss,best_trade,worst_trade,avg_bars,trade_log,computed_at) VALUES (%d,'%s','%s','%s',%d,%d,%d,%d,'%.2f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f',%d,'%s','%s')",
                $strat['id'],
                $conn->real_escape_string($strat['name']),
                $conn->real_escape_string($strat['cat']),
                $conn->real_escape_string($pair),
                $tf,
                $bt['total'], $bt['wins'], $bt['losses'],
                $bt['win_rate'], $bt['total_return'], $bt['profit_factor'],
                $bt['sharpe'], $bt['max_dd'],
                $bt['avg_win'], $bt['avg_loss'],
                $bt['best_trade'], $bt['worst_trade'],
                $bt['avg_bars'],
                $conn->real_escape_string($trade_log_json),
                date('Y-m-d H:i:s')
            );
            $conn->query($sql);

            $results_summary[] = array(
                'strategy' => $strat['name'],
                'pair' => $pair,
                'trades' => $bt['total'],
                'win_rate' => $bt['win_rate'],
                'total_return' => $bt['total_return'],
                'profit_factor' => $bt['profit_factor'],
                'sharpe' => $bt['sharpe']
            );
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'action' => 'run_batch',
        'batch' => $batch,
        'strategies' => array_map('strat_name_only', $batch_strats),
        'pairs_tested' => count($pairs_to_run),
        'results_count' => count($results_summary),
        'results' => $results_summary,
        'elapsed_ms' => $elapsed
    ));
}

function strat_name_only($s) { return $s['name']; }

// ═══════════════════════════════════════════════════════════════════
//  ACTION: RUN ALL — Run all 10 batches sequentially
// ═══════════════════════════════════════════════════════════════════
function action_run_all($conn)
{
    global $TOP_PAIRS;
    $start = microtime(true);
    $tf = isset($_GET['tf']) ? intval($_GET['tf']) : 240;

    // Clear previous results
    $conn->query("DELETE FROM psi_results WHERE tf = " . intval($tf));

    $all_strats = get_all_strategies();
    $total_results = 0;
    $summary = array();

    foreach ($TOP_PAIRS as $pair) {
        $ohlcv = load_cached_ohlcv($conn, $pair, $tf);
        if (count($ohlcv) < 100) continue;
        $ind = precompute_indicators($ohlcv);

        foreach ($all_strats as $strat) {
            $bt = run_single_backtest($ohlcv, $ind, $strat);
            $trade_log_json = json_encode(array_slice($bt['trades'], -10));
            $sql = sprintf(
                "INSERT INTO psi_results (sid,sname,scat,pair,tf,trades,wins,losses,win_rate,total_ret,profit_factor,sharpe,max_dd,avg_win,avg_loss,best_trade,worst_trade,avg_bars,trade_log,computed_at) VALUES (%d,'%s','%s','%s',%d,%d,%d,%d,'%.2f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f',%d,'%s','%s')",
                $strat['id'],
                $conn->real_escape_string($strat['name']),
                $conn->real_escape_string($strat['cat']),
                $conn->real_escape_string($pair),
                $tf,
                $bt['total'], $bt['wins'], $bt['losses'],
                $bt['win_rate'], $bt['total_return'], $bt['profit_factor'],
                $bt['sharpe'], $bt['max_dd'],
                $bt['avg_win'], $bt['avg_loss'],
                $bt['best_trade'], $bt['worst_trade'],
                $bt['avg_bars'],
                $conn->real_escape_string($trade_log_json),
                date('Y-m-d H:i:s')
            );
            $conn->query($sql);
            $total_results++;
        }
        $summary[] = array('pair' => $pair, 'candles' => count($ohlcv));
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'action' => 'run_all',
        'total_strategies' => count($all_strats),
        'total_pairs' => count($summary),
        'total_backtests' => $total_results,
        'pairs' => $summary,
        'elapsed_ms' => $elapsed
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  ACTION: TOURNAMENT — Elimination rounds
// ═══════════════════════════════════════════════════════════════════
function action_tournament($conn)
{
    $start = microtime(true);
    $tid = 'T' . date('Ymd_His');

    // Get aggregate performance per strategy (across all pairs)
    $res = $conn->query("SELECT sid, sname, scat,
        COUNT(*) as pair_count,
        SUM(trades) as total_trades,
        SUM(wins) as total_wins,
        SUM(losses) as total_losses,
        AVG(win_rate) as avg_wr,
        AVG(total_ret) as avg_ret,
        AVG(profit_factor) as avg_pf,
        AVG(sharpe) as avg_sharpe,
        AVG(max_dd) as avg_dd,
        AVG(avg_win) as avg_win_pct,
        AVG(avg_loss) as avg_loss_pct,
        MAX(best_trade) as best_ever,
        MIN(worst_trade) as worst_ever
    FROM psi_results GROUP BY sid ORDER BY avg_wr DESC");

    if (!$res || $res->num_rows == 0) {
        echo json_encode(array('ok' => false, 'error' => 'No backtest results found. Run batches first.'));
        return;
    }

    $strategies = array();
    while ($r = $res->fetch_assoc()) {
        $r['avg_wr'] = floatval($r['avg_wr']);
        $r['avg_ret'] = floatval($r['avg_ret']);
        $r['avg_pf'] = floatval($r['avg_pf']);
        $r['avg_sharpe'] = floatval($r['avg_sharpe']);
        $r['avg_dd'] = floatval($r['avg_dd']);
        $r['total_trades'] = intval($r['total_trades']);
        $strategies[] = $r;
    }

    $now = date('Y-m-d H:i:s');
    $rounds = array();

    // --- ROUND 1: Minimum activity filter ---
    $survivors = array();
    $eliminated_r1 = array();
    foreach ($strategies as $s) {
        $reason = '';
        $elim = false;
        if ($s['total_trades'] < 10) {
            $reason = 'Too few trades: ' . $s['total_trades'] . ' (min 10)';
            $elim = true;
        }
        if ($elim) {
            $eliminated_r1[] = array('sid' => $s['sid'], 'name' => $s['sname'], 'reason' => $reason);
            $conn->query(sprintf(
                "INSERT INTO psi_tournament (tid,rnd,sid,sname,action,reason,score,rnk,created_at) VALUES ('%s',1,%d,'%s','ELIMINATED','%s','%.4f',0,'%s')",
                $conn->real_escape_string($tid), intval($s['sid']),
                $conn->real_escape_string($s['sname']),
                $conn->real_escape_string($reason), $s['avg_wr'], $now
            ));
        } else {
            $survivors[] = $s;
            $conn->query(sprintf(
                "INSERT INTO psi_tournament (tid,rnd,sid,sname,action,reason,score,rnk,created_at) VALUES ('%s',1,%d,'%s','SURVIVED','Sufficient trades: %d','%.4f',0,'%s')",
                $conn->real_escape_string($tid), intval($s['sid']),
                $conn->real_escape_string($s['sname']),
                $s['total_trades'], $s['avg_wr'], $now
            ));
        }
    }
    $rounds[] = array('round' => 1, 'name' => 'Activity Filter', 'survivors' => count($survivors), 'eliminated' => count($eliminated_r1));

    // --- ROUND 2: Win rate filter ---
    // Note: with ATR-based TP/SL giving ~2:1 R:R, 35% win rate is still profitable
    $prev = $survivors;
    $survivors = array();
    $eliminated_r2 = array();
    foreach ($prev as $s) {
        if ($s['avg_wr'] < 33) {
            $reason = 'Win rate too low: ' . round($s['avg_wr'], 1) . '% (min 33%)';
            $eliminated_r2[] = array('sid' => $s['sid'], 'name' => $s['sname'], 'reason' => $reason);
            $conn->query(sprintf(
                "INSERT INTO psi_tournament (tid,rnd,sid,sname,action,reason,score,rnk,created_at) VALUES ('%s',2,%d,'%s','ELIMINATED','%s','%.4f',0,'%s')",
                $conn->real_escape_string($tid), intval($s['sid']),
                $conn->real_escape_string($s['sname']),
                $conn->real_escape_string($reason), $s['avg_wr'], $now
            ));
        } else {
            $survivors[] = $s;
            $conn->query(sprintf(
                "INSERT INTO psi_tournament (tid,rnd,sid,sname,action,reason,score,rnk,created_at) VALUES ('%s',2,%d,'%s','SURVIVED','Win rate: %.1f%%','%.4f',0,'%s')",
                $conn->real_escape_string($tid), intval($s['sid']),
                $conn->real_escape_string($s['sname']),
                $s['avg_wr'], $s['avg_wr'], $now
            ));
        }
    }
    $rounds[] = array('round' => 2, 'name' => 'Win Rate Filter (>=40%)', 'survivors' => count($survivors), 'eliminated' => count($eliminated_r2));

    // --- ROUND 3: Profit factor filter ---
    $prev = $survivors;
    $survivors = array();
    foreach ($prev as $s) {
        if ($s['avg_pf'] < 1.0) {
            $reason = 'Profit factor < 1.0: ' . round($s['avg_pf'], 2);
            $conn->query(sprintf(
                "INSERT INTO psi_tournament (tid,rnd,sid,sname,action,reason,score,rnk,created_at) VALUES ('%s',3,%d,'%s','ELIMINATED','%s','%.4f',0,'%s')",
                $conn->real_escape_string($tid), intval($s['sid']),
                $conn->real_escape_string($s['sname']),
                $conn->real_escape_string($reason), $s['avg_pf'], $now
            ));
        } else {
            $survivors[] = $s;
            $conn->query(sprintf(
                "INSERT INTO psi_tournament (tid,rnd,sid,sname,action,reason,score,rnk,created_at) VALUES ('%s',3,%d,'%s','SURVIVED','PF: %.2f','%.4f',0,'%s')",
                $conn->real_escape_string($tid), intval($s['sid']),
                $conn->real_escape_string($s['sname']),
                $s['avg_pf'], $s['avg_pf'], $now
            ));
        }
    }
    $rounds[] = array('round' => 3, 'name' => 'Profit Factor Filter (>=1.0)', 'survivors' => count($survivors), 'eliminated' => count($prev) - count($survivors));

    // --- ROUND 4: Max drawdown filter ---
    $prev = $survivors;
    $survivors = array();
    foreach ($prev as $s) {
        if ($s['avg_dd'] > 40) {
            $reason = 'Max DD too high: ' . round($s['avg_dd'], 1) . '% (max 40%)';
            $conn->query(sprintf(
                "INSERT INTO psi_tournament (tid,rnd,sid,sname,action,reason,score,rnk,created_at) VALUES ('%s',4,%d,'%s','ELIMINATED','%s','%.4f',0,'%s')",
                $conn->real_escape_string($tid), intval($s['sid']),
                $conn->real_escape_string($s['sname']),
                $conn->real_escape_string($reason), $s['avg_dd'], $now
            ));
        } else {
            $survivors[] = $s;
            $conn->query(sprintf(
                "INSERT INTO psi_tournament (tid,rnd,sid,sname,action,reason,score,rnk,created_at) VALUES ('%s',4,%d,'%s','SURVIVED','DD: %.1f%%','%.4f',0,'%s')",
                $conn->real_escape_string($tid), intval($s['sid']),
                $conn->real_escape_string($s['sname']),
                $s['avg_dd'], $s['avg_dd'], $now
            ));
        }
    }
    $rounds[] = array('round' => 4, 'name' => 'Max Drawdown Filter (<=40%)', 'survivors' => count($survivors), 'eliminated' => count($prev) - count($survivors));

    // --- ROUND 5: Composite ranking ---
    // Score = (win_rate * 0.3) + (profit_factor * 15) + (sharpe * 10) + (avg_return * 0.5) - (max_dd * 0.2)
    foreach ($survivors as $k => $s) {
        $score = ($s['avg_wr'] * 0.3) + ($s['avg_pf'] * 15) + ($s['avg_sharpe'] * 10) + ($s['avg_ret'] * 0.5) - ($s['avg_dd'] * 0.2);
        $survivors[$k]['composite_score'] = round($score, 2);
    }
    usort($survivors, 'sort_by_score_desc');

    // Rank them
    $rank = 0;
    foreach ($survivors as $k => $s) {
        $rank++;
        $survivors[$k]['rank'] = $rank;
        $act = ($rank <= 15) ? 'WINNER' : 'RANKED';
        $conn->query(sprintf(
            "INSERT INTO psi_tournament (tid,rnd,sid,sname,action,reason,score,rnk,created_at) VALUES ('%s',5,%d,'%s','%s','Composite score: %.2f | WR:%.1f%% PF:%.2f Sharpe:%.2f DD:%.1f%%','%.4f',%d,'%s')",
            $conn->real_escape_string($tid), intval($s['sid']),
            $conn->real_escape_string($s['sname']),
            $act,
            $s['composite_score'], $s['avg_wr'], $s['avg_pf'], $s['avg_sharpe'], $s['avg_dd'],
            $s['composite_score'], $rank, $now
        ));
    }
    $rounds[] = array('round' => 5, 'name' => 'Composite Ranking', 'total_ranked' => count($survivors), 'top_15' => array_slice($survivors, 0, 15));

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'action' => 'tournament',
        'tournament_id' => $tid,
        'rounds' => $rounds,
        'total_strategies' => count($strategies),
        'final_survivors' => count($survivors),
        'top_15' => array_slice($survivors, 0, 15),
        'elapsed_ms' => $elapsed
    ));
}

function sort_by_score_desc($a, $b)
{
    if ($a['composite_score'] == $b['composite_score']) return 0;
    return ($a['composite_score'] > $b['composite_score']) ? -1 : 1;
}

// ═══════════════════════════════════════════════════════════════════
//  ACTION: LIVE SCAN — Run winning strategies on current data
// ═══════════════════════════════════════════════════════════════════
function action_live_scan($conn)
{
    global $TOP_PAIRS;
    $start = microtime(true);

    // Get top 15 winning strategy IDs from latest tournament (winners + top ranked)
    $res = $conn->query("SELECT sid, sname FROM psi_tournament WHERE action IN ('WINNER','RANKED') ORDER BY score DESC LIMIT 15");
    if (!$res || $res->num_rows == 0) {
        echo json_encode(array('ok' => false, 'error' => 'No tournament winners found. Run tournament first.'));
        return;
    }
    $winners = array();
    while ($r = $res->fetch_assoc()) {
        $winners[intval($r['sid'])] = $r['sname'];
    }
    $winner_ids = array_keys($winners);

    // Get all strategy definitions
    $all_strats = get_all_strategies();
    $winner_strats = array();
    foreach ($all_strats as $s) {
        if (in_array($s['id'], $winner_ids)) {
            $winner_strats[] = $s;
        }
    }

    // Fetch live OHLCV for all pairs
    $pair_str = implode(',', $TOP_PAIRS);
    $tickers = fetch_kraken_tickers($pair_str);

    $signals = array();
    $pair_confluence = array();

    foreach ($TOP_PAIRS as $pair) {
        // Load recent cached OHLCV + append latest ticker
        $ohlcv = load_cached_ohlcv($conn, $pair, 240);
        if (count($ohlcv) < 100) continue;
        $ind = precompute_indicators($ohlcv);

        $last_idx = count($ohlcv) - 1;
        $agreeing = array();

        // Check last 3 candles for recent signals (12h window on 4h TF)
        foreach ($winner_strats as $strat) {
            $fired = false;
            for ($ci = $last_idx; $ci >= max(55, $last_idx - 2); $ci--) {
                $sig = call_strategy($strat, $ci, $ohlcv, $ind);
                if ($sig > 0) { $fired = true; break; }
            }
            if ($fired) {
                $agreeing[] = $strat['name'];
            }
        }

        $confluence_count = count($agreeing);
        if ($confluence_count >= 2) {
            $price = floatval($ohlcv[$last_idx]['c']);
            $atr = $ind['atr_arr'][count($ind['atr_arr']) - 1];
            if ($atr <= 0) $atr = $price * 0.02;
            // ATR-based TP/SL scaled by confluence strength
            $tp_atr_mult = 2.5 + ($confluence_count * 0.3);
            $sl_atr_mult = 1.5;
            $tp_price = $price + ($atr * $tp_atr_mult);
            $sl_price = $price - ($atr * $sl_atr_mult);
            $tp_pct = round((($tp_price - $price) / $price) * 100, 2);
            $sl_pct = round((($price - $sl_price) / $price) * 100, 2);

            $confidence = min(95, 40 + ($confluence_count * 5));
            $reasoning = $confluence_count . ' winning strategies agree: ' . implode(', ', $agreeing);

            // Insert signal
            $now = date('Y-m-d H:i:s');
            $sql = sprintf(
                "INSERT INTO psi_signals (sig_type,pair,direction,entry_price,tp_price,sl_price,tp_pct,sl_pct,confidence,confluence,strats_agreed,reasoning,status,created_at) VALUES ('PRO','%s','LONG','%.10f','%.10f','%.10f','%.4f','%.4f',%d,%d,'%s','%s','ACTIVE','%s')",
                $conn->real_escape_string($pair),
                $price, $tp_price, $sl_price, $tp_pct, $sl_pct,
                $confidence, $confluence_count,
                $conn->real_escape_string(implode(',', $agreeing)),
                $conn->real_escape_string($reasoning),
                $now
            );
            $conn->query($sql);

            $signals[] = array(
                'pair' => $pair,
                'price' => $price,
                'tp' => round($tp_price, 10),
                'sl' => round($sl_price, 10),
                'tp_pct' => $tp_pct,
                'sl_pct' => $sl_pct,
                'confidence' => $confidence,
                'confluence' => $confluence_count,
                'strategies' => $agreeing,
                'reasoning' => $reasoning
            );
        }
        $pair_confluence[$pair] = array('count' => $confluence_count, 'strats' => $agreeing);
    }

    usort($signals, 'sort_by_confluence_desc');

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'action' => 'live_scan',
        'timestamp' => date('Y-m-d H:i:s T'),
        'winning_strategies' => count($winner_strats),
        'pairs_scanned' => count($TOP_PAIRS),
        'pro_signals' => count($signals),
        'signals' => $signals,
        'all_confluence' => $pair_confluence,
        'elapsed_ms' => $elapsed
    ));
}

function sort_by_confluence_desc($a, $b)
{
    if ($a['confluence'] == $b['confluence']) return 0;
    return ($a['confluence'] > $b['confluence']) ? -1 : 1;
}

// ═══════════════════════════════════════════════════════════════════
//  ACTION: SIGNALS — Get current active pro signals
// ═══════════════════════════════════════════════════════════════════
function action_signals($conn)
{
    $res = $conn->query("SELECT * FROM psi_signals WHERE status='ACTIVE' ORDER BY confidence DESC, confluence DESC");
    $signals = array();
    if ($res) {
        while ($r = $res->fetch_assoc()) { $signals[] = $r; }
    }

    // Also get resolved history
    $res2 = $conn->query("SELECT * FROM psi_signals WHERE status='RESOLVED' ORDER BY resolved_at DESC LIMIT 50");
    $history = array();
    if ($res2) {
        while ($r = $res2->fetch_assoc()) { $history[] = $r; }
    }

    // Stats
    $res3 = $conn->query("SELECT
        COUNT(*) as total,
        SUM(CASE WHEN exit_reason='TP_HIT' THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN exit_reason='SL_HIT' THEN 1 ELSE 0 END) as losses,
        AVG(CASE WHEN status='RESOLVED' THEN pnl_pct ELSE NULL END) as avg_pnl,
        MAX(pnl_pct) as best,
        MIN(pnl_pct) as worst
    FROM psi_signals WHERE status='RESOLVED'");
    $stats = ($res3) ? $res3->fetch_assoc() : array();
    $resolved_total = intval($stats['wins']) + intval($stats['losses']);
    $stats['win_rate'] = ($resolved_total > 0) ? round(intval($stats['wins']) / $resolved_total * 100, 1) : 0;

    echo json_encode(array(
        'ok' => true,
        'active_signals' => $signals,
        'history' => $history,
        'stats' => $stats
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  ACTION: MONITOR — Check live prices vs active signals
// ═══════════════════════════════════════════════════════════════════
function action_monitor($conn)
{
    $start = microtime(true);
    $res = $conn->query("SELECT * FROM psi_signals WHERE status='ACTIVE'");
    if (!$res || $res->num_rows == 0) {
        echo json_encode(array('ok' => true, 'message' => 'No active signals', 'active' => 0));
        return;
    }

    $signals = array();
    $pairs_needed = array();
    while ($r = $res->fetch_assoc()) {
        $signals[] = $r;
        $pairs_needed[$r['pair']] = true;
    }

    $pair_str = implode(',', array_keys($pairs_needed));
    $tickers = fetch_kraken_tickers($pair_str);
    $now = date('Y-m-d H:i:s');
    $resolved = 0;
    $still_open = 0;

    foreach ($signals as $sig) {
        $pair = $sig['pair'];
        // Find matching ticker key
        $current = 0;
        foreach ($tickers as $tk => $td) {
            if (strpos($tk, str_replace('USD', '', $pair)) !== false || $tk === $pair) {
                $current = floatval($td['c'][0]);
                break;
            }
        }
        if ($current <= 0) { $still_open++; continue; }

        $entry = floatval($sig['entry_price']);
        $tp = floatval($sig['tp_price']);
        $sl = floatval($sig['sl_price']);
        $pnl = (($current - $entry) / $entry) * 100;
        $peak = max(floatval($sig['peak_pnl']), $pnl);
        $trough = min(floatval($sig['trough_pnl']), $pnl);
        $checks = intval($sig['checks']) + 1;

        $is_resolved = false;
        $exit_reason = '';
        if ($current >= $tp) { $is_resolved = true; $exit_reason = 'TP_HIT'; }
        elseif ($current <= $sl) { $is_resolved = true; $exit_reason = 'SL_HIT'; }

        $hours = (time() - strtotime($sig['created_at'])) / 3600;
        if (!$is_resolved && $hours >= 72) { $is_resolved = true; $exit_reason = 'EXPIRED_72H'; }

        if ($is_resolved) {
            $conn->query(sprintf(
                "UPDATE psi_signals SET status='RESOLVED',current_price='%.10f',pnl_pct='%.4f',peak_pnl='%.4f',trough_pnl='%.4f',exit_price='%.10f',exit_reason='%s',checks=%d,resolved_at='%s' WHERE id=%d",
                $current, $pnl, $peak, $trough, $current,
                $conn->real_escape_string($exit_reason), $checks, $now, intval($sig['id'])
            ));
            $resolved++;
        } else {
            $conn->query(sprintf(
                "UPDATE psi_signals SET current_price='%.10f',pnl_pct='%.4f',peak_pnl='%.4f',trough_pnl='%.4f',checks=%d WHERE id=%d",
                $current, $pnl, $peak, $trough, $checks, intval($sig['id'])
            ));
            $still_open++;
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array(
        'ok' => true,
        'checked' => count($signals),
        'resolved' => $resolved,
        'still_open' => $still_open,
        'elapsed_ms' => $elapsed
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  ACTION: AUDIT — Full audit trail
// ═══════════════════════════════════════════════════════════════════
function action_audit($conn)
{
    // Latest tournament
    $res = $conn->query("SELECT tid FROM psi_tournament ORDER BY id DESC LIMIT 1");
    $tid = '';
    if ($res && $r = $res->fetch_assoc()) { $tid = $r['tid']; }

    // Get all rounds for this tournament
    $rounds = array();
    if ($tid !== '') {
        for ($rnd = 1; $rnd <= 5; $rnd++) {
            $res2 = $conn->query(sprintf(
                "SELECT sid,sname,action,reason,score,rnk FROM psi_tournament WHERE tid='%s' AND rnd=%d ORDER BY action DESC, score DESC",
                $conn->real_escape_string($tid), $rnd
            ));
            $entries = array();
            if ($res2) { while ($r = $res2->fetch_assoc()) { $entries[] = $r; } }
            $rounds[$rnd] = $entries;
        }
    }

    // Top strategies with per-pair breakdown
    $res3 = $conn->query("SELECT sid, sname, scat, pair, win_rate, total_ret, profit_factor, sharpe, max_dd, trades
    FROM psi_results ORDER BY win_rate DESC LIMIT 200");
    $detail = array();
    if ($res3) { while ($r = $res3->fetch_assoc()) { $detail[] = $r; } }

    // Signal audit
    $res4 = $conn->query("SELECT * FROM psi_signals ORDER BY created_at DESC LIMIT 50");
    $sig_audit = array();
    if ($res4) { while ($r = $res4->fetch_assoc()) { $sig_audit[] = $r; } }

    echo json_encode(array(
        'ok' => true,
        'tournament_id' => $tid,
        'rounds' => $rounds,
        'strategy_detail' => $detail,
        'signal_audit' => $sig_audit
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  ACTION: STATUS — System overview
// ═══════════════════════════════════════════════════════════════════
function action_status($conn)
{
    global $TOP_PAIRS;
    $cache = $conn->query("SELECT pair, tf, COUNT(*) as candles, MAX(fetched_at) as last_fetch FROM psi_ohlcv_cache GROUP BY pair, tf");
    $cached = array();
    if ($cache) { while ($r = $cache->fetch_assoc()) { $cached[] = $r; } }

    $bt = $conn->query("SELECT COUNT(DISTINCT sid) as strats, COUNT(DISTINCT pair) as pairs, COUNT(*) as total_runs FROM psi_results");
    $bt_info = ($bt) ? $bt->fetch_assoc() : array();

    $trn = $conn->query("SELECT tid, MAX(rnd) as max_round, COUNT(*) as entries FROM psi_tournament GROUP BY tid ORDER BY id DESC LIMIT 1");
    $trn_info = ($trn) ? $trn->fetch_assoc() : array();

    $sig = $conn->query("SELECT COUNT(*) as active FROM psi_signals WHERE status='ACTIVE'");
    $sig_info = ($sig) ? $sig->fetch_assoc() : array();

    echo json_encode(array(
        'ok' => true,
        'system' => 'Pro Signal Engine v1.0',
        'configured_pairs' => count($TOP_PAIRS),
        'pairs' => $TOP_PAIRS,
        'total_strategies' => 100,
        'cached_data' => $cached,
        'backtest_info' => $bt_info,
        'tournament_info' => $trn_info,
        'active_signals' => $sig_info
    ));
}

// ═══════════════════════════════════════════════════════════════════
//  ACTION: PAIRS
// ═══════════════════════════════════════════════════════════════════
function action_pairs($conn)
{
    global $TOP_PAIRS;
    // Fetch live tickers for all pairs
    $pair_str = implode(',', $TOP_PAIRS);
    $tickers = fetch_kraken_tickers($pair_str);

    $pairs = array();
    foreach ($TOP_PAIRS as $p) {
        $info = array('pair' => $p, 'price' => 0, 'range_pct' => 0, 'vol_usd' => 0);
        foreach ($tickers as $tk => $td) {
            if ($tk === $p || strpos($tk, str_replace('USD', '', $p)) !== false) {
                $price = floatval($td['c'][0]);
                $high = floatval($td['h'][1]);
                $low = floatval($td['l'][1]);
                $vol = floatval($td['v'][1]) * $price;
                $range = ($low > 0) ? (($high - $low) / $low) * 100 : 0;
                $info = array('pair' => $p, 'price' => $price, 'range_pct' => round($range, 2), 'vol_usd' => round($vol));
                break;
            }
        }
        $pairs[] = $info;
    }

    usort($pairs, 'sort_by_range_desc');
    echo json_encode(array('ok' => true, 'pairs' => $pairs));
}

function sort_by_range_desc($a, $b)
{
    if ($a['range_pct'] == $b['range_pct']) return 0;
    return ($a['range_pct'] > $b['range_pct']) ? -1 : 1;
}

// ═══════════════════════════════════════════════════════════════════
//  HELPER: Fetch Kraken tickers
// ═══════════════════════════════════════════════════════════════════
function fetch_kraken_tickers($pair_str)
{
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . $pair_str;
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'ProSignalEngine/1.0');
    $resp = curl_exec($ch);
    curl_close($ch);
    if (!$resp) return array();
    $data = json_decode($resp, true);
    if (!$data || !isset($data['result'])) return array();
    return $data['result'];
}

// ═══════════════════════════════════════════════════════════════════
//  HELPER: Load cached OHLCV
// ═══════════════════════════════════════════════════════════════════
function load_cached_ohlcv($conn, $pair, $tf)
{
    $res = $conn->query(sprintf(
        "SELECT t,o,h,l,c,vw,v,tc FROM psi_ohlcv_cache WHERE pair='%s' AND tf=%d ORDER BY t ASC",
        $conn->real_escape_string($pair), intval($tf)
    ));
    $data = array();
    if ($res) {
        while ($r = $res->fetch_assoc()) {
            $data[] = array(
                't' => intval($r['t']),
                'o' => floatval($r['o']),
                'h' => floatval($r['h']),
                'l' => floatval($r['l']),
                'c' => floatval($r['c']),
                'vw' => floatval($r['vw']),
                'v' => floatval($r['v']),
                'tc' => intval($r['tc'])
            );
        }
    }
    return $data;
}

// ═══════════════════════════════════════════════════════════════════
//  INDICATOR CALCULATIONS
// ═══════════════════════════════════════════════════════════════════

function calc_ema_arr($data, $period)
{
    $n = count($data);
    if ($n < $period) return array_fill(0, $n, $data[$n - 1]);
    $k = 2.0 / ($period + 1);
    $ema = array_fill(0, $period - 1, 0);
    $sma = array_sum(array_slice($data, 0, $period)) / $period;
    $ema[$period - 1] = $sma;
    for ($i = $period; $i < $n; $i++) {
        $val = ($data[$i] * $k) + ($ema[$i - 1] * (1 - $k));
        $ema[$i] = $val;
    }
    // Fill initial with first valid
    for ($i = 0; $i < $period - 1; $i++) {
        $ema[$i] = $ema[$period - 1];
    }
    return $ema;
}

function calc_sma_arr($data, $period)
{
    $n = count($data);
    $sma = array_fill(0, $n, 0);
    $sum = 0;
    for ($i = 0; $i < $n; $i++) {
        $sum += $data[$i];
        if ($i >= $period) { $sum -= $data[$i - $period]; }
        if ($i >= $period - 1) {
            $sma[$i] = $sum / $period;
        } else {
            $sma[$i] = $sum / ($i + 1);
        }
    }
    return $sma;
}

function calc_rsi_arr($closes, $period)
{
    $n = count($closes);
    $rsi = array_fill(0, $n, 50);
    if ($n < $period + 1) return $rsi;

    $gains = array();
    $losses = array();
    for ($i = 1; $i < $n; $i++) {
        $diff = $closes[$i] - $closes[$i - 1];
        $gains[$i] = ($diff > 0) ? $diff : 0;
        $losses[$i] = ($diff < 0) ? abs($diff) : 0;
    }

    $avg_gain = 0;
    $avg_loss = 0;
    for ($i = 1; $i <= $period; $i++) {
        $avg_gain += $gains[$i];
        $avg_loss += $losses[$i];
    }
    $avg_gain /= $period;
    $avg_loss /= $period;

    if ($avg_loss == 0) { $rsi[$period] = 100; }
    else { $rsi[$period] = 100 - (100 / (1 + $avg_gain / $avg_loss)); }

    for ($i = $period + 1; $i < $n; $i++) {
        $avg_gain = (($avg_gain * ($period - 1)) + $gains[$i]) / $period;
        $avg_loss = (($avg_loss * ($period - 1)) + $losses[$i]) / $period;
        if ($avg_loss == 0) { $rsi[$i] = 100; }
        else { $rsi[$i] = 100 - (100 / (1 + $avg_gain / $avg_loss)); }
    }
    return $rsi;
}

function calc_atr_arr($highs, $lows, $closes, $period)
{
    $n = count($closes);
    $atr = array_fill(0, $n, 0);
    if ($n < $period + 1) return $atr;

    $trs = array(0);
    for ($i = 1; $i < $n; $i++) {
        $tr = max(
            $highs[$i] - $lows[$i],
            abs($highs[$i] - $closes[$i - 1]),
            abs($lows[$i] - $closes[$i - 1])
        );
        $trs[$i] = $tr;
    }

    $sum = 0;
    for ($i = 1; $i <= $period; $i++) { $sum += $trs[$i]; }
    $atr[$period] = $sum / $period;

    for ($i = $period + 1; $i < $n; $i++) {
        $atr[$i] = (($atr[$i - 1] * ($period - 1)) + $trs[$i]) / $period;
    }
    for ($i = 0; $i < $period; $i++) { $atr[$i] = $atr[$period]; }
    return $atr;
}

function calc_bb_arr($closes, $period, $mult)
{
    $n = count($closes);
    $upper = array_fill(0, $n, 0);
    $middle = array_fill(0, $n, 0);
    $lower = array_fill(0, $n, 0);
    $bw = array_fill(0, $n, 0);

    $sma = calc_sma_arr($closes, $period);
    for ($i = $period - 1; $i < $n; $i++) {
        $slice = array_slice($closes, $i - $period + 1, $period);
        $mean = $sma[$i];
        $sum_sq = 0;
        foreach ($slice as $v) { $sum_sq += ($v - $mean) * ($v - $mean); }
        $std = sqrt($sum_sq / $period);

        $middle[$i] = $mean;
        $upper[$i] = $mean + ($mult * $std);
        $lower[$i] = $mean - ($mult * $std);
        $bw[$i] = ($mean > 0) ? ($std * $mult * 2) / $mean * 100 : 0;
    }
    return array('upper' => $upper, 'middle' => $middle, 'lower' => $lower, 'bandwidth' => $bw);
}

function calc_macd_arr($closes)
{
    $ema12 = calc_ema_arr($closes, 12);
    $ema26 = calc_ema_arr($closes, 26);
    $n = count($closes);
    $macd_line = array_fill(0, $n, 0);
    for ($i = 0; $i < $n; $i++) {
        $macd_line[$i] = $ema12[$i] - $ema26[$i];
    }
    $signal = calc_ema_arr($macd_line, 9);
    $histogram = array_fill(0, $n, 0);
    for ($i = 0; $i < $n; $i++) {
        $histogram[$i] = $macd_line[$i] - $signal[$i];
    }
    return array('line' => $macd_line, 'signal' => $signal, 'histogram' => $histogram);
}

function calc_obv_arr($closes, $volumes)
{
    $n = count($closes);
    $obv = array_fill(0, $n, 0);
    for ($i = 1; $i < $n; $i++) {
        if ($closes[$i] > $closes[$i - 1]) { $obv[$i] = $obv[$i - 1] + $volumes[$i]; }
        elseif ($closes[$i] < $closes[$i - 1]) { $obv[$i] = $obv[$i - 1] - $volumes[$i]; }
        else { $obv[$i] = $obv[$i - 1]; }
    }
    return $obv;
}

function calc_stoch_arr($highs, $lows, $closes, $k_period, $d_period)
{
    $n = count($closes);
    $stoch_k = array_fill(0, $n, 50);
    for ($i = $k_period - 1; $i < $n; $i++) {
        $hh = 0; $ll = 999999999;
        for ($j = $i - $k_period + 1; $j <= $i; $j++) {
            if ($highs[$j] > $hh) $hh = $highs[$j];
            if ($lows[$j] < $ll) $ll = $lows[$j];
        }
        $range = $hh - $ll;
        $stoch_k[$i] = ($range > 0) ? (($closes[$i] - $ll) / $range) * 100 : 50;
    }
    $stoch_d = calc_sma_arr($stoch_k, $d_period);
    return array('k' => $stoch_k, 'd' => $stoch_d);
}

function calc_adx_arr($highs, $lows, $closes, $period)
{
    $n = count($closes);
    $adx = array_fill(0, $n, 25);
    $plus_di = array_fill(0, $n, 0);
    $minus_di = array_fill(0, $n, 0);
    if ($n < $period * 2) return array('adx' => $adx, 'plus_di' => $plus_di, 'minus_di' => $minus_di);

    $tr = array(0);
    $plus_dm = array(0);
    $minus_dm = array(0);
    for ($i = 1; $i < $n; $i++) {
        $tr[$i] = max($highs[$i] - $lows[$i], abs($highs[$i] - $closes[$i - 1]), abs($lows[$i] - $closes[$i - 1]));
        $up = $highs[$i] - $highs[$i - 1];
        $down = $lows[$i - 1] - $lows[$i];
        $plus_dm[$i] = ($up > $down && $up > 0) ? $up : 0;
        $minus_dm[$i] = ($down > $up && $down > 0) ? $down : 0;
    }

    $atr14 = 0; $pdm14 = 0; $mdm14 = 0;
    for ($i = 1; $i <= $period; $i++) {
        $atr14 += $tr[$i]; $pdm14 += $plus_dm[$i]; $mdm14 += $minus_dm[$i];
    }

    $dx_arr = array();
    for ($i = $period; $i < $n; $i++) {
        if ($i > $period) {
            $atr14 = $atr14 - ($atr14 / $period) + $tr[$i];
            $pdm14 = $pdm14 - ($pdm14 / $period) + $plus_dm[$i];
            $mdm14 = $mdm14 - ($mdm14 / $period) + $minus_dm[$i];
        }
        $pdi = ($atr14 > 0) ? ($pdm14 / $atr14) * 100 : 0;
        $mdi = ($atr14 > 0) ? ($mdm14 / $atr14) * 100 : 0;
        $plus_di[$i] = $pdi;
        $minus_di[$i] = $mdi;
        $di_sum = $pdi + $mdi;
        $dx = ($di_sum > 0) ? abs($pdi - $mdi) / $di_sum * 100 : 0;
        $dx_arr[] = $dx;
    }

    // Smooth ADX
    if (count($dx_arr) >= $period) {
        $adx_val = array_sum(array_slice($dx_arr, 0, $period)) / $period;
        $adx[$period * 2 - 1] = $adx_val;
        for ($i = $period; $i < count($dx_arr); $i++) {
            $adx_val = (($adx_val * ($period - 1)) + $dx_arr[$i]) / $period;
            $idx = $i + $period;
            if ($idx < $n) $adx[$idx] = $adx_val;
        }
    }

    return array('adx' => $adx, 'plus_di' => $plus_di, 'minus_di' => $minus_di);
}

function calc_cci_arr($highs, $lows, $closes, $period)
{
    $n = count($closes);
    $cci = array_fill(0, $n, 0);
    $tp = array();
    for ($i = 0; $i < $n; $i++) {
        $tp[$i] = ($highs[$i] + $lows[$i] + $closes[$i]) / 3;
    }
    for ($i = $period - 1; $i < $n; $i++) {
        $slice = array_slice($tp, $i - $period + 1, $period);
        $mean = array_sum($slice) / $period;
        $md = 0;
        foreach ($slice as $v) { $md += abs($v - $mean); }
        $md /= $period;
        $cci[$i] = ($md > 0) ? ($tp[$i] - $mean) / (0.015 * $md) : 0;
    }
    return $cci;
}

function calc_williams_r_arr($highs, $lows, $closes, $period)
{
    $n = count($closes);
    $wr = array_fill(0, $n, -50);
    for ($i = $period - 1; $i < $n; $i++) {
        $hh = 0; $ll = 999999999;
        for ($j = $i - $period + 1; $j <= $i; $j++) {
            if ($highs[$j] > $hh) $hh = $highs[$j];
            if ($lows[$j] < $ll) $ll = $lows[$j];
        }
        $range = $hh - $ll;
        $wr[$i] = ($range > 0) ? (($hh - $closes[$i]) / $range) * -100 : -50;
    }
    return $wr;
}

function calc_mfi_arr($highs, $lows, $closes, $volumes, $period)
{
    $n = count($closes);
    $mfi = array_fill(0, $n, 50);
    $tp = array();
    for ($i = 0; $i < $n; $i++) {
        $tp[$i] = ($highs[$i] + $lows[$i] + $closes[$i]) / 3;
    }
    for ($i = $period; $i < $n; $i++) {
        $pos = 0; $neg = 0;
        for ($j = $i - $period + 1; $j <= $i; $j++) {
            $mf = $tp[$j] * $volumes[$j];
            if ($j > 0 && $tp[$j] > $tp[$j - 1]) { $pos += $mf; }
            else { $neg += $mf; }
        }
        $mfi[$i] = ($neg > 0) ? 100 - (100 / (1 + $pos / $neg)) : 100;
    }
    return $mfi;
}

function calc_roc_arr($closes, $period)
{
    $n = count($closes);
    $roc = array_fill(0, $n, 0);
    for ($i = $period; $i < $n; $i++) {
        $roc[$i] = ($closes[$i - $period] > 0) ? (($closes[$i] - $closes[$i - $period]) / $closes[$i - $period]) * 100 : 0;
    }
    return $roc;
}

function calc_supertrend_arr($highs, $lows, $closes, $period, $mult)
{
    $atr = calc_atr_arr($highs, $lows, $closes, $period);
    $n = count($closes);
    $st = array_fill(0, $n, 0);
    $direction = array_fill(0, $n, 1); // 1 = up, -1 = down

    for ($i = 1; $i < $n; $i++) {
        $hl2 = ($highs[$i] + $lows[$i]) / 2;
        $upper = $hl2 + ($mult * $atr[$i]);
        $lower = $hl2 - ($mult * $atr[$i]);

        if ($closes[$i] > $st[$i - 1]) {
            $direction[$i] = 1;
            $st[$i] = $lower;
        } else {
            $direction[$i] = -1;
            $st[$i] = $upper;
        }
    }
    return array('value' => $st, 'direction' => $direction);
}

function calc_donchian_arr($highs, $lows, $period)
{
    $n = count($highs);
    $upper = array_fill(0, $n, 0);
    $lower = array_fill(0, $n, 0);
    for ($i = $period - 1; $i < $n; $i++) {
        $hh = 0; $ll = 999999999;
        for ($j = $i - $period + 1; $j <= $i; $j++) {
            if ($highs[$j] > $hh) $hh = $highs[$j];
            if ($lows[$j] < $ll) $ll = $lows[$j];
        }
        $upper[$i] = $hh;
        $lower[$i] = $ll;
    }
    return array('upper' => $upper, 'lower' => $lower);
}

// ═══════════════════════════════════════════════════════════════════
//  PRE-COMPUTE ALL INDICATORS
// ═══════════════════════════════════════════════════════════════════
function precompute_indicators($ohlcv)
{
    $closes = array(); $highs = array(); $lows = array(); $volumes = array(); $opens = array();
    foreach ($ohlcv as $c) {
        $opens[] = $c['o'];
        $highs[] = $c['h'];
        $lows[] = $c['l'];
        $closes[] = $c['c'];
        $volumes[] = $c['v'];
    }

    return array(
        'closes' => $closes,
        'highs' => $highs,
        'lows' => $lows,
        'volumes' => $volumes,
        'opens' => $opens,
        // EMAs
        'ema9' => calc_ema_arr($closes, 9),
        'ema12' => calc_ema_arr($closes, 12),
        'ema21' => calc_ema_arr($closes, 21),
        'ema26' => calc_ema_arr($closes, 26),
        'ema50' => calc_ema_arr($closes, 50),
        'ema55' => calc_ema_arr($closes, 55),
        'ema200' => calc_ema_arr($closes, 200),
        // SMAs
        'sma20' => calc_sma_arr($closes, 20),
        'sma50' => calc_sma_arr($closes, 50),
        'sma200' => calc_sma_arr($closes, 200),
        // RSI
        'rsi14' => calc_rsi_arr($closes, 14),
        'rsi7' => calc_rsi_arr($closes, 7),
        'rsi21' => calc_rsi_arr($closes, 21),
        // ATR
        'atr_arr' => calc_atr_arr($highs, $lows, $closes, 14),
        'atr7' => calc_atr_arr($highs, $lows, $closes, 7),
        // Bollinger
        'bb20' => calc_bb_arr($closes, 20, 2),
        'bb20_1' => calc_bb_arr($closes, 20, 1.5),
        // MACD
        'macd' => calc_macd_arr($closes),
        // OBV
        'obv' => calc_obv_arr($closes, $volumes),
        // Stochastic
        'stoch14' => calc_stoch_arr($highs, $lows, $closes, 14, 3),
        'stoch9' => calc_stoch_arr($highs, $lows, $closes, 9, 3),
        // ADX
        'adx14' => calc_adx_arr($highs, $lows, $closes, 14),
        // CCI
        'cci20' => calc_cci_arr($highs, $lows, $closes, 20),
        // Williams %R
        'wr14' => calc_williams_r_arr($highs, $lows, $closes, 14),
        // MFI
        'mfi14' => calc_mfi_arr($highs, $lows, $closes, $volumes, 14),
        // ROC
        'roc10' => calc_roc_arr($closes, 10),
        'roc14' => calc_roc_arr($closes, 14),
        'roc21' => calc_roc_arr($closes, 21),
        // Supertrend
        'st_2' => calc_supertrend_arr($highs, $lows, $closes, 10, 2),
        'st_3' => calc_supertrend_arr($highs, $lows, $closes, 10, 3),
        // Donchian
        'don20' => calc_donchian_arr($highs, $lows, 20),
        'don50' => calc_donchian_arr($highs, $lows, 50),
        // Volume SMA
        'vol_sma20' => calc_sma_arr($volumes, 20),
        // OBV EMA
        'obv_ema10' => calc_ema_arr(calc_obv_arr($closes, $volumes), 10)
    );
}

// ═══════════════════════════════════════════════════════════════════
//  BACKTEST SIMULATION
// ═══════════════════════════════════════════════════════════════════
function run_single_backtest($ohlcv, $ind, $strat)
{
    $n = count($ohlcv);
    $warmup = 55; // Skip first 55 candles for indicator warmup
    $tp_atr_mult = isset($strat['tp_atr']) ? $strat['tp_atr'] : 2.5;
    $sl_atr_mult = isset($strat['sl_atr']) ? $strat['sl_atr'] : 1.5;

    $trades = array();
    $in_position = false;
    $entry_price = 0;
    $entry_idx = 0;
    $tp_price = 0;
    $sl_price = 0;
    $trailing_sl = 0;

    for ($i = $warmup; $i < $n; $i++) {
        $price = $ind['closes'][$i];
        $high = $ind['highs'][$i];
        $low = $ind['lows'][$i];

        if ($in_position) {
            // Trailing stop: move SL up if price makes new high
            $new_trail = $high - ($ind['atr_arr'][$i] * $sl_atr_mult);
            if ($new_trail > $trailing_sl) $trailing_sl = $new_trail;

            // Check TP/SL hit (using high/low for realism)
            if ($high >= $tp_price) {
                $pnl = (($tp_price - $entry_price) / $entry_price) * 100;
                $trades[] = array('entry_idx' => $entry_idx, 'exit_idx' => $i, 'entry' => $entry_price, 'exit' => $tp_price, 'pnl' => $pnl, 'reason' => 'TP', 'bars' => $i - $entry_idx);
                $in_position = false;
            } elseif ($low <= $trailing_sl) {
                $exit_p = max($trailing_sl, $low);
                $pnl = (($exit_p - $entry_price) / $entry_price) * 100;
                $trades[] = array('entry_idx' => $entry_idx, 'exit_idx' => $i, 'entry' => $entry_price, 'exit' => $exit_p, 'pnl' => $pnl, 'reason' => 'SL', 'bars' => $i - $entry_idx);
                $in_position = false;
            }
            // Max hold: 50 candles (200h for 4h TF = ~8 days)
            if ($in_position && ($i - $entry_idx) >= 50) {
                $pnl = (($price - $entry_price) / $entry_price) * 100;
                $trades[] = array('entry_idx' => $entry_idx, 'exit_idx' => $i, 'entry' => $entry_price, 'exit' => $price, 'pnl' => $pnl, 'reason' => 'TIMEOUT', 'bars' => $i - $entry_idx);
                $in_position = false;
            }
        } else {
            // Check for entry signal
            $signal = call_strategy($strat, $i, $ohlcv, $ind);
            if ($signal > 0 && $price > 0) {
                $atr = $ind['atr_arr'][$i];
                if ($atr <= 0) $atr = $price * 0.02; // fallback 2%
                $in_position = true;
                $entry_price = $price;
                $entry_idx = $i;
                $tp_price = $price + ($atr * $tp_atr_mult);
                $sl_price = $price - ($atr * $sl_atr_mult);
                $trailing_sl = $sl_price;
            }
        }
    }

    // Close any open position
    if ($in_position && $n > 0) {
        $price = $ind['closes'][$n - 1];
        $pnl = (($price - $entry_price) / $entry_price) * 100;
        $trades[] = array('entry_idx' => $entry_idx, 'exit_idx' => $n - 1, 'entry' => $entry_price, 'exit' => $price, 'pnl' => $pnl, 'reason' => 'END', 'bars' => $n - 1 - $entry_idx);
    }

    return compute_bt_stats($trades);
}

function compute_bt_stats($trades)
{
    $total = count($trades);
    $wins = 0; $losses = 0;
    $gross_profit = 0; $gross_loss = 0;
    $returns = array();
    $best = -999; $worst = 999;
    $total_bars = 0;
    $total_win_pnl = 0; $total_loss_pnl = 0;

    foreach ($trades as $t) {
        $pnl = $t['pnl'];
        $returns[] = $pnl;
        $total_bars += $t['bars'];
        if ($pnl >= 0) {
            $wins++;
            $gross_profit += $pnl;
            $total_win_pnl += $pnl;
        } else {
            $losses++;
            $gross_loss += abs($pnl);
            $total_loss_pnl += $pnl;
        }
        if ($pnl > $best) $best = $pnl;
        if ($pnl < $worst) $worst = $pnl;
    }

    $win_rate = ($total > 0) ? ($wins / $total) * 100 : 0;
    $profit_factor = ($gross_loss > 0) ? $gross_profit / $gross_loss : (($gross_profit > 0) ? 99 : 0);
    $total_return = array_sum($returns);
    $avg_win = ($wins > 0) ? $total_win_pnl / $wins : 0;
    $avg_loss = ($losses > 0) ? $total_loss_pnl / $losses : 0;
    $avg_bars = ($total > 0) ? round($total_bars / $total) : 0;

    // Sharpe ratio (simplified: mean / std of returns)
    $sharpe = 0;
    if ($total > 1) {
        $mean = $total_return / $total;
        $variance = 0;
        foreach ($returns as $r) { $variance += ($r - $mean) * ($r - $mean); }
        $std = sqrt($variance / ($total - 1));
        $sharpe = ($std > 0) ? $mean / $std : 0;
    }

    // Max drawdown
    $max_dd = 0;
    $equity = 100;
    $peak = 100;
    foreach ($returns as $r) {
        $equity *= (1 + $r / 100);
        if ($equity > $peak) $peak = $equity;
        $dd = (($peak - $equity) / $peak) * 100;
        if ($dd > $max_dd) $max_dd = $dd;
    }

    return array(
        'total' => $total,
        'wins' => $wins,
        'losses' => $losses,
        'win_rate' => round($win_rate, 2),
        'total_return' => round($total_return, 4),
        'profit_factor' => round($profit_factor, 4),
        'sharpe' => round($sharpe, 4),
        'max_dd' => round($max_dd, 4),
        'avg_win' => round($avg_win, 4),
        'avg_loss' => round($avg_loss, 4),
        'best_trade' => ($best > -999) ? round($best, 4) : 0,
        'worst_trade' => ($worst < 999) ? round($worst, 4) : 0,
        'avg_bars' => $avg_bars,
        'trades' => $trades
    );
}

// ═══════════════════════════════════════════════════════════════════
//  STRATEGY DISPATCHER
// ═══════════════════════════════════════════════════════════════════
function call_strategy($strat, $i, $ohlcv, $ind)
{
    $func = $strat['func'];
    $p = isset($strat['params']) ? $strat['params'] : array();
    return $func($i, $ind, $p);
}

// ═══════════════════════════════════════════════════════════════════
//  100 STRATEGY DEFINITIONS
// ═══════════════════════════════════════════════════════════════════
function get_all_strategies()
{
    return array(
        // === TREND FOLLOWING (1-20) ===
        // tp_atr = ATR multiplier for take profit, sl_atr = ATR multiplier for stop loss
        array('id'=>1, 'name'=>'SMA Cross 9/21', 'cat'=>'trend', 'func'=>'strat_sma_cross', 'params'=>array(9,21), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>2, 'name'=>'SMA Cross 20/50', 'cat'=>'trend', 'func'=>'strat_sma_cross', 'params'=>array(20,50), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>3, 'name'=>'EMA Cross 9/21', 'cat'=>'trend', 'func'=>'strat_ema_cross', 'params'=>array(9,21), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>4, 'name'=>'EMA Cross 12/26', 'cat'=>'trend', 'func'=>'strat_ema_cross', 'params'=>array(12,26), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>5, 'name'=>'EMA Cross 20/50', 'cat'=>'trend', 'func'=>'strat_ema_cross', 'params'=>array(20,50), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>6, 'name'=>'Triple EMA 9/21/55', 'cat'=>'trend', 'func'=>'strat_triple_ema', 'params'=>array(9,21,55), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>7, 'name'=>'Triple EMA 12/26/50', 'cat'=>'trend', 'func'=>'strat_triple_ema', 'params'=>array(12,26,50), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>8, 'name'=>'MACD Signal Cross', 'cat'=>'trend', 'func'=>'strat_macd_cross', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>9, 'name'=>'MACD Histogram Reversal', 'cat'=>'trend', 'func'=>'strat_macd_hist', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>10, 'name'=>'Supertrend 10/2', 'cat'=>'trend', 'func'=>'strat_supertrend', 'params'=>array('st_2'), 'tp_atr'=>3.0, 'sl_atr'=>2.0),
        array('id'=>11, 'name'=>'Supertrend 10/3', 'cat'=>'trend', 'func'=>'strat_supertrend', 'params'=>array('st_3'), 'tp_atr'=>3.5, 'sl_atr'=>2.0),
        array('id'=>12, 'name'=>'ADX Trend + EMA', 'cat'=>'trend', 'func'=>'strat_adx_trend', 'params'=>array(25), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>13, 'name'=>'ADX Trend + EMA (20)', 'cat'=>'trend', 'func'=>'strat_adx_trend', 'params'=>array(20), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>14, 'name'=>'Donchian Breakout 20', 'cat'=>'trend', 'func'=>'strat_donchian', 'params'=>array('don20'), 'tp_atr'=>3.0, 'sl_atr'=>2.0),
        array('id'=>15, 'name'=>'Donchian Breakout 50', 'cat'=>'trend', 'func'=>'strat_donchian', 'params'=>array('don50'), 'tp_atr'=>4.0, 'sl_atr'=>2.0),
        array('id'=>16, 'name'=>'EMA Cross 9/55', 'cat'=>'trend', 'func'=>'strat_ema_cross', 'params'=>array(9,55), 'tp_atr'=>3.5, 'sl_atr'=>2.0),
        array('id'=>17, 'name'=>'SMA Cross 50/200', 'cat'=>'trend', 'func'=>'strat_sma_cross', 'params'=>array(50,200), 'tp_atr'=>4.0, 'sl_atr'=>2.0),
        array('id'=>18, 'name'=>'MACD + EMA Trend', 'cat'=>'trend', 'func'=>'strat_macd_ema', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>19, 'name'=>'Price > SMA200 + EMA Cross', 'cat'=>'trend', 'func'=>'strat_trend_filter', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>20, 'name'=>'DEMA Cross 9/21', 'cat'=>'trend', 'func'=>'strat_dema_cross', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),

        // === MEAN REVERSION (21-35) ===
        array('id'=>21, 'name'=>'BB Lower Bounce 2s', 'cat'=>'mean_rev', 'func'=>'strat_bb_bounce', 'params'=>array('bb20',2), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>22, 'name'=>'BB Lower Bounce 1.5s', 'cat'=>'mean_rev', 'func'=>'strat_bb_bounce', 'params'=>array('bb20_1',1.5), 'tp_atr'=>1.5, 'sl_atr'=>1.0),
        array('id'=>23, 'name'=>'BB Squeeze Breakout', 'cat'=>'mean_rev', 'func'=>'strat_bb_squeeze', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>24, 'name'=>'RSI Oversold 30', 'cat'=>'mean_rev', 'func'=>'strat_rsi_level', 'params'=>array(30, 'rsi14'), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>25, 'name'=>'RSI Oversold 25', 'cat'=>'mean_rev', 'func'=>'strat_rsi_level', 'params'=>array(25, 'rsi14'), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>26, 'name'=>'RSI Oversold 20', 'cat'=>'mean_rev', 'func'=>'strat_rsi_level', 'params'=>array(20, 'rsi14'), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>27, 'name'=>'RSI7 Oversold 25', 'cat'=>'mean_rev', 'func'=>'strat_rsi_level', 'params'=>array(25, 'rsi7'), 'tp_atr'=>2.0, 'sl_atr'=>1.0),
        array('id'=>28, 'name'=>'Stoch Oversold 20', 'cat'=>'mean_rev', 'func'=>'strat_stoch_level', 'params'=>array(20, 'stoch14'), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>29, 'name'=>'Stoch + RSI Double Oversold', 'cat'=>'mean_rev', 'func'=>'strat_stoch_rsi', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>30, 'name'=>'Williams %R Oversold -80', 'cat'=>'mean_rev', 'func'=>'strat_wr_level', 'params'=>array(-80), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>31, 'name'=>'Williams %R Oversold -90', 'cat'=>'mean_rev', 'func'=>'strat_wr_level', 'params'=>array(-90), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>32, 'name'=>'CCI Oversold -100', 'cat'=>'mean_rev', 'func'=>'strat_cci_level', 'params'=>array(-100), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>33, 'name'=>'CCI Oversold -200', 'cat'=>'mean_rev', 'func'=>'strat_cci_level', 'params'=>array(-200), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>34, 'name'=>'MFI Oversold 20', 'cat'=>'mean_rev', 'func'=>'strat_mfi_level', 'params'=>array(20), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>35, 'name'=>'BB + RSI Combo', 'cat'=>'mean_rev', 'func'=>'strat_bb_rsi', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.2),

        // === MOMENTUM (36-50) ===
        array('id'=>36, 'name'=>'RSI Momentum >50 Rising', 'cat'=>'momentum', 'func'=>'strat_rsi_momentum', 'params'=>array(50), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>37, 'name'=>'RSI Momentum >55 Rising', 'cat'=>'momentum', 'func'=>'strat_rsi_momentum', 'params'=>array(55), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>38, 'name'=>'ROC Positive 10', 'cat'=>'momentum', 'func'=>'strat_roc', 'params'=>array('roc10', 0), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>39, 'name'=>'ROC Positive 14', 'cat'=>'momentum', 'func'=>'strat_roc', 'params'=>array('roc14', 0), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>40, 'name'=>'ROC Strong 21 (>5%)', 'cat'=>'momentum', 'func'=>'strat_roc', 'params'=>array('roc21', 5), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>41, 'name'=>'MACD Hist Positive + Rising', 'cat'=>'momentum', 'func'=>'strat_macd_mom', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>42, 'name'=>'Price Momentum 10-bar', 'cat'=>'momentum', 'func'=>'strat_price_mom', 'params'=>array(10), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>43, 'name'=>'Price Momentum 20-bar', 'cat'=>'momentum', 'func'=>'strat_price_mom', 'params'=>array(20), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>44, 'name'=>'VWAP Momentum (Volume-Weighted)', 'cat'=>'momentum', 'func'=>'strat_vwap_mom', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>45, 'name'=>'Stoch Momentum (K crosses D up)', 'cat'=>'momentum', 'func'=>'strat_stoch_cross', 'params'=>array('stoch14'), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>46, 'name'=>'Stoch9 Momentum Cross', 'cat'=>'momentum', 'func'=>'strat_stoch_cross', 'params'=>array('stoch9'), 'tp_atr'=>2.0, 'sl_atr'=>1.0),
        array('id'=>47, 'name'=>'Elder Ray Bull Power', 'cat'=>'momentum', 'func'=>'strat_elder_ray', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>48, 'name'=>'OBV Rising + Price Up', 'cat'=>'momentum', 'func'=>'strat_obv_momentum', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>49, 'name'=>'ADX Rising + DI+ > DI-', 'cat'=>'momentum', 'func'=>'strat_adx_di', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>50, 'name'=>'Multi-Momentum Score', 'cat'=>'momentum', 'func'=>'strat_multi_mom', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),

        // === BREAKOUT (51-65) ===
        array('id'=>51, 'name'=>'ATR Breakout 1.5x', 'cat'=>'breakout', 'func'=>'strat_atr_break', 'params'=>array(1.5), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>52, 'name'=>'ATR Breakout 2x', 'cat'=>'breakout', 'func'=>'strat_atr_break', 'params'=>array(2.0), 'tp_atr'=>3.0, 'sl_atr'=>2.0),
        array('id'=>53, 'name'=>'ATR Breakout 2.5x', 'cat'=>'breakout', 'func'=>'strat_atr_break', 'params'=>array(2.5), 'tp_atr'=>3.5, 'sl_atr'=>2.0),
        array('id'=>54, 'name'=>'20-Bar High Breakout', 'cat'=>'breakout', 'func'=>'strat_nbar_high', 'params'=>array(20), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>55, 'name'=>'50-Bar High Breakout', 'cat'=>'breakout', 'func'=>'strat_nbar_high', 'params'=>array(50), 'tp_atr'=>4.0, 'sl_atr'=>2.0),
        array('id'=>56, 'name'=>'BB Squeeze + Volume', 'cat'=>'breakout', 'func'=>'strat_bb_squeeze_vol', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>57, 'name'=>'Keltner Breakout', 'cat'=>'breakout', 'func'=>'strat_keltner_break', 'params'=>array(2.0), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>58, 'name'=>'Keltner Breakout 1.5x', 'cat'=>'breakout', 'func'=>'strat_keltner_break', 'params'=>array(1.5), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>59, 'name'=>'Inside Bar Breakout', 'cat'=>'breakout', 'func'=>'strat_inside_bar', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.0),
        array('id'=>60, 'name'=>'Engulfing Bullish', 'cat'=>'breakout', 'func'=>'strat_engulfing', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>61, 'name'=>'Three White Soldiers', 'cat'=>'breakout', 'func'=>'strat_three_bar', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>62, 'name'=>'Range Contraction Breakout', 'cat'=>'breakout', 'func'=>'strat_range_contract', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>63, 'name'=>'Volatility Squeeze Breakout', 'cat'=>'breakout', 'func'=>'strat_vol_squeeze', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>64, 'name'=>'Turtle Breakout 20/10', 'cat'=>'breakout', 'func'=>'strat_turtle', 'params'=>array(20), 'tp_atr'=>3.0, 'sl_atr'=>2.0),
        array('id'=>65, 'name'=>'Turtle Breakout 55/20', 'cat'=>'breakout', 'func'=>'strat_turtle', 'params'=>array(55), 'tp_atr'=>4.0, 'sl_atr'=>2.0),

        // === VOLUME-BASED (66-75) ===
        array('id'=>66, 'name'=>'Volume Spike 1.5x + Up', 'cat'=>'volume', 'func'=>'strat_vol_spike', 'params'=>array(1.5), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>67, 'name'=>'Volume Spike 2x + Up', 'cat'=>'volume', 'func'=>'strat_vol_spike', 'params'=>array(2.0), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>68, 'name'=>'Volume Spike 3x + Up', 'cat'=>'volume', 'func'=>'strat_vol_spike', 'params'=>array(3.0), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>69, 'name'=>'OBV Trend Following', 'cat'=>'volume', 'func'=>'strat_obv_trend', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>70, 'name'=>'OBV Divergence Bullish', 'cat'=>'volume', 'func'=>'strat_obv_divergence', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>71, 'name'=>'MFI + Volume Confluence', 'cat'=>'volume', 'func'=>'strat_mfi_vol', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>72, 'name'=>'Accumulation Detection', 'cat'=>'volume', 'func'=>'strat_accumulation', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>73, 'name'=>'Volume Profile + Trend', 'cat'=>'volume', 'func'=>'strat_vol_profile', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>74, 'name'=>'VWAP Bounce', 'cat'=>'volume', 'func'=>'strat_vwap_bounce', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.0),
        array('id'=>75, 'name'=>'Vol Climax Reversal', 'cat'=>'volume', 'func'=>'strat_vol_climax', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.2),

        // === SMART MONEY / PRICE ACTION (76-85) ===
        array('id'=>76, 'name'=>'Order Block Bounce', 'cat'=>'smart_money', 'func'=>'strat_order_block', 'params'=>array(5), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>77, 'name'=>'Order Block Bounce (3-bar)', 'cat'=>'smart_money', 'func'=>'strat_order_block', 'params'=>array(3), 'tp_atr'=>2.0, 'sl_atr'=>1.0),
        array('id'=>78, 'name'=>'Fair Value Gap Fill', 'cat'=>'smart_money', 'func'=>'strat_fvg', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>79, 'name'=>'Liquidity Sweep + Reclaim', 'cat'=>'smart_money', 'func'=>'strat_liq_sweep', 'params'=>array(20), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>80, 'name'=>'Liquidity Sweep 50-bar', 'cat'=>'smart_money', 'func'=>'strat_liq_sweep', 'params'=>array(50), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>81, 'name'=>'Break of Structure', 'cat'=>'smart_money', 'func'=>'strat_bos', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>82, 'name'=>'Demand Zone Bounce', 'cat'=>'smart_money', 'func'=>'strat_demand_zone', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>83, 'name'=>'Hammer Candle + Support', 'cat'=>'smart_money', 'func'=>'strat_hammer', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.0),
        array('id'=>84, 'name'=>'Rejection Wick', 'cat'=>'smart_money', 'func'=>'strat_rejection_wick', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>85, 'name'=>'Pin Bar Reversal', 'cat'=>'smart_money', 'func'=>'strat_pin_bar', 'params'=>array(), 'tp_atr'=>2.0, 'sl_atr'=>1.0),

        // === REGIME-BASED (86-90) ===
        array('id'=>86, 'name'=>'Regime RSI Mean Rev (ADX<25)', 'cat'=>'regime', 'func'=>'strat_regime_rsi', 'params'=>array(25), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>87, 'name'=>'Regime RSI Mean Rev (ADX<20)', 'cat'=>'regime', 'func'=>'strat_regime_rsi', 'params'=>array(20), 'tp_atr'=>2.0, 'sl_atr'=>1.2),
        array('id'=>88, 'name'=>'Regime Momentum (ADX>25)', 'cat'=>'regime', 'func'=>'strat_regime_mom', 'params'=>array(25), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>89, 'name'=>'Regime Breakout (Squeeze->Trend)', 'cat'=>'regime', 'func'=>'strat_regime_break', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>90, 'name'=>'Adaptive Regime Switch', 'cat'=>'regime', 'func'=>'strat_adaptive', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.2),

        // === CONFLUENCE / COMPOSITE (91-100) ===
        array('id'=>91, 'name'=>'RSI+MACD+EMA Triple', 'cat'=>'confluence', 'func'=>'strat_triple_confirm', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>92, 'name'=>'BB+Volume+RSI Combo', 'cat'=>'confluence', 'func'=>'strat_bvr_combo', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>93, 'name'=>'Breakout+Volume+RSI', 'cat'=>'confluence', 'func'=>'strat_break_vol_rsi', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>94, 'name'=>'Trend+MeanRev Filter', 'cat'=>'confluence', 'func'=>'strat_trend_mr', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>95, 'name'=>'5-Indicator Score >=4', 'cat'=>'confluence', 'func'=>'strat_5ind_score', 'params'=>array(4), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>96, 'name'=>'5-Indicator Score >=3', 'cat'=>'confluence', 'func'=>'strat_5ind_score', 'params'=>array(3), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>97, 'name'=>'TEMA Cross + Vol Surge', 'cat'=>'confluence', 'func'=>'strat_tema_vol', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.2),
        array('id'=>98, 'name'=>'RSI Divergence + Volume', 'cat'=>'confluence', 'func'=>'strat_rsi_div_vol', 'params'=>array(), 'tp_atr'=>2.5, 'sl_atr'=>1.5),
        array('id'=>99, 'name'=>'Smart Money + Momentum', 'cat'=>'confluence', 'func'=>'strat_smc_mom', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.5),
        array('id'=>100, 'name'=>'Ultimate Confluence 7-Check', 'cat'=>'confluence', 'func'=>'strat_ultimate', 'params'=>array(), 'tp_atr'=>3.0, 'sl_atr'=>1.2)
    );
}

// ═══════════════════════════════════════════════════════════════════
//  STRATEGY IMPLEMENTATIONS
// ═══════════════════════════════════════════════════════════════════

// -- TREND FOLLOWING --
function strat_sma_cross($i, $d, $p)
{
    $fast_key = 'sma' . $p[0]; $slow_key = 'sma' . $p[1];
    if (!isset($d[$fast_key]) || !isset($d[$slow_key])) return 0;
    if ($i < 2) return 0;
    $f = $d[$fast_key]; $s = $d[$slow_key];
    if ($f[$i] > $s[$i] && $f[$i-1] <= $s[$i-1]) return 1;
    return 0;
}

function strat_ema_cross($i, $d, $p)
{
    $fast_key = 'ema' . $p[0]; $slow_key = 'ema' . $p[1];
    if (!isset($d[$fast_key]) || !isset($d[$slow_key])) return 0;
    if ($i < 2) return 0;
    $f = $d[$fast_key]; $s = $d[$slow_key];
    if ($f[$i] > $s[$i] && $f[$i-1] <= $s[$i-1]) return 1;
    return 0;
}

function strat_triple_ema($i, $d, $p)
{
    $k1 = 'ema' . $p[0]; $k2 = 'ema' . $p[1]; $k3 = 'ema' . $p[2];
    if (!isset($d[$k1]) || !isset($d[$k2]) || !isset($d[$k3])) return 0;
    if ($i < 2) return 0;
    // All three aligned bullish AND fast just crossed mid
    if ($d[$k1][$i] > $d[$k2][$i] && $d[$k2][$i] > $d[$k3][$i]) {
        if ($d[$k1][$i-1] <= $d[$k2][$i-1]) return 1;
    }
    return 0;
}

function strat_macd_cross($i, $d, $p)
{
    $m = $d['macd'];
    if ($i < 2) return 0;
    if ($m['line'][$i] > $m['signal'][$i] && $m['line'][$i-1] <= $m['signal'][$i-1]) return 1;
    return 0;
}

function strat_macd_hist($i, $d, $p)
{
    $h = $d['macd']['histogram'];
    if ($i < 3) return 0;
    // Histogram turns positive after being negative
    if ($h[$i] > 0 && $h[$i-1] <= 0 && $h[$i-2] < 0) return 1;
    return 0;
}

function strat_supertrend($i, $d, $p)
{
    $key = $p[0];
    if (!isset($d[$key])) return 0;
    if ($i < 2) return 0;
    $dir = $d[$key]['direction'];
    if ($dir[$i] == 1 && $dir[$i-1] == -1) return 1;
    return 0;
}

function strat_adx_trend($i, $d, $p)
{
    $threshold = $p[0];
    if ($i < 2) return 0;
    $adx = $d['adx14']['adx'];
    $pdi = $d['adx14']['plus_di'];
    $mdi = $d['adx14']['minus_di'];
    if ($adx[$i] > $threshold && $pdi[$i] > $mdi[$i] && $d['ema9'][$i] > $d['ema21'][$i]) {
        if ($d['ema9'][$i-1] <= $d['ema21'][$i-1]) return 1;
    }
    return 0;
}

function strat_donchian($i, $d, $p)
{
    $key = $p[0];
    if (!isset($d[$key])) return 0;
    if ($i < 2) return 0;
    $c = $d['closes'];
    if ($c[$i] > $d[$key]['upper'][$i-1] && $c[$i-1] <= $d[$key]['upper'][$i-2]) return 1;
    return 0;
}

function strat_macd_ema($i, $d, $p)
{
    if ($i < 2) return 0;
    $m = $d['macd'];
    if ($m['histogram'][$i] > 0 && $d['ema9'][$i] > $d['ema21'][$i] && $d['closes'][$i] > $d['ema50'][$i]) return 1;
    return 0;
}

function strat_trend_filter($i, $d, $p)
{
    if ($i < 2) return 0;
    if ($d['closes'][$i] > $d['sma200'][$i] && $d['ema9'][$i] > $d['ema21'][$i] && $d['ema9'][$i-1] <= $d['ema21'][$i-1]) return 1;
    return 0;
}

function strat_dema_cross($i, $d, $p)
{
    // DEMA = 2*EMA - EMA(EMA)
    if ($i < 2) return 0;
    $e9 = $d['ema9']; $e21 = $d['ema21'];
    // Approximate DEMA
    $dema_fast = 2 * $e9[$i] - $d['ema12'][$i];
    $dema_slow = 2 * $e21[$i] - $d['ema26'][$i];
    $dema_fast_prev = 2 * $e9[$i-1] - $d['ema12'][$i-1];
    $dema_slow_prev = 2 * $e21[$i-1] - $d['ema26'][$i-1];
    if ($dema_fast > $dema_slow && $dema_fast_prev <= $dema_slow_prev) return 1;
    return 0;
}

// -- MEAN REVERSION --
function strat_bb_bounce($i, $d, $p)
{
    $key = $p[0];
    if (!isset($d[$key])) return 0;
    if ($i < 2) return 0;
    $c = $d['closes']; $l = $d['lows'];
    // Price touched or went below lower band, then closed above it
    if ($l[$i-1] <= $d[$key]['lower'][$i-1] && $c[$i] > $d[$key]['lower'][$i]) return 1;
    return 0;
}

function strat_bb_squeeze($i, $d, $p)
{
    if ($i < 5) return 0;
    $bw = $d['bb20']['bandwidth'];
    // Bandwidth contracted (squeeze), then expanding with price going up
    $min_bw = 999;
    for ($j = $i - 5; $j < $i; $j++) { if ($bw[$j] < $min_bw) $min_bw = $bw[$j]; }
    if ($bw[$i] > $min_bw * 1.5 && $d['closes'][$i] > $d['bb20']['middle'][$i]) return 1;
    return 0;
}

function strat_rsi_level($i, $d, $p)
{
    $level = $p[0]; $key = $p[1];
    if (!isset($d[$key])) return 0;
    if ($i < 2) return 0;
    // RSI was below level, now crossing back up
    if ($d[$key][$i-1] < $level && $d[$key][$i] >= $level) return 1;
    return 0;
}

function strat_stoch_level($i, $d, $p)
{
    $level = $p[0]; $key = $p[1];
    if (!isset($d[$key])) return 0;
    if ($i < 2) return 0;
    $k = $d[$key]['k'];
    if ($k[$i-1] < $level && $k[$i] >= $level) return 1;
    return 0;
}

function strat_stoch_rsi($i, $d, $p)
{
    if ($i < 2) return 0;
    $sk = $d['stoch14']['k'];
    $rsi = $d['rsi14'];
    if ($sk[$i-1] < 20 && $sk[$i] >= 20 && $rsi[$i] < 35) return 1;
    return 0;
}

function strat_wr_level($i, $d, $p)
{
    $level = $p[0];
    if ($i < 2) return 0;
    $wr = $d['wr14'];
    if ($wr[$i-1] < $level && $wr[$i] >= $level) return 1;
    return 0;
}

function strat_cci_level($i, $d, $p)
{
    $level = $p[0];
    if ($i < 2) return 0;
    $cci = $d['cci20'];
    if ($cci[$i-1] < $level && $cci[$i] >= $level) return 1;
    return 0;
}

function strat_mfi_level($i, $d, $p)
{
    $level = $p[0];
    if ($i < 2) return 0;
    $mfi = $d['mfi14'];
    if ($mfi[$i-1] < $level && $mfi[$i] >= $level) return 1;
    return 0;
}

function strat_bb_rsi($i, $d, $p)
{
    if ($i < 2) return 0;
    $c = $d['closes'];
    // Price near lower BB AND RSI oversold
    if ($c[$i] <= $d['bb20']['lower'][$i] * 1.01 && $d['rsi14'][$i] < 35) return 1;
    return 0;
}

// -- MOMENTUM --
function strat_rsi_momentum($i, $d, $p)
{
    $level = $p[0];
    if ($i < 3) return 0;
    $rsi = $d['rsi14'];
    if ($rsi[$i] > $level && $rsi[$i] > $rsi[$i-1] && $rsi[$i-1] > $rsi[$i-2]) return 1;
    return 0;
}

function strat_roc($i, $d, $p)
{
    $key = $p[0]; $threshold = $p[1];
    if (!isset($d[$key])) return 0;
    if ($i < 2) return 0;
    $roc = $d[$key];
    if ($roc[$i] > $threshold && $roc[$i] > $roc[$i-1]) return 1;
    return 0;
}

function strat_macd_mom($i, $d, $p)
{
    if ($i < 3) return 0;
    $h = $d['macd']['histogram'];
    if ($h[$i] > 0 && $h[$i] > $h[$i-1] && $h[$i-1] > $h[$i-2]) return 1;
    return 0;
}

function strat_price_mom($i, $d, $p)
{
    $lookback = $p[0];
    if ($i < $lookback + 1) return 0;
    $c = $d['closes'];
    $mom_pct = (($c[$i] - $c[$i - $lookback]) / $c[$i - $lookback]) * 100;
    $prev_mom = (($c[$i-1] - $c[$i - $lookback - 1]) / $c[$i - $lookback - 1]) * 100;
    if ($mom_pct > 2 && $mom_pct > $prev_mom) return 1;
    return 0;
}

function strat_vwap_mom($i, $d, $p)
{
    if ($i < 20) return 0;
    // Volume-weighted price vs SMA
    $vwap_sum = 0; $vol_sum = 0;
    for ($j = $i - 19; $j <= $i; $j++) {
        $vwap_sum += $d['closes'][$j] * $d['volumes'][$j];
        $vol_sum += $d['volumes'][$j];
    }
    $vwap = ($vol_sum > 0) ? $vwap_sum / $vol_sum : $d['closes'][$i];
    if ($d['closes'][$i] > $vwap && $d['closes'][$i] > $d['closes'][$i-1]) return 1;
    return 0;
}

function strat_stoch_cross($i, $d, $p)
{
    $key = $p[0];
    if (!isset($d[$key])) return 0;
    if ($i < 2) return 0;
    $k = $d[$key]['k']; $dd = $d[$key]['d'];
    if ($k[$i] > $dd[$i] && $k[$i-1] <= $dd[$i-1] && $k[$i] < 80) return 1;
    return 0;
}

function strat_elder_ray($i, $d, $p)
{
    if ($i < 2) return 0;
    $bull = $d['highs'][$i] - $d['ema21'][$i];
    $bull_prev = $d['highs'][$i-1] - $d['ema21'][$i-1];
    if ($bull > 0 && $bull > $bull_prev && $d['closes'][$i] > $d['ema21'][$i]) return 1;
    return 0;
}

function strat_obv_momentum($i, $d, $p)
{
    if ($i < 5) return 0;
    $obv = $d['obv'];
    $obv_ma = $d['obv_ema10'];
    if ($obv[$i] > $obv_ma[$i] && $d['closes'][$i] > $d['closes'][$i-1]) return 1;
    return 0;
}

function strat_adx_di($i, $d, $p)
{
    if ($i < 3) return 0;
    $adx = $d['adx14']['adx'];
    $pdi = $d['adx14']['plus_di'];
    $mdi = $d['adx14']['minus_di'];
    if ($adx[$i] > $adx[$i-1] && $pdi[$i] > $mdi[$i] && $pdi[$i-1] <= $mdi[$i-1]) return 1;
    return 0;
}

function strat_multi_mom($i, $d, $p)
{
    if ($i < 5) return 0;
    $score = 0;
    if ($d['rsi14'][$i] > 50 && $d['rsi14'][$i] > $d['rsi14'][$i-1]) $score++;
    if ($d['macd']['histogram'][$i] > 0) $score++;
    if ($d['roc10'][$i] > 0) $score++;
    if ($d['closes'][$i] > $d['ema21'][$i]) $score++;
    if ($d['stoch14']['k'][$i] > 50) $score++;
    if ($score >= 4) return 1;
    return 0;
}

// -- BREAKOUT --
function strat_atr_break($i, $d, $p)
{
    $mult = $p[0];
    if ($i < 2) return 0;
    $c = $d['closes'];
    $atr = $d['atr_arr'];
    if ($c[$i] > $d['sma20'][$i] + ($mult * $atr[$i]) && $c[$i-1] <= $d['sma20'][$i-1] + ($mult * $atr[$i-1])) return 1;
    return 0;
}

function strat_nbar_high($i, $d, $p)
{
    $period = $p[0];
    if ($i < $period + 1) return 0;
    $c = $d['closes']; $h = $d['highs'];
    $hh = 0;
    for ($j = $i - $period; $j < $i; $j++) { if ($h[$j] > $hh) $hh = $h[$j]; }
    if ($c[$i] > $hh && $c[$i-1] <= $hh) return 1;
    return 0;
}

function strat_bb_squeeze_vol($i, $d, $p)
{
    if ($i < 5) return 0;
    $bw = $d['bb20']['bandwidth'];
    $min_bw = 999;
    for ($j = $i - 5; $j < $i; $j++) { if ($bw[$j] < $min_bw) $min_bw = $bw[$j]; }
    $vol_ratio = ($d['vol_sma20'][$i] > 0) ? $d['volumes'][$i] / $d['vol_sma20'][$i] : 1;
    if ($bw[$i] > $min_bw * 1.5 && $vol_ratio > 1.5 && $d['closes'][$i] > $d['bb20']['middle'][$i]) return 1;
    return 0;
}

function strat_keltner_break($i, $d, $p)
{
    $mult = $p[0];
    if ($i < 2) return 0;
    $upper = $d['ema21'][$i] + ($mult * $d['atr_arr'][$i]);
    $upper_prev = $d['ema21'][$i-1] + ($mult * $d['atr_arr'][$i-1]);
    if ($d['closes'][$i] > $upper && $d['closes'][$i-1] <= $upper_prev) return 1;
    return 0;
}

function strat_inside_bar($i, $d, $p)
{
    if ($i < 3) return 0;
    $h = $d['highs']; $l = $d['lows']; $c = $d['closes'];
    // Bar i-1 is inside bar i-2 (range contained), then bar i breaks out upward
    if ($h[$i-1] < $h[$i-2] && $l[$i-1] > $l[$i-2] && $c[$i] > $h[$i-1]) return 1;
    return 0;
}

function strat_engulfing($i, $d, $p)
{
    if ($i < 2) return 0;
    $o = $d['opens']; $c = $d['closes'];
    // Bullish engulfing: prev was red, current is green and body engulfs prev
    $prev_red = ($c[$i-1] < $o[$i-1]);
    $curr_green = ($c[$i] > $o[$i]);
    if ($prev_red && $curr_green && $o[$i] <= $c[$i-1] && $c[$i] >= $o[$i-1]) return 1;
    return 0;
}

function strat_three_bar($i, $d, $p)
{
    if ($i < 3) return 0;
    $c = $d['closes']; $o = $d['opens'];
    // Three consecutive green candles with higher closes
    if ($c[$i] > $o[$i] && $c[$i-1] > $o[$i-1] && $c[$i-2] > $o[$i-2] && $c[$i] > $c[$i-1] && $c[$i-1] > $c[$i-2]) return 1;
    return 0;
}

function strat_range_contract($i, $d, $p)
{
    if ($i < 10) return 0;
    $h = $d['highs']; $l = $d['lows']; $c = $d['closes'];
    // Range contracting over last 5 bars, then expansion
    $ranges = array();
    for ($j = $i - 5; $j < $i; $j++) { $ranges[] = $h[$j] - $l[$j]; }
    $avg_range = array_sum($ranges) / 5;
    $current_range = $h[$i] - $l[$i];
    if ($current_range > $avg_range * 1.5 && $c[$i] > $d['sma20'][$i]) return 1;
    return 0;
}

function strat_vol_squeeze($i, $d, $p)
{
    if ($i < 10) return 0;
    $atr = $d['atr_arr'];
    // ATR compressed then expanding
    $min_atr = 999999;
    for ($j = $i - 5; $j < $i; $j++) { if ($atr[$j] < $min_atr) $min_atr = $atr[$j]; }
    if ($atr[$i] > $min_atr * 1.5 && $d['closes'][$i] > $d['ema21'][$i]) return 1;
    return 0;
}

function strat_turtle($i, $d, $p)
{
    $period = $p[0];
    if ($i < $period + 1) return 0;
    $h = $d['highs']; $c = $d['closes'];
    $hh = 0;
    for ($j = $i - $period; $j < $i; $j++) { if ($h[$j] > $hh) $hh = $h[$j]; }
    // Classic turtle: close above N-period high
    if ($c[$i] > $hh) return 1;
    return 0;
}

// -- VOLUME --
function strat_vol_spike($i, $d, $p)
{
    $mult = $p[0];
    if ($i < 2) return 0;
    $v = $d['volumes']; $vsma = $d['vol_sma20'];
    $c = $d['closes'];
    if ($vsma[$i] > 0 && $v[$i] > $vsma[$i] * $mult && $c[$i] > $c[$i-1]) return 1;
    return 0;
}

function strat_obv_trend($i, $d, $p)
{
    if ($i < 10) return 0;
    $obv = $d['obv'];
    $obv_ema = $d['obv_ema10'];
    // OBV above its EMA and rising for 3 bars
    if ($obv[$i] > $obv_ema[$i] && $obv[$i] > $obv[$i-1] && $obv[$i-1] > $obv[$i-2] && $d['closes'][$i] > $d['ema21'][$i]) return 1;
    return 0;
}

function strat_obv_divergence($i, $d, $p)
{
    if ($i < 10) return 0;
    $c = $d['closes']; $obv = $d['obv'];
    // Price making lower low but OBV making higher low (bullish divergence)
    $price_ll = ($c[$i] < $c[$i-5] && $c[$i-5] < $c[$i-10]);
    $obv_hl = ($obv[$i] > $obv[$i-5]);
    if ($price_ll && $obv_hl) return 1;
    return 0;
}

function strat_mfi_vol($i, $d, $p)
{
    if ($i < 2) return 0;
    $mfi = $d['mfi14'];
    $vol_ratio = ($d['vol_sma20'][$i] > 0) ? $d['volumes'][$i] / $d['vol_sma20'][$i] : 1;
    if ($mfi[$i] < 30 && $vol_ratio > 1.5 && $d['closes'][$i] > $d['closes'][$i-1]) return 1;
    return 0;
}

function strat_accumulation($i, $d, $p)
{
    if ($i < 10) return 0;
    $c = $d['closes']; $v = $d['volumes']; $vsma = $d['vol_sma20'];
    // Volume above average for 3+ bars but price barely moved (accumulation)
    $vol_above = 0;
    $price_range = abs($c[$i] - $c[$i-5]);
    $atr = $d['atr_arr'][$i];
    for ($j = $i - 4; $j <= $i; $j++) {
        if ($vsma[$j] > 0 && $v[$j] > $vsma[$j] * 1.2) $vol_above++;
    }
    if ($vol_above >= 3 && $price_range < $atr && $c[$i] > $c[$i-1]) return 1;
    return 0;
}

function strat_vol_profile($i, $d, $p)
{
    if ($i < 20) return 0;
    // Simplified volume profile: find price level with most volume in last 20 bars
    $c = $d['closes']; $v = $d['volumes'];
    $poc_price = 0; $poc_vol = 0;
    for ($j = $i - 19; $j <= $i; $j++) {
        if ($v[$j] > $poc_vol) { $poc_vol = $v[$j]; $poc_price = $c[$j]; }
    }
    // Price bouncing off POC
    if ($poc_price > 0 && abs($c[$i] - $poc_price) / $poc_price < 0.02 && $c[$i] > $c[$i-1]) return 1;
    return 0;
}

function strat_vwap_bounce($i, $d, $p)
{
    if ($i < 20) return 0;
    $c = $d['closes']; $v = $d['volumes'];
    $vwap_sum = 0; $vol_sum = 0;
    for ($j = $i - 19; $j <= $i; $j++) {
        $vwap_sum += $c[$j] * $v[$j];
        $vol_sum += $v[$j];
    }
    $vwap = ($vol_sum > 0) ? $vwap_sum / $vol_sum : $c[$i];
    // Price touches VWAP from above and bounces
    if ($d['lows'][$i] <= $vwap * 1.005 && $c[$i] > $vwap && $c[$i] > $c[$i-1]) return 1;
    return 0;
}

function strat_vol_climax($i, $d, $p)
{
    if ($i < 5) return 0;
    $v = $d['volumes']; $vsma = $d['vol_sma20']; $c = $d['closes'];
    // Huge volume bar (3x+) that was red, then next bar green → capitulation reversal
    if ($i >= 2 && $vsma[$i-1] > 0 && $v[$i-1] > $vsma[$i-1] * 3 && $c[$i-1] < $d['opens'][$i-1] && $c[$i] > $d['opens'][$i]) return 1;
    return 0;
}

// -- SMART MONEY / PRICE ACTION --
function strat_order_block($i, $d, $p)
{
    $lookback = $p[0];
    if ($i < $lookback + 2) return 0;
    $c = $d['closes']; $o = $d['opens']; $l = $d['lows'];
    // Find bullish order block: last bearish candle before a strong bullish move
    for ($j = $i - $lookback; $j < $i - 1; $j++) {
        $is_bearish = ($c[$j] < $o[$j]);
        $bullish_after = ($c[$j+1] > $o[$j+1]) && (($c[$j+1] - $o[$j+1]) > ($o[$j] - $c[$j]) * 2);
        if ($is_bearish && $bullish_after) {
            // Price returned to the OB zone
            $ob_top = $o[$j];
            $ob_bot = $c[$j];
            if ($l[$i] <= $ob_top && $c[$i] > $ob_top && $c[$i] > $c[$i-1]) return 1;
        }
    }
    return 0;
}

function strat_fvg($i, $d, $p)
{
    if ($i < 4) return 0;
    $h = $d['highs']; $l = $d['lows']; $c = $d['closes'];
    // Bullish FVG: gap between candle[i-2] high and candle[i] low
    for ($j = $i - 3; $j < $i; $j++) {
        if ($j < 2) continue;
        $gap_top = $l[$j + 2];
        $gap_bot = $h[$j];
        if ($gap_top > $gap_bot) {
            // FVG exists. Price filling the gap from above
            if ($c[$i] > $gap_bot && $l[$i] <= $gap_top && $c[$i] > $c[$i-1]) return 1;
        }
    }
    return 0;
}

function strat_liq_sweep($i, $d, $p)
{
    $period = $p[0];
    if ($i < $period + 2) return 0;
    $l = $d['lows']; $c = $d['closes'];
    // Find the lowest low in the lookback period
    $ll = 999999999;
    for ($j = $i - $period; $j < $i - 1; $j++) { if ($l[$j] < $ll) $ll = $l[$j]; }
    // Price swept below that low (liquidity grab) then reclaimed
    if ($l[$i-1] < $ll && $c[$i] > $ll && $c[$i] > $c[$i-1]) return 1;
    return 0;
}

function strat_bos($i, $d, $p)
{
    if ($i < 20) return 0;
    $h = $d['highs']; $c = $d['closes'];
    // Break of structure: price breaks above recent swing high
    $swing_high = 0;
    for ($j = $i - 10; $j < $i - 2; $j++) {
        if ($h[$j] > $h[$j-1] && $h[$j] > $h[$j+1] && $h[$j] > $swing_high) {
            $swing_high = $h[$j];
        }
    }
    if ($swing_high > 0 && $c[$i] > $swing_high && $c[$i-1] <= $swing_high) return 1;
    return 0;
}

function strat_demand_zone($i, $d, $p)
{
    if ($i < 20) return 0;
    $c = $d['closes']; $l = $d['lows']; $o = $d['opens'];
    // Find demand zone: area of strong bullish rejection in last 20 bars
    $demand_level = 0;
    for ($j = $i - 15; $j < $i - 2; $j++) {
        $body = abs($c[$j] - $o[$j]);
        $lower_wick = min($c[$j], $o[$j]) - $l[$j];
        if ($lower_wick > $body * 2 && $c[$j] > $o[$j]) {
            $demand_level = $l[$j];
        }
    }
    if ($demand_level > 0 && abs($l[$i] - $demand_level) / $demand_level < 0.02 && $c[$i] > $c[$i-1]) return 1;
    return 0;
}

function strat_hammer($i, $d, $p)
{
    if ($i < 2) return 0;
    $o = $d['opens']; $c = $d['closes']; $h = $d['highs']; $l = $d['lows'];
    $body = abs($c[$i] - $o[$i]);
    $lower_wick = min($c[$i], $o[$i]) - $l[$i];
    $upper_wick = $h[$i] - max($c[$i], $o[$i]);
    $total = $h[$i] - $l[$i];
    if ($total > 0 && $lower_wick > $body * 2 && $upper_wick < $body * 0.5 && $c[$i] > $o[$i]) return 1;
    return 0;
}

function strat_rejection_wick($i, $d, $p)
{
    if ($i < 2) return 0;
    $o = $d['opens']; $c = $d['closes']; $h = $d['highs']; $l = $d['lows'];
    $body = abs($c[$i] - $o[$i]);
    $lower_wick = min($c[$i], $o[$i]) - $l[$i];
    $total = $h[$i] - $l[$i];
    // Long lower wick = rejection of lower prices
    if ($total > 0 && $lower_wick / $total > 0.6 && $c[$i] > $o[$i]) return 1;
    return 0;
}

function strat_pin_bar($i, $d, $p)
{
    if ($i < 3) return 0;
    $o = $d['opens']; $c = $d['closes']; $h = $d['highs']; $l = $d['lows'];
    // Pin bar: very small body, long lower shadow, at a low point
    $body = abs($c[$i] - $o[$i]);
    $lower_wick = min($c[$i], $o[$i]) - $l[$i];
    $total = $h[$i] - $l[$i];
    if ($total > 0 && $body / $total < 0.2 && $lower_wick / $total > 0.65 && $l[$i] < $l[$i-1] && $l[$i] < $l[$i-2]) return 1;
    return 0;
}

// -- REGIME-BASED --
function strat_regime_rsi($i, $d, $p)
{
    $adx_thresh = $p[0];
    if ($i < 2) return 0;
    $adx = $d['adx14']['adx'];
    // In ranging market (low ADX), use RSI mean reversion
    if ($adx[$i] < $adx_thresh && $d['rsi14'][$i-1] < 30 && $d['rsi14'][$i] >= 30) return 1;
    return 0;
}

function strat_regime_mom($i, $d, $p)
{
    $adx_thresh = $p[0];
    if ($i < 2) return 0;
    $adx = $d['adx14']['adx'];
    $pdi = $d['adx14']['plus_di'];
    $mdi = $d['adx14']['minus_di'];
    // In trending market (high ADX), use momentum
    if ($adx[$i] > $adx_thresh && $pdi[$i] > $mdi[$i] && $d['macd']['histogram'][$i] > 0 && $d['rsi14'][$i] > 50) return 1;
    return 0;
}

function strat_regime_break($i, $d, $p)
{
    if ($i < 10) return 0;
    $adx = $d['adx14']['adx'];
    $bw = $d['bb20']['bandwidth'];
    // Regime shift: from squeeze (low BW + low ADX) to trend (expanding + ADX rising)
    $was_squeeze = ($bw[$i-3] < $bw[$i-5]) && ($adx[$i-3] < 20);
    $now_breaking = ($bw[$i] > $bw[$i-1]) && ($adx[$i] > $adx[$i-1]) && ($d['closes'][$i] > $d['bb20']['upper'][$i-1]);
    if ($was_squeeze && $now_breaking) return 1;
    return 0;
}

function strat_adaptive($i, $d, $p)
{
    if ($i < 5) return 0;
    $adx = $d['adx14']['adx'];
    // Switch between mean reversion and trend following based on regime
    if ($adx[$i] < 25) {
        // Mean reversion mode
        if ($d['rsi14'][$i-1] < 30 && $d['rsi14'][$i] >= 30 && $d['closes'][$i] <= $d['bb20']['lower'][$i] * 1.02) return 1;
    } else {
        // Trend following mode
        if ($d['ema9'][$i] > $d['ema21'][$i] && $d['ema9'][$i-1] <= $d['ema21'][$i-1] && $d['macd']['histogram'][$i] > 0) return 1;
    }
    return 0;
}

// -- CONFLUENCE / COMPOSITE --
function strat_triple_confirm($i, $d, $p)
{
    if ($i < 2) return 0;
    $rsi_ok = ($d['rsi14'][$i] > 40 && $d['rsi14'][$i] < 70);
    $macd_ok = ($d['macd']['histogram'][$i] > 0 && $d['macd']['line'][$i] > $d['macd']['signal'][$i]);
    $ema_ok = ($d['ema9'][$i] > $d['ema21'][$i] && $d['ema9'][$i-1] <= $d['ema21'][$i-1]);
    if ($rsi_ok && $macd_ok && $ema_ok) return 1;
    return 0;
}

function strat_bvr_combo($i, $d, $p)
{
    if ($i < 2) return 0;
    $c = $d['closes'];
    $near_lower_bb = ($c[$i] <= $d['bb20']['lower'][$i] * 1.02);
    $rsi_low = ($d['rsi14'][$i] < 40);
    $vol_up = ($d['vol_sma20'][$i] > 0 && $d['volumes'][$i] > $d['vol_sma20'][$i] * 1.3);
    $recovering = ($c[$i] > $c[$i-1]);
    if ($near_lower_bb && $rsi_low && $vol_up && $recovering) return 1;
    return 0;
}

function strat_break_vol_rsi($i, $d, $p)
{
    if ($i < 20) return 0;
    $c = $d['closes']; $h = $d['highs'];
    $hh = 0;
    for ($j = $i - 20; $j < $i; $j++) { if ($h[$j] > $hh) $hh = $h[$j]; }
    $breakout = ($c[$i] > $hh);
    $vol_ok = ($d['vol_sma20'][$i] > 0 && $d['volumes'][$i] > $d['vol_sma20'][$i] * 1.5);
    $rsi_ok = ($d['rsi14'][$i] > 50 && $d['rsi14'][$i] < 80);
    if ($breakout && $vol_ok && $rsi_ok) return 1;
    return 0;
}

function strat_trend_mr($i, $d, $p)
{
    if ($i < 2) return 0;
    // In uptrend (price > SMA50), use mean reversion on RSI dips
    if ($d['closes'][$i] > $d['sma50'][$i] && $d['rsi14'][$i-1] < 35 && $d['rsi14'][$i] >= 35) return 1;
    return 0;
}

function strat_5ind_score($i, $d, $p)
{
    $threshold = $p[0];
    if ($i < 5) return 0;
    $score = 0;
    // 1. EMA trend
    if ($d['ema9'][$i] > $d['ema21'][$i]) $score++;
    // 2. MACD positive
    if ($d['macd']['histogram'][$i] > 0) $score++;
    // 3. RSI healthy
    if ($d['rsi14'][$i] > 45 && $d['rsi14'][$i] < 75) $score++;
    // 4. Volume above average
    if ($d['vol_sma20'][$i] > 0 && $d['volumes'][$i] > $d['vol_sma20'][$i]) $score++;
    // 5. Price above BB middle
    if ($d['closes'][$i] > $d['bb20']['middle'][$i]) $score++;
    if ($score >= $threshold) return 1;
    return 0;
}

function strat_tema_vol($i, $d, $p)
{
    if ($i < 2) return 0;
    // TEMA cross (approximated via double-smoothed EMA) + volume surge
    $tema_fast = 3 * $d['ema9'][$i] - 3 * $d['ema12'][$i] + $d['ema21'][$i];
    $tema_slow = 3 * $d['ema21'][$i] - 3 * $d['ema26'][$i] + $d['ema50'][$i];
    $tema_fast_prev = 3 * $d['ema9'][$i-1] - 3 * $d['ema12'][$i-1] + $d['ema21'][$i-1];
    $tema_slow_prev = 3 * $d['ema21'][$i-1] - 3 * $d['ema26'][$i-1] + $d['ema50'][$i-1];
    $vol_surge = ($d['vol_sma20'][$i] > 0 && $d['volumes'][$i] > $d['vol_sma20'][$i] * 1.5);
    if ($tema_fast > $tema_slow && $tema_fast_prev <= $tema_slow_prev && $vol_surge) return 1;
    return 0;
}

function strat_rsi_div_vol($i, $d, $p)
{
    if ($i < 10) return 0;
    $c = $d['closes']; $rsi = $d['rsi14'];
    // RSI divergence: price lower low but RSI higher low + volume confirmation
    $price_ll = ($c[$i] < $c[$i-5]);
    $rsi_hl = ($rsi[$i] > $rsi[$i-5]);
    $rsi_low = ($rsi[$i] < 40);
    $vol_ok = ($d['vol_sma20'][$i] > 0 && $d['volumes'][$i] > $d['vol_sma20'][$i]);
    if ($price_ll && $rsi_hl && $rsi_low && $vol_ok && $c[$i] > $c[$i-1]) return 1;
    return 0;
}

function strat_smc_mom($i, $d, $p)
{
    if ($i < 10) return 0;
    // Smart money structure + momentum confirmation
    $c = $d['closes']; $l = $d['lows']; $h = $d['highs'];
    // Check for liquidity sweep
    $ll = 999999999;
    for ($j = $i - 10; $j < $i - 1; $j++) { if ($l[$j] < $ll) $ll = $l[$j]; }
    $swept = ($l[$i-1] < $ll);
    $reclaimed = ($c[$i] > $ll);
    $momentum_ok = ($d['macd']['histogram'][$i] > 0 && $d['rsi14'][$i] > 40);
    if ($swept && $reclaimed && $momentum_ok) return 1;
    return 0;
}

function strat_ultimate($i, $d, $p)
{
    if ($i < 10) return 0;
    $score = 0;
    // 1. Trend: EMA alignment
    if ($d['ema9'][$i] > $d['ema21'][$i] && $d['ema21'][$i] > $d['ema55'][$i]) $score++;
    // 2. Momentum: MACD bullish
    if ($d['macd']['histogram'][$i] > 0 && $d['macd']['histogram'][$i] > $d['macd']['histogram'][$i-1]) $score++;
    // 3. RSI confirmation
    if ($d['rsi14'][$i] > 45 && $d['rsi14'][$i] < 75) $score++;
    // 4. Volume above average
    if ($d['vol_sma20'][$i] > 0 && $d['volumes'][$i] > $d['vol_sma20'][$i] * 1.2) $score++;
    // 5. OBV rising
    if ($d['obv'][$i] > $d['obv_ema10'][$i]) $score++;
    // 6. ADX trend strength
    if ($d['adx14']['adx'][$i] > 20) $score++;
    // 7. Price above BB middle
    if ($d['closes'][$i] > $d['bb20']['middle'][$i]) $score++;

    if ($score >= 5) return 1;
    return 0;
}

// ═══════════════════════════════════════════════════════════════════
//  UTILITY
// ═══════════════════════════════════════════════════════════════════
function _require_key()
{
    global $API_KEY;
    $k = isset($_GET['key']) ? $_GET['key'] : '';
    if ($k !== $API_KEY) {
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        exit;
    }
}
?>
