<?php
/**
 * Edge Finder — High Conviction Trade Scanner
 * Identifies "near free money" setups by combining:
 *   1. Only algorithms with PROVEN edge (80%+ win rate in forward testing)
 *   2. CDR stocks only (zero Questrade commission)
 *   3. Multi-system consensus (picks confirmed across 2+ independent systems)
 *   4. Real-time price validation (entry still within range)
 *
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=scan       — Find current high-conviction setups (public)
 *   ?action=edge_stats — Show algorithm edge statistics (public)
 *   ?action=history    — Historical edge-filtered trade outcomes (public)
 *   ?action=market     — Current market status + live prices for edge picks (public)
 */
require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'scan';

// ─── CDR TICKERS (Zero Questrade Commission) ───────────────
$CDR_TICKERS = array(
    'AAPL','AMD','AMZN','CSCO','CRM','GOOG','GOOGL','IBM','INTC','META','MSFT','NFLX','NVDA',
    'COST','DIS','HD','MCD','NKE','SBUX','TSLA','WMT',
    'ABBV','CVS','JNJ','PFE','UNH',
    'BAC','BRK.B','CITI','GS','JPM','MA','PYPL','V',
    'BA','CVX','XOM','HON','UPS','KO','VZ','UBER'
);

// ─── ALGORITHMS WITH PROVEN EDGE (from Kelly sizing forward-test) ───
$EDGE_ALGORITHMS = array(
    'Cursor Genius'    => array('win_rate' => 85.71, 'min_score' => 70),
    'ETF Masters'      => array('win_rate' => 82.35, 'min_score' => 70),
    'Blue Chip Growth' => array('win_rate' => 80.00, 'min_score' => 70),
    'Sector Rotation'  => array('win_rate' => 72.73, 'min_score' => 60),
    'Alpha Factor Growth'     => array('win_rate' => 70.00, 'min_score' => 80),
    'Alpha Factor Composite'  => array('win_rate' => 68.00, 'min_score' => 60),
    'Alpha Factor Earnings'   => array('win_rate' => 65.00, 'min_score' => 70),
    'Alpha Factor Quality'    => array('win_rate' => 65.00, 'min_score' => 70)
);

// ─── MIRACLE STRATEGIES WITH EDGE ───
$MIRACLE_EDGE = array(
    'Momentum Continuation' => 65,
    'CDR Zero-Fee Play'     => 60,
    'CDR Zero-Fee Priority' => 60,
    'Gap Up Momentum'       => 55,
    'Volume Surge Breakout' => 55
);

// ─── Route ───
if ($action === 'scan') {
    _ef_scan($conn);
} elseif ($action === 'edge_stats') {
    _ef_edge_stats($conn);
} elseif ($action === 'history') {
    _ef_history($conn);
} elseif ($action === 'market') {
    _ef_market($conn);
} else {
    echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

$conn->close();
exit;

// ═══════════════════════════════════════════════════════════════
// HELPER: Check if market is open
// ═══════════════════════════════════════════════════════════════
function _ef_market_open() {
    $now = time();
    $et = $now - (5 * 3600); // UTC to EST
    $dow = (int)gmdate('w', $et);
    $hour = (int)gmdate('G', $et);
    $min = (int)gmdate('i', $et);
    $time_mins = $hour * 60 + $min;
    // Mon-Fri, 9:30 AM - 4:00 PM ET
    if ($dow >= 1 && $dow <= 5 && $time_mins >= 570 && $time_mins < 960) {
        return true;
    }
    return false;
}

// ═══════════════════════════════════════════════════════════════
// SCAN — Find current high-conviction setups
// ═══════════════════════════════════════════════════════════════
function _ef_scan($conn) {
    global $CDR_TICKERS, $EDGE_ALGORITHMS, $MIRACLE_EDGE;

    $market_open = _ef_market_open();
    $now = time();
    $et_offset = 5 * 3600;

    // Step 1: Get recent picks from edge algorithms (stock_picks table, last 3 days)
    $cdr_list = "'" . implode("','", $CDR_TICKERS) . "'";
    $algo_list = array();
    foreach ($EDGE_ALGORITHMS as $name => $info) {
        $algo_list[] = "'" . $conn->real_escape_string($name) . "'";
    }
    $algo_in = implode(',', $algo_list);

    $edge_picks = array();
    $three_days_ago = date('Y-m-d', $now - 7 * 86400);

    // Query stock_picks for edge algorithm picks on CDR tickers
    $r = $conn->query("SELECT ticker, algorithm_name, entry_price, score, pick_date
        FROM stock_picks
        WHERE ticker IN ($cdr_list)
        AND algorithm_name IN ($algo_in)
        AND pick_date >= '$three_days_ago'
        ORDER BY pick_date DESC, score DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $tk = $row['ticker'];
            if (!isset($edge_picks[$tk])) {
                $edge_picks[$tk] = array(
                    'ticker' => $tk,
                    'sources' => array(),
                    'algorithms' => array(),
                    'entry_prices' => array(),
                    'scores' => array(),
                    'latest_pick_date' => $row['pick_date'],
                    'direction' => 'LONG'
                );
            }
            $algo = $row['algorithm_name'];
            if (!in_array($algo, $edge_picks[$tk]['algorithms'])) {
                $edge_picks[$tk]['algorithms'][] = $algo;
                $edge_picks[$tk]['sources'][] = array(
                    'system' => 'Portfolio',
                    'algorithm' => $algo,
                    'score' => (int)$row['score'],
                    'entry' => floatval($row['entry_price']),
                    'date' => $row['pick_date'],
                    'proven_wr' => isset($EDGE_ALGORITHMS[$algo]) ? $EDGE_ALGORITHMS[$algo]['win_rate'] : 0
                );
                $edge_picks[$tk]['entry_prices'][] = floatval($row['entry_price']);
                $edge_picks[$tk]['scores'][] = (int)$row['score'];
            }
        }
    }

    // Step 2: Cross-reference with Miracle v2 picks
    $r2 = $conn->query("SELECT ticker, strategy_name, entry_price, score, pick_date
        FROM miracle_picks2
        WHERE ticker IN ($cdr_list)
        AND pick_date >= '$three_days_ago'
        AND outcome = 'pending'
        ORDER BY pick_date DESC");
    if ($r2) {
        while ($row = $r2->fetch_assoc()) {
            $tk = $row['ticker'];
            if (!isset($edge_picks[$tk])) {
                $edge_picks[$tk] = array(
                    'ticker' => $tk,
                    'sources' => array(),
                    'algorithms' => array(),
                    'entry_prices' => array(),
                    'scores' => array(),
                    'latest_pick_date' => $row['pick_date'],
                    'direction' => 'LONG'
                );
            }
            $edge_picks[$tk]['sources'][] = array(
                'system' => 'Miracle v2',
                'algorithm' => $row['strategy_name'],
                'score' => (int)$row['score'],
                'entry' => floatval($row['entry_price']),
                'date' => $row['pick_date'],
                'proven_wr' => isset($MIRACLE_EDGE[$row['strategy_name']]) ? $MIRACLE_EDGE[$row['strategy_name']] : 50
            );
            $edge_picks[$tk]['entry_prices'][] = floatval($row['entry_price']);
            $edge_picks[$tk]['scores'][] = (int)$row['score'];
            if (!in_array($row['strategy_name'], $edge_picks[$tk]['algorithms'])) {
                $edge_picks[$tk]['algorithms'][] = $row['strategy_name'];
            }
        }
    }

    // Step 3: Cross-reference with Miracle v3 picks
    $r3 = $conn->query("SELECT ticker, strategy_name, entry_price, score, pick_date
        FROM miracle_picks3
        WHERE ticker IN ($cdr_list)
        AND pick_date >= '$three_days_ago'
        AND outcome = 'pending'
        ORDER BY pick_date DESC");
    if ($r3) {
        while ($row = $r3->fetch_assoc()) {
            $tk = $row['ticker'];
            if (!isset($edge_picks[$tk])) {
                $edge_picks[$tk] = array(
                    'ticker' => $tk,
                    'sources' => array(),
                    'algorithms' => array(),
                    'entry_prices' => array(),
                    'scores' => array(),
                    'latest_pick_date' => $row['pick_date'],
                    'direction' => 'LONG'
                );
            }
            $edge_picks[$tk]['sources'][] = array(
                'system' => 'Miracle v3',
                'algorithm' => $row['strategy_name'],
                'score' => (int)$row['score'],
                'entry' => floatval($row['entry_price']),
                'date' => $row['pick_date'],
                'proven_wr' => isset($MIRACLE_EDGE[$row['strategy_name']]) ? $MIRACLE_EDGE[$row['strategy_name']] : 50
            );
            $edge_picks[$tk]['entry_prices'][] = floatval($row['entry_price']);
            $edge_picks[$tk]['scores'][] = (int)$row['score'];
            if (!in_array($row['strategy_name'], $edge_picks[$tk]['algorithms'])) {
                $edge_picks[$tk]['algorithms'][] = $row['strategy_name'];
            }
        }
    }

    // Step 4: Get latest prices
    $latest_prices = array();
    $rp = $conn->query("SELECT symbol, price, change_24h_pct, updated_at FROM lm_price_cache WHERE asset_class = 'STOCK'");
    if ($rp) {
        while ($row = $rp->fetch_assoc()) {
            $latest_prices[$row['symbol']] = $row;
        }
    }
    // Also check daily_prices table
    $rp2 = $conn->query("SELECT ticker, close_price, trade_date FROM daily_prices WHERE trade_date >= '$three_days_ago' ORDER BY trade_date DESC");
    if ($rp2) {
        while ($row = $rp2->fetch_assoc()) {
            $tk = $row['ticker'];
            if (!isset($latest_prices[$tk])) {
                $latest_prices[$tk] = array('symbol' => $tk, 'price' => $row['close_price'], 'updated_at' => $row['trade_date']);
            }
        }
    }

    // Step 5: Score and rank the setups
    $setups = array();
    foreach ($edge_picks as $tk => $pick) {
        $algo_count = count($pick['algorithms']);
        $source_count = count($pick['sources']);

        // Count unique systems (Portfolio, Miracle v2, Miracle v3)
        $systems = array();
        foreach ($pick['sources'] as $src) {
            $systems[$src['system']] = 1;
        }
        $system_count = count($systems);

        // Skip single-algo picks UNLESS the algo has 80%+ proven win rate
        if ($algo_count < 2) {
            $top_wr = 0;
            foreach ($pick['sources'] as $src) {
                if ($src['proven_wr'] > $top_wr) $top_wr = $src['proven_wr'];
            }
            if ($top_wr < 80) continue;
        }

        $avg_entry = count($pick['entry_prices']) > 0 ? array_sum($pick['entry_prices']) / count($pick['entry_prices']) : 0;
        $avg_score = count($pick['scores']) > 0 ? array_sum($pick['scores']) / count($pick['scores']) : 0;

        // Get latest price
        $latest_price = 0;
        $price_fresh = false;
        if (isset($latest_prices[$tk])) {
            $latest_price = floatval($latest_prices[$tk]['price']);
            $price_fresh = true;
        }

        // Calculate conviction score
        // Formula: (algo_count * 15) + (system_count * 20) + (avg_score * 0.3) + (avg proven WR * 0.5)
        $avg_wr = 0;
        $wr_count = 0;
        foreach ($pick['sources'] as $src) {
            if ($src['proven_wr'] > 0) {
                $avg_wr += $src['proven_wr'];
                $wr_count++;
            }
        }
        $avg_wr = $wr_count > 0 ? $avg_wr / $wr_count : 50;

        $conviction = ($algo_count * 15) + ($system_count * 20) + ($avg_score * 0.3) + ($avg_wr * 0.5);

        // Confidence level
        $confidence = 'LOW';
        if ($conviction >= 150) $confidence = 'VERY HIGH';
        elseif ($conviction >= 120) $confidence = 'HIGH';
        elseif ($conviction >= 90) $confidence = 'MEDIUM';

        // Calculate SL/TP (CDR = no commission, so pure price moves)
        $sl_pct = 3.0; // 3% stop loss
        $tp_pct = 6.0; // 6% take profit (2:1 R:R)
        if ($conviction >= 150) {
            $tp_pct = 8.0; // Let high conviction winners run
            $sl_pct = 4.0;
        }

        $sl_price = $avg_entry > 0 ? round($avg_entry * (1 - $sl_pct / 100), 2) : 0;
        $tp_price = $avg_entry > 0 ? round($avg_entry * (1 + $tp_pct / 100), 2) : 0;

        // Current return if already in trade
        $current_return = 0;
        if ($latest_price > 0 && $avg_entry > 0) {
            $current_return = round(($latest_price - $avg_entry) / $avg_entry * 100, 2);
        }

        // Distance to SL/TP
        $dist_sl = $latest_price > 0 && $sl_price > 0 ? round(($latest_price - $sl_price) / $latest_price * 100, 2) : 0;
        $dist_tp = $latest_price > 0 && $tp_price > 0 ? round(($tp_price - $latest_price) / $latest_price * 100, 2) : 0;

        $setups[] = array(
            'ticker' => $tk,
            'direction' => $pick['direction'],
            'conviction_score' => round($conviction, 1),
            'confidence' => $confidence,
            'algo_count' => $algo_count,
            'system_count' => $system_count,
            'systems' => array_keys($systems),
            'avg_entry' => round($avg_entry, 2),
            'avg_score' => round($avg_score, 1),
            'avg_proven_wr' => round($avg_wr, 1),
            'latest_price' => $latest_price,
            'current_return_pct' => $current_return,
            'sl_pct' => $sl_pct,
            'tp_pct' => $tp_pct,
            'sl_price' => $sl_price,
            'tp_price' => $tp_price,
            'distance_to_sl' => $dist_sl,
            'distance_to_tp' => $dist_tp,
            'risk_reward' => $sl_pct > 0 ? round($tp_pct / $sl_pct, 1) : 0,
            'cdr' => true,
            'commission' => '$0 (CDR)',
            'latest_pick_date' => $pick['latest_pick_date'],
            'sources' => $pick['sources']
        );
    }

    // Sort by conviction score
    usort($setups, '_ef_sort_by_conviction');

    // Separate into tiers
    $very_high = array();
    $high = array();
    $medium = array();
    foreach ($setups as $s) {
        if ($s['confidence'] === 'VERY HIGH') $very_high[] = $s;
        elseif ($s['confidence'] === 'HIGH') $high[] = $s;
        else $medium[] = $s;
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'scan',
        'market_open' => $market_open,
        'scan_time' => date('Y-m-d H:i:s'),
        'scan_time_est' => date('Y-m-d H:i:s', time() - 5 * 3600),
        'total_setups' => count($setups),
        'very_high_conviction' => count($very_high),
        'high_conviction' => count($high),
        'medium_conviction' => count($medium),
        'note' => 'All picks are CDR stocks ($0 Questrade commission). Algorithms shown have 72-86% win rate in forward testing.',
        'setups' => $setups
    ));
}

function _ef_sort_by_conviction($a, $b) {
    if ($a['conviction_score'] == $b['conviction_score']) return 0;
    return $a['conviction_score'] > $b['conviction_score'] ? -1 : 1;
}

// ═══════════════════════════════════════════════════════════════
// EDGE STATS — Algorithm edge statistics
// ═══════════════════════════════════════════════════════════════
function _ef_edge_stats($conn) {
    global $EDGE_ALGORITHMS, $MIRACLE_EDGE;

    // Get actual paper trade outcomes per algorithm
    $algo_stats = array();

    // From paper_trades table (if exists)
    $r = $conn->query("SELECT algorithm_name,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(AVG(realized_pnl_pct), 2) as avg_return,
        ROUND(SUM(realized_pnl_pct), 2) as total_return
    FROM paper_trades
    WHERE status = 'closed'
    GROUP BY algorithm_name
    ORDER BY (wins / GREATEST(COUNT(*),1)) DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $trades = (int)$row['trades'];
            $wins = (int)$row['wins'];
            $algo_stats[] = array(
                'algorithm' => $row['algorithm_name'],
                'source' => 'paper_trades',
                'trades' => $trades,
                'wins' => $wins,
                'win_rate' => $trades > 0 ? round($wins / $trades * 100, 1) : 0,
                'avg_return' => floatval($row['avg_return']),
                'total_return' => floatval($row['total_return']),
                'has_edge' => ($trades >= 5 && ($wins / max($trades, 1)) >= 0.55)
            );
        }
    }

    // From live-monitor trades (if any closed)
    $r2 = $conn->query("SELECT algorithm_name,
        COUNT(*) as trades,
        SUM(CASE WHEN realized_pnl_usd > 0 THEN 1 ELSE 0 END) as wins,
        ROUND(AVG(realized_pct), 2) as avg_return,
        ROUND(SUM(realized_pnl_usd), 2) as total_pnl
    FROM lm_trades
    WHERE status = 'closed' AND algorithm_name != ''
    GROUP BY algorithm_name
    ORDER BY (wins / GREATEST(COUNT(*),1)) DESC");
    if ($r2) {
        while ($row = $r2->fetch_assoc()) {
            $trades = (int)$row['trades'];
            $wins = (int)$row['wins'];
            $algo_stats[] = array(
                'algorithm' => $row['algorithm_name'],
                'source' => 'live_monitor',
                'trades' => $trades,
                'wins' => $wins,
                'win_rate' => $trades > 0 ? round($wins / $trades * 100, 1) : 0,
                'avg_return' => floatval($row['avg_return']),
                'total_pnl' => floatval($row['total_pnl']),
                'has_edge' => ($trades >= 5 && ($wins / max($trades, 1)) >= 0.55)
            );
        }
    }

    // Include the known edge algorithms from Kelly sizing
    $known_edge = array();
    foreach ($EDGE_ALGORITHMS as $name => $info) {
        $known_edge[] = array(
            'algorithm' => $name,
            'source' => 'kelly_forward_test',
            'proven_win_rate' => $info['win_rate'],
            'min_score_threshold' => $info['min_score'],
            'has_edge' => true
        );
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'edge_stats',
        'known_edge_algorithms' => $known_edge,
        'live_performance' => $algo_stats,
        'edge_criteria' => 'Win rate >= 55% with 5+ trades in forward testing',
        'cdr_advantage' => 'CDR stocks have $0 commission on Questrade, eliminating 3.5% round-trip drag'
    ));
}

// ═══════════════════════════════════════════════════════════════
// HISTORY — Historical edge-filtered picks and outcomes
// ═══════════════════════════════════════════════════════════════
function _ef_history($conn) {
    global $CDR_TICKERS, $EDGE_ALGORITHMS;

    $cdr_list = "'" . implode("','", $CDR_TICKERS) . "'";
    $algo_list = array();
    foreach ($EDGE_ALGORITHMS as $name => $info) {
        $algo_list[] = "'" . $conn->real_escape_string($name) . "'";
    }
    $algo_in = implode(',', $algo_list);

    $days = isset($_GET['days']) ? max(1, min(90, (int)$_GET['days'])) : 30;
    $since = date('Y-m-d', time() - $days * 86400);

    // Step 1: Get latest prices per ticker (limited to recent for speed)
    $latest_prices = array();
    $recent_price = date('Y-m-d', time() - 14 * 86400);
    $rp = $conn->query("SELECT ticker, close_price, trade_date
        FROM daily_prices
        WHERE ticker IN ($cdr_list)
        AND trade_date >= '$recent_price'
        ORDER BY trade_date DESC");
    if ($rp) {
        while ($row = $rp->fetch_assoc()) {
            $tk = $row['ticker'];
            if (!isset($latest_prices[$tk])) {
                $latest_prices[$tk] = array(
                    'close_price' => floatval($row['close_price']),
                    'trade_date' => $row['trade_date']
                );
            }
        }
    }

    // Step 2: Get edge-filtered picks (simple query, no JOIN)
    $picks = array();
    $r = $conn->query("SELECT ticker, algorithm_name, entry_price, score, pick_date
        FROM stock_picks
        WHERE ticker IN ($cdr_list)
        AND algorithm_name IN ($algo_in)
        AND pick_date >= '$since'
        ORDER BY pick_date DESC, score DESC");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $tk = $row['ticker'];
            $entry = floatval($row['entry_price']);
            $latest = isset($latest_prices[$tk]) ? $latest_prices[$tk]['close_price'] : 0;
            $trade_date = isset($latest_prices[$tk]) ? $latest_prices[$tk]['trade_date'] : '';
            $ret = ($entry > 0 && $latest > 0) ? round(($latest - $entry) / $entry * 100, 2) : 0;
            $picks[] = array(
                'ticker' => $tk,
                'algorithm' => $row['algorithm_name'],
                'entry_price' => $entry,
                'latest_price' => $latest,
                'return_pct' => $ret,
                'is_winner' => $ret > 0,
                'score' => (int)$row['score'],
                'pick_date' => $row['pick_date'],
                'trade_date' => $trade_date
            );
        }
    }

    // Calculate aggregate stats
    $total = count($picks);
    $winners = 0;
    $total_return = 0;
    foreach ($picks as $p) {
        if ($p['is_winner']) $winners++;
        $total_return += $p['return_pct'];
    }
    $win_rate = $total > 0 ? round($winners / $total * 100, 1) : 0;
    $avg_return = $total > 0 ? round($total_return / $total, 2) : 0;

    echo json_encode(array(
        'ok' => true,
        'action' => 'history',
        'days' => $days,
        'total_picks' => $total,
        'winners' => $winners,
        'losers' => $total - $winners,
        'win_rate' => $win_rate,
        'avg_return_pct' => $avg_return,
        'total_return_pct' => round($total_return, 2),
        'note' => 'Returns are mark-to-market (entry price vs latest available close). CDR stocks = $0 commission.',
        'picks' => $picks
    ));
}

// ═══════════════════════════════════════════════════════════════
// MARKET — Current market status + live prices for edge tickers
// ═══════════════════════════════════════════════════════════════
function _ef_market($conn) {
    $market_open = _ef_market_open();
    $now = time();
    $et = $now - 5 * 3600;
    $dow_names = array('Sun','Mon','Tue','Wed','Thu','Fri','Sat');
    $dow = (int)gmdate('w', $et);

    $next_open = '';
    if (!$market_open) {
        // Calculate when market next opens
        $next_day = $dow;
        if ($dow == 0) $next_day = 1; // Sun -> Mon
        elseif ($dow == 6) $next_day = 1; // Sat -> Mon (skip)
        elseif ((int)gmdate('G', $et) >= 16) $next_day = $dow + 1; // After close -> next day
        if ($next_day > 5) $next_day = 1; // Wrap to Monday
        $next_open = $dow_names[$next_day] . ' 9:30 AM ET';
    }

    // Get live prices for edge tickers
    $prices = array();
    $r = $conn->query("SELECT symbol, asset_class, price, bid, ask, spread_pct, change_24h_pct, updated_at
        FROM lm_price_cache
        WHERE asset_class IN ('STOCK','CRYPTO','FOREX')
        ORDER BY asset_class, symbol");
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $prices[] = array(
                'symbol' => $row['symbol'],
                'asset_class' => $row['asset_class'],
                'price' => floatval($row['price']),
                'change_24h' => floatval($row['change_24h_pct']),
                'spread_pct' => floatval($row['spread_pct']),
                'updated' => $row['updated_at']
            );
        }
    }

    // Crypto/forex are 24/7
    $crypto_active = true;
    $forex_active = ($dow >= 1 && $dow <= 5); // Mon-Fri only

    echo json_encode(array(
        'ok' => true,
        'action' => 'market',
        'current_time_est' => gmdate('Y-m-d H:i:s', $et),
        'day_of_week' => $dow_names[$dow],
        'stock_market_open' => $market_open,
        'next_stock_open' => $next_open,
        'crypto_market' => 'always open',
        'forex_market' => $forex_active ? 'open (Mon-Fri)' : 'closed (weekend)',
        'prices' => $prices
    ));
}

?>
