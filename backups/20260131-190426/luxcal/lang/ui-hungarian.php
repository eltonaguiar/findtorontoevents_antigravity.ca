<?php
/*
= LuxCal lamguage file =

This file has been produced by LuxSoft. Please send comments / improvements to rb@luxsoft.eu.

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "hu";

/* -- Titles on the Header of the Calendar and Date Picker -- */

$months = array("január","február","március","április","május","június","július","augusztus","szeptember","október","november","december");
$months_m = array("jan","feb","már","ápr","máj","jún","júl","aug","sze","okt","nov","dec");
$wkDays = array("vasárnap","hétfő","kedd","szerda","csütörtök","péntek","szombat","vasárnap");
$wkDays_l = array("vas","hét","ked","sze","csü","pén","szo","vas");
$wkDays_m = array("Vas","Hé","Ke","Sze","Csü","Pé","Szo","Vas");
$wkDays_s = array("V","H","K","SZ","CS","P","SZ","V");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Submit",
"log_in" => "Bejelentkezés",
"log_out" => "Kijelentkezés",
"portrait" => "Portrait",
"landscape" => "Landscape",
"none" => "None.",
"all_day" => "All day",
"back" => "Back",
"restart" => "Restart",
"by" => "by",
"of" => "of",
"max" => "max.",
"options" => "Options",
"done" => "Done",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "From", //e.g. from 9:30
"until" => "Until", //e.g. until 15:30
"to" => "To", //e.g. to 17-02-2020
"birthdays_in" => "Birthdays in",
"open_calendar" => "Nyílt naptár",
"no_way" => "You are not authorized to perform this action",

//index.php
"title_log_in" => "Log In",
"title_profile" => "User Profile",
"title_upcoming" => "Következő események",
"title_event" => "Esemény",
"title_check_event" => "Check Event",
"title_dmarking" => "Day Marking",
"title_search" => "Text Search",
"title_contact" => "Contact Form",
"title_thumbnails" => "Thumbnail Images",
"title_user_guide" => "LuxCal Felhasználói Útmutató",
"title_settings" => "Naptár beállítás",
"title_edit_cats" => "Kategóriák szerkesztése",
"title_edit_users" => "Felhasználók szerkesztése",
"title_edit_groups" => "Edit User Groups",
"title_edit_text" => "Text Editor",
"title_manage_db" => "Kezeli database",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Hozzáadott / Szerkesztett / Törölt események",
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
"hdr_options_submit" => "When done click this header or 'Done'",
"hdr_options_panel" => "Options panel",
"hdr_select_date" => "Dátum kiválasztása",
"hdr_calendar" => "Calendar",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Nézet",
"hdr_lang" => "Nyelvet",
"hdr_all_cats" => "Minden kategória",
"hdr_all_groups" => "All Groups",
"hdr_all_users" => "Minden felhasználó",
"hdr_go_to_view" => "Go to view",
"hdr_view_1" => "Év",
"hdr_view_2" => "Hónap",
"hdr_view_3" => "Hónap munka",
"hdr_view_4" => "Hét",
"hdr_view_5" => "Hét munka",
"hdr_view_6" => "Nap",
"hdr_view_7" => "Elkövetkező",
"hdr_view_8" => "Változtatás",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantt Chart",
"hdr_select_admin_functions" => "Admin funkció kiválasztása",
"hdr_admin" => "Adminisztráció",
"hdr_settings" => "Beállítások",
"hdr_categories" => "Kategóriák",
"hdr_users" => "Felhasználók",
"hdr_groups" => "User Groups",
"hdr_text_editor" => "Text Editor",
"hdr_database" => "Database",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "User Import (CSV file)",
"hdr_export_usr" => "User Export (CSV file)",
"hdr_import_csv" => "Event Import (CSV file)",
"hdr_import_ics" => "Event Import (iCal file)",
"hdr_export_ics" => "Event Export (iCal file)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Styling",
"hdr_back_to_cal" => "Back to calendar view",
"hdr_button_print" => "Nyomtatás",
"hdr_print_page" => "Az oldal kinyomtatása",
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
"hdr_upco_list" => "Következő események",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Search",
"hdr_search" => "Text Search",
"hdr_button_add" => "Add",
"hdr_add_event" => "Esemény hozzáadás",
"hdr_button_help" => "Segítség",
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
"hdr_today" => "ma", //dtpicker.js
"hdr_clear" => "törli", //dtpicker.js

//event.php
"evt_no_title" => "Nincs cím",
"evt_no_start_date" => "Nincs kezdő dátum",
"evt_bad_date" => "Rossz dátum",
"evt_bad_rdate" => "Rossz ismételt befejező dátum",
"evt_no_start_time" => "Nincs kezdő időpont",
"evt_bad_time" => "Rossz időpont",
"evt_end_before_start_time" => "A záró időpont megelőzi a kezdő időpontot",
"evt_end_before_start_date" => "A záró dátum megelőzi a kezdő dátumot",
"evt_until_before_start_date" => "Repeat end megelőzi a kezdő dátumot",
"evt_default_duration" => "Default event duration of $1 hours and $2 minutes",
"evt_fixed_duration" => "Fixed event duration of $1 hours and $2 minutes",
"evt_approved" => "Event approved",
"evt_apd_locked" => "Event approved and locked",
"evt_title" => "Cím",
"evt_venue" => "Helyszín",
"evt_address_button" => "An address between ! marks will become a button",
"evt_list" => "List",
"evt_category" => "Kategória",
"evt_subcategory" => "Subcategory",
"evt_description" => "Leírás",
"evt_attachments" => "Attachments",
"evt_attach_file" => "Attach file",
"evt_click_to_open" => "Click to open",
"evt_click_to_remove" => "Click to remove",
"evt_no_pdf_img_vid" => "Attachment should be pdf, image or video",
"evt_error_file_upload" => "Error uploading file",
"evt_upload_too_large" => "Uploaded file too large",
"evt_date_time" => "Dátum / idő",
"evt_date" => "Dátum",
"evt_private" => "Saját esemény",
"evt_start_date" => "Kezdeti",
"evt_end_date" => "Befejező",
"evt_select_date" => "Dátum kiválasztása",
"evt_select_time" => "Select time",
"evt_all_day" => "Egésznapos",
"evt_no_time" => "No Time",
"evt_change" => "Változtatás",
"evt_set_repeat" => "Ismétlődés beállítása",
"evt_set" => "OK",
"evt_help" => "help",
"evt_repeat_not_supported" => "Specified repetition not supported",
"evt_no_repeat" => "Nincs ismétlődés",
"evt_rolling" => "Rolling",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Ismétel minden",
"evt_until" => "eddig",
"evt_blank_no_end" => "üres: nincs befejezés",
"evt_each_month" => "each month",
"evt_interval2_1" => "első",
"evt_interval2_2" => "második",
"evt_interval2_3" => "harmadik",
"evt_interval2_4" => "negyedik",
"evt_interval2_5" => "utolsó",
"evt_period1_1" => "nap",
"evt_period1_2" => "hét",
"evt_period1_3" => "hónap",
"evt_period1_4" => "év",
"evt_notification" => "Értesítés",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "now and/or",
"evt_event_added" => "The following event has been added",
"evt_event_edited" => "The following event has been modified",
"evt_event_deleted" => "The following event has been deleted",
"evt_event_approved" => "Approved event",
"evt_days_before_event" => "nappal az esemény",
"evt_to" => "To",
"evt_not_help" => "List of recipients separated by semicolons. A recipient can be a user name, an email address, a mobile phone number, a Telegram chat ID or, enclosed in square brackets, the name (without type) of a .txt file with recipients in the 'reciplists' folder. This file should contain one recipient (a user name, an email address, a mobile phone number or a Telegram chat ID) per line.<br>Maximum field length: 255 characters.",
"evt_recip_list_too_long" => "Címek listája túl sok karakterből áll.",
"evt_no_recip_list" => "Értesítési címlista hiányzik",
"evt_not_in_past" => "Notification date in past",
"evt_not_days_invalid" => "Notification days invalid",
"evt_status" => "Status",
"evt_descr_help" => "The following items can be used in the description fields ...<br>• HTML tags &lt;b&gt;, &lt;i&gt;, &lt;u&gt; and &lt;s&gt; for bold, italic, underlined and striked-through text.",
"evt_descr_help_img" => "• small images (thumbnails) in the format: 'image_name.ext'. The thumbnail files, with file extension .gif, .jpg or .png, must be present in 'thumbnails' folder. If enabled, the Thumbnails page can be used to upload thumbnail files.",
"evt_descr_help_eml" => "• Mailto-links in the format: 'email address' or 'email address [name]', where 'name' will be the title of the hyperlink. E.g. xxx@yyyy.zzz [For info click here].",
"evt_descr_help_url" => "• URL links in the format: 'url' or 'url [name]', where 'name' will be the title of the link. If 'S:' is placed in front of the URL, the link will open in the same page/tab, otherwise the link will open in a blank page/tab. E.g. S:https://www.google.com [search].",
"evt_confirm_added" => "event added",
"evt_confirm_saved" => "event saved",
"evt_confirm_deleted" => "event deleted",
"evt_add_close" => "Add and close",
"evt_add" => "Hozzáadása",
"evt_edit" => "Szerkesztése",
"evt_save_close" => "Mentés és bezárás ",
"evt_save" => "Mentés",
"evt_clone" => "Mentés új",
"evt_delete" => "Törlése",
"evt_close" => "Bezár",
"evt_added" => "Hozzáadva",
"evt_edited" => "Edited",
"evt_is_repeating" => "is a repeating event.",
"evt_is_multiday" => "is a multi-day event.",
"evt_edit_series_or_occurrence" => "Do you want to edit the series or this occurrence?",
"evt_edit_series" => "Edit the series",
"evt_edit_occurrence" => "Edit this occurrence",
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
"vws_add_event" => "Esemény hozzáadása",
"vws_edit_event" => "Edit Event",
"vws_see_event" => "See event details",
"vws_view_month" => "Hónap nézet",
"vws_view_week" => "Hét nézet",
"vws_view_day" => "Nap nézet",
"vws_click_for_full" => "for full calendar click month",
"vws_view_full" => "View full calendar",
"vws_prev_year" => "Previous year",
"vws_next_year" => "Next year",
"vws_prev_month" => "Previous month",
"vws_next_month" => "Next month",
"vws_forward" => "Forward",
"vws_backward" => "Backward",
"vws_mark_day" => "Mark day",
"vws_today" => "Ma",
"vws_back_to_today" => "Vissza a hónapban a ma",
"vws_back_to_main_cal" => "Back to the main calendar month",
"vws_week" => "Hét",
"vws_wk" => "hét",
"vws_time" => "idő",
"vws_events" => "Események",
"vws_all_day" => "Egésznapos",
"vws_earlier" => "Earlier",
"vws_later" => "Later",
"vws_venue" => "Helyszín",
"vws_address" => "Address",
"vws_events_for_next" => "Következő események a következő",
"vws_days" => "nap",
"vws_added" => "Hozzáadva",
"vws_edited" => "Szerkesztve",
"vws_notify" => "Értesítés",
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
"chg_select_date" => "Kezdő dátum kiválasztása",
"chg_notify" => "Értesítő",
"chg_days" => "Nap",
"chg_added" => "Hozzáadva",
"chg_edited" => "Szerkesztve",
"chg_deleted" => "Törölve",
"chg_changed_on" => "Módosítása",
"chg_no_changes" => "Nincs változás.",

//search.php
"sch_define_search" => "Define Search",
"sch_search_text" => "Search text",
"sch_event_fields" => "Event fields",
"sch_all_fields" => "All fields",
"sch_title" => "Title",
"sch_description" => "Description",
"sch_venue" => "Venue",
"sch_user_group" => "User group",
"sch_event_cat" => "Event category",
"sch_all_groups" => "All Groups",
"sch_all_cats" => "All Categories",
"sch_occurring_between" => "Occurring between",
"sch_select_start_date" => "Select start date",
"sch_select_end_date" => "Select end date",
"sch_search" => "Search",
"sch_invalid_search_text" => "Search text missing or too short",
"sch_bad_start_date" => "Bad start date",
"sch_bad_end_date" => "Bad end date",
"sch_no_results" => "No results found",
"sch_new_search" => "New Search",
"sch_calendar" => "Go to calendar",
"sch_extra_field1" => "Extra field 1",
"sch_extra_field2" => "Extra field 2",
"sch_sd_events" => "Single-day events",
"sch_md_events" => "Multi-day events",
"sch_rc_events" => "Recurring events",
"sch_instructions" =>
"<h3>Text Search Instructions</h3>
<p>The calendar database can be searched for events matching specific text.</p>
<br><p><b>Search text</b>: The selected fields (see below) of each event 
will be searched. For characters a - z the search is case insensitive.</p>
<p>Two wildcard characters can be used:</p>
<ul>
<li>A question mark (?) in the search text will match any single character.<br>E.g.: '?e?r' matches 'beer', 'dear', 'heir'.</li>
<li>An asterisk (*) in the search text will match any number of characters.<br>E.g.: 'de*r' matches 'December', 'dear', 'developer'.</li>
</ul>
<br><p><b>Event fields</b>: The selected fields will be searched only.</p>
<br><p><b>User group</b>: Events in the selected user group will be searched 
only.</p>
<br><p><b>Event category</b>: Events in the selected category will be searched 
only.</p>
<br><p><b>Occurring between</b>: The start and end date are both optional. In 
case of a blank start / end date, the default number of days to search back and 
ahead will be $1 days and $2 days respectively.</p>
<br><p>To avoid repetitions of the same event, the search results will be split 
in single-day events, multi-day events and recurring events.</p>
<p>The search results will be displayed in chronological order.</p>",

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
