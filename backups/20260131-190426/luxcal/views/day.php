<?php
/*
= calendar day view =


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
$nextDay = date("Y-m-d", $tcDate + 86400);
$prevDay = date("Y-m-d", $tcDate - 86400);

/* display header */
$header = "<span".($winXS ? '' : " class='viewHdr'").'>'.makeD($opt['cD'],5).'</span>';
$dateHdr = !$cH ? $header : "<a href='javascript:index({cP:`up`});'>{$header}</a>";
$arrowL = "<a class='noPrint arrowLink' href='javascript:index({cD:`{$prevDay}`});'>&#9664;</a>";
$arrowR = "<a class='noPrint arrowLink' href='javascript:index({cD:`{$nextDay}`});'>&#9654;</a>";
echo "<h5 class='floatC'>{$arrowL}{$dateHdr}{$arrowR}</h5>\n";

/* retrieve events */
retrieve($opt['cD'],$nextDay,'guc');

echo "<div".($winXS ? '' : " class='scrollBox sBoxDa'").">\n";
echo "<table class='grid'>\n";
/* display day headers */
echo "<colgroup><col class='tCol'></colgroup>\n"; //time hdr
echo "<thead>\n";
echo "<tr><th class='tCol'>{$xx['vws_time']}</th><th class='dCol'>{$xx['vws_events']}</th></tr>\n";
echo "</tr>\n";
echo "</thead>\n";
/* display day */
echo "<tr>\n<td class='tCol tColBg'>\n";
showHours();
echo "</td>";
$dayBg = '';
$curSeq = 0;
if (!empty($evtList[$opt['cD']])) { //check day background should be set
	foreach ($evtList[$opt['cD']] as $evt) {
		if (($evt['dbg'] & 2) and $evt['seq'] > $curSeq) {
			$dayBg = " style='background:{$evt['cbg']}'";
			$curSeq = $evt['seq'];
		}
	}
}
echo "<td class='wd0'{$dayBg}>\n";
showDay($opt['cD'],$xx['vws_events']);
echo "</td>\n</tr>\n</table>
</div>\n";
if ($usr['privs'] > 1) {
	echo "<script>dragTime()</script>\n";
}
?>
