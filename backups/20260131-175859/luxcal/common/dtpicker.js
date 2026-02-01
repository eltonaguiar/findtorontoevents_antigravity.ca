/* -- Date / Time Picker -- */

'use strict';

//Common functions

function $I(elmId) { return document.getElementById(elmId); }

function createElm(elmId,x,y) {;
	//if not present, create picker element
	if (!$I(elmId)) {
		const elmType = elmId === 'tPicker' ? 'div' : 'table';
		const newNode = document.createElement(elmType);
		newNode.setAttribute("id", elmId);
		newNode.setAttribute("style", "display: none;");
		document.body.appendChild(newNode);
	}
 	//move element to x,y and toggle display
	const pkrElm = $I(elmId);
	pkrElm.className = elmId; 
	pkrElm.style.position = "absolute";
	pkrElm.style.left = x + "px";
	pkrElm.style.top = y + "px";
	pkrElm.style.display = (pkrElm.style.display === "block" ? "none" : "block");
	pkrElm.style.zIndex = 10000;
	return(pkrElm);
}


//Date Picker

let formName, dateFieldId, clearButton;
 
//vars dFormat, tFormat, wStart, dwStartH, dwEndH, dpMonths, dpWkdays, dpClear and dpToday must be defined outside dtpicker.js !

function dPicker(cB,dateForm,dateFieldId1,dateFieldId2) {

	const dateField1 = $I(dateFieldId1);
	const dateField2 = (dateFieldId2) ? $I(dateFieldId2) : "";
	dateFieldId = dateFieldId1;
	formName = dateForm;
	clearButton = cB;

	//compute dpicker coordinates
	const df1Rect = dateField1.getBoundingClientRect();
	const x = df1Rect.right + 22;
	const y = df1Rect.top;
	
	//if not present, create dpTable at x,y and toggle display
	const dpTable = createElm("dPicker",x,y);

	//get working date from dateField 1 or 2
	let dateString;
	let dt;
 
	if (dateField1.value) {
		dateString = dateField1.value;
	} else if (dateField2) {
		dateString = dateField2.value;
	}
	if (dateString) {
		const dtArray = dateString.split(/[^\d]/);
		const posY = dFormat.search("y") / 2;
		const posM = dFormat.search("m") / 2;
		const posD = dFormat.search("d") / 2;
		dt = new Date(parseInt(dtArray[posY],10), parseInt(dtArray[posM],10) - 1, parseInt(dtArray[posD],10));
	}
	if (!dateString || isNaN(dt.getTime())) { //invalid date
		dt = new Date();
	}
	refreshDP(dt.getFullYear(), dt.getMonth(), dt.getDate());
}

function refreshDP(year,month,day) { //display/refresh date picker
	let i;
	let curDate = new Date();
	const today = curDate.getFullYear()+("0"+(curDate.getMonth()+1)).slice(-2)+("0"+curDate.getDate()).slice(-2);
	const TD = `<td onMouseOut='this.className="";' onMouseOver='this.className="dpTDHover";' `; //leave open
	let html = `<tr>
		<td>${getArrowTag(year,month,-1,"&#9664;")}</td>\n
		<td class='dpTitle' colspan='5'>${dpMonths[month]} ${year}</td>\n
		<td>${getArrowTag(year,month,1,"&#9654;")}</td>\n</tr>\n
		<tr>\n`;
  for (i = wStart; i < wStart+7; i++) { html += `<th>${dpWkdays[i]}</th>\n`; }
	html += `</tr>\n<tr>`;
 	curDate = new Date(year, month, 1);
  for (i = (curDate.getDay() + 6 + (1-wStart)) % 7; i > 0; i--) { html += `<td></td>\n`; }
 	do {
		const dayNum = curDate.getDate();
		const dateString = year + ("0"+(month+1)).slice(-2) + ("0"+dayNum).slice(-2); //yyyymmdd
		const TD_onclick = ` onclick="updateDateField('${dateString}');">`;
		html += TD + TD_onclick + (dayNum === day ? `<div class='dpHilight'>${dayNum}</div>` : dayNum) + `</td>\n`;
    if ((curDate.getDay() + 6 + (1-wStart)) % 7 === 6) html += `</tr>\n<tr>`; //if EndOfWeek, start new row
		curDate.setDate(dayNum + 1); //increment the day
	} while (curDate.getDate() > 1)
  for (i = (curDate.getDay() + 6 + (1-wStart)) % 7; i < 7; i++) { html += `<td class=out></td>\n`; }
	html += `</tr>\n<tr><td colspan='7'>
		<button class='dpButton' onclick="updateDateField('${today}');"> ${dpToday} </button> `;
	if (clearButton != 0) {
		html += `<button class='dpButton' onclick='updateDateField();'> ${dpClear} </button>`;
	}
  html += `</td>\n</tr>\n`;
	const dpTable = $I("dPicker");
 	dpTable.innerHTML = html;
	//last minute y-correction
	const dpRect = dpTable.getBoundingClientRect();
	const dpH = dpRect.height;
	const dpB = dpRect.bottom;
	const winH = window.innerHeight;
	if (dpB > winH) {
		dpTable.style.top = winH - dpH - 15 + "px";
	}
}

function getArrowTag(year,month,offset,label) {
	const newM = (month + 12 + offset) % 12;
	const newY = (Math.abs(newM - month) > 1) ? year + offset : year;
	return `<span class='dpArrow' onclick='refreshDP(${newY},${newM});'>${label}</span>`;
}

function updateDateField(yyyymmdd) {
	const dateField = $I(dateFieldId);
	const dpTable = $I("dPicker");
	if (yyyymmdd) {
		dateField.value = dFormat.replace ("y",yyyymmdd.slice(0,4)).replace ("m",yyyymmdd.slice(4,6)).replace ("d",yyyymmdd.slice(6,8));
		if (formName) document.forms[formName].submit();
	} else {
		dateField.value = '';
	}
	dpTable.style.display = "none";
}


//Time Picker

function tPicker(timeFieldId) {
	const timeField = $I(timeFieldId);
	let hhmm1, hhmm2;

	//compute tpicker coordinates
	const rect = timeField.getBoundingClientRect();
	const x = rect.right + 22;
	const y = 5;

	//if not present, create tPicker, move it to x,y and toggle display
	const tpDiv = createElm("tPicker",x,y);

 	//draw the tpicker table; the timeField object will receive the time
	let html=`<div class="tpFrame">`;
	const apm = /\s?a$/i.exec(tFormat);
	let am, pm;
	if (apm !== null) {
		am = apm[0].replace("a","am").replace("A","AM"); 
		pm = apm[0].replace("a","pm").replace("A","PM"); 
	}
	if (apm) { html += '- '+am+' -'; }
	for (let i = dwStartH; i <= Math.min(dwEndH,23); i++) {
		if (i === dwStartH) { html += `<div class="tpAM">`; }
		if (i === 12 && apm) { html += `- ${pm} -`; }
		if (i === 12) { html += `<div class="tpPM">`; }
		if (i === 18) { html += `<div class="tpEM">`; }
		for (let j = 0; j < 60; j += 15) {
			if (apm) {
				let hh = i;
				const ampm = (hh < 12) ? am : pm;
				if (hh >= 13) { hh -= 12; }
				if (hh === 0) { hh = 12; } //midnight: 12:00am (not: 0:00am)
				hhmm1 = hh + ":" + ("0"+j).slice(-2) + ampm;
				hhmm2 = ("0"+hh).slice(-2) + ":" + ("0"+j).slice(-2);
			} else {
				hhmm1 = hhmm2 = ("0"+i).slice(-2) + ":" + ("0"+j).slice(-2)
			}
			html += `<span class='tpPick' onclick="updateTimeField('${timeFieldId}', '${hhmm1}');">${hhmm2}</span>`;
			if (j<45) { html += ' '; }
		}
		html += (i === 11 || i === 17 || i === 23) ? '</div>' : '<br>';
	}
	html += '</div>';
	tpDiv.innerHTML = html;
}

function updateTimeField(timeFieldId,timeString) {
	const timeField = $I(timeFieldId);
	if (timeString) { timeField.value = timeString.replace(/^0(\d:)/,'$1'); } //trim leading zero
	const tpDiv = $I("tPicker");
	tpDiv.style.display = "none";
	timeField.focus();
}
