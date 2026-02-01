<?php
/*
= LuxCal user interface language file = ROMANIAN / ROMÂNĂ

Traducerea în limba română realizată de Laurențiu Florin Bubuianu (laurfb@gmail.com - laurfb.tk).
This file has been translated in română by Laurențiu Florin Bubuianu (laurfb@gmail.com - laurfb.tk).

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "ro";

/* -- Titles on the Header of the Calendar and Date Picker -- */

$months = array("Ianuarie","Februarie","Martie","Aprilie","Mai","Iunie","Iulie","August","Septembrie","Octombrie","Noiembrie","Decembrie");
$months_m = array("Ian","Feb","Mar","Apr","Mai","Iun","Iul","Aug","Sep","Oct","Nov","Dec");
$wkDays = array("Duminică","Luni","Marți","Miercuri","Joi","Vineri","Sâmbătă","Duminică");
$wkDays_l = array("Dum","Lun","Mar","Mie","Joi","Vin","Sâm","Dum");
$wkDays_m = array("D","L","Ma","Mi","J","V","S","D");
$wkDays_s = array("D","L","Ma","M","J","V","S","D");
$dhm = array("Z","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Trimite",
"log_in" => "Autentificare",
"log_out" => "Deautentificare",
"portrait" => "Portret",
"landscape" => "Landscape",
"none" => "Niciunul.",
"all_day" => "Toată ziua",
"back" => "Înapoi",
"restart" => "Restart",
"by" => "de",
"of" => "de",
"max" => "max.",
"options" => "Opțiuni",
"done" => "Gata",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "De la", //e.g. from 9:30
"until" => "Până la", //e.g. until 15:30
"to" => "la", //e.g. to 17-02-2020
"birthdays_in" => "Aniversări în",
"open_calendar" => "Deschide calendarul",
"no_way" => "Nu sunteți autorizat să efectuați această operațiune",

//index.php
"title_log_in" => "Autentificare",
"title_profile" => "Profil utilizator",
"title_upcoming" => "Evenimente viitoare",
"title_event" => "Eveniment",
"title_check_event" => "Confirmare eveniment",
"title_dmarking" => "Marcare zi",
"title_search" => "Căutare text",
"title_contact" => "Formular contact",
"title_thumbnails" => "Imagine miniatură (thumbnail)",
"title_user_guide" => "Ghid de utilizare",
"title_settings" => "Setări generale calendar",
"title_edit_cats" => "Editare categorii",
"title_edit_users" => "Editare utilizatori",
"title_edit_groups" => "Editare grupuri",
"title_edit_text" => "Editare informații text",
"title_manage_db" => "Setări bază de date",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Adăugare/Editare/Ștergere Evenimente",
"title_usr_import" => "Import fișier utilizator - format CSV",
"title_usr_export" => "Export fișier utilizator - format CSV",
"title_evt_import" => "Import fișier eveniment - format CSV",
"title_ics_import" => "Import fișier eveniment - format iCal",
"title_ics_export" => "Export fișier eveniment - format iCal",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "Stil interfață utilizator",
"title_bd_calendar" => "Calendar aniversări",

//header.php
"hdr_button_back" => "Revenire la pagina părinte",
"hdr_options_submit" => "După selecție apăsați butonul 'Gata'",
"hdr_options_panel" => "Meniu opțiuni",
"hdr_select_date" => "Selecție dată",
"hdr_calendar" => "Calendar",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Mod vizualizare",
"hdr_lang" => "Limbă",
"hdr_all_cats" => "Toate categoriile",
"hdr_all_groups" => "Toate grupurile",
"hdr_all_users" => "Toți utilizatorii",
"hdr_go_to_view" => "Mergi la",
"hdr_view_1" => "Anual",
"hdr_view_2" => "Lunar",
"hdr_view_3" => "Luna curentă",
"hdr_view_4" => "Săptămânal",
"hdr_view_5" => "Săptămâna curentă",
"hdr_view_6" => "Zilnic",
"hdr_view_7" => "Care urmează",
"hdr_view_8" => "Modificări",
"hdr_view_9" => "Matrice(C)",
"hdr_view_10" => "Matrice(U)",
"hdr_view_11" => "Grafic Gantt",
"hdr_select_admin_functions" => "Selecție opțiuni administrare",
"hdr_admin" => "Administrare",
"hdr_settings" => "Setări",
"hdr_categories" => "Categorii",
"hdr_users" => "Utilizatori",
"hdr_groups" => "Grupuri utilizatori",
"hdr_text_editor" => "Editor text",
"hdr_database" => "Bază de date",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "Import utilizator (fișier CSV)",
"hdr_export_usr" => "Export utilizator (fișier CSV)",
"hdr_import_csv" => "Import eveniment (fișier CSV)",
"hdr_import_ics" => "Import eveniment (fișier iCal)",
"hdr_export_ics" => "Export eveniment (fișier iCal)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Stil",
"hdr_back_to_cal" => "Revenire la calendar",
"hdr_button_print" => "Listare",
"hdr_print_page" => "Listare pagină curentă",
"hdr_button_pdf" => "Fișier PDF - Evenimente",
"hdr_button_pdf_bc" => "Fisier PDF - Aniversări",
"hdr_dload_pdf" => "Descărcare evenimente viitoare",
"hdr_dload_pdf_bc" => "Descărcare calendar aniversări",
"hdr_button_contact" => "Contact",
"hdr_contact" => "Contactare administrator",
"hdr_button_tnails" => "Imagini miniatură",
"hdr_tnails" => "Afișare imagini miniatură",
"hdr_button_toap" => "Aprobare",
"hdr_toap_list" => "Evenimente de aprobat",
"hdr_button_todo" => "De văzut",
"hdr_todo_list" => "De văzut",
"hdr_button_upco" => "Care urmează",
"hdr_upco_list" => "Evenimente viitoare",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Căutare",
"hdr_search" => "Căutare",
"hdr_button_add" => "Adăugare",
"hdr_add_event" => "Adăugare eveniment",
"hdr_button_help" => "Asistență",
"hdr_user_guide" => "Ghid utilizator",
"hdr_gen_guide" => "Ghid general de utilizare",
"hdr_cs_guide" => "Ghid de utilizare contextual",
"hdr_gen_help" => "Manual general",
"hdr_prev_help" => "Explicația anterioară",
"hdr_open_menu" => "Meniu principal",
"hdr_side_menu" => "Meniu lateral",
"hdr_dest_cals" => "Calendar(e) destinație",
"hdr_copy_evt" => "Copiere eveniment",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "astăzi", //dtpicker.js
"hdr_clear" => "șterge", //dtpicker.js

//event.php
"evt_no_title" => "Fără titlu",
"evt_no_start_date" => "Fără dată de început",
"evt_bad_date" => "Dată greșită",
"evt_bad_rdate" => "Dată finală greșită",
"evt_no_start_time" => "Fără timp inițial",
"evt_bad_time" => "Timp greșit",
"evt_end_before_start_time" => "Ora de final este definită înaintea orei de început",
"evt_end_before_start_date" => "Data finală este definită înaintea datei de început",
"evt_until_before_start_date" => "Data finală pentru repetare este definită înaintea datei de început",
"evt_default_duration" => "Durată implicită eveniment de $1 oră(ore) și $2 minute",
"evt_fixed_duration" => "Durată fixă eveniment de $1 oră(ore) și $2 minute",
"evt_approved" => "Eveniment aprobat",
"evt_apd_locked" => "Eveniment aprobat și blocat",
"evt_title" => "Denumire",
"evt_venue" => "Locație",
"evt_address_button" => "O adresă între două caractere ! vor deveni un buton",
"evt_list" => "List",
"evt_category" => "Categorie",
"evt_subcategory" => "Subcategorie",
"evt_description" => "Descriere",
"evt_attachments" => "Atașamente",
"evt_attach_file" => "Atașare fișier",
"evt_click_to_open" => "Click pentru deschidere",
"evt_click_to_remove" => "Click pentru ștergere",
"evt_no_pdf_img_vid" => "Atașamentul trebuie să fie fișier pdf, imagine sau clip video",
"evt_error_file_upload" => "Eroare încărcare fișier",
"evt_upload_too_large" => "Fișierul încărcat este prea mare",
"evt_date_time" => "Dată/Oră",
"evt_date" => "Dată",
"evt_private" => "Eveniment privat",
"evt_start_date" => "Începe la",
"evt_end_date" => "Se termină la",
"evt_select_date" => "Selecție dată",
"evt_select_time" => "Selecție oră",
"evt_all_day" => "Zilnic",
"evt_no_time" => "Fără timp",
"evt_change" => "Modificare",
"evt_set_repeat" => "Setare repetiție",
"evt_set" => "OK",
"evt_help" => "explicații",
"evt_repeat_not_supported" => "repetiția specificată este incorectă",
"evt_no_repeat" => "Fără repetare",
"evt_rolling" => "Cu rulare",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Repetă",
"evt_until" => "până când",
"evt_blank_no_end" => "câmp gol = fără sfârșit",
"evt_each_month" => "fiecare lună",
"evt_interval2_1" => "în prima",
"evt_interval2_2" => "în a doua",
"evt_interval2_3" => "în a treia",
"evt_interval2_4" => "în a patra",
"evt_interval2_5" => "ultima",
"evt_period1_1" => "zi",
"evt_period1_2" => "săptămână",
"evt_period1_3" => "lună",
"evt_period1_4" => "an",
"evt_notification" => "Notificare",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "acum și/sau cu",
"evt_event_added" => "Următorul eveniment a fost adăugat",
"evt_event_edited" => "Următorul eveniment a fost modificat",
"evt_event_deleted" => "Următorul eveniment a fost șters",
"evt_event_approved" => "Eveniment aprobat",
"evt_days_before_event" => "zi(le) înainte de eveniment",
"evt_to" => "Către",
"evt_not_help" => "Lista adreselor separate prin punct și virgulă. O listă poate conține nume, adrese de email, numere de telefon, Telegram chat ID, toate incluse în paranteze pătrate, nume (without type) de .txt fișier cu adrese din folderul 'reciplists'. Fișierul cu adrese trebuie să conțină câte o singură înregistrare pe rând.<br>Lungimea maximă a câmpului este de 255 caractere.",
"evt_recip_list_too_long" => "Lista de adrese este prea mare.",
"evt_no_recip_list" => "Lista destinatarilor este goală",
"evt_not_in_past" => "Data de notificare este incorectă (este expirată deja)",
"evt_not_days_invalid" => "Zile de notificare invalide",
"evt_status" => "Stare",
"evt_descr_help" => "Următoarele elemente pot fi incluse în câmpul de descriere ...<br>• taguri HTML &lt;b&gt;, &lt;i&gt;, &lt;u&gt; și &lt;s&gt; pentru text bold, italic, subliniat și supraliniat.",
"evt_descr_help_img" => "• imagini reprezentative (thumbnails) în următorul format: 'nume_imagine.ext'. Fișierele imagine corespunzătoare , cu extensii tip .gif, .jpg sau .png, trebuie să fie prezente în folderul 'thumbnails'. Dacă este activat, pagina Thumbnails poate fi utilizată pentru încărcarea de imagini.",
"evt_descr_help_eml" => "• Linkurile email to în următorul format: 'adresele de email' or 'adresele de email [nume]', unde 'nume' reprezintă titlul linkului. E.g. xxx@yyyy.zzz [Pentru informații fă click aici].",
"evt_descr_help_url" => "• Linkurile URL în următorul format: 'url' sau 'url [nume]', unde 'nume' reprezintă titlul linkului. Dacă textul 'S:' este plasat înaintea unui URL, linkul va fi deschis în acceași pagină/tab, altfel el va fi deschis într=o pagina/tab goale. Ex. S:https://www.google.com [caută].",
"evt_confirm_added" => "eveniment adăugat",
"evt_confirm_saved" => "eveniment salvat",
"evt_confirm_deleted" => "eveniment șters",
"evt_add_close" => "Adaugă și închide",
"evt_add" => "Adaugă",
"evt_edit" => "Modifică",
"evt_save_close" => "Salvează și închide",
"evt_save" => "Salvează",
"evt_clone" => "Salvează ca nou",
"evt_delete" => "Șterge",
"evt_close" => "Închide",
"evt_added" => "Adăugat la",
"evt_edited" => "Modificat",
"evt_is_repeating" => "este un eveniment repetitiv.",
"evt_is_multiday" => "este un eveniment derulat pe mai multe zile.",
"evt_edit_series_or_occurrence" => "Doriți să modificați seria repetițiilor sau doar acest eveniment?",
"evt_edit_series" => "Modifică serie de evenimente",
"evt_edit_occurrence" => "Modifică doar acest eveniment",
"evt_select_from_list" => "Select recipients from list",
"evt_select_recips" => "Select Recipients",
"evt_recip_lists" => "Lists with Recipients",
"evt_regist_recips" => "Registered Recipients",
"evt_public_recips" => "Public Recipients",

//events - dmark specific
"mrk_text_and_color" => "Text și culoare",
"mrk_is_repeating" => "este un marcaj repetitiv",
"mrk_is_multiday" => "este un marcaj multi-zi",
"mrk_text" => "Text",
"mrk_color" => "Culoare",
"mrk_background" => "Fundal",
"mrk_select_color" => "selecție culoare",
"mrk_start_date" => "Data de început",
"mrk_end_date" => "Data de final",
"mrk_dmark_added" => "Marcare nouă",
"mrk_dmark_edited" => "Marcaj de zi schimbat",
"mrk_dmark_deleted" => "Marcaj de zi șters",
"mrk_dates" => "Dată(e)",

//views
"vws_add_event" => "Adăugare eveniment",
"vws_edit_event" => "Editare eveniment",
"vws_see_event" => "Detalii eveniment",
"vws_view_month" => "Vizualizare lună",
"vws_view_week" => "Vizualizare săptămână",
"vws_view_day" => "Vizualizare zi",
"vws_click_for_full" => "pentru calendar complet selectați luna",
"vws_view_full" => "Vizualizare completă calendar",
"vws_prev_year" => "Anul anterioară",
"vws_next_year" => "Anul următoare",
"vws_prev_month" => "Luna anterioară",
"vws_next_month" => "Luna următoare",
"vws_forward" => "Înainte",
"vws_backward" => "Înapoi",
"vws_mark_day" => "Marcare zi",
"vws_today" => "Astăzi",
"vws_back_to_today" => "Salt la luna curentă",
"vws_back_to_main_cal" => "Înapoi la luna principală a calendarului",
"vws_week" => "săptămâna",
"vws_wk" => "săpt.",
"vws_time" => "Timp",
"vws_events" => "Evenimente",
"vws_all_day" => "Zilnic",
"vws_earlier" => "Înainte de",
"vws_later" => "Mai târziu",
"vws_venue" => "Locație",
"vws_address" => "Adresă",
"vws_events_for_next" => "Evenimentele pentru următoarele",
"vws_days" => "zi(le)",
"vws_added" => "Adăugat",
"vws_edited" => "Modificat",
"vws_notify" => "Notificare",
"vws_none_due_in" => "Niciun eveniment nu este programat",
"vws_evt_cats" => "Categorii eveniment",
"vws_cal_users" => "Utilizatori calendar",
"vws_no_users" => "Niciun utilizator în grupul(grupurile) selectat(e)",
"vws_start" => "Start",
"vws_duration" => "Durată",
"vws_no_events_in_gc" => "Niciun eveniment în perioada specificată",
"vws_download" => "Descărcare",
"vws_download_title" => "Descarcă un fișier cu aceste evenimente",
"vws_send_mail" => "Trimite email",

//changes.php
"chg_select_date" => "Selectare data inițială",
"chg_notify" => "Notificare",
"chg_days" => "Zi(le)",
"chg_added" => "Adăugat",
"chg_edited" => "Modificat",
"chg_deleted" => "Șters",
"chg_changed_on" => "Modificat la",
"chg_no_changes" => "Nicio modificare.",

//search.php
"sch_define_search" => "Parametri căutare",
"sch_search_text" => "Text căutare",
"sch_event_fields" => "Căutare în",
"sch_all_fields" => "Toate câmpurile",
"sch_title" => "Denumire",
"sch_description" => "Descriere",
"sch_venue" => "Locație",
"sch_user_group" => "Grup utilizatori",
"sch_event_cat" => "Categorie eveniment",
"sch_all_groups" => "Toate grupurile",
"sch_all_cats" => "Toate categoriile",
"sch_occurring_between" => "Între datele",
"sch_select_start_date" => "Selecție dată început",
"sch_select_end_date" => "Selecție dată sfârșit",
"sch_search" => "Căutare",
"sch_invalid_search_text" => "Text de căutat lipsă sau prea scurt",
"sch_bad_start_date" => "Dată de început greșită",
"sch_bad_end_date" => "Dată de sfârșit greșită",
"sch_no_results" => "Nu a fost găsit nimic",
"sch_new_search" => "Căutare nouă",
"sch_calendar" => "Afișare calendar",
"sch_extra_field1" => "Echipa",
"sch_extra_field2" => "Difuzare",
"sch_sd_events" => "Eveniment de o zi",
"sch_md_events" => "Eveniment multi-zi",
"sch_rc_events" => "Evenimente recurente",
"sch_instructions" =>
"<h3>Instrucțiuni căutare</h3>
<p>Pagina permite căutarea unui text oarecare în baza de date cu afișarea evenimentelor care conțin acel text.</p>
<br><p><b>Text căutare</b>: Câmpul permite introducerea textului (șirului de caractere) de căutat. Căutarea nu ține cont de tipul caracterelor (majuscule sau minuscule).</p>
<p>Pentru simplificare, în definirea textului de căutat pot fi folosite și două caractere speciale:</p>
<ul>
<li>Un semn de întrebare (?) folosit în definirea textului de căutat înlocuiește orice caracter singular. Spre exemplu: textul '?er?' va determina căutarea atât a cuvîntului 'bere' cât și a cuvântului 'zero'.</li>
<li>Caracterul 'Asterisk' (*) înlocuiește la căutare un grup de caractere. Spre exemplu textul 'de*' va determina găsirea cuvintelor 'Decembrie', 'deal', 'dezvoltare' etc..</li>
</ul>
<p>Un câmp gol sau caracterul ”&” va determina afișarea tuturor evenimentelor.</p>
<br><p><b>Căutare în</b>: Textul introdus va fi căutat în toate câmpurile marcate.</p>
<br><p><b>User group</b>: Textul introdus va fi căutat doar în evenimentele din grupul selectat.</p>
<br><p><b>Categorie evenimente</b>: Textul introdus va fi căutat doar în categoria de evenimente selectată.</p>
<br><p><b>Între datele</b>: Data de început și de sfîrșit este opțională. În cazul unei date de început/sfârșit necompletate, numărul de date de căutare va fi de $1 zile, respectiv $2 zile.</p>
<br><p>Pentru a evita repetiția aceluiași eveniment, căutarea va fi împărțită pe evenimente pentru o  zi, evenimente multi-zi și evenimente recurente.</p>
<br><p>Rezultatele căutării vor fi afișate în ordine cronologică.</p>",

//thumbnails.php
"tns_man_tnails_instr" => "Instrucțiuni de gestionare imagini miniatură",
"tns_help_general" => "Imaginile miniatură pot fi utilizate în calendar prin inserarea numelui de fișier corespunzător în câmpul descriere eveniment sau într-unul din câmpurile suplimentare. Numele fișierului imagine poate fi copiat în clipboard făcând click pe una din imaginile miniatură de mai jos; apoi, în fereastra Eveniment, imaginea poate fi inserată folosind combinația CTRL-V. Sub fiecare imagine miniatură veți găsi numele fișierului corespunzător (fără prefixul ID), data, și între paranteze, ultima dată la care imaginea a fost utilizată în calendar.",
"tns_help_upload" => "Miniaturile pot fi încărcate de pe calculaotrul local folosind butonul Browse/Navigare. Pentru selcția mai multor imagini mențineți apăsată tastele CTLR sau SHIFT în timp ce faceți click pe imaginile dorite. Pot fi selectate astfel maxim 20 de imagini. Următoarele tipuri de fișiere sunt acceptate: $1. Imaginile miniatură cu dimensiuni mai mari de $2 x $3 pixeli (lățime x înălțime) vor fi scalate (micșorate) automat.",
"tns_help_delete" => "Imaginea miniatură afișată cu o cruciuliță roșie în colțul stânga sus poate fi ștearsă făcând click pe 'cruciuliță'. Cele fără 'cruciuliță' nu pot fi șterse pentru că sunt utilizate încă după $1. Atenție: Imaginile șterse nu pot fi recuperate!",
"tns_your_tnails" => "Imaginea ta miniatură",
"tns_other_tnails" => "Altă imagine miniatură",
"tns_man_tnails" => "Gestionare imagini miniatură",
"tns_sort_by" => "Sortare după",
"tns_sort_order" => "Ordine sortare",
"tns_search_fname" => "Căutare nume fișier",
"tns_upload_tnails" => "Încărcare imagini",
"tns_name" => "nume",
"tns_date" => "dată",
"tns_ascending" => "crescător",
"tns_descending" => "descrescător",
"tns_not_used" => "neutilizat",
"tns_infinite" => "infinit",
"tns_del_tnail" => "Ștergere imagine",
"tns_tnail" => "Imagine miniatură",
"tns_deleted" => "șters",
"tns_tn_uploaded" => "imagine miniatură încărcată",
"tns_overwrite" => "permite suprascrirea",
"tns_tn_exists" => "imaginea miniatură există deja – nu a fost reîncărcată",
"tns_upload_error" => "eroare încărcare",
"tns_no_valid_img" => "reprezintă o imagine invalidă",
"tns_file_too_large" => "fișier prea mare",
"tns_resized" => "scalată",
"tns_resize_error" => "eroare scalare",

//contact.php
"con_msg_to_admin" => "Mesaj către administrator",
"con_from" => "De la",
"con_name" => "Nume",
"con_email" => "Email",
"con_subject" => "Subiect",
"con_message" => "Mesaj",
"con_send_msg" => "Trimite mesaj",
"con_fill_in_all_fields" => "Vă rugăm să completați toate câmpurile",
"con_invalid_name" => "Nume invalid",
"con_invalid_email" => "Adresă de email invalidă",
"con_no_urls" => "Nu este permis introducerea de linkuri în mesaj",
"con_mail_error" => "Eroare email. Mesajul nu a putut fi trimis. Vă rugăm să reîncercați mai târziu.",
"con_con_msg" => "Mesaj de la Calendar",
"con_thank_you" => "Mulțumim pentru mesaj",
"con_get_reply" => "Veți primi un răspuns cât de curând posibil",
"con_date" => "Data",
"con_your_msg" => "Mesajul dumneavoastră",
"con_your_cal_msg" => "Mesajul dumneavoastră către Calendar",
"con_has_been_sent" => "a fost trimis către administrator",
"con_confirm_eml_sent" => "Un mesaj de confirmare a fost trimis către",

//msglog.php
"msl_search" => "Search",
"msl_date" => "date",
"msl_text" => "text",
"msl_sent_msgs" => "Sent notification messages",
"msl_no_logs_found" => "No message logs found!",
"msl_errors" => "ERRORS OCCURRED! See luxcal log",

//alert.php
"alt_message#0" => "Sesiunea dumneavoastră va expira în scurt timp!",
"alt_message#1" => "SESIUNEA PHP A EXPIRAT",
"alt_message#2" => "Vă rugăm să restartați Calendarul",
"alt_message#3" => "CERERE INVALIDĂ",

//stand-alone sidebar (lcsbar.php)
"ssb_upco_events" => "Evenimente viitoare",
"ssb_all_day" => "Toate zilele",
"ssb_none" => "Niciun eveniment."
);
?>
