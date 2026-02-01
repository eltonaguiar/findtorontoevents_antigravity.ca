<?php
/*
= LuxCal admin interface language file =

This file has been produced by LuxSoft. Please send comments / improvements to rb@luxsoft.eu.
Wijzigingen en vertalingen zijn aangebracht door J.C.Barnhoorn - Hellevoetsluis 9 mei 2024

This file is part of the LuxCal Web Calendar.
*/
$ax = array(

//general
"none" => "Geen",
"no" => "nee",
"yes" => "ja",
"own" => "eigen",
"all" => "alle",
"or" => "of",
"back" => "Terug",
"ahead" => "Vooruit",
"close" => "Sluiten",
"always" => "altijd",
"at_time" => "@", //datum en tijdscheidingsteken (bijv. 30-01-2020 @ 10:45)
"times" => "tijd",
"cat_seq_nr" => "categorie volgnummer",
"rows" => "rijen",
"columns" => "kolommen",
"hours" => "uur",
"minutes" => "minuten",
"user_group" => "gebruikersgroep",
"event_cat" => "aciviteitcategorie",
"email" => "Email",
"telegram" => "Telegram",
"sms" => "SMS",
"id" => "ID",
"username" => "Gebruikersnaam",
"password" => "Wachtwoord",
"public" => "Niet aangemeld",
"logged_in" => "Aangemeld",
"pw_no_chars" => "<, > en ~ niet toegestaan in het wachtwoord",

//settings.php - fieldset headers + general
"set_general_settings" => "Kalender algemeen",
"set_navbar_settings" => "Navigatiebalk",
"set_event_settings" => "Activiteiten",
"set_user_settings" => "Gebruikers",
"set_upload_settings" => "File Uploads",
"set_reminder_settings" => "Herinneringen",
"set_perfun_settings" => "Periodieke Functies (alleen relevant indien cronjob loopt)",
"set_sidebar_settings" => "Binnenkort zijbalk (alleen relevant indien in gebruik)",
"set_view_settings" => "Weergave",
"set_dt_settings" => "Datum/Tijd",
"set_save_settings" => "Instellingen opslaan",
"set_test_mail" => "Test e-mail",
"set_mail_sent_to" => "Test e-mail verstuurd naar",
"set_mail_sent_from" => "Deze test mail is verstuurd via de pagina Kalenderinstellingen van de webkalender",
"set_mail_failed" => "Versturen test e-mail mislukt - ontvanger(s)",
"set_missing_invalid" => "ontbrekende of ongeldige instellingen (achtergrond gekleurd)",
"set_settings_saved" => "Kalenderinstellingen opgeslagen",
"set_save_error" => "Database fout. Opslaan kalenderinstellingen mislukt",
"hover_for_details" => "Ga met de muis over de beschrijving voor details",
"default" => "standaard",
"enabled" => "aan",
"disabled" => "uit",
"pixels" => "pixels",
"warnings" => "Waarschuwingen",
"notices" => "Mededelingen",
"visitors" => "Bezoekers",
"height" => "Height",
"no_way" => "U bent niet bevoegd tot het uitvoeren van deze actie.",

//settings.php - general settings.
"versions_label" => "Versies",
"versions_text" => "• kalender versie, gevolgd door de in gebruik zijnde database<br>• PHP versie<br>• database versie",
"calTitle_label" => "Kalendertitel",
"calTitle_text" => "Weergegeven in de titelbalk van de kalender en gebruikt in e-mail herinneringen",
"calUrl_label" => "Kalender-URL",
"calUrl_text" => "Webadres van de kalender",
"calEmail_label" => "Kalender e-mailadres",
"calEmail_text" => "Het e-mailadres voor het ontvangen van contactberichten en voor het zenden/ontvangen van e-mail herinneringen<br>Opmaak: 'e-mail' of 'naam &#8826;mail&#8827;'.",
"logoPath_label" => "Pad/naam van de logo afbeelding",
"logoPath_text" => "Indien opgegeven, verschijnt het logo in de linkerbovenhoek van de kalender. Indien ook een link naar de bovenliggende pagina is opgegeven (zie hieronder), dan zal het logo de link naar deze pagina worden. Het logo mag een maximum hoogte en breedte hebben van 70 pixels.",
"logoXlPath_label" => "Pad/naam van aanmeld logo afbeelding",
"logoXlPath_text" => "Indiens opgegeven, zal een logo van de opgegeven afmetingen worden getoond op de aanmeldpagina onder de login gegevens.",
"backLinkUrl_label" => "Link naar bovenliggende pagina",
"backLinkUrl_text" => "URL van de bovenliggende pagina. Indien gespecificeerd, zal er een Terug-knop worden weergegeven aan de linkerzijde van de Navigatie Balk met een link naar de opgegeven URL.<br>Bijvoorbeeld om terug te linken naar de pagina waar vandaan de kalender werd gestart. Indien een logo pad/naam is opgegeven (zie hierboven), dan wordt er geen Terug knop weergegeven, maar zal daarvoor in de plaats het logo de terug-link zijn.",
"timeZone_label" => "Tijdzone",
"timeZone_text" => "De door de kalender gebruikte tijdzone voor het correct weergeven van de huidige tijd",
"see" => "zie",
"notifChange_label" => "Stuur mededeling met kalenderwijzigingen",
"notifChange_text" => "Wanneer een gebruiker een activiteit toevoegt, wijzigt of verwijdert, zal een e-mailbericht naar de opgegeven e-mailadressen worden gestuurd.",
"chgRecipList" => "puntkomma gescheiden ontvangerslijst",
"maxXsWidth_label" => "Max. breedte van smalle displays",
"maxXsWidth_text" => "Voor displays met een breedte kleiner dan het hierboven gespecificeerde aantal pixels, wordt de kalender in een speciale responsieve modus weergegeven. Daarbij worden minder relevante elementen weggelaten.",
"rssFeed_label" => "RSS feed links",
"rssFeed_text" => "Indien geactiveerd: Voor gebruikers met minstens rechten 'bekijken' zal een RSS feed link worden weergegeven in de voet van de kalender; ook zal een RSS feed link worden toegevoegd aan de HTML head van de kalender pagina's.",
"logging_label" => "Log kalender gegevens",
"logging_text" => "De kalender kan foutmeldingen, waarschuwingen, mededelingen en bezoekersgegevens loggen. Foutmeldingen worden altijd gelogd. Het loggen van waarschuwingen, mededelingen en bezoekersgegevens kan worden aan- of uitgezet door de relevante vakjes aan te vinken. Alle foutmeldingen, waarschuwingen en mededelingen worden in het bestand 'logs/luxcal.log' gelogd en bezoekersgegevens worden in de bestanden 'logs/hitlog.log' en 'logs/botlog.log' gelogd.<br>Opmerking: PHP foutmeldingen, waarschuwingen en mededelingen worden op een andere plaats opgeslagen, bepaald door uw ISP (Internet Service Provider).",
"maintMode_label" => "PHP Onderhoudsmode",
"maintMode_text" => "Indien aangevinkt, in the PHP scripts data submitted via the note (message) function and data stored in the 'note' variable getoond zal worden in de voettekstbalk.",
"reciplist" => "<br>De lijst met geadresseerden kan bestaan uit: gebruikersnamen, e-mailadressen, telefoonnummers, Telegram chat IDs en bestandsnamen met geadresseerden ingesloten door vierkante haken, gescheiden door puntkomma's. Bestanden met geadresseerden dienen een geadresseerde per regel te bevatten en deze bestanden moeten als .txt bestanden worden opgeslagen in de map 'reciplists'.",
"calendar" => "kalender",
"user" => "gebruiker",
"database" => "database",

//settings.php - navigation bar settings.
"contact_label" => "Contactknop",
"contact_text" => "Indien geactiveerd: Er wordt een contactknop getoond in het beheermenu. Indien deze knop wordt geselecteerd zal een contactformulier openen, dat gebruikt kan worden om een bericht naar de kalenderbeheerder te sturen.",
"optionsPanel_label" => "Opties menu",
"optionsPanel_text" => "Het weergeven van menu's onder de 'Opties' knop (helemaal links in de navigatiebalk).<br>• Het kalender menu is beschikbaar voor de admin en maakt het mogelijk om een kalender te kiezen (inschakelen alleen relevant als meerdere kalenders zijn geïnstalleerd).<br>• Het Weergaven menu kan worden gebruikt om de verschillende kalenderweergaven te kiezen.<br>• Het Gebruikersgroepen menu kan worden gebruikt om activiteiten weer te geven die horen bij de geselecteerde gebruikersgroepen.<br>• Het Gebruikers menu kan worden gebruikt om activiteiten weer te geven die horen bij de geselecteerde gebruikers.<br>• Het Categorieën menu kan worden gebruikt om activiteiten weer te geven die tot de geselecteerde activiteitencategorieën behoren.<br>• Met het Talen menu kan de taal van de gebruikersinterface worden gekozen (inschakelen alleen relevant als meerdere talen zijn geïnstalleerd).<br>Opmerking: Als geen enkel menu is geselecteerd, zal de 'Opties' knop (helemaal links in de navigatiebalk) <b>niet</b> worden weergegeven.",
"calMenu_label" => "kalender",
"viewMenu_label" => "weergaven",
"groupMenu_label" => "groepen",
"userMenu_label" => "gebruikers",
"catMenu_label" => "categorieën",
"langMenu_label" => "talen",
"availViews_label" => "Beschikbare kalenderweergaven",
"availViews_text" => "Beschikbare kalenderweergaven voor zowel niet aangemelde als voor aangemelde gebruikers worden d.m.v. een reeks van door komma's gescheiden cijfers gedefinieerd.<br>Betekenins van deze nummers:<br>1: jaarweergave<br>2: maandweergave (7 dagen)<br>3: werkmaand weergave<br>4: week weergave (7 dagen)<br>5: werkweek weergave<br>6: dag weergave<br>7: binnenkort weergave<br>8: wijzigingen weergave<br>9: matrix weergave (categorieën)<br>10: matrix weergave (gebruikers)<br>11: gantt chart weergave",
"viewButtonsL_label" => "Weergaveknoppen op de navigatiebalk (groot beeldscherm)",
"viewButtonsS_label" => "Weergaveknoppen op de navigatiebalk (klein beeldscherm)",
"viewButtons_text" => "Weergaveknoppen op de navigatiebalk voor zowel niet aangemelde als voor aangemelde gebruikers, worden d.m.v. een reeks van door komma's gescheiden cijfers gedefinieerd. Elk cijfer in de reeks correspondeert met een weer te geven knop. Als geen enkel cijfer wordt ingevuld, wordt er geen weergaveknop getoond.<br>Betekenis van de cijfers:<br>1: Jaar<br>2: Maand<br>3: Werkmaand<br>4: Week<br>5: Werkweek<br>6: Dag<br>7: Binnenkort<br>8: Wijzigingen<br>9: Matrix(C)<br>10: Matrix(U)<br>11: Gantt Chart<br>De volgorde van de cijfers bepaalt de volgorde van de weer te geven knoppen.<br>Bijvoorbeeld: '2,4' betekent: geef de knoppen 'Maand' en 'Week' weer.",
"defaultViewL_label" => "Standaardweergave bij opstarten (groot beeldscherm)",
"defaultViewL_text" => "Standaardweergave bij het starten van de kalender voor zowel niet aangemelde als voor aangemelde gebruikers met een groot beeldscherm.<br>Aanbevolen instelling: Maand",
"defaultViewS_label" => "Standaardweergave bij opstarten (klein beeldscherm)",
"defaultViewS_text" => "Standaardweergave bij het starten van de kalender voor zowel niet aangemelde als voor aangemelde gebruikers met een klein beeldscherm.<br>Aanbevolen instelling: Binnenkort",
"language_label" => "Standaard taal voor gebruikers interface (public user)",
"language_text" => "Voor standaard (niet aangemelde) gebruikers zal de taal indesteld voor de browser gebruikers interface ook voor de kalender worden gebruikt. Als de browser taal geen geldige taal is, Wordt deze standaard taal gebruikt.<br>Opmerking: De bestanden ui-{taal}.php, ai-{taal}.php, ug-{taal}.php en ug-layout.png moeten in de lang/ map aanwezig zijn. {taal} = taal gekozen voor de gebruikersinterface. Bestandsnamen in kleine letter!",
"birthday_cal_label" => "PDF Verjaardagskalender",
"birthday_cal_text" => "Indien ingeschakeld, verschijnt er een optie 'PDF Bestand - Verjaardag' in het zijmenu voor gebruikers met 'view' rechten. Bekijk de admin_guide.html - Verjaardagskalender voor verdere details",
"sideLists_label" => "Goedkeuren, Tedoen, Komende Afspraken",
"sideLists_text" => "Indien ingeschakeld, verschijnt er een optie in het zijmenu om het betreffende bestand te tone. De 'Goed te keuren Evenementen' lijst is alleen beschikbaar voor gebruikers met ten minste 'manager' rechten.",
"toapList_label" => "Goed te keuren lijst",
"todoList_label" => "Te Doen lijst",
"upcoList_label" => "Komende afspraken lijst",

//settings.php - events settings.
"privEvents_label" => "Plaatsen van privé activiteiten",
"privEvents_text" => "Privé activiteiten zijn alleen zichtbaar voor de gebruiker die de activiteit invoerde. De mogelijke instellingen zijn:<br><ul><li><b>uit</b>: gebruiker kan geen privé activiteiten invoeren.</li><li><b>aan</b>: gebruiker kan privé activiteiten invoeren.</li><li><b>standaard</b>: wanneer een nieuwe activiteit wordt toegevoegd, zal het 'privé' vinkje in het Activiteit venster standaard aan staan.</li><li><b>altijd</b>: wanneer nieuwe activiteiten worden toegevoegd zullen deze altijd privé zijn, de 'privé' checkbox in het Activiteit venster zal niet zichtbaar zijn.</li></ul>",
"venueInput_label" => "Locaties aangeven",
"venueInput_text" => "In het gebeurtenis venster kan een locatie worden ingevoerd. Er kan een vrije tekst worden ingevoerd of uit een voorgedefinieerde lijst worden gekozen. If Free text is selected, the user can type the venue, if List is selected the user can select a venue from a drop-down list and when Both is selected, the user can choose between the two.<br> Als er is gekozen voor een lijst moet de 'files' map een bestand bevatten met de naam venues.txt met een locatie per regel.",
"timeDefault_label" => "Nieuwe activiteiten toevoegen - tijd weergave",
"timeDefault_text" => "When adding events, in the Event window the default way the event time fields appear in the event form can be set as follows:<br>â€¢ show times: The start and end time fields are shown and ready to be completed<br>â€¢ all day: The All Day check box is checked, no start and end time fields are shown<br>â€¢ no time: The No Time check box is checked, no start and end time fields are shown.",
"evtDelButton_label" => "Toon knop Verwijderen in het Activiteit venster",
"evtDelButton_text" => "<ul><li><b>uit</b>: de knop 'Verwijderen' in het Activiteit venster is niet zichtbaar. Gebruikers met edit rechten kunnen dus geen activiteiten verwijderen.</li><li><b>aan</b>: de knop 'Verwijderen' in het Activiteit venster is zichtbaar voor alle gebruikers.</li><li></b>manager</b>: de knop 'Verwijderen' in het Activiteit venster is alleen zichtbaar voor gebruikers met tenminste 'manager' rechten.</li>",
"eventColor_label" => "Activiteitkleuren gebaseerd op",
"eventColor_text" => "Activiteiten in de verschillende kalenderweergaven kunnen worden weergegeven in de kleur die is toegewezen aan de groep waar de eigenaar van de activiteit toe behoort of de kleur van de categorie die aan de activiteit is toegekend.",
"defVenue_label" => "Standaardlocatie",
"defVenue_text" => "In dit tekst veld kan een standaard locatie worden gegeven voor wanneer men een nieuwe activiteit toevoegd.",
"xField1_label" => "Extra veld 1",
"xField2_label" => "Extra veld 2",
"xFieldx_text" => "Optioneel tekstveld. Indien dit veld voorkomt in een model in de sectie Weergave, zal het als een tekstveld worden toegevoegd aan het Activiteiten venster en aan de activiteiten in alle kalender pagina's. <br>• <b>Label</b>: optioneel tekst label voor het extra veld (max. 15 tekens). Bijv. 'E-mailadres', 'Website', 'Tel.nummer'<br>• <b>Minimale gebruikersrechten</b>: het veld is alleen zichtbaar voor gebruikers met de geselecteerde rechten of hoger.",
"evtWinSmall_label" => "Verkleind activiteiten venster",
"evtWinSmall_text" => "Indien aangevinkt, wordt, bij het toevoegen/wijzigen van activiteiten, alleen een subset van de invoervelden in het activiteitenvenster getoond. Om alle invoervelden in het activiteitenvenster te zien, dient u eerst op een pijl te klikken.",
"emojiPicker_label" => "Emoji kiezer in gebeurtenis venster",
"emojiPicker_text" => "When enabled, in the Event Add/Edit window an emoji picker can be selected to add emoji to the event title and to the description fields.",
"mapViewer_label" => "Kaartviewer URL",
"mapViewer_text" => "Als hier een kaartviewer is gespecificeerd, en een adres in het locatie veld (van het activiteiten venster) is ingesloten door '!' tekens, dan wordt een klikbare 'adres'-knop zichtbaar in de kalender weergave. Door met de muis te bewegen over deze knop, wordt de tekst van het betreffende adres getoond. Door vervolgens met de muis te klikken op deze knop, wordt een nieuw scherm geopend dat het betreffende adres op de kaart zal tonen.<br>De volledige URL van de kaartviewer moet worden aangegeven. Aan het einde van deze URL wordt dan automatisch het betreffende adres toegevoegd.<br>Voorbeelden van kaartviewers:<br><ul><li>Google Maps: https://maps.google.com/maps?q=</li><li>OpenStreetMap: https://www.openstreetmap.org/search?query=</li></ul>Als dit veld leeg gelaten wordt, zal een aanwezig adres in het locatie veld niet als adres-knop zichtbaar zijn.",
"evtDrAndDr_label" => "Gebeurtenis slepen",
"evtDrAndDr_text" => "Indien ingeschakeld, dan kunnen gebeurtenissen worden versleept in de jaar- en maandkalender en de mini kalender in het zijpaneel. Als 'beheerder' is geselecteerd, kunnen alleen gebruikers met minstens beheerders rechten deze functie gebruiken. Kijk in de admin_guide.html voor meer details.",
"free_text" => "Vrije tekst",
"venue_list" => "Locatie lijst",
"both" => "Beide",
"xField_label" => "Label",
"show_times" => "toon tijden",
"check_ald" => "hele dag",
"check_ntm" => "geen tijd",
"min_rights" => "Minimale gebruikersrechten",
"no_color" => 'geen kleur',
"manager_only" => 'beheerder',

//settings.php - user accounts settings.
"selfReg_label" => "Zelfregistratie",
"selfReg_text" => "Gebruikers toestaan zich te registreren en toegang tot de kalender te krijgen.<br>Gebruikersgroep waar zichzelf geregistreerde gebruikers in worden geplaatst.",
"selfRegQA_label" => "Zelfregistratie vraag/antwoord",
"selfRegQA_text" => "Als zelfregistratie is ingeschakeld, wordt tijdens het zelfregistratieproces aan de gebruiker deze vraag gesteld en kan hij/zij zich alleen zelf registreren als het juiste antwoord op deze vraag wordt gegeven. Als het vraagveld leeg blijft, wordt er tijdens de zelfregistratie ook geen vraag gesteld.",
"selfRegNot_label" => "Melding van een zelfregistratie",
"selfRegNot_text" => "Stuur een e-mail naar het kalender e-mailadres wanneer een zelfregistatie plaatsvindt.",
"restLastSel_label" => "Laatste gebruikers selecties onthouden",
"restLastSel_text" => "Indien aangevinkt, worden van elke gebruiker zijn/haar laatste selecties (van het Opties menu in de navigatiebalk) bewaard en bij een volgend bezoek automatisch weer toegepast. Indien de gebruiker gedurende het gespecificeerde aantal dagen niet inlogt, gaan de laatste selecties verloren.",
"answer" => "Antwoord",
"exp_days" => "days",
"view" => "bekijken",
"post_own" => 'eigen invoer',
"post_all" => 'alle invoeren',
"manager" => 'invoeren/manager',

//settings.php - view settings.
"templFields_text" => "Betekenis van de cijfers:<br>1: Locatie<br>2: Activiteit categorie<br>3: Omschrijving<br>4: Extra veld 1 (zie hieronder)<br>5: Extra veld 2 (zie hieronder)<br>6: Stuur mail gegevens (alleen als een e-mail herinnering is gevraagd)<br>7: Datum/tijd ingevoerd/gewijzigd en de betreffende persoon<br>8: Pdf, image en video bijlagen als hyperlinks.<br>De volgorde van de cijfers bepaalt de volgorde waarin de betreffende velden worden weergegeven.",
"evtTemplate_label" => "Activiteit modellen - Algemeen",
"evtTemplate_text" => "De activiteitvelden en de volgorde waarin deze worden weergegeven op de algemene kalender pagina's, de binnenkort pagina's en in de hover box met activiteitendetails, kunnen worden opgegeven d.m.v. een reeks van cijfers. Indien een cijfer is gespecificeerd, dan zal het corresponderende veld worden weergegeven.",
"evtTemplPublic" => "Openbare gebruikers",
"evtTemplLogged" => "Aangemelde gebruikers",
"evtTemplGen" => "Algemeen",
"evtTemplUpc" => "Binnenkort",
"evtTemplPop" => "Pop up",
"sortEvents_label" => "Sorteer activiteiten op tijd of categorie",
"sortEvents_text" => "In de verschillende views, kunnen events gesorteerd worden op de volgende criteria:<br>• event tijd<br>• event categorie volgnummer",
"yearStart_label" => "Beginmaand in Jaar weergave",
"yearStart_text" => "Indien een beginmaand is opgegeven (1 - 12), zal de kalender in Jaar weergave altijd met deze maand beginnen en het jaar van deze eerste maand zal pas veranderen vanaf de eerste dag van dezelfde maand in het volgende jaar.<br>De waarde 0 heeft een speciale betekenis: de beginmaand is dan namelijk gebaseerd op de huidige datum en zal in de eerste rij maanden vallen.",
"YvRowsColumns_label" => "Aantal rijen en kolommen in Jaar weergave",
"YvRowsColumns_text" => "Aantal rijen van telkens vier maanden weer te geven in Jaar weergave<br>Aanbevolen waarde: 4, zodat door 16 maanden kan worden gescrold.<br>Aantal maanden (kolommen) weer te geven in elke rij in Jaar weergave<br>Aanbevolen waarde: 3 of 4.",
"MvWeeksToShow_label" => "Aantal weken in Maand weergave",
"MvWeeksToShow_text" => "Aantal weken weer te geven in Maand weergave<br>Aanbevolen waarde: 10, zodat door 2.5 maand kan worden gescrold<br>De waarden 0 en 1 hebben een speciale betekenis:<br>0: geef precies een maand weer - zonder activiteiten in de voorafgaande en volgende dagen.<br>1: geef precies een maand weer - met ook activiteiten in de voorafgaande en volgende dagen.",
"XvWeeksToShow_label" => "Aantal weken in Matrix weergave",
"XvWeeksToShow_text" => "Het aantal weken weergegeven in Matrix weergave.",
"GvWeeksToShow_label" => "Aantal weken in Gantt-Chart weergave",
"GvWeeksToShow_text" => "Het aantal weken weergegeven in Gantt-Chart weergave.",
"workWeekDays_label" => "Werkdagen",
"workWeekDays_text" => "Dagen die als werkdagen worden gekleurd in de kalenderweergaven en die bijvoorbeeld zichtbaar zijn in de weken in Werkmaand en Werkweek weergave.<br>Geef het nummer van elke werkdag aan. Bijv. 12345: maandag - vrijdag<br>Niet ingegeven dagen worden als weekend dagen aangemerkt.",
"weekStart_label" => "Eerste dag van de week",
"weekStart_text" => "Voer het nummer in van de eerste dag van de week.",
"lookBackAhead_label" => "Aantal dagen terug/vooruit kijken",
"lookBackAhead_text" => "Aantal dagen dat wordt teruggekeken in de Takenlijst en aantal dagen dat wordt vooruitgekeken in het overzicht Binnenkort, in de Taken Lijst en in de RSS feeds.",
"searchBackAhead_label" => "Default aantal dagen terug/vooruit zoeken",
"searchBackAhead_text" => "Wanneer op de zoekpagina geen datums zijn ingevuld, is dit het standaard aantal dagen dat terug en vooruit wordt gezocht.",
"dwStartEndHour_label" => "Beginuur en Einduur in de Dag/Week weergave",
"dwStartEndHour_text" => "Het uur waarop een normale dag begint/eindigt<br>Wanneer deze waarden op bijv. 6 en 18 zijn gesteld, wordt in de Dag/Week weergaven niet nodeloos ruimte gebruikt voor de tijd tussen middernacht en 6:00 uur en tussen 18:00 en middernacht (uren waar normaal niet veel wordt uitgevoerd).<br>De tijdkiezer, die wordt gebruikt bij het invoeren van een tijd, zal ook op deze uren beginnen/eindigen.",
"dwTimeSlot_label" => "Tijdverdeling in Dag/Week weergave (minuten)",
"dwTimeSlot_text" => "Tijdverdeling en hoogte per rij in Dag/Week weergave in aantal minuten.<br>Deze waarde bepaalt, samen met het uur waarop de normale dag begint en eindigt (zie hierboven), het aantal rijen in de Dag/Week weergaven.",
"dwTsInterval" => "Tijdsverdeling",
"dwTsHeight" => "Hoogte",
"evtHeadX_label" => "Activiteiten layout in Maand, Week/Dag weergave",
"evtHeadX_text" => "Sjablonen met maskers van velden die in elk activiteiten venster getoond dienen te worden.<br>De volgende maskers zijn beschikbaar:<table><tr><td>#ts</td><td>- starttijd</td></tr><tr><td>#tx</td><td>- starttijd en eindtijd</td></tr><tr><td>#e</td><td>- titel van activiteit</td></tr><tr><td>#o</td><td>- eigenaar van activiteit</td></tr><tr><td>#v</td><td>- locatie van activiteit</td></tr><tr><td>#lv</td><td>- locatie, voorafgegaan door het label 'Locatie:' </td></tr><tr><td>#c</td><td>- categorie</td></tr><tr><td>#lc</td><td>- categorie, voorafgegaan door het label 'Categorie:' </td></tr><tr><td>#a</td><td>- leeftijd (zie opmerking hieronder)</td></tr><tr><td>#x1</td><td>- extra veld 1</td></tr><tr><td>#lx1</td><td>- extra veld 1, voorafgegaan door het label zoals vermeld bij ..... </td></tr><tr><td>#x2</td><td>- extra veld 2</td></tr><tr><td>#lx2</td><td>- extra veld 2, voorafgegaan door het label zoals vermeld bij ..... </td></tr><tr><td>#/</td><td>- nieuwe regel</td></tr></table><br>De volgorde van de velden bepaalt ook de volgorde van weergave in het activiteiten venster. Andere tekens dan de maskers, blijven ongewijzigd en maken deel uit van het weergegeven activiteiten venster.<br><br>In deze sjabloon zijn HTML-tags toegestaan. Bijvoorbeeld: &lt;b&gt;#e&lt;/b&gt;.<br><br>Het | teken kan worden gebruikt om het sjabloon in secties te splitsen. Als binnen een sectie, de gedefinieerde maskers resulteren in een lege string, dan wordt die hele sectie niet weergegeven.<br><br>Opmerking: De leeftijd wordt weergegeven als de activiteit deel uitmaakt van een categorie met 'Herhalen' ingesteld op 'elk jaar' en het geboortejaar tussen haakjes ergens in het beschrijvingsveld of een van de extra velden van de activiteit wordt vermeld.",
"monthView" => "Maand weergave",
"wkdayView" => "Week/Dag weergave",
"ownerTitle_label" => "Toon plaatser van de activiteit bij de activiteit",
"ownerTitle_text" => "In de verschillende kalenderweergaven kan de plaatser voor de naam van de activiteit worden vermeld.",
"showSpanel_label" => "Zijpaneel in kalenderweergaven",
"showSpanel_text" => "In de kalenderweergave, rechts naast de hoofdkalender, kan het volgende worden weergegeven:<br>• een mini kalender om snel terug of vooruit te kijken zonder eerst de datum van de hoofdkalender te moeten veranderen.<br>• een decoratieve afbeelding voor de huidige maand<br>• een infoscherm om voor een periode bepaalde berichten c.q. aankondigingen te plaatsen.<br>>Per item kan een door comma's gescheiden lijst met weergave nummers wordt opgegeven, waarvoor het item moet worden weergegeven.<br>Mogelijke weergave nummers:<br>0: Alle weergaven<br>1: Jaar<br>2: Maand<br>3: Werkmaand<br>4: Week<br>5: Werkweek<br>6: Dag<br>7: Binnenkort<br>8: Wijzigingen<br>9: Matrix(C)<br>10: Matrix(U)<br>11: Gantt Chart.<br>Indien 'Vandaag' is aangevinkt, zal het zijpaneel de datum van vandaag gebruiken, anders wordt de datum geselecteerd voor de hoofdkalender gebruikt.<br>Kijk in het bestand 'admin_guide.html' voor verdere Zijpaneel details.",
"spMiniCal" => "Mini kalender",
"spImages" => "Afbeeldingen",
"spInfoArea" => "Infoscherm",
"spToday" => "Vandaag",
"topBarDate_label" => "Toon huidige datum in bovenste balk",
"topBarDate_text" => "In- en uischakelen van de datum in bovenste balk. Als het is ingeschakeld kun je op deze datum klikken om de kalender teryg te zetten naar de huidige datum.",
"showImgInMV_label" => "Miniatuurafbeeldingen weergeven in maandoverzicht",
"showImgInMV_text" => "Hier kunnen desgewenst miniatuurafbeeldingen ook in het maandoverzicht worden weergegeven.<br><ul><li><b>aangevinkt</b>: miniatuurafbeeldingen worden in de dagcellen weergegeven.</li><li><b>uitgevinkt</b>: miniatuurafbeeldingen worden alleen weergegeven bij met de muis bewegen over een dagcel (als zo'n dagcel een afbeelding bevat).</li></ul>",
"urls" => "URL links",
"emails" => "e-mail links",
"monthInDCell_label" => "Maandnaam voor elke dag",
"monthInDCell_text" => "Toon in Maand weergave de 3-letterige maandnaam voor elke dag",
"scrollDCell_label" => "Scrollbar in dagcellen",
"scrollDCell_text" => "Als in het maandoverzicht een dagcel te klein is, zal i.p.v. de dagcel hoogte te vergroten een vertikale scrollbar verschijnen.",

//settings.php - date/time settings.
"dateFormat_label" => "Datumopmaak (dd mm jjjj)",
"dateFormat_text" => "Tekenreeks met de opmaak van datums in de kalender weergaven en input velden.<br>Toegestane tekens: y = jaar, m = maand en d = dag.<br>Niet-alfanumerieke tekens kunnen als scheidingsteken worden gebruikt en worden letterlijk overgenomen.<br>Voorbeelden:<br>y-m-d: 2024-10-31<br>m.d.y: 10.31.2024<br>d/m/y: 31/10/2024",
"dateFormat_expl" => "bijv. y.m.d: 2024.10.31",
"MdFormat_label" => "Datumopmaak (dd maand)",
"MdFormat_text" => "Tekenreeks met de opmaak van datums bestaande uit dag en maand.<br>Toegestane tekens: M = maand in tekst, d = dag in cijfers.<br>Niet-alfanumerieke tekens kunnen als scheidingsteken worden gebruikt en worden letterlijk overgenomen.<br>Voorbeelden:<br>d M: 12 april<br>M, d: juli, 14",
"MdFormat_expl" => "bijv. M, d: juli, 14",
"MdyFormat_label" => "Datumopmaak (dd maand jjjj)",
"MdyFormat_text" => "Tekenreeks met de opmaak van datums bestaande uit dag, maand en jaar.<br>Toegestane tekens: d = dag in cijfers, M = maand in tekst, y = jaar in cijfers.<br>Niet-alfanumerieke tekens kunnen als scheidingsteken worden gebruikt en worden letterlijk overgenomen.<br>Voorbeelden:<br>d M y: 12 april 2024<br>M d, y: juli 8, 2024",
"MdyFormat_expl" => "bijv. M d, y: juli 8, 2024",
"MyFormat_label" => "Datumopmaak (maand jjjj)",
"MyFormat_text" => "Tekenreeks met de opmaak van datums bestaande uit maand en jaar.<br>Toegestane tekens: M = maand in tekst, y = jaar in cijfers.<br>Niet-alfanumerieke tekens kunnen als scheidingsteken worden gebruikt en worden letterlijk overgenomen.<br>Voorbeelden:<br>M y: april 2024<br>y - M: 2024 - juli",
"MyFormat_expl" => "bijv. M y: april 2024",
"DMdFormat_label" => "Datumopmaak (dag dd maand)",
"DMdFormat_text" => "Tekenreeks met de opmaak van datums bestaande uit weekdag, dag en maand.<br>Toegestane tekens: WD = weekdag in tekst, M = maand in tekst, d = dag in cijfers.<br>Niet-alfanumerieke tekens kunnen als scheidingsteken worden gebruikt en worden letterlijk overgenomen.<br>Voorbeelden:<br>WD d M: vrijdag 12 april<br>WD, M d: Maandag, juli 14",
"DMdFormat_expl" => "bijv. WD - M d: zondag - april 6",
"DMdyFormat_label" => "Datumopmaak (dag dd maand jjjj)",
"DMdyFormat_text" => "Tekenreeks met de opmaak van datums bestaande uit weekdag, dag, maand en jaar.<br>Toegestane tekens: WD = weekdag in tekst, M = maand in tekst, d = dag in cijfers, y = jaar in cijfers.<br>Niet-alfanumerieke tekens kunnen als scheidingsteken worden gebruikt en worden letterlijk overgenomen.<br>Voorbeelden:<br>WD d M y: vrijdag 13 april 2024<br>WD - M d, y: Maandag - juli 16, 2024",
"DMdyFormat_expl" => "bijv. WD, M d, y: maandag, juli 16, 2024",
"timeFormat_label" => "Tijdopmaak (uu mm)",
"timeFormat_text" => "Tekenreeks met de opmaak van tijden in de kalender weergaven en input velden.<br>Toegestane tekens: h = uren, H = uren met opvulnul, m = minuten, a = am/pm (optioneel), A = AM/PM (optioneel).<br>Niet-alfanumerieke tekens kunnen als scheidingsteken worden gebruikt en worden letterlijk overgenomen.<br>Voorbeelden:<br>h:m: 18:35<br>h.m a: 6.35 pm<br>H:mA: 06:35PM",
"timeFormat_expl" => "bijv. h:m: 22:35 en h:mA: 10:35PM",
"weekNumber_label" => "Geef weeknummers weer",
"weekNumber_text" => "De weergave van weeknummers in de relevante views kan aan- of uitgezet worden",
"time_format_us" => "12 uur AM/PM",
"time_format_eu" => "24 uur",
"sunday" => "zondag",
"monday" => "maandag",
"time_zones" => "TIJD ZONES",
"dd_mm_yyyy" => "dd-mm-jjjj",
"mm_dd_yyyy" => "mm-dd-jjjj",
"yyyy_mm_dd" => "jjjj-mm-dd",

//settings.php - file uploads settings.
"maxUplSize_label" => "Maximum bestandsgrootte bij uploaden",
"maxUplSize_text" => "Maximum toegestane bestandsgrootte wanneer gebruikers bijlagen of miniatuurafbeeldingen uploaden.<br>Let op: De meeste PHP installaties hebben een maximum bestandsgrootte van 2 MB ingesteld (in het php_ini bestand) ",
"attTypes_label" => "Bijlage bestandstypen",
"attTypes_text" => "Door komma's gescheiden lijst met geldige bijlage bestandstypen die mogen worden ge-upload.<br>Bijvoorbeeld: .pdf,.jpg,.gif,.png,.mp4,.avi",
"tnlTypes_label" => "Miniatuurafbeeldingen bestandstypen",
"tnlTypes_text" => "Door komma's gescheiden lijst met geldige miniatuurafbeeldingen bestandstypen die mogen worden ge-upload.<br>Bijvoorbeeld: .jpg,.jpeg,.gif,.png",
"tnlMaxSize_label" => "Miniatuurafbeelding - maximum grootte",
"tnlMaxSize_text" => "Maximum afbeeldingsgrootte van een miniatuurafbeelding. Indien gebruikers grotere afbeeldingen uploaden, worden de afbeeldingen automatisch verkleind naar de maximum grootte. Let op: Hoge miniatuurafbeeldingen zullen de dagen in de Maand weergave oprekken, hetgeen tot ongewenste effecten kan leiden.",
"tnlDelDays_label" => "Miniatuurafbeelding - verwijdermarge",
"tnlDelDays_text" => "Indien een miniatuurafbeelding wordt gebruikt na dit aantal dagen geleden, kan die afbeelding niet worden verwijderd.<br>De waarde 0 dagen betekent dat de miniatuurafbeelding niet kan worden verwijderd.",
"days" =>"dagen",
"mbytes" => "MB",
"wxhinpx" => "B x H in pixels",

//settings.php - reminders settings.
"services_label" => "Beschikbare berichtendiensten",
"services_text" => "Beschikbare diensten om herinneringen aan bepaalde activiteiten te versturen. Als een dienst niet is geselecteerd, zal het betreffende onderdeel in het Activiteiten venster ook niet worden weergegeven. Als geen enkele dienst is geselecteerd, zullen ook geen herinneringen worden verstuurd.",
"msgLogging_label" => "Notification message logging",
"msgLogging_text" => "Indien geactiveerd, worden de verstuurde kenningsgevingsberichten gelogd in het messages.log bestand. Het 'weken' veld geeft aan hoe lang de gelogde gegevens bewaard moeten worden",
"smsCarrier_label" => "SMS-carrier sjabloon",
"smsCarrier_text" => "Het SMS-carrier sjabloon wordt gebruikt om het SMS-gateway e-mailadres samen te stellen: ppp#sss@carrier, waarbij deze tekens het volgende betekenen:<br><ul><li><b>ppp</b>: optionele text string die voor het telefoonnummer wordt geplaatst</li><li><b>#</b>: placeholder voor het mobiele telefoonnummer van de ontvanger (de kalender zal de # vervangen door het telefoonnummer)</li><li><b>sss</b>: optionele text string die wordt toegevoegd na het telefoonnummer, bijv. een gebruikersnaam en wachtwoord, vereist door sommige dienstverleners</li><li><b>@</b>: scheidingsteken</li><li><b>carrier</b>: carrier adres (bijv. mail2sms.com)</li></ul><br>Sjabloon voorbeelden: #@xmobile.com, 0#@carr2.int, #myunmypw@sms.gway.net.",
"smsCountry_label" => "SMS-landnummer",
"smsCountry_text" => "Als de SMS-gateway zich in een ander land bevindt dan de kalender, dan moet het landnummer van het land waar de kalender wordt gebruikt, worden opgegeven.<br><br>Vink aan, of de provider het voorvoegsel '+' of '00' vereist.",
"smsSubject_label" => "SMS-onderwerp sjabloon",
"smsSubject_text" => "Indien opgegeven, zal de tekst in dit sjabloon naar het onderwerp veld worden gekopieerd van het SMS-je dat naar de carrier wordt gestuurd. De tekst mag het teken # bevatten. Dit # teken zal worden vervangen door het telefoonnummer van de kalender of van de eigenaar van de activiteit (afhankelijk van bovenstaande instelling).<br>Voorbeeld: 'FROMPHONENUMBER=#'.",
"smsAddLink_label" => "Link naar de activiteit toevoegen aan de SMS",
"smsAddLink_text" => "Indien aangevinkt, wordt een link naar de activiteit aan elk SMS-je toegevoegd. Wanneer deze link op een mobiele telefoon wordt geopend, zal de onvanger de details van de betreffende activiteit kunnen zien.",
"maxLenSms_label" => "Maximum lengte SMS-bericht",
"maxLenSms_text" => "SMS-berichten worden verstuurd met utf-8 karakter codering. Berichten tot 70 tekens resulteren in een enkel SMS-bericht; berichten > 70 tekens, met veel Unicode tekens, kunnen worden opgedeeld in meerdere SMS-berichten.",
"calPhone_label" => "Kalender telefoonnummer",
"calPhone_text" => "Het telefoonnummer wordt gebruikt als zender ID bij het versturen van SMS herinneringsberichten.<br><br>Het formaat is in principe vrij, met een maximum van 20 tekens (sommige landen eisen een telefoonnummer, andere landen accepteren ook alfabetische tekens).<br><br>Als de SMS-service niet actief is of als geen SMS onderwerk sjabloon is gedefinieerd, mag dit veld leeg zijn.",
"notSenderEml_label" => "Voeg 'Antwoord aan' veld toe aan e-mail",
"notSenderEml_text" => "Indien geselecteerd, zullen herinnerings e-mails een veld 'Antwoord aan' bevatten met het e-mailadres van de eigenaar van de activiteit. De ontvanger kan dit e-mailadres gebruiken om te antwoorden.",
"notSenderSms_label" => "Afzender van SMS-jes",
"notSenderSms_text" => "Wanneer de kalender herinnerings SMS-jes vestuurt, kan de afzender van het SMS-je of het telefoonnummer van de kalender zijn, of het telefoonnummer van de gebruiker die de activiteit heeft ingevoerd.<br><br>Indien 'gebruiker' is geselecteerd en in het gebruikersprofiel geen telefoonnummer is opgegeven, zal het telefoonnummer van de kalender worden genomen.<br><br>Indien het telefoonnummer van de gebruiker wordt genomen, kan de ontvanger ook op het SMS-je antwoorden.",
"defRecips_label" => "Standaard lijst met geadresseerden",
"defRecips_text" => "Indien gespecificeerd, zal dit de standaard lijst in het activiteiten venster zijn voor e-mail en/of SMS-herinneringen. Indien dit veld leeg blijft, zal de standaard geadresseerde de gebruiker zijn die de betreffende activiteit heeft ingevoerd.",
"maxEmlCc_label" => "Max. aantal geadresseerden per e-mail",
"maxEmlCc_text" => "Meestal staan ISPs slechts een beperkt aantal geadresseerden per e-mail toe. Tijdens het versturen van e-mails of SMS-reminders, als het aantal geadresseerden hoger is dan het hier gespecificeerde aantal, zal de e-mail worden gesplitst in meerdere e-mails die elk worden verstuurd aan het hier gespecificeerde maximale aantal geadresseerden.",
"emlFootnote_label" => "Herinnerings e-mail voetnoot",
"emlFootnote_text" => "Vrije tekst wordt toegevoegd als een paragraaf aan het einde van een e-mail bericht. HTML tags zijn toegestaan.",
"mailServer_label" => "Mail server",
"mailServer_text" => "PHP mail is prima bruikbaar voor niet beveiligde e-mails in kleine aantallen. Voor grotere aantallen te versturen e-mails of wanneer wachtwoordbeveiliging vereist is, dient u SMTP mail te gebruiken.<br>Om SMTP mail te kunnen gebruiken is een SMTP mailserver nodig. De configuratie parameters voor deze SMTP server moeten hieronder worden gespecificeerd.",
"smtpServer_label" => "SMTP server naam",
"smtpServer_text" => "Als SMTP mail is geselecteerd, moet hier de SMTP servernaam worden vermeld. Bij toepassing van gmail, dient u als SMTP servernaam het volgende in te vullen: smtp.gmail.com",
"smtpPort_label" => "SMTP poort nummer",
"smtpPort_text" => "Als SMTP mail is geselecteerd, moet hier het SMTP portnummer worden gespecificeerd. Bijvoorbeeld 25, 465 of 587. Bij toepassing van gmail, dient u als poortnummer in te vullen: 465",
"smtpSsl_label" => "SSL (Secure Sockets Layer)",
"smtpSsl_text" => "Als SMTP mail is geselecteerd, kies dan hier of de secure sockets layer (SSL) moet worden gebruikt. Voor gmail: aan",
"smtpAuth_label" => "SMTP authenticatie",
"smtpAuth_text" => "Als SMTP authenticatie is geselecteerd, worden de gebruikersnaam en het wachtwoord hiernaast daarvoor gebruikt. Voor gmail is de gebruikersnaam bijvoorbeeld het deel van het e-mail adres voor de @.",
"tlgToken_label" => "Telegram token",
"tlgToken_text" => "Telegram token in de volgende opmaak: &lt;bot ID&gt;:&lt;bot hash&gt;. Voor details kijk in de installation_guide.html, onderdeel Event Notification Messages.",
"cc_prefix" => "Landnummer begint met voorvoegsel + of 00",
"general" => "Algemeen",
"php_mail" => "PHP mail",
"smtp_mail" => "SMTP mail (vul onderstaande velden in)",

//settings.php - periodic function settings.
"cronHost_label" => "Cronjob host",
"cronHost_text" => "Selecteer waar de cronjob draait die periodiek het script 'lcalcron.php' start.<br>• <b>lokaal</b>: cronjob draait op dezelfde server als de kalender<br>• <b>extern</b>: cronjob draait op een externe server of lcalcron.php wordt met de hand gestart (testen)<br>• <b>IP-adres</b>: cronjob draait op een externe server met het opgegeven IP adres.",
"cronSummary_label" => "Admin cronjob samenvatting",
"cronSummary_text" => "E-mail een cronjob samenvatting naar de kalenderbeheerder.<br>Inschakelen is alleen zinvol als een cronjob is geactiveerd voor de kalender.",
"chgSummary_text" => "Aantal dagen dat wordt teruggegaan voor het overzicht met kalenderwijzigingen.<br>Als het aantal dagen 0 is, wordt er geen overzicht met kalenderwijzigingen verstuurd.",
"icsExport_label" => "Dagelijkse export van iCal activiteiten",
"icsExport_text" => "Indien ingeschakeld, worden alle activiteiten in het datumbereik van -1 week tot +1 jaar geëxporteerd in iCalendar formaat in een .ics file in de 'files' folder.<br>De bestandsnaam wordt de kalendernaam met spatie's vervangen door underscores. Oude bestanden worden overschreven door nieuwere.",
"eventExp_label" => "Aantal dagen voordat activiteiten worden verwijderd",
"eventExp_text" => "Aantal dagen na de activiteit datum waarna deze automatisch wordt verwijderd.<br>Indien 0 of als er geen cronjob is gedefinieerd, worden geen activiteiten verwijderd.",
"maxNoLogin_label" => "Max. aantal dagen niet ingelogd",
"maxNoLogin_text" => "Als een gebruiker gedurende dit aantal dagen niet is ingelogd, dan wordt zijn/haar account automatisch verwijderd.<br>Als het aantal dagen 0 is, zullen gebruikersaccounts nooit worden verwijderd",
"weeks" => "Weken",
"local" => "lokaal",
"remote" => "extern",
"ip_address" => "IP adres",

//settings.php - mini calendar / sidebar settings.
"popFieldsSbar_label" => "Activiteit velden - sidebar hover box",
"popFieldsSbar_text" => "De weer te geven activiteitvelden in de hover box met activiteitdetails in de stand-alone sidebar kunnen worden opgegeven d.m.v. een reeks van cijfers.<br>Als dit veld leeg is, zal geen hover box worden weergegeven.",
"showLinkInSB_label" => "Toon links in zijbalk",
"showLinkInSB_text" => "Toon URLs in de omschrijving van een activiteit als een hyperlink in de Binnenkort zijbalk",
"sideBarDays_label" => "Dagen te tonen in zijbalk",
"sideBarDays_text" => "Aantal dagen vooruit te kijken in de Binnenkort zijbalk.",

//login.php
"log_log_in" => "Aanmelden",
"log_remember_me" => "Onthoud mij",
"log_register" => "Registreren",
"log_change_my_data" => "Mijn gegevens wijzigen",
"log_save" => "Opslaan",
"log_done" => "Klaar",
"log_un_or_em" => "Gebruikersnaam of e-mailadres",
"log_un" => "Gebruikersnaam",
"log_em" => "E-mailadres",
"log_ph" => "Mobiel telefoonnummer",
"log_tg" => "Telegram chat ID",
"log_answer" => "Uw antwoord",
"log_pw" => "Wachtwoord",
"log_expir_date" => "Account afloopdatum",
"log_account_expired" => "Deze account is verlopen",
"log_new_un" => "Nieuwe gebruikersnaam",
"log_new_em" => "Nieuw e-mailadres",
"log_new_pw" => "Nieuw wachtwoord",
"log_con_pw" => "Bevestig wachtwoord",
"log_pw_msg" => "Hier zijn de aanmeldgegevens voor de web kalender",
"log_pw_subject" => "Uw wachtwoord",
"log_npw_subject" => "Uw nieuwe wachtwoord",
"log_npw_sent" => "Uw nieuwe wachtwoord is verstuurd",
"log_registered" => "Registratie gelukt - Uw wachtwoord is per mail verstuurd",
"log_em_problem_not_sent" => "E-mailprobleem - uw wachtwoord kon niet worden verstuurd",
"log_em_problem_not_noti" => "E-mailprobleem - de beheerder kon niet worden geïnformeerd",
"log_un_exists" => "Gebruikersnaam bestaat al",
"log_em_exists" => "E-mailadres bestaat al",
"log_un_invalid" => "Gebruikersnaam ongeldig (min lengte 2: A-Z, a-z, 0-9, en _-.) ",
"log_em_invalid" => "E-mailadres ongeldig",
"log_ph_invalid" => "Ongeldig mobiel telefoonnummer",
"log_tg_invalid" => "Invalid Telegram chat ID",
"log_sm_nr_required" => "SMS: mobile phone number required",
"log_tg_id_required" => "Telegram: chat ID required",
"log_sra_wrong" => "Incorrect answer to the question",
"log_sra_wrong_4x" => "You have answered incorrectly 4 times - try again in 30 minutes",
"log_un_em_invalid" => "Gebruikersnaam of wachtwoord onjuist",
"log_un_em_pw_invalid" => "Uw gebruikersnaam/e-mailadres of wachtwoord is onjuist",
"log_pw_error" => "Wachtwoord komt niet overeen",
"log_no_un_em" => "U hebt uw gebruikersnaam of e-mailadres niet ingevoerd",
"log_no_un" => "Voer uw gebruikersnaam in",
"log_no_em" => "Voer uw e-mailadres in",
"log_no_pw" => "U hebt uw wachtwoord niet ingevoerd",
"log_no_rights" => "Aanmelden afgewezen: u hebt geen toegangsrechten - Vraag de beheerder",
"log_send_new_pw" => "Stuur mij een nieuw wachtwoord",
"log_new_un_exists" => "De nieuwe gebruikersnaam bestaat al",
"log_new_em_exists" => "Het nieuwe e-mailadres bestaat al",
"log_ui_language" => "Taal gebruikersinterface",
"log_new_reg" => "Nieuwe gebruikersregistratie",
"log_date_time" => "Datum / tijd",
"log_time_out" => "Time out",

//categories.php
"cat_list" => "Categorieën",
"cat_edit" => "Wijzigen",
"cat_delete" => "Verwijderen",
"cat_add_new" => "Nieuwe categorie toevoegen",
"cat_add" => "Toevoegen",
"cat_edit_cat" => "Categorie wijzigen",
"cat_sort" => "Sorteer op naam",
"cat_cat_name" => "Naam categorie",
"cat_symbol" => "Symbool",
"cat_symbol_repms" => "Categorie symbool (vervangt minisquare)",
"cat_symbol_eg" => "bijv. A, X, ♥, ⛛",
"cat_matrix_url_link" => "URL link (zichtbaar in matrix weergave)",
"cat_seq_in_menu" => "Volgorde in menu",
"cat_cat_color" => "Categorie kleur",
"cat_text" => "Tekst",
"cat_background" => "Achtergrond",
"cat_select_color" => "Kies kleur",
"cat_subcats" => "Sub-<br>categorieën",
"cat_subcats_opt" => "Aantal subcategorieën (optioneel)",
"cat_copy_from" => "Kopieer van",
"cat_eml_changes_to" => "Send event changes to",
"cat_url" => "URL",
"cat_name" => "Naam",
"cat_subcat_note" => "Note that the currently existing subcategories may already be used for events",
"cat_save" => "Opslaan",
"cat_added" => "Categorie toegevoegd",
"cat_updated" => "Categorie gewijzigd",
"cat_deleted" => "Categorie verwijderd",
"cat_not_added" => "Categorie niet toegevoegd",
"cat_not_updated" => "Categorie niet gewijzigd",
"cat_not_deleted" => "Categorie niet verwijderd",
"cat_nr" => "#",
"cat_repeat" => "Herhalen",
"cat_every_day" => "elke dag",
"cat_every_week" => "elke week",
"cat_every_month" => "elke maand",
"cat_every_year" => "elk jaar",
"cat_overlap" => "Overlap<br>toegestaan<br>(tussentijd)",
"cat_need_approval" => "Activiteit vereist<br>goedkeuring",
"cat_no_overlap" => "Geen overlap toegestaan",
"cat_same_category" => "zelfde categorie",
"cat_all_categories" => "alle categorieën",
"cat_gap" => "gap",
"cat_ol_error_text" => "Foutmelding, in geval van overlap",
"cat_no_ol_note" => "Pas op: er wordt niet gecontroleerd op reeds aanwezige activiteiten; deze kunnen dus overlappen",
"cat_ol_error_msg" => "activiteit overlapt - kies een andere tijd",
"cat_no_ol_error_msg" => "Geen overlap foutmelding",
"cat_duration" => "Activiteits-<br>Duur<br>! = vast",
"cat_default" => "standaard (geen eindtijd)",
"cat_fixed" => "vast",
"cat_event_duration" => "Activiteitsduur",
"cat_olgap_invalid" => "Ongeldige overlaptijd",
"cat_duration_invalid" => "Ongeldige tijdsduur",
"cat_no_url_name" => "Geen URL link naam",
"cat_invalid_url" => "Ongeldige URL link",
"cat_day_color" => "Dag kleur",
"cat_day_color1" => "Dag kleur (jaar/matrix weergave)",
"cat_day_color2" => "Dag kleur (maand/week/dag weergave)",
"cat_approve" => "Activiteit vereist goedkeuring",
"cat_check_mark" => "Vinkje",
"cat_not_list" => "Herinnerings<br>lijst",
"cat_label" => "betekenis",
"cat_mark" => "symbool",
"cat_name_missing" => "Categorienaam ontbreekt",
"cat_mark_label_missing" => "Vinkteken/label ontbreekt",

//users.php
"usr_list_of_users" => "Lijst met gebruikers",
"usr_name" => "Gebruikersnaam",
"usr_email" => "E-mailadres",
"usr_phone" => "Mobiel telefoonnummer",
"usr_phone_br" => "Mobiel<br>telefoonnummer",
"usr_tg_id" => "Telegram chat ID",
"usr_tg_id_br" => "Telegram<br>chat ID",
"usr_not_via" => "Herinner via",
"usr_not_via_br" => "Herinner<br>via",
"usr_language" => "Taal",
"usr_ui_language" => "Gebruikersinterface taal",
"usr_group" => "Groep",
"usr_password" => "Wachtwoord",
"usr_expir_date" => "Account verloopdatum",
"usr_select_exp_date" => "Kies verloopdatum",
"usr_blank_none" => "leeg: geen",
"usr_expires" => "Verlopen",
"usr_edit_user" => "Gebruikersprofiel wijzigen",
"usr_add" => "Gebruiker toevoegen",
"usr_edit" => "Wijzigen",
"usr_delete" => "Verwijderen",
"usr_login_0" => "Eerste aanmelding",
"usr_login_1" => "Laatste aanmelding",
"usr_login_cnt" => "Aanmeldingen",
"usr_add_profile" => "Profiel toevoegen",
"usr_upd_profile" => "Profiel wijzigen",
"usr_if_changing_pw" => "Alleen als het wachtwoord verandert",
"usr_pw_not_updated" => "Wachtwoord niet gewijzigd",
"usr_added" => "Gebruiker toegevoegd",
"usr_updated" => "Gebruikersprofiel gewijzigd",
"usr_deleted" => "Gebruiker verwijderd",
"usr_not_deleted" => "Gebruiker niet verwijderd",
"usr_cred_required" => "Gebruikersnaam, e-mailadres en wachtwoord zijn verplicht",
"usr_name_exists" => "Gebruikersnaam bestaat al",
"usr_email_exists" => "E-mailadres bestaat al",
"usr_un_invalid" => "Gebruikersnaam ongeldig (min lengte 2: A-Z, a-z, 0-9, en _-.) ",
"usr_em_invalid" => "E-mailadres ongeldig",
"usr_ph_invalid" => "Ongeldig mobiel telefoonnummer",
"usr_tg_invalid" => "Invalid Telegram chat ID",
"usr_xd_invalid" => "Invalid account expiration date",
"usr_cant_delete_yourself" => "Je kunt jezelf niet verwijderen",
"usr_go_to_groups" => "Ga naar Groepen",
"usr_all_cats" => "Alle Categorieën",
"usr_select" => "Selecteer",
"usr_transfer" => "Verplaats",
"usr_transfer_evts" => "Verplaats Gebeurtenissen",
"usr_transfer_ownership" => "Verplaats eigenaar van gebeurtenissen",
"usr_cur_owner" => "Huidige eigenaar",
"usr_new_owner" => "Nieuwe eigenaar",
"usr_event_cat" => "Gebeurtenis categorie",
"usr_sdate_between" => "Startdatum tussen",
"usr_cdate_between" => "Maakdatum tussen",
"usr_select_start_date" => "Selecteer startdatum",
"usr_select_end_date" => "Selecteer einddatum",
"usr_blank_no_limit" => "Lege datum: geen limiet",
"usr_no_undone" => "OPGEPAST, ACTIE KAN NIET WORDEN HERSTELD",
"usr_invalid_sdata" => "Ongeldige startdatum",
"usr_invalid_cdata" => "Ongeldige maakdatum",
"usr_edate_lt_sdate" => "Einddatum voor startdatum",
"usr_no_new_owner" => "Nieuwe eigenaar niet aangegeven",
"usr_evts_transferred" => "Klaar. Gebeurtenissen verplaatst",

//groups.php
"grp_list_of_groups" => "Lijst met Gebruikersgroepen",
"grp_name" => "Groepsnaam",
"grp_priv" => "Gebruikersrechten",
"grp_categories" => "Activiteiten categorieën",
"grp_all_cats" => "alle categorieën",
"grp_rep_events" => "Herhalende<br>activiteiten",
"grp_m-d_events" => "Meerdaagse<br>activiteiten",
"grp_priv_events" => "Privé<br>activiteiten",
"grp_upload_files" => "Bestanden<br>uploaden",
"grp_tnail_privs" => "Miniatuur<br>rechten",
"grp_priv0" => "Geen rechten",
"grp_priv1" => "Kalender bekijken",
"grp_priv2" => "Invoeren/wijzigen eigen activiteiten",
"grp_priv3" => "Invoeren/wijzigen alle activiteiten",
"grp_priv4" => "Invoeren/wijzigen + manager",
"grp_priv9" => "Beheerder-functies",
"grp_may_post_revents" => "Mag herhalende activiteiten invoeren",
"grp_may_post_mevents" => "Mag meerdags activiteiten invoeren",
"grp_may_post_pevents" => "Mag privé activiteiten invoeren",
"grp_may_upload_files" => "Mag bestanden uploaden",
"grp_tn_privs" => "Thumbnails rechten",
"grp_tn_privs00" => "geen",
"grp_tn_privs11" => "zie alle",
"grp_tn_privs20" => "beheer eigen",
"grp_tn_privs21" => "m. eigen/z. alle",
"grp_tn_privs22" => "manage alle",
"grp_edit_group" => "Gebruikersgroep wijzigen",
"grp_sub_to_rights" => "Subject to user rights",
"grp_view" => "Bekijken",
"grp_add" => "Toevoegen",
"grp_edit" => "Wijzigen",
"grp_delete" => "Verwijderen",
"grp_add_group" => "Groep toevoegen",
"grp_upd_group" => "Groep wijzigen",
"grp_added" => "Groep toegevoegd",
"grp_updated" => "Groep gewijzigd",
"grp_deleted" => "Groep verwijderd",
"grp_not_deleted" => "Groep niet verwijderd",
"grp_in_use" => "Groep is in gebruik",
"grp_cred_required" => "Groepsnaam, Rechten en Categorieën zijn verplicht",
"grp_name_exists" => "Groepsnaam al gebruikt",
"grp_name_invalid" => "Groepsnaam ongeldig (min lengte 2: A-Z, a-z, 0-9, en _-.) ",
"grp_check_add" => "Tenminste een check box in de colom Toevoegen moet actief zijn",
"grp_background" => "Achtergrondkleur",
"grp_select_color" => "Kies kleur",
"grp_invalid_color" => "Ongeldige kleuropmaak (#XXXXXX waar X = HEX-waarde)",
"grp_go_to_users" => "Ga naar Gebruikers",

//texteditor.php
"edi_text_editor" => "Bewerk informatie tekst",
"edi_file_name" => "File name",
"edi_save" => "Opslaan tekst",
"edi_backup" => "Backup tekst",
"edi_select_file" => "Kies bestand",
"edi_info_text" => "Informatie tekst",
"edi_pub_recips" => "Openbare geadresseerden",
"edi_recips_list" => "Lijst met geadresseerden",
"edi_new_recips_list" => "Nieuwe lijst met geadresseerden",
"edi_no_file_name" => "Geen bestandsnaam opgegeven",
"edi_no_text" => "Er is geen tekst",
"edi_confirm_changes" => "The text changes have not been saved\\nDo you want to continue?", //don't remove '\\n'
"edi_text_saved" => "Tekst opgeslagen als bestand $1",

//database.php
"mdb_dbm_functions" => "Database Functies",
"mdb_noshow_tables" => "Geen toegang tot tabel(len)",
"mdb_noshow_restore" => "Geen backup bestand geselecteerd of bestand is te groot om te uploaden",
"mdb_file_not_sql" => "Backup bestand moet een SQL bestand zijn (type '.sql')",
"mdb_db_content" => "Inhoud Database",
"mdb_total_evenst" => "Totaal aantal gebeurtenissen",
"mdb_evts_older_1m" => "Gebeurtenissen ouder dan 1 maand",
"mdb_evts_older_6m" => "Gebeurtenissen ouder dan 6 maanden",
"mdb_evts_older_1y" => "Gebeurtenissen ouder dan 1 jaar",
"mdb_evts_deleted" => "Totaal aantal verwijderde gebeurtenissen",
"mdb_not_removed" => "nog niet verwijderd van de DB",
"mdb_total_cats" => "Totaal aantal categorieën",
"mdb_total_users" => "Totaal aantal gebruikers",
"mdb_total_groups" => "Totaal aantal gebruikersgroepen",
"mdb_compact" => "Comprimeer database",
"mdb_compact_table" => "Comprimeer tabel",
"mdb_compact_error" => "Fout",
"mdb_compact_done" => "OK, klaar",
"mdb_purge_done" => "Activiteiten meer dan 30 dagen geleden verwijderd definitief weggegooid",
"mdb_backup" => "Back-up database",
"mdb_backup_table" => "Back-up tabel",
"mdb_backup_file" => "Backup bestand",
"mdb_backup_done" => "OK, klaar",
"mdb_records" => "gegevens",
"mdb_restore" => "Herstel database",
"mdb_restore_table" => "Tabel terugzetten",
"mdb_inserted" => "gegevens toegevoegd",
"mdb_db_restored" => "Database teruggezet",
"mdb_db_upgraded" => "Database ge-upgrade",
"mdb_no_bup_match" => "Backup bestand komt niet overeen met kalenderversie<br>Database niet teruggezet",
"mdb_events" => "Activiteiten",
"mdb_delete" => "verwijderen",
"mdb_undelete" => "herstellen",
"mdb_between_dates" => "voorkomend tussen",
"mdb_deleted" => "Activiteiten verwijderd",
"mdb_undeleted" => "Activiteiten hersteld",
"mdb_file_saved" => "Back-up bestand opgeslagen in map 'files' op de server.",
"mdb_file_name" => "Bestandsnaam",
"mdb_start" => "Start",
"mdb_no_function_checked" => "Geen functie(s) geselecteerd",
"mdb_write_error" => "Opslaan back-up bestand mislukt<br>Controleer rechten van de 'files/' map",

//import/export.php
"iex_file" => "Gekozen bestand",
"iex_file_name" => "Doel-bestandsnaam",
"iex_file_description" => "Beschrijving iCal bestand",
"iex_filters" => "Activiteitfilters",
"iex_export_usr" => "Exporteer gebruikers, download CSV bestand",
"iex_import_usr" => "Importeer gebruikers, upload CSV bestand",
"iex_upload_ics" => "Importeer activiteiten, upload iCal bestand",
"iex_create_ics" => "Exporteer activiteiten, download iCal bestand",
"iex_tz_adjust" => "Tijdzone aanpassingen",
"iex_upload_csv" => "Importeer activiteiten, upload CSV bestand",
"iex_upload_file" => "Upload bestand",
"iex_create_file" => "Download bestand",
"iex_download_file" => "Download bestand",
"iex_fields_sep_by" => "Velden gescheiden door",
"iex_birthday_cat_id" => "ID verjaardagcategorie",
"iex_default_grp_id" => "ID standaard gebruikersgroep",
"iex_default_cat_id" => "ID standaardcategorie",
"iex_default_pword" => "Default wachtwoord",
"iex_if_no_pw" => "Indien geen wachtwoord gespecificeerd",
"iex_replace_users" => "Vervang bestaande gebruikers",
"iex_if_no_grp" => "indien geen gebruikersgroep gevonden",
"iex_if_no_cat" => "indien geen categorie gevonden",
"iex_import_events_from_date" => "Importeer activiteiten die plaatsvinden vanaf",
"iex_no_events_from_date" => "Geen activiteiten gevonden na de opgegeven datum",
"iex_see_insert" => "zie aanwijzingen aan de rechterzijde",
"iex_no_file_name" => "Bestandsnaam ontbreekt",
"iex_no_begin_tag" => "ongeldig iCal bestand",
"iex_bad_date" => "Ongeldige datum",
"iex_date_format" => "Activiteit datum opmaak",
"iex_time_format" => "Activiteit tijd opmaak",
"iex_number_of_errors" => "Aantal fouten in de lijst",
"iex_bgnd_highlighted" => "achtergrond gemarkeerd",
"iex_verify_event_list" => "Lijst van activiteiten verifiëren, fouten verbeteren en klik op",
"iex_add_events" => "Activiteiten aan database toevoegen",
"iex_verify_user_list" => "Controleer gebruikerslijst, corrigeer mogelijke fouten en klik",
"iex_add_users" => "Voeg gebruikers toe aan database",
"iex_select_ignore_birthday" => "Vink eventueel Verjaardag en/of Wissen aan",
"iex_select_ignore" => "Vink Wissen aan om activiteit over te slaan",
"iex_check_all_ignore" => "Alle Wissen vakjes aan/uit",
"iex_title" => "Titel",
"iex_venue" => "Plaats",
"iex_owner" => "Eigenaar",
"iex_category" => "Categorie",
"iex_date" => "Datum",
"iex_end_date" => "Einddatum",
"iex_start_time" => "Begintijd",
"iex_end_time" => "Eindtijd",
"iex_description" => "Omschrijving",
"iex_repeat" => "Herhaal",
"iex_birthday" => "Verjaardag",
"iex_ignore" => "Wissen",
"iex_events_added" => "activiteiten toegevoegd",
"iex_events_dropped" => "activiteiten overgeslagen (al aanwezig)",
"iex_users_added" => "gebruikers toegevoegd",
"iex_users_deleted" => "gebruikers verwijderd",
"iex_csv_file_error_on_line" => "CSV bestandsfout op regel",
"iex_between_dates" => "Plaatsvindend tussen",
"iex_changed_between" => "Toegevoegd/gewijzigd tussen",
"iex_select_date" => "Kies datum",
"iex_select_start_date" => "Kies begindatum",
"iex_select_end_date" => "Kies einddatum",
"iex_group" => "Gebruikersgroep",
"iex_name" => "Gebruikersnaam",
"iex_email" => "E-mail adres",
"iex_phone" => "Telefoon nummer",
"iex_msgID" => "Chat ID",
"iex_lang" => "Taal",
"iex_pword" => "Wachtwoord",
"iex_all_groups" => "alle groepen",
"iex_all_cats" => "alle categorieën",
"iex_all_users" => "alle gebruikers",
"iex_no_events_found" => "Geen activiteiten gevonden",
"iex_file_created" => "Bestand aangemaakt",
"iex_write error" => "Opslaan exportbestand mislukt<br>Controleer permissies van 'files/' map",
"iex_invalid" => "foutief",
"iex_in_use" => "reeds in gebruik",

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
"sty_css_intro" =>  "Waarden die op deze pagina worden gespecificeerd, moeten voldoen aan de CSS-normen",
"sty_preview_theme" => "Voorbeeld thema",
"sty_preview_theme_title" => "Bekijk dit thema in de kalender",
"sty_stop_preview" => "Stop bekijken",
"sty_stop_preview_title" => "Stop met bekijken van thema in de kalender",
"sty_save_theme" => "Bewaar thema",
"sty_save_theme_title" => "Bewaar dit thema in database",
"sty_backup_theme" => "Maak een backup van het thema",
"sty_backup_theme_title" => "Exporteer het thema van de database naar een bestand",
"sty_restore_theme" => "Herstel het thema",
"sty_restore_theme_title" => "Herstel het thema van een eerder geexporteerde file",
"sty_default_luxcal" => "standaard LuxCal thema",
"sty_close_window" => "Sluit het venster",
"sty_close_window_title" => "sluit dit venster",
"sty_theme_title" => "Thema titel",
"sty_general" => "Algemeen",
"sty_grid_views" => "Raster / Weergaven",
"sty_hover_boxes" => "Hover Vensters",
"sty_bgtx_colors" => "Achtergrond/tekst kleuren",
"sty_bord_colors" => "Border kleuren",
"sty_fontfam_sizes" => "Font familie/grootte",
"sty_font_sizes" => "Font grootte",
"sty_miscel" => "Diversen",
"sty_background" => "Achtergrond",
"sty_text" => "Tekst",
"sty_color" => "Kleur",
"sty_example" => "Voorbeeld",
"sty_theme_previewed" => "Voorbeeld modus- je kunt nu de kalender bekijken en daarna, als je klaar bent, de voorbeeld modus stoppen.",
"sty_theme_saved" => "Thema opgeslagen in de database",
"sty_theme_backedup" => "Thema gekopieerd van de database naar bestand:",
"sty_theme_restored1" => "Thema teruggeplaatst van bestand:",
"sty_theme_restored2" => "Klik op Opslaan om thema te bewaren in de database",
"sty_unsaved_changes" => "WAARSCHUWING – Niet opgeslagen wijzigingen!\\nAls je dit venster afsluit, verdwijnen de wijzigingen.", //niet verwijderen '\\n'
"sty_number_of_errors" => "Aantal fouten in de lijst",
"sty_bgnd_highlighted" => "achtergrond gemarkeerd",
"sty_XXXX" => "kalender algemeen",
"sty_TBAR" => "kalender top balk",
"sty_BHAR" => "balken, kopteksten en regels",
"sty_BUTS" => "knoppen",
"sty_DROP" => "drop-down menus",
"sty_XWIN" => "popup vensters",
"sty_INBX" => "invoegblokken",
"sty_OVBX" => "overlay blokken",
"sty_BUTH" => "knoppen - bij erover gaan",
"sty_FFLD" => "formuliervelden",
"sty_CONF" => "bevestigingsbericht",
"sty_WARN" => "waarschuwingsbericht",
"sty_ERRO" => "foutbericht",
"sty_HLIT" => "tekstmarkering",
"sty_FXXX" => "standaard lettertype familie",
"sty_SXXX" => "standaard letter grootte",
"sty_PGTL" => "pagina titels",
"sty_THDL" => "tabel koptitel L",
"sty_THDM" => "tabel koptitel M",
"sty_DTHD" => "datum koptitels",
"sty_SNHD" => "sectie koptitels",
"sty_PWIN" => "popup vensters",
"sty_SMAL" => "kleine tekst",
"sty_GCTH" => "dagcel - eroverheen gaan",
"sty_GTFD" => "celtitel 1e dag van maand",
"sty_GWTC" => "weeknr / tijd kolom",
"sty_GWD1" => "weekdag maand 1",
"sty_GWD2" => "weekdag maand 2",
"sty_GWE1" => "weekend maand 1",
"sty_GWE2" => "weekend maand 2",
"sty_GOUT" => "buiten actuele maand",
"sty_GTOD" => "dagcel vandaag",
"sty_GSEL" => "dagcel geselecteerde dag",
"sty_LINK" => "URL en e-mail links",
"sty_CHBX" => "tedoen check box",
"sty_EVTI" => "activiteiten titel in weergaven",
"sty_HNOR" => "normale activiteit",
"sty_HPRI" => "privé activiteit",
"sty_HREP" => "herhalende activiteit",
"sty_POPU" => "eroverheen gaan popup venster",
"sty_TbSw" => "top balk schaduw (0:nee 1:ja)",
"sty_CtOf" => "inhoud offset",

//lcalcron.php
"cro_sum_header" => "CRONJOB SAMENVATTING",
"cro_sum_trailer" => "EINDE SAMENVATTING",
"cro_sum_title_eve" => "ACTIVITEITEN VERLOPEN",
"cro_nr_evts_deleted" => "Aantal activiteiten verwijderd",
"cro_sum_title_not" => "HERINNERINGEN",
"cro_no_reminders_due" => "Geen herinneringen te versturen",
"cro_due_in" => "Vindt plaats over",
"cro_due_today" => "Vandaag",
"cro_days" => "dag(en)",
"cro_date_time" => "Datum/tijd",
"cro_title" => "Titel",
"cro_venue" => "Locatie",
"cro_description" => "Omschrijving",
"cro_category" => "Categorie",
"cro_status" => "Status",
"cro_none_active" => "Geen herinneringen actief",
"cro_sum_title_use" => "GEBRUIKERSACCOUNTS VERLOPEN",
"cro_nr_accounts_deleted" => "Aantal accounts verwijderd",
"cro_no_accounts_deleted" => "Geen accounts verwijderd",
"cro_sum_title_ice" => "GEEXPORTEERDE ACTIVITEITEN",
"cro_nr_events_exported" => "Aantal gebeurtenissen dat is geëxporteerd in iCalendar opmaak naar bestand",

//messaging.php
"mes_no_msg_no_recip" => "Niet gestuurd, geen bestemming gevonden",

//explanations
"xpl_edit" =>
"<h3>Edit Instructions</h3>
<p>Deze tekst editor kan worden gevruikt om de inhoud van de volgende bestanden te bewerken:
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
"<h3>Bewerk instructies - Informatie Tekst</h3>
<p>Wanneer ingeschakeld op de instellingen pagina, zal de informatie in het 
tekstvenster (links) worden getoond in het zijpaneel aan de rechterzijde van de 
kalender paginas. Er kan gebruik worden gemaakt van HTML tags. 
Voorbeelden van de mogelijkheden in de informatie tekst staan in het bestand 
'sidepanel/samples/info.txt'.</p>
<p>Informatie kan getoond worden gedurende een bepaalde periode.
Ieder infobericht moet worden voorafgegaan door een regel met de gespecificeerde 
weergeefperiode, ingesloten door ~ tekens. Tekst voor de eerste regel met een ~ 
wordt niet weergegeven en kun je gebruiken voor aantekening en zal niet worden 
weergegeven.</p><br>
<p>Start en einddatum opmaak: ~m1.d1-m2.d2~, waar m1 en d1 de start maand en dag 
betekenen en m2 en d2 de eind maand en dag. Als d1 wordt weggelaten dan wordt de 
eerste dag van m1 bedoeld. Als d2 wordt weggelaten, dan wordt de laatste dag van 
m2 bedoeld. Als m2 en d2 worden weggelaten, dan wordt de laatste dag van m1 
bedoeld.</p>
<p>Voorbeelden:<br>
<b>~4~</b>: De hele maand april<br>
<b>~2.10-2.14~</b>: 10 - 14 februari<br>
<b>~6-7~</b>: 1 june - 31 juli<br>
<b>~12.15-12.25~</b>: 15 - 25 december<br>
<b>~8.15-10.5~</b>: 15 augustus - 5 oktober<br>
<b>~12.15~</b>: 15 december - 31 december</p><br>
<b>~6-4~</b>: 4 juni<br>
<p>Suggestie: Maak altijd eerst een backup (Backup tekst).</p>",

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
"<h3>Instructies voor het database beheer</h3>
<p>Op deze pagina kunnen de volgende functies worden geselecteerd:</p><br>
<h6>Comprimeer database</h6>
<p>Als een gebruiker een activiteit verwijdert, wordt deze als 'verwijderd' gemarkeerd, maar blijft die activiteit vooralsnog gewoon in de database aanwezig. De 'Comprimeer database' functie zal de 
activiteiten die meer dan 30 dagen geleden als 'verwijderd' zijn gemarkeerd, definitief uit de database verwijderen, waardoor deze ruimte weer vrij komt. BELANGRIJK: Wanneer de database wordt gecomprimeerd, kunnen de activiteiten die permanent worden verwijderd, later ook niet meer worden hersteld!</p><br>
<h6>Back-up database</h6>
<p>Deze functie maakt een back-up van de volledige kalender database (tabellen, structuur en inhoud) in het .sql formaat. De back-up zal worden opgeslagen in de <strong>files/</strong> map met de bestandsnaam: 
<kbd>dump-cal-lcv-yyyymmdd-hhmmss.sql</kbd> (waar 'cal' = kalender ID, 'lcv' = kalender versie en 'yyyymmdd-hhmmss' = jaar, maand, dag, uur, minuten en seconden).</p>
<p>Dit back-up bestand kan op enig moment worden gebruikt om de database tabelstructuur en inhoud opnieuw te genereren, bijvoorbeeld:<br>
-- via 'Herstel database' (zie hierna)<br>
-- of door het bestand te importeren in de <strong>phpMyAdmin</strong> applicatie, die op de server van de meeste hosting providers beschikbaar is.</p><br>
<h6>Herstel database</h6>
<p>Deze functie kan de tabellen, structuur en inhoud van de complete kalender database herstellen met behulp van een (eerder gemaakt) back-up bestand (bestandstype .sql). Als het .sql bestand groter is dan 2MB kan het nodig zijn de <b>upload_max_filesize</b> en <b>post_max_size</b> variabelen in het php.ini bestand te wijzigen, of het .sql bestand op te delen in meerdere kleinere bestanden. Zie de admin_guide.html hoofdstuk 3 voor een dedetaileerde uitleg.</p>
<p>Let op: Wanneer de database wordt hersteld, GAAN ALLE IN DE DATABASE TOT DAN TOE AANWEZIGE GEGEVENS VERLOREN!</p><br>
<h6>Activiteiten</h6>
<p>Deze funktie verwijdert/herstelt activiteiten die plaatsvinden binnen de opgegeven datums. Indien een datumveld leeg wordt gelaten, 
is er geen sprake van een datumlimiet; dus als beide datumvelden leeg worden gelaten, WORDEN ALLE ACTIVITEITEN VERWIJDERD!</p>",

"xpl_import_csv" =>
"<h3>Instructie: Importeer activiteiten (upload als CSV bestand)</h3>
<p>Dit formulier wordt gebruikt om <strong>Comma Separated Values (CSV)</strong> bestanden met activiteiten in de LuxCal kalender te importeren.</p>
<p>De volgorde van de kolommen in het CSV bestand moet zijn: titel, plaats, categorie id (zie hieronder), datum, einddatum, begintijd, eindtijd en 
omschrijving. Als de eerste rij van het CSV bestand een omschrijving van de 
kolommen bevat, zal deze worden genegeerd.</p>
<p>Voor een juiste interpretatie van speciale tekens, moet het CSV bestand UTF-8 gecodeerd zijn.</p><br>
<h6>Voorbeeld CSV bestanden</h6>
<p>Voorbeeld CSV bestanden kunt u vinden in de '!luxcal-toolbox/' map van de LuxCal 
download.</p><br>
<h6>Scheidingsteken voor de velden</h6>
Het scheidingsteken kan elk teken zijn, bijv. een komma, een puntkomma of een 
tab-teken (tab-teken: '\\t'). Het scheidingsteken moet uniek zijn en mag geen 
onderdeel uitmaken van de tekst, getallen of de datums in de velden.<br><br>
<h6>Datum- en tijdopmaak</h6>
<p>De geselecteerde datum- en tijdopmaak aan de linker zijde moet overeenstemmen 
met het datum- en tijdopmaak in het ge-uploade CSV bestand.</p><br>
<p>Indien geen begintijd aanwezig is, zal de activiteit zonder tijd worden weergegeven 
in de kalender. Indien de begintijd 00:00 of 12:00am is, zal de activiteit als een 
'hele dag' activiteit worden weergegeven in de kalender.</p>
<h6>Categorieënlijst</h6>
<p>De kalender kent ID nummers toe aan categorieën. De categorie ID's in het CSV 
bestand moeten overeenkomen met de categorieën welke in de kalender worden 
gebruikt of moeten 'leeg' zijn.</p>
<p>Als je in de volgende stap activiteiten wilt markeren als 'verjaardag', dan 
moet de <strong>ID verjaardag categorie</strong> worden gelijk gemaakt met de 
corresponderende ID in categorieënlijst hieronder.
<span class='hired'>Pas op: Importeer niet meer dan 100 activiteiten per keer!</span><br><br>
<p>Voor de kalender zijn op dit moment de volgende categorieën gedefinieerd:</p>",

"xpl_import_user" =>
"<h3>Instructie: Importeer gebruikers als CSV bestand</h3>
<p>Dit formulier wordt gebruikt om een CSV (Comma Separated Values) tekstbestand met gebruikersprofielen te importeren in de LuxCal kalender.</p>
<p>Voor de juiste afhandeling van speciale tekens moet het CSV-bestand UTF-8 gecodeerd zijn.</p>
<h6>Veldscheidingsteken</h6>
<p>Het veldscheidingsteken kan elk teken zijn, bijvoorbeeld een komma, puntkomma, etc.
Het veldscheidingsteken moet echter wel uniek zijn en mag verder niet voorkomen in de tekst van de te importeren velden.</p>
<h6>Standaard gebruikersgroep ID</h6>
<p>Als in het CSV-bestand een gebruikersgroep ID leeg is gelaten, zal standaard de opgegeven waarde als gebruikersgroep ID worden gebruikt.</p>
<h6>Standaard wachtwoord</h6>
<p>Als in het CSV-bestand een gebruikerswachtwoord leeg is gelaten, zal standaard de opgegeven waarde als gebruikerswachtwoord worden gebruikt.</p>
<h6>Vervang bestaande gebruikers</h6>
<p>Als het selectievakje bestaande gebruikers vervangen is aangevinkt, zullen alle bestaande gebruikers, behalve de openbare gebruiker en de beheerder, worden verwijderd voordat de nieuwe gebruikers worden geïmporteerd.</p>
<br>
<h6>Voorbeelden van bestanden met gebruikersprofielen</h6>
<p>Voorbeeld CSV-bestanden van gebruikersprofielen (.csv) zijn te vinden in de map '!luxcal-toolbox/' van uw LuxCal-installatie.</p><br>
<h6>Velden in het CSV-bestand</h6>
<p>De volgorde van de kolommen moet zijn zoals hieronder vermeld. Als de eerste rij van het CSV-bestand kolomkoppen bevat, worden deze genegeerd.</p>
<ul>
<li>Gebruikersgroep ID: moet overeenkomen met de gebruikersgroepen die in uw kalender worden gebruikt (zie tabel hieronder). Indien leeg, wordt de gebruiker in de gespecificeerde standaard gebruikersgroep geplaatst.</li>
<li>Gebruikersnaam: verplicht</li>
<li>E-mailadres: verplicht</li>
<li>Mobiel telefoonnummer: optioneel</li>
<li>Telegram chat ID: optioneel</li>
<li>Interfacetaal: optioneel. Bijv. Engels, Dansk. Indien leeg, zal standaard de taal die is geselecteerd op de pagina 'Instellingen' worden gebruikt.</li>
<li> Wachtwoord: optioneel. Indien leeg, wordt het opgegeven standaard wachtwoord gebruikt.</li>
</ul>
<p>Lege velden moeten worden aangegeven door twee aanhalingstekens. Lege velden aan het einde van elke rij, kunnen worden weggelaten.</p>
<p class='hired'>Waarschuwing: importeer niet meer dan 60 gebruikersprofielen tegelijk per keer!</p><br>
<h6>Tabel met gebruikersgroep ID's</h6>
<p>Voor uw kalender zijn momenteel de volgende gebruikersgroepen gedefinieerd:</p>",


"xpl_export_user" =>
"<h3>Instructie: Exporteer gebruikers als CSV bestand</h3>
<p>Dit formulier wordt gebruikt om <strong>gebruikersprofielen</strong> uit de kalender te extraheren en te exporteren naar een CSV bestand.</p>
<p>Het CVS bestand wordt aangemaakt in de map 'files/' op de server met de door u opgegeven bestandnaam met de extensie .csv (door komma's gescheiden waarden).</p><br>
<h6>Naamgeving van dit CSV bestand</h6>
Indien door u niet anders gespecificeerd, wordt de standaard bestandsnaam: de kalendernaam gevolgd door het achtervoegsel '_users'.<br>
De bestandsnaamextensie zal automatisch worden ingesteld op <b>.csv</b>.</p><br>
<h6>Gebruikersgroep</h6>
Alleen de gebruikersprofielen van de door u geselecteerde gebruikersgroep(en) worden geëxporteerd. Als 'alle groepen' is geselecteerd, worden de gebruikersprofielen in het doelbestand gesorteerd op de bijbehorende gebruikersgroep</p><br>
<h6>Veldscheidingsteken</h6>
<p>Het veldscheidingsteken kan elk teken zijn, bijvoorbeeld een komma, puntkomma, etc. Het veldscheidingsteken moet echter wel uniek zijn en mag verder niet voorkomen in de tekst van de te importeren velden.</p><br>
<p>Een reeds aanwezig CSV bestand in de map 'bestanden/' op de server met dezelfde naam, zal worden overschreven door het nieuwe CSV bestand.</p>
<p>De volgorde van de kolommen in het CSV bestemmingsbestand is: groeps-ID, gebruikersnaam, e-mailadres, gsm-nummer, interfacetaal en wachtwoord.<br>
<b>Opmerking:</b> wachtwoorden in de geëxporteerde gebruikersprofielen zijn gecodeerd en kunnen niet worden gedecodeerd.</p><br>
<p>Bij het <b>downloaden</b> van het geëxporteerde .csv-bestand, zullen de huidige datum en tijd worden toegevoegd aan de naam van het gedownloade bestand.</p><br>
<h6>Voorbeelden van gebruikersprofielbestanden</h6>
<p>Voorbeelden van gebruikersprofielbestanden (bestandsextensie .csv) zijn te vinden in de 'files /'
directory van uw LuxCal-download.</p>",

"xpl_import_ical" =>
"<h3>Instructie: Importeer iCalendar activiteiten</h3>
<p>Dit formulier wordt gebruikt om <strong>iCalendar</strong> activiteiten in de kalender te importeren.</p>
<p>De inhoud van het iCal bestand moet voldoen aan de [<u><a href='https://tools.ietf.org/html/rfc5545' 
target='_blank'>RFC5545 standaard</a></u>] van de IETF (Internet Engineering Task Force).</p>
<p>Alleen iCalendar activiteiten zullen worden geïmporteerd; andere iCal onderdelen, zoals: To-Do, Journal, Free / Busy en Alarm, worden genegeerd en derhalve niet geïmporteerd.</p><br>
<h6>Voorbeeld iCal bestanden</h6>
<p>Voorbeelden van iCal bestanden (bestandstype .ics) kunnen in de '!luxcal-toolbox/' map van de LuxCal download worden gevonden.</p><br>
<h6>Tijdzone aanpassingen</h6>
<p>Als het iCal bestand activiteiten uit een andere tijdzone bevat en de data/tijden moeten worden aangepast aan de tijdzone van de kalender, selecteer dan 'Tijdzone aanpassingen'.</p><br>
<h6>Categorieënlijst</h6>
<p>De kalender kent ID nummers toe aan categorieën. De categorie ID's in het iCal bestand moeten daarom overeenkomen met de categorieën die in de kalender worden gebruikt of moeten 'leeg' zijn. <span class='hired'>Pas op: Importeer niet meer dan 100 activiteiten tegelijk per keer!</span>
<p>Voor de kalender zijn op dit moment de volgende categorieën gedefinieerd:</p>",

"xpl_export_ical" =>
"<h3>Instructie: Exporteer activiteiten naar iCalendar formaat</h3>
<p>Dit formulier wordt gebruikt om kalender activiteiten te exporteren naar een <strong>iCalendar</strong> bestand.</p><br>
<p>De <b>iCal bestandsnaam</b> (zonder type) is optioneel. Geëxporteerde bestanden zullen worden opgeslagen in de \"files/\" map op de server met de opgegeven bestandsnaam, of anders met de naam van de kalender. Het bestandstype 
is <b>.ics</b>. Bestaande bestanden in de \"files/\" map op de server met dezelfde naam, zullen worden overschreven door het nieuwe iCal bestand.</p><br>
<p>Een <b>Beschrijving iCal bestand</b> (bijv. 'Vergaderingen 2024') is optioneel. Indien ingevuld zal de beschrijving worden toegevoegd aan de 'header' van het geëxporteerde 
iCal bestand.</p>
<p><b>Activiteitenfilters</b>: De te exporteren activiteiten kunnen worden gefilterd op:</p>
<ul>
<li>eigenaar van de activiteit</li>
<li>categorie van de activiteit</li>
<li>begindatum van de categorie</li>
<li>datum activiteit toegevoegd/laatst gewijzigd</li>
</ul>
<p>Elk filter is optioneel.<br>
• Een leeg 'plaatsvindend tussen' datumvelden = respectievelijk -1 jaar en +1 jaar.<br> 
• Een leeg 'toegevoegd/gewijzigd' datumveld = geen begrenzing.</p><br>
<p>De inhoud van het iCal bestand met geëxporteerde activiteiten voldoet aan de [<u><a href='https://tools.ietf.org/html/rfc5545' target='_blank'>RFC5545 standaard</a></u>] 
van de IETF (Internet Engineering Task Force).</p>
<p>Wanneer het geëxporteerde iCal bestand wordt <b>gedownload</b>, zullen de datum en tijd worden toegevoegd aan de naam van het gedownloade iCal bestand.</p><br>
<h6>Voorbeeld iCal bestanden</h6>
<p><p>Voorbeelden van iCal bestanden (bestandstype .ics) kunt u vinden in de '!luxcal-toolbox/' map van de LuxCal download.</p>",

"xpl_clean_up" =>
"<h3>Opruimen Instructies</h3>
<p>Op deze pagina kan het volgende worden opgeruimd:</p>
<h6>Gebeurtenis in het verleden</h6>
<p>Gebeurtenissen met een einddatum voor de opgegeven datum worden verwijderd uit de kalender. De ingevoerde datum moet minstens een maand voor de datum van vandaag zijn.</p>
<h6>Inactieve Gebruikers</h6>
<p>De accounts van gebruikers worden verwijderd als ze de kalender niet hebben gebruikt na de ingevoerde datum. De ingevoerde datum moet minstens een maand voor de datum van vandaag zijn.</p>
<h6>Attachments map</h6>
<p>Bijlagen bij gebeurtenissen welke niet worden gebruikt na de opgegeven datum worden gewist in de attachments map. De datum moet leeg zijn of in het verleden liggen. Als er meerdere kalenders in gebruik zijn, gebeurt dit bij alle kalenders.</p>
<h6>Recipients map</h6>
<p>De lijsten met geadresseerden welke niet worden gebruikt na de opgegeven datum worden gewist in de recipients map. De datum moet leeg zijn of in het verleden liggen. Als er meerdere kalenders in gebruik zijn, gebeurt dit bij alle kalenders.</p>
<h6>Thumbnails map</h6>
<p>Miniaturen die niet worden gebruikt sinds de opgegeven datum en niet in gebruik zijn het info.txt bestand van het zijpaneel worden gewist in de thumbnails map. De datum moet leeg zijn of in het verleden liggen. Als er meerdere kalenders in gebruik zijn, gebeurt dit bij alle kalenders</p>"
);
?>
