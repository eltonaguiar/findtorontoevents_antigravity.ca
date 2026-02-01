<?php
/*
= LuxCal sidebar style sheet =
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
*/

header('content-type:text/css');

//=============================================================//
//DEFINITIONS AFTER THE COMMAS BETWEEN THE QUOTES CAN BE EDITED//
//=============================================================//

//COLORS
define("BGND1","#8D003C"); //background list header
define("BGND2","#FFFCF9"); //background content
define("BGND4","#EEEEEE"); //background dates
define("TEXT1","#F7DA76"); //text color list header
define("TEXT2","#203050"); //text color content
define("TEXT3","#203000"); //text color dates
define("BORD1","2px solid #8D003C"); //list borders
define("POPDT","border:1px solid #808080; color:#8D003C; background:#FFFFE0;"); //hover box normal event
define("POPRT","border:1px solid #E00060; color:#8D003C; background:#FFFFE0;"); //hover box repeating event

//FONT SIZES
define("FONT1","bold 12px arial,sans-serif"); //list header
define("FONT2","11px arial,sans-serif"); //list content
define("FONT3","bold 11px arial,sans-serif"); //dates
define("FONT4","11px arial,sans-serif"); //hover pop-up box

//SHADOWS & BOX CORNERS (0:no 1:yes)
$boxSw = 1; //box shadow
$boxRd = 1; //box corners rounded

//=============================================================//

echo
//============================================================================//
//The default sidebar container style is 'sidebar'. If you have specified your//
//own sidebar classes (see installation_guide.html - $sbClass), add them here //
//(e.g. sidebar1, sidebar2, ....) and tailor these styles to meet your needs. //
//============================================================================//

// ---- Sidebar container style(s) -----
"
div.sideBar {
position: relative; top:10px; right:0px;
float:right;
height:150px; width:160px;
margin:10px 30px 30px 30px;
padding:4px;
background:".BGND2.";
border:".BORD1.";".($boxRd ? ' border-radius:5px;' : '').($boxSw ? ' box-shadow:5px 5px 5px #888;' : '')."
z-index:10;
overflow:hidden;}

div.sideBar2 {
position: relative; top:10px; left:0px;
float:left;
height:400px; width:200px;
margin:10px 30px 30px 30px;
padding:4px;
background:".BGND2.";
border:".BORD1.";".($boxRd ? ' border-radius:5px;' : '').($boxSw ? ' box-shadow:5px 5px 5px #888;' : '')."
z-index:10;
overflow:hidden;}

"
.// ---- Sidebar content styles ----
"
[class^='ssb_'] {padding:0; margin:0;} "./*DON'T TOUCH THIS STYLE!*/"

.ssb_floatL {float:left;}
.ssb_point {cursor:pointer;}
.ssb_arrow {cursor:default;}

div.ssb_header {font:".FONT1."; color:".TEXT1."; background:".BGND1."; padding:0 4px; margin:2px 0 2px 0;}
div.ssb_scrollList {width:100%; height:95%; font:".FONT2."; color:".TEXT2."; overflow:auto;}

div.ssb_date {margin:10px 0 0 0; font:".FONT3."; color:".TEXT3.";background:".BGND4.";}
div.ssb_event {margin:4px 0 0 4px;}
div.ssb_evtTime {font-weight:bold;}
div.ssb_evtTitle {}
div.ssb_chkBox {color:".TEXT2."; background:#FFFFFF; padding-right:2px;}
div.ssb_chkBox:hover {background:".BGND2.";}
div.ssb_evtUrl {margin:0 0 0 4px;}
div.ssb_evtUrl a {text-decoration:underline; cursor:pointer;}
"
.// ---- Hover popup styles (toolbox.js poptext) ----
"
#htmlPop {position:absolute; width:200px; font:".FONT4."; padding:4px; margin:0; overflow:auto; ".($boxRd ? 'border-radius:5px; ' : '').($boxSw ? 'box-shadow:5px 5px 5px #888; ' : '')."visibility:hidden; z-index:100;}
.ssb_normal {".POPDT."}
.ssb_repeat {".POPRT."}
"
?>
