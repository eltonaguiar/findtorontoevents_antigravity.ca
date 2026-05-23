<?php
require_once dirname(__FILE__) . '/db_connect.php';
$r = array('ok' => true);

// Get first pick
$pr = $conn->query("SELECT symbol, pick_date, entry_nav FROM mf2_fund_picks WHERE entry_nav > 0 ORDER BY id LIMIT 1");
if (!$pr || $pr->num_rows === 0) {
    $r['error'] = 'No picks found';
    echo json_encode($r);
    exit;
}
$pick = $pr->fetch_assoc();
$r['pick'] = $pick;

$sym = $conn->real_escape_string($pick['symbol']);
$pd = $conn->real_escape_string($pick['pick_date']);

// Query NAV data
$sql = "SELECT nav_date, nav FROM mf2_nav_history WHERE symbol='$sym' AND nav_date >= '$pd' ORDER BY nav_date ASC LIMIT 30";
$r['sql'] = $sql;
$nr = $conn->query($sql);

if (!$nr) {
    $r['error'] = 'Query failed: ' . $conn->error;
} else {
    $r['nav_count'] = $nr->num_rows;
    $navs = array();
    while ($row = $nr->fetch_assoc()) {
        $navs[] = $row;
    }
    $r['navs'] = $navs;
}

// Also count total NAV records for this symbol
$cr = $conn->query("SELECT COUNT(*) as c FROM mf2_nav_history WHERE symbol='$sym'");
if ($cr) { $row = $cr->fetch_assoc(); $r['total_nav_for_symbol'] = (int)$row['c']; }

// Try a simulated backtest for this one pick
$enav = (float)$pick['entry_nav'];
$exit_n = $enav;
$dc = 0;
$ex_r = 'end_of_data';
$navs2 = $r['navs'];
$nc = count($navs2);
for ($i = 1; $i < $nc; $i++) {
    $dc++;
    $dn = (float)$navs2[$i]['nav'];
    $chg = (($dn - $enav) / $enav) * 100;
    if ($dc >= 21) {
        $exit_n = $dn;
        $ex_r = 'max_hold';
        break;
    }
}
$rpct = ($enav > 0) ? (($exit_n - $enav) / $enav) * 100 : 0;
$r['test_trade'] = array('entry' => $enav, 'exit' => $exit_n, 'return_pct' => round($rpct, 4), 'hold_days' => $dc, 'exit_reason' => $ex_r);

echo json_encode($r);
$conn->close();
?>
