<?php
/**
 * Toronto Event Resources API
 * 
 * Returns structured resources data with optional category filtering
 * and today's events from the resource sources.
 * 
 * GET: https://findtorontoevents.ca/api/events/resources.php
 * GET: https://findtorontoevents.ca/api/events/resources.php?category=music
 * GET: https://findtorontoevents.ca/api/events/resources.php?today=1
 * GET: https://findtorontoevents.ca/api/events/resources.php?category=arts&today=1
 *
 * PHP 5.2 compatible.
 */
error_reporting(0);
ini_set('display_errors', '0');
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Cache-Control: public, max-age=3600');

$json_path = dirname(dirname(dirname(__FILE__))) . '/resources/resources.json';
$json_raw = @file_get_contents($json_path);

if (!$json_raw) {
    echo json_encode(array('ok' => false, 'error' => 'resources_file_not_found'));
    exit;
}

$data = json_decode($json_raw, true);
if (!$data || !isset($data['categories'])) {
    echo json_encode(array('ok' => false, 'error' => 'invalid_json'));
    exit;
}

$category_filter = isset($_GET['category']) ? strtolower(trim($_GET['category'])) : '';
$show_today = isset($_GET['today']) ? (intval($_GET['today']) === 1) : false;

$today_str = date('M j');
$today_full = date('F j');
$today_day = strtolower(date('l'));
$today_month = date('M');
$today_date_num = intval(date('j'));

$categories = $data['categories'];
$filtered_categories = array();

foreach ($categories as $cat) {
    if ($category_filter !== '' && strtolower($cat['id']) !== $category_filter) {
        continue;
    }
    $filtered_categories[] = $cat;
}

$result = array(
    'ok' => true,
    'total_sources' => $data['total_sources'],
    'last_updated' => $data['last_updated'],
    'page_url' => 'https://findtorontoevents.ca/resources/resources.html',
    'categories' => $filtered_categories
);

if ($show_today) {
    $todays_events = array();

    foreach ($filtered_categories as $cat) {
        foreach ($cat['sources'] as $src) {
            if (!isset($src['events'])) continue;
            foreach ($src['events'] as $evt) {
                $d = isset($evt['date']) ? $evt['date'] : '';
                if (_is_today_match($d, $today_str, $today_full, $today_day, $today_date_num, $today_month)) {
                    $todays_events[] = array(
                        'title' => $evt['title'],
                        'date' => $d,
                        'price' => isset($evt['price']) ? $evt['price'] : '',
                        'source' => $src['name'],
                        'source_url' => $src['url'],
                        'category' => $cat['name'],
                        'category_id' => $cat['id'],
                        'category_emoji' => $cat['emoji']
                    );
                }
            }
        }
    }

    $result['todays_events'] = $todays_events;
    $result['todays_count'] = count($todays_events);
    $result['today_date'] = date('l, F j, Y');
}

echo json_encode($result);
exit;

/**
 * Check if an event date string matches today.
 * Handles formats like "Feb 15", "Daily", "Ongoing", "Weekly", etc.
 */
function _is_today_match($date_str, $today_str, $today_full, $today_day, $today_date_num, $today_month) {
    $d = strtolower(trim($date_str));
    if ($d === '') return false;

    if ($d === strtolower($today_str)) return true;
    if ($d === strtolower($today_full)) return true;

    if ($d === 'daily' || $d === 'ongoing' || $d === '24/7') return true;

    if ($d === 'weekly') return true;

    if ($d === 'weekends' && ($today_day === 'saturday' || $today_day === 'sunday')) return true;

    if (strpos($d, 'year-round') !== false) return true;
    if (strpos($d, 'daily updates') !== false) return true;
    if (strpos($d, 'regular') !== false) return true;

    if (strpos($d, 'thu-sun') !== false) {
        $dow = date('w');
        if ($dow >= 4 || $dow === 0) return true;
    }
    if (strpos($d, 'fri') !== false && $today_day === 'friday') return true;
    if (strpos($d, 'wed') !== false && $today_day === 'wednesday') return true;
    if (strpos($d, 'every thu') !== false && $today_day === 'thursday') return true;

    if (strpos($d, strtolower($today_month)) !== false) {
        if (preg_match('/(\d{1,2})\s*-\s*(\d{1,2})/', $d, $m)) {
            $start = intval($m[1]);
            $end = intval($m[2]);
            if ($today_date_num >= $start && $today_date_num <= $end) return true;
        }
        if (strpos($d, strtolower($today_str)) !== false) return true;
        if (strpos($d, strtolower($today_month)) !== false && strpos($d, '-') !== false) {
            return true;
        }
    }

    $month_abbrev = strtolower(substr($date_str, 0, 3));
    if ($month_abbrev === strtolower($today_month)) {
        $number_match = array();
        if (preg_match('/\b' . $today_date_num . '\b/', $date_str, $number_match)) {
            return true;
        }
    }

    return false;
}
