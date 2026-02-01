<?php
/*
=== MESSAGING FUNCTIONS ===

This file is part of the LuxCal Web Calendar.
Copyright 2009-2022 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

/*============= configuration =============*/

$styles = [ //email body styles
"background:#FFFFDD; color:#000099; font:12px arial, sans-serif;", //email
"background:#DDFFFF; color:#000099; font:12px arial, sans-serif;", //cronmail
"background:#EEFFEE; color:#000099; font:12px arial, sans-serif;" //contact message
];

$tlgBotApi = "https://api.telegram.org/bot"; //telegram bot API URL

$nl = "\r\n"; //new line character(s) in mail header (\n or\r\n)

/*========== end of configuration ==========*/

//make message recipient list
function notify(&$evt,$rawRecList,$header) {
	global $set, $rxPhone;

	$rawRecList = preg_replace('~;\s*;+~',';',trim($rawRecList,';')); //remove empty slots
	$recArray = array();
	$rawRecArray = explode(';',$rawRecList);
	foreach ($rawRecArray as $recipient) { //create full recipient list
		$recipient = trim($recipient);
		if (!$recipient) { continue; } //empty entry
		if (preg_match('~^\[(.+)\]$~',$recipient,$matches)) { //file list name
			$listName = $matches[1].(strpos($matches[1],'.') ? '' : '.txt');
			if (file_exists("./reciplists/{$listName}")) { //recipients list
				$fileRecArray = file("./reciplists/{$listName}", FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES); // recipients from file
				foreach ($fileRecArray as $line) { //add recipients from file
					$line = trim(explode("#",$line)[0]); //remove comments
					if ($line) { //recipient
						$recArray[] = $line;
					}
				}
			}
		} else {
			$recArray[] = $recipient;
		}
	}
	array_walk($recArray,function(&$v,$k) use($rxPhone) { if (preg_match($rxPhone,rtrim($v,'$'))) $v = str_replace([' ','-','/','(',')'],'',$v); }); //strip non-digits from phone numbers

	//now $recArray contains unique user names, email addresses, chat IDs and phone numbers

	$recArrayE = $recArrayT = $recArrayS = array();
	foreach ($recArray as $recipient) {
		$stH = stPrep("SELECT `ID`, `email`, `phone`, `msingID`, `notSrvs` FROM `users` WHERE (LOWER(`email`) = ? OR name = ?  OR msingID = ? OR `phone` LIKE ?) AND `status` >= 0 limit 1");
		stExec($stH,[strtolower($recipient), $recipient, $recipient, '%'.ltrim($recipient,'+0'),]); //email case-insensitive
		if ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
			$count = 0;
			if (strpos($row['notSrvs'],'E') !== false and $set['emlService']) { $recArrayE[] = $row['email']; $count++; }
			if (strpos($row['notSrvs'],'T') !== false and $set['tlgService']) { $recArrayT[] = $row['msingID']; $count++; }
			if (strpos($row['notSrvs'],'S') !== false and $set['smsService']) { $recArrayS[] = $row['phone']; $count++; }
			if (!$count) { $recArrayE[] = $row['email']; }
		} elseif (strpos($recipient,'@',1)) { //email address
			$recArrayE[] = $recipient;
		} elseif (strpos('0+',$recipient[0]) !== false) { //phone number
			if ($set['smsService']) {
				$recArrayS[] = $recipient;
			} else {
				logMessage('luxcal',2,"Send notification. User: {$recipient} - SMS service not enabled.");
			}
		} elseif (ctype_digit($recipient)) { //Telegram chat ID
			if ($set['tlgService']) {
				$recArrayT[] = $recipient;
			} else {
				logMessage('luxcal',2,"Send notification. User: {$recipient} - Telegram service not enabled.");
			}
		} else {
			logMessage('luxcal',2,"Send notification. User: {$recipient} - No matching or valid email address, user name, Telegram chat ID or phone number.");
		}
	}
	//remove duplicates
	$recArrayE = array_unique($recArrayE); //email addresses
	$recArrayT = array_unique($recArrayT); //Telegram chat IDs
	$recArrayS = array_unique($recArrayS); //SMS phone numbers

	$errorsE = $errorsT = $errorsS = 0; //init
	if ($recArrayE) {
		$errorsE = notifyEml($evt,$recArrayE,$header);
//		echo "<br>E to: ".implode(', ',$recArrayE); //TEST
	}
	if ($recArrayT) {
		$errorsT = notifyTlg($evt,$recArrayT,$header);
//		echo "<br>T to: ".implode(', ',$recArrayT); //TEST
	}
	if ($recArrayS) {
		$errorsS = notifySms($evt,$recArrayS,$header);
//		echo "<br>S to: ".implode(', ',$recArrayS); //TEST
	}
	//log notifications messages
	if ($set['msgLogging']) {
		$logData = "{$evt['sda']} {$evt['tit']}".($evt['ven'] ? ", venue: {$evt['ven']}" : '').", category: {$evt['cnm']}, owner: {$evt['una']}";
		$sentTo = $recArrayE ? ' | E: '.implode(', ',$recArrayE).($errorsE ? ' ~E~' : '') : '';
		$sentTo .= $recArrayT ? ' | T: '.implode(', ',$recArrayT).($errorsT ? ' ~E~' : '') : '';
		$sentTo .= $recArrayS ? ' | S: '.implode(', ',$recArrayS).($errorsS ? ' ~E~' : '') : '';
		logNotMsg(0,$logData.$sentTo); //log message
	}
}

//notify via email
function notifyEml(&$evt,$recArrayE,$header) {
	global $set, $xx;
	
	//get category data
	$stH = stPrep("SELECT `name`,`approve`,`color`,`bgColor`,`checkBx`,`checkLb`,`checkMk` FROM `categories` WHERE `ID` = ?");
	stExec($stH,[$evt['cid']]);
	$cat = $stH->fetch(PDO::FETCH_ASSOC);
	$stH = null;
	
	//compose email message
	$subject = "{$header}: ".strip_tags($evt['tit']);
	$dateTime = makeFullDT(true,$evt['sda'],$evt['eda'],$evt['sti'],$evt['eti'],$evt['ald']).($evt['r_t'] ? " ({$evt['repTxt']})" : ''); //add full date/time and repeat text
	$datiLbl = ($evt['sti'] or $evt['eti']) ? $xx['evt_date_time'] : $xx['evt_date'];
	if ($evt['typ'] == 0) { //event
		$status = '';
		if (!$evt['eda'] and !$evt['r_t']) { //no multi-day and not repeating
			if ($cat['checkBx']) { $status .= $cat['checkLb'].': '.(cMark($evt,$evt['sda']) ? $cat['checkMk'] : '- -'); }
		}
		$catColor = ($cat['color'] ? "color:{$cat['color']};" : "").($cat['bgColor'] ? "background-color:{$cat['bgColor']};" : "");
		$eStyle = $catColor ? " style='{$catColor}'" : "";
		$eBoxStyle = ' style="padding-left:5px;'.(($cat['approve'] and !$evt['apd']) ? ' border-left:2px solid #ff0000;' : '').'"';
		$fields = '12378'.($set['xField1Rights'] == 1 ? '4' : '').($set['xField2Rights'] == 1 ? '5' : ''); //add xFields
		$evtText = makeE($evt,$set['evtTemplGen'],'td','',$fields);
		$msgBody = "
<h5>= {$header} =</h5>
<br>
<table{$eBoxStyle}>
<tr><td>{$xx['evt_title']}:</td><td><b><span{$eStyle}>{$evt['tit']}</span></b></td></tr>
".($status ? "<tr><td>{$xx['evt_status']}:</td><td>{$status}</td></tr>" : '')."
<tr><td>{$datiLbl}:</td><td>{$dateTime}</td></tr>
{$evtText}
</table>\n";
	} else { //day mark
		$msgBody = "
<h5>= {$header} =</h5>
<br>
<table style='padding-left:5px;'>
<tr><td>{$xx['mrk_text_and_color']}:</td><td><b><span style='padding:0 24px; color:{$evt['tx2']}; background-color:{$evt['tx3']};'>{$evt['tit']}</span></b></td></tr>
<tr><td>{$xx['mrk_dates']}:</td><td>{$dateTime}</td></tr>
<tr><td>{$xx['vws_added']}:</td><td>".IDTtoDDT($evt['adt'])." ({$evt['una']})</td></tr>\n".
(($evt['mdt'] and $evt['edr']) ? "<tr><td>{$xx['vws_edited']}:</td><td>".IDTtoDDT($evt['mdt'])." ({$evt['edr']})</td></tr>\n" : '').
"</table>\n";
	}
	//send email message
	$sender = $set['notSenderEml'] ? $evt['uid'] : 0;
	$errors = sendEml($subject,$msgBody,$recArrayE,0,$sender,$evt['sda'],$evt['eid']);
	return $errors;
}

//notify via Telegram
function notifyTlg(&$evt,$recArrayT,$header) {
	global $set, $xx;

	$dateTime = makeFullDT(false,$evt['sda'],$evt['eda'],$evt['sti'],$evt['eti'],$evt['ald']).($evt['r_t'] ? " ({$evt['repTxt']})" : ''); //get full date/time
	$datiLbl = ($evt['sti'] or $evt['eti']) ? $xx['evt_date_time'] : $xx['evt_date'];
	$tlgMsg = "From: <b>{$set['calendarTitle']}</b>"; //Telegram message
	$tlgMsg .= "\n= {$header} =";
	$tlgMsg .= "\n{$xx['evt_title']}: <b>{$evt['tit']}</b>";
	$tlgMsg .= "\n{$datiLbl}: <b>{$dateTime}</b>";
	if ($evt['typ'] == 0) { //event
		if ($evt['ven']) { $tlgMsg .= "\n{$xx['evt_venue']}: <b>{$evt['ven']}</b>"; }
		if ($evt['cnm']) { $tlgMsg .= "\n{$xx['evt_category']}: <b>{$evt['cnm']}</b>"; }
		if ($evt['tx1']) { $tlgMsg .= "\n{$evt['tx1']}"; }
		if ($evt['tx2']) { $tlgMsg .= "\n{$evt['tx2']}"; }
		if ($evt['tx3']) { $tlgMsg .= "\n{$evt['tx3']}"; }
	}
	$errors = sendTlg($tlgMsg,$recArrayT,$evt['att']); //send Telegram message
	return $errors;
}

//notify via SMS
function notifySms(&$evt,$recArrayS,$header) {
	global $set;
	
	$dateTime = makeFullDT(true,$evt['sda'],$evt['eda'],$evt['sti'],$evt['eti'],$evt['ald']); //get full date/time
	$smsMsg = "= {$header} =\n".$dateTime.': '.strip_tags($evt['tit']); //SMS message
	if ($evt['ven']) { $smsMsg .= "\n".str_replace('!','',strip_tags($evt['ven'])); }
	//send SMS message
	$sender = $set['notSenderSms'] ? $evt['uid'] : 0;
	$errors = sendSms($smsMsg,$recArrayS,$sender,$evt['eid']);
	return $errors;
}

//========================== SENDING ===============================

//send emails
function sendEml($subject,$msgBody,$emlArray,$style,$senderId,$date,$evtID=0) {
	global $styles, $set, $nl, $xx;

	//compile subject and message
	$calUrl = $date ? $set['calendarUrl'].(strpos($set['calendarUrl'],'?',6) ? '&amp;' : '?')."nD=".IDtoDD($date) : $set['calendarUrl'];
	$calLogo = $set['logoPath'] ? "<img class='logo' src='".calRootUrl()."{$set['logoPath']}' alt='calendar logo'>" : '';
	$msgBody = preg_replace("~(<br>|</tr>)([^\r\n])~","$1\r\n$2",$msgBody); //keep lines short (RFC 2045)
	$footnote = $set['emlFootnote'] ? "<br><p>".nl2br($set['emlFootnote'])."</p>" : '';
	$message = "
<html>
<head>
<meta charset=\"UTF-8\">
<title>{$set['calendarTitle']} mailer</title>
<style type='text/css'>
* {padding:0; margin:0;}
body {{$styles[$style]} padding-left:20px;}
h4 {
	font-size:1.2em;
	display:inline;
}
h5 {
	font-size:1.0em;
}
button {
	padding:0px 2px;
	font-size:1.0em;
	color:#064070;
	background:#E0E0E0;
	border-radius:2px;
	border:1px solid #666;
	cursor:pointer;
}
table {
	border-collapse:collapse;
}
td {
	padding:2px 10px;
	vertical-align:top;
}
fieldset {
	display:inline;
	margin:0 0 20px 20px;
	padding:20px;
	border:1px solid #888888;
	background:#FFFFFF;
	border-radius:5px;
}
div.head {
	margin:20px 0 20px 20px;
}
img.logo {
	margin-right:20px;
	max-width:70px;
	max-height:70px;
	vertical-align:middle;
}
.bold {
	font-weight:bold;
}
</style>
</head>
<body>
<div class='head'>
{$calLogo}
<h4>{$set['calendarTitle']}</h4>
</div>
<fieldset>{$msgBody}</fieldset>
<p><a href='{$calUrl}'>{$xx['open_calendar']}</a></p>
{$footnote}
<br>&nbsp;
</body>
</html>
";
	$replyTo = ''; //init
	$from = translit($set['calendarTitle'],true)." <{$set['calendarEmail']}>";
	if ($senderId) {//sender is user
		$stH = stPrep("SELECT `name`, `email` FROM `users` WHERE `ID` = ? limit 1");
		stExec($stH,[$senderId]);
		list($name,$email) = $stH->fetch(PDO::FETCH_NUM);
		$replyTo = "Reply-To: {$name} <{$email}>{$nl}";
	}
	$subjectX = "{$set['calendarTitle']} - {$subject}";
	$subject = '=?utf-8?B?'.base64_encode(htmlspecialchars_decode($subjectX,ENT_QUOTES)).'?='; //follow RFC 1342 for utf-8 encoding
	$curSlice = 0;
	$lenSlice = $set['maxEmlCc'] ?: 10;
	$headers = "MIME-Version: 1.0{$nl}Content-type: text/html; charset=utf-8{$nl}Message-id: {$evtID}{$nl}{$replyTo}Date: ".date(DATE_RFC2822);
	$errors = 0;
	while ($curSlice < count($emlArray)) {
		$ok = 1;
		$recipSlice = implode(', ',array_slice($emlArray,$curSlice,$lenSlice)); //take a slice of length maxEmlCc
		$curSlice += $lenSlice;
		if ($set['mailServer'] <= 1) { //mail via PHP
			$headers .= "{$nl}From: {$from}{$nl}Return-path: {$from}{$nl}Bcc: {$recipSlice}"; //additional headers
			if (!mail('',$subject,$message,$headers)) { //send PHP mail
				$ok = 0;
			}
			$mailType = 'PHP';
		} elseif ($set['mailServer'] == 2) { //mail via SMTP server
			if (!smtpMail($from,$recipSlice,$subject,$message,$headers)) { // send SMTP mail
				$ok = 0;
			}
			$mailType = 'SMTP';
		}
		$level = $ok ? 3 : 1;
		$what = $ok ? 'sent' :'failed' ;
		if (!$ok) { $errors++; }
		logMessage('luxcal',$level,"{$mailType} email {$what} . . .\n- To: {$recipSlice}\n- Headers: ".eol2txt($headers)."\n- Subject (before RFC 1342 encoding): {$subjectX} \n- Message: ".strip_tags(eol2txt(substr($msgBody,0,560))));
	}
	return $errors;
}

//send SMSes
function sendSms($message,$phoneArray,$senderId,$evtID) {
	global $set, $nl;

	//compile subject and message
	if ($set['smsAddLink']) {
		$p2 = strrpos($message,': ') + 3;
		$link = "\n{$set['calendarUrl']}".(strpos($set['calendarUrl'],'?',6) ? '&' : '?')."xP=32&eid={$evtID}&k=".ord($message[$p2]);
		$message = mbtrunc($message,$set['maxLenSms'] - strlen($link)).$link; //UTF: max. message length set by admin - length of link
	} else {
		$message = mbtrunc($message,$set['maxLenSms']); //UTF: max. message length set by admin
	}
	$from = $set['calendarEmail']; //sender ID SMS email
	$subjectX = $subject = ''; //default (subjectX for logging)
	if ($set['smsSubject']) {
		$fromPhone = $set['calendarPhone']; //default calendar phone nr
		if ($senderId) { //sender is user
			$stH = stPrep("SELECT `phone` FROM `users` WHERE `ID` = ? limit 1");
			stExec($stH,[$senderId]);
			$row = $stH->fetch(PDO::FETCH_NUM);
			if ($row != false and !empty($row[0])) {
				$fromPhone = $row[0]; //event owner phone nr
			}
		}
		if ($set['smsCountry'] and !preg_match('%^(\+|00)%',$fromPhone[0])) { $fromPhone = '+'.$set['smsCountry'].ltrim($fromPhone,'0'); } //add country code
		if (!$set['cCodePrefix']) { $fromPhone = preg_replace('%^(\+|00)%','',$fromPhone); } //remove prefix (+ or 00)
		$subjectX = str_replace('#',$fromPhone,$set['smsSubject']); //replace # by sender ID (phone) 
		$subject = '=?utf-8?B?'.base64_encode($subjectX).'?='; //follow RFC 1342 for utf-8 encoding
	}
	$curSlice = 0;
	$lenSlice = $set['maxEmlCc'] ?: 10;
	$errors = 0;
	while ($curSlice < count($phoneArray)) {
		$ok = 1;
		$recipSlice = array_slice($phoneArray,$curSlice,$lenSlice); //take a slice of length maxEmlCc
		$curSlice += $lenSlice;
		array_walk($recipSlice,function(&$recipient,$k) use($set) { //convert mobile numbers to SMS carrier mail addresses
				if ($set['smsCountry'] and !preg_match('~^(\+|00)~',$recipient)) $recipient = '+'.$set['smsCountry'].ltrim($recipient,'0'); //add country code
				if (!$set['cCodePrefix']) $recipient = preg_replace('~^(\+|00)~','',$recipient); //remove prefix + or 00
				$recipient = str_replace('#',$recipient,$set['smsCarrier']);
			});
		$recipList = implode(', ',$recipSlice);
//echo $recipList."<br>Subject: ".$subjectX."<br>Message: ".$message; //TEST
		$ok = 1;
		if ($set['mailServer'] <= 1) { //mail via PHP
			$headers = "MIME-Version: 1.0{$nl}Content-type: text/plain; charset=utf-8{$nl}From: {$from}{$nl}Date: ".date(DATE_RFC2822);
			if (!mail($recipList,$subject,$message,$headers)) { //SMS mail via PHP
				$ok = 0;
			}
			$mailType = 'PHP';
		} elseif ($set['mailServer'] == 2) { //SMS mail via SMTP server
			$headers = "MIME-Version: 1.0{$nl}Content-type: text/plain; charset=utf-8{$nl}Date: ".date(DATE_RFC2822);
			if (!smtpMail($from,$recipList,$subject,$message,$headers)) { // send SMTP mail
				$ok = 0;
			}
			$mailType = 'SMTP';
		}
		$level = $ok ? 3 : 1;
		$what = $ok ? 'sent' :'failed' ;
		if (!$ok) { $errors++; }
		logMessage('luxcal',$level,"{$mailType} SMS mail {$what} . . .\n- To: {$recipList}\n- Headers: ".eol2txt($headers)."\n- Subject (before RFC 1342 encoding): {$subjectX}\n- Message: ".strip_tags(eol2txt($message)));
	}
	return $errors;
}

//send Telegram messages
function sendTlg($message, $tlgIdArray, $attachments) {
	global $set, $xx, $rxELink, $tlgBotApi;

	//pre-process message  
	$message = str_replace(['<br>','&amp;','&apos;','&quot;'],["\n","&#038;","&#039;",'&#034;'],$message); //convert <br> to nl (Telegram doesn't like HTML5 characters (&amp;, &apos;, &quot;')
	$message = preg_replace($rxELink," $1 ",$message); //mailto links => bare mail addresses

	//convert images to URLs
	$calUrl = calBaseUrl(); //calendar base URL
	$regex = '~<img.*src=[\'\"](.+/[\w\-]+/([^\s/]+)\.(?:gif|jpg|png)).*?>~';
	$message = preg_replace_callback($regex,
        function ($matches) {
					$imgUrl = substr($matches[1],0,4) == 'http' ? $matches[1] : $calUrl.ltrim($matches[1],'./');
					return "<a href='{$imgUrl}'>{$matches[2]}</a>"; },
        $message
  );
	if ($attachments) { //add attachments to the end as URL
		$message .= "\n_______________";
		$atts = array_filter(explode(';',$attachments));
		foreach ($atts as $att) {
			$message .= "\n<a href='{$calUrl}dloader.php?ftd=./attachments/".rawurlencode($att)."&amp;nwN=".substr($att,14)."'>".substr($att,14)."</a>";
		}
	}
	$message .= "\n\n<a href='{$calUrl}'>{$xx['open_calendar']}</a>"; //add calendar link
	$bareMsg = trim(strip_tags($message,'<a><b><i><u><s>'));

	//prepare parameters and send message
	$apiUrl = "{$tlgBotApi}{$set['tlgToken']}/sendMessage"; //telegram API URL
	$qPars = ['chat_id' => '', 'text' => $bareMsg, 'parse_mode' => 'html'];
	$recipOK = $recipNOK = array();
	$cURL = !filter_var(ini_get( 'allow_url_fopen' ), FILTER_VALIDATE_BOOLEAN);
	if ($cURL) { //init cURL + options
		$ch = curl_init(); //cURL handle
		curl_setopt_array($ch, [
			CURLOPT_URL => $apiUrl,
			CURLOPT_HEADER => 0,
			CURLOPT_RETURNTRANSFER => 1,
			CURLOPT_POST => 1,
//			CURLOPT_SSL_VERIFYPEER => 0
		]);
	}
	foreach ($tlgIdArray as $msgID) {
		$qPars['chat_id'] = $msgID;
		if ($cURL) { //use cURL
			curl_setopt($ch, CURLOPT_POSTFIELDS, $qPars);
			$ok = curl_exec($ch); //send
		} else { //use file_get_contents
			$response = @file_get_contents($apiUrl.'?'.http_build_query($qPars)); //send
			if (is_object($response)) { $result = json_decode($response); }
			$ok = (!empty($result) and $result->ok) ? true : false;
		}
		if ($ok) { //telegram sent
			$recipOK[] = $msgID;
		} else {
			$recipNOK[] = $msgID;
		}
	}
	if ($cURL) { curl_close($ch); }
	if ($recipNOK) { //failed
		logMessage('luxcal',1,"Telegram message failed . . .\n- To: ".implode(', ',$recipNOK)."\n- Message: ".eol2txt($bareMsg)); //TEST
		$errors = 1;
	} else { //all sent
		$errors = 0;
	}
	return $errors;
}

//send SMTP mail
function smtpMail($from,$recipList,$subject,$message,$headers) {
	global $set, $nl;
	
	$smtpServer = ($set['smtpSsl'] ? 'ssl://' : '').strtolower($set['smtpServer']);
	preg_match('~^(?:https?://)?([^?/]+)(?:/|\?|$)~',$set['calendarUrl'],$matches);
	$smtpClient = $matches[1]; //bare client URL
	$toArray = explode(',', $recipList);
	$hits = [];
	$errMsg = $toString = '';
	foreach($toArray as $k => $v) {
		if (preg_match("~^([^<>@]*?)<?([^\s<>]*@[^\s<>]*)>?$~i",trim($v),$hits)) {
			$toArray[$k] = '<'.$hits[2].'>';
			$toString .= $hits[1].'<'.$hits[2].'>, ';
		} else {
			$errMsg .= "Error in 'to' field. "; break;
		}
	}
	$toString = rtrim($toString,' ,');
	$hits = [];
	if (preg_match("~^([^<>@]*?)<?([^\s<>]*@[^\s<>]*)>?$~i",trim($from),$hits)) {
		$fromS = '<'.$hits[2].'>';
	} else {
		$errMsg .= "Error in 'from' field.";
	}
	if ($errMsg) {
		logMessage('luxcal',1,"SMTP mail to {$recipList} failed.\n{$errMsg}");
		return false;
	}

	$cmdArray = []; //keyword, data, expected return code
	$cmdArray[] = array ('Connect','','220');
	$cmdArray[] = array ('EHLO','EHLO '.$smtpClient,'250');
	if ($set['smtpAuth']) {
		$cmdArray[] = array ('AUTH LOGIN','AUTH LOGIN','334');
		$cmdArray[] = array ('User',base64_encode($set['smtpUser']),'334');
		$cmdArray[] = array ('Password',base64_encode($set['smtpPass']),'235');
	}
	$cmdArray[] = array ('MAIL FROM','MAIL FROM: '.$fromS,'250');
	foreach ($toArray as $email) { $cmdArray[] = array ('RCPT TO','RCPT TO: '.$email,'250'); }
	$cmdArray[] = array ('DATA','DATA','354');
	$cmdArray[] = array ('DATA string',"$headers{$nl}From: $from{$nl}To: $toString{$nl}Subject: $subject{$nl}Reply-To: $fromS{$nl}Return-path: $fromS{$nl}$message{$nl}.",'250');
	$cmdArray[] = array ('QUIT','QUIT','221');

	if (!($socket = fsockopen($smtpServer,$set['smtpPort'],$errNo,$errStr,20))) { //connect to socket
		logMessage('luxcal',1,"Could not connect to SMTP server {$smtpServer}, port {$set['smtpPort']} ({$errNo} - {$errStr})");
		return false;
	}
	foreach ($cmdArray as $cmdData) {
		if ($cmdData[0] != 'Connect') {
			fwrite($socket,$cmdData[1]."\r\n");
		}
		do { //ignore reply codes followed by a hyphen
			if (!($serverReply = fgets($socket, 256))) {
				logMessage('luxcal',1,"SMTP mail to {$recipList} failed.\nNo SMTP server reply code.");
				return false;
			}
		} while (substr($serverReply,3,1) != ' ');
		if (!(substr($serverReply,0,3) == $cmdData[2])) {
			logMessage('luxcal',1,"SMTP mail to {$recipList} failed.\n{$cmdData[0]}: SMTP server reply: {$serverReply}");
			return false;
		}
	}
	fclose($socket);
	return true;
}
?>