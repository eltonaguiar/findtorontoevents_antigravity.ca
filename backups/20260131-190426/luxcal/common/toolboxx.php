<?php
/*
======== ADMIN WORK BENCH TOOLS =========

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

*/
$httpX = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] != 'off' ? 'https' : 'http'); //init

//default settings
$defSet = [ //name => default value, outline
	'calendarTitle' => ['LuxCal Calendar','Calendar title displayed in the top bar'],
	'calendarUrl' => ["{$httpX}://{$_SERVER['SERVER_NAME']}".rtrim(dirname($_SERVER["PHP_SELF"]),'/').'/index.php','Calendar link (URL)'],
	'backLinkUrl' => ['','Nav bar back link URL (blank: no link, url: link)'],
	'logoPath' => ['','Path/name of optional left upper corner logo image'],
	'logoXlPath' => ['','Path/name of optional login page logo image'],
	'logoHeight' => ['','Height of the login page logo image'],
	'timeZone' => ['Europe/Amsterdam','Calendar time zone'],
	'chgRecipList' => ['','List of notification email/SMS addresses'],
	'maxXsWidth' => [800,'Upper limit responsive calendar mode'],
	'rssFeed' => [1,'Display RSS feed links in footer and HTML head (0:no, 1:yes)'],
	'logWarnings' => [1,'Log calendar warning messages (0:no, 1:yes)'],
	'logNotices' => [0,'Log calendar notice messages (0:no, 1:yes)'],
	'logVisitors' => [0,'Log calendar visitors data (0:no, 1:yes)'],
	'maintMode' => [0,'Run calendar in maintenance mode (0:no, 1:yes)'],
	'contButton' => [1,'Display Contact button in side menu (0:no, 1:yes)'],
	'calMenu' => [1,'Display calendar menu in options panel (0:no, 1:yes)'],
	'viewMenu' => [1,'Display view menu in options panel (0:no, 1:yes)'],
	'groupMenu' => [1,'Display group filter menu in options panel (0:no, 1:yes)'],
	'userMenu' => [1,'Display user filter menu in options panel (0:no, 1:yes)'],
	'catMenu' => [1,'Display category filter menu in options panel(0:no, 1:yes)'],
	'langMenu' => [0,'Display ui-language selection menu in options panel (0:no, 1:yes)'],
	'birthdayCal' => [0,'Display option PDF File - Birthdays in side menu (0:no, 1:yes)'],
	'toapList' => [1,'Display option Approve in side menu (0:no, 1:yes)'],
	'todoList' => [1,'Display option Todo in side menu (0:no, 1:yes)'],
	'upcoList' => [1,'Display option Upcoming in side menu (0:no, 1:yes)'],
	'viewsPublic' => ['1,2,3,4,5,6,7,8,9,10,11','Calendar views available to the public users'],
	'viewsLogged' => ['1,2,3,4,5,6,7,8,9,10,11','Calendar views available to the logged-in users'],
	'viewButsPubL' => ['2,7','View buttons on the navbar (1:year, ... 11:gantt) - public user, large display'],
	'viewButsLogL' => ['1,2,4,7','View buttons on the navbar (1:year, ... 11:gantt) - logged in user, large display'],
	'viewButsPubS' => ['','View buttons on the navbar (1:year, ... 11:gantt) - public user, small display'],
	'viewButsLogS' => ['2,7','View buttons on the navbar (1:year, ... 11:gantt) - logged in user, small display'],
	'defViewPubL' => [2,'View large display at start-up (1:year, ... 8:changes) - public user'],
	'defViewPubS' => [7,'View small display at start-up (1:year, ... 8:changes) - public user'],
	'defViewLogL' => [2,'View large display at start-up (1:year, ... 8:changes) - logged in user'],
	'defViewLogS' => [7,'View small display at start-up (1:year, ... 8:changes) - logged in user'],
	'language' => ['English','Default user interface language'],
	'privEvents' => [1,'Private events (0:disabled 1:enabled, 2:default, 3:always)'],
	'venueInput' => [0,'Venue input (0:free text 1:drop-down list, 2:both)'],
	'timeDefault' => [0,'Time default for new events (0:time fields 1:all day 2: no time)'],
	'evtDelButton' => [1,'Display Delete button in Event window (0:no, 1:yes, 2:manager)'],
	'defVenue' => ['','Default venue in the venue field of the event form'],
	'xField1Label' => ['','Label optional extra event field 1'],
	'xField2Label' => ['','Label optional extra event field 2'],
	'xField1Rights' => [1,'Extra event field 1 minimum required rights to see'],
	'xField2Rights' => [1,'Extra event field 2 minimum required rights to see'],
	'selfReg' => [0,'Self-registration (0:no, 1:yes)'],
	'selfRegGrp' => [4,'Self-registration user group ID'],
	'selfRegQ' => ['','Self-registration question to answer'],
	'selfRegA' => ['','Self-registration answer to selfregQ'],
	'selfRegNot' => [0,'User self-reg notification to admin (0:no, 1:yes)'],
	'restLastSel' => [1,'Restore last session when user revisits calendar'],
	'cookieExp' => [30,'Number of days before a Remember Me cookie expires'],
	'evtTemplGen' => ['12345678','Public user: Event fields and order in general views'],
	'evtTemplUpc' => ['123458','Public user: Event fields and order in upcoming events view'],
	'evtTemplPop' => ['123458','Public user: Event fields and order in hover box'],
	'evtTemplGen2' => ['','Logged-in user: Event fields and order in general views'],
	'evtTemplUpc2' => ['','Logged-in user: Event fields and order in upcoming events view'],
	'evtTemplPop2' => ['','Logged-in user: Event fields and order in hover box'],
	'evtHeadM' => ['#ts #e','Event fields / layout template for month view'],
	'evtHeadW' => ['#ts #e','Event fields / layout template for week and day views'],
	'ownerTitle' => [0,'Prepend owner to event title (0:disabled 1:enabled)'],
	'eventColor' => [1,'Event colors (0:no color, 1:cat color, 2:user group color)'],
	'evtSorting' => [0,'Sort events on times or cat. seq. nr (0:times, 1:cat seq nr)'],
	'yearStart' => [0,'Start month in year view (1-12 or 0, 0:current month)'],
	'YvColsToShow' => [3,'Number of months to show per row in year view'],
	'YvRowsToShow' => [4,'Number of rows to show in year view'],
	'MvWeeksToShow' => [10,'Number of weeks to show in month view'],
	'XvWeeksToShow' => [8,'Number of weeks to show in matrix view'],
	'GvWeeksToShow' => [8,'Number of weeks to show in gantt view'],
	'workWeekDays' => ['12345','Working days (0: su - 6: sa)'],
	'weekStart' => [1,'First day of the week (0: su - 6: sa)'],
	'lookbackDays' => [30,'Days to look back in the todo list'],
	'lookaheadDays' => [14,'Days to look ahead in upcoming view, todo list and RSS feeds'],
	'searchBackDays' => [365,'Default days to look back on Search page'],
	'searchAheadDays' => [365,'Defalt days to look ahead on Search page'],
	'dwStartHour' => [6,'Day/week view start hour'],
	'dwEndHour' => [18,'Day/week view end hour'],
	'dwTimeSlot' => [30,'Day/week time slot in minutes'],
	'dwTsHeight' => [20,'Day/week time slot height in pixels'],
	'spMiniCal' => ['','Show mini calendar in side panel (csv-list with views)'],
	'spImages' => ['','Show images in side panel (csv-list with views)'],
	'spInfoArea' => ['','Show info area in side panel (csv-list with views)'],
	'spDateFixed' => [0,'Side panel date fixed (0:cD is taken, 1:date of today)'],
	'topBarDate' => [1,'Show current date on top bar in calendar views (0:no, 1:yes)'],
	'weekNumber' => [1,'Week numbers on(1) or off(0)'],
	'showImgInMV' => [0,'Show images in month view (0:no, 1:yes)'],
	'monthInDCell' => [0,'Show in month view month for each day (0:no, 1:yes)'],
	'scrollDCell' => [0,'Vertical scrollbar in month view day cells (0:no, 1:yes)'],
	'evtWinSmall' => [0,'Show reduced Event window (0:no, 1:yes)'],
	'emojiPicker' => [1,'Show emoji picker in Event Add/Edit window (0:no, 1:yes)'],
	'mapViewer' => ['https://maps.google.com/maps?q=','map viewer for the event address button'],
	'evtDrAndDr' => [0,'Event drag and drop (0:disabled, 1:enabled, 2:manager)'],
	'dateFormat' => ['d.m.y','Date format: yyyy-mm-dd (y:yyyy, m:mm, d:dd)'],
	'MdFormat' => ['d M','Date format: dd month (d:dd, M:month)'],
	'MdyFormat' => ['d M y','Date format: dd month yyyy (d:dd, M:month, y:yyyy)'],
	'MyFormat' => ['M y','Date format: month yyyy (M:month, y:yyyy)'],
	'DMdFormat' => ['WD d M','Date format: weekday dd month (WD:weekday d:dd, M:month)'],
	'DMdyFormat' => ['WD d M y','Date format: weekday dd month yyyy (WD:weekday d:dd, M:month, y:yyyy)'],
	'timeFormat' => ['h:m','Time format (H:hh, h:h, m:mm, a:am|pm, A:AM|PM)'],
	'maxUplSize' => [2,'Max. size of uploaded attachment and thumbnail files in MBs'],
	'attTypes' => ['.pdf,.jpg,.gif,.png,.mp4,.avi','Valid types of uploaded attachments'],
	'tnlTypes' => ['.jpg,.jpeg,.gif,.png','Valid types of uploaded thumbnails'],
	'tnlMaxW' => ['160','Max. width of uploaded thumbnails image in pixels'],
	'tnlMaxH' => ['120','Max. height of uploaded thumbnails image in pixels'],
	'tnlDelDays' => ['20','thumbnails used since last 20 days cannot be deleted'],
	'emlService' => [1,'Email service (0:no, 1:yes)'],
	'tlgService' => [0,'Telegram service (0:no, 1:yes)'],
	'smsService' => [0,'SMS service (0:no, 1:yes)'],
	'defRecips' => ['','Default recipients list for email and SMS notifications'],
	'maxEmlCc' => [10,'Default max. number of recipients in email Cc field'],
	'msgLogging' => [0,'Notification message logging'],
	'msgLogWeeks' => [2,'Default max. number of weeks to keep message logs'],
	'notSenderEml' => [0,'Sender of notification emails (0:calendar, 1:user)'],
	'emlFootnote' => ['','Footnote text added to email reminders'],
	'calendarEmail' => ['calendar@email.com','Sender of email notifications'],
	'smtpServer' => ['','SMTP mail server name'],
	'smtpPort' => [465,'SMTP port number'],
	'smtpSsl' => [1,'Use SSL (Secure Sockets Layer) (0:no, 1:yes)'],
	'smtpAuth' => [1,'Use SMTP authentication (0:no, 1:yes)'],
	'smtpUser' => ['','SMTP username'],
	'smtpPass' => ['','SMTP password'],
	'tlgToken' => ['','Telegram token'],
	'notSenderSms' => [0,'Sender of notification SMSes (0:calendar, 1:user)'],
	'calendarPhone' => ['','Sender of SMS notifications'],
	'smsCarrier' => ['','SMS carrier template (# = mob. phone number)'],
	'smsCountry' => ['','SMS country code'],
	'cCodePrefix' => [1,'Country code starts with prefix + or 00 (0:no, 1:yes)'],
	'smsSubject' => [' ','Subject field template for SMS emails to the carrier'],
	'maxLenSms' => [70,'Maximum length of SMS messages (bytes)'],
	'smsAddLink' => [0,'Add event report link to SMS (0:no, 1:yes)'],
	'mailServer' => [1,'Mail server (1:PHP mail, 2:SMTP mail)'],
	'adminCronSum' => [1,'Send cron job summary to admin (0:no, 1:yes)'],
	'icsExport' => [0,'Daily export of events in iCal format (0:no 1:yes)'],
	'eventExp' => [0,'Number of days after due when an event expires / can be deleted (0:never)'],
	'maxNoLogin' => [0,'Number of days not logged in, before deleting user account (0:never delete)'],
	'popFieldsSbar' => ['12345','Event fields in sidebar hover box (none: no box)'],
	'showLinkInSB' => [1,'Show URL-links in sidebar (0:no, 1:yes)'],
	'sideBarDays' => [14,'Days to look ahead in sidebar']
];

//default styles & settings
//B: background, C; color, E: border, F" font family, P: fontsize px, M; font size em
$defSaS = [ //name => default value
	'000' => 'THEME TITLE',
	'THEME' => '', //theme title

	'010' => 'GENERAL',
	'011' => 'BACKGROUND COLORS',
	'BXXXX' => '#E0E0E0', //calendar general
	'BTBAR' => '#FDFDFD', //calendar top bar
	'BBHAR' => '#96B4FF', //bar, headers & lines
	'BBUTS' => '#FFFFFF', //buttons
	'BDROP' => '#FFFFFF', //drop down menus
	'BXWIN' => '#FFFFEE', //event/help window
	'BINBX' => '#FFFFEE', //insert boxes
	'BOVBX' => '#FEFEFE', //overlay boxes
	'BFFLD' => '#FFFFFF', //form fields
	'BCONF' => '#A0D070', //confirmation msg
	'BWARN' => '#FFF0A0', //warning msg
	'BERRO' => '#F0A070', //error msg
	'BHLIT' => '#FF2222', //text highlight
	'012' => 'TEXT COLORS',
	'CXXXX' => '#2B3856', //normal text
	'CTBAR' => '#2B3856', //calendar top bar
	'CBHAR' => '#2B3856', //bars, headers & lines
	'CBUTS' => '#2B3856', //buttons
	'CDROP' => '#2B3856', //drop down menus
	'CXWIN' => '#2B3856', //event/help window
	'CINBX' => '#2B3856', //insert boxes
	'COVBX' => '#2B3856', //overlay boxes
	'CFFLD' => '#2B3856', //form fields
	'CCONF' => '#2B3856', //confirmation msg
	'CWARN' => '#2B3856', //warning msg
	'CERRO' => '#2B3856', //error msg
	'CHLIT' => '#2B3856', //text highlight
	'013' => 'BORDER COLORS',
	'EXXXX' => '#808080', //general borders
	'EOVBX' => '#96B4FF', //overlay borders
	'EBUTS' => '#0080FE', //buttons on hover borders
	'014' => 'FONT FAMILY/SIZES',
	'FFXXX' => 'arial,sans-serif', //base font family
	'PSXXX' => '12', //base font size
	'PTBAR' => '13', //top bar text
	'PPGTL' => '14', //page headers
	'PTHDL' => '13', //table headers L
	'MTHDM' => '1.0', //table headers M
	'MDTHD' => '1.0', //date headers
	'MSNHD' => '1.0', //section headers
	'MOVBX' => '1.0', //side bar, options panel
	'MFFLD' => '1.0', //form fields
	'MBUTS' => '0.9', //buttons
	'MPWIN' => '1.1', //popup window
	'MSMAL' => '0.8', //small text
	'015' => 'MISCELLANEOUS',
	'sTbSw' => 1, //top bar shadow (0:no 1:yes)
	'sCtOf' => 0, //content top in pixels

	'020' => 'GRID / VIEWS',
	'021' => 'BACKGROUND COLORS',
	'BGCTH' => '#F2F2F2', //day cell - hover
	'BGTFD' => '#96B4FF', //first day of month
	'BGWTC' => '#FFFFBB', //grid - weeknr/time column
	'BGWD1' => '#FFFFEE', //grid - weekday month 1
	'BGWD2' => '#FFFFDD', //grid - weekday month 2
	'BGWE1' => '#FFFFCC', //grid - weekend month 1
	'BGWE2' => '#FFFFBB', //grid - weekend month 2
	'BGOUT' => '#FEFEFE', //grid - outside month
	'BGTOD' => '#EEEEFF', //grid - day cell today
	'BGSEL' => '#FFEEEE', //grid - day cell selected day
	'BLINK' => '#FFFFFF', //URL & email links
	'BCHBX' => '#FFFFDD', //todo check box
	'022' => 'TEXT COLORS',
	'CGWTC' => '#666666', //cell head, times, week numbers
	'CGTFD' => '#2B3856', //1st day of month
	'CGWD1' => '#2B3856', //grid - weekday month 1
	'CGWD2' => '#2B3856', //grid - weekday month 2
	'CGWE1' => '#2B3856', //grid - weekend month 1
	'CGWE2' => '#2B3856', //grid - weekend month 2
	'CGOUT' => '#2B3856', //grid - outside month
	'CGTOD' => '#2B3856', //grid - day cell today
	'CGSEL' => '#2B3856', //grid - day cell selected day
	'CLINK' => '#C02020', //URL & email links
	'CCHBX' => '#FF0000', //todo check box
	'023' => 'BORDER COLORS',
	'EGTOD' => '#0000FF', //grid - day cell today
	'EGSEL' => '#FF0000', //grid - day cell selected day
	'024' => 'FONT SIZES',
	'MEVTI' => '1.0', //event title in views

	'030' => 'HOVER BOXES',
	'031' => 'BACKGROUND COLORS',
	'BHNOR' => '#FFFFE0', //normal event
	'BHPRI' => '#CCFFCC', //private event
	'BHREP' => '#FFFFE0', //repeating event
	'032' => 'TEXT COLORS',
	'CHNOR' => '#2B3856', //hover popup box
	'CHPRI' => '#2B3856', //hover popup box
	'CHREP' => '#2B3856', //hover popup box
	'033' => 'BORDER COLORS',
	'EHNOR' => '#808080', //normal event
	'EHPRI' => '#808080', //private event
	'EHREP' => '#E00060', //repeating event
	'034' => 'FONT SIZES',
	'MPOPU' => '1.0' //hover popup box
];

//database table SQL definitions
$sqlTableDefs = [
	"events" => "`ID` INTEGER PRIMARY KEY ".($dbType == 'SQLite' ? 'AUTOINCREMENT' : 'AUTO_INCREMENT').",
		`type` TINYINT NOT NULL DEFAULT 0,
		`private` TINYINT NOT NULL DEFAULT 0,
		`title` VARCHAR(255) NOT NULL DEFAULT '',
		`venue` VARCHAR(128) NOT NULL DEFAULT '',
		`text1` TEXT,
		`text2` VARCHAR(255) NOT NULL DEFAULT '',
		`text3` VARCHAR(255) NOT NULL DEFAULT '',
		`attach` TEXT,
		`catID` MEDIUMINT NOT NULL DEFAULT 1,
		`scatID` TINYINT NOT NULL DEFAULT 0,
		`userID` MEDIUMINT NOT NULL DEFAULT 0,
		`editor` VARCHAR(48) NOT NULL DEFAULT '',
		`approved` TINYINT NOT NULL DEFAULT 0,
		`checked` TEXT,
		`notify` TINYINT NOT NULL DEFAULT -1,
		`notRecip` VARCHAR(255) NOT NULL DEFAULT '',
		`sDate` VARCHAR(10) NOT NULL DEFAULT '',
		`eDate` VARCHAR(10) NOT NULL DEFAULT '9999-00-00',
		`xDates` TEXT,
		`sTime` VARCHAR(5) NOT NULL DEFAULT '',
		`eTime` VARCHAR(5) NOT NULL DEFAULT '99:00',
		`rType` TINYINT NOT NULL DEFAULT 0,
		`rInterval` TINYINT NOT NULL DEFAULT 0,
		`rPeriod` TINYINT NOT NULL DEFAULT 0,
		`rMonth` TINYINT NOT NULL DEFAULT 0,
		`rUntil` VARCHAR(10) NOT NULL DEFAULT '9999-00-00',
		`aDateTime` VARCHAR(16) NOT NULL DEFAULT '9999-00-00 00:00',
		`mDateTime` VARCHAR(16) NOT NULL DEFAULT '9999-00-00 00:00',
		`status` BOOLEAN NOT NULL DEFAULT 0",
	"categories" => "`ID` INTEGER PRIMARY KEY ".($dbType == 'SQLite' ? 'AUTOINCREMENT' : 'AUTO_INCREMENT').",
		`name` VARCHAR(48) NOT NULL DEFAULT '',
		`symbol` VARCHAR(8) NOT NULL DEFAULT '',
		`sequence` TINYINT NOT NULL DEFAULT 1,
		`repeat` TINYINT NOT NULL DEFAULT 0,
		`noverlap` TINYINT NOT NULL DEFAULT 0,
		`olapGap` TINYINT NOT NULL DEFAULT 0,
		`olErrMsg` VARCHAR(56) NOT NULL DEFAULT '',
		`defSlot` SMALLINT NOT NULL DEFAULT 0,
		`fixSlot` TINYINT NOT NULL DEFAULT 0,
		`approve` TINYINT NOT NULL DEFAULT 0,
		`dayColor` TINYINT NOT NULL DEFAULT 0,
		`color` VARCHAR(8) NOT NULL DEFAULT '',
		`bgColor` VARCHAR(8) NOT NULL DEFAULT '',
		`checkBx` TINYINT NOT NULL DEFAULT 0,
		`checkLb` VARCHAR(16) NOT NULL DEFAULT 'approved',
		`checkMk` VARCHAR(8) NOT NULL DEFAULT '&#x2713;',
		`subCats` TEXT,
		`notList` VARCHAR(255) NOT NULL DEFAULT '',
		`urlLink` VARCHAR(120) NOT NULL DEFAULT '',
		`status` BOOLEAN NOT NULL DEFAULT 0",
	"users" => "`ID` INTEGER PRIMARY KEY ".($dbType == 'SQLite' ? 'AUTOINCREMENT' : 'AUTO_INCREMENT').",
		`token` VARCHAR(165) NOT NULL DEFAULT '',
		`name` VARCHAR(48) NOT NULL DEFAULT '',
		`password` VARCHAR(32) NOT NULL DEFAULT '',
		`tPassword` VARCHAR(32) NOT NULL DEFAULT '',
		`email` VARCHAR(255) NOT NULL DEFAULT '',
		`phone` VARCHAR(32) NOT NULL DEFAULT '',
		`msingID` VARCHAR(16) NOT NULL DEFAULT '',
		`notSrvs` VARCHAR(8) NOT NULL DEFAULT '',
		`groupID` MEDIUMINT NOT NULL DEFAULT 3,
		`language` VARCHAR(24) DEFAULT '',
		`expDate` VARCHAR(10) NOT NULL DEFAULT '9999-00-00',
		`login0` VARCHAR(10) NOT NULL DEFAULT '9999-00-00',
		`login1` VARCHAR(10) NOT NULL DEFAULT '9999-00-00',
		`loginCnt` MEDIUMINT NOT NULL DEFAULT 0,
		`status` BOOLEAN NOT NULL DEFAULT 0",
	"groups" => "`ID` INTEGER PRIMARY KEY ".($dbType == 'SQLite' ? 'AUTOINCREMENT' : 'AUTO_INCREMENT').",
		`name` VARCHAR(255) NOT NULL DEFAULT '',
		`privs` TINYINT NOT NULL DEFAULT 0,
		`vCatIDs` VARCHAR(128) NOT NULL DEFAULT '0',
		`eCatIDs` VARCHAR(128) NOT NULL DEFAULT '0',
		`rEvents` TINYINT NOT NULL DEFAULT 1,
		`mEvents` TINYINT NOT NULL DEFAULT 1,
		`pEvents` TINYINT NOT NULL DEFAULT 1,
		`upload` TINYINT NOT NULL DEFAULT 0,
		`tnPrivs` VARCHAR(2) NOT NULL DEFAULT '00',
		`color` VARCHAR(8) NOT NULL DEFAULT '',
		`status` BOOLEAN NOT NULL DEFAULT 0",
	"settings" => "`name` VARCHAR(16) PRIMARY KEY,
		`value` VARCHAR(255) NOT NULL DEFAULT '',
		`outline` VARCHAR(128) NOT NULL DEFAULT ''",
	"styles" => "`name` VARCHAR(8) PRIMARY KEY,
		`value` VARCHAR(255) NOT NULL DEFAULT ''"
];

function createDbTable($name,$drop = 0) { //create database table
	global $sqlTableDefs, $dbType;

	if ($drop) { dbQuery("DROP TABLE IF EXISTS `{$name}`"); }
	$trailer = $dbType == 'MySQL' ? ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4' : '';
	dbQuery("CREATE TABLE IF NOT EXISTS `{$name}` (\n{$sqlTableDefs[rtrim($name,'X')]}){$trailer}");
	if ($dbType == 'MySQL') { dbQuery("ALTER TABLE `{$name}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;"); } //emoji and mb4 characters
}

function initUsers($adName,$adMail,$adPwMd5) { //init users table
	$users = [[1,'Public Access','','',3,''],[2,$adName,$adMail,$adPwMd5,2,'english']]; //public user + admin user
	$stH = stPrep("REPLACE INTO `users` (`ID`,`name`,`email`,`password`,`groupID`,`language`) VALUES (?,?,?,?,?,?)");
	foreach($users as $user) {
		stExec($stH,$user);
	}
}

function initCats() { //init categories table, if needed
	$stH = dbQuery("SELECT 1 FROM `categories` WHERE `status` >= 0");
	if (!$stH->fetch(PDO::FETCH_NUM)) { //empty
		$stH = stPrep("REPLACE INTO `categories` (`ID`,`name`,`sequence`,`subCats`) VALUES (?,?,?,?)");
		stExec($stH,[1,'no cat',1,'[]']);
	}
}

function initGroups() { //init groups table, if needed
	$stH = dbQuery("SELECT 1 FROM `groups` WHERE `status` >= 0");
	if (!$stH->fetch(PDO::FETCH_NUM)) { //empty
		$groups = [[1,'No access',0,'0',0,'00'],[2,'Admin',9,'0',1,'22'],[3,'Read access',1,'0',0,'00'],[4,'Post Own',2,'0',0,'20'],[5,'Post All',3,'0',0,'21'],[6,'Manager',4,'0',1,'22']];
		$stH = stPrep("REPLACE INTO `groups` (`ID`,`name`,`privs`,`vCatIDs`,`upload`,`tnPrivs`) VALUES (?,?,?,?,?,?)");
		foreach($groups as $group) {
			stExec($stH,$group);
		}
	}
}

function initStyles($calName) { //init styles table
	global $defSaS;
	
	$theme = [];
	foreach($defSaS as $key => $value) { //get default styles
		if ($key[0] != '0') { //skip titles
			$theme[$key] = $value;
		}
	}
	$theme['THEME'] = $calName;
	$stH = dbQuery("SELECT `name`,`value` FROM `styles`"); //overwrite defaults with styles from DB
	while (list($name,$value) = $stH->fetch(PDO::FETCH_NUM)) {
		if ($value) { $theme[$name] = $value; }
	}
	dbQuery("DELETE FROM `styles`"); //empty styles table
	$stH = stPrep("INSERT INTO `styles` (`name`,`value`) VALUES (?,?)"); //save to DB
	foreach($theme as $key => $value) {
		stExec($stH,[$key,$value]);
	}
}

function checkSettings(&$dbSet) { //check, complete & save calendar settings
	global $defSet;
	
	foreach($defSet as $key => $value) {
		if (!isset($dbSet[$key])) { //set not-set settings to default value
			$dbSet[$key] = $value[0];
		}
	}
	foreach($dbSet as $key => $value) {
		if (!isset($defSet[$key])) { //delete redundant settings
			unset($dbSet[$key]);
		}
	}
	//if logged-in user templates empty, take public user
	if (!$dbSet['evtTemplGen2']) { $dbSet['evtTemplGen2'] = $dbSet['evtTemplGen']; }
	if (!$dbSet['evtTemplUpc2']) { $dbSet['evtTemplUpc2'] = $dbSet['evtTemplUpc']; }
	if (!$dbSet['evtTemplPop2']) { $dbSet['evtTemplPop2'] = $dbSet['evtTemplPop']; }
	saveSettings($dbSet); //save checked settings
}

function saveSettings(&$dbSet) { //save settings to calendar
	global $defSet;
	
	dbTransaction('begin');
	$stH = stPrep("DELETE FROM `settings`"); // empty table
	stExec($stH,null);
	$stH = stPrep("REPLACE INTO `settings` VALUES (?,?,?)"); //save settings
	foreach($dbSet as $key => $value) {
		stExec($stH,[$key,trim(strval($value)),$defSet[$key][1]]);
	}
	dbTransaction('commit');
}

function saveConfig() { //save LuxCal version and db credentials to lcconfig.php
	global $lcV, $dbType, $dbDef, $crHost, $crIpAd;

	$config = '<?php
/*
= LuxCal configuration =
*/
$lcV="'.$lcV.'"; //LuxCal version';
	if ($dbType == 'SQLite') { //SQLite
		global $dbDir;

		$config .= '
$dbType="SQLite"; //db type (MySQL or SQLite)
$dbDir="'.($dbDir ?: 'db/').'"; //db folder';
	} else { //MySQL
		global $dbHost, $dbUnam, $dbPwrd, $dbName;

		$config .= '
$dbType="MySQL"; //db type (MySQL or SQLite)
$dbHost="'.$dbHost.'"; //MySQL server
$dbUnam="'.$dbUnam.'"; //database username
$dbPwrd="'.$dbPwrd.'"; //database password
$dbName="'.$dbName.'"; //database name';
	}
	$config .= '
$dbDef="'.($dbDef ?: '').'"; //default calendar (name)
$crHost='.($crHost ?: 0).'; //0:local, 1:remote, 2:remote+IP address
$crIpAd="'.($crIpAd ?: '').'"; //IP address of remote cron service
?>';
	return file_put_contents('./lcconfig.php',$config);
}

function exportSqlFile($tables,$echo) { //export db tables to an SQL file
	global $dbType, $ax, $calID, $set, $lcV;
	
	//file header
	$sqlFile = "--
-- SQL DUMP ".date('Y.m.d @ H:i')."
-- Calendar: {$set['calendarTitle']}
-- Calendar ID: {$calID}
--
-- LuxCal version: {$lcV}
-- https://www.luxsoft.eu
--\n\n";
	if ($dbType == 'MySQL') { //MySQL database
		$sqlFile .= "SET SQL_MODE = \"NO_AUTO_VALUE_ON_ZERO\";\nSET time_zone = \"+00:00\";\n\n";
	}

	//backup tables
	usort($tables,function($a,$b) { return (substr($a,-6) == 'events') ? 1 : -1; }); //move events to the end
	foreach ($tables as $table) {
		if ($echo) { echo "{$ax['mdb_backup_table']} '{$table}' - "; }
		$sqlFile .= "-- ".str_repeat("-", 56)."\n\n--\n-- Table {$table}\n--\n\n";
		$sqlFile .= "DROP TABLE IF EXISTS `{$table}`;\n\n";
		$tableSql = getTableSql($table); //get SQL code to create table
		preg_match_all("%[\n|\(][\t\s]*[`'\"]?(ID|[a-z]\w+)[`'\"]?\s%",$tableSql,$colNames); //get column names
		$cNames = '`'.implode('`,`',$colNames[1]).'`';
		$sqlFile .= $tableSql.";\n\n";
		$stH = dbQuery("SELECT * FROM `{$table}`");
		$rows = 0;
		while($row = $stH->fetch(PDO::FETCH_NUM)) {
			if (($rows % 150) == 0) {
				$sqlFile .= "INSERT INTO `{$table}` ({$cNames}) VALUES\n";
			}
			$sqlFile .= "("; //start row
			foreach($row as $value) {
				$sqlFile .= isset($value) ? "'".str_replace(["'","\\"],["''",""],$value)."'," : "'',";
			}
			$sqlFile = rtrim($sqlFile,',').")"; //end row
			$rows++;
			$sqlFile .=	($rows % 150) != 0 ? ",\n" : ";\n";
		}
		$sqlFile = rtrim($sqlFile,",;\n").";\n\n"; //end of table
		$stH = null; //release statement handle
		if ($echo) { echo "{$ax['mdb_backup_done']} ({$rows} {$ax['mdb_records']})<br>\n"; }
	}
	return str_replace("\r\n","\n",$sqlFile);
}

function importSqlFile(&$sqlArray,$tbCreate) { //import db tables from an SQL file
	global $dbType;

	array_walk($sqlArray,function(&$v,$k) { $v = trim($v); }); //prepare
	$count = ['cat' => 0, 'eve' => 0, 'use' => 0, 'gro' => 0, 'set' => 0, 'sty' => 0]; //table counters
	$from = [' date ',' time ',' datetime ']; //column types in old versions
	$to = ['VARCHAR(10)','VARCHAR(8)','VARCHAR(19)'];
	//start restore
	for ($i = 0, $size = count($sqlArray); $i < $size; $i++) {
		if (strpos('~CREATE~INSERT',substr($sqlArray[$i],0,6)) and preg_match('~(events|categories|users|groups|settings|styles)[`"\s]~',$sqlArray[$i],$table)) { //find table name
			$query = preg_replace('~["`]?(?:\w{1,20}_)?'.$table[1].'["`]~',"`{$table[1]}`",$sqlArray[$i],1); //strip possible calID_
			if (substr($sqlArray[$i],0,6) == "CREATE") { //CREATE
				$stH = dbQuery("DROP TABLE IF EXISTS `{$table[1]}`;\n"); //drop table before creating
				if ($tbCreate) {
					while (substr($sqlArray[$i],-1) !== ';') { //flush CREATE query lines
						$i++;
					}
					createDbTable($table[1],0); //create standard table
				} else {
					while (substr($sqlArray[$i],-1) !== ';') { //build CREATE query
						$i++;
						$query .= str_replace($from,$to,$sqlArray[$i])."\n";
					}
					$stH = dbQuery($query); //create table
					if ($dbType == 'MySQL') { dbQuery("ALTER TABLE `{$table[1]}` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_bin;"); } //emoji and mb4 characters
				}
			} else { //INSERT
				while (substr($sqlArray[$i],-1) !== ';') { //build INSERT query
					$i++;
					$query .= $sqlArray[$i]."\n";
				}
				//execute query
				$query = preg_replace('~\\\\+["\']~',"''",$query); //modify escaped quotes
				$rowsStart = strpos($query,'VALUES') + 6;
				$count[substr($table[1],0,3)] += (preg_match_all('~\),(\r?\n|\s*\()~',$query,$m,0,$rowsStart) + 1); //increment INSERT counter with number of rows
				$stH = dbQuery($query);
			}
		}
	}
	return $count;
}

//
//Upgrade the current ($calID) database from 4.1 to the latest version
//

/*============ POPULATE FUNCTION ============*/
//===== versions 2.7 - 3.2 need <= PHP 5 =====
//======== version 4.1 needs <= PHP 7 ========

function populate($index) {
	switch ($index) {
	case 'events1': //4.1, 4.2, 4.3
		dbQuery("INSERT INTO `eventsX` (`ID`,`private`,`title`,`venue`,`text1`,`text2`,`text3`,`catID`,`userID`,`editor`,`approved`,`checked`,`notify`,`notRecip`,`sDate`,`eDate`,`xDates`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`,`status`) 
			SELECT `ID`,`private`,`title`,`venue`,`text1`,`text2`,`text3`,`catID`,`userID`,`editor`,`approved`,`checked`,`notify`,`notMail`,`sDate`,`eDate`,`xDates`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`,`status` FROM `events`");
		break;
	case 'events2': //4.4
		dbQuery("INSERT INTO `eventsX` (`ID`,`private`,`title`,`venue`,`text1`,`text2`,`text3`,`attach`,`catID`,`userID`,`editor`,`approved`,`checked`,`notify`,`notRecip`,`sDate`,`eDate`,`xDates`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`,`status`) 
			SELECT `ID`,`private`,`title`,`venue`,`text1`,`text2`,`text3`,`attach`,`catID`,`userID`,`editor`,`approved`,`checked`,`notify`,`notMail`,`sDate`,`eDate`,`xDates`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`,`status` FROM `events`");
		break;
	case 'events3': //4.5
		dbQuery("INSERT INTO `eventsX` (`ID`,`private`,`title`,`venue`,`text1`,`text2`,`text3`,`attach`,`catID`,`scatID`,`userID`,`editor`,`approved`,`checked`,`notify`,`notRecip`,`sDate`,`eDate`,`xDates`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`,`status`) 
			SELECT `ID`,`private`,`title`,`venue`,`text1`,`text2`,`text3`,`attach`,`catID`,`scatID`,`userID`,`editor`,`approved`,`checked`,`notify`,`notMail`,`sDate`,`eDate`,`xDates`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`,`status` FROM `events`");
		break;
	case 'events4': //4.6, 4.7, 5.1, 5.2
		dbQuery("INSERT INTO `eventsX` (`ID`,`type`,`private`,`title`,`venue`,`text1`,`text2`,`text3`,`attach`,`catID`,`scatID`,`userID`,`editor`,`approved`,`checked`,`notify`,`notRecip`,`sDate`,`eDate`,`xDates`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`,`status`) 
			SELECT `ID`,`type`,`private`,`title`,`venue`,`text1`,`text2`,`text3`,`attach`,`catID`,`scatID`,`userID`,`editor`,`approved`,`checked`,`notEml`,`notRecip`,`sDate`,`eDate`,`xDates`,`sTime`,`eTime`,`rType`,`rInterval`,`rPeriod`,`rMonth`,`rUntil`,`aDateTime`,`mDateTime`,`status` FROM `events`");
		break;
	case 'events99': //5.3
		dbQuery("INSERT INTO `eventsX` SELECT * FROM `events`");
		break;
	case 'users1': //4.1, 4.2, 4.3, 4.4, 4.5
		dbQuery("INSERT INTO `usersX` (`ID`,`name`,`password`,`tPassword`,`email`,`groupID`,`language`,`login0`,`login1`,`loginCnt`,`status`) 
			SELECT `ID`,`name`,`password`,`tPassword`,`email`,`groupID`,`language`,`login0`,`login1`,`loginCnt`,`status` FROM `users`");
		break;
	case 'users2': //4.6, 4.7, 5.1, 5.2
		dbQuery("INSERT INTO `usersX` (`ID`,`name`,`password`,`tPassword`,`email`,`phone`,`groupID`,`language`,`login0`,`login1`,`loginCnt`,`status`) 
			SELECT `ID`,`name`,`password`,`tPassword`,`email`,`phone`,`groupID`,`language`,`login0`,`login1`,`loginCnt`,`status` FROM `users`");
		break;
	case 'users99': //5.3
		dbQuery("INSERT INTO `usersX` SELECT * FROM `users`");
		break;
	case 'groups1': //4.1, 4.2
		dbQuery("INSERT INTO `groupsX` (`ID`,`name`,`privs`,`vCatIDs`,`color`,`status`) 
			SELECT `ID`,`name`,`privs`,`catIDs`,`color`,`status` FROM `groups`");
		break;
	case 'groups2': //4.3
		dbQuery("INSERT INTO `groupsX` (`ID`,`name`,`privs`,`vCatIDs`,`rEvents`,`mEvents`,`pEvents`,`color`,`status`) 
			SELECT `ID`,`name`,`privs`,`catIDs`,`rEvents`,`mEvents`,`pEvents`,`color`,`status` FROM `groups`");
		break;
	case 'groups3': //4.4
		dbQuery("INSERT INTO `groupsX` (`ID`,`name`,`privs`,`vCatIDs`,`rEvents`,`mEvents`,`pEvents`,`upload`,`color`,`status`) 
			SELECT `ID`,`name`,`privs`,`catIDs`,`rEvents`,`mEvents`,`pEvents`,`upload`,`color`,`status` FROM `groups`");
		break;
	case 'groups4': //4.5, 4.6
		dbQuery("INSERT INTO `groupsX` (`ID`,`name`,`privs`,`vCatIDs`,`eCatIDs`,`rEvents`,`mEvents`,`pEvents`,`upload`,`color`,`status`) 
			SELECT `ID`,`name`,`privs`,`vcatIDs`,`ecatIDs`,`rEvents`,`mEvents`,`pEvents`,`upload`,`color`,`status` FROM `groups`");
		break;
	case 'groups5': //4.7, 5.1, 5.2
		dbQuery("INSERT INTO `groupsX` (`ID`,`name`,`privs`,`vCatIDs`,`eCatIDs`,`rEvents`,`mEvents`,`pEvents`,`upload`,`tnPrivs`,`color`,`status`) 
			SELECT `ID`,`name`,`privs`,`vcatIDs`,`ecatIDs`,`rEvents`,`mEvents`,`pEvents`,`upload`,`tnPrivs`,`color`,`status` FROM `groups`");
		break;
	case 'groups99': //5.3
		dbQuery("INSERT INTO `groupsX` SELECT * FROM `groups`");
		break;
	case 'categories1': //4.1
		dbQuery("INSERT INTO `categoriesX` (`ID`,`name`,`sequence`,`repeat`,`approve`,`color`,`bgColor`,`checkBx`,`checkLb`,`checkMk`,`subCats`,`status`) 
			SELECT `ID`,`name`,`sequence`,`repeat`,`approve`,`color`,`bgColor`,`checkBx`,`checkLb`,SUBSTR(`checkMk`,1,8),'[]',`status` FROM `categories`");
		break;
	case 'categories2': //4.2
		dbQuery("INSERT INTO `categoriesX` (`ID`,`name`,`sequence`,`repeat`,`approve`,`dayColor`,`color`,`bgColor`,`checkBx`,`checkLb`,`checkMk`,`subCats`,`status`) 
			SELECT `ID`,`name`,`sequence`,`repeat`,`approve`,`dayColor`,`color`,`bgColor`,`checkBx`,`checkLb`,SUBSTR(`checkMk`,1,8),'[]',`status` FROM `categories`");
		break;
	case 'categories3': //4.3, 4.4
		dbQuery("INSERT INTO `categoriesX` (`ID`,`name`,`sequence`,`repeat`,`noverlap`,`olErrMsg`,`defSlot`,`approve`,`dayColor`,`color`,`bgColor`,`checkBx`,`checkLb`,`checkMk`,`subCats`,`status`)
			SELECT `ID`,`name`,`sequence`,`repeat`,`noverlap`,`olErrMsg`,`defSlot`,`approve`,`dayColor`,`color`,`bgColor`,`checkBx`,`checkLb`,SUBSTR(`checkMk`,1,8),'[]',`status` FROM `categories`");
		break;
	case 'categories4': //4.5, 4.6
		$stHdest = stPrep("INSERT INTO `categoriesX` VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
		$stH = dbQuery("SELECT * FROM `categories`"); //get old subcats
		while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
			$subCats = '[["'.$row['subName1'].'","'.$row['subColor1'].'","'.$row['subBgrnd1'].'"],["'.$row['subName2'].'","'.$row['subColor2'].'","'.$row['subBgrnd2'].'"],["'.$row['subName3'].'","'.$row['subColor3'].'","'.$row['subBgrnd3'].'"],["'.$row['subName4'].'","'.$row['subColor4'].'","'.$row['subBgrnd4'].'"]]';
			$subCats = preg_replace('%,?\["","[^,]*","[^,]*"\],?%','',$subCats);
			stExec($stHdest,[$row['ID'],$row['name'],$row['symbol'],$row['sequence'],$row['repeat'],$row['noverlap'],0,$row['olErrMsg'],$row['defSlot'],0,$row['approve'],$row['dayColor'],$row['color'],$row['bgColor'],$row['checkBx'],$row['checkLb'],$row['checkMk'],$subCats,'',$row['urlLink'],$row['status']]);
		}
		break;
	case 'categories5': //4.7
		$stHdest = stPrep("INSERT INTO `categoriesX` VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
		$stH = dbQuery("SELECT * FROM `categories`"); //get old subcats
		while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
			$subCats = '[["'.$row['subName1'].'","'.$row['subColor1'].'","'.$row['subBgrnd1'].'"],["'.$row['subName2'].'","'.$row['subColor2'].'","'.$row['subBgrnd2'].'"],["'.$row['subName3'].'","'.$row['subColor3'].'","'.$row['subBgrnd3'].'"],["'.$row['subName4'].'","'.$row['subColor4'].'","'.$row['subBgrnd4'].'"]]';
			$subCats = preg_replace('%,?\["","[^,]*","[^,]*"\],?%','',$subCats);
			stExec($stHdest,[$row['ID'],$row['name'],$row['symbol'],$row['sequence'],$row['repeat'],$row['noverlap'],$row['olapGap'],$row['olErrMsg'],$row['defSlot'],$row['fixSlot'],$row['approve'],$row['dayColor'],$row['color'],$row['bgColor'],$row['checkBx'],$row['checkLb'],$row['checkMk'],$subCats,'',$row['urlLink'],$row['status']]);
		}
		break;
	case 'categories6': //5.1, 5.2
		dbQuery("INSERT INTO `categoriesX` (`ID`,`name`,`symbol`,`sequence`,`repeat`,`noverlap`,`olapGap`,`olErrMsg`,`defSlot`,`fixSlot`,`approve`,`dayColor`,`color`,`bgColor`,`checkBx`,`checkLb`,`checkMk`,`subCats`,`urlLink`,`status`)
			SELECT `ID`,`name`,`symbol`,`sequence`,`repeat`,`noverlap`,`olapGap`,`olErrMsg`,`defSlot`,`fixSlot`,`approve`,`dayColor`,`color`,`bgColor`,`checkBx`,`checkLb`,SUBSTR(`checkMk`,1,8),`subCats`,`urlLink`,`status` FROM `categories`");
		break;
	case 'categories99': //5.3
		dbQuery("INSERT INTO `categoriesX` SELECT * FROM `categories`");
		break;
	case 'settings99': //4.1+
		dbQuery("INSERT INTO `settingsX` SELECT * FROM `settings`");
		break;
	case 'styles0': //4.1 - 4.4
		createDbTable("styles",1); //table not present
		break;
	}
}
/*========= END OF POPULATE FUNCTIONS =========*/

function upgradeDb() {
	global $dbType, $calID, $set;

	$dbTables = ['users','groups','categories','events','settings']; //db tables (styles are populated at the end)
	
	//create temporary tables with new schema
	foreach ($dbTables as $dbTable) {
		createDbTable("{$dbTable}X",1);
	}

	/* === tables version-processing === */
	do {
		//test if version < 3.1
		if (!dbQuery("SELECT `approve` FROM `categories` LIMIT 1",0)) { //column 'approve' not present - version 2.7
			$lcVUpg = '2.7';
			echo "Your calendar version $lcVUpg is not supported anymore. For help contact LuxSoft.";
			break;
		}
		//test if version = 3.1
		if (dbQuery("SELECT `a_date` FROM `events` LIMIT 1",0)) { //column 'a_date' IS present - version 3.1
			$lcVUpg = '3.1';
			echo "Your calendar version $lcVUpg is not supported anymore. For help contact LuxSoft.";
			break;
		}
		//test if version = 3.2
		if (!dbQuery("SELECT `ID` FROM `events` LIMIT 1",0)) { //column 'ID' not present - version 3.2
			$lcVUpg = '3.2';
			echo "Your calendar version $lcVUpg is not supported anymore. For help contact LuxSoft.";
			break;
		}
		//test if version = 4.1
		if (!dbQuery("SELECT `dayColor` FROM `categories` LIMIT 1",0)) { //column 'dayColor' not present - version 4.1
			$lcVUpg = '4.1';
			$insert = 'events1,users1,groups1,categories1,settings99,styles0';
			break;
		}
		//test if version = 4.2
		if (!dbQuery("SELECT `noverlap` FROM `categories` LIMIT 1",0)) { //column 'overlay' not present - version 4.2
			$lcVUpg = '4.2';
			$insert = 'events1,users1,groups1,categories2,settings99,styles0';
			break;
		}
		//test if version = 4.3
		if (!dbQuery("SELECT `attach` FROM `events` LIMIT 1",0)) { //column 'attach' not present - version 4.3
			$lcVUpg = '4.3';
			$insert = 'events1,users1,groups2,categories3,settings99,styles0';
			break;
		}
		//test if version = 4.4
		if (!dbQuery("SELECT `vCatIDs` FROM `groups` LIMIT 1",0)) { //column 'vCatIDs' not present - version 4.4
			$lcVUpg = '4.4';
			$insert = 'events2,users1,groups3,categories3,settings99,styles0';
			break;
		}
		//test if version = 4.5
		if (!dbQuery("SELECT `notRecip` FROM `events` LIMIT 1",0)) { //column 'notRecip' not present - version 4.5
			$lcVUpg = '4.5';
			$insert = 'events3,users1,groups4,categories4,settings99';
			break;
		}
		//test if version = 4.6
		if (!dbQuery("SELECT `olapGap` FROM `categories` LIMIT 1",0)) { //column 'olapGap' not present - version 4.6
			$lcVUpg = '4.6';
			$insert = 'events4,users2,groups4,categories4,settings99';
			break;
		}
		//test if version = 4.7
		if (!dbQuery("SELECT `subCats` FROM `categories` LIMIT 1",0)) { //column 'subCats' not present - version 4.7
			$lcVUpg = '4.7';
			$insert = 'events4,users2,groups5,categories5,settings99';
			break;
		}
		//test if version = 5.1
		if (!dbQuery("SELECT `token` FROM `users` LIMIT 1",0)) { //column 'token' not present - version 5.1
			$lcVUpg = '5.1';
			$insert = 'events4,users2,groups5,categories6,settings99';
			break;
		}
		//test if version = 5.2
		if (!dbQuery("SELECT `expDate` FROM `users` LIMIT 1",0)) { //column 'expDate' not present - version 5.2
			$lcVUpg = '5.2';
			$insert = 'events4,users2,groups5,categories6,settings99';
			break;
		}
		//version = current version (no changes)
		$lcVUpg = '5.3';
		$insert = 'events99,users99,groups99,categories99,settings99';
	} while (0); //end of: process calendar $calID

	/* === TABLES PRE-PROCESSING === */
	
	if ($lcVUpg <= '5.2') { //replace NULL values by '' when possible
		$nullCols = [
			'events' => ['text2', 'text3', 'attach', 'editor', 'checked', 'notRecip', 'notMail', 'xDates'], //notMail < V4.6
			'categories' => ['symbol', 'olErrMsg', 'color', 'bgColor', 'urlLink'],
			'users' => ['token', 'temp_password', 'tPassword', 'email', 'phone', 'msingID'],
			'groups' => ['color'],
			];

		foreach ($nullCols as $table => $columns) {
			foreach ($columns as $column) {
				if (dbQuery("SELECT `$column` FROM `$table` LIMIT 1",0)) { //if $column exists
					dbQuery("UPDATE `$table` SET `$column` = '' WHERE `$column` IS NULL");
				}
			}
		}
	}

	/* === END OF PRE-PROCESSING === */

	//populate X-tables
	foreach (explode(',',$insert) as $tabxx) {
		populate($tabxx);
	}

	//compact tables
	if ($dbType == 'SQLite') { //SQLite db
		$stH = dbQuery("VACUUM");
	} else { //MySQL db
		$stH = dbQuery('OPTIMIZE TABLE `'.implode('`,`',getTables()).'`');
	}

	/* === TABLES POST-PROCESSING === */

//< 4.1
	//events.aDateTime/mDateTime: pad to yyyy-mm-dd 00:00
	$stH = dbQuery("SELECT `aDateTime` FROM `eventsX` LIMIT 1");
	if ($row = $stH->fetch(PDO::FETCH_NUM)) { //column 'aDateTime' exists
		if (strlen($row[0]) < 16) {
			if ($dbType == 'SQLite') { //SQLite / MySQL incompatibilities
				dbQuery("UPDATE `eventsX` SET `aDateTime` = substr(`aDateTime`,1,10)||' 00:00',`mDateTime` = substr(`mDateTime`,1,10)||' 00:00'");
			} else {
				dbQuery("UPDATE `eventsX` SET `aDateTime` = CONCAT(substr(`aDateTime`,1,10),' 00:00'),`mDateTime` = CONCAT(substr(`mDateTime`,1,10),' 00:00')");
			}
		}
	}
//< 4.2
	//groups.ID and users.groupID: renumber ID starting from 1
	$stH = dbQuery("SELECT * FROM `groupsX` WHERE `ID` = 0");
	if ($row = $stH->fetch(PDO::FETCH_NUM)) { //column 'ID' = 0 exists - renumber
		$stH = dbQuery("SELECT `ID` FROM `groupsX` ORDER BY `ID` DESC"); 
		while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
			dbQuery("UPDATE `groupsX` SET `ID` = `ID` + 1 WHERE `ID` = {$row['ID']}"); //must be done in reverse order
		}
		dbQuery("UPDATE `usersX` SET `groupID` = `groupID` + 1");
	}
//<4.2
	//events.checked: ;yyyy-mm-dda -> ;yyyy-mm-dd and drop ;yyyy-mm-ddb
	$stH = dbQuery("SELECT `ID`,`checked` FROM `eventsX` WHERE `checked` LIKE '%a%'");
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		$chBoxed = preg_replace(['~;\d\d\d\d-\d\d-\d\db~','~(;\d\d\d\d-\d\d-\d\d)a~'],['','$1'],$row['checked']);
		dbQuery("UPDATE `eventsX` SET `checked` = '{$chBoxed}' WHERE `ID` = {$row['ID']}");
	}
//< 4.7
	//settings.viewsPublic/viewsLogged: add ",11" (new Gantt chart view V4.7.7)
	$stH = dbQuery("SELECT `value` FROM `settingsX` WHERE `name` = 'viewsLogged'");
	if ($row = $stH->fetch(PDO::FETCH_NUM)) {
		if (!strpos($row[0],',11')) { //Gantt chart not present
			if ($dbType == 'SQLite') { //SQLite - solve MySQL incompatibilities
				dbQuery("UPDATE `settingsX` SET `value` = `value`||',11' WHERE `name` = 'viewsPublic' OR `name` = 'viewsLogged'");
			} else {
				dbQuery("UPDATE `settingsX` SET `value` = CONCAT(`value`,',11') WHERE `name` = 'viewsPublic' OR `name` = 'viewsLogged'");
			}
		}
	}
//< 4.7.3
	//settings.chgEmailList: name has changed to chgRecipList (more than just email addresses)
	dbQuery("UPDATE `settingsX` SET `name` = 'chgRecipList' WHERE `name` = 'chgEmailList'");
//< 4.7.7
	//settings.spMiniCal/spImages/spInfoArea: don't surprise existing calendars with a side panel (V4.7.7)
	$stH = dbQuery("SELECT `value` FROM `settingsX` WHERE `name` = 'spMiniCal'");
	if (!$row = $stH->fetch(PDO::FETCH_NUM)) { //spMiniCal not existing
		$stH = stPrep("INSERT INTO `settingsX` (`name`,`value`) VALUES (?,?)");
		foreach(['spMiniCal','spImages','spInfoArea'] as $name) {
			stExec($stH,[$name,'']);
		}
	} else { //spMiniCal existing (0 -> '', 1-> '2,4,6')
		dbQuery("UPDATE `settingsX` SET `value` = '' WHERE (`name` = 'spMiniCal' OR `name` = 'spImages' OR `name` = 'spInfoArea') AND `value` = '0'");
		dbQuery("UPDATE `settingsX` SET `value` = '2,4,6' WHERE (`name` = 'spMiniCal' OR `name` = 'spImages' OR `name` = 'spInfoArea') AND `value` = '1'");
	}
//< 5.0
	//correct groupIDs admin (3 -> 2) and read-access (2 -> 3)
	$stH = dbQuery("SELECT `ID`,`groupID` FROM `usersX` WHERE `ID` = 2 AND `groupID` = 3",0); //admin in group 3
	if ($row = $stH->fetch(PDO::FETCH_NUM)) {
		dbQuery("UPDATE `groupsX` SET `ID` = 100 WHERE `ID` = 2"); //park read-only
		dbQuery("UPDATE `usersX` SET `groupID` = 100 WHERE `groupID` = 2"); //idem
		dbQuery("UPDATE `groupsX` SET `ID` = 2 WHERE `ID` = 3"); //set admin to 2
		dbQuery("UPDATE `usersX` SET `groupID` = 2 WHERE `groupID` = 3"); //idem
		dbQuery("UPDATE `groupsX` SET `ID` = 3 WHERE `ID` = 100"); //set parked to 3
		dbQuery("UPDATE `usersX` SET `groupID` = 3 WHERE `groupID` = 100"); //idem
	}
//< 5.2
	//upgrade "sml" email links
	$pattern = "~<a\s.{28,34}sml\('([^']+)','([^']+)','([^']+)','\[cd\] - ([^']+)'\)[^<>]+>([^<>]+)</a>~";
	$replacement = "<a class='link' href='mailto:$1@$2.$3?subject=$4'>$5</a>";
	$stH = dbQuery("SELECT `ID`,`text1`,`text2`,`text3` FROM `eventsX` WHERE `text1` LIKE '%sml(%' OR `text2` LIKE '%sml(%' OR `text3` LIKE '%sml(%'");
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		if (strpos($row['text1'],'sml(') !== false) {
			$newLink = preg_replace($pattern,$replacement,$row['text1']);
			dbQuery("UPDATE `eventsX` SET `text1` = \"{$newLink}\" WHERE `ID` = {$row['ID']}");
		}
		if (strpos($row['text2'],'sml(') !== false) {
			$newLink = preg_replace($pattern,$replacement,$row['text2']);
			dbQuery("UPDATE `eventsX` SET `text2` = \"{$newLink}\" WHERE `ID` = {$row['ID']}");
		}
		if (strpos($row['text3'],'sml(') !== false) {
			$newLink = preg_replace($pattern,$replacement,$row['text3']);
			dbQuery("UPDATE `eventsX` SET `text3` = \"{$newLink}\" WHERE `ID` = {$row['ID']}");
		}
	}
//< 5.2.3
	//events.checked: ;yyyy-mm-dd change to ;offset
	$stH = dbQuery("SELECT `ID`,`sDate`,`checked` FROM `eventsX` WHERE `checked` LIKE '%-%'"); //abs. dates
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		$cDarr = explode(';',ltrim($row['checked'],';')); //array with all 'checked' dates
		$cOffset = '';
		foreach($cDarr as $cDate) {
			$cOffset .= ';'.strval(round((strtotime($cDate) - strtotime($row['sDate'])) / 86400)); //days
		}
		dbQuery("UPDATE `eventsX` SET `checked` = '{$cOffset}' WHERE `ID` = {$row['ID']}");
	}
//< 5.2.3
	//events.xDates: ;yyyy-mm-dd change to ;offset
	$stH = dbQuery("SELECT `ID`,`sDate`,`xDates` FROM `eventsX` WHERE `xDates` LIKE '%-%'"); //abs. dates
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		$xDarr = explode(';',ltrim($row['xDates'],';')); //array with all excluded dates
		$xOffset = '';
		foreach($xDarr as $xDate) {
			$xOffset .= ';'.strval(round((strtotime($xDate) - strtotime($row['sDate'])) / 86400)); //days
		}
		dbQuery("UPDATE `eventsX` SET `xDates` = '{$xOffset}' WHERE `ID` = {$row['ID']}");
	}
// always
	//blank out `language` for the Public User to force the default language from the settings
	dbQuery("UPDATE `usersX` SET `language` = '' WHERE `ID` = 1");
// always 
	//settings.calendarUrl: set calendar URL to the correct value
	$calURL = calBaseUrl().'?cal='.$calID;
	dbQuery("UPDATE `settingsX` SET `value` = '$calURL' WHERE `name` = 'calendarUrl'");
	
	/* === END OF POST-PROCESSING === */

	$stH = null; //release statement handle

	//drop original tables and rename new upgraded tables
	foreach ($dbTables as $dbTable) {
		dbQuery("DROP TABLE `{$dbTable}`");
		dbQuery("ALTER TABLE `{$dbTable}X` RENAME TO `{$dbTable}`");
	}

	$set = getSettings(); //get settings
	checkSettings($set); //check, complete & save settings

	initStyles($set['calendarTitle']); //ensure and store consistent styles

	return $lcVUpg;
}
?>