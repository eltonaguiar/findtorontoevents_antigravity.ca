<?php		
/*
= LuxCal Clean Up files =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$adminLang = (file_exists("./lang/ai-{$opt['cL']}.php")) ? $opt['cL'] : "english";
require "./lang/ai-{$adminLang}.php";

function showForm($action, $msg = '') {
	global $formCal, $ax;
	
	$class = $msg ? ($msg[0] === 'E' ? 'error' : 'confirm') : '';
	$msg = substr($msg,1);
	echo "<div class='centerBox sBoxAd'>\n";
	echo "<p class='{$class}'>".($msg ? $msg : '&nbsp;')."</p><br>\n";
	echo "<form action='index.php' method='post'>
{$formCal}
<fieldset><legend>{$ax['cup_cup_functions']}</legend>
<h4>{$ax['cup_fill_fields']}</h4>
<p>{$ax['cup_found_confirm']}</p>
<br>\n";
$pholdD = IDtoDD('yyyy-mm-dd'); //make date place holder
echo "<table class='cleanUp'>
<tr>
<td><button type='submit' name='action' value='tryEvt'>{$ax['cup_clean_up']}</button> {$ax['cup_past_events']}</td>
<td>{$ax['cup_evt_text']}</td>
<td><input class='date' type='text' name='dateEvt' id='dateEvt' value='{$_SESSION['dateEvt']}'>
<span class='dtPick' title='{$ax['cup_select_date']}' onclick='dPicker(1,``,`dateEvt`);return false;'>&#x1F4C5;</span></td>
</tr>
<tr>
<td><button type='submit' name='action' value='tryUsr'>{$ax['cup_clean_up']}</button> {$ax['cup_past_users']}</td>
<td>{$ax['cup_usr_text']}<span class='sup'>*</span></td>
<td><input class='date' type='text' name='dateUsr' id='dateUsr' value='{$_SESSION['dateUsr']}'>
<span class='dtPick' title='{$ax['cup_select_date']}' onclick='dPicker(1,``,`dateUsr`);return false;'>&#x1F4C5;</span></td>
</tr>
<tr>
<td><button type='submit' name='action' value='tryAtt'>{$ax['cup_clean_up']}</button> {$ax['cup_att_dir']}</td>
<td>{$ax['cup_att_text']}<span class='sup'>**</span></td>
<td><input class='date' placeholder='{$pholdD}' type='text' name='dateAtt' id='dateAtt' value='{$_SESSION['dateAtt']}'>
<span class='dtPick' title='{$ax['cup_select_date']}' onclick='dPicker(1,``,`dateAtt`);return false;'>&#x1F4C5;</span></td>
</tr>
<tr>
<td><button type='submit' name='action' value='tryRec'>{$ax['cup_clean_up']}</button> {$ax['cup_rec_dir']}</td>
<td>{$ax['cup_rec_text']}<span class='sup'>**</span></td>
<td><input class='date' placeholder='{$pholdD}' type='text' name='dateRec' id='dateRec' value='{$_SESSION['dateRec']}'>
<span class='dtPick' title='{$ax['cup_select_date']}' onclick='dPicker(1,``,`dateRec`);return false;'>&#x1F4C5;</span></td>
</tr>
<tr>
<td><button type='submit' name='action' value='tryTns'>{$ax['cup_clean_up']}</button> {$ax['cup_tns_dir']}</td>
<td>{$ax['cup_tns_text']}<span class='sup'>**</span></td>
<td><input class='date' placeholder='{$pholdD}' type='text' name='dateTns' id='dateTns' value='{$_SESSION['dateTns']}'>
<span class='dtPick' title='{$ax['cup_select_date']}' onclick='dPicker(1,``,`dateTns`);return false;'>&#x1F4C5;</span></td>
</tr>
<tr><td colspan='3'><span class='sup'>* </span><span class='fontS'>{$ax['cup_blank_date1']}</span></td></tr>
<tr><td colspan='3'><span class='sup'>**</span><span class='fontS'>{$ax['cup_blank_date2']}</span></td></tr>
</table>
</fieldset>\n
</form>\n";
	echo "<h4>{$ax['cup_important']}</h4>
<ul class='bold'>
<li>{$ax['cup_deleted_compact']}.</li>
<li>{$ax['cup_deleted_files']}.</li>
</ul>\n";
	echo "</div>\n";
}

function validateDate ($action) {
	global $ax, $actDate, $today;
	
	$result = '';
	switch ($action) {
	case 'tryEvt':
		if (!$actDate or $actDate > date('Y-m-d',time() - 2764800)) { $result = 'E'.$ax['cup_past_events'].': '.$ax['cup_invalid date']; break; }
		break;
	case 'tryUsr':
		if ($actDate === false or $actDate > date('Y-m-d',time() - 2764800)) { $result = 'E'.$ax['cup_past_users'].': '.$ax['cup_invalid date']; break; }
		break;
	case 'tryAtt':
		if ($actDate === false or $actDate >= $today) { $result = 'E'.$ax['cup_att_dir'].': '.$ax['cup_invalid date']; break; }
		break;
	case 'tryRec':
		if ($actDate === false or $actDate >= $today) { $result = 'E'.$ax['cup_rec_dir'].': '.$ax['cup_invalid date']; break; }
		break;
	case 'tryTns':
			if ($actDate === false or $actDate >= $today) { $result = 'E'.$ax['cup_tns_dir'].': '.$ax['cup_invalid date']; break; }
	}
	return $result;
}

function showList ($action, $list) {
	global $formCal, $ax;
	
	$legName = 'cup_'.strtolower(substr($action,3));
	echo "<div class='centerBox sBoxAd'>\n";
	echo "<form action='index.php' method='post'>
{$formCal}
<fieldset><legend>{$ax[$legName]}</legend>
<div class='cupList'>\n";
	foreach ($list as $item) { //list item
		echo "<p>{$item}</p>\n";
	}
	$delete = 'exe'.substr($action,3);
	echo "</div>
</fieldset>
<button type='submit' name='action' value='cancel'>{$ax['cup_cancel']}</button>&emsp;
<button type='submit' name='action' value='{$delete}'>{$ax['cup_delete']}</button>
</form>\n";
	if (substr($action,0,3) == 'exe' and $class) {
		echo "<h4>{$ax["cup_remove_compact"]}.</h4>\n";
	}
	echo "</div>\n";
}

function tryAction($action) {
	
	switch ($action) {
	case 'tryEvt':
		$list = cleanEvents(0);
		break;
	case 'tryUsr':
		$list = cleanAccounts(0);
		break;
	case 'tryAtt':
		$list = cleanAttDir(0);
		break;
	case 'tryRec':
		$list = cleanRecDir(0);
		break;
	case 'tryTns':
		$list = cleanTnsDir(0);
	}
	return $list;
}

function exeAction($action) {
	global $ax;
	
//		$results[] = 'C'.$ax['cup_cleanup_done'];
	$result = '';
	switch ($action) {
	case 'exeEvt':
		$result = $ax['cup_past_events'].' - '.$ax['cup_events_deleted'].': '.cleanEvents(1);
		break;
	case 'exeUsr':
		$result = $ax['cup_past_users'].' - '.$ax['cup_accounts_deleted'].': '.cleanAccounts(1);
		break;
	case 'exeAtt':
		$result = $ax['cup_att_dir'].' - '.$ax['cup_files_deleted'].': '.cleanAttDir(1);
		break;
	case 'exeRec':
		$result = $ax['cup_rec_dir'].' - '.$ax['cup_files_deleted'].': '.cleanRecDir(1);
		break;
	case 'exeTns':
		$result = $ax['cup_tns_dir'].' - '.$ax['cup_files_deleted'].': '.cleanTnsDir(1);
	}
	return $result;
}

function makeDateFilter($testDate,$gol) {
	if ($testDate) { //no date, no filter
		if ($gol == 'g') { //greater
			return "AND ((SELECT `repeat` FROM `categories` AS cat WHERE cat.`ID` = `catID`) > 0 OR (CASE WHEN `rType` > 0 THEN `rUntil` ELSE CASE WHEN `eDate` LIKE '9%' THEN `sDate` ELSE `eDate` END END >= '$testDate'))";
		} else { //less
			return "AND (SELECT `repeat` FROM `categories` AS cat WHERE cat.`ID` = `catID`) = 0 AND (CASE WHEN `rType` > 0 THEN `rUntil` ELSE CASE WHEN `eDate` LIKE '9%' THEN `sDate` ELSE `eDate` END END < '$testDate')";
		}
	} else {
		return '';
	}
}

function cleanEvents($exe = 0) {
	global $dbH, $calID, $actDate;
	
	$dFilter = makeDateFilter($actDate,'l');
	$dbH = dbConnect($calID,0); //connect to db
	if ($exe) {
		$stH = dbQuery("UPDATE `events` SET `status` = -1, `mDateTime` = '".date("Y-m-d H:i")."' WHERE `status` >= 0 {$dFilter}"); //delete
		return $stH->rowCount();
	} else {
		$stH = dbQuery("SELECT `title`,`sdate` FROM `events` WHERE `status` >= 0 {$dFilter}"); //candidate for delete
		$result = [];
		while ($qResult = $stH->fetch(PDO::FETCH_NUM)) {
			$result[] = IDtoDD($qResult[1]).": {$qResult[0]}";
		}
		return $result;
	}
}

function cleanAccounts($exe = 0) {
	global $dbH, $actDate, $calID;

	$filter = $actDate ? " OR `login1` <= '{$actDate}'" : '';
	$dbH = dbConnect($calID,0); //connect to db
	if ($exe) {
		$stH = dbQuery("UPDATE `users` SET `status` = -1 WHERE `status` >= 0 AND `ID` > 2 AND (`loginCnt` = 0{$filter})"); //delete (NOT the public and admin user)
		return $stH->rowCount();
	} else {
		$stH = dbQuery("SELECT `name`,`login1`,`loginCnt` FROM `users` WHERE `status` >= 0 AND `ID` > 2 AND (`loginCnt` = 0{$filter})"); //candidate (NOT the public and admin user)
		$result = [];
		while ($qResult = $stH->fetch(PDO::FETCH_NUM)) {
			$result[] = "{$qResult[0]} last login: ".($qResult[2] ? IDtoDD($qResult[1]) : '- -');
		}
		return $result;
	}
}

function cleanAttDir($exe = 0) {
	global $dbH, $actDate, $allCals, $set;

	$result = $exe ? 0 : [];
	$dFilter = makeDateFilter($actDate,'g');
	$fNames = preg_grep('~.+\.[a-z]{3}$~i',scandir("./attachments")); //valid files only
	foreach ($fNames as $fName) { //for each attachment file name
		if (stripos($set['attTypes'],substr($fName,-4)) === false) { continue; } //no attachment file
		$inUse = false;
		foreach($allCals as $calID => $title) { //for each installed calendar
			$dbH = dbConnect($calID,0); //connect to db
			$stH = dbQuery("SELECT COUNT(*) FROM `events` WHERE `status` >= 0 {$dFilter} AND `attach` LIKE '%{$fName}%' LIMIT 1",0);
			$qResult = $stH->fetch(PDO::FETCH_NUM);
			$stH = null;
			if ($qResult[0] > 0) { //attachment used
				$inUse = true;
				break;
			}
		}
		if (!$inUse) {
			if ($exe) {
				unlink("./attachments/{$fName}"); //delete
				$result++;
			} else {
				$result[] = "attachments/{$fName}"; //cadidate
			}
		}
	}
	return $result;
}

function cleanRecDir($exe = 0) {
	global $dbH, $actDate, $allCals;

	$result = $exe ? 0 : [];
	$dFilter = makeDateFilter($actDate,'g');
	$fNames = preg_grep('~.+\.[a-z]{3}$~i',scandir("./reciplists")); //valid files only
	foreach ($fNames as $fName) { //for each recipients list file name
		$inUse = false;
		foreach($allCals as $calID => $title) { //for each installed calendar
			$dbH = dbConnect($calID,0); //connect to db
			$stH = dbQuery("SELECT COUNT(*) FROM `events` WHERE `status` >= 0 {$dFilter} AND `notRecip` LIKE '%{$fName}%' LIMIT 1",0);
			$qResult = $stH->fetch(PDO::FETCH_NUM);
			$stH = null;
			if ($qResult[0] > 0) { //attachment used
				$inUse = true;
				break;
			}
		}
		if (!$inUse) {
			if ($exe) {
				unlink("./reciplists/{$fName}"); //delete
				$result++;
			} else {
				$result[] = "reciplists/{$fName}"; //cadidate
			}
		}
	}
	return $result;
}

function cleanTnsDir($exe = 0) {
	global $dbH, $actDate, $allCals, $set;

	$result = $exe ? 0 : [];
	$dFilter = makeDateFilter($actDate,'g');
	$fNames = preg_grep('~.+\.[a-z]{3}$~i',scandir("./thumbnails")); //valid files only
	foreach ($fNames as $fName) { //for each thumbnail file name
		if (stripos($set['tnlTypes'],substr($fName,-4)) === false) { continue; } //no thumbnail file
		$inUse = false;
		foreach($allCals as $calID => $title) { //for each installed calendar
			$dbH = dbConnect($calID,0); //connect to db
			$stH = dbQuery("SELECT COUNT(*) FROM `events` WHERE `status` >= 0 {$dFilter} AND (`text1` LIKE '%{$fName}%' OR `text2` LIKE '%{$fName}%' OR `text3` LIKE '%{$fName}%') LIMIT 1",0);
			$qResult = $stH->fetch(PDO::FETCH_NUM);
			$stH = null;
			if ($qResult[0] > 0 or strpos(file_get_contents("./sidepanel/info.txt"),$fName) !== false) { //thumbnail used in DB or in info.txt file
				$inUse = true;
				break;
			}
		}
		if (!$inUse) {
			if ($exe) {
				unlink("./thumbnails/{$fName}"); //delete
				$result++;
			} else {
				$result[] = "thumbnails/{$fName}"; //cadidate
			}
		}
	}
	return $result;
}


//init
$monthAgo = IDtoDD(date('Y-m-d',time() - 2764800)); //1 month ago
$action = $_POST["action"] ?? '';
if (!$action) {
	$_SESSION['dateEvt'] = $monthAgo; //1 month ago
	$_SESSION['dateUsr'] = $monthAgo; //1 month ago
	$_SESSION['dateAtt'] = '';
	$_SESSION['dateRec'] = '';
	$_SESSION['dateTns'] = '';
} elseif (substr($action,0,3) == 'try') {
	$_SESSION['dateEvt'] = $_POST["dateEvt"];
	$_SESSION['dateUsr'] = $_POST["dateUsr"];
	$_SESSION['dateAtt'] = $_POST["dateAtt"];
	$_SESSION['dateRec'] = $_POST["dateRec"];
	$_SESSION['dateTns'] = $_POST["dateTns"];
	$dateName = 'date'.substr($action,3);
	$_SESSION['actDate'] = DDtoID($_SESSION[$dateName]);
}
$actDate = $_SESSION['actDate'] ?? '';

//control logic
if ($usr['privs'] == 9) {
	echo "<aside class='aside sBoxAd'>{$ax['xpl_clean_up']}</aside>\n";
	//init
	$msg = '';
	$listOn = false;
	if (substr($action,0,3) == 'try') { //clean up - try
		$msg = validateDate($action);
		if (!$msg) {
			$allCals = getCals(); //get installed calendars
			$list = tryAction($action);
			if ($list) {
				showList($action,$list); //items to be deleted (cancel / delete)
				$listOn = true;
			} else {
				$msg = 'C'.$ax['cup_nothing_to_delete'];
			}
		}
	} elseif (substr($action,0,3) == 'exe') {
		$allCals = getCals(); //get installed calendars
		$msg = 'C'.exeAction($action);
	}
	if ($listOn == false) {
		showForm($action,$msg); //show cleanup form
	}
} else {
	echo "<p class='error'>{$ax['no_way']}</p>\n";
}
?>