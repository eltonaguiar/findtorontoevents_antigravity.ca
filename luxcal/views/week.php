<?php
/*
= week view of events =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$evtList = [];
$tcDate = strtotime($opt['cD'].' 12:00:00'); //Unix time of cD
$d = substr($opt['cD'],8,2);
$m = substr($opt['cD'],5,2);
$y = substr($opt['cD'],0,4);
$days = ($mode == 'fw') ? '0123456' : $set['workWeekDays']; //days to show
$sOffset = (date("w", mktime(12,0,0,$m,$d,$y)) - $set['weekStart'] + 7) % 7;
$sDow = $d-$sOffset; //first day of week
$sDayOfWk = date("Y-m-d", mktime(12,0,0,$m,$sDow,$y));
$eDayOfWk = date("Y-m-d", mktime(12,0,0,$m,$sDow+strlen($days)-1,$y));
$sDoLastW = date("Y-m-d", mktime(12,0,0,$m,$sDow-7,$y));
$sDoNextW = date("Y-m-d", mktime(12,0,0,$m,$sDow+7,$y));

/* display header */
$weekNr = ($set['weekNumber'] and !$winXS) ? ' ('.$xx['vws_week'].' '.date('W', mktime(12,0,0,$m,$sDow+1,$y)).')' : '';
$x3 = $winXS ? 'x3' : '';
$header = '&nbsp;<span'.($winXS ? '' : ' class="viewHdr"').'>'.makeD($sDayOfWk,2,$x3).' - '.makeD($eDayOfWk,2,$x3)."{$weekNr}</span>&nbsp;";
$arrowL = "<a class='noPrint arrowLink' href='javascript:index({cD:`{$sDoLastW}`});'>&#9664;</a>";
$arrowR = "<a class='noPrint arrowLink' href='javascript:index({cD:`{$sDoNextW}`});'>&#9654;</a>";
$dateHdr = !$cH ? $header : "<a href='javascript:index({cP:`up`});'>{$header}</a>";
echo "<h5 class='floatC'>{$arrowL}{$dateHdr}{$arrowR}</h5>\n";

$cWidth = round(98 / strlen($days),1).'%';

/* retrieve events */
retrieve($sDayOfWk,$sDoNextW,'guc');

echo "<div".($winXS ? '' : " class='scrollBox sBoxWe'").">\n";
echo "<table class='grid'>\n";
/* display day headers */
echo "<colgroup><col class='tCol'></colgroup>\n"; //time hdr
echo "<thead>\n";
echo "<tr><th class='tCol'>{$xx['vws_time']}</th>\n";
for ($i=0;$i<7;$i++) {
	$cTime = mktime(12,0,0,$m,$sDow+$i,$y); //current time
	if (strpos($days,date("w",$cTime)) !== false) {
		$sDate = date("Y-m-d",$cTime);
		echo "<th class='dCol' style='width:{$cWidth}'".($cH ? " onclick='index({cP:6,cD:`{$sDate}`});' title=\"{$xx['vws_view_day']}\"" : '').">".makeD($sDate,($winXS ? 1 : 4),'xs')."</th>\n";
	}
}
echo "</tr>\n";
echo "</thead>\n";
/* display days */
echo "<tr><td class='tCol tColBg'>\n";
showHours();
echo "</td>\n";
for ($i=0;$i<7;$i++) {
	$cTime = mktime(12,0,0,$m,$sDow+$i,$y); //current time
	$cDate = date("Y-m-d", $cTime); //current date
	$dayNr = date("w",$cTime);
	if (strpos($days,$dayNr) !== false) {
		$dayBg = '';
		$curSeq = 0;
		if (!empty($evtList[$cDate])) { //check day background should be set
			foreach ($evtList[$cDate] as $evt) {
				if (($evt['dbg'] & 2) and $evt['seq'] > $curSeq) {
					$dayBg = " background:{$evt['cbg']};";
					$curSeq = $evt['seq'];
				}
			}
		}
		$dow = strpos($set['workWeekDays'],$dayNr) === false ? 'we0' : 'wd0'; //week end or week day
		$dow .= $cDate == $today ? ' today' : ($cDate == $newDate ? ' slday' : '');
		echo "<td class='dCol {$dow}' style='width:{$cWidth};{$dayBg}'>\n";
		showDay(date("Y-m-d",$cTime));
		echo "</td>\n";
	}
}
echo "</tr>\n</table>
</div>\n";
if ($usr['privs'] > 1) {
	echo "<script>dragTime()</script>\n";
}
?>