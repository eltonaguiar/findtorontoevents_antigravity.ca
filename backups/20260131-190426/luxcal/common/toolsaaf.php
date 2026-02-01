<?php
/*
= LuxCal Toolbox for the Async Await Fetch Method =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

*/

chdir('..'); //change to calendar root

$data = json_decode(rawurldecode(trim(file_get_contents("php://input")))); //decoding JSON input

if (empty($data->q) or !strpos('~dnd~tec~cop',$data->q)) { exit(json_encode(["ok"=>"invalid request"])); } //invalid request

require './lcconfig.php'; //load config data
require './common/toolbox.php'; //load config data

$calID = $data->calID; //get calendar in use
$cPage = $data->cPage; //calendar page
$uName = $data->uName; //user name (editor)

//sanity check primary params
if (!preg_match('%^[\w-]{1,20}$%', $calID) or
		!preg_match('%^\d{1,2}$%', $cPage) or
		!preg_match('%^[\w\s\._-]{0,30}$%u', $uName)
	) { exit(json_encode(["ok"=>"Invalid parameters: calID = $calID, cPage = $cPage, uName = $uName"])); } //exit

//start session
session_name('PHPSESSID'); //session cookie name
session_start();

if ($data->tkn != $_SESSION["LXCtkn_{$calID}:{$cPage}"]) { exit(json_encode(["ok"=>"invalid token"])); }

require './common/toolboxd.php'; //get database tools + LCV

$dbH = dbConnect($calID); //connect to db

$set = getSettings(); //get default timezone from settings
date_default_timezone_set($set['timeZone']);
require './lang/ai-'.strtolower($set['language']).'.php'; //get ai texts

//execute queries
switch($data->q) {
	case'tec': //toggle event check mark
		//get input params
		$evtID = $data->evtID;
		$evtDt = $data->evtDt;

		//sanity check
		if (!preg_match('%^\d{1,8}$%', $evtID) or
				!preg_match('%^\d{2,4}-\d{2}-\d{2,4}$%', $evtDt)
			) { exit(json_encode(["ok"=>"Invalid parameters: evtID = $evtID, evtDt = $evtDt"])); } //exit

		//get check data
		$stH = stPrep("SELECT e.`sDate`,e.`checked`,c.`checkMk` FROM `events` e INNER JOIN `categories` c ON c.`ID` = e.`catID` WHERE e.`ID` = ?");
		stExec($stH,[$evtID]);
		list($sda,$chd,$cmk) = $stH->fetch(PDO::FETCH_NUM);
		$stH = null;
		$offset = strval(round((strtotime($evtDt) - strtotime($sda)) / 86400)); //days

		//set/unset checked
		if (!$chd or strpos($chd,";{$offset}") === false) { //check
			$chd .= ";{$offset}";
			$response = $cmk; //check mark
		} else { //uncheck
			$chd = str_replace(";{$offset}",'',$chd);
			$response = '&#x2610;'; //ballot box
		}

		//update event
		$stH = stPrep("UPDATE `events` SET `checked` = ?,`editor` = ?,`mDateTime` = ? WHERE `ID` = ?");
		stExec($stH,[$chd,$uName,date("Y-m-d H:i"),$evtID]); //update events table

		echo json_encode(["ok"=>"OK","response"=>$response]);
		break;
	case'dnd': //drag and drop
		//get input params
		$evtID = $data->evtID;
		$seconds = $data->seconds;
		$copy = $data->copy;

		//sanity check
		if (!preg_match('%^\d{1,8}$%', $evtID) or
				!preg_match('%^-?\d{1,8}$%', $seconds) or
				!preg_match('%^[01]$%', $copy)
			) { exit(json_encode(["ok"=>"Invalid parameters: evtID = $evtID, seconds = $seconds, copy = $copy"])); } //exit

		//get event data
		$stH = stPrep("	SELECT * FROM `events` WHERE `ID` = ?");
		stExec($stH,[$evtID]);
		$row = $stH->fetch(PDO::FETCH_ASSOC);
		$stH = null;
		unset($row['ID']);

		$sDateNewTs = strtotime($row['sDate']) + $seconds;
		$sDateNew = date('Y-m-d',$sDateNewTs);
		$eDateNew = $row['eDate'][0] != '9' ? date('Y-m-d',strtotime($row['eDate']) + $seconds) : $row['eDate'];
		$uDateNew = $row['rUntil'][0] != '9' ? date('Y-m-d',strtotime($row['rUntil']) + $seconds) : $row['rUntil'];
		$rPeriod = $row['rType'] == 2 ? date('N',$sDateNewTs) : $row['rPeriod']; //repeating on a specific day of the week: update rPeriod

		if ($copy) { //copy event
			$row['sDate'] = $sDateNew;
			$row['eDate'] = $eDateNew;
			$row['rPeriod'] = $rPeriod;
			$row['rUntil'] = $uDateNew;
			$row['editor'] = $uName;
			$row['mDateTime'] = date("Y-m-d H:i");
			dbQuery("INSERT INTO events (".implode(",",array_keys($row)).") VALUES ('".implode("', '",array_values($row))."')");
		} else { //update event
			$stH = stPrep("UPDATE `events` SET `sDate` = ?,`eDate` = ?,`rPeriod` = ?,`rUntil` = ?,`editor` = ?,`mDateTime` = ? WHERE `ID` = ?");
			stExec($stH,[$sDateNew,$eDateNew,$rPeriod,$uDateNew,$uName,date("Y-m-d H:i"),$evtID]); //update events table
		}

		echo json_encode(["ok"=>"OK"]);
		break;
	case'cop': //copy event to other calendar
		//get input params
		$evtID = $data->evtID;
		$calIDs = $data->calIDs;
		
		//sanity check
		if (count($calIDs) == 0) { exit(json_encode(["ok"=>"NOK","msg"=>"{$ax['aff_sel_cals']}"])); } //exit
		if (!preg_match('%^\d{1,8}$%', $evtID)) { exit(json_encode(["ok"=>"NOK","msg"=>"Invalid parameter evtID: $evtID"])); } //exit
		foreach($calIDs as $destID) {
			if (!preg_match('%^[\w-]{1,20}$%', $destID)) { exit(json_encode(["ok"=>"NOK","msg"=>"Invalid parameter calID: $destID"])); } //exit
		}

		//get event data and reset calendar-specific fields
		$stH = stPrep("	SELECT * FROM `events` WHERE `ID` = ?");
		stExec($stH,[$evtID]);
		$row = $stH->fetch(PDO::FETCH_ASSOC);
		$stH = null;
		unset($row['ID']); 
		$row['catID'] = 1;
		$row['scatID'] = 0;
		$row['userID'] = 2;
		$row['editor'] = $uName;
		$row['mDateTime'] = date("Y-m-d H:i");
		array_walk($row,function (&$value) { $value = SQLite3::escapeString($value); }); //escape quotes

		//copy to destination calendars
		foreach($calIDs as $destID) { //switch calendar and copy event
			$dbH = dbConnect($destID); //connect to cal2 db
			dbQuery("INSERT INTO events (".implode(",",array_keys($row)).") VALUES ('".implode("', '",array_values($row))."')");
		}
		exit(json_encode(["ok"=>"OK","msg"=>"{$ax['aff_evt_copied']}"])); //exit
}
?>