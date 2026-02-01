<?php
/*
= LuxCal information text editor page =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

//initialize
$adminLang = (file_exists("./lang/ai-{$opt['cL']}.php")) ? $opt['cL'] : "english";
require "./lang/ai-{$adminLang}.php";

function editForm($fName) {
	global $formCal, $selFile, $allDisabled, $fnmReadOnly, $ax, $teText;
	
	$fBaseName = substr($fName,0,-4);
	echo "<form action='index.php' method='post'>\n";
	echo "{$formCal}\n";
	echo "<div class='floatC'>
<select name='selFile' onfocus=\"this.dataset.prevIndex = this.selectedIndex;\" onchange=\"teTextSubmit(this,'teText','{$ax['edi_confirm_changes']}');\">
<option value='0' hidden>{$ax['edi_select_file']}</option>';
<option value='info'".($selFile == 'info' ? ' selected' : '').">{$ax['edi_info_text']} (info.txt)</option>
<option value='reci'".($selFile == 'reci' ? ' selected' : '').">{$ax['edi_pub_recips']} (+recipients.txt)</option>\n";
	$listNames = preg_grep("~^[\-\w]+\.(txt)$~i",scandir('./reciplists'));
	foreach ($listNames as $k => $listName) {
		echo "<option value='{$listName}'".($selFile == $listName ? ' selected' : '').">{$ax['edi_recips_list']} ({$listName})</option>\n";
	}
	echo "<option value='newList'".($selFile == 'newList' ? ' selected' : '').">{$ax['edi_new_recips_list']}</option>\n";
	echo "</select></div><br>\n";
	echo "<fieldset>\n
<legend>{$ax['edi_text_editor']}</legend>\n
<p>{$ax['edi_file_name']}: <input type='text' name='fName'  size='20' value='{$fBaseName}'{$allDisabled}{$fnmReadOnly}>.txt</p>
<br><textarea data-changed='0' id='teText' name='teText' onchange=\"this.dataset.changed = '1';\" rows='30' cols='1' style='width:40vw'{$allDisabled}>{$teText}</textarea><br>
</fieldset>\n
&emsp;<button type='submit' name='action' value='save'{$allDisabled}>{$ax['edi_save']}</button>&ensp;\n
<button type='submit' name='action' value='backup'{$allDisabled}>{$ax['edi_backup']}</button>\n
</form>\n";
}

function submit($action,$fName) {
	global $ax, $teText;

	$fPath = $fName == 'info.txt' ? "./sidepanel/{$fName}" : "./reciplists/{$fName}";

	if (!$fName) {
		$msg = 'E'.$ax['edi_no_file_name'];
	} elseif (!$teText) {
		$msg = 'E'.$ax['edi_no_text'];
	}	elseif ($action == 'save') {
		file_put_contents($fPath,$teText);
		$msg = 'C'.str_replace('$1',$fPath,$ax['edi_text_saved']);
	} elseif ($action == 'backup') {
		$fPathBu = str_replace(".txt",'-'.date('Ymd-His').'.bak',$fPath);
		file_put_contents($fPathBu,$teText);
		$msg = 'C'.str_replace('$1',$fPathBu,$ax['edi_text_saved']);
	}
	return $msg;
}


//init
$msg = '';
$selFile = $_POST["selFile"] ?? '0';
$prevSelFile = $_SESSION["selFile"] ?? $selFile;
$teHelp = $_SESSION["teHelp"] ?? $ax['xpl_edit'];
$fName = !empty($_POST["fName"]) ? str_replace('.txt','',$_POST["fName"]).'.txt' : '';
$teText = $_POST["teText"] ?? ''; //text in edit field
$action = $_POST["action"] ?? ''; //save, backup or blank (edit)
$allDisabled = $fnmReadOnly = '';
if (!$selFile) { //1st pass
	$fName = '';
	$teText = '';
	$allDisabled = ' disabled';
} elseif ($selFile != $prevSelFile) { //file selected
	switch ($selFile) {
		case 'info': //info text sidebar
			$teHelp = $ax['xpl_edit_info_texts'];
			$fName = 'info.txt';
			$teText = htmlentities(file_get_contents("./sidepanel/{$fName}"),ENT_QUOTES);
			break;
		case 'reci': //public recips
			$teHelp = $ax['xpl_edit_pub_recips'];
			$fName = '+recipients.txt';
			$teText = htmlentities(file_get_contents("./reciplists/{$fName}"),ENT_QUOTES);
			break;
		case 'newList': //new recips list
			$teHelp = $ax['xpl_edit_recips_list'];
			$fName = '';
			$teText = '';
			break;
		default: //recips lists
			$teHelp = $ax['xpl_edit_recips_list'];
			$fName = $selFile;
			$teText = htmlentities(file_get_contents("./reciplists/{$fName}"),ENT_QUOTES);
	}
}
$fnmReadOnly = ($selFile == 'info' or $selFile == 'reci') ? ' readonly' : '';
$_SESSION["selFile"] = $selFile; //remember selected file
$_SESSION["teHelp"] = $teHelp; //remember help file
//control logic
if ($usr['privs'] >= 4) {
	if ($action) { //submit
		$msg = submit($action,$fName);
	}
	$class = $msg ? ($msg[0] == 'E' ? 'error' : 'confirm') : '';
	$msg = substr($msg,1);
	$hidden = $teHelp ? '' : ' hidden';
	echo "<aside class='aside sBoxTe{$hidden}'>{$teHelp}</aside>\n";
	echo "<div class='centerBox sBoxTe'>\n";
	echo $msg ? "<p class='{$class}'>{$msg}</p>\n" : "<p>&nbsp;</p>\n";
	echo '<br>';
	editForm($fName); //text edit form
	echo "</div>\n";
} else {
	echo "<p class='error'>{$ax['no_way']}</p>\n";
}
?>