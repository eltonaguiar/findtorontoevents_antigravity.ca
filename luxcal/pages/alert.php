<?php
/*
= LuxCal alert page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

$bButton = ''; //init

//get calendar ID and connect to db
$calID = isset($_COOKIE['LXCcid']) ? unserialize($_COOKIE['LXCcid']) : $dbDef;
$dbH = dbConnect($calID);

//get settings
$set = getSettings();
 
//get language file
$lang = strtolower($set['language']);
require "./lang/ui-{$lang}.php";

if (!empty($winXP)) { //small window
	$rButton = "<button type='button' onclick='javascript:self.close();'>{$xx['evt_close']}</button>\n"; //close button
} else {
	$rButton = "<button type='button' onclick='window.location = window.location.href.split(`?`)[0];'>{$xx['restart']}</button>\n"; //restart button
	if ($set['backLinkUrl']) {
		$bButton = "<button type='button' title='{$xx['hdr_button_back']}' onclick='window.location.href=`{$set['backLinkUrl']}`;'>{$xx['back']}</button>\n"; //back button
	}
}
if (strpos($alert,'#') !== false) { //populate alert message
	preg_match_all("~#\d~",$alert,$matches);
	foreach($matches[0] as $v) {
		$alert = str_replace($v,$xx["alt_message{$v}"],$alert);
	}
}
?>
<!DOCTYPE html>
<html lang="<?php echo $isocode ?>">
<head>
<meta charset="utf-8">
<title><?=$set['calendarTitle']?></title>
<meta name="description" content="LuxCal web calendar - a LuxSoft product">
<meta name="application-name" content="LuxCal">
<meta name="author" content="Roel Buining">
<meta name="robots" content="nofollow">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="lcal.png">
<link rel="stylesheet" type="text/css" href="css/css.php">
</head>

<body>
<div class='barTop'>
LuxCal Alert Message
</div>
<div class='contentH scroll'>
<div class='alert'>
<?php
echo "<span>{$alert}";
echo "<br><br>{$rButton}\n";
if ($bButton) { 
	echo "&emsp;{$bButton}\n";
}
echo "</span>\n";
?>
</div>
</div>
<footer>
<?php
echo "<a href='https://www.luxsoft.eu?V".LCV."' target='_blank'>powered by <span class='footLS'>LuxSoft</span></a>";
if (!empty($note)) { echo "<span class='note'>== {$note} ==</span>"; }
?>
</footer>
</body>
</html>

