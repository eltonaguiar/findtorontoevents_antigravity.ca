<?php
//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

if ($set['emojiPicker']) { //enable emoji picker
	echo "<script>new EmojiPicker({selector:'.emoButton', fields:'.emoYes'});</script>\n";
}

//init - preset colors
if ($tx2 == '') { $tx2 = '#404040'; }
if ($tx3 == '') { $tx3 = '#70E0D0'; }
$pholdD = IDtoDD('yyyy-mm-dd'); //make date place holder

echo "<form id='event' name='event' action='index.php' method='post'>
{$formCal}
<input type='hidden' name='xP' value='31'>
<input type='hidden' name='state' value='{$state}'>
<input type='hidden' name='eid' value='{$eid}'>
<input type='hidden' name='evD' value='{$evD}'>
<input type='hidden' name='ediN' value='{$ediN}'>\n";
echo "<div class='evtCanvas'>\n";
echo "<table class='evtForm'>\n";
echo "<tr>
<td>{$xx['mrk_text']}:</td><td><input type='text' class='emoYes' onblur='lastFocus = this;' name='tit' id='tit' style='width:55%; color:{$tx2}; background-color:{$tx3};' maxlength='30' value=\"{$tit}\"></td>\n";
echo "</tr>\n";
echo "<tr>\n";
echo "<td>{$xx['mrk_color']}:</td>
	<td>{$xx['mrk_text']}&nbsp;<input type='text' id='tx2' name='tx2' title=\"{$xx['mrk_select_color']}\" class=\"jscolor {onFineChange:`update(this,'','tit')`,styleElement:null}\" value='{$tx2}' size='7' maxlength='7'>&emsp;
	{$xx['mrk_background']}&nbsp;<input type='text' id='tx3' name='tx3' title=\"{$xx['mrk_select_color']}\" class=\"jscolor {onFineChange:`update(this,'tit','')`,styleElement:null}\" value='{$tx3}' size='7' maxlength='7'></td>\n";
echo "</tr>\n";
echo "<tr>
	<td>{$xx['mrk_start_date']}:</td>
	<td><input class='date' type='text' name='sda' id='sda' placeholder='($pholdD}' value='{$sda}'><span class='dtPick' title=\"{$xx['evt_select_date']}\" onclick='dPicker(0,``,`sda`,`eda`);return false;'>&#x1F4C5;</span></td>\n";
echo "</tr>\n";
echo "<tr>\n";
echo "<td>{$xx['mrk_end_date']}:</td>
	<td><input class='date' type='text' name='eda' id='eda' placeholder='($pholdD}' value='{$eda}'><span class='dtPick' title=\"{$xx['evt_select_date']}\" onclick='dPicker(1,``,`eda`,`sda`);return false;'>&#x1F4C5;</span></td>\n";
echo "<tr>\n";
echo "</table>\n";
echo "<hr>\n";
echo "<div class='repetition'>\n";
echo "<div><input type='radio' name='r_t' id='r_t0' value='0'".(!$r_t ? " checked" : '').">&nbsp;<label for='r_t0'>{$xx['evt_no_repeat']}</label></div>
<div><input type='radio' name='r_t' id='r_t1' value='1'".($r_t == "1" ? " checked" : '').">&nbsp;<label for='r_t1'>{$xx['evt_repeat_on']}</label>
<input type='number' min='1' max='99' name='ri1' style='width:30px' onclick='\$I(`r_t1`).checked=true;' value='{$ri1}'>\n";
echo "<select name='rp1' id='rp1' onclick='\$I(`r_t1`).checked=true;'>\n";
	for ($i = 1; $i < 5; $i++) { echo "<option value='{$i}'".($rp1 == $i ? ' selected' : '').">".$xx["evt_period1_{$i}"]."</option>\n"; }
echo "</select></div>
<div><input type='radio' name='r_t' id='r_t2' value='2'".($r_t == "2" ? " checked" : '').">&nbsp;<label for='r_t2'>{$xx['evt_repeat_on']}</label> 
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
echo "</select></div>
{$xx['evt_until']} <input class='date' type='text' name='rul' id='rul' placeholder='($pholdD}' value='{$rul}'><span class='dtPick' title=\"{$xx['evt_select_date']}\" onclick='dPicker(1,``,`rul`,`sda`); return false;'>&#x1F4C5;</span> ({$xx['evt_blank_no_end']})
</div>\n";
echo "<hr>\n";
echo "<table class='evtForm'>\n";
	echo "<tr>\n<td>{$xx['evt_added']}:</td><td>".IDTtoDDT($_SESSION['evt']['adt'])." {$xx['by']} ";
	echo $_SESSION['evt']['own'];
	if ($_SESSION['evt']['mdt'] and $_SESSION['evt']['edr']) {
		echo "</td>\n</tr>\n<tr>\n<td>{$xx['evt_edited']}:</td><td>".IDTtoDDT($_SESSION['evt']['mdt'])." {$xx['by']} {$_SESSION['evt']['edr']}"; }
	echo "</td>\n</tr>\n";
echo "</table>\n";
echo "</div>\n";

echo "<div class='ewButtons floatC noPrint'>\n";
if ($state[0] == 'a') { //add
	echo "<button type='submit' name='action' value='add_exe_cls'>{$xx['evt_add_close']}</button>
&ensp;<button type='submit' name='action' value='add_exe'>{$xx['evt_add']}</button>";
} else { //edit
	echo "<button type='submit' name='action' value='upd_exe_cls'>{$xx['evt_save_close']}</button>
		&ensp;<button type='submit' name='action' value='upd_exe'>{$xx['evt_save']}</button>\n";
	if ($set['evtDelButton'] == 1 or ($set['evtDelButton'] == 2 and $usr['privs'] > 3)) {
		echo "&ensp;<button type='submit' name='action' value='del_exe_cls' onclick='return confirm(`{$xx['evt_delete']} {$tit}?`);'>{$xx['evt_delete']}</button>\n";
	}
}
echo "&ensp;<button type='button' onclick='javascript:self.close();'>{$xx['evt_close']}</button>
</div>
</form>\n";
?>
<script>$I("tit").focus();</script>
