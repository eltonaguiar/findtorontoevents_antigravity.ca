<?php
/*
= LuxCal index =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed without any warranty.
*/

//page definitions
$pages = array ( //page, header, no hdr, xs hdr, footer, xs ftr, title, includes (r:retrieve, v:view functions m:messaging), spec. attributes
//calendar views
 1 => ['views/year.php','f','0','x','f','0','','rv',''],
 2 => ['views/month.php','f','0','x','f','0','','rv','fm'],
 3 => ['views/month.php','f','0','x','f','0','','rv','wm'],
 4 => ['views/week.php','f','0','x','f','0','','rv','fw'],
 5 => ['views/week.php','f','0','x','f','0','','rv','ww'],
 6 => ['views/day.php','f','0','x','f','0','','rv',''],
 7 => ['views/upcoming.php','f','0','x','f','0','upcoming','rv',''],
 8 => ['views/changes.php','f','0','x','f','0','changes','rv',''],
 9 => ['views/matrixc.php','f','0','x','f','0','','rv',''],
10 => ['views/matrixu.php','f','0','x','f','0','','rv',''],
11 => ['views/gantt.php','f','0','x','f','0','','rv',''],
//support pages
20 => ['pages/login.php','l','l','l','f','0','log_in','m',''],
21 => ['pages/account.php','l','l','l','f','0','profile','',''],
22 => ['pages/search.php','a','a','a','f','0','search','r',''],
23 => ['pages/contact.php','a','a','a','f','0','contact','m',''],
24 => ['pages/thumbnails.php','a','a','a','f','0','thumbnails','',''],
//small pop-up windows
30 => ['pages/event.php','e','e','e','0','0','event','rm','0'], //attrib: evt type
31 => ['pages/dmark.php','e','e','e','0','0','dmarking','rm','1'], //attrib: evt type
32 => ['pages/eventreport.php','e','e','e','0','0','event','r',''],
39 => ['pages/help.php','h','h','h','0','0','user_guide','',''],
//admin pages
80 => ['pages/settings.php','a+','a+','a+','f','0','settings','m',''],
81 => ['pages/categories.php','a','a','a','f','0','edit_cats','',''],
82 => ['pages/users.php','a','a','a','f','0','edit_users','',''],
83 => ['pages/groups.php','a','a','a','f','0','edit_groups','',''],
84 => ['pages/database.php','a','a','a','f','0','manage_db','',''],
85 => ['pages/importUsr.php','a','a','a','f','0','usr_import','',''],
86 => ['pages/exportUsr.php','a','a','a','f','0','usr_export','',''],
87 => ['pages/importIcs.php','a','a','a','f','0','ics_import','',''],
88 => ['pages/exportIcs.php','a','a','a','f','0','ics_export','r',''],
89 => ['pages/importEvt.php','a','a','a','f','0','evt_import','',''],
90 => ['pages/texteditor.php','a','a','a','f','0','edit_text','',''],
91 => ['pages/cleanup.php','a','a','a','f','0','clean_up','',''],
92 => ['pages/msglog.php','a','a','a','f','0','msg_log','',''],
99 => ['pages/styling.php','s','s','s','0','0','ui_styling','',''],
);

//get toolboxes
require './common/toolboxd.php'; //database tools + LCV
require './common/toolbox.php'; //general tools

//set error reporting
//error_reporting(E_ERROR); //errors only
//ini_set('display_errors',0); ini_set('log_errors',1); //no error display
error_reporting(E_ALL); //errors, warnings and notices - test
ini_set('display_errors',1); ini_set('log_errors',1); //test

//proxies: don't cache
header("Cache-control:private");

//load config data
$version = strtok(LCV,'-'); //software version
if (!file_exists('./lcconfig.php')) {//no current config data: install
	header("Location: install".str_replace('.','',rtrim($version,'LM')).".php"); exit();
}
require './lcconfig.php';
if ($version != $lcV) { //new version: upgrade
	header("Location: upgrade".str_replace('.','',rtrim($version,'LM')).".php"); exit();
}

//init
$nowTS = time(); //current time uts
$calPath = rtrim(dirname($_SERVER["PHP_SELF"]),'/').'/';
session_set_cookie_params(1440,$calPath); //set cookie path

//get calendar ID
$calID = getCalID();

//connect to db
$dbH = dbConnect($calID);

//get settings from database
$set = getSettings();

//validate input variables
if ($alert = validInputVars()) {
	require './pages/alert.php'; exit(); //alert page
}

//check for a small viewport
$winXS = (!empty($_COOKIE['LXCxs']) or isset($_GET['xs']));

//start session
session_name('PHPSESSID'); //session cookie name
session_start();
session_regenerate_id();

//page counter
$_SESSION['pageCount'] = empty($_SESSION['pageCount']) ? 1 : $_SESSION['pageCount'] + 1;

//check for SSO (user email passed by parent)
if (!empty($_SESSION['lcUser'])) {
	$stH = stPrep("SELECT `ID` FROM `users` WHERE (`email` = ? OR `name` = ?) AND `status` >= 0");
	stExec($stH,[$_SESSION['lcUser'],$_SESSION['lcUser']]);
	if ($row = $stH->fetch(PDO::FETCH_NUM)) { $_SESSION[$calID]['uid'] = $row[0]; }; //set user ID (log in)
	$stH = null; //release statement handle
	unset($_SESSION['lcUser']);
}

//load last selected cP, cG, cU, cC, cL, cD
$opt = loadLastSel();
$newDate = ''; //preset no new date

//get user ID
if (isset($_POST['loff'])) { //log off
	logoff($opt);
	if ($set['backLinkUrl']) { //back link defined: redirect
		header("Location: {$set['backLinkUrl']}");
	}
	$_SESSION[$calID]['uid'] = 1; //set public user
} elseif (isset($_POST["userID"]) and isset($_POST["userTK"])) { //from login page
	$stH = stPrep("SELECT `ID` FROM `users` WHERE `ID` = ? AND `token` LIKE '%{$_POST['userTK']}%' AND status >= 0");
	stExec($stH,[$_POST["userID"]]);
	if ($row = $stH->fetch(PDO::FETCH_ASSOC)) { //valid user ID
		$opt['uT'] = $_POST["userTK"];
		$_SESSION[$calID]['uid'] = $_POST["userID"];
	}
	$stH = null;
}
if (empty($_SESSION[$calID]['uid'])) { //fall back
	$_SESSION[$calID]['uid'] = (!empty($opt['uI']) and (!empty($_POST) or $opt['uI'][0])) ? intval(substr($opt['uI'],1)) : 1;
}

//set time zone
date_default_timezone_set($set['timeZone']);
$today = date('Y-m-d'); //date of today

//get user data & privs
$stH = stPrep("SELECT u.`ID`,u.`name`,u.`email`,u.`phone`,u.`msingID`,u.`notSrvs`,u.`language` AS lang,u.`expDate`,g.`privs`,g.`vCatIDs` AS vCats,g.`eCatIDs` AS eCats,g.`rEvents` AS rEvts,g.`mEvents` AS mEvts,g.`pEvents` AS pEvts,g.`upload`,g.`tnPrivs` FROM `users` AS u INNER JOIN `groups` AS g ON g.`ID` = u.`groupID` WHERE (u.`ID` = 1 OR u.`ID` = ?) AND u.`expDate` >= $today ORDER BY u.`ID` DESC"); //if userID not found, revert to public user
stExec($stH,[$_SESSION[$calID]['uid']]);
$usr = $stH->fetch(PDO::FETCH_ASSOC); //user & group data
$row = $stH->fetch(PDO::FETCH_ASSOC); //public user or false (if $usr is public user)
$stH = null;
if (isset($_GET['pP']) and $usr['privs'] == 9) { phpinfo(); exit; } //admin - show PHP installation page
if ($row != false) { //$usr is not the public user: take care that usr has v & e rights of usr + public user
	if ($usr['vCats'] != '0' and $row['privs'] > 0) { $usr['vCats'] = $row['vCats'] == '0' ? '0' : $usr['vCats'].','.$row['vCats']; } //view categories
	if ($usr['eCats'] != '0' and $row['privs'] > 1) { $usr['eCats'] = $row['eCats'] == '0' ? '0' : $usr['eCats'].','.$row['eCats']; } //edit categories
} else { //uid not found or is public user
	$_SESSION[$calID]['uid'] = 1;
}
unset($row);
$opt['uI'] = (empty($opt['uI']) ? '0' : $opt['uI'][0]).strval($_SESSION[$calID]['uid']);

if (empty($opt['tS']) or ($nowTS - $opt['tS']) > 1440) { //new hit
	if ($usr['ID'] == 1 or !$set['restLastSel']) { //don't use last selections
		$opt = ['uI' => '01']; //set bake: no, user: public user
	}
	$opt['cD'] = $today;
}

if (!empty($_POST['calID'])) { //check form token
	$srcPage = $_REQUEST['xP'] ?? $opt['cP'] ?? 0; //source page
	if ($alert = checkToken($srcPage)) {
		require './pages/alert.php'; exit(); //alert page
	}
}

if (empty($_POST) or isset($_POST['bake'])) { //new hit or log in - update login data
	$stH = stPrep("UPDATE `users` SET `login0` = CASE WHEN substr(`login0`,1,1) = '9' THEN ? ELSE `login0` END, `login1` = ?, `loginCnt` = `loginCnt` + 1 WHERE `ID` = ?");
	stExec($stH,[$today,$today,$usr['ID']]);
}

//set default views
$defViewLog = $winXS ? $set['defViewLogS'] : $set['defViewLogL']; //for logged users
$defViewPub = $winXS ? $set['defViewPubS'] : $set['defViewPubL']; //for public users

//set header display
$cH = $_SESSION[$calID]['hdr'] = ($_GET['hdr'] ?? $_SESSION[$calID]['hdr'] ?? 1);

//set language
$locale = isset($_SERVER['HTTP_ACCEPT_LANGUAGE']) ? locale_accept_from_http($_SERVER['HTTP_ACCEPT_LANGUAGE']) : '';
$locale = $locale ? substr($locale,0,2) : '';
$defLang = array_key_exists($locale,$languages) ? $languages[$locale] : $set['language'];
if (isset($_REQUEST["cL"])) { $opt['cL'] = $_REQUEST['cL']; }
if (empty($opt['cL'])) { $opt['cL'] = strtolower($usr['lang'] ?: $defLang); }
if (!file_exists("./lang/ui-{$opt['cL']}.php")) { $opt['cL'] = 'english'; }
require "./lang/ui-{$opt['cL']}.php"; //load language file

//set view templates ? public user : logged-in user
$avViews = $usr['ID'] == 1 ? $set['viewsPublic'] : $set['viewsLogged'];
$templ['gen'] = $usr['ID'] == 1 ? $set['evtTemplGen'] : $set['evtTemplGen2'];
$templ['upc'] = $usr['ID'] == 1 ? $set['evtTemplUpc'] : $set['evtTemplUpc2'];
$templ['pop'] = $usr['ID'] == 1 ? $set['evtTemplPop'] : $set['evtTemplPop2'];


if (isset($_POST['loff']) or !$usr['privs']) { //logoff or no access: reset options
	$opt['cP'] = $usr['privs'] ? $defViewPub : 20;
	$opt['cG'] = $opt['cU'] = $opt['cC']  = [0];
	$opt['cL'] = strtolower($set['language']);
	$opt['cD'] = $today;
	goto allSet;
}

//set current page
if (isset($_REQUEST['cP'])) {
	if ($_REQUEST['cP'] == 'up' and !empty($opt['cP'])) { //one level up
		$oneUp = [2 => 1, 3 => 1, 4 => 2, 5 => 3, 6 => 4];
		$upPage = $opt['cP'];
		while ($upPage > 1) {
			$upPage = $oneUp[$upPage];
			if (strpos($avViews,strval($upPage)) !== false) { $opt['cP'] = $upPage; break; }
		}
	} elseif (($_REQUEST['cP'] > 10 or strpos($avViews,strval($_REQUEST['cP'])) !== false) and isset($pages[$_REQUEST['cP']])) {
		$opt['cP'] = $_REQUEST['cP'];
	} elseif ($_REQUEST['cP'] == 0) {
		$opt['cP'] = $usr['ID'] == 1 ? $defViewPub : $defViewLog;
	}
}
if (empty($opt['cP'])) { //set current page
	$opt['cP'] = $usr['ID'] > 1 ? $defViewLog : ($usr['privs'] ? $defViewPub : 20); //if no privs, force login
}

//set filters
$opt['cG'] = $_REQUEST['cG'] ?? $opt['cG'] ?? [0]; //group
$opt['cU'] = $_REQUEST['cU'] ?? $opt['cU'] ?? [0]; //user
$opt['cC'] = $_REQUEST['cC'] ?? $opt['cC'] ?? [0]; //category
if (!empty($_REQUEST['nD'])) {
	$opt['cD'] = $newDate = DDtoID($_REQUEST['nD']); //current date
} else { 
	$opt['cD'] = $_REQUEST['cD'] ?? $opt['cD'] ?? $today;
}

allSet:

//save last selected cP, cG, cU, cC, cL, cD
if (isset($_POST['bake'])) { $opt['uI'][0] = $_POST['bake']; } //when login bake: 0 = forget, 1 = remember
$opt['tS'] = $nowTS;
saveLastSel($opt);

$winXP = !empty($_REQUEST['xP']); //small window
if ($winXP) { $opt['cP'] = $_REQUEST['xP']; }
$page = &$pages[$opt['cP']]; //current page

//set rss get-method filter
$cF = "?cal={$calID}";
foreach ($opt['cG'] as $group) { if ($group) { $cF .= '&amp;cG%5B%5D='.$group; } }
foreach ($opt['cU'] as $user) { if ($user) { $cF .= '&amp;cU%5B%5D='.$user; } }
foreach ($opt['cC'] as $categ) { if ($categ) { $cF .= '&amp;cC%5B%5D='.$categ; } }

$mode = $page[8]; //page mode
$state = $_REQUEST['state'] ?? ''; //event edit state

if (strpos($page[7],'r') !== false) { //retrieve required
	require './common/retrieve.php';
}
if (strpos($page[7],'v') !== false) { //view functions required
	require './common/vfunctions.php';
}
if (strpos($page[7],'m') !== false) { //messaging required
	require './common/messaging.php';
}

//set token for destination page
$tkn = $_SESSION["LXCtkn_{$calID}:{$opt['cP']}"] = md5(rand());
$formCal = "<input type='hidden' name='calID' value='{$calID}'>\n<input type='hidden' name='tkn' value='{$tkn}'>\n<script>setTimeout(function() { alert(`{$xx['alt_message#0']}`); }, 1200000);</script>";

//get all calendar IDs
$calIDs = getCIDs();

/* build calendar page */
$pageTitle = !empty($page[6]) ? $xx["title_{$page[6]}"] : '';
$hdrType = $cH < 1 ? $page[2] : ($winXS ? $page[3] : $page[1]); //set header type
$ftrType = $winXS ? $page[5] : $page[4]; //set footer type
$body = $page[0]; //body uri
unset($page,$pages);
require './common/header.php'; //header
require "./{$body}"; //body
require './common/footer.php'; //footer
?>
