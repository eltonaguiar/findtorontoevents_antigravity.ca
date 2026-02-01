<?php
/*
= LuxCal categories management page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV) or
		(isset($_REQUEST['cid']) and !preg_match('%^\d{1,4}$%',$_REQUEST['cid'])) or
		(!empty($state) and !preg_match('%^(add|edit|sort)$%',$state))
	) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); }

//initialize
$adminLang = (file_exists("./lang/ai-{$opt['cL']}.php")) ? $opt['cL'] : "english";
require "./lang/ai-{$adminLang}.php";
if (!isset($state)) { $state = ''; }

$cat = [];
$cat['id'] = $_REQUEST['cid'] ?? 0;
$cat['name'] = trim($_POST['cname'] ?? '');
$cat['color'] = $_POST['color'] ?? '#303030';
$cat['bgrnd'] = (isset($_POST['bgrnd']) and $_POST['bgrnd'] != '#FFFFFF') ? $_POST['bgrnd'] : ''; //white: transparent
$cat['symbl'] = trim($_POST['symbl'] ?? '');
$cat['sqnce'] = $_POST['sqnce'] ?? 1;
$cat['rpeat'] = $_POST['repeat'] ?? 0;
$cat['nolap'] = $_POST['nolap'] ?? 0;
$cat['olGap'] = $_POST['olGap'] ?? 0;
$cat['olErr'] = $_POST['olErr'] ?? $ax['cat_ol_error_msg'];
$cat['tsHrs'] = $_POST['tsHrs'] ?? 0;
$cat['tsMin'] = $_POST['tsMin'] ?? 0;
$cat['tsFix'] = $_POST['tsFix'] ?? 0;
$cat['daybg'] = isset($_POST['daybg1']) ? 1 : 0;
$cat['daybg'] = isset($_POST['daybg2']) ? $cat['daybg'] + 2 : $cat['daybg'];
$cat['appro'] = isset($_POST['approve']) ? 1 : 0;
$cat['chBox'] = isset($_POST['chBox']) ? 1 : 0;
$cat['chLab'] = trim($_POST['chLab'] ?? '');
$cat['chMrk'] = trim($_POST['chMrk'] ?? '&#x2713;');
$cat['sCats'] = [];
if (!empty($_POST['subN'])) {
	foreach ($_POST['subN'] as $i => $name) {
		$cat['sCats'][$i] = [$name,(isset($_POST['subC'][$i]) ? trim($_POST['subC'][$i]) : '#303030'),(isset($_POST['subB'][$i]) ? trim($_POST['subB'][$i]) : '#FFFFFF')];
	}
}
$cat['cyCat'] = $_POST['cyCat'] ?? '';
$cat['scNbr'] = $_POST['scNbr'] ?? 0;
$cat['ntLst'] = trim($_POST['ntLst'] ?? '');
$cat['urlNm'] = trim($_POST['urlNm'] ?? '');
$cat['urlLk'] = trim($_POST['urlLk'] ?? '');

//get number of cats
$stH = dbQuery("SELECT COUNT(*) FROM `categories` WHERE `status` >= 0");
$row = $stH->fetch(PDO::FETCH_NUM);
$stH = null;
$nrCats = $row[0];

function showCategories($bare) { //bare: no edit/add buttons
	global $ax;
	
	echo "<fieldset><legend>{$ax['cat_list']}</legend>\n";
	$stH = stPrep("SELECT * FROM `categories` WHERE `status` >= 0 ORDER BY `sequence`");
	stExec($stH,null);
	$rows = $stH->fetchAll(PDO::FETCH_ASSOC);
	echo "<table class='list catList'>
<tr><th>&nbsp;{$ax['cat_nr']}&nbsp;</th><th>&nbsp;{$ax['id']}&nbsp;</th><th>{$ax['cat_cat_name']}</th><th>{$ax['cat_symbol']}</th><th>{$ax['cat_repeat']}</th><th>{$ax['cat_overlap']}</th><th>{$ax['cat_duration']}</th><th>{$ax['cat_need_approval']}</th><th>{$ax['cat_day_color']}</th><th>{$ax['cat_check_mark']}</th><th>{$ax['cat_not_list']}</th><th>{$ax['cat_subcats']}</th>";
	if (!$bare) {
		echo "<td colspan='2'></td>";
	}
	echo "</tr>\n";
	foreach ($rows as $cat) {
		switch ($cat['repeat']) {
			case 0: $repeat = ''; break;
			case 1: $repeat = $ax['cat_every_day']; break;
			case 2: $repeat = $ax['cat_every_week']; break;
			case 3: $repeat = $ax['cat_every_month']; break;
			case 4: $repeat = $ax['cat_every_year'];
		}
		$style = ($cat['color'] ? "color:{$cat['color']};" : '').($cat['bgColor'] ? "background-color:{$cat['bgColor']};" : '');
		$style = $style ? " style='{$style}'" : '';
		echo "<tr>\n<td>{$cat['sequence']}</td><td>{$cat['ID']}</td><td{$style}>{$cat['name']}</td><td>{$cat['symbol']}</td><td>{$repeat}</td>
<td>".($cat['noverlap'] < 1 ? $ax['yes'] : $ax['no'].' ('.$cat['olapGap'].')')."</td>
<td>".($cat['defSlot'] > 0 ? substr('0'.intval($cat['defSlot'] / 60),-2).':'.substr('0'.($cat['defSlot'] % 60),-2).($cat['fixSlot'] > 0 ? ' !' : '') : '-')."</td>
<td>".($cat['approve'] < 1 ? $ax['no'] : $ax['yes'])."</td>
<td>".($cat['dayColor'] < 1 ? $ax['no'] : $ax['yes'])."</td>
<td>".($cat['checkBx'] ? $cat['checkMk'].': "'.$cat['checkLb'].'"' : $ax['no'])."</td>
<td>".(!$cat['notList'] ? $ax['no'] : $ax['yes'])."</td>
<td>".($cat['subCats'] != '[]' ? $ax['yes'] : $ax['no']).'</td>';
		if (!$bare) {
			echo "<td><button type='button' onclick='index({state:`edit`,cid:{$cat['ID']}});'>{$ax['cat_edit']}</button></td>";
			echo ($cat['ID'] > 1) ? "<td><button type='button' onclick=\"delConfirm(`cat`,{$cat['ID']},`{$ax['cat_delete']} {$cat['name']}`);\">{$ax['cat_delete']}</button></td>" : '<td></td>';
		}
		echo "</tr>\n";
	}
	echo "</table>\n";
	echo "</fieldset>\n";
	if (!$bare) {
		echo "<button type='button' onclick='index({state:`add`});'>{$ax['cat_add_new']}</button>\n";
		echo "&emsp;<button type='button' onclick='index({state:`sort`});'>{$ax['cat_sort']}</button>\n";
	}
	echo "<br><br>\n";
}

function sortCategories() {
	$stH = dbQuery("SELECT `ID` FROM `categories` WHERE `status` >= 0 ORDER BY CASE WHEN `ID` < 2 THEN `ID` ELSE LOWER(name) END");
	$rowArray = $stH->fetchAll(PDO::FETCH_ASSOC);
	$stH = null;
	$stH = stPrep("UPDATE `categories` SET `sequence` = ? WHERE `ID` = ?");
	$count = 0;
	foreach ($rowArray as $row) {
		stExec($stH,[++$count,$row['ID']]);
	}
}

function editCategory($cat) {
	global $formCal, $ax, $state, $nrCats;
	
	echo "<form action='index.php' method='post'>
{$formCal}
<input type='hidden' name='cid' id='cid' value='{$cat['id']}'>
<input type='hidden' name='state' id='state' value='{$state}'>\n";
	echo "<fieldset>";
	if ($state == 'edit') { //edit
		$stH = stPrep("SELECT * FROM `categories` WHERE `ID` = ? LIMIT 1");
		stExec($stH,[$cat['id']]);
		$row = $stH->fetch(PDO::FETCH_ASSOC);
		$stH = null;
		if ($row and !isset($_POST['cname'])) {
			$cat['name'] = $row['name'];
			$cat['color'] = $row['color'] ?: '#303030';
			$cat['bgrnd'] = $row['bgColor'] ?: '#FFFFFF';
			$cat['symbl'] = $row['symbol'];
			$cat['sqnce'] = $row['sequence'];
			$cat['rpeat'] = $row['repeat'];
			$cat['nolap'] = $row['noverlap'];
			$cat['olGap'] = $row['olapGap'];
			$cat['olErr'] = $row['olErrMsg'];
			$cat['tsHrs'] = intval($row['defSlot'] / 60);
			$cat['tsMin'] = $row['defSlot'] % 60;
			$cat['tsFix'] = $row['fixSlot'];
			$cat['appro'] = $row['approve'];
			$cat['daybg'] = $row['dayColor'];
			$cat['chBox'] = $row['checkBx'];
			$cat['chLab'] = $row['checkLb'];
			$cat['chMrk'] = $row['checkMk'];
			$cat['ntLst'] = $row['notList'];
			$cat['sCats'] = json_decode($row['subCats']); //2-D array
			$cat['scNbr'] = count($cat['sCats']);
			preg_match('~(.+)\s*\[(.*)\]~',$row['urlLink'],$matches);
			$cat['urlLk'] = $matches[1] ?? '';
			$cat['urlNm'] = $matches[2] ?? '';
		}
		echo "<legend>{$ax['cat_edit_cat']}</legend>\n";
	} else { //add
		echo "<legend>{$ax['cat_add_new']}</legend>\n";
		$cat['sqnce'] = $nrCats + 1;
	}
	//get categories
	$stH = stPrep("SELECT `ID`,`name`,`subCats`,`color`,`bgColor` FROM `categories` WHERE NOT `subCats` = '[]' AND NOT `ID` = '{$cat['id']}' AND `status` >= 0 ORDER BY `sequence`");
	stExec($stH,null);
	$cats = $stH->fetchAll(PDO::FETCH_ASSOC);
	array_walk($cats,function(&$v,$k) {$v['subCats'] = json_decode($v['subCats']);}); //json decode sub cats
	$style = ($cat['color'] ? "color:{$cat['color']};" : "").($cat['bgrnd'] ? "background-color:{$cat['bgrnd']};" : "");
	$style = $style ? " style='{$style}'" : '';
	$selected = array_fill(0,5,'');
	$selected[$cat['rpeat']] = ' selected';
	$sCatNote = $cat['scNbr'] ? "<span class='sup'>**</span>" : '';
	$hideNoCat = $cat['id'] == 1 ? " class='hide'" : ''; //category 'no cat'
	echo "<table class='list'>\n";
	if ($state != 'add') { echo "<tr><td>{$ax['id']}:</td><td>&nbsp;{$cat['id']}</td></tr>\n"; }
	echo	"<tr><td>{$ax['cat_cat_name']}:</td><td><input type='text' id='cname' name='cname' value=\"{$cat['name']}\" size='20' maxlength='40'{$style}></td></tr>
<tr><td>{$ax['cat_cat_color']}:</td><td>{$ax['cat_text']}: <input type='text' id='color' name='color' title=\"{$ax['cat_select_color']}\" class=\"jscolor {onFineChange:`update(this,'','cname')`,styleElement:null}\" value='{$cat['color']}' size='7' maxlength='7'>
&ensp;{$ax['cat_background']}: <input type='text' id='bgrnd' name='bgrnd' title=\"{$ax['cat_select_color']}\" class=\"jscolor {onFineChange:`update(this,'cname','')`,styleElement:null}\" value='{$cat['bgrnd']}' size='7' maxlength='7'></td></tr>
<tr><td>{$ax['cat_symbol_repms']}:</td><td><input type='text' id='symbl' name='symbl' value=\"{$cat['symbl']}\" size='1' maxlength='1'> ({$ax['cat_symbol_eg']})</td></tr>
<tr><td>{$ax['cat_seq_in_menu']}:</td><td><input type='text' name='sqnce' value='{$cat['sqnce']}' size='1' maxlength='2'></td></tr>
<tr><td>{$ax['cat_repeat']}:</td>
<td><select name='repeat'>
<option value='0'{$selected[0]}>-</option>
<option value='1'{$selected[1]}>{$ax['cat_every_day']}</option>
<option value='2'{$selected[2]}>{$ax['cat_every_week']}</option>
<option value='3'{$selected[3]}>{$ax['cat_every_month']}</option>
<option value='4'{$selected[4]}>{$ax['cat_every_year']}</option>
</select></td></tr>
<tr{$hideNoCat}><td>{$ax['cat_no_overlap']}:<span class='sup'>*</span></td><td><label>{$ax['cat_same_category']}: <input type='checkbox' name='nolap' value='1' onclick='check1T(`nolap`,this);'".($cat['nolap'] == 1 ? " checked> " : ' > ')."</label>&ensp;<label>{$ax['cat_all_categories']}: <input type='checkbox' name='nolap' value='2' onclick='check1T(`nolap`,this);'".($cat['nolap'] == 2 ? " checked> " : ' > ')."</label>&ensp;{$ax['cat_gap']}: <input type='text' name='olGap' value='{$cat['olGap']}' size='1' maxlength='3'> (0-720 {$ax['minutes']})</td></tr>
<tr{$hideNoCat}><td>{$ax['cat_ol_error_text']}:</td><td><input type='text' name='olErr' value='{$cat['olErr']}' size='50' maxlength='80'></td></tr>
<tr><td>{$ax['cat_event_duration']} (0: {$ax['none']}):</td><td><input type='text' name='tsHrs' value='{$cat['tsHrs']}' size='1' maxlength='2'> {$ax['hours']}&ensp;<input type='text' name='tsMin' value='{$cat['tsMin']}' size='1' maxlength='2'> {$ax['minutes']}&ensp;
<label><input type='radio' name='tsFix' value='0'".(!$cat['tsFix'] ? " checked" : '').">{$ax['cat_default']}</label>&ensp;
<label><input type='radio' name='tsFix' value='1'".($cat['tsFix'] ? " checked" : '').">{$ax['cat_fixed']}</label></td></tr>
<tr><td><label for='dbg1'>{$ax['cat_day_color1']}</label>:</td><td><input type='checkbox' name='daybg1' id='dbg1' value='1'".(($cat['daybg'] & 1) ? " checked> " : ' > ')."</td></tr>
<tr><td><label for='dbg2'>{$ax['cat_day_color2']}</label>:</td><td><input type='checkbox' name='daybg2' id='dbg2' value='1'".(($cat['daybg'] & 2) ? " checked> " : ' > ')."</td></tr>
<tr><td><label for='app'>{$ax['cat_approve']}</label>:</td><td><input type='checkbox' name='approve' id='app' value='1'".($cat['appro'] ? " checked> " : ' > ')."</td></tr>
<tr><td><label for='chb'>{$ax['cat_check_mark']}</label>:</td><td><input type='checkbox' name='chBox' id='chb' value='1'".($cat['chBox'] ? " checked" : '').">
&ensp;{$ax['cat_label']}: <input type='text' name='chLab' value='{$cat['chLab']}' size='8' maxlength='20'>
&ensp;{$ax['cat_mark']}: <input type='text' name='chMrk' value='{$cat['chMrk']}' size='5' maxlength='10'></td></tr>
<tr><td>{$ax['cat_eml_changes_to']}:</td><td><input type='text' placeholder='{$ax['chgRecipList']}' name='ntLst' value='{$cat['ntLst']}' size='50' maxlength='120'></td></tr>
<tr><td>{$ax['cat_matrix_url_link']}:</td><td>{$ax['cat_name']}: <input type='text' name='urlNm' value='{$cat['urlNm']}' size='10' maxlength='30'>
&ensp;{$ax['cat_url']}: <input type='text' name='urlLk' value='{$cat['urlLk']}' size='35' maxlength='120'></td></tr>
<tr><td>{$ax['cat_subcats_opt']}:{$sCatNote}</td><td><select name='scNbr' onChange='this.form.submit();'>\n";
	for ($i = 0; $i <= 12; $i++) {
		$selected = ($i == $cat['scNbr']) ? ' selected' : '';
		echo "<option value='{$i}'{$selected}>{$i}</option>\n";
	}
	echo "</select>\n";
	if ($cats) { //other cats with subcats present- show copy from list
		echo "&ensp;{$ax['cat_copy_from']}: <select name='cyCat' onChange='this.form.submit();'>\n";
		echo "<option value=''>{$ax['none']}</option>\n";
		foreach($cats as $sCat) {
			$style = ($sCat['color'] ? "color:{$sCat['color']};" : '').($sCat['bgColor'] ? "background-color:{$sCat['bgColor']};" : '');
			$style = $style ? " style='{$style}'" : '';
			if ($sCat['ID'] == $cat['cyCat']) {
				$selected = ' selected';
				$cat['sCats'] = $sCat['subCats'];
			} else {
				$selected = '';
			}
			echo "<option{$style} value='{$sCat['ID']}'{$selected}>{$sCat['name']}</option>\n";
		}
		echo "</select>\n";
	}
	echo "</td></tr>\n";
	for ($i = 0; $i < $cat['scNbr']; $i++) { //make subcats
		if (empty($cat['sCats'][$i])) {
			$cat['sCats'][$i] = ['','#303030','#FFFFFF'];
		}
	}
	foreach ($cat['sCats'] as $i => $sCat) {
		if ($i >= $cat['scNbr']) { break; }
		$style = " style = 'color:{$sCat[1]}; background-color:{$sCat[2]};'";
		echo "<tr><td class='floatR'>".($i+1)." - {$ax['cat_name']}: <input type='text' id='subN{$i}' name='subN[]' value='{$sCat[0]}' size='8' maxlength='20'{$style}></td><td>
&nbsp;{$ax['cat_text']}: <input type='text' name='subC[]' title=\"{$ax['cat_select_color']}\" class=\"jscolor {onFineChange:`update(this,'','subN{$i}')`,styleElement:null}\" value='{$sCat[1]}' size='7' maxlength='7'>
&ensp;{$ax['cat_background']}: <input type='text' name='subB[]' title=\"{$ax['cat_select_color']}\" class=\"jscolor {onFineChange:`update(this,'subN{$i}','')`,styleElement:null}\" value='{$sCat[2]}' size='7' maxlength='7'></td></tr>\n";
	}
	echo "</table>\n";
	if ($cat['id'] > 1) {
		echo "<span class='sup'>*</span><span class='fontS'> {$ax['cat_no_ol_note']}</span>\n";
	}
	if ($cat['scNbr']) {
		echo "<br><span class='sup'>**</span><span class='fontS'> {$ax['cat_subcat_note']}</span>\n";
	}
	echo "</fieldset>\n";
	if ($state == 'add') {
		echo "<button type='submit' name='addExe' value='y'>{$ax['cat_add']}</button>";
	} else {
		echo "<button type='submit' name='updExe' value='y'>{$ax['cat_save']}</button>";
	}
	echo "&emsp;<button type='submit' name='back' value='y'>{$ax['back']}</button>
		</form><br><br><br>\n";
}

function validateCat(&$cat) { //validate category
	global $ax, $nrCats, $rxCalURL;

	$msg = ''; //init
	do {
		if (!$cat['name']) { $msg = 'E'.$ax['cat_name_missing']; break; }
		if (!ctype_digit($cat['olGap']) or $cat['olGap'] < 0 or $cat['olGap'] > 720) { $msg = 'E'.$ax['cat_olgap_invalid']; break; }
		if (!ctype_digit($cat['tsHrs']) or $cat['tsHrs'] < 0 or !ctype_digit($cat['tsMin']) or $cat['tsMin'] > 59 or $cat['tsMin'] < 0) { $msg = 'E'.$ax['cat_duration_invalid']; break; }
		if ($cat['chBox'] and (!$cat['chLab'] or !$cat['chMrk'])) { $msg = 'E'.$ax['cat_mark_label_missing']; break; }
		if (!ctype_digit($cat['sqnce']) or $cat['sqnce'] == 0) {
			$cat['sqnce'] = 1;
		} elseif ($cat['sqnce'] > $nrCats) {
			$cat['sqnce'] = $nrCats + 1;
		}
		if ($cat['nolap'] and !$cat['olErr']) { $msg = 'E'.$ax['cat_no_ol_error_msg']; break; }
		$cat['olErr'] = str_replace(';',' -',$cat['olErr']); //semicolons can cause PHP problems
		if (($cat['urlNm'] and !$cat['urlLk']) or ($cat['urlLk'] and !preg_match($rxCalURL, $cat['urlLk']))) { $msg = 'E'.$ax['cat_invalid_url']; break; }
		$cat['urlNm'] = str_replace(['[',']'],'',$cat['urlNm']);
		if ($cat['urlLk'] and empty($cat['urlNm'])) { $msg = 'E'.$ax['cat_no_url_name']; break; }
		$cat['urlLN'] = $cat['urlLk'] ? "{$cat['urlLk']}[{$cat['urlNm']}]" : '';
	} while (false);
	return $msg;
}

function addCat(&$cat) { //add category
	global $ax, $state, $nrCats;
	
	do {
		//validate form fields
		if ($msg = validateCat($cat)) { break; }
		//renumber sequence
		$stH = stPrep("SELECT `ID` FROM `categories` WHERE `status` >= 0 AND `sequence` >= ? ORDER BY `sequence`");
		stExec($stH,[$cat['sqnce']]);
		$rowArray = $stH->fetchAll(PDO::FETCH_ASSOC);
		$stH = null;
		$stH = stPrep("UPDATE `categories` SET `sequence` = ? WHERE `ID` = ?");
		$count = $cat['sqnce'];
		foreach ($rowArray as $row) {
			stExec($stH,[++$count,$row['ID']]);
		}
		$sCats = array_values(array_filter($cat['sCats'], function($sCat) { return $sCat[0]; })); //remove inactive subcats and re-index
		//add new category
		$stH = stPrep("INSERT INTO `categories` (`name`,`symbol`,`sequence`,`repeat`,`noverlap`,`olapGap`,`olErrMsg`,`defSlot`,`fixSlot`,`approve`,`dayColor`,`color`,`bgColor`,`checkBx`,`checkLb`,`checkMk`,`subCats`,`notList`,`urlLink`) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)");
		stExec($stH,[$cat['name'],$cat['symbl'],$cat['sqnce'],$cat['rpeat'],$cat['nolap'],$cat['olGap'],$cat['olErr'],(($cat['tsHrs'] * 60) + $cat['tsMin']),$cat['tsFix'],$cat['appro'],$cat['daybg'],$cat['color'],$cat['bgrnd'],$cat['chBox'],$cat['chLab'],$cat['chMrk'],json_encode($sCats),$cat['ntLst'],$cat['urlLN']]);
		$count = $stH->rowCount();
		if (!$count) { $msg = 'E'."Database Error: {$ax['cat_not_added']}"; break; }
		$msg = 'C'.$ax['cat_added'];
		$state = '';
	} while (false);
	return $msg;
}

function updateCat(&$cat) { //update category
	global $ax, $state, $nrCats;
	
	do {
		//validate form fields
		if ($msg = validateCat($cat)) { break; }
		$sCats = array_values(array_filter($cat['sCats'], function($sCat) { return $sCat[0]; })); //remove inactive subcats and re-index
		//update
		$stH = stPrep("UPDATE `categories` SET `name`=?,`symbol`=?,`sequence`=?,`repeat`=?,`noverlap`=?,`olapGap`=?,`olErrMsg`=?,`defSlot`=?,`fixSlot`=?,`approve`=?,`dayColor`=?,`color`=?,`bgColor`=?,`checkBx`=?,`checkLb`=?,`checkMk`=?,`subCats`=?,`notList`=?,`urlLink`=? WHERE `ID`=?");
		stExec($stH,[$cat['name'],$cat['symbl'],$cat['sqnce'],$cat['rpeat'],$cat['nolap'],$cat['olGap'],$cat['olErr'],(($cat['tsHrs'] * 60) + $cat['tsMin']),$cat['tsFix'],$cat['appro'],$cat['daybg'],$cat['color'],$cat['bgrnd'],$cat['chBox'],$cat['chLab'],$cat['chMrk'],json_encode($sCats),$cat['ntLst'],$cat['urlLN'],$cat['id']]);
		$count = $stH->rowCount();
		if (!$count) { $msg = 'E'."Database Error: {$ax['cat_not_updated']}"; break; }
		//renumber sequence
		$stH = dbQuery("SELECT `ID` FROM `categories` WHERE `status` >= 0 ORDER BY `sequence`");
		$rowArray = $stH->fetchAll(PDO::FETCH_ASSOC);
		$stH = null;
		$stH = stPrep("UPDATE `categories` SET `sequence` = ? WHERE `ID` = ?");
		$count = 1;
		foreach ($rowArray as $row) {
			if ($row['ID'] != $cat['id']) {
				if ($count == $cat['sqnce']) { $count++; }
				stExec($stH,[$count++,$row['ID']]);
			}
		}
		$msg = 'C'.$ax['cat_updated'];
		$state = '';
	} while (false);
	return $msg;
}

function deleteCat($cat) { //delete category
	global $ax;
	
	$stH = stPrep("UPDATE `categories` SET `sequence` = 0, `status` = -1 WHERE `ID` = ?");
	stExec($stH,[$cat['id']]);
	$count = $stH->rowCount();
	if (!$count) {
		$msg = 'E'."Database Error: {$ax['cat_not_deleted']}";
	} else {
		$msg = 'C'.$ax['cat_deleted'];
		//renumber sequence
		$stH = dbQuery("SELECT `ID` FROM `categories` WHERE `status` >= 0 ORDER BY `sequence`");
		$rowArray = $stH->fetchAll(PDO::FETCH_ASSOC);
		$stH = null;
		$stH = stPrep("UPDATE `categories` SET `sequence` = ? WHERE `ID` = ?");
		$count = 1;
		foreach ($rowArray as $row) {
			stExec($stH,[$count++,$row['ID']]);
		}
	}
	return $msg;
}

//Control logic
if ($usr['privs'] >= 4) { //manager or admin
	$msg = '';
	if (isset($_POST['addExe'])) {
		$msg = addCat($cat);
	} elseif (isset($_POST['updExe'])) {
		$msg = updateCat($cat);
	} elseif (isset($_POST['delExe'])) {
		$msg = deleteCat($cat);
	}
	$class = $msg ? ($msg[0] == 'E' ? 'error' : 'confirm') : '';
	$msg = substr($msg,1);
	echo $msg ? "<p class='{$class}'>{$msg}</p>\n" : "<p>&nbsp;</p>\n";
	echo "<div class='centerBox sBoxAd'>\n";
	if ($state == 'sort') {
		sortCategories(); //sort on name
	}
	if (($state != 'add' and $state != 'edit') or isset($_POST['back'])) {
		showCategories(false); //no add / no edit
	} else {
		editCategory($cat); //add or edit
		showCategories(true);
	}
	echo "</div>\n";
} else {
	echo "<p class='error'>{$ax['no_way']}</p>\n";
}
?>