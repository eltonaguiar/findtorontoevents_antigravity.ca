<?php
/**
 * Algorithm Battle Royale v2.0
 * 10 competing algorithms + AI Grok picks + consensus analysis.
 * Uses real Kraken OHLCV data and technical indicators.
 *
 * ACADEMIC/TECHNICAL (5):
 *   1. RSI Mean Reversion      — Buy RSI<30, Sell RSI>70
 *   2. MACD Crossover           — Signal line cross
 *   3. Bollinger Band Squeeze   — Buy lower band + volume
 *   4. Triple EMA Crossover     — 9/26/55 EMA system
 *   5. Ichimoku Cloud Breakout  — Price vs cloud + TK cross
 *
 * SOCIAL/REDDIT (5):
 *   6. Momentum + BTC Regime    — Cross-sectional momentum with BTC filter
 *   7. StochRSI + Volume        — Stochastic RSI cross + volume filter
 *   8. Funding Rate Contrarian  — VWAP deviation as funding proxy
 *   9. Whale Accumulation       — Volume spike + range compression
 *  10. Multi-Confluence Score   — 8-component scoring system
 *
 * Actions:
 *   run         — Run all 10 algos on all coins, seed predictions
 *   consensus   — Cross-reference picks, find overlaps
 *   leaderboard — Show algo win rates and rankings
 *   status      — Current state of all algo predictions
 *   monitor     — Check live prices and auto-resolve
 *
 * PHP 5.2 compatible.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

error_reporting(0);
ini_set('display_errors', '0');

$API_KEY = 'algo_battle2026';

$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) {
    echo json_encode(array('ok' => false, 'error' => 'DB connection failed'));
    exit;
}
$conn->set_charset('utf8');

$conn->query("CREATE TABLE IF NOT EXISTS algo_battle_preds (
    id INT AUTO_INCREMENT PRIMARY KEY,
    batch_id VARCHAR(50) NOT NULL,
    algo_id VARCHAR(30) NOT NULL,
    algo_name VARCHAR(80) NOT NULL,
    algo_source VARCHAR(20) NOT NULL DEFAULT 'ACADEMIC',
    symbol VARCHAR(20) NOT NULL,
    kraken_pair VARCHAR(30) NOT NULL,
    direction VARCHAR(10) NOT NULL DEFAULT 'LONG',
    entry_price DECIMAL(20,10) NOT NULL,
    current_price DECIMAL(20,10) DEFAULT NULL,
    tp_price DECIMAL(20,10) NOT NULL,
    sl_price DECIMAL(20,10) NOT NULL,
    tp_pct DECIMAL(8,4) NOT NULL,
    sl_pct DECIMAL(8,4) NOT NULL,
    signal_strength DECIMAL(8,4) DEFAULT 0,
    confidence VARCHAR(20) NOT NULL,
    thesis TEXT NOT NULL,
    timeframe VARCHAR(20) NOT NULL DEFAULT '48h',
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    pnl_pct DECIMAL(8,4) DEFAULT NULL,
    peak_pnl_pct DECIMAL(8,4) DEFAULT NULL,
    trough_pnl_pct DECIMAL(8,4) DEFAULT NULL,
    exit_price DECIMAL(20,10) DEFAULT NULL,
    exit_reason VARCHAR(50) DEFAULT NULL,
    consensus_count INT DEFAULT 0,
    checks_count INT DEFAULT 0,
    last_check DATETIME DEFAULT NULL,
    created_at DATETIME NOT NULL,
    resolved_at DATETIME DEFAULT NULL,
    INDEX idx_status (status),
    INDEX idx_algo (algo_id),
    INDEX idx_batch (batch_id),
    INDEX idx_symbol (symbol),
    INDEX idx_consensus (consensus_count)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? $_GET['action'] : 'status';

switch ($action) {
    case 'run':
        _require_key();
        _run_all_algos($conn);
        break;
    case 'consensus':
        _consensus_analysis($conn);
        break;
    case 'leaderboard':
        _leaderboard($conn);
        break;
    case 'status':
        _status($conn);
        break;
    case 'monitor':
        _monitor($conn);
        break;
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}
$conn->close();

function _require_key() {
    $key = isset($_GET['key']) ? $_GET['key'] : '';
    if ($key !== 'algo_battle2026') { echo json_encode(array('ok' => false, 'error' => 'Invalid key')); exit; }
}

// ── Kraken data fetchers ──
function _fetch_ohlcv($pair, $interval) {
    $url = 'https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=' . $interval;
    $ch = curl_init($url); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); curl_setopt($ch, CURLOPT_USERAGENT, 'AlgoBattle/2.0');
    $resp = curl_exec($ch); curl_close($ch);
    if (!$resp) return array();
    $data = json_decode($resp, true);
    if (!$data || !isset($data['result'])) return array();
    $candles = array();
    foreach ($data['result'] as $key => $val) {
        if ($key === 'last') continue;
        foreach ($val as $c) {
            $candles[] = array('time'=>intval($c[0]),'open'=>floatval($c[1]),'high'=>floatval($c[2]),'low'=>floatval($c[3]),'close'=>floatval($c[4]),'vwap'=>floatval($c[5]),'volume'=>floatval($c[6]),'count'=>intval($c[7]));
        }
    }
    return $candles;
}

function _fetch_ticker($pair) {
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . $pair;
    $ch = curl_init($url); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); $resp = curl_exec($ch); curl_close($ch);
    if (!$resp) return null;
    $data = json_decode($resp, true);
    if (!$data || !isset($data['result'])) return null;
    foreach ($data['result'] as $k => $v) {
        return array('price'=>floatval($v['c'][0]),'high24'=>floatval($v['h'][1]),'low24'=>floatval($v['l'][1]),'vwap24'=>floatval($v['p'][1]),'vol24'=>floatval($v['v'][1]),'open24'=>floatval($v['o']));
    }
    return null;
}

// ── Indicator library ──
function _ema($d,$p){$e=array();$m=2.0/($p+1);$e[0]=$d[0];for($i=1;$i<count($d);$i++){$e[$i]=($d[$i]-$e[$i-1])*$m+$e[$i-1];}return $e;}

function _sma($d,$p){$s=array();for($i=0;$i<count($d);$i++){if($i<$p-1){$s[$i]=null;continue;}$sum=0;for($j=$i-$p+1;$j<=$i;$j++)$sum+=$d[$j];$s[$i]=$sum/$p;}return $s;}

function _rsi($c,$p){$r=array();$g=array();$l=array();$pag=0;$pal=0;for($i=0;$i<count($c);$i++){if($i===0){$r[]=50;continue;}$ch=$c[$i]-$c[$i-1];$g[]=$ch>0?$ch:0;$l[]=$ch<0?abs($ch):0;if(count($g)<$p){$r[]=50;continue;}if(count($g)===$p){$ag=array_sum(array_slice($g,-$p))/$p;$al=array_sum(array_slice($l,-$p))/$p;}else{$ag=($pag*($p-1)+end($g))/$p;$al=($pal*($p-1)+end($l))/$p;}$pag=$ag;$pal=$al;$r[]=$al==0?100:100-(100/(1+$ag/$al));}return $r;}

function _macd($c,$f,$s,$sp){$ef=_ema($c,$f);$es=_ema($c,$s);$ml=array();for($i=0;$i<count($c);$i++)$ml[$i]=$ef[$i]-$es[$i];$sl=_ema($ml,$sp);$h=array();for($i=0;$i<count($c);$i++)$h[$i]=$ml[$i]-$sl[$i];return array('macd'=>$ml,'signal'=>$sl,'hist'=>$h);}

function _bollinger($c,$p,$m){$s=_sma($c,$p);$u=array();$l=array();for($i=0;$i<count($c);$i++){if($s[$i]===null){$u[$i]=null;$l[$i]=null;continue;}$sl=array_slice($c,max(0,$i-$p+1),$p);$mn=array_sum($sl)/count($sl);$v=0;foreach($sl as $x)$v+=($x-$mn)*($x-$mn);$sd=sqrt($v/count($sl));$u[$i]=$s[$i]+$m*$sd;$l[$i]=$s[$i]-$m*$sd;}return array('mid'=>$s,'up'=>$u,'lo'=>$l);}

function _stoch_rsi($c,$rp,$sp,$ks,$ds){$r=_rsi($c,$rp);$sk=array();for($i=0;$i<count($r);$i++){if($i<$sp-1){$sk[$i]=50;continue;}$sl=array_slice($r,$i-$sp+1,$sp);$mn=min($sl);$mx=max($sl);$sk[$i]=($mx==$mn)?50:(($r[$i]-$mn)/($mx-$mn))*100;}$k=_sma($sk,$ks);$d=_sma($sk,$ds);for($i=0;$i<count($k);$i++){if($k[$i]===null)$k[$i]=50;if($d[$i]===null)$d[$i]=50;}return array('k'=>$k,'d'=>$d);}

function _midpoint($h,$l,$p){$r=array();for($i=0;$i<count($h);$i++){if($i<$p-1){$r[$i]=($h[$i]+$l[$i])/2;continue;}$r[$i]=(max(array_slice($h,$i-$p+1,$p))+min(array_slice($l,$i-$p+1,$p)))/2;}return $r;}

// ── THE 10 ALGORITHMS ──

function algo_rsi($candles,$ticker){
    $c=array();foreach($candles as $x)$c[]=$x['close'];$r=_rsi($c,14);$n=count($c);$rv=$r[$n-1];$rp=$r[$n-2];
    if($rv<30)return array('signal'=>'LONG','strength'=>round((30-$rv)/30,4),'thesis'=>'RSI='.$rv.' oversold(<30). Academic: RSI mean-reversion outperformed B&H on BTC,ETH,BNB,ADA,XRP.');
    if($rv>70)return array('signal'=>'SHORT','strength'=>round(($rv-70)/30,4),'thesis'=>'RSI='.$rv.' overbought(>70). Mean reversion to 50-60 zone expected.');
    if($rv<40&&$rp<$rv)return array('signal'=>'LONG','strength'=>0.3,'thesis'=>'RSI='.$rv.' recovering from near-oversold. Weak buy.');
    if($rv>60&&$rp>$rv)return array('signal'=>'SHORT','strength'=>0.3,'thesis'=>'RSI='.$rv.' declining from near-overbought. Weak sell.');
    return array('signal'=>'HOLD','strength'=>0,'thesis'=>'RSI='.$rv.' neutral zone.');
}

function algo_macd($candles,$ticker){
    $c=array();foreach($candles as $x)$c[]=$x['close'];$m=_macd($c,12,26,9);$n=count($c);
    $mn=$m['macd'][$n-1];$sn=$m['signal'][$n-1];$mp=$m['macd'][$n-2];$sp=$m['signal'][$n-2];$hn=$m['hist'][$n-1];$hp=$m['hist'][$n-2];
    if($mp<=$sp&&$mn>$sn)return array('signal'=>'LONG','strength'=>min(abs($hn)/max(abs($mn),0.0001),1),'thesis'=>'MACD bullish crossover. Springer 2024: outperformed B&H for BTC,BNB,XRP.');
    if($mp>=$sp&&$mn<$sn)return array('signal'=>'SHORT','strength'=>min(abs($hn)/max(abs($mn),0.0001),1),'thesis'=>'MACD bearish crossover. Histogram negative.');
    if($hn>0&&$hn>$hp)return array('signal'=>'LONG','strength'=>0.3,'thesis'=>'MACD histogram expanding positive.');
    if($hn<0&&$hn<$hp)return array('signal'=>'SHORT','strength'=>0.3,'thesis'=>'MACD histogram expanding negative.');
    return array('signal'=>'HOLD','strength'=>0,'thesis'=>'MACD neutral.');
}

function algo_bb($candles,$ticker){
    $c=array();$v=array();foreach($candles as $x){$c[]=$x['close'];$v[]=$x['volume'];}
    $bb=_bollinger($c,20,2);$n=count($c);$p=$c[$n-1];$u=$bb['up'][$n-1];$l=$bb['lo'][$n-1];$mid=$bb['mid'][$n-1];
    if($u===null)return array('signal'=>'HOLD','strength'=>0,'thesis'=>'Insufficient BB data.');
    $bw=($u-$l)/$mid;$av=array_sum(array_slice($v,-20))/20;$vr=$v[$n-1]/max($av,0.01);$pb=($p-$l)/max($u-$l,0.0001);
    if($pb<0.15&&$vr>1.2)return array('signal'=>'LONG','strength'=>min((0.15-$pb)*5+($vr-1)*0.3,1),'thesis'=>'BB '.round($pb*100,1).'% (lower band). Vol '.round($vr,1).'x. Reversal expected.');
    if($pb>0.85&&$vr>1.2)return array('signal'=>'SHORT','strength'=>min(($pb-0.85)*5+($vr-1)*0.3,1),'thesis'=>'BB '.round($pb*100,1).'% (upper band). Vol '.round($vr,1).'x. Mean reversion likely.');
    if($bw<0.03&&$vr>1.5){if($p>$mid)return array('signal'=>'LONG','strength'=>0.5,'thesis'=>'BB squeeze breakout UP. Width='.round($bw*100,2).'%.');return array('signal'=>'SHORT','strength'=>0.5,'thesis'=>'BB squeeze breakout DOWN.');}
    return array('signal'=>'HOLD','strength'=>0,'thesis'=>'BB neutral. %B='.round($pb*100,1));
}

function algo_ema3($candles,$ticker){
    $c=array();foreach($candles as $x)$c[]=$x['close'];$n=count($c);
    $e9=_ema($c,9);$e26=_ema($c,26);$e55=_ema($c,55);
    $a=$e9[$n-1];$b=$e26[$n-1];$d=$e55[$n-1];$ap=$e9[$n-2];$bp=$e26[$n-2];
    if($a>$b&&$b>$d){if($ap<=$bp)return array('signal'=>'LONG','strength'=>0.9,'thesis'=>'Triple EMA fresh bullish crossover! EMA9>EMA26>EMA55. Golden Momentum Capture.');return array('signal'=>'LONG','strength'=>0.5,'thesis'=>'Triple EMA bullish alignment.');}
    if($a<$b&&$b<$d){if($ap>=$bp)return array('signal'=>'SHORT','strength'=>0.9,'thesis'=>'Triple EMA bearish crossover. Death cross.');return array('signal'=>'SHORT','strength'=>0.5,'thesis'=>'Triple EMA bearish alignment.');}
    return array('signal'=>'HOLD','strength'=>0,'thesis'=>'EMAs mixed.');
}

function algo_ichimoku($candles,$ticker){
    $c=array();$h=array();$l=array();foreach($candles as $x){$c[]=$x['close'];$h[]=$x['high'];$l[]=$x['low'];}$n=count($c);
    $tk=_midpoint($h,$l,9);$kj=_midpoint($h,$l,26);$sb=_midpoint($h,$l,52);
    $t=$tk[$n-1];$k=$kj[$n-1];$tp=$tk[$n-2];$kp=$kj[$n-2];$p=$c[$n-1];
    $ci=max(0,$n-27);$sa=($tk[$ci]+$kj[$ci])/2;$sbb=$sb[$ci];$ct=max($sa,$sbb);$cb=min($sa,$sbb);
    if($p>$ct&&$t>$k&&$tp<=$kp)return array('signal'=>'LONG','strength'=>0.9,'thesis'=>'Ichimoku bullish breakout. Price above cloud + TK cross.');
    if($p>$ct&&$t>$k)return array('signal'=>'LONG','strength'=>0.5,'thesis'=>'Price above Ichimoku cloud, bullish TK.');
    if($p<$cb&&$t<$k&&$tp>=$kp)return array('signal'=>'SHORT','strength'=>0.9,'thesis'=>'Ichimoku bearish breakdown.');
    if($p<$cb&&$t<$k)return array('signal'=>'SHORT','strength'=>0.5,'thesis'=>'Price below cloud, bearish TK.');
    return array('signal'=>'HOLD','strength'=>0,'thesis'=>'Inside Ichimoku cloud.');
}

function algo_momentum_regime($candles,$ticker,$btc_candles){
    $c=array();foreach($candles as $x)$c[]=$x['close'];$n=count($c);
    $m24=($c[$n-1]-$c[max(0,$n-25)])/$c[max(0,$n-25)]*100;
    $m7d=($c[$n-1]-$c[max(0,$n-168)])/$c[max(0,$n-168)]*100;
    $bc=array();foreach($btc_candles as $x)$bc[]=$x['close'];$be=_ema($bc,50);$bn=count($bc);$risk=$bc[$bn-1]>$be[$bn-1];
    if($risk){if($m24>3&&$m7d>5)return array('signal'=>'LONG','strength'=>min($m24/10+$m7d/20,1),'thesis'=>'Momentum+Regime: BTC risk-on. +'.round($m24,1).'% 24h, +'.round($m7d,1).'% 7d. PyQuantLab 12-655% annual.');if($m24<-3)return array('signal'=>'LONG','strength'=>0.3,'thesis'=>'BTC risk-on, coin dipping '.round($m24,1).'%. Dip buy.');}
    else{if($m24<-3)return array('signal'=>'SHORT','strength'=>min(abs($m24)/15,1),'thesis'=>'BTC risk-off. Coin falling '.round($m24,1).'%.');}
    return array('signal'=>'HOLD','strength'=>0,'thesis'=>'Momentum neutral. BTC regime: '.($risk?'ON':'OFF'));
}

function algo_stochrsi($candles,$ticker){
    $c=array();$v=array();foreach($candles as $x){$c[]=$x['close'];$v[]=$x['volume'];}$n=count($c);
    $sr=_stoch_rsi($c,14,14,3,3);$kn=$sr['k'][$n-1];$dn=$sr['d'][$n-1];$kp=$sr['k'][$n-2];$dp=$sr['d'][$n-2];
    $av=array_sum(array_slice($v,-7))/7;$vr=$v[$n-1]/max($av,0.01);
    if($kp<=$dp&&$kn>$dn&&$kn<30&&$vr>1.0)return array('signal'=>'LONG','strength'=>min(0.6+($vr-1)*0.2,1),'thesis'=>'StochRSI bullish cross in oversold (K='.round($kn,1).'). Vol '.round($vr,1).'x. Reddit community strategy.');
    if($kp>=$dp&&$kn<$dn&&$kn>70&&$vr>1.0)return array('signal'=>'SHORT','strength'=>min(0.6+($vr-1)*0.2,1),'thesis'=>'StochRSI bearish cross in overbought (K='.round($kn,1).'). Vol confirms.');
    if($kn<10)return array('signal'=>'LONG','strength'=>0.4,'thesis'=>'StochRSI deeply oversold K='.round($kn,1).'.');
    if($kn>90)return array('signal'=>'SHORT','strength'=>0.4,'thesis'=>'StochRSI deeply overbought K='.round($kn,1).'.');
    return array('signal'=>'HOLD','strength'=>0,'thesis'=>'StochRSI neutral K='.round($kn,1));
}

function algo_funding($candles,$ticker){
    $p=$ticker['price'];$vw=$ticker['vwap24'];$dev=(($p-$vw)/$vw)*100;
    if($dev>3)return array('signal'=>'SHORT','strength'=>min($dev/8,1),'thesis'=>'Funding Contrarian: Price '.round($dev,2).'% above VWAP. Overcrowded longs, squeeze risk.');
    if($dev<-3)return array('signal'=>'LONG','strength'=>min(abs($dev)/8,1),'thesis'=>'Funding Contrarian: Price '.round($dev,2).'% below VWAP. Shorts vulnerable.');
    return array('signal'=>'HOLD','strength'=>0,'thesis'=>'VWAP deviation '.round($dev,2).'% - neutral.');
}

function algo_whale($candles,$ticker){
    $c=array();$v=array();$h=array();$l=array();foreach($candles as $x){$c[]=$x['close'];$v[]=$x['volume'];$h[]=$x['high'];$l[]=$x['low'];}$n=count($c);
    $av20=array_sum(array_slice($v,-20))/20;$rv=array_sum(array_slice($v,-5))/5;$vs=$rv/max($av20,0.01);
    $rr=0;for($i=$n-5;$i<$n;$i++)$rr+=($h[$i]-$l[$i])/max($c[$i],0.01);$rr/=5;
    $or=0;for($i=$n-25;$i<$n-5;$i++)$or+=($h[$i]-$l[$i])/max($c[$i],0.01);$or/=20;
    $rc=($or>0)?$rr/$or:1;$pc=($c[$n-1]-$c[max(0,$n-6)])/$c[max(0,$n-6)]*100;
    if($vs>1.5&&$rc<0.7&&$pc>-1)return array('signal'=>'LONG','strength'=>min(($vs-1)*0.4+(1-$rc)*0.3,1),'thesis'=>'Whale Accumulation: Vol '.round($vs,1).'x + '.round((1-$rc)*100,0).'% range compression. Supply being absorbed.');
    if($vs>2.0&&$pc<-2)return array('signal'=>'SHORT','strength'=>min(($vs-1)*0.3,1),'thesis'=>'Whale Distribution: Vol '.round($vs,1).'x + price dropping '.round($pc,1).'%.');
    return array('signal'=>'HOLD','strength'=>0,'thesis'=>'No whale pattern. Vol ratio '.round($vs,1).'x.');
}

function algo_confluence($candles,$ticker){
    $c=array();$v=array();foreach($candles as $x){$c[]=$x['close'];$v[]=$x['volume'];}$n=count($c);$p=$c[$n-1];
    $bull=0;$bear=0;$comp=array();
    $e20=_ema($c,20);$e50=_ema($c,50);
    if($e20[$n-1]>$e50[$n-1]){$bull++;$comp[]='EMA20>50';}else{$bear++;$comp[]='EMA20<50';}
    if($p>$e20[$n-1]){$bull++;$comp[]='P>EMA20';}else{$bear++;$comp[]='P<EMA20';}
    $r=_rsi($c,14);if($r[$n-1]>50){$bull++;$comp[]='RSI'.round($r[$n-1],0);}else{$bear++;$comp[]='RSI'.round($r[$n-1],0);}
    $m=_macd($c,12,26,9);if($m['hist'][$n-1]>0){$bull++;$comp[]='MACD+';}else{$bear++;$comp[]='MACD-';}
    $av=array_sum(array_slice($v,-20))/20;if($v[$n-1]>$av){$bull++;$comp[]='Vol+';}else{$bear++;$comp[]='Vol-';}
    if($p>$ticker['vwap24']){$bull++;$comp[]='P>VWAP';}else{$bear++;$comp[]='P<VWAP';}
    if($c[$n-1]>$c[$n-3]){$bull++;$comp[]='HL';}else{$bear++;$comp[]='LL';}
    $mm=($c[$n-1]-$c[max(0,$n-6)])/$c[max(0,$n-6)]*100;if($mm>0){$bull++;$comp[]='Mom+';}else{$bear++;$comp[]='Mom-';}
    if($bull>=6)return array('signal'=>'LONG','strength'=>$bull/8,'thesis'=>'Multi-Confluence BULL '.$bull.'/8: '.implode(',',$comp).'. Reddit: 6+ = high prob.');
    if($bear>=6)return array('signal'=>'SHORT','strength'=>$bear/8,'thesis'=>'Multi-Confluence BEAR '.$bear.'/8: '.implode(',',$comp).'.');
    return array('signal'=>'HOLD','strength'=>0,'thesis'=>'Mixed '.$bull.'B/'.$bear.'b: '.implode(',',$comp));
}

// ── RUN ALL ──
function _run_all_algos($conn){
    $start=microtime(true);
    $coins=array(
        array('s'=>'BTC','p'=>'XXBTZUSD'),array('s'=>'ETH','p'=>'XETHZUSD'),array('s'=>'SOL','p'=>'SOLUSD'),
        array('s'=>'BNB','p'=>'BNBUSD'),array('s'=>'XRP','p'=>'XXRPZUSD'),array('s'=>'DOGE','p'=>'XDGUSD'),
        array('s'=>'ADA','p'=>'ADAUSD'),array('s'=>'LINK','p'=>'LINKUSD'),array('s'=>'AVAX','p'=>'AVAXUSD'),
        array('s'=>'ATOM','p'=>'ATOMUSD'),array('s'=>'DOT','p'=>'DOTUSD'),array('s'=>'UNI','p'=>'UNIUSD'),
        array('s'=>'AAVE','p'=>'AAVEUSD'),array('s'=>'NEAR','p'=>'NEARUSD'),array('s'=>'LTC','p'=>'XLTCZUSD')
    );
    $algos=array(
        array('id'=>'rsi','name'=>'RSI Mean Reversion','src'=>'ACADEMIC','func'=>'algo_rsi','tp'=>5,'sl'=>2.5),
        array('id'=>'macd','name'=>'MACD Crossover','src'=>'ACADEMIC','func'=>'algo_macd','tp'=>5,'sl'=>2.5),
        array('id'=>'bb','name'=>'Bollinger Squeeze','src'=>'ACADEMIC','func'=>'algo_bb','tp'=>5,'sl'=>2.5),
        array('id'=>'ema3','name'=>'Triple EMA Cross','src'=>'ACADEMIC','func'=>'algo_ema3','tp'=>6,'sl'=>3),
        array('id'=>'ichimoku','name'=>'Ichimoku Cloud','src'=>'ACADEMIC','func'=>'algo_ichimoku','tp'=>6,'sl'=>3),
        array('id'=>'momreg','name'=>'Momentum+BTC Regime','src'=>'SOCIAL','func'=>'algo_momentum_regime','tp'=>6,'sl'=>3),
        array('id'=>'stochrsi','name'=>'StochRSI+Volume','src'=>'SOCIAL','func'=>'algo_stochrsi','tp'=>5,'sl'=>2.5),
        array('id'=>'funding','name'=>'Funding Contrarian','src'=>'SOCIAL','func'=>'algo_funding','tp'=>4,'sl'=>2),
        array('id'=>'whale','name'=>'Whale Accumulation','src'=>'SOCIAL','func'=>'algo_whale','tp'=>6,'sl'=>3),
        array('id'=>'confluence','name'=>'Multi-Confluence','src'=>'SOCIAL','func'=>'algo_confluence','tp'=>5,'sl'=>2.5)
    );

    $btc_candles=_fetch_ohlcv('XXBTZUSD',60);
    sleep(1);
    $batch_id='battle_'.date('Y-m-d_H-i');
    $all=array();$pred_count=0;

    foreach($coins as $ci=>$coin){
        if($ci>0)usleep(600000);
        $candles=($coin['p']==='XXBTZUSD')?$btc_candles:_fetch_ohlcv($coin['p'],60);
        if(count($candles)<60){$all[$coin['s']]=array('error'=>'No data');continue;}
        $ticker=_fetch_ticker($coin['p']);
        if(!$ticker){$all[$coin['s']]=array('error'=>'No ticker');continue;}
        $sigs=array();
        foreach($algos as $algo){
            $func_name=$algo['func'];
            $r=($func_name==='algo_momentum_regime')?$func_name($candles,$ticker,$btc_candles):$func_name($candles,$ticker);
            $r['algo_id']=$algo['id'];$r['algo_name']=$algo['name'];$r['algo_source']=$algo['src'];
            if($r['signal']!=='HOLD'&&$r['strength']>=0.3){
                $dir=$r['signal'];$entry=$ticker['price'];$tp=$algo['tp'];$sl=$algo['sl'];
                $tpp=$dir==='LONG'?$entry*(1+$tp/100):$entry*(1-$tp/100);
                $slp=$dir==='LONG'?$entry*(1-$sl/100):$entry*(1+$sl/100);
                $conf='LEAN';if($r['strength']>=0.7)$conf='HIGH';elseif($r['strength']>=0.4)$conf='MEDIUM';
                $sql=sprintf("INSERT INTO algo_battle_preds(batch_id,algo_id,algo_name,algo_source,symbol,kraken_pair,direction,entry_price,tp_price,sl_price,tp_pct,sl_pct,signal_strength,confidence,thesis,timeframe,status,created_at) VALUES('%s','%s','%s','%s','%s','%s','%s','%.10f','%.10f','%.10f','%.4f','%.4f','%.4f','%s','%s','48h','OPEN','%s')",
                    $conn->real_escape_string($batch_id),$conn->real_escape_string($algo['id']),$conn->real_escape_string($algo['name']),$conn->real_escape_string($algo['src']),
                    $conn->real_escape_string($coin['s']),$conn->real_escape_string($coin['p']),$dir,$entry,$tpp,$slp,$tp,$sl,$r['strength'],
                    $conn->real_escape_string($conf),$conn->real_escape_string($r['thesis']),date('Y-m-d H:i:s'));
                if($conn->query($sql)){$r['pred_id']=$conn->insert_id;$pred_count++;}
            }
            $sigs[]=$r;
        }
        $all[$coin['s']]=$sigs;
    }

    // Consensus
    $cons=_compute_consensus($conn,$batch_id);
    $elapsed=round((microtime(true)-$start)*1000,1);
    echo json_encode(array('ok'=>true,'batch_id'=>$batch_id,'coins_scanned'=>count($coins),'predictions_made'=>$pred_count,'consensus'=>$cons,'latency_ms'=>$elapsed,'signals'=>$all));
}

function _compute_consensus($conn,$bid){
    $w=$bid?" AND batch_id='".$conn->real_escape_string($bid)."'":'';
    $res=$conn->query("SELECT symbol,direction,COUNT(*) as cnt,GROUP_CONCAT(algo_name SEPARATOR ', ') as algos,AVG(signal_strength) as avg_str FROM algo_battle_preds WHERE status='OPEN'".$w." GROUP BY symbol,direction HAVING cnt>=2 ORDER BY cnt DESC,avg_str DESC");
    $picks=array();
    if($res){while($r=$res->fetch_assoc()){
        $r['cnt']=intval($r['cnt']);$r['avg_str']=round(floatval($r['avg_str']),4);
        $r['grade']=$r['cnt']>=5?'STRONG':($r['cnt']>=3?'MODERATE':'WEAK');
        $conn->query(sprintf("UPDATE algo_battle_preds SET consensus_count=%d WHERE symbol='%s' AND direction='%s' AND status='OPEN'".$w,$r['cnt'],$conn->real_escape_string($r['symbol']),$conn->real_escape_string($r['direction'])));
        $picks[]=$r;
    }}
    return $picks;
}

function _consensus_analysis($conn){
    $bid=isset($_GET['batch_id'])?$_GET['batch_id']:'';
    $cons=_compute_consensus($conn,$bid);
    $perf=$conn->query("SELECT CASE WHEN consensus_count>=3 THEN 'CONSENSUS_3+' WHEN consensus_count>=2 THEN 'CONSENSUS_2' ELSE 'SINGLE' END as tier,COUNT(*) as total,SUM(CASE WHEN exit_reason='TP_HIT' THEN 1 ELSE 0 END) as wins,SUM(CASE WHEN exit_reason='SL_HIT' THEN 1 ELSE 0 END) as losses,AVG(CASE WHEN status='RESOLVED' THEN pnl_pct ELSE NULL END) as avg_pnl FROM algo_battle_preds WHERE status='RESOLVED' GROUP BY tier");
    $perfData=array();
    if($perf){while($r=$perf->fetch_assoc()){$rv=intval($r['wins'])+intval($r['losses']);$r['win_rate']=$rv>0?round(intval($r['wins'])/$rv*100,1):0;$perfData[]=$r;}}
    echo json_encode(array('ok'=>true,'current_consensus'=>$cons,'consensus_performance'=>$perfData));
}

function _leaderboard($conn){
    $res=$conn->query("SELECT algo_id,algo_name,algo_source,COUNT(*) as total_picks,SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open_picks,SUM(CASE WHEN exit_reason='TP_HIT' THEN 1 ELSE 0 END) as wins,SUM(CASE WHEN exit_reason='SL_HIT' THEN 1 ELSE 0 END) as losses,SUM(CASE WHEN exit_reason='EXPIRED_48H' THEN 1 ELSE 0 END) as expired,AVG(CASE WHEN status='RESOLVED' THEN pnl_pct ELSE NULL END) as avg_pnl,MAX(CASE WHEN status='RESOLVED' THEN pnl_pct ELSE NULL END) as best_trade,MIN(CASE WHEN status='RESOLVED' THEN pnl_pct ELSE NULL END) as worst_trade,AVG(signal_strength) as avg_signal_strength FROM algo_battle_preds GROUP BY algo_id,algo_name,algo_source ORDER BY avg_pnl DESC");
    $lb=array();$rank=1;
    if($res){while($r=$res->fetch_assoc()){$rv=intval($r['wins'])+intval($r['losses']);$r['resolved']=$rv;$r['win_rate']=$rv>0?round(intval($r['wins'])/$rv*100,1):0;$r['rank']=$rank++;$lb[]=$r;}}
    // Add AI Grok for comparison
    $ai=$conn->query("SELECT 'ai_grok' as algo_id,'AI Grok Personal' as algo_name,'AI' as algo_source,COUNT(*) as total_picks,SUM(CASE WHEN status='OPEN' THEN 1 ELSE 0 END) as open_picks,SUM(CASE WHEN exit_reason='TP_HIT' THEN 1 ELSE 0 END) as wins,SUM(CASE WHEN exit_reason='SL_HIT' THEN 1 ELSE 0 END) as losses,SUM(CASE WHEN exit_reason='EXPIRED_48H' THEN 1 ELSE 0 END) as expired,AVG(CASE WHEN status='RESOLVED' THEN pnl_pct ELSE NULL END) as avg_pnl,MAX(CASE WHEN status='RESOLVED' THEN pnl_pct ELSE NULL END) as best_trade,MIN(CASE WHEN status='RESOLVED' THEN pnl_pct ELSE NULL END) as worst_trade,0.5 as avg_signal_strength FROM ai_personal_predictions");
    if($ai){$r=$ai->fetch_assoc();$rv=intval($r['wins'])+intval($r['losses']);$r['resolved']=$rv;$r['win_rate']=$rv>0?round(intval($r['wins'])/$rv*100,1):0;$r['rank']=count($lb)+1;$lb[]=$r;}
    echo json_encode(array('ok'=>true,'leaderboard'=>$lb));
}

function _monitor($conn){
    $start=microtime(true);
    $res=$conn->query("SELECT * FROM algo_battle_preds WHERE status='OPEN'");
    if(!$res||$res->num_rows===0){echo json_encode(array('ok'=>true,'msg'=>'No open predictions'));return;}
    $pm=array();$open=array();
    while($row=$res->fetch_assoc()){$open[]=$row;$pm[$row['kraken_pair']]=true;}
    $url='https://api.kraken.com/0/public/Ticker?pair='.implode(',',array_keys($pm));
    $ch=curl_init($url);curl_setopt($ch,CURLOPT_RETURNTRANSFER,true);curl_setopt($ch,CURLOPT_TIMEOUT,10);curl_setopt($ch,CURLOPT_SSL_VERIFYPEER,false);
    $resp=curl_exec($ch);curl_close($ch);$prices=array();
    if($resp){$data=json_decode($resp,true);if($data&&isset($data['result'])){foreach($data['result'] as $k=>$v)$prices[$k]=floatval($v['c'][0]);}}
    $rc=0;$now=date('Y-m-d H:i:s');
    foreach($open as $pr){
        $kp=$pr['kraken_pair'];$live=isset($prices[$kp])?$prices[$kp]:null;if(!$live)continue;
        $entry=floatval($pr['entry_price']);$tp=floatval($pr['tp_price']);$sl=floatval($pr['sl_price']);$dir=$pr['direction'];
        $pnl=$dir==='LONG'?(($live-$entry)/$entry)*100:(($entry-$live)/$entry)*100;
        $peak=max(floatval($pr['peak_pnl_pct']),$pnl);$trough=min(floatval($pr['trough_pnl_pct']),$pnl);$ck=intval($pr['checks_count'])+1;
        $resolved=false;$er='';
        if($dir==='LONG'){if($live>=$tp){$resolved=true;$er='TP_HIT';}elseif($live<=$sl){$resolved=true;$er='SL_HIT';}}
        else{if($live<=$tp){$resolved=true;$er='TP_HIT';}elseif($live>=$sl){$resolved=true;$er='SL_HIT';}}
        $hrs=(time()-strtotime($pr['created_at']))/3600;if(!$resolved&&$hrs>=48){$resolved=true;$er='EXPIRED_48H';}
        if($resolved){$conn->query(sprintf("UPDATE algo_battle_preds SET status='RESOLVED',current_price='%.10f',pnl_pct='%.4f',peak_pnl_pct='%.4f',trough_pnl_pct='%.4f',exit_price='%.10f',exit_reason='%s',checks_count=%d,last_check='%s',resolved_at='%s' WHERE id=%d",$live,$pnl,$peak,$trough,$live,$conn->real_escape_string($er),$ck,$now,$now,intval($pr['id'])));$rc++;}
        else{$conn->query(sprintf("UPDATE algo_battle_preds SET current_price='%.10f',pnl_pct='%.4f',peak_pnl_pct='%.4f',trough_pnl_pct='%.4f',checks_count=%d,last_check='%s' WHERE id=%d",$live,$pnl,$peak,$trough,$ck,$now,intval($pr['id'])));}
    }
    echo json_encode(array('ok'=>true,'checked'=>count($open),'resolved'=>$rc,'latency_ms'=>round((microtime(true)-$start)*1000,1)));
}

function _status($conn){
    $t=$conn->query("SELECT COUNT(*) as c FROM algo_battle_preds")->fetch_assoc();
    $o=$conn->query("SELECT COUNT(*) as c FROM algo_battle_preds WHERE status='OPEN'")->fetch_assoc();
    $r=$conn->query("SELECT COUNT(*) as c FROM algo_battle_preds WHERE status='RESOLVED'")->fetch_assoc();
    $bs=array();$br=$conn->query("SELECT batch_id,COUNT(*) as picks,MIN(created_at) as started FROM algo_battle_preds GROUP BY batch_id ORDER BY started DESC LIMIT 10");
    if($br)while($row=$br->fetch_assoc())$bs[]=$row;
    echo json_encode(array('ok'=>true,'total'=>intval($t['c']),'open'=>intval($o['c']),'resolved'=>intval($r['c']),'batches'=>$bs));
}
?>