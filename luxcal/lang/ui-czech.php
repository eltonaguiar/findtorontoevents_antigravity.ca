<?php
/*
= LuxCal user interface language file =

This file has been produced by LuxSoft. Please send your comments to rb@luxsoft.eu.

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "cs";

/* -- Titles on the Header of the Calendar and Date Picker -- */

$months = array("leden","únor","březen","duben","květen","červen","červenec","srpen","září","říjen","listopad","prosinec");
$months_m = array("led","úno","bře","dub","kvě","čvn","čnc","srp","zář","říj","lis","pro");
$wkDays = array("neděle","pondělí","úterý","středa","čtvrtek","pátek","sobota","neděle");
$wkDays_l = array("ned","pon","úte","stř","čtv","pát","sob","ned");
$wkDays_m = array("ne","po","út","st","čt","pá","so","ne");
$wkDays_s = array("N","P","Ú","S","Č","P","S","N");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Odeslat",
"log_in" => "Přihlásit",
"log_out" => "Odhlásit",
"portrait" => "Portrait",
"landscape" => "Landscape",
"none" => "Nic",
"all_day" => "All day",
"back" => "Zpět",
"restart" => "Restart",
"by" => "autor",
"of" => "v",
"max" => "max.",
"options" => "Volby",
"done" => "Hotovo",
"at_time" => '-', //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "From", //e.g. from 9:30
"until" => "Until", //e.g. until 15:30
"to" => "To", //e.g. to 17-02-2020
"birthdays_in" => "Birthdays in",
"open_calendar" => "Otevřít kalendář",
"no_way" => "Nejste oprávnění provádět tuto akci",

//index.php
"title_log_in" => "Přihlášení",
"title_profile" => "User Profile",
"title_upcoming" => "Blízké události",
"title_event" => "Událost",
"title_check_event" => "Příznaky události",
"title_dmarking" => "Day Marking",
"title_search" => "Textové vyhledávání",
"title_contact" => "Contact Form",
"title_thumbnails" => "Thumbnail Images",
"title_user_guide" => "Příručka LuxCal",
"title_settings" => "Upravit nastavení kalendáře",
"title_edit_cats" => "Upravit kategorie",
"title_edit_users" => "Upravit uživatele",
"title_edit_groups" => "Změnit skupiny uživatele",
"title_edit_text" => "Text Editor",
"title_manage_db" => "Správa databáze",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Přidané / Změněné / Smazané události",
"title_usr_import" => "User File Import - CSV format",
"title_usr_export" => "User File Export - CSV format",
"title_evt_import" => "Event File Import - CSV format",
"title_ics_import" => "Event File Import - iCal format",
"title_ics_export" => "Event File Export - iCal format",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "User Interface Styling",
"title_bd_calendar" => "Birthday Calendar",

//header.php
"hdr_button_back" => "Výchozí stránka",
"hdr_options_submit" => "Vyberte si možnosti a stiskněte Hotovo",
"hdr_options_panel" => "Zobrazit panel voleb",
"hdr_select_date" => "Skok na datum",
"hdr_calendar" => "Kalendář",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Pohled",
"hdr_lang" => "Jazyk",
"hdr_all_cats" => "Všechny kategorie",
"hdr_all_groups" => "All Groups",
"hdr_all_users" => "Všichni uživatelé",
"hdr_go_to_view" => "Go to view",
"hdr_view_1" => "Rok",
"hdr_view_2" => "Měsíc",
"hdr_view_3" => "Pracovní měsíc",
"hdr_view_4" => "Týden",
"hdr_view_5" => "Pracovní týden",
"hdr_view_6" => "Den",
"hdr_view_7" => "Blízké události",
"hdr_view_8" => "Změny",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantt Chart",
"hdr_select_admin_functions" => "Zvolte funkci pro nastavení",
"hdr_admin" => "Administrace",
"hdr_settings" => "Nastavení",
"hdr_categories" => "Kategorie",
"hdr_users" => "Uživatelé",
"hdr_groups" => "Skupiny",
"hdr_text_editor" => "Text Editor",
"hdr_database" => "Databáze",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "User Import (CSV file)",
"hdr_export_usr" => "User Export (CSV file)",
"hdr_import_csv" => "Event Import (CSV file)",
"hdr_import_ics" => "Event Import (iCal file)",
"hdr_export_ics" => "Event Export (iCal file)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Styling",
"hdr_back_to_cal" => "Zpět na kalendář",
"hdr_button_print" => "Tisk",
"hdr_print_page" => "Tisk této stránky",
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
"hdr_button_todo" => "Úkoly",
"hdr_todo_list" => "Úkoly",
"hdr_button_upco" => "Blízké události",
"hdr_upco_list" => "Přehled chystaných událostí",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Hledat",
"hdr_search" => "Hledat v kalendáři",
"hdr_button_add" => "Přidat",
"hdr_add_event" => "Přidat událost",
"hdr_button_help" => "Nápověda",
"hdr_user_guide" => "Uživatelská příručka",
"hdr_gen_guide" => "General User Guide",
"hdr_cs_guide" => "Context-sensitive User Guide",
"hdr_gen_help" => "General help",
"hdr_prev_help" => "Previous help",
"hdr_open_menu" => "Open Menu",
"hdr_side_menu" => "Side Menu",
"hdr_dest_cals" => "Destination Calendar(s)",
"hdr_copy_evt" => "Copy Event",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "Dnes", //dtpicker.js
"hdr_clear" => "Smazat", //dtpicker.js

//event.php
"evt_no_title" => "Bez názvu",
"evt_no_start_date" => "Nemá počáteční datum",
"evt_bad_date" => "Chybné datum",
"evt_bad_rdate" => "Chybné datum konce opakování",
"evt_no_start_time" => "Bez počátečního data",
"evt_bad_time" => "Chybný čas",
"evt_end_before_start_time" => "Koncový čas je před začátkem",
"evt_end_before_start_date" => "Koncové datum je před začátkem",
"evt_until_before_start_date" => "Konec opakování je před začátkem",
"evt_default_duration" => "Default event duration of $1 hours and $2 minutes",
"evt_fixed_duration" => "Fixed event duration of $1 hours and $2 minutes",
"evt_approved" => "Událost schválena",
"evt_apd_locked" => "Událost schválena a uzamčena",
"evt_title" => "Název",
"evt_venue" => "Místo",
"evt_address_button" => "An address between ! marks will become a button",
"evt_list" => "List",
"evt_category" => "Kategorie",
"evt_subcategory" => "Subcategory",
"evt_description" => "Popis",
"evt_attachments" => "Attachments",
"evt_attach_file" => "Attach file",
"evt_click_to_open" => "Click to open",
"evt_click_to_remove" => "Click to remove",
"evt_no_pdf_img_vid" => "Attachment should be pdf, image or video",
"evt_error_file_upload" => "Error uploading file",
"evt_upload_too_large" => "Uploaded file too large",
"evt_date_time" => "Datum / čas",
"evt_date" => "Datum",
"evt_private" => "neveřejná událost",
"evt_start_date" => "Začátek",
"evt_end_date" => "Konec",
"evt_select_date" => "Zvolte datum",
"evt_select_time" => "Zvolte čas",
"evt_all_day" => "Celý den",
"evt_no_time" => "No Time",
"evt_change" => "Změnit",
"evt_set_repeat" => "Opakování",
"evt_set" => "OK",
"evt_help" => "nápověda",
"evt_repeat_not_supported" => "Zadané opakování není podporováno",
"evt_no_repeat" => "Bez opakování",
"evt_rolling" => "Rolling",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Opakovat každý",
"evt_until" => "až do",
"evt_blank_no_end" => "prázdné: nekončí",
"evt_each_month" => "měsíce",
"evt_interval2_1" => "první",
"evt_interval2_2" => "druhý",
"evt_interval2_3" => "třetí",
"evt_interval2_4" => "čtvrtý",
"evt_interval2_5" => "poslední",
"evt_period1_1" => "den",
"evt_period1_2" => "týden",
"evt_period1_3" => "měsíc",
"evt_period1_4" => "rok",
"evt_notification" => "Oznámení",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "teď a nebo",
"evt_event_added" => "Nová událost",
"evt_event_edited" => "Změněná událost",
"evt_event_deleted" => "Smazaná událost",
"evt_event_approved" => "Approved event",
"evt_days_before_event" => "dní před začátkem",
"evt_to" => "Na",
"evt_not_help" => "List of recipients separated by semicolons. A recipient can be a user name, an email address, a mobile phone number, a Telegram chat ID or, enclosed in square brackets, the name (without type) of a .txt file with recipients in the 'reciplists' folder. This file should contain one recipient (a user name, an email address, a mobile phone number or a Telegram chat ID) per line.<br>Maximum field length: 255 characters.",
"evt_recip_list_too_long" => "Seznam je příliš dlouhý.",
"evt_no_recip_list" => "Chybí adresy pro zaslání upozornění",
"evt_not_in_past" => "Datum připomenutí již uplynulo",
"evt_not_days_invalid" => "Dny připomenutí jsou chybné",
"evt_status" => "Stav",
"evt_descr_help" => "V poli Popis můžete použít následující prvky ...<br>- HTML značky &lt;b&gt;, &lt;i&gt;, &lt;u&gt; a &lt;s&gt; for tučné, kurzívu, podtržené a přeškrtnuté písmo.",
"evt_descr_help_img" => "• náhledy obrázků (thumbnails) v tomto formátu: 'image_name.ext'. The thumbnail files, with file extension .gif, .jpg or .png, must be present in 'thumbnails' folder. If enabled, the Thumbnails page can be used to upload thumbnail files.",
"evt_descr_help_eml" => "• Mailto-links in the format: 'email address' or 'email address [name]', where 'name' will be the title of the link. E.g. xxx@yyyy.zzz [For info click here].",
"evt_descr_help_url" => "• URL odkazy v následujícím formátu: url nebo url [jméno], kde 'jméno' bude název odkazu. If 'S:' is placed in front of the URL, the link will open in the same page/tab, otherwise the link will open in a blank page/tab. Např. S:https://www.google.com [hledat].",
"evt_confirm_added" => "událost přidána",
"evt_confirm_saved" => "událost uložena",
"evt_confirm_deleted" => "událost smazána",
"evt_add_close" => "Přidat a zavřít",
"evt_add" => "Přidat",
"evt_edit" => "Upravit",
"evt_save_close" => "Uložit a zavřít",
"evt_save" => "Uložit",
"evt_clone" => "Uložit jako nové",
"evt_delete" => "Smazat",
"evt_close" => "Zavřít",
"evt_added" => "Vloženo",
"evt_edited" => "upravil",
"evt_is_repeating" => "je opakovaná událost.",
"evt_is_multiday" => "je vicedenní událost.",
"evt_edit_series_or_occurrence" => "Chcete smazat sérii tohoto opakování",
"evt_edit_series" => "Upravit sérii",
"evt_edit_occurrence" => "Upravit tento výskyt",
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
"vws_add_event" => "Přidat událost",
"vws_edit_event" => "Edit Event",
"vws_see_event" => "See event details",
"vws_view_month" => "Měsíční pohled",
"vws_view_week" => "Týdenní pohled",
"vws_view_day" => "Denní pohled",
"vws_click_for_full" => "Kalendář akcí - Klikněte na název měsíce",
"vws_view_full" => "Ukázat celý kalendář",
"vws_prev_year" => "Předchozí rok",
"vws_next_year" => "Další rok",
"vws_prev_month" => "Předchozí měsíc",
"vws_next_month" => "Další měsíc",
"vws_forward" => "Forward",
"vws_backward" => "Backward",
"vws_mark_day" => "Mark day",
"vws_today" => "Dnes",
"vws_back_to_today" => "Zpět na současný měsíc",
"vws_back_to_main_cal" => "Back to the main calendar month",
"vws_week" => "týden",
"vws_wk" => "T",
"vws_time" => "čas",
"vws_events" => "Události",
"vws_all_day" => "Celý den",
"vws_earlier" => "Dříve",
"vws_later" => "Později",
"vws_venue" => "Místo",
"vws_address" => "Address",
"vws_events_for_next" => "Nadcházející události pro příštích",
"vws_days" => "dnů",
"vws_added" => "Vloženo",
"vws_edited" => "Upraveno",
"vws_notify" => "Oznámit",
"vws_none_due_in" => "Žádné události pro příštích",
"vws_evt_cats" => "Event categories",
"vws_cal_users" => "Calendar users",
"vws_no_users" => "No users in selected group(s)",
"vws_start" => "Start",
"vws_duration" => "Duration",
"vws_no_events_in_gc" => "No events in the selected period",
"vws_download" => "Stáhnout",
"vws_download_title" => "Stáhnout textový soubor s těmito událostmi",
"vws_send_mail" => "Send email",

//changes.php
"chg_select_date" => "Zvolte počáteční datum",
"chg_notify" => "Připomenout",
"chg_days" => "dnů",
"chg_added" => "Vloženo",
"chg_edited" => "Upraveno",
"chg_deleted" => "Smazáno",
"chg_changed_on" => "Změněno",
"chg_no_changes" => "Beze změn.",

//search.php
"sch_define_search" => "Podrobnosti hledání",
"sch_search_text" => "Hledat text",
"sch_event_fields" => "Pole události",
"sch_all_fields" => "Všechna pole",
"sch_title" => "Název",
"sch_description" => "Popis",
"sch_venue" => "Místo",
"sch_user_group" => "User group",
"sch_event_cat" => "Kategorie události",
"sch_all_groups" => "All Groups",
"sch_all_cats" => "Všechny kategorie",
"sch_occurring_between" => "Koná se mezi",
"sch_select_start_date" => "Počáteční datum",
"sch_select_end_date" => "Koncové datum",
"sch_search" => "Hledat",
"sch_invalid_search_text" => "Text pro hledání chybí, nebo je moc krátký",
"sch_bad_start_date" => "Chybné počáteční datum",
"sch_bad_end_date" => "Chybné koncové datum",
"sch_no_results" => "Nic nebylo nelzeno",
"sch_new_search" => "Nové hledání",
"sch_calendar" => "Přejít do kalendáře",
"sch_extra_field1" => "Doplňkové pole 1",
"sch_extra_field2" => "Doplňkové pole 2",
"sch_sd_events" => "Single-day events",
"sch_md_events" => "Multi-day events",
"sch_rc_events" => "Recurring events",
"sch_instructions" =>
"<h3>Pokyny pro textové vyhledávání</h3>
<p>V databázi kalendáře můžete vyhledat události odpovídající danému textu.</p>
<br><p><b>Hledat text</b>: budou prohledána vybraná pole (viz dále) všech událostí.
Při vyhledávání nejsou rozlišována malá a velká pismena.</p>
<p>Můžete použít zástupné znaky:</p>
<ul>
<li>Otazník (?) v hledaném textu nahradí jeden znak.
<br>Např.: '?o?a' odpovídá slovům 'voda', 'rosa', 'kosa'.</li>
<li>Znak hvězdičky (*) zastupuje v textu libovolný počet znaků.
<br>Např: 'po*a' vyhledá 'pohádka', 'Pošta', 'polední přestávka'.</li>
</ul>
<br><p><b>Pole události</b>: Vyhledávání textu bude probíhat pouze ve vybraných polích.</p>
<br><p><b>User group</b>: Events in the selected user group will be searched only.</p>
<br><p><b>Kategorie události</b>: Bude se vyhledávat jen v událostech vybraného typu.</p>
<br><p><b>Koná se mezi</b>: Počáteční i koncové datum je nepovinné. In case of a blank 
start / end date, the default number of days to search back and ahead will be $1 days 
and $2 days respectively.</p>
<br><p>To avoid repetitions of the same event, the search results will be split 
in single-day events, multi-day events and recurring events.</p>
<p>Vyhledané události budou zobrazeny v chronologickém pořadí.</p>",

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
"ssb_upco_events" => "Nadcházející události",
"ssb_all_day" => "Celý den",
"ssb_none" => "Žádné události."
);
?>
