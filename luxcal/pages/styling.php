<?php
/*
= Change Calendar Theme page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$adminLang = (file_exists("./lang/ai-{$opt['cL']}.php")) ? $opt['cL'] : "english";
require "./lang/ai-{$adminLang}.php"; //admin language file
require './common/toolboxx.php'; //admin tools
$msg = '';

if ($usr['privs'] != 9) { //no admin
	echo "<p class='error'>{$ax['no_way']}</p>\n"; exit;
}

function checkTheme(&$themeDefs) { //check & complete theme
	global $defSaS, $set;
	
	$diffArr = array_diff_key($themeDefs,$defSaS);
	foreach ($diffArr as $k => $v) { //delete unknown keys-value pairs
		unset($themeDefs[$k]);
	}
	$diffArr = array_diff_key($defSaS,$themeDefs);
	foreach ($diffArr as $k => $v) { //add missing keys-value pairs
		if ($k[0] != '0') { $themeDefs[$k] = $defSaS[$k]; }
	}
	if (empty($themeDefs['THEME'])) { $themeDefs['THEME'] = $set['calendarTitle']; }
}

function validateTheme(&$themeDefs) {//validate theme - non-color values
	$errArr = [];
	foreach ($themeDefs as $key => &$value) {
		$value = trim($value);
		if ($key[0] == 'F') { //font family
			$errArr[$key] = !preg_match('%^(([a-z]{3,20}|"[a-z\s]{3,20}"),\s*){1,2}[a-z-]{3,20}$%i',$value) ? " class='inputError'" : '';
		} elseif ($key[0] == 'P') { //font size px
			$errArr[$key] = !preg_match('%^1[0-9]$%',$value) ? " class='inputError'" : '';
		} elseif ($key[0] == 'M') { //font size em
			$errArr[$key] = !preg_match('%^(0\.[5-9]|1(\.[0-9])?)$%',$value) ? " class='inputError'" : '';
		} elseif ($key == 'sTbSw') { //shadow
			$errArr[$key] = !preg_match('%^[0-1]$%',$value) ? " class='inputError'" : '';
		} elseif ($key == 'sCtOf') { //content offset
			$errArr[$key] = !preg_match('%^\d\d?$%',$value) ? " class='inputError'" : '';
		}
	}
	return $errArr;
}

function getTheme($themeFile) { //get theme from file
	$themeDefs = [];
	$styles = file($themeFile,FILE_SKIP_EMPTY_LINES);
	foreach($styles as $style) {
		$style = trim($style);
		if (preg_match('~^"([A-Za-z0-9]{5})"\s?=>\s?"(.{3,})",~',trim($style),$matches)) {
			$themeDefs[$matches[1]] = $matches[2];
		}
	}
	checkTheme($themeDefs); //check against master $defSaS - unset unknown / add missing
	return $themeDefs;
}

function putTheme($themeDefs,$targetFile) { //put theme in file
	global $lcV, $defSaS, $set, $ax;

	if (empty($themeDefs['THEME'])) { $themeDefs['THEME'] = $set['calendarTitle']; }
	$themeFile = "<?php
/*
== LuxCal V{$lcV} event calendar theme ==
== Created: ".date("Y-m-d H:i")." ==
*/\n
/* ---- USER-INTERFACE STYLES ---- */\n\n
\$th = array(";
	foreach($defSaS as $key => $value) {
		if ($key[0] == '0') { //comment
			if ($key[2] == '0') { //heading
				$themeFile .= "\n\n/*====== {$value} ======*/\n";
			} else {
				$themeFile .= "\n//{$value}\n";
			}
			continue;
		}
		$value = isset($themeDefs[$key]) ? $themeDefs[$key] : $value;
		$k4 = 'sty_'.substr($key,1,4);
		$themeFile .= "\"{$key}\" => \"{$value}\",".($k4 != 'sty_HEME' ? " //{$ax[$k4]}" : '')."\n";
	}
	$nob = file_put_contents("./css/{$targetFile}",$themeFile.");\n?>");
	return $nob ? true : false;
}

function loadTheme() { //load theme from database
	$themeDefs = [];
	$stH = stPrep("SELECT name,value FROM `styles`");
	stExec($stH,null);
	while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
		$themeDefs[$row['name']] = $row['value'];
	}
	checkTheme($themeDefs); //check against master $defSaS - unset unknown / add missing
	return $themeDefs;
}

function storeTheme($themeDefs) { //store theme in database
	createDbTable("stylesX",1); //create temp table
	dbTransaction('begin');
	$stH = stPrep("INSERT INTO `stylesX` (`name`,`value`) VALUES (?,?)");
	foreach($themeDefs as $key => $value) {
		stExec($stH,[$key,$value]);
	}
	dbTransaction('commit');
	$stH = dbQuery("SELECT COUNT(*) FROM `stylesX`");
	$row = $stH->fetch(PDO::FETCH_NUM);
	if ($row[0] != count($themeDefs)) { return false; }
	$stH = null; //release statement handle
	dbQuery("DROP TABLE `styles`");
	dbQuery("ALTER TABLE `stylesX` RENAME TO `styles`");
	return true;
}

//program start

//initialize
$e = []; //error array
$errors = 0; //number of errors
$buDone =  $_POST['buD'] ?? false; //backup done?

$fSaS = []; //init
if (isset($_POST['prev']) or isset($_POST['save']) or isset($_POST['bkup']) or isset($_POST['close'])) { //fill pSaS array with form field styles
	foreach ($defSaS as $key => $void) { //get posted styles & settings
		if ($key[0] == '0') { continue; } //skip comment
		$fSaS[$key] = trim($_POST[$key]);
	}
} else {
	$fSaS = loadTheme(); //load theme from database
}

$e = validateTheme($fSaS);
foreach ($e as $value) { if (!empty($value)) $errors++; }

//init
$prevBut = $ax['sty_preview_theme'];
$prevTit = $ax['sty_preview_theme_title'];

if (isset($_POST['prev']) and !$errors) { //create preview theme file and show in calendar
	if (empty($_SESSION[$calID]['theme'])) {
		putTheme($fSaS,'lctheme_prev.php');
		$_SESSION[$calID]['theme'] = 'lctheme_prev.php'; //use lctheme_prev file
		$msg = $ax['sty_theme_previewed'];
		$prevBut = $ax['sty_stop_preview'];
		$prevTit = $ax['sty_stop_preview_title'];
	} else {
		unset($_SESSION[$calID]['theme']); //back to db version
	}
	echo "\n<script>done('r');</script>\n"; //refresh calendar
}

if (isset($_POST['save']) and !$errors) { //save/store posted theme
	if (!$buDone) { //first Save since page opened: backup
		$tempTheme = loadTheme(); //load theme from database
		putTheme($tempTheme,'theme'.date('Ymd-His').'.abak'); //save theme to bak file
		$buDone = true; //backup made
	}
	storeTheme($fSaS); //store in db
	$_SESSION[$calID]['theme'] = ''; //set $_SESSION[$calID]['theme'] to force a refresh of styles (see header.php)
	echo "\n<script>done('r');</script>\n"; //refresh calendar
	$msg = $ax['sty_theme_saved'];
}

if (isset($_POST['bkup']) and !$errors) { //backup current theme file
	$tempTheme = loadTheme(); //load theme from database
	$fName = 'theme'.date('Ymd-His').'.mbak';
	putTheme($tempTheme,$fName); //save theme to bak file
	$buDone = true; //backup made
	$msg = $ax['sty_theme_backedup'].' '.$fName;
}

if (!empty($_POST['rest']) and !$errors) { //restore theme from file
	if (strtolower(substr($_POST['rest'],0,6)) == 'luxcal') { //restore LuxCal defaults
		$fSaS = [];
		checkTheme($fSaS); //fill with $defSaS
	} else { //restore from theme file
		$fName = "./css/{$_POST['rest']}";
		$fSaS = getTheme($fName);
	}
	$msg = $ax['sty_theme_restored1'].' '.$_POST['rest'].'. '.$ax['sty_theme_restored2'];
}

if (!empty($_POST['close'])) { //close window
	$tempSaS = loadTheme(); //load theme from database
	$diff = array_diff_assoc($tempSaS,$fSaS); //compare db and sceen values
	if (!$diff) {
		echo "\n<script>window.close();</script>\n"; //close
	} else {
		echo "\n<script>yes = confirm('{$ax['sty_unsaved_changes']}'); if (yes == true) { window.close(); }</script>\n"; //warn
	}
}

if ($errors) { $msg = "{$ax['sty_number_of_errors']}: {$errors} ({$ax['sty_bgnd_highlighted']})"; }
$eClass = $errors ? 'error' : 'warning';

echo "<p class=\"{$eClass} noPrint\">".($msg ?: $ax['sty_css_intro'])."</p>\n";
//display form fields
echo "<form action='index.php' method='post'>
{$formCal}
<input type='hidden' name='xP' value='99'>
<input type='hidden' name='buD' value='{$buDone}'>\n";
//display buttons
echo "<div class='butHead floatC noPrint'>
	<button title='{$prevTit}' type='submit' name='prev' value='y'>{$prevBut}</button>&ensp;";
if (empty($_SESSION[$calID]['theme'])) { //no preview mode
	echo "<button title='{$ax['sty_save_theme_title']}' type='submit' name='save' value='y'>{$ax['sty_save_theme']}</button>&ensp;\n";
	echo "<button title='{$ax['sty_backup_theme_title']}' type='submit' name='bkup' value='y'>{$ax['sty_backup_theme']}</button>&ensp;\n";
	echo "<select title='{$ax['sty_restore_theme_title']}' name='rest' onchange='this.form.submit()'>\n";
	echo "<option hidden value=''>{$ax['sty_restore_theme']}&nbsp;</option>\n";
	echo "<option value='LuxCal defaults'>{$ax['sty_default_luxcal']}</option>\n";
	$fNames = preg_grep("~^theme~",scandir("./css"));
	foreach($fNames as $fName) {
		echo "<option value='{$fName}'>{$fName}</option>\n";
	}
	echo "</select>&ensp;\n";
	echo "<button title='{$ax['sty_close_window_title']}' type='submit' name='close' value='y'>{$ax['sty_close_window']}</button>\n";
}
echo "<br><br><div>{$ax['sty_theme_title']}: <input type='text' id='THEME' name='THEME' size='40' value='{$fSaS['THEME']}' maxlength='60'></div>";
echo "</div>
	<div class='centerBox sBoxSt'>";

echo "<fieldset><legend>{$ax['sty_general']}</legend>
	<div class='stylesL'>
	<table>
	<colgroup><col style='width:190px'><col style='width:75px'><col style='width:75px'><col style='width:135px'></colgroup>
	<tr>
	<td><b>{$ax['sty_bgtx_colors']}</b></td><td><b>{$ax['sty_background']}</b></td><td><b>{$ax['sty_text']}</b></td><td><b>{$ax['sty_example']}</b></td>
	</tr><tr>
	<td>{$ax['sty_XXXX']}:</td><td><input type='text' id='BXXXX' name='BXXXX' class=\"jscolor {onFineChange:`update(this,'gXXXX','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BXXXX']}' maxlength='7'></td><td><input type='text' id='CXXXX' name='CXXXX' class=\"jscolor {onFineChange:`update(this,'','gXXXX')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CXXXX']}' maxlength='7'></td><td><input type='text' id='gXXXX' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BXXXX']}; color:{$fSaS['CXXXX']}'></td>
	</tr><tr>
	<td>{$ax['sty_TBAR']}:</td><td><input type='text' id='BTBAR' name='BTBAR' class=\"jscolor {onFineChange:`update(this,'gTBAR','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BTBAR']}' maxlength='7'></td><td><input type='text' id='CTBAR' name='CTBAR' class=\"jscolor {onFineChange:`update(this,'','gTBAR')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CTBAR']}' maxlength='7'></td><td><input type='text' id='gTBAR' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BTBAR']}; color:{$fSaS['CTBAR']}'></td>
	</tr><tr>
	<td>{$ax['sty_BHAR']}:</td><td><input type='text' id='BBHAR' name='BBHAR' class=\"jscolor {onFineChange:`update(this,'gBHAR','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BBHAR']}' maxlength='7'></td><td><input type='text' id='CBHAR' name='CBHAR' class=\"jscolor {onFineChange:`update(this,'','gBHAR')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CBHAR']}' maxlength='7'></td><td><input type='text' id='gBHAR' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BBHAR']}; color:{$fSaS['CBHAR']}'></td>
	</tr><tr>
	<td>{$ax['sty_BUTS']}:</td><td><input type='text' id='BBUTS' name='BBUTS' class=\"jscolor {onFineChange:`update(this,'gBUTS','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BBUTS']}' maxlength='7'></td><td><input type='text' id='CBUTS' name='CBUTS' class=\"jscolor {onFineChange:`update(this,'','gBUTS')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CBUTS']}' maxlength='7'></td><td><input type='text' id='gBUTS' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BBUTS']}; color:{$fSaS['CBUTS']}'></td>
	</tr><tr>
	<td>{$ax['sty_DROP']}:</td><td><input type='text' id='BDROP' name='BDROP' class=\"jscolor {onFineChange:`update(this,'gDROP','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BDROP']}' maxlength='7'></td><td><input type='text' id='CDROP' name='CDROP' class=\"jscolor {onFineChange:`update(this,'','gDROP')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CDROP']}' maxlength='7'></td><td><input type='text' id='gDROP' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BDROP']}; color:{$fSaS['CDROP']}'></td>
	</tr><tr>
	<td>{$ax['sty_XWIN']}:</td><td><input type='text' id='BXWIN' name='BXWIN' class=\"jscolor {onFineChange:`update(this,'gXWIN','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BXWIN']}' maxlength='7'></td><td><input type='text' id='CXWIN' name='CXWIN' class=\"jscolor {onFineChange:`update(this,'','gXWIN')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CXWIN']}' maxlength='7'></td><td><input type='text' id='gXWIN' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BXWIN']}; color:{$fSaS['CXWIN']}'></td>
	</tr><tr>
	<td>{$ax['sty_INBX']}:</td><td><input type='text' id='BINBX' name='BINBX' class=\"jscolor {onFineChange:`update(this,'gINBX','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BINBX']}' maxlength='7'></td><td><input type='text' id='CINBX' name='CINBX' class=\"jscolor {onFineChange:`update(this,'','gINBX')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CINBX']}' maxlength='7'></td><td><input type='text' id='gINBX' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BINBX']}; color:{$fSaS['CINBX']}'></td>
	</tr><tr>
	<td>{$ax['sty_OVBX']}:</td><td><input type='text' id='BOVBX' name='BOVBX' class=\"jscolor {onFineChange:`update(this,'gOVBX','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BOVBX']}' maxlength='7'></td><td><input type='text' id='COVBX' name='COVBX' class=\"jscolor {onFineChange:`update(this,'','gOVBX')`,styleElement:null} hexColor\" size='8' value='{$fSaS['COVBX']}' maxlength='7'></td><td><input type='text' id='gOVBX' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BOVBX']}; color:{$fSaS['COVBX']}'></td>
	</tr><tr>
	<td>{$ax['sty_FFLD']}:</td><td><input type='text' id='BFFLD' name='BFFLD' class=\"jscolor {onFineChange:`update(this,'gFFLD','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BFFLD']}' maxlength='7'></td><td><input type='text' id='CFFLD' name='CFFLD' class=\"jscolor {onFineChange:`update(this,'','gFFLD')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CFFLD']}' maxlength='7'></td><td><input type='text' id='gFFLD' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BFFLD']}; color:{$fSaS['CFFLD']}'></td>
	</tr><tr>
	<td>{$ax['sty_CONF']}:</td><td><input type='text' id='BCONF' name='BCONF' class=\"jscolor {onFineChange:`update(this,'gCONF','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BCONF']}' maxlength='7'></td><td><input type='text' id='CCONF' name='CCONF' class=\"jscolor {onFineChange:`update(this,'','gCONF')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CCONF']}' maxlength='7'></td><td><input type='text' id='gCONF' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BCONF']}; color:{$fSaS['CCONF']}'></td>
	</tr><tr>
	<td>{$ax['sty_WARN']}:</td><td><input type='text' id='BWARN' name='BWARN' class=\"jscolor {onFineChange:`update(this,'gWARN','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BWARN']}' maxlength='7'></td><td><input type='text' id='CWARN' name='CWARN' class=\"jscolor {onFineChange:`update(this,'','gWARN')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CWARN']}' maxlength='7'></td><td><input type='text' id='gWARN' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BWARN']}; color:{$fSaS['CWARN']}'></td>
	</tr>
	<tr>
	<td>{$ax['sty_ERRO']}:</td><td><input type='text' id='BERRO' name='BERRO' class=\"jscolor {onFineChange:`update(this,'gERRO','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BERRO']}' maxlength='7'></td><td><input type='text' id='CERRO' name='CERRO' class=\"jscolor {onFineChange:`update(this,'','gERRO')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CERRO']}' maxlength='7'></td><td><input type='text' id='gERRO' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BERRO']}; color:{$fSaS['CERRO']}'></td>
	</tr><tr>
	<td>{$ax['sty_HLIT']}:</td><td><input type='text' id='BHLIT' name='BHLIT' class=\"jscolor {onFineChange:`update(this,'gHLIT','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BHLIT']}' maxlength='7'></td><td><input type='text' id='CHLIT' name='CHLIT' class=\"jscolor {onFineChange:`update(this,'','gHLIT')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CHLIT']}' maxlength='7'></td><td><input type='text' id='gHLIT' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BHLIT']}; color:{$fSaS['CHLIT']}'></td>
	</tr>
	<tr><td>&nbsp;</td><td></td><td></td><td></td></tr>
	<tr>
	<td><b>{$ax['sty_bord_colors']}</b></td><td></td><td><b>{$ax['sty_color']}</b></td><td><b>{$ax['sty_example']}</b></td>
	</tr><tr>
	<td>{$ax['sty_XXXX']}:</td><td></td><td><input type='text' id='EXXXX' name='EXXXX' class=\"jscolor {onFineChange:`update(this,'eXXXX','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['EXXXX']}' maxlength='7'></td><td><input type='text' id='eXXXX' value='' style='background-color:{$fSaS['EXXXX']};'></td>
	</tr><tr>
	<td>{$ax['sty_OVBX']}:</td><td></td><td><input type='text' id='EOVBX' name='EOVBX' class=\"jscolor {onFineChange:`update(this,'eOVBX','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['EOVBX']}' maxlength='7'></td><td><input type='text' id='eOVBX' value='' style='background-color:{$fSaS['EOVBX']};'></td>
	</tr><tr>
	<td>{$ax['sty_BUTH']}:</td><td></td><td><input type='text' id='EBUTS' name='EBUTS' class=\"jscolor {onFineChange:`update(this,'eBUTS','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['EBUTS']}' maxlength='7'></td><td><input type='text' id='eBUTS' value='' style='background-color:{$fSaS['EBUTS']};'></td>
	</tr>
	</table>
	</div>
	<div class='stylesR'>
	<table>
	<colgroup><col style='width:190px'><col style='width:75px'></colgroup>
	<tr>
	<td colspan='2'><b>{$ax['sty_fontfam_sizes']}</b> (10-19px / 0.5-1.9em)</td>
	</tr><tr>
	<td colspan='2'>{$ax['sty_FXXX']}:<span class='floatR'><input{$e['FFXXX']} type='text' id='FFXXX' name='FFXXX' size='15' value='{$fSaS['FFXXX']}' maxlength='30'></span></td>
	</tr><tr>
	<td>{$ax['sty_SXXX']}:</td><td><input{$e['PSXXX']} type='text' id='PSXXX' name='PSXXX' size='2' value='{$fSaS['PSXXX']}' maxlength='2'> px</td>
	</tr><tr>
	<td>{$ax['sty_TBAR']}:</td><td><input{$e['PTBAR']} type='text' id='PTBAR' name='PTBAR' size='2' value='{$fSaS['PTBAR']}' maxlength='2'> px</td>
	</tr><tr>
	<td>{$ax['sty_PGTL']}:</td><td><input{$e['PPGTL']} type='text' id='PPGTL' name='PPGTL' size='2' value='{$fSaS['PPGTL']}' maxlength='2'> px</td>
	</tr><tr>
	<td>{$ax['sty_THDL']}:</td><td><input{$e['PTHDL']} type='text' id='PTHDL' name='PTHDL' size='2' value='{$fSaS['PTHDL']}' maxlength='2'> px</td>
	</tr><tr>
	<td>{$ax['sty_THDM']}:</td><td><input{$e['MTHDM']} type='text' id='MTHDM' name='MTHDM' size='2' value='{$fSaS['MTHDM']}' maxlength='3'> em</td>
	</tr><tr>
	<td>{$ax['sty_DTHD']}:</td><td><input{$e['MDTHD']} type='text' id='MDTHD' name='MDTHD' size='2' value='{$fSaS['MDTHD']}' maxlength='3'> em</td>
	</tr><tr>
	<td>{$ax['sty_SNHD']}:</td><td><input{$e['MSNHD']} type='text' id='MSNHD' name='MSNHD' size='2' value='{$fSaS['MSNHD']}' maxlength='3'> em</td>
	</tr><tr>
	<td>{$ax['sty_OVBX']}:</td><td><input{$e['MOVBX']} type='text' id='MOVBX' name='MOVBX' size='2' value='{$fSaS['MOVBX']}' maxlength='3'> em</td>
	</tr><tr>
	<td>{$ax['sty_FFLD']}:</td><td><input{$e['MFFLD']} type='text' id='MFFLD' name='MFFLD' size='2' value='{$fSaS['MFFLD']}' maxlength='3'> em</td>
	</tr><tr>
	<td>{$ax['sty_BUTS']}:</td><td><input{$e['MBUTS']} type='text' id='MBUTS' name='MBUTS' size='2' value='{$fSaS['MBUTS']}' maxlength='3'> em</td>
	</tr><tr>
	<td>{$ax['sty_PWIN']}:</td><td><input{$e['MPWIN']} type='text' id='MPWIN' name='MPWIN' size='2' value='{$fSaS['MPWIN']}' maxlength='3'> em</td>
	</tr><tr>
	<td>{$ax['sty_SMAL']}:</td><td><input{$e['MSMAL']} type='text' id='MSMAL' name='MSMAL' size='2' value='{$fSaS['MSMAL']}' maxlength='3'> em</td>
	</tr>
	<tr><td>&nbsp;</td><td></td></tr>
	<tr>
	<td><b>{$ax['sty_miscel']}</b></td><td></td>
	</tr><tr>
	<td>{$ax['sty_TbSw']}:</td><td><input{$e['sTbSw']} type='text' id='sTbSw' name='sTbSw' size='2' value='{$fSaS['sTbSw']}' maxlength='1'></td>
	</tr><tr>
	<td>{$ax['sty_CtOf']} (0-99):</td><td><input{$e['sCtOf']} type='text' id='sCtOf' name='sCtOf' size='2' value='{$fSaS['sCtOf']}' maxlength='2'> px</td>
	</tr>
	</table>
	</div>
</fieldset>\n";
echo "<fieldset><legend>{$ax['sty_grid_views']}</legend>
	<div class='stylesL'>
	<table>
	<colgroup><col style='width:190px'><col style='width:75px'><col style='width:75px'><col style='width:135px'></colgroup>
	<tr>
	<td><b>{$ax['sty_bgtx_colors']}</b></td><td><b>{$ax['sty_background']}</b></td><td><b>{$ax['sty_text']}</b></td><td><b>{$ax['sty_example']}</b></td>
	</tr><tr>
	<td>{$ax['sty_GCTH']}:</td><td><input type='text' id='BGCTH' name='BGCTH' class=\"jscolor {onFineChange:`update(this,'vGCTH','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BGCTH']}' maxlength='7'></td><td></td><td><input type='text' id='vGCTH' value='' style='background-color:{$fSaS['BGCTH']};' ></td>
	</tr><tr>
	<td>{$ax['sty_GTFD']}:</td><td><input type='text' id='BGTFD' name='BGTFD' class=\"jscolor {onFineChange:`update(this,'vGTFD','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BGTFD']}' maxlength='7'></td><td><input type='text' id='CGTFD' name='CGTFD' class=\"jscolor {onFineChange:`update(this,'','vGTFD')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CGTFD']}' maxlength='7'></td><td><input type='text' id='vGTFD' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BGTFD']}; color:{$fSaS['CGTFD']}'></td>
	</tr><tr>
	<td>{$ax['sty_GWTC']}:</td><td><input type='text' id='BGWTC' name='BGWTC' class=\"jscolor {onFineChange:`update(this,'vGWTC','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BGWTC']}' maxlength='7'></td><td><input type='text' id='CGWTC' name='CGWTC' class=\"jscolor {onFineChange:`update(this,'','vGWTC')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CGWTC']}' maxlength='7'></td><td><input type='text' id='vGWTC' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BGWTC']}; color:{$fSaS['CGWTC']}'></td>
	</tr><tr>
	<td>{$ax['sty_GWD1']}:</td><td><input type='text' id='BGWD1' name='BGWD1' class=\"jscolor {onFineChange:`update(this,'vGWD1','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BGWD1']}' maxlength='7'></td><td><input type='text' id='CGWD1' name='CGWD1' class=\"jscolor {onFineChange:`update(this,'','vGWD1')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CGWD1']}' maxlength='7'></td><td><input type='text' id='vGWD1' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BGWD1']}; color:{$fSaS['CGWD1']}'></td>
	</tr><tr>
	<td>{$ax['sty_GWD2']}:</td><td><input type='text' id='BGWD2' name='BGWD2' class=\"jscolor {onFineChange:`update(this,'vGWD2','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BGWD2']}' maxlength='7'></td><td><input type='text' id='CGWD2' name='CGWD2' class=\"jscolor {onFineChange:`update(this,'','vGWD2')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CGWD2']}' maxlength='7'></td><td><input type='text' id='vGWD2' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BGWD2']}; color:{$fSaS['CGWD2']}'></td>
	</tr><tr>
	<td>{$ax['sty_GWE1']}:</td><td><input type='text' id='BGWE1' name='BGWE1' class=\"jscolor {onFineChange:`update(this,'vGWE1','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BGWE1']}' maxlength='7'></td><td><input type='text' id='CGWE1' name='CGWE1' class=\"jscolor {onFineChange:`update(this,'','vGWE1')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CGWE1']}' maxlength='7'></td><td><input type='text' id='vGWE1' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BGWE1']}; color:{$fSaS['CGWE1']}'></td>
	</tr><tr>
	<td>{$ax['sty_GWE2']}:</td><td><input type='text' id='BGWE2' name='BGWE2' class=\"jscolor {onFineChange:`update(this,'vGWE2','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BGWE2']}' maxlength='7'></td><td><input type='text' id='CGWE2' name='CGWE2' class=\"jscolor {onFineChange:`update(this,'','vGWE2')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CGWE2']}' maxlength='7'></td><td><input type='text' id='vGWE2' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BGWE2']}; color:{$fSaS['CGWE2']}'></td>
	</tr><tr>
	<td>{$ax['sty_GOUT']}:</td><td><input type='text' id='BGOUT' name='BGOUT' class=\"jscolor {onFineChange:`update(this,'vGOUT','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BGOUT']}' maxlength='7'></td><td><input type='text' id='CGOUT' name='CGOUT' class=\"jscolor {onFineChange:`update(this,'','vGOUT')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CGOUT']}' maxlength='7'></td><td><input type='text' id='vGOUT' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BGOUT']}; color:{$fSaS['CGOUT']}'></td>
	</tr><tr>
	<td>{$ax['sty_GTOD']}:</td><td><input type='text' id='BGTOD' name='BGTOD' class=\"jscolor {onFineChange:`update(this,'vGTOD','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BGTOD']}' maxlength='7'></td><td><input type='text' id='CGTOD' name='CGTOD' class=\"jscolor {onFineChange:`update(this,'','vGTOD')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CGTOD']}' maxlength='7'></td><td><input type='text' id='vGTOD' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BGTOD']}; color:{$fSaS['CGTOD']}'></td>
	</tr><tr>
	<td>{$ax['sty_GSEL']}:</td><td><input type='text' id='BGSEL' name='BGSEL' class=\"jscolor {onFineChange:`update(this,'vGSEL','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BGSEL']}' maxlength='7'></td><td><input type='text' id='CGSEL' name='CGSEL' class=\"jscolor {onFineChange:`update(this,'','vGSEL')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CGSEL']}' maxlength='7'></td><td><input type='text' id='vGSEL' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BGSEL']}; color:{$fSaS['CGSEL']}'></td>
	</tr><tr>
	<td>{$ax['sty_LINK']}:</td><td><input type='text' id='BLINK' name='BLINK' class=\"jscolor {onFineChange:`update(this,'vLINK','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BLINK']}' maxlength='7'></td><td><input type='text' id='CLINK' name='CLINK' class=\"jscolor {onFineChange:`update(this,'','vLINK')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CLINK']}' maxlength='7'></td><td><input type='text' id='vLINK' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BLINK']}; color:{$fSaS['CLINK']}'></td>
	</tr><tr>
	<td>{$ax['sty_CHBX']}:</td><td><input type='text' id='BCHBX' name='BCHBX' class=\"jscolor {onFineChange:`update(this,'vCHBX','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BCHBX']}' maxlength='7'></td><td><input type='text' id='CCHBX' name='CCHBX' class=\"jscolor {onFineChange:`update(this,'','vCHBX')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CCHBX']}' maxlength='7'></td><td><input type='text' id='vCHBX' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BCHBX']}; color:{$fSaS['CCHBX']}'></td>
	</tr>
	<tr><td>&nbsp;</td><td></td><td></td><td></td></tr>
	<tr>
	<td><b>{$ax['sty_bord_colors']}</b></td><td></td><td><b>{$ax['sty_color']}</b></td><td><b>{$ax['sty_example']}</b></td>
	</tr><tr>
	<td>{$ax['sty_GTOD']}:</td><td></td><td><input type='text' id='EGTOD' name='EGTOD' class=\"jscolor {onFineChange:`update(this,'eGTOD','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['EGTOD']}' maxlength='7'></td><td><input type='text' id='eGTOD' value='' style='background-color:{$fSaS['EGTOD']};'></td>
	</tr><tr>
	<td>{$ax['sty_GSEL']}:</td><td></td><td><input type='text' id='EGSEL' name='EGSEL' class=\"jscolor {onFineChange:`update(this,'eGSEL','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['EGSEL']}' maxlength='7'></td><td><input type='text' id='eGSEL' value='' style='background-color:{$fSaS['EGSEL']};'></td>
	</tr>
	</table>
	</div>
	<div class='stylesR'>
	<table>
	<colgroup><col style='width:190px'><col style='width:75px'></colgroup>
	<tr>
	<td colspan='2'><b>{$ax['sty_font_sizes']}</b> (0.5-1.9em)</td>
	</tr><tr>
	<td>{$ax['sty_EVTI']}:</td><td><input{$e['MEVTI']} type='text' id='MEVTI' name='MEVTI' size='2' value='{$fSaS['MEVTI']}' maxlength='3'> em</td>
	</tr>
	</table>
	</div>
</fieldset>\n";
echo "<fieldset><legend>{$ax['sty_hover_boxes']}</legend>
	<div class='stylesL'>
	<table>
	<colgroup><col style='width:190px'><col style='width:75px'><col style='width:75px'><col style='width:135px'></colgroup>
	<tr>
	<td><b>{$ax['sty_bgtx_colors']}</b></td><td><b>{$ax['sty_background']}</b></td><td><b>{$ax['sty_text']}</b></td><td><b>{$ax['sty_example']}</b></td>
	</tr><tr>
	<td>{$ax['sty_HNOR']}:</td><td><input type='text' id='BHNOR' name='BHNOR' class=\"jscolor {onFineChange:`update(this,'hHNOR','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BHNOR']}' maxlength='7'></td><td><input type='text' id='CHNOR' name='CHNOR' class=\"jscolor {onFineChange:`update(this,'','hHNOR')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CHNOR']}' maxlength='7'></td><td><input type='text' id='hHNOR' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BHNOR']}; color:{$fSaS['CHNOR']}'></td>
	</tr><tr>
	<td>{$ax['sty_HPRI']}:</td><td><input type='text' id='BHPRI' name='BHPRI' class=\"jscolor {onFineChange:`update(this,'hHPRI','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BHPRI']}' maxlength='7'></td><td><input type='text' id='CHPRI' name='CHPRI' class=\"jscolor {onFineChange:`update(this,'','hHPRI')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CHPRI']}' maxlength='7'></td><td><input type='text' id='hHPRI' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BHPRI']}; color:{$fSaS['CHPRI']}'></td>
	</tr><tr>
	<td>{$ax['sty_HREP']}:</td><td><input type='text' id='BHREP' name='BHREP' class=\"jscolor {onFineChange:`update(this,'hHREP','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['BHREP']}' maxlength='7'></td><td><input type='text' id='CHREP' name='CHREP' class=\"jscolor {onFineChange:`update(this,'','hHREP')`,styleElement:null} hexColor\" size='8' value='{$fSaS['CHREP']}' maxlength='7'></td><td><input type='text' id='hHREP' value='Lorem ipsum dolor sit amet' style='background-color:{$fSaS['BHREP']}; color:{$fSaS['CHREP']}'></td>
	</tr>
	<tr><td colspan='4'>&nbsp;</td></tr>
	<tr>
	<td><b>{$ax['sty_bord_colors']}</b></td><td></td><td><b>{$ax['sty_color']}</b></td><td><b>{$ax['sty_example']}</b></td>
	</tr><tr>
	<td>{$ax['sty_HNOR']}:</td><td></td><td><input type='text' id='EHNOR' name='EHNOR' class=\"jscolor {onFineChange:`update(this,'eHNOR','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['EHNOR']}' maxlength='7'></td><td><input type='text' id='eHNOR' value='' style='background-color:{$fSaS['EHNOR']};'></td>
	</tr><tr>
	<td>{$ax['sty_HPRI']}:</td><td></td><td><input type='text' id='EHPRI' name='EHPRI' class=\"jscolor {onFineChange:`update(this,'eHPRI','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['EHPRI']}' maxlength='7'></td><td><input type='text' id='eHPRI' value='' style='background-color:{$fSaS['EHPRI']};'></td>
	</tr><tr>
	<td>{$ax['sty_HREP']}:</td><td></td><td><input type='text' id='EHREP' name='EHREP' class=\"jscolor {onFineChange:`update(this,'eHREP','')`,styleElement:null} hexColor\" size='8' value='{$fSaS['EHREP']}' maxlength='7'></td><td><input type='text' id='eHREP' value='' style='background-color:{$fSaS['EHREP']};'></td>
	</tr>
	</table>
	</div>
	<div class='stylesR'>
	<table>
	<colgroup><col style='width:190px'><col style='width:75px'></colgroup>
	<tr>
	<td colspan='2'><b>{$ax['sty_font_sizes']}</b> (0.5-1.9em)</td>
	</tr><tr>
	<td>{$ax['sty_POPU']}:</td><td><input{$e['MPOPU']} type='text' id='MPOPU' name='MPOPU' size='2' value='{$fSaS['MPOPU']}' maxlength='3'> em</td>
	</tr>
	</table>
	</div>
</fieldset>\n";
?>
</div>
</form>
<br>
