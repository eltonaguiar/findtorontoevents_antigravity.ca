<?php
/*
=== DATABASE RELATED FUNCTIONS - MYSQL ===

This file is part of the LuxCal Web Calendar.
Copyright (C) 2009-2025 LuxSoft - www.LuxSoft.eu
License http://www.gnu.org/licenses/gpl.html GPL version 3
*/

//Current LuxCal version
define("LCV","5.3.4M");

//Connect to database
function dbConnect($calID,$exitOnError=1) {
	global $dbHost, $dbUnam, $dbPwrd, $dbName;
	
	try {
		$dbH = new PDO("mysql:host={$dbHost};dbname={$dbName};charset=utf8mb4",$dbUnam,$dbPwrd);
		$dbH->setAttribute(PDO::ATTR_ERRMODE,PDO::ERRMODE_EXCEPTION);
		$stH = $dbH->query("SHOW TABLES LIKE '{$calID}\_%'");
		if ($exitOnError and !$row = $stH->fetch(PDO::FETCH_NUM)) {
			exit("Calendar '{$calID}' not found.");
		}
	}
	catch(PDOException $e) {
		if ($exitOnError) {
			logMessage('sql',1,"Database connection error: ".$e->getMessage());
			exit("Could not connect to the calendar database. See 'logs/sql.log'");
		} else {
			return false; //error
		}
	}
	return $dbH; //return db handle
}

//Query database
function dbQuery($query,$logError=1) {
global $dbH, $calID;

	$query = preg_replace("~(\s`)(events|groups|users|categories|settings|styles)~","$1{$calID}_$2",$query); //use calendar with calID
	try {
		$stH = $dbH->query($query);
	}
	catch (PDOException $e) {
		if ($logError) {
			logMessage('sql',1,"SQL query error: ".$e->getMessage()."\nQuery string: {$query}");
			exit("SQL error. See 'logs/sql.log'");
		} else {
			return false; //error
		}
	}
	return $stH; //result statement handle
}

//Begin / commit transaction
function dbTransaction($action,$logError=1) {
global $dbH;

	try {
		switch ($action[0]) {
			case 'b': $result = $dbH->beginTransaction(); break;
			case 'c': $result = $dbH->commit(); break;
			case 'r': $result = $dbH->rollBack();
		}
	}
	catch (PDOException $e) {
		if ($logError) {
			logMessage('sql',1,"SQL transaction error: ".$e->getMessage()."\nQuery: {$action} transaction");
			exit("SQL error. See 'logs/sql.log'");
		} else {
			return false; //error
		}
	}
	return $result;
}

//Get last inserted row ID
function dbLastRowId() {
global $dbH;

	return $dbH->lastInsertId();
}

//Prepare SQL statement 
function stPrep($query,$logError=1) {
global $dbH, $calID;

	$query = preg_replace("~(\s`)(events|groups|users|categories|settings|styles)~","$1{$calID}_$2",$query); //use calendar with calID
	try {
		$stH = $dbH->prepare($query);
	}
	catch (PDOException $e) {
		if ($logError) {
			logMessage('sql',1,"SQL prepare error: ".$e->getMessage()."\nQuery string: {$query}");
			exit("SQL error. See 'logs/sql.log'");
		} else {
			return false; //error
		}
	}
	return $stH; //successful
}

//Execute prepared statement 
function stExec($stH,$values,$logError=1) {
	try {
		$result = $stH->execute(!empty($values) ? $values : array());
	}
	catch (PDOException $e) {
		if ($logError) {
			logMessage('sql',1,"SQL execute error: ".$e->getMessage()."\nValues string: ".implode(',',$values));
			exit("SQL error. See 'logs/sql.log'");
		} else {
			return false; //error
		}
	}
	return $result; //successful
}

function getTableSql($table) { //get SQL code to create table
	$stH = dbQuery("SHOW CREATE TABLE `{$table}`");
	$sqlCode = $stH->fetch(PDO::FETCH_NUM);
	$stH = null; //release statement handle!
	return $sqlCode[1];
}

function getTables($like='%') { //get array with db tables
	global $calID;
	
	$tables = array();
	$stH = dbQuery("SHOW TABLES LIKE '{$calID}\_{$like}'"); //get table names
	while ($row = $stH->fetch(PDO::FETCH_NUM)) {
		$tables[] = $row[0]; //add table name
	}
	$stH = null; //release statement handle!
	return $tables;
}

function getCIDs() { //get array with installed calendar IDs
	$cals = array();
	$stH = dbQuery("SHOW TABLES LIKE '%\_events'"); //get events table names
	while ($row = $stH->fetch(PDO::FETCH_NUM)) {
		$cals1[] = substr($row[0],0,-7); //extract calendar ID (table prefix)
	}
	$stH = dbQuery("SHOW TABLES LIKE '%\_settings'"); //get settings table names
	while ($row = $stH->fetch(PDO::FETCH_NUM)) {
		$cals2[] = substr($row[0],0,-9); //extract calendar ID (table prefix)
	}
	$stH = null; //release statement handle!
	return array_intersect($cals1,$cals2);
}

function getCals() { //get array with installed calendar ID/title pairs
	global $dbH;

	$curCals = array();
	if (isset($dbH)) { //connected to db
		$cals = getCIDs(); //get calendar IDs
		foreach ($cals as $id) {
			if ($stH = dbQuery("SELECT `value` FROM {$id}_settings WHERE `name` = 'calendarTitle'",0)) {
				$row = $stH->fetch(PDO::FETCH_NUM);
				$stH = null; //release statement handle!
				if (!empty($row)) { //found
					$curCals[$id] = $row[0]; //add calendar title
				}
			}
		}
	}
	return $curCals;
}

function getSettings() { //get settings from database
	$set = array();
	$stH = dbQuery("SELECT `name`,`value` FROM `settings`");
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		$set[$row['name']] = $row['value'];
	}
	$stH = null; //release statement handle
	return $set; //array with settings
}
?>