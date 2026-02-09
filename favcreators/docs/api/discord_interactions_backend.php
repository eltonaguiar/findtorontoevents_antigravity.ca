<?php
/**
 * Discord Interactions Backend
 * Called by Cloudflare Worker after signature verification
 * PHP 5.2 compatible
 */

error_reporting(0);
ini_set('display_errors', 0);

// Start output buffering to capture any db_connect output
ob_start();

// Only accept POST
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    ob_end_clean();
    header('HTTP/1.1 405 Method Not Allowed');
    header('Content-Type: application/json');
    echo '{"error":"Method not allowed"}';
    exit;
}

// Parse interaction
$body = file_get_contents('php://input');
$interaction = json_decode($body, true);

if (!$interaction) {
    ob_end_clean();
    header('HTTP/1.1 400 Bad Request');
    header('Content-Type: application/json');
    echo '{"error":"Invalid JSON"}';
    exit;
}

$type = isset($interaction['type']) ? intval($interaction['type']) : 0;

// Handle PING (shouldn't reach here, worker handles it)
if ($type === 1) {
    ob_end_clean();
    header('Content-Type: application/json');
    echo '{"type":1}';
    exit;
}

// Handle slash commands (type 2)
if ($type === 2) {
    $data = isset($interaction['data']) ? $interaction['data'] : array();
    $command_name = isset($data['name']) ? $data['name'] : '';
    $user = isset($interaction['user']) ? $interaction['user'] : 
            (isset($interaction['member']['user']) ? $interaction['member']['user'] : array());
    $discord_id = isset($user['id']) ? $user['id'] : '';
    
    // Get options from command
    $options = isset($data['options']) ? $data['options'] : array();
    
    switch ($command_name) {
        case 'fc-live':
            handle_live_command($discord_id);
            break;
        case 'fc-creators':
            handle_creators_command($discord_id);
            break;
        case 'fc-posts':
            $creator_name = get_option_value($options, 'creator');
            $count = get_option_value($options, 'count');
            handle_posts_command($creator_name, $count ? intval($count) : 5);
            break;
        case 'fc-feed':
            $feed_count = get_option_value($options, 'count');
            $feed_platform = get_option_value($options, 'platform');
            handle_feed_command($discord_id, $feed_count ? intval($feed_count) : 10, $feed_platform ? $feed_platform : null);
            break;
        case 'fc-about':
            $creator_name = get_option_value($options, 'creator');
            handle_about_command($creator_name);
            break;
        case 'fc-events':
            $search = get_option_value($options, 'search');
            $timeframe = get_option_value($options, 'when');
            handle_events_command($search, $timeframe);
            break;
        case 'fc-myevents':
            handle_myevents_command($discord_id);
            break;
        case 'fc-subscribe':
            $category = get_option_value($options, 'category');
            $frequency = get_option_value($options, 'frequency');
            handle_subscribe_command($discord_id, $category, $frequency);
            break;
        case 'fc-unsubscribe':
            $category = get_option_value($options, 'category');
            handle_unsubscribe_command($discord_id, $category);
            break;
        case 'fc-mysubs':
            handle_mysubs_command($discord_id);
            break;
        case 'fc-link':
            handle_link_command($discord_id);
            break;
        case 'fc-help':
            handle_help_command();
            break;
        case 'fc-info':
            $feature = get_option_value($options, 'feature');
            handle_info_command($feature);
            break;
        // Movie/TV commands
        case 'fc-movies':
            $search = get_option_value($options, 'search');
            $content_type = get_option_value($options, 'type');
            handle_movies_command($search, $content_type, 0);
            break;
        case 'fc-newreleases':
            $content_type = get_option_value($options, 'type');
            $period = get_option_value($options, 'period');
            handle_newreleases_command($content_type, $period, 0);
            break;
        case 'fc-trailers':
            $title = get_option_value($options, 'title');
            handle_trailers_command($title);
            break;
        // Stock commands
        case 'fc-stocks':
            $rating = get_option_value($options, 'rating');
            handle_stocks_command($rating, 0);
            break;
        case 'fc-stock':
            $symbol = get_option_value($options, 'symbol');
            handle_stock_command($symbol);
            break;
        case 'fc-stockperf':
            handle_stockperf_command();
            break;
        case 'fc-stocksub':
            $symbol = get_option_value($options, 'symbol');
            handle_stocksub_command($discord_id, $symbol);
            break;
        case 'fc-stockunsub':
            $symbol = get_option_value($options, 'symbol');
            handle_stockunsub_command($discord_id, $symbol);
            break;
        case 'fc-mystocks':
            handle_mystocks_command($discord_id);
            break;
        // Weather commands
        case 'fc-weather':
            $location = get_option_value($options, 'location');
            handle_weather_command($location);
            break;
        case 'fc-jacket':
            $location = get_option_value($options, 'location');
            handle_jacket_command($location);
            break;
        // Mental Health Resources command
        case 'fc-mentalhealth':
            $topic = get_option_value($options, 'topic');
            handle_mentalhealth_command($topic);
            break;
        // Notification delivery mode command
        case 'fc-notifymode':
            $mode = get_option_value($options, 'mode');
            handle_notifymode_command($discord_id, $mode);
            break;
        // Accountability Status (standalone shortcut)
        case 'fc-status':
            require_once dirname(__FILE__) . '/accountability/handler.php';
            $result = handle_fc_status_command($discord_id, $options);
            send_response($result);
            break;
        // Accountability Score (standalone shortcut)
        case 'fc-score':
            require_once dirname(__FILE__) . '/accountability/handler.php';
            $result = handle_coach_score(_acc_get_db(), $discord_id);
            send_response($result);
            break;
        // Accountability Coach commands
        case 'fc-coach':
            $action = get_option_value($options, 'action');
            // Handle followup on/off directly (no handler.php dependency)
            if ($action === 'followup') {
                $followup_arg = get_option_value($options, 'value');
                if (!$followup_arg) $followup_arg = get_option_value($options, 'taskname');
                _handle_followup_command($discord_id, $followup_arg);
                break;
            }
            require_once dirname(__FILE__) . '/accountability/handler.php';
            $result = handle_fc_coach_command($discord_id, $action, $options);
            send_response($result);
            break;
        case 'fc-gym':
            require_once dirname(__FILE__) . '/accountability/handler.php';
            $result = handle_fc_gym_command($discord_id, $options);
            send_response($result);
            break;
        case 'fc-timer':
            require_once dirname(__FILE__) . '/accountability/handler.php';
            $action = get_option_value($options, 'action');
            $result = handle_fc_timer_command($discord_id, $action, $options);
            send_response($result);
            break;
        case 'fc-stats':
            require_once dirname(__FILE__) . '/accountability/handler.php';
            $action = get_option_value($options, 'action');
            $result = handle_fc_stats_command($discord_id, $action, $options);
            send_response($result);
            break;
        default:
            send_response("Unknown command. Use /fc-help to see available commands.");
    }
    exit;
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
            // Format: stocks_page:page:rating_filter
            $rating_filter = isset($parts[2]) ? $parts[2] : 'all';
            handle_stocks_command($rating_filter, $page, true);
            break;
        case 'goal_followup_optout':
            // Format: goal_followup_optout:discord_user_id
            $optout_discord_id = isset($parts[1]) ? $parts[1] : '';
            _handle_followup_optout_button($optout_discord_id);
            break;
        default:
            send_response("Unknown action.");
    }
    exit;
}

// Unknown type
ob_end_clean();
header('HTTP/1.1 400 Bad Request');
header('Content-Type: application/json');
echo '{"error":"Unhandled interaction type"}';
exit;

// ============================================================================
// Helper Functions
// ============================================================================

// PHP 5.2-compatible comparison functions (no anonymous closures)
function _cmp_ts_desc($a, $b) { return $b['ts'] - $a['ts']; }
function _cmp_live_then_ts($a, $b) {
    if ($a['is_live'] && !$b['is_live']) return -1;
    if (!$a['is_live'] && $b['is_live']) return 1;
    return $b['ts'] - $a['ts'];
}

function send_response($content, $ephemeral = true) {
    ob_end_clean();
    header('Content-Type: application/json');
    $response = array(
        'type' => 4,
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

function get_db_connection() {
    // Load config directly without db_connect.php to avoid header issues
    require_once dirname(__FILE__) . '/db_config.php';
    
    $conn = @new mysqli($servername, $username, $password, $dbname);
    if ($conn->connect_error) {
        return null;
    }
    return $conn;
}

function get_movies_db_connection() {
    // Connect to the movies/trailers database
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

function send_response_with_components($content, $components, $ephemeral = true, $is_update = false) {
    ob_end_clean();
    header('Content-Type: application/json');
    
    // Type 4 = new message, Type 7 = update existing message
    $response_type = $is_update ? 7 : 4;
    
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

/**
 * Handle /fc-coach followup on|off slash command.
 * Toggles morning goal follow-up DMs for the user.
 */
function _handle_followup_command($discord_id, $value) {
    if (!$discord_id) {
        send_response("Could not identify your account.");
        return;
    }

    $value = strtolower(trim($value));
    if ($value !== 'on' && $value !== 'off' && $value !== 'status') {
        send_response("**Morning Goal Follow-Up**\n\nUsage:\n`/fc-coach action:followup value:on` — Enable morning follow-ups\n`/fc-coach action:followup value:off` — Disable morning follow-ups\n`/fc-coach action:followup value:status` — Check current status\n\nYou can also toggle this in your [Dashboard](https://findtorontoevents.ca/fc/#/accountability).");
        return;
    }

    $conn = get_db_connection();
    if (!$conn) {
        send_response("Database error. Please try via the dashboard.");
        return;
    }

    // Ensure table
    $conn->query("CREATE TABLE IF NOT EXISTS accountability_followup_optouts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        discord_user_id VARCHAR(32) DEFAULT NULL,
        app_user_id INT DEFAULT NULL,
        opted_out_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY unique_discord (discord_user_id),
        INDEX idx_app_user (app_user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

    $esc_id = $conn->real_escape_string($discord_id);

    if ($value === 'status') {
        $check = $conn->query("SELECT id FROM accountability_followup_optouts WHERE discord_user_id = '" . $esc_id . "' LIMIT 1");
        $isOff = ($check && $check->num_rows > 0);
        $conn->close();
        if ($isOff) {
            send_response("🔕 Morning follow-ups are currently **OFF**.\n\nUse `/fc-coach action:followup value:on` to re-enable them.");
        } else {
            send_response("🔔 Morning follow-ups are currently **ON**.\n\nYou receive a DM at 9 AM EST each day with your goal summary.\nUse `/fc-coach action:followup value:off` to stop them.");
        }
        return;
    }

    if ($value === 'off') {
        $conn->query("INSERT IGNORE INTO accountability_followup_optouts (discord_user_id) VALUES ('" . $esc_id . "')");
        $conn->close();
        send_response("🔕 **Morning follow-ups stopped.**\n\nYou will no longer receive daily 9 AM goal follow-ups.\nUse `/fc-coach action:followup value:on` to re-enable them anytime.");
        return;
    }

    // value === 'on'
    $conn->query("DELETE FROM accountability_followup_optouts WHERE discord_user_id = '" . $esc_id . "'");
    $conn->close();
    send_response("🔔 **Morning follow-ups enabled!**\n\nYou will receive a DM at 9 AM EST each day with your active goals summary and streaks.\nUse `/fc-coach action:followup value:off` to stop them.");
}

/**
 * Handle the "Stop Follow-ups" button click from a morning goal follow-up DM.
 * Inserts an opt-out record so the user won't receive further morning DMs.
 */
function _handle_followup_optout_button($discord_id) {
    if (!$discord_id) {
        send_response("Could not identify your account. Please opt out via the dashboard:\nhttps://findtorontoevents.ca/fc/#/accountability");
        return;
    }

    $conn = get_db_connection();
    if (!$conn) {
        send_response("Database error. Please try opting out via the dashboard:\nhttps://findtorontoevents.ca/fc/#/accountability");
        return;
    }

    // Ensure table exists
    $conn->query("CREATE TABLE IF NOT EXISTS accountability_followup_optouts (
        id INT AUTO_INCREMENT PRIMARY KEY,
        discord_user_id VARCHAR(32) DEFAULT NULL,
        app_user_id INT DEFAULT NULL,
        opted_out_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY unique_discord (discord_user_id),
        INDEX idx_app_user (app_user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4");

    $esc_id = $conn->real_escape_string($discord_id);
    $conn->query("INSERT IGNORE INTO accountability_followup_optouts (discord_user_id) VALUES ('" . $esc_id . "')");
    $conn->close();

    // Respond with a confirmation (update the original message)
    send_response_with_components(
        "🔕 **Morning follow-ups stopped.**\n\nYou will no longer receive daily 9 AM goal follow-ups.\n\nYou can re-enable them anytime from your [Accountability Dashboard](https://findtorontoevents.ca/fc/#/accountability) or use `/fc-coach followup on`.",
        array(),
        true,
        true
    );
}

/**
 * Verify a creator's live status using TLC.php
 * Returns true if actually live, false otherwise
 */
function verify_live_status($platform, $username) {
    if (empty($platform) || empty($username)) {
        return false;
    }
    
    // Build TLC URL - use relative URL since we're on the same server
    $tlc_url = 'https://findtorontoevents.ca/fc/TLC.php?user=' . urlencode($username) . '&platform=' . urlencode(strtolower($platform));
    
    // Make quick HTTP request with short timeout (2 seconds per check)
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $tlc_url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 3);
    curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 2);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'FavCreators-Discord-Bot/1.0');
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($response === false || $http_code !== 200) {
        // On error, trust the cached value (don't mark as offline on network error)
        return null;
    }
    
    $data = json_decode($response, true);
    if (!$data) {
        return null;
    }
    
    return isset($data['live']) && $data['live'] === true;
}

/**
 * Extract username from account URL for TLC.php
 */
function extract_username_from_url($url, $platform) {
    if (empty($url)) {
        return null;
    }
    
    $platform = strtolower($platform);
    
    switch ($platform) {
        case 'tiktok':
            // https://www.tiktok.com/@username or tiktok.com/@username
            if (preg_match('/tiktok\.com\/@([a-zA-Z0-9_.]+)/', $url, $match)) {
                return $match[1];
            }
            break;
        case 'twitch':
            // https://www.twitch.tv/username
            if (preg_match('/twitch\.tv\/([a-zA-Z0-9_]+)/', $url, $match)) {
                return $match[1];
            }
            break;
        case 'kick':
            // https://kick.com/username
            if (preg_match('/kick\.com\/([a-zA-Z0-9_]+)/', $url, $match)) {
                return $match[1];
            }
            break;
        case 'youtube':
            // https://www.youtube.com/@username or /c/username or /channel/ID
            if (preg_match('/youtube\.com\/(@[a-zA-Z0-9_-]+|c\/[a-zA-Z0-9_-]+|channel\/[a-zA-Z0-9_-]+)/', $url, $match)) {
                return $match[1];
            }
            break;
        case 'instagram':
            if (preg_match('/instagram\.com\/([a-zA-Z0-9_.]+)/', $url, $match)) {
                return $match[1];
            }
            break;
        case 'facebook':
            if (preg_match('/facebook\.com\/([a-zA-Z0-9.]+)/', $url, $match)) {
                return $match[1];
            }
            break;
    }
    
    return null;
}

function handle_live_command($discord_id) {
    $conn = get_db_connection();
    
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("Your Discord is not linked to FavCreators yet!\n\nLink your account at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    
    // Get creators marked as potentially live (from cache)
    $sql = "SELECT sls.creator_id, sls.creator_name, sls.platform, sls.account_url
            FROM notification_preferences np
            JOIN streamer_last_seen sls ON np.creator_id COLLATE utf8mb4_unicode_ci = sls.creator_id
            WHERE np.user_id = $user_id 
            AND np.discord_notify = 1
            AND sls.is_live = 1
            ORDER BY sls.creator_name";
    
    $result = $conn->query($sql);
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        $timestamp = gmdate('M j, g:i A') . ' UTC';
        send_response("None of your tracked creators are live right now.\n\n_Last checked: $timestamp_\n\nManage notifications at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    // Collect creators to verify
    $creators_to_check = array();
    while ($row = $result->fetch_assoc()) {
        $creators_to_check[] = $row;
    }
    
    // Verify each creator's live status in real-time
    $verified_live = array();
    $verified_offline = array();
    $check_time = time();
    
    foreach ($creators_to_check as $creator) {
        $platform = isset($creator['platform']) ? $creator['platform'] : '';
        $url = isset($creator['account_url']) ? $creator['account_url'] : '';
        $name = isset($creator['creator_name']) ? $creator['creator_name'] : '';
        $creator_id = isset($creator['creator_id']) ? $creator['creator_id'] : '';
        
        // Extract username from URL
        $username = extract_username_from_url($url, $platform);
        
        // If we can't extract username, fall back to creator name
        if (!$username) {
            $username = $name;
        }
        
        // Verify live status via TLC.php
        $is_actually_live = verify_live_status($platform, $username);
        
        if ($is_actually_live === true) {
            // Confirmed live
            $verified_live[] = array(
                'name' => $name,
                'platform' => ucfirst($platform),
                'url' => $url
            );
        } else if ($is_actually_live === false) {
            // Confirmed offline - update database to correct the cache
            $verified_offline[] = $creator_id;
        }
        // If null (network error), don't include and don't update database
    }
    
    // Update database for creators that are no longer live
    if (!empty($verified_offline)) {
        foreach ($verified_offline as $offline_creator_id) {
            $offline_creator_id_esc = $conn->real_escape_string($offline_creator_id);
            $conn->query("UPDATE streamer_last_seen SET is_live = 0, last_checked = NOW() WHERE creator_id = '$offline_creator_id_esc'");
        }
    }
    
    $conn->close();
    
    // Format timestamp
    $timestamp = gmdate('M j, g:i A') . ' UTC';
    
    if (empty($verified_live)) {
        $content = "None of your tracked creators are live right now.\n\n";
        $content .= "_Last verified: $timestamp_\n\n";
        $content .= "🔔 **Missing a creator?** Make sure you have the bell icon enabled on our app!\n";
        $content .= "https://findtorontoevents.ca/fc/";
        send_response($content);
        return;
    }
    
    // Build response with verified live creators
    $live_list = array();
    foreach ($verified_live as $creator) {
        $line = "LIVE: " . $creator['name'] . " (" . $creator['platform'] . ")";
        if (!empty($creator['url'])) {
            $line .= " - " . $creator['url'];
        }
        $live_list[] = $line;
    }
    
    $count = count($verified_live);
    $content = "$count creator(s) live now:\n\n" . implode("\n", $live_list);
    $content .= "\n\n_Last verified: $timestamp_\n\n";
    $content .= "🔔 **Missing a creator?** Make sure you have the bell icon enabled on our app!\n";
    $content .= "https://findtorontoevents.ca/fc/";
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
        $conn->close();
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
        $conn->close();
        send_response("You have no notifications enabled.\n\nEnable them at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $creators = array();
    while ($row = $result->fetch_assoc()) {
        $name = $row['creator_name'] ? $row['creator_name'] : $row['creator_id'];
        $platform = $row['platform'] ? ucfirst($row['platform']) : '';
        $status = $row['is_live'] ? '[LIVE] ' : '';
        $creators[] = $status . $name . ($platform ? " ($platform)" : "");
    }
    
    $conn->close();
    $count = count($creators);
    $content = "Your $count tracked creator(s):\n\n" . implode("\n", $creators);
    send_response($content);
}

function handle_link_command($discord_id) {
    $conn = get_db_connection();
    
    if ($conn && $discord_id) {
        $discord_id_esc = $conn->real_escape_string($discord_id);
        $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
        
        if ($result && $result->num_rows > 0) {
            $conn->close();
            send_response("Your Discord is already linked!\n\nManage at: https://findtorontoevents.ca/fc/");
            return;
        }
        $conn->close();
    }
    
    send_response("Link your Discord to FavCreators:\n\n1. Go to https://findtorontoevents.ca/fc/\n2. Log in or create an account\n3. Click 'Link Discord' in Account panel");
}

function handle_help_command() {
    $content = "**FindTorontoEvents Bot — All Commands (31 total)**\n";
    $content .= "💡 *Type `/fc-` to see all commands in autocomplete*\n";
    $content .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n";
    
    $content .= "**🎭 Creators** (4 commands)\n";
    $content .= "`/fc-live` - See which tracked creators are live\n";
    $content .= "`/fc-creators` - List creators with notifications enabled\n";
    $content .= "`/fc-posts <creator> [count]` - See latest posts from a creator (default 5, max 25)\n";
    $content .= "`/fc-feed [count] [platform]` - Combined feed from ALL your creators\n";
    $content .= "`/fc-about <creator>` - Get info about a creator\n\n";
    
    $content .= "**📅 Events** (5 commands)\n";
    $content .= "`/fc-events <search> [when]` - Find Toronto events\n";
    $content .= "`/fc-myevents` - See your saved events\n";
    $content .= "`/fc-subscribe <category> [frequency]` - Auto-notifications\n";
    $content .= "`/fc-unsubscribe <category>` - Stop auto-notifications\n";
    $content .= "`/fc-mysubs` - View your subscriptions\n\n";
    
    $content .= "**🎬 Movies & TV** (3 commands)\n";
    $content .= "`/fc-movies [search] [type]` - Search movies & TV shows\n";
    $content .= "`/fc-newreleases [type] [period]` - New releases this week/month\n";
    $content .= "`/fc-trailers <title>` - Get trailer for a movie or show\n\n";
    
    $content .= "**📈 Stocks** (6 commands)\n";
    $content .= "`/fc-stocks [rating]` - View today's AI stock picks\n";
    $content .= "`/fc-stock <symbol>` - Get details about a stock pick\n";
    $content .= "`/fc-stockperf` - View performance statistics\n";
    $content .= "`/fc-stocksub <symbol>` - Subscribe to stock alerts\n";
    $content .= "`/fc-stockunsub <symbol>` - Unsubscribe from alerts\n";
    $content .= "`/fc-mystocks` - View your stock subscriptions\n\n";
    
    $content .= "**🌤️ Weather** (2 commands)\n";
    $content .= "`/fc-weather <location>` - Weather alerts & RealFeel\n";
    $content .= "`/fc-jacket <location>` - Do I need a jacket? Quick advice\n\n";
    
    $content .= "**💚 Mental Health** (1 command)\n";
    $content .= "`/fc-mentalhealth [topic]` - Crisis lines, breathing, grounding, panic help\n\n";
    
    $content .= "**🏋️ Accountability Coach** (6 commands)\n";
    $content .= "`/fc-status` - **Full status check** — tasks, actions, next reminders\n";
    $content .= "`/fc-score` - **Accountability score** — weekly/monthly/yearly ratings\n";
    $content .= "`/fc-coach <action>` - Main coach (setup, checkin, skip, punishment, etc.)\n";
    $content .= "`/fc-gym <exercise>` - Log gym workout\n";
    $content .= "`/fc-timer <action>` - Start/stop activity timers\n";
    $content .= "`/fc-stats <action>` - Set or view personal stats\n\n";
    
    $content .= "**ℹ️ General** (4 commands)\n";
    $content .= "`/fc-info [feature]` - See all site apps & features\n";
    $content .= "`/fc-link` - Link your Discord account\n";
    $content .= "`/fc-notifymode <mode>` - Choose notification delivery (DM/channel/both)\n";
    $content .= "`/fc-help` - Show this command list\n\n";
    
    $content .= "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n";
    $content .= "🌐 **Website:** https://findtorontoevents.ca/";
    send_response($content);
}

/**
 * /events <search> [when] - Search Toronto events
 */
function handle_events_command($search, $timeframe) {
    if (empty($search)) {
        send_response("Please specify what events to search for.\n\nExamples:\n/fc-events dating today\n/fc-events music this week\n/fc-events free weekend");
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
    
    // Search keywords - expand common searches
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
    
    // Sort by date
    usort($matched, '_sort_events_by_date');
    
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
    $title = ucfirst($search) . " events";
    if ($time_label) $title .= " $time_label";
    $title .= " (" . count($matched) . " found):\n\n";
    
    $lines = array();
    foreach ($matched as $e) {
        $date_str = date('M j', $e['date']);
        $day = date('D', $e['date']);
        $line = "$day $date_str: " . substr($e['title'], 0, 60);
        if (strlen($e['title']) > 60) $line .= '...';
        if ($e['url']) $line .= "\n  " . $e['url'];
        $lines[] = $line;
    }
    
    $content = $title . implode("\n\n", $lines);
    $content .= "\n\nMore: https://findtorontoevents.ca/";
    send_response($content);
}

/**
 * /myevents - Show user's saved events
 */
function handle_myevents_command($discord_id) {
    $conn = get_db_connection();
    
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    // Find user by discord_id
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("Your Discord is not linked to FavCreators yet!\n\nLink your account at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    
    // Get saved events
    $result = $conn->query("SELECT event_id, event_data FROM user_saved_events WHERE user_id = $user_id ORDER BY created_at DESC LIMIT 10");
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
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
    
    $conn->close();
    
    if (count($events) === 0) {
        send_response("You don't have any saved events yet.\n\nBrowse and save events at: https://findtorontoevents.ca/");
        return;
    }
    
    // Format response
    $lines = array();
    foreach ($events as $e) {
        $title = isset($e['title']) ? $e['title'] : 'Untitled';
        $date = isset($e['date']) ? date('M j', strtotime($e['date'])) : '';
        $url = isset($e['url']) ? $e['url'] : '';
        
        $line = ($date ? "$date: " : '') . substr($title, 0, 55);
        if (strlen($title) > 55) $line .= '...';
        if ($url) $line .= "\n  $url";
        $lines[] = $line;
    }
    
    $count = count($events);
    $content = "Your saved events ($count):\n\n" . implode("\n\n", $lines);
    $content .= "\n\nManage at: https://findtorontoevents.ca/";
    send_response($content);
}

/**
 * /subscribe <category> [frequency] - Subscribe to event notifications
 */
function handle_subscribe_command($discord_id, $category, $frequency) {
    if (empty($category)) {
        $category = 'dating';
    }
    if (empty($frequency)) {
        $frequency = 'daily';
    }
    
    // Normalize inputs
    $category = strtolower(trim($category));
    $frequency = strtolower(trim($frequency));
    
    // Currently only support dating
    if ($category !== 'dating') {
        send_response("Currently only 'dating' event notifications are available.\n\nUse: /fc-subscribe dating daily\nor: /fc-subscribe dating weekly");
        return;
    }
    
    // Validate frequency
    if ($frequency !== 'daily' && $frequency !== 'weekly' && $frequency !== 'both') {
        send_response("Invalid frequency. Use 'daily', 'weekly', or 'both'.\n\nExamples:\n/fc-subscribe dating daily - Get dating events every morning\n/fc-subscribe dating weekly - Get weekly roundup on Mondays\n/fc-subscribe dating both - Get both daily and weekly");
        return;
    }
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    // Find user by discord_id
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("Your Discord is not linked yet!\n\nLink your account first at:\nhttps://findtorontoevents.ca/fc/\n\nThen try /fc-subscribe again.");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    $category_esc = $conn->real_escape_string($category);
    
    // Handle 'both' frequency - create two subscriptions
    $frequencies = ($frequency === 'both') ? array('daily', 'weekly') : array($frequency);
    $created = array();
    
    foreach ($frequencies as $freq) {
        $freq_esc = $conn->real_escape_string($freq);
        
        // Check if subscription exists
        $check = $conn->query("SELECT id, enabled FROM event_subscriptions 
                              WHERE user_id = $user_id AND subscription_type = '$category_esc' AND frequency = '$freq_esc' LIMIT 1");
        
        if ($check && $check->num_rows > 0) {
            $existing = $check->fetch_assoc();
            if (intval($existing['enabled']) === 0) {
                // Re-enable existing subscription
                $conn->query("UPDATE event_subscriptions SET enabled = 1 WHERE id = " . intval($existing['id']));
            }
            $created[] = $freq;
        } else {
            // Create new subscription
            $conn->query("INSERT INTO event_subscriptions (user_id, discord_id, subscription_type, frequency, enabled) 
                         VALUES ($user_id, '$discord_id_esc', '$category_esc', '$freq_esc', 1)");
            $created[] = $freq;
        }
    }
    
    $conn->close();
    
    // Build response
    $freq_text = implode(' and ', $created);
    $content = "Subscribed to $category events ($freq_text)!\n\n";
    
    if (in_array('daily', $created)) {
        $content .= "Daily: You'll receive dating events each morning around 8 AM ET\n";
    }
    if (in_array('weekly', $created)) {
        $content .= "Weekly: You'll receive a weekly roundup every Monday morning\n";
    }
    
    $content .= "\nUse /unsubscribe $category to stop notifications.";
    $content .= "\nUse /mysubs to see all your subscriptions.";
    
    send_response($content);
}

/**
 * /unsubscribe <category> - Unsubscribe from event notifications
 */
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
    
    // Find user by discord_id
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("Your Discord is not linked.\n\nLink at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    $category_esc = $conn->real_escape_string($category);
    
    // Disable all subscriptions for this category
    $conn->query("UPDATE event_subscriptions SET enabled = 0 
                  WHERE user_id = $user_id AND subscription_type = '$category_esc'");
    
    $affected = $conn->affected_rows;
    $conn->close();
    
    if ($affected > 0) {
        send_response("Unsubscribed from $category event notifications.\n\nYou can re-subscribe anytime with /fc-subscribe $category");
    } else {
        send_response("You weren't subscribed to $category events.\n\nUse /fc-subscribe $category to start receiving notifications.");
    }
}

/**
 * /mysubs - Show user's current subscriptions
 */
function handle_mysubs_command($discord_id) {
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    // Find user by discord_id
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("Your Discord is not linked.\n\nLink at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    
    // Get all subscriptions
    $subs = $conn->query("SELECT subscription_type, frequency, enabled, last_daily_sent, last_weekly_sent 
                          FROM event_subscriptions 
                          WHERE user_id = $user_id 
                          ORDER BY subscription_type, frequency");
    
    $conn->close();
    
    if (!$subs || $subs->num_rows === 0) {
        send_response("You have no event subscriptions.\n\nStart receiving dating event notifications:\n/fc-subscribe dating daily - Every morning\n/fc-subscribe dating weekly - Weekly roundup\n/fc-subscribe dating both - Get both!");
        return;
    }
    
    $content = "Your Event Subscriptions:\n\n";
    while ($row = $subs->fetch_assoc()) {
        $status = intval($row['enabled']) ? 'Active' : 'Paused';
        $type = ucfirst($row['subscription_type']);
        $freq = ucfirst($row['frequency']);
        $content .= "$type ($freq): $status\n";
    }
    
    $content .= "\nManage:\n/fc-subscribe <category> <frequency> - Add subscription\n/fc-unsubscribe <category> - Remove subscription";
    
    send_response($content);
}

/**
 * Sort helper for events by date (PHP 5.2 compatible)
 */
function _sort_events_by_date($a, $b) {
    return $a['date'] - $b['date'];
}

/**
 * Get option value from Discord command options
 */
function get_option_value($options, $name) {
    foreach ($options as $opt) {
        if (isset($opt['name']) && $opt['name'] === $name) {
            return isset($opt['value']) ? $opt['value'] : '';
        }
    }
    return '';
}

/**
 * /posts <creator> [count] - Show latest posts from a creator
 * Searches both creator_status_updates and creator_mentions tables
 */
function handle_posts_command($creator_name, $count = 5) {
    if (empty($creator_name)) {
        send_response("Please specify a creator name.\n\nUsage: /fc-posts <creator_name> [count]");
        return;
    }
    
    // Clamp count to 1-25
    $count = max(1, min(25, intval($count)));
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $search = '%' . $conn->real_escape_string($creator_name) . '%';
    // Fetch more than requested to account for placeholder filtering
    $fetch_limit = $count * 3;
    
    $posts = array();
    $seen_urls = array();
    $found_creator = '';
    
    // PART 1: Search creator_status_updates (direct posts from creator platforms)
    $sql = "SELECT creator_name, platform, username, content_title, content_preview, content_url, content_published_at
            FROM creator_status_updates 
            WHERE creator_name LIKE '$search' OR username LIKE '$search'
            ORDER BY content_published_at DESC
            LIMIT $fetch_limit";
    
    $result = $conn->query($sql);
    
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            if (!$found_creator) $found_creator = $row['creator_name'];
            
            $title = $row['content_title'] ? $row['content_title'] : '';
            $preview = $row['content_preview'] ? $row['content_preview'] : '';
            
            // Skip placeholder content
            if (stripos($title, 'Download TikTok') !== false || stripos($title, 'Make Your Day') !== false) {
                continue;
            }
            
            $url = $row['content_url'] ? $row['content_url'] : '';
            if ($url && isset($seen_urls[$url])) continue;
            if ($url) $seen_urls[$url] = true;
            
            $platform = ucfirst($row['platform']);
            $text = $title ? $title : substr($preview, 0, 100);
            if (strlen($preview) > 100 && !$title) $text .= '...';
            
            $date = $row['content_published_at'] ? date('M j', strtotime($row['content_published_at'])) : '';
            $ts = $row['content_published_at'] ? strtotime($row['content_published_at']) : 0;
            
            $line = "[$platform]";
            if ($date) $line .= " $date:";
            $line .= " $text";
            if ($url) $line .= "\n  $url";
            
            $posts[] = array('line' => $line, 'ts' => $ts);
        }
    }
    
    // PART 2: Search creator_mentions (indexed content like YouTube, news, etc.)
    $mentions_sql = "SELECT cm.platform, cm.title, cm.description, cm.content_url, cm.posted_at, cm.author,
                            c.name as creator_name
                     FROM creator_mentions cm
                     LEFT JOIN creators c ON cm.creator_id = c.id
                     WHERE (c.name LIKE '$search' OR cm.author LIKE '$search')
                     ORDER BY cm.posted_at DESC
                     LIMIT $fetch_limit";
    
    $mentions_result = $conn->query($mentions_sql);
    
    if ($mentions_result) {
        while ($row = $mentions_result->fetch_assoc()) {
            if (!$found_creator && $row['creator_name']) $found_creator = $row['creator_name'];
            
            $title = $row['title'] ? $row['title'] : '';
            $description = $row['description'] ? $row['description'] : '';
            
            // Skip placeholder content
            if (stripos($title, 'Download TikTok') !== false || stripos($title, 'Make Your Day') !== false) {
                continue;
            }
            
            $url = $row['content_url'] ? $row['content_url'] : '';
            if ($url && isset($seen_urls[$url])) continue;
            if ($url) $seen_urls[$url] = true;
            
            $platform = ucfirst($row['platform']);
            $text = $title ? $title : substr($description, 0, 100);
            if (strlen($description) > 100 && !$title) $text .= '...';
            
            $ts = intval($row['posted_at']);
            $date = $ts > 0 ? date('M j', $ts) : '';
            
            $line = "[$platform]";
            if ($date) $line .= " $date:";
            $line .= " $text";
            if ($url) $line .= "\n  $url";
            
            $posts[] = array('line' => $line, 'ts' => $ts);
        }
    }
    
    $conn->close();
    
    if (count($posts) === 0) {
        send_response("No posts found for '$creator_name'.\n\nTry a different search term or check https://findtorontoevents.ca/fc/creator_updates/");
        return;
    }
    
    // Sort by timestamp descending (newest first)
    usort($posts, '_cmp_ts_desc');
    
    // Trim to requested count
    $posts = array_slice($posts, 0, $count);
    
    $lines = array();
    foreach ($posts as $p) {
        $lines[] = $p['line'];
    }
    
    $label = $count > 5 ? "Latest $count posts" : "Latest posts";
    $content = "$label from $found_creator:\n\n" . implode("\n\n", $lines);
    send_response($content);
}

/**
 * /fc-feed [count] [platform] - Combined updates feed from all followed creators
 * Mirrors the web page at /fc/#/updates
 */
function handle_feed_command($discord_id, $count = 10, $platform_filter = null) {
    // Clamp count
    $count = max(1, min(25, intval($count)));
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    // Resolve discord_id -> user_id
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("Your Discord is not linked to FavCreators yet!\n\nLink your account at: https://findtorontoevents.ca/fc/\nThen use `/fc-feed` to see updates from all your creators.");
        return;
    }
    
    $user = $result->fetch_assoc();
    $user_id = intval($user['id']);
    
    // Get user's creator list from user_lists (JSON)
    $ul_result = $conn->query("SELECT creators FROM user_lists WHERE user_id = $user_id");
    if (!$ul_result || $ul_result->num_rows === 0) {
        $conn->close();
        send_response("You don't have any creators in your list yet.\n\nAdd creators at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $ul_row = $ul_result->fetch_assoc();
    $creators_data = json_decode($ul_row['creators'], true);
    
    if (!$creators_data || count($creators_data) === 0) {
        $conn->close();
        send_response("Your creator list is empty.\n\nAdd creators at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    // Build lookup maps (same as creator_news_api.php)
    $creator_ids = array();
    $creator_map = array();
    $account_keys = array();
    
    foreach ($creators_data as $creator) {
        $cid = isset($creator['id']) ? $creator['id'] : '';
        if ($cid !== '') {
            $creator_ids[] = $conn->real_escape_string($cid);
            $creator_map[$cid] = $creator;
        }
        if (isset($creator['accounts']) && is_array($creator['accounts'])) {
            foreach ($creator['accounts'] as $account) {
                $p = isset($account['platform']) ? strtolower($account['platform']) : '';
                $u = isset($account['username']) ? $account['username'] : '';
                if ($p !== '' && $u !== '' && $p !== 'other') {
                    $account_keys[] = array(
                        'creator_id' => $cid,
                        'creator_name' => isset($creator['name']) ? $creator['name'] : '',
                        'platform' => $p,
                        'username' => $u
                    );
                }
            }
        }
    }
    
    if (count($creator_ids) === 0) {
        $conn->close();
        send_response("No valid creators found in your list.\n\nManage at: https://findtorontoevents.ca/fc/");
        return;
    }
    
    $fetch_limit = $count * 3; // Over-fetch to account for filtering
    $posts = array();
    $seen_urls = array();
    
    // Placeholder patterns to skip
    $skip_patterns = array('download tiktok', 'make your day', 'could not be extracted', 'profile not found', 'error fetching', 'no recent content');
    
    // PART 1: creator_status_updates (direct posts)
    if (!empty($account_keys)) {
        $conditions = array();
        foreach ($account_keys as $ak) {
            $esc_p = $conn->real_escape_string($ak['platform']);
            $esc_u = $conn->real_escape_string($ak['username']);
            $conditions[] = "(platform = '$esc_p' AND username = '$esc_u')";
        }
        $where = implode(' OR ', $conditions);
        
        $platform_where = '';
        if ($platform_filter) {
            $pf_safe = $conn->real_escape_string($platform_filter);
            $platform_where = " AND platform = '$pf_safe'";
        }
        
        $sql = "SELECT creator_name, platform, username, content_title, content_preview, content_url, content_published_at, is_live, viewer_count
                FROM creator_status_updates
                WHERE ($where)$platform_where
                ORDER BY content_published_at DESC
                LIMIT $fetch_limit";
        
        $result = $conn->query($sql);
        if ($result) {
            while ($row = $result->fetch_assoc()) {
                $title = $row['content_title'] ? $row['content_title'] : '';
                $preview = $row['content_preview'] ? $row['content_preview'] : '';
                $check_text = strtolower($title . ' ' . $preview);
                
                // Skip placeholders
                $skip = false;
                foreach ($skip_patterns as $pat) {
                    if (strpos($check_text, $pat) !== false) { $skip = true; break; }
                }
                if ($skip) continue;
                
                $url = $row['content_url'] ? $row['content_url'] : '';
                if ($url && isset($seen_urls[$url])) continue;
                if ($url) $seen_urls[$url] = true;
                
                // Find creator name from our map
                $cname = $row['creator_name'];
                foreach ($account_keys as $ak) {
                    if (strtolower($ak['platform']) === $row['platform'] && strtolower($ak['username']) === strtolower($row['username'])) {
                        $cname = $ak['creator_name'] ? $ak['creator_name'] : $cname;
                        break;
                    }
                }
                
                $platform = ucfirst($row['platform']);
                $text = $title ? $title : substr($preview, 0, 100);
                if (strlen($preview) > 100 && !$title) $text .= '...';
                
                $date = $row['content_published_at'] ? date('M j', strtotime($row['content_published_at'])) : '';
                $ts = $row['content_published_at'] ? strtotime($row['content_published_at']) : 0;
                $is_live = $row['is_live'] == 1;
                
                $line = '';
                if ($is_live) $line .= '🔴 ';
                $line .= "**$cname** [$platform]";
                if ($date) $line .= " $date";
                $line .= "\n$text";
                if ($url) $line .= "\n$url";
                
                $posts[] = array('line' => $line, 'ts' => $ts, 'is_live' => $is_live);
            }
        }
    }
    
    // PART 2: creator_mentions (indexed content)
    $ids_in = "'" . implode("','", $creator_ids) . "'";
    $mentions_platform = '';
    if ($platform_filter) {
        $pf_safe = $conn->real_escape_string($platform_filter);
        $mentions_platform = " AND cm.platform = '$pf_safe'";
    }
    
    $mentions_sql = "SELECT cm.platform, cm.title, cm.description, cm.content_url, cm.posted_at, cm.author, cm.creator_id
                     FROM creator_mentions cm
                     WHERE cm.creator_id IN ($ids_in)$mentions_platform
                     ORDER BY cm.posted_at DESC
                     LIMIT $fetch_limit";
    
    $mentions_result = $conn->query($mentions_sql);
    if ($mentions_result) {
        while ($row = $mentions_result->fetch_assoc()) {
            $title = $row['title'] ? $row['title'] : '';
            $description = $row['description'] ? $row['description'] : '';
            $check_text = strtolower($title . ' ' . $description);
            
            $skip = false;
            foreach ($skip_patterns as $pat) {
                if (strpos($check_text, $pat) !== false) { $skip = true; break; }
            }
            if ($skip) continue;
            
            $url = $row['content_url'] ? $row['content_url'] : '';
            if ($url && isset($seen_urls[$url])) continue;
            if ($url) $seen_urls[$url] = true;
            
            $cid = $row['creator_id'];
            $cname = isset($creator_map[$cid]) && isset($creator_map[$cid]['name']) ? $creator_map[$cid]['name'] : ($row['author'] ? $row['author'] : 'Unknown');
            
            $platform = ucfirst($row['platform']);
            $text = $title ? $title : substr($description, 0, 100);
            if (strlen($description) > 100 && !$title) $text .= '...';
            
            $ts = intval($row['posted_at']);
            $date = $ts > 0 ? date('M j', $ts) : '';
            
            $line = "**$cname** [$platform]";
            if ($date) $line .= " $date";
            $line .= "\n$text";
            if ($url) $line .= "\n$url";
            
            $posts[] = array('line' => $line, 'ts' => $ts, 'is_live' => false);
        }
    }
    
    $conn->close();
    
    if (count($posts) === 0) {
        $filter_note = $platform_filter ? " on " . ucfirst($platform_filter) : "";
        send_response("No recent updates found from your creators$filter_note.\n\nView full feed: https://findtorontoevents.ca/fc/#/updates");
        return;
    }
    
    // Sort: live first, then by timestamp desc
    usort($posts, '_cmp_live_then_ts');
    
    // Trim to count
    $posts = array_slice($posts, 0, $count);
    
    $lines = array();
    foreach ($posts as $p) {
        $lines[] = $p['line'];
    }
    
    $filter_label = $platform_filter ? " (" . ucfirst($platform_filter) . ")" : "";
    $total_creators = count($creators_data);
    $header = "📰 Updates from your $total_creators creators$filter_label:\n\n";
    $footer = "\n\n_Full feed: https://findtorontoevents.ca/fc/#/updates_";
    $content = $header . implode("\n\n", $lines) . $footer;
    
    // Discord limit is 2000 chars; truncate if needed
    if (strlen($content) > 1950) {
        $content = substr($content, 0, 1900) . "\n\n... _See full feed: https://findtorontoevents.ca/fc/#/updates_";
    }
    
    send_response($content);
}

/**
 * /about <creator> - Show info about a creator
 */
function handle_about_command($creator_name) {
    if (empty($creator_name)) {
        send_response("Please specify a creator name.\n\nUsage: /about <creator_name>");
        return;
    }
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    $search = '%' . $conn->real_escape_string($creator_name) . '%';
    
    // Search in streamer_last_seen for creator info
    $sql = "SELECT creator_id, creator_name, platform, username, account_url, is_live, stream_title, viewer_count
            FROM streamer_last_seen 
            WHERE creator_name LIKE '$search' OR username LIKE '$search'
            ORDER BY is_live DESC, creator_name
            LIMIT 10";
    
    $result = $conn->query($sql);
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
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
                'stream_title' => '',
                'viewer_count' => 0
            );
        }
        
        $platform = ucfirst($row['platform']);
        $url = $row['account_url'];
        $creators[$name]['platforms'][] = "$platform: $url";
        
        if ($row['is_live']) {
            $creators[$name]['is_live'] = true;
            $creators[$name]['stream_title'] = $row['stream_title'];
            $creators[$name]['viewer_count'] = intval($row['viewer_count']);
        }
    }
    
    $conn->close();
    
    // Format response
    $lines = array();
    foreach ($creators as $c) {
        $status = $c['is_live'] ? "LIVE NOW" : "Offline";
        $line = "**" . $c['name'] . "** - $status\n";
        
        if ($c['is_live'] && $c['stream_title']) {
            $line .= "Streaming: " . $c['stream_title'] . "\n";
        }
        if ($c['is_live'] && $c['viewer_count']) {
            $line .= "Viewers: " . number_format($c['viewer_count']) . "\n";
        }
        
        $line .= "Platforms:\n";
        foreach ($c['platforms'] as $p) {
            $line .= "  - $p\n";
        }
        
        $lines[] = $line;
    }
    
    $content = implode("\n", $lines);
    $content .= "\nMore info: https://findtorontoevents.ca/fc/";
    send_response($content);
}

/**
 * /info [feature] - Show all site links or info about a specific feature
 */
function handle_info_command($feature) {
    // Feature details with URLs and descriptions
    $features = array(
        'events' => array(
            'emoji' => '🎉',
            'name' => 'Toronto Events',
            'url' => 'https://findtorontoevents.ca/',
            'short' => 'Daily events in Toronto',
            'long' => "**🎉 Toronto Events**\nhttps://findtorontoevents.ca/\n\nBrowse 1000+ daily events in Toronto:\n• **Filters** — Dating, music, comedy, free, sports & more\n• **Time filters** — Today, tomorrow, weekend, this week\n• **Categories** — Concerts, festivals, workshops, networking\n• **Save events** — Link Discord to save favorites\n\nUse `/fc-events <search> [when]` to search directly from Discord!"
        ),
        'creators' => array(
            'emoji' => '💎',
            'name' => 'Fav Creators',
            'url' => 'https://findtorontoevents.ca/fc/',
            'short' => 'Never miss when your favorites go live',
            'long' => "**💎 Fav Creators**\nhttps://findtorontoevents.ca/fc/\n\nTrack your favorite streamers in one dashboard:\n• **Multi-platform** — TikTok, Twitch, Kick, YouTube\n• **Live alerts** — See who's streaming now\n• **Recent posts** — Latest content in one feed\n• **Discord notifications** — Get DMs when creators go live\n\nUse `/fc-live` to see who's live, `/fc-creators` to list your tracked creators!"
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
        )
    );
    
    // If specific feature requested, show detailed info
    if (!empty($feature) && isset($features[$feature])) {
        send_response($features[$feature]['long']);
        return;
    }
    
    // Show all links overview
    $content = "**🌐 FindTorontoEvents.ca - All Apps & Features**\n\n";
    
    foreach ($features as $key => $f) {
        $content .= $f['emoji'] . " **" . $f['name'] . "**\n";
        $content .= "   " . $f['short'] . "\n";
        $content .= "   " . $f['url'] . "\n\n";
    }
    
    $content .= "─────────────────────\n";
    $content .= "💡 Use `/info <feature>` for detailed info about each app!\n";
    $content .= "Example: `/info trailers` or `/info stocks`";
    
    send_response($content);
}

// ============================================================================
// Movie & TV Show Commands
// ============================================================================

/**
 * /movies [search] [type] - Search movies and TV shows
 */
function handle_movies_command($search, $content_type, $page = 0, $is_update = false) {
    $conn = get_movies_db_connection();
    if (!$conn) {
        send_response('Movie database unavailable. Please try again later.');
        return;
    }
    
    $per_page = 5;
    $offset = $page * $per_page;
    
    // Build WHERE clause
    $where_parts = array();
    $where_parts[] = "t.is_active = 1";
    
    if ($content_type === 'movie') {
        $where_parts[] = "m.type = 'movie'";
    } else if ($content_type === 'tv') {
        $where_parts[] = "m.type = 'tv'";
    }
    
    if (!empty($search)) {
        $search_esc = $conn->real_escape_string($search);
        $where_parts[] = "(m.title LIKE '%$search_esc%' OR m.genre LIKE '%$search_esc%')";
    }
    
    $where_clause = implode(' AND ', $where_parts);
    
    // Count total results
    $count_sql = "SELECT COUNT(DISTINCT m.id) as total FROM movies m 
                  INNER JOIN trailers t ON m.id = t.movie_id 
                  WHERE $where_clause";
    $count_result = $conn->query($count_sql);
    $total_row = $count_result ? $count_result->fetch_assoc() : null;
    $total = $total_row ? intval($total_row['total']) : 0;
    
    if ($total == 0) {
        $conn->close();
        $msg = empty($search) ? "No movies/TV shows found." : "No results found for '$search'.";
        $msg .= "\n\nTry browsing at: https://findtorontoevents.ca/movieshows3/";
        send_response($msg);
        return;
    }
    
    // Fetch results
    $sql = "SELECT m.id, m.title, m.type, m.genre, m.release_year, m.imdb_rating, m.description,
                   t.youtube_id, th.url as thumbnail
            FROM movies m
            INNER JOIN trailers t ON m.id = t.movie_id
            LEFT JOIN thumbnails th ON m.id = th.movie_id AND th.is_primary = 1
            WHERE $where_clause
            GROUP BY m.id
            ORDER BY m.release_year DESC, m.created_at DESC
            LIMIT $per_page OFFSET $offset";
    
    $result = $conn->query($sql);
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("No more results.");
        return;
    }
    
    $movies = array();
    while ($row = $result->fetch_assoc()) {
        $movies[] = $row;
    }
    $conn->close();
    
    // Format response
    $total_pages = ceil($total / $per_page);
    $current_page = $page + 1;
    
    $type_label = $content_type === 'movie' ? 'Movies' : ($content_type === 'tv' ? 'TV Shows' : 'Movies & TV');
    $title = empty($search) ? "Latest $type_label" : "$type_label matching '$search'";
    $content = "**$title** (Page $current_page/$total_pages, $total total)\n\n";
    
    foreach ($movies as $m) {
        $type_icon = $m['type'] === 'tv' ? '📺' : '🎬';
        $rating = $m['imdb_rating'] ? " ⭐ {$m['imdb_rating']}" : '';
        $year = $m['release_year'] ? " ({$m['release_year']})" : '';
        $genre = $m['genre'] ? " • {$m['genre']}" : '';
        
        $content .= "$type_icon **{$m['title']}**$year$rating\n";
        if ($m['genre']) {
            $content .= "   $genre\n";
        }
        if ($m['youtube_id']) {
            $content .= "   🎥 https://youtube.com/watch?v={$m['youtube_id']}\n";
        }
        $content .= "\n";
    }
    
    // Build pagination buttons
    $components = array();
    $buttons = array();
    
    // Encode search for custom_id (max 100 chars in Discord)
    $search_encoded = urlencode(substr($search, 0, 30));
    $type_encoded = $content_type ? $content_type : 'both';
    
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
    
    $content .= "Browse more: https://findtorontoevents.ca/movieshows3/";
    
    if (!empty($components)) {
        send_response_with_components($content, $components, true, $is_update);
    } else {
        send_response($content);
    }
}

/**
 * /newreleases [type] [period] - Show new releases
 */
function handle_newreleases_command($content_type, $period, $page = 0, $is_update = false) {
    $conn = get_movies_db_connection();
    if (!$conn) {
        send_response('Movie database unavailable. Please try again later.');
        return;
    }
    
    $per_page = 5;
    $offset = $page * $per_page;
    
    // Build WHERE clause based on period
    $where_parts = array();
    $where_parts[] = "t.is_active = 1";
    
    if ($content_type === 'movie') {
        $where_parts[] = "m.type = 'movie'";
    } else if ($content_type === 'tv') {
        $where_parts[] = "m.type = 'tv'";
    }
    
    $current_year = intval(date('Y'));
    $period_label = '';
    
    if ($period === 'week') {
        // This week: recent entries in current year
        $where_parts[] = "m.release_year = $current_year";
        $where_parts[] = "m.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)";
        $period_label = 'This Week';
    } else if ($period === 'month') {
        // This month
        $where_parts[] = "m.release_year = $current_year";
        $where_parts[] = "m.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)";
        $period_label = 'This Month';
    } else if ($period === 'upcoming') {
        // Coming soon - 2026 and beyond
        $where_parts[] = "m.release_year >= $current_year";
        $period_label = 'Coming Soon';
    } else {
        // Default: recent additions (last 2 weeks)
        $where_parts[] = "m.created_at >= DATE_SUB(NOW(), INTERVAL 14 DAY)";
        $period_label = 'Recent';
    }
    
    $where_clause = implode(' AND ', $where_parts);
    
    // Count total
    $count_sql = "SELECT COUNT(DISTINCT m.id) as total FROM movies m 
                  INNER JOIN trailers t ON m.id = t.movie_id 
                  WHERE $where_clause";
    $count_result = $conn->query($count_sql);
    $total_row = $count_result ? $count_result->fetch_assoc() : null;
    $total = $total_row ? intval($total_row['total']) : 0;
    
    if ($total == 0) {
        $conn->close();
        $type_label = $content_type === 'movie' ? 'movies' : ($content_type === 'tv' ? 'TV shows' : 'releases');
        send_response("No new $type_label found for $period_label.\n\nBrowse all at: https://findtorontoevents.ca/movieshows3/");
        return;
    }
    
    // Fetch results
    $sql = "SELECT m.id, m.title, m.type, m.genre, m.release_year, m.imdb_rating, m.description,
                   t.youtube_id, th.url as thumbnail
            FROM movies m
            INNER JOIN trailers t ON m.id = t.movie_id
            LEFT JOIN thumbnails th ON m.id = th.movie_id AND th.is_primary = 1
            WHERE $where_clause
            GROUP BY m.id
            ORDER BY m.release_year DESC, m.created_at DESC
            LIMIT $per_page OFFSET $offset";
    
    $result = $conn->query($sql);
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("No more results.");
        return;
    }
    
    $movies = array();
    while ($row = $result->fetch_assoc()) {
        $movies[] = $row;
    }
    $conn->close();
    
    // Format response
    $total_pages = ceil($total / $per_page);
    $current_page = $page + 1;
    
    $type_label = $content_type === 'movie' ? 'Movies' : ($content_type === 'tv' ? 'TV Shows' : 'Releases');
    $content = "**$period_label $type_label** (Page $current_page/$total_pages, $total total)\n\n";
    
    foreach ($movies as $m) {
        $type_icon = $m['type'] === 'tv' ? '📺' : '🎬';
        $rating = $m['imdb_rating'] ? " ⭐ {$m['imdb_rating']}" : '';
        $year = $m['release_year'] ? " ({$m['release_year']})" : '';
        
        $content .= "$type_icon **{$m['title']}**$year$rating\n";
        if ($m['genre']) {
            $content .= "   • {$m['genre']}\n";
        }
        if ($m['youtube_id']) {
            $content .= "   🎥 https://youtube.com/watch?v={$m['youtube_id']}\n";
        }
        $content .= "\n";
    }
    
    // Build pagination buttons
    $components = array();
    $buttons = array();
    
    $type_encoded = $content_type ? $content_type : 'both';
    $period_encoded = $period ? $period : '';
    
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
    
    $content .= "Browse more: https://findtorontoevents.ca/movieshows3/";
    
    if (!empty($components)) {
        send_response_with_components($content, $components, true, $is_update);
    } else {
        send_response($content);
    }
}

/**
 * /trailers <title> - Get trailer for a specific movie/TV show
 */
function handle_trailers_command($title) {
    if (empty($title)) {
        send_response("Please specify a movie or TV show title.\n\nUsage: /trailers <title>");
        return;
    }
    
    $conn = get_movies_db_connection();
    if (!$conn) {
        send_response('Movie database unavailable. Please try again later.');
        return;
    }
    
    $title_esc = $conn->real_escape_string($title);
    
    // Search for matching titles with trailers
    $sql = "SELECT m.id, m.title, m.type, m.genre, m.release_year, m.imdb_rating, m.description,
                   t.youtube_id, t.title as trailer_title
            FROM movies m
            INNER JOIN trailers t ON m.id = t.movie_id
            WHERE t.is_active = 1 
            AND (m.title LIKE '%$title_esc%' OR m.title SOUNDS LIKE '$title_esc')
            ORDER BY 
                CASE WHEN m.title = '$title_esc' THEN 0
                     WHEN m.title LIKE '$title_esc%' THEN 1
                     ELSE 2 END,
                m.release_year DESC, t.priority DESC
            LIMIT 5";
    
    $result = $conn->query($sql);
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("No trailers found for '$title'.\n\nTry a different search or browse at: https://findtorontoevents.ca/movieshows3/");
        return;
    }
    
    $trailers = array();
    $seen_movies = array();
    while ($row = $result->fetch_assoc()) {
        // Only show one trailer per movie
        if (!in_array($row['id'], $seen_movies)) {
            $trailers[] = $row;
            $seen_movies[] = $row['id'];
        }
    }
    $conn->close();
    
    $count = count($trailers);
    
    if ($count === 1) {
        // Single result - show detailed view
        $m = $trailers[0];
        $type_icon = $m['type'] === 'tv' ? '📺' : '🎬';
        $rating = $m['imdb_rating'] ? " ⭐ {$m['imdb_rating']}/10" : '';
        $year = $m['release_year'] ? " ({$m['release_year']})" : '';
        
        $content = "$type_icon **{$m['title']}**$year$rating\n";
        if ($m['genre']) {
            $content .= "Genre: {$m['genre']}\n";
        }
        if ($m['description']) {
            $desc = strlen($m['description']) > 200 ? substr($m['description'], 0, 200) . '...' : $m['description'];
            $content .= "\n$desc\n";
        }
        $content .= "\n🎥 **Watch Trailer:**\nhttps://youtube.com/watch?v={$m['youtube_id']}";
    } else {
        // Multiple results
        $content = "**Trailers for '$title'** ($count found)\n\n";
        
        foreach ($trailers as $m) {
            $type_icon = $m['type'] === 'tv' ? '📺' : '🎬';
            $rating = $m['imdb_rating'] ? " ⭐ {$m['imdb_rating']}" : '';
            $year = $m['release_year'] ? " ({$m['release_year']})" : '';
            
            $content .= "$type_icon **{$m['title']}**$year$rating\n";
            $content .= "   🎥 https://youtube.com/watch?v={$m['youtube_id']}\n\n";
        }
    }
    
    $content .= "\nMore trailers: https://findtorontoevents.ca/movieshows3/";
    send_response($content);
}

// ============================================================================
// Stock Commands
// ============================================================================

/**
 * Fetch stock data from JSON file
 */
function fetch_stock_data($file = 'daily-stocks.json') {
    $url = "https://findtorontoevents.ca/STOCKSUNIFY/data/$file";
    $context = stream_context_create(array(
        'http' => array(
            'timeout' => 10,
            'user_agent' => 'FavCreators-Bot/1.0'
        )
    ));
    
    $json = @file_get_contents($url, false, $context);
    if (!$json) {
        return null;
    }
    
    return json_decode($json, true);
}

/**
 * /stocks [rating] - View today's stock picks
 */
function handle_stocks_command($rating_filter, $page = 0, $is_update = false) {
    $data = fetch_stock_data('daily-stocks.json');
    
    if (!$data || !isset($data['stocks']) || empty($data['stocks'])) {
        send_response("No stock picks available. Check back later or visit https://findtorontoevents.ca/findstocks/");
        return;
    }
    
    $stocks = $data['stocks'];
    $last_updated = isset($data['lastUpdated']) ? $data['lastUpdated'] : '';
    
    // Filter by rating
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
    
    $total = count($stocks);
    if ($total === 0) {
        $msg = "No stocks match that filter.";
        $msg .= "\n\nTry `/fc-stocks all` or visit https://findtorontoevents.ca/findstocks/";
        send_response($msg);
        return;
    }
    
    // Pagination
    $per_page = 5;
    $offset = $page * $per_page;
    $stocks_page = array_slice($stocks, $offset, $per_page);
    $total_pages = ceil($total / $per_page);
    $current_page = $page + 1;
    
    // Format header
    $filter_label = '';
    if ($rating_filter === 'strong_buy') $filter_label = ' (Strong Buy)';
    else if ($rating_filter === 'buy') $filter_label = ' (Buy+)';
    
    $updated = '';
    if ($last_updated) {
        $dt = strtotime($last_updated);
        $updated = date('M j, g:ia', $dt);
    }
    
    $content = "**Today's Stock Picks$filter_label** (Page $current_page/$total_pages)\n";
    $content .= "Updated: $updated\n\n";
    
    // Format stocks
    foreach ($stocks_page as $stock) {
        $symbol = isset($stock['symbol']) ? $stock['symbol'] : '???';
        $name = isset($stock['name']) ? $stock['name'] : '';
        $price = isset($stock['price']) ? '$' . number_format($stock['price'], 2) : '';
        $rating = isset($stock['rating']) ? $stock['rating'] : '';
        $score = isset($stock['score']) ? $stock['score'] : 0;
        $risk = isset($stock['risk']) ? $stock['risk'] : '';
        $timeframe = isset($stock['timeframe']) ? $stock['timeframe'] : '';
        $algorithm = isset($stock['algorithm']) ? $stock['algorithm'] : '';
        
        // Rating emoji
        $rating_icon = '';
        if ($rating === 'STRONG BUY') $rating_icon = '🟢';
        else if ($rating === 'BUY') $rating_icon = '🟡';
        else $rating_icon = '⚪';
        
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

/**
 * /stock <symbol> - Get details about a specific stock pick
 */
function handle_stock_command($symbol) {
    if (empty($symbol)) {
        send_response("Please specify a stock symbol.\n\nUsage: /stock AAPL");
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
        send_response("No picks found for $symbol.\n\nThis stock hasn't been flagged by our algorithms recently.\n\nBrowse all picks: https://findtorontoevents.ca/findstocks/");
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
        
        // Rating emoji
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
        
        // Show indicators if available
        if (isset($found_current['indicators']) && is_array($found_current['indicators'])) {
            $indicators = $found_current['indicators'];
            $content .= "\n**Technical Indicators:**\n";
            if (isset($indicators['rsi'])) $content .= "RSI: " . round($indicators['rsi'], 1) . "\n";
            if (isset($indicators['regime'])) $content .= "Market Regime: " . $indicators['regime'] . "\n";
            if (isset($indicators['martinRatio'])) $content .= "Martin Ratio: " . round($indicators['martinRatio'], 2) . "\n";
            if (isset($indicators['ulcerIndex'])) $content .= "Ulcer Index: " . round($indicators['ulcerIndex'], 2) . "\n";
        }
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

/**
 * /stockperf - View overall performance statistics
 */
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
    $last_verified = isset($data['lastVerified']) ? $data['lastVerified'] : '';
    
    $content = "**📊 Stock Pick Performance**\n\n";
    
    // Overall stats
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
            $algo_losses = isset($stats['losses']) ? $stats['losses'] : 0;
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
    
    if ($last_verified) {
        $dt = strtotime($last_verified);
        $content .= "\nLast verified: " . date('M j, g:ia', $dt) . "\n";
    }
    
    $content .= "\n📈 Detailed analytics: https://findtorontoevents.ca/findstocks/research/\n";
    $content .= "*Not financial advice. Do your own research.*";
    
    send_response($content);
}

/**
 * /stocksub <symbol> - Subscribe to stock alerts
 */
function handle_stocksub_command($discord_id, $symbol) {
    if (empty($symbol)) {
        send_response("Please specify a stock symbol.\n\nUsage: /fc-stocksub AAPL");
        return;
    }
    
    $symbol = strtoupper(trim($symbol));
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    // Ensure table exists
    ensure_stock_subscriptions_table($conn);
    
    // Check if already subscribed
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $symbol_esc = $conn->real_escape_string($symbol);
    
    $result = $conn->query("SELECT id FROM stock_subscriptions WHERE discord_id = '$discord_id_esc' AND symbol = '$symbol_esc' LIMIT 1");
    
    if ($result && $result->num_rows > 0) {
        $conn->close();
        send_response("You're already subscribed to $symbol alerts!\n\nUse `/mystocks` to see your subscriptions.");
        return;
    }
    
    // Check subscription limit (max 20)
    $result = $conn->query("SELECT COUNT(*) as cnt FROM stock_subscriptions WHERE discord_id = '$discord_id_esc'");
    $count_row = $result ? $result->fetch_assoc() : null;
    $count = $count_row ? intval($count_row['cnt']) : 0;
    
    if ($count >= 20) {
        $conn->close();
        send_response("You've reached the maximum of 20 stock subscriptions.\n\nUse `/stockunsub <symbol>` to remove some first.");
        return;
    }
    
    // Add subscription
    $conn->query("INSERT INTO stock_subscriptions (discord_id, symbol, created_at) VALUES ('$discord_id_esc', '$symbol_esc', NOW())");
    
    $conn->close();
    
    $content = "✅ Subscribed to **$symbol** alerts!\n\n";
    $content .= "You'll get a DM when our algorithm picks this stock.\n\n";
    $content .= "Use `/mystocks` to see all subscriptions.\n";
    $content .= "Use `/stockunsub $symbol` to unsubscribe.";
    
    send_response($content);
}

/**
 * /stockunsub <symbol> - Unsubscribe from stock alerts
 */
function handle_stockunsub_command($discord_id, $symbol) {
    if (empty($symbol)) {
        send_response("Please specify a stock symbol.\n\nUsage: /stockunsub AAPL");
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
    
    // Check if subscribed
    $result = $conn->query("SELECT id FROM stock_subscriptions WHERE discord_id = '$discord_id_esc' AND symbol = '$symbol_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("You're not subscribed to $symbol.\n\nUse `/mystocks` to see your subscriptions.");
        return;
    }
    
    // Remove subscription
    $conn->query("DELETE FROM stock_subscriptions WHERE discord_id = '$discord_id_esc' AND symbol = '$symbol_esc'");
    
    $conn->close();
    
    send_response("✅ Unsubscribed from **$symbol** alerts.\n\nUse `/mystocks` to see remaining subscriptions.");
}

/**
 * /mystocks - View stock subscriptions
 */
function handle_mystocks_command($discord_id) {
    $conn = get_db_connection();
    if (!$conn) {
        send_response('Database unavailable. Please try again later.');
        return;
    }
    
    // Ensure table exists
    ensure_stock_subscriptions_table($conn);
    
    $discord_id_esc = $conn->real_escape_string($discord_id);
    
    $result = $conn->query("SELECT symbol, created_at FROM stock_subscriptions WHERE discord_id = '$discord_id_esc' ORDER BY symbol");
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("You have no stock subscriptions.\n\nUse `/fc-stocksub <symbol>` to subscribe to alerts when a stock is picked.\n\nExample: `/fc-stocksub AAPL`");
        return;
    }
    
    $subs = array();
    while ($row = $result->fetch_assoc()) {
        $subs[] = $row;
    }
    $conn->close();
    
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
        
        // Check if currently picked
        $is_active = in_array(strtoupper($sym), $current_symbols);
        $status = $is_active ? '🟢 ACTIVE PICK' : '';
        
        $content .= "• **$sym** — subscribed $date $status\n";
    }
    
    $content .= "\nUse `/stockunsub <symbol>` to unsubscribe.\n";
    $content .= "Use `/stock <symbol>` to see pick details.\n";
    $content .= "\n📈 Browse all picks: https://findtorontoevents.ca/findstocks/";
    
    send_response($content);
}

/**
 * Ensure stock_subscriptions table exists
 */
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
// Weather Command (Primary: Open-Meteo, Fallback: OpenWeatherMap)
// ============================================================================

/**
 * Get OpenWeatherMap API key from .env (used for alerts fallback)
 */
function get_weather_api_key() {
    static $api_key = null;
    if ($api_key !== null) {
        return $api_key;
    }
    
    $env_path = dirname(__FILE__) . '/.env';
    if (file_exists($env_path)) {
        $lines = file($env_path, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
        foreach ($lines as $line) {
            if (strpos($line, '#') === 0) continue;
            if (strpos($line, 'OPENWEATHERMAP_API_KEY=') === 0) {
                $api_key = trim(substr($line, strlen('OPENWEATHERMAP_API_KEY=')));
                $api_key = trim($api_key, '"\'');
                return $api_key;
            }
        }
    }
    return '';
}

/**
 * Geocode a location using Open-Meteo (no API key required)
 * Supports Canadian postal codes and city names
 * Returns array with lat, lon, name, country, admin1 (province/state) or null
 * 
 * OPTIMIZED: 2 second timeout to stay within Discord's 3 second limit
 */
function geocode_location_openmeteo($location) {
    $location = trim($location);
    
    // Check if it looks like a Canadian postal code (letter-number pattern)
    $postal_pattern = '/^[A-Za-z]\d[A-Za-z]\s?\d[A-Za-z]\d$/';
    
    if (preg_match($postal_pattern, $location)) {
        // FIRST: Try local lookup (instant, no API call needed)
        // This covers 150+ GTA postal codes
        $postal_coords = get_postal_code_coords($location);
        if ($postal_coords) {
            return $postal_coords;
        }
        
        // FALLBACK: Try OpenWeatherMap API for postal codes not in local cache
        $api_key = get_weather_api_key();
        if ($api_key) {
            $postal = strtoupper(str_replace(' ', '', $location));
            $url = "https://api.openweathermap.org/geo/1.0/zip?zip=" . urlencode($postal) . ",CA&appid=" . urlencode($api_key);
            
            $context = stream_context_create(array(
                'http' => array('timeout' => 2, 'user_agent' => 'FavCreators-Bot/1.0')
            ));
            
            $response = @file_get_contents($url, false, $context);
            if ($response) {
                $data = json_decode($response, true);
                if (isset($data['lat']) && isset($data['lon'])) {
                    return array(
                        'lat' => $data['lat'],
                        'lon' => $data['lon'],
                        'name' => isset($data['name']) ? $data['name'] : $location,
                        'country' => 'Canada',
                        'admin1' => 'Ontario'
                    );
                }
            }
        }
    }
    
    // Use Open-Meteo geocoding for city names
    $search = $location;
    $url = "https://geocoding-api.open-meteo.com/v1/search?name=" . urlencode($search) . "&count=5&language=en&format=json";
    
    $context = stream_context_create(array(
        'http' => array('timeout' => 2, 'user_agent' => 'FavCreators-Bot/1.0')
    ));
    
    $response = @file_get_contents($url, false, $context);
    if (!$response) {
        return null;
    }
    
    $data = json_decode($response, true);
    
    if (!isset($data['results']) || empty($data['results'])) {
        return null;
    }
    
    // Prefer Canadian results if searching without country specification
    $results = $data['results'];
    $best = $results[0];
    
    // If user didn't specify country, prefer Canada
    if (strpos(strtolower($location), 'canada') === false && 
        strpos($location, ',') === false) {
        foreach ($results as $r) {
            if (isset($r['country']) && $r['country'] === 'Canada') {
                $best = $r;
                break;
            }
        }
    }
    
    return array(
        'lat' => $best['latitude'],
        'lon' => $best['longitude'],
        'name' => isset($best['name']) ? $best['name'] : $location,
        'country' => isset($best['country']) ? $best['country'] : '',
        'admin1' => isset($best['admin1']) ? $best['admin1'] : ''
    );
}

/**
 * Get approximate coordinates for Canadian postal codes (FSA - first 3 chars)
 * Fallback when API is slow - covers major Toronto/GTA areas
 */
function get_postal_code_coords($postal) {
    $postal = strtoupper(str_replace(' ', '', $postal));
    $fsa = substr($postal, 0, 3); // Forward Sortation Area (first 3 chars)
    
    // Toronto and GTA postal code prefixes with approximate center coordinates
    $fsa_coords = array(
        // Downtown Toronto
        'M5A' => array(43.6532, -79.3598, 'Downtown Toronto'),
        'M5B' => array(43.6561, -79.3802, 'Downtown Toronto'),
        'M5C' => array(43.6513, -79.3766, 'Downtown Toronto'),
        'M5E' => array(43.6447, -79.3733, 'Downtown Toronto'),
        'M5G' => array(43.6579, -79.3873, 'Downtown Toronto'),
        'M5H' => array(43.6505, -79.3845, 'Financial District'),
        'M5J' => array(43.6425, -79.3871, 'Harbourfront'),
        'M5K' => array(43.6471, -79.3815, 'Financial District'),
        'M5L' => array(43.6481, -79.3798, 'Financial District'),
        'M5M' => array(43.7332, -79.4197, 'Bedford Park'),
        'M5N' => array(43.7116, -79.4169, 'Roselawn'),
        'M5P' => array(43.6969, -79.4113, 'Forest Hill'),
        'M5R' => array(43.6727, -79.4056, 'The Annex'),
        'M5S' => array(43.6627, -79.3957, 'University'),
        'M5T' => array(43.6532, -79.4000, 'Chinatown'),
        'M5V' => array(43.6289, -79.3944, 'CityPlace'),
        'M5W' => array(43.6461, -79.3840, 'Downtown'),
        'M5X' => array(43.6481, -79.3798, 'Downtown'),
        
        // Central Toronto
        'M4A' => array(43.7252, -79.3156, 'Victoria Village'),
        'M4B' => array(43.7063, -79.3094, 'Parkview Hill'),
        'M4C' => array(43.6953, -79.3183, 'Woodbine Heights'),
        'M4E' => array(43.6763, -79.2930, 'The Beaches'),
        'M4G' => array(43.7090, -79.3634, 'Leaside'),
        'M4H' => array(43.7053, -79.3493, 'Thorncliffe Park'),
        'M4J' => array(43.6850, -79.3394, 'East York'),
        'M4K' => array(43.6795, -79.3522, 'Riverdale'),
        'M4L' => array(43.6689, -79.3155, 'East End'),
        'M4M' => array(43.6595, -79.3372, 'Leslieville'),
        'M4N' => array(43.7280, -79.3887, 'Lawrence Park'),
        'M4P' => array(43.7127, -79.3901, 'Davisville Village'),
        'M4R' => array(43.7153, -79.4057, 'North Toronto'),
        'M4S' => array(43.7043, -79.3887, 'Davisville'),
        'M4T' => array(43.6895, -79.3883, 'Summerhill'),
        'M4V' => array(43.6864, -79.3981, 'Deer Park'),
        'M4W' => array(43.6795, -79.3733, 'Rosedale'),
        'M4X' => array(43.6677, -79.3631, 'Cabbagetown'),
        'M4Y' => array(43.6658, -79.3831, 'Church-Yonge Corridor'),
        
        // East Toronto / Scarborough
        'M1B' => array(43.8066, -79.1943, 'Rouge'),
        'M1C' => array(43.7845, -79.1604, 'Highland Creek'),
        'M1E' => array(43.7635, -79.1887, 'West Hill'),
        'M1G' => array(43.7709, -79.2169, 'Woburn'),
        'M1H' => array(43.7709, -79.2394, 'Cedarbrae'),
        'M1J' => array(43.7448, -79.2394, 'Scarborough Village'),
        'M1K' => array(43.7279, -79.2620, 'Kennedy Park'),
        'M1L' => array(43.7111, -79.2846, 'Golden Mile'),
        'M1M' => array(43.7164, -79.2303, 'Cliffside'),
        'M1N' => array(43.6927, -79.2648, 'Birch Cliff'),
        'M1P' => array(43.7574, -79.2733, 'Dorset Park'),
        'M1R' => array(43.7500, -79.3000, 'Wexford'),
        'M1S' => array(43.7942, -79.2620, 'Agincourt'),
        'M1T' => array(43.7816, -79.3044, 'Tam O\'Shanter'),
        'M1V' => array(43.8152, -79.2846, 'Milliken'),
        'M1W' => array(43.7995, -79.3183, 'L\'Amoreaux'),
        'M1X' => array(43.8361, -79.2056, 'Rouge'),
        
        // North York
        'M2H' => array(43.8037, -79.3544, 'Hillcrest Village'),
        'M2J' => array(43.7785, -79.3465, 'Henry Farm'),
        'M2K' => array(43.7869, -79.3856, 'Bayview Village'),
        'M2L' => array(43.7574, -79.3744, 'York Mills'),
        'M2M' => array(43.7869, -79.4169, 'Willowdale'),
        'M2N' => array(43.7695, -79.4056, 'Willowdale'),
        'M2P' => array(43.7527, -79.4000, 'York Mills'),
        'M2R' => array(43.7827, -79.4422, 'Lansing'),
        'M3A' => array(43.7527, -79.3294, 'Don Mills'),
        'M3B' => array(43.7459, -79.3521, 'Don Mills'),
        'M3C' => array(43.7332, -79.3352, 'Don Mills'),
        'M3H' => array(43.7543, -79.4422, 'Downsview'),
        'M3J' => array(43.7669, -79.4872, 'York University'),
        'M3K' => array(43.7374, -79.4647, 'Downsview'),
        'M3L' => array(43.7390, -79.5097, 'Downsview'),
        'M3M' => array(43.7279, -79.4872, 'Downsview'),
        'M3N' => array(43.7616, -79.5210, 'Jane & Finch'),
        
        // Etobicoke
        'M8V' => array(43.6058, -79.5097, 'New Toronto'),
        'M8W' => array(43.6021, -79.5435, 'Long Branch'),
        'M8X' => array(43.6532, -79.5097, 'Kingsway'),
        'M8Y' => array(43.6363, -79.4985, 'Mimico'),
        'M8Z' => array(43.6289, -79.5210, 'New Toronto'),
        'M9A' => array(43.6668, -79.5322, 'Islington'),
        'M9B' => array(43.6506, -79.5547, 'Islington'),
        'M9C' => array(43.6431, -79.5773, 'Markland Wood'),
        'M9L' => array(43.7564, -79.5547, 'Humber Summit'),
        'M9M' => array(43.7248, -79.5435, 'Emery'),
        'M9N' => array(43.7069, -79.5210, 'Weston'),
        'M9P' => array(43.6958, -79.5322, 'Westmount'),
        'M9R' => array(43.6884, -79.5547, 'Richview'),
        'M9V' => array(43.7395, -79.5885, 'Rexdale'),
        'M9W' => array(43.7111, -79.5885, 'Rexdale'),
        
        // Mississauga (L postal codes)
        'L4T' => array(43.6900, -79.6000, 'Malton'),
        'L4V' => array(43.6700, -79.6200, 'Airport'),
        'L4W' => array(43.6400, -79.6100, 'Central Mississauga'),
        'L4X' => array(43.6100, -79.5700, 'Applewood'),
        'L4Y' => array(43.5900, -79.5500, 'Lakeview'),
        'L4Z' => array(43.6200, -79.6300, 'Meadowvale'),
        'L5A' => array(43.6000, -79.5800, 'Cooksville'),
        'L5B' => array(43.5900, -79.6000, 'City Centre'),
        'L5C' => array(43.5700, -79.5600, 'Port Credit'),
        'L5E' => array(43.5600, -79.5800, 'Lakeshore'),
        'L5G' => array(43.5500, -79.5900, 'Lakeshore'),
        'L5H' => array(43.5400, -79.6000, 'Clarkson'),
        'L5J' => array(43.5200, -79.6200, 'Clarkson'),
        'L5K' => array(43.5300, -79.6400, 'Clarkson'),
        'L5L' => array(43.5400, -79.6600, 'Erin Mills'),
        'L5M' => array(43.5500, -79.6800, 'Erin Mills'),
        'L5N' => array(43.5800, -79.7000, 'Erin Mills'),
        'L5R' => array(43.6100, -79.6600, 'Central Mississauga'),
        'L5T' => array(43.6400, -79.6600, 'Malton'),
        'L5V' => array(43.6000, -79.7000, 'Churchill Meadows'),
        'L5W' => array(43.6200, -79.7000, 'Meadowvale'),
        
        // Brampton
        'L6P' => array(43.7400, -79.7600, 'Brampton'),
        'L6R' => array(43.7200, -79.7400, 'Brampton'),
        'L6S' => array(43.7000, -79.7200, 'Brampton'),
        'L6T' => array(43.6900, -79.7000, 'Brampton'),
        'L6V' => array(43.6900, -79.7700, 'Brampton'),
        'L6W' => array(43.6700, -79.7500, 'Brampton'),
        'L6X' => array(43.7100, -79.7200, 'Brampton'),
        'L6Y' => array(43.7200, -79.7600, 'Brampton'),
        'L6Z' => array(43.7400, -79.7200, 'Brampton'),
        
        // Vaughan / Richmond Hill / Markham
        'L4J' => array(43.8500, -79.4300, 'Thornhill'),
        'L4K' => array(43.8200, -79.4700, 'Concord'),
        'L4L' => array(43.7900, -79.5200, 'Woodbridge'),
        'L3R' => array(43.8500, -79.3700, 'Markham'),
        'L3S' => array(43.8700, -79.3500, 'Markham'),
        'L3T' => array(43.8300, -79.4000, 'Thornhill'),
        'L6A' => array(43.8600, -79.4700, 'Maple')
    );
    
    if (isset($fsa_coords[$fsa])) {
        $coords = $fsa_coords[$fsa];
        return array(
            'lat' => $coords[0],
            'lon' => $coords[1],
            'name' => $coords[2],
            'country' => 'Canada',
            'admin1' => 'Ontario'
        );
    }
    
    // Generic fallback for any M (Toronto) or L (GTA) postal code
    if ($fsa[0] === 'M') {
        return array('lat' => 43.6532, 'lon' => -79.3832, 'name' => 'Toronto', 'country' => 'Canada', 'admin1' => 'Ontario');
    }
    if ($fsa[0] === 'L') {
        return array('lat' => 43.6500, 'lon' => -79.6000, 'name' => 'GTA', 'country' => 'Canada', 'admin1' => 'Ontario');
    }
    
    return null;
}

/**
 * /weather <location> - Get weather with RealFeel and alerts
 * Primary: Open-Meteo (free, no key, 10k/day)
 * 
 * OPTIMIZED for Discord's 3-second response limit:
 * - Reduced timeouts to 2 seconds
 * - Local postal code lookup as fallback
 * - Alerts fetched only if time permits
 */
function handle_weather_command($location) {
    $start_time = microtime(true);
    
    if (empty($location)) {
        send_response("Please provide a location.\n\nUsage:\n/weather M5V 3A8 (postal code)\n/weather Toronto (city name)");
        return;
    }
    
    // Geocode the location (with local fallback for postal codes)
    $geo = geocode_location_openmeteo($location);
    if (!$geo) {
        send_response("Could not find location: $location\n\nTry:\n• Canadian postal code (e.g. M5V 3A8)\n• City name (e.g. Toronto)\n• City, Country (e.g. New York, US)");
        return;
    }
    
    $lat = $geo['lat'];
    $lon = $geo['lon'];
    $location_name = $geo['name'];
    $country = $geo['country'];
    $admin1 = isset($geo['admin1']) ? $geo['admin1'] : '';
    
    // Fetch weather from Open-Meteo (fast, no API key needed)
    $weather_url = "https://api.open-meteo.com/v1/forecast?" . http_build_query(array(
        'latitude' => $lat,
        'longitude' => $lon,
        'current' => 'temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,wind_speed_10m,wind_gusts_10m',
        'daily' => 'temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,weather_code,uv_index_max,precipitation_probability_max',
        'timezone' => 'auto',
        'forecast_days' => 3
    ));
    
    $context = stream_context_create(array(
        'http' => array('timeout' => 2, 'user_agent' => 'FavCreators-Bot/1.0')
    ));
    
    $response = @file_get_contents($weather_url, false, $context);
    
    if (!$response) {
        send_response("Could not fetch weather data. Please try again later.");
        return;
    }
    
    $weather = json_decode($response, true);
    if (!$weather || !isset($weather['current'])) {
        send_response("Error parsing weather data. Please try again later.");
        return;
    }
    
    // Check if we have time to fetch alerts (< 1.5 seconds elapsed)
    $elapsed = microtime(true) - $start_time;
    $alerts = array();
    
    if ($elapsed < 1.5) {
        // Try to fetch alerts (with very short timeout)
        $alerts = fetch_weather_alerts_fast($lat, $lon, $country);
    }
    
    // Format the response
    format_weather_response_openmeteo($weather, $location_name, $country, $admin1, $alerts, $lat, $lon);
}

/**
 * Fast alert fetching - only Environment Canada RSS (single call, short timeout)
 */
function fetch_weather_alerts_fast($lat, $lon, $country) {
    // Only try ECCC for Canadian locations
    if ($country !== 'Canada' && $country !== 'CA') {
        return array();
    }
    
    $region_code = get_eccc_region_code($lat, $lon);
    if (!$region_code) {
        return array();
    }
    
    $url = "https://weather.gc.ca/rss/warning/{$region_code}_e.xml";
    
    $context = stream_context_create(array(
        'http' => array('timeout' => 1, 'user_agent' => 'FavCreators-Bot/1.0')
    ));
    
    $response = @file_get_contents($url, false, $context);
    if (!$response) {
        return array();
    }
    
    // Parse RSS quickly
    libxml_use_internal_errors(true);
    $xml = @simplexml_load_string($response);
    if (!$xml) {
        return array();
    }
    
    $alerts = array();
    foreach ($xml->channel->item as $item) {
        $title = (string)$item->title;
        
        // Skip "No watches or warnings" entries
        if (stripos($title, 'No watches or warnings') !== false) {
            continue;
        }
        
        $event = $title;
        if (preg_match('/^(.+?) in effect/i', $title, $matches)) {
            $event = trim($matches[1]);
        }
        
        $alerts[] = array(
            'event' => $event,
            'sender_name' => 'Environment Canada',
            'description' => strip_tags((string)$item->description),
            'start' => strtotime((string)$item->pubDate),
            'end' => null,
            'source' => 'ECCC',
            'link' => (string)$item->link
        );
        
        // Only get first 2 alerts to keep response short
        if (count($alerts) >= 2) break;
    }
    
    return $alerts;
}

/**
 * Format weather response from Open-Meteo API
 */
function format_weather_response_openmeteo($weather, $location_name, $country, $admin1, $alerts, $lat = null, $lon = null) {
    $current = $weather['current'];
    
    $temp = isset($current['temperature_2m']) ? round($current['temperature_2m']) : '?';
    $feels_like = isset($current['apparent_temperature']) ? round($current['apparent_temperature']) : '?';
    $humidity = isset($current['relative_humidity_2m']) ? $current['relative_humidity_2m'] : '?';
    $wind_speed = isset($current['wind_speed_10m']) ? round($current['wind_speed_10m']) : '?';
    $wind_gusts = isset($current['wind_gusts_10m']) ? round($current['wind_gusts_10m']) : null;
    $is_day = isset($current['is_day']) ? $current['is_day'] : 1;
    $weather_code = isset($current['weather_code']) ? $current['weather_code'] : 0;
    
    // Determine RealFeel label based on temperature difference
    $realfeel_label = 'Feels Like';
    if ($temp !== '?' && $feels_like !== '?') {
        $diff = $feels_like - $temp;
        if ($temp > 20 && $diff > 2) {
            $realfeel_label = 'Humidex'; // Summer - humidity makes it feel hotter
        } else if ($temp < 10 && $diff < -2) {
            $realfeel_label = 'Wind Chill'; // Winter - wind makes it feel colder
        }
    }
    
    // Get weather description and emoji from WMO code
    $weather_info = get_wmo_weather_info($weather_code, $is_day);
    $weather_emoji = $weather_info['emoji'];
    $description = $weather_info['description'];
    
    // Build location string
    $loc_str = $location_name;
    if ($admin1 && $admin1 !== $location_name) {
        $loc_str .= ", $admin1";
    }
    if ($country && $country !== $admin1) {
        $loc_str .= ", $country";
    }
    
    $content = "**$weather_emoji Weather for $loc_str**\n\n";
    
    // Current conditions
    $content .= "**Current Conditions:**\n";
    $content .= "🌡️ Temperature: **{$temp}°C**\n";
    $content .= "🤒 $realfeel_label: **{$feels_like}°C**\n";
    $content .= "☁️ $description\n";
    $content .= "💧 Humidity: {$humidity}%\n";
    $content .= "💨 Wind: {$wind_speed} km/h";
    if ($wind_gusts && $wind_gusts > $wind_speed + 10) {
        $content .= " (gusts {$wind_gusts} km/h)";
    }
    $content .= "\n";
    
    // Daily forecast (today, tomorrow, day after)
    if (isset($weather['daily']) && isset($weather['daily']['time'])) {
        $daily = $weather['daily'];
        $days = count($daily['time']);
        
        $content .= "\n**Forecast:**\n";
        
        for ($i = 0; $i < min(3, $days); $i++) {
            $date = strtotime($daily['time'][$i]);
            $day_name = ($i === 0) ? 'Today' : (($i === 1) ? 'Tomorrow' : date('D', $date));
            
            $high = isset($daily['temperature_2m_max'][$i]) ? round($daily['temperature_2m_max'][$i]) : '?';
            $low = isset($daily['temperature_2m_min'][$i]) ? round($daily['temperature_2m_min'][$i]) : '?';
            $feels_max = isset($daily['apparent_temperature_max'][$i]) ? round($daily['apparent_temperature_max'][$i]) : '?';
            $day_code = isset($daily['weather_code'][$i]) ? $daily['weather_code'][$i] : 0;
            $uv = isset($daily['uv_index_max'][$i]) ? round($daily['uv_index_max'][$i], 1) : null;
            $precip = isset($daily['precipitation_probability_max'][$i]) ? $daily['precipitation_probability_max'][$i] : null;
            
            $day_info = get_wmo_weather_info($day_code, 1);
            
            $content .= "📅 **$day_name:** {$high}°/{$low}° (feels {$feels_max}°) — {$day_info['description']}";
            
            // Add precipitation chance if significant
            if ($precip !== null && $precip > 20) {
                $content .= " 🌧️{$precip}%";
            }
            
            // Add UV if high
            if ($uv !== null && $uv >= 6) {
                $uv_level = get_uvi_level($uv);
                $content .= " ☀️UV:{$uv_level}";
            }
            
            $content .= "\n";
        }
    }
    
    // Weather alerts
    $alert_source = '';
    if (!empty($alerts)) {
        $content .= "\n**⚠️ Weather Alerts:**\n";
        $alerts_to_show = array_slice($alerts, 0, 3);
        foreach ($alerts_to_show as $alert) {
            $content .= format_alert($alert);
            if (isset($alert['source']) && $alert['source'] === 'ECCC') {
                $alert_source = 'Environment Canada';
            }
        }
        if (count($alerts) > 3) {
            $content .= "... and " . (count($alerts) - 3) . " more alert(s)\n";
        }
    } else {
        $content .= "\n✅ No active weather alerts for this area.\n";
    }
    
    // Weather links for more details
    if ($lat !== null && $lon !== null) {
        $links = get_weather_links($lat, $lon, $location_name, $country);
        $content .= "\n**More details:** ";
        $link_parts = array();
        $link_parts[] = "[Weather.com]({$links['weather_com']})";
        $link_parts[] = "[Windy]({$links['windy']})";
        if (isset($links['env_canada'])) {
            $link_parts[] = "[Env Canada]({$links['env_canada']})";
        }
        $content .= implode(' • ', $link_parts) . "\n";
        $content .= "💡 Try `/jacket " . $location_name . "` for quick advice!\n";
    }
    
    // Attribution footer
    $sources = array('Open-Meteo');
    if ($alert_source) {
        $sources[] = $alert_source;
    }
    $content .= "\n📍 Data: " . implode(' + ', $sources);
    
    send_response($content);
}

/**
 * Generate links to popular weather sites for a location
 */
function get_weather_links($lat, $lon, $location_name, $country) {
    $links = array();
    
    // Weather.com (The Weather Channel)
    $links['weather_com'] = "https://weather.com/weather/today/l/" . round($lat, 2) . "," . round($lon, 2);
    
    // AccuWeather - search by city name
    $city_encoded = urlencode($location_name);
    $links['accuweather'] = "https://www.accuweather.com/en/search-locations?query=" . $city_encoded;
    
    // Environment Canada (for Canadian locations)
    if ($country === 'Canada' || $country === 'CA') {
        $region_code = get_eccc_region_code($lat, $lon);
        if ($region_code) {
            $links['env_canada'] = "https://weather.gc.ca/city/pages/{$region_code}_metric_e.html";
        }
    }
    
    // Windy.com (great for radar/wind visualization)
    $links['windy'] = "https://www.windy.com/" . round($lat, 2) . "/" . round($lon, 2);
    
    return $links;
}

/**
 * /jacket <location> - Do I need a jacket? Quick weather advice
 */
function handle_jacket_command($location) {
    $start_time = microtime(true);
    
    if (empty($location)) {
        send_response("Please provide a location.\n\nUsage: /jacket M5V 3A8 or /jacket Toronto");
        return;
    }
    
    // Geocode the location
    $geo = geocode_location_openmeteo($location);
    if (!$geo) {
        send_response("Could not find location: $location\n\nTry a postal code (M5V 3A8) or city name (Toronto)");
        return;
    }
    
    $lat = $geo['lat'];
    $lon = $geo['lon'];
    $location_name = $geo['name'];
    $country = $geo['country'];
    
    // Fetch weather from Open-Meteo
    $weather_url = "https://api.open-meteo.com/v1/forecast?" . http_build_query(array(
        'latitude' => $lat,
        'longitude' => $lon,
        'current' => 'temperature_2m,apparent_temperature,weather_code,wind_speed_10m,precipitation',
        'hourly' => 'precipitation_probability,precipitation',
        'daily' => 'temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum',
        'timezone' => 'auto',
        'forecast_days' => 1,
        'forecast_hours' => 12
    ));
    
    $context = stream_context_create(array(
        'http' => array('timeout' => 2, 'user_agent' => 'FavCreators-Bot/1.0')
    ));
    
    $response = @file_get_contents($weather_url, false, $context);
    
    if (!$response) {
        send_response("Could not fetch weather data. Try again later.");
        return;
    }
    
    $weather = json_decode($response, true);
    if (!$weather || !isset($weather['current'])) {
        send_response("Error getting weather data. Try again later.");
        return;
    }
    
    // Extract current conditions
    $temp = isset($weather['current']['temperature_2m']) ? round($weather['current']['temperature_2m']) : null;
    $feels_like = isset($weather['current']['apparent_temperature']) ? round($weather['current']['apparent_temperature']) : null;
    $wind = isset($weather['current']['wind_speed_10m']) ? round($weather['current']['wind_speed_10m']) : 0;
    $weather_code = isset($weather['current']['weather_code']) ? $weather['current']['weather_code'] : 0;
    
    // Get precipitation probability for next 12 hours
    $max_precip_prob = 0;
    $will_rain = false;
    $rain_hours = array();
    
    if (isset($weather['hourly']['precipitation_probability'])) {
        foreach ($weather['hourly']['precipitation_probability'] as $i => $prob) {
            if ($prob > $max_precip_prob) {
                $max_precip_prob = $prob;
            }
            if ($prob >= 50 && $i < 12) {
                $rain_hours[] = $i;
                $will_rain = true;
            }
        }
    }
    
    // Daily precipitation
    $daily_precip_prob = isset($weather['daily']['precipitation_probability_max'][0]) 
        ? $weather['daily']['precipitation_probability_max'][0] : 0;
    $daily_precip_sum = isset($weather['daily']['precipitation_sum'][0])
        ? $weather['daily']['precipitation_sum'][0] : 0;
    
    // Determine recommendations
    $need_jacket = false;
    $need_warm_jacket = false;
    $need_umbrella = false;
    $need_layers = false;
    $need_sunglasses = false;
    $stay_inside = false;
    
    $reasons = array();
    
    // Temperature-based recommendations (using feels_like)
    $effective_temp = ($feels_like !== null) ? $feels_like : $temp;
    
    if ($effective_temp !== null) {
        if ($effective_temp <= -10) {
            $need_warm_jacket = true;
            $need_layers = true;
            $reasons[] = "It's **freezing** ({$feels_like}°C feels like)";
        } else if ($effective_temp <= 5) {
            $need_warm_jacket = true;
            $reasons[] = "It's **cold** ({$feels_like}°C feels like)";
        } else if ($effective_temp <= 15) {
            $need_jacket = true;
            $reasons[] = "It's **cool** ({$feels_like}°C feels like)";
        } else if ($effective_temp <= 20) {
            $need_jacket = true;
            $reasons[] = "It's **mild** - light jacket recommended";
        }
        // 20+ = no jacket needed
    }
    
    // Wind-based
    if ($wind >= 40) {
        $need_jacket = true;
        $reasons[] = "**Strong winds** ({$wind} km/h)";
    } else if ($wind >= 25) {
        if (!$need_jacket && $effective_temp < 22) {
            $need_jacket = true;
        }
        $reasons[] = "Windy ({$wind} km/h)";
    }
    
    // Rain-based
    if ($will_rain || $daily_precip_prob >= 60 || $weather_code >= 51) {
        $need_umbrella = true;
        if ($daily_precip_prob >= 80) {
            $reasons[] = "**Rain likely** ({$daily_precip_prob}% chance)";
        } else if ($daily_precip_prob >= 50) {
            $reasons[] = "Possible rain ({$daily_precip_prob}% chance)";
        }
    }
    
    // Snow
    if ($weather_code >= 71 && $weather_code <= 77) {
        $reasons[] = "**Snow expected** ❄️";
        $need_warm_jacket = true;
    }
    
    // Thunderstorm
    if ($weather_code >= 95) {
        $stay_inside = true;
        $need_umbrella = true;
        $reasons[] = "**Thunderstorm warning** ⛈️";
    }
    
    // Clear/sunny
    if ($weather_code <= 1 && $effective_temp > 20) {
        $need_sunglasses = true;
    }
    
    // Build response
    $weather_info = get_wmo_weather_info($weather_code, 1);
    $emoji = $weather_info['emoji'];
    
    $content = "**$emoji Jacket Check for $location_name**\n\n";
    
    // Main verdict
    if ($stay_inside) {
        $content .= "🏠 **STAY INSIDE IF POSSIBLE**\n";
    } else if ($need_warm_jacket) {
        $content .= "🧥 **YES - Warm winter jacket needed!**\n";
        if ($need_layers) {
            $content .= "🧣 Layer up - hat, gloves, scarf recommended\n";
        }
    } else if ($need_jacket) {
        $content .= "🧥 **YES - Bring a jacket**\n";
    } else {
        $content .= "👕 **NO JACKET NEEDED** - You're good!\n";
    }
    
    if ($need_umbrella) {
        $content .= "☔ **Bring an umbrella**\n";
    }
    
    if ($need_sunglasses && !$need_umbrella) {
        $content .= "😎 Sunglasses recommended\n";
    }
    
    // Show reasons
    if (!empty($reasons)) {
        $content .= "\n**Why:**\n• " . implode("\n• ", $reasons) . "\n";
    }
    
    // Current conditions summary
    $content .= "\n**Right now:** {$temp}°C";
    if ($feels_like !== null && $feels_like != $temp) {
        $content .= " (feels {$feels_like}°C)";
    }
    $content .= " — {$weather_info['description']}\n";
    
    // Rain timing
    if ($will_rain && !empty($rain_hours)) {
        $first_rain = $rain_hours[0];
        if ($first_rain == 0) {
            $content .= "🌧️ Rain expected **now or very soon**\n";
        } else if ($first_rain <= 3) {
            $content .= "🌧️ Rain expected in **~{$first_rain} hours**\n";
        } else {
            $content .= "🌧️ Rain possible later today\n";
        }
    }
    
    // Quick links for more info
    $links = get_weather_links($lat, $lon, $location_name, $country);
    $content .= "\n**More details:**\n";
    $content .= "• [Weather.com]({$links['weather_com']})\n";
    $content .= "• [Windy Radar]({$links['windy']})\n";
    if (isset($links['env_canada'])) {
        $content .= "• [Environment Canada]({$links['env_canada']})\n";
    }
    
    send_response($content);
}

/**
 * Fetch weather alerts with failover chain:
 * 1. Environment Canada (ECCC) - Official Canadian government alerts (best for Toronto)
 * 2. OpenWeatherMap One Call API 3.0 (fallback)
 */
function fetch_weather_alerts_with_failover($lat, $lon, $country) {
    $alerts = array();
    
    // 1. Try Environment Canada first (for Canadian locations)
    if ($country === 'Canada' || $country === 'CA') {
        $alerts = fetch_alerts_environment_canada($lat, $lon);
        if (!empty($alerts)) {
            return $alerts;
        }
    }
    
    // 2. Fallback to OpenWeatherMap
    $api_key = get_weather_api_key();
    if ($api_key) {
        $alerts = fetch_weather_alerts_owm($lat, $lon, $api_key);
    }
    
    return $alerts;
}

/**
 * Fetch alerts from Environment Canada (ECCC) - Official Government of Canada
 * Uses the CAP (Common Alerting Protocol) Atom feeds
 * https://weather.gc.ca/warnings/index_e.html
 */
function fetch_alerts_environment_canada($lat, $lon) {
    // Map coordinates to Environment Canada region codes
    // Toronto area codes: on-143 (City of Toronto), on-116 (York-Durham), etc.
    $region_code = get_eccc_region_code($lat, $lon);
    
    if (!$region_code) {
        return array();
    }
    
    // Fetch the warning RSS feed for this region
    $url = "https://weather.gc.ca/rss/warning/{$region_code}_e.xml";
    
    $context = stream_context_create(array(
        'http' => array(
            'timeout' => 10,
            'user_agent' => 'FavCreators-Bot/1.0',
            'ignore_errors' => true
        )
    ));
    
    $response = @file_get_contents($url, false, $context);
    
    if (!$response) {
        return array();
    }
    
    // Parse the RSS/Atom feed
    $alerts = array();
    
    // Suppress XML errors
    libxml_use_internal_errors(true);
    $xml = @simplexml_load_string($response);
    
    if (!$xml) {
        return array();
    }
    
    // Parse RSS items (alerts)
    foreach ($xml->channel->item as $item) {
        $title = (string)$item->title;
        $description = (string)$item->description;
        $pubDate = (string)$item->pubDate;
        $link = (string)$item->link;
        
        // Skip "No watches or warnings" entries
        if (stripos($title, 'No watches or warnings') !== false) {
            continue;
        }
        
        // Extract alert type from title
        $event = $title;
        if (preg_match('/^(.+?) in effect/i', $title, $matches)) {
            $event = trim($matches[1]);
        }
        
        $alerts[] = array(
            'event' => $event,
            'sender_name' => 'Environment Canada',
            'description' => strip_tags($description),
            'start' => strtotime($pubDate),
            'end' => null,
            'source' => 'ECCC',
            'link' => $link
        );
    }
    
    return $alerts;
}

/**
 * Map lat/lon to Environment Canada region code
 * Focus on GTA (Greater Toronto Area) and major Canadian cities
 */
function get_eccc_region_code($lat, $lon) {
    // Define regions with bounding boxes (approximate)
    $regions = array(
        // Ontario - GTA
        'on-143' => array('name' => 'City of Toronto', 'lat_min' => 43.58, 'lat_max' => 43.86, 'lon_min' => -79.64, 'lon_max' => -79.10),
        'on-116' => array('name' => 'York-Durham', 'lat_min' => 43.80, 'lat_max' => 44.30, 'lon_min' => -79.70, 'lon_max' => -78.80),
        'on-121' => array('name' => 'Halton-Peel', 'lat_min' => 43.40, 'lat_max' => 43.90, 'lon_min' => -80.10, 'lon_max' => -79.50),
        'on-148' => array('name' => 'Hamilton-Niagara', 'lat_min' => 42.90, 'lat_max' => 43.50, 'lon_min' => -80.00, 'lon_max' => -79.00),
        
        // Other major Ontario cities
        'on-118' => array('name' => 'Ottawa', 'lat_min' => 45.20, 'lat_max' => 45.55, 'lon_min' => -76.00, 'lon_max' => -75.40),
        'on-131' => array('name' => 'London-Middlesex', 'lat_min' => 42.80, 'lat_max' => 43.20, 'lon_min' => -81.50, 'lon_max' => -81.00),
        'on-107' => array('name' => 'Windsor-Essex', 'lat_min' => 41.90, 'lat_max' => 42.40, 'lon_min' => -83.20, 'lon_max' => -82.50),
        'on-140' => array('name' => 'Kitchener-Waterloo', 'lat_min' => 43.30, 'lat_max' => 43.60, 'lon_min' => -80.70, 'lon_max' => -80.30),
        
        // Quebec
        'qc-126' => array('name' => 'Montreal', 'lat_min' => 45.40, 'lat_max' => 45.70, 'lon_min' => -73.90, 'lon_max' => -73.40),
        'qc-133' => array('name' => 'Quebec City', 'lat_min' => 46.70, 'lat_max' => 47.00, 'lon_min' => -71.50, 'lon_max' => -71.00),
        
        // British Columbia
        'bc-45' => array('name' => 'Vancouver Metro', 'lat_min' => 49.00, 'lat_max' => 49.40, 'lon_min' => -123.30, 'lon_max' => -122.60),
        'bc-48' => array('name' => 'Victoria', 'lat_min' => 48.30, 'lat_max' => 48.60, 'lon_min' => -123.60, 'lon_max' => -123.20),
        
        // Alberta
        'ab-55' => array('name' => 'Calgary', 'lat_min' => 50.85, 'lat_max' => 51.20, 'lon_min' => -114.30, 'lon_max' => -113.80),
        'ab-71' => array('name' => 'Edmonton', 'lat_min' => 53.40, 'lat_max' => 53.70, 'lon_min' => -113.80, 'lon_max' => -113.20),
        
        // Manitoba
        'mb-36' => array('name' => 'Winnipeg', 'lat_min' => 49.75, 'lat_max' => 50.00, 'lon_min' => -97.30, 'lon_max' => -96.95),
        
        // Saskatchewan
        'sk-61' => array('name' => 'Saskatoon', 'lat_min' => 52.05, 'lat_max' => 52.25, 'lon_min' => -106.80, 'lon_max' => -106.50),
        'sk-68' => array('name' => 'Regina', 'lat_min' => 50.35, 'lat_max' => 50.55, 'lon_min' => -104.70, 'lon_max' => -104.50),
        
        // Nova Scotia
        'ns-36' => array('name' => 'Halifax', 'lat_min' => 44.55, 'lat_max' => 44.75, 'lon_min' => -63.70, 'lon_max' => -63.45),
        
        // New Brunswick
        'nb-34' => array('name' => 'Saint John', 'lat_min' => 45.20, 'lat_max' => 45.35, 'lon_min' => -66.15, 'lon_max' => -65.90)
    );
    
    // Find the closest matching region
    foreach ($regions as $code => $region) {
        if ($lat >= $region['lat_min'] && $lat <= $region['lat_max'] &&
            $lon >= $region['lon_min'] && $lon <= $region['lon_max']) {
            return $code;
        }
    }
    
    // Default to Toronto for nearby Ontario locations
    if ($lat >= 43.0 && $lat <= 45.0 && $lon >= -80.5 && $lon <= -78.5) {
        return 'on-143'; // City of Toronto
    }
    
    return null;
}

/**
 * Fetch weather alerts from OpenWeatherMap (fallback)
 */
function fetch_weather_alerts_owm($lat, $lon, $api_key) {
    // Try One Call API 3.0 for alerts
    $url = "https://api.openweathermap.org/data/3.0/onecall?lat=$lat&lon=$lon&exclude=minutely,hourly,daily,current&appid=" . urlencode($api_key);
    
    $context = stream_context_create(array(
        'http' => array('timeout' => 10, 'user_agent' => 'FavCreators-Bot/1.0')
    ));
    
    $response = @file_get_contents($url, false, $context);
    
    if ($response) {
        $data = json_decode($response, true);
        if (isset($data['alerts']) && !empty($data['alerts'])) {
            return $data['alerts'];
        }
    }
    
    return array();
}

/**
 * Format a single weather alert for display
 */
function format_alert($alert) {
    $event = isset($alert['event']) ? $alert['event'] : 'Weather Alert';
    $sender = isset($alert['sender_name']) ? $alert['sender_name'] : '';
    $description = isset($alert['description']) ? $alert['description'] : '';
    $start = isset($alert['start']) && $alert['start'] ? date('M j, g:ia', $alert['start']) : '';
    $end = isset($alert['end']) && $alert['end'] ? date('M j, g:ia', $alert['end']) : '';
    $link = isset($alert['link']) ? $alert['link'] : '';
    $source = isset($alert['source']) ? $alert['source'] : '';
    
    $content = "🚨 **$event**\n";
    if ($sender) {
        $source_badge = ($source === 'ECCC') ? ' 🇨🇦' : '';
        $content .= "   From: $sender$source_badge\n";
    }
    if ($start) {
        if ($end) {
            $content .= "   Valid: $start - $end\n";
        } else {
            $content .= "   Issued: $start\n";
        }
    }
    if ($description) {
        // Truncate long descriptions
        $desc_short = strlen($description) > 200 ? substr($description, 0, 200) . '...' : $description;
        $content .= "   $desc_short\n";
    }
    if ($link) {
        $content .= "   🔗 $link\n";
    }
    $content .= "\n";
    
    return $content;
}

/**
 * Get weather description and emoji from WMO weather code
 * https://open-meteo.com/en/docs - WMO Weather interpretation codes
 */
function get_wmo_weather_info($code, $is_day = 1) {
    $codes = array(
        0 => array('Clear sky', '☀️', '🌙'),
        1 => array('Mainly clear', '🌤️', '🌙'),
        2 => array('Partly cloudy', '⛅', '☁️'),
        3 => array('Overcast', '☁️', '☁️'),
        45 => array('Fog', '🌫️', '🌫️'),
        48 => array('Depositing rime fog', '🌫️', '🌫️'),
        51 => array('Light drizzle', '🌦️', '🌧️'),
        53 => array('Moderate drizzle', '🌦️', '🌧️'),
        55 => array('Dense drizzle', '🌧️', '🌧️'),
        56 => array('Light freezing drizzle', '🌧️', '🌧️'),
        57 => array('Dense freezing drizzle', '🌧️', '🌧️'),
        61 => array('Slight rain', '🌦️', '🌧️'),
        63 => array('Moderate rain', '🌧️', '🌧️'),
        65 => array('Heavy rain', '🌧️', '🌧️'),
        66 => array('Light freezing rain', '🌧️', '🌧️'),
        67 => array('Heavy freezing rain', '🌧️', '🌧️'),
        71 => array('Slight snow', '🌨️', '🌨️'),
        73 => array('Moderate snow', '🌨️', '🌨️'),
        75 => array('Heavy snow', '❄️', '❄️'),
        77 => array('Snow grains', '🌨️', '🌨️'),
        80 => array('Slight rain showers', '🌦️', '🌧️'),
        81 => array('Moderate rain showers', '🌧️', '🌧️'),
        82 => array('Violent rain showers', '🌧️', '🌧️'),
        85 => array('Slight snow showers', '🌨️', '🌨️'),
        86 => array('Heavy snow showers', '❄️', '❄️'),
        95 => array('Thunderstorm', '⛈️', '⛈️'),
        96 => array('Thunderstorm with slight hail', '⛈️', '⛈️'),
        99 => array('Thunderstorm with heavy hail', '⛈️', '⛈️')
    );
    
    if (isset($codes[$code])) {
        $info = $codes[$code];
        return array(
            'description' => $info[0],
            'emoji' => $is_day ? $info[1] : $info[2]
        );
    }
    
    return array('description' => 'Unknown', 'emoji' => '🌡️');
}

/**
 * Get UV index level description
 */
function get_uvi_level($uvi) {
    if ($uvi < 3) return 'Low';
    if ($uvi < 6) return 'Moderate';
    if ($uvi < 8) return 'High';
    if ($uvi < 11) return 'Very High';
    return 'Extreme';
}

// ============================================================================
// Mental Health Resources Command
// ============================================================================

/**
 * /mentalhealth [topic] - Get mental health resources, crisis lines, and wellness tools
 */
function handle_mentalhealth_command($topic) {
    $base_url = 'https://findtorontoevents.ca/MENTALHEALTHRESOURCES/';
    
    // Topic-specific responses
    if ($topic === 'crisis') {
        $content = "**🆘 Crisis Support Lines**\n\n";
        $content .= "**If you're in immediate danger, call 911**\n\n";
        $content .= "**🇨🇦 Canada:**\n";
        $content .= "☎️ 1-833-456-4566 (24/7 Talk Suicide Canada)\n";
        $content .= "💬 Text HOME to 741741 (Crisis Text Line)\n";
        $content .= "🧒 Kids Help Phone: 1-800-668-6868\n\n";
        $content .= "**🇺🇸 United States:**\n";
        $content .= "☎️ 988 (Suicide & Crisis Lifeline, 24/7)\n";
        $content .= "💬 Text HOME to 741741 (Crisis Text Line)\n";
        $content .= "🏳️‍🌈 Trevor Project: 1-866-488-7386\n\n";
        $content .= "**🇬🇧 United Kingdom:**\n";
        $content .= "☎️ 116 123 (Samaritans, 24/7)\n";
        $content .= "💬 Text SHOUT to 85258\n\n";
        $content .= "**🌍 International:**\n";
        $content .= "Visit: $base_url\n";
        $content .= "(Select your country for local resources)\n\n";
        $content .= "❤️ You are not alone. Help is available.";
        send_response($content);
        return;
    }
    
    if ($topic === 'breathing') {
        $content = "**🫁 4-7-8 Breathing Exercise**\n\n";
        $content .= "A calming technique to reduce anxiety:\n\n";
        $content .= "1️⃣ **Inhale** through your nose for **4 seconds**\n";
        $content .= "2️⃣ **Hold** your breath for **7 seconds**\n";
        $content .= "3️⃣ **Exhale** slowly through your mouth for **8 seconds**\n\n";
        $content .= "🔄 Repeat 4 times\n\n";
        $content .= "**Why it works:** This activates your parasympathetic nervous system, slowing your heart rate and promoting calm.\n\n";
        $content .= "🎮 **Interactive guided version:**\n$base_url#breathing\n\n";
        $content .= "Other breathing tools: `/mentalhealth games`";
        send_response($content);
        return;
    }
    
    if ($topic === 'grounding') {
        $content = "**🌱 5-4-3-2-1 Grounding Technique**\n\n";
        $content .= "For panic attacks and overwhelming anxiety:\n\n";
        $content .= "Name out loud:\n";
        $content .= "👀 **5** things you can **SEE**\n";
        $content .= "✋ **4** things you can **TOUCH**\n";
        $content .= "👂 **3** things you can **HEAR**\n";
        $content .= "👃 **2** things you can **SMELL**\n";
        $content .= "👅 **1** thing you can **TASTE**\n\n";
        $content .= "**Why it works:** Engages all five senses to bring you back to the present moment and break the anxiety spiral.\n\n";
        $content .= "🎮 **Interactive guided version:**\n$base_url#grounding\n\n";
        $content .= "More tools: `/mentalhealth games`";
        send_response($content);
        return;
    }
    
    if ($topic === 'panic') {
        $content = "**🫁 Panic Attack Relief**\n\n";
        $content .= "**You're safe. This will pass.**\n\n";
        $content .= "**Immediate steps:**\n";
        $content .= "1️⃣ **Splash cold water** on your face (activates dive reflex)\n";
        $content .= "2️⃣ **Box breathing:** Inhale 4s → Hold 4s → Exhale 4s → Hold 4s\n";
        $content .= "3️⃣ **Ground yourself:** 5-4-3-2-1 technique (see `/mentalhealth grounding`)\n";
        $content .= "4️⃣ **If hyperventilating:** Breathe into cupped hands\n\n";
        $content .= "**Remember:**\n";
        $content .= "• Panic attacks peak in ~10 minutes\n";
        $content .= "• They cannot hurt you physically\n";
        $content .= "• You have survived every one so far\n\n";
        $content .= "🎮 **Interactive panic relief tools:**\n$base_url#panic\n\n";
        $content .= "❤️ If panic attacks are frequent, please reach out to a mental health professional.";
        send_response($content);
        return;
    }
    
    if ($topic === 'games') {
        $content = "**🎮 Wellness Games & Interactive Tools**\n\n";
        $content .= "Free, science-backed tools at:\n$base_url\n\n";
        $content .= "**🫁 Breathing Exercises:**\n";
        $content .= "• 4-7-8 Breathing — Calm anxiety\n";
        $content .= "• Cyclical Sighing — Rapid stress relief\n";
        $content .= "• Box Breathing — Focus & calm\n\n";
        $content .= "**🧘 Mindfulness:**\n";
        $content .= "• 5-Minute Meditation\n";
        $content .= "• Progressive Muscle Relaxation\n";
        $content .= "• 5-4-3-2-1 Grounding\n\n";
        $content .= "**❤️ Heart & Body:**\n";
        $content .= "• Quick Coherence (HRV improvement)\n";
        $content .= "• Vagus Nerve Reset\n";
        $content .= "• Panic Attack Relief\n\n";
        $content .= "**🧠 Long-term Wellness:**\n";
        $content .= "• Gratitude Journal\n";
        $content .= "• Identity Builder (Atomic Habits)\n";
        $content .= "• 5-3-1 Social Fitness\n";
        $content .= "• Anger Management (CBT/DBT)\n\n";
        $content .= "🎨 All tools are interactive and free!";
        send_response($content);
        return;
    }
    
    if ($topic === 'demographics') {
        $content = "**👥 Resources by Demographics**\n\n";
        $content .= "Specialized mental health support:\n\n";
        $content .= "**🏳️‍🌈 LGBTQ+:**\n";
        $content .= "• Trevor Project: 1-866-488-7386\n";
        $content .= "• Trans Lifeline: 1-877-565-8860\n\n";
        $content .= "**🧒 Youth & Teens:**\n";
        $content .= "• Kids Help Phone (CA): 1-800-668-6868\n";
        $content .= "• Youthline: Text 647-694-4275\n\n";
        $content .= "**🎖️ Veterans:**\n";
        $content .= "• Veterans Affairs (CA): 1-800-268-7708\n";
        $content .= "• Veterans Crisis Line (US): 988, press 1\n\n";
        $content .= "**👴 Seniors:**\n";
        $content .= "• Seniors Safety Line: 1-866-299-1011\n\n";
        $content .= "**🌍 Indigenous Communities:**\n";
        $content .= "• Hope for Wellness: 1-855-242-3310\n\n";
        $content .= "**✊ BIPOC Communities:**\n";
        $content .= "• Black Mental Health Matters\n";
        $content .= "• Therapy for Black Girls\n\n";
        $content .= "More resources: $base_url";
        send_response($content);
        return;
    }
    
    // Default: Show overview
    $content = "**🌟 Mental Health Resources**\n\n";
    $content .= "**🆘 In Crisis? Get Help Now:**\n";
    $content .= "🇨🇦 1-833-456-4566 | 🇺🇸 988 | 💬 Text HOME to 741741\n\n";
    $content .= "**🎮 Wellness Tools Available:**\n";
    $content .= "• Breathing exercises (4-7-8, box breathing)\n";
    $content .= "• Guided meditation & grounding\n";
    $content .= "• Panic attack relief\n";
    $content .= "• Gratitude journal\n";
    $content .= "• And many more...\n\n";
    $content .= "**Quick Commands:**\n";
    $content .= "`/mentalhealth crisis` — Crisis lines by country\n";
    $content .= "`/mentalhealth breathing` — 4-7-8 breathing guide\n";
    $content .= "`/mentalhealth grounding` — 5-4-3-2-1 technique\n";
    $content .= "`/mentalhealth panic` — Panic attack relief\n";
    $content .= "`/mentalhealth games` — All wellness tools\n";
    $content .= "`/mentalhealth demographics` — LGBTQ+, youth, veterans, etc.\n\n";
    $content .= "**🌐 Full Resource Hub:**\n$base_url\n\n";
    $content .= "❤️ You matter. Help is available.";
    
    send_response($content);
}

// ============================================================================
// Notification Delivery Mode Command
// ============================================================================

function handle_notifymode_command($discord_id, $mode) {
    if (empty($discord_id)) {
        send_response("❌ Could not identify your Discord account.");
        return;
    }
    
    // Validate mode
    $valid_modes = array('channel', 'dm', 'both');
    if (!in_array($mode, $valid_modes)) {
        send_response("❌ Invalid mode. Choose: channel, dm, or both");
        return;
    }
    
    $conn = get_db_connection();
    if (!$conn) {
        send_response("❌ Database unavailable. Please try again later.");
        return;
    }
    
    // Find user by discord_id
    $discord_id_esc = $conn->real_escape_string($discord_id);
    $result = $conn->query("SELECT id, delivery_mode FROM users WHERE discord_id = '$discord_id_esc' LIMIT 1");
    
    if (!$result || $result->num_rows === 0) {
        $conn->close();
        send_response("❌ Your Discord is not linked to a FavCreators account.\n\nUse `/link` to get started!");
        return;
    }
    
    $row = $result->fetch_assoc();
    $user_id = intval($row['id']);
    $current_mode = isset($row['delivery_mode']) ? $row['delivery_mode'] : 'channel';
    
    // Check if delivery_mode column exists (might need setup)
    $col_check = $conn->query("SHOW COLUMNS FROM users LIKE 'delivery_mode'");
    if (!$col_check || $col_check->num_rows === 0) {
        // Add column if missing
        $conn->query("ALTER TABLE users ADD COLUMN delivery_mode VARCHAR(16) DEFAULT 'channel'");
    }
    
    // Update the delivery mode
    $mode_esc = $conn->real_escape_string($mode);
    $update = $conn->query("UPDATE users SET delivery_mode = '$mode_esc' WHERE id = $user_id");
    
    $conn->close();
    
    if (!$update) {
        send_response("❌ Failed to update your notification mode. Please try again.");
        return;
    }
    
    // Build response
    $mode_descriptions = array(
        'channel' => '📢 **Channel only** — You\'ll be @mentioned in #notifications',
        'dm' => '📬 **DM only** — You\'ll receive private messages from the bot',
        'both' => '📢📬 **Both** — You\'ll get @mentions AND DMs'
    );
    
    $content = "✅ **Notification mode updated!**\n\n";
    $content .= $mode_descriptions[$mode] . "\n\n";
    
    if ($mode === 'dm' || $mode === 'both') {
        $content .= "💡 **Note:** Make sure you have DMs enabled from server members and share a server with this bot to receive DMs.\n\n";
    }
    
    $content .= "**Your settings:**\n";
    $content .= "• Previous: `$current_mode`\n";
    $content .= "• New: `$mode`\n\n";
    $content .= "Use `/notifymode` again anytime to change this.";
    
    send_response($content);
}
