<?php
/*
= LuxCal user interface language file =

This file has been translated by Chayote. Please send commentsto rb@luxsoft.eu.

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "vi";

/* -- Titles on the Header of the Calendar and Date Picker -- */

$months = array("Tháng 1","Tháng 2","Tháng 3","Tháng 4","Tháng 5","Tháng 6","Tháng 7","Tháng 8","Tháng 9","Tháng 10","Tháng 11","Tháng 12");
$months_m = array("Thg1","Thg2","Thg3","Thg4","Thg5","Thg6","Thg7","Thg8","Thg9","Thg10","Thg11","Thg12");
$wkDays = array("Chủ nhật","Thứ 2","Thứ 3","Thứ 4","Thứ 5","Thứ 6","Thứ 7","Chủ nhật");
$wkDays_l = array("CN","T2","T3","T4","T5","T6","T7","CN");
$wkDays_m = array("CN","T2","T3","T4","T5","T6","T7","CN");
$wkDays_s = array("CN","2","3","4","5","6","7","CN");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Submit",
"log_in" => "Đăng nhập",
"log_out" => "Thoát",
"portrait" => "Portrait",
"landscape" => "Landscape",
"none" => "None.",
"all_day" => "All day",
"back" => "Trở lại",
"restart" => "Restart",
"by" => "bởi",
"of" => "của",
"max" => "max.",
"options" => "Lựa chọn",
"done" => "Ok",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "From", //e.g. from 9:30
"until" => "Until", //e.g. until 15:30
"to" => "To", //e.g. to 17-02-2020
"birthdays_in" => "Birthdays in",
"open_calendar" => "Mở lịch",
"no_way" => "You are not authorized to perform this action",

//index.php
"title_log_in" => "Log In",
"title_profile" => "User Profile",
"title_upcoming" => "Sự kiện sắp tới",
"title_event" => "Lịch hẹn",
"title_check_event" => "Kiểm tra lịch hẹn",
"title_dmarking" => "Day Marking",
"title_search" => "Tìm kiếm",
"title_contact" => "Contact Form",
"title_thumbnails" => "Thumbnail Images",
"title_user_guide" => "Hướng dẫn",
"title_settings" => "Quản lý cài đặt",
"title_edit_cats" => "Sửa menu",
"title_edit_users" => "Sửa users",
"title_edit_groups" => "Edit User Groups",
"title_edit_text" => "Text Editor",
"title_manage_db" => "Quản lý dữ liệu",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Added / Edited / Deleted Events",
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
"hdr_options_submit" => "Bạn hãy lựa chọn và bấm vào 'Ok'",
"hdr_options_panel" => "Bảng lựa chọn",
"hdr_select_date" => "Chọn ngày",
"hdr_calendar" => "Calendar",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Xem",
"hdr_lang" => "Ngôn ngữ",
"hdr_all_cats" => "Tất cả danh sách",
"hdr_all_groups" => "All Groups",
"hdr_all_users" => "Tất cả user",
"hdr_go_to_view" => "Go to view",
"hdr_view_1" => "Năm",
"hdr_view_2" => "Đủ tháng",
"hdr_view_3" => "Tháng làm việc",
"hdr_view_4" => "Đủ tuần",
"hdr_view_5" => "Tuần làm việc",
"hdr_view_6" => "Ngày",
"hdr_view_7" => "Sắp diễn ra",
"hdr_view_8" => "Thay đổi",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantt Chart",
"hdr_select_admin_functions" => "Select Admin Function",
"hdr_admin" => "Administration",
"hdr_settings" => "Cài đặt",
"hdr_categories" => "Tất cả danh mục",
"hdr_users" => "Người dùng",
"hdr_groups" => "User Groups",
"hdr_text_editor" => "Text Editor",
"hdr_database" => "Dữ liệu",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "User Import (CSV file)",
"hdr_export_usr" => "User Export (CSV file)",
"hdr_import_csv" => "Event Import (CSV file)",
"hdr_import_ics" => "Event Import (iCal file)",
"hdr_export_ics" => "Event Export (iCal file)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Styling",
"hdr_back_to_cal" => "Back to calendar view",
"hdr_button_print" => "In",
"hdr_print_page" => "In trang",
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
"hdr_todo_list" => "Công việc cần làm",
"hdr_button_upco" => "Upcoming",
"hdr_upco_list" => "Lịch hẹn sắp tới",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Search",
"hdr_search" => "Tìm kiếm",
"hdr_button_add" => "Add",
"hdr_add_event" => "Thêm lịch hẹn",
"hdr_button_help" => "Giúp đỡ",
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
"hdr_today" => "Hôm nay", //dtpicker.js
"hdr_clear" => "clear", //dtpicker.js

//event.php
"evt_no_title" => "Không tiêu đề",
"evt_no_start_date" => "Không ngày bắt đầu",
"evt_bad_date" => "Ngày xấu",
"evt_bad_rdate" => "Lặp lại ngày xấu",
"evt_no_start_time" => "Không thời gian bắt đầu",
"evt_bad_time" => "Thời gian xấu",
"evt_end_before_start_time" => "Thời gian kết thúc trước thời gian bắt đầu",
"evt_end_before_start_date" => "Ngày kết thúc trước ngày bắt đầu",
"evt_until_before_start_date" => "Lặp lại ngày cuối trước ngày bắt đầu",
"evt_default_duration" => "Default event duration of $1 hours and $2 minutes",
"evt_fixed_duration" => "Fixed event duration of $1 hours and $2 minutes",
"evt_approved" => "Event approved",
"evt_apd_locked" => "Event approved and locked",
"evt_title" => "Tiêu đề",
"evt_venue" => "Nơi hẹn",
"evt_address_button" => "An address between ! marks will become a button",
"evt_list" => "List",
"evt_category" => "Danh mục",
"evt_subcategory" => "Subcategory",
"evt_description" => "Mô tả",
"evt_attachments" => "Attachments",
"evt_attach_file" => "Attach file",
"evt_click_to_open" => "Click to open",
"evt_click_to_remove" => "Click to remove",
"evt_no_pdf_img_vid" => "Attachment should be pdf, image or video",
"evt_error_file_upload" => "Error uploading file",
"evt_upload_too_large" => "Uploaded file too large",
"evt_date_time" => "Ngày / Thời gian",
"evt_date" => "Ngày",
"evt_private" => "Lịch hẹn cá nhân",
"evt_start_date" => "Bắt đầu",
"evt_end_date" => "Kết thúc",
"evt_select_date" => "Chọn ngày",
"evt_select_time" => "Chọn thời gian",
"evt_all_day" => "Cả ngày",
"evt_no_time" => "No Time",
"evt_change" => "Thay đổi",
"evt_set_repeat" => "Lặp lại",
"evt_set" => "OK",
"evt_help" => "help",
"evt_repeat_not_supported" => "Không hỗ trợ lặp lại",
"evt_no_repeat" => "Không lặp lại",
"evt_rolling" => "Rolling",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Lặp lại mỗi ngày",
"evt_until" => "Đến khi",
"evt_blank_no_end" => "Trống: không kết thúc",
"evt_each_month" => "Mỗi tháng",
"evt_interval2_1" => "Đầu tiên",
"evt_interval2_2" => "Lần hai",
"evt_interval2_3" => "Lần ba",
"evt_interval2_4" => "Lần bốn",
"evt_interval2_5" => "Lần cuối",
"evt_period1_1" => "Ngày",
"evt_period1_2" => "Tuần",
"evt_period1_3" => "Tháng",
"evt_period1_4" => "Năm",
"evt_notification" => "Thông báo",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "ngay và/hoặc",
"evt_event_added" => "Lịch hẹn mới",
"evt_event_edited" => "Đổi lịch hẹn",
"evt_event_deleted" => "Xoá lịch hẹn",
"evt_event_approved" => "Approved event",
"evt_days_before_event" => "Ngày(s) trước lịch",
"evt_to" => "Hen",
"evt_not_help" => "List of recipients separated by semicolons. A recipient can be a user name, an email address, a mobile phone number, a Telegram chat ID or, enclosed in square brackets, the name (without type) of a .txt file with recipients in the 'reciplists' folder. This file should contain one recipient (a user name, an email address, a mobile phone number or a Telegram chat ID) per line.<br>Maximum field length: 255 characters.",
"evt_recip_list_too_long" => "Địa chỉ quá nhiều ký tự.",
"evt_no_recip_list" => "nhắc lịch(es) lỗi",
"evt_not_in_past" => "Ngày nhắc lịch trong quá khứ",
"evt_not_days_invalid" => "Ngày nhắc lịch không đúng",
"evt_status" => "Tình trạng",
"evt_descr_help" => "The following items can be used in the description fields ...<br>• HTML tags &lt;b&gt;, &lt;i&gt;, &lt;u&gt; and &lt;s&gt; for bold, italic, underlined and striked-through text.",
"evt_descr_help_img" => "• small images (thumbnails) in the format: 'image_name.ext'. The thumbnail files, with file extension .gif, .jpg or .png, must be present in 'thumbnails' folder. If enabled, the Thumbnails page can be used to upload thumbnail files.",
"evt_descr_help_eml" => "• Mailto-links in the format: 'email address' or 'email address [name]', where 'name' will be the title of the hyperlink. E.g. xxx@yyyy.zzz [For info click here].",
"evt_descr_help_url" => "• URL links in the format: 'url' or 'url [name]', where 'name' will be the title of the link. If 'S:' is placed in front of the URL, the link will open in the same page/tab, otherwise the link will open in a blank page/tab. E.g. S:https://www.google.com [search].",
"evt_confirm_added" => "Liệc hẹn đã được đặt",
"evt_confirm_saved" => "Lịch hẹn đã được lưu",
"evt_confirm_deleted" => "Lịch hẹn đã được xoá",
"evt_add_close" => "Thêm và đóng",
"evt_add" => "Thêm",
"evt_edit" => "Sửa",
"evt_save_close" => "Lưu và đóng",
"evt_save" => "Lưu",
"evt_clone" => "Lưu lịch hẹn mới",
"evt_delete" => "Xoá",
"evt_close" => "Đóng",
"evt_added" => "Đã thêm",
"evt_edited" => "Đã sửa",
"evt_is_repeating" => "Đang lặp lại lịch hẹn.",
"evt_is_multiday" => "Lịch hẹn nhiều ngày.",
"evt_edit_series_or_occurrence" => "Bạn có muốn sửa hàng loạt hoặc chỉ sự kiện ngày không?",
"evt_edit_series" => "Sửa hàng loạt",
"evt_edit_occurrence" => "Sửa sự kiện ngày",
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
"vws_add_event" => "Thêm lịch hẹn",
"vws_edit_event" => "Edit Event",
"vws_see_event" => "See event details",
"vws_view_month" => "Xem tháng",
"vws_view_week" => "Xem tuần",
"vws_view_day" => "Xem ngày",
"vws_click_for_full" => "for full calendar click month",
"vws_view_full" => "View full calendar",
"vws_prev_year" => "Năm trước",
"vws_next_year" => "Năm tiếp",
"vws_prev_month" => "Tháng trước",
"vws_next_month" => "Tháng tiếp",
"vws_forward" => "Forward",
"vws_backward" => "Backward",
"vws_mark_day" => "Mark day",
"vws_today" => "Hôm nay",
"vws_back_to_today" => "Trở lại tháng ngày hôm nay",
"vws_back_to_main_cal" => "Back to the main calendar month",
"vws_week" => "Tuần",
"vws_wk" => "wk",
"vws_time" => "Thời gian",
"vws_events" => "Các lịch hẹn",
"vws_all_day" => "Cả ngày",
"vws_earlier" => "Sớm hơn",
"vws_later" => "Muộn hơn",
"vws_venue" => "Nơi hẹn",
"vws_address" => "Address",
"vws_events_for_next" => "Upcoming events for the next",
"vws_days" => "Ngày(s)",
"vws_added" => "Đã thêm",
"vws_edited" => "Đã sửa",
"vws_notify" => "Thông báo",
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
"chg_select_date" => "Chọn ngày bắt đầu",
"chg_notify" => "Thông báo",
"chg_days" => "Ngày(s)",
"chg_added" => "Đã thêm",
"chg_edited" => "Đã sửa",
"chg_deleted" => "Đã xoá",
"chg_changed_on" => "Thay đổi",
"chg_no_changes" => "Không thay đổi.",

//search.php
"sch_define_search" => "Define Search",
"sch_search_text" => "Tìm kiếm",
"sch_event_fields" => "Trường lịch hẹn",
"sch_all_fields" => "Các trường",
"sch_title" => "Tiêu đề",
"sch_description" => "Mô tả",
"sch_venue" => "Nơi hẹn",
"sch_user_group" => "User group",
"sch_event_cat" => "Danh mục lịch hẹn",
"sch_all_groups" => "All Groups",
"sch_all_cats" => "Tất cả danh mục",
"sch_occurring_between" => "Đang diễn ra giữa",
"sch_select_start_date" => "Chọn ngày bắt đầu",
"sch_select_end_date" => "Chọn ngày kết thúc",
"sch_search" => "Tìm kiếm",
"sch_invalid_search_text" => "Search text missing or too short",
"sch_bad_start_date" => "Bad start date",
"sch_bad_end_date" => "Bad end date",
"sch_no_results" => "Không có kết quả",
"sch_new_search" => "Tìm kiếm mới",
"sch_calendar" => "Đi tới lịch hẹn",
"sch_extra_field1" => "Extra field 1",
"sch_extra_field2" => "Extra field 2",
"sch_sd_events" => "Single-day events",
"sch_md_events" => "Multi-day events",
"sch_rc_events" => "Recurring events",
"sch_instructions" =>
"<h3>Text Search Instructions</h3>
<p>The calendar database can be searched for events matching specific text.</p>
<br><p><b>Search text</b>: The selected fields (see below) of each event will 
be searched. The search is not case sensitive.</p>
<p>Two wildcard characters can be used:</p>
<ul>
<li>A question mark (?) in the search text will match any single character.<br>E.g.: '?e?r' matches 'beer', 'dear', 'heir'.</li>
<li>An asterisk character (*) in the search text will match any number of characters.<br>E.g.: 'de*r' matches 'December', 'dear', 'developer'.</li>
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
