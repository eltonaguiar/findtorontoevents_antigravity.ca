<?php
/*
= iCal event file import script =

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

$defcatID = $_POST['defcatID'] ?? 1;
$tzAdjust = !empty($_POST['tzAdjust']) ? 1 : 0;
$fromD = $_POST['fromD'] ?? IDtoDD($today);
$fromID = DDtoID($fromD); //convert to ISO date
$tZone = $set['timeZone']; //set default time zone

$curLine = 0; //current iCal file line #

/* sub-functions */

function parseEvent(&$icsLines) { //parse iCal file
global $curLine, $tzAdjust, $tZone, $set;

	//initialize
	$event = [
		"dtS" => "", //date/time stamp
		"uid" => "", //unique id
		"tit" => "", //title
		"des" => "", //description
		"cat" => "", //category
		"ven" => "", //venue
		"pri" => 0, //private
		"sda" => "", //start date
		"eda" => "", //end date
		"sti" => "", //start time
		"eti" => "", //end time
		"r_t" => 0, //repeat type
		"r_i" => 0, //repeat interval
		"r_p" => 0, //repeat period
		"r_m" => 0, //repeat month
		"r_u" => "", //repeat until
		"tmz" => "" //timezone
	];
	$hits = [];
	$rrule = $valarm = false;
	
	//iterate icsLines for one event
	while (list($k, $v) = explode(':', str_replace('\;','~',$icsLines[$curLine++]), 2)) { //1st colon only
		$key = explode(';',$k);
		$value = explode(';',$v);
		foreach ($key as &$val) { $val = trim($val); }
		foreach ($value as &$val) { $val = trim($val); }
		unset($val); //break reference
		if ($key[0] == "END" and $value[0] == "VEVENT") { break; } //event end
		if ($key[0] == "BEGIN" and $value[0] == "VALARM") { $valarm = true; break; } //alarm begin
		if ($key[0] == "END" and $value[0] == "VALARM") { $valarm = false; break; } //alarm end
		if ($valarm) { break; } //skipping through alarm component
 		switch (strtoupper($key[0])) {
		case "DTSTAMP":
			$event['dtS'] = $value[0];
			break;
		case "UID":
			$event['uid'] = $value[0];
			break;
		case "CLASS":
			if ($value[0] != "PUBLIC") {
				$event['pri'] = 1;
			}
			break;
		case "SUMMARY":
			$event['tit'] = $value[0];
			break;
		case "DESCRIPTION":
			$event['des'] .= trim(stripslashes(str_ireplace(['\n','~'],["\n",';'],$value[0]))); //double quotes important!
			break;
		case "URL":
			$event['des'] .= "\n<a class='urlembed' href='{$value[0]}' target='_blank'>url</a>\n";
			break;
		case "LOCATION":
			$event['ven'] = $value[0];
			break;
		case "CATEGORIES":
			$event['cat'] = $value[0];
			break;
		case "RRULE":
			$rrule = true;
			$r_i1 = $r_i2 = $r_p1 = $r_p2 = $r_count = $r_m = 0; $rUntil = ''; //init
			foreach ($value as &$val) { //process each individual value
				if (preg_match("%^FREQ=(DAILY|WEEKLY|MONTHLY|YEARLY)$%i", $val, $hits)) {
					$r_i1 = 1;
					switch (strtoupper($hits[1])) {
						case 'DAILY': $r_p1 = 1; break;
						case 'WEEKLY': $r_p1 = 2; break;
						case 'MONTHLY': $r_p1 = 3; break;
						case 'YEARLY': $r_p1 = 4;
					}
				} elseif (preg_match("%^INTERVAL=([1-6])$%i" , $val, $hits)) {
					$r_i1 = $hits[1];
				} elseif (preg_match("%^BYMONTH=(\d|1[0-2])$%i" , $val, $hits)) { //only works if only 1 month
					$r_m = $hits[1];
				} elseif (preg_match("%^BYDAY=([1-4]?|(?:-1)?)(MO|TU|WE|TH|FR|SA|SU)$%i", $val, $hits)) {
					$r_i2 = ($hits[1]) ? (($hits[1] != '-1') ? $hits[1] : '5') : '1'; //-1 => 5 (last x-day)
					switch (strtoupper($hits[2])) {
						case 'MO': $r_p2 = 1; break;
						case 'TU': $r_p2 = 2; break;
						case 'WE': $r_p2 = 3; break;
						case 'TH': $r_p2 = 4; break;
						case 'FR': $r_p2 = 5; break;
						case 'SA': $r_p2 = 6; break;
						case 'SU': $r_p2 = 7;
					}
				} elseif (preg_match("%^COUNT=([1-9][0-9]?)$%i", $val, $hits)) {
					$r_count = $hits[1];
				} elseif (preg_match("%^UNTIL=(\d{8})(T.*)*$%i" , $val, $hits)) {
					$rUntil = substr($hits[1],0,4)."-".substr($hits[1],4,2)."-".substr($hits[1],6,2);
				}
			}
			break;
		case "DTSTART":
			if (preg_match("%^(\d{8})(T\d{4})?%i",$value[0],$hits)) {
				$event['sda'] = substr($hits[1],0,4)."-".substr($hits[1],4,2)."-".substr($hits[1],6,2);
				if (isset($hits[2])) {
					$event['sti'] = substr($hits[2],1,2).":".substr($hits[2],3,2);
				}
				if (substr($value[0],-1) == 'Z') {
					$event['tmz'] = 'UTC'; //UTC time
				} elseif (!empty($key[1]) and strtoupper(substr($key[1],0,5)) == 'TZID=') {
					$event['tmz'] = substr($key[1],5);
				}
			}
			break;
		case "DTEND":
			if (preg_match("%^(\d{8})(T\d{4})?%i",$value[0],$hits)) {
				$event['eda'] = substr($hits[1],0,4)."-".substr($hits[1],4,2)."-".substr($hits[1],6,2);
				if (isset($hits[2])) {
					$event['eti'] = substr($hits[2],1,2).":".substr($hits[2],3,2);
				}
			}
			break;
		case "DURATION":
			if (!isset($event['eda']) and !isset($event['eti'])) {
				if (preg_match("%^\+?P(?:(\d{1,2})W)?(?:(\d{1,2})D)?T(?:(\d{1,2})H)?(?:(\d{1,2})M)?%i", $value[0], $hits)) {
					$durSeconds = 604800*$hits[1] + 86400*$hits[2] + 3600*$hits[3] + 60*$hits[1];
					$eUnixTS = strtotime($event['sda'].' '.$event['sti'].':00') + $durSeconds;
					$event['eda'] = date('Y-m-d',$eUnixTS);
					$event['eti'] = date('H:i',$eUnixTS);
				}
			}
			break;
		}
	}
	if (!$event['tmz']) { $event['tmz'] = $tZone; } //event timezone
	$validTZ = in_array($event['tmz'], timezone_identifiers_list()); //check if valid timezone
	if ($tzAdjust and $validTZ and $event['tmz'] != $set['timeZone']) { //adjust to timezone differences
		$curTZone = new DateTimeZone($set['timeZone']);
		$evtTZone = new DateTimeZone($event['tmz']);
		$dtNow = new DateTime("now");
		$tzOffset = $curTZone->getOffset($dtNow) - $evtTZone->getOffset($dtNow); //offset
		$eUnixTS = strtotime($event['sda'].' '.$event['sti'].':00') + $tzOffset;
		$event['sda'] = date('Y-m-d',$eUnixTS);
		$event['sti'] = date('H:i',$eUnixTS);
		if ($event['eti']) {
			$eDate = $event['eda'] ?: $event['sda'];
			$eUnixTS = strtotime($eDate.' '.$event['eti'].':00') + $tzOffset;
			$event['eda'] = date('Y-m-d',$eUnixTS);
			$event['eti'] = date('H:i',$eUnixTS);
		}
	}
	/* validate event */
	$event['des'] = trim($event['des']); //strip off newlines
	/* post processing */
	//end date
	if ($event['eda'] > $event['sda'] and !$event['eti']) {
		$event['eda'] = date('Y-m-d',strtotime($event['eda']) - 86400); //-1 day
	}
	if ($event['eda'] == $event['sda']) { $event['eda'] = ''; };
	//recurring events
	if ($rrule) {
		if (($r_p1 == 3 and $r_p2 > 0) or ($r_p1 == 4 and $r_p2 > 0 and $r_m > 0)) { //every xth (r_i) (0-5) <dayname> (r_p) of the month y (r_m)
			$event['r_t'] = 2;
			$event['r_i'] = $r_i2;
			$event['r_p'] = $r_p2;
			$event['r_m'] = $r_m;
			if ($rUntil) {
				$event['r_u'] = $rUntil;
			} elseif ($r_count) {
				$r_count--;
				$event['r_u'] = date('Y-m-d', mktime (0,0,0,(INT)substr($event['sda'],5,2) + $r_count,(INT)substr($event['sda'],8,2),(INT)substr($event['sda'],0,4)));
			}
		} elseif ($r_i2 == 0 and $r_p1 > 0) {
			$event['r_t'] = 1; //every xth (0-6) day|week|month|year
			$event['r_i'] = $r_i1;
			$event['r_p'] = $r_p1;
			if ($rUntil) {
				$event['r_u'] = $rUntil;
			} elseif ($r_count) {
				$r_count--;
				$r_offd = $r_offm = $r_offy = 0;
				switch ($r_p1) {
					case 1: $r_offd = $r_i1 * $r_count; break; //daily
					case 2: $r_offd = $r_i1 * 7 * $r_count; break; //weekly
					case 3: $r_offm = $r_i1 * $r_count; break; //monthly
					case 4: $r_offy = $r_i1 * $r_count; //yearly
				}
				$event['r_u'] = date('Y-m-d',mktime(12,0,0,(INT)substr($event['sda'],5,2) + $r_offm,(INT)substr($event['sda'],8,2) + $r_offd,(INT)substr($event['sda'],0,4) + $r_offy));
			}
		} else {
			$event['r_t'] = -1; //RRULE incompatible
		}
	}
	return $event;
}

function processEvtFields(&$sDate,&$eDate,&$sTime,&$eTime,&$title) { //validate event fields
	$errors = 0;
	$nofDates = count($sDate);
	for ($i = 0; $i < $nofDates; $i++) {
		$error = 0;
		if (($IsDate = DDtoID($sDate[$i])) === false) { $error++; } //convert Display Date to ISO Date
		if (($IeDate = DDtoID($eDate[$i])) === false) { $error++; }
		if (($IsTime = DTtoIT($sTime[$i])) === false) { $error++; }
		if (($IeTime = DTtoIT($eTime[$i])) === false) { $error++; }
		if (!$error) {
			if ($IsDate == $IeDate) { $IeDate = ''; }
			if ($IeDate and (!$IsDate or $IeDate < $IsDate)) { list($IsDate,$IeDate) = [$IeDate,$IsDate]; } //swap start and end date
			if ($IeDate and !$IsTime and !$IeTime) {
				$IeDate = date("Y-m-d",strtotime($IeDate.' 12:00:00') - 86400); //-1 day
				if ($IsDate == $IeDate) { $IeDate = ''; }
			}
			if (!$IeDate and $IsTime == $IeTime) { $IeTime = ""; }
			if ($IeTime and !$IeDate and ($IeTime < $IsTime or !$IsTime)) { list($IsTime,$IeTime) = [$IeTime,$IsTime]; } //swap start and end time
			$sDate[$i] = IDtoDD($IsDate); //convert ISO Date to Display Date
			$eDate[$i] = IDtoDD($IeDate);
			$sTime[$i] = ITtoDT($IsTime); //convert ISO Time to Display Time
			$eTime[$i] = ITtoDT($IeTime);
		}
		$errors += $error;
		if (!$title[$i]) { $errors++; } //title empty
	}
return $errors;
}

function eventInDb($title,$sDate,$eDate,$sTime,$eTime) {	//test if event present in db

	$q = 
	"SELECT
		`title`
	FROM `events` e
	WHERE
		`status` >= 0 AND `title` = ? AND `sDate` = ? AND `eDate` = ? AND `sTime` = ? AND `eTime` = ?
	";
	$stH = stPrep($q);
	stExec($stH,[$title,$sDate,$eDate,$sTime,$eTime]);
	$row = $stH->fetch(PDO::FETCH_ASSOC);
	$stH = null;
	return (!empty($row) ? true : false);
}

/* main functions */

function instructions() {
	global $ax;
	
	$stH = dbQuery("SELECT `ID`,`name` FROM `categories` WHERE `status` >= 0 ORDER BY `ID`");
	echo "<aside class='aside sBoxAd'>{$ax['xpl_import_ical']}
<table class='list'>
<tr><th style='width:auto;'>ID</th><th style='width:auto;'>{$ax['iex_category']}</th></tr>\n";
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		echo "<tr><td class='floatC'>{$row['ID']}</td><td>&nbsp;{$row['name']}</td></tr>\n";
	}
	echo "</table>\n</aside>\n";
}

function uploadFile() {
global $formCal, $ax, $defcatID, $tzAdjust, $fromD;

echo "<form action='index.php' method='post' enctype='multipart/form-data'>
{$formCal}
<input type='hidden' name='MAX_FILE_SIZE' value='1000000'>
<fieldset><legend>{$ax['iex_upload_ics']}</legend>\n
<table class='list'>
<tr><td class='label'>{$ax['iex_file']}:</td><td><input type='file' name='fName'></td></tr>
<tr><td class='label'>{$ax['iex_default_cat_id']}:</td><td><input type='text' name='defcatID' value='{$defcatID}' size='1'> ({$ax['iex_if_no_cat']})</td></tr>
<tr><td class='label'>{$ax['iex_tz_adjust']}:</td><td><input type='checkbox' name='tzAdjust' value='1'".($tzAdjust == 1 ? " checked" : '')."></td></tr>
<tr><td class='label'>{$ax['iex_import_events_from_date']}:</td><td><input class='date' type='text' name='fromD' id='fromD' value='{$fromD}'>
<span class='dtPick' title=\"{$ax['iex_select_date']}\" onclick='dPicker(0,``,`fromD`); return false;'>&#x1F4C5;</span></td></tr>
</table>
</fieldset>
<button type='submit' name='uploadFile' value='y'>{$ax['iex_upload_file']}</button>
</form>
<div style='clear:right'></div>\n";
}

function processUpload() {
	global $ax, $curLine, $defcatID, $tZone, $fromID;
	
	$calProps = ["PRODID","VERSION","TZID","X-WR-CALNAME","X-LC-CONTENT"]; //iCal properties and components of interest
	
	$fName = $_FILES['fName']['tmp_name'];
	if (!$fName) { return $ax['iex_no_file_name']; } //ical file missing
	$fContent = file_get_contents($fName); //read file
	unlink($fName);
	$begin = strpos($fContent,'BEGIN:VCALENDAR');
	if ($begin === false) { return $ax['iex_no_begin_tag']; }	//sanity check
	$fContent = preg_replace("#\r?\n[\s\t]#m","",trim(substr($fContent,$begin+15))); //skip BEGIN and unfold lines
	$icsLines = preg_split("#\r?\n#", $fContent); //split into lines
	unset($fContent);

	//Get calendar categories
	$cats = [];
	$stH = dbQuery("SELECT `ID`,`name` FROM `categories` WHERE `status` >= 0 ORDER BY `ID`");
 	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		$cats[$row['name']] = $row['ID'];
	}

	//Iterate icsLines
	$curLine = 1;
	while (isset($icsLines[$curLine])) {
		list($key, $value) = explode(':', $icsLines[$curLine++], 2);
		$key = strtoupper(trim($key));
		$value = trim($value);
		if ($key == "BEGIN" and strtoupper($value) == "VEVENT") { //event start
			$event = parseEvent($icsLines);
			//save event data
			if (($event['r_t'] == 0 and ($event['sda'] >= $fromID or $event['eda'] >= $fromID)) or ($event['r_t'] != 0 and (!$event['r_u'] or $event['r_u'] >= $fromID))) {
				$curCat = '';
				foreach ($cats as $catName => $catID) {
					if (strpos(strtolower($event['cat']), trim(strtolower($catName))) !== false) { $curCat = $catID; break; }
				}
				$_POST['title'][] = $event['tit'];
				$_POST['venue'][] = $event['ven'];
				$_POST['descr'][] = $event['des'];
				$_POST['catID'][] = $curCat ?: $defcatID;
				$_POST['sDate'][] = IDtoDD($event['sda']);
				$_POST['eDate'][] = IDtoDD($event['eda']);
				if ($event['sti'] == '00:00' and $event['eti'] == '23:59') { //all day
					$event['sti'] = $event['eti'] = '';
				}
				$_POST['sTime'][] = ITtoDT($event['sti']);
				$_POST['eTime'][] = ITtoDT($event['eti']);
				$_POST['r_t'][] = $event['r_t'];
				$_POST['r_i'][] = $event['r_i'];
				$_POST['r_p'][] = $event['r_p'];
				$_POST['r_m'][] = $event['r_m'];
				$_POST['r_u'][] = IDtoDD($event['r_u']);
				$_POST['delete'][] = 0;
			}
		} else { //meta data
			if (in_array($key, $calProps)) {
				if ($key == 'TZID') { $tZone = $value; } //set global time zone
				$_POST[$key] = $value; //save meta data
			}
		}
	}
	if (empty($_POST['title'])) { return $ax['iex_no_events_from_date']." ".IDtoDD($fromID); } //no events
	return ''; //no error
}

function displayEvents($errors) {
	global $formCal, $ax, $defcatID, $tzAdjust, $fromD, $fromID;
	
	$nofEvents = count($_POST['title']);
	if ($nofEvents == 0) { //no events
		echo "<div class='centerBox'>
{$ax['iex_no_events_from_date']} ".IDtoDD($fromID)."<br><br>
<button type='button' onclick='index({defcatID:`{$_POST['defcatID']}`,tzAdjust:`{$_POST['tzAdjust']}`,fromD:`{$_POST['fromD']}`});'>{$ax['back']}</button>
</div>\n";
		return;
	}
	$listHead = "";
	echo "<div class='centerBox'>
<p class='error'>{$ax['iex_number_of_errors']}: {$errors} ({$ax['iex_bgnd_highlighted']})</p><br>
<h3>{$ax['iex_verify_event_list']} \"{$ax['iex_add_events']}\"</h3><br>
{$ax['iex_select_ignore']}<br><br>\n";
	echo "<button type='button' onclick='checkA(`delete`);'>{$ax['iex_check_all_ignore']}</button>\n";
//display event list
	echo "<form action='index.php' method='post'>
{$formCal}
<input type='hidden' name='defcatID' value='{$defcatID}'>
<input type='hidden' name='tzAdjust' value='{$tzAdjust}'>
<input type='hidden' name='fromD' value='{$fromD}'>\n";
	if (!empty($_POST['X-WR-CALNAME'])) {
		$listHead .= $_POST['X-WR-CALNAME'];
		echo "<input type='hidden' name='X-WR-CALNAME' value=\"{$_POST['X-WR-CALNAME']}\">\n";
	}
	if (!empty($_POST['X-LC-CONTENT'])) {
		$listHead .= "&nbsp;&nbsp;&nbsp;({$_POST['X-LC-CONTENT']})";
		echo "<input type='hidden' name='X-LC-CONTENT' value=\"{$_POST['X-LC-CONTENT']}\">\n";
	}
	echo "<table class='list'>\n";
	if ($listHead) { echo "<tr><td colspan='11' class='floatC'><h3>{$listHead}</h3></td></tr>\n"; }
	echo "<tr><th>#</th><th>{$ax['iex_ignore']}</th><th>{$ax['iex_title']}</th><th>{$ax['iex_venue']}</th><th>{$ax['iex_category']}</th><th>{$ax['iex_date']}</th><th>{$ax['iex_end_date']}</th><th>{$ax['iex_start_time']}</th><th>{$ax['iex_end_time']}</th><th>{$ax['iex_description']}</th><th>{$ax['iex_repeat']}</th></tr>\n";
	for ($i = 0; $i < $nofEvents; $i++) {
		$tic = (!$_POST['title'][$i]) ? " class='inputError'" : '';
		$sdc = (DDtoID($_POST['sDate'][$i]) === false) ? ' class="inputError"' : '';
		$edc = (($_POST['eDate'][$i]) and (DDtoID($_POST['eDate'][$i]) === false)) ? ' class="inputError"' : '';
		$stc = (DTtoIT($_POST['sTime'][$i]) === false) ? ' class="inputError"' : '';
		$etc = (($_POST['eTime'][$i]) and (DTtoIT($_POST['eTime'][$i]) === false)) ? ' class="inputError"' : '';
		$nr = $i+1;
		echo "<tr>
<td>{$nr}</td>
<td class='floatC'><input type='checkbox' name='delete[]' value='1'".(empty($_POST['delete'][$i]) ? "" : " checked").">
<input type='hidden' name='r_t[]' value='{$_POST['r_t'][$i]}'>
<input type='hidden' name='r_i[]' value='{$_POST['r_i'][$i]}'>
<input type='hidden' name='r_p[]' value='{$_POST['r_p'][$i]}'>
<input type='hidden' name='r_m[]' value='{$_POST['r_m'][$i]}'>
<input type='hidden' name='r_u[]' value='{$_POST['r_u'][$i]}'>
</td>
<td><input type='text'{$tic} size='20' name='title[]' value=\"".mbtrunc($_POST['title'][$i],100)."\"></td>
<td><input type='text' size='20' name='venue[]' value=\"".mbtrunc($_POST['venue'][$i],100)."\"></td>
<td><input class='floatC' type='text' size='2' name='catID[]' value='{$_POST['catID'][$i]}'></td>
<td><input class='date floatC' type='text'{$sdc} name='sDate[]' value='{$_POST['sDate'][$i]}'></td>
<td><input class='date floatC' type='text'{$edc} name='eDate[]' value='{$_POST['eDate'][$i]}'></td>
<td><input class='time floatC' type='text'{$stc} name='sTime[]' value='{$_POST['sTime'][$i]}'></td>
<td><input class='time floatC' type='text'{$etc} name='eTime[]' value='{$_POST['eTime'][$i]}'></td>
<td><textarea cols='30' rows='1' name='descr[]'>{$_POST['descr'][$i]}</textarea></td>
<td>".repeatText($_POST['r_t'][$i],$_POST['r_i'][$i],$_POST['r_p'][$i],$_POST['r_m'][$i],DDtoID($_POST['r_u'][$i]))."</td>\n";
//		echo '<td>r_t= '.$_POST['r_t'][$i].' r_i= '.$_POST['r_i'][$i].' r_p= '.$_POST['r_p'][$i].'<br> r_m= '.$_POST['r_m'][$i].' r_u= '.$_POST['r_u'][$i]."</td>\n"; //for testing
		echo "</tr>\n";
	}
	echo "</table>
<br>
<button type='submit' name='addEvents' value='y'>{$ax['iex_add_events']}</button>
<button type='submit' name='back' value='y'>{$ax['back']}</button>
</form>
</div>\n";
}

function addEvents() {
	global $usr, $ax, $defcatID;

	$msg = "";
	$nofEvents = count($_POST['title']);
	$added = $dropped = 0;
	for ($i = 0; $i < $nofEvents; $i++) {
		if (empty($_POST['delete'][$i]) and $_POST['r_t'][$i] >= 0) { //if delete not ticked and repeat-type is valid
			$title = htmlspecialchars_decode(trim($_POST['title'][$i]));
			$venue = htmlspecialchars_decode(trim($_POST['venue'][$i]));
			$descr = strip_tags(trim($_POST['descr'][$i]),'<a>');
			$descr = addUrlImgEmlTags($descr,'x--'); //add URL link tags
			$descr = str_ireplace(["\r\n", "\n", "\r"],"<br>",$descr); //allow URLs and replace newline by <br>
			$sDate = DDtoID($_POST['sDate'][$i]);
			$eDate = ($_POST['eDate'][$i]) ? DDtoID($_POST['eDate'][$i]) : "9999-00-00";
			$sTime = DTtoIT($_POST['sTime'][$i]);
			$eTime = ($_POST['eTime'][$i]) ? DTtoIT($_POST['eTime'][$i]) : "99:00:00";
			if (empty($sTime)) { //no time
				$sTime = '00:00';
				$eTime = '00:00';
			}
			$r_t = $_POST['r_t'][$i];
			$r_i = $_POST['r_i'][$i];
			$r_p = $_POST['r_p'][$i];
			$r_m = $_POST['r_m'][$i];
			$r_u = $_POST['r_u'][$i] ? DDtoID($_POST['r_u'][$i]) : "9999-00-00";
			$catID = $_POST['catID'][$i] ?: 1; //no cat
			if (!eventInDb($title,$sDate,$eDate,$sTime,$eTime)) { //add event to db
				$q = "INSERT INTO `events` (`title`,`venue`,`text1`,`catID`,`userID`,`sDate`,`eDate`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";
				$stH = stPrep($q);
				stExec($stH,[$title,$venue,$descr,$catID,$usr['ID'],$sDate,$eDate,$sTime,$eTime,$r_t,$r_i,$r_p,$r_m,$r_u,date("Y-m-d H:i"),date("Y-m-d H:i")]);
				$added++;
			} else {
				$dropped++;
			}
		}
	}
	if (!$msg) $msg = $added." ".$ax['iex_events_added'].($dropped > 0 ? " / {$dropped} {$ax['iex_events_dropped']}" : "");
	return $msg;
}


//control logic

$msg = ""; $errors = 0; //init
if ($usr['privs'] == 9) { //admin
	if (isset($_POST['uploadFile'])) {
		if (!$fromID) {
			$msg = $ax['iex_bad_date']; //invalid date
		} else {
			$msg = processUpload();
		}
	}
	if ((isset($_POST['uploadFile']) and !$msg) or isset($_POST['addEvents'])) {
		$errors = processEvtFields($_POST['sDate'],$_POST['eDate'],$_POST['sTime'],$_POST['eTime'],$_POST['title']);
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
		echo "<button type='button' onclick='index({defcatID:`{$_POST['defcatID']}`,tzAdjust:`{$_POST['tzAdjust']}`,fromD:`{$_POST['fromD']}`});'>{$ax['back']}</button>\n";
	}
	echo "</div>\n";
} else {
	echo "<p class='error'>{$ax['no_way']}</p>\n";
}
?>
