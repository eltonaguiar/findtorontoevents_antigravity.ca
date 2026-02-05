<?php
// Debug version - check what the aggregation is actually doing
error_reporting(E_ALL);
ini_set('display_errors', 1);
set_time_limit(300);

require_once dirname(__FILE__) . '/db_connect.php';

header('Content-Type: text/plain');

echo "=== Debug: Aggregation Process ===\n\n";

// Get creators with 50K+ followers
$sql = "SELECT id, name, follower_count FROM creators WHERE follower_count >= 50000 ORDER BY follower_count DESC LIMIT 10";
$result = $conn->query($sql);

echo "Creators to search for:\n";
echo str_repeat("-", 80) . "\n";

$creators_to_search = array();

while ($row = $result->fetch_assoc()) {
    echo sprintf("%-30s | %10s followers\n", $row['name'], number_format($row['follower_count']));
    $creators_to_search[] = $row;
}

echo "\n\nSearching for content...\n";
echo str_repeat("-", 80) . "\n";

// Simulate what the aggregator would search for
foreach ($creators_to_search as $creator) {
    $search_query = urlencode($creator['name'] . " news");
    $google_news_url = "https://news.google.com/rss/search?q=" . $search_query;

    echo "\n{$creator['name']}:\n";
    echo "  Search URL: $google_news_url\n";

    // Try to fetch RSS feed
    $context = stream_context_create(array(
        'http' => array(
            'timeout' => 10,
            'user_agent' => 'Mozilla/5.0'
        )
    ));

    $rss_content = @file_get_contents($google_news_url, false, $context);

    if ($rss_content) {
        // Parse XML
        $xml = @simplexml_load_string($rss_content);
        if ($xml && isset($xml->channel->item)) {
            $count = count($xml->channel->item);
            echo "  ✅ Found $count news items\n";

            // Show first 3 titles
            $shown = 0;
            foreach ($xml->channel->item as $item) {
                if ($shown >= 3)
                    break;
                echo "     - " . (string) $item->title . "\n";
                $shown++;
            }
        } else {
            echo "  ❌ No items in RSS feed\n";
        }
    } else {
        echo "  ❌ Failed to fetch RSS feed\n";
    }
}

$conn->close();
?>