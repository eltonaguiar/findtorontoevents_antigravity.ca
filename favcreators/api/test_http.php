<?php
error_reporting(E_ALL);
ini_set('display_errors', 1);
set_time_limit(30);

header('Content-Type: text/plain');

echo "=== Testing HTTP Requests ===\n\n";

// Test 1: Check if file_get_contents is enabled
echo "1. file_get_contents enabled: " . (function_exists('file_get_contents') ? 'YES' : 'NO') . "\n";

// Test 2: Check if allow_url_fopen is enabled
echo "2. allow_url_fopen: " . (ini_get('allow_url_fopen') ? 'YES' : 'NO') . "\n";

// Test 3: Try to fetch Google News RSS
echo "\n3. Testing Google News RSS fetch:\n";

$test_url = "https://news.google.com/rss/search?q=pokimane&hl=en-US";

$context = stream_context_create(array(
    'http' => array(
        'timeout' => 10,
        'user_agent' => 'Mozilla/5.0'
    )
));

echo "   URL: $test_url\n";

$start = microtime(true);
$content = @file_get_contents($test_url, false, $context);
$duration = microtime(true) - $start;

if ($content) {
    echo "   ✅ SUCCESS (took " . round($duration, 2) . "s)\n";
    echo "   Content length: " . strlen($content) . " bytes\n";

    // Try to parse XML
    $xml = @simplexml_load_string($content);
    if ($xml && isset($xml->channel->item)) {
        $count = count($xml->channel->item);
        echo "   Found $count news items\n";
        if ($count > 0) {
            echo "   First item: " . (string) $xml->channel->item[0]->title . "\n";
        }
    } else {
        echo "   ❌ Failed to parse XML\n";
    }
} else {
    echo "   ❌ FAILED (took " . round($duration, 2) . "s)\n";
    $error = error_get_last();
    if ($error) {
        echo "   Error: " . $error['message'] . "\n";
    }
}

?>