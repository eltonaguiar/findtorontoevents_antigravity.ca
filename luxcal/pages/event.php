<?php
/*
= LuxCal add/edit event page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//get input params
$action = $_REQUEST['action'] ?? '';
$eid = $_REQUEST['eid'] ?? 0;
$evD = $_REQUEST['evD'] ?? '';
$evTs = $_REQUEST['evTs'] ?? '';
$evTe = $_REQUEST['evTe'] ?? '';
$catID = $_REQUEST['catID'] ?? '';

//sanity check
if (empty($lcV) or
		(!empty($action) and !preg_match('%^(add|edi(0|1|2)?|upd|del)(_exe)?(_cls)?$%',$action)) or
		(isset($eid) and !preg_match('%^\d{1,8}$%',$eid)) or
		(!empty($evD) and !preg_match('%^\d{2,4}-\d{2}-\d{2,4}$%',$evD)) or
		(!empty($evTs) and !preg_match('%^\d{2}:\d{2}$%',$evTs)) or
		(!empty($evTe) and !preg_match('%^\d{2}:\d{2}$%',$evTe)) or
		(!empty($catID) and !preg_match('%^\d+$%', $catID))
	) { exit("not permitted - {$action}-(".substr(basename(__FILE__),0,-4).')'); }

//set actions & state
$close = $exec = false;
$ediN = $_POST['ediN'] ?? 0; //0: not relevant, 1: occurrence, 2: series
if (empty($action)) {
	$refresh = true;
} else {
	$refresh = false;
	$state = substr($action,0,3); //edi, add, upd or del
	$exec = strpos($action,'exe') ? true : false;
	$close = strpos($action,'cls') ? true : false;
	if ($state == 'edi' and is_numeric($action[3])) { $ediN = $action[3]; } //0: not relevant, 1: occurrence, 2: series
}

//init
$eMsg = $wMsg = $cMsg = '';
$todayDT = date("Y-m-d H:i");
$todayD = substr($todayDT,0,10);

//init event data
if ($state == 'edi' and !$refresh) { //show/edit event
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
	$_SESSION['evt']['apd'] = $row['approved'];
	$_SESSION['evt']['xda'] = $row['xDates'];
	$_SESSION['evt']['chd'] = $row['checked'];
	$_SESSION['evt']['r_u'] = $row['rUntil'];
	//input fields
	$tit = $row['title'];
	$ven = $row['venue'];
	$tx1 = $row['text1'];
	$tx2 = $row['text2'];
	$tx3 = $row['text3'];
	$tx1 = remUrlImgEmlTags($tx1); //remove URL, image and email tags
	$tx2 = remUrlImgEmlTags($tx2);
	$tx3 = remUrlImgEmlTags($tx3);
	list($tx1,$tx2,$tx3) = str_replace(["<br>","<br />"],"\r\n",[$tx1,$tx2,$tx3]); //replace <br> by crlf
	$att = $row['attach'];
	$cid = $row['catID'];
	$sid = $row['scatID'];
	$uid = $row['userID'];
	$nal = $row['notRecip'] ?: ($set['defRecips'] ?: $usr['email']);
	$apd = $row['approved'];
	$pri = $row['private'];
	if ($ediN == 1) {
		$sda = IDtoDD($evD);
		$eda = "";
		$r_t = 0;
	} else {
		$sda = IDtoDD($row['sDate']);
		$eda = IDtoDD($row['eDate']);
		$r_t = $row['rType'];
	}
	$sti = ITtoDT($row['sTime']);
	$eti = ITtoDT($row['eTime']);
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
	$not = $row['notify'];
} else { //add, upd or refresh
	if ($state == 'add') { //init (in case of clone)
		$eid = 0;
		$_SESSION['evt']['own'] = $usr['name'];
		$_SESSION['evt']['edr'] = '';
		$_SESSION['evt']['xda'] = '';
		$_SESSION['evt']['apd'] = 0;
		$_SESSION['evt']['chd'] = '';
		$_SESSION['evt']['adt'] = $todayDT;
		$_SESSION['evt']['mdt'] = '';
	} else { //upd
		$_SESSION['evt']['edr'] = $usr['name'];
		$_SESSION['evt']['mdt'] = $todayDT;
	}
	$uid = $_POST['uid'] ?? $_POST['oUid'] ?? $usr['ID'];
	$tit = isset($_POST['tit']) ? validTags($_POST['tit'],'<b><i><u><s><sub><sup><br>') : '';
	$ven = isset($_POST['ven']) ? validTags($_POST['ven'],'<b><i><u><s>') : $set['defVenue'];
	$tx1 = isset($_POST['tx1']) ? validTags($_POST['tx1'],'<a><b><i><u><s><sub><sup><img>') : '';
	$tx2 = isset($_POST['tx2']) ? validTags($_POST['tx2'],'<a><b><i><u><s><sub><sup><img>') : '';
	$tx3 = isset($_POST['tx3']) ? validTags($_POST['tx3'],'<a><b><i><u><s><sub><sup><img>') : '';
	$att = $_POST['att'] ?? '';
	$eCats = explode(',',$usr['eCats']);
	$cid = $_POST['cid'] ?? ($eCats[0] == '0' ? 1 : intval($eCats[0]));
	$sid = $_POST['sid'] ?? 0;
	$nal = isset($_POST['nal']) ? trim($_POST['nal']," ;") : ($set['defRecips'] ?: $usr['email']);
	$apd = !empty($_POST['apd']) ? 1 : 0;
	$pri = $set['privEvents'] == 3 ? 1 : (($set['privEvents'] == 0 or !$usr['pEvts']) ? 0 : (empty($_POST['pri']) ? 0 : 1));
	$sda = $_POST['sda'] ?? '';
	$eda = $_POST['eda'] ?? '';
	$sti = $_POST['sti'] ?? '';
	$eti = $_POST['eti'] ?? '';
	$r_t = $_POST['r_t'] ?? 0;
	$ri1 = $_POST['ri1'] ?? 1;
	$rp1 = $_POST['rp1'] ?? 1;
	$ri2 = $_POST['ri2'] ?? 0;
	$rp2 = $_POST['rp2'] ?? 0;
	$r_m = $_POST['rpm'] ?? 0;
	$rul = $_POST['rul'] ?? '';
	$not = $_POST['not'] ?? -1;

	if ($state == "add" and !$refresh) { //add event - preset date/times if available
		if (!empty($evD) and empty($sda)) { $sda = IDtoDD($evD); }
		if (!empty($evTs)) { $sti = ITtoDT($evTs); }
		if (!empty($evTe)) { $eti = ITtoDT($evTe); }
		if (!empty($catID)) { //from matrix(C)
			$cid = $catID;
		} elseif (count($opt['cC']) == 1 and $opt['cC'][0] != 0) { //if a single cC selected: default
			$cid = $opt['cC'][0];
		}
	}
}

$vel = empty($_POST['vel']) ? 0 : 1; //venue list

//get category data
$stH = stPrep("SELECT * FROM `categories` WHERE `ID` = ?");
stExec($stH,[$cid]);
$row = $stH->fetch(PDO::FETCH_ASSOC);
$stH = null; //release statement handle
$cat = ['cnm' => $row['name'], 'rpt' => $row['repeat'], 'nol' => $row['noverlap'], 'olg' => $row['olapGap'], 'oem' => $row['olErrMsg'], 'dur' => $row['defSlot'], 'fur' => $row['fixSlot'], 'app' => $row['approve'], 'col' => $row['color'], 'bco' => $row['bgColor'], 'sub' => json_decode($row['subCats']), 'not' => $row['notList']];

if ($sda == $eda) { $eda = ''; } //reset end date if not used
$non = isset($_POST['nen']) ? ($_POST['nen'] == 'yes' ? 1 : 0) : 0; //notify now
$oUid = $_POST['oUid'] ?? $uid; //remember original user ID

//set repeat params
if ($cat['rpt']) { //cat repeat overrides
	$r_t = $r_i = 1;
	$r_p = $cat['rpt'];
	$rul = '';
} else {
	$r_i = $r_t == 1 ? $ri1 : ($r_t == 2 ? $ri2 : 0);
	$r_p = $r_t == 1 ? $rp1 : ($r_t == 2 ? $rp2 : 0);
}
$repTxt = repeatText($r_t,$r_i,$r_p,$r_m,DDtoID($rul)); //make repeat text
if (!$repTxt) { $repTxt = $xx['evt_no_repeat']; }

//all day event? No time?
$ald = (isset($_POST['ald']) or ($sti == '' and $set['timeDefault'] == 1) or (DTtoIT($sti) == '00:00' and DTtoIT($eti) == '23:59'));
$ntm = (isset($_POST['ntm']) or ($sti == '' and $set['timeDefault'] == 2) or (DTtoIT($sti) == '00:00' and DTtoIT($eti) == '00:00'));
if ($ald or $ntm) { $sti = $eti = ''; }

//last minute edit rights check
$mayEdit = (
	($usr['eCats'] == '0' or strpos($usr['eCats'],strval($cid)) !== false) and
	($usr['privs'] > 2 or ($usr['privs'] == 2 and $uid == $usr['ID'])) and
	(!$cat['app'] or $apd or $usr['privs'] > 3 or $uid == $usr['ID'])
	);

//execute?
if (!$mayEdit or !$exec) goto noExe; //no

//add/update event
$evtValid = 0; //init
if ($state == "add" or $state == "upd") {
	//validate input fields
	do {
		if (!$tit and $mode == 0) { $eMsg .= $xx['evt_no_title']."<br>"; break; } //normal event must have a title
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
		if ($ald) { //all day
			$sTime = '00:00';
			$eTime = '23:59';
		} elseif ($ntm) { //no time
			$sTime = $eTime = '00:00';
		} else {
			if ($sti) {
				$sTime = DTtoIT($sti);
				if (!$sTime) { $eMsg .= $xx['evt_bad_time'].": ".$sti."<br>"; break; }
			} elseif ($eDate[0] != '9') {
				$sTime = '00:00';
				$sti = ITtoDT('00:00');
			} else {
				$eMsg .= $xx['evt_no_start_time']."<br>"; break;
			}
			if ($eti) { //end time specified
				$eTime = DTtoIT($eti);
				if (!$eTime) { $eMsg .= $xx['evt_bad_time'].": ".$eti."<br>"; break; }
				if (($eDate[0] == '9' or $eDate == $sDate) and $eTime < $sTime) { $eMsg .= $xx['evt_end_before_start_time']."<br>"; break; }
				if ($sTime == $eTime and $eDate[0] == '9') { $eTime = '99:00'; }
			} else { //no end time
				if ($eDate[0] != '9') { //end date specified
					$eTime = '23:59';
				} else {
					$eTime = '99:00';
				}
			}
			if ($cat['dur'] and ($cat['fur'] or (!$eti and ($eDate[0] == '9')))) { //fixed / default event duration, re-compute eDate and eTime
				$eUnixTs = strtotime($sDate.' '.$sTime.':00') + ($cat['dur'] * 60);
				$eDate = date('Y-m-d',$eUnixTs);
				if ($eDate == $sDate) { $eDate = '9999-00-00'; }
				$eTime = date('H:i',$eUnixTs);
			}
		}
		if ($sTime == '00:00' and $eTime == '23:59') { $ald = true; }
		if ($sTime == '00:00' and $eTime == '00:00') { $ntm = true; }
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
		if ($not == '' or $not == '-' or !$set['emlService']) {
			$not = -1;
		} elseif (!is_numeric($not)) {
			$eMsg .= $xx['evt_not_days_invalid']."<br>"; break;
		} elseif ($sDate < date("Y-m-d",$nowTS + 86400 * $not)) { //$not >= 0
			$wMsg .= $xx['evt_not_in_past']."<br>";
		}
		$nal = preg_replace('%;\s*;%',';',$nal); //remove empty addresses
		if (($not >= 0 or $non) and strlen($nal) < 2) { $eMsg .= $xx['evt_no_recip_list']."<br>"; break; }
		if (strlen($nal) > 255) { $eMsg .= $xx['evt_recip_list_too_long']."<br>"; break; }
		if (!$pri and !$ntm and $r_t != 3) { //overlap test (not for 'no time' and 'rolling' events)
			$errMsg = overlap($mode,$eid,$cid,$sDate,$eDate,$_SESSION['evt']['xda'],$sTime,$eTime,$cat['rpt'],$cat['nol'],$cat['olg'],$cat['oem'],$r_t,$r_i,$r_p,$r_m,DDtoID($rul)); //check for overlap (same cat and all cats)
			if ($errMsg) { $eMsg .= $errMsg."<br>"; break; }
		}
		//no errors in form fields - so continue
		$evtValid = 1;
		
		//if file(s) uploaded, save each file and update db
		if (!empty($_FILES['uplAtt'])) {
			foreach($_FILES['uplAtt']['name'] as $k => $fName) {
				if ($fName) {
					if ($_FILES['uplAtt']['error'][$k]) { $eMsg .= "{$fName}: {$xx['evt_error_file_upload']}<br>"; continue; }
					if (!stripos(','.$set['attTypes'],substr($fName,-4))) { $eMsg .= "{$fName}: {$xx['evt_no_pdf_img_vid']}<br>"; continue; }
					if ($_FILES['uplAtt']['size'][$k] > ($set['maxUplSize'] * 1048570)) { $eMsg .= "{$fName}: {$xx['evt_upload_too_large']}<br>"; continue; }
					$fName = str_replace(' ','_',$fName); //get rid of spaces
					$tsfName = date('YmdHis').$fName; //get timestamped file name
					move_uploaded_file($_FILES['uplAtt']['tmp_name'][$k],"./attachments/{$tsfName}");
					$att .= ";".$tsfName; //add file attachments in db
				}
			}
		}
		if ($eMsg) { $close = false; } //upload problem - don't close window
	} while (false);
}

if ((($state == "add" or $state == "upd") and $evtValid) or $state == "del") { //update database

	//if owner changed, default not recipient = owner email
	if ($uid != $oUid) {
		$stH = stPrep("SELECT `email` FROM `users` WHERE `ID` = ?");
		stExec($stH,[$uid]);
		$row = $stH->fetch(PDO::FETCH_ASSOC);
		$stH = null;
		if ($row) {
			$nal = $row['email'];
		}
		$oUid = $uid; //set original user ID to current user
	}

	$from = ['&',"'",'"'];
	$to = ['&amp;','&apos;','&quot;'];
	list($tit,$ven,$tx1,$tx2,$tx3) = str_replace($from,$to,[$tit,$ven,$tx1,$tx2,$tx3]);
	$tx1Html = addUrlImgEmlTags($tx1); //add URL, image, mailto tags
	$tx2Html = addUrlImgEmlTags($tx2);
	$tx3Html = addUrlImgEmlTags($tx3);
	list($tx1Html,$tx2Html,$tx3Html) = str_replace(["\r\n", "\n", "\r"], "<br>", [$tx1Html,$tx2Html,$tx3Html]); //replace newline by <br>

	//update events table
	if ($state == "add") { //add new event
		$q = "INSERT INTO `events` (`type`,`private`,`title`,`venue`,`text1`,`text2`,`text3`,`attach`,`catID`,`scatID`,`userID`,`approved`,`notify`,`notRecip`,`sDate`,`eDate`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)";
		$stH = stPrep($q); //add to events table
		stExec($stH,[$mode,$pri,$tit,$ven,$tx1Html,$tx2Html,$tx3Html,$att,$cid,$sid,$uid,$apd,$not,$nal,$sDate,$eDate,$sTime,$eTime,$r_t,$r_i,$r_p,$r_m,$runtil,$todayDT]);
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
				SET `type`=?,`private`=?,`title`=?,`venue`=?,`text1`=?,`text2`=?,`text3`=?,`attach`=?,`catID`=?,`scatID`=?,`userID`=?,`editor`=?,`approved`=?,`checked`=?,`notify`=?,`notRecip`=?,`sDate`=?,`eDate`=?,`xDates`=?,`sTime`=?,`eTime`=?,`rType`=?,`rInterval`=?,`rPeriod`=?,`rMonth`=?,`rUntil`=?, `mDateTime`=?
				WHERE `ID`=?"); //update events table
			stExec($stH,[$mode,$pri,$tit,$ven,$tx1Html,$tx2Html,$tx3Html,$att,$cid,$sid,$uid,$usr['name'],$apd,$chd,$not,$nal,$sDate,$eDate,$xda,$sTime,$eTime,$r_t,$r_i,$r_p,$r_m,$runtil,$modDT,$eid]);
			$stH = null;
			$cMsg .= $xx['evt_confirm_saved'];
		} else { //update 1 occurrence
			$offset = strval(round((strtotime($evD) - strtotime($_SESSION['evt']['sda'])) / 86400)); //days
			$_SESSION['evt']['xda'] .= ';'.$offset;
			$stH = stPrep("UPDATE `events` SET `editor`=?,`xDates`=?,`mDateTime`=? WHERE `ID`=?");
			stExec($stH,[$usr['name'],$_SESSION['evt']['xda'],$todayDT,$eid]); //exclude date from series
			$newChd = (isset($_SESSION['evt']['sda']) and  cMark($_SESSION['evt'],$evD)) ? ';0' : '';
			$stH = stPrep("INSERT INTO `events` (`type`,`private`,`title`,`venue`,`text1`,`text2`,`text3`,`attach`,`catID`,`scatID`,`userID`,`editor`,`approved`,`checked`,`notify`,`notRecip`,`sDate`,`eDate`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"); //add new event
			stExec($stH,[$mode,$pri,$tit,$ven,$tx1Html,$tx2Html,$tx3Html,$att,$cid,$sid,$uid,$usr['name'],$apd,$newChd,$not,$nal,$sDate,$eDate,$sTime,$eTime,$r_t,$r_i,$r_p,$r_m,$runtil,$_SESSION['evt']['adt'],$todayDT]);
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
	$snm = $sid ? $cat['sub'][$sid-1][0] : '';
	$evtArr = array ('cnm' => $cat['cnm'], 'snm' => $snm, 'eid' => $eid, 'typ' => $mode, 'tit' => $tit, 'ven' => $ven, 'cid' => $cid, 'tx1' => $tx1Html, 'tx2' => $tx2Html, 'tx3' => $tx3Html, 'apd' => $apd, 'sda' => DDtoID($sda), 'eda' => DDtoID($eda), 'sti' => $sti, 'eti' => $eti, 'ald' => $ald, 'uid' => $uid, 'r_t' => $r_t, 'repTxt' => $repTxt, 'att' => $att, 'una' => $_SESSION['evt']['own'], 'edr' => $usr['name'], 'chd' => $_SESSION['evt']['chd'], 'adt' => $_SESSION['evt']['adt'], 'mdt' => $_SESSION['evt']['mdt']); //html: with hyperlinks
	$prefix = $mode == 0 ? 'evt_event' : 'mrk_dmark';
	$header = $state == 'add' ? $xx["{$prefix}_added"] : ($state == 'upd' ? $xx["{$prefix}_edited"] : $xx["{$prefix}_deleted"]);
	
	//send notifications
	$recipList = ''; //init
	if ($non or ($not == 0 and $sDate == $todayD)) { //notify now
		$recipList .= ';'.$nal;
	}
	if ($cat['not'] and (!$cat['app'] or $apd)) { //notify changes to category email addresses
		$emlList = str_ireplace([$usr['email'],$usr['name'],$usr['phone'],$usr['msingID']],'',$cat['not']); //remove editor from list
		$recipList .= ';'.$emlList;
	}
	if ($set['chgRecipList']) { //notify changes to recip list on settings page
		$recipList .= ';'.$set['chgRecipList'];
	}
	if ($recipList) {
		notify($evtArr,$recipList,$header); //notify
	}
	if ($apd and !$_SESSION['evt']['apd']) { //notify approval to event owner
		notify($evtArr,$evtArr['una'],$xx["evt_event_approved"]);
	}

	//refresh calendar and close event box
	echo "\n<script>done('".($close ? 'cr' : 'r')."');</script>\n"; //c: close window, r: reload calendar
	$state = $state == 'del' ? 'add' : 'edi'; //update state if not closed
}

noExe:

if ($cat['dur']) { //default event duration
	if ($cat['fur']) { //fixed event duration
		$ald = $ntm = false;
		$wMsg .= str_replace(['$1','$2'],[intval($cat['dur'] / 60),substr('0'.($cat['dur'] % 60),-2)],$xx['evt_fixed_duration'])."<br>";
	} else {
		$wMsg .= str_replace(['$1','$2'],[intval($cat['dur'] / 60),substr('0'.($cat['dur'] % 60),-2)],$xx['evt_default_duration'])."<br>";
	}
}

if ($not == -1) { $not = ''; }

if ($eMsg) echo "<p class='error'>{$eMsg}</p>\n";
if ($wMsg) echo "<p class='warning'>{$wMsg}</p>\n";
if ($cMsg) echo "<p class='confirm'>{$cMsg}</p>\n";

if ($mayEdit) {
	$eType = $mode == 0 ? 'event' : 'dmark';
	$formX = (($r_t == 1 or $r_t == 2 or $eda) and !($state == "add" or $ediN or $refresh or $eMsg or $cMsg)) ? '0' : '1'; //0: ask series or occurrence
	require "./pages/{$eType}form{$formX}.php";
} else {
	echo $xx['no_way'];
}
?>
