<?php
/*
= LuxCal - BOM removing utility =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

Files with utf-8 character encoding may have a three-byte signature, called BOM 
(Byte Order Mask), at the beginning of the file. The BOM defines the byte order 
("little-endian" or "big-endian") for multi-byte characters and can sometimes 
cause unexpected characters to appear at the top of a web page.

=================================================================================
For the LuxCal language files we recommend character encoding "utf-8 without BOM"
=================================================================================

This script should be run from the lang/ folder. It will read the language files 
in the current folder and, if present, removes the BOM from the beginning of each 
language file (files: ai-{lang}.php, ug-{lang}.php and ui-{lang}.php).
*/

if (isset($_GET['f'])) {
	if (!preg_match('~^list$|(^(ai-|ui-|ug-)[\w]+)$~i', $_GET['f'])) { exit('Invalid file name.'); }
	$f = strtolower($_GET['f']);
	$f .= ($f != 'list') ? '.php' : '';
}
if (empty($f) or $f == 'list') {
	//init
	$dir = "./";
	$files = $boms = 0;
	echo "== LuxCal BOM Removing Utility ==<br><br>";
	//do it!
	$fArray = scandir($dir);
	if ($fArray === false) { exit("unable to open directory $dir"); } //run from lang/ directory
	foreach ($fArray as $fileName) {
		if (!preg_match("%^(ai-|ug-|ui-)\w+\.php$%i",$fileName)) { continue; } //language files only
		if ($f == 'list') {
			echo '- '.$fileName.'<br>';
		} else {
			$string = file_get_contents($dir.$fileName);
			$files++;
			if(substr($string,0,3) == pack('CCC',0xef,0xbb,0xbf)) { //hex representation of BOM
				file_put_contents($dir.$fileName,substr($string,3)); //remove BOM
				$boms++;
			}
		}
	}
	if ($f != 'list') {
		//display results
		if ($files) {
			echo "Number of files processed: ".$files."<br>Number of BOMs removed: ".$boms;
		} else {
			echo "No language files found.";
		}
	} else {
		echo "<br>End of list.";
	}
} else {
	if (file_exists($f)) {
		header("Content-type: application/octet-stream");
		header("Content-Disposition: attachment; filename=$f");
		readfile($f); //send dl
	} else {
		echo "File ".$f." not present";
	}
}
?>