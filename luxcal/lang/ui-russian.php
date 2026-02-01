<?php
/*
= LuxCal user interface language file =

Russian translation: iluhis.com Update of Russian translation: 0x3.ru

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "ru";

/* -- Titles on the Header of the Calendar and Date Picker -- */

$months = array("Январь","Февраль","Март","Апрель","Май","Июнь","Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь");
$months_m = array("Янв","Февр","Мар","Апр","Май","Июн","Июл","Авг","Сен","Окт","Ноя","Дек");
$wkDays = array("Воскресенье","Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье");
$wkDays_l = array("Вос","Пон","Вто","Сре","Чет","Пят","Суб","Вос");
$wkDays_m = array("Вс","Пн","Вт","Ср","Чт","Пт","Сб","Вс");
$wkDays_s = array("В","П","В","С","Ч","П","С","В");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Отправить",
"log_in" => "Войти",
"log_out" => "Выйти",
"portrait" => "Portrait",
"landscape" => "Landscape",
"none" => "Нет",
"all_day" => "Весь день",
"back" => "Назад",
"restart" => "Restart",
"by" => "by",
"of" => "of",
"max" => "max.",
"options" => "Опции просмотра",
"done" => "Готово",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "C", //e.g. from 9:30
"until" => "До", //e.g. until 15:30
"to" => "To", //e.g. to 17-02-2020
"birthdays_in" => "Birthdays in",
"open_calendar" => "Открыть календарь ",
"no_way" => "Для этого нужно авторизоваться",

//index.php
"title_log_in" => "Войти",
"title_profile" => "User Profile",
"title_upcoming" => "Ближайшие события",
"title_event" => "Событие",
"title_check_event" => "Проверить событие",
"title_dmarking" => "Day Marking",
"title_search" => "Текстовый поиск",
"title_contact" => "Contact Form",
"title_thumbnails" => "Thumbnail Images",
"title_user_guide" => "Руководство по календарю",
"title_settings" => "Настройка календаря",
"title_edit_cats" => "Редактировать категории",
"title_edit_users" => "Редактировать пользователей",
"title_edit_groups" => "Изменить группы пользователей",
"title_edit_text" => "Text Editor",
"title_manage_db" => "Управляйте базу данных",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Добавить / Изменить / Удалить события",
"title_usr_import" => "User File Import - CSV format",
"title_usr_export" => "User File Export - CSV format",
"title_evt_import" => "Event File Import - CSV format",
"title_ics_import" => "Event File Import - iCal format",
"title_ics_export" => "Event File Export - iCal format",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "User Interface Styling",
"title_bd_calendar" => "Birthday Calendar",

//header.php
"hdr_button_back" => "Вернуться на главную страницу сайта",
"hdr_options_submit" => "Сделайте выбор и нажмите на «Готово»",
"hdr_options_panel" => "Показать панель опций",
"hdr_select_date" => "Перейти к дате",
"hdr_calendar" => "Календарь",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Режим",
"hdr_lang" => "язык",
"hdr_all_cats" => "Все категории",
"hdr_all_groups" => "All Groups",
"hdr_all_users" => "Все пользователи",
"hdr_go_to_view" => "Go to view",
"hdr_view_1" => "Год",
"hdr_view_2" => "Месяц",
"hdr_view_3" => "Рабочий месяц",
"hdr_view_4" => "Неделя",
"hdr_view_5" => "Рабочая неделя",
"hdr_view_6" => "День",
"hdr_view_7" => "Ближайшее",
"hdr_view_8" => "Изменения",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantt Chart",
"hdr_select_admin_functions" => "Выберите функцию управления",
"hdr_admin" => "Управление",
"hdr_settings" => "Настройки",
"hdr_categories" => "Категории",
"hdr_users" => "Пользователи",
"hdr_groups" => "User Groups",
"hdr_text_editor" => "Text Editor",
"hdr_database" => "База данных",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "User Import (CSV file)",
"hdr_export_usr" => "User Export (CSV file)",
"hdr_import_csv" => "Event Import (CSV file)",
"hdr_import_ics" => "Event Import (iCal file)",
"hdr_export_ics" => "Event Export (iCal file)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Styling",
"hdr_back_to_cal" => "Вернуться к просмотру календаря",
"hdr_button_print" => "Печать",
"hdr_print_page" => "Напечатайте эту страницу",
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
"hdr_button_todo" => "Запланированное",
"hdr_todo_list" => "Список запланированных событий",
"hdr_button_upco" => "Ближайшие",
"hdr_upco_list" => "Приближающиеся события",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Поиск",
"hdr_search" => "Поиск",
"hdr_button_add" => "Создать",
"hdr_add_event" => "Добавить событие",
"hdr_button_help" => "Справка",
"hdr_user_guide" => "Руководство",
"hdr_gen_guide" => "General User Guide",
"hdr_cs_guide" => "Context-sensitive User Guide",
"hdr_gen_help" => "General help",
"hdr_prev_help" => "Previous help",
"hdr_open_menu" => "Open Menu",
"hdr_side_menu" => "Side Menu",
"hdr_dest_cals" => "Destination Calendar(s)",
"hdr_copy_evt" => "Copy Event",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "сегодня", //dtpicker.js
"hdr_clear" => "стереть", //dtpicker.js

//event.php
"evt_no_title" => "Без имени",
"evt_no_start_date" => "Нет даты начала",
"evt_bad_date" => "Неправильная дата",
"evt_bad_rdate" => "Неверный повтор конечной даты",
"evt_no_start_time" => "Нет времени начала",
"evt_bad_time" => "Неправильное время",
"evt_end_before_start_time" => "Время окончания предшествует времени начала",
"evt_end_before_start_date" => "Дата окончания предшествует дате начала",
"evt_until_before_start_date" => "Повторите дату окончания перед датой начала",
"evt_default_duration" => "Default event duration of $1 hours and $2 minutes",
"evt_fixed_duration" => "Fixed event duration of $1 hours and $2 minutes",
"evt_approved" => "Event approved",
"evt_apd_locked" => "Event approved and locked",
"evt_title" => "Заголовок",
"evt_venue" => "Место проведения",
"evt_address_button" => "An address between ! marks will become a button",
"evt_list" => "List",
"evt_category" => "Категория",
"evt_subcategory" => "Subcategory",
"evt_description" => "Описание",
"evt_attachments" => "Attachments",
"evt_attach_file" => "Attach file",
"evt_click_to_open" => "Click to open",
"evt_click_to_remove" => "Click to remove",
"evt_no_pdf_img_vid" => "Attachment should be pdf, image or video",
"evt_error_file_upload" => "Error uploading file",
"evt_upload_too_large" => "Uploaded file too large",
"evt_date_time" => "Дата / время",
"evt_date" => "Дата",
"evt_private" => "Частное событие",
"evt_start_date" => "Начало",
"evt_end_date" => "Конец",
"evt_select_date" => "Выберите дату",
"evt_select_time" => "Выберите time",
"evt_all_day" => "Весь день",
"evt_no_time" => "No Time",
"evt_change" => "Изменить",
"evt_set_repeat" => "Задать повтор",
"evt_set" => "OK",
"evt_help" => "help",
"evt_repeat_not_supported" => "Заданное повторение не поддерживается",
"evt_no_repeat" => "Без повтора",
"evt_rolling" => "Rolling",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Повторять каждый",
"evt_until" => "до",
"evt_blank_no_end" => "если бесконечно, то оставьте пустым",
"evt_each_month" => "каждый месяц",
"evt_interval2_1" => "первый",
"evt_interval2_2" => "второй",
"evt_interval2_3" => "третий",
"evt_interval2_4" => "четвертый",
"evt_interval2_5" => "последний",
"evt_period1_1" => "день",
"evt_period1_2" => "неделя",
"evt_period1_3" => "месяц",
"evt_period1_4" => "год",
"evt_notification" => "Уведомление",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "сейчас и/или",
"evt_event_added" => "Указанное ниже событие добавлено",
"evt_event_edited" => "Указанное ниже событие изменено",
"evt_event_deleted" => "Указанное ниже событие удалено",
"evt_event_approved" => "Approved event",
"evt_days_before_event" => "день(дней) до начала",
"evt_to" => "Cобытия",
"evt_not_help" => "List of recipients separated by semicolons. A recipient can be a user name, an email address, a mobile phone number, a Telegram chat ID or, enclosed in square brackets, the name (without type) of a .txt file with recipients in the 'reciplists' folder. This file should contain one recipient (a user name, an email address, a mobile phone number or a Telegram chat ID) per line.<br>Maximum field length: 255 characters.",
"evt_recip_list_too_long" => "Список адресов слишком длинный.",
"evt_no_recip_list" => "Отсутствует уведомление на адрес(а)",
"evt_not_in_past" => "Дата оповещения уже прошла",
"evt_not_days_invalid" => "Неверное количество дней оповещения",
"evt_status" => "Статус",
"evt_descr_help" => "The following items can be used in the description fields ...<br>• HTML tags &lt;b&gt;, &lt;i&gt;, &lt;u&gt; and &lt;s&gt; for bold, italic, underlined and striked-through text.",
"evt_descr_help_img" => "• small images (thumbnails) in the format: 'image_name.ext'. The thumbnail files, with file extension .gif, .jpg or .png, must be present in 'thumbnails' folder. If enabled, the Thumbnails page can be used to upload thumbnail files.",
"evt_descr_help_eml" => "• Mailto-links in the format: 'email address' or 'email address [name]', where 'name' will be the title of the hyperlink. E.g. xxx@yyyy.zzz [For info click here].",
"evt_descr_help_url" => "• URL links in the format: 'url' or 'url [name]', where 'name' will be the title of the link. If 'S:' is placed in front of the URL, the link will open in the same page/tab, otherwise the link will open in a blank page/tab. E.g. S:https://www.google.com [search].",
"evt_confirm_added" => "Событие добавлено",
"evt_confirm_saved" => "Событие сохранено",
"evt_confirm_deleted" => "Событие удалено",
"evt_add_close" => "Добавить и закрыть",
"evt_add" => "Добавить",
"evt_edit" => "Редактировать",
"evt_save_close" => "Сохранить и закрыть",
"evt_save" => "Сохранить",
"evt_clone" => "Сохранить как новую",
"evt_delete" => "Удалить",
"evt_close" => "Закрыть",
"evt_added" => "Добавлено",
"evt_edited" => "Редактирует",
"evt_is_repeating" => "повторяющееся событие.",
"evt_is_multiday" => "многодневное событие.",
"evt_edit_series_or_occurrence" => "Хотите редактировать всю серию или одно событие?",
"evt_edit_series" => "Редактировать серию",
"evt_edit_occurrence" => "Редактировать одно",
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
"vws_add_event" => "Добавить событие",
"vws_edit_event" => "Edit Event",
"vws_see_event" => "See event details",
"vws_view_month" => "Обзор месяца",
"vws_view_week" => "Обзор недели",
"vws_view_day" => "Обзор дня",
"vws_click_for_full" => "Щелкните на месяц для большого календаря",
"vws_view_full" => "Смотреть большой календарь",
"vws_prev_year" => "Предыдущий год",
"vws_next_year" => "Следующий год",
"vws_prev_month" => "Предыдущий месяц",
"vws_next_month" => "Следующий месяц",
"vws_forward" => "Forward",
"vws_backward" => "Backward",
"vws_mark_day" => "Mark day",
"vws_today" => "Cегодня",
"vws_back_to_today" => "Перейти к сегодня",
"vws_back_to_main_cal" => "Back to the main calendar month",
"vws_week" => "нед.",
"vws_wk" => "нд",
"vws_time" => "Время",
"vws_events" => "События",
"vws_all_day" => "Весь день",
"vws_earlier" => "Ранее",
"vws_later" => "Позднее",
"vws_venue" => "Место проведения",
"vws_address" => "Address",
"vws_events_for_next" => "Предстоящие к следующему события",
"vws_days" => "день(дней)",
"vws_added" => "Добавлено",
"vws_edited" => "Отредактировано",
"vws_notify" => "Уведомление",
"vws_none_due_in" => "No events due in the next",
"vws_evt_cats" => "Event categories",
"vws_cal_users" => "Calendar users",
"vws_no_users" => "No users in selected group(s)",
"vws_start" => "Start",
"vws_duration" => "Duration",
"vws_no_events_in_gc" => "No events in the selected period",
"vws_download" => "Скачать",
"vws_download_title" => "Скачать файл с этими событиями",
"vws_send_mail" => "Send email",

//changes.php
"chg_select_date" => "Выберите дату начала",
"chg_notify" => "Уведомление",
"chg_days" => "День(дней)",
"chg_added" => "Добавлено",
"chg_edited" => "Отредактировано",
"chg_deleted" => "Удалено",
"chg_changed_on" => "Изменено",
"chg_no_changes" => "Нет изменений",

//search.php
"sch_define_search" => "Настройки поиска",
"sch_search_text" => "Искать текст",
"sch_event_fields" => "Поля событий",
"sch_all_fields" => "Все поля",
"sch_title" => "Заголовок",
"sch_description" => "Описание",
"sch_venue" => "Место проведения",
"sch_user_group" => "User group",
"sch_event_cat" => "Категория",
"sch_all_groups" => "All Groups",
"sch_all_cats" => "Все категории",
"sch_occurring_between" => "Искать между числами",
"sch_select_start_date" => "Выбрать начальную дату",
"sch_select_end_date" => "Выбрать конечную дату",
"sch_search" => "Поиск",
"sch_invalid_search_text" => "Текст поиска слишком короткий",
"sch_bad_start_date" => "Неверная начальная дата",
"sch_bad_end_date" => "Неверная конечная дата",
"sch_no_results" => "Ничего не найдено",
"sch_new_search" => "Новый поиск",
"sch_calendar" => "Перейти в календарь",
"sch_extra_field1" => "Дополнительное поле 1",
"sch_extra_field2" => "Дополнительное поле 2",
"sch_sd_events" => "Single-day events",
"sch_md_events" => "Multi-day events",
"sch_rc_events" => "Recurring events",
"sch_instructions" =>
"<h3>Инструкции при поиске текста</h3>
<p>В базе данных календаря может быть произведен поиск заданного текста.</p>
<br><p><b>Искать текст</b>: Будет произведен поиск по выделенным полям (см. ниже).
Поиск не чувствителен к регистру.</p>
<p>Могут быть испоьзованы два символа-шаблона (маски):</p>
<ul>
<li>Вопросительный знак (?) в поиске текста будет заменять любой один символ.
<br>Т.е.: '?и?о' означает 'пиво','шило','кило'.</li>
<li>Символ звездочки (*) в поиске будет заменять любое количество символов.
<br>Т.е.: 'бу*а' означает 'бутылка', 'бура', 'буженина'.</li>
</ul>
<br><p><b>Поля событий</b>: Будет произведен поиск только по указанным полям.</p>
<br><p><b>User group</b>: Events in the selected user group will be searched only.</p>
<br><p><b>Категории событий</b>: Будет произведен поиск только в указанных категориях.</p>
<br><p><b>Искать между числами</b>: Даты начала и окончания являются необязательными. 
In case of a blank start / end date, the default number of days to search back and 
ahead will be $1 days and $2 days respectively.</p>
<br><p>To avoid repetitions of the same event, the search results will be split 
in single-day events, multi-day events and recurring events.</p>
<p>Результаты поиска будут выведены в хронологическом порядке.</p>",

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
"ssb_upco_events" => "Ближайшие",
"ssb_all_day" => "Весь день",
"ssb_none" => "Нет событий."
);
?>
