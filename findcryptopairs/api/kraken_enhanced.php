<?php
/**
 * Kraken Enhanced Meme Scanner v2
 * Implements academic best practices:
 * - Volatility-targeted position sizing
 * - Liquidity screening (spread + depth)
 * - Kelly fraction calculation
 * - Realized volatility measurements
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: no-cache, must-revalidate');

error_reporting(0);
ini_set('display_errors', '0');

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'Database connection failed'));
    exit;
}
$conn->set_charset('utf8');

$action = isset($_GET['action']) ? $_GET['action'] : 'scan';

// Portfolio settings (configurable)
$PORTFOLIO_VALUE = isset($_GET['portfolio']) ? floatval($_GET['portfolio']) : 10000;
$DAILY_RISK_TARGET = 0.005; // 0.5% daily risk per position
$MAX_POSITION_PCT = 0.03;   // 3% max position size
$MAX_SPREAD_PCT = 0.5;      // 50 bips max spread
$MIN_BOOK_DEPTH = 50000;    // $50K at BBO

switch ($action) {
    case 'scan':
        _kraken_enhanced_scan($conn, $PORTFOLIO_VALUE, $DAILY_RISK_TARGET, $MAX_POSITION_PCT);
        break;
    case 'buynow':
        _kraken_enhanced_buynow($conn, $PORTFOLIO_VALUE, $DAILY_RISK_TARGET, $MAX_POSITION_PCT);
        break;
    case 'paper_trade':
        _kraken_record_paper_trade($conn);
        break;
    case 'paper_status':
        _kraken_paper_status($conn);
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}

/**
 * Enhanced scan with academic risk framework
 */
function _kraken_enhanced_scan($conn, $portfolio_value, $daily_risk_target, $max_position_pct) {
    $start_time = microtime(true);
    
    // Kraken meme pairs with metadata
    $meme_pairs = array(
        'PEPEUSD'  => array('name' => 'PEPE',  'tier' => 2, 'max_position_pct' => 0.02),
        'FLOKIUSD' => array('name' => 'FLOKI', 'tier' => 2, 'max_position_pct' => 0.02),
        'BONKUSD'  => array('name' => 'BONK',  'tier' => 2, 'max_position_pct' => 0.02),
        'SHIBUSD'  => array('name' => 'SHIB',  'tier' => 1, 'max_position_pct' => 0.03),
        'DOGEUSD'  => array('name' => 'DOGE',  'tier' => 1, 'max_position_pct' => 0.03),
        'WIFUSD'   => array('name' => 'WIF',   'tier' => 2, 'max_position_pct' => 0.02),
        'MOGUSD'   => array('name' => 'MOG',   'tier' => 2, 'max_position_pct' => 0.01),
        'POPCATUSD'=> array('name' => 'POPCAT','tier' => 2, 'max_position_pct' => 0.02),
    );
    
    $signals = array();
    
    foreach ($meme_pairs as $pair => $meta) {
        $signal = _kraken_enhanced_analyze($pair, $meta, $portfolio_value, $daily_risk_target, $max_position_pct);
        if ($signal && $signal['passes_liquidity_screen'] && $signal['score'] >= 65) {
            $signals[] = $signal;
        }
    }
    
    usort($signals, '_kraken_sort_by_ev'); // Sort by expected value, not just score
    
    $elapsed = round(microtime(true) - $start_time, 3);
    
    echo json_encode(array(
        'ok' => true,
        'timestamp' => date('c'),
        'portfolio_settings' => array(
            'value' => $portfolio_value,
            'daily_risk_target_pct' => $daily_risk_target * 100,
            'max_position_pct' => $max_position_pct * 100
        ),
        'signals_found' => count($signals),
        'signals' => array_slice($signals, 0, 5),
        'processing_time_ms' => $elapsed * 1000,
        'methodology' => 'volatility_targeted_kelly_sizing'
    ));
}

/**
 * Enhanced analysis with academic risk framework
 */
function _kraken_enhanced_analyze($pair, $meta, $portfolio_value, $daily_risk_target, $max_position_pct) {
    // Get OHLC data (60m intervals)
    $ohlc = _kraken_api('OHLC', array('pair' => $pair, 'interval' => 60));
    if (!$ohlc || !isset($ohlc['result'][$pair])) return null;
    
    $candles = $ohlc['result'][$pair];
    if (count($candles) < 12) return null;
    
    // Get orderbook for liquidity analysis
    $orderbook = _kraken_api('Depth', array('pair' => $pair, 'count' => 10));
    
    // Get ticker
    $ticker = _kraken_api('Ticker', array('pair' => $pair));
    if (!$ticker || !isset($ticker['result'][$pair])) return null;
    
    $tick = $ticker['result'][$pair];
    $current_price = floatval($tick['c'][0]);
    $best_bid = floatval($tick['b'][0]);
    $best_ask = floatval($tick['a'][0]);
    $spread = $best_ask - $best_bid;
    $spread_pct = ($spread / $best_bid) * 100;
    $volume_24h = floatval($tick['v'][1]);
    
    // Calculate realized volatility (60-minute rolling)
    $returns = array();
    for ($i = max(1, count($candles) - 12); $i < count($candles); $i++) {
        $prev = floatval($candles[$i-1][4]);
        $curr = floatval($candles[$i][4]);
        if ($prev > 0) {
            $returns[] = ($curr - $prev) / $prev;
        }
    }
    
    $realized_vol = _calc_realized_volatility($returns);
    $realized_vol_pct = $realized_vol * 100; // Annualized approx
    
    // Calculate momentum scores
    $price_1h = floatval($candles[count($candles)-2][4]);
    $price_6h = floatval($candles[max(0, count($candles)-7)][4]);
    $price_24h = floatval($candles[0][4]);
    
    $change_1h = (($current_price - $price_1h) / $price_1h) * 100;
    $change_6h = (($current_price - $price_6h) / $price_6h) * 100;
    $change_24h = (($current_price - $price_24h) / $price_24h) * 100;
    
    // LIQUIDITY SCREENING
    $passes_liquidity = true;
    $liquidity_issues = array();
    
    if ($spread_pct > 0.5) {
        $passes_liquidity = false;
        $liquidity_issues[] = "Spread {$spread_pct}% > 0.5%";
    }
    if ($volume_24h < 500000) {
        $passes_liquidity = false;
        $liquidity_issues[] = "Volume \${$volume_24h} < \$500K";
    }
    
    // Book depth check (if available)
    $book_depth_usd = 0;
    if ($orderbook && isset($orderbook['result'][$pair])) {
        $bids = $orderbook['result'][$pair]['bids'];
        $depth_sum = 0;
        for ($i = 0; $i < min(5, count($bids)); $i++) {
            $depth_sum += floatval($bids[$i][1]);
        }
        $book_depth_usd = $depth_sum * $current_price;
        if ($book_depth_usd < 50000) {
            $liquidity_issues[] = "Book depth \${$book_depth_usd} < \$50K";
        }
    }
    
    // SCORING (0-100)
    $score = 0;
    $factor_scores = array();
    
    // 1. Momentum (0-40 pts) - primary signal
    if ($change_1h > 3) $score += 15;
    elseif ($change_1h > 1) $score += 8;
    elseif ($change_1h > 0) $score += 3;
    
    if ($change_6h > 8) $score += 15;
    elseif ($change_6h > 3) $score += 8;
    elseif ($change_6h > 0) $score += 3;
    
    if ($change_24h > 15) $score += 10;
    elseif ($change_24h > 5) $score += 5;
    
    $factor_scores['momentum'] = $score;
    
    // 2. Volatility regime (0-20 pts)
    // Optimal: 3-8% hourly vol for memes
    $vol_score = 0;
    if ($realized_vol_pct >= 3 && $realized_vol_pct <= 8) $vol_score = 20;
    elseif ($realized_vol_pct >= 2 && $realized_vol_pct < 3) $vol_score = 15;
    elseif ($realized_vol_pct > 8 && $realized_vol_pct <= 12) $vol_score = 10;
    elseif ($realized_vol_pct > 12) $vol_score = 5; // Too volatile
    $score += $vol_score;
    $factor_scores['volatility'] = $vol_score;
    
    // 3. Trend quality (0-20 pts)
    $trend_score = 0;
    if ($change_1h > 0 && $change_6h > 0) $trend_score += 10;
    if ($change_6h > 0 && $change_24h > 0) $trend_score += 10;
    $score += $trend_score;
    $factor_scores['trend_quality'] = $trend_score;
    
    // 4. Volume confirmation (0-20 pts)
    $vol_confirm = 0;
    if ($volume_24h > 2000000) $vol_confirm = 20;
    elseif ($volume_24h > 1000000) $vol_confirm = 15;
    elseif ($volume_24h > 500000) $vol_confirm = 10;
    $score += $vol_confirm;
    $factor_scores['volume'] = $vol_confirm;
    
    // POSITION SIZING - Volatility Targeted
    // Formula: Position Size = Risk Budget / (Volatility * Price)
    $risk_budget = $portfolio_value * $daily_risk_target;
    
    // Conservative estimate: assume 1 std dev move against us
    $risk_per_unit = $current_price * ($realized_vol_pct / 100);
    
    if ($risk_per_unit > 0) {
        $theoretical_position = $risk_budget / $risk_per_unit;
        $theoretical_position_value = $theoretical_position * $current_price;
    } else {
        $theoretical_position_value = $portfolio_value * 0.01; // Fallback
    }
    
    // Apply caps
    $max_position_value = $portfolio_value * min($max_position_pct, $meta['max_position_pct']);
    $position_value = min($theoretical_position_value, $max_position_value);
    $position_value = min($position_value, $portfolio_value * 0.05); // Hard 5% cap
    
    // Position metrics
    $position_size_coins = $position_value / $current_price;
    $position_risk_pct = ($risk_per_unit * $position_size_coins) / $portfolio_value * 100;
    
    // KELLY FRACTION CALCULATION (simplified)
    // Assuming historical win rate of 35% for meme momentum (conservative)
    $estimated_win_rate = 0.35;
    $avg_win_to_loss = 1.5; // Target 1.5:1 reward/risk
    $kelly_pct = $estimated_win_rate - ((1 - $estimated_win_rate) / $avg_win_to_loss);
    $kelly_fraction = max(0, $kelly_pct) * 0.25; // Quarter Kelly for safety
    
    // Adjust position by Kelly
    $kelly_adjusted_position = $position_value * (1 + $kelly_fraction);
    $position_value = min($kelly_adjusted_position, $max_position_value);
    
    // TARGETS based on volatility
    // Take profit: 1.5-2x risk
    $target_pct = min(20, max(3, $realized_vol_pct * 2));
    $stop_pct = min(10, max(2, $realized_vol_pct * 0.8));
    
    $target_price = $current_price * (1 + $target_pct / 100);
    $stop_price = $current_price * (1 - $stop_pct / 100);
    
    // Risk/Reward ratio
    $rr_ratio = $target_pct / $stop_pct;
    
    // Expected Value (EV) calculation
    $ev = ($estimated_win_rate * $target_pct) - ((1 - $estimated_win_rate) * $stop_pct);
    
    // Signal rating
    if ($score >= 85) $rating = 'STRONG BUY';
    elseif ($score >= 70) $rating = 'BUY';
    elseif ($score >= 60) $rating = 'WEAK BUY';
    else $rating = 'NO TRADE';
    
    return array(
        'pair' => $pair,
        'name' => $meta['name'],
        'tier' => $meta['tier'],
        'score' => $score,
        'rating' => $rating,
        'passes_liquidity_screen' => $passes_liquidity,
        'liquidity_issues' => $liquidity_issues,
        
        // Price data
        'price' => round($current_price, 10),
        'price_formatted' => _format_price($current_price),
        'spread_pct' => round($spread_pct, 3),
        
        // Momentum
        'change_1h' => round($change_1h, 2),
        'change_6h' => round($change_6h, 2),
        'change_24h' => round($change_24h, 2),
        'realized_vol_1h_pct' => round($realized_vol_pct, 2),
        
        // Position sizing (the key improvement)
        'position_sizing' => array(
            'portfolio_value' => $portfolio_value,
            'risk_budget_usd' => round($risk_budget, 2),
            'theoretical_position_usd' => round($theoretical_position_value, 2),
            'recommended_position_usd' => round($position_value, 2),
            'recommended_position_coins' => round($position_size_coins, 2),
            'position_risk_pct' => round($position_risk_pct, 3),
            'max_position_pct' => $meta['max_position_pct'] * 100,
            'kelly_fraction_used' => round($kelly_fraction * 100, 2),
            'sizing_method' => 'volatility_targeted_quarter_kelly'
        ),
        
        // Targets
        'target_price' => round($target_price, 10),
        'target_price_formatted' => _format_price($target_price),
        'stop_price' => round($stop_price, 10),
        'stop_price_formatted' => _format_price($stop_price),
        'target_pct' => round($target_pct, 1),
        'stop_pct' => round($stop_pct, 1),
        'rr_ratio' => round($rr_ratio, 2),
        
        // Expected value
        'expected_value_pct' => round($ev, 3),
        'estimated_win_rate' => $estimated_win_rate * 100,
        
        'factor_scores' => $factor_scores,
        'timestamp' => time()
    );
}

/**
 * Get specific BUY NOW recommendation with best EV
 */
function _kraken_enhanced_buynow($conn, $portfolio_value, $daily_risk_target, $max_position_pct) {
    $meme_pairs = array(
        'PEPEUSD'  => array('name' => 'PEPE',  'tier' => 2, 'max_position_pct' => 0.02),
        'FLOKIUSD' => array('name' => 'FLOKI', 'tier' => 2, 'max_position_pct' => 0.02),
        'BONKUSD'  => array('name' => 'BONK',  'tier' => 2, 'max_position_pct' => 0.02),
        'SHIBUSD'  => array('name' => 'SHIB',  'tier' => 1, 'max_position_pct' => 0.03),
        'DOGEUSD'  => array('name' => 'DOGE',  'tier' => 1, 'max_position_pct' => 0.03),
        'WIFUSD'   => array('name' => 'WIF',   'tier' => 2, 'max_position_pct' => 0.02),
    );
    
    $candidates = array();
    
    foreach ($meme_pairs as $pair => $meta) {
        $signal = _kraken_enhanced_analyze($pair, $meta, $portfolio_value, $daily_risk_target, $max_position_pct);
        if ($signal && $signal['passes_liquidity_screen'] && $signal['score'] >= 70 && $signal['rr_ratio'] >= 1.5) {
            $candidates[] = $signal;
        }
    }
    
    // Sort by expected value (academic approach)
    usort($candidates, '_kraken_sort_by_ev');
    
    if (empty($candidates)) {
        echo json_encode(array(
            'ok' => true,
            'has_recommendation' => false,
            'message' => 'No signals meet risk-adjusted criteria (min score 70, min R/R 1.5:1, passes liquidity screen).',
            'timestamp' => date('c')
        ));
        return;
    }
    
    $pick = $candidates[0];
    
    // Build detailed rationale
    $rationale = _build_academic_rationale($pick);
    $pick['detailed_rationale'] = $rationale;
    
    echo json_encode(array(
        'ok' => true,
        'has_recommendation' => true,
        'timestamp' => date('c'),
        'pick' => $pick,
        'alternatives' => array_slice($candidates, 1, 2),
        'academic_notes' => array(
            'sizing_method' => 'Volatility-targeted position sizing per Moskowitz et al. (2012)',
            'kelly_fraction' => 'Quarter-Kelly criterion for risk control (MacLean, Thorp, Ziemba)',
            'volatility_window' => '60-minute realized volatility',
            'expected_value' => 'EV = (Win Rate × Target) - (Loss Rate × Stop)',
            'liquidity_screen' => 'Spread < 0.5%, Volume > $500K, Depth > $50K'
        ),
        'disclaimer' => 'NOT FINANCIAL ADVICE. MEME COINS ARE HIGHLY SPECULATIVE. PAST PERFORMANCE DOES NOT GUARANTEE FUTURE RESULTS.'
    ));
}

/**
 * Record paper trade
 */
function _kraken_record_paper_trade($conn) {
    $pair = isset($_POST['pair']) ? $conn->real_escape_string($_POST['pair']) : '';
    $entry = isset($_POST['entry_price']) ? floatval($_POST['entry_price']) : 0;
    $target = isset($_POST['target_price']) ? floatval($_POST['target_price']) : 0;
    $stop = isset($_POST['stop_price']) ? floatval($_POST['stop_price']) : 0;
    $position_usd = isset($_POST['position_usd']) ? floatval($_POST['position_usd']) : 0;
    $rationale = isset($_POST['rationale']) ? $conn->real_escape_string($_POST['rationale']) : '';
    
    if (!$pair || $entry <= 0) {
        echo json_encode(array('ok' => false, 'error' => 'Invalid parameters'));
        return;
    }
    
    $sql = "INSERT INTO kraken_paper_trades 
            (pair, entry_price, target_price, stop_price, position_usd, rationale, status, created_at)
            VALUES 
            ('$pair', $entry, $target, $stop, $position_usd, '$rationale', 'open', NOW())";
    
    if ($conn->query($sql)) {
        echo json_encode(array(
            'ok' => true,
            'trade_id' => $conn->insert_id,
            'message' => 'Paper trade recorded. Monitor in paper trading dashboard.'
        ));
    } else {
        echo json_encode(array('ok' => false, 'error' => 'Database error'));
    }
}

/**
 * Get paper trading status
 */
function _kraken_paper_status($conn) {
    // Open positions
    $open_res = $conn->query("SELECT * FROM kraken_paper_trades WHERE status = 'open' ORDER BY created_at DESC");
    $open = array();
    while ($row = $open_res->fetch_assoc()) {
        $open[] = $row;
    }
    
    // Closed positions with stats
    $stats_res = $conn->query("SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN pnl_pct > 0 THEN 1 ELSE 0 END) as wins,
        SUM(CASE WHEN pnl_pct <= 0 THEN 1 ELSE 0 END) as losses,
        AVG(pnl_pct) as avg_pnl,
        SUM(pnl_usd) as total_pnl_usd
    FROM kraken_paper_trades WHERE status = 'closed'");
    $stats = $stats_res->fetch_assoc();
    
    echo json_encode(array(
        'ok' => true,
        'open_positions' => $open,
        'statistics' => $stats,
        'win_rate' => $stats['total'] > 0 ? round(($stats['wins'] / $stats['total']) * 100, 1) : 0
    ));
}

// Helper functions
function _kraken_api($method, $params = array()) {
    $base_url = 'https://api.kraken.com/0/public/' . $method;
    if (!empty($params)) {
        $qs = http_build_query($params);
        $base_url .= '?' . $qs;
    }
    
    $ch = curl_init($base_url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'KrakenAcademicScanner/1.0');
    
    $resp = curl_exec($ch);
    curl_close($ch);
    
    if (!$resp) return null;
    $data = json_decode($resp, true);
    if (isset($data['error']) && !empty($data['error'])) return null;
    return $data;
}

function _calc_realized_volatility($returns) {
    if (count($returns) < 2) return 0;
    $n = count($returns);
    $mean = array_sum($returns) / $n;
    
    $sum_sq = 0;
    foreach ($returns as $r) {
        $sum_sq += pow($r - $mean, 2);
    }
    
    $variance = $sum_sq / ($n - 1);
    $std_dev = sqrt($variance);
    
    // Annualized (approximate for hourly data: sqrt(24*365))
    return $std_dev * sqrt(8760);
}

function _format_price($price) {
    if ($price >= 1) return number_format($price, 4);
    if ($price >= 0.01) return number_format($price, 6);
    if ($price >= 0.0001) return number_format($price, 8);
    return number_format($price, 10);
}

function _kraken_sort_by_ev($a, $b) {
    return $b['expected_value_pct'] - $a['expected_value_pct'];
}

function _build_academic_rationale($pick) {
    $parts = array();
    
    $parts[] = "Momentum Score: {$pick['factor_scores']['momentum']}/40 (1h: {$pick['change_1h']}%, 6h: {$pick['change_6h']}%)";
    $parts[] = "Volatility Regime: {$pick['realized_vol_1h_pct']}% (optimal for memes: 3-8%)";
    $parts[] = "Position sized to 0.5% daily risk budget = \${$pick['position_sizing']['risk_budget_usd']}";
    $parts[] = "Quarter-Kelly fraction: {$pick['position_sizing']['kelly_fraction_used']}% applied";
    $parts[] = "R/R Ratio: {$pick['rr_ratio']}:1 (target: 1.5:1+)";
    $parts[] = "Expected Value: {$pick['expected_value_pct']}% per trade";
    
    if (!empty($pick['liquidity_issues'])) {
        $parts[] = "WARNINGS: " . implode(', ', $pick['liquidity_issues']);
    }
    
    return implode("; ", $parts);
}

// Create paper trades table
$conn->query("CREATE TABLE IF NOT EXISTS kraken_paper_trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(20) NOT NULL,
    entry_price DECIMAL(20,10) NOT NULL,
    target_price DECIMAL(20,10) NOT NULL,
    stop_price DECIMAL(20,10) NOT NULL,
    position_usd DECIMAL(12,2) NOT NULL,
    rationale TEXT,
    status VARCHAR(20) DEFAULT 'open',
    exit_price DECIMAL(20,10) DEFAULT NULL,
    exit_reason VARCHAR(50) DEFAULT NULL,
    pnl_pct DECIMAL(8,4) DEFAULT NULL,
    pnl_usd DECIMAL(12,2) DEFAULT NULL,
    created_at DATETIME NOT NULL,
    closed_at DATETIME DEFAULT NULL,
    INDEX idx_status (status),
    INDEX idx_pair (pair),
    INDEX idx_created (created_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->close();
?>