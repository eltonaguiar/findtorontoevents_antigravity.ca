<?php
/*
= text search script =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$schText = $_POST["schText"] ?? ""; //search text
$eF = $_POST['eF'] ?? [0]; //field filter
$grpName = $_POST["grpName"] ?? ""; //group filter
$catName = $_POST["catName"] ?? ""; //category filter
$fromDda = (isset($_POST["fromDda"])) ? DDtoID($_POST["fromDda"]) : ""; //from event due date
$tillDda = (isset($_POST["tillDda"])) ? DDtoID($_POST["tillDda"]) : ""; //until event due date
if ($usr['privs'] < $set['xField1Rights']) { $templ['gen'] = str_replace('4','',$templ['gen']); } //exclude xField 1
if ($usr['privs'] < $set['xField2Rights']) { $templ['gen'] = str_replace('5','',$templ['gen']); } //exclude xField 2


/* functions */
function groupList($selGrp) {
	global $xx;
	
	$stH = dbQuery("SELECT `ID`,`name`,`color` FROM `groups` WHERE `status` >= 0 ORDER BY `name`");
	echo "<option value='*'>{$xx['sch_all_groups']}&nbsp;</option>\n";
	while (list($ID,$name,$color) = $stH->fetch(PDO::FETCH_NUM)) {
		$selected = ($selGrp == $name) ? ' selected' : '';
		echo "<option value='{$name}'".($color ? " style='background-color:{$color};'" : '')."{$selected}>{$name}</option>\n";
	}
}

function catList($selCat) {
	global $xx, $usr;
	
	$where = 'WHERE `status` >= 0'.($usr['vCats'] != '0' ? " AND `ID` IN ({$usr['vCats']})" : '');
	$stH = dbQuery("SELECT `ID`,`name`,`color`,`bgColor` FROM `categories` {$where} ORDER BY `sequence`");
	echo "<option value='*'>{$xx['sch_all_cats']}&nbsp;</option>\n";
	while (list($ID,$name,$color,$bgColor) = $stH->fetch(PDO::FETCH_NUM)) {
		$selected = ($selCat == $name) ? ' selected' : '';
		$catColor = ($color ? "color:{$color};" : '').($bgColor ? "background-color:{$bgColor};" : '');
		echo "<option value=\"{$name}\"".($catColor ? " style='{$catColor}'" : '')."{$selected}>{$name}</option>\n";
	}
}

function searchForm() {
	global $xx, $set, $templ, $schText, $eF, $grpName, $catName, $fromDda, $tillDda;
	
	echo "<form action='index.php' method='post'>
<fieldset><legend>{$xx['sch_define_search']}</legend>\n
<table class='list'>\n
<tr>\n<td class='label'>{$xx['sch_search_text']}:</td>
<td><input type='text' name='schText' id='schText' value=\"{$schText}\" maxlength='50' size='30'></td>\n</tr>
<tr><td colspan='2'><hr></td></tr>
<tr>\n<td class='label'>{$xx['sch_event_fields']}:</td>
<td><label><input type='checkbox' name='eF[]' value='0' onclick='check0(`eF`);'".(in_array(0, $eF) ? " checked" : '')."> 
{$xx['sch_all_fields']}</label></td>\n</tr>
<tr>\n<td></td><td><label><input type='checkbox' name='eF[]' value='1' onclick='checkN(`eF`);'".(in_array(1, $eF) ? " checked" : '')."> 
{$xx['sch_title']}</label></td>\n</tr>\n";
	foreach (str_split($templ['gen']) as $fieldNr) {
		if (strpos('1345',$fieldNr) !== false) {
			switch ($fieldNr) {
			case '1': 
				echo "<tr>\n<td></td><td><label><input type='checkbox' name='eF[]' value='2' onclick='checkN(`eF`);'".(in_array(2, $eF) ? " checked" : '')."> {$xx['sch_venue']}</label></td>\n</tr>\n";
				break;
			case '3':
				echo "<tr>\n<td></td><td><label><input type='checkbox' name='eF[]' value='3' onclick='checkN(`eF`);'".(in_array(3, $eF) ? " checked" : '')."> {$xx['sch_description']}</label></td>\n</tr>\n";
				break;
			case '4':
				echo "<tr>\n<td></td><td><label><input type='checkbox' name='eF[]' value='4' onclick='checkN(`eF`);'".(in_array(4, $eF) ? " checked" : '')."> ".($set['xField1Label'] ?: $xx['sch_extra_field1'])."</label></td>\n</tr>\n";
				break;
			case '5':
				echo "<tr>\n<td></td><td><label><input type='checkbox' name='eF[]' value='5' onclick='checkN(`eF`);'".(in_array(5, $eF) ? " checked" : '')."> ".($set['xField2Label'] ?: $xx['sch_extra_field2'])."</label></td>\n</tr>\n";
			}
		}
	}
	echo "<tr><td class='label'>{$xx['sch_user_group']}:</td><td><select name='grpName'>\n";
	groupList($grpName);
	echo "</select></td></tr>\n";
	echo "<tr><td class='label'>{$xx['sch_event_cat']}:</td><td><select name='catName'>\n";
	catList($catName);
	echo "</select></td></tr>\n";
	$pholdD = IDtoDD('yyyy-mm-dd'); //make date place holder
	echo "<tr>\n<td class='label'>{$xx['sch_occurring_between']}:</td><td>
<input class='date' type='text' placeholder='{$pholdD}' name='fromDda' id='fromDda' value='".IDtoDD($fromDda)."'>
<span class='dtPick' title=\"{$xx['sch_select_start_date']}\" onclick='dPicker(1,``,`fromDda`); return false;'>&#x1F4C5;</span> &#8211;
<input class='date' type='text' placeholder='{$pholdD}' name='tillDda' id='tillDda' value='".IDtoDD($tillDda)."'>
<span class='dtPick' title=\"{$xx['sch_select_end_date']}\" onclick='dPicker(1,``,`tillDda`); return false;'>&#x1F4C5;</span></td>\n</tr>
</table>\n
</fieldset>
<button type='submit' name='search' value='y'>{$xx['sch_search']}</button>\n
</form>
<div style='clear:right'></div>\n
<script>document.getElementById('schText').focus();</script>";
}

function validateForm() {
	global $xx, $schText, $fromDda, $tillDda;
	
	$schText = trim(str_replace('%', '', $schText),'&');
	if (strlen(str_replace(['*','?'], '', $schText)) < 1) { return $xx['sch_invalid_search_text']; }
	if ($fromDda === false) { return $xx['sch_bad_start_date']; }
	if ($tillDda === false) { return $xx['sch_bad_end_date']; }
	if ($fromDda and $tillDda and $fromDda > $tillDda) { return $xx['evt_end_before_start_date']; }
	//valid
	$schText = htmlspecialchars($schText,ENT_QUOTES); //convert " and ' to HTML entities
	return '';
}

function searchText() {
	global $xx, $set, $templ, $nowTS, $schText, $eF, $grpName, $catName, $fromDda, $tillDda;

	//set event date range
	$sDate = $fromDda ?: date('Y-m-d',$nowTS-86400*$set['searchBackDays']);
	$eDate = $tillDda ?: date('Y-m-d',$nowTS+86400*$set['searchAheadDays']);

	//set event filter
	$schString = strtoupper(str_replace(['*','?'], ['%','_'], "%{$schText}%"));
	//prepare description filter
	$filter = $values = '';
	if ($grpName != '*') {
		$filter .= " AND g.`name` = ?";
		$values .= ','.str_replace("'","''",$grpName);
	}
	if ($catName != '*') {
		$filter .= " AND c.`name` = ?";
		$values .= ','.str_replace("'","''",$catName);
	}
	$filter .= " AND (";
	if (in_array(0, $eF) or in_array(1, $eF)) { //title
		$filter .= "UPPER(e.`title`) LIKE ?";
		$values .= ','."%{$schString}%";
	}
	if (in_array(0, $eF) or in_array(2, $eF)) { //venue
		$filter .= ((substr($filter, -1) == '(') ? '' : ' OR ')."UPPER(e.`venue`) LIKE ?";
		$values .= ','."%{$schString}%";
	}
	if (in_array(0, $eF) or in_array(3, $eF)) { //text field 1
		$filter .= ((substr($filter, -1) == '(') ? '' : ' OR ')."UPPER(e.`text1`) LIKE ?";
		$values .= ','."%{$schString}%";
		}
	if (in_array(0, $eF) or in_array(4, $eF)) { //text field 2
		$filter .= ((substr($filter, -1) == '(') ? '' : ' OR ')."UPPER(e.`text2`) LIKE ?";
		$values .= ','."%{$schString}%";
	}
	if (in_array(0, $eF) or in_array(5, $eF)) { //text field 3
		$filter .= ((substr($filter, -1) == '(') ? '' : ' OR ')."UPPER(e.`text3`) LIKE ?";
		$values .= ','."%{$schString}%";
	}
	$filter .= ")";

	retrieve($sDate,$eDate,'',[$filter,substr($values,1)]); //retrieve events

	//display header
	$fields = '';
	if (in_array(0, $eF) or in_array(1, $eF)) { $fields = ' + '.$xx['sch_title']; }
	foreach (str_split($templ['gen']) as $fieldNr) {
		if (strpos('1345',$fieldNr) !== false) {
			switch ($fieldNr) {
			case '1': 
				if (in_array(0, $eF) or in_array(2, $eF)) { $fields .= ' + '.$xx['sch_venue']; } break;
			case '3':
				if (in_array(0, $eF) or in_array(3, $eF)) { $fields .= ' + '.$xx['sch_description']; } break;
			case '4':
				if (in_array(0, $eF) or in_array(4, $eF)) { $fields .= ' + '.($set['xField1Label'] ?: $xx['sch_extra_field1']); } break;
			case '5':
				if (in_array(0, $eF) or in_array(5, $eF)) { $fields .= ' + '.($set['xField2Label'] ?: $xx['sch_extra_field2']); }
			}
		}
	}
	$fields = substr($fields,3);

	echo "<div class='subHead'>
<form id='event' name='event' action='index.php' method='post'>
<input type='hidden' name='schText' value=\"{$schText}\">\n";
	foreach ($eF as $key => $value) { echo "<input type='hidden' name='eF[]' value=\"{$value}\">\n";	}
	echo "<input type='hidden' name='grpName' value=\"{$grpName}\">
<input type='hidden' name='catName' value=\"{$catName}\">
<input type='hidden' name='fromDda' value='".IDtoDD($fromDda)."'>
<input type='hidden' name='tillDda' value='".IDtoDD($tillDda)."'>
<div class='floatC'><button type='submit' name='newSearch' value='y'>{$xx['sch_new_search']}</button></div>
</form>
{$xx['sch_search_text']}: <b>{$schText}</b><br>
{$xx['sch_event_fields']}: <b>{$fields}</b><br>
{$xx['sch_user_group']}: <b>".($grpName != '*' ? $grpName : $xx['sch_all_groups'])."</b><br>
{$xx['sch_event_cat']}: <b>".($catName != '*' ? $catName : $xx['sch_all_cats'])."</b><br>
{$xx['sch_occurring_between']}: <b>".makeD($sDate,2)." - ".makeD($eDate,2)."</b>
</div>\n";
}

function showMatches($eType) { //eType (0: normal, 1: mde, 2: recurring)
	global $usr, $set, $xx, $evtList, $templ, $schText;

	//display matching events
	$match = '%('.str_replace(['?','*'],['.','[^<>]+?'],$schText).')(?![^<]*>)%i'; //convert to regex (?!: neg.look-ahead condition)
	$evtDone = [];
	echo "<table>\n<colgroup><col class='col1'><col></colgroup>\n";
	foreach($evtList as $date => &$events) {
		foreach ($events as $evt) {
			if ($eType == 0) {
				if ($evt['mde'] or $evt['r_t']) { continue; } //mde or rec event
				$evtDate = "<a href='javascript:index({cP:2,cD:`{$date}`})' title=\"{$xx['sch_calendar']}\">".makeD($date,5)."</a>";
			} elseif ($eType == 1) {
				if (!$evt['mde'] or in_array($evt['eid'],$evtDone)) { continue; } //!mde or mde processed
				$evtDate = "<a href='javascript:index({cP:2,cD:`{$date}`})' title=\"{$xx['sch_calendar']}\">".makeD($evt['sda'],5)." - ".makeD($evt['eda'],5)."</a>";
			} elseif ($eType == 2) {
				if (!$evt['r_t'] or in_array($evt['eid'],$evtDone)) { continue; } //!rec or rec processed
				$evtDate = "<a href='javascript:index({cP:2,cD:`{$date}`});' title=\"{$xx['sch_calendar']}\">".makeD($date,5).' - '.repeatText($evt['r_t'],$evt['r_i'],$evt['r_p'],$evt['r_m'],$evt['r_u'])."</a>";
			}
			$evtDone[] = $evt['eid'];
			$evtTime = makeTime($evt['ald'],0,0,$evt['sti'],$evt['eti']);
			$eStyle = colorStyle($evt); //get event colors
			$eStyle = $eStyle ? " style=\"{$eStyle}\"" : '';
			$chBox = $evt['cbx'] ? checkBox($evt,$date,'?') : '';
			$toAppr = ($evt['app'] and !$evt['apd']) ? ' toAppr' : '';
			echo "<tr>\n<td colspan='2' class='line1 bold'>{$evtDate}</td>\n</tr>\n";
			echo "<tr>\n<td>{$evtTime}</td>\n";
			echo "<td class='eBox{$toAppr}'>";
			$eTitle = preg_replace($match, '<mark>$1</mark>',$evt['tit']);
			if ($templ['gen'] or $evt['mayE']) {
				$click = ($evt['mayE'] ? 'editE' : 'showE')."({$evt['eid']},`{$date}`)";
				echo "<div class='evtTitle bold'>{$chBox}<span{$eStyle} onclick='{$click};'>".$eTitle."</span></div>\n";
				echo preg_replace($match, '<mark>$1</mark>',makeE($evt,$templ['gen'],'bx',"<br>\n"))."\n";
			} else {
				echo "<div class='evtTitle bold'>{$chBox}<span{$eStyle}>".$eTitle."</span></div>\n";
			}
			echo "</td>\n</tr>\n";
		}
	}
	echo "</table><br>\n";
	if (empty($evtDone)) {
		echo $xx['none'];
	}
}

//control logic

$msg = ''; //init
if (isset($_POST["search"])) {
	$msg = validateForm();
}
echo $msg ? "<p class='error'>{$msg}</p>\n" : "<p>&nbsp;</p>\n";
if (isset($_POST["search"]) and !$msg) {
	searchText(); //search
	if ($evtList) {
		$evtTypes = [$xx['sch_sd_events'],$xx['sch_md_events'],$xx['sch_rc_events']];
		foreach($evtTypes as $k => $evtType) {
			echo "<fieldset class='list sBoxTs'>\n<legend>{$evtType}</legend>\n";
			showMatches($k); //show results single-day events
			echo "</fieldset>\n";
		}
	} else {
		echo "<div class='floatC'>{$xx['sch_no_results']}</div>\n";
	}
} else {
	echo "<aside class='aside sBoxTs'>\n".str_replace(['$1','$2'],[$set['searchBackDays'],$set['searchAheadDays']],$xx['sch_instructions'])."\n</aside>\n";
	echo "<div class='centerBox sBoxTs'>\n";
	searchForm(); //define search
	echo "</div>\n";
}
?>
