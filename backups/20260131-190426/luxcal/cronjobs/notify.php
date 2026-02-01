<?php
/*
= check calendar database for notification messages to be sent =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

-------------------------------------------------------------------
This script is executed via the file lcalcron.php. See lcalcron.php 
header for details.
-------------------------------------------------------------------

*/

function cronNotify() {
	global $evtList, $set, $ax, $xx;

	//initialize
	$todayT = time()+43200; //today 12:00
	$todayD00 = date("Y-m-d", $todayT); //today
	$todayD99 = date("Y-m-d", $todayT + 8553600); //today + 99 days
	$sentTo = '';

	//set filter
	$filter = ' AND notify >= 0';

	//retrieve and process events
	$usr['ID'] = 0; //all users
	$usr['privs'] = 9; //include private events
	retrieve($todayD00,$todayD99,'',[$filter,'']);

	if ($evtList) {
		foreach($evtList as $date => &$events) {
			$daysDue = round((strtotime($date.' 12:00:00') - $todayT) / 86400);
			foreach ($events as $evt) {
				if ($evt['mde'] <= 1 and //single day event or first day of multi-day event
						($daysDue == $evt['nom'] or $date == $todayD00)) { //event due
					$header = $daysDue ? "{$ax['cro_due_in']} {$daysDue} {$ax['cro_days']}" : $ax['cro_due_today'];
					$evt['repTxt'] = repeatText($evt['r_t'],$evt['r_i'],$evt['r_p'],$evt['r_m'],DDtoID($evt['r_u'])); //make repeat text
					$result = notify($evt, $evt['nal'], $header);
					$sentTo .= "• {$header}: <b>{$evt['tit']}</b>\n";
					foreach ($result as $type => $recList) {
						if ($recList) {
							$failures = $recList[0] ? " (FAILURES - see logs/luxcal.log for details.)" : '';
							$service = $type == 'E' ? "Email" : ($type == 'T' ? "Telegram" : "SMS");
							$sentTo .= "&ensp;{$service} to: " .substr($recList,3)."{$failures}\n";
						}
						
					}
				}
			}
		}
	}
	return $sentTo;
}
?>
