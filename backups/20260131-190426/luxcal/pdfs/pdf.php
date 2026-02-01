<?php
/* =========== LuxCal - PDF Print Events ===========*/ $LDV='2025-08-18';
/*Copyright 2009-2025 LuxSoft www.LuxSoft.eu
/*
This file is part of the LuxCal Calendar and is distributed WITHOUT ANY 
WARRANTY. See the GNU General Public License for details.

============================== MUST READ ================================
======== SEE THE configs/pdf.html FILE FOR A DETAILED DESCRIPTION =======
=========================================================================

/*------------------ start of default settings section ----------------*/

//GENERAL SETTINGS (see configs/pdf.html for details)
$ctuID = ""; //ID of the calendar to use, e.g. "mycal". Blank (""): the current calendar 
$pageHdr = "#c - Upcoming Events"; //page header text (#c: calendar title)
$pageFtr = "#p>page #n>#d #u"; //page footer template (#p: period, #n: page number, #d: date/time printed, u: user name (if logged in), >: tab left > center > right)
$sortD = 0; //event sorting on dates; 0: ascending, 1: descending
$maxDays = 0; //max. number of days to show; 0: no maximum
$evtHead = '#c'; //event head template (#e: event title, #c: event title - category color, #u: event title - owner group color, #o: event owner, #/: new line)
$evtBody = '12345678'; //event fields to show (list of numbers: 1: venue, 2: category, 3: description, . . . for more see configs/pdf.html)
$hdStyle = 'B'; //event head style ('' (empty): none, 'B': bold, 'I': italic, 'U': underline)

//PAGE SIZE
$pSize = "A4"; //page size can be A4 or Letter

//DATE FORMATS
$mFormat = "M y"; //month format (M: January, m: Jan, y:2020). Blank (""): No month/year line
$dFormat = "W d"; //day format (W: Monday, w: Mon, d: 21, M: January, m: Jan)

//PRINT COLORS
$cHEAD = "#606060"; //header text color
$bHEAD = "#90FFFF"; //header background color
$cMOYE = "#606060"; //month/year text color
$bMOYE = "#90FFFF"; //month/year background color
$cDATE = "#5862BA"; //day text color
$bDATE = "#E0E0E0"; //day background color

/*----------------- end of default settings section -------------------*/

function printEvents($date) { //print events to pdf
	global $pdf, $evtList, $xx, $evtHead, $evtBody, $hdStyle;

	foreach ($evtList[$date] as $evt) {
		$evtT = makeTime($evt['ald'],$evt['ntm'],$evt['mde'],$evt['sti'],$evt['eti']);
		if ($evt['typ'] == 1) { //day marking
			$color = $evt['tx2'];
			$bgrnd = $evt['tx3'];
			$evt['tit'] = strip_tags($evt['tit']);
			$evt['tx2'] = $evt['tx3'] = '';
		} elseif (strpos($evtHead,'#c') !== false) { //category color
			$color = $evt['cco'] ?: '#505050';
			$bgrnd = $evt['cbg'] ?: '#FFFFFF';
		} elseif (strpos($evtHead,'#u') !== false) { //user color
			$color = '#505050';
			$bgrnd = $evt['uco'] ?: '#FFFFFF';
		} else { //no color
			$color = '#505050';
			$bgrnd = '#FFFFFF';
		}
		$keys = ['#e', '#c', '#u', '#o', '#/']; //possible template keys
		$subs = [$evt['tit'], $evt['tit'], $evt['tit'], $evt['una'], "\n"]; //substitutes
		$title = html_entity_decode(str_replace($keys,$subs,$evtHead),ENT_QUOTES);
		$body = $evtBody ? html_entity_decode(makeE($evt,$evtBody,'br',"<br>"),ENT_QUOTES) : '';
		$pdf->PrintEvent($evtT,$title,$body,strtoupper($hdStyle),$color,$bgrnd);
	}
}

function makeMoye($date) { //format dates
	global $months, $months_m, $mFormat;

	$y = intval(substr($date, 0, 4));
	$m = intval(substr($date, 5, 2));
	$d = ltrim(substr($date, 8, 2),"0");
	$nMoye = '';
	$dElms = ['M' => $months[$m - 1], 'm' => $months_m[$m - 1], 'y' => $y]; //possible date elements
	foreach(str_split($mFormat) as $c) {
		$nMoye .= $dElms[$c] ?? $c;
	}
	return strtoupper($nMoye);
}

function makeDay($date) { //format dates
	global $months, $months_m, $wkDays, $wkDays_l, $dFormat;

	$m = intval(substr($date, 5, 2));
	$d = ltrim(substr($date, 8, 2),"0");
	$n = date("N", strtotime($date));
	$nDay = '';
	$dElms = ['W' => $wkDays[$n], 'w' => $wkDays_l[$n], 'M' => $months[$m - 1], 'm' => $months_m[$m - 1], 'd' => $d]; //possible date elements
	foreach(str_split($dFormat) as $c) {
		$nDay .= $dElms[$c] ?? $c;
	}
	return $nDay;
}

/***** MAIN PROGRAM *****/

//error_reporting(E_ERROR); //errors only
error_reporting(E_ALL); //errors, warnings and notices - test line

chdir('..'); //change to calendar root

//sanity check
if (empty($_POST)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//load required scripts
require './lcconfig.php'; //calendar config data
require './common/toolbox.php'; //tools
require './common/toolboxd.php'; //database tools
require './common/retrieve.php'; //retrieve function

//get parameters (user ID and event filters)
$pars = json_decode($_POST['pdfJson']);  //decode json object
//first load possible PDF configuration
if (!empty($pars->pdfCnf) and file_exists("./configs/{$pars->pdfCnf}.cnf")) { //specified
	include "./configs/{$pars->pdfCnf}.cnf";
} elseif (file_exists("./configs/".basename(__FILE__,'.php').".cnf")) { //default
	include "./configs/".basename(__FILE__,'.php').".cnf";
}
$calID = !empty($ctuID) ? $ctuID : (!empty($pars->calID) ? $pars->calID : $dbDef); //select calendar

$dbH = dbConnect($calID); //connect to database
$set = getSettings(); //get settings from db
//continue get parameters

$lang = $pars->lang ?: $set['language'];
$uID = $pars->uID ?: 1; //default: public user
$users = $pars->users ?: '0';
$groups = $pars->groups ?: '0';
$cats = $pars->cats ?: '0';
$fDate = DDtoID($_POST['fDate']);
$tDate = DDtoID($_POST['tDate']);
if (!$fDate) { $fDate = date('Y-m-d',time()); }
if (!$tDate) { $tDate = date('Y-m-d',time() + ($set['lookaheadDays'] * 86400)); }

//load pdf class + possible configuration
$pdf = $_POST['pdf'] ?? '1';
require("./pdfs/pdfclass{$pdf}.php"); //PDF class

$pageHdr = str_replace('#c',$set['calendarTitle'],$pageHdr);
date_default_timezone_set($set['timeZone']); //set time zone

require "./lang/ui-{$lang}.php"; //load language file

//get user credentials
$stH = stPrep("SELECT u.`ID`, u.`name`, g.`ID` as gID, g.`privs`, g.`vCatIDs` as vCats, g.`eCatIDs` as eCats FROM `users` AS u INNER JOIN `groups` AS g ON g.`ID` = u.`groupID` WHERE u.`ID` = ?");
stExec($stH,[$uID]);
$usr = $stH->fetch(PDO::FETCH_ASSOC); //user & group data
$stH = null; //release statement handle!

//set filters
if ($cats) { //categories to show
	$cats = str_replace(' ','',$cats); //remove spaces
	$usr['vCats'] = ($usr['vCats'] == '0') ? $cats : implode(',',array_intersect(explode(',',$usr['vCats']),explode(',',$cats)));
}

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

//retrieve events
retrieve($fDate,$tDate,'',[$filter,substr($values,1)],'*');

if ($sortD) { krsort ($evtList); }

//create PDF document
//header definition
$title = $pageHdr;
$logo = file_exists($set['logoPath']) ? $set['logoPath'] : ''; //path to logo image
$link = $set['backLinkUrl']; //logo hyperlink, e.g https://www.mysite.com
//footer definition
$keys = ['#p', '#d', '#n', '#u']; //possible template keys
$repl = [$_POST['fDate'].' - '.$_POST['tDate'], IDtoDD(date('Y-m-d')).' '.ITtoDT(date('H:i')), "#", ($usr['ID'] > 1 ? $usr['name'] : '')]; //replacements
$footer = str_replace($keys,$repl,$pageFtr);
//document data
$pdf->SetTitle($set['calendarTitle'].' - Upcoming Events');
$pdf->SetAuthor($set['calendarTitle']);
$pdf->SetSubject("Events: {$fDate}-{$tDate}");
//fill document
$pdf->SetAutoPageBreak(true,10);
$pdf->AddPage();

if ($evtList) { //process events
	$month = '';
	foreach ($evtList as $cDate => &$events) { //loop thru dates
		if(substr($cDate,5,2) !== $month) {
			$pdf->PrintMonth(makeMoye($cDate)); //new month
			$month = substr($cDate,5,2);
		}
		$pdf->PrintDay(makeDay($cDate)); //print date
		printEvents($cDate); //show events for this date
		if (--$maxDays == 0) { break; }
	}
}
$pdf->Output('D',"Upcoming {$fDate} - {$tDate}.pdf"); //start download dialogue
?>
