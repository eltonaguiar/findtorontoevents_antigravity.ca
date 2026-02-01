<?php
/*
= Footer for LuxCal event calendar pages =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3
*/

if (isset($spItems) and ($spItems !== '000')) { //side panel
	echo "</div>\n";
}
echo "</div>\n";//close container
if ($set['logVisitors'] and $usr['privs'] < 4) { //visits logging enabled
	include './common/logvisit.php'; //log visit
}
switch ($ftrType) { //footer types - 0: no, f: full 
	case '0':
		break;
	case 'f':
		echo "<footer class='noPrint'>\n";
		echo "<a href='https://www.luxsoft.eu?V".LCV."' target='_blank'>powered by <span class='footLS'>LuxSoft</span></a>\n";
		if ($set['logVisitors'] and is_readable("./logs/{$calID}~hitcnt.log")) {
			$hitCnt = file_get_contents("./logs/{$calID}~hitcnt.log"); //get hit counter
			echo "<span class='hitCnt floatL'>".($usr['ID'] == 2 ? "<a href='dloader.php?ftd=./logs/{$calID}~hitlog.log'>{$hitCnt}</a>" : $hitCnt)."</span>\n";
		}
		if ($usr['privs'] > 0 and $opt['cP'] < 20 and $set['rssFeed']) { //>= view rights, calendar views only
			echo "<span class='floatL'><a href='rssfeed.php{$cF}' title='RSS feed'>RSS</a></span>\n";
		}
		if (!empty($note)) { echo "== {$note} =="; }
		echo "</footer>\n";
}
unset($ftrType);
?>
</body>
</html>
