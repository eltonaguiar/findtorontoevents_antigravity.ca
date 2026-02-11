<?php
/**
 * Discord Slash Commands Registration
 * Run once to register/update slash commands with Discord
 * 
 * Usage: https://findtorontoevents.ca/fc/api/discord_register_commands.php
 * 
 * Note: This uses the Bot Token, not the OAuth client secret.
 * Set DISCORD_BOT_TOKEN in your .env file.
 */

header('Content-Type: application/json');

require_once dirname(__FILE__) . '/discord_config.php';

$config = get_discord_config();
$application_id = $config['client_id'];
$bot_token = isset($config['bot_token']) ? $config['bot_token'] : '';

if (empty($application_id)) {
    echo json_encode(array('ok' => false, 'error' => 'DISCORD_CLIENT_ID not configured'));
    exit;
}

if (empty($bot_token)) {
    echo json_encode(array('ok' => false, 'error' => 'DISCORD_BOT_TOKEN not configured. Add it to your .env file.'));
    exit;
}

// Define slash commands (PHP 5.2 compatible array syntax)
// All commands prefixed with "fc-" for easy discovery (type /fc- to see all)
$commands = array(
    array(
        'name' => 'fc-live',
        'description' => 'See which of your tracked creators are live right now',
        'type' => 1
    ),
    array(
        'name' => 'fc-creators',
        'description' => 'List all creators you have notifications enabled for',
        'type' => 1
    ),
    array(
        'name' => 'fc-posts',
        'description' => 'See latest posts from a creator',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'creator',
                'description' => 'Creator name to search for',
                'type' => 3,
                'required' => true
            ),
            array(
                'name' => 'count',
                'description' => 'Number of posts to show (default 5, max 25)',
                'type' => 4,
                'required' => false,
                'min_value' => 1,
                'max_value' => 25
            )
        )
    ),
    array(
        'name' => 'fc-feed',
        'description' => 'See latest updates from ALL your followed creators',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'count',
                'description' => 'Number of updates to show (default 10, max 25)',
                'type' => 4,
                'required' => false,
                'min_value' => 1,
                'max_value' => 25
            ),
            array(
                'name' => 'platform',
                'description' => 'Filter by platform',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'YouTube', 'value' => 'youtube'),
                    array('name' => 'Twitch', 'value' => 'twitch'),
                    array('name' => 'Kick', 'value' => 'kick'),
                    array('name' => 'TikTok', 'value' => 'tiktok'),
                    array('name' => 'Twitter', 'value' => 'twitter'),
                    array('name' => 'Instagram', 'value' => 'instagram'),
                    array('name' => 'Reddit', 'value' => 'reddit')
                )
            )
        )
    ),
    array(
        'name' => 'fc-about',
        'description' => 'Get info about a creator (platforms, live status)',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'creator',
                'description' => 'Creator name to search for',
                'type' => 3,
                'required' => true
            )
        )
    ),
    array(
        'name' => 'fc-events',
        'description' => 'Find Toronto events (dating, music, free, etc.)',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'search',
                'description' => 'What to search for (dating, music, comedy, free, etc.)',
                'type' => 3,
                'required' => true
            ),
            array(
                'name' => 'when',
                'description' => 'When (today, tomorrow, weekend, this week)',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Today', 'value' => 'today'),
                    array('name' => 'Tomorrow', 'value' => 'tomorrow'),
                    array('name' => 'This Weekend', 'value' => 'weekend'),
                    array('name' => 'This Week', 'value' => 'this week')
                )
            )
        )
    ),
    array(
        'name' => 'fc-myevents',
        'description' => 'See your saved Toronto events',
        'type' => 1
    ),
    array(
        'name' => 'fc-subscribe',
        'description' => 'Subscribe to automatic event notifications',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'category',
                'description' => 'Event category (currently: dating)',
                'type' => 3,
                'required' => true,
                'choices' => array(
                    array('name' => 'Dating Events', 'value' => 'dating')
                )
            ),
            array(
                'name' => 'frequency',
                'description' => 'How often to receive notifications',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Daily (every morning)', 'value' => 'daily'),
                    array('name' => 'Weekly (Monday mornings)', 'value' => 'weekly'),
                    array('name' => 'Both daily and weekly', 'value' => 'both')
                )
            )
        )
    ),
    array(
        'name' => 'fc-unsubscribe',
        'description' => 'Stop receiving automatic event notifications',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'category',
                'description' => 'Event category to unsubscribe from',
                'type' => 3,
                'required' => true,
                'choices' => array(
                    array('name' => 'Dating Events', 'value' => 'dating')
                )
            )
        )
    ),
    array(
        'name' => 'fc-mysubs',
        'description' => 'View your event notification subscriptions',
        'type' => 1
    ),
    array(
        'name' => 'fc-link',
        'description' => 'Get instructions to link your Discord to FavCreators',
        'type' => 1
    ),
    array(
        'name' => 'fc-help',
        'description' => 'Show available FavCreators bot commands',
        'type' => 1
    ),
    array(
        'name' => 'fc-info',
        'description' => 'See all findtorontoevents.ca apps and features',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'feature',
                'description' => 'Get detailed info about a specific feature',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Toronto Events', 'value' => 'events'),
                    array('name' => 'Fav Creators', 'value' => 'creators'),
                    array('name' => 'Movie/TV Trailers', 'value' => 'trailers'),
                    array('name' => 'Stock Ideas', 'value' => 'stocks'),
                    array('name' => 'Mental Health', 'value' => 'mental'),
                    array('name' => '$100K+ Jobs', 'value' => 'jobs'),
                    array('name' => 'Windows Fixer', 'value' => 'windows')
                )
            )
        )
    ),
    array(
        'name' => 'fc-movies',
        'description' => 'Search movies and TV shows from our trailer database',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'search',
                'description' => 'Search by title (leave empty for latest releases)',
                'type' => 3,
                'required' => false
            ),
            array(
                'name' => 'type',
                'description' => 'Filter by content type',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Movies', 'value' => 'movie'),
                    array('name' => 'TV Shows', 'value' => 'tv'),
                    array('name' => 'Both', 'value' => 'both')
                )
            )
        )
    ),
    array(
        'name' => 'fc-newreleases',
        'description' => 'See new movie and TV show releases',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'type',
                'description' => 'Filter by content type',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Movies', 'value' => 'movie'),
                    array('name' => 'TV Shows', 'value' => 'tv'),
                    array('name' => 'Both', 'value' => 'both')
                )
            ),
            array(
                'name' => 'period',
                'description' => 'Time period',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'This Week', 'value' => 'week'),
                    array('name' => 'This Month', 'value' => 'month'),
                    array('name' => 'Coming Soon (2026)', 'value' => 'upcoming')
                )
            )
        )
    ),
    array(
        'name' => 'fc-trailers',
        'description' => 'Get a trailer for a movie or TV show',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'title',
                'description' => 'Movie or TV show title to find trailer for',
                'type' => 3,
                'required' => true
            )
        )
    ),
    array(
        'name' => 'fc-stocks',
        'description' => 'View today\'s AI-validated stock picks',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'rating',
                'description' => 'Filter by rating',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Strong Buy only', 'value' => 'strong_buy'),
                    array('name' => 'Buy or better', 'value' => 'buy'),
                    array('name' => 'All picks', 'value' => 'all')
                )
            )
        )
    ),
    array(
        'name' => 'fc-stock',
        'description' => 'Get details about a specific stock pick',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'symbol',
                'description' => 'Stock ticker symbol (e.g. AAPL, NVDA)',
                'type' => 3,
                'required' => true
            )
        )
    ),
    array(
        'name' => 'fc-stockperf',
        'description' => 'View stock pick performance statistics',
        'type' => 1
    ),
    array(
        'name' => 'fc-stocksub',
        'description' => 'Subscribe to alerts when a stock is picked',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'symbol',
                'description' => 'Stock ticker symbol (e.g. AAPL, NVDA)',
                'type' => 3,
                'required' => true
            )
        )
    ),
    array(
        'name' => 'fc-stockunsub',
        'description' => 'Unsubscribe from stock alerts',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'symbol',
                'description' => 'Stock ticker symbol to unsubscribe from',
                'type' => 3,
                'required' => true
            )
        )
    ),
    array(
        'name' => 'fc-mystocks',
        'description' => 'View your stock subscriptions',
        'type' => 1
    ),
    array(
        'name' => 'fc-weather',
        'description' => 'Get weather alerts and RealFeel temperature for your location',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'location',
                'description' => 'Postal code (e.g. M5V 3A8) or city name (e.g. Toronto)',
                'type' => 3,
                'required' => true
            )
        )
    ),
    // Mental Health Resources Command
    array(
        'name' => 'fc-mentalhealth',
        'description' => 'Get mental health resources, crisis lines, and wellness tools',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'topic',
                'description' => 'Specific topic or tool to learn about',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Crisis Lines', 'value' => 'crisis'),
                    array('name' => 'Breathing Exercise (4-7-8)', 'value' => 'breathing'),
                    array('name' => '5-4-3-2-1 Grounding', 'value' => 'grounding'),
                    array('name' => 'Panic Attack Relief', 'value' => 'panic'),
                    array('name' => 'All Wellness Games', 'value' => 'games'),
                    array('name' => 'Resources by Demographics', 'value' => 'demographics')
                )
            )
        )
    ),
    // Near Me / Location Finder command
    array(
        'name' => 'fc-nearme',
        'description' => 'Find nearby places, restaurants, services, and amenities',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'query',
                'description' => 'What to find (e.g. coffee shops, washrooms, halal pizza, pharmacy)',
                'type' => 3,
                'required' => true
            ),
            array(
                'name' => 'location',
                'description' => 'Where to search (postal code, intersection, landmark). Default: downtown Toronto',
                'type' => 3,
                'required' => false
            ),
            array(
                'name' => 'filter',
                'description' => 'Time/availability filter',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Open Now', 'value' => 'open_now'),
                    array('name' => 'Open Late (past 11pm)', 'value' => 'open_late'),
                    array('name' => 'Open 24/7', 'value' => 'open_247'),
                    array('name' => 'Top Rated', 'value' => 'top_rated')
                )
            ),
            array(
                'name' => 'dietary',
                'description' => 'Dietary restriction filter',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Halal', 'value' => 'halal'),
                    array('name' => 'Vegan', 'value' => 'vegan'),
                    array('name' => 'Kosher', 'value' => 'kosher'),
                    array('name' => 'Vegetarian', 'value' => 'vegetarian'),
                    array('name' => 'Gluten-Free', 'value' => 'gluten-free')
                )
            ),
            array(
                'name' => 'radius',
                'description' => 'Search radius in km (default 2, max 50)',
                'type' => 4,
                'required' => false,
                'min_value' => 1,
                'max_value' => 50
            )
        )
    ),
    // World Events command
    array(
        'name' => 'fc-worldevents',
        'description' => 'See what\'s happening in the world today (Super Bowl, news, holidays, etc.)',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'range',
                'description' => 'Time range to show',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Today', 'value' => 'today'),
                    array('name' => 'This Week', 'value' => 'week'),
                    array('name' => 'Next Few Days', 'value' => '3days')
                )
            )
        )
    ),
    // Notification delivery mode command
    array(
        'name' => 'fc-notifymode',
        'description' => 'Choose how you receive notifications (DM, channel, or both)',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'mode',
                'description' => 'Where to receive notifications',
                'type' => 3,
                'required' => true,
                'choices' => array(
                    array('name' => 'Channel only (#notifications)', 'value' => 'channel'),
                    array('name' => 'DM only (private messages)', 'value' => 'dm'),
                    array('name' => 'Both channel and DM', 'value' => 'both')
                )
            )
        )
    ),
    // ─── Penny Stock Picks Commands ──────────────────────────
    array(
        'name' => 'fc-penny',
        'description' => 'Daily penny stock picks scored by 7-factor quality algorithm',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'rating',
                'description' => 'Filter by rating',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Strong Buy only', 'value' => 'STRONG_BUY'),
                    array('name' => 'Buy or better', 'value' => 'BUY'),
                    array('name' => 'All picks', 'value' => 'all')
                )
            ),
            array(
                'name' => 'country',
                'description' => 'Filter by market',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'US stocks', 'value' => 'US'),
                    array('name' => 'Canadian stocks', 'value' => 'CA'),
                    array('name' => 'Both', 'value' => 'ALL')
                )
            )
        )
    ),
    array(
        'name' => 'fc-pennydetail',
        'description' => 'Get detailed scoring breakdown for a penny stock pick',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'symbol',
                'description' => 'Stock ticker symbol (e.g. SNDL, ABEV)',
                'type' => 3,
                'required' => true
            )
        )
    ),
    // ─── Daily Picks Commands ───────────────────────────────
    array(
        'name' => 'fc-crypto',
        'description' => 'Daily crypto picks from 19 algorithms (BTC, ETH, SOL, etc.)',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'timeline',
                'description' => 'Trading timeline',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Scalp (1-4 hours)', 'value' => 'scalp'),
                    array('name' => 'Day Trade (4-24 hours)', 'value' => 'daytrader'),
                    array('name' => 'Swing (1-7 days)', 'value' => 'swing'),
                    array('name' => 'All timeframes', 'value' => 'all')
                )
            ),
            array(
                'name' => 'budget',
                'description' => 'Your trading budget for position sizing guidance',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Under $500', 'value' => 'small'),
                    array('name' => '$500-$5,000', 'value' => 'medium'),
                    array('name' => 'Over $5,000', 'value' => 'large')
                )
            )
        )
    ),
    array(
        'name' => 'fc-forex',
        'description' => 'Daily forex picks (EUR/USD, GBP/USD, USD/JPY, etc.)',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'timeline',
                'description' => 'Trading timeline',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Scalp (1-4 hours)', 'value' => 'scalp'),
                    array('name' => 'Day Trade (4-24 hours)', 'value' => 'daytrader'),
                    array('name' => 'Swing (1-7 days)', 'value' => 'swing'),
                    array('name' => 'All timeframes', 'value' => 'all')
                )
            ),
            array(
                'name' => 'budget',
                'description' => 'Your trading budget for position sizing guidance',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Under $500', 'value' => 'small'),
                    array('name' => '$500-$5,000', 'value' => 'medium'),
                    array('name' => 'Over $5,000', 'value' => 'large')
                )
            )
        )
    ),
    array(
        'name' => 'fc-realtime',
        'description' => 'See recent winning trades across stocks, crypto and forex',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'asset',
                'description' => 'Filter by asset class',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Crypto', 'value' => 'CRYPTO'),
                    array('name' => 'Forex', 'value' => 'FOREX'),
                    array('name' => 'Stocks', 'value' => 'STOCK'),
                    array('name' => 'All', 'value' => 'all')
                )
            )
        )
    ),
    array(
        'name' => 'fc-momentum',
        'description' => 'Highest-conviction picks most likely to continue going up',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'asset',
                'description' => 'Filter by asset class',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Crypto', 'value' => 'CRYPTO'),
                    array('name' => 'Forex', 'value' => 'FOREX'),
                    array('name' => 'Stocks', 'value' => 'STOCK'),
                    array('name' => 'All', 'value' => 'all')
                )
            )
        )
    ),
    array(
        'name' => 'fc-picks',
        'description' => 'Daily picks across all markets with budget and timeline options',
        'type' => 1,
        'options' => array(
            array(
                'name' => 'asset',
                'description' => 'Asset class',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Crypto', 'value' => 'CRYPTO'),
                    array('name' => 'Forex', 'value' => 'FOREX'),
                    array('name' => 'Stocks', 'value' => 'STOCK'),
                    array('name' => 'All Markets', 'value' => 'all')
                )
            ),
            array(
                'name' => 'timeline',
                'description' => 'Trading timeline',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Scalp (1-4 hours)', 'value' => 'scalp'),
                    array('name' => 'Day Trade (4-24 hours)', 'value' => 'daytrader'),
                    array('name' => 'Swing (1-7 days)', 'value' => 'swing'),
                    array('name' => 'All timeframes', 'value' => 'all')
                )
            ),
            array(
                'name' => 'budget',
                'description' => 'Your trading budget for position sizing guidance',
                'type' => 3,
                'required' => false,
                'choices' => array(
                    array('name' => 'Under $500', 'value' => 'small'),
                    array('name' => '$500-$5,000', 'value' => 'medium'),
                    array('name' => 'Over $5,000', 'value' => 'large')
                )
            )
        )
    )
);

// Register commands globally using bulk PUT (avoids rate limits)
$url = "https://discord.com/api/v10/applications/$application_id/commands";

$ch = curl_init($url);
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, 'PUT');
curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($commands));
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 60);
curl_setopt($ch, CURLOPT_HTTPHEADER, array(
    'Authorization: Bot ' . $bot_token,
    'Content-Type: application/json',
    'User-Agent: FavCreators-Bot/1.0'
));

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$error = curl_error($ch);
curl_close($ch);

$response_data = json_decode($response, true);

if ($http_code >= 200 && $http_code < 300 && is_array($response_data)) {
    $results = array();
    foreach ($response_data as $cmd) {
        $results[] = array(
            'command' => '/' . $cmd['name'],
            'status' => 'registered',
            'id' => isset($cmd['id']) ? $cmd['id'] : null
        );
    }
    echo json_encode(array(
        'ok' => true,
        'message' => 'All ' . count($results) . ' commands registered successfully',
        'commands' => $results,
        'note' => 'Global commands may take up to 1 hour to appear in all servers'
    ));
} else {
    echo json_encode(array(
        'ok' => false,
        'message' => 'Failed to register commands',
        'http_code' => $http_code,
        'error' => $error ? $error : (isset($response_data['message']) ? $response_data['message'] : 'Unknown error'),
        'response' => $response_data
    ));
}
