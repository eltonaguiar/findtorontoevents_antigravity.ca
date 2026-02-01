<?php
/*= file downloader script =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3


this script tells the http server and client browser that the requested 
file is coming back as an application attachment to be saved as a file.
*/


//sanity checks
if (empty($_GET['ftd'])) { exit('no file name'); }
$fName = $_GET['ftd']; //file to download
if (strpos($fName,'..') !== false or strpos('./logs./atta./file',substr($fName,0,6)) === false) { exit('no way!'); }
if ($ext = strrchr($fName, '.')) {
	$ext = strtolower(substr($ext, 1));
} else {
	exit('invalid file type!');
}

//get calendar ID and user ID
$calID = isset($_COOKIE['LXCcid']) ? unserialize($_COOKIE['LXCcid']) : ''; //get calendar ID
if (!$calID) { exit('no cal ID'); }
session_name('PHPSESSID'); //session cookie name
session_start();
if (empty($_SESSION[$calID]['uid']))  { exit('no user ID'); }

//get db tools and connect to db
require './lcconfig.php';
require './common/toolboxd.php';
$dbH = dbConnect($calID);

//get settings from database
$set = getSettings();

//validate file type
if (!strpos(",{$set['attTypes']},txt,csv,sql,ics,log",$ext))  { exit("invalid file type"); } //invalid file extension

//get user privs and validate
$stH = stPrep("SELECT g.`privs` FROM `users` AS u INNER JOIN `groups` AS g ON g.`ID` = u.`groupID` WHERE u.`ID` = ?");
stExec($stH,[$_SESSION[$calID]['uid']]);
$user = $stH->fetch(PDO::FETCH_ASSOC); //user privs
if ($user['privs'] < 1) { exit("you are not authorized"); } //no read access
if ($user['privs'] < 9 and !strpos(",{$set['attTypes']},txt,csv",$ext))  { exit("you are not authorized"); } //invalid file extension

//all seems fine
if (!empty($_GET['nwN'])) { //get new file name
	$nName = preg_replace('~\.\w{2,4}$~','',strip_tags($_GET['nwN'])).'.'.$ext; //new name
} else {
	$nName = substr(strrchr('/'.$fName,'/'),1);
}
if (file_exists($fName)) { //file valid
	header('Content-Description: File Transfer');
	header("Content-type: application/octet-stream");
	header('Content-Disposition: attachment; filename="'.$nName.'"');
	header('Expires: 0');
	header('Cache-Control: must-revalidate');
	header('Pragma: public');
	header('Content-Length: '.filesize($fName));
	readfile($fName); //serve file
} else {
	echo "File not present";
}
?>
