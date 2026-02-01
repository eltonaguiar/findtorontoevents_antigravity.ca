<?php
/*
= View notification message log page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$sentT = $_POST["sentT"] ?? ""; //search text
$sentD = isset($_POST['sentD']) ? DDtoID($_POST['sentD']) : '';

//display header
echo "<div class='subHead'>
<form id='selectD' name='selectD' action='index.php' method='post'>
".ucfirst($xx['msl_date'])."&nbsp;
<input class='date' type='text' id='sentD' name='sentD' value='".IDtoDD($sentD)."'>
<span class='dtPick noPrint' title=\"{$xx['chg_select_date']}\" onclick='dPicker(1,`selectD`,`sentD`); return false;'>&#x1F4C5;</span>
&emsp;".ucfirst($xx['msl_text'])."&nbsp;
<input type='text' name='sentT' id='sentT' value=\"{$sentT}\" maxlength='30' size='20'>
&emsp;<button type='submit' name='search' value='y'>{$xx['msl_search']}</button>\n
&emsp;(?: 1 char. *: n chars.)
";
echo "</form>
</div>\n";

//display message log
$logPath = "./logs/{$calID}~messages.log";
if (is_file($logPath)) {
	$logArr = file($logPath, FILE_IGNORE_NEW_LINES);
	if ($sentD) {
		$sentD[4] = '.';
		$sentD[7] = '.';
	}
	if ($sentT) {
		$regex = preg_replace(array('~\.~','~\*~'),array("[\w\s']","[\w\s']*?"),$sentT);
	}
}
echo "<div".($winXS ? '' : " class='scrollBox sBoxLg'").">\n";
echo "<fieldset class='log'>\n<legend>{$xx['msl_sent_msgs']}</legend>\n";

$hits = 0; //init
if (!empty($logArr)) {
	foreach($logArr as $logLine) {
		if ($sentD and !($sentD == substr($logLine,0,10))) { continue; }
		if ($sentT and !preg_match("~($regex)~i",substr($logLine,20))) { continue; }
		if ($sentT) {
			$logLine = preg_replace("~($regex)~i","<em class='red'>$1</em>",$logLine,-1,$count);
		}
		$lineArr = explode('|',$logLine);
		foreach($lineArr as $k => $part) {
			if ($k == 0) {
				echo "<div><em class='sentDT'> ".substr($part,0,16)." </em>:".substr($part,16)."</div>\n";
			} else {
				$part = str_replace('~E~',"&emsp;<em class='hired'>{$xx['msl_errors']}</em>",$part);
				echo "<p>• {$part}</p>\n";
			}
			$hits++;
		}
	}
}
if (!$hits) {
	echo "<br><div class='floatC'>{$xx['msl_no_logs_found']}</div><br>\n";
}
echo "</fieldset>";
echo "</div>\n<br>";
?>
