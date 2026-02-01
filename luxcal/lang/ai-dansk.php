<?php
/*
= LuxCal admin interface language file =

This file has been produced by LuxSoft. Please send comments / improvements to rb@luxsoft.eu.
Additional Danish - John Schwartz. Sidst redigeret 21-12-2024

This file is part of the LuxCal Web Calendar.
*/

$ax = array(

//general
"none" => "Ingen",
"no" => "nej",
"yes" => "ja",
"own" => "egne",
"all" => "alle",
"or" => "eller",
"back" => "Tilbage",
"ahead" => "Frem",
"close" => "Luk",
"always" => "altid",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"times" => "times",
"cat_seq_nr" => "category sequence nr",
"rows" => "rækker",
"columns" => "kolonner",
"hours" => "hours",
"minutes" => "minutter",
"user_group" => "ejer farve",
"event_cat" => "kategori farve",
"email" => "Email",
"telegram" => "Telegram",
"sms" => "SMS",
"id" => "ID",
"username" => "Brugernavn",
"password" => "Password",
"public" => "Public",
"logged_in" => "Logget ind",
"pw_no_chars" => "Karaktererne <, > og ~ er ikke tilladte i password-et",

//settings.php - fieldset headers + general
"set_general_settings" => "Kalenderindstillinger",
"set_navbar_settings" => "Navigationsbjælke",
"set_event_settings" => "Begivenheder",
"set_user_settings" => "Brugerindstillinger",
"set_upload_settings" => "File Uploads",
"set_reminder_settings" => "Reminders",
"set_perfun_settings" => "Periodiske Funktioner (kun relevant hvis cron job er konfigureret)",
"set_sidebar_settings" => "Fritstående Sidebjælke (kun relevant hvis den bruges)",
"set_view_settings" => "Visningsindstilinger",
"set_dt_settings" => "Dato/tid indstilinger",
"set_save_settings" => "Gem indstilinger",
"set_test_mail" => "Test Mail",
"set_mail_sent_to" => "Test mail sendt til",
"set_mail_sent_from" => "Denne testmail var sendt fra din kalender",
"set_mail_failed" => "Send testmail mislykkedes - Modtager",
"set_missing_invalid" => "manglende eller ugyldige indstillinger (baggrund farvemarkeret)",
"set_settings_saved" => "Kalenderindstilingerer gemt",
"set_save_error" => "Databasefejl - Gem kalender indstillinger mislykkedes",
"hover_for_details" => "Hold musemarkør over beskrivelser for detaljer",
"default" => "standard",
"enabled" => "aktiveret",
"disabled" => "deaktiveret",
"pixels" => "pixels",
"warnings" => "Advarsler",
"notices" => "Notices",
"visitors" => "Gæster",
"height" => "Height",
"no_way" => "Du har ikke rettigheder til at udføre denne funktion",

//settings.php - general settings.
"versions_label" => "Versions",
"versions_text" => "• kalender version, fulgt af anvendt database version<br>• PHP version<br>• database version",
"calTitle_label" => "Kalendertitel",
"calTitle_text" => "Vises i kalenderens topbjælke og bruges ved beskeder.",
"calUrl_label" => "Kalender URL",
"calUrl_text" => "Kalenderens webside-adresse",
"calEmail_label" => "Kalender email-adresse",
"calEmail_text" => "E-mail adressen brugt til at modtage kontakt-beskeder or til at sende eller modtage notifikations emails.<br>Format: 'email' eller 'navn &#8826;email&#8827;'.",
"logoPath_label" => "Sti/navn til LOGO billede",
"logoPath_text" => "Hvis angivet, vil et LOGO billede blive vist i øvre venstre hjørne af kalenderen. Hvis der også er angivet et link til parent page - overordnet side ( se herunder ), vil LOGO billedet blive et link til parent siden. LOGO billedet vil/skal have en max-størrelse på 70 x 70 px.",
"logoXlPath_label" => "Sti/navn til log-in logo billede",
"logoXlPath_text" => "Hvis angivet, vil et logo-billede med den angivne højde blive vist på log-in siden under log-in formen.",
"backLinkUrl_label" => "Link til overordnet side",
"backLinkUrl_text" => "URL for den overordnede side. Hvis angivet, vil en Tilbage-knap blive vist i venstre side af Navigationsbjælken, som linker til denne URL.<br>Fx for at linke tilbage til den overordnede hjemmeside hvorfra kalenderen blev åbnet. If a logo path/name has been specified (see above), then no Back button will be displayed, but the logo will become the back link instead.",
"timeZone_label" => "Tidszone",
"timeZone_text" => "Kalenderens tidszone, bruges til at beregne tidspunktet.",
"see" => "se",
"notifChange_label" => "Send notification af kalender ændringer",
"notifChange_text" => "Hvis en bruger tilføjer, editerer eller sletter en event, vil en besked blive sent til den angivne modtager.",
"chgRecipList" => "semicolon separated recipient list",
"maxXsWidth_label" => "Max. bredde ved brug af mindre skærme",
"maxXsWidth_text" => "For skærme med en bredde mindre end det angivne antal pixels, vil kalenderen køre i en speciel responsive mode, som udelader visse mindre vigtige elementer.",
"rssFeed_label" => "RSS feed links",
"rssFeed_text" => "Hvis aktiveret: For brugere med mindst 'vise' rettigheder, vil et RSS feed link blive vist i bunden af kalenderen, og et RSS feed link vil blive tilføjet HTML header på kalendersider.",
"logging_label" => "Log kalender data",
"logging_text" => "Kalenderen kan logge error, warning og notice messages og visitors data. Error messages bliver altid logged. Logging af warning og notice messages og visitors data kan disables eller enables ved at checke de relevante tekstbokse. Alle error, warning og notice messages bliver logget i filen 'logs/luxcal.log' og visitors data are logged in the files 'logs/hitlog.log' and 'logs/botlog.log'.<br>Note: PHP error, warning and notice messages bliver logget på en anden location, bestemt af din ISP.",
"maintMode_label" => "PHP Maintenance mode",
"maintMode_text" => "Hvis angivet, vil der i PHP scripts, data angivet via the note (message) funktionen og data stored i 'note' variable vedr. vedligehold blive vist i kalenderens fod bjælke.",
"reciplist" => "Modtager listen kan indeholde brugernavne, email adresser, mobilnumre og navne, Telegram chat IDs på filer indeholdende modtagere (omgivet af square brackets), adskilt af semicolons. Filer med modtagere med een modtager per linie skal være placeret i folderen 'reciplists'. Hvis udeladt bliver file extension sat til .txt",
"calendar" => "kalender",
"user" => "bruger",
"database" => "database",

//settings.php - navigation bar settings.
"contact_label" => "Kontakt knap",
"contact_text" => "Hvis aktiveret : En kontakt-knap vil blive vist i side-menuen. Ved klik på knappen, vil en kontakt-form blive vist. Formularen kan bruges til at sende en besked til kalender administratoren.",
"optionsPanel_label" => "Options panel menuer",
"optionsPanel_text" => "Aktiver/deaktiver menuer i Valg panelet.<br>• Kalendermenuen gør det muligt for admin at skifte kalendere. (enabling er kun relevant hvis flere kalendere er installeret)<br>• Visningsmenuen kan bruges til at vælge een af de mulige kalender visninger.<br>• Gruppemenuen kan anvendes til at vise, kun de brugere der tilhører den/de valgte gruppe(r).<br>• Menuen Brugere kan bruges til kun at vise begivenheder oprettet af den/de angivne brugere.<br>• Menuen Kategorier kan bruges til kun at vise begivenheder i den/de angivne kategorier.<br>• Menuen Sprog kan bruges til at vælge det ønskede sprog (kun relevant hvis der er installeret flere sprog).<br>Note: Hvis ingen menuer er valgt, vil option panel knappen blive valgt.",
"calMenu_label" => "Kalender",
"viewMenu_label" => "Visning",
"groupMenu_label" => "Grupper",
"userMenu_label" => "Bruger",
"catMenu_label" => "Kategori",
"langMenu_label" => "Sprog",
"availViews_label" => "Tilgængelige kalender visninger",
"availViews_text" => "Tilgængelige kalender visninger public og logged-in brugere specificeret ved hjælp af en komma-separeret liste med visnings numre. Betydning af numrene:<br>1: år view<br>2: måned view (7 dage)<br>3: arbejdsmåned view<br>4: uge view (7 dage)<br>5: arbejdsuge view<br>6: dag view<br>7: kommende begivenheder view<br>8: ændringer view<br>9: matrix view (kategorier)<br>10: matrix view (brugere)<br>11: gantt chart view",
"viewButtonsL_label" => "View knapper på navigations bjælken (stor skærm)",
"viewButtonsS_label" => "View knapper på navigations bjælken (lille skærm)",
"viewButtons_text" => "View knapper på navigations bjælken for public og logged-in brugere, specificeret ved hjælp af en komma-separeret liste med visnings numre.<br>Hvis et nummer er specificeret vil den pågældende knap blive vist. Hvis ingen numre er angivet vil ingen knapper blive vist.<br>Brtydning af numrene:<br>1: År<br>2: Fuld måned<br>3: Arbejdsmåned<br>4: Fuld uge<br>5: Arbejds uge<br>6: Dag<br>7: Kommende<br>8: Ændringer<br>9: Matrix-C<br>10: Matrix-U<br>11: Gantt Chart<br>Rækkefølgen på numrene afgør i hvilken rækkefølge knapperne vises.<br>For eksempel: '2,4' betyder: vis 'Fuld måned' og 'Fuld uge' knapper.",
"defaultViewL_label" => "Standardvisning ved start (stor skærm)",
"defaultViewL_text" => "Default Kalendar visning ved opstart for public og logged-in Brugere using large displays.<br>Anbefalet valg: Måned.",
"defaultViewS_label" => "Standardvisning ved start (lille skærm)",
"defaultViewS_text" => "Default Kalendar visning ved opstart for public og logged-in Brugere using small displays.<br>Anbefalet valg: Kommende.",
"language_label" => "Standard brugerinterface-sprog (public user)",
"language_text" => "For public (Ikke logget ind) vil kalenderens sprog blive sat til samme sprog som browserens. Hvis browserens sprog ikke er et sprog benyttet af kalenderen, vil default sproget blive benyttet. <br>Note: Filerne ui-{sprog}.php, ai-{sprog}.php, ug-{sprog}.php og ug-layout.png skal findes i lang/ folderen. {sprog} = det valgte sprog til brugerinterfacet. Filnavne skal skrives med små bogstaver!",
"birthday_cal_label" => "PDF Fødselsdag kalender",
"birthday_cal_text" => "Hvis angivet, vil en linie/mulighed 'PDF File - Fødselsdag' blive vist i side menuen for brugere med mindst 'view' rettigheder. Se admin_guide.html - Fødselsdag kalender for yderligere oplysninger",
"sideLists_label" => "Approve, Todo, Upcoming lists",
"sideLists_text" => "Hvis angivet vil en mulighed for at vise de enkelte lister komme til syne i side-menuen. Listen 'Events to be approved' vil kun blive vist for brugere med mindst 'manager' rettigheder.",
"toapList_label" => "To approve list",
"todoList_label" => "To do list",
"upcoList_label" => "Upcoming list",

//settings.php - events settings.
"privEvents_label" => "Oprettelse af private begivenheder",
"privEvents_text" => "Private begivenheder er kun synlige for den bruger som har oprettet begivenheden.<br>Deaktiveret: brugere kan ikke oprette private begivenheder. 'Privat' markeringsfeltet vil ikke blive vist i begivenhedsvinduet.<br>Aktiveret: brugere kan oprette private begivenheder ved at sætte markeringen 'Privat'.<br>Standard: når nye begivenheder tilføjes, sættes markeringen 'Privat' automatisk, og brugeren kan ændre markeringen.<br>Altid: når nye begivenheder tilføjes vil de altid være private, og 'Privat' markeringsfeltet vil ikke blive vist i begivenhedsvinduet.",
"venueInput_label" => "Specifying venues",
"venueInput_text" => "Et venue kan angives enten ved at indtaste, eller vælge fra en præ-defineret liste. Hvis fri-tekst er valgt kan brugeren indtaste venue, hvis liste er valgt, kan brugeren vælge fra en drop-down liste, og hvis begge er valgt, kan brugeren selv vælge mellem de to. <br> Hvis drop-down listen er anvendt skal 'files' folderen indeholde en fil kaldt venues.txt med et venue per linie.",
"timeDefault_label" => "Tilføjelse af nye events - time default",
"timeDefault_text" => "Ved tilføjelse af events i eventvinduet, vil event tids felterne blive sat således:<br>• show times: Start og end tidsfelterne er vist og klar til at blive udfyldt<br>• all day: All Day check boxen er checked, ingen  start- og sluttider er vist<br>• no time: No Time check boxen er checked, ingen start- og sluttider er vist.",
"evtDelButton_label" => "Vis sletteknap i begivenhedsvindue",
"evtDelButton_text" => "Deaktiveret: knappen Slet vil ikke være synlig i begivenhedsvinduet. Brugere med editeringsrettigheder vil ikke kunne slette begivenheder.<br>Aktiveret: knappen Slet vil være synlig i begivenhedsvinduet for alle brugere.<br>Manager: knappen Slet vil kun være synlig for brugere med i det mindste 'manager' rettigheder.",
"eventColor_label" => "Begivenhedsfarver baseres på",
"eventColor_text" => "Begivenheder i de forskellige kalendervisninger kan vises i farven som er tildelt brugeren som oprettede begivenheden eller farven for begivenhedskategorien.",
"defVenue_label" => "Default Venue",
"defVenue_text" => "I dette tekst felt, kan venue være specificeret hvilket vil medføre at indholdet vil blive kopieret til venue feltet i event formularen når der tilføjes nye events.",
"xField1_label" => "Ekstra felt 1",
"xField2_label" => "Ekstra felt 2",
"xFieldx_text" => "Valgfrit tekstfelt. Hvis det sættes således op, vil feltet blive vist i diverse visninger.<br>• label: Valgfri text label for det extra felt (max. 15 characters). E.g. 'Email address', 'Website', 'Phone number'<br>• Minimum user rights: Feltet vil kun være synlig for brugere med den angivne brugerrettighed eller højere.",
"evtWinSmall_label" => "Minimeret event vindue",
"evtWinSmall_text" => "Ved tilføj/editer event, vil vinduet vise et reduceret antal felter. For at få vist alle felter, kan der klikkes på pil.",
"emojiPicker_label" => "Emoji picker i Event vinduet",
"emojiPicker_text" => "Hvis angivet vil en emoji picker blive vist som man kan vælge en emoji fra, til brug i titlen eller et af tekstfelterne.",
"mapViewer_label" => "Map viewer URL",
"mapViewer_text" => "Hvis en map viewer URL er angivet, vil en adresse i event's venue feltet omgivet af !-tegn (udråbstegn), blive vist som en adresse knap/button i kalender visningen. Ved hovering denne knap/button vil adressen blive vist som tekst,og ved klik vil et nyt vinduw åbnes hvor adressen vil blive vist på et kort.<br>Den fulde URL til en map viewer skal specificeres, hvor der i enden kan tilføjes adressen.<br>Eksempler:<br>Google Maps: https://maps.google.com/maps?q=<br>OpenStreetMap: https://www.openstreetmap.org/search?query=<br>Hvis dette felt er blankt, vil adressen i Venue feltet ikke blive vist som en adresse knap/button.",
"evtDrAndDr_label" => "Event drag and drop",
"evtDrAndDr_text" => "Hvis angivet kan der i Year view, Month view og i mini calendaren i side-panelet, Flyttes eller kopieres events fra en dag til en anden, ved at anvende Drag and Drop. Hvis 'manager' er valgt, kan kun brugere med mindst manager rights bruge denne mulighed. Se admin_guide.html for en detaljeret beskrivelse.",
"free_text" => "Free text",
"venue_list" => "Venue list",
"both" => "Begge",
"xField_label" => " Overskrift",
"show_times" => "Vis tidspunkter",
"check_ald" => "all day",
"check_ntm" => "no time",
"min_rights" => "Minimum user rights",
"no_color" => 'ingen farve',
"manager_only" => 'manager',

//settings.php - user accounts settings.
"selfReg_label" => "Selvregistrering",
"selfReg_text" => "Tillad brugere at registrere sig selv for at få adgang til kalenderen.<br>Brugergruppe for hvilken selv-registrerede brugere vil blive tilknyttet.",
"selfRegQA_label" => "selv registrering spørgsmål/svar",
"selfRegQA_text" => "Hvis selvregistrering er enabled/sat til tilladt, vil brugeren i selvregistreringsprocessen blive stillet dette spørgsmål og vil kun blive tilladt registrering hvis der angives korrekt svar. Hvis feltet forbliver blankt/tomt vil der ikke blive stillet noget spørgsmål.",
"selfRegNot_label" => "Selvregistrering advisering",
"selfRegNot_text" => "Send en advisering email til kalender email addressen når en selvregistrering foretages.",
"restLastSel_label" => "Gen-etabler seneste brugersession",
"restLastSel_text" => "Den seneste brugersession (Valgmuligheders indstillinger) bliver gemt, og når brugeren senere vender tilbage til kalenderen, vil værdierne blive anvendt igen. If the user does not log in during the specified number of days, the values will be lost.",
"answer" => "svar",
"exp_days" => "days",
"view" => "vis",
"post_own" => 'opret/editer egne',
"post_all" => 'opret/editer alle',
"manager" => 'opret/manager',

//settings.php - view settings.
"templFields_text" => "Numrenes betydning:<br>1: Venue(sted)field<br>2: Event kategori felt<br>3: Beskrivelse felt<br>4: Ekstra felt 1 (se nedenunder)<br>5: Ekstra felt 2 (se nedenunder)<br>6: Email notification data (kun hvis en advisering er angivet)<br>7: Date/time added/edited og de(n) tilhørende bruger(e)<br>8: Attached pdf, image eller video files som hyperlinks.<br>Numrenes rækkefølge afgør visningsrækkefølgen.",
"evtTemplate_label" => "Begivenhed skabeloner",
"evtTemplate_text" => "Felter der skal vises i diverse kalendervisninger.<br>Hvis et nummer er medtaget, vil det tilhørende felt blive vist.",
"evtTemplPublic" => "Public users",
"evtTemplLogged" => "Logged-in users",
"evtTemplGen" => "General view",
"evtTemplUpc" => "Upcoming view",
"evtTemplPop" => "Pop-up boks",
"sortEvents_label" => "Sorter events efter tidspunkt eller kategori",
"sortEvents_text" => "I de forskellige visninger kan events sorteres efter følgende kriterier:<br>• event tider<br>• event kategori sekvens nummer",
"yearStart_label" => "Startmåned i års-visning",
"yearStart_text" => "Hvis en startmåned er angivet (1 - 12), vil års-visning af kalenderen altid starte med denne måned, og året for denne første måned vil først skifte ved den første dag i den samme måned i det næste år.<br>Værdien 0 har en speciel betydning: startmåneden er baseret på den aktuelle dato og vil falde i den første række af måneder.",
"YvRowsColumns_label" => "Rækker og kolonner der vises i års-visning",
"YvRowsColumns_text" => "Antal rækker af måneder der vises i års-visningen.<br>Anbefalet valg: 4, hvilket giver 12 eller 16 måneder, at scrolle igennem med de anbefalede værdier for Kolonner.<br>Antal måneder der skal vises i hver række i års-visning.<br>Anbefalet valg: 3 eller 4.",
"MvWeeksToShow_label" => "Uger der vises i måneds-visning",
"MvWeeksToShow_text" => "Antal uger der vises i månedsvisning.<br>Anbefalet valg: 10, hvilket giver 2,5 måned at scrolle igennem.<br>Værdierne 0 og 1 har en speciel betydning:<br>0: vis præcis 1 måned - blank forudgående og efterfølgende dage.<br>1: vis præcis 1 måned - vis begivenheder på forudgående og efterfølgende dage.",
"XvWeeksToShow_label" => "Ugeantal der vises i Matrix view",
"XvWeeksToShow_text" => "Antal kalenderuger der skal vises i Matrix view.",
"GvWeeksToShow_label" => "Ugeantal der vises i Gantt chart view",
"GvWeeksToShow_text" => "Antal kalenderuger der skal vises i Gantt Chart view.",
"workWeekDays_label" => "Dage i arbejdsuge",
"workWeekDays_text" => "Dage markeret/farvet som working days/arbejdsdage i kalender visninger og for eksempel vist som uger i arbejdsmåned i arbejdsugevisning og arbejdsmånedvisning.<br>Angiv nummeret på hver enkelt arbejdsdag.<br>ex. 12345: Mandag - Fredag<br>Ikke angivne dage betragtes som weekend dage.",
"weekStart_label" => "Ugens første dag",
"weekStart_text" => "Angiv den første dag i ugen.",
"lookBackAhead_label" => "Dage der skal ses tilbage/fremad",
"lookBackAhead_text" => "Antal dage der skal ses tilbage i Opgavelisten og fremad i visningen Kommende begivenheder, Opgavelisten og RSS feeds.",
"searchBackAhead_label" => "Default antal dage der søges frem/tilbage",
"searchBackAhead_text" => "Hvis der ikke angives datoer i søgeformularen, er dette det antal dage der bruges som default for søgning frem/tilbage.",
"dwStartEndHour_label" => "Starttime og sluttime i dag-/ugevisning",
"dwStartEndHour_text" => "Tidspunkt hvor en normal dags begivenheder starter/slutter.<br>Hvis denne værdi f.eks. sættes til 6 -18, undgår man at spilde plads i dag-/ugevisning til de stille timer mellem midnat og 6.00 / 18.00 og midmat.<br>Tidsvælgeren, som bruges til at vælge et tidspunkt, vil også starte ved denne time.",
"dwTimeSlot_label" => "Tidsintervaller i dag-/ugevisning",
"dwTimeSlot_text" => "Dag-/ugevisning tidsinterval i antal minutter og højden.<br>Denne værdi vil sammen med Starttime og Sluttime (se ovenfor) afgøre antallet af rækker i dag/-ugevisning.",
"dwTsInterval" => "Tidsinterval",
"dwTsHeight" => "Højden",
"evtHeadX_label" => "Event skabelon i Måneds, uge og dag visning",
"evtHeadX_text" => "Skabelon med pladsholder der angiver hvilke event-felter der skal vises . Følgende pladsholdere kan bruges:<br>#ts - start tidspunkt<br>#tx - start og slut tidspunkt<br>#e - event titel<br>#o - event ejer/owner<br>#v - Sted<br>#lv - sted med ledetekst 'Sted:' foran<br>#c - Kategori<br>#lc - Kategori med ledetekst 'Kategori:' foran<br>#a - alder (se note nedenfor)<br>#x1 - Ekstra felt 1<br>#lx1 - Ekstra felt 1 med ledetekst fra Settings-siden foran<br>#x2 - Ekstra felt 2<br>#lx2 - Ekstra felt 2 med ledetekst fra Settings-siden foran<br>#/ - Ny linie<br>Felterne vises i angivet orden. Andre karakterer end pladsholderne vil vises som de er og vil være del af den viste event.<br>HTML-tags er tilladte i skabelonen. Eksempelvis &lt;b&gt;#e&lt;/b&gt;.<br> | Karakteren kan bruges til at opsplitte i sektioner. Hvis der indenfor en sektion med alle #-parametre vil blive en tom streng, vil hele sektionen blive udeladt.<br>Note: Alderen bliver vist hvis der på en event er benyttet en kategori med  'Repeat' set to 'every year' og årstallet for fødslen er angivet i paranteser. Fødselsåret i parantes kan angives hvorsomhelst i eventbeskrivelsen or in one of the extra texts.",
"monthView" => "Måneds visning",
"wkdayView" => "Uge/Dag visning",
"ownerTitle_label" => "Vis event owner foran event titlen",
"ownerTitle_text" => "I diverse kalender visninger, vis event owner navnet foran event titlen.",
"showSpanel_label" => "Side panel i calender views",
"showSpanel_text" => "I kalender views vil der til højre i hoved-kalenderen blive vist et side-panel hvor følgende muligheder kan vises:<br>• en mini kalender som kan bruges til at kigge tilbage eller frem, uden at ændre datoen for hovedkalenderen<br>• Et månedsbillede der automatisk skifter efter hovedkalenderens måned<br>• Et info-areal der kan bruges til at poste beskeder/annonceringer i bestemte perioder.<br>For hvert emne kan en komma-separeret liste angive hvilke numre/views der skal vises i side-panelet.<br>Mulige view numre:<br>0: all views<br>1: år view<br>2: måned view (7 dage)<br>3: arbejdsmåned view<br>4: uge view (7 dage)<br>5: arbejdsuge view<br>6: dag view<br>7: kommende begivenheder view<br>8: ændringer view<br>9: matrix view (kategorier)<br>10: matrix view (brugere)<br>11: gantt chart view.<br>If 'Today' is checked, the side panel will always use the date of today, otherwise it will follow the date selected for the main calendar.<br>Se admin_guide.html for Side Panel detaljer.",
"spMiniCal" => "Mini kalender",
"spImages" => "Billeder",
"spInfoArea" => "Info område",
"spToday" => "Today",
"topBarDate_label" => "Vis aktuel dato i topbjælken",
"topBarDate_text" => "Enable/disable visningen af aktuel dato i kalenderens top-bar i kalender views. Hvis vist, kan datoen klikkes og kalenderen sættes til aktuel dato.",
"showImgInMV_label" => "Vis i månedsvisning",
"showImgInMV_text" => "Enabled/disable visning i måneds-visning af billeder tilføjet til et af event beskrivelses felterne. Hvis enabled, thumbnails vil blive vist i dag-cellerne og hvis disabled, thumbnails vil blive vist i on-mouse-over boxes i stedet for.",
"urls" => "URL links",
"emails" => "email links",
"monthInDCell_label" => "Måned i hvert dagfelt",
"monthInDCell_text" => "3-bogstavs månedsnavn vises i hvert dagfelt i månedsvisning.",
"scrollDCell_label" => "Brug scrollbar i dag-celler",
"scrollDCell_text" => "Hvis en dag-celle i månedsvisning bliver for lille så vil der i stedet for at cellen bliver for høj, vises en scrollbar.",

//settings.php - date/time settings.
"dateFormat_label" => "Begivenhedsdatoformat (dd mm yyyy)",
"dateFormat_text" => "Tekststreng som definerer formatet for begivenhedsdatoer i kalendervisningerne og indtastningsfelter.<br>Mulige tegn: y = år, m = måned og d = dag.<br>Ikke-alfanumeriske tegn kan bruges som skilletegn, og vil blive kopieret tegn for tegn.<br>Eksempler:<br>y-m-d: 2024-10-31<br>m.d.y: 10.31.2024<br>d/m/y: 31/10/2024",
"dateFormat_expl" => "fx y.m.d: 2024.10.31",
"MdFormat_label" => "Datoformat (dd måned)",
"MdFormat_text" => "Tekststreng som definerer formatet for datoer som består af måned og dag.<br>Mulige tegn: M = måned i tekst, d = dato i tal.<br>Ikke-alfanumeriske tegn kan bruges som skilletegn, og vil blive kopieret tegn for tegn.<br>Eksempler:<br>d M: 12 April<br>M, d: Juli, 14",
"MdFormat_expl" => "fx M, d: Juli, 14",
"MdyFormat_label" => "Datoformat (dd måned yyyy)",
"MdyFormat_text" => "Tekststreng som definerer formatet for datoer som består af dag, måned og år.<br>Mulige tegn: d = dag i tal, M = måned i tekst, y = år i tal.<br>Ikke-alfanumeriske tegn kan bruges som skilletegn, og vil blive kopieret tegn for tegn.<br>Eksempler:<br>d M y: 12 April 2024<br>M d, y: Juli 8, 2024",
"MdyFormat_expl" => "fx M d, y: Juli 8, 2024",
"MyFormat_label" => "Datoformat (måned yyyy)",
"MyFormat_text" => "Tekststreng som definerer formatet for datoer som består af måned og år.<br>Mulige tegn: M = måned i tekst, y = år i tal.<br>Ikke-alfanumeriske tegn kan bruges som skilletegn, og vil blive kopieret tegn for tegn.<br>Eksempler:<br>M y: April 2024<br>y - M: 2024 - Juli",
"MyFormat_expl" => "fx M y: April 2024",
"DMdFormat_label" => "Datoformat (ugedag dd måned)",
"DMdFormat_text" => "Tekststreng som definerer formatet for datoer som består af ugedag, dag og måned.<br>Mulige tegn: WD = ugedag i tekst, M = måned i tekst, d = dag i tal.<br>Ikke-alfanumeriske tegn kan bruges som skilletegn, og vil blive kopieret tegn for tegn.<br>Eksempler:<br>WD d M: Fredag 12 April<br>WD, M d: Mandag, Juli 14",
"DMdFormat_expl" => "fx WD - M d: Søndag - April 6",
"DMdyFormat_label" => "Datoformat (ugedag dd måned yyyy)",
"DMdyFormat_text" => "Tekststreng som definerer formatet for datoer som består af ugedag, dag, måned og år.<br>Mulige tegn: WD = ugedag i tekst, M = måned i tekst, d = dag i tal, y = år i tal.<br>Ikke-alfanumeriske tegn kan bruges som skilletegn, og vil blive kopieret tegn for tegn.<br>Eksempler:<br>WD d M y: Fredag 13 April 2024<br>WD - M d, y: Mandag - Juli 16, 2024",
"DMdyFormat_expl" => "fx WD, M d, y: Mandag, Juli 16, 2024",
"timeFormat_label" => "Tidsformat (hh mm)",
"timeFormat_text" => "Tekststreng som definerer formatet for begivenhedstider i kalendervisningerne og indtastningsfelter.<br>Mulige tegn: h = timer, H = timer med foranstillede nuller, m = minutter, a = am/pm (valgfrit), A = AM/PM (valgfrit).<br>Ikke-alfanumeriske tegn kan bruges som skilletegn, og vil blive kopieret tegn for tegn.<br>Eksempler:<br>h:m: 18:35<br>h.m a: 6.35 pm<br>H:mA: 06:35PM",
"timeFormat_expl" => "fx h:m: 22:35 og h:mA: 10:35PM",
"weekNumber_label" => "Vis ugenumre",
"weekNumber_text" => "Ugenumre vises i de relevante visnings.",
"time_format_us" => "12-timer AM/PM",
"time_format_eu" => "24-timer",
"sunday" => "Søndag",
"monday" => "Mandag",
"time_zones" => "TIME ZONES",
"dd_mm_yyyy" => "dd-mm-yyyy",
"mm_dd_yyyy" => "mm-dd-yyyy",
"yyyy_mm_dd" => "yyyy-mm-dd",

//settings.php - file uploads settings.
"maxUplSize_label" => "Maximum fil upload størrelse",
"maxUplSize_text" => "Maximum tilladt fil størrelse når brugere uploader attachments eller thumbnail filer.<br>Note: De fleste PHP installationer har et maximum der er sat til 2 MB. (php_ini file) ",
"attTypes_label" => "Attachment fil typer",
"attTypes_text" => "Komma separeret liste med tilladte attachment filtyper der må uploades. (Eks. '.pdf,.jpg,.gif,.png,.mp4,.avi')",
"tnlTypes_label" => "Thumbnail fil typer",
"tnlTypes_text" => "Komma separeret liste med tilladte thumbnail filtyper der må uploades. (Eks. '.jpg,.jpeg,.gif,.png')",
"tnlMaxSize_label" => "Thumbnail - maximum størrelse",
"tnlMaxSize_text" => "Maximum thumbnail image størrelse. Hvis brugeren uploader større billeder, vil billedet blive resizet til maximun størrelse.<br>Note: Store thumbnails vil fylde hele dag-cellen i månedsvisning, hvilket kan føre til uønskede effekter.",
"tnlDelDays_label" => "Thumbnail delete margin",
"tnlDelDays_text" => "Hvis en thumbnail er brugt siden det angivne antal dage, kan den ikke slettes.<br>En o-værdi betyder at thumbnail-en ikke kan slettes.",
"days" =>"dage",
"mbytes" => "MB",
"wxhinpx" => "W x H ( bredde/Width W gange højde/Height H )i pixels",

//settings.php - reminders settings.
"services_label" => "Tilgængelige message services",
"services_text" => "Services tilgængelige til at sende reminders. Hvis en service ikke er valgt, vil den tilhørende sektion i event-vinduet ikke blive vist. Hvis ingen service er valgt, er det ikke muligt at sende reminders.",
"msgLogging_label" => "Notification message logging",
"msgLogging_text" => "When checked, the notification messages sent are logged in the messages.log file. The 'weeks' field specifies how long the logged messages should be kept",
"smsCarrier_label" => "SMS carrier template/skabelon",
"smsCarrier_text" => "SMS carrier templaten bruges til at sammensætte SMS gateway email adressen: ppp#sss@carrier, hvor . . .<br>• ppp: valgfri tekst streng der kan tilføjes før mobilnummeret<br>• #: pladsholder for modtagerens mobilnummer (kalenderen vil udskifte # med mobilnummer)<br>• sss: valgfri tekst streng til indsættelse efter mobilnummeret, eks. et username og password, som nogle operatører kræver<br>• @: separator karakter<br>• carrier: carrier adresse (eks. mail2sms.com)<br>Template eksempel: #@xmobile.com, 0#@carr2.int, #myunmypw@sms.gway.net.",
"smsCountry_label" => "SMS landekode",
"smsCountry_text" => "Hvis SMS gateway en er lokaliseret i et andet land end kalenderen, så skal landekoden hvor kalenderen befinder sig, bruges.<br>Vælg om '+' eller '00' prefix er krævet.",
"smsSubject_label" => "SMS subject template",
"smsSubject_text" => "Hvis angivet, vil teksten i denne template, blive kopieret til Emnefeltet i SMS email beskeden der sendes til carrieren. Teksten kan indeholde karakteren #, hvilket vil blive udskiftet med mobilnummeret på event-ejeren (afhængig af opsætningen ovenover).<br>Example: 'FROMPHONENUMBER=#'.",
"smsAddLink_label" => "Tilføj et event-link til SMS",
"smsAddLink_text" => "Hvis checked, vil et link til eventen blive tilføjet hver SMS. Ved at åbne dette link på mobilen, vil modtageren være i stand til at se event detaljer på sin mobil.",
"maxLenSms_label" => "Maximum SMS besked længde",
"maxLenSms_text" => "SMS beskeder er sendt med utf-8 character encoding. Beskeder op til 70 karakterer ( 160 hvis der ingen specialtegn er ) vil medføre en enkelt SMS besked; beskeder > 70 karakterer, med mange Unicode karakterer , kan blive delt til flere multi-beskeder.",
"calPhone_label" => "Kalenderens mobilnummer",
"calPhone_text" => "Mobilnummer brugt som sender ID når der sendes SMS beskeder.<br>Format: free, max. 20 digits (nogle lande kræver et telefonnummer, andre lande accepterer også alfanumeriske karakterer).<br>Hvis ingen SMS service er aktiv, eller hvis ingen SMS subject template er defineret, kan dette felt være blankt.",
"notSenderEml_label" => "Tilføj 'Reply to' felt til emailen",
"notSenderEml_text" => "Hvis valgt, notification emails vil indeholde et 'Reply to' felt med email adressen på event-ejeren, til hvem modtageren kan svare.",
"notSenderSms_label" => "Sender af notification SMSes",
"notSenderSms_text" => "Når kalenderen sender påmindelse SMSer, kan sender ID på SMS beskeden være enten kalenderens mobilnummer eller mobilnummeret på den der oprettede eventen.<br>Hvis  'bruger' er valgt og en brugerkonto ikke har et mobilnummer, vil kalenderens mobilnummer blive anvendt.<br>Hvis brugerens mobilnummer er valgt, kan modtageren svare på SMS beskeden.",
"defRecips_label" => "Default liste på modtagere",
"defRecips_text" => "hvis angivet, vil dette blive default modtagerliste for email og/eller SMS beskeder i event vinduet. Hvis feltet efterlades blankt, vil default modtager være event-ejeren.",
"maxEmlCc_label" => "Max. antal modtagere per email",
"maxEmlCc_text" => "Normalt tillader ISPer et maximum antal modtagere pr. email. Hvis man sender emails med et større antal modtagere end angivet her, vil emailen blive splittet op i flere email, hver med det angivne antal max modtagere.",
"emlFootnote_label" => "Reminder email fodnote",
"emlFootnote_text" => "Free-format tekst som vil blive tilføjet som et afsnit i enden af emailen. HTML tags er tilladt i teksten.",
"mailServer_label" => "Mail server",
"mailServer_text" => "PHP mail kan bruges ved ikke-autentificeret mail i mindre omfang. For større omfang eller hvis autentificering er påkrævet, anbefales det at anvende SMTP.<br>Brug af SMTP mail kræver en SMTP mail server. Konfigurationsoplysningerne skal angives herunder.",
"smtpServer_label" => "SMTP server navn",
"smtpServer_text" => "Hvis SMTP mail er valgt, skal SMTP server navnet angives her. Fx gmail SMTP server: smtp.gmail.com.",
"smtpPort_label" => "SMTP port nummer",
"smtpPort_text" => "Hvis SMTP mail er valgt, skal SMTP Port nummer angives her. Fx 25, 465 or 587. Gmail bruger for eksempel port nummer 465.",
"smtpSsl_label" => "SSL (Secure Sockets Layer)",
"smtpSsl_text" => "Hvis SMTP mail er valgt, kan her angives om secure sockets layer (SSL) skal anvendes. For gmail: aktiveret",
"smtpAuth_label" => "SMTP autentificering",
"smtpAuth_text" => "Hvis SMTP autentificering er valgt, vil det brugernavn og adgangskode som angives her blive anvendt til at autentificere SMTP mail.<br>For gmail for instance, the user name is the part of your email address before the @.",
"tlgToken_label" => "Telegram token",
"tlgToken_text" => "Telegram token i følgende format: &lt;bot ID&gt;:&lt;bot hash&gt;. For detailjer se installation_guide.html, afsnit Event Notification Messages.",
"cc_prefix" => "landekode starter med prefix + eller 00",
"weeks" => "Weeks",
"general" => "Generelt",
"php_mail" => "PHP mail",
"smtp_mail" => "SMTP mail (complete fields below)",

//settings.php - periodic function settings.
"cronHost_label" => "Cron job host",
"cronHost_text" => "Angiv hvor cronjobbet er hosted. Det er det periodevise job der kører scriptet 'lcalcron.php'.<br>• local: cronjobbet kører på den samme server<br>• remote: cronjobbet kører på en remote server, eller lcalcron.php stsartes manuelt via browseren ( kan bruges til test)<br>• IP address: cronjobbet kører på en remote server som har den angivne IP adressse.",
"cronSummary_label" => "Admin cron job oversigt",
"cronSummary_text" => "Send en cron job oversigt til kalender administratoren.<br>Aktivering er kun relevant hvis et cron job er blevet konfigureret for kalenderen.",
"chgSummary_text" => "Antal dage, der skal ses tilbage efter kalender-ændringer.<br>Hvis antal dage sættes til 0 vil der ikke blive sendt en oversigt over ændringer.",
"icsExport_label" => "Daglig eksport af iCal begivenheder",
"icsExport_text" => "Hvis aktiveret: Alle begivenheder i datointervallet -1 uge til +1 år vil blive eksporteret i iCalendar format til en .ics fil i folderen 'files'.<br>Filnavnet vil være kalenderens navn, hvor mellemrum erstattes af underscore-tegn ('_'). Eksisterende filer vil blive overskrevet af nye filer.",
"eventExp_label" => "Begivenhed udløb dage",
"eventExp_text" => "Antal dage efter begivenhedens slutdato, hvor begivenheden udløber og automatisk slettes.<br>Hvis antal dage sættes til 0 eller hvis der ikke er konfigureret et cron job, vil der ikke automatisk blive slettet begivenheder.",
"maxNoLogin_label" => "Max. antal dage ikke logget ind",
"maxNoLogin_text" => "Hvis en bruger ikke har logget ind i løbet af dette antal dage, vil brugerprofilen automatisk blive slettet.<br>Hvis værdien sættes til 0, vil brugerprofiler ikke blive slettet automatisk",
"local" => "local",
"remote" => "remote",
"ip_address" => "IP address",

//settings.php - mini calendar / sidebar settings.
"popFieldsSbar_label" => "Begivenhedsfelter - sidebjælke pop-up boks",
"popFieldsSbar_text" => "Begivenhedsfelter, der skal vises i en pop-up boks når musen føres hen over en begivenhed i den fritstående sidebjælke, kan angives ved en række numre.<br>Hvis ingen numre specificeres, vil der ikke blive vist en pop-up boks når musen holdes over begivenheden.",
"showLinkInSB_label" => "Vis links i sidebjælke",
"showLinkInSB_text" => "Vis URL'er fra begivenhed beskrivelsesfeltet som et hyperlink i sidebjælken med kommende begivenheder.",
"sideBarDays_label" => "Antal dage at se frem i sidebjælke",
"sideBarDays_text" => "Antal dage som der skal ses frem efter begivenheder i sidebjælken.",

//login.php
"log_log_in" => "Log ind",
"log_remember_me" => "Husk mig",
"log_register" => "Registrer",
"log_change_my_data" => "Ændre mine data",
"log_save" => "Ændre",
"log_done" => "Klar",
"log_un_or_em" => "Brugernavn eller email",
"log_un" => "Brugernavn",
"log_em" => "Email",
"log_ph" => "Mobiltelefon nummer",
"log_tg" => "Telegram chat ID",
"log_answer" => "Dit svar",
"log_pw" => "Password",
"log_expir_date" => "Account expiration date",
"log_account_expired" => "This account has expired",
"log_new_un" => "Nyt brugernavn",
"log_new_em" => "Ny email",
"log_new_pw" => "Nyt Password",
"log_con_pw" => "Bekræft Password",
"log_pw_msg" => "Her er dine login detaljer til at logge ind til",
"log_pw_subject" => "Dit Password",
"log_npw_subject" => "Dit nye Password",
"log_npw_sent" => "Dit nye password er blevet sendt.",
"log_registered" => "Registrering lykkedes - dit password er sendt til dig pr. email",
"log_em_problem_not_sent" => "Email problem - dit password kunne ikke sendes",
"log_em_problem_not_noti" => "Email problem - kunne ikke underrette administrator",
"log_un_exists" => "Brugernavn findes allerede",
"log_em_exists" => "Email-adresse findes allerede",
"log_un_invalid" => "Ugyldigt brugernavn (min. længde 2: A-Z, a-z, 0-9, og _-.) ",
"log_em_invalid" => "Ugyldig email-adresse",
"log_ph_invalid" => "Ugyldigt mobiltelefon nummer",
"log_tg_invalid" => "Invalid Telegram chat ID",
"log_sm_nr_required" => "SMS: mobile phone number required",
"log_tg_id_required" => "Telegram: chat ID required",
"log_sra_wrong" => "Forkert svar til det stillede spørgsmål",
"log_sra_wrong_4x" => "Du har svaret forkert 4 gange - prøv igen om 30 minutter",
"log_un_em_invalid" => "Brugernavn/email er ikke gyldig",
"log_un_em_pw_invalid" => "Dit brugernavn/email eller password er forkert",
"log_pw_error" => "Password stemmer ikke",
"log_no_un_em" => "Du indtastede ikke brugernavn/email",
"log_no_un" => "Indtast dit brugernavn",
"log_no_em" => "Indtast din email-adresse",
"log_no_pw" => "Du indtastede ikke dit password",
"log_no_rights" => "Login afvist: du har ingen rettigheder til at se kalender - Kontakt administrator",
"log_send_new_pw" => "Send nyt password",
"log_new_un_exists" => "Nyt brugernavn findes allerede",
"log_new_em_exists" => "Ny email-adresse findes allerede",
"log_ui_language" => "Brugerinterface sprog",
"log_new_reg" => "Ny bruger registrering",
"log_date_time" => "Dato / tid",
"log_time_out" => "Time out",

//categories.php
"cat_list" => "Liste med kategorier",
"cat_edit" => "Editer",
"cat_delete" => "Slet",
"cat_add_new" => "Tilføj ny kategori",
"cat_add" => "Tilføj",
"cat_edit_cat" => "Editer kategori",
"cat_sort" => "Sorter på Navn",
"cat_cat_name" => "Kategorinavn",
"cat_symbol" => "Symbol",
"cat_symbol_repms" => "Category symbol (erstatter minifirkanterne)",
"cat_symbol_eg" => "e.g. A, X, ♥, ⛛",
"cat_matrix_url_link" => "URL link (vises i matrix view)",
"cat_seq_in_menu" => "Rækkefølge i menu",
"cat_cat_color" => "Kategorifarve",
"cat_text" => "Tekst",
"cat_background" => "Baggrund",
"cat_select_color" => "Vælg farve",
"cat_subcats" => "Under-<br>categorier",
"cat_subcats_opt" => "Antal underkategorier (valgfri)",
"cat_copy_from" => "Kopier fra",
"cat_eml_changes_to" => "Send event changes to",
"cat_url" => "URL",
"cat_name" => "Navn",
"cat_subcat_note" => "Bemærk at aktuelle eksisterende subkategorier kan være brugt på en eksisterende event.",
"cat_save" => "Opdater",
"cat_added" => "Kategori tilføjet",
"cat_updated" => "Kategori opdateret",
"cat_deleted" => "Kategori slettet",
"cat_not_added" => "Kategori ikke tilføjet",
"cat_not_updated" => "Kategori ikke opdateret",
"cat_not_deleted" => "Kategori ikke slettet",
"cat_nr" => "#",
"cat_repeat" => "Gentagelse",
"cat_every_day" => "hver dag",
"cat_every_week" => "hver uge",
"cat_every_month" => "hver måned",
"cat_every_year" => "hvert år",
"cat_overlap" => "Overlap<br>tilladt<br>(gap)",
"cat_need_approval" => "Begivenheder kræver<br>godkendelse",
"cat_no_overlap" => "Overlap ikke tilladt",
"cat_same_category" => "Samme kategori",
"cat_all_categories" => "Alle kategorier",
"cat_gap" => "gap",
"cat_ol_error_text" => "Fejltekst ved overlap",
"cat_no_ol_note" => "Bemærk at allerede eksisterende events ikke bliver tjekket, og at de måske allerede overlapper",
"cat_ol_error_msg" => "event overlap; Vælg andet tidspunkt",
"cat_no_ol_error_msg" => "Overlap error message mangler",
"cat_duration" => "Event<br>varighed<br>! = fixed",
"cat_default" => "default (ikke sluttid)",
"cat_fixed" => "fixed",
"cat_event_duration" => "Event varighed",
"cat_olgap_invalid" => "Ugyldig overlap gap",
"cat_duration_invalid" => "Ugyldig tids periode",
"cat_no_url_name" => "URL link navn mangler",
"cat_invalid_url" => "Ugyldigt URL link",
"cat_day_color" => "Dag farve",
"cat_day_color1" => "Dag farve (år/matrix view)",
"cat_day_color2" => "Dag farve (måned/uge/dag visning)",
"cat_approve" => "Begivenheder kræver godkendelse",
"cat_check_mark" => "Tjekboks",
"cat_not_list" => "Notify<br>list",
"cat_label" => "betegnelse",
"cat_mark" => "mærke",
"cat_name_missing" => "Kategorinavn mangler",
"cat_mark_label_missing" => "Tjekmærke/betegnelse mangler",

//users.php
"usr_list_of_users" => "Liste med brugere",
"usr_name" => "Brugernavn",
"usr_email" => "Email",
"usr_phone" => "Mobil telefon nummer",
"usr_phone_br" => "Mobil telefon<br>number",
"usr_tg_id" => "Telegram chat ID",
"usr_tg_id_br" => "Telegram<br>chat ID",
"usr_not_via" => "Notify via",
"usr_not_via_br" => "Notify<br>via",
"usr_language" => "Sprog",
"usr_ui_language" => "Bruger interface sprog",
"usr_group" => "Gruppe",
"usr_password" => "Password",
"usr_expir_date" => "Account expiration date",
"usr_select_exp_date" => "Select expiration date",
"usr_blank_none" => "blank: no expiration",
"usr_expires" => "Expires",
"usr_edit_user" => "Editer bruger profil",
"usr_add" => "Tilføj bruger",
"usr_edit" => "Editer",
"usr_delete" => "Slet",
"usr_login_0" => "Første login",
"usr_login_1" => "Sidste login",
"usr_login_cnt" => "Logins",
"usr_add_profile" => "Tilføj profil",
"usr_upd_profile" => "Opdater profiler",
"usr_if_changing_pw" => "Kun hvis password skal ændres",
"usr_pw_not_updated" => "Password ikke opdateret",
"usr_added" => "Bruger tilføjet",
"usr_updated" => "Brugerprofil opdateret",
"usr_deleted" => "Bruger slettet",
"usr_not_deleted" => "Bruger ikke slettet",
"usr_cred_required" => "Brugernavn, email og password kræves",
"usr_name_exists" => "Brugernavn findes allerede",
"usr_email_exists" => "Emailadresse findes allerede",
"usr_un_invalid" => "Ugyldigt brugernavn (min. længde 2: A-Z, a-z, 0-9, og _-.) ",
"usr_em_invalid" => "Ugyldig email addresse",
"usr_ph_invalid" => "Ugyldig mobil telefon nummer",
"usr_tg_invalid" => "Invalid Telegram chat ID",
"usr_xd_invalid" => "Invalid account expiration date",
"usr_cant_delete_yourself" => "Du kan ikke slette dig selv",
"usr_go_to_groups" => "Gå til gruppe",
"usr_all_cats" => "Alle kategorier",
"usr_select" => "Vælg",
"usr_transfer" => "Overfør",
"usr_transfer_evts" => "Overfør Events",
"usr_transfer_ownership" => "Overfør ejerskab of events",
"usr_cur_owner" => "Nuværende ejer",
"usr_new_owner" => "Ny ejer",
"usr_event_cat" => "Event kategori",
"usr_sdate_between" => "Start dato mellem",
"usr_cdate_between" => "Creation dato mellem",
"usr_select_start_date" => "Vælg start dato",
"usr_select_end_date" => "Vælg slut dato",
"usr_blank_no_limit" => "Blank date: ingen grænse",
"usr_no_undone" => "ADVARSEL, DENNE HANDLING KAN IKKE FORTRYDES - det kan den godt men den kan ikke omgøres",
"usr_invalid_sdata" => "Ugyldig start dato",
"usr_invalid_cdata" => "Ugyldig creation dato",
"usr_edate_lt_sdate" => "Slut dato før start dato",
"usr_no_new_owner" => "Ny ejer ikke angivet",
"usr_evts_transferred" => "Done. Events overført",

//groups.php
"grp_list_of_groups" => "Liste over Bruger Gruppe",
"grp_name" => "Gruppenavn",
"grp_priv" => "Rettigheder",
"grp_categories" => "Kategorier",
"grp_all_cats" => "Alle kategorier",
"grp_rep_events" => "Repeating<br>events",
"grp_m-d_events" => "Multi-day<br>events",
"grp_priv_events" => "Private<br>events",
"grp_upload_files" => "Upload<br>files",
"grp_tnail_privs" => "Thumbnail<br>rettigheder",
"grp_priv0" => "Ingen adgangsrettigheder",
"grp_priv1" => "Vise calendar",
"grp_priv2" => "Opret/editer egne events",
"grp_priv3" => "Opret/editer alle events",
"grp_priv4" => "Opret/Edit + manager",
"grp_priv9" => "Administrator",
"grp_may_post_revents" => "Post repeating events tilladt",
"grp_may_post_mevents" => "Post multi-day events tilladt",
"grp_may_post_pevents" => "Post private events tilladt",
"grp_may_upload_files" => "Upload filer tilladt",
"grp_tn_privs" => "Thumbnails rettigheder",
"grp_tn_privs00" => "Ingen",
"grp_tn_privs11" => "Vis alle",
"grp_tn_privs20" => "Håndter egne",
"grp_tn_privs21" => "H.egne/V.alle",
"grp_tn_privs22" => "Håndter alle",
"grp_edit_group" => "Editer Bruger Gruppe",
"grp_sub_to_rights" => "Givne brugerrettigheder",
"grp_view" => "Vis",
"grp_add" => "Tilføj",
"grp_edit" => "Editer",
"grp_delete" => "Slet",
"grp_add_group" => "Tilføj Gruppe",
"grp_upd_group" => "Opdater Gruppe",
"grp_added" => "Gruppe tilføjet",
"grp_updated" => "Gruppe opdateret",
"grp_deleted" => "Gruppe slettet",
"grp_not_deleted" => "Gruppe ikke slettet",
"grp_in_use" => "Gruppe er i brug",
"grp_cred_required" => "Gruppenavn, Rettigheder og Kategorier kræves",
"grp_name_exists" => "Gruppenavn findes allerede",
"grp_name_invalid" => "Ugyldigt Gruppenavn (min længde 2: A-Z, a-z, 0-9, og _-.) ",
"grp_check_add" => "Mindst en check box i Add kolonnen skal være checked",
"grp_background" => "Baggrund farve",
"grp_select_color" => "Vælg farve",
"grp_invalid_color" => "Favekode ugyldig (#XXXXXX hvor X = HEX-værdi)",
"grp_go_to_users" => "Gå til brugere",

//texteditor.php
"edi_text_editor" => "Edit Informations tekst",
"edi_file_name" => "File name",
"edi_save" => "Save tekst",
"edi_backup" => "Backup tekst",
"edi_select_file" => "Vælg fil",
"edi_info_text" => "Info tekst",
"edi_pub_recips" => "Public modtagere",
"edi_recips_list" => "Modtager liste",
"edi_new_recips_list" => "Ny modtager liste",
"edi_no_file_name" => "Intet filnavn angivet",
"edi_no_text" => "Der er ingen tekst",
"edi_confirm_changes" => "Tekstændringerne er ikke gemt\\nØnsker du at fortsætte?", //don't remove '\\n'
"edi_text_saved" => "Tekst gemt i fil $1",

//database.php
"mdb_dbm_functions" => "Databasefunktioner",
"mdb_noshow_tables" => "Kan ikke hente tabel(ler)",
"mdb_noshow_restore" => "Kan ikke finde backupfil",
"mdb_file_not_sql" => "Source backup fil skulle være en SQL fil (extension '.sql')",
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
"mdb_compact" => "Komprimer database",
"mdb_compact_table" => "Komprimer tabel",
"mdb_compact_error" => "Fejl",
"mdb_compact_done" => "Udført",
"mdb_purge_done" => "Begivenheder slettet for mere end 30 dage siden fjernet permanent",
"mdb_backup" => "Backup database",
"mdb_backup_table" => "Backup tabel",
"mdb_backup_file" => "Backup fil",
"mdb_backup_done" => "Udført",
"mdb_records" => "poster",
"mdb_restore" => "Gendan database",
"mdb_restore_table" => "Gendan tabel",
"mdb_inserted" => "poster indsat",
"mdb_db_restored" => "Database gendannet",
"mdb_db_upgraded" => "Database upgraded",
"mdb_no_bup_match" => "Backupfil stemte ikke overens med kalender version.<br>Database blev ikke restored.",
"mdb_events" => "Begivenheder",
"mdb_delete" => "slet",
"mdb_undelete" => "gendan",
"mdb_between_dates" => "forekommer i perioden",
"mdb_deleted" => "Begivenheder slettet",
"mdb_undeleted" => "Begivenheder gendannet",
"mdb_file_saved" => "Backupfil gemt i 'files' folder på server.",
"mdb_file_name" => "Filnavn",
"mdb_start" => "Start",
"mdb_no_function_checked" => "Ingen funktion(er) valgt",
"mdb_write_error" => "Fejl ved skrivning af backupfil<br>Tjek rettigheder for 'files/' folderen",

//import/export.php
"iex_file" => "Valgt fil",
"iex_file_name" => "Destination filnavn",
"iex_file_description" => "iCal fil-beskrivelse",
"iex_filters" => "Begivenhed filtre",
"iex_export_usr" => "Eksporter User Profiles",
"iex_import_usr" => "Importer User Profiles",
"iex_upload_ics" => "Opload iCal-fil",
"iex_create_ics" => "Opret iCal-fil",
"iex_tz_adjust" => "Timezone adjustments",
"iex_upload_csv" => "Opload CSV-fil",
"iex_upload_file" => "Opload fil",
"iex_create_file" => "Opret fil",
"iex_download_file" => "Download fil",
"iex_fields_sep_by" => "Felter adskilt af",
"iex_birthday_cat_id" => "Fødselsdagskategori ID",
"iex_default_grp_id" => "Default user group ID",
"iex_default_cat_id" => "Standardkategori ID",
"iex_default_pword" => "Default password",
"iex_if_no_pw" => "Hvis intet password angivet",
"iex_replace_users" => "Erstat-Replace eksisterende brugere",
"iex_if_no_grp" => "Hvis ingen brugergruppe fundet",
"iex_if_no_cat" => "hvis ingen kategori findes",
"iex_import_events_from_date" => "Importer begivenheder der sker efter",
"iex_no_events_from_date" => "Ingen begivenheder fundet udfra dato",
"iex_see_insert" => "se vejledning i højre side",
"iex_no_file_name" => "Filnavn mangler",
"iex_no_begin_tag" => "ugyldig iCal-fil (BEGIN-tag mangler)",
"iex_bad_date" => "Ugyldig dato",
"iex_date_format" => "Begivenheds-dato-format",
"iex_time_format" => "Begivenheds-tids-format",
"iex_number_of_errors" => "Antal fejl i listen",
"iex_bgnd_highlighted" => "baggrund fremhævet",
"iex_verify_event_list" => "Verificer begivenhedsliste, korriger fejl og klik",
"iex_add_events" => "Tilføj begivenheder til database",
"iex_verify_user_list" => "Kontroller bruger listen, ret eventuelle fejl og klik",
"iex_add_users" => "Tilføj brugere til databasen",
"iex_select_ignore_birthday" => "Vælg fødselsdag og slet markeringsfelter som ønsket",
"iex_select_ignore" => "Vælg slet markeringsfelter for at ignorere begivenheder",
"iex_check_all_ignore" => "Alle ignore bokse tændt/af",
"iex_title" => "Titel",
"iex_venue" => "Sted",
"iex_owner" => "Ejer",
"iex_category" => "Kategori",
"iex_date" => "Dato",
"iex_end_date" => "Slutdato",
"iex_start_time" => "Starttid",
"iex_end_time" => "Sluttid",
"iex_description" => "Beskrivelse",
"iex_repeat" => "Gentagelse",
"iex_birthday" => "Fødselsdag",
"iex_ignore" => "Slet",
"iex_events_added" => "begivenheder tilføjet",
"iex_events_dropped" => "begivenheder udeladt (findes allerede)",
"iex_users_added" => "users tilføjet",
"iex_users_deleted" => "users slettet",
"iex_csv_file_error_on_line" => "CSV-filfejl på linje",
"iex_between_dates" => "Startdato i perioden",
"iex_changed_between" => "Tilføjet/ændret i perioden",
"iex_select_date" => "Vælg dato",
"iex_select_start_date" => "Vælg startdato",
"iex_select_end_date" => "Vælg slutdato",
"iex_group" => "Bruger gruppe",
"iex_name" => "Bruger navn",
"iex_email" => "Email adresse",
"iex_phone" => "Telefonnummer",
"iex_msgID" => "Chat ID",
"iex_lang" => "Sprog",
"iex_pword" => "Password",
"iex_all_groups" => "alle grupper",
"iex_all_cats" => "alle kategorier",
"iex_all_users" => "alle brugere",
"iex_no_events_found" => "Ingen begivenheder fundet",
"iex_file_created" => "Fil oprettet",
"iex_write error" => "Oprettelse af eksportfil mislykkedes<br>Tjek rettigheder for folderen 'files/'",
"iex_invalid" => "ugyldig",
"iex_in_use" => "allerede i brug",

//cleanup.php
"cup_cup_functions" => "Clean Up Funktioner",
"cup_fill_fields" => "Udfyld dato og klik oprydning-Clean Up.",
"cup_found_confirm" => "Hvis der er emner i 'to be cleaned up' vil du blive spurgt om confirmation.",
"cup_evt" => "Events til sletning",
"cup_usr" => "Brugerkonto der skal slettes",
"cup_att" => "Attachments der skal slettes",
"cup_rec" => "Modtager liste der skal slettes",
"cup_tns" => "Thumbnails der skal slettes",
"cup_past_events" => "Forgangne events",
"cup_past_users" => "Inaktive brugere",
"cup_att_dir" => "Attachments folder",
"cup_rec_dir" => "Modtagerliste folder",
"cup_tns_dir" => "Thumbnails folder",
"cup_usr_text" => "Brugerkonti der ikke er logget ind på siden",
"cup_evt_text" => "Events som er sket før",
"cup_att_text" => "Attachments ikke brugt i en event siden",
"cup_rec_text" => "Modtagerlister ikke brugt siden",
"cup_tns_text" => "Thumbnails ikke brugt i events siden",
"cup_select_date" => "Vælg dato",
"cup_blank_date1" => "En blank dato betyder: Har aldrig logget ind.",
"cup_blank_date2" => "En blank dato betyder: Aldrig brugt (forældreløs).",
"cup_nothing_to_delete" => "Ingenting at rydde op",
"cup_clean_up" => "Ryd op",
"cup_cancel" => "Fortryd",
"cup_delete" => "Slet",
"cup_invalid date" => "Ugyldig dato",
"cup_events_deleted" => "Events slettet",
"cup_accounts_deleted" => "Konti slettet",
"cup_files_deleted" => "Filer slettet",
"cup_important" => "VIGTIGT:",
"cup_deleted_compact" => "Slettede events og brugerkonti bliver markeret 'slettet', men optager stadig plads.<br> På siden(menupunktet) Database, kan disse events og konti slettes permanent<br>ved at bruge Compact funktionen.",
"cup_deleted_files" => "Slettede filer er permanent fjernet fra folderne og kan ikke genskabes medmindre du har en kopi!",

//toolsaaf.php
"aff_sel_cals" =>  "Select calendar(s)",
"aff_evt_copied" =>  "Event copied",

//styling.php
"sty_css_intro" =>  "Værdier speciferet på denne side, skal følge CSS standarden",
"sty_preview_theme" => "Preview Tema",
"sty_preview_theme_title" => "Preview vist tema i kalenderen",
"sty_stop_preview" => "Stop Preview",
"sty_stop_preview_title" => "Stop preview af vist tema i kalenderen",
"sty_save_theme" => "Save Tema",
"sty_save_theme_title" => "Save vist tema i database",
"sty_backup_theme" => "Backup Tema",
"sty_backup_theme_title" => "Backup tema fra database to file",
"sty_restore_theme" => "Restore Tema",
"sty_restore_theme_title" => "Restore tema fra file til aktuel visning",
"sty_default_luxcal" => "default LuxCal tema",
"sty_close_window" => "Luk vindue",
"sty_close_window_title" => "Luk dette vindue",
"sty_theme_title" => "Tema titel",
"sty_general" => "Generelt",
"sty_grid_views" => "Grid / Views",
"sty_hover_boxes" => "Hover Boxes",
"sty_bgtx_colors" => "Background/text colors",
"sty_bord_colors" => "Border colors",
"sty_fontfam_sizes" => "Font family/sizes",
"sty_font_sizes" => "Font sizes",
"sty_miscel" => "Diverse",
"sty_background" => "Baggrund",
"sty_text" => "Tekst",
"sty_color" => "Farve",
"sty_example" => "Eksempel",
"sty_theme_previewed" => "Preview mode - du kan nu se/bruge kalenderen. Vælg Stop Preview når du er færdig.",
"sty_theme_saved" => "Tema gemt i database",
"sty_theme_backedup" => "Tema backed up fra database til fil:",
"sty_theme_restored1" => "Tema restored fra fil:",
"sty_theme_restored2" => "Tryk Save Theme for at gemme temaet i database",
"sty_unsaved_changes" => "ADVARSEL – Unsaved ændringer!\\nHvis du lukker dette vindue vil du miste ændringerne.", //don't remove '\\n'
"sty_number_of_errors" => "Antal fejl i liste",
"sty_bgnd_highlighted" => "baggrund highlighted",
"sty_XXXX" => "kalender generelt",
"sty_TBAR" => "kalender top bar",
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
"cro_sum_header" => "CRON JOB OVERSIGT",
"cro_sum_trailer" => "SLUT PÅ OVERSIGT",
"cro_sum_title_eve" => "BEGIVENHEDER UDLØBET",
"cro_nr_evts_deleted" => "Antal begivenheder slettet",
"cro_sum_title_not" => "PÅMINDELSER",
"cro_no_reminders_due" => "Ingen påmindelsesdatoer nået",
"cro_due_in" => "Sker om",
"cro_due_today" => "Sker i dag",
"cro_days" => "dag(e)",
"cro_date_time" => "Dato /tid",
"cro_title" => "Titel",
"cro_venue" => "Sted",
"cro_description" => "Beskrivelse",
"cro_category" => "Kategori",
"cro_status" => "Status",
"cro_none_active" => "No reminders or periodic services active",
"cro_sum_title_use" => "BRUGERPROFILER UDLØBET",
"cro_nr_accounts_deleted" => "Antal profiler slettet",
"cro_no_accounts_deleted" => "Ingen profiler slettet",
"cro_sum_title_ice" => "EKSPORTEREDE  BEGIVENHEDER",
"cro_nr_events_exported" => "Antal begivenheder eksporteret i iCalendar format til fil",

//messaging.php
"mes_no_msg_no_recip" => "Ikke sendt, ingen modtagere fundet",

//explanations
"xpl_edit" =>
"<h3>Edit Instructioner</h3>
<p>Denne teksteditor kan benyttes til at editere indholdet af følgende filer:
<dl>
<dt>info.txt</dt><dd>Info teksten, som - hvis sat i indstillinger 
siden - er synlig i sidepanelet i højre side af kalenderen.</dd>
<dt>+recipients.txt</dt><dd>Denne fil med public (ikke-registrerede) modtagere, 
fra hvilken modtagere kan vælges som modtagere af reminder-beskeder.</dd>
<dt>&lt;list_name&gt;.txt</dt><dd>En eller flere lister med modtagere, som kan 
tilføjes og indholdet vil benyttes som modtagere af reminder beskeder.</dd>
</dl>
</p>",

"xpl_edit_info_texts" =>
"<h3>Edit Instructions - Information Texts</h3>
<p>Hvis aktiveret på settings-siden vil informations beskeden i tekst området 
til venstre blive vist i kalender-visningerne i et side-panel til højre for 
den aktuelle kalender side. Teksten kan indeholde HTML-tags og inline-styles. 
Eksempler på mulige tekstbeskeder kan findes i filen 
'sidepanel/samples/info.txt'.</p>
<p>Informations beskeder kan vises fra en start-dato til en slut-dato.
Hver informations blok skal indledes med en linie indeholdende perioden den ønskes vist 
omsluttet af ~ karakterer. Tekst før den første linie der starter med en ~ karakter
kan bruges til personlige notater og vil ikke blive vist i side-panelets informations område.</p><br>
<p>Start og slut dato format: ~m1.d1-m2.d2~, hvor m1 og d1 er start-måned 
og dag og m2 og d2 er slut måned og dag. Hvis d1 er udeladt, vil den første dag 
i m1 Blive anvendt. Hvis d2 er udeladt, vil den sidste dag i m2 blive anvendt. Hvis m2 og d2 
er udeladt, vil den sidste dag i m1 blive anvendt.</p>
<p>Eksempler:<br>
<b>~4~</b>: Hele april måned<br>
<b>~2.10-2.14~</b>: 10 - 14 februar<br>
<b>~6-7~</b>: 1 juni - 31 juli<br>
<b>~12.15-12.25~</b>: 15 - 25 december<br>
<b>~8.15-10.5~</b>: 15 august - 5 oktober<br>
<b>~12.15~</b>: 15 december - 31 december</p><br>
<p>FORSLAG: Start med at lave en backup-kopi (Backup tekst).</p>",

"xpl_edit_pub_recips" =>
"<h3>Edit Instructioner - Public modtagere</h3>
<p>Denne fil kan indeholde en liste med public (ikke registrerede) modtagere fra
hvilken modtagere kan vælges og kopieres til modtagerlisten som modtagere af reminder beskeder.</p>
<p>Hver modtager skal angives på en separat linie.</p><br>
<p>Afhængig af hvad der er specificeret i indstillinger angående beskedtjenester 
kan der angives:</p>
<ul>
<li>email adresse,</li>
<li>Telegram chat ID,</li>
<li>Mobiltelefon nummer.</li>
</ul>
<br>
<p>I filen vil en tekst startende med en #-karakter blive ignoreret
og blanke i starten eller enden af en specificeret modtager vil fjernes.</p>",

"xpl_edit_recips_list" =>
"<h3>Edit instruktioner - Recipients List</h3>
<p>Denne fil kan indeholde en liste med public eller registrerede modtagere. Hele filen 
kan tilføjes som et enkeltelement, da de enkelte modtagere i listen vil blive brugt som modtagere af reminder beskeder.</p>
<p>Hver modtager skal specificeres på en separat linie.</p><br>
<p>Afhængig af hvad der er specificeret i indstillinger angående beskedtjenester 
kan der angives:</p>
<ul>
<li>brugernavn,</li>
<li>email adresse,</li>
<li>Telegram chat ID,</li>
<li>Mobiltelefon nummer.</li>
</ul>
<br>
<p>I filen vil en tekst startende med en #-karakter blive ignoreret
og blanke i starten eller enden af en specificeret modtager vil fjernes.</p>
<p>En ny modtagerliste kan dannes ved at ændre filnavnet og vælge
Save (tekst) knappen</p>",

"xpl_manage_db" =>
"<h3>Vedligehold Database vejledning</h3>
<p>På denne side kan følgende funktioner vælges:</p>
<h6>Komprimer database</h6>
<p>Når en bruger sletter en begivenhed, vil begivenheden blive markeret som 'slettet', men den fjernes ikke fra databasen. Komprimer Database funktionen fjerner begivenheder permanent, hvis det er mere end 30 dage siden de blev slettet, for at frigøre plads i databasen.</p>
<h6>Backup database</h6>
<p>Denne funktion vil oprette en backup af hele kalenderdatabasen (tabellernes struktur og indhold) i .sql format. Backupfilen gemmes i <strong>files/</strong> folderen med filnavn: 
<kbd>dump-cal-lcv-ååååmmdd-ttmmss.sql</kbd> (hvor 'cal' = kalender ID, 'lcv' = kalender version og 'ååååmmdd-ttmmss' = år, måned og dag, time, minut og sekund).</p>
<p>Backupfilen kan bruges til at gendanne kalenderdatabasen (struktur og data), via gendannelsesfunktionnen beskrevet nedenfor, eller ved at bruge fx
<strong>phpMyAdmin</strong> værktøjet, som de fleste webhoteller stiller til rådighed.</p>
<h6>Gendan database</h6>
<p>Denne funktion vil gendanne kalenderdatabasen ud fra indholdet af den oploadede backup file (file type .sql). If your .sql file is larger than 2MB you may have to modify the <b>upload_max_filesize</b> and <b>post_max_size</b> variables in the php.ini file, or split your .sql file in several smaller files. See the admin_guide.html section 3 for a detailed explanation.</p>
<p>Når databasen gendannes, vil ALLE NUVÆRENDE DATA VÆRE FJERNET! Kun de gendannede data vil være tilstede.</p>
<h6>Begivenheder</h6>
<p>Denne funktion vil slette eller gendanne begivenheder, som forekommer mellem de angivne datoer. Hvis et datofelt er tomt, vil der ikke være nogen grænse; så hvis begge datofelter er tomme, VIL ALLE BEGIVENHEDER BLIVE SLETTET!</p><br>
<p>VIGTIGT: Når databasen bliver komprimeret (se ovenfor), vil begivenheder som fjernes permanent fra databasen ikke længere kunne gendannes!</p>",

"xpl_import_csv" =>
"<h3>CSV import-vejledning</h3>
<p>Denne formular bruges til at importere en <strong>kommasepareret (CSV)</strong> tekst-fil med begivenheder til LuxCal kalenderen.</p>
<p>Rækkefølgen af kolonner i CSV-filen skal være: titel, sted, kategori-id (se herunder), dato, slutdato, starttid, sluttid og beskrivelse. Første række i CSV-filen, der bruges til kolonnebeskrivelser, ignoreres.</p>
<h6>Eksempel CSV-filer</h6>
<p>Eksempel CSV-filer findes i folderen 'files/' i din LuxCal-download.</p>
<h6>Field separator</h6>
Som adskillelsestegn ( field separator ) kan anvendes enhver karakter, for eksempel et komma, semi-kolon eller en
tab-karakter (tab-character: '\\t'). Felt-adskilleslsestegnet skal være unikt og må ikke være en del af tekst, tal, eller dato i nogen af felterne.
<h6>Dato- og tidsformat</h6>
<p>Det valgte begivenheds datoformat og begivenheds tidsformat til venstre skal passe til formatet for datoer og tider i den oploadede CSV-fil.</p>
<h6>Timezone justeringer</h6>
<p>Hvis din iCalendar fil indeholder events i en anden tidszone og datoer/tidspunkter 
skal justeres til kalenderens tidszone så afcheck 'Timezone adjustments'.</p>
<p>If no start time (blank) is present, the event will be shown as a 'no time' event 
in the calendar. If the start time is 00:00 or 12:00am, the event will be shown as 
an 'all day' event in the calendar.</p>
<h6>Tabel med kategorier</h6>
<p>Kalenderen bruger ID-numre til at angive kategorier. Kategori-ID'erne i CSV-filen skal svare til kategorierne brugt i kalenderen eller være tomme.</p>
<p>Hvis du i næste skridt vil markere en begivenhed som 'fødselsdag', skal <strong>fødselsdags-kategorien</strong> sættes til den tilsvarende ID i kategorilisten herunder.</p>
<p class='hired'>ADVARSEL: Importer ikke mere end 100 begivenheder af gangen!</p>
<p>I din kalender er de følgende kategorier defineret i øjeblikket:</p>",

"xpl_import_user" =>
"<h3>vejledning for import af brugere/users</h3>
<p>Denne formular bruges til import af en CSV (Comma Separated Values) tekst fil indeholdende 
bruger data til import af brugere til users-tabellen i LuxCal kalenderen.</p>
<p>For at opnå en korrekt håndtering af specielle karakterer, må CSV-filen være UTF-8 encoded.</p>
<h6>Felt adskiller/separator</h6>
<p>Feltadskilleren/separatoren kan være enhver karakter, for eksempel comma, semi-kolon, etc.
Felt adskiller/separator tegnet skal være unikt 
og må ikke findes i teksten i filen.</p>
<h6>Default user group ID</h6>
<p>Hvis user group ID feltet er blankt/tomt i en record, vil det angivne default 
user group ID blive anvendt.</p>
<h6>Default password</h6>
<p>Hvis password feltet er blankt/tomt i en record, vil det angivne default 
password blive anvendt.</p>
<h6>Replace eksisterende brugere/users</h6>
<p>Hvis Replace eksisterende brugere/users er valgt, vil alle eksisterende brugere, 
undtagen public user og administrator, blive slettet før import af 
brugere fra filen.</p>
<br>
<h6>Eksempelfiler brugere til import</h6>
<p>Eksempel på brugerfiler CSV files (.csv) kan findes i '!luxcal-toolbox/' folderen af/på 
dine LuxCal installationsfiler.</p>
<h6>Felter i CSV filen</h6>
<p>Rækkefølgen af kolonner skal være som angivet. Hvis den første række af CSV filen 
indeholder kolonneoverskrifter, vil den blive ignoreret.</p>
<ul>
<li>User group ID: Skal svare til brugergrupperne i kalenderen (se
liste herunder). Hvis blank/tom, vil brugeren blive anbragt i den angivne brugergruppe</li>
<li>User name: mandatory</li>
<li>Email address: mandatory</li>
<li>Mobile phone number: optional</li>
<li>Telegram chat ID: optional</li>
<li>Interface language/sprog: optional. Ex. English, Dansk. Hvis blank/tom vil default 
language/sproget angivet i settings, blive anvendt.</li>
<li>Password: optional. Hvis blank/tom, vil det angivne default password blive anvendt.</li>
</ul>
<p>Blanke/tomme felter bør indikeres med to quotes. Blanke/tomme felter i enden af hver 
række kan udelades.</p>
<p class='hired'>Adwarsel: Importer ikke mere end 60 brugere ad gangen!</p>
<h6>Liste med User Group IDs</h6>
<p>I kalenderen er der i øjeblikket defineret:</p>",

"xpl_export_user" =>
"<h3>Brugere Export vejledning</h3>
<p>Denne formular bruges til at udtrække og eksportere <strong>User Profiles</strong> fra
LuxCal kalenderen.</p>
<p>Filer vil blive oprettet i'files/' folderen på din server med det 
angivne filnavn og i en kommasepareret ( hvis komma er valgt som tegn ) fil (.csv) format.</p>
<h6>Destination/target filnavn</h6>
Hvis ikke angivet vil filnavnet blive 
kalendernavnet fulgt af suffix '_users'. Filnavn extension vil 
automatisk blive sat til<b>.csv</b>.</p>
<h6>User Group/brugergruppe</h6>
Kun brugere tilhørende den angivne gruppe vil blive 
eksporteret. Hvis 'all groups' er angivet vil brugere i destinationsfilen 
blive sorteret på brugergruppe/user group</p>
<h6>Felt separator</h6>
<p>Felt separator kan være enhver karakter, for eksempel komma semikolon eller andet tegn.
Felt separator tegnet skal være unikt 
og må ikke være del af teksten i nogle af felterne.</p><br>
<p>Eksisterende filer i 'files/' folderen på serveren med samme navn vil 
blive overskrevet af den nye fil.</p>
<p>Rækkefølgen af kolonner/felter i destinationsfilen vil være: group/gruppe ID, user/bruger name, 
email adresse, mobile nummer, interface language/sprog og password.<br>
<b>Note:</b> Passwords i den eksporterede fil er kodet og kan ikke 
afkodes.</p><br>
<p>Ved <b>downloading</b> af den eksporterede .csv fil, vil aktuel dato og tid 
blive en del af navnet på den downloadede/eksporterede fil.</p><br>
<h6>Eksempel på User Profile filer</h6>
<p>Eksempler på  User Profile files (file extension .csv) kan findes i '!luxcal-toolbox/' 
directory/mappen af/i dine LuxCal download/installationsfiler.</p>",

"xpl_import_ical" =>
"<h3>iCalendar import-vejledning</h3>
<p>Denne formular bruges til at importere en <strong>iCalendar</strong>-fil med begivenheder til LuxCal-kalender.</p>
<p>Filindholdet skal svare til standarden [<u><a href='https://tools.ietf.org/html/rfc5545' 
target='_blank'>RFC5545</a></u>] fra Internet Engineering Task Force.</p>
<p>Kun begivenheder importeres; andre iCal-komponenter, som: To-Do, Journal, Fri / optaget, Tidszone og Alarm, ignoreres.</p>
<p>Eksempel iCalendar-filer kan findes i folderen '!luxcal-toolbox/' i din LuxCal download.</p>
<h6>Tabel med kategorier</h6>
<p>Kalenderen bruger ID-numre til at angive kategorier. Kategori-ID'er i iCalendar-filen skal svare til kategorierne brugt i din kalender eller være tomme.</p>
<p class='hired'>Advarsel: Importer ikke mere end 100 begivenheder af gangen!</p>
<p>I din kalender er de følgende kategorier defineret i øjeblikket:</p>",

"xpl_export_ical" =>
"<h3>iCalendar eksport-vejledning</h3>
<p>Denne formular bruges til at udlæse og eksportere <strong>iCalendar</strong> begivenheder fra LuxCal kalenderen.</p>
<p><b>iCal filnavnet</b> (uden extension) er valgfrit. 
Oprettede filer bliver gemt med det angivne filnavn på serveren i folderen \"files/\", eller med kalenderens navn hvis filnavn ikke er angivet. Filens extension vil være <b>.ics</b>.
En evt. eksisterende fil med det samme navn i folderen \"!luxcal-toolbox/\" på serveren vil blive overskrevet af den nye fil.</p>
<p>iCal filbeskrivelsen (f.eks. 'Møder 2024') er valgfri. Hvis det indtastes, tilføjes det til headeren i den eksporterede iCal-fil.</p>
<p>Begivenhed filtre: De eksporterede begivenheder kan filtreres med:</p>
<ul>
<li>begivenhedsejer</li>
<li>begivenhedskategori</li>
<li>begivenhedsstartdato</li>
<li>begivenheds tilføjet/sidste ændringsdato</li>
</ul>
<p>Hvert filter er valgfrit. En blank dato betyder: ingen grænser</p>
<br>
<p>Indholdet af filen med udlæste begivenheder vil svare til standarden 
[<u><a href='https://tools.ietf.org/html/rfc5545' target='_blank'>RFC5545</a></u>] 
fra Internet Engineering Task Force.</p>
<p>Ved <b>download</b> af den eksporterede iCal fil vil dato og tid blive tilføjet til navnet på den downloadede fil.</p>
<p>Eksempel iCalendar-filer kan findes i folderen '!luxcal-toolbox/' i din LuxCal download.</p>",

"xpl_clean_up" =>
"<h3>Clean Up Instruktioner</h3>
<p>På denne side kan der ryddes op i følgende:</p>
<h6>Fortidige Events</h6>
<p>Events i denne kalender med en slutdato før den angivne, 
vil blive slettet fra kalenderen. Den angivne dato skal være mindst en måned 
før dags dato.</p>
<h6>Inaktive brugere</h6>
<p>Konti for brugere der ikke har logget ind i kalenderen siden den angivne dato,
vil blive fjernet fra kalenderen. Den angivne dato,
skal være mindst en måned før dags dato.</p>
<h6>Attachment folderen</h6>
<p>Attachment filerne som ikke er brugt i events siden den angivne dato,
vil blive slettet. Datoen skal være blank eller fortidig. I tilfælde af multi-kalendere, 
vil attachment filer blive tjekket i alle kalendere.</p>
<h6>Modtagerliste folder</h6>
<p>Modtagerliste filer som ikke har været brugt i events siden den angivne dato, 
vil blive slettet. Datoen skal være blank eller fortidig. I tilfælde af multi-kalendere, 
vil modtagerliste filerne blive tjekket i alle kalendere.</p>
<h6>Thumbnails folder</h6>
<p>Thumbnail filer som ikke er brugt i events siden den angivne dato,
og som ikke er brugt i sidepanelets info.txt fil,
vil blive slettet. Datoen skal være blank eller fortidig. I tilfælde af multi-kalendere, 
vil thumbnail filerne blive tjekket i alle kalendere.</p>"
);
?>
