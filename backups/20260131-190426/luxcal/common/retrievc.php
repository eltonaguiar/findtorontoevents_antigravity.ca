<?php
/*
= Retrieve changed events from db =
Queries database starting from a specified date and dumps changed events in an arrays
Input params:
- start date (in yyyy-mm-dd format)
- allEvents; 0: apply normal filters, 1: no filters

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

function sortEvts2($a,$b) { //sort event (cat seq nr + times)
	if ($a['sts'] < $b['sts']) { return -1; } //status
	if ($a['sts'] > $b['sts']) { return 1; }
	if ($a['sda'] < $b['sda']) { return -1; } //start date
	if ($a['sda'] > $b['sda']) { return 1; }
	if ($a['sti'] < $b['sti']) { return -1; } //start time
	if ($a['sti'] > $b['sti']) { return 1; }
	return $a['seq'] < $b['seq'] ? -1 : 1; //cat seq nr
}

function grabChanges($sDate,$allEvents) { //query db for changes since $sDate
	global $set, $usr, $opt, $evtList;

	//set filter
	$filter = $usr['vCats'] != '0' ? " AND c.`ID` IN ({$usr['vCats']})" : '';
	$filter .= " AND e.`type` IN (0)";
	if (!$allEvents) {
		if (count($opt['cG']) > 0 and $opt['cG'][0] != 0) {
			$filter .= " AND u.`groupID` IN (".implode(",",$opt['cG']).")";
		}
		if (count($opt['cU']) > 0 and $opt['cU'][0] != 0) {
			$filter .= " AND e.`userID` IN (".implode(",",$opt['cU']).")";
		}
		if (count($opt['cC']) > 0 and $opt['cC'][0] != 0) {
			$filter .= " AND c.`ID` IN (".implode(",",$opt['cC']).")";
		}
	}

	//retrieve events
	$query =
	"SELECT
		e.`ID` AS eid,
		e.`private` AS pri,
		e.`type` AS typ,
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
		e.`notify` AS nom,
		e.`sDate` AS sda,
		e.`eDate` AS eda,
		e.`sTime` AS sti,
		e.`eTime` AS eti,
		e.`rType` AS r_t,
		e.`rInterval` AS r_i,
		e.`rPeriod` AS r_p,
		e.`rMonth` AS r_m,
		e.`rUntil` AS r_u,
		e.`aDateTime` AS adt,
		e.`mDateTime` AS mdt,
		e.`status` AS sts,
		c.`name` AS cnm,
		c.`sequence` AS seq,
		c.`repeat` AS rpt,
		c.`approve` AS app,
		c.`dayColor` AS dbg,
		c.`color` AS cco,
		c.`bgColor` AS cbg,
		c.`subCats` AS scs,
		u.`name` AS una,
		g.`color` AS uco
	FROM `events` AS e
	INNER JOIN `categories` AS c ON c.`ID` = e.`catID`
	INNER JOIN `users` AS u ON u.`ID` = e.`userID`
	INNER JOIN `groups` AS g ON g.`ID` = u.`groupID`
	WHERE ((e.`aDateTime` NOT LIKE '9%' AND SUBSTR(e.`aDateTime`,1,10) >= '$sDate') OR (e.`mDateTime` NOT LIKE '9%' AND SUBSTR(e.`mDateTime`,1,10) >= '$sDate'))".$filter." 
	ORDER BY
		e.`sDate`";
	$stH = dbQuery($query);

	//process events
	while ($evt = $stH->fetch(PDO::FETCH_ASSOC)) {
		if (!$allEvents and (($evt['app'] and !$evt['apd'] and !$usr['privs'] > 3) or $evt['pri']) and $evt['uid'] != $usr['ID'] and $usr['privs'] != 9) { continue; } //not approved: | private | not owner | not admin
		//pre-processing
		if ($evt['eda'][0] == '9') { $evt['eda'] = ''; }
		$evt['ald'] = $evt['ntm'] = false; //init
		if ($evt['eti'][0] == '9') { //no end time = ''
			$evt['eti'] = '';
		} else {
			$evt['ald'] = ($evt['sti'] == '00:00' and $evt['eti'] == '23:59');
			$evt['ntm'] = ($evt['sti'] == '00:00' and $evt['eti'] == '00:00');
			if ($evt['ald'] or $evt['ntm']) { $evt['sti'] = $evt['eti'] = ''; } //all day or no time: start/end time = ''
		}
		if (!$evt['tx1']) { $evt['tx1'] = ''; }
		if (!$evt['att']) { $evt['att'] = ''; }
		$evt['seq'] = substr("0".$evt['seq'],-2);
		$sCats = json_decode($evt['scs']);
		if (!$evt['sid'] or empty($sCats[$evt['sid']-1])) { //no subcat
			$evt['snm'] = '';
		} else {
			$sCat = $sCats[$evt['sid']-1];
			$evt['snm'] = $sCat[0];
			$evt['cco'] = $sCat[1] ?: $evt['cco'];
			$evt['cbg'] = $sCat[2] ?: $evt['cbg'];
		}
		$evt['tix'] = $set['ownerTitle'] ? "{$evt['una']}: {$evt['tit']}" : $evt['tit'];
		$evt['mayE'] = (($usr['eCats'] == '0' or strpos($usr['eCats'],strval($evt['cid'])) !== false) and
			($usr['privs'] > 2 or ($usr['privs'] == 2 and $evt['uid'] == $usr['ID']))); //edit rights
		//copy event to evtList
		$modDate = substr(max($evt['adt'],$evt['mdt']),0,10);
		$evtList[$modDate][] = $evt;
	}
	ksort($evtList);
	foreach ($evtList as &$events) { //sort event list per change date
		usort($events,'sortEvts2');
	}
}
?>