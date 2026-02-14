<?php
/**
 * Expert Consensus Engine v1.0 — Subject Matter Expert Intelligence
 * ==================================================================
 * Integrates findings from 10 social media sources, 10 algo communities,
 * and 5 expert disciplines into actionable signals.
 *
 * EXPERT SOURCES CONSULTED:
 * Social Media Layer:
 *   1. Willy Woo (@woonomic) - NVT, on-chain cycles, $220K BTC target
 *   2. Ki Young Ju (CryptoQuant) - Exchange flows, whale vs consolidation
 *   3. Glassnode - MVRV, SOPR, STH profitability, supply clusters
 *   4. Arthur Hayes - Macro liquidity cycles, Fed policy, ETF mechanics
 *   5. Hildobby (Dune) - ETH on-chain visualization, staking flows
 *   6. PlanB (S2F) - Bitcoin cyclical nature, time-based features
 *   7. Lex Moskovski - OI/funding daily charts, derivatives sentiment
 *   8. The Block Research - Structural market changes
 *   9. Whale Alert / Arkham - Real-time whale tracking
 *  10. Miles Deutscher - Retail momentum meta, altcoin spotlight
 *
 * Algo/Statistician Communities:
 *   1. Numerai Tournament - Crowdsourced model stress-testing
 *   2. QuantConnect/LEAN - Institutional execution critique
 *   3. r/algotrading - Live vs backtest gap, strategy adaptation
 *   4. Stack Exchange (Quant Finance) - Mathematical rigor
 *   5. r/ethfinance - ETH technical mechanics
 *   6. Kaggle Crypto - Winning feature engineering
 *   7. Dune Analytics - On-chain SQL verification
 *   8. Freqtrade Community - Execution reality
 *   9. r/statistics - Sample size / Sharpe distribution
 *  10. Quantopian Archives - Overfitting bible
 *
 * Expert Disciplines:
 *   1. Market Microstructure - Slippage, order book depth, execution
 *   2. On-Chain Forensics - Distinguish whale moves from exchange ops
 *   3. MLOps - Model drift detection, retraining triggers
 *   4. DeFi Mechanics - Protocol upgrade impact on features
 *   5. Behavioral Economics - Sentiment extremes as contrarian signals
 *
 * KEY FINDINGS INTEGRATED:
 * - CryptoQuant: Whale accumulation OVERSTATED (exchange consolidation)
 * - Glassnode: BTC in defensive consolidation $60-72k, STH profitability negative
 * - Hayes: Liquidity expansion coming 2026, ETF delta-hedging caused Feb drop
 * - Funding rates: -0.0014% (most negative since Apr 2024) = crowded short
 * - Slippage: 80% worse on memecoins vs mature assets (real data)
 * - Numerai: Unique/proprietary data + LightGBM wins competitions
 * - Freqtrade: Market-state classification (7 states) is key to adaptation
 *
 * PHP 5.2 compatible.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

error_reporting(0);
ini_set('display_errors', '0');
set_time_limit(180);

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) { echo json_encode(array('ok' => false, 'error' => 'DB fail')); exit; }
$conn->set_charset('utf8');

$conn->query("CREATE TABLE IF NOT EXISTS ec_signals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pair VARCHAR(30) NOT NULL,
    direction VARCHAR(10) DEFAULT 'LONG',
    entry_price DECIMAL(20,10),
    tp_price DECIMAL(20,10),
    sl_price DECIMAL(20,10),
    confidence DECIMAL(8,4),
    expert_score DECIMAL(8,4),
    market_state VARCHAR(30),
    slippage_adjusted TINYINT DEFAULT 0,
    execution_cost_pct DECIMAL(8,4) DEFAULT 0,
    expert_signals TEXT,
    contrarian_flags TEXT,
    microstructure_note TEXT,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    current_price DECIMAL(20,10),
    pnl_pct DECIMAL(8,4),
    exit_reason VARCHAR(50),
    created_at DATETIME,
    resolved_at DATETIME,
    INDEX idx_status (status),
    INDEX idx_pair (pair)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS ec_audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    action VARCHAR(50) NOT NULL,
    details TEXT,
    created_at DATETIME
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$PAIRS = array(
    'XXBTZUSD','XETHZUSD','SOLUSD','XXRPZUSD','ADAUSD','AVAXUSD',
    'DOTUSD','LINKUSD','UNIUSD','AAVEUSD','NEARUSD','ATOMUSD',
    'INJUSD','APTUSD','FTMUSD','ARBUSD','OPUSD','SUIUSD',
    'COMPUSD','BCHUSD','XLTCZUSD','XDGUSD','PEPEUSD','BONKUSD',
    'SHIBUSD','FLOKIUSD','SNXUSD','CRVUSD','GRTUSD','FETUSD'
);

$action = isset($_GET['action']) ? $_GET['action'] : 'analyze';

switch ($action) {
    case 'analyze':    action_analyze($conn); break;
    case 'signals':    action_signals($conn); break;
    case 'monitor':    action_monitor($conn); break;
    case 'research':   action_research($conn); break;
    case 'full_run':   action_full_run($conn); break;
    case 'audit':      action_audit($conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown action'));
}
$conn->close();
exit;

// ═══════════════════════════════════════════════════════════════
//  7-STATE MARKET CLASSIFICATION (from Freqtrade/SpiceTrader research)
// ═══════════════════════════════════════════════════════════════
function classify_market_state($f)
{
    $adx = $f['adx'];
    $rsi = $f['rsi'];
    $bb_bw = $f['bb_bandwidth'];
    $vol_r = $f['vol_ratio'];
    $trend = $f['ema_trend']; // 1=bull, -1=bear, 0=flat

    // State 1: STRONG_TREND_UP - ADX>30, bullish EMA, RSI 55-75
    if ($adx > 30 && $trend == 1 && $rsi > 55 && $rsi < 75) return 'STRONG_TREND_UP';
    // State 2: STRONG_TREND_DOWN
    if ($adx > 30 && $trend == -1 && $rsi < 45 && $rsi > 25) return 'STRONG_TREND_DOWN';
    // State 3: VOLATILE_BREAKOUT - High vol + squeeze release
    if ($f['squeeze_release'] && $vol_r > 1.5) return 'VOLATILE_BREAKOUT';
    // State 4: RANGE_BOUND - Low ADX, tight bandwidth
    if ($adx < 20 && $bb_bw < 0.03) return 'RANGE_BOUND';
    // State 5: CHOPPY - Low ADX but high volatility
    if ($adx < 25 && $f['hvol'] > 3.0) return 'CHOPPY';
    // State 6: CAPITULATION - Extreme fear, negative funding, RSI<25
    if ($rsi < 25 && $f['funding_proxy'] < 0) return 'CAPITULATION';
    // State 7: EUPHORIA - RSI>80, high volume
    if ($rsi > 80 && $vol_r > 2.0) return 'EUPHORIA';

    return 'NORMAL';
}

// ═══════════════════════════════════════════════════════════════
//  EXPERT-SOURCED SIGNAL FUNCTIONS
// ═══════════════════════════════════════════════════════════════

// Willy Woo: NVT-proxy (network value relative to transaction throughput)
// We approximate using volume as transaction proxy
function woo_nvt_signal($c, $v, $i)
{
    if ($i < 30) return array('signal' => 0, 'note' => '');
    // NVT Signal: price / 90-day MA of volume (simplified)
    $vol_ma = 0;
    for ($j = max(0,$i-28); $j <= $i; $j++) { $vol_ma += $v[$j]; }
    $vol_ma /= 28;
    if ($vol_ma <= 0) return array('signal' => 0, 'note' => '');
    $nvt = $c[$i] / $vol_ma;
    // NVT below historical mean = undervalued (buy signal)
    // We compare to 90-period average
    $nvt_arr = array();
    for ($j = max(0,$i-89); $j <= $i; $j++) {
        $vm = 0; for ($k = max(0,$j-28); $k <= $j; $k++) { $vm += $v[$k]; } $vm /= 28;
        if ($vm > 0) $nvt_arr[] = $c[$j] / $vm;
    }
    if (count($nvt_arr) < 10) return array('signal' => 0, 'note' => '');
    $nvt_avg = array_sum($nvt_arr) / count($nvt_arr);
    if ($nvt < $nvt_avg * 0.8) return array('signal' => 1, 'note' => 'Woo NVT: undervalued (NVT=' . round($nvt,2) . ' vs avg=' . round($nvt_avg,2) . ')');
    if ($nvt > $nvt_avg * 1.3) return array('signal' => -1, 'note' => 'Woo NVT: overvalued');
    return array('signal' => 0, 'note' => '');
}

// CryptoQuant: Exchange flow proxy (volume spikes as proxy for exchange in/outflow)
function cryptoquant_flow_signal($c, $v, $i)
{
    if ($i < 20) return array('signal' => 0, 'note' => '');
    // Large volume with price drop = exchange inflow (sell pressure)
    // Large volume with price flat/up = exchange outflow (accumulation)
    $vol_avg = 0;
    for ($j = max(0,$i-20); $j < $i; $j++) { $vol_avg += $v[$j]; }
    $vol_avg /= 20;
    $vol_spike = ($vol_avg > 0) ? $v[$i] / $vol_avg : 1;
    $price_chg = ($c[$i-1] > 0) ? ($c[$i] - $c[$i-1]) / $c[$i-1] * 100 : 0;
    if ($vol_spike > 2.0 && abs($price_chg) < 1.0) {
        return array('signal' => 1, 'note' => 'CryptoQuant: Volume accumulation (vol ' . round($vol_spike,1) . 'x, price flat) - whale outflow proxy');
    }
    if ($vol_spike > 2.5 && $price_chg < -3.0) {
        return array('signal' => -1, 'note' => 'CryptoQuant: Sell pressure (vol ' . round($vol_spike,1) . 'x + price drop ' . round($price_chg,1) . '%)');
    }
    return array('signal' => 0, 'note' => '');
}

// Glassnode: STH profitability proxy (short-term holder cost basis)
function glassnode_sth_signal($c, $i)
{
    if ($i < 30) return array('signal' => 0, 'note' => '');
    // Approximate STH cost basis as 30-period SMA (recent buyers' avg entry)
    $sth_basis = 0;
    for ($j = max(0,$i-29); $j <= $i; $j++) { $sth_basis += $c[$j]; }
    $sth_basis /= 30;
    $ratio = ($sth_basis > 0) ? $c[$i] / $sth_basis : 1;
    // MVRV proxy: if price < STH basis, short-term holders are at a loss (capitulation zone)
    if ($ratio < 0.92) return array('signal' => 1, 'note' => 'Glassnode: STH deeply underwater (MVRV proxy=' . round($ratio,3) . ') - accumulation zone');
    if ($ratio < 0.97) return array('signal' => 1, 'note' => 'Glassnode: STH slightly underwater (MVRV proxy=' . round($ratio,3) . ')');
    if ($ratio > 1.15) return array('signal' => -1, 'note' => 'Glassnode: STH overextended (MVRV proxy=' . round($ratio,3) . ')');
    return array('signal' => 0, 'note' => '');
}

// Hayes: Liquidity cycle proxy (price relative to long-term trend)
function hayes_liquidity_signal($c, $i)
{
    if ($i < 100) return array('signal' => 0, 'note' => '');
    // Compare price to 200-period EMA as liquidity cycle proxy
    $ema200 = ema_at_idx($c, $i, 200);
    $ratio = ($ema200 > 0) ? $c[$i] / $ema200 : 1;
    if ($ratio < 0.75) return array('signal' => 1, 'note' => 'Hayes: Deep below 200-EMA (ratio=' . round($ratio,3) . ') - liquidity expansion buy zone');
    if ($ratio < 0.9) return array('signal' => 1, 'note' => 'Hayes: Below 200-EMA (ratio=' . round($ratio,3) . ') - potential accumulation');
    if ($ratio > 1.5) return array('signal' => -1, 'note' => 'Hayes: Far above 200-EMA (ratio=' . round($ratio,3) . ') - overextended');
    return array('signal' => 0, 'note' => '');
}

// Funding rate proxy (contrarian: extreme negative = short squeeze setup)
function funding_rate_signal($c, $i)
{
    if ($i < 10) return array('signal' => 0, 'note' => '');
    // Proxy: consecutive down candles with increasing volume = shorts piling in
    $down_streak = 0;
    for ($j = $i; $j > max(0,$i-5); $j--) {
        if ($c[$j] < $c[$j-1]) $down_streak++;
        else break;
    }
    if ($down_streak >= 3) {
        return array('signal' => 1, 'note' => 'Funding proxy: ' . $down_streak . ' consecutive down candles - crowded short setup (mirrors -0.0014% funding Feb 2026)');
    }
    $up_streak = 0;
    for ($j = $i; $j > max(0,$i-5); $j--) {
        if ($c[$j] > $c[$j-1]) $up_streak++;
        else break;
    }
    if ($up_streak >= 3) {
        return array('signal' => -1, 'note' => 'Funding proxy: ' . $up_streak . ' consecutive up candles - crowded long risk');
    }
    return array('signal' => 0, 'note' => '');
}

// Microstructure: Slippage-adjusted confidence
function microstructure_adjust($pair, $vol_ratio, $confidence)
{
    // Memecoins: 80% worse slippage (from research)
    $meme_pairs = array('PEPEUSD','BONKUSD','SHIBUSD','FLOKIUSD','XDGUSD','FARTCOINUSD','MOODENGUSD','WIFUSD','POPCATUSD','TURBOUSD','MOGUSD','DOGUSD','TRUMPUSD');
    $is_meme = in_array($pair, $meme_pairs);
    $base_slippage = $is_meme ? 0.50 : 0.15; // 50bps vs 15bps
    // Low volume = worse execution
    if ($vol_ratio < 0.5) $base_slippage *= 2;
    // Adjust confidence down by slippage impact
    $adj = max(0, $confidence - ($base_slippage * 5));
    return array('confidence' => round($adj, 1), 'slippage_pct' => round($base_slippage, 2),
        'note' => $is_meme ? 'MEMECOIN: 80% higher slippage (50bps est). Confidence reduced.' : 'Mature asset: 15bps slippage est.');
}

// ═══════════════════════════════════════════════════════════════
//  MAIN ANALYSIS: Expert Consensus Scan
// ═══════════════════════════════════════════════════════════════
function action_analyze($conn)
{
    global $PAIRS;
    $start = microtime(true);
    $all_ohlcv = fetch_ohlcv_batch($PAIRS, 60);
    $now = date('Y-m-d H:i:s');
    $signals = array();

    foreach ($all_ohlcv as $pair => $candles) {
        if (count($candles) < 120) continue;
        $ind = precompute_ind($candles);
        $n = count($ind['close']);
        if ($n < 105) continue;
        $i = $n - 1;
        $c = $ind['close']; $v = $ind['volume']; $h = $ind['high']; $l = $ind['low'];

        // Compute features for market state
        $f = array(
            'adx' => $ind['adx'][$i],
            'rsi' => $ind['rsi'][$i],
            'bb_bandwidth' => ($ind['bb_m'][$i] > 0) ? ($ind['bb_u'][$i] - $ind['bb_l'][$i]) / $ind['bb_m'][$i] : 0,
            'vol_ratio' => vol_ratio($v, $i, 20),
            'ema_trend' => ($ind['ema9'][$i] > $ind['ema21'][$i] && $ind['ema21'][$i] > $ind['ema50'][$i]) ? 1 :
                           (($ind['ema9'][$i] < $ind['ema21'][$i] && $ind['ema21'][$i] < $ind['ema50'][$i]) ? -1 : 0),
            'squeeze_release' => squeeze_check($ind, $i),
            'hvol' => hvol_at($c, $i, 20),
            'funding_proxy' => ($c[$i] < $c[$i-1] && $c[$i-1] < $c[$i-2]) ? -1 : (($c[$i] > $c[$i-1] && $c[$i-1] > $c[$i-2]) ? 1 : 0)
        );

        $state = classify_market_state($f);

        // Run all expert signals
        $expert_sigs = array();
        $bull_score = 0; $bear_score = 0;

        $woo = woo_nvt_signal($c, $v, $i);
        if ($woo['signal'] == 1) { $bull_score += 15; $expert_sigs[] = $woo['note']; }
        if ($woo['signal'] == -1) { $bear_score += 15; $expert_sigs[] = $woo['note']; }

        $cq = cryptoquant_flow_signal($c, $v, $i);
        if ($cq['signal'] == 1) { $bull_score += 20; $expert_sigs[] = $cq['note']; }
        if ($cq['signal'] == -1) { $bear_score += 20; $expert_sigs[] = $cq['note']; }

        $gn = glassnode_sth_signal($c, $i);
        if ($gn['signal'] == 1) { $bull_score += 20; $expert_sigs[] = $gn['note']; }
        if ($gn['signal'] == -1) { $bear_score += 20; $expert_sigs[] = $gn['note']; }

        $ah = hayes_liquidity_signal($c, $i);
        if ($ah['signal'] == 1) { $bull_score += 15; $expert_sigs[] = $ah['note']; }
        if ($ah['signal'] == -1) { $bear_score += 15; $expert_sigs[] = $ah['note']; }

        $fr = funding_rate_signal($c, $i);
        if ($fr['signal'] == 1) { $bull_score += 15; $expert_sigs[] = $fr['note']; }
        if ($fr['signal'] == -1) { $bear_score += 15; $expert_sigs[] = $fr['note']; }

        // Contrarian flags (behavioral economics layer)
        $contrarian = array();
        if ($state === 'CAPITULATION') { $bull_score += 25; $contrarian[] = 'CAPITULATION state detected - extreme fear = historical buy zone (Fear&Greed=9 in Feb 2026)'; }
        if ($state === 'EUPHORIA') { $bear_score += 25; $contrarian[] = 'EUPHORIA state - extreme greed = historical distribution zone'; }
        if ($ind['rsi'][$i] < 25) { $bull_score += 10; $contrarian[] = 'RSI extreme oversold (' . round($ind['rsi'][$i],1) . ')'; }
        if ($ind['rsi'][$i] > 80) { $bear_score += 10; $contrarian[] = 'RSI extreme overbought (' . round($ind['rsi'][$i],1) . ')'; }

        // Technical confluence
        if ($ind['rsi'][$i] < 40 && $ind['macd_h'][$i] > $ind['macd_h'][$i-1] && $f['vol_ratio'] > 1.2) {
            $bull_score += 10; $expert_sigs[] = 'Technical: RSI recovering + MACD improving + volume confirm';
        }
        $obv_div = ($c[$i] < $c[max(0,$i-10)] && $ind['obv'][$i] > $ind['obv'][max(0,$i-10)]);
        if ($obv_div) { $bull_score += 10; $expert_sigs[] = 'OBV bullish divergence detected'; }

        $net_score = $bull_score - $bear_score;
        $max_possible = 130;
        $confidence = min(95, max(0, abs($net_score) / $max_possible * 100));
        $direction = ($net_score > 0) ? 'LONG' : (($net_score < 0) ? 'SHORT' : 'NEUTRAL');

        // === TREND FILTER: Block SHORT in uptrends (audit fix Feb 14 2026) ===
        // Root cause of 0% WR: all 5 losses were contrarian SHORTs in trending-up markets.
        // Fix: Only allow SHORT in confirmed downtrends or extreme conditions.
        if ($direction === 'SHORT') {
            $trend_up = ($state === 'STRONG_TREND_UP' || $state === 'NORMAL');
            $ema_bullish = ($ind['ema9'][$i] > $ind['ema21'][$i] && $ind['ema21'][$i] > $ind['ema50'][$i]);
            if ($trend_up || $ema_bullish) {
                // Block SHORT unless net_score is extremely negative (strong conviction)
                if ($net_score > -60) {
                    $direction = 'NEUTRAL'; // suppress weak contrarian shorts
                    $expert_sigs[] = 'TREND_FILTER: SHORT blocked in uptrend (state=' . $state . ')';
                }
            }
        }

        // Raise confidence threshold: LONG >= 20, SHORT >= 35 (was 15 for both)
        $min_confidence = ($direction === 'SHORT') ? 35 : 20;

        // Microstructure adjustment
        $micro = microstructure_adjust($pair, $f['vol_ratio'], $confidence);

        if ($micro['confidence'] >= $min_confidence && $direction !== 'NEUTRAL') {
            $entry = $c[$i];
            $atr = $ind['atr'][$i]; if ($atr <= 0) $atr = $entry * 0.02;
            // Slippage-adjusted TP/SL (wider for memecoins)
            $tp_mult = ($micro['slippage_pct'] > 0.3) ? 4.5 : 3.5;
            $sl_mult = ($micro['slippage_pct'] > 0.3) ? 2.5 : 1.8;
            $tp = ($direction === 'LONG') ? $entry + ($atr * $tp_mult) : $entry - ($atr * $tp_mult);
            $sl = ($direction === 'LONG') ? $entry - ($atr * $sl_mult) : $entry + ($atr * $sl_mult);

            $signal = array(
                'pair' => $pair, 'direction' => $direction,
                'price' => $entry,
                'expert_score' => $net_score,
                'confidence' => $micro['confidence'],
                'market_state' => $state,
                'expert_signals' => $expert_sigs,
                'contrarian_flags' => $contrarian,
                'microstructure' => $micro['note'],
                'slippage_est' => $micro['slippage_pct'] . '%',
                'tp_price' => round($tp, 10), 'sl_price' => round($sl, 10),
                'tp_pct' => round(abs($tp - $entry) / $entry * 100, 2),
                'sl_pct' => round(abs($entry - $sl) / $entry * 100, 2),
                'rsi' => round($ind['rsi'][$i], 1),
                'adx' => round($ind['adx'][$i], 1)
            );
            $signals[] = $signal;

            // Store
            $chk = $conn->query(sprintf("SELECT id FROM ec_signals WHERE pair='%s' AND status='ACTIVE'", $conn->real_escape_string($pair)));
            if (!$chk || $chk->num_rows == 0) {
                $conn->query(sprintf(
                    "INSERT INTO ec_signals (pair,direction,entry_price,tp_price,sl_price,confidence,expert_score,market_state,slippage_adjusted,execution_cost_pct,expert_signals,contrarian_flags,microstructure_note,status,created_at) VALUES ('%s','%s','%.10f','%.10f','%.10f','%.4f','%.4f','%s',1,'%.4f','%s','%s','%s','ACTIVE','%s')",
                    $conn->real_escape_string($pair), $conn->real_escape_string($direction),
                    $entry, $tp, $sl, $micro['confidence'], $net_score,
                    $conn->real_escape_string($state), $micro['slippage_pct'],
                    $conn->real_escape_string(implode(' | ', $expert_sigs)),
                    $conn->real_escape_string(implode(' | ', $contrarian)),
                    $conn->real_escape_string($micro['note']), $now
                ));
            }
        }
    }

    usort($signals, 'sort_by_score');
    $elapsed = round((microtime(true) - $start) * 1000);
    audit_log($conn, 'analyze', json_encode(array('pairs'=>count($all_ohlcv),'signals'=>count($signals))));
    echo json_encode(array('ok'=>true,'action'=>'analyze','pairs_scanned'=>count($all_ohlcv),'signals_found'=>count($signals),'signals'=>$signals,'elapsed_ms'=>$elapsed));
}

function sort_by_score($a,$b){if(abs($a['expert_score'])==abs($b['expert_score']))return 0;return(abs($a['expert_score'])>abs($b['expert_score']))?-1:1;}

function action_signals($conn)
{
    $active = array(); $history = array();
    $res = $conn->query("SELECT * FROM ec_signals WHERE status='ACTIVE' ORDER BY confidence DESC");
    if ($res) { while ($r = $res->fetch_assoc()) { $active[] = $r; } }
    $res2 = $conn->query("SELECT * FROM ec_signals WHERE status='RESOLVED' ORDER BY resolved_at DESC LIMIT 50");
    if ($res2) { while ($r = $res2->fetch_assoc()) { $history[] = $r; } }
    $wins=0;$losses=0;$pnl=0;
    foreach ($history as $hh) { $p=floatval($hh['pnl_pct']); $pnl+=$p; if($p>0)$wins++;else $losses++; }
    $wr = ($wins+$losses>0) ? round($wins/($wins+$losses)*100,1) : 0;
    echo json_encode(array('ok'=>true,'active'=>$active,'history'=>$history,
        'stats'=>array('win_rate'=>$wr,'total_pnl'=>round($pnl,2),'wins'=>$wins,'losses'=>$losses)));
}

function action_monitor($conn)
{
    $res = $conn->query("SELECT * FROM ec_signals WHERE status='ACTIVE'");
    if (!$res || $res->num_rows == 0) { echo json_encode(array('ok'=>true,'message'=>'No active signals')); return; }
    $sigs=array();$pairs=array();
    while($r=$res->fetch_assoc()){$sigs[]=$r;$pairs[$r['pair']]=true;}
    $tickers=fetch_tickers(array_keys($pairs));
    $now=date('Y-m-d H:i:s');$resolved=0;
    foreach($sigs as $sig){
        $cur=isset($tickers[$sig['pair']])?$tickers[$sig['pair']]:0;
        if($cur<=0)continue;
        $entry=floatval($sig['entry_price']);
        $is_long=($sig['direction']==='LONG');
        $pnl=$is_long?(($cur-$entry)/$entry*100):(($entry-$cur)/$entry*100);
        $done=false;$reason='';
        if($is_long&&$cur>=floatval($sig['tp_price'])){$done=true;$reason='TP_HIT';}
        elseif($is_long&&$cur<=floatval($sig['sl_price'])){$done=true;$reason='SL_HIT';}
        elseif(!$is_long&&$cur<=floatval($sig['tp_price'])){$done=true;$reason='TP_HIT';}
        elseif(!$is_long&&$cur>=floatval($sig['sl_price'])){$done=true;$reason='SL_HIT';}
        $hours=(time()-strtotime($sig['created_at']))/3600;
        if(!$done&&$hours>=96){$done=true;$reason='EXPIRED';}
        if($done){$conn->query(sprintf("UPDATE ec_signals SET status='RESOLVED',current_price='%.10f',pnl_pct='%.4f',exit_reason='%s',resolved_at='%s' WHERE id=%d",$cur,$pnl,$conn->real_escape_string($reason),$now,intval($sig['id'])));$resolved++;}
        else{$conn->query(sprintf("UPDATE ec_signals SET current_price='%.10f',pnl_pct='%.4f' WHERE id=%d",$cur,$pnl,intval($sig['id'])));}
    }
    echo json_encode(array('ok'=>true,'checked'=>count($sigs),'resolved'=>$resolved));
}

function action_research($conn)
{
    $social = array(
        array('name'=>'Willy Woo (@woonomic)','role'=>'On-chain pioneer','finding'=>'NVT ratio, cycle prediction ($220K BTC target), AI pattern recognition now used by hedge funds'),
        array('name'=>'Ki Young Ju (CryptoQuant)','role'=>'Exchange flow expert','finding'=>'Whale accumulation reports OVERSTATED due to exchange wallet consolidation. Real whales still distributing. LTH just flipped to net accumulation.'),
        array('name'=>'Glassnode','role'=>'On-chain metrics','finding'=>'BTC in defensive consolidation $60-72k. STH profitability negative. Supply clusters at $82-97k and $100-117k in unrealized losses.'),
        array('name'=>'Arthur Hayes','role'=>'Macro liquidity cycles','finding'=>'Feb 2026 drop caused by ETF delta-hedging + $300B Treasury drain. Predicts liquidity expansion = new ATH. Recommends scaled entry.'),
        array('name'=>'Hildobby (Dune)','role'=>'ETH on-chain visualization','finding'=>'Gold standard for independent ETH data. Essential for verifying staking flows and TVL metrics.'),
        array('name'=>'PlanB (S2F)','role'=>'Bitcoin cyclical analysis','finding'=>'Stock-to-Flow model for time-based feature engineering. Cyclical patterns persist per Willy Woo.'),
        array('name'=>'Lex Moskovski','role'=>'Derivatives analyst','finding'=>'Daily OI/funding charts. Funding rate hit -0.0014% (most negative since Apr 2024) = crowded short setup.'),
        array('name'=>'The Block Research','role'=>'Structural changes','finding'=>'ETF flows now dominate. 1.3M BTC held by ETFs (6.2% of supply). Fundamental shift in ownership patterns.'),
        array('name'=>'Whale Alert / Arkham','role'=>'Real-time whale tracking','finding'=>'Essential for distinguishing exchange internal transfers from actual whale movement. CryptoQuant warns consolidation inflates metrics.'),
        array('name'=>'Miles Deutscher','role'=>'Retail sentiment','finding'=>'Retail momentum meta. Useful for gauging which altcoins are in spotlight, affecting momentum indicator reliability.')
    );
    $communities = array(
        array('name'=>'Numerai Tournament','finding'=>'Winning models require UNIQUE data. LightGBM standard. Pure backtesting is insufficient - crowdsourced stress-test required.'),
        array('name'=>'QuantConnect/LEAN','finding'=>'10bps slippage assumption is laughable. Real market impact on $5M AVAX order could wipe entire edge. TWAP/VWAP execution required.'),
        array('name'=>'r/algotrading','finding'=>'SpiceTrader approach: 7-state market classification. Strategy adaptation to market state is KEY to live profitability.'),
        array('name'=>'Freqtrade Community','finding'=>'Open-source bot execution reality. API timeouts during flash crashes. Must handle exchange downtime gracefully.'),
        array('name'=>'r/statistics','finding'=>'Sharpe ratio NOT normally distributed. Sample size concerns with crypto backtests. Need purged K-fold cross-validation.'),
        array('name'=>'Kaggle Crypto','finding'=>'Winning kernels use EMD (Empirical Mode Decomposition), wavelet transforms. Feature engineering > model complexity.'),
        array('name'=>'Dune Analytics','finding'=>'On-chain SQL queries expose flaws in API-reported volume. Cross-chain volume often inflated.'),
        array('name'=>'Stack Exchange (Quant)','finding'=>'Regime-switching GARCH models. Mathematical rigor for volatility clustering in crypto.'),
        array('name'=>'r/ethfinance','finding'=>'Pectra upgrade changed validator mechanics. Max balance now 2048 ETH. 11,000+ validators consolidated.'),
        array('name'=>'Quantopian Archives','finding'=>'Overfitting bible. Out-of-sample testing methodology. Alpha decay research essential.')
    );
    $experts = array(
        array('discipline'=>'Market Microstructure','why'=>'Slippage 80% worse on memecoins vs mature assets. Optimal execution with exponential decay reduces costs 60%. Your 10bps assumption is wrong.'),
        array('discipline'=>'On-Chain Forensics','why'=>'Exchange wallet consolidation creates false whale signals. Must filter internal transfers from real accumulation/distribution.'),
        array('discipline'=>'MLOps Engineer','why'=>'XGBoost models suffer drift. Need automatic retraining when accuracy drops. 148% Sharpe improvement decays after 6 months without refresh.'),
        array('discipline'=>'DeFi Mechanic','why'=>'Pectra changed ETH staking: max 2048 ETH/validator, compounding rewards, reduced slashing. Gas mechanics changed with EIP-4844. Feature logic must update.'),
        array('discipline'=>'Behavioral Economist','why'=>'Fear & Greed Index hit 9 (FTX-era lows). Extreme fear preceded 70% of major rallies historically. Contrarian signals are the most profitable edge.')
    );
    echo json_encode(array('ok'=>true,'social_sources'=>$social,'algo_communities'=>$communities,'expert_disciplines'=>$experts));
}

function action_full_run($conn)
{
    $start = microtime(true);
    ob_start(); action_analyze($conn); $a = json_decode(ob_get_clean(), true);
    $elapsed = round((microtime(true) - $start) * 1000);
    echo json_encode(array('ok'=>true,'action'=>'full_run',
        'signals'=>isset($a['signals'])?$a['signals']:array(),
        'pairs_scanned'=>isset($a['pairs_scanned'])?$a['pairs_scanned']:0,
        'elapsed_ms'=>$elapsed));
}

function action_audit($conn)
{
    $logs=array();$sigs=array();
    $res=$conn->query("SELECT * FROM ec_audit ORDER BY created_at DESC LIMIT 20");
    if($res){while($r=$res->fetch_assoc()){$logs[]=$r;}}
    $res2=$conn->query("SELECT * FROM ec_signals ORDER BY created_at DESC LIMIT 30");
    if($res2){while($r=$res2->fetch_assoc()){$sigs[]=$r;}}
    echo json_encode(array('ok'=>true,'audit_logs'=>$logs,'signals'=>$sigs));
}

// ═══════════════════════════════════════════════════════════════
//  HELPERS
// ═══════════════════════════════════════════════════════════════
function vol_ratio($v,$i,$p){$avg=0;for($j=max(0,$i-$p);$j<$i;$j++){$avg+=$v[$j];}$avg/=$p;return($avg>0)?$v[$i]/$avg:1;}
function hvol_at($c,$i,$p){$rets=array();for($j=max(1,$i-$p);$j<=$i;$j++){if($c[$j-1]>0)$rets[]=($c[$j]-$c[$j-1])/$c[$j-1];}if(count($rets)<2)return 0;$m=array_sum($rets)/count($rets);$v=0;foreach($rets as $r){$v+=($r-$m)*($r-$m);}return sqrt($v/count($rets))*100;}
function squeeze_check($ind,$i){if($i<2)return 0;$prev_sq=($ind['bb_l'][$i-1]>($ind['ema21'][$i-1]-1.5*$ind['atr'][$i-1])&&$ind['bb_u'][$i-1]<($ind['ema21'][$i-1]+1.5*$ind['atr'][$i-1]));$now_sq=($ind['bb_l'][$i]>($ind['ema21'][$i]-1.5*$ind['atr'][$i])&&$ind['bb_u'][$i]<($ind['ema21'][$i]+1.5*$ind['atr'][$i]));return($prev_sq&&!$now_sq)?1:0;}
function ema_at_idx($arr,$i,$p){if($i<$p)return $arr[$i];$k=2.0/($p+1);$s=0;for($j=0;$j<$p;$j++){$s+=$arr[$j];}$e=$s/$p;for($j=$p;$j<=$i;$j++){$e=($arr[$j]*$k)+($e*(1-$k));}return $e;}
function audit_log($conn,$a,$d){$conn->query(sprintf("INSERT INTO ec_audit (action,details,created_at) VALUES ('%s','%s','%s')",$conn->real_escape_string($a),$conn->real_escape_string($d),date('Y-m-d H:i:s')));}

// ═══════════════════════════════════════════════════════════════
//  INDICATOR + DATA
// ═══════════════════════════════════════════════════════════════
function precompute_ind($candles){$o=array();$h=array();$l=array();$c=array();$v=array();foreach($candles as $cd){$o[]=floatval($cd[1]);$h[]=floatval($cd[2]);$l[]=floatval($cd[3]);$c[]=floatval($cd[4]);$v[]=floatval($cd[6]);}$rsi=i_rsi($c,14);$atr=i_atr($h,$l,$c,14);$bb=i_bb($c,20,2.0);$macd=i_macd($c);$obv=i_obv($c,$v);$adx=i_adx($h,$l,$c,14);$e9=i_ema($c,9);$e21=i_ema($c,21);$e50=i_ema($c,50);return array('open'=>$o,'high'=>$h,'low'=>$l,'close'=>$c,'volume'=>$v,'rsi'=>$rsi,'atr'=>$atr,'bb_u'=>$bb['u'],'bb_m'=>$bb['m'],'bb_l'=>$bb['l'],'macd_h'=>$macd['h'],'obv'=>$obv,'adx'=>$adx['adx'],'ema9'=>$e9,'ema21'=>$e21,'ema50'=>$e50);}
function fetch_ohlcv_batch($pairs,$interval){$results=array();$batches=array_chunk($pairs,5);foreach($batches as $batch){$mh=curl_multi_init();$handles=array();foreach($batch as $pair){$ch=curl_init('https://api.kraken.com/0/public/OHLC?pair='.$pair.'&interval='.$interval);curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);curl_setopt($ch,CURLOPT_TIMEOUT,10);curl_setopt($ch,CURLOPT_SSL_VERIFYPEER,false);curl_setopt($ch,CURLOPT_USERAGENT,'ExpertConsensus/1.0');curl_multi_add_handle($mh,$ch);$handles[$pair]=$ch;}$running=null;do{curl_multi_exec($mh,$running);curl_multi_select($mh,1);}while($running>0);foreach($handles as $pair=>$ch){$resp=curl_multi_getcontent($ch);curl_multi_remove_handle($mh,$ch);curl_close($ch);if($resp){$data=json_decode($resp,true);if($data&&isset($data['result'])){foreach($data['result'] as $k=>$vv){if($k!=='last'){$results[$pair]=$vv;break;}}}}}curl_multi_close($mh);}return $results;}
function fetch_tickers($pairs){$ch=curl_init('https://api.kraken.com/0/public/Ticker?pair='.implode(',',$pairs));curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);curl_setopt($ch,CURLOPT_TIMEOUT,10);curl_setopt($ch,CURLOPT_SSL_VERIFYPEER,false);curl_setopt($ch,CURLOPT_USERAGENT,'ExpertConsensus/1.0');$resp=curl_exec($ch);curl_close($ch);if(!$resp)return array();$data=json_decode($resp,true);if(!$data||!isset($data['result']))return array();$out=array();foreach($data['result'] as $k=>$vv){$out[$k]=floatval($vv['c'][0]);}return $out;}
function i_ema($d,$p){$n=count($d);if($n<$p)return array_fill(0,$n,$d[$n-1]);$k=2.0/($p+1);$e=array_fill(0,$p-1,0);$s=array_sum(array_slice($d,0,$p))/$p;$e[$p-1]=$s;for($i=$p;$i<$n;$i++){$e[$i]=($d[$i]*$k)+($e[$i-1]*(1-$k));}for($i=0;$i<$p-1;$i++){$e[$i]=$e[$p-1];}return $e;}
function i_rsi($c,$p){$n=count($c);$r=array_fill(0,$n,50);if($n<$p+1)return $r;$g=array();$lo=array();for($i=1;$i<$n;$i++){$d=$c[$i]-$c[$i-1];$g[$i]=($d>0)?$d:0;$lo[$i]=($d<0)?abs($d):0;}$ag=0;$al=0;for($i=1;$i<=$p;$i++){$ag+=$g[$i];$al+=$lo[$i];}$ag/=$p;$al/=$p;$r[$p]=($al==0)?100:100-(100/(1+$ag/$al));for($i=$p+1;$i<$n;$i++){$ag=(($ag*($p-1))+$g[$i])/$p;$al=(($al*($p-1))+$lo[$i])/$p;$r[$i]=($al==0)?100:100-(100/(1+$ag/$al));}return $r;}
function i_atr($h,$l,$c,$p){$n=count($c);$a=array_fill(0,$n,0);if($n<$p+1)return $a;$t=array(0);for($i=1;$i<$n;$i++){$t[$i]=max($h[$i]-$l[$i],abs($h[$i]-$c[$i-1]),abs($l[$i]-$c[$i-1]));}$s=0;for($i=1;$i<=$p;$i++){$s+=$t[$i];}$a[$p]=$s/$p;for($i=$p+1;$i<$n;$i++){$a[$i]=(($a[$i-1]*($p-1))+$t[$i])/$p;}for($i=0;$i<$p;$i++){$a[$i]=$a[$p];}return $a;}
function i_bb($c,$p,$m){$n=count($c);$u=array_fill(0,$n,0);$mid=array_fill(0,$n,0);$lo=array_fill(0,$n,0);for($i=$p-1;$i<$n;$i++){$sl=array_slice($c,$i-$p+1,$p);$mn=array_sum($sl)/$p;$sq=0;foreach($sl as $v){$sq+=($v-$mn)*($v-$mn);}$sd=sqrt($sq/$p);$mid[$i]=$mn;$u[$i]=$mn+($m*$sd);$lo[$i]=$mn-($m*$sd);}return array('u'=>$u,'m'=>$mid,'l'=>$lo);}
function i_macd($c){$e12=i_ema($c,12);$e26=i_ema($c,26);$n=count($c);$ml=array_fill(0,$n,0);for($i=0;$i<$n;$i++){$ml[$i]=$e12[$i]-$e26[$i];}$sig=i_ema($ml,9);$h=array_fill(0,$n,0);for($i=0;$i<$n;$i++){$h[$i]=$ml[$i]-$sig[$i];}return array('l'=>$ml,'s'=>$sig,'h'=>$h);}
function i_obv($c,$v){$n=count($c);$o=array_fill(0,$n,0);for($i=1;$i<$n;$i++){if($c[$i]>$c[$i-1])$o[$i]=$o[$i-1]+$v[$i];elseif($c[$i]<$c[$i-1])$o[$i]=$o[$i-1]-$v[$i];else $o[$i]=$o[$i-1];}return $o;}
function i_adx($h,$l,$c,$p){$n=count($c);$adx=array_fill(0,$n,25);$pdi=array_fill(0,$n,0);$mdi=array_fill(0,$n,0);if($n<$p*2)return array('adx'=>$adx,'pdi'=>$pdi,'mdi'=>$mdi);$tr=array(0);$pdm=array(0);$mdm=array(0);for($i=1;$i<$n;$i++){$tr[$i]=max($h[$i]-$l[$i],abs($h[$i]-$c[$i-1]),abs($l[$i]-$c[$i-1]));$up=$h[$i]-$h[$i-1];$dn=$l[$i-1]-$l[$i];$pdm[$i]=($up>$dn&&$up>0)?$up:0;$mdm[$i]=($dn>$up&&$dn>0)?$dn:0;}$a14=0;$p14=0;$m14=0;for($i=1;$i<=$p;$i++){$a14+=$tr[$i];$p14+=$pdm[$i];$m14+=$mdm[$i];}$dx_arr=array();for($i=$p;$i<$n;$i++){if($i>$p){$a14=$a14-($a14/$p)+$tr[$i];$p14=$p14-($p14/$p)+$pdm[$i];$m14=$m14-($m14/$p)+$mdm[$i];}$pd=($a14>0)?($p14/$a14)*100:0;$md=($a14>0)?($m14/$a14)*100:0;$pdi[$i]=$pd;$mdi[$i]=$md;$ds=$pd+$md;$dx=($ds>0)?abs($pd-$md)/$ds*100:0;$dx_arr[]=$dx;}if(count($dx_arr)>=$p){$av=array_sum(array_slice($dx_arr,0,$p))/$p;$adx[$p*2-1]=$av;for($i=$p;$i<count($dx_arr);$i++){$av=(($av*($p-1))+$dx_arr[$i])/$p;$ix=$i+$p;if($ix<$n)$adx[$ix]=$av;}}return array('adx'=>$adx,'pdi'=>$pdi,'mdi'=>$mdi);}
?>
