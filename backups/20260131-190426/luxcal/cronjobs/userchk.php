<?php
/*
= check calendar inactive user accounts which can be deleted =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

-------------------------------------------------------------------
 This script depends on and is executed via the file lcalcron.php.
 See lcalcron.php header for details.
-------------------------------------------------------------------


---------- THIS SCRIPT USES THE FOLLOWING CALENDAR SETTINGS ----------
maxNoLogin: Maximum number of 'no login' days before deleting account
----------------------------------------------------------------------
*/

function cronUserChk() {
	global $set;
	
	//calculate minimum last login date required to keep account
	$minLoginDate = date("Y-m-d", time() - $set['maxNoLogin'] * 86400);

	//remove user accounts for users not logged in since $minLoginDate
	//but never delete the public access user and admin user!
	$stH = stPrep("DELETE FROM `users` WHERE `ID` > 2 AND `login1` < ?");
	stExec($stH,[$minLoginDate]);
	$nrRemoved = $stH->rowCount();
	return $nrRemoved;
}
?>
