<?php
/**
 * Discord Interactions - Full Handler
 * Called from discord_interactions.php for non-PING requests
 * 
 * Complete implementation with all 24+ commands
 */

define('RESPONSE_CHANNEL_MESSAGE', 4);
define('RESPONSE_UPDATE_MESSAGE', 7);

function handle_interaction($interaction) {
    $type = isset($interaction['type']) ? intval($interaction['type']) : 0;
    
    // Application command (slash commands)
    if ($type === 2) {
        $data = isset($interaction['data']) ? $interaction['data'] : array();
        $command_name = isset($data['name']) ? $data['name'] : '';
        $user = isset($interaction['user']) ? $interaction['user'] : 
                (isset($interaction['member']['user']) ? $interaction['member']['user'] : array());
        $discord_id = isset($user['id']) ? $user['id'] : '';
        
        // Get options from command
        $options = isset($data['options']) ? $data['options'] : array();
        
        // Normalize command name — Discord sends 'fc-live' but we route as 'live'
        if (substr($command_name, 0, 3) === 'fc-') {
            $command_name = substr($command_name, 3);
        }
        
        switch ($command_name) {
            // Creators commands
            case 'live':
                handle_live_command($discord_id);
                break;
            case 'creators':
                handle_creators_command($discord_id);
                break;
            case 'posts':
                $creator_name = get_option_value($options, 'creator');
                handle_posts_command($creator_name);
                break;
            case 'about':
                $creator_name = get_option_value($options, 'creator');
                handle_about_command($creator_name);
                break;
                
            // Events commands
            case 'events':
                $search = get_option_value($options, 'search');
                $timeframe = get_option_value($options, 'when');
                handle_events_command($search, $timeframe);
                break;
            case 'myevents':
                handle_myevents_command($discord_id);
                break;
            case 'subscribe':
                $category = get_option_value($options, 'category');
                $frequency = get_option_value($options, 'frequency');
                handle_subscribe_command($discord_id, $category, $frequency);
                break;
            case 'unsubscribe':
                $category = get_option_value($options, 'category');
                handle_unsubscribe_command($discord_id, $category);
                break;
            case 'mysubs':
                handle_mysubs_command($discord_id);
                break;
                
            // Movie/TV commands
            case 'movies':
                $search = get_option_value($options, 'search');
                $content_type = get_option_value($options, 'type');
                handle_movies_command($search, $content_type, 0);
                break;
            case 'newreleases':
                $content_type = get_option_value($options, 'type');
                $period = get_option_value($options, 'period');
                handle_newreleases_command($content_type, $period, 0);
                break;
            case 'trailers':
                $title = get_option_value($options, 'title');
                handle_trailers_command($title);
                break;
                
            // Stock commands
            case 'stocks':
                $rating = get_option_value($options, 'rating');
                handle_stocks_command($rating, 0);
                break;
            case 'stock':
                $symbol = get_option_value($options, 'symbol');
                handle_stock_command($symbol);
                break;
            case 'stockperf':
                handle_stockperf_command();
                break;
            case 'stocksub':
                $symbol = get_option_value($options, 'symbol');
                handle_stocksub_command($discord_id, $symbol);
                break;
            case 'stockunsub':
                $symbol = get_option_value($options, 'symbol');
                handle_stockunsub_command($discord_id, $symbol);
                break;
            case 'mystocks':
                handle_mystocks_command($discord_id);
                break;
                
            // Weather command
            case 'weather':
                $location = get_option_value($options, 'location');
                handle_weather_command($location);
                break;
                
            // Mental Health command
            case 'mentalhealth':
                $topic = get_option_value($options, 'topic');
                handle_mentalhealth_command($topic);
                break;
                
            // General commands
            case 'link':
                handle_link_command($discord_id);
                break;
            case 'help':
                handle_help_command();
                break;
            case 'info':
                $feature = get_option_value($options, 'feature');
                handle_info_command($feature);
                break;
            
            // Accountability Coach commands
            case 'coach':
                require_once dirname(__FILE__) . '/accountability/handler.php';
                $action = get_option_value($options, 'action');
                $result = handle_fc_coach_command($discord_id, $action, $options);
                send_response($result);
                break;
            case 'gym':
                require_once dirname(__FILE__) . '/accountability/handler.php';
                $result = handle_fc_gym_command($discord_id, $options);
                send_response($result);
                break;
            case 'timer':
                require_once dirname(__FILE__) . '/accountability/handler.php';
                $action = get_option_value($options, 'action');
                $result = handle_fc_timer_command($discord_id, $action, $options);
                send_response($result);
                break;
            case 'stats':
                require_once dirname(__FILE__) . '/accountability/handler.php';
                $action = get_option_value($options, 'action');
                $result = handle_fc_stats_command($discord_id, $action, $options);
                send_response($result);
                break;
                
            // Feed command — show latest updates from all followed creators
            case 'feed':
                $count = get_option_value($options, 'count');
                $platform = get_option_value($options, 'platform');
                handle_feed_command($discord_id, $count, $platform);
                break;
                
            // Notification mode command
            case 'notifymode':
                $mode = get_option_value($options, 'mode');
                handle_notifymode_command($discord_id, $mode);
                break;
            
            // World Events command
            case 'worldevents':
                $we_range = get_option_value($options, 'range');
                handle_worldevents_command($we_range);
                break;
                
            // Near Me / Location Finder command
            case 'nearme':
                $nm_query = get_option_value($options, 'query');
                $nm_location = get_option_value($options, 'location');
                $nm_filter = get_option_value($options, 'filter');
                $nm_dietary = get_option_value($options, 'dietary');
                $nm_radius = get_option_value($options, 'radius');
                handle_nearme_command($nm_query, $nm_location, $nm_filter, $nm_dietary, $nm_radius);
                break;
                
            // Daily Picks commands (crypto, forex, realtime wins, momentum, unified picks)
            case 'crypto':
                handle_crypto_picks_command($options);
                break;
            case 'forex':
                handle_forex_picks_command($options);
                break;
            case 'realtime':
                $rt_asset = get_option_value($options, 'asset');
                handle_realtime_wins_command($rt_asset);
                break;
            case 'momentum':
                $mom_asset = get_option_value($options, 'asset');
                handle_momentum_command($mom_asset);
                break;
            case 'picks':
                handle_daily_picks_command($options);
                break;

            default:
                send_response("Unknown command. Use /fc-help to see available commands.");
        }
        return;
    }
    
    // Handle message component interactions (type 3) - for pagination buttons
    if ($type === 3) {
        $data = isset($interaction['data']) ? $interaction['data'] : array();
        $custom_id = isset($data['custom_id']) ? $data['custom_id'] : '';
        
        // Parse custom_id format: action:page:type:search
        $parts = explode(':', $custom_id);
        $action = isset($parts[0]) ? $parts[0] : '';
        $page = isset($parts[1]) ? intval($parts[1]) : 0;
        $content_type = isset($parts[2]) ? $parts[2] : 'both';
        $search = isset($parts[3]) ? urldecode($parts[3]) : '';
        $period = isset($parts[4]) ? $parts[4] : '';
        
        switch ($action) {
            case 'movies_page':
                handle_movies_command($search, $content_type, $page, true);
                break;
            case 'releases_page':
                handle_newreleases_command($content_type, $period, $page, true);
                break;
            case 'stocks_page':
                $rating_filter = isset($parts[2]) ? $parts[2] : 'all';
                handle_stocks_command($rating_filter, $page, true);
                break;
            default:
                send_response("Unknown action.");
        }
        return;
    }
    
    // Unknown type
    header('HTTP/1.1 400 Bad Request');
    header('Content-Type: application/json');
    echo '{"error":"Unhandled interaction type"}';
    exit;
}

// ============================================================================
// Helper Functions
// ============================================================================

function send_response($content, $ephemeral = true) {
    header('Content-Type: application/json');
    $response = array(
        'type' => RESPONSE_CHANNEL_MESSAGE,
        'data' => array(
            'content' => $content
        )
    );
    if ($ephemeral) {
        $response['data']['flags'] = 64;
    }
    echo json_encode($response);
    exit;
}

function send_response_with_components($content, $components, $ephemeral = true, $is_update = false) {
    header('Content-Type: application/json');
    
    $response_type = $is_update ? RESPONSE_UPDATE_MESSAGE : RESPONSE_CHANNEL_MESSAGE;
    
    $response = array(
        'type' => $response_type,
        'data' => array(
            'content' => $content,
            'components' => $components
        )
    );
    if ($ephemeral) {
        $response['data']['flags'] = 64;
    }
    echo json_encode($response);
    exit;
}

function get_option_value($options, $name) {
    foreach ($options as $opt) {
        if (isset($opt['name']) && $opt['name'] === $name) {
            return isset($opt['value']) ? $opt['value'] : '';
        }
    }
    return '';
}

function get_db_connection() {
    require_once dirname(__FILE__) . '/db_connect.php';
    global $conn;
    return $conn;
}

// Comparison callback for usort (PHP 5.2 — no closures)
function _cmp_event_date($a, $b) {
    return $a['date'] - $b['date'];
}

function get_movies_db_connection() {
    $host = 'localhost';
    $dbname = 'ejaguiar1_tvmoviestrailers';
    $username = 'ejaguiar1_tvmoviestrailers';
    $password = 'virus2016';
    
    $conn = @new mysqli($host, $username, $password, $dbname);
    if ($conn->connect_error) {
        return null;
    }
    $conn->set_charset('utf8mb4');
    return $conn;
}

// ============================================================================
// CREATORS Commands
// ============================================================================

function handle_live_command($discord_id) {
    $conn = get_db_connection();
    
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        send_response("Your Discord is not linked to FavCreators yet!\n\nLink your account at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    
    $sql = "SELECT sls.creator_name, sls.platform, sls.account_url
            FROM notification_preferences np
            JOIN streamer_last_seen sls ON np.creator_id COLLATE utf8mb4_unicode_ci = sls.creator_id
            WHERE np.user_id = $user_id 
            AND np.discord_notify = 1
            AND sls.is_live = 1
            ORDER BY sls.creator_name";
    
    $result = $conn->query($sql);
    
    if (!$result || $result->num_rows === 0) {
        send_response("None of your tracked creators are live right now.\n\nManage notifications at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $live_list = array();
    while ($row = $result->fetch_assoc()) {
        $name = $row['creator_name'];
        $platform = ucfirst($row['platform']);
        $url = $row['account_url'] ? $row['account_url'] : '';
        $live_list[] = "🔴 **$name** ($platform)" . ($url ? "\n   $url" : "");
    }
    
    $count = count($live_list);
    $content = "**$count creator(s) live now!**\n\n" . implode("\n\n", $live_list);
    send_response($content);
}

function handle_creators_command($discord_id) {
    $conn = get_db_connection();
    
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        send_response("Your Discord is not linked yet!\n\nLink at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    
    $sql = "SELECT np.creator_id, sls.creator_name, sls.platform, sls.is_live
            FROM notification_preferences np
            LEFT JOIN streamer_last_seen sls ON np.creator_id COLLATE utf8mb4_unicode_ci = sls.creator_id
            WHERE np.user_id = $user_id AND np.discord_notify = 1
            ORDER BY sls.creator_name";
    
    $result = $conn->query($sql);
    
    if (!$result || $result->num_rows === 0) {
        send_response("You have no notifications enabled.\n\nEnable them at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $creators = array();
    while ($row = $result->fetch_assoc()) {
        $name = $row['creator_name'] ? $row['creator_name'] : $row['creator_id'];
        $platform = $row['platform'] ? ucfirst($row['platform']) : '';
        $status = $row['is_live'] ? '🔴 ' : '⚪ ';
        $creators[] = $status . $name . ($platform ? " ($platform)" : "");
    }
    
    $count = count($creators);
    $content = "**Your $count tracked creator(s):**\n\n" . implode("\n", $creators);
    $content .= "\n\n🔴 = Live now | ⚪ = Offline";
    send_response($content);
}

function handle_posts_command($creator_name) {
    if (empty($creator_name)) {
        send_response("Please specify a creator name.\n\nUsage: `/posts <creator_name>`");
        return;
    }
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $search = '%' . $conn->real_escape_string($creator_name) . '%';
    
    $sql = "SELECT creator_name, platform, username, content_title, content_preview, content_url, content_published_at
            FROM creator_status_updates 
            WHERE creator_name LIKE '$search' OR username LIKE '$search'
            ORDER BY content_published_at DESC
            LIMIT 5";
    
    $result = $conn->query($sql);
    
    if (!$result || $result->num_rows === 0) {
        send_response("No posts found for '$creator_name'.\n\nTry a different search term or check https://findtorontoevents.ca/fc/");
        return;
    }
    
    $posts = array();
    $found_creator = '';
    while ($row = $result->fetch_assoc()) {
        if (!$found_creator) $found_creator = $row['creator_name'];
        
        $title = $row['content_title'] ? $row['content_title'] : '';
        $preview = $row['content_preview'] ? $row['content_preview'] : '';
        
        // Skip placeholder content
        if (stripos($title, 'Download TikTok') !== false || stripos($title, 'Make Your Day') !== false) {
            continue;
        }
        
        $platform = ucfirst($row['platform']);
        $text = $title ? $title : substr($preview, 0, 100);
        if (strlen($preview) > 100 && !$title) $text .= '...';
        
        $url = $row['content_url'] ? $row['content_url'] : '';
        $date = $row['content_published_at'] ? date('M j', strtotime($row['content_published_at'])) : '';
        
        $line = "**[$platform]**";
        if ($date) $line .= " $date:";
        $line .= " $text";
        if ($url) $line .= "\n$url";
        
        $posts[] = $line;
    }
    
    if (count($posts) === 0) {
        send_response("No recent posts found for '$creator_name'.\n\nCheck https://findtorontoevents.ca/fc/");
        return;
    }
    
    $content = "**Latest posts from $found_creator:**\n\n" . implode("\n\n", $posts);
    send_response($content);
}

function handle_about_command($creator_name) {
    if (empty($creator_name)) {
        send_response("Please specify a creator name.\n\nUsage: `/about <creator_name>`");
        return;
    }
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $search = '%' . $conn->real_escape_string($creator_name) . '%';
    
    $sql = "SELECT creator_id, creator_name, platform, username, account_url, is_live, stream_title, viewer_count
            FROM streamer_last_seen 
            WHERE creator_name LIKE '$search' OR username LIKE '$search'
            ORDER BY is_live DESC, creator_name
            LIMIT 10";
    
    $result = $conn->query($sql);
    
    if (!$result || $result->num_rows === 0) {
        send_response("No creator found matching '$creator_name'.\n\nBrowse creators at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    // Group by creator
    $creators = array();
    while ($row = $result->fetch_assoc()) {
        $name = $row['creator_name'];
        if (!isset($creators[$name])) {
            $creators[$name] = array(
                'name' => $name,
                'platforms' => array(),
                'is_live' => false,
                'live_info' => null
            );
        }
        
        $platform_info = array(
            'platform' => ucfirst($row['platform']),
            'username' => $row['username'],
            'url' => $row['account_url'],
            'is_live' => (bool)$row['is_live'],
            'stream_title' => $row['stream_title'],
            'viewers' => $row['viewer_count']
        );
        
        $creators[$name]['platforms'][] = $platform_info;
        
        if ($row['is_live']) {
            $creators[$name]['is_live'] = true;
            $creators[$name]['live_info'] = $platform_info;
        }
    }
    
    // Format response
    $lines = array();
    foreach ($creators as $creator) {
        $name = $creator['name'];
        $status = $creator['is_live'] ? '🔴 LIVE' : '⚪ Offline';
        
        $line = "**$name** — $status\n";
        
        // If live, show stream info first
        if ($creator['live_info']) {
            $live = $creator['live_info'];
            $line .= "📺 Streaming on {$live['platform']}";
            if ($live['viewers']) $line .= " ({$live['viewers']} viewers)";
            $line .= "\n";
            if ($live['stream_title']) $line .= "   *{$live['stream_title']}*\n";
            if ($live['url']) $line .= "   {$live['url']}\n";
        }
        
        // Show all platforms
        $line .= "**Platforms:**\n";
        foreach ($creator['platforms'] as $p) {
            $live_icon = $p['is_live'] ? '🔴' : '⚪';
            $line .= "   $live_icon {$p['platform']}";
            if ($p['username']) $line .= " (@{$p['username']})";
            if ($p['url']) $line .= "\n      {$p['url']}";
            $line .= "\n";
        }
        
        $lines[] = $line;
    }
    
    $content = implode("\n", array_slice($lines, 0, 3));
    if (count($lines) > 3) {
        $content .= "\n...and " . (count($lines) - 3) . " more results";
    }
    $content .= "\n\n🔍 Full profiles: https://findtorontoevents.ca/fc/";
    
    send_response($content);
}

// ============================================================================
// EVENTS Commands
// ============================================================================

function handle_events_command($search, $timeframe) {
    if (empty($search)) {
        send_response("Please specify what events to search for.\n\nExamples:\n`/events dating today`\n`/events music this week`\n`/events free weekend`");
        return;
    }
    
    // Fetch events from JSON
    $events_url = 'https://findtorontoevents.ca/events.json';
    $context = stream_context_create(array(
        'http' => array(
            'timeout' => 10,
            'user_agent' => 'FavCreators-Bot/1.0'
        )
    ));
    
    $json = @file_get_contents($events_url, false, $context);
    if (!$json) {
        send_response("Could not fetch events. Try again later or visit https://findtorontoevents.ca/");
        return;
    }
    
    $all_events = json_decode($json, true);
    if (!$all_events || !is_array($all_events)) {
        send_response("Error parsing events. Visit https://findtorontoevents.ca/");
        return;
    }
    
    // Parse timeframe
    $today = strtotime('today');
    $tomorrow = strtotime('tomorrow');
    $week_end = strtotime('+7 days');
    $weekend_start = strtotime('next saturday');
    $weekend_end = strtotime('next sunday 23:59:59');
    
    // If today is Saturday or Sunday, adjust weekend
    $dow = date('w');
    if ($dow == 6) { // Saturday
        $weekend_start = strtotime('today');
        $weekend_end = strtotime('tomorrow 23:59:59');
    } else if ($dow == 0) { // Sunday
        $weekend_start = strtotime('today');
        $weekend_end = strtotime('today 23:59:59');
    }
    
    $time_filter = null;
    $time_label = '';
    $timeframe = strtolower($timeframe);
    
    if (strpos($timeframe, 'today') !== false) {
        $time_filter = array($today, $tomorrow);
        $time_label = 'today';
    } else if (strpos($timeframe, 'tomorrow') !== false) {
        $time_filter = array($tomorrow, strtotime('+2 days'));
        $time_label = 'tomorrow';
    } else if (strpos($timeframe, 'weekend') !== false) {
        $time_filter = array($weekend_start, $weekend_end);
        $time_label = 'this weekend';
    } else if (strpos($timeframe, 'week') !== false) {
        $time_filter = array($today, $week_end);
        $time_label = 'this week';
    }
    
    // Search keywords
    $search_lower = strtolower($search);
    $keywords = array($search_lower);
    
    // Add related keywords for common searches
    if (strpos($search_lower, 'dating') !== false || strpos($search_lower, 'date') !== false) {
        $keywords = array_merge($keywords, array('dating', 'singles', 'speed date', 'matchmaking', 'mixer'));
    }
    if (strpos($search_lower, 'music') !== false || strpos($search_lower, 'concert') !== false) {
        $keywords = array_merge($keywords, array('music', 'concert', 'live music', 'dj', 'band'));
    }
    if (strpos($search_lower, 'free') !== false) {
        $keywords = array_merge($keywords, array('free'));
    }
    
    // Filter events
    $matched = array();
    foreach ($all_events as $event) {
        $text = strtolower($event['title'] . ' ' . (isset($event['description']) ? $event['description'] : ''));
        
        // Check keywords
        $matches = false;
        foreach ($keywords as $kw) {
            if (strpos($text, $kw) !== false) {
                $matches = true;
                break;
            }
        }
        
        // Special handling for "free" - check isFree field
        if ($search_lower === 'free' && isset($event['isFree']) && $event['isFree']) {
            $matches = true;
        }
        
        if (!$matches) continue;
        
        // Parse event date
        $event_date = isset($event['date']) ? strtotime($event['date']) : 0;
        
        // Apply time filter
        if ($time_filter) {
            if ($event_date < $time_filter[0] || $event_date > $time_filter[1]) {
                continue;
            }
        } else {
            // Default: only show future events
            if ($event_date < $today) continue;
        }
        
        $matched[] = array(
            'title' => $event['title'],
            'date' => $event_date,
            'location' => isset($event['location']) ? $event['location'] : '',
            'url' => isset($event['url']) ? $event['url'] : '',
            'price' => isset($event['price']) ? $event['price'] : ''
        );
    }
    
    // Sort by date (PHP 5.2 compatible — no closures)
    usort($matched, '_cmp_event_date');
    
    // Limit results
    $matched = array_slice($matched, 0, 8);
    
    if (count($matched) === 0) {
        $msg = "No '$search' events found";
        if ($time_label) $msg .= " $time_label";
        $msg .= ".\n\nTry a broader search or visit https://findtorontoevents.ca/";
        send_response($msg);
        return;
    }
    
    // Format response
    $title = "**" . ucfirst($search) . " events";
    if ($time_label) $title .= " $time_label";
    $title .= "** (" . count($matched) . " found)\n\n";
    
    $lines = array();
    foreach ($matched as $e) {
        $date_str = date('M j', $e['date']);
        $day = date('D', $e['date']);
        $line = "📅 **$day $date_str**: " . substr($e['title'], 0, 55);
        if (strlen($e['title']) > 55) $line .= '...';
        if ($e['url']) $line .= "\n   $e[url]";
        $lines[] = $line;
    }
    
    $content = $title . implode("\n\n", $lines);
    $content .= "\n\n🔍 More: https://findtorontoevents.ca/";
    send_response($content);
}

function handle_myevents_command($discord_id) {
    $conn = get_db_connection();
    
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        send_response("Your Discord is not linked to FavCreators yet!\n\nLink your account at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    
    $result = $conn->query("SELECT event_id, event_data FROM user_saved_events WHERE user_id = $user_id ORDER BY created_at DESC LIMIT 10");
    
    if (!$result || $result->num_rows === 0) {
        send_response("You don't have any saved events yet.\n\nBrowse and save events at: https://findtorontoevents.ca/");
        return;
    }
    
    $events = array();
    while ($row = $result->fetch_assoc()) {
        $data = json_decode($row['event_data'], true);
        if (is_array($data)) {
            $events[] = $data;
        }
    }
    
    if (count($events) === 0) {
        send_response("You don't have any saved events yet.\n\nBrowse and save events at: https://findtorontoevents.ca/");
        return;
    }
    
    $lines = array();
    foreach ($events as $e) {
        $title = isset($e['title']) ? $e['title'] : 'Untitled';
        $date = isset($e['date']) ? date('M j', strtotime($e['date'])) : '';
        $url = isset($e['url']) ? $e['url'] : '';
        
        $line = "📅 " . ($date ? "**$date**: " : '') . substr($title, 0, 50);
        if (strlen($title) > 50) $line .= '...';
        if ($url) $line .= "\n   $url";
        $lines[] = $line;
    }
    
    $count = count($events);
    $content = "**Your saved events ($count):**\n\n" . implode("\n\n", $lines);
    $content .= "\n\n📋 Manage at: https://findtorontoevents.ca/";
    send_response($content);
}

function handle_subscribe_command($discord_id, $category, $frequency) {
    if (empty($category)) {
        $category = 'dating';
    }
    if (empty($frequency)) {
        $frequency = 'daily';
    }
    
    $category = strtolower(trim($category));
    $frequency = strtolower(trim($frequency));
    
    // Currently only support dating
    if ($category !== 'dating') {
        send_response("Currently only 'dating' event notifications are available.\n\nUse: `/subscribe dating daily`\nor: `/subscribe dating weekly`");
        return;
    }
    
    // Validate frequency
    if ($frequency !== 'daily' && $frequency !== 'weekly' && $frequency !== 'both') {
        send_response("Invalid frequency. Use 'daily', 'weekly', or 'both'.\n\nExamples:\n`/subscribe dating daily` - Get dating events every morning\n`/subscribe dating weekly` - Get weekly roundup on Mondays\n`/subscribe dating both` - Get both daily and weekly");
        return;
    }
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        send_response("Your Discord is not linked yet!\n\nLink your account first at:\nhttps://findtorontoevents.ca/fc/\n\nThen try `/subscribe` again.");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    $category_esc = $conn->real_escape_string($category);
    
    // Handle 'both' frequency
    $frequencies = ($frequency === 'both') ? array('daily', 'weekly') : array($frequency);
    $created = array();
    
    foreach ($frequencies as $freq) {
        $freq_esc = $conn->real_escape_string($freq);
        
        $check = $conn->query("SELECT id, enabled FROM event_subscriptions 
                              WHERE user_id = $user_id AND subscription_type = '$category_esc' AND frequency = '$freq_esc' LIMIT 1");
        
        if ($check && $check->num_rows > 0) {
            $existing = $check->fetch_assoc();
            if (intval($existing['enabled']) === 0) {
                $conn->query("UPDATE event_subscriptions SET enabled = 1 WHERE id = " . intval($existing['id']));
            }
            $created[] = $freq;
        } else {
            $conn->query("INSERT INTO event_subscriptions (user_id, discord_id, subscription_type, frequency, enabled) 
                         VALUES ($user_id, '$discord_id_esc', '$category_esc', '$freq_esc', 1)");
            $created[] = $freq;
        }
    }
    
    $freq_text = implode(' and ', $created);
    $content = "✅ **Subscribed to $category events ($freq_text)!**\n\n";
    
    if (in_array('daily', $created)) {
        $content .= "📅 **Daily:** You'll receive dating events each morning around 8 AM ET\n";
    }
    if (in_array('weekly', $created)) {
        $content .= "📋 **Weekly:** You'll receive a weekly roundup every Monday morning\n";
    }
    
    $content .= "\nUse `/unsubscribe $category` to stop notifications.";
    $content .= "\nUse `/mysubs` to see all your subscriptions.";
    
    send_response($content);
}

function handle_unsubscribe_command($discord_id, $category) {
    if (empty($category)) {
        $category = 'dating';
    }
    $category = strtolower(trim($category));
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        send_response("Your Discord is not linked.\n\nLink at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    $category_esc = $conn->real_escape_string($category);
    
    $conn->query("UPDATE event_subscriptions SET enabled = 0 
                  WHERE user_id = $user_id AND subscription_type = '$category_esc'");
    
    $affected = $conn->affected_rows;
    
    if ($affected > 0) {
        send_response("✅ **Unsubscribed from $category event notifications.**\n\nYou can re-subscribe anytime with `/subscribe $category`");
    } else {
        send_response("You weren't subscribed to $category events.\n\nUse `/subscribe $category` to start receiving notifications.");
    }
}

function handle_mysubs_command($discord_id) {
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        send_response("Your Discord is not linked.\n\nLink at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    
    $subs = $conn->query("SELECT subscription_type, frequency, enabled, last_daily_sent, last_weekly_sent 
                          FROM event_subscriptions 
                          WHERE user_id = $user_id 
                          ORDER BY subscription_type, frequency");
    
    if (!$subs || $subs->num_rows === 0) {
        send_response("**You have no event subscriptions.**\n\nStart receiving dating event notifications:\n`/subscribe dating daily` - Every morning\n`/subscribe dating weekly` - Weekly roundup\n`/subscribe dating both` - Get both!");
        return;
    }
    
    $content = "**📋 Your Event Subscriptions:**\n\n";
    while ($row = $subs->fetch_assoc()) {
        $status_icon = intval($row['enabled']) ? '✅' : '⏸️';
        $status = intval($row['enabled']) ? 'Active' : 'Paused';
        $type = ucfirst($row['subscription_type']);
        $freq = ucfirst($row['frequency']);
        $content .= "$status_icon **$type** ($freq): $status\n";
    }
    
    $content .= "\n**Manage:**\n`/subscribe <category> <frequency>` - Add subscription\n`/unsubscribe <category>` - Remove subscription";
    
    send_response($content);
}

// ============================================================================
// MOVIES & TV Commands
// ============================================================================

function handle_movies_command($search, $content_type, $page = 0, $is_update = false) {
    $db = get_movies_db_connection();
    if (!$db) {
        send_response("Movies database unavailable. Visit https://findtorontoevents.ca/movieshows2/");
        return;
    }
    
    $per_page = 5;
    $offset = $page * $per_page;
    
    // Build query
    $where = array("1=1");
    
    if (!empty($search)) {
        $search_esc = $db->real_escape_string($search);
        $where[] = "(title LIKE '%$search_esc%' OR original_title LIKE '%$search_esc%')";
    }
    
    if ($content_type === 'movie') {
        $where[] = "media_type = 'movie'";
    } else if ($content_type === 'tv') {
        $where[] = "media_type = 'tv'";
    }
    
    $where_sql = implode(' AND ', $where);
    
    // Get total count
    $count_result = $db->query("SELECT COUNT(*) as cnt FROM trailers WHERE $where_sql");
    $count_row = $count_result ? $count_result->fetch_assoc() : null;
    $total = $count_row ? intval($count_row['cnt']) : 0;
    $total_pages = ceil($total / $per_page);
    
    if ($total === 0) {
        $db->close();
        $msg = "No movies/shows found";
        if ($search) $msg .= " matching '$search'";
        $msg .= ".\n\nBrowse all: https://findtorontoevents.ca/movieshows2/";
        send_response($msg);
        return;
    }
    
    // Get results
    $sql = "SELECT title, media_type, release_date, vote_average, trailer_url, poster_path, overview
            FROM trailers 
            WHERE $where_sql
            ORDER BY popularity DESC, release_date DESC
            LIMIT $per_page OFFSET $offset";
    
    $result = $db->query($sql);
    $db->close();
    
    $items = array();
    while ($row = $result->fetch_assoc()) {
        $items[] = $row;
    }
    
    // Format response
    $current_page = $page + 1;
    $type_label = $content_type === 'movie' ? 'Movies' : ($content_type === 'tv' ? 'TV Shows' : 'Movies & TV');
    $header = "**🎬 $type_label";
    if ($search) $header .= " matching '$search'";
    $header .= "** (Page $current_page/$total_pages, $total total)\n\n";
    
    $lines = array();
    foreach ($items as $item) {
        $title = $item['title'];
        $type_icon = $item['media_type'] === 'tv' ? '📺' : '🎬';
        $rating = $item['vote_average'] ? '⭐' . number_format($item['vote_average'], 1) : '';
        $year = $item['release_date'] ? date('Y', strtotime($item['release_date'])) : '';
        
        $line = "$type_icon **$title**";
        if ($year) $line .= " ($year)";
        if ($rating) $line .= " $rating";
        if ($item['trailer_url']) $line .= "\n   🎥 $item[trailer_url]";
        $lines[] = $line;
    }
    
    $content = $header . implode("\n\n", $lines);
    
    // Build pagination buttons
    $components = array();
    $buttons = array();
    
    $type_encoded = $content_type ? $content_type : 'both';
    $search_encoded = urlencode($search ? $search : '');
    
    if ($page > 0) {
        $buttons[] = array(
            'type' => 2,
            'style' => 1,
            'label' => '◀ Previous',
            'custom_id' => "movies_page:" . ($page - 1) . ":$type_encoded:$search_encoded"
        );
    }
    
    if ($current_page < $total_pages) {
        $buttons[] = array(
            'type' => 2,
            'style' => 1,
            'label' => 'Next ▶',
            'custom_id' => "movies_page:" . ($page + 1) . ":$type_encoded:$search_encoded"
        );
    }
    
    if (!empty($buttons)) {
        $components[] = array(
            'type' => 1,
            'components' => $buttons
        );
    }
    
    $content .= "\n\n🔍 Browse all: https://findtorontoevents.ca/movieshows2/";
    
    if (!empty($components)) {
        send_response_with_components($content, $components, true, $is_update);
    } else {
        send_response($content);
    }
}

function handle_newreleases_command($content_type, $period, $page = 0, $is_update = false) {
    $db = get_movies_db_connection();
    if (!$db) {
        send_response("Movies database unavailable. Visit https://findtorontoevents.ca/movieshows2/");
        return;
    }
    
    $per_page = 5;
    $offset = $page * $per_page;
    
    // Build date range
    $now = date('Y-m-d');
    $date_start = $now;
    $date_end = $now;
    $period_label = 'this week';
    
    if ($period === 'month') {
        $date_start = date('Y-m-01');
        $date_end = date('Y-m-t');
        $period_label = 'this month';
    } else if ($period === 'upcoming') {
        $date_start = $now;
        $date_end = date('Y-12-31');
        $period_label = 'coming soon';
    } else {
        // This week
        $date_start = date('Y-m-d', strtotime('monday this week'));
        $date_end = date('Y-m-d', strtotime('sunday this week'));
    }
    
    $where = array("release_date >= '$date_start'", "release_date <= '$date_end'");
    
    if ($content_type === 'movie') {
        $where[] = "media_type = 'movie'";
    } else if ($content_type === 'tv') {
        $where[] = "media_type = 'tv'";
    }
    
    $where_sql = implode(' AND ', $where);
    
    // Get total count
    $count_result = $db->query("SELECT COUNT(*) as cnt FROM trailers WHERE $where_sql");
    $count_row = $count_result ? $count_result->fetch_assoc() : null;
    $total = $count_row ? intval($count_row['cnt']) : 0;
    $total_pages = ceil($total / $per_page);
    
    if ($total === 0) {
        $db->close();
        $type_label = $content_type === 'movie' ? 'movie' : ($content_type === 'tv' ? 'TV show' : '');
        send_response("No $type_label releases found $period_label.\n\nBrowse all: https://findtorontoevents.ca/movieshows2/");
        return;
    }
    
    // Get results
    $sql = "SELECT title, media_type, release_date, vote_average, trailer_url
            FROM trailers 
            WHERE $where_sql
            ORDER BY release_date ASC, popularity DESC
            LIMIT $per_page OFFSET $offset";
    
    $result = $db->query($sql);
    $db->close();
    
    $items = array();
    while ($row = $result->fetch_assoc()) {
        $items[] = $row;
    }
    
    // Format response
    $current_page = $page + 1;
    $type_label = $content_type === 'movie' ? 'Movie' : ($content_type === 'tv' ? 'TV Show' : '');
    $header = "**🆕 New $type_label Releases $period_label** (Page $current_page/$total_pages, $total total)\n\n";
    
    $lines = array();
    foreach ($items as $item) {
        $title = $item['title'];
        $type_icon = $item['media_type'] === 'tv' ? '📺' : '🎬';
        $rating = $item['vote_average'] ? '⭐' . number_format($item['vote_average'], 1) : '';
        $date = $item['release_date'] ? date('M j', strtotime($item['release_date'])) : '';
        
        $line = "$type_icon **$title**";
        if ($date) $line .= " — $date";
        if ($rating) $line .= " $rating";
        if ($item['trailer_url']) $line .= "\n   🎥 $item[trailer_url]";
        $lines[] = $line;
    }
    
    $content = $header . implode("\n\n", $lines);
    
    // Build pagination buttons
    $components = array();
    $buttons = array();
    
    $type_encoded = $content_type ? $content_type : 'both';
    $period_encoded = $period ? $period : 'week';
    
    if ($page > 0) {
        $buttons[] = array(
            'type' => 2,
            'style' => 1,
            'label' => '◀ Previous',
            'custom_id' => "releases_page:" . ($page - 1) . ":$type_encoded::$period_encoded"
        );
    }
    
    if ($current_page < $total_pages) {
        $buttons[] = array(
            'type' => 2,
            'style' => 1,
            'label' => 'Next ▶',
            'custom_id' => "releases_page:" . ($page + 1) . ":$type_encoded::$period_encoded"
        );
    }
    
    if (!empty($buttons)) {
        $components[] = array(
            'type' => 1,
            'components' => $buttons
        );
    }
    
    $content .= "\n\n🔍 Browse all: https://findtorontoevents.ca/movieshows2/";
    
    if (!empty($components)) {
        send_response_with_components($content, $components, true, $is_update);
    } else {
        send_response($content);
    }
}

function handle_trailers_command($title) {
    if (empty($title)) {
        send_response("Please specify a movie or TV show title.\n\nUsage: `/trailers Avatar`");
        return;
    }
    
    $db = get_movies_db_connection();
    if (!$db) {
        send_response("Movies database unavailable. Visit https://findtorontoevents.ca/movieshows2/");
        return;
    }
    
    $title_esc = $db->real_escape_string($title);
    
    $sql = "SELECT title, media_type, release_date, vote_average, trailer_url, overview
            FROM trailers 
            WHERE title LIKE '%$title_esc%' OR original_title LIKE '%$title_esc%'
            ORDER BY popularity DESC
            LIMIT 5";
    
    $result = $db->query($sql);
    $db->close();
    
    if (!$result || $result->num_rows === 0) {
        send_response("No trailers found for '$title'.\n\nBrowse all: https://findtorontoevents.ca/movieshows2/");
        return;
    }
    
    $items = array();
    while ($row = $result->fetch_assoc()) {
        $items[] = $row;
    }
    
    $lines = array();
    foreach ($items as $item) {
        $type_icon = $item['media_type'] === 'tv' ? '📺' : '🎬';
        $rating = $item['vote_average'] ? '⭐' . number_format($item['vote_average'], 1) : '';
        $year = $item['release_date'] ? '(' . date('Y', strtotime($item['release_date'])) . ')' : '';
        
        $line = "$type_icon **{$item['title']}** $year";
        if ($rating) $line .= " $rating";
        if ($item['overview']) {
            $overview = substr($item['overview'], 0, 120);
            if (strlen($item['overview']) > 120) $overview .= '...';
            $line .= "\n   $overview";
        }
        if ($item['trailer_url']) {
            $line .= "\n   🎥 **Trailer:** {$item['trailer_url']}";
        } else {
            $line .= "\n   *(No trailer available)*";
        }
        $lines[] = $line;
    }
    
    $content = "**🎬 Trailers for '$title':**\n\n" . implode("\n\n", $lines);
    $content .= "\n\n🔍 Browse all: https://findtorontoevents.ca/movieshows2/";
    
    send_response($content);
}

// ============================================================================
// STOCK Commands
// ============================================================================

function fetch_stock_data($filename) {
    $url = "https://findtorontoevents.ca/findstocks/$filename";
    $context = stream_context_create(array(
        'http' => array(
            'timeout' => 10,
            'user_agent' => 'FavCreators-Bot/1.0'
        )
    ));
    
    $json = @file_get_contents($url, false, $context);
    if (!$json) return null;
    
    return json_decode($json, true);
}

function handle_stocks_command($rating_filter, $page = 0, $is_update = false) {
    $data = fetch_stock_data('daily-stocks.json');
    
    if (!$data || !isset($data['stocks']) || empty($data['stocks'])) {
        send_response("No stock picks available right now. Check back later!\n\n📈 https://findtorontoevents.ca/findstocks/");
        return;
    }
    
    $stocks = $data['stocks'];
    $market_date = isset($data['marketDate']) ? $data['marketDate'] : date('Y-m-d');
    
    // Apply rating filter (PHP 5.2 compatible — no closures)
    if ($rating_filter === 'strong_buy') {
        $filtered = array();
        foreach ($stocks as $s) {
            if (isset($s['rating']) && $s['rating'] === 'STRONG BUY') {
                $filtered[] = $s;
            }
        }
        $stocks = $filtered;
    } else if ($rating_filter === 'buy') {
        $filtered = array();
        foreach ($stocks as $s) {
            if (isset($s['rating']) && ($s['rating'] === 'STRONG BUY' || $s['rating'] === 'BUY')) {
                $filtered[] = $s;
            }
        }
        $stocks = $filtered;
    }
    
    if (empty($stocks)) {
        $msg = "No stocks match that filter.";
        if ($rating_filter === 'strong_buy') $msg .= " Try `/stocks buy` or `/stocks all`.";
        $msg .= "\n\n📈 https://findtorontoevents.ca/findstocks/";
        send_response($msg);
        return;
    }
    
    // Pagination
    $per_page = 5;
    $total = count($stocks);
    $total_pages = ceil($total / $per_page);
    $offset = $page * $per_page;
    $current_page = $page + 1;
    
    $page_stocks = array_slice($stocks, $offset, $per_page);
    
    // Format
    $filter_label = '';
    if ($rating_filter === 'strong_buy') $filter_label = ' (Strong Buy only)';
    else if ($rating_filter === 'buy') $filter_label = ' (Buy or better)';
    
    $content = "**📈 Today's Stock Picks$filter_label**\n";
    $content .= "Page $current_page/$total_pages • $total picks • $market_date\n\n";
    
    foreach ($page_stocks as $stock) {
        $symbol = isset($stock['symbol']) ? $stock['symbol'] : '';
        $name = isset($stock['name']) ? $stock['name'] : '';
        $price = isset($stock['price']) ? '$' . number_format($stock['price'], 2) : '';
        $rating = isset($stock['rating']) ? $stock['rating'] : '';
        $score = isset($stock['score']) ? $stock['score'] : 0;
        $risk = isset($stock['risk']) ? $stock['risk'] : '';
        $timeframe = isset($stock['timeframe']) ? $stock['timeframe'] : '';
        $algorithm = isset($stock['algorithm']) ? $stock['algorithm'] : '';
        
        // Rating emoji
        $rating_icon = '⚪';
        if ($rating === 'STRONG BUY') $rating_icon = '🟢';
        else if ($rating === 'BUY') $rating_icon = '🟡';
        
        // Risk emoji
        $risk_icon = '';
        if ($risk === 'Low') $risk_icon = '🛡️';
        else if ($risk === 'Medium') $risk_icon = '⚠️';
        else if ($risk === 'High') $risk_icon = '🔥';
        
        $content .= "$rating_icon **$symbol** $price — $rating\n";
        $content .= "   $name\n";
        $content .= "   Score: $score | $risk_icon $risk risk | $timeframe\n";
        $content .= "   Algorithm: $algorithm\n\n";
    }
    
    // Build pagination buttons
    $components = array();
    $buttons = array();
    
    $filter_encoded = $rating_filter ? $rating_filter : 'all';
    
    if ($page > 0) {
        $buttons[] = array(
            'type' => 2,
            'style' => 1,
            'label' => '◀ Previous',
            'custom_id' => "stocks_page:" . ($page - 1) . ":$filter_encoded"
        );
    }
    
    if ($current_page < $total_pages) {
        $buttons[] = array(
            'type' => 2,
            'style' => 1,
            'label' => 'Next ▶',
            'custom_id' => "stocks_page:" . ($page + 1) . ":$filter_encoded"
        );
    }
    
    if (!empty($buttons)) {
        $components[] = array(
            'type' => 1,
            'components' => $buttons
        );
    }
    
    $content .= "📈 More details: https://findtorontoevents.ca/findstocks/\n";
    $content .= "*Not financial advice. Do your own research.*";
    
    if (!empty($components)) {
        send_response_with_components($content, $components, true, $is_update);
    } else {
        send_response($content);
    }
}

function handle_stock_command($symbol) {
    if (empty($symbol)) {
        send_response("Please specify a stock symbol.\n\nUsage: `/stock AAPL`");
        return;
    }
    
    $symbol = strtoupper(trim($symbol));
    
    // Fetch current picks
    $data = fetch_stock_data('daily-stocks.json');
    $found_current = null;
    
    if ($data && isset($data['stocks'])) {
        foreach ($data['stocks'] as $stock) {
            if (isset($stock['symbol']) && strtoupper($stock['symbol']) === $symbol) {
                $found_current = $stock;
                break;
            }
        }
    }
    
    // Fetch performance data
    $perf_data = fetch_stock_data('pick-performance.json');
    $historical_picks = array();
    
    if ($perf_data && isset($perf_data['allPicks'])) {
        foreach ($perf_data['allPicks'] as $pick) {
            if (isset($pick['symbol']) && strtoupper($pick['symbol']) === $symbol) {
                $historical_picks[] = $pick;
            }
        }
    }
    
    if (!$found_current && empty($historical_picks)) {
        send_response("No picks found for **$symbol**.\n\nThis stock hasn't been flagged by our algorithms recently.\n\n📈 Browse all picks: https://findtorontoevents.ca/findstocks/");
        return;
    }
    
    $content = "**📊 Stock Details: $symbol**\n\n";
    
    // Show current pick if exists
    if ($found_current) {
        $name = isset($found_current['name']) ? $found_current['name'] : '';
        $price = isset($found_current['price']) ? '$' . number_format($found_current['price'], 2) : '';
        $rating = isset($found_current['rating']) ? $found_current['rating'] : '';
        $score = isset($found_current['score']) ? $found_current['score'] : 0;
        $risk = isset($found_current['risk']) ? $found_current['risk'] : '';
        $timeframe = isset($found_current['timeframe']) ? $found_current['timeframe'] : '';
        $algorithm = isset($found_current['algorithm']) ? $found_current['algorithm'] : '';
        $stop_loss = isset($found_current['stopLoss']) ? '$' . number_format($found_current['stopLoss'], 2) : '';
        $picked_at = isset($found_current['pickedAt']) ? date('M j, g:ia', strtotime($found_current['pickedAt'])) : '';
        
        $rating_icon = $rating === 'STRONG BUY' ? '🟢' : ($rating === 'BUY' ? '🟡' : '⚪');
        $risk_icon = $risk === 'Low' ? '🛡️' : ($risk === 'Medium' ? '⚠️' : '🔥');
        
        $content .= "**CURRENT PICK** $rating_icon\n";
        $content .= "Company: $name\n";
        $content .= "Price: $price\n";
        $content .= "Rating: $rating (Score: $score/100)\n";
        $content .= "Risk: $risk_icon $risk\n";
        $content .= "Timeframe: $timeframe\n";
        $content .= "Algorithm: $algorithm\n";
        if ($stop_loss) $content .= "Stop Loss: $stop_loss\n";
        $content .= "Picked: $picked_at\n";
    }
    
    // Show historical picks
    if (!empty($historical_picks)) {
        $content .= "\n**Historical Picks:** (" . count($historical_picks) . " total)\n";
        $recent = array_slice($historical_picks, 0, 3);
        foreach ($recent as $pick) {
            $algo = isset($pick['algorithm']) ? $pick['algorithm'] : '';
            $picked = isset($pick['pickedAt']) ? date('M j', strtotime($pick['pickedAt'])) : '';
            $status = isset($pick['status']) ? $pick['status'] : 'PENDING';
            $return_pct = isset($pick['returnPercent']) ? $pick['returnPercent'] : 0;
            
            $status_icon = '⏳';
            if ($status === 'WIN') $status_icon = '✅';
            else if ($status === 'LOSS') $status_icon = '❌';
            
            $return_str = $return_pct != 0 ? ' (' . ($return_pct > 0 ? '+' : '') . round($return_pct, 1) . '%)' : '';
            $content .= "$status_icon $picked — $algo$return_str\n";
        }
    }
    
    $content .= "\n📈 Full details: https://findtorontoevents.ca/findstocks/\n";
    $content .= "*Not financial advice. Do your own research.*";
    
    send_response($content);
}

function handle_stockperf_command() {
    $data = fetch_stock_data('pick-performance.json');
    
    if (!$data) {
        send_response("Performance data unavailable. Visit https://findtorontoevents.ca/findstocks/");
        return;
    }
    
    $total = isset($data['totalPicks']) ? $data['totalPicks'] : 0;
    $verified = isset($data['verified']) ? $data['verified'] : 0;
    $pending = isset($data['pending']) ? $data['pending'] : 0;
    $wins = isset($data['wins']) ? $data['wins'] : 0;
    $losses = isset($data['losses']) ? $data['losses'] : 0;
    $win_rate = isset($data['winRate']) ? $data['winRate'] : 0;
    $avg_return = isset($data['avgReturn']) ? $data['avgReturn'] : 0;
    
    $content = "**📊 Stock Pick Performance**\n\n";
    
    $content .= "**Overall Statistics:**\n";
    $content .= "Total Picks: $total\n";
    $content .= "Verified: $verified | Pending: $pending\n";
    if ($verified > 0) {
        $content .= "Wins: $wins ✅ | Losses: $losses ❌\n";
        $content .= "Win Rate: " . round($win_rate * 100) . "%\n";
        if ($avg_return != 0) {
            $content .= "Avg Return: " . ($avg_return > 0 ? '+' : '') . round($avg_return, 2) . "%\n";
        }
    }
    
    // By algorithm
    if (isset($data['byAlgorithm']) && !empty($data['byAlgorithm'])) {
        $content .= "\n**By Algorithm:**\n";
        foreach ($data['byAlgorithm'] as $algo => $stats) {
            $algo_picks = isset($stats['picks']) ? $stats['picks'] : 0;
            $algo_wins = isset($stats['wins']) ? $stats['wins'] : 0;
            $algo_verified = isset($stats['verified']) ? $stats['verified'] : 0;
            
            if ($algo_verified > 0) {
                $algo_rate = round(($algo_wins / $algo_verified) * 100);
                $content .= "• $algo: $algo_wins/$algo_verified verified ($algo_rate%)\n";
            } else {
                $content .= "• $algo: $algo_picks picks (pending)\n";
            }
        }
    }
    
    // Recent hits
    if (isset($data['recentHits']) && !empty($data['recentHits'])) {
        $content .= "\n**Recent Wins:**\n";
        $recent = array_slice($data['recentHits'], 0, 3);
        foreach ($recent as $hit) {
            $sym = isset($hit['symbol']) ? $hit['symbol'] : '';
            $ret = isset($hit['returnPercent']) ? $hit['returnPercent'] : 0;
            $algo = isset($hit['algorithm']) ? $hit['algorithm'] : '';
            $content .= "✅ $sym: +" . round($ret, 1) . "% ($algo)\n";
        }
    }
    
    $content .= "\n📈 Detailed analytics: https://findtorontoevents.ca/findstocks/research/\n";
    $content .= "*Not financial advice. Do your own research.*";
    
    send_response($content);
}

function handle_stocksub_command($discord_id, $symbol) {
    if (empty($symbol)) {
        send_response("Please specify a stock symbol.\n\nUsage: `/stocksub AAPL`");
        return;
    }
    
    $symbol = strtoupper(trim($symbol));
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    ensure_stock_subscriptions_table($conn);
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $symbol_esc = $conn->real_escape_string($symbol);
    
    $result = $conn->query("SELECT id FROM stock_subscriptions WHERE discord_id = '$discord_id_esc' AND symbol = '$symbol_esc' LIMIT 1");
    
    if ($result && $result->num_rows > 0) {
        send_response("You're already subscribed to **$symbol** alerts!\n\nUse `/mystocks` to see your subscriptions.");
        return;
    }
    
    // Check subscription limit (max 20)
    $result = $conn->query("SELECT COUNT(*) as cnt FROM stock_subscriptions WHERE discord_id = '$discord_id_esc'");
    $count_row = $result ? $result->fetch_assoc() : null;
    $count = $count_row ? intval($count_row['cnt']) : 0;
    
    if ($count >= 20) {
        send_response("You've reached the maximum of 20 stock subscriptions.\n\nUse `/stockunsub <symbol>` to remove some first.");
        return;
    }
    
    $conn->query("INSERT INTO stock_subscriptions (discord_id, symbol, created_at) VALUES ('$discord_id_esc', '$symbol_esc', NOW())");
    
    $content = "✅ **Subscribed to $symbol alerts!**\n\n";
    $content .= "You'll get a DM when our algorithm picks this stock.\n\n";
    $content .= "Use `/mystocks` to see all subscriptions.\n";
    $content .= "Use `/stockunsub $symbol` to unsubscribe.";
    
    send_response($content);
}

function handle_stockunsub_command($discord_id, $symbol) {
    if (empty($symbol)) {
        send_response("Please specify a stock symbol.\n\nUsage: `/stockunsub AAPL`");
        return;
    }
    
    $symbol = strtoupper(trim($symbol));
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $symbol_esc = $conn->real_escape_string($symbol);
    
    $result = $conn->query("SELECT id FROM stock_subscriptions WHERE discord_id = '$discord_id_esc' AND symbol = '$symbol_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        send_response("You're not subscribed to **$symbol**.\n\nUse `/mystocks` to see your subscriptions.");
        return;
    }
    
    $conn->query("DELETE FROM stock_subscriptions WHERE discord_id = '$discord_id_esc' AND symbol = '$symbol_esc'");
    
    send_response("✅ **Unsubscribed from $symbol alerts.**\n\nUse `/mystocks` to see remaining subscriptions.");
}

function handle_mystocks_command($discord_id) {
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    ensure_stock_subscriptions_table($conn);
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    
    $result = $conn->query("SELECT symbol, created_at FROM stock_subscriptions WHERE discord_id = '$discord_id_esc' ORDER BY symbol");
    
    if (!$result || $result->num_rows === 0) {
        send_response("**You have no stock subscriptions.**\n\nUse `/stocksub <symbol>` to subscribe to alerts when a stock is picked.\n\nExample: `/stocksub AAPL`");
        return;
    }
    
    $subs = array();
    while ($row = $result->fetch_assoc()) {
        $subs[] = $row;
    }
    
    // Fetch current picks to check if any subscribed stocks are active
    $data = fetch_stock_data('daily-stocks.json');
    $current_symbols = array();
    if ($data && isset($data['stocks'])) {
        foreach ($data['stocks'] as $stock) {
            if (isset($stock['symbol'])) {
                $current_symbols[] = strtoupper($stock['symbol']);
            }
        }
    }
    
    $content = "**📋 Your Stock Subscriptions** (" . count($subs) . "/20)\n\n";
    
    foreach ($subs as $sub) {
        $sym = $sub['symbol'];
        $date = date('M j', strtotime($sub['created_at']));
        
        $is_active = in_array(strtoupper($sym), $current_symbols);
        $status = $is_active ? '🟢 ACTIVE PICK' : '';
        
        $content .= "• **$sym** — subscribed $date $status\n";
    }
    
    $content .= "\nUse `/stockunsub <symbol>` to unsubscribe.\n";
    $content .= "Use `/stock <symbol>` to see pick details.\n";
    $content .= "\n📈 Browse all picks: https://findtorontoevents.ca/findstocks/";
    
    send_response($content);
}

function ensure_stock_subscriptions_table($conn) {
    $sql = "CREATE TABLE IF NOT EXISTS stock_subscriptions (
        id INT AUTO_INCREMENT PRIMARY KEY,
        discord_id VARCHAR(32) NOT NULL,
        symbol VARCHAR(10) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_notified_at TIMESTAMP NULL,
        UNIQUE KEY unique_sub (discord_id, symbol),
        INDEX idx_symbol (symbol),
        INDEX idx_discord (discord_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4";
    
    $conn->query($sql);
}

// ============================================================================
// WEATHER Command
// ============================================================================

function handle_weather_command($location) {
    if (empty($location)) {
        send_response("Please specify a location.\n\nUsage: `/weather Toronto` or `/weather M5V 3A8`");
        return;
    }
    
    // Try to get weather data
    // For now, provide a helpful message since we'd need an API key
    $content = "**🌤️ Weather for $location**\n\n";
    $content .= "Weather data coming soon!\n\n";
    $content .= "For now, check:\n";
    $content .= "• [Environment Canada](https://weather.gc.ca/)\n";
    $content .= "• [Weather Network](https://www.theweathernetwork.com/)\n";
    
    send_response($content);
}

// ============================================================================
// MENTAL HEALTH Command
// ============================================================================

function handle_mentalhealth_command($topic) {
    $topic = strtolower(trim(isset($topic) ? $topic : ''));
    
    // Crisis resources (default)
    if ($topic === 'crisis' || empty($topic)) {
        $content = "**💚 Mental Health Resources**\n\n";
        $content .= "**🆘 Crisis Lines (24/7)**\n";
        $content .= "• **Canada Suicide Prevention:** 988\n";
        $content .= "• **Crisis Text Line:** Text HOME to 741741\n";
        $content .= "• **Kids Help Phone (under 20):** 1-800-668-6868\n";
        $content .= "• **Trans Lifeline:** 1-877-330-6366\n";
        $content .= "• **Veterans Crisis Line:** 1-800-273-8255 (Press 1)\n\n";
        
        if (empty($topic)) {
            $content .= "**More Topics:**\n";
            $content .= "`/mentalhealth breathing` - Breathing exercises\n";
            $content .= "`/mentalhealth grounding` - 5-4-3-2-1 grounding technique\n";
            $content .= "`/mentalhealth panic` - Panic attack help\n";
            $content .= "`/mentalhealth games` - Distraction games & apps\n";
            $content .= "`/mentalhealth demographics` - LGBTQ+, BIPOC specific support\n";
        }
        
        $content .= "\n💙 You matter. Help is available.";
        send_response($content);
        return;
    }
    
    // Breathing exercises
    if ($topic === 'breathing' || $topic === 'breathe') {
        $content = "**🌬️ Breathing Exercises**\n\n";
        $content .= "**Box Breathing (4-4-4-4)**\n";
        $content .= "1. Breathe IN for 4 seconds\n";
        $content .= "2. HOLD for 4 seconds\n";
        $content .= "3. Breathe OUT for 4 seconds\n";
        $content .= "4. HOLD for 4 seconds\n";
        $content .= "Repeat 4 times\n\n";
        $content .= "**4-7-8 Technique (for sleep/calm)**\n";
        $content .= "1. Breathe IN for 4 seconds\n";
        $content .= "2. HOLD for 7 seconds\n";
        $content .= "3. Breathe OUT for 8 seconds\n";
        $content .= "Repeat 3-4 times\n\n";
        $content .= "💙 Take your time. You're doing great.";
        send_response($content);
        return;
    }
    
    // Grounding technique
    if ($topic === 'grounding' || $topic === 'ground' || $topic === '54321') {
        $content = "**🌍 5-4-3-2-1 Grounding Technique**\n\n";
        $content .= "When feeling anxious or overwhelmed, name:\n\n";
        $content .= "**5** things you can **SEE** 👀\n";
        $content .= "**4** things you can **TOUCH** ✋\n";
        $content .= "**3** things you can **HEAR** 👂\n";
        $content .= "**2** things you can **SMELL** 👃\n";
        $content .= "**1** thing you can **TASTE** 👅\n\n";
        $content .= "Take your time with each one. This brings you back to the present moment.\n\n";
        $content .= "💙 You are safe. You are here.";
        send_response($content);
        return;
    }
    
    // Panic attack help
    if ($topic === 'panic' || $topic === 'attack' || $topic === 'anxiety') {
        $content = "**😰 Panic Attack Help**\n\n";
        $content .= "**Remember: Panic attacks are NOT dangerous. They WILL pass.**\n\n";
        $content .= "**Immediate steps:**\n";
        $content .= "1. Find somewhere to sit if possible\n";
        $content .= "2. Put your hand on your chest - feel your heartbeat\n";
        $content .= "3. Slow your breathing (try `/mentalhealth breathing`)\n";
        $content .= "4. Ground yourself (try `/mentalhealth grounding`)\n";
        $content .= "5. Remind yourself: \"This will pass\"\n\n";
        $content .= "**During a panic attack:**\n";
        $content .= "• Don't fight it - let it pass through\n";
        $content .= "• Splash cold water on your face\n";
        $content .= "• Hold an ice cube\n";
        $content .= "• Focus on something specific around you\n\n";
        $content .= "💙 You've survived every panic attack so far. You'll survive this one too.";
        send_response($content);
        return;
    }
    
    // Games and distractions
    if ($topic === 'games' || $topic === 'distraction' || $topic === 'apps') {
        $content = "**🎮 Distraction Games & Apps**\n\n";
        $content .= "**Free Calming Games:**\n";
        $content .= "• **Candy Crush** - Simple matching\n";
        $content .= "• **2048** - Number puzzle\n";
        $content .= "• **Alto's Odyssey** - Peaceful snowboarding\n";
        $content .= "• **Stardew Valley** - Relaxing farm sim\n\n";
        $content .= "**Mental Health Apps:**\n";
        $content .= "• **Calm** - Meditation & sleep\n";
        $content .= "• **Headspace** - Guided meditation\n";
        $content .= "• **Woebot** - AI therapy chatbot (free)\n";
        $content .= "• **What's Up** - CBT & ACT tools (free)\n";
        $content .= "• **Finch** - Self-care pet app\n\n";
        $content .= "💙 It's okay to distract yourself. Take care of you.";
        send_response($content);
        return;
    }
    
    // Demographics / specific support
    if ($topic === 'demographics' || $topic === 'lgbtq' || $topic === 'bipoc' || $topic === 'specific') {
        $content = "**🏳️‍🌈 Specific Support Lines**\n\n";
        $content .= "**LGBTQ+:**\n";
        $content .= "• Trevor Project: 1-866-488-7386\n";
        $content .= "• Trans Lifeline: 1-877-330-6366\n";
        $content .= "• LGBT National Hotline: 1-888-843-4564\n\n";
        $content .= "**BIPOC:**\n";
        $content .= "• BlackLine: 1-800-604-5841\n";
        $content .= "• AAKOMA Project: aakoma.org\n";
        $content .= "• Native & Indigenous: 1-800-273-8255\n\n";
        $content .= "**Other:**\n";
        $content .= "• Veterans: 1-800-273-8255 (Press 1)\n";
        $content .= "• Deaf/Hard of Hearing: 711 (relay)\n";
        $content .= "• Postpartum: 1-800-944-4773\n\n";
        $content .= "💙 You deserve support that understands you.";
        send_response($content);
        return;
    }
    
    // Unknown topic - show all options
    $content = "**💚 Mental Health Resources**\n\n";
    $content .= "Available topics:\n";
    $content .= "`/mentalhealth` - Crisis lines (default)\n";
    $content .= "`/mentalhealth breathing` - Breathing exercises\n";
    $content .= "`/mentalhealth grounding` - 5-4-3-2-1 technique\n";
    $content .= "`/mentalhealth panic` - Panic attack help\n";
    $content .= "`/mentalhealth games` - Distraction apps & games\n";
    $content .= "`/mentalhealth demographics` - LGBTQ+, BIPOC, specific support\n\n";
    $content .= "💙 Help is always available: **988** (Suicide Prevention)";
    send_response($content);
}

// ============================================================================
// GENERAL Commands
// ============================================================================

function handle_link_command($discord_id) {
    $conn = get_db_connection();
    
    if ($conn && $discord_id) {
        $discord_id_esc = $conn->real_escape_string($discord_id);
        $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
        
        if ($result && $result->num_rows > 0) {
            send_response("✅ **Your Discord is already linked!**\n\nManage at: https://findtorontoevents.ca/fc/");
            return;
        }
    }
    
    send_response("**Link your Discord to FavCreators:**\n\n1. Go to https://findtorontoevents.ca/fc/\n2. Log in or create an account\n3. Click 'Link Discord' in Account panel");
}

function handle_help_command() {
    $content = "**FindTorontoEvents Bot — All Commands**\n";
    $content .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";
    
    $content .= "**🎭 Creators**\n";
    $content .= "`/live` - See which tracked creators are live\n";
    $content .= "`/creators` - List creators with notifications enabled\n";
    $content .= "`/posts <creator>` - See latest posts from a creator\n";
    $content .= "`/about <creator>` - Get info about a creator\n\n";
    
    $content .= "**📅 Events**\n";
    $content .= "`/events <search> [when]` - Find Toronto events\n";
    $content .= "`/myevents` - See your saved events\n";
    $content .= "`/subscribe <category> [frequency]` - Auto-notifications\n";
    $content .= "`/unsubscribe <category>` - Stop auto-notifications\n";
    $content .= "`/mysubs` - View your subscriptions\n\n";
    
    $content .= "**🎬 Movies & TV**\n";
    $content .= "`/movies [search] [type]` - Search movies & TV shows\n";
    $content .= "`/newreleases [type] [period]` - New releases this week/month\n";
    $content .= "`/trailers <title>` - Get trailer for a movie or show\n\n";
    
    $content .= "**📈 Stocks**\n";
    $content .= "`/stocks [rating]` - View today's AI stock picks\n";
    $content .= "`/stock <symbol>` - Get details about a stock pick\n";
    $content .= "`/stockperf` - View performance statistics\n";
    $content .= "`/stocksub <symbol>` - Subscribe to stock alerts\n";
    $content .= "`/stockunsub <symbol>` - Unsubscribe from alerts\n";
    $content .= "`/mystocks` - View your stock subscriptions\n\n";
    
    $content .= "**🌤️ Weather**\n";
    $content .= "`/weather <location>` - Weather alerts & RealFeel\n\n";
    
    $content .= "**📍 Near Me / Location Finder**\n";
    $content .= "`/nearme <query> [location] [filter] [dietary] [radius]` - Find nearby places\n";
    $content .= "  Examples: `coffee shops`, `halal pizza`, `washrooms`, `pharmacy`\n";
    $content .= "  Location: intersection, landmark, or postal code\n";
    $content .= "  Filters: Open Now, Open Late, Open 24/7, Top Rated\n";
    $content .= "  Dietary: Halal, Vegan, Kosher, Vegetarian, Gluten-Free\n\n";
    
    $content .= "**🌍 World Events**\n";
    $content .= "`/worldevents [range]` - See what's happening in the world\n";
    $content .= "  Super Bowl, Oscars, Olympics, holidays, breaking news, and more\n";
    $content .= "  Range: Today, This Week, Next Few Days\n\n";
    
    $content .= "**💚 Mental Health**\n";
    $content .= "`/mentalhealth [topic]` - Crisis lines, breathing, grounding, panic help\n\n";
    
    $content .= "**🎯 Accountability Coach**\n";
    $content .= "`/fc-coach dashboard` - View all tasks & progress\n";
    $content .= "`/fc-coach setup` - Create a new habit/task\n";
    $content .= "`/fc-coach checkin` - Log task completion\n";
    $content .= "`/fc-coach status` - View task progress\n";
    $content .= "`/fc-coach templates` - See available templates\n";
    $content .= "`/fc-gym` - Log gym workout with details\n";
    $content .= "`/fc-timer` - Timer for activities\n";
    $content .= "`/fc-stats` - Set/view personal stats\n";
    $content .= "🌐 Web: https://findtorontoevents.ca/fc/#/accountability\n\n";
    
    $content .= "**📊 Daily Picks — Live Signals**\n";
    $content .= "`/fc-crypto [timeline] [budget]` - Daily crypto picks from 19 algorithms\n";
    $content .= "`/fc-forex [timeline] [budget]` - Daily forex picks (8 pairs)\n";
    $content .= "`/fc-realtime [asset]` - Recent winning trades across all markets\n";
    $content .= "`/fc-momentum [asset]` - Highest-conviction picks most likely to continue up\n";
    $content .= "`/fc-picks [asset] [timeline] [budget]` - Unified picks across all markets\n\n";

    $content .= "**ℹ️ General**\n";
    $content .= "`/info [feature]` - See all site apps & features\n";
    $content .= "`/link` - Link your Discord account\n";
    $content .= "`/help` - Show this command list\n\n";
    
    $content .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
    $content .= "🌐 **Website:** https://findtorontoevents.ca/";
    send_response($content);
}

function handle_info_command($feature) {
    $features = array(
        'events' => array(
            'emoji' => '🎉',
            'name' => 'Toronto Events',
            'url' => 'https://findtorontoevents.ca/',
            'short' => 'Daily events in Toronto',
            'long' => "**🎉 Toronto Events**\nhttps://findtorontoevents.ca/\n\nBrowse 1000+ daily events in Toronto:\n• **Filters** — Dating, music, comedy, free, sports & more\n• **Time filters** — Today, tomorrow, weekend, this week\n• **Categories** — Concerts, festivals, workshops, networking\n• **Save events** — Link Discord to save favorites\n\nUse `/events <search> [when]` to search directly from Discord!"
        ),
        'creators' => array(
            'emoji' => '💎',
            'name' => 'Fav Creators',
            'url' => 'https://findtorontoevents.ca/fc/',
            'short' => 'Never miss when your favorites go live',
            'long' => "**💎 Fav Creators**\nhttps://findtorontoevents.ca/fc/\n\nTrack your favorite streamers in one dashboard:\n• **Multi-platform** — TikTok, Twitch, Kick, YouTube\n• **Live alerts** — See who's streaming now\n• **Recent posts** — Latest content in one feed\n• **Discord notifications** — Get DMs when creators go live\n\nUse `/live` to see who's live, `/creators` to list your tracked creators!"
        ),
        'trailers' => array(
            'emoji' => '🎬',
            'name' => 'Movie/TV Trailers',
            'url' => 'https://findtorontoevents.ca/movieshows2/',
            'short' => 'TikTok-style trailer browsing',
            'long' => "**🎬 Movie/TV Show Trailers**\n\n3 versions to choose from:\n• **V1** — https://findtorontoevents.ca/MOVIESHOWS/\n  Toronto theater info, IMDb + RT ratings, emoji reactions\n\n• **V2** — https://findtorontoevents.ca/movieshows2/\n  TMDB integration, genre filters, playlist export/import\n\n• **V3** — https://findtorontoevents.ca/movieshows3/\n  User accounts, likes, auto-scroll, queue\n\nSwipe through trailers to find your next binge!"
        ),
        'stocks' => array(
            'emoji' => '📈',
            'name' => 'Stock Ideas',
            'url' => 'https://findtorontoevents.ca/findstocks/',
            'short' => 'AI-validated picks, updated daily',
            'long' => "**📈 Stock Ideas**\nhttps://findtorontoevents.ca/findstocks/\n\nDaily picks from 11+ algorithms, AI cross-validated:\n• **Fresh picks** — Updated daily before market open\n• **Regime-aware** — Adapts to market conditions\n• **Slippage tested** — Realistic execution modeling\n• **Multi-algo** — Momentum, mean-reversion, ML models\n\n*Not financial advice. Do your own research.*"
        ),
        'mental' => array(
            'emoji' => '🧠',
            'name' => 'Mental Health',
            'url' => 'https://findtorontoevents.ca/MENTALHEALTHRESOURCES/',
            'short' => 'Wellness games, crisis support & tools',
            'long' => "**🧠 Mental Health Resources**\nhttps://findtorontoevents.ca/MENTALHEALTHRESOURCES/\n\nFree wellness toolkit:\n• **🎮 Wellness games** — Breathing, grounding, meditation\n• **🆘 Crisis lines** — 24/7 support by country\n• **🌍 Global resources** — LGBTQ+, youth, veterans & more\n\n**If in crisis:**\n• 🇨🇦 Canada: 1-833-456-4566\n• 🇺🇸 USA: 988 or text HOME to 741741"
        ),
        'jobs' => array(
            'emoji' => '💼',
            'name' => '$100K+ Jobs',
            'url' => 'https://findtorontoevents.ca/gotjob/',
            'short' => 'Toronto tech & creative manager roles',
            'long' => "**💼 \$100K+ Jobs**\nhttps://findtorontoevents.ca/gotjob/\n\nSkip the \$60K listings:\n• **Salary filter** — Set your minimum (\$100K+)\n• **11+ sources** — Adzuna, Greenhouse, LinkedIn & more\n• **Remote options** — Filter for remote-friendly roles\n• **Toronto focused** — Tech & creative manager roles\n\nAggregates 12,000+ listings daily."
        ),
        'windows' => array(
            'emoji' => '🛠️',
            'name' => 'Windows Boot Fixer',
            'url' => 'https://findtorontoevents.ca/WINDOWSFIXER/',
            'short' => 'Fix boot issues - EFI, winload.efi, BSOD',
            'long' => "**🛠️ Miracle Boot - Windows Recovery Toolkit**\nhttps://findtorontoevents.ca/WINDOWSFIXER/\n\nComprehensive recovery for Windows boot issues:\n• **💀 BSOD Fix** — Resolve INACCESSIBLE_BOOT_DEVICE\n• **🔄 Boot Repair** — Fix corrupted bootloaders & MBR\n• **💾 Recovery** — Restore Windows when it won't start\n• **🛡️ Safe** — No data loss, works offline\n\nFree download. Works with Windows 10/11."
        ),
        'coach' => array(
            'emoji' => '🎯',
            'name' => 'Accountability Coach',
            'url' => 'https://findtorontoevents.ca/fc/#/accountability',
            'short' => 'Track habits, streaks & goals',
            'long' => "**🎯 Accountability Coach**\nhttps://findtorontoevents.ca/fc/#/accountability\n\nYour personal habit-building system:\n• **📋 Templates** — Gym, mental health, self-care & more\n• **🔥 Streaks** — Bronze → Silver → Gold → Diamond → Savage\n• **🛡️ Shields** — Protect streaks from one-day misses\n• **⏱️ Timers** — Track time-based activities\n• **📊 Dashboard** — Visual progress & insights\n• **🤝 Partners** — Accountability buddies\n\n**Discord Commands:**\n`/fc-coach dashboard` — View all tasks\n`/fc-coach setup taskname:gym` — Create a task\n`/fc-gym` — Log workouts\n`/fc-stats` — Track personal stats"
        )
    );
    
    if (!empty($feature) && isset($features[$feature])) {
        send_response($features[$feature]['long']);
        return;
    }
    
    $content = "**🌐 FindTorontoEvents.ca - All Apps & Features**\n\n";
    
    foreach ($features as $key => $f) {
        $content .= $f['emoji'] . " **" . $f['name'] . "**\n";
        $content .= "   " . $f['short'] . "\n";
        $content .= "   " . $f['url'] . "\n\n";
    }
    
    $content .= "─────────────────────\n";
    $content .= "💡 Use `/fc-info <feature>` for detailed info about each app!\n";
    $content .= "Example: `/fc-info trailers` or `/fc-info stocks`";
    
    send_response($content);
}

// ============================================================================
// FEED Command
// ============================================================================

function handle_feed_command($discord_id, $count, $platform) {
    $conn = get_db_connection();
    
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        send_response("Your Discord is not linked to FavCreators yet!\n\nLink your account at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    
    $limit = 10;
    if (!empty($count) && intval($count) > 0) {
        $limit = min(intval($count), 25);
    }
    
    $where = "np.user_id = $user_id AND np.discord_notify = 1";
    if (!empty($platform)) {
        $platform_esc = $conn->real_escape_string($platform);
        $where .= " AND csu.platform = '$platform_esc'";
    }
    
    $sql = "SELECT csu.creator_name, csu.platform, csu.content_title, csu.content_preview, csu.content_url, csu.content_published_at
            FROM creator_status_updates csu
            JOIN notification_preferences np ON csu.creator_id COLLATE utf8mb4_unicode_ci = np.creator_id
            WHERE $where
            ORDER BY csu.content_published_at DESC
            LIMIT $limit";
    
    $result = $conn->query($sql);
    
    if (!$result || $result->num_rows === 0) {
        send_response("No recent updates from your tracked creators.\n\nManage notifications at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $lines = array();
    while ($row = $result->fetch_assoc()) {
        $name = $row['creator_name'];
        $plat = ucfirst($row['platform']);
        $title = $row['content_title'] ? $row['content_title'] : '';
        $preview = $row['content_preview'] ? $row['content_preview'] : '';
        $url = $row['content_url'] ? $row['content_url'] : '';
        $date = $row['content_published_at'] ? date('M j', strtotime($row['content_published_at'])) : '';
        
        // Skip placeholder content
        if (stripos($title, 'Download TikTok') !== false || stripos($title, 'Make Your Day') !== false) {
            continue;
        }
        
        $text = $title ? $title : substr($preview, 0, 80);
        if (!$title && strlen($preview) > 80) $text .= '...';
        
        $line = "**$name** [$plat]";
        if ($date) $line .= " — $date";
        $line .= "\n   $text";
        if ($url) $line .= "\n   $url";
        $lines[] = $line;
    }
    
    if (count($lines) === 0) {
        send_response("No recent updates from your tracked creators.\n\nManage at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $content = "**📰 Latest from your creators:**\n\n" . implode("\n\n", $lines);
    $content .= "\n\n🔍 Full feed: https://findtorontoevents.ca/fc/";
    send_response($content);
}

// ============================================================================
// NOTIFY MODE Command
// ============================================================================

function handle_notifymode_command($discord_id, $mode) {
    if (empty($mode)) {
        send_response("Please specify a notification mode.\n\nUsage: `/fc-notifymode <mode>`\n• `channel` — Notifications in #notifications channel only\n• `dm` — Private DMs only\n• `both` — Both channel and DM");
        return;
    }
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        send_response("Your Discord is not linked to FavCreators yet!\n\nLink your account at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    $mode_esc = $conn->real_escape_string($mode);
    
    // Update or insert notification mode preference
    $check = $conn->query("SELECT id FROM user_settings WHERE user_id = $user_id AND setting_key = 'discord_notify_mode' LIMIT 1");
    
    if ($check && $check->num_rows > 0) {
        $conn->query("UPDATE user_settings SET setting_value = '$mode_esc' WHERE user_id = $user_id AND setting_key = 'discord_notify_mode'");
    } else {
        // Try to insert; if user_settings table doesn't exist, just acknowledge
        $conn->query("INSERT INTO user_settings (user_id, setting_key, setting_value) VALUES ($user_id, 'discord_notify_mode', '$mode_esc')");
    }
    
    $mode_labels = array(
        'channel' => 'Channel only (#notifications)',
        'dm' => 'DM only (private messages)',
        'both' => 'Both channel and DM'
    );
    $label = isset($mode_labels[$mode]) ? $mode_labels[$mode] : $mode;
    
    send_response("✅ **Notification mode set to: $label**\n\nYou can change this anytime with `/fc-notifymode`.");
}


// ============================================================================
// NEAR ME / LOCATION FINDER
// ============================================================================

function handle_nearme_command($query, $location, $filter, $dietary, $radius) {
    if (empty($query)) {
        send_response("Please specify what you're looking for.\n\nUsage: `/fc-nearme query:coffee shops`\n\nExamples:\n• `/fc-nearme query:halal pizza location:Yonge and Dundas filter:Open Now`\n• `/fc-nearme query:washrooms location:Eaton Centre`\n• `/fc-nearme query:pharmacy filter:Open 24/7`\n• `/fc-nearme query:homeless shelter`");
        return;
    }
    
    // Build API URL
    $api_base = dirname(__FILE__) . '/nearme.php';
    
    // We need to call nearme.php via HTTP (since it outputs JSON directly)
    $api_url = 'https://findtorontoevents.ca/fc/api/nearme.php';
    
    $params = array();
    $params['query'] = $query;
    
    // Location defaults to downtown Toronto
    $default_lat = 43.6532;
    $default_lng = -79.3832;
    
    if (!empty($location)) {
        $params['location'] = $location;
    } else {
        $params['lat'] = $default_lat;
        $params['lng'] = $default_lng;
    }
    
    // Filters
    if (!empty($filter)) {
        if ($filter === 'open_now' || $filter === 'open_247') {
            $params['open_now'] = 'true';
        }
        if ($filter === 'open_late') {
            $params['open_now'] = 'true';
            $params['open_at'] = '23:00';
        }
        if ($filter === 'top_rated') {
            $params['sort'] = 'RATING';
        }
    }
    
    if (!empty($dietary)) {
        $params['dietary'] = $dietary;
    }
    
    if (!empty($radius)) {
        $params['radius'] = intval($radius) * 1000; // km to meters
    }
    
    $params['limit'] = 10;
    
    // Build query string
    $qs = '';
    foreach ($params as $k => $v) {
        if ($qs !== '') $qs .= '&';
        $qs .= urlencode($k) . '=' . urlencode($v);
    }
    
    $url = $api_url . '?' . $qs;
    
    // Call the API
    $context = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'timeout' => 15,
            'header' => "User-Agent: FavCreators-Discord-Bot/1.0\r\n"
        )
    ));
    
    $response = @file_get_contents($url, false, $context);
    
    // Fallback to curl
    if ($response === false && function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array('User-Agent: FavCreators-Discord-Bot/1.0'));
        $response = curl_exec($ch);
        curl_close($ch);
    }
    
    if ($response === false) {
        send_response("Could not reach the places search service. Please try again later.");
        return;
    }
    
    $data = json_decode($response, true);
    
    if (!is_array($data) || !isset($data['ok']) || !$data['ok']) {
        $err = isset($data['error']) ? $data['error'] : 'Unknown error';
        if (strpos($err, 'API key') !== false) {
            send_response("The Near Me feature needs a Foursquare API key to be configured.\n\nThe site admin needs to add `FOURSQUARE_API_KEY` to the server configuration.\nGet a free key at: https://foursquare.com/developers/signup");
        } else {
            send_response("Search error: " . $err);
        }
        return;
    }
    
    // Handle crisis response
    if (isset($data['is_crisis']) && $data['is_crisis']) {
        _nearme_discord_crisis_response($data, $query);
        return;
    }
    
    // Format results
    _nearme_discord_results_response($data, $query, $location, $dietary, $filter);
}

function _nearme_discord_crisis_response($data, $query) {
    $content = "**24/7 Resources Available Now**\n";
    $content .= "━━━━━━━━━━━━━━━━━━━━━━━\n\n";
    
    if (isset($data['crisis_resources']) && is_array($data['crisis_resources'])) {
        foreach ($data['crisis_resources'] as $r) {
            $name = isset($r['name']) ? $r['name'] : '';
            $phone = isset($r['phone']) ? $r['phone'] : '';
            $hours = isset($r['hours']) ? $r['hours'] : '';
            $type = isset($r['type']) ? $r['type'] : '';
            $address = isset($r['address']) ? $r['address'] : '';
            
            $content .= "**" . $name . "**";
            if ($phone !== '') $content .= " — 📞 `" . $phone . "`";
            $content .= "\n";
            if ($hours !== '') $content .= "🕐 " . $hours;
            if ($type !== '') $content .= " · " . $type;
            $content .= "\n";
            if ($address !== '') $content .= "📍 " . $address . "\n";
            $content .= "\n";
        }
    }
    
    // Also show Foursquare results if any
    if (isset($data['results']) && is_array($data['results']) && count($data['results']) > 0) {
        $content .= "\n**Also found nearby:**\n";
        $count = 0;
        foreach ($data['results'] as $r) {
            if ($count >= 5) break;
            $count++;
            $name = isset($r['name']) ? $r['name'] : 'Unknown';
            $dist = isset($r['distance_m']) ? $r['distance_m'] : 0;
            $phone = isset($r['phone']) ? $r['phone'] : '';
            $maps = isset($r['maps_url']) ? $r['maps_url'] : '';
            
            $dist_str = ($dist < 1000) ? $dist . 'm' : round($dist / 1000, 1) . 'km';
            
            $content .= $count . ". **" . $name . "** — " . $dist_str . "\n";
            if ($phone !== '') $content .= "   📞 " . $phone . "\n";
            if ($maps !== '') $content .= "   🗺️ " . $maps . "\n";
        }
    }
    
    send_response($content);
}

function _nearme_discord_results_response($data, $query, $location, $dietary, $filter) {
    $results = isset($data['results']) ? $data['results'] : array();
    $total = isset($data['total']) ? $data['total'] : 0;
    
    if ($total === 0) {
        $content = "**No results found** for \"" . $query . "\"";
        if (!empty($location)) $content .= " near " . $location;
        $content .= ".\n\n";
        $content .= "**Next steps:**\n";
        $content .= "• Search [Google Maps](https://www.google.com/maps/search/" . urlencode($query) . ") for \"" . $query . "\"\n";
        $content .= "• Try a broader search term or increase the radius\n";
        if (!empty($dietary)) $content .= "• Try without the dietary filter first\n";
        $content .= "• Call **311** for Toronto city services\n";
        $content .= "• Check Uber Eats, DoorDash, or SkipTheDishes apps\n";
        send_response($content);
        return;
    }
    
    // Header
    $content = "**" . ucwords($query) . "**";
    $loc_resolved = '';
    if (isset($data['location']) && isset($data['location']['resolved_from'])) {
        $loc_resolved = $data['location']['resolved_from'];
    }
    if (!empty($location)) {
        $content .= " near **" . $location . "**";
    } else if ($loc_resolved !== '' && $loc_resolved !== 'coordinates' && $loc_resolved !== 'default (downtown Toronto)') {
        $content .= " near **" . $loc_resolved . "**";
    }
    if (!empty($dietary)) $content .= " (" . $dietary . ")";
    $content .= "\n━━━━━━━━━━━━━━━━━━━━━━━\n\n";
    
    // Results (show up to 5 in first page)
    $per_page = 5;
    $page_results = array_slice($results, 0, $per_page);
    
    $num = 0;
    foreach ($page_results as $r) {
        $num++;
        $name = isset($r['name']) ? $r['name'] : 'Unknown';
        $category = isset($r['category']) ? $r['category'] : '';
        $dist = isset($r['distance_m']) ? $r['distance_m'] : 0;
        $address = isset($r['address']) ? $r['address'] : '';
        $open_now = isset($r['open_now']) ? $r['open_now'] : null;
        $hours = isset($r['hours']) ? $r['hours'] : '';
        $hours_detail = isset($r['hours_detail']) ? $r['hours_detail'] : '';
        $rating = isset($r['rating']) ? $r['rating'] : 0;
        $price = isset($r['price']) ? $r['price'] : '';
        $phone = isset($r['phone']) ? $r['phone'] : '';
        $maps_url = isset($r['maps_url']) ? $r['maps_url'] : '';
        $dietary_notes = isset($r['dietary_notes']) ? $r['dietary_notes'] : '';
        
        $dist_str = ($dist < 1000) ? $dist . 'm' : round($dist / 1000, 1) . 'km';
        
        $content .= "**" . $num . ". " . $name . "** — " . $dist_str . "\n";
        
        if ($address !== '') $content .= "   📍 " . $address . "\n";
        
        // Open/closed status
        $status_parts = array();
        if ($open_now === true) {
            $s = "✅ Open now";
            if ($hours_detail !== '') $s .= " (" . $hours_detail . ")";
            $status_parts[] = $s;
        } else if ($open_now === false) {
            $s = "❌ Closed";
            if ($hours_detail !== '') $s .= " (" . $hours_detail . ")";
            $status_parts[] = $s;
        } else if ($hours !== '') {
            $status_parts[] = "🕐 " . $hours;
        }
        
        if ($rating > 0) {
            $status_parts[] = "⭐ " . number_format($rating, 1) . "/10";
        }
        if ($price !== '') {
            $status_parts[] = $price;
        }
        
        if (count($status_parts) > 0) {
            $content .= "   " . implode(" · ", $status_parts) . "\n";
        }
        
        if ($dietary_notes !== '') {
            $content .= "   🌿 " . $dietary_notes . "\n";
        }
        
        // Action links
        $actions = array();
        if ($maps_url !== '') $actions[] = "[Maps](" . $maps_url . ")";
        if ($phone !== '') $actions[] = "📞 " . $phone;
        if (count($actions) > 0) {
            $content .= "   " . implode(" · ", $actions) . "\n";
        }
        $content .= "\n";
    }
    
    // Footer tips
    $delivery_tip = isset($data['delivery_tip']) ? $data['delivery_tip'] : '';
    $pro_tip = isset($data['pro_tip']) ? $data['pro_tip'] : '';
    
    if ($delivery_tip !== '') {
        $content .= "🚚 " . $delivery_tip . "\n";
    }
    if ($pro_tip !== '') {
        $content .= "💡 " . $pro_tip . "\n";
    }
    
    if ($total > $per_page) {
        $content .= "\n_Showing " . $per_page . " of " . $total . " results. Use the website for full results._";
    }
    
    send_response($content);
}

// ============================================================================
// WORLD EVENTS Command
// ============================================================================

function handle_worldevents_command($range) {
    if (empty($range)) {
        $range = 'today';
    }
    $range = strtolower(trim($range));
    
    // Call the world events API
    $api_url = 'https://findtorontoevents.ca/fc/api/world_events.php?range=' . urlencode($range) . '&limit=15';
    
    $context = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'timeout' => 15,
            'header' => "User-Agent: FavCreators-Discord-Bot/1.0\r\n"
        )
    ));
    
    $response = @file_get_contents($api_url, false, $context);
    
    // Fallback to curl
    if ($response === false && function_exists('curl_init')) {
        $ch = curl_init($api_url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array('User-Agent: FavCreators-Discord-Bot/1.0'));
        $response = curl_exec($ch);
        curl_close($ch);
    }
    
    if ($response === false) {
        send_response("Could not fetch world events. Please try again later.\n\nVisit https://findtorontoevents.ca/ for more.");
        return;
    }
    
    $data = json_decode($response, true);
    
    if (!is_array($data) || !isset($data['ok']) || !$data['ok'] || !isset($data['events']) || count($data['events']) === 0) {
        send_response("No world events found for " . $range . ".\n\nTry `/fc-worldevents week` for this week's events.");
        return;
    }
    
    $events = $data['events'];
    $date = isset($data['date']) ? $data['date'] : date('Y-m-d');
    
    $range_label = 'Today';
    if ($range === 'week') $range_label = 'This Week';
    if ($range === '3days' || $range === 'upcoming') $range_label = 'Next Few Days';
    
    // Category emojis
    $cat_icons = array(
        'sports' => "\xF0\x9F\x8F\x86",
        'entertainment' => "\xF0\x9F\x8E\xAC",
        'holiday' => "\xF0\x9F\x8E\x89",
        'culture' => "\xF0\x9F\x8C\x8E",
        'tech' => "\xF0\x9F\x92\xBB",
        'world_news' => "\xF0\x9F\x93\xB0",
        'world' => "\xF0\x9F\x8C\x90",
        'armed_conflicts' => "\xE2\x9A\xA0\xEF\xB8\x8F",
        'disasters' => "\xF0\x9F\x8C\x8A",
        'politics_elections' => "\xF0\x9F\x97\xB3\xEF\xB8\x8F"
    );
    
    $content = "**\xF0\x9F\x8C\x8D World Events \xe2\x80\x94 " . $range_label . "** (" . $date . ")\n";
    $content .= "\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\xe2\x94\x80\n\n";
    
    // Split by importance
    $high = array();
    $medium = array();
    $normal = array();
    foreach ($events as $evt) {
        $imp = isset($evt['importance']) ? $evt['importance'] : 'normal';
        if ($imp === 'high') $high[] = $evt;
        else if ($imp === 'medium') $medium[] = $evt;
        else $normal[] = $evt;
    }
    
    // Featured events (high importance)
    if (count($high) > 0) {
        foreach ($high as $evt) {
            $cat = isset($evt['category']) ? $evt['category'] : 'world';
            $icon = isset($cat_icons[$cat]) ? $cat_icons[$cat] : "\xF0\x9F\x8C\x90";
            $title = isset($evt['title']) ? $evt['title'] : '';
            $desc = isset($evt['description']) ? $evt['description'] : '';
            $url = isset($evt['url']) ? $evt['url'] : '';
            
            $content .= $icon . " **" . $title . "** \xF0\x9F\x94\xB4\n";
            if ($desc !== '' && $desc !== $title) {
                $show_desc = (strlen($desc) > 150) ? substr($desc, 0, 150) . '...' : $desc;
                $content .= "   " . $show_desc . "\n";
            }
            if ($url !== '') {
                $content .= "   " . $url . "\n";
            }
            $content .= "\n";
        }
    }
    
    // Medium importance (top headlines)
    if (count($medium) > 0) {
        $content .= "**\xF0\x9F\x93\xB0 Top Headlines:**\n";
        $med_count = 0;
        foreach ($medium as $evt) {
            if ($med_count >= 5) break;
            $med_count++;
            $cat = isset($evt['category']) ? $evt['category'] : 'world';
            $icon = isset($cat_icons[$cat]) ? $cat_icons[$cat] : "\xF0\x9F\x93\xB0";
            $title = isset($evt['title']) ? $evt['title'] : '';
            $src = isset($evt['source']) ? $evt['source'] : '';
            $url = isset($evt['url']) ? $evt['url'] : '';
            
            $src_label = '';
            if ($src === 'bbc_news') $src_label = 'BBC';
            else if ($src === 'wikipedia') $src_label = 'Wikipedia';
            else if ($src === 'curated_calendar') $src_label = 'Calendar';
            
            $content .= $icon . " " . $title;
            if ($src_label !== '') $content .= " _(" . $src_label . ")_";
            $content .= "\n";
            if ($url !== '') $content .= "   " . $url . "\n";
        }
        $content .= "\n";
    }
    
    // Normal events (compact)
    if (count($normal) > 0) {
        $show_normal = (count($normal) > 5) ? 5 : count($normal);
        $content .= "**Also in the news:**\n";
        for ($i = 0; $i < $show_normal; $i++) {
            $evt = $normal[$i];
            $title = isset($evt['title']) ? $evt['title'] : '';
            if (strlen($title) > 80) $title = substr($title, 0, 80) . '...';
            $content .= "\xe2\x80\xa2 " . $title . "\n";
        }
        if (count($normal) > $show_normal) {
            $content .= "_...and " . (count($normal) - $show_normal) . " more stories_\n";
        }
    }
    
    $content .= "\n\xF0\x9F\x8C\x90 **Website:** https://findtorontoevents.ca/\n";
    $content .= "_Sources: Wikipedia, BBC World News, Curated Calendar_";

    send_response($content);
}

// ═══════════════════════════════════════════════════════════════════
// DAILY PICKS — Crypto, Forex, Realtime Wins, Momentum, Unified
// ═══════════════════════════════════════════════════════════════════

function _dp_fetch($action, $extra_params) {
    $url = "https://findtorontoevents.ca/live-monitor/api/daily_picks.php?action=" . urlencode($action);
    if ($extra_params) $url .= '&' . $extra_params;
    $context = stream_context_create(array('http' => array('timeout' => 15, 'user_agent' => 'FavCreators-Bot/1.0')));
    $json = @file_get_contents($url, false, $context);
    if (!$json) return null;
    return json_decode($json, true);
}

function _dp_format_pick($pick) {
    $sym = isset($pick['symbol']) ? $pick['symbol'] : '???';
    $type = isset($pick['signal_type']) ? $pick['signal_type'] : 'BUY';
    $entry = isset($pick['entry_price']) ? $pick['entry_price'] : 0;
    $curr = isset($pick['current_price']) ? $pick['current_price'] : $entry;
    $tp = isset($pick['target_tp_pct']) ? $pick['target_tp_pct'] : 0;
    $sl = isset($pick['target_sl_pct']) ? $pick['target_sl_pct'] : 0;
    $algo = isset($pick['algorithm']) ? $pick['algorithm'] : '';
    $strength = isset($pick['signal_strength']) ? $pick['signal_strength'] : 0;
    $hold = isset($pick['max_hold_hours']) ? $pick['max_hold_hours'] : 0;
    $tl = isset($pick['timeline_label']) ? $pick['timeline_label'] : '';
    $streak = isset($pick['win_streak']) ? (int)$pick['win_streak'] : 0;
    $dir_icon = ($type === 'BUY' || $type === 'LONG') ? "\xF0\x9F\x9F\xA2" : "\xF0\x9F\x94\xB4";
    $bar = '';
    $filled = (int)round($strength / 20);
    for ($i = 0; $i < 5; $i++) { $bar .= ($i < $filled) ? "\xe2\x96\x88" : "\xe2\x96\x91"; }
    $ac = isset($pick['asset_class']) ? $pick['asset_class'] : '';
    if ($ac === 'FOREX') { $es = number_format($entry, 5); $cs = number_format($curr, 5); }
    elseif ($entry > 1) { $es = '$' . number_format($entry, 2); $cs = '$' . number_format($curr, 2); }
    else { $es = '$' . number_format($entry, 6); $cs = '$' . number_format($curr, 6); }
    $line = "$dir_icon **$sym** $type @ $es";
    if ($curr != $entry && $curr > 0) {
        $cp = $entry > 0 ? round(($curr - $entry) / $entry * 100, 2) : 0;
        $ci = $cp >= 0 ? '+' : '';
        $line .= " (now $cs, {$ci}{$cp}%)";
    }
    $line .= "\n   TP: +{$tp}% | SL: -{$sl}% | Hold: {$hold}h ($tl)\n";
    $line .= "   Algo: $algo | Strength: $bar $strength/100\n";
    if ($streak >= 2) $line .= "   \xF0\x9F\x94\xA5 $streak consecutive wins!\n";
    return $line;
}

function _dp_format_win($win) {
    $sym = isset($win['symbol']) ? $win['symbol'] : '???';
    $asset = isset($win['asset_class']) ? $win['asset_class'] : '';
    $pnl = isset($win['realized_pnl']) ? $win['realized_pnl'] : 0;
    $pct = isset($win['realized_pct']) ? $win['realized_pct'] : 0;
    $algo = isset($win['algorithm']) ? $win['algorithm'] : '';
    $hold = isset($win['hold_hours']) ? round($win['hold_hours'], 1) : 0;
    $exit_time = isset($win['exit_time']) ? $win['exit_time'] : '';
    $pnl_str = ($pnl >= 0 ? '+' : '') . '$' . number_format(abs($pnl), 2);
    $pct_str = ($pct >= 0 ? '+' : '') . number_format($pct, 2) . '%';
    if ($asset === 'CRYPTO') $ai = "\xE2\x82\xBF";
    elseif ($asset === 'FOREX') $ai = "\xF0\x9F\x92\xB1";
    else $ai = "\xF0\x9F\x93\x88";
    $ts = ''; if ($exit_time && ($t = strtotime($exit_time))) $ts = ' (' . date('M j, g:ia', $t) . ')';
    return "\xe2\x9c\x85 $ai **$sym** $pnl_str ($pct_str) in {$hold}h \xe2\x80\x94 $algo$ts\n";
}

function _dp_format_perf($perf) {
    $total = isset($perf['total_trades_30d']) ? $perf['total_trades_30d'] : 0;
    $wr = isset($perf['win_rate']) ? $perf['win_rate'] : 0;
    $w = isset($perf['wins']) ? $perf['wins'] : 0;
    $l = isset($perf['losses']) ? $perf['losses'] : 0;
    $aw = isset($perf['avg_win_pct']) ? $perf['avg_win_pct'] : 0;
    $al = isset($perf['avg_loss_pct']) ? $perf['avg_loss_pct'] : 0;
    $best = isset($perf['best_algorithm']) ? $perf['best_algorithm'] : 'N/A';
    return "\n**30-Day Performance:**\nTrades: $total (W:$w L:$l) | Win Rate: {$wr}%\nAvg Win: +{$aw}% | Avg Loss: {$al}%\nBest Algo: $best\n";
}

function handle_crypto_picks_command($options) {
    $tl = get_option_value($options, 'timeline'); $bd = get_option_value($options, 'budget');
    if (!$tl) $tl = 'all';
    $params = "timeline=" . urlencode($tl); if ($bd) $params .= "&budget=" . urlencode($bd);
    $data = _dp_fetch('crypto', $params);
    if (!$data || !$data['ok']) { send_response("Could not fetch crypto picks. Try again later.\n\xE2\x82\xBF https://findtorontoevents.ca/live-monitor/live-monitor.html"); return; }
    $picks = isset($data['picks']) ? $data['picks'] : array();
    $c = count($picks); $gen = isset($data['generated_at']) ? $data['generated_at'] : '';
    $content = "**\xE2\x82\xBF Daily Crypto Picks**\n$c active signals | $gen\n";
    if ($tl !== 'all') { $labels = array('scalp'=>'Scalp (1-4h)','daytrader'=>'Day Trade (4-24h)','swing'=>'Swing (1-7d)'); $content .= "Timeline: " . (isset($labels[$tl]) ? $labels[$tl] : $tl) . "\n"; }
    $content .= "\n";
    if ($c === 0) { $content .= "_No active crypto signals. Signals refresh every 30 minutes._\n"; }
    else { $s = ($c > 5) ? 5 : $c; for ($i = 0; $i < $s; $i++) $content .= _dp_format_pick($picks[$i]) . "\n"; if ($c > $s) $content .= "_...and " . ($c-$s) . " more signals_\n"; }
    $wins = isset($data['recent_wins']) ? $data['recent_wins'] : array();
    if (count($wins) > 0) { $content .= "\n**Recent Crypto Wins (7d):**\n"; $sw = (count($wins) > 3) ? 3 : count($wins); for ($i = 0; $i < $sw; $i++) $content .= _dp_format_win($wins[$i]); }
    if (isset($data['performance_summary'])) $content .= _dp_format_perf($data['performance_summary']);
    if ($bd && isset($data['budget_guidance']['guidance'])) $content .= "\n\xF0\x9F\x92\xB0 **Budget ($bd):** " . $data['budget_guidance']['guidance'] . "\n";
    $content .= "\n\xE2\x82\xBF **Live Monitor:** https://findtorontoevents.ca/live-monitor/live-monitor.html\n";
    $content .= "_" . (isset($data['disclaimer']) ? $data['disclaimer'] : 'Not financial advice.') . "_";
    send_response($content);
}

function handle_forex_picks_command($options) {
    $tl = get_option_value($options, 'timeline'); $bd = get_option_value($options, 'budget');
    if (!$tl) $tl = 'all';
    $params = "timeline=" . urlencode($tl); if ($bd) $params .= "&budget=" . urlencode($bd);
    $data = _dp_fetch('forex', $params);
    if (!$data || !$data['ok']) { send_response("Could not fetch forex picks. Try again later.\n\xF0\x9F\x92\xB1 https://findtorontoevents.ca/live-monitor/live-monitor.html"); return; }
    $picks = isset($data['picks']) ? $data['picks'] : array();
    $c = count($picks); $gen = isset($data['generated_at']) ? $data['generated_at'] : '';
    $content = "**\xF0\x9F\x92\xB1 Daily Forex Picks**\n$c active signals | $gen\n";
    if ($tl !== 'all') { $labels = array('scalp'=>'Scalp (1-4h)','daytrader'=>'Day Trade (4-24h)','swing'=>'Swing (1-7d)'); $content .= "Timeline: " . (isset($labels[$tl]) ? $labels[$tl] : $tl) . "\n"; }
    $content .= "\n";
    if ($c === 0) { $content .= "_No active forex signals. Signals refresh every 30 minutes._\n_Pairs: EUR/USD, GBP/USD, USD/JPY, USD/CAD, AUD/USD, NZD/USD, USD/CHF, EUR/GBP_\n"; }
    else { $s = ($c > 5) ? 5 : $c; for ($i = 0; $i < $s; $i++) $content .= _dp_format_pick($picks[$i]) . "\n"; if ($c > $s) $content .= "_...and " . ($c-$s) . " more signals_\n"; }
    $wins = isset($data['recent_wins']) ? $data['recent_wins'] : array();
    if (count($wins) > 0) { $content .= "\n**Recent Forex Wins (7d):**\n"; $sw = (count($wins) > 3) ? 3 : count($wins); for ($i = 0; $i < $sw; $i++) $content .= _dp_format_win($wins[$i]); }
    if (isset($data['performance_summary'])) $content .= _dp_format_perf($data['performance_summary']);
    if ($bd && isset($data['budget_guidance']['guidance'])) $content .= "\n\xF0\x9F\x92\xB0 **Budget ($bd):** " . $data['budget_guidance']['guidance'] . "\n";
    $content .= "\n\xF0\x9F\x92\xB1 **Live Monitor:** https://findtorontoevents.ca/live-monitor/live-monitor.html\n";
    $content .= "_" . (isset($data['disclaimer']) ? $data['disclaimer'] : 'Not financial advice.') . "_";
    send_response($content);
}

function handle_realtime_wins_command($asset_filter) {
    $params = ($asset_filter && $asset_filter !== 'all') ? 'asset=' . urlencode($asset_filter) : '';
    $data = _dp_fetch('wins', $params);
    if (!$data || !$data['ok']) { send_response("Could not fetch recent wins. Try again later."); return; }
    $wins = isset($data['wins']) ? $data['wins'] : array();
    $gen = isset($data['generated_at']) ? $data['generated_at'] : '';
    $al = ($asset_filter && $asset_filter !== 'all') ? ' (' . strtoupper($asset_filter) . ')' : '';
    $content = "**\xF0\x9F\x8F\x86 Recent Winning Trades$al**\n" . count($wins) . " wins (7d) | $gen\n\n";
    if (count($wins) === 0) $content .= "_No winning trades in the last 7 days._\n";
    else { $s = (count($wins) > 10) ? 10 : count($wins); for ($i = 0; $i < $s; $i++) $content .= _dp_format_win($wins[$i]); if (count($wins) > $s) $content .= "_...and " . (count($wins)-$s) . " more_\n"; }
    if (isset($data['performance_summary'])) $content .= _dp_format_perf($data['performance_summary']);
    $content .= "\n\xF0\x9F\x93\x8A **Live Monitor:** https://findtorontoevents.ca/live-monitor/live-monitor.html\n";
    $content .= "_" . (isset($data['disclaimer']) ? $data['disclaimer'] : 'Not financial advice.') . "_";
    send_response($content);
}

function handle_momentum_command($asset_filter) {
    $params = ($asset_filter && $asset_filter !== 'all') ? 'asset=' . urlencode($asset_filter) : '';
    $data = _dp_fetch('momentum', $params);
    if (!$data || !$data['ok']) { send_response("Could not fetch momentum picks. Try again later."); return; }
    $picks = isset($data['picks']) ? $data['picks'] : array();
    $streaks = isset($data['win_streaks']) ? $data['win_streaks'] : array();
    $gen = isset($data['generated_at']) ? $data['generated_at'] : '';
    $al = ($asset_filter && $asset_filter !== 'all') ? ' (' . strtoupper($asset_filter) . ')' : '';
    $content = "**\xF0\x9F\x9A\x80 Momentum Picks$al \xe2\x80\x94 Most Likely to Continue Up**\n" . count($picks) . " high-conviction signals (70+) | $gen\n\n";
    if (count($picks) === 0) { $content .= "_No high-conviction signals now. Algorithms require strong multi-indicator confluence._\n_Signals refresh every 30 min across 36 assets._\n"; }
    else { $s = (count($picks) > 5) ? 5 : count($picks); for ($i = 0; $i < $s; $i++) $content .= _dp_format_pick($picks[$i]) . "\n"; if (count($picks) > $s) $content .= "_...and " . (count($picks)-$s) . " more_\n"; }
    if (count($streaks) > 0) { $content .= "\n**\xF0\x9F\x94\xA5 Win Streaks:**\n"; foreach ($streaks as $sk) $content .= "\xe2\x80\xa2 **" . $sk['symbol'] . "** (" . $sk['asset_class'] . ") \xe2\x80\x94 " . $sk['win_streak'] . " consecutive wins\n"; }
    if (isset($data['performance_summary'])) $content .= _dp_format_perf($data['performance_summary']);
    $content .= "\n\xF0\x9F\x9A\x80 **Live Monitor:** https://findtorontoevents.ca/live-monitor/live-monitor.html\n";
    $content .= "_" . (isset($data['disclaimer']) ? $data['disclaimer'] : 'Not financial advice.') . "_";
    send_response($content);
}

function handle_daily_picks_command($options) {
    $asset = get_option_value($options, 'asset');
    $tl = get_option_value($options, 'timeline'); $bd = get_option_value($options, 'budget');
    if (!$tl) $tl = 'all';
    if ($asset === 'CRYPTO') { handle_crypto_picks_command($options); return; }
    if ($asset === 'FOREX')  { handle_forex_picks_command($options); return; }
    if ($asset === 'STOCK') {
        $params = "timeline=" . urlencode($tl); if ($bd) $params .= "&budget=" . urlencode($bd);
        $data = _dp_fetch('stocks', $params);
        if (!$data || !$data['ok']) { send_response("Could not fetch stock signals. Try `/fc-stocks` for daily picks.\n\xF0\x9F\x93\x88 https://findtorontoevents.ca/findstocks/"); return; }
        $picks = isset($data['picks']) ? $data['picks'] : array();
        $content = "**\xF0\x9F\x93\x88 Stock Signals (Live Monitor)**\n" . count($picks) . " active | " . (isset($data['generated_at']) ? $data['generated_at'] : '') . "\n\n";
        if (count($picks) === 0) $content .= "_No active stock signals. NYSE hours only (9:30am-4pm ET). Try `/fc-stocks`._\n";
        else { $s = (count($picks) > 5) ? 5 : count($picks); for ($i = 0; $i < $s; $i++) $content .= _dp_format_pick($picks[$i]) . "\n"; }
        if (isset($data['performance_summary'])) $content .= _dp_format_perf($data['performance_summary']);
        $content .= "\n\xF0\x9F\x93\x88 https://findtorontoevents.ca/findstocks/\n_Not financial advice._";
        send_response($content); return;
    }
    // ALL
    $params = "timeline=" . urlencode($tl); if ($bd) $params .= "&budget=" . urlencode($bd);
    $data = _dp_fetch('all', $params);
    if (!$data || !$data['ok']) { send_response("Could not fetch daily picks. Try again later."); return; }
    $gen = isset($data['generated_at']) ? $data['generated_at'] : '';
    $tot = isset($data['total_picks']) ? $data['total_picks'] : 0;
    $content = "**\xF0\x9F\x93\x8A Daily Picks \xe2\x80\x94 All Markets**\n$tot active signals | $gen\n";
    if ($tl !== 'all') { $labels = array('scalp'=>'Scalp (1-4h)','daytrader'=>'Day Trade (4-24h)','swing'=>'Swing (1-7d)'); $content .= "Timeline: " . (isset($labels[$tl]) ? $labels[$tl] : $tl) . "\n"; }
    $content .= "\n";
    foreach (array('crypto' => "\xE2\x82\xBF Crypto", 'forex' => "\xF0\x9F\x92\xB1 Forex", 'stocks' => "\xF0\x9F\x93\x88 Stocks") as $key => $label) {
        $sec = isset($data[$key]['picks']) ? $data[$key]['picks'] : array();
        $content .= "**$label** (" . count($sec) . " signals)\n";
        if (count($sec) === 0) { $content .= "_No active signals_\n"; }
        else { $show = (count($sec) > 3) ? 3 : count($sec); for ($i = 0; $i < $show; $i++) $content .= _dp_format_pick($sec[$i]); if (count($sec) > $show) $content .= "_+" . (count($sec)-$show) . " more_\n"; }
        $content .= "\n";
    }
    if (isset($data['performance_summary'])) $content .= _dp_format_perf($data['performance_summary']);
    if ($bd && isset($data['budget_guidance']['guidance'])) $content .= "\n\xF0\x9F\x92\xB0 **Budget ($bd):** " . $data['budget_guidance']['guidance'] . "\n";
    $content .= "\n\xF0\x9F\x93\x8A **Live Monitor:** https://findtorontoevents.ca/live-monitor/live-monitor.html\n";
    $content .= "_" . (isset($data['disclaimer']) ? $data['disclaimer'] : 'Not financial advice.') . "_";
    send_response($content);
}
