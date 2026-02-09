<?php
/**
 * DayTrades Miracle Claude — Picks API
 * List, filter, and query miracle picks.
 * PHP 5.2 compatible.
 *
 * Usage:
 *   GET .../picks2.php                            — today's picks
 *   GET .../picks2.php?date=2026-02-09            — picks for specific date
 *   GET .../picks2.php?strategy=Gap+Up+Momentum   — filter by strategy
 *   GET .../picks2.php?ticker=NVDA                — filter by ticker
 *   GET .../picks2.php?outcome=winner              — filter by outcome (pending,winner,loser,expired)
 *   GET .../picks2.php?confidence=high             — filter by confidence
 *   GET .../picks2.php?cdr_only=1                  — CDR tickers only
 *   GET .../picks2.php?days=7                      — last N days
 *   GET .../picks2.php?limit=50                    — max results
 *   GET .../picks2.php?sort=score|risk_reward|net_profit  — sort field
 */
require_once dirname(__FILE__) . '/db_connect2.php';

$date       = isset($_GET['date']) ? trim($_GET['date']) : '';
$strategy   = isset($_GET['strategy']) ? trim($_GET['strategy']) : '';
$ticker     = isset($_GET['ticker']) ? strtoupper(trim($_GET['ticker'])) : '';
$outcome    = isset($_GET['outcome']) ? trim($_GET['outcome']) : '';
$confidence = isset($_GET['confidence']) ? trim($_GET['confidence']) : '';
$cdr_only   = isset($_GET['cdr_only']) ? (int)$_GET['cdr_only'] : 0;
$days       = isset($_GET['days']) ? (int)$_GET['days'] : 0;
$limit      = isset($_GET['limit']) ? (int)$_GET['limit'] : 100;
$sort       = isset($_GET['sort']) ? trim($_GET['sort']) : 'score';

if ($limit < 1 || $limit > 500) $limit = 100;

$where = array();
$params = array();

if ($date !== '') {
    $where[] = "scan_date = '" . $conn->real_escape_string($date) . "'";
} elseif ($days > 0) {
    $where[] = "scan_date >= DATE_SUB(CURDATE(), INTERVAL $days DAY)";
} else {
    $where[] = "scan_date = CURDATE()";
}

if ($strategy !== '') {
    $where[] = "strategy_name = '" . $conn->real_escape_string($strategy) . "'";
}
if ($ticker !== '') {
    $where[] = "ticker = '" . $conn->real_escape_string($ticker) . "'";
}
if ($outcome !== '') {
    $where[] = "outcome = '" . $conn->real_escape_string($outcome) . "'";
}
if ($confidence !== '') {
    $where[] = "confidence = '" . $conn->real_escape_string($confidence) . "'";
}
if ($cdr_only) {
    $where[] = "is_cdr = 1";
}

$where_sql = count($where) > 0 ? 'WHERE ' . implode(' AND ', $where) : '';

// Sort
$valid_sorts = array('score', 'risk_reward_ratio', 'net_profit_if_tp', 'take_profit_pct', 'scan_date', 'ticker');
$found_sort = false;
foreach ($valid_sorts as $vs) { if ($vs === $sort) { $found_sort = true; break; } }
if (!$found_sort) $sort = 'score';
$order_dir = ($sort === 'ticker' || $sort === 'scan_date') ? 'ASC' : 'DESC';

$sql = "SELECT * FROM miracle_picks2 $where_sql ORDER BY $sort $order_dir, score DESC LIMIT $limit";
$res = $conn->query($sql);

$picks = array();
if ($res) {
    while ($row = $res->fetch_assoc()) {
        $row['signals_json'] = json_decode($row['signals_json'], true);
        $picks[] = $row;
    }
}

// Summary stats
$total = count($picks);
$winners = 0;
$losers = 0;
$pending = 0;
$avg_score = 0;
$cdr_count = 0;
foreach ($picks as $p) {
    $avg_score += (int)$p['score'];
    if ($p['outcome'] === 'winner') $winners++;
    elseif ($p['outcome'] === 'loser') $losers++;
    else $pending++;
    if ($p['is_cdr']) $cdr_count++;
}
$avg_score = $total > 0 ? round($avg_score / $total, 1) : 0;

echo json_encode(array(
    'ok'       => true,
    'total'    => $total,
    'summary'  => array(
        'winners'   => $winners,
        'losers'    => $losers,
        'pending'   => $pending,
        'avg_score' => $avg_score,
        'cdr_count' => $cdr_count
    ),
    'picks'    => $picks
));

$conn->close();
?>
