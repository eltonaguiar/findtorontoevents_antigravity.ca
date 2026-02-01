<?php
//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //via script only

$evDD = IDtoDD($evD); //selected date -  display format

$snm = $sid ? $cat['sub'][($sid-1)][0] : '';
$evt = array ('ven' => $ven, 'cnm' => $cat['cnm'], 'tx1' => $tx1, 'tx2' => $tx2, 'tx3' => $tx3, 'snm' => $snm); //tx1 - tx3: with hyperlinks
$catColor = ($cat['col'] ? "color:{$cat['col']};" : '').($cat['bco'] ? "background-color:{$cat['bco']};" : '');
echo "<div class='evtCanvas'>\n";
echo "<table class='evtForm'>
<tr><td>{$xx['evt_title']}:</td><td><span".($catColor ? " style='{$catColor}'" : '').">{$tit}</span></td></tr>\n";
echo makeE($evt,$templ['gen'],'td',"\n",'12345');
echo "</table>
</div>
<br>\n";
echo "<div class='floatC'>\n".($r_t > 0 ? $xx['evt_is_repeating'] : $xx['evt_is_multiday']).".
<br>{$xx['evt_edit_series_or_occurrence']}<br><br>
</div>\n";
echo "<form id='event' class='floatC' name='event' action='index.php' method='post'>
{$formCal}
<input type='hidden' name='xP' value='30'>
<input type='hidden' name='state' value='{$state}'>
<input type='hidden' name='eid' value='{$eid}'>
<input type='hidden' name='evD' value='{$evD}'>
<input type='hidden' name='oUid' value='{$oUid}'>
<button type='submit' name='action' value='edi2'>{$xx['evt_edit_series']}</button>&ensp;
<button type='submit' name='action' value='edi1'>{$xx['evt_edit_occurrence']} ({$evDD})</button>&ensp;
<button type='button' onclick='javascript:self.close();'>{$xx['evt_close']}</button>
</form>\n";
?>
