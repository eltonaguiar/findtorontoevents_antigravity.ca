<?php
/*
= LuxCal database management page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$adminLang = (file_exists("./lang/ai-{$opt['cL']}.php")) ? $opt['cL'] : "english";
require "./lang/ai-{$adminLang}.php";
require './common/toolboxx.php'; //admin tools

function showDbCount() {
	global $ax, $nowTS;

	echo "<fieldset>\n
<legend>{$ax['mdb_db_content']}</legend>\n
<table class='dbContent'>\n";
	$stH = dbQuery("SELECT COUNT(*) FROM `events` WHERE `status` >= 0",0);
	$count = $stH->fetch(PDO::FETCH_NUM);
	echo "<tr><td>{$ax['mdb_total_evenst']}:</td><td><b>{$count[0]}</b></td></tr>\n";
	$dLimit = date('Y-m-d',$nowTS - 86400*30); //1 month ago
	$where = "(SELECT `repeat` FROM `categories` AS cat WHERE cat.`ID` = `catID`) = 0 AND (CASE WHEN `rType` > 0 THEN `rUntil` ELSE CASE WHEN `eDate` LIKE '9%' THEN `sDate` ELSE `eDate` END END <= '$dLimit')";
	$stH = dbQuery("SELECT COUNT(*) FROM `events` WHERE `status` >= 0 AND $where",0);
	$count = $stH->fetch(PDO::FETCH_NUM);
	echo "<tr><td>{$ax['mdb_evts_older_1m']}:</td><td><b>{$count[0]}</b></td></tr>\n";
	if ($count[0]) {
		$dLimit = date('Y-m-d',$nowTS - 86400*183); //6 month ago
		$where = "(SELECT `repeat` FROM `categories` AS cat WHERE cat.`ID` = `catID`) = 0 AND (CASE WHEN `rType` > 0 THEN `rUntil` ELSE CASE WHEN `eDate` LIKE '9%' THEN `sDate` ELSE `eDate` END END <= '$dLimit')";
		$stH = dbQuery("SELECT COUNT(*) FROM `events` WHERE `status` >= 0 AND $where",0);
		$count = $stH->fetch(PDO::FETCH_NUM);
		echo "<tr><td>{$ax['mdb_evts_older_6m']}:</td><td><b>{$count[0]}</b></td></tr>\n";
	}
	if ($count[0]) {
		$dLimit = date('Y-m-d',$nowTS - 86400*365); //1 year ago
		$where = "(SELECT `repeat` FROM `categories` AS cat WHERE cat.`ID` = `catID`) = 0 AND (CASE WHEN `rType` > 0 THEN `rUntil` ELSE CASE WHEN `eDate` LIKE '9%' THEN `sDate` ELSE `eDate` END END <= '$dLimit')";
		$stH = dbQuery("SELECT COUNT(*) FROM `events` WHERE `status` >= 0 AND $where",0);
		$count = $stH->fetch(PDO::FETCH_NUM);
		echo "<tr><td>{$ax['mdb_evts_older_1y']}:</td><td><b>{$count[0]}</b></td></tr>\n";
	}
	$stH = dbQuery("SELECT COUNT(*) FROM `events` WHERE `status` < 0",0);
	$count = $stH->fetch(PDO::FETCH_NUM);
	echo "<tr><td>{$ax['mdb_evts_deleted']}:</td><td><b>{$count[0]}</b>&emsp;({$ax['mdb_not_removed']})</td></tr>\n";
	$stH = dbQuery("SELECT COUNT(*) FROM `categories` WHERE `status` >= 0",0);
	$count = $stH->fetch(PDO::FETCH_NUM);
	echo "<tr><td>{$ax['mdb_total_cats']}:</td><td><b>{$count[0]}</b></td></tr>\n";
	$stH = dbQuery("SELECT COUNT(*) FROM `users` WHERE `status` >= 0",0);
	$count = $stH->fetch(PDO::FETCH_NUM);
	echo "<tr><td>{$ax['mdb_total_users']}:</td><td><b>{$count[0]}</b></td></tr>\n";
	$stH = dbQuery("SELECT COUNT(*) FROM `groups` WHERE `status` >= 0",0);
	$count = $stH->fetch(PDO::FETCH_NUM);
	echo "<tr><td>{$ax['mdb_total_groups']}:</td><td><b>{$count[0]}</b></td></tr>\n";
	echo "</table>
</fieldset>\n";
	$stH = null;
}

function mdbForm() {
	global $formCal, $ax, $compact, $export, $import, $events, $delEvt, $fromD, $tillD;
	
	$comChecked = $compact > 0 ? " checked" : '';
	$expChecked = $export > 0 ? " checked" : '';
	$impChecked = $import > 0 ? " checked" : '';
	$evtChecked = $events > 0 ? " checked" : '';
	$delChecked = $delEvt > 0 ? " checked" : '';
	$undChecked = !$delEvt > 0 ? " checked" : '';
	echo "<form action='index.php' method='post' enctype='multipart/form-data'>
{$formCal}
<input type='hidden' name='MAX_FILE_SIZE' value='2050000'>
<fieldset>\n
<legend>{$ax['mdb_dbm_functions']}</legend>\n
<label><input type='checkbox' name='compact' value='yes'{$comChecked}> {$ax['mdb_compact']}</label><br>
<br><label><input type='checkbox' name='export' value='yes'{$expChecked}> {$ax['mdb_backup']}</label><br>
<br><label><input type='checkbox' name='import' value='yes'{$impChecked}> {$ax['mdb_restore']}</label>&emsp;
<label>{$ax['iex_file']}:</label> <input type='file' name='fName'><br><br>
<label><input type='checkbox' name='events' value='yes'{$evtChecked}> {$ax['mdb_events']}</label>:&emsp;
<label><input type='radio' name='delEvt' value='1'{$delChecked}> {$ax['mdb_delete']}</label>&emsp;
<label><input type='radio' name='delEvt' value='0'{$undChecked}> {$ax['mdb_undelete']}</label>\n<br>
&emsp;&emsp;{$ax['mdb_between_dates']}: <input class='date' type='text' name='fromD' id='fromD' value='".IDtoDD($fromD)."' maxlength='10'>
<span class='dtPick' title=\"{$ax['iex_select_start_date']}\" onclick='dPicker(1,``,`fromD`);return false;'>&#x1F4C5;</span> &#8211;
<input class='date' type='text' name='tillD' id='tillD' value='".IDtoDD($tillD)."' maxlength='10'>
<span class='dtPick' title=\"{$ax['iex_select_end_date']}\" onclick='dPicker(1,``,`tillD`);return false;'>&#x1F4C5;</span>
<br><br>
<button class='center' type='submit' name='exe' value='y'>{$ax['mdb_start']}</button>\n
</fieldset>\n
</form>\n";
}

function processFunctions() {
	global $formCal, $ax, $compact, $export, $import, $events, $delEvt, $fromD, $tillD;
	
	$fName = false;
	if ($compact) { compactDb(); }
	if ($export) { $fName = exportTables(); }
	if ($import) { importTables(); }
	if ($events) { delEvents($delEvt, $fromD, $tillD); }
	echo "<form action='index.php' method='post'>
{$formCal}
<input type='hidden' name='compact' id='compact' value='{$compact}'>
<input type='hidden' name='export' id='export' value='{$export}'>
<input type='hidden' name='import' id='import' value='{$import}'>
<input type='hidden' name='events' id='events' value='{$events}'>
<input type='hidden' name='delEvt' id='delEvt' value='{$delEvt}'>
<input type='hidden' name='fromD' id='fromD' value='".IDtoDD($fromD)."'>
<input type='hidden' name='tillD' id='tillD' value='".IDtoDD($tillD)."'>
<button type='submit' name='back' value='y'>{$ax['back']}</button>\n";
	if ($fName) {
		echo "&emsp;<button type='button' onclick='location.href=`dloader.php?ftd=./files/{$fName}`;'>{$ax['iex_download_file']}</button>\n";
	}
	echo "</form>\n";
}


/* Compact database */
function compactDb() {
	global $ax, $dbType, $nowTS;
	
	echo "<fieldset><legend>{$ax['mdb_compact']}</legend>\n";
	$deleteDT = date('Y-m-d H:i', $nowTS - 86400*30); //remove if deleted more than 30 days ago
	//remove deleted events from db
	$stH = dbQuery("DELETE FROM `events` WHERE `status` = -1 AND `mDateTime` <= '{$deleteDT}'");
	echo "{$ax['mdb_purge_done']}.<br>\n";		
	if ($dbType == 'SQLite') { //SQLite db
		$stH = dbQuery("VACUUM");
	} else { //MySQL db
		$stH = dbQuery('OPTIMIZE TABLE `'.implode('`,`',getTables()).'`');
	}
	if ($stH) {
		echo "{$ax['mdb_compact_done']}.<br>\n";		
	} else {
		echo "{$ax['mdb_compact_error']}.<br>\n";
	}
	echo "</fieldset>\n";
}

/* Export db tables*/
function exportTables() {
	global $ax, $calID, $lcV;
	
	echo "<fieldset><legend>{$ax['mdb_backup']}</legend>\n";
	//get table names
	$tables = getTables();
	if (empty($tables)) {
		echo "{$ax['mdb_noshow_tables']}\n";
		$result = false;
	} else {
		$sqlFile = exportSqlFile($tables,true); //export to SQL file
		//save .sql dump file
		$fName = "./files/dump-{$calID}-{$lcV}-".date('Ymd-His').'.sql';
		echo "<br>{$ax['mdb_file_name']}: <strong>{$fName}</strong><br>\n";
		if (file_put_contents($fName, $sqlFile) !== false) {
			echo "{$ax['mdb_file_saved']}<br>\n";
			$result = basename($fName);
		} else {
			echo "<br><br><strong>{$ax['mdb_write_error']}</strong><br>\n";
			$result = false;
		}
	}
	echo "</fieldset>\n";
	return $result;
}

/* Import db tables */
function importTables() {
	global $ax, $lcV, $dbType;
	
	echo "<fieldset><legend>{$ax['mdb_restore']}</legend>\n";
	do {
		if (empty($_FILES['fName']['tmp_name'])) {
			echo "{$ax['mdb_noshow_restore']}\n"; break; //abort import
		}
		if (substr($_FILES['fName']['name'],-4) != '.sql') {
			echo "{$ax['mdb_file_not_sql']}\n"; break; //abort import
		}
		$buFile = $_FILES['fName']['tmp_name']; //get backup file name
		//Read SQL queries from $buFile
		$sqlArray = file($buFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
		unlink($buFile);
		//get calendar version and db type of backup file
		$buLcVer = '';
		$buDbType = $dbType;
		foreach ($sqlArray as $k => $qLine) { //search until 'INCREMENT' or 'INSERT INTO'
			if (preg_match('~LuxCal version:\s*(\d.\d)~i',$qLine,$match)) { $buLcVer = $match[1]; }
			if (stripos($qLine,'AUTO_INCREMENT')) { $buDbType = 'MySQL'; }
			if (stripos($qLine,'INCREMENT') or stripos($qLine,'INSERT INTO')) { break; }
		}
		if ($buDbType != $dbType and $buLcVer != substr($lcV,0,3)) { //db type and version not matching
			echo "<span class='hired'>{$ax['mdb_no_bup_match']}</span><br>\n"; break; //abort import
		}
		//import SQL file
		echo "{$ax['mdb_backup_file']}: '<strong>{$_FILES['fName']['name']}</strong>'<br><br>";
		$lcV3 = substr($lcV,0,3);
		$stCreate = $buLcVer == $lcV3; //lc versions matching => create standard tables
		$count = importSqlFile($sqlArray,$stCreate);
		$upgFrom = upgradeDb(); //recreate db schema for the current calendar
		$upgrFrTo = $upgFrom != $lcV3 ? "{$ax['mdb_db_upgraded']}: <b>V{$upgFrom}</b> => <b>V{$lcV3}</b><br><br>" : '';
		echo $upgrFrTo."
{$ax['mdb_restore_table']} 'events' - {$count['eve']} {$ax['mdb_inserted']}<br>
{$ax['mdb_restore_table']} 'users' - {$count['use']} {$ax['mdb_inserted']}<br>
{$ax['mdb_restore_table']} 'groups' - {$count['gro']} {$ax['mdb_inserted']}<br>
{$ax['mdb_restore_table']} 'categories' - {$count['cat']} {$ax['mdb_inserted']}<br>
{$ax['mdb_restore_table']} 'settings' - {$count['set']} {$ax['mdb_inserted']}<br>
{$ax['mdb_restore_table']} 'styles' - {$count['sty']} {$ax['mdb_inserted']}<br>\n";
		if ($count['cat'] > 0 and $count['use'] > 0 and $count['gro'] > 0 and $count['set'] > 0 and $count['sty'] > 0) {
			echo "<br><strong>{$ax['mdb_db_restored']}.</strong><br>\n";
		}
	} while (0); //end of: import tables
	echo "</fieldset>\n";
}

/* (Un)delete events */
function delEvents($delEvt, $fromD, $tillD) {
	global $ax;
	
	$where = $delEvt ? "WHERE `status` >= 0 " : "WHERE `status` = -1 ";
	if ($fromD) { $where .= " AND `sDate` >= '$fromD'"; }
	if ($tillD) { $where .= " AND (SELECT `repeat` FROM `categories` AS cat WHERE cat.`ID` = `catID`) = 0 AND (CASE WHEN `rType` > 0 THEN `rUntil` ELSE CASE WHEN `eDate` LIKE '9%' THEN `sDate` ELSE `eDate` END END <= '$tillD')"; }
	if ($delEvt) {
		$stH = dbQuery("UPDATE `events` SET `status` = -1, `mDateTime` = '".date("Y-m-d H:i")."' $where"); //delete
	} else {
		$stH = dbQuery("UPDATE `events` SET `status` = 0, `mDateTime` = '".date("Y-m-d H:i")."' $where"); //undelete
	}
	$nrAffected = $stH->rowCount();
	echo "<fieldset><legend>{$ax['mdb_events']}</legend>\n";
	echo ($delEvt ? $ax['mdb_deleted'] : $ax['mdb_undeleted']).": {$nrAffected}";
	echo "</fieldset>\n";
}

//init
$msg = '';
$compact = empty($_POST["compact"]) ? 0 : 1;
$export = empty($_POST["export"]) ? 0 : 1;
$import = empty($_POST["import"]) ? 0 : 1;
$events = empty($_POST["events"]) ? 0 : 1;
$delEvt = empty($_POST["delEvt"]) ? 0 : 1;
$fromD = (isset($_POST['fromD'])) ? DDtoID($_POST['fromD']) : ''; //from event date
$tillD = (isset($_POST['tillD'])) ? DDtoID($_POST['tillD']) : ''; //until event date
if ($fromD and $tillD and $fromD > $tillD) {
	$temp = $fromD;
	$fromD = $tillD;
	$tillD = $temp;
}
$exe = !empty($_POST["exe"]) ? 1 : 0;

//control logic
if ($usr['privs'] == 9) {
	if ($exe and (!$compact and !$export and !$import and !$events)) { $msg = $ax['mdb_no_function_checked'];	}
	echo $msg ? "<p class='error'>{$msg}</p>\n" : "<p>&nbsp;</p>\n";
	if (!$exe or (!$compact and !$export and !$import and !$events)) {
		echo "<aside class='aside sBoxAd'>{$ax['xpl_manage_db']}</aside>\n";
		echo "<div class='centerBox sBoxAd'>\n";
		showDbCount();
		echo "<br>\n";
		mdbForm(); //manage db form
		echo "</div>\n";
	} else {
		echo "<div class='centerBox sBoxAd'>\n";
		processFunctions();
		echo "</div>\n";
	}
} else {
	echo "<p class='error'>{$ax['no_way']}</p>\n";
}
?>