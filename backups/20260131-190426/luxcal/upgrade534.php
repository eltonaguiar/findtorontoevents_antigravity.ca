<?php
/*
LuxCal Upgrade script - MySQL database version

!!!!!!! AFTER UPLOADING A NEW LUXCAL VERSION TO YOUR SERVER, THIS !!!!!!!
!!!!!!! SCRIPT WILL RUN AUTOMATICALLY WHEN STARTING THE CALENDAR. !!!!!!!
!!!!!!! THIS SCRIPT MAY BE LAUNCHED VIA YOUR BROWSER AT ANY TIME. !!!!!!!

© Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
*/

if (isset($_GET['phpinfo'])) { phpinfo(); exit; }

//sanity check
if (version_compare(PHP_VERSION,'5.3.0') < 0) { //check PHP version
	exit('<br><br><b>PHP version too low</b><br><br>You need version 5.3 or higher<br>Your current version is: '.PHP_VERSION);
}
foreach ($_REQUEST as $key => $value) { if (is_string($value)) $_REQUEST[$key] = htmlspecialchars(strip_tags(trim($value)),ENT_QUOTES,'UTF-8'); }

//set error reporting
error_reporting(E_ALL); //errors and notices
ini_set('display_errors',1);
ini_set('log_errors',1);

//get configuration data
date_default_timezone_set(@date_default_timezone_get()); //set time zone
if (file_exists('./lcconfig.php')) {
	include './lcconfig.php';
}
$lcVcurr = !empty($lcV) ? $lcV : '0'; //current LuxCal version
if (empty($dbType)) { $dbType = 'MySQL'; } //set database type
$lcV = implode('.',str_split(substr(basename(__FILE__),7,-4))).'M'; //set new LuxCal version

//get calendar tools
require './common/toolbox.php'; //general toolbox
require './common/toolboxd.php'; //database tools
require './common/toolboxx.php'; //admin tools
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>LuxCal Event Calendar - Upgrade</title>
<meta name="description" content="LuxCal web calendar - a LuxSoft product">
<meta name="author" content="Roel Buining">
<meta name="robots" content="nofollow">
<link rel="icon" href="lcal.png" type="image/png">
<style type="text/css">
* { padding:0; margin:0;}
body {font:14px arial, sans-serif; background:#E0E0E0; color:#2B3856; cursor:default;}
a {text-decoration:none; cursor:pointer;}
header {display:block; margin:6px 0; padding:0 1%; font-size:1.2em; font-weight:bold;}
h4 {margin:6px 0; font-size:1.2em;}
h5 {margin:2px 0; font-size:1.1em;}
button {font-size:0.9em; padding:0 4px; margin:0 15px; cursor:pointer;}
ul {margin:0 20px;}
li {margin-top:5px;}
.floatR {float:right;}
.floatL {float:left;}
div.centerBox {display:table; margin:auto;}
div.niceBox {width:500px; border:1px solid #808080; background:#FFFFFF; padding:5px; text-align:justify;}
div.infoBox {width:500px; border:1px solid #008080; color:#008080; background:#FFFFFF; padding:5px; text-align:justify;}
div.bLine {position:absolute; left:0; bottom:50px; width:98%; text-align:center;}
.hilite {background:#F0A070;}
.lolite {background:#70C070;}
.mark {color:#AA0000;}
.center {text-align:center;}
.title {font:bold 1.4em arial, sans-serif;}
div.topBar {
	position:absolute; top:34px; left:0; right:0;
	padding:0 1%;
	background:#AAAAFF;
	text-align:center;
	border:1px #808080;
	border-style:solid none;
	line-height:20px;
	vertical-align:middle;
}
div.content {
	position:absolute; left:0; top:110px; right:0px; bottom:90px;
	padding:0 20px;
	overflow:auto;
}
div.endBar {
	position:absolute; left:0; right:0; bottom:10px;
	padding:0 1%;
	background:#AAAAFF;
	text-align:right;
	border:1px #808080;
	border-style:solid none;
	font-size:0.8em;
}
div.endBar span {font:italic bold 1.1em arial,sans-serif; color:#990000;}
</style>
<script type="text/javascript">
function showMe(elID) {
    var el = document.getElementById(elID);
    el.scrollIntoView(true);
}
</script>
</head>

<body onLoad="showMe('endofpage');">
<header>LuxCal Event Calendar</header>
<?php
//init
$dbH = null; //disconnect from db
$report = array();

echo "<div class='topBar'><span class='floatL'>LuxCal: {$lcV}</span><span class='floatR'>Your PHP version: ".PHP_VERSION."</span><span class='title'>Calendar Upgrade to Version {$lcV}</span></div>\n";
echo "<div class='content'>\n";

do { //start of processing
	if (empty($dbHost) OR empty($dbUnam) OR empty($dbName)) { //no db credentials found
		$error = "No database credentials found in calendar root (file: lcconfig.php)"; break;
	}
	if (!isset($dbDef)) { //before v4.1
		if (!isset($dbPfix)) { //config data not complete
			$error = "Not all configuration data found in calendar root (file: lcconfig.php)"; break;
		}
		$dbDef = $dbPfix; //set default calendar
	}
	$calID = $dbDef = rtrim($dbDef,'_'); //remove possible separator "_"

	$report[] = "Configuration file 'lcconfig.php' found. Configuration data loaded:";
	$report[] = "- Database name: {$dbName}";
	$report[] = "- Default calendar: {$dbDef}";

	//connect to database
	if (!$dbH = dbConnect('void',0)) {
		$error = "Could not connect to database"; break;
	}

	//check/update table prefixes of old versions
	$stH = dbQuery("SHOW TABLES LIKE '%settings'");
	while ($row = $stH->fetch(PDO::FETCH_NUM)) {
		$matches = array();
		if (preg_match('~^([a-z\d-]{0,20})settings$~',$row[0],$matches)) { //no prefix or no separator (_)
			$fromPf = empty($matches[1]) ? '' : $matches[1];
			$toPf = empty($matches[1]) ? 'mycal' : $matches[1]; //no prefix: 'mycal'
			$q = "RENAME TABLE
			{$fromPf}events     TO {$toPf}_events,
			{$fromPf}categories TO {$toPf}_categories,
			{$fromPf}users      TO {$toPf}_users,
			{$fromPf}settings   TO {$toPf}_settings
			";
			$stH2 = dbQuery($q);
			if ($stH2) { $report[] = "Tables '{$fromPf}xxxxxx' renamed to '{$toPf}_xxxxxx'"; }
			$calID = $dbDef = $toPf;
		}
	}
	
	//get settings of default calendar and set time zone
	$dbSet = getSettings();
	if ($dbSet === false) {
		$error = "Could not retrieve calendar settings from the database"; break;
	}
	date_default_timezone_set($dbSet['timeZone']);
	$report[] = "Default calendar settings retrieved and timezone set to:";
	$report[] = "- ".$dbSet['timeZone'];

	/* ===== LuxCal 3.1.0 drop table `x_sessdata` (not used anymore) ===== */
	dbQuery("DROP TABLE IF EXISTS `x_sessdata`",0);
		
	//get installed calendars
	$allCals = getCals();
	if (empty($allCals)) {
		$error = "No calendars found in the database."; break;
	}
	$report[] = "Calendar(s) found in the database:";
	foreach($allCals as $cID=>$title) {
		$report[] = '- '.$cID.' = '.$title.($cID == $dbDef ? " <span class='mark'>(default)</span>" : '');
	}

	/*============================= start upgrading ==============================*/

	foreach($allCals as $cID=>$title) { //process each installed calendar
		$report[] = "Processing calendar: {$cID} - {$title}";
		$calID = $cID; //set current calendar
		
		//upgrade db tables to the latest schema, while preserving data
		$fromV = upgradeDb();
		$report[] = "- V{$fromV} database tables and structures verified/updated.";

		//upgrade admin settings
		$dbSet = getSettings();
		checkSettings($dbSet); //check, complete & save settings
		$report[] = "- Administrator settings verified/updated";
	}
	
	//Save LuxCal version and config data
	if (!saveConfig()) {
		$error = "Unable to write the file lcconfig.php to calendar root. Check file permissions (should be 755)."; break;
	}
	$report[] = "Configuration file 'lcconfig.php' updated and saved to root folder.";
} while (0); //end of processing

echo "<div class='centerBox'><br>\n";
if (empty($error)) {
	echo "<h5>Start of Upgrade</h5>\n";
	echo "<ul>\n";
	foreach($report as $text) {	echo $text[0] == '-' ? "<br>{$text}\n" : "<li>{$text}\n"; } //show each step
	echo "</ul>\n";
	echo "<h5>End of Upgrade</h5>\n";
	echo "<br>\n";
	echo "<div class='niceBox'>\n";
	echo "The calendar has been upgraded to version {$lcV}.\n";
	echo "<p>Make a back-up copy of the configuration file 'lcconfig.php'.</p><br>\n";
	echo "<div class='center'>\n";
	echo "<button type='button' onclick=\"window.location.href='index.php'\">Start Calendar</button>\n";
	echo "</div>\n";
	echo "</div>\n";
} else {
	echo "<div class='niceBox'>\n";
	echo "<h5>The following error occurred:</h5>\n";
	echo "<div class='hilite'>- {$error}</div><br>\n";
	echo "The calendar upgrade to version {$lcV} has been aborted.<br>\n";
	echo "Correct the error and restart the upgrade script.\n";
	echo "</div>\n";
}
if (empty($error) and $lcVcurr < '4.7.7L' and is_file('relnotes.html')) {
	echo "<br><div class='infoBox'>\n";
	echo file_get_contents('relnotes.html')."<br>\n";
	echo "</div>\n";
}
echo "<div id='endofpage'>&nbsp;</div>\n";
echo "</div>\n";
?>
</div>
<br>
<div class="bLine mark"><h4>AFTER USE MAKE THE FILE <?=basename(__FILE__);?> INACCESSIBLE OR REMOVE IT FROM THE SERVER !</h4></div>
<div class="endBar">design <?=date('Y');?> - powered by <a href="http://www.luxsoft.eu"><span>LuxSoft</span></a></div>
<br>&nbsp;
</body>
</html>
