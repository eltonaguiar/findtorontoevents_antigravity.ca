<?php
/**
 * world_events.php — World Events API (FREE, no API keys)
 *
 * Returns major world events happening today/this week that "everyone is talking about."
 * Combines 4 sources:
 *   1. Curated calendar of major annual events (Super Bowl, Oscars, holidays, etc.)
 *   2. Wikipedia Current Events portal scraping (daily world news)
 *   3. BBC World News RSS feed (top headlines)
 *   4. Dexerto.com scraping (streamers, gaming, esports, TV/movies)
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

// Force Toronto/EST timezone — this site is Toronto-based
date_default_timezone_set('America/Toronto');

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

// For curated events, use a wider "buzz window" so major events still show
// the day after (e.g. Super Bowl on Feb 8 should still appear on Feb 9).
// High-importance: ±2 days buzz window; medium: ±1 day.
$curated_start = $date_start - (2 * 86400);  // 2 days before
$curated_end   = $date_end   + (2 * 86400);  // 2 days after
$curated_events = _we_get_curated_events($today, $curated_start, $curated_end, $today_year, $date_start, $date_end);


// ============================================================
// SOURCE 2: WIKIPEDIA CURRENT EVENTS
// ============================================================

$wiki_events = _we_scrape_wikipedia_current($today_str);


// ============================================================
// SOURCE 3: BBC WORLD NEWS RSS
// ============================================================

$news_events = _we_scrape_bbc_rss();


// ============================================================
// SOURCE 4: DEXERTO (Streamers, Gaming, Esports, TV/Movies)
// ============================================================

$dexerto_events = _we_scrape_dexerto();


// ============================================================
// MERGE + RESPOND
// ============================================================

$all_events = array();
foreach ($curated_events as $e) { $all_events[] = $e; }
foreach ($wiki_events as $e) { $all_events[] = $e; }
foreach ($news_events as $e) { $all_events[] = $e; }
foreach ($dexerto_events as $e) { $all_events[] = $e; }

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
        'news_count' => count($news_events),
        'dexerto_count' => count($dexerto_events)
    );
}

echo json_encode($response);
exit;


// ============================================================
// CURATED EVENTS
// ============================================================

function _we_get_curated_events($today_ts, $buzz_start, $buzz_end, $year, $strict_start, $strict_end) {
    $events = array();

    // Build the full curated calendar for this year
    $calendar = _we_build_calendar($year);

    foreach ($calendar as $evt) {
        $evt_ts = strtotime($evt['date']);
        if ($evt_ts === false) continue;

        // Events within the strict date range always show
        $in_strict = ($evt_ts >= $strict_start && $evt_ts < $strict_end);

        // Events within the wider buzz window show only if high/medium importance
        $in_buzz = ($evt_ts >= $buzz_start && $evt_ts < $buzz_end);

        if ($in_strict || ($in_buzz && ($evt['importance'] === 'high' || $evt['importance'] === 'medium'))) {
            // If it's outside strict range, add a "buzz" note to description
            $desc = $evt['description'];
            if (!$in_strict && $in_buzz) {
                $days_diff = round(($strict_start - $evt_ts) / 86400);
                if ($days_diff > 0) {
                    $desc = $desc . ' (was ' . $days_diff . ' day' . ($days_diff > 1 ? 's' : '') . ' ago — still trending)';
                } elseif ($days_diff < 0) {
                    $days_until = abs($days_diff);
                    $desc = $desc . ' (in ' . $days_until . ' day' . ($days_until > 1 ? 's' : '') . ')';
                }
            }

            $events[] = array(
                'title' => $evt['title'],
                'description' => $desc,
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
// ENTERTAINMENT NEWS — Gaming, Streaming, Esports, TV/Movies
// (via Google News RSS — aggregates Dexerto, IGN, Kotaku, etc.)
// ============================================================

function _we_scrape_dexerto() {
    $all = array();

    // Use Google News RSS search for each topic — returns fresh articles from many sources
    $feeds = array(
        array(
            'url' => 'https://news.google.com/rss/search?q=esports+OR+competitive+gaming+OR+tournament&hl=en-US&gl=US&ceid=US:en',
            'cat' => 'esports',
            'limit' => 4
        ),
        array(
            'url' => 'https://news.google.com/rss/search?q=twitch+streamer+OR+youtube+creator+OR+kick+streaming&hl=en-US&gl=US&ceid=US:en',
            'cat' => 'streaming',
            'limit' => 4
        ),
        array(
            'url' => 'https://news.google.com/rss/search?q=new+movie+OR+tv+show+premiere+OR+anime+release+OR+netflix+series&hl=en-US&gl=US&ceid=US:en',
            'cat' => 'tv_movies',
            'limit' => 4
        ),
        array(
            'url' => 'https://news.google.com/rss/search?q=video+game+news+OR+gaming+announcement+OR+playstation+OR+xbox+OR+nintendo&hl=en-US&gl=US&ceid=US:en',
            'cat' => 'gaming',
            'limit' => 4
        )
    );

    $seen_titles = array();

    for ($f = 0; $f < count($feeds); $f++) {
        $feed = $feeds[$f];
        $xml = _we_http_get($feed['url']);
        if ($xml === false || strlen($xml) < 100) continue;

        $items = _we_parse_google_news_rss($xml);
        $count = 0;
        for ($i = 0; $i < count($items); $i++) {
            if ($count >= $feed['limit']) break;
            $item = $items[$i];

            // Skip duplicates by title similarity
            $key = strtolower(substr($item['title'], 0, 50));
            if (isset($seen_titles[$key])) continue;
            $seen_titles[$key] = true;

            // Refine category based on title keywords
            $cat = _we_detect_entertainment_category($item['title'], $feed['cat']);

            // First 2 per feed are medium, rest normal
            $imp = ($count < 2) ? 'medium' : 'normal';

            $all[] = array(
                'title' => $item['title'],
                'description' => ($item['description'] !== '') ? $item['description'] : $item['title'],
                'category' => $cat,
                'date' => ($item['date'] !== '') ? $item['date'] : date('Y-m-d'),
                'source' => 'dexerto',
                'url' => $item['url'],
                'importance' => $imp
            );
            $count++;
        }
    }

    return $all;
}

/**
 * Parse Google News RSS XML for article items.
 * Returns array of: title, url, description, date, source_name
 */
function _we_parse_google_news_rss($xml) {
    $items = array();

    preg_match_all('/<item>(.*?)<\\/item>/s', $xml, $matches);
    if (!isset($matches[1])) return array();

    for ($i = 0; $i < count($matches[1]); $i++) {
        $item_xml = $matches[1][$i];

        $title = '';
        if (preg_match('/<title>(?:<\\!\\[CDATA\\[)?(.+?)(?:\\]\\]>)?<\\/title>/', $item_xml, $tm)) {
            $title = html_entity_decode(trim($tm[1]), ENT_QUOTES, 'UTF-8');
            // Google News appends " - Source Name", remove it for cleaner titles
            $dash_pos = strrpos($title, ' - ');
            if ($dash_pos !== false && $dash_pos > 20) {
                $title = trim(substr($title, 0, $dash_pos));
            }
        }

        $url = '';
        if (preg_match('/<link>(.+?)<\\/link>/', $item_xml, $lm)) {
            $url = trim($lm[1]);
        }

        $desc = '';
        if (preg_match('/<description>(?:<\\!\\[CDATA\\[)?(.+?)(?:\\]\\]>)?<\\/description>/s', $item_xml, $dm)) {
            $desc = html_entity_decode(strip_tags(trim($dm[1])), ENT_QUOTES, 'UTF-8');
            if (strlen($desc) > 200) $desc = substr($desc, 0, 200) . '...';
        }

        $pub_date = '';
        if (preg_match('/<pubDate>(.+?)<\\/pubDate>/', $item_xml, $pm)) {
            $ts = strtotime(trim($pm[1]));
            if ($ts !== false) $pub_date = date('Y-m-d', $ts);
        }

        if ($title === '' || strlen($title) < 15) continue;

        $items[] = array(
            'title' => $title,
            'url' => $url,
            'description' => $desc,
            'date' => $pub_date
        );
    }

    return $items;
}

/**
 * Detect specific sub-category from article title keywords.
 */
function _we_detect_entertainment_category($title, $default_cat) {
    $t = strtolower($title);

    // Streaming platforms / creators
    if (preg_match('/\\btwitch\\b|\\bstreamer|\\byoutub|\\bkick\\b|\\btiktok\\b|\\bcreator\\b/i', $t)) return 'streaming';

    // Esports / competitive
    if (preg_match('/\\besport|\\btournament\\b|\\bchampion|\\bcompetitive|\\bleague\\b|\\bmajor\\b|\\bvalorant\\b|\\bcounter.?strike|\\boverwatch\\b/i', $t)) return 'esports';

    // TV & Movies
    if (preg_match('/\\bmovie\\b|\\bfilm\\b|\\bnetflix\\b|\\bdisney|\\bmarvel\\b|\\btrailer\\b|\\banime\\b|\\btv show|\\bseason\\b|\\bseries\\b|\\bpremiere/i', $t)) return 'tv_movies';

    // Gaming
    if (preg_match('/\\bgame\\b|\\bgaming\\b|\\bplaystation\\b|\\bxbox\\b|\\bnintendo\\b|\\bfortnite\\b|\\bminecraft\\b|\\bgta\\b|\\bconsole\\b/i', $t)) return 'gaming';

    return $default_cat;
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
    // Same importance — sort by source priority (curated > wiki > dexerto > news)
    $src_order = array('curated_calendar' => 0, 'wikipedia' => 1, 'dexerto' => 2, 'bbc_news' => 3);
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
