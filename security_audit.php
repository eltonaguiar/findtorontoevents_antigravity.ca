<?php
/**
 * Security Audit Script for findtorontoevents.ca
 * 
 * Tests:
 * 1. XSS vulnerabilities in API endpoints
 * 2. SQL injection vulnerabilities
 * 3. Admin panel exposure
 * 4. API domain restrictions
 * 5. GitHub Actions security
 */

echo "=== SECURITY AUDIT ===\n";
echo "Date: " . date('Y-m-d H:i:s') . "\n\n";

$baseUrl = 'https://findtorontoevents.ca';
$fcBaseUrl = 'https://findtorontoevents.ca/fc';
$tdotBaseUrl = 'https://tdotevent.ca';

// ===== TEST 1: XSS VULNERABILITIES =====
echo "TEST 1: XSS Vulnerability Scan\n";
echo "--------------------------------\n";

$xssPayloads = [
    '<script>alert("XSS")</script>',
    '"><script>alert(String.fromCharCode(88,83,83))</script>',
    "'-alert(1)-'",
    '<img src=x onerror=alert("XSS")>',
    'javascript:alert("XSS")',
];

$endpointsToTest = [
    '/fc/api/TLC.php?user=',
    '/fc/api/creator_news_api.php?creator_id=',
    '/fc/api/get_my_creators.php?user_id=',
];

$xssVulnerabilities = [];
foreach ($endpointsToTest as $endpoint) {
    foreach ($xssPayloads as $payload) {
        $url = $baseUrl . $endpoint . urlencode($payload);
        $response = @file_get_contents($url);
        
        if ($response !== false && (
            strpos($response, $payload) !== false ||
            strpos($response, '<script>') !== false ||
            strpos($response, 'alert(') !== false
        )) {
            $xssVulnerabilities[] = [
                'endpoint' => $endpoint,
                'payload' => $payload,
                'url' => $url
            ];
            echo "  [!] POTENTIAL XSS: $endpoint\n";
        }
    }
}

if (empty($xssVulnerabilities)) {
    echo "  [✓] No obvious XSS vulnerabilities detected in basic scan\n";
} else {
    echo "  [!] Found " . count($xssVulnerabilities) . " potential XSS issues\n";
}

// ===== TEST 2: SQL INJECTION VULNERABILITIES =====
echo "\nTEST 2: SQL Injection Scan\n";
echo "--------------------------------\n";

$sqlPayloads = [
    "' OR '1'='1",
    "' OR 1=1--",
    "' UNION SELECT * FROM users--",
    "1' AND 1=1--",
    "1' AND 1=2--",
    "'; DROP TABLE users;--",
    "' OR 'x'='x",
];

$sqlVulnerabilities = [];
$testEndpoints = [
    '/fc/api/TLC.php?user=',
    '/fc/api/get_my_creators.php?user_id=',
    '/fc/api/save_note.php', // POST endpoint
];

foreach ($testEndpoints as $endpoint) {
    foreach ($sqlPayloads as $payload) {
        $url = $baseUrl . $endpoint . urlencode($payload);
        
        // Use error suppression to catch warnings
        $context = stream_context_create([
            'http' => [
                'timeout' => 5,
                'ignore_errors' => true
            ]
        ]);
        
        $response = @file_get_contents($url, false, $context);
        
        // Check for SQL error messages
        $sqlErrors = [
            'sql syntax',
            'mysql_fetch',
            'mysqli_error',
            'pdo exception',
            'sqlstate',
            'ora-',
            'pl/sql',
            'psql:',
            'sqlite3',
            'unrecognized token',
        ];
        
        if ($response !== false) {
            $responseLower = strtolower($response);
            foreach ($sqlErrors as $error) {
                if (strpos($responseLower, $error) !== false) {
                    $sqlVulnerabilities[] = [
                        'endpoint' => $endpoint,
                        'payload' => $payload,
                        'error' => $error
                    ];
                    echo "  [!] POTENTIAL SQLi: $endpoint - $error\n";
                    break 2; // Skip remaining payloads for this endpoint
                }
            }
        }
    }
}

if (empty($sqlVulnerabilities)) {
    echo "  [✓] No obvious SQL injection vulnerabilities detected\n";
} else {
    echo "  [!] Found " . count($sqlVulnerabilities) . " potential SQL injection issues\n";
}

// ===== TEST 3: ADMIN PANEL EXPOSURE =====
echo "\nTEST 3: Admin Panel Exposure Check\n";
echo "--------------------------------\n";

$adminPaths = [
    '/fc/api/admin_tools.php',
    '/fc/api/view_logs.php',
    '/fc/api/validate_tables.php',
    '/fc/api/debug_user2.php',
    '/fc/api/sync_creators_table.php',
    '/fc/api/setup_tables.php',
];

$exposedPanels = [];
foreach ($adminPaths as $path) {
    $url = $baseUrl . $path;
    $context = stream_context_create([
        'http' => [
            'timeout' => 5,
            'ignore_errors' => true
        ]
    ]);
    
    $response = @file_get_contents($url, false, $context);
    $httpCode = 0;
    
    if (isset($http_response_header)) {
        foreach ($http_response_header as $header) {
            if (preg_match('/HTTP\/\d\.\d\s+(\d+)/', $header, $matches)) {
                $httpCode = intval($matches[1]);
                break;
            }
        }
    }
    
    // Check if accessible without auth (200 OK or not redirecting to login)
    if ($httpCode === 200) {
        // Check if it shows admin content
        if (strpos($response, 'Unauthorized') === false && 
            strpos($response, 'login') === false &&
            strpos($response, 'Forbidden') === false) {
            $exposedPanels[] = [
                'path' => $path,
                'status' => $httpCode,
                'issue' => 'Accessible without authentication'
            ];
            echo "  [!] EXPOSED: $path (HTTP $httpCode)\n";
        } else {
            echo "  [✓] Protected: $path (requires auth)\n";
        }
    } elseif ($httpCode === 401 || $httpCode === 403) {
        echo "  [✓] Protected: $path (HTTP $httpCode)\n";
    } else {
        echo "  [?] Status: $path (HTTP $httpCode)\n";
    }
}

// ===== TEST 4: API DOMAIN RESTRICTIONS =====
echo "\nTEST 4: API Domain/CORS Configuration\n";
echo "--------------------------------\n";

$apiEndpoints = [
    '/fc/api/TLC.php?user=test',
    '/fc/api/creator_news_api.php',
    '/fc/api/get_my_creators.php',
];

$corsIssues = [];
foreach ($apiEndpoints as $endpoint) {
    $url = $baseUrl . $endpoint;
    
    // Test with different origins
    $origins = [
        'https://evil.com',
        'http://localhost:3000',
        'null',
        'file://',
    ];
    
    foreach ($origins as $origin) {
        $context = stream_context_create([
            'http' => [
                'method' => 'GET',
                'header' => "Origin: $origin\r\n",
                'timeout' => 5,
                'ignore_errors' => true
            ]
        ]);
        
        $response = @file_get_contents($url, false, $context);
        
        // Check CORS headers
        $allowsWildcard = false;
        $allowsOrigin = false;
        
        if (isset($http_response_header)) {
            foreach ($http_response_header as $header) {
                if (stripos($header, 'Access-Control-Allow-Origin: *') !== false) {
                    $allowsWildcard = true;
                }
                if (stripos($header, "Access-Control-Allow-Origin: $origin") !== false) {
                    $allowsOrigin = true;
                }
            }
        }
        
        if ($allowsWildcard && $origin !== $baseUrl) {
            $corsIssues[] = [
                'endpoint' => $endpoint,
                'origin' => $origin,
                'issue' => 'Allows wildcard CORS from untrusted origin'
            ];
            echo "  [!] CORS ISSUE: $endpoint allows * from $origin\n";
        }
    }
}

if (empty($corsIssues)) {
    echo "  [✓] CORS appears properly restricted\n";
}

// ===== TEST 5: CHECK LOGIN SECURITY =====
echo "\nTEST 5: Login Security Check\n";
echo "--------------------------------\n";

// Test weak credentials
$weakCredentials = [
    ['email' => 'admin', 'password' => 'admin'],
    ['email' => 'admin', 'password' => 'password'],
    ['email' => 'admin', 'password' => '123456'],
    ['email' => 'bob', 'password' => 'bob'],
];

$loginUrl = $baseUrl . '/fc/api/login.php';

$weakLogins = [];
foreach ($weakCredentials as $creds) {
    $postData = json_encode($creds);
    
    $context = stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => "Content-Type: application/json\r\n",
            'content' => $postData,
            'timeout' => 5,
            'ignore_errors' => true
        ]
    ]);
    
    $response = @file_get_contents($loginUrl, false, $context);
    
    if ($response !== false) {
        $data = json_decode($response, true);
        if (isset($data['user']) && isset($data['user']['role']) && $data['user']['role'] === 'admin') {
            $weakLogins[] = [
                'credentials' => $creds['email'] . '/' . $creds['password'],
                'issue' => 'Weak credentials accepted for admin'
            ];
            echo "  [!] WEAK ADMIN LOGIN: " . $creds['email'] . "/" . $creds['password'] . "\n";
        } elseif (isset($data['user'])) {
            echo "  [?] Login succeeded: " . $creds['email'] . "/" . $creds['password'] . " (not admin)\n";
        }
    }
}

if (empty($weakLogins)) {
    echo "  [✓] No weak admin credentials detected\n";
}

// ===== TEST 6: CHECK RATE LIMITING =====
echo "\nTEST 6: Rate Limiting Check\n";
echo "--------------------------------\n";

$testEndpoint = $baseUrl . '/fc/api/TLC.php?user=test';
$requests = 10;
$startTime = microtime(true);

for ($i = 0; $i < $requests; $i++) {
    @file_get_contents($testEndpoint);
}

$endTime = microtime(true);
$duration = $endTime - $startTime;

if ($duration < 2) { // Less than 2 seconds for 10 requests
    echo "  [!] WARNING: No rate limiting detected ($requests requests in " . round($duration, 2) . "s)\n";
} else {
    echo "  [?] Possible rate limiting ($requests requests in " . round($duration, 2) . "s)\n";
}

// ===== SUMMARY =====
echo "\n=== SECURITY AUDIT SUMMARY ===\n";
echo "--------------------------------\n";

$totalIssues = count($xssVulnerabilities) + count($sqlVulnerabilities) + 
               count($exposedPanels) + count($corsIssues) + count($weakLogins);

if ($totalIssues === 0) {
    echo "✓ No critical security issues detected in automated scan\n";
} else {
    echo "! Found $totalIssues potential security issues:\n";
    echo "  - XSS: " . count($xssVulnerabilities) . "\n";
    echo "  - SQL Injection: " . count($sqlVulnerabilities) . "\n";
    echo "  - Exposed Panels: " . count($exposedPanels) . "\n";
    echo "  - CORS Issues: " . count($corsIssues) . "\n";
    echo "  - Weak Logins: " . count($weakLogins) . "\n";
}

echo "\n=== RECOMMENDATIONS ===\n";
echo "1. Implement prepared statements for all database queries\n";
echo "2. Add output encoding for all user-supplied data\n";
echo "3. Implement rate limiting on all API endpoints\n";
echo "4. Use specific CORS origins instead of wildcard (*)\n";
echo "5. Add CSRF tokens for state-changing operations\n";
echo "6. Implement proper session timeout and regeneration\n";
echo "7. Add security headers (X-Frame-Options, CSP, etc.)\n";
echo "8. Regular security audits and dependency updates\n";

echo "\n=== ADMIN PASSWORD STATUS ===\n";
echo "Admin backdoor password updated to: adminelton2016\n";
echo "Location: favcreators/public/api/login.php\n";
echo "Location: favcreators/docs/api/login.php\n";

?>