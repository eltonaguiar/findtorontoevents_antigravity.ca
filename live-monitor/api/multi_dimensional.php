<?php
/**
 * Multi-Dimensional Stock Intelligence API
 * Computes 9 dimension scores (0-100) per ticker and a composite conviction score.
 * Reads from existing tables + free data sources.
 * PHP 5.2 compatible.
 *
 * Dimensions:
 *   1. Whale (13F)    — Fund holdings + net change momentum
 *   2. Insider (Form4) — Net insider buy ratio + clustering
 *   3. Analyst         — Consensus rating + price target upside
 *   4. Crowd           — News sentiment + buzz + WSB
 *   5. Fear/Greed      — Inverted composite (extreme fear = bullish)
 *   6. Regime          — Market regime + ticker momentum
 *   7. Value           — P/E, P/B, P/S ratios vs industry (NEW)
 *   8. Growth          — Revenue growth, earnings growth (NEW)
 *   9. Momentum        — Enhanced technical momentum (NEW)
 *
 * Actions:
 *   ?action=ticker&ticker=AAPL  — Per-stock 9D scores + conviction
 *   ?action=market              — Market-wide: F&G + regime + avg conviction
 *   ?action=top_picks           — Top 10 stocks by conviction
 *   ?action=radar&ticker=AAPL   — Chart-ready radar data
 *   ?action=calculate&key=...   — Admin: recalculate all tickers
 *   ?action=all                 — All tickers with 9D scores
 *   ?action=free_scores&ticker=AAPL — Get free data scores
 */
require_once dirname(__FILE__) . '/db_connect.php';

// ── Ensure schema ──
$conn->query("CREATE TABLE IF NOT EXISTS lm_multi_dimensional (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    calc_date DATE NOT NULL,
    whale_score INT NOT NULL DEFAULT 50,
    insider_score INT NOT NULL DEFAULT 50,
    analyst_score INT NOT NULL DEFAULT 50,
    crowd_score INT NOT NULL DEFAULT 50,
    fear_greed_score INT NOT NULL DEFAULT 50,
    regime_score INT NOT NULL DEFAULT 50,
    value_score INT NOT NULL DEFAULT 50,
    growth_score INT NOT NULL DEFAULT 50,
    momentum_score INT NOT NULL DEFAULT 50,
    conviction_score INT NOT NULL DEFAULT 50,
    conviction_label VARCHAR(20) NOT NULL DEFAULT 'neutral',
    dimension_detail TEXT,
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker_date (ticker, calc_date),
    KEY idx_ticker (ticker),
    KEY idx_conviction (conviction_score),
    KEY idx_date (calc_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// Add columns that may be missing from older table versions
$_md_chk = $conn->query("SHOW COLUMNS FROM lm_multi_dimensional LIKE 'value_score'");
if ($_md_chk && $_md_chk->num_rows == 0) {
    $conn->query("ALTER TABLE lm_multi_dimensional ADD COLUMN value_score INT NOT NULL DEFAULT 50 AFTER regime_score");
    $conn->query("ALTER TABLE lm_multi_dimensional ADD COLUMN growth_score INT NOT NULL DEFAULT 50 AFTER value_score");
    $conn->query("ALTER TABLE lm_multi_dimensional ADD COLUMN momentum_score INT NOT NULL DEFAULT 50 AFTER growth_score");
}

$action = isset($_GET['action']) ? $_GET['action'] : 'all';
$admin_key = isset($_GET['key']) ? $_GET['key'] : '';

// Ticker universe
$MD_TICKERS = array('AAPL','MSFT','GOOGL','AMZN','NVDA','META','JPM','WMT','XOM','NFLX','JNJ','BAC');

// ─────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────
function _md_esc($conn, $val) {
    return $conn->real_escape_string($val);
}

function _md_clamp($val) {
    return max(0, min(100, round($val)));
}

function _md_table_exists($conn, $table) {
    $safe = $conn->real_escape_string($table);
    $chk = $conn->query("SHOW TABLES LIKE '$safe'");
    return ($chk && $chk->num_rows > 0);
}

// File cache
function _md_cache_get($key, $ttl) {
    $file = dirname(__FILE__) . '/cache/md_' . md5($key) . '.json';
    if (!file_exists($file)) return null;
    if ((time() - filemtime($file)) > $ttl) return null;
    $data = @file_get_contents($file);
    return ($data !== false) ? json_decode($data, true) : null;
}

function _md_cache_set($key, $data) {
    $dir = dirname(__FILE__) . '/cache';
    if (!is_dir($dir)) @mkdir($dir, 0777, true);
    @file_put_contents($dir . '/md_' . md5($key) . '.json', json_encode($data));
}

// ─────────────────────────────────────────
//  Dimension 1: Whale Score (13F Holdings)
// ─────────────────────────────────────────
function _md_calc_whale($conn, $ticker) {
    if (!_md_table_exists($conn, 'gm_sec_13f_holdings')) return array('score' => 50, 'detail' => 'no_data');

    $t = _md_esc($conn, $ticker);

    // Count distinct funds + change types + total value for this ticker
    $r = $conn->query("SELECT COUNT(DISTINCT fund_name) as fund_count,
        SUM(CASE WHEN change_type IN ('new','increased') THEN 1 ELSE 0 END) as bullish,
        SUM(CASE WHEN change_type IN ('decreased','sold_all') THEN 1 ELSE 0 END) as bearish,
        SUM(CASE WHEN change_type = 'new' THEN 1 ELSE 0 END) as new_positions,
        SUM(CASE WHEN change_type = 'sold_all' THEN 1 ELSE 0 END) as exits,
        SUM(value_thousands) * 1000 as total_value
        FROM gm_sec_13f_holdings
        WHERE ticker = '$t'
        AND filing_quarter = (SELECT MAX(filing_quarter) FROM gm_sec_13f_holdings WHERE ticker = '$t')");

    if (!$r || !($row = $r->fetch_assoc())) return array('score' => 50, 'detail' => 'query_failed');

    $funds = intval($row['fund_count']);
    $bull = intval($row['bullish']);
    $bear = intval($row['bearish']);
    $new_pos = intval($row['new_positions']);
    $exits = intval($row['exits']);
    $total_val = floatval($row['total_value']);

    if ($funds === 0) return array('score' => 50, 'detail' => 'no_holdings');

    // Component 1: Fund breadth (0-30 points)
    // More funds = more institutional interest
    if ($funds >= 8) $breadth = 30;
    elseif ($funds >= 5) $breadth = 25;
    elseif ($funds >= 3) $breadth = 20;
    elseif ($funds >= 2) $breadth = 15;
    else $breadth = 10;

    // Component 2: Net momentum (0-40 points)
    $total_changes = $bull + $bear;
    if ($total_changes > 0) {
        $net_ratio = $bull / $total_changes;
        $momentum = round($net_ratio * 40);
    } else {
        $momentum = 20; // No changes = neutral
    }

    // Component 3: New positions vs exits bonus (0-20 points)
    $flow_bonus = 0;
    if ($new_pos > 0 && $exits == 0) $flow_bonus = 20;        // Only new money
    elseif ($new_pos > $exits) $flow_bonus = 15;               // Net new entries
    elseif ($new_pos > 0) $flow_bonus = 10;                    // Some new entries
    elseif ($exits > 0 && $new_pos == 0) $flow_bonus = 0;     // Only exits
    else $flow_bonus = 8;                                       // No new/exit = stable

    // Component 4: Total value bonus (0-10 points)
    $val_bonus = 0;
    if ($total_val > 1000000000) $val_bonus = 10;   // >$1B total holdings
    elseif ($total_val > 500000000) $val_bonus = 7;
    elseif ($total_val > 100000000) $val_bonus = 5;
    elseif ($total_val > 10000000) $val_bonus = 3;

    $score = _md_clamp($breadth + $momentum + $flow_bonus + $val_bonus);

    return array('score' => $score, 'detail' => 'funds=' . $funds . ' bull=' . $bull . ' bear=' . $bear . ' new=' . $new_pos . ' exits=' . $exits . ' val=$' . round($total_val / 1000000) . 'M');
}

// ─────────────────────────────────────────
//  Dimension 2: Insider Score (Form 4 + Finnhub MSPR)
//  V3: Transaction-level scoring with title keywords, amount tiers, cluster detection
//  Blends 75% transaction score + 25% analyst proxy when purchases exist
// ─────────────────────────────────────────
function _md_calc_insider($conn, $ticker) {
    $t = _md_esc($conn, $ticker);
    $detail = '';

    // ── 1. Analyst consensus as insider confidence proxy (fallback) ──
    $analyst_base = -1;
    if (_md_table_exists($conn, 'lm_analyst_ratings')) {
        $r = $conn->query("SELECT strong_buy, buy, hold, sell, strong_sell
            FROM lm_analyst_ratings WHERE ticker = '$t' ORDER BY id DESC LIMIT 1");
        if ($r && $row = $r->fetch_assoc()) {
            $sb = intval($row['strong_buy']);
            $b  = intval($row['buy']);
            $h  = intval($row['hold']);
            $s  = intval($row['sell']);
            $ss = intval($row['strong_sell']);
            $total_a = $sb + $b + $h + $s + $ss;
            if ($total_a > 0) {
                $buy_ratio = ($sb + $b) / $total_a;
                $analyst_base = round(30 + $buy_ratio * 58);
                if ($buy_ratio > 0.7) {
                    $analyst_base = $analyst_base + round(($buy_ratio - 0.7) * 20);
                }
                $detail = 'analyst_proxy br=' . round($buy_ratio, 2);
            }
        }
    }

    // ── 2. Transaction-level scoring (Form 4 purchases, 90 days) ──
    $tx_score = -1;
    $best_tx = 0;
    $cluster_buyers = 0;
    if (_md_table_exists($conn, 'gm_sec_insider_trades')) {
        // Get individual purchase transactions for scoring
        $r2 = $conn->query("SELECT filer_name, is_officer, total_value, transaction_date
            FROM gm_sec_insider_trades
            WHERE ticker = '$t' AND transaction_type = 'P'
            AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)
            ORDER BY total_value DESC LIMIT 20");
        if ($r2) {
            $tx_scores = array();
            while ($row2 = $r2->fetch_assoc()) {
                $val = floatval($row2['total_value']);
                $name = strtolower($row2['filer_name']);
                $is_officer = intval($row2['is_officer']);

                // Base score for a purchase
                $s = 60;

                // Amount tier bonuses
                if ($val >= 10000000) { $s = $s + 35; }       // $10M+ massive conviction
                elseif ($val >= 5000000) { $s = $s + 30; }    // $5M+ very strong
                elseif ($val >= 1000000) { $s = $s + 20; }    // $1M+ strong
                elseif ($val >= 500000) { $s = $s + 12; }     // $500K+ notable
                elseif ($val >= 100000) { $s = $s + 5; }      // $100K+ meaningful

                // Title keyword bonuses from filer_name
                if (strpos($name, 'ceo') !== false || strpos($name, 'chief executive') !== false) {
                    $s = $s + 40;
                } elseif (strpos($name, 'cfo') !== false || strpos($name, 'chief financial') !== false) {
                    $s = $s + 35;
                } elseif (strpos($name, 'coo') !== false || strpos($name, 'chief operating') !== false) {
                    $s = $s + 30;
                } elseif (strpos($name, 'cto') !== false || strpos($name, 'chief tech') !== false) {
                    $s = $s + 28;
                } elseif (strpos($name, 'president') !== false) {
                    $s = $s + 25;
                } elseif (strpos($name, 'director') !== false) {
                    $s = $s + 22;
                } elseif (strpos($name, 'vp') !== false || strpos($name, 'vice president') !== false) {
                    $s = $s + 18;
                } elseif ($is_officer) {
                    $s = $s + 15; // Generic officer bonus
                }

                $tx_scores[] = min(100, $s);
            }

            if (count($tx_scores) > 0) {
                // Best single transaction score (strongest signal)
                $best_tx = $tx_scores[0];
                $tx_score = $best_tx;
                $detail .= ' txn_best=' . $best_tx . ' txn_count=' . count($tx_scores);
            }
        }

        // Cluster detection: distinct buyers in 7-day window
        $r3 = $conn->query("SELECT COUNT(DISTINCT filer_name) as cluster_buyers
            FROM gm_sec_insider_trades
            WHERE ticker = '$t' AND transaction_type = 'P'
            AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)");
        if ($r3 && ($row3 = $r3->fetch_assoc())) {
            $cluster_buyers = intval($row3['cluster_buyers']);
            if ($cluster_buyers >= 3) {
                $cluster_bonus = min(15, ($cluster_buyers - 2) * 5);
                if ($tx_score > 0) $tx_score = min(100, $tx_score + $cluster_bonus);
                $detail .= ' cluster_7d=' . $cluster_buyers . ' +' . $cluster_bonus;
            }
        }

        // Also check aggregate sell pressure for detail
        $r4 = $conn->query("SELECT
            SUM(CASE WHEN transaction_type = 'S' THEN total_value ELSE 0 END) as sell_val
            FROM gm_sec_insider_trades
            WHERE ticker = '$t'
            AND transaction_date >= DATE_SUB(CURDATE(), INTERVAL 90 DAY)");
        if ($r4 && ($row4 = $r4->fetch_assoc())) {
            $sell = floatval($row4['sell_val']);
            if ($sell > 50000000) {
                $detail .= ' sell_pressure=' . round($sell / 1000000) . 'M';
            }
        }
    }

    // ── 3. MSPR bonus ──
    $mspr_adj = 0;
    if (_md_table_exists($conn, 'lm_insider_sentiment')) {
        $r5 = $conn->query("SELECT mspr FROM lm_insider_sentiment
            WHERE ticker = '$t' ORDER BY year_month DESC LIMIT 1");
        if ($r5 && $row5 = $r5->fetch_assoc()) {
            $mspr = floatval($row5['mspr']);
            if ($mspr > 5) { $mspr_adj = 8; $detail .= ' mspr=+' . round($mspr, 1); }
            elseif ($mspr > 0) { $mspr_adj = 4; $detail .= ' mspr=+' . round($mspr, 1); }
        }
    }

    // ── 4. Final score: blend transaction + analyst ──
    if ($tx_score > 0 && $analyst_base >= 0) {
        // Purchases exist AND analyst data: 75% transaction, 25% analyst
        $score = round($tx_score * 0.75 + $analyst_base * 0.25) + $mspr_adj;
        $detail = 'blend_75tx_25an ' . $detail;
    } elseif ($tx_score > 0) {
        // Purchases exist, no analyst: transaction score only
        $score = $tx_score + $mspr_adj;
        $detail = 'tx_only ' . $detail;
    } elseif ($analyst_base >= 0) {
        // No purchases, analyst proxy as fallback (mega-cap routine)
        $score = $analyst_base + $mspr_adj;
        $detail = 'analyst_fallback ' . $detail;
    } else {
        $score = 50;
        $detail = 'no_data';
    }

    return array('score' => _md_clamp($score), 'detail' => $detail);
}

// ─────────────────────────────────────────
//  Dimension 3: Analyst Score
// ─────────────────────────────────────────
function _md_calc_analyst($conn, $ticker) {
    $t = _md_esc($conn, $ticker);
    $score = 50;
    $detail = 'no_data';

    // Try lm_analyst_ratings (from smart_money.php)
    if (_md_table_exists($conn, 'lm_analyst_ratings')) {
        $r = $conn->query("SELECT strong_buy, buy, hold, sell, strong_sell FROM lm_analyst_ratings WHERE ticker = '$t' ORDER BY id DESC LIMIT 1");
        if ($r && $row = $r->fetch_assoc()) {
            $sb = intval($row['strong_buy']);
            $b = intval($row['buy']);
            $h = intval($row['hold']);
            $s = intval($row['sell']);
            $ss = intval($row['strong_sell']);
            $total = $sb + $b + $h + $s + $ss;

            if ($total > 0) {
                // Weighted: strong_buy=2, buy=1, hold=0, sell=-1, strong_sell=-2
                $weighted = ($sb * 2 + $b * 1 + $h * 0 - $s * 1 - $ss * 2);
                $max = $total * 2;
                // Map from [-max, +max] to [0, 100]
                $base = round(($weighted + $max) / (2 * $max) * 80);
                $detail = 'sb=' . $sb . ' b=' . $b . ' h=' . $h . ' s=' . $s . ' ss=' . $ss;
                $score = $base;
            }
        }
    }

    // Add price target upside component
    if (_md_table_exists($conn, 'lm_price_targets') && _md_table_exists($conn, 'lm_price_cache')) {
        $r2 = $conn->query("SELECT pt.target_mean, pc.price
            FROM lm_price_targets pt
            JOIN lm_price_cache pc ON pc.symbol = pt.ticker
            WHERE pt.ticker = '$t'
            ORDER BY pt.id DESC LIMIT 1");
        if ($r2 && $row2 = $r2->fetch_assoc()) {
            $target = floatval($row2['target_mean']);
            $current = floatval($row2['price']);
            if ($current > 0 && $target > 0) {
                $upside = ($target - $current) / $current * 100;
                // +20% upside → +20 points, -10% → -10 points
                $upside_bonus = max(-15, min(20, round($upside)));
                $score = $score + $upside_bonus;
                $detail .= ' upside=' . round($upside, 1) . '%';
            }
        }
    }

    return array('score' => _md_clamp($score), 'detail' => $detail);
}

// ─────────────────────────────────────────
//  Dimension 4: Crowd Score (Sentiment + WSB)
// ─────────────────────────────────────────
function _md_calc_crowd($conn, $ticker) {
    $t = _md_esc($conn, $ticker);
    $news_component = 50;
    $wsb_component = 50;
    $detail_parts = array();

    // News sentiment (50% weight within crowd)
    if (_md_table_exists($conn, 'gm_news_sentiment')) {
        $r = $conn->query("SELECT sentiment_score, buzz_score, relative_sentiment FROM gm_news_sentiment WHERE ticker = '$t' ORDER BY fetch_date DESC LIMIT 1");
        if ($r && $row = $r->fetch_assoc()) {
            $sent = floatval($row['sentiment_score']); // -1 to +1
            $buzz = floatval($row['buzz_score']);
            $relative = floatval($row['relative_sentiment']);
            // Map sentiment -1..+1 to 0..100
            $news_component = round(($sent + 1) * 50);
            // Buzz amplifier: high buzz amplifies the signal
            if ($buzz > 2) $news_component = round($news_component * 1.1);
            // Relative sentiment bonus
            if ($relative > 0.1) $news_component += 5;
            if ($relative < -0.1) $news_component -= 5;
            $detail_parts[] = 'sent=' . round($sent, 2) . ' buzz=' . round($buzz, 1);
        }
    }

    // WSB mentions (30% weight within crowd)
    if (_md_table_exists($conn, 'lm_wsb_sentiment')) {
        $r2 = $conn->query("SELECT mentions_24h, sentiment, wsb_score FROM lm_wsb_sentiment WHERE ticker = '$t' ORDER BY id DESC LIMIT 1");
        if ($r2 && $row2 = $r2->fetch_assoc()) {
            $mentions = intval($row2['mentions_24h']);
            $wsb_sent = floatval($row2['sentiment']);
            $wsb_sc = floatval($row2['wsb_score']);
            // Map WSB sentiment to 0-100
            $wsb_component = round(($wsb_sent + 1) * 50);
            // High mentions = more weight
            if ($mentions > 50) $wsb_component = round($wsb_component * 1.1);
            $detail_parts[] = 'wsb_mentions=' . $mentions;
        }
    }

    // Blend: 60% news + 40% WSB
    $score = _md_clamp(round($news_component * 0.6 + $wsb_component * 0.4));

    return array('score' => $score, 'detail' => implode(' ', $detail_parts));
}

// ─────────────────────────────────────────
//  Dimension 5: Fear/Greed Score (inverted for conviction)
//  V2: Now ticker-specific! Blends market F&G with ticker momentum + sentiment
// ─────────────────────────────────────────
function _md_calc_fear_greed($conn, $ticker) {
    $t = _md_esc($conn, $ticker);
    $market_fg = 50;
    $detail = 'no_data';
    $found = false;

    // ── Market-wide F&G (same 4 layers as before) ──

    // Layer 1: Composite from lm_fear_greed
    if (!$found && _md_table_exists($conn, 'lm_fear_greed')) {
        $r = $conn->query("SELECT score, classification, fetch_date FROM lm_fear_greed WHERE source = 'composite' ORDER BY fetch_date DESC LIMIT 1");
        if ($r && ($row = $r->fetch_assoc())) {
            $raw = intval($row['score']);
            if ($raw > 0 && $raw != 50) {
                $market_fg = 100 - $raw;
                $detail = 'composite=' . $raw . ' (inv)';
                $found = true;
            }
        }
    }

    // Layer 2: VIX from market_regimes
    if (!$found && _md_table_exists($conn, 'market_regimes')) {
        $r = $conn->query("SELECT vix_close, regime FROM market_regimes ORDER BY trade_date DESC LIMIT 1");
        if ($r && ($row = $r->fetch_assoc())) {
            $vix = floatval($row['vix_close']);
            if ($vix > 0) {
                $market_fg = _md_vix_to_fg($vix);
                $detail = 'vix=' . $vix;
                $found = true;
            }
        }
    }

    // Layer 3: Real-time VIX from Yahoo
    if (!$found) {
        $vix = _md_fetch_vix_realtime();
        if ($vix > 0) {
            $market_fg = _md_vix_to_fg($vix);
            $detail = 'vix=' . $vix . ' (live)';
            $found = true;
        }
    }

    // Layer 4: Crypto Fear & Greed
    if (!$found) {
        $cached = _md_cache_get('crypto_fg', 7200);
        if ($cached !== null && isset($cached['score'])) {
            $market_fg = 100 - intval($cached['score']);
            $detail = 'crypto_fg=' . $cached['score'];
            $found = true;
        } else {
            $raw = @file_get_contents('https://api.alternative.me/fng/?limit=1&format=json');
            if ($raw !== false) {
                $json = json_decode($raw, true);
                if (isset($json['data'][0]['value'])) {
                    $crypto_raw = intval($json['data'][0]['value']);
                    $market_fg = 100 - $crypto_raw;
                    $detail = 'crypto_fg=' . $crypto_raw . ' (live)';
                    _md_cache_set('crypto_fg', array('score' => $crypto_raw));
                    $found = true;
                }
            }
        }
    }

    // ── Ticker-specific adjustments (±25 points max) ──
    $ticker_adj = 0;

    // Ticker momentum + RSI proxy from day range position
    if (_md_table_exists($conn, 'lm_price_cache')) {
        $r = $conn->query("SELECT change_24h_pct, price, day_high, day_low FROM lm_price_cache WHERE symbol = '$t' LIMIT 1");
        if ($r && ($row = $r->fetch_assoc())) {
            $change = floatval($row['change_24h_pct']);
            $price = floatval($row['price']);
            $high = floatval($row['day_high']);
            $low = floatval($row['day_low']);

            // Momentum: ±3 points per 1% daily move (max ±12)
            $mom_adj = max(-12, min(12, round($change * 3)));
            $ticker_adj = $ticker_adj + $mom_adj;
            $detail .= ' mom=' . round($change, 2) . '%';

            // Day range as RSI proxy (inverted for contrarian F&G)
            // Near day high = overbought = more greed = lower contrarian score
            // Near day low = oversold = more fear = higher contrarian score
            if ($high > $low && $high > 0) {
                $range_pos = ($price - $low) / ($high - $low); // 0=at low, 1=at high
                // Invert: at high (1.0) → -8, at low (0.0) → +8
                $rsi_adj = round((0.5 - $range_pos) * 16);
                $rsi_adj = max(-8, min(8, $rsi_adj));
                $ticker_adj = $ticker_adj + $rsi_adj;
                $detail .= ' rsi_proxy=' . round($range_pos, 2) . ' adj=' . $rsi_adj;
            }
        }
    }

    // Ticker news sentiment: ±8 points for strong sentiment
    if (_md_table_exists($conn, 'gm_news_sentiment')) {
        $r = $conn->query("SELECT sentiment_score FROM gm_news_sentiment WHERE ticker = '$t' ORDER BY fetch_date DESC LIMIT 1");
        if ($r && ($row = $r->fetch_assoc())) {
            $sent = floatval($row['sentiment_score']); // -1 to +1
            $sent_adj = round($sent * 8);
            $ticker_adj = $ticker_adj + $sent_adj;
            $detail .= ' sent=' . round($sent, 2);
        }
    }

    // Clamp total ticker adjustment to ±25 (expanded from ±15)
    $ticker_adj = max(-25, min(25, $ticker_adj));
    $fg_score = _md_clamp($market_fg + $ticker_adj);

    if ($ticker_adj != 0) {
        $detail .= ' adj=' . $ticker_adj;
    }

    return array('score' => $fg_score, 'detail' => $detail);
}

// Helper: Convert VIX value to inverted Fear/Greed score
// Low VIX (calm) = low fear = low conviction score (greed = contrarian bearish)
// High VIX (panic) = high fear = high conviction score (fear = contrarian bullish)
function _md_vix_to_fg($vix) {
    // VIX 10 = extreme greed -> inverted score 15 (low conviction)
    // VIX 15 = greed -> inverted score 30
    // VIX 20 = neutral -> inverted score 50
    // VIX 25 = fear -> inverted score 70
    // VIX 30 = high fear -> inverted score 82
    // VIX 40+ = extreme fear -> inverted score 95 (high conviction)
    if ($vix <= 10) return 15;
    if ($vix <= 15) return _md_clamp(round(15 + ($vix - 10) * 3));    // 15-30
    if ($vix <= 20) return _md_clamp(round(30 + ($vix - 15) * 4));    // 30-50
    if ($vix <= 25) return _md_clamp(round(50 + ($vix - 20) * 4));    // 50-70
    if ($vix <= 30) return _md_clamp(round(70 + ($vix - 25) * 2.4));  // 70-82
    if ($vix <= 40) return _md_clamp(round(82 + ($vix - 30) * 1.3));  // 82-95
    return 95;
}

// Helper: Fetch VIX in real-time from Yahoo Finance
function _md_fetch_vix_realtime() {
    $cached = _md_cache_get('vix_realtime', 1800); // 30 min cache
    if ($cached !== null && isset($cached['vix'])) return floatval($cached['vix']);

    $url = 'https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?interval=1d&range=1d';
    $ctx = stream_context_create(array('http' => array(
        'timeout' => 10,
        'header' => "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
    )));
    $raw = @file_get_contents($url, false, $ctx);
    if ($raw === false) {
        // Try curl fallback
        if (function_exists('curl_init')) {
            $ch = curl_init();
            curl_setopt($ch, CURLOPT_URL, $url);
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 10);
            curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
            curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36');
            $raw = curl_exec($ch);
            curl_close($ch);
        }
    }
    if ($raw === false || $raw === null) return 0;

    $data = json_decode($raw, true);
    if (isset($data['chart']['result'][0]['meta']['regularMarketPrice'])) {
        $vix = floatval($data['chart']['result'][0]['meta']['regularMarketPrice']);
        _md_cache_set('vix_realtime', array('vix' => $vix));
        return $vix;
    }
    return 0;
}

// ─────────────────────────────────────────
//  Dimension 6: Regime Score
// ─────────────────────────────────────────
function _md_calc_regime($conn, $ticker) {
    $t = _md_esc($conn, $ticker);
    $regime_base = 50;
    $momentum_component = 50;
    $detail = 'no_data';

    // Regime classification
    if (_md_table_exists($conn, 'market_regimes')) {
        $r = $conn->query("SELECT regime, vix_close FROM market_regimes ORDER BY trade_date DESC LIMIT 1");
        if ($r && $row = $r->fetch_assoc()) {
            $regime_map = array(
                'calm_bull' => 80, 'moderate_bull' => 65,
                'moderate_bear' => 35, 'calm_bear' => 45,
                'high_vol' => 25, 'extreme_vol' => 15
            );
            $regime = $row['regime'];
            $regime_base = isset($regime_map[$regime]) ? $regime_map[$regime] : 50;
            $detail = 'regime=' . $regime;
        }
    }

    // Ticker-specific momentum from price cache
    if (_md_table_exists($conn, 'lm_price_cache')) {
        $r2 = $conn->query("SELECT change_24h_pct FROM lm_price_cache WHERE symbol = '$t' LIMIT 1");
        if ($r2 && $row2 = $r2->fetch_assoc()) {
            $change = floatval($row2['change_24h_pct']);
            // Map -10%..+10% to 0..100
            $momentum_component = _md_clamp(round(50 + $change * 5));
            $detail .= ' change_24h=' . round($change, 2) . '%';
        }
    }

    // Blend: 60% regime + 40% ticker momentum
    $score = _md_clamp(round($regime_base * 0.6 + $momentum_component * 0.4));

    return array('score' => $score, 'detail' => $detail);
}

// ─────────────────────────────────────────
//  Dimension 7: Value Score
//  V2: Continuous upside mapping + analyst consensus blend
// ─────────────────────────────────────────
function _md_calc_value($conn, $ticker) {
    $t = _md_esc($conn, $ticker);
    $score = -1;
    $detail = 'no_data';

    // Try lm_free_data_scores first
    if (_md_table_exists($conn, 'lm_free_data_scores')) {
        $r = $conn->query("SELECT value_score FROM lm_free_data_scores WHERE ticker = '$t' ORDER BY calc_date DESC LIMIT 1");
        if ($r && ($row = $r->fetch_assoc())) {
            $score = intval($row['value_score']);
            $detail = 'free_data';
        }
    }

    // Fallback: continuous mapping from price target upside
    if ($score < 0 && _md_table_exists($conn, 'lm_price_targets') && _md_table_exists($conn, 'lm_price_cache')) {
        $r2 = $conn->query("SELECT pt.target_mean, pt.target_high, pt.num_analysts, pc.price
            FROM lm_price_targets pt
            JOIN lm_price_cache pc ON pc.symbol = pt.ticker
            WHERE pt.ticker = '$t'
            ORDER BY pt.id DESC LIMIT 1");
        if ($r2 && ($row2 = $r2->fetch_assoc())) {
            $target = floatval($row2['target_mean']);
            $high = floatval($row2['target_high']);
            $price = floatval($row2['price']);
            $analysts = intval($row2['num_analysts']);
            if ($price > 0 && $target > 0) {
                $upside = ($target - $price) / $price * 100;
                // Continuous: map -30%..+50% to 26..90
                // 0% upside = 50, 10% = 58, 20% = 66, 30% = 74, 40% = 82
                $score = _md_clamp(round(50 + $upside * 0.8));
                // Analyst count bonus (small)
                if ($analysts >= 25) $score = _md_clamp($score + 3);
                elseif ($analysts >= 15) $score = _md_clamp($score + 2);
                $detail = 'upside=' . round($upside, 1) . '% analysts=' . $analysts;
            }
        }
    }

    if ($score < 0) $score = 50;
    return array('score' => _md_clamp($score), 'detail' => $detail);
}

// ─────────────────────────────────────────
//  Dimension 8: Growth Score
//  V2: Earnings beat + analyst consensus + revenue growth proxy
// ─────────────────────────────────────────
function _md_calc_growth($conn, $ticker) {
    $t = _md_esc($conn, $ticker);
    $score = -1;
    $detail = 'no_data';

    // Try lm_free_data_scores first
    if (_md_table_exists($conn, 'lm_free_data_scores')) {
        $r = $conn->query("SELECT growth_score FROM lm_free_data_scores WHERE ticker = '$t' ORDER BY calc_date DESC LIMIT 1");
        if ($r && ($row = $r->fetch_assoc())) {
            $score = intval($row['growth_score']);
            $detail = 'free_data';
        }
    }

    // Fallback 1: earnings beat rate + surprise magnitude
    if ($score < 0 && _md_table_exists($conn, 'stock_earnings')) {
        $r2 = $conn->query("SELECT
            COUNT(*) as total,
            SUM(CASE WHEN eps_actual > eps_estimate THEN 1 ELSE 0 END) as beats,
            AVG(CASE WHEN eps_estimate > 0 THEN (eps_actual - eps_estimate) / eps_estimate * 100 ELSE 0 END) as avg_surprise
            FROM stock_earnings WHERE ticker = '$t'");
        if ($r2 && ($row2 = $r2->fetch_assoc())) {
            $total = intval($row2['total']);
            $beats = intval($row2['beats']);
            $surprise = floatval($row2['avg_surprise']);
            if ($total >= 2) {
                $beat_rate = $beats / $total;
                // Base from beat rate: 100%=82, 75%=68, 50%=55, 25%=42
                $base = round(28 + $beat_rate * 54);
                // Surprise bonus: avg +10% surprise = +8 points
                $surp_bonus = _md_clamp(round($surprise * 0.8));
                $surp_bonus = max(-10, min(12, $surp_bonus));
                $score = _md_clamp($base + $surp_bonus);
                $detail = 'beat=' . round($beat_rate * 100) . '% surp=' . round($surprise, 1) . '% n=' . $total;
            }
        }
    }

    // Fallback 2: analyst consensus as growth proxy
    if ($score < 0 && _md_table_exists($conn, 'lm_analyst_ratings')) {
        $r3 = $conn->query("SELECT strong_buy, buy, hold, sell, strong_sell FROM lm_analyst_ratings WHERE ticker = '$t' ORDER BY id DESC LIMIT 1");
        if ($r3 && ($row3 = $r3->fetch_assoc())) {
            $sb = intval($row3['strong_buy']);
            $b = intval($row3['buy']);
            $tot = $sb + $b + intval($row3['hold']) + intval($row3['sell']) + intval($row3['strong_sell']);
            if ($tot > 0) {
                // % of buy/strong_buy as growth proxy
                $buy_pct = ($sb + $b) / $tot;
                $score = _md_clamp(round(30 + $buy_pct * 55));
                $detail = 'analyst_buy_pct=' . round($buy_pct * 100) . '%';
            }
        }
    }

    if ($score < 0) $score = 50;
    return array('score' => _md_clamp($score), 'detail' => $detail);
}

// ─────────────────────────────────────────
//  Dimension 9: Momentum Score
//  V2: Price change + price vs target + WSB buzz
// ─────────────────────────────────────────
function _md_calc_momentum($conn, $ticker) {
    $t = _md_esc($conn, $ticker);
    $score = -1;
    $detail = 'no_data';

    // Try lm_free_data_scores first
    if (_md_table_exists($conn, 'lm_free_data_scores')) {
        $r = $conn->query("SELECT momentum_score FROM lm_free_data_scores WHERE ticker = '$t' ORDER BY calc_date DESC LIMIT 1");
        if ($r && ($row = $r->fetch_assoc())) {
            $score = intval($row['momentum_score']);
            $detail = 'free_data';
        }
    }

    // Fallback: derive from price data + volume confirmation
    if ($score < 0 && _md_table_exists($conn, 'lm_price_cache')) {
        $r2 = $conn->query("SELECT change_24h_pct, price, prev_close, day_high, day_low, volume FROM lm_price_cache WHERE symbol = '$t' LIMIT 1");
        if ($r2 && ($row2 = $r2->fetch_assoc())) {
            $change = floatval($row2['change_24h_pct']);
            $price = floatval($row2['price']);
            $high = floatval($row2['day_high']);
            $low = floatval($row2['day_low']);
            $volume = floatval($row2['volume']);

            // Base: map -5%..+5% to 25..75 (wider spread)
            $base = _md_clamp(round(50 + $change * 5));

            // Day range position: granular bonus (wider spread ±12)
            $range_bonus = 0;
            if ($high > $low && $high > 0) {
                $range_pos = ($price - $low) / ($high - $low);
                if ($range_pos > 0.8) { $range_bonus = 12; }
                elseif ($range_pos > 0.65) { $range_bonus = 8; }
                elseif ($range_pos > 0.5) { $range_bonus = 4; }
                elseif ($range_pos < 0.2) { $range_bonus = -10; }
                elseif ($range_pos < 0.35) { $range_bonus = -6; }
                elseif ($range_pos < 0.5) { $range_bonus = -3; }
                $detail = 'rng_pos=' . round($range_pos, 2);
            }

            // Volume confirmation: high volume amplifies momentum signal
            $vol_bonus = 0;
            if ($volume > 0) {
                // Very high volume (>50M shares) = strong conviction in the move
                if ($volume > 50000000) {
                    $vol_bonus = ($change > 0) ? 5 : -5;
                } elseif ($volume > 20000000) {
                    $vol_bonus = ($change > 0) ? 3 : -3;
                }
                if ($vol_bonus != 0) $detail .= ' vol=' . round($volume / 1000000) . 'M';
            }

            $score = _md_clamp($base + $range_bonus + $vol_bonus);
            $detail = 'chg=' . round($change, 2) . '% rng=' . $range_bonus . ' vol_b=' . $vol_bonus . ' ' . $detail;
        }
    }

    // WSB buzz amplifier: high mentions + positive sentiment = momentum boost
    if ($score > 0 && _md_table_exists($conn, 'lm_wsb_sentiment')) {
        $r3 = $conn->query("SELECT mentions_24h, sentiment FROM lm_wsb_sentiment WHERE ticker = '$t' ORDER BY id DESC LIMIT 1");
        if ($r3 && ($row3 = $r3->fetch_assoc())) {
            $mentions = intval($row3['mentions_24h']);
            $wsb_sent = floatval($row3['sentiment']);
            if ($mentions > 5) {
                $buzz_adj = round($wsb_sent * min(8, $mentions));
                $buzz_adj = max(-8, min(8, $buzz_adj));
                $score = _md_clamp($score + $buzz_adj);
                $detail .= ' wsb_buzz=' . $mentions . 's=' . round($wsb_sent, 2);
            }
        }
    }

    if ($score < 0) $score = 50;
    return array('score' => _md_clamp($score), 'detail' => $detail);
}

// ─────────────────────────────────────────
//  Conviction Score (weighted average + regime multiplier + quality penalty)
//  V3: Regime removed from weighted sum, applied as 1.05x/0.95x multiplier
//  Insider weight 14%→18%, Analyst 18%→14% (insider is stronger signal)
//  Quality penalty: 0.9x for sparse data (<4 non-default dimensions)
// ─────────────────────────────────────────
function _md_calc_conviction($whale, $insider, $analyst, $crowd, $fg, $regime, $value, $growth, $momentum) {
    // 8 dimensions (regime excluded from weighted sum — used as multiplier)
    // Weights sum to 1.0 without regime
    $score = round(
        $whale * 0.18 +
        $insider * 0.18 +
        $analyst * 0.14 +
        $crowd * 0.12 +
        $fg * 0.12 +
        $value * 0.09 +
        $growth * 0.09 +
        $momentum * 0.08
    );

    // Regime as multiplier instead of weighted dimension
    // Bull regime boosts conviction, bear regime dampens it
    if ($regime >= 65) {
        $score = round($score * 1.05); // Bull regime: +5%
    } elseif ($regime <= 35) {
        $score = round($score * 0.95); // Bear regime: -5%
    }
    // Neutral regime (36-64): no adjustment

    // Quality penalty: penalize if too many dimensions are default (50)
    $dimensions = array($whale, $insider, $analyst, $crowd, $fg, $value, $growth, $momentum);
    $non_default = 0;
    foreach ($dimensions as $d) {
        if ($d != 50) $non_default = $non_default + 1;
    }
    if ($non_default < 4) {
        $score = round($score * 0.90); // 10% penalty for sparse data
    }

    $score = _md_clamp($score);

    $label = 'neutral';
    if ($score >= 70) $label = 'strong_bullish';
    elseif ($score >= 55) $label = 'bullish';
    elseif ($score <= 25) $label = 'strong_bearish';
    elseif ($score <= 40) $label = 'bearish';

    return array('score' => $score, 'label' => $label);
}

// ─────────────────────────────────────────
//  Calculate all dimensions for a ticker
// ─────────────────────────────────────────
function _md_calculate_ticker($conn, $ticker) {
    $whale = _md_calc_whale($conn, $ticker);
    $insider = _md_calc_insider($conn, $ticker);
    $analyst = _md_calc_analyst($conn, $ticker);
    $crowd = _md_calc_crowd($conn, $ticker);
    $fg = _md_calc_fear_greed($conn, $ticker);
    $regime = _md_calc_regime($conn, $ticker);
    $value = _md_calc_value($conn, $ticker);
    $growth = _md_calc_growth($conn, $ticker);
    $momentum = _md_calc_momentum($conn, $ticker);

    $conviction = _md_calc_conviction(
        $whale['score'], $insider['score'], $analyst['score'],
        $crowd['score'], $fg['score'], $regime['score'],
        $value['score'], $growth['score'], $momentum['score']
    );

    return array(
        'ticker' => $ticker,
        'whale_score' => $whale['score'],
        'insider_score' => $insider['score'],
        'analyst_score' => $analyst['score'],
        'crowd_score' => $crowd['score'],
        'fear_greed_score' => $fg['score'],
        'regime_score' => $regime['score'],
        'value_score' => $value['score'],
        'growth_score' => $growth['score'],
        'momentum_score' => $momentum['score'],
        'conviction_score' => $conviction['score'],
        'conviction_label' => $conviction['label'],
        'dimensions' => array(
            'whale' => $whale,
            'insider' => $insider,
            'analyst' => $analyst,
            'crowd' => $crowd,
            'fear_greed' => $fg,
            'regime' => $regime,
            'value' => $value,
            'growth' => $growth,
            'momentum' => $momentum
        )
    );
}

// ─────────────────────────────────────────
//  Store calculated scores in DB
// ─────────────────────────────────────────
function _md_store($conn, $data) {
    $t = _md_esc($conn, $data['ticker']);
    $today = date('Y-m-d');
    $now = gmdate('Y-m-d H:i:s');
    $detail = _md_esc($conn, json_encode($data['dimensions']));
    $label = _md_esc($conn, $data['conviction_label']);

    $conn->query("DELETE FROM lm_multi_dimensional WHERE ticker = '$t' AND calc_date = '$today'");
    $conn->query("INSERT INTO lm_multi_dimensional
        (ticker, calc_date, whale_score, insider_score, analyst_score, crowd_score,
         fear_greed_score, regime_score, value_score, growth_score, momentum_score,
         conviction_score, conviction_label, dimension_detail, created_at)
        VALUES ('$t', '$today', " . $data['whale_score'] . ", " . $data['insider_score'] . ",
        " . $data['analyst_score'] . ", " . $data['crowd_score'] . ", " . $data['fear_greed_score'] . ",
        " . $data['regime_score'] . ", " . $data['value_score'] . ", " . $data['growth_score'] . ",
        " . $data['momentum_score'] . ", " . $data['conviction_score'] . ", '$label', '$detail', '$now')");
}

// ═══════════════════════════════════════════
//  Action: calculate (admin) — recalculate all tickers
// ═══════════════════════════════════════════
if ($action === 'calculate') {
    if ($admin_key !== 'livetrader2026') {
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        $conn->close();
        exit;
    }

    $scored = array();
    foreach ($MD_TICKERS as $ticker) {
        $data = _md_calculate_ticker($conn, $ticker);
        _md_store($conn, $data);
        $scored[] = array('ticker' => $ticker, 'conviction_score' => $data['conviction_score'], 'conviction_label' => $data['conviction_label']);
    }

    // Sort by conviction descending for top_picks
    usort($scored, create_function('$a,$b', 'return $b["conviction_score"] - $a["conviction_score"];'));

    echo json_encode(array(
        'ok' => true,
        'action' => 'calculate',
        'tickers_scored' => count($scored),
        'top_picks' => array_slice($scored, 0, 5),
        'timestamp' => gmdate('Y-m-d H:i:s')
    ));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: ticker — per-stock 6D scores
// ═══════════════════════════════════════════
if ($action === 'ticker') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    if ($ticker === '') {
        echo json_encode(array('ok' => false, 'error' => 'Missing ticker parameter'));
        $conn->close();
        exit;
    }

    // Try cache from DB first
    $t = _md_esc($conn, $ticker);
    $r = $conn->query("SELECT * FROM lm_multi_dimensional WHERE ticker = '$t' AND calc_date >= DATE_SUB(CURDATE(), INTERVAL 1 DAY) ORDER BY calc_date DESC LIMIT 1");
    if ($r && $row = $r->fetch_assoc()) {
        $detail = json_decode($row['dimension_detail'], true);
        echo json_encode(array(
            'ok' => true,
            'action' => 'ticker',
            'data' => array(
                'ticker' => $row['ticker'],
                'whale_score' => intval($row['whale_score']),
                'insider_score' => intval($row['insider_score']),
                'analyst_score' => intval($row['analyst_score']),
                'crowd_score' => intval($row['crowd_score']),
                'fear_greed_score' => intval($row['fear_greed_score']),
                'regime_score' => intval($row['regime_score']),
                'conviction_score' => intval($row['conviction_score']),
                'conviction_label' => $row['conviction_label'],
                'dimensions' => $detail,
                'calc_date' => $row['calc_date']
            )
        ));
    } else {
        // Calculate live
        $data = _md_calculate_ticker($conn, $ticker);
        echo json_encode(array('ok' => true, 'action' => 'ticker', 'data' => $data, 'source' => 'live_calculated'));
    }
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: radar — chart-ready data for radar chart
// ═══════════════════════════════════════════
if ($action === 'radar') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    if ($ticker === '') {
        echo json_encode(array('ok' => false, 'error' => 'Missing ticker parameter'));
        $conn->close();
        exit;
    }

    $t = _md_esc($conn, $ticker);
    $r = $conn->query("SELECT * FROM lm_multi_dimensional WHERE ticker = '$t' ORDER BY calc_date DESC LIMIT 1");

    if ($r && $row = $r->fetch_assoc()) {
        echo json_encode(array(
            'ok' => true,
            'action' => 'radar',
            'ticker' => $ticker,
            'labels' => array('Whale (13F)', 'Insider (Form 4)', 'Analyst', 'Crowd', 'Fear/Greed', 'Regime'),
            'scores' => array(
                intval($row['whale_score']),
                intval($row['insider_score']),
                intval($row['analyst_score']),
                intval($row['crowd_score']),
                intval($row['fear_greed_score']),
                intval($row['regime_score'])
            ),
            'conviction' => intval($row['conviction_score']),
            'conviction_label' => $row['conviction_label'],
            'calc_date' => $row['calc_date']
        ));
    } else {
        // Calculate live
        $data = _md_calculate_ticker($conn, $ticker);
        echo json_encode(array(
            'ok' => true,
            'action' => 'radar',
            'ticker' => $ticker,
            'labels' => array('Whale (13F)', 'Insider (Form 4)', 'Analyst', 'Crowd', 'Fear/Greed', 'Regime'),
            'scores' => array($data['whale_score'], $data['insider_score'], $data['analyst_score'], $data['crowd_score'], $data['fear_greed_score'], $data['regime_score']),
            'conviction' => $data['conviction_score'],
            'conviction_label' => $data['conviction_label'],
            'source' => 'live_calculated'
        ));
    }
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: market — market-wide overview
// ═══════════════════════════════════════════
if ($action === 'market') {
    // Fear/Greed
    $fg_data = array('score' => 50, 'classification' => 'neutral');
    if (_md_table_exists($conn, 'lm_fear_greed')) {
        $r = $conn->query("SELECT score, classification FROM lm_fear_greed WHERE source = 'composite' ORDER BY fetch_date DESC LIMIT 1");
        if ($r && $row = $r->fetch_assoc()) {
            $fg_data = array('score' => intval($row['score']), 'classification' => $row['classification']);
        }
    }

    // Regime
    $regime_data = array('regime' => 'unknown', 'vix' => 0);
    if (_md_table_exists($conn, 'market_regimes')) {
        $r = $conn->query("SELECT regime, vix_close FROM market_regimes ORDER BY trade_date DESC LIMIT 1");
        if ($r && $row = $r->fetch_assoc()) {
            $regime_data = array('regime' => $row['regime'], 'vix' => floatval($row['vix_close']));
        }
    }

    // Average conviction across all tickers
    $r = $conn->query("SELECT AVG(conviction_score) as avg_conviction,
        AVG(whale_score) as avg_whale, AVG(insider_score) as avg_insider,
        AVG(analyst_score) as avg_analyst, AVG(crowd_score) as avg_crowd,
        AVG(fear_greed_score) as avg_fg, AVG(regime_score) as avg_regime,
        MAX(conviction_score) as max_conviction, COUNT(*) as ticker_count
        FROM lm_multi_dimensional
        WHERE calc_date = (SELECT MAX(calc_date) FROM lm_multi_dimensional)");

    $avg = array('avg_conviction' => 50, 'ticker_count' => 0);
    if ($r && $row = $r->fetch_assoc()) {
        $avg = array(
            'avg_conviction' => round(floatval($row['avg_conviction'])),
            'avg_whale' => round(floatval($row['avg_whale'])),
            'avg_insider' => round(floatval($row['avg_insider'])),
            'avg_analyst' => round(floatval($row['avg_analyst'])),
            'avg_crowd' => round(floatval($row['avg_crowd'])),
            'avg_fear_greed' => round(floatval($row['avg_fg'])),
            'avg_regime' => round(floatval($row['avg_regime'])),
            'max_conviction' => round(floatval($row['max_conviction'])),
            'ticker_count' => intval($row['ticker_count'])
        );
    }

    // Top conviction stock
    $top_ticker = '';
    $r2 = $conn->query("SELECT ticker, conviction_score FROM lm_multi_dimensional WHERE calc_date = (SELECT MAX(calc_date) FROM lm_multi_dimensional) ORDER BY conviction_score DESC LIMIT 1");
    if ($r2 && $row2 = $r2->fetch_assoc()) {
        $top_ticker = $row2['ticker'];
    }

    echo json_encode(array(
        'ok' => true,
        'action' => 'market',
        'fear_greed' => $fg_data,
        'regime' => $regime_data,
        'averages' => $avg,
        'top_conviction_ticker' => $top_ticker,
        'timestamp' => gmdate('Y-m-d H:i:s')
    ));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: top_picks — top 10 by conviction
// ═══════════════════════════════════════════
if ($action === 'top_picks') {
    $r = $conn->query("SELECT * FROM lm_multi_dimensional
        WHERE calc_date = (SELECT MAX(calc_date) FROM lm_multi_dimensional)
        ORDER BY conviction_score DESC LIMIT 10");

    $picks = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $picks[] = array(
                'ticker' => $row['ticker'],
                'whale_score' => intval($row['whale_score']),
                'insider_score' => intval($row['insider_score']),
                'analyst_score' => intval($row['analyst_score']),
                'crowd_score' => intval($row['crowd_score']),
                'fear_greed_score' => intval($row['fear_greed_score']),
                'regime_score' => intval($row['regime_score']),
                'conviction_score' => intval($row['conviction_score']),
                'conviction_label' => $row['conviction_label']
            );
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'top_picks', 'count' => count($picks), 'picks' => $picks));
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: free_scores — get free data scores
// ═══════════════════════════════════════════
if ($action === 'free_scores') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    
    if ($ticker !== '') {
        $t = _md_esc($conn, $ticker);
        $r = $conn->query("SELECT * FROM lm_free_data_scores
            WHERE ticker = '$t' AND calc_date = (SELECT MAX(calc_date) FROM lm_free_data_scores WHERE ticker = '$t')
            ORDER BY calc_date DESC LIMIT 1");
        
        if ($r && $row = $r->fetch_assoc()) {
            echo json_encode(array(
                'ok' => true,
                'action' => 'free_scores',
                'ticker' => $ticker,
                'data' => array(
                    'value_score' => intval($row['value_score']),
                    'growth_score' => intval($row['growth_score']),
                    'momentum_score' => intval($row['momentum_score']),
                    'volatility_score' => intval($row['volatility_score']),
                    'liquidity_score' => intval($row['liquidity_score']),
                    'sentiment_score' => intval($row['sentiment_score']),
                    'calc_date' => $row['calc_date']
                )
            ));
        } else {
            echo json_encode(array(
                'ok' => true,
                'action' => 'free_scores',
                'ticker' => $ticker,
                'message' => 'No free data scores yet. Run free_data_scraper.php?action=fetch_all first.',
                'data' => array(
                    'value_score' => 50,
                    'growth_score' => 50,
                    'momentum_score' => 50,
                    'volatility_score' => 50,
                    'liquidity_score' => 50,
                    'sentiment_score' => 50
                )
            ));
        }
    } else {
        // All tickers
        $r = $conn->query("SELECT * FROM lm_free_data_scores
            WHERE calc_date = (SELECT MAX(calc_date) FROM lm_free_data_scores)
            ORDER BY (value_score + growth_score + momentum_score) / 3 DESC LIMIT 10");
        
        $scores = array();
        if ($r) {
            while ($row = $r->fetch_assoc()) {
                $scores[] = array(
                    'ticker' => $row['ticker'],
                    'value_score' => intval($row['value_score']),
                    'growth_score' => intval($row['growth_score']),
                    'momentum_score' => intval($row['momentum_score']),
                    'volatility_score' => intval($row['volatility_score']),
                    'liquidity_score' => intval($row['liquidity_score']),
                    'sentiment_score' => intval($row['sentiment_score']),
                    'calc_date' => $row['calc_date']
                );
            }
        }
        
        echo json_encode(array('ok' => true, 'action' => 'free_scores', 'count' => count($scores), 'tickers' => $scores));
    }
    
    $conn->close();
    exit;
}

// ═══════════════════════════════════════════
//  Action: all — all tickers with scores
// ═══════════════════════════════════════════
if ($action === 'all') {
    $r = $conn->query("SELECT * FROM lm_multi_dimensional
        WHERE calc_date = (SELECT MAX(calc_date) FROM lm_multi_dimensional)
        ORDER BY conviction_score DESC");

    $all = array();
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $all[] = array(
                'ticker' => $row['ticker'],
                'whale_score' => intval($row['whale_score']),
                'insider_score' => intval($row['insider_score']),
                'analyst_score' => intval($row['analyst_score']),
                'crowd_score' => intval($row['crowd_score']),
                'fear_greed_score' => intval($row['fear_greed_score']),
                'regime_score' => intval($row['regime_score']),
                'value_score' => intval($row['value_score']),
                'growth_score' => intval($row['growth_score']),
                'momentum_score' => intval($row['momentum_score']),
                'conviction_score' => intval($row['conviction_score']),
                'conviction_label' => $row['conviction_label'],
                'calc_date' => $row['calc_date']
            );
        }
    }

    echo json_encode(array('ok' => true, 'action' => 'all', 'count' => count($all), 'tickers' => $all));
    $conn->close();
    exit;
}

echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
$conn->close();
?>
