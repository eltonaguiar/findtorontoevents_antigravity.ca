<?php
/*
= view/manage thumbnails script =

This file is part of the LuxCal Web Calendar.
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
License https://www.gnu.org/licenses/gpl.html GPL version 3

The LuxCal Web Calendar is distributed WITHOUT ANY WARRANTY.
*/

//sanity check
if (empty($lcV)) { exit('not permitted ('.substr(basename(__FILE__),0,-4).')'); } //launch via script only

function getTnList($path,$sort,$order) {
	global $tnSearch, $set;
	
  $fileList = [];
  if (!$files = array_filter(scandir($path), function ($v) use ($set) { return (strlen($v) > 4 and stripos($set['tnlTypes'],substr($v,-3))); })) { return false; }
  foreach ($files as $fName) {
		if (!empty($tnSearch) and stripos(substr($fName,0,-4),$tnSearch) === false) { continue; }
		$fileList[] = [
			'name' => $fName,
			'name-id' => $fName[4] != '~' ? $fName : substr($fName,5),
			'size' => filesize($path.$fName),
			'lastmod' => filemtime($path.$fName)
    ];
  }
	$mulFactor = $order == 'a' ? 1 : -1;
	uasort($fileList,function($a,$b) use($sort,$mulFactor) {return (($a[$sort] > $b[$sort]) ? 1 : -1) * $mulFactor;}); //sort on $sort-field
  return $fileList;
}

function showTnails($userID,$myTnails,$mayDel) {
	global $xx, $tnPath, $tnailList, $delLimit;

	$nofTnails = 0;
	foreach($tnailList as $tnail) {
		if (substr($tnail['name'],0,5) == str_pad($userID,4,'0',STR_PAD_LEFT).'~')  { //my thumbnails
			if (!$myTnails) { continue; }
		} else { //other thumbnails
			if ($myTnails) { continue; }
		}
		$fullName = str_replace(' ','%20',$tnail['name']); //deal with spaces
		$tnID = ($myTnails ? 'mTn' : 'oTn').++$nofTnails;
		$stH = dbQuery("SELECT `sDate`,`eDate`,`rType`,`rUntil`
			FROM `events`
			WHERE status >= 0 AND `text1` LIKE '%{$fullName}%' OR `text2` LIKE '%{$fullName}%' OR `text3` LIKE '%{$fullName}%'");
		$lastUsed = '0000-00-00';
		while ($row = $stH->fetch(PDO::FETCH_ASSOC)) {
			if ($row['rType'] > 0 and $row['rUntil'][0] == '9') { $lastUsed = '9999-99-99'; break; }
			if ($row['rType'] > 0 and $row['rUntil'][0] != '9' and $lastUsed < $row['rUntil']) { $lastUsed = $row['rUntil']; }
			if ($row['eDate'][0] != '9' and $lastUsed < $row['eDate']) { $lastUsed = $row['eDate']; }
			if ($lastUsed < $row['sDate']) { $lastUsed = $row['sDate']; }
		}
		$stH = null;
		$delX = '';
		if ($mayDel and $lastUsed[0] != '9' and ($lastUsed[0] == '0' or $lastUsed < $delLimit)) { //may delete thumbnail
			$delX = "\n<span id='{$fullName}' onclick='deleteTn(this,`{$xx['tns_del_tnail']}`);'>&#10060;</span>";
		}
		$lastUsed = $lastUsed[0] == '0' ? $xx['tns_not_used'] : ($lastUsed[0] == '9' ? $xx['tns_infinite'] : IDtoDD($lastUsed));
		echo "<div class='tnBox'>
<div id='{$tnID}' onclick='toClipboard(this)'>
<input type='text' id='s{$tnID}' value=' {$fullName} '>
<img src='{$tnPath}{$fullName}' alt='{$tnID}'>
<p>{$tnail['name-id']}<br>".IDtoDD(date('Y-m-d',$tnail['lastmod']))."<br>({$lastUsed})</p>
</div>{$delX}
</div>\n";
	}
	if ($nofTnails == 0) {
		echo "<br><p class='floatC'>{$xx['none']}</p>";
	}
}
/* image resize function
$file - file name to resize
$width - new image width
$height - new image height
$output - name of the new file (include path if needed)
$deleteOriginal - if true the original image will be deleted
$quality - enter 1-100 (100 is best quality) default is 100
*/
function resize_image($file,$width,$height,$output,$deleteOriginal = true,$quality = 100) {
 
	//setting defaults and meta
	list($widthOld, $heightOld, $imageType) = getimagesize($file);

	//calculating proportionality
	if      ($width  == 0)  $factor = $height/$heightOld;
	elseif  ($height == 0)  $factor = $width/$widthOld;
	else                    $factor = min($width / $widthOld, $height / $heightOld);
	$newWidth  = round($widthOld * $factor);
	$newHeight = round($heightOld * $factor);

	//loading image to memory
	switch ( $imageType ) {
		case IMAGETYPE_JPEG: $image = imagecreatefromjpeg($file); break;
		case IMAGETYPE_GIF: $image = imagecreatefromgif($file); break;
		case IMAGETYPE_PNG: $image = imagecreatefrompng($file); break;
		default: return false;
	}

	//this is the resizing/resampling/transparency-preserving magic
	$imageResized = imagecreatetruecolor($newWidth,$newHeight);
	if (($imageType == IMAGETYPE_GIF) || ($imageType == IMAGETYPE_PNG)) {
		$transparency = imagecolortransparent($image);
		$palletsize = imagecolorstotal($image);

		if ($transparency >= 0 && $transparency < $palletsize) {
			$transparentColor = imagecolorsforindex($image,$transparency);
			$transparency     = imagecolorallocate($imageResized,$transparentColor['red'],$transparentColor['green'],$transparentColor['blue']);
			imagefill($imageResized,0,0,$transparency);
			imagecolortransparent($imageResized, $transparency);
		}
		elseif ($imageType == IMAGETYPE_PNG) {
			imagealphablending($imageResized, false);
			$color = imagecolorallocatealpha($imageResized,0,0,0,127);
			imagefill($imageResized,0,0,$color);
			imagesavealpha($imageResized,true);
		}
	}
	imagecopyresampled($imageResized,$image,0,0,0,0,$newWidth,$newHeight,$widthOld,$heightOld);

	//delete original, if needed
	if ($deleteOriginal) {
		@unlink($file);
	}
	
	//writing image according to type to the output destination and image quality
	switch ($imageType) {
		case IMAGETYPE_GIF:  imagegif($imageResized,$output); break;
		case IMAGETYPE_JPEG: imagejpeg($imageResized,$output,$quality); break;
		case IMAGETYPE_PNG:
			$quality = 9 - (int)((0.9*$quality)/10.0);
			imagepng($imageResized,$output,$quality);
			break;
		default: return false;
	}
	return true;
}

//here it starts

//get POST arguments
$tnSort = $_POST['tnSort'] ?? 'n';
$tnOrder = $_POST['tnOrder'] ?? 'a';
$tnSearch = trim($_POST['tnSearch'] ?? '');
$tnOwrite = !empty($_POST['tnOwrite']) ? 1 : 0;

//init
$tnPath = './thumbnails/';
$nMsg = $eMsg = ''; //notice, error messages
$mayMng = $usr['tnPrivs'][0] == '2';
$sortOn = $tnSort == 'n' ? 'name-id' : 'lastmod';
$delLimit = date('Y-m-d',$nowTS-($set['tnlDelDays'] * 86400)); //date after which no delete allowed

//thumbnail to delete?
if (isset($_POST['delTn']) and file_exists("{$tnPath}{$_POST['delTn']}")) {
	unlink("{$tnPath}{$_POST['delTn']}");
	$tnail = $_POST['delTn'][4] == '~' ? substr($_POST['delTn'],5) : $_POST['delTn'];
	$nMsg .= "{$xx['tns_tnail']} {$tnail} {$xx['tns_deleted']}<br>";
}

//thumbnails to upload?
if (!empty($_FILES['uplTnl'])) { //if file(s) uploaded, save files to thumbnails folder
	$nrUpload = 0;
	foreach($_FILES['uplTnl']['name'] as $k => $fName) {
		if ($fName) {
			if ($_FILES['uplTnl']['error'][$k] > 1) { $eMsg .= "{$fName} {$xx['tns_upload_error']}<br>"; continue; }
			if (stripos($set['tnlTypes'],substr($fName,-4)) === false) { $eMsg .= "{$fName} {$xx['tns_no_valid_img']}<br>"; continue; }
			if ($_FILES['uplTnl']['error'][$k] == 1 or $_FILES['uplTnl']['size'][$k] > ($set['maxUplSize'] * 1048570)) { $eMsg .= "{$fName} {$xx['tns_file_too_large']}<br>"; continue; } //max. $set['maxUplSize'] MB
			$tnName = $fName[4] == '~' ? substr($fName,5) : $fName; //remove possible userID prefix
			$tnName = str_replace([' ',"'",'"'],'_',$tnName); //get rid of spaces and quotes
			$tnfName = str_pad($usr['ID'],4,'0',STR_PAD_LEFT).'~'.$tnName; //add current userID prefix
			if ($tnOwrite or !file_exists("./thumbnails/{$tnfName}")) {
				move_uploaded_file($_FILES['uplTnl']['tmp_name'][$k],"./thumbnails/{$tnfName}");
				$nrUpload++;
				$tnSize = getimagesize("./thumbnails/{$tnfName}");
				if ($tnSize[0] > $set['tnlMaxW'] or $tnSize[1] > $set['tnlMaxH']) { //width & height
					$result = resize_image("./thumbnails/{$tnfName}",$set['tnlMaxW'],$set['tnlMaxH'],"./thumbnails/{$tnfName}"); //resize image
					if ($result) {
						$nMsg .= "{$tnName} {$xx['tns_resized']}<br>";
					} else {
						$eMsg .= "{$tnName} {$xx['tns_resize_error']}<br>";
					}
				}
			} else {
				$nMsg .= "{$tnName} {$xx['tns_tn_exists']}<br>";
			}
		}
	}
	if ($nrUpload > 0) {
		$nMsg .= "{$nrUpload} {$xx['tns_tn_uploaded']}<br>";
	}
}

//get all thumbnails
$tnailList = getTnList($tnPath,$sortOn,$tnOrder);

//load page
echo "<aside class='aside sBoxTn'>
<h3>{$xx['tns_man_tnails_instr']}</h3>
<ul>\n<li>{$xx['tns_help_general']}</li>\n";
if ($mayMng) {
	$validExt = str_replace(',',', ',$set['tnlTypes']);
	echo "<li>".str_replace(['$1','$2','$3'],[$validExt,$set['tnlMaxW'],$set['tnlMaxH']],$xx['tns_help_upload'])."</li>\n";
}
if ($mayMng and $set['tnlDelDays'] != 0) {
	echo "<li>".str_replace('$1',IDtoDD($delLimit),$xx['tns_help_delete'])."</li>\n";
}
echo "</ul>
</aside>\n";
echo "<div class='centerBox sBoxTn'>
<form id='tnails' action='index.php' method='post' enctype='multipart/form-data'>
<fieldset><legend>{$xx['tns_man_tnails']}</legend>\n
<table class='list'>
<tr>\n<td>{$xx['tns_sort_by']}:</td>
<td><label><input type='radio' name='tnSort' value='n'".($tnSort == 'n' ? " checked" : '').">{$xx['tns_name']}</label></td>
<td><label><input type='radio' name='tnSort' value='d'".($tnSort == 'd' ? " checked" : '').">{$xx['tns_date']}</label></td>\n</tr>
<tr>\n<td>{$xx['tns_sort_order']}:</td>
<td><label><input type='radio' name='tnOrder' value='a'".($tnOrder == 'a' ? " checked" : '').">{$xx['tns_ascending']}</label></td>
<td><label><input type='radio' name='tnOrder' value='d'".($tnOrder == 'd' ? " checked" : '').">{$xx['tns_descending']}</label></td>\n</tr>\n
<tr>\n<td>{$xx['tns_search_fname']}:</td>
<td colspan='2'><input type='text' name='tnSearch' id='tnSearch' value=\"{$tnSearch}\" maxlength='20' size='15'></td>\n</tr>\n";
if ($mayMng) { //may upload tnails
	echo "<tr>\n<td>{$xx['tns_upload_tnails']}:</td>
<td colspan='2'><input type='file' id='uplTnl' name='uplTnl[]' accept='image/*' multiple>&ensp;({$xx['max']} {$set['maxUplSize']} MB)</td>\n</tr>\n";
	echo "<tr>\n<td></td>
<td colspan='2'><label><input type='checkbox' name='tnOwrite' value='1'>{$xx['tns_overwrite']}</label></td>\n</tr>\n";
}
echo "</table>
<br>
<div class='floatC'><button type='submit' name='tnlExe' value='y'>{$xx['submit']}</button></div>
</fieldset>
</form>\n";
if ($nMsg) {
	echo "<br><p class='confirm'>{$nMsg}</p>\n";
}
if ($eMsg) {
	echo "<p class='error'>{$eMsg}</p>\n";
}
echo "</div>\n";
echo "<br class='clear'><br><h3 class='floatC'>===== {$xx['tns_your_tnails']} =====</h3>\n";
$mayDel = ($mayMng and $set['tnlDelDays'] != 0) ? $set['tnlDelDays'] : 0;
showTnails($usr['ID'],true,$mayDel);
if ($usr['tnPrivs'][1] >= '1') { //view or manage all
	echo "<br class='clear'><br><h3 class='floatC'>===== {$xx['tns_other_tnails']} =====</h3>";
	$mayDel = ($usr['tnPrivs'][1] == '2' and $set['tnlDelDays'] != 0) ? $set['tnlDelDays'] : 0;
	showTnails($usr['ID'],false,$mayDel);
}
?>
