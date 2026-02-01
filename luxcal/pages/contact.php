<?php
/*
= contact message script =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

function contactForm() {
	global $formCal, $xx, $visName, $visMail, $visSubj, $visMsg;

	echo"<fieldset class='contact'><legend>{$xx['con_msg_to_admin']}</legend>
<form action='index.php' method='post'>
<p><span class='msgCol1'>Name<span class='red'>*</span>:</span><input type='text' name='visName' value='{$visName}' size='30'></p>
<p><span class='msgCol1'>Email Address<span class='red'>*</span>:</span><input type='text' name='visMail' value='{$visMail}' size='30'></p>
<div class='hpot'>Your URL:<br><input type='text' name='url' size='30'></div>
<p><span class='msgCol1'>Subject<span class='red'>*</span>:</span><input type='text' name='visSubj' value='{$visSubj}' size='30'></p>
<br>
<p>{$xx['con_message']}<span class='red'>*</span>:</p>
<textarea class='message' name='visMsg' rows='4'>{$visMsg}</textarea>
<br><br>
<button type='submit' name='sendMsg' value='y'>{$xx['con_send_msg']}</button>
</form>
</fieldset>
";
}

function validateForm() { //validate form fields
	global $xx, $visName, $visMail, $visSubj, $visMsg;
	
	$msg = '';
	//validate input
	if(empty($visName) or empty($visMail) or empty($visSubj) or empty($visMsg )) {
		$msg .= "{$xx['con_fill_in_all_fields']}.<br>";
	}
	if (!empty($visName) and !preg_match("%^[\p{L}\s.\-']{2,}$%u", $visName)) {
		$msg .= "{$xx['con_invalid_name']}.<br>";
	}
	if (!empty($visMail) and !preg_match("/^\D\w*?(\.{0,1}\w+?){0,2}@((\w|-){2,}\.){1,2}\D{2,4}$/", $visMail)) {
		$msg .= "{$xx['con_invalid_email']}.<br>";
	}
	if (strpos($visMsg,'http') !== false or strpos($visMsg,'www.') !== false) {
		$msg .= "{$xx['con_no_urls']}.<br>";
	}
	return $msg;
}


function sendMessage() { //send message
	global $xx, $set, $inPot, $visName, $visMail, $visSubj, $visMsg;

	if ($inPot) {
		return 'honey'; //caught in honey pot
	}
	
	$msgBody = "<h5>{$xx['con_con_msg']}.</h5>
<br><br>
<table>
<tr><td class='bold'>{$xx['con_from']}:</td><td>{$visName} ({$visMail})</td></tr>
<tr><td class='bold'>{$xx['con_subject']}:</td><td>{$visSubj}</td></tr>
<tr><td class='bold'>{$xx['con_message']}:</td><td>".nl2br($visMsg)."</td></tr>
</table>\n";
	$errors = sendEml($visSubj,$msgBody,[$set['calendarEmail']],2,0,0);
	
	$msgBody = "<h5>{$xx['con_thank_you']}.</h5>
<br><br>
<table>
<tr><td class='bold'>{$xx['con_from']}:</td><td>{$visName} ({$visMail})</td></tr>
<tr><td class='bold'>{$xx['con_subject']}:</td><td>{$visSubj}</td></tr>
<tr><td class='bold'>{$xx['con_message']}:</td><td>".nl2br($visMsg)."</td></tr>
</table>
<br><br>
<p>{$xx['con_get_reply']}.</p>\n";
	sendEml($xx['con_your_cal_msg'],$msgBody,[$visMail],2,0,0);
	
	return $errors;
}

function messageSent() { //confirm message sent
	global $xx, $today, $wkDays, $dtStamp, $visName, $visMail, $visSubj, $visMsg;
	
	$dtStamp = $wkDays[date("w")]." ".IDtoDD($today)." {$xx['at_time']} ".ITtoDT(date("H:i")); //date/time stamp
	echo "<p>{$xx['con_thank_you']} ".$visName.".</p>
<br>
<p>{$xx['con_your_msg']}</p>
<br>
<fieldset>
<table class='contact'>
<tr><td class='bold'>{$xx['con_date']}:</td><td>".$dtStamp."</td></tr>
<tr><td class='bold'>{$xx['con_name']}:</td><td>".$visName."</td></tr>
<tr><td class='bold'>{$xx['con_email']}:</td><td>".$visMail."</td></tr>
<tr><td class='bold'>{$xx['con_subject']}:</td><td>".$visSubj."</td></tr>
<tr><td class='bold'>{$xx['con_message']}:</td><td>".nl2br($visMsg,false)."</td></tr>
</table>
</fieldset>
<p>{$xx['con_has_been_sent']}.</p>
<br>
<p>{$xx['con_confirm_eml_sent']} $visMail.</p>
";
}


//control logic

//init
$pass2 = isset($_POST["sendMsg"]) ? true : false;
$inPot = !empty($_POST['url']) ? true : false; //honey pot
if ($usr['email']) {
	$name = $usr['name'];
	$mail = $usr['email'];
} else {
	$name = $mail= '';
}
$visName = !empty($_POST['visName']) ? trim($_POST['visName']) : $name;
$visMail = !empty($_POST['visMail']) ? trim($_POST['visMail']) : $mail;
$visSubj = !empty($_POST['visSubj']) ? trim(strip_tags($_POST['visSubj'])) : '';
$visMsg = !empty($_POST['visMsg']) ? trim(strip_tags($_POST['visMsg'])) : '';
$msg ='';

if ($pass2) {
	$msg = validateForm();
	if (!$msg) { //form fields valid
		$errors = sendMessage();
		if ($errors) { $msg = $xx['con_mail_error']; }
	}
}
if ($msg) { //validation error
	echo "<p class='error'>{$msg}</p>\n";
}
echo "<div class='centerBox sBoxAd'>\n";
if (!$pass2 or $msg) {
	contactForm(); //show contact form
} else {
	messageSent(); //confirm message sent
}
echo "</div>\n";
?>
