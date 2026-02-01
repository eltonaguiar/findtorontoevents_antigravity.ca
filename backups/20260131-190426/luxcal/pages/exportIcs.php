<?php
/*
= iCal event file export script =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$adminLang = (file_exists("./lang/ai-{$opt['cL']}.php")) ? $opt['cL'] : "english";
require "./lang/ai-{$adminLang}.php";

$fileName = $_POST['fileName'] ?? ''; //file name
$fileDes = strip_tags($_POST['fileDes'] ?? ''); //file description
$usrName = $_POST['usrName'] ?? ''; //user filter
$catName = $_POST['catName'] ?? ''; //category filter
$fromDda = (isset($_POST['fromDda'])) ? DDtoID($_POST['fromDda']) : ''; //from event due date
$fromMda = (isset($_POST['fromMda'])) ? DDtoID($_POST['fromMda']) : ''; //from event modified date
$tillDda = (isset($_POST['tillDda'])) ? DDtoID($_POST['tillDda']) : ''; //untill event due date
$tillMda = (isset($_POST['tillMda'])) ? DDtoID($_POST['tillMda']) : ''; //untill event modified date

$meta = []; //iCal meta data
$calProps = ["PRODID","VERSION"]; //iCal properties and components of interest


/* sub-functions */

function catList($selCat) {
	global $ax;
	$stH = dbQuery("SELECT `name`,`color`,`bgColor` FROM `categories` WHERE `status` >= 0 ORDER BY `sequence`");
	echo "<option value='*'>{$ax['iex_all_cats']}&nbsp;</option>\n";
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		$selected = ($selCat == $row['name']) ? ' selected' : '';
		$catColor = ($row['color'] ? "color:{$row['color']};" : '').($row['bgColor'] ? "background-color:{$row['bgColor']};" : '');
		echo "<option value=\"{$row['name']}\"".($catColor ? " style='{$catColor}'" : '')."{$selected}>{$row['name']}</option>\n";
	}
}

function userMenu($selUser) {
	global $ax;
	$stH = dbQuery("SELECT `name` FROM `users` ORDER BY `name`");
	echo "<option value='*'>{$ax['iex_all_users']}&nbsp;</option>\n";
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		$selected = ($selUser == $row['name']) ? ' selected' : '';
		echo "<option value=\"{$row['name']}\"{$selected}>{$row['name']}</option>\n";
	}
}


/* main functions */

function selectEvents() {
	global $formCal, $ax, $set, $msg, $fileName, $fileDes, $usrName, $catName, $fromDda, $fromMda, $tillDda, $tillMda;
	
	if (!$fileName) {
		$fileName = substr(translit($set['calendarTitle'],true),0,60);
	}
	echo "<form action='index.php' method='post'>
{$formCal}
<fieldset><legend>{$ax['iex_create_ics']}</legend>
<table class='list'>
<tr><td class='label'>{$ax['iex_file_name']}:</td><td><input type='text' name='fileName' maxlength='60' value=\"{$fileName}\" size='26'> .ics</td></tr>
<tr><td class='label'>{$ax['iex_file_description']}:</td><td><input type='text' name='fileDes' value=\"{$fileDes}\" maxlength='50' size='30'></td></tr>
<tr><td colspan='2'><hr>\n</td></tr>
<tr><td colspan='2'>{$ax['iex_filters']}</td></tr>
<tr><td class='label'>{$ax['iex_owner']}:</td><td><select name='usrName' >\n";
	userMenu($usrName);
	echo "</select></td></tr>\n<tr><td class='label'>{$ax['iex_category']}:</td><td><select name='catName' >\n";
	catList($catName);
	echo "</select></td></tr>\n";
	$pholdD = IDtoDD('yyyy-mm-dd'); //make date place holder
	echo "<tr><td class='label'>{$ax['iex_between_dates']}:</td><td>
<input class='date' type='text' placeholder='{$pholdD}' name='fromDda' id='fromDda' value='".IDtoDD($fromDda)."'>
<span class='dtPick' title=\"{$ax['iex_select_start_date']}\" onclick='dPicker(1,``,`fromDda`); return false;'>&#x1F4C5;</span> &#8211;
<input class='date' type='text' placeholder='{$pholdD}' name='tillDda' id='tillDda' value='".IDtoDD($tillDda)."'>
<span class='dtPick' title=\"{$ax['iex_select_end_date']}\" onclick='dPicker(1,``,`tillDda`); return false;'>&#x1F4C5;</span></td></tr>
<tr><td class='label'>{$ax['iex_changed_between']}:</td><td>
<input class='date' type='text' placeholder='{$pholdD}' name='fromMda' id='fromMda' value='".IDtoDD($fromMda)."'>
<span class='dtPick' title=\"{$ax['iex_select_start_date']}\" onclick='dPicker(1,``,`fromMda`); return false;'>&#x1F4C5;</span> &#8211;
<input class='date' type='text' placeholder='{$pholdD}' name='tillMda' id='tillMda' value='".IDtoDD($tillMda)."'>
<span class='dtPick' title=\"{$ax['iex_select_end_date']}\" onclick='dPicker(1,``,`tillMda`); return false;'>&#x1F4C5;</span></td></tr>
</table>
</fieldset>
<button type='submit' name='create' value='y'>{$ax['iex_create_file']}</button>\n";
	if (isset($_POST['create']) and $msg == $ax['iex_file_created']) {
		$icalfName = $fileName ?: $set['calendarTitle'];
		$icalfName = substr(translit($icalfName,true).'.ics',0,60);
		$rName = str_replace('.','-'.date("Ymd-Hi").'.',$icalfName);
		echo "&emsp;<button type='button' onclick='location.href=`dloader.php?ftd=./files/{$icalfName}&amp;nwN={$rName}`;'>{$ax['iex_download_file']}</button>\n";
	}
	echo "</form>\n<div style='clear:right'></div>\n";
}

function makeFile() {
	global $ax, $nowTS, $evtList, $set, $fileName, $fileDes, $usrName, $catName, $fromDda, $fromMda, $tillDda, $tillMda;

	$icsHead = "BEGIN:VCALENDAR\r\n";
	$icsHead .= "PRODID:- // LuxCal ".LCV." // {$set['calendarTitle']} // EN\r\n";
	$icsHead .= "VERSION:2.0\r\n";
	$icsHead .= "CALSCALE:GREGORIAN\r\n";
	$icsHead .= "METHOD:PUBLISH\r\n";
	$icsHead .= "X-LC-CONTENT:\r\n";
	$icsHead .= " // user: ".(($usrName != '*') ? $usrName : "all")."\r\n";
	$icsHead .= " // cat: ".(($catName != '*') ? $catName : "all")."\r\n";
	$icsHead .= " // due: ".($fromDda ?: "begin")." - ".($tillDda ?: "end")."\r\n";
	$icsHead .= " // mod: ".($fromMda ?: "begin")." - ".($tillMda ?: "end")."\r\n";
	$icsHead .= "X-WR-CALNAME:".(($fileDes) ? htmlspecialchars_decode($fileDes,ENT_QUOTES) : "Events")."\r\n";
	$icsHead .= "X-WR-TIMEZONE:{$set['timeZone']}\r\n";

	//set event date range
	$sRange = $fromDda ?: date('Y-m-d',$nowTS-31536000); //-1 year
	$eRange = $tillDda ?: date('Y-m-d',$nowTS+31536000); //+1 year

	//set event filter
	$filter = $values = '';
	if ($usrName != '*') {
		$filter .= " AND u.`name` = ?";
		$values .= ','.$usrName;
	}
	if ($catName != '*') {
		$filter .= " AND c.`name` = ?";
		$values .= ','.$catName;
	}
	if ($fromMda) {
		$filter .= " AND SUBSTR(e.`mDateTime`,1,10) >= ?";
		$values .= ','.$fromMda;
	}
	if ($tillMda) {
		$filter .= " AND SUBSTR(e.`mDateTime`,1,10) <= ?";
		$values .= ','.$tillMda;
	}

	//retrieve events
	retrieve($sRange,$eRange,'',[$filter,substr($values,1)]);

	if (count($evtList) == 0) { return $ax['iex_no_events_found']; }

	$icsBody = '';
	$from = [',',';','<br>'];
	$to = ['\,','\;','\n'];
	$eidDone = []; //events processed
	foreach ($evtList as $evtListDate) {
		foreach ($evtListDate as $evt) {
			if (!in_array($evt['eid'], $eidDone)) { //event not yet processed
				$vDescription = str_replace($from,$to,htmlspecialchars_decode(makeE($evt,$set['evtTemplGen'],'br','\n','345'),ENT_QUOTES));
				$vDescription = chunk_split_unicode($vDescription,63,"\r\n "); //fold to 72 chars line length
				//compile DTSTART and DTEND values
				$dateS = str_replace('-','',$evt['sda']);
				$dateE = ($evt['eda'][0] != '9') ? str_replace('-','',$evt['eda']) : $dateS;
				$timeS = str_replace(':','',$evt['sti']);
				$timeE = str_replace(':','',$evt['eti']);
				if ($evt['ald']) { //all day
					$timeS = '0000';
					$dateE = date('Ymd',strtotime($dateE.'12:00:00') + 86400); //+1 day
				} else {
					$dateS .= 'T'.$timeS.'00';
					$dateE .= 'T'.(!empty($timeE) ? $timeE.'00' : $timeS.'01');
				}

				//compile RRULE property
				$rrule = '';
				if ($evt['r_t'] == 1) { //every 1|2|3|4 d|w|m|y
					$rrule .= "FREQ=";
					switch ($evt['r_p']) {
						case 1: $rrule .= 'DAILY'; break;
						case 2: $rrule .= 'WEEKLY'; break;
						case 3: $rrule .= 'MONTHLY'; break;
						case 4: $rrule .= 'YEARLY';
					}
					$rrule .= ";INTERVAL=".$evt['r_i'];
				}
				if ($evt['r_t'] == 2) { //every 1|2|3|4|5 m|t|w|t|f|s|s of the month
					$rrule .= $evt['r_m'] ? "FREQ=YEARLY" : "FREQ=MONTHLY";
					$rrule .= ";BYDAY=".(($evt['r_i'] != 5) ? $evt['r_i'] : '-1');
					switch ($evt['r_p']) {
						case 1: $rrule .= 'MO'; break;
						case 2: $rrule .= 'TU'; break;
						case 3: $rrule .= 'WE'; break;
						case 4: $rrule .= 'TH'; break;
						case 5: $rrule .= 'FR'; break;
						case 6: $rrule .= 'SA'; break;
						case 7: $rrule .= 'SU';
					}
					if ($evt['r_m']) {
						$rrule .= ";BYMONTH=".$evt['r_m'];
					}
				}
				if ($evt['r_u'][0] != '9') {
					$rrule .= ";UNTIL=".str_replace('-','',$evt['r_u']).'T235900';
				}
				$tStamp = mktime((int)substr($timeS,0,2),(int)substr($timeS,2,2),0,(int)substr($dateS,4,2),(int)substr($dateS,6,2),(int)substr($dateS,0,4));
				$icsBody .= "BEGIN:VEVENT\r\n";
				$icsBody .= "DTSTART;".($evt['ald'] ? "VALUE=DATE" : "TZID=".date_default_timezone_get()).":{$dateS}\r\n";
				$icsBody .= "DTEND;".($evt['ald'] ? "VALUE=DATE" : "TZID=".date_default_timezone_get()).":{$dateE}\r\n"; //+1 ?
				$icsBody .= "DTSTAMP:".gmdate('Ymd\THis\Z')."\r\n";
				if ($evt['adt']) {
					$icsBody .= "CREATED:".gmdate('Ymd\THis\Z',strtotime($evt['adt']))."\r\n";
				}
				if ($evt['mdt']) {
					$icsBody .= "LAST-MODIFIED:".gmdate('Ymd\THis\Z',strtotime($evt['mdt']) + 86400)."\r\n";
				}
				$calUrlShort = preg_match('~.+://([^?/]+)~',$set['calendarUrl'],$matches); //strip http(s)://20150301T010000ZStar-LuxCal@lcl.luxsoft.eu
				$icsBody .= "UID:".gmdate("Ymd\THis\Z", $tStamp).trim(substr(iconv('UTF-8','ASCII//TRANSLIT//IGNORE',$evt['tit']),0,4))."-LuxCal@{$matches[1]}\r\n";
				$icsBody .= "SUMMARY:".str_replace(",","\,",htmlspecialchars_decode($evt['tit'],ENT_QUOTES))."\r\n";
				if ($vDescription) { $icsBody .= "DESCRIPTION:{$vDescription}\r\n"; }
				$icsBody .= "CATEGORIES:".str_replace(",","\,",$evt['cnm'])."\r\n";
				if ($evt['pri']) { $icsBody .= "CLASS:PRIVATE\r\n"; }
				if ($evt['ven']) { $icsBody .= "LOCATION:".str_replace([",","!"],["\,",""],htmlspecialchars_decode($evt['ven'],ENT_QUOTES))."\r\n"; }
				if ($rrule) { $icsBody .= "RRULE:{$rrule}\r\n"; }
				$icsBody .= "END:VEVENT\r\n";
				$eidDone[] = $evt['eid']; //mark as processed
			}
		}
	}
	$icsTail = "END:VCALENDAR";
	//save to iCal file
	$icalfName = $fileName ?: $set['calendarTitle'];
	$icalfName = translit($icalfName,true);
	if (file_put_contents("./files/{$icalfName}.ics", $icsHead.$icsBody.$icsTail, LOCK_EX) !== false) {
		$result = $ax['iex_file_created'];
	} else {
		$result = $ax['iex_write error'];
	}
	return $result;
}

//control logic
$msg = ''; //init
if ($usr['privs'] == 9) { //admin
	if (isset($_POST['create'])) {
		$msg = makeFile();
	}
	echo $msg ? "<p class='error'>{$msg}</p>\n" : "<p>&nbsp;</p>\n";
	echo "<aside class='aside sBoxAd'>{$ax['xpl_export_ical']}</aside>\n";
	echo "<div class='centerBox sBoxAd'>\n";
	selectEvents();
	echo "</div>\n";
} else {
	echo "<p class='error'>{$ax['no_way']}</p>\n";
}
?>
