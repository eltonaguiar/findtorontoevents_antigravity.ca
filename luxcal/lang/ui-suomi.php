<?php
/*
= LuxCal user interface language file =

Finnish translation: Heikki Laitala. Please send comments to rb@luxsoft.eu.

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "fi";

/* -- Titles on the Header of the Calendar and Date Picker -- */

$months = array("Tammikuu","Helmikuu","Maaliskuu","Huhtikuu","Toukokuu","Kesäkuu","Heinäkuu","Elokuu","Syyskuu","Lokakuu","Marraskuu","Joulukuu");
$months_m = array("Tam","Hel","Maa","Huh","Tou","Kes","Hei","Elo","Syy","Lok","Mar","Jou");
$wkDays = array("Sunnuntai","Maanantai","Tiistai","Keskiviikko","Torstai","Perjantai","Lauantai","Sunnuntai");
$wkDays_l = array("Su","Ma","Ti","Ke","To","Pe","La","Su");
$wkDays_m = array("Su","Ma","Ti","Ke","To","Pe","La","Su");
$wkDays_s = array("Su","Ma","Ti","Ke","To","Pe","La","Su");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Lähetä",
"log_in" => "Näytä",
"log_out" => "Piilota",
"portrait" => "Portrait",
"landscape" => "Landscape",
"none" => "Ei mitään.",
"all_day" => "All day",
"back" => "Takaisin",
"restart" => "Restart",
"by" => "by",
"of" => "-",
"max" => "max.",
"options" => "Optiot",
"done" => "Done",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "From", //e.g. from 9:30
"until" => "Until", //e.g. until 15:30
"to" => "To", //e.g. to 17-02-2020
"birthdays_in" => "Birthdays in",
"open_calendar" => "Avaa kalenteri",
"no_way" => "You are not authorized to perform this action",

//index.php
"title_log_in" => "Log In",
"title_profile" => "User Profile",
"title_upcoming" => "Tulevat",
"title_event" => "Varaus",
"title_check_event" => "Check Event",
"title_dmarking" => "Day Marking",
"title_search" => "Tekstihaku",
"title_contact" => "Contact Form",
"title_thumbnails" => "Thumbnail Images",
"title_user_guide" => "Ohje",
"title_settings" => "Kalenteriasetukset",
"title_edit_cats" => "Muuta kategorioita",
"title_edit_users" => "Muuta käyttäjätietoja",
"title_edit_groups" => "Edit User Groups",
"title_edit_text" => "Text Editor",
"title_manage_db" => "Hallinnoi tietokantaa",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Lisätyt / muutetut / poistetut varaukset",
"title_usr_import" => "User File Import - CSV format",
"title_usr_export" => "User File Export - CSV format",
"title_evt_import" => "Event File Import - CSV format",
"title_ics_import" => "Event File Import - iCal format",
"title_ics_export" => "Event File Export - iCal format",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "User Interface Styling",
"title_bd_calendar" => "Birthday Calendar",

//header.php
"hdr_button_back" => "Back to parent page",
"hdr_options_submit" => "Tee valintasi ja paina 'Done'",
"hdr_options_panel" => "Valintapaneeli",
"hdr_select_date" => "Valitse päivä",
"hdr_calendar" => "Kalenteriin",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Näkymä",
"hdr_lang" => "Kieli",
"hdr_all_cats" => "Kaikki kategoriat",
"hdr_all_groups" => "All Groups",
"hdr_all_users" => "Kaikki käyttäjät",
"hdr_go_to_view" => "Go to view",
"hdr_view_1" => "Vuosi",
"hdr_view_2" => "Kuukausi",
"hdr_view_3" => "Work month",
"hdr_view_4" => "Viikko",
"hdr_view_5" => "Work week",
"hdr_view_6" => "Päivä",
"hdr_view_7" => "Tulevat",
"hdr_view_8" => "Muutokset",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantt Chart",
"hdr_select_admin_functions" => "Valitse pääkäyttäjän toiminnot",
"hdr_admin" => "Hallinta",
"hdr_settings" => "Asetukset",
"hdr_categories" => "Kategoriat",
"hdr_users" => "Käyttäjät",
"hdr_groups" => "User Groups",
"hdr_text_editor" => "Text Editor",
"hdr_database" => "Tietokanta",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "User Import (CSV file)",
"hdr_export_usr" => "User Export (CSV file)",
"hdr_import_csv" => "Event Import (CSV file)",
"hdr_import_ics" => "Event Import (iCal file)",
"hdr_export_ics" => "Event Export (iCal file)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Styling",
"hdr_back_to_cal" => "Back to calendar view",
"hdr_button_print" => "Tulosta",
"hdr_print_page" => "Tulosta tämä sivu",
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
"hdr_button_todo" => "Todo",
"hdr_todo_list" => "Todo List",
"hdr_button_upco" => "Upcoming",
"hdr_upco_list" => "Tulevat",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Search",
"hdr_search" => "Haku",
"hdr_button_add" => "Add",
"hdr_add_event" => "Lisää varaus",
"hdr_button_help" => "Help",
"hdr_user_guide" => "User Guide",
"hdr_gen_guide" => "General User Guide",
"hdr_cs_guide" => "Context-sensitive User Guide",
"hdr_gen_help" => "General help",
"hdr_prev_help" => "Previous help",
"hdr_open_menu" => "Open Menu",
"hdr_side_menu" => "Side Menu",
"hdr_dest_cals" => "Destination Calendar(s)",
"hdr_copy_evt" => "Copy Event",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "tänään", //dtpicker.js
"hdr_clear" => "tyhjä", //dtpicker.js

//event.php
"evt_no_title" => "Otsikko puuttuu",
"evt_no_start_date" => "Aloituspäivä puuttuu",
"evt_bad_date" => "Virheellinen päiväys",
"evt_bad_rdate" => "Virheellinen toiston päättymispäivä",
"evt_no_start_time" => "Aloitusaika puuttuu",
"evt_bad_time" => "Virheellinen aika",
"evt_end_before_start_time" => "Päättymisaika ennen alkamisaikaa",
"evt_end_before_start_date" => "Päättymispäivä ennen alkupäivää",
"evt_until_before_start_date" => "Toiston päättymispäivä ennen alkupäivää",
"evt_default_duration" => "Default event duration of $1 hours and $2 minutes",
"evt_fixed_duration" => "Fixed event duration of $1 hours and $2 minutes",
"evt_approved" => "Event approved",
"evt_apd_locked" => "Event approved and locked",
"evt_title" => "Otsikko",
"evt_venue" => "Paikka",
"evt_address_button" => "An address between ! marks will become a button",
"evt_list" => "List",
"evt_category" => "Kategoria",
"evt_subcategory" => "Subcategory",
"evt_description" => "Kuvaus",
"evt_attachments" => "Attachments",
"evt_attach_file" => "Attach file",
"evt_click_to_open" => "Click to open",
"evt_click_to_remove" => "Click to remove",
"evt_no_pdf_img_vid" => "Attachment should be pdf, image or video",
"evt_error_file_upload" => "Error uploading file",
"evt_upload_too_large" => "Uploaded file too large",
"evt_date_time" => "Päivä / aika",
"evt_date" => "Päivä",
"evt_private" => "Yksityisvaraus",
"evt_start_date" => "Alkupäivä",
"evt_end_date" => "Päättymispäivä",
"evt_select_date" => "Valitse päivä",
"evt_select_time" => "Valitse aika",
"evt_all_day" => "Koko pv",
"evt_no_time" => "No Time",
"evt_change" => "Muuta",
"evt_set_repeat" => "Aseta toisto",
"evt_set" => "OK",
"evt_help" => "help",
"evt_repeat_not_supported" => "Määritettyä toistoa ei tueta",
"evt_no_repeat" => "Ei toistoa",
"evt_rolling" => "Rolling",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Toisto joka",
"evt_until" => "asti",
"evt_blank_no_end" => "tyhjä: ei päättymispäivää",
"evt_each_month" => "joka kuukausi",
"evt_interval2_1" => "ensimmäinen",
"evt_interval2_2" => "toinen",
"evt_interval2_3" => "kolmas",
"evt_interval2_4" => "neljäs",
"evt_interval2_5" => "viimeinen",
"evt_period1_1" => "päivä",
"evt_period1_2" => "viikko",
"evt_period1_3" => "kuukausi",
"evt_period1_4" => "vuosi",
"evt_notification" => "Ilmoitus",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "nyt ja/tai",
"evt_event_added" => "Uusi varaus",
"evt_event_edited" => "Muutettu varaus",
"evt_event_deleted" => "Poistettu varaus",
"evt_event_approved" => "Approved event",
"evt_days_before_event" => "päivä(ä) ennen varausta",
"evt_to" => "To",
"evt_not_help" => "List of recipients separated by semicolons. A recipient can be a user name, an email address, a mobile phone number, a Telegram chat ID or, enclosed in square brackets, the name (without type) of a .txt file with recipients in the 'reciplists' folder. This file should contain one recipient (a user name, an email address, a mobile phone number or a Telegram chat ID) per line.<br>Maximum field length: 255 characters.",
"evt_recip_list_too_long" => "Sähköpostilista liian pitkä.",
"evt_no_recip_list" => "Vastaanottajat-luettelo on tyhjä",
"evt_not_in_past" => "Muistutuspäivä ohitettu",
"evt_not_days_invalid" => "Muistutuspäivä virheellinen",
"evt_status" => "Status",
"evt_descr_help" => "The following items can be used in the description fields ...<br>• HTML tags &lt;b&gt;, &lt;i&gt;, &lt;u&gt; and &lt;s&gt; for bold, italic, underlined and striked-through text.",
"evt_descr_help_img" => "• small images (thumbnails) in the format: 'image_name.ext'. The thumbnail files, with file extension .gif, .jpg or .png, must be present in 'thumbnails' folder. If enabled, the Thumbnails page can be used to upload thumbnail files.",
"evt_descr_help_eml" => "• Mailto-links in the format: 'email address' or 'email address [name]', where 'name' will be the title of the hyperlink. E.g. xxx@yyyy.zzz [For info click here].",
"evt_descr_help_url" => "• URL links in the format: 'url' or 'url [name]', where 'name' will be the title of the link. If 'S:' is placed in front of the URL, the link will open in the same page/tab, otherwise the link will open in a blank page/tab. E.g. S:https://www.google.com [search].",
"evt_confirm_added" => "varaus lisätty",
"evt_confirm_saved" => "varaus päivitetty",
"evt_confirm_deleted" => "varaus poistettu",
"evt_add_close" => "Lisää ja sulje",
"evt_add" => "Lisää",
"evt_edit" => "Muuta",
"evt_save_close" => "Tallenna ja sulje",
"evt_save" => "Tallenna",
"evt_clone" => "Tallenna uutena",
"evt_delete" => "Poista",
"evt_close" => "Sulje",
"evt_added" => "Lisätty",
"evt_edited" => "Muutettu",
"evt_is_repeating" => "on toistuva varaus.",
"evt_is_multiday" => "on monipäiväinen varaus.",
"evt_edit_series_or_occurrence" => "Haluatko muuttaa sarjaa vai pelkästään tätä varausta?",
"evt_edit_series" => "Muuta sarjaa",
"evt_edit_occurrence" => "Muuta varausta",
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
"vws_add_event" => "Lisää varaus",
"vws_edit_event" => "Edit Event",
"vws_see_event" => "See event details",
"vws_view_month" => "Näytä kuukausi",
"vws_view_week" => "Näytä viikko",
"vws_view_day" => "Näytä päivä",
"vws_click_for_full" => "valitse kuukausi koko kalenterinäkymään",
"vws_view_full" => "Näytä koko kalenteri",
"vws_prev_year" => "Edellinen vuosi",
"vws_next_year" => "Seuraava vuosi",
"vws_prev_month" => "Edellinen kuukausi",
"vws_next_month" => "Seuraava kuukausi",
"vws_forward" => "Forward",
"vws_backward" => "Backward",
"vws_mark_day" => "Mark day",
"vws_today" => "Tänään",
"vws_back_to_today" => "Takaisin tähän kuukauteen",
"vws_back_to_main_cal" => "Back to the main calendar month",
"vws_week" => "Viikko",
"vws_wk" => "vk",
"vws_time" => "Aika",
"vws_events" => "Varaukset",
"vws_all_day" => "Koko pv",
"vws_earlier" => "Earlier",
"vws_later" => "Later",
"vws_venue" => "Paikka",
"vws_address" => "Address",
"vws_events_for_next" => "Tulevat varaukset seuraaville",
"vws_days" => "päivälle",
"vws_added" => "Lisätty",
"vws_edited" => "Muutettu",
"vws_notify" => "Muistutus",
"vws_none_due_in" => "No events due in the next",
"vws_evt_cats" => "Event categories",
"vws_cal_users" => "Calendar users",
"vws_no_users" => "No users in selected group(s)",
"vws_start" => "Start",
"vws_duration" => "Duration",
"vws_no_events_in_gc" => "No events in the selected period",
"vws_download" => "Download",
"vws_download_title" => "Download a file with these events",
"vws_send_mail" => "Send email",

//changes.php
"chg_select_date" => "Valitse alkupäivä",
"chg_notify" => "Muistutus",
"chg_days" => "Päivä(ä)",
"chg_added" => "Lisätty",
"chg_edited" => "Muuttaja",
"chg_deleted" => "Poistettu",
"chg_changed_on" => "Muutettu",
"chg_no_changes" => "Ei muutoksia.",

//search.php
"sch_define_search" => "Määritä haku",
"sch_search_text" => "Etsi tekstiä",
"sch_event_fields" => "Varaustiedot",
"sch_all_fields" => "Kaikki tiedot",
"sch_title" => "Otsikko",
"sch_description" => "Kuvaus",
"sch_venue" => "Paikka",
"sch_user_group" => "User group",
"sch_event_cat" => "Kategoria",
"sch_all_groups" => "All Groups",
"sch_all_cats" => "Kaikki kategoriat",
"sch_occurring_between" => "Aikaväli",
"sch_select_start_date" => "Valitse alkupäivä",
"sch_select_end_date" => "Valitse päättymispäivä",
"sch_search" => "Etsi",
"sch_invalid_search_text" => "Etsittävä teksti tyhjä tai liian lyhyt",
"sch_bad_start_date" => "Virheellinen alkupäivä",
"sch_bad_end_date" => "Virheellinen päättymispäivä",
"sch_no_results" => "Ei tuloksia",
"sch_new_search" => "Uusi haku",
"sch_calendar" => "Siirry kalenteriin",
"sch_extra_field1" => "Extra field 1",
"sch_extra_field2" => "Extra field 2",
"sch_sd_events" => "Single-day events",
"sch_md_events" => "Multi-day events",
"sch_rc_events" => "Recurring events",
"sch_instructions" =>
"<h3>Tekstin hakuohjeet</h3>
<p>Kalenterin tietokannasta voidaan hakea varauksia, joissa teksti esiinytyy.</p>
<br><p><b>Etsittävä teksti</b>: Jokaisesta varauksesta etsitään tekstijonoa. Haku ei erottele isoja tai pieniä kirjaimia.</p>
<p>Kahta jokerimerkkiä voi käyttää:</p>
<ul>
<li>Kysymysmerkki (?) hakutekstissä voi olla mikä vain yksittäinen merkki.<br>Esim.: '?e?r' voi tarkoittaa 'beer', 'dear', 'heir'.</li>
<li>Tähtimerkki (*;) hakutekstissä voi olla mikä vain merkkijono.<br>Esim.: 'de*r' voi tarkoittaa 'December', 'dear', 'developer'.</li>
</ul>
<br><p><b>Varauskentät</b>: Vain valituista kentistä etsitään.</p>
<br><p><b>User group</b>: Events in the selected user group will be searched only.</p>
<br><p><b>Varauskategoriat</b>: Vain valituista kategorioista etsitään.</p>
<br><p><b>Aikaväli</b>: Sekä alku- että loppupäivä ovat valinnaisia. In case of a blank start / end date, the default number of days to search back and ahead will be $1 days and $2 days respectively.</p>
<br><p>To avoid repetitions of the same event, the search results will be split in single-day events, multi-day events and recurring events.</p>
<p>Hakutulokset näytetään kronologisessa järjestyksessä.</p>",

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
"ssb_upco_events" => "Upcoming Events",
"ssb_all_day" => "All day",
"ssb_none" => "No events."
);
?>
