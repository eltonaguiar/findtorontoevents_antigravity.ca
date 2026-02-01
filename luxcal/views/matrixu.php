<?php
/*
= users matrix view of events =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

function showEvents($date,$uID) {
	global $xx, $templ, $evtList, $set;

	foreach ($evtList[$date] as $evt) {
		if ($evt['uid'] != $uID) { continue; }
		$popAttr = makePopAttrib($evt,$date);
		$bgColor = $set['eventColor'] == 1 ? $evt['cbg'] : ($set['eventColor'] == 2 ? $evt['uco'] : '#FFFFFF');
		$style = " style='background-color:{$bgColor};'";
		$class = $evt['sym'] ? 'symbol' : 'square';
		$click = ($evt['mayE'] ? 'editE' : 'showE')."({$evt['eid']},`{$date}`)";
		$onClick = ($templ['pop'] or $evt['mayE']) ? "class='{$class}'{$style} onclick='{$click}; event.stopPropagation();'" : "class='{$class} arrow'{$style}";
		$title = $evt['mayE'] ? $xx['vws_edit_event'] : ($templ['pop'] ? $xx['vws_see_event'] : '');
		echo "<div {$onClick}{$popAttr} title=\"{$title}\">{$evt['sym']}</div>\n";
	}
}

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$evtList = [];
$daysToShow = $set['XvWeeksToShow'] * 7;
$uxTime = strtotime($opt['cD'].' 12:00:00'); //Unix time of cD
$dayNr = date('w',$uxTime); //0:Su - 6:Sa

//set the start and end date of the calendar period to show
$sTime = $uxTime - ((($dayNr - $set['weekStart'] + 7) % 7) * 86400); //calendar start time
$sDate = date('Y-m-d',$sTime); //cal start date
$eDate = date('Y-m-d',$sTime + (($daysToShow - 1) * 86400)); //cal end date

$prevDate = date("Y-m-d",$sTime - (($daysToShow - 7) * 86400));
$nextDate = date("Y-m-d",$sTime + (($daysToShow - 7) * 86400));

//get users

$filter = ''; //user filter
if (count($opt['cU']) > 0 and $opt['cU'][0] != 0) {
	$filter .= "u.`ID` IN (".implode(",",$opt['cU']).") AND ";
}
if (count($opt['cG']) > 0 and $opt['cG'][0] != 0) {
	$filter .= "g.`ID` IN (".implode(",",$opt['cG']).") AND ";
}
$stH = dbQuery("SELECT u.`ID`, u.`name`, g.`color` 
	FROM `users` AS u
	INNER JOIN `groups` AS g ON g.`ID` = u.`groupID`
	WHERE {$filter}u.`status` >= 0
	ORDER BY u.`name`");
$users = $stH->fetchAll(PDO::FETCH_ASSOC); //2-dim array

if (count($users) == 0) {
	echo "<div class='scrollBox sBoxMx'><h3>{$xx['vws_no_users']}</h3></div>";
	goto end;
}

//retrieve events
retrieve($sDate,$eDate,'guc');

//display header
if (!$winXS) {
	$dateHdr = '<span class="viewHdr">'.makeD($sDate,3)." - ".makeD($eDate,3).'</span>';
	$arrowL = "<a class='noPrint arrowLink' href='javascript:index({cD:`{$prevDate}`});'>&#9664;</a>";
	$arrowR = "<a class='noPrint arrowLink' href='javascript:index({cD:`{$nextDate}`});'>&#9654;</a>";
echo "<div class='calHeadMx'>\n<h5>{$arrowL}{$dateHdr}{$arrowR}</h5>\n</div>";
}

//display matrix - users
echo '<div'.($winXS ? '' : " class='scrollBox sBoxMx'").">\n";
echo "<div class='matrix'>\n";
echo "<table class='matrix'>\n";
//matrix header
//calendar months
echo "<tr><th class='col0'>"; //col 0
if (strpos($avViews,'9') !== false) {
	echo	"<form method='post' action='javascript:index({cP:9});'><button type='submit' name='back' value='y'>{$xx['vws_evt_cats']}</button></form>";
}
echo "</th>\n";
$cTime = $sTime;
for($i = 0; $i < $daysToShow; $i++) { //make matrix columns header
	$dx = date('j',$cTime); //day of month (1 - 31)
	$dxNext = date('j',$cTime+86400);
	$mx = date('n',$cTime); //month (1 - 12)
	if($dx == 1 or $dx == 15 or ($i == 0 and $dxNext != '1' and $dxNext != '15')) {
		echo "<th class='month'>{$months[$mx-1]}</th>\n";
	} else {
		echo "<th></th>\n";
	}
	$cTime += 86400; //+1 day
}
echo "</tr>\n";
//week numbers
if ($set['weekNumber']) {
	echo "<tr><th class='col0'></th>\n"; //col 0
	for($i = 0; $i < $daysToShow; $i++) {
		$cTime = $sTime + $i * 86400;
		echo date('N',$cTime) == 1 ? "<th>{$xx['vws_wk']} ".date('W',$cTime)."</th>\n" : "<th></th>\n"; //day of week = Monday
	}
	echo "</tr>\n";
}
echo "<tr><th class='col0'>{$xx['vws_cal_users']}</th>\n"; //col 0
//week days
for($i=$set['weekStart']; $i < ($set['weekStart']+$daysToShow); $i++) {
	$cTime = $sTime + (($i - $set['weekStart']) * 86400);
	$cDate = date("Y-m-d",$cTime);
	$attrib = $cH ? " onclick='index({cP:6,cD:`{$cDate}`}); event.stopPropagation();' title=\"{$xx['vws_view_day']}\"" : " class='arrow'";
	echo "<th{$attrib}>{$wkDays_l[$i%7]} ".date("j",$cTime)."</th>\n"; //week days
}
echo "</tr>\n";
//matrix body
foreach($users as $user) {
	$style = $user['color'] ? " style='background-color:{$user['color']};'" : '';
	echo "<tr>\n<td class='col0'{$style}>{$user['name']}</td>\n"; //col 0
	for($i=0; $i < $daysToShow; $i++){ //number of days to show
		$cTime = $sTime + ($i * 86400);
		$cDate = date("Y-m-d",$cTime);
		$dayBg = '';
		if (!empty($evtList[$cDate])) { //check if day background should be set
			foreach ($evtList[$cDate] as $evt) {
				if ($evt['uid'] == $user['ID'] and ($evt['dbg'] & 1)) {
					$dayBg = " style='background:{$evt['cbg']}'";
				}
			}
		}
		$dow = strpos($set['workWeekDays'],date("w",$cTime)) === false ? 'we0' : 'wd0';
		$dow .= $cDate == $today ? ' today' : ($cDate == $newDate ? ' slday' : '');
		$addNew = '';
		if ($usr['ID'] == $user['ID'] and $usr['privs'] > 1) {
			$dow .= ' hyper';
			$addNew = " onclick=\"newE('{$cDate}');\" title=\"{$xx['vws_add_event']}\"";
		}
		echo "<td class='{$dow}'{$dayBg}{$addNew}>\n";
		if (!empty($evtList[$cDate])) { showEvents($cDate,$user['ID']); }
		echo "</td>\n";
	}
	echo "</tr>\n";
}
//matrix footer
//week days
echo "<tr><th class='col0'></th>\n"; //col 0
for($i=$set['weekStart']; $i < ($set['weekStart']+$daysToShow); $i++) {
	$cTime = $sTime + (($i - $set['weekStart']) * 86400);
	$cDate = date("Y-m-d",$cTime);
	$attrib = $cH ? " onclick=\"index({cP:6,cD:'{$cDate}'}); event.stopPropagation();\" title=\"{$xx['vws_view_day']}\"" : " class='arrow'";
	echo "<th{$attrib}>{$wkDays_l[$i%7]} ".date("j",$cTime)."</th>\n";
}
echo "</tr>\n";
//week numbers
if ($set['weekNumber']) {
	echo "<tr><th class='col0'></th>\n"; //col 0
	for($i = 0; $i < $daysToShow; $i++) {
		$cTime = $sTime + $i * 86400;
		echo date('N',$cTime) == 1 ? "<th>{$xx['vws_wk']} ".date('W',$cTime)."</th>\n" : "<th></th>\n"; //day of week = Monday
	}
	echo "</tr>\n";
}
echo "</table>\n</div>\n</div>\n";
echo "<script>window.onload = function() {document.getElementById('matrix').focus()}</script>\n";
end:
?>
