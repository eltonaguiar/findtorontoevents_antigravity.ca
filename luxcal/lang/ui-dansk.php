<?php
/*
= LuxCal language file =

Additional Danish - John Schwartz. Sidst redigeret 21-12-2024

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "da";

/* -- Titles on the Header of the Calendar -- */

$months = array("Januar","Februar","Marts","April","Maj","Juni","Juli","August","September","Oktober","November","December");
$months_m = array("Jan","Feb","Mar","Apr","Maj","Jun","Jul","Aug","Sep","Okt","Nov","Dec");
$wkDays = array("Søndag","Mandag","Tirsdag","Onsdag","Torsdag","Fredag","Lørdag","Søndag");
$wkDays_l = array("Søn","Man","Tir","Ons","Tor","Fre","Lør","Søn");
$wkDays_m = array("Sø","Ma","Ti","On","To","Fr","Lø","Sø");
$wkDays_s = array("S","M","T","O","T","F","L","S");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Udfør",
"log_in" => "Log ind",
"log_out" => "Log ud",
"portrait" => "Stående",
"landscape" => "Liggende",
"none" => "Ingen.",
"all_day" => "All day",
"back" => "Tilbage",
"restart" => "Restart",
"by" => "af",
"of" => "i",
"max" => "max.",
"options" => "Valg",
"done" => "Udfør",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "Fra", //e.g. from 9:30
"until" => "Til", //e.g. until 15:30
"to" => "To", //e.g. to 17-02-2020
"birthdays_in" => "Fødselsdage i",
"open_calendar" => "Åbn kalender",
"no_way" => "Du har ikke autorisation til denne funktion",

//index.php
"title_log_in" => "Log ind",
"title_profile" => "Brugerprofil",
"title_upcoming" => "Kommende begivenheder",
"title_event" => "Begivenhed",
"title_check_event" => "Tjek begivenhed",
"title_dmarking" => "Dags markering",
"title_search" => "Tekst Søgning",
"title_contact" => "Kontakt Form",
"title_thumbnails" => "Thumbnail Images",
"title_user_guide" => "LuxCal brugervejledning",
"title_settings" => "Kalenderindstillinger",
"title_edit_cats" => "Editer kategorier",
"title_edit_users" => "Editer brugere",
"title_edit_groups" => "Editer Bruger Grupper",
"title_edit_text" => "Rediger Informationstekst",
"title_manage_db" => "Vedligehold databasen",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Tilføje / ændre / slette begivenheder",
"title_usr_import" => "User fil import - CSV format",
"title_usr_export" => "User fil eksport - CSV format",
"title_evt_import" => "Event fil-import - CSV format",
"title_ics_import" => "Event fil-import - iCal format",
"title_ics_export" => "Event fil-eksport - iCal format",
"title_msg_log" => "Notifikation besked Log",
"title_ui_styling" => "Bruger Interface Styling",
"title_bd_calendar" => "Fødselsdags kalender",

//header.php
"hdr_button_back" => "Tilbage til forrige side",
"hdr_options_submit" => "Foretag valg og klik 'Udfør'",
"hdr_options_panel" => "Valgmuligheder",
"hdr_select_date" => "Gå til dato ",
"hdr_calendar" => "Kalender",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Visning",
"hdr_lang" => "Sprog",
"hdr_all_cats" => "Alle kategorier",
"hdr_all_groups" => "Alle Grupper",
"hdr_all_users" => "Alle brugere",
"hdr_go_to_view" => "Gå til visning",
"hdr_view_1" => "År",
"hdr_view_2" => "Måned",
"hdr_view_3" => "Arbejdsmåned",
"hdr_view_4" => "Uge",
"hdr_view_5" => "Arbejdsuge",
"hdr_view_6" => "Dag",
"hdr_view_7" => "Kommende",
"hdr_view_8" => "Ændringer",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantt Chart",
"hdr_select_admin_functions" => "Vælg admin funktion",
"hdr_admin" => "Administration",
"hdr_settings" => "Indstillinger",
"hdr_categories" => "Kategorier",
"hdr_users" => "Brugere",
"hdr_groups" => "Bruger Grupper",
"hdr_text_editor" => "Teksteditor",
"hdr_database" => "Database",
"hdr_clean_up" => "Clean up",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "User Import (CSV file)",
"hdr_export_usr" => "User Export (CSV file)",
"hdr_import_csv" => "Event Import (CSV file)",
"hdr_import_ics" => "Event Import (iCal file)",
"hdr_export_ics" => "Event Export (iCal file)",
"hdr_msg_log" => "Besked Log",
"hdr_styling" => "Styling",
"hdr_back_to_cal" => "Tilbage til kalender visning",
"hdr_button_print" => "Udskriv",
"hdr_print_page" => "Udskriv denne side",
"hdr_button_pdf" => "PDF Fil - Events",
"hdr_button_pdf_bc" => "PDF Fil - Fødselsdage",
"hdr_dload_pdf" => "Download events displayed",
"hdr_dload_pdf_bc" => "Download fødselsdags kalender",
"hdr_button_contact" => "Kontakt",
"hdr_contact" => "Kontakt Administrator",
"hdr_button_tnails" => "Thumbnails",
"hdr_tnails" => "Vis thumbnails",
"hdr_button_toap" => "Godkend",
"hdr_toap_list" => "Events til godkendelse",
"hdr_button_todo" => "Opgaver",
"hdr_todo_list" => "Opgaveliste",
"hdr_button_upco" => "Kommende",
"hdr_upco_list" => "Kommende begivenheder",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Søg",
"hdr_search" => "Tekst søgning",
"hdr_button_add" => "Tilføj",
"hdr_add_event" => "Tilføj begivenhed",
"hdr_button_help" => "Hjælp",
"hdr_user_guide" => "Brugervejledning",
"hdr_gen_guide" => "Generel brugervejledning",
"hdr_cs_guide" => "Context-sensitiv bruger beskrivelse",
"hdr_gen_help" => "General help",
"hdr_prev_help" => "Forrige help",
"hdr_open_menu" => "Åben Menu",
"hdr_side_menu" => "Side Menu",
"hdr_dest_cals" => "Destination kalender(e)",
"hdr_copy_evt" => "Kopier Event",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "i dag", //dtpicker.js
"hdr_clear" => "slette", //dtpicker.js

//event.php
"evt_no_title" => "Ingen titel",
"evt_no_start_date" => "Ingen startdato",
"evt_bad_date" => "Forkert dato",
"evt_bad_rdate" => "Forkert gentagelse slutdato",
"evt_no_start_time" => "Ingen starttid",
"evt_bad_time" => "Forkert tid",
"evt_end_before_start_time" => "Sluttid før starttid",
"evt_end_before_start_date" => "Slutdato før startdato",
"evt_until_before_start_date" => "Gentagelse slutdato før startdato",
"evt_default_duration" => "Default event varighed på $1 time(r) og $2 minut(ter)",
"evt_fixed_duration" => "Fixed event varighed på $1 time(r) og $2 minut(ter)",
"evt_approved" => "Begivenhed godkendt",
"evt_apd_locked" => "Begivenhed godkendt og låst",
"evt_title" => "Titel",
"evt_venue" => "Sted",
"evt_address_button" => "En adresse mellem ! (udråbstegn) bliver en `adresseknap`",
"evt_list" => "Liste",
"evt_category" => "Kategori",
"evt_subcategory" => "Subcategory",
"evt_description" => "Beskrivelse",
"evt_attachments" => "Attachments",
"evt_attach_file" => "Attach fil",
"evt_click_to_open" => "Click for at åbne",
"evt_click_to_remove" => "Click for at slette",
"evt_no_pdf_img_vid" => "Attachment skal være pdf, billede eller video",
"evt_error_file_upload" => "Error uploading file",
"evt_upload_too_large" => "Uploaded fil for stor",
"evt_date_time" => "Dato / tid",
"evt_date" => "Dato",
"evt_private" => "Privat begivenhed",
"evt_start_date" => "Start",
"evt_end_date" => "Slut",
"evt_select_date" => "Vælg dato",
"evt_select_time" => "Vælg tid",
"evt_all_day" => "Hele dagen",
"evt_no_time" => "Ingen tid",
"evt_change" => "Ændre",
"evt_set_repeat" => "Sæt gentagelse",
"evt_set" => "OK",
"evt_help" => "hjælp",
"evt_repeat_not_supported" => "Angivet gentagelse ikke understøttet",
"evt_no_repeat" => "Ingen gentagelse",
"evt_rolling" => "Rolling",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Gentag hver",
"evt_until" => "indtil",
"evt_blank_no_end" => "blank: ingen ende",
"evt_each_month" => "hver måned",
"evt_interval2_1" => "første",
"evt_interval2_2" => "anden",
"evt_interval2_3" => "tredje",
"evt_interval2_4" => "fjerde",
"evt_interval2_5" => "sidste",
"evt_period1_1" => "dag",
"evt_period1_2" => "uge",
"evt_period1_3" => "måned",
"evt_period1_4" => "år",
"evt_notification" => "Meddelelse",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "nu og/eller",
"evt_event_added" => "Begivenhed blev oprettet",
"evt_event_edited" => "Begivenhed blev opdateret",
"evt_event_deleted" => "Begivenhed blev slettet",
"evt_event_approved" => "Begivenhed blev godkendt",
"evt_days_before_event" => "dag(e) før begivenheden",
"evt_to" => "Til",
"evt_not_help" => "Modtagerliste adskilt af semikolon. En modtageradresse kan være et brugernavn, et emailadresse, et mobilnummer, et Telegram chat ID eller, mellem square bracktes, navnet på en .txt fil med adresser i 'reciplists' folderen, med een adresse (en username, et emailadresse et mobilnummer eller Telegram chat ID) per linie.<br>Maximum field længde: 255 karakterer.",
"evt_recip_list_too_long" => "adresselisten er for lang.",
"evt_no_recip_list" => "Listen modtagere er tom",
"evt_not_in_past" => "Påmindelsesdato før dags dato",
"evt_not_days_invalid" => "Påmindelsesdage ugyldig",
"evt_status" => "Status",
"evt_descr_help" => "Følgende koder kan bruges i beskrivelsesfeltet ...<br>• HTML tags &lt;b&gt;, &lt;i&gt;, &lt;u&gt; og &lt;s&gt; for fed, kursiv, understreget og gennemstreget tekst.",
"evt_descr_help_img" => "• små billeder (thumbnails) i format: 'bilede_navn.ext'. The thumbnail files, with file extension .gif, .jpg or .png, must be present in 'thumbnails' folder. If enabled, the Thumbnails page can be used to upload thumbnail files.",
"evt_descr_help_eml" => "• Mailto-links i format: 'email adres' eller 'email adres [name]', where 'name' will be the title of the link. E.g. xxx@yyyy.zzz [For info click here].",
"evt_descr_help_url" => "• URL links i format: 'url' eller 'url [navn]', hvor 'navn' vises som titel for linket. If 'S:' is placed in front of the URL, the link will open in the same page/tab, otherwise the link will open in a blank page/tab. Fx S:https://www.google.com [Søgning].",
"evt_confirm_added" => "begivenhed tilføjet",
"evt_confirm_saved" => "begivenhed gemt",
"evt_confirm_deleted" => "begivenhed slettet",
"evt_add_close" => "Tilføj og luk",
"evt_add" => "Tilføj",
"evt_edit" => "Editer",
"evt_save_close" => "Gem og luk",
"evt_save" => "Gem",
"evt_clone" => "Gem som Ny",
"evt_delete" => "Slet",
"evt_close" => "Luk",
"evt_owner" => "Ejer",
"evt_added" => "Tilføjet",
"evt_edited" => "Ændret",
"evt_is_repeating" => "er en gentaget begivenhed.",
"evt_is_multiday" => "er en flerdages begivenhed.",
"evt_edit_series_or_occurrence" => "Vil du editere serien eller denne forekomst?",
"evt_edit_series" => "Editer serien",
"evt_edit_occurrence" => "Editer denne forekomst",
"evt_select_from_list" => "Vælg modtagere fra liste",
"evt_select_recips" => "Vælg modtagere",
"evt_recip_lists" => "Liste med modtagere",
"evt_regist_recips" => "Registrerede modtagere",
"evt_public_recips" => "Public modtagere",

//events - dmark specific
"mrk_text_and_color" => "Tekst og farve",
"mrk_is_repeating" => "er en repeating markering",
"mrk_is_multiday" => "er en  multi-day markering",
"mrk_text" => "Tekst",
"mrk_color" => "Farve",
"mrk_background" => "Baggrund",
"mrk_select_color" => "vælg farve",
"mrk_start_date" => "Start dato",
"mrk_end_date" => "End dato",
"mrk_dmark_added" => "Ny dag markering",
"mrk_dmark_edited" => "Ændret dag markering",
"mrk_dmark_deleted" => "Slettet dag markering",
"mrk_dates" => "Dato(er)",

//views
"vws_add_event" => "Tilføj begivenhed",
"vws_edit_event" => "Edit Event",
"vws_see_event" => "Se event detaljer",
"vws_view_month" => "Vis måned",
"vws_view_week" => "Vis uge",
"vws_view_day" => "Vis dag",
"vws_click_for_full" => "for fuld kalender, klik måned",
"vws_view_full" => "Vis fuld kalender",
"vws_prev_year" => "Forrige år",
"vws_next_year" => "Forrige år",
"vws_prev_month" => "Forrige måned",
"vws_next_month" => "Næste måned",
"vws_forward" => "Fremad",
"vws_backward" => "Bagud",
"vws_mark_day" => "Mark dag",
"vws_today" => "Dag",
"vws_back_to_today" => "Tilbage til måneden for dags dato",
"vws_back_to_main_cal" => "Tilbage til hovedkalenderens måned",
"vws_week" => "Uge",
"vws_wk" => "Uge",
"vws_time" => "Tid",
"vws_events" => "Begivenheder",
"vws_all_day" => "Hele dagen",
"vws_earlier" => "Tidligere",
"vws_later" => "Senere",
"vws_venue" => "Sted",
"vws_address" => "Adresse",
"vws_events_for_next" => "Kommende begivenheder for de næste",
"vws_days" => "dag(e)",
"vws_added" => "Tilføjet",
"vws_edited" => "Ændret",
"vws_notify" => "Alarmer",
"vws_none_due_in" => "Ingen begivenheder den følgende",
"vws_evt_cats" => "Event kategorier",
"vws_cal_users" => "Calender brugere",
"vws_no_users" => "Ingen brugere i udvalgt gruppe(r)",
"vws_start" => "Start",
"vws_duration" => "Varighed",
"vws_no_events_in_gc" => "Ingen begivenheder i valgte periode",
"vws_download" => "Download",
"vws_download_title" => "Download en fil med disse begivenheder",
"vws_send_mail" => "Send email",

//changes.php
"chg_select_date" => "Vælg startdato",
"chg_notify" => "Alarmer",
"chg_days" => "Dag(e)",
"chg_added" => "Tilføjet",
"chg_edited" => "Ændret",
"chg_deleted" => "Slettet",
"chg_changed_on" => "Ændret",
"chg_no_changes" => "Ingen ændringer.",

//search.php
"sch_define_search" => "Definer søgning",
"sch_search_text" => "Søgetekst",
"sch_event_fields" => "Begivenhedsfelter",
"sch_all_fields" => "Alle felter",
"sch_title" => "Titel",
"sch_description" => "Beskrivelse",
"sch_venue" => "Sted",
"sch_user_group" => "Bruger Gruppe",
"sch_event_cat" => "Begivenhedskategori",
"sch_all_groups" => "Alle Grupper",
"sch_all_cats" => "Alle kategorier",
"sch_occurring_between" => "Foregår mellem",
"sch_select_start_date" => "Vælg startdato",
"sch_select_end_date" => "Vælg slutdato",
"sch_search" => "Søg",
"sch_invalid_search_text" => "Søgetekst mangler eller for kort",
"sch_bad_start_date" => "Ugyldig startdato",
"sch_bad_end_date" => "Ugyldig slutdato",
"sch_no_results" => "Ingen resultater",
"sch_new_search" => "Ny Søgning",
"sch_calendar" => "Gå til kalender",
"sch_extra_field1" => "Ekstra felt 1",
"sch_extra_field2" => "Ekstra felt 2",
"sch_sd_events" => "Single-day events",
"sch_md_events" => "Multi-day events",
"sch_rc_events" => "Recurring events",
"sch_instructions" =>
"<h3>Tekst Søgning vejledning</h3>
<p>Der kan søges i kalenderdatabasen efter begivenheder som matcher specifik tekst.</p>
<br><p><b>Søgetekst</b>: Der søges i de valgte felter (se nedenfor) i hver begivenhed. Søgning tager ikke hensyn til store eller små bogstaver (er ikke case sensitiv).</p>
<p>To jokertegn (wildcard) kan bruges:</p>
<ul>
<li>Et spørgsmålstegn (?) i søgeteksten vil matche ethvert enkelt tegn.<br>Fx: '?e?r' matcher 'sejr', 'Vejr', 'lejr'.</li>
<li>En asterisk (*) i søgeteksten vil matche ethvert antal tegn.<br>Fx: 'de*r' matcher 'December', 'deler', 'deltager'.</li>
</ul>
<br><p><b>Begivenhedsfelter</b>: Der søges kun i de valgte felter.</p>
<br><p><b>User group</b>: Kun begivenheder i den valgte bruger gruppe vil blive gennemsøgt.</p>
<br><p><b>Begivenhedskategori</b>: Der søges kun begivenheder i den valgte kategori.</p>
<br><p><b>Foregår mellem</b>: Start og slutdato er begge valgfri. I tilfælde af blank start / end dato, vil default antal dage frem og tilbage være henholdsvis $1 dage og $2 dage.</p>
<br><p>For at undgå repetitioner af samme event, vil søgeresultaterne blive opsplittet i single-day events, multi-day events og recurring events.</p>
<p>Søgeresultaterne vil blive vist i kronologisk orden.</p>",

//thumbnails.php
"tns_man_tnails_instr" => "Instruktioner til håndtering af thumbnails",
"tns_help_general" => "Billeder herunder, kan bruges i kelender visninger, ved at indsætte deres filnavn i eventbeskrivelsen eller i et af ekstrafelterne ELLER : et filnavn kan kopieres til udklipholderen ved at klikke på billedet og herefter kan filnavnet indsættes i en event ved at placere cursoren hvor billedet ønskes, og der trykkes så CTRL+V. Under hver thumbnail kan ses : Filnavn ( uden ID som prefix ), Fil dato, og imellem parantser ses dato på event hvor den sidst er anvendt.",
"tns_help_upload" => "Thumbnails kan uploades fra lokal computer ved at vælge 'Vælg filer' knappen. For at vælge flere filer : hold CTRL nede og klik på filerne ( max 20 ). Følgende filtyper accepteres: $1. Thumbnails der er større end $2 x $3 pixels (bredde x højde) vil automatisk blive resized.",
"tns_help_delete" => "Thumbnails med et rødt kryds i øverste venstre hjørne, kan slettes ved at klikke på krydset. Thumbnails uden det røde kryds kan ikke slettes, fordi de stadig bruges efter $1 . Advarsel: Slettede thumbnails kan ikke gendannes! ( medmindre de uploades igen ).",
"tns_your_tnails" => "Dine thumbnails",
"tns_other_tnails" => "Andre thumbnails",
"tns_man_tnails" => "Håndter Thumbnails",
"tns_sort_by" => "Sorter efter",
"tns_sort_order" => "Sorteringsorden",
"tns_search_fname" => "Søg filnavn",
"tns_upload_tnails" => "Upload thumbnails",
"tns_name" => "Navn",
"tns_date" => "Dato",
"tns_ascending" => "Stigende",
"tns_descending" => "Faldende",
"tns_not_used" => "Ikke brugt",
"tns_infinite" => "infinite",
"tns_del_tnail" => "Slet thumbnail",
"tns_tnail" => "Thumbnail",
"tns_deleted" => "Slettet",
"tns_tn_uploaded" => "thumbnail(s) uploaded",
"tns_overwrite" => "Tillad overskrivning",
"tns_tn_exists" => "Thumbnail findes allerede – ikke uploaded",
"tns_upload_error" => "upload error",
"tns_no_valid_img" => "Ikke valid image",
"tns_file_too_large" => "fil for stor",
"tns_resized" => "resized",
"tns_resize_error" => "resize error",

//contact.php
"con_msg_to_admin" => "Besked til Administrator",
"con_from" => "fra",
"con_name" => "Navn",
"con_email" => "Email",
"con_subject" => "Emne",
"con_message" => "Besked",
"con_send_msg" => "Send besked",
"con_fill_in_all_fields" => "Venligst udfyld alle felter",
"con_invalid_name" => "Ugyldigt navn",
"con_invalid_email" => "Ugyldig email adresse",
"con_no_urls" => "Weblinks ikke tilladt",
"con_mail_error" => "Email problem. Beskeden kunne ikke sendes. Prøv venligst igen,senere.",
"con_con_msg" => "Kontakt besked fra kalenderen",
"con_thank_you" => "Tak for din besked vedrørende kalenderen",
"con_get_reply" => "Du vil modtage et svar på din henvendelse, snarest muligt.",
"con_date" => "Dato",
"con_your_msg" => "Din besked",
"con_your_cal_msg" => "Din besked til kalenderen",
"con_has_been_sent" => "er blevet sendt til kalenderens administrator",
"con_confirm_eml_sent" => "En kvitterings email er blevet sendt til",

//msglog.php
"msl_search" => "Søg",
"msl_date" => "dato",
"msl_text" => "tekst",
"msl_sent_msgs" => "Sendte notifikation beskeder",
"msl_no_logs_found" => "Ingen besked logs fundet!",
"msl_errors" => "DER OPSTOD FEJL! Se luxcal log",

//alert.php
"alt_message#0" => "Vil din session snart udløbe!",
"alt_message#1" => "PHP SESSION ER UDLØBET",
"alt_message#2" => "Venligst genstart Kalenderen",
"alt_message#3" => "UGYLDIG FORESPØRGSEL",

//stand-alone sidebar (lcsbar.php)
"ssb_upco_events" => "Kommende begivenheder",
"ssb_all_day" => "Hele dagen",
"ssb_none" => "Ingen begivenheder."
);
?>
