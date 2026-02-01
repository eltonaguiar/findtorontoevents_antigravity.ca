<?php
/*
= users gantt view of events =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

function showEvent($date,$evt,$cDayNr) {
	global $usr, $xx, $templ, $colW, $evtList, $set, $daysToShow;

	$symbol = '';
	if ($evt['mde']) {
		$startT = ($evt['sti'] and $evt['smd'] == $date) ? $evt['sti'].':00' : '00:00:00';
		$endT = $evt['eti'] ? $evt['eti'].':00' : '24:00:00';
		$startD = max($date,$evt['smd']);
		$durMT = (strtotime($evt['emd'].' '.$endT) - strtotime($startD.' '.$startT)) / 60; //duration in mins
		$barL = round($durMT * $colW / 1440) - 3;
		$offset = round((60 * intval(substr($startT,0,2)) + intval(substr($startT,3,2))) / 1440 * $colW); //in mins
		$maxBarL = ($daysToShow - $cDayNr) * $colW - $offset - 2;
		$barL = min($barL,$maxBarL);
		$class = 'ganttBar'; 
	} elseif ($evt['ald']) {
		$offset = '0';
		$barL = $colW - 3;
		$class = 'ganttBar'; 
	} elseif(!empty($evt['eti'])) {
		$startT = $evt['sti'].':00';
		$endT = $evt['eti'].':00';
		$durMT = (strtotime($date.' '.$endT) - strtotime($date.' '.$startT)) / 60; //duration in mins
		$barL = round($durMT * $colW / 1440) - 3;
		$offset = round((60 * intval(substr($startT,0,2)) + intval(substr($startT,3,2))) / 1440 * $colW); //in mins
		$class = 'ganttBar'; 
	} else {
		$offset = '0';
		$symbol = '&#9670;';
		$class = 'diamant'; 
	}
	$popAttr = makePopAttrib($evt,$date);
	$bgColor = $set['eventColor'] == 1 ? $evt['cbg'] : ($set['eventColor'] == 2 ? $evt['uco'] : '#FFFFFF');
	$style = " style='background-color:{$bgColor}; margin-left:{$offset}px;".($symbol ? "" : " width:{$barL}px;")."'";
	$click = ($evt['mayE'] ? 'editE' : 'showE')."({$evt['eid']},`{$date}`)";
	$onClick = ($templ['pop'] or $evt['mayE']) ? " onclick='{$click}; event.stopPropagation();'" : "";
	$title = $evt['mayE'] ? $xx['vws_edit_event'] : ($templ['pop'] ? $xx['vws_see_event'] : '');
	$event = str_replace("<br>",' ',$evt['tix']);
	echo "<div class='ganttLine'{$onClick}{$popAttr} title='{$title}'><span class='{$class}'{$style}>{$symbol}</span>{$event}</div>\n";
}

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$colW = 56; //column width
$evtList = [];
$daysToShow = $set['GvWeeksToShow'] * 7;
$uxTime = strtotime($opt['cD'].' 12:00:00'); //Unix time of cD
$dayNr = date('w',$uxTime); //0:Su - 6:Sa

//set the start and end date of the calendar period to show
$sTime = $uxTime - ((($dayNr - $set['weekStart'] + 7) % 7) * 86400); //calendar start time
$sDate = date('Y-m-d',$sTime); //cal start date
$eDate = date('Y-m-d',$sTime + (($daysToShow - 1) * 86400)); //cal end date

$prevDate = date("Y-m-d",$sTime - (($daysToShow - 7) * 86400));
$nextDate = date("Y-m-d",$sTime + (($daysToShow - 7) * 86400));

//get events

//retrieve events
retrieve($sDate,$eDate,'guc');

//remove multiples of multi-day event
if (!empty($evtList)) {
	$evts1x = []; //init
	foreach ($evtList as $date => &$events) { //loop thru dates
		foreach ($events as $k => &$evt) { //loop thru events
			if ($evt['mde']) {
				if (in_array($evt['eid'].$evt['smd'],$evts1x)) { //same id, same start date
					unset($events[$k]);
				} else {
					$evts1x[] = $evt['eid'].$evt['smd'];
				}
			}
		}
		if (empty($events)) { unset($evtList[$date]); } //no events left for this date
	}
}

//display header
if (!$winXS) {
	$dateHdr = '<span class="viewHdr">'.makeD($sDate,3)." - ".makeD($eDate,3).'</span>';
	$arrowL = "<a class='noPrint arrowLink' href='javascript:index({cD:`{$prevDate}`});'>&#9664;</a>";
	$arrowR = "<a class='noPrint arrowLink' href='javascript:index({cD:`{$nextDate}`});'>&#9654;</a>";
	echo "<div class='calHeadMx'>\n<h5>{$arrowL}{$dateHdr}{$arrowR}</h5>\n</div>";
}

//display gantt chart
echo '<div'.($winXS ? '' : " class='scrollBox sBoxMx'").">\n";
echo "<div class='gantt'>\n";
echo "<table class='gantt'>\n";
//calendar months
echo "<tr><th class='col0'></th><th class='col1'></th>".($set['weekNumber'] ? "<th class='col2'></th>\n" : "<th class='col2'>{$xx['vws_duration']}</th>\n");
$cTime = $sTime;
for($i = 0; $i < $daysToShow; $i++) {
	$dx = date('j',$cTime); //day of month (1 - 31)
	$dxNext = date('j',$cTime+86400);
	$mx = date('n',$cTime); //month (1 - 12)
	if ($dx == 1 or $dx == 15 or ($i == 0 and $dxNext != '1' and $dxNext != '15')) {
		echo "<th class='month'>{$months[$mx-1]}</th>\n";
	} else {
		echo "<th></th>\n";
	}
	$cTime += 86400; //+1 day
}
echo "</tr>\n";
//week numbers
if ($set['weekNumber']) {
	echo "<tr><th class='col0'></th><th class='col1'></th><th class='col2'>{$xx['vws_duration']}</th>\n";
	for($i = 0; $i < $daysToShow; $i++) {
		$cTime = $sTime + $i * 86400;
		echo date('N',$cTime) == 1 ? "<th>{$xx['vws_wk']} ".date('W',$cTime)."</th>\n" : "<th></th>\n"; //day of week = Monday
	}
	echo "</tr>\n";
}
//week days
echo "<tr><th class='col0'>{$xx['vws_events']}</th><th class='col1'>{$xx['vws_start']}</th><th class='col2'>({$dhm[0]}-{$dhm[1]}:{$dhm[2]})</th>\n";
for($i=$set['weekStart']; $i < ($set['weekStart']+$daysToShow); $i++) {
	$cTime = $sTime + (($i - $set['weekStart']) * 86400);
	$cDate = date("Y-m-d",$cTime);
	$attrib = $cH ? " onclick='index({cP:6,cD:`{$cDate}`}); event.stopPropagation();' title=\"{$xx['vws_view_day']}\"" : " class='arrow'";
	echo "<th{$attrib}>{$wkDays_l[$i%7]} ".date("j",$cTime)."</th>\n"; //week days
}
echo "</tr>\n";
//calendar body
if ($evtList) {
	foreach($evtList as $eDate => &$events) {
		foreach($events as &$evt) {
			if ($evt['eti'] == '23:59') { $evt['eti'] = '24:00'; }
			if ($evt['mde']) {
				$startT = $evt['sti'] ? $evt['sti'].':00' : '00:00:00';
				$endT = $evt['eti'] ? $evt['eti'].':00' : '24:00:00';
				$eDate = min($eDate,$evt['sda']);
				$durMT = (strtotime($evt['eda'].' '.$endT) - strtotime($evt['sda'].' '.$startT)) / 60; //duration in mins
				$durD = floor($durMT / 1440);
				$durH = floor(($durMT - $durD * 1440) / 60);
				$durM = $durMT - $durD * 1440 - $durH * 60;
				$duration = substr('0'.strval($durD),-2).'-'.substr('0'.strval($durH),-2).':'.substr('0'.strval($durM),-2);
			} elseif ($evt['ald']) {
				$duration = '01-00:00';
			} elseif ($evt['eti']) {
				$startT = $evt['sti'] ? $evt['sti'].':00' : '00:00:00';
				$endT = $evt['eti'] ? $evt['eti'].':00' : '24:00:00';
				$durMT = (strtotime($evt['sda'].' '.$endT) - strtotime($evt['sda'].' '.$startT)) / 60; //duration in mins
				$durH = floor(($durMT) / 60);
				$durM = $durMT - $durH * 60;
				$duration = "00-".substr('0'.strval($durH),-2).':'.substr('0'.strval($durM),-2);
			} else {
				$duration = "<span class='diamant'>&#9670;</span>";
			}
			echo "<tr>\n<td class='col0'><div class='scrollY'>{$evt['tit']}</div></td><td class='col1'>".IDtoDD($date)."</td><td class='col2'>{$duration}</td>\n";
			for($i=0; $i < $daysToShow; $i++){ //number of days to show
				$cTime = $sTime + ($i * 86400);
				$cDate = date("Y-m-d",$cTime);
				$dow = strpos($set['workWeekDays'],date("w",$cTime)) === false ? 'we0' : 'wd0';
				$dow .= $cDate == $today ? ' today' : ($cDate == $newDate ? ' slday' : '');
				echo "<td class='{$dow}'>";
				if ($eDate == $cDate) {
					showEvent($cDate,$evt,$i);
				}
				echo "</td>\n";
			}
			echo "</tr>\n";
		}
	}
} else {
	echo "<tr><td colspan='20' class='msg warning'>{$xx['vws_no_events_in_gc']}<br></td></tr>\n";
}
//week days
echo "<tr><th class='col0'></th><th class='col1'></th><th class='col2'></th>\n";
for($i=$set['weekStart']; $i < ($set['weekStart']+$daysToShow); $i++) {
	$cTime = $sTime + (($i - $set['weekStart']) * 86400);
	$cDate = date("Y-m-d",$cTime);
	$attrib = $cH ? " onclick='index({cP:6,cD:`{$cDate}`}); event.stopPropagation();' title=\"{$xx['vws_view_day']}\"" : " class='arrow'";
	echo "<th{$attrib}>{$wkDays_l[$i%7]} ".date("j",$cTime)."</th>"; //week days
}
echo "</tr>\n";
//week numbers
if ($set['weekNumber']) {
	echo "<tr><th class='col0'></th><th class='col1'></th><th class='col2'></th>\n";
	for($i = 0; $i < $daysToShow; $i++) {
		$cTime = $sTime + $i * 86400;
		echo date('N',$cTime) == 1 ? "<th>{$xx['vws_wk']} ".date('W',$cTime)."</th>\n" : "<th></th>\n"; //day of week = Monday
	}
	echo "</tr>\n";
}
echo "</table>\n";
echo "</div>\n</div>\n";
end:
?>
