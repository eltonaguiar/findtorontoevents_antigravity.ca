<?php
//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

if ($set['emojiPicker']) { //enable emoji picker
	echo "<script>new EmojiPicker({selector:'.emoButton', fields:'.emoYes'});</script>\n";
}

//functions

function venueMenu($selVenue) {
	$venues = file('files/venues.txt', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
	if (!$venues) {
		$venues = ['Venue list empty or not found'];
	}
	foreach ($venues as $venue) {
		$venue = trim($venue);
		if ($venue[0] === '#') { continue; } //skip comment
		$selected = ($selVenue == $venue) ? ' selected' : '';
		echo "<option value='{$venue}'{$selected}>{$venue}</option>\n";
	}
}

function catMenu($selCat) {
	global $usr, $todo;

	$eCats = $usr['eCats'];
	$stH = dbQuery("SELECT `ID`,`name`,`color`,`bgColor`,`checkBx` FROM `categories` WHERE `status` >= 0".($eCats != '0' ? " AND `ID` IN ($eCats)" : '')." ORDER BY sequence");
	echo "\n<select name='cid' id='cid' onChange='this.form.submit();'>\n";
	while (list($ID,$name,$color,$bgColor,$cBox) = $stH->fetch(PDO::FETCH_NUM)) {
		if ($selCat == $ID) {
			$selected = ' selected';
			$todo = $cBox;
		} else {
			$selected = '';
		}
		$catColor = ($color ? "color:{$color};" : '').($bgColor ? "background-color:{$bgColor};" : '');
		echo "<option value='{$ID}'".($catColor ? " style='{$catColor}'" : '')."{$selected}>{$name}</option>\n";
	}
	echo "</select>\n";
}

function scatMenu($sid) {
	global $cat, $xx;
	
	$options = '';
	foreach ($cat['sub'] as $k => $scat) {
		$i = $k + 1;
		if (empty($scat[0])) { continue; } //no name, no subcat
		$selected = $sid == $i ? ' selected' : '';
		$color = ($scat[1] ? "color:{$scat[1]};" : '').($scat[2] ? "background-color:{$scat[2]};" : '');
		$options .= "<option value='{$i}'".($color ? " style='{$color}'" : '')."{$selected}>{$scat[0]}</option>\n";
	}
	echo "\n<select name='sid' id='sid'>\n";
	echo $options ? "<option value='0'>{$xx['none']}</option>\n".$options : "<script>showX('scMenu',0)</script>\n";
	echo "</select>\n";
}

function userMenu($selUser) {
	$stH = dbQuery("SELECT `ID`,`name` FROM `users` WHERE `status` >= 0 ORDER BY `name`");
	while (list($ID,$name) = $stH->fetch(PDO::FETCH_NUM)) {
		$selected = ($selUser == $ID) ? ' selected' : '';
		echo "<option value='{$ID}'{$selected}>{$name}</option>\n";
	}
}

function repeatBox() { //make repeat box
	global $xx, $wkDays, $months, $todo, $r_t, $ri1, $ri2, $rp1, $rp2, $r_m, $rul, $pholdD;
	
	$untilChecked = $todo ? " ({$xx['evt_until_checked']})" : '';
	echo "<fieldset class='repBox' id='repBox'><legend>{$xx['evt_set_repeat']}</legend>
<p><label><input type='radio' name='r_t' id='r_t0' value='0'".(!$r_t ? " checked" : '').">{$xx['evt_no_repeat']}</label></p>
<p><label><input type='radio' name='r_t' id='r_t3' value='3'".($r_t == "3" ? " checked" : '').">{$xx['evt_rolling']} {$untilChecked}</label></p>
<p><label><input type='radio' name='r_t' id='r_t1' value='1'".($r_t == "1" ? " checked" : '').">{$xx['evt_repeat_on']}</label>
<input type='number' min='1' max='99' name='ri1' style='width:30px' onclick='\$I(`r_t1`).checked=true;' value='{$ri1}'>
<select name='rp1' id='rp1' onclick='\$I(`r_t1`).checked=true;'>\n";
	for ($i = 1; $i < 5; $i++) { echo "<option value='{$i}'".($rp1 == $i ? ' selected' : '').">".$xx["evt_period1_{$i}"]."</option>\n"; }
	echo "</select></p>
<p><label><input type='radio' name='r_t' id='r_t2' value='2'".($r_t == "2" ? " checked" : '').">{$xx['evt_repeat_on']}</label> 
<select name='ri2' id='ri2' onclick='\$I(`r_t2`).checked=true;'>\n";
	for ($i = 1; $i < 6; $i++) { echo "<option value='{$i}'".($ri2 == $i ? ' selected' : '').">".$xx["evt_interval2_{$i}"]."</option>\n"; }
	echo "</select>\n";
	echo "<select name='rp2' id='rp2' onclick='\$I(`r_t2`).checked=true;'>\n";
	for ($i = 1; $i < 8; $i++) { echo "<option value='{$i}'".($rp2 == $i ? ' selected' : '').">{$wkDays[$i]}</option>\n"; }
	echo "</select>
		{$xx['of']} ";
	echo "<select name='rpm' id='rpm' onclick='\$I(`r_t2`).checked=true;'>
<option value='0'".($r_m == 0 ? " selected" : '').">{$xx['evt_each_month']}</option>\n";
	for ($i = 1; $i < 13; $i++) { echo "<option value='{$i}'".($r_m == $i ? ' selected' : '').">{$months[$i-1]}</option>\n"; }
	echo "</select></p>
<div class='tbspace'>{$xx['evt_until']} 
<input class='date' type='text' name='rul' id='rul' placeholder='($pholdD}' value='{$rul}'><span class='dtPick' title='{$xx['evt_select_date']}' onclick='dPicker(1,``,`rul`,`sda`); return false;'>&#x1F4C5;</span> ({$xx['evt_blank_no_end']})</div>
<div class='floatC'><button type='submit'>{$xx['evt_set']}</button></div>
</fieldset>\n";
}

function recipBox() { //make recipient selection box
	global $xx, $nal;

	//collect selectable recipients
	$listArr = preg_grep("~^[^+].+\.txt$~",scandir('reciplists/')); //all lists
	$stH = dbQuery("SELECT `name`,`email`,`phone`,`msingID` FROM `users`WHERE `ID` > 1 AND `status` >= 0 ORDER BY `name`");
	$registArr = $stH->fetchAll(PDO::FETCH_NAMED); //2-dim array
	if (is_file('reciplists/+recipients.txt')) { //recips from +recipients list
		$fileArr = file('reciplists/+recipients.txt', FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
		array_walk($fileArr, function (&$line, $key) { $line = preg_replace(['~^\s*#.*~','~\s{2,}~'],['',' '],$line); }); //flush comment lines and mutiple spaces
		$publicArr = array_filter($fileArr); //remove empty lines
	}

	$nalX = str_replace(' ','',"~;{$nal};"); //remove spaces, ~ to avoid result 0
	echo "<fieldset  class='recipBox' id='recipBox'><legend>{$xx['evt_select_recips']}</legend>\n";
	echo "<span class='closeXr' onclick='toggleX(`recipBox`);'>&nbsp;&#10060;&nbsp;</span>\n";
	if ($listArr) {
		echo "<h3 class='floatC'>{$xx['evt_recip_lists']}</h3>\n";
		foreach ($listArr as $list) {
			$checked = strpos($nalX,"[$list]") ? ' checked' : '';
			echo "<p><label><input type='checkbox' name=\"{$list}\" value='1' onclick='checkRecip(this,`list`);'{$checked}>{$list}</label></p>\n";			
		}
	}
	echo "<h3 class='floatC marT4'>{$xx['evt_regist_recips']}</h3>\n";
	foreach ($registArr as $recip) {
		$checked = (strpos($nalX,";{$recip['name']};") or strpos($nalX,";{$recip['email']};") or strpos($nalX,";{$recip['msingID']};") or strpos($nalX,";{$recip['phone']};")) ? ' checked' : '';
		echo "<p><label><input type='checkbox' name=\"{$recip['name']};{$recip['email']};{$recip['msingID']};{$recip['phone']}\" value='1' onclick='checkRecip(this,`regist`);'{$checked}>{$recip['name']}</label></p>\n";			
	}
	if (!empty($publicArr)) {
		echo "<h3 class='floatC marT4'>{$xx['evt_public_recips']}</h3>\n";
		foreach ($publicArr as $line) {
			$recip = trim(explode("#",$line)[0]); //remove comments
			$checked = strpos($nalX,";{$recip};") ? ' checked' : '';
			echo "<p><label><input type='checkbox' name=\"{$recip}\" value='1' onclick='checkRecip(this,`public`);'{$checked}>{$line}</label></p>\n";			
		}
	}
	echo "</fieldset>\n";
}

//init
$todo = '';
$pholdD = IDtoDD('yyyy-mm-dd'); //make date place holder
$evtTemplTot = $templ['gen'].$templ['upc'].$templ['pop'];
if ($set['evtWinSmall']) { //reduced Event window
	$eExt = $_POST['eExt'] ?? 0;
} else {
	$eExt = 1;
}
echo "<form id='event' name='event' action='index.php' method='post' enctype='multipart/form-data'>
{$formCal}
<input type='hidden' name='xP' value='30'>
<input type='hidden' name='state' value='{$state}'>
<input type='hidden' name='eid' value='{$eid}'>
<input type='hidden' name='evD' value='{$evD}'>
<input type='hidden' name='oUid' value='{$oUid}'>
<input type='hidden' name='ediN' value='{$ediN}'>
<input type='hidden' name='eExt' value='{$eExt}'>
<input type='hidden' id='att' name='att' value='{$att}'>\n";
if (strpos($evtTemplTot,'4') !== false and $usr['privs'] < $set['xField1Rights']) {
	echo "<input type='hidden' name='tx2' value='{$tx2}'>\n";
}
if (strpos($evtTemplTot,'5') !== false and $usr['privs'] < $set['xField2Rights']) {
	echo "<input type='hidden' name='tx3' value='{$tx3}'>\n";
}
echo "<div class='evtCanvas'>\n";
if ($cat['app'] and $usr['privs'] > 3) { //manager or admin
	echo "<div class='apdBar'><label><input type='checkbox' name='apd' value='yes'".($apd ? " checked" : '').">{$xx['evt_approved']}</label></div>\n";
}
echo "<table class='evtForm'>\n";
echo "<tr>
<td>{$xx['evt_title']}:</td><td><input class='emoYes' onblur='lastFocus = this;' type='text' name='tit' id='tit' style='width:97%' maxlength='255' value=\"{$tit}\">
<td>\n";
if ($usr['ID'] > 1 and $usr['pEvts'] and ($set['privEvents'] == 1 or $set['privEvents'] == 2)) { //logged in - private allowed
	$checked = ($pri or ($set['privEvents'] == 2 and $state =='add' and !$eMsg)) ? " checked" : '';
	echo "<label><input type='checkbox' name='pri' value='yes'{$checked}>{$xx['evt_private']}</label>";
}
echo "</td>\n</tr>\n";
if (strpos($evtTemplTot,'1') !== false) {
	$placeHolder = $set['mapViewer'] ? " placeholder='{$xx['evt_address_button']}'" : '';
	echo "<tr>\n<td>{$xx['evt_venue']}:</td><td>\n";
	if ($set['venueInput'] == 0) {
		echo "<input type='text' name='ven' id='ven'{$placeHolder} style='width:97%' maxlength='220' value='{$ven}'></td><td>";
	} elseif ($set['venueInput'] == 1) {
		echo "<select name='ven' id='ven' style='width:97%'>\n"; venueMenu($ven); echo "</select></td><td>";
	} else {  //2
		if ($vel) {
			$hide1 = " class='hide'";
			$hide2 = '';
			$name1 = '';
			$name2 = 'ven';
		} else {
			$hide1 = '';
			$hide2 = " class='hide'";
			$name1 = 'ven';
			$name2 = '';
		}
		echo "<input type='text' id='venue1'{$hide1} name='{$name1}'{$placeHolder} style='width:97%' maxlength='128' value='{$ven}'>";
		echo "<select id='venue2'{$hide2} name='{$name2}' style='width:97%'>\n"; venueMenu($ven); echo "</select></td>";
		echo "<td><label id='venBoxLbl'><input type='checkbox' onclick='toggleVenue(this);' name='vel' id='vel' value='1'".($vel ? ' checked' : '').">{$xx['evt_list']}</label>";
	}
	echo "</td>\n</tr>\n";
}
//category always required
echo "<tr>\n<td>{$xx['evt_category']}:</td><td colspan='2'>"; catMenu($cid);
if (!empty($cat['sub'])) {
	echo "&emsp;<span id='scMenu'>{$xx['evt_subcategory']}: "; scatMenu($sid);
	echo "</span></td>\n</tr>\n";
}

$hidden = ($ald or $ntm)  ? " style='visibility:hidden;'" : '';
echo "<tr>
	<td>{$xx['evt_start_date']}:</td>
	<td colspan='2'><input class='date' type='text' name='sda' id='sda' placeholder='($pholdD}' value='{$sda}'><span class='dtPick' title=\"{$xx['evt_select_date']}\" onclick='dPicker(0,``,`sda`,`eda`);return false;'>&#x1F4C5;</span>
	&emsp;<span id='dTimeS'{$hidden}><input inputmode='decimal' class='time' type='text' name='sti' id='sti' value='{$sti}'><span class='dtPick' title=\"{$xx['evt_select_time']}\" onclick='tPicker(`sti`);return false;'>&#x1F552;</span></span>";
if (!$cat['fur']) { //no fixed event duration
	echo "&emsp;<label><input type='checkbox' onclick='hideTimes(this);' name='ald' id='ald' value='1'".($ald ? ' checked' : '').">{$xx['evt_all_day']}</label>";
}
echo "</td>\n</tr>\n";
if (!$cat['fur']) { //no fixed event duration
	$hide = !$usr['mEvts'] ? " class='hidden'" : '';
	echo "<tr>\n";
	echo "<td><span{$hide}>{$xx['evt_end_date']}:</span></td>
	<td colspan='2'><span{$hide}><input class='date' type='text' name='eda' id='eda' placeholder='($pholdD}' value='{$eda}'><span class='dtPick' title=\"{$xx['evt_select_date']}\" onclick='dPicker(1,``,`eda`,`sda`); return false;'>&#x1F4C5;</span></span>\n";
	echo "&emsp;<span id='dTimeE'{$hidden}><input inputmode='decimal' class='time' type='text' name='eti' id='eti' value='{$eti}'><span class='dtPick' title=\"{$xx['evt_select_time']}\" onclick='tPicker(`eti`); return false;'>&#x1F552;</span></span>";
	echo "&emsp;<label><input type='checkbox' onclick='hideTimes(this);' name='ntm' id='ntm' value='1'".($ntm ? ' checked' : '').">{$xx['evt_no_time']}</label>";
	echo "</td>";
	echo "</tr>\n";
}
if ($usr['rEvts']) { //repeating allowed
	echo "<tr>
		<td colspan='3'>{$repTxt}".(!$cat['rpt'] ? "&ensp;<button type='button' onclick='showX(`repBox`,1);'>{$xx['evt_change']}</button>" : '')."<br></td>
	</tr>\n";
}
echo "</table>\n";
if ($set['evtWinSmall']) { //reduced Event window
	echo "<div id='eExtS' class='evtExt red' onclick='ewShow(`eExt`);' title='More details'>".($eExt ? '&#9650;' : '&#9660;')."</div>\n";
} else {
	echo "<div class='evtExt'></div>\n";
}

$display = $eExt ? 'block' : 'none';
echo "<div id='eExt' style='display:{$display};'>\n";
echo "<table class='evtForm'>\n";
if (strpos($evtTemplTot,'3') !== false) {
	$descrHelp = "{$xx['evt_descr_help']}<br>{$xx['evt_descr_help_img']}<br>{$xx['evt_descr_help_eml']}<br>{$xx['evt_descr_help_url']}";
	echo "<tr>\n<td>{$xx['evt_description']}:<br><br>(<span class='info noPrint' onmouseover='pop(this,`".htmlspecialchars($descrHelp, ENT_QUOTES | ENT_HTML5)."`,`normal`,80);'>?</span>)</td>";
	if (!trim($tx1) and is_file("files/descriptions.txt")) {
		if (preg_match("~<{$cid}>(.+?)(?:<\d\d?>|$)~s",file_get_contents('files/descriptions.txt'),$match)) {
			$tx1 = trim($match[1],"\n\r");
		}
	}
	echo "<td><textarea class='emoYes' onblur='lastFocus = this;' name='tx1' id='tx1' rows='3' cols='1' style='width:98%'>{$tx1}</textarea></td>\n</tr>\n";
}
if (strpos($evtTemplTot,'4') !== false and $usr['privs'] >= $set['xField1Rights']) {
	echo "<tr>\n<td>".($set['xField1Label'] ? $set['xField1Label'] : $xx['sch_extra_field1']).":</td><td><textarea class='emoYes' onblur='lastFocus = this;' name='tx2' id='tx2' rows='1' cols='1' style='width:98%' maxlength='255'>{$tx2}</textarea></td>\n</tr>\n";
}
if (strpos($evtTemplTot,'5') !== false and $usr['privs'] >= $set['xField2Rights']) {
	echo "<tr>\n<td>".($set['xField2Label'] ? $set['xField2Label'] : $xx['sch_extra_field2']).":</td><td><textarea class='emoYes' onblur='lastFocus = this;' name='tx3' id='tx3' rows='1' cols='1' style='width:98%' maxlength='255'>{$tx3}</textarea></td>\n</tr>\n";
}
if ($att) {
	$label = $xx['evt_attachments'].':';
	foreach(explode(';',trim($att,';')) as $attachment) {
		echo "<tr>\n<td>{$label}</td><td><span class='select' title='{$xx['evt_click_to_remove']}' onclick='detach(this,`{$attachment}`);'>&nbsp;&#10060;&nbsp;</span><a title='{$xx['evt_click_to_open']}' href='dloader.php?ftd=./attachments/".rawurlencode($attachment)."&amp;nwN=".substr($attachment,14)."'>".substr($attachment,14)."</a></td>\n</tr>\n";
		$label = '';
	}
}
if ($usr['upload']) { //may upload
	echo "<tr>\n<td>{$xx['evt_attach_file']}:</td><td><input type='file' id='uplAtt' name='uplAtt[]' multiple>&emsp;({$xx['max']} {$set['maxUplSize']} MB)</td>\n</tr>\n";
}
if ($set['emlService'] or $set['tlgService'] or $set['smsService'] and (!$cat['app'] or $apd)) {
	echo "<tr>\n<td colspan='2'><hr></td>\n</tr>\n";
	echo "<tr>\n<td>{$xx['evt_notification']}:</td><td>";
	echo "<label><input type='checkbox' name='nen' value='yes'".($non ? " checked" : '').">{$xx['evt_now_and_or']}</label>&nbsp;";
	echo "<input type='text' name='not' style='width:20px' maxlength='2' value=\"{$not}\"> {$xx['evt_days_before_event']}
</td>\n</tr>\n";
	$notHelp = $xx['evt_not_help'];
	echo "<tr>\n<td>{$xx['evt_to']}:&ensp;(<span class='info noprint' onmouseover='pop(this,`".htmlspecialchars($notHelp, ENT_QUOTES | ENT_HTML5)."`,`normal`,80);'>?</span>)</td><td>
<input type='text' name='nal' id='nal' style='width:93%' maxlength='255' value=\"{$nal}\"><span title='{$xx['evt_select_from_list']}' onclick='toggleX(`recipBox`)'>👩‍🦱</span></td>\n</tr>\n";
}
if (strpos($evtTemplTot,'7') !== false) {
	echo "<tr>\n<td colspan='2'><hr></td>\n</tr>\n";
	echo "<tr>\n<td>{$xx['evt_added']}:</td><td>".IDTtoDDT($_SESSION['evt']['adt'])." {$xx['by']} ";
	if ($usr['privs'] > 3) { //manager or admin
		echo "<select name='uid' id='uid'>\n"; userMenu($uid); echo "</select>\n";
	} else {
		echo $_SESSION['evt']['own'];
	}
	if ($_SESSION['evt']['mdt'] and $_SESSION['evt']['edr']) {
		echo "</td>\n</tr>\n<tr>\n<td>{$xx['evt_edited']}:</td><td>".IDTtoDDT($_SESSION['evt']['mdt'])." {$xx['by']} {$_SESSION['evt']['edr']}"; }
	echo "</td>\n</tr>\n";
}
echo "</table>\n";
echo "</div>\n";

if ($usr['rEvts'] and !$cat['rpt']) { //add repeat box
	repeatBox();
}
if ($set['emlService'] or $set['tlgService'] or $set['smsService'] and (!$cat['app'] or $apd)) {
	recipBox(); //add recipients selection box
}
echo "</div>\n";

echo "<div class='ewButtons floatC noPrint'>\n";
if ($state[0] == 'a') { //add
	echo "<button type='submit' name='action' value='add_exe_cls'>{$xx['evt_add_close']}</button>
&ensp;<button type='submit' name='action' value='add_exe'>{$xx['evt_add']}</button>";
} else { //edit
	echo "<button type='submit' name='action' value='upd_exe_cls'>{$xx['evt_save_close']}</button>
		&ensp;<button type='submit' name='action' value='upd_exe'>{$xx['evt_save']}</button>
		&ensp;<button type='submit' name='action' value='add_exe'>{$xx['evt_clone']}</button>\n";
	if ($set['evtDelButton'] == 1 or ($set['evtDelButton'] == 2 and $usr['privs'] > 3)) {
		echo "&ensp;<button type='submit' name='action' value='del_exe_cls' onclick='return confirm(`{$xx['evt_delete']} {$tit}?`);'>{$xx['evt_delete']}</button>\n";
	}
}
echo "&ensp;<button type='button' onclick='javascript:self.close();'>{$xx['evt_close']}</button>
</div>
</form>\n";
?>
<script>$I("tit").focus();</script>
