<?php
/* LuxCal PDF Print Birthday Calendar - Portrait class
Copyright 2009-2025 LuxSoft www.LuxSoft.eu
-------------------------------------------------------------------
This file is part of the LuxCal Calendar and is distributed WITHOUT 
ANY WARRANTY. See the GNU General Public License for details.
*/
$pWidth = (strtolower($pSize) === 'letter') ? 215.9 : 210; //Letter (215.9 x 279.4) or A4 (210 x 297)
$marginL = 20;
$marginR = 20;
$ttf = extension_loaded('mbstring') ? 't' : ''; //unicode or cp1252
$font = $ttf ? 'DejaVu' : 'Helvetica';
$encoding = 'cp1252//TRANSLIT'; //if no unicode

require("./pdfs/{$ttf}fpdf.php");

class PDF extends FPDF 
{
function csConv($text) {
	global $ttf, $encoding;
	
	return $ttf ? $text : iconv('UTF-8',$encoding,$text);
}

function Header() { //page header
	global $marginL, $marginR;
	
	$this->SetY(24);
	$this->SetLeftMargin($marginL);
	$this->SetRightMargin($marginR);
	$this->SetAutoPageBreak(true,18);
}

function Footer() { //page footer
	global $font, $marginL, $marginR, $pWidth, $footer;

	$this->SetFont($font,'I',8);
	$this->SetTextColor(128);
	$this->SetY(-10);
	$ftrText = str_replace('#',$this->PageNo(), $footer);
	$ftrText = $this->csConv($ftrText);
	$ftrArr = explode('>',$ftrText);
	if (!empty($ftrArr[0])) {
		$this->Text($marginL,$this->GetY(),$ftrArr[0]);
	}
	if (!empty($ftrArr[1])) {
		$w = $this->GetStringWidth($ftrArr[1]);
		$this->Text(($pWidth - $w) / 2,$this->GetY(),$ftrArr[1]);
	}
	if (!empty($ftrArr[2])) {
		$w = $this->GetStringWidth($ftrArr[2]);
		$this->Text($pWidth - $marginR - $w,$this->GetY(),$ftrArr[2]);
	}
}

function AcceptPageBreak() { //method accepting or not automatic page break
	global $marginL, $marginR;

	$this->SetLeftMargin($marginL);
	$this->SetRightMargin($marginR);
	return true; //page break
}

function NextPage() { //go to next page
	$this->Addpage();
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
		$this->Image($logo,$marginL,18,14,0);
	}
	$strWidth = $this->GetStringWidth($title)+4;
	$this->Text($pWidth - $marginR - $strWidth,30,$title);
	if (!empty($image)) {
		$this->Image($image,$pWidth - $marginR - 40,40,40,0);
		$this->SetY(90);
	} else {
		$this->SetY(24);
	}
	$this->SetX($marginL);
}

function printName($dateName) { //birth date and name of person
	global $font, $marginL, $fNAME, $cNAME;

	$text = $this->csConv($dateName);
	$this->Ln(1);
	$this->SetFont($font,'',$fNAME);
	list($r,$g,$b) = sscanf($cNAME,"#%02x%02x%02x");
	$this->SetTextColor($r,$g,$b);
	$this->SetX($marginL);
	$this->Cell(0,6,$text,0,1,'L');
}
}
//start a new PDF
$pdf = new PDF('P','mm',$pSize);
if ($ttf) { 
	$pdf->AddFont('DejaVu','','DejaVuSansCondensed.ttf',true);
	$pdf->AddFont('DejaVu','B','DejaVuSansCondensed-Bold.ttf',true);
	$pdf->AddFont('DejaVu','I','DejaVuSansCondensed-Oblique.ttf',true);
	$pdf->AddFont('DejaVu','BI','DejaVuSansCondensed-BoldOblique.ttf',true);
}
?>
