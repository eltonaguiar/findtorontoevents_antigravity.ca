<?php
/*
= view calendar changes (added / edited / deleted events) since specified date =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

require './common/retrievc.php';

function showEvents(&$events,$date) {
	global $set, $usr, $xx, $templ;
	
	echo "<table>\n<colgroup><col class='col1'><col class='col2'></colgroup>\n";
	foreach ($events as $evt) {
		$repTxt = repeatText($evt['r_t'],$evt['r_i'],$evt['r_p'],$evt['r_m'],$evt['r_u']); //make repeat text
		$dateTime = makeFullDT(true,$evt['sda'],$evt['eda'],$evt['sti'],$evt['eti'],$evt['ald']); //make full date/time
		if ($repTxt) { $dateTime .= " ({$repTxt})\n"; } //add repeat text
		$eStyle = colorStyle($evt); //get event colors
		$eStyle = $eStyle ? " style='{$eStyle}'" : '';
		$toAppr = ($evt['app'] and !$evt['apd']) ? ' toAppr' : '';
		$age = ($evt['rpt'] == 4 and preg_match('%\(((?:19|20)\d\d)\)%',$evt['tx1'],$year)) ? ' ('.strval(substr($date,0,4) - $year[1]).')' : '';
		echo "<tr>\n<td class='line1'>".(($evt['sts'] < 0) ? $xx['chg_deleted'] : ($evt['mdt'] > $evt['adt'] ? $xx['chg_edited'] : $xx['chg_added']))."</td>\n";
		echo "<td class='line1 eBox{$toAppr}'>{$dateTime}";
		if ($evt['sts'] >= 0 and ($templ['pop'] or $evt['mayE'])) {
			$click = ($evt['mayE'] ? 'editE' : 'showE')."({$evt['eid']},`{$date}`)";
			$title = $evt['mayE'] ? $xx['vws_edit_event'] : ($templ['pop'] ? $xx['vws_see_event'] : '');
			echo "<div class='evtTitle bold'{$eStyle} onclick='{$click};' title=\"{$title}\">{$evt['tix']}{$age}</div>\n";
		} else {
			echo "<div class='evtTitle bold'{$eStyle}>{$evt['tix']}{$age}</div>\n";
		}
		if ($templ['gen']) {
			echo makeE($evt,$templ['gen'],'bx',"<br>\n")."\n";
		}
		echo "</td>\n</tr>\n";
	}
	echo "</table>\n<br>\n";
}

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//main program
$evtList = [];
$fromD = (isset($_POST['fromD'])) ? DDtoID($_POST['fromD']) : $today;
$fromD = min($fromD,$today);

//display header
echo "<div class='subHead'>
<form id='selectD' name='selectD' action='index.php' method='post'>{$xx['from']}: 
<input class='date' type='text' id='fromD' name='fromD' value='".IDtoDD($fromD)."'>
<span class='dtPick noPrint' title=\"{$xx['chg_select_date']}\" onclick='dPicker(0,`selectD`,`fromD`); return false;'>&#x1F4C5;</span>";
if ($fromD != $today) {
	echo "&emsp;{$xx['to']} ".makeD($today,2)."\n";
}
echo "</form>
</div>\n";

// retrieve changed events
grabChanges($fromD,0); //query db for changes

//display changes
echo "<div".($winXS ? '' : " class='scrollBox sBoxCh'").">\n";
if ($evtList) {
	foreach($evtList as $date => &$events) {
		if ($events) {
			echo "<fieldset class='list'>\n<legend>{$xx['chg_changed_on']} ".makeD($date,5)."</legend>\n";
			showEvents($events,$date);
			echo "</fieldset>";
		}
	}
} else {
	echo "<div class='floatC'>{$xx['chg_no_changes']}</div>\n";
}
echo "</div>\n<br>";
?>
