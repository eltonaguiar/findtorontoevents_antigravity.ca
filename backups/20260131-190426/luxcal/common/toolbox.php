<?php
/*
=== REGEX DEFINITIONS & TOOLBOX FUNCTIONS ===

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

*/

/*---------- REGEX DEFINITIONS ----------*/

$rxEML = "~(^|\s)([\w!#$%&'*+/=`{|}\^\~\-\.]{1,64})@([a-z0-9-]{2,50})\.(\w{2,6})(?:\s*\[([^<>\[]*?)\])?(\.|\s|<|$)~imu"; //jd@skyweb.com [title]

$rxELink = "~<a\s.{18,21}mailto:([^@]+@[^\.]+\.[^?]+)\?[^<>]+>([^<>]+)</a>~i"; //<a ... mailto:...>...</a>

$rxURL = '~(^|\s)(S:|B:)?(https?://([^\s\[\<$]{5,}[^.\s\[\<$]))(?:\s*\[([^<>\[]+?)\])?(\.|\s|<|$)~im'; //S:https://www.mysite.xxx [title]

$rxULink = '~<a\s[^<>]*?href=["\'](https?://([^|<>\s]{5,}))["\'][^_<>]+(_b|_s)?[^_<>]+>([^|<>]*?)</a>~i'; //<a href=..._blank">title</a>

$rxCalURL = '~^(https?://)?((?:[\w\-:]+\.)+[a-z]{2,15}(?:[/?#:][^<>\s\[]*)?|[\w\-]{2,10}host(?::[0-9]{1,3})?|(?:[0-9]{1,3}\.){3}[0-9]{1,3})(/[^<>\s\[]+)*/?$~i'; //https://XXX/mycal/calendar.php (XXX = www.mysite.xxx | ?????host:70 | ip address)

$rxPhone = '~^[0+][\d\s\-/()]{6,20}$~'; //+1-541-754-3010, (089) / 636-48018, etc.

$rxIMGTags = '~<img.*?/[\w\-]+/([^\s/]+\.(?:gif|jpg|png)).*?>~i'; // <img src=...>

$rxIMG = '~(^|\s)(([^\s/]+)\.(?:gif|jpg|png))(\.|\s|$)~i'; //mytnail.gif (or .jpg, or .png)

$languages = ['bg' => 'bulgarian', 'cs' => 'czech', 'da' => 'dansk', 'de' => 'deutsch', 'en' => 'english', 'es' => 'espanol', 'fr' => 'francais', 'el' => 'greek', 'hu' => 'hungarian', 'it' => 'italiano', 'nl' => 'nederlands', 'no' => 'norsk', 'pl' => 'polska', 'pt' => 'portuguese', 'ro' => 'romanian', 'ru' => 'russian', 'sl' => 'slovenski', 'fi' => 'suomi', 'sv' => 'svenska', 'vi' => 'tiengviet', 'tr' => 'turkish'];

	
/*---------- TOOLBOX FUNCTIONS ----------*/

//multi-byte utf-8 truncate on char boundary
function mbtrunc($string,$length) {
	if (strlen($string) <= $length) { return $string; }
	$ordNext = ord($string[$length]);
	if ($ordNext <= 127 or $ordNext >= 194) { return substr($string,0,$length); } //next byte is single byte or 1st byte of mb
	for ($i = ($length - 1); $i >= 0; $i--) {
		if (ord($string[$i]) <= 127) { return substr($string,0,$i+1); } //single byte
		if (ord($string[$i]) >= 194) { return substr($string,0,$i); } //1st byte of mb
	}
	return ''; //empty
}

//replace \n\r by {nl} and </tr> by </tr>\n
function eol2txt($string) {
	return preg_replace(["~\R~","~</tr>~"],["{nl}","</tr>\n "],trim($string));
}

//replace quotes by HTML entity\n
function unQuote($string) {
	return str_replace(["'",'"'],['&apos;','&quot;'],$string);
}

//time formatting
function ITtoDT($time,$format = '') { //convert hh:mm(:ss) to display time
	global $set;
	if (!$time or substr($time,0,2) == '99') { return ''; }
	if (!$format) { $format = $set['timeFormat']; }
	$ampm = stripos($format,'a') !== false;
	if ($ampm and substr($time,0,2) =='24') { $time = '12'.substr($time,2); }
	$phpFormat = str_replace(['h','H','m'],[($ampm ? 'g' : 'G'),($ampm ? 'h' : 'H'),'i'],$format);
	return date($phpFormat,strtotime($time));
}

function DTtoIT($time,$format = '') { //convert Display Time to ISO Time hh:mm
	global $set;
	$time = trim(str_replace(['.',','],':',$time));
	if (!$time) { return ''; }
	if (!$format) { $format = $set['timeFormat']; }
	$ampm = stripos($format,'a') !== false;
	$regEx = $ampm ? '(0{0,1}[0-9]|1[0-2])[:.][0-5][0-9]\s*(a|A|p|P)(m|M)' : '(0{0,1}[0-9]|1[0-9]|2[0-4])[:.][0-5][0-9]([:.][0-5][0-9]){0,1}';
	if (!preg_match("%^".$regEx."$%",$time)) { return false; }
	$tStamp = strtotime($time);
	return ($tStamp < 1) ? false : date("H:i", $tStamp);
}

//date formatting
function IDtoDD($date,$format = '') { //convert ISO date (yyyy mm dd) to display date
	global $set;
	if (!$date or substr($date,0,4) == '9999') { return ''; }
	if (!$format) { $format = $set['dateFormat']; }
	return str_replace(['y','m','d'],[substr($date,0,4),substr($date,5,2),substr($date,8,2)],$format);
}

function IDTtoDDT($dateTime) { //convert ISO date+time (yyyy mm dd hh:mm:ss) to display date
	global $xx;
	$date = substr($dateTime,0,10);
	if (!$date) { return ''; }
	$time = substr($dateTime,11,5);
	$dD = IDtoDD($date);
	$dT = ITtoDT($time);
	return $dD.($dT ? " {$xx['at_time']} {$dT}" : '');
}

function DDtoID($date,$format = '') { //validate display date and convert to ISO date (yyyy-mm-dd)
	global $set;
	$date = trim($date);
	if (!$date) { return ''; }
	if (!$format) { $format = $set['dateFormat']; }
	$indexY = strpos($format,'y') / 2;
	$indexM = strpos($format,'m') / 2;
	$indexD = strpos($format,'d') / 2;
	$split = preg_split('%[^\d]%',$date);
	if (count($split) != 3) { return false; } //invalid date format
	if ($split[$indexY] < 1800 or $split[$indexY] > 2200) { return false; } //year out of range
	if (!checkdate(intval($split[$indexM]),intval($split[$indexD]),intval($split[$indexY]))) { return false; } //invalid date
	return $split[$indexY]."-".substr("0".$split[$indexM],-2)."-".substr("0".$split[$indexD],-2);
}

function makeD($date,$formatNr,$x3 = '') { //make long date
	global $set, $months, $months_m, $wkDays, $wkDays_l;
	$y = intval(substr($date, 0, 4));
	$m = intval(ltrim(substr($date, 5, 2),"0"));
	$d = intval(ltrim(substr($date, 8, 2),"0"));
	if ($formatNr > 3) {
		$wdNr = date("N", mktime(12,0,0,$m,$d,$y));
		$wkDay = $x3 ? $wkDays_l[$wdNr] : $wkDays[$wdNr];
	}
	$month = $x3 ? $months_m[$m - 1] : $months[$m - 1];
	switch ($formatNr) {
	case 1: //Dec... 9 / 9 dec...
		return str_replace(['d','M'],[$d,$month],$set['MdFormat']);
	case 2: //Dec... 9, 2020 / 9 dec... 2020
		return str_replace(['d','y','M'],[$d,$y,$month],$set['MdyFormat']);
	case 3: //Dec... 2020 / dec... 2020
		return str_replace(['y','M'],[$y,$month],$set['MyFormat']);
	case 4: //Mon..., Dec... 9 / mon 9 dec
		return str_replace(['d','M','WD'],[$d,$month,$wkDay],$set['DMdFormat']);
	case 5: //Mon..., Dec... 9, 2020 / mon... 9 dec... 2020
		return str_replace(['d','y','M','WD'],[$d,$y,$month,$wkDay],$set['DMdyFormat']);
	}
}

//make event time
function makeTime($ald,$ntm,$mde,$sti,$eti) {
	global $xx;
	
	$txtAD = $ald ? $xx['vws_all_day'] : ''; //text for all day or no time
	switch ($mde) { //multi-day event?
		case 0: $evtT = ($ald or $ntm) ? $txtAD : ITtoDT($sti).($eti ? ' - '.ITtoDT($eti) : ''); break; //no
		case 1: $evtT = ($sti != '00:00' and $sti != '') ? $xx['from']." ".ITtoDT($sti) : $txtAD; break; //first
		case 2: $evtT = $txtAD; break; //in between
		case 3: $evtT = ($eti < '23:59' and $eti != '') ? $xx['until']." ".ITtoDT($eti) : $txtAD; //last
	}
	return $evtT;
}

//make full date/time
function makeFullDT($iso,$sda,$eda,$sti,$eti,$ald) {
	global $xx;
	$fullDT = $iso ? IDtoDD($sda) : $sda;
	if ($sti) { $fullDT .= " {$xx['at_time']} ".($iso ? ITtoDT($sti) : $sti); }
	if (($eda and $eda[0] != 9) or $eti) { $fullDT .= ' -'; }
	if ($eda and $eda[0] != 9) { $fullDT .= ' '.($iso ? IDtoDD($eda) : $eda).($eti ? " {$xx['at_time']}" : ''); }
	if ($eti) { $fullDT .= ' '.($iso ? ITtoDT($eti) : $eti); }
	if ($ald) { $fullDT .= " {$xx['vws_all_day']}"; }
	return $fullDT;
}

//make event head for MWD views
function makeHead(&$evt,$template,$date) {
	global $usr, $set, $xx;

	$template = '|'.trim($template,'|').'|';
	preg_match_all('~(#ts|#tx|#e|#o|#v|#lv|#c|#lc|#a|#x1|#lx1|#x2|#lx2|#/)~i',$template,$comps); //split components
	$keys = $comps[1];
	$html = [];
	foreach($keys as $c) { //process components
		$subStr = '';
		switch ($c) {
		case '#ts':
			if (!$evt['ntm']) {
				if ($evt['mde']) {
					$subStr = makeHovT($evt);
				} elseif ($evt['sti']) {
					$subStr = ITtoDT($evt['sti']);
				}
			}
			break;
		case '#tx':
			if (!$evt['ntm'] and !$evt['ald']) {
				$subStr = makeHovT($evt);
			}
			break;
		case '#e':
			$subStr = $evt['tit'];
			break;
		case '#o':
			$subStr = $evt['una'];
			break;
		case '#lv':
		case '#v':
			if ($evt['ven']) {
				if ($c[1] == 'l') { $subStr = $xx['evt_venue'].': '; }
				$subStr .= str_replace('<a ','<a onclick="event.stopPropagation();" ',makeVenue($evt['ven']));
			}
			break;
		case '#lc':
		case '#c':
			$subStr = ($c[1] == 'l' ? $xx['evt_category'].': ': '').$evt['cnm'];
			break;
		case '#a':
			$age = ($evt['rpt'] == 4 and preg_match('%\(((?:19|20)\d\d)\)%',$evt['tx3'].$evt['tx2'].$evt['tx1'],$year)) ? strval(substr($date,0,4) - $year[1]) : ''; //(year) in one of the tx field
			if ($age) { $subStr = $age; }
			break;
		case '#lx1':
		case '#x1':
			if ($usr['privs'] >= $set['xField1Rights'] and $evt['tx2']) {
				if ($c[1] == 'l') { $subStr = ($set['xField1Label'] ?: $xx['sch_extra_field1']).': '; }
				$subStr .= str_replace('<a ','<a onclick="event.stopPropagation();" ',$evt['tx2']);
			}
			break;
		case '#lx2':
		case '#x2':
			if ($usr['privs'] >= $set['xField2Rights'] and $evt['tx3']) {
				if ($c[1] == 'l') { $subStr = ($set['xField2Label'] ?: $xx['sch_extra_field2']).': '; }
				$subStr .= str_replace('<a ','<a onclick="event.stopPropagation();" ',$evt['tx3']);
			}
			break;
		case '#/':
			$subStr = '<br>';
		}
		$html[] = $subStr;
		if (!$subStr) {
			$template = str_replace($c,'',$template); //remove empty component
		}
	}
	$template = preg_replace("%\|[^#]*\|%",'|',$template); //remove empty sections
	$evtStr = trim(str_replace($keys,$html,$template)); //substitute keys
	$evtStr = str_replace('|','',$evtStr); //remove separators
	return preg_replace(["%<img\s[^>]+>%","%(<br>\s*)+%","%(<br>\s*)+$%"],['','<br>',''],$evtStr); //remove images and empty lines
}

//make venue field
function makeVenue($venue) {
	global $set, $xx;

	if ($venue) {
		if ($set['mapViewer'] and preg_match("%^([^!]*)!\s*([^!$]+)\s*(?:!\s*(.*)|$)%",$venue,$matches)) {
			$urlAddr = urlencode($matches[2]);
			$mapLink = " <a title='{$matches[2]}' href='{$set['mapViewer']}{$urlAddr}' target='_blank'><button>{$xx['vws_address']}</button></a>";
			$suffix = empty($matches[3]) ? '' : ' '.$matches[3];
			return $matches[1].$mapLink.$suffix;
		} else {
			return str_replace('!','',$venue);
		}
	}
	return '';
}

//make hover box time
function makeHovT(&$evt) {
	global $xx;
	switch ($evt['mde']) { //multi-day event?
		case 0: return $evt['ald'] ? $xx['vws_all_day'] : ITtoDT($evt['sti']).($evt['eti'] ? ' - '.ITtoDT($evt['eti']) : ''); break; //no
		case 1: return (($evt['sti'] != '00:00' and $evt['sti'] != '') ? ITtoDT($evt['sti']) : '&bull;').'&middot;&middot;&middot;'; break; //first
		case 2: return '&middot;&middot;&middot;'; break; //in between
		case 3: return '&middot;&middot;&middot;'.(($evt['eti'] < '23:59' and $evt['eti'] != '') ? ITtoDT($evt['eti']) : '&bull;'); //last
	}
}

//make hover box pop attribute
function makePopAttrib(&$evt,$date,$noImg=0) {
	global $templ, $winXS;

	if (!$templ['pop']) { return ''; } //no pop fields specified in template
	$time = !$evt['ntm'] ? makeHovT($evt).': ' : '';
	$chBox = '';
	if ($evt['cbx']) {
		$offset = strval(round((strtotime($date) - strtotime($evt['sda'])) / 86400)); //days
		$chBox = "<span class='chkBox'>".(cMark($evt,$date) ? $evt['cmk'] : '&#x2610;')."</span>";
	}
	$popText = "<b>{$chBox} {$time}{$evt['tix']}</b><br>";
	$popText .= makeE($evt,$templ['pop'],'br','<br>');
	if ($noImg) { $popText = preg_replace('~<img.+?>~i','',$popText); } //remove images
	$popText = str_replace(["'",'"'],['&apos;','&quot;'],$popText); //escape quotes
	$popClass = (($evt['mde'] or $evt['r_t']) ? 'repeat' : 'normal').($evt['pri'] ? ' private' : '');
	$appClass = ($evt['app'] and !$evt['apd']) ? ' class="toAppr"' : '';
	$maxChars = $winXS ? 35 : 80;
	$popAttrib = " onmouseover='pop(this,`<div{$appClass}>{$popText}</div>`,`{$popClass}`,{$maxChars})'";
	return $popAttrib;
}

//make event color style
function colorStyle(&$evt,$defBgd='') {
	global $set;

	$defBgd = $defBgd ? 'background-color:'.$defBgd.';' : '';
	if ($set['eventColor'] == 1) { //cat color
		$eStyle = ($evt['cco'] ? 'color:'.$evt['cco'].';' : '').($evt['cbg'] ? 'background-color:'.$evt['cbg'].';' : $defBgd);
	} elseif ($set['eventColor'] == 2) { //group color
		$eStyle = $evt['uco'] ? 'background-color:'.$evt['uco'].';' : $defBgd;
	} else {
		$eStyle = $defBgd;
	}
	return $eStyle;
}

//make 'complete' check box
function checkBox(&$evt,$date,$mde='') {
	global $usr;

	$mayCheck = ($usr['privs'] > 2 or ($usr['privs'] > 1 and $evt['uid'] == $usr['ID'])); //boolean
	$chBox = !($mde and $evt['mde']) ? (cMark($evt,$date) ? $evt['cmk'] : '&#x2610;') : '?';
	$cBoxAtt = ($mayCheck and !($mde and $evt['mde'])) ? "class='chkBox' onclick='checkE(this,{$evt['eid']},`{$date}`); event.stopPropagation();'" : 'class="chkBox arrow" onclick="event.stopPropagation();"';
	return "<span title='{$evt['clb']}' {$cBoxAtt}>{$chBox}</span>";
}

//check mark
function cMark(&$evt,$date) {
	$offset = strval(round((strtotime($date) - strtotime($evt['sda'])) / 86400)); //days
	return strpos($evt['chd'],";{$offset}") !== false;
}

//exclude date from series
function xDate($xDates,$sda,$date) {
	$offset = strval(round((strtotime($date) - strtotime($sda)) / 86400)); //days
	return strpos($xDates,";{$offset}") !== false;
}

//make repeat text
function repeatText($type,$interval,$period,$rmonth,$until) {
	global $xx, $months, $wkDays;

	switch ($type) {
		case -1: $repTxt = "<b>{$xx['evt_repeat_not_supported']}</b>"; break;
		case 0: $repTxt = ''; break;
		case 1: $repTxt = $xx['evt_repeat_on'].' '.$interval.' '.$xx['evt_period1_'.$period]; break;
		case 2: $repTxt = $xx['evt_repeat_on'].' '.$xx['evt_interval2_'.$interval].' '.$wkDays[$period].' '.$xx['of'].' '.($rmonth ? $months[$rmonth-1] : $xx['evt_each_month']); break;
		case 3: $repTxt = $xx['evt_rolling'];
	}
	if ($type > 0 and $until and $until[0] != 9) {
		$repTxt .= " {$xx['evt_until']} ".IDtoDD($until);
	}
	return $repTxt;
}

//make event body using template
function makeE(&$evt,$template,$type,$glue,$show = '12345678') {
	global $set, $usr, $xx;

	if ($usr['privs'] < $set['xField1Rights']) { //exclude xField 1
		$show = str_replace('4','',$show);
	} else {
		$tx2 = preg_replace('~#.*#~','',$evt['tx2']); //remove birthday tag
	}
	if ($usr['privs'] < $set['xField2Rights']) { //exclude xField 2
		$show = str_replace('5','',$show);
	} else {
		$tx3 = preg_replace('~#.*#~','',$evt['tx3']); //remove birthday tag
	}

	$eArray = [];
	if ($type[0] == 'b') { //type <br>
		foreach (str_split($template) as $fieldNr) {
			if (strpos($show,$fieldNr) === false) { continue; }
			switch ($fieldNr) {
			case '1': 
				if ($evt['ven']) { $eArray[] = "{$xx['evt_venue']}: ".makeVenue($evt['ven']); }
				break;
			case '2':
				$eArray[] = "{$xx['evt_category']}: {$evt['cnm']}".($evt['snm'] ? " - {$evt['snm']}" : ''); break;
			case '3':
				if ($evt['tx1']) { $eArray[] = $type[1] == 'x' ? hyperImg($evt['tx1']) : $evt['tx1']; } break;
			case '4':
				if ($tx2) { $eArray[] = ($set['xField1Label'] ? "{$set['xField1Label']}: " : '').($type[1] == 'x' ? hyperImg($tx2) : $tx2); } break;
			case '5':
				if ($tx3) { $eArray[] = ($set['xField2Label'] ? "{$set['xField2Label']}: " : '').($type[1] == 'x' ? hyperImg($tx3) : $tx3); } break;
			case '6':
				if ($evt['nom'] >= 0) { $eArray[] = "{$xx['vws_notify']}: {$evt['nom']} {$xx['vws_days']}"; }
				break;
			case '7':
				$eArray[] = "{$xx['vws_added']}: ".IDTtoDDT($evt['adt'])." ({$evt['una']})";
				if ($evt['mdt'] and $evt['edr']) { $eArray[] = "{$xx['vws_edited']}: ".IDTtoDDT($evt['mdt'])." ({$evt['edr']})"; }
				break;
			case '8':
				if ($evt['att']) {
					$attachments = [];
					foreach(explode(';',trim($evt['att'],';')) as $attachment) {
						$attachments[] = "<a title='{$xx['evt_click_to_open']}' href='".calRootUrl()."dloader.php?ftd=./attachments/".rawurlencode($attachment)."&amp;nwN=".substr($attachment,14)."'>".substr($attachment,14)."</a>";
					}
					$eArray[] = $xx['evt_attachments'].': '.implode(', ',$attachments);
				}
			}
		}
	} elseif ($type[0] == 't') { //type <td>
		foreach (str_split($template) as $fieldNr) {
			if (strpos($show,$fieldNr) === false) { continue; }
			switch ($fieldNr) {
			case '1':
				if ($evt['ven']) { $eArray[] = "<tr><td>{$xx['evt_venue']}:</td><td>".makeVenue($evt['ven'])."</td></tr>"; }
				break;
			case '2':
				$eArray[] = "<tr><td>{$xx['evt_category']}:</td><td>{$evt['cnm']}".($evt['snm'] ? " - {$evt['snm']}" : '')."</td></tr>"; break;
			case '3':
				if ($evt['tx1']) { $eArray[] = "<tr><td>{$xx['evt_description']}:</td><td>".($type[1] == 'x' ? hyperImg($evt['tx1']) : $evt['tx1'])."</td></tr>"; } break;
			case '4':
				if ($tx2) { $eArray[] = "<tr><td>".($set['xField1Label'] ? "{$set['xField1Label']}: " : '')."</td><td>".($type[1] == 'x' ? hyperImg($tx2) : $tx2)."</td></tr>"; } break;
			case '5':
				if ($tx3) { $eArray[] = "<tr><td>".($set['xField2Label'] ? "{$set['xField2Label']}: " : '')."</td><td>".($type[1] == 'x' ? hyperImg($tx3) : $tx3)."</td></tr>"; } break;
			case '6':
				if ($evt['nom'] >= 0) { $eArray[] = "<tr><td>{$xx['vws_notify']}:</td><td>{$evt['nom']} {$xx['vws_days']}</td></tr>"; }
				break;
			case '7':
				$eArray[] = "<tr><td>{$xx['vws_added']}:</td><td>".IDTtoDDT($evt['adt'])." ({$evt['una']})</td></tr>";
				if ($evt['mdt'] and $evt['edr']) { $eArray[] = "<tr><td>{$xx['vws_edited']}:</td><td>".IDTtoDDT($evt['mdt'])." ({$evt['edr']})</td></tr>"; }
				break;
			case '8':
				if ($evt['att']) {
					$label = $xx['evt_attachments'].':';
					foreach(explode(';',trim($evt['att'],';')) as $attachment) {
						$eArray[] = "<tr><td>{$label}</td><td><a title='{$xx['evt_click_to_open']}' href='".calRootUrl()."dloader.php?ftd=./attachments/".rawurlencode($attachment)."&amp;nwN=".substr($attachment,14)."'>".substr($attachment,14)."</a></td></tr>";
						$label = '';
					}
				}
			}
		}
	} elseif ($type[0] == 'c') { //type CSV
		foreach (str_split($template) as $fieldNr) {
			if (strpos($show,$fieldNr) === false) { continue; }
			switch ($fieldNr) {
			case '1': 
				$eArray[] = makeVenue($evt['ven']); break;
			case '2':
				$eArray[] = $evt['cnm'].($evt['snm'] ? " - {$evt['snm']}" : ''); break;
			case '3':
				$eArray[] = $evt['tx1']; break;
			case '4':
				$eArray[] = $tx2; break;
			case '5':
				$eArray[] = $tx3; break;
			}
		}
	}
	return implode($glue,$eArray);
}

//
//Check on overlap. For recurring events look ahead $chkYears years
//
function overlap($typ,$eid,$cid,$sDate,$eDate,$xDates,$sTime,$eTime,$catRpt,$catNol,$catOlg,$catOem,$r_t,$r_i,$r_p,$r_m,$r_u) { //check for no overlap
	global $evtList, $usr, $nowTS;
	
	//Number of years to look ahead for overlaps
	$chkYears = 2;
	
	//prepare overlap test
	$filter = " AND e.`eTime` != '00:00'"; //exclude "no time" events
	if ($catNol == 0) { //check against all "no overlap at all"
		$filter .= " AND (c.`noverlap` = 2)";
	} elseif ($catNol == 1) { //check against all existing "no overlap in same cat" and "no overlap at all"
		$filter .= " AND ((c.`noverlap` = 1 AND c.`ID` = $cid) OR c.`noverlap` = 2)".($eid ? " AND e.`ID` != {$eid}" : ''); //if update, exclude event self		
	} elseif ($catNol == 2) { //check against all events
		$filter .= $eid ? " AND e.`ID` != {$eid}" : ''; //if update, exclude event self
	}
	$usrPrivs = $usr['privs']; //set privs temporary to admin to catch all events
	$usr['privs'] = 9;
	$dUts = ($eDate[0] != '9') ? strtotime($eDate) - strtotime($sDate) : 0; //delta start date - end date uts
	if ($eTime[0] == '9') { $eTime = $sTime; } //no end time
	$sDateEvt = $sDate; //event start date

	if ($catRpt > 0) { //cat repeat overrides
		$r_t = $r_i = 1;
		$r_p = $catRpt;
		$r_u = '9999-00-00';
	}
	if ($r_t == 2) {
		$sDate = nextRdate2($sDate,$r_i,$r_p,$r_m,0); //1st occurrence of xth <dayname> in month y
	}
	//now $sDate is the first date for $r_t = 0, 1 or 2
	$eDate = $dUts > 0 ? date("Y-m-d",strtotime($sDate) + $dUts) : $sDate;
	if (!$r_u) { $r_u = '9999-00-00'; }
	$uDate = min($r_u,date("Y-m-d",$nowTS + (32000000 * $chkYears))); //check until date ($r_u or $lookAhead years)
	$oDate = $oMsg = '';
	do {
		//retrieve 'no-overlap' events in same date/time bracket
		$sTimeNew = strtotime($sDate.' '.$sTime.':00');
		$eTimeNew = strtotime($eDate.' '.$eTime.':00');
		$vCats = $usr['vCats']; //backup vCats
		$usr['vCats'] = '0'; //temp set vCats to 'all'
		retrieve(date("Y-m-d"),$eDate,'',[$filter,''],$typ); //only existing events starting today or later
		$usr['vCats'] = $vCats; //restore vCats
		//overlap check
		foreach ($evtList as $date => $calEvts) {
			if ($xDates and xDate($xDates,$sDateEvt,$date)) { continue; } //skip if $date is excluded
			foreach ($calEvts as $evt) { //check events on this day
				if (!$evt['sti'] or $evt['mde'] >= 2) { $evt['sti'] = '00:00'; } //no sti or mde not the first day
				if (!$evt['eti'] or $evt['mde'] == 1 or $evt['mde'] == 2) { $evt['eti'] = '23:59'; } //no eti or mde not the last day
				$sTimeCal = strtotime($date.' '.$evt['sti'].':00');
				$eTimeCal = strtotime($date.' '.$evt['eti'].':00');
				if ($catNol == $evt['nol']) { //both 1 => always same cat; both 2 => same or diff cats
					$minGap = max($catOlg,$evt['olg']); //biggest gap
				} elseif ($catNol < $evt['nol']) {
					$minGap = $evt['olg']; //gap of existing event
				} else {
					$minGap = $catOlg; //gap of new event
				}
				if ($sTimeNew < ($eTimeCal + ($minGap * 60)) and ($eTimeNew + ($minGap * 60)) > $sTimeCal) { //overlap
					$oMsg = $catOem ?: $evt['oem']; //overlap error message
					$oDate = $date;
					break 3;
				}
			}
		}
		if ($r_t > 0) {
			$sDate = ($r_t == 1) ? nextRdate1($sDate,$r_i,$r_p) : nextRdate2($sDate,$r_i,$r_p,$r_m,1);
			$eDate = date("Y-m-d",strtotime($sDate) + $dUts);
		}
	} while ($r_t > 0 and $sDate <= $uDate);
	$usr['privs'] = $usrPrivs; //restore privs
	return $oMsg ? IDtoDD($oDate).': '.$oMsg : '';
}

//Compute next event start date - repeat every xth ($rI) day, week, month or year ($rP)
function nextRdate1($curD, $rI, $rP) {
	$curT = strtotime($curD.' 12:00:00');
	$curDoM = date('j',$curT);
	switch ($rP) { //period
	case 1: //day
		$nUts = strtotime("+$rI days",$curT); break;
	case 2: //week
		$nUts =  strtotime("+$rI weeks",$curT); break;
	case 3: //month
		$i = 1;
		while(date('j',strtotime('+'.$i*$rI.' months',$curT)) != $curDoM) { $i++; } //deal with 31st
		$nUts =  strtotime('+'.$i*$rI.' months',$curT); break;
	case 4: //year
		$i = 1;
		while(date('j',strtotime('+'.$i*$rI.' years',$curT)) != $curDoM) { $i++; } //deal with 29/02
		$nUts =  strtotime('+'.$i*$rI.' years',$curT); break;
	}
	return date("Y-m-d",$nUts);
}

//Compute next event start date - repeat on the xth ($rI) <dayname> ($rP) of month y ($rM)
function nextRdate2($curD, $rI, $rP, $rM, $i) { //$i=0: 1st occurrence; $i=1: next occurrence
	if ($rM) {
		$curM = $rM; //one specific month
		$curY = substr($curD,0,4)+$i+((substr($curD,5,2) <= $rM) ? 0 : 1);
	} else { //each month
		$curM = substr($curD,5,2)+$i;
		$curY = substr($curD,0,4);
	}
	$day1Ts = mktime(12,0,0,$curM,1,$curY);
	$dowDif = $rP - date('N',$day1Ts); //day of week difference
	$offset = $dowDif + 7 * $rI;
	if ($dowDif >= 0) { $offset -= 7; }
	if ($offset >= date('t',$day1Ts)) { $offset -= 7; } //'t': number of days in the month
	return date("Y-m-d",$day1Ts + (86400 * $offset));
}

//expand images to image hyperlinks
function hyperImg($text) {
	global $rxIMGTags;
	
	return preg_replace($rxIMGTags,"<a href='./thumbnails/$1' target='_blank'>$0</a>",$text);
}

//get calendar base URL (used at install and upgrade)
function calBaseUrl() {
	$httpX = (!empty($_SERVER['HTTPS']) and $_SERVER['HTTPS'] != 'off' or $_SERVER['SERVER_PORT'] == '443') ? 'https' : 'http'; 
	$baseUrl = $httpX.'://'.$_SERVER['SERVER_NAME'];
	$baseUrl .= rtrim(dirname($_SERVER["PHP_SELF"]),'/').'/'; // add calendar directory
	return $baseUrl;
}

//get calendar root URL
function calRootUrl() {
	global $set;

	$rootUrl = strstr($set['calendarUrl'].'?','?',true);
	$rootUrl = strstr($rootUrl.'/index.php','/index.php',true);
	return rtrim($rootUrl,'/').'/';
}

//add URL, IMG and EML links
function addUrlImgEmlTags($html,$uie='xxx') {
	global $rxURL, $rxIMG, $rxEML, $xx;

	if ($uie[0] == 'x') { //create URL links
		$html = preg_replace_callback($rxURL,function ($m) { $bs = $m[2] != 'S:' ? 'blank' : 'self'; return "{$m[1]}<a class='link' href='{$m[3]}' target='_{$bs}'>".($m[5] ?: $m[4])."</a>{$m[6]}"; },$html);
	}
	if ($uie[1] == 'x') { //create image links
		$html = preg_replace_callback($rxIMG,function ($m) { return "{$m[1]}<img class='thNail' src='".calRootUrl()."thumbnails/{$m[2]}' alt='{$m[3]}'>{$m[4]}"; },$html);
	}
	if ($uie[2] == 'x') { //create email links
		$html = preg_replace_callback($rxEML,function ($m) { global $tit, $sda, $xx; return "{$m[1]}<a class='link' href='mailto:{$m[2]}@{$m[3]}.{$m[4]}?subject=$sda%20-%20".str_replace(' ','%20',$tit)."'>".($m[5] ?: $xx['vws_send_mail'])."</a>{$m[6]}"; },$html);
	}
	return $html;
}

//remove URL, IMG and EML links
function remUrlImgEmlTags($html,$uie='xxx') {
	global $rxULink, $rxIMGTags, $rxELink;

	if ($uie[0] == 'x') { //remove URL links
		$html = preg_replace_callback($rxULink,function ($m) { $bs = $m[3] != '_b' ? 'S:' : ''; return $bs.$m[1].($m[2] != $m[4] ? " [".$m[4]."]" : ""); },$html);
	}
	if ($uie[1] == 'x') { //remove image links
		$html = preg_replace($rxIMGTags,"$1",$html);
	}
	if ($uie[2] == 'x') { //remove email links
		$html = preg_replace($rxELink,"$1 [$2]",$html);
	}
	return $html;
}

//chunk split unicode string
function chunk_split_unicode($str,$len,$eol) {
	$chunks = array_chunk(preg_split('%%u',$str,-1,PREG_SPLIT_NO_EMPTY),$len);
	$str = '';
	foreach ($chunks as $chunk) {
		$str .= implode('',$chunk).$eol;
	}
	return rtrim($str);
}

//transliterate text string (e.g. file name)
function translit($text,$strict=false) {
	setlocale(LC_CTYPE,'en_US');
	$transText = iconv('UTF-8','ASCII//TRANSLIT',$text);
	if ($strict) {
		return str_replace([' ','/','\\','?','%','*','+',':',';','{','}',"'",'"'],'_',$transText);
	} else {
		return $transText;
	}
}

//load selections from cookie LXCsel_<calID> (must be called after validateInputVars)
function loadLastSel() {
	global $calID;

	$opt = isset($_COOKIE["LXCsel_{$calID}"]) ? @unserialize($_COOKIE["LXCsel_{$calID}"]) : ['uI' => '01'];
	if (!isset($opt['uT'])) { $opt['uI'] = '01'; } //bake: no, user: public user
	if (substr($opt['uI'],1) != '1') { //logged in user - protected with token
		$stH = stPrep("SELECT `ID` FROM `users` WHERE `ID` = ? AND `token` LIKE '%{$opt['uT']}%' AND status >= 0");
		stExec($stH,[substr($opt['uI'],1)]); //check user ID and token
		if (!($row = $stH->fetch(PDO::FETCH_ASSOC))) { //unknown user
			$opt['uI'] = '01'; //bake: no, user: public user
		}
		$stH = null;
	}
	return $opt;
}

//save selections to cookie LXCsel_<calID>
function saveLastSel(&$opt) {
	global $set, $calID, $calPath;

	if ($_SESSION['pageCount'] == 1 and substr($opt['uI'],1) != '1') { //new visit of logged in user - protect with token
		$token = md5(rand());
		$stH = stPrep("SELECT `token` FROM `users` WHERE `ID` = ? AND status >= 0");
		stExec($stH,[substr($opt['uI'],1)]); //get user token
		$user = $stH->fetch(PDO::FETCH_ASSOC);
		if (isset($opt['uT'])) {
			$dbToken =  str_replace($opt['uT'],$token,$user['token'],$count);
		}
		if (empty($count)) {
			$dbToken = substr($user['token'],-165).$token; //login from max. 5 devices
		}
		$stH = stPrep("UPDATE `users` SET `token` = '{$dbToken}' WHERE `ID` = ?");
		stExec($stH,[substr($opt['uI'],1)]); //set new token for user
		$stH = null;
		$opt['uT'] = $token; //add new token to options
	}
	setcookie("LXCsel_{$calID}", serialize($opt), time() + (86400 * $set['cookieExp']),$calPath); //keep data for 'cookieExp' days
}

//log off user
function logoff(&$opt) {
	global $calID, $calPath;

	if (substr($opt['uI'],1) != '1') { //logged in user - remove token and cookie
		$tknSign = $opt['uI'][0] == '0' ? '-' : '+'; //+: remember, -: forget
		$stH = stPrep("UPDATE `users` SET `token` = REPLACE(`token`,'{$tknSign}{$opt['uT']}','') WHERE `ID` = ?");
		stExec($stH,[substr($opt['uI'],1)]); //remove token for user
		$stH = null;
		unset($opt['uT']); //remove token from options
	}
	setcookie("LXCsel_{$calID}", "", time() - 3600,$calPath); //remove cookie
}

//get calendar ID
function getCalID() {
	global $dbDef, $nowTS, $calPath;
	
	$cIDs = [];
	if (isset($_COOKIE['LXCcid'])) { $cIDs['cook'] = unserialize($_COOKIE['LXCcid']); } //cookie
	if (isset($_REQUEST['cal'])) { $cIDs['cal'] = $_REQUEST['cal']; } //new calendar
	if (isset($_POST['calID'])) { $cIDs['post'] = $_POST['calID']; } //via form
	if (isset($_POST['cal1x'])) { $cIDs['c1x'] = $_POST['cal1x']; } //edit or show event
	foreach($cIDs as $k => $cID) { //validate possible calID inputs
		if (!preg_match('~^[\w-]{1,20}$~',$cID)) {
			echo "Invalid calendar ID ({$k})"; exit(); //error: invalid calendar ID
		}
	}
	//now we have valid cal IDs
	$calID = $cIDs['cook'] ?? $dbDef;
	if (isset($cIDs['post'])) { //via form
		$calID = $cIDs['post'];
	} elseif (isset($cIDs['cal']) and $cIDs['cal'] != $calID) { //switch calendar
		$calID = $cIDs['cal'];
		$_POST = $_REQUEST = []; //reset
	}
	setcookie('LXCcid',serialize($calID),$nowTS+2592000,$calPath); //set calID cookie to 30 days
	if (isset($cIDs['c1x'])) { $calID = $cIDs['c1x']; } //switch calendar just once (edit or show event)
	return $calID;
}

//validate input variables
function validInputVars() {
	global $calID;
	
	$allVars = [];
	if (isset($_GET)) { $allVars['GET'] = &$_GET; }
	if (isset($_POST)) { $allVars['POST'] = &$_POST; }
	if (isset($_COOKIE["LXCsel_{$calID}"])) { $allVars['COOKIE'] = @unserialize($_COOKIE["LXCsel_{$calID}"]); }
	//validate all fixed format vars and sanitize free format vars
	$ok = true;
	foreach ($allVars as $group => &$varArray) {
		foreach ($varArray as $name => &$value) {
			switch ($name) {
				case 'action': $ok = preg_match('~^\w{2,11}$~',$value); break;
				case 'xP': $ok = preg_match('~^\d{1,2}$~',$value); break;
				case 'cP': $ok = preg_match('~^(\d{1,2}|up)$~',$value); break;
				case 'cG': $ok = (is_array($value) and ctype_digit(implode('',$value))); break;
				case 'cU': $ok = (is_array($value) and ctype_digit(implode('',$value))); break;
				case 'cC': $ok = (is_array($value) and preg_match('~^[0-9\-]+$~',implode('',$value))); break;
				case 'cL': $ok = empty($value) ? true : preg_match('~^[a-zA-Z]{1,12}$~',$value); break;
				case 'cD': $ok = empty($value) ? true : preg_match('~^\d{4}-\d{2}-\d{2}$~',$value); break; //ID
				case 'nD': $ok = empty($value) ? true : preg_match('~^\d{2}[^\d]\d{2}[^\d]\d{4}$~',$value); break; //DD
				case 'hdr': $ok = preg_match('~^(0|1|-1|-2)$~',$value); break;
				case 'tkn': $ok = preg_match('~^[\da-f]{32}$~',$value); break; //form token
				case 'uI': $ok = preg_match('~^(0|1)\d{1,6}$~',$value); break; //last saved
				case 'tS': $ok = preg_match('~^\d{10}$~',$value); break; //last saved
				case 'uT': $ok = preg_match('~^[\da-f]{32}$~',$value); break; //last saved
				case 'pword':
				case 'pword2': $vars[$name] = str_replace(['<','>'],'~',$value); break;
				default: //free format
					if (is_string($value)) { //sanitize free format POST and GET values
						if ($group == 'POST' and $name != 'infoText') {
							$_POST[$name] = $_REQUEST[$name] = strip_tags(preg_replace(['~%[0-9A-F]{2}~i'],'',trim($value)),'<a><b><i><u><s><sub><sup><img><br>');
						} elseif ($group == 'GET') {
							$_GET[$name] = $_REQUEST[$name] = strip_tags(preg_replace(['~%[0-9A-F]{2}~i'],'',trim($value)));
						} elseif ($group == 'COOKIE') {
							$ok = false;
						}
					}
			}
			if (!$ok) { break 2; }
		}
	}
	if (!$ok) {
		if (is_array($value)) { $value = 'array: '.implode('|',$value); }
		logMessage('luxcal',2,"Invalid {$group} variable {$name}=".htmlspecialchars($value,ENT_QUOTES | ENT_HTML5,'UTF-8'));
		note("Invalid {$group} variable {$name}");
		$append =  $group == 'COOKIE' ? "<br><br><b>Delete calendar cookies!</b>" : '';
		return "Invalid {$group} variable {$name}{$append}";
	}
	unset($group,$name,$value);
	return '';
}

//check form token
function checkToken($page) {
	$error = ''; //init
	$tknName = "LXCtkn_{$_POST['calID']}:{$page}";
	if (empty($_SESSION[$tknName])) { $error = '#1<br><br>#2'; $cause = 'no token assigned'; }
	elseif (empty($_POST['tkn'])) { $error = '#1<br><br>#2'; $cause = 'no token received'; }
	elseif ($_SESSION[$tknName] != $_POST['tkn']) { $error = '#3<br><br>#2.'; $cause = 'invalid token'; }
	if ($error) { //error
		logMessage('luxcal',2,"Access denied. Invalid POST variable.\nPage: {$page}\nCause: {$cause}\nForm input keys:\n- ".implode("\n- ",array_keys($_POST)));
		note($cause);
	} else { //no error
		unset($_SESSION[$tknName]); //delete token
	}
	return $error;
}

//strip not allowed HTML tags and annul not closed tags
function validTags($string,$tags) {
	$string = strip_tags(trim($string),$tags);
	if (preg_match_all("~<(.(.{2})?>)~",$string,$matches, PREG_SET_ORDER)) {
		foreach ($matches as $match) {
			if (strpos($string,"</{$match[1]}") === false) {
				$string = str_replace($match[0],"{$match[0]}</{$match[1]}",$string);
			}
		}
	}
	return $string;
}

function sanitize($var) { //used by displays
	return strip_tags(urldecode(trim($var)));
}

//log message
function logMessage($logName,$level,$logMsg,$script='-') {
	global $set;

	$calID = !empty($GLOBALS['calID']) ? $GLOBALS['calID'].':' : '';
	$levels = [0 => 'CRONJOB','ERROR','WARNING','NOTICE'];
	if ($level < 2 or ($level == 2 and $set['logWarnings']) or ($level == 3 and $set['logNotices'])) {
		date_default_timezone_set(@date_default_timezone_get());
		if ($script == '-') { $script = $_SERVER['PHP_SELF']; }
		$intro = "\n".date('Y.m.d H:i:s')." {$calID}{$levels[$level]} Script: ".htmlentities($script);
		file_put_contents("./logs/{$logName}.log","{$intro} - {$logMsg}",FILE_APPEND | LOCK_EX);
	}
}

//log notification message
function logNotMsg($level,$logMsg) {
	global $set;

	$calID = !empty($GLOBALS['calID']) ? $GLOBALS['calID'].'~' : '';
	$logPath = "./logs/{$calID}messages.log";
	if (is_file($logPath)) {
		$truncDate = date('Y.m.d',time() - ($set['msgLogWeeks'] * 604800));
		$logArr = file($logPath, FILE_IGNORE_NEW_LINES);
		foreach($logArr as $k => $log) {
			if (substr($log,0,10) > $truncDate) { break; }
			unset($logArr[$k]);
		}
	}
	$logArr[] = date('Y.m.d H:i')." {$logMsg}\n";
	file_put_contents($logPath,implode("\n",$logArr), LOCK_EX);
}

//show message in footer
function note($msg) {
	global $note, $set;

	if (!empty($set['maintMode'])) { //calendar runs in maintenance mode
		if (!empty($note)) { $note .= ' / '.$msg; } else { $note = $msg; }
	}
}
?>