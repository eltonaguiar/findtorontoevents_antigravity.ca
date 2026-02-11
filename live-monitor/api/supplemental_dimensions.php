<?php
/**
 * Supplemental Dimensions API for Multi-Dimensional Analysis
 * Adds 4 new dimensions using FREE data sources
 * PHP 5.2 compatible
 */

require_once dirname(__FILE__) . '/db_connect.php';
require_once dirname(__FILE__) . '/db_config.php';

// API Keys are now loaded from db_config.php
// If db_config.php doesn't have them defined, they can be set as environment variables
// For local testing, you can also define them directly below:
// $FMP_API_KEY = 'your_key_here';
// $MASSIVE_API_KEY = 'your_key_here';

// Ensure schema
$conn->query("CREATE TABLE IF NOT EXISTS lm_supplemental_dimensions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    calc_date DATE NOT NULL,
    options_score INT NOT NULL DEFAULT 50,
    short_interest_score INT NOT NULL DEFAULT 50,
    technical_score INT NOT NULL DEFAULT 50,
    earnings_quality_score INT NOT NULL DEFAULT 50,
    composite_supplemental INT NOT NULL DEFAULT 50,
    detail_json TEXT,
    created_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker_date (ticker, calc_date),
    KEY idx_ticker (ticker)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

$conn->query("CREATE TABLE IF NOT EXISTS lm_scraped_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    data_type VARCHAR(30) NOT NULL,
    data_json TEXT NOT NULL,
    scraped_at DATETIME NOT NULL,
    expires_at DATETIME NOT NULL,
    UNIQUE KEY idx_ticker_type (ticker, data_type),
    KEY idx_expires (expires_at)
) ENGINE=MyISAM DEFAULT CHARSET=utf8");

// ─────────────────────────────────────────
//  Helper Functions
// ─────────────────────────────────────────
function _sd_esc($conn, $val) {
    return $conn->real_escape_string($val);
}

function _sd_clamp($val, $min = 0, $max = 100) {
    return max($min, min($max, round($val)));
}

function _sd_http_get($url, $headers = array()) {
    $ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';
    
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, $ua);
        if (!empty($headers)) {
            curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
        }
        $resp = curl_exec($ch);
        curl_close($ch);
        if ($resp !== false) return $resp;
    }
    
    $ctx = stream_context_create(array('http' => array(
        'timeout' => 15,
        'user_agent' => $ua,
        'header' => 'Accept: application/json, text/html, */*'
    )));
    return @file_get_contents($url, false, $ctx);
}

// Cache helpers
function _sd_cache_get($conn, $ticker, $data_type) {
    $t = _sd_esc($conn, $ticker);
    $d = _sd_esc($conn, $data_type);
    $r = $conn->query("SELECT data_json FROM lm_scraped_data 
        WHERE ticker = '$t' AND data_type = '$d' AND expires_at > NOW() LIMIT 1");
    if ($r && $row = $r->fetch_assoc()) {
        return json_decode($row['data_json'], true);
    }
    return null;
}

function _sd_cache_set($conn, $ticker, $data_type, $data, $ttl_minutes = 60) {
    $t = _sd_esc($conn, $ticker);
    $d = _sd_esc($conn, $data_type);
    $json = _sd_esc($conn, json_encode($data));
    $expires = date('Y-m-d H:i:s', strtotime("+{$ttl_minutes} minutes"));
    
    $conn->query("INSERT INTO lm_scraped_data (ticker, data_type, data_json, scraped_at, expires_at)
        VALUES ('$t', '$d', '$json', NOW(), '$expires')
        ON DUPLICATE KEY UPDATE data_json = VALUES(data_json), scraped_at = NOW(), expires_at = VALUES(expires_at)");
}

// ─────────────────────────────────────────
//  Dimension 7: Options Flow Score
// ─────────────────────────────────────────
function calc_options_score($conn, $ticker, $api_key) {
    $score = 50;
    $detail = 'no_data';
    $put_call_ratio = 1.0;
    $unusual_activity = false;
    
    // Try cache first
    $cached = _sd_cache_get($conn, $ticker, 'options');
    if ($cached) {
        return array(
            'score' => $cached['score'],
            'detail' => $cached['detail'],
            'put_call_ratio' => $cached['put_call_ratio'],
            'unusual_activity' => $cached['unusual_activity']
        );
    }
    
    // Method 1: Massive (formerly Polygon.io) - if API key available
    if ($api_key && $api_key !== 'YOUR_MASSIVE_KEY_HERE' && $api_key !== 'YOUR_POLYGON_KEY_HERE') {
        $url = "https://api.polygon.io/v3/reference/options/contracts?underlying_ticker={$ticker}&apiKey={$api_key}&limit=10";
        $resp = _sd_http_get($url);
        if ($resp) {
            $data = json_decode($resp, true);
            if ($data && isset($data['results']) && count($data['results']) > 0) {
                // Calculate implied put/call from contract count
                $puts = 0;
                $calls = 0;
                foreach ($data['results'] as $contract) {
                    if (isset($contract['contract_type'])) {
                        if ($contract['contract_type'] === 'put') $puts++;
                        if ($contract['contract_type'] === 'call') $calls++;
                    }
                }
                if ($calls + $puts > 0) {
                    $put_call_ratio = $puts / max($calls, 1);
                }
            }
        }
    }
    
    // Method 2: Yahoo Finance scrape (fallback)
    if ($put_call_ratio === 1.0) {
        $url = "https://finance.yahoo.com/quote/{$ticker}/options";
        $html = _sd_http_get($url);
        if ($html) {
            // Look for put/call ratio in page
            // Pattern: "Put/Call Ratio" followed by number
            if (preg_match('/Put\/Call Ratio[^0-9]*([0-9.]+)/i', $html, $matches)) {
                $put_call_ratio = floatval($matches[1]);
            }
        }
    }
    
    // Calculate score from put/call ratio
    // Low P/C ratio = bullish (calls > puts) = higher score
    // High P/C ratio = bearish (puts > calls) = lower score
    if ($put_call_ratio < 0.7) {
        $score = _sd_clamp(85 - ($put_call_ratio * 50)); // 0.7 → 50, 0.3 → 70
        $detail = 'bullish_flow pcr=' . round($put_call_ratio, 2);
    } elseif ($put_call_ratio > 1.3) {
        $score = _sd_clamp(65 - ($put_call_ratio * 30)); // 1.3 → 26, 2.0 → 5
        $detail = 'bearish_flow pcr=' . round($put_call_ratio, 2);
    } else {
        $score = 50;
        $detail = 'neutral_flow pcr=' . round($put_call_ratio, 2);
    }
    
    // Unusual activity bonus (would need more data to detect)
    if ($put_call_ratio < 0.4 || $put_call_ratio > 2.0) {
        $unusual_activity = true;
        $detail .= ' unusual';
    }
    
    $result = array(
        'score' => $score,
        'detail' => $detail,
        'put_call_ratio' => $put_call_ratio,
        'unusual_activity' => $unusual_activity
    );
    
    _sd_cache_set($conn, $ticker, 'options', $result, 15); // 15 min cache
    return $result;
}

// ─────────────────────────────────────────
//  Dimension 8: Short Interest Score
// ─────────────────────────────────────────
function calc_short_interest_score($conn, $ticker, $api_key) {
    $score = 50;
    $detail = 'no_data';
    $short_pct_float = 0;
    $days_to_cover = 0;
    $squeeze_potential = 'low';
    
    // Try cache first
    $cached = _sd_cache_get($conn, $ticker, 'short_interest');
    if ($cached) {
        return $cached;
    }
    
    // Method 1: Financial Modeling Prep (FMP)
    if ($api_key && $api_key !== 'YOUR_FMP_KEY_HERE' && strlen($api_key) > 10) {
        $url = "https://financialmodelingprep.com/api/v4/short_interest/{$ticker}?apikey={$api_key}";
        $resp = _sd_http_get($url);
        if ($resp) {
            $data = json_decode($resp, true);
            if ($data && is_array($data) && count($data) > 0) {
                $short_pct_float = floatval($data[0]['shortPercentOfFloat'] ?? 0) * 100;
                $days_to_cover = floatval($data[0]['daysToCover'] ?? 0);
            }
        }
    }
    
    // Method 2: Yahoo Finance scrape (fallback)
    if ($short_pct_float == 0) {
        $url = "https://finance.yahoo.com/quote/{$ticker}/key-statistics";
        $html = _sd_http_get($url);
        if ($html) {
            // Look for short ratio
            if (preg_match('/Short Ratio[^0-9]*([0-9.]+)/i', $html, $matches)) {
                $days_to_cover = floatval($matches[1]);
            }
            // Look for short % of float
            if (preg_match('/Short % of Float[^0-9]*([0-9.]+)/i', $html, $matches)) {
                $short_pct_float = floatval($matches[1]);
            }
        }
    }
    
    // Calculate score
    // High short interest + high days to cover = squeeze potential = BULLISH signal
    if ($short_pct_float > 0) {
        $squeeze_score = ($short_pct_float * $days_to_cover) / 100;
        
        if ($short_pct_float > 30 && $days_to_cover > 5) {
            // Extreme squeeze potential - very bullish
            $score = 85;
            $squeeze_potential = 'extreme';
            $detail = 'extreme_squeeze short=' . round($short_pct_float, 1) . '% dtc=' . round($days_to_cover, 1);
        } elseif ($short_pct_float > 20 && $days_to_cover > 3) {
            // High squeeze potential - bullish
            $score = 75;
            $squeeze_potential = 'high';
            $detail = 'high_squeeze short=' . round($short_pct_float, 1) . '% dtc=' . round($days_to_cover, 1);
        } elseif ($short_pct_float > 15) {
            // Moderate short interest
            $score = 60;
            $squeeze_potential = 'moderate';
            $detail = 'moderate_short short=' . round($short_pct_float, 1) . '%';
        } elseif ($short_pct_float < 5) {
            // Low short interest - neutral
            $score = 50;
            $squeeze_potential = 'low';
            $detail = 'low_short short=' . round($short_pct_float, 1) . '%';
        } else {
            $score = 55;
            $detail = 'normal short=' . round($short_pct_float, 1) . '%';
        }
    }
    
    $result = array(
        'score' => $score,
        'detail' => $detail,
        'short_pct_float' => $short_pct_float,
        'days_to_cover' => $days_to_cover,
        'squeeze_potential' => $squeeze_potential
    );
    
    // Cache for longer - short interest only updates 2x per month
    _sd_cache_set($conn, $ticker, 'short_interest', $result, 720); // 12 hours
    return $result;
}

// ─────────────────────────────────────────
//  Dimension 9: Technical Score
// ─────────────────────────────────────────
function calc_technical_score($conn, $ticker) {
    $score = 50;
    $detail = 'no_data';
    $rsi = 50;
    $trend = 'neutral';
    $ma_alignment = 'neutral';
    
    // Get price history from existing daily_prices table
    $t = _sd_esc($conn, $ticker);
    $r = $conn->query("SELECT close_price, high_price, low_price, volume
        FROM daily_prices 
        WHERE ticker = '$t' 
        ORDER BY trade_date DESC 
        LIMIT 50");
    
    $prices = array();
    $highs = array();
    $lows = array();
    $volumes = array();
    
    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $prices[] = floatval($row['close_price']);
            $highs[] = floatval($row['high_price']);
            $lows[] = floatval($row['low_price']);
            $volumes[] = intval($row['volume']);
        }
    }
    
    if (count($prices) < 20) {
        return array('score' => 50, 'detail' => 'insufficient_data', 'rsi' => 50, 'trend' => 'unknown');
    }
    
    // Calculate RSI (simplified)
    $rsi = _calc_rsi_simple($prices, 14);
    
    // Calculate moving averages
    $ema_20 = _calc_ema($prices, 20);
    $ema_50 = count($prices) >= 50 ? _calc_ema($prices, 50) : $ema_20;
    $current_price = $prices[0];
    
    // MA Alignment
    if ($current_price > $ema_20 && $ema_20 > $ema_50) {
        $ma_alignment = 'bullish';
    } elseif ($current_price < $ema_20 && $ema_20 < $ema_50) {
        $ma_alignment = 'bearish';
    } else {
        $ma_alignment = 'mixed';
    }
    
    // RSI Component (40% weight)
    if ($rsi < 30) {
        $rsi_component = 80; // Oversold = bullish
    } elseif ($rsi < 45) {
        $rsi_component = 65;
    } elseif ($rsi < 55) {
        $rsi_component = 50;
    } elseif ($rsi < 70) {
        $rsi_component = 40;
    } else {
        $rsi_component = 25; // Overbought = bearish
    }
    
    // MA Component (40% weight)
    if ($ma_alignment === 'bullish') {
        $ma_component = 80;
    } elseif ($ma_alignment === 'bearish') {
        $ma_component = 30;
    } else {
        $ma_component = 50;
    }
    
    // Trend Strength (20% weight) - simplified ADX approximation
    $price_change_20 = ($prices[0] - $prices[min(19, count($prices)-1)]) / $prices[min(19, count($prices)-1)] * 100;
    if (abs($price_change_20) > 10) {
        $trend_component = 80;
    } elseif (abs($price_change_20) > 5) {
        $trend_component = 65;
    } else {
        $trend_component = 50;
    }
    
    // Calculate final score
    $score = _sd_clamp(($rsi_component * 0.4) + ($ma_component * 0.4) + ($trend_component * 0.2));
    
    $detail = "rsi=" . round($rsi, 1) . " ma={$ma_alignment} change20d=" . round($price_change_20, 1) . "%";
    
    return array(
        'score' => $score,
        'detail' => $detail,
        'rsi' => round($rsi, 2),
        'trend' => $ma_alignment,
        'price_change_20d' => round($price_change_20, 2)
    );
}

// Helper: Simple RSI calculation
function _calc_rsi_simple($prices, $period = 14) {
    if (count($prices) < $period + 1) return 50;
    
    $gains = 0;
    $losses = 0;
    
    for ($i = 0; $i < $period; $i++) {
        $change = $prices[$i] - $prices[$i + 1];
        if ($change > 0) {
            $gains += $change;
        } else {
            $losses += abs($change);
        }
    }
    
    if ($losses == 0) return 100;
    
    $rs = $gains / $losses;
    return 100 - (100 / (1 + $rs));
}

// Helper: EMA calculation
function _calc_ema($prices, $period) {
    if (count($prices) < $period) return $prices[0];
    
    $multiplier = 2 / ($period + 1);
    $ema = array_slice($prices, -$period)[0]; // Start with SMA
    
    for ($i = $period - 1; $i >= 0; $i--) {
        $ema = ($prices[$i] - $ema) * $multiplier + $ema;
    }
    
    return $ema;
}

// ─────────────────────────────────────────
//  Dimension 10: Earnings Quality Score
// ─────────────────────────────────────────
function calc_earnings_quality_score($conn, $ticker, $api_key) {
    $score = 50;
    $detail = 'no_data';
    $beat_rate = 0;
    $avg_surprise = 0;
    $streak = 0;
    
    // Try cache first
    $cached = _sd_cache_get($conn, $ticker, 'earnings');
    if ($cached) {
        return $cached;
    }
    
    // Method 1: FMP API
    if ($api_key && $api_key !== 'YOUR_FMP_KEY_HERE' && strlen($api_key) > 10) {
        $url = "https://financialmodelingprep.com/api/v3/earnings-surprises/{$ticker}?apikey={$api_key}";
        $resp = _sd_http_get($url);
        if ($resp) {
            $data = json_decode($resp, true);
            if ($data && is_array($data)) {
                $beats = 0;
                $total = count($data);
                $surprises = array();
                
                foreach ($data as $earnings) {
                    $surprise = floatval($earnings['surprisePercentage'] ?? 0);
                    $surprises[] = $surprise;
                    if ($surprise > 0) $beats++;
                }
                
                if ($total > 0) {
                    $beat_rate = ($beats / $total) * 100;
                    $avg_surprise = array_sum($surprises) / $total;
                }
                
                // Calculate streak
                $streak = 0;
                for ($i = 0; $i < count($surprises); $i++) {
                    if ($surprises[$i] > 0) {
                        if ($streak >= 0) $streak++;
                        else break;
                    } else {
                        if ($streak <= 0) $streak--;
                        else break;
                    }
                }
            }
        }
    }
    
    // Method 2: Use existing stock_earnings table if available
    if ($beat_rate == 0) {
        $t = _sd_esc($conn, $ticker);
        $r = $conn->query("SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN eps_actual > eps_estimate THEN 1 ELSE 0 END) as beats,
            AVG((eps_actual - eps_estimate) / eps_estimate * 100) as avg_surprise
            FROM stock_earnings WHERE ticker = '$t'");
        
        if ($r && $row = $r->fetch_assoc()) {
            $total = intval($row['total']);
            if ($total > 0) {
                $beat_rate = (intval($row['beats']) / $total) * 100;
                $avg_surprise = floatval($row['avg_surprise']);
            }
        }
    }
    
    // Calculate score
    if ($beat_rate > 0) {
        // Beat rate component (60% weight)
        if ($beat_rate >= 80) {
            $beat_component = 85;
        } elseif ($beat_rate >= 70) {
            $beat_component = 75;
        } elseif ($beat_rate >= 60) {
            $beat_component = 60;
        } elseif ($beat_rate >= 50) {
            $beat_component = 50;
        } else {
            $beat_component = 35;
        }
        
        // Surprise consistency (25% weight)
        if (abs($avg_surprise) > 10) {
            $consistency_component = 55; // High volatility
        } elseif (abs($avg_surprise) > 5) {
            $consistency_component = 70;
        } else {
            $consistency_component = 75; // Predictable
        }
        
        // Streak bonus (15% weight)
        $streak_component = 50;
        if ($streak >= 3) $streak_component = 85;
        elseif ($streak >= 2) $streak_component = 70;
        elseif ($streak <= -2) $streak_component = 30;
        elseif ($streak <= -3) $streak_component = 15;
        
        $score = _sd_clamp(($beat_component * 0.6) + ($consistency_component * 0.25) + ($streak_component * 0.15));
        
        $detail = "beat_rate=" . round($beat_rate, 1) . "% avg_surprise=" . round($avg_surprise, 1) . "% streak={$streak}";
    }
    
    $result = array(
        'score' => $score,
        'detail' => $detail,
        'beat_rate' => round($beat_rate, 2),
        'avg_surprise_pct' => round($avg_surprise, 2),
        'beat_streak' => $streak
    );
    
    _sd_cache_set($conn, $ticker, 'earnings', $result, 1440); // 24 hour cache
    return $result;
}

// ─────────────────────────────────────────
//  API Endpoints
// ─────────────────────────────────────────
$action = isset($_GET['action']) ? $_GET['action'] : 'all';
$ticker = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
$key = isset($_GET['key']) ? $_GET['key'] : '';
$admin = ($key === 'livetrader2026');
$now = date('Y-m-d H:i:s');

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');

// ── Single dimension: Options ──
if ($action === 'options' && $ticker) {
    $data = calc_options_score($conn, $ticker, $POLYGON_API_KEY);
    echo json_encode(array('ok' => true, 'ticker' => $ticker, 'dimension' => 'options', 'data' => $data));
    exit;
}

// ── Single dimension: Short Interest ──
if ($action === 'short' && $ticker) {
    $data = calc_short_interest_score($conn, $ticker, $FMP_API_KEY);
    echo json_encode(array('ok' => true, 'ticker' => $ticker, 'dimension' => 'short_interest', 'data' => $data));
    exit;
}

// ── Single dimension: Technical ──
if ($action === 'technical' && $ticker) {
    $data = calc_technical_score($conn, $ticker);
    echo json_encode(array('ok' => true, 'ticker' => $ticker, 'dimension' => 'technical', 'data' => $data));
    exit;
}

// ── Single dimension: Earnings ──
if ($action === 'earnings' && $ticker) {
    $data = calc_earnings_quality_score($conn, $ticker, $FMP_API_KEY);
    echo json_encode(array('ok' => true, 'ticker' => $ticker, 'dimension' => 'earnings_quality', 'data' => $data));
    exit;
}

// ── All supplemental dimensions ──
if ($action === 'all' && $ticker) {
    $options = calc_options_score($conn, $ticker, $MASSIVE_API_KEY);
    $short = calc_short_interest_score($conn, $ticker, $FMP_API_KEY);
    $technical = calc_technical_score($conn, $ticker);
    $earnings = calc_earnings_quality_score($conn, $ticker, $FMP_API_KEY);
    
    // Composite supplemental score (weighted average)
    $composite = _sd_clamp(
        $options['score'] * 0.25 +
        $short['score'] * 0.25 +
        $technical['score'] * 0.25 +
        $earnings['score'] * 0.25
    );
    
    $result = array(
        'ok' => true,
        'ticker' => $ticker,
        'timestamp' => $now,
        'composite_supplemental_score' => $composite,
        'dimensions' => array(
            'options_flow' => $options,
            'short_interest' => $short,
            'technical' => $technical,
            'earnings_quality' => $earnings
        )
    );
    
    echo json_encode($result);
    exit;
}

// ── Admin: Calculate and store all tickers ──
if ($action === 'calculate_all' && $admin) {
    $tickers = array('AAPL','MSFT','GOOGL','AMZN','NVDA','META','JPM','WMT','XOM','NFLX','JNJ','BAC');
    $processed = 0;
    $errors = array();
    
    foreach ($tickers as $t) {
        try {
            $options = calc_options_score($conn, $t, $POLYGON_API_KEY);
            $short = calc_short_interest_score($conn, $t, $FMP_API_KEY);
            $technical = calc_technical_score($conn, $t);
            $earnings = calc_earnings_quality_score($conn, $t, $FMP_API_KEY);
            
            $composite = _sd_clamp(
                $options['score'] * 0.25 +
                $short['score'] * 0.25 +
                $technical['score'] * 0.25 +
                $earnings['score'] * 0.25
            );
            
            $detail = json_encode(array(
                'options' => $options,
                'short' => $short,
                'technical' => $technical,
                'earnings' => $earnings
            ));
            
            $t_esc = _sd_esc($conn, $t);
            $d_esc = _sd_esc($conn, $detail);
            
            $conn->query("INSERT INTO lm_supplemental_dimensions 
                (ticker, calc_date, options_score, short_interest_score, technical_score, earnings_quality_score, 
                 composite_supplemental, detail_json, created_at)
                VALUES ('$t_esc', CURDATE(), {$options['score']}, {$short['score']}, {$technical['score']}, {$earnings['score']}, 
                        $composite, '$d_esc', '$now')
                ON DUPLICATE KEY UPDATE 
                options_score = VALUES(options_score),
                short_interest_score = VALUES(short_interest_score),
                technical_score = VALUES(technical_score),
                earnings_quality_score = VALUES(earnings_quality_score),
                composite_supplemental = VALUES(composite_supplemental),
                detail_json = VALUES(detail_json),
                created_at = VALUES(created_at)");
            
            $processed++;
            
        } catch (Exception $e) {
            $errors[] = $t . ': ' . $e->getMessage();
        }
        
        // Rate limiting - be nice to APIs
        usleep(500000); // 0.5 second delay
    }
    
    echo json_encode(array(
        'ok' => true,
        'processed' => $processed,
        'errors' => $errors,
        'timestamp' => $now
    ));
    exit;
}

// ── Default: Help ──
echo json_encode(array(
    'ok' => true,
    'message' => 'Supplemental Dimensions API',
    'usage' => array(
        'single_dimensions' => array(
            '?action=options&ticker=AAPL' => 'Options flow score',
            '?action=short&ticker=AAPL' => 'Short interest score',
            '?action=technical&ticker=AAPL' => 'Technical score',
            '?action=earnings&ticker=AAPL' => 'Earnings quality score'
        ),
        'combined' => array(
            '?action=all&ticker=AAPL' => 'All 4 supplemental dimensions'
        ),
        'admin' => array(
            '?action=calculate_all&key=livetrader2026' => 'Batch calculate all tickers'
        )
    ),
    'data_sources' => array(
        'options' => 'Massive (formerly Polygon.io, free tier) + Yahoo Finance scrape',
        'short_interest' => 'Financial Modeling Prep (free tier) + Yahoo scrape',
        'technical' => 'Calculated from your existing daily_prices table',
        'earnings' => 'FMP (free tier) + your existing stock_earnings table'
    ),
    'note' => 'Set FMP_API_KEY and POLYGON_API_KEY in db_config.php for best results'
));
exit;
?>
