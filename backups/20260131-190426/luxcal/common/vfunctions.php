<?php
/*
 = General functions used by the LuxCal view scripts =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

/* week and day functions used by Day and Week view scripts */

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

function showDayEvents($date) {
	global $evtList, $set, $templ, $xx;

	$thsM = ($set['dwStartHour'] * 60); //threshold start of day in mins
	$theM = ($set['dwEndHour'] * 60); //threshold end of day in mins
	$offset = $set['dwStartHour'] ? 2 * $set['dwTimeSlot'] : $set['dwTimeSlot']; //"earlier" row
	//hereafter: M = in nbr of mins
	foreach ($evtList[$date] as $evt) {
		if ($evt['mde']) { //multi-day-event
			if ($evt['mde'] != 1) { $evt['sti'] = '00:00'; } //not the first day
			if ($evt['mde'] != 3) { $evt['eti'] = '23:59'; } //not the last day
		}
		if ($evt['ntm'] or $evt['ald']) { //no time or all day (takes up 1 slot at the top)
			$st[] = 0; //start time
			$et[] = $set['dwTimeSlot']; //end time
		} else {
			$stM = substr($evt['sti'],0,2) * 60 + intval(substr($evt['sti'],3,2)); //start time
			if ($stM < $thsM) {
				$st[] = $set['dwTimeSlot']; //start time < threshold start of day in mins
			} elseif ($stM < $theM) {
				$st[] = $stM - $thsM + $offset; //start time < threshold end of day in mins
			} else {
				$st[] = $theM - $thsM + $offset; //start time >= threshold end of day in mins
			}
			if ($evt['eti'] == "" or $evt['eti'] == $evt['sti']) {
				$et[] = end($st) + $set['dwTimeSlot'];
			} else {
				$etM = substr($evt['eti'],0,2) * 60 + intval(substr($evt['eti'],3,2)); //end time in mins
				if ($etM <= $thsM) {
					$et[] = $offset; //end time <= threshold start of day in mins
				} elseif ($etM <= $theM) {
					$et[] = $etM - $thsM + $offset; //end time < threshold end of day in mins
				} else {
					$et[] = $theM - $thsM + $offset + $set['dwTimeSlot']; //end time > threshold end of day in mins
				}
			}
		}
	}
	//for day $date we now have:
	//$st: array with start time in mins for each event
	//$et: array with end time in mins for each event
	//the indexes in these arrays correspond to the indexes in $evtList
	$sEmpty = [[]]; //columns with start of empty # of minutes
	$eEmpty = [[]]; //columns with end of empty # of minutes
	$sFill = [[]]; //columns with start time of each event
	$eIndx = [[]]; //columns with indexes in $evtList
	$column = []; //array with column number of each event
	//init
	$sEmpty[0][0] = 0;
	$eEmpty[0][0] = 1440; //24 x 60 mins
	$indent = 0;
	//process events
	foreach ($st as $i => $stM) { //i: index in $evtList, stM: start time in mins
		$found = false;
		foreach ($sEmpty as $c => $ses) { //c: column nr, ses: start of empty spaces in mins
			foreach ($ses as $k => $sEtM) { //look for an empty slot in the current column
				if ($stM >= $sEtM and $et[$i] <= $eEmpty[$c][$k]) {
					$found = true;
					$sEmpty[$c][] = $et[$i]; //end time in mins
					$eEmpty[$c][] = $eEmpty[$c][$k];
					$eEmpty[$c][$k] = $stM; //start in mins
					$sFill[$c][] = $stM;
					$eIndx[$c][] = $i;
					$column[$i] = $c;
					break 2;
				}
			}
		}
		if (!$found) {
			$indent++;
			$sEmpty[$indent][0] = 0;
			$eEmpty[$indent][0] = $stM;
			$sEmpty[$indent][1] = $et[$i];
			$eEmpty[$indent][1] = 1440; //24 x 60 mins
			$sFill[$indent][0] = $stM;
			$eIndx[$indent][0] = $i;
			$column[$i] = $indent;
		}
	}
	$cWidth = round(98 / ($indent+1),1); //width of smallest column
	foreach ($sFill as $c => $stA) { //c: column nr, stA: array with event start times
		$eLeft = $cWidth * $c + 0.5; //event left side in %
		foreach ($stA as $k => $stM) { //event start time in mins
			$etM = $sEmpty[$c][$k + 1]; //event end time in mins
			$eHeight = $etM - $stM; //event height in mins
			$stP = round($stM * $set['dwTsHeight'] / $set['dwTimeSlot']) - 1; //scale start time in px
			$eHeight = round($eHeight * $set['dwTsHeight'] / $set['dwTimeSlot']) - 1; //scale height in px
			$i = $eIndx[$c][$k];
			$evt = $evtList[$date][$i];
			$sti = ($evt['sti']) ? ITtoDT($evt['sti']) : '';
			//widen event box if possible
			$ovlCol = $indent+1;
			foreach ($column as $iCol => $colNr) { //find next column of overlapping event
				$evtT = $evtList[$date][$iCol];
				if ($evtT['sti'] < $evt['eti'] and $evtT['eti'] > $evt['sti']) { //overlap
					if ($colNr > $column[$i] and $colNr < $ovlCol) { //column nr lower
						$ovlCol = $colNr;
					}
				}
			}
			$eWidth = ($ovlCol-$c) * $cWidth - 0.5;
			$toAppr = ($evt['app'] and !$evt['apd']) ? ' toAppr' : '';
			$popAttr = makePopAttrib($evt,$date);
			$eStyle = colorStyle($evt,'#FFFFFF'); //get event colors
			$chBox = $evt['cbx'] ? checkBox($evt,$date) : '';
			$onClick = ($templ['gen'] or $evt['mayE']) ? " onclick='".($evt['mayE'] ? 'editE' : 'showE')."({$evt['eid']},`{$date}`);'" : '';
			$class = ($eHeight < 21 ? ' noWrap' : '').($onClick ? '' : ' arrow');
			$title = $evt['mayE'] ? $xx['vws_edit_event'] : ($templ['gen'] ? $xx['vws_see_event'] : '');
			echo "<div class='evtBox evtTitle{$toAppr}'{$popAttr}{$onClick} title=\"{$title}\" style='top:{$stP}px; left:{$eLeft}%; height:{$eHeight}px; width:{$eWidth}%; {$eStyle}'>\n";
			$event = makeHead($evt,$set['evtHeadW'],$date);
			if ($eHeight < 21) { $event = str_replace("<br>",' ',$event); }
			echo "<div class='dwEvent{$class}'>{$chBox}{$event}</div>\n";
			echo "</div>\n";
		}
	}
}

function showHours() {
	global $set, $xx;
	//build day
	$tsHeight = "style='height:".($set['dwTsHeight'] -1)."px;'";
	echo "<div class='times' {$tsHeight}>{$xx['vws_all_day']}</div>\n";
	$i = $set['dwStartHour'];
	$j = 0;
	if ($set['dwStartHour']) {
		echo "<div class='times' {$tsHeight}>{$xx['vws_earlier']}</div>\n";
	}
	while ($i < $set['dwEndHour']) {
		echo "<div class='times' {$tsHeight}>".ITtoDT(substr("0".$i,-2).":".substr("0".$j,-2))."</div>\n";
		if (($j += $set['dwTimeSlot']) >= 60) {
			$i++;
			$j -= 60;
		}
	}
	if ($set['dwEndHour'] < 24) {
		echo "<div class='times' {$tsHeight}>{$xx['vws_later']}</div>\n";
	}
}

function showDay($cDate,$caption="") {
	global $set, $evtList;

	//build day
	$tsHeight = "style='height:".($set['dwTsHeight'] -1)."px;'";
	echo "<div class='timeFrame' data-slot='{$set['dwTimeSlot']}'>\n";
	echo "<div id='d.{$cDate}.00:00' class='tSlot' {$tsHeight}></div>\n";
	$i = $set['dwStartHour'];
	$j = 0;
	if ($i > 0) {
		echo "<div id='d.{$cDate}.00:30' class='tSlot' {$tsHeight}></div>\n";
	}
	while ($i < $set['dwEndHour']) {
		echo "<div id='d.{$cDate}.".substr("0".$i,-2).":".substr("0".$j,-2)."' class='tSlot' {$tsHeight}></div>\n";
		if (($j += $set['dwTimeSlot']) >= 60) {
			$i++;
			$j -= 60;
		}
	}
	if ($set['dwEndHour'] < 24) {
		echo "<div id='d.{$cDate}.".substr("0".$i,-2).":".substr("0".$j,-2)."' class='tSlot' {$tsHeight}></div>\n";
	}
	echo "<div class=dates>\n";
	if (!empty($evtList[$cDate])) { showDayEvents($cDate); }
	echo "</div>";
	echo "</div>\n";
}


/* Side Panel functions used by header script */

function showMiniCal($tslotD,$mode) {
	global $set, $xx, $usr, $wkDays_s, $evtList;
	
	//compute dates
	$offM = $_GET['oM'] ?? 0; //offset Month
	$timeD1 = mktime(12,0,0,date('n',$tslotD)+$offM,1,date('Y',$tslotD)); //time 1st day
	$dateD1 = date("Y-m-d", $timeD1); //date 1st day
	$curM = date("n",$timeD1);
	$curY = date("Y",$timeD1);
	$sOffset = ($set['weekStart']) ? date("N", $timeD1) - 1 : date("w", $timeD1); //offset first day
	$eOffset = date("t", $timeD1) + $sOffset; //offset last day
	$daysToShow = ($eOffset == 28) ? 28 : (($eOffset > 35) ? 42 : 35); //4, 5 or 6 weeks
	$sDate = date("Y-m-d", $timeD1 - ($sOffset * 86400)); //start date in 1st week
	$eDate = date("Y-m-d", $timeD1 + ($daysToShow - $sOffset - 1) * 86400); //end date in last week
	retrieve($sDate,$eDate,'guc','','*'); //retrieve events

	/* display header */
	$phpSelf = htmlentities($_SERVER['PHP_SELF']);
	$arrowLL = "<a class='arrowLink' href='{$phpSelf}?oM=".($offM-12)."' title='{$xx['vws_prev_year']}'>&#9664;</a>\n";
	$arrowRR = "<a class='arrowLink' href='{$phpSelf}?oM=".($offM+12)."' title='{$xx['vws_next_year']}'>&#9654;</a>\n";
	$arrowL = "<a class='arrowLink' href='{$phpSelf}?oM=".($offM-1)."' title='{$xx['vws_prev_month']}'>&#9664;</a>\n";
	$arrowR = "<a class='arrowLink' href='{$phpSelf}?oM=".($offM+1)."' title='{$xx['vws_next_month']}'>&#9654;</a>\n";
	echo "<h6 class='floatC'>\n{$arrowLL}{$arrowL}<span class='miniHdr'>".makeD($dateD1,3)."</span>\n{$arrowR}{$arrowRR}</h6>\n";

	/* display month */
	$days = ($mode and $mode[0] == 'w') ? $set['workWeekDays'] : '1234567'; //set days to show
	$cWidth = round(98 / strlen($days),1).'%';
	echo "<div class='miniBdy'>";
	echo "<table class='grid'>
<col span='".strlen($days)."' class='dCol' style='width:{$cWidth}'>
<tr>\n";
	for ($i = 0; $i < 7; $i++) {
		$cTime = mktime(12,0,0,$curM,$i-$sOffset+1,$curY ); //current time
		if (strpos($days,date("N",$cTime)) !== false) { echo "<th>{$wkDays_s[$set['weekStart'] + $i]}</th>"; } //week days
	}
	echo "</tr>\n";
	for ($i = 0; $i < $daysToShow; $i++) {
		$cTime = mktime(12,0,0,$curM,$i-$sOffset+1,$curY ); //current time
		$cDate = date("Y-m-d", $cTime);
		if ($i%7 == 0) { //new week
			echo "<tr class='yearWeek'>\n";
		}
		$dayNr = date("N", $cTime);
		if (strpos($days,$dayNr) !== false) {
			$dow = ($i < $sOffset or $i >= $eOffset) ? 'out' : (($dayNr > 5) ? 'we0' : 'wd0');
			if ($cDate == date("Y-m-d")) { $dow .= ' today'; }
			$day = ltrim(substr($cDate,8,2),'0');
			$day = "<span class='dom fontS floatR'>{$day}</span>";
			$dayBg = $hdrTxt = $hdrCol = '';
			$curSeq = 0;
			if (!empty($evtList[$cDate])) {
				foreach ($evtList[$cDate] as $evt) {
					if (($evt['dbg'] & 1) and $evt['seq'] > $curSeq) { //set day background
						$dayBg = " style='background:{$evt['cbg']}'";
						$curSeq = $evt['seq'];
					}
					if ($evt['typ'] == 1) { //day marker event
						$hdrId = $evt['eid'];
						$hdrTxt = " title='".strip_tags($evt['tit'])."'";
						$hdrCol = " style='background:{$evt['tx3']};'";
					}
				}
			}
			$mayDrop = $set['evtDrAndDr'] ? " id='y{$cDate}' ondrop='drop(event,this)' ondragover='event.preventDefault()'" : '';
			echo "<td{$mayDrop} class='{$dow}'{$dayBg}>$day\n"; //day cell
			$draggable = ($set['evtDrAndDr'] and $hdrTxt and $usr['privs'] >= 4) ? " id='m.{$hdrId}.{$cDate}.0' draggable='true' ondragstart='drag(event)'" : '';
			echo "<div{$draggable}{$hdrTxt}{$hdrCol}>&nbsp;</div>\n";
			if (!empty($evtList[$cDate])) {
				foreach ($evtList[$cDate] as $evt) { //show events for this date
					if ($evt['typ'] > 0) { continue; } //skip day marker events
					$popAttr = makePopAttrib($evt,$cDate);
					$bgColor = $evt['cbg'] ? " style='background-color:{$evt['cbg']};'" : '';
					$class = $evt['sym'] ? 'symbol' : 'square';
					$draggable = ($evt['mayE'] and $evt['nol'] == 0) ? " id='s.{$evt['eid']}.{$cDate}' draggable='true' ondragstart='drag(event)'" : '';
					echo "<span{$draggable} class='arrow {$class}'{$bgColor}{$popAttr}>{$evt['sym']}</span>\n";
				}
			}
			echo "</td>\n";
		}
		if ($i%7 == 6) { echo "</tr>\n"; } //if last day of week, wrap to left
	}
	echo "<tr>\n<th class='smallHt' colspan='7'>";
	if ($offM != 0) { echo "<a class='floatC' href='".htmlentities($_SERVER['PHP_SELF'])."?oM=0' title='{$xx['vws_back_to_main_cal']}'>{$xx['back']}</a>"; }
	echo "</th>\n</tr>\n</table>\n</div>\n";
}

function showSidePanel($tcDate,$spItems) {
	global $mode;

	echo "<div class='sPanel noPrint'>\n";
	if ($spItems[0]) {
		echo "<div class='spCal'>\n";
		showMiniCal($tcDate,$mode); //this month
		echo "</div>\n";
	}
	if ($spItems[1]) {
		$fName = preg_grep('~^'.date('m',$tcDate).'[a-z0-9_]+\.(jpg|gif|png)$~i',scandir("sidepanel")); //get images from sidepanel folder
		if ($fName) {
			echo "<div class='spImg'>\n<img class='spImage' src='sidepanel/".array_shift($fName)."' alt='decoration'>\n</div>\n";
		}
	}
	if ($spItems[2] and is_file('sidepanel/info.txt')) {
		$info = file_get_contents('sidepanel/info.txt');
		if (preg_match_all('%^\s*~(\d\d?)(?:\.(\d\d?))?(?:\s*-\s*(\d\d?)(?:\.(\d\d?))?)?~([^~]+)%m',$info,$matches,PREG_SET_ORDER)) {
			$spInfo = '';
			$cMD = date('md',$tcDate); //month.day (mm.dd)
			foreach($matches as $match) {
				$sMD = substr('0'.$match[1],-2).substr('00'.$match[2],-2);
				$eMD = ($match[3] ? substr('0'.$match[3],-2) : substr($sMD,0,2)).($match[4] ? substr('00'.$match[4],-2) : '31');
				if ($cMD >= $sMD and $cMD <= $eMD) {
					$spInfo .= trim($match[5]).'<br><br>';
				}
			}
			if ($spInfo) {
				echo "<div class='spMsg'>\n".substr($spInfo,0,-8)."\n</div>\n";
			}
		}
	}
	echo "</div>\n";
}
?>
