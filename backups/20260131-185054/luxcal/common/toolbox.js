/*
= LuxCal JavaScript tools =
Copyright 2009-2025 LuxSoft - www.LuxSoft.eu
*/

'use strict';

//global variables
const winXS = '0';
const hlpWinH = 500, hlpWinW = 800, hlpWinT = 100; //help window height, width, top
const evtWinH = 200, evtWinW = 510, evtWinT = 100; //event window height, width, top
var lastFocus;

//shortcut functions

function $I(id) { return document.getElementById(id); }
function $N(name) { return document.getElementsByName(name); }
function $Q(selector,node = document) { return node.querySelector(selector); }
function $QA(selector,node = document) { return node.querySelectorAll(selector); }

function initCal() {
	if (location != parent.location) { showX('urlButton',false); }
	initLists();
}

const curV = document.currentScript.src.split("?v=")[1].slice(0,6); //get current LuxCal version
function showAbout() { //show about and check version number
	let script = document.createElement('script');
	script.src = `https://www.luxsoft.eu/downloads/!luxcal.php?v=${curV}`;
	document.head.append(script);
}

function aboutLC(luxcal) { //populate and show about LuxCal box
	let aboutBox = $I('about');
	if (!aboutBox) { //about box not yet existing
		aboutBox = document.createElement("div");
		aboutBox.id = 'about';
		aboutBox.className = "about";
		document.body.appendChild(aboutBox);
	}
	let content = `<h1>LuxCal Web Calendar</h1>`;
	content += `<p><b>Version ${curV}</b></p>`;
	content += luxcal.msgV ? `<p>${luxcal.msgV}</p>` : `<p>Check for newer LuxCal version failed. Try again later.</p>`;
	content += `<p><b>LuxCal is a product from the LuxSoft Freeware Factory</b></p>`;
	content += `<p><a href="https://www.luxsoft.eu" target="_blank">www.luxsoft.eu</a>`;
	content += luxcal.msgF ? `&emsp;&emsp;<a href="${luxcal.msgF}" target="_blank">LuxCal forum</a></p>` : `</p>`;
	if (luxcal.msgN) {
		content += `<p><span class='note'>${luxcal.msgN}</span></p>`;
	}
	if (luxcal.msgH) {
		content += `<p><span class='warn'>${luxcal.msgH}</span></p>`;
	}
	content += `<p><button type='button' onclick='$I(\`about\`).remove();'>OK</button></p>`;
	
	aboutBox.innerHTML = content;
}

function initLists() { //initialize (show or hide) list after page reload;
	["toapBar","todoBar","upcoBar"].forEach (function (list) {
		if (sessionStorage.getItem(list) === '1') { $I(list).style.display = "block"; }
	});
}

function help(page,back) { //show user guide, if back, show back button
	const hlpWinL = (screen.width - hlpWinW) / 2;
	const hlpWin = window.open('','hlpWin',`menubar=no,location=no,toolbar=no,height=${hlpWinH},width=${hlpWinW},top=${hlpWinT},left=${hlpWinL},scrollbars=0`);
	const parObj = {xP:39,hP:page};
	if (back) { parObj.bP = back; }
	index(parObj,'hlpWin');
	hlpWin.focus();
}

function fullscreen() {
  if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
  } else {
    if (document.exitFullscreen) {
      document.exitFullscreen();
    }
  }
}

function pwShow($pword) {
	const pwInput = $I($pword);
	pwInput.type = pwInput.type == "password" ? "text" : "password"; 
}

function scrollV(scrObj) { //save/restore V-scroll values to/from local storage
	const elm1 = $Q('.content');
	const elm2 = $Q('.scrollBox');
	if (elm1 !== null) {
		const item = `page${scrObj.cP}`;
		if (scrObj.action === 'save') { //save V-scroll value
			sessionStorage.setItem(item,elm1.scrollTop);
		}	else if (sessionStorage.getItem(item)) { //goto V-scroll value
			elm1.scrollTop = sessionStorage.getItem(item);
		}
	}
	if (elm2 !== null) {
		const item = `sBox${scrObj.cP}`;
		if (scrObj.action === 'save') { //save V-scroll value
			sessionStorage.setItem(item,elm2.scrollTop);
		}	else if (sessionStorage.getItem(item)) { //goto V-scroll value
			elm2.scrollTop = sessionStorage.getItem(item);
		}
	}
}

function newE(date,cid,st,et){ //new event - date, cat ID and times (optional)
	const parObj = {xP:30,action:'add'};
	if (date) { parObj.evD = date; }
	if (cid) { parObj.catID = cid; }
	if (arguments.length > 2) { parObj.evTs = st; parObj.evTe = et; }
	openWin(parObj);
}

function editE(id,date,cal){ //edit event
	const parObj = {xP:30,action:'edi0',eid:id,evD:date};
	if (cal) { parObj.cal1x = cal; } //if defined, use cal; but don't store in session (used by displays)
	openWin(parObj);
}

function showE(id,date,cal){ //show event
	const parObj = {xP:32,eid:id,evD:date};
	if (cal) { parObj.cal1x = cal; } //if defined, use cal; but don't store in session (used by displays)
	openWin(parObj);
}

function newM(date){ //new marking
	const parObj = {xP:31,action:'add',evD:date};
	openWin(parObj);
}

function editM(id,date){ //edit marking
	const parObj = {xP:31,action:'edi0',eid:id,evD:date};
	openWin(parObj);
}

function openWin(parObj,winName){ //open small window
	if (!winName) { winName = 'evtWin'; }
	const evtWinL = (screen.width - evtWinW) / 2;
	const evtWin = window.open('',winName,`menubar=no,location=no,toolbar=no,height=${evtWinH},width=${evtWinW},top=${evtWinT},left=${evtWinL},scrollbars=0`);
	index(parObj,winName);
	if (parObj.xp < 32) { //add/edit window
		evtWin.focus();
	}
}

function winFit() { //resize window height to fit its content
	window.resizeBy(0,document.body.offsetHeight - window.innerHeight + 16); //needed - inner height +16
}

function winNar(limit) { //update "window Xtra Small" cookie
	const v = document.cookie.match('LXCxs=([0|1])');
	const setXS = (!v || v[1] === '0') ? '0' : '1';
	const winXS = (window.innerWidth < limit) ? '1' : '0';
	if (setXS !== winXS) {
		cookie('LXCxs',winXS,14400,'/'); //10 days
		return true; //cookie set
	}
	return false;
}

function cookie(name,value,minutes,path) { //bake cookie
	const d = new Date;
	d.setTime(d.getTime() + 60000 * minutes); //expires in 'minutes' minutes
	const cPath = (path) ? `;path=${path}` : '';
	document.cookie = `${name}=${value};expires=${d.toUTCString()}${cPath}`;
}

function detach(obj,fName) { //detach file from event
	const elm = $I('att');
	elm.value = elm.value.replace(`;${fName}`,'');
	obj.parentNode.innerHTML = '';
}

//await fetch function

async function askServer(fileName,query,data) {
	data.q = query;
	data.calID = calID;
	data.uName = uName ?? '';
	data.cPage = cPage;
	data.tkn = $Q('meta[name="tkn"]').content;
	const response = await fetch(`common/${fileName}.php`, {
		method:'POST',
    mode:"same-origin",
    credentials:"same-origin",
		headers: { 'Content-Type':'application/json' },
		body:encodeURIComponent(JSON.stringify(data)), //encode json data
  });
	if (!response.ok) { alert(`Fetch error: ${response.status}`); return; }
  return await response.json();
}

//async fetch functions

async function checkE(obj,evtID,evtDt) { //toggle the event check mark
	const result = await askServer('toolsaaf','tec',{evtID:evtID, evtDt:evtDt});
	if (result.ok != 'OK') { alert(`Server problem: ${result.ok}`); }
	obj.innerHTML = result.response;
}

function drag(ev) {
  ev.dataTransfer.setData("text",ev.target.id);
}

async function drop(ev,elem) {
  ev.preventDefault();
  const evtId = ev.dataTransfer.getData("text");
	const evtArr = evtId.split('.');
	if (evtArr.length < 4 || evtArr[3] != 0) { elem.appendChild($I(evtId)); } //don't append day markings
  const date1 = new Date(evtArr[2]);
  const date2 = new Date(elem.id.slice(1));
  const secs = (date2.getTime() - date1.getTime()) / 1000; //seconds
	if (secs !== 0) {
		const copy = ev.ctrlKey ? '1' : '0'; //copy or edit event
		const result = await askServer('toolsaaf','dnd',{evtID:evtArr[1], seconds:secs, copy:copy});
		if (result.ok != 'OK') { alert(`Server problem: ${result.ok}`); }
		location = location.href; //reload the page
	}
}

function dropCopy(ev) {
  ev.preventDefault();
  const evtId = ev.dataTransfer.getData("text");
	const evtArr = evtId.split('.');
	const calList = $I('calList');
	const msgLine = $Q('p',calList);
	calList.setAttribute('data-evtid', evtArr[1]); //save ID of event to copy
	calList.style.display = 'block'; //show calendar selection list
	msgLine.innerHTML = "&nbsp;";
	msgLine.style.backgroundColor = '';
}

async function copy2Cals() {
	const calList = $I('calList');
	const evtID = calList.getAttribute('data-evtid');
	const cbChecked = $QA('input[type="checkbox"]:checked',calList);
	const msgLine = $Q('p',calList);
	const calIDs = [];
	cbChecked.forEach(function(elm) {
		calIDs.push(elm.value);
	});
//	alert ('EvtID: ' + evtID + ' - calIDs: ' + calIDs);
	const result = await askServer('toolsaaf','cop',{evtID:evtID, calIDs:calIDs});
	msgLine.innerHTML = result.msg;
	if (result.ok == 'OK') {
		msgLine.style.backgroundColor = '#90F0A0';
	} else {
		msgLine.style.backgroundColor = '#F0A070';
	}
}

//general functions

function index(parObj,target) { //dummy form to turn GET into POST
	const form = document.createElement("form");
	form.method = "post";
	form.action = "index.php";
	if (target) {
		form.target = target; //window change
	}
	for(let key in parObj) {
		form.innerHTML += `<input type="hidden" name="${key}" value="${parObj[key]}">`;
	}
	document.body.appendChild(form);
	form.submit();
}

function done(action) { //close window and refresh calendar (action: c = close; r = reload opener)
	if (action.indexOf('r') > -1) { window.opener.location = window.opener.location.href; } //refresh calendar 
	if (action.indexOf('c') > -1) { window.close(); }
}

function styleWin(page) { //styling page (new window)
	const pageObj = new Object();
	pageObj.xP = page;
	const styleWin = window.open('','styleWin',"top=100,left=200,width=1000,height=800");
	index(pageObj,'styleWin');
	styleWin.focus();
}

function check1(boxName,thisBox,submit) { //check 1 of N check boxes and submit options menu
	$N(boxName).forEach (function(value) { value.checked = false; });
	thisBox.checked = true;
	if (submit) {
		$I('optForm').submit();
	}
}

function check1T(boxName,thisBox) { //toggle 1 of N check boxes
	const checked = thisBox.checked;
	$N(boxName).forEach (function(value) { value.checked = false; });
	thisBox.checked = checked ? true : false ;
}

function check0(boxName,boxCopy) { //check box 0 of N check boxes
	let chBoxes = $N(boxName+'[]');
	chBoxes.forEach (function(value) { value.checked = false; });
	chBoxes[0].checked = true;
	if (boxCopy) {
		chBoxes = $N(boxCopy+'[]');
		chBoxes.forEach (function(value) { value.checked = false; });
		chBoxes[0].checked = true;
	}
}

function checkN(boxName) { //check any of N check boxes
	const chBoxes = $N(boxName+'[]');
	let check = false;
	chBoxes.forEach (function(value) { if (value.checked) check = true; });
	chBoxes[0].checked = !check;
}

function checkGvN(boxNameV,boxNameA) { //check any of N group View check boxes
	const chBoxesV = $N(boxNameV+'[]');
	let check = false;
	chBoxesV.forEach (function(value) { if (value.checked) check = true; });
	chBoxesV[0].checked = !check;
	if (check === true) {
		const chBoxesA = $N(boxNameA+'[]');
		chBoxesA[0].checked = false;
		chBoxesV.forEach (function(value,i) { if (!value.checked) chBoxesA[i].checked = false; });
	}
}

function checkGaN(boxNameA,boxNameV) { //check any of N group Add check boxes
	const chBoxesA = $N(boxNameA+'[]');
	let checked = [];
	chBoxesA.forEach (function(value,i) { if (value.checked) checked.push(i); });
	if (checked) {
		chBoxesA[0].checked = false;
		const chBoxesV = $N(boxNameV+'[]');
		if (!chBoxesV[0].checked) {
			for (let i of checked) { chBoxesV[i].checked = true; };
		}
	}
}

function checkA(boxName) { //toggle all check boxes
	const chBoxes = $N(boxName+'[]');
	let check = !chBoxes[0].checked;
	chBoxes.forEach (function(value) { value.checked = check; });
}

function checkRecip(thisElm,type) { //check recipients in Event window
	let nalArr2, nalArr = $I(`nal`).value.replace(/\s*/,'').split(';'); //sanitized recips array
	
	if (thisElm.checked) { //checked
		if (type == `list`) {
			nalArr.push(`[${thisElm.name}]`);
		} else if (type == `regist`) {
			const xArr = thisElm.name.split(';');
			nalArr.push(xArr[0]); //user name
		} else if (type == `public`) {
			nalArr.push(thisElm.name);
		}
		nal.value = nalArr.join(';');
	} else { //not checked
		if (type == `list`) {
			nalArr2 = nalArr.filter(e => e != `[${thisElm.name}]`);
		} else if (type == `regist`) {
			const xArr = thisElm.name.split(';');
			nalArr2 = nalArr.filter(e => e != xArr[0] && e != xArr[1] && e != xArr[2] && e != xArr[3]);
		} else if (type == `public`) {
			nalArr2 = nalArr.filter(e => e != thisElm.name);
		}
		nal.value = nalArr2.join(';');
	}
}

function toggleLabel(optBut,text1,text2) {
	const elm = $I(optBut);
	elm.innerHTML = (elm.innerHTML === text1) ? text2 : text1;
}

function showX(elmID,on) { //show or hide element
	const elm = $I(elmID);
	if (elm) { elm.style.display = (on ? "block" : "none"); }
}

function toggleX(elmID) { //show or hide element
	const elm = $I(elmID);
	if (elm) {
		elm.style.display = (elm.style.display == '' ? 'block' : '');
	}
}

function showL(list,on) { //show or hide list;
	$I(list).style.display = (on ? "block" : "none");
	sessionStorage.setItem(list,on);
}

function ewShow(evtExt) { //show or hide event window extension
	const elm = $I(evtExt);
	const none = (elm.style.display === "none");
	elm.style.display = none ? "block" : "none";
	$I(evtExt + 'S').innerHTML = none ? '&#9650;' : '&#9660;';
	document.forms['event'].elements[evtExt].value = none ? '1' : '0';
	winFit();
}

function showUm(elmID) { //user menu
	const elm = $I(elmID);
	elm.style.visibility = (elm.clientHeight > 20) ? 'hidden' : 'visible';
	elm.style.height = (elm.clientHeight > 20) ? '0px' : '40px';
}

function showSm(elmID) { //side menu
	const elm = $I(elmID);
	elm.style.visibility = (elm.clientWidth > 50) ? 'hidden' : 'visible';
	elm.style.width = (elm.clientWidth > 50) ? "0px" : "150px";
}

function showOp(elmID,formName) { //show or hide and submit Options Panel
	const elm = $I(elmID);
	elm.style.visibility = (elm.clientHeight > 150) ? 'hidden' : 'visible';
	elm.style.height = (elm.clientHeight > 150) ? '0px' : '250px';
	if (elm.style.height === "0px") { document.forms[formName].submit(); }
}

function toggleVenue(bBox) { //toggle venue free text / drop-down list
	const ven1 = $I("venue1");
	const ven2 = $I("venue2");
	if (bBox.checked) {
		ven1.style.display = "none";
		ven1.setAttribute("name","");
		ven2.style.display = "inline";
		ven2.setAttribute("name","ven");
	} else {
		ven1.style.display = "inline";
		ven1.setAttribute("name","ven");
		ven2.style.display = "none";
		ven2.setAttribute("name","");
	}
}

function hideTimes(t) { //toggle visibility of event times
	$I("dTimeS").style.visibility = $I("dTimeE").style.visibility = t.checked ? "hidden" : "visible";
	if (t.checked) {
		$I(t.id === 'ald' ? 'ntm' : 'ald').checked = false; //uncheck the other box
	}
}

function delConfirm(item,ID,confText) {
	if (confirm(confText+'?')) {
		switch(item) {
			case 'usr': index({delExe:'y',uid:ID}); break;
			case 'grp': index({delExe:'y',gid:ID}); break;
			case 'cat': index({delExe:'y',cid:ID});
		}
	}
}

function update(jscolor,bgcol,color,bdcol) { //jscolor color changer
	if (bgcol) {
		const bArr = bgcol.split(',');
		bArr.forEach (function(value) { $I(value).style.backgroundColor = `#${jscolor}`; });
	}
	if (color) {
		const cArr = color.split(',');
		cArr.forEach (function(value) { $I(value).style.color = `#${jscolor}`; });
	}
	if (bdcol) {
		const dArr = bdcol.split(',');
		dArr.forEach (function(value) { $I(value).style.borderColor = `#${jscolor}`; });
	}
}

//text editor page

function teTextSubmit(selElm,theText,note) {
	if ($I(theText).dataset.changed === '0' || confirm(note) == true) {
		selElm.form.submit();
	} else {
		selElm.selectedIndex  = selElm.dataset.prevIndex;
	}
}

//thumbnail functions

function toClipboard(elm) {
	$I('s'+elm.id).select(); //select the text field
	document.execCommand('Copy'); //copy the text inside the text field
	let note = document.createElement("div"); //create notification
	note.className = 'tnNote';
	note.innerHTML = tnNote;
	elm.appendChild(note);
	setTimeout(function() { note.parentNode.removeChild(note); },2000); //show 2 seconds
}

function deleteTn(elm,confText) {
	const tnId = elm.id.replace('%20',' ');
	const tnName = tnId.slice(4,5) === '~' ? tnId.slice(5) : tnId;
	if (confirm(`${confText} ${tnName}?`)) {
		index({delTn:tnId});
	}
}

//drag functions
let theElm, posX, posY;

function dragMe(elmID,e) {
	theElm = $I(elmID); //object to drag
	posX = theElm.offsetLeft - e.clientX;
	posY = theElm.offsetTop - e.clientY;
	document.onmousemove=moveMe;
	document.onmouseup=new Function("document.onmouseup = null; document.onmousemove = null;");
}

function moveMe(e) {
	let newPosX = posX + e.clientX;
	let newPosY = posY + e.clientY;
	newPosX = Math.max(newPosX,0);
	newPosX = Math.min(newPosX,window.innerWidth - theElm.offsetWidth)
	theElm.style.left = newPosX + "px";
	newPosY = Math.max(newPosY,0);
	newPosY = Math.min(newPosY,window.innerHeight - 26);
	theElm.style.top = newPosY + "px";
}
//end drag functions

function printNice() {
	const oriHTML = document.body.innerHTML;
	const bgColor = document.body.style.backgroundColor;
	const elms = $QA("*"); //select all elements
	const regexNP = /noPrint/;
	const regexSB = /scrollBox/;

	document.body.style.backgroundColor = "white";
	elms.forEach (function(elm) {
		if (elm.tagName === "BUTTON" || regexNP.test(elm.className)) {
			elm.style.display = "none";
		}
		if (regexSB.test(elm.className)) {
			elm.style.position = "static";
			elm.style.overflow = "visible";
		}
	});
	window.print();
	document.body.innerHTML = oriHTML;
	document.body.style.backgroundColor = bgColor;
}

//drag time functions (week and day view)
let drOn = false, drDate, drTime, drLast, drTSlot;

function dragTime() {
	Array.from($QA(".tSlot")).forEach (function(elm) {
		elm.onmousedown = startDrag;
		elm.onmouseenter = trackDrag;
		elm.onmouseup = stopDrag;
		});
}

function startDrag() {
	drOn = true;
	drDate = this.id.slice(2,12); //date
	drTime = this.id.slice(13,18); //start time
	drTSlot = parseInt(this.parentElement.dataset.slot);
	drLast = this;
	this.style.backgroundColor = "#DDDDDD";
}

function trackDrag() {
	if (drOn && this.id.slice(2,12) === drDate) { //drag On and same day
		if (this.id.slice(13,18) < drLast.id.slice(13,18)) {
			drLast.style.backgroundColor = ''; //back to css color
		} else {
			this.style.backgroundColor = "#DDDDDD";
		}
		drLast = this;
	}
}

function stopDrag() {
	drOn = false;
	if (drLast.id.slice(13,18) >= drTime) {
		const totMins = (drLast.id.slice(13,15) * 60) + parseInt(drLast.id.slice(16,18)) + drTSlot;
		const eHrs = Math.trunc(totMins / 60);
		const eMins = totMins % 60;
		const eTime = `${(`0${eHrs}`).slice(-2)}:${(`0${eMins}`).slice(-2)}`;
		if (drTime == '00:00') { drTime = '00:00'; eTime ="23:59"; } //all day
		newE(drDate,0,drTime,eTime);
	}
	Array.from($QA(".tSlot")).forEach (function(value) { value.style.backgroundColor = ''; }); //back to css color
}

//pop-up div functions

function getPopDiv(divID){
	let popElm = $I(divID);
	if (!popElm) { //element not yet existing
		popElm = document.createElement("div");
		popElm.id = divID;
		document.body.appendChild(popElm);
	}
	return popElm;
}

//==== hover box pop-up function - static ====

function pop(parent,popContent,popClass,maxChars){
	let xOffL, xOffR;
	const popElm = getPopDiv("htmlPop");
	popElm.style.maxWidth = (5 * maxChars) + "px";
	popElm.className = popClass;
	popElm.innerHTML = popContent;

	//compute coordinates
	const evtRect = parent.getBoundingClientRect(); //size and position relative to viewport
	if (evtRect.width < 20) { //mini-squares or symbols
		xOffR = 0;
		xOffL = evtRect.width;
	} else {
		xOffR = xOffL = evtRect.width * (winXS === '1' ? 0.5 : 0.3);
	}

	popElm.style.left = ((evtRect.left + popElm.offsetWidth + xOffR) < (window.innerWidth - 20) ? xOffR : xOffL - popElm.offsetWidth) + evtRect.left + window.scrollX + "px";
	if ((evtRect.bottom + popElm.offsetHeight) < window.innerHeight || evtRect.top < (window.innerHeight / 2)) { //show box under event title
		popElm.style.top = evtRect.bottom + window.scrollY + "px";
	} else { //show box above event title
		popElm.style.top = evtRect.top - popElm.offsetHeight + window.scrollY + "px";
	}
	popElm.style.visibility = "visible";
	popElm.onmouseover = function() { popElm.style.visibility = "visible"; };
	parent.onmouseout = popElm.onmouseout = function() { popElm.style.visibility = "hidden"; };
}

//==== hover box pop-up function - moving ====

function popM(parent,popContent,popClass = 'normal'){
	let offsetX = -60, offsetY = 16; //x, y offset of box
	
	const popElm = getPopDiv("htmlPop");
	popElm.style.maxWidth = "600px"; //max. hover box width
	popElm.className = popClass;
	popElm.innerHTML = popContent;
	popElm.style.visibility = "visible";
	parent.onmousemove = function(e) {
		if (window.innerWidth - 20 - e.pageX - offsetX < popElm.offsetWidth) { //pop hits the right edge
			popElm.style.left = window.innerWidth - 20 - popElm.offsetWidth - 5 + "px"; //don't move it
		} else {
			popElm.style.left = (e.pageX < -offsetX) ? "5px" : e.pageX + offsetX + "px"; //move it with mouse
		}
		if (window.innerHeight - 10 - e.pageY - offsetY < popElm.offsetHeight) { //pop hits the bottom edge
			popElm.style.top = e.pageY - popElm.offsetHeight - (offsetY/2) + "px"; //flip it up
		} else {
			popElm.style.top = e.pageY + offsetY + "px"; //move it with mouse
		}
	};
	parent.onmouseout = function() {
		parent.onmousemove = null;
		popElm.style.visibility = "hidden";
	};
}
