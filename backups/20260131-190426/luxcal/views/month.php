<?php
/*
= month view of events =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

function showEvents($date) {
	global $usr, $xx, $evtList, $templ, $set, $rxIMGTags;

	foreach ($evtList[$date] as $evt) {
		if ($evt['typ'] > 0) { continue; }
		$chBox = $evt['cbx'] ? checkBox($evt,$date) : '';
		$popAttr = makePopAttrib($evt,$date,$set['showImgInMV']);
		$eStyle = colorStyle($evt); //get event colors
		$eStyle = $eStyle ? " style='{$eStyle}'" : '';
		$toAppr = ($evt['app'] and !$evt['apd']) ? ' toAppr' : '';
		$click = ($evt['mayE'] ? 'editE' : 'showE')."({$evt['eid']},`{$date}`)";
		$onClick = ($templ['pop'] or $evt['mayE']) ? "class='evtTitle' onclick='{$click}; event.stopPropagation();'" : "class='evtTitle arrow'";
		$title = $evt['mayE'] ? $xx['vws_edit_event'] : ($templ['pop'] ? $xx['vws_see_event'] : '');
		$event = makeHead($evt,$set['evtHeadM'],$date);
		$draggable = (($set['evtDrAndDr'] == 1 or ($set['evtDrAndDr'] == 2 and $usr['privs'] >= 4)) and $evt['mayE'] and $evt['nol'] == 0) ? " id='y.{$evt['eid']}.{$date}' draggable='true' ondragstart='drag(event)'" : '';
		echo "<div{$draggable} class='event{$toAppr}'{$eStyle}>\n";
		echo "<div {$onClick}{$popAttr} title=\"{$title}\">{$chBox}{$event}</div>\n";
		if ($set['showImgInMV']) {
			$xfText = ($usr['privs'] >= $set['xField1Rights'] ? $evt['tx2'] : '').($usr['privs'] >= $set['xField2Rights'] ? $evt['tx3'] : '');
			if (preg_match_all($rxIMGTags,$evt['tx1'].$xfText,$imgs, PREG_SET_ORDER)) {
				foreach ($imgs as $img) { echo $img[0]; }
			}
		}
		echo "</div>\n";
	}
}

/*===  main program ===*/
//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$evtList = []; //init
$cYear = intval(substr($opt['cD'],0,4));
$cMonth = intval(substr($opt['cD'],5,2));
$cDay = intval(substr($opt['cD'],8,2));
$tcDate = mktime(12,0,0,$cMonth,$cDay,$cYear); //Unix time of cD
$prevYear = strval($cYear - 1).substr($opt['cD'],4);
$nextYear = strval($cYear + 1).substr($opt['cD'],4);
if ($set['MvWeeksToShow'] < 2) { //single month
	$tfDay = mktime(12,0,0,$cMonth,1, $cYear); //Unix time of 1st day of the month
	$prevDate = date("Y-m-d",mktime(12,0,0,$cMonth-1,1,$cYear)); //1st of prev. month
	$nextDate = date("Y-m-d",mktime(12,0,0,$cMonth+1,1,$cYear)); //1st of next month

	//determine total number of days to show, start date, end date
	$sOffset = date("N",$tfDay) - $set['weekStart']; //offset first day (ISO)
	$eOffset = date("t",$tfDay) + $sOffset; //offset last day
	$totDays = ($eOffset == 28) ? 28 : (($eOffset > 35) ? 42 : 35); //4, 5 or 6 weeks

	$st = $tfDay - $sOffset * 86400; //start time
	$et = $st + ($totDays - 1) * 86400; //end time
	$sDate = date("Y-m-d",$st);
	$eDate = date("Y-m-d",$et);
	$header = '<span'.($winXS ? '' : ' class="viewHdr"').'>'.makeD($opt['cD'],3).'</span>';
} else {
	$jumpWeeks = $set['MvWeeksToShow'] - intval($set['MvWeeksToShow']*0.5) + 1;
	$prevDate = date("Y-m-d",$tcDate - $jumpWeeks * 604800);
	$nextDate = date("Y-m-d",$tcDate + $jumpWeeks * 604800);

	//determine total number of days to show, start date, end date
	$totDays = $set['MvWeeksToShow'] * 7; //number of weeks to show
	$sOffset = (date("w",$tcDate) - $set['weekStart'] + 7) % 7; //offset first day
	$st = $tcDate - ($sOffset + 7) * 86400; //start time (1 past week)
	$et = $st + ($totDays - 1) * 86400; //end time
	$sDate = date("Y-m-d",$st);
	$eDate = date("Y-m-d",$et);
	$x3 = $winXS ? 'x3' : '';
	$header = '<span'.($winXS ? '' : ' class="viewHdr"').'>'.makeD($sDate,3,$x3).' - '.makeD($eDate,3,$x3).'</span>';
}

//display header
$dateHdr = !$cH ? $header : "<a href='javascript:index({cP:`up`});'>{$header}</a>";
$floatL = $winXS ? 'floatL' : '';
$floatR = $winXS ? 'floatR' : '';
$arrowLL = "<a class='noPrint arrowLink {$floatL}' href='javascript:index({cD:`{$prevYear}`});' title='{$xx['vws_prev_year']}'>&#9664;</a>";
$arrowRR = "<a class='noPrint arrowLink {$floatR}' href='javascript:index({cD:`{$nextYear}`});' title='{$xx['vws_next_year']}'>&#9654;</a>";
$arrowL = "<a class='noPrint arrowLink' href='javascript:index({cD:`{$prevDate}`});' title='{$xx['vws_backward']}'>&#9664;</a>";
$arrowR = "<a class='noPrint arrowLink' href='javascript:index({cD:`{$nextDate}`});' title='{$xx['vws_forward']}'>&#9654;</a>";
echo "<h5 class='floatC'>{$arrowLL}{$arrowL}{$dateHdr}{$arrowR}{$arrowRR}</h5>\n";
//display days
$days = ($mode == 'fm') ? '0123456' : $set['workWeekDays']; //days to show

//display day headers
echo '<div'.($winXS ? '' : " class='scrollBox sBoxMo'").">\n";
echo "<table class='grid'>\n";
if ($set['weekNumber']) { echo "<colgroup><col class='wkCol'></colgroup>\n"; } //week # hdr
echo "<thead>\n";
echo "<tr>";
if ($set['weekNumber']) { echo "<th class='wkCol'>{$xx['vws_wk']}</th>"; } //week # hdr
for ($i = 0; $i < 7; $i++) {
	$cTime = $st + $i * 86400; //current time
	if (strpos($days,date("w",$cTime)) !== false) { echo "<th>{$wkDays[($set['weekStart'] + $i) % 7]}</th>"; } //week days
}
echo "</tr>\n";
echo "</thead>\n";

//retrieve events
retrieve($sDate,$eDate,'guc','','*');

//build grid
for ($i = 0; $i < $totDays; $i++) {
	$cTime = $st + $i * 86400; //current time
	$cDate = date("Y-m-d",$cTime); //current date
	$curM = ltrim(substr($cDate,5,2),"0");
	$curD = ltrim(substr($cDate,8,2),"0");
	if ($i%7 == 0) { //new week
		echo '<tr class="monthWeek">';
		if ($set['weekNumber']) { //display week nr
			$weekX = $mode = 'fm' ? 4 : 5;
			echo !$cH ? "<td class='wnr'>" : "<td class='wnr hyper' onclick='index({cP:{$weekX},cD:`{$cDate}`});' title=\"{$xx['vws_view_week']}\">";
			echo date("W",$cTime + 86400)."</td>\n";
		}
	}
	$dayNr = date("w",$cTime);
	if (strpos($days,$dayNr) !== false) {
		if ($set['MvWeeksToShow'] > 0 or ($i >= $sOffset and $i < $eOffset)) { //no single month or day inside
			$dayBg = $hdrCol = $hdrTxt = '';
			$hdrId = $curSeq = 0;
			if (!empty($evtList[$cDate])) {
				foreach ($evtList[$cDate] as $evt) { //check if day background should be set
					if (($evt['dbg'] & 2) and $evt['seq'] > $curSeq) {
						$dayBg = " style='background:{$evt['cbg']}'";
						$curSeq = $evt['seq'];
					}
					if ($evt['typ'] == 1) {
						$hdrId = $evt['eid'];
						$hdrTxt = $evt['tit'];
						$hdrCol = " style='color:{$evt['tx2']}; background:{$evt['tx3']};'";
					}
				}
			}
			if ($set['MvWeeksToShow'] < 2) { //single month
				$dow = ($i < $sOffset or $i >= $eOffset) ? 'out' : ((strpos($set['workWeekDays'],$dayNr) === false) ? 'we0' : 'wd0');
			} else {
				$dow = ((strpos($set['workWeekDays'],$dayNr) === false) ? 'we' : 'wd').strval($curM%2); //alternate color per month
			}
			$day = $curD.$curM == "11" ? makeD($cDate,2) : (($i == 0 or $curD == "1") ? makeD($cDate,1) : ($set['monthInDCell'] ? makeD($cDate,1,'x3') : $curD));
			$class = ($curD == "1" or $curD.$curM == "11") ? 'dom1' : 'dom';
			if ($cH and $usr['privs'] > 1) { //calendar header and privs
				$day = "<span class='{$class} floatR hyper' onclick='newE(`{$cDate}`); event.stopPropagation();' title=\"{$xx['vws_add_event']}\">{$day}</span>";
			} else{
				$day = "<span class='{$class} floatR'>{$day}</span>";
			}
			$dow .= $cDate == $today ? ' today' : ($cDate == $newDate ? ' slday' : '');
			$addNew = '';
			if ($usr['privs'] > 1) {
				$dow .= ' hyper';
				$addNew = " onclick='newE(`{$cDate}`);' title=\"{$xx['vws_add_event']}\"";
			}
			$hdrClick = '';
			$hdrClass = 'floatC';
			if ($usr['privs'] >= 4) {
				$hdrClass .= ' hyper';
				$marker = $hdrId ? "editM({$hdrId},`{$cDate}`)" : "newM(`{$cDate}`)";
				$hdrClick = " onclick='{$marker}; event.stopPropagation();'  title=\"{$xx['vws_mark_day']}\"";
			}
			echo "<td class='{$dow}'{$dayBg}{$addNew}>\n{$day}\n"; //day cell
			$draggable = ($set['evtDrAndDr'] and $hdrTxt and $usr['privs'] >= 4) ? " id='m.{$hdrId}.{$cDate}.0' draggable='true' ondragstart='drag(event)'" : '';
			echo "<div{$draggable} class='{$hdrClass}'{$hdrCol}{$hdrClick}>{$hdrTxt}&hairsp;</div>\n";
			$class = $set['scrollDCell'] ? 'scrollCell' : 'cell';
			$mayDrop = $set['evtDrAndDr'] ? " id='y{$cDate}' ondrop='drop(event,this)' ondragover='event.preventDefault()'" : '';
			echo "<div{$mayDrop} class='{$class}'>\n";
			if (!empty($evtList[$cDate])) {
				showEvents($cDate);
			}
			echo "</div>\n";
		} else { //one month and day outside
			echo "<td class='blank'>\n";
		}
		echo "</td>\n";
	}
	if ($i%7 == 6) { echo "</tr>\n"; } //if last day of week, wrap to left
}
echo "</table>\n</div>\n";
?>
