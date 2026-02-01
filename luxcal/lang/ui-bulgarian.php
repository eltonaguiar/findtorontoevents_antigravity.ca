<?php
/*
= LuxCal езиков файл за потребителския интерфейс =

Български потребителски интерфей

Този файл е създаден от LuxSoft и е преведен от Йордан Павлов.

Този файл е част от уеб календара на LuxCal.
*/

//LuxCal ui language
$isocode = "bg";

/* -- Titles on the Header of the Calendar and Date Picker -- */

$months = array("Януари","Февруари","Март","Април","Май","Юни","Юли","Август","Септември","Октомври","Ноември","Декември");
$months_m = array("Яну","Фев","Мар","Апр","Май","Юни","Юли","Авг","Сеп","Окт","Ное","Дек");
$wkDays = array("Неделя","Понеделник","Вторник","Сряда","Четвъртък","Петък","Събота","Неделя");
$wkDays_l = array("Нед","Пон","Вто","Сря","Чет","Пет","Съб","Нед");
$wkDays_m = array("Нд","Пн","Вт","Ср","Чт","Пт","Сб","Нд");
$wkDays_s = array("Н","П","В","С","Ч","П","С","Н");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Потвърди",
"log_in" => "ВХОД",
"log_out" => "ИЗХОД",
"portrait" => "Портрет",
"landscape" => "Пейзаж",
"none" => "Няма",
"all_day" => "Цял ден",
"back" => "Назад",
"restart" => "Рестарт",
"by" => "от",
"of" => "от",
"max" => "макс.",
"options" => "Филтри",
"done" => "Готово",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "от", //e.g. from 9:30
"until" => "до", //e.g. until 15:30
"to" => "до", //e.g. to 17-02-2020
"birthdays_in" => "Рождени дни в",
"open_calendar" => "Отвори календар",
"no_way" => "Нямате нужните права,за да извършите желаните от вас действия",

//index.php
"title_log_in" => "Влез",
"title_profile" => "Моят профил",
"title_upcoming" => "Предстоящи задачи",
"title_event" => "Задача",
"title_check_event" => "Провери задача",
"title_dmarking" => "Маркиране на ден",
"title_search" => "Tърсене",
"title_contact" => "Форма за контакт",
"title_thumbnails" => "Миниатюри",
"title_user_guide" => "Ръководство",
"title_settings" => "Редактиране на настройките",
"title_edit_cats" => "Промени категория",
"title_edit_users" => "Промени потребители",
"title_edit_groups" => "Редакция на Групи",
"title_edit_text" => "Редактиране на информационния текст",
"title_manage_db" => "База данни",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Промени на задачи",
"title_usr_import" => "Потребители от CSV",
"title_usr_export" => "Потребители в CSV",
"title_evt_import" => "Задачи от CSV",
"title_ics_import" => "Задачи от iCal",
"title_ics_export" => "Задачи в iCal",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "Настройки на интерфейса",
"title_bd_calendar" => "Рожденици",

//header.php
"hdr_button_back" => "Върни се системата",
"hdr_options_submit" => "Направете своят избор и натиснете 'Готово'",
"hdr_options_panel" => "Панел с филтри",
"hdr_select_date" => "Отиди на дата",
"hdr_calendar" => "Календар",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Изглед",
"hdr_lang" => "Език",
"hdr_all_cats" => "Всички категории",
"hdr_all_groups" => "Всички групи",
"hdr_all_users" => "Всички потребители",
"hdr_go_to_view" => "Отвори изглед",
"hdr_view_1" => "Година",
"hdr_view_2" => "Месец",
"hdr_view_3" => "Работен месец",
"hdr_view_4" => "Седмица",
"hdr_view_5" => "Работна седмица",
"hdr_view_6" => "Ден",
"hdr_view_7" => "Предстоящи задачи",
"hdr_view_8" => "Промени",
"hdr_view_9" => "Матричен(К)",
"hdr_view_10" => "Матричен(П)",
"hdr_view_11" => "Диаграма",
"hdr_select_admin_functions" => "Изберете административни функции",
"hdr_admin" => "Мениджър",
"hdr_settings" => "Настройки",
"hdr_categories" => "Категории",
"hdr_users" => "Потребители",
"hdr_groups" => "Групи",
"hdr_text_editor" => "текстов редактор",
"hdr_database" => "База данни",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "Потребители от CSV",
"hdr_export_usr" => "Потребители в CSV",
"hdr_import_csv" => "Задачи от CSV",
"hdr_import_ics" => "Задачи от iCal",
"hdr_export_ics" => "Задачи в iCal",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Стилизиране",
"hdr_back_to_cal" => "Обратно към изглед Календар",
"hdr_button_print" => "Печат",
"hdr_print_page" => "Разпечатай този изглед",
"hdr_button_pdf" => "PDF - Задачи",
"hdr_button_pdf_bc" => "PDF - Рождени дни",
"hdr_dload_pdf" => "Изтегли предстоящите задачи в PDF файл",
"hdr_dload_pdf_bc" => "Изтегли рождените дни в PDF файл", // add by Yordan Pavlov
"hdr_button_contact" => "Контакт",
"hdr_contact" => "Контакт с администратора",
"hdr_button_tnails" => "Миниатюри",
"hdr_tnails" => "Управление на миниатюри",
"hdr_button_toap" => "За одобрение",
"hdr_toap_list" => "Задачи за одобрение",
"hdr_button_todo" => "За изпълнение",
"hdr_todo_list" => "Задачи за изпълнение",
"hdr_button_upco" => "Предстоящи",
"hdr_upco_list" => "Предстоящи задачи",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Търси",
"hdr_search" => "Търсене",
"hdr_button_add" => "ДОБАВИ ЗАДАЧА",
"hdr_add_event" => "Добавяне на нова задача",
"hdr_button_help" => "Помощ",
"hdr_user_guide" => "Ръководство",
"hdr_gen_guide" => "Общо ръководство",
"hdr_cs_guide" => "Контекстно ръкововдство",
"hdr_gen_help" => "Обща помощ",
"hdr_prev_help" => "Предходна страница",
"hdr_open_menu" => "Отвори страничното меню",
"hdr_side_menu" => "Странично меню",
"hdr_dest_cals" => "Destination Calendar(s)",
"hdr_copy_evt" => "Copy Event",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "Днес", //dtpicker.js
"hdr_clear" => "Изчисти", //dtpicker.js

//event.php
"evt_no_title" => "Без заглавие",
"evt_no_start_date" => "Без начална дата",
"evt_bad_date" => "Неправилен формат на датата",
"evt_bad_rdate" => "Неправилно повторение на крайната дата",
"evt_no_start_time" => "Без начално време",
"evt_bad_time" => "Неправилен формат на времето",
"evt_end_before_start_time" => "Крайното време е преди началното",
"evt_end_before_start_date" => "Крайната дата е преди началната",
"evt_until_before_start_date" => "Повторащ край преди началната дата",
"evt_default_duration" => "Обикновено продължителността е $1 часа и $2 минути",
"evt_fixed_duration" => "Фиксирана продължителност от $1 часа $2 минути",
"evt_approved" => "Одобрена задача",
"evt_apd_locked" => "Одобрена и заключена задача",
"evt_title" => "Заглавие",
"evt_venue" => "Място",
"evt_address_button" => "Адрес, обграден с ! (удивителна) ще се показва като бутон",
"evt_list" => "List",
"evt_category" => "Категория",
"evt_subcategory" => "Подкатегория",
"evt_description" => "Описание",
"evt_attachments" => "Прикачени",
"evt_attach_file" => "Приложи файл",
"evt_click_to_open" => "Щракни за отваряне",
"evt_click_to_remove" => "Щракни за премахване",
"evt_no_pdf_img_vid" => "Може да прикачате pdf и снимки",
"evt_error_file_upload" => "Грешка при прикачане на файл",
"evt_upload_too_large" => "Файла е прекалено голям",
"evt_date_time" => "Дата / Час",
"evt_date" => "Дата",
"evt_private" => "Лична задача",
"evt_start_date" => "Начало",
"evt_end_date" => "Край",
"evt_select_date" => "Изберете дата",
"evt_select_time" => "Изберете час",
"evt_all_day" => "Целодневно",
"evt_no_time" => "No Time",
"evt_change" => "Промяна",
"evt_set_repeat" => "Задайте повторение",
"evt_set" => "OK",
"evt_help" => "Помощ",
"evt_repeat_not_supported" => "Указаното повторение не се поддържа",
"evt_no_repeat" => "Без повторение",
"evt_rolling" => "Прескачаща",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Всеки",
"evt_until" => "до дата",
"evt_blank_no_end" => "Ако е празно: безкрайно",
"evt_each_month" => "Всеки месец",
"evt_interval2_1" => "Първи",
"evt_interval2_2" => "Втори",
"evt_interval2_3" => "Трети",
"evt_interval2_4" => "Четвърти",
"evt_interval2_5" => "Пети",
"evt_period1_1" => "дни",
"evt_period1_2" => "Седмици",
"evt_period1_3" => "Месеца",
"evt_period1_4" => "Години",
"evt_notification" => "Известие",
"evt_send_sms" => "SMS",
"evt_now_and_or" => " при настъпване и/или ",
"evt_event_added" => "Нова задача",
"evt_event_edited" => "Променете задача",
"evt_event_deleted" => "Изтриване на задача",
"evt_event_approved" => "Потвърдена задача",
"evt_days_before_event" => " дни преди настъпване",
"evt_to" => "На",
"evt_not_help" => "Списък на получателите, разделени с точка и запетая. Адресът на получателя може да бъде потребителско име, имейл адрес, номер, мобилен телефон на Telegram chat ID или, enclosed in square brackets, the name (without type) of a .txt file with recipients in the 'reciplists' folder., с един адрес (потребителско име, имейл адрес или номер, мобилен телефон на Telegram chat ID) на ред.<br> Максимална дължина на полето: 255 знака.",
"evt_recip_list_too_long" => "Прекалено много символи в електронната поща.",
"evt_no_recip_list" => "Има грешка в напомнянето за електронна поща.",
"evt_not_in_past" => "Датата за напомняне е в миналото",
"evt_not_days_invalid" => "Дните за напомняне са невалидни",
"evt_status" => "Статус",
"evt_descr_help" => "Следните елементи могат да се използват в полетата за описание :<br>• HTML тагове &lt;b&gt;, &lt;i&gt;, &lt;u&gt; и &lt;s&gt; за удебелен, наклонен, подчертан и зачеркани текстове.",
"evt_descr_help_img" => "• малки снимки (миниатюри) в  формат: 'image_name.ext'. Миниатюри с разширения на файла .gif, .jpg или .png, трябва да се намират в папка 'thumbnails' . Ако е позволено, страницата за Миниатюри може да се изпозлва за качване на файлове.",
"evt_descr_help_eml" => "• Е-mail връзки в  формати: 'email адрес' или 'email адрес [Заглавие]', където 'Заглавие' ще бъде заглавието на връзката. Например: xxx@yyyy.zzz [Изпрати писмо от тук].",
"evt_descr_help_url" => "• URL връзки в  формат: 'url' или 'url [Заглавие]', където 'Заглавие' ще бъде заглавието на връзката. Ако поставите 'S:' пред URL адреса, връзката ще се отвори в същия прозорец/раздел, в противен случай връзката ще се отвори в нов прозорец/раздел. Например: S:https://www.google.com [Търсене в Google].",
"evt_confirm_added" => "Добавени задачи",
"evt_confirm_saved" => "Запазени задачи",
"evt_confirm_deleted" => "Изтрити задачи",
"evt_add_close" => "Добави и затвори",
"evt_add" => "Добави",
"evt_edit" => "Редактирай",
"evt_save_close" => "Запиши и затвори",
"evt_save" => "Записване",
"evt_clone" => "Направи дубликат",
"evt_delete" => "ИЗТРИЙ",
"evt_close" => "Затвори",
"evt_added" => "Добавена",
"evt_edited" => "Променена",
"evt_is_repeating" => "Задачата е повтаряема.",
"evt_is_multiday" => "Задачата продължава няколко дни.",
"evt_edit_series_or_occurrence" => "Изберете да редактирате цялата серията или само тази задача от серията?",
"evt_edit_series" => "Редактиране на серия задачи",
"evt_edit_occurrence" => "Редактиране на отделна задача",
"evt_select_from_list" => "Select recipients from list",
"evt_select_recips" => "Select Recipients",
"evt_recip_lists" => "Lists with Recipients",
"evt_regist_recips" => "Registered Recipients",
"evt_public_recips" => "Public Recipients",

//events - dmark specific
"mrk_text_and_color" => "Текст и цвят",
"mrk_is_repeating" => "Маркировката е повторяема",
"mrk_is_multiday" => "Маркировката е многодневна",
"mrk_text" => "Текст",
"mrk_color" => "Цвят",
"mrk_select_color" => "Избери Цвят",
"mrk_background" => "Фон",
"mrk_start_date" => "Начална дата",
"mrk_end_date" => "Крайна дата",
"mrk_dmark_added" => "Нова дневна маркировка",
"mrk_dmark_edited" => "Променена дневна маркировка",
"mrk_dmark_deleted" => "Изтрита дневна маркировка",
"mrk_dates" => "Дати",

//views
"vws_add_event" => "Добави задача",
"vws_edit_event" => "Редактирай задача",
"vws_see_event" => "Виж детайли на задачата",
"vws_view_month" => "Месечен изглед",
"vws_view_week" => "Седмичен изглед",
"vws_view_day" => "Дневен изглед",
"vws_click_for_full" => "Пълен месечен изглед",
"vws_view_full" => "Пълен изглед",
"vws_prev_year" => "Предходна година",
"vws_next_year" => "Следваща година",
"vws_prev_month" => "Предходен месец",
"vws_next_month" => "Следващ месец",
"vws_forward" => "Напред",
"vws_backward" => "Назад",
"vws_mark_day" => "Маркиране на ден",
"vws_today" => "Днес",
"vws_back_to_today" => "Върни се към днес",
"vws_back_to_main_cal" => "Обратно към началото",
"vws_week" => "Седмица",
"vws_wk" => "сед",
"vws_time" => "Час",
"vws_events" => "Задачи",
"vws_all_day" => "Целодневно",
"vws_earlier" => "По-рано",
"vws_later" => "По-късно",
"vws_venue" => "Място",
"vws_address" => "Адрес",
"vws_events_for_next" => "Задачи за следващите ",
"vws_days" => "дни",
"vws_added" => "Дoбавен",
"vws_edited" => "Редактиран",
"vws_notify" => "Уведомяване",
"vws_none_due_in" => "Няма предстоящи задачи през следващите",
"vws_evt_cats" => "Категории задачи",
"vws_cal_users" => "Потребители на календара",
"vws_no_users" => "Няма потребители в избраните групи",
"vws_start" => "Начало",
"vws_duration" => "Продължителност",
"vws_no_events_in_gc" => "Няма задачи за избрания период",
"vws_download" => "Изтегли",
"vws_download_title" => "Изтегли файл с тези задачи",
"vws_send_mail" => "Изпрати E-mail",

//changes.php
"chg_select_date" => "Изберете начална дата",
"chg_notify" => "Напомняне",
"chg_days" => "Ден(дни)",
"chg_added" => "Добавен",
"chg_edited" => "Редактиран",
"chg_deleted" => "Изтрити",
"chg_changed_on" => "Промени от",
"chg_no_changes" => "Без промяна.",

//search.php
"sch_define_search" => "Дефинирайте търсене",
"sch_search_text" => "Търсен текст",
"sch_event_fields" => "Полета на задачата",
"sch_all_fields" => "Всички полета",
"sch_title" => "Заглавие",
"sch_description" => "Описание",
"sch_venue" => "Местоположение",
"sch_user_group" => "Потребителска група",
"sch_event_cat" => "Категория на задачата",
"sch_all_groups" => "Всички групи",
"sch_all_cats" => "Всички категории",
"sch_occurring_between" => "Настъпващи между",
"sch_select_start_date" => "Изберете начална дата",
"sch_select_end_date" => "Изберете крайна дата",
"sch_search" => "Търси",
"sch_invalid_search_text" => "Не е зададен текст за търсене или е твърде кратък",
"sch_bad_start_date" => "Неправилна начална дата",
"sch_bad_end_date" => "Неправилна крайна дата",
"sch_no_results" => "Не са намерени резултати",
"sch_new_search" => "Ново търсене",
"sch_calendar" => "Отиди към календар",
"sch_extra_field1" => "Допълнително поле 1",
"sch_extra_field2" => "Допълнително поле 2",
"sch_sd_events" => "Еднодневни задачи",
"sch_md_events" => "Многодневни задачи",
"sch_rc_events" => "Повтарящи се задачи",
"sch_instructions" =>
"<h3>Инструкции за търсене</h3>
<p> В календара може да се търсят задачи, съдържащи конкретен текст. </p>
<br> <p> <b> Търсене на текст </b>: Избрани полета (вижте по-долу) на всяка задача ще
бъдат претърсени.<br>За знаци <b>a - z</b> търсенето не е чувствително към регистъра. </p>
<p> Могат да се използват два заместващи знака: </p>
<ul>
<li><b>Въпросник (?)</b> в търсения текст замества отделен символ.
<br>Например: '?e?r' ще открие 'beer', 'dear', 'heir'.</li>
<li><b>звездички (*)</b> в търсения текст замества неограничен брой 
символи.<br>Например: 'de*r' ще открие 'December', 'dear', 'developer'.</li>
</ul>
<br><p><b>Полета на задачите</b>: Ще се търси само в избраните полета.</p>
<br><p><b>Потребителска група</b>: Ще бъдат търсени само задачи за избраната потребителска група.</p>
<br><p><b>Категория на задачата</b>: Ще бъдат търсени само задачи от избраната категория</p>
<br><p><b>Настъпващи между</b>: Началната и крайната дата не са задължителни. В
в случай на празна начална / крайна дата, броя дни по подразбиране за търсене назад е $1 дни, 
а напред $2 дни спрямо текущата дата. </p>
<br> <p> За да се избегне повторение на едно и също събитие, резултатите от търсенето ще бъдат разделени
в еднодневни задачи, многодневни задачи и повтарящи се задачи. </p>
<p> Резултатите от търсенето се показват в хронологичен ред. </p>",

//thumbnails.php
"tns_man_tnails_instr" => "Инструкция за редакция на миниатюри",
"tns_help_general" => "Изображенията по -долу могат да се използват в изгледите на календара, като вмъкнете името на файла си в полето за описание на събитието или в едно от допълнителните полета. Име на файл с изображение може да бъде копирано в клипборда, като щракнете върху желаната миниатюра по -долу; впоследствие в прозореца на събитието името на изображението може да бъде вмъкнато в едно от полетата чрез въвеждане на CTRL-V. Под всяка миниатюра ще намерите: името на файла (без префикса на ID), датата на файла и между скобите последната дата, която миниатюрата се използва от календара.",
"tns_help_upload" => "Миниатюрите могат да бъдат качени от вашия локален компютър, като изберете бутона Преглед. За да изберете няколко файла, задръжте клавиша CTRL или SHIFT, докато избирате (максимум 20 наведнъж). Приемат се следните типове файлове: $1. Миниатюри с размер по -голям от $2 x $3 пиксела (ш x в) ще бъдат преоразмерени автоматично.",
"tns_help_delete" => "Миниатюри с червен Х в горния ляв ъгъл могат да бъдат изтрити, като изберете този Х. Миниатюрите без червен Х не могат да бъдат изтрити, защото те все още се използват след $1. Внимание: Изтритите миниатюри не могат да бъдат възстановени!",
"tns_your_tnails" => "Ваши миниатюри",
"tns_other_tnails" => "Други миниатюри",
"tns_man_tnails" => "Редакция на миниатюри",
"tns_sort_by" => "Подреди по",
"tns_sort_order" => "Подредба",
"tns_search_fname" => "Търси име на файл",
"tns_upload_tnails" => "Качи миниатюра",
"tns_name" => "име",
"tns_date" => "дата",
"tns_ascending" => "възходящо",
"tns_descending" => "низходящо",
"tns_not_used" => "не се ползва",
"tns_infinite" => "безкраен",
"tns_del_tnail" => "Изтрий миниатюра",
"tns_tnail" => "Миниатюра",
"tns_deleted" => "изтрит",
"tns_tn_uploaded" => "миниатюра(и) качени",
"tns_overwrite" => "позволи презаписване",
"tns_tn_exists" => "миниатюрата вече съществува – не е качена",
"tns_upload_error" => "грешка при качване",
"tns_no_valid_img" => "не е валидна картинка",
"tns_file_too_large" => "файла е прекалено голям",
"tns_resized" => "преоразмерен",
"tns_resize_error" => "грешка при преоразмеряване",

//contact.php
"con_msg_to_admin" => "Съобщение до администратора",
"con_from" => "От",
"con_name" => "Име",
"con_email" => "E-mail",
"con_subject" => "Тема",
"con_message" => "Съобщение",
"con_send_msg" => "Изпрати",
"con_fill_in_all_fields" => "Моля, попълнете всички полета",
"con_invalid_name" => "Невалидно Име",
"con_invalid_email" => "Невалиден E-mail адрес",
"con_no_urls" => "В съобщението не се допускат уеб връзки",
"con_mail_error" => "Съобщението не можа да бъде изпратено. Моля, опитайте отново по-късно.",
"con_con_msg" => "Съобщение за контакт от календара",
"con_thank_you" => "Благодарим за Вашето съобщение",
"con_get_reply" => "Ще получите отговор на съобщението си възможно най-скоро",
"con_date" => "Дата",
"con_your_msg" => "Вашето съобщение",
"con_your_cal_msg" => "Вашето съобщение",
"con_has_been_sent" => "беше изпратено на администраторът",
"con_confirm_eml_sent" => "Имейл за потвърждение е изпратен на",

//msglog.php
"msl_search" => "Search",
"msl_date" => "date",
"msl_text" => "text",
"msl_sent_msgs" => "Sent notification messages",
"msl_no_logs_found" => "No message logs found!",
"msl_errors" => "ERRORS OCCURRED! See luxcal log",

//alert.php
"alt_message#0" => "Сесията ви скоро ще изтече!",
"alt_message#1" => "PHP СЕСИЯТА ИЗТЕЧЕ",
"alt_message#2" => "Презаредете Календара",
"alt_message#3" => "НЕВАЛИДНА ЗАЯВКА",

//stand-alone sidebar (lcsbar.php)
"ssb_upco_events" => "Предстоящи задачи",
"ssb_all_day" => "Целодневни",
"ssb_none" => "Няма задачи."
);
?>
