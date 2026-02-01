<?php
/*
= LuxCal cronjobs =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

This file should be executed via a cronjob once a day at 3:15am user time
=============================================================================

It will subsequently start the following scripts:
1. notify.php: 
	Generate email notifications for events for which the user has asked a 
	notification a certain number of days before the event date.
	
2. expical.php (only if selected on the Settings page):
	Export events in iCalendar format to a .ics file in 'files' folder. Events
	in the time bracket -7 days till +365 days will be exported. The file name
	will be the calendar name.

3. eventchk.php (only if selected on the Settings page):
	Delete events when expired. Events will expire when the event's due date +
	eventExp days have passed. 	If setting 'eventExp' = 0, NO events will be
	deleted.

4. userchk.php (only if selected on the Settings page):
	Delete 'inactive' user accounts. If setting 'maxNoLogin' = 0, NO user
	accounts will be deleted.

---------------------------- CRON JOB SETTINGS ------------------------------
General:
  A cron job is defined by a "time definition" and a "command to be executed"
	
Time definition for LuxCal (Unix notation):
  Minute Hour Day Month Weekday
    15    3    *    *      *
Command:
  Ask your provider for the command syntax to execute the script lcalcron.php
  in the root of your calendar installation.
  It should look something like:
  php -q /home/youraccount/public_html/yoursite.com/calendar/lcalcron.php
	
Notes:
1. If the calendar server and the calendar user are in different time zones,
zones, the time setting should correspond to 3:15am user time.
2. If your cron job is running on a remote server, or if you want to start 
lcalcron.php manually via your browser, then go to the admin's Settings page 
and under Periodic Functions change the Cron job host accordingly.
-----------------------------------------------------------------------------

------------------ THIS SCRIPT USES THE FOLLOWING SETTINGS ------------------
The database credentials : to connect to the calendar database
adminCronSum: Send cron job summary to admin (1 = yes, 0 = no)
calendarEmail: Email sender ("from") for notification messages
timeZone: To get the current time right
icsExport: Export events in iCalendar format (1 = yes, 0 = no)
eventExp: Number of days after due date when an event can be deleted
maxNoLogin: Number of 'no login' days, before a user account is deleted
From lcconfig.php:
$crHost: Cron service host 0:local, 1:remote, 2:remote+IP address
$crIpAd: Cron service IP address (only if crHost = 2)
-----------------------------------------------------------------------------
*/
//
//Send cronjob summary
//
function sendSum($sumReport) {
	global $cmlStyle, $set, $ax;

	$subject = $ax['cro_sum_header'];
	//create cronjob summary message
	$msgBody = "
<p>=== {$ax['cro_sum_header']} ~ ".IDtoDD(date("Y-m-d"))." {$ax['at_time']} ".date("H:i")." ===</p>
<br>{$sumReport}<br>
<p>=== {$ax['cro_sum_trailer']} ===</p>
";
	sendEml($subject,$msgBody,[$set['calendarEmail']],1,0,0);
}
//end of Send cronjob summary

//prevent abortion when run as command line script
ignore_user_abort(true);

//set working directory
chdir(dirname(__FILE__));

//set user parameters
$usr['vCats'] = '0'; //view: all categories
$usr['eCats'] = ''; //edit: no categories

//load config data
require './lcconfig.php';

//load toolboxes
require './common/messaging.php';
require './common/toolbox.php';
require './common/toolboxd.php'; //database tools

//log start of cron job
$message = "Cron job started - Cron host: ".($crHost == 0 ? 'local' : 'remote');
if ($crHost >= 1) {
	$message .= ' - Remote IP address: '.($_SERVER['REMOTE_ADDR'] ?? 'None');
}
if ($crHost == 2) {
	$message .= " - Required IP address: {$crIpAd}";
}
logMessage('luxcal',0,$message,'lcalcron:'.__LINE__);

//security checks
if ($crHost == 0 and !empty($_SERVER['HTTP_USER_AGENT'])) { //local cron only (via browser not allowed)
	logMessage('luxcal',0,'Aborted - Local cron started from remote server.','lcalcron:'.__LINE__); //log abortion of cron job
	exit();
} elseif ($crHost == 2 and $_SERVER['REMOTE_ADDR'] != $crIpAd) { //remote cron with fixed IP address
	logMessage('luxcal',0,'Aborted - Remote cron IP-address mismatch.','lcalcron:'.__LINE__); //log abortion of cron job
	exit();
}

if ($dbType == 'MySQL') { //MySQL
	if (!$dbH = dbConnect('void',0)) { exit('Could not connect to calendar database'); } //connect to db
}

//get calendars
$calIDs = getCIDs();
if (empty($calIDs)) { exit('No calendars found in database'); }

//load retrieve functions
require './common/retrieve.php';
require './common/retrievc.php';

//load cronjob functions
require './cronjobs/notify.php';
require './cronjobs/expical.php';
require './cronjobs/eventchk.php';
require './cronjobs/userchk.php';

//run job for each calendar in the db
foreach ($calIDs as $cID) {
	if ($dbType == 'SQLite') { //SQLite
		$dbH = dbConnect($cID); //connect to database
	} else { //MySQL	
		$calID = $cID; //set current active calendar ID
	}

	//get settings from database
	$set = getSettings();

	//load language files
	require_once './lang/ui-'.strtolower($set['language']).'.php';
	require_once './lang/ai-'.strtolower($set['language']).'.php';

	//set timezone
	date_default_timezone_set($set['timeZone']);
	
	$sumReport = ''; //init

//1 - check for notifications to be sent
	$sentTo = cronNotify();
	$sumText = $sentTo ? $sentTo : $ax['cro_no_reminders_due'].".\n";
	$sumReport .= "<h4>{$ax['cro_sum_title_not']}</h4>\n<p>".nl2br(trim($sumText))."</p>\n";

//2 - export events in iCalendar format to .ics file in 'files' folder
	if ($set['icsExport'] > 0) {
		$fileName = '';
		$nrExported = cronExpIcal();
		$sumText = "{$ax['cro_nr_events_exported']} {$fileName}: {$nrExported}.\n";
		$sumReport .= "<h4>{$ax['cro_sum_title_ice']}</h4>\n<p>".nl2br(trim($sumText))."</p>\n";
	}

//3 - check for expired events which can be deleted
	if ($set['eventExp'] > 0) {
		$nrDeleted = cronEventChk();
		$sumText = "{$ax['cro_nr_evts_deleted']}: {$nrDeleted}.\n";
		$sumReport .= "<h4>{$ax['cro_sum_title_eve']}</h4>\n<p>".nl2br(trim($sumText))."</p>\n";
	}

//4 - check for unused user accounts
	if ($set['maxNoLogin'] > 0) {
		$nrRemoved = cronUserChk();
		$sumText = ($nrRemoved > 0) ? "{$ax['cro_nr_accounts_deleted']}: {$nrRemoved}\n" : $ax['cro_no_accounts_deleted'].".\n";
		$sumReport .= "<h4>{$ax['cro_sum_title_use']}</h4>\n<p>".nl2br(trim($sumText))."</p>\n";
	}

	if (!$sumReport) { //No reminders or periodic services active
		$sumReport = "<h5>{$ax['cro_none_active']}</h5><br>\n";
	}

	if ($set['adminCronSum']) { //send cronjob summary to admin
		sendSum($sumReport);
	}
}
//log completion of cron job
logMessage('luxcal',0,'OK.','lcalcron:'.__LINE__); //log end of cron job
?>