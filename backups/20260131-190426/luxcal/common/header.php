<?php
/*
= Header for the LuxCal calendar pages =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//functions
function headerRss() {
	global $set, $usr, $cF;

	$httpX = (!empty($_SERVER['HTTPS']) and $_SERVER['HTTPS'] != 'off') ? 'https' : 'http'; 
	if ($usr['privs'] > 0 and $set['rssFeed']) {
		echo "<link rel='alternate' type='application/rss+xml' title='LuxCal RSS Feed' href='{$httpX}://{$_SERVER['SERVER_NAME']}".rtrim(dirname($_SERVER["PHP_SELF"]),'/')."/rssfeed.php{$cF}'>\n";
	}
}

function topBar($showDate) {
	global $xx, $hdrType, $set, $usr, $today;

	if (!isset($set['logoPath'])) { $set['logoPath'] = ''; } //needed for a smooth upgrade
	$x = $hdrType[0] == 'x' ? 'S' : 'L' ; //narrow or wide display
	$topL =	"<span class='barL{$x}'>{$set['calendarTitle']}</span>";
	if ($usr['ID'] > 1) {
		$topR = "<span class='barR{$x} navLink' onclick='showUm(`usrMenu`);'>{$usr['name']} &#9660;</span>";
	} else {
		$topR = "<span class='barR{$x} navLink' onclick='index({cP:20});'>{$xx['log_in']}</span>";
	}
	$left = '';
	if ($x == 'L' and $set['logoPath']) { //wide display and logo
		$left = "<img class='logo' src='{$set['logoPath']}' alt='logo'>"; //show logo
		if ($set['backLinkUrl']) { //make logo back link
			$left = "<a href='{$set['backLinkUrl']}' title='{$xx['hdr_button_back']}'>{$left}</a>";
		}
	}
	$topC = '&nbsp;';
	if ($showDate) {
		$dLink = $showDate === '1' ? " class='noPrint navLink' onclick='index({cD:`{$today}`});'" : '';
		$topC = "<span{$dLink}>".makeD($today,5)."</span>";
	}
	echo "<span class='fullscreen' onclick='fullscreen()' title='This page full screen'>&#x26F6;</span>\n";
	$ondrop = mayCopy() ? " ondrop='dropCopy(event)' ondragover='event.preventDefault()'" : '';
	echo "{$left}\n<div class='topBar'{$ondrop}>\n<h1>{$topL}{$topC}{$topR}</h1>\n</div>\n";
}

function sideMenu($groups) { //make hamburger menu
	global $xx, $set, $usr, $opt, $templ;

	echo "<div class='menu sideMenu noPrint' id='sideMenu'>";
	echo "<h5 class='inline noWrap'>&nbsp;{$xx['hdr_side_menu']}</h5><span class='closeX' onclick='showSm(`sideMenu`);'>&nbsp;&#10060;&nbsp;</span>\n";
	//display menu
	echo "<div class='smGroup'>\n"; //fixed group
	echo "<p title='{$xx['hdr_user_guide']}' onclick='help({$opt['cP']}); showSm(`sideMenu`);'>{$xx['hdr_button_help']}</p>\n";
	echo "<p title='{$xx['hdr_print_page']}' onclick='printNice(); showSm(`sideMenu`);'>{$xx['hdr_button_print']}</p>\n";
	if (strpos($groups,'gen')) {
		echo "<p title='{$xx['hdr_dload_pdf']}' onclick='showX(`pdfPop`,true); showSm(`sideMenu`);'>{$xx['hdr_button_pdf']}</p>\n";
		if ($set['birthdayCal'] and $templ['gen']) {
			echo "<p title='{$xx['hdr_dload_pdf_bc']}' onclick='showX(`pdfPopBc`,true); showSm(`sideMenu`);'>{$xx['hdr_button_pdf_bc']}</p>\n";
		}
	}
	echo "</div>\n";
	if (strpos($groups,'gen')) {
		echo "<div class='smGroup'>\n"; //general group
		echo "<p title='{$xx['hdr_search']}' onclick='index({cP:22});'>{$xx['hdr_button_search']}</p>\n";
		if ($usr['tnPrivs'] > '00') {
			echo "<p title='{$xx['hdr_tnails']}' onclick='index({cP:24});'>{$xx['hdr_button_tnails']}</p>\n";
		}
		if ($set['contButton']) {
			echo "<p title='{$xx['hdr_contact']}' onclick='index({cP:23});'>{$xx['hdr_button_contact']}</p>\n";
		}
		echo "</div>\n";
	}
	if (strpos($groups,'adm') and $usr['privs'] >= 4) {
		echo "<div class='smGroup'>\n"; //manager group
		echo "<p onclick='index({cP:81});'>{$xx['hdr_categories']}</p>\n";
		echo "<p onclick='index({cP:82});'>{$xx['hdr_users']}</p>\n";
		echo "<p onclick='index({cP:83});'>{$xx['hdr_groups']}</p>\n";
		echo "<p onclick='index({cP:90});'>{$xx['hdr_text_editor']}</p>\n";
		echo "<p onclick='index({cP:85});'>{$xx['hdr_import_usr']}</p>\n";
		echo "<p onclick='index({cP:86});'>{$xx['hdr_export_usr']}</p>\n";
		if ($set['msgLogging']) {
			echo "<p onclick='index({cP:92});'>{$xx['hdr_msg_log']}</p>\n";
		}
		echo "</div>\n";
	}
	if (strpos($groups,'adm') and $usr['privs'] == 9) {
		echo "<div id='admin' class='smGroup'>\n"; //admin group
		echo "<p onclick='index({cP:80});'>{$xx['hdr_settings']}</p>\n";
		echo "<p onclick='index({cP:84});'>{$xx['hdr_database']}</p>\n";
		echo "<p onclick='index({cP:87});'>{$xx['hdr_import_ics']}</p>\n";
		echo "<p onclick='index({cP:88});'>{$xx['hdr_export_ics']}</p>\n";
		echo "<p onclick='index({cP:89});'>{$xx['hdr_import_csv']}</p>\n";
		echo "<p onclick='index({cP:91});'>{$xx['hdr_clean_up']}</p>\n";
		echo "<p onclick='styleWin(99); showSm(`sideMenu`);'>{$xx['hdr_styling']}</p>\n";
		echo "</div>\n";
	}
	if (strpos($groups,'lst')) {
		echo "<div class='smGroup'>\n"; //list group
		if ($set['toapList'] and $usr['privs'] >= 4) {
			echo "<p title='{$xx['hdr_toap_list']}' onclick='showL(`toapBar`,1); showSm(`sideMenu`);'>{$xx['hdr_button_toap']}</p>\n";
		}
		if ($set['todoList']) {
			echo "<p title='{$xx['hdr_todo_list']}' onclick='showL(`todoBar`,1); showSm(`sideMenu`);'>{$xx['hdr_button_todo']}</p>\n";
		}
		if ($set['upcoList']) {
			echo "<p title='{$xx['hdr_upco_list']}' onclick='showL(`upcoBar`,1); showSm(`sideMenu`);'>{$xx['hdr_button_upco']}</p>\n";
		}
		echo "</div>\n";
	}
	if (strpos($groups,'adm') and $usr['privs'] == 9) {
		echo "<div id='admin' class='smGroup'>\n"; //admin group
		echo "<p onclick='showAbout(); showSm(`sideMenu`);'>{$xx['hdr_about_lc']}</p>\n";
		echo "</div>\n";
	}
	echo "</div>\n";
}

function pdfDialog() {
	global $calID, $xx, $set, $usr, $opt, $today, $nowTS;
	
	$pdfJson = json_encode(['calID' => $calID, 'uID' => $usr['ID'], 'lang' => $opt['cL'], 'users' => implode(',',$opt['cU']), 'groups' => implode(',',$opt['cG']), 'cats' => implode(',',$opt['cC'])]); //json encode object
	echo "\n<div id='pdfPop' class='dialogBox'>
<fieldset>\n<legend>PDF - {$xx['title_upcoming']}</legend>
<form action='pdfs/pdf.php' method='post'>
<input type='hidden' name='pdfJson' value='{$pdfJson}'>
<label><input type='radio' name='pdf' value='1' checked>{$xx['portrait']}</label>&emsp;
<label><input type='radio' name='pdf' value='2'>{$xx['landscape']}</label><br><br>
{$xx['from']}: <input class='date' type='text' name='fDate' id='fDate' value=".IDtoDD($today).">
<span class='dtPick' onclick='dPicker(1,``,`fDate`); return false;'>&#x1F4C5;</span>&emsp;
{$xx['to']}: <input class='date' type='text' name='tDate' id='tDate' value=".IDtoDD(date('Y-m-d',$nowTS + ($set['lookaheadDays'] * 86400))).">
<span class='dtPick' onclick='dPicker(1,``,`tDate`); return false;'>&#x1F4C5;</span>
<br><br>
<button type='submit' class='bold' onclick='showX(`pdfPop`,false);'>&nbsp;OK&nbsp;</button>&emsp;
<button type='button' onclick='showX(`pdfPop`,false);'>Cancel</button>
</form></fieldset></div>";
	echo "\n<div id='pdfPopBc' class='dialogBox'>
<fieldset>\n<legend>PDF - {$xx['title_bd_calendar']}</legend>
<form action='pdfs/pdfbc.php' method='post'>
<input type='hidden' name='calID' value='{$calID}'>
<input type='hidden' name='uiLang' value='{$opt['cL']}'>
<label><input type='radio' name='pdf' value='1' checked>{$xx['portrait']}</label>&emsp;
<label><input type='radio' name='pdf' value='2'>{$xx['landscape']}</label>
<br><br>
<button type='submit' class='bold' onclick='showX(`pdfPopBc`,false);'>&nbsp;OK&nbsp;</button>&emsp;
<button type='button' onclick='showX(`pdfPopBc`,false);'>Cancel</button>
</form></fieldset></div>";
}

function calButton () {
	global $xx, $usr;

	if ($usr['privs'] > 0) { //view rights
		echo "<button type='button' title='{$xx['hdr_back_to_cal']}' onclick='index({cP:0});'>{$xx['hdr_calendar']}</button>\n";
	}
}

function addButton() {
	global $xx, $usr;

	if ($usr['privs'] > 1) { //post rights
		echo "<button type='button' title='{$xx['hdr_add_event']}' onclick='newE(0);'>{$xx['hdr_button_add']}</button>\n";
	}
}

function srcButton () {
	global $xx;

	echo "<button type='button' title='{$xx['hdr_search']}' onclick='index({cP:22});'>&#x1f50d;</button>\n";
}

function prtButton () {
	global $xx;

	echo "<button type='button' title='{$xx['hdr_print_page']}' onclick='printNice();'>{$xx['hdr_button_print']}</button>\n";
}

function hlpButton($cPage) {
	global $xx;

	echo "<button type='button' title='{$xx['hdr_user_guide']}' onclick='help({$cPage});'>{$xx['hdr_button_help']}</button>\n";
}

function menButton() {
	global $xx;

		echo "<button type='button' title='{$xx['hdr_open_menu']}' onclick='showSm(`sideMenu`)'>&nbsp;&#9776;&nbsp;</button>\n";
}

function urlButton() {
	global $xx, $set;

	if ($set['backLinkUrl'] and !$set['logoPath']) { //if no logo, display button
		echo "<button id='urlButton' type='button' title='{$xx['hdr_button_back']}' onclick='location.href=`{$set['backLinkUrl']}`;'>{$xx['back']}</button>&emsp;\n";
	}
}

function optButton() {
	global $options, $xx;

	if ($options) { //menus
		echo "<button type='button' class='optBut' id='optButton' title='{$xx['hdr_options_panel']}' onclick='toggleLabel(`optButton`,`{$xx['options']}`,`{$xx['done']}`); showOp(`optMenu`,`optMenu`)'>{$xx['options']}</button>\n";
	}
}

function nbCenter() {
	global $options, $xx;

	echo "<div ".($options ? "class='noPrint' onclick='toggleLabel(`optButton`,`{$xx['options']}`,`{$xx['done']}`); showOp(`optMenu`,`optMenu`)'" : '').">&nbsp;</div>\n";
}


function viewButtons() {
	global $xx, $set, $usr, $winXS;

	if ($winXS) {
		$viewButtons = $usr['ID'] == 1 ? $set['viewButsPubS'] : $set['viewButsLogS']; //view buttons to display - small display
	} else {
		$viewButtons = $usr['ID'] == 1 ? $set['viewButsPubL'] : $set['viewButsLogL']; //view buttons to display - large display
	}
	if ($viewButtons) {
		foreach (explode(',',$viewButtons) as $viewNr) {
			$label = $xx["hdr_view_{$viewNr}"];
			echo "<button type='button' title='{$xx['hdr_go_to_view']}' onclick='index({cP:{$viewNr}})'>{$label}</button>\n";
		}
	}
	unset($viewButtons,$label);
}

function dateForm() {
	global $xx, $opt;

	echo "<form class='inline' id='gotoD' method='post'>
<input class='date' type='text' name='nD' id='nD' value='".IDtoDD($opt['cD'])."'><span class='dtPick' title='{$xx['hdr_select_date']}' onclick='dPicker(0,`gotoD`,`nD`); return false;'>&#x1F4C5;</span>
</form>\n";
}

function usrMenu() { //make user menu
	global $xx, $hdrType;

	$x = $hdrType[0] == 'x' ? 'S' : 'L' ; //narrow or wide display
	echo "<div class='menu usrMenu{$x}' id='usrMenu'>
<div class='umGroup'>
<p onclick='index({cP:0,loff:1});'>{$xx['log_out']}</p>
<p onclick='index({cP:21});'>{$xx['title_profile']}</p>
</div>
</div>\n";
}

function optMenu() { //make options panel
	global $options, $xx, $set, $calID, $calIDs, $usr, $opt, $avViews;

	if (!$options) { return; } //no menus
	
	echo "<div class='menu optMenu noPrint' id='optMenu'>
<h3 class='floatC' onclick='showOp(`optMenu`,`optMenu`)'>{$xx['hdr_options_submit']}</h3>
<form id='optForm' name='optMenu' method='post'>\n";
	if ($set['calMenu'] and $usr['privs'] == 9 and count($calIDs) > 1) { //show column with cal IDs
		echo "<div class='option'>\n<div class='optHead'>{$xx['hdr_calendar']}</div>\n<div class='optList'>\n";
		foreach ($calIDs as $cal) {
			$checked = ($calID == $cal) ? " checked" : '';
			echo "<label><input type='checkbox' name='cal' value='{$cal}' onclick='check1(`cal`,this,1);'{$checked}>{$cal}</label><br>\n";
		}
		echo "</div>\n</div>\n";
	}
	if ($set['viewMenu']) {
		$checkedA = array_fill(1,11,'');
		$checkedA[$opt['cP']] = " checked";
		echo "<div class='option'>\n<div class='optHead'>{$xx['hdr_view']}</div>\n<div class='optList'>";
		foreach (explode(',',$avViews) as $v) {
			$vLabel = $xx["hdr_view_{$v}"];
			echo "<label><input type='checkbox' name='cP' value='{$v}' onclick='check1(`cP`,this,1);'{$checkedA[$v]}>{$vLabel}</label><br>\n";
		}
		echo "</div>\n</div>\n";
	}
	if ($set['groupMenu']) {
		echo "<div class='option'>\n<div class='optHead'>{$xx['hdr_groups']}</div>\n<div class='optList'>\n";
		$stH = dbQuery("SELECT `ID`,`name`,`color` FROM `groups` WHERE `status` >= 0 ORDER BY `name`");
		$checked = in_array(0, $opt['cG']) ? " checked" : '';
		echo "<label><input type='checkbox' name='cG[]' value='0' onclick='check0(`cG`);'{$checked}>{$xx['hdr_all_groups']}</label><br>\n";
		while (list($xgID,$gName,$color) = $stH->fetch(PDO::FETCH_NUM)) {
			$checked = in_array($xgID, $opt['cG']) ? " checked" : '';
			$groupColor = ($color) ? " style='background-color:{$color};'" : '';
			echo "<label{$groupColor}><input type='checkbox' name='cG[]' value='{$xgID}' onclick='checkN(`cG`);'{$checked}>{$gName}</label><br>\n";
		}
		echo "</div>\n</div>\n";
	}
	if ($set['userMenu'] and $usr['ID'] > 1) {
		echo "<div class='option'>\n<div class='optHead'>{$xx['hdr_users']}</div>\n<div class='optList'>\n";
		$stH = dbQuery("SELECT u.`ID`,u.`name`,g.`color` FROM `users` AS u INNER JOIN `groups` AS g ON g.`ID` = u.`groupID` WHERE u.`status` >= 0 ORDER BY u.`name`");
		$checked = in_array(0, $opt['cU']) ? " checked" : '';
		echo "<label><input type='checkbox' name='cU[]' value='0' onclick='check0(`cU`);'{$checked}>{$xx['hdr_all_users']}</label><br>\n";
		while (list($xuID,$uName,$color) = $stH->fetch(PDO::FETCH_NUM)) {
			$checked = in_array($xuID, $opt['cU']) ? " checked" : '';
			$userColor = ($color) ? " style='background-color:{$color};'" : '';
			echo "<label{$userColor}><input type='checkbox' name='cU[]' value='{$xuID}' onclick='checkN(`cU`);'{$checked}>{$uName}</label><br>\n";
		}
		echo "</div>\n</div>\n";
	}
	if ($set['catMenu']) {
		echo "<div class='option'>\n<div class='optHead'>{$xx['hdr_categories']}</div>\n<div class='optList'>\n";
		$where = ' WHERE `status` >= 0'.($usr['vCats'] != '0' ? " AND `ID` IN ({$usr['vCats']})" : '');
		$stH = dbQuery("SELECT `ID`,`name`,`color`,`bgColor` FROM `categories`".$where." ORDER BY `sequence`");
		$checked = in_array(0, $opt['cC']) ? " checked" : '';
		echo "<label><input type='checkbox' name='cC[]' value='0' onclick='check0(`cC`);'{$checked}>{$xx['hdr_all_cats']}</label><br>\n";
		while (list($xC,$cName,$color,$bgColor) = $stH->fetch(PDO::FETCH_NUM)) {
			$checked = in_array($xC, $opt['cC']) ? " checked" : '';
			$catColor = ($color ? "color:{$color};" : '').($bgColor ? "background-color:{$bgColor};" : '');
			echo "<label".($catColor ? " style='".$catColor."'" : "")."><input type='checkbox' name='cC[]' value='{$xC}' onclick='checkN(`cC`);'{$checked}>{$cName}</label><br>\n";
		}
		echo "</div>\n</div>\n";
	}
	if ($set['langMenu']) {
		echo "<div class='option'>\n<div class='optHead'>{$xx['hdr_lang']}</div>\n<div class='optList'>\n";
		$files = preg_grep("~^ui-[a-z]+\.php$~",scandir("lang/"));
		foreach ($files as $k => $file) {
			$lang = strtolower(substr($file,3,-4));
			$checked = ($opt['cL'] == $lang) ? " checked" : '';
			echo "<label><input type='checkbox' name='cL' value='{$lang}' onclick='check1(`cL`,this,1);'{$checked}>".ucfirst($lang)."</label><br>\n";
		}
		echo "</div>\n</div>\n";
	}
	echo "</form>\n</div>\n";
}

function toapList() { //make list with events to be approved
	global $xx, $set, $opt, $evtList;
	
	echo "<div class='toapBar' id='toapBar'>
<div class='barTop move' onmousedown='dragMe(`toapBar`,event)'>{$xx['hdr_toap_list']}<span class='closeX' onclick='showL(`toapBar`,0)'>&nbsp;&#10060;&nbsp;</span></div>\n";
	$curT = strtotime($opt['cD'].' 12:00:00'); //current Unix time
	$startD = date("Y-m-d", $curT - (7 * 86400)); //current date - 1 week
	$endD = date("Y-m-d", $curT + (($set['lookaheadDays']-1) * 86400)); //current date + look ahead nr of days
	$filter = ' AND (c.`approve` = 1 AND e.`approved` = 0)'; //events in cat to be approved but not yet approved
	retrieve($startD,$endD,'guc',[$filter,'']);

	echo '<h5 class="floatC">'.IDtoDD($startD).' - '.IDtoDD($endD)."</h5>\n";
	//display list
	echo "<div class='barBody'>\n";
	if ($evtList) {
		$evtDone = [];
		$lastDate = '';
		foreach($evtList as $date => &$events) {
			foreach ($events as $evt) {
				if (!$evt['mde'] or !in_array($evt['eid'],$evtDone)) { //!mde or mde not processed
					$evtDone[] = $evt['eid'];
					$evtDate = $evt['mde'] ? makeD($evt['sda'],5)." - ".makeD($evt['eda'],5) : makeD($date,5);
					$evtTime = makeTime($evt['ald'],0,0,$evt['sti'],$evt['eti']);
					$onClick = " onclick='editE({$evt['eid']},`{$date}`);'";
					$eStyle = colorStyle($evt); //get event colors
					$eStyle = $eStyle ? " style='{$eStyle}'" : '';
					echo $lastDate != $evtDate ? "<h5>{$evtDate}</h5>\n" : '';
					echo "<p>{$evtTime}</p>\n";
					echo "<p{$onClick}{$eStyle}>&emsp;{$evt['tit']}</p><br>\n";
					$lastDate = $evtDate;
				}
			}
		}
	} else {
		echo $xx['none']."\n";
	}
	echo "</div>\n</div>\n";
}

function todoList() { //make list with todo events
	global $xx, $set, $opt, $evtList, $templ;
	
	echo "<div class='todoBar' id='todoBar'>
<div class='barTop move' onmousedown='dragMe(`todoBar`,event)'>{$xx['hdr_todo_list']}<span class='closeX' onclick='showL(`todoBar`,0)'>&nbsp;&#10060;&nbsp;</span></div>\n";
	$curT = strtotime($opt['cD'].' 12:00:00'); //current Unix time
	$startD = date("Y-m-d", $curT - ($set['lookbackDays'] * 86400)); //current date - 1 month
	$endD = date("Y-m-d", $curT + (($set['lookaheadDays']-1) * 86400)); //current date + look ahead nr of days
	$filter = 'AND (c.`checkBx` = 1)'; //events in cat with a check mark
	retrieve($startD,$endD,'guc',[$filter,'']);

	echo '<h5 class="floatC">'.IDtoDD($startD).' - '.IDtoDD($endD)."</h5>\n";
	//display list
	echo "<div class='barBody'>\n";
	if ($evtList) {
		foreach($evtList as $date => &$events) {
			$dShown = 0;
			foreach ($events as $evt) {
				if (strpos($evt['chd'],$date)) { continue; } //flush completed events
				if (!$dShown) {
					echo "<h5>".makeD($date,5)."</h5>\n";
					$dShown = 1;
				}
				$evtTime = makeTime($evt['ald'],0,0,$evt['sti'],$evt['eti']);
				$click = ($evt['mayE'] ? 'editE' : 'showE')."({$evt['eid']},`{$date}`)";
				$onClick = ($templ['gen'] or $evt['mayE']) ? " onclick='{$click};'" : " class='arrow'";
				$eStyle = colorStyle($evt); //get event colors
				$eStyle = $eStyle ? " style='{$eStyle}'" : '';
				$chBox = $evt['cbx'] ? checkBox($evt,$date) : '';
				echo "<p>{$evtTime}</p>\n";
				echo "<p{$onClick}{$eStyle}>{$chBox}{$evt['tit']}</p><br>\n";
			}
		}
	} else {
		echo $xx['none']."\n";
	}
	echo "</div>\n</div>\n";
}

function upcoList() { //make list with upcoming events
	global $xx, $set, $opt, $evtList, $templ;

	echo "<div class='upcoBar' id='upcoBar'>
<div class='barTop move' onmousedown='dragMe(`upcoBar`,event)'>{$xx['hdr_upco_list']}<span class='closeX' onclick='showL(`upcoBar`,0)'>&nbsp;&#10060;&nbsp;</span></div>\n";
	$startD = $opt['cD'];
	$eTime = strtotime($startD.' 12:00:00') + (($set['lookaheadDays']-1) * 86400); //Unix time of end date
	$endD = date("Y-m-d", $eTime);
	retrieve($startD,$endD,'guc');

	echo '<h5 class="floatC">'.IDtoDD($startD).' - '.IDtoDD($endD)."</h5>\n";
	//display events
	echo "<div class='barBody'>\n";
	if ($evtList) {
		$evtDone = [];
		$lastDate = '';
		foreach($evtList as $date => &$events) {
			foreach ($events as $evt) {
				if (!$evt['mde'] or !in_array($evt['eid'],$evtDone)) { //!mde or mde not processed
					$evtDone[] = $evt['eid'];
					$evtDate = $evt['mde'] ? makeD($evt['sda'],5)." - ".makeD($evt['eda'],5) : makeD($date,5);
					$evtTime = makeTime($evt['ald'],0,0,$evt['sti'],$evt['eti']);
					$click = ($evt['mayE'] ? 'editE' : 'showE')."({$evt['eid']},`{$date}`)";
					$onClick = ($templ['gen'] or $evt['mayE']) ? " onclick='{$click};'" : " class='arrow'";
					$eStyle = colorStyle($evt); //get event colors
					$eStyle = $eStyle ? " style='{$eStyle}'" : '';
					echo $lastDate != $evtDate ? "<h5>{$evtDate}</h5>\n" : '';
					echo "<p>{$evtTime}</p>\n";
					echo "<p{$onClick}{$eStyle}>&emsp;{$evt['tit']}</p><br>\n";
					$lastDate = $evtDate;
				}
			}
		}
	} else {
		echo $xx['none']."\n";
	}
	echo "</div>\n</div>\n";
}

function mayCopy() {
	global $usr, $opt, $calIDs;
	
	return ($usr['privs'] >= 4 and ($opt['cP'] > 0 and $opt['cP'] < 4) and count($calIDs) > 1);
}


function calDropList() { //make destination calendar drop list
	global $xx, $calIDs, $calID;
	
	if (mayCopy()) { //admin
		echo "\n<div id='calList' class='dialogBox'>
<fieldset>\n<legend>{$xx['hdr_dest_cals']}</legend>
<p class='floatC'>&nbsp;</p>\n";
		foreach ($calIDs as $cal) {
			if ($calID !== $cal) {
				echo "<div><label><input type='checkbox' value='{$cal}'>{$cal}</label></div>\n";
			}
		}
		echo "<br>
<button type='submit' class='bold' onclick='copy2Cals()'>{$xx['hdr_copy_evt']}</button>&emsp;
<button type='button' onclick='showX(`calList`);'>{$xx['evt_close']}</button>
</fieldset>
</div>\n";
	}
}

//start of HTML header
$cssX = isset($_SESSION[$calID]['theme']) ? "-{$nowTS}" : ''; //?pv: force reload of styles
$version = LCV;
$cid = count($opt['cC']) == 1 ? $opt['cC'][0] : 0;
$options = (($set['calMenu'] and $usr['privs'] == 9) or $set['viewMenu'] or $set['groupMenu'] or $set['userMenu'] or $set['catMenu'] or $set['langMenu']) ? true : false; //menus
echo "<!DOCTYPE html>
<html lang='{$isocode}'>\n";
echo <<<TXT
<!--     ____   ______                                   _ __
  ____ _/ / /  / ____/ _____    ____     _____ ___ ___  (_) /___
 / __ `/ / /  /_/ __ \/ ___/  / __ `/   / ___/ __ `__ \/ / / __ \
/ /_/ / / /  / / /_/ / /     / /_/ /   (__  ) / / / / / / / /___/
\__,_/_/_/  /_/\____/_/      \__,_/   /____/_/ /_/ /_/_/_/\____/

-->
<head>
<meta charset="utf-8">
<title>{$set['calendarTitle']}</title>
<meta name="description" content="LuxCal web calendar - a LuxSoft product">
<meta name="application-name" content="LuxCal V{$version}">
<meta name="author" content="Roel Buining">
<meta name="robots" content="nofollow">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="tkn" content="{$tkn}">
<link rel="icon" type="image/png" href="lcal.png">
<link rel="stylesheet" type="text/css" href="css/css.php?v={$version}{$cssX}">
<script src='common/toolbox.js?v={$version}'></script>
<script>
const uName = "{$usr['name']}", calID = "{$calID}", cPage = "{$opt['cP']}", cid = {$cid}, mode = "{$mode}";
const tFormat = "{$set['timeFormat']}", dFormat = "{$set['dateFormat']}", wStart = {$set['weekStart']}, dwStartH = {$set['dwStartHour']}, dwEndH = {$set['dwEndHour']};
const dpToday = "{$xx['hdr_today']}", dpClear = "{$xx['hdr_clear']}";
const tnNote = "{$xx['hdr_tn_note']}";
TXT;
echo "
const dpMonths = ['",implode("','",$months),"'];
const dpWkdays = ['",implode("','",$wkDays_m),"'];\n";
if (strpos('~0fax',$hdrType[0])) {
	$limit = $set['maxXsWidth'] ?? 500;
	echo "if (winNar({$limit})) { location.reload(); }\n";
}
echo "</script>\n";

switch ($hdrType[0]) { //header types - 0: no, f: full, a: admin, l: login, m: mobile, s: styling, e: event, h: help
	case '0': //no header (hdr=0)
		echo <<<TXT
</head>\n
<body>
<div class='contentN'>\n
TXT;
		if ($pageTitle) echo "<br><h2 class='pageTitle'>{$pageTitle}</h2>\n";
		break;
	case 'f': //calendar view pages
		headerRss();
		echo <<<TXT
<script async src="common/dtpicker.js"></script>
</head>\n
<body onload="scrollV({cP:{$opt['cP']},action:'goto'}); initCal();" onunload="scrollV({cP:{$opt['cP']},action:'save'});">\n
TXT;
		topBar($set['topBarDate']);
		if ($usr['privs'] > 0) { //view rights
			echo "<div class='navBar ".($set['logoPath'] ? 'lPadXL' : 'xPadXS')." noPrint'>\n";
			echo "<span class='floatR'>\n";
			addButton();
			srcButton();
			menButton();
			echo "</span>\n";
			echo "<span class='floatL'>\n";
			urlButton();
			optButton();
			viewButtons();
			dateForm();
			echo "</span>\n";
			nbCenter();
			echo "</div>\n";
			optMenu();
			usrMenu();
			if (($set['toapList'] and $usr['privs'] >= 4) or $set['todoList'] or $set['upcoList']) {
				sideMenu('~gen~adm~lst');
				if ($set['toapList'] and $usr['privs'] >= 4) { toapList(); } //manager+ events to be approved list
				if ($set['todoList']) { todoList(); } //todo list
				if ($set['upcoList']) { upcoList(); } //upcoming events list
			} else {
				sideMenu('~gen~adm');
			}
			pdfDialog();
			calDropList();
		} else { //display dummy navbar
			echo <<<TXT
<div class='navBar noPrint'>&nbsp;</div>\n
TXT;
		}
		echo "<div class='content'>\n";
		//side panel
		$regex = "~(^|,){$opt['cP']}($|,)~";
		$spItems =
			(($set['spMiniCal'] == '0' or preg_match($regex,$set['spMiniCal'])) ? '1' : '0').
			(($set['spImages'] == '0' or preg_match($regex,$set['spImages'])) ? '1' : '0').
			(($set['spInfoArea'] == '0' or preg_match($regex,$set['spInfoArea'])) ? '1' : '0');
		if ($usr['privs'] > 0 and $spItems !== '000' and !$winXS) { //show side panel
			$tcDate = $set['spDateFixed'] ? time() : strtotime($opt['cD'].' 12:00:00'); //Unix time for side panel
			showSidePanel($tcDate,$spItems);
			echo "<div class='container'>\n";
		}
		if ($pageTitle) echo "<br><h2 class='pageTitle'>{$pageTitle}</h2>\n";
		break;
	case 'a': //admin pages
		echo <<<TXT
<script async src="common/dtpicker.js"></script>
<script async src="common/jscolor.js"></script>
</head>\n
<body onload="scrollV({cP:{$opt['cP']},action:'goto'});" onunload="scrollV({cP:{$opt['cP']},action:'save'});">\n
TXT;
		topBar(true);
		echo "<div class='navBar ".($set['logoPath'] ? 'lPadXL' : 'xPadXS')." noPrint'>\n";
		echo "<span class='floatR'>\n";
		calButton();
		hlpButton($opt['cP']);
		menButton();
		echo "</span>\n";
		echo "<span class='floatL'>\n";
		optButton();
		echo "<span class='pTitleAdm'>{$pageTitle}</span>\n";
		echo "</span>\n";
		nbCenter();
		echo "</div>\n";
		optMenu();
		usrMenu();
		sideMenu('~adm');
		$scrAuto = (strlen($hdrType) > 1 and $hdrType[1] == '+') ? '' : ' scrAuto'; //settings
		echo "<div class='content{$scrAuto}'>\n<br>\n";
		break;
	case 's': //styling window
		echo <<<TXT
<script async src="common/jscolor.js"></script>
</head>\n
<body>\n
TXT;
		echo "<div class='barTop floatC noPrint'>
<span class='floatL'>{$pageTitle}</span>
<span class='floatR'>\n";
		prtButton();
		hlpButton($opt['cP']);
		echo "</span>
{$set['calendarTitle']}
</div>\n";
		echo "<div class='content scrAuto'>\n";
		break;
	case 'l': //log in page
		echo <<<TXT
</head>\n
<body>\n
TXT;
		topBar(true);
		echo "<div class='navBar ".($set['logoPath'] ? 'lPadXL' : 'xPadXS')."'>\n";
		echo "<span class='floatR'>\n";
		calButton();
		hlpButton($opt['cP']);
		menButton();
		echo "</span>\n";
		echo "<span class='pTitleAdm'>{$pageTitle}</span>\n";
		echo "</div>\n";
		usrMenu();
		sideMenu('~');
		echo "<div class='content scrAuto'>\n<br>\n";
		break;
	case 'x': //calendar pages - xs display/window
		echo <<<TXT
<script async src="common/dtpicker.js"></script>
</head>\n
<body>\n
TXT;
		topBar(false);
		if ($usr['privs'] > 0) { //view rights
			echo "<div class='navBar noPrint'>\n";
			echo "<span class='floatR'>\n";
			addButton();
			srcButton();
			menButton();
			echo "</span>\n";
			urlButton();
			optButton();
			viewButtons();
			dateForm();
			echo "</div>\n";
			optMenu();
			usrMenu();
			sideMenu('~gen~adm');
			pdfDialog();
		} else { //display dummy navbar
			echo <<<TXT
<div class='navBar noPrint'>&nbsp;</div>\n
TXT;
		}
		echo "<div class='content'>\n";
		if ($pageTitle) echo "<br><h2 class='pageTitle'>{$pageTitle}</h2>\n";
		break;
	case 'e': //event window
		echo <<<TXT
<script async src="common/dtpicker.js"></script>
<script async src="common/jscolor.js"></script>
TXT;
		if ($set['emojiPicker']) {
		echo <<<TXT
\n<script src='common/empicker.js?v={$version}'></script>
<script src='common/emojis.js?v={$version}'></script>
TXT;
}
		echo <<<TXT
\n<script>
window.onload = function() {winFit();}
window.onkeyup = function (event) {if (event.keyCode==27) {window.close();}}
</script>
</head>\n
<body>\n
TXT;
		echo "<div class='barTop floatC noPrint'>&ensp;\n";
		if ($set['emojiPicker']) {
			echo "<span class='emoButton' title='emojis'>😀</span>\n";
		}
		echo "<span class='floatR'>\n";
		prtButton();
		hlpButton($opt['cP']);
		echo "</span>\n";
		$eState = empty($state) ? '' : ($state[0] == 'a' ?  " - {$xx['evt_add']}" : " - {$xx['evt_edit']}");
		echo "<span class='floatL'>{$pageTitle}{$eState}</span>\n";
		echo "</div>\n";
		echo "<div class='contentE'>\n";
		break;
	case 'h': //help window
		echo <<<TXT
</head>\n
<body>
<div class='barTop'>
<span class='floatR select' onclick="self.close();">&nbsp;&#10060;&nbsp;</span>&nbsp;
{$pageTitle}
</div>
<div class='contentH'>\n
TXT;
}
unset($version);
unset($hdrType);
?>
