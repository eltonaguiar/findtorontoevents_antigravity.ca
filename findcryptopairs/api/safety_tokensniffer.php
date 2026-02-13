<?php
/**
 * TokenSniffer API Wrapper for Token Safety Analysis
 * Free tier available with rate limits
 * 
 * Features:
 *   - Contract safety scores
 *   - Honeypot detection
 *   - Buy/sell tax detection
 *   - Liquidity analysis
 * 
 * PHP 5.2 compatible
 */

class TokenSnifferAPI {
    private $apiKey = '';
    private $baseUrl = 'https://tokensniffer.com/api/v2';
    private $lastError = '';
    private $cacheDir;
    private $cacheEnabled = true;
    private $rateLimitDelay = 1000000; // 1 second between calls for free tier
    private $lastCallTime = 0;
    
    // Chain IDs for TokenSniffer
    private $chainIds = array(
        'ethereum' => '1',
        'bsc' => '56',
        'polygon' => '137',
        'arbitrum' => '42161',
        'base' => '8453'
    );
    
    public function __construct($apiKey = '') {
        $this->apiKey = $apiKey;
        $this->cacheDir = dirname(__FILE__) . '/cache/safety';
        
        // Create cache directory if needed
        if (!is_dir($this->cacheDir)) {
            @mkdir($this->cacheDir, 0755, true);
        }
    }
    
    /**
     * Set API key
     */
    public function setApiKey($apiKey) {
        $this->apiKey = $apiKey;
    }
    
    /**
     * Get last error message
     */
    public function getLastError() {
        return $this->lastError;
    }
    
    /**
     * Enable/disable caching
     */
    public function setCacheEnabled($enabled) {
        $this->cacheEnabled = $enabled;
    }
    
    /**
     * Get token audit/safety report
     * 
     * @param string $contractAddress Token contract address
     * @param string $chain Chain name
     * @return array|false Safety report or false on error
     */
    public function getTokenAudit($contractAddress, $chain = 'ethereum') {
        $cacheKey = 'audit_' . $chain . '_' . strtolower($contractAddress);
        $cached = $this->getCache($cacheKey);
        
        if ($cached !== false) {
            return $cached;
        }
        
        $this->rateLimit();
        
        $chainId = isset($this->chainIds[$chain]) ? $this->chainIds[$chain] : '1';
        $normalizedAddress = $this->normalizeAddress($contractAddress);
        
        // TokenSniffer API v2 endpoint
        $url = $this->baseUrl . '/tokens/' . $chainId . '/' . $normalizedAddress;
        
        $headers = array(
            'User-Agent: Mozilla/5.0 (compatible; SafetyChecker/1.0)'
        );
        
        if (!empty($this->apiKey)) {
            $headers[] = 'X-API-KEY: ' . $this->apiKey;
        }
        
        $context = stream_context_create(array(
            'http' => array(
                'method' => 'GET',
                'header' => implode("\r\n", $headers),
                'timeout' => 30,
                'ignore_errors' => true
            )
        ));
        
        $response = @file_get_contents($url, false, $context);
        
        if ($response === false) {
            $this->lastError = 'TokenSniffer API request failed';
            return false;
        }
        
        $data = json_decode($response, true);
        
        if ($data === null) {
            $this->lastError = 'Invalid JSON response from TokenSniffer';
            return false;
        }
        
        // Check for API errors
        if (isset($data['error'])) {
            $this->lastError = $data['error'];
            return false;
        }
        
        $result = $this->parseTokenAudit($data);
        
        // Cache successful results
        $this->setCache($cacheKey, $result, 3600); // 1 hour cache
        
        return $result;
    }
    
    /**
     * Check if token is a honeypot (cannot sell)
     * 
     * @param string $contractAddress Token contract address
     * @param string $chain Chain name
     * @return array Honeypot check results
     */
    public function checkHoneypot($contractAddress, $chain = 'ethereum') {
        $audit = $this->getTokenAudit($contractAddress, $chain);
        
        if ($audit === false) {
            return array(
                'is_honeypot' => null,
                'error' => $this->lastError,
                'sell_enabled' => null,
                'buy_tax' => 0,
                'sell_tax' => 0
            );
        }
        
        return array(
            'is_honeypot' => $audit['is_honeypot'],
            'sell_enabled' => !$audit['is_honeypot'],
            'buy_tax' => $audit['buy_tax'],
            'sell_tax' => $audit['sell_tax'],
            'transfer_tax' => $audit['transfer_tax'],
            'slippage_warning' => ($audit['buy_tax'] > 5 || $audit['sell_tax'] > 5)
        );
    }
    
    /**
     * Get liquidity information
     * 
     * @param string $contractAddress Token contract address
     * @param string $chain Chain name
     * @return array Liquidity info
     */
    public function getLiquidityInfo($contractAddress, $chain = 'ethereum') {
        $audit = $this->getTokenAudit($contractAddress, $chain);
        
        if ($audit === false) {
            return array(
                'has_liquidity' => null,
                'liquidity_locked' => null,
                'liquidity_amount_usd' => 0,
                'lp_tokens_burned' => null,
                'error' => $this->lastError
            );
        }
        
        return array(
            'has_liquidity' => $audit['liquidity_usd'] > 0,
            'liquidity_amount_usd' => $audit['liquidity_usd'],
            'liquidity_locked' => $audit['liquidity_locked'],
            'lp_tokens_burned' => $audit['lp_burned'],
            'lock_duration_days' => $audit['lock_duration_days'],
            'dex' => $audit['dex']
        );
    }
    
    /**
     * Get holder distribution
     * 
     * @param string $contractAddress Token contract address
     * @param string $chain Chain name
     * @return array Holder distribution info
     */
    public function getHolderDistribution($contractAddress, $chain = 'ethereum') {
        $audit = $this->getTokenAudit($contractAddress, $chain);
        
        if ($audit === false || !isset($audit['holders'])) {
            return array(
                'total_holders' => 0,
                'top10_percent' => 0,
                'top5_percent' => 0,
                'top_holder_percent' => 0,
                'distribution_risk' => 'unknown'
            );
        }
        
        $holders = $audit['holders'];
        $totalHolders = count($holders);
        
        // Calculate concentrations
        $top10Percent = 0;
        $top5Percent = 0;
        $topHolderPercent = 0;
        
        if ($totalHolders > 0) {
            // Sort by percentage descending
            usort($holders, array($this, 'sortHoldersByPercent'));
            
            // Top holder
            $topHolderPercent = isset($holders[0]['percent']) ? $holders[0]['percent'] : 0;
            
            // Top 5
            for ($i = 0; $i < min(5, $totalHolders); $i++) {
                $top5Percent += isset($holders[$i]['percent']) ? $holders[$i]['percent'] : 0;
            }
            
            // Top 10
            for ($i = 0; $i < min(10, $totalHolders); $i++) {
                $top10Percent += isset($holders[$i]['percent']) ? $holders[$i]['percent'] : 0;
            }
        }
        
        // Determine risk level
        $distributionRisk = 'low';
        if ($topHolderPercent > 20 || $top5Percent > 50) {
            $distributionRisk = 'critical';
        } elseif ($topHolderPercent > 10 || $top5Percent > 30 || $top10Percent > 50) {
            $distributionRisk = 'high';
        } elseif ($top10Percent > 30) {
            $distributionRisk = 'medium';
        }
        
        return array(
            'total_holders' => $totalHolders,
            'top_holder_percent' => $topHolderPercent,
            'top5_percent' => $top5Percent,
            'top10_percent' => $top10Percent,
            'distribution_risk' => $distributionRisk,
            'holders' => array_slice($holders, 0, 10) // Top 10 details
        );
    }
    
    /**
     * Get quick safety score
     * 
     * @param string $contractAddress Token contract address
     * @param string $chain Chain name
     * @return array Quick score results
     */
    public function getQuickScore($contractAddress, $chain = 'ethereum') {
        $cacheKey = 'quick_' . $chain . '_' . strtolower($contractAddress);
        $cached = $this->getCache($cacheKey);
        
        if ($cached !== false) {
            return $cached;
        }
        
        $audit = $this->getTokenAudit($contractAddress, $chain);
        
        if ($audit === false) {
            return array(
                'score' => 0,
                'risk_level' => 'unknown',
                'error' => $this->lastError
            );
        }
        
        $result = array(
            'score' => $audit['overall_score'],
            'risk_level' => $this->scoreToRiskLevel($audit['overall_score']),
            'is_honeypot' => $audit['is_honeypot'],
            'has_mint' => $audit['can_mint'],
            'can_blacklist' => $audit['can_blacklist'],
            'has_proxy' => $audit['is_proxy'],
            'contract_verified' => $audit['verified']
        );
        
        $this->setCache($cacheKey, $result, 1800); // 30 min cache
        
        return $result;
    }
    
    /**
     * Parse TokenSniffer audit response
     */
    private function parseTokenAudit($data) {
        // Default values
        $result = array(
            'overall_score' => 0,
            'is_honeypot' => false,
            'can_mint' => false,
            'can_blacklist' => false,
            'can_pause' => false,
            'is_proxy' => false,
            'verified' => false,
            'buy_tax' => 0,
            'sell_tax' => 0,
            'transfer_tax' => 0,
            'liquidity_usd' => 0,
            'liquidity_locked' => false,
            'lp_burned' => false,
            'lock_duration_days' => 0,
            'dex' => '',
            'name' => '',
            'symbol' => '',
            'holders' => array(),
            'warnings' => array(),
            'red_flags' => array()
        );
        
        // Parse based on TokenSniffer API response format
        if (isset($data['score'])) {
            $result['overall_score'] = (int)$data['score'];
        }
        
        if (isset($data['name'])) {
            $result['name'] = $data['name'];
        }
        
        if (isset($data['symbol'])) {
            $result['symbol'] = $data['symbol'];
        }
        
        // Contract checks
        if (isset($data['checks'])) {
            $checks = $data['checks'];
            
            $result['is_honeypot'] = isset($checks['is_honeypot']) ? $checks['is_honeypot'] : false;
            $result['can_mint'] = isset($checks['can_mint']) ? $checks['can_mint'] : false;
            $result['can_blacklist'] = isset($checks['can_blacklist']) ? $checks['can_blacklist'] : false;
            $result['can_pause'] = isset($checks['can_pause']) ? $checks['can_pause'] : false;
            $result['is_proxy'] = isset($checks['is_proxy']) ? $checks['is_proxy'] : false;
            $result['verified'] = isset($checks['verified']) ? $checks['verified'] : false;
        }
        
        // Taxes
        if (isset($data['taxes'])) {
            $taxes = $data['taxes'];
            $result['buy_tax'] = isset($taxes['buy']) ? (float)$taxes['buy'] : 0;
            $result['sell_tax'] = isset($taxes['sell']) ? (float)$taxes['sell'] : 0;
            $result['transfer_tax'] = isset($taxes['transfer']) ? (float)$taxes['transfer'] : 0;
        }
        
        // Liquidity
        if (isset($data['liquidity'])) {
            $liq = $data['liquidity'];
            $result['liquidity_usd'] = isset($liq['usd']) ? (float)$liq['usd'] : 0;
            $result['liquidity_locked'] = isset($liq['locked']) ? $liq['locked'] : false;
            $result['lp_burned'] = isset($liq['burned']) ? $liq['burned'] : false;
            $result['lock_duration_days'] = isset($liq['lock_days']) ? (int)$liq['lock_days'] : 0;
            $result['dex'] = isset($liq['dex']) ? $liq['dex'] : '';
        }
        
        // Holders
        if (isset($data['holders']) && is_array($data['holders'])) {
            $result['holders'] = $data['holders'];
        }
        
        // Warnings and red flags
        if (isset($data['warnings']) && is_array($data['warnings'])) {
            $result['warnings'] = $data['warnings'];
        }
        
        if (isset($data['red_flags']) && is_array($data['red_flags'])) {
            $result['red_flags'] = $data['red_flags'];
        }
        
        return $result;
    }
    
    /**
     * Convert score to risk level
     */
    private function scoreToRiskLevel($score) {
        if ($score >= 80) return 'low';
        if ($score >= 60) return 'medium';
        if ($score >= 40) return 'high';
        return 'critical';
    }
    
    /**
     * Sort holders by percentage
     */
    private function sortHoldersByPercent($a, $b) {
        $pctA = isset($a['percent']) ? $a['percent'] : 0;
        $pctB = isset($b['percent']) ? $b['percent'] : 0;
        
        if ($pctA == $pctB) return 0;
        return ($pctA > $pctB) ? -1 : 1;
    }
    
    /**
     * Get cached data
     */
    private function getCache($key) {
        if (!$this->cacheEnabled) {
            return false;
        }
        
        $file = $this->cacheDir . '/' . $key . '.json';
        
        if (!file_exists($file)) {
            return false;
        }
        
        $data = @file_get_contents($file);
        
        if ($data === false) {
            return false;
        }
        
        $cached = json_decode($data, true);
        
        if ($cached === null || !isset($cached['expires']) || $cached['expires'] < time()) {
            @unlink($file);
            return false;
        }
        
        return $cached['data'];
    }
    
    /**
     * Set cached data
     */
    private function setCache($key, $data, $ttl = 3600) {
        if (!$this->cacheEnabled) {
            return;
        }
        
        $file = $this->cacheDir . '/' . $key . '.json';
        
        $cache = array(
            'expires' => time() + $ttl,
            'data' => $data
        );
        
        @file_put_contents($file, json_encode($cache), LOCK_EX);
    }
    
    /**
     * Rate limit requests
     */
    private function rateLimit() {
        $now = microtime(true) * 1000000;
        $elapsed = $now - $this->lastCallTime;
        
        if ($elapsed < $this->rateLimitDelay) {
            usleep($this->rateLimitDelay - $elapsed);
        }
        
        $this->lastCallTime = microtime(true) * 1000000;
    }
    
    /**
     * Normalize Ethereum address
     */
    private function normalizeAddress($address) {
        $address = strtolower(trim($address));
        $address = preg_replace('/[^a-f0-9x]/', '', $address);
        
        if (!preg_match('/^0x[a-f0-9]{40}$/', $address)) {
            return '';
        }
        
        return $address;
    }
}
?>
