<?php
/**
 * Multi-Exchange Price Validation System for Meme Coin Trading Assistant
 * 
 * Features:
 * - Multi-exchange failover: Kraken → Binance → Coinbase → CoinGecko
 * - Price anomaly detection (>2% spread triggers warning + median fallback)
 * - Rate limiting with automatic backoff on 429 errors
 * - 30-second file-based caching
 * - Health check endpoint for exchange status
 * 
 * PHP 5.2+ compatible
 */

// Error handling
error_reporting(0);
ini_set('display_errors', '0');

// Configuration
define('MXP_CACHE_DIR', dirname(__FILE__) . '/../../tmp');
define('MXP_CACHE_TTL', 30); // 30 seconds
define('MXP_ANOMALY_THRESHOLD', 0.02); // 2% spread threshold
define('MXP_LOG_FILE', dirname(__FILE__) . '/../../tmp/multi_exchange_log.txt');

// Ensure cache directory exists
if (!is_dir(MXP_CACHE_DIR)) {
    @mkdir(MXP_CACHE_DIR, 0755, true);
}

/**
 * MultiExchangePriceAggregator Class
 * Aggregates prices from multiple exchanges with failover and anomaly detection
 */
class MultiExchangePriceAggregator
{
    private $exchanges;
    private $rateLimits;
    private $anomalies;
    private $lastErrors;
    
    // Exchange priority order (lower = tried first)
    private $exchangePriority = array('kraken', 'binance', 'coinbase', 'coingecko');
    
    // Rate limit configuration (requests per minute)
    private $rateLimitConfig = array(
        'kraken' => array('calls' => 0, 'window_start' => 0, 'max_per_min' => 60),
        'binance' => array('calls' => 0, 'window_start' => 0, 'max_per_min' => 1200),
        'coinbase' => array('calls' => 0, 'window_start' => 0, 'max_per_min' => 6000), // 100/sec = 6000/min
        'coingecko' => array('calls' => 0, 'window_start' => 0, 'max_per_min' => 30)
    );
    
    // Backoff tracking
    private $backoffUntil = array(
        'kraken' => 0,
        'binance' => 0,
        'coinbase' => 0,
        'coingecko' => 0
    );
    
    /**
     * Constructor - load state from cache if available
     */
    public function __construct()
    {
        $this->exchanges = array();
        $this->anomalies = array();
        $this->lastErrors = array();
        $this->loadState();
    }
    
    /**
     * Get price for a symbol with automatic failover
     * 
     * @param string $symbol Base symbol (e.g., 'BTC', 'PEPE')
     * @param string $quote Quote currency (default: 'USDT')
     * @return array Price data or null on failure
     */
    public function getPrice($symbol, $quote = 'USDT')
    {
        $symbol = strtoupper(trim($symbol));
        $quote = strtoupper(trim($quote));
        $cacheKey = $symbol . '_' . $quote;
        
        // Check cache first
        $cached = $this->getFromCache($cacheKey);
        if ($cached) {
            $cached['cached'] = true;
            return $cached;
        }
        
        $startTime = microtime(true);
        $allResults = array();
        $errors = array();
        
        // Try each exchange in priority order
        foreach ($this->exchangePriority as $exchangeName) {
            // Skip if in backoff period
            if (time() < $this->backoffUntil[$exchangeName]) {
                $errors[] = $exchangeName . ': in backoff until ' . date('H:i:s', $this->backoffUntil[$exchangeName]);
                continue;
            }
            
            // Check rate limits
            if ($this->isRateLimited($exchangeName)) {
                $errors[] = $exchangeName . ': rate limited';
                continue;
            }
            
            $exchangeStart = microtime(true);
            $result = $this->fetchFromExchange($exchangeName, $symbol, $quote);
            $latency = round(microtime(true) - $exchangeStart, 3);
            
            if ($result) {
                $this->recordCall($exchangeName);
                $result['latency'] = $latency;
                $result['exchange'] = $exchangeName;
                $allResults[$exchangeName] = $result;
                
                // If this is the primary exchange, we can potentially return early
                // But we still want to check other sources for anomaly detection
                if ($exchangeName === 'kraken') {
                    // Continue to fetch from others for validation
                }
            } else {
                $errors[] = $exchangeName . ': fetch failed';
            }
        }
        
        // If we have no results, return null
        if (empty($allResults)) {
            $this->logError('All exchanges failed for ' . $symbol . ': ' . implode(', ', $errors));
            return null;
        }
        
        // Detect anomalies and calculate consensus price
        $processed = $this->processResults($symbol, $allResults);
        $processed['total_latency'] = round(microtime(true) - $startTime, 3);
        $processed['errors'] = $errors;
        
        // Cache the result
        $this->saveToCache($cacheKey, $processed);
        
        return $processed;
    }
    
    /**
     * Get best price weighted by volume across all exchanges
     * 
     * @param string $symbol Base symbol (e.g., 'BTC')
     * @return array Weighted price data
     */
    public function getBestPrice($symbol)
    {
        $result = $this->getPrice($symbol, 'USDT');
        
        if (!$result || !isset($result['all_sources'])) {
            return null;
        }
        
        $totalVolume = 0;
        $volumePriceSum = 0;
        $validSources = 0;
        
        foreach ($result['all_sources'] as $source => $data) {
            if (isset($data['volume_24h']) && $data['volume_24h'] > 0 && isset($data['price'])) {
                $totalVolume += $data['volume_24h'];
                $volumePriceSum += ($data['price'] * $data['volume_24h']);
                $validSources++;
            }
        }
        
        if ($totalVolume > 0) {
            $weightedPrice = $volumePriceSum / $totalVolume;
            return array(
                'symbol' => $symbol,
                'price' => round($weightedPrice, 10),
                'source' => 'volume_weighted',
                'sources_used' => $validSources,
                'total_volume_24h' => $totalVolume,
                'timestamp' => time(),
                'raw_data' => $result
            );
        }
        
        // Fallback to median if no volume data
        return array(
            'symbol' => $symbol,
            'price' => $result['price'],
            'source' => 'median_fallback',
            'timestamp' => time(),
            'raw_data' => $result
        );
    }
    
    /**
     * Get health status of all exchanges
     * 
     * @return array Health status for each exchange
     */
    public function getExchangeHealth()
    {
        $health = array();
        
        foreach ($this->exchangePriority as $exchangeName) {
            $status = 'unknown';
            $latency = null;
            $lastError = isset($this->lastErrors[$exchangeName]) ? $this->lastErrors[$exchangeName] : null;
            
            // Quick ping test
            $testStart = microtime(true);
            $testResult = $this->pingExchange($exchangeName);
            $latency = round((microtime(true) - $testStart) * 1000, 1); // ms
            
            if ($testResult) {
                $status = 'healthy';
            } else {
                $status = 'down';
                if (time() < $this->backoffUntil[$exchangeName]) {
                    $status = 'backoff';
                }
            }
            
            $health[$exchangeName] = array(
                'status' => $status,
                'latency_ms' => $latency,
                'rate_limit' => $this->rateLimitConfig[$exchangeName],
                'backoff_until' => $this->backoffUntil[$exchangeName] > time() ? $this->backoffUntil[$exchangeName] : null,
                'last_error' => $lastError
            );
        }
        
        return array(
            'timestamp' => time(),
            'exchanges' => $health,
            'overall_status' => $this->calculateOverallHealth($health)
        );
    }
    
    /**
     * Get detected price anomalies
     * 
     * @return array List of anomalies
     */
    public function getAnomalies()
    {
        // Clean old anomalies (> 1 hour)
        $cutoff = time() - 3600;
        $this->anomalies = array_filter($this->anomalies, create_function('$a', 'return $a["timestamp"] > ' . $cutoff . ';'));
        
        return array(
            'count' => count($this->anomalies),
            'anomalies' => array_values($this->anomalies),
            'threshold_percent' => MXP_ANOMALY_THRESHOLD * 100
        );
    }
    
    /**
     * Fetch price from specific exchange
     * 
     * @param string $exchange Exchange name
     * @param string $symbol Symbol
     * @param string $quote Quote currency
     * @return array Price data or null
     */
    private function fetchFromExchange($exchange, $symbol, $quote)
    {
        switch ($exchange) {
            case 'kraken':
                return $this->fetchKraken($symbol, $quote);
            case 'binance':
                return $this->fetchBinance($symbol, $quote);
            case 'coinbase':
                return $this->fetchCoinbase($symbol, $quote);
            case 'coingecko':
                return $this->fetchCoinGecko($symbol, $quote);
            default:
                return null;
        }
    }
    
    /**
     * Fetch from Kraken API
     */
    private function fetchKraken($symbol, $quote)
    {
        // Kraken uses XBT for BTC, XDG for DOGE
        $krakenSymbols = array(
            'BTC' => 'XBT',
            'DOGE' => 'XDG'
        );
        
        $krakenSymbol = isset($krakenSymbols[$symbol]) ? $krakenSymbols[$symbol] : $symbol;
        $pair = $krakenSymbol . $quote;
        
        // Try with USD if USDT fails
        $pairsToTry = array($pair);
        if ($quote === 'USDT') {
            $pairsToTry[] = $krakenSymbol . 'USD';
        }
        
        foreach ($pairsToTry as $tryPair) {
            $url = 'https://api.kraken.com/0/public/Ticker?pair=' . urlencode($tryPair);
            $resp = $this->httpGet($url);
            
            if (!$resp) continue;
            
            $data = json_decode($resp, true);
            if (!$data || (isset($data['error']) && !empty($data['error']))) continue;
            if (!isset($data['result']) || empty($data['result'])) continue;
            
            // Get first result
            $ticker = null;
            foreach ($data['result'] as $key => $val) {
                $ticker = $val;
                break;
            }
            
            if (!$ticker) continue;
            
            $price = isset($ticker['c'][0]) ? floatval($ticker['c'][0]) : 0;
            if ($price <= 0) continue;
            
            $volume = isset($ticker['v'][1]) ? floatval($ticker['v'][1]) : 0;
            $high = isset($ticker['h'][1]) ? floatval($ticker['h'][1]) : 0;
            $low = isset($ticker['l'][1]) ? floatval($ticker['l'][1]) : 0;
            
            return array(
                'price' => $price,
                'volume_24h' => $volume,
                'high_24h' => $high,
                'low_24h' => $low,
                'timestamp' => time()
            );
        }
        
        return null;
    }
    
    /**
     * Fetch from Binance API
     */
    private function fetchBinance($symbol, $quote)
    {
        $pair = $symbol . $quote;
        $url = 'https://api.binance.com/api/v3/ticker/24hr?symbol=' . urlencode($pair);
        
        $resp = $this->httpGet($url);
        
        if (!$resp) {
            return null;
        }
        
        $data = json_decode($resp, true);
        if (!$data || !isset($data['lastPrice'])) {
            return null;
        }
        
        $price = floatval($data['lastPrice']);
        if ($price <= 0) {
            return null;
        }
        
        return array(
            'price' => $price,
            'volume_24h' => isset($data['quoteVolume']) ? floatval($data['quoteVolume']) : 0,
            'high_24h' => isset($data['highPrice']) ? floatval($data['highPrice']) : 0,
            'low_24h' => isset($data['lowPrice']) ? floatval($data['lowPrice']) : 0,
            'change_24h' => isset($data['priceChangePercent']) ? floatval($data['priceChangePercent']) : 0,
            'timestamp' => time()
        );
    }
    
    /**
     * Fetch from Coinbase API
     */
    private function fetchCoinbase($symbol, $quote)
    {
        // Coinbase uses exchange-rates endpoint
        $url = 'https://api.coinbase.com/v2/exchange-rates?currency=' . urlencode($symbol);
        
        $resp = $this->httpGet($url);
        
        if (!$resp) {
            return null;
        }
        
        $data = json_decode($resp, true);
        if (!$data || !isset($data['data']['rates'][$quote])) {
            // Try USD if USDT not available
            if ($quote === 'USDT' && isset($data['data']['rates']['USD'])) {
                $quote = 'USD';
            } else {
                return null;
            }
        }
        
        $rate = floatval($data['data']['rates'][$quote]);
        if ($rate <= 0) {
            return null;
        }
        
        // Coinbase doesn't give us volume, return basic data
        return array(
            'price' => 1 / $rate, // Invert since rate is quote per base
            'volume_24h' => 0, // Not available
            'high_24h' => 0,
            'low_24h' => 0,
            'timestamp' => time()
        );
    }
    
    /**
     * Fetch from CoinGecko API
     */
    private function fetchCoinGecko($symbol, $quote)
    {
        // Map common symbols to CoinGecko IDs
        $cgIds = array(
            'BTC' => 'bitcoin',
            'ETH' => 'ethereum',
            'DOGE' => 'dogecoin',
            'SHIB' => 'shiba-inu',
            'PEPE' => 'pepe',
            'FLOKI' => 'floki',
            'BONK' => 'bonk',
            'WIF' => 'dogwifhat',
            'MOG' => 'mog-coin',
            'POPCAT' => 'popcat',
            'BRETT' => 'brett',
            'TURBO' => 'turbo',
            'NEIRO' => 'neiro-3',
            'PNUT' => 'peanut-the-squirrel',
            'GOAT' => 'goatseus-maximus',
            'MEME' => 'memecoin-2',
            'MYRO' => 'myro',
            'MOODENG' => 'moo-deng',
            'ACT' => 'act-i-the-ai-prophecy',
            'SPX' => 'spx6900',
            'GIGA' => 'gigachad-2',
            'PONKE' => 'ponke',
            'FWOG' => 'fwog',
            'SLERF' => 'slerf',
            'BOME' => 'book-of-meme',
            'WOJAK' => 'wojak',
            'COQ' => 'coq-inu',
            'TOSHI' => 'toshi',
            'LADYS' => 'milady-meme-coin',
            'TRUMP' => 'official-trump',
            'DEGEN' => 'degen-base',
            'HIGHER' => 'higher',
            'ANDY' => 'andy-on-base',
            'BABYDOGE' => 'baby-doge-coin',
            'KISHU' => 'kishu-inu',
            'SATS' => '1000sats',
            'ORDI' => 'ordinals',
            'RATS' => 'rats',
            'DOG' => 'dog-go-to-the-moon-runes',
            'PORK' => 'pepefork',
            'CATDOG' => 'catdog',
            'MICHI' => 'michi',
            'MEW' => 'cat-in-a-dogs-world',
            'WEN' => 'wen-4',
            'BODEN' => 'jeo-boden',
            'TREMP' => 'doland-tremp',
            'CHAD' => 'chad-index',
            'AI16Z' => 'ai16z',
            'GRIFFAIN' => 'griffain',
            'PENGU' => 'pudgy-penguins',
            'VIRTUAL' => 'virtual-protocol',
            'FARTCOIN' => 'fartcoin',
            'CHILLGUY' => 'just-a-chill-guy'
        );
        
        $cgId = isset($cgIds[$symbol]) ? $cgIds[$symbol] : strtolower($symbol);
        $vsCurrency = strtolower($quote);
        
        $url = 'https://api.coingecko.com/api/v3/simple/price?ids=' . urlencode($cgId) . 
               '&vs_currencies=' . urlencode($vsCurrency) . 
               '&include_24hr_vol=true&include_24hr_change=true';
        
        $resp = $this->httpGet($url);
        
        if (!$resp) {
            return null;
        }
        
        $data = json_decode($resp, true);
        if (!$data || !is_array($data) || empty($data)) {
            return null;
        }
        
        // Get first coin data
        $coinData = null;
        foreach ($data as $key => $val) {
            $coinData = $val;
            break;
        }
        
        if (!$coinData || !isset($coinData[$vsCurrency])) {
            return null;
        }
        
        $price = floatval($coinData[$vsCurrency]);
        if ($price <= 0) {
            return null;
        }
        
        return array(
            'price' => $price,
            'volume_24h' => isset($coinData[$vsCurrency . '_24h_vol']) ? floatval($coinData[$vsCurrency . '_24h_vol']) : 0,
            'change_24h' => isset($coinData[$vsCurrency . '_24h_change']) ? floatval($coinData[$vsCurrency . '_24h_change']) : 0,
            'high_24h' => 0,
            'low_24h' => 0,
            'timestamp' => time()
        );
    }
    
    /**
     * Process results from multiple exchanges
     * Detect anomalies and calculate consensus price
     */
    private function processResults($symbol, $results)
    {
        $prices = array();
        $allSources = array();
        
        foreach ($results as $exchange => $data) {
            $prices[$exchange] = $data['price'];
            $allSources[$exchange] = array(
                'price' => $data['price'],
                'latency' => isset($data['latency']) ? $data['latency'] : 0,
                'volume_24h' => isset($data['volume_24h']) ? $data['volume_24h'] : 0
            );
        }
        
        // Calculate spread
        $minPrice = min($prices);
        $maxPrice = max($prices);
        $spread = $maxPrice - $minPrice;
        $spreadPercent = ($minPrice > 0) ? ($spread / $minPrice) : 0;
        
        // Determine final price
        $finalPrice = null;
        $source = null;
        $anomalyDetected = false;
        
        if ($spreadPercent > MXP_ANOMALY_THRESHOLD) {
            // Anomaly detected - use median price
            $sortedPrices = $prices;
            sort($sortedPrices);
            $count = count($sortedPrices);
            
            if ($count % 2 === 0) {
                $finalPrice = ($sortedPrices[$count / 2 - 1] + $sortedPrices[$count / 2]) / 2;
            } else {
                $finalPrice = $sortedPrices[floor($count / 2)];
            }
            
            $source = 'median';
            $anomalyDetected = true;
            
            // Log anomaly
            $this->logAnomaly($symbol, $prices, $spreadPercent);
            $this->logError('PRICE ANOMALY: ' . $symbol . ' spread ' . round($spreadPercent * 100, 2) . '%');
        } else {
            // Use primary exchange (kraken) if available, otherwise first result
            if (isset($prices['kraken'])) {
                $finalPrice = $prices['kraken'];
                $source = 'kraken';
            } else {
                $firstKey = null;
                foreach ($prices as $key => $val) {
                    $firstKey = $key;
                    break;
                }
                $finalPrice = $prices[$firstKey];
                $source = $firstKey;
            }
        }
        
        return array(
            'symbol' => $symbol,
            'price' => round($finalPrice, 10),
            'source' => $source,
            'timestamp' => time(),
            'all_sources' => $allSources,
            'spread_percent' => round($spreadPercent, 6),
            'anomaly_detected' => $anomalyDetected,
            'price_range' => array(
                'min' => $minPrice,
                'max' => $maxPrice
            )
        );
    }
    
    /**
     * HTTP GET request with error handling
     */
    private function httpGet($url)
    {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'MultiExchangeAggregator/1.0');
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        
        $resp = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        // Handle rate limiting (429) or server errors (5xx)
        if ($httpCode === 429) {
            $this->handleRateLimit($url);
            return null;
        }
        
        if ($httpCode < 200 || $httpCode >= 300) {
            return null;
        }
        
        if (!$resp) {
            return null;
        }
        
        return $resp;
    }
    
    /**
     * Handle rate limit response - implement backoff
     */
    private function handleRateLimit($url)
    {
        // Determine which exchange from URL
        $exchange = null;
        if (strpos($url, 'kraken') !== false) {
            $exchange = 'kraken';
        } elseif (strpos($url, 'binance') !== false) {
            $exchange = 'binance';
        } elseif (strpos($url, 'coinbase') !== false) {
            $exchange = 'coinbase';
        } elseif (strpos($url, 'coingecko') !== false) {
            $exchange = 'coingecko';
        }
        
        if ($exchange) {
            // Exponential backoff: 60 seconds
            $this->backoffUntil[$exchange] = time() + 60;
            $this->logError('Rate limited on ' . $exchange . ', backing off for 60s');
            $this->lastErrors[$exchange] = 'Rate limited at ' . date('Y-m-d H:i:s');
            $this->saveState();
        }
    }
    
    /**
     * Check if exchange is currently rate limited
     */
    private function isRateLimited($exchange)
    {
        $config = $this->rateLimitConfig[$exchange];
        
        // Reset window if expired
        if (time() - $config['window_start'] > 60) {
            $this->rateLimitConfig[$exchange]['calls'] = 0;
            $this->rateLimitConfig[$exchange]['window_start'] = time();
            return false;
        }
        
        // Check if over limit
        if ($config['calls'] >= $config['max_per_min']) {
            return true;
        }
        
        return false;
    }
    
    /**
     * Record an API call for rate limiting
     */
    private function recordCall($exchange)
    {
        $this->rateLimitConfig[$exchange]['calls']++;
        $this->saveState();
    }
    
    /**
     * Quick ping test for health check
     */
    private function pingExchange($exchange)
    {
        switch ($exchange) {
            case 'kraken':
                $url = 'https://api.kraken.com/0/public/Time';
                break;
            case 'binance':
                $url = 'https://api.binance.com/api/v3/ping';
                break;
            case 'coinbase':
                $url = 'https://api.coinbase.com/v2/time';
                break;
            case 'coingecko':
                $url = 'https://api.coingecko.com/api/v3/ping';
                break;
            default:
                return false;
        }
        
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 5);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_USERAGENT, 'MultiExchangeHealthCheck/1.0');
        
        $resp = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        return ($resp && $httpCode >= 200 && $httpCode < 300);
    }
    
    /**
     * Calculate overall health status
     */
    private function calculateOverallHealth($health)
    {
        $healthy = 0;
        $total = count($health);
        
        foreach ($health as $ex) {
            if ($ex['status'] === 'healthy') {
                $healthy++;
            }
        }
        
        if ($healthy === $total) {
            return 'healthy';
        } elseif ($healthy >= $total / 2) {
            return 'degraded';
        } else {
            return 'critical';
        }
    }
    
    /**
     * Log an anomaly
     */
    private function logAnomaly($symbol, $prices, $spreadPercent)
    {
        $this->anomalies[] = array(
            'symbol' => $symbol,
            'prices' => $prices,
            'spread_percent' => round($spreadPercent * 100, 2),
            'timestamp' => time(),
            'datetime' => gmdate('Y-m-d H:i:s') . ' UTC'
        );
        
        // Keep only last 100 anomalies
        if (count($this->anomalies) > 100) {
            array_shift($this->anomalies);
        }
        
        $this->saveState();
    }
    
    /**
     * Log error to file
     */
    private function logError($message)
    {
        $line = gmdate('Y-m-d H:i:s') . ' UTC | ' . $message . "\n";
        @file_put_contents(MXP_LOG_FILE, $line, FILE_APPEND | LOCK_EX);
    }
    
    /**
     * Get from cache
     */
    private function getFromCache($key)
    {
        $cacheFile = MXP_CACHE_DIR . '/mxp_' . md5($key) . '.json';
        
        if (!file_exists($cacheFile)) {
            return null;
        }
        
        $age = time() - filemtime($cacheFile);
        if ($age > MXP_CACHE_TTL) {
            return null;
        }
        
        $data = @file_get_contents($cacheFile);
        if (!$data) {
            return null;
        }
        
        $decoded = json_decode($data, true);
        if (!$decoded) {
            return null;
        }
        
        $decoded['cache_age'] = $age;
        return $decoded;
    }
    
    /**
     * Save to cache
     */
    private function saveToCache($key, $data)
    {
        $cacheFile = MXP_CACHE_DIR . '/mxp_' . md5($key) . '.json';
        @file_put_contents($cacheFile, json_encode($data), LOCK_EX);
    }
    
    /**
     * Load state from persistent storage
     */
    private function loadState()
    {
        $stateFile = MXP_CACHE_DIR . '/mxp_state.json';
        
        if (!file_exists($stateFile)) {
            return;
        }
        
        $data = @file_get_contents($stateFile);
        if (!$data) {
            return;
        }
        
        $state = json_decode($data, true);
        if (!$state) {
            return;
        }
        
        if (isset($state['rate_limits'])) {
            $this->rateLimitConfig = $state['rate_limits'];
        }
        if (isset($state['backoff'])) {
            $this->backoffUntil = $state['backoff'];
        }
        if (isset($state['anomalies'])) {
            $this->anomalies = $state['anomalies'];
        }
        if (isset($state['last_errors'])) {
            $this->lastErrors = $state['last_errors'];
        }
    }
    
    /**
     * Save state to persistent storage
     */
    private function saveState()
    {
        $stateFile = MXP_CACHE_DIR . '/mxp_state.json';
        
        $state = array(
            'rate_limits' => $this->rateLimitConfig,
            'backoff' => $this->backoffUntil,
            'anomalies' => $this->anomalies,
            'last_errors' => $this->lastErrors,
            'saved_at' => time()
        );
        
        @file_put_contents($stateFile, json_encode($state), LOCK_EX);
    }
}

// ═══════════════════════════════════════════════════════════════════════
//  API ENDPOINT HANDLING
//  Usage: ?action=get_price&symbol=BTC&quote=USDT
//         ?action=best_price&symbol=BTC
//         ?action=health
//         ?action=anomalies
// ═══════════════════════════════════════════════════════════════════════

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

$action = isset($_GET['action']) ? $_GET['action'] : 'get_price';
$aggregator = new MultiExchangePriceAggregator();

switch ($action) {
    case 'get_price':
        $symbol = isset($_GET['symbol']) ? strtoupper(trim($_GET['symbol'])) : '';
        $quote = isset($_GET['quote']) ? strtoupper(trim($_GET['quote'])) : 'USDT';
        
        if (!$symbol) {
            echo json_encode(array('ok' => false, 'error' => 'Missing symbol parameter'));
            exit;
        }
        
        $result = $aggregator->getPrice($symbol, $quote);
        
        if ($result) {
            echo json_encode(array('ok' => true, 'data' => $result));
        } else {
            echo json_encode(array(
                'ok' => false, 
                'error' => 'Failed to fetch price for ' . $symbol . '/' . $quote,
                'message' => 'All exchanges failed or returned invalid data'
            ));
        }
        break;
        
    case 'best_price':
        $symbol = isset($_GET['symbol']) ? strtoupper(trim($_GET['symbol'])) : '';
        
        if (!$symbol) {
            echo json_encode(array('ok' => false, 'error' => 'Missing symbol parameter'));
            exit;
        }
        
        $result = $aggregator->getBestPrice($symbol);
        
        if ($result) {
            echo json_encode(array('ok' => true, 'data' => $result));
        } else {
            echo json_encode(array(
                'ok' => false,
                'error' => 'Failed to fetch best price for ' . $symbol
            ));
        }
        break;
        
    case 'health':
        $health = $aggregator->getExchangeHealth();
        echo json_encode(array('ok' => true, 'data' => $health));
        break;
        
    case 'anomalies':
        $anomalies = $aggregator->getAnomalies();
        echo json_encode(array('ok' => true, 'data' => $anomalies));
        break;
        
    default:
        echo json_encode(array(
            'ok' => false,
            'error' => 'Unknown action: ' . $action,
            'valid_actions' => array('get_price', 'best_price', 'health', 'anomalies')
        ));
}
?>
