<?php
// Debug: Test the scrape_og_image function with a real Google News URL
error_reporting(E_ALL);
ini_set('display_errors', 1);
set_time_limit(30);

header('Content-Type: application/json');

// Copy the scrape_og_image function
function scrape_og_image($url)
{
    // Scrape Open Graph image from article URL
    try {
        $context = stream_context_create(array(
            'http' => array(
                'timeout' => 5,
                'user_agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
        ));

        $html = @file_get_contents($url, false, $context);

        if ($html) {
            // Look for og:image meta tag
            if (preg_match('/<meta[^>]+property=["\'](og:image)["\'][^>]+content=["\'](https?:\/\/[^"\']+)["\']/i', $html, $matches)) {
                return array('method' => 'og:image property-first', 'url' => $matches[2]);
            }

            // Try alternative format
            if (preg_match('/<meta[^>]+content=["\'](https?:\/\/[^"\']+)["\'][^>]+property=["\'](og:image)["\']/i', $html, $matches)) {
                return array('method' => 'og:image content-first', 'url' => $matches[1]);
            }

            // Try twitter:image as fallback
            if (preg_match('/<meta[^>]+name=["\'](twitter:image)["\'][^>]+content=["\'](https?:\/\/[^"\']+)["\']/i', $html, $matches)) {
                return array('method' => 'twitter:image', 'url' => $matches[2]);
            }

            return array('method' => 'none', 'html_length' => strlen($html), 'html_preview' => substr($html, 0, 500));
        }

        return array('error' => 'Failed to fetch HTML');
    } catch (Exception $e) {
        return array('error' => $e->getMessage());
    }
}

// Test with a sample Google News URL
$test_url = isset($_GET['url']) ? $_GET['url'] : 'https://news.google.com/rss/articles/CBMiggFBVV95cUxPZHVPdVJkUGNPNjRfWGlQVGRWNGJfbHlGdGxoYjhDVmhqMjhxdWJVNTBfRjFOV25LRnZaR3UtdGctSHNDRVA1OXFYeTJBajZ1Q2Fxag?oc=5';

$result = scrape_og_image($test_url);

echo json_encode(array(
    'test_url' => $test_url,
    'result' => $result
), JSON_PRETTY_PRINT);
?>