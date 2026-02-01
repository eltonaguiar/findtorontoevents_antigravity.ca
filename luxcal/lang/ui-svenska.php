<?php
/*
= LuxCal lamguage file =

This file has been produced by LuxSoft. Please send comments / improvements to rb@luxsoft.eu.
Translation to swedish by Christer "Scunder" Nordahl.

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "sv";

/* -- Titles on the Header of the Calendar -- */

$months = array("Januari","Februari","Mars","April","Maj","Juni","Juli","Augusti","September","Oktober","November","December");
$months_m = array("Jan","Feb","Mar","Apr","Maj","Jun","Jul","Aug","Sep","Okt","Nov","Dec");
$wkDays = array("Söndag","Måndag","Tisdag","Onsdag","Torsdag","Fredag","Lördag","Söndag");
$wkDays_l = array("Sön","Mån","Tis","Ons","Tor","Fre","Lör","Sön");
$wkDays_m = array("Sö","Må","Ti","On","To","Fr","Lö","Sö");
$wkDays_s = array("S","M","T","O","T","F","L","S");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Skicka",
"log_in" => "Logga in",
"log_out" => "Logga ut",
"portrait" => "Portrait",
"landscape" => "Landscape",
"none" => "Ingen.",
"all_day" => "Alla dagar",
"back" => "Tillbaka",
"restart" => "Restart",
"by" => "av",
"of" => "av",
"max" => "max.",
"options" => "Alternativ",
"done" => "Klar",
"at_time" => "kl", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "Från", //e.g. from 9:30
"until" => "Till", //e.g. until 15:30
"to" => "To", //e.g. to 17-02-2020
"birthdays_in" => "Födelsedagar i",
"open_calendar" => "Öppna kalender",
"no_way" => "Du har inte rättighet att göra detta",

//index.php
"title_log_in" => "Logga in",
"title_profile" => "Användar profil",
"title_upcoming" => "Kommande händelser",
"title_event" => "Händelse",
"title_check_event" => "Kontrollera händelse",
"title_dmarking" => "Day Marking",
"title_search" => "Sök text",
"title_contact" => "Kontakt Formulär",
"title_thumbnails" => "Miniatyrbilder",
"title_user_guide" => "Användarhandbok",
"title_settings" => "Kalenderinställningar",
"title_edit_cats" => "Redigera kategorier",
"title_edit_users" => "Redigera användare",
"title_edit_groups" => "Redigera användargrupper",
"title_edit_text" => "Redigera Information Text",
"title_manage_db" => "Hantera databas",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Sparade/Redigerade/Raderade händelser",
"title_usr_import" => "Användar Fil Import - CSV format",
"title_usr_export" => "Användar Fil Export - CSV format",
"title_evt_import" => "Händelse Fil Import - CSV format",
"title_ics_import" => "Händelse Fil Import - iCal format",
"title_ics_export" => "Händelse Fil Export - iCal format",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "Styling av användargränssnitt",
"title_bd_calendar" => "Födelsedagskalender",

//header.php
"hdr_button_back" => "Tillbaka till ursprunglig sida",
"hdr_options_submit" => "Gör ditt val och klicka 'Klar'",
"hdr_options_panel" => "Alternativ-menyer",
"hdr_select_date" => "Välj datum",
"hdr_calendar" => "Kalender",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Visa",
"hdr_lang" => "Språk",
"hdr_all_cats" => "Alla kategorier",
"hdr_all_groups" => "Alla Grupper",
"hdr_all_users" => "Alla användare",
"hdr_go_to_view" => "Gå till vy",
"hdr_view_1" => "År",
"hdr_view_2" => "Månad",
"hdr_view_3" => "Arbetsmånad",
"hdr_view_4" => "Vecka",
"hdr_view_5" => "Arbetsvecka",
"hdr_view_6" => "Dag",
"hdr_view_7" => "Kommande",
"hdr_view_8" => "Ändringar",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantlett-diagram",
"hdr_select_admin_functions" => "Välj administrativ funktion",
"hdr_admin" => "Administration",
"hdr_settings" => "Inställningar",
"hdr_categories" => "Kategorier",
"hdr_users" => "Användare",
"hdr_groups" => "Användargrupper",
"hdr_text_editor" => "Text Redigerare",
"hdr_database" => "Databas",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "Användar Import (CSV fil)",
"hdr_export_usr" => "Användar Export (CSV fil)",
"hdr_import_csv" => "Händelse Import (CSV fil)",
"hdr_import_ics" => "Händelse Import (iCal fil)",
"hdr_export_ics" => "Händelse Export (iCal fil)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Styling",
"hdr_back_to_cal" => "Tillbaka till kalender",
"hdr_button_print" => "Skriv ut",
"hdr_print_page" => "Skriv ut sida",
"hdr_button_pdf" => "PDF Fil - Händelser",
"hdr_button_pdf_bc" => "PDF Fil - Födelsedagar",
"hdr_dload_pdf" => "Ladda ner kommande evenet",
"hdr_dload_pdf_bc" => "Ladda ner födelsedagskalender",
"hdr_button_contact" => "Kontakt",
"hdr_contact" => "Kontakta administratören",
"hdr_button_tnails" => "Miniatyrer",
"hdr_tnails" => "Visa miniatyrer",
"hdr_button_toap" => "Godkänna",
"hdr_toap_list" => "Händelse att godkännas",
"hdr_button_todo" => "Att-göra",
"hdr_todo_list" => "Att-göra lista",
"hdr_button_upco" => "Kommande",
"hdr_upco_list" => "Kommande händelser",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Sök",
"hdr_search" => "Sök text",
"hdr_button_add" => "Skapa",
"hdr_add_event" => "Skapa händelse",
"hdr_button_help" => "Hjälp",
"hdr_user_guide" => "Användarhandbok",
"hdr_gen_guide" => "Allmän användarhandbok",
"hdr_cs_guide" => "Kontextkänslig användarhandbok",
"hdr_gen_help" => "Generell hjälp",
"hdr_prev_help" => "Tidigare hjälp",
"hdr_open_menu" => "Öppna meny",
"hdr_side_menu" => "Meny",
"hdr_dest_cals" => "Destination Calendar(s)",
"hdr_copy_evt" => "Copy Event",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "idag", //dtpicker.js
"hdr_clear" => "rensa", //dtpicker.js

//event.php
"evt_no_title" => "Titel saknas",
"evt_no_start_date" => "Startdatum saknas",
"evt_bad_date" => "Felaktigt datum",
"evt_bad_rdate" => "Felaktigt slutdatum för repetition",
"evt_no_start_time" => "Starttid saknas",
"evt_bad_time" => "Felaktid tidsangivelse",
"evt_end_before_start_time" => "Sluttid före starttid",
"evt_end_before_start_date" => "Slutdatum före startdatum",
"evt_until_before_start_date" => "Repetition slut före startdatum",
"evt_default_duration" => "Standardhändelselängd på $1 timmar och $2 minuter",
"evt_fixed_duration" => "Fast händelselängd på $1 timmar och $2 minuter",
"evt_approved" => "Händelse godkänd",
"evt_apd_locked" => "Händelse godkänd och låst",
"evt_title" => "Titel",
"evt_venue" => "Plats",
"evt_address_button" => "En adress mellan ! tecken blir en knapp",
"evt_list" => "List",
"evt_category" => "Kategori",
"evt_subcategory" => "Underkategori",
"evt_description" => "Beskrivning",
"evt_attachments" => "Bilagor",
"evt_attach_file" => "Bifoga fil",
"evt_click_to_open" => "Klicka för att öppna",
"evt_click_to_remove" => "Klicka för att ta bort",
"evt_no_pdf_img_vid" => "Bilaga ska vara pdf, bild eller video",
"evt_error_file_upload" => "Det gick inte att ladda upp filen",
"evt_upload_too_large" => "Uppladdad fil för stor",
"evt_date_time" => "Datum / tid",
"evt_date" => "Datum",
"evt_private" => "Privat händelse",
"evt_start_date" => "Start",
"evt_end_date" => "Slut",
"evt_select_date" => "Välj datum",
"evt_select_time" => "Välj tid",
"evt_all_day" => "Heldag",
"evt_no_time" => "Ingen tid",
"evt_change" => "Ändra",
"evt_set_repeat" => "Ställ repetition",
"evt_set" => "OK",
"evt_help" => "Hjälp",
"evt_repeat_not_supported" => "Angiven repetition stöds inte",
"evt_no_repeat" => "Ingen repetition",
"evt_rolling" => "Rullande",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Repetera var",
"evt_until" => "tills",
"evt_blank_no_end" => "blankt: tills vidare",
"evt_each_month" => "varje månad",
"evt_interval2_1" => "första",
"evt_interval2_2" => "andra",
"evt_interval2_3" => "tredje",
"evt_interval2_4" => "fjärde",
"evt_interval2_5" => "sista",
"evt_period1_1" => "dag(ar)",
"evt_period1_2" => "vecka(or)",
"evt_period1_3" => "månad(er)",
"evt_period1_4" => "år",
"evt_notification" => "Anmälan",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "nu och/eller",
"evt_event_added" => "Ny händelse",
"evt_event_edited" => "Ändrad händelse",
"evt_event_deleted" => "Raderad händelse",
"evt_event_approved" => "Godkänd händelse",
"evt_days_before_event" => "dag(ar) före händelsen",
"evt_to" => "Till",
"evt_not_help" => "Lista över mottagaradresser separerade med semikolon. En mottagaradress kan vara ett användarnamn, en e-postadress, ett mobiltelefonnummer, en Telegram chat ID eller, omgiven av hakparenteser, namnet (without type) på en .txt fil med adresser i katalogen 'reciplists', med en adress (ett användarnamn, en e-postadress). adress eller ett mobiltelefonnummer, en Telegram chat ID) per rad.<br>Maximal fältlängd: 255 tecken.",
"evt_recip_list_too_long" => "Fältet för adresser har för många tecken (max 255 tecken).",
"evt_no_recip_list" => "Det saknas för meddelande",
"evt_not_in_past" => "Meddelandedatum har passerat",
"evt_not_days_invalid" => "Meddelandedagar ogiltiga",
"evt_status" => "Status",
"evt_descr_help" => "Följande teckenkoder kan användas i beskrivningen ...<br>• HTML tags &lt;b&gt;, &lt;i&gt;, &lt;u&gt; och &lt;s&gt; för fet, kursiv, understruken och överstruken text.",
"evt_descr_help_img" => "• små bilder (miniatyrer) i följande format: 'bild_namn.ext'. Miniatyrfilerna, med filtillägget .gif, .jpg eller .png, måste finnas i mappen 'thumbnails'. Om den är aktiverad kan sidan med miniatyrbilder användas för att ladda upp miniatyrbilder.",
"evt_descr_help_eml" => "• Mailto-links i följande format: 'email address' eller 'email address [namn]', där 'namn' blir länkens titel. E.g. xxx@yyyy.zzz [Klicka här för info].",
"evt_descr_help_url" => "• URL-länkar i följande format: 'url' eller 'url [namn]', där 'namn' blir länkens titel. If 'S:' placeras framför URL:en öppnas länken på samma sida/flik, annars öppnas länken på en tom sida/flik. T.ex. S:https://www.google.com [sök].",
"evt_confirm_added" => "händelse skapad",
"evt_confirm_saved" => "händelse sparad",
"evt_confirm_deleted" => "händelse raderad",
"evt_add_close" => "Spara och stäng",
"evt_add" => "Spara",
"evt_edit" => "Redigera",
"evt_save_close" => "Spara och stäng",
"evt_save" => "Spara",
"evt_clone" => "Spara som ny",
"evt_delete" => "Radera",
"evt_close" => "Stäng",
"evt_added" => "Skapad",
"evt_edited" => "Redigerad",
"evt_is_repeating" => "är en repetativ händelse.",
"evt_is_multiday" => "är en flerdygns-händelse.",
"evt_edit_series_or_occurrence" => "Vill du ändra i hela händelseserien eller bara denna enstaka händelsen?",
"evt_edit_series" => "Ändra serien",
"evt_edit_occurrence" => "Ändra denna enstaka händelse",
"evt_select_from_list" => "Select recipients from list",
"evt_select_recips" => "Select Recipients",
"evt_recip_lists" => "Lists with Recipients",
"evt_regist_recips" => "Registered Recipients",
"evt_public_recips" => "Public Recipients",

//events - dmark specific
"mrk_text_and_color" => "Text och färg",
"mrk_is_repeating" => "är en återkommande markering",
"mrk_is_multiday" => "är en flerdagarsmarkering",
"mrk_text" => "Text",
"mrk_color" => "Färg",
"mrk_background" => "Bakgrund",
"mrk_select_color" => "välj färg",
"mrk_start_date" => "Start datum",
"mrk_end_date" => "Slut datum",
"mrk_dmark_added" => "Ny dagsmarkering",
"mrk_dmark_edited" => "Ändrad dagsmarkering",
"mrk_dmark_deleted" => "Raderad dagmarkering",
"mrk_dates" => "Datum",

//views
"vws_add_event" => "Skapa händelse",
"vws_edit_event" => "Redigera händelse",
"vws_see_event" => "Se händelsedetaljer",
"vws_view_month" => "Visa månad",
"vws_view_week" => "Visa vecka",
"vws_view_day" => "Visa dag",
"vws_click_for_full" => "för stor kalender klicka månad",
"vws_view_full" => "Visa stora kalendern",
"vws_prev_year" => "Föregående år",
"vws_next_year" => "Nästa år",
"vws_prev_month" => "Föregående månad",
"vws_next_month" => "Nästa månad",
"vws_forward" => "Framåt",
"vws_backward" => "Bakåt",
"vws_mark_day" => "Markera dagen",
"vws_today" => "Idag",
"vws_back_to_today" => "Tillbaka till aktuell månad",
"vws_back_to_main_cal" => "Tillbaka till huvudkalendermånaden",
"vws_week" => "Vecka",
"vws_wk" => "v.",
"vws_time" => "Tid",
"vws_events" => "Händelser",
"vws_all_day" => "Heldag",
"vws_earlier" => "Tidigare",
"vws_later" => "Senare",
"vws_venue" => "Plats",
"vws_address" => "Address",
"vws_events_for_next" => "Kommande händelser för följande",
"vws_days" => "dag(ar)",
"vws_added" => "Skapad",
"vws_edited" => "Redigerad",
"vws_notify" => "Meddela",
"vws_none_due_in" => "Inga förestående händelser inom följande",
"vws_evt_cats" => "Händelsekategorier",
"vws_cal_users" => "Kalenderanvändare",
"vws_no_users" => "Inga användare i den valda gruppen/grupperna",
"vws_start" => "Start",
"vws_duration" => "Varaktighet",
"vws_no_events_in_gc" => "Inga händelser under den valda perioden",
"vws_download" => "Ladda ned",
"vws_download_title" => "Ladda ned en fil med dessa händelser",
"vws_send_mail" => "Skicka email",

//changes.php
"chg_select_date" => "Välj startdatum",
"chg_notify" => "Meddela",
"chg_days" => "Dag(ar)",
"chg_added" => "Skapad",
"chg_edited" => "Redigerad",
"chg_deleted" => "Raderad",
"chg_changed_on" => "Ändrad den",
"chg_no_changes" => "Inga ändringar.",

//search.php
"sch_define_search" => "Definiera sökning",
"sch_search_text" => "Sök text",
"sch_event_fields" => "Händelsefält",
"sch_all_fields" => "Alla fält",
"sch_title" => "Titel",
"sch_description" => "Beskrivning",
"sch_venue" => "Plats",
"sch_user_group" => "Användargrupp",
"sch_event_cat" => "Händelsekategori",
"sch_all_groups" => "Alla grupper",
"sch_all_cats" => "Alla kategorier",
"sch_occurring_between" => "Inträffar mellan",
"sch_select_start_date" => "Välj startdatum",
"sch_select_end_date" => "Välj slutdatum",
"sch_search" => "Sök",
"sch_invalid_search_text" => "Söktext saknas eller är för kort",
"sch_bad_start_date" => "Felaktigt startdatum",
"sch_bad_end_date" => "Felaktigt slutdatum",
"sch_no_results" => "Inga resultat funna",
"sch_new_search" => "Ny sökning",
"sch_calendar" => "Gå till kalender",
"sch_extra_field1" => "Extra fält 1",
"sch_extra_field2" => "Extra fält 2",
"sch_sd_events" => "Endagshändelser",
"sch_md_events" => "Flerdagarshändelse",
"sch_rc_events" => "Återkommande händelser",
"sch_instructions" =>
"<h3>Instruktioner för textsökning</h3>
<p>Kalenderns databas kan genomsökas efter händelser med specifik text.</p>
<br><p><b>Söktext</b>: De valda fälten (se nedan) i varje händelse kommer att 
genomsökas. Sökningen skiljer INTE på små/STORA bokstäver.</p>
<p>Två jokertecken kan användas i söksträngen:</p>
<ul>
<li>Ett frågetecken (?) i söktexten matchar ett enstaka 
tecken.<br>T.ex. : '?e?r' matchar 'beer', 'dear', 'heir'.</li>
<li>En asterisk som (*) i söktexten matchar ett antal olika 
tecken.<br>E.g.: 'de*r' matchar 'December', 'dear', 'developer'.</li>
</ul>
<br><p><b>Händelsefält</b>: Endast de valda fälten genomsöks.</p>
<br><p><b>Användargrupp</b>: Händelser i den valda användargruppen kommer endast att genomsökas.</p>
<br><p><b>Händelsekategori</b>: Endast fält med den valda kategorin genomsöks.</p>
<br><p><b>Inträffar mellan</b>: Start- och slutdatum anges frivilligt. Om
av ett tomt start-/slutdatum, standardantalet dagar för att söka fram och tillbaka
kommer att vara $1 dagar respektive $2 dagar.</p>
<br><p>För att undvika upprepningar av samma händelse delas sökresultaten
i endagsevenemang, flerdagarsevenemang och återkommande evenemang.</p>
<p>Sökresultaten visas i kronologisk ordning.</p>",

//thumbnails.php
"tns_man_tnails_instr" => "Instruktioner för hantering av miniatyrbilder",
"tns_help_general" => "Bilderna nedan kan användas i kalendervyerna, genom att infoga deras filnamn i händelsens beskrivningsfält eller i något av de extra fälten. Ett bildfilnamn kan kopieras till urklippet genom att klicka på önskad miniatyrbild nedan; därefter, i händelsefönstret, kan bildnamnet infogas i ett av fälten genom att skriva CTRL-V. Under varje miniatyrbild hittar du: filnamnet (utan användar-ID-prefix), fildatum och mellan parentes det datum då miniatyren senast används av kalendern.",
"tns_help_upload" => "Miniatyrer kan laddas upp från din lokala dator genom att välja knappen Bläddra. För att välja flera filer, håll ned CTRL eller SHIFT medan du väljer (max. 20 åt gången). Följande filtyper accepteras: $1. Miniatyrer med en storlek större än $2 x $3 pixlar (b x h) ändras automatiskt.",
"tns_help_delete" => "Miniatyrbilder med ett rött kryss i det övre vänstra hörnet kan raderas genom att markera detta kryss. Miniatyrer utan rött kors kan inte raderas, eftersom de fortfarande används efter $1. Varning: Raderade miniatyrer kan inte hämtas!",
"tns_your_tnails" => "Dina miniatyrer",
"tns_other_tnails" => "Andra miniatyrer",
"tns_man_tnails" => "Hantera miniatyrer",
"tns_sort_by" => "Sortera efter",
"tns_sort_order" => "Sorteringsordning",
"tns_search_fname" => "Sök filnamn",
"tns_upload_tnails" => "Ladda upp miniatyrer",
"tns_name" => "namn",
"tns_date" => "datum",
"tns_ascending" => "stigande",
"tns_descending" => "nedåtgående",
"tns_not_used" => "ej använd",
"tns_infinite" => "oändlig",
"tns_del_tnail" => "Ta bort miniatyrbild",
"tns_tnail" => "Miniatyr",
"tns_deleted" => "ta bort",
"tns_tn_uploaded" => "miniatyr(er) uppladdade",
"tns_overwrite" => "tillåta överskrivning",
"tns_tn_exists" => "miniatyrbilden finns redan – laddades inte upp",
"tns_upload_error" => "uppladdningsfel",
"tns_no_valid_img" => "är ingen giltig bild",
"tns_file_too_large" => "fil för stor",
"tns_resized" => "storleksändrat",
"tns_resize_error" => "fel vid storleksändring",

//contact.php
"con_msg_to_admin" => "Message to the Administrator",
"con_from" => "Från",
"con_name" => "Namn",
"con_email" => "Email",
"con_subject" => "Ämne",
"con_message" => "Meddelande",
"con_send_msg" => "Skicka meddelande",
"con_fill_in_all_fields" => "Vänligen fyll i alla fält",
"con_invalid_name" => "Ogiltigt namn",
"con_invalid_email" => "Ogiltig e-postadress",
"con_no_urls" => "Inga webblänkar tillåtna i meddelandet",
"con_mail_error" => "E-postproblem. Meddelandet kunde inte skickas. Vänligen försök igen senare.",
"con_con_msg" => "Kontaktmeddelande från kalendern",
"con_thank_you" => "Tack för ditt meddelande till kalendern",
"con_get_reply" => "Du kommer att få svar på ditt meddelande så snart som möjligt",
"con_date" => "Datum",
"con_your_msg" => "Ditt meddelande",
"con_your_cal_msg" => "Ditt meddelande till kalendern",
"con_has_been_sent" => "har skickats till kalenderadministratören",
"con_confirm_eml_sent" => "Ett bekräftelsemeddelande har skickats till",

//msglog.php
"msl_search" => "Search",
"msl_date" => "date",
"msl_text" => "text",
"msl_sent_msgs" => "Sent notification messages",
"msl_no_logs_found" => "No message logs found!",
"msl_errors" => "ERRORS OCCURRED! See luxcal log",

//alert.php
"alt_message#0" => "Din session går snart ut!",
"alt_message#1" => "PHP SESSION HAR UPPHÖRT",
"alt_message#2" => "Vänligen starta om kalendern",
"alt_message#3" => "OGILTIG FÖRFRÅGAN",

//stand-alone sidebar (lcsbar.php)
"ssb_upco_events" => "Kommande händelser",
"ssb_all_day" => "Heldag",
"ssb_none" => "Inga händelser."
);
?>
