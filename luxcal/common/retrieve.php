<?php
/*
= Retrieve events from db =
Queries the database for a specified period and dumps events per day in the $evtList array
Input params:
- start date
- end date (in yyyy-mm-dd format)
- string with letters u and/or c (optional); if present, u includes user filter and c includes cat filter
- filter (optional) additional filter in SQL format
- event type (0: normal, 1: day marking)

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$evtList = [];

function sortEvts0($a,$b) { //sort event (times)
	if ($a['sort'] < $b['sort']) { return -1; } //times
	if ($a['sort'] > $b['sort']) { return 1; }
	return $b['adt'] <=> $a['adt'] ; //date-time added (last added at top)
}

function sortEvts1($a,$b) { //sort event (cat seq nr + times)
	if ($a['seq'] < $b['seq']) { return -1; } //cat seq nr
	if ($a['seq'] > $b['seq']) { return 1; }
	if ($a['sort'] < $b['sort']) { return -1; } //times
	if ($a['sort'] > $b['sort']) { return 1; }
	return $b['adt'] <=> $a['adt']; //date-time added (last added at top)
}

//main function
function retrieve($start,$end,$iFilter='',$xFilter='',$eType='0') {
	global $usr, $set, $opt, $evtList;

	$evtList = []; //clear event list
	$today = date('Y-m-d');

	//set filters
	$filter = $usr['vCats'] != '0' ? " AND c.`ID` IN ({$usr['vCats']})" : '';
	if ($eType !== "*") { $filter .= " AND e.`type` IN ({$eType})"; }
	if (strpos($iFilter,'g') !== false and count($opt['cG']) > 0 and $opt['cG'][0] != 0) {
		$filter .= " AND u.`groupID` IN (".implode(",",$opt['cG']).")";
	}
	if (strpos($iFilter,'u') !== false and count($opt['cU']) > 0 and $opt['cU'][0] != 0) {
		$filter .= " AND e.`userID` IN (".implode(",",$opt['cU']).")";
	}
	if (strpos($iFilter,'c') !== false and count($opt['cC']) > 0 and $opt['cC'][0] != 0) {
		$cCList = implode(",",$opt['cC']);
		if ($opt['cC'][0] > 0) {
			$filter .= " AND c.`ID` IN ({$cCList})";
		} else { //exclude cCs
			$filter .= " AND c.`ID` NOT IN (".str_replace('-','',$cCList).")";
		}
	}
	$values = '';
	if ($xFilter) {//add external filter
		$filter .= $xFilter[0];
		$values .= $xFilter[1];
	} 
	$valArr = $values ? explode(',',$values) : [];
	$filter = $filter ? '('.substr($filter,5).')' : '';
	
	//set user id
	if (empty($usr['ID'])) { $usr['ID'] = 1; } //if no UserID, set to public
	if (empty($usr['privs'])) { $usr['privs'] = 1; } //if no UserID, set to public

	/* roll rolling events */
	$stH = dbQuery("SELECT `ID`,`sDate`,`eDate`,`checked`,`rUntil` FROM `events` WHERE `rType` = 3 AND `sDate` < '$today' AND `rUntil` >= '$today' AND `status` >= 0");
	while (list($ID,$sda,$eda,$checked,$rUntil) = $stH->fetch(PDO::FETCH_NUM)) {
		if (!$checked) {
			if ($eda[0] != '9') { $eda = date('Y-m-d',time() + strtotime($eda) - strtotime($sda)); }
			$reset = $rUntil == $today ? ",`rType`=0,`rUntil`='9999-00-00'" : ''; //reset rolling when rUntil
			$stH2 = dbQuery("UPDATE `events` SET `sDate`='$today',`eDate`='$eda'{$reset} WHERE `ID` = $ID");
		} else {
			$stH2 = dbQuery("UPDATE `events` SET `rType`=0,`rUntil`='9999-00-00' WHERE `ID` = $ID");
		}
	}

	/* retrieve events between $start and $end */
	$query =
	"SELECT
		e.`ID` AS eid,
		e.`type` AS typ,
		e.`private` AS pri,
		e.`title` AS tit,
		e.`venue` AS ven,
		e.`text1` AS tx1,
		e.`text2` AS tx2,
		e.`text3` AS tx3,
		e.`attach` AS att,
		e.`catID` AS cid,
		e.`scatID` AS sid,
		e.`userID` AS uid,
		e.`editor` AS edr,
		e.`approved` AS apd,
		e.`checked` AS chd,
		e.`notify` AS nom,
		e.`notRecip` AS nal,
		e.`sDate` AS sda,
		e.`eDate` AS eda,
		e.`xDates` AS xda,
		e.`sTime` AS sti,
		e.`eTime` AS eti,
		e.`rType` AS r_t,
		e.`rInterval` AS r_i,
		e.`rPeriod` AS r_p,
		e.`rMonth` AS r_m,
		e.`rUntil` AS r_u,
		e.`aDateTime` AS adt,
		e.`mDateTime` AS mdt,
		c.`name` AS cnm,
		c.`symbol` AS sym,
		c.`sequence` AS seq,
		c.`repeat` AS rpt,
		c.`noverlap` AS nol,
		c.`olapGap` AS olg,
		c.`olErrMsg` AS oem,
		c.`approve` AS app,
		c.`dayColor` AS dbg,
		c.`color` AS cco,
		c.`bgColor` AS cbg,
		c.`checkBx` AS cbx,
		c.`checkLb` AS clb,
		c.`checkMk` AS cmk,
		c.`subCats` AS scs,
		u.`name` AS una,
		g.`color` AS uco
	FROM `events` AS e
	INNER JOIN `categories` AS c ON c.`ID` = e.`catID`
	INNER JOIN `users` AS u ON u.`ID` = e.`userID`
	INNER JOIN `groups` AS g ON g.`ID` = u.`groupID`
	WHERE e.`status` >= 0".($filter ? " AND ($filter".($eType === "*" ? " OR e.`type` > 0" : "").")" : "")."
		AND e.`sDate` <= '$end'
		AND (CASE WHEN e.`eDate` LIKE '9%' THEN e.`sDate` ELSE e.`eDate` END >= '$start' OR e.`rUntil` >= '$start')
	ORDER BY
		e.`sDate`";
	$stH = stPrep($query);
	stExec($stH,$valArr);
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		if ((($row['app'] and !$row['apd'] and $usr['privs'] < 4) or $row['pri']) and $row['uid'] != $usr['ID'] and $usr['privs'] != 9) { continue; } //not approved | private | not owner | not admin
			//pre-processing
			$row['ald'] = $row['ntm'] = false; //init
			if ($row['eti'][0] == '9') { //no end time = ''
				$row['eti'] = '';
			} else {
				$row['ald'] = ($row['sti'] == '00:00' and $row['eti'] == '23:59');
				$row['ntm'] = ($row['sti'] == '00:00' and $row['eti'] == '00:00');
				if ($row['ald'] or $row['ntm']) { $row['sti'] = $row['eti'] = ''; } //all day or no time: start/end time = ''
			}
			if (!$row['tx1']) { $row['tx1'] = ''; }
			if (!$row['att']) { $row['att'] = ''; }
			if (!$row['chd']) { $row['chd'] = ''; }
			$row['seq'] = substr("0".$row['seq'],-2);
			$sCats = json_decode($row['scs']);
			if (!$row['sid'] or empty($sCats[$row['sid']-1])) { //no subcat
				$row['snm'] = '';
			} else {
				$sCat = $sCats[$row['sid']-1];
				$row['snm'] = $sCat[0];
				$row['cco'] = $sCat[1] ?: $row['cco'];
				$row['cbg'] = $sCat[2] ?: $row['cbg'];
			}
			$row['tix'] = $set['ownerTitle'] ? "{$row['una']}: {$row['tit']}" : $row['tit'];
			$row['mayE'] = (($usr['eCats'] == '0' or strpos($usr['eCats'],strval($row['cid'])) !== false) and
				($usr['privs'] > 2 or ($usr['privs'] == 2 and $row['uid'] == $usr['ID'])) and
				(!$row['apd'] or $usr['privs'] >= 4)); //edit rights

		//here we go	
		if ($row['rpt'] == 0 and $row['r_t'] < 1 or $row['r_t'] > 2) { //non-recurring
			$eEnd = ($row['eda'][0] != '9') ? $row['eda'] : $row['sda'];
			processEvent(max($start,$row['sda']), min($end,$eEnd), $row['sda'], $eEnd, $row);
		} else { //recurring
			$dUts = ($row['eda'][0] != '9') ? strtotime($row['eda']) - strtotime($row['sda']) : 0; //delta start date - end date uts
			$eStart = $row['sda'];
			if ($row['rpt'] > 0) { //cat repeat overrides
				$row['r_t'] = $row['r_i'] = 1;
				$row['r_p'] = $row['rpt'];
				$row['r_u'] = '9999-00-00';
			} elseif ($row['r_t'] == 2) {
				$nxtD = nextRdate2($eStart,$row['r_i'],$row['r_p'],$row['r_m'],0); //goto 1st occurrence of xth <dayname> in month y
				$eStart = ($nxtD < $eStart) ? nextRdate2($eStart,$row['r_i'],$row['r_p'],$row['r_m'],1) : $nxtD;
			}
			$eEnd = date("Y-m-d",strtotime($eStart.' 12:00:00') + $dUts);
			while ($eStart <= min($end, $row['r_u']) and $row['r_u'] >= $start) {
				if ($eEnd >= $start) { //hit
					processEvent(max($start,$eStart), min($end,$eEnd), $eStart, $eEnd, $row);
				}
				$eStart = $row['r_t'] == 1 ? nextRdate1($eStart,$row['r_i'],$row['r_p']) : nextRdate2($eStart,$row['r_i'],$row['r_p'],$row['r_m'],1);
				$eEnd = date("Y-m-d",strtotime($eStart.' 12:00:00') + $dUts);
			}
		}
	}

	//sort the event list per date
	ksort($evtList);
	foreach ($evtList as &$events) {
		switch ($set['evtSorting']) { //sort events per day on ...
			case '0': usort($events, 'sortEvts0'); break; //times
			case '1': usort($events, 'sortEvts1'); //cat seq. nr + times
		}
	}
}

//
//Process (multi-day) events and save event data
//
function processEvent($from, $till, $eStart, $eEnd, &$evt) {
	global $evtList;

	$evt['smd'] = $eStart; //for gantt chart
	$evt['emd'] = $eEnd; //for gantt chart

	//process event data
	$sTs = strtotime($from.' 12:00:00');
	$eTs = strtotime($till.' 14:00:00');
	for($i = $sTs; $i <= $eTs; $i += 86400) { //increment 1 day
		$curD = date('Y-m-d',$i);
		if ($evt['xda'] and xDate($evt['xda'],$evt['sda'],$curD)) { continue; } //exclude date from series
		$curdm = substr($curD,5);
		if ($evt['eda'][0] != '9' and $evt['sda'] < $evt['eda']) { //multi-day event; mde -> 1:first, 2:in between ,3:last day
			$evt['mde'] = ($curdm == substr($eStart,5)) ? 1 : (($curdm == substr($eEnd,5)) ? 3 : 2);
		} else { //single day event
			$evt['mde'] = 0;
		}
		$evt['sort'] = $evt['mde'] <= 1 ? $evt['sti'] : ($evt['mde'] == 2 ? '' : $evt['eti']);
		//copy event to evtList
		$evtList[$curD][] = $evt;
	}
}
?>