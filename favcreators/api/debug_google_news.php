<?php
// Debug Google News fetching
error_reporting(E_ALL);
ini_set('display_errors', 1);

header('Content-Type: text/plain');

$creator_name = "Pokimane";

echo "=== Testing Google News Fetch for $creator_name ===\n\n";

$search_query = urlencode($creator_name . " streamer OR " . $creator_name . " twitch OR " . $creator_name . " youtube");
$rss_url = "https://news.google.com/rss/search?q=$search_query&hl=en-US&gl=US&ceid=US:en";

echo "URL: $rss_url\n\n";

$context = stream_context_create(array(
    'http' => array(
        'timeout' => 15,
        'user_agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
));

$rss_content = @file_get_contents($rss_url, false, $context);

if ($rss_content) {
    echo "✅ Fetched RSS (" . strlen($rss_content) . " bytes)\n\n";

    $xml = @simplexml_load_string($rss_content);

    if ($xml && isset($xml->channel->item)) {
        $count = count($xml->channel->item);
        echo "✅ Parsed XML - Found $count items\n\n";

        $i = 0;
        foreach ($xml->channel->item as $item) {
            if ($i >= 3)
                break;

            echo "Item " . ($i + 1) . ":\n";
            echo "  Title: " . (string) $item->title . "\n";
            echo "  Link: " . (string) $item->link . "\n";
            echo "  PubDate: " . (string) $item->pubDate . "\n";
            echo "  Timestamp: " . strtotime((string) $item->pubDate) . "\n\n";

            $i++;
        }
    } else {
        echo "❌ Failed to parse XML\n";
        echo "First 500 chars:\n" . substr($rss_content, 0, 500) . "\n";
    }
} else {
    echo "❌ Failed to fetch RSS\n";
    $error = error_get_last();
    if ($error) {
        echo "Error: " . print_r($error, true) . "\n";
    }
}
?>