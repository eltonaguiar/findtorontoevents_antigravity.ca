<?php
/*
= LuxCal user management page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV) or
		(isset($_REQUEST['uid']) and !preg_match('%^\d{1,5}$%',$_REQUEST['uid'])) or
		(isset($_POST['delExe']) and !preg_match('%^\w$%',$_POST['delExe'])) or
		(!empty($state) and !preg_match('%^(add|edit|trans)$%',$state))
	) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); }

//initialize
$adminLang = (file_exists("./lang/ai-{$opt['cL']}.php")) ? $opt['cL'] : "english";
require "./lang/ai-{$adminLang}.php";
if (!isset($state)) { $state = ''; }

$user = [];
$user['id'] = $_REQUEST['uid'] ?? 0;
$user['name'] = trim($_POST['uName'] ?? '');
$user['mail'] = trim($_POST['email'] ?? '');
$user['phone'] = isset($_POST['phone']) ? str_replace([' ','-','/','\\','(',')'],'',$_POST['phone']) : '';
$user['msgID'] = trim($_POST['msgID'] ?? '');
$user['notEml'] = $_POST['notEml'] ?? 0;
$user['notTlg'] = $_POST['notTlg'] ?? 0;
$user['notSms'] = $_POST['notSms'] ?? 0;
$user['lang'] = $_POST['lang'] ?? $set['language'];
$user['pword'] = $_POST['pword'] ?? '';
$user['grpID'] = $_POST['grpID'] ?? $set['selfRegGrp'];
$user['xDate'] = $_POST['xDate'] ?? ''; //account expiration date
$catID = $_POST["catID"] ?? '';
$usrID = $_POST["usrID"] ?? ''; //user ID (new owner)
$fromEvtD = $_POST["fromEvtD"] ?? '';
$tillEvtD = $_POST["tillEvtD"] ?? '';
$fromCreD = $_POST["fromCreD"] ?? '';
$tillCreD = $_POST["tillCreD"] ?? '';

function catList($selCid) {
	global $ax;
	
	$stH = dbQuery("SELECT `ID`,`name`,`color`,`bgColor` FROM `categories` ORDER BY `sequence`");
	echo "<option value='*'>{$ax['usr_all_cats']}&nbsp;</option>\n";
	while (list($ID,$name,$color,$bgColor) = $stH->fetch(PDO::FETCH_NUM)) {
		$selected = ($selCid == $ID) ? ' selected' : '';
		$catColor = ($color ? "color:{$color};" : '').($bgColor ? "background-color:{$bgColor};" : '');
		echo "<option value='{$ID}'".($catColor ? " style='{$catColor}'" : '')."{$selected}>{$name}</option>\n";
	}
}

function usrList($uid,$selUid) {
	global $ax, $usr;
	
	$stH = dbQuery("SELECT `ID`,`name`,`email` FROM `users`WHERE `status` >= 0 ORDER BY `name`");
	echo "<option hidden value=''>{$ax['usr_select']}&nbsp;</option>\n";
	while (list($ID,$name,$email) = $stH->fetch(PDO::FETCH_NUM)) {
		if ($ID == 1 or $ID == $uid) { continue; } //public or current user 
		$selected = ($selUid == $ID) ? ' selected' : '';
		echo "<option value='{$ID}'{$selected}>{$name} ({$email})</option>\n";
	}
}

function listUsers() {
	global $ax, $usr;

	echo "<fieldset><legend>{$ax['usr_list_of_users']}</legend>\n";
	$stH = stPrep("SELECT u.`ID`, u.`name`, u.`email`, u.`phone`, u.`msingID`, u.`notSrvs`, u.`language`, u.`expDate`, u.`login0`, u.`login1`, u.`loginCnt`, g.`name` AS gname, g.`color` FROM `users` AS u INNER JOIN `groups` AS g ON g.`ID` = u.`groupID` WHERE u.`status` >= 0 ORDER BY CASE WHEN u.`ID` <= 2 THEN u.`ID` ELSE u.`name` END");
	stExec($stH,null);
	$rows = $stH->fetchAll(PDO::FETCH_ASSOC);
	echo "<table class='list'>\n";
	echo "<tr>\n<th>&nbsp;{$ax['id']}&nbsp;</th><th>{$ax['usr_name']}</th><th>{$ax['usr_email']}</th><th>{$ax['usr_phone_br']}</th><th>{$ax['usr_tg_id_br']}</th><th>{$ax['usr_not_via_br']}</th><th>{$ax['usr_language']}</th><th>{$ax['usr_group']}</th><th>{$ax['usr_expires']}</th><th>{$ax['usr_login_0']}</th><th>{$ax['usr_login_1']}</th><th>{$ax['usr_login_cnt']}</th><td colspan='3'></td></tr>\n";
	foreach ($rows as $user) {
		$xDate = IDtoDD($user['expDate']);
		$firstLoginD = IDtoDD($user['login0']);
		$lastLoginD = IDtoDD($user['login1']);
		$style = $user['color'] ? " style='background-color:{$user['color']};'" : '';
		$notVia = rtrim((strpos($user['notSrvs'],'E') !== false ? 'E+' : '').(strpos($user['notSrvs'],'T') !== false ? 'T+' : '').(strpos($user['notSrvs'],'S') !== false ? 'S+' : ''),'+');
		echo "<tr><td>{$user['ID']}</td><td><b>{$user['name']}</b></td><td>{$user['email']}</td><td>{$user['phone']}</td><td>{$user['msingID']}</td><td>{$notVia}</td><td>".ucfirst($user['language'])."</td>";
		echo "<td{$style}>{$user['gname']}</td><td>{$xDate}</td><td>{$firstLoginD}</td><td>{$lastLoginD}</td><td>{$user['loginCnt']}</td><td>";
		echo ($usr['privs'] == 9 or $user['ID'] != 2) ? "<button type='button' onclick='index({state:`edit`,uid:{$user['ID']}});'>{$ax['usr_edit']}</button>&ensp;" : '';
		echo "<button type='button' onclick='index({state:`trans`,uid:{$user['ID']}});'>{$ax['usr_transfer_evts']}</button>&ensp;";
		echo ($user['ID'] > 2 and $user['ID'] != $usr['ID']) ? "<button type='button' onclick='delConfirm(`usr`,{$user['ID']},`{$ax['usr_delete']} {$user['name']}`);'>{$ax['usr_delete']}</button>" : '';
		echo "</td></tr>\n";
	}
	echo "</table>\n";
	echo "</fieldset>
<button type='button' onclick='index({state:`add`});'>{$ax['usr_add']}</button>&ensp;
<button type='button' onclick='index({cP:83});'>{$ax['usr_go_to_groups']}</button>\n";
}

function editUser(&$user) {
	global $formCal, $ax, $set, $usr, $state;

	$uid = $user['id'];
	echo "<form action='index.php' method='post'>
{$formCal}
<fieldset>";
	if ($state != 'add' and !isset($_POST["uName"])) {
		$stH = stPrep("SELECT * FROM `users` WHERE `ID` = ?");
		stExec($stH,[$uid]);
		$row = $stH->fetch(PDO::FETCH_ASSOC);
		$stH = null;
		if ($row) {
			$user['name'] = $row['name'];
			$user['mail'] = $row['email'];
			$user['phone'] = $row['phone'];
			$user['msgID'] = $row['msingID'];
			$user['notEml'] = (strpos($row['notSrvs'],'E') !== false) ? 1 : 0;
			$user['notTlg'] = (strpos($row['notSrvs'],'T') !== false) ? 1 : 0;
			$user['notSms'] = (strpos($row['notSrvs'],'S') !== false) ? 1 : 0;
			$user['lang'] = $row['language'] ?: $set['language'];
			$user['grpID'] = $row['groupID'];
			$user['xDate'] = IDtoDD($row['expDate']);
		}
		$pwStar = "<span class='hired'>*</span>";
		echo "<legend>{$ax['usr_edit_user']}</legend>\n";
	} else {
		$pwStar = '';
		echo "<legend>{$ax['usr_add']}</legend>\n";
	}
	echo "<input type='hidden' name='uid' id='uid' value='{$uid}'>
		<input type='hidden' name='state' id='state' value='{$state}'>\n";
	echo "<table class='list'>\n";
	if ($state != 'add') { echo "<tr><td>{$ax['id']}:</td><td>&nbsp;{$user['id']}</td></tr>\n"; }
	echo "<tr><td>{$ax['usr_name']}:</td><td><input type='text' id='uName' name='uName' size='30' value='{$user['name']}'></td></tr>\n";
	if ($uid != 1) { //not public access
		echo "<tr><td>{$ax['usr_email']}:</td><td><input type='text' name='email' size='30' value='{$user['mail']}'></td></tr>\n";
		echo "<tr><td>{$ax['usr_phone']}:</td><td><input type='text' name='phone' size='30' maxlength='14' value='{$user['phone']}'></td></tr>\n";
		echo "<tr><td>{$ax['usr_tg_id']}:</td><td><input type='text' name='msgID' size='30' maxlength='14' value='{$user['msgID']}'></td></tr>\n";
		echo "<tr><td>{$ax['usr_not_via']}:</td><td><label><input type='checkbox' name='notEml' value='1'".($user['notEml'] ? " checked" : '').">{$ax['email']}</label>&ensp;<label><input type='checkbox' name='notTlg' value='1'".($user['notTlg'] ? " checked" : '').">{$ax['telegram']}</label>&ensp;<label><input type='checkbox' name='notSms' value='1'".($user['notSms'] ? " checked" : '').">{$ax['sms']}</label></td>\n";
		echo "<tr><td>{$ax['usr_ui_language']}:</td><td><select name='lang'>\n";
		$files = preg_grep("~^ui-[a-z]+\.php$~",scandir("lang/"));
		foreach ($files as $file) {
			$lang = strtolower(substr($file,3,-4));
			echo "<option value='{$lang}'".(strtolower($user['lang']) == $lang ? ' selected' : '').'>'.ucfirst($lang)."</option>\n";
		}
		echo "</select></td></tr>\n";
		echo "<tr><td>{$ax['usr_password']} {$pwStar}:</td><td><input type='password' id='pword' name='pword' value='' size='30'><span class='eye' onclick='pwShow(`pword`)'>&#128065;</span></td></tr>\n";
		if ($pwStar) { echo "<tr><td colspan='2'>{$pwStar}<span class='fontS'> {$ax['usr_if_changing_pw']}</span></td></tr>\n"; }
	}
	echo "<tr><td>{$ax['usr_group']}:</td>";
	if ($uid == $usr['ID'] or $uid == 2) { //can't put yourself or the admin in a different group or change the account expiry date
		$stH = stPrep("SELECT `name`,`color` FROM `groups` WHERE `ID` = ?");
		stExec($stH,[$user['grpID']]);
		$row = $stH->fetch(PDO::FETCH_ASSOC);
		$stH = null;
		$color = $row['color'] ? " style='background-color:{$row['color']};'" : '';
		echo "<td><input type='hidden' id='grpID' name='grpID' value='{$user['grpID']}'><span{$color}>{$row['name']}</span></td>\n";
		if ($user['xDate']) {
			echo "<tr><td>{$ax['usr_expir_date']}:</td><td><input class='date' type='hidden' name='xDate' value='{$user['xDate']}'><span>{$user['xDate']}</span>\n";
		}
	} else {
		$stH = stPrep("SELECT `ID`,`name`,`color` FROM `groups` WHERE `status` >= 0 ORDER BY `ID`");
		stExec($stH,null);
		echo "<td><select name='grpID'>\n";
		while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
			if ($usr['privs'] == 9 or $row['ID'] != 2) {
				$color = $row['color'] ? " style='background-color:{$row['color']};'" : '';
				$selected = $row['ID'] == $user['grpID'] ? ' selected' : '';
				echo "<option value='{$row['ID']}'{$color}{$selected}>{$row['name']}</option>\n";
			}
		}
		echo "</select></td></tr>\n";
		echo "<tr><td>{$ax['usr_expir_date']}:</td><td><input class='date' type='text' name='xDate' id='xDate' size='10' maxlength='10' value='{$user['xDate']}'><span class='xDate' title=\"{$ax['usr_select_exp_date']}\" onclick='dPicker(1,``,`xDate`);return false;'>&#x1F4C5;</span>&ensp;({$ax['usr_blank_none']})</td></tr>\n";
	}
	echo "</table>\n</fieldset>\n";
	if ($state == 'add') {
		echo "<button type='submit' name='addExe' value='y'>{$ax['usr_add_profile']}</button>";
	} else {
		echo "<button type='submit' name='updExe' value='y'>{$ax['usr_upd_profile']}</button>";
	}
	echo "&emsp;<button type='submit' name='back' value='y'>{$ax['back']}</button>
</form>\n";
}

function transferEvents(&$user) {
	global $formCal, $ax, $state, $catID, $fromEvtD, $tillEvtD, $fromCreD, $tillCreD, $usrID;

	$uid = $user['id'];
	$stH = stPrep("SELECT `name`, `email` FROM `users` WHERE `ID` = ?");
	stExec($stH,[$uid]);
	$row = $stH->fetch(PDO::FETCH_ASSOC);
	$stH = null;
	echo "<form action='index.php' method='post'>
{$formCal}
<fieldset><legend>{$ax['usr_transfer_ownership']}</legend>";
	echo "<input type='hidden' name='uid' id='uid' value='{$uid}'>\n";
	echo "<input type='hidden' name='state' id='state' value='{$state}'>\n";
	echo "<div class='bold'>{$ax['usr_cur_owner']}: {$row['name']} ({$row['email']})</div>";
	echo "<br>\n";
	echo "<table class='list'>\n";
	echo "<tr><td>{$ax['usr_event_cat']}:</td><td><select name='catID'>\n";
	catList($catID);
	echo "</select></td></tr>\n";
	echo "<tr>\n<td>{$ax['usr_sdate_between']}:<span class='sup'>*</span></td><td>
<input class='date' type='text' name='fromEvtD' id='fromEvtD' value='$fromEvtD'>
<span class='dtPick' title=\"{$ax['usr_select_start_date']}\" onclick='dPicker(1,``,`fromEvtD`); return false;'>&#x1F4C5;</span> &#8211;
<input class='date' type='text' name='tillEvtD' id='tillEvtD' value='$tillEvtD'>
<span class='dtPick' title=\"{$ax['usr_select_end_date']}\" onclick='dPicker(1,``,`tillEvtD`); return false;'>&#x1F4C5;</span></td>\n</tr>";
	echo "<tr>\n<td>{$ax['usr_cdate_between']}:<span class='sup'>*</span></td><td>
<input class='date' type='text' name='fromCreD' id='fromCreD' value='$fromCreD'>
<span class='dtPick' title=\"{$ax['usr_select_start_date']}\" onclick='dPicker(1,``,`fromCreD`); return false;'>&#x1F4C5;</span> &#8211;
<input class='date' type='text' name='tillCreD' id='tillCreD' value='$tillCreD'>
<span class='dtPick' title=\"{$ax['usr_select_end_date']}\" onclick='dPicker(1,``,`tillCreD`); return false;'>&#x1F4C5;</span></td>\n</tr>";
	echo "<tr><td colspan='2'><span class='sup'>*</span><span class='fontS'>{$ax['usr_blank_no_limit']}</span></td></tr>\n";
	echo "<tr><td colspan='2'>&nbsp;</td></tr>\n";
	echo "<tr><td>{$ax['usr_new_owner']}:</td><td><select name='usrID'>\n";
	usrList($uid,$usrID);
	echo "</select>\n";
	echo "</td></tr>\n";
	echo "</table>\n";
	echo "<br>\n";
	echo "<div class='floatC hired'>{$ax['usr_no_undone']}!</div>\n";
	echo "</fieldset>\n";
	echo "<button type='submit' name='trfExe' value='y'>{$ax['usr_transfer']}</button>";
	echo "&emsp;<button type='submit' name='back' value='y'>{$ax['back']}</button>
</form>\n";
}

function addUser(&$user) { //add user account
	global $ax, $state, $today;

	do {
		//validate input
		if (!$user['name'] or !$user['mail'] or !$user['pword']) { $msg = 'E'.$ax['usr_cred_required']; break; }
		if (strpos($user['pword'],'~') !== false) { $msg = 'E'.$ax['pw_no_chars']; break; }
		if (!preg_match("/^[\w\s\._-]{2,}$/u", $user['name'])) { $msg = 'E'.$ax['usr_un_invalid']; break; }
		if (!filter_var($user['mail'],FILTER_VALIDATE_EMAIL)) { $msg = 'E'.$ax['usr_em_invalid']; break; }
		if ($user['phone'] and !preg_match("/^[+0][\d]{8,18}$/",$user['phone'])) { $msg = 'E'.$ax['usr_ph_invalid']; break; }
		//add to database
		$stH = stPrep("SELECT `name`,`email` FROM `users` WHERE (`name` = ? OR `email` = ?) AND `status` >= 0");
		stExec($stH,[$user['name'],$user['mail']]);
		$row = $stH->fetch(PDO::FETCH_ASSOC);
		$stH = null;
		if ($row) { // name or email already exists
			$msg = $row['name'] == $user['name'] ? 'E'.$ax['usr_name_exists'] : 'E'.$ax['usr_email_exists'];
			break;
		}
		$xDate = $user['xDate'] ? DDtoID($user['xDate']) : '9999-00-00';
		if ($xDate === false or $xDate <= $today)  { $msg = 'E'.$ax['usr_xd_invalid']; break; }
		$password = md5($user['pword']);
		$notSrvs = ($user['notEml'] ? 'E' : '').($user['notTlg'] ? 'T' : '').($user['notSms'] ? 'S' : '');
		$stH = stPrep("INSERT INTO `users` (`name`,`password`,`email`,`phone`,`msingID`,`notSrvs`,`groupID`,`language`,`expDate`) VALUES (?,?,?,?,?,?,?,?,?)");
		stExec($stH,[$user['name'],$password,$user['mail'],$user['phone'],$user['msgID'],$notSrvs,$user['grpID'],$user['lang'],$xDate]);
		$user['id'] = dbLastRowId(); //set id to new user
		$msg = 'C'.$ax['usr_added'];
		$state = '';
	} while (false);
	return $msg;
}

function updateUser(&$user) { //update user account
	global $ax, $state, $today;

	do {
		//validate input
		if (!preg_match("/^[\w\s\._-]{2,}$/u", $user['name'])) { $msg = 'E'.$ax['usr_un_invalid']; break; }
		if ($user['id'] > 1) { //not Public User
			if (!filter_var($user['mail'],FILTER_VALIDATE_EMAIL)) { $msg = 'E'.$ax['usr_em_invalid']; break; }
			if ($user['phone'] and !preg_match("/^[+0][\d]{8,18}$/",$user['phone'])) { $msg = 'E'.$ax['usr_ph_invalid']; break; }
			if ($user['msgID'] and !preg_match("~^\+?[\d]{8,12}$~",$user['msgID'])) { $msg = 'E'.$ax['usr_tg_invalid']; break; }
		}
		//for duplicates
		$stH = stPrep("SELECT `name`,`email` FROM `users` WHERE (`name` = ? OR `email` = ?) AND `ID` != ? AND `status` >= 0");
		stExec($stH,[$user['name'],$user['mail'],$user['id']]);
		$row = $stH->fetch(PDO::FETCH_ASSOC);
		$stH = null;
		if ($row) { //name or email already exists
			$msg = $row['name'] == $user['name'] ? 'E'.$ax['usr_name_exists'] : 'E'.$ax['usr_email_exists'];
			break;
		}
		$xDate = $user['xDate'] ? DDtoID($user['xDate']) : '9999-00-00';
		if ($xDate === false or $xDate <= $today)  { $msg = 'E'.$ax['usr_xd_invalid']; break; }
		$notSrvs = ($user['notEml'] ? 'E' : '').($user['notTlg'] ? 'T' : '').($user['notSms'] ? 'S' : '');
		//update user profile
		if ($user['pword']) { //new password
			if (strpos($user['pword'],'~') !== false) { $msg = 'E'.$ax['pw_no_chars']; break; }
			$password = md5($user['pword']);
			$stH = stPrep("UPDATE `users` SET `name` = ?,`password` = ?,`email` = ?,`phone` = ?,`msingID` = ?,`notSrvs` = ?,`groupID` = ?,`language` = ?,`expDate` = ? WHERE `ID` = ?");
			stExec($stH,[$user['name'],$password,$user['mail'],$user['phone'],$user['msgID'],$notSrvs,$user['grpID'],$user['lang'],$xDate, $user['id']]);
		} else { //no new password
			$stH = stPrep("UPDATE `users` SET `name` = ?,`email` = ?,`phone` = ?,`msingID` = ?,`notSrvs` = ?,`groupID` = ?,`language` = ?,`expDate` = ? WHERE `ID` = ?");
			stExec($stH,[$user['name'],$user['mail'],$user['phone'],$user['msgID'],$notSrvs,$user['grpID'],$user['lang'],$xDate, $user['id']]);
		}
		$msg = 'C'.$ax['usr_updated'];
		$state = '';
	} while (false);
	return $msg;
}

function deleteUser($user) { //delete user account
	global $ax, $usr;
	
	do {
		if ($user['id'] == $usr['ID']) { $msg = 'E'.$ax['usr_cant_delete_yourself']; break; }
		$stH = stPrep("UPDATE `users` SET `status` = -1 WHERE `ID` = ?");
		stExec($stH,[$user['id']]);
		$deleted = $stH->rowCount();
		if (!$deleted) { $msg = 'E'."Database Error: {$ax['usr_not_deleted']}"; break; }
		$msg = 'C'.$ax['usr_deleted'];
	} while (false);
	return $msg;
}

function updateEvents($user) { //update events (transfer)
	global $ax, $state, $catID, $usrID, $fromEvtD, $tillEvtD, $fromCreD, $tillCreD;
	do {
		//validate input
		$sEvtDate = DDtoID($fromEvtD);
		$eEvtDate = DDtoID($tillEvtD);
		if ($sEvtDate === false or $eEvtDate === false) { $msg = 'E'.$ax['usr_invalid_sdata']; break; }
		if ($sEvtDate and $eEvtDate and $eEvtDate < $sEvtDate) { $msg = 'E'.$ax['usr_edate_lt_sdate']; break; }
		$sCreDate = DDtoID($fromCreD);
		$eCreDate = DDtoID($tillCreD);
		if ($sCreDate === false or $eCreDate === false) { $msg = 'E'.$ax['usr_invalid_cdata']; break; }
		if ($sCreDate and $eCreDate and $eCreDate < $sCreDate) { $msg = 'E'.$ax['usr_edate_lt_sdate']; break; }
		if (!$usrID) { $msg = 'E'.$ax['usr_no_new_owner']; break; }
		//update events
		$where = "`userID` = '{$user['id']}'";
		if ($catID !== '*') { $where .= " AND `catID` = '{$catID}'"; }
		if ($sEvtDate) { $where .= " AND `sDate` >= '{$sEvtDate}'"; }
		if ($eEvtDate) { $where .= " AND `sDate` <= '{$eEvtDate}'"; }
		if ($sCreDate) { $where .= " AND substr(aDateTime,1,10) >= '{$sCreDate}'"; }
		if ($eCreDate) { $where .= " AND substr(aDateTime,1,10) <= '{$eCreDate}'"; }
		$stH = stPrep("UPDATE `events` SET `userID` = ? WHERE {$where} AND `status` >= 0");
		stExec($stH,[$usrID]);
		$count = $stH->rowCount();
		$msg = "C{$ax['usr_evts_transferred']}: $count";
		$state = 'trans';
	} while (false);
	return $msg;
}

//control logic
if ($usr['privs'] >= 4) { //manager or admin
	$msg = '';
	if (isset($_POST['addExe'])) {
		$msg = addUser($user);
	} elseif (isset($_POST['updExe'])) {
		$msg = updateUser($user);
	} elseif (isset($_POST['delExe'])) {
		$msg = deleteUser($user);
	} elseif (isset($_POST['trfExe'])) {
		$msg = updateEvents($user);
	}
	$class = $msg ? ($msg[0] == 'E' ? 'error' : 'confirm') : '';
	$msg = substr($msg,1);
	echo $msg ? "<p class='{$class}'>{$msg}</p>\n" : "<p>&nbsp;</p>\n";
	echo "<div class='centerBox sBoxAd'>\n";
	if (!$state or isset($_POST['back'])) {
		listUsers(); //no add / no edit
	} elseif ($state == 'add' or $state == 'edit') {
		editUser($user); //add or edit
	} elseif ($state == 'trans') {
		transferEvents($user); //transfer events
	}
	echo "</div>\n";
} else {
	echo "<p class='error'>{$ax['no_way']}</p>\n";
}
?>
