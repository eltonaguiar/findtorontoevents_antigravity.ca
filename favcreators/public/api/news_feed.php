<?php
/**
 * News Feed Aggregator API
 * Fetches, caches, and serves RSS news from 100+ sources across 4 categories.
 *
 * Actions:
 *   ?action=get       — Read articles (cache + DB), filtered by category/source/search/tag
 *   ?action=fetch     — Force re-fetch feeds, store to DB
 *   ?action=sources   — List all configured sources with status
 *   ?action=tags      — List all available tags with article counts
 *
 * Params:
 *   &category=toronto|canada|us|world|all  (default: all)
 *   &source=cbc_toronto|blogto|...         (filter by source key)
 *   &search=keyword                        (search titles/descriptions)
 *   &tag=crime|events|positive|...         (filter by tag)
 *   &page=1                                (pagination)
 *   &per_page=20                           (items per page, max 50)
 *
 * PHP 5.2 compatible. Separate DB: ejaguiar1_news
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if (isset($_SERVER['REQUEST_METHOD']) && $_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    exit;
}

require_once(dirname(__FILE__) . '/news_feed_schema.php');

// ────────────────────────────────────────────────────────────
//  Source Configuration
// ────────────────────────────────────────────────────────────

function _nf_get_sources() {
    return array(
        // ════════════════════════════════════════════════════════
        //  TORONTO — Major News (10)
        // ════════════════════════════════════════════════════════
        array('name' => 'BlogTO',               'key' => 'blogto',            'url' => 'https://feeds.feedburner.com/blogto',                                          'category' => 'toronto', 'domain' => 'blogto.com',          'tags' => 'events,food,lifestyle,downtown'),
        array('name' => 'Narcity Toronto',       'key' => 'narcity_toronto',   'url' => 'https://www.narcity.com/feeds/toronto.rss',                                    'category' => 'toronto', 'domain' => 'narcity.com',         'tags' => 'events,lifestyle,deals,positive'),
        array('name' => 'CBC Toronto',           'key' => 'cbc_toronto',       'url' => 'https://www.cbc.ca/webfeed/rss/rss-canada-toronto',                            'category' => 'toronto', 'domain' => 'cbc.ca',              'tags' => 'crime,politics,transit'),
        array('name' => 'Global News Toronto',   'key' => 'global_toronto',    'url' => 'https://globalnews.ca/toronto/feed/',                                          'category' => 'toronto', 'domain' => 'globalnews.ca',       'tags' => 'crime,politics'),
        array('name' => 'NOW Toronto',           'key' => 'now_toronto',       'url' => 'https://nowtoronto.com/feed/',                                                 'category' => 'toronto', 'domain' => 'nowtoronto.com',      'tags' => 'events,arts,food,lifestyle,positive'),
        array('name' => 'Toronto Sun',           'key' => 'toronto_sun',       'url' => 'https://torontosun.com/category/news/feed',                                    'category' => 'toronto', 'domain' => 'torontosun.com',      'tags' => 'crime,politics,sports'),
        array('name' => 'Daily Hive Toronto',    'key' => 'dailyhive_toronto', 'url' => 'https://dailyhive.com/feed/toronto',                                           'category' => 'toronto', 'domain' => 'dailyhive.com',       'tags' => 'events,food,lifestyle,deals'),
        array('name' => 'CityNews Toronto',      'key' => 'citynews_toronto',  'url' => 'https://toronto.citynews.ca/feed/',                                            'category' => 'toronto', 'domain' => 'toronto.citynews.ca', 'tags' => 'crime,politics,transit'),
        array('name' => 'Toronto Star - GTA',    'key' => 'star_gta',          'url' => 'https://www.thestar.com/search/?f=rss&t=article&c=news/gta*&l=50&s=start_time&sd=desc', 'category' => 'toronto', 'domain' => 'thestar.com', 'tags' => 'crime,politics,gta'),
        array('name' => 'City of Toronto',       'key' => 'city_toronto',      'url' => 'https://www.toronto.ca/news/feed/',                                            'category' => 'toronto', 'domain' => 'toronto.ca',          'tags' => 'politics,events,transit,positive'),

        // ════════════════════════════════════════════════════════
        //  TORONTO — Lifestyle, Culture & Events (14)
        // ════════════════════════════════════════════════════════
        array('name' => 'Toronto Life',          'key' => 'toronto_life',      'url' => 'https://torontolife.com/feed/',                                                'category' => 'toronto', 'domain' => 'torontolife.com',     'tags' => 'food,lifestyle,real_estate,arts,positive'),
        array('name' => 'Toronto Guardian',      'key' => 'toronto_guardian',  'url' => 'https://torontoguardian.com/feed/',                                            'category' => 'toronto', 'domain' => 'torontoguardian.com', 'tags' => 'positive,arts,food,hero,events'),
        array('name' => 'View the Vibe',         'key' => 'viewthevibe',       'url' => 'https://viewthevibe.com/feed/',                                                'category' => 'toronto', 'domain' => 'viewthevibe.com',     'tags' => 'events,food,lifestyle,positive'),
        array('name' => 'Over Here Toronto',     'key' => 'overhere_toronto',  'url' => 'https://overheretoronto.com/feed/',                                            'category' => 'toronto', 'domain' => 'overheretoronto.com', 'tags' => 'events,food,lifestyle,positive'),
        array('name' => 'Curiocity',             'key' => 'curiocity',         'url' => 'https://curiocity.com/feed/',                                                  'category' => 'toronto', 'domain' => 'curiocity.com',       'tags' => 'events,deals,food,lifestyle,positive'),
        array('name' => 'Streets of Toronto',    'key' => 'streets_toronto',   'url' => 'https://streetsoftoronto.com/feed/',                                           'category' => 'toronto', 'domain' => 'streetsoftoronto.com','tags' => 'lifestyle,arts,positive,downtown'),
        array('name' => 'INsauga',               'key' => 'insauga',           'url' => 'https://www.insauga.com/feed/',                                                'category' => 'toronto', 'domain' => 'insauga.com',         'tags' => 'crime,mississauga,brampton,gta'),
        array('name' => 'Toronto Star - Life',   'key' => 'star_life',         'url' => 'https://www.thestar.com/search/?f=rss&t=article&c=life*&l=50&s=start_time&sd=desc', 'category' => 'toronto', 'domain' => 'thestar.com', 'tags' => 'lifestyle,food,positive,health'),
        array('name' => 'Toronto Star - Arts',   'key' => 'star_entertainment','url' => 'https://www.thestar.com/search/?f=rss&t=article&c=entertainment*&l=50&s=start_time&sd=desc', 'category' => 'toronto', 'domain' => 'thestar.com', 'tags' => 'arts,events,positive'),
        array('name' => 'Intermission Magazine', 'key' => 'intermission',      'url' => 'https://www.intermissionmagazine.ca/feed/',                                    'category' => 'toronto', 'domain' => 'intermissionmagazine.ca', 'tags' => 'arts,events,positive'),
        array('name' => 'TorontoToday',          'key' => 'torontotoday',      'url' => 'https://www.torontotoday.ca/rss',                                              'category' => 'toronto', 'domain' => 'torontotoday.ca',     'tags' => 'crime,politics'),
        array('name' => 'Toronto Food Blog',     'key' => 'to_food_blog',      'url' => 'https://torontofoodblog.com/feed/',                                            'category' => 'toronto', 'domain' => 'torontofoodblog.com', 'tags' => 'food,positive,downtown'),
        array('name' => 'Diary of a TO Girl',    'key' => 'diary_to_girl',     'url' => 'https://diaryofatorontogirl.com/feed/',                                        'category' => 'toronto', 'domain' => 'diaryofatorontogirl.com', 'tags' => 'lifestyle,deals,food,events,positive'),
        array('name' => 'Storeys',               'key' => 'storeys',           'url' => 'https://storeys.com/feeds/feed.rss',                                           'category' => 'toronto', 'domain' => 'storeys.com',         'tags' => 'real_estate,downtown'),

        // ════════════════════════════════════════════════════════
        //  TORONTO — Blogs & Independent Media (5)
        // ════════════════════════════════════════════════════════
        array('name' => 'The Local (Toronto)',   'key' => 'the_local_to',      'url' => 'https://thelocal.to/feed/',                                                    'category' => 'toronto', 'domain' => 'thelocal.to',         'tags' => 'politics,transit,health'),
        array('name' => 'Spacing Toronto',       'key' => 'spacing_toronto',   'url' => 'https://spacing.ca/toronto/feed/',                                             'category' => 'toronto', 'domain' => 'spacing.ca',          'tags' => 'transit,politics,downtown'),
        array('name' => 'Toronto Mike',          'key' => 'toronto_mike',      'url' => 'https://torontomike.com/feed/',                                                'category' => 'toronto', 'domain' => 'torontomike.com',     'tags' => 'lifestyle,sports,positive'),
        array('name' => 'The Varsity (U of T)',  'key' => 'the_varsity',       'url' => 'https://thevarsity.ca/feed/',                                                  'category' => 'toronto', 'domain' => 'thevarsity.ca',       'tags' => 'politics,arts,downtown'),

        // ════════════════════════════════════════════════════════
        //  TORONTO — YouTube Channels (10)
        // ════════════════════════════════════════════════════════
        array('name' => '6ixBuzzTV',             'key' => '6ixbuzztv',         'url' => 'https://www.youtube.com/feeds/videos.xml?channel_id=UCAlBsloUr2UdJiappAG1EVw', 'category' => 'toronto', 'domain' => '6ix.buzz',            'tags' => 'crime,lifestyle,events'),
        array('name' => 'BlogTO (YouTube)',      'key' => 'blogto_yt',         'url' => 'https://www.youtube.com/feeds/videos.xml?channel_id=UCfIXdjgUFGqVwR3GjmiNneQ', 'category' => 'toronto', 'domain' => 'blogto.com',          'tags' => 'events,food,lifestyle,positive'),
        array('name' => 'CP24 (YouTube)',        'key' => 'cp24_yt',           'url' => 'https://www.youtube.com/feeds/videos.xml?channel_id=UCnW7gOT-W0MjNrCmB47u3yA', 'category' => 'toronto', 'domain' => 'cp24.com',            'tags' => 'crime,politics,transit'),
        array('name' => 'CityNews Toronto YT',   'key' => 'citynews_yt',       'url' => 'https://www.youtube.com/feeds/videos.xml?channel_id=UCsWM5Rti6cNixla4P4KOr2g', 'category' => 'toronto', 'domain' => 'toronto.citynews.ca', 'tags' => 'crime,politics'),
        array('name' => 'Toronto Star (YT)',     'key' => 'star_yt',           'url' => 'https://www.youtube.com/feeds/videos.xml?channel_id=UCNcfIRE3HGJbSd5-L83GVcw', 'category' => 'toronto', 'domain' => 'thestar.com',         'tags' => 'crime,politics,lifestyle'),
        array('name' => 'Narcity (YouTube)',     'key' => 'narcity_yt',        'url' => 'https://www.youtube.com/feeds/videos.xml?channel_id=UCMPF7ABQ9q5V8bj3SIuSGOQ', 'category' => 'toronto', 'domain' => 'narcity.com',         'tags' => 'events,lifestyle,positive'),
        array('name' => 'Explore TO (YT)',       'key' => 'explore_to_yt',     'url' => 'https://www.youtube.com/feeds/videos.xml?channel_id=UCB-0Xi2g_pQeaB8FPUqaImQ', 'category' => 'toronto', 'domain' => 'youtube.com',         'tags' => 'events,lifestyle,positive,downtown'),
        array('name' => 'Toronto 4K Walks',      'key' => 'to_walks_yt',       'url' => 'https://www.youtube.com/feeds/videos.xml?channel_id=UCFVr-RaFgxluqPrVuYGb2lQ', 'category' => 'toronto', 'domain' => 'youtube.com',         'tags' => 'lifestyle,positive,downtown'),
        array('name' => 'Peter Santenello TO',   'key' => 'santenello_yt',     'url' => 'https://www.youtube.com/feeds/videos.xml?channel_id=UC3Vuq4Q1bKFtAkEjRsNz5FA', 'category' => 'toronto', 'domain' => 'youtube.com',         'tags' => 'lifestyle,positive'),
        array('name' => 'Daily Hive (YT)',       'key' => 'dailyhive_yt',      'url' => 'https://www.youtube.com/feeds/videos.xml?channel_id=UCuJiUAFtpwuAJJI5f_EB2Pw', 'category' => 'toronto', 'domain' => 'dailyhive.com',       'tags' => 'events,food,lifestyle'),

        // ════════════════════════════════════════════════════════
        //  TORONTO — Reddit (10)
        // ════════════════════════════════════════════════════════
        array('name' => 'r/toronto',             'key' => 'reddit_toronto',    'url' => 'https://www.reddit.com/r/toronto/.rss',                                        'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'crime,events,transit,downtown'),
        array('name' => 'r/askTO',               'key' => 'reddit_askto',      'url' => 'https://www.reddit.com/r/askTO/.rss',                                          'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'lifestyle,events'),
        array('name' => 'r/TorontoEvents',       'key' => 'reddit_to_events',  'url' => 'https://www.reddit.com/r/Torontoevents/.rss',                                  'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'events'),
        array('name' => 'r/FoodToronto',         'key' => 'reddit_food_to',    'url' => 'https://www.reddit.com/r/FoodToronto/.rss',                                    'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'food'),
        array('name' => 'r/TorontoRealEstate',   'key' => 'reddit_to_re',      'url' => 'https://www.reddit.com/r/TorontoRealEstate/.rss',                              'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'real_estate'),
        array('name' => 'r/torontobiking',       'key' => 'reddit_to_bike',    'url' => 'https://www.reddit.com/r/torontobiking/.rss',                                  'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'transit,lifestyle,positive'),
        array('name' => 'r/Raptors',             'key' => 'reddit_raptors',    'url' => 'https://www.reddit.com/r/torontoraptors/.rss',                                 'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'sports'),
        array('name' => 'r/Leafs',               'key' => 'reddit_leafs',      'url' => 'https://www.reddit.com/r/leafs/.rss',                                          'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'sports'),
        array('name' => 'r/TFC',                 'key' => 'reddit_tfc',        'url' => 'https://www.reddit.com/r/tfc/.rss',                                            'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'sports'),
        array('name' => 'r/BlueJays',            'key' => 'reddit_bluejays',   'url' => 'https://www.reddit.com/r/Torontobluejays/.rss',                                'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'sports'),

        // ════════════════════════════════════════════════════════
        //  GTA — Regional News (10)
        // ════════════════════════════════════════════════════════
        array('name' => 'r/Mississauga',         'key' => 'reddit_mississauga','url' => 'https://www.reddit.com/r/mississauga/.rss',                                    'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'mississauga,gta'),
        array('name' => 'r/Brampton',            'key' => 'reddit_brampton',   'url' => 'https://www.reddit.com/r/Brampton/.rss',                                       'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'brampton,gta'),
        array('name' => 'r/Ontario',             'key' => 'reddit_ontario',    'url' => 'https://www.reddit.com/r/ontario/.rss',                                        'category' => 'canada',  'domain' => 'reddit.com',          'tags' => 'politics,gta'),
        array('name' => 'York Region',           'key' => 'york_region',       'url' => 'https://www.yorkregion.com/search/?f=rss&t=article&c=news*&l=50&s=start_time&sd=desc', 'category' => 'toronto', 'domain' => 'yorkregion.com', 'tags' => 'york_region,gta,crime'),
        array('name' => 'Mississauga.com',       'key' => 'mississauga_com',   'url' => 'https://www.mississauga.com/search/?f=rss&t=article&l=50&s=start_time&sd=desc','category' => 'toronto', 'domain' => 'mississauga.com',     'tags' => 'mississauga,gta'),
        array('name' => 'Durham Region',         'key' => 'durham_region',     'url' => 'https://www.durhamregion.com/search/?f=rss&t=article&l=50&s=start_time&sd=desc','category' => 'toronto', 'domain' => 'durhamregion.com',   'tags' => 'durham,gta'),
        array('name' => 'Inside Halton',         'key' => 'inside_halton',     'url' => 'https://www.insidehalton.com/search/?f=rss&t=article&c=news*&l=50&s=start_time&sd=desc', 'category' => 'toronto', 'domain' => 'insidehalton.com', 'tags' => 'halton,gta'),
        array('name' => 'Hamilton Spectator',    'key' => 'hamilton_spec',     'url' => 'https://www.thespec.com/search/?f=rss&t=article&c=news*&l=50&s=start_time&sd=desc', 'category' => 'toronto', 'domain' => 'thespec.com', 'tags' => 'gta,crime'),
        array('name' => 'Barrie Today',          'key' => 'barrie_today',      'url' => 'https://www.barrietoday.com/rss',                                              'category' => 'toronto', 'domain' => 'barrietoday.com',     'tags' => 'gta'),
        array('name' => 'r/Hamilton',            'key' => 'reddit_hamilton',   'url' => 'https://www.reddit.com/r/Hamilton/.rss',                                        'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'gta'),

        // ════════════════════════════════════════════════════════
        //  TORONTO — Sports (6)
        // ════════════════════════════════════════════════════════
        array('name' => 'Raptors HQ',            'key' => 'raptors_hq',        'url' => 'https://www.raptorshq.com/rss/current.xml',                                    'category' => 'toronto', 'domain' => 'raptorshq.com',       'tags' => 'sports,positive'),
        array('name' => 'Pension Plan Puppets',   'key' => 'ppp_leafs',         'url' => 'https://www.pensionplanpuppets.com/rss/current.xml',                           'category' => 'toronto', 'domain' => 'pensionplanpuppets.com','tags' => 'sports'),
        array('name' => 'Bluebird Banter',       'key' => 'bluebird_banter',   'url' => 'https://www.bluebirdbanter.com/rss/current.xml',                               'category' => 'toronto', 'domain' => 'bluebirdbanter.com',  'tags' => 'sports'),
        array('name' => 'Waking the Red',        'key' => 'waking_red',        'url' => 'https://www.wakingthered.com/rss/current.xml',                                 'category' => 'toronto', 'domain' => 'wakingthered.com',    'tags' => 'sports'),
        array('name' => 'Toronto Sun Sports',    'key' => 'sun_sports',        'url' => 'https://torontosun.com/category/sports/feed',                                  'category' => 'toronto', 'domain' => 'torontosun.com',      'tags' => 'sports'),
        array('name' => 'Sportsnet',             'key' => 'sportsnet',         'url' => 'https://www.sportsnet.ca/feed/',                                               'category' => 'canada',  'domain' => 'sportsnet.ca',        'tags' => 'sports'),

        // ════════════════════════════════════════════════════════
        //  TORONTO — Deals, Free Stuff, Real Estate (5)
        // ════════════════════════════════════════════════════════
        array('name' => 'RedFlagDeals',          'key' => 'redflagdeals',      'url' => 'https://forums.redflagdeals.com/feed/forum/9',                                 'category' => 'canada',  'domain' => 'redflagdeals.com',    'tags' => 'deals,free_stuff'),
        array('name' => 'SmartCanucks',          'key' => 'smartcanucks',      'url' => 'https://smartcanucks.ca/feed/',                                                'category' => 'canada',  'domain' => 'smartcanucks.ca',     'tags' => 'deals,free_stuff'),
        array('name' => 'r/PersonalFinanceCA',   'key' => 'reddit_pfc',        'url' => 'https://www.reddit.com/r/PersonalFinanceCanada/.rss',                          'category' => 'canada',  'domain' => 'reddit.com',          'tags' => 'deals'),
        array('name' => 'r/TODeals',             'key' => 'reddit_to_deals',   'url' => 'https://www.reddit.com/r/TODeals/.rss',                                        'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'deals,free_stuff'),
        array('name' => 'Buzz Connected',        'key' => 'buzzconnected',     'url' => 'https://buzzconnected.com/feed/',                                              'category' => 'canada',  'domain' => 'buzzconnected.com',   'tags' => 'deals,tech'),

        // ════════════════════════════════════════════════════════
        //  TORONTO — Tech & Startups (4)
        // ════════════════════════════════════════════════════════
        array('name' => 'BetaKit',               'key' => 'betakit',           'url' => 'https://betakit.com/feed/',                                                    'category' => 'canada',  'domain' => 'betakit.com',         'tags' => 'tech,positive'),
        array('name' => 'IT World Canada',       'key' => 'itworldcanada',     'url' => 'https://www.itworldcanada.com/feed',                                           'category' => 'canada',  'domain' => 'itworldcanada.com',   'tags' => 'tech'),
        array('name' => 'MobileSyrup',           'key' => 'mobilesyrup',       'url' => 'https://mobilesyrup.com/feed/',                                                'category' => 'canada',  'domain' => 'mobilesyrup.com',     'tags' => 'tech,deals'),
        array('name' => 'r/TorontoJobs',         'key' => 'reddit_to_jobs',    'url' => 'https://www.reddit.com/r/TorontoJobs/.rss',                                    'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'tech'),

        // ════════════════════════════════════════════════════════
        //  POSITIVE NEWS & WELLNESS (6)
        // ════════════════════════════════════════════════════════
        array('name' => 'Good News Network',     'key' => 'goodnewsnetwork',   'url' => 'https://www.goodnewsnetwork.org/feed/',                                        'category' => 'world',   'domain' => 'goodnewsnetwork.org', 'tags' => 'positive,hero'),
        array('name' => 'Positive News',         'key' => 'positivenews',      'url' => 'https://www.positive.news/feed/',                                              'category' => 'world',   'domain' => 'positive.news',       'tags' => 'positive,hero'),
        array('name' => 'r/UpliftingNews',       'key' => 'reddit_uplifting',  'url' => 'https://www.reddit.com/r/UpliftingNews/.rss',                                  'category' => 'world',   'domain' => 'reddit.com',          'tags' => 'positive,hero'),
        array('name' => 'r/HumansBeingBros',     'key' => 'reddit_bros',       'url' => 'https://www.reddit.com/r/HumansBeingBros/.rss',                                'category' => 'world',   'domain' => 'reddit.com',          'tags' => 'positive,hero'),
        array('name' => 'r/MadeMeSmile',         'key' => 'reddit_smile',      'url' => 'https://www.reddit.com/r/MadeMeSmile/.rss',                                   'category' => 'world',   'domain' => 'reddit.com',          'tags' => 'positive,hero'),
        array('name' => 'Reasons to be Cheerful','key' => 'reasons_cheerful',  'url' => 'https://reasonstobecheerful.world/feed/',                                      'category' => 'world',   'domain' => 'reasonstobecheerful.world', 'tags' => 'positive,hero'),
        array('name' => 'Sunny Skyz',           'key' => 'sunnyskyz',         'url' => 'https://www.sunnyskyz.com/rss.xml',                                                'category' => 'world',   'domain' => 'sunnyskyz.com',       'tags' => 'positive,hero'),
        array('name' => 'r/GetMotivated',       'key' => 'reddit_motivated',  'url' => 'https://www.reddit.com/r/GetMotivated/.rss',                                       'category' => 'world',   'domain' => 'reddit.com',          'tags' => 'positive'),
        array('name' => 'r/CanadaHousing',      'key' => 'reddit_ca_housing', 'url' => 'https://www.reddit.com/r/canadahousing/.rss',                                      'category' => 'canada',  'domain' => 'reddit.com',          'tags' => 'real_estate'),
        array('name' => 'r/TorontoAnarchy',     'key' => 'reddit_to_anarchy', 'url' => 'https://www.reddit.com/r/TorontoAnarchy/.rss',                                     'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'politics,lifestyle'),
        array('name' => 'r/Scarborough',        'key' => 'reddit_scarborough','url' => 'https://www.reddit.com/r/Scarborough/.rss',                                        'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'gta'),
        array('name' => 'r/Etobicoke',          'key' => 'reddit_etobicoke',  'url' => 'https://www.reddit.com/r/Etobicoke/.rss',                                          'category' => 'toronto', 'domain' => 'reddit.com',          'tags' => 'gta'),

        // ════════════════════════════════════════════════════════
        //  CANADIAN (8)
        // ════════════════════════════════════════════════════════
        array('name' => 'CBC Canada',            'key' => 'cbc_canada',        'url' => 'https://www.cbc.ca/webfeed/rss/rss-canada',                                    'category' => 'canada',  'domain' => 'cbc.ca',              'tags' => 'politics,crime'),
        array('name' => 'CBC Politics',          'key' => 'cbc_politics',      'url' => 'https://www.cbc.ca/webfeed/rss/rss-politics',                                  'category' => 'canada',  'domain' => 'cbc.ca',              'tags' => 'politics'),
        array('name' => 'Global News Canada',    'key' => 'global_canada',     'url' => 'https://globalnews.ca/feed/',                                                  'category' => 'canada',  'domain' => 'globalnews.ca',       'tags' => 'politics,crime'),
        array('name' => 'National Post',         'key' => 'national_post',     'url' => 'https://nationalpost.com/feed/',                                               'category' => 'canada',  'domain' => 'nationalpost.com',    'tags' => 'politics'),
        array('name' => 'CBC Business',          'key' => 'cbc_business',      'url' => 'https://www.cbc.ca/webfeed/rss/rss-business',                                  'category' => 'canada',  'domain' => 'cbc.ca',              'tags' => 'tech'),
        array('name' => 'CBC Top Stories',       'key' => 'cbc_top',           'url' => 'https://www.cbc.ca/webfeed/rss/rss-topstories',                                'category' => 'canada',  'domain' => 'cbc.ca',              'tags' => 'politics,crime'),
        array('name' => 'CBC Arts',              'key' => 'cbc_arts',          'url' => 'https://www.cbc.ca/webfeed/rss/rss-arts',                                      'category' => 'canada',  'domain' => 'cbc.ca',              'tags' => 'arts,positive'),
        array('name' => 'Macleans',              'key' => 'macleans',          'url' => 'https://macleans.ca/feed/',                                                    'category' => 'canada',  'domain' => 'macleans.ca',         'tags' => 'politics,lifestyle'),

        // ════════════════════════════════════════════════════════
        //  US (4)
        // ════════════════════════════════════════════════════════
        array('name' => 'CNN',                   'key' => 'cnn',              'url' => 'http://rss.cnn.com/rss/cnn_topstories.rss',                                     'category' => 'us',      'domain' => 'cnn.com',             'tags' => 'politics,crime'),
        array('name' => 'NPR',                   'key' => 'npr',              'url' => 'https://feeds.npr.org/1001/rss.xml',                                            'category' => 'us',      'domain' => 'npr.org',             'tags' => 'politics'),
        array('name' => 'NBC News',              'key' => 'nbc_news',         'url' => 'https://feeds.nbcnews.com/nbcnews/public/news',                                 'category' => 'us',      'domain' => 'nbcnews.com',         'tags' => 'politics,crime'),
        array('name' => 'Dexerto',               'key' => 'dexerto',          'url' => 'https://www.dexerto.com/feed/',                                                  'category' => 'us',      'domain' => 'dexerto.com',         'tags' => 'tech,lifestyle'),

        // ════════════════════════════════════════════════════════
        //  WORLD (5)
        // ════════════════════════════════════════════════════════
        array('name' => 'BBC World',             'key' => 'bbc_world',        'url' => 'https://feeds.bbci.co.uk/news/world/rss.xml',                                   'category' => 'world',   'domain' => 'bbc.co.uk',           'tags' => 'politics,crime'),
        array('name' => 'Al Jazeera',            'key' => 'aljazeera',        'url' => 'https://www.aljazeera.com/xml/rss/all.xml',                                     'category' => 'world',   'domain' => 'aljazeera.com',       'tags' => 'politics'),
        array('name' => 'The Guardian World',    'key' => 'guardian_world',   'url' => 'https://www.theguardian.com/world/rss',                                          'category' => 'world',   'domain' => 'theguardian.com',     'tags' => 'politics'),
        array('name' => 'Reuters Top News',      'key' => 'reuters',          'url' => 'https://www.reutersagency.com/feed/',                                           'category' => 'world',   'domain' => 'reuters.com',         'tags' => 'politics'),
        array('name' => 'r/WorldNews',           'key' => 'reddit_worldnews', 'url' => 'https://www.reddit.com/r/worldnews/.rss',                                       'category' => 'world',   'domain' => 'reddit.com',          'tags' => 'politics,crime')
    );
}

// ────────────────────────────────────────────────────────────
//  HTTP Fetch
// ────────────────────────────────────────────────────────────

function _nf_http_get($url) {
    if (function_exists('curl_init')) {
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 15);
        curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_MAXREDIRS, 3);
        curl_setopt($ch, CURLOPT_USERAGENT, 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        $body = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($code >= 200 && $code < 400 && $body !== false) {
            return $body;
        }
        return false;
    }

    $ctx = stream_context_create(array(
        'http' => array(
            'timeout' => 15,
            'user_agent' => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'follow_location' => true,
            'max_redirects' => 3
        ),
        'ssl' => array(
            'verify_peer' => false,
            'verify_peer_name' => false
        )
    ));
    $body = @file_get_contents($url, false, $ctx);
    return ($body !== false) ? $body : false;
}

// ────────────────────────────────────────────────────────────
//  File Cache
// ────────────────────────────────────────────────────────────

function _nf_cache_path($source_key) {
    return sys_get_temp_dir() . '/fte_news_' . $source_key . '.json';
}

function _nf_read_cache($source_key, $ttl) {
    $path = _nf_cache_path($source_key);
    if (!file_exists($path)) return false;
    $age = time() - filemtime($path);
    if ($age > $ttl) return false;
    $raw = @file_get_contents($path);
    if ($raw === false) return false;
    $data = json_decode($raw, true);
    return is_array($data) ? $data : false;
}

function _nf_read_stale_cache($source_key, $max_age) {
    $path = _nf_cache_path($source_key);
    if (!file_exists($path)) return false;
    $age = time() - filemtime($path);
    if ($age > $max_age) return false;
    $raw = @file_get_contents($path);
    if ($raw === false) return false;
    $data = json_decode($raw, true);
    return is_array($data) ? $data : false;
}

function _nf_write_cache($source_key, $articles) {
    $path = _nf_cache_path($source_key);
    @file_put_contents($path, json_encode($articles));
}

// ────────────────────────────────────────────────────────────
//  RSS Parser
// ────────────────────────────────────────────────────────────

function _nf_strip_cdata($str) {
    $str = preg_replace('/<!\[CDATA\[/', '', $str);
    $str = preg_replace('/\]\]>/', '', $str);
    return trim($str);
}

function _nf_extract_image($item_xml) {
    // media:thumbnail
    if (preg_match('/<media:thumbnail[^>]+url=["\']([^"\']+)["\']/i', $item_xml, $m)) {
        return $m[1];
    }
    // media:content with image
    if (preg_match('/<media:content[^>]+url=["\']([^"\']+)["\']/i', $item_xml, $m)) {
        if (preg_match('/\.(jpg|jpeg|png|gif|webp)/i', $m[1]) || preg_match('/medium=["\']image["\']/i', $item_xml)) {
            return $m[1];
        }
    }
    // enclosure with image type
    if (preg_match('/<enclosure[^>]+url=["\']([^"\']+)["\'][^>]*type=["\']image/i', $item_xml, $m)) {
        return $m[1];
    }
    if (preg_match('/<enclosure[^>]+type=["\']image[^"\']*["\'][^>]*url=["\']([^"\']+)["\']/i', $item_xml, $m)) {
        return $m[1];
    }
    // img tag in description
    if (preg_match('/<img[^>]+src=["\']([^"\']+)["\']/i', $item_xml, $m)) {
        return $m[1];
    }
    return '';
}

function _nf_parse_rss($xml_string, $source) {
    $articles = array();

    // Try simplexml first
    $parsed = _nf_parse_rss_simplexml($xml_string, $source);
    if ($parsed !== false && count($parsed) > 0) {
        return $parsed;
    }

    // Fallback: regex parsing
    if (!preg_match_all('/<item[^>]*>(.*?)<\/item>/si', $xml_string, $items)) {
        // Try <entry> for Atom feeds
        if (!preg_match_all('/<entry[^>]*>(.*?)<\/entry>/si', $xml_string, $items)) {
            return $articles;
        }
    }

    $logo = 'https://www.google.com/s2/favicons?domain=' . $source['domain'] . '&sz=32';

    foreach ($items[1] as $item_xml) {
        // Title
        $title = '';
        if (preg_match('/<title[^>]*>(.*?)<\/title>/si', $item_xml, $m)) {
            $title = _nf_strip_cdata($m[1]);
            $title = strip_tags($title);
            $title = html_entity_decode($title, ENT_QUOTES, 'UTF-8');
        }
        if (empty($title)) continue;

        // Link
        $link = '';
        if (preg_match('/<link[^>]*>(.*?)<\/link>/si', $item_xml, $m)) {
            $link = trim(_nf_strip_cdata($m[1]));
        }
        if (empty($link) && preg_match('/<link[^>]+href=["\']([^"\']+)["\']/i', $item_xml, $m)) {
            $link = trim($m[1]);
        }
        if (empty($link) && preg_match('/<guid[^>]*>(.*?)<\/guid>/si', $item_xml, $m)) {
            $guid = trim(_nf_strip_cdata($m[1]));
            if (strpos($guid, 'http') === 0) $link = $guid;
        }
        if (empty($link)) continue;

        // Date
        $pub_date = '';
        if (preg_match('/<pubDate[^>]*>(.*?)<\/pubDate>/si', $item_xml, $m)) {
            $pub_date = trim(_nf_strip_cdata($m[1]));
        }
        if (empty($pub_date) && preg_match('/<dc:date[^>]*>(.*?)<\/dc:date>/si', $item_xml, $m)) {
            $pub_date = trim(_nf_strip_cdata($m[1]));
        }
        if (empty($pub_date) && preg_match('/<published[^>]*>(.*?)<\/published>/si', $item_xml, $m)) {
            $pub_date = trim(_nf_strip_cdata($m[1]));
        }
        if (empty($pub_date) && preg_match('/<updated[^>]*>(.*?)<\/updated>/si', $item_xml, $m)) {
            $pub_date = trim(_nf_strip_cdata($m[1]));
        }
        $ts = !empty($pub_date) ? strtotime($pub_date) : time();
        if ($ts === false || $ts <= 0) $ts = time();

        // Description
        $desc = '';
        if (preg_match('/<description[^>]*>(.*?)<\/description>/si', $item_xml, $m)) {
            $desc = _nf_strip_cdata($m[1]);
        }
        if (empty($desc) && preg_match('/<content:encoded[^>]*>(.*?)<\/content:encoded>/si', $item_xml, $m)) {
            $desc = _nf_strip_cdata($m[1]);
        }
        if (empty($desc) && preg_match('/<summary[^>]*>(.*?)<\/summary>/si', $item_xml, $m)) {
            $desc = _nf_strip_cdata($m[1]);
        }
        $desc = strip_tags($desc);
        $desc = html_entity_decode($desc, ENT_QUOTES, 'UTF-8');
        $desc = preg_replace('/\s+/', ' ', $desc);
        if (strlen($desc) > 300) {
            $desc = substr($desc, 0, 297) . '...';
        }

        // Image
        $image = _nf_extract_image($item_xml);

        $source_tags = isset($source['tags']) ? $source['tags'] : '';
        $tags = _nf_auto_tag($title, $desc, $source_tags);

        $articles[] = array(
            'title'       => $title,
            'link'        => $link,
            'source_name' => $source['name'],
            'source_key'  => $source['key'],
            'source_logo' => $logo,
            'category'    => $source['category'],
            'pub_date'    => date('Y-m-d H:i:s', $ts),
            'pub_ts'      => $ts,
            'description' => $desc,
            'image_url'   => $image,
            'tags'        => $tags
        );
    }

    return $articles;
}

function _nf_parse_rss_simplexml($xml_string, $source) {
    if (!function_exists('simplexml_load_string')) return false;

    libxml_use_internal_errors(true);
    $xml = @simplexml_load_string($xml_string);
    if ($xml === false) return false;

    $articles = array();
    $logo = 'https://www.google.com/s2/favicons?domain=' . $source['domain'] . '&sz=32';

    // RSS 2.0 format
    $items_list = array();
    if (isset($xml->channel->item)) {
        foreach ($xml->channel->item as $item) {
            $items_list[] = $item;
        }
    }
    // Atom format
    if (count($items_list) === 0 && isset($xml->entry)) {
        foreach ($xml->entry as $item) {
            $items_list[] = $item;
        }
    }

    if (count($items_list) === 0) return false;

    $ns = $xml->getNamespaces(true);
    $media_ns = isset($ns['media']) ? $ns['media'] : 'http://search.yahoo.com/mrss/';

    foreach ($items_list as $item) {
        $title = trim((string)$item->title);
        if (empty($title)) continue;
        $title = html_entity_decode($title, ENT_QUOTES, 'UTF-8');

        // Link
        $link = '';
        if (isset($item->link)) {
            $link_val = (string)$item->link;
            if (!empty($link_val)) {
                $link = $link_val;
            }
        }
        if (empty($link) && isset($item->link['href'])) {
            $link = (string)$item->link['href'];
        }
        if (empty($link) && isset($item->link)) {
            $attrs = $item->link->attributes();
            if (isset($attrs['href'])) {
                $link = (string)$attrs['href'];
            }
        }
        if (empty($link) && isset($item->guid)) {
            $guid = (string)$item->guid;
            if (strpos($guid, 'http') === 0) $link = $guid;
        }
        if (empty($link)) continue;

        // Date
        $pub_date = '';
        if (isset($item->pubDate)) $pub_date = (string)$item->pubDate;
        if (empty($pub_date) && isset($item->published)) $pub_date = (string)$item->published;
        if (empty($pub_date) && isset($item->updated)) $pub_date = (string)$item->updated;
        $ts = !empty($pub_date) ? strtotime($pub_date) : time();
        if ($ts === false || $ts <= 0) $ts = time();

        // Description
        $desc = '';
        if (isset($item->description)) $desc = strip_tags((string)$item->description);
        if (empty($desc) && isset($item->summary)) $desc = strip_tags((string)$item->summary);
        $desc = html_entity_decode(trim($desc), ENT_QUOTES, 'UTF-8');
        $desc = preg_replace('/\s+/', ' ', $desc);
        if (strlen($desc) > 300) $desc = substr($desc, 0, 297) . '...';

        // Image via media namespace (@ suppresses PHP 5.2 SimpleXML node warnings)
        $image = '';
        $media = @$item->children($media_ns);
        if ($media && @isset($media->thumbnail)) {
            $attrs = @$media->thumbnail->attributes();
            if ($attrs && isset($attrs['url'])) $image = (string)$attrs['url'];
        }
        if (empty($image) && $media && @isset($media->content)) {
            $attrs = @$media->content->attributes();
            if ($attrs && isset($attrs['url'])) $image = (string)$attrs['url'];
        }
        if (empty($image) && isset($item->enclosure)) {
            $enc_attrs = $item->enclosure->attributes();
            $enc_type = isset($enc_attrs['type']) ? (string)$enc_attrs['type'] : '';
            if (strpos($enc_type, 'image') !== false && isset($enc_attrs['url'])) {
                $image = (string)$enc_attrs['url'];
            }
        }
        // Fallback: img in raw description
        if (empty($image) && isset($item->description)) {
            $raw_desc = (string)$item->description;
            if (preg_match('/<img[^>]+src=["\']([^"\']+)["\']/i', $raw_desc, $m2)) {
                $image = $m2[1];
            }
        }

        $source_tags = isset($source['tags']) ? $source['tags'] : '';
        $tags = _nf_auto_tag($title, $desc, $source_tags);

        $articles[] = array(
            'title'       => $title,
            'link'        => $link,
            'source_name' => $source['name'],
            'source_key'  => $source['key'],
            'source_logo' => $logo,
            'category'    => $source['category'],
            'pub_date'    => date('Y-m-d H:i:s', $ts),
            'pub_ts'      => $ts,
            'description' => $desc,
            'image_url'   => $image,
            'tags'        => $tags
        );
    }

    return (count($articles) > 0) ? $articles : false;
}

// ────────────────────────────────────────────────────────────
//  Time Ago
// ────────────────────────────────────────────────────────────

function _nf_time_ago($datetime_str) {
    $ts = strtotime($datetime_str);
    if ($ts === false) return '';
    $diff = time() - $ts;
    if ($diff < 0) return 'just now';
    if ($diff < 60) return 'just now';
    if ($diff < 3600) return floor($diff / 60) . 'm ago';
    if ($diff < 86400) return floor($diff / 3600) . 'h ago';
    if ($diff < 172800) return 'yesterday';
    if ($diff < 604800) return floor($diff / 86400) . 'd ago';
    return date('M j', $ts);
}

// ────────────────────────────────────────────────────────────
//  Auto-Tagging Engine
// ────────────────────────────────────────────────────────────

function _nf_get_tag_rules() {
    return array(
        'crime'      => array('crime','murder','shooting','stabbing','arrest','charged','police','homicide','robbery','assault','stolen','theft','fraud','suspect','weapon','gun','knife','fatal','killed','dead body','drug bust','carjack','break-in','arson'),
        'events'     => array('event','festival','concert','parade','exhibition','fair','show','gala','marathon','fireworks','carnival','market','open house','meetup','workshop','things to do','this week','this weekend','coming up','whats on','upcoming','tickets','admission'),
        'positive'   => array('hero','inspiring','heartwarming','good news','uplifting','amazing','celebrates','award','achievement','milestone','record-breaking','breakthrough','community spirit','volunteer','donation','rescued','saved','kindness','generous','hope','beautiful','wonderful','incredible','free','giveaway'),
        'hero'       => array('hero','rescued','saved a life','bravery','courage','firefighter saves','officer saves','good samaritan','selfless','risked','helped'),
        'food'       => array('restaurant','food','chef','recipe','brunch','dinner','lunch','cafe','bakery','pizza','sushi','patio','cocktail','beer','wine','foodie','tasting','michelin','menu','kitchen','dining'),
        'deals'      => array('deal','discount','sale','coupon','promo','free','giveaway','freebie','clearance','bargain','save money','cheap','affordable','price drop','offer'),
        'free_stuff' => array('free','giveaway','freebie','no cost','complimentary','gratis','free admission','free entry','free sample'),
        'sports'     => array('raptors','leafs','blue jays','bluejays','tfc','toronto fc','argonauts','nhl','nba','mlb','mls','playoff','championship','goal','score','game','match','season','traded','draft','coach'),
        'transit'    => array('ttc','subway','streetcar','bus route','transit','go train','go transit','presto','commute','bike lane','cycling','road closure','traffic','highway','dvp','gardiner','401','transit fare'),
        'real_estate'=> array('condo','housing','real estate','rent','mortgage','property','development','tower','building permit','zoning','affordable housing','home price','listing'),
        'arts'       => array('theatre','theater','art','gallery','museum','film','movie','music','dance','opera','comedy','exhibit','performance','artist','culture','literary','book','author'),
        'tech'       => array('startup','tech','ai','artificial intelligence','app','software','innovation','digital','coding','cybersecurity','data','crypto','blockchain','fintech'),
        'politics'   => array('mayor','council','election','premier','trudeau','ford','government','legislation','bill','policy','vote','liberal','conservative','ndp','parliament','senate','bylaw','budget'),
        'health'     => array('health','hospital','doctor','covid','vaccine','mental health','wellness','fitness','medical','cancer','heart','emergency room','er wait','healthcare'),
        'weather'    => array('weather','storm','snow','rain','tornado','heat wave','cold warning','flood','ice','forecast','temperature','wind','freezing'),
        'downtown'   => array('downtown','king street','queen street','yonge','bloor','kensington','distillery','harbourfront','cn tower','eaton','dundas','st lawrence','union station','financial district','liberty village','entertainment district','waterfront'),
        'mississauga'=> array('mississauga','square one','port credit','streetsville','erin mills','hurontario','peel region','meadowvale','clarkson','cooksville','lakeshore mississauga'),
        'brampton'   => array('brampton','bramalea','brampton transit','gore road','bovaird','flower city','peel region brampton','mount pleasant brampton'),
        'gta'        => array('gta','greater toronto','york region','durham region','halton','peel region','markham','richmond hill','vaughan','newmarket','oakville','burlington','ajax','pickering','oshawa','whitby','milton','aurora','scarborough','etobicoke','north york'),
        'york_region'=> array('markham','richmond hill','vaughan','newmarket','aurora','stouffville','king city','york region','georgina'),
        'durham'     => array('oshawa','whitby','ajax','pickering','clarington','bowmanville','durham region','port perry','uxbridge'),
        'halton'     => array('oakville','burlington','milton','halton hills','georgetown','halton region')
    );
}

function _nf_auto_tag($title, $description, $source_tags) {
    $text = strtolower($title . ' ' . $description);
    $rules = _nf_get_tag_rules();
    $tags = array();

    // Source-level tags
    if (!empty($source_tags)) {
        $src_tags = explode(',', $source_tags);
        foreach ($src_tags as $st) {
            $st = trim($st);
            if (!empty($st)) $tags[$st] = true;
        }
    }

    // Content-based keyword matching
    foreach ($rules as $tag => $keywords) {
        if (isset($tags[$tag])) continue; // already tagged by source
        foreach ($keywords as $kw) {
            if (strpos($text, $kw) !== false) {
                $tags[$tag] = true;
                break;
            }
        }
    }

    $result = array_keys($tags);
    sort($result);
    return implode(',', $result);
}

// ────────────────────────────────────────────────────────────
//  Fetch Single Source
// ────────────────────────────────────────────────────────────

function _nf_fetch_single($source) {
    $cache_ttl = 1800; // 30 minutes
    $stale_ttl = 7200; // 2 hours stale fallback

    // Check fresh cache
    $cached = _nf_read_cache($source['key'], $cache_ttl);
    if ($cached !== false) {
        return $cached;
    }

    // Fetch RSS
    $xml_string = _nf_http_get($source['url']);
    if ($xml_string === false || empty($xml_string)) {
        // Try stale cache
        $stale = _nf_read_stale_cache($source['key'], $stale_ttl);
        if ($stale !== false) return $stale;
        return array();
    }

    // Parse
    $articles = _nf_parse_rss($xml_string, $source);

    // Cache results (even if empty, to avoid hammering)
    _nf_write_cache($source['key'], $articles);

    return $articles;
}

// ────────────────────────────────────────────────────────────
//  Fetch All Sources
// ────────────────────────────────────────────────────────────

function _nf_fetch_all($category) {
    $sources = _nf_get_sources();
    $all_articles = array();

    foreach ($sources as $src) {
        if ($category !== 'all' && $src['category'] !== $category) continue;
        $articles = _nf_fetch_single($src);
        foreach ($articles as $art) {
            $all_articles[] = $art;
        }
    }

    // Sort by date descending
    usort($all_articles, '_nf_sort_by_date');

    return $all_articles;
}

function _nf_sort_by_date($a, $b) {
    $ta = isset($a['pub_ts']) ? $a['pub_ts'] : 0;
    $tb = isset($b['pub_ts']) ? $b['pub_ts'] : 0;
    if ($ta == $tb) return 0;
    return ($ta > $tb) ? -1 : 1;
}

// ────────────────────────────────────────────────────────────
//  Database Storage
// ────────────────────────────────────────────────────────────

function _nf_store_articles($conn, $articles) {
    if (!$conn || count($articles) === 0) return;

    $now = date('Y-m-d H:i:s');
    $inserted = 0;

    foreach ($articles as $art) {
        $title = $conn->real_escape_string($art['title']);
        $link  = $conn->real_escape_string($art['link']);
        $sname = $conn->real_escape_string($art['source_name']);
        $skey  = $conn->real_escape_string($art['source_key']);
        $slogo = $conn->real_escape_string(isset($art['source_logo']) ? $art['source_logo'] : '');
        $cat   = $conn->real_escape_string($art['category']);
        $pdate = $conn->real_escape_string($art['pub_date']);
        $desc  = $conn->real_escape_string(isset($art['description']) ? $art['description'] : '');
        $img   = $conn->real_escape_string(isset($art['image_url']) ? $art['image_url'] : '');
        $tags  = $conn->real_escape_string(isset($art['tags']) ? $art['tags'] : '');

        $sql = "INSERT INTO news_articles (title, link, source_name, source_key, source_logo, category, pub_date, description, image_url, tags, fetched_at)
                VALUES ('$title', '$link', '$sname', '$skey', '$slogo', '$cat', '$pdate', '$desc', '$img', '$tags', '$now')
                ON DUPLICATE KEY UPDATE title='$title', description='$desc', image_url='$img', tags='$tags', fetched_at='$now'";
        if ($conn->query($sql)) $inserted++;
    }

    return $inserted;
}

function _nf_update_source_status($conn, $source_key, $count, $error) {
    if (!$conn) return;
    $now  = date('Y-m-d H:i:s');
    $skey = $conn->real_escape_string($source_key);
    $err  = $conn->real_escape_string($error);

    $sql = "INSERT INTO news_sources (name, source_key, feed_url, category, last_fetched, article_count, last_error)
            VALUES ('', '$skey', '', '', '$now', $count, '$err')
            ON DUPLICATE KEY UPDATE last_fetched='$now', article_count=$count, last_error='$err'";
    $conn->query($sql);
}

function _nf_get_from_db($conn, $category, $source_filter, $search, $tag_filter, $page, $per_page) {
    if (!$conn) return false;

    $where = array();
    if ($category !== 'all') {
        $where[] = "category='" . $conn->real_escape_string($category) . "'";
    }
    if (!empty($source_filter)) {
        $where[] = "source_key='" . $conn->real_escape_string($source_filter) . "'";
    }
    if (!empty($search)) {
        $esc = $conn->real_escape_string($search);
        $where[] = "(title LIKE '%$esc%' OR description LIKE '%$esc%')";
    }
    if (!empty($tag_filter)) {
        // Support comma-separated tags (OR logic)
        $tag_parts = explode(',', $tag_filter);
        $tag_clauses = array();
        foreach ($tag_parts as $tp) {
            $tp = trim($tp);
            if (!empty($tp)) {
                $esc_tag = $conn->real_escape_string($tp);
                $tag_clauses[] = "FIND_IN_SET('$esc_tag', tags)";
            }
        }
        if (count($tag_clauses) > 0) {
            $where[] = '(' . implode(' OR ', $tag_clauses) . ')';
        }
    }

    $where_sql = count($where) > 0 ? ' WHERE ' . implode(' AND ', $where) : '';

    // Count
    $count_res = $conn->query("SELECT COUNT(*) as cnt FROM news_articles" . $where_sql);
    $total = 0;
    if ($count_res) {
        $row = $count_res->fetch_assoc();
        $total = (int)$row['cnt'];
    }

    // Fetch page
    $offset = ($page - 1) * $per_page;
    $sql = "SELECT * FROM news_articles" . $where_sql . " ORDER BY pub_date DESC LIMIT $offset, $per_page";
    $result = $conn->query($sql);

    $articles = array();
    if ($result) {
        while ($row = $result->fetch_assoc()) {
            $row['time_ago'] = _nf_time_ago($row['pub_date']);
            $row['pub_ts']   = strtotime($row['pub_date']);
            if (!isset($row['tags'])) $row['tags'] = '';
            $articles[] = $row;
        }
    }

    return array('articles' => $articles, 'total' => $total);
}

// ────────────────────────────────────────────────────────────
//  Seed sources table
// ────────────────────────────────────────────────────────────

function _nf_seed_sources($conn) {
    if (!$conn) return;
    $sources = _nf_get_sources();
    foreach ($sources as $src) {
        $name = $conn->real_escape_string($src['name']);
        $key  = $conn->real_escape_string($src['key']);
        $url  = $conn->real_escape_string($src['url']);
        $cat  = $conn->real_escape_string($src['category']);
        $logo = 'https://www.google.com/s2/favicons?domain=' . $conn->real_escape_string($src['domain']) . '&sz=32';
        $conn->query("INSERT IGNORE INTO news_sources (name, source_key, feed_url, category, logo_url, is_active) VALUES ('$name', '$key', '$url', '$cat', '$logo', 1)");
    }
}

// ────────────────────────────────────────────────────────────
//  Action Router
// ────────────────────────────────────────────────────────────

$action   = isset($_GET['action'])   ? strtolower(trim($_GET['action']))   : 'get';
$category = isset($_GET['category']) ? strtolower(trim($_GET['category'])) : 'all';
$source_f = isset($_GET['source'])   ? trim($_GET['source'])               : '';
$search   = isset($_GET['search'])   ? trim($_GET['search'])               : '';
$tag_f    = isset($_GET['tag'])      ? strtolower(trim($_GET['tag']))      : '';
$page     = isset($_GET['page'])     ? max(1, (int)$_GET['page'])          : 1;
$per_page = isset($_GET['per_page']) ? min(50, max(1, (int)$_GET['per_page'])) : 20;

$valid_cats = array('all', 'toronto', 'canada', 'us', 'world');
if (!in_array($category, $valid_cats)) $category = 'all';

// Connect DB (optional — API works without it)
$nf_conn = _nf_db_connect();
if ($nf_conn) {
    _nf_ensure_tables($nf_conn);
}

// ── ACTION: tags ──
if ($action === 'tags') {
    $all_tags = array(
        'crime'       => array('label' => 'Crime & Safety',    'icon' => '🚨', 'color' => '#dc3545'),
        'events'      => array('label' => 'Events',            'icon' => '🎉', 'color' => '#6f42c1'),
        'positive'    => array('label' => 'Positive News',     'icon' => '☀️', 'color' => '#28a745'),
        'hero'        => array('label' => 'Heroes',            'icon' => '🦸', 'color' => '#fd7e14'),
        'food'        => array('label' => 'Food & Dining',     'icon' => '🍽️', 'color' => '#e83e8c'),
        'deals'       => array('label' => 'Deals',             'icon' => '💰', 'color' => '#20c997'),
        'free_stuff'  => array('label' => 'Free Stuff',        'icon' => '🎁', 'color' => '#17a2b8'),
        'sports'      => array('label' => 'Sports',            'icon' => '⚽', 'color' => '#007bff'),
        'transit'     => array('label' => 'Transit & Traffic',  'icon' => '🚇', 'color' => '#6610f2'),
        'real_estate' => array('label' => 'Real Estate',       'icon' => '🏠', 'color' => '#795548'),
        'arts'        => array('label' => 'Arts & Culture',    'icon' => '🎭', 'color' => '#9c27b0'),
        'tech'        => array('label' => 'Tech',              'icon' => '💻', 'color' => '#2196f3'),
        'politics'    => array('label' => 'Politics',          'icon' => '🏛️', 'color' => '#607d8b'),
        'health'      => array('label' => 'Health',            'icon' => '❤️', 'color' => '#f44336'),
        'weather'     => array('label' => 'Weather',           'icon' => '🌤️', 'color' => '#03a9f4'),
        'lifestyle'   => array('label' => 'Lifestyle',         'icon' => '✨', 'color' => '#ff9800'),
        'downtown'    => array('label' => 'Downtown TO',       'icon' => '🏙️', 'color' => '#3f51b5'),
        'mississauga' => array('label' => 'Mississauga',       'icon' => '📍', 'color' => '#009688'),
        'brampton'    => array('label' => 'Brampton',          'icon' => '📍', 'color' => '#4caf50'),
        'gta'         => array('label' => 'GTA',               'icon' => '🗺️', 'color' => '#ff5722'),
        'york_region' => array('label' => 'York Region',       'icon' => '📍', 'color' => '#8bc34a'),
        'durham'      => array('label' => 'Durham',            'icon' => '📍', 'color' => '#cddc39'),
        'halton'      => array('label' => 'Halton',            'icon' => '📍', 'color' => '#ffc107')
    );
    echo json_encode(array('ok' => true, 'tags' => $all_tags));
    exit;
}

// ── ACTION: sources ──
if ($action === 'sources') {
    $sources = _nf_get_sources();
    $out = array();
    foreach ($sources as $src) {
        $cache_file = _nf_cache_path($src['key']);
        $last_fetched = file_exists($cache_file) ? date('Y-m-d H:i:s', filemtime($cache_file)) : null;
        $cache_age = file_exists($cache_file) ? (int)((time() - filemtime($cache_file)) / 60) : null;
        $out[] = array(
            'name'          => $src['name'],
            'key'           => $src['key'],
            'category'      => $src['category'],
            'tags'          => isset($src['tags']) ? $src['tags'] : '',
            'feed_url'      => $src['url'],
            'logo'          => 'https://www.google.com/s2/favicons?domain=' . $src['domain'] . '&sz=32',
            'last_fetched'  => $last_fetched,
            'cache_age_min' => $cache_age
        );
    }
    echo json_encode(array('ok' => true, 'sources' => $out, 'total' => count($out)));
    exit;
}

// ── ACTION: fetch ──
if ($action === 'fetch') {
    $sources = _nf_get_sources();
    $total_articles = 0;
    $source_results = array();

    foreach ($sources as $src) {
        if ($category !== 'all' && $src['category'] !== $category) continue;

        $xml_string = _nf_http_get($src['url']);
        $articles = array();
        $error = '';

        if ($xml_string === false || empty($xml_string)) {
            $error = 'Failed to fetch feed';
        } else {
            $articles = _nf_parse_rss($xml_string, $src);
            if (count($articles) === 0) {
                $error = 'No articles parsed';
            }
        }

        _nf_write_cache($src['key'], $articles);

        if ($nf_conn && count($articles) > 0) {
            _nf_store_articles($nf_conn, $articles);
        }
        if ($nf_conn) {
            _nf_update_source_status($nf_conn, $src['key'], count($articles), $error);
        }

        $source_results[] = array(
            'source' => $src['name'],
            'key'    => $src['key'],
            'count'  => count($articles),
            'error'  => $error
        );
        $total_articles += count($articles);
    }

    echo json_encode(array(
        'ok'             => true,
        'action'         => 'fetch',
        'category'       => $category,
        'total_articles' => $total_articles,
        'sources'        => $source_results,
        'fetched_at'     => date('Y-m-d H:i:s')
    ));
    exit;
}

// ── ACTION: get (default) ──

// Strategy: try DB first (has search/pagination), fallback to file cache aggregation
$db_result = false;
if ($nf_conn) {
    $db_result = _nf_get_from_db($nf_conn, $category, $source_f, $search, $tag_f, $page, $per_page);
}

if ($db_result !== false && $db_result['total'] > 0) {
    // Serve from DB
    echo json_encode(array(
        'ok'         => true,
        'source'     => 'database',
        'category'   => $category,
        'articles'   => $db_result['articles'],
        'total'      => $db_result['total'],
        'page'       => $page,
        'per_page'   => $per_page,
        'fetched_at' => date('Y-m-d H:i:s')
    ));
} else {
    // Fallback: fetch from RSS cache/live
    $all_articles = _nf_fetch_all($category);

    // Store to DB if available
    if ($nf_conn && count($all_articles) > 0) {
        _nf_seed_sources($nf_conn);
        _nf_store_articles($nf_conn, $all_articles);
    }

    // Apply source filter
    if (!empty($source_f)) {
        $filtered = array();
        foreach ($all_articles as $art) {
            if ($art['source_key'] === $source_f) $filtered[] = $art;
        }
        $all_articles = $filtered;
    }

    // Apply search filter
    if (!empty($search)) {
        $filtered = array();
        $search_lower = strtolower($search);
        foreach ($all_articles as $art) {
            if (strpos(strtolower($art['title']), $search_lower) !== false ||
                strpos(strtolower($art['description']), $search_lower) !== false) {
                $filtered[] = $art;
            }
        }
        $all_articles = $filtered;
    }

    // Apply tag filter
    if (!empty($tag_f)) {
        $tag_parts = explode(',', $tag_f);
        $filtered = array();
        foreach ($all_articles as $art) {
            $art_tags = isset($art['tags']) ? $art['tags'] : '';
            foreach ($tag_parts as $tp) {
                $tp = trim($tp);
                if (!empty($tp) && strpos(',' . $art_tags . ',', ',' . $tp . ',') !== false) {
                    $filtered[] = $art;
                    break;
                }
            }
        }
        $all_articles = $filtered;
    }

    $total = count($all_articles);

    // Paginate
    $offset = ($page - 1) * $per_page;
    $page_articles = array_slice($all_articles, $offset, $per_page);

    // Add time_ago
    foreach ($page_articles as $idx => $art) {
        $page_articles[$idx]['time_ago'] = _nf_time_ago($art['pub_date']);
    }

    echo json_encode(array(
        'ok'         => true,
        'source'     => 'rss_cache',
        'category'   => $category,
        'articles'   => $page_articles,
        'total'      => $total,
        'page'       => $page,
        'per_page'   => $per_page,
        'fetched_at' => date('Y-m-d H:i:s')
    ));
}

if ($nf_conn) $nf_conn->close();
