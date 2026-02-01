<?php
/*
= LuxCal admin interface language file =

This file has been produced by LuxSoft. Please send your comments to rb@luxsoft.eu.

This file is part of the LuxCal Web Calendar.
*/

$ax = array(

//general
"none" => "Žádný",
"no" => "ne",
"yes" => "ano",
"own" => "own",
"all" => "Všechny",
"or" => "nebo",
"back" => "Zpět",
"ahead" => "Ahead",
"close" => "Zavřít",
"always" => "vždy",
"at_time" => 'v', //date and time separator (e.g. 30-01-2020 @ 10:45)
"times" => "times",
"cat_seq_nr" => "category sequence nr",
"rows" => "rows",
"columns" => "columns",
"hours" => "hours",
"minutes" => "minut",
"user_group" => "Barvy vlastníka",
"event_cat" => "Barvy kategorie",
"email" => "Email",
"telegram" => "Telegram",
"sms" => "SMS",
"id" => "ID",
"username" => "Jméno",
"password" => "Heslo",
"public" => "Public",
"logged_in" => "Přihlášen",
"pw_no_chars" => "Characters <, > and ~ not allowed in password",

//settings.php - fieldset headers + general
"set_general_settings" => "Základní nastavení",
"set_navbar_settings" => "Navigační pruh",
"set_event_settings" => "Události",
"set_user_settings" => "Uživatelské účty",
"set_upload_settings" => "File Uploads",
"set_reminder_settings" => "Reminders",
"set_perfun_settings" => "Periodické funkce (pouze je-li aktivní cron job)",
"set_sidebar_settings" => "Seznam nadcházejících událostí  (jen jsou-li použity)",
"set_view_settings" => "Pohledy",
"set_dt_settings" => "Datum/čas",
"set_save_settings" => "Uložit nastavení",
"set_test_mail" => "Zkušební mail",
"set_mail_sent_to" => "Zkušební mail byl odeslán",
"set_mail_sent_from" => "Tento zkušební mail byl odeslán ze stránek administrace vašeho kalendáře",
"set_mail_failed" => "Sending test mail failed - recipient(s)",
"set_missing_invalid" => "Chybné nebo neplatné nastavení",
"set_settings_saved" => "Nastavení kalendáře uloženo",
"set_save_error" => "Chyba databáze - Nastavení kalendáře nelze uložit",
"hover_for_details" => "Po najetí myší na názvy nastavení se vám zobrazí krátká nápověda",
"default" => "výchozí",
"enabled" => "povoleno",
"disabled" => "zakázáno",
"pixels" => "pixelů",
"warnings" => "Warnings",
"notices" => "Notices",
"visitors" => "Visitors",
"height" => "Height",
"no_way" => "Nejste oprávněni provádět tuto akci",

//settings.php - general settings.
"versions_label" => "Versions",
"versions_text" => "• calendar version, followed by the database in use<br>• PHP version<br>• database version",
"calTitle_label" => "Název kalendáře",
"calTitle_text" => "Zobrazí se v záhlaví kalendáře a je použit v emailových připomínkách.",
"calUrl_label" => "URL kalendáře",
"calUrl_text" => "Webová stránka kalendáře.",
"calEmail_label" => "E-mail adresa kalendáře",
"calEmail_text" => "Adresa odesílatele použitá v emailových připomínkách.<br>Formát: 'email' nebo 'jméno &#8826;email&#8827;'. 'jméno' by měl být název kalendáře.",
"logoPath_label" => "Path/name of logo image",
"logoPath_text" => "If specified, a logo image will be displayed in the left upper corner of the calendar. If also a link to a parent page is specified (see below), then the logo will be a hyper-link to the parent page. The logo image should have a maximum height and width of 70 pixels.",
"logoXlPath_label" => "Path/name of log-in logo image",
"logoXlPath_text" => "If specified, a logo image of the specified height will be displayed on the Log In page below the Log In form.",
"backLinkUrl_label" => "Odkaz na nadřazenou stránku",
"backLinkUrl_text" => "URL mateřské stránky. Je-li použito, bude v levé části navigačníhu pruhu zobrazeno tlačítko Zpět které bude odkazovat na zadané URL.<br>Například na nadřazenou stránku, ze které je odkazováno na kalendář If a logo path/name has been specified (see above), then no Back button will be displayed, but the logo will become the back link instead.",
"timeZone_label" => "Časové pásmo",
"timeZone_text" => "Časové pásmo kalendáře se používá k určení aktuálního času.",
"see" => "viz",
"notifChange_label" => "Send notification of calendar changes",
"notifChange_text" => "When a user adds, edits or deletes an event, a notification message will be sent to the specified recipients.",
"chgRecipList" => "semicolon separated recipient list",
"maxXsWidth_label" => "Max. width of small screens",
"maxXsWidth_text" => "For displays with a width smaller than the specified number of pixels, the calendar will run in a special responsive mode, leaving out certain less important elements.",
"rssFeed_label" => "Odkaz na RSS kanál",
"rssFeed_text" => "Je-li povoleno: pro uživatele, kteří mají alespoň práva pro 'prohlížení' bude zobrazen odkaz na RSS kanál v zápatí kalendáře a do HTML hlavičky stránky kalendáře bude přidán odkaz.",
"logging_label" => "Log calendar data",
"logging_text" => "The calendar can log error, warning and notice messages and visitors data. Error messages are always logged. Logging of warning and notice messages and visitors data can each be disabled or enabled by checking the relevant check boxes. All error, warning and notice messages are logged in the file 'logs/luxcal.log' and visitors data are logged in the files 'logs/hitlog.log' and 'logs/botlog.log'.<br>Note: PHP error, warning and notice messages are logged at a different location, determined by your ISP.",
"maintMode_label" => "PHP Maintenance mode",
"maintMode_text" => "When enabled, in the PHP scripts data submitted via the note (message) function and data stored in the 'note' variable will be shown in the calendar footer bar.",
"reciplist" => "The recipient list can contain a semicolon-separated list with user names, email addresses, phone numbers, Telegram chat IDs and, enclosed in square brackets, names of files with recipients. Files with recipients with one recipient per line should be located in the folder 'reciplists'. When omitted, the default file extension is .txt",
"calendar" => "kalendář",
"user" => "uživatel",
"database" => "database",

//settings.php - navigation bar settings.
"contact_label" => "Contact button",
"contact_text" => "If enabled: A Contact button will be displayed in the side menu. Clicking this button will open a contact form, which can be used to send a message to the calendar administrator.",
"optionsPanel_label" => "Panel s menu nastavení",
"optionsPanel_text" => "Zapíná/vypíná menu na panelu s nastavením.<br>• Menu kalendáře je přístupné administrátorovi k přepínání kalendářů. (Zapnutí má smysl jen pokud je nastaveno více kalendářů)<br>• The view menu can be used to select one of the calendar views.<br>• The groups menu can be used to display only events created by users in the selected groups.<br>• Volba uživatelů slouží k přepínání zobrazení pouze událostí určitých uživatelů<br>• Menu volby kategorie filtruje zobrazení pouze událostí vybraných kategorií.<br>• Menu volby jazyka se používá pro přepínání zobrazeného jazyka (pouze pokud je nainstalovaáno více jazyků).<br>Note: If no menus are selected, the option panel button will not be displayed.",
"calMenu_label" => "kalendář",
"viewMenu_label" => "view",
"groupMenu_label" => "groups",
"userMenu_label" => "uživatelé",
"catMenu_label" => "kategorie",
"langMenu_label" => "jazyk",
"availViews_label" => "Available calendar views",
"availViews_text" => "Calendar views available to publc and logged-in users specified by means of a comma-separated list with view numbers. Meaning of the numbers:<br>1: year view<br>2: month view (7 days)<br>3: work month view<br>4: week view (7 days)<br>5: work week view<br>6: day view<br>7: upcoming events view<br>8: changes view<br>9: matrix view (categories)<br>10: matrix view (users)<br>11: gantt chart view",
"viewButtonsL_label" => "View buttons on navigation bar (large display)",
"viewButtonsS_label" => "View buttons on navigation bar (small display)",
"viewButtons_text" => "View buttons on the navigation bar for public and logged-in users, specified by means of a comma-separated list of view numbers.<br>If a number is specified in the sequence, the corresponding button will be displayed. If no numbers are specified, no View buttons will be displayed.<br>Meaning of the numbers:<br>1: Year<br>2: Full Month<br>3: Work Month<br>4: Full Week<br>5: Work Week<br>6: Day<br>7: Upcoming<br>8: Changes<br>9: Matrix-C<br>10: Matrix-U<br>11: Gantt Chart<br>The order of the numbers determines the order of the displayed buttons.<br>For example: '2,4' means: display 'Full Month' and 'Full Week' buttons.",
"defaultViewL_label" => "Výchozí pohled po startu (large displays)",
"defaultViewL_text" => "Default calendar view on startup for public and logged-in users using large displays.<br>Recommended choice: Month.",
"defaultViewS_label" => "Výchozí pohled po startu (small display)",
"defaultViewS_text" => "Default calendar view on startup for public and logged-in users using small displays.<br>Recommended choice: Upcoming.",
"language_label" => "Výchozí jazyk uživatelského rozhraní (public user)",
"language_text" => "For public (not logged in) users the language set for the browser user interface will be used for the calendar as well. If the browser language is not a valid calendar language, this default language will be used.<br>Note: soubory ui-{language}.php, ai-{language}.php, ug-{language}.php a ug-layout.png musí být ve složce lang/ . {language} = vybraný jazyk rozhraní. Názvy souborů musí být malými písmeny!",
"birthday_cal_label" => "PDF Birthday Calendar",
"birthday_cal_text" => "If enabled, an option 'PDF File - Birthday' will appear in the Side Menu for users with at least 'view' rights. See the admin_guide.html - Birthday Calendar for further details",
"sideLists_label" => "Approve, Todo, Upcoming lists",
"sideLists_text" => "If enabled, an option to show the respective list will appear in the Side Menu. The 'Events to be approved' list will only be available for users with at least 'manager' rights.",
"toapList_label" => "To approve list",
"todoList_label" => "To do list",
"upcoList_label" => "Upcoming list",

//settings.php - events settings.
"privEvents_label" => "Vkládaní soukromých událostí",
"privEvents_text" => "Povoleno: uživatelé mohou vkládat soukromé události.<br>Ty budou viditelné pouze pro uživatele, který je vložil.<br>Výchozí: při vkládání nových událostí bude volba 'soukromé' zaškrtnuta jako výchozí.<br>Always: when adding new events they will always be private, the 'private' checkbox in the Event window will not be shown.",
"venueInput_label" => "Specifying venues",
"venueInput_text" => "In the Event window specifying a venue can be done either by typing the venue or by selecting a venue from a pre-defined list. If Free text is selected, the user can type the venue, if List is selected the user can select a venue from a drop-down list and when Both is selected, the user can choose between the two.<br> When a drop-down list is used, the 'files' folder must contain a file called venues.txt with one venue per line.",
"timeDefault_label" => "Adding new events - time default",
"timeDefault_text" => "When adding events, in the Event window the default way the event time fields appear in the event form can be set as follows:<br>• show times: The start and end time fields are shown and ready to be completed<br>• all day: The All Day check box is checked, no start and end time fields are shown<br>• no time: The No Time check box is checked, no start and end time fields are shown.",
"evtDelButton_label" => "Zobrazit tlačítko Smazat v okně události",
"evtDelButton_text" => "Zakázáno: tlačítko Smazat nebude zobrazeno v okně události. Uživatelé s právy editace nemohou mazat události.<br>Povoleno: tlačítko Smazat bude zobrazeno v okně události pro všechny uživatele<br>Manager: tlačítko Smazat v okně události bude viditelné pouze pro uživatele s právy 'manažer'.",
"eventColor_label" => "Barva událostií se řídí podle",
"eventColor_text" => "Události v pohledech do kalendáře mohou mít přiřazenu barvu podle vlastníka, nebo kategorie, do které jsou zařazeny",
"defVenue_label" => "Default Venue",
"defVenue_text" => "In this text field a venue can be specified which will be copied to the Venue field of the event form when adding new events.",
"xField1_label" => "Název doplňkového pole 1",
"xField2_label" => "Název doplňkového pole 2",
"xFieldx_text" => "Název dpolňkového pole. Je-li toto pole zahrnuto v šabloně události, bude vloženo jako další textové pole do okna události a zobrazeno u události ve všech pohledech a stránkách.<br>• Popisný název může být max. 15 znaků dlouhý např. 'Email', 'Webové stránky', 'Tel. číslo'.<br>• Minimum user rights: the field will only be visible to users with the selected user rights or higher.",
"evtWinSmall_label" => "Reduced event window",
"evtWinSmall_text" => "When adding/editing events, the Event window will show a subset of the input fields. To show all fields, an arrow can be selected.",
"emojiPicker_label" => "Emoji picker in Event window",
"emojiPicker_text" => "When enabled, in the Event Add/Edit window an emoji picker can be selected to add emoji to the event title and to the description fields.",
"mapViewer_label" => "Map viewer URL",
"mapViewer_text" => "If a map viewer URL has been specified, an address in the event's venue field enclosed in !-marks, will be shown as an Address button in the calendar views. When hovering this button the textual address will be shown and when clicked, a new window will open where the address will be shown on the map.<br>The full URL of a map viewer should be specified, to the end of which the address can be joined.<br>Examples:<br>Google Maps: https://maps.google.com/maps?q=<br>OpenStreetMap: https://www.openstreetmap.org/search?query=<br>If this field is left blank, addresses in the Venue field will not be show as an Address button.",
"evtDrAndDr_label" => "Event drag and drop",
"evtDrAndDr_text" => "When enabled, in Year view, Month view and in the mini calendar on the side panel, events can be moved or copied from one day to an other day by means of Drag and Drop. If 'manager' is selected, only users with at least manager rights can use this feature. See the admin_guide.html for a detailed description.",
"free_text" => "Free text",
"venue_list" => "Venue list",
"both" => "Both",
"xField_label" => "Label",
"show_times" => "show times",
"check_ald" => "all day",
"check_ntm" => "no time",
"min_rights" => "Minimum user rights",
"no_color" => 'no color',
"manager_only" => 'manažer',

//settings.php - user account settings.
"selfReg_label" => "Samoobslužná registrace",
"selfReg_text" => "Umožní uživatelům se sami zaregistrovat a získat přístup ke kalendáři.<br>Skupina do které budou přidáni uživatelé při samoobslužné registraci.",
"selfRegQA_label" => "Self registration question/answer",
"selfRegQA_text" => "When self registration is enabled, during the self-registration process the user will be asked this question and will only be able to self-register if the correct answer is given. When the question field is left blank, no question will be asked.",
"selfRegNot_label" => "Oznámení samoobslužné registrace",
"selfRegNot_text" => "Odeslat oznamovací e-mail na adresu administrátora kalendáře, když proběhne samoobslužná registrace.",
"restLastSel_label" => "Obnovit předvolby uživatele ",
"restLastSel_text" => "Předvolby uživatele (Nastavení panelu voleb) budou uloženy a když uživatel opět navštíví stránky kalendáře, opět obnoveny. If the user does not log in during the specified number of days, the values will be lost.",
"answer" => "answer",
"exp_days" => "days",
"view" => "prohlížet",
"post_own" => 'jen vlastní',
"post_all" => 'všechny',
"manager" => 'manažer',

//settings.php - view settings.
"templFields_text" => "Meaning of the numbers:<br>1: Venue field<br>2: Event category field<br>3: Description field<br>4: Extra field 1 (see below)<br>5: Extra field 2 (see below)<br>6: Email notification data (only if a notification has been requested)<br>7: Date/time added/edited and the associated user(s)<br>8: Attached pdf, image or video files as hyperlinks.<br>The order of the numbers determines the order of the displayed fields.",
"evtTemplate_label" => "Event templates",
"evtTemplate_text" => "The event fields to be displayed in the general calendar views, the upcoming event views and in the hover box with event details can be specified by means of a sequence of numbers.<br>If a number is specified in the sequence, the corresponding field will be displayed.",
"evtTemplPublic" => "Public users",
"evtTemplLogged" => "Logged-in users",
"evtTemplGen" => "General view",
"evtTemplUpc" => "Upcoming view",
"evtTemplPop" => "Hover box",
"sortEvents_label" => "Sort events on times or category",
"sortEvents_text" => "In the various views events can be sorted on the following criteria:<br>• event times<br>• event category sequence number",
"yearStart_label" => "Počáteční měsíc v ročním pohledu",
"yearStart_text" => "Pokud zadáte počáteční měsíc (1 - 12), roční pohled bude vždy začínat tímto měsícem i při listování mezi roky.<br>Hodnota 0 nemá zvláštní význam: výchozí měsíc potom závisí na aktuálním datu a zobrazí se v prvním řádku tabulky.",
"YvRowsColumns_label" => "Rows and columns to show in Year view",
"YvRowsColumns_text" => "Počet řádků, každý obsahující 4 měsíce, které se budou zobrazovat v Ročním pohledu.<br>Doporučeno: 4, což zobrazí 16 měsíců na stránku.<br>Počet měsíců, které se zobrazí v jednom řádku u Ročního pohledu.<br>Doporučená hodnota: 3 nebo 4.",
"MvWeeksToShow_label" => "Počet týdnů v měsíčním pohledu",
"MvWeeksToShow_text" => "Počet týdnů, které se zobrazí v Měsíčním pohledu.<br>doporučená hodnota: 10, což zobrazí 2,5 měsíce na stránku.<br>The values 0 and 1 have a special meaning:<br>0: display exactly 1 month - blank leading and trailing days.<br>1: display exactly 1 month - display events on leading and trailing days.",
"XvWeeksToShow_label" => "Weeks to show in Matrix view",
"XvWeeksToShow_text" => "Number of calendar weeks to display in Matrix view.",
"GvWeeksToShow_label" => "Weeks to show in Gantt chart view",
"GvWeeksToShow_text" => "Number of calendar weeks to display in Gantt Chart view.",
"workWeekDays_label" => "Pracovní dny",
"workWeekDays_text" => "Days colored as working days in the calendar views and for instance to be shown in the weeks in Work Month view and Work Week view.<br>Enter the number of each working day.<br>e.g. 12345: Monday - Friday<br>Not entered days are considered to be weekend days.",
"weekStart_label" => "První den týdne",
"weekStart_text" => "Enter the day number of the first day of the week.",
"lookBackAhead_label" => "Nadcházejících dní v přehledu",
"lookBackAhead_text" => "Počet dní, které budou zahrnuty do přehledu nadcházejících události, seznamu úkolů a RSS kanálu.",
"searchBackAhead_label" => "Default days to search back/ahead",
"searchBackAhead_text" => "When no dates are specified on the Search page, these are the default number of days to search back and to search ahead.",
"dwStartEndHour_label" => "Start and end hour in Day/Week view",
"dwStartEndHour_text" => "Hours at which a normal day of events starts and ends.<br>E.g. setting these values to 6 and 18 will avoid wasting space in Week/Day view for the quiet time between midnight and 6:00 and 18:00 and midnight.<br>The time picker, used to enter a time, will also start and end at these hours.",
"dwTimeSlot_label" => "Rozlišení v Denním/Týdenním pohledu",
"dwTimeSlot_text" => "Časové měřítko a výška v denním/týdenním pohledu v minutách.<br>Tato hodnota, společně s Počáteční hodinou (viz předchozí položka) určuje počet řádků v denním/týdenním pohledu.",
"dwTsInterval" => "Časové trvání",
"dwTsHeight" => " Výška",
"evtHeadX_label" => "Event layout in Month, Week and Day view",
"evtHeadX_text" => "Templates with placeholders of event fields that should be displayed. The following placeholders can be used:<br>#ts - start time<br>#tx - start and end time<br>#e - event title<br>#o - event owner<br>#v - venue<br>#lv - venue with label 'Venue:' in front<br>#c - category<br>#lc - category with label 'Category:' in front<br>#a - age (see note below)<br>#x1 - extra field 1<br>#lx1 - extra field 1 with label from Settings page in front<br>#x2 - extra field 2<br>#lx2 - extra field 2 with label from Settings page in front<br>#/ - new line<br>The fields are displayed in the specified order. Characters other than the placeholders will remain unchanged and will be part of the displayed event.<br>HTML-tags are allowed in the template. E.g. &lt;b&gt;#e&lt;/b&gt;.<br>The | character can be used to split the template in sections. If within a section all #-parameters result in an empty string, the whole section will be omitted.<br>Note: The age is shown if the event is part of a category with 'Repeat' set to 'every year' and the year of birth in parentheses is mentioned somewhere in either the event description field or in one of the extra fields.",
"monthView" => "Month view",
"wkdayView" => "Week/Day view",
"ownerTitle_label" => "Show event owner in front of event title",
"ownerTitle_text" => "In the various calendar views, show the event owner name in front of the event title.",
"showSpanel_label" => "Side panel in calendar views",
"showSpanel_text" => "In the calendar views, right next to the main calendar page, a side panel with the following items can be shown:<br>• a mini calendar which can be used to look back or ahead without changing the date of the main calendar<br>• a decoration image corresponding to the current month<br>• an info area to post messages/announcements during specified periods.<br>Per item a comma-separated list of view numbers can be specified, for which the side panel should be shown.<br>Possible view numbers:<br>0: all views<br>1: year view<br>2: month view (7 days)<br>3: work month view<br>4: week view (7 days)<br>5: work week view<br>6: day view<br>7: upcoming events view<br>8: changes view<br>9: matrix view (categories)<br>10: matrix view (users)<br>11: gantt chart view.<br>If 'Today' is checked, the side panel will always use the date of today, otherwise it will follow the date selected for the main calendar.<br>See admin_guide.html for Side Panel details.",
"spMiniCal" => "Mini calendar",
"spImages" => "Images",
"spInfoArea" => "Info area",
"spToday" => "Today",
"topBarDate_label" => "Show current date on top bar",
"topBarDate_text" => "Enable/disable the display of the current date on the calendar top bar in the calendar views. If displayed, the current date can be clicked to reset the calendar to the current date.",
"showImgInMV_label" => "Zobrazit odkazy v měsíčním pohledu",
"showImgInMV_text" => "Enable/disable the display in Month view of thumbnail images added to one of the event description fields. When enabled, thumbnails will be shown in the day cells and when disabled, thumbnails will be shown in the on-mouse-over boxes instead.",
"urls" => "URL links",
"emails" => "email links",
"monthInDCell_label" => "Název měsíce v každém poli",
"monthInDCell_text" => "V měsíčním pohledu zobrazí v polích pro jednotlivé dny zkratku názvu měsíce",
"scrollDCell_label" => "Use scrollbar in day cells",
"scrollDCell_text" => "If in month view a day cell is too small, rather than increasing the day cell height, a vertical scrollbar will appear.",

//settings.php - date/time settings.
"dateFormat_label" => "Formát data události (dd mm yyyy)",
"dateFormat_text" => "Textový řetězec, který určuje formát data událostí v pohledech kalendáře a vstuoních polích.<br>Povolené znaky: y = rok, m = měsíc a d = den.<br>Ne-alfanumerické znaky mohou být použity jako oddělovače a budou zobrazeny jak jsou.<br>Příklad: <br>y-m-d: 2024-10-31<br>m.d.y: 10.31.2024<br>d/m/y: 31/10/2024",
"dateFormat_expl" => "např. y.m.d: 2024.10.31",
"MdFormat_label" => "Formát data (dd měsíc)",
"MdFormat_text" => "Textový řetězec určující formát data obsahujícího den a měsíc.<br>Povolené znaky: M = název měsíce, d = den čísly.<br>Ne-alfanumerické znaky mohou být použity jako oddělovače a budou zobrazeny jak jsou.<br>Příklad: <br>d M: 12 duben<br>M, d: červenec, 14",
"MdFormat_expl" => "např. M, d: červenec, 14",
"MdyFormat_label" => "Formát data (dd měsíc yyyy)",
"MdyFormat_text" => "Textový řetězec určující formát data obsahujícího den, měsíc a rok.<br>Povolené znaky: d = den čísly, M = název měsíce, y = rok čísly.<br>Ne-alfanumerické znaky mohou být použity jako oddělovače a budou zobrazeny jak jsou.<br>Příklad:<br>d. M y: 12. duben 2024<br>M d, y: červenec 8, 2024",
"MdyFormat_expl" => "např. M d, y: červenec 8, 2024",
"MyFormat_label" => "Formát data (měsíc yyyy)",
"MyFormat_text" => "Textový řetězec určující formát data obsahujícíhoměsíc a rok.<br>Povolené znaky: M = název měsíce, y = rok čísly.<br>Ne-alfanumerické znaky mohou být použity jako oddělovače a budou zobrazeny jak jsou.<br>Příklad: <br>M y: duben 2024<br>y - M: 2024 - červenec",
"MyFormat_expl" => "např. M y: duben 2024",
"DMdFormat_label" => "Formát data (den-v-týdnu dd měsíc)",
"DMdFormat_text" => "Textový řetězec určující formát data obsahujícího den v týdnu, den a měsíc.<br>Povolené znaky: WD = den v týdnu slovy, d = den, M = název měsíce.<br>Ne-alfanumerické znaky mohou být použity jako oddělovače a budou zobrazeny jak jsou.<br>Příklad: <br>WD d. M: pátek 12. duben<br>WD, M d: pondělí, červenec 14",
"DMdFormat_expl" => "např. WD - M d: neděle - duben 6",
"DMdyFormat_label" => "Formát data (den-v-týdnu dd měsíc yyyy)",
"DMdyFormat_text" => "Textový řetězec určující formát data obsahujícího den v týdnu, den, měsíc a rok.<br>Povolené znaky: WD = den v týdnu slovy, M = název měsíce, d = den, y = rok.<br>Ne-alfanumerické znaky mohou být použity jako oddělovače a budou zobrazeny jak jsou.<br>Příklad:<br>WD d M y: Friday 13 April 2024<br>WD - M d, y: Monday - July 16, 2024",
"DMdyFormat_expl" => "např. WD, M d, y: pondělí, červenec 16, 2024",
"timeFormat_label" => "Formát času (hh mm)",
"timeFormat_text" => "Textový řetězec určující formát času událostí v pohledech kalendáře a vstupních polích.<br>Povolené znaky: h = hodiny, H = hodiny with leading zeros, m = minuty, a = am/pm (volitelné), A = AM/PM (volitelné).<br>Ne-alfanumerické znaky mohou být použity jako oddělovače a budou zobrazeny jak jsou.<br>Příklad:<br>h:m: 18:35<br>h.m a: 6.35 pm<br>H:mA: 06:35PM",
"timeFormat_expl" => "např. h:m: 22:35 a h:mA: 10:35PM",
"weekNumber_label" => "Zobrazovat čísla týdnů",
"weekNumber_text" => "Zapíná zobrazování čísla týdne v ročním, měsíčním a týdenním pohledu",
"time_format_us" => "12-hod AM/PM",
"time_format_eu" => "24-hod",
"sunday" => "neděle",
"monday" => "pondělí",
"time_zones" => "Časová pásma",
"dd_mm_yyyy" => "dd-mm-yyyy",
"mm_dd_yyyy" => "mm-dd-yyyy",
"yyyy_mm_dd" => "yyyy-mm-dd",

//settings.php - file uploads settings.
"maxUplSize_label" => "Maximum file upload size",
"maxUplSize_text" => "Maximum allowed file size when users upload attachment or thumbnail files.<br>Note: Most PHP installations have this maximum set to 2 MB (php_ini file) ",
"attTypes_label" => "Attachment file types",
"attTypes_text" => "Comma-separated list with valid attachment file types that can be uploaded (e.g. '.pdf,.jpg,.gif,.png,.mp4,.avi')",
"tnlTypes_label" => "Thumbnail file types",
"tnlTypes_text" => "Comma-separated list with valid thumbnail file types that can be uploaded (e.g. '.jpg,.jpeg,.gif,.png')",
"tnlMaxSize_label" => "Thumbnail - maximum size",
"tnlMaxSize_text" => "Maximum thumbnail image size. If users upload larger thumbnails, the thumbnails will be automatically resized to the maximum size.<br>Note: High thumbnails will stretch the day cells in Month view, which may result in undesired effects.",
"tnlDelDays_label" => "Thumbnail delete margin",
"tnlDelDays_text" => "If a thumbnail is used since this number of days ago, it can not be deleted.<br>The value 0 days means the thumbnail can not be deleted.",
"days" =>"days",
"mbytes" => "MB",
"wxhinpx" => "W x H in pixels",

//settings.php - reminders settings.
"services_label" => "Available message services",
"services_text" => "Services available to sent event reminders. If a service is not selected, the corresponding section in the Event window will be suppressed. If no service is selected, no event reminders will be sent.",
"msgLogging_label" => "Notification message logging",
"msgLogging_text" => "When checked, the notification messages sent are logged in the messages.log file. The 'weeks' field specifies how long the logged messages should be kept",
"smsCarrier_label" => "SMS carrier template",
"smsCarrier_text" => "The SMS carrier template is used to compile the SMS gateway email address: ppp#sss@carrier, where . . .<br>• ppp: optional text string to be added before the phone number<br>• #: placeholder for the recipient's mobile phone number (the calendar will replace the # by the phone number)<br>• sss: optional text string to be inserted after the phone number, e.g. a username and password, required by some operators<br>• @: separator character<br>• carrier: carrier address (e.g. mail2sms.com)<br>Template examples: #@xmobile.com, 0#@carr2.int, #myunmypw@sms.gway.net.",
"smsCountry_label" => "SMS country code",
"smsCountry_text" => "If the SMS gateway is located in a different country than the calendar, then the country code of the country where the calendar is used must be specified.<br>Select whether the '+' or '00' prefix is required.",
"smsSubject_label" => "SMS subject template",
"smsSubject_text" => "If specified, the text in this template will be copied in the subject field of the SMS email messages sent to the carrier. The text may contain the character #, which will be replaced by the phone number of the calendar or the event owner (depending on the setting above).<br>Example: 'FROMPHONENUMBER=#'.",
"smsAddLink_label" => "Add event report link to SMS",
"smsAddLink_text" => "When checked, a link to the event report will be added to each SMS. By opening this link on their mobile phone, recipients will be able to view the event details.",
"maxLenSms_label" => "Maximum SMS message length",
"maxLenSms_text" => "SMS messages are sent with utf-8 character encoding. Messages up to 70 characters will result in one single SMS message; messages > 70 characters, with many Unicode characters, may be split into multiple messages.",
"calPhone_label" => "Calendar phone number",
"calPhone_text" => "The phone number used as sender ID when sending SMS notification messages.<br>Format: free, max. 20 digits (some countries require a telephone number, other countries also accept alphabetic characters).<br>If no SMS service is active or if no SMS subject template has been defined, this field may be blank.",
"notSenderEml_label" => "Add 'Reply to' field to email",
"notSenderEml_text" => "When selected, notification emails will contain a 'Reply to' field with the email address of the event owner, to which the recipient can reply.",
"notSenderSms_label" => "Sender of notification SMSes",
"notSenderSms_text" => "When the calendar sends reminder SMSes, the sender ID of the SMS message can be either the calendar phone number, or the phone number of the user who created the event.<br>If 'user' is selected and a user account has no phone number specified, the calendar phone number will be taken.<br>In case of the user phone number, the receiver can reply to the message.",
"defRecips_label" => "Default list of recipients",
"defRecips_text" => "If specified, this will be the default recipients list for email and/or SMS notifications in the Event window. If this field is left blank, the default recipient will be the event owner.",
"maxEmlCc_label" => "Max. no. of recipients per email",
"maxEmlCc_text" => "Normally ISPs allow a maximum number of recipients per email. When sending email or SMS reminders, if the number of recipients is greater than the number specified here, the email will be split in multiple emails, each with the specified maximum number of recipients.",
"emlFootnote_label" => "Reminder email footnote",
"emlFootnote_text" => "Free-format text that will be added as a paragraph to the end of reminder email messages. HTML tags are allowed in the text.",
"mailServer_label" => "Mail server",
"mailServer_text" => "PHP je vhodné pro malý počet mailů bez možnosti autorizace. Pro větší počet mailů, nebo je li požadována autorizace byste měli požívat SMTP.<br>Pro SMTP je potřeba SMTP mail server. Zvolíte-li SMTP, bude třeba zadat konfigurační parametry serveru.",
"smtpServer_label" => "Jméno SMTP serveru",
"smtpServer_text" => "Zde nastavte adresu SMTP serveru. Např. gmail SMTP server: smtp.gmail.com.",
"smtpPort_label" => "Číslo portu SMTP",
"smtpPort_text" => "Nastavuje číslo portu pro komunikaci s SMTP serverem. Obvykle nastaveno na 25, 465 nebo 587. Gmail používá port 465.",
"smtpSsl_label" => "SSL (Secure Sockets Layer)",
"smtpSsl_text" => "Pro SMTP mail zapíná zabezpečenou komunikaci přes secure sockets layer (SSL). Pro gmail zapněte",
"smtpAuth_label" => "SMTP ověření",
"smtpAuth_text" => "Je-li požadována SMTP autorizace, bude uživatelské jméno a heslo nastavené níže použito k přihlášení k SMTP.<br>For gmail for instance, the user name is the part of your email address before the @.",
"tlgToken_label" => "Telegram token",
"tlgToken_text" => "Telegram token in the following format: &lt;bot ID&gt;:&lt;bot hash&gt;. For details see installation_guide.html, section Event Notification Messages.",
"cc_prefix" => "Country code starts with prefix + or 00",
"weeks" => "Weeks",
"general" => "General",
"php_mail" => "PHP mail",
"smtp_mail" => "SMTP mail (complete fields below)",

//settings.php - periodic function settings.
"cronHost_label" => "Cron job host",
"cronHost_text" => "Specify where the cron job is hosted which periodically starts the script 'lcalcron.php'.<br>• local: cron job runs on the same server as the calendar<br>• remote: cron job runs on a remote server or lcalcron.php is started manually (testing)<br>• IP address: cron job runs on a remote server with the specified IP address.",
"cronSummary_label" => "Souhrn z cronu pro admina",
"cronSummary_text" => "Poslat souhrn úlohou cronu administrátorovi kalendáře.<br>Povolení je užitečné jen pokud:<br>- je aktivní úloha cronu",
"chgSummary_text" => "Počet dní, za které se zpětně zjišťují změny v kalendáři.<br>Pokud je počet nastaven na 0 souhrn se nebude zasílat.",
"icsExport_label" => "Denní export událostí do iCal",
"icsExport_text" => "Je-li povoleno, všechny události v rozsahu -1 týden až +1 rok budou exportovány ve formátu iCalendar do .ics souboru do složky 'files'.<br>Jméno souboru bude název kalendáře (mezery nahrazeny znaky _ ). Staré soubory přepisují nové.",
"eventExp_label" => "Událost vyprší po dnech",
"eventExp_text" => "Počet dní po platnosti události, kdy bude automaticky smazána.<br>Je-li nastaveno na 0 nebo neběží cron, žádné události nebudou mazány.",
"maxNoLogin_label" => "Max. počet dní bez přihlášení",
"maxNoLogin_text" => "Pokud se uživatel nepřihlásí po tuto dobu, jeho účet bude automaticky smazán.<br>Je-li nastaveno na 0, uživatelské účty ne nikdy nesmažou.",
"local" => "local",
"remote" => "remote",
"ip_address" => "IP address",

//settings.php - mini calendar / upcoming events list settings.
"popFieldsSbar_label" => "Pole události - bublina v postraní liště",
"popFieldsSbar_text" => "The event fields to be displayed in an overlay when the user hovers an event in the stand-alone sidebar can be specified by means of a sequence of numbers.<br>If no fields are specified at all, no hover box will be displayed.",
"showLinkInSB_label" => "Zobrazovat odkazy v měsíčním pohledu",
"showLinkInSB_text" => "Zobrazí URL z popisu události jako hyperlink v seznamu nadcházejících událostí",
"sideBarDays_label" => "Počet dní v seznamu nadcházejících událostí",
"sideBarDays_text" => "Počet nadcházejících dní, které se zahrnují do přehledu chystaných událostí.",

//login.php
"log_log_in" => "Přihlásit",
"log_remember_me" => "Pamatuj si mě",
"log_register" => "Registrovat",
"log_change_my_data" => "Změnit moje údaje",
"log_save" => "Změnit",
"log_done" => "Done",
"log_un_or_em" => "Uživatelské jméno nebo e-mail",
"log_un" => "Jméno",
"log_em" => "E-mail",
"log_ph" => "Mobile phone number",
"log_tg" => "Telegram chat ID",
"log_answer" => "Your answer",
"log_pw" => "Heslo",
"log_expir_date" => "Account expiration date",
"log_account_expired" => "This account has expired",
"log_new_un" => "Nové Jméno",
"log_new_em" => "Nový e-mail",
"log_new_pw" => "Nové heslo",
"log_con_pw" => "Confirm Password",
"log_pw_msg" => "Zde jsou přihlašovací údaje pro kalendář",
"log_pw_subject" => "Vaše heslo",
"log_npw_subject" => "Vaše nové heslo",
"log_npw_sent" => "Vaše nové heslo bylo odesláno",
"log_registered" => "Registrace úspěšná - Vaše heslo bylo odesláno e-mailem",
"log_em_problem_not_sent" => "Email problem - your password could not be sent",
"log_em_problem_not_noti" => "Email problem - could not notify the administrator",
"log_un_exists" => "Uživatelské jméno již existuje",
"log_em_exists" => "E-mailová adresa již existuje",
"log_un_invalid" => "Chybné jméno (min. délka 2: A-Z, a-z, 0-9, a _-.) ",
"log_em_invalid" => "Chybná emailová adresa",
"log_ph_invalid" => "Invalid mobile phone number",
"log_tg_invalid" => "Invalid Telegram chat ID",
"log_sm_nr_required" => "SMS: mobile phone number required",
"log_tg_id_required" => "Telegram: chat ID required",
"log_sra_wrong" => "Incorrect answer to the question",
"log_sra_wrong_4x" => "You have answered incorrectly 4 times - try again in 30 minutes",
"log_un_em_invalid" => "Uživatelské jméno/e-mail není platný",
"log_un_em_pw_invalid" => "Uživatelské jméno/e-mail nebo heslo je chybné",
"log_pw_error" => "Passwords not matching",
"log_no_un_em" => "Prosím zadejte vaše uživatelské jméno/e-mail",
"log_no_un" => "Zadejte uživatelské jméno",
"log_no_em" => "Zadejte vaši e-mailovou adresu",
"log_no_pw" => "Zadejte heslo",
"log_no_rights" => "Přihlášení odepřeno: nemáte právo k prohlížení - kontaktujte administrátora",
"log_send_new_pw" => "Zaslat nové heslo",
"log_new_un_exists" => "Nové jméno již existuje",
"log_new_em_exists" => "Nová e-mailová adresa již existuje",
"log_ui_language" => "Jazyk uživatelského rozhraní",
"log_new_reg" => "Registrace nového uživatele",
"log_date_time" => "Datum / čas",
"log_time_out" => "Time out",

//categories.php
"cat_list" => "Seznam kategorií",
"cat_edit" => "Změnit",
"cat_delete" => "Smazat",
"cat_add_new" => "Přidat novou kategorii",
"cat_add" => "Přidat",
"cat_edit_cat" => "Změnit kategorii",
"cat_sort" => "Seřadit podle názvu",
"cat_cat_name" => "Název kategorie",
"cat_symbol" => "Symbol",
"cat_symbol_repms" => "Category symbol (replaces minisquare)",
"cat_symbol_eg" => "e.g. A, X, ♥, ⛛",
"cat_matrix_url_link" => "URL link (shown in matrix view)",
"cat_seq_in_menu" => "Pořadí v menu",
"cat_cat_color" => "Barva kategorie",
"cat_text" => "Textu",
"cat_background" => "Pozadí",
"cat_select_color" => "Vyberte barvu",
"cat_subcats" => "Sub-<br>categories",
"cat_subcats_opt" => "Number of subcategories (optional)",
"cat_copy_from" => "Copy from",
"cat_eml_changes_to" => "Send event changes to",
"cat_url" => "URL",
"cat_name" => "Name",
"cat_subcat_note" => "Note that the currently existing subcategories may already be used for events",
"cat_save" => "Uložit",
"cat_added" => "Kategorie uložena",
"cat_updated" => "Kategorie upravena",
"cat_deleted" => "Kategorie smazána",
"cat_not_added" => "Kategorie nebyla přidána",
"cat_not_updated" => "Kategorie nebyla změněna",
"cat_not_deleted" => "Kategorie nebyla smazána",
"cat_nr" => "č",
"cat_repeat" => "Opakování",
"cat_every_day" => "denně",
"cat_every_week" => "týdně",
"cat_every_month" => "měsíčně",
"cat_every_year" => "ročně",
"cat_overlap" => "Overlap<br>allowed<br>(gap)",
"cat_need_approval" => "Události čekají<br>na potvrzení",
"cat_no_overlap" => "No overlap allowed",
"cat_same_category" => "same category",
"cat_all_categories" => "all categories",
"cat_gap" => "gap",
"cat_ol_error_text" => "Error message, if overlap",
"cat_no_ol_note" => "Note that already existing events are not checked and consequently may overlap",
"cat_ol_error_msg" => "event overlap - select an other time",
"cat_no_ol_error_msg" => "Overlap error message missing",
"cat_duration" => "Event<br>duration<br>! = fixed",
"cat_default" => "default (no end time)",
"cat_fixed" => "fixed",
"cat_event_duration" => "Event duration",
"cat_olgap_invalid" => "Invalid overlap gap",
"cat_duration_invalid" => "Invalid event duration",
"cat_no_url_name" => "URL link name missing",
"cat_invalid_url" => "Invalid URL link",
"cat_day_color" => "Day color",
"cat_day_color1" => "Barva dne (year/matrix view)",
"cat_day_color2" => "Barva dne (month/week/day view)",
"cat_approve" => "Události čekají na potvrzení",
"cat_check_mark" => "Značka",
"cat_not_list" => "Notify<br>list",
"cat_label" => "štítek",
"cat_mark" => "značka",
"cat_name_missing" => "Chybí název kategorie",
"cat_mark_label_missing" => "Chybí značka/štítek",

//users.php
"usr_list_of_users" => "Seznam uživatelů",
"usr_name" => "Jméno",
"usr_email" => "E-mail",
"usr_phone" => "Mobile phone number",
"usr_phone_br" => "Mobile phone<br>number",
"usr_tg_id" => "Telegram chat ID",
"usr_tg_id_br" => "Telegram<br>chat ID",
"usr_not_via" => "Notify via",
"usr_not_via_br" => "Notify<br>via",
"usr_language" => "Language",
"usr_ui_language" => "User interface language",
"usr_group" => "Skupina",
"usr_password" => "Heslo",
"usr_expir_date" => "Account expiration date",
"usr_select_exp_date" => "Select expiration date",
"usr_blank_none" => "blank: no expiration",
"usr_expires" => "Expires",
"usr_edit_user" => "Změnit uživatelský profil",
"usr_add" => "Přidat uživatele",
"usr_edit" => "Změnit",
"usr_delete" => "Smazat",
"usr_login_0" => "První přihlášení",
"usr_login_1" => "Poslední přihlášení",
"usr_login_cnt" => "Přihlášení",
"usr_add_profile" => "Přidat profil",
"usr_upd_profile" => "Upravit profil",
"usr_if_changing_pw" => "Pouze při změně hesla",
"usr_pw_not_updated" => "Heslo nebylo změněno",
"usr_added" => "Uživatel byl přidán",
"usr_updated" => "Uživatelský profil byl aktualizován",
"usr_deleted" => "Uživatel smazán",
"usr_not_deleted" => "Uživatel nebyl smazán",
"usr_cred_required" => "Musíte zadat uživatelské jméno, e-mail a heslo",
"usr_name_exists" => "Uživatelské jméno již existuje",
"usr_email_exists" => "E-mailová adresa již existuje",
"usr_un_invalid" => "Chybné uživatelské jméno (min. délka 2: A-Z, a-z, 0-9, a _-.) ",
"usr_em_invalid" => "Chybná e-mailová adresa",
"usr_ph_invalid" => "Invalid mobile phone number",
"usr_tg_invalid" => "Invalid Telegram chat ID",
"usr_xd_invalid" => "Invalid account expiration date",
"usr_cant_delete_yourself" => "Nemůžete se sami smazat",
"usr_go_to_groups" => "Správa skupin",
"usr_all_cats" => "All Categories",
"usr_select" => "Select",
"usr_transfer" => "Transfer",
"usr_transfer_evts" => "Transfer Events",
"usr_transfer_ownership" => "Transfer ownership of events",
"usr_cur_owner" => "Current owner",
"usr_new_owner" => "New owner",
"usr_event_cat" => "Event category",
"usr_sdate_between" => "Start date between",
"usr_cdate_between" => "Creation date between",
"usr_select_start_date" => "Select start date",
"usr_select_end_date" => "Select end date",
"usr_blank_no_limit" => "Blank date: no limit",
"usr_no_undone" => "CAUTION, THIS TRANSACTION CANNOT BE UNDONE",
"usr_invalid_sdata" => "Invalid start date",
"usr_invalid_cdata" => "Invalid creation date",
"usr_edate_lt_sdate" => "End date before start date",
"usr_no_new_owner" => "New owner not specified",
"usr_evts_transferred" => "Done. Events transferred",

//groups.php
"grp_list_of_groups" => "Seznam skupin uživatelů",
"grp_name" => "Název skupiny",
"grp_priv" => "Oprávnění",
"grp_categories" => "Kategorie",
"grp_all_cats" => "všechny kategorie",
"grp_rep_events" => "Repeating<br>events",
"grp_m-d_events" => "Multi-day<br>events",
"grp_priv_events" => "Private<br>events",
"grp_upload_files" => "Upload<br>files",
"grp_tnail_privs" => "Thumbnail<br>privileges",
"grp_priv0" => "Bez práva přístupu",
"grp_priv1" => "Prohlížení",
"grp_priv2" => "Jen vlastní",
"grp_priv3" => "Všechny",
"grp_priv4" => "Manažer",
"grp_priv9" => "Administrace",
"grp_may_post_revents" => "May post repeating events",
"grp_may_post_mevents" => "May post multi-day events",
"grp_may_post_pevents" => "May post private events",
"grp_may_upload_files" => "May upload files",
"grp_tn_privs" => "Thumbnails privileges",
"grp_tn_privs00" => "none",
"grp_tn_privs11" => "view all",
"grp_tn_privs20" => "manage own",
"grp_tn_privs21" => "m. own/v. all",
"grp_tn_privs22" => "manage all",
"grp_edit_group" => "Upravit skupinu uživatelů",
"grp_sub_to_rights" => "Subject to user rights",
"grp_view" => "View",
"grp_add" => "Add",
"grp_edit" => "Změnit",
"grp_delete" => "Smazat",
"grp_add_group" => "Přidat skupinu",
"grp_upd_group" => "Změnit skupinu",
"grp_added" => "Skupina přidána",
"grp_updated" => "Skupina změněna",
"grp_deleted" => "Skupina smazána",
"grp_not_deleted" => "Skupina nebyla smazána",
"grp_in_use" => "Skupina se používá",
"grp_cred_required" => "Je vyžadován název skupiny, práva a kategorie",
"grp_name_exists" => "Skupina s tímto názvem již existuje",
"grp_name_invalid" => "Nepřípustný název skupiny (min délka 2: A-Z, a-z, 0-9, and _-.) ",
"grp_check_add" => "At least one check box in the Add column must be checked",
"grp_background" => "Barva pozadí",
"grp_select_color" => "Zvolte barvu",
"grp_invalid_color" => "Chybný formát barvy (#XXXXXX - X = HEX-hodnota)",
"grp_go_to_users" => "Správa uživatelů",

//texteditor.php
"edi_text_editor" => "Text Editor",
"edi_file_name" => "File name",
"edi_save" => "Save text",
"edi_backup" => "Backup text",
"edi_select_file" => "Select file",
"edi_info_text" => "Information text",
"edi_pub_recips" => "Public recipients",
"edi_recips_list" => "Recipients list",
"edi_new_recips_list" => "New recipients list",
"edi_no_file_name" => "No file name specified",
"edi_no_text" => "There is no text",
"edi_confirm_changes" => "The text changes have not been saved\\nDo you want to continue?", //don't remove '\\n'
"edi_text_saved" => "Text saved to file $1",

//database.php
"mdb_dbm_functions" => "Databázové funkce",
"mdb_noshow_tables" => "Nelze získat tabulku(y)",
"mdb_noshow_restore" => "Nemohu najít soubor se zálohou",
"mdb_file_not_sql" => "Typ souboru není '.sql'",
"mdb_db_content" => "Database Content",
"mdb_total_evenst" => "Total number of events",
"mdb_evts_older_1m" => "Events older than 1 month",
"mdb_evts_older_6m" => "Events older than 6 months",
"mdb_evts_older_1y" => "Events older than 1 year",
"mdb_evts_deleted" => "Total number of deleted events",
"mdb_not_removed" => "not yet removed from the DB",
"mdb_total_cats" => "Total number of categories",
"mdb_total_users" => "Total number of users",
"mdb_total_groups" => "Total number of user groups",
"mdb_compact" => "Komprimace databáze",
"mdb_compact_table" => "komprimace tabulky",
"mdb_compact_error" => "Chyba",
"mdb_compact_done" => "Hotovo",
"mdb_purge_done" => "Smazané události byly odstraněny",
"mdb_backup" => "Zálohování databáze",
"mdb_backup_table" => "Zálohování tabulky",
"mdb_backup_file" => "Záložní soubor",
"mdb_backup_done" => "Hotovo",
"mdb_records" => "záznamů",
"mdb_restore" => "Obnova databáze",
"mdb_restore_table" => "Obnova tabulky",
"mdb_inserted" => "záznamů vloženo",
"mdb_db_restored" => "Databáze obnovena",
"mdb_db_upgraded" => "Databáze upgraded",
"mdb_no_bup_match" => "Soubor se zálohou neodpovídá verzi kalendáře.<br>Database not restored.",
"mdb_events" => "Události",
"mdb_delete" => "smazat",
"mdb_undelete" => "obnovit",
"mdb_between_dates" => "mezi dny",
"mdb_deleted" => "Události smazány",
"mdb_undeleted" => "Události obnoveny",
"mdb_file_saved" => "Záložní soubor uložen na server.",
"mdb_file_name" => "Název souboru",
"mdb_start" => "Start",
"mdb_no_function_checked" => "Nebyla vybrána žádná funkce",
"mdb_write_error" => "Ukládání zálohy selhalo<br>zkontrolujte práva u adresáře 'files/'",

//import/export.php
"iex_file" => "Vybraný soubor",
"iex_file_name" => "Název iCal souboru",
"iex_file_description" => "Název cílového souboru",
"iex_filters" => "Filtry událostí",
"iex_export_usr" => "Export User Profiles",
"iex_import_usr" => "Import User Profiles",
"iex_upload_ics" => "Nahrát iCal soubor",
"iex_create_ics" => "Vytvořit iCal soubor",
"iex_tz_adjust" => "Timezone adjustments",
"iex_upload_csv" => "Nahrát CSV soubor",
"iex_upload_file" => "Nahrát soubor",
"iex_create_file" => "Vytvořit soubor",
"iex_download_file" => "Uložit soubor",
"iex_fields_sep_by" => "Pole oddělena",
"iex_birthday_cat_id" => "ID kategorie narozenin",
"iex_default_grp_id" => "Default user group ID",
"iex_default_cat_id" => "ID výchozí kategorie",
"iex_default_pword" => "Default password",
"iex_if_no_pw" => "If no password specified",
"iex_replace_users" => "Replace existing users",
"iex_if_no_grp" => "if no user group found",
"iex_if_no_cat" => "pokud není nalezena žádná kategorie",
"iex_import_events_from_date" => "Importovat události konané od",
"iex_no_events_from_date" => "No events found as of the specified date",
"iex_see_insert" => "viz vysvětlivky vpravo",
"iex_no_file_name" => "Chybí název souboru",
"iex_no_begin_tag" => "chybný iCal soubor (chybí značka BEGIN)",
"iex_bad_date" => "Bad date",
"iex_date_format" => "Formát data události",
"iex_time_format" => "Formát času události",
"iex_number_of_errors" => "Počet chyb v seznamu",
"iex_bgnd_highlighted" => "pozadí zvýrazněno",
"iex_verify_event_list" => "Prověřte seznam událostí, opravte chyby a klikněte na",
"iex_add_events" => "Přidat události do databáze",
"iex_verify_user_list" => "Verify User List, correct possible errors and click",
"iex_add_users" => "Add Users to Database",
"iex_select_ignore_birthday" => "Zaškrtněte políčka Narozeniny a Smazat jak je potřeba",
"iex_select_ignore" => "Zaškrtněte políčko Smazat pro přeskočení události",
"iex_check_all_ignore" => "Toggle all Ignore boxes",
"iex_title" => "Název",
"iex_venue" => "Místo",
"iex_owner" => "Vlastník",
"iex_category" => "Kategorie",
"iex_date" => "Datum",
"iex_end_date" => "Začátek",
"iex_start_time" => "Čas od",
"iex_end_time" => "Čas do",
"iex_description" => "Popis",
"iex_repeat" => "Repeat",
"iex_birthday" => "Narozeniny",
"iex_ignore" => "Smazat",
"iex_events_added" => "události přidány",
"iex_events_dropped" => "události nebyly přidány (již uloženy)",
"iex_users_added" => "users added",
"iex_users_deleted" => "users deleted",
"iex_csv_file_error_on_line" => "Chyba CSV souboru na řádku",
"iex_between_dates" => "Datum konání mezi",
"iex_changed_between" => "Přidáno/změněno mezi",
"iex_select_date" => "Zvolte datum",
"iex_select_start_date" => "Zvolte počáteční datum",
"iex_select_end_date" => "Zvolte koncové datum",
"iex_group" => "User group",
"iex_name" => "User name",
"iex_email" => "Email address",
"iex_phone" => "Phone number",
"iex_msgID" => "Chat ID",
"iex_lang" => "Language",
"iex_pword" => "Password",
"iex_all_groups" => "all groups",
"iex_all_cats" => "všechny kategorie",
"iex_all_users" => "všichni uživatelé",
"iex_no_events_found" => "Žádná událost nenalezena",
"iex_file_created" => "Soubor byl vytvořen",
"iex_write error" => "Ukládání souboru selhalo<br>Zkontrolujte práva u adresáře 'files/'",
"iex_invalid" => "invalid",
"iex_in_use" => "already in use",

//cleanup.php
"cup_cup_functions" => "Clean Up Functions",
"cup_fill_fields" => "Fill in the date and click Clean Up.",
"cup_found_confirm" => "If items 'to be cleaned up' are found, you will be asked asked for confirmation.",
"cup_evt" => "Events to delete",
"cup_usr" => "User accounts to delete",
"cup_att" => "Attachments to delete",
"cup_rec" => "Recipient lists to delete",
"cup_tns" => "Thumbnails to delete",
"cup_past_events" => "Past events",
"cup_past_users" => "Inactive users",
"cup_att_dir" => "Attachments folder",
"cup_rec_dir" => "Reciplists folder",
"cup_tns_dir" => "Thumbnails folder",
"cup_usr_text" => "Account of users not logged in since",
"cup_evt_text" => "Events which occurred before",
"cup_att_text" => "Attachments not used in events since",
"cup_rec_text" => "Recipients lists not used in events since",
"cup_tns_text" => "Thumbnails not used in events since",
"cup_select_date" => "Select date",
"cup_blank_date1" => "A blank date means: Never logged in.",
"cup_blank_date2" => "A blank date means: Not used at all (orphans).",
"cup_nothing_to_delete" => "Nothing to clean up",
"cup_clean_up" => "Clean Up",
"cup_cancel" => "Cancel",
"cup_delete" => "Delete",
"cup_invalid date" => "Invalid date",
"cup_events_deleted" => "Events deleted",
"cup_accounts_deleted" => "Accounts deleted",
"cup_files_deleted" => "Files deleted",
"cup_important" => "IMPORTANT:",
"cup_deleted_compact" => "Deleted events and user accounts are marked 'deleted', but still take up space.<br> On the Database page these events and accounts can be permanently removed<br>with the Compact function.",
"cup_deleted_files" => "Deleted files are permanently removed from the folders and cannot be recovered!",

//toolsaaf.php
"aff_sel_cals" =>  "Select calendar(s)",
"aff_evt_copied" =>  "Event copied",

//styling.php
"sty_css_intro" =>  "Values specified on this page should adhere to the CSS standards",
"sty_preview_theme" => "Preview Theme",
"sty_preview_theme_title" => "Preview displayed theme in calendar",
"sty_stop_preview" => "Stop Preview",
"sty_stop_preview_title" => "Stop preview of displayed theme in calendar",
"sty_save_theme" => "Save Theme",
"sty_save_theme_title" => "Save displayed theme to database",
"sty_backup_theme" => "Backup Theme",
"sty_backup_theme_title" => "Backup theme from database to file",
"sty_restore_theme" => "Restore Theme",
"sty_restore_theme_title" => "Restore theme from file to display",
"sty_default_luxcal" => "default LuxCal theme",
"sty_close_window" => "Close Window",
"sty_close_window_title" => "Close this window",
"sty_theme_title" => "Theme title",
"sty_general" => "General",
"sty_grid_views" => "Grid / Views",
"sty_hover_boxes" => "Hover Boxes",
"sty_bgtx_colors" => "Background/text colors",
"sty_bord_colors" => "Border colors",
"sty_fontfam_sizes" => "Font family/sizes",
"sty_font_sizes" => "Font sizes",
"sty_miscel" => "Miscellaneous",
"sty_background" => "Background",
"sty_text" => "Text",
"sty_color" => "Color",
"sty_example" => "Example",
"sty_theme_previewed" => "Preview mode - you can now navigate the calendar. Select Stop Preview when done.",
"sty_theme_saved" => "Theme saved to database",
"sty_theme_backedup" => "Theme backed up from database to file:",
"sty_theme_restored1" => "Theme restored from file:",
"sty_theme_restored2" => "Press Save Theme to save the theme to the database",
"sty_unsaved_changes" => "WARNING – Unsaved changes!\\nIf you close the window, the changes will be lost.", //don't remove '\\n'
"sty_number_of_errors" => "Number of errors in list",
"sty_bgnd_highlighted" => "background highlighted",
"sty_XXXX" => "calendar general",
"sty_TBAR" => "calendar top bar",
"sty_BHAR" => "bars, headers and lines",
"sty_BUTS" => "buttons",
"sty_DROP" => "drop-down menus",
"sty_XWIN" => "popup windows",
"sty_INBX" => "insert boxes",
"sty_OVBX" => "overlay boxes",
"sty_BUTH" => "buttons - on hover",
"sty_FFLD" => "form fields",
"sty_CONF" => "confirmation message",
"sty_WARN" => "warning message",
"sty_ERRO" => "error message",
"sty_HLIT" => "text highlight",
"sty_FXXX" => "base font family",
"sty_SXXX" => "base font size",
"sty_PGTL" => "page titles",
"sty_THDL" => "table headers L",
"sty_THDM" => "table headers M",
"sty_DTHD" => "date headers",
"sty_SNHD" => "section headers",
"sty_PWIN" => "popup windows",
"sty_SMAL" => "small text",
"sty_GCTH" => "day cell - hover",
"sty_GTFD" => "cell head 1st day of month",
"sty_GWTC" => "weeknr / time column",
"sty_GWD1" => "weekday month 1",
"sty_GWD2" => "weekday month 2",
"sty_GWE1" => "weekend month 1",
"sty_GWE2" => "weekend month 2",
"sty_GOUT" => "outside month",
"sty_GTOD" => "day cell today",
"sty_GSEL" => "day cell selected day",
"sty_LINK" => "URL and email links",
"sty_CHBX" => "todo check box",
"sty_EVTI" => "event title in views",
"sty_HNOR" => "normal event",
"sty_HPRI" => "private event",
"sty_HREP" => "repeating event",
"sty_POPU" => "hover popup box",
"sty_TbSw" => "top bar shadow (0:no 1:yes)",
"sty_CtOf" => "content offset",

//lcalcron.php
"cro_sum_header" => "SOUHRN ÚLOH CRONU",
"cro_sum_trailer" => "KONEC SOUHRNU",
"cro_sum_title_eve" => "UPLYNULÉ UDÁLOSTI",
"cro_nr_evts_deleted" => "Počet smazaných událostí",
"cro_sum_title_not" => "PŘIPOMÍNKY",
"cro_no_reminders_due" => "No reminder messages due",
"cro_due_in" => "Událost nastane za",
"cro_due_today" => "Dnes",
"cro_days" => "dní",
"cro_date_time" => "Datum / čas",
"cro_title" => "Název",
"cro_venue" => "Místo",
"cro_description" => "Popis",
"cro_category" => "Kategorie",
"cro_status" => "Status",
"cro_none_active" => "No reminders or periodic services active",
"cro_sum_title_use" => "KONTROLA UŽIVATELSKÝCH ÚČTŮ",
"cro_nr_accounts_deleted" => "Počet smazaných účtů",
"cro_no_accounts_deleted" => "Žádný účet nebyl smazán",
"cro_sum_title_ice" => "EXPORTOVANÉ UDÁLOSTI",
"cro_nr_events_exported" => "Počet událostí exportovaných do souboru v formátu iCalendar",

//messaging.php
"mes_no_msg_no_recip" => "Not sent, no recipients found",

//explanations
"xpl_edit" =>
"<h3>Edit Instructions</h3>
<p>This text editor can be used to edit the content of the following files:
<dl>
<dt>info.txt</dt><dd>The information text, which - when enabled on the Settings 
page - is visible in the side panel right next to the calendar page.</dd>
<dt>+recipients.txt</dt><dd>The file with public (not-registered) recipients, 
from which recipients can be selected for reminder messages.</dd>
<dt>&lt;list_name&gt;.txt</dt><dd>One or more lists with recipients, which can 
be added in its entirety to the recipients for reminder messages.</dd>
</dl>
</p>",

"xpl_edit_info_texts" =>
"<h3>Edit Instructions - Information Texts</h3>
<p>When enabled on the Settings page, the information messages in the text area 
on the left will be shown in the calendar views in a side panel right next to 
the calendar page. The messages may contain HTML-tags and inline styles. 
Examples of of the various possibilities of info messages can be found in the file 
'sidepanel/samples/info.txt'.</p>
<p>Information messages can be displayed from a start date till an end date.
Each info message must be preceded by a line with the specified display period 
enclosed by ~ characters. Text before the first line starting with a ~ character 
can be used for your personal notes and will not be shown in the side panel's 
info area.</p><br>
<p>Start and end date format: ~m1.d1-m2.d2~, where m1 and d1 are the start month 
and day and m2 and d2 are the end month and day. If d1 is omitted, the first day 
of m1 is assumed. If d2 is omitted, the last day of m2 is assumed. If m2 and d2 
are omitted, the last day of m1 is assumed.</p>
<p>Examples:<br>
<b>~4~</b>: The whole month of April<br>
<b>~2.10-2.14~</b>: 10 - 14 February<br>
<b>~6-7~</b>: 1 June - 31 July<br>
<b>~12.15-12.25~</b>: 15 - 25 December<br>
<b>~8.15-10.5~</b>: 15 August - 5 October<br>
<b>~12.15~</b>: 15 December - 31 December</p><br>
<p>Suggestion: Start with creating a backup copy (Backup text).</p>",

"xpl_edit_pub_recips" =>
"<h3>Edit Instructions - Public Recipients</h3>
<p>This file can contain a list with public (not registered) recipients from 
which recipients can be copied to the recipients lists for reminder messages.</p>
<p>Each recipient should be specified on a separate line.</p><br>
<p>Depending on the messaging services enabled on the settings page recipients 
can be specified by:</p>
<ul>
<li>email address,</li>
<li>Telegram chat ID,</li>
<li>mobile phone number.</li>
</ul>
<br>
<p>In the file text starting with a #-character and empty lines will be flushed 
and blanks at the start or end of specified recipients will be removed.</p>",

"xpl_edit_recips_list" =>
"<h3>Edit Instructions - Recipients List</h3>
<p>This file can contain a list with public or registered recipients. The file 
can be added in its entirety to the list of recipients for reminder messages.</p>
<p>Each recipient should be specified on a separate line.</p><br>
<p>Depending on the messaging services enabled on the settings page and the user 
account recipients can be specified by:</p>
<ul>
<li>user name,</li>
<li>email address,</li>
<li>Telegram chat ID,</li>
<li>mobile phone number.</li>
</ul>
<br>
<p>In the file text starting with a #-character and empty lines will be flushed 
and blanks at the start or end of specified recipients will be removed.</p>
<p>A new recipients list can be created by changing the file name and selecting 
the Save text button</p>",

"xpl_manage_db" =>
"<h3>Správa databáze, instrukce</h3>
<p>Na této stránce lze provádět následující činnosti:</p>
<h6>Komprimace databáze</h6>
<p>Po smazání události je tato pouze označena jako smazaná, ale zůstává nadále v 
databázi. Komprese databáze trvale odstraní události smazané před více jak 30ti 
dny z databáze a uvolní místo, které zabírají.</p>
<h6>Záloha databáze</h6>
<p>Funkce vytvoří zálohu celé databáze kalendáře (tabulky, strukturu a obsah)
v .sql formátu. Záložní soubor se uloží do adresáře <strong>files/</strong> 
a je pojmenován v následujícím tvaru: 
<kbd>dump-cal-lcv-yyyymmdd-hhmmss.sql</kbd> (kde 'cal' = calendar ID, 'lcv' = 
calendar version a 'yyyymmdd-hhmmss' = rok, měsíc, den, hodina, minuta a 
sekunda).</p>
<p>Záložní soubor lze použít k obnově databáze kalendáře (struktury i údajů) 
pomocí Obnovy databáze popsané dále, nebo s využitím nástroje  
<strong>phpMyAdmin</strong>, který poskytuje většina hostingů.</p>
<h6>Obnova databáze</h6>
<p>Tato funkce obnoví databázi kalendáře do stavu daného obsahem záložního souboru
(typu .sql). See the admin_guide.html section 3 for a detailed explanation.</p>
<p>Při obnově databáze BUDOU VŠECHNA SOUČASNÁ DATA ZTRACENA!</p>
<h6>Události</h6>
<p>Tato funkce smaže nebo obnoví události, které probíhají mezi zadanými daty.
Je-li datum prázdné, není nastaven žádný limit, takže pokud ponecháte obě rozmezí 
prázdné, VŠECNY UDÁLOSTI BUDOU SMAZÁNY!</p>
<p>POZOR: Po kompresi databáze (viz výše), události, které byly trvale smazány 
již nemohou být zpětně obnoveny!</p>",

"xpl_import_csv" =>
"<h3>Instrukce pro CSV import</h3>
<p>Tento formulář se používá pro import textových souborů <strong>Comma Separated Values 
(CSV)</strong> s údaji o událostech do LuxCal kalendáře.</p>
<p>Pořadí sloupců ve vstupním CSV souboru musí být následující: název, místo, id kategorie
(viz dále), datum, koncové datum, počáteční čas, koncový čas, popis. První řádek
CSV souboru s názvy sloupců je při importu ignorován.</p>
<h6>Ukázkové CSV soubory</h6>
<p>Vzorové CSV soubory (s příponou .cvs) jsou uloženy v adresáři 'files/' v instalačním 
balíku.</p>
<h6>Field separator</h6>
The field separator can be any character, for instance a comma, semi-colon, etc.
The field separator character must be unique and may not be part of the text, 
numbers or dates in the fields.
<h6>Formáty data a času</h6>
<p>Zvolený formát data a času událostí musí odpovídat formátu použitému ve vstupním 
CSV souboru.</p>
<p>If no start time (blank) is present, the event will be shown as a 'no time' event 
in the calendar. If the start time is 00:00 or 12:00am, the event will be shown as 
an 'all day' event in the calendar.</p>
<h6>Tabulka kategorií</h6>
<p>Kalendář používá k identifikaci jednotlivých kategorií ID čísla. Tato čísla určující 
kategorie v CSV souboru a následující tabulce si musí odpovídat, nebo musí být v CSV 
vynechána.</p>
<p>Pokud chcete v následující kroku označit události jako 'narozeniny', pak musíte také
nastavit <strong>ID kategorie Narozeniny</strong> na odpovídající ID kategorie níže.</p>
<p class='hired'>Warning: Do not import more than 100 events at a time!</p>
<p>Ve vašem kalendáři jsou definovány tyto kategorie:</p>",

"xpl_import_user" =>
"<h3>User Profile Import Instructions</h3>
<p>This form is used to import a CSV (Comma Separated Values) text file containing 
user profile data into the LuxCal Calendar.</p>
<p>For the proper handling of special characters, the CSV file must be UTF-8 encoded.</p>
<h6>Field separator</h6>
<p>The field separator can be any character, for instance a comma, semi-colon, etc.
The field separator character must be unique 
and may not be part of the text in the fields.</p>
<h6>Default user group ID</h6>
<p>If in the CSV file a user group ID has been left blank, the specified default 
user group ID will be taken.</p>
<h6>Default password</h6>
<p>If in the CSV file a user password has been left blank, the specified default 
password will be taken.</p>
<h6>Replace existing users</h6>
<p>If the replace existing users check-box has been checked, all existing users, 
except the public user and the administrator, will be deleted before importing the 
user profiles.</p>
<br>
<h6>Sample User Profile files</h6>
<p>Sample User profile CSV files (.csv) can be found in the '!luxcal-toolbox/' folder of 
your LuxCal installation.</p>
<h6>Fields in the CSV file</h6>
<p>The order of columns must be as listed below. If the first row of the CSV file 
contains column headers, it will be ignored.</p>
<ul>
<li>User group ID: should correspond to the user groups used in your calendar (see 
table below). If blank, the user will be put in the specified default user group</li>
<li>User name: mandatory</li>
<li>Email address: mandatory</li>
<li>Mobile phone number: optional</li>
<li>Telegram chat ID: optional</li>
<li>Interface language: optional. E.g. English, Dansk. If blank, the default 
language selected on the Settings page will be taken.</li>
<li>Password: optional. If blank, the specified default password will be taken.</li>
</ul>
<p>Blank fields should be indicated by two quotes. Blank fields at the end of each 
row may be left out.</p>
<p class='hired'>Warning: Do not import more than 60 user profiles at a time!</p>
<h6>Table of User Group IDs</h6>
<p>For your calendar, the following user groups have currently been defined:</p>",

"xpl_export_user" =>
"<h3>User Profile Export Instructions</h3>
<p>This form is used to extract and export <strong>User Profiles</strong> from 
the LuxCal Calendar.</p>
<p>Files will be created in the 'files/' directory on the server with the 
specified filename and in the Comma Separated Value (.csv) format.</p>
<h6>Destination file name</h6>
If not specified, the default filename will be 
the calendar name followed by the suffix '_users'. The filename extension will 
be automatically set to <b>.csv</b>.</p>
<h6>User Group</h6>
Only the user profiles of the selected user group will be 
exported. If 'all groups' is selected, the user profiles in the destination file 
will be sorted on user group</p>
<h6>Field separator</h6>
<p>The field separator can be any character, for instance a comma, semi-colon, etc.
The field separator character must be unique 
and may not be part of the text in the fields.</p><br>
<p>Existing files in the 'files/' directory on the server with the same name will 
be overwritten by the new file.</p>
<p>The order of columns in the destination file will be: group ID, user name, 
email address, mobile phone number, interface language and password.<br>
<b>Note:</b> Passwords in the exported user profiles are encoded and cannot be 
decoded.</p><br>
<p>When <b>downloading</b> the exported .csv file, the current date and time will 
be added to the name of the downloaded file.</p><br>
<h6>Sample User Profile files</h6>
<p>Sample User Profile files (file extension .csv) can be found in the '!luxcal-toolbox/' 
directory of your LuxCal download.</p>",

"xpl_import_ical" =>
"<h3>Instrukce pro import iCalendar</h3>
<p>Tento formulář slouží pro import souborů <strong>iCalendar</strong> s událostmi
do kalendáře LuxCal.</p>
<p>Formát souboru musí odpovídat [<u><a href='https://tools.ietf.org/html/rfc5545' 
target='_blank'>standardu RFC5545 </a></u>] Internet Engineering Task Force.</p>
<p>Budou importovány pouze události. Ostatní části iCal souboru, jako jsou úkoly,
žurnál, alarmy, budou při importu ignorovány.</p>
<h6>Ukázkové iCal soubory</h6>
<p>Vzorové soubory iCalendar (s příponou .ics) jsou uloženy v adresáři '!luxcal-toolbox/' 
v instalačním balíku LuxCal.</p>
<h6>Timezone adjustments</h6>
<p>If your iCalendar file contains events in a different timezone and the dates/times 
should be adjusted to the calendar timezone, then check 'Timezone adjustments'.</p>
<h6>Tabulka kategorií</h6>
<p>Kalendář používá k označení kategorií ID čísla. Tato čísla určující 
kategorie v iCal souboru musí odpovídat číslům použitým v kalendáři, nebo musí být v iCal
vynechána.</p>
<p class='hired'>Pozor: Neimportujte najednou více než 100 událostí!</p>
<p>Ve vašem kalendáři jsou definovány tyto kategorie:</p>",

"xpl_export_ical" =>
"<h3>Instrukce pro export iCalendar</h3>
<p>Tento formulář slouží pro export událostí <strong>iCalendar</strong> z LuxCal kalendáře.</p>
<p>Jméno <b>iCal souboru</b> (bez přípony) je volitelné. Takto pojmenované soubory s jsou 
ukládány do adresáře \"files/\" na serveru. Pokud jméno nezadáte, bude pojmenován
 of the calendar. Přípona souboru bude <b>.ics</b>.
Existující soubory v adresáři \"files/\" na serveru se stejným jménem budou přepsány
novým obsahem.
<p> <b>Popis iCal souboru</b> (např. 'Schůzky 2011') je nepovinný. Pokud ho zadáte,
bude vložen do hlavičky exportovaného iCal souboru.</p>
<p><b>filtry událostí</b>: Ukládané události mohou být filtrovány podle:</p>
<ul>
<li>vlastníka události</li>
<li>kategorie události</li>
<li>data začátku</li>
<li>data vložení/poslední změny události</li>
</ul>
<p>Filtry jsou nepovinné, prázdné pole data znamená bez omezení.</p>
<br>
<p>Obsah vytvořeného souboru splňuje 
[<u><a href='https://tools.ietf.org/html/rfc5545' target='_blank'>standard RFC5545</a></u>] 
Internet Engineering Task Force.</p>
<p>Při <b>stahování</b> exportovaného iCal souboru, bude k jeho názvu přidáno datum a čas.</p>
<h6>Ukázkové iCal soubory</h6>
<p>Vzorové soubory iCalendar (s příponou .ics) jsou uloženy v adresáři '!luxcal-toolbox/' 
v instalačním balíku LuxCal.</p>",

"xpl_clean_up" =>
"<h3>Clean Up Instructions</h3>
<p>On this page the following can be cleaned up:</p>
<h6>Past Events</h6>
<p>Events in this calendar with an end date before the specified date will be 
deleted from the calendar. The specified date must be at least one month 
before the date of today.</p>
<h6>Inactive Users</h6>
<p>The accounts of users that have not logged in this calendar since the 
specified date will be removed from the calendar. The specified date must be 
at least one month before the date of today.</p>
<h6>Attachments folder</h6>
<p>Attachment files which are not used in events since the specified date, will 
be deleted. The date must be blank or in the past. In case of multiple calendars, the 
attachment files will be checked against all calendars.</p>
<h6>Reciplists folder</h6>
<p>Recipients list files which are not used in events since the specified date, 
will be deleted. The date must be blank or in the past. In case of multiple calendars, 
the recipients list files will be checked against all calendars.</p>
<h6>Thumbnails folder</h6>
<p>Thumbnail files which are not used in events since the specified date and are not 
used in the side panel's info.txt file, will 
be deleted. The date must be blank or in the past. In case of multiple calendars, the 
thumbnail files will be checked against all calendars.</p>"
);
?>
