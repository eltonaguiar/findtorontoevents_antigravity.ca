<?php
/**
 * Etherscan API Wrapper for On-Chain Safety Analysis
 * Free tier: 5 calls/sec, up to 100,000 calls/day
 * 
 * Features:
 *   - Contract verification status
 *   - Contract source code
 *   - Transaction history
 *   - Token holder info
 *   - Contract ABI
 * 
 * PHP 5.2 compatible
 */

class EtherscanAPI {
    private $apiKey;
    private $baseUrl = 'https://api.etherscan.io/api';
    private $lastError = '';
    private $rateLimitDelay = 210000; // 210ms between calls (under 5/sec)
    private $lastCallTime = 0;
    
    // Chain configurations
    private $chains = array(
        'ethereum' => array(
            'baseUrl' => 'https://api.etherscan.io/api',
            'explorer' => 'https://etherscan.io'
        ),
        'bsc' => array(
            'baseUrl' => 'https://api.bscscan.com/api',
            'explorer' => 'https://bscscan.com'
        ),
        'polygon' => array(
            'baseUrl' => 'https://api.polygonscan.com/api',
            'explorer' => 'https://polygonscan.com'
        )
    );
    
    public function __construct($apiKey = '') {
        $this->apiKey = $apiKey;
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
     * Check if contract is verified on Etherscan
     * 
     * @param string $contractAddress Contract address
     * @param string $chain Chain name (ethereum, bsc, polygon)
     * @return array|false Verification info or false on error
     */
    public function getContractVerification($contractAddress, $chain = 'ethereum') {
        $this->rateLimit();
        
        $params = array(
            'module' => 'contract',
            'action' => 'getsourcecode',
            'address' => $this->normalizeAddress($contractAddress),
            'apikey' => $this->apiKey
        );
        
        $response = $this->makeRequest($params, $chain);
        
        if (!$response || $response['status'] !== '1' || !isset($response['result'][0])) {
            $this->lastError = isset($response['message']) ? $response['message'] : 'Unknown error';
            return false;
        }
        
        $result = $response['result'][0];
        
        return array(
            'is_verified' => !empty($result['SourceCode']) && $result['SourceCode'] !== '',
            'source_code' => isset($result['SourceCode']) ? $result['SourceCode'] : '',
            'abi' => isset($result['ABI']) ? $result['ABI'] : '',
            'contract_name' => isset($result['ContractName']) ? $result['ContractName'] : '',
            'compiler_version' => isset($result['CompilerVersion']) ? $result['CompilerVersion'] : '',
            'optimization_used' => isset($result['OptimizationUsed']) ? $result['OptimizationUsed'] : '',
            'runs' => isset($result['Runs']) ? $result['Runs'] : '',
            'license_type' => isset($result['LicenseType']) ? $result['LicenseType'] : '',
            'proxy' => isset($result['Proxy']) ? $result['Proxy'] : '0',
            'implementation' => isset($result['Implementation']) ? $result['Implementation'] : ''
        );
    }
    
    /**
     * Get token holder information
     * 
     * @param string $contractAddress Token contract address
     * @param string $chain Chain name
     * @return array|false Holder info or false on error
     */
    public function getTokenHolders($contractAddress, $chain = 'ethereum') {
        $this->rateLimit();
        
        $params = array(
            'module' => 'stats',
            'action' => 'tokenholderlist',
            'contractaddress' => $this->normalizeAddress($contractAddress),
            'page' => '1',
            'offset' => '100',
            'apikey' => $this->apiKey
        );
        
        $response = $this->makeRequest($params, $chain);
        
        if (!$response || $response['status'] !== '1') {
            // Try alternative: get token info
            return $this->getTokenInfo($contractAddress, $chain);
        }
        
        $holders = isset($response['result']) ? $response['result'] : array();
        
        return array(
            'holders' => $holders,
            'total_holders' => count($holders)
        );
    }
    
    /**
     * Get token info (name, symbol, supply)
     * 
     * @param string $contractAddress Token contract address
     * @param string $chain Chain name
     * @return array|false Token info or false on error
     */
    public function getTokenInfo($contractAddress, $chain = 'ethereum') {
        $this->rateLimit();
        
        $normalizedAddress = $this->normalizeAddress($contractAddress);
        
        // Get token supply
        $supplyParams = array(
            'module' => 'stats',
            'action' => 'tokensupply',
            'contractaddress' => $normalizedAddress,
            'apikey' => $this->apiKey
        );
        
        $supplyResponse = $this->makeRequest($supplyParams, $chain);
        
        // This endpoint works differently, try token info via proxy
        $info = array(
            'address' => $normalizedAddress,
            'total_supply' => ($supplyResponse && isset($supplyResponse['result'])) ? $supplyResponse['result'] : '0'
        );
        
        return $info;
    }
    
    /**
     * Get contract transaction history
     * 
     * @param string $contractAddress Contract address
     * @param int $limit Number of transactions to fetch
     * @param string $chain Chain name
     * @return array|false Transaction list or false on error
     */
    public function getTransactions($contractAddress, $limit = 50, $chain = 'ethereum') {
        $this->rateLimit();
        
        $params = array(
            'module' => 'account',
            'action' => 'txlist',
            'address' => $this->normalizeAddress($contractAddress),
            'startblock' => '0',
            'endblock' => '99999999',
            'page' => '1',
            'offset' => (string)$limit,
            'sort' => 'desc',
            'apikey' => $this->apiKey
        );
        
        $response = $this->makeRequest($params, $chain);
        
        if (!$response || $response['status'] !== '1') {
            $this->lastError = isset($response['message']) ? $response['message'] : 'No transactions found';
            return false;
        }
        
        return isset($response['result']) ? $response['result'] : array();
    }
    
    /**
     * Get internal transactions (contract calls)
     * 
     * @param string $contractAddress Contract address
     * @param int $limit Number of transactions
     * @param string $chain Chain name
     * @return array|false Internal transactions or false on error
     */
    public function getInternalTransactions($contractAddress, $limit = 50, $chain = 'ethereum') {
        $this->rateLimit();
        
        $params = array(
            'module' => 'account',
            'action' => 'txlistinternal',
            'address' => $this->normalizeAddress($contractAddress),
            'startblock' => '0',
            'endblock' => '99999999',
            'page' => '1',
            'offset' => (string)$limit,
            'sort' => 'desc',
            'apikey' => $this->apiKey
        );
        
        $response = $this->makeRequest($params, $chain);
        
        if (!$response || $response['status'] !== '1') {
            return array();
        }
        
        return isset($response['result']) ? $response['result'] : array();
    }
    
    /**
     * Check if address is a contract
     * 
     * @param string $address Address to check
     * @param string $chain Chain name
     * @return bool True if contract, false otherwise
     */
    public function isContract($address, $chain = 'ethereum') {
        $this->rateLimit();
        
        $params = array(
            'module' => 'proxy',
            'action' => 'eth_getCode',
            'address' => $this->normalizeAddress($address),
            'tag' => 'latest',
            'apikey' => $this->apiKey
        );
        
        $response = $this->makeRequest($params, $chain);
        
        if (!$response || !isset($response['result'])) {
            return false;
        }
        
        // If result is "0x" or empty, it's not a contract
        $code = $response['result'];
        return strlen($code) > 2 && $code !== '0x';
    }
    
    /**
     * Get token transfer events
     * 
     * @param string $contractAddress Token contract
     * @param int $limit Number of events
     * @param string $chain Chain name
     * @return array|false Transfer events or false on error
     */
    public function getTokenTransfers($contractAddress, $limit = 100, $chain = 'ethereum') {
        $this->rateLimit();
        
        $params = array(
            'module' => 'account',
            'action' => 'tokentx',
            'contractaddress' => $this->normalizeAddress($contractAddress),
            'page' => '1',
            'offset' => (string)$limit,
            'sort' => 'desc',
            'apikey' => $this->apiKey
        );
        
        $response = $this->makeRequest($params, $chain);
        
        if (!$response || $response['status'] !== '1') {
            return array();
        }
        
        return isset($response['result']) ? $response['result'] : array();
    }
    
    /**
     * Analyze contract for dangerous functions
     * 
     * @param string $sourceCode Contract source code
     * @return array Analysis results
     */
    public function analyzeContractFunctions($sourceCode) {
        $result = array(
            'has_mint' => false,
            'has_blacklist' => false,
            'has_pause' => false,
            'has_ownership' => false,
            'ownership_renounced' => false,
            'has_hidden_mint' => false,
            'has_selfdestruct' => false,
            'dangerous_functions' => array()
        );
        
        if (empty($sourceCode)) {
            return $result;
        }
        
        $sourceLower = strtolower($sourceCode);
        
        // Check for mint function
        if (preg_match('/function\s+(mint|_mint|mintTokens)/i', $sourceCode)) {
            $result['has_mint'] = true;
            $result['dangerous_functions'][] = 'mint';
        }
        
        // Check for blacklist function
        if (preg_match('/function\s+(blacklist|addBlacklist|setBlacklist|isBlacklisted)/i', $sourceCode)) {
            $result['has_blacklist'] = true;
            $result['dangerous_functions'][] = 'blacklist';
        }
        
        // Check for pause function
        if (preg_match('/function\s+(pause|unpause|paused|whenNotPaused)/i', $sourceCode)) {
            $result['has_pause'] = true;
            $result['dangerous_functions'][] = 'pause';
        }
        
        // Check for ownership patterns
        if (preg_match('/(Ownable|onlyOwner|transferOwnership|renounceOwnership)/i', $sourceCode)) {
            $result['has_ownership'] = true;
        }
        
        // Check for ownership renounced (look for patterns)
        if (preg_match('/(0x0000000000000000000000000000000000000000|renounceOwnership|OwnershipTransferred.*address\(0\))/i', $sourceCode)) {
            $result['ownership_renounced'] = true;
        }
        
        // Check for selfdestruct
        if (preg_match('/(selfdestruct|suicide)/i', $sourceCode)) {
            $result['has_selfdestruct'] = true;
            $result['dangerous_functions'][] = 'selfdestruct';
        }
        
        // Check for hidden mint (assembly)
        if (preg_match('/assembly\s*\{/s', $sourceCode) && preg_match('/(sstore|mstore)/i', $sourceCode)) {
            // This is a heuristic - assembly code could hide minting
            $result['has_hidden_mint'] = true;
            $result['dangerous_functions'][] = 'assembly_code';
        }
        
        return $result;
    }
    
    /**
     * Get explorer URL for address
     * 
     * @param string $address Contract address
     * @param string $chain Chain name
     * @return string Explorer URL
     */
    public function getExplorerUrl($address, $chain = 'ethereum') {
        if (!isset($this->chains[$chain])) {
            $chain = 'ethereum';
        }
        return $this->chains[$chain]['explorer'] . '/address/' . $this->normalizeAddress($address);
    }
    
    /**
     * Make HTTP request to Etherscan API
     * 
     * @param array $params Request parameters
     * @param string $chain Chain name
     * @return array|false Response or false on error
     */
    private function makeRequest($params, $chain = 'ethereum') {
        if (!isset($this->chains[$chain])) {
            $chain = 'ethereum';
        }
        
        $url = $this->chains[$chain]['baseUrl'] . '?' . http_build_query($params);
        
        $context = stream_context_create(array(
            'http' => array(
                'method' => 'GET',
                'header' => "User-Agent: Mozilla/5.0 (compatible; SafetyChecker/1.0)\r\n",
                'timeout' => 30,
                'ignore_errors' => true
            )
        ));
        
        $response = @file_get_contents($url, false, $context);
        
        if ($response === false) {
            $this->lastError = 'HTTP request failed';
            return false;
        }
        
        $data = json_decode($response, true);
        
        if ($data === null) {
            $this->lastError = 'Invalid JSON response';
            return false;
        }
        
        return $data;
    }
    
    /**
     * Rate limit requests to stay under free tier limits
     */
    private function rateLimit() {
        $now = microtime(true) * 1000000; // microseconds
        $elapsed = $now - $this->lastCallTime;
        
        if ($elapsed < $this->rateLimitDelay) {
            usleep($this->rateLimitDelay - $elapsed);
        }
        
        $this->lastCallTime = microtime(true) * 1000000;
    }
    
    /**
     * Normalize Ethereum address
     * 
     * @param string $address Address to normalize
     * @return string Normalized address
     */
    private function normalizeAddress($address) {
        $address = strtolower(trim($address));
        
        // Basic validation
        if (!preg_match('/^0x[a-f0-9]{40}$/', $address)) {
            // Try to clean it up
            $address = preg_replace('/[^a-f0-9x]/', '', $address);
        }
        
        return $address;
    }
}
?>
