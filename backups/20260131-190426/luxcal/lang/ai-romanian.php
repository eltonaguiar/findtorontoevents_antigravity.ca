<?php
/*
= LuxCal admin interface language file = ROMANIAN / ROMÂNĂ

Traducerea în limba română realizată de Laurențiu Florin Bubuianu (laurfb@gmail.com - laurfb.tk).
This file has been translated in română by Laurențiu Florin Bubuianu (laurfb@gmail.com - laurfb.tk).

This file has been produced by LuxSoft. Please send comments / improvements to rb@luxsoft.eu.
This file is part of the LuxCal Web Calendar.
*/

$ax = array(

//general
"none" => "Niciunul",
"no" => "nu",
"yes" => "da",
"own" => "propriu",
"all" => "Toate",
"or" => "sau",
"back" => "Înapoi",
"ahead" => "Înainte",
"close" => "Închide",
"always" => "întotdeauna",
"at_time" => "/", //separator dată și timp (ex. 30-01-2020 @ 10:45)
"times" => "timp",
"cat_seq_nr" => "nr. secvență categorie",
"rows" => "rânduri",
"columns" => "coloane",
"hours" => "ore",
"minutes" => "minute",
"user_group" => "paletă utilizator",
"event_cat" => "paletă categorie",
"email" => "Email",
"telegram" => "Telegram",
"sms" => "SMS",
"id" => "ID",
"username" => "Nume utilizator",
"password" => "Parola",
"public" => "Public",
"logged_in" => "Autentificat",
"pw_no_chars" => "Caracterele <, > și ~ nu sunt permise în parolă",

//settings.php - fieldset headers + general
"set_general_settings" => "Setări generale",
"set_navbar_settings" => "Meniu",
"set_event_settings" => "Evenimente",
"set_user_settings" => "Setări utilizator",
"set_upload_settings" => "Încărcare fișier",
"set_reminder_settings" => "Memento",
"set_perfun_settings" => "Funcții periodice (relevant doar dacă folosiți cron)",
"set_sidebar_settings" => "Bară laterală evenimente (relevant doar dacă este folosită)",
"set_view_settings" => "Setări vizualizare",
"set_dt_settings" => "Setări Dată/Oră",
"set_save_settings" => "Salvare setări",
"set_test_mail" => "Test email",
"set_mail_sent_to" => "Email de test trimis către",
"set_mail_sent_from" => "Acest email de test a fost trimis din pagina Setări a Calendarului",
"set_mail_failed" => "Eroare trimitere email de test - către",
"set_missing_invalid" => "setări lipsă sau incorecte (sunt marcate)",
"set_settings_saved" => "Setările au fost salvate",
"set_save_error" => "Eroare Bază de date - Setările nu au putut fi salvate",
"hover_for_details" => "Detalii setări Calendar",
"default" => "implicit",
"enabled" => "activ",
"disabled" => "inactiv",
"pixels" => "pixeli",
"warnings" => "Atenționare",
"notices" => "Notă",
"visitors" => "Vizitatori",
"height" => "Height",
"no_way" => "Nu sunteți autorizat să efectuați această operațiune",

//settings.php - general settings.
"versions_label" => "Versiune",
"versions_text" => "• versiune Calendar, urmată de baza de date în uz<br>• Versiune PHP<br>• versiune bază de date",
"calTitle_label" => "Titlu",
"calTitle_text" => "Titlul Calendarului (utilizat și în emailul de notificare).",
"calUrl_label" => "URL Calendar",
"calUrl_text" => "Adresa web, completă, a Calendarului.",
"calEmail_label" => "Adresa de email",
"calEmail_text" => "Adresa de email folosită pentru contacte sau pentru mesajele de notificare.<br><b>Format</b>: 'email' sau 'nume &#8826;email&#8827;'",
"logoPath_label" => "Calea/numele imaginii logo",
"logoPath_text" => "Dacă este specificată, imaginea (logoul) va fi afișată în colțul din stânga sus al Calendarului. Dacă ați specificat și un hyper-link către o pagină părinte (vezi mai jos) logoul va permite și saltul la această pagină. Dimensiunea maximă acceptatîă a logoului este de 70x70 pixeli.",
"logoXlPath_label" => "Path/name of log-in logo image",
"logoXlPath_text" => "If specified, a logo image of the specified height will be displayed on the Log In page below the Log In form.",
"backLinkUrl_label" => "Link către pagina părinte",
"backLinkUrl_text" => "URL-ul paginii părinte. Dacă introduceți aici o adresă URL, suplimentar, în partea stângă a barei meniu a Calendarului, va fi afișat un buton <b>Înapoi</b> care vă permite întoarcerea rapidă la pagina părinte (pagina de unde a fost lansat Calendarul). Dacă ați specificat și o imagine/logo (vezi mai sus) butonul <b>Înapoi</b> va fi înlocuit cu această imagine.",
"timeZone_label" => "Fus orar",
"timeZone_text" => "Fusul orar folosit pentru afișarea orei curente.",
"see" => "vezi",
"notifChange_label" => "Activare trimitere notificări la modificarea setărilor Calendarului",
"notifChange_text" => "Dacă opțiunea este activă, când un utilizator adaugă, editează sau șterge un eveniment, un mesaj de notificare automat va fi trimis către destinatarii specificați în lista de adrese.",
"chgRecipList" => "semicolon separated recipient list",
"maxXsWidth_label" => "Lățimea maximă a ecranului",
"maxXsWidth_text" => "Pentru ecrane cu lățimea inferioară celei specificate, Calendarul va rula în modul responsive, putând lăsa, eventual, în afara zonei de afișare, anumite elemente mai puțin importante.",
"rssFeed_label" => "Flux RSS",
"rssFeed_text" => "<b>Activ</b>: Pentru utilizatorii care au cel puțin drepturi de 'vizualizare' un link pentru fluxul RSS va fi vizibil la baza Calendarului iar un altul va fi adăugat și la începutul codului HTML al paginilor Calendarului.",
"logging_label" => "Log date Calendar",
"logging_text" => "Calendarul poate salva în fișiere log erorile, mesajele de atenționare, alte mesaje diverse, date despre vizitatori etc. Erorile vor fi întotdeauna scrise în log, în timp ce restul datelor, mesajele de atenționare, date vizitatori etc. pot fi activate/dezactivate la salvare în mod independent. Locația fișierului de log pentru erori, mesaje etc. este 'logs/luxcal.log' iar a celor cu date despre vizitatori este 'logs/hitlog.log' și 'logs/botlog.log'.<br><b>Notă</b>: Erorile PHP sistem, mesajele de eroare și notele proprii sistemului vor fi salvate într-o locație distinctă, specifică ISP-ului dumneavoastră.",
"maintMode_label" => "PHP Mod mentenanță",
"maintMode_text" => "Când este activată, in the PHP scripts data submitted via the note (message) function and data stored in the 'note' variable will be shown in the calendar footer bar.",
"reciplist" => "Lista poate conține nume, adrese de email, numere de telefon, Telegram chat IDs, sau nume de fișiere cu adrese (încadrate prin paranteze pătrate), separate prin punct și virgulă. Fișierele, care vor avea obligatoriu doar câte o înregistrare pe linie, vor fi salvate în folderul 'reciplists'. Dacă nu este specificată, extensia implicită a fișierului este  .txt",
"calendar" => "calendar",
"user" => "utilizator",
"database" => "bază de date",

//settings.php - navigation bar settings.
"contact_label" => "Buton contact",
"contact_text" => "Când opțiunea este activă, un buton de Contact va fi afișat în meniul lateral. Utilizarea butonul determină deschiderea unei ferestre care poate fi utilizată pentru trimiterea unui mesaj către administratorul Calendarului.",
"optionsPanel_label" => "Elemente în meniul Opțiuni",
"optionsPanel_text" => "Activează/dezactivează modurile de afișare din meniul Opțiuni.<br>• Meniul calendarului permite administratorului să schimbe rapid calendarul activ. (util doar dacă sunt instalate mai multe calendare simultan)<br>• Opțiunea Grupuri a meniului permite afișarea selectivă a evenimentelor create de utilizatorii din grupul selectat.<br>• Opțiunea Utilizatori a meniului poate fi folosită pentru afișarea selectivă a evenimentelor corespunzătoare utilizatorului selectat.<br>• Opțiunea Categorie a meniului poate fi folosită similar pentru afișarea selectivă doar a anumitor categorii de evenimente.<br>• Meniul de selecție al limbii permite definirea limbii de afișare a calendarului (doar dacă calendarul are mai multe fișiere de limbă instalate)",
"calMenu_label" => "calendar",
"viewMenu_label" => "vedere",
"groupMenu_label" => "grupuri",
"userMenu_label" => "utilizatori",
"catMenu_label" => "categorie",
"langMenu_label" => "limbă",
"availViews_label" => "Vederi disponibile",
"availViews_text" => "Vederile calendarului disponibile public sau utilizatorilor autentificați reprezentate printr-o listă de numere, separate prin virgulă. Semnificația numerelor:<br>1: vedere anuală<br>2: afișare lunără (7 zile)<br>3: afișarea lunii curente<br>4: afișare săptămânală (7 zile)<br>5: săptămâna curentă<br>6: afișare pe zile<br>7: afișarea evenimentelor următoare<br>8: afișarea modificărilor<br>9: afișare matricială (categorii)<br>10: afișare matricială (utilizatori)<br>11: afișare tabel Gantt.",
"viewButtonsL_label" => "Afișare butoane în bara de navigare (ecran extins)",
"viewButtonsS_label" => "Afișare butoane în bara de navigare (ecrane mici)",
"viewButtons_text" => "Afișarea butoanelor de navigare pentru public și pentru utilizatorii autentificați, într-o formă specificată printr-o listă de numere.<br>Dacă un număr apare în listă, butonul corespunzător va fi afișat. Dacă nu se specifică niciun număr - niciun buton de vizualizare nu va fi afișat.<br>Semnificația numerelor:<br>1: An<br>2: Întreaga lună<br>3: Luna curentă<br>4: Întreaga săptămână<br>5: Săptămâna curentă<br>6: Zi<br>7: Care urmează<br>8: Modificări<br>9: Matricial-C<br>10: Matricial-U<br>11: Gantt Chart<br>Ordinea  numerelor determină modul de afișare al butoanelor.<br>Spre exemplu: '2,4' înseamnă că vor fi afișate butoanele 'Întreaga lună' și 'Întreaga săptămână'.",
"defaultViewL_label" => "Mod inițial vizualizare (ecran extins)",
"defaultViewL_text" => "Modul implicit de vizualizare la pornire pentru public și pentru utilizatorii neautentificați folosind ecrane extinse. <br>Se recomandă utilizarea modului 'Lunar'.",
"defaultViewS_label" => "Mod inițial vizualizare (ecrane mici)",
"defaultViewS_text" => "Modul implicit de vizualizare la pornire pentru public și pentru utilizatorii neautentificați la utilizarea ecranelor mici. <br>Se recomandă utilizarea modului 'Urmează'.",
"language_label" => "Limba implicită (public user)",
"language_text" => "For public (not logged in) users the language set for the browser user interface will be used for the calendar as well. If the browser language is not a valid calendar language, this default language will be used.<br>Note: Fișierele specifice de limbă ui-{limbă}.php, ai-{limbă}.php, ug-{limbă}.php precum și fișierul ug-layout.png trebuie să fie prezente în directorul 'lang/', unde textul {limba} reprezintă limba folosită pentru interfață, numele acestora trebuind să fie obligatoriu scrise cu litere mici (minuscule)!",
"birthday_cal_label" => "PDF Calendar aniversări",
"birthday_cal_text" => "dacă opțiunea este activată, un câmp 'Fișier PDF - Aniversări' va apare în meniul lateral pentru toți utilizatorii care au cel puțin drepturi de 'vizualizare'. Vedeți ghidul admin_guide.html - Calendar aniversări pentru mai multe detalii",
"sideLists_label" => "Approve, Todo, Upcoming lists",
"sideLists_text" => "If enabled, an option to show the respective list will appear in the Side Menu. The 'Events to be approved' list will only be available for users with at least 'manager' rights.",
"toapList_label" => "To approve list",
"todoList_label" => "To do list",
"upcoList_label" => "Upcoming list",

//settings.php - events settings.
"privEvents_label" => "Postare evenimente private",
"privEvents_text" => "<b>Activ</b>: utilizatorul poate posta propriile evenimente private.<br>Evenimentele private vor fi vizibile doar pentru cel care le-a introdus.<br><b>Implicit</b>: când sunt adaugăte evenimente noi, opțiunea 'privat' din fereastra Eveniment va fi selectată automat, în mod implicit.<br><b>Întotdeauna</b>: când sunt adăugate evenimente noi acestea vor fi întotdeauna evenimente private, opțiunea 'privat' din fereastra Eveniment nemaifiind afișată.",
"venueInput_label" => "Specifying venues",
"venueInput_text" => "In the Event window specifying a venue can be done either by typing the venue or by selecting a venue from a pre-defined list. If Free text is selected, the user can type the venue, if List is selected the user can select a venue from a drop-down list and when Both is selected, the user can choose between the two.<br> When a drop-down list is used, the 'files' folder must contain a file called venues.txt with one venue per line.",
"timeDefault_label" => "Timp implicit evenimente noi",
"timeDefault_text" => "Când se adaugă evenimente, modul implicit de afișare al câmpului timp poate fi setat după cum urmeaza:<br>• afișare timpi: Timpul de început și de sfârșit sunt afișați și pot fi completați/modificați<br>• toată ziua: Opțiunea Toată Ziua este marcată câmpurile timp de început și de sfârșit nemaifiind afișate<br>• fără timp: Opțiunea Fără timp este marcată câmpurile timp de început și de sfârșit nemaifiind afișate.",
"evtDelButton_label" => "Afișare buton ștergere în fereastra Eveniment",
"evtDelButton_text" => "<b>Selectat</b>: butonul Ștergere din fereastra evenimentului nu va fi afișat astfel încât, chiar și utilizatorii cu drept de editare, nu vor putea să șteargă evenimente.<br><b>Neselectat</b>: butonul Ștergere va fi afișat pentru toți utilizatorii.<br><b>Manager</b>: butonul Ștergere va fi afișat doar pentru utilizatorii cu drepturi de 'administrare'.",
"eventColor_label" => "Paleta de culori folosită pentru afișarea evenimentelor",
"eventColor_text" => "Evenimentele din calendar pot fi afișate folosind fie paletele definite de utilizator, fie paletele setate pentru categoria de eveniment.",
"defVenue_label" => "Locație implicită",
"defVenue_text" => "În acest câmp poate fi specificată o locație de bază, care va fi folosită la adăugarea de noi evenimente.",
"xField1_label" => "Câmp suplimentar 1",
"xField2_label" => "Câmp suplimentar 2",
"xFieldx_text" => "Dacă aceast câmp este inclus în afișarea ferestrei evenimentului, textul corespunzător va fi adăugat ferestrei Eveniment și tuturor modurilor de afișare corespunzătoare.<br>• etichetă: permite definirea/adăugarea unei etichete personalizate acestui câmp (max. 15 caractere). Spre ex.: 'Adresă de email', 'Site web', 'Număr de telefon'<br>• Drepturi minime utilizator: câmpul va fi vizibil doar utilizatorilor cu drepturi similare sau superioare de acces.",
"evtWinSmall_label" => "Fereastră redusă eveniment",
"evtWinSmall_text" => "Când se adaugă/editează un eveniment, fereastra <b>Eveniment</b> va afișa un subset al câmpurilor de intrare. Pentru afișarea tuturor câmpurilor selectați (click pe) săgeata de culoare roșie (stânga jos, deasupra butoanelor ferestrei).",
"emojiPicker_label" => "Emoji picker in Event window",
"emojiPicker_text" => "When enabled, in the Event Add/Edit window an emoji picker can be selected to add emoji to the event title and to the description fields.",
"mapViewer_label" => "URL hartă",
"mapViewer_text" => "Dacă s-a specificat un URL pentru locația pe hartă a evenimentului, adică o adresă în câmpul locație inclusă între două caractere '!', Calendarul va afișa un buton <b>Adresă</b>. Trecerea cu mouseul pe deasupra acestui buton va determina afișarea în clar a întregii adrese, iar selectarea efectivă a acestuia va determina afișarea hărții respective într-o nouă fereastră.<br>Trebuie avut în vedere că adresa locației (hărții) trebuie să conțină URL-ul complet, așa cum este el afișat de site-ul sursă.<br>Exemplu:<br><b>Google Maps</b>: https://maps.google.com/maps?q=<br><b>OpenStreetMap</b>: https://www.openstreetmap.org/search?query=<br>Dacă acest câmp rămâne necompletat calendarul nu va afișa butonul <b>Adresă</b>.",
"evtDrAndDr_label" => "Event drag and drop",
"evtDrAndDr_text" => "When enabled, in Year view, Month view and in the mini calendar on the side panel, events can be moved or copied from one day to an other day by means of Drag and Drop. If 'manager' is selected, only users with at least manager rights can use this feature. See the admin_guide.html for a detailed description.",
"free_text" => "Free text",
"venue_list" => "Venue list",
"both" => "Both",
"xField_label" => "Etichetă",
"show_times" => "afișare timpi",
"check_ald" => "toată ziua",
"check_ntm" => "fără timp",
"min_rights" => "Drepturi minime utilizator",
"no_color" => 'fără culoare',
"manager_only" => 'manager',

//settings.php - user accounts settings.
"selfReg_label" => "Auto-înregistrare",
"selfReg_text" => "Permite utilizatorilor fără cont să se auto-înregistreze pentru a putea vizualiza calendarul.<br>Grup de utilizatori la care vor fi atribuiți automat utilizatorii care se auto-înregistrează.",
"selfRegQA_label" => "Întrebare/răspuns auto-înregistrare",
"selfRegQA_text" => "Dacă opțiunea de auto-înregistrare este activă, în timpul procesului de înregistrare, utilzatorul va trebui să răspundă la această întrebare pentru a se putea auto-înregistra și a putea utiliza calendarul. Dacă câmpul este lăsat necompletat, (utilizatorul) nu va trebui să răspundă la nicio întrebare.",
"selfRegNot_label" => "Notificare auto-înregistrare",
"selfRegNot_text" => "Trimite un email la adresa proprie a Calendarului pentru a notifica apariția unei auto-înregistrări în calendar.",
"restLastSel_label" => "Restaurarea sesiunii ultimului utilizator",
"restLastSel_text" => "Sesiunea corespunzătoare ultimului utilizator (setare definită în Panoul de Opțiuni) va fi salvată, ea fiind automat reâncărcată la reconectarea acestuia la Calendar. Dacă utilizatorul nu se loghează în calendar un anumit număr de zile specificat, valoarea se va pierde.",
"answer" => "răspuns",
"exp_days" => "zile",
"view" => "vizualizare",
"post_own" => 'postare activităţi proprii',
"post_all" => 'postare/editare toate activităţile',
"manager" => 'postare/manager',

//settings.php - view settings.
"templFields_text" => "Corespondența numerelor:<br>1: Locație<br>2: Categorie<br>3: Descriere<br>4: Câmp suplimentar 1 (vezi mai jos)<br>5: Câmp suplimentar 2 (vezi mai jos)<br>6: Email de notificare (doar dacă s-a solicitat o notificare)<br>7: Data/ora adăugării/modificării și utilizatorul asociat<br>8: Fișier pdf, imagine sau video  atașat ca hiperlink.<br>Ordinea numerelor în secvență va determina și ordinea de afișare a câmpurilor.",
"evtTemplate_label" => "Șabloane evenimente",
"evtTemplate_text" => "Câmpul eveniment de afișat în vederea generală a Calendarului, evenimentele următoare cât și cele afișate în ferestrele tip hover pot fi stabilite printr-o secvență de numere.<br>Pentru fiecare număr din secvență butonul corespunzător va fi afișat.",
"evtTemplPublic" => "Utilizatori publici",
"evtTemplLogged" => "Utilizatori logați",
"evtTemplGen" => "Vedere generală",
"evtTemplUpc" => "Evenimente programate",
"evtTemplPop" => "Box tip hover",
"sortEvents_label" => "Sortare evenimente după timp sau categorie",
"sortEvents_text" => "Evenimentele pot fi sortate în diferite moduri de vizualizare după următoarele criterii:<br>• data/timpul evenimentului<br>• numărul secvenței categoriei corespunzătoare evenimentului",
"yearStart_label" => "Luna de start pentru modul de afișare 'Anual'",
"yearStart_text" => "Dacă se specifică o lună de start (1-12) pentru afișarea în modul 'Anual', Calendarul va fi afișat mereu pornind de la această lună, anul următor fiind afișat începând cu prima zi a lunii specificate (nu din prima zi a lunii ianuarie).<br>Valoarea '0' specifică faptul că afișarea lunilor se va baza pe data curentă.",
"YvRowsColumns_label" => "Numărul de luni si coloane de afișat în modul Anual",
"YvRowsColumns_text" => "Numărul de luni de afișat pe fiecare rând în modul 'Anual'.<br>Recomandabil 3 sau 4.<br>Numărul de coloane (pentru patru luni) de afișat în modul de vizualizare 'Anual'.<br>Recomandat 4 (pentru a avea 16 luni de vizualizat în pagină).",
"MvWeeksToShow_label" => "Numărul de săptămâni de afișat în modul 'Lunar'",
"MvWeeksToShow_text" => "Numărul de săptămâni de afișat în modul 'Lunar'.<br>Recomandabil 10 pentru a avea 2.5 luni de vizualizat în pagină.<br>Valorile 0 și 1 au aici un rol special:<br>0: se afișează exact 1 lună - lăsând neafișate zilele de început și de final din pagină.<br>1: se afișează exact 1 lună - fiind afișate suplimentar și zilele de început și de final din pagină.",
"XvWeeksToShow_label" => "Săptămânile de afișat în vederea matricială",
"XvWeeksToShow_text" => "Numărul de săptămâni de afișat în vizualizarea matricială.",
"GvWeeksToShow_label" => "Săptămânile de afișat în modul Gantt",
"GvWeeksToShow_text" => "Numărul de săptămâni de afișat în vizualizarea de tip Gantt.",
"workWeekDays_label" => "Zilele săptămînii curente",
"workWeekDays_text" => "Zilele din calendar colorate ca zile de lucru de afișat în vederile Calendarului sau, spre exemplu, în vederile <b>Luna curentă</b> sau <b>Săptămâna curentă</b>.<br>Introduceți un număr pentru fiecare zi de lucru.<br>ex. 12345: Luni - Vineri<br>Nu au fost introduse zilele care sunt considerate zile de weekend.",
"weekStart_label" => "Prima zi a săptămânii",
"weekStart_text" => "Introduceți prima zi a săptămânii de lucru.",
"lookBackAhead_label" => "Numărul de zile de afișat în modul 'Care urmează'",
"lookBackAhead_text" => "Numărul de zile de afișat pentru modul evenimente 'Care urmează', 'De văzut' și în fluxul RSS.",
"searchBackAhead_label" => "Numărul implicit de zile pentru căutare înainte/înapoi",
"searchBackAhead_text" => "Acesta reprezintă numărul implicit de zile pentru căutare pentru cazul în care nu se specifică nicio altă valoare în pagina de Căutare.",
"dwStartEndHour_label" => "Orele de început și de sfârșit pentru vederile tip Zi/Săptămână",
"dwStartEndHour_text" => "Orele la care o zi normală de lucru începe sau se termină.<br>Spre exemplu, setând aceste valori la 6 și la 18 se permite conservarea spațiului de afișare prin eliminarea de la afișare a orelor de noapte (între 18.00 și 6.00).<br>În mod similar și selectorul pentru timp va afișa doar acest interval restrâns.",
"dwTimeSlot_label" => "Dimensiune rând în modul 'Zilnic/Săptămânal'",
"dwTimeSlot_text" => "Înălțimea.<br>Această valoare, împreună cu 'Ora de început' (vezi mai sus), va determina numărul de linii maxim (rânduri) în modul 'Zilnic/Săptămânal'.",
"dwTsInterval" => "Intervalul de timp",
"dwTsHeight" => "Înălțimea",
"evtHeadX_label" => "Mod afișare eveniment în modul Lunar, Săptămânal, Zilnic",
"evtHeadX_text" => "Model cu zona de afișare a câmpurile eveniment. Pot fi folosite următoarele câmpuri de plasare/formatare:<br>#ts - timp de început<br>#tx - timp de început și de sfârșit<br>#e - titlu eveniment<br>#o - proprietar eveniment<br>#v - locație<br>#lv - locația cu afișarea etichetei 'Locație:' în față<br>#c - categorie<br>#lc - categorie cu afișarea etichetei 'Categorie:' în față<br>#a - vârsta (vezi nota de mai jos)<br>#x1 - câmpul suplimentar 1<br>#lx1 - câmpul suplimentar 1 cu eticheta din pagina de Setări afișată în față<br>#x2 - câmpul suplimentar 2<br>#lx2 - câmpul suplimentar 2 cu eticheta din pagina de Setări afișată în față<br>#/ - linie nouă<br>Câmpurile sunt afișate în ordinea specificată. Caracterele, altele decât cele de plasare/formatare, vor rămâne neschimbate și vor fi afișate ca parte a evenimentului.<br>Tagurile HTML sunt permise (ex. &lt;b&gt;#e&lt;/b&gt;.<br>caracterul | poate fi utilizat pentru a separa șablonul în secțiuni. Dacă într-o secțiune toți parametrii vor genera un șir nul de caractere, toată secțiunea va fi omisă.<br>Notă: Vârsta va fi afișată dacă evenimentul este parte a unei categorii pentru care opțiunea 'Repetare' a fost definită 'în fiecare an' și anul de naștere este menționat (în paranteze) undeva în câmpurile de descriere ale evenimentului or in one of the extra fields.",
"monthView" => "Modul Lunar",
"wkdayView" => "Modul Săptămânal/Zilnic",
"ownerTitle_label" => "Afișare proprietar eveniment în titlul evenimentului",
"ownerTitle_text" => "În diverse moduri de vizualizare ale calendarului numele celui care a definit evenimentul va fi afișat în titlul evenimentului, la început.",
"showSpanel_label" => "Vedere laterală în moduri de vizualizare",
"showSpanel_text" => "În modurile de vizualizare, pot fi afișate și următoarele elemente, în partea dreaptă a Calendarului:<br>• un minicalendar care poate fi utilizat pentru parcurgerea rapidă a calendarului fără schimbarea datei calendarului principal<br>• o imagine decorativă corespunzătoare lunei curente<br>• o zonă info pentru postarea mesajelor/anunțurilor pentru o anumită perioadă de timp.<br>>Pentru fiecare element se poate defini o listă de numere separate prin virgulă ca mod de vizualizare.<br>Valori posibile:<br>0: toate vederile<br>1: vedere anuală<br>2: afișare lunără (7 zile)<br>3: afișarea lunii curente<br>4: afișare săptămânală (7 zile)<br>5: săptămâna curentă<br>6: afișare pe zile<br>7: afișarea evenimentelor următoare<br>8: afișarea modificărilor<br>9: afișare matricială (categorii)<br>10: afișare matricială (utilizatori)<br>Dacă opțiunea 'Astăzi' este selectată, panoul lateral va utiliza întotdeauna data curentă, altfel va utiliza data din calendarul principal.<br>11: afișare tabel Gantt.<br>Vedeți și ghidul admin_guide.html pentru detalii.",
"spMiniCal" => "Mini calendar",
"spImages" => "Imagini",
"spInfoArea" => "Zona Info",
"spToday" => "Astăzi",
"topBarDate_label" => "Afișare dată curentă în bara de sus",
"topBarDate_text" => "Activează/dezactivează afișarea datei curente în bara de sus a calendarului. Dacă data este afișată, ea poate fi selectată pentru a reseta data calendarului la data curentă (a sistemului).",
"showImgInMV_label" => "Afișare în modul 'Lunar'",
"showImgInMV_text" => "Activare/dezactivare afișare imagini în modul Lunar. Dacă se activează opțiunea, imaginile (dacă sunt definite) vor fi afișate în celula corespunzătoare a fiecărei zile. Dacă opțiunea este dezactivată imaginile (dacă sunt definite) vor fi afișate doar când se trece cu mouse-ul pe deasupra zilei respective.",
"urls" => "Linkuri URL",
"emails" => "Linkuri email",
"monthInDCell_label" => "Afișare lună în fiecare celulă (zi)",
"monthInDCell_text" => "Afișează în modul lunar numele lunii (primele 3 litere) în fiecare celulă (zi)",
"scrollDCell_label" => "Use scrollbar in day cells",
"scrollDCell_text" => "If in month view a day cell is too small, rather than increasing the day cell height, a vertical scrollbar will appear.",

//settings.php - date/time settings.
"dateFormat_label" => "Formatul datei (zz ll aaaa)",
"dateFormat_text" => "Șir de caractere care definește modul de afișare pentru dată în calendar.<br>Caracterele acceptate: a = pentru an, l = pentru lună și d = pentru zi.<br>Caracterele non-alfanumerice pot fi utilizate ca separator și vor fi copiate ca atare. <br>Exemplu:<br>a-l-z: 2024-10-31<br>l.z.a: 10.31.2024<br>z/l/a: 31/10/2024",
"dateFormat_expl" => "ex. a.l.z: 2024.10.31",
"MdFormat_label" => "Format dată (zz lună)",
"MdFormat_text" => "Șir de caractere care definește modul de afișare pentru dată în calendar, pentru lună și zi.<br>Caractere posibile: L = luna ca text, z = ziua în cifre.<br>Caracterele non-alfanumerice pot fi utilizate ca separator și vor fi copiate ca atare.<br>Exemplu:<br>z L: 12 Aprilie<br>L, z: Iulie, 14",
"MdFormat_expl" => "ex. L, z: Iulie, 14",
"MdyFormat_label" => "Format dată (zz lună aaaa)",
"MdyFormat_text" => "Șir de caractere care definește modul de afișare pentru dată în calendar, pentru zi, lună și an.<br>Caractere posibile: d = ziua în cifre, M = luna ca text, y = anul în cifre.<br>Caracterele non-alfanumerice pot fi utilizate ca separator și vor fi copiate ca atare.<br>Exemplu:<br>d M y: 12 Aprilie 2024<br>M d, y: Iulie 8, 2024",
"MdyFormat_expl" => "ex. L z, y: Iulie 8, 2024",
"MyFormat_label" => "Format dată (lună aaaa)",
"MyFormat_text" => "Șir de caractere care definește modul de afișare pentru dată în calendar, pentru lună și an.<br>Caractere posibile: L = luna ca text, y = anul în cifre.<br>Caracterele non-alfanumerice pot fi utilizate ca separator și vor fi copiate ca atare.<br>Exemplu:<br>L a: Aprilie 2024<br>a - L: 2024 - Iulie",
"MyFormat_expl" => "ex. L a: Aprilie 2024",
"DMdFormat_label" => "Format dată (ziua săptămânii zz lună)",
"DMdFormat_text" => "Șir de caractere care definește modul de afișare pentru dată în calendar, pentru ziua săptămânii, zi și lună.<br>Caractere posibile: ZS = ziua din săptămână ca text, L = luna ca text, d = ziua în cifre.<br>Caracterele non-alfanumerice pot fi utilizate ca separator și vor fi copiate ca atare.<br>Exemple:<br>ZS z L: Vineri 12 Aprilie<br>ZS, L z: Luni, Iulie 14",
"DMdFormat_expl" => "ex. ZS - L z: Duminică - Aprilie 6",
"DMdyFormat_label" => "Format dată (ziua săptămînii zz lună aaaa)",
"DMdyFormat_text" => "Șir de caractere care definește modul de afișare pentru dată în calendar, pentru ziua săptămânii, zi, lună și an.<br>Caractere posibile: ZS = ziua din săptămână ca text, L = luna ca text, z = ziua în cifre, a = anul în cifre.<br>Caracterele non-alfanumerice pot fi utilizate ca separator și vor fi copiate ca atare.<br>Exemple:<br>ZS z L a: Vineri 13 Aprilie 2024<br>ZS - L z, a: Luni - Iulie 16, 2024",
"DMdyFormat_expl" => "ex. ZS, L z, a: Luni, Iulie 16, 2024",
"timeFormat_label" => "Format timp (hh mm)",
"timeFormat_text" => "Șir de caractere care definește modul de afișare pentru oră în calendar.<br>Caractere posibile: h = oră, H = ore cu cifra zero la început, m = minute, a = am/pm (opțional), A = AM/PM (opțional).<br>Caracterele non-alfanumerice pot fi utilizate ca separator și vor fi copiate ca atare.<br>Exemplu:<br>h:m: 18:35<br>h.m a: 6.35 pm<br>H:mA: 06:35PM",
"timeFormat_expl" => "ex. h:m: 22:35 și h:mA: 10:35PM",
"weekNumber_label" => "Afișare număr săptămână",
"weekNumber_text" => "Afișarea numărului săptămânii în modurile relevante poate fi activată/dezactivată",
"time_format_us" => "12-ore AM/PM",
"time_format_eu" => "24-ore",
"sunday" => "Duminică",
"monday" => "Luni",
"time_zones" => "FUS ORAR",
"dd_mm_yyyy" => "zz-ll-aaaa",
"mm_dd_yyyy" => "ll-zz-aaaa",
"yyyy_mm_dd" => "aaaa-ll-zz",

//settings.php - file uploads settings.
"maxUplSize_label" => "Dimensiune maximă fișier de încărcat",
"maxUplSize_text" => "Dimensiunea maximă a fișierului pentru atașamente sau imagini miniatură.<br><b>Notă</b>: Cele mai multe instalări PHP stabilesc deja această valoare maximă la 2 MB (în fișierul php_ini) ",
"attTypes_label" => "Tipul de fișier pentru atașamente",
"attTypes_text" => "Tipurile de fișiere (extensii), separate prin virgulă, care pot fi încărcate (ex. '.pdf,.jpg,.gif,.png,.mp4,.avi')",
"tnlTypes_label" => "Tipul de imagini miniatură acceptate",
"tnlTypes_text" => "Tipurile de imagini miniatură, separate prin virgulă, care pot fi încărcate (ex. '.jpg,.jpeg,.gif,.png')",
"tnlMaxSize_label" => "Dimensiune maximă imagine miniatură",
"tnlMaxSize_text" => "Dimensiunea maximă pentru imaginea miniatură. Dacă utilizatorul încarcă o imagine miniatură cu dimensiunea mai mare decât valoarea specificată aici, aceasta va fi automat redimensionată la această valoare.<br><b>Notă</b>: Imaginile de mari dimensiuni pot deforma căsuța corespunzătoare zilei în care vor fi afișate ceea ce poate duce la alterarea modului de afișare al calendarului, pe ansamblu, sau alte efecte secundare nedorite.",
"tnlDelDays_label" => "Margine de ștergere miniatură",
"tnlDelDays_text" => "Dacă o imagine miniatură este utilizată deja de un număr de zile specificat de acest număr, ea nu va putea fi ștearsă.<br>Valoarea 0 (zile) înseamnă că imaginea nu poate fi ștearsă.",
"days" =>"zile",
"mbytes" => "MB",
"wxhinpx" => "Lățime x Înălțime în pixeli",

//settings.php - reminders settings.
"services_label" => "Servicii",
"services_text" => "Serviciile disponibile pentru a trimite un memento. Dacă nu selectați niciun serviciu, secțiunea corespunzătoare din fereastra <b>Eveniment</b> va fi eliminată.",
"msgLogging_label" => "Notification message logging",
"msgLogging_text" => "When checked, the notification messages sent are logged in the messages.log file. The 'weeks' field specifies how long the logged messages should be kept",
"smsCarrier_label" => "Model furnizor SMS",
"smsCarrier_text" => "Modelul de suport SMS permite definirea adresei de trimitere SMS: ppp#sss@carrier, unde . . .<br>• ppp: text opțional care va fi atașat în mod automat înaintea numărului de telefon<br>• #: loc pentru introducerea numărului de telefon (Calendarul va înlocui caracterul # cu numărul/numerele de telefon corespunzătoare)<br>• sss: text opțional care va fi adăugat în mod automat după numărul de telefon, spre exemplu un nume de utilizator sau o parolă cerută în mod expres de anumiți operatori de telefonie<br>• @: caracter separator<br>• furnizor: adresa furnizorului (ex. mail2sms.com)<br><b>Model exemplu</b>: #@xmobile.com, 0#@carr2.int, #myunmypw@sms.gway.net.",
"smsCountry_label" => "Cod SMS țară",
"smsCountry_text" => "Dacă serverul de SMS utilizat este localizat în altă țară, codul de țară al zonei în care este utilizat calendarul va trebui specificat în clar, în mod obligatoriu.<br>Puteți folosi fie '<b>+</b>' fie '<b>00</b>' dacă este nevoie de prefix.",
"smsSubject_label" => "Șablon subiect SMS",
"smsSubject_text" => "Dacă specificați un șablon, textul corespunzător șablonului va fi copiat în mod automat în câmpul <b>Subiect</b> al fiecărui SMS trimis. Textul poate conține caracterul <b>#</b>, care va fi înlocuit însă în mod automat de numărul de telefon asociat Calendarului sau al utilizatorului (properietarul evenimentului), în funcție de setările de mai jos.<br><b>Exemplu</b>: 'FROMPHONENUMBER=#'.",
"smsAddLink_label" => "Adăugare link eveniment la SMS",
"smsAddLink_text" => "Dacă opțiunea este activă, un link către eveniment va fi adăugat în mod automat la fiecare SMS. Prin deschiderea acestui link destinatarul va putea să vadă astfel detalii ale respectivului eveniment.",
"maxLenSms_label" => "Lungime maximă SMS",
"maxLenSms_text" => "Mesajele SMS sunt trimise folosind codarea utf-8. Mesajele care au maxim 70 de caractere vor fi trimise într-un singur mesaj, cele care depășesc 70 de caractere vor fi împărțite în mai multe mesaje separate.",
"calPhone_label" => "Numărul de telefon asociat Calendarului",
"calPhone_text" => "Numărul de telefon folosit ca ID atunci când se trimite un mesaj SMS de notificare.<br><b>Format</b>: gratuit, max. 20 digiți (în unele țări e necesar un număr de telefon, în altele se acceptă și caractere din alfabet).<br>Dacă nu există niciun serviciu SMS activ sau nu a fost definit niciun șablon pentru subiectul SMS-urilor, acest câmp poate fi lasat necompletat.",
"notSenderEml_label" => "Adăugare câmp 'Reply to' la email",
"notSenderEml_text" => "Dacă opțiunea este selectată, emailurile de notificare vor conține un câmp 'Reply to' cu adresa de email a proprietarului evenimentului, către care se poate trimite un email de răspuns.",
"notSenderSms_label" => "Expeditorul notificărilor SMS",
"notSenderSms_text" => "Când Calendarul trimite mesaje SMS, ID-ul expeditorului poate fi fie numărul de telefon asociat Calendarului fie numărul de telefon al celui care a creat evenimentul.<br>Dacă 'user' este selectat și acesta nu are niciun număr de telefon asociat Calendarul va folosi numărul propriu. <br>Dacă se folosește numărul de telefon al utilizatorului, atunci cel care primește SMS-ul poate răspunde.",
"defRecips_label" => "Lista implicită de adrese",
"defRecips_text" => "Dacă este specificată, aceasta va fi lista implicită pentru mesajele email/SMS de notificare din fereastra <b>Eveniment</b>. Dacă câmpul rămâne necompletat, atunci adresa implicită va fi adresa proprietarului evenimentului.",
"maxEmlCc_label" => "Numărul maxim de adrese per email",
"maxEmlCc_text" => "Îm mod normal fiecare ISP limitează numărul de adrese pentru fiecare mesaj de trimis. Când se trimite un email sau un SMS, dacă numărul de adrese către care trebuie trimis mesajul e mai mare dacât valoarea specificată aici, mesajul (emai/SMS) va fi trimis succesiv, pe grupe de adrese, fiecare grup având cel mult numărul maxim de adrese posibil.",
"emlFootnote_label" => "Nota de subsol email de aduce aminte",
"emlFootnote_text" => "Text neformatat care va fi adăugat ca paragraf la finalul mesajelor email de aducere aminte. Pot fi folosite tag-uri HTML pentru formatare.",
"mailServer_label" => "Utilizare <b>PHP mail</b> sau <b>SMTP mail</b>",
"mailServer_text" => "Modulul <b>PHP mail</b> este indicat să fie folosit pentru trimiterea unui număr relativ mic de emailuri, fără autentificare. Pentru un număr crescut de emailuri, când se impune și existența autentificării, este recomandat folosirea modulului <b>SMTP mail</b>.<br>Utilizarea <b>SMTP mail</b> presupune existența unui server de email dedicat, parametrii de configurare pentru utilizarea serverului SMTP trebuind să fie specificați mai jos.",
"smtpServer_label" => "Nume server SMTP",
"smtpServer_text" => "Dacă selectați modul <b>SMTP mail</b> va trebui să introduceți aici numele serverului SMTP. Spre exemplu: smtp.gmail.com.",
"smtpPort_label" => "Port SMTP",
"smtpPort_text" => "Dacă selectați modul <b>SMTP mail</b> va trebui să introduceți aici portul utilizat de serverul SMTP. Spre exemplu: 25, 465 sau 587. Gmail utilizează spre exemplu portul 465.",
"smtpSsl_label" => "SSL (Secure Sockets Layer)",
"smtpSsl_text" => "Dacă selectați modul <b>SMTP mail</b>, puteți selecta aici utilizarea modului SSL (Secure Sockets Layer). Spre exemplu pentru gmail opțiunea SSL trebuie activată.",
"smtpAuth_label" => "Autentificare SMTP",
"smtpAuth_text" => "Dacă opțiunea este selectată, numele și parola specificate mai jos vor fi utilizate ca date de autentificare pentru serverul de mail SMTP.<br>Pentru Gmail spre exemplu numele de utilizator face parte din adresa de email (partea dinaintea caracterului @).",
"tlgToken_label" => "Telegram token",
"tlgToken_text" => "Telegram token in the following format: &lt;bot ID&gt;:&lt;bot hash&gt;. For details see installation_guide.html, section Event Notification Messages.",
"cc_prefix" => "Codul de țară începe cu prefixul <b>+</b> sau <b>00</b>",
"weeks" => "Weeks",
"general" => "General",
"php_mail" => "Mail PHP",
"smtp_mail" => "Mail SMTP (completați câmpurile de mai jos)",

//settings.php - periodic function settings.
"cronHost_label" => "Host Cron job",
"cronHost_text" => "Specifică localizarea cron job care startează periodic scriptul. 'lcalcron.php'.<br>• <b>local</b>: cron job rulează pe același server cu Calendarul<br>• <b>remote</b>: cron job rulează pe un server separat sau lcalcron.php este rulat manual (testare)<br>• <b>Adresă IP</b>: cron job va rula de pe un server specificat prin această adresa IP.",
"cronSummary_label" => "Sumar Cron",
"cronSummary_text" => "Mod de trimitere a sumarului serviciului cron pe email la administratorul Calendarului.<br>Opțiunea este utilă doar dacă pe server a fost activată cel puțin o acțiune în cron.",
"icsExport_label" => "Export zilnic pentru evenimente iCal",
"icsExport_text" => "<b>Activ</b>: Toate evenimentele aflate în intervalul -1 săptămână până peste 1 an vor fi exportate într-un fișier .ics în folderul 'files' în formatul iCalendar.<br>Numele fișierului va fi generat pe baza numelui calendarului având eventualele spații înlocuite cu caracterul '_' (underscores), cu suprascrierea automată a fișierului mai vechi.",
"eventExp_label" => "Nr. zile expirare eveniment",
"eventExp_text" => "Numărul de zile după care un eveniment este șters în mod automat.<br>Pentru valoarea 0 sau dacă nu este definit niciun eveniment în lista cron, niciun eveniment nu va fi șters în mod automat.",
"maxNoLogin_label" => "Numărul maxim de zile acceptat fără logare",
"maxNoLogin_text" => "Dacă un utilizator nu se autentifică (nu accesează Calendarul) în numărul specificat de zile, contul corespunzator va fi automat șters.<br>Dacă valoare introdusă este '0' conturile utilizatorilor nu vor fi șterse niciodată.",
"local" => "local",
"remote" => "remote",
"ip_address" => "Adresă IP",

//settings.php - mini calendar / sidebar settings.
"popFieldsSbar_label" => "Câmpuri eveniment - fereastra laterală (tip hover)",
"popFieldsSbar_text" => "Câmpurile evenimentului care vor fi afișate într-o fereastră laterală tip hover pot fi specificate aici printr-o secvență de numere.<br>Dacă nu se specifică niciun câmp fereastra hover nu va mai fi afișată.",
"showLinkInSB_label" => "Afișare linkuri în fereastra laterală",
"showLinkInSB_text" => "Afișare URL-uri din descrierea evenimentului ca hyperlink-uri în fereastra laterală a evenimentelor care urmează",
"sideBarDays_label" => "Zile de urmărit în zona de afișare laterală",
"sideBarDays_text" => "Numărul de zile de urmărit pentru evenimentele afișate în fereastra laterală.",

//login.php
"log_log_in" => "Autentificare",
"log_remember_me" => "Memorare utilizator",
"log_register" => "Înregistrare",
"log_change_my_data" => "Modificare date acces",
"log_save" => "Modifică",
"log_done" => "Gata",
"log_un_or_em" => "Nume utilizator sau email",
"log_un" => "Nume utilizator",
"log_em" => "Email",
"log_ph" => "Număr telefon mobil",
"log_tg" => "Telegram chat ID",
"log_answer" => "Răspunsul dumneavoastră",
"log_pw" => "Parola",
"log_expir_date" => "Account expiration date",
"log_account_expired" => "This account has expired",
"log_new_un" => "Nume utilizator nou",
"log_new_em" => "Adresă nouă de email",
"log_new_pw" => "Parola nouă",
"log_con_pw" => "Confirmare parolă",
"log_pw_msg" => "Aveți aici detaliile log pentru autentificare",
"log_pw_subject" => "parola dvs.",
"log_npw_subject" => "Noua dumneavoastră parolă",
"log_npw_sent" => "Noua parolă a fost trimisă",
"log_registered" => "Înregistrare corectă - Parola v-a fost deja trimisă prin email",
"log_em_problem_not_sent" => "Problemă email - parola dumneavoastră nu a putut să fie trimisă",
"log_em_problem_not_noti" => "Problemă email - nu se poate verifica administratorul",
"log_un_exists" => "Acest nume de utilizator există deja",
"log_em_exists" => "Această adresă de email există deja",
"log_un_invalid" => "Nume utilizator invalid (nr. minim de caractere - 2. Folosiți doar caracterele: A-Z, a-z, 0-9, and _-.) ",
"log_em_invalid" => "Adresă de email incorectă",
"log_ph_invalid" => "Număr de telefon invalid",
"log_tg_invalid" => "Invalid Telegram chat ID",
"log_sm_nr_required" => "SMS: mobile phone number required",
"log_tg_id_required" => "Telegram: chat ID required",
"log_sra_wrong" => "Răspuns incorect",
"log_sra_wrong_4x" => "Ați răspuns incorect de 4 ori - puteți reâncerca în 30 de minute",
"log_un_em_invalid" => "Numele de utilizator / email incorecte",
"log_un_em_pw_invalid" => "Numele de utilizator / email sau parolă incorecte",
"log_pw_error" => "Parolele nu corespund",
"log_no_un_em" => "Introduceți numele sau adresa de email",
"log_no_un" => "Introduceți numele",
"log_no_em" => "Introduceți adresa de email",
"log_no_pw" => "Introduceți parola",
"log_no_rights" => "Autentificare eșuată: nu aveți drepturi de vizualizare - Contactați administratorul",
"log_send_new_pw" => "Trimite parolă nouă",
"log_new_un_exists" => "Numele de utilizator introdus există deja",
"log_new_em_exists" => "Adresa introdusă există deja",
"log_ui_language" => "Limba pentru Interfața Utilizator",
"log_new_reg" => "Înregistrare utilizator nou",
"log_date_time" => "Data / ora",
"log_time_out" => "Timp expirat",

//categories.php
"cat_list" => "Lista categoriilor",
"cat_edit" => "Editare",
"cat_delete" => "Ștergere",
"cat_add_new" => "Adăugare categorie nouă",
"cat_add" => "Adăugare categorie",
"cat_edit_cat" => "Editare categorie",
"cat_sort" => "Sortare după nume",
"cat_cat_name" => "Denumire categorie",
"cat_symbol" => "Simbol",
"cat_symbol_repms" => "Categoria simbol (înlocuiește parantezele)",
"cat_symbol_eg" => "e.g. A, X, ♥, ⛛",
"cat_matrix_url_link" => "Link URL (afișat în vederea matricială)",
"cat_seq_in_menu" => "Poziția în meniu",
"cat_cat_color" => "Culoare categorie",
"cat_text" => "Text",
"cat_background" => "Fundal",
"cat_select_color" => "Selecție culoare",
"cat_subcats" => "Sub-<br>categorii",
"cat_subcats_opt" => "Numărul de subcategorii (opțional)",
"cat_copy_from" => "Copiere de la",
"cat_eml_changes_to" => "Send event changes to",
"cat_url" => "URL",
"cat_name" => "Nume",
"cat_subcat_note" => "Notați că subcategoria curentă poate fi deja utilizată pentru cel puțin un eveniment",
"cat_save" => "Actualizare categorie",
"cat_added" => "Categorie adăugată",
"cat_updated" => "Categorie actualizată",
"cat_deleted" => "Categorie ștearsă",
"cat_not_added" => "Categoria nu a fost adăugată",
"cat_not_updated" => "Categoria nu a fost actualizată",
"cat_not_deleted" => "Categoria nu a fost ștearsă",
"cat_nr" => "#",
"cat_repeat" => "Cu repetare",
"cat_every_day" => "în fiecare zi",
"cat_every_week" => "în fiecare săptămână",
"cat_every_month" => "în fiecare lună",
"cat_every_year" => "în fiecare an",
"cat_overlap" => "Permisiune la<br>suprapunere<br>(gap)",
"cat_need_approval" => "Evenimentul necesită<br>aprobare",
"cat_no_overlap" => "Fără suprapuneri",
"cat_same_category" => "acceași categorie",
"cat_all_categories" => "toate categoriile",
"cat_gap" => "gap",
"cat_ol_error_text" => "Mesaj de eroare în caz de suprapunere",
"cat_no_ol_note" => "De menționat că evenimentele deja definite nu vor fi verificate pentru eventuale suprapuneri",
"cat_ol_error_msg" => "suprapunere eveniment - selectați altă oră",
"cat_no_ol_error_msg" => "Mesajul de suprapunere lipsește",
"cat_duration" => "Durată<br>eveniment<br>! = fix",
"cat_default" => "implicit (fără timp de final)",
"cat_fixed" => "fix",
"cat_event_duration" => "Durată eveniment",
"cat_olgap_invalid" => "Zonă invalidă de suprapunere",
"cat_duration_invalid" => "Durată invalidă eveniment",
"cat_no_url_name" => "Numele linkului URL lipsește",
"cat_invalid_url" => "Link URL invalid",
"cat_day_color" => "Culoare zi",
"cat_day_color1" => "Culoare zi (vedere anuală/matricilă)",
"cat_day_color2" => "Culoare zi (vedere lunară/săptămânală/zilnică)",
"cat_approve" => "Evenimentul necesită aprobare",
"cat_check_mark" => "Marcaj confirmare",
"cat_not_list" => "Notify<br>list",
"cat_label" => "etichetă",
"cat_mark" => "marcaj",
"cat_name_missing" => "Numele categoriei lipsește",
"cat_mark_label_missing" => "Bifa/eticheta lipsește",

//users.php
"usr_list_of_users" => "Listă utilizatori",
"usr_name" => "Nume utilizator",
"usr_email" => "Email",
"usr_phone" => "Număr telefon mobil",
"usr_phone_br" => "Număr telefon<br>mobil",
"usr_tg_id" => "Telegram chat ID",
"usr_tg_id_br" => "Telegram<br>chat ID",
"usr_not_via" => "Notify via",
"usr_not_via_br" => "Notify<br>via",
"usr_language" => "Limbă",
"usr_ui_language" => "Limbă interfață utilizator",
"usr_group" => "Grupa",
"usr_password" => "Parola",
"usr_expir_date" => "Account expiration date",
"usr_select_exp_date" => "Select expiration date",
"usr_blank_none" => "blank: no expiration",
"usr_expires" => "Expires",
"usr_edit_user" => "Editare profil utilizator",
"usr_add" => "Adăugare utilizator",
"usr_edit" => "Editare",
"usr_delete" => "Ștergere",
"usr_login_0" => "Prima conectare",
"usr_login_1" => "Ultima conectare",
"usr_login_cnt" => "Conectări",
"usr_add_profile" => "Adăugare utilizator",
"usr_upd_profile" => "Actualizare profil",
"usr_if_changing_pw" => "Doar dacă se schimbă parola",
"usr_pw_not_updated" => "Parola nu a fost actualizată",
"usr_added" => "Utilizator adăugat",
"usr_updated" => "Profile utilizatori",
"usr_deleted" => "Utilizator șters",
"usr_not_deleted" => "Utilizatorul nu a fost șters",
"usr_cred_required" => "Numele utilizatorului, emailul și parola sunt necesare",
"usr_name_exists" => "Acest nume de utilizator există deja",
"usr_email_exists" => "Această adresă de email există deja",
"usr_un_invalid" => "Nume utilizator invalid (minim '2' caractere. Folosiți doar caracterele: A-Z, a-z, 0-9, and _-.) ",
"usr_em_invalid" => "Adresă de email invalidă",
"usr_ph_invalid" => "Număr de telefon invalid",
"usr_tg_invalid" => "Invalid Telegram chat ID",
"usr_xd_invalid" => "Invalid account expiration date",
"usr_cant_delete_yourself" => "Nu vă puteți șterge propriul cont",
"usr_go_to_groups" => "Selecție grupuri",
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
"grp_list_of_groups" => "Listă grupuri",
"grp_name" => "Nume grup",
"grp_priv" => "Drepturi de acces",
"grp_categories" => "Categorii",
"grp_all_cats" => "toate categoriile",
"grp_rep_events" => "Evenimente repetitive",
"grp_m-d_events" => "Evenimente pe mai multe zile",
"grp_priv_events" => "Evenimente private",
"grp_upload_files" => "Încărcare<br>fișiere",
"grp_tnail_privs" => "Privilegii<br>imagini miniatură",
"grp_priv0" => "Fără drepturi de acces",
"grp_priv1" => "Vizualizare calendar",
"grp_priv2" => "Postare/editare evenimente proprii",
"grp_priv3" => "Postare/editare toate evenimentele",
"grp_priv4" => "Postare/editare și aprobare",
"grp_priv9" => "Funcții administrare",
"grp_may_post_revents" => "Poate adăuga evenimente repetitive",
"grp_may_post_mevents" => "Poate adăuga evenimente pentru mai multe zile",
"grp_may_post_pevents" => "Poate adăuga evenimente private",
"grp_may_upload_files" => "Poate încărca fișiere",
"grp_tn_privs" => "Privilegii imagini miniatură",
"grp_tn_privs00" => "fără",
"grp_tn_privs11" => "vizualizare toate",
"grp_tn_privs20" => "administrare imagini proprii",
"grp_tn_privs21" => "m. proprii/v. toate",
"grp_tn_privs22" => "administrare toate",
"grp_edit_group" => "Editare grup",
"grp_sub_to_rights" => "Subiect de drepturi de utilizator",
"grp_view" => "Vedere",
"grp_add" => "Adăugare",
"grp_edit" => "Editare",
"grp_delete" => "Ștergere",
"grp_add_group" => "Adăugare grup",
"grp_upd_group" => "Actualizare grupuri",
"grp_added" => "Grup adăugat",
"grp_updated" => "Grup actualizat",
"grp_deleted" => "Grup șters",
"grp_not_deleted" => "Grupul nu a fost șters",
"grp_in_use" => "Grup activ, nu poate fi editat",
"grp_cred_required" => "E necesar definirea numelui de grup, drepturile de acces și categoriile asociate",
"grp_name_exists" => "Acest nume există deja",
"grp_name_invalid" => "Nume de grup invalid (minim '2' caractere. Folosiți doar caracterele: A-Z, a-z, 0-9, and _-.) ",
"grp_check_add" => "At least one check box in the Add column must be checked",
"grp_background" => "Culoare fundal",
"grp_select_color" => "Selectare culoare",
"grp_invalid_color" => "Format de culoare invalid (#XXXXXX - X = valoare HEXA)",
"grp_go_to_users" => "Selecție utilizatori",

//texteditor.php
"edi_text_editor" => "Editare text informare",
"edi_file_name" => "File name",
"edi_save" => "Salavare text",
"edi_backup" => "Backup text",
"edi_select_file" => "Select file",
"edi_info_text" => "Information text",
"edi_pub_recips" => "Public recipients",
"edi_recips_list" => "Recipients list",
"edi_new_recips_list" => "New recipients list",
"edi_no_file_name" => "No file name specified",
"edi_no_text" => "Nu există niciun text",
"edi_confirm_changes" => "The text changes have not been saved\\nDo you want to continue?", //don't remove '\\n'
"edi_text_saved" => "Text salvat în fișierul $1",

//database.php
"mdb_dbm_functions" => "Funcții pentru Baza de date",
"mdb_noshow_tables" => "Tabelele (din bază) nu pot fi accesate",
"mdb_noshow_restore" => "Nu a fost selectat fișierul backup",
"mdb_file_not_sql" => "Fișierul de backup trebuie sa fie un fișier SQL (cu extensia '.sql')",
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
"mdb_compact" => "Compactare bază de date",
"mdb_compact_table" => "Compactare tabele",
"mdb_compact_error" => "Eroare",
"mdb_compact_done" => "Gata",
"mdb_purge_done" => "Evenimentele marcate pentru ștergere au fost eliminate definitiv",
"mdb_backup" => "Back-up Bază de date",
"mdb_backup_table" => "Back-up tabel",
"mdb_backup_file" => "Back-up fișier",
"mdb_backup_done" => "Gata",
"mdb_records" => "înregistrări",
"mdb_restore" => "Restaurare bază",
"mdb_restore_table" => "Restaurare tabelă",
"mdb_inserted" => "înregistrări adăugate",
"mdb_db_restored" => "Baza a fost restaurată",
"mdb_db_upgraded" => "Baza a fost upgradată",
"mdb_no_bup_match" => "Fișierul backup selectat nu corespunde versiunii curente a calendarului.<br0>Baza de date nu a fost restaurată.",
"mdb_events" => "Evenimente",
"mdb_delete" => "ștegere",
"mdb_undelete" => "recuperare",
"mdb_between_dates" => "care apar între",
"mdb_deleted" => "Evenimente șterse",
"mdb_undeleted" => "Evenimente recuperate",
"mdb_file_saved" => "Fișier de back-up salvat.",
"mdb_file_name" => "Nume fișier",
"mdb_start" => "Execută",
"mdb_no_function_checked" => "Nicio funcție selectată",
"mdb_write_error" => "Eroare salvare fișier de back-up. <br>Verificați drepturile de scriere pentru fișiere în folderul de back-up",

//import/export.php
"iex_file" => "Selecție Fișier",
"iex_file_name" => "Nume fișier destinație",
"iex_file_description" => "Descriere fișier iCal",
"iex_filters" => "Filtru evenimente",
"iex_export_usr" => "Export profile utilizator",
"iex_import_usr" => "Import profile utilizator",
"iex_upload_ics" => "Import fișier iCal",
"iex_create_ics" => "Creare fișier iCal",
"iex_tz_adjust" => "Ajustare fus orar",
"iex_upload_csv" => "Incărcare fișier CSV",
"iex_upload_file" => "Import fișier",
"iex_create_file" => "Creare fișier",
"iex_download_file" => "Descărcare fișier",
"iex_fields_sep_by" => "Câmpuri separate prin",
"iex_birthday_cat_id" => "ID categorie",
"iex_default_grp_id" => "ID implicit grup",
"iex_default_cat_id" => "ID implicit categorie",
"iex_default_pword" => "Parolă implicită",
"iex_if_no_pw" => "Dacă nu este specificată nicio parolă",
"iex_replace_users" => "Înlocuire utilizatori existenți",
"iex_if_no_grp" => "dacă nu a fost găsit niciun grup",
"iex_if_no_cat" => "dacă nu este gasită nicio categorie",
"iex_import_events_from_date" => "Import evenimente definite până la",
"iex_no_events_from_date" => "Nu a fost găsit niciun eveniment la data specificată",
"iex_see_insert" => "vezi instrucțiunile în partea dreaptă",
"iex_no_file_name" => "Numele fișierului lipsește",
"iex_no_begin_tag" => "fișier iCal invalid (lipsește tag-ul BEGIN)",
"iex_bad_date" => "Dată eronată",
"iex_date_format" => "Format dată eveniment",
"iex_time_format" => "Format timp eveniment",
"iex_number_of_errors" => "Numărul erorilor din listă",
"iex_bgnd_highlighted" => "evidențiere fundal",
"iex_verify_event_list" => "Verificați Lista evenimentelor și faceți corecțiile necesare, apoi faceți click",
"iex_add_events" => "Adăugare evenimente la baza de date",
"iex_verify_user_list" => "Verificați lista utilizatorilor, corectați eventualele erori",
"iex_add_users" => "Adăugare utilizatori la baza de date",
"iex_select_ignore_birthday" => "Selectați opțiunile Ziua de naștere și Ștergere după nevoie",
"iex_select_ignore" => "Selectați opțiunea Ștergere pentru a ignora evenimentul",
"iex_check_all_ignore" => "Verificați toate opțiunile",
"iex_title" => "Denumire",
"iex_venue" => "Locație",
"iex_owner" => "Proprietar",
"iex_category" => "Categorie",
"iex_date" => "Data",
"iex_end_date" => "Data de sfârșit",
"iex_start_time" => "Ora de începere",
"iex_end_time" => "Ora de terminare",
"iex_description" => "Descriere",
"iex_repeat" => "Repetă",
"iex_birthday" => "data aniversare",
"iex_ignore" => "Ștergere",
"iex_events_added" => "evenimente adăugate",
"iex_events_dropped" => "eveniment ignorat (există deja)",
"iex_users_added" => "utilizatori adăugați",
"iex_users_deleted" => "utilizatori șterși",
"iex_csv_file_error_on_line" => "eroare în fișierul CSS la linia",
"iex_between_dates" => "Apare în intervalul",
"iex_changed_between" => "Adăugat/modificat între",
"iex_select_date" => "Selecție dată",
"iex_select_start_date" => "Selecție dată de început",
"iex_select_end_date" => "Selecție dată de sfârșit",
"iex_group" => "Grup utilizatori",
"iex_name" => "Nume utilizator",
"iex_email" => "Adresă de email",
"iex_phone" => "Număr de telefon",
"iex_msgID" => "Chat ID",
"iex_lang" => "Limbă",
"iex_pword" => "Parolă",
"iex_all_groups" => "toate grupurile",
"iex_all_cats" => "toate categoriile",
"iex_all_users" => "toți utilizatorilor",
"iex_no_events_found" => "Niciun eveniment găsit",
"iex_file_created" => "Fișier creat",
"iex_write error" => "Eroare salvare fișier export. <br>Verificați drepturile de scriere pentru fișiere în folderul selectat",
"iex_invalid" => "invalid",
"iex_in_use" => "deja în uz",

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
"sty_css_intro" =>  "vaorile specificate în această pagină trebuie să fie conforme standardelor CSS",
"sty_preview_theme" => "Previzualizare temă",
"sty_preview_theme_title" => "Previzualizarea temei selectate în calendar",
"sty_stop_preview" => "Oprire previzualizare",
"sty_stop_preview_title" => "Oprirea afișării temei selectate în calendar",
"sty_save_theme" => "Salvare temă",
"sty_save_theme_title" => "Salvarea temei selectate în baza de date",
"sty_backup_theme" => "Backup temă",
"sty_backup_theme_title" => "Backup-ul temei din bază într-un fișier",
"sty_restore_theme" => "Restaurare temă",
"sty_restore_theme_title" => "Restaurarea temei din fișier",
"sty_default_luxcal" => "tema implicită LuxCal",
"sty_close_window" => "Închidere fereastră",
"sty_close_window_title" => "Se închide fereastra curentă",
"sty_theme_title" => "Titlu temă",
"sty_general" => "Generalități",
"sty_grid_views" => "Grilă / Vederi",
"sty_hover_boxes" => "Box-uri tip Hover",
"sty_bgtx_colors" => "Culoare Background/text",
"sty_bord_colors" => "Culoare Border",
"sty_fontfam_sizes" => "Tipuri Font/dimensiuni",
"sty_font_sizes" => "Dimensiuni fonturi",
"sty_miscel" => "Diverse",
"sty_background" => "Background",
"sty_text" => "Text",
"sty_color" => "Culoare",
"sty_example" => "Exemple",
"sty_theme_previewed" => "Mod previzualizare - puteți verifica tema direct în calendar. Folosiți butonul Stop Previzualizare când ați terminat.",
"sty_theme_saved" => "Temă salvate în baza de date",
"sty_theme_backedup" => "Temă salvată din bază într-un fișier:",
"sty_theme_restored1" => "Temă restaurată din:",
"sty_theme_restored2" => "Apăsați butonul <b>Salvare</b> pentru a salva tema în bază",
"sty_unsaved_changes" => "ATENȚIE – Aveți modificări nesalvate!\\nDacă închideți această fereastră toate modificările efectuate vor fi pierdute.", //don't remove '\\n'
"sty_number_of_errors" => "Numărul de erori din listă",
"sty_bgnd_highlighted" => "evidențiere background",
"sty_XXXX" => "calendar general",
"sty_TBAR" => "top bar calendar",
"sty_BHAR" => "bare, headere și reguli",
"sty_BUTS" => "butoane",
"sty_DROP" => "meniuri drop-down",
"sty_XWIN" => "ferestre popup",
"sty_INBX" => "inserare boxuri",
"sty_OVBX" => "boxuri supraimprimate",
"sty_BUTH" => "butoane - tip hover",
"sty_FFLD" => "forma câmpuri",
"sty_CONF" => "mesaj de confirmare",
"sty_WARN" => "mesaj de atenționare",
"sty_ERRO" => "mesaj de eroare",
"sty_HLIT" => "text evidențiat",
"sty_FXXX" => "font implicit",
"sty_SXXX" => "dimensiune implicită font",
"sty_PGTL" => "titluri pagină",
"sty_THDL" => "header tabele L",
"sty_THDM" => "header tabele M",
"sty_DTHD" => "header date",
"sty_SNHD" => "header secțiune",
"sty_PWIN" => "ferestre popup",
"sty_SMAL" => "text mic",
"sty_GCTH" => "hover - celulă zilnică",
"sty_GTFD" => "header celulă - prima zi din lună",
"sty_GWTC" => "coloană nr. săptămână / timp",
"sty_GWD1" => "prima zi din săptămână luna 1",
"sty_GWD2" => "prima zi din săptămână luna 2",
"sty_GWE1" => "weekend luna 1",
"sty_GWE2" => "weekend luna 2",
"sty_GOUT" => "luna adiacentă",
"sty_GTOD" => "celula zilei curente",
"sty_GSEL" => "celula zilei selectate",
"sty_LINK" => "URL și linkuri email",
"sty_CHBX" => "box eveniment de văzut",
"sty_EVTI" => "titlu eveniment în vederi",
"sty_HNOR" => "eveniment normal",
"sty_HPRI" => "eveniment privat",
"sty_HREP" => "eveniment repetitiv",
"sty_POPU" => "box popup hover",
"sty_TbSw" => "umbră top bar (0:nu 1:da)",
"sty_CtOf" => "ofset conținut",

//lcalcron.php
"cro_sum_header" => "SUMAR CRON JOB",
"cro_sum_trailer" => "SFÂRȘIT SUMAR",
"cro_sum_title_eve" => "EVENIMENTE EXPIRATE",
"cro_nr_evts_deleted" => "Numărul evenimentelor șterse",
"cro_sum_title_not" => "DE NOTIFICARE",
"cro_no_reminders_due" => "Nicio notificare",
"cro_due_in" => "Scadent în",
"cro_due_today" => "Astăzi",
"cro_days" => "zi(zile)",
"cro_date_time" => "Dată / oră",
"cro_title" => "Denumire",
"cro_venue" => "Locație",
"cro_description" => "Descriere",
"cro_category" => "Categorie",
"cro_status" => "Aprobat",
"cro_none_active" => "Niciun reminsder sau serviciu periodic activ",
"cro_sum_title_use" => "VERIFICARE CONT UTILIZATOR",
"cro_nr_accounts_deleted" => "Numărul de conturi șterse",
"cro_no_accounts_deleted" => "Niciun cont șters",
"cro_sum_title_ice" => "EVENIMENTE EXPORTATE",
"cro_nr_events_exported" => "Numărul de evenimente exportate în formatul iCalendar",

//messaging.php
"mes_no_msg_no_recip" => "Netrimis, nu ați introdus nicio adresă",

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
"<h3>Instrucțiuni editare - Mesajele de Informare</h3>
<p>Cand opțiunea este activată în pagina de Setări, mesajele de informare 
vor fi afișate într-o fereastră poziționață în imediata apropiere
a paginii calendarului. Mesajele pot conține tag-uri HTML și stiluri inline. 
Exemple cu diverse tipuri de mesaje și stiluri puteți găsi în fișierul 
'sidepanel/samples/info.txt'.</p>
<p>Mesajele de informare pot fi afișate într-un intervl de timp, de la o dată 
de început până la o data de final.
Fiecare mesaj trebuie precedat de o linie care să specifice perioada de afișare
cuprinsă între caracterele ~ . Textul dinaintea liniei care începe cu 
caracterului  ~ poate fi folosit pentru diverse note personale 
și nu va fi afișat în zona de infomare.</p><br>
<p>Format pentru data de început și sfârșit: ~m1.d1-m2.d2~, unde m1 și d1 
reprezintă luna și ziua de început iar m2 și d2 reprezintă luna și data de sfârșit
a mesajului. Dacă d1 este omis, se asumă automat prima zi a lunii.
Dacă se omite d2 se ia automat în considerare ultima zi a lunii.
Dacă sunt omise și m2 și d2 se ia în considerare ultima zi a lumii m1.</p>
<p>Exemple:<br>
<b>~4~</b>: Toată luna Aprilie<br>
<b>~2.10-2.14~</b>: 10 - 14 Februarie<br>
<b>~6-7~</b>: 1 Iunie - 31 Iulie<br>
<b>~12.15-12.25~</b>: 15 - 25 Decembrie<br>
<b>~8.15-10.5~</b>: 15 August - 5 Octombrie<br>
<b>~12.15~</b>: 15 Decembrie - 31 Decembrie</p><br>
<p>Sugestie: Începeți prin a crea o copie de siguranță (backup).</p>",

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
"<h3>Instrucțiuni de Lucru cu Baza de Date</h3>
<p>În aceast formular pot fi selectate și folosite următoarele funcții:</p>
<h6>Compactare Bază de date</h6>
<p>Când un utilizator șterge un eveniment, evenimentul este marcat ca 'șters', fără a fi eliminat efectiv din bază.
Utilizarea funcției 'Compactare Bază de Date' permite ștergerea permanentă a evenimentelor marcate, cu eliberarea spațiul ocupat de acestea.</p>
<h6>Back-up Bază de date</h6>
<p>Această funcție crează un back-up al întregii baze de date (structură tabele și conținut) în formatul .sql.
Fișierul de back-up este salvat în directorul <strong>files/</strong> în server, numele fișierului fiind de forma: 
<kbd>dump-cal-lcv-yyyymmdd-hhmmss.sql</kbd> (unde 'cal' = calendar ID, 'lcv' = calendar version iar 'yyyymmdd-hhmmss' reprezintă anul, luna, ziua, ore, minute, secunde).</p>
<p>Acest fișier de back-up permite refacerea bazei de date în cazul unui accident 
(pierderea bazei de date), prin intermediul funcției de restaurare descrisă mai jos sau prin intermediul utilitarului <strong>phpMyAdmin</strong>, oferit de cele mai multe servere web.</p>
<h6>Restaurare bază de date</h6>
<p>Această funcție va restaura baza de date a calendarului folosind înregistrările din fișierul indicat (fișier tip .sql). vedeți secțiunea 3 din admin_guide.html pentru explicații detaliate.</p>
<p>Când se restaurează baza de date TOATE DATELE CURENTE VOR FI ȘTERSE!</p>

<h6>Evenimente</h6>
<p>Această funcție va șterge sau va recupera evenimentele care apar în intervalul specificat. Dacă nu se specifică nicio dată înseamnă că nu există nicio limită de timp, astfel încât, dacă ambele câmpuri, cel de început și cel de sfârșit, sunt necompletate, TOATE EVENIMENTELE VOR FI ȘTERSE!</p>
<p><b>IMPORTANT</b>: Când baza este compactată (vezi mai sus), toate evenimentele marcate pentru ștergere vor fi eliminate definitiv, fără nicio posibilitate de recuperare (doar eventual prin restaurarea unui backup anterior)!</p>",

"xpl_import_csv" =>
"<h3>Instrucțiuni pentru Import CSV</h3>
<p>Acest formular permite importul de text formatat <strong>CVS (Comma Separated Values)</strong> pentru introducerea de evenimente în Calendar.</p>
<p>Ordinea coloanelor în fișierul CSV trebuie să fie: denumire, locație, ID categorie (vezi mai jos), data, data finală, ora de început și de sfârșit precum și descrierea evenimentului. Prima linie din fișierul CSV, (capul de tabel), este ignorată.</p>
<h6>Model Fișier CSV</h6>
<p>Un model de fișier CVS (fișier cu extensia .cvs) poate fi găsit în folderul '<strong>!luxcal-toolbox/</strong>' al distribuției LuxCal.</p>
<h6>Separator câmp</h6>
Separatorul de câmp poate fi orice caracter, spre exemplu virgula sau caracterul punct și virgulă, sau chiar caracterul tab: '\\t'). Separatorul de câmp trebuie să fie unic și nu trebuie să apară în text/datele din câmp.
<h6>Formatul pentru dată și oră</h6>
<p>Formatul selectat pentru dată și oră trebuie să corespundă formatului folosit în fișierul CVS importat.</p>
<p>If no start time (blank) is present, the event will be shown as a 'no time' event 
in the calendar. If the start time is 00:00 or 12:00am, the event will be shown as 
an 'all day' event in the calendar.</p>
<h6>Tabelul Categoriilor</h6>
<p>Calendarul utilizează numere (ID-uri) pentru specificarea categoriilor. ID-urile categoriilor din fișierul CVS trebuie să corespundă cu cele definite în calendar sau pot fi nule.</p>
<p>Spre exemplu, dacă doriți ca toate evenimentele să fie marcate ca 'important', ID-ul <strong>IMPORTANT</strong> trebuie să fie definit conform ID-ului din listă.</p>
<p class='hired'>Atenție: Nu importați mai mult de 100 de evenimente odată!</p>
<p>Pentru calendarul dumneavoastră, pînă acum, au fost definite următoarele categorii:</p>",

"xpl_import_user" =>
"<h3>Instrucțiuni Import Profile Utilizator</h3>
<p>Acest formular este folosit pentru a importa dintr-un fișier CSV (Comma Separated Values) 
profile utilizator în Calendarul LuxCal.</p>
<p>Pentru gestionarea corectă a caracterelor speciale, fișierul CSV trebuie să fie codat UTF-8.</p>
<h6>Field separator</h6>
<p>Câmpul separator poate fi orice caracter, spre exemplu virgula, punct și virgulă etc.
Câmpul separator trebuie să fie unic și să nu fie folosit în text.</p>
<h6>ID implicit grup utilizator</h6>
<p>Dacă în fișierul CSV un ID de grup utilizator a fost lăsat necompletat, 
Calendarul va folosi ID-ul implicit de grup.</p>
<h6>Parola implicită</h6>
<p>Dacă în fișierul CSV o parolă de utilizator a fost lăsată necompletată, 
Calendarul va folosi parola implicită.</p>
<h6>Înlocuire utilizatori existenți</h6>
<p>Dacă check-box-ul <b>Înlocuire utilizatori</b> a fost selectat, toți utilizatorii, cu excepția utilizatorului public și al administratorilor, vor fi șterși înainte de importul noilor profile de utilizator.</p>
<br>
<h6>Fișier exemplu profile utilizatori</h6>
<p>Un fișier exemplu de profile utilizator (.csv) poate fi găsit în folderul '!luxcal-toolbox/'
al instalației LuxCal.</p>
<h6>Câmpuri în fișierul CSV</h6>
<p>Ordinea coloanelor în fișierele CSV trebuie să fie cea prezentată mai jos.
Dacă primul rând al fișierului conține numele coloanelor, acesta va fi ignorat.</p>
<ul>
<li>ID grup utilizator: trebuie să aibă corespondent în grupul utilizatorilor din Calendar 
(vezi tabelul de mai jos). Dacă acesta nu este completat, utilizatorul corespunzător 
va fi alocat în grupul implicit de utilizatori</li>
<li>Nume utilizator: obligatoriu</li>
<li>Adresă email: obligatoriu</li>
<li>Număr telefon: opțional</li>
<li>Telegram chat ID: optional</li>
<li>Limba interfață: opțional. Ex. English, Dansk. Dacă câmpul rămâne 
necompletat, limba implicită va fi cea selectată din pagina de Setări.</li>
</ul>
<p>Câmpurile necompletate trebuie indicate prin două ghilimele.
Câmpurile goale de la sfârșitul fiecărei linii pot fi neglijate.</p>
<p class='hired'><b>Atenție</b>: NU importați mai mult de 60 de profile o dată!</p>
<h6>Tabel ID grupuri utilizator</h6>
<p>Pentru Calendar au fost definite următoarele grupuri:</p>",

"xpl_export_user" =>
"<h3>Instrucțiuni Export Profile Utilizator</h3>
<p>Acest formular este utilizat pentru extragerea și exportul <strong>Profilelor Utilizator</strong> 
din calendar.</p>
<p>Fișierele vor fi create în folderul 'files/' din server 
în formatul CSV (Comma Separated Value).</p>
<h6>Nume fișier</h6>
Dacă nu este specificat, numele implict folosit va fi numele calendarului
urmat de sufixul '_users'. Extensia va fi setată în mod automat în <b>.csv</b>.</p>
<h6>Grup Utilizatori</h6>
Doar profilele utilizatorilor din grupul selectat vor fi exportate.
Dacă se selectează opțiunea 'toate grupurile', profilele utilizatorilor în fișierul 
destinație vor fi sortate după grup</p>
<h6>Separator câmpuri</h6>
<p>Câmpul separator poate fi orice caracter, spre exemplu virgulă, punct și virgulă etc.
Câmpul separator trebuie să fie unic și să nu fie folosit în text.</p><br>
<p>Fișierele existente în folderul 'files/' din server, care au acest nume, vor fi suprascrise.</p>
<p>Ordinea coloanelor din fișier va fi: ID grup, nume utilizator
adresă de email, număr de telefon, limba și parola.<br>
<b>Notă:</b> Parolele exportate în fișier sunt codate și nu pot fi afișate în clar.</p><br>
<p>Când fișierul .csv este <b>descărcat</b>, la numele acestuia vor fi adăugate automat 
data și ora curentă.</p><br>
<h6>Fișier model Profile Utilizator</h6>
<p>Un model de fișier cu profile utilizator (cu extensia .csv) 
poate fi găsit în folderul '!luxcal-toolbox/' din server.</p>",

"xpl_import_ical" =>
"<h3>Instrucțiuni pentru Import iCalendar </h3>
<p>Acest formular permite importul fișierelor de tipul <strong>iCalendar</strong> pentru introducerea de evenimente în Calendarul LuxCal.</p>
<p>Fișierul trebuie să respecte specificațiile prevăzute în standardul [<u><a href='https://tools.ietf.org/html/rfc5545' 
target='_blank'>RFC5545</a></u>] al Internet Engineering Task Force.</p>
<p>Vor fi importate doar evenimentele importante; toate celelalte componente iCal components, ca: 'De Făcut', 'Jurnal', 'Liber / 
Ocupat', 'Fus Orar' și 'Alarme' vor fi ignorate.</p>
<h6>Model de fișier iCal</h6>
<p>Un exemplu de fișier iCalendar (fișier cu extensia .ics) poate fi găsit în folderul '<strong>!luxcal-toolbox/</strong>' al distribuției LuxCal.</p>
<h6>Ajustări fus orar</h6>
<p>Dacă fișierul iCalendar conține evenimente definite după un alt fus orar, va trebui să folosiți această opțiune pentru ajustarea orelor asociate evenimentelor.</p>
<h6>Tabelul Categoriilor</h6>
<p>Calendarul utilizează numere (ID-uri) pentru specificarea categoriilor. ID-urile categoriilor din fișierul iCalendar trebuie să corespundă cu cele definite în calendar, sau pot fi nule.</p>
<p class='hired'>Atenție: Nu importați mai mult de 100 de evenimente o dată!</p>
<p>Pentru calendarul dumneavoastră, până acum, au fost definite următoarele categorii:</p>",

"xpl_export_ical" =>
"<h3>Exportul fișierelor iCalendar</h3>
<p>Acest formular permite exportul evenimentelor din calendar în formatul <strong>iCalendar</strong>.</p>
<p>Numele fișierului <b>iCal nume fișier</b> (fără extensie) este opțional. Fișierul creat va fi 
salvat în folderul \"files/\" din server, cu numele specificat, sau, dacă nu se specifică nimic, 
cu numele implicit al calendarului. Extensia fișierului va fi <b>.ics</b>.
Dacă în folderul \"files/\" există deja un fișier cu ecest nume, el va fi suprascris.</p>
<p>Opțional se poate adăuga și o descriere sumară a fișierului (ex. 'Activități 2024') care va apare în head-erul fișierului iCal exportat.</p>
<p><b>Filtru</b>: Evenimentele exportate pot fi filtrate după:</p>
<ul>
<li>proprietar eveniment</li>
<li>categorie</li>
<li>data de început</li>
<li>data adăugării/modificării</li>
</ul>
<p>Fiecare filtru este opțional, lipsa filtrului determinând exportul tuturor evenimentelelor</p>
<br>
<p>Fișierul exportat respectă specificațiile prevăzute în standardul [<u><a href='https://tools.ietf.org/html/rfc5545' target='_blank'>RFC5545</a></u>] al Internet Engineering Task Force</p>
<p>Când se descarcă fișierul iCal exportat, la numele acestuia vor fi adăugate în mod automat data și ora.</p>
<h6>Exemplu de fișier iCal</h6>
<p>Un exemplu de fișier iCalendar (fișier cu extensia .ics) poate fi găsit în folderul '<strong>!luxcal-toolbox/</strong>' al distribuției LuxCal.</p>",

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
