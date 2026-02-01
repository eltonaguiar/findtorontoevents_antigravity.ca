<?php
/* LuxCal display1 © 2009-2025 LuxSoft www.LuxSoft.eu*/$LDV='2024-12-20';
/*
This file is part of the LuxCal Calendar and is distributed WITHOUT ANY 
WARRANTY. See the GNU General Public License for details.

============================== MUST READ ================================
This display must be run from the calendar's root folder!
SEE THE display.html FILE IN THE configs FOLDER FOR A FURTHER DESCRIPTION
=========================================================================

/*------------------ start of default settings section ----------------*/

//SET START AND END DATE (see configs/display.html for details)
$fromDate = "DAY"; //from date
$tillDate = "MONTH+1"; //till date

//GENERAL SETTINGS (see display.txt for details)
$calID = "mycal"; //calendar to use (ID of the calendar. Blank (""): the default calendar) 
$calName = "Upcoming Events"; //calendar header text. Asterisk ("*"): calendar title, blank (""): no header
$login = 1; //show user name and login button in right upper corner (0: no, 1: yes)
$logMsg = "No account yet: contact the administrator"; //message shown at the top of the log in page
$pdfBut = 1; //show PDF file download button in right upper corner (0: no, 1: all users, 2: for logged in users)
$pdfCnf = ""; //name (without extension) of configuration file to be used when producing the PDF file; blank (""): use default)
$sortD = 0; //event sorting on dates; 0: ascending, 1: descending
$maxDays = 0; //max. number of days to show; 0: no maximum
$futEvts = 0; //show ongoing and future events only (0: no, 1: yes). Note: This setting overrules the "from date" and sets it to "DAY"
$evtHead = "#t #c"; //event head template (#t: times, #e: event title, #c: event title - category color, #u: event title - owner group color, #o: event owner, #a: age, #/: new line)
$evtBody = "123"; //event fields to show (list of numbers: 1: venue, 2: category, 3: description, . . . for more see Settings page - Event templates)
$evtWin = 1; //on click open event window (0: no, 1: yes). If the user has post rights, the event add/edit window will open, otherwise the event report window will open
$recOnce = 0; //for recurring events, show only one (the next) occurrence (0: all, 1: next only)
$mulOnce = 0; //for multi-day events, show only one (the next) occurrence (0: all, 1: next only)
$maxImgH = 80; //maximum height of images (in pixels)
$noEvents = "No events"; //message shown when no upcoming events
$icon = "lcal.png"; //path to a favicon shown in the browser tab for the display. Only applicable if the display is shown in its own browser tab

//EVENT FILTERS
$users = "0"; //events of users (event owners) to show (comma separated list of user IDs; 0: all users, the text "own": own events only).
$groups = "0"; //events of users (event owners) in certain groups to show (comma separated list of group IDs; 0: all groups, the text "own": events of users in own group only).
$cats = "0"; //events in categories to show (comma separated list of cat IDs; 0: all categories).
$scats = "0"; //events in subcategories to show (comma separated list of subcat IDs; possible values: 1, 2, 3 , etc. 0: all subcats).
$venue = ""; //show only events with case-insensitive text string present in venue. Blank (""): no filter 
//Note: It is also possible to use a URL parameter 'cats'. The intersection of the $cats setting above and the URL parameter will be applied. Example: www.yoursite.xxx/calendar/display1.php?cats=1,4,5

//MARGINS/BORDERS in pixels
$MOUTR = "8"; //container outer margin
$MINNR = "4"; //container inner margin
$WDCOL = "10"; //date column width in %
$WBORD = "4"; //container border width
$WGRID = "2"; //calendar grid width
$MDATE = "5px"; //date margin - top
$MEVNT = "0px 0px 10px 0px"; //event margins - top right bottom left
$MTITL = "0px 0px 0px 0px"; //title margins - top right bottom left
$MBODY = "0px 0px 0px 10px"; //body margins - top right bottom left

//DATE FORMAT
$dFormat = "W/d m"; //W: Monday, w: Mon, d: 21, M: January, m: Jan, /: new line

//DISPLAY COLORS
$BGENL = "#F0F0F0"; //general background color
$BBORD = "#F0F0F0"; //container background color
$CBORD = "#884444"; //container border color
$CGRID = "#FFFFFF"; //calendar grid color
$BDATE = "#EDD070"; //calendar date background color
$CDATE = "#4040E8"; //calendar date text color
$CHEAD = "#4040E8"; //header text color
$BEVNT = "#F0F0D0"; //event background color
$CTITL = "#990000"; //event title color
$CEVNT = "#202030"; //event description color
$CDATI = "#4040E8"; //event date/time color
$CLINK = "#222288"; //URL link color

//FONT STYLE WEIGHT SIZE/LINE-HEIGHT FAMILY
//size and family are required; rest optional
$FBASE = "14px arial,sans-serif"; //base font
$FHEAD = "bold 1.6em arial,sans-serif"; //header
$FDATE = "1.4em tahoma,sans-serif"; //date
$FETIT = "1.1em arial,sans-serif"; //event title
$FEVNT = "1.1em arial,sans-serif"; //event
$FNOEV = "1.0em arial,sans-serif"; //"No events" text

//VERTICAL SPACE in px
$HHEAD = "32"; //header height
$HBRKS = "2"; //extra space between event sections

/*------------------ end of default settings section ------------------*/

function makeEvtHead($head,$evt,$date) { //make event head
	global $xx;

	$evtT = makeTime($evt['ald'],$evt['ntm'],$evt['mde'],$evt['sti'],$evt['eti']);
	$uStyle = $evt['uco'] ? " style='background-color:{$evt['uco']};'" : '';
	$cStyle = ($evt['cco'] ? "color:{$evt['cco']};" : '').($evt['cbg'] ? "background-color:{$evt['cbg']};" : '');
	$cStyle = !empty($cStyle) ? " style='{$cStyle}'" : '';
	$age = (isset($evt['rpt']) and $evt['rpt'] == 4 and preg_match('%(19|20)\d\d%',$evt['tx1'].$evt['tx3'],$year)) ? strval(substr($date,0,4) - $year[0]) : '';
	if (!$age) { $head = preg_replace('~(^|\|)[^|]*#a[^|]*(\||$)~','#a',$head); } //no age, delete section
	else { $head = str_replace('|','',$head); }
	$keys = ['#t', '#e', '#c', '#u', '#o', '#a', '#/', '|']; //possible template keys
	$html = ["<span class='time'>{$evtT}</span>", $evt['tit'], "<span{$cStyle}>{$evt['tit']}</span>", "<span{$uStyle}>{$evt['tit']}</span>", $evt['una'], $age, "<br>", ""]; //html code
	return str_replace($keys,$html,$head);
}

function showEvents($date) { //show events in calendar
	global $calID, $evtList, $evtHead, $evtBody, $futEvts, $evtWin, $rxULink, $rxIMGTags;

	$now = date('Y-m-dH:i');
	foreach ($evtList[$date] as $evt) {
		if ($futEvts and $evt['eti'] and $date.$evt['eti'] < $now) { continue; } //future events only
		$chBox = $evt['cbx'] ? checkBox($evt,$date) : '';
		if ($evtWin) {
			$onClick = " onclick='".($evt['mayE'] ? 'editE' : 'showE')."({$evt['eid']},`{$date}`,`{$calID}`);'"; //view or post/edit 
		} else {
			$onClick = '';
		}
		echo "<div class='event'>\n";
		if (strpos($evtBody,'4') === false and preg_match($rxIMGTags,$evt['tx2'],$img)) { //image found in field tx2
			$image = preg_match($rxULink,$evt['tx2'],$url) ? "<a href='{$url[1]}' target='_blank'>{$img[0]}</a>" : $img[0];
			echo "<span class='imageL'>{$image}</span>\n";
		}
		if (strpos($evtBody,'5') === false and preg_match($rxIMGTags,$evt['tx3'],$img)) { //image found in field tx3
			$image = preg_match($rxULink,$evt['tx3'],$url) ? "<a href='{$url[1]}' target='_blank'>{$img[0]}</a>" : $img[0];
			echo "<span class='imageR'>{$image}</span>\n";
		}
		$eHead = makeEvtHead($evtHead,$evt,$date); //make event head
		echo "<div class='eHead'>{$chBox}<span{$onClick}>{$eHead}</span></div>\n";
		echo "<div class='eBody'>".makeE($evt,$evtBody,'br',"<br>")."</div>\n";
		echo "</div>\n";
	}
}

function calcFTDate($date,$from) { //compute From / To date
	global $futEvts;
	
	if ($futEvts and $from) { //future events only
		$dStamp = time(); //from date is today
	} else {
		$date = str_replace(' ','',$date);
		if (preg_match('~^\d{2,4}[\./-]\d{2}[\./-]\d{2}$~i',$date,$match)) { //fixed date
			$dStamp = mktime(12,0,0,(INT)substr($date,5,2),(INT)substr($date,8,2),(INT)substr($date,0,4)); //current Unix time
		} elseif (preg_match('~^(DAY|WEEK|MONTH|YEAR)([+-]\d{1,4})?$~i',$date,$match)) { //parse date
			$mult = !empty($match[2]) ? intval($match[2]) : 0;
			switch (strtoupper($match[1])) { //compute date
			case 'DAY':
				$dStamp = time() + ($mult * 86400); //time first day
				break;
			case 'WEEK':
				$wkDay = ($from ? 0 : 6) - date('w');
				$dStamp = time() + ($set['weekStart'] + $wkDay * 86400) + ($mult * 604800); //time first day
				break;
			case 'MONTH':
				$month = date('n') + $mult + ($from ? 0 : 1);
				$day = $from ? 1 : 0;
				$dStamp = mktime(12,0,0,$month,$day,date('Y')); //time first day of from month / last day of till month
				break;
			case 'YEAR':
				$dStamp = $from ? mktime(12,0,0,1,1,date('Y') + $mult) : mktime(12,0,0,1,0,date('Y') + $mult + 1); //time first day of from year : last day of till year (next year -1 day)
			}
		} else {
			echo 'Error in $date'; exit;
		}
	}
	return date('Y-m-d', $dStamp);
}

function makeDate($date) { //format dates
	global $months, $months_m, $wkDays, $wkDays_l, $dFormat;

	$m = intval(substr($date, 5, 2));
	$d = ltrim(substr($date, 8, 2),"0");
	$n = date("N", strtotime($date));
	$nDate = '';
	$dElms = ['W' => $wkDays[$n], 'w' => $wkDays_l[$n], 'M' => $months[$m - 1], 'm' => $months_m[$m - 1], 'd' => $d, '/' => "<br>"]; //possible date elements
	foreach(str_split($dFormat) as $c) {
		$nDate .= !empty($dElms[$c]) ? $dElms[$c] : $c;
	}
	return $nDate;
}

function intersect($str1,$str2) {
	if ($str1 == '0') { return $str2; }
	return implode(',',array_intersect(explode(',',$str1),explode(',',$str2)));
}

/***** MAIN PROGRAM *****/

//error_reporting(E_ERROR); //errors only
error_reporting(E_ALL); //errors, warnings and notices - test line
require './lcconfig.php'; //calendar config data
require './common/toolbox.php'; //tools
require './common/toolboxd.php'; //database tools
require './common/retrieve.php'; //retrieve function

//init
$calPath = rtrim(dirname($_SERVER["PHP_SELF"]),'/').'/';
session_set_cookie_params(1440,$calPath); //set cookie path

//load display configuration
if (isset($_GET['cnf'])) { //sanitize GET params
	$cnf = sanitize($_GET['cnf']);
}
if (!empty($cnf) and file_exists("./configs/{$cnf}.cnf")) { //specified
	include "./configs/{$cnf}.cnf";
} elseif (file_exists("./configs/".basename(__FILE__,'.php').".cnf")) { //default
	include "./configs/".basename(__FILE__,'.php').".cnf";
}

if (empty($calID)) { $calID = $dbDef; } //select calendar

$dbH = dbConnect($calID); //connect to database
$set = getSettings(); //get settings from db
date_default_timezone_set($set['timeZone']); //set time zone
header("Cache-control: private"); //proxies: don't cache
if ($calName == '*') { $calName = $set['calendarTitle']; }

//get default UI language
$locale = isset($_SERVER['HTTP_ACCEPT_LANGUAGE']) ? locale_accept_from_http($_SERVER['HTTP_ACCEPT_LANGUAGE']) : '';
$locale = $locale ? substr($locale,0,2) : '';
$defLang = array_key_exists($locale,$languages) ? $languages[$locale] : $set['language'];

require './lang/ai-'.strtolower($defLang).'.php'; //get ai texts

session_name('PHPSESSID'); //session cookie name
session_start();

//get user ID
$opt = loadLastSel(); //load uID, if saved - default: public user
$uID = substr($opt['uI'],1);
$msg = $un_em = ''; //init
if (!empty($_POST['logX'])) { //log-in mode
	$logX = $_POST['logX'][0];
	$un_em = sanitize($_POST['un_em'] ?? '');
	$pword = sanitize($_POST['pword'] ?? '');
	if ($logX == 'w') { //login form
		$msg = $logMsg;
	} elseif ($logX == 'o') { //log out button pressed
		$uID = 1; //public user
		$opt['uI'] = '01';
		saveLastSel($opt);
	} elseif ($logX == 'i') { //logging in: validate form
		if (!$un_em) { $msg = $ax['log_no_un_em']; goto end; }
		if (!$pword) { $msg = $ax['log_no_pw']; goto end; }
		$md5Pw = md5($pword);
		$stH = stPrep("SELECT `ID` FROM `users` WHERE (`name` = ? OR `email` = ?) AND (`password` = ? OR `tPassword` = ?) AND `status` >= 0");
		stExec($stH,[$un_em,$un_em,$md5Pw,$md5Pw]);
		$row = $stH->fetch(PDO::FETCH_ASSOC); //fetch user details
		$stH = null;
		if (!$row) { $msg = $ax['log_un_em_pw_invalid']; goto end; }
		$uID = $row['ID'];
		$opt['uI'] = $opt['uI'][0].strval($uID); //preserve bake/eat digit
		saveLastSel($opt);
		end: //watch out for the T-rex
	}
}
//get user credentials
$stH = stPrep("SELECT u.`ID`, u.`name`, u.`language`, g.`ID` as gID, g.`privs`, g.`vCatIDs` as vCats, g.`eCatIDs` as eCats FROM `users` AS u INNER JOIN `groups` AS g ON g.`ID` = u.`groupID` WHERE u.`ID` = ?");
stExec($stH,[$uID]);
$usr = $stH->fetch(PDO::FETCH_ASSOC); //user & group data
$stH = null;

require './lang/ui-'.strtolower($usr['language'] ?: $defLang).'.php'; //get ui texts

if (!$msg and !$usr['privs']) {
	$msg = $logMsg; //login form
}

$evtList = []; //init
if (!$msg) { //read access: get events
	if ($usr['privs'] > 1) { $_SESSION[$calID]['uid'] = $uID; } //uid for index.php when editE

	$fDate = calcFTDate($fromDate,true); //compute from date
	$tDate = calcFTDate($tillDate,false); //compute till date

	//set filters
	$cats = str_replace(' ','',$cats); //remove spaces
	if (isset($_GET['cats'])) {
		$getCats = sanitize($_GET['cats']);
	}
	if (!empty($getCats)) {
		$urlCats = preg_replace_callback('~(,?)([^,]+)(,?)~', function ($m) { return $m[1].intval($m[2]).$m[3]; }, $getCats); //sanitize
		$cats = intersect($cats,$urlCats); //intersection of $cats and URL cats
	}
	$usr['vCats'] = intersect($usr['vCats'],$cats);

	$filter = $values = '';
	if ($users) {
		if ($users == 'own') { $users = $uID; }
		$placeholders = preg_replace("~\d+~",'?',$users);
		$filter .= " AND e.`userID` IN ({$placeholders})";
		$values .= ','.$users; 
	}
	if ($groups) {
		if ($groups == 'own') { $groups = $usr['gID']; }
		$placeholders = preg_replace("~\d+~",'?',$groups);
		$filter .= " AND g.`ID` IN ({$placeholders})";
		$values .= ','.$groups;
	}
	if ($scats) {
		$placeholders = preg_replace("~\d+~",'?',$scats);
		$filter .= " AND g.`ID` IN ({$placeholders})";
		$values .= ','.$scats;
	}
	if ($venue) {
		$filter .= " AND e.`venue` LIKE ?";
		$values .= ','."%{$venue}%";
	}

	//retrieve events
	retrieve($fDate,$tDate,'',[$filter,substr($values,1)],'*');
	
	if ($sortD) { krsort ($evtList); }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title><?php echo $set['calendarTitle']; ?></title>
<meta name="application-name" content="LuxCal V<?= LCV.' Display1 V'.$LDV.' Calendar ID '.$calID?>">
<meta name="author" content="Roel Buining">
<meta name="robots" content="nofollow">
<meta name="viewport" content="width=device-width, initial-scale=1">
<?php
echo "<link rel='icon' type='image/".substr(strrchr($icon,'.'),1)."' href='{$icon}'>\n";
echo "<script src='common/toolbox.js?v=".LCV."'></script>\n";
echo "<script>var calID = '{$calID}';</script>";
$calTop = ($calName or $login) ? (int)$MOUTR + (int)$HHEAD : (int)$MOUTR;
$hdrMarginV = (int)$MOUTR + 0;
$hdrMarginH = (int)$MOUTR + (int)$MINNR + (int)$WBORD;
echo "
<style type='text/css'>
* {padding:0; margin:0;}
body {font:{$FBASE}; background: {$BGENL}; overflow:hidden; cursor:default;}
br {margin-bottom:{$HBRKS}px;}
a {color:{$CLINK}; text-decoration:none; cursor:pointer;}
a:hover {text-shadow: 0.2em 0.3em 0.2em {$CLINK};}
img {max-height:{$maxImgH}px;}
fieldset {display:table-cell; font-size:1.1em; padding:8px; border:1px solid {$CBORD}; background:{$BEVNT}; border-radius:5px;}
legend {font-weight:bold; padding:0 5px; color:{$CHEAD}; background:{$BEVNT};}
input[type=text], input[type=password] {font-size:1.0em; padding:0 2px; color:{$CEVNT}; background:{$BGENL}; border-radius:2px; border:1px solid #666; cursor:text; height:18px; margin-bottom:10px;}
input[type='radio'] {cursor:pointer;}
input.date {width:5.5em; height:1.1em;}
label {cursor:pointer; margin:0 10px 0 4px;}
button {font-size:0.9em; padding:1px 4px; color:{$CLINK}; background:{$BBORD}; border-radius:4px; border:1px solid {$CBORD}; cursor:pointer;}
button:hover {border:1px solid #F44;}
[onClick] {cursor:pointer;}
div.msgLine {display:table; margin:30px auto; background:#F0A070; padding:4px 10px;}
div#pdfPop {position:absolute; top:20%; left:0; right:0; display:none; z-index:10;}
div.dialogBox {display:table; margin:0 auto; font-size:1.0em; background:{$BEVNT}; padding:12px 18px; border:1px solid {$CBORD}; border-radius:5px; box-shadow:5px 5px 5px #888;}
.bold {font-weight:bold;}
.floatC {text-align:center;}
div.header {font:{$FHEAD}; color:{$CHEAD}; margin:{$hdrMarginV}px {$hdrMarginH}px;}
form {color:{$CHEAD};}
form.login {float:right; color:{$CHEAD}; margin-right:{$hdrMarginH}px;}
button.pdf {float:right; margin-right:20px;}
div.container {position:absolute; top:{$calTop}px; right:{$MOUTR}px; bottom:{$MOUTR}px; left:{$MOUTR}px; padding:{$MINNR}px; overflow:auto; border:{$WBORD}px solid {$CBORD}; border-radius:8px;}
table.calendar {width:100%; background:{$BBORD}; border:none;}
td {vertical-align:top; border:{$WGRID}px solid {$CGRID};}
td.dCol {font:{$FDATE}; width:{$WDCOL}%; color:{$CDATE}; background:{$BDATE}; padding-top:{$MDATE};}
td.eCol {font:{$FEVNT}; padding:5px 10px; background:{$BEVNT};}
td.noEvt {text-align:center; padding:30px 0; color:{$CEVNT}; font:{$FNOEV};}
div.event {margin:{$MEVNT}; clear:both;}
div.eHead {font:{$FETIT}; color:{$CTITL}; margin:{$MTITL};}
div.eBody {color:{$CEVNT}; margin:{$MEVNT};}
.chkBox {padding-right:2px;}
.time {color:{$CDATI};}
.imageL {float:left; margin: 0px 10px 10px 0px;}
.imageR {float:right; margin: 0px 0px 10px 10px;}
</style>
</head>
<body>\n";
//display calendar
if (!$msg) { //no login form
	if ($login) { //show login/out button
		echo "<form class='login' action='".htmlspecialchars($_SERVER["REQUEST_URI"])."' method='post'>\n";
		echo $uID == 1 ? "<button name='logX' value='w'>{$xx['log_in']}</button>" : "{$usr['name']}&ensp;<button name='logX' value='o'>{$xx['log_out']}</button>\n";
		echo "</form>\n";
	}
	if ($pdfBut == 1 or ($pdfBut == 2 and $uID > 1)) { //show PDF File button
		echo "<button class='pdf' title='{$xx['hdr_dload_pdf']}' onclick='showX(`pdfPop`,true);'>PDF</button>\n";
		//prepare PDF dialog box (hidden)
		$pdfJson = json_encode(['calID' => $calID, 'uID' => $uID, 'users' => $users, 'groups' => $groups, 'cats' => $cats, 'venue' => $venue, 'pdfCnf' => $pdfCnf]); //json encode object
		echo "<div id='pdfPop'>
<div class='dialogBox floatC'>
<fieldset>\n<legend>PDF - {$xx['title_upcoming']}</legend>
<form action='pdfs/pdf.php' method='post'>
<input type='hidden' name='pdfJson' value='{$pdfJson}'>
<label><input type='radio' name='pdf' value='1' checked>{$xx['portrait']}</label>&ensp;
<label><input type='radio' name='pdf' value='2'>{$xx['landscape']}</label><br><br>
{$xx['from']}: <input class='date' type='text' name='fDate' id='fDate' value=".IDtoDD($fDate).">
&ensp;{$xx['to']}: <input class='date' type='text' name='tDate' id='tDate' value=".IDtoDD($tDate).">
<br><br>
<button type='submit' class='bold' onclick='showX(`pdfPop`,false);'>&nbsp;OK&nbsp;</button>&ensp;
<button type='button' onclick='showX(`pdfPop`,false);'>Cancel</button>
</form></fieldset></div></div>";
	}
}
if ($calName) {
	echo "<div class=".(($evtWin and $usr['privs'] > 1) ? "'header' onclick='newE(0);'" : "'header'").">{$calName}</div>\n";
}
echo "<div class='container'>\n";
if ($msg) { //login form
	echo "<div class='msgLine'>{$msg}</div>\n";
	echo "<div class='dialogBox'>\n<fieldset><legend>{$xx['log_in']}</legend>
<form action='".htmlspecialchars($_SERVER["REQUEST_URI"])."' method='post'>{$ax['log_un_or_em']}<br><input type='text' name='un_em' size='15' value='{$un_em}'><br><br>
{$ax['log_pw']}<br><input type='password' name='pword' size='15'><br><br>
<div class='floatC'><button type='submit' class='bold' name='logX' value='i'>{$xx['log_in']}</button>\n";
	if ($usr['privs']) { echo "&ensp;<button type='submit' name='back'>{$xx['back']}</button>\n"; }
	echo "</div>\n</form>
	</fieldset>
	</div>\n";
} else { //show events
	echo "<table class='calendar'>\n";
	$evts1x = []; //init
	if ($evtList) {
		foreach ($evtList as $cDate => &$events) { //loop thru dates
			foreach ($events as $k => $evt) { //loop thru events
				if (($evt['r_t'] and $recOnce) or ($evt['mde'] and $mulOnce)) { //remove recurring and/or multi-day event multiples
					if (in_array($evt['eid'],$evts1x)) {
						unset($events[$k]);
					} else {
						$evts1x[] = $evt['eid'];
					}
				}
			}
			if (empty($events)) { continue; } //no events left for this date
			$onclick = ''; //init
			if ($evtWin and $usr['privs'] > 1) {
				$onclick = " onclick='newE(`{$cDate}`);' title='{$xx['vws_add_event']}'";
			}
			echo "<tr>\n";
			echo "<td class='dCol floatC'{$onclick}>".makeDate($cDate)."</td>\n"; //show date
			echo "<td class='eCol'>\n";
			showEvents($cDate); //show events for this date
			echo "</td>\n";
			echo "</tr>\n";
			if (--$maxDays == 0) { break; }
		}
	} else {
		echo "<tr><td class='noEvt'>{$noEvents}</td></tr>\n";
	}
	echo "</table>\n";
}
echo "</div>\n";
?>
</body>
</html>
