<?php
/**
 * On-Chain Safety & Rug-Pull Detection System
 * Analyzes Ethereum/BSC/Polygon tokens for safety risks
 * 
 * Endpoints:
 *   ?action=analyze&address=0x...&chain=ethereum          - Full safety analysis
 *   ?action=quick&address=0x...&chain=ethereum            - Quick score only
 *   ?action=batch&addresses=0x...,0x...&chain=ethereum    - Batch analysis
 *   ?action=holders&address=0x...&chain=ethereum          - Holder distribution
 *   ?action=honeypot&address=0x...&chain=ethereum         - Honeypot check only
 *   ?action=health                                         - Service status
 * 
 * Risk Levels:
 *   80-100: LOW RISK (green)    - Safe to trade
 *   60-79:  MEDIUM RISK (yellow) - Exercise caution
 *   40-59:  HIGH RISK (orange)   - High chance of issues
 *   0-39:   CRITICAL RISK (red)  - Likely scam/rug
 * 
 * PHP 5.2 compatible
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

// Load dependencies
require_once dirname(__FILE__) . '/safety_etherscan.php';
require_once dirname(__FILE__) . '/safety_tokensniffer.php';

// Error handling
error_reporting(0);
ini_set('display_errors', '0');

// API Keys (should be configured via environment or config file)
$ETHERSCAN_API_KEY = isset($_ENV['ETHERSCAN_API_KEY']) ? $_ENV['ETHERSCAN_API_KEY'] : '';
$TOKENSNIFFER_API_KEY = isset($_ENV['TOKENSNIFFER_API_KEY']) ? $_ENV['TOKENSNIFFER_API_KEY'] : '';

// Try to load from .env file if present
$envFile = dirname(__FILE__) . '/.env';
if (file_exists($envFile)) {
    $envLines = file($envFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if ($envLines) {
        foreach ($envLines as $line) {
            if (strpos($line, '=') !== false && strpos($line, '#') !== 0) {
                list($key, $value) = explode('=', $line, 2);
                $key = trim($key);
                $value = trim($value);
                if ($key === 'ETHERSCAN_API_KEY') $ETHERSCAN_API_KEY = $value;
                if ($key === 'TOKENSNIFFER_API_KEY') $TOKENSNIFFER_API_KEY = $value;
            }
        }
    }
}

// Initialize APIs
$etherscan = new EtherscanAPI($ETHERSCAN_API_KEY);
$tokensniffer = new TokenSnifferAPI($TOKENSNIFFER_API_KEY);

// Cache configuration
$cacheDir = dirname(__FILE__) . '/cache/safety';
if (!is_dir($cacheDir)) {
    @mkdir($cacheDir, 0755, true);
}

// Get request parameters
$action = isset($_GET['action']) ? strtolower(trim($_GET['action'])) : 'analyze';
$address = isset($_GET['address']) ? trim($_GET['address']) : '';
$chain = isset($_GET['chain']) ? strtolower(trim($_GET['chain'])) : 'ethereum';
$addresses = isset($_GET['addresses']) ? trim($_GET['addresses']) : '';
$skipCache = isset($_GET['nocache']) && $_GET['nocache'] === '1';

// Validate chain
$validChains = array('ethereum', 'bsc', 'polygon', 'arbitrum', 'base');
if (!in_array($chain, $validChains)) {
    $chain = 'ethereum';
}

// Route to appropriate handler
switch ($action) {
    case 'analyze':
        echo json_encode(analyzeToken($address, $chain, $skipCache));
        break;
        
    case 'quick':
        echo json_encode(quickScore($address, $chain, $skipCache));
        break;
        
    case 'batch':
        echo json_encode(batchAnalyze($addresses, $chain, $skipCache));
        break;
        
    case 'holders':
        echo json_encode(getHolderAnalysis($address, $chain, $skipCache));
        break;
        
    case 'honeypot':
        echo json_encode(checkHoneypot($address, $chain, $skipCache));
        break;
        
    case 'health':
        echo json_encode(healthCheck());
        break;
        
    default:
        echo json_encode(array('ok' => false, 'error' => 'Unknown action: ' . $action));
}

/**
 * Full token safety analysis
 */
function analyzeToken($address, $chain, $skipCache = false) {
    global $etherscan, $tokensniffer, $cacheDir;
    
    // Validate address
    $validation = validateAddress($address);
    if (!$validation['valid']) {
        return array('ok' => false, 'error' => $validation['error']);
    }
    $address = $validation['normalized'];
    
    // Check cache
    $cacheKey = 'analyze_' . $chain . '_' . strtolower($address);
    if (!$skipCache) {
        $cached = getCache($cacheKey, $cacheDir);
        if ($cached !== false) {
            $cached['cached'] = true;
            return $cached;
        }
    }
    
    // Initialize result
    $result = array(
        'ok' => true,
        'contract_address' => $address,
        'chain' => $chain,
        'token_name' => '',
        'token_symbol' => '',
        'safety_score' => 0,
        'risk_level' => 'unknown',
        'risk_color' => 'gray',
        'checks' => array(),
        'red_flags' => array(),
        'warnings' => array(),
        'holder_stats' => array(),
        'liquidity_info' => array(),
        'contract_analysis' => array(),
        'tax_info' => array(),
        'recommendation' => '',
        'explorer_url' => $etherscan->getExplorerUrl($address, $chain),
        'timestamp' => time()
    );
    
    // Track score breakdown
    $scores = array(
        'contract' => 0,
        'liquidity' => 0,
        'holders' => 0,
        'transaction' => 0
    );
    
    // ========== 1. Contract Safety Analysis (40 points) ==========
    $contractVerified = false;
    $sourceCode = '';
    $contractAnalysis = array();
    
    // Try Etherscan for contract info
    $contractInfo = $etherscan->getContractVerification($address, $chain);
    
    if ($contractInfo !== false) {
        $contractVerified = $contractInfo['is_verified'];
        $sourceCode = $contractInfo['source_code'];
        
        $result['token_name'] = $contractInfo['contract_name'];
        
        if ($contractVerified) {
            $scores['contract'] += 10;
            $result['checks']['contract_verified'] = true;
            
            // Analyze contract functions
            $contractAnalysis = $etherscan->analyzeContractFunctions($sourceCode);
            $result['contract_analysis'] = $contractAnalysis;
            
            // Check mint function
            if (!$contractAnalysis['has_mint'] || $contractAnalysis['ownership_renounced']) {
                $scores['contract'] += 10;
                $result['checks']['mint_renounced'] = true;
            } else {
                $result['checks']['mint_renounced'] = false;
                $result['red_flags'][] = 'Contract has mint function and ownership not renounced';
            }
            
            // Check blacklist
            if (!$contractAnalysis['has_blacklist']) {
                $scores['contract'] += 10;
                $result['checks']['no_blacklist'] = true;
            } else {
                $result['checks']['no_blacklist'] = false;
                $result['red_flags'][] = 'Contract has blacklist function';
            }
            
            // Source code available (already verified)
            $scores['contract'] += 10;
            $result['checks']['source_available'] = true;
            
        } else {
            $result['checks']['contract_verified'] = false;
            $result['checks']['mint_renounced'] = null;
            $result['checks']['no_blacklist'] = null;
            $result['checks']['source_available'] = false;
            $result['red_flags'][] = 'Contract not verified on Etherscan';
        }
    } else {
        // Try TokenSniffer as fallback
        $tsAudit = $tokensniffer->getTokenAudit($address, $chain);
        
        if ($tsAudit !== false) {
            $result['token_name'] = $tsAudit['name'];
            $result['token_symbol'] = $tsAudit['symbol'];
            
            if ($tsAudit['verified']) {
                $scores['contract'] += 10;
                $result['checks']['contract_verified'] = true;
            } else {
                $result['checks']['contract_verified'] = false;
                $result['red_flags'][] = 'Contract not verified';
            }
            
            // TokenSniffer checks
            if (!$tsAudit['can_mint']) {
                $scores['contract'] += 10;
                $result['checks']['mint_renounced'] = true;
            } else {
                $result['checks']['mint_renounced'] = false;
                $result['red_flags'][] = 'Contract can mint new tokens';
            }
            
            if (!$tsAudit['can_blacklist']) {
                $scores['contract'] += 10;
                $result['checks']['no_blacklist'] = true;
            } else {
                $result['checks']['no_blacklist'] = false;
                $result['red_flags'][] = 'Contract has blacklist function';
            }
            
            if ($tsAudit['verified']) {
                $scores['contract'] += 10;
                $result['checks']['source_available'] = true;
            }
            
            // Additional warnings
            if ($tsAudit['can_pause']) {
                $result['warnings'][] = 'Contract can be paused';
            }
            
            if ($tsAudit['is_proxy']) {
                $result['warnings'][] = 'Contract is a proxy (upgradable)';
            }
        } else {
            $result['checks']['contract_verified'] = null;
            $result['red_flags'][] = 'Unable to verify contract - API limits may apply';
        }
    }
    
    // ========== 2. Liquidity Safety Analysis (30 points) ==========
    $liquidityInfo = $tokensniffer->getLiquidityInfo($address, $chain);
    
    if (isset($liquidityInfo['error'])) {
        // Try to get from TokenSniffer audit
        $tsAudit = $tokensniffer->getTokenAudit($address, $chain);
        if ($tsAudit !== false) {
            $liquidityInfo = array(
                'has_liquidity' => $tsAudit['liquidity_usd'] > 0,
                'liquidity_amount_usd' => $tsAudit['liquidity_usd'],
                'liquidity_locked' => $tsAudit['liquidity_locked'],
                'lp_tokens_burned' => $tsAudit['lp_burned'],
                'lock_duration_days' => $tsAudit['lock_duration_days'],
                'dex' => $tsAudit['dex']
            );
        }
    }
    
    if (!isset($liquidityInfo['error'])) {
        $result['liquidity_info'] = $liquidityInfo;
        
        // Liquidity locked > 6 months (15 pts)
        if ($liquidityInfo['liquidity_locked'] && $liquidityInfo['lock_duration_days'] >= 180) {
            $scores['liquidity'] += 15;
            $result['checks']['liquidity_locked'] = true;
            $result['checks']['lock_duration_ok'] = true;
        } elseif ($liquidityInfo['liquidity_locked'] && $liquidityInfo['lock_duration_days'] > 0) {
            $scores['liquidity'] += 10;
            $result['checks']['liquidity_locked'] = true;
            $result['checks']['lock_duration_ok'] = false;
            $result['warnings'][] = 'Liquidity locked for only ' . $liquidityInfo['lock_duration_days'] . ' days';
        } else {
            $result['checks']['liquidity_locked'] = false;
            $result['checks']['lock_duration_ok'] = false;
            $result['red_flags'][] = 'Liquidity not locked - rug pull risk';
        }
        
        // LP tokens burned (10 pts)
        if ($liquidityInfo['lp_tokens_burned']) {
            $scores['liquidity'] += 10;
            $result['checks']['lp_burned'] = true;
        } else {
            $result['checks']['lp_burned'] = false;
            if (!$liquidityInfo['liquidity_locked']) {
                $result['red_flags'][] = 'LP tokens not burned or locked';
            }
        }
        
        // Adequate liquidity $50k+ (5 pts)
        if ($liquidityInfo['liquidity_amount_usd'] >= 50000) {
            $scores['liquidity'] += 5;
            $result['checks']['adequate_liquidity'] = true;
        } else {
            $result['checks']['adequate_liquidity'] = false;
            $result['warnings'][] = 'Low liquidity: $' . number_format($liquidityInfo['liquidity_amount_usd'], 2);
        }
    } else {
        $result['checks']['liquidity_locked'] = null;
        $result['checks']['lp_burned'] = null;
        $result['checks']['adequate_liquidity'] = null;
    }
    
    // ========== 3. Holder Distribution Analysis (20 points) ==========
    $holderDist = $tokensniffer->getHolderDistribution($address, $chain);
    $result['holder_stats'] = $holderDist;
    
    // Top 10 holders < 30% (10 pts)
    if ($holderDist['top10_percent'] > 0) {
        if ($holderDist['top10_percent'] < 30) {
            $scores['holders'] += 10;
            $result['checks']['top10_concentration_ok'] = true;
        } else {
            $result['checks']['top10_concentration_ok'] = false;
            $result['red_flags'][] = 'Top 10 holders own ' . $holderDist['top10_percent'] . '% of supply';
        }
        
        // Top 5 < 20% (5 pts)
        if ($holderDist['top5_percent'] < 20) {
            $scores['holders'] += 5;
            $result['checks']['top5_concentration_ok'] = true;
        } else {
            $result['checks']['top5_concentration_ok'] = false;
        }
        
        // No single holder > 10% (5 pts)
        if ($holderDist['top_holder_percent'] < 10) {
            $scores['holders'] += 5;
            $result['checks']['top_holder_ok'] = true;
        } else {
            $result['checks']['top_holder_ok'] = false;
            $result['red_flags'][] = 'Single holder owns ' . $holderDist['top_holder_percent'] . '% of supply';
        }
    } else {
        $result['checks']['top10_concentration_ok'] = null;
        $result['checks']['top5_concentration_ok'] = null;
        $result['checks']['top_holder_ok'] = null;
    }
    
    // ========== 4. Transaction Safety Analysis (10 points) ==========
    $honeypotCheck = $tokensniffer->checkHoneypot($address, $chain);
    $result['tax_info'] = $honeypotCheck;
    
    // Can sell token (5 pts)
    if (isset($honeypotCheck['is_honeypot']) && $honeypotCheck['is_honeypot'] === false) {
        $scores['transaction'] += 5;
        $result['checks']['can_sell'] = true;
    } elseif (isset($honeypotCheck['is_honeypot']) && $honeypotCheck['is_honeypot'] === true) {
        $result['checks']['can_sell'] = false;
        $result['red_flags'][] = 'HONEYPOT DETECTED - Cannot sell tokens!';
    } else {
        $result['checks']['can_sell'] = null;
        $result['warnings'][] = 'Unable to verify sell functionality';
    }
    
    // No hidden taxes > 5% (5 pts)
    if (isset($honeypotCheck['sell_tax']) && isset($honeypotCheck['buy_tax'])) {
        if ($honeypotCheck['sell_tax'] <= 5 && $honeypotCheck['buy_tax'] <= 5) {
            $scores['transaction'] += 5;
            $result['checks']['taxes_ok'] = true;
        } else {
            $result['checks']['taxes_ok'] = false;
            $taxMsg = 'High taxes detected';
            if ($honeypotCheck['buy_tax'] > 5) $taxMsg .= ' - Buy: ' . $honeypotCheck['buy_tax'] . '%';
            if ($honeypotCheck['sell_tax'] > 5) $taxMsg .= ' - Sell: ' . $honeypotCheck['sell_tax'] . '%';
            $result['warnings'][] = $taxMsg;
        }
    } else {
        $result['checks']['taxes_ok'] = null;
    }
    
    // ========== Calculate Final Score ==========
    $totalScore = $scores['contract'] + $scores['liquidity'] + $scores['holders'] + $scores['transaction'];
    $result['safety_score'] = $totalScore;
    
    // Determine risk level
    $riskInfo = getRiskLevel($totalScore);
    $result['risk_level'] = $riskInfo['level'];
    $result['risk_color'] = $riskInfo['color'];
    
    // Generate recommendation
    $result['recommendation'] = generateRecommendation($result, $scores);
    
    // Score breakdown
    $result['score_breakdown'] = $scores;
    
    // Cache result
    if (!$skipCache) {
        setCache($cacheKey, $result, 3600, $cacheDir);
    }
    
    return $result;
}

/**
 * Quick score check
 */
function quickScore($address, $chain, $skipCache = false) {
    global $tokensniffer, $cacheDir;
    
    $validation = validateAddress($address);
    if (!$validation['valid']) {
        return array('ok' => false, 'error' => $validation['error']);
    }
    $address = $validation['normalized'];
    
    $cacheKey = 'quick_' . $chain . '_' . strtolower($address);
    if (!$skipCache) {
        $cached = getCache($cacheKey, $cacheDir);
        if ($cached !== false) {
            $cached['cached'] = true;
            return $cached;
        }
    }
    
    $quick = $tokensniffer->getQuickScore($address, $chain);
    
    if (isset($quick['error'])) {
        return array('ok' => false, 'error' => $quick['error']);
    }
    
    $result = array(
        'ok' => true,
        'contract_address' => $address,
        'chain' => $chain,
        'safety_score' => $quick['score'],
        'risk_level' => $quick['risk_level'],
        'is_honeypot' => $quick['is_honeypot'],
        'has_mint' => $quick['has_mint'],
        'can_blacklist' => $quick['can_blacklist'],
        'contract_verified' => $quick['contract_verified'],
        'timestamp' => time()
    );
    
    if (!$skipCache) {
        setCache($cacheKey, $result, 1800, $cacheDir);
    }
    
    return $result;
}

/**
 * Batch analysis
 */
function batchAnalyze($addresses, $chain, $skipCache = false) {
    global $cacheDir;
    
    if (empty($addresses)) {
        return array('ok' => false, 'error' => 'No addresses provided');
    }
    
    $addressList = explode(',', $addresses);
    $results = array();
    $errors = array();
    
    foreach ($addressList as $addr) {
        $addr = trim($addr);
        if (empty($addr)) continue;
        
        $analysis = analyzeToken($addr, $chain, $skipCache);
        
        if ($analysis['ok']) {
            $results[] = array(
                'address' => $addr,
                'name' => isset($analysis['token_name']) ? $analysis['token_name'] : '',
                'symbol' => isset($analysis['token_symbol']) ? $analysis['token_symbol'] : '',
                'score' => $analysis['safety_score'],
                'risk_level' => $analysis['risk_level'],
                'risk_color' => $analysis['risk_color'],
                'is_honeypot' => isset($analysis['tax_info']['is_honeypot']) ? $analysis['tax_info']['is_honeypot'] : null
            );
        } else {
            $errors[] = array('address' => $addr, 'error' => $analysis['error']);
        }
    }
    
    return array(
        'ok' => true,
        'chain' => $chain,
        'analyzed' => count($results),
        'errors' => count($errors),
        'results' => $results,
        'error_details' => $errors,
        'timestamp' => time()
    );
}

/**
 * Holder distribution analysis
 */
function getHolderAnalysis($address, $chain, $skipCache = false) {
    global $tokensniffer, $cacheDir;
    
    $validation = validateAddress($address);
    if (!$validation['valid']) {
        return array('ok' => false, 'error' => $validation['error']);
    }
    $address = $validation['normalized'];
    
    $cacheKey = 'holders_' . $chain . '_' . strtolower($address);
    if (!$skipCache) {
        $cached = getCache($cacheKey, $cacheDir);
        if ($cached !== false) {
            $cached['cached'] = true;
            return $cached;
        }
    }
    
    $distribution = $tokensniffer->getHolderDistribution($address, $chain);
    
    $result = array(
        'ok' => true,
        'contract_address' => $address,
        'chain' => $chain,
        'holder_stats' => $distribution,
        'risk_assessment' => assessHolderRisk($distribution),
        'timestamp' => time()
    );
    
    if (!$skipCache) {
        setCache($cacheKey, $result, 3600, $cacheDir);
    }
    
    return $result;
}

/**
 * Honeypot check only
 */
function checkHoneypot($address, $chain, $skipCache = false) {
    global $tokensniffer, $cacheDir;
    
    $validation = validateAddress($address);
    if (!$validation['valid']) {
        return array('ok' => false, 'error' => $validation['error']);
    }
    $address = $validation['normalized'];
    
    $cacheKey = 'honeypot_' . $chain . '_' . strtolower($address);
    if (!$skipCache) {
        $cached = getCache($cacheKey, $cacheDir);
        if ($cached !== false) {
            $cached['cached'] = true;
            return $cached;
        }
    }
    
    $honeypot = $tokensniffer->checkHoneypot($address, $chain);
    
    $result = array(
        'ok' => true,
        'contract_address' => $address,
        'chain' => $chain,
        'honeypot_check' => $honeypot,
        'is_safe' => isset($honeypot['is_honeypot']) ? !$honeypot['is_honeypot'] : null,
        'warning' => isset($honeypot['is_honeypot']) && $honeypot['is_honeypot'] ? 'HONEYPOT DETECTED - DO NOT BUY!' : '',
        'timestamp' => time()
    );
    
    if (!$skipCache) {
        setCache($cacheKey, $result, 1800, $cacheDir);
    }
    
    return $result;
}

/**
 * Health check
 */
function healthCheck() {
    global $etherscan, $tokensniffer;
    
    $status = array(
        'ok' => true,
        'service' => 'onchain_safety',
        'status' => 'operational',
        'apis' => array(),
        'timestamp' => time()
    );
    
    // Test Etherscan with a known contract (WETH)
    $testContract = '0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2';
    $etherscanResult = $etherscan->isContract($testContract);
    $status['apis']['etherscan'] = array(
        'status' => $etherscanResult !== false ? 'operational' : 'degraded',
        'error' => $etherscan->getLastError()
    );
    
    // Check TokenSniffer (just check if class loads - API may need key)
    $status['apis']['tokensniffer'] = array(
        'status' => 'operational',
        'note' => 'API key may be required for full access'
    );
    
    return $status;
}

// ========== Helper Functions ==========

/**
 * Validate Ethereum address
 */
function validateAddress($address) {
    $address = trim(strtolower($address));
    
    if (empty($address)) {
        return array('valid' => false, 'error' => 'Address is required');
    }
    
    // Remove any whitespace
    $address = preg_replace('/\s+/', '', $address);
    
    // Check format
    if (!preg_match('/^0x[a-f0-9]{40}$/', $address)) {
        return array('valid' => false, 'error' => 'Invalid address format. Expected: 0x followed by 40 hex characters');
    }
    
    return array('valid' => true, 'normalized' => $address);
}

/**
 * Get risk level from score
 */
function getRiskLevel($score) {
    if ($score >= 80) {
        return array('level' => 'low', 'color' => 'green');
    } elseif ($score >= 60) {
        return array('level' => 'medium', 'color' => 'yellow');
    } elseif ($score >= 40) {
        return array('level' => 'high', 'color' => 'orange');
    } else {
        return array('level' => 'critical', 'color' => 'red');
    }
}

/**
 * Generate recommendation text
 */
function generateRecommendation($result, $scores) {
    $redFlags = $result['red_flags'];
    $warnings = $result['warnings'];
    $score = $result['safety_score'];
    
    // Critical - honeypot
    if (isset($result['tax_info']['is_honeypot']) && $result['tax_info']['is_honeypot']) {
        return 'CRITICAL: Honeypot detected! DO NOT INVEST - You will not be able to sell.';
    }
    
    // Critical score
    if ($score < 40) {
        return 'CRITICAL RISK: Multiple red flags detected. This appears to be a scam or has high rug-pull risk. Avoid investing.';
    }
    
    // High risk
    if ($score < 60) {
        $issues = array();
        if (!$result['checks']['liquidity_locked']) $issues[] = 'unlocked liquidity';
        if (isset($result['checks']['mint_renounced']) && !$result['checks']['mint_renounced']) $issues[] = 'mint function';
        if (isset($result['checks']['no_blacklist']) && !$result['checks']['no_blacklist']) $issues[] = 'blacklist';
        
        $issueStr = count($issues) > 0 ? ' (' . implode(', ', $issues) . ')' : '';
        return 'HIGH RISK: Exercise extreme caution.' . $issueStr . ' Only invest what you can afford to lose completely.';
    }
    
    // Medium risk
    if ($score < 80) {
        if (count($redFlags) > 0) {
            return 'MODERATE RISK: Some concerns identified - ' . $redFlags[0] . '. Trade with caution and consider small position size.';
        }
        if (count($warnings) > 0) {
            return 'MODERATE RISK: Minor concerns - ' . $warnings[0] . '. Generally safer but monitor closely.';
        }
        return 'MODERATE RISK: Generally acceptable but has some minor issues. Trade with standard caution.';
    }
    
    // Low risk
    return 'LOW RISK: Contract appears safe with good practices. Standard trading precautions still apply.';
}

/**
 * Assess holder distribution risk
 */
function assessHolderRisk($distribution) {
    $risks = array();
    $score = 100;
    
    if ($distribution['top_holder_percent'] > 20) {
        $risks[] = 'Whale concentration - top holder has >20%';
        $score -= 30;
    } elseif ($distribution['top_holder_percent'] > 10) {
        $risks[] = 'High top holder concentration';
        $score -= 15;
    }
    
    if ($distribution['top5_percent'] > 50) {
        $risks[] = 'Top 5 holders control majority';
        $score -= 25;
    } elseif ($distribution['top5_percent'] > 30) {
        $risks[] = 'Top 5 holders have significant control';
        $score -= 10;
    }
    
    if ($distribution['top10_percent'] > 70) {
        $risks[] = 'Extreme concentration in top 10';
        $score -= 20;
    }
    
    $level = 'low';
    if ($score < 40) $level = 'critical';
    elseif ($score < 60) $level = 'high';
    elseif ($score < 80) $level = 'medium';
    
    return array(
        'risk_score' => max(0, $score),
        'risk_level' => $level,
        'concerns' => $risks
    );
}

/**
 * Get from cache
 */
function getCache($key, $cacheDir) {
    $file = $cacheDir . '/' . $key . '.json';
    
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
 * Set cache
 */
function setCache($key, $data, $ttl, $cacheDir) {
    $file = $cacheDir . '/' . $key . '.json';
    
    $cache = array(
        'expires' => time() + $ttl,
        'data' => $data
    );
    
    @file_put_contents($file, json_encode($cache), LOCK_EX);
}
?>
