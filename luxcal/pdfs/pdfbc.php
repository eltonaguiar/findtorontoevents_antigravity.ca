<?php
/* ====== LuxCal - PDF Print Birthday Calendar =====*/ $LDV='2023-08-01';
/*Copyright 2009-2025 LuxSoft www.LuxSoft.eu
/*
This file is part of the LuxCal Calendar and is distributed WITHOUT ANY 
WARRANTY. See the GNU General Public License for details.

============================== MUST READ ================================
=== SEE THE configs/pdf-birthdays.html FILE FOR A DETAILED DESCRIPTION ==
=========================================================================

/*------------------ start of default settings section ----------------*/

//GENERAL SETTINGS (see configs/pdf-birthdays.html for details)
$ctuID = ""; //ID of the calendar to use, e.g. "mycal". Blank (""): the current calendar 
$pageFtr = ">>#d"; //page footer template (#c: calendar title, #d: date printed, >: tab left > center > right)

//PAGE SIZE
$pSize = "A4"; //page size can be A4 or Letter

//PRINT STYLES
$fHEAD = "16"; //header font size (in pixels)
$sHEAD = ''; //header style ('' (empty): none, 'B': bold, 'I': italic)
$cHEAD = "#5862BA"; //header text color
$fNAME = "14"; //date / name font size (in pixels)
$cNAME = "#5862BA"; //day text color

/*----------------- end of default settings section -------------------*/

function makeDate($desc,$date) { //make and format birth date
	$year = preg_match('%\(((?:19|20)\d\d)\)%',$desc,$yyyy) ? $yyyy[1] : '????';
	return str_replace('9999',$year,IDtoDD('9999'.substr($date,4)));
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

//load PDF configuration
if (file_exists("./configs/".basename(__FILE__,'.php').".cnf")) { //default
	include "./configs/".basename(__FILE__,'.php').".cnf";
}
$calID = $ctuID ? $ctuID : ($_POST['calID'] ?? $dbDef); //select calendar

$dbH = dbConnect($calID); //connect to database
$set = getSettings(); //get settings from db

//load pdf class
$pdf = $_POST['pdf'] ?? '1';
require("./pdfs/pdfclassbc{$pdf}.php"); //PDF class birthday calendar

date_default_timezone_set($set['timeZone']); //set time zone

require "./lang/ui-{$_POST['uiLang']}.php"; //load language file

//set filters and get birthdays
$usr['vCats'] = $usr['eCats'] = '0';
$filter = " AND (e.`text3` LIKE '%#%#%')";
$fDate = date('Y').'-01-01';
$tDate = date('Y').'-12-31';
$evtList = []; //init
retrieve($fDate,$tDate,'',[$filter,'']); //retrieve events

//create PDF document
//header definition
$logo = file_exists($set['logoPath']) ? $set['logoPath'] : ''; //path to logo image
//footer definition
$keys = ['#c', '#d', '#n']; //possible template keys
$repl = [$set['calendarTitle'], IDtoDD(date('Y-m-d')), "#"]; //replacements
$footer = str_replace($keys,$repl,$pageFtr);
//document data
$pdf->SetTitle($set['calendarTitle'].' - Birthday Calendar');
$pdf->SetAuthor($set['calendarTitle']);
$pdf->SetSubject("Birthday Calendar");

//fill document
$pdf->SetAutoPageBreak(true,10);

for ($month = 1; $month <= 12; $month++) {
	$pdf->NextPage();
	$title = "{$xx['birthdays_in']} ".$months[$month - 1];
	$cMonth = substr('0'.$month,-2);
	$image = file_exists("./pdfs/images/{$cMonth}.png") ? "./pdfs/images/{$cMonth}.png" : '';
	$pdf->PrintMonth(); //new month
	$found = false; //init
	foreach ($evtList as $cDate => &$events) { //loop thru dates
		if (intval(substr($cDate,5,2)) === $month) {
			$found = true;
			foreach ($events as $evt) {
				if (preg_match('%#([^\d]+)(?:\(((?:19|20)[\d?]{2})\))?#%',$evt['tx3'].$evt['tx2'].$evt['tx1'],$match)) {
					$year = $match[2] ?? '????';
					$dateName = IDtoDD($year.substr($cDate,4)).'  '.trim($match[1]);
					$pdf->PrintName($dateName); //print date / name to calendar
				}
			}
		} elseif ($found) {
			break;
		}
	}
}

$pdf->Output('D',"Birthday-calendar.pdf"); //start download dialogue
?>
