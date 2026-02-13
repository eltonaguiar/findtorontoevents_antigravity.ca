<?php
/**
 * Recommendation Audit Trail API
 * Returns detailed methodology data for any pick that can be analyzed by other AIs
 */

// Start output buffering to catch any errors
ob_start();

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

error_reporting(0);
ini_set('display_errors', '0');

$type = isset($_GET['type']) ? $_GET['type'] : ''; // 'kraken', 'hot', 'scanner'
$symbol = isset($_GET['symbol']) ? strtoupper($_GET['symbol']) : '';
$timestamp = isset($_GET['ts']) ? $_GET['ts'] : date('Y-m-d H:i:s');

if (empty($type) || empty($symbol)) {
    ob_clean();
    echo json_encode(array('ok' => false, 'error' => 'Missing type or symbol'));
    exit;
}

// Generate comprehensive audit based on type
$audit = null;
$function_error = null;

try {
    switch ($type) {
        case 'kraken':
            $audit = _generate_kraken_audit($symbol);
            break;
        case 'hot':
            $audit = _generate_hot_audit($symbol);
            break;
        case 'scanner':
            $audit = _generate_scanner_audit($symbol);
            break;
        default:
            ob_clean();
            echo json_encode(array('ok' => false, 'error' => 'Unknown type'));
            exit;
    }
} catch (Exception $e) {
    $function_error = $e->getMessage();
}

// Clear any unexpected output
ob_clean();

if ($function_error) {
    echo json_encode(array('ok' => false, 'error' => 'Internal error: ' . $function_error));
} elseif ($audit) {
    echo json_encode($audit);
} else {
    echo json_encode(array('ok' => false, 'error' => 'Failed to generate audit'));
}

/**
 * Generate Kraken ranking audit
 */
function _generate_kraken_audit($symbol) {
    // Fetch current data
    $pulse_data = _fetch_pulse_data();
    $coin_data = null;
    
    foreach ($pulse_data['rankings'] as $r) {
        if ($r['symbol'] === $symbol) {
            $coin_data = $r;
            break;
        }
    }
    
    if (!$coin_data) {
        return array('ok' => false, 'error' => 'Coin not found in current rankings');
    }
    
    // Add full name to avoid confusion
    $full_name = _get_coin_full_name($symbol);
    $coin_data['full_name'] = $full_name;
    
    $audit_text = _build_audit_text($symbol, $coin_data, 'Kraken Rankings v2.2');
    
    return array(
        'ok' => true,
        'type' => 'kraken',
        'symbol' => $symbol,
        'full_name' => $full_name,
        'timestamp' => date('c'),
        'audit_data' => $coin_data,
        'audit_text' => $audit_text,
        'formatted_for_ai' => _format_for_ai($symbol, $coin_data, 'kraken')
    );
}

/**
 * Generate Hot Trending audit
 */
function _generate_hot_audit($symbol) {
    $cache_file = dirname(__FILE__) . '/../../tmp/hot_trending_1h.json';
    $hot_data = null;
    $coin_data = null;
    
    if (file_exists($cache_file)) {
        $hot_data = json_decode(file_get_contents($cache_file), true);
    }
    
    if ($hot_data) {
        $kraken_hot = isset($hot_data['kraken_hot']) ? $hot_data['kraken_hot'] : array();
        $watch_list = isset($hot_data['watch_list']) ? $hot_data['watch_list'] : array();
        $other_trending = isset($hot_data['other_trending']) ? $hot_data['other_trending'] : array();
        $all_coins = array_merge($kraken_hot, $watch_list, $other_trending);
        
        foreach ($all_coins as $c) {
            if ($c['symbol'] === $symbol) {
                $coin_data = $c;
                break;
            }
        }
    }
    
    if (!$coin_data) {
        return array('ok' => false, 'error' => 'Coin not found in hot trending');
    }
    
    // Add full name to avoid confusion (use existing name if available, otherwise lookup)
    $full_name = isset($coin_data['name']) && $coin_data['name'] ? $coin_data['name'] : _get_coin_full_name($symbol);
    $coin_data['full_name'] = $full_name;
    
    $audit_text = _build_hot_audit_text($symbol, $coin_data);
    
    return array(
        'ok' => true,
        'type' => 'hot',
        'symbol' => $symbol,
        'full_name' => $full_name,
        'timestamp' => date('c'),
        'audit_data' => $coin_data,
        'audit_text' => $audit_text,
        'formatted_for_ai' => _format_hot_for_ai($symbol, $coin_data)
    );
}

/**
 * Generate Scanner audit
 */
function _generate_scanner_audit($symbol) {
    // This would fetch from the meme_scanner database
    return array(
        'ok' => true,
        'type' => 'scanner',
        'symbol' => $symbol,
        'note' => 'Scanner audit requires signal ID - not yet implemented',
        'formatted_for_ai' => 'Scanner audit trail coming in v3.0'
    );
}

/**
 * Build human-readable audit text
 */
function _build_audit_text($symbol, $data, $source) {
    $scores = isset($data['scores']) ? $data['scores'] : array();
    $rating = isset($data['rating_10']) ? $data['rating_10'] : isset($data['rating']) ? $data['rating'] : 'N/A';
    $zone = isset($data['rating_zone']) ? $data['rating_zone'] : 'unknown';
    
    $text = "=== RECOMMENDATION AUDIT TRAIL ===\n";
    $text .= "Source: $source\n";
    $text .= "Generated: " . date('Y-m-d H:i:s T') . "\n";
    $text .= "Coin: $symbol\n";
    $text .= "Current Rating: $rating/10 ($zone)\n";
    $text .= "Price: \\$" . (isset($data['price']) ? $data['price'] : 'N/A') . "\n";
    $text .= "24h Change: " . (isset($data['chg_24h']) ? $data['chg_24h'] : 'N/A') . "%\n";
    $text .= "\n=== SCORING BREAKDOWN ===\n";
    $text .= "Momentum (35 pts): " . (isset($scores['momentum']) ? $scores['momentum'] : 'N/A') . "/35\n";
    $text .= "Volume (25 pts): " . (isset($scores['volume']) ? $scores['volume'] : 'N/A') . "/25\n";
    $text .= "Social Buzz (15 pts): " . (isset($scores['trending']) ? $scores['trending'] : 'N/A') . "/15\n";
    $text .= "Entry Position (15 pts): " . (isset($scores['entry_position']) ? $scores['entry_position'] : 'N/A') . "/15\n";
    $text .= "Spread (10 pts): " . (isset($scores['spread']) ? $scores['spread'] : 'N/A') . "/10\n";
    
    if (isset($data['chasing_warning']) && $data['chasing_warning']) {
        $text .= "\n⚠️ CHASING PENALTY APPLIED: -" . $data['chasing_penalty'] . " pts\n";
        $text .= "Reason: High momentum but poor entry position (buying near daily high)\n";
    }
    
    if (isset($data['pump_dump_risk']) && $data['pump_dump_risk'] !== 'none') {
        $text .= "\n⚠️ PUMP & DUMP RISK: " . strtoupper($data['pump_dump_risk']) . "\n";
        $text .= "Signals: " . implode(', ', isset($data['pump_dump_signals']) ? $data['pump_dump_signals'] : array()) . "\n";
    }
    
    $text .= "\n=== METHODOLOGY NOTES ===\n";
    $text .= "- Momentum: Sweet spot is +3% to +15% 24h change\n";
    $text .= "- Volume: Higher is better, $500K+ ideal\n";
    $text .= "- Social: Binary 15pt bonus if trending on CoinGecko\n";
    $text .= "- Entry: Near 24h low = better, near high = chasing\n";
    $text .= "- Spread: Tighter = less slippage\n";
    
    $text .= "\n=== RAW DATA ===\n";
    $text .= json_encode($data, JSON_PRETTY_PRINT);
    
    return $text;
}

/**
 * Build Hot Trending audit text
 */
function _build_hot_audit_text($symbol, $data) {
    $tech = isset($data['technical']) ? $data['technical'] : array();
    
    $text = "=== HOT TRENDING AUDIT TRAIL ===\n";
    $text .= "Source: Hot Trending Scanner v1.0\n";
    $text .= "Generated: " . date('Y-m-d H:i:s T') . "\n";
    $text .= "Coin: $symbol\n";
    $text .= "Name: " . (isset($data['name']) ? $data['name'] : 'N/A') . "\n";
    $text .= "CMC Rank: " . (isset($data['cmc_rank']) ? $data['cmc_rank'] : 'N/A') . "\n";
    $text .= "\n=== CONFIDENCE SCORE ===\n";
    $text .= "Confidence: " . $data['confidence'] . "%\n";
    $text .= "Trend Strength: " . $data['trend_strength'] . "/100\n";
    $text .= "Recommendation: " . $data['recommendation'] . "\n";
    $text .= "On Kraken: " . ($data['on_kraken'] ? 'Yes' : 'No') . "\n";
    
    $text .= "\n=== PRICE DATA ===\n";
    $text .= "Price: \\$" . (isset($data['price']) ? $data['price'] : 'N/A') . "\n";
    $text .= "24h Change: " . (isset($data['chg_24h']) ? $data['chg_24h'] : 'N/A') . "%\n";
    $text .= "24h Volume: $" . number_format(isset($data['volume_24h']) ? $data['volume_24h'] : 0) . "\n";
    $text .= "Market Cap: $" . number_format(isset($data['market_cap']) ? $data['market_cap'] : 0) . "\n";
    
    $text .= "\n=== TECHNICAL ANALYSIS ===\n";
    if ($tech) {
        $text .= "EMA-12: $" . (isset($tech['ema_12']) ? $tech['ema_12'] : 'N/A') . "\n";
        $text .= "EMA-26: $" . (isset($tech['ema_26']) ? $tech['ema_26'] : 'N/A') . "\n";
        $text .= "RSI: " . (isset($tech['rsi']) ? $tech['rsi'] : 'N/A') . "\n";
        $text .= "Momentum 5m: " . (isset($tech['momentum_5m']) ? $tech['momentum_5m'] : 'N/A') . "%\n";
        $text .= "Momentum 15m: " . (isset($tech['momentum_15m']) ? $tech['momentum_15m'] : 'N/A') . "%\n";
        $text .= "Momentum 1h: " . (isset($tech['momentum_1h']) ? $tech['momentum_1h'] : 'N/A') . "%\n";
        $text .= "Volume Ratio: " . (isset($tech['volume_ratio']) ? $tech['volume_ratio'] : 'N/A') . "x avg\n";
        $text .= "Acceleration: " . ($tech['momentum_acceleration'] ? 'Yes' : 'No') . "\n";
        $text .= "\nActive Factors:\n";
        foreach (isset($tech['factors']) ? $tech['factors'] : array() as $factor) {
            $text .= "  ✓ " . str_replace('_', ' ', $factor) . "\n";
        }
    }
    
    $text .= "\n=== CONFIDENCE METHODOLOGY ===\n";
    $text .= "Trend Alignment (35 pts): Price above EMA-12 & EMA-26, bullish crossover\n";
    $text .= "Momentum (25 pts): 5m > 15m > 1h acceleration pattern\n";
    $text .= "Volume (15 pts): Current > 2x 20-period average\n";
    $text .= "RSI Sweet Spot (15 pts): 50-75 range\n";
    $text .= "Not Overbought (10 pts): RSI < 80\n";
    
    $text .= "\n=== DISCLAIMERS ===\n";
    $text .= "- Confidence % estimates probability based on technical factors\n";
    $text .= "- Does NOT guarantee future performance\n";
    $text .= "- Meme coins can reverse violently at any time\n";
    $text .= "- Never risk more than 1-2% of portfolio\n";
    
    return $text;
}

/**
 * Format for AI analysis (structured prompt)
 */
function _format_for_ai($symbol, $data, $type) {
    $prompt = "Please analyze this cryptocurrency recommendation and provide critical feedback on the methodology.\n\n";
    $prompt .= "=== PICK DETAILS ===\n";
    $prompt .= "Coin: $symbol\n";
    $prompt .= "Source: " . ($type === 'kraken' ? 'Kraken Meme Rankings v2.2' : 'Unknown') . "\n";
    $prompt .= "Rating: " . (isset($data['rating_10']) ? $data['rating_10'] : 'N/A') . "/10\n";
    $prompt .= "Price: \\$" . (isset($data['price']) ? $data['price'] : 'N/A') . "\n";
    $prompt .= "24h Change: " . (isset($data['chg_24h']) ? $data['chg_24h'] : 'N/A') . "%\n";
    $prompt .= "\n=== SCORE BREAKDOWN ===\n";
    
    $scores = isset($data['scores']) ? $data['scores'] : array();
    $prompt .= "- Momentum (35% weight): " . (isset($scores['momentum']) ? $scores['momentum'] : 0) . "/35 points\n";
    $prompt .= "  -> 24h price change sweet spot: +3% to +15%\n";
    $prompt .= "  -> Current 24h: " . (isset($data['chg_24h']) ? $data['chg_24h'] : 'N/A') . "%\n";
    $prompt .= "\n";
    $prompt .= "- Volume (25% weight): " . (isset($scores['volume']) ? $scores['volume'] : 0) . "/25 points\n";
    $prompt .= "  -> 24h Volume: $" . number_format(isset($data['vol_24h_usd']) ? $data['vol_24h_usd'] : 0) . "\n";
    $prompt .= "\n";
    $prompt .= "- Social Buzz (15% weight): " . (isset($scores['trending']) ? $scores['trending'] : 0) . "/15 points\n";
    $prompt .= "  -> Binary bonus if trending on CoinGecko\n";
    $prompt .= "  -> Is Trending: " . ($data['is_trending'] ? 'Yes (+15 pts)' : 'No (0 pts)') . "\n";
    $prompt .= "\n";
    $prompt .= "- Entry Position (15% weight): " . (isset($scores['entry_position']) ? $scores['entry_position'] : 0) . "/15 points\n";
    $prompt .= "  -> Price position in 24h range: " . (isset($data['price_in_range_pct']) ? $data['price_in_range_pct'] : 'N/A') . "%\n";
    $prompt .= "  -> Near 0% = near low (good), Near 100% = near high (bad)\n";
    $prompt .= "\n";
    $prompt .= "- Spread (10% weight): " . (isset($scores['spread']) ? $scores['spread'] : 0) . "/10 points\n";
    $prompt .= "  -> Bid/ask spread: " . (isset($data['spread_pct']) ? $data['spread_pct'] : 'N/A') . "%\n";
    $prompt .= "\n=== WARNINGS ===\n";
    
    if (isset($data['chasing_warning']) && $data['chasing_warning']) {
        $prompt .= "⚠️ CHASING PENALTY: -" . $data['chasing_penalty'] . " points applied\n";
        $prompt .= "   High momentum but buying near daily high\n";
    }
    
    if (isset($data['pump_dump_risk']) && $data['pump_dump_risk'] !== 'none') {
        $prompt .= "⚠️ PUMP & DUMP RISK: " . strtoupper($data['pump_dump_risk']) . "\n";
    }
    
    $prompt .= "\n=== QUESTIONS FOR ANALYSIS ===\n";
    $prompt .= "1. Is the methodology sound? Are the weights appropriate?\n";
    $prompt .= "2. Are there any red flags with this pick?\n";
    $prompt .= "3. What factors might the algorithm be missing?\n";
    $prompt .= "4. Would you recommend this pick? Why or why not?\n";
    $prompt .= "5. What's the biggest risk with this recommendation?\n";
    
    return $prompt;
}

/**
 * Format Hot Trending for AI
 */
function _format_hot_for_ai($symbol, $data) {
    $prompt = "Please analyze this Hot Trending cryptocurrency recommendation and provide critical feedback.\n\n";
    $prompt .= "=== PICK DETAILS ===\n";
    $prompt .= "Coin: $symbol\n";
    $prompt .= "Source: Hot Trending Scanner v1.0 BETA\n";
    $prompt .= "Confidence: " . $data['confidence'] . "%\n";
    $prompt .= "Trend Strength: " . $data['trend_strength'] . "/100\n";
    $prompt .= "Recommendation: " . $data['recommendation'] . "\n";
    $prompt .= "Tradable on Kraken: " . ($data['on_kraken'] ? 'Yes' : 'No') . "\n";
    $prompt .= "\n=== PRICE DATA ===\n";
    $prompt .= "Price: \\$" . (isset($data['price']) ? $data['price'] : 'N/A') . "\n";
    $prompt .= "24h Change: " . (isset($data['chg_24h']) ? $data['chg_24h'] : 'N/A') . "%\n";
    $prompt .= "24h Volume: $" . number_format(isset($data['volume_24h']) ? $data['volume_24h'] : 0) . "\n";
    $prompt .= "\n=== TECHNICAL ANALYSIS ===\n";
    
    $tech = isset($data['technical']) ? $data['technical'] : array();
    if ($tech) {
        $prompt .= "EMA-12: $" . (isset($tech['ema_12']) ? $tech['ema_12'] : 'N/A') . "\n";
        $prompt .= "EMA-26: $" . (isset($tech['ema_26']) ? $tech['ema_26'] : 'N/A') . "\n";
        $prompt .= "RSI: " . (isset($tech['rsi']) ? $tech['rsi'] : 'N/A') . "\n";
        $prompt .= "5m Momentum: " . (isset($tech['momentum_5m']) ? $tech['momentum_5m'] : 'N/A') . "%\n";
        $prompt .= "15m Momentum: " . (isset($tech['momentum_15m']) ? $tech['momentum_15m'] : 'N/A') . "%\n";
        $prompt .= "1h Momentum: " . (isset($tech['momentum_1h']) ? $tech['momentum_1h'] : 'N/A') . "%\n";
        $prompt .= "Volume Ratio: " . (isset($tech['volume_ratio']) ? $tech['volume_ratio'] : 'N/A') . "x average\n";
        $prompt .= "Momentum Accelerating: " . ($tech['momentum_acceleration'] ? 'Yes' : 'No') . "\n";
        $prompt .= "\nActive Technical Factors:\n";
        foreach (isset($tech['factors']) ? $tech['factors'] : array() as $factor) {
            $prompt .= "  ✓ " . str_replace('_', ' ', $factor) . "\n";
        }
    }
    
    $prompt .= "\n=== CONFIDENCE METHODOLOGY ===\n";
    $prompt .= "The confidence score (0-100%) is calculated as:\n";
    $prompt .= "- Trend Alignment (35 pts): Price above EMA-12 & EMA-26, bullish crossover\n";
    $prompt .= "- Momentum (25 pts): 5m > 15m > 1h price acceleration\n";
    $prompt .= "- Volume Confirmation (15 pts): Volume > 2x 20-period average\n";
    $prompt .= "- RSI Sweet Spot (15 pts): RSI between 50-75\n";
    $prompt .= "- Not Overbought (10 pts): RSI < 80\n";
    $prompt .= "\nAdjustments:\n";
    $prompt .= "- RSI > 80: -20 points (overbought)\n";
    $prompt .= "- RSI < 40: -15 points (weak momentum)\n";
    $prompt .= "- Volume < 0.8x: -15 points (low interest)\n";
    $prompt .= "- No acceleration: -10 points (decelerating)\n";
    
    $prompt .= "\n=== QUESTIONS FOR ANALYSIS ===\n";
    $prompt .= "1. Is the confidence calculation methodology sound?\n";
    $prompt .= "2. Are the technical factors appropriately weighted?\n";
    $prompt .= "3. What risks is the algorithm missing?\n";
    $prompt .= "4. Would you trust this confidence score? Why or why not?\n";
    $prompt .= "5. What additional factors should be considered?\n";
    $prompt .= "6. Is this actually a good entry point?\n";
    
    return $prompt;
}

/**
 * Fetch current pulse data
 */
function _fetch_pulse_data() {
    $cache_file = dirname(__FILE__) . '/../../tmp/mp_kraken_ranked.json';
    if (file_exists($cache_file)) {
        $content = @file_get_contents($cache_file);
        if ($content) {
            $data = @json_decode($content, true);
            if ($data && is_array($data) && isset($data['rankings'])) {
                return $data;
            }
        }
    }
    return array('rankings' => array());
}

/**
 * Get full name for a coin symbol to avoid confusion
 */
function _get_coin_full_name($symbol) {
    $names = array(
        'DOGE' => 'Dogecoin',
        'SHIB' => 'Shiba Inu',
        'PEPE' => 'Pepe',
        'FLOKI' => 'Floki',
        'BONK' => 'Bonk',
        'WIF' => 'Dogwifhat',
        'TURBO' => 'Turbo',
        'NEIRO' => 'Neiro',
        'MEME' => 'Memecoin',
        'TRUMP' => 'Official Trump',
        'FARTCOIN' => 'Fartcoin',
        'PNUT' => 'Peanut the Squirrel',
        'PENGU' => 'Pudgy Penguins',
        'POPCAT' => 'Popcat',
        'BRETT' => 'Brett',
        'MOG' => 'Mog Coin',
        'BOME' => 'Book of Meme',
        'ACT' => 'Act I: The AI Prophecy',
        'SPX' => 'SPX6900',
        'PONKE' => 'Ponke',
        'FWOG' => 'Fwog',
        'SLERF' => 'Slerf',
        'AI16Z' => 'AI16Z',
        'VIRTUAL' => 'Virtual Protocol',
        'MYRO' => 'Myro',
        'GOAT' => 'Goatseus Maximus',
        'MOODENG' => 'Moo Deng',
        'GIGA' => 'Gigachad',
        'DEGEN' => 'Degen',
        'BABYDOGE' => 'Baby Doge Coin',
        'WOJAK' => 'Wojak',
        'SATS' => '1000SATS',
        'COQ' => 'Coq Inu',
        'DOG' => 'DOG (Runes)',
        'CHILLGUY' => 'Just a Chill Guy',
        'TOSHI' => 'Toshi',
        'ME' => 'Magic Eden',
        'KEEP' => 'Keep Network',
        'LRC' => 'Loopring',
        'PEP' => 'Pepecoin Network',
        'CAMP' => 'Camp Network',
        'SRM' => 'Serum',
        'ESP' => 'Espresso',
        'SOSO' => 'Sosovalue',
        'AZTEC' => 'Aztec Protocol',
        'BTC' => 'Bitcoin',
        'ETH' => 'Ethereum',
        'SOL' => 'Solana',
        'XRP' => 'Ripple',
        'ADA' => 'Cardano',
        'DOT' => 'Polkadot',
        'LINK' => 'Chainlink',
        'UNI' => 'Uniswap',
        'AAVE' => 'Aave',
        'SNX' => 'Synthetix',
        'MKR' => 'Maker',
        'CRV' => 'Curve DAO',
        'LDO' => 'Lido DAO',
        'GMX' => 'GMX',
        'DYDX' => 'dYdX',
        'APE' => 'ApeCoin',
        'SAND' => 'The Sandbox',
        'MANA' => 'Decentraland',
        'AXS' => 'Axie Infinity',
        'GALA' => 'Gala',
        'ENJ' => 'Enjin Coin',
        'CHZ' => 'Chiliz',
        'FTM' => 'Fantom',
        'AVAX' => 'Avalanche',
        'NEAR' => 'NEAR Protocol',
        'ATOM' => 'Cosmos',
        'ALGO' => 'Algorand',
        'XTZ' => 'Tezos',
        'FIL' => 'Filecoin',
        'AR' => 'Arweave'
    );
    return isset($names[$symbol]) ? $names[$symbol] : $symbol;
}
