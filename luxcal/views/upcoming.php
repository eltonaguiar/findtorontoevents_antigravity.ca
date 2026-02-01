<?php
/*
= upcoming events view =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

function showEvents(&$events,$date) {
	global $set, $usr, $templ, $hoverBox, $xx, $upcoTxt, $upcoCsv;
	
	echo "<table>\n<colgroup><col class='col1'><col></colgroup>\n";
	foreach ($events as $evt) {
		$eStyle = colorStyle($evt); //get event colors
		$eStyle = $eStyle ? " style='{$eStyle}'" : '';
		$chBox = $evt['cbx'] ? checkBox($evt,$date) : '';
		$popAttr = $hoverBox ? makePopAttrib($evt,$date,'?') : '';
		$toAppr = ($evt['app'] and !$evt['apd']) ? ' toAppr' : '';
		$time = makeHovT($evt);
		$age = ($evt['rpt'] == 4 and preg_match('%\(((?:19|20)\d\d)\)%',$evt['tx1'],$year)) ? ' ('.strval(substr($date,0,4) - $year[1]).')' : '';
		echo "<tr>\n<td>{$time}</td>\n<td class='eBox{$toAppr}'>";
		if ($templ['pop'] or $evt['mayE']) {
			$click = ($evt['mayE'] ? 'editE' : 'showE')."({$evt['eid']},`{$date}`)";
			$title = $evt['mayE'] ? $xx['vws_edit_event'] : ($templ['pop'] ? $xx['vws_see_event'] : '');
			echo "<div class='evtTitle bold'>{$chBox}<span{$eStyle} onclick='{$click};'{$popAttr} title=\"{$title}\">{$evt['tix']}{$age}</span></div>\n";
			echo makeE($evt,$templ['upc'],'bx',"<br>")."\n";
		} else {
			echo "<div class='evtTitle bold'>{$chBox}<span{$eStyle}{$popAttr}>{$evt['tix']}{$age}</span></div>\n";
		}
		echo "</td>\n</tr>\n";
		//download file - add event
		$time = str_replace(["&middot;","&bull;"],".",$time);
		$time = preg_replace("~^\.{3,4}$~","All day",$time);
		$upcoTxt .= "\n".($time ? $time."\n" : '').html_entity_decode($evt['tix'],ENT_QUOTES)."{$age}\n"; //text version
		$upcoCsv .= "{$date} | {$time} | ".html_entity_decode($evt['tix'],ENT_QUOTES)."{$age} | "; //CSV version
		if ($templ['upc']) {
			$upcoTxt .= str_replace("<br>","\n",html_entity_decode(makeE($evt,$templ['upc'],'br',"\n"),ENT_QUOTES))."\n"; //text version
			$upcoCsv .= html_entity_decode(makeE($evt,$templ['upc'],'csv'," | ","12345"),ENT_QUOTES)."\n"; //CSV version
		}
	}
	echo "</table>\n<br>\n";
}

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$evtList = [];
$hoverBox = array_diff(str_split($set['evtTemplPop']),str_split($set['evtTemplUpc'])); //if pop > upc display hover box
$fromD = isset($_POST['fromD']) ? DDtoID($_POST['fromD']) : $today;
if (isset($_POST['tillD'])) {
	$tillD = DDtoID($_POST['tillD']);
} else {
	$tillU = strtotime($fromD.' 12:00:00') + (($set['lookaheadDays']-1) * 86400); //Unix time of end date
	$tillD = date("Y-m-d", $tillU);
}
$rName = str_replace(' ','_',$set['calendarTitle'])."_{$fromD}-{$tillD}";

//display header
echo "<div class='subHead'>
<form class='inline' id='selectD' method='post'>
{$xx['from']}: <input class='date' type='text' id='fromD' name='fromD' value='".IDtoDD($fromD)."'>
<span class='dtPick noPrint' title=\"{$xx['chg_select_date']}\" onclick='dPicker(0,`selectD`,`fromD`); return false;'>&#x1F4C5;</span>&emsp;
{$xx['to']}: <input class='date' type='text' id='tillD' name='tillD' value='".IDtoDD($tillD)."'>
<span class='dtPick noPrint' title=\"{$xx['chg_select_date']}\" onclick='dPicker(0,`selectD`,`tillD`); return false;'>&#x1F4C5;</span>
</form>\n";
if (!$winXS) {
	echo "&emsp;
<button type='button' title='{$xx['vws_download_title']}' onclick='location.href=`dloader.php?ftd=./files/upco.txt&amp;nwN={$rName}.txt`;'>{$xx['vws_download']} (txt)</button>&emsp;
<button type='button' title='{$xx['vws_download_title']}' onclick='location.href=`dloader.php?ftd=./files/upco.csv&amp;nwN={$rName}.csv`;'>{$xx['vws_download']} (csv)</button>\n";
}
echo "</div>\n";

//header down-loadable text file
$upcoTxt = "";
$upcoCsv = "Date | Time | Title | Venue | Category | Description | Xfield 1 | Xfield 2\n";

//retrieve events
retrieve($fromD,$tillD,'guc');

//display upcoming events
echo "<div".($winXS ? '' : " class='scrollBox sBoxUp'").">\n";
if ($evtList) {
	foreach($evtList as $date => &$events) {
		if ($events) {
			$evtDate = makeD($date,5);
			$upcoTxt .= "\n{$evtDate}\n".str_repeat('-',strlen($evtDate)); //text version - new date
			echo "<fieldset class='list'>\n<legend>{$evtDate}</legend>\n";
			showEvents($events,$date);
			echo "</fieldset>\n";
		}
	}
} else {
	echo "<div class='floatC'>{$xx['none']}</div>\n";
}
echo "</div>\n";
file_put_contents("./files/upco.txt",$upcoTxt,LOCK_EX); //save upco text file
file_put_contents("./files/upco.csv",$upcoCsv,LOCK_EX); //save upco csv file
?>
<script>
$I('selectD').addEventListener("keypress", function(event) {
  if (event.key === "Enter") {
    event.preventDefault();
    $I('selectD').submit();
  }
});
</script>
