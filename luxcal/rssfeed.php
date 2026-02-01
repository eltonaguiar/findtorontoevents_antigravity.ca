<?php
/*
= LuxCal RSS feeder =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/
header("Content-type: text/xml");

//load toolbox
require './common/toolbox.php';
require './common/toolboxd.php'; //database tools

//load config data
require './lcconfig.php';

//get calendar
$calID = (!empty($_GET['cal']) and preg_match('~^\w{1,20}$~',$_GET['cal'])) ? $_GET['cal'] : $dbDef;

//connect to database
$dbH = dbConnect($calID);

//get settings from database
$set = getSettings();

//set time zone
date_default_timezone_set($set['timeZone']);

//get common functions
require './common/retrieve.php';

//set language
require './lang/ui-'.strtolower($set['language']).'.php';

//init
$fDate = date("Y-m-d");
$tDate = date("Y-m-d", time() + (($set['lookaheadDays']-1) * 86400));
$qMark = strpos($set['calendarUrl'],'?');
$parSep = $qMark !== false ? '&amp;' : '?'; //? or &amp;

//set user parameters
$usr['vCats'] = '0'; //view: all categories
$usr['eCats'] = ''; //edit: no categories

//set filters
$filter = $values = '';
if (isset($_GET['cU'])) {
	$placeholders = preg_replace("~\d+~",'?',$_GET['cU']);
	$filter .= " AND e.`userID` IN ({$placeholders})";
	$values .= ','.$_GET['cU'];
}
if (isset($_GET['cG'])) {
	$placeholders = preg_replace("~\d+~",'?',$_GET['cG']);
	$filter .= " AND g.`ID` IN ({$placeholders})";
	$values .= ','.$_GET['cG'];
}
if (isset($_GET['cC'])) {
	$placeholders = preg_replace("~\d+~",'?',$_GET['cC']);
	$filter .= " AND c.`ID` IN ({$placeholders})";
	$values .= ','.$_GET['cC'];
}

	//retrieve events
$evtList = [];
retrieve($fDate,$tDate,'',[$filter,substr($values,1)],'*');

//feed header
echo "<?xml version='1.0' encoding='utf-8' ?>
<rss version='2.0'>
<channel>
	<title>{$set['calendarTitle']} - RSS feed</title>
	<link>{$set['calendarUrl']}</link>
	<description>{$xx['vws_events_for_next']} {$set['lookaheadDays']} {$xx['vws_days']}</description>
	<language>en-us</language>
	<category>Calendar events</category>
	<pubDate>".date("r")."</pubDate>
	<generator>LuxCal Web calendar</generator>\n";

//set user parameters
$usr['vCats'] = '0'; //view: all categories
$usr['eCats'] = ''; //edit: no categories

//process events and send feeds
$evtDone = [];
if ($evtList) {
	foreach($evtList as $date => &$events) {
		foreach ($events as &$evt) {
			if (!$evt['mde'] or !in_array($evt['eid'],$evtDone)) { //!mde or mde not processed
				$evtDone[] = $evt['eid'];
				$checkBx = (cMark($evt,$date) ? $evt['cmk'] : '');
				$evtDate = $evt['mde'] ? makeD($evt['sda'],5).' - '.makeD($evt['eda'],5) : makeD($date,5);
				$evtTime = makeTime($evt['ald'],0,0,$evt['sti'],$evt['eti']);
				$feed = "\n<item>\n";
				$feed .= "<title>{$evtDate}: {$checkBx}".htmlentities($evt['tit'])."</title>\n";
				$feed .= "<link>{$set['calendarUrl']}{$parSep}cD={$date}</link>\n";
				$feed .= "<description>\n<![CDATA[\n";
				$feed .= "{$evtTime}\n";
				if ($set['evtTemplGen']) {
					$fields = '123'.($set['xField1Rights'] == 1 ? '4' : '').($set['xField2Rights'] == 1 ? '5' : ''); //exclude xField 1
					$feed .= '<br>'.makeE($evt,$set['evtTemplGen'],'br',"<br>\n",$fields);
				}
				$feed .= "]]>\n</description>\n";
				$feed .= "<guid isPermaLink='false'>{$set['calendarUrl']}{$parSep}evt={$evt['eid']}&amp;{$date}</guid>\n";
				$feed .= "</item>\n";
				echo $feed;
			}
		}
	}
} else { //no events due
	echo "\n<item>
		<description>\n{$xx['vws_none_due_in']} {$set['lookaheadDays']} {$xx['vws_days']}\n</description>
		<guid isPermaLink='false'>{$set['calendarUrl']}</guid>
		</item>\n";
}
//feed trailer
echo "\n</channel>
</rss>";
?>