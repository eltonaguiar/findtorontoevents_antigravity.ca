<?php
// Populate sample creator news data
// Path: /findtorontoevents.ca/fc/api/populate_sample_news.php

header('Content-Type: application/json');

require_once 'db_config.php';

try {
    $conn = get_db_connection();

    // First, get some creator IDs
    $creators_result = $conn->query("SELECT id, name FROM creators LIMIT 5");
    $creators = array();
    while ($row = $creators_result->fetch_assoc()) {
        $creators[] = $row;
    }

    if (empty($creators)) {
        echo json_encode(array(
            'success' => false,
            'message' => 'No creators found in database. Please add creators first.'
        ));
        exit;
    }

    // Sample news data for each creator
    $sample_data = array();
    $now = time();

    foreach ($creators as $creator) {
        $creator_name = $creator['name'];
        $creator_id = $creator['id'];

        // Google News article
        $sample_data[] = array(
            'creator_id' => $creator_id,
            'platform' => 'news',
            'content_type' => 'article',
            'content_url' => 'https://news.google.com/search?q=' . urlencode($creator_name),
            'title' => "$creator_name announces major partnership deal",
            'description' => "Popular content creator $creator_name has signed a multi-million dollar partnership with a major brand, sources confirm.",
            'thumbnail_url' => 'https://via.placeholder.com/400x300/4F46E5/FFFFFF?text=News',
            'author' => 'Gaming News Daily',
            'engagement_count' => rand(5000, 50000),
            'posted_at' => $now - rand(3600, 86400)
        );

        // Twitter mention
        $sample_data[] = array(
            'creator_id' => $creator_id,
            'platform' => 'twitter',
            'content_type' => 'mention',
            'content_url' => 'https://twitter.com/search?q=' . urlencode($creator_name),
            'title' => "Community reacts to $creator_name's latest stream",
            'description' => "Fans are buzzing about $creator_name's surprise announcement during yesterday's stream. The hashtag is trending worldwide.",
            'thumbnail_url' => 'https://via.placeholder.com/400x300/1DA1F2/FFFFFF?text=Twitter',
            'author' => '@StreamerNews',
            'engagement_count' => rand(10000, 100000),
            'posted_at' => $now - rand(7200, 172800)
        );

        // YouTube video about creator
        $sample_data[] = array(
            'creator_id' => $creator_id,
            'platform' => 'youtube',
            'content_type' => 'video',
            'content_url' => 'https://youtube.com/results?search_query=' . urlencode($creator_name . ' news'),
            'title' => "The Rise of $creator_name: A Documentary",
            'description' => "An in-depth look at how $creator_name became one of the most influential creators in the streaming world.",
            'thumbnail_url' => 'https://via.placeholder.com/400x300/FF0000/FFFFFF?text=YouTube',
            'author' => 'Creator Chronicles',
            'engagement_count' => rand(50000, 500000),
            'posted_at' => $now - rand(86400, 259200)
        );

        // Reddit discussion
        $sample_data[] = array(
            'creator_id' => $creator_id,
            'platform' => 'reddit',
            'content_type' => 'discussion',
            'content_url' => 'https://reddit.com/search?q=' . urlencode($creator_name),
            'title' => "Discussion: $creator_name's impact on streaming culture",
            'description' => "r/LivestreamFail discusses how $creator_name has changed the landscape of content creation and what it means for the future.",
            'thumbnail_url' => 'https://via.placeholder.com/400x300/FF4500/FFFFFF?text=Reddit',
            'author' => 'u/StreamWatcher',
            'engagement_count' => rand(2000, 20000),
            'posted_at' => $now - rand(43200, 345600)
        );

        // TikTok mention
        $sample_data[] = array(
            'creator_id' => $creator_id,
            'platform' => 'tiktok',
            'content_type' => 'mention',
            'content_url' => 'https://tiktok.com/search?q=' . urlencode($creator_name),
            'title' => "Viral TikTok about $creator_name's latest controversy",
            'description' => "This TikTok breaking down $creator_name's recent drama has gone viral with over 5M views in 24 hours.",
            'thumbnail_url' => 'https://via.placeholder.com/400x300/000000/FFFFFF?text=TikTok',
            'author' => '@dramaalert',
            'engagement_count' => rand(100000, 1000000),
            'posted_at' => $now - rand(10800, 129600)
        );
    }

    // Insert sample data
    $stmt = $conn->prepare("INSERT INTO creator_mentions 
        (creator_id, platform, content_type, content_url, title, description, thumbnail_url, author, engagement_count, posted_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)");

    $inserted = 0;
    foreach ($sample_data as $data) {
        $stmt->bind_param(
            'isssssssii',
            $data['creator_id'],
            $data['platform'],
            $data['content_type'],
            $data['content_url'],
            $data['title'],
            $data['description'],
            $data['thumbnail_url'],
            $data['author'],
            $data['engagement_count'],
            $data['posted_at']
        );

        if ($stmt->execute()) {
            $inserted++;
        }
    }

    echo json_encode(array(
        'success' => true,
        'message' => "Inserted $inserted sample news items for " . count($creators) . " creators",
        'total_items' => $inserted
    ));

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode(array(
        'success' => false,
        'error' => $e->getMessage()
    ));
}
?>