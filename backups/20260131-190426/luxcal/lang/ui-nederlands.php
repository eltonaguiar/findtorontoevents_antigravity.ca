<?php
/*
= LuxCal language file =

Wijzigingen en vertalingen zijn aangebracht door J.C.Barnhoorn - Hellevoetsluis datum 9 mei 2024

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "nl";

/* -- Titles on the Header of the Calendar -- */

$months = array("januari","februari","maart","april","mei","juni","juli","augustus","september","oktober","november","december");
$months_m = array("jan","feb","mrt","apr","mei","jun","jul","aug","sep","okt","nov","dec");
$wkDays = array("zondag","maandag","dinsdag","woensdag","donderdag","vrijdag","zaterdag","zondag");
$wkDays_l = array("zon","maa","din","woe","don","vrij","zat","zon");
$wkDays_m = array("zo","ma","di","wo","do","vr","za","zo");
$wkDays_s = array("z","m","d","w","d","v","z","z");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Verzenden",
"log_in" => "Aanmelden",
"log_out" => "Afmelden",
"portrait" => "Staand",
"landscape" => "Liggend",
"none" => "Geen.",
"all_day" => "Hele dag",
"back" => "Terug",
"restart" => "Herstart",
"by" => "door",
"of" => "in",
"max" => "max.",
"options" => "Opties",
"done" => "OK",
"at_time" => "@", //datum en tijd scheiding (e.g. 30-01-2020 @ 10:45)
"from" => "Van", //e.g. vanaf 9:30
"until" => "Tot", //e.g. tot 15:30
"to" => "Tot", //e.g. tot 17-02-2020
"birthdays_in" => "jarig in",
"open_calendar" => "Kalender openen",
"no_way" => "U bent niet bevoegd tot deze actie.",

//index.php
"title_log_in" => "Aanmelden",
"title_profile" => "Gebruikersprofiel",
"title_upcoming" => "Binnenkort",
"title_event" => "Activiteit",
"title_check_event" => "Activiteit Aanvinken",
"title_dmarking" => "Dagmarkering",
"title_search" => "Zoeken op Tekst",
"title_contact" => "Contact Formulier",
"title_ miniatuurs" => "Miniatuur Afbeeldingen",
"title_user_guide" => "LuxCal handleiding",
"title_settings" => "Kalenderinstellingen",
"title_edit_cats" => "Categorieën wijzigen",
"title_edit_users" => "Gebruikers wijzigen",
"title_edit_groups" => "Bewerk gebruikersgroepen",
"title_edit_text" => "Wijzig informatie tekst",
"title_manage_db" => "Onderhoud database",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Toegevoegde / Gewijzigde / Verwijderde Activiteiten",
"title_usr_import" => "Gebruikers importeren - CSV formaat",
"title_usr_export" => "Gebruikers exporteren - CSV formaat",
"title_evt_import" => "Activiteiten importeren - CSV formaat",
"title_ics_import" => "Activiteiten importeren - iCal formaat",
"title_ics_export" => "Activiteiten exporteren - iCal formaat",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "Gebruikersinterface Opmaak",
"title_bd_calendar" => "Verjaardagskalender",

//header.php
"hdr_button_back" => "Terug naar de vorige pagina",
"hdr_options_submit" => "Maak je keuze en klik op deze kop of op 'OK'",
"hdr_options_panel" => "Opties menu",
"hdr_select_date" => "Ga naar dag",
"hdr_calendar" => "Kalender",
"hdr_evt_copied_to" => "Activiteit gekopieerd naar kalender",
"hdr_view" => "Weergaven",
"hdr_lang" => "Talen",
"hdr_all_cats" => "Alle categorieën",
"hdr_all_groups" => "Alle Groepen",
"hdr_all_users" => "Alle gebruikers",
"hdr_go_to_view" => "Ga naar weergave",
"hdr_view_1" => "Jaar",
"hdr_view_2" => "Maand",
"hdr_view_3" => "Werkmaand",
"hdr_view_4" => "Week",
"hdr_view_5" => "Werkweek",
"hdr_view_6" => "Dag",
"hdr_view_7" => "Binnenkort",
"hdr_view_8" => "Wijzigingen",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantt Kaart",
"hdr_select_admin_functions" => "Kies beheerfunctie",
"hdr_admin" => "Beheer",
"hdr_settings" => "Instellingen",
"hdr_categories" => "Categorieën",
"hdr_users" => "Gebruikers",
"hdr_groups" => "Gebruikersgroepen",
"hdr_text_editor" => "Teksteditor",
"hdr_database" => "Database",
"hdr_clean_up" => "Opruimen",
"hdr_import_usr" => "Importeer gebruikers (CSV file)",
"hdr_export_usr" => "Exporteer gebruikers (CSV file)",
"hdr_import_csv" => "Importeer activiteiten (CSV file)",
"hdr_import_ics" => "Importeer activiteiten (iCal file)",
"hdr_export_ics" => "Exporteer activiteiten (iCal file)",
"hdr_msg_log" => "Berichten Log",
"hdr_styling" => "Opmaak",
"hdr_back_to_cal" => "Terug naar kalenderweergave",
"hdr_button_print" => "Afdrukken",
"hdr_print_page" => "Druk deze pagina af",
"hdr_button_pdf" => "PDF bestand - Activiteiten",
"hdr_button_pdf_bc" => "PDF bestand - Verjaardagen",
"hdr_dload_pdf" => "Download weergegeven activiteiten",
"hdr_dload_pdf_bc" => "Download verjaardagskalender",
"hdr_button_contact" => "Contact",
"hdr_contact" => "Contacteer de beheerder",
"hdr_button_tnails" => "Miniaturen",
"hdr_tnails" => "Toon  miniaturen",
"hdr_button_toap" => "Keur goed",
"hdr_toap_list" => "Goed te keuren activiteiten",
"hdr_button_todo" => "Taken",
"hdr_todo_list" => "Takenlijst",
"hdr_button_upco" => "Binnenkort",
"hdr_upco_list" => "Binnenkort",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Zoeken",
"hdr_search" => "Tekst zoeken",
"hdr_button_add" => "Toevoegen",
"hdr_add_event" => "Activiteit toevoegen",
"hdr_button_help" => "Help",
"hdr_user_guide" => "Handleiding",
"hdr_gen_guide" => "Algemene Handleiding",
"hdr_cs_guide" => "Specifieke Handleiding",
"hdr_gen_help" => "Algemene hulp",
"hdr_prev_help" => "Vorige hulp",
"hdr_open_menu" => "Open Menu",
"hdr_side_menu" => "Beheermenu",
"hdr_dest_cals" => "Doelkalender(s)",
"hdr_copy_evt" => "Kopieer activiteit",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "vandaag", //dtpicker.js
"hdr_clear" => "wissen", //dtpicker.js

//event.php
"evt_no_title" => "Geen titel",
"evt_no_start_date" => "Geen begindatum",
"evt_bad_date" => "Datum fout",
"evt_bad_rdate" => "Einddatum voor herhaling fout",
"evt_no_start_time" => "Geen begintijd",
"evt_bad_time" => "Tijd fout",
"evt_end_before_start_time" => "Eindtijd is voor begintijd",
"evt_end_before_start_date" => "Einddatum is voor begindatum",
"evt_until_before_start_date" => "Herhalingseinde is voor begindatum",
"evt_default_duration" => "Standaard activiteitsduur van $1 uur en $2 minuten",
"evt_fixed_duration" => "Vaste activiteitsduur van $1 uur en $2 minuten",
"evt_approved" => "Activiteit goedgekeurd",
"evt_apd_locked" => "Activiteit goedgekeurd en geblokkeerd",
"evt_title" => "Titel",
"evt_venue" => "Locatie",
"evt_address_button" => "Een adres tussen ! wordt een `adresknop`",
"evt_list" => "Lijst",
"evt_category" => "Categorie",
"evt_subcategory" => "Subcategorie",
"evt_description" => "Omschrijving",
"evt_attachments" => "Bijlagen",
"evt_attach_file" => "Voeg bijlage toe",
"evt_click_to_open" => "Klik om te openen",
"evt_click_to_remove" => "Klik om te verwijderen",
"evt_no_pdf_img_vid" => "Bijlage moet pdf, foto of video zijn",
"evt_error_file_upload" => "Fout tijdens het uploaden van de bijlage",
"evt_upload_too_large" => "Bijlagebestand te groot",
"evt_date_time" => "Datum / tijd",
"evt_date" => "Datum",
"evt_private" => "Privé",
"evt_start_date" => "Begintijd",
"evt_end_date" => "Eindtijd",
"evt_select_date" => "Kies datum",
"evt_select_time" => "Kies tijd",
"evt_all_day" => "Hele dag",
"evt_no_time" => "Geen tijd",
"evt_change" => "Wijzigen",
"evt_set_repeat" => "Herhalen",
"evt_set" => "OK",
"evt_help" => "help",
"evt_repeat_not_supported" => "Gespecificeerde herhaling niet ondersteund",
"evt_no_repeat" => "Niet herhalen",
"evt_rolling" => "Rollend",
"evt_until_checked" => "tot afgevinkt",
"evt_repeat_on" => "Herhaal elke",
"evt_until" => "tot",
"evt_blank_no_end" => "leeg: geen einddatum",
"evt_each_month" => "elke maand",
"evt_interval2_1" => "eerste",
"evt_interval2_2" => "tweede",
"evt_interval2_3" => "derde",
"evt_interval2_4" => "vierde",
"evt_interval2_5" => "laatste",
"evt_period1_1" => "dagen",
"evt_period1_2" => "weken",
"evt_period1_3" => "maanden",
"evt_period1_4" => "jaren",
"evt_notification" => "Herinnering",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "nu en/of",
"evt_event_added" => "Nieuwe activiteit",
"evt_event_edited" => "Gewijzigde activiteit",
"evt_event_deleted" => "Verwijderde activiteit",
"evt_event_approved" => "Goedgekeurde activiteit",
"evt_days_before_event" => "dag(en) vóór activiteit",
"evt_to" => "Aan",
"evt_not_help" => "Lijst met geadresseerden gescheiden door punt-comma's. Een geadresseerde kan zijn: een gebruikersnaam, een e-mail adres, een mobiel telefoonnummer, een Telegram chat ID of, tussen rechte haken, de naam (zonder type) van een .txt bestand met adressen in de map 'reciplists', met een adres (een gebruikersnaam, een e-mail adres, een mobiel telefoonnummer of een Telegram chat ID) per regel.<br>Maximum veld lengte: 255 tekens.",
"evt_recip_list_too_long" => "De adreslijst is te lang",
"evt_no_recip_list" => "De adreslijst is leeg",
"evt_not_in_past" => "Herinneringsdatum valt in het verleden",
"evt_not_days_invalid" => "Herinneringsdatum ongeldig",
"evt_status" => "Status",
"evt_descr_help" => "De volgende items kunnen in de omschrijvingsvelden worden toegepast ...<br>• HTML tags &lt;b&gt;, &lt;i&gt;, &lt;u&gt; en &lt;s&gt; voor vette, schuine, onderstreepte en doorgehaalde tekst.",
"evt_descr_help_img" => "• Kleine images ( miniaturen) in het formaat: 'image_naam.ext'. De miniatuur bestanden, met bestandstype .gif, .jpg or .png, moeten aanwezig zijn in de 'thumbnails' map. Indien geactiveerd, kan de  miniaturen pagina worden gebruikt om  miniatuur bestanden te uploaden.",
"evt_descr_help_eml" => "• Mailto-links in het formaat: 'e-mailadres' of 'e-mailadres [naam]', waar 'naam' de naam van de link is. Bijv. xxx@yyyy.zzz [Voor info klik hier].",
"evt_descr_help_url" => "• Links naar websites in het formaat: 'url' of 'url [naam]', waar 'naam' de naam van de link is. Bijv. www.google.nl [zoeken].",
"evt_confirm_added" => "activiteit toegevoegd",
"evt_confirm_saved" => "activiteit opgeslagen",
"evt_confirm_deleted" => "activiteit verwijderd",
"evt_add_close" => "Toevoegen en sluiten",
"evt_add" => "Toevoegen",
"evt_edit" => "Wijzigen",
"evt_save_close" => "Opslaan en sluiten",
"evt_save" => "Opslaan",
"evt_clone" => "Als nieuw opslaan",
"evt_delete" => "Verwijderen",
"evt_close" => "Sluiten",
"evt_added" => "Ingevoerd",
"evt_edited" => "Gewijzigd",
"evt_is_repeating" => "is een herhalende activiteit.",
"evt_is_multiday" => "is een meerdere dagen durende activiteit.",
"evt_edit_series_or_occurrence" => "Wil je deze activiteit of de hele serie wijzigen?",
"evt_edit_series" => "Wijzig de serie activiteiten",
"evt_edit_occurrence" => "Wijzig deze activiteit",
"evt_select_from_list" => "Kies geadresseerden van een lijst",
"evt_select_recips" => "Kies geadresseerden",
"evt_recip_lists" => "Lijsten met geadresseerden",
"evt_regist_recips" => "Geregistreerde geadresseerden",
"evt_public_recips" => "Publieke geadresseerden",

//events - dmark specific
"mrk_text_and_color" => "Tekst en kleur",
"mrk_is_repeating" => "is een herhalende markering",
"mrk_is_multiday" => "is een herhalende markering",
"mrk_text" => "Tekst",
"mrk_color" => "Kleur",
"mrk_background" => "Achtergrond",
"mrk_select_color" => "kies kleur",
"mrk_start_date" => "Start datum",
"mrk_end_date" => "Eind datum",
"mrk_dmark_added" => "Nieuwe dag markering",
"mrk_dmark_edited" => "Gewijzigde dag markering",
"mrk_dmark_deleted" => "Verwijderde dag markering",
"mrk_dates" => "Datum(s)",

//views
"vws_add_event" => "Activiteit toevoegen",
"vws_edit_event" => "Activiteit wijzigen",
"vws_see_event" => "Zie activiteitendetails",
"vws_view_month" => "Per maand",
"vws_view_week" => "Per week",
"vws_view_day" => "Deze dag",
"vws_click_for_full" => "voor volledige kalender klik op maand",
"vws_view_full" => "Open volledige kalender",
"vws_prev_year" => "Vorig jaar",
"vws_next_year" => "Volgend jaar",
"vws_prev_month" => "Vorige maand",
"vws_next_month" => "Volgende maand",
"vws_forward" => "Vooruit",
"vws_backward" => "Terug",
"vws_mark_day" => "Markeer dag",
"vws_today" => "Vandaag",
"vws_back_to_today" => "Terug naar de maand van vandaag",
"vws_back_to_main_cal" => "Terug naar de maand van de hoofdkalender",
"vws_week" => "week",
"vws_wk" => "wk",
"vws_time" => "tijd",
"vws_events" => "Activiteiten",
"vws_all_day" => "Hele dag",
"vws_earlier" => "vroeger",
"vws_later" => "later",
"vws_venue" => "Locatie",
"vws_address" => "Adres",
"vws_events_for_next" => "Activiteiten voor de komende",
"vws_days" => "dag(en)",
"vws_added" => "Toegevoegd",
"vws_edited" => "Gewijzigd",
"vws_notify" => "Stuur e-mail",
"vws_none_due_in" => "Geen activiteiten voor de komende",
"vws_evt_cats" => "Activiteitcategorieën",
"vws_cal_users" => "Kalender gebruikers",
"vws_no_users" => "Geen gebruiker in geselecteerde groep(en)",
"vws_start" => "Start",
"vws_duration" => "Duur",
"vws_no_events_in_gc" => "Geen activiteiten in deze periode",
"vws_download" => "Download",
"vws_download_title" => "Download een bestand met deze activiteiten",
"vws_send_mail" => "Stuur e-mail",

//changes.php
"chg_select_date" => "Kies begindatum",
"chg_notify" => "Stuur e-mail",
"chg_days" => "dag(en)",
"chg_added" => "Toegevoegd",
"chg_edited" => "Gewijzigd",
"chg_deleted" => "Verwijderd",
"chg_changed_on" => "Gewijzigd op",
"chg_no_changes" => "Geen wijzigingen.",

//search.php
"sch_define_search" => "Definieer zoekactie",
"sch_search_text" => "Zoektekst",
"sch_event_fields" => "Activiteitvelden",
"sch_all_fields" => "Alle velden",
"sch_title" => "Titel",
"sch_description" => "Omschrijving",
"sch_venue" => "Plaats",
"sch_user_group" => "Gebruikersgroep",
"sch_event_cat" => "Activiteitcategorie",
"sch_all_groups" => "Alle groepen",
"sch_all_cats" => "Alle categorieën",
"sch_occurring_between" => "Tussen data",
"sch_select_start_date" => "Kies begindatum",
"sch_select_end_date" => "Kies einddatum",
"sch_search" => "Zoek",
"sch_invalid_search_text" => "Zoektekst ontbreekt of is te kort",
"sch_bad_start_date" => "Ongeldige begindatum",
"sch_bad_end_date" => "Ongeldige einddatum",
"sch_no_results" => "Geen resultaten gevonden",
"sch_new_search" => "Nieuwe zoekopdracht",
"sch_calendar" => "Naar kalender",
"sch_extra_field1" => "Extra veld 1",
"sch_extra_field2" => "Extra veld 2",
"sch_sd_events" => "Eendags activiteiten",
"sch_md_events" => "Meerdags activiteiten",
"sch_rc_events" => "Herhalende activiteiten",
"sch_instructions" =>
"<h3>Zoek Instructies</h3>
<p>De kalender database kan worden doorzocht op activiteiten waarin een bepaalde tekst voorkomt.</p>
<br><p><b>Zoektekst</b>: Alleen de geselecteerde velden (zie hieronder) van de activiteiten worden doorzocht. Voor de letters a - z is de  zoekactie hoofdletterongevoelig.</p>
<p>Er zijn twee jokers beschikbaar:</p>
<ul>
<li>Vraagtekens (?) in de zoektekst dienen als joker voor één karakter. <br>Bijv. '?ie?' geeft 'dier', 'Piet', 'lied'.</li>
<li>Asterisks (*) in de zoektekst dienen als joker voor één of meer karakters. <br>Bijv. 'd*r' geeft 'december', 'dor', 'dader'.</li>
</li>
</ul>
<br><p><b>Activiteitvelden</b>: Alleen de geselecteerde velden worden doorzocht.</p>
<br><p><b>Gebruikersgroep</b>: Alleen activiteiten in de geselecteerde gebruikersgroep worden doorzocht.</p>
<br><p><b>Activiteitcategorie</b>: Alleen activiteiten in de geselecteerde categorie worden doorzocht.</p>
<br><p><b>Tussen data</b>: De begin- en einddatum zijn beide optioneel. Indien geen start / eind datum wordt opgegeven, wordt er default $1 dagen terug en $2 dagen vooruit gekeken.</p>
<br><p>Om herhaling van dezelfde activiteit te voorkomen, worden de zoekresultaten opgesplitst in eendaagse activiteiten, meerdaagse activiteiten en herhalende activiteiten.</p>
<br><p>De zoekresultaten worden weergegeven in chronologische volgorde.</p>",

//thumbnails.php
"tns_man_tnails_instr" => "Beheer  miniaturen Instructies",
"tns_help_general" => "De afbeeldingen hieronder kunnen worden gebruikt in de kalender, door de bestandsnaam toe te voegen in het veld omschrijving of een van de extra velden van de activiteit. Een bestandsnaam kan naar het klembord worden gekopieerd door op de betreffende  miniatuar te klikken; vervolgens kan de  miniatuur naam worden toegevoegd in een van de activiteitvelden d.m.v. de toets combinatie CTRL-V. Onder elke  miniatuur vindt u: de bestandsnaam (zonder het gebruikers ID voorvoegsel), de bestandsdatum en tussen haakjes de laatste datum waarop de  miniatuur wordt gebruikt in de kalender.",
"tns_help_upload" => " miniaturen kunnen worden ge-upload van je computer door de Browse knop te selecteren. Om meerdere bestanden te selecteren, houd de CTRL of SHIFT knop ingedrukt tijdens het selecteren van de bestanden (max. 20 per keer). De volgende bestandstypen zijn toegestaan: $1.  miniaturen afbeeldingen groter dan $2 x $3 pixels (b x h) worden automatisch verkleind.",
"tns_help_delete" => " miniaturen met een rood kruis in de linkerbovenhoek kunnen worden verwijderd door dit kruis te selecteren.  miniaturen zonder rood kruis kunnen niet worden verwijderd, omdat ze nog in gebruik zijn na $1. Pas op: Verwijderde  miniaturen kunnen niet worden teruggehaald!",
"tns_your_tnails" => "Uw  miniaturen",
"tns_other_tnails" => "Andere  miniaturen",
"tns_man_tnails" => "Organiseer  miniaturen",
"tns_sort_by" => "Sorteer op",
"tns_sort_order" => "Sorteervolgorde",
"tns_search_fname" => "Zoek bestandsnaam",
"tns_upload_tnails" => "Upload miniaturen",
"tns_name" => "naam",
"tns_date" => "datum",
"tns_ascending" => "oplopend",
"tns_descending" => "aflopend",
"tns_not_used" => "niet gebruikt",
"tns_infinite" => "oneindig",
"tns_del_tnail" => "Verwijder miniatuur",
"tns_tnail" => "Miniatuur",
"tns_deleted" => "verwijderd",
"tns_tn_uploaded" => "miniatuur(en) ge-upload",
"tns_overwrite" => "sta overschrijven toe",
"tns_tn_exists" => "miniatuur bestaat al – niet ge-upload",
"tns_upload_error" => "upload fout",
"tns_no_valid_img" => "is geen geaccepteerde afbeelding",
"tns_file_too_large" => "bestand te groot",
"tns_resized" => "verkleind",
"tns_resize_error" => "verklein fout",

//contact.php
"con_msg_to_admin" => "Bericht aan de beheerder",
"con_from" => "Van",
"con_name" => "Naam",
"con_email" => "E-mail",
"con_subject" => "Onderwerp",
"con_message" => "Bericht",
"con_send_msg" => "Verstuur bericht",
"con_fill_in_all_fields" => "Alle velden invullen a.u.b.",
"con_invalid_name" => "Ongeldige naam",
"con_invalid_email" => "Ongeldig e-mailadres",
"con_no_urls" => "Geen web links toegestaan in het bericht",
"con_mail_error" => "E-mailprobleem. Het bericht kon niet worden verstuurd. Probeer het later nog eens.",
"con_con_msg" => "Contactbericht van de kalender",
"con_thank_you" => "Dank u voor het bericht aan de kalender",
"con_get_reply" => "U krijgt zo spoedig mogelijk antwoord op uw bericht",
"con_date" => "Datum",
"con_your_msg" => "Uw bericht",
"con_your_cal_msg" => "Uw bericht aan de kalender",
"con_has_been_sent" => "is naar de kalenderadministrator verstuurd",
"con_confirm_eml_sent" => "Een bevestigings e-mail is verstuurd naar",

//msglog.php
"msl_search" => "Zoek",
"msl_date" => "datum",
"msl_text" => "tekst",
"msl_sent_msgs" => "Stuur kennisgevingsbericht",
"msl_no_logs_found" => "Geen berichtenlog gevonden!",
"msl_errors" => "ER ZIJN FOUTEN OPGETREDEN! Zie luxcal log",

//alert.php
"alt_message#0" => "Uw sessie verloopt binnenkort!",
"alt_message#1" => "PHP SESSIE VERLOPEN",
"alt_message#2" => "Herstart de Kalender a.u.b.",
"alt_message#3" => "ONGELDIGE AANVRAAG",

//stand-alone sidebar (lcsbar.php)
"ssb_upco_events" => "Binnenkort",
"ssb_all_day" => "Gehele dag",
"ssb_none" => "Geen activiteiten."
);
?>
