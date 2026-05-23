<?php
/**
 * edge_finder.php — Edge-finder algorithm win-rate stats for the Investment Hub.
 * PHP 5.2 compatible.
 *
 * Actions:
 *   ?action=edge_stats   — Per-algorithm win rates (cached 5 min)
 */

header('Content-Type: application/json');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') { exit; }

require_once dirname(__FILE__) . '/db_connect.php';

$action    = isset($_GET['action']) ? $_GET['action'] : 'edge_stats';
$CACHE_DIR = dirname(__FILE__) . '/cache/';
if (!is_dir($CACHE_DIR)) { @mkdir($CACHE_DIR, 0755, true); }

function _ef_cache_get($key, $ttl) {
    global $CACHE_DIR;
    $f = $CACHE_DIR . 'ef_' . md5($key) . '.json';
    if (file_exists($f) && (time() - filemtime($f)) < $ttl) {
        $d = @file_get_contents($f);
        if ($d !== false) return json_decode($d, true);
    }
    return false;
}
function _ef_cache_set($key, $data) {
    global $CACHE_DIR;
    $f = $CACHE_DIR . 'ef_' . md5($key) . '.json';
    @file_put_contents($f, json_encode($data));
}

// ── edge_stats: per-algorithm closed-pick win rates ──
if ($action === 'edge_stats') {
    $cached = _ef_cache_get('edge_stats', 300);
    if ($cached) { echo json_encode($cached); exit; }

    $algorithms = array();

    // Query gm_unified_picks grouped by algorithm_name (closed picks only)
    $r = $conn->query("
        SELECT
            algorithm_name,
            COUNT(*)                                                      AS total,
            SUM(CASE WHEN status = 'tp_hit' THEN 1 ELSE 0 END)          AS wins,
            SUM(CASE WHEN status = 'sl_hit' THEN 1 ELSE 0 END)          AS losses,
            SUM(CASE WHEN status IN ('max_hold','expired') THEN 1 ELSE 0 END) AS expired,
            AVG(final_return_pct)                                         AS avg_return,
            MAX(pick_date)                                                AS last_pick
        FROM gm_unified_picks
        WHERE status != 'open'
          AND algorithm_name != ''
        GROUP BY algorithm_name
        HAVING total >= 5
        ORDER BY wins / total DESC, total DESC
        LIMIT 50
    ");

    if ($r) {
        while ($row = $r->fetch_assoc()) {
            $total    = (int)$row['total'];
            $wins     = (int)$row['wins'];
            $win_rate = $total > 0 ? round($wins / $total, 4) : 0;
            $algorithms[] = array(
                'name'       => $row['algorithm_name'],
                'win_rate'   => $win_rate,
                'trade_count'=> $total,
                'wins'       => $wins,
                'losses'     => (int)$row['losses'],
                'avg_return' => round((float)$row['avg_return'], 2),
                'last_pick'  => $row['last_pick'],
                'edge'       => $win_rate >= 0.55,
            );
        }
    }

    // Fallback: if gm_unified_picks is empty, try lm_opportunities (edge dashboard)
    if (empty($algorithms)) {
        $r2 = $conn->query("
            SELECT
                algorithm_tag                                              AS algorithm_name,
                COUNT(*)                                                   AS total,
                SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END)          AS wins,
                SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END)         AS losses,
                AVG(return_pct)                                            AS avg_return,
                MAX(created_at)                                            AS last_pick
            FROM lm_opportunities
            WHERE outcome IS NOT NULL AND algorithm_tag != ''
            GROUP BY algorithm_tag
            HAVING total >= 5
            ORDER BY wins / total DESC
            LIMIT 30
        ");
        if ($r2) {
            while ($row = $r2->fetch_assoc()) {
                $total    = (int)$row['total'];
                $wins     = (int)$row['wins'];
                $win_rate = $total > 0 ? round($wins / $total, 4) : 0;
                $algorithms[] = array(
                    'name'       => $row['algorithm_name'],
                    'win_rate'   => $win_rate,
                    'trade_count'=> $total,
                    'wins'       => $wins,
                    'losses'     => (int)$row['losses'],
                    'avg_return' => round((float)$row['avg_return'], 2),
                    'last_pick'  => $row['last_pick'],
                    'edge'       => $win_rate >= 0.55,
                );
            }
        }
    }

    $edge_count = 0;
    foreach ($algorithms as $a) { if ($a['edge']) $edge_count++; }

    $result = array(
        'algorithms'  => $algorithms,
        'edge_count'  => $edge_count,
        'total_algos' => count($algorithms),
        'generated_at'=> date('Y-m-d H:i:s'),
    );

    _ef_cache_set('edge_stats', $result);
    echo json_encode($result);
    exit;
}

echo json_encode(array('error' => 'Unknown action'));
