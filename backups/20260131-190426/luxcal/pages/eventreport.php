<?php
//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

$viaGet = isset($_GET['eid']) ? true : false; //stand-alone use of event report

//get input params
$eid = $_REQUEST['eid'] ?? 0;
$evD = $_POST['evD'] ?? '';

//get event data
$stH = stPrep("
	SELECT e.*,u.`name` AS own
	FROM `events` e
	INNER JOIN `users` u ON u.`ID` = e.`userID`
	WHERE e.`ID` = ?");
stExec($stH,[$eid]);
$row = $stH->fetch(PDO::FETCH_ASSOC);
$stH = null;
$adt = $row['aDateTime'];
$mdt = $row['mDateTime'][0] != '9' ? $row['mDateTime'] : "";
$edr = $row['editor'];
$tit = $row['title'];
$ven = $row['venue'];
$tx1 = $row['text1'];
$tx2 = $row['text2'];
$tx3 = $row['text3'];
$att = $row['attach'];
$cid = $row['catID'];
$sid = $row['scatID'];
$uid = $row['userID'];
$nal = $row["notRecip"] ?: $usr['email'];
$apd = $row['approved'];
$pri = $row['private'];
$sda = IDtoDD($row['sDate']);
$eda = IDtoDD($row['eDate']);
$sti = $row['sTime'];
$eti = $row['eTime'];
$r_t = $row['rType'];
$r_i = $row['rInterval'];
$r_p = $row['rPeriod'];
$r_m = $row['rMonth'];
$rul = ($row['rUntil'][0] != "9") ? $row['rUntil'] : '';
$not = $row['notify'] > -1 ? $row['notify'] : '';
$own = $row['own'];

if ($viaGet) { //stand-alone use
	$p2 = strrpos(": {$tit}",': ') + 1;
	if (empty($_GET['k']) or $_GET['k'] != ord($tit[$p2])) {
		echo $xx['no_way']; //no or invalid key
		exit;
	}
}

//get category data
$stH = stPrep("SELECT 
	`name`,`approve`, `color`,`bgColor`,`subCats`
	FROM `categories`
	WHERE `ID` = ?");
stExec($stH,[$cid]);
$row = $stH->fetch(PDO::FETCH_ASSOC);
$stH = null; //release statement handle
$cnm = $row['name'];
$app = $row['approve'];
$sCats = json_decode($row['subCats']);
if (!$sid or empty($sCats[$sid-1])) { //no subcat
	$snm = '';
	$cco = $row['color'];
	$cbg = $row['bgColor'];
} else {
	$sCat = $sCats[$sid-1];
	$snm = $sCat[0];
	$cco = $sCat[1] ?: $row['cco'];
	$cbg = $sCat[2] ?: $row['cbg'];
}

$repTxt = repeatText($r_t,$r_i,$r_p,$r_m,$rul); //make repeat text

$ald = $ntm = false; //init
if ($sti == '00:00' and ($eti == '23:59' or $eti == '00:00')) {
	if ($eti == '23:59') { $ald = true; }
	if ($eti == '00:00') { $ntm = true; }
	$sti = $eti = ''; //all day or no time: start/end time = ''
} else {
	$sti = ITtoDT($sti);
	$eti = ITtoDT($eti);
}
if (!$eda) { $sda = IDtoDD($evD); }

if ($app and $apd) { //event approved
	echo "<div class='apdBar'>{$xx['evt_apd_locked']}</div>\n";
}

$evt = array ('ven' => $ven, 'cnm' => $cnm, 'tx1' => $tx1, 'tx2' => $tx2, 'tx3' => $tx3, 'att' => $att, 'snm' => $snm); //tx1 - tx3: with hyperlinks

$eColor = ($cco or $cbg) ? " style='color:{$cco}; background:{$cbg};'" : '';
echo "<div class='evtCanvas'>\n";
echo "<table class='evtForm arrow'>
<colgroup><col class='c01'><col></colgroup>
<tr><td>{$xx['evt_title']}:</td><td><span{$eColor}>{$tit}</span></td></tr>";
if ($pri) { echo "<tr><td colspan='2'>{$xx['evt_private']}</td></tr>\n"; }
echo makeE($evt,$templ['gen'],'tx',"\n",'123458');
echo "<tr><td colspan='2'><hr></td></tr>";
$fullDT = makeFullDT(false,$sda,$eda,$sti,$eti,$ald);
echo "<tr><td>".($ntm ? $xx['evt_date'] : $xx['evt_date_time']).":</td><td>{$fullDT}</td></tr>\n"; //make full date (display values)
if ($r_t) {
	echo "<tr><td colspan='2'>{$repTxt}<br></td></tr>\n";
}
if ($not != "" and ($usr['privs'] > 2 or ($usr['privs'] == 2 and $uid == $usr['ID']))) { //has rights to see reminder address list
	echo "<tr><td colspan='2'><hr></td></tr>\n";
	if ($not != "") {
		echo "<tr><td>{$xx['evt_notification']}:</td>\n<td>{$not} {$xx['evt_days_before_event']}</td></tr>\n";
	}
	echo "<tr><td colspan='2'>{$nal}</td></tr>\n";
}
if (strpos($templ['gen'],'7') !== false) {
	echo "<tr><td colspan='2'><hr></td></tr>
<tr><td>{$xx['evt_added']}:</td><td>".IDTtoDDT($adt)." {$xx['by']} {$own}";
	if ($mdt and $edr) {
		echo "</td></tr>\n<tr><td>{$xx['evt_edited']}:</td><td>".IDTtoDDT($mdt)." {$xx['by']} {$edr}";
	}
}
echo "</td></tr>\n";
echo "</table>\n";
echo "</div><br>\n";
if (!$viaGet) {
	echo "<div class='floatC noPrint'><button onClick='javascript:self.close();'>{$xx["evt_close"]}</button></div>\n";
}
?>
