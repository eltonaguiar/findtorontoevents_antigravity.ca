<?php
/**
 * world_events.php — World Events API (FREE, no API keys)
 *
 * Returns major world events happening today/this week that "everyone is talking about."
 * Combines 3 sources:
 *   1. Curated calendar of major annual events (Super Bowl, Oscars, holidays, etc.)
 *   2. Wikipedia Current Events portal scraping (daily world news)
 *   3. BBC World News RSS feed (top headlines)
 *
 * Usage:
 *   GET world_events.php                    — today's events
 *   GET world_events.php?range=week         — this week's events
 *   GET world_events.php?range=today        — today only
 *   GET world_events.php?date=2026-02-08    — specific date
 *   GET world_events.php?limit=20           — max results
 *   GET world_events.php?debug=1            — include source debug info
 *
 * Response: JSON with "ok", "date", "events" array
 *   Each event: { title, description, category, date, source, url, importance }
 *   importance: "high" (everyone talking), "medium" (major news), "normal" (notable)
 *
 * PHP 5.2 compatible.
 */

header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
if (strtoupper($_SERVER['REQUEST_METHOD']) === 'OPTIONS') {
    exit;
}

// ============================================================
// PARAMETERS
// ============================================================

$range    = isset($_GET['range']) ? strtolower(trim($_GET['range'])) : 'today';
$date_str = isset($_GET['date']) ? trim($_GET['date']) : '';
$limit    = isset($_GET['limit']) ? (int)$_GET['limit'] : 30;
$debug    = isset($_GET['debug']) ? (int)$_GET['debug'] : 0;

if ($limit < 1) $limit = 1;
if ($limit > 100) $limit = 100;

// Determine date range
$today = ($date_str !== '') ? strtotime($date_str) : time();
if ($today === false) $today = time();

$date_start = strtotime('today', $today);
$date_end   = $date_start + 86400; // +1 day

if ($range === 'week') {
    // Show events from 1 day before to 6 days after
    $date_start = $date_start - 86400;
    $date_end   = $date_start + (8 * 86400);
} elseif ($range === '3days' || $range === 'upcoming') {
    $date_end = $date_start + (3 * 86400);
}

$today_str = date('Y-m-d', $today);
$today_month = (int)date('n', $today);
$today_day   = (int)date('j', $today);
$today_year  = (int)date('Y', $today);
$today_dow   = (int)date('w', $today); // 0=Sun, 6=Sat


// ============================================================
// SOURCE 1: CURATED MAJOR EVENTS CALENDAR
// ============================================================

$curated_events = _we_get_curated_events($today, $date_start, $date_end, $today_year);


// ============================================================
// SOURCE 2: WIKIPEDIA CURRENT EVENTS
// ============================================================

$wiki_events = _we_scrape_wikipedia_current($today_str);


// ============================================================
// SOURCE 3: BBC WORLD NEWS RSS
// ============================================================

$news_events = _we_scrape_bbc_rss();


// ============================================================
// MERGE + RESPOND
// ============================================================

$all_events = array();
foreach ($curated_events as $e) { $all_events[] = $e; }
foreach ($wiki_events as $e) { $all_events[] = $e; }
foreach ($news_events as $e) { $all_events[] = $e; }

// Sort: high importance first, then medium, then normal
usort($all_events, '_we_sort_events');

if (count($all_events) > $limit) {
    $all_events = array_slice($all_events, 0, $limit);
}

$response = array(
    'ok' => true,
    'date' => $today_str,
    'range' => $range,
    'events' => $all_events,
    'total' => count($all_events)
);

if ($debug) {
    $response['debug'] = array(
        'curated_count' => count($curated_events),
        'wiki_count' => count($wiki_events),
        'news_count' => count($news_events)
    );
}

echo json_encode($response);
exit;


// ============================================================
// CURATED EVENTS
// ============================================================

function _we_get_curated_events($today_ts, $range_start, $range_end, $year) {
    $events = array();

    // Build the full curated calendar for this year
    $calendar = _we_build_calendar($year);

    foreach ($calendar as $evt) {
        $evt_ts = strtotime($evt['date']);
        if ($evt_ts === false) continue;

        // Check if event falls in our date range
        if ($evt_ts >= $range_start && $evt_ts < $range_end) {
            $events[] = array(
                'title' => $evt['title'],
                'description' => $evt['description'],
                'category' => $evt['category'],
                'date' => $evt['date'],
                'source' => 'curated_calendar',
                'url' => isset($evt['url']) ? $evt['url'] : '',
                'importance' => $evt['importance']
            );
        }
    }

    return $events;
}

function _we_build_calendar($year) {
    $cal = array();

    // --- SPORTS ---

    // Super Bowl — first Sunday in February
    $feb1 = mktime(0, 0, 0, 2, 1, $year);
    $feb1_dow = (int)date('w', $feb1);
    $sb_day = ($feb1_dow === 0) ? 1 : (8 - $feb1_dow);
    // 2026 Super Bowl is Feb 8
    $cal[] = array(
        'title' => 'Super Bowl LX',
        'description' => 'The NFL championship game — the biggest single-day sporting event in the US. San Francisco 49ers vs Buffalo Bills at Levi\'s Stadium.',
        'category' => 'sports',
        'date' => $year . '-02-08',
        'importance' => 'high',
        'url' => 'https://www.nfl.com/super-bowl'
    );

    // NBA All-Star Game — mid February
    $cal[] = array(
        'title' => 'NBA All-Star Weekend',
        'description' => 'The NBA\'s annual showcase of the league\'s best players with slam dunk contest, 3-point contest, and the All-Star Game.',
        'category' => 'sports',
        'date' => $year . '-02-16',
        'importance' => 'medium',
        'url' => 'https://www.nba.com/allstar'
    );

    // March Madness — mid March to early April
    $cal[] = array(
        'title' => 'NCAA March Madness Begins',
        'description' => 'The NCAA Division I Men\'s Basketball Tournament kicks off — 68 teams compete in single-elimination for the national championship.',
        'category' => 'sports',
        'date' => $year . '-03-17',
        'importance' => 'high',
        'url' => 'https://www.ncaa.com/march-madness'
    );

    // Masters Tournament — second week of April
    $cal[] = array(
        'title' => 'The Masters Tournament',
        'description' => 'The first major golf championship of the year at Augusta National Golf Club.',
        'category' => 'sports',
        'date' => $year . '-04-10',
        'importance' => 'medium',
        'url' => 'https://www.masters.com'
    );

    // Kentucky Derby — first Saturday in May
    $may1 = mktime(0, 0, 0, 5, 1, $year);
    $may1_dow = (int)date('w', $may1);
    $derby_day = ($may1_dow <= 6) ? (7 - $may1_dow) : 1;
    if ($may1_dow === 0) $derby_day = 7;
    $cal[] = array(
        'title' => 'Kentucky Derby',
        'description' => 'The "most exciting two minutes in sports" — America\'s premier horse race at Churchill Downs.',
        'category' => 'sports',
        'date' => $year . '-05-' . sprintf('%02d', $derby_day),
        'importance' => 'medium',
        'url' => 'https://www.kentuckyderby.com'
    );

    // Stanley Cup Finals — June
    $cal[] = array(
        'title' => 'NHL Stanley Cup Finals',
        'description' => 'The championship series of the National Hockey League.',
        'category' => 'sports',
        'date' => $year . '-06-05',
        'importance' => 'high',
        'url' => 'https://www.nhl.com/stanley-cup-playoffs'
    );

    // NBA Finals — June
    $cal[] = array(
        'title' => 'NBA Finals',
        'description' => 'The championship series of the National Basketball Association.',
        'category' => 'sports',
        'date' => $year . '-06-05',
        'importance' => 'high',
        'url' => 'https://www.nba.com/playoffs'
    );

    // Wimbledon — late June / early July
    $cal[] = array(
        'title' => 'Wimbledon Championships',
        'description' => 'The oldest and most prestigious tennis tournament in the world, held at the All England Club in London.',
        'category' => 'sports',
        'date' => $year . '-06-30',
        'importance' => 'high',
        'url' => 'https://www.wimbledon.com'
    );

    // Olympics — check if this is an Olympic year
    if ($year % 4 === 2) {
        // Winter Olympics in even years not divisible by 4? Actually 2026 is Winter Olympics
        $cal[] = array(
            'title' => 'Winter Olympics — Milano Cortina 2026',
            'description' => 'The XXV Olympic Winter Games held in Milan and Cortina d\'Ampezzo, Italy.',
            'category' => 'sports',
            'date' => $year . '-02-06',
            'importance' => 'high',
            'url' => 'https://olympics.com/en/olympic-games/milano-cortina-2026'
        );
    }
    if ($year % 4 === 0) {
        // Summer Olympics
        $cal[] = array(
            'title' => 'Summer Olympics',
            'description' => 'The Olympic Summer Games.',
            'category' => 'sports',
            'date' => $year . '-07-26',
            'importance' => 'high',
            'url' => 'https://olympics.com'
        );
    }

    // FIFA World Cup 2026 — special case, held in US/Mexico/Canada
    if ($year === 2026) {
        $cal[] = array(
            'title' => 'FIFA World Cup 2026 Kicks Off',
            'description' => 'The first 48-team FIFA World Cup, co-hosted by USA, Mexico, and Canada. Matches across 16 cities in North America.',
            'category' => 'sports',
            'date' => '2026-06-11',
            'importance' => 'high',
            'url' => 'https://www.fifa.com/fifaplus/en/tournaments/mens/worldcup/canadamexicousa2026'
        );
        $cal[] = array(
            'title' => 'FIFA World Cup 2026 Final',
            'description' => 'The final match of the 2026 FIFA World Cup at MetLife Stadium, New Jersey.',
            'category' => 'sports',
            'date' => '2026-07-19',
            'importance' => 'high',
            'url' => 'https://www.fifa.com/fifaplus/en/tournaments/mens/worldcup/canadamexicousa2026'
        );
    }

    // World Series — late October
    $cal[] = array(
        'title' => 'MLB World Series',
        'description' => 'The championship series of Major League Baseball.',
        'category' => 'sports',
        'date' => $year . '-10-24',
        'importance' => 'high',
        'url' => 'https://www.mlb.com/postseason'
    );

    // --- AWARDS / ENTERTAINMENT ---

    // Grammy Awards — early February
    $cal[] = array(
        'title' => 'Grammy Awards',
        'description' => 'The Recording Academy\'s annual celebration of excellence in music across all genres.',
        'category' => 'entertainment',
        'date' => $year . '-02-02',
        'importance' => 'high',
        'url' => 'https://www.grammy.com'
    );

    // Oscar Awards — early March
    $cal[] = array(
        'title' => 'Academy Awards (Oscars)',
        'description' => 'The most prestigious film awards ceremony, honoring the best in cinema.',
        'category' => 'entertainment',
        'date' => $year . '-03-02',
        'importance' => 'high',
        'url' => 'https://www.oscars.org'
    );

    // Eurovision — May
    $cal[] = array(
        'title' => 'Eurovision Song Contest Grand Final',
        'description' => 'Europe\'s iconic international song competition watched by hundreds of millions worldwide.',
        'category' => 'entertainment',
        'date' => $year . '-05-17',
        'importance' => 'high',
        'url' => 'https://eurovision.tv'
    );

    // Met Gala — first Monday in May
    $cal[] = array(
        'title' => 'Met Gala',
        'description' => 'The Metropolitan Museum of Art\'s annual fundraising gala — fashion\'s biggest night.',
        'category' => 'entertainment',
        'date' => $year . '-05-05',
        'importance' => 'high',
        'url' => 'https://www.metmuseum.org'
    );

    // Coachella — mid April
    $cal[] = array(
        'title' => 'Coachella Valley Music and Arts Festival',
        'description' => 'One of the world\'s most famous music festivals, held in Indio, California.',
        'category' => 'entertainment',
        'date' => $year . '-04-11',
        'importance' => 'medium',
        'url' => 'https://www.coachella.com'
    );

    // Emmy Awards — September
    $cal[] = array(
        'title' => 'Primetime Emmy Awards',
        'description' => 'Television\'s biggest night, honoring the best in primetime TV.',
        'category' => 'entertainment',
        'date' => $year . '-09-21',
        'importance' => 'medium',
        'url' => 'https://www.emmys.com'
    );

    // Golden Globes — early January
    $cal[] = array(
        'title' => 'Golden Globe Awards',
        'description' => 'Awards honoring the best in film and television, often seen as an Oscar predictor.',
        'category' => 'entertainment',
        'date' => $year . '-01-05',
        'importance' => 'medium',
        'url' => 'https://www.goldenglobes.com'
    );

    // --- HOLIDAYS ---

    $cal[] = array(
        'title' => 'Valentine\'s Day',
        'description' => 'A celebration of love and romance observed worldwide.',
        'category' => 'holiday',
        'date' => $year . '-02-14',
        'importance' => 'high',
        'url' => ''
    );

    $cal[] = array(
        'title' => 'St. Patrick\'s Day',
        'description' => 'Irish cultural and religious celebration observed worldwide with parades, festivals, and wearing green.',
        'category' => 'holiday',
        'date' => $year . '-03-17',
        'importance' => 'medium',
        'url' => ''
    );

    // Earth Day
    $cal[] = array(
        'title' => 'Earth Day',
        'description' => 'Annual event supporting environmental protection, observed in over 190 countries.',
        'category' => 'holiday',
        'date' => $year . '-04-22',
        'importance' => 'medium',
        'url' => 'https://www.earthday.org'
    );

    // Mother's Day — second Sunday in May
    $may1_dow2 = (int)date('w', mktime(0, 0, 0, 5, 1, $year));
    $mothers_day = ($may1_dow2 === 0) ? 8 : (15 - $may1_dow2);
    $cal[] = array(
        'title' => 'Mother\'s Day',
        'description' => 'A day honoring mothers and motherhood, celebrated worldwide.',
        'category' => 'holiday',
        'date' => $year . '-05-' . sprintf('%02d', $mothers_day),
        'importance' => 'medium',
        'url' => ''
    );

    // Father's Day — third Sunday in June
    $jun1_dow = (int)date('w', mktime(0, 0, 0, 6, 1, $year));
    $fathers_day = ($jun1_dow === 0) ? 15 : (22 - $jun1_dow);
    $cal[] = array(
        'title' => 'Father\'s Day',
        'description' => 'A day celebrating fathers and fatherhood.',
        'category' => 'holiday',
        'date' => $year . '-06-' . sprintf('%02d', $fathers_day),
        'importance' => 'medium',
        'url' => ''
    );

    // Canada Day
    $cal[] = array(
        'title' => 'Canada Day',
        'description' => 'Canada\'s national day celebrating Confederation in 1867.',
        'category' => 'holiday',
        'date' => $year . '-07-01',
        'importance' => 'medium',
        'url' => ''
    );

    // US Independence Day
    $cal[] = array(
        'title' => 'US Independence Day (4th of July)',
        'description' => 'America\'s birthday — celebrating the Declaration of Independence with fireworks, parades, and cookouts.',
        'category' => 'holiday',
        'date' => $year . '-07-04',
        'importance' => 'high',
        'url' => ''
    );

    // Halloween
    $cal[] = array(
        'title' => 'Halloween',
        'description' => 'Costumes, trick-or-treating, haunted houses, and spooky celebrations worldwide.',
        'category' => 'holiday',
        'date' => $year . '-10-31',
        'importance' => 'high',
        'url' => ''
    );

    // US Thanksgiving — fourth Thursday in November
    $nov1_dow = (int)date('w', mktime(0, 0, 0, 11, 1, $year));
    $tgiving_day = ($nov1_dow <= 4) ? (26 - $nov1_dow) : (33 - $nov1_dow);
    $cal[] = array(
        'title' => 'US Thanksgiving',
        'description' => 'American holiday celebrating gratitude, family, and a big feast. Also the start of holiday shopping season.',
        'category' => 'holiday',
        'date' => $year . '-11-' . sprintf('%02d', $tgiving_day),
        'importance' => 'high',
        'url' => ''
    );

    // Black Friday — day after Thanksgiving
    $cal[] = array(
        'title' => 'Black Friday',
        'description' => 'The biggest shopping day of the year with massive sales and deals.',
        'category' => 'culture',
        'date' => $year . '-11-' . sprintf('%02d', $tgiving_day + 1),
        'importance' => 'high',
        'url' => ''
    );

    // Christmas
    $cal[] = array(
        'title' => 'Christmas Day',
        'description' => 'The world\'s most widely celebrated holiday, marking the birth of Jesus Christ.',
        'category' => 'holiday',
        'date' => $year . '-12-25',
        'importance' => 'high',
        'url' => ''
    );

    // New Year's Eve
    $cal[] = array(
        'title' => 'New Year\'s Eve',
        'description' => 'Celebrations worldwide welcoming the new year with fireworks, parties, and countdowns.',
        'category' => 'holiday',
        'date' => $year . '-12-31',
        'importance' => 'high',
        'url' => ''
    );

    // New Year's Day
    $cal[] = array(
        'title' => 'New Year\'s Day',
        'description' => 'The first day of the new year — parades, resolutions, and recovery.',
        'category' => 'holiday',
        'date' => $year . '-01-01',
        'importance' => 'high',
        'url' => ''
    );

    // --- TECH / CULTURE ---

    // CES — early January
    $cal[] = array(
        'title' => 'CES (Consumer Electronics Show)',
        'description' => 'The world\'s most influential tech event in Las Vegas, showcasing cutting-edge gadgets and innovations.',
        'category' => 'tech',
        'date' => $year . '-01-07',
        'importance' => 'medium',
        'url' => 'https://www.ces.tech'
    );

    // Apple WWDC — June
    $cal[] = array(
        'title' => 'Apple WWDC (Worldwide Developers Conference)',
        'description' => 'Apple\'s annual developer conference with major software and hardware announcements.',
        'category' => 'tech',
        'date' => $year . '-06-09',
        'importance' => 'medium',
        'url' => 'https://developer.apple.com/wwdc'
    );

    // E3 / Summer Game Fest — June
    $cal[] = array(
        'title' => 'Summer Game Fest',
        'description' => 'The biggest gaming showcase of the year with new game reveals and trailers.',
        'category' => 'tech',
        'date' => $year . '-06-07',
        'importance' => 'medium',
        'url' => 'https://www.summergamefest.com'
    );

    return $cal;
}


// ============================================================
// WIKIPEDIA CURRENT EVENTS
// ============================================================

function _we_scrape_wikipedia_current($date_str) {
    // Wikipedia Current Events portal: https://en.wikipedia.org/wiki/Portal:Current_events
    // Date-specific page format: Portal:Current_events/2026_February_8
    $parts = explode('-', $date_str);
    if (count($parts) !== 3) return array();

    $year = $parts[0];
    $month_name = date('F', mktime(0, 0, 0, (int)$parts[1], 1));
    $day = (int)$parts[2];

    $url = 'https://en.wikipedia.org/w/index.php?title=Portal:Current_events/' . $year . '_' . $month_name . '_' . $day . '&action=raw';

    $response = _we_http_get($url);
    if ($response === false || strlen($response) < 50) return array();

    $events = array();

    // Wikipedia current events use wikitext format:
    // * '''[[Topic]]''' — Description of event.
    // or just: * Description of event.
    $lines = explode("\n", $response);
    $current_category = 'world';

    foreach ($lines as $line) {
        $line = trim($line);

        // Category headers: ;Armed conflicts, ;Business, ;Disasters, etc.
        if (substr($line, 0, 1) === ';') {
            $cat = strtolower(trim(substr($line, 1)));
            $cat = preg_replace('/\\s+and\\s+/', '_', $cat);
            $cat = preg_replace('/[^a-z_]/', '', $cat);
            if ($cat !== '') $current_category = $cat;
            continue;
        }

        // Event lines start with *
        if (substr($line, 0, 1) !== '*') continue;
        $line = ltrim($line, '* ');
        if (strlen($line) < 10) continue;

        // Clean wikitext markup
        // Remove [[ ]] links, keeping display text
        $clean = preg_replace('/\\[\\[(?:[^|\\]]*\\|)?([^\\]]+)\\]\\]/', '$1', $line);
        // Remove ''' bold
        $clean = str_replace("'''", '', $clean);
        // Remove '' italic
        $clean = str_replace("''", '', $clean);
        // Remove {{ }} templates
        $clean = preg_replace('/\\{\\{[^}]*\\}\\}/', '', $clean);
        // Remove [http...] external links
        $clean = preg_replace('/\\[[a-z]+:\\/\\/[^\\s\\]]+(\\s[^\\]]+)?\\]/', '$1', $clean);
        $clean = trim($clean);

        if (strlen($clean) < 15) continue;

        // Extract a title (first sentence or bolded text)
        $title = $clean;
        if (strlen($title) > 100) {
            // Use first sentence as title
            $dot_pos = strpos($clean, '. ');
            if ($dot_pos !== false && $dot_pos < 120) {
                $title = substr($clean, 0, $dot_pos + 1);
            } else {
                $title = substr($clean, 0, 100) . '...';
            }
        }

        $importance = 'normal';
        // Boost importance for certain categories
        if ($current_category === 'armed_conflicts' || $current_category === 'disasters') {
            $importance = 'medium';
        }
        if ($current_category === 'international_relations' || $current_category === 'politics_elections') {
            $importance = 'medium';
        }

        $events[] = array(
            'title' => $title,
            'description' => $clean,
            'category' => $current_category,
            'date' => $date_str,
            'source' => 'wikipedia',
            'url' => 'https://en.wikipedia.org/wiki/Portal:Current_events',
            'importance' => $importance
        );
    }

    return $events;
}


// ============================================================
// BBC WORLD NEWS RSS
// ============================================================

function _we_scrape_bbc_rss() {
    $url = 'https://feeds.bbci.co.uk/news/world/rss.xml';
    $response = _we_http_get($url);
    if ($response === false) return array();

    $events = array();

    // Parse RSS XML
    // Extract <item><title>...</title><description>...</description><link>...</link></item>
    preg_match_all('/<item>(.*?)<\\/item>/s', $response, $items);
    if (!isset($items[1])) return array();

    $count = 0;
    foreach ($items[1] as $item_xml) {
        if ($count >= 10) break; // Limit to 10 top news items

        $title = '';
        if (preg_match('/<title>(?:<\\!\\[CDATA\\[)?(.+?)(?:\\]\\]>)?<\\/title>/', $item_xml, $tm)) {
            $title = html_entity_decode(trim($tm[1]), ENT_QUOTES, 'UTF-8');
        }

        $desc = '';
        if (preg_match('/<description>(?:<\\!\\[CDATA\\[)?(.+?)(?:\\]\\]>)?<\\/description>/s', $item_xml, $dm)) {
            $desc = html_entity_decode(strip_tags(trim($dm[1])), ENT_QUOTES, 'UTF-8');
        }

        $link = '';
        if (preg_match('/<link>(.+?)<\\/link>/', $item_xml, $lm)) {
            $link = trim($lm[1]);
        }
        // BBC sometimes uses guid
        if ($link === '' && preg_match('/<guid[^>]*>(.+?)<\\/guid>/', $item_xml, $gm)) {
            $link = trim($gm[1]);
        }

        $pub_date = '';
        if (preg_match('/<pubDate>(.+?)<\\/pubDate>/', $item_xml, $pm)) {
            $pub_date = date('Y-m-d', strtotime(trim($pm[1])));
        }

        if ($title === '') continue;

        $events[] = array(
            'title' => $title,
            'description' => ($desc !== '') ? $desc : $title,
            'category' => 'world_news',
            'date' => ($pub_date !== '') ? $pub_date : date('Y-m-d'),
            'source' => 'bbc_news',
            'url' => $link,
            'importance' => ($count < 3) ? 'medium' : 'normal'
        );
        $count++;
    }

    return $events;
}


// ============================================================
// SORT + HELPERS
// ============================================================

function _we_sort_events($a, $b) {
    $order = array('high' => 0, 'medium' => 1, 'normal' => 2);
    $a_imp = isset($order[$a['importance']]) ? $order[$a['importance']] : 2;
    $b_imp = isset($order[$b['importance']]) ? $order[$b['importance']] : 2;
    if ($a_imp !== $b_imp) {
        return ($a_imp < $b_imp) ? -1 : 1;
    }
    // Same importance — sort by source priority (curated > wiki > news)
    $src_order = array('curated_calendar' => 0, 'wikipedia' => 1, 'bbc_news' => 2);
    $a_src = isset($src_order[$a['source']]) ? $src_order[$a['source']] : 3;
    $b_src = isset($src_order[$b['source']]) ? $src_order[$b['source']] : 3;
    if ($a_src !== $b_src) {
        return ($a_src < $b_src) ? -1 : 1;
    }
    return 0;
}

function _we_http_get($url) {
    if (function_exists('curl_init')) {
        $ch = curl_init($url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_TIMEOUT, 10);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'User-Agent: FindTorontoEvents-WorldEvents/1.0',
            'Accept: text/html,application/xhtml+xml,application/xml,text/xml'
        ));
        $response = curl_exec($ch);
        $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        if ($response !== false && $code >= 200 && $code < 400) {
            return $response;
        }
    }

    $ctx = stream_context_create(array(
        'http' => array(
            'method' => 'GET',
            'timeout' => 10,
            'header' => "User-Agent: FindTorontoEvents-WorldEvents/1.0\r\n"
        )
    ));
    $response = @file_get_contents($url, false, $ctx);
    return ($response !== false) ? $response : false;
}
