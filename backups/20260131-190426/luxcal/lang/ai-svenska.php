<?php
/*
= LuxCal admin interface language file =

Translation to swedish by Christer "Scunder" Nordahl. Please send comments to rb@luxsoft.eu.

This file is part of the LuxCal Web Calendar.
*/


/* -- Admin Interface texts (ai) -- */
$ax = array(

//general
"none" => "Inga",
"no" => "nej",
"yes" => "ja",
"own" => "egna",
"all" => "alla",
"or" => "eller",
"back" => "Tillbaka",
"ahead" => "Framåt",
"close" => "Stäng",
"always" => "alltid",
"at_time" => "kl", //datum och tid avskiljare (t.ex. 30-01-2020 kl 10:45)
"times" => "tider",
"cat_seq_nr" => "kategorisekvens nr",
"rows" => "rad",
"columns" => "kolumner",
"hours" => "timmar",
"minutes" => "minuter",
"user_group" => "användargrupp",
"event_cat" => "händelsekategori",
"email" => "Email",
"telegram" => "Telegram",
"sms" => "SMS",
"id" => "ID",
"username" => "Användarnamn",
"password" => "Lösenord",
"public" => "Offentlig",
"logged_in" => "Inloggad",
"pw_no_chars" => "Characters <, > and ~ not allowed in password",

//settings.php - fieldset headers + general
"set_general_settings" => "Allmänt",
"set_navbar_settings" => "Verktygsfält",
"set_event_settings" => "Händelser",
"set_user_settings" => "Användarkonton",
"set_upload_settings" => "Filuppladdning",
"set_reminder_settings" => "Påminnelser",
"set_perfun_settings" => "Schemalagda funktioner (endast om 'Cron Job' används)",
"set_sidebar_settings" => "Fristående sidopanel (endast vid användning)",
"set_view_settings" => "Visningar",
"set_dt_settings" => "Datum/tid",
"set_save_settings" => "Spara inställningar",
"set_test_mail" => "Epost-test",
"set_mail_sent_to" => "Epost-test skickades till",
"set_mail_sent_from" => "Denna epost-test skickades från din kalenders Inställningssida",
"set_mail_failed" => "Det gick inte att skicka testmail - mottagare(r)",
"set_missing_invalid" => "saknade eller felaktiga inställningar (se markerad text)",
"set_settings_saved" => "Inställningar sparade",
"set_save_error" => "Fel i databas - inställningar ej sparade",
"hover_for_details" => "Peka på rubriker för förklaringar",
"default" => "förinställt",
"enabled" => "aktiverat",
"disabled" => "inaktiverat",
"pixels" => "punkter",
"warnings" => "Varningar",
"notices" => "Lägger märke till",
"visitors" => "Besökare",
"height" => "Height",
"no_way" => "Du har inte behörighet att utföra denna funktion",

//settings.php - general settings.
"versions_label" => "Versioner",
"versions_text" => "• kalenderversion, följt av databasen som används<br>• PHP-version<br>• databasversion",
"calTitle_label" => "Kalendertitel",
"calTitle_text" => "Visas i kalenderns namnlist och i epostmeddelanden.",
"calUrl_label" => "Kalenderns URL (Internet-länk)",
"calUrl_text" => "Kalenderns hemsidesadress.",
"calEmail_label" => "Kalenderns epostadress",
"calEmail_text" => "Epostadressen används för att ta emot kontaktmeddelanden och för att skicka eller ta emot aviseringar via e-post.<br>Format: 'e-post' eller 'namn &#8826;e-post&#8827;'.",
"logoPath_label" => "Sökväg/namn till logotypbild",
"logoPath_text" => "Om det anges kommer en logotypbild att visas i det övre vänstra hörnet av kalendern. Om även en länk till en överordnad sida anges (se nedan), kommer logotypen att vara en hyperlänk till den överordnade sidan. Logotypbilden bör ha en maximal höjd och bredd på 70 pixlar.",
"logoXlPath_label" => "Path/name of log-in logo image",
"logoXlPath_text" => "If specified, a logo image of the specified height will be displayed on the Log In page below the Log In form.",
"backLinkUrl_label" => "Länk till ursprungssida",
"backLinkUrl_text" => "URL till ursprungssida. En 'Tillbaka'-knapp som länkar till angiven plats kommer att visas till vänster i verktygsfältet.<br>Kan användas t.ex. för att användaren lätt ska kunna återvända till den sida Kalendern startades ifrån. Om en sökväg/namn till en logotyp har angivits (se ovan), så kommer ingen Tillbaka-knapp att visas, utan logotypen blir tillbakalänken istället.",
"timeZone_label" => "Tidszon",
"timeZone_text" => "Kalenderns tidszon som används till att beräkna tidpunkter.", 
"see" => "se",
"notifChange_label" => "Skicka meddelande om kalenderändringar",
"notifChange_text" => "När en användare lägger till, redigerar eller tar bort en händelse kommer ett meddelande att skickas till de angivna mottagarna.",
"chgRecipList" => "semicolon separated recipient list",
"maxXsWidth_label" => "Max. bredd på små skärmar",
"maxXsWidth_text" => "För skärmar med en bredd som är mindre än det angivna antalet pixlar kommer kalendern att köras i ett speciellt svarsläge och utelämna vissa mindre viktiga element.",
"rssFeed_label" => "Länkar för RSS-flöde",
"rssFeed_text" => "Om aktiverat: För användare med rättigheter att visa kalendern blir en 'RSS feed link' synlig i kalenderns sidfot, och en länk för RSS-flöde kommer att infogas i kalendersidornas HTML-huvud.",
"logging_label" => "Logga kalenderdata",
"logging_text" => "Kalendern kan logga fel-, varnings-, notismeddelanden och besökardata. Felmeddelanden loggas alltid. Loggning av varnings-, notismeddelanden och besökardata kan var och en inaktiveras eller aktiveras genom att kryssa i de relevanta kryssrutorna. Alla fel-, varnings- och notismeddelanden loggas i filen 'logs/luxcal.log' och besökardata loggas i filerna 'logs/hitlog.log' och 'logs/botlog.log'.<br>Obs: PHP-fel, varningar och meddelanden loggas på en annan plats, bestämt av din internetleverantör.",
"maintMode_label" => "PHP Underhållsläge",
"maintMode_text" => "When enabled, in the PHP scripts data submitted via the note (message) function and data stored in the 'note' variable will be shown in the calendar footer bar.",
"reciplist" => "Mottagarlistan kan innehålla användarnamn, e-postadresser, telefonnummer, Telegram chat IDs och namn på filer med mottagare (omslutna av hakparenteser), separerade med semikolon. Filer med mottagare med en mottagare per rad ska finnas i mappen 'reciplists'. När den utelämnas är standardfiltillägget .txt",
"calendar" => "kalender",
"user" => "användare",
"database" => "databas",

//settings.php - navigation bar settings.
"contact_label" => "Kontaktknapp",
"contact_text" => "Om aktiverat: En kontaktknapp kommer att visas i sidomenyn. Genom att klicka på den här knappen öppnas ett kontaktformulär som kan användas för att skicka ett meddelande till kalenderadministratören.",
"optionsPanel_label" => "Alternativ-menyer",
"optionsPanel_text" => "Visa/dölj menyer under verktygsfältets Alternativ-knapp.<br>• Kalendermenyn (synlig endast för administratör) används för att byta kalender (om flera kalendrar är installerade).<br>• Visa-menyn kan användas för att välja en av kalendervyerna.<br>• Gruppmenyn kan användas för att endast visa händelser skapade av användare i de valda grupperna.<br>• Användarmenyn används för att visa en speciell användares händelser.<br>• Kategorimenyn för att visa en speciell kategori av händelser.<br>• Språkmenyn används för att ändra användargränssnittets språk (om flera språk är installerade).<br>Obs: Om inga menyer är valda, visas inte knappen på alternativpanelen.",
"calMenu_label" => "kalender",
"viewMenu_label" => "vy",
"groupMenu_label" => "grupper",
"userMenu_label" => "användare",
"catMenu_label" => "kategorier",
"langMenu_label" => "språk",
"availViews_label" => "Tillgängliga kalendervyer",
"availViews_text" => "Kalendervyer tillgängliga för offentliga och inloggade användare specificerade med hjälp av en kommaseparerad lista med vynummer. Siffrornas betydelse:<br>1: årsvy<br>2: månadsvy (7 dagar)<br>3: arbetsmånadsvy<br>4: veckovy (7 dagar)<br>5: arbetsveckavy <br>6: dagsvy<br>7: kommande händelsevy<br>8: förändringsvy<br>9: matrisvy (kategorier)<br>10: matrisvy (användare)<br>11: gantt-diagramvy",
"viewButtonsL_label" => "Visa knappar på navigeringsfältet (stor skärm)",
"viewButtonsS_label" => "Visa knappar på navigeringsfältet (liten skärm)",
"viewButtons_text" => "Visa knappar i navigeringsfältet för offentliga och inloggade användare, specificerade med hjälp av en kommaseparerad lista med vynummer.<br>Om ett nummer anges i sekvensen kommer motsvarande knapp att visas. Om inga siffror anges, kommer inga Visa-knappar att visas.<br>Siffrornas betydelse:<br>1: År<br>2: Hel månad<br>3: Arbetsmånad<br>4: Hel vecka<br >5: Arbetsvecka<br>6: Dag<br>7: Kommande<br>8: Förändringar<br>9: Matrix-C<br>10: Matrix-U<br>11: Gantt-diagram<br>The ordningen på siffrorna avgör ordningen på knapparna som visas.<br>Till exempel: '2,4' betyder: visa knapparna 'Hel månad' och 'Hel vecka'.",
"defaultViewL_label" => "Standardvisning vid start (stor skärm)",
"defaultViewL_text" => "Standard kalendervy vid start för offentliga och inloggade användare med stora skärmar.<br>Rekommenderat val: Månad.",
"defaultViewS_label" => "Standardvisning vid start (liten skärm)",
"defaultViewS_text" => "Standard kalendervy vid start för offentliga och inloggade användare som använder små skärmar.<br>Rekommenderat val: Kommande.",
"language_label" => "Förinställt språk för användargränssnittet (public user)",
"language_text" => "For public (not logged in) users the language set for the browser user interface will be used for the calendar as well. If the browser language is not a valid calendar language, this default language will be used.<br>Note: Filerna ui-{språk}.php, ai-{språk}.php, ug-{språk}.php och ug-layout.png ska finnas i lang/ mappen. {språk} = det valda språket till användargränssnittet. Filnamnet ska skrivas med små bokstäver!",
"birthday_cal_label" => "PDF Födelsedagskalender",
"birthday_cal_text" => "Om det är aktiverat, kommer ett alternativ 'PDF-fil - Födelsedag' att visas i sidomenyn för användare med åtminstone 'visa'-rättigheter. Se admin_guide.html - Födelsedagskalender för mer information",
"sideLists_label" => "Approve, Todo, Upcoming lists",
"sideLists_text" => "If enabled, an option to show the respective list will appear in the Side Menu. The 'Events to be approved' list will only be available for users with at least 'manager' rights.",
"toapList_label" => "To approve list",
"todoList_label" => "To do list",
"upcoList_label" => "Upcoming list",

//settings.php - events settings.
"privEvents_label" => "Skapa privata händelser",
"privEvents_text" => "Privata händelser visas bara för användaren som skapade dom.<br>Aktiverat: Användare kan skapa privata händelser.<br>Förinställt: När ny händelse skapas är alternativrutan 'privat' normalt markerad.<br>Alltid: När ny händelse skapas blir den alltid privat och alternativrutan 'privat' i händelsefönstret visas inte.",
"venueInput_label" => "Specifying venues",
"venueInput_text" => "In the Event window specifying a venue can be done either by typing the venue or by selecting a venue from a pre-defined list. If Free text is selected, the user can type the venue, if List is selected the user can select a venue from a drop-down list and when Both is selected, the user can choose between the two.<br> When a drop-down list is used, the 'files' folder must contain a file called venues.txt with one venue per line.",
"timeDefault_label" => "Lägger till nya händelser - tidsstandard",
"timeDefault_text" => "När du lägger till händelser, i händelsefönstret kan standardsättet för händelsetidsfälten visas i händelseformuläret, ställas in på följande sätt:<br>• visa tider: Start- och sluttidfälten visas och är redo att fyllas i<br>• hela dagen: Kryssrutan Hela dagen är markerad, inga start- och sluttidsfält visas<br>• ingen tid: Kryssrutan Ingen tid är markerad, inga start- och sluttidfält visas.",
"evtDelButton_label" => "Visa 'Radera'-knapp i händelsefönstret",
"evtDelButton_text" => "Inaktiverad: 'Radera'-knappen i händelsefönstret visas inte. Användare med rätt att redigera kan ej radera händelser.<br>Aktiverad: 'Radera'-knappen i händelsefönstret visas för alla användare.<br>Administratör: 'Radera'-knappen i händelsefönstret visas endast för användare med administratörs-rättigheter.",
"eventColor_label" => "Händelsers färger baserade på",
"eventColor_text" => "Händelser i de olika kalendervisningarna kan visas i den färg som är kopplad till den grupp till vilken personen som skapade händelsen tillhör, eller i den färg som är kopplad till kategorin.",
"defVenue_label" => "Standardplats",
"defVenue_text" => "I detta textfält kan en plats anges som kommer att kopieras till fältet Plats i evenemangsformuläret när nya evenemang läggs till.",
"xField1_label" => "Extra fält 1",
"xField2_label" => "Extra fält 2",
"xFieldx_text" => "Frivilligt textfält. Om detta fält inkluderas i händelsemallen framöver, kommer fältet (textfält i fritt format) att ingå i händelseformuläret och i händelser som visas i alla kalendervisningar och sidor.<br>• etikett: frivillig textetikett för det extra fältet (max. 15 tecken). Exempelvis 'Epostadress', 'Websida', 'Telefonnummer'.<br>• Minsta användarrättigheter: fältet kommer endast att vara synligt för användare med valda användarrättigheter eller högre.",
"evtWinSmall_label" => "Reducerat händelsefönster",
"evtWinSmall_text" => "När du lägger till/redigerar händelser kommer händelsefönstret att visa en delmängd av inmatningsfälten. För att visa alla fält kan en pil väljas.",
"emojiPicker_label" => "Emoji picker in Event window",
"emojiPicker_text" => "When enabled, in the Event Add/Edit window an emoji picker can be selected to add emoji to the event title and to the description fields.",
"mapViewer_label" => "URL för kartvisning",
"mapViewer_text" => "Om en webbadress för kartvisare har angetts, kommer en adress i evenemangets platsfält omgiven av !-markeringar att visas som en adressknapp i kalendervyerna. När du håller muspekaren på den här knappen kommer textadressen att visas och när du klickar på den öppnas ett nytt fönster där adressen kommer att visas på kartan.<br>Den fullständiga webbadressen till en kartvisare ska anges, till slutet av vilken adressen kan gå med.<br>Exempel:<br>Google Maps: https://maps.google.com/maps?q=<br>OpenStreetMap: https://www.openstreetmap.org/search?query=<br >Om det här fältet lämnas tomt kommer adresserna i fältet Plats inte att visas som en adressknapp.",
"evtDrAndDr_label" => "Event drag and drop",
"evtDrAndDr_text" => "When enabled, in Year view, Month view and in the mini calendar on the side panel, events can be moved or copied from one day to an other day by means of Drag and Drop. If 'manager' is selected, only users with at least manager rights can use this feature. See the admin_guide.html for a detailed description.",
"free_text" => "Free text",
"venue_list" => "Venue list",
"both" => "Both",
"xField_label" => "Etikett",
"show_times" => "visa tider",
"check_ald" => "hela dagen",
"check_ntm" => "ingen tid",
"min_rights" => "Minsta användarrättigheter",
"no_color" => 'ingen färg',
"manager_only" => "administratör",

//settings.php - user accounts settings.
"selfReg_label" => "Självregistrering",
"selfReg_text" => "Tillåt användare att registrera sig själva för att få tillgång till kalendern.<br>Den användargrupp som självregistrerade kommer att tillhöra.",
"selfRegQA_label" => "Självregistrering fråga/svar",
"selfRegQA_text" => "När självregistrering är aktiverat kommer användaren att ställas denna fråga under självregistreringsprocessen och kommer endast att kunna självregistrera sig om rätt svar ges. När frågefältet lämnas tomt kommer ingen fråga att ställas.",
"selfRegNot_label" => "Meddelande om självregistrering",
"selfRegNot_text" => "Skicka ett epostmeddelande till kalenderns epostadress när en självregistrering sker.",
"restLastSel_label" => "Återställ senaste användarval",
"restLastSel_text" => "En användares senaste inställningar på Alternativpanelen sparas, och aktiveras åter vid användarens nästa inloggning. Om användaren inte loggar in under det angivna antalet dagar kommer värdena att gå förlorade.",
"answer" => "svar",
"exp_days" => "dagar",
"view" => "visa",
"post_own" => "spara/redigera egna",
"post_all" => "spara/redigera alla",
"manager" => "spara/administratör",

//settings.php - view settings.
"templFields_text" => "Siffrorna motsvarar:<br>1: Titelfält<br>2: Kategorifält<br>3: Beskrivningsfält<br>4: Extrafält 1 (se nedan)<br>5: Extrafält 2 (se nedan)<br>6: Epostadress (endast om ett meddelande har begärts)<br>7: Datum/tid skapad/ändrad och den eller de användare som sparat händelsen<br>8: Bifogade pdf-, bild- eller videofiler som hyperlänkar.<br>Siffrornas turordning bestämmer fältens visningsföljd.",
"evtTemplate_label" => "Händelse mallar",
"evtTemplate_text" => "Händelsefälten som ska visas i de allmänna kalendervyerna, de kommande händelsevyerna och i hover box med händelsedetaljer kan specificeras med hjälp av en sekvens av nummer.<br>Om ett nummer anges i sekvensen, kommer motsvarande fält att visas.",
"evtTemplPublic" => "Public users",
"evtTemplLogged" => "Logged-in users",
"evtTemplGen" => "Allmän vy",
"evtTemplUpc" => "Kommande vy",
"evtTemplPop" => "Hover box",
"sortEvents_label" => "Sortera händelser på tider eller kategori",
"sortEvents_text" => "I de olika vyerna kan händelser sorteras efter följande kriterier:<br>• händelsetider<br>• händelsekategorins sekvensnummer",
"yearStart_label" => "Startmånad i Årsvisning",
"yearStart_text" => "Om en startmånad har angetts (1-12), kommer Årsvisning alltid att börja med denna månad och visa 12 månader framåt.<br>Anges värdet 0 kommer alltid den aktuella månaden (innehållande visningsdagens datum) att vara den första i visningen.",
"YvRowsColumns_label" => "Antal rader och kolumner i års-visning",
"YvRowsColumns_text" => "Antal rader av månader som ska visas i årsvisningen.<br>Observera! Årsvisningen kan visa mer eller mindre är 1 år. T.ex. är 4 kolumner * 3 rader = 12 månader, medan 4 kolumner * 4 rader = 16 månader.<br>Antal månader som ska visas på varje rad i årsvisning.<br>Rekommenderat val: 3 eller 4.",
"MvWeeksToShow_label" => "Antal veckor i månadsvisning",
"MvWeeksToShow_text" => "Antal veckor som ska visas i månadsvisning.<br>Rekommenderat val: 10, vilket ger 2,5 månader att scrolla igenom.<br>Värdena 0 och 1 har speciella betydelser:<br>0: visa exakt en månad med föregående och följande tomma rutor.<br>1: visa exakt en månad med innehåll i föregående och följande rutor.",
"XvWeeksToShow_label" => "Veckor att visa i matrisvy",
"XvWeeksToShow_text" => "Number of calendar weeks to display in Matrix view.",
"GvWeeksToShow_label" => "Veckor som ska visas i Gantt-diagramvyn",
"GvWeeksToShow_text" => "Antal kalenderveckor som ska visas i Gantt-diagramvyn.",
"workWeekDays_label" => "Arbetsveckodagar",
"workWeekDays_text" => "Dagar färgade som arbetsdagar i kalendervyerna och till exempel för att visas i veckorna i vyn Arbetsmånad och Arbetsvecka.<br>Ange numret för varje arbetsdag.<br>t.ex. 12345: Måndag - fredag<br>Ej angivna dagar anses vara helgdagar.",
"weekStart_label" => "Veckans första dag",
"weekStart_text" => "Ange numret för den första dagen i veckan.",
"lookBackAhead_label" => "Antal dagar framöver",
"lookBackAhead_text" => "Antal dagar som ska visas framöver i visningarna, Kommande händelser, Att-göra lista och i RSS-flöden.",
"searchBackAhead_label" => "Standarddagar för att söka bakåt/framåt",
"searchBackAhead_text" => "När inga datum har angetts på söksidan är dessa standardantalet dagar för att söka bakåt och framåt.",
"dwStartEndHour_label" => "Start- och sluttimme i dag/veckovy",
"dwStartEndHour_text" => "Timmar då en normal dag med evenemang börjar och slutar.<br>T.ex. Om du ställer in dessa värden till 6 och 18 undviks slöseri med utrymme i vecko-/dagvyn för den tysta tiden mellan midnatt och 6:00 och 18:00 och midnatt.<br>Tidsväljaren, som används för att ange en tid, startar också och sluta vid dessa tider.",
"dwTimeSlot_label" => "Tidsintervall i Dag- och Veckovisning",
"dwTimeSlot_text" => "Tidsintervallet och höjden för varje rad (tidsintervall) i visningarna Dag/Vecka.<br>Detta värde avgör tillsammans med Start- och Sluttimma (se ovan) antalet rader i Dag- och Veckovisning.",
"dwTsInterval" => "Tidsintervall",
"dwTsHeight" => "Höjden",
"evtHeadX_label" => "Händelselayout i månads-, vecko- och dagvy",
"evtHeadX_text" => "Mallar med platshållare för händelsefält som ska visas. Följande platshållare kan användas:<br>#ts - starttid<br>#tx - start- och sluttid<br>#e - evenemangstitel<br>#o - evenemangsägare<br>#v - plats<br >#lv - plats med etiketten 'Plats:' framför<br>#c - kategori<br>#lc - kategori med etiketten 'Kategori:' framför<br>#a - ålder (se notering nedan) )<br>#x1 - extra fält 1<br>#lx1 - extra fält 1 med etikett från sidan Inställningar framför<br>#x2 - extra fält 2<br>#lx2 - extra fält 2 med etikett från sidan Inställningar i front<br>#/ - new line<br>Fälten visas i angiven ordning. Andra tecken än platshållarna kommer att förbli oförändrade och kommer att vara en del av den visade händelsen.<br>HTML-taggar är tillåtna i mallen. T.ex. &lt;b&gt;#e&lt;/b&gt;.<br>Den | tecken kan användas för att dela upp mallen i sektioner. Om alla #-parametrar inom en sektion resulterar i en tom sträng, kommer hela sektionen att utelämnas.<br>Obs: Åldern visas om händelsen är en del av en kategori med 'Repeat' inställd på 'varje år ' och födelseåret inom parentes nämns någonstans i händelsens beskrivningsfält or in one of the extra fields.",
"monthView" => "Månadsvy",
"wkdayView" => "Vecko-/Dagvy",
"ownerTitle_label" => "Visa händelseägaren framför händelsetiteln",
"ownerTitle_text" => "Visa händelseägarens namn framför händelsetiteln i de olika kalendervyerna.",
"showSpanel_label" => "Sidopanel i kalendervyer",
"showSpanel_text" => "I kalendervyerna, precis bredvid huvudkalendersidan, kan en sidopanel med följande poster visas:<br>• en minikalender som kan användas för att se bakåt eller framåt utan att ändra datumet för huvudkalendern<br >• en dekorationsbild som motsvarar den aktuella månaden<br>• ett infoområde för att posta meddelanden/meddelanden under angivna perioder.<br>Per artikel kan en kommaseparerad lista med vynummer anges, för vilken sidopanelen ska vara visas.<br>Möjliga visningssiffror:<br>0: alla visningar<br>1: årsvy<br>2: månadsvy (7 dagar)<br>3: arbetsmånadsvy<br>4: veckovy ( 7 dagar)<br>5: arbetsveckovy<br>6: dagsvy<br>7: vy över kommande evenemang<br>8: vy över ändringar<br>9: matrisvy (kategorier)<br>10: matrisvy (användare)<br>11: gantt-diagramvy.<br>Om 'Idag' är markerad kommer sidopanelen alltid att använda dagens datum, annars följer det datumet som valts för huvudkalendern.<br> Se admin_guide.html för information om sidopanelen.",
"spMiniCal" => "Minikalender",
"spImages" => "Bilder",
"spInfoArea" => "Info område",
"spToday" => "Idag",
"topBarDate_label" => "Visa aktuellt datum i den övre raden",
"topBarDate_text" => "Aktivera/inaktivera visningen av det aktuella datumet i kalenderns översta fält i kalendervyerna. Om det visas kan det aktuella datumet klickas för att återställa kalendern till det aktuella datumet.",
"showImgInMV_label" => "Visa i Månadsvy",
"showImgInMV_text" => "Aktiverade/inaktiverade visning av miniatyrbilder i månadsvy",
"urls" => "URL länkar",
"emails" => "e-post länkar",
"monthInDCell_label" => "Månadsnamn i varje cell",
"monthInDCell_text" => "Visa månadsförkortning på varje dag i Månadsvisning",
"scrollDCell_label" => "Use scrollbar in day cells",
"scrollDCell_text" => "If in month view a day cell is too small, rather than increasing the day cell height, a vertical scrollbar will appear.",

//settings.php - date/time settings.
"dateFormat_label" => "Händelsers datumformat (dd mm yyyy)",
"dateFormat_text" => "En textsträng som definierar händelsers datumformat i kalendervisningar och inmatningsfält.<br>Giltiga tecken: y = år, m = månad och d = dag.<br>Icke alfanumeriska tecken kan användas som skiljetecken och visas då exakt som angivits.<br>Exempelvis:<br>y-m-d: 2024-10-31<br>m.d.y: 10.31.2024<br>d/m/y: 31/10/2024",
"dateFormat_expl" => "T.ex. y.m.d: 2024.10.31",
"MdFormat_label" => "Datumformat (dd månad)",
"MdFormat_text" => "En textsträng som definierar datumformat bestående av månad och dag.<br>Giltiga tecken: M = månad i text, d = dag med siffror.<br>Icke alfanumeriska tecken kan användas som skiljetecken och visas då exakt som angivits.<br>Exempelvis:<br>d M: 12 April<br>M, d: Juli, 14",
"MdFormat_expl" => "T.ex. M, d: Juli, 14",
"MdyFormat_label" => "Datumformat (dd månad yyyy)",
"MdyFormat_text" => "En textsträng som definierar datumformat bestående av dag, månad och år.<br>Giltiga tecken: d = dag med siffror, M = månad i text, y = år med siffror.<br>Icke alfanumeriska tecken kan användas som skiljetecken och visas då exakt som angivits.<br>Exempelvis:<br>d M y: 12 April 2024<br>M d, y: Juli 8, 2024",
"MdyFormat_expl" => "T.ex. M d, y: Juli 8, 2024",
"MyFormat_label" => "Datumformat (månad yyyy)",
"MyFormat_text" => "En textsträng som definierar datumformat bestående av månad och år.<br>Giltiga tecken: M = månad i text, y = år med siffror.<br>Icke alfanumeriska tecken kan användas som skiljetecken och visas då exakt som angivits.<br>Exempelvis:<br>M y: April 2024<br>y - M: 2024 - Juli",
"MyFormat_expl" => "T.ex. M y: April 2024",
"DMdFormat_label" => "Datumformat (veckodag dd månad)",
"DMdFormat_text" => "En textsträng som definierar datumformat bestående av veckodag, dag och månad.<br>Giltiga tecken: WD = veckodag i text, M = månad i text, d = dag med siffror.<br>Icke alfanumeriska tecken kan användas som skiljetecken och visas då exakt som angivits.<br>Exempelvis:<br>WD d M: Fredag 12 April<br>WD, M d: Måndag, Juli 14",
"DMdFormat_expl" => "T.ex. WD - M d: Söndag - April 6",
"DMdyFormat_label" => "Datumformat (veckodag dd månad yyyy)",
"DMdyFormat_text" => "En textsträng som definierar datumformat bestående av veckodag, dag, månad och år.<br>Giltiga tecken: WD = veckodag i text, M = månad i text, d = dag med siffror, y = år med siffror.<br>Icke alfanumeriska tecken kan användas som skiljetecken och visas då exakt som angivits.<br>Exempelvis:<br>WD d M y: Fredag 13 April 2024<br>WD - M d, y: Måndag - Juli 16, 2024",
"DMdyFormat_expl" => "T.ex. WD, M d, y: Måndag, Juli 16, 2024",
"timeFormat_label" => "Tidsformat (hh mm)",
"timeFormat_text" => "En textsträng som definierar händelsers tidsformat i kalendervisningar och inmatningsfält.<br>Giltiga tecken: h = timmar, H = timmar med inledande nollor, m = minuter, a = am/pm (frivilligt), A = AM/PM (frivilligt).<br>Icke alfanumeriska tecken kan användas som skiljetecken och visas då exakt som angivits.<br>Exempelvis:<br>h:m: 18:35<br>h.m a: 6.35 pm<br>H:mA: 06:35PM",
"timeFormat_expl" => "T.ex. h:m: 22:35 och h:mA: 10:35PM",
"weekNumber_label" => "Visa veckonummer",
"weekNumber_text" => "Veckonummer kan visas i visningarna för År, Månad och Vecka.",
"time_format_us" => "12-timmar AM/PM",
"time_format_eu" => "24-timmar",
"sunday" => "Söndag",
"monday" => "Måndag",
"time_zones" => "TIDSZONER",
"dd_mm_yyyy" => "dd-mm-yyyy",
"mm_dd_yyyy" => "mm-dd-yyyy",
"yyyy_mm_dd" => "yyyy-mm-dd",

//settings.php - file uploads settings.
"maxUplSize_label" => "Maximal filuppladdnings storlek",
"maxUplSize_text" => "Maximal tillåtna filstorlek när användare laddar upp bifogade filer eller miniatyrfiler.<br>Obs! De flesta PHP-installationer har denna maximala inställning på 2 MB (php_ini-fil) ",
"attTypes_label" => "Bifogade filtyper",
"attTypes_text" => "Komma separerad lista med giltiga bifogade filtyper som kan laddas upp (t.ex. '.pdf,.jpg,.gif,.png,.mp4,.avi')",
"tnlTypes_label" => "Filtyper för miniatyrbilder",
"tnlTypes_text" => "Komma separerad lista med giltiga miniatyrfiler som kan laddas upp (t.ex. '.jpg,.jpeg,.gif,.png')",
"tnlMaxSize_label" => "Miniatyrbild - maximal storlek",
"tnlMaxSize_text" => "Maximal storlek på miniatyrbilder. Om användare laddar upp större miniatyrer kommer miniatyrerna automatiskt att ändras till maximal storlek.<br>Obs! Höga miniatyrer kommer att sträcka ut dagcellerna i månadsvyn, vilket kan resultera i oönskade effekter.",
"tnlDelDays_label" => "Marginal för borttagning av miniatyrbilder",
"tnlDelDays_text" => "Om en miniatyrbild används sedan detta antal dagar sedan kan den inte tas bort.<br>Värdet 0 dagar betyder att miniatyren inte kan tas bort.",
"days" =>"dagar",
"mbytes" => "MB",
"wxhinpx" => "W x H i pixels",

//settings.php - reminders settings.
"services_label" => "Meddelandetjänster",
"services_text" => "Tjänster tillgängliga för skickade händelsepåminnelser. Om en tjänst inte väljs kommer motsvarande sektion i händelsefönstret att döljas. Om ingen tjänst väljs skickas inga händelsepåminnelser.",
"msgLogging_label" => "Notification message logging",
"msgLogging_text" => "When checked, the notification messages sent are logged in the messages.log file. The 'weeks' field specifies how long the logged messages should be kept",
"smsCarrier_label" => "Operatörsmall för SMS",
"smsCarrier_text" => "SMS-operatörsmallen används för att kompilera SMS-gatewayens e-postadress: ppp#sss@carrier, där . . .<br>• ppp: valfri textsträng som ska läggas till före telefonnumret<br>• #: platshållare för mottagarens mobiltelefonnummer (kalendern kommer att ersätta # med telefonnumret)<br>• sss : valfri textsträng som ska infogas efter telefonnumret, t.ex ett användarnamn och lösenord som krävs av vissa operatörer<br>• @: separator tecken<br>• operatör: operatörens adress (t.ex. mail2sms.com)<br>Mallexempel: #@xmobile.com, 0#@carr2.int, #myunmypw@sms.gway.net.",
"smsCountry_label" => "Landskod för SMS",
"smsCountry_text" => "Om SMS-gatewayen finns i ett annat land än kalendern, måste landskoden för det land där kalendern används anges.<br>Välj om prefixet '+' eller '00' krävs .",
"smsSubject_label" => "SMS ämne mall",
"smsSubject_text" => "Om det anges kommer texten i denna mall att kopieras i ämnesfältet för de SMS-e-postmeddelanden som skickas till operatören. Texten kan innehålla tecknet #, som kommer att ersättas av telefonnumret till kalendern eller händelseägaren (beroende på inställningen ovan).<br>Exempel: 'FROMPHONENUMBER=#'.",
"smsAddLink_label" => "Lägg till händelserapportlänk i SMS",
"smsAddLink_text" => "När det är markerat läggs en länk till händelserapporten till varje SMS. Genom att öppna denna länk på sin mobiltelefon kommer mottagarna att kunna se händelsedetaljerna.",
"maxLenSms_label" => "Maximal längd för SMS",
"maxLenSms_text" => "SMS-meddelanden skickas med utf-8 teckenkodning. Meddelanden på upp till 70 tecken kommer att resultera i ett enda SMS-meddelande; meddelanden > 70 tecken, med många Unicode-tecken, kan delas upp i flera meddelanden.",
"calPhone_label" => "Kalenderns telefonnummer",
"calPhone_text" => "Telefonnumret som används som avsändar-ID när du skickar SMS-aviseringsmeddelanden.<br>Format: gratis, max. 20 siffror (vissa länder kräver ett telefonnummer, andra länder accepterar även alfabetiska tecken).<br>Om ingen SMS-tjänst är aktiv eller om ingen SMS-ämnesmall har definierats kan detta fält vara tomt.",
"notSenderEml_label" => "Lägg till fältet 'Svara till' i e-postmeddelandet",
"notSenderEml_text" => "När det är valt kommer e-postmeddelanden att innehålla ett 'Svara till'-fält med e-postadressen till händelseägaren, som mottagaren kan svara på.",
"notSenderSms_label" => "Avsändare av SMS-meddelanden",
"notSenderSms_text" => "När kalendern skickar påminnelse-SMS kan avsändar-ID för SMS-meddelandet vara antingen kalendertelefonnumret eller telefonnumret till användaren som skapade händelsen.<br>Om 'användare' är valt och ett användarkonto har inget telefonnummer angett, kalendertelefonnumret kommer att tas.<br>Om det är användarens telefonnummer kan mottagaren svara på meddelandet.",
"defRecips_label" => "Standardlista över mottagare",
"defRecips_text" => "Om det anges kommer detta att vara standardmottagarelistan för e-post- och/eller SMS-aviseringar i händelsefönstret. Om det här fältet lämnas tomt kommer standardmottagaren att vara händelseägaren.",
"maxEmlCc_label" => "Max. Nr. av mottagare per e-post",
"maxEmlCc_text" => "Normalt tillåter Internetleverantörer ett maximalt antal mottagare per e-post. När du skickar e-post- eller SMS-påminnelser, om antalet mottagare är större än det antal som anges här, kommer e-postmeddelandet att delas upp i flera e-postmeddelanden, var och en med det angivna maximala antalet mottagare.",
"emlFootnote_label" => "Påminnelse e-fotnot",
"emlFootnote_text" => "Text i fritt format som läggs till som ett stycke i slutet av e-postpåminnelser. HTML-taggar är tillåtna i texten.",
"mailServer_label" => "Epost-server",
"mailServer_text" => "PHP epost lämpar sig för oautentiserad epost i små mängder. För större mängder epost eller när det krävs autentisering bör SMTP epost användas.<br>Användande av SMTP epost kräver en SMTP epost-server. Konfigurations-inställningarna för SMTP server måste anges här nedan.",
"smtpServer_label" => "SMTP servernamn",
"smtpServer_text" => "Om SMTP epost är valt ska SMTP servernamn anges här. Till exempel - gmail SMTP server: smtp.gmail.com.",
"smtpPort_label" => "SMTP portnummer",
"smtpPort_text" => "Om SMTP epost är valt ska SMTP portnummer anges här. Till exempel 25, 465 or 587. (Gmail använder portnummer 465.)",
"smtpSsl_label" => "SSL (Secure Sockets Layer)",
"smtpSsl_text" => "Om SMTP epost är valt, välj då här ifall secure sockets layer (SSL) ska vara aktiverat. För gmail: enabled",
"smtpAuth_label" => "SMTP autentisering",
"smtpAuth_text" => "Om SMTP autentisering är valt kommer användarnamn och lösenord specificerat här nedan att användas för att autentisera SMTP epost.<br>För Gmail till exempel, användarnamnet är den del av din e-postadress före @.",
"tlgToken_label" => "Telegram token",
"tlgToken_text" => "Telegram token in the following format: &lt;bot ID&gt;:&lt;bot hash&gt;. For details see installation_guide.html, section Event Notification Messages.",
"cc_prefix" => "Landskoden börjar med prefixet + eller 00",
"weeks" => "Weeks",
"general" => "Allmän",
"php_mail" => "PHP e-post",
"smtp_mail" => "SMTP e-post (fyll i fälten nedan)",

//settings.php - periodic function settings.
"cronHost_label" => "Cron jobbvärd",
"cronHost_text" => "Ange var cron-jobbet är värd vilket med jämna mellanrum startar skriptet 'lcalcron.php'.<br>• lokalt: cron-jobbet körs på samma server<br>• remote: cron-jobbet körs på en fjärrserver eller lcalcron.php startas manuellt (testning)<br>• IP-adress: cron-jobbet körs på en fjärrserver med angiven IP-adress",
"cronSummary_label" => "Admin Cron jobbb sammanställning",
"cronSummary_text" => "Skicka en Cron jobb sammanställning till kalenderns administratör.<br>Endast användbart om ett Cron Job har aktiverats för kalendern.",
"icsExport_label" => "Daglig iCal-export av händelser",
"icsExport_text" => "Alla händelser 1 vecka bakåt i tiden till 1 år framåt kan exporteras i iCalendar format som en .ics fil i 'files' mappen.<br>Filnamnet blir kalenderns namn med blanksteg ersatta av understrykningstecken. Äldre filer ersätts av nya filer.",
"eventExp_label" => "Händelsers förfallodagar",
"eventExp_text" => "Antal dagar efter händelsedatum då händelsen förfaller och raderas.<br>Om antal dagar anges med 0 (eller om inget Cron Job är aktiverat) så kommer inga händelser att raderas.",
"maxNoLogin_label" => "Max antal dagar ej inloggad",
"maxNoLogin_text" => "Om en användare inte varit inloggad x antal dagar kommer dennes konto att raderas.<br>Om antal dagar anges med 0 kommer användarkonton aldrig att raderas.",
"local" => "local",
"remote" => "remote",
"ip_address" => "IP address",

//settings.php - mini calendar / sidebar settings.
"popFieldsSbar_label" => "Händelsefält i sidopanelens inforuta",
"popFieldsSbar_text" => "De händelsefält som ska visas i inforutan när användaren pekar på en händelse i den fristående sidopanelen kan väljas med hjälp av en siffersekvens.<br>Om inga fält väljs visas inte inforutan.",
"showLinkInSB_label" => "Visa länkar i sidopanelen",
"showLinkInSB_text" => "Visa URL:er i händelsers beskrivningsfält som aktiva hyperlänkar i sidopanelens Kommande-visning.",
"sideBarDays_label" => "Antal dagar framöver i sidopanelen",
"sideBarDays_text" => "Ange de antal dagar framåt i tiden som ska visas i sidopanelen.",

//login.php
"log_log_in" => "Logga in",
"log_remember_me" => "Kom ihåg mig",
"log_register" => "Registrera dig",
"log_change_my_data" => "Ändra mina uppgifter", 
"log_save" => "Ändra", 
"log_done" => "Ok",
"log_un_or_em" => "Användarnamn eller E-post",
"log_un" => "Användarnamn",
"log_em" => "E-post",
"log_ph" => "Mobilnummer",
"log_tg" => "Telegram chat ID",
"log_answer" => "Ditt svar",
"log_pw" => "Lösenord",
"log_expir_date" => "Account expiration date",
"log_account_expired" => "This account has expired",
"log_new_un" => "Nytt användarnamn",
"log_new_em" => "Ny e-postadress",
"log_new_pw" => "Nytt lösenord",
"log_con_pw" => "Bekräfta lösenord",
"log_pw_msg" => "Här är dina inloggningsuppgifter för kalendern",
"log_pw_subject" => "Ditt lösenord",
"log_npw_subject" => "Ditt nya lösenord",
"log_npw_sent" => "Ditt nya lösenord har skickats",
"log_registered" => "Registreringen lyckades - ditt lösenord har skickats till dig via e-post.", 
"log_em_problem_not_sent" => "E-postproblem - ditt lösenord kunde inte skickas",
"log_em_problem_not_noti" => "E-postproblem - kunde inte meddela administratören",
"log_un_exists" => "Användarnamnet är upptaget",
"log_em_exists" => "E-postadressen är upptagen",
"log_un_invalid" => "Ogiltigt användarnamn (min. längd 2: A-Z, a-z, 0-9, och _-.) ",
"log_em_invalid" => "Ogiltig epostadress",
"log_ph_invalid" => "Ogiltigt mobilnummer",
"log_tg_invalid" => "Invalid Telegram chat ID",
"log_sm_nr_required" => "SMS: mobile phone number required",
"log_tg_id_required" => "Telegram: chat ID required",
"log_sra_wrong" => "Felaktigt svar på frågan",
"log_sra_wrong_4x" => "Du har svarat fel 4 gånger - försök igen om 30 minuter",
"log_un_em_invalid" => "Användarnamn/e-post är ogiltigt",
"log_un_em_pw_invalid" => "Ditt användarnamn/e-post eller lösenord är ogiltigt",
"log_pw_error" => "Lösenord matchar inte",
"log_no_un_em" => "Ange ditt användarnamn/e-post", 
"log_no_un" => "Ange ditt användarnamn",
"log_no_em" => "Ange din e-postadress",
"log_no_pw" => "Ange ditt lösenord",
"log_no_rights" => "Inloggning avvisades: du har inga visningsrättigheter - Kontakta administratören",//
"log_send_new_pw" => "Skicka nytt lösenord",
"log_new_un_exists" => "Nytt användarnamn är upptaget",
"log_new_em_exists" => "Ny e-postadress är upptagen",
"log_ui_language" => "Användargränssnittets språk",
"log_new_reg" => "Registrera ny användare",
"log_date_time" => "Datum / tid",
"log_time_out" => "Time out",

//categories.php
"cat_list" => "Kategorilista",
"cat_edit" => "Redigera",
"cat_delete" => "Radera",
"cat_add_new" => "Skapa ny kategori",
"cat_add" => "Skapa",
"cat_edit_cat" => "Redigera kategori",
"cat_sort" => "Sortera efter namn",
"cat_cat_name" => "Kategorinamn", 
"cat_symbol" => "Symbol",
"cat_symbol_repms" => "Kategorisymbol (ersätter minirutan)",
"cat_symbol_eg" => "t.ex. A, X, ♥, ⛛",
"cat_matrix_url_link" => "URL länk (visas i matrisvy)",
"cat_seq_in_menu" => "Sekvens i meny",
"cat_cat_color" => "Kategorifärg",
"cat_text" => "Text",
"cat_background" => "Bakgrund",
"cat_select_color" => "Välj färg",
"cat_subcats" => "Under-<br>kategori",
"cat_subcats_opt" => "Antal underkategorier (valfritt)",
"cat_copy_from" => "Kopiera från",
"cat_eml_changes_to" => "Send event changes to",
"cat_url" => "URL",
"cat_name" => "Namn",
"cat_subcat_note" => "Observera att de för närvarande befintliga underkategorierna redan kan användas för evenemang",
"cat_save" => "Spara",
"cat_added" => "Kategori skapad",
"cat_updated" => "Kategori uppdaterad",
"cat_deleted" => "Kategori raderad",
"cat_not_added" => "Kategori ej skapad",
"cat_not_updated" => "Kategori ej uppdaterad",
"cat_not_deleted" => "Kategori ej raderad",
"cat_nr" => "#",
"cat_repeat" => "Repetera",
"cat_every_day" => "varje dag",
"cat_every_week" => "varje vecka",
"cat_every_month" => "varje månad",
"cat_every_year" => "varje år",
"cat_overlap" => "Överlappning<br>tillåten<br>(glipa)",
"cat_need_approval" => "Händelser behöver<br>godkännas",
"cat_no_overlap" => "Ingen överlappning tillåten",
"cat_same_category" => "samma kategori",
"cat_all_categories" => "alla kategori",
"cat_gap" => "glipa",
"cat_ol_error_text" => "Felmeddelande vid överlappning",
"cat_no_ol_note" => "Observera att redan existerande händelser inte kontrolleras och följaktligen kan överlappa varandra",
"cat_ol_error_msg" => "händelseöverlappning - välj en annan tid",
"cat_no_ol_error_msg" => "Överlappnings felmeddelande saknas",
"cat_duration" => "Händelse<br>varaktighet<br>! = fast",
"cat_default" => "standard (ingen sluttid)",
"cat_fixed" => "fixerad",
"cat_event_duration" => "Händelsens varaktighet",
"cat_olgap_invalid" => "Ogiltig överlappnings glipa",
"cat_duration_invalid" => "Ogiltig händelselängd",
"cat_no_url_name" => "URL länknamn saknas",
"cat_invalid_url" => "Ogiltig URL-länk",
"cat_day_color" => "Dagsfärg",
"cat_day_color1" => "Färg på dag (år/matrix vy)",
"cat_day_color2" => "Färg på dag (månad/vecka/dagvy)",
"cat_approve" => "Händelser behöver godkännas",
"cat_check_mark" => "Markeringstecken",
"cat_not_list" => "Notify<br>list",
"cat_label" => "etikett",
"cat_mark" => "markering",
"cat_name_missing" => "Kategorinamn saknas",
"cat_mark_label_missing" => "Markerings-tecken/etikett saknas",

//users.php
"usr_list_of_users" => "Användarlista",
"usr_name" => "Användarnamn",
"usr_email" => "E-post",
"usr_phone" => "Mobilnummer",
"usr_phone_br" => "Mobiltelefon<br>nummer",
"usr_tg_id" => "Telegram chat ID",
"usr_tg_id_br" => "Telegram<br>chat ID",
"usr_not_via" => "Notify via",
"usr_not_via_br" => "Notify<br>via",
"usr_language" => "Språk",
"usr_ui_language" => "Användargränssnitts språk",
"usr_group" => "Grupp",
"usr_password" => "Lösenord",
"usr_expir_date" => "Account expiration date",
"usr_select_exp_date" => "Select expiration date",
"usr_blank_none" => "blank: no expiration",
"usr_expires" => "Expires",
"usr_edit_user" => "Redigera användarprofil",
"usr_add" => "Skapa användare", 
"usr_edit" => "Redigera",
"usr_delete" => "Radera",
"usr_login_0" => "Första inloggning",
"usr_login_1" => "Senaste inloggning",
"usr_login_cnt" => "Inloggningar",
"usr_add_profile" => "Skapa profil",
"usr_upd_profile" => "Uppdatera profil",
"usr_if_changing_pw" => "Bara om lösenordet ska ändras",
"usr_pw_not_updated" => "Lösenord ej uppdaterat",
"usr_added" => "Användare skapad",
"usr_updated" => "Användarprofil uppdaterad",
"usr_deleted" => "Användare raderad",
"usr_not_deleted" => "Användare ej raderad",
"usr_cred_required" => "Användarnamn, epost och lösenord krävs",
"usr_name_exists" => "Användarnamn upptaget",
"usr_email_exists" => "E-postadress upptagen",
"usr_un_invalid" => "Ogiltigt användarnamn (min. längd 2: A-Z, a-z, 0-9, och _-.) ", //
"usr_em_invalid" => "Ogiltig e-postadress",
"usr_ph_invalid" => "Ogiltigt mobiltelefonnummer",
"usr_tg_invalid" => "Invalid Telegram chat ID",
"usr_xd_invalid" => "Invalid account expiration date",
"usr_cant_delete_yourself" => "Du kan inte radera dig själv",
"usr_go_to_groups" => "Gå till Grupper",
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
"grp_list_of_groups" => "Grupplista",
"grp_name" => "Gruppnamn",
"grp_priv" => "Rättigheter",
"grp_categories" => "Kategorier",
"grp_all_cats" => "alla kategorier",
"grp_rep_events" => "Upprepade<br>händelser",
"grp_m-d_events" => "Flerdagars<br>händelser",
"grp_priv_events" => "Privat<br>händelse",
"grp_upload_files" => "Ladda upp<br>filer",
"grp_tnail_privs" => "Miniatyrbild<br>privilegier",
"grp_priv0" => "Ingen behörighet",
"grp_priv1" => "Visa kalender",
"grp_priv2" => "Skapa/redigera egna händelser",
"grp_priv3" => "Skapa/redigera alla händelser",
"grp_priv4" => "Skapa/redigera + administratör",
"grp_priv9" => "Administratör",
"grp_may_post_revents" => "Kan lägga upp återkommande händelser",
"grp_may_post_mevents" => "Kan lägga upp flerdagars händelser",
"grp_may_post_pevents" => "Kan lägga upp privata händelser",
"grp_may_upload_files" => "Får ladda upp filer",
"grp_tn_privs" => "Miniatyr privilegier",
"grp_tn_privs00" => "inga",
"grp_tn_privs11" => "visa alla",
"grp_tn_privs20" => "hantera egna",
"grp_tn_privs21" => "m. egna/v. alla",
"grp_tn_privs22" => "hantera alla",
"grp_edit_group" => "Redigera användargrupp",
"grp_sub_to_rights" => "Med förbehåll för användarrättigheter",
"grp_view" => "Vy",
"grp_add" => "Lägg till",
"grp_edit" => "Redigera",
"grp_delete" => "Radera",
"grp_add_group" => "Skapa grupp",
"grp_upd_group" => "Uppdatera grupp",
"grp_added" => "Grupp skapad",
"grp_updated" => "Grupp uppdaterad",
"grp_deleted" => "Grupp raderad",
"grp_not_deleted" => "Grupp ej raderad",
"grp_in_use" => "Gruppen används för närvarande",
"grp_cred_required" => "Gruppnamn, Rättigheter och Kategorier krävs",
"grp_name_exists" => "Gruppnamn upptaget",
"grp_name_invalid" => "Ogiltigt gruppnamn (min. längd 2: A-Z, a-z, 0-9, and _-.) ",
"grp_background" => "Bakgrundsfärg",
"grp_select_color" => "Välj färg",
"grp_invalid_color" => "Färgformat ogiltigt (#XXXXXX där X = HEX-värde)",
"grp_go_to_users" => "Gå till Användare",

//texteditor.php
"edi_text_editor" => "Redigera Informations Text",
"edi_file_name" => "File name",
"edi_save" => "Spara text",
"edi_backup" => "Säkerhetskopiera text",
"edi_select_file" => "Select file",
"edi_info_text" => "Information text",
"edi_pub_recips" => "Public recipients",
"edi_recips_list" => "Recipients list",
"edi_new_recips_list" => "New recipients list",
"edi_no_file_name" => "No file name specified",
"edi_no_text" => "Det finns ingen text",
"edi_confirm_changes" => "The text changes have not been saved\\nDo you want to continue?", //don't remove '\\n'
"edi_text_saved" => "Text sparad till fil $1",

//database.php
"mdb_dbm_functions" => "Databas-funktioner",
"mdb_noshow_tables" => "Kan ej hämta tabell(er)",
"mdb_noshow_restore" => "Kan ej hitta säkerhetskopia",
"mdb_file_not_sql" => "Säkerhetskopia är ej av typ '.sql'",
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
"mdb_compact" => "Komprimera databas",
"mdb_compact_table" => "Komprimera tabell",
"mdb_compact_error" => "Fel",
"mdb_compact_done" => "Klar",
"mdb_purge_done" => "Raderade händelser är nu permanent borttagna från databasen",
"mdb_backup" => "Säkerhetskopiera databas",
"mdb_backup_table" => "Säkerhetskopiera tabell",
"mdb_backup_file" => "Säkerhetskopia",
"mdb_backup_done" => "Klar",
"mdb_records" => "poster",
"mdb_restore" => "Återställ databas",
"mdb_restore_table" => "Återställ tabell",
"mdb_inserted" => "poster infogade",
"mdb_db_restored" => "Databas återställd",
"mdb_db_upgraded" => "Databas upgraded",
"mdb_no_bup_match" => "Varning:<br>Säkerhetskopia är av annan version än kalendern.<br>Databas återställs inte.",
"mdb_events" => "Händelser",
"mdb_delete" => "radera",
"mdb_undelete" => "återskapa",
"mdb_between_dates" => "som inträffar mellan",
"mdb_deleted" => "Händelser raderade",
"mdb_undeleted" => "Händelser återskapade",
"mdb_file_saved" => "Säkerhetskopia sparad i mappen 'files' på servern.",
"mdb_file_name" => "Filnamn",
"mdb_start" => "Start",
"mdb_no_function_checked" => "Ingen funktion vald",
"mdb_write_error" => "Säkerhetskopiering misslyckades<br>Kontrollera rättigheterna till mappen 'files/'",

//import/export.php
"iex_file" => "Vald fil",
"iex_file_name" => "iCal filnamn",
"iex_file_description" => "iCal filbeskrivning",
"iex_filters" => "Händelsefilter",
"iex_export_usr" => "Exportera användarprofiler",
"iex_import_usr" => "Importera användarprofiler",
"iex_upload_ics" => "Ladda upp iCal-fil",
"iex_create_ics" => "Skapa iCal-fil",
"iex_tz_adjust" => "Tidszons justeringar",
"iex_upload_csv" => "Ladda upp CSV-fil",
"iex_upload_file" => "Ladda upp fil",
"iex_create_file" => "Skapa fil",
"iex_download_file" => "Ladda ner fil",
"iex_fields_sep_by" => "Fält avskiljda med",
"iex_birthday_cat_id" => "Födelsedags kategori-ID",
"iex_default_grp_id" => "Standard användargrupp ID",
"iex_default_cat_id" => "Standard kategori-ID",
"iex_default_pword" => "Standardlösenord",
"iex_if_no_pw" => "Om inget lösenord anges",
"iex_replace_users" => "Ersätt befintliga användare",
"iex_if_no_grp" => "om ingen användargrupp hittas",
"iex_if_no_cat" => "om ingen kategori hittades",
"iex_import_events_from_date" => "Importera händelser som sker fr.o.m.",
"iex_no_events_from_date" => "Inga händelser hittades per det angivna datumet",
"iex_see_insert" => "se instruktioner till höger på sidan",
"iex_no_file_name" => "Filnamn saknas",
"iex_no_begin_tag" => "ogiltig iCal-fil (BEGIN-tag saknas)",
"iex_bad_date" => "Dåligt datum",
"iex_date_format" => "Händelsers datumformat",
"iex_time_format" => "Händelsers tidsformat",
"iex_number_of_errors" => "Antal fel i listan",
"iex_bgnd_highlighted" => "markerad",
"iex_verify_event_list" => "Verifiera händelselista, korrigera fel och klicka",
"iex_add_events" => "Infoga händelser i databasen",
"iex_verify_user_list" => "Verifiera användarlistan, korrigera eventuella fel och klicka",
"iex_add_users" => "Lägg till användare i databasen",
"iex_select_ignore_birthday" => "Markera Ignorera för Födelsedag efter behov",
"iex_select_ignore" => "Markera Ignorera för att ignorera händelse",
"iex_check_all_ignore" => "Markera alla ignorera rutor",
"iex_title" => "Titel",
"iex_venue" => "Plats",
"iex_owner" => "Ägare",
"iex_category" => "Kategori",
"iex_date" => "Datum",
"iex_end_date" => "Slutdatum",
"iex_start_time" => "Starttid",
"iex_end_time" => "Sluttid",
"iex_description" => "Beskrivning",
"iex_repeat" => "Repetition",
"iex_birthday" => "Födelsedag",
"iex_ignore" => "Ignorera",
"iex_events_added" => "händelser skapade",
"iex_events_dropped" => "händelser ignorerade (finns redan)",
"iex_users_added" => "användare har lagts till",
"iex_users_deleted" => "användare raderade",
"iex_csv_file_error_on_line" => "CSV-filfel på rad",
"iex_between_dates" => "Inträffar mellan",
"iex_changed_between" => "Sparad/redigerad mellan",
"iex_select_date" => "Välj datum",
"iex_select_start_date" => "Välj startdatum",
"iex_select_end_date" => "Välj slutdatum",
"iex_group" => "Användargrupp",
"iex_name" => "Användarnamn",
"iex_email" => "E-postadress",
"iex_phone" => "Telefonnummer",
"iex_msgID" => "Chat ID",
"iex_lang" => "Språk",
"iex_pword" => "Lösenord",
"iex_all_groups" => "alla grupper",
"iex_all_cats" => "alla kategorier",
"iex_all_users" => "alla användare",
"iex_no_events_found" => "Inga händelser funna", 
"iex_file_created" => "Fil skapad",
"iex_write error" => "Skapande av exportfil misslyckades<br>Kontrollera rättigheterna till mappen 'files'",
"iex_invalid" => "invalid",
"iex_in_use" => "används redan",

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
"sty_css_intro" =>  "Värden som anges på den här sidan bör följa CSS-standarderna",
"sty_preview_theme" => "Förhandsgranska tema",
"sty_preview_theme_title" => "Förhandsgranska visat tema i kalendern",
"sty_stop_preview" => "Stoppa förhandsgranskning",
"sty_stop_preview_title" => "Stoppa förhandsvisning av visat tema i kalendern",
"sty_save_theme" => "Spara tema",
"sty_save_theme_title" => "Spara visat tema till databasen",
"sty_backup_theme" => "Säkerhetskopiera tema",
"sty_backup_theme_title" => "Säkerhetskopiera tema från databas till fil",
"sty_restore_theme" => "Återställ tema",
"sty_restore_theme_title" => "Återställ tema från fil till skärm",
"sty_default_luxcal" => "default LuxCal theme",
"sty_close_window" => "Stäng fönstret",
"sty_close_window_title" => "Stäng det här fönstret",
"sty_theme_title" => "Tema titel",
"sty_general" => "Allmän",
"sty_grid_views" => "Rutnät / vyer",
"sty_hover_boxes" => "Hover Box",
"sty_bgtx_colors" => "Bakgrund/textfärger",
"sty_bord_colors" => "Kantfärger",
"sty_fontfam_sizes" => "Teckensnittsfamilj/format",
"sty_font_sizes" => "Teckenstorlekar",
"sty_miscel" => "Diverse",
"sty_background" => "Bakgrund",
"sty_text" => "Text",
"sty_color" => "Färg",
"sty_example" => "Exampel",
"sty_theme_previewed" => "Förhandsgranskningsläge - du kan nu navigera i kalendern. Välj Stoppa förhandsgranskning när du är klar.",
"sty_theme_saved" => "Tema sparat i databasen",
"sty_theme_backedup" => "Tema säkerhetskopierat från databas till fil:",
"sty_theme_restored1" => "Temat återställt från fil:",
"sty_theme_restored2" => "Tryck på Spara tema för att spara temat i databasen",
"sty_unsaved_changes" => "VARNING – Osparade ändringar!\\nOm du stänger fönstret kommer ändringarna att gå förlorade.", //don't remove '\\n'
"sty_number_of_errors" => "Antal fel i listan",
"sty_bgnd_highlighted" => "bakgrunden markerad",
"sty_XXXX" => "kalender allmänt",
"sty_TBAR" => "översta fältet i kalendern",
"sty_BHAR" => "staplar, rubriker och linjer",
"sty_BUTS" => "knappar",
"sty_DROP" => "drop-down menyer",
"sty_XWIN" => "popup fönster",
"sty_INBX" => "infoga rutor",
"sty_OVBX" => "överligande rutor",
"sty_BUTH" => "knappar - på hover",
"sty_FFLD" => "formulärfält",
"sty_CONF" => "bekräftelsemeddelande",
"sty_WARN" => "varningsmeddelande",
"sty_ERRO" => "felmeddelande",
"sty_HLIT" => "textmarkering",
"sty_FXXX" => "standard teckensnittsfamilj",
"sty_SXXX" => "standard teckensnitts storlek",
"sty_PGTL" => "sidtitlar",
"sty_THDL" => "tabellrubriker L",
"sty_THDM" => "tabellrubriker M",
"sty_DTHD" => "datumrubriker",
"sty_SNHD" => "avsnittsrubriker",
"sty_PWIN" => "popup-fönster",
"sty_SMAL" => "liten text",
"sty_GCTH" => "dagcell - hover",
"sty_GTFD" => "cellhuvud 1:a dagen i månaden",
"sty_GWTC" => "veckor:nr / tidskolumn",
"sty_GWD1" => "vardag månad 1",
"sty_GWD2" => "vardag månad 2",
"sty_GWE1" => "veckoslut månad 1",
"sty_GWE2" => "veckoslut månad 2",
"sty_GOUT" => "utanför månaden",
"sty_GTOD" => "dagcell idag",
"sty_GSEL" => "dag cell vald dag",
"sty_LINK" => "URL och e-postlänkar",
"sty_CHBX" => "kryssrutan att göra",
"sty_EVTI" => "händelserubrik i vyer",
"sty_HNOR" => "normal händelse",
"sty_HPRI" => "privat händelse",
"sty_HREP" => "upprepande händelse",
"sty_POPU" => "hover popup-ruta",
"sty_TbSw" => "övre bar skugga (0:nej 1:ja)",
"sty_CtOf" => "innehållskompensation",

//lcalcron.php
"cro_sum_header" => "CRON JOBB SAMMANSTÄLLNING",
"cro_sum_trailer" => "SLUT PÅ SAMMANSTÄLLNING",
"cro_sum_title_eve" => "FÖRFALLNA HÄNDELSER",
"cro_nr_evts_deleted" => "Antal raderade händelser",
"cro_sum_title_not" => "MEDDELANDEN",
"cro_no_reminders_due" => "Inga aktuella meddelandedatum",
"cro_due_in" => "Sker om",
"cro_due_today" => "Sker idag",
"cro_days" => "dag(ar)",
"cro_date_time" => "Datum / tid",
"cro_title" => "Titel", 
"cro_venue" => "Plats",
"cro_description" => "Beskrivning",
"cro_category" => "Kategori",
"cro_status" => "Status",
"cro_none_active" => "Inga påminnelser eller periodiska tjänster aktiva",
"cro_sum_title_use" => "FÖRFALLNA ANVÄNDARKONTON",
"cro_nr_accounts_deleted" => "Antal raderade konton",
"cro_no_accounts_deleted" => "Inga konton raderade",
"cro_sum_title_ice" => "EXPORTERADE HÄNDELSER",
"cro_nr_events_exported" => "Antal händelser exporterade i iCalendar-format till fil",

//messaging.php
"mes_no_msg_no_recip" => "Ej skickat, inga mottagare hittades",

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
"<h3>Redigera Instruktioner - Informationsmeddelanden</h3>
<p>När det är aktiverat på sidan Inställningar visas informationsmeddelanden i textområdet
till vänster kommer att visas i kalendervyerna i en sidopanel precis bredvid
kalendersidan. Meddelanden kan innehålla HTML-taggar och inline-stilar. 
Examples of of the various possibilities of info messages can be found in the file 
'sidepanel/samples/info.txt'.</p>
<p>Informationsmeddelanden kan visas från ett startdatum till ett slutdatum.
Informationsmeddelanden kan visas från ett startdatum till ett slutdatum. Text före den första raden som börjar med ett ~-tecken
kan användas för dina personliga anteckningar och kommer inte att visas i sidopanelen
info område.</p><br>
<p>Start- och slutdatumformat: ~m1.d1-m2.d2~, där m1 och d1 är startmånaden
och dag och m2 och d2 är slutmånaden och dag. Om d1 utelämnas, första dagen
av m1 antas. Om d2 utelämnas antas sista dagen av m2. Om m2 och d2
utelämnas, antas sista dagen av m1.</p>
<p>Exempel:<br>
<b>~4~</b>: Hela april månad<br>
<b>~2.10-2.14~</b>: 10 - 14 Februari<br>
<b>~6-7~</b>: 1 Juni - 31 Juli<br>
<b>~12.15-12.25~</b>: 15 - 25 December<br>
<b>~8.15-10.5~</b>: 15 Augusti - 5 Oktober<br>
<b>~12.15~</b>: 15 December - 31 December</p><br>
<p>Förslag: Börja med att skapa en säkerhetskopia (Säkerhetskopieringstext).</p>",

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
"<h3>Instruktioner för att hantera databas</h3>
<p>På denna sida kan följande funktioner väljas:</p>
<h6>Komprimera databas</h6>
<p>När en användare raderar en händelse markeras händelsen som 'raderad', men 
avlägsnas INTE från databasen. Komprimera-funktionen avlägsnar däremot helt 
och hållet händelser som är raderade av en användare för mer än 30 dagar sedan, 
och frigör därigenom utrymmet i databasen reserverat för dessa händelser.</p>
<h6>Säkerhetskopiera databas</h6>
<p>Denna funktion skapar en säkerhetskopia av kalenderns databas (struktur och 
innehåll) i .sql-format. (OBS! Endast de tabeller som tillhör LuxCal kalendern 
berörs.) 
Säkerhetskopian sparas i mappen <strong>files/</strong> med filnamnet: 
<kbd>dump-cal-lcv-yyyymmdd-hhmmss.sql</kbd> (där 'cal' = calendar ID, 'lcv' = 
calendar version och 'yyyymmdd-hhmmss' = år, månad, dag, timmar, minuter och 
sekunder).</p>
<p>Säkerhetskopian kan användas för att återskapa kalenderns databas-tabeller 
(struktur och innehåll) med hjälp av 'Återställ databas' (se nedan) eller genom 
att t.ex. använda <strong>phpMyAdmin</strong>-verktyget som de flesta webbhotell 
tillhandahåller för sina kunder.</p>
<h6>Återställ databas</h6>
<p>Denna funktion återställer kalenderns databas-tabeller (struktur och innehåll) 
med hjälp av en sparad säkerhetskopia (i .sql-format).</p>
<p>Vid återställande av databas kommer ALL DATA SOM I ÖGONBLICKET ÄR SPARADE I 
KALENDERNS TABELLER ATT RADERAS och ersättas med säkerhetskopians innehåll!</p>
<h6>Radera/Återskapa händelser</h6>
<p>Denna funktion raderar eller återskapar händelser som inträffar mellan de 
angivna datumen. Om ett datum utelämnas finns det ingen datumgräns, så om båda 
datum utelämnas KOMMER ALLA HÄNDELSER ATT RADERAS!</p><br>
<p>VIKTIGT: När databasen komprimeras (se ovan) kommer de 'raderade' 
händelserna att helt och hållet avlägsnas, och kan aldrig återskapas igen!</p>",

"xpl_import_csv" =>
"<h3>Instruktioner för import av CSV</h3>
<p>Detta formulär används för att importera en CSV (Comma Separated Values) textfil med 
händelsedata till kalendern.</p>
<p>Ordningen på kolumnerna i CSV-filen måste vara: titel, plats, kategori-id (se nedan), 
datum, slutdatum, starttid, sluttid och beskrivning. Om den första raden i CSV-filen 
består av kolumnrubriker ignoreras denna.</p>
<p>För korrekt behandling av internationella och speciella tecken måste CSV-filen vara 
sparad i UTF-8 teckenkod.</p>
<h6>CSV exempelfiler</h6>
<p>CSV exempelfiler med filändelsen .cvs finns i mappen 'files' i din LuxCal-
installation.</p>
<h6>Fält separator</h6>
Fältavgränsaren kan vara vilket tecken som helst, till exempel kommatecken, semikolon, etc.
Fältavgränsaren måste vara unik och får inte vara en del av texten,
siffror eller datum i fälten.
<h6>Datum- och tidsformat</h6>
<p>Den valda händelsens datum- och tidsformat till vänster måste överensstämma med 
formatet på datum och tider i den uppladdade CSV-filen.</p>
<p>If no start time (blank) is present, the event will be shown as a 'no time' event 
in the calendar. If the start time is 00:00 or 12:00am, the event will be shown as 
an 'all day' event in the calendar.</p>
<h6>Lista med Kategorier</h6>
<p>Kalendern använder ID-nummer för att ange kategorier. CSV-filens kategori-ID:n 
måste motsvara de kategorier som används i din kalender eller vara tomma.</p>
<p>Om du i nästa steg vill öronmärka händelser som 'födelsedag' måste <strong>
Födelsedagens kategori-ID</strong> vara satt till att motsvara samma ID 
i kategorin-listan nedan.</p>
<p class='hired'>Varning: Importera aldrig mer än 100 händelser åt gången!</p>
<p>För närvarande har följande kategorier definierats i din kalender:</p>", 

"xpl_import_user" =>
"<h3>Instruktioner för import av användarprofil</h3>
<p>Detta formulär används för att importera en CSV (komma separerade värden) textfil som innehåller
användarprofildata till LuxCal-kalendern.</p>
<p>För korrekt hantering av specialtecken måste CSV-filen vara UTF-8-kodad.</p>
<h6>Fältavskiljare</h6>
<p>Fältavgränsaren kan vara vilket tecken som helst, till exempel kommatecken, semikolon, etc.
Fältavgränsaren måste vara unik
och kanske inte ingår i texten i fälten.</p>
<h6>Standard användargrupp-ID</h6>
<p>Om ett användargrupps-ID har lämnats tomt i CSV-filen, är den angivna standardinställningen
användargrupps-ID kommer att tas.</p>
<h6>Standardlösenord</h6>
<p>Om ett användarlösenord har lämnats tomt i CSV-filen, är den angivna standardinställningen
lösenord kommer att tas.</p>
<h6>Ersätt befintliga användare</h6>
<p>Om kryssrutan ersätt befintliga användare har markerats, kommer alla befintliga användare,
förutom den offentliga användaren och administratören, kommer att raderas innan importen
användarprofiler.</p>
<br>
<h6>Exempel på användarprofil filer</h6>
<p>Exempel på användarprofil CSV-filer (.csv) finns i mappen '!luxcal-toolbox/' i
din LuxCal-installation.</p>
<h6>Fält i CSV-filen</h6>
<p>Kolumnernas ordning måste vara enligt listan nedan. Om den första raden i CSV-filen
innehåller kolumnrubriker, kommer den att ignoreras.</p>
<ul>
<li>Användargrupps-ID: bör motsvara de användargrupper som används i din kalender (se
tabell nedanför). Om tomt, kommer användaren att placeras i den angivna standardanvändargruppen</li>
<li>Användarnamn: obligatoriskt</li>
<li>E-postadress: obligatorisk</li>
<li>Mobilnummer: valfritt</li>
<li>Telegram chat ID: valfritt</li>
<li>Gränssnittsspråk: valfritt. T.ex. engelska, danska. Om tom, standard
språk som valts på sidan Inställningar kommer att användas.</li>
<li>Lösenord: valfritt. Om tomt, kommer det angivna standardlösenordet att tas.</li>
</ul>
<p>Tomma fält ska anges med två citattecken. Tomma fält i slutet av varje
rad kan utelämnas</p>
<p class='hired'>Varning: Importera inte mer än 60 användarprofiler åt gången!</p>
<h6>Tabell över användargrupps-ID</h6>
<p>För din kalender har följande användargrupper för närvarande definierats:</p>",

"xpl_export_user" =>
"<h3>Exportinstruktioner för användarprofil</h3>
<p>Det här formuläret används för att extrahera och exportera <strong>Användarprofiler</strong> från
LuxCal-kalendern.</p>
<pFiler kommer att skapas i katalogen 'files/' på servern med
angivet filnamn och i formatet kommaseparerat värde (.csv).</p>
<h6>Destinationsfilens namn</h6>
Om det inte anges kommer standardfilnamnet att vara
kalendernamnet följt av suffixet '_users'. Filnamnstillägget kommer
ställas in automatiskt på <b>.csv</b>.</p>
<h6>Användargrupp</h6>
Endast användarprofilerna för den valda användargruppen kommer att
exporteras. Om 'alla grupper' är valt, kommer användarprofilerna i målfilen
att sorteras på användargrupp</p>
<h6>Fältavskiljare</h6>
<p>Fältavgränsaren kan vara vilket tecken som helst, till exempel kommatecken, semikolon, etc.
Fältavgränsaren måste vara unik
och inte ingå i texten i fälten.</p><br>
<p>Befintliga filer i katalogen 'files/' på servern med samma namn kommer att
skrivas över av den nya filen.</p>
<p>Ordningen på kolumner i destinationsfilen kommer att vara: grupp-ID, användarnamn,
e-postadress, mobiltelefonnummer, gränssnittsspråk och lösenord.<br>
<b>Obs:</b> Lösenord i de exporterade användarprofilerna är kodade och kan inte
avkodas.</p><br>
<p>När du <b>laddar ner</b> den exporterade .csv-filen kommer det aktuella datumet och tiden
läggas till i namnet på den nedladdade filen.</p><br>
<h6>Exempel på användarprofil filer</h6>
<p>Exempel på användarprofil filer (filtillägget .csv) finns i 'filer/'
katalogen för din LuxCal-nedladdning.</p>",

"xpl_import_ical" =>
"<h3>Instruktioner för import av iCalendar</h3>
<p>Detta formulär används för att importera en <strong>iCalendar</strong> händelsefil 
till kalendern.</p>
<p>Innehållet i filen måste motsvara [<u><a href='https://tools.ietf.org/html/rfc5545' 
target='_blank'>RFC5545 standard</a></u>] av Internet Engineering Task Force.</p>
<p>Endast händelser importeras. Andra iCal-komponenter som t.ex: Att-Göra, Journal, Ledig / 
Upptagen, Tidszon och Påminnelser kommer att ignoreras.</p>
<h6>iCal exempelfiler</h6>
<p>iCal exempelfiler med filändelsen .ics finns i mappen 'files' i din LuxCal-
installation.</p>
<h6>Tidszons justeringar</h6>
<p>Om din iCalendar-fil innehåller händelser i en annan tidszon och datum/tider
bör de justeras till kalenderns tidszon, kontrollera sedan 'Tidszons justeringar'.</p>
<h6>Kategoritabell</h6>
<p>Kalendern använder ID-nummer för att ange kategorier. iCalendar-filens 
kategori-ID:n måste motsvara de kategorier som används i din kalender eller 
vara tomma .</p>
<p class='hired'>Varning: Importera aldrig mer än 100 händelser åt gången!</p>
<p>För närvarande har följande kategorier definierats i din kalender:</p>", 

"xpl_export_ical" =>
"<h3>Instruktioner för export av iCalendar</h3>
<p>Detta formulär används för att extrahera och exportera <strong>iCalendar</strong>
-händelser från kalendern.</p>
<p>Filerna sparas i mappen 'files/' på servern. Ange filnamn utan filtillägg 
(filtillägget blir automatiskt <b>.ics</b>). Om inget filnamn anges får filen 
automatiskt samma namn som kalendern. Existerande filer med samma namn kommer 
att skrivas över av den nya filen.</p>
<p><b>iCal-filens beskrivning</b> (t.ex. 'Möten 2024') är valfritt. Om du anger 
den så läggs den till i sidhuvudet på den exporterade iCal-filen.</p>
<p><b>Händelsefilter</b>: Händelserna som extraheras kan filtreras genom:</p>
<ul>
<li>händelse ägare</li>
<li>händelse kategori</li>
<li>händelse startdatum</li>
<li>händelse sparad/redigerad-datum</li>
</ul>
<p>Varje filter är valfritt. Utelämnat datum avser: ingen gräns</p>
<br>
<p>Innehållet i filen med extraherade händelser måste motsvara 
[<u><a href='https://tools.ietf.org/html/rfc5545' target='_blank'>RFC5545 standard</a></u>] 
av Internet Engineering Task Force.</p>
<p>När nedladdning sker av den exporterade iCal-file kommer datum och tid att läggas till 
i namnet på den nedladdade filen.</p>
<h6>iCal exempelfiler</h6>
 <p>iCalendar exempelfiler med filändelsen .ics finns i mappen 'files' i din LuxCal-
installation.</p>",

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
