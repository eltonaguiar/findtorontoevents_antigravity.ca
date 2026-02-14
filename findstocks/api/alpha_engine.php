<?php
/**
 * Alpha Suite - Factor Engine & Strategy Pick Generator
 * Computes 6 factor scores + composite + regime-adjusted composite.
 * Generates picks for 9 alpha strategies.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   ?action=factors           - Compute all factor scores
 *   ?action=picks             - Generate strategy picks
 *   ?action=all               - Both factors + picks
 *
 * Auth: ?key=alpharefresh2026
 */
require_once dirname(__FILE__) . '/db_connect.php';

$action = isset($_GET['action']) ? $_GET['action'] : 'status';
$key    = isset($_GET['key']) ? $_GET['key'] : '';

if ($key !== 'alpharefresh2026') {
    echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
    exit;
}

$result = array('ok' => true, 'action' => $action, 'data' => array(), 'errors' => array());

/* ================================================================
   HELPER: Cross-sectional percentile rank (0-100)
   ================================================================ */
function alpha_rank_pctile($values) {
    // $values = array('AAPL' => 0.15, 'MSFT' => 0.22, ...)
    // Returns array('AAPL' => 75.5, 'MSFT' => 92.1, ...)
    $n = count($values);
    if ($n === 0) return array();
    if ($n === 1) {
        $keys = array_keys($values);
        $out = array();
        $out[$keys[0]] = 50;
        return $out;
    }

    // Create sorted list of (ticker, value) pairs
    $pairs = array();
    foreach ($values as $k => $v) {
        $pairs[] = array('t' => $k, 'v' => (float)$v);
    }
    // Sort by value ascending
    for ($i = 0; $i < count($pairs) - 1; $i++) {
        for ($j = $i + 1; $j < count($pairs); $j++) {
            if ($pairs[$j]['v'] < $pairs[$i]['v']) {
                $tmp = $pairs[$i];
                $pairs[$i] = $pairs[$j];
                $pairs[$j] = $tmp;
            }
        }
    }

    // Assign percentile ranks
    $ranks = array();
    for ($i = 0; $i < count($pairs); $i++) {
        $ranks[$pairs[$i]['t']] = round(($i / ($n - 1)) * 100, 2);
    }
    return $ranks;
}

/* ================================================================
   HELPER: Compute standard deviation
   ================================================================ */
function alpha_stddev($arr) {
    $n = count($arr);
    if ($n < 2) return 0;
    $mean = array_sum($arr) / $n;
    $sum_sq = 0;
    for ($i = 0; $i < $n; $i++) {
        $diff = $arr[$i] - $mean;
        $sum_sq += $diff * $diff;
    }
    return sqrt($sum_sq / ($n - 1));
}

/* ================================================================
   ACTION: factors - Compute all factor scores
   ================================================================ */
if ($action === 'factors' || $action === 'all') {
    $today = date('Y-m-d');

    // Get universe tickers
    $tickers = array();
    $res = $conn->query("SELECT ticker FROM alpha_universe WHERE active=1 ORDER BY ticker");
    if ($res) {
        while ($row = $res->fetch_assoc()) {
            $tickers[] = $row['ticker'];
        }
    }
    if (count($tickers) === 0) {
        $result['errors'][] = 'No tickers in universe';
        echo json_encode($result);
        exit;
    }

    // Get current regime
    $regime_row = $conn->query("SELECT regime, regime_score, regime_detail FROM alpha_macro ORDER BY trade_date DESC LIMIT 1");
    $current_regime = 'unknown';
    $regime_score = 50;
    if ($regime_row && $r = $regime_row->fetch_assoc()) {
        $current_regime = $r['regime'];
        $regime_score = (int)$r['regime_score'];
    }

    // ── FACTOR 1: MOMENTUM (from daily_prices) ──
    $momentum_12m = array();
    $momentum_6m = array();
    $momentum_3m = array();
    $momentum_1m = array();

    // Date lookbacks
    $d12m = date('Y-m-d', strtotime('-12 months'));
    $d6m  = date('Y-m-d', strtotime('-6 months'));
    $d3m  = date('Y-m-d', strtotime('-3 months'));
    $d1m  = date('Y-m-d', strtotime('-1 month'));

    foreach ($tickers as $ticker) {
        $st = $conn->real_escape_string($ticker);

        // Get latest close
        $q = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$st' ORDER BY trade_date DESC LIMIT 1");
        $latest = 0;
        if ($q && $row = $q->fetch_assoc()) {
            $latest = (float)$row['close_price'];
        }
        if ($latest <= 0) continue;

        // Get historical closes for return calculation
        $lookbacks = array(
            '12m' => $d12m,
            '6m' => $d6m,
            '3m' => $d3m,
            '1m' => $d1m
        );
        foreach ($lookbacks as $period => $cutoff) {
            $q = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$st' AND trade_date <= '$cutoff' ORDER BY trade_date DESC LIMIT 1");
            $old = 0;
            if ($q && $row = $q->fetch_assoc()) {
                $old = (float)$row['close_price'];
            }
            $ret = ($old > 0) ? (($latest - $old) / $old) : 0;
            if ($period === '12m') $momentum_12m[$ticker] = $ret;
            if ($period === '6m')  $momentum_6m[$ticker]  = $ret;
            if ($period === '3m')  $momentum_3m[$ticker]  = $ret;
            if ($period === '1m')  $momentum_1m[$ticker]  = $ret;
        }
    }

    // Rank momentum (higher return = higher rank)
    $rank_12m = alpha_rank_pctile($momentum_12m);
    $rank_6m  = alpha_rank_pctile($momentum_6m);
    $rank_3m  = alpha_rank_pctile($momentum_3m);
    // For 1M: INVERT because short-term reversal (higher recent return = slightly lower score)
    $inv_1m = array();
    foreach ($momentum_1m as $t => $v) {
        $inv_1m[$t] = -$v;
    }
    $rank_1m = alpha_rank_pctile($inv_1m);

    // Momentum composite: 40% 12M + 35% 6M + 15% 3M + 10% (1-month reversal)
    $momentum_composite = array();
    foreach ($tickers as $t) {
        $r12 = isset($rank_12m[$t]) ? $rank_12m[$t] : 50;
        $r6  = isset($rank_6m[$t])  ? $rank_6m[$t]  : 50;
        $r3  = isset($rank_3m[$t])  ? $rank_3m[$t]  : 50;
        $r1  = isset($rank_1m[$t])  ? $rank_1m[$t]  : 50;
        $momentum_composite[$t] = round(0.40 * $r12 + 0.35 * $r6 + 0.15 * $r3 + 0.10 * $r1, 2);
    }

    // ── FACTOR 2: QUALITY (from fundamentals) ──
    $quality_roe_raw = array();
    $quality_margin_raw = array();
    $quality_fcf_raw = array();
    $quality_debt_raw = array();

    foreach ($tickers as $t) {
        $st = $conn->real_escape_string($t);
        $q = $conn->query("SELECT * FROM alpha_fundamentals WHERE ticker='$st' ORDER BY fetch_date DESC LIMIT 1");
        if ($q && $row = $q->fetch_assoc()) {
            $quality_roe_raw[$t] = (float)$row['return_on_equity'];
            $gm = (float)$row['gross_margins'];
            $om = (float)$row['operating_margins'];
            $quality_margin_raw[$t] = ($gm > 0 || $om > 0) ? ($gm * 0.6 + $om * 0.4) : 0;
            $mcap = (float)$row['market_cap'];
            $fcf  = (float)$row['free_cashflow'];
            $quality_fcf_raw[$t] = ($mcap > 0) ? ($fcf / $mcap) : 0;
            // Lower debt = higher quality (invert)
            $dte = (float)$row['debt_to_equity'];
            $quality_debt_raw[$t] = -$dte; // negative so lower debt ranks higher
        }
    }

    $rank_roe = alpha_rank_pctile($quality_roe_raw);
    $rank_margin = alpha_rank_pctile($quality_margin_raw);
    $rank_fcf = alpha_rank_pctile($quality_fcf_raw);
    $rank_debt = alpha_rank_pctile($quality_debt_raw);

    $quality_composite = array();
    foreach ($tickers as $t) {
        $r1 = isset($rank_roe[$t]) ? $rank_roe[$t] : 50;
        $r2 = isset($rank_margin[$t]) ? $rank_margin[$t] : 50;
        $r3 = isset($rank_fcf[$t]) ? $rank_fcf[$t] : 50;
        $r4 = isset($rank_debt[$t]) ? $rank_debt[$t] : 50;
        $quality_composite[$t] = round(0.30 * $r1 + 0.25 * $r2 + 0.25 * $r3 + 0.20 * $r4, 2);
    }

    // ── FACTOR 3: VALUE (from fundamentals) ──
    $value_pe_raw = array();
    $value_pb_raw = array();
    $value_ps_raw = array();
    $value_div_raw = array();

    foreach ($tickers as $t) {
        $st = $conn->real_escape_string($t);
        $q = $conn->query("SELECT * FROM alpha_fundamentals WHERE ticker='$st' ORDER BY fetch_date DESC LIMIT 1");
        if ($q && $row = $q->fetch_assoc()) {
            $pe = (float)$row['pe_forward'];
            if ($pe <= 0) $pe = (float)$row['pe_trailing'];
            $value_pe_raw[$t] = ($pe > 0) ? -$pe : -999; // lower PE = higher value
            $pb = (float)$row['price_to_book'];
            $value_pb_raw[$t] = ($pb > 0) ? -$pb : -999;
            $ps = (float)$row['price_to_sales'];
            $value_ps_raw[$t] = ($ps > 0) ? -$ps : -999;
            $value_div_raw[$t] = (float)$row['dividend_yield']; // higher div = higher value
        }
    }

    $rank_pe = alpha_rank_pctile($value_pe_raw);
    $rank_pb = alpha_rank_pctile($value_pb_raw);
    $rank_ps = alpha_rank_pctile($value_ps_raw);
    $rank_div = alpha_rank_pctile($value_div_raw);

    $value_composite = array();
    foreach ($tickers as $t) {
        $r1 = isset($rank_pe[$t]) ? $rank_pe[$t] : 50;
        $r2 = isset($rank_pb[$t]) ? $rank_pb[$t] : 50;
        $r3 = isset($rank_ps[$t]) ? $rank_ps[$t] : 50;
        $r4 = isset($rank_div[$t]) ? $rank_div[$t] : 50;
        $value_composite[$t] = round(0.30 * $r1 + 0.25 * $r2 + 0.25 * $r3 + 0.20 * $r4, 2);
    }

    // ── FACTOR 4: EARNINGS (from alpha_earnings) ──
    $earn_surprise_raw = array();
    $earn_beat_raw = array();
    $earn_growth_raw = array();

    foreach ($tickers as $t) {
        $st = $conn->real_escape_string($t);
        $q = $conn->query("SELECT surprise_pct FROM alpha_earnings WHERE ticker='$st' ORDER BY quarter_end DESC LIMIT 4");
        $surprises = array();
        $beats = 0;
        if ($q) {
            while ($row = $q->fetch_assoc()) {
                $s = (float)$row['surprise_pct'];
                $surprises[] = $s;
                if ($s > 0) $beats++;
            }
        }
        $avg_surprise = (count($surprises) > 0) ? array_sum($surprises) / count($surprises) : 0;
        $beat_rate = (count($surprises) > 0) ? ($beats / count($surprises)) : 0;
        $earn_surprise_raw[$t] = $avg_surprise;
        $earn_beat_raw[$t] = $beat_rate;

        // Earnings growth from fundamentals
        $qf = $conn->query("SELECT earnings_growth FROM alpha_fundamentals WHERE ticker='$st' ORDER BY fetch_date DESC LIMIT 1");
        $eg = 0;
        if ($qf && $row = $qf->fetch_assoc()) {
            $eg = (float)$row['earnings_growth'];
        }
        $earn_growth_raw[$t] = $eg;
    }

    $rank_surprise = alpha_rank_pctile($earn_surprise_raw);
    $rank_beat = alpha_rank_pctile($earn_beat_raw);
    $rank_egrow = alpha_rank_pctile($earn_growth_raw);

    $earnings_composite = array();
    foreach ($tickers as $t) {
        $r1 = isset($rank_surprise[$t]) ? $rank_surprise[$t] : 50;
        $r2 = isset($rank_beat[$t]) ? $rank_beat[$t] : 50;
        $r3 = isset($rank_egrow[$t]) ? $rank_egrow[$t] : 50;
        $earnings_composite[$t] = round(0.45 * $r1 + 0.30 * $r2 + 0.25 * $r3, 2);
    }

    // ── FACTOR 5: VOLATILITY (from daily_prices) ──
    $vol_60d_raw = array();
    $vol_beta_raw = array();
    $vol_dd_raw = array();

    // Get SPY returns for beta calculation
    $spy_returns = array();
    $spy_q = $conn->query("SELECT trade_date, close_price FROM daily_prices WHERE ticker='SPY' ORDER BY trade_date DESC LIMIT 252");
    if (!$spy_q || $spy_q->num_rows < 10) {
        // Try ^GSPC or use alpha_macro
        $spy_q = $conn->query("SELECT trade_date, spy_close as close_price FROM alpha_macro WHERE spy_close > 0 ORDER BY trade_date DESC LIMIT 252");
    }
    $spy_prices = array();
    if ($spy_q) {
        while ($row = $spy_q->fetch_assoc()) {
            $spy_prices[] = (float)$row['close_price'];
        }
    }
    $spy_prices = array_reverse($spy_prices); // oldest first
    for ($i = 1; $i < count($spy_prices); $i++) {
        if ($spy_prices[$i - 1] > 0) {
            $spy_returns[] = ($spy_prices[$i] - $spy_prices[$i - 1]) / $spy_prices[$i - 1];
        }
    }

    foreach ($tickers as $t) {
        $st = $conn->real_escape_string($t);

        // Get last 252 trading days of prices
        $pq = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$st' ORDER BY trade_date DESC LIMIT 252");
        $prices = array();
        if ($pq) {
            while ($row = $pq->fetch_assoc()) {
                $prices[] = (float)$row['close_price'];
            }
        }
        $prices = array_reverse($prices); // oldest first

        if (count($prices) < 30) continue;

        // Daily returns
        $returns = array();
        for ($i = 1; $i < count($prices); $i++) {
            if ($prices[$i - 1] > 0) {
                $returns[] = ($prices[$i] - $prices[$i - 1]) / $prices[$i - 1];
            }
        }

        // 60-day realized vol (annualized) - INVERT: lower vol = higher score
        $recent_returns = array_slice($returns, -60);
        $vol60 = alpha_stddev($recent_returns) * sqrt(252);
        $vol_60d_raw[$t] = -$vol60;

        // Beta vs SPY (lower beta = higher defensive score)
        $min_len = min(count($returns), count($spy_returns));
        if ($min_len >= 30) {
            $stock_slice = array_slice($returns, -$min_len);
            $spy_slice = array_slice($spy_returns, -$min_len);
            $mean_s = array_sum($stock_slice) / $min_len;
            $mean_m = array_sum($spy_slice) / $min_len;
            $cov = 0;
            $var_m = 0;
            for ($i = 0; $i < $min_len; $i++) {
                $cov += ($stock_slice[$i] - $mean_s) * ($spy_slice[$i] - $mean_m);
                $var_m += ($spy_slice[$i] - $mean_m) * ($spy_slice[$i] - $mean_m);
            }
            $beta = ($var_m > 0) ? ($cov / $var_m) : 1;
            $vol_beta_raw[$t] = -$beta; // lower beta = higher score
        } else {
            $vol_beta_raw[$t] = -1;
        }

        // Max drawdown last 90 days (smaller = better, so negate)
        $recent_prices = array_slice($prices, -90);
        $peak = $recent_prices[0];
        $max_dd = 0;
        for ($i = 1; $i < count($recent_prices); $i++) {
            if ($recent_prices[$i] > $peak) $peak = $recent_prices[$i];
            $dd = ($peak > 0) ? (($peak - $recent_prices[$i]) / $peak) : 0;
            if ($dd > $max_dd) $max_dd = $dd;
        }
        $vol_dd_raw[$t] = -$max_dd; // smaller drawdown = higher score
    }

    $rank_vol60 = alpha_rank_pctile($vol_60d_raw);
    $rank_beta = alpha_rank_pctile($vol_beta_raw);
    $rank_dd = alpha_rank_pctile($vol_dd_raw);

    $vol_composite = array();
    foreach ($tickers as $t) {
        $r1 = isset($rank_vol60[$t]) ? $rank_vol60[$t] : 50;
        $r2 = isset($rank_beta[$t]) ? $rank_beta[$t] : 50;
        $r3 = isset($rank_dd[$t]) ? $rank_dd[$t] : 50;
        $vol_composite[$t] = round(0.40 * $r1 + 0.35 * $r2 + 0.25 * $r3, 2);
    }

    // ── FACTOR 6: GROWTH (from fundamentals) ──
    $growth_rev_raw = array();
    $growth_earn_raw = array();

    foreach ($tickers as $t) {
        $st = $conn->real_escape_string($t);
        $q = $conn->query("SELECT revenue_growth, earnings_growth, pe_forward, pe_trailing FROM alpha_fundamentals WHERE ticker='$st' ORDER BY fetch_date DESC LIMIT 1");
        if ($q && $row = $q->fetch_assoc()) {
            $growth_rev_raw[$t] = (float)$row['revenue_growth'];
            $growth_earn_raw[$t] = (float)$row['earnings_growth'];
        }
    }

    $rank_rgrow = alpha_rank_pctile($growth_rev_raw);
    $rank_egrow2 = alpha_rank_pctile($growth_earn_raw);

    $growth_composite = array();
    foreach ($tickers as $t) {
        $r1 = isset($rank_rgrow[$t]) ? $rank_rgrow[$t] : 50;
        $r2 = isset($rank_egrow2[$t]) ? $rank_egrow2[$t] : 50;
        $growth_composite[$t] = round(0.50 * $r1 + 0.50 * $r2, 2);
    }

    // ── COMPOSITE: Regime-adjusted multi-factor blend ──
    // Base weights: Momentum 25%, Quality 20%, Value 20%, Earnings 15%, Vol 10%, Growth 10%
    $base_w = array('m' => 0.25, 'q' => 0.20, 'v' => 0.20, 'e' => 0.15, 'vol' => 0.10, 'g' => 0.10);

    // Regime adjustments
    $regime_w = $base_w;
    if (strpos($current_regime, 'goldilocks') !== false) {
        $regime_w = array('m' => 0.30, 'q' => 0.15, 'v' => 0.15, 'e' => 0.20, 'vol' => 0.05, 'g' => 0.15);
    } elseif (strpos($current_regime, 'calm_bull') !== false) {
        $regime_w = array('m' => 0.30, 'q' => 0.18, 'v' => 0.15, 'e' => 0.17, 'vol' => 0.05, 'g' => 0.15);
    } elseif (strpos($current_regime, 'moderate_bull') !== false) {
        $regime_w = array('m' => 0.25, 'q' => 0.20, 'v' => 0.20, 'e' => 0.15, 'vol' => 0.10, 'g' => 0.10);
    } elseif (strpos($current_regime, 'bear') !== false) {
        $regime_w = array('m' => 0.10, 'q' => 0.30, 'v' => 0.25, 'e' => 0.10, 'vol' => 0.20, 'g' => 0.05);
    } elseif (strpos($current_regime, 'high_vol') !== false) {
        $regime_w = array('m' => 0.10, 'q' => 0.25, 'v' => 0.20, 'e' => 0.10, 'vol' => 0.25, 'g' => 0.10);
    } elseif (strpos($current_regime, 'extreme') !== false) {
        $regime_w = array('m' => 0.05, 'q' => 0.30, 'v' => 0.20, 'e' => 0.05, 'vol' => 0.35, 'g' => 0.05);
    }

    $composite_base = array();
    $composite_regime = array();

    foreach ($tickers as $t) {
        $m = isset($momentum_composite[$t]) ? $momentum_composite[$t] : 50;
        $q = isset($quality_composite[$t]) ? $quality_composite[$t] : 50;
        $v = isset($value_composite[$t]) ? $value_composite[$t] : 50;
        $e = isset($earnings_composite[$t]) ? $earnings_composite[$t] : 50;
        $vol = isset($vol_composite[$t]) ? $vol_composite[$t] : 50;
        $g = isset($growth_composite[$t]) ? $growth_composite[$t] : 50;

        $composite_base[$t] = round(
            $base_w['m'] * $m + $base_w['q'] * $q + $base_w['v'] * $v +
            $base_w['e'] * $e + $base_w['vol'] * $vol + $base_w['g'] * $g, 2);

        $composite_regime[$t] = round(
            $regime_w['m'] * $m + $regime_w['q'] * $q + $regime_w['v'] * $v +
            $regime_w['e'] * $e + $regime_w['vol'] * $vol + $regime_w['g'] * $g, 2);
    }

    // Final rankings
    $rank_composite = alpha_rank_pctile($composite_base);
    $rank_regime_adj = alpha_rank_pctile($composite_regime);
    $rank_momentum_final = alpha_rank_pctile($momentum_composite);
    $rank_quality_final = alpha_rank_pctile($quality_composite);
    $rank_value_final = alpha_rank_pctile($value_composite);
    $rank_earnings_final = alpha_rank_pctile($earnings_composite);
    $rank_vol_final = alpha_rank_pctile($vol_composite);
    $rank_growth_final = alpha_rank_pctile($growth_composite);

    // ── INSERT FACTOR SCORES ──
    $scores_inserted = 0;
    foreach ($tickers as $t) {
        $st = $conn->real_escape_string($t);

        $m12 = isset($momentum_12m[$t]) ? round($momentum_12m[$t], 4) : 0;
        $m6  = isset($momentum_6m[$t])  ? round($momentum_6m[$t], 4) : 0;
        $m3  = isset($momentum_3m[$t])  ? round($momentum_3m[$t], 4) : 0;
        $m1  = isset($momentum_1m[$t])  ? round($momentum_1m[$t], 4) : 0;
        $ms  = isset($momentum_composite[$t]) ? $momentum_composite[$t] : 50;
        $mr  = isset($rank_momentum_final[$t]) ? (int)round($rank_momentum_final[$t]) : 50;

        $qroe = isset($quality_roe_raw[$t]) ? round($quality_roe_raw[$t], 4) : 0;
        $qmarg = isset($quality_margin_raw[$t]) ? round($quality_margin_raw[$t], 4) : 0;
        $qfcf = isset($quality_fcf_raw[$t]) ? round($quality_fcf_raw[$t], 4) : 0;
        $qdebt = isset($quality_debt_raw[$t]) ? round(-$quality_debt_raw[$t], 4) : 0; // un-negate
        $qs = isset($quality_composite[$t]) ? $quality_composite[$t] : 50;
        $qr = isset($rank_quality_final[$t]) ? (int)round($rank_quality_final[$t]) : 50;

        $vpe = isset($value_pe_raw[$t]) ? round(-$value_pe_raw[$t], 4) : 0; // un-negate
        $vpb = isset($value_pb_raw[$t]) ? round(-$value_pb_raw[$t], 4) : 0;
        $vps = isset($value_ps_raw[$t]) ? round(-$value_ps_raw[$t], 4) : 0;
        $vdy = isset($value_div_raw[$t]) ? round($value_div_raw[$t], 6) : 0;
        $vs = isset($value_composite[$t]) ? $value_composite[$t] : 50;
        $vr = isset($rank_value_final[$t]) ? (int)round($rank_value_final[$t]) : 50;

        $esa = isset($earn_surprise_raw[$t]) ? round($earn_surprise_raw[$t], 4) : 0;
        $ebr = isset($earn_beat_raw[$t]) ? round($earn_beat_raw[$t], 4) : 0;
        $egr = isset($earn_growth_raw[$t]) ? round($earn_growth_raw[$t], 4) : 0;
        $es = isset($earnings_composite[$t]) ? $earnings_composite[$t] : 50;
        $er = isset($rank_earnings_final[$t]) ? (int)round($rank_earnings_final[$t]) : 50;

        $v60 = isset($vol_60d_raw[$t]) ? round(-$vol_60d_raw[$t], 4) : 0; // un-negate
        $vb = isset($vol_beta_raw[$t]) ? round(-$vol_beta_raw[$t], 4) : 0;
        $vdd = isset($vol_dd_raw[$t]) ? round(-$vol_dd_raw[$t], 4) : 0;
        $vols = isset($vol_composite[$t]) ? $vol_composite[$t] : 50;
        $volr = isset($rank_vol_final[$t]) ? (int)round($rank_vol_final[$t]) : 50;

        $grr = isset($growth_rev_raw[$t]) ? round($growth_rev_raw[$t], 4) : 0;
        $gre = isset($growth_earn_raw[$t]) ? round($growth_earn_raw[$t], 4) : 0;
        $gs  = isset($growth_composite[$t]) ? $growth_composite[$t] : 50;
        $grank = isset($rank_growth_final[$t]) ? (int)round($rank_growth_final[$t]) : 50;

        $cs = isset($composite_base[$t]) ? $composite_base[$t] : 50;
        $cr = isset($rank_composite[$t]) ? (int)round($rank_composite[$t]) : 50;
        $ras = isset($composite_regime[$t]) ? $composite_regime[$t] : 50;
        $rar = isset($rank_regime_adj[$t]) ? (int)round($rank_regime_adj[$t]) : 50;

        $factors_detail = array(
            'regime' => $current_regime,
            'regime_weights' => $regime_w,
            'momentum_components' => array('12m' => $m12, '6m' => $m6, '3m' => $m3, '1m' => $m1),
            'quality_components' => array('roe' => $qroe, 'margins' => $qmarg, 'fcf_yield' => $qfcf, 'debt_equity' => $qdebt),
            'value_components' => array('pe' => $vpe, 'pb' => $vpb, 'ps' => $vps, 'div_yield' => $vdy),
            'earnings_components' => array('avg_surprise' => $esa, 'beat_rate' => $ebr, 'growth' => $egr),
            'vol_components' => array('vol_60d' => $v60, 'beta' => $vb, 'max_dd_90d' => $vdd)
        );
        $safe_json = $conn->real_escape_string(json_encode($factors_detail));

        $sql = "INSERT INTO alpha_factor_scores
                (ticker, score_date,
                 momentum_12m, momentum_6m, momentum_3m, momentum_1m, momentum_score, momentum_rank,
                 quality_roe, quality_margins, quality_fcf_yield, quality_debt, quality_score, quality_rank,
                 value_pe, value_pb, value_ps, value_div_yield, value_score, value_rank,
                 earnings_surprise_avg, earnings_beat_rate, earnings_growth_rate, earnings_score, earnings_rank,
                 vol_realized_60d, vol_beta, vol_max_dd_90d, vol_score, vol_rank,
                 growth_revenue, growth_earnings, growth_score, growth_rank,
                 composite_score, composite_rank, regime_adj_score, regime_adj_rank, factors_json)
                VALUES ('$st', '$today',
                        $m12,$m6,$m3,$m1,$ms,$mr,
                        $qroe,$qmarg,$qfcf,$qdebt,$qs,$qr,
                        $vpe,$vpb,$vps,$vdy,$vs,$vr,
                        $esa,$ebr,$egr,$es,$er,
                        $v60,$vb,$vdd,$vols,$volr,
                        $grr,$gre,$gs,$grank,
                        $cs,$cr,$ras,$rar,'$safe_json')
                ON DUPLICATE KEY UPDATE
                    momentum_12m=$m12, momentum_6m=$m6, momentum_3m=$m3, momentum_1m=$m1,
                    momentum_score=$ms, momentum_rank=$mr,
                    quality_roe=$qroe, quality_margins=$qmarg, quality_fcf_yield=$qfcf, quality_debt=$qdebt,
                    quality_score=$qs, quality_rank=$qr,
                    value_pe=$vpe, value_pb=$vpb, value_ps=$vps, value_div_yield=$vdy,
                    value_score=$vs, value_rank=$vr,
                    earnings_surprise_avg=$esa, earnings_beat_rate=$ebr, earnings_growth_rate=$egr,
                    earnings_score=$es, earnings_rank=$er,
                    vol_realized_60d=$v60, vol_beta=$vb, vol_max_dd_90d=$vdd,
                    vol_score=$vols, vol_rank=$volr,
                    growth_revenue=$grr, growth_earnings=$gre,
                    growth_score=$gs, growth_rank=$grank,
                    composite_score=$cs, composite_rank=$cr,
                    regime_adj_score=$ras, regime_adj_rank=$rar, factors_json='$safe_json'";

        if ($conn->query($sql)) {
            $scores_inserted++;
        } else {
            $result['errors'][] = 'Factor insert fail ' . $t . ': ' . $conn->error;
        }
    }

    $result['data']['factors'] = array(
        'computed' => $scores_inserted,
        'total' => count($tickers),
        'regime' => $current_regime,
        'regime_score' => $regime_score,
        'regime_weights' => $regime_w
    );
}

/* ================================================================
   ACTION: picks - Generate strategy picks from factor scores
   ================================================================ */
if ($action === 'picks' || $action === 'all') {
    $today = date('Y-m-d');
    $now = date('Y-m-d H:i:s');

    // Load factor scores for today (or most recent)
    $scores = array();
    $q = $conn->query("SELECT * FROM alpha_factor_scores WHERE score_date = (SELECT MAX(score_date) FROM alpha_factor_scores) ORDER BY composite_rank DESC");
    if ($q) {
        while ($row = $q->fetch_assoc()) {
            $scores[$row['ticker']] = $row;
        }
    }

    if (count($scores) === 0) {
        $result['errors'][] = 'No factor scores found. Run factors first.';
        echo json_encode($result);
        exit;
    }

    // Load latest fundamentals for price/rationale
    $fund = array();
    foreach ($scores as $t => $s) {
        $st = $conn->real_escape_string($t);
        $fq = $conn->query("SELECT * FROM alpha_fundamentals WHERE ticker='$st' ORDER BY fetch_date DESC LIMIT 1");
        if ($fq && $row = $fq->fetch_assoc()) {
            $fund[$t] = $row;
        }
    }

    // Load current regime
    $regime_q = $conn->query("SELECT regime FROM alpha_macro ORDER BY trade_date DESC LIMIT 1");
    $regime = 'unknown';
    if ($regime_q && $r = $regime_q->fetch_assoc()) {
        $regime = $r['regime'];
    }

    // Helper: sort scores by a field descending
    $strategies = array(
        'Alpha Factor Momentum'  => array('sort' => 'momentum_score',  'top_n' => 10, 'horizon' => '1m',  'risk' => 'Medium'),
        'Alpha Factor Quality'   => array('sort' => 'quality_score',   'top_n' => 10, 'horizon' => '3m',  'risk' => 'Low'),
        'Alpha Factor Value'     => array('sort' => 'value_score',     'top_n' => 10, 'horizon' => '3m',  'risk' => 'Medium'),
        'Alpha Factor Earnings'  => array('sort' => 'earnings_score',  'top_n' => 10, 'horizon' => '2m',  'risk' => 'Medium'),
        'Alpha Factor Low Vol'   => array('sort' => 'vol_score',       'top_n' => 10, 'horizon' => '3m',  'risk' => 'Low'),
        'Alpha Factor Growth'    => array('sort' => 'growth_score',    'top_n' => 10, 'horizon' => '3m',  'risk' => 'Medium-High'),
        'Alpha Factor Composite' => array('sort' => 'regime_adj_score','top_n' => 10, 'horizon' => '1m',  'risk' => 'Medium'),
        'Alpha Factor Safe Bets' => array('sort' => 'safe_score',      'top_n' => 10, 'horizon' => '6m',  'risk' => 'Low')
    );

    // Compute "Safe Bets" score: quality 35% + low_vol 35% + value 20% + earnings 10%
    $safe_scores = array();
    foreach ($scores as $t => $s) {
        $safe_scores[$t] = round(
            0.35 * (float)$s['quality_score'] +
            0.35 * (float)$s['vol_score'] +
            0.20 * (float)$s['value_score'] +
            0.10 * (float)$s['earnings_score'], 2);
    }

    $total_picks = 0;
    $picks_by_strategy = array();

    foreach ($strategies as $strat_name => $cfg) {
        $sort_field = $cfg['sort'];
        $top_n = $cfg['top_n'];

        // Build sortable array
        $sortable = array();
        foreach ($scores as $t => $s) {
            if ($sort_field === 'safe_score') {
                $sortable[$t] = isset($safe_scores[$t]) ? $safe_scores[$t] : 0;
            } else {
                $sortable[$t] = (float)$s[$sort_field];
            }
        }
        arsort($sortable); // Sort descending

        $rank = 0;
        $strat_picks = array();
        foreach ($sortable as $t => $score_val) {
            $rank++;
            if ($rank > $top_n) break;

            $s = $scores[$t];
            $f = isset($fund[$t]) ? $fund[$t] : array();
            $price = isset($f['regular_market_price']) ? (float)$f['regular_market_price'] : 0;
            if ($price <= 0) {
                // Try daily_prices
                $st = $conn->real_escape_string($t);
                $pq = $conn->query("SELECT close_price FROM daily_prices WHERE ticker='$st' ORDER BY trade_date DESC LIMIT 1");
                if ($pq && $pr = $pq->fetch_assoc()) {
                    $price = (float)$pr['close_price'];
                }
            }

            // Conviction based on rank
            $conviction = 'medium';
            if ($rank <= 3) $conviction = 'high';
            if ($rank >= 8) $conviction = 'low';

            // Position sizing suggestion (Kelly-lite: higher conviction = larger position)
            $pos_size = 5.0;
            if ($conviction === 'high') $pos_size = 8.0;
            if ($conviction === 'low') $pos_size = 3.0;
            if ($cfg['risk'] === 'Low') $pos_size = $pos_size * 1.2;

            // Stop loss / take profit based on volatility
            $vol60 = isset($s['vol_realized_60d']) ? (float)$s['vol_realized_60d'] : 0.20;
            $sl = round(max(5, min(20, $vol60 * 100 * 1.5)), 1);
            $tp = round(max(10, min(40, $vol60 * 100 * 3)), 1);
            if ($cfg['risk'] === 'Low') {
                $sl = round($sl * 0.7, 1);
                $tp = 999; // long hold, no TP
            }

            // Rationale
            $rationale_parts = array();
            $rationale_parts[] = 'Rank #' . $rank . ' in ' . $strat_name;
            $rationale_parts[] = 'Composite: ' . round((float)$s['composite_score'], 1);
            $rationale_parts[] = 'Regime: ' . $regime;
            if ((float)$s['momentum_score'] > 70) $rationale_parts[] = 'Strong momentum';
            if ((float)$s['quality_score'] > 70) $rationale_parts[] = 'High quality';
            if ((float)$s['value_score'] > 70) $rationale_parts[] = 'Attractive valuation';
            if ((float)$s['earnings_score'] > 70) $rationale_parts[] = 'Earnings strength';
            if ((float)$s['vol_score'] > 70) $rationale_parts[] = 'Low volatility';
            $rationale = implode('. ', $rationale_parts);

            // Top factors
            $factor_scores_arr = array(
                'Momentum' => round((float)$s['momentum_score'], 1),
                'Quality' => round((float)$s['quality_score'], 1),
                'Value' => round((float)$s['value_score'], 1),
                'Earnings' => round((float)$s['earnings_score'], 1),
                'Low Vol' => round((float)$s['vol_score'], 1),
                'Growth' => round((float)$s['growth_score'], 1)
            );
            arsort($factor_scores_arr);
            $top3 = array_slice($factor_scores_arr, 0, 3, true);
            $top_factors = array();
            foreach ($top3 as $fname => $fval) {
                $top_factors[] = $fname . ': ' . $fval;
            }

            // Avoid reasons
            $avoid = array();
            if ((float)$s['vol_realized_60d'] > 0.50) $avoid[] = 'Very high volatility (' . round((float)$s['vol_realized_60d'] * 100, 1) . '%)';
            if ($price <= 0) $avoid[] = 'No price data';

            $hash = sha1('alpha_' . $t . '_' . $today . '_' . $strat_name);
            $safe_hash = $conn->real_escape_string($hash);

            // Check duplicate
            $dup = $conn->query("SELECT id FROM alpha_picks WHERE pick_hash='$safe_hash'");
            if ($dup && $dup->num_rows > 0) continue;

            $safe_ticker = $conn->real_escape_string($t);
            $safe_strat = $conn->real_escape_string($strat_name);
            $safe_rationale = $conn->real_escape_string($rationale);
            $safe_top = $conn->real_escape_string(implode('; ', $top_factors));
            $safe_avoid = $conn->real_escape_string(implode('; ', $avoid));

            $sql = "INSERT INTO alpha_picks
                    (ticker, strategy, pick_date, entry_price, score, conviction, expected_horizon,
                     risk_level, position_size_pct, stop_loss_pct, take_profit_pct,
                     rationale, top_factors, avoid_reasons, pick_hash, created_at)
                    VALUES ('$safe_ticker', '$safe_strat', '$today', $price, $score_val,
                            '$conviction', '" . $cfg['horizon'] . "', '" . $cfg['risk'] . "',
                            $pos_size, $sl, $tp,
                            '$safe_rationale', '$safe_top', '$safe_avoid', '$safe_hash', '$now')";

            if ($conn->query($sql)) {
                $total_picks++;
                $strat_picks[] = $t;

                // Audit Trail for each strategy pick
                $a_strat_data = json_encode(array('strategy' => $strat_name, 'score' => $score_val, 'conviction' => $conviction, 'regime' => $regime, 'top_factors' => $top_factors));
                $a_strat_details = json_encode(array('entry_price' => $price, 'tp_pct' => $tp, 'sl_pct' => $sl, 'risk' => $cfg['risk'], 'horizon' => $cfg['horizon']));
                $a_strat_ai = "Analyze: " . $t . " picked by " . $strat_name . ". " . $rationale . "\nData: " . $a_strat_data;
                $conn->query("INSERT INTO audit_trails (asset_class, symbol, pick_timestamp, generation_source, reasons, supporting_data, pick_details, formatted_for_ai) VALUES ('STOCKS', '$safe_ticker', '$now', 'alpha_engine.php - " . $conn->real_escape_string($strat_name) . "', '" . $conn->real_escape_string($rationale) . "', '" . $conn->real_escape_string($a_strat_data) . "', '" . $conn->real_escape_string($a_strat_details) . "', '" . $conn->real_escape_string($a_strat_ai) . "')");
            }

            // Also insert into main stock_picks table for backtesting
            $main_hash = sha1('alphafactor_' . $t . '_' . $today . '_' . $strat_name);
            $safe_main_hash = $conn->real_escape_string($main_hash);
            $dup2 = $conn->query("SELECT id FROM stock_picks WHERE pick_hash='$safe_main_hash'");
            if (!$dup2 || $dup2->num_rows === 0) {
                $algo_q = $conn->query("SELECT id FROM algorithms WHERE name='$safe_strat' LIMIT 1");
                $algo_id = 0;
                if ($algo_q && $ar = $algo_q->fetch_assoc()) {
                    $algo_id = (int)$ar['id'];
                }
                $indicators = array(
                    'strategy' => $strat_name,
                    'factor_scores' => $factor_scores_arr,
                    'composite' => round((float)$s['composite_score'], 1),
                    'regime_adj' => round((float)$s['regime_adj_score'], 1),
                    'regime' => $regime,
                    'conviction' => $conviction,
                    'top_factors' => $top_factors,
                    'safe_score' => isset($safe_scores[$t]) ? $safe_scores[$t] : 0
                );
                $safe_indicators = $conn->real_escape_string(json_encode($indicators));
                $score_int = min(100, max(0, (int)round($score_val)));
                $rating = ($conviction === 'high') ? 'Strong Buy' : (($conviction === 'medium') ? 'Buy' : 'Speculative Buy');
                $sl_price = ($price > 0) ? round($price * (1 - $sl / 100), 4) : 0;

                $conn->query("INSERT INTO stock_picks
                    (ticker, algorithm_id, algorithm_name, pick_date, pick_time, entry_price, simulated_entry_price,
                     score, rating, risk_level, timeframe, stop_loss_price, pick_hash, indicators_json, verified)
                    VALUES ('$safe_ticker', $algo_id, '$safe_strat', '$today', '$now', $price, $price,
                            $score_int, '$rating', '" . $cfg['risk'] . "', '" . $cfg['horizon'] . "',
                            $sl_price, '$safe_main_hash', '$safe_indicators', 1)");
            }
        }
        $picks_by_strategy[$strat_name] = $strat_picks;
    }

    // ── CONSENSUS STRATEGY: Stocks in 3+ strategies ──
    $consensus_count = array();
    foreach ($picks_by_strategy as $strat => $strat_tickers) {
        foreach ($strat_tickers as $t) {
            if (!isset($consensus_count[$t])) $consensus_count[$t] = 0;
            $consensus_count[$t]++;
        }
    }

    $consensus_picks = array();
    foreach ($consensus_count as $t => $cnt) {
        if ($cnt >= 3) {
            $consensus_picks[] = array('ticker' => $t, 'count' => $cnt);
        }
    }

    // Sort by appearance count desc
    for ($i = 0; $i < count($consensus_picks) - 1; $i++) {
        for ($j = $i + 1; $j < count($consensus_picks); $j++) {
            if ($consensus_picks[$j]['count'] > $consensus_picks[$i]['count']) {
                $tmp = $consensus_picks[$i];
                $consensus_picks[$i] = $consensus_picks[$j];
                $consensus_picks[$j] = $tmp;
            }
        }
    }

    foreach ($consensus_picks as $cp) {
        $t = $cp['ticker'];
        $cnt = $cp['count'];
        $hash = sha1('alpha_' . $t . '_' . $today . '_Alpha Factor Consensus');
        $safe_hash = $conn->real_escape_string($hash);
        $dup = $conn->query("SELECT id FROM alpha_picks WHERE pick_hash='$safe_hash'");
        if ($dup && $dup->num_rows > 0) continue;

        $s = isset($scores[$t]) ? $scores[$t] : array();
        $f = isset($fund[$t]) ? $fund[$t] : array();
        $price = isset($f['regular_market_price']) ? (float)$f['regular_market_price'] : 0;
        $cs = isset($s['composite_score']) ? (float)$s['composite_score'] : 50;

        $safe_ticker = $conn->real_escape_string($t);
        $rationale = 'Consensus pick: appears in ' . $cnt . ' strategies. Composite score: ' . round($cs, 1);
        $safe_rationale = $conn->real_escape_string($rationale);

        $conn->query("INSERT INTO alpha_picks
            (ticker, strategy, pick_date, entry_price, score, conviction, expected_horizon,
             risk_level, position_size_pct, stop_loss_pct, take_profit_pct,
             rationale, top_factors, avoid_reasons, pick_hash, created_at)
            VALUES ('$safe_ticker', 'Alpha Factor Consensus', '$today', $price, $cs,
                    'high', '1m', 'Medium', 8.0, 10.0, 25.0,
                    '$safe_rationale', 'Multi-strategy consensus', '', '$safe_hash', '$now')");
        $total_picks++;

        // Audit Trail
        $a_data = json_encode(array('composite_score' => $cs, 'strategy_count' => $cnt, 'regime' => $regime));
        $a_details = json_encode(array('entry_price' => $price, 'conviction' => 'high', 'horizon' => '1m', 'risk_level' => 'Medium'));
        $a_ai = "Analyze this stock pick:\nSymbol: " . $t . "\nStrategy: Alpha Factor Consensus\nRationale: " . $rationale . "\nData: " . $a_data;
        $conn->query("INSERT INTO audit_trails (asset_class, symbol, pick_timestamp, generation_source, reasons, supporting_data, pick_details, formatted_for_ai) VALUES ('STOCKS', '$safe_ticker', '$now', 'alpha_engine.php - Consensus', '" . $conn->real_escape_string($rationale) . "', '" . $conn->real_escape_string($a_data) . "', '" . $conn->real_escape_string($a_details) . "', '" . $conn->real_escape_string($a_ai) . "')");
    }

    // ── UPDATE ALPHA STATUS ──
    $next_refresh = date('Y-m-d H:i:s', strtotime('tomorrow 21:30:00 UTC'));
    // If today is Friday, next is Monday
    $dow = date('N');
    if ($dow == 5) {
        $next_refresh = date('Y-m-d H:i:s', strtotime('+3 days 21:30:00 UTC'));
    } elseif ($dow == 6) {
        $next_refresh = date('Y-m-d H:i:s', strtotime('+2 days 21:30:00 UTC'));
    }

    $summary = array(
        'regime' => $regime,
        'factors_computed' => count($scores),
        'picks_generated' => $total_picks,
        'consensus_picks' => count($consensus_picks),
        'strategies' => array_keys($picks_by_strategy)
    );
    $safe_summary = $conn->real_escape_string(json_encode($summary));
    $safe_regime = $conn->real_escape_string($regime);

    $conn->query("UPDATE alpha_status SET
        last_refresh_end='$now',
        last_refresh_status='completed',
        next_expected_refresh='$next_refresh',
        universe_count=" . count($scores) . ",
        factors_computed=" . count($scores) . ",
        picks_generated=$total_picks,
        current_regime='$safe_regime',
        summary_json='$safe_summary'
        WHERE id=1");

    $result['data']['picks'] = array(
        'total' => $total_picks,
        'by_strategy' => $picks_by_strategy,
        'consensus' => $consensus_picks
    );

    // Log
    $detail = $conn->real_escape_string(json_encode($result['data']['picks']));
    $conn->query("INSERT INTO alpha_refresh_log (refresh_date, step, status, details, tickers_processed, errors_count)
                  VALUES ('$now', 'generate_picks', 'completed', '$detail', $total_picks, " . count($result['errors']) . ")");
}

echo json_encode($result);
$conn->close();
?>
