<?php
/* LuxCal PDF Print Birthday Calendar - Landscape class
Copyright 2009-2025 LuxSoft www.LuxSoft.eu
-------------------------------------------------------------------
This file is part of the LuxCal Calendar and is distributed WITHOUT 
ANY WARRANTY. See the GNU General Public License for details.
*/
$pWidth = (strtolower($pSize) === 'letter') ? 279.4 : 297; //Letter (215.9 x 279.4) or A4 (210 x 297)
$marginL = [20, $pWidth / 2 + 20]; //margin left column 1, 2
$marginR = [$pWidth / 2 + 20, 20]; //margin right column 1, 2
$ttf = extension_loaded('mbstring') ? 't' : ''; //unicode or cp1252
$font = $ttf ? 'DejaVu' : 'Helvetica';
$encoding = 'cp1252//TRANSLIT'; //if no unicode

require("./pdfs/{$ttf}fpdf.php");

class PDF extends FPDF 
{
protected $col = 1; //current column

function csConv($text) {
	global $ttf, $encoding;
	
	return $ttf ? $text : iconv('UTF-8',$encoding,$text);
}

function Header() { //page header
	global $marginL, $marginR;
	
	$this->SetY(24);
	$this->SetLeftMargin($marginL[$this->col]);
	$this->SetRightMargin($marginR[$this->col]);
	$this->SetAutoPageBreak(true,18);
	$newMonth = false;
}

function Footer() { //page footer
	global $font, $marginL, $marginR, $pWidth, $footer;

	$this->SetFont($font,'I',6);
	$this->SetTextColor(128);
	$this->SetY(-10);
	foreach([0,1] as $colNr) {
		$ftrText = $this->csConv($footer);
		$ftrArr = explode('>',$ftrText);
		if (!empty($ftrArr[0])) {
			$this->Text($marginL[$colNr],$this->GetY(),$ftrArr[0]);
		}
		if (!empty($ftrArr[1])) {
			$w = $this->GetStringWidth($ftrArr[1]);
			$this->Text(($marginL[$colNr] + $pWidth - $marginR[$colNr] - $w) / 2,$this->GetY(),$ftrArr[1]);
		}
		if (!empty($ftrArr[2])) {
			$w = $this->GetStringWidth($ftrArr[2]);
			$this->Text($pWidth - $marginR[$colNr] - $w,$this->GetY(),$ftrArr[2]);
		}
	}
}

function AcceptPageBreak() { //method accepting or not automatic page break
	global $marginL, $marginR;

	$this->col = $this->col ? 0 : 1; //go to other column
	$this->SetLeftMargin($marginL[$this->col]);
	$this->SetRightMargin($marginR[$this->col]);
	
	if($this->col == 1) { //go to column 2
		$this->SetY(24);
		return false; //keep on page
	} else { //go back to column 1
		$this->Ln(0);
		return true; //page break
	}
}

function NextPage() { //go to next page
	if($this->col == 0) { //go to column 2
		$this->col = 1;
	} else { //new page
		$this->col = 0;
		$this->Addpage();
	}
}

function printMonth() { //month title
	global $font, $pWidth, $marginL, $marginR, $logo, $title, $image, $fHEAD, $sHEAD, $cHEAD;

	$title = $this->csConv($title);
	$logo = ltrim($logo,"/\\");
	$image = ltrim($image,"/\\");
	$this->SetFont($font,$sHEAD,$fHEAD);
	list($r,$g,$b) = sscanf($cHEAD,"#%02x%02x%02x");
	$this->SetTextColor($r,$g,$b);
	if (!empty($logo)) {
		$this->Image($logo,$marginL[$this->col],18,14,0);
	}
	$strWidth = $this->GetStringWidth($title)+4;
	$this->Text($pWidth - $marginR[$this->col] - $strWidth,30,$title);
	if (!empty($image)) {
		$this->Image($image,$pWidth - $marginR[$this->col] - 40,40,40,0);
		$this->SetY(90);
	} else {
		$this->SetY(24);
	}
	$this->SetX($marginL[$this->col]);
}

function printName($dateName) { //birth date and name of person
	global $font, $marginL, $fNAME, $cNAME;

	$text = $this->csConv($dateName);
	$this->Ln(1);
	$this->SetFont($font,'',$fNAME);
	list($r,$g,$b) = sscanf($cNAME,"#%02x%02x%02x");
	$this->SetTextColor($r,$g,$b);
	$this->SetX($marginL[$this->col]);
	$this->Cell(0,6,$text,0,1,'L');
}
}
//start a new PDF
$pdf = new PDF('L','mm',$pSize);
if ($ttf) { 
	$pdf->AddFont('DejaVu','','DejaVuSansCondensed.ttf',true);
	$pdf->AddFont('DejaVu','B','DejaVuSansCondensed-Bold.ttf',true);
	$pdf->AddFont('DejaVu','I','DejaVuSansCondensed-Oblique.ttf',true);
	$pdf->AddFont('DejaVu','BI','DejaVuSansCondensed-BoldOblique.ttf',true);
}
?>
