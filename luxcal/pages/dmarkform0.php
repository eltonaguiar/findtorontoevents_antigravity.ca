<?php
//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //via script only

$evDD = IDtoDD($evD); //selected date -  display format

echo "<div class='evtCanvas'>\n";
echo "<br><p>{$xx['mrk_text_and_color']}: <span style='padding:0 80px; color:{$tx2}; background-color:{$tx3};'>{$tit}</span></p></br>\n";
echo "</div>
<br>\n";
echo "<div class='floatC'>\n".($r_t > 0 ? $xx['mrk_is_repeating'] : $xx['mrk_is_multiday']).".
<br>{$xx['evt_edit_series_or_occurrence']}<br><br>
</div>\n";
echo "<form id='event' class='floatC' name='event' action='index.php' method='post'>
{$formCal}
<input type='hidden' name='xP' value='31'>
<input type='hidden' name='state' value='{$state}'>
<input type='hidden' name='eid' value='{$eid}'>
<input type='hidden' name='evD' value='{$evD}'>
<button type='submit' name='action' value='edi2'>{$xx['evt_edit_series']}</button>&ensp;
<button type='submit' name='action' value='edi1'>{$xx['evt_edit_occurrence']} ({$evDD})</button>&ensp;
<button type='button' onclick='javascript:self.close();'>{$xx['evt_close']}</button>
</form>\n";
?>
