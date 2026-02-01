<?php
/*
= LuxCal user account data page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); }

//initialize
$adminLang = (file_exists("./lang/ai-{$opt['cL']}.php")) ? $opt['cL'] : "english";
require "./lang/ai-{$adminLang}.php";
$msg = '';

$user = array();
$xCode = $_POST['xCode'] ?? '';
$user['ID'] = $usr['ID'];
$user['name'] = $_POST['uname'] ?? $usr['name'];
$user['email'] = $_POST['email'] ?? $usr['email'];
$user['phone'] = isset($_POST['phone']) ? preg_replace("%[\s\\/-]%",'',$_POST['phone']) : $usr['phone'];
$user['msingID'] = $_POST['msingID'] ?? $usr['msingID'];
$user['notEml'] = isset($_POST['xCode']) ? ($_POST['notEml'] ?? 0) : (strpos($usr['notSrvs'],'E') !== false ? 1 : 0);
$user['notTlg'] = isset($_POST['xCode']) ? ($_POST['notTlg'] ?? 0) : (strpos($usr['notSrvs'],'T') !== false ? 1 : 0);
$user['notSms'] = isset($_POST['xCode']) ? ($_POST['notSms'] ?? 0) : (strpos($usr['notSrvs'],'S') !== false ? 1 : 0);
$user['lang'] = $_POST['lang'] ?? strtolower($usr['lang']);
$user['pword'] = $_POST['pword'] ?? '';
$user['pword2'] = $_POST['pword2'] ?? '';
$user['expDate'] = IDtoDD($usr['expDate']);

function changeUser($user) { //change user data
	global $ax, $xCode, $nowTS, $rxPhone;

	$msg = '';
	$lNewPw = trim($_POST["lNewPw"] ?? '');
	do {
		if (!$xCode OR $xCode > $nowTS OR $xCode < $nowTS-300) { $msg = $ax['log_time_out']; break; }
		if (!$user['name']) { $msg = $ax['log_no_un_em']; break; }
		if (!preg_match("~^[\w\s\-.]{2,}$~", $user['name'])) { $msg = $ax['log_un_invalid']; break; }
		if (!filter_var($user['email'],FILTER_VALIDATE_EMAIL)) { $msg = $ax['log_em_invalid']; break; }
		if ($user['phone'] and !preg_match($rxPhone,$user['phone'])) { $msg = $ax['log_ph_invalid']; break; }
		if ($user['msingID'] and !preg_match("~^\+?[\d]{8,12}$~",$user['msingID'])) { $msg = $ax['log_tg_invalid']; break; }
		if ($user['notTlg'] and !$user['msingID']) { $msg = $ax['log_tg_id_required']; break; }
		if ($user['notSms'] and !$user['phone']) { $msg = $ax['log_sm_nr_required']; break; }
		if ($user['pword'] != $user['pword2']) { $msg = $ax['log_pw_error']; break; }
		if (strpos($user['pword'],'~') !== false) { $msg = $ax['pw_no_chars']; break; }
		$stH = stPrep("SELECT `name`,`email` FROM `users` WHERE `ID` = ?");
		stExec($stH,[$user['ID']]);
		$row = $stH->fetch(PDO::FETCH_NUM); //fetch user details
		$stH = null;
		if (!$row) { $msg = $ax['log_un_em_pw_invalid']; break; }
		list($name,$email) = $row;

		if ($name != $user['name']) { //username changed
			$stH = stPrep("SELECT `ID` FROM `users` WHERE `ID` != ? AND `name` = ? AND `status` >= 0");
			stExec($stH,[$user['ID'],$user['name']]);
			if ($stH->fetchAll()) { $msg = $ax['log_new_un_exists']; break; } //un already exists
		}
		if ($email != $user['email']) {	//email changed	
			$stH = stPrep("SELECT `ID` FROM `users` WHERE `ID` != ? AND `email` = ? AND `status` >= 0");
			stExec($stH,[$user['ID'],$user['email']]);
			if ($stH->fetchAll()) { $msg = $ax['log_new_em_exists']; break; } //em already exists
		}
		$notSrvs = ($user['notEml'] ? 'E' : '').($user['notTlg'] ? 'T' : '').($user['notSms'] ? 'S' : '');
		$stH = stPrep("UPDATE `users` SET `name` = ?,`email` = ?,`phone` = ?,`msingID` = ?,`notSrvs` = ?,`language` = ? WHERE `ID` = ?");
		stExec($stH,[$user['name'],$user['email'],$user['phone'],$user['msingID'],$notSrvs,$user['lang'],$user['ID']]);
		if ($user['pword']) {
			$md5Pw = md5($user['pword']);
			$stH = stPrep("UPDATE `users` SET `password` = ? WHERE `ID` = ?");
			stExec($stH,[$md5Pw,$user['ID']]);
		}
	} while (false);
	return $msg;
}

function changeForm($user) { //change my data
	global $formCal, $ax, $set, $nowTS;

	$notServices = $set['emlService'] + $set['tlgService'] + $set['smsService'];
	
	echo "<legend>{$ax['log_change_my_data']}</legend>\n";
	if ($user['expDate']) {
		echo "<h4 class='red'>{$ax['log_expir_date']}: {$user['expDate']}</h4><br>\n";
	}
	echo "<form action='index.php' method='post'>
{$formCal}
<input type='hidden' name='xCode' value='{$nowTS}'>
<input type='hidden' name='expDate' value='{$user['expDate']}'>\n";
	if (!$set['emlService'] or $notServices < 2) { echo "<input type='hidden' name='notEml' value='{$user['notEml']}'>\n"; }
	if (!$set['tlgService'] or $notServices < 2) { echo "<input type='hidden' name='notTlg' value='{$user['notTlg']}'>\n"; }
	if (!$set['smsService'] or $notServices < 2) { echo "<input type='hidden' name='notSms' value='{$user['notSms']}'>\n"; }
	echo "{$ax['log_un']}<span class='hired'>*</span><br><input type='text' name='uname' size='40' value='{$user['name']}'><br><br>
{$ax['log_em']}<span class='hired'>*</span><br><input type='text' name='email' size='40' value='{$user['email']}'><br><br>
{$ax['log_ph']}<br><input type='text' name='phone' size='40' maxlength='20' value='{$user['phone']}'><br><br>
{$ax['log_tg']}<br><input type='text' name='msingID' size='40' maxlength='12' value='{$user['msingID']}'><br><br>\n";
	if ($notServices > 1) {
		echo "{$ax['usr_not_via']}:&emsp;";
		if ($set['emlService']) { echo "<label><input type='checkbox' name='notEml' value='1'".($user['notEml'] ? " checked" : '').">{$ax['email']}</label>&ensp;\n"; }
		if ($set['tlgService']) { echo "<label><input type='checkbox' name='notTlg' value='1'".($user['notTlg'] ? " checked" : '').">{$ax['telegram']}</label>&ensp;\n"; }
		if ($set['smsService']) { echo "<label><input type='checkbox' name='notSms' value='1'".($user['notSms'] ? " checked" : '').">{$ax['sms']}</label>\n"; }
		echo "<br><br>";
	}
	echo "{$ax['log_ui_language']}:&emsp;
<select name='lang'>\n";
	$files = preg_grep("~^ui-[a-z]+\.php$~",scandir("lang/"));
	foreach ($files as $file) {
		$lang = strtolower(substr($file,3,-4));
		echo "<option value='{$lang}'".($user['lang'] == $lang ? ' selected' : '').'>'.ucfirst($lang)."</option>\n";
	}
	echo "</select><br><br>
{$ax['log_new_pw']}<br><input type='password' id='pword' name='pword' size='40'><span class='eye' onclick='pwShow(`pword`)'>&#128065;</span><br><br>
{$ax['log_con_pw']}<br><input type='password' id='pword2' name='pword2' size='40'><span class='eye' onclick='pwShow(`pword2`)'>&#128065;</span><br><br>
<div class='floatC'>
<button type='submit' name='action' value='chgExe'>{$ax['log_save']}</button>&emsp;
<button type='button' name='action' onclick='index({cP:0,cL:`{$user['lang']}`});'>{$ax['log_done']}</button>
</div>
</form>\n";
}

//control logic
$msg = '';
$class = 'error';
$action = $_POST['action'] ?? '';

if ($action == "chgExe") { //change data
	$msg = changeUser($user);
	if (!$msg) { $msg = $ax['usr_updated']; $class = 'confirm'; }
}

//display form
echo $msg ? "<p class='{$class}'>{$msg}</p>\n" : "<p>&nbsp;</p>\n";
echo "<div class='centerBox sBoxAd'>\n<fieldset>\n";
changeForm($user); //change data form
echo "</fieldset>\n</div>\n";
?>