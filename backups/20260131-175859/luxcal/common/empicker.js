const EmojiPicker = function(options) {

	let emojisHTML = '';
	let emoNavHTML = '';
	let emojiList = undefined;
	const pickerPos = `left:calc(50vw - 175px); bottom:0;`; 
	const pickerWidth = 350;
	const pickerHeight = 190;

	this.lib = function(el = undefined) {

		return {

			on(event, callback, cbClass) {
				el.addEventListener(event, (e) => {
					if (e.target.closest(cbClass)) { callback(e) }
				})
			},

			remove() {
				document.querySelector('.emop-container').remove()
			}
		}
	};

	const functions = {

		styles: () => {
			const styles = `
<style>
.emop-container {position:fixed; width:${pickerWidth}px; height:${pickerHeight}px; border-radius:4px; box-shadow:5px 5px 5px #888; background-color:white; overflow:hidden; z-index:100;}

.emop-nav {background-color:#B0B0B0; font-size:14px;}
.emop-nav ul {display:flex; flex-wrap:wrap; list-style:none; margin:0;}
.emop-nav ul li {flex:1; margin:0; padding:4px;}
.emop-nav ul li a {display:flex; justify-content:center; align-items:center; height:14px; transition:all .2s ease;}
.emop-nav-close {background-color:#E03030; font-size:18px;}

.emop-search input {font-size:12px; border:1px solid #D0D0D0; outline:none; box-shadow:none; width:100%; padding:2px 7px; background-color:#E0E0E0;}

.emop-list {list-style:none; margin:0; overflow-y:scroll; overflow-x:hidden; height:calc(${pickerHeight}px - 55px);}
.emop-list-cat {display:flex; flex-wrap:wrap; flex:1;}
.emop-list-cat p {padding:0 8px; font-size:13px; font-weight:bold; flex:100%;}
.emop-list li {display:flex; flex-wrap:wrap; justify-content:center; flex:0 0 calc(100% * 25 / ${pickerWidth});}
.emop-list li a {display:flex; flex-wrap:wrap; justify-content:center; font-size:14px; background-color:#FFFFFF;}
</style>
`;
			document.head.insertAdjacentHTML('beforeend', styles);
		},

		render: e => {
			emojiList = undefined;

			if (document.querySelector('.emop-container')) { //picker shown
				this.lib('.emop-container').remove();
				return;
			}
	
			if (!emojisHTML.length) {
				for (const key in emojiObj) {
					if (Object.hasOwn(emojiObj, key)) {
						const catObj = emojiObj[key];
						emoNavHTML += `<li><a title="${key}" href="#${key}">${catObj[0][0]}</a></li>`;
						emojisHTML += `<div class="emop-list-cat" id="${key}">`;
						emojisHTML += `<p>${key}</p>`;
						catObj.forEach(emo => {
							emojisHTML += `<li data-title="${emo[1].toLowerCase()}"><a title="${emo[1]}" href="#">${emo[0]}</a></li>`;
						});
						emojisHTML += `</div>`;
					}
				}
			}

			const picker = `
				<div class="emop-container" style="${pickerPos}">
					<nav class="emop-nav">
						<ul>
							${emoNavHTML}
							<li class="emop-nav-close"><a id="emop-close" href="#">&#10006;</a></li>
						</ul>
					</nav>
					<div class="emop-search">
						<input type="text" placeholder="Search" autofocus>
					</div>
					<div>
						<ul class="emop-list">
							${emojisHTML}
						</ul>
					</div>
				</div>
			`;

			document.body.insertAdjacentHTML('beforeend', picker);
		},

		closeMe: e => {
			e.preventDefault();
			
			this.lib('.emop-container').remove();
			lastFocus.focus();
		},

		insert: e => {
			e.preventDefault();
			
			const emoji = e.target.innerText.trim();
			const fields = document.querySelectorAll(options.fields);

			fields.forEach(field => {
				if (field == lastFocus) {
					if (field.selectionStart || field.selectionStart == "0") {
						const startPos = field.selectionStart;
						const endPos = field.selectionEnd;
						field.value = field.value.substring(0, startPos) + emoji + field.value.substring(endPos, field.value.length);
						field.setSelectionRange(startPos + 2, startPos + 2); //set caret position
					} else {
						field.value += emoji;
					}
					field.focus();
				}
			})
		},

		catNav: e => {
			e.preventDefault();

			const link = e.target.closest('a');

			if (link.getAttribute('id') && link.getAttribute('id') === 'emop-close') return false;

			const id = link.getAttribute('href');
			const emojiBody = document.querySelector('.emop-list');
			const destination = emojiBody.querySelector(`${id}`);
			destination.scrollIntoView({behavior:"smooth", block:"start", inline:"nearest"})
		},

		search: e => {
			const val = e.target.value.trim();

			if (!emojiList) {
				emojiList = Array.from(document.querySelectorAll('.emop-list-cat li'));
			}

			emojiList.filter(emoji => {
				if (!emoji.getAttribute('data-title').match(val)) {
					emoji.style.display = 'none'
				} else {
					emoji.style.display = ''
				}
			})
		}

	};

	const bindEvents = () => {
		this.lib(document.body).on('click', functions.closeMe, '#emop-close');
		this.lib(document.body).on('click', functions.render, options.selector);
		this.lib(document.body).on('click', functions.insert, '.emop-list a');
		this.lib(document.body).on('click', functions.catNav, '.emop-nav a');
		this.lib(document.body).on('input', functions.search, '.emop-search input');
	};


	//start the picker
	functions.styles(); //insert styles
	bindEvents.call(this); //event functions
}
