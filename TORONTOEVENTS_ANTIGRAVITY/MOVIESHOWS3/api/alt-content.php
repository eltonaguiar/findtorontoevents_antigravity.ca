<?php
/**
 * Alt Content API - Fetch alternative trailers and descriptions from TMDB
 * 
 * Query params:
 *   ?tmdb_id=12345&type=movie   (preferred - direct TMDB ID lookup)
 *   OR
 *   ?title=Movie+Name&year=2025&type=movie  (fallback - search by title)
 */
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');

$TMDB_API_KEY = 'b84ff7bfe35ffad8779b77bcbbda317f';
$TMDB_READ_TOKEN = 'eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiODRmZjdiZmUzNWZmYWQ4Nzc5Yjc3YmNiYmRhMzE3ZiIsIm5iZiI6MTU4NTg2ODk2NC41Mzc5OTk5LCJzdWIiOiI1ZTg2NzBhNGE1NzQzZDAwMTEwZmU3MWUiLCJzY29wZXMiOlsiYXBpX3JlYWQiXSwidmVyc2lvbiI6MX0.zKkPzhHNhnlghJQeJJz2GddR8NEI_TzXAUgU96Ky_Q4';

$tmdbId = isset($_GET['tmdb_id']) ? (int)$_GET['tmdb_id'] : 0;
$title = isset($_GET['title']) ? trim($_GET['title']) : '';
$year = isset($_GET['year']) ? (int)$_GET['year'] : 0;
$type = isset($_GET['type']) ? $_GET['type'] : 'movie';
if ($type !== 'tv') $type = 'movie';

$headers = array(
    'Authorization: Bearer ' . $TMDB_READ_TOKEN,
    'Accept: application/json'
);

// If no tmdb_id, search by title to find it
if ($tmdbId <= 0 && $title !== '') {
    $searchUrl = "https://api.themoviedb.org/3/search/" . $type . "?api_key=" . $TMDB_API_KEY . "&query=" . urlencode($title) . "&page=1";
    if ($year > 0) {
        $yearParam = ($type === 'tv') ? 'first_air_date_year' : 'primary_release_year';
        $searchUrl .= '&' . $yearParam . '=' . $year;
    }

    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $searchUrl);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    $searchResp = curl_exec($ch);
    curl_close($ch);

    if ($searchResp) {
        $searchData = json_decode($searchResp, true);
        if (isset($searchData['results']) && count($searchData['results']) > 0) {
            $tmdbId = (int)$searchData['results'][0]['id'];
        }
    }
}

if ($tmdbId <= 0) {
    echo json_encode(array('success' => false, 'error' => 'Could not find movie on TMDB'));
    exit;
}

// Fetch videos (trailers, teasers, clips, featurettes)
$videoUrl = "https://api.themoviedb.org/3/" . $type . "/" . $tmdbId . "/videos?api_key=" . $TMDB_API_KEY;

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $videoUrl);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
$videoResp = curl_exec($ch);
curl_close($ch);

$videos = array();
if ($videoResp) {
    $videoData = json_decode($videoResp, true);
    if (isset($videoData['results'])) {
        foreach ($videoData['results'] as $vid) {
            if (!isset($vid['site']) || $vid['site'] !== 'YouTube') continue;
            $videos[] = array(
                'key' => $vid['key'],
                'name' => isset($vid['name']) ? $vid['name'] : 'Untitled',
                'type' => isset($vid['type']) ? $vid['type'] : 'Unknown',
                'official' => isset($vid['official']) ? (bool)$vid['official'] : false,
                'published' => isset($vid['published_at']) ? $vid['published_at'] : ''
            );
        }
    }
}

// Sort: Official Trailers first, then Teasers, then Clips, then others
function alt_video_sort_score($v) {
    $score = 0;
    if ($v['official']) $score += 100;
    $t = strtolower($v['type']);
    if ($t === 'trailer') $score += 50;
    elseif ($t === 'teaser') $score += 40;
    elseif ($t === 'clip') $score += 30;
    elseif ($t === 'featurette') $score += 20;
    elseif ($t === 'behind the scenes') $score += 10;
    return $score;
}

// Manual sort (no closures for PHP 5.2)
for ($i = 0; $i < count($videos); $i++) {
    for ($j = $i + 1; $j < count($videos); $j++) {
        if (alt_video_sort_score($videos[$j]) > alt_video_sort_score($videos[$i])) {
            $tmp = $videos[$i];
            $videos[$i] = $videos[$j];
            $videos[$j] = $tmp;
        }
    }
}

// Fetch movie/show details for alternative description
$detailUrl = "https://api.themoviedb.org/3/" . $type . "/" . $tmdbId . "?api_key=" . $TMDB_API_KEY;

$ch = curl_init();
curl_setopt($ch, CURLOPT_URL, $detailUrl);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_TIMEOUT, 10);
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
$detailResp = curl_exec($ch);
curl_close($ch);

$altDescription = '';
$tagline = '';
if ($detailResp) {
    $detailData = json_decode($detailResp, true);
    if (isset($detailData['overview'])) {
        $altDescription = $detailData['overview'];
    }
    if (isset($detailData['tagline'])) {
        $tagline = $detailData['tagline'];
    }
}

echo json_encode(array(
    'success' => true,
    'tmdb_id' => $tmdbId,
    'videos' => $videos,
    'video_count' => count($videos),
    'alt_description' => $altDescription,
    'tagline' => $tagline
));
?>
