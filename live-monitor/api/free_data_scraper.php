<?php
/**
 * Free Data Scraper API
 * Integrates free data sources to supplement multi-dimensional analysis
 * 
 * Data Sources:
 * - Alpha Vantage (Free Tier)
 * - Financial Modeling Prep (Free Tier)
 * - SEC EDGAR (Free)
 * - Reddit API (Free)
 * 
 * PHP 5.2 compatible
 */

require_once dirname(__FILE__) . '/db_connect.php';

// ── Ensure schema ──
$conn->query("CREATE TABLE IF NOT EXISTS lm_free_data_cache (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    source VARCHAR(30) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    data_json TEXT NOT NULL,
    fetch_date DATETIME NOT NULL,
    expiry_date DATETIME NOT NULL,
    UNIQUE KEY idx_ticker_source (ticker, source, data_type),
    KEY idx_expiry (expiry_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS lm_free_data_scores (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    calc_date DATE NOT NULL,
    value_score INT NOT NULL DEFAULT 50,
    growth_score INT NOT NULL DEFAULT 50,
    momentum_score INT NOT NULL DEFAULT 50,
    volatility_score INT NOT NULL DEFAULT 50,
    liquidity_score INT NOT NULL DEFAULT 50,
    sentiment_score INT NOT NULL DEFAULT 50,
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker_date (ticker, calc_date),
    KEY idx_ticker (ticker),
    KEY idx_date (calc_date)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$action = isset($_GET['action']) ? $_GET['action'] : 'status';
$admin_key = isset($_GET['key']) ? $_GET['key'] : '';

// ─────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────
function _fds_esc($conn, $val) {
    return $conn->real_escape_string($val);
}

function _fds_http_get($url) {
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'FreeDataScraper/1.0 contact@findtorontoevents.ca');
        $result = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($code >= 200 && $code < 300 && $result !== false) return $result;
    }
    $ctx = stream_context_create(array('http' => array(
        'timeout' => 15,
        'header' => "User-Agent: FreeDataScraper/1.0\r\n"
    )));
    $result = @file_get_contents($url, false, $ctx);
    return ($result !== false) ? $result : null;
}

function _fds_cache_get($conn, $ticker, $source, $data_type, $ttl) {
    $t = _fds_esc($conn, $ticker);
    $s = _fds_esc($conn, $source);
    $dt = _fds_esc($conn, $data_type);
    $now = gmdate('Y-m-d H:i:s');
    
    $r = $conn->query("SELECT data_json FROM lm_free_data_cache 
        WHERE ticker = '$t' AND source = '$s' AND data_type = '$dt' 
        AND expiry_date > '$now' ORDER BY fetch_date DESC LIMIT 1");
    
    if ($r && $row = $r->fetch_assoc()) {
        return json_decode($row['data_json'], true);
    }
    return null;
}

function _fds_cache_set($conn, $ticker, $source, $data_type, $data) {
    $t = _fds_esc($conn, $ticker);
    $s = _fds_esc($conn, $source);
    $dt = _fds_esc($conn, $data_type);
    $json = _fds_esc($conn, json_encode($data));
    $now = gmdate('Y-m-d H:i:s');
    $expiry = gmdate('Y-m-d H:i:s', time() + 3600); // 1 hour expiry
    
    $conn->query("DELETE FROM lm_free_data_cache 
        WHERE ticker = '$t' AND source = '$s' AND data_type = '$dt'");
    
    $conn->query("INSERT INTO lm_free_data_cache 
        (ticker, source, data_type, data_json, fetch_date, expiry_date)
        VALUES ('$t', '$s', '$dt', '$json', '$now', '$expiry')");
}

function _fds_clamp($val) {
    return max(0, min(100, round($val)));
}

// ─────────────────────────────────────────
//  Alpha Vantage Integration
// ─────────────────────────────────────────
function _fds_fetch_alpha_vantage($conn, $ticker) {
    // Get API key from config or use demo key
    $api_key = isset($ALPHA_VANTAGE_KEY) ? $ALPHA_VANTAGE_KEY : 'demo';
    
    // Check cache
    $cached = _fds_cache_get($conn, $ticker, 'alpha_vantage', 'quote', 300);
    if ($cached !== null) return $cached;
    
    $url = "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=" . urlencode($ticker) . "&apikey=" . urlencode($api_key);
    $raw = _fds_http_get($url);
    
    if ($raw === null) {
        return array('error' => 'fetch_failed', 'score' => 50);
    }
    
    $json = json_decode($raw, true);
    
    if (!isset($json['Global Quote'])) {
        return array('error' => 'parse_failed', 'score' => 50);
    }
    
    $quote = $json['Global Quote'];
    $result = array(
        'symbol' => $quote['01. symbol'],
        'price' => floatval($quote['05. price']),
        'change' => floatval($quote['09. change']),
        'change_pct' => floatval($quote['10. change percent']),
        'volume' => intval($quote['06. volume']),
        'latest_trading_day' => $quote['07. latest trading day'],
        'score' => 50, // Will be calculated
        'fetched_at' => gmdate('Y-m-d H:i:s')
    );
    
    _fds_cache_set($conn, $ticker, 'alpha_vantage', 'quote', $result);
    return $result;
}

function _fds_fetch_alpha_fundamentals($conn, $ticker) {
    $api_key = isset($ALPHA_VANTAGE_KEY) ? $ALPHA_VANTAGE_KEY : 'demo';
    
    $cached = _fds_cache_get($conn, $ticker, 'alpha_vantage', 'overview', 86400); // 24h cache
    if ($cached !== null) return $cached;
    
    $url = "https://www.alphavantage.co/query?function=OVERVIEW&symbol=" . urlencode($ticker) . "&apikey=" . urlencode($api_key);
    $raw = _fds_http_get($url);
    
    if ($raw === null) {
        return array('error' => 'fetch_failed', 'score' => 50);
    }
    
    $json = json_decode($raw, true);
    
    $result = array(
        'symbol' => $ticker,
        'name' => isset($json['Name']) ? $json['Name'] : '',
        'sector' => isset($json['Sector']) ? $json['Sector'] : '',
        'industry' => isset($json['Industry']) ? $json['Industry'] : '',
        'market_cap' => isset($json['MarketCapitalization']) ? floatval($json['MarketCapitalization']) : 0,
        'pe_ratio' => isset($json['PERatio']) ? floatval($json['PERatio']) : 0,
        'eps' => isset($json['EPS']) ? floatval($json['EPS']) : 0,
        'dividend_yield' => isset($json['DividendYield']) ? floatval($json['DividendYield']) : 0,
        'beta' => isset($json['Beta']) ? floatval($json['Beta']) : 0,
        '52_week_high' => isset($json['52WeekHigh']) ? floatval($json['52WeekHigh']) : 0,
        '52_week_low' => isset($json['52WeekLow']) ? floatval($json['52WeekLow']) : 0,
        'score' => 50,
        'fetched_at' => gmdate('Y-m-d H:i:s')
    );
    
    _fds_cache_set($conn, $ticker, 'alpha_vantage', 'overview', $result);
    return $result;
}

// ─────────────────────────────────────────
//  Financial Modeling Prep Integration
// ─────────────────────────────────────────
function _fds_fetch_fmp_quote($conn, $ticker) {
    $api_key = isset($FMP_API_KEY) ? $FMP_API_KEY : '';
    
    if (empty($api_key)) {
        return array('error' => 'no_api_key', 'score' => 50);
    }
    
    $cached = _fds_cache_get($conn, $ticker, 'fmp', 'quote', 300);
    if ($cached !== null) return $cached;
    
    $url = "https://financialmodelingprep.com/api/v3/quote/" . urlencode($ticker) . "?apikey=" . urlencode($api_key);
    $raw = _fds_http_get($url);
    
    if ($raw === null) {
        return array('error' => 'fetch_failed', 'score' => 50);
    }
    
    $json = json_decode($raw, true);
    
    if (!is_array($json) || count($json) === 0) {
        return array('error' => 'parse_failed', 'score' => 50);
    }
    
    $quote = $json[0];
    $result = array(
        'symbol' => $quote['symbol'],
        'price' => floatval($quote['price']),
        'change' => floatval($quote['change']),
        'change_pct' => floatval($quote['changesPercentage']),
        'volume' => intval($quote['volume']),
        'market_cap' => floatval($quote['marketCap']),
        'pe_ratio' => floatval($quote['peRatio']),
        'eps' => floatval($quote['eps']),
        'score' => 50,
        'fetched_at' => gmdate('Y-m-d H:i:s')
    );
    
    _fds_cache_set($conn, $ticker, 'fmp', 'quote', $result);
    return $result;
}

function _fds_fetch_fmp_ratios($conn, $ticker) {
    $api_key = isset($FMP_API_KEY) ? $FMP_API_KEY : '';
    
    if (empty($api_key)) {
        return array('error' => 'no_api_key', 'score' => 50);
    }
    
    $cached = _fds_cache_get($conn, $ticker, 'fmp', 'ratios', 86400); // 24h cache
    if ($cached !== null) return $cached;
    
    $url = "https://financialmodelingprep.com/api/v3/ratios/" . urlencode($ticker) . "?apikey=" . urlencode($api_key);
    $raw = _fds_http_get($url);
    
    if ($raw === null) {
        return array('error' => 'fetch_failed', 'score' => 50);
    }
    
    $json = json_decode($raw, true);
    
    if (!is_array($json) || count($json) === 0) {
        return array('error' => 'parse_failed', 'score' => 50);
    }
    
    $ratio = $json[0];
    $result = array(
        'symbol' => $ticker,
        'pe_ratio' => floatval($ratio['peRatio']),
        'pb_ratio' => floatval($ratio['pbRatio']),
        'ps_ratio' => floatval($ratio['psRatio']),
        'de_ratio' => floatval($ratio['deRatio']),
        'current_ratio' => floatval($ratio['currentRatio']),
        'roe' => floatval($ratio['returnOnEquity']),
        'roa' => floatval($ratio['returnOnAssets']),
        'net_margin' => floatval($ratio['netProfitMargin']),
        'score' => 50,
        'fetched_at' => gmdate('Y-m-d H:i:s')
    );
    
    _fds_cache_set($conn, $ticker, 'fmp', 'ratios', $result);
    return $result;
}

// ─────────────────────────────────────────
//  Reddit API Integration (WSB)
// ─────────────────────────────────────────
function _fds_fetch_reddit_sentiment($conn, $ticker) {
    $cached = _fds_cache_get($conn, $ticker, 'reddit', 'sentiment', 1800); // 30 min cache
    if ($cached !== null) return $cached;
    
    // Use Reddit search API
    $url = "https://www.reddit.com/r/wallstreetbets/search.json?q=" . urlencode($ticker) . "&sort=relevance&limit=25";
    $raw = _fds_http_get($url);
    
    if ($raw === null) {
        return array('error' => 'fetch_failed', 'score' => 50, 'mentions' => 0);
    }
    
    $json = json_decode($raw, true);
    
    if (!isset($json['data']) || !isset($json['data']['children'])) {
        return array('error' => 'parse_failed', 'score' => 50, 'mentions' => 0);
    }
    
    $posts = $json['data']['children'];
    $mentions = count($posts);
    $positive = 0;
    $negative = 0;
    
    foreach ($posts as $post) {
        $title = strtolower($post['data']['title']);
        $selftext = strtolower($post['data']['selftext']);
        
        // Simple sentiment analysis
        $positive_words = array('buy', 'long', 'call', 'moon', 'rocket', 'bull', 'gain', 'profit', 'up', 'green');
        $negative_words = array('sell', 'short', 'put', 'dump', 'crash', 'bear', 'loss', 'down', 'red', 'sell');
        
        $pos_count = 0;
        $neg_count = 0;
        
        foreach ($positive_words as $word) {
            if (strpos($title, $word) !== false || strpos($selftext, $word) !== false) {
                $pos_count++;
            }
        }
        
        foreach ($negative_words as $word) {
            if (strpos($title, $word) !== false || strpos($selftext, $word) !== false) {
                $neg_count++;
            }
        }
        
        if ($pos_count > $neg_count) $positive++;
        elseif ($neg_count > $pos_count) $negative++;
    }
    
    $total = $positive + $negative;
    $sentiment = ($total > 0) ? (($positive - $negative) / $total) : 0;
    
    // Map -1 to 1 to 0 to 100
    $score = _fds_clamp(round(($sentiment + 1) * 50));
    
    $result = array(
        'ticker' => $ticker,
        'mentions' => $mentions,
        'positive' => $positive,
        'negative' => $negative,
        'sentiment' => $sentiment,
        'score' => $score,
        'fetched_at' => gmdate('Y-m-d H:i:s')
    );
    
    _fds_cache_set($conn, $ticker, 'reddit', 'sentiment', $result);
    return $result;
}

// ─────────────────────────────────────────
//  Score Calculations
// ─────────────────────────────────────────
function _fds_calculate_value_score($fmp_ratios, $alpha_fundamentals) {
    $score = 50;
    $details = array();
    
    // P/E Ratio analysis
    $pe = $fmp_ratios['pe_ratio'] ?? ($alpha_fundamentals['pe_ratio'] ?? 0);
    if ($pe > 0) {
        if ($pe < 15) {
            $score += 20;
            $details[] = 'low_pe';
        } elseif ($pe < 25) {
            $score += 10;
            $details[] = 'moderate_pe';
        } elseif ($pe < 35) {
            $score += 0;
            $details[] = 'high_pe';
        } else {
            $score -= 10;
            $details[] = 'very_high_pe';
        }
    }
    
    // P/B Ratio analysis
    $pb = $fmp_ratios['pb_ratio'] ?? 0;
    if ($pb > 0) {
        if ($pb < 1.5) {
            $score += 15;
            $details[] = 'low_pb';
        } elseif ($pb < 2.5) {
            $score += 8;
            $details[] = 'moderate_pb';
        } else {
            $score -= 5;
            $details[] = 'high_pb';
        }
    }
    
    // P/S Ratio analysis
    $ps = $fmp_ratios['ps_ratio'] ?? 0;
    if ($ps > 0) {
        if ($ps < 3) {
            $score += 15;
            $details[] = 'low_ps';
        } elseif ($ps < 5) {
            $score += 8;
            $details[] = 'moderate_ps';
        } else {
            $score -= 5;
            $details[] = 'high_ps';
        }
    }
    
    // Dividend Yield
    $yield = $alpha_fundamentals['dividend_yield'] ?? 0;
    if ($yield > 0) {
        $score += min(15, round($yield * 2));
        $details[] = 'dividend_' . ($yield > 3 ? 'high' : 'moderate');
    }
    
    return array('score' => _fds_clamp($score), 'details' => $details);
}

function _fds_calculate_growth_score($fmp_ratios, $alpha_fundamentals) {
    $score = 50;
    $details = array();
    
    // ROE analysis
    $roe = $fmp_ratios['roa'] ?? 0;
    if ($roe > 0) {
        if ($roe > 0.15) {
            $score += 25;
            $details[] = 'strong_roe';
        } elseif ($roe > 0.10) {
            $score += 15;
            $details[] = 'good_roe';
        } elseif ($roe > 0.05) {
            $score += 5;
            $details[] = 'moderate_roe';
        } else {
            $score -= 5;
            $details[] = 'low_roe';
        }
    }
    
    // Net Margin analysis
    $margin = $fmp_ratios['net_margin'] ?? 0;
    if ($margin > 0) {
        if ($margin > 0.20) {
            $score += 20;
            $details[] = 'high_margin';
        } elseif ($margin > 0.10) {
            $score += 12;
            $details[] = 'good_margin';
        } elseif ($margin > 0.05) {
            $score += 5;
            $details[] = 'moderate_margin';
        } else {
            $score -= 5;
            $details[] = 'low_margin';
        }
    }
    
    // Market Cap (larger = more stable)
    $mcap = $fmp_ratios['market_cap'] ?? ($alpha_fundamentals['market_cap'] ?? 0);
    if ($mcap > 0) {
        if ($mcap > 100000000000) {
            $score += 15;
            $details[] = 'mega_cap';
        } elseif ($mcap > 10000000000) {
            $score += 10;
            $details[] = 'large_cap';
        } elseif ($mcap > 2000000000) {
            $score += 5;
            $details[] = 'mid_cap';
        } else {
            $score += 0;
            $details[] = 'small_cap';
        }
    }
    
    return array('score' => _fds_clamp($score), 'details' => $details);
}

function _fds_calculate_momentum_score($alpha_quote, $fmp_quote) {
    $score = 50;
    $details = array();
    
    // Price change (24h)
    $change_pct = $alpha_quote['change_pct'] ?? ($fmp_quote['change_pct'] ?? 0);
    if ($change_pct > 0) {
        $score += min(30, round($change_pct * 3));
        $details[] = 'positive_momentum';
    } else {
        $score -= min(20, abs(round($change_pct * 2)));
        $details[] = 'negative_momentum';
    }
    
    // Volume analysis
    $volume = $alpha_quote['volume'] ?? ($fmp_quote['volume'] ?? 0);
    if ($volume > 1000000) {
        $score += 15;
        $details[] = 'high_volume';
    } elseif ($volume > 500000) {
        $score += 8;
        $details[] = 'moderate_volume';
    }
    
    // 52-week high proximity
    $high = $alpha_quote['52_week_high'] ?? 0;
    $price = $alpha_quote['price'] ?? 0;
    if ($high > 0 && $price > 0) {
        $proximity = ($price / $high) * 100;
        if ($proximity > 90) {
            $score += 15;
            $details[] = 'near_52h_high';
        } elseif ($proximity > 80) {
            $score += 8;
            $details[] = 'near_52h_high';
        }
    }
    
    return array('score' => _fds_clamp($score), 'details' => $details);
}

function _fds_calculate_volatility_score($alpha_fundamentals, $fmp_quote) {
    $score = 50;
    $details = array();
    
    // Beta analysis
    $beta = $alpha_fundamentals['beta'] ?? 1.0;
    if ($beta < 0.8) {
        $score += 20;
        $details[] = 'low_volatility';
    } elseif ($beta < 1.2) {
        $score += 10;
        $details[] = 'moderate_volatility';
    } else {
        $score -= 5;
        $details[] = 'high_volatility';
    }
    
    // Price range (52-week)
    $high = $alpha_fundamentals['52_week_high'] ?? 0;
    $low = $alpha_fundamentals['52_week_low'] ?? 0;
    $price = $alpha_fundamentals['price'] ?? 0;
    
    if ($high > 0 && $low > 0 && $price > 0) {
        $range_pct = (($high - $low) / $low) * 100;
        if ($range_pct < 30) {
            $score += 15;
            $details[] = 'stable_price';
        } elseif ($range_pct < 50) {
            $score += 5;
            $details[] = 'moderate_range';
        } else {
            $score -= 5;
            $details[] = 'volatile_price';
        }
    }
    
    return array('score' => _fds_clamp($score), 'details' => $details);
}

function _fds_calculate_liquidity_score($alpha_quote, $fmp_quote) {
    $score = 50;
    $details = array();
    
    // Volume analysis
    $volume = $alpha_quote['volume'] ?? ($fmp_quote['volume'] ?? 0);
    if ($volume > 1000000) {
        $score += 30;
        $details[] = 'high_liquidity';
    } elseif ($volume > 500000) {
        $score += 20;
        $details[] = 'moderate_liquidity';
    } elseif ($volume > 100000) {
        $score += 10;
        $details[] = 'low_liquidity';
    } else {
        $score -= 5;
        $details[] = 'very_low_liquidity';
    }
    
    // Market Cap
    $mcap = $alpha_quote['market_cap'] ?? ($fmp_quote['market_cap'] ?? 0);
    if ($mcap > 10000000000) {
        $score += 20;
        $details[] = 'large_mcap_liquidity';
    } elseif ($mcap > 2000000000) {
        $score += 10;
        $details[] = 'mid_mcap_liquidity';
    }
    
    return array('score' => _fds_clamp($score), 'details' => $details);
}

function _fds_calculate_sentiment_score($reddit_sentiment, $alpha_quote) {
    $score = 50;
    $details = array();
    
    // Reddit sentiment
    if ($reddit_sentiment['mentions'] > 0) {
        $score += round(($reddit_sentiment['score'] - 50) * 0.5);
        $details[] = 'reddit_' . $reddit_sentiment['mentions'] . 'mentions';
    }
    
    // News sentiment from price action
    $change_pct = $alpha_quote['change_pct'] ?? 0;
    if ($change_pct > 2) {
        $score += 15;
        $details[] = 'positive_news';
    } elseif ($change_pct < -2) {
        $score -= 10;
        $details[] = 'negative_news';
    }
    
    return array('score' => _fds_clamp($score), 'details' => $details);
}

// ─────────────────────────────────────────
//  Store scores in DB
// ─────────────────────────────────────────
function _fds_store_scores($conn, $ticker, $scores) {
    $t = _fds_esc($conn, $ticker);
    $today = date('Y-m-d');
    $now = gmdate('Y-m-d H:i:s');
    
    $conn->query("DELETE FROM lm_free_data_scores 
        WHERE ticker = '$t' AND calc_date = '$today'");
    
    $conn->query("INSERT INTO lm_free_data_scores 
        (ticker, calc_date, value_score, growth_score, momentum_score, 
         volatility_score, liquidity_score, sentiment_score, created_at)
        VALUES ('$t', '$today', " . $scores['value_score'] . ", " . $scores['growth_score'] . ",
        " . $scores['momentum_score'] . ", " . $scores['volatility_score'] . ",
        " . $scores['liquidity_score'] . ", " . $scores['sentiment_score'] . ", '$now')");
}

// ═══════════════════════════════════════════
//  Actions
// ═══════════════════════════════════════════

// ── fetch_all (admin) ──────────────────────
if ($action === 'fetch_all') {
    if ($admin_key !== 'livetrader2026') {
        echo json_encode(array('ok' => false, 'error' => 'Invalid key'));
        $conn->close();
        exit;
    }
    
    $tickers = array('AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'JPM', 'WMT', 'XOM', 'NFLX', 'JNJ', 'BAC');
    $results = array();
    
    foreach ($tickers as $ticker) {
        $alpha_quote = _fds_fetch_alpha_vantage($conn, $ticker);
        $alpha_fund = _fds_fetch_alpha_fundamentals($conn, $ticker);
        $fmp_quote = _fds_fetch_fmp_quote($conn, $ticker);
        $fmp_ratios = _fds_fetch_fmp_ratios($conn, $ticker);
        $reddit = _fds_fetch_reddit_sentiment($conn, $ticker);
        
        // Calculate scores
        $value = _fds_calculate_value_score($fmp_ratios, $alpha_fund);
        $growth = _fds_calculate_growth_score($fmp_ratios, $alpha_fund);
        $momentum = _fds_calculate_momentum_score($alpha_quote, $fmp_quote);
        $volatility = _fds_calculate_volatility_score($alpha_fund, $fmp_quote);
        $liquidity = _fds_calculate_liquidity_score($alpha_quote, $fmp_quote);
        $sentiment = _fds_calculate_sentiment_score($reddit, $alpha_quote);
        
        $scores = array(
            'ticker' => $ticker,
            'value_score' => $value['score'],
            'growth_score' => $growth['score'],
            'momentum_score' => $momentum['score'],
            'volatility_score' => $volatility['score'],
            'liquidity_score' => $liquidity['score'],
            'sentiment_score' => $sentiment['score']
        );
        
        _fds_store_scores($conn, $ticker, $scores);
        
        $results[] = array(
            'ticker' => $ticker,
            'scores' => $scores,
            'details' => array(
                'value' => $value['details'],
                'growth' => $growth['details'],
                'momentum' => $momentum['details'],
                'volatility' => $volatility['details'],
                'liquidity' => $liquidity['details'],
                'sentiment' => $sentiment['details']
            )
        );
    }
    
    echo json_encode(array(
        'ok' => true,
        'action' => 'fetch_all',
        'tickers_processed' => count($results),
        'results' => $results,
        'timestamp' => gmdate('Y-m-d H:i:s')
    ));
    $conn->close();
    exit;
}

// ── scores (public) ────────────────────────
if ($action === 'scores') {
    $ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
    
    if ($ticker !== '') {
        $t = _fds_esc($conn, $ticker);
        $r = $conn->query("SELECT * FROM lm_free_data_scores 
            WHERE ticker = '$t' AND calc_date = (SELECT MAX(calc_date) FROM lm_free_data_scores WHERE ticker = '$t')
            ORDER BY calc_date DESC LIMIT 1");
        
        if ($r && $row = $r->fetch_assoc()) {
            echo json_encode(array(
                'ok' => true,
                'action' => 'scores',
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
                'action' => 'scores',
                'ticker' => $ticker,
                'message' => 'No scores yet. Run fetch_all first.',
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
        
        echo json_encode(array(
            'ok' => true,
            'action' => 'scores',
            'count' => count($scores),
            'tickers' => $scores
        ));
    }
    
    $conn->close();
    exit;
}

// ── status ─────────────────────────────────
if ($action === 'status') {
    $has_data = false;
    $r = $conn->query("SELECT COUNT(*) as c FROM lm_free_data_scores");
    if ($r && $row = $r->fetch_assoc()) {
        $has_data = intval($row['c']) > 0;
    }
    
    echo json_encode(array(
        'ok' => true,
        'action' => 'status',
        'has_data' => $has_data,
        'tables' => array(
            'lm_free_data_cache' => 'Created',
            'lm_free_data_scores' => 'Created'
        ),
        'admin_actions' => array(
            'fetch_all' => 'Fetch all data sources and calculate scores (key required)'
        ),
        'public_actions' => array(
            'scores' => 'Get free data scores (?ticker=AAPL optional)'
        )
    ));
    $conn->close();
    exit;
}

// Default
echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
$conn->close();
?>
