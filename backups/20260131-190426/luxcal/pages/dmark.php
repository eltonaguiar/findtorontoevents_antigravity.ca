<?php
/*
= LuxCal add/edit day marking page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//get input params
$action = $_REQUEST['action'] ?? '';
$eid = $_REQUEST['eid'] ?? 0;
$evD = $_REQUEST['evD'] ?? '';

//sanity check
if (empty($lcV) or
		(!empty($action) and !preg_match('%^(add|edi(0|1|2)?|upd|del)(_exe)?(_cls)?$%',$action)) or
		(isset($eid) and !preg_match('%^\d{1,8}$%',$eid)) or
		(!empty($evD) and !preg_match('%^\d{2,4}-\d{2}-\d{2,4}$%',$evD))
	) { exit("not permitted - {$action}-(".substr(basename(__FILE__),0,-4).')'); }

//set actions & state
$close = $exec = false;
$ediN = $_POST['ediN'] ?? 0; //0: not relevant, 1: occurrence, 2: series
$state = substr($action,0,3); //edi, add, upd or del
$exec = strpos($action,'exe') ? true : false;
$close = strpos($action,'cls') ? true : false;
if ($state == 'edi' and is_numeric($action[3])) { $ediN = $action[3]; } //0: not relevant, 1: occurrence, 2: series

//init
$eMsg = $wMsg = $cMsg = '';
$type = 1;
$todayDT = date("Y-m-d H:i");

//init day marking data
if ($state == 'edi') { //show/edit day marking
	$stH = stPrep("
		SELECT e.*,u.`name` AS own
		FROM `events` e
		INNER JOIN `users` u ON u.`ID` = e.`userID`
		WHERE e.`ID` = ?");
	stExec($stH,[$eid]);
	$row = $stH->fetch(PDO::FETCH_ASSOC);
	$stH = null;
	//remember non-input fields
	$_SESSION['evt']['sda'] = $row['sDate']; //original sDate
	$_SESSION['evt']['adt'] = $row['aDateTime'];
	$_SESSION['evt']['mdt'] = $row['mDateTime'][0] != '9' ? $row['mDateTime'] : '';
	$_SESSION['evt']['edr'] = $row['editor'];
	$_SESSION['evt']['own'] = $row['own'];
	$_SESSION['evt']['xda'] = $row['xDates'];
	$_SESSION['evt']['r_u'] = $row['rUntil'];
	//input fields
	$tit = $row['title'];
	$tx2 = $row['text2'];
	$tx3 = $row['text3'];
	$uid = $row['userID'];
	if ($ediN == 1) {
		$sda = IDtoDD($evD);
		$eda = "";
		$r_t = 0;
	} else {
		$sda = IDtoDD($row['sDate']);
		$eda = IDtoDD($row['eDate']);
		$r_t = $row['rType'];
	}
	$ri1 = $rp1 = 1;
	$ri2 = $rp2 = 0;
	if ($r_t == 1) {
		$ri1 = $row['rInterval'];
		$rp1 = $row['rPeriod'];
	} elseif ($r_t == 2) {
		$ri2 = $row['rInterval'];
		$rp2 = $row['rPeriod'];
	}
	$r_m = $row['rMonth'];
	$rul = IDtoDD($row['rUntil']);
} else { //add or upd
	if ($state == 'add') { //init (in case of clone)
		$eid = 0;
		$_SESSION['evt']['own'] = $usr['name'];
		$_SESSION['evt']['edr'] = '';
		$_SESSION['evt']['xda'] = '';
		$_SESSION['evt']['adt'] = $todayDT;
		$_SESSION['evt']['mdt'] = '';
	} else { //upd
		$_SESSION['evt']['edr'] = $usr['name'];
		$_SESSION['evt']['mdt'] = $todayDT;
	}
	$uid = $usr['ID'];
	$tit = isset($_POST['tit']) ? strip_tags(trim($_POST['tit']),'<b><i><u><s><sub><sup><br>') : '';
	$tx2 = $_POST['tx2'] ?? '';
	$tx3 = $_POST['tx3'] ?? '';
	$sda = $_POST['sda'] ?? '';
	$eda = $_POST['eda'] ?? '';
	$r_t = $_POST['r_t'] ?? 0;
	$ri1 = $_POST['ri1'] ?? 1;
	$rp1 = $_POST['rp1'] ?? 1;
	$ri2 = $_POST['ri2'] ?? 0;
	$rp2 = $_POST['rp2'] ?? 0;
	$r_m = $_POST['rpm'] ?? 0;
	$rul = $_POST['rul'] ?? '';

	if ($state == "add") { //add day marking - preset start date if available
		if (!empty($evD) and empty($sda)) { $sda = IDtoDD($evD); }
	}
}

if ($sda == $eda) { $eda = ''; } //reset end date if not used

//set repeat params
$r_i = $r_t == 1 ? $ri1 : ($r_t == 2 ? $ri2 : 0);
$r_p = $r_t == 1 ? $rp1 : ($r_t == 2 ? $rp2 : 0);
$repTxt = repeatText($r_t,$r_i,$r_p,$r_m,DDtoID($rul)); //make repeat text
if (!$repTxt) { $repTxt = $xx['evt_no_repeat']; }

//last minute edit rights check
$mayEdit = ($usr['privs'] > 2 or ($usr['privs'] == 2 and $uid == $usr['ID']));

//execute?
if (!$mayEdit or !$exec) goto noExe; //no

//add/update day marking
$evtValid = 0; //init
if ($state == "add" or $state == "upd") {
	//validate input fields
	do {
		if (!$tit) { $eMsg .= $xx['evt_no_title']."<br>"; break; } //dmark must have a title
		if ($sda) {
			$sDate = DDtoID($sda);
			if (!$sDate) { $eMsg .= $xx['evt_bad_date'].": ".$sda."<br>"; break; }
		} else {
			$eMsg .= $xx['evt_no_start_date']."<br>"; break;
		}
		if ($eda) {
			$eDate = DDtoID($eda);
			if (!$eDate) { $eMsg .= $xx['evt_bad_date'].": ".$eda."<br>"; break; }
			if ($eDate < $sDate) { $eMsg .= $xx['evt_end_before_start_date']."<br>"; break; }
		} else { $eDate = '9999-00-00'; }
		if ($r_t > 0 and $rul) {
			$runtil = DDtoID($rul);
			if (!$runtil) {
				$eMsg .= $xx['evt_bad_rdate'].": ".$rul."<br>"; break;
			} elseif ($runtil < $sDate) {
				$eMsg .= $xx['evt_until_before_start_date']."<br>"; break;
			}
		} else {
			$runtil = "9999-00-00";
		}
		//no errors in form fields - so continue
		$evtValid = 1;
		
		if ($eMsg) { $close = false; } //upload problem - don't close window
	} while (false);
}

if ((($state == "add" or $state == "upd") and $evtValid) or $state == "del") { //update database
	$tit = str_replace(['&',"'",'"'],['&amp;',"&apos;",'&quot;'],$tit);

	//update events table
	if ($state == "add") { //add new event
		$q = "INSERT INTO `events` (`type`,`title`,`text2`,`text3`,`userID`,`sDate`,`eDate`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)";
		$stH = stPrep($q); //add to events table
		stExec($stH,[$type,$tit,$tx2,$tx3,$uid,$sDate,$eDate,$r_t,$r_i,$r_p,$r_m,$runtil,$todayDT]);
		$stH = null;
		$eid = dbLastRowId(); //set id to new event
		$cMsg .= $xx['evt_confirm_added'];
	} elseif ($state == "upd") { //update event
		//scrutinize 'checked' and 'xDates'
		$chd = $xda = ''; //init
		$maxDate = $_SESSION['evt']['r_u'][0] == '9' ? ($eDate[0] == '9' ? '0' : $eDate) : ($eDate[0] == '9' ? $_SESSION['evt']['r_u'] : max($_SESSION['evt']['r_u'],$eDate));
		$maxOffset = $maxDate == '0' ? '0' : strval(round((strtotime($maxDate) - strtotime($sDate)) / 86400)); //days
		if (!empty($_SESSION['evt']['chd'])) {
			$chd = preg_replace_callback('~;\d{1,4}~',function ($matches) use ($maxOffset) { return ltrim($matches[0],';') <= $maxOffset ? $matches[0] : ''; },$_SESSION['evt']['chd']);
		}
		if (!empty($_SESSION['evt']['xda'])) {
			$xda = preg_replace_callback('~;\d{1,4}~',function ($matches) use ($maxOffset) { return ltrim($matches[0],';') <= $maxOffset ? $matches[0] : ''; },$_SESSION['evt']['xda']);
		}
		//modified time stamp
		$adtStamp = strtotime($_SESSION['evt']['adt']);
		$modDT = ($nowTS - $adtStamp > 600) ? $todayDT : '9999-00-00 00:00'; //mod time not set if < 10 mins passed
		if ($ediN != 1) { //update event or the series
			$stH = stPrep("UPDATE `events`
				SET `type`=?,`title`=?,`text2`=?,`text3`=?,`userID`=?,`editor`=?,`sDate`=?,`eDate`=?,`xDates`=?,`rType`=?,`rInterval`=?,`rPeriod`=?,`rMonth`=?,`rUntil`=?, `mDateTime`=?
				WHERE `ID`=?"); //update events table
			stExec($stH,[$type,$tit,$tx2,$tx3,$uid,$usr['name'],$sDate,$eDate,$xda,$r_t,$r_i,$r_p,$r_m,$runtil,$modDT,$eid]);
			$stH = null;
			$cMsg .= $xx['evt_confirm_saved'];
		} else { //update 1 occurrence
			$offset = strval(round((strtotime($evD) - strtotime($_SESSION['evt']['sda'])) / 86400)); //days
			$_SESSION['evt']['xda'] .= ';'.$offset;
			$stH = stPrep("UPDATE `events` SET `editor`=?,`xDates`=?,`mDateTime`=? WHERE `ID`=?");
			stExec($stH,[$usr['name'],$_SESSION['evt']['xda'],$todayDT,$eid]); //exclude date from series
			$stH = stPrep("INSERT INTO `events` (`type`,`title`,`text2`,`text3`,`userID`,`editor`,`sDate`,`eDate`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"); //add new event
			stExec($stH,[$type,$tit,$tx2,$tx3,$uid,$usr['name'],$sDate,$eDate,$r_t,$r_i,$r_p,$r_m,$runtil,$_SESSION['evt']['adt'],$todayDT]);
			$stH = null;
			$eid = dbLastRowId(); //set id to new event
			$ediN = 0;
			$cMsg .= $xx['evt_confirm_added'];
		}
	} elseif ($state == "del") { //delete event
		if ($ediN != 1) { //delete series
			$stH = stPrep("UPDATE `events` SET `status`=-1,`editor`=?,`mDateTime`=? WHERE `ID`=?"); //delete
			stExec($stH,[$usr['name'],$todayDT,$eid]);
		} else { //delete 1 occurrence
			$offset = strval(round((strtotime($evD) - strtotime($_SESSION['evt']['sda'])) / 86400)); //days
			$_SESSION['evt']['xda'] .= ';'.$offset;
			$stH = stPrep("UPDATE `events` SET `editor`=?,`xDates`=?,`mDateTime`=? WHERE `ID`=?"); //exclude date
			stExec($stH,[$usr['name'],$_SESSION['evt']['xda'],$todayDT,$eid]);
			$ediN = 0;
		}
		$cMsg = $xx['evt_confirm_deleted'];
	}

	//send notifications
	
	//prepare event array and message header
	$evtArr = array ('cnm' => '', 'snm' => '', 'eid' => $eid, 'typ' => '1', 'tit' => $tit, 'ven' => '', 'cid' => 1, 'tx1' => '', 'tx2' => '', 'tx3' => '', 'apd' => 0, 'sda' => DDtoID($sda), 'eda' => DDtoID($eda), 'sti' => '', 'eti' => '', 'ald' => false, 'uid' => $uid, 'r_t' => $r_t, 'repTxt' => $repTxt, 'att' => '', 'una' => $_SESSION['evt']['own'], 'edr' => $usr['name'], 'adt' => $_SESSION['evt']['adt'], 'mdt' => $_SESSION['evt']['mdt']); //html: with hyperlinks
	$prefix = 'mrk_dmark';
	$header = $state == 'add' ? $xx["{$prefix}_added"] : ($state == 'upd' ? $xx["{$prefix}_edited"] : $xx["{$prefix}_deleted"]);
	
	if ($set['chgRecipList']) { //notify changes to recip list on settings page
		notify($evtArr,$set['chgRecipList'],$header); //notify
	}

	//refresh calendar and close event box
	echo "\n<script>done('".($close ? 'cr' : 'r')."');</script>\n"; //c: close window, r: reload calendar
	$state = $state == 'del' ? 'add' : 'edi'; //update state if not closed
}

noExe:

if ($eMsg) echo "<p class='error'>{$eMsg}</p>\n";
if ($wMsg) echo "<p class='warning'>{$wMsg}</p>\n";
if ($cMsg) echo "<p class='confirm'>{$cMsg}</p>\n";

if ($mayEdit) {
	$formX = (($r_t == 1 or $r_t == 2 or $eda) and !($state == "add" or $ediN or $eMsg or $cMsg)) ? '0' : '1'; //0: ask series or occurrence
	require "./pages/dmarkform{$formX}.php";
} else {
	echo $xx['no_way'];
}
?>
