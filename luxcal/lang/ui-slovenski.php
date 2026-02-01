<?php
/*
= LuxCal user interface language file =

This file has been produced by LuxSoft and has been translated by David.

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "sl";

/* -- Titles on the Header of the Calendar and Date Picker -- */

$months = array("Januar","Februar","Marc","April","Maj","Junij","Julij","Avgust","September","Oktober","November","December");
$months_m = array("Jan","Feb","Mar","Apr","Maj","Jun","Jul","Avg","Sep","Okt","Nov","Dec");
$wkDays = array("Nedelja","Ponedeljek","Torek","Sreda","Četrtek","Petek","Sobota","Nedelja");
$wkDays_l = array("Ned","Pon","Tor","Sre","Čet","Pet","Sob","Ned");
$wkDays_m = array("Ne","Po","To","Sr","Če","Pe","So","Ne");
$wkDays_s = array("N","P","T","S","Č","P","S","N");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Pošlji",
"log_in" => "Vpis",
"log_out" => "Izpis",
"portrait" => "Portrait",
"landscape" => "Landscape",
"none" => "Brez.",
"all_day" => "All day",
"back" => "Nazaj",
"restart" => "Restart",
"by" => "z",
"of" => "od",
"max" => "max.",
"options" => "Možnosti",
"done" => "Narejeno",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "From", //e.g. from 9:30
"until" => "Until", //e.g. until 15:30
"to" => "To", //e.g. to 17-02-2020
"birthdays_in" => "Birthdays in",
"open_calendar" => "Odpri koledar",
"no_way" => "Nimate pooblastil za izvedbo tega dejanja",

//index.php
"title_log_in" => "Vpis",
"title_profile" => "User Profile",
"title_upcoming" => "Prihajajoči dogodki",
"title_event" => "Dogodek",
"title_check_event" => "Preglej dogodek",
"title_dmarking" => "Day Marking",
"title_search" => "Iskanje po tekstu",
"title_contact" => "Contact Form",
"title_thumbnails" => "Thumbnail Images",
"title_user_guide" => "LuxCal uporabniški vodič",
"title_settings" => "Upravljaj nastavitve koledarja",
"title_edit_cats" => "Spremeni kategorije",
"title_edit_users" => "Spremeni uporabike",
"title_edit_groups" => "Spremeni uporabniška skupina",
"title_edit_text" => "Text Editor",
"title_manage_db" => "Upravljaj podatkovne baze",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Dodani / spremenjeni / izbrisani dogodki",
"title_usr_import" => "User File Import - CSV format",
"title_usr_export" => "User File Export - CSV format",
"title_evt_import" => "Event File Import - CSV format",
"title_ics_import" => "Event File Import - iCal format",
"title_ics_export" => "Event File Export - iCal format",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "User Interface Styling",
"title_bd_calendar" => "Birthday Calendar",

//header.php
"hdr_button_back" => "Nazaj na starševsko stran",
"hdr_options_submit" => "Izberite svojo izbiro in pritisnite 'Naredi'",
"hdr_options_panel" => "Plošča z možnostmi",
"hdr_select_date" => "Pojdi do datuma",
"hdr_calendar" => "Koledar",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Pogled",
"hdr_lang" => "Jezik",
"hdr_all_cats" => "Vse kategorije",
"hdr_all_groups" => "All Groups",
"hdr_all_users" => "Vsi uporabniki",
"hdr_go_to_view" => "Go to view",
"hdr_view_1" => "Leto",
"hdr_view_2" => "Mesec",
"hdr_view_3" => "Delovni mesec",
"hdr_view_4" => "Teden",
"hdr_view_5" => "Delovni teden",
"hdr_view_6" => "Dan",
"hdr_view_7" => "Prihajajoče",
"hdr_view_8" => "Spremembe",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantt Chart",
"hdr_select_admin_functions" => "Izberi možnosti upravitelja",
"hdr_admin" => "Administrator",
"hdr_settings" => "Nastavitve",
"hdr_categories" => "Kategorije",
"hdr_users" => "Uporabniki",
"hdr_groups" => "User Groups",
"hdr_text_editor" => "Text Editor",
"hdr_database" => "Podatkovna baza",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "User Import (CSV file)",
"hdr_export_usr" => "User Export (CSV file)",
"hdr_import_csv" => "Event Import (CSV file)",
"hdr_import_ics" => "Event Import (iCal file)",
"hdr_export_ics" => "Event Export (iCal file)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Styling",
"hdr_back_to_cal" => "Nazaj do pogleda koledarja",
"hdr_button_print" => "Natisni",
"hdr_print_page" => "Natisni to stran",
"hdr_button_pdf" => "PDF File - Events",
"hdr_button_pdf_bc" => "PDF File - Birthdays",
"hdr_dload_pdf" => "Download events displayed",
"hdr_dload_pdf_bc" => "Download birthday calendar",
"hdr_button_contact" => "Contact",
"hdr_contact" => "Contact the administrator",
"hdr_button_tnails" => "Thumbnails",
"hdr_tnails" => "Show thumbnails",
"hdr_button_toap" => "Approve",
"hdr_toap_list" => "Events to be approved",
"hdr_button_todo" => "ToDo",
"hdr_todo_list" => "Todo spisek",
"hdr_button_upco" => "Prihajajoče",
"hdr_upco_list" => "Prihajajoči dogodki",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Išči",
"hdr_search" => "Iskanje teksta",
"hdr_button_add" => "Dodaj",
"hdr_add_event" => "Dodaj dogodek",
"hdr_button_help" => "Pomoč",
"hdr_user_guide" => "Uporabniški vodič",
"hdr_gen_guide" => "General User Guide",
"hdr_cs_guide" => "Context-sensitive User Guide",
"hdr_gen_help" => "General help",
"hdr_prev_help" => "Previous help",
"hdr_open_menu" => "Open Menu",
"hdr_side_menu" => "Side Menu",
"hdr_dest_cals" => "Destination Calendar(s)",
"hdr_copy_evt" => "Copy Event",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "danes", //dtpicker.js
"hdr_clear" => "izbriši", //dtpicker.js

//event.php
"evt_no_title" => "Brez vrste",
"evt_no_start_date" => "Brez začetnega datuma",
"evt_bad_date" => "Napačen datum",
"evt_bad_rdate" => "Napčna ponovitev in datum",
"evt_no_start_time" => "Brez začetnega časa",
"evt_bad_time" => "Napačen čas",
"evt_end_before_start_time" => "Čas za konec dogodka je pred časom za začetek",
"evt_end_before_start_date" => "Datum za konec dogodka je pred datumom za začetek",
"evt_until_before_start_date" => "Konec ponovitve je pred začetnim datumom",
"evt_default_duration" => "Default event duration of $1 hours and $2 minutes",
"evt_fixed_duration" => "Fixed event duration of $1 hours and $2 minutes",
"evt_approved" => "Dogodek potrjen",
"evt_apd_locked" => "Dogodek potrjen in zaklenjen",
"evt_title" => "Vrsta",
"evt_venue" => "Ime in Priimek",
"evt_address_button" => "An address between ! marks will become a button",
"evt_list" => "List",
"evt_category" => "Kategorija",
"evt_subcategory" => "Subcategory",
"evt_description" => "Opis",
"evt_attachments" => "Attachments",
"evt_attach_file" => "Attach file",
"evt_click_to_open" => "Click to open",
"evt_click_to_remove" => "Click to remove",
"evt_no_pdf_img_vid" => "Attachment should be pdf, image or video",
"evt_error_file_upload" => "Error uploading file",
"evt_upload_too_large" => "Uploaded file too large",
"evt_date_time" => "datum / čas",
"evt_date" => "Datum",
"evt_private" => "Zasebni dogodek(priporočljivo)",
"evt_start_date" => "Začetek",
"evt_end_date" => "Konec",
"evt_select_date" => "Izberi datum",
"evt_select_time" => "Izberi čas",
"evt_all_day" => "Ves dan",
"evt_no_time" => "No Time",
"evt_change" => "Spremeni",
"evt_set_repeat" => "Nastavi ponovitev",
"evt_set" => "OK",
"evt_help" => "pomoč",
"evt_repeat_not_supported" => "Nastavljena ponovitev ni podprta",
"evt_no_repeat" => "Brez ponovitve",
"evt_rolling" => "Rolling",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Ponovi vsakih",
"evt_until" => "dokler",
"evt_blank_no_end" => "prazno: brez konca",
"evt_each_month" => "vsak mesec",
"evt_interval2_1" => "prvi",
"evt_interval2_2" => "drugi",
"evt_interval2_3" => "tretji",
"evt_interval2_4" => "četrti",
"evt_interval2_5" => "zadnji",
"evt_period1_1" => "dan",
"evt_period1_2" => "teden",
"evt_period1_3" => "meesec",
"evt_period1_4" => "leto",
"evt_notification" => "Obvestilo",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "zdaj in/ali",
"evt_event_added" => "Nov dogodek",
"evt_event_edited" => "Spremenjeni dogodek",
"evt_event_deleted" => "Izbrisani dogodek",
"evt_event_approved" => "Approved event",
"evt_days_before_event" => "dni pred dogodkom",
"evt_to" => "Da",
"evt_not_help" => "List of recipients separated by semicolons. A recipient can be a user name, an email address, a mobile phone number, a Telegram chat ID or, enclosed in square brackets, the name (without type) of a .txt file with recipients in the 'reciplists' folder. This file should contain one recipient (a user name, an email address, a mobile phone number or a Telegram chat ID) per line.<br>Maximum field length: 255 characters.",
"evt_recip_list_too_long" => "Polje z naslovi spletnih pošt vsebuje preveč znakov.",
"evt_no_recip_list" => "Manjka(jo) spletni naslov(i) za obveščanje.",
"evt_not_in_past" => "Obveščevalni datum v preteklosti",
"evt_not_days_invalid" => "Neveljavni obveščevalni dnevi",
"evt_status" => "Status",
"evt_descr_help" => "Naslednji elementi so lahko uporabljeni v polju za opis...<br>• HTML oznake &lt;b&gt;, &lt;i&gt;, &lt;u&gt; in &lt;s&gt; za odebeljen, poševen, podčrtan in prečrtan-čez tekst.",
"evt_descr_help_img" => "• majhne slike (ikone) v sledečih formatih: 'ime_slike.ext'. The thumbnail files, with file extension .gif, .jpg or .png, must be present in 'thumbnails' folder. If enabled, the Thumbnails page can be used to upload thumbnail files.",
"evt_descr_help_eml" => "• Mailto-links in the following formatu: 'email address' or 'email address [ime]', kjer je 'ime' naslov povezave. E.g. xxx@yyyy.zzz [For info click here].",
"evt_descr_help_url" => "• URL povezave morajo biti v sledečem formatu: 'url' ali 'url [ime]', kjer je 'ime' naslov povezave. If 'S:' is placed in front of the URL, the link will open in the same page/tab, otherwise the link will open in a blank page/tab. Npr.: S:https://www.google.com [iskanje].",
"evt_confirm_added" => "dogodek dodan",
"evt_confirm_saved" => "dogodek shranjen",
"evt_confirm_deleted" => "dogodek zbrisan",
"evt_add_close" => "dodaj in zapri",
"evt_add" => "dodaj",
"evt_edit" => "Spremeni",
"evt_save_close" => "Shrani in zapri",
"evt_save" => "Shrani",
"evt_clone" => "Shrani kot novo",
"evt_delete" => "Zbriši",
"evt_close" => "Zapri",
"evt_added" => "dodano",
"evt_edited" => "Edited",
"evt_is_repeating" => "je ponavljajoči dogodek.",
"evt_is_multiday" => "je dogodek, ki se dogaja skozi več dni.",
"evt_edit_series_or_occurrence" => "Ali želite spremeniti celo serijo ali samo ta pojav?",
"evt_edit_series" => "Spremeni serije",
"evt_edit_occurrence" => "Spremeni ta pojav",
"evt_select_from_list" => "Select recipients from list",
"evt_select_recips" => "Select Recipients",
"evt_recip_lists" => "Lists with Recipients",
"evt_regist_recips" => "Registered Recipients",
"evt_public_recips" => "Public Recipients",

//events - dmark specific
"mrk_text_and_color" => "Text and color",
"mrk_is_repeating" => "is a repeating marking",
"mrk_is_multiday" => "is a multi-day marking",
"mrk_text" => "Text",
"mrk_color" => "Color",
"mrk_background" => "Background",
"mrk_select_color" => "select color",
"mrk_start_date" => "Start date",
"mrk_end_date" => "End date",
"mrk_dmark_added" => "New day marking",
"mrk_dmark_edited" => "Changed day marking",
"mrk_dmark_deleted" => "Deleted day marking",
"mrk_dates" => "Date(s)",

//views
"vws_add_event" => "Dodaj dogodek",
"vws_edit_event" => "Edit Event",
"vws_see_event" => "See event details",
"vws_view_month" => "Poglej mesec",
"vws_view_week" => "Poglej teden",
"vws_view_day" => "Poglej dan",
"vws_click_for_full" => "za celoten koledar kliknite mesec",
"vws_view_full" => "Poglej celoten koledar",
"vws_prev_year" => "Prejšnje leto",
"vws_next_year" => "Naslednje leto",
"vws_prev_month" => "Prejšnji mesec",
"vws_next_month" => "Naslednji mesec",
"vws_forward" => "Forward",
"vws_backward" => "Backward",
"vws_mark_day" => "Mark day",
"vws_today" => "Danes",
"vws_back_to_today" => "Nazaj na mesc ki je danes",
"vws_back_to_main_cal" => "Back to the main calendar month",
"vws_week" => "Teden",
"vws_wk" => "tdn",
"vws_time" => "Čas",
"vws_events" => "Dogodki",
"vws_all_day" => "Ves dan",
"vws_earlier" => "Zgodnje",
"vws_later" => "Pozneje",
"vws_venue" => "Kraj",
"vws_address" => "Address",
"vws_events_for_next" => "Prihajajoči dogodki za naslednji",
"vws_days" => "dan(dnevi)",
"vws_added" => "Dodano",
"vws_edited" => "Spremenjeno",
"vws_notify" => "Obvesti",
"vws_none_due_in" => "Ni dogodkov za naslednji mesec.",
"vws_evt_cats" => "Event categories",
"vws_cal_users" => "Calendar users",
"vws_no_users" => "No users in selected group(s)",
"vws_start" => "Start",
"vws_duration" => "Duration",
"vws_no_events_in_gc" => "No events in the selected period",
"vws_download" => "Prenesi",
"vws_download_title" => "Prenesi datoteko s temi dogodki",
"vws_send_mail" => "Send email",

//changes.php
"chg_select_date" => "Izberi datum začetka",
"chg_notify" => "Obvesti",
"chg_days" => "dan(dni)",
"chg_added" => "Dodano",
"chg_edited" => "Spremenjeno",
"chg_deleted" => "Izbrisano",
"chg_changed_on" => "Spremenjeno na",
"chg_no_changes" => "Brez sprememb.",

//search.php
"sch_define_search" => "Opredeli iskanje",
"sch_search_text" => "Išči po tekstu",
"sch_event_fields" => "Polja dogodka",
"sch_all_fields" => "Vsa polja",
"sch_title" => "Naslov",
"sch_description" => "Opis",
"sch_venue" => "Vrsta",
"sch_user_group" => "User group",
"sch_event_cat" => "Kategorija dogodka",
"sch_all_groups" => "All Groups",
"sch_all_cats" => "Vse kategorije",
"sch_occurring_between" => "Pojavljanje med",
"sch_select_start_date" => "Izberi datum začetka",
"sch_select_end_date" => "Izberi datum konca",
"sch_search" => "Iskanje",
"sch_invalid_search_text" => "Prazen vnos ali prekratka beseda za iskanje",
"sch_bad_start_date" => "Napačen datum začetka",
"sch_bad_end_date" => "Napačen datum konca",
"sch_no_results" => "Ni najdenih rezultatov",
"sch_new_search" => "Novo isaknje",
"sch_calendar" => "Pojdi na koledar",
"sch_extra_field1" => "Model avta",
"sch_extra_field2" => "Tel.",
"sch_sd_events" => "Single-day events",
"sch_md_events" => "Multi-day events",
"sch_rc_events" => "Recurring events",
"sch_instructions" =>
"<h3>Navodila za iskanje po tekstu</h3>
<p>Podatkovna baza koledarja je lahko iskana za dogodke ki se ujemajo z iskanim tekstom.</p>
<br><p><b>Išči tekst</b>: Izbrana polja (poglej spodaj) za vsak edogodek bodo iskana. Iskalnik ni občutjiv na velike ali male črke.</p>
<p>Dva nadomestna znaka(wildcard characters) sta lahko uporabljena:</p>
<ul>
<li>Vprašalni znak (?) se bodo v polju za iskanje ujemali z vsakim enotnim znakom.<br>Npr.: '?e?r' se ujema z 'beer', 'dear', 'heir'.</li>
<li>'Asterisk' znak (*) seb odo v polju za iskanje ujemali z vsakim znakom .<br>Npr.: 'de*r' se ujema z 'December', 'dear', 'developer'.</li>
</ul>
<br><p><b>Polja dogodkov:</b>: Izbrana polja bodo samo iskana.</p>
<br><p><b>User group</b>: Events in the selected user group will be searched only.</p>
<br><p><b>Kategorija dogodkov</b>: Izbrani dogodki v kategorijah bodo samo iskani.</p>
<br><p><b>Pojavljanje med/b>: Začetni in končni datum sta oba opcijska. In case of a blank start / end date, the default number of days to search back and ahead will be $1 days and $2 days respectively.</p>
<br><p>To avoid repetitions of the same event, the search results will be split in single-day events, multi-day events and recurring events.</p>
<p>Rezultati iskanja bodo prikazani v kronološkem zaporedju.</p>",

//thumbnails.php
"tns_man_tnails_instr" => "Manage Thumbnails Instructions",
"tns_help_general" => "The images below can be used in the calendar views, by inserting their filename in the event's description field or in one of the extra fields. An image file name can be copied to the clipboard by clicking the desired thumbnail below; subsequently, in the Event window, the image name can be inserted in one of the fields by typing CTRL-V. Under each thumbnail you will find: the file name (without the user ID prefix), the file date and between brackets the last date the thumbnail is used by the calendar.",
"tns_help_upload" => "Thumbnails can be uploaded from your local computer by selecting the Browse button. To select multiple files, hold down the CTRL or SHIFT key while selecting (max. 20 at a time). The following file types are accepted: $1. Thumbnails with a size greater than $2 x $3 pixels (w x h) will be resized automatically.",
"tns_help_delete" => "Thumbnails with a red cross in the upper left corner can be deleted by selecting this cross. Thumbnails without red cross can not be deleted, because they are still used after $1. Caution: Deleted thumbnails cannot be retrieved!",
"tns_your_tnails" => "Your thumbnails",
"tns_other_tnails" => "Other thumbnails",
"tns_man_tnails" => "Manage Thumbnails",
"tns_sort_by" => "Sort by",
"tns_sort_order" => "Sort order",
"tns_search_fname" => "Search file name",
"tns_upload_tnails" => "Upload thumbnails",
"tns_name" => "name",
"tns_date" => "date",
"tns_ascending" => "ascending",
"tns_descending" => "descending",
"tns_not_used" => "not used",
"tns_infinite" => "infinite",
"tns_del_tnail" => "Delete thumbnail",
"tns_tnail" => "Thumbnail",
"tns_deleted" => "deleted",
"tns_tn_uploaded" => "thumbnail(s) uploaded",
"tns_overwrite" => "allow overwriting",
"tns_tn_exists" => "thumbnail already exists – not uploaded",
"tns_upload_error" => "upload error",
"tns_no_valid_img" => "is no valid image",
"tns_file_too_large" => "file too large",
"tns_resized" => "resized",
"tns_resize_error" => "resize error",

//contact.php
"con_msg_to_admin" => "Message to the Administrator",
"con_from" => "From",
"con_name" => "Name",
"con_email" => "Email",
"con_subject" => "Subject",
"con_message" => "Message",
"con_send_msg" => "Send message",
"con_fill_in_all_fields" => "Please fill in all fields",
"con_invalid_name" => "Invalid name",
"con_invalid_email" => "Invalid email address",
"con_no_urls" => "No web links allowed in the message",
"con_mail_error" => "Email problem. The message could not be sent. Please try again later.",
"con_con_msg" => "Contact message from the calendar",
"con_thank_you" => "Thank you for your message to the calendar",
"con_get_reply" => "You will receive a reply to your message as soon as possible",
"con_date" => "Date",
"con_your_msg" => "Your message",
"con_your_cal_msg" => "Your message to the calendar",
"con_has_been_sent" => "has been sent to the calendar administrator",
"con_confirm_eml_sent" => "A confirmation email has been sent to",

//msglog.php
"msl_search" => "Search",
"msl_date" => "date",
"msl_text" => "text",
"msl_sent_msgs" => "Sent notification messages",
"msl_no_logs_found" => "No message logs found!",
"msl_errors" => "ERRORS OCCURRED! See luxcal log",

//alert.php
"alt_message#0" => "Your session will soon expire!",
"alt_message#1" => "PHP SESSION EXPIRED",
"alt_message#2" => "Please restart the Calendar",
"alt_message#3" => "INVALID REQUEST",

//stand-alone sidebar (lcsbar.php)
"ssb_upco_events" => "Prihajajoči dogodki",
"ssb_all_day" => "Ves dan",
"ssb_none" => "Ni dogodkov."
);
?>
