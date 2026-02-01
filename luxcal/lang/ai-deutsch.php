<?php
/*
= LuxCal admin interface language file =

This file has been produced by LuxSoft. Bitte senden Sie Kommentare / Verbesserungen an rb@luxsoft.eu.
2011-05-31 übersetzt von Alfred Bruckner
2018-02-09 aktualisiert von Markus Windgassen
2020.11.29 aktualisiert von Piotr Linski, Rellingen, Germany.
2020.01.06 aktualisiert von Stefan Hain, Braunschweig, Germany.

This file is part of the LuxCal Web Calendar.
*/

$ax = array(

//general
"none" => "Keine",
"no" => "nein",
"yes" => "ja",
"own" => "Eigene",
"all" => "alle",
"or" => "oder",
"back" => "Zurück",
"ahead" => "Voraus",
"close" => "Schliessen",
"always" => "Immer",
"at_time" => "@", //Datum- und Zeit- Trennzeichen (Beispiel: 30-01-2020 @ 10:45)
"times" => "Zeiten",
"cat_seq_nr" => "Kategorie Sequenznummer",
"rows" => "Zeilen",
"columns" => "Spalten",
"hours" => "Stunden",
"minutes" => "Minuten",
"user_group" => "Benutzergruppe",
"event_cat" => "Kategorie",
"email" => "Email",
"telegram" => "Telegram",
"sms" => "SMS",
"id" => "ID",
"username" => "Benutzername",
"password" => "Passwort",
"public" => "Öffentlich",
"logged_in" => "Eingeloggt",
"pw_no_chars" => "Characters <, > and ~ not allowed in password",

//settings.php - fieldset headers + general
"set_general_settings" => "Allgemein",
"set_navbar_settings" => "Navigations Balken",
"set_event_settings" => "Termine",
"set_user_settings" => "Benutzer",
"set_upload_settings" => "Datei Uploads",
"set_reminder_settings" => "Erinnerungen",
"set_perfun_settings" => "Wiederkehrende Funktion (nur relevant, wenn cron job definiert wurde)",
"set_sidebar_settings" => "Stand-Alone-Seitenleiste (nur relevant, wenn aktiviert)",
"set_view_settings" => "Anzeige",
"set_dt_settings" => "Datum/Zeit",
"set_save_settings" => "Speichern",
"set_test_mail" => "Test E-Mail",
"set_mail_sent_to" => "Test E-mail geschickt an",
"set_mail_sent_from" => "Diese Test E-Mail wurde von Ihrer Einstellungsseite des Kalenders versandt",
"set_mail_failed" => "Senden der Testmail fehlgeschlagen - Empfänger",
"set_missing_invalid" => "Fehlende oder ungültige Einstellungen (Hintergrund hervorgehoben)",
"set_settings_saved" => "Einstellungen gespeichert",
"set_save_error" => "Datenbank Fehler - Abspeichern der Einstellungen fehlgeschlagen",
"hover_for_details" => "Für Hilfe Mauszeiger über die Beschreibung bewegen",
"default" => "Standard",
"enabled" => "Aktiviert",
"disabled" => "Deaktiviert",
"pixels" => "Pixel",
"warnings" => "Warnungen",
"notices" => "Hinweise",
"visitors" => "Besucher",
"height" => "Height",
"no_way" => "Sie haben keine Rechte für diese Aktion",

//settings.php - calendar settings
"versions_label" => "Versionen",
"versions_text" => "• Kalender Version, gefolgt von der benutzten Datenbank<br>• PHP Version<br>• Datenbank Version",
"calTitle_label" => "Titel",
"calTitle_text" => "Wird in der Kopfzeile angezeigt und in E-Mail Benachrichtigungen verwendet.",
"calUrl_label" => "URL",
"calUrl_text" => "Die Webseite des Kalenders.",
"calEmail_label" => "E-Mail Adresse des Kalenders",
"calEmail_text" => "E-Mail Adresse für das Senden und Entphangen von Benachrichtigungs-E-Mails.<br>Format: 'E-Mail' or 'Name &#8826;E-Mail&#8827;'.",
"logoPath_label" => "Pfad / Name des Logo-Bildes",
"logoPath_text" => "Wenn angegeben wird ein Logo-Bild in der linken oberen Ecke des Kalenders angezeigt. Wenn außerdem ein Link zur Hauptseite angegeben wurde (siehe unten) dient das Logo als Link zur Hauptseite . Das Logo sollte eine maximale Höhe und Breite von 70 Pixel haben",
"logoXlPath_label" => "Path/name of log-in logo image",
"logoXlPath_text" => "If specified, a logo image of the specified height will be displayed on the Log In page below the Log In form.",
"backLinkUrl_label" => "Link zur Hauptseite",
"backLinkUrl_text" => "URL der Hauptseite. Falls angegeben, wird ein zurück Feld auf der linken Seite angezeigt, welche auf diese URL verweist.<br>zum Beispiel auf die Hauptseite, von der der Kalender gestartet wurde. If a logo path/name has been specified (see above), then no Back button will be displayed, but the logo will become the back link instead.",
"timeZone_label" => "Zeitzone",
"timeZone_text" => "Die Zeitzone die zur Berechnung der aktuellen Zeit verwendet wird.",
"see" => "siehe",
"notifChange_label" => "Sende Benachrichtigung bei Änderungen im Kalender",
"notifChange_text" => "Wenn ein Benutzer einen Termin erstellt, ändert oder löscht wird eine Benachrichtigung an den angegebenen Empfänger versendet.",
"chgRecipList" => "semicolon separated recipient list",
"maxXsWidth_label" => "Max. Breite kleiner Bildschirme",
"maxXsWidth_text" => "Für Bildschirme mit einer kleineren als der hier angegebenen Breite in Pixeln wird der Kalender in einem speziellen responsiven Modus angezeigt und einige weniger wichtige Elemente werden weggelassen.",
"rssFeed_label" => "RSS Feed Links",
"rssFeed_text" => "Falls aktiviert: Für Benutzer mit mindestens 'Ansicht' Rechten wird ein RSS Feed Verweis in der Fußzeile des Kalenders sichtbar sein und ein RSS Feed wird zum HTML head des Kalenders hinzugefügt.",
"logging_label" => "Kalenderdaten protokollieren",
"logging_text" => "Der Kalender kann Fehler, Warnungen, Hinweise und Benutzerdaten protokollieren. Fehler werden immer protokolliert. Das Protokollieren von Warnungen, Hinweisen und Benutzerdaten kann einzeln durch markieren des entsprechenden Kontrollkästchens aktiviert oder deaktiviert werden. Fehler, Warnungen und Hinweise werden in der Datei 'logs/luxcal.log' protokolliert, Benutzerdaten in den Dateien 'logs/hitlog.log' und 'logs/botlog.log'.<br>Hinweis: PHP Fehler, Warnungen und Hinweise werden an unterschiedlichen Stellen, abhängig vom jeweiligen ISP gespeichert.",
"maintMode_label" => "PHP Wartungsmodus",
"maintMode_text" => "Wenn aktiviert, in the PHP scripts data submitted via the note (message) function and data stored in the 'note' variable werden in der Fußzeile des Kalenders angezeigt.",
"reciplist" => "Die Empfängerliste kann Benutzernamen, E-Mail-Adressen, Telefonnummern, Telegram chat IDs und Dateinamen von Dateien mit Empfängern(in eckige Klammern eingeschlossen) enthalten, getrennt durch Semikolons. Dateien mit Empfängern, die einen Empfänger pro Zeile enthalten, sollten im Verzeichnis 'reciplists' liegen. Wenn leer gelassen, die Standard Datei-Erweiterung ist .txt",
"calendar" => "Kalender",
"user" => "Benutzer",
"database" => "Datenbank",

//settings.php - navigation bar settings.
"contact_label" => "Kontaktschaltfläche",
"contact_text" => "Wenn aktiviert: Eine Kontakt-Schaltfläche wird im Seiten-Menü angezeigt. Beim Klick darauf wird ein Kontaktformular geöffnet, mit dem man dem Kalender-Administrator eine Nachricht senden kann.",
"optionsPanel_label" => "Optionen Menüs",
"optionsPanel_text" => "Aktiviert/Deaktiviert Menüs im Optionen Bereich.<br>• Das Kalender-Menü ist für den Administrator verfügbar, um zwischen Kalendern umzuschalten. (Nur sinnvoll, wenn mehrere Kalender installiert sind)<br>•Das Ansicht-Menü kann zum Auswählen einer der Kalender-Ansichten genutzt werden.<br>• Das Gruppen-Menü kann benutzt werden um nur Termine anzuzeigen, die von einem Benutzer der ausgewählten Gruppe erstellt wurden.<br>• Das Benutzer-Menü kann genutzt werden, um nur Termine anzuzeigen, die vom ausgewählten Benutzer erstellt wurden.<br>• Das Kategorie-Menü kann genutzt werden, um nur Termine anzuzeigen, die zur ausgewählten Kategorie gehören.<br>• Das Sprachen-Menü kann genutzt werden, um die Anzeige-Sprache auszuwählen. (Nur sinnvoll, wenn mehrere Sprachen installiert sind)<br>Hinweis: Wenn keine Menüs ausgewählt sind. wird keine Optionen-Schaltfläche angezeigt.",
"calMenu_label" => "Kalender",
"viewMenu_label" => "Ansicht",
"groupMenu_label" => "Gruppen",
"userMenu_label" => "Benutzer",
"catMenu_label" => "Kategorien",
"langMenu_label" => "Sprache",
"availViews_label" => "Verfügbare Kalender Ansichten",
"availViews_text" => "Kalenderansichten, die für öffentliche und eingeloggte Benutzer verfügbar sind, angegeben durch Komma-separierte Listen mit Nummern der Ansichten. Die Bedeutung der Nummern: <br>1: Jahres-Ansicht<br>2: Monats-Ansicht (7 Tage)<br>3: Arbeits-Monats-Ansicht<br>4: Wochenansicht (7 Tage)<br>5: Arbeits-Wochen-Ansicht<br>6: Tages-Ansicht<br>7: Anstehende-Termine-Ansicht<br>8: Änderungen-Ansicht<br>9: Matrix-Ansicht (Kategorien)<br>10: Matrix-Ansicht (Benutzer)<br>11: Gantt-Chart-Ansicht",
"viewButtonsL_label" => "Schaltflächen für Ansichten in der Navigationsleiste (Große Displays)",
"viewButtonsS_label" => "Schaltflächen für Ansichten in der Navigationsleiste (Kleine Displays)",
"viewButtons_text" => "Zeige Schaltflächen für Ansichten in der Navigationsleiste für öffentliche oder eingeloggte Benutzer, angegeben durch eine Komma-separierte Liste mit Nummern der Ansichten.<br>Wenn eine Nummer in der Liste angegeben wurde, wird die entsprechende Schaltfläche angezeigt. Wenn keine Nummer angegeben wird, wird keine Schaltfläche angezeigt.<br>Bedeutung der Nummern:<br>1: Jahr<br>2: Ganzer Monat<br>3: Arbeits-Monat<br>4: Ganze Woche<br>5: Arbeits-Woche<br>6: Tag<br>7: Anstehende<br>8: Veränderungen<br>9: Matrix-Kategorien<br>10: Matrix-Benutzer<br>11: Gantt Chart<br>Die Reihenfolge der Nummern bestimmt die Reihenfolge der Schaltflächen.<br>Beispiel: '2,4' bedeutet: Zeige Schaltflächen für 'Ganzer Monat' und 'Ganze Woche'.",
"defaultViewL_label" => "Ansicht beim Start (Große Displays)",
"defaultViewL_text" => "Standard Kalender Ansicht beim Start für öffentliche und eingeloggte Benutzer bei der Nutzung von großen Displays,<br>Empfohlen: Monat.",
"defaultViewS_label" => "Ansicht beim Start (Kleine Displays)",
"defaultViewS_text" => "Standard Kalender Ansicht beim Start für öffentliche und eingeloggte Benutzer bei der Nutzung von kleinen Displays,<br>Empfohlen: Anstehende.",
"language_label" => "Benutzersprache (public user)",
"language_text" => "For public (not logged in) users the language set for the browser user interface will be used for the calendar as well. If the browser language is not a valid calendar language, this default language will be used.<br>Note: Die Dateien ui-{sprache}.php, ai-{sprache}.php, ug-{sprache}.php und ug-layout.png müssen im lang/ Verzeichnis vorhanden sein. {sprache} = ausgewählte Sprache. Dateinamen müssen in Kleinbuchstaben sein!",
"birthday_cal_label" => "PDF Birthday Calendar",
"birthday_cal_text" => "If enabled, an option 'PDF File - Birthday' will appear in the Side Menu for users with at least 'view' rights. See the admin_guide.html - Birthday Calendar for further details",
"sideLists_label" => "Approve, Todo, Upcoming lists",
"sideLists_text" => "If enabled, an option to show the respective list will appear in the Side Menu. The 'Events to be approved' list will only be available for users with at least 'manager' rights.",
"toapList_label" => "To approve list",
"todoList_label" => "To do list",
"upcoList_label" => "Upcoming list",

//settings.php - events settings.
"privEvents_label" => "Eingeben von privaten Terminen",
"privEvents_text" => "Private Termine koennen nur vom Benutzer gesehen werden, der diese erstellt hat.<br>Aktiviert: Benutzer koennen private Termine eingeben.<br>Standard: beim Hinzufügen von Terminen ist die 'privat' checkbox im Terminfenster standardmäßig aktiviert.<br>Immer: beim Hinzufügen neuer Termine, werden diese immer als privat eingestellt, das 'privat' Feld wird in diesem Fall nicht angezeigt.",
"venueInput_label" => "Specifying venues",
"venueInput_text" => "In the Event window specifying a venue can be done either by typing the venue or by selecting a venue from a pre-defined list. If Free text is selected, the user can type the venue, if List is selected the user can select a venue from a drop-down list and when Both is selected, the user can choose between the two.<br> When a drop-down list is used, the 'files' folder must contain a file called venues.txt with one venue per line.",
"timeDefault_label" => "Hinzufügen neuer Terminen, Zeit standard",
"timeDefault_text" => "When adding events, in the Event window the default way the event time fields appear in the event form can be set as follows:<br>• show times: The start and end time fields are shown and ready to be completed<br>• all day: The All Day check box is checked, no start and end time fields are shown<br>• no time: The No Time check box is checked, no start and end time fields are shown.",
"evtDelButton_label" => "Schaltfläche 'Löschen' im Terminfenster anzeigen",
"evtDelButton_text" => "Deaktiviert: Die Löschen-Schaltfläche im Terminfenster wird nicht angezeigt. Damit können Benutzer mit EDIT Rechten keine Termine löschen.<br>Aktiviert: Die Löschen-Schaltfläche im Terminfenster ist für alle Benutzer sichtbar.<br>Manager: Die Löschen-Schaltfläche im Terminfenster ist nur für Benutzer mit mindestens 'manager' Rechten sichtbar.",
"eventColor_label" => "Terminfarbe basiert auf",
"eventColor_text" => "In den unterschiedlichen Ansichten werden Termine in der ausgwählten Hintergrundfarbe für den Gruppe der Ersteller oder der Kategorie angezeigt.",
"defVenue_label" => "Standard Veranstaltungsort",
"defVenue_text" => "Hier kann ein Ort eingetragen werden, der beim Erstellen eines Termines in das Ort-Feld kopiert wird.",
"xField1_label" => "Zusätzliches Feld 1",
"xField2_label" => "Zusätzliches Feld 2",
"xFieldx_text" => "Optionales Text Feld. Wenn dieses Feld in einr Terminvorlage im Ansichten-Abschnitt vorkommt, wird das Feld als frei formatierbares Textfeld im Terminfenster hinzugefügt und bei den Terminen in allen Ansichten und Seiten des Kalenders angezeigt.
<br>• : optionale Bezeichnung für das Zusatzfeld  (max. 15 Zeichen). Beispiele: 'E-Mail Adresse', 'Webseite', 'Telefonnummer'<br>• Mindest-Benutzerrechte: dieses Feld wird nur für die Benutzer mit den angegeben oder mehr  Rechten sichtbar sein.",
"evtWinSmall_label" => "Reduziertes Ereignisfenster",
"evtWinSmall_text" => "Beim erstellen/ändern von Terminen wird nur eine Auswahl von Eingabefeldern angezeigt. Um alle Felder anzuzeigen kann ein Pfeil angeklickt werden.",
"emojiPicker_label" => "Emoji picker in Event window",
"emojiPicker_text" => "When enabled, in the Event Add/Edit window an emoji picker can be selected to add emoji to the event title and to the description fields.",
"mapViewer_label" => "URL einer Karten-Ansicht",
"mapViewer_text" => "Wenn eine Karten-Ansicht angegeben ist, werden Adressen im Orts-Feld, die mit Ausrufezeichen umschlossen sind, als Adress-Schaltfläche in der Kalenderansicht angezeigt. Wenn man diese Schaltfläche mit der Maus überfährt, wird die Adressse als Text angezeigt und beim Klicken wird ein neues Fenster mit dem Karten-Ansicht geöffnet.<br>Es sollte die komplette URL der kartenansicht angegeben werden, sodass die Adresse angehängt werden kann.<br>Beispiele:<br>Google Maps: https://maps.google.com/maps?q=<br>OpenStreetMap: https://www.openstreetmap.org/search?query=<br>Wenn dieses Feld leer gelassen wird, werden Adressen im Orts-Feld nicht als Schaltfläche angezeigt.",
"evtDrAndDr_label" => "Event drag and drop",
"evtDrAndDr_text" => "When enabled, in Year view, Month view and in the mini calendar on the side panel, events can be moved or copied from one day to an other day by means of Drag and Drop. If 'manager' is selected, only users with at least manager rights can use this feature. See the admin_guide.html for a detailed description.",
"free_text" => "Free text",
"venue_list" => "Venue list",
"both" => "Both",
"xField_label" => "Bezeichnung",
"show_times" => "show times",
"check_ald" => "all day",
"check_ntm" => "no time",
"min_rights" => "Mindest-Benutzerrechte",
"no_color" => 'keine Farbe',
"manager_only" => 'Manager',

//settings.php - user accounts settings.
"selfReg_label" => "Eigene Anmeldung",
"selfReg_text" => "Erlaubt Benutzern sich selbst anzumelden um Zugriff auf den Kalender zu haben.<br>Benutzergruppe, zu der der sich selbst angemeldetete Benutzer hinzugefügt wird.",
"selfRegQA_label" => "Frage/Antwort zur Selbstregistrierung",
"selfRegQA_text" => "Wenn die eigene Anmeldung aktiviert ist, wird beim Anmeldevorgang folgende Frage gestellt und die Anmeldung ist nur möglich, wenn eine richtige Antwort eingetragen wird. Wenn das Frage-Feld leer bleibt, wird keine Frage gestellt.",
"selfRegNot_label" => "Benachrichtigung bei Anmeldung",
"selfRegNot_text" => "Sende eine E-Mail an die Kalender Adresse wenn eine Eigene Anmeldung stattgefunden hat.",
"restLastSel_label" => "Wiederherstellen der letzten Auswahl des Benutzers",
"restLastSel_text" => "Die letzte Auswahl des Benutzers (Einstellungen des Optionen-Bereiches) wird gespeichert und beim nächsten Besuch des Benutzers wieder hergestellt. If the user does not log in during the specified number of days, the values will be lost.",
"answer" => "Antwort",
"exp_days" => "days",
"view" => "Anschauen",
"post_own" => "Eigene",
"post_all" => "Alle",
"manager" => 'post/manager',

//settings.php - view settings.
"templFields_text" => "Bedeutung der Nummern:<br>1: Orts-Feld<br>2: Termin-Kategorie-Feld<br>3: Beschreibungs-Feld<br>4: Extra Feld 1 (siehe unten)<br>5: Extra Feld 2 (siehe unten)<br>6: E-Mail Benachrichtigungs Daten (nur wenn die Benachrichtigung angefragt wurde)<br>7: Datum/Zeit hinzugefügt/geändert und der/die dazugehörigen Benutzer<br>8: Angehängte Pdf-, Bild- oder Video Dateien als Hyperlinks.<br>Die Reihenfolge der Nummern bestimmt die Reihenfolge der angezeigten Felder.",
"evtTemplate_label" => "Terminvorlagen",
"evtTemplate_text" => "Die Terminfelder, die in den üblichen Kalenderansichten angezeigt werden, sowie in der Ansicht der anstehenden Termine  und in der Hover-Box mit Termin-Details können hier mit Hilfe einer Abfolge von Nummern angegeben werden.<br>Wenn eine Nummer in der Abfolge angegeben wurde, wird das dazugehörige Feld angezeigt werden.",
"evtTemplPublic" => "Public users",
"evtTemplLogged" => "Logged-in users",
"evtTemplGen" => "Gesamtansicht",
"evtTemplUpc" => "'Anstehende Termine' Ansicht",
"evtTemplPop" => "Hover box",
"sortEvents_label" => "Termine sortieren nach Zeiten oder Kategorien",
"sortEvents_text" => "In den verschiendenen Ansichten können Termine nach den folgenden Kriterien sortiert werden:<br>• Termin Zeiten<br>• Kategorie Reihenfolge  ",
"yearStart_label" => "Start-Monat in der Jahresansicht",
"yearStart_text" => "Wenn ein Start-Monat konfiguriert wurde (1 - 12), beginnt die Anzeige in der Jahresansicht mit diesem Monat auch beim Wechsel zu vorigen oder darauffolgenden Jahren.<br>Der Wert 0 hat eine spezielle Bedeutung: der Start-Monat wird vom aktuellen Datum abgeleitet und wird in der ersten Reihe der Monate angezeigt.",
"YvRowsColumns_label" => "Zeilen und Spalten für Jahresansicht",
"YvRowsColumns_text" => "Anzahl der angezeigten Reihen der Jahresansicht.<br>Empfehlung: 4, wodurch 12 oder 16 Monate angezeigt werden.<br>Anzahl der angezeigten Monate in einer Reihe der Jahresansicht.<br>Empfehlung: 3 oder 4.",
"MvWeeksToShow_label" => "Anzahl der angezeigten Wochen in der Monatsansicht",
"MvWeeksToShow_text" => "Anzahl der in der Monatsansicht angezeigten Wochen.<br>Empfehlung: 10, wodurch 2.5 Monate angezeigt werden.<br>Die Werte 0 und 1 haben eine spezielle Bedeutung:<br>0: genau einen Monat anzeigen - die Tage vor und nach dem Monat werden leer dargestellt.<br>1: genau einen Monat anzeigen - Tage vor und nach dem Monat werden mit ihren Terminen dargestellt.",
"XvWeeksToShow_label" => "In der Matrixansicht anzuzeigende Wochen",
"XvWeeksToShow_text" => "Anzahl der Kalenderwochen, die in der Matrixansicht angezeigt werden sollen.",
"GvWeeksToShow_label" => "In der Gantt-Chartansicht anzuzeigende Wochen",
"GvWeeksToShow_text" => "Anzahl der Kalenderwochen, die in der Gantt-Chartansicht angezeigt werden sollen.",
"workWeekDays_label" => "Arbeitstage",
"workWeekDays_text" => "Die als Arbeitstage farbig dargestellte Wochentage in den Kalender-Ansichten, die beispielsweise auch in den Wochen der Arbeits-Monats-Ansicht und der Arbeits-Wochen-Ansicht angezeigt werden.<br>Alle Nummern der Arbeitstage eingeben.<br>z.B. 12345: Montag - Freitag<br>Nicht eingegebene Tage werden wie Wochenend-Tage behandelt.",
"weekStart_label" => "Erster Tag der Woche",
"weekStart_text" => "Geben Sie bitte die Tagnummer des ersten Wochentages ein.",
"lookBackAhead_label" => "Vorschau auf anstehende Termine",
"lookBackAhead_text" => "Anzahl der Tage die zur Ermittlung der Termine in der Anstehende-Termine-Ansicht, der Todo Liste und RSS feeds verwendet wird.",
"searchBackAhead_label" => "Standard Anzahl der Tage zurück/nach vorn bei der Suche.",
"searchBackAhead_text" => "Wenn auf der Suchseite keine Daten eingegeben werden, wird automatisch diese Standard Anzahl von Tagen für die Suche zurück bzw. nach vorn genommen.",
"dwStartEndHour_label" => "Erste und letzte Stunde in der Tag- und Wochen-Ansicht",
"dwStartEndHour_text" => "Uhrzeit zu der ein normaler Tag mit Terminen beginnt/ended.<br>Eine Einstellung auf z.B. 6 - 18 vermeidet in der Woche/Tag-Ansicht die Anzeige der ungenützten Zeit zwischen Mitternacht und 6:00 und 18:00 und Mitternacht.<br>Auch die Zeit-Auswahl-Anzeige, die zum Eingeben der Zeit genutzt werden kann, beginnt und endet mit diesen Uhrzeiten.",
"dwTimeSlot_label" => "Zeitraster in der Tag/Wochen-Ansicht",
"dwTimeSlot_text" => "Zeitraster der Tag/Wochen-Ansicht in Minuten.<br>Dieser Wert bestimmt zusammen mit der &quotErste Stunde&quot und der &quotLetste Stunde&quot Einstellung die Anzahl der Zeilen in der Tag/Wochen-Ansicht",
"dwTsInterval" => "Zeitraster",
"dwTsHeight" => "Höhe",
"evtHeadX_label" => "Terminlayout in der Monats-, Wochen- und Tagesansicht",
"evtHeadX_text" => "Vorlagen mit Platzhaltern für Terminfelder, die angezeigt werden sollen. Die folgenden Platzhalter können verwendet werden:<br>#ts - Start-Zeit<br>#tx - Start- und End-Zeit<br>#e - Termin-Titel<br>#o - Termin-Ersteller<br>#v - Ort<br>#lv - Ort mit Beschriftung 'Ort:' davor<br>#c - Kategorie<br>#lc - Kategorie mit Beschriftung 'Kategorie:' davor<br>#a - Alter (siehe Hinweis unten)<br>#x1 - Extra Feld 1<br>#lx1 - Extra Feld 1 mit der Beschriftung von der Einstellungen-Seite davor<br>#x2 - Extra Feld 2<br>#lx2 - Extra Feld 2  mit der Beschriftung von der Einstellungen-Seite davor<br>#/ - neue Zeile<br>Die Felder werden in der angegebenen Reihenfolge angezeigt. Zeichen, die nicht zu den Platzhaltern gehören, werden nicht verändert und als Teil des Termins angezeigt.<br>HTML-Tags sind in der Vorlage erlaubt. Z.B. &lt;b&gt;#e&lt;/b&gt;.<br>Das | Zeichen kann benutzt werden, um die Vorlage in Bereiche aufzuteilen. Wenn innerhalb eines Bereiches alle Platzhalter zusammen eine leere Zeichenfolge ergeben, dann wird der ganze Bereich verworfen.<br>Hinweis: Das Alter wird angezeigt, wenn der Termin zu einer Kategorie gehört, deren 'Wiederholung' auf 'jedes Jahr' gesetzt ist und das year of birth in Klammern irgendwo in der Termin Beschreibung oder eines der zusätzlichen Felder erwähnt ist.",
"monthView" => "Monatsansicht",
"wkdayView" => "Wochen-/Tagesansicht",
"ownerTitle_label" => "Zeige den Terminersteller im Titel",
"ownerTitle_text" => "In den verschiedenen Kalender Ansichten den Termin-Ersteller vor dem termin-Titel anzeigen.",
"showSpanel_label" => "Seiten-Bereich in der Kalender Ansichten",
"showSpanel_text" => "In der Kalender Ansichten können rechts neben dem eigentlichen Kalender folgende Elemente angezeigt werden:<br>• Ein Mini-Kalendar, mit dem man zurück oder nach vorn schauen kann ohne das Datum des eigentlichen Kalenders zu ändern<br>• ein Gestaltungs-Bild korrespondierend zum aktuellen Monat<br>• ein Info-Bereich, um Nachrichten/Hinweise zu bestimmte Zeiträume zu schreiben.<br>>Per item a comma-separated list of view numbers can be specified, for which the side panel should be shown.<br>Possible view numbers:<br>0: all views<br>1: Jahres-Ansicht<br>2: Monats-Ansicht (7 Tage)<br>3: Arbeits-Monats-Ansicht<br>4: Wochenansicht (7 Tage)<br>5: Arbeits-Wochen-Ansicht<br>6: Tages-Ansicht<br>7: Anstehende-Termine-Ansicht<br>8: Änderungen-Ansicht<br>9: Matrix-Ansicht (Kategorien)<br>10: Matrix-Ansicht (Benutzer)<br>11: Gantt-Chart-Ansicht.<br>If 'Today' is checked, the side panel will always use the date of today, otherwise it will follow the date selected for the main calendar.<br>Siehe admin_guide.html für Seite-Bereich Details.",
"spMiniCal" => "Mini Kalender",
"spImages" => "Bilder",
"spInfoArea" => "Infobereich",
"spToday" => "Today",
"topBarDate_label" => "Show current date on top bar",
"topBarDate_text" => "Enable/disable the display of the current date on the calendar top bar in the calendar views. If displayed, the current date can be clicked to reset the calendar to the current date.",
"showImgInMV_label" => "Miniaturbilder in der Monatsansicht zeigen",
"showImgInMV_text" => "Aktivieren/deaktivieren der Anzeige von Miniaturbild in der Monats-Ansicht, die zu einem der beschreibungsfelder hinzugefügt wurden. Wenn aktiviert, When aktiviert werden die Miniaturbild in den Tages-Zellen angezeigt - wenn deaktiviert werden die Miniaturbild stattdessen in den Hover-Boxen beim Überfahren mit der Maus angezeigt.",
"urls" => "URL links",
"emails" => "E-Mail links",
"monthInDCell_label" => "Monat in jeder Tageszelle",
"monthInDCell_text" => "Für jede Tages-Zelle in der Monats-Ansicht den Monat mit 3 Buchstaben anzeigen.",
"scrollDCell_label" => "Use scrollbar in day cells",
"scrollDCell_text" => "If in month view a day cell is too small, rather than increasing the day cell height, a vertical scrollbar will appear.",

//settings.php - date/time settings.
"dateFormat_label" => "Datums Format (dd mm yyyy)",
"dateFormat_text" => "Eine Zeichenfolge zum Formatieren der Termindaten in Kalenderansichten.<br>Mögliche Zeichen: y = Jahr, m = Monat and d = Tag.<br>Nicht alphanumerische Zeichen können als Trennzeichen genutzt werden und werden buchstäblich übernommen.<br>Beispiele:<br>y-m-d: 2024-10-31<br>m.d.y: 10.31.2024<br>d/m/y: 31/10/2024",
"dateFormat_expl" => "Beispiel: y.m.d: 2024.10.31",
"MdFormat_label" => "Datums Format (dd Monat)",
"MdFormat_text" => "Zeichenfolge zum Formatieren von Daten, die aus Monat und Tag bestehen.<br>Mögliche Zeichen: M = Monat als Text, d = Tag in Ziffern.<br>Nicht alphanumerische Zeichen können als Trennzeichen genutzt werden und werden buchstäblich übernommen.<br>Beispiele:<br>d M: 12 April<br>M, d: July, 14",
"MdFormat_expl" => "Beispiel: M, d: Juli, 14",
"MdyFormat_label" => "Datums Format (dd Monat yyyy)",
"MdyFormat_text" => "Zeichenfolge zum Formatieren von Daten, die aus Tag, Monat und Jahr bestehen.<br>Mögliche Zeichen: d = Tag in Ziffern, M = Monat als Text, y = Jahr in Ziffern.<br>Nicht alphanumerische Zeichen können als Trennzeichen genutzt werden und werden buchstäblich übernommen.<br>Beispiele:<br>d M y: 12 April 2024<br>M d, y: Juli 8, 2024",
"MdyFormat_expl" => "Beispiel: M d, y: Juli 8, 2024",
"MyFormat_label" => "Datums Format (Monat yyyy)",
"MyFormat_text" => "Zeichenfolge zum Formatieren von Daten, die aus Monat und Jahr bestehen.<br>Mögliche Zeichen: M = Monat als Text, y = Jahr in Ziffern.<br>Nicht alphanumerische Zeichen können als Trennzeichen genutzt werden und werden buchstäblich übernommen.<br>Beispiele:<br>M y: April 2024<br>y - M: 2024 - Juli",
"MyFormat_expl" => "Beispiel: M y: April 2024",
"DMdFormat_label" => "Datum Format (Wochentag tt Monat)",
"DMdFormat_text" => "Zeichenfolge zum Formatieren von Daten, die aus Wochentag, Tag und Monat bestehen.<br>Mögliche Zeichen: WD = Wochentag als Text, M = Monat als Text, d = Tag in Ziffern.<br>Nicht alphanumerische Zeichen können als Trennzeichen genutzt werden und werden buchstäblich übernommen.<br>Beispiele:<br>WD d M: Freitag 12 April<br>WD, M d: Montag, Juli 14",
"DMdFormat_expl" => "Beispiel: WD - M d: Sonntag - April 6",
"DMdyFormat_label" => "Datum Format (Wochentag d Monat yyyy)",
"DMdyFormat_text" => "Zeichenfolge zum Formatieren von Daten, die aus Wochentag, Tag, Monat und Jahr bestehen.<br>Mögliche Zeichen: WD = Wochentag als Text, M = Monat als Text, d = Tag in Ziffern, y = Jahr in Ziffern.<br>Nicht alphanumerische Zeichen können als Trennzeichen genutzt werden und werden buchstäblich übernommen.<br>Beispiele:<br>WD d M y: Freitag 13 April 2024<br>WD - M d, y: Montag - Juli 16, 2024",
"DMdyFormat_expl" => "Beispiel: WD, M d, y: Montag, Juli 16, 2024",
"timeFormat_label" => "Zeit Format (hh mm)",
"timeFormat_text" => "Zeichenfolge zum Formatieren von Uhrzeiten in Kalenderansichten und Eingabefeldern.<br>Mögliche Zeichen: h = Stunden, H = Stunden mit führender Null, m = Minuten, a = am/pm (optional), A = AM/PM (optional).<br>Nicht alphanumerische Zeichen können als Trennzeichen genutzt werden und werden buchstäblich übernommen.<br>Beispiele:<br>h:m: 18:35<br>h.m a: 6.35 pm<br>H:mA: 06:35PM",
"timeFormat_expl" => "Beispiel: hh:mm: 22:35 (EU; 24-Std.) und hh:mmA: 10:35PM (US; 12-Std.)",
"weekNumber_label" => "Wochennummern",
"weekNumber_text" => "Anzeige der Wochennummern in Jahr, Monat und Tag-Ansicht.",
"time_format_us" => "12-Stunden AM/PM",
"time_format_eu" => "24-Stunden",
"sunday" => "Sonntag",
"monday" => "Montag",
"time_zones" => "ZEIT-ZONEN",
"dd_mm_yyyy" => "tt-mm-jjjj",
"mm_dd_yyyy" => "mm-tt-jjjj",
"yyyy_mm_dd" => "jjjj-mm-tt",

//settings.php - file uploads settings.
"maxUplSize_label" => "Maximale Größe für das Hochladen von Dateien",
"maxUplSize_text" => "Maximal erlaubte Dateigröße wenn Benutzer Anhänge oder Miniaturbilder hochladen.<br>Hinweis: Die meisten PHP-Installationen haben dieses Maximum bei 2MB eingestellt(php_ini Datei) ",
"attTypes_label" => "Anhangs-Dateitypen",
"attTypes_text" => "Komma-separierte Liste mit erlaubten Datei-Typen für den Datei-Upload von Anhängen(z.B. '.pdf,.jpg,.gif,.png,.mp4,.avi')",
"tnlTypes_label" => "Miniaturbild-Dateitypen",
"tnlTypes_text" => "Komma-separierte Liste mit erlaubten Datei-Typen für den Datei-Upload von Thumbnials (e.g. '.jpg,.jpeg,.gif,.png')",
"tnlMaxSize_label" => "Miniaturbild - maximale Größe",
"tnlMaxSize_text" => "Maximale Miniaturbild Größe. Wenn Benutzer größere Miniaturbilder hochladen werden diese automatisch auf die maximale Größe verkleinert.<br>Hinweis: Hohe Miniaturbilder dehnen die Zelle eines Tages in der Monatsansicht, was eventuell zu unerwünschten Effekten führt.",
"tnlDelDays_label" => "Miniaturbild Löschspanne",
"tnlDelDays_text" => "Wenn ein Miniaturbild seit dieser Anzahl von Tagen benutzt wurde, kann es nicht gelöscht werden.<br>Der Wert 0 bedeutet, dass das Minitaurbild nicht gelöscht werden kann.",
"days" =>"Tage",
"mbytes" => "MB",
"wxhinpx" => "B x H in Pixel",

//settings.php - reminders settings.
"services_label" => "Erinnerungen",
"services_text" => "Mögliche Dienste zum Senden von Erinnerungen. Wenn ein dienst nicht ausgewählt ist, wird der entsprechende Bereich im Terminfenster ausgeblendet. Wenn kein Dienst ausgewählt ist, werden keine Erinnerungen gesendet.",
"msgLogging_label" => "Notification message logging",
"msgLogging_text" => "When checked, the notification messages sent are logged in the messages.log file. The 'weeks' field specifies how long the logged messages should be kept",
"smsCarrier_label" => "SMS-Dienst Vorlage",
"smsCarrier_text" => "Die SMS-Dienst Vorlage wird zum Erstellen der SMS-Dienst E-Mail Adresse genutzt: ppp#sss@carrier, where . . .<br>• ppp: optionale Zeichenfolge, die vor der Telefonnummer eingefügt wird<br>• #: Platzhalter für die Empfänger Mobil-Nummer (der kalender wird das Zeichen # durch die Telefonnummer ersetzen)<br>• sss: optionale Zeichenfolge, die nach der Telefonnummer eingefügt wird, z.B. ein Benutzername oder Passwort, wie es für einige Vermittlerdienste erforderlich ist<br>• @: Trennzeichen<br>• carrier: Dienst-Anbieter Adresse (z.B. mail2sms.com)<br>Vorlagen Beispiele: #@xmobile.com, 0#@carr2.int, #myunmypw@sms.gway.net.",
"smsCountry_label" => "SMS-Ländercode",
"smsCountry_text" => "Wenn der SMS-Dienst in einem anderen Land als der Kalender angesiedelt ist, muss der Länder-Code angegeben werden, in dem dem der Kalender genutzt wird.<br>Auswählen, ob  '+' oder '00' voran gestellt werden muss.",
"smsSubject_label" => "SMS-Betreff Vorlage",
"smsSubject_text" => "Wenn angegeben wird der Text in dieser Vorlage in das Betreff-Feld der SMS Email Nachrichten kopiert, die dem SMS-Dienst geschickt werden. Der Text kann das Zeichen # enthalten, welches durch die Telefonnummer des Kalenders oder des termin-Erstellers ersetzt wird (abhängig von er Einstellung darüber).<br>Beispiel: 'FROMPHONENUMBER=#'.",
"smsAddLink_label" => "Link zur Terminansicht zur SMS hinzufügen",
"smsAddLink_text" => "Wenn aktiviert wird der SMS ein Link zur Terminansicht hinzugefügt. Durch das Öffnen dieses Links auf dem Smartphone können sich Teilnehmer die Termindetails ansehen.",
"maxLenSms_label" => "Maximum SMS Nachrichtenlänge",
"maxLenSms_text" => "SMS Nachrichten werden mit UTF-8 Zeichenkodierung versendet. Nachrichten bis zu 70 Zeichen ergeben eine SMS; Nachricht mit mehr als 70 Zeichen mit vielen Unicode zeichen könnten in mehrere Nachrichten aufgeteilt werden.",
"calPhone_label" => "Telefonnummer des Kalenders",
"calPhone_text" => "Die Telefonnummer, die als Sender ID beim Senden von SMS Nachrichten genutzt wird.<br>Format: frei, max. 20 Ziffern (einige Länder benötigen eine Telefonnummer - andere Länder akzeptieren auch alphabetische Zeichen).<br>Wenn kein SMS Dienst aktiviert ist oder wenn keine SMS-Betreff-Vorlage festgelegt wurde, kann dieses Feld leer bleiben.",
"notSenderEml_label" => "Das Feld 'Antwort an' der E-Mail hinzufügen",
"notSenderEml_text" => "Wenn ausgewählt enthalten Erinnerungs-E-Mails ein 'Antwort an' Feld mit der Email-Adresse des terminerstellers, sodass der Empfänger direkt antworten kann.",
"notSenderSms_label" => "Absender von Benachrichtigungs-SMS",
"notSenderSms_text" => "Wennd er Kalender Erinnerungs-SMSs verschickt, kann die Sender-ID entweder die Telefonnummer des Kalenders sein oder die Telefonnummer des Terminerstellers.<br>Wenn hier 'Benutzer' ausgewählt wird,d er Benutzer aber keine Telefonnummer hat, wird stattdessen die Telefonnummer des Kalenders gnutzt.<br>Wenn eine Benutzer Telefonnummer vorhanden ist, kann der Empfänger auf die Nachricht antworten.",
"defRecips_label" => "Standardliste der Empfänger",
"defRecips_text" => "Wenn angegeben wird das die Standard Empfängerliste für E-Mail und SMS Erinnerungen im Terminfenster.If specified, this will be the default recipients list for E-Mail and/or SMS notifications in the Event window. Wenn das Feld leer bleibt, wird der Standardempfänger der Terminersteller sein.",
"maxEmlCc_label" => "Max. Anzahl der Empfänger per E-Mail",
"maxEmlCc_text" => "Normalerweise erlauben Internetprovider nur eine bestimmte maximale Anzahl an Empfängern pro E-Mail. Normally ISPs allow a maximum number of recipients per E-Mail. Wenn beim Senden von E-Mails oder SMS-Nachrichten die Anzahl der Empfänger größer ist als hier angegeben, wird die Nachricht auf mehrere E-Mails aufgeteilt - jede mit der angegebenen maximalen Anzahl von Empfängern.",
"emlFootnote_label" => "Reminder email footnote",
"emlFootnote_text" => "Free-format text that will be added as a paragraph to the end of reminder email messages. HTML tags are allowed in the text.",
"mailServer_label" => "Mail server",
"mailServer_text" => "PHP mail is ausreichend für kleine Mengen von E-Mails, bei denen keine Anmeldung notwendig ist. Für größere Mengen oder wenn eine Anmeldung beim Server erforderlich ist, sollte SMTP genutzt werden, was einen SMTP Server notwendig macht. Die Konfigurationseinstellungen, die für den SMTP Server gebraucht werden, müssen im Folgenden eingegeben werden.",
"smtpServer_label" => "SMTP-Servername",
"smtpServer_text" => "Wenn SMTP ausgewählt ist, sollte hier der SMTP Servername eingegeben werden. Beispiel: smtp.gmail.com.",
"smtpPort_label" => "SMTP-Portnummer",
"smtpPort_text" => "Wenn SMTP ausgewählt ist, sollte hier die Portnummer eingegeben werden. Als Beispiel 25, 465 or 587. Gmail zum Beispiel nutz die port nummer 465.",
"smtpSsl_label" => "SSL (Secure Sockets Layer)",
"smtpSsl_text" => "Wenn SMTP ausgewählt ist, hier auswählen, ob SSl genutzt wird. Für gmail: auswählen",
"smtpAuth_label" => "SMTP-Authentifizierung",
"smtpAuth_text" => "Wenn SMTP Authorisierung ausgewählt ist, wird der im folgenden eingegebene Benutzername und das Passwort zur Anmeldung am SMTP Server genutzt.<br>Für gmail zum Beispiel, ist der Benutzername der Teil der Emailadresse vor dem @-Zeichen.",
"tlgToken_label" => "Telegram token",
"tlgToken_text" => "Telegram token in the following format: &lt;bot ID&gt;:&lt;bot hash&gt;. For details see installation_guide.html, section Event Notification Messages.",
"cc_prefix" => "Ländercode beginnt mit dem Präfix + oder 00",
"weeks" => "Weeks",
"general" => "Allgemein",
"php_mail" => "PHP mail",
"smtp_mail" => "SMTP mail (Bitte folgende Felder ausfüllen)",

//settings.php - periodic function settings.
"cronHost_label" => "Cron job host",
"cronHost_text" => "Hier angeben, wo der cron job gehostet ist, der in Abständen das Skript 'lcalcron.php' startet.<br>• local: der cron job läuft auf dem selben Server als der kalender<br>• remote: der cron job läuft auf einem entfernten Server oder lcalcron.php wird manuell gestartet<br>• IP address: der cron job läuft auf einem entfernten Server mit der angegebenen  IP Adresse.",
"cronSummary_label" => "Admin cron job Zusammenfassung",
"cronSummary_text" => "Sende eine cron job Zusammenfassung zum Kalender Administrator.<br>Aktivieren ist nur sinnvoll wenn ein cron job aktiviert wurde für der Kalender",
"icsExport_label" => "Täglicher Export von iCal-Terminen",
"icsExport_text" => "Wenn ausgewählt: Alle Termine im Bereich von -1 Woche bis +1 Jahr werden im iCalendar Format .ics Datei im 'files' Verzeichnis exportiert.<br>Der Dateiname wird der Kalendername sein, wobei Leerzeichen durch Unterstriche ersetzt werden.Ältere Datein werden durch neuere überschrieben.",
"eventExp_label" => "Anzahl der Tage, bevor Termine gelöscht werden",
"eventExp_text" => "Anzahl von Tagen nach dem Erreichen des Fälligkeitsdatums, bis der Termin abläuft und automatisch gelöscht wird.<br>Wenn 0 oder wenn kein cron job ausgewählt ist, werden keine Termine gelöscht.",
"maxNoLogin_label" => "Max. Anzahl an Tagen ohne Login",
"maxNoLogin_text" => "Wenn sich ein Benutzer länger als diese Zeit nicht einloggt, wird der Benutzer automatisch wieder gelöscht.<br>Wenn der Wert au 0 gesetzt wird, werden keine Benutzer automatisch gelöscht.",
"local" => "Lokal",
"remote" => "Fernbedienung",
"ip_address" => "IP-Adresse",

//settings.php - mini calendar / sidebar settings.
"popFieldsSbar_label" => "Termin Felder - Seitenleiste Hover Box",
"popFieldsSbar_text" => "Die Terminfelder, die als Überlagerung angezeigt werden, wenn ein Benutzer mit der Maus über einen Termin in der Seitenleiste fährt können mit Hilfe einer Abfolge von Nummern angegeben werden.<br>Wenn keine Felder eingetragen werden, wird keine Hoverbox angezeigt.",
"showLinkInSB_label" => "Links in der Seitenleiste anzeigen",
"showLinkInSB_text" => "Zeige URLs innerhalb der Termin Beschreibung als Hyperlinks in der Seitenleiste",
"sideBarDays_label" => "Anzahl der Tage die in der Seitenleiste gezeigt werden",
"sideBarDays_text" => "Anzahl der Tage die in der Seitenleiste gezeigt werden.",

//login.php
"log_log_in" => "Einloggen",
"log_remember_me" => "Automatisch Einloggen",
"log_register" => "Registrieren",
"log_change_my_data" => "Meine Daten ändern",
"log_save" => "Ändern",
"log_done" => "Fertig",
"log_un_or_em" => "Benutzername oder E-Mail",
"log_un" => "Benutzername",
"log_em" => "E-Mail",
"log_ph" => "Mobile Telefonnummer",
"log_tg" => "Telegram chat ID",
"log_answer" => "Ihre Antwort",
"log_pw" => "Passwort",
"log_expir_date" => "Account expiration date",
"log_account_expired" => "This account has expired",
"log_new_un" => "Neuer Benutzername",
"log_new_em" => "Neue E-Mail",
"log_new_pw" => "Neues Passwort",
"log_con_pw" => "Passwortbestätigung",
"log_pw_msg" => "Hier sind Ihr Einlogdetails für den Kalender",
"log_pw_subject" => "Ihr Passwort",
"log_npw_subject" => "Ihr neues Passwort",
"log_npw_sent" => "Ihr neues Passwort wurde gesendet",
"log_registered" => "Registrierung erfolgreich - Ihr Passwort wurde per E-Mail gesendet",
"log_em_problem_not_sent" => "E-Mail Problem - Ihr Passwort kann nicht gesendet werden",
"log_em_problem_not_noti" => "E-Mail Problem - der Administrator konnte nicht informiert werden",
"log_un_exists" => "Benutzername existiert schon",
"log_em_exists" => "E-Mail Adresse existiert schon",
"log_un_invalid" => "Ungültiger Benutzername (min. Länge 2: A-Z, a-z, 0-9, und _-.)",
"log_em_invalid" => "Ungültige E-Mail Adresse",
"log_ph_invalid" => "Ungültige Mobilnummer",
"log_tg_invalid" => "Invalid Telegram chat ID",
"log_sm_nr_required" => "SMS: mobile phone number required",
"log_tg_id_required" => "Telegram: chat ID required",
"log_sra_wrong" => "Falsche Antwort auf die Frage",
"log_sra_wrong_4x" => "4 mal falsch geantwortet - nächster Versuch in 30 Minuten möglich",
"log_un_em_invalid" => "Dieser Benutzername/E-Mail ist ungültig",
"log_un_em_pw_invalid" => "Ihr Benutzername/E-Mail oder Passwort ist falsch",
"log_pw_error" => "Passwort stimmt nicht überein",
"log_no_un_em" => "Bitte Benutzernamen oder E-Mail eingeben",
"log_no_un" => "Bitte Benutzername eingeben",
"log_no_em" => "Bitte E-Mail eingeben",
"log_no_pw" => "Bitte Passwort eingeben",
"log_no_rights" => "Einloggen nicht möglich: keine Berechtigung – Administrator kontaktieren",
"log_send_new_pw" => "Sende neues Passwort",
"log_new_un_exists" => "Neuer Benutzername existiert schon",
"log_new_em_exists" => "Neue E-Mail Adresse existiert schon",
"log_ui_language" => "Sprache der Benutzeroberfläche",
"log_new_reg" => "Neue Benutzer ",
"log_date_time" => "Datum/Zeit",
"log_time_out" => "Time out",

//categories.php
"cat_list" => "Kategorieliste",
"cat_edit" => "Bearbeiten",
"cat_delete" => "Löschen",
"cat_add_new" => "Neue Kategorie anlegen",
"cat_add" => "Hinzufügen",
"cat_edit_cat" => "Kategorie bearbeiten",
"cat_sort" => "Sortiere nach Name",
"cat_cat_name" => "Kategoriebezeichnung",
"cat_symbol" => "Symbol",
"cat_symbol_repms" => "Symbol der Kategorie (Ersetzt minisquare)",
"cat_symbol_eg" => "Beispiel: A, X, ♥, ⛛",
"cat_matrix_url_link" => "URL link (shown in matrix view)",
"cat_seq_in_menu" => "Reihenfolge im Menü",
"cat_cat_color" => "Kategoriefarbe",
"cat_text" => "Text",
"cat_background" => "Hintergrund",
"cat_select_color" => "Wähle Farbe",
"cat_subcats" => "Unter-<br>Kategorien",
"cat_subcats_opt" => "Anzahl der Unter-KategorienNumber (optional)",
"cat_copy_from" => "Kopiere von",
"cat_eml_changes_to" => "Send event changes to",
"cat_url" => "URL",
"cat_name" => "Name",
"cat_subcat_note" => "Beachten, dass die aktuell existierenden Unter-Kategorien bereits für Termine genutzt werden.",
"cat_save" => "Aktualisieren",
"cat_added" => "Kategorie hinzugefügt",
"cat_updated" => "Kategorie aktualisiert",
"cat_deleted" => "Kategorie gelöscht",
"cat_not_added" => "Kategorie nicht hinzugefügt",
"cat_not_updated" => "Kategorie nicht aktualisiert",
"cat_not_deleted" => "Kategorie nicht gelöscht",
"cat_nr" => "#",
"cat_repeat" => "Wiederholung",
"cat_every_day" => "Täglich",
"cat_every_week" => "Wöchentlich",
"cat_every_month" => "Monatlich",
"cat_every_year" => "Jährlich",
"cat_overlap" => "Überschneidung<br>erlaubt<br>(Lücke)",
"cat_need_approval" => "Ereignis benötigt<br>Bestätigung",
"cat_no_overlap" => "Keine Überschneidung erlaubt",
"cat_same_category" => "gleiche Kategorie",
"cat_all_categories" => "alle Kategorien",
"cat_gap" => "gap",
"cat_ol_error_text" => "Fehlermeldung bei Überschneidung",
"cat_no_ol_note" => "Hinweis: Bereits existierende Ereignisse werden nicht geprüft können andere überschneiden",
"cat_ol_error_msg" => "Terminüberschneidung - wählen Sie eine andere Zeit",
"cat_no_ol_error_msg" => "Die Fehlermeldung für Terminüberscheidungen fehlt",
"cat_duration" => "Termindauer<br>! = fest",
"cat_default" => "standard (keine Endzeit)",
"cat_fixed" => "fest",
"cat_event_duration" => "Termindauer",
"cat_olgap_invalid" => "Ungültige Überschneidungs-Lücke",
"cat_duration_invalid" => "Ungültiger Termindauer",
"cat_no_url_name" => "URL link name missing",
"cat_invalid_url" => "Ungültiger URL",
"cat_day_color" => "Tag Farbe",
"cat_day_color1" => "Tag Farbe (Jahr/Matrix Ansicht)",
"cat_day_color2" => "Tag Farbe (Monat/Woche/Tag Ansicht)",
"cat_approve" => "Ereignisse benötigen Bestätigung",
"cat_check_mark" => "Häkchen",
"cat_not_list" => "Notify<br>list",
"cat_label" => "Bezeichnung",
"cat_mark" => "markieren",
"cat_name_missing" => "Kategoriename fehlt",
"cat_mark_label_missing" => "Prüfe Markierung/Bezeichnung fehlt",

//users.php
"usr_list_of_users" => "Benutzerliste",
"usr_name" => "Benutzername",
"usr_email" => "E-Mail",
"usr_phone" => "Mobilnummer",
"usr_phone_br" => "Mobile<BR>Telefonnummer",
"usr_tg_id" => "Telegram chat ID",
"usr_tg_id_br" => "Telegram<br>chat ID",
"usr_not_via" => "Notify via",
"usr_not_via_br" => "Notify<br>via",
"usr_language" => "Sprache",
"usr_ui_language" => "Benutzer Oberflächen Sprache",
"usr_group" => "Benutzer-<BR>Gruppe",
"usr_password" => "Passwort",
"usr_expir_date" => "Account expiration date",
"usr_select_exp_date" => "Select expiration date",
"usr_blank_none" => "blank: no expiration",
"usr_expires" => "Expires",
"usr_edit_user" => "Benutzer Profil bearbeiten",
"usr_add" => "Benutzer hinzufügen",
"usr_edit" => "Bearbeiten",
"usr_delete" => "Löschen",
"usr_login_0" => "Erstes<BR>Einloggen",
"usr_login_1" => "Letztes<br>Einloggen",
"usr_login_cnt" => "Anzahl",
"usr_add_profile" => "Profil anlegen",
"usr_upd_profile" => "Profil aktualisieren",
"usr_if_changing_pw" => "Nur für Passwortänderung",
"usr_pw_not_updated" => "Passwort nicht erneuert",
"usr_added" => "Benutzer angelegt",
"usr_updated" => "Benutzerprofil aktualisiert",
"usr_deleted" => "Benutzer gelöscht",
"usr_not_deleted" => "Benutzer nicht gelöscht",
"usr_cred_required" => "Benutzername, E-Mail und Passwort werden benötigt",
"usr_name_exists" => "Benutzername existiert schon",
"usr_email_exists" => "E-Mail Adresse existiert schon",
"usr_un_invalid" => "Ungültiger Benutzername (min. Länge 2: A-Z, a-z, 0-9, und _-.)",
"usr_em_invalid" => "E-Mail Adresse ist ungültig",
"usr_ph_invalid" => "Ungültige Mobilnummer",
"usr_tg_invalid" => "Invalid Telegram chat ID",
"usr_xd_invalid" => "Invalid account expiration date",
"usr_cant_delete_yourself" => "Sie können sich nicht selbst löschen",
"usr_go_to_groups" => "Gehe zu den Gruppen",
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
"grp_list_of_groups" => "Benutzergruppenliste",
"grp_name" => "Gruppenname",
"grp_priv" => "Benutzerrechte",
"grp_categories" => "Kategorien",
"grp_all_cats" => "alle Kategorien",
"grp_rep_events" => "Wiederkehrende<br>Termine",
"grp_m-d_events" => "Mehrtägige<br>Termine",
"grp_priv_events" => "Private<br>Termine",
"grp_upload_files" => "Dateien<br>hochladen",
"grp_tnail_privs" => "Miniaturbild<br>Rechte",
"grp_priv0" => "Keine Rechte",
"grp_priv1" => "Kalender anzeigen",
"grp_priv2" => "Erstelle/bearbeite eigene Termine",
"grp_priv3" => "Erstelle/bearbeite alle Termine",
"grp_priv4" => "Erstelle/bearbeite + manager rights",
"grp_priv9" => "Administrator",
"grp_may_post_revents" => "Darf wiederholende Termine eintragen",
"grp_may_post_mevents" => "Darf mehrtägige Termine eintragen",
"grp_may_post_pevents" => "Darf private Termine eintragen",
"grp_may_upload_files" => "Darf Dateien hochladen",
"grp_tn_privs" => "Miniaturbilder Rechte",
"grp_tn_privs00" => "keine",
"grp_tn_privs11" => "Alle ansehen",
"grp_tn_privs20" => "Eigene verwalten",
"grp_tn_privs21" => " eigene verwalten/alle ansehen",
"grp_tn_privs22" => "Alle verwalten",
"grp_edit_group" => "Benutzergruppe bearbeiten",
"grp_sub_to_rights" => "Vorbehaltlich der Benutzerrechte",
"grp_view" => "Ansicht",
"grp_add" => "Hinzufügen",
"grp_edit" => "Bearbeiten",
"grp_delete" => "Löschen",
"grp_add_group" => "Gruppe hinzufügen",
"grp_upd_group" => "Aktualisiere Gruppe",
"grp_added" => "Gruppe hinzugefügt",
"grp_updated" => "Gruppe aktualisiert",
"grp_deleted" => "Gruppe gelöscht",
"grp_not_deleted" => "Gruppe nicht gelöscht",
"grp_in_use" => "Gruppe ist in gebrauch",
"grp_cred_required" => "Gruppenname, Rechte und Kategorien werden benötigt",
"grp_name_exists" => "Gruppenname wird schon benutzt",
"grp_name_invalid" => "Ungültiger Gruppenname (min. Länge 2: A-Z, a-z, 0-9, und _-.)",
"grp_check_add" => "At least one check box in the Add column must be checked",
"grp_background" => "Hintergrundfarbe",
"grp_select_color" => "Farbe wählen",
"grp_invalid_color" => "Ungültiges Farbformat (#XXXXXX wo X = HEX-wert)",
"grp_go_to_users" => "Gehe zu den Benutzern",

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
"mdb_dbm_functions" => "Aufgaben",
"mdb_noshow_tables" => "Tabellen können nicht gelesen werden",
"mdb_noshow_restore" => "Keine Quellsicherungsdatei ausgewaehlt oder Datei ist zu groß zum Hochladen",
"mdb_file_not_sql" => "Quell Backup-Datei sollte eine SQL-Datei sein (Erweiterung '.sql')",
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
"mdb_compact" => "Komprimieren",
"mdb_compact_table" => "Tabelle Komprimieren",
"mdb_compact_error" => "Fehler",
"mdb_compact_done" => "abgeschlossen",
"mdb_purge_done" => "Vor mehr als 30 Tagen gelöschte Termine endgültig gelöscht",
"mdb_backup" => "Backup",
"mdb_backup_table" => "Backup der Tabelle",
"mdb_backup_file" => "Backup Datei",
"mdb_backup_done" => "abgeschlossen",
"mdb_records" => "Datensätze",
"mdb_restore" => "Wiederherstellung der Datenbank",
"mdb_restore_table" => "Wiederherstellung der Tabellen",
"mdb_inserted" => "Datensätze eingefügt",
"mdb_db_restored" => "Datenbank wiederhergestellt",
"mdb_db_upgraded" => "Datenbank upgraded",
"mdb_no_bup_match" => "Die Sicherungsdatei stimmt nicht mit der Kalenderversion überein.<br>Datenbank nicht wiederhergestellt.",
"mdb_events" => "Termine",
"mdb_delete" => "löschen",
"mdb_undelete" => "wiederherstellen",
"mdb_between_dates" => "zwischen",
"mdb_deleted" => "Termine gelöscht",
"mdb_undeleted" => "Termine nicht gelöscht",
"mdb_file_saved" => "Backup Datei gespeichert.",
"mdb_file_name" => "Datei Name",
"mdb_start" => "Start",
"mdb_no_function_checked" => "Keine Operation(en) ausgewählt",
"mdb_write_error" => "Das Schreiben der Sicherungsdatei ist fehlgeschlagen<br>überprüfen Sie die Berechtigungen des Verzeichnisses 'files/'",

//import/export.php
"iex_file" => "Ausgewählte Datei",
"iex_file_name" => "Ziel-Dateiname",
"iex_file_description" => "iCal Datei Beschreibung",
"iex_filters" => "Terminfilter",
"iex_export_usr" => "Benutzer exportieren, CSV-Datei herunterladen",
"iex_import_usr" => "Benutzer importieren, CSV-Datei hochladen",
"iex_upload_ics" => "Termine importieren, iCal Datei hochladen",
"iex_create_ics" => "Termine exportieren, iCal Datei herunterladen",
"iex_tz_adjust" => "Zeitzonen Anpassungen",
"iex_upload_csv" => "Termine importieren, CSV-Datei hochladen",
"iex_upload_file" => "Datei hochladen",
"iex_create_file" => "Datei generieren",
"iex_download_file" => "Datei herunterladen",
"iex_fields_sep_by" => "Felder getrennt durch",
"iex_birthday_cat_id" => "Geburtstags Kategorie ID",
"iex_default_grp_id" => "Standardbenutzergruppe ID",
"iex_default_cat_id" => "Kategorie ID",
"iex_default_pword" => "Standard Passwort",
"iex_if_no_pw" => "Wenn kein Passwort angegeben ist",
"iex_replace_users" => "Ersetze vorhandene Benutzer",
"iex_if_no_grp" => "wenn keine Benutzergruppe gefunden wurde",
"iex_if_no_cat" => "wenn keine Kategorie gefunden wurde",
"iex_import_events_from_date" => "Termine importieren ab:",
"iex_no_events_from_date" => "Keine Ereignisse zum genannten Datum gefunden",
"iex_see_insert" => "Siehe Beschreibung rechts",
"iex_no_file_name" => "Dateiname fehlt",
"iex_no_begin_tag" => "Ungültige iCal Datei (BEGIN-tag fehlt)",
"iex_bad_date" => "Falsches Datum",
"iex_date_format" => "Datum Format",
"iex_time_format" => "Zeit Format",
"iex_number_of_errors" => "Anzahl der Fehler in der Liste",
"iex_bgnd_highlighted" => "Hintergrund hervorgehoben",
"iex_verify_event_list" => "Überprüfe Termin Liste, korrigiere Fehler und wähle",
"iex_add_events" => "Termine zur Datenbank hinzufügen",
"iex_verify_user_list" => "Überprüfen Sie die Benutzerliste, korrigieren Sie mögliche Fehler und klicken Sie auf",
"iex_add_users" => "Benutzer zur Datenbank hinzufügen",
"iex_select_ignore_birthday" => "Wähle Geburtstag aus und lösche Checkbox wie gewünscht",
"iex_select_ignore" => "Wähle Löschen Checkbox um den Termin zu ignorieren",
"iex_check_all_ignore" => "Aktivieren Sie alle Kontrollk�stchen zum Ignorieren",
"iex_title" => "Titel",
"iex_venue" => "Ort",
"iex_owner" => "Ersteller",
"iex_category" => "Kategorie",
"iex_date" => "Datum",
"iex_end_date" => "Ende",
"iex_start_time" => "Anfang",
"iex_end_time" => "Endzeit",
"iex_description" => "Beschreibung",
"iex_repeat" => "Wiederholen",
"iex_birthday" => "Geburtstag",
"iex_ignore" => "Löschen",
"iex_events_added" => "Termine hinzugefügt",
"iex_events_dropped" => "Termine übersprungen (bereits vorhanden)",
"iex_users_added" => "Benutzer hinzugefügt",
"iex_users_deleted" => "Benutzer gelöscht",
"iex_csv_file_error_on_line" => "CSV Datei Fehler in Zeile",
"iex_between_dates" => "von - bis",
"iex_changed_between" => "Erstellt/Geändert von - bis",
"iex_select_date" => "Datum auswählen",
"iex_select_start_date" => "Startdatum auswählen",
"iex_select_end_date" => "Enddatum auswählen",
"iex_group" => "Benutzergruppe",
"iex_name" => "Benutzername",
"iex_email" => "E-Mail Adresse",
"iex_phone" => "Telefonnummer",
"iex_msgID" => "Chat ID",
"iex_lang" => "Sprache",
"iex_pword" => "Passwort",
"iex_all_groups" => "all Benutzergruppen",
"iex_all_cats" => "alle Kategorien",
"iex_all_users" => "alle Benutzer",
"iex_no_events_found" => "Keine Termine gefunden",
"iex_file_created" => "Datei generiert",
"iex_write error" => "Schreiben der Export Datei fehlgeschlagen<br>Zugriffsrechte des 'files/' Verzeichnisses überprüfen",
"iex_invalid" => "ungültig",
"iex_in_use" => "bereits verwendet",

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
"sty_css_intro" =>  "Die auf dieser Seite angegebenen Werte sollten den CSS-Standards entsprechen",
"sty_preview_theme" => "Vorschau Thema",
"sty_preview_theme_title" => "Vorschau des eingestellten Themas im Kalender",
"sty_stop_preview" => "Stop Vorschau",
"sty_stop_preview_title" => "Stop der Vorschau des eingestellten Themas im Kalender",
"sty_save_theme" => "Thema speichern",
"sty_save_theme_title" => "Das angezeigte Thema in die Datenbank speichern",
"sty_backup_theme" => "Backup Thema",
"sty_backup_theme_title" => "Backup des Themas in eine Datei",
"sty_restore_theme" => "Thema wiederherstellen",
"sty_restore_theme_title" => "Thema von Datei wieder herstellen",
"sty_default_luxcal" => "Standard LuxCal Thema",
"sty_close_window" => "Fenster schließen",
"sty_close_window_title" => "Fenster schließen",
"sty_theme_title" => "Thema Titel",
"sty_general" => "Allgemein",
"sty_grid_views" => "Raster / Ansichten",
"sty_hover_boxes" => "Schwebekästen",
"sty_bgtx_colors" => "Hintergrund / Textfarben",
"sty_bord_colors" => "Randfarben",
"sty_fontfam_sizes" => "Schriftarten / Größen",
"sty_font_sizes" => "Schriftgröße",
"sty_miscel" => "Verschiedenes",
"sty_background" => "Hintergrund",
"sty_text" => "Text",
"sty_color" => "Farbe",
"sty_example" => "Beispiel",
"sty_theme_previewed" => "Vorschau Modus - man kann jetzt durch den Kalender navigieren. Wähle Stop Vorschauzum beenden.",
"sty_theme_saved" => "Thema ind er Datenbank gespeichert",
"sty_theme_backedup" => "Thema in einer Datei gesichert:",
"sty_theme_restored1" => "Thema aus einer Datei wieder hergestellt:",
"sty_theme_restored2" => "Klicke Thema speichern zum speichern des Thema in der Datenbank",
"sty_unsaved_changes" => "WARNUNG – Ungesicherte Änderungen!\\nWenn Sie das Fenster schließen, sind alle Änderungen verloren.", //don't remove '\\n'
"sty_number_of_errors" => "Anzahl der Fehler in der Liste",
"sty_bgnd_highlighted" => "Hintergrund markiert",
"sty_XXXX" => "Kalender allgemein",
"sty_TBAR" => "Kalender Titelbalken",
"sty_BHAR" => "Balken, überschriften und Zeilen",
"sty_BUTS" => "Knöpfe",
"sty_DROP" => "Dropdown Menus",
"sty_XWIN" => "Popup Fenster",
"sty_INBX" => "Einfüge Boxen",
"sty_OVBX" => "Overlay Boxen",
"sty_BUTH" => "Schaltflächen - bei hover",
"sty_FFLD" => "Formularfelder",
"sty_CONF" => "Bestätigungsmeldung",
"sty_WARN" => "Warnmeldung",
"sty_ERRO" => "Fehlermeldung",
"sty_HLIT" => "Text hervorheben",
"sty_FXXX" => "Basisschriftfamilie",
"sty_SXXX" => "Basisschriftgröße",
"sty_PGTL" => "Seitentitel",
"sty_THDL" => "Tabellenüberschriften L.",
"sty_THDM" => "Tabellenüberschriften M.",
"sty_DTHD" => "Datumsüberschriften",
"sty_SNHD" => "Abschnittsüberschriften",
"sty_PWIN" => "Popup-Fenster",
"sty_SMAL" => "kleiner Text",
"sty_GCTH" => "Tageszelle - hover",
"sty_GTFD" => "Zellkopf 1. Tag des Monats",
"sty_GWTC" => "Wochennr. / Zeit Spalte",
"sty_GWD1" => "Wochentag Monat 1",
"sty_GWD2" => "Wochentag Monat 2",
"sty_GWE1" => "Wochenende Monat 1",
"sty_GWE2" => "Wochenende Monat 2",
"sty_GOUT" => "Außerhalb des Monats",
"sty_GTOD" => "Tageszelle - Heute",
"sty_GSEL" => "Tageszelle - ausgewählt",
"sty_LINK" => "URL und E-Mail Links",
"sty_CHBX" => "Todo Kontrollkästchen",
"sty_EVTI" => "Termintitel in Ansichten",
"sty_HNOR" => "Normaler Termin",
"sty_HPRI" => "Privater Termin",
"sty_HREP" => "Wiederholender Termin",
"sty_POPU" => "Schwebekästen",
"sty_TbSw" => "Topbalken Schatten (0:nein 1:ja)",
"sty_CtOf" => "Inhalt Versatz",

//lcalcron.php
"cro_sum_header" => "CRON JOB ZUSAMMENFASSUNG",
"cro_sum_trailer" => "ENDE DER ZUSAMMENFASSUNG",
"cro_sum_title_eve" => "EVENTS EXPIRED",
"cro_nr_evts_deleted" => "Anzahl der gelöschten Termine",
"cro_sum_title_not" => "ERINNERUNGEN",
"cro_no_reminders_due" => "Keine Erinnerungen gesendet",
"cro_due_in" => "Fällig in",
"cro_due_today" => "Heute fällig",
"cro_days" => "Tag(en)",
"cro_date_time" => "Datum / Zeit",
"cro_title" => "Titel",
"cro_venue" => "Ort",
"cro_description" => "Beschreibung",
"cro_category" => "Kategorie",
"cro_status" => "Status",
"cro_none_active" => "No reminders or periodic services active",
"cro_sum_title_use" => "BENUTZER PRÜFUNG",
"cro_nr_accounts_deleted" => "Anzahl der gelöschten Konten",
"cro_no_accounts_deleted" => "Keine Konten gelöscht",
"cro_sum_title_ice" => "EXPORTED EVENTS",
"cro_nr_events_exported" => "Number of events exported in iCalendar format to file",

//messaging.php
"mes_no_msg_no_recip" => "Nicht gesendet, keine empfänger gefunden",

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
"<h3>Datenbank Wartung</h3>
<p>Auf dieser Seite können folgende Aufgaben ausgewählt werden:</p>
<h6>Komprimieren</h6>
<p>Wenn ein Termin gelöscht wird, wird dieser nur als 'gelöscht' markiert, wird aber
nicht aus der Datenbank gelöscht. Diese Funktion löscht Termine endgültig aus der Datenbank
die vor länger als 30 Tagen gelöscht wurden und gibt den belegten Speicher wieder frei.</p>
<h6>Backup</h6>
<p>Diese Funktion generiert ein Backup der kompletten Datenbank (Struktur und Inhalt) im .sql Format.</p>
Das Backup wird in dem Verzeichnis <strong>files/</strong> mit dem Namen:
<kbd>dump-cal-lcv-yyyymmdd-hhmmss.sql</kbd> (wobei 'cal' = calendar ID, 'lcv' = calendar version und
'yyyymmdd-hhmmss' = Jahr, Monat, Tag, Stunde, Minuten und Sekunden).</p>
<p>Die Backup Datei kann zur Wiederherstellung der Datenbank (Struktur und Inhalt) verwendet werden,
entweder über die Wiederherstellungsfunkzion, die unten beschrieben ist, oder z.B. mit dem <strong>phpMyAdmin</strong> Tool, welches von den meisten Web Hosts unterstützt wird.</p>
<h6>Datenbank wiederherstellen</h6>
<p>Diese Funktion stellt die Kalenderdatenbank mit den Inhalten der hochgeladenen Sicherungsdatei wieder her(Dateityp .sql). If your .sql file is larger than 2MB you may have to modify the <b>upload_max_filesize</b> and <b>post_max_size</b> variables in the php.ini file, or split your .sql file in several smaller files. See the admin_guide.html section 3 for a detailed explanation.</p>
<p>Bei Wiederherstellung der Datenbank GEHEN ALLE AKTUELLEN DATEN VERLOREN!</p>
<h6>Termine</h6>
<p>Diese Funktion wird Termine zwischen den angegebenen Daten löschen oder die Löschung wieder aufheben. Wenn ein Datum leer bleibt bedeutet das keine Begrenzung; wenn also beiden Daten leer bleiben WERDEN ALLE TERMINE GELÖSCHT!</p><br>
<p>Wichtig: Wenn die Datenbank komprimiert wurde (siehe oben), können die Löschung der endgültig gelöschten Termine nicht wieder aufgehoben werden!</p>",

"xpl_import_csv" =>
"<h3>CSV Import Anleitung</h3>
<p>Diese Seite dient zum Hochladen und Einlesen von Terminen in den Kalender mit Hilfe einer
<strong>'Komma separierte Werte (CSV)'</strong> Text Datei.</p>
<p>Die Reihenfolge der Spalten in der CSV Datei muss wie folgt sein: Titel, Ort, Kategorie ID (siehe unterhalb),
Anfang, Ende Datum, Anfang, Ende Zeit und Beschreibung. Die erste Zeile der CSV Datei dient als Beschreibung für
die Spalten und wird ignoriert.</p>
<h6>Beispiel CSV Datei</h6>
<p>Beispiel CSV Dateien befinden sich in dem Verzeichnis '!luxcal-toolbox/' der LuxCal Installation.</p>
<h6>Feld Trennzeichen</h6>
Das Feld-Trennzeichen kann ein beliebieges zeichen sein, z.B. ein Komma oder Semikolon.
Das Feld-Trennzeichen muss einmalig sein und darf nicht Teil des Textes, der Nummern der der Daten des Feldes sein.
<h6>Datum und Zeit Format</h6>
<p>Das links ausgewählte Format für das Datum und die Zeit muss den Einträgen in der zu verarbeiteten
CSV Datei entsprechen.</p>
<p>If no start time (blank) is present, the event will be shown as a 'no time' event 
in the calendar. If the start time is 00:00 or 12:00am, the event will be shown as 
an 'all day' event in the calendar.</p>
<h6>Kategorien Tabelle</h6>
<p>Der Kalender verwendet ID Nummern um diese zu definieren. Die Kategorie IDs in der CSV
Datei sollten mit denen des Kalenders übereinstimmen oder leer sein.</p>
<p>Wenn im nächsten Schritt ein Termin als 'Geburtstag' gekennzeichnet werden soll, muss die <strong>Geburtstag
Kategorie ID</strong> entsprechend der nachfolgenden Liste gesetzt werden.</p>
<p class='hired'>Warnung: Importieren Sie nie mehr als 100 Termine auf einmal!</p>
<p>Für diesen Kalender sind folgende Kategorien definiert:</p>",

"xpl_import_user" =>
"<h3>Anleitung für den Import eines Benutzerprofils</h3>
<p>Dieses Formular wird für genutzt, um eine CSV (Comma Separated Values) Text Datei, die Benutzer-Profil-Daten enthält, in den Kalender zu importieren.</p>
<p>Für die richtige Behandlung von Sonderzeichen, muss die CSV Datei UTF-8 kodiert sein.</p>
<h6>Feld-Trennzeichen</h6>
<p>Die Feld-Trennzeichen dürfen aus beliebigen Zeichen bestehen, z.B. Kommas, Semikolons usw.. <br>
Das Feld-Trennzeichen muss eindeutig sein und darf nicht Teil des Textes in den Feldern sein.</p>
<h6>Standard Benutzer-Gruppen ID</h6>
<p>Wenn in der CSV Datei die Benutzergruppen ID leer gelassen wurde, wird die hier definierte Standard Benutzergruppen ID verwendet.</p>
<h6>Standard Passwort</h6>
<p>Wenn in der CSV Datei das Passwort leer gelassen wurde, wird das hier definierte Standard Passwort verwendet.</p>
<h6>Vorhandene Benutzer ersetzen</h6>
<p>Wenn die 'vorhandene Benutzer ersetzen' Checkbox aktiviert wurde, werden alle vorhandene Benutzer - außer dem öffentlichen Benutzer und dem Administrator - gelöscht, bevor die Benutzerprofile importiert werden.</p>
<br>
<h6>Beispiel Benutzer Profil Dateien</h6>
<p>Beispiel Benutzer Profil CSV Dateien Sample können im '!luxcal-toolbox/' Verzeichnis der Luxcal Installation gefunden werden.</p>
<h6>Felder ind er CSV Datei</h6>
<p>Die Reihenfolge der Spalten muss wie unten aufgeführt sein. Wenn die erste Reihe der CSV Datei Spaltenüberschriften enthält, wird sie ignoriert.</p>
<ul>
<li>Benutzergruppen ID: sollte mit den Benutzergruppen des Kalenders korresponieren (siehe Tabelle unten). Wenn leer wird der Benutzer der angegebenen Standard Benutzergruppe zugewiesen.</li>
<li>Benutzername: erforderlich</li>
<li>E-Mail Adresse erforderlich</li>
<li>Mobile Teleonnummer: optional</li>
<li>Telegram chat ID: optional</li>
<li>Sprache der Programmoberfläche: optional. Z.B. English, Dansk. Wenn leer wird die Standard Sprache genommen, wie sie auf der Einstellungseite ausgewählt ist.</li>
<li>Passwort: optional. Wenn leer wird das angegebene Standard Passwort verwendet.</li>
</ul>
<p>Leere Felder sollten durch zwei Anführungszeichen markiert sein. Leere Felder am Ende jeder Zeile können weg gelassen werden.</p>
<p class='hired'>Warnung: Nicht mehr als 60 Bebnutzerprofile auf einmal importieren!</p>
<h6>Tabelle Benutzergruppen IDs</h6>
<p>Für den Kalender sind aktuell folgende Benutzergruppen angelegt:</p>",

"xpl_export_user" =>
"<h3>Benutzerprofil Export Anleitung</h3>
<p>Dieses Formular wird benutzt, um <strong>Benutzerprofile</strong> des Kalenders auszulesen und zu exportieren.</p>
<p>Die Dateien werden im 'files/' Verzeichnis auf dem Server mit dem definierten Dateinamen als Komma separierte Werte abgelegt (.csv)</p>
<h6>Ziel Dateiname</h6>
Wenn nicht angegeben wird als Standard der Kalendername genommen, gefolgt vom Suffix '_users'. Die Dateierweiterung wird automatisch auf <b>.csv</b> gesetzt.</p>
<h6>Benutzergruppe</h6>
Nur die Benutzer der gewählten Benutzergruppe werden exportiert. Wenn 'alle Gruppen' ausgewählt ist, werfden die Benutzerprofile ind er Zieldatei nach der Benutzergruppe sortiert.</p>
<h6>Feld Trennzeichen</h6>
<p>Die Feld-Trennzeichen dürfen aus beliebigen Zeichen bestehen, z.B. Kommas, Semikolons usw.. <br>
Das Feld-Trennzeichen muss eindeutig sein und darf nicht Teil des Textes in den Feldern sein.</p><br>
<p>Bereits vorhandene Dateien im 'files/' Verzeichnis auf dem Server mit dem selben Dateinamen werden durch die neue datei überschrieben.</p>
<p>Die Reihenfolge der Spalten in der Zieldatei ist wie folgt: group ID, user name, E-Mail address, mobile phone number, interface language and password.<br>
<b>Hinweis:</b> Passwörter in den exportierten Benutzerprofilen sind verschlüsselt und können nicht entschlüsselt werden.</p><br>
<p>Beim <b>Herunterladen</b> der exportierten .csv Datei wird das aktuelle DAtum und die aktuelle Zeit dem Namen der herunter galadenen Datei hinzugefügt.</p><br>
<h6>Beispiel Benutzerprofil Dateien</h6>
<p>Beispiel-Benutzerprofil-Dateien (Dateierweiterung .csv) sind im '!luxcal-toolbox/' Verzeichnis des Luxcal Donwloads enthalten.</p>",

"xpl_import_ical" =>
"<h3>iCalendar Import Anleitung</h3>
<p>Diese Seite dient zum Hochladen und Einlesen von einer <strong>iCalendar</strong> Datei mit Terminen
in den LuxCal Kalender.</p>
<p>Der Datei Inhalt muss dem [<u><a href='https://tools.ietf.org/html/rfc5545'
target='_blank'>RFC5545 Standard</a></u>] der 'Internet Engineering Task Force' entsprechen.</p>
<p>Nur Termine werden importiert; andere iCal Elemente wie: To-Do, Journal, Frei /
Belegt, Zeitzone und Alarm werden ignoriert.</p>
<p>Beispiel iCalendar Dateien sind im dem Verzeichnis '!luxcal-toolbox/' der LuxCal Installation zu finden.</p>
<h6>Anpassungen der Zeitzone</h6>
<p>Für den Fall, dass die iCalendar-Datei Termine mit einer anderen Zeitzone enthält und diese an die Kalender Zeitzone angepasst werden sollen, 'Anpassungen der Zeitzone' aktivieren.</p>
<h6>Kategorien Tabelle</h6>
<p>Der Kalender verwendet ID Nummern um diese zu definieren. Die Kategorie IDs in der CSV
Datei sollten mit denen des Kalenders übereinstimmen oder leer sein.</p>
<p class='hired'>Warnung: Importieren Sie nie mehr als 80 Termine auf einmal!</p>
<p>Für diesen Kalender sind folgende Kategorien definiert:</p>",

"xpl_export_ical" =>
"<h3>iCalendar Export Anleitung</h3>
<p>Diese Seite dient zum Erzeugen und Herunterladen von einer <strong>iCalendar</strong> Datei mit Terminen
aus dem LuxCal Kalender.</p>
<p>Der <b>iCal Dateiname</b> (ohne Erweiterung) ist optional. Generierte Dateien werden am Server mit dem 
angegebenen Dateinamen, oder mit dem Namen der Kalender im Verzeichnis \"!luxcal-toolbox/\" gespeichert.
Die Dateierweiterung ist <b>.ics</b>.
Am Server im Verzeichnis \"files/\" gespeicherte Dateien mit dem selben Namen werden durch die neue Datei überschrieben.</p>
<p>Die <b>iCal Datei Beschreibung</b> (z.B. 'Besprechungen 2024') ist optional. Wenn sie angegeben ist,
wird sie in die exportierte iCal Datei eingetragen.</p>
<p><b>Termin Filter</b><br>
Die zu exportierenden Termine können gefiltert werden nach:</p>
<ul>
<li>dem Ersteller</li>
<li>der Kategorie</li>
<li>dem Anfang Datum</li>
<li>hinzugefügt/zuletzt geändert Datum</li>
</ul>
<p>Jeder Filter ist optional.<br>
Ein leeres Datum bedeutet: keine Filterung</p>
<br>
<p>Der Inhalt der Datei entspricht dem [<u><a href='https://tools.ietf.org/html/rfc5545' target='_blank'>RFC5545 Standard</a></u>]
der 'Internet Engineering Task Force'.</p>
<p>Beim <b>Herunterladen</b> der exportierten iCal Datei wird das Datum und die Uhrzeit zum Namen hinzugefügt.</p>
<p>Beispiel iCalendar Dateien sind im Verzeichnis '!luxcal-toolbox/' der LuxCal Installation zu finden.</p>",

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
