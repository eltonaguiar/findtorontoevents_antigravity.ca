<?php
/* LuxCal PDF Print Upcoming Events - Landscape class
Copyright 2009-2025 LuxSoft www.LuxSoft.eu
-------------------------------------------------------------------
This file is part of the LuxCal Calendar and is distributed WITHOUT 
ANY WARRANTY. See the GNU General Public License for details.
*/
$pWidth = (strtolower($pSize) === 'letter') ? 279.4 : 297; //Letter or A4
$marginL = [10, $pWidth / 2 + 10];
$marginR = [$pWidth / 2 + 10, 10];
$ttf = extension_loaded('mbstring') ? 't' : ''; //unicode or cp1252
$font = $ttf ? 'DejaVu' : 'Helvetica';
$encoding = 'cp1252//TRANSLIT'; //if no unicode

require("./pdfs/{$ttf}fpdf.php");

class PDF extends FPDF 
{
protected $B = 0;
protected $I = 0;
protected $U = 0;
protected $HREF = '';
protected $col = 0; //current column
protected $body = 0; //body being printed
protected $pageNr = 1; //page number

function csConv($text) {
	global $ttf, $encoding;
	
	return $ttf ? $text : iconv('UTF-8',$encoding,$text);
}

function Header() { //page header
	global $font, $pWidth, $logo, $marginL, $marginR, $link, $title, $cHEAD, $bHEAD;

	$title = $this->csConv($title);
	$logo = ltrim($logo,"/\\");
	$this->SetFont($font,'B',12);
	list($r,$g,$b) = sscanf($cHEAD,"#%02x%02x%02x");
	$this->SetTextColor($r,$g,$b);
	list($r,$g,$b) = sscanf($bHEAD,"#%02x%02x%02x");
	$this->SetFillColor($r,$g,$b);
	$w = $this->GetStringWidth($title)+4;
	$offset = 0;
	if (!empty($logo)) {
		$this->Image($logo,$marginL[0],6,14,0,'',$link);
		$this->Image($logo,$marginL[1],6,14,0,'',$link);
		$offset = 7;
	}
	$titleX = ($pWidth / 2 - $w) / 2 + $offset;
	$this->SetX($titleX);
	$this->Cell($w,6,$title,0,0,'C',true,$link);
	$this->SetX($titleX + $pWidth / 2);
	$this->Cell($w,6,$title,0,0,'C',true,$link);
	$this->SetY(30);
	$this->SetLeftMargin($marginL[0] + $this->body * 35);
	$this->SetRightMargin($marginR[0]);
	$this->SetAutoPageBreak(true,16);
}

function Footer() { //page footer
	global $font, $pWidth, $marginL, $marginR, $footer;

	$this->SetFont($font,'I',6);
	$this->SetTextColor(128);
	$this->SetY(-10);
	foreach([0,1] as $colNr) {
		$ftrText = str_replace('#',$this->pageNr++, $footer);
		$ftrText = $this->csConv($ftrText);
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

	$this->SetY(30);
	if($this->col < 1) { //go to column 2
		$this->col = 1;
		$this->SetLeftMargin($marginL[1] + $this->body * 35); //set abscissa to left of column 2
		$this->SetRightMargin($marginR[1]);
		$this->Ln(0);
		return false; //keep on page
	} else { //go back to column 1
		$this->col = 0;
		$this->SetLeftMargin($marginL[0] + $this->body * 35); //set abscissa to left of column 1
		$this->SetRightMargin($marginR[0]);
		$this->Ln(0);
		return true; //page break
	}
}

function writeHTML($html) { //HTML parser
	$html = str_replace("\n",' ',$html);
	$a = preg_split('/<(.*)>/U',$html,-1,PREG_SPLIT_DELIM_CAPTURE);
	foreach($a as $i=>$e) {
		if ($i%2 == 0) { //text
			if ($this->HREF)
				$this->PutLink($this->HREF,$e);
			else
				$this->Write(5,$e);
		} else { //tag
			if($e[0] == '/') {
				$this->CloseTag(strtoupper(substr($e,1)));
			} else { //extract attributes
				$a2 = explode(' ',$e);
				$tag = strtoupper(array_shift($a2));
				$attr = [];
				foreach($a2 as $v) {
					if(preg_match('/([^=]*)=["\']?([^"\']*)/',$v,$a3)) {
						$attr[strtoupper($a3[1])] = $a3[2];
					}
				}
				$this->OpenTag($tag,$attr);
			}
		}
	}
}

function OpenTag($tag, $attr) { //opening tag
	global $marginL;

	if ($tag=='B' || $tag=='I' || $tag=='U')
		$this->SetStyle($tag,true);
	if ($tag=='A')
		$this->HREF = $attr['HREF'];
	if ($tag=='BR')
		$this->Ln(5);
		$this->SetLeftMargin($marginL[$this->col] + 35); //set abscissa to left of column. important
}

function CloseTag($tag) { //closing tag
	if ($tag=='B' || $tag=='I' || $tag=='U')
		$this->SetStyle($tag,false);
	if ($tag=='A')
		$this->HREF = '';
}

function SetStyle($tag, $enable) { //modify style and select corresponding font
	$this->$tag += ($enable ? 1 : -1);
	$style = '';
	foreach(['B', 'I', 'U'] as $s) {
		if ($this->$s > 0)
			$style .= $s;
	}
	$this->SetFont('',$style);
}

function PutLink($URL, $txt) { //put a hyperlink
	$this->SetTextColor(0,0,255);
	$this->SetStyle('U',true);
	$this->Write(5,$txt,$URL);
	$this->SetStyle('U',false);
	$this->SetTextColor(80,80,80);
}

function PrintMonth($monthTitle) { //month title
	global $font, $marginL, $cMOYE, $bMOYE;

	$monthTitle = $this->csConv($monthTitle);
	if ($this->GetY() > 25) { //no nl at the top
		$this->Ln(4);
	}
	$this->SetFont($font,'B',11);
	list($r,$g,$b) = sscanf($cMOYE,"#%02x%02x%02x");
	$this->SetTextColor($r,$g,$b);
	list($r,$g,$b) = sscanf($bMOYE,"#%02x%02x%02x");
	$this->SetFillColor($r,$g,$b);
	$this->SetX($marginL[$this->col]);
	$this->Cell(0,5,$monthTitle,'0',1,'L',true);
}

function PrintDay($wDay) { //week day + day
	global $font, $marginL, $cDATE, $bDATE;

	$wDay = $this->csConv($wDay);
	$this->Ln(1);
	$this->SetFont($font,'B',10);
	list($r,$g,$b) = sscanf($cDATE,"#%02x%02x%02x");
	$this->SetTextColor($r,$g,$b);
	list($r,$g,$b) = sscanf($bDATE,"#%02x%02x%02x");
	$this->SetFillColor($r,$g,$b);
	$w = $this->GetStringWidth($wDay)+2;
	$this->SetX($marginL[$this->col]);
	$this->Cell($w,4,$wDay,0,1,'C',true);
}

function PrintEvent($evtTime,$evtTitle,$evtBody,$hdStyle,$tColor='#505050',$tBgrnd='#FFFFFF') { //event details
	global $font, $marginL;

	$evtTime = $this->csConv($evtTime);
	$evtTitle = $this->csConv($evtTitle);
	$evtBody = $this->csConv($evtBody);
	$this->SetFont($font,'',10);
	$this->SetTextColor(80,80,80);
	$this->SetFillColor(255,255,255);
	$this->SetX($marginL[$this->col]);
	$this->Cell(35,4,$evtTime,0,0,'L');
	list($r,$g,$b) = sscanf($tColor,"#%02x%02x%02x");
	$this->SetTextColor($r,$g,$b);
	list($r,$g,$b) = sscanf($tBgrnd,"#%02x%02x%02x");
	$this->SetFont('',$hdStyle);
	$this->SetFillColor($r,$g,$b);
	$this->SetLeftMargin($marginL[$this->col] + 35);
	$this->SetX($marginL[$this->col] + 35);
	$this->MultiCell(0,4,$evtTitle,0,'L',true);
	$this->SetFont('','');
	if (!empty($evtBody)) {
		$this->SetTextColor(80,80,80);
		$this->body = 1; //start of event body
		$this->writeHTML($evtBody);
		$this->body = 0; //end of event body
		$this->Ln(7);
	}
	$this->SetLeftMargin($marginL[$this->col]);
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
