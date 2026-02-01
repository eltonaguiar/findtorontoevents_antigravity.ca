<?php
/*
= LuxCal log in / register page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

function notifyReg($uName,$eMail) { //notify a new user registration
	global $ax, $set, $today;
		
	//compose email message
	$subject = "{$ax['log_new_reg']}: {$uName}";
	$msgBody = "
<p>{$ax['log_new_reg']}:</p><br>
<table>
	<tr><td>{$ax['log_un']}:</td><td>{$uName}</td></tr>
	<tr><td>{$ax['log_em']}:</td><td>{$eMail}</td></tr>
	<tr><td>{$ax['log_date_time']}:</td><td>".IDtoDD($today)." {$ax['at_time']} ".ITtoDT(date("H:i"))."</td></tr>
</table>
";
	//send email
	$errors = sendEml($subject,$msgBody,[$set['calendarEmail']],1,0,0);
	return $errors;
}

function loginUser(&$user) { //login user
	global $ax, $xCode, $cookie, $nowTS, $today;
	
	$msg = '';
	do {
		if (!$user['un_em']) { $msg = $ax['log_no_un_em']; break; }
		if (strpos($user['un_em'],'@') and !filter_var($user['un_em'],FILTER_VALIDATE_EMAIL)) { $msg = $ax['log_em_invalid']; break; }
		if (!$user['pword']) { $msg = $ax['log_no_pw']; break; }
		if (strpos($user['pword'],'~') !== false) { $msg = $ax['pw_no_chars']; break; }
		if (!$xCode OR $xCode > $nowTS OR $xCode < $nowTS-300) { $msg = $ax['log_time_out']; break; }
		$md5Pw = md5($user['pword']);
		$stH = stPrep("SELECT u.`ID`,u.`token`,u.`password`,u.`tPassword`,u.`language`,u.`expDate`,g.`privs` FROM `users` AS u INNER JOIN `groups` AS g ON g.`ID` = u.`groupID` WHERE (u.`name` = ? OR `email` = ?) AND (`password` = ? OR `tPassword` = ?) AND u.`status` >= 0");
		stExec($stH,[$user['un_em'],$user['un_em'],$md5Pw,$md5Pw]);
		$row = $stH->fetch(PDO::FETCH_ASSOC); //fetch user details
		$stH = null;
		if (!$row) { $msg = $ax['log_un_em_pw_invalid']; break; }
		if ($row['expDate'] < $today) { $msg = $ax['log_account_expired']; break; }
		if ($row['privs'] < 1) { $msg = $ax['log_no_rights']; break; }
		//all OK - login and start calendar
		$user['ID'] = $row['ID'];
		$token = md5(rand());
		$xToken = $cookie ? '+'.$token : '-'.$token; //+: remember, -: forget
		$dbToken = preg_replace("~-.{32}~i",'',$row['token']); //delete possible temp token
		$dbToken = substr($dbToken,-132).$xToken; //login from max. 5 devices
		$stH = stPrep("UPDATE `users` SET `password` = ?,`tPassword` = ?,`token` = ? WHERE `ID` = ?");
		stExec($stH,[$md5Pw,'',$dbToken,$row['ID']]);
		echo "<script>index({userID:{$row['ID']},userTK:`{$token}`,cP:0,cL:`{$row['language']}`,bake:{$cookie}});</script>\n"; //goto default page
	} while (false);
	return $msg;
}

function registerUser(&$user) { //register user
	global $ax, $set, $xCode, $nowTS, $rxPhone;
	
	$msg = '';
	do {
		if (!$xCode OR $xCode > $nowTS OR $xCode < $nowTS-300) { $msg = $ax['log_time_out']; break; }
		if (!$user['name']) { $msg = $ax['log_no_un']; break; }
		if (!$user['email']) { $msg = $ax['log_no_em']; break; }
		if (!preg_match("/^[\w\s\._-]{2,}$/u", $user['name'])) { $msg = $ax['log_un_invalid']; break; }
		if (!filter_var($user['email'],FILTER_VALIDATE_EMAIL)) { $msg = $ax['log_em_invalid']; break; }
		if ($user['phone'] and !preg_match($rxPhone,$user['phone'])) { $msg = $ax['log_ph_invalid']; break; }
		if ($set['selfRegQ'] and $user['selfRegA'] != $set['selfRegA']) {
			$_SESSION['srCnt'] = isset($_SESSION['srCnt']) ? $_SESSION['srCnt'] + 1 : 1;
			$msg = $_SESSION['srCnt'] < 4 ? $ax['log_sra_wrong'] : $ax['log_sra_wrong_4x'];
			break;
		}
		$stH = stPrep("SELECT `name` FROM `users` WHERE `name` = ? AND `status` >= 0");
		stExec($stH,[$user['name']]);
		if ($stH->fetchAll()) { $msg = $ax['log_un_exists']; break; } //un already exists
		$stH = stPrep("SELECT `email` FROM `users` WHERE `email` = ? AND `status` >= 0");
		stExec($stH,[$user['email']]);
		if ($stH->fetchAll()) { $msg = $ax['log_em_exists']; break; } //em already exists
		$newPw = substr(md5($user['name'].microtime()), 0, 8);
		$stH = stPrep("INSERT INTO `users` (`name`,`password`,`email`,`phone`,`groupID`,`language`) VALUES (?,?,?,?,?,?)");
		stExec($stH,[$user['name'],md5($newPw),$user['email'],$user['phone'],$set['selfRegGrp'],$user['lang']]);
		$stH = null;
		$msgBody = "
<p>{$ax['log_pw_msg']}: {$set['calendarTitle']}:</p><br>
<p>{$ax['log_un']}: <span class='bold'>{$user['name']}</span> {$ax['or']} {$ax['log_em']}: <span class='bold'>{$user['email']}</span></p>
<p>{$ax['log_pw']}: <span class='bold'>{$newPw}</span></p>
";
		$errors = sendEml($ax['log_pw_subject'],$msgBody,[$user['email']],1,0,0); //send email
		$user['un_em'] = $user['name']; //save for login
		if ($errors) { $msg = $ax['log_em_problem_not_sent']; }
		if ($set['selfRegNot']) {
			$errors = notifyReg($user['name'],$user['email']);
			if ($errors and empty($msg)) { $msg = $ax['log_em_problem_not_noti']; }
		}
	} while (false);
	return $msg;
}

function sendNewPw($user) { //send new password
	global $ax, $set;
	
	$msg = '';
	do {
		if (!$user['un_em']) { $msg = $ax['log_no_un_em']; break; }
		$stH = stPrep("SELECT `name`,`email` FROM `users` WHERE (`name` = ? OR `email` = ?) AND `status` >= 0");
		stExec($stH,[$user['un_em'],$user['un_em']]);
		$row = $stH->fetch(PDO::FETCH_ASSOC); //fetch user details
		$stH = null;
		if (!$row) { $msg = $ax['log_un_em_invalid']; break; }
		$email = $row['email'];
		$uname = $row['name'];
		$newPw = substr(md5($user['un_em'].microtime()),0,8);
		$cryptpw = md5($newPw);
		$stH = stPrep("UPDATE `users` SET `tPassword` = ? WHERE `name` = ? OR `email` = ?");
		stExec($stH,[md5($newPw),$user['un_em'],$user['un_em']]);
		$msgBody = "
<p>{$ax['log_pw_msg']}: {$set['calendarTitle']}:</p><br>
<p>{$ax['log_un']}: <span class='bold'>{$uname}</span> {$ax['or']} {$ax['log_em']}: <span class='bold'>{$email}</span></p>
<p>{$ax['log_pw']}: <span class='bold'>{$newPw}</span></p>
";
		$errors = sendEml($ax['log_npw_subject'],$msgBody,[$email],1,0,0); //send email
		if ($errors) { $msg = $ax['log_em_problem_not_sent']; }
	} while (false);
	return $msg;
}

function loginForm($user) { //login form
	global $opt, $formCal, $ax, $set, $nowTS;

	if (!empty($user['name'])) { $user['un_em'] = $user['name']; }
	echo "<fieldset class='logIn'><legend>{$ax['log_log_in']}</legend>
<form action='index.php' method='post'>
{$formCal}
<input type='hidden' name='xCode' value='{$nowTS}'>
<div class='input'><span class='icon'>&#x1f64e;&#x200d;&#x2642;&#xfe0f;</span><input type='text' id='uname' placeholder='{$ax['log_un_or_em']}' maxlength='36' name='un_em' value='{$user['un_em']}'></div>
<div class='input'><span class='icon'>&#128274;</span><input type='password' id='pword' placeholder='{$ax['log_pw']}' maxlength='20' name='pword' value=''><span class='eye' onclick='pwShow(`pword`)'>&#128065;</span></div>
<button type='submit' class='bold' name='action' value='logExe'>{$ax['log_log_in']}</button>\n";
	echo "<span class='floatR'><label><input type='checkbox' name='cookie' value='1' ".(!empty($opt['uI'][0]) ? " checked" : '')."> {$ax['log_remember_me']}</label></span>\n";
	echo "<br><br><hr>\n";
	if ($set['selfReg'] and (!isset($_SESSION['srCnt']) or $_SESSION['srCnt'] < 4)) {
		echo "<button class='floatR butLink' type='submit' name='action' value='rgr'>{$ax['log_register']}</button><br>\n";
	}
	echo "<button class='clear floatR butLink' type='submit' name='action' value='logSpw'>{$ax['log_send_new_pw']}</button>\n";
	echo "</form>
</fieldset>";
}

function registerForm($user) { //register form
	global $formCal, $set, $ax, $nowTS;

	if ($user['un_em']) {
		if (strpos($user['un_em'],'@')) {
			$user['email'] = $user['un_em'];
		} else {
			$user['name'] = $user['un_em'];
		}
	}
	echo "<form action='index.php' method='post'>
{$formCal}
<fieldset><legend>{$ax['log_register']}</legend>
<input type='hidden' name='xCode' value='{$nowTS}'>
<input type='hidden' name='un_em' value='{$user['un_em']}'>
{$ax['log_un']}<span class='hired'>*</span><br><input type='text' name='uname' id='uname' size='30' value='{$user['name']}'><br><br>
{$ax['log_em']}<span class='hired'>*</span><br><input type='text' name='email' size='30' value='{$user['email']}'><br><br>
{$ax['log_ph']}<br><input type='text' name='phone' size='30' value='{$user['phone']}'><br><br>
{$ax['log_ui_language']}&ensp;
<select name='lang'>\n";
	$files = preg_grep("~^ui-[a-z]+\.php$~",scandir("lang/"));
	foreach ($files as $file) {
		$lang = strtolower(substr($file,3,-4));
		echo "<option value='{$lang}'".(strtolower($user['lang']) == $lang ? ' selected' : '').'>'.ucfirst($lang)."</option>\n";
	}
	echo "</select><br><br>";
if ($set['selfRegQ']) {
	echo "<span class='bold'>{$set['selfRegQ']}?</span><span class='hired'>*</span><br>
{$ax['log_answer']}: <input type='text' name='selfRegA' size='25' value='{$user['selfRegA']}'><br><br>";
}
echo "<button class='bold' type='submit' name='action' value='rgrExe'>{$ax['log_register']}</button>&emsp;
<button type='submit' name='back' value='y'>{$ax['back']}</button>
</fieldset></form>\n";
}


//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); }

//initialize
$adminLang = (file_exists("./lang/ai-{$opt['cL']}.php")) ? $opt['cL'] : "english";
require "./lang/ai-{$adminLang}.php";
$msg = '';
$user = [];
$xCode = $_POST['xCode'] ?? '';
$user['un_em'] = $_POST['un_em'] ?? '';
$user['name'] = $_POST['uname'] ?? '';
$user['pword'] = $_POST['pword'] ?? '';
$user['email'] = $_POST['email'] ?? '';
$user['phone'] = isset($_POST['phone']) ? preg_replace("%[\s\\/-]%",'',$_POST['phone']) : '';
$user['selfRegA'] = $_POST['selfRegA'] ?? '';
$user['lang'] = $_POST['lang'] ?? $set['language'];
$cookie = empty($_POST['cookie']) ? '0' : '1';

//control logic
$msg = '';
$class = 'error';
$action = $_POST['action'] ?? '';

switch ($action) {
case "logExe": //login
	$msg = loginUser($user);
	$action = 'back';
	break;
case "logSpw": //send new password
	$msg = sendNewPw($user);
	if (!$msg) { $msg = $ax['log_npw_sent']; $class = 'confirm'; }
	$action = 'back';
	break;
case "rgrExe": //register
	$msg = registerUser($user);
	if (!$msg) { $msg = $ax['log_registered']; $class = 'confirm'; }
	$action = (!isset($_SESSION['srCnt']) or $_SESSION['srCnt'] < 4) ? 'rgr' : 'back'; //register form or back to login form
}

//display form
echo $msg ? "<p class='{$class}'>{$msg}</p>\n" : "<p>&nbsp;</p>\n";
echo "<div class='centerBox sBoxAd'>\n";
	if (!$action or $action == 'back') { //login form
		loginForm($user);
	} elseif ($action == 'rgr') { //register form
		registerForm($user);
	}
echo "</div>\n";
if ($set['logoXlPath'] and file_exists($set['logoXlPath'])) {
	echo "<img class='logoXL' src='{$set['logoXlPath']}' alt='logo' height='{$set['logoHeight']}'>\n";
}
echo '<script>$I("uname").focus();</script>'."\n";
?>