<?php
/*
= LuxCal language file =

Ins Deutsche übersetzt von Ulrich Krause. Bitte senden Sie Kommentare / Verbesserungen an rb@luxsoft.eu.
2020.11.29 aktualisiert von Piotr Linski, Rellingen, Germany.

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "de";

/* -- Titles im Kopf Kalender -- */

$months = array("Januar","Februar","März","April","Mai","Juni","Juli","August","September","Oktober","November","Dezember");
$months_m = array("Jan","Feb","Mär","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez");
$wkDays = array("Sonntag","Montag","Dienstag","Mittwoch","Donnerstag","Freitag","Samstag","Sonntag");
$wkDays_l = array("Son","Mon","Die","Mit","Don","Fre","Sam","Son");
$wkDays_m = array("So","Mo","Di","Mi","Do","Fr","Sa","So");
$wkDays_s = array("S","M","D","M","D","F","S","S");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Senden",
"log_in" => "Einloggen",
"log_out" => "Ausloggen",
"portrait" => "Hochformat",
"landscape" => "Querformat",
"none" => "Keine.",
"all_day" => "ganztägig",
"back" => "Zurück",
"restart" => "Restart",
"by" => "durch",
"of" => "im",
"max" => "max.",
"options" => "Optionen",
"done" => "OK",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "Ab", //Bsp.: ab 9:30
"until" => "Bis", //Bsp.: bis 15:30
"to" => "Bis", //Bsp.: bis 17.02.2020
"birthdays_in" => "Birthdays in",
"open_calendar" => "Kalender öffnen",
"no_way" => "Sie haben keine Berechtigung für diese Aktion",

//index.php
"title_log_in" => "Log In",
"title_profile" => "Benutzerprofil",
"title_upcoming" => "Anstehende Termine",
"title_event" => "Termin",
"title_check_event" => "Termin prüfen",
"title_dmarking" => "Tagesmarkierung",
"title_search" => "Text Suche",
"title_contact" => "Kontakt Formular",
"title_thumbnails" => "Miniaturbilder",
"title_user_guide" => "LuxCal Bedienungsanleitung",
"title_settings" => "Kalendereinstellungen",
"title_edit_cats" => "Kategorien bearbeiten",
"title_edit_users" => "Benutzer bearbeiten",
"title_edit_groups" => "Benutzergruppen bearbeiten",
"title_edit_text" => "Informationstext bearbeiten",
"title_manage_db" => "Datenbank Wartung",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Hinzugefügte / Geänderte / Gelöschte Termine",
"title_usr_import" => "Nutzer Datei Import - CSV Format",
"title_usr_export" => "Nutzer Datei Export - CSV Format",
"title_evt_import" => "Termin Datei Import - CSV Format",
"title_ics_import" => "Termin Datei Import - iCal Format",
"title_ics_export" => "Termin Datei Export - iCal Format",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "Styling der Benutzeroberfläche",
"title_bd_calendar" => "Birthday Calendar",

//header.php
"hdr_button_back" => "Zurück zur Hauptseite",
"hdr_options_submit" => "Auswählen und auf 'OK' klicken",
"hdr_options_panel" => "Anzeige Optionen einstellen",
"hdr_select_date" => "Datum auswählen",
"hdr_calendar" => "Kalender",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Ansicht",
"hdr_lang" => "Sprache",
"hdr_all_cats" => "Alle Kategorien",
"hdr_all_groups" => "Alle Benutzergruppen",
"hdr_all_users" => "Alle Benutzer",
"hdr_go_to_view" => "Gehe zu Ansicht",
"hdr_view_1" => "Jahr",
"hdr_view_2" => "Monat",
"hdr_view_3" => "Arbeitsmonat",
"hdr_view_4" => "Woche",
"hdr_view_5" => "Arbeitswoche",
"hdr_view_6" => "Tag",
"hdr_view_7" => "Anstehend",
"hdr_view_8" => "Änderungen",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantt Chart",
"hdr_select_admin_functions" => "Administrator Funktion auswählen",
"hdr_admin" => "Administration",
"hdr_settings" => "Einstellungen",
"hdr_categories" => "Kategorien",
"hdr_users" => "Benutzer",
"hdr_groups" => "Benutzergruppen",
"hdr_text_editor" => "Texteditor",
"hdr_database" => "Datenbank",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "Benutzer Import (CSV file)",
"hdr_export_usr" => "Benutzer Export (CSV file)",
"hdr_import_csv" => "Termin Import (CSV file)",
"hdr_import_ics" => "Termin Import (iCal file)",
"hdr_export_ics" => "Termin Export (iCal file)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Styling",
"hdr_back_to_cal" => "Zurück zur Kalenderansicht",
"hdr_button_print" => "Ausdrucken",
"hdr_print_page" => "Diese Seite ausdrucken",
"hdr_button_pdf" => "PDF Datei - Termine",
"hdr_button_pdf_bc" => "PDF Datei - Geburtstage",
"hdr_dload_pdf" => "Laden Sie anstehende Termine herunter",
"hdr_dload_pdf_bc" => "Download birthday calendar",
"hdr_button_contact" => "Kontakt",
"hdr_contact" => "Wenden Sie sich an den Administrator",
"hdr_button_tnails" => "Miniaturbilder",
"hdr_tnails" => "Zeige Miniaturbilder",
"hdr_button_toap" => "Bestätigen",
"hdr_toap_list" => "Bestätigungspflichtige Termine",
"hdr_button_todo" => "Todo",
"hdr_todo_list" => "Todo Liste",
"hdr_button_upco" => "Bald",
"hdr_upco_list" => "Termine in Kürze",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Suche",
"hdr_search" => "Suche",
"hdr_button_add" => "Hinzufügen",
"hdr_add_event" => "Termin hinzufügen",
"hdr_button_help" => "Hilfe",
"hdr_user_guide" => "Gebrauchsanweisung",
"hdr_gen_guide" => "Allgemeine Gebrauchsanweisung",
"hdr_cs_guide" => "Kontextsensitive Gebrauchsanweisung",
"hdr_gen_help" => "Allgemeine Hilfe",
"hdr_prev_help" => "vorheriges Hilfethema",
"hdr_open_menu" => "öffne Menu",
"hdr_side_menu" => "Verwaltungsmenu",
"hdr_dest_cals" => "Destination Calendar(s)",
"hdr_copy_evt" => "Copy Event",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "Heute", //dtpicker.js
"hdr_clear" => "Löschen", //dtpicker.js

//event.php
"evt_no_title" => "Kein Titel",
"evt_no_start_date" => "Kein Startdatum",
"evt_bad_date" => "Falsches Datum",
"evt_bad_rdate" => "Falsches Wiederholungsende Datum",
"evt_no_start_time" => "Keine Startzeit",
"evt_bad_time" => "Falsche Zeit",
"evt_end_before_start_time" => "Endzeit vor Anfangszeit",
"evt_end_before_start_date" => "Enddatum vor Anfangsdatum",
"evt_until_before_start_date" => "Wiederholungsende vor Anfangsdatum",
"evt_default_duration" => "Standard Termindauer von $1 Stunden und $2 Minuten",
"evt_fixed_duration" => "Feste Termindauer von $1 Stunden und $2 Minuten",
"evt_approved" => "Termin bestätigt",
"evt_apd_locked" => "Termin bestätigt und gesperrt",
"evt_title" => "Titel",
"evt_venue" => "Ort",
"evt_address_button" => "Eine Adresse zwischen ! wird eine `Adresseknopf`",
"evt_list" => "Liste",
"evt_category" => "Kategorie",
"evt_subcategory" => "Subkategorie",
"evt_description" => "Beschreibung",
"evt_attachments" => "Anhänge",
"evt_attach_file" => "Datei anhängen",
"evt_click_to_open" => "Klicke zum öffnen",
"evt_click_to_remove" => "Klicke zum Entfernen",
"evt_no_pdf_img_vid" => "Anhang darf nur PDF, Bild oder Video sein",
"evt_error_file_upload" => "Fehler beim hochladen der Datei",
"evt_upload_too_large" => "Hochzuladende Datei ist zu groß",
"evt_date_time" => "Datum / Zeit",
"evt_date" => "Datum",
"evt_private" => "Privater Termin",
"evt_start_date" => "Anfangsdatum",
"evt_end_date" => "Enddatum",
"evt_select_date" => "Wähle Datum",
"evt_select_time" => "Wähle Zeit",
"evt_all_day" => "Ganztags",
"evt_no_time" => "Keine Zeit",
"evt_change" => "Ändern",
"evt_set_repeat" => "Wiederholung",
"evt_set" => "OK",
"evt_help" => "Hilfe",
"evt_repeat_not_supported" => "Wiederholungsdatei nicht unterstützt",
"evt_no_repeat" => "Keine Wiederholung",
"evt_rolling" => "Rolling",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Wiederhole jeden",
"evt_until" => "bis",
"evt_blank_no_end" => "leer: kein Ende",
"evt_each_month" => "jeden Monat",
"evt_interval2_1" => "1.",
"evt_interval2_2" => "2.",
"evt_interval2_3" => "3.",
"evt_interval2_4" => "4.",
"evt_interval2_5" => "letzten",
"evt_period1_1" => "Tagen",
"evt_period1_2" => "Wochen",
"evt_period1_3" => "Monaten",
"evt_period1_4" => "Jahren",
"evt_notification" => "Erinnerung",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "sofort und/oder",
"evt_event_added" => "Neuer Termin",
"evt_event_edited" => "Geänderter Termin",
"evt_event_deleted" => "Gelöschter Termin",
"evt_event_approved" => "Bestätigter Termin",
"evt_days_before_event" => "Tag(e) vor dem Termin",
"evt_to" => "An",
"evt_not_help" => "Liste der Empfänger getrennt durch Semicolon. Ein Empfänger kann eine Benutzername sein, eine E-Mail Adresse, eine Mobilnummer, eine Telegram chat ID oder, zwischen eckige Klammern, der Name (ohne type) einer .txt Datei mit Adressen im 'reciplists' Verzeichnis, mit einer Adresse (eine Benutzername, eine E-Mail Adresse, eine Mobilnummer oder eine Telegram chat ID) pro Zeile.<br>Maximale Feldlänge: 255 Zeichen.",
"evt_recip_list_too_long" => "Adressenliste hat mehr als 255 Zeichen",
"evt_no_recip_list" => "Benachrichtigungsadresse(n) fehl(t)(en)",
"evt_not_in_past" => "Benachrichtigung in der Vergangenheit",
"evt_not_days_invalid" => "Ungültige Anzahl an Tagen",
"evt_status" => "Status",
"evt_descr_help" => "Die folgenden Elemente können in den Beschreibungsfeldern verwendet werden ...<br>• HTML tags &lt;b&gt;, &lt;i&gt;, &lt;u&gt; und &lt;s&gt; für fett, kursiv, unterstrichenen und durchgestrichenen Text.",
"evt_descr_help_img" => "• kleine Bilder (Miniaturbilder) im Format: 'image_name.ext'. Die Miniaturbilder Dateien mit Dateierweiterungen wie .gif, .jpg oder .png, müssen anwesend sein in dem 'thumbnails' Ordner. Wenn diese Option aktiviert ist, können in diesem Ordner Miniaturbilder Dateien hochgeladen werden.",
"evt_descr_help_eml" => "• Mailto-Links im Format: 'E-Mail-Adresse' oder 'E-Mail-Adresse [Name]', wobei 'Name' der Titel des Hyperlinks ist. Bsp.: xxx@yyyy.zzz [Für Info, klicke hier].",
"evt_descr_help_url" => "• URL links im Format: 'url' oder 'url [name]', wobei 'name' der Titel des Hyperlinks ist. If 'S:' is placed in front of the URL, the link will open in the same page/tab, otherwise the link will open in a blank page/tab. Bsp.: S:https://www.google.com [suchen].",
"evt_confirm_added" => "Termin hinzugefügt",
"evt_confirm_saved" => "Termin gespeichert",
"evt_confirm_deleted" => "Termin gelöscht",
"evt_add_close" => "Hinzufügen und schließen",
"evt_add" => "Hinzufügen",
"evt_edit" => "Bearbeiten",
"evt_save_close" => "Speichern und schließen",
"evt_save" => "Speichern",
"evt_clone" => "Kopie Speichern",
"evt_delete" => "Löschen",
"evt_close" => "Schließen",
"evt_added" => "Hinzugefügt",
"evt_edited" => "Bearbeitet",
"evt_is_repeating" => "ist ein sich wiederholender Termin.",
"evt_is_multiday" => "ist ein mehrtägiger Termin.",
"evt_edit_series_or_occurrence" => "Ganze Serie oder einzelnen Termin bearbeiten?",
"evt_edit_series" => "Ganze Serie",
"evt_edit_occurrence" => "Einzelner Termin",
"evt_select_from_list" => "Select recipients from list",
"evt_select_recips" => "Select Recipients",
"evt_recip_lists" => "Lists with Recipients",
"evt_regist_recips" => "Registered Recipients",
"evt_public_recips" => "Public Recipients",

//events - dmark specific
"mrk_text_and_color" => "Text und Farbe",
"mrk_is_repeating" => "ist ein sich wiederholender Markierung",
"mrk_is_multiday" => "ist ein mehrtägiger Markierung",
"mrk_text" => "Text",
"mrk_color" => "Farbe",
"mrk_background" => "Hintergrund",
"mrk_select_color" => "Wähle Farbe",
"mrk_start_date" => "Startdatum",
"mrk_end_date" => "Enddatum",
"mrk_dmark_added" => "Neue Tagesmarkierung",
"mrk_dmark_edited" => "Geänderte Tagesmarkierung",
"mrk_dmark_deleted" => "Gelöschte Tagesmarkierung",
"mrk_dates" => "Datum(s)",

//views
"vws_add_event" => "Termin hinzufügen",
"vws_edit_event" => "Termin bearbeiten",
"vws_see_event" => "Siehe Termindetails",
"vws_view_month" => "Zeige Monat",
"vws_view_week" => "Zeige Woche",
"vws_view_day" => "Zeige Tag",
"vws_click_for_full" => "Für ganzen Kalender Monat auswählen",
"vws_view_full" => "Ganzen Kalender zeigen",
"vws_prev_year" => "Voriges Jahr",
"vws_next_year" => "Nächstes Jahr",
"vws_prev_month" => "Vorigen Monat",
"vws_next_month" => "Nächsten Monat",
"vws_forward" => "Vorwärts",
"vws_backward" => "Rückwärts",
"vws_mark_day" => "Tag markieren",
"vws_today" => "Heute",
"vws_back_to_today" => "Zurück zum aktuellen Monat",
"vws_back_to_main_cal" => "Zurück zum Hauptkalendermonat",
"vws_week" => "Woche",
"vws_wk" => "KW",
"vws_time" => "Zeit",
"vws_events" => "Termine",
"vws_all_day" => "Ganztags",
"vws_earlier" => "Früher",
"vws_later" => "Später",
"vws_venue" => "Ort",
"vws_address" => "Adresse",
"vws_events_for_next" => "Anstehende Termine für die nächste",
"vws_days" => "Tag(e)",
"vws_added" => "Hinzugefügt",
"vws_edited" => "Bearbeitet",
"vws_notify" => "Melden",
"vws_none_due_in" => "Keine anstehende Termine für die nächste",
"vws_evt_cats" => "Terminkategorien",
"vws_cal_users" => "Kalenderbenutzer",
"vws_no_users" => "Keine Benutzer in (der) ausgewählte(n) Benutzergruppe(n)",
"vws_start" => "Start",
"vws_duration" => "Dauer",
"vws_no_events_in_gc" => "Keine Termine im ausgewählten Zeitraum",
"vws_download" => "Herunterladen",
"vws_download_title" => "eine Textdatei mit diesen Ereignissen herunterladen",
"vws_send_mail" => "E-Mail senden",

//changes.php
"chg_select_date" => "Wähle Startdatum",
"chg_notify" => "Sende E-Mail",
"chg_days" => "Tag(e)",
"chg_added" => "Hinzugefügt",
"chg_edited" => "Bearbeitet",
"chg_deleted" => "Gelöscht",
"chg_changed_on" => "Geändert am",
"chg_no_changes" => "Keine Änderungen.",

//search.php
"sch_define_search" => "Suchkriterien",
"sch_search_text" => "Text",
"sch_event_fields" => "Termin Felder",
"sch_all_fields" => "Alle Felder",
"sch_title" => "Titel",
"sch_description" => "Beschreibung",
"sch_venue" => "Ort",
"sch_user_group" => "Benutzergruppe",
"sch_event_cat" => "Kategorie",
"sch_all_groups" => "Alle Benutzergruppen",
"sch_all_cats" => "Alle Kategorien",
"sch_occurring_between" => "Fällig zwischen",
"sch_select_start_date" => "Startdatum",
"sch_select_end_date" => "Enddatum",
"sch_search" => "Suchen",
"sch_invalid_search_text" => "Text fehlt oder ist zu kurz",
"sch_bad_start_date" => "Falsches Startdatum",
"sch_bad_end_date" => "Falsches Enddatum",
"sch_no_results" => "Nichts gefunden",
"sch_new_search" => "Neue Suche",
"sch_calendar" => "Zum Kalender",
"sch_extra_field1" => "Extra Feld 1",
"sch_extra_field2" => "Extra Feld 2",
"sch_sd_events" => "Eintägige Termine",
"sch_md_events" => "Mehrtägige Termine",
"sch_rc_events" => "Wiederkehrende Termine",
"sch_instructions" =>
"<h3>Anleitung zur Text Suche</h3>
<p>Die Kalender Datenbank kann nach Terminen die den angegebenen Text enthalten durchsucht werden.</p>
<br><p><b>Text</b>: Die ausgewählten Felder (siehe unterhalb) der Termine werden durchsucht.
 Die Suche unterscheidet Groß-und Kleinschreibung.</p>
<p>Zwei Arten von Platzhalter Zeichen können angegeben werden:</p>
<ul>
<li>Ein Fragezeichen (?) im Text steht für ein beliebiges Zeichen.<br>Zum Beispiel: '?i?r' findet: 'Bier', 'Tier', 'hier'.</li>
<li>Ein Ein Sternchen (*) im Text steht für eine beliebige Anzahl an Zeichen.
<br>Zum Beispiel: 'de*r' findet: 'Dezember', 'Denker', 'deiner'.</li>
</ul>
<br><p><b>Termin Felder</b>: Nur die gewählten Felder werden durchsucht.</p>
<br><p><b>Benutzergruppe</b>: Nur Termine der betreffenden Benutzergruppe werden durchsucht.</p>
<br><p><b>Kategorie</b>: Nur Termine der betreffenden Kategorie werden durchsucht.</p>
<br><p><b>Fällig zwischen</b>: Startdatum und Enddatum sind optional.
Bei einem leeren Startdatum/Enddatum, wir die Standardanzahl der Tage, nach denen rückwerts bzw. vorwärts gesucht werden soll, 1 $ Tage bzw. 2 $ Tage sein.</p>
<br><p>Um Wiederholungen desselben Termines zu vermeiden, werden die Suchergebnisse aufgeteilt in: eintägigen Terminen, mehrtägigen Terminen und wiederkehrenden Terminen.</p>
<p>Die Ergebnisse der Suche wird in chronologischer Reihenfolge angezeigt.</p>",

//thumbnails.php
"tns_man_tnails_instr" => "Anweisungen zum Verwalten von Miniaturbilder",
"tns_help_general" => "Die folgenden Bilder können in den Kalenderansichten verwendet werden, indem ihr Dateiname in das Beschreibungsfeld des Termines oder in eines der zusätzlichen Felder eingefügt wird. Ein Bilddateiname kann in die Zwischenablage kopiert werden, indem Sie auf das gewünschte Miniaturbild unten klicken. Anschlie�end kann im Terminfenster der Bildname durch Eingabe von STRG-V in eines der Felder eingefügt werden. Unter jeder Miniaturbild finden Sie: den Dateinamen (ohne das Präfix der Benutzer-ID), das Dateidatum und in Klammern das letzte Datum, an dem das Miniaturbild vom Kalender verwendet wird.",
"tns_help_upload" => "Miniaturbilder können von Ihrem lokalen Computer hochgeladen werden, indem Sie auf die Schaltfläche Browse klicken. Um mehrere Dateien auszuwählen, halten Sie bei der Auswahl die STRG- oder UMSCHALTTASTE gedrückt (jeweils maximal 20 Stück). Die folgenden Dateitypen werden akzeptiert: $1. Miniaturansichten mit einer Größe von mehr als 2$ x 3$ (B x H) werden automatisch in der Größe geändert.",
"tns_help_delete" => "Miniaturbilder mit einem roten Kreuz in der oberen linken Ecke können durch Auswahl dieses Kreuzes gelöscht werden. Miniaturbilder ohne rotes Kreuz können nicht gelöscht werden, da sie nach $1 noch verwendet werden. Achtung: Gelöschte Miniaturbilder können nicht abgerufen werden!",
"tns_your_tnails" => "Ihre Miniaturbilder",
"tns_other_tnails" => "Sonstige Miniaturbilder",
"tns_man_tnails" => "Verwalte Miniaturbilder",
"tns_sort_by" => "Sortieren nach",
"tns_sort_order" => "Sortierreihenfolge",
"tns_search_fname" => "Suche den Dateinamen",
"tns_upload_tnails" => "Miniaturbilder hochladen",
"tns_name" => "Name",
"tns_date" => "Datum",
"tns_ascending" => "aufsteigend",
"tns_descending" => "absteigend",
"tns_not_used" => "nicht benutzt",
"tns_infinite" => "unendlich",
"tns_del_tnail" => "lösche Miniaturbild",
"tns_tnail" => "Miniaturbild",
"tns_deleted" => "gelöscht",
"tns_tn_uploaded" => "Miniaturbild(er) hochgeladen",
"tns_overwrite" => "überschreiben zulassen",
"tns_tn_exists" => "Miniaturbild besteht bereits – nicht hochgeladen",
"tns_upload_error" => "Fehler beim Hochladen",
"tns_no_valid_img" => "ist kein gültiges Bild",
"tns_file_too_large" => "Datei zu groß",
"tns_resized" => "Größe geändert",
"tns_resize_error" => "Größenänderungsfehler",

//contact.php
"con_msg_to_admin" => "Nachricht an den Administrator",
"con_from" => "Von",
"con_name" => "Name",
"con_email" => "E-Mail",
"con_subject" => "Betreff",
"con_message" => "Nachricht",
"con_send_msg" => "Sende Nachricht",
"con_fill_in_all_fields" => "Bitte füllen Sie alle Felder aus",
"con_invalid_name" => "Ungültiger Name",
"con_invalid_email" => "Ungültige E-Mail Adresse",
"con_no_urls" => "In der Nachricht sind keine Weblinks zulässig",
"con_mail_error" => "E-Mail Problem. Die Nachricht konnte nicht gesendet werden. Bitte versuchen Sie es später noch einmal.",
"con_con_msg" => "Kontaktnachricht aus dem Kalender",
"con_thank_you" => "Vielen Dank für Ihre Nachricht an den Kalender",
"con_get_reply" => "Sie erhalten so schnell wie möglich eine Antwort auf Ihre Nachricht",
"con_date" => "Datum",
"con_your_msg" => "Ihre Nachricht",
"con_your_cal_msg" => "Ihre Nachricht an den Kalender",
"con_has_been_sent" => "wurde an den Kalenderadministrator gesendet",
"con_confirm_eml_sent" => "Eine Bestätigungs-E-Mail wurde gesendet an",

//msglog.php
"msl_search" => "Search",
"msl_date" => "date",
"msl_text" => "text",
"msl_sent_msgs" => "Sent notification messages",
"msl_no_logs_found" => "No message logs found!",
"msl_errors" => "ERRORS OCCURRED! See luxcal log",

//alert.php
"alt_message#0" => "Ihre Sitzung läuft bald ab!",
"alt_message#1" => "PHP SESSION ABGELAUFEN",
"alt_message#2" => "Kalender neu starten bitte.",
"alt_message#3" => "UNGÜLTIGE ANFRAGE",

//stand-alone sidebar (lcsbar.php)
"ssb_upco_events" => "Anstehende Termine",
"ssb_all_day" => "Ganztags",
"ssb_none" => "Keine Termine."
);
?>
