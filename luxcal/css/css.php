<?php
/*
= LuxCal style sheet =
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
*/

header('content-type:text/css');

/* ---- LOAD USER-INTERFACE THEME DEFINITIONS ---- */

//get calendar in use
if (empty($_COOKIE['LXCcid'])) { exit; }
$calID = unserialize($_COOKIE['LXCcid']);

//start session
$calPath = rtrim(substr(dirname($_SERVER["PHP_SELF"]),0,-4),'/').'/';
session_set_cookie_params(1800,$calPath); //set cookie path
session_name('PHPSESSID');
session_start();
if (!empty($_SESSION[$calID]['theme'])) { //theme file specified
	$theme = $_SESSION[$calID]['theme'];
	require "./{$theme}";
} else { //no theme specified, take theme from db
	chdir('../'); //change working directory
	require 'common/toolboxd.php'; //get database tools + LCV
	require 'lcconfig.php'; //get db credentials
	$dbH = dbConnect($calID); //connect to db
	$stH = dbQuery("SELECT `name`,`value` FROM `styles`");
	$th = [];
	while (list($name,$value) = $stH->fetch(PDO::FETCH_NUM)) {
		$th[$name] = $value;
	}
	$theme = 'db theme';
}

//preprocessing
$thHt = $th['PSXXX'] + 6; //height table headers
$buttonHt = intval(($th['MBUTS'] * $th['PSXXX']) + 8); //height buttons
$tInputHt = intval(($th['MFFLD'] * $th['PSXXX']) + 4); //height buttons
$selectHt = intval(($th['MFFLD'] * $th['PSXXX']) + 6); //height buttons
$sBoxTp = $thHt + 8; //month/week/day view scrollbox top
$topBar = $th['PTBAR'] + 12; //offset topbar bottom
$navBar = $topBar + $buttonHt + 6 + $th['sCtOf']; //offset navbar bottom
$offCal = $navBar + 2 + $th['sCtOf']; //offset calendar
$offUpc = $navBar; //offset side bar Upcoming
$offTod = $navBar + 20; //offset side bar Todo
$offToa = $navBar + 40; //offset side bar To approve

//serve styles
echo
"/*theme: {$theme}*/
"
.// ---- general: site ----- cursor:default;
"
* {padding:0; margin:0;}
body, select, th, td {font:{$th['PSXXX']}px {$th['FFXXX']};}
pre {display:inline;}
a, input, label, select {cursor:pointer;}
textarea {resize:vertical;}
input[type='text'], input[type='number'], input[type='password'], textarea {font-family:inherit; font-size:{$th['MFFLD']}em; padding:0 2px; color:{$th['CFFLD']}; background:{$th['BFFLD']}; border-radius:2px; border:1px solid #666; cursor:text;}
input:focus, textarea:focus {outline:none; box-shadow:0 0 0 1px #0000F0;}
input[type='text'], input[type='number'], input[type='password'] {height:{$tInputHt}px; margin-right:3px;}
button {font-size:{$th['MBUTS']}em; height:{$buttonHt}px; padding:0px 2px; color:{$th['CBUTS']}; background:{$th['BBUTS']}; border-radius:2px; border:1px solid #666; cursor:pointer;}
input[type='radio'], input[type='checkbox'] {vertical-align:middle; margin-right:3px;}
input[type='file'] {font-size:{$th['MBUTS']}em; border-color:#666; color:{$th['CBUTS']}; background:{$th['BBUTS']};}
input[type='file']:hover, button:hover {border-color:{$th['EBUTS']};}
select {padding:0 2px; font-size:{$th['MFFLD']}em; height:{$selectHt}px; color:{$th['CDROP']}; background:{$th['BDROP']}; border-radius:2px; border:1px solid #666;}
select option {padding:0 2px;}
body {background:{$th['BXXXX']}; color:{$th['CXXXX']};}
table {border-collapse:collapse;}
th {height:{$thHt}px; color:{$th['CBHAR']}; background:{$th['BBHAR']}; cursor:default;}
td {vertical-align:top;}
dt {font-weight:bold;}
dd {margin:0 0 0 25px;}
a {color:{$th['CXXXX']}; text-decoration:none;}
a:hover {text-shadow:0.2em 0.3em 0.2em #F88;}
a.urlembed {font-weight:bold; text-decoration:underline;}
hr {margin:10px 0px; border:1px solid {$th['BBHAR']};}
p {text-align:justify;}
img {border-style:none;}
mark {color:{$th['BHLIT']}; font-weight:bold; text-decoration:underline;}
[onClick] {cursor:pointer;}

h1 {font:bold {$th['PTBAR']}px {$th['FFXXX']}; padding:4px 0px;".($th['sTbSw'] ? ' text-shadow:0.2em 0.3em 0.2em #888;' : '')." text-align:center;}
h2 {font:bold {$th['PPGTL']}px {$th['FFXXX']};}
h3 {font:bold {$th['PTHDL']}px {$th['FFXXX']};}
h4 {font:bold {$th['MTHDM']}em {$th['FFXXX']};}
h5 {font:bold {$th['MDTHD']}em {$th['FFXXX']};}
h6 {font:bold {$th['MSNHD']}em {$th['FFXXX']};}

ul, ol {margin:0 25px;}
li {margin:4px 0;}

.fontS {font-size:{$th['MSMAL']}em;}
.bold {font-weight:bold;}

.floatR {float:right;}
.floatL {float:left;}
.floatC {text-align:center;}
.center {display:block; margin:auto;}
.inline {display:inline;}
.clear {clear:both;}
.optBut {font-weight:bold; margin-right:10px;}
.sup {font-size:1.4em; line-height:80%; color:red; display:inline-block; width:1.2rem;}

.navLink {cursor:pointer;}
.link {text-decoration:underline; color:{$th['CLINK']}; background:{$th['BLINK']};}
.butLink {border:none; color:{$th['CLINK']}; background:none; cursor:pointer; text-decoration:underline;}
.navLink:hover, .butLink:hover {text-shadow:0.2em 0.3em 0.2em #F88;}
.point {cursor:pointer;}
.arrow {cursor:default;}
.move {cursor:move;}
.hyper:hover {cursor:pointer; background:{$th['BGCTH']}; overflow:hidden;}
.select:hover {cursor:pointer; background:red;}
.pageTitle {margin:0 0 20px 5%;}
.borderB {border-bottom:2px solid {$th['BBHAR']};}
.confirm {margin:auto; width:70%; text-align:center; color:{$th['CCONF']}; background:{$th['BCONF']};}
.warning {margin:auto; width:70%; text-align:center; color:{$th['CWARN']}; background:{$th['BWARN']};}
.error {margin:auto; width:70%; text-align:center; color:{$th['CERRO']}; background:{$th['BERRO']};}
.inputWarning {background:{$th['BWARN']} !important;}
.inputError {background:{$th['BERRO']} !important;}
.green {color:#00B000;}
.red {color:#B00000;}
.hired {color:#FF0000; font-weight:bold;}
.info {font-size:1.2em; font-weight:bold; color:#B00000; cursor:pointer;}
.hide, .hpot {display:none;}
.hidden {visibility:hidden;}
.noWrap {white-space:nowrap;}
.alert {position:relative; top:15%; text-align:center;}
.alert span {display:inline-block; padding:30px 60px; font-size:1.2em; background:white; border:1px solid red; border-radius:5px; box-shadow:5px 5px 5px #888;}
.bar {padding:0 20px;}
.scrAuto {overflow:auto;}
"
.// ---- common ----
"
img.logo {position:absolute; left:8px; top:5px; max-width:70px; max-height:70px; z-index:20;}
img.logoXL {display:block; margin:40px auto 0; max-width:80vw;}
div.xPadXL {padding:0 80px;}
div.xPadXS {padding:0 10px;}
div.lPadXL {padding:0 10px 0 80px;}
div.topBar {position:relative; line-height:20px; color:{$th['CTBAR']}; background:{$th['BTBAR']};}
span.barLS {position:absolute; top:4px; left:10px;}
span.barLL {position:absolute; top:4px; left:80px;}
span.barRS {position:absolute; top:4px; right:30px;}
span.barRL {position:absolute; top:4px; right:80px;}
div.navBar {position:absolute; left:0; top:{$topBar}px; right:0; line-height:20px; color:{$th['CBHAR']}; background:{$th['BBHAR']}; border:1px solid {$th['EXXXX']}; border-style:solid none;}
span.emoButton {font-size:1.2em; cursor:pointer;}
div.content {position:absolute; left:0; top:{$offCal}px; right:0; bottom:20px;}
div.contentN {position:absolute; left:0; top:0; right:0; bottom:30px;}
div.contentE {padding:0 4px; font-size:{$th['MPWIN']}em;}
div.contentH {margin-bottom:10px; padding:3px 10px; font-size:{$th['MPWIN']}em; color:{$th['CXWIN']}; background:{$th['BXWIN']};}
footer {position:absolute; left:0; right:0; bottom:0px; height:14px; padding:2px 10px; font-size:0.8em; color:{$th['CBHAR']}; background:{$th['BBHAR']}; border:1px solid {$th['EXXXX']}; border-style:solid none; text-align:center;}
footer a {font:1.1em arial,sans-serif; color:{$th['CBHAR']}; float:right;}
.footLS {font-style:italic; font-weight:bold}
.hitCnt {margin-right:12px;}
div#calList {position:absolute; top:{$topBar}px; left:0; right:0; width:220px; display:none; z-index:30;}
div#calList div {margin:8px 0;}
div#toapBar, div#todoBar, div#upcoBar {position:absolute; height:60%; width:200px; padding:4px; border:2px solid {$th['EXXXX']}; border-radius:5px; box-shadow:5px 5px 5px #888; font-size:{$th['MOVBX']}em; color:{$th['COVBX']}; background:{$th['BOVBX']}; overflow:hidden; display:none;}
div.toapBar {top:{$offToa}px; right:60px; z-index:22;}
div.todoBar {top:{$offTod}px; right:40px; z-index:21;}
div.upcoBar {top:{$offUpc}px; right:20px; z-index:20;}
div.barTop {margin-bottom:8px; padding:0 10px; line-height:20px; font-weight:bold; user-select:none; color:{$th['CBHAR']}; background:{$th['BBHAR']};}
div.barBody {position:absolute; top:60px; bottom:0px; width:96%; overflow:auto;}
div.menu {visibility:hidden; border:1px solid {$th['EXXXX']}; border-radius:5px; box-shadow:5px 5px 5px #888; font-size:{$th['MOVBX']}em; color:{$th['COVBX']}; background:{$th['BOVBX']}; z-index:100; overflow:hidden; transition:0.5s;}
div.usrMenuS {position:absolute; top:{$topBar}px; right:30px; height:0; padding:0 4px;}
div.usrMenuL {position:absolute; top:{$topBar}px; right:80px; height:0; padding:0 4px;}
div.sideMenu {position:absolute; top:{$navBar}px; right:4px; width:0; padding:4px 0;}
div.optMenu {position:absolute; top:{$navBar}px; left:4px; height:0; padding:0 4px;}
div.option {float:left; margin:0 2px;}
div.optHead {margin:4px 0; color:{$th['CBHAR']}; background:{$th['BBHAR']};}
div.optList {max-height:206px; overflow-y:scroll; scrollbar-width:thin;}
div.smGroup {margin:4px 0; border-top:1px solid #D0D0D0;}
div.smGroup p, div.umGroup p {padding:1px 4px; cursor:pointer; white-space:nowrap; transition:0.3s;}
div.smGroup p:hover, div.umGroup p:hover {background:#E0E0E0;}
.closeX {position:absolute; top:4px; right:4px; cursor:pointer;}
.closeXr {position:sticky; top:-10px; float:right; margin:-10px; cursor:pointer;}
"
.// ---- all pages -----
"
input.date {width:5.5em;}
input.time {width:4.0em;}

.dtPick {cursor:pointer; font-size:14px;}
div.scrollBox {position:absolute; left:0; right:0; bottom:0; overflow:auto;}
div.sBoxYe, div.sBoxMo, div.sBoxWe, div.sBoxDa, div.sBoxMx {top:{$sBoxTp}px;}
div.sBoxUp, div.sBoxCh, div.sBoxLg {top:85px;}

@media screen and (max-width:600px) {
	div.sBoxAd, aside.sBoxAd {margin-top:20px;}
}
@media screen and (min-width:601px) {
	div.sBoxAd, aside.sBoxAd {margin-top:90px;}
}
div.sBoxSe {position:absolute; top:100px; left:0; right:0; width:fit-content;  margin:0 auto;;  height:calc(100% - 100px); overflow:auto;}div.sBoxTs, aside.sBoxTs {margin-top:125px;}
div.sBoxTe {margin-top:50px;}
aside.sBoxTe {margin-top:135px;}
div.sBoxSt {margin-top:15px;}
div.sBoxTn, aside.sBoxTn {margin-top:50px;}
div.calHeadMx {margin-left:185px; text-align:center;}
div.rowBoxMx {margin-left:5px; width:180px;}
div.calBoxMx {position:absolute; left:185px; top:0; right:5px; overflow-x:scroll;}
div.rowBoxGt {margin-left:5px; width:360px;}
div.calBoxGt {position:absolute; left:365px; top:0; right:5px; overflow-x:scroll;}

.dialogBox {display:table; margin:0 auto; font-size:{$th['MPOPU']}em; background:{$th['BHNOR']}; padding:18px 24px; border:1px solid {$th['EHNOR']}; border-radius:5px; box-shadow:5px 5px 5px #888;}
.centerBox {display:table; margin:0 auto;}

fieldset.logIn {padding:20px 30px;}
fieldset.logIn span.icon {font-size:20px; margin-right:12px;}
fieldset.logIn div.input {margin:20px 0;}
fieldset.logIn div.input input {width:200px;}
span.eye {margin-left:-28px; font-size:1.4em;}

fieldset.contact {padding:20px; margin-bottom:10px; width:550px; max-width:90vw;}
fieldset.contact input {margin-top:10px;}
span.msgCol1 {display:inline-block; min-width:9em;}
textarea.message {margin-top:4px; width:98%;}

table.grid {width:100%; table-layout:fixed;}
table.grid thead {z-index:10;}
table.grid thead::after, thead::before {content:''; position:absolute; left:0; width:100%; border-top:1px solid {$th['EXXXX']};}
table.grid thead {position:sticky; top:0px;}
table.grid thead th {background-clip:padding-box;}\n".//Firefox bug
"table.grid .wkCol {width:25px;}
table.grid .tCol {width:50px;}
table.grid .dCol7 {width:14%;}
table.grid .tColBg {background:{$th['BGWTC']};}
table.grid tr.monthWeek {height:120px;}
table.grid tr.yearWeek {height:40px;}
table.grid th {border:1px solid {$th['EXXXX']}; overflow:hidden;}
table.grid th.smallHt {height:14px;}
table.grid td {border:1px solid {$th['EXXXX']}; overflow:hidden;}
table.grid td.wnr {border:none; vertical-align:middle; text-align:center; background:{$th['BGWTC']};}
table.grid td.mBox{border:none; text-align:center; padding:4px;}

div.matrix {overflow-x:scroll; margin-left:185px; width:calc(100% - 185px);}
table.matrix {width:100%; table-layout:fixed;}
table.matrix .col0 {position:absolute; left:0; width:180px; overflow:hidden;}
table.matrix th.col0 {width:185px; border-right:1px solid {$th['EXXXX']};}
table.matrix th {width:56px; height:20px;}
table.matrix th.month {padding-left:4px; text-align:left;}
table.matrix td.col0 {margin-top:-1px;}
table.matrix td {height:38px; border:1px solid {$th['EXXXX']}; padding:2px; overflow:hidden;}

div.gantt {overflow-x:scroll; margin-left:373px; width:calc(100% - 373px);}
table.gantt {width:100%; table-layout:fixed;}
table.gantt .col0, table.gantt .col1, table.gantt .col2 {position:absolute; padding:0 5px; overflow:hidden; border-right:1px solid {$th['EXXXX']};}
table.gantt .col0 {left:0; width:210px;}
table.gantt .col1 {left:221px; width:70px;}
table.gantt .col2 {left:302px; width:60px;}
table.gantt th {width:56px; height:20px;}
table.gantt th.month {padding-left:4px; text-align:left;}
table.gantt td.col0, table.gantt td.col1, table.gantt td.col2 {margin-top:-1px;}
table.gantt td {height:24px; border:1px solid {$th['EXXXX']}; white-space:nowrap;}
table.gantt td.msg {height:100px; border:none; white-space:nowrap;}

table td.we0 {color:{$th['CGWE2']}; background:{$th['BGWE2']};}
table td.we1 {color:{$th['CGWE1']}; background:{$th['BGWE1']};}
table td.wd0 {color:{$th['CGWD2']}; background:{$th['BGWD2']};}
table td.wd1 {color:{$th['CGWD1']}; background:{$th['BGWD1']};}
table td.out {color:{$th['CGOUT']}; background:{$th['BGOUT']};}
table td.blank {border:none; background:rgba(0,0,0,0);}
table td.today {border:1px solid {$th['EGTOD']}; color:{$th['CGTOD']}; background:{$th['BGTOD']};}
table td.slday {border:1px solid {$th['EGSEL']}; color:{$th['CGSEL']}; background:{$th['BGSEL']};}

table.contact td {padding:4px 10px; vertical-align:top;}

table.cleanUp td {padding:3px 2px; vertical-align:top;}

div.scrollY {height:100%; overflow:auto;}

fieldset {width:auto; margin-bottom:10px; padding:12px; border:1px solid #888888; background:{$th['BINBX']}; border-radius:5px;}
fieldset.list {max-width:700px; margin:10px auto; padding:10px;}
fieldset.log {max-width:900px; margin:10px auto; padding:10px;}
legend {font-weight:bold; padding:0 5px; background:{$th['BINBX']};}
"
.// -- view: all --
"
span.fullscreen {position:fixed; top:-6px; right:6px; color:#F02030; font-size:2em; cursor:pointer; z-index:1000;}
.viewHdr {display:inline-block; min-width:230px;}
.miniHdr {display:inline-block; min-width:100px;}
.miniBdy {margin-top:3px;}
.arrowLink {font:1.8em/0.8em sans-serif; padding:0 6px; position:relative; top:3px;}
.chkBox {color:{$th['CCHBX']}; background:{$th['BCHBX']}; padding-right:2px;}
.chkBox:hover {background:{$th['BGCTH']};}
div.container {position:absolute; left:0; top:0; right:300px; bottom:0;}
div.sPanel {position:absolute; width:292px; top:0; right:4px; bottom:0; display:flex; flex-flow:column;}
div.spCal {flex:0 1 auto;}
div.spImg {flex:0 1 auto;}
div.spMsg {flex:1 1 auto; padding:8px; overflow-y:auto; background:{$th['BINBX']}; border:1px solid {$th['EXXXX']}; scrollbar-width:thin;}
img.spImage {width:292px; border-bottom:14px solid {$th['BBHAR']};}
"
.// -- about box --
"
.about {position:fixed; top:20vh; left:0; right:0; display:table; margin:0 auto; padding:12px 20px 4px; font-size:1.2em; background:#FFFFFF; border:1px solid #904040; border-radius:5px; box-shadow:5px 5px 5px #888;}
.about h1 {font-size:2.0em; color:#336699}
.about p {text-align:center; margin:12px 0;}
.about a {background:#D0E0F0;}
.about .note {padding:2px 6px; color:#404040; background:#D0F0D0;}
.about .warn {padding:2px 6px; color:#404040; background:#F09090;}
.about button {height:24px; width:60px; border:1px solid #336699; margin-top:12px; font-size:1.0em;}
.about button:hover {border-width:2px;}
"
.// -- view: year/month --
"
.square {float:left; width:8px; height:8px; border:1px solid {$th['EXXXX']};}
.symbol {float:left; position:relative; font-size:10px; line-height:9px;}
.event {margin:2px 2px 0 2px;}
.evtTitle {font-size:{$th['MEVTI']}em;}
.dom1 {padding:0 2px; color:{$th['CGTFD']}; background:{$th['BGTFD']};}
.dom {padding:0 2px; color:{$th['CGTFD']};}
.firstDom {padding:0 2px; color:{$th['CGTFD']}; background:{$th['BGTFD']};}
.wnr {color:{$th['CGWTC']};}
.thNail {max-width:100%;}
.cell {min-height:100px;}
.scrollCell {height:100px; overflow:auto; scrollbar-width:thin;}
"
.// -- view: week / day / vfunctions --
"
.day ul {margin:5px; padding:0px 15px;}
.timeFrame {position:relative;}
.tSlot, .times {border:1px solid {$th['EXXXX']}; border-style:none none solid none;}
.times {text-align:center; color:{$th['CGWTC']};}
.dates {position:absolute; left:0px; top:0px; width:100%;}
.evtBox {position:absolute; border:1px solid {$th['EXXXX']}; z-index:1; overflow:hidden; border-radius:5px; box-shadow:10px 10px 25px grey;}
.dwEvent {padding:2px 0 0 3px;}
"
.// -- view: upcoming / changes / search / vfunctions --
"
div.subHead {margin:10px 5% 0px 5%}
col.col1 {width:120px;}
col.col2 {width:70%;}
td.line1 {padding-top:8px;}
td.eBox {padding-left:5px;}
.toAppr {border-left:2px solid #ff0000;}
"
.// -- view: matrix / gantt --
"
.ganttLine {font-weight:bold;}
.ganttBar {display:inline-block; margin:4px 6px 0 0; height:14px; border:1px solid {$th['EXXXX']};}
.diamant {overflow:visible; white-space:nowrap; font-size:16px; line-height:20px; margin-right:6px;}
"
.// -- event window --
"
div.evtCanvas {padding:2px; color:{$th['CXWIN']}; background:{$th['BXWIN']}; cursor:default;}
table.evtForm {width:100%;}
table.evtForm td {padding:2px;}
table.evtForm td:nth-child(1) {width:100px;}
table.evtForm td:nth-child(3) {width:100px;}
div.apdBar {text-align:center; margin:4px 0; font-weight:bold;}
div.evtExt {margin:4px 0; font-size:1.6em; border-bottom:2px solid {$th['BBHAR']}; cursor:pointer;}
fieldset.repBox {position:absolute; top:50px; left:50%; transform:translate(-50%,0); padding:5px 10px; white-space:nowrap; font-size:{$th['MOVBX']}em; color:{$th['COVBX']}; background:{$th['BOVBX']}; box-shadow:5px 5px 5px #888; z-index:20; display:none;}
div.tbspace {margin:4px 0;}
fieldset.recipBox {position:absolute; bottom:130px; left:50%; transform:translate(-50%,0); max-height:270px; padding:10px; white-space:nowrap; overflow-x:hidden; overflow-y:auto; font-size:{$th['MOVBX']}em; color:{$th['COVBX']}; background:{$th['BOVBX']}; box-shadow:5px 5px 5px #888; z-index:20; display:none;}
div.ewButtons {margin:6px 0;}
div.repetition {margin:12px 0;}
div.repetition div {line-height:20px;}
input.reason {width:300px;}
.marT4 {margin-top:4px;}
"
.// ---- thumbnails page ----
"
div.tnBox {position:relative; float:left; width:100px; height:120px; margin:6px; background:{$th['BINBX']};}
div.tnBox div {position:absolute; top:0; right:0; bottom:0; left:0; cursor:pointer;}
div.tnBox input {width:1px; opacity:0; pointer-events:none;}
div.tnBox span {position:absolute; top:0; left:0; font-size:0.8em;}
div.tnBox span:hover {cursor:pointer; background:red;}
div.tnBox img {position:absolute; top:0; left:15px; max-width:80px; max-height:80px;}
div.tnBox p {position:absolute; left:0px; bottom:0px; width:95%; font-size:0.8em; text-align:center;}
div.tnNote {margin:30px 0; padding:10px 0; text-align:center; background:#FD7; border:1px solid #888888;}

"
.// ---- admin pages -----
"
table.dbContent td {padding:2px 4px;}
table.list {border-collapse:separate; border-spacing:4px; white-space:nowrap;}
table.catList td {text-align:center;}
table.catList td:nth-child(3) {text-align:left;}
td.takeRest {width:100%;}
.pTitleAdm {margin-left:40px; font-weight:bold; font-size:{$th['PPGTL']}px;}
.stylesL {display:inline-block; float:left; cursor:default; vertical-align:top;}
.stylesR {display:inline-block; float:right; cursor:default; vertical-align:top;}
.style {margin:6px 12px;}
fieldset.setting div {cursor:default; margin-bottom:2px; display:flex; align-items:center;}
fieldset.setting div span {width:320px; text-align:right; margin-right:6px;}
.label {cursor:default; text-align:right; padding:0 6px 0 0;}
.cupList {width:45vw; max-width:500px; height:250px; padding:0 0 10px 0; overflow-y:auto;}
.aside {width:45vw; margin:0 4% 10px 0; padding:8px; border:1px solid {$th['EXXXX']}; border-radius:5px; box-shadow:5px 5px 5px #888; font-size:{$th['MOVBX']}em; color:{$th['COVBX']}; background:{$th['BOVBX']}; float:right;}
.butHead {margin:20px auto 10px auto;}
.log div {margin:10px 2px 2px 0;}
.sentDT {font-weight:bold; border:1px solid {$th['EXXXX']};}
.log p {margin-left:130px; text-indent:-20px; text-align:left;}
"
.// ---- Popup Styles (toolbox.js poptext) ----
"
div#pdfPop, div#pdfPopBc {position:absolute; top:20%; left:0; right:0; width:320px; display:none; z-index:30;}
div#htmlPop {position:absolute; font-size:{$th['MPOPU']}em ; padding:4px; border-radius:5px; box-shadow:5px 5px 5px #888; visibility:hidden; z-index:10;}
div#htmlPop img {max-width:200px; max-height:200px;}
.normal, .private, .repeat {overflow:auto; cursor:default;}
.normal {border:1px solid {$th['EHNOR']}; color:{$th['CHNOR']}; background:{$th['BHNOR']};}
.private {border:1px solid {$th['EHPRI']}; color:{$th['CHPRI']}; background:{$th['BHPRI']};}
.repeat {border:1px solid {$th['EHREP']}; color:{$th['CHREP']}; background:{$th['BHREP']};}
"
.// ---- Date Picker Styles -----
"
.dPicker {width:150px; text-align:center; color:#505050; background:{$th['BINBX']}; border:1px solid #D0D0D0; border-radius:5px; box-shadow:5px 5px 5px #888;}
.dPicker th {font-size:10px; font-weight:bold; background:{$th['BBHAR']}; color:{$th['CBHAR']};}
.dPicker td {width:20px; font:10px/11px arial; border:1px solid {$th['BINBX']};}
.dPicker td.dpTitle {font:bold 11px/12px arial; color:{$th['CXXXX']};}
.dPicker td.dpTDHover {border:1px solid #888888; cursor:pointer; color:red;}
div.dpHilight {border:1px solid #888888; color:red; font-weight:bold;}
.dpArrow {padding:0 2px; cursor:pointer;}
.dpButton {font-size:9px;}
"
.// ---- Time Picker Styles -----
"
.tpFrame {max-height:180px; width:165px; overflow:auto; font:10px/11px courier,monospace; text-align:center; color:#505050; border:1px solid #AAAAAA; border-radius:5px; box-shadow:5px 5px 5px #888;}
.tpAM {background:#EEFFFF;}
.tpPM {background:#FFCCEE;}
.tpEM {background:#DDFFDD;}
.tpPick:hover {background:#A0A0A0; color:red; cursor:pointer;}
"
?>
