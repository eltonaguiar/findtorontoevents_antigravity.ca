<?php
/*
= User profile import script =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//set language
$adminLang = (file_exists("./lang/ai-{$opt['cL']}.php")) ? $opt['cL'] : "english";
require "./lang/ai-{$adminLang}.php";

/* sub-functions */

function processUserFields() {
	global $rxPhone, $set, $defGrpID, $defPword, $rplUsers;
	
	$errors = [];
	
	//get current user group IDs
	$stH = dbQuery("SELECT `ID` FROM `groups` WHERE `status` >= 0");
	$giUsed = $stH->fetchAll(PDO::FETCH_COLUMN,0);

	//get current user names and email addresses
	$unUsed = $emUsed = $phUsed = $ciUsed = [];
	$filter = $rplUsers ? "`ID` <= 2 AND " : '';
	$stH = dbQuery("SELECT `name`,`email`,`phone`,`msingID` FROM `users` WHERE {$filter}`status` >= 0");
 	while ($row = $stH->fetch(PDO::FETCH_NUM)) {
		$unUsed[] = $row[0];
		$emUsed[] = strtolower($row[1]);
		if ($row[2]) {
			$phUsed[] = $row[2];
		}
		if ($row[3]) {
			$ciUsed[] = $row[3];
		}
	}
	$nofUsers = count($_POST['uGpID']);
	for ($i = 0; $i < $nofUsers; $i++) {
		if (empty($_POST['uGpID'][$i])) { //group
			$_POST['uGpID'][$i] = $defGrpID;
		}
		if (!in_array($_POST['uGpID'][$i],$giUsed)) {
			$errors['uGpID'][$i] = 1;
		}
		if (empty($_POST['uName'][$i])) { //no username
			$errors['uName'][$i] = 1;
		} elseif (in_array($_POST['uName'][$i],$unUsed)) { //already in use
			$errors['uName'][$i] = 2;
		}
		if (empty($_POST['uMail'][$i]) or !filter_var($_POST['uMail'][$i],FILTER_VALIDATE_EMAIL)) { //no or invalid email address
			$errors['uMail'][$i] = 1;
		} elseif (in_array(strtolower($_POST['uMail'][$i]),$emUsed)) { //already in use
			$errors['uMail'][$i] = 2;
		}
		if (!empty($_POST['uPhon'][$i]) and !preg_match($rxPhone,$_POST['uPhon'][$i])) { //invalid phone number
			$errors['uPhon'][$i] = 1;
		} elseif (in_array(strtolower($_POST['uPhon'][$i]),$phUsed)) { //already in use
			$errors['uPhon'][$i] = 2;
		}
		if (!empty($_POST['uChID'][$i]) and !preg_match('~^[1-9]\d{6,14}$~',$_POST['uChID'][$i])) { //invalid Telegram chat ID
			$errors['uChID'][$i] = 1;
		} elseif (in_array($_POST['uChID'][$i],$ciUsed)) { //already in use
			$errors['uChID'][$i] = 2;
		}
		if (empty($_POST['uLang'][$i])) { //language
			$_POST['uLang'][$i] = $set['language'];
		}
		if (!file_exists("./lang/ai-".strtolower($_POST['uLang'][$i]).".php")) {
			$errors['uLang'][$i] = 1;
		}
		if (empty($_POST['uPwrd'][$i])) { //password
			$_POST['uPwrd'][$i] = $defPword;
		}
	}
	return $errors;
}


/* main functions */

function instructions() {
	global $ax;
	
	$stH = dbQuery("SELECT `ID`,`name` FROM `groups` WHERE `status` >= 0 ORDER BY `ID`");
	echo "<aside class='aside sBoxAd'>{$ax['xpl_import_user']}
<table class='list'>
<tr><th style='width:auto;'>ID</th><th style='width:auto;'>{$ax['iex_group']}</th></tr>\n";
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		echo "<tr><td class='floatC'>{$row['ID']}</td><td>&nbsp;{$row['name']}</td></tr>\n";
	}
	echo "</table>\n</aside>\n";
}

function uploadFile() {
global $formCal, $ax, $delimiter, $defGrpID, $defPword, $rplUsers;

echo "<form action='index.php' method='post' enctype='multipart/form-data'>
{$formCal}
<input type='hidden' name='MAX_FILE_SIZE' value='1000000'>
<fieldset><legend>{$ax['iex_upload_csv']}</legend>\n
<table class='list'>
<tr><td class='label'>{$ax['iex_file']}:</td><td><input type='file' name='fileName'></td></tr>
<tr><td class='label'>{$ax['iex_fields_sep_by']}:</td><td><input type='text' name='delimiter' maxlength='2' value='{$delimiter}' size='1'></td></tr>
<tr><td class='label'>{$ax['iex_default_grp_id']}:</td><td><input type='text' name='defGrpID' maxlength='2' value='{$defGrpID}' size='1'> ({$ax['iex_if_no_grp']})</td></tr>
<tr><td class='label'>{$ax['iex_default_pword']}:</td><td><input type='text' name='defPword' value='{$defPword}' size='8'> ({$ax['iex_if_no_pw']})</td></tr>
<tr><td class='label'>{$ax['iex_replace_users']}:</td><td><input type='checkbox' name='rplUsers' value='1'".($rplUsers == 1 ? ' checked' : '')."></td></tr>
</table>
</fieldset>
<button type='submit' name='uploadFile' value='y'>{$ax['iex_upload_file']}</button>
</form>
<div style='clear:right'></div>\n";
}
	
function processUpload() {
	global $ax, $set, $defGrpID, $defPword;
	
	$tmpName = $_FILES['fileName']['tmp_name'];
	if (!$tmpName) { return $ax['iex_no_file_name']; } //csv file missing
	$csvArray = file($tmpName, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
	unlink($tmpName); //release file

	//process user profiles from CSV array
 	$lineNr = 0;
	foreach ($csvArray as $csvUser) {
		$csvUser = strip_tags(html_entity_decode($csvUser)); //remove html tags
		$user = preg_split("%(?<!\\\\){$_POST['delimiter']}%",$csvUser,7); //split on delimiter not escaped by \
		array_walk($user,function(&$v,$k) {$v = trim($v,' "\'');}); //remove blanks & quotes
		$lineNr++;
		if ((!empty($user[0]) and !ctype_digit($user[0])) and $lineNr = 1) { continue; } //flush header line
		array_push($user,'','','',''); //pad to ensure min. 7 fields
		//user[] (0:group ID, 1:username, 2:email address, 3:phone number, 4:chat ID, 5:language, 6:password)
		
		//validate user data
		if (count($user) < 3 or empty($user[1]) or empty($user[2])) { //too few fields or no user name or no email address 
			return "{$ax['iex_csv_file_error_on_line']}: {$lineNr} (first three fields should be filled)";
		}
		if (!$user[0]) { //user group
			$user[0] = $defGrpID;
		}
		$user[3] = empty($user[3]) ? '' : str_replace([' ','-','/','\\','(',')'],'',$user[3]); //phone number
		if (empty($user[5]) or !file_exists("./lang/ai-".strtolower($user[4]).".php")) { //language
			$user[5] = $set['language'];
		}
		if (empty($user[6])) { //password
			$user[6] = $defPword;
		}
		//save user data
		$_POST['uGpID'][] = $user[0];
		$_POST['uName'][] = $user[1];
		$_POST['uMail'][] = $user[2];
		$_POST['uPhon'][] = $user[3];
		$_POST['uChID'][] = $user[4];
		$_POST['uLang'][] = $user[5];
		$_POST['uPwrd'][] = $user[6];
	}
	if (empty($_POST['uGpID']) or count($_POST['uGpID']) == 0) { return $ax['iex_no_user_profiles']; } //no user profiles
	return ''; //no error
}

function displayUsers($errors) {
	global $formCal, $ax, $delimiter, $defGrpID, $defPword, $rplUsers;

	$nofErrors = array_sum(array_map("count", $errors));
	if ($nofErrors) {
		echo "<p class='error'>{$ax['iex_number_of_errors']}: {$nofErrors} ({$ax['iex_bgnd_highlighted']})</p><br>";
		echo "<p><span class='bar inputError'>&nbsp;</span> : {$ax['iex_invalid']}&emsp;<span class='bar inputWarning'>&nbsp;</span> : {$ax['iex_in_use']}</p>";
	} else {
		echo "<p class='confirm'>{$ax['iex_number_of_errors']}: {$nofErrors}</p><br>";
		echo "<p>&nbsp;</p>";
	}
	echo "<br>\n<h3>{$ax['iex_verify_user_list']} \"{$ax['iex_add_users']}\"</h3>\n<br>\n";
//display user profile list
	echo "<form action='index.php' method='post'>
{$formCal}
<input type='hidden' name='delimiter' value='{$delimiter}'>
<input type='hidden' name='defGrpID' value='{$defGrpID}'>
<input type='hidden' name='defPword' value='{$defPword}'>
<input type='hidden' name='rplUsers' value='{$rplUsers}'>\n";
	$nofUsers = count($_POST['uGpID']);
	echo "<table>
		<tr><th>&nbsp;#&nbsp;</th><th>{$ax['iex_group']}</th><th>{$ax['iex_name']}</th><th>{$ax['iex_email']}</th><th>{$ax['iex_phone']}</th><th>{$ax['iex_msgID']}</th><th>{$ax['iex_lang']}</th><th>{$ax['iex_pword']}</th></tr>\n";
	for ($i = 0; $i < $nofUsers; $i++) {
		$gpc = (!empty($errors['uGpID'][$i])) ? " class='inputError'" : '';
		$unc = empty($errors['uName'][$i]) ? '' : ($errors['uName'][$i] == 1 ? " class='inputError'" : " class='inputWarning'");
		$emc = empty($errors['uMail'][$i]) ? '' : ($errors['uMail'][$i] == 1 ? " class='inputError'" : " class='inputWarning'");
		$phc = empty($errors['uPhon'][$i]) ? '' : ($errors['uPhon'][$i] == 1 ? " class='inputError'" : " class='inputWarning'");
		$cic = empty($errors['uChID'][$i]) ? '' : ($errors['uChID'][$i] == 1 ? " class='inputError'" : " class='inputWarning'");
		$lgc = (!empty($errors['uLang'][$i])) ? " class='inputError'" : '';
		$nr = $i+1;
		echo "<tr>
<td>{$nr}</td>
<td><input{$gpc} type='text' size='2' name='uGpID[]' value='{$_POST['uGpID'][$i]}'></td>
<td><input{$unc} type='text' size='15' name='uName[]' value='{$_POST['uName'][$i]}'></td>
<td><input{$emc} type='text' size='30' name='uMail[]' value='{$_POST['uMail'][$i]}'></td>
<td><input{$phc} type='text' size='15' name='uPhon[]' value='{$_POST['uPhon'][$i]}'></td>
<td><input{$cic} type='text' size='12' name='uChID[]' value='{$_POST['uChID'][$i]}'></td>
<td><input{$lgc} type='text' size='10' name='uLang[]' value='{$_POST['uLang'][$i]}'></td>
<td><input type='text' size='32' name='uPwrd[]' value='{$_POST['uPwrd'][$i]}'></td>\n";
		echo "</tr>\n";
	}
	echo "</table>
<br>\n";
echo "<button type='submit' name='addUsers' value='y'>{$ax['iex_add_users']}</button>\n";
echo "<button type='submit' name='back' value='y'>{$ax['back']}</button>
</form>\n";
}

function addUsers() {
	global $ax, $rplUsers;

	$nofUsers = count($_POST['uGpID']);
	$added = $deleted = 0;
	if ($rplUsers) { //delete users, except public user and admin
		$stH = stPrep("UPDATE `users` SET `status` = -1 WHERE `ID` > 2 and `status` = 0"); //delete active users with ID > 2
		stExec($stH,[]);
		$deleted += $stH->rowCount();
	}
	for ($i = 0; $i < $nofUsers; $i++) {
		if (strlen($_POST['uPwrd'][$i]) != 32) { //password not encrypted
			$_POST['uPwrd'][$i] = md5($_POST['uPwrd'][$i]);
		}
		$stH = stPrep("INSERT INTO `users` (`name`,`password`,`email`,`phone`,`msingID`,`groupID`,`language`) VALUES (?,?,?,?,?,?,?)");
		stExec($stH,[$_POST['uName'][$i],$_POST['uPwrd'][$i],$_POST['uMail'][$i],$_POST['uPhon'][$i],$_POST['uChID'][$i],$_POST['uGpID'][$i],$_POST['uLang'][$i]]);
		$added++;
	}
	$msg = $added." ".$ax['iex_users_added'];
	if ($deleted) {
		$msg .= " / {$deleted} {$ax['iex_users_deleted']}";
	}
	return $msg;
}


//initialize
$delimiter = $_POST['delimiter'] ?? ',';
$defGrpID = $_POST['defGrpID'] ?? 3;
$defPword = $_POST['defPword'] ?? 'password';
$rplUsers = $_POST['rplUsers'] ?? '';
$msg = ""; $errors = 0;

/* control logic */

if ($usr['privs'] >= 4) { //manager or admin
	if (isset($_POST['uploadFile'])) {
		$msg = processUpload();
	}
	if ((isset($_POST['uploadFile']) and !$msg) or isset($_POST['addUsers'])) {
		$errors = processUserFields(); //user fields in $_POST arrays
	}
	if (isset($_POST['addUsers']) and !$errors) {
		$msg = addUsers(); //add events to calendar
	}
	echo $msg ? "<p class='error'>{$msg}</p>\n" : "<p>&nbsp;</p>\n";
	if (!isset($_POST['uploadFile']) and !isset($_POST['addUsers']) or (isset($_POST['uploadFile']) and $msg)) {
		instructions();
	}
	echo "<div class='centerBox sBoxAd'>\n";
	if (!isset($_POST['uploadFile']) and !isset($_POST['addUsers']) or (isset($_POST['uploadFile']) and $msg)) {
		uploadFile();
	} elseif (!isset($_POST['addUsers']) or $errors) {
		displayUsers($errors); //file uploaded or errors, display user profiles
	} else {
		echo "<button type='button' onclick='index({delimiter:`{$delimiter}`,defGrpID:`{$defGrpID}`,defPword:`{$defPword}`,rplUsers:`{$rplUsers}`});'>{$ax['back']}</button>\n";
	}
	echo "</div>\n";
} else {
	echo "<p class='error'>{$ax['no_way']}</p>\n";
}
?>
