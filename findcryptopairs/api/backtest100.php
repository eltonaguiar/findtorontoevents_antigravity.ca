<?php
/**
 * Backtest Arena v1.0 — 100 Strategy Backtester
 * Tests 100 strategies across volatile Kraken pairs on multiple timeframes.
 * Full audit trail of every decision.
 *
 * STRATEGY CATEGORIES (100 total):
 *   1-20:  Trend Following (EMA crosses, MACD, Ichimoku, Supertrend, etc.)
 *  21-40:  Mean Reversion (RSI, Bollinger, Stoch, CCI, Z-score, etc.)
 *  41-55:  Momentum (ROC, TSI, KST, Awesome Osc, Elder Ray, etc.)
 *  56-70:  Volume-Based (OBV, A/D, Chaikin, Force Index, VWAP, etc.)
 *  71-80:  Volatility-Based (ATR breakout, BB squeeze, Keltner, etc.)
 *  81-90:  Pattern-Based (Inside bar, engulfing, swing failure, etc.)
 *  91-100: Composite/Advanced (multi-indicator confluence systems)
 *
 * Actions:
 *   scan_volatile      — Find top volatile Kraken pairs
 *   backtest_pair      — Run all 100 strategies on 1 pair (3 timeframes)
 *   backtest_batch     — Run batch of pairs (offset/limit)
 *   rank               — Rank all strategies by performance
 *   top_picks          — High-certainty picks where top strategies agree
 *   audit              — Full audit log
 *   status             — Current state
 *
 * PHP 5.2 compatible.
 */
header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }
error_reporting(0);
ini_set('display_errors', '0');
set_time_limit(120);

$API_KEY = 'bt100_2026';
$conn = new mysqli('mysql.50webs.com', 'ejaguiar1_memecoin', 'testing123', 'ejaguiar1_memecoin');
if ($conn->connect_error) { echo json_encode(array('ok' => false, 'error' => 'DB fail')); exit; }
$conn->set_charset('utf8');

// Tables
$conn->query("CREATE TABLE IF NOT EXISTS bt100_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL,
    pair VARCHAR(30) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    strat_id INT NOT NULL,
    strat_name VARCHAR(80) NOT NULL,
    strat_category VARCHAR(30) NOT NULL,
    total_trades INT DEFAULT 0,
    wins INT DEFAULT 0,
    losses INT DEFAULT 0,
    win_rate DECIMAL(8,4) DEFAULT 0,
    total_pnl DECIMAL(12,4) DEFAULT 0,
    avg_pnl DECIMAL(8,4) DEFAULT 0,
    max_win DECIMAL(8,4) DEFAULT 0,
    max_loss DECIMAL(8,4) DEFAULT 0,
    profit_factor DECIMAL(8,4) DEFAULT 0,
    sharpe_ratio DECIMAL(8,4) DEFAULT 0,
    max_drawdown DECIMAL(8,4) DEFAULT 0,
    avg_hold_bars INT DEFAULT 0,
    signal_now VARCHAR(10) DEFAULT 'HOLD',
    signal_strength DECIMAL(8,4) DEFAULT 0,
    signal_thesis TEXT,
    created_at DATETIME NOT NULL,
    INDEX idx_run (run_id),
    INDEX idx_pair (pair),
    INDEX idx_strat (strat_id),
    INDEX idx_winrate (win_rate),
    INDEX idx_pnl (total_pnl)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS bt100_audit (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL,
    phase VARCHAR(30) NOT NULL,
    action VARCHAR(50) NOT NULL,
    detail TEXT NOT NULL,
    data TEXT,
    created_at DATETIME NOT NULL,
    INDEX idx_run (run_id),
    INDEX idx_phase (phase)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS bt100_picks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    run_id VARCHAR(50) NOT NULL,
    pair VARCHAR(30) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    entry_price DECIMAL(20,10) DEFAULT 0,
    tp_price DECIMAL(20,10) DEFAULT 0,
    sl_price DECIMAL(20,10) DEFAULT 0,
    tp_pct DECIMAL(8,4) DEFAULT 0,
    sl_pct DECIMAL(8,4) DEFAULT 0,
    certainty_score DECIMAL(8,4) DEFAULT 0,
    certainty_grade VARCHAR(20) DEFAULT 'LOW',
    strategies_agreeing INT DEFAULT 0,
    strategy_names TEXT,
    avg_backtest_winrate DECIMAL(8,4) DEFAULT 0,
    avg_backtest_pf DECIMAL(8,4) DEFAULT 0,
    thesis TEXT,
    status VARCHAR(20) DEFAULT 'OPEN',
    current_price DECIMAL(20,10) DEFAULT 0,
    pnl_pct DECIMAL(8,4) DEFAULT 0,
    exit_price DECIMAL(20,10) DEFAULT 0,
    exit_reason VARCHAR(30) DEFAULT NULL,
    created_at DATETIME NOT NULL,
    resolved_at DATETIME DEFAULT NULL,
    INDEX idx_run (run_id),
    INDEX idx_status (status),
    INDEX idx_cert (certainty_score)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? $_GET['action'] : 'status';
switch ($action) {
    case 'scan_volatile': _scan_volatile($conn); break;
    case 'backtest_pair': _require_key(); _backtest_pair($conn); break;
    case 'backtest_batch': _require_key(); _backtest_batch($conn); break;
    case 'rank': _rank($conn); break;
    case 'top_picks': _top_picks($conn); break;
    case 'audit': _audit($conn); break;
    case 'status': _status($conn); break;
    case 'monitor': _monitor_picks($conn); break;
    default: echo json_encode(array('ok' => false, 'error' => 'Unknown: ' . $action));
}
$conn->close();

function _require_key() {
    $k = isset($_GET['key']) ? $_GET['key'] : '';
    if ($k !== 'bt100_2026') { echo json_encode(array('ok' => false, 'error' => 'Key')); exit; }
}

function _audit_log($conn, $run_id, $phase, $action, $detail, $data_json) {
    $conn->query(sprintf("INSERT INTO bt100_audit(run_id,phase,action,detail,data,created_at) VALUES('%s','%s','%s','%s','%s','%s')",
        $conn->real_escape_string($run_id), $conn->real_escape_string($phase),
        $conn->real_escape_string($action), $conn->real_escape_string($detail),
        $conn->real_escape_string($data_json ? $data_json : ''), date('Y-m-d H:i:s')));
}

// ══════════════════════════════════════════════════════════════
// DATA FETCHERS
// ══════════════════════════════════════════════════════════════
function _kraken_ohlcv($pair, $interval) {
    $url = 'https://api.kraken.com/0/public/OHLC?pair=' . $pair . '&interval=' . $interval;
    $ch = curl_init($url); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_TIMEOUT, 15);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); curl_setopt($ch, CURLOPT_USERAGENT, 'BT100/1.0');
    $r = curl_exec($ch); curl_close($ch);
    if (!$r) return array();
    $d = json_decode($r, true);
    if (!$d || !isset($d['result'])) return array();
    $out = array();
    foreach ($d['result'] as $k => $v) {
        if ($k === 'last') continue;
        foreach ($v as $c) $out[] = array('t'=>intval($c[0]),'o'=>floatval($c[1]),'h'=>floatval($c[2]),'l'=>floatval($c[3]),'c'=>floatval($c[4]),'vw'=>floatval($c[5]),'v'=>floatval($c[6]),'n'=>intval($c[7]));
    }
    return $out;
}

function _kraken_ticker($pair) {
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . $pair;
    $ch = curl_init($url); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); $r = curl_exec($ch); curl_close($ch);
    if (!$r) return null; $d = json_decode($r, true);
    if (!$d || !isset($d['result'])) return null;
    foreach ($d['result'] as $k => $v) return array('price'=>floatval($v['c'][0]),'h24'=>floatval($v['h'][1]),'l24'=>floatval($v['l'][1]),'vw24'=>floatval($v['p'][1]),'vol24'=>floatval($v['v'][1]),'open24'=>floatval($v['o']));
    return null;
}

function _kraken_all_tickers() {
    $url = 'https://api.kraken.com/0/public/Ticker';
    $ch = curl_init($url); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_TIMEOUT, 20);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false); $r = curl_exec($ch); curl_close($ch);
    if (!$r) return array(); $d = json_decode($r, true);
    return isset($d['result']) ? $d['result'] : array();
}

// ══════════════════════════════════════════════════════════════
// INDICATOR LIBRARY (compact)
// ══════════════════════════════════════════════════════════════
function _ema($d,$p){$e=array();$m=2.0/($p+1);$e[0]=$d[0];for($i=1;$i<count($d);$i++)$e[$i]=($d[$i]-$e[$i-1])*$m+$e[$i-1];return $e;}
function _sma($d,$p){$s=array();for($i=0;$i<count($d);$i++){if($i<$p-1){$s[$i]=null;continue;}$sm=0;for($j=$i-$p+1;$j<=$i;$j++)$sm+=$d[$j];$s[$i]=$sm/$p;}return $s;}
function _rsi($c,$p){$r=array();$ag=0;$al=0;for($i=0;$i<count($c);$i++){if($i===0){$r[]=50;continue;}$ch=$c[$i]-$c[$i-1];$g=$ch>0?$ch:0;$l=$ch<0?abs($ch):0;if($i<$p){$r[]=50;continue;}if($i===$p){$sg=0;$sl=0;for($j=1;$j<=$p;$j++){$d=$c[$j]-$c[$j-1];$sg+=$d>0?$d:0;$sl+=$d<0?abs($d):0;}$ag=$sg/$p;$al=$sl/$p;}else{$ag=($ag*($p-1)+$g)/$p;$al=($al*($p-1)+$l)/$p;}$r[]=$al==0?100:100-(100/(1+$ag/$al));}return $r;}
function _macd($c,$f,$s,$sg){$ef=_ema($c,$f);$es=_ema($c,$s);$ml=array();for($i=0;$i<count($c);$i++)$ml[$i]=$ef[$i]-$es[$i];$sl=_ema($ml,$sg);$h=array();for($i=0;$i<count($c);$i++)$h[$i]=$ml[$i]-$sl[$i];return array($ml,$sl,$h);}
function _bb($c,$p,$m){$s=_sma($c,$p);$u=array();$l=array();for($i=0;$i<count($c);$i++){if($s[$i]===null){$u[$i]=null;$l[$i]=null;continue;}$sl=array_slice($c,max(0,$i-$p+1),$p);$mn=array_sum($sl)/count($sl);$v=0;foreach($sl as $x)$v+=($x-$mn)*($x-$mn);$sd=sqrt($v/count($sl));$u[$i]=$s[$i]+$m*$sd;$l[$i]=$s[$i]-$m*$sd;}return array($s,$u,$l);}
function _atr($h,$l,$c,$p){$tr=array();for($i=0;$i<count($c);$i++){if($i===0){$tr[]=($h[$i]-$l[$i]);continue;}$tr[]=max($h[$i]-$l[$i],abs($h[$i]-$c[$i-1]),abs($l[$i]-$c[$i-1]));}return _ema($tr,$p);}
function _stoch($h,$l,$c,$kp,$dp){$k=array();for($i=0;$i<count($c);$i++){if($i<$kp-1){$k[$i]=50;continue;}$hh=max(array_slice($h,$i-$kp+1,$kp));$ll=min(array_slice($l,$i-$kp+1,$kp));$k[$i]=($hh==$ll)?50:(($c[$i]-$ll)/($hh-$ll))*100;}$d=_sma($k,$dp);for($i=0;$i<count($d);$i++)if($d[$i]===null)$d[$i]=50;return array($k,$d);}
function _srsi($c,$rp,$sp,$ks,$ds){$r=_rsi($c,$rp);$sk=array();for($i=0;$i<count($r);$i++){if($i<$sp-1){$sk[$i]=50;continue;}$sl=array_slice($r,$i-$sp+1,$sp);$mn=min($sl);$mx=max($sl);$sk[$i]=($mx==$mn)?50:(($r[$i]-$mn)/($mx-$mn))*100;}$k=_sma($sk,$ks);$d=_sma($sk,$ds);for($i=0;$i<count($k);$i++){if($k[$i]===null)$k[$i]=50;if($d[$i]===null)$d[$i]=50;}return array($k,$d);}
function _cci($h,$l,$c,$p){$tp=array();for($i=0;$i<count($c);$i++)$tp[$i]=($h[$i]+$l[$i]+$c[$i])/3;$sma=_sma($tp,$p);$cci=array();for($i=0;$i<count($tp);$i++){if($sma[$i]===null){$cci[$i]=0;continue;}$sl=array_slice($tp,max(0,$i-$p+1),$p);$md=0;foreach($sl as $x)$md+=abs($x-$sma[$i]);$md/=count($sl);$cci[$i]=$md==0?0:($tp[$i]-$sma[$i])/(0.015*$md);}return $cci;}
function _obv($c,$v){$o=array();$o[0]=0;for($i=1;$i<count($c);$i++){if($c[$i]>$c[$i-1])$o[$i]=$o[$i-1]+$v[$i];elseif($c[$i]<$c[$i-1])$o[$i]=$o[$i-1]-$v[$i];else $o[$i]=$o[$i-1];}return $o;}
function _ad($h,$l,$c,$v){$a=array();$a[0]=0;for($i=1;$i<count($c);$i++){$mfm=($h[$i]==$l[$i])?0:(((($c[$i]-$l[$i])-($h[$i]-$c[$i]))/($h[$i]-$l[$i]))*$v[$i]);$a[$i]=$a[$i-1]+$mfm;}return $a;}
function _midpt($h,$l,$p){$r=array();for($i=0;$i<count($h);$i++){if($i<$p-1){$r[$i]=($h[$i]+$l[$i])/2;continue;}$r[$i]=(max(array_slice($h,$i-$p+1,$p))+min(array_slice($l,$i-$p+1,$p)))/2;}return $r;}
function _hl_mid($h, $l) {
    $r = array();
    for ($i = 0; $i < count($h); $i++) $r[$i] = ($h[$i] + $l[$i]) / 2;
    return $r;
}
function _cmp_range($a, $b) { return $b['range'] > $a['range'] ? 1 : -1; }
function _cmp_certainty($a, $b) { return $b['certainty'] > $a['certainty'] ? 1 : -1; }
function _wma($d,$p){$w=array();for($i=0;$i<count($d);$i++){if($i<$p-1){$w[$i]=null;continue;}$s=0;$dv=0;for($j=0;$j<$p;$j++){$wt=$p-$j;$s+=$d[$i-$j]*$wt;$dv+=$wt;}$w[$i]=$s/$dv;}return $w;}
function _hma($d,$p){$half=max(1,intval($p/2));$sq=max(1,intval(sqrt($p)));$wh=_wma($d,$half);$wf=_wma($d,$p);$diff=array();for($i=0;$i<count($d);$i++){if($wh[$i]===null||$wf[$i]===null){$diff[$i]=$d[$i];continue;}$diff[$i]=2*$wh[$i]-$wf[$i];}return _wma($diff,$sq);}

// ══════════════════════════════════════════════════════════════
// THE 100 STRATEGIES — each returns array of signals per bar
// Signal: 1=BUY, -1=SELL, 0=HOLD
// ══════════════════════════════════════════════════════════════
function _get_strategies() {
    return array(
        // TREND FOLLOWING (1-20)
        array('id'=>1,'name'=>'EMA 9/21 Cross','cat'=>'TREND'),
        array('id'=>2,'name'=>'EMA 12/26 Cross','cat'=>'TREND'),
        array('id'=>3,'name'=>'EMA 20/50 Cross','cat'=>'TREND'),
        array('id'=>4,'name'=>'EMA 50/200 Cross','cat'=>'TREND'),
        array('id'=>5,'name'=>'Triple EMA 9/21/55','cat'=>'TREND'),
        array('id'=>6,'name'=>'MACD Standard','cat'=>'TREND'),
        array('id'=>7,'name'=>'MACD Histogram Div','cat'=>'TREND'),
        array('id'=>8,'name'=>'Parabolic SAR','cat'=>'TREND'),
        array('id'=>9,'name'=>'Supertrend ATR','cat'=>'TREND'),
        array('id'=>10,'name'=>'Donchian 20 Breakout','cat'=>'TREND'),
        array('id'=>11,'name'=>'Keltner Channel','cat'=>'TREND'),
        array('id'=>12,'name'=>'HMA Cross','cat'=>'TREND'),
        array('id'=>13,'name'=>'DEMA 9/21 Cross','cat'=>'TREND'),
        array('id'=>14,'name'=>'VWAP Trend','cat'=>'TREND'),
        array('id'=>15,'name'=>'Ichimoku TK Cross','cat'=>'TREND'),
        array('id'=>16,'name'=>'Ichimoku Cloud','cat'=>'TREND'),
        array('id'=>17,'name'=>'Aroon Oscillator','cat'=>'TREND'),
        array('id'=>18,'name'=>'ADX DI Cross','cat'=>'TREND'),
        array('id'=>19,'name'=>'Linear Reg Slope','cat'=>'TREND'),
        array('id'=>20,'name'=>'Price vs SMA200','cat'=>'TREND'),
        // MEAN REVERSION (21-40)
        array('id'=>21,'name'=>'RSI 14 Extreme','cat'=>'MEANREV'),
        array('id'=>22,'name'=>'RSI 7 Extreme','cat'=>'MEANREV'),
        array('id'=>23,'name'=>'RSI Divergence','cat'=>'MEANREV'),
        array('id'=>24,'name'=>'BB Bounce','cat'=>'MEANREV'),
        array('id'=>25,'name'=>'BB Squeeze Breakout','cat'=>'MEANREV'),
        array('id'=>26,'name'=>'BB %B Extreme','cat'=>'MEANREV'),
        array('id'=>27,'name'=>'Stochastic 14/3','cat'=>'MEANREV'),
        array('id'=>28,'name'=>'Stochastic RSI','cat'=>'MEANREV'),
        array('id'=>29,'name'=>'Williams %R','cat'=>'MEANREV'),
        array('id'=>30,'name'=>'CCI 20 Extreme','cat'=>'MEANREV'),
        array('id'=>31,'name'=>'CCI 14 Extreme','cat'=>'MEANREV'),
        array('id'=>32,'name'=>'MFI Extreme','cat'=>'MEANREV'),
        array('id'=>33,'name'=>'Price vs SMA20 Dev','cat'=>'MEANREV'),
        array('id'=>34,'name'=>'Price vs SMA50 Dev','cat'=>'MEANREV'),
        array('id'=>35,'name'=>'Z-Score Reversion','cat'=>'MEANREV'),
        array('id'=>36,'name'=>'Keltner Mean Rev','cat'=>'MEANREV'),
        array('id'=>37,'name'=>'Envelope 3% Rev','cat'=>'MEANREV'),
        array('id'=>38,'name'=>'VWAP Mean Rev','cat'=>'MEANREV'),
        array('id'=>39,'name'=>'Pivot Point Bounce','cat'=>'MEANREV'),
        array('id'=>40,'name'=>'Double Deviation','cat'=>'MEANREV'),
        // MOMENTUM (41-55)
        array('id'=>41,'name'=>'ROC 10','cat'=>'MOMENTUM'),
        array('id'=>42,'name'=>'ROC 20','cat'=>'MOMENTUM'),
        array('id'=>43,'name'=>'TSI 25/13','cat'=>'MOMENTUM'),
        array('id'=>44,'name'=>'Ultimate Oscillator','cat'=>'MOMENTUM'),
        array('id'=>45,'name'=>'Awesome Oscillator','cat'=>'MOMENTUM'),
        array('id'=>46,'name'=>'PPO 12/26','cat'=>'MOMENTUM'),
        array('id'=>47,'name'=>'TRIX 15','cat'=>'MOMENTUM'),
        array('id'=>48,'name'=>'Elder Ray','cat'=>'MOMENTUM'),
        array('id'=>49,'name'=>'Chande MO','cat'=>'MOMENTUM'),
        array('id'=>50,'name'=>'RVI','cat'=>'MOMENTUM'),
        array('id'=>51,'name'=>'KST Oscillator','cat'=>'MOMENTUM'),
        array('id'=>52,'name'=>'Coppock Curve','cat'=>'MOMENTUM'),
        array('id'=>53,'name'=>'Momentum 10','cat'=>'MOMENTUM'),
        array('id'=>54,'name'=>'Acceleration','cat'=>'MOMENTUM'),
        array('id'=>55,'name'=>'Mass Index','cat'=>'MOMENTUM'),
        // VOLUME (56-70)
        array('id'=>56,'name'=>'OBV Trend','cat'=>'VOLUME'),
        array('id'=>57,'name'=>'OBV Divergence','cat'=>'VOLUME'),
        array('id'=>58,'name'=>'A/D Line Trend','cat'=>'VOLUME'),
        array('id'=>59,'name'=>'Chaikin MF','cat'=>'VOLUME'),
        array('id'=>60,'name'=>'Chaikin Oscillator','cat'=>'VOLUME'),
        array('id'=>61,'name'=>'Force Index','cat'=>'VOLUME'),
        array('id'=>62,'name'=>'VWAP+Vol Spike','cat'=>'VOLUME'),
        array('id'=>63,'name'=>'Volume Breakout','cat'=>'VOLUME'),
        array('id'=>64,'name'=>'Ease of Movement','cat'=>'VOLUME'),
        array('id'=>65,'name'=>'Volume-Price Trend','cat'=>'VOLUME'),
        array('id'=>66,'name'=>'NVI Strategy','cat'=>'VOLUME'),
        array('id'=>67,'name'=>'MFI Divergence','cat'=>'VOLUME'),
        array('id'=>68,'name'=>'OBV+EMA Cross','cat'=>'VOLUME'),
        array('id'=>69,'name'=>'Vol Weighted MACD','cat'=>'VOLUME'),
        array('id'=>70,'name'=>'Klinger Proxy','cat'=>'VOLUME'),
        // VOLATILITY (71-80)
        array('id'=>71,'name'=>'ATR Breakout','cat'=>'VOLATILITY'),
        array('id'=>72,'name'=>'ATR Trailing Stop','cat'=>'VOLATILITY'),
        array('id'=>73,'name'=>'BB Width Expansion','cat'=>'VOLATILITY'),
        array('id'=>74,'name'=>'Hist Vol Breakout','cat'=>'VOLATILITY'),
        array('id'=>75,'name'=>'Keltner+BB Squeeze','cat'=>'VOLATILITY'),
        array('id'=>76,'name'=>'StdDev Channel','cat'=>'VOLATILITY'),
        array('id'=>77,'name'=>'ATR Channel Break','cat'=>'VOLATILITY'),
        array('id'=>78,'name'=>'Range Expansion','cat'=>'VOLATILITY'),
        array('id'=>79,'name'=>'Chaikin Volatility','cat'=>'VOLATILITY'),
        array('id'=>80,'name'=>'Intraday Intensity','cat'=>'VOLATILITY'),
        // PATTERN (81-90)
        array('id'=>81,'name'=>'Support/Resist Break','cat'=>'PATTERN'),
        array('id'=>82,'name'=>'Inside Bar Break','cat'=>'PATTERN'),
        array('id'=>83,'name'=>'Engulfing Candle','cat'=>'PATTERN'),
        array('id'=>84,'name'=>'Hammer/ShootStar','cat'=>'PATTERN'),
        array('id'=>85,'name'=>'Three Bar Rev','cat'=>'PATTERN'),
        array('id'=>86,'name'=>'Higher High/Low','cat'=>'PATTERN'),
        array('id'=>87,'name'=>'Swing Failure','cat'=>'PATTERN'),
        array('id'=>88,'name'=>'Range Contract Break','cat'=>'PATTERN'),
        array('id'=>89,'name'=>'Gap and Go','cat'=>'PATTERN'),
        array('id'=>90,'name'=>'Fibonacci Retrace','cat'=>'PATTERN'),
        // COMPOSITE (91-100)
        array('id'=>91,'name'=>'RSI+MACD Confluence','cat'=>'COMPOSITE'),
        array('id'=>92,'name'=>'EMA+RSI+Vol Triple','cat'=>'COMPOSITE'),
        array('id'=>93,'name'=>'BB+RSI+MACD Triple','cat'=>'COMPOSITE'),
        array('id'=>94,'name'=>'Ichimoku Full','cat'=>'COMPOSITE'),
        array('id'=>95,'name'=>'ADX+RSI Filter','cat'=>'COMPOSITE'),
        array('id'=>96,'name'=>'MACD+Stoch Confirm','cat'=>'COMPOSITE'),
        array('id'=>97,'name'=>'Supertrend+Vol','cat'=>'COMPOSITE'),
        array('id'=>98,'name'=>'Multi-TF RSI','cat'=>'COMPOSITE'),
        array('id'=>99,'name'=>'5-Indicator Score','cat'=>'COMPOSITE'),
        array('id'=>100,'name'=>'Kitchen Sink 8+','cat'=>'COMPOSITE')
    );
}

function _run_strategy($id, $candles) {
    $n = count($candles);
    if ($n < 60) return array_fill(0, $n, 0);
    $c = array(); $h = array(); $l = array(); $o = array(); $v = array(); $vw = array();
    foreach ($candles as $x) { $c[] = $x['c']; $h[] = $x['h']; $l[] = $x['l']; $o[] = $x['o']; $v[] = $x['v']; $vw[] = $x['vw']; }

    $sigs = array_fill(0, $n, 0);

    switch ($id) {
        // ── TREND 1-20 ──
        case 1: // EMA 9/21
            $e9 = _ema($c,9); $e21 = _ema($c,21);
            for ($i=1;$i<$n;$i++) if ($e9[$i]>$e21[$i] && $e9[$i-1]<=$e21[$i-1]) $sigs[$i]=1; elseif ($e9[$i]<$e21[$i] && $e9[$i-1]>=$e21[$i-1]) $sigs[$i]=-1;
            break;
        case 2: // EMA 12/26
            $ea = _ema($c,12); $eb = _ema($c,26);
            for ($i=1;$i<$n;$i++) if ($ea[$i]>$eb[$i] && $ea[$i-1]<=$eb[$i-1]) $sigs[$i]=1; elseif ($ea[$i]<$eb[$i] && $ea[$i-1]>=$eb[$i-1]) $sigs[$i]=-1;
            break;
        case 3: // EMA 20/50
            $ea = _ema($c,20); $eb = _ema($c,50);
            for ($i=1;$i<$n;$i++) if ($ea[$i]>$eb[$i] && $ea[$i-1]<=$eb[$i-1]) $sigs[$i]=1; elseif ($ea[$i]<$eb[$i] && $ea[$i-1]>=$eb[$i-1]) $sigs[$i]=-1;
            break;
        case 4: // EMA 50/200
            $ea = _ema($c,50); $eb = _ema($c,200);
            for ($i=1;$i<$n;$i++) if ($ea[$i]>$eb[$i] && $ea[$i-1]<=$eb[$i-1]) $sigs[$i]=1; elseif ($ea[$i]<$eb[$i] && $ea[$i-1]>=$eb[$i-1]) $sigs[$i]=-1;
            break;
        case 5: // Triple EMA 9/21/55
            $e9=_ema($c,9);$e21=_ema($c,21);$e55=_ema($c,55);
            for($i=1;$i<$n;$i++){if($e9[$i]>$e21[$i]&&$e21[$i]>$e55[$i]&&!($e9[$i-1]>$e21[$i-1]&&$e21[$i-1]>$e55[$i-1]))$sigs[$i]=1;elseif($e9[$i]<$e21[$i]&&$e21[$i]<$e55[$i]&&!($e9[$i-1]<$e21[$i-1]&&$e21[$i-1]<$e55[$i-1]))$sigs[$i]=-1;}
            break;
        case 6: // MACD Standard
            $m=_macd($c,12,26,9);
            for($i=1;$i<$n;$i++){if($m[0][$i]>$m[1][$i]&&$m[0][$i-1]<=$m[1][$i-1])$sigs[$i]=1;elseif($m[0][$i]<$m[1][$i]&&$m[0][$i-1]>=$m[1][$i-1])$sigs[$i]=-1;}
            break;
        case 7: // MACD Histogram Divergence
            $m=_macd($c,12,26,9);
            for($i=2;$i<$n;$i++){if($m[2][$i]>0&&$m[2][$i]>$m[2][$i-1]&&$m[2][$i-1]<=$m[2][$i-2])$sigs[$i]=1;elseif($m[2][$i]<0&&$m[2][$i]<$m[2][$i-1]&&$m[2][$i-1]>=$m[2][$i-2])$sigs[$i]=-1;}
            break;
        case 8: // Parabolic SAR
            $af=0.02;$mx_af=0.2;$sar=$l[0];$ep=$h[0];$bull=true;$caf=$af;
            for($i=1;$i<$n;$i++){$psar=$sar;$sar=$sar+$caf*($ep-$sar);if($bull){if($l[$i]<$sar){$bull=false;$sar=$ep;$ep=$l[$i];$caf=$af;$sigs[$i]=-1;}else{if($h[$i]>$ep){$ep=$h[$i];$caf=min($caf+$af,$mx_af);}}}else{if($h[$i]>$sar){$bull=true;$sar=$ep;$ep=$h[$i];$caf=$af;$sigs[$i]=1;}else{if($l[$i]<$ep){$ep=$l[$i];$caf=min($caf+$af,$mx_af);}}}}
            break;
        case 9: // Supertrend ATR
            $atr=_atr($h,$l,$c,10);$mul=3;
            $st_up=array();$st_dn=array();$trend=array();
            for($i=0;$i<$n;$i++){$ub=(($h[$i]+$l[$i])/2)+$mul*$atr[$i];$lb=(($h[$i]+$l[$i])/2)-$mul*$atr[$i];if($i===0){$st_up[$i]=$ub;$st_dn[$i]=$lb;$trend[$i]=1;continue;}$st_up[$i]=$lb>$st_up[$i-1]||$c[$i-1]>$st_up[$i-1]?$lb:$st_up[$i-1];$st_dn[$i]=$ub<$st_dn[$i-1]||$c[$i-1]<$st_dn[$i-1]?$ub:$st_dn[$i-1];if($c[$i]>$st_dn[$i])$trend[$i]=1;elseif($c[$i]<$st_up[$i])$trend[$i]=-1;else $trend[$i]=$trend[$i-1];if($i>0&&$trend[$i]!=$trend[$i-1])$sigs[$i]=$trend[$i];}
            break;
        case 10: // Donchian 20
            for($i=20;$i<$n;$i++){$hh=max(array_slice($h,$i-20,20));$ll=min(array_slice($l,$i-20,20));if($c[$i]>$hh&&$c[$i-1]<=$hh)$sigs[$i]=1;elseif($c[$i]<$ll&&$c[$i-1]>=$ll)$sigs[$i]=-1;}
            break;
        case 11: // Keltner Channel
            $e20=_ema($c,20);$atr=_atr($h,$l,$c,10);
            for($i=1;$i<$n;$i++){$ku=$e20[$i]+2*$atr[$i];$kl=$e20[$i]-2*$atr[$i];if($c[$i]>$ku&&$c[$i-1]<=$e20[$i-1]+2*$atr[$i-1])$sigs[$i]=1;elseif($c[$i]<$kl&&$c[$i-1]>=$e20[$i-1]-2*$atr[$i-1])$sigs[$i]=-1;}
            break;
        case 12: // HMA Cross
            $hma9=_hma($c,9);$hma21=_hma($c,21);
            for($i=1;$i<$n;$i++){if($hma9[$i]!==null&&$hma21[$i]!==null&&$hma9[$i-1]!==null&&$hma21[$i-1]!==null){if($hma9[$i]>$hma21[$i]&&$hma9[$i-1]<=$hma21[$i-1])$sigs[$i]=1;elseif($hma9[$i]<$hma21[$i]&&$hma9[$i-1]>=$hma21[$i-1])$sigs[$i]=-1;}}
            break;
        case 13: // DEMA Cross
            $e9a=_ema($c,9);$e9b=_ema($e9a,9);$e21a=_ema($c,21);$e21b=_ema($e21a,21);$d9=array();$d21=array();
            for($i=0;$i<$n;$i++){$d9[$i]=2*$e9a[$i]-$e9b[$i];$d21[$i]=2*$e21a[$i]-$e21b[$i];}
            for($i=1;$i<$n;$i++){if($d9[$i]>$d21[$i]&&$d9[$i-1]<=$d21[$i-1])$sigs[$i]=1;elseif($d9[$i]<$d21[$i]&&$d9[$i-1]>=$d21[$i-1])$sigs[$i]=-1;}
            break;
        case 14: // VWAP Trend
            for($i=1;$i<$n;$i++){if($c[$i]>$vw[$i]*1.02&&$c[$i-1]<=$vw[$i-1]*1.02)$sigs[$i]=1;elseif($c[$i]<$vw[$i]*0.98&&$c[$i-1]>=$vw[$i-1]*0.98)$sigs[$i]=-1;}
            break;
        case 15: // Ichimoku TK Cross
            $tk=_midpt($h,$l,9);$kj=_midpt($h,$l,26);
            for($i=1;$i<$n;$i++){if($tk[$i]>$kj[$i]&&$tk[$i-1]<=$kj[$i-1])$sigs[$i]=1;elseif($tk[$i]<$kj[$i]&&$tk[$i-1]>=$kj[$i-1])$sigs[$i]=-1;}
            break;
        case 16: // Ichimoku Cloud
            $tk=_midpt($h,$l,9);$kj=_midpt($h,$l,26);$sb=_midpt($h,$l,52);
            for($i=27;$i<$n;$i++){$ci=$i-26;$sa=($tk[$ci]+$kj[$ci])/2;$sbb=$sb[$ci];$ct=max($sa,$sbb);$cb=min($sa,$sbb);if($c[$i]>$ct&&$c[$i-1]<=$ct)$sigs[$i]=1;elseif($c[$i]<$cb&&$c[$i-1]>=$cb)$sigs[$i]=-1;}
            break;
        case 17: // Aroon
            for($i=25;$i<$n;$i++){$hh_idx=0;$ll_idx=0;$hh_val=$h[$i-25];$ll_val=$l[$i-25];for($j=$i-25;$j<=$i;$j++){if($h[$j]>=$hh_val){$hh_val=$h[$j];$hh_idx=$j;}if($l[$j]<=$ll_val){$ll_val=$l[$j];$ll_idx=$j;}}$au=(($i-($i-$hh_idx))/25)*100;$ad2=(($i-($i-$ll_idx))/25)*100;$ao=$au-$ad2;if($ao>50&&$c[$i]>$c[$i-1])$sigs[$i]=1;elseif($ao<-50&&$c[$i]<$c[$i-1])$sigs[$i]=-1;}
            break;
        case 18: // ADX+DI
            $atr=_atr($h,$l,$c,14);$pdm=array();$ndm=array();
            for($i=0;$i<$n;$i++){if($i===0){$pdm[]=0;$ndm[]=0;continue;}$up=$h[$i]-$h[$i-1];$dn=$l[$i-1]-$l[$i];$pdm[]=$up>$dn&&$up>0?$up:0;$ndm[]=$dn>$up&&$dn>0?$dn:0;}
            $spdm=_ema($pdm,14);$sndm=_ema($ndm,14);$pdi=array();$ndi=array();
            for($i=0;$i<$n;$i++){$pdi[$i]=$atr[$i]>0?($spdm[$i]/$atr[$i])*100:0;$ndi[$i]=$atr[$i]>0?($sndm[$i]/$atr[$i])*100:0;}
            for($i=1;$i<$n;$i++){if($pdi[$i]>$ndi[$i]&&$pdi[$i-1]<=$ndi[$i-1]&&$pdi[$i]>20)$sigs[$i]=1;elseif($ndi[$i]>$pdi[$i]&&$ndi[$i-1]<=$pdi[$i-1]&&$ndi[$i]>20)$sigs[$i]=-1;}
            break;
        case 19: // Linear Regression Slope
            for($i=20;$i<$n;$i++){$x_sum=0;$y_sum=0;$xy_sum=0;$xx_sum=0;for($j=0;$j<20;$j++){$x_sum+=$j;$y_sum+=$c[$i-19+$j];$xy_sum+=$j*$c[$i-19+$j];$xx_sum+=$j*$j;}$slope=(20*$xy_sum-$x_sum*$y_sum)/(20*$xx_sum-$x_sum*$x_sum);$norm=$slope/$c[$i]*100;if($norm>0.5&&$c[$i]>$c[$i-1])$sigs[$i]=1;elseif($norm<-0.5&&$c[$i]<$c[$i-1])$sigs[$i]=-1;}
            break;
        case 20: // Price vs SMA200
            $s200=_sma($c,200);
            for($i=1;$i<$n;$i++){if($s200[$i]!==null){if($c[$i]>$s200[$i]&&$c[$i-1]<=$s200[$i-1])$sigs[$i]=1;elseif($c[$i]<$s200[$i]&&($s200[$i-1]===null||$c[$i-1]>=$s200[$i-1]))$sigs[$i]=-1;}}
            break;
        // ── MEAN REVERSION 21-40 ──
        case 21: $r=_rsi($c,14);for($i=1;$i<$n;$i++){if($r[$i]<30&&$r[$i-1]>=30)$sigs[$i]=1;elseif($r[$i]>70&&$r[$i-1]<=70)$sigs[$i]=-1;} break;
        case 22: $r=_rsi($c,7);for($i=1;$i<$n;$i++){if($r[$i]<25&&$r[$i-1]>=25)$sigs[$i]=1;elseif($r[$i]>75&&$r[$i-1]<=75)$sigs[$i]=-1;} break;
        case 23: // RSI Divergence
            $r=_rsi($c,14);
            for($i=20;$i<$n;$i++){$plo=min(array_slice($c,$i-10,10));$rlo=min(array_slice($r,$i-10,10));if($c[$i]<=$plo*1.01&&$r[$i]>$rlo+5)$sigs[$i]=1;$phi=max(array_slice($c,$i-10,10));$rhi=max(array_slice($r,$i-10,10));if($c[$i]>=$phi*0.99&&$r[$i]<$rhi-5)$sigs[$i]=-1;}
            break;
        case 24: // BB Bounce
            $bb=_bb($c,20,2);
            for($i=1;$i<$n;$i++){if($bb[1][$i]!==null){if($c[$i-1]<=$bb[2][$i-1]&&$c[$i]>$bb[2][$i])$sigs[$i]=1;elseif($c[$i-1]>=$bb[1][$i-1]&&$c[$i]<$bb[1][$i])$sigs[$i]=-1;}}
            break;
        case 25: // BB Squeeze Breakout
            $bb=_bb($c,20,2);
            for($i=2;$i<$n;$i++){if($bb[1][$i]===null)continue;$bw1=($bb[1][$i-1]-$bb[2][$i-1])/$bb[0][$i-1];$bw0=($bb[1][$i]-$bb[2][$i])/$bb[0][$i];if($bw1<0.04&&$bw0>$bw1&&$c[$i]>$bb[1][$i])$sigs[$i]=1;elseif($bw1<0.04&&$bw0>$bw1&&$c[$i]<$bb[2][$i])$sigs[$i]=-1;}
            break;
        case 26: // BB %B Extreme
            $bb=_bb($c,20,2);
            for($i=1;$i<$n;$i++){if($bb[1][$i]===null)continue;$pb=($c[$i]-$bb[2][$i])/max($bb[1][$i]-$bb[2][$i],0.0001);if($pb<0.05)$sigs[$i]=1;elseif($pb>0.95)$sigs[$i]=-1;}
            break;
        case 27: // Stochastic 14/3
            $st=_stoch($h,$l,$c,14,3);for($i=1;$i<$n;$i++){if($st[0][$i]<20&&$st[0][$i]>$st[1][$i]&&$st[0][$i-1]<=$st[1][$i-1])$sigs[$i]=1;elseif($st[0][$i]>80&&$st[0][$i]<$st[1][$i]&&$st[0][$i-1]>=$st[1][$i-1])$sigs[$i]=-1;}
            break;
        case 28: // StochRSI
            $sr=_srsi($c,14,14,3,3);for($i=1;$i<$n;$i++){if($sr[0][$i]<20&&$sr[0][$i]>$sr[1][$i]&&$sr[0][$i-1]<=$sr[1][$i-1])$sigs[$i]=1;elseif($sr[0][$i]>80&&$sr[0][$i]<$sr[1][$i]&&$sr[0][$i-1]>=$sr[1][$i-1])$sigs[$i]=-1;}
            break;
        case 29: // Williams %R
            for($i=14;$i<$n;$i++){$hh=max(array_slice($h,$i-14,14));$ll=min(array_slice($l,$i-14,14));$wr=($hh-$c[$i])/max($hh-$ll,0.0001)*-100;if($wr<-80&&$c[$i]>$c[$i-1])$sigs[$i]=1;elseif($wr>-20&&$c[$i]<$c[$i-1])$sigs[$i]=-1;}
            break;
        case 30: $cc=_cci($h,$l,$c,20);for($i=1;$i<$n;$i++){if($cc[$i]<-100&&$cc[$i-1]>=-100)$sigs[$i]=1;elseif($cc[$i]>100&&$cc[$i-1]<=100)$sigs[$i]=-1;} break;
        case 31: $cc=_cci($h,$l,$c,14);for($i=1;$i<$n;$i++){if($cc[$i]<-150)$sigs[$i]=1;elseif($cc[$i]>150)$sigs[$i]=-1;} break;
        case 32: // MFI
            $tp=array();$mfp=array();$mfn=array();for($i=0;$i<$n;$i++){$tp[$i]=($h[$i]+$l[$i]+$c[$i])/3;$rmf=$tp[$i]*$v[$i];if($i>0&&$tp[$i]>$tp[$i-1])$mfp[$i]=$rmf;else $mfp[$i]=0;if($i>0&&$tp[$i]<$tp[$i-1])$mfn[$i]=$rmf;else $mfn[$i]=0;}
            for($i=14;$i<$n;$i++){$pmf=array_sum(array_slice($mfp,$i-14,14));$nmf=array_sum(array_slice($mfn,$i-14,14));$mfi=$nmf==0?100:100-(100/(1+$pmf/$nmf));if($mfi<20)$sigs[$i]=1;elseif($mfi>80)$sigs[$i]=-1;}
            break;
        case 33: // Price vs SMA20 deviation
            $s20=_sma($c,20);for($i=0;$i<$n;$i++){if($s20[$i]===null)continue;$dev=($c[$i]-$s20[$i])/$s20[$i]*100;if($dev<-5)$sigs[$i]=1;elseif($dev>5)$sigs[$i]=-1;}
            break;
        case 34: $s50=_sma($c,50);for($i=0;$i<$n;$i++){if($s50[$i]===null)continue;$dev=($c[$i]-$s50[$i])/$s50[$i]*100;if($dev<-8)$sigs[$i]=1;elseif($dev>8)$sigs[$i]=-1;} break;
        case 35: // Z-Score
            for($i=20;$i<$n;$i++){$sl=array_slice($c,$i-20,20);$mn=array_sum($sl)/20;$sd=0;foreach($sl as $x)$sd+=($x-$mn)*($x-$mn);$sd=sqrt($sd/20);if($sd==0)continue;$z=($c[$i]-$mn)/$sd;if($z<-2)$sigs[$i]=1;elseif($z>2)$sigs[$i]=-1;}
            break;
        case 36: // Keltner Mean Reversion
            $e20=_ema($c,20);$atr=_atr($h,$l,$c,10);for($i=1;$i<$n;$i++){$kl=$e20[$i]-2.5*$atr[$i];$ku=$e20[$i]+2.5*$atr[$i];if($c[$i]<$kl&&$c[$i-1]>=$kl)$sigs[$i]=1;elseif($c[$i]>$ku&&$c[$i-1]<=$ku)$sigs[$i]=-1;}
            break;
        case 37: // Envelope 3%
            $s20=_sma($c,20);for($i=1;$i<$n;$i++){if($s20[$i]===null)continue;if($c[$i]<$s20[$i]*0.97&&$c[$i-1]>=$s20[$i-1]*0.97)$sigs[$i]=1;elseif($c[$i]>$s20[$i]*1.03&&$c[$i-1]<=$s20[$i-1]*1.03)$sigs[$i]=-1;}
            break;
        case 38: // VWAP Mean Reversion
            for($i=1;$i<$n;$i++){if($vw[$i]<=0)continue;$dev=($c[$i]-$vw[$i])/$vw[$i]*100;if($dev<-3&&$c[$i]>$c[$i-1])$sigs[$i]=1;elseif($dev>3&&$c[$i]<$c[$i-1])$sigs[$i]=-1;}
            break;
        case 39: // Pivot Bounce
            for($i=2;$i<$n;$i++){$pp=($h[$i-1]+$l[$i-1]+$c[$i-1])/3;$s1=2*$pp-$h[$i-1];$r1=2*$pp-$l[$i-1];if($l[$i]<=$s1&&$c[$i]>$s1)$sigs[$i]=1;elseif($h[$i]>=$r1&&$c[$i]<$r1)$sigs[$i]=-1;}
            break;
        case 40: // Double Deviation
            $s20=_sma($c,20);$bb=_bb($c,20,2);for($i=20;$i<$n;$i++){if($bb[1][$i]===null)continue;$pb=($c[$i]-$bb[2][$i])/max($bb[1][$i]-$bb[2][$i],0.0001);$dev=($c[$i]-$s20[$i])/$s20[$i]*100;if($pb<0.1&&$dev<-4)$sigs[$i]=1;elseif($pb>0.9&&$dev>4)$sigs[$i]=-1;}
            break;
        // ── MOMENTUM 41-55 ──
        case 41: for($i=10;$i<$n;$i++){$roc=($c[$i]-$c[$i-10])/$c[$i-10]*100;if($roc>5&&$c[$i]>$c[$i-1])$sigs[$i]=1;elseif($roc<-5&&$c[$i]<$c[$i-1])$sigs[$i]=-1;} break;
        case 42: for($i=20;$i<$n;$i++){$roc=($c[$i]-$c[$i-20])/$c[$i-20]*100;if($roc>8&&$c[$i]>$c[$i-1])$sigs[$i]=1;elseif($roc<-8&&$c[$i]<$c[$i-1])$sigs[$i]=-1;} break;
        case 43: // TSI
            $pc=array();for($i=1;$i<$n;$i++)$pc[$i]=$c[$i]-$c[$i-1];$pc[0]=0;
            $e25=_ema($pc,25);$e13=_ema($e25,13);$apc=array();for($i=0;$i<$n;$i++)$apc[$i]=abs($pc[$i]);$ae25=_ema($apc,25);$ae13=_ema($ae25,13);
            $tsi=array();for($i=0;$i<$n;$i++)$tsi[$i]=$ae13[$i]==0?0:($e13[$i]/$ae13[$i])*100;$ts=_ema($tsi,7);
            for($i=1;$i<$n;$i++){if($tsi[$i]>$ts[$i]&&$tsi[$i-1]<=$ts[$i-1])$sigs[$i]=1;elseif($tsi[$i]<$ts[$i]&&$tsi[$i-1]>=$ts[$i-1])$sigs[$i]=-1;}
            break;
        case 44: // Ultimate Oscillator
            for($i=28;$i<$n;$i++){$bp7=0;$tr7=0;$bp14=0;$tr14=0;$bp28=0;$tr28=0;
            for($j=$i-27;$j<=$i;$j++){$mn=min($l[$j],$c[max(0,$j-1)]);$mx=max($h[$j],$c[max(0,$j-1)]);$bp=$c[$j]-$mn;$tr=$mx-$mn;if($j>$i-7){$bp7+=$bp;$tr7+=$tr;}if($j>$i-14){$bp14+=$bp;$tr14+=$tr;}$bp28+=$bp;$tr28+=$tr;}
            $uo=$tr7==0||$tr14==0||$tr28==0?50:((4*$bp7/$tr7+2*$bp14/$tr14+$bp28/$tr28)/7)*100;if($uo<30)$sigs[$i]=1;elseif($uo>70)$sigs[$i]=-1;}
            break;
        case 45: // Awesome Oscillator
            $hlm = _hl_mid($h, $l);
            $s5=_sma($hlm,5);
            $s34=_sma($hlm,34);
            for($i=1;$i<$n;$i++){if($s5[$i]!==null&&$s34[$i]!==null){$ao=$s5[$i]-$s34[$i];$aop=$s5[$i-1]!==null&&$s34[$i-1]!==null?$s5[$i-1]-$s34[$i-1]:0;if($ao>0&&$aop<=0)$sigs[$i]=1;elseif($ao<0&&$aop>=0)$sigs[$i]=-1;}}
            break;
        case 46: // PPO
            $e12=_ema($c,12);$e26=_ema($c,26);$ppo=array();for($i=0;$i<$n;$i++)$ppo[$i]=$e26[$i]==0?0:(($e12[$i]-$e26[$i])/$e26[$i])*100;$ps=_ema($ppo,9);
            for($i=1;$i<$n;$i++){if($ppo[$i]>$ps[$i]&&$ppo[$i-1]<=$ps[$i-1])$sigs[$i]=1;elseif($ppo[$i]<$ps[$i]&&$ppo[$i-1]>=$ps[$i-1])$sigs[$i]=-1;}
            break;
        case 47: // TRIX
            $e1=_ema($c,15);$e2=_ema($e1,15);$e3=_ema($e2,15);$tx=array();for($i=1;$i<$n;$i++)$tx[$i]=$e3[$i-1]==0?0:(($e3[$i]-$e3[$i-1])/$e3[$i-1])*100;$tx[0]=0;$ts=_ema($tx,9);
            for($i=1;$i<$n;$i++){if($tx[$i]>$ts[$i]&&$tx[$i-1]<=$ts[$i-1])$sigs[$i]=1;elseif($tx[$i]<$ts[$i]&&$tx[$i-1]>=$ts[$i-1])$sigs[$i]=-1;}
            break;
        case 48: // Elder Ray
            $e13=_ema($c,13);for($i=1;$i<$n;$i++){$bp=$h[$i]-$e13[$i];$brp=$l[$i]-$e13[$i];if($brp<0&&$brp>$l[$i-1]-$e13[$i-1]&&$e13[$i]>$e13[$i-1])$sigs[$i]=1;elseif($bp>0&&$bp<$h[$i-1]-$e13[$i-1]&&$e13[$i]<$e13[$i-1])$sigs[$i]=-1;}
            break;
        case 49: // Chande MO
            for($i=10;$i<$n;$i++){$su=0;$sd=0;for($j=$i-9;$j<=$i;$j++){$ch=$c[$j]-$c[$j-1];if($ch>0)$su+=$ch;else $sd+=abs($ch);}$cmo=($su+$sd)==0?0:(($su-$sd)/($su+$sd))*100;if($cmo<-50)$sigs[$i]=1;elseif($cmo>50)$sigs[$i]=-1;}
            break;
        case 50: // RVI
            for($i=10;$i<$n;$i++){$nu=0;$de=0;for($j=$i-9;$j<=$i;$j++){$nu+=($c[$j]-$o[$j]);$de+=($h[$j]-$l[$j]);}$rvi=$de==0?0:$nu/$de;if($rvi>0.3)$sigs[$i]=1;elseif($rvi<-0.3)$sigs[$i]=-1;}
            break;
        case 51: // KST
            $r1=array();$r2=array();$r3=array();$r4=array();
            for($i=0;$i<$n;$i++){$r1[$i]=$i>=10?($c[$i]-$c[$i-10])/$c[$i-10]*100:0;$r2[$i]=$i>=15?($c[$i]-$c[$i-15])/$c[$i-15]*100:0;$r3[$i]=$i>=20?($c[$i]-$c[$i-20])/$c[$i-20]*100:0;$r4[$i]=$i>=30?($c[$i]-$c[$i-30])/$c[$i-30]*100:0;}
            $k=array();for($i=0;$i<$n;$i++)$k[$i]=$r1[$i]+$r2[$i]*2+$r3[$i]*3+$r4[$i]*4;$ks=_sma($k,9);
            for($i=1;$i<$n;$i++){if($ks[$i]!==null&&$ks[$i-1]!==null){if($k[$i]>$ks[$i]&&$k[$i-1]<=$ks[$i-1])$sigs[$i]=1;elseif($k[$i]<$ks[$i]&&$k[$i-1]>=$ks[$i-1])$sigs[$i]=-1;}}
            break;
        case 52: // Coppock
            $r14=array();$r11=array();for($i=0;$i<$n;$i++){$r14[$i]=$i>=14?($c[$i]-$c[$i-14])/$c[$i-14]*100:0;$r11[$i]=$i>=11?($c[$i]-$c[$i-11])/$c[$i-11]*100:0;}
            $sum=array();for($i=0;$i<$n;$i++)$sum[$i]=$r14[$i]+$r11[$i];$cop=_wma($sum,10);
            for($i=1;$i<$n;$i++){if($cop[$i]!==null&&$cop[$i-1]!==null){if($cop[$i]>0&&$cop[$i-1]<=0)$sigs[$i]=1;elseif($cop[$i]<0&&$cop[$i-1]>=0)$sigs[$i]=-1;}}
            break;
        case 53: for($i=10;$i<$n;$i++){$m=$c[$i]-$c[$i-10];if($m>0&&$c[$i-10]-$c[max(0,$i-20)]<=0)$sigs[$i]=1;elseif($m<0&&$c[$i-10]-$c[max(0,$i-20)]>=0)$sigs[$i]=-1;} break;
        case 54: // Acceleration
            $s5=_sma($c,5);$s34=_sma(_hl_mid($h,$l),34);
            for($i=2;$i<$n;$i++){if($s5[$i]!==null&&$s34[$i]!==null&&$s5[$i-1]!==null&&$s34[$i-1]!==null&&$s5[$i-2]!==null&&$s34[$i-2]!==null){$ao=$s5[$i]-$s34[$i];$aop=$s5[$i-1]-$s34[$i-1];$aopp=$s5[$i-2]-$s34[$i-2];$ac=$ao-$aop;$acp=$aop-$aopp;if($ac>0&&$acp<=0)$sigs[$i]=1;elseif($ac<0&&$acp>=0)$sigs[$i]=-1;}}
            break;
        case 55: // Mass Index
            $hl=array();for($i=0;$i<$n;$i++)$hl[$i]=$h[$i]-$l[$i];$e9=_ema($hl,9);$e99=_ema($e9,9);
            for($i=25;$i<$n;$i++){$mi=0;for($j=$i-24;$j<=$i;$j++){if($e99[$j]!=0)$mi+=$e9[$j]/$e99[$j];}if($mi>27&&$c[$i]<$c[$i-1])$sigs[$i]=-1;elseif($mi<26.5&&$mi>25&&$c[$i]>$c[$i-1])$sigs[$i]=1;}
            break;
        // ── VOLUME 56-70 ──
        case 56: $ob=_obv($c,$v);$oe=_ema($ob,20);for($i=1;$i<$n;$i++){if($ob[$i]>$oe[$i]&&$ob[$i-1]<=$oe[$i-1])$sigs[$i]=1;elseif($ob[$i]<$oe[$i]&&$ob[$i-1]>=$oe[$i-1])$sigs[$i]=-1;} break;
        case 57: // OBV Divergence
            $ob=_obv($c,$v);for($i=20;$i<$n;$i++){$plo=min(array_slice($c,$i-10,10));$olo=min(array_slice($ob,$i-10,10));if($c[$i]<=$plo*1.01&&$ob[$i]>$olo*1.05)$sigs[$i]=1;$phi=max(array_slice($c,$i-10,10));$ohi=max(array_slice($ob,$i-10,10));if($c[$i]>=$phi*0.99&&$ob[$i]<$ohi*0.95)$sigs[$i]=-1;}
            break;
        case 58: $ad=_ad($h,$l,$c,$v);$ae=_ema($ad,20);for($i=1;$i<$n;$i++){if($ad[$i]>$ae[$i]&&$ad[$i-1]<=$ae[$i-1])$sigs[$i]=1;elseif($ad[$i]<$ae[$i]&&$ad[$i-1]>=$ae[$i-1])$sigs[$i]=-1;} break;
        case 59: // Chaikin MF
            for($i=20;$i<$n;$i++){$mfv=0;$vsum=0;for($j=$i-19;$j<=$i;$j++){$mfm=$h[$j]==$l[$j]?0:((($c[$j]-$l[$j])-($h[$j]-$c[$j]))/($h[$j]-$l[$j]));$mfv+=$mfm*$v[$j];$vsum+=$v[$j];}$cmf=$vsum==0?0:$mfv/$vsum;if($cmf>0.15)$sigs[$i]=1;elseif($cmf<-0.15)$sigs[$i]=-1;}
            break;
        case 60: // Chaikin Oscillator
            $ad=_ad($h,$l,$c,$v);$e3=_ema($ad,3);$e10=_ema($ad,10);for($i=1;$i<$n;$i++){if($e3[$i]>$e10[$i]&&$e3[$i-1]<=$e10[$i-1])$sigs[$i]=1;elseif($e3[$i]<$e10[$i]&&$e3[$i-1]>=$e10[$i-1])$sigs[$i]=-1;}
            break;
        case 61: // Force Index
            $fi=array();for($i=1;$i<$n;$i++)$fi[$i]=($c[$i]-$c[$i-1])*$v[$i];$fi[0]=0;$fe=_ema($fi,13);
            for($i=1;$i<$n;$i++){if($fe[$i]>0&&$fe[$i-1]<=0)$sigs[$i]=1;elseif($fe[$i]<0&&$fe[$i-1]>=0)$sigs[$i]=-1;}
            break;
        case 62: // VWAP + Vol Spike
            for($i=1;$i<$n;$i++){$av=0;for($j=max(0,$i-20);$j<$i;$j++)$av+=$v[$j];$av/=min($i,20);$vs=$v[$i]/max($av,0.01);if($vs>2&&$c[$i]>$vw[$i]*1.01)$sigs[$i]=1;elseif($vs>2&&$c[$i]<$vw[$i]*0.99)$sigs[$i]=-1;}
            break;
        case 63: // Volume Breakout
            for($i=20;$i<$n;$i++){$av=array_sum(array_slice($v,$i-20,20))/20;$hh=max(array_slice($h,$i-20,20));$ll=min(array_slice($l,$i-20,20));if($v[$i]>$av*2.5&&$c[$i]>$hh)$sigs[$i]=1;elseif($v[$i]>$av*2.5&&$c[$i]<$ll)$sigs[$i]=-1;}
            break;
        case 64: // Ease of Movement
            $em=array();for($i=1;$i<$n;$i++){$dm=(($h[$i]+$l[$i])/2)-(($h[$i-1]+$l[$i-1])/2);$br=$v[$i]/max($h[$i]-$l[$i],0.0001)/10000;$em[$i]=$br==0?0:$dm/$br;}$em[0]=0;$eme=_sma($em,14);
            for($i=1;$i<$n;$i++){if($eme[$i]!==null&&$eme[$i-1]!==null){if($eme[$i]>0&&$eme[$i-1]<=0)$sigs[$i]=1;elseif($eme[$i]<0&&$eme[$i-1]>=0)$sigs[$i]=-1;}}
            break;
        case 65: // Volume-Price Trend
            $vpt=array();$vpt[0]=0;for($i=1;$i<$n;$i++)$vpt[$i]=$vpt[$i-1]+$v[$i]*(($c[$i]-$c[$i-1])/$c[$i-1]);$ve=_ema($vpt,20);
            for($i=1;$i<$n;$i++){if($vpt[$i]>$ve[$i]&&$vpt[$i-1]<=$ve[$i-1])$sigs[$i]=1;elseif($vpt[$i]<$ve[$i]&&$vpt[$i-1]>=$ve[$i-1])$sigs[$i]=-1;}
            break;
        case 66: // NVI
            $nvi=array();$nvi[0]=1000;for($i=1;$i<$n;$i++){if($v[$i]<$v[$i-1])$nvi[$i]=$nvi[$i-1]*(1+($c[$i]-$c[$i-1])/$c[$i-1]);else $nvi[$i]=$nvi[$i-1];}$ne=_ema($nvi,255>$n?$n:255);
            for($i=1;$i<$n;$i++){if($nvi[$i]>$ne[$i]&&$nvi[$i-1]<=$ne[$i-1])$sigs[$i]=1;elseif($nvi[$i]<$ne[$i]&&$nvi[$i-1]>=$ne[$i-1])$sigs[$i]=-1;}
            break;
        case 67: // MFI Divergence
            $tp=array();$mfp=array();$mfn=array();for($i=0;$i<$n;$i++){$tp[$i]=($h[$i]+$l[$i]+$c[$i])/3;$rmf=$tp[$i]*$v[$i];$mfp[$i]=$i>0&&$tp[$i]>$tp[$i-1]?$rmf:0;$mfn[$i]=$i>0&&$tp[$i]<$tp[$i-1]?$rmf:0;}
            $mfi=array();for($i=14;$i<$n;$i++){$pm=array_sum(array_slice($mfp,$i-14,14));$nm=array_sum(array_slice($mfn,$i-14,14));$mfi[$i]=$nm==0?100:100-(100/(1+$pm/$nm));}
            for($i=20;$i<$n;$i++){if(!isset($mfi[$i]))continue;$plo=min(array_slice($c,$i-10,10));if($c[$i]<=$plo*1.01&&isset($mfi[$i-5])&&$mfi[$i]>$mfi[$i-5]+10)$sigs[$i]=1;}
            break;
        case 68: $ob=_obv($c,$v);$oe9=_ema($ob,9);$oe21=_ema($ob,21);for($i=1;$i<$n;$i++){if($oe9[$i]>$oe21[$i]&&$oe9[$i-1]<=$oe21[$i-1])$sigs[$i]=1;elseif($oe9[$i]<$oe21[$i]&&$oe9[$i-1]>=$oe21[$i-1])$sigs[$i]=-1;} break;
        case 69: // Vol Weighted MACD
            $vc=array();for($i=0;$i<$n;$i++)$vc[$i]=$c[$i]*sqrt(max($v[$i],1));$m=_macd($vc,12,26,9);
            for($i=1;$i<$n;$i++){if($m[0][$i]>$m[1][$i]&&$m[0][$i-1]<=$m[1][$i-1])$sigs[$i]=1;elseif($m[0][$i]<$m[1][$i]&&$m[0][$i-1]>=$m[1][$i-1])$sigs[$i]=-1;}
            break;
        case 70: // Klinger Proxy
            $kvo=array();for($i=1;$i<$n;$i++){$tr=($c[$i]>$c[$i-1])?1:-1;$dm=$h[$i]-$l[$i];$kvo[$i]=$v[$i]*$tr*$dm;}$kvo[0]=0;$ke34=_ema($kvo,34);$ke55=_ema($kvo,55);$kd=array();for($i=0;$i<$n;$i++)$kd[$i]=$ke34[$i]-$ke55[$i];$ks=_ema($kd,13);
            for($i=1;$i<$n;$i++){if($kd[$i]>$ks[$i]&&$kd[$i-1]<=$ks[$i-1])$sigs[$i]=1;elseif($kd[$i]<$ks[$i]&&$kd[$i-1]>=$ks[$i-1])$sigs[$i]=-1;}
            break;
        // ── VOLATILITY 71-80 ──
        case 71: $atr=_atr($h,$l,$c,14);for($i=1;$i<$n;$i++){if($c[$i]>$c[$i-1]+2*$atr[$i-1]&&$v[$i]>$v[$i-1]*1.5)$sigs[$i]=1;elseif($c[$i]<$c[$i-1]-2*$atr[$i-1]&&$v[$i]>$v[$i-1]*1.5)$sigs[$i]=-1;} break;
        case 72: // ATR Trailing
            $atr=_atr($h,$l,$c,14);$ts_val=$c[0]-3*$atr[0];$dir=1;
            for($i=1;$i<$n;$i++){if($dir===1){$nts=max($ts_val,$c[$i]-3*$atr[$i]);if($c[$i]<$nts){$dir=-1;$ts_val=$c[$i]+3*$atr[$i];$sigs[$i]=-1;}else $ts_val=$nts;}else{$nts=min($ts_val,$c[$i]+3*$atr[$i]);if($c[$i]>$nts){$dir=1;$ts_val=$c[$i]-3*$atr[$i];$sigs[$i]=1;}else $ts_val=$nts;}}
            break;
        case 73: // BB Width Expansion
            $bb=_bb($c,20,2);for($i=2;$i<$n;$i++){if($bb[1][$i]===null)continue;$bw=($bb[1][$i]-$bb[2][$i])/$bb[0][$i];$bwp=($bb[1][$i-1]-$bb[2][$i-1])/$bb[0][$i-1];if($bw>$bwp*1.5&&$c[$i]>$bb[0][$i])$sigs[$i]=1;elseif($bw>$bwp*1.5&&$c[$i]<$bb[0][$i])$sigs[$i]=-1;}
            break;
        case 74: // Historical Vol Breakout
            for($i=20;$i<$n;$i++){$rets=array();for($j=$i-19;$j<=$i;$j++)$rets[]=($c[$j]-$c[$j-1])/$c[$j-1];$mn=array_sum($rets)/count($rets);$var=0;foreach($rets as $r)$var+=($r-$mn)*($r-$mn);$hv=sqrt($var/count($rets));if($hv>0.05&&$c[$i]>$c[$i-1])$sigs[$i]=1;elseif($hv>0.05&&$c[$i]<$c[$i-1])$sigs[$i]=-1;}
            break;
        case 75: // Keltner+BB Squeeze
            $bb=_bb($c,20,2);$e20=_ema($c,20);$atr=_atr($h,$l,$c,10);
            for($i=1;$i<$n;$i++){if($bb[1][$i]===null)continue;$ku=$e20[$i]+1.5*$atr[$i];$kl=$e20[$i]-1.5*$atr[$i];$sq=$bb[2][$i]>$kl&&$bb[1][$i]<$ku;$sqp=($i>1&&$bb[2][$i-1]!==null)?($bb[2][$i-1]>($e20[$i-1]-1.5*$atr[$i-1])&&$bb[1][$i-1]<($e20[$i-1]+1.5*$atr[$i-1])):false;if($sqp&&!$sq&&$c[$i]>$e20[$i])$sigs[$i]=1;elseif($sqp&&!$sq&&$c[$i]<$e20[$i])$sigs[$i]=-1;}
            break;
        case 76: // StdDev Channel
            for($i=20;$i<$n;$i++){$sl=array_slice($c,$i-20,20);$mn=array_sum($sl)/20;$sd=0;foreach($sl as $x)$sd+=($x-$mn)*($x-$mn);$sd=sqrt($sd/20);if($c[$i]>$mn+2.5*$sd)$sigs[$i]=-1;elseif($c[$i]<$mn-2.5*$sd)$sigs[$i]=1;}
            break;
        case 77: // ATR Channel Break
            $atr=_atr($h,$l,$c,14);$e20=_ema($c,20);for($i=1;$i<$n;$i++){if($c[$i]>$e20[$i]+2.5*$atr[$i])$sigs[$i]=1;elseif($c[$i]<$e20[$i]-2.5*$atr[$i])$sigs[$i]=-1;}
            break;
        case 78: // Range Expansion
            for($i=5;$i<$n;$i++){$rng=$h[$i]-$l[$i];$avg_rng=0;for($j=$i-5;$j<$i;$j++)$avg_rng+=($h[$j]-$l[$j]);$avg_rng/=5;if($rng>$avg_rng*2&&$c[$i]>$o[$i])$sigs[$i]=1;elseif($rng>$avg_rng*2&&$c[$i]<$o[$i])$sigs[$i]=-1;}
            break;
        case 79: // Chaikin Volatility
            $hl=array();for($i=0;$i<$n;$i++)$hl[$i]=$h[$i]-$l[$i];$he=_ema($hl,10);
            for($i=10;$i<$n;$i++){$cv=($he[$i]-$he[$i-10])/$he[$i-10]*100;if($cv>30&&$c[$i]>$c[$i-1])$sigs[$i]=1;elseif($cv>30&&$c[$i]<$c[$i-1])$sigs[$i]=-1;}
            break;
        case 80: // Intraday Intensity
            $ii=array();for($i=0;$i<$n;$i++){$rng=$h[$i]-$l[$i];$ii[$i]=$rng==0?0:((2*$c[$i]-$h[$i]-$l[$i])/$rng)*$v[$i];}$iis=_sma($ii,21);
            for($i=1;$i<$n;$i++){if($iis[$i]!==null&&$iis[$i-1]!==null){if($iis[$i]>0&&$iis[$i-1]<=0)$sigs[$i]=1;elseif($iis[$i]<0&&$iis[$i-1]>=0)$sigs[$i]=-1;}}
            break;
        // ── PATTERN 81-90 ──
        case 81: // Support/Resistance Break
            for($i=20;$i<$n;$i++){$hh=max(array_slice($h,$i-20,20));$ll=min(array_slice($l,$i-20,20));if($c[$i]>$hh&&$c[$i-1]<$hh)$sigs[$i]=1;elseif($c[$i]<$ll&&$c[$i-1]>$ll)$sigs[$i]=-1;}
            break;
        case 82: // Inside Bar
            for($i=2;$i<$n;$i++){if($h[$i-1]<$h[$i-2]&&$l[$i-1]>$l[$i-2]){if($c[$i]>$h[$i-1])$sigs[$i]=1;elseif($c[$i]<$l[$i-1])$sigs[$i]=-1;}}
            break;
        case 83: // Engulfing
            for($i=1;$i<$n;$i++){if($c[$i-1]<$o[$i-1]&&$c[$i]>$o[$i]&&$c[$i]>$o[$i-1]&&$o[$i]<$c[$i-1])$sigs[$i]=1;elseif($c[$i-1]>$o[$i-1]&&$c[$i]<$o[$i]&&$c[$i]<$o[$i-1]&&$o[$i]>$c[$i-1])$sigs[$i]=-1;}
            break;
        case 84: // Hammer/Shooting Star
            for($i=1;$i<$n;$i++){$body=abs($c[$i]-$o[$i]);$rng=$h[$i]-$l[$i];if($rng==0)continue;$lr=min($c[$i],$o[$i])-$l[$i];$ur=$h[$i]-max($c[$i],$o[$i]);if($lr>$body*2&&$ur<$body*0.5&&$c[$i-1]<$o[$i-1])$sigs[$i]=1;elseif($ur>$body*2&&$lr<$body*0.5&&$c[$i-1]>$o[$i-1])$sigs[$i]=-1;}
            break;
        case 85: // Three Bar Reversal
            for($i=3;$i<$n;$i++){if($c[$i-2]<$o[$i-2]&&$c[$i-1]<$o[$i-1]&&$c[$i]>$o[$i]&&$c[$i]>$h[$i-1])$sigs[$i]=1;elseif($c[$i-2]>$o[$i-2]&&$c[$i-1]>$o[$i-1]&&$c[$i]<$o[$i]&&$c[$i]<$l[$i-1])$sigs[$i]=-1;}
            break;
        case 86: // Higher High/Lower Low
            for($i=4;$i<$n;$i++){if($h[$i]>$h[$i-1]&&$h[$i-1]>$h[$i-2]&&$l[$i]>$l[$i-1]&&$l[$i-1]>$l[$i-2])$sigs[$i]=1;elseif($l[$i]<$l[$i-1]&&$l[$i-1]<$l[$i-2]&&$h[$i]<$h[$i-1]&&$h[$i-1]<$h[$i-2])$sigs[$i]=-1;}
            break;
        case 87: // Swing Failure
            for($i=10;$i<$n;$i++){$hh=max(array_slice($h,$i-10,10));if($h[$i-1]>=$hh&&$c[$i]<$c[$i-1]&&$c[$i]<$o[$i])$sigs[$i]=-1;$ll=min(array_slice($l,$i-10,10));if($l[$i-1]<=$ll&&$c[$i]>$c[$i-1]&&$c[$i]>$o[$i])$sigs[$i]=1;}
            break;
        case 88: // Range Contraction Breakout
            for($i=10;$i<$n;$i++){$rngs=array();for($j=$i-5;$j<$i;$j++)$rngs[]=$h[$j]-$l[$j];$avg=array_sum($rngs)/5;$curr=$h[$i]-$l[$i];if($curr>$avg*2){if($c[$i]>$o[$i])$sigs[$i]=1;else $sigs[$i]=-1;}}
            break;
        case 89: // Gap and Go
            for($i=1;$i<$n;$i++){$gap=($o[$i]-$c[$i-1])/$c[$i-1]*100;if($gap>2&&$c[$i]>$o[$i])$sigs[$i]=1;elseif($gap<-2&&$c[$i]<$o[$i])$sigs[$i]=-1;}
            break;
        case 90: // Fibonacci Retrace
            for($i=50;$i<$n;$i++){$hh=max(array_slice($h,$i-50,50));$ll=min(array_slice($l,$i-50,50));$fib618=$hh-0.618*($hh-$ll);$fib382=$hh-0.382*($hh-$ll);if($c[$i]<=$fib618*1.01&&$c[$i]>=$fib618*0.99&&$c[$i]>$c[$i-1])$sigs[$i]=1;elseif($c[$i]>=$fib382*0.99&&$c[$i]<=$fib382*1.01&&$c[$i]<$c[$i-1])$sigs[$i]=-1;}
            break;
        // ── COMPOSITE 91-100 ──
        case 91: // RSI+MACD
            $r=_rsi($c,14);$m=_macd($c,12,26,9);
            for($i=1;$i<$n;$i++){if($r[$i]<35&&$m[2][$i]>0&&$m[2][$i-1]<=0)$sigs[$i]=1;elseif($r[$i]>65&&$m[2][$i]<0&&$m[2][$i-1]>=0)$sigs[$i]=-1;}
            break;
        case 92: // EMA+RSI+Vol
            $e20=_ema($c,20);$r=_rsi($c,14);
            for($i=20;$i<$n;$i++){$av=array_sum(array_slice($v,$i-20,20))/20;if($c[$i]>$e20[$i]&&$r[$i]>50&&$r[$i]<70&&$v[$i]>$av*1.3)$sigs[$i]=1;elseif($c[$i]<$e20[$i]&&$r[$i]<50&&$r[$i]>30&&$v[$i]>$av*1.3)$sigs[$i]=-1;}
            break;
        case 93: // BB+RSI+MACD
            $bb=_bb($c,20,2);$r=_rsi($c,14);$m=_macd($c,12,26,9);
            for($i=1;$i<$n;$i++){if($bb[2][$i]!==null){$pb=($c[$i]-$bb[2][$i])/max($bb[1][$i]-$bb[2][$i],0.0001);if($pb<0.2&&$r[$i]<35&&$m[2][$i]>$m[2][$i-1])$sigs[$i]=1;elseif($pb>0.8&&$r[$i]>65&&$m[2][$i]<$m[2][$i-1])$sigs[$i]=-1;}}
            break;
        case 94: // Ichimoku Full
            $tk=_midpt($h,$l,9);$kj=_midpt($h,$l,26);$sb=_midpt($h,$l,52);
            for($i=52;$i<$n;$i++){$ci=$i-26;$sa=($tk[$ci]+$kj[$ci])/2;$sbb=$sb[$ci];$ct=max($sa,$sbb);$cb=min($sa,$sbb);if($c[$i]>$ct&&$tk[$i]>$kj[$i]&&$tk[$i-1]<=$kj[$i-1])$sigs[$i]=1;elseif($c[$i]<$cb&&$tk[$i]<$kj[$i]&&$tk[$i-1]>=$kj[$i-1])$sigs[$i]=-1;}
            break;
        case 95: // ADX+RSI
            $r=_rsi($c,14);$atr=_atr($h,$l,$c,14);$pdm=array();$ndm=array();
            for($i=0;$i<$n;$i++){if($i===0){$pdm[]=0;$ndm[]=0;continue;}$up=$h[$i]-$h[$i-1];$dn=$l[$i-1]-$l[$i];$pdm[]=$up>$dn&&$up>0?$up:0;$ndm[]=$dn>$up&&$dn>0?$dn:0;}
            $sp=_ema($pdm,14);$sn=_ema($ndm,14);
            for($i=0;$i<$n;$i++){$pdi=$atr[$i]>0?($sp[$i]/$atr[$i])*100:0;$ndi=$atr[$i]>0?($sn[$i]/$atr[$i])*100:0;$dx=($pdi+$ndi)==0?0:abs($pdi-$ndi)/($pdi+$ndi)*100;if($dx>25&&$r[$i]<35&&$pdi>$ndi)$sigs[$i]=1;elseif($dx>25&&$r[$i]>65&&$ndi>$pdi)$sigs[$i]=-1;}
            break;
        case 96: // MACD+Stoch
            $m=_macd($c,12,26,9);$st=_stoch($h,$l,$c,14,3);
            for($i=1;$i<$n;$i++){if($m[0][$i]>$m[1][$i]&&$m[0][$i-1]<=$m[1][$i-1]&&$st[0][$i]<40)$sigs[$i]=1;elseif($m[0][$i]<$m[1][$i]&&$m[0][$i-1]>=$m[1][$i-1]&&$st[0][$i]>60)$sigs[$i]=-1;}
            break;
        case 97: // Supertrend+Volume
            $atr=_atr($h,$l,$c,10);$mul=3;$st_up=array();$st_dn=array();$trend=array();
            for($i=0;$i<$n;$i++){$ub=(($h[$i]+$l[$i])/2)+$mul*$atr[$i];$lb=(($h[$i]+$l[$i])/2)-$mul*$atr[$i];if($i===0){$st_up[$i]=$ub;$st_dn[$i]=$lb;$trend[$i]=1;continue;}$st_up[$i]=$lb>$st_up[$i-1]||$c[$i-1]>$st_up[$i-1]?$lb:$st_up[$i-1];$st_dn[$i]=$ub<$st_dn[$i-1]||$c[$i-1]<$st_dn[$i-1]?$ub:$st_dn[$i-1];if($c[$i]>$st_dn[$i])$trend[$i]=1;elseif($c[$i]<$st_up[$i])$trend[$i]=-1;else $trend[$i]=$trend[$i-1];}
            for($i=1;$i<$n;$i++){$av=0;for($j=max(0,$i-20);$j<$i;$j++)$av+=$v[$j];$av/=min($i,20);if($trend[$i]!=$trend[$i-1]&&$v[$i]>$av*1.5)$sigs[$i]=$trend[$i];}
            break;
        case 98: // Multi-TF RSI (simulated: RSI14 + RSI7 + RSI21 alignment)
            $r7=_rsi($c,7);$r14=_rsi($c,14);$r21=_rsi($c,21);
            for($i=1;$i<$n;$i++){if($r7[$i]<35&&$r14[$i]<40&&$r21[$i]<45)$sigs[$i]=1;elseif($r7[$i]>65&&$r14[$i]>60&&$r21[$i]>55)$sigs[$i]=-1;}
            break;
        case 99: // 5-Indicator Score
            $e20=_ema($c,20);$r=_rsi($c,14);$m=_macd($c,12,26,9);$bb=_bb($c,20,2);$ob=_obv($c,$v);$oe=_ema($ob,20);
            for($i=1;$i<$n;$i++){if($bb[1][$i]===null)continue;$bull=0;$bear=0;if($c[$i]>$e20[$i])$bull++;else $bear++;if($r[$i]>50)$bull++;else $bear++;if($m[2][$i]>0)$bull++;else $bear++;$pb=($c[$i]-$bb[2][$i])/max($bb[1][$i]-$bb[2][$i],0.0001);if($pb>0.5)$bull++;else $bear++;if($ob[$i]>$oe[$i])$bull++;else $bear++;if($bull>=4)$sigs[$i]=1;elseif($bear>=4)$sigs[$i]=-1;}
            break;
        case 100: // Kitchen Sink 8+
            $e9=_ema($c,9);$e21=_ema($c,21);$r=_rsi($c,14);$m=_macd($c,12,26,9);$bb=_bb($c,20,2);$st=_stoch($h,$l,$c,14,3);$ob=_obv($c,$v);$oe=_ema($ob,20);$atr=_atr($h,$l,$c,14);
            for($i=20;$i<$n;$i++){if($bb[1][$i]===null)continue;$bu=0;$be=0;if($e9[$i]>$e21[$i])$bu++;else $be++;if($c[$i]>$e21[$i])$bu++;else $be++;if($r[$i]>50&&$r[$i]<70)$bu++;elseif($r[$i]<50&&$r[$i]>30)$be++;if($m[2][$i]>0)$bu++;else $be++;if($st[0][$i]>$st[1][$i]&&$st[0][$i]<80)$bu++;elseif($st[0][$i]<$st[1][$i]&&$st[0][$i]>20)$be++;if($ob[$i]>$oe[$i])$bu++;else $be++;$av=array_sum(array_slice($v,$i-20,20))/20;if($v[$i]>$av)$bu++;else $be++;if($c[$i]>$c[$i-1])$bu++;else $be++;if($bu>=6)$sigs[$i]=1;elseif($be>=6)$sigs[$i]=-1;}
            break;
    }
    return $sigs;
}

// ══════════════════════════════════════════════════════════════
// BACKTESTER
// ══════════════════════════════════════════════════════════════
function _backtest($signals, $candles, $tp_pct, $sl_pct) {
    $n = count($candles);
    $trades = array();
    $in_trade = false;
    $entry = 0; $dir = 0; $entry_bar = 0;

    for ($i = 0; $i < $n; $i++) {
        if (!$in_trade && $signals[$i] != 0) {
            $in_trade = true;
            $dir = $signals[$i];
            $entry = $candles[$i]['c'];
            $entry_bar = $i;
        } elseif ($in_trade) {
            $px = $candles[$i]['c'];
            $pnl = $dir === 1 ? (($px - $entry) / $entry) * 100 : (($entry - $px) / $entry) * 100;
            $hit_tp = $pnl >= $tp_pct;
            $hit_sl = $pnl <= -$sl_pct;
            $expired = ($i - $entry_bar) >= 20;
            if ($hit_tp || $hit_sl || $expired || $signals[$i] == -$dir) {
                $trades[] = array('pnl' => $hit_tp ? $tp_pct : ($hit_sl ? -$sl_pct : $pnl), 'bars' => $i - $entry_bar, 'dir' => $dir);
                $in_trade = false;
            }
        }
    }
    if (count($trades) === 0) return array('trades' => 0, 'wins' => 0, 'losses' => 0, 'win_rate' => 0, 'total_pnl' => 0, 'avg_pnl' => 0, 'max_win' => 0, 'max_loss' => 0, 'pf' => 0, 'sharpe' => 0, 'mdd' => 0, 'avg_bars' => 0);

    $wins = 0; $losses = 0; $gross_profit = 0; $gross_loss = 0; $pnls = array(); $equity = 0; $peak = 0; $mdd = 0; $total_bars = 0;
    foreach ($trades as $t) {
        $pnls[] = $t['pnl'];
        $total_bars += $t['bars'];
        if ($t['pnl'] > 0) { $wins++; $gross_profit += $t['pnl']; }
        else { $losses++; $gross_loss += abs($t['pnl']); }
        $equity += $t['pnl'];
        if ($equity > $peak) $peak = $equity;
        $dd = $peak - $equity;
        if ($dd > $mdd) $mdd = $dd;
    }
    $tc = count($trades);
    $avg = array_sum($pnls) / $tc;
    $sd = 0; foreach ($pnls as $p) $sd += ($p - $avg) * ($p - $avg); $sd = sqrt($sd / $tc);
    $sharpe = $sd > 0 ? $avg / $sd : 0;
    $max_w = max($pnls); $max_l = min($pnls);
    $pf = $gross_loss > 0 ? $gross_profit / $gross_loss : ($gross_profit > 0 ? 99 : 0);

    return array('trades' => $tc, 'wins' => $wins, 'losses' => $losses, 'win_rate' => round($tc > 0 ? $wins / $tc * 100 : 0, 2),
        'total_pnl' => round($equity, 2), 'avg_pnl' => round($avg, 4), 'max_win' => round($max_w, 2), 'max_loss' => round($max_l, 2),
        'pf' => round($pf, 2), 'sharpe' => round($sharpe, 4), 'mdd' => round($mdd, 2), 'avg_bars' => round($total_bars / $tc, 1));
}

// ══════════════════════════════════════════════════════════════
// ACTIONS
// ══════════════════════════════════════════════════════════════
function _scan_volatile($conn) {
    $tickers = _kraken_all_tickers();
    $volatile = array();
    $skip = array('USDC','USDT','DAI','PAX','BUSD','TUSD','PYUSD','FDUSD','USDE','ZGBP','ZEUR','ZCAD','ZJPY','ZAUD');
    foreach ($tickers as $pair => $d) {
        if (!preg_match('/USD$/', $pair)) continue;
        $skip_it = false;
        foreach ($skip as $s) { if (strpos($pair, $s) === 0) { $skip_it = true; break; } }
        if ($skip_it) continue;
        $h24 = floatval($d['h'][1]); $l24 = floatval($d['l'][1]); $px = floatval($d['c'][0]); $vol = floatval($d['v'][1]); $op = floatval($d['o']);
        if ($l24 <= 0 || $px <= 0) continue;
        $range = (($h24 - $l24) / $l24) * 100;
        $chg = (($px - $op) / $op) * 100;
        $vol_usd = $vol * $px;
        if ($vol_usd < 50000) continue;
        $volatile[] = array('pair' => $pair, 'price' => $px, 'range' => round($range, 2), 'chg' => round($chg, 2), 'vol_usd' => round($vol_usd));
    }
    usort($volatile, '_cmp_range');
    echo json_encode(array('ok' => true, 'count' => count($volatile), 'top30' => array_slice($volatile, 0, 30)));
}

function _backtest_pair($conn) {
    $pair = isset($_GET['pair']) ? $_GET['pair'] : '';
    if (!$pair) { echo json_encode(array('ok' => false, 'error' => 'No pair')); return; }
    $run_id = isset($_GET['run_id']) ? $_GET['run_id'] : 'run_' . date('Y-m-d_H-i');
    $start = microtime(true);

    $timeframes = array(array('tf'=>'1h','int'=>60), array('tf'=>'4h','int'=>240), array('tf'=>'1d','int'=>1440));
    $strategies = _get_strategies();
    $all_results = array();
    $tp = 6; $sl = 3; // Default TP/SL for backtesting

    _audit_log($conn, $run_id, 'BACKTEST', 'START', 'Backtesting ' . $pair . ' across 3 timeframes with 100 strategies', '');

    foreach ($timeframes as $tfi => $tfinfo) {
        if ($tfi > 0) usleep(500000);
        $candles = _kraken_ohlcv($pair, $tfinfo['int']);
        if (count($candles) < 60) {
            _audit_log($conn, $run_id, 'BACKTEST', 'SKIP_TF', $pair . ' ' . $tfinfo['tf'] . ': insufficient data (' . count($candles) . ' candles)', '');
            continue;
        }
        _audit_log($conn, $run_id, 'BACKTEST', 'DATA', $pair . ' ' . $tfinfo['tf'] . ': ' . count($candles) . ' candles loaded', '');

        foreach ($strategies as $strat) {
            $signals = _run_strategy($strat['id'], $candles);
            $result = _backtest($signals, $candles, $tp, $sl);

            // Current signal (last bar)
            $last_sig = 'HOLD'; $last_str = 0;
            for ($k = count($signals) - 1; $k >= max(0, count($signals) - 5); $k--) {
                if ($signals[$k] != 0) { $last_sig = $signals[$k] === 1 ? 'BUY' : 'SELL'; $last_str = abs($signals[$k]); break; }
            }

            $thesis = $strat['name'] . ' on ' . $pair . ' ' . $tfinfo['tf'] . ': ' . $result['trades'] . ' trades, ' . $result['win_rate'] . '% WR, PF=' . $result['pf'] . ', Sharpe=' . $result['sharpe'];

            $sql = sprintf("INSERT INTO bt100_results(run_id,pair,timeframe,strat_id,strat_name,strat_category,total_trades,wins,losses,win_rate,total_pnl,avg_pnl,max_win,max_loss,profit_factor,sharpe_ratio,max_drawdown,avg_hold_bars,signal_now,signal_strength,signal_thesis,created_at) VALUES('%s','%s','%s',%d,'%s','%s',%d,%d,%d,'%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f',%d,'%s','%.4f','%s','%s')",
                $conn->real_escape_string($run_id), $conn->real_escape_string($pair), $conn->real_escape_string($tfinfo['tf']),
                $strat['id'], $conn->real_escape_string($strat['name']), $conn->real_escape_string($strat['cat']),
                $result['trades'], $result['wins'], $result['losses'], $result['win_rate'],
                $result['total_pnl'], $result['avg_pnl'], $result['max_win'], $result['max_loss'],
                $result['pf'], $result['sharpe'], $result['mdd'], $result['avg_bars'],
                $conn->real_escape_string($last_sig), $last_str,
                $conn->real_escape_string($thesis), date('Y-m-d H:i:s'));
            $conn->query($sql);

            $all_results[] = array('strat' => $strat['name'], 'tf' => $tfinfo['tf'], 'trades' => $result['trades'], 'wr' => $result['win_rate'], 'pnl' => $result['total_pnl'], 'pf' => $result['pf'], 'sig' => $last_sig);
        }
    }

    $elapsed = round((microtime(true) - $start) * 1000, 1);
    _audit_log($conn, $run_id, 'BACKTEST', 'COMPLETE', $pair . ' done. ' . count($all_results) . ' strategy-timeframe combos tested in ' . $elapsed . 'ms', '');
    echo json_encode(array('ok' => true, 'pair' => $pair, 'run_id' => $run_id, 'results_count' => count($all_results), 'latency_ms' => $elapsed));
}

function _backtest_batch($conn) {
    $offset = isset($_GET['offset']) ? intval($_GET['offset']) : 0;
    $limit = isset($_GET['limit']) ? intval($_GET['limit']) : 3;
    $run_id = isset($_GET['run_id']) ? $_GET['run_id'] : 'run_' . date('Y-m-d_H-i');

    // Get volatile pairs
    $tickers = _kraken_all_tickers();
    $volatile = array();
    $skip = array('USDC','USDT','DAI','PAX','BUSD','TUSD','PYUSD','FDUSD','USDE','ZGBP','ZEUR','ZCAD','ZJPY','ZAUD');
    foreach ($tickers as $pair => $d) {
        if (!preg_match('/USD$/', $pair)) continue;
        $skip_it = false; foreach ($skip as $s) { if (strpos($pair, $s) === 0) { $skip_it = true; break; } } if ($skip_it) continue;
        $h24 = floatval($d['h'][1]); $l24 = floatval($d['l'][1]); $px = floatval($d['c'][0]); $vol = floatval($d['v'][1]);
        if ($l24 <= 0 || $px <= 0) continue;
        $range = (($h24 - $l24) / $l24) * 100; $vol_usd = $vol * $px;
        if ($vol_usd < 50000) continue;
        $volatile[] = array('pair' => $pair, 'range' => $range, 'vol_usd' => $vol_usd);
    }
    usort($volatile, '_cmp_range');

    $batch = array_slice($volatile, $offset, $limit);
    $results = array();
    foreach ($batch as $bi => $coin) {
        if ($bi > 0) sleep(2);
        // Inline backtest for this pair
        $pair = $coin['pair'];
        $timeframes = array(array('tf'=>'4h','int'=>240), array('tf'=>'1d','int'=>1440));
        $strategies = _get_strategies();
        $pair_results = 0;

        _audit_log($conn, $run_id, 'BATCH', 'PAIR_START', 'Processing ' . $pair . ' (offset=' . ($offset + $bi) . ', range=' . round($coin['range'], 1) . '%, vol=$' . number_format($coin['vol_usd']) . ')', '');

        foreach ($timeframes as $tfi => $tfinfo) {
            if ($tfi > 0) usleep(600000);
            $candles = _kraken_ohlcv($pair, $tfinfo['int']);
            if (count($candles) < 60) continue;

            foreach ($strategies as $strat) {
                $signals = _run_strategy($strat['id'], $candles);
                $result = _backtest($signals, $candles, 6, 3);
                $last_sig = 'HOLD';
                for ($k = count($signals) - 1; $k >= max(0, count($signals) - 5); $k--) { if ($signals[$k] != 0) { $last_sig = $signals[$k] === 1 ? 'BUY' : 'SELL'; break; } }
                $thesis = $strat['name'] . ' on ' . $pair . ' ' . $tfinfo['tf'] . ': ' . $result['trades'] . 'T, ' . $result['win_rate'] . '%WR, PF=' . $result['pf'];

                $conn->query(sprintf("INSERT INTO bt100_results(run_id,pair,timeframe,strat_id,strat_name,strat_category,total_trades,wins,losses,win_rate,total_pnl,avg_pnl,max_win,max_loss,profit_factor,sharpe_ratio,max_drawdown,avg_hold_bars,signal_now,signal_strength,signal_thesis,created_at) VALUES('%s','%s','%s',%d,'%s','%s',%d,%d,%d,'%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f','%.4f',%d,'%s',1,'%s','%s')",
                    $conn->real_escape_string($run_id), $conn->real_escape_string($pair), $conn->real_escape_string($tfinfo['tf']),
                    $strat['id'], $conn->real_escape_string($strat['name']), $conn->real_escape_string($strat['cat']),
                    $result['trades'], $result['wins'], $result['losses'], $result['win_rate'],
                    $result['total_pnl'], $result['avg_pnl'], $result['max_win'], $result['max_loss'],
                    $result['pf'], $result['sharpe'], $result['mdd'], $result['avg_bars'],
                    $conn->real_escape_string($last_sig), $conn->real_escape_string($thesis), date('Y-m-d H:i:s')));
                $pair_results++;
            }
        }
        $results[] = array('pair' => $pair, 'tests' => $pair_results);
    }

    _audit_log($conn, $run_id, 'BATCH', 'COMPLETE', 'Batch offset=' . $offset . ' limit=' . $limit . '. Processed ' . count($results) . ' pairs.', json_encode($results));
    echo json_encode(array('ok' => true, 'run_id' => $run_id, 'offset' => $offset, 'processed' => $results, 'total_volatile' => count($volatile), 'next_offset' => $offset + $limit));
}

function _rank($conn) {
    $run_id = isset($_GET['run_id']) ? $_GET['run_id'] : '';
    $where = $run_id ? " WHERE run_id='" . $conn->real_escape_string($run_id) . "'" : '';
    $min_trades = isset($_GET['min_trades']) ? intval($_GET['min_trades']) : 5;

    // Rank strategies across all pairs/timeframes
    $res = $conn->query("SELECT strat_id, strat_name, strat_category,
        COUNT(*) as pair_tf_combos,
        SUM(total_trades) as total_trades,
        AVG(win_rate) as avg_win_rate,
        AVG(total_pnl) as avg_total_pnl,
        AVG(profit_factor) as avg_pf,
        AVG(sharpe_ratio) as avg_sharpe,
        AVG(max_drawdown) as avg_mdd,
        MAX(win_rate) as best_wr,
        MIN(win_rate) as worst_wr
    FROM bt100_results" . $where . "
    GROUP BY strat_id, strat_name, strat_category
    HAVING total_trades >= " . $min_trades . "
    ORDER BY avg_total_pnl DESC");

    $rankings = array();
    $rank = 1;
    $eliminated = array();
    if ($res) {
        while ($r = $res->fetch_assoc()) {
            $r['rank'] = $rank;
            $wr = floatval($r['avg_win_rate']);
            $pf = floatval($r['avg_pf']);
            $sharpe = floatval($r['avg_sharpe']);
            $trades = intval($r['total_trades']);

            // Elimination criteria
            $elim_reason = null;
            if ($wr < 35) $elim_reason = 'Win rate below 35% (' . round($wr, 1) . '%)';
            elseif ($pf < 0.8) $elim_reason = 'Profit factor below 0.8 (' . round($pf, 2) . ')';
            elseif ($trades < $min_trades) $elim_reason = 'Too few trades (' . $trades . ')';
            elseif ($sharpe < -0.5) $elim_reason = 'Negative Sharpe ratio (' . round($sharpe, 2) . ')';

            $r['eliminated'] = $elim_reason !== null;
            $r['elim_reason'] = $elim_reason;
            $r['tier'] = 'ELIMINATED';
            if (!$r['eliminated']) {
                if ($wr >= 55 && $pf >= 1.5 && $sharpe >= 0.3) $r['tier'] = 'ELITE';
                elseif ($wr >= 50 && $pf >= 1.2) $r['tier'] = 'STRONG';
                elseif ($wr >= 45 && $pf >= 1.0) $r['tier'] = 'VIABLE';
                else $r['tier'] = 'MARGINAL';
            }
            $rankings[] = $r;
            $rank++;
        }
    }

    $elite_count = 0; $strong_count = 0; $elim_count = 0;
    foreach ($rankings as $rr) {
        if ($rr['tier'] === 'ELITE') $elite_count++;
        if ($rr['tier'] === 'STRONG') $strong_count++;
        if ($rr['eliminated']) $elim_count++;
    }
    echo json_encode(array('ok' => true, 'rankings' => $rankings,
        'elite' => $elite_count,
        'strong' => $strong_count,
        'eliminated' => $elim_count
    ));
}

function _top_picks($conn) {
    $run_id = isset($_GET['run_id']) ? $_GET['run_id'] : '';
    $where = $run_id ? " AND run_id='" . $conn->real_escape_string($run_id) . "'" : '';

    // Find current BUY/SELL signals from top strategies
    $res = $conn->query("SELECT r.pair, r.signal_now, r.strat_name, r.strat_id, r.win_rate, r.profit_factor, r.sharpe_ratio, r.total_trades, r.timeframe
        FROM bt100_results r
        WHERE r.signal_now != 'HOLD' AND r.win_rate >= 45 AND r.profit_factor >= 1.0 AND r.total_trades >= 5" . $where . "
        ORDER BY r.pair, r.signal_now");

    $picks_raw = array();
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $key = $row['pair'] . '_' . $row['signal_now'];
            if (!isset($picks_raw[$key])) {
                $picks_raw[$key] = array('pair' => $row['pair'], 'direction' => $row['signal_now'] === 'BUY' ? 'LONG' : 'SHORT', 'strategies' => array(), 'avg_wr' => 0, 'avg_pf' => 0);
            }
            $picks_raw[$key]['strategies'][] = array('name' => $row['strat_name'], 'wr' => $row['win_rate'], 'pf' => $row['profit_factor'], 'tf' => $row['timeframe']);
        }
    }

    $picks = array();
    foreach ($picks_raw as $pk) {
        $cnt = count($pk['strategies']);
        if ($cnt < 3) continue; // Need at least 3 strategies agreeing
        $total_wr = 0; $total_pf = 0;
        $names = array();
        foreach ($pk['strategies'] as $s) { $total_wr += floatval($s['wr']); $total_pf += floatval($s['pf']); $names[] = $s['name'] . '(' . $s['tf'] . ')'; }
        $avg_wr = $total_wr / $cnt;
        $avg_pf = $total_pf / $cnt;
        $certainty = min(($cnt / 10) * 40 + ($avg_wr / 100) * 30 + min($avg_pf / 2, 1) * 30, 100);
        $grade = 'LOW';
        if ($certainty >= 80) $grade = 'VERY_HIGH';
        elseif ($certainty >= 65) $grade = 'HIGH';
        elseif ($certainty >= 50) $grade = 'MODERATE';

        // Get current price
        $ticker = _kraken_ticker($pk['pair']);
        $price = $ticker ? $ticker['price'] : 0;
        $tp_pct = $avg_wr > 55 ? 8 : 6;
        $sl_pct = 3;
        $tp_price = $pk['direction'] === 'LONG' ? $price * (1 + $tp_pct / 100) : $price * (1 - $tp_pct / 100);
        $sl_price = $pk['direction'] === 'LONG' ? $price * (1 - $sl_pct / 100) : $price * (1 + $sl_pct / 100);

        $thesis = $cnt . ' backtested strategies agree on ' . $pk['direction'] . '. Avg backtest win rate: ' . round($avg_wr, 1) . '%, Avg profit factor: ' . round($avg_pf, 2) . '. Strategies: ' . implode(', ', $names);

        // Save pick
        $conn->query(sprintf("INSERT INTO bt100_picks(run_id,pair,direction,entry_price,tp_price,sl_price,tp_pct,sl_pct,certainty_score,certainty_grade,strategies_agreeing,strategy_names,avg_backtest_winrate,avg_backtest_pf,thesis,status,created_at) VALUES('%s','%s','%s','%.10f','%.10f','%.10f','%.4f','%.4f','%.4f','%s',%d,'%s','%.4f','%.4f','%s','OPEN','%s')",
            $conn->real_escape_string($run_id ? $run_id : 'pick_' . date('Y-m-d_H-i')),
            $conn->real_escape_string($pk['pair']), $pk['direction'],
            $price, $tp_price, $sl_price, $tp_pct, $sl_pct,
            $certainty, $conn->real_escape_string($grade), $cnt,
            $conn->real_escape_string(implode(', ', $names)),
            $avg_wr, $avg_pf, $conn->real_escape_string($thesis), date('Y-m-d H:i:s')));

        $picks[] = array('pair' => $pk['pair'], 'direction' => $pk['direction'], 'price' => $price,
            'tp' => $tp_price, 'sl' => $sl_price, 'certainty' => round($certainty, 1), 'grade' => $grade,
            'strategies_agreeing' => $cnt, 'avg_wr' => round($avg_wr, 1), 'avg_pf' => round($avg_pf, 2),
            'strategy_names' => $names);
    }

    usort($picks, '_cmp_certainty');
    echo json_encode(array('ok' => true, 'picks' => $picks));
}

function _audit($conn) {
    $run_id = isset($_GET['run_id']) ? $_GET['run_id'] : '';
    $where = $run_id ? " WHERE run_id='" . $conn->real_escape_string($run_id) . "'" : '';
    $res = $conn->query("SELECT * FROM bt100_audit" . $where . " ORDER BY created_at DESC LIMIT 200");
    $logs = array();
    if ($res) while ($r = $res->fetch_assoc()) $logs[] = $r;
    echo json_encode(array('ok' => true, 'audit_entries' => count($logs), 'logs' => $logs));
}

function _status($conn) {
    $t = $conn->query("SELECT COUNT(*) as c FROM bt100_results")->fetch_assoc();
    $p = $conn->query("SELECT COUNT(DISTINCT pair) as c FROM bt100_results")->fetch_assoc();
    $s = $conn->query("SELECT COUNT(DISTINCT strat_id) as c FROM bt100_results")->fetch_assoc();
    $pk = $conn->query("SELECT COUNT(*) as c FROM bt100_picks")->fetch_assoc();
    $runs = array();
    $rr = $conn->query("SELECT run_id, COUNT(*) as tests, COUNT(DISTINCT pair) as pairs, MIN(created_at) as started FROM bt100_results GROUP BY run_id ORDER BY started DESC LIMIT 10");
    if ($rr) while ($r = $rr->fetch_assoc()) $runs[] = $r;
    echo json_encode(array('ok' => true, 'total_tests' => intval($t['c']), 'pairs_tested' => intval($p['c']), 'strategies_tested' => intval($s['c']), 'picks' => intval($pk['c']), 'runs' => $runs));
}

function _monitor_picks($conn) {
    $res = $conn->query("SELECT * FROM bt100_picks WHERE status='OPEN'");
    if (!$res || $res->num_rows === 0) { echo json_encode(array('ok' => true, 'msg' => 'No open picks')); return; }
    $open = array(); $pm = array();
    while ($r = $res->fetch_assoc()) { $open[] = $r; $pm[$r['pair']] = true; }
    $url = 'https://api.kraken.com/0/public/Ticker?pair=' . implode(',', array_keys($pm));
    $ch = curl_init($url); curl_setopt($ch, CURLOPT_RETURNTRANSFER, true); curl_setopt($ch, CURLOPT_TIMEOUT, 10); curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $resp = curl_exec($ch); curl_close($ch);
    $prices = array();
    if ($resp) { $d = json_decode($resp, true); if ($d && isset($d['result'])) foreach ($d['result'] as $k => $vv) $prices[$k] = floatval($vv['c'][0]); }
    $rc = 0; $now = date('Y-m-d H:i:s');
    foreach ($open as $pk) {
        $live = isset($prices[$pk['pair']]) ? $prices[$pk['pair']] : null; if (!$live) continue;
        $entry = floatval($pk['entry_price']); $tp = floatval($pk['tp_price']); $sl = floatval($pk['sl_price']); $dir = $pk['direction'];
        $pnl = $dir === 'LONG' ? (($live - $entry) / $entry) * 100 : (($entry - $live) / $entry) * 100;
        $hit_tp = $dir === 'LONG' ? $live >= $tp : $live <= $tp;
        $hit_sl = $dir === 'LONG' ? $live <= $sl : $live >= $sl;
        $hrs = (time() - strtotime($pk['created_at'])) / 3600;
        if ($hit_tp || $hit_sl || $hrs >= 72) {
            $er = $hit_tp ? 'TP_HIT' : ($hit_sl ? 'SL_HIT' : 'EXPIRED');
            $conn->query(sprintf("UPDATE bt100_picks SET status='RESOLVED',current_price='%.10f',pnl_pct='%.4f',exit_price='%.10f',exit_reason='%s',resolved_at='%s' WHERE id=%d", $live, $pnl, $live, $er, $now, intval($pk['id'])));
            $rc++;
        } else {
            $conn->query(sprintf("UPDATE bt100_picks SET current_price='%.10f',pnl_pct='%.4f' WHERE id=%d", $live, $pnl, intval($pk['id'])));
        }
    }
    echo json_encode(array('ok' => true, 'checked' => count($open), 'resolved' => $rc));
}
?>