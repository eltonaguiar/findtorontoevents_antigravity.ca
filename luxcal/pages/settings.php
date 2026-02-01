<?php
/*
= Change Calendar Settings page =

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
require './common/toolboxx.php'; //admin tools
$msg = "";

if ($usr['privs'] != 9) { //no admin
	echo "<p class='error'>{$ax['no_way']}</p>\n"; exit;
}

function buttonsValid($buttons,$range) {
	if (empty($buttons)) { return true; }
	foreach (explode(',',$buttons) as $buttonNr) {
		if (substr_count(','.$buttons.',',','.$buttonNr.',') > 1 or strpos($range.',',$buttonNr.',') === false) { return false; }
	}
	return true;
}

function fieldsValid($fields,$range) {
	if (!empty($fields)) {
		foreach (str_split($fields) as $fieldNr) {
			if ($fieldNr < $range[0] or $fieldNr > $range[2]) { return false; }
		}
	}
	return true;
}

//set lcconfig params
$calMenu = $_POST['calMenu'] ?? 0; //calendar menu in Opt panel
$cronHost = $_POST['cronHost'] ?? $crHost; //cron service host
$cronIpAd = $_POST['cronIpAd'] ?? $crIpAd; //cron service Ip address

if (isset($_POST["save"])) { //get posted settings
	foreach ($defSet as $key => $void) {
		if (!isset($_POST['pSet'][$key])) {
			$pSet[$key] = 0; //set unchecked check box to unchecked
		} else {
			$pSet[$key] = is_int($defSet[$key][0]) ? intval($_POST['pSet'][$key]) : trim($_POST['pSet'][$key]); //make int-strings integers
		}
	}
} else { //get current settings
	foreach ($defSet as $key => $value) {
		$pSet[$key] = $set[$key] ?? $value[0];
	}
}
if (isset($_POST["mail"]) and $pSet['calendarEmail']) { //send test mail
	$msgBody = "<p>{$ax['set_mail_sent_from']}.</p>";
	$errors = sendEml($ax['set_test_mail'],$msgBody,[$pSet['calendarEmail']],1,0,0);
	$msg .= !$errors ? $ax['set_mail_sent_to'].' '.$pSet['calendarEmail'] : $ax['set_mail_failed'].": ".$pSet['calendarEmail'];	
}

/*========== preprocessing ==========*/
//comma separate viewws (old versions didn't use comma separators)
$pSet['viewsPublic'] = preg_replace('%(\d)(?!0|1|,|$)%',"$1,",trim($pSet['viewsPublic'],' ,'));
$pSet['viewsLogged'] = preg_replace('%(\d)(?!0|1|,|$)%',"$1,",trim($pSet['viewsLogged'],' ,'));
$pSet['viewButsPubL'] = preg_replace('%(\d)(?!0|1|,|$)%',"$1,",trim($pSet['viewButsPubL'],' ,'));
$pSet['viewButsLogL'] = preg_replace('%(\d)(?!0|1|,|$)%',"$1,",trim($pSet['viewButsLogL'],' ,'));
//strip prefix . and/or / of relative file paths
$pSet['logoPath'] = ltrim($pSet['logoPath'],'./');
$pSet['logoXlPath'] = ltrim($pSet['logoXlPath'],'./');
//various other
$pSet['chgRecipList'] = trim(preg_replace("%[\s\\\\<>]%",'',$pSet['chgRecipList']),' ,;.');
$pSet['smsCountry'] = ltrim($pSet['smsCountry'],'+0');
/*===================================*/

//validate inputs
$eClass = 'warning';
$errors = array_fill(0,65,''); $e = 0; //init

if (isset($_POST["save"])) { //validate settings
	if (!$pSet['calendarTitle']) { $errors[$e] = ' class="inputError"'; } $e++;
	if (!$pSet['calendarUrl'] or !preg_match($rxCalURL,$pSet['calendarUrl'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (substr($pSet['calendarUrl'],0,4) != 'http') { $pSet['calendarUrl'] = 'https://'.$pSet['calendarUrl']; }
	if (!$pSet['calendarEmail'] or !filter_var($pSet['calendarEmail'],FILTER_VALIDATE_EMAIL)) { $errors[$e] = " class='inputError'"; } $e++; //xxx
	if (!$pSet['timeZone'] or !@date_default_timezone_set($pSet['timeZone'])) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['chgRecipList'] and !preg_match('%^([^@;]+@[^@;]+?\.\w+;|\d{8,14};|\w{2,};|\[[^\]]{2,}\];)+$%',$pSet['chgRecipList'].';')) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['maxXsWidth'] < 400 or $pSet['maxXsWidth'] > 2000) { $errors[$e] = " class='inputError'"; } $e++;
	if (!preg_match('%^(([1-9]|10|11),\s*)*([1-9]|10|11)$%',$pSet['viewsPublic'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!preg_match('%^(([1-9]|10|11),\s*)*([1-9]|10|11)$%',$pSet['viewsLogged'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!buttonsValid($pSet['viewButsPubL'],$pSet['viewsPublic'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!buttonsValid($pSet['viewButsLogL'],$pSet['viewsLogged'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!buttonsValid($pSet['viewButsPubS'],$pSet['viewsPublic'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!buttonsValid($pSet['viewButsLogS'],$pSet['viewsLogged'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (strpos($pSet['viewsPublic'].',',strval($pSet['defViewPubL']).',') === false) { $errors[$e] = " class='inputError'"; } $e++;
	if (strpos($pSet['viewsLogged'].',',strval($pSet['defViewLogL']).',') === false) { $errors[$e] = " class='inputError'"; } $e++;
	if (strpos($pSet['viewsPublic'].',',strval($pSet['defViewPubS']).',') === false) { $errors[$e] = " class='inputError'"; } $e++;
	if (strpos($pSet['viewsLogged'].',',strval($pSet['defViewLogS']).',') === false) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['cookieExp'] < 1 or $pSet['cookieExp'] > 365) { $errors[$e] = " class='inputError'"; } $e++;
	if (!fieldsValid($pSet['evtTemplGen'],'1-8')) { $errors[$e] = " class='inputError'"; } $e++;
	if (!fieldsValid($pSet['evtTemplUpc'],'1-8')) { $errors[$e] = " class='inputError'"; } $e++;
	if (!fieldsValid($pSet['evtTemplPop'],'1-8')) { $errors[$e] = " class='inputError'"; } $e++;
	if (!fieldsValid($pSet['evtTemplGen2'],'1-8')) { $errors[$e] = " class='inputError'"; } $e++;
	if (!fieldsValid($pSet['evtTemplUpc2'],'1-8')) { $errors[$e] = " class='inputError'"; } $e++;
	if (!fieldsValid($pSet['evtTemplPop2'],'1-8')) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['yearStart'] < 0 or $pSet['yearStart'] > 12) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['YvRowsToShow'] < 1 or $pSet['YvRowsToShow'] > 10) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['YvColsToShow'] < 1 or $pSet['YvColsToShow'] > 6) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['MvWeeksToShow'] < 0 or $pSet['MvWeeksToShow'] > 20) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['XvWeeksToShow'] < 4 or $pSet['XvWeeksToShow'] > 20) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['GvWeeksToShow'] < 4 or $pSet['GvWeeksToShow'] > 20) { $errors[$e] = " class='inputError'"; } $e++;
	if (!preg_match("/^[0-6]{1,7}$/", $pSet['workWeekDays'])) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['weekStart'] < 0 or $pSet['weekStart'] > 6) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['lookbackDays'] < 1 or $pSet['lookbackDays'] > 365) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['lookaheadDays'] < 1 or $pSet['lookaheadDays'] > 365) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['searchBackDays'] < 1) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['searchAheadDays'] < 1) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['dwStartHour'] < 0 or $pSet['dwStartHour'] > 18 or $pSet['dwStartHour'] > ($pSet['dwEndHour'] - 4)) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['dwEndHour'] > 24 or $pSet['dwEndHour'] < 6 or $pSet['dwStartHour'] > ($pSet['dwEndHour'] - 4)) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['dwTsHeight'] < 10 or $pSet['dwTsHeight'] > 60) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['mapViewer'] and substr($pSet['mapViewer'],0,4) != 'http') { $pSet['mapViewer'] = 'https://'.$pSet['mapViewer']; }
//the following regexs use lookahead assertion
	if (!preg_match('%^([ymd])([^\da-zA-Z])(?!\1)([ymd])\2(?!(\1|\3))[ymd]$%',$pSet['dateFormat'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!preg_match('%^([Md])[^\da-zA-Z]+(?!\1)[Md]$%',$pSet['MdFormat'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!preg_match('%^([Myd])[^\da-zA-Z]+(?!\1)([Myd])[^\da-zA-Z]+(?!(\1|\2))[Myd]$%',$pSet['MdyFormat'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!preg_match('%^([My])[^\da-zA-Z]+(?!\1)[My]$%',$pSet['MyFormat'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!preg_match('%^(WD|[Md])[^\da-zA-Z]+(?!\1)(WD|[Md])[^\da-zA-Z]+(?!(\1|\2))(WD|[Md])$%',$pSet['DMdFormat'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!preg_match('%^(WD|[Mdy])[^\da-zA-Z]+(?!\1)(WD|[Mdy])[^\da-zA-Z]+(?!(\1|\2))(WD|[Mdy])[^\da-zA-Z]+(?!(\1|\2\3))(WD|[Mdy])$%',$pSet['DMdyFormat'])) { $errors[$e] = " class='inputError'"; } $e++;
	if (!preg_match('%^([Hhm])[^\da-zA-Z](?!\1)[Hhm](\s?[aA])?$%',$pSet['timeFormat'])) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['maxUplSize'] < 1 or $pSet['maxUplSize'] > 200) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['tnlMaxW'] < 10 or $pSet['tnlMaxW'] > 800) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['tnlMaxH'] < 10 or $pSet['tnlMaxH'] > 800) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['tnlDelDays'] < 0 or $pSet['tnlDelDays'] > 99) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['maxEmlCc'] < 5 or $pSet['maxEmlCc'] > 99) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['msgLogWeeks'] < 1 or $pSet['msgLogWeeks'] > 99) { $errors[$e] = " class='inputError'"; } $e++;
	if (!$pSet['smtpServer'] and $pSet['mailServer'] == 2) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['smtpPort'] < 0 or $pSet['smtpPort'] > 10025) { $errors[$e] = " class='inputError'"; } $e++; //10025 max port nr for SMTP
	if (!$pSet['smtpUser'] and $pSet['smtpAuth'] and $pSet['mailServer'] == 2) { $errors[$e] = " class='inputError'"; } $e++;
	if (!$pSet['smtpPass'] and $pSet['smtpAuth'] and $pSet['mailServer'] == 2) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['tlgToken'] and !preg_match('%^\d{6,12}:[\w-]{30,40}$%',$pSet['tlgToken'])) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['smsService'] and strpos($pSet['smsSubject'],'#') !== false and !preg_match($rxPhone,$pSet['calendarPhone']) and !$pSet['notSenderSms']) { $errors[$e] = " class='inputError'"; } $e++; //xxx
	if ($pSet['smsService'] and !preg_match('%^[^#@]*#[^#@]*?@([^@\.]+?\.)+[\w]+$%',$pSet['smsCarrier'])) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['smsService'] and $pSet['smsCountry'] and !is_numeric($pSet['smsCountry'])) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['maxLenSms'] < 70 or $pSet['maxLenSms'] > 500) { $errors[$e] = " class='inputError'"; } $e++;
	if ($cronHost == 2 and !preg_match('%(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){4}%',$cronIpAd.'.')) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['eventExp'] < 0 or $pSet['eventExp'] > 999) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['maxNoLogin'] < 0 or $pSet['maxNoLogin'] > 365) { $errors[$e] = " class='inputError'"; } $e++;
	if (!empty($pSet['popFieldsSbar']) and !fieldsValid($pSet['popFieldsSbar'],'1-7')) { $errors[$e] = " class='inputError'"; } $e++;
	if ($pSet['sideBarDays'] < 1 or $pSet['sideBarDays'] > 365) { $errors[$e] = " class='inputError'"; } $e++;

	//no errors, save settings in database
	if (!in_array(" class='inputError'",$errors)) {
		if ($crHost != $cronHost or $crIpAd != $cronIpAd) {
			$crHost = $cronHost;
			$crIpAd = $cronIpAd;
			saveConfig(); //save config data
		}
		saveSettings($pSet);
		$msg = $ax['set_settings_saved'];
	} else { //errors found
		$msg .= $ax['set_missing_invalid'];
		$eClass = 'error';
	}
}

echo "<br><p class='{$eClass} noPrint'>".($msg ?: $ax['hover_for_details'])."</p>\n<br>\n";
//display form fields
echo "<form action='index.php' method='post'>
	{$formCal}
	<button type='submit' class='center' name='save' value='y'><b>{$ax['set_save_settings']}</b></button>
	<div class='sBoxSe'>\n";
$e = 0; //init errors index

//== General ==
echo "<fieldset class='setting'><legend>{$ax['set_general_settings']}</legend>
	<div><span class='sLabel' onmouseover='popM(this,`".str_replace(["'",'"'],['&apos;','&quot;'],$ax['versions_text'])."`);'>{$ax['versions_label']}:</span>
	LuxCal {$ax['calendar']}: ".LCV." (".($dbType == 'SQLite' ? $dbDir : '')."{$calID})</div>
	<div><span class='sLabel'></span> PHP: ".phpversion()."&ensp;<button type='button' onclick='window.open(`index.php?pP=1`);'>PHP Info</button></div>
	<div><span class='sLabel'></span> ".ucfirst($ax['database']).": {$dbType} V".$dbH->getAttribute(PDO::ATTR_SERVER_VERSION)."</div>
	
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['calTitle_text'])."`);'>{$ax['calTitle_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[calendarTitle]' size='45' value=\"{$pSet['calendarTitle']}\"></div>
	
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['calUrl_text'])."`);'>{$ax['calUrl_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[calendarUrl]' size='45' value=\"{$pSet['calendarUrl']}\"></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['calEmail_text'])."`);'>{$ax['calEmail_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[calendarEmail]' size='24' value=\"{$pSet['calendarEmail']}\">&ensp;<button type='submit' name='mail' value='y'>{$ax['set_test_mail']}</button></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['logoPath_text'])."`);'>{$ax['logoPath_label']}:</span>
	<input type='text' name='pSet[logoPath]' size='45' value=\"{$pSet['logoPath']}\"></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['logoXlPath_text'])."`);'>{$ax['logoXlPath_label']}:</span>
	<input type='text' name='pSet[logoXlPath]' size='45' value=\"{$pSet['logoXlPath']}\">&emsp;
	{$ax['height']}:&ensp;<input type='text' name='pSet[logoHeight]' maxlength='3' size='3' value='{$pSet['logoHeight']}'> px</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['backLinkUrl_text'])."`);'>{$ax['backLinkUrl_label']}:</span>
	<input type='text' name='pSet[backLinkUrl]' size='45' value=\"{$pSet['backLinkUrl']}\"></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['timeZone_text'])."`);'>{$ax['timeZone_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[timeZone]' size='24' value=\"{$pSet['timeZone']}\">&ensp;{$ax['see']}:&nbsp;<strong>[<a href='https://www.php.net/manual/en/timezones.php' target='_blank'>{$ax['time_zones']}</a>]</strong></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['notifChange_text'].'<br>'.$ax['reciplist'])."`);'>{$ax['notifChange_label']}:</span>
	<input type='text'{$errors[$e++]} placeholder='{$ax['chgRecipList']}' name='pSet[chgRecipList]'  maxlength='255' size='60' value='{$pSet['chgRecipList']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['maxXsWidth_text'])."`);'>{$ax['maxXsWidth_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[maxXsWidth]' maxlength='4' size='3' value='{$pSet['maxXsWidth']}'> pixels (400 - 2000)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['rssFeed_text'])."`);'>{$ax['rssFeed_label']}:</span>
	<input type='checkbox' name='pSet[rssFeed]' value='1'".($pSet['rssFeed'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['logging_text'])."`);'>{$ax['logging_label']}:</span>
	<label><input type='checkbox' name='pSet[logWarnings]' value='1'".($pSet['logWarnings'] ? " checked" : '').">{$ax['warnings']}</label>&ensp;
	<label><input type='checkbox' name='pSet[logNotices]' value='1'".($pSet['logNotices'] ? " checked" : '').">{$ax['notices']}</label>&ensp;
	<label><input type='checkbox' name='pSet[logVisitors]' value='1'".($pSet['logVisitors'] ? " checked" : '').">{$ax['visitors']}</label></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['maintMode_text'])."`);'>{$ax['maintMode_label']}:</span>
	<input type='checkbox' name='pSet[maintMode]' value='1'".($pSet['maintMode'] == 1 ? " checked" : '')."></div>
	</fieldset>\n";

//== Navigation Bar ==
echo "<fieldset class='setting'><legend>{$ax['set_navbar_settings']}</legend>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['contact_text'])."`);'>{$ax['contact_label']}:</span>
	<input type='checkbox' id='cont' name='pSet[contButton]' value='1'".($pSet['contButton'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['optionsPanel_text'])."`);'>{$ax['optionsPanel_label']}:</span>
	<label><input type='checkbox' name='pSet[calMenu]' value='1'".($pSet['calMenu'] == 1 ? " checked" : '').">{$ax['calMenu_label']}</label>&ensp;
	<label><input type='checkbox' name='pSet[viewMenu]' value='1'".($pSet['viewMenu'] == 1 ? " checked" : '').">{$ax['viewMenu_label']}</label>&ensp;
	<label><input type='checkbox' name='pSet[groupMenu]' value='1'".($pSet['groupMenu'] == 1 ? " checked" : '').">{$ax['groupMenu_label']}</label>&ensp;
	<label><input type='checkbox' name='pSet[userMenu]' value='1'".($pSet['userMenu'] == 1 ? " checked" : '').">{$ax['userMenu_label']}</label>&ensp;
	<label><input type='checkbox' name='pSet[catMenu]' value='1'".($pSet['catMenu'] == 1 ? " checked" : '').">{$ax['catMenu_label']}</label>&ensp;
	<label><input type='checkbox' name='pSet[langMenu]' value='1'".($pSet['langMenu'] == 1 ? " checked" : '').">{$ax['langMenu_label']}</label></div>
	
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['availViews_text'])."`);'>{$ax['availViews_label']}:</span>
	{$ax['public']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[viewsPublic]' maxlength='23' size='22' value='{$pSet['viewsPublic']}'>&ensp;{$ax['logged_in']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[viewsLogged]' maxlength='23' size='22' value='{$pSet['viewsLogged']}'></div>
	
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['viewButtons_text'])."`);'>{$ax['viewButtonsL_label']}:</span>
	{$ax['public']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[viewButsPubL]' maxlength='23' size='22' value='{$pSet['viewButsPubL']}'>&ensp;{$ax['logged_in']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[viewButsLogL]' maxlength='23' size='22' value='{$pSet['viewButsLogL']}'></div>
	
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['viewButtons_text'])."`);'>{$ax['viewButtonsS_label']}:</span>
	{$ax['public']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[viewButsPubS]' maxlength='23' size='22' value='{$pSet['viewButsPubS']}'>&ensp;{$ax['logged_in']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[viewButsLogS]' maxlength='23' size='22' value='{$pSet['viewButsLogS']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['defaultViewL_text'])."`);'>{$ax['defaultViewL_label']}:</span>
	{$ax['public']}:&nbsp;<select name='pSet[defViewPubL]'{$errors[$e++]}>";
foreach (explode(',',$pSet['viewsPublic']) as $v) {
		echo "<option value='{$v}'".($pSet['defViewPubL'] == "{$v}" ? ' selected' : '').">".$xx["hdr_view_{$v}"]."</option>\n";
}
echo "</select>&ensp;{$ax['logged_in']}:&nbsp;<select name='pSet[defViewLogL]'{$errors[$e++]}>";
foreach (explode(',',$pSet['viewsLogged']) as $v) {
		echo "<option value='{$v}'".($pSet['defViewLogL'] == "{$v}" ? ' selected' : '').">".$xx["hdr_view_{$v}"]."</option>\n";
}
echo "</select>
	</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['defaultViewS_text'])."`);'>{$ax['defaultViewS_label']}:</span>
	{$ax['public']}:&nbsp;<select name='pSet[defViewPubS]'{$errors[$e++]}>";
foreach (explode(',',$pSet['viewsPublic']) as $v) {
		echo "<option value='{$v}'".($pSet['defViewPubS'] == "{$v}" ? ' selected' : '').">".$xx["hdr_view_{$v}"]."</option>\n";
}
echo "</select>&ensp;{$ax['logged_in']}:&nbsp;<select name='pSet[defViewLogS]'{$errors[$e++]}>";
foreach (explode(',',$pSet['viewsLogged']) as $v) {
		echo "<option value='{$v}'".($pSet['defViewLogS'] == "{$v}" ? ' selected' : '').">".$xx["hdr_view_{$v}"]."</option>\n";
}
echo "</select>
	</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['language_text'])."`);'>{$ax['language_label']}:</span>
	<select name='pSet[language]'>\n";
$files = preg_grep("~^ui-[a-z]+\.php$~",scandir("lang/"));
foreach ($files as $file) {
	$lang = strtolower(substr($file,3,-4));
	echo "\t<option value='{$lang}'".(strtolower($pSet['language']) == $lang ? ' selected' : '').">".ucfirst($lang)."</option>\n";
}
echo "</select>
	</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['birthday_cal_text'])."`);'>{$ax['birthday_cal_label']}:</span>
	<input type='checkbox' id='cont' name='pSet[birthdayCal]' value='1'".($pSet['birthdayCal'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['sideLists_text'])."`);'>{$ax['sideLists_label']}:</span>
	<label><input type='checkbox' name='pSet[toapList]' value='1'".($pSet['toapList'] == 1 ? " checked" : '').">{$ax['toapList_label']}</label>&ensp;
	<label><input type='checkbox' name='pSet[todoList]' value='1'".($pSet['todoList'] == 1 ? " checked" : '').">{$ax['todoList_label']}</label>&ensp;
	<label><input type='checkbox' name='pSet[upcoList]' value='1'".($pSet['upcoList'] == 1 ? " checked" : '').">{$ax['upcoList_label']}</label></div>
</fieldset>\n";

//== User Accounts ==
echo "<fieldset class='setting'><legend>{$ax['set_user_settings']}</legend>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['selfReg_text'])."`);'>{$ax['selfReg_label']}:</span>
	<input type='checkbox' name='pSet[selfReg]' value='1'".($pSet['selfReg'] == 1 ? " checked" : '').">&ensp;<select name='pSet[selfRegGrp]'>\n";
	$stH = dbQuery("SELECT `ID`,`name`,`color` FROM `groups` WHERE `status` >= 0 ORDER BY `name`");
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		if ($row['ID'] != 2) {
			$color = $row['color'] ? " style='background-color:{$row['color']};'" : '';
			$selAttr = $row['ID'] == $pSet['selfRegGrp'] ? ' selected' : '';
			echo "<option value='{$row['ID']}'{$color}{$selAttr}>{$row['name']}</option>\n";
		}
	}
	echo "</select>&ensp;{$ax['user_group']}</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['selfRegQA_text'])."`);'>{$ax['selfRegQA_label']}:</span>
	<input type='text' name='pSet[selfRegQ]' maxlength='50' size='40' value='{$pSet['selfRegQ']}'>?&ensp;
	{$ax['answer']}:&nbsp;<input type='text' name='pSet[selfRegA]' maxlength='15' size='12' value='{$pSet['selfRegA']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['selfRegNot_text'])."`);'>{$ax['selfRegNot_label']}:</span>
	<input type='checkbox' name='pSet[selfRegNot]' value='1'".($pSet['selfRegNot'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['restLastSel_text'])."`);'>{$ax['restLastSel_label']}:</span>
	<input type='checkbox' name='pSet[restLastSel]' value='1'".($pSet['restLastSel'] == 1 ? " checked" : '').">&ensp;
	{$ax['exp_days']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[cookieExp]' maxlength='3' size='2' value='{$pSet['cookieExp']}'> (1 - 365)</div>
</fieldset>\n";

//== Events ==
echo "<fieldset class='setting'><legend>{$ax['set_event_settings']}</legend>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote("<b>{$ax['evtTemplPublic']}</b>:<br>{$ax['evtTemplate_text']}<br>{$ax['templFields_text']}")."`);'>{$ax['evtTemplate_label']} - {$ax['evtTemplPublic']}:</span>
	{$ax['evtTemplGen']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[evtTemplGen]' maxlength='8' size='8' value='{$pSet['evtTemplGen']}'>&ensp;
	{$ax['evtTemplUpc']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[evtTemplUpc]' maxlength='8' size='8' value='{$pSet['evtTemplUpc']}'>&ensp;
	{$ax['evtTemplPop']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[evtTemplPop]' maxlength='8' size='8' value='{$pSet['evtTemplPop']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote("<b>{$ax['evtTemplLogged']}</b>:<br>{$ax['evtTemplate_text']}<br>{$ax['templFields_text']}")."`);'>{$ax['evtTemplate_label']} - {$ax['evtTemplLogged']}:</span>
	{$ax['evtTemplGen']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[evtTemplGen2]' maxlength='8' size='8' value='{$pSet['evtTemplGen2']}'>&ensp;
	{$ax['evtTemplUpc']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[evtTemplUpc2]' maxlength='8' size='8' value='{$pSet['evtTemplUpc2']}'>&ensp;
	{$ax['evtTemplPop']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[evtTemplPop2]' maxlength='8' size='8' value='{$pSet['evtTemplPop2']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['evtHeadX_text'])."`);'>{$ax['evtHeadX_label']}:</span>
	{$ax['monthView']}:&nbsp;<input type='text' name='pSet[evtHeadM]' maxlength='60' size='19' value='{$pSet['evtHeadM']}'>&ensp;
	{$ax['wkdayView']}:&nbsp;<input type='text' name='pSet[evtHeadW]' maxlength='60' size='19' value='{$pSet['evtHeadW']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['ownerTitle_text'])."`);'>{$ax['ownerTitle_label']}:</span>
	<input type='checkbox' name='pSet[ownerTitle]' value='1'".($pSet['ownerTitle'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['eventColor_text'])."`);'>{$ax['eventColor_label']}:</span>
	<label><input type='radio' name='pSet[eventColor]' value='0'".($pSet['eventColor'] == 0 ? " checked" : '').">{$ax['no_color']}</label>&ensp;
	<label><input type='radio' name='pSet[eventColor]' value='1'".($pSet['eventColor'] == 1 ? " checked" : '').">{$ax['event_cat']}</label>&ensp;
	<label><input type='radio' name='pSet[eventColor]' value='2'".($pSet['eventColor'] == 2 ? " checked" : '').">{$ax['user_group']}</label></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['sortEvents_text'])."`);'>{$ax['sortEvents_label']}:</span>
	<label><input type='radio' name='pSet[evtSorting]' value='0'".($pSet['evtSorting'] == 0 ? " checked" : '').">{$ax['times']}</label>&ensp;
	<label><input type='radio' name='pSet[evtSorting]' value='1'".($pSet['evtSorting'] == 1 ? " checked" : '').">{$ax['cat_seq_nr']}</label></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['privEvents_text'])."`);'>{$ax['privEvents_label']}:</span>
	<label><input type='radio' name='pSet[privEvents]' value='0'".($pSet['privEvents'] == 0 ? " checked" : '').">{$ax['disabled']}</label>&ensp;
	<label><input type='radio' name='pSet[privEvents]' value='1'".($pSet['privEvents'] == 1 ? " checked" : '').">{$ax['enabled']}</label>&ensp;
	<label><input type='radio' name='pSet[privEvents]' value='2'".($pSet['privEvents'] == 2 ? " checked" : '').">{$ax['default']}</label>&ensp;
	<label><input type='radio' name='pSet[privEvents]' value='3'".($pSet['privEvents'] == 3 ? " checked" : '').">{$ax['always']}</label>
	</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['venueInput_text'])."`);'>{$ax['venueInput_label']}:</span>
	<label><input type='radio' name='pSet[venueInput]' value='0'".($pSet['venueInput'] == 0 ? " checked" : '').">{$ax['free_text']}</label>&ensp;
	<label><input type='radio' name='pSet[venueInput]' value='1'".($pSet['venueInput'] == 1 ? " checked" : '').">{$ax['venue_list']}</label>&ensp;
	<label><input type='radio' name='pSet[venueInput]' value='2'".($pSet['venueInput'] == 2 ? " checked" : '').">{$ax['both']}</label></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['defVenue_text'])."`);'>{$ax['defVenue_label']}:</span>
	<input type='text' name='pSet[defVenue]' size='45' value='{$pSet['defVenue']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['timeDefault_text'])."`);'>{$ax['timeDefault_label']}:</span>
	<label><input type='radio' name='pSet[timeDefault]' value='0'".($pSet['timeDefault'] == 0 ? " checked" : '').">{$ax['show_times']}</label>&ensp;
	<label><input type='radio' name='pSet[timeDefault]' value='1'".($pSet['timeDefault'] == 1 ? " checked" : '').">{$ax['check_ald']}</label>&ensp;
	<label><input type='radio' name='pSet[timeDefault]' value='2'".($pSet['timeDefault'] == 2 ? " checked" : '').">{$ax['check_ntm']}</label></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['evtDelButton_text'])."`);'>{$ax['evtDelButton_label']}:</span>
	<label><input type='radio' name='pSet[evtDelButton]' value='0'".($pSet['evtDelButton'] == 0 ? " checked" : '').">{$ax['disabled']}</label>&ensp;
	<label><input type='radio' name='pSet[evtDelButton]' value='1'".($pSet['evtDelButton'] == 1 ? " checked" : '').">{$ax['enabled']}</label>&ensp;
	<label><input type='radio' name='pSet[evtDelButton]' value='2'".($pSet['evtDelButton'] == 2 ? " checked" : '').">{$ax['manager_only']}</label></div>
	
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['xFieldx_text'])."`);'>{$ax['xField1_label']}:</span>
	{$ax['xField_label']}:&nbsp;<input type='text' name='pSet[xField1Label]' maxlength='15' size='12' value='{$pSet['xField1Label']}'>&ensp;
	{$ax['min_rights']}:&nbsp;<select name='pSet[xField1Rights]'>
	<option value='1'".($pSet['xField1Rights'] == 1 ? ' selected' : '').">{$ax['grp_priv1']}</option>
	<option value='2'".($pSet['xField1Rights'] == 2 ? ' selected' : '').">{$ax['grp_priv2']}</option>
	<option value='3'".($pSet['xField1Rights'] == 3 ? ' selected' : '').">{$ax['grp_priv3']}</option>
	<option value='4'".($pSet['xField1Rights'] == 4 ? ' selected' : '').">{$ax['grp_priv4']}</option>
	<option value='9'".($pSet['xField1Rights'] == 9 ? ' selected' : '').">{$ax['grp_priv9']}</option>
	</select></div>
	
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['xFieldx_text'])."`);'>{$ax['xField2_label']}:</span>
	{$ax['xField_label']}:&nbsp;<input type='text' name='pSet[xField2Label]' maxlength='15' size='12' value='{$pSet['xField2Label']}'>&ensp;
	{$ax['min_rights']}:&nbsp;<select name='pSet[xField2Rights]'>
	<option value='1'".($pSet['xField2Rights'] == 1 ? ' selected' : '').">{$ax['grp_priv1']}</option>
	<option value='2'".($pSet['xField2Rights'] == 2 ? ' selected' : '').">{$ax['grp_priv2']}</option>
	<option value='3'".($pSet['xField2Rights'] == 3 ? ' selected' : '').">{$ax['grp_priv3']}</option>
	<option value='4'".($pSet['xField2Rights'] == 4 ? ' selected' : '').">{$ax['grp_priv4']}</option>
	<option value='9'".($pSet['xField2Rights'] == 9 ? ' selected' : '').">{$ax['grp_priv9']}</option>
	</select></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['evtWinSmall_text'])."`);'>{$ax['evtWinSmall_label']}:</span>
	<input type='checkbox' name='pSet[evtWinSmall]' value='1'".($pSet['evtWinSmall'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['emojiPicker_text'])."`);'>{$ax['emojiPicker_label']}:</span>
	<input type='checkbox' name='pSet[emojiPicker]' value='1'".($pSet['emojiPicker'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['mapViewer_text'])."`);'>{$ax['mapViewer_label']}:</span>
	<input type='text' name='pSet[mapViewer]' size='45' value='{$pSet['mapViewer']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['evtDrAndDr_text'])."`);'>{$ax['evtDrAndDr_label']}:</span>
	<label><input type='radio' name='pSet[evtDrAndDr]' value='0'".($pSet['evtDrAndDr'] == 0 ? " checked" : '').">{$ax['disabled']}</label>&ensp;
	<label><input type='radio' name='pSet[evtDrAndDr]' value='1'".($pSet['evtDrAndDr'] == 1 ? " checked" : '').">{$ax['enabled']}</label>&ensp;
	<label><input type='radio' name='pSet[evtDrAndDr]' value='2'".($pSet['evtDrAndDr'] == 2 ? " checked" : '').">{$ax['manager_only']}</label></div>
</fieldset>\n";

//== Views ==
echo "<fieldset class='setting'><legend>{$ax['set_view_settings']}</legend>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['yearStart_text'])."`);'>{$ax['yearStart_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[yearStart]' maxlength='2' size='2' value='{$pSet['yearStart']}'> (1 - 12 {$ax['or']} 0)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['YvRowsColumns_text'])."`);'>{$ax['YvRowsColumns_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[YvRowsToShow]' maxlength='2' size='2' value='{$pSet['YvRowsToShow']}'> {$ax['rows']} (1 - 10)&ensp;<input type='text'{$errors[$e++]} name='pSet[YvColsToShow]' maxlength='1' size='2' value='{$pSet['YvColsToShow']}'> {$ax['columns']} (1 - 6)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['MvWeeksToShow_text'])."`);'>{$ax['MvWeeksToShow_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[MvWeeksToShow]' maxlength='2' size='2' value='{$pSet['MvWeeksToShow']}'> (2 - 20 {$ax['or']} 0 {$ax['or']} 1)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['XvWeeksToShow_text'])."`);'>{$ax['XvWeeksToShow_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[XvWeeksToShow]' maxlength='2' size='2' value='{$pSet['XvWeeksToShow']}'> (4 - 20)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['GvWeeksToShow_text'])."`);'>{$ax['GvWeeksToShow_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[GvWeeksToShow]' maxlength='2' size='2' value='{$pSet['GvWeeksToShow']}'> (4 - 20)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['workWeekDays_text'])."`);'>{$ax['workWeekDays_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[workWeekDays]' maxlength='7' size='6' value='{$pSet['workWeekDays']}'> (0: {$wkDays_l[0]}, 1: {$wkDays_l[1]} .... 6: {$wkDays_l[6]})</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['weekStart_text'])."`);'>{$ax['weekStart_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[weekStart]' maxlength='1' size='1' value='{$pSet['weekStart']}'> (0: {$wkDays_l[0]}, 1: {$wkDays_l[1]} .... 6: {$wkDays_l[6]})</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['lookBackAhead_text'])."`);'>{$ax['lookBackAhead_label']}:</span>
	{$ax['back']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[lookbackDays]' maxlength='3' size='2' value='{$pSet['lookbackDays']}'>&ensp;
	{$ax['ahead']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[lookaheadDays]' maxlength='3' size='2' value='{$pSet['lookaheadDays']}'> (1 - 365)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['searchBackAhead_text'])."`);'>{$ax['searchBackAhead_label']}:</span>
	{$ax['back']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[searchBackDays]' maxlength='3' size='2' value='{$pSet['searchBackDays']}'>&ensp;
	{$ax['ahead']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[searchAheadDays]' maxlength='3' size='2' value='{$pSet['searchAheadDays']}'> (1 - 999)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['dwStartEndHour_text'])."`);'>{$ax['dwStartEndHour_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[dwStartHour]' maxlength='2' size='2' value='{$pSet['dwStartHour']}'> (0 - 18)&ensp;
	<input type='text'{$errors[$e++]} name='pSet[dwEndHour]' maxlength='2' size='2' value='{$pSet['dwEndHour']}'> (6 - 24)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['dwTimeSlot_text'])."`);'>{$ax['dwTimeSlot_label']}:</span>
	{$ax['dwTsInterval']}:&nbsp;<select name='pSet[dwTimeSlot]'>
	<option value='10'".($pSet['dwTimeSlot'] == "10" ? ' selected' : '').">10</option>
	<option value='15'".($pSet['dwTimeSlot'] == "15" ? ' selected' : '').">15</option>
	<option value='20'".($pSet['dwTimeSlot'] == "20" ? ' selected' : '').">20</option>
	<option value='30'".($pSet['dwTimeSlot'] == "30" ? ' selected' : '').">30</option>
	<option value='60'".($pSet['dwTimeSlot'] == "60" ? ' selected' : '').">60</option>
	</select>&nbsp;{$ax['minutes']}&ensp;
	{$ax['dwTsHeight']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[dwTsHeight]' maxlength='2' size='2' value='{$pSet['dwTsHeight']}'> {$ax['pixels']} (10 - 60)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['showSpanel_text'])."`);'>{$ax['showSpanel_label']}:</span>
	{$ax['spMiniCal']}:&nbsp;<input type='text' name='pSet[spMiniCal]' maxlength='20' size='6' value='{$pSet['spMiniCal']}'>&ensp;
	{$ax['spImages']}:&nbsp;<input type='text' name='pSet[spImages]' maxlength='20' size='6' value='{$pSet['spImages']}'>&ensp;
	{$ax['spInfoArea']}:&nbsp;<input type='text' name='pSet[spInfoArea]' maxlength='20' size='6' value='{$pSet['spInfoArea']}'>&ensp;
	<label><input type='checkbox' name='pSet[spDateFixed]' value='1'".($pSet['spDateFixed'] == 1 ? " checked" : '').">{$ax['spToday']}</label></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['topBarDate_text'])."`);'>{$ax['topBarDate_label']}:</span>
	<input type='checkbox' name='pSet[topBarDate]' value='1'".($pSet['topBarDate'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['weekNumber_text'])."`);'>{$ax['weekNumber_label']}:</span>
	<input type='checkbox' name='pSet[weekNumber]' value='1'".($pSet['weekNumber'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['showImgInMV_text'])."`);'>{$ax['showImgInMV_label']}:</span>
	<input type='checkbox' name='pSet[showImgInMV]' value='1'".($pSet['showImgInMV'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['monthInDCell_text'])."`);'>{$ax['monthInDCell_label']}:</span>
	<input type='checkbox' name='pSet[monthInDCell]' value='1'".($pSet['monthInDCell'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['scrollDCell_text'])."`);'>{$ax['scrollDCell_label']}:</span>
	<input type='checkbox' name='pSet[scrollDCell]' value='1'".($pSet['scrollDCell'] == 1 ? " checked" : '')."></div>
</fieldset>\n";

//== Dates/Times ==
echo "<fieldset class='setting'><legend>{$ax['set_dt_settings']}</legend>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['dateFormat_text'])."`);'>{$ax['dateFormat_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[dateFormat]' size='4' value='{$pSet['dateFormat']}'> ({$ax['dateFormat_expl']})</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['MdFormat_text'])."`);'>{$ax['MdFormat_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[MdFormat]' size='4' value='{$pSet['MdFormat']}'> ({$ax['MdFormat_expl']})</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['MdyFormat_text'])."`);'>{$ax['MdyFormat_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[MdyFormat]' size='4' value='{$pSet['MdyFormat']}'> ({$ax['MdyFormat_expl']})</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['MyFormat_text'])."`);'>{$ax['MyFormat_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[MyFormat]' size='4' value='{$pSet['MyFormat']}'> ({$ax['MyFormat_expl']})</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['DMdFormat_text'])."`);'>{$ax['DMdFormat_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[DMdFormat]' size='7' value='{$pSet['DMdFormat']}'> ({$ax['DMdFormat_expl']})</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['DMdyFormat_text'])."`);'>{$ax['DMdyFormat_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[DMdyFormat]' size='7' value='{$pSet['DMdyFormat']}'> ({$ax['DMdyFormat_expl']})</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['timeFormat_text'])."`);'>{$ax['timeFormat_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[timeFormat]' size='4' value='{$pSet['timeFormat']}'> ({$ax['timeFormat_expl']})</div>
</fieldset>\n";

//== File Uploads ==
echo "<fieldset class='setting'><legend>{$ax['set_upload_settings']}</legend>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['maxUplSize_text'])."`);'>{$ax['maxUplSize_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[maxUplSize]' maxlength='3' size='4' value='{$pSet['maxUplSize']}'> {$ax['mbytes']}</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['attTypes_text'])."`);'>{$ax['attTypes_label']}:</span>
	<input type='text' name='pSet[attTypes]' maxlength='70' size='45' value='{$pSet['attTypes']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['tnlTypes_text'])."`);'>{$ax['tnlTypes_label']}:</span>
	<input type='text' name='pSet[tnlTypes]' maxlength='70' size='45' value='{$pSet['tnlTypes']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['tnlMaxSize_text'])."`);'>{$ax['tnlMaxSize_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[tnlMaxW]' maxlength='3' size='4' value='{$pSet['tnlMaxW']}'>&nbsp;x&nbsp;<input type='text'{$errors[$e++]} name='pSet[tnlMaxH]' maxlength='3' size='4' value='{$pSet['tnlMaxH']}'> {$ax['wxhinpx']} (10 - 800)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['tnlDelDays_text'])."`);'>{$ax['tnlDelDays_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[tnlDelDays]' maxlength='2' size='4' value='{$pSet['tnlDelDays']}'> {$ax['days']}</div>
</fieldset>\n";

//== Reminders ==
echo "<fieldset class='setting'><legend>{$ax['set_reminder_settings']}</legend>
	<div class='borderB'>&emsp;{$ax['general']}</div>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['services_text'])."`);'>{$ax['services_label']}:</span>
	<label><input type='checkbox' name='pSet[emlService]' value='1'".($pSet['emlService'] ? " checked" : '').">{$ax['email']}</label>&ensp;
	<label><input type='checkbox' name='pSet[tlgService]' value='1'".($pSet['tlgService'] ? " checked" : '').">{$ax['telegram']}</label>&ensp;
	<label><input type='checkbox' name='pSet[smsService]' value='1'".($pSet['smsService'] ? " checked" : '').">{$ax['sms']}</label></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['defRecips_text'].'<br>'.$ax['reciplist'])."`);'>{$ax['defRecips_label']}:</span>
	<input type='text' placeholder='{$ax['chgRecipList']}' name='pSet[defRecips]' maxlength='255' size='60' value='{$pSet['defRecips']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['maxEmlCc_text'])."`);'>{$ax['maxEmlCc_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[maxEmlCc]' maxlength='2' size='2' value='{$pSet['maxEmlCc']}'> (5 - 99)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['msgLogging_text'])."`);'>{$ax['msgLogging_label']}:</span>
	<input type='checkbox' name='pSet[msgLogging]' value='1'".($pSet['msgLogging'] ? " checked" : '').">&ensp;
	{$ax['weeks']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[msgLogWeeks]' maxlength='2' size='2' value='{$pSet['msgLogWeeks']}'> (1 - 99)</div>

	<div class='borderB'>&emsp;{$ax['email']}</div>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['notSenderEml_text'])."`);'>{$ax['notSenderEml_label']}:</span>
	<input type='checkbox' name='pSet[notSenderEml]' value='1'".($pSet['notSenderEml'] ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['emlFootnote_text'])."`);'>{$ax['emlFootnote_label']}:</span>
	<textarea style='max-width:40%;' name='pSet[emlFootnote]' rows='1'>{$pSet['emlFootnote']}</textarea></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['mailServer_text'])."`);'>{$ax['mailServer_label']}:</span>
	<label><input type='radio' name='pSet[mailServer]' value='1'".($pSet['mailServer'] == 1 ? " checked" : '').">{$ax['php_mail']}</label>&ensp;
	<label><input type='radio' name='pSet[mailServer]' value='2'".($pSet['mailServer'] == 2 ? " checked" : '').">{$ax['smtp_mail']}</label></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['smtpServer_text'])."`);'>{$ax['smtpServer_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[smtpServer]' size='45' value='{$pSet['smtpServer']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['smtpPort_text'])."`);'>{$ax['smtpPort_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[smtpPort]' maxlength='5' size='2' value='{$pSet['smtpPort']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['smtpSsl_text'])."`);'>{$ax['smtpSsl_label']}:</span>
	<input type='checkbox' name='pSet[smtpSsl]' value='1'".($pSet['smtpSsl'] ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['smtpAuth_text'])."`);'>{$ax['smtpAuth_label']}:</span>
	<input type='checkbox' name='pSet[smtpAuth]' value='1'".($pSet['smtpAuth'] ? " checked" : '').">&ensp;{$ax['username']}:&nbsp;<input type='text'{$errors[$e++]} name='pSet[smtpUser]' size='16' value='{$pSet['smtpUser']}'>&ensp;{$ax['password']}:&nbsp;<input type='password'{$errors[$e++]} name='pSet[smtpPass]' size='16' value='{$pSet['smtpPass']}'></div>

	<div class='borderB'>&emsp;{$ax['telegram']}</div>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['tlgToken_text'])."`);'>{$ax['tlgToken_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[tlgToken]' size='45' value='{$pSet['tlgToken']}'></div>

	<div class='borderB'>&emsp;{$ax['sms']}</div>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['notSenderSms_text'])."`);'>{$ax['notSenderSms_label']}:</span>
	<label><input type='radio' name='pSet[notSenderSms]' value='0'".($pSet['notSenderSms'] == 0 ? " checked" : '').">{$ax['calendar']}</label>&ensp;
	<label><input type='radio' name='pSet[notSenderSms]' value='1'".($pSet['notSenderSms'] == 1 ? " checked" : '').">{$ax['user']}</label></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['calPhone_text'])."`);'>{$ax['calPhone_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[calendarPhone]' size='24' maxlength='20' value='{$pSet['calendarPhone']}'></div>
	
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['smsCarrier_text'])."`);'>{$ax['smsCarrier_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[smsCarrier]' size='45' value='{$pSet['smsCarrier']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['smsCountry_text'])."`);'>{$ax['smsCountry_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[smsCountry]' maxlength='6' size='2' value='{$pSet['smsCountry']}'>&ensp;
	<label><input type='checkbox' name='pSet[cCodePrefix]' value='1'".($pSet['cCodePrefix'] ? " checked" : '').">{$ax['cc_prefix']}</label></div>
	
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['smsSubject_text'])."`);'>{$ax['smsSubject_label']}:</span>
	<input type='text' name='pSet[smsSubject]' size='45' value='{$pSet['smsSubject']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['maxLenSms_text'])."`);'>{$ax['maxLenSms_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[maxLenSms]' maxlength='3' size='2' value='{$pSet['maxLenSms']}'> (70 - 500 bytes)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['smsAddLink_text'])."`);'>{$ax['smsAddLink_label']}:</span>
	<input type='checkbox' name='pSet[smsAddLink]' value='1'".($pSet['smsAddLink'] ? " checked" : '')."></div>
</fieldset>\n";

//== Periodic Functions ==
echo "<fieldset class='setting'><legend>{$ax['set_perfun_settings']}</legend>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['cronHost_text'])."`);'>{$ax['cronHost_label']}:</span>
	<label><input type='radio' name='cronHost' value='0'".($cronHost == 0 ? " checked" : '').">{$ax['local']}</label>&ensp;
	<label><input type='radio' name='cronHost' value='1'".($cronHost == 1 ? " checked" : '').">{$ax['remote']}</label>&ensp;
	<label><input type='radio' name='cronHost' value='2'".($cronHost == 2 ? " checked" : '').">{$ax['ip_address']}</label>:&nbsp;<input type='text'{$errors[$e++]} name='cronIpAd' maxlength='15' size='12' value='{$cronIpAd}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['cronSummary_text'])."`);'>{$ax['cronSummary_label']}:</span>
	<label><input type='radio' name='pSet[adminCronSum]' value='0'".($pSet['adminCronSum'] == 0 ? " checked" : '').">{$ax['disabled']}</label>&ensp;
	<label><input type='radio' name='pSet[adminCronSum]' value='1'".($pSet['adminCronSum'] == 1 ? " checked" : '').">{$ax['enabled']}</label></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['icsExport_text'])."`);'>{$ax['icsExport_label']}:</span>
	<input type='checkbox' name='pSet[icsExport]' value='1'".($pSet['icsExport'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['eventExp_text'])."`);'>{$ax['eventExp_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[eventExp]' maxlength='3' size='2' value='{$pSet['eventExp']}'> (0 - 999)</div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['maxNoLogin_text'])."`);'>{$ax['maxNoLogin_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[maxNoLogin]' maxlength='3' size='2' value='{$pSet['maxNoLogin']}'> (0 - 365)</div>
</fieldset>\n";

//== Stand-Alone Sidebar ==
echo "<fieldset class='setting'><legend>{$ax['set_sidebar_settings']}</legend>
	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['popFieldsSbar_text'].'<br>'.$ax['templFields_text'])."`);'>{$ax['popFieldsSbar_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[popFieldsSbar]' maxlength='7' size='6' value='{$pSet['popFieldsSbar']}'></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['showLinkInSB_text'])."`);'>{$ax['showLinkInSB_label']}:</span>
	<input type='checkbox' name='pSet[showLinkInSB]' value='1'".($pSet['showLinkInSB'] == 1 ? " checked" : '')."></div>

	<div><span class='sLabel' onmouseover='popM(this,`".unQuote($ax['sideBarDays_text'])."`);'>{$ax['sideBarDays_label']}:</span>
	<input type='text'{$errors[$e++]} name='pSet[sideBarDays]' maxlength='3' size='2' value='{$pSet['sideBarDays']}'> (1 - 365)</div>\n";
?>
</fieldset>
</div>
</form>
