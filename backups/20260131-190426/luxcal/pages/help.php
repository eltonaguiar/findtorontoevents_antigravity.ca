<?php
/*
= LuxCal help page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

$hP = !empty($_REQUEST['hP']) ? substr('0'.strval($_REQUEST['hP']),-2) : '00'; //help page (2 digits)
$bP = $_REQUEST['bP'] ?? 0; //back page
$fName1 = "./help/ug-{$hP}-{$opt['cL']}"; //possible c-s help file name ug-cp-curlang
$fName2 = "./help/ug-{$hP}-english"; //possible c-s help file name ug-cp-english
$fName3 = "./help/ug-{$hP}"; //possible context sensitive help file name ug-cp

$fName = ''; //help file name
if (file_exists($fName1.'.htm')) {
	$fName = $fName1.'.htm';
} elseif (file_exists($fName1.'.html')) {
	$fName = $fName1.'.html';
} elseif (file_exists($fName2.'.htm')) {
	$fName = $fName2.'.htm';
} elseif (file_exists($fName2.'.html')) {
	$fName = $fName2.'.html';
} elseif (file_exists($fName3.'.htm')) {
	$fName = $fName3.'.htm';
} elseif (file_exists($fName3.'.html')) {
	$fName = $fName3.'.html';
}
if ($fName) {
	echo "<div class='floatR'>\n{$xx['hdr_gen_help']}:&ensp;<button type='button' title=\"{$xx['hdr_gen_guide']}\" onclick='help(0,{$hP});'>{$xx['hdr_button_help']}</button>\n</div><br>&nbsp;\n";
	echo file_get_contents($fName); //c-s help
} else {
	if ($bP) {
		echo "<div class='floatR'>{$xx['hdr_prev_help']}:&ensp;<button type='button' title=\"{$xx['hdr_cs_guide']}\" onclick='help({$bP});'>{$xx['back']}</button></div><br>&nbsp;\n";
	}
	require("lang/ug-{$opt['cL']}.php"); //general help
}
?>
