<?php
/*
= Log visitors data for LuxCal event calendar pages =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3
*/

function browser($userAgent) {
	$agent = stripos($userAgent, 'mobile') ? 'Mobile ' : '';
	$needle = ['Opera' => 'Opera','OPR' => 'Opera','Edge' => 'Edge', 'Chrome' => 'Chrome','Safari' => 'Safari','Firefox' => 'Firefox','MSIE' => 'IE','Trident/7' =>'IE'];
	foreach ($needle as $key => $value) {
		if (strpos($userAgent,$key)) { return $agent.$value; }
	}
	return $agent.'Other';
}

$page = substr($body,6,-4); //current page
if ($usr['privs'] < 9 and (empty($_SESSION[$calID]['lastHit4']) or $page != $_SESSION[$calID]['lastHit4'])) { //no admin and a new page
	$userAgent = !empty($_SERVER['HTTP_USER_AGENT']) ? $_SERVER['HTTP_USER_AGENT'] : '- -';
	//check if hit or bot and get counter
	$file = (preg_match('/bot|crawl|slurp|spider/i',$userAgent)) ? 'bot' : 'hit';
	$counter = is_readable("./logs/{$calID}~{$file}cnt.log") ? intval(file_get_contents("./logs/{$calID}~{$file}cnt.log")) : 0; //get hit/bot counter
	//collect visitor's data
	$tStamp = $_SERVER['REQUEST_TIME'];
	$host = gethostbyaddr($_SERVER['REMOTE_ADDR']);
	$agent = browser($userAgent);
	if (!empty($_SESSION[$calID]['lastHit1']) and !empty($_SESSION[$calID]['lastHit2']) and !empty($_SESSION[$calID]['lastHit3']) and //last hit data present
		(($tStamp - $_SESSION[$calID]['lastHit1']) < 600) and $host == $_SESSION[$calID]['lastHit2'] and $agent == $_SESSION[$calID]['lastHit3']) { //< 10 minutes ago: repeating hit
		$newHit = false;
		$_SESSION[$calID]['lastHit1'] = $tStamp; //save last hit time stamp
		$_SESSION[$calID]['lastHit4'] = $page;
		$logData = ', '.$page; //add page
	} else { //new hit
		$newHit = true;
		$_SESSION[$calID]['lastHit1'] = $tStamp; //save last hit data
		$_SESSION[$calID]['lastHit2'] = $host;
		$_SESSION[$calID]['lastHit3'] = $agent;
		$_SESSION[$calID]['lastHit4'] = $page;
		$logData = ($counter % 50 == 0) ? "\n\nDATE       TIME  HOST                                     BROWSER         PAGES" : ''; //titles every 50 lines
		$logData .= "\n".date("Y.m.d H:i",$tStamp)." ".str_pad(substr($host,-40),40)." ".str_pad($agent,15)." ".$page;
	}
	file_put_contents("./logs/{$calID}~{$file}log.log",$logData,FILE_APPEND | LOCK_EX);//append log data to hitlog/botlog file
	
	if ($newHit) { //increment hit/bot counter
		$fPath = "./logs/{$calID}~{$file}cnt.log";
		$file = fopen($fPath,"w");
		if (flock($file,LOCK_EX)) {
			fwrite($file,++$counter);
			fflush($file);
			flock($file,LOCK_UN);
		}
		fclose($file);
	}
}
?>
