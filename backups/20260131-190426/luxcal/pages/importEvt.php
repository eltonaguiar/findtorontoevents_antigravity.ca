<?php
/*
= CSV event file import script =

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

$delimiter = $_POST['delimiter'] ?? ',';
$birthdayID = $_POST['birthdayID'] ?? '';
$dFormat = $_POST['dFormat'] ?? 'y-m-d';
$tFormat = $_POST['tFormat'] ?? 'h:m';

/* sub-functions */

function processEvtFields(&$sDate,&$eDate,&$sTime,&$eTime,&$title,&$catID) {
	global $dFormat, $tFormat;
	
	//Get calendar category ids
	$catIDs = [];
	$stH = dbQuery("SELECT `ID` FROM `categories` WHERE `status` >= 0");
 	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		$catIDs[] = $row['ID'];
	}
	//Processing
	$errors = 0;
	$nofDates = count($sDate);
	for ($i = 0; $i < $nofDates; $i++) {
		$error = 0;
		if (($IsDate = DDtoID($sDate[$i],$dFormat)) === false) { $error++; }
		if (($IeDate = DDtoID($eDate[$i],$dFormat)) === false) { $error++; }
		if (($IsTime = DTtoIT($sTime[$i],$tFormat)) === false) { $error++; }
		if (($IeTime = DTtoIT($eTime[$i],$tFormat)) === false) { $error++; }
		if (!$error) {
			if ($eDate[$i]) {
				if ($IsDate == $IeDate) { $eDate[$i] = ''; }
				elseif ($IeDate < $IsDate) {
					list($sDate[$i],$eDate[$i]) = [$eDate[$i],$sDate[$i]]; //swap start and end date
				} elseif ($IeDate > $IsDate and !$IsTime and !$IeTime) { //all day
					$eDate[$i] = IDtoDD(date("Y-m-d",strtotime($IeDate.' 12:00:00') - 86400),$dFormat); //-1 day
				}
			}
			if (!$sTime[$i] and $eTime[$i]) { $sTime[$i] = $eTime[$i]; }
			if ($sTime[$i] == $eTime[$i]) { $eTime[$i] = ''; }
			if ($eTime[$i]) {
				if ($IeTime < $IsTime) {
					list($sTime[$i],$eTime[$i]) = [$eTime[$i],$sTime[$i]]; //swap start and end time
				}
			}
		}
		$errors += $error;
		if (!$title[$i]) { $errors++; } //title empty
		if (!in_array($catID[$i], $catIDs)) { $catID[$i] = 0; } //reset non-existing category IDs
	}
return $errors;
}


/* main-functions */

function instructions() {
	global $ax;
	
	$stH = dbQuery("SELECT `ID`,`name` FROM `categories` WHERE `status` >= 0 ORDER BY `ID`");
	echo "<aside class='aside sBoxAd'>\n{$ax['xpl_import_csv']}
		<table class='list'>
		<tr><th style='width:auto;'>ID</th><th style='width:auto;'>{$ax['iex_category']}</th></tr>\n";
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		echo "<tr><td class='floatC'>{$row['ID']}</td><td>&nbsp;{$row['name']}</td></tr>\n";
	}
	echo "</table>\n</aside>\n";
}

function uploadFile() {
	global $formCal, $ax, $delimiter, $birthdayID, $dFormat, $tFormat;
	
	echo "<form action='index.php' method='post' enctype='multipart/form-data'>
{$formCal}
<input type='hidden' name='MAX_FILE_SIZE' value='1000000'>
<fieldset><legend>{$ax['iex_upload_csv']}</legend>
<table class='list'>
<tr><td class='label'>{$ax['iex_file']}:</td><td><input type='file' name='fileName'></td></tr>
<tr><td class='label'>{$ax['iex_fields_sep_by']}:</td><td><input type='text' name='delimiter' value='{$delimiter}' maxlength='2' size='1'></td></tr>
<tr><td class='label'>{$ax['iex_birthday_cat_id']}:</td><td><input type='text' name='birthdayID' maxlength='2' value='{$birthdayID}' size='1'> ({$ax['iex_see_insert']})</td></tr>
<tr><td class='label'>{$ax['iex_date_format']}:</td><td>
<label><input type='radio' name='dFormat' value='d-m-y'".($dFormat == 'd-m-y' ? " checked" : '').">{$ax['dd_mm_yyyy']}</label>&emsp;
<label><input type='radio' name='dFormat' value='m-d-y'".($dFormat == 'm-d-y' ? " checked" : '').">{$ax['mm_dd_yyyy']}</label>&emsp;
<label><input type='radio' name='dFormat' value='y-m-d'".($dFormat == 'y-m-d' ? " checked" : '').">{$ax['yyyy_mm_dd']}</label></td></tr>
<tr><td class='label'>{$ax['iex_time_format']}:</td><td>
<label><input type='radio' name='tFormat' value='h:ma'".($tFormat == 'h:ma' ? " checked" : '').">{$ax['time_format_us']}</label>&emsp;
<label><input type='radio' name='tFormat' value='h:m'".($tFormat == 'h:m' ? " checked" : '').">{$ax['time_format_eu']}</label></td></tr>
</table>
</fieldset>
<button type='submit' name='uploadFile' value='y'>{$ax['iex_upload_file']}</button>
</form>
<div style='clear:right'></div>\n";
}

function processUpload() {
	global $ax, $tFormat;
	
	$fileName = $_FILES['fileName']['tmp_name'];
	if (!$fileName) { return $ax['iex_no_file_name']; } //csv file missing
	$csvArray = file($fileName, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
	unlink($fileName); //release file
 	$lineNr = 0;
	//process events from CSV array
	foreach ($csvArray as $csvEvent) {
		$csvEvent = strip_tags(html_entity_decode($csvEvent),'<a><b><i><u><s><br><img>'); //remove unwanted html tags
		$csvFields = str_getcsv($csvEvent, $_POST['delimiter']); //get csv fields
		foreach ($csvFields as $key => $dum) { $csvFields[$key] = trim($csvFields[$key],' "\''); } //remove blanks & quotes
		$lineNr++;
		if ((!empty($csvFields[2]) and !ctype_digit($csvFields[2])) and $lineNr = 1) { continue; } //flush header line
		if (empty($csvFields[0])) { continue; } //flush events without title
		if (empty($csvFields[3]) or count($csvFields) < 4) { //fields empty or too few fields
			return "{$ax['iex_csv_file_error_on_line']}: {$lineNr}";
		}
		array_push($csvFields,'','','',''); //pad to ensure 8 fields
		list($title, $venue, $cat, $sDate, $eDate, $sTime, $eTime, $desc) = $csvFields;
		$_POST['title'][] = $title;
		$_POST['venue'][] = $venue;
		$_POST['catID'][] = $cat;
		$_POST['sDate'][] = $sDate;
		$_POST['eDate'][] = $eDate;
		$_POST['sTime'][] = preg_replace('~(\d\d?:\d\d):\d\d~','$1',$sTime); //remove seconds
		$_POST['eTime'][] = preg_replace('~(\d\d?:\d\d):\d\d~','$1',$eTime); //remove seconds
		$_POST['descr'][] = $desc;
		$_POST['birthday'][] = 0;
		$_POST['ignore'][] = 0;
	}
	return ''; //no error
}

function displayEvents($errors) {
	global $formCal, $ax, $delimiter, $birthdayID, $dFormat, $tFormat;
	
	echo "<p class='error'>{$ax['iex_number_of_errors']}: {$errors} ({$ax['iex_bgnd_highlighted']})</p><br>
<h3>{$ax['iex_verify_event_list']} \"{$ax['iex_add_events']}\"</h3>
<br>{$ax['iex_select_ignore_birthday']}<br><br>\n";
//display event list
	echo "<form action='index.php' method='post'>
{$formCal}
<input type='hidden' name='delimiter' value='{$delimiter}'>
<input type='hidden' name='birthdayID' value='{$birthdayID}'>
<input type='hidden' name='dFormat' value='{$dFormat}'>
<input type='hidden' name='tFormat' value='{$tFormat}'>\n";
	$nofEvents = count($_POST['title']);
	echo "<table>
		<tr><th>#</th><th>{$ax['iex_ignore']}</th><th>{$ax['iex_birthday']}</th><th>{$ax['iex_title']}</th><th>{$ax['iex_venue']}</th><th>{$ax['iex_category']}</th><th>{$ax['iex_date']}</th><th>{$ax['iex_end_date']}</th><th>{$ax['iex_start_time']}</th><th>{$ax['iex_end_time']}</th><th>{$ax['iex_description']}</th></tr>\n";
	for ($i = 0; $i < $nofEvents; $i++) {
		$tic = (!$_POST['title'][$i]) ? " class='inputError'" : '';
		$sdc = (DDtoID($_POST['sDate'][$i],$dFormat) === false) ? ' inputError' : '';
		$edc = (($_POST['eDate'][$i]) and (DDtoID($_POST['eDate'][$i],$dFormat) === false)) ? ' inputError' : '';
		$stc = (DTtoIT($_POST['sTime'][$i],$tFormat) === false) ? ' inputError' : '';
		$etc = (($_POST['eTime'][$i]) and (DTtoIT($_POST['eTime'][$i],$tFormat) === false)) ? ' inputError' : '';
		$nr = $i+1;
		echo "<tr>
<td>{$nr}</td>
<td class='floatC'><input type='checkbox' name='ignore[{$i}]' value='1'".(empty($_POST['ignore'][$i]) ? '' : " checked")."></td>
<td class='floatC'><input type='checkbox' name='birthday[{$i}]' value='1'".(empty($_POST['birthday'][$i]) ? '' : " checked")."></td>
<td><input type='text'{$tic} size='20' name='title[]' value=\"".mbtrunc($_POST['title'][$i],100)."\"></td>
<td><input type='text' size='20' name='venue[]' value=\"".mbtrunc($_POST['venue'][$i],100)."\"></td>
<td><input class='floatC' type='text' size='2' name='catID[]' value='{$_POST['catID'][$i]}'></td>
<td><input class='date floatC{$sdc}' type='text' name='sDate[]' value='{$_POST['sDate'][$i]}'></td>
<td><input class='date floatC{$edc}' type='text' name='eDate[]' value='{$_POST['eDate'][$i]}'></td>
<td><input class='time floatC{$stc}' type='text' name='sTime[]' value='{$_POST['sTime'][$i]}'></td>
<td><input class='time floatC{$etc}' type='text' name='eTime[]' value='{$_POST['eTime'][$i]}'></td>
<td><textarea cols='30' rows='1' name='descr[]'>{$_POST['descr'][$i]}</textarea></td>
</tr>\n";
	}
	echo "</table>
<br>
<button type='submit' name='addEvents' value='y'>{$ax['iex_add_events']}</button>
<button type='submit' name='back' value='y'>{$ax['back']}</button>
</form>\n";
}

function addEvents() {
	global $usr, $ax, $birthdayID, $dFormat, $tFormat;

	$msg = '';
	$nofEvents = count($_POST['title']);
	$added = $dropped = 0;
	for ($i = 0; $i < $nofEvents; $i++) {
		if (empty($_POST['ignore'][$i])) {
			$title = strip_tags($_POST['title'][$i]);
			$venue = strip_tags($_POST['venue'][$i]);
			$descr = strip_tags($_POST['descr'][$i],'<a><b><i><u><s><img>'); //remove most html tags
			$descr = preg_replace("~ +~"," ", $descr); //trim spaces
			$descr = str_replace(["\r\n","\n\r","\n","\r"],"<br>", $descr); //replace newline by <br>
			$descr = addUrlImgEmlTags($descr,'xxx'); //add URL link, image and email tags
			$sDate = DDtoID($_POST['sDate'][$i],$dFormat);
			$eDate = ($_POST['eDate'][$i]) ? DDtoID($_POST['eDate'][$i],$dFormat) : "9999-00-00";
			$sTime = DTtoIT($_POST['sTime'][$i],$tFormat);
			if (!$sTime) { //no time
				$sTime = '00:00';
				$eTime = '00:00';
			} elseif ($stime == '00:00') { //all day
				$sTime = '00:00';
				$eTime = '23:59';
			} else {
				$eTime = ($_POST['eTime'][$i]) ? DTtoIT($_POST['eTime'][$i],$tFormat) : "99:00";
			}
			$catID = $_POST['catID'][$i] ?? 1; //no cat
			$rType = $rInterval = $rPeriod = $rMonth = 0;
			if (!empty($_POST['birthday'][$i]) or $catID == $birthdayID) { //birthday
				$catID = $birthdayID;
				$rType = 1;
				$rInterval = 1;
				$rPeriod = 4;
				$eDate = "9999-00-00";
			}
			// test if event present in db
			$q = "SELECT `title` FROM `events` WHERE `status` >= 0 AND `title` = ? AND `sDate` = ? AND `eDate` = ? AND `sTime` = ? AND `eTime` = ?";
			$stH = stPrep($q);
			stExec($stH,[$title,$sDate,$eDate,$sTime,$eTime]);
			$row = $stH->fetch(PDO::FETCH_ASSOC);
			$stH = null;
			//if not present add event to db
			if (empty($row)) { //not present
				$q = "INSERT INTO `events` (`title`,`venue`,`text1`,`catID`,`userID`,`sDate`,`eDate`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`aDateTime`,`mDateTime`) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";
				$stH = stPrep($q);
				stExec($stH,[$title,$venue,$descr,$catID,$usr['ID'],$sDate,$eDate,$sTime,$eTime,$rType,$rInterval,$rPeriod,$rMonth,date("Y-m-d H:i"),date("Y-m-d H:i")]);
				$added++;
			} else {
				$dropped++;
			}
		}
	}
	if (!$msg) $msg = "{$added} {$ax['iex_events_added']}".($dropped > 0 ? " / {$dropped} {$ax['iex_events_dropped']}" : '');
	return $msg;
}


//control logic

$msg = ''; $errors = 0; //init
if ($usr['privs'] == 9) { //admin
	if (isset($_POST['uploadFile'])) {
		$msg = processUpload();
	}
	if ((isset($_POST['uploadFile']) and !$msg) or isset($_POST['addEvents'])) {
		$errors = processEvtFields($_POST['sDate'],$_POST['eDate'],$_POST['sTime'],$_POST['eTime'],$_POST['title'],$_POST['catID']);
	}
	if (isset($_POST['addEvents']) and !$errors) {
		$msg = addEvents(); //add events to calendar
	}
	echo $msg ? "<p class='error'>{$msg}</p>\n" : "<p>&nbsp;</p>\n";
	if (!isset($_POST['uploadFile']) and !isset($_POST['addEvents']) or (isset($_POST['uploadFile']) and $msg)) {
		instructions();
	}
	echo "<div class='centerBox sBoxAd'>\n";
	if (!isset($_POST['uploadFile']) and !isset($_POST['addEvents']) or (isset($_POST['uploadFile']) and $msg)) {
		uploadFile();
	} elseif (!isset($_POST['addEvents']) or $errors) {
		displayEvents($errors); //file uploaded or errors, display events
	} else {
		echo "<button type='button' onclick='index({delimiter:`{$_POST['delimiter']}`,birthdayID:`{$_POST['birthdayID']}`,dFormat:`{$_POST['dFormat']}`,tFormat:`{$_POST['tFormat']}`});'>{$ax['back']}</button>\n";
	}
	echo "</div>\n";
} else {
	echo "<p class='error'>{$ax['no_way']}</p>\n";
}
?>
