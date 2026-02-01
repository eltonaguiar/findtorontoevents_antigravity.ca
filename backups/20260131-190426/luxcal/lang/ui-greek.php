<?php
/*
= LuxCal user interface language file =

This file has been produced by Icehockey. Please send comments to rb@luxsoft.eu.

The content of this file is put in the public domain. Use it any way you like.
This file is part of the LuxCal Web Calendar (www.LuxSoft.eu).
*/

//LuxCal ui language
$isocode = "el";

/* -- Titles on the Header of the Calendar and Date Picker -- */

$months = array("Ιανουάριος", "Φεβρουάριος", "Μάρτιος", "Απρίλιος", "Μάιος", "Ιούνιος", "Ιούλιος", "Αύγουστος", "Σεπτέμβριος", "Οκτώβριος", "Νοέμβριος", "Δεκέμβριος");
$months_m = array("Ιαν", "Φεβ", "Μαρ", "Απρ", "Μαϊ", "Ιουν", "Ιουλ", "Αυγ", "Σεπ", "Οκτ", "Νοε", "Δεκ");
$wkDays = array("Κυριακή", "Δευτέρα", "Τρίτη", "Τετάρτη", "Πέμπτη", "Παρασκευή", "Σάββατο", "Κυριακή");
$wkDays_l = array("Κυρ", "Δευ", "Τρι", "Τετ", "Πεμ", "Παρ", "Σαβ","Κυρ");
$wkDays_m = array("Κυ", "Δε", "Τρ", "Τε", "Πε", "Πα", "Σα","Κυ");
$wkDays_s = array("Κ", "Δ", "Τ", "Τ", "Π", "Π", "Σ","Κ");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Υποβολή",
"log_in" => "Σύνδεση",
"log_out" => "Αποσύνδεση",
"portrait" => "Portrait",
"landscape" => "Landscape",
"none" => "Καμία",
"all_day" => "Ολοήμερο",
"back" => "Επιστροφή",
"restart" => "Επανεκίνηση",
"by" => "από",
"of" => "του",
"max" => "Μέγιστι.",
"options" => "Επιλογές",
"done" => "OK",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "Από", //e.g. from 9:30
"until" => "Μέχρι", //e.g. until 15:30
"to" => "To", //e.g. to 17-02-2020
"birthdays_in" => "Birthdays in",
"open_calendar" => "Άνοιγμα ημερολογίου",
"no_way" => "Δεν έχετε εξουσιοδότηση να εκτελέσετε αυτή την ενέργεια",

//index.php
"title_log_in" => "Σύνδεση",
"title_profile" => "Προφίλ χρήσττη",
"title_upcoming" => "Επερχόμενες εκδηλώσεις",
"title_event" => "Εκδήλωση",
"title_check_event" => "Έλεγχος εκδήλωσης",
"title_dmarking" => "Day Marking",
"title_search" => "Αναζήτηση κειμένου",
"title_contact" => "Φόρμα επικοινονίας",
"title_thumbnails" => "Μικρογραφίες",
"title_user_guide" => "Οδηγίες χρήσης LuxCal",
"title_settings" => "Διαχείριση ρυθμίσεων ημερολογίου",
"title_edit_cats" => "Επεξεργασία κατηγοριών",
"title_edit_users" => "Επεξεργασία χρηστών",
"title_edit_groups" => "Επεξεργασία ομάδων χρηστών",
"title_edit_text" => "Text Editor",
"title_manage_db" => "Διαχείριση βάσης δεδομένων",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "Προστεθείσες / Τροποποιηθείσες / Διαγραφείσες εκδηλώσεις",
"title_usr_import" => "User File Import - CSV format",
"title_usr_export" => "User File Export - CSV format",
"title_evt_import" => "Event File Import - CSV format",
"title_ics_import" => "Event File Import - iCal format",
"title_ics_export" => "Event File Export - iCal format",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "Μορφή περιβάλλοντος χρήστη",
"title_bd_calendar" => "Birthday Calendar",

//header.php
"hdr_button_back" => "Επιστροφή στην προηγούμενη σελίδα",
"hdr_options_submit" => "Κάντε τις επιλογές σας και πατήστε 'OK'",
"hdr_options_panel" => "Μενού καρτέλας επιλογών",
"hdr_select_date" => "Μετάβαση στην ημερομηνία",
"hdr_calendar" => "Ημερολόγιο",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Εικόνα",
"hdr_lang" => "Γλώσσα",
"hdr_all_cats" => "Όλες οι κατηγορίες",
"hdr_all_groups" => "Όλες οι ομάδες",
"hdr_all_users" => "Όλοι οι χρήστες",
"hdr_go_to_view" => "Μετάβαση σε εμφάνιση",
"hdr_view_1" => "Έτους",
"hdr_view_2" => "Mήνα",
"hdr_view_3" => "Εργάσιμου μήνα",
"hdr_view_4" => "Εβδομάδας",
"hdr_view_5" => "Εργάσιμης εβδομάδας",
"hdr_view_6" => "Ημέρας",
"hdr_view_7" => "Επερχόμενων εκδηλώσεων",
"hdr_view_8" => "Μεταβολών",
"hdr_view_9" => "Matrix(C)",
"hdr_view_10" => "Matrix(U)",
"hdr_view_11" => "Gantt Chart",
"hdr_select_admin_functions" => "Επιλογή λειτουργιών διαχειριστή",
"hdr_admin" => "Διαχείριση",
"hdr_settings" => "Ρυθμίσεις",
"hdr_categories" => "Κατηγορίες",
"hdr_users" => "Χρήστες",
"hdr_groups" => "Ομάδες χρηστών",
"hdr_text_editor" => "Text Editor",
"hdr_database" => "Βάση δεδομένων",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "User Import (CSV file)",
"hdr_export_usr" => "User Export (CSV file)",
"hdr_import_csv" => "Event Import (CSV file)",
"hdr_import_ics" => "Event Import (iCal file)",
"hdr_export_ics" => "Event Export (iCal file)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Μορφή",
"hdr_back_to_cal" => "Επιστροφή στο ημερολόγιο",
"hdr_button_print" => "Εκτύπωση",
"hdr_print_page" => "Εκτύπωση αυτής της σελίδας",
"hdr_button_pdf" => "PDF File - Events",
"hdr_button_pdf_bc" => "PDF File - Birthdays",
"hdr_dload_pdf" => "Download events displayed",
"hdr_dload_pdf_bc" => "Download birthday calendar",
"hdr_button_contact" => "Επαφή",
"hdr_contact" => "Επικοινωνήστε με το διαχειριστή",
"hdr_button_tnails" => "Μικρογραφίες",
"hdr_tnails" => "Ε",
"hdr_button_toap" => "Ενέκρινε",
"hdr_toap_list" => "Συμβάντα για έγκριση",
"hdr_button_todo" => "Εργασίες",
"hdr_todo_list" => "Λίστα εργασιών",
"hdr_button_upco" => "Επερχόμενα",
"hdr_upco_list" => "Επερχόμενες εκδηλώσεις",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Αναζήτηση",
"hdr_search" => "Αναζήτηση κειμένου",
"hdr_button_add" => "Προσθήκη",
"hdr_add_event" => "Προσθήκη εκδήλωσης",
"hdr_button_help" => "Βοήθεια",
"hdr_user_guide" => "Οδηγίες χρήσης",
"hdr_gen_guide" => "Γενικό Εγχειρίδιο Χρήσης",
"hdr_cs_guide" => "Εγχειρίδιο Χρήσης με βάση το Περιεχόμενο",
"hdr_gen_help" => "Γενική βοήθεια",
"hdr_prev_help" => "Προηγούμενη βοήθεια",
"hdr_open_menu" => "Ανοίξτε το Μενού",
"hdr_side_menu" => "Πλευρικό μενού",
"hdr_dest_cals" => "Destination Calendar(s)",
"hdr_copy_evt" => "Copy Event",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "σήμερα", //dtpicker.js
"hdr_clear" => "εκκαθάριση", //dtpicker.js

//event.php
"evt_no_title" => "Χωρίς τίτλο",
"evt_no_start_date" => "Χωρίς ημερομηνία έναρξης",
"evt_bad_date" => "Λανθασμένη ημερομηνία",
"evt_bad_rdate" => "Λανθασμένη ημερομηνία λήξης επανάληψης",
"evt_no_start_time" => "Χωρίς ώρα έναρξης",
"evt_bad_time" => "Λανθασμένη ώρα",
"evt_end_before_start_time" => "Ώρα λήξης πριν την ώρα έναρξης",
"evt_end_before_start_date" => "Ημερομηνία λήξης πριν την ημερομηνία έναρξης",
"evt_until_before_start_date" => "Ημερομηνία επανάληψης πριν την ημερομηνία έναρξης",
"evt_default_duration" => "Προεπιλεγμένη διάρκεια συμβάντος $1 ώρες και $2 λεπτά",
"evt_fixed_duration" => "Σταθερή διάρκεια συμβάντος $1 ώρες και $2 λεπτά",
"evt_approved" => "Εκδήλωση εγκεκριμένη",
"evt_apd_locked" => "Εκδήλωση εγκεκριμένη και κλειδωμένη",
"evt_title" => "Τίτλος",
"evt_venue" => "Τόπος",
"evt_address_button" => "Μία διεύθυνση μεταξύ του χαρακτήρα ! θα γίνει ένα κουμπί",
"evt_list" => "List",
"evt_category" => "Κατηγορία",
"evt_subcategory" => "Υποκατηγορία",
"evt_description" => "Περιγραφή",
"evt_attachments" => "Συνημμένα",
"evt_attach_file" => "Επισύναψη αρχείου",
"evt_click_to_open" => "Πατήστε για άνοιγμα",
"evt_click_to_remove" => "Πατήστε για διαγραφή",
"evt_no_pdf_img_vid" => "Το συνημμένο πρέπει να είναι pdf, εικόνα ή video",
"evt_error_file_upload" => "Σφάλμα κατά την επισύναψη αρχείου",
"evt_upload_too_large" => "Το επισυναπτόμενο αρχείο είναι πολύ μεγάλο",
"evt_date_time" => "Ημερομηνία / ώρα",
"evt_date" => "Ημερομηνία",
"evt_private" => "Ιδιωτική εκδήλωση",
"evt_start_date" => "Έναρξη",
"evt_end_date" => "Λήξη",
"evt_select_date" => "Επιλέξτε ημερομηνία",
"evt_select_time" => "Επιλέξτε ώρα",
"evt_all_day" => "Ολοήμερη",
"evt_no_time" => "No Time",
"evt_change" => "Μεταβολή",
"evt_set_repeat" => "Ρύθμιση επανάληψης",
"evt_set" => "OK",
"evt_help" => "βοήθεια",
"evt_repeat_not_supported" => "Η ορισθείσα επανάληψη δεν υποστηρίζεται",
"evt_no_repeat" => "Χωρίς επανάληψη",
"evt_rolling" => "Rolling",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Επανάληψη κάθε",
"evt_until" => "μέχρι",
"evt_blank_no_end" => "κενό: χωρίς λήξη",
"evt_each_month" => "κάθε μήνα",
"evt_interval2_1" => "πρώτο/η",
"evt_interval2_2" => "δεύτερο/η",
"evt_interval2_3" => "τρίτο/η",
"evt_interval2_4" => "τέταρτο/η",
"evt_interval2_5" => "τελευταίο/α",
"evt_period1_1" => "ημέρα/ες",
"evt_period1_2" => "εβδομάδα/ες",
"evt_period1_3" => "μήνα/ες",
"evt_period1_4" => "έτος/η",
"evt_notification" => "Ειδοποίηση",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "τώρα και/ή",
"evt_event_added" => "Νέα εκδήλωση",
"evt_event_edited" => "Τροποποιηθείσα εκδήλωση",
"evt_event_deleted" => "Διαγραφείσα εκδήλωση",
"evt_event_approved" => "Εγκεκριμένο συμβάν",
"evt_days_before_event" => "ημέρα/ες πριν την εκδήλωση στον:",
"evt_to" => "Προς",
"evt_not_help" => "Λίστα διευθύνσεων παραληπτών που χωρίζονται με ερωτηματάκια.Η διεύθυνση παραλήπτη μπορεί να είναι ένα όνομα χρήστη, μια διεύθυνση ηλεκτρονικού ταχυδρομείου, ένας αριθμός κινητού τηλεφώνου, eva Telegram chat ID ή, μεταξύ αγκύλων, το όνομα ενός αρχείου .txt με διευθύνσεις στους 'επιστήμονες ' με μια διεύθυνση (ένα όνομα χρήστη, μια διεύθυνση ηλεκτρονικού ταχυδρομείου ή έναν αριθμό κινητού τηλεφώνου ή eva Telegram chat ID) ανά γραμμή .. <br>Μέγιστο μήκος πεδίου: 255 χαρακτήρες.",
"evt_recip_list_too_long" => "Η λίστα διευθύνσεων παραληπτών έχει πάρα πολλούς χαρακτήρες.",
"evt_no_recip_list" => "Λείπουν οι διευθύνσεις αποστολής ειδοποιήσεων",
"evt_not_in_past" => "Η ημερομηνία ειδοποίησης είναι στο παρελθόν",
"evt_not_days_invalid" => "Λανθασμένες ημέρες ειδοποίησης",
"evt_status" => "Κατάσταση",
"evt_descr_help" => "Στο πεδίο περιγραφή μπορούν να χρησιμοποιηθούν τα παρακάτω στοιχεία ...<br>• ετικέτες HTML &lt;b&gt;, &lt;i&gt;, &lt;u&gt; και &lt;s&gt; για έντονο, πλάγιο, υπογραμμισμένο και διεγραμμένο κείμενο.",
"evt_descr_help_img" => "• μικρές εικόνες (μικρογραφίες) στην ακόλουθη μορφή: 'όνομα_εικόνας.επέκταση'. Τα αρχεία μικρογραφιών, με επέκταση αρχείου .gif, .jpg ή .png, πρέπει να είναι παρόντα στο φάκελο 'thumbnails'. Εάν είναι ενεργοποιημένη, η σελίδα Thumbnails μπορεί να χρησιμοποιηθεί για τη μεταφόρτωση αρχείων μικρογραφιών.",
"evt_descr_help_eml" => "• Αποστολή προς - συνδέσεις με την ακόλουθη μορφή: 'διεύθυνση email' ή 'διεύθυνση email [όνομα]', where 'όνομα' θα είναι ο τίτλος του συνδέσμου. π.χ. xxx@yyyy.zzz [Για πληροφορίες πατήστε εδώ].",
"evt_descr_help_url" => "• Υπερσύνδεσμοι URL στη μορφή: 'url' ή  'url [όνομα]', όπου 'όνομα' θα είναι ο τίτλος του υπερσυνδέσμου. If 'S:' is placed in front of the URL, the link will open in the same page/tab, otherwise the link will open in a blank page/tab. Π.χ. S:https://www.google.com [εύρεση].",
"evt_confirm_added" => "η εκδήλωση προστέθηκε",
"evt_confirm_saved" => "η εκδήλωση αποθηκεύτηκε",
"evt_confirm_deleted" => "η εκδήλωση διαγράφηκε",
"evt_add_close" => "Προσθήκη και επιστροφή",
"evt_add" => "Προσθήκη",
"evt_edit" => "Επεξεργασία",
"evt_save_close" => "Αποθήκευση και επιστροφή",
"evt_save" => "Αποθήκευση",
"evt_clone" => "Αποθήκευση ως νέα",
"evt_delete" => "Διαγραφή",
"evt_close" => "Επιστροφή",
"evt_added" => "Προστέθηκε",
"evt_edited" => "Τροποποιήθηκε",
"evt_is_repeating" => "είναι επαναλαμβανόμενη εκδήλωση.",
"evt_is_multiday" => "είναι πολυήμερη εκδήλωση.",
"evt_edit_series_or_occurrence" => "Επιθυμείτε να τροποποιήσετε την εκδήλωση για όλη τη χρονική διάρκειά της ή μόνο την συγκεκριμένη;",
"evt_edit_series" => "Επεξεργασία για όλη τη χρονική διάρκεια της εκδήλωσης",
"evt_edit_occurrence" => "Επεξεργασία μόνο για τη συγκεκριμένη εκδήλωση",
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
"vws_add_event" => "Προσθήκη εκδήλωσης",
"vws_edit_event" => "Επεξεργασία συμβάντος",
"vws_see_event" => "Δείτε λεπτομέρειες εκδήλωσης",
"vws_view_month" => "Εικόνα μήνα",
"vws_view_week" => "Εικόνα εβδομάδας",
"vws_view_day" => "Εικόνα ημέρας",
"vws_click_for_full" => "για πλήρες ημερολόγιο πατήστε στον μήνα",
"vws_view_full" => "Εικόνα πλήρους ημερολογίου",
"vws_prev_year" => "Προηγούμενο έτος",
"vws_next_year" => "Επόμενο έτος",
"vws_prev_month" => "Προηγούμενος μήνας",
"vws_next_month" => "Επόμενος μήνας",
"vws_forward" => "Forward",
"vws_backward" => "Backward",
"vws_mark_day" => "Mark day",
"vws_today" => "Σήμερα",
"vws_back_to_today" => "Επιστροφή στον σημερινό μήνα",
"vws_back_to_main_cal" => "Back to the main calendar month",
"vws_week" => "Εβδομάδα",
"vws_wk" => "εβδ",
"vws_time" => "Ώρα",
"vws_events" => "Εκδηλώσεις",
"vws_all_day" => "Ολοήμερη",
"vws_earlier" => "Νωρίτερα",
"vws_later" => "Αργότερα",
"vws_venue" => "Τόπος",
"vws_address" => "Address",
"vws_events_for_next" => "Επερχόμενες εκδηλώσεις επόμενης/ων",
"vws_days" => "ημέρας(ων)",
"vws_added" => "Προστέθηκε",
"vws_edited" => "Τροποποιήθηκε",
"vws_notify" => "Ειδοποίηση",
"vws_none_due_in" => "Καμμία εκδήλωση δεν λήγει τον/την επόμενο/η",
"vws_evt_cats" => "Κατηγορίες συμβάντων",
"vws_cal_users" => "Χρήστες ημερολογίου",
"vws_no_users" => "Δεν υπάρχουν χρήστες σε επιλεγμένες ομάδες",
"vws_start" => "Start",
"vws_duration" => "Duration",
"vws_no_events_in_gc" => "No events in the selected period",
"vws_download" => "Μεταφόρτωση",
"vws_download_title" => "Μεταφόρτωση αρχείου κειμένου με αυτές τις εκδηλώσεις",
"vws_send_mail" => "Αποστολή ηλεκτρονικού ταχυδρομείου",

//changes.php
"chg_select_date" => "Επιλογή αρχικής ημερομηνίας",
"chg_notify" => "Ειδοποίηση",
"chg_days" => "Ημέρα(ες)",
"chg_added" => "Προστέθηκε",
"chg_edited" => "Τροποποιήθηκε",
"chg_deleted" => "Διαγράφηκε",
"chg_changed_on" => "Μεταβολές για",
"chg_no_changes" => "Χωρίς μεταβολές.",

//search.php
"sch_define_search" => "Καθορισμός αναζήτησης",
"sch_search_text" => "Κείμενο αναζήτησης",
"sch_event_fields" => "Στα πεδία",
"sch_all_fields" => "Σε όλα τα πεδία",
"sch_title" => "Στον τίτλο",
"sch_description" => "Στην περιγραφή",
"sch_venue" => "Στον τόπο",
"sch_user_group" => "Ομάδα χρηστών",
"sch_event_cat" => "Κατηγορία εκδήλωσης",
"sch_all_groups" => "Όλες οι ομάδες",
"sch_all_cats" => "Όλες οι κατηγορίες",
"sch_occurring_between" => "Η εκδήλωση πραγματοποιείται μεταξύ",
"sch_select_start_date" => "Επιλέξτε ημερομηνία έναρξης",
"sch_select_end_date" => "Επιλέξτε ημερομηνία λήξης",
"sch_search" => "Αναζήτηση",
"sch_invalid_search_text" => "Το κείμενο αναζήτησης λείπει ή είναι πολύ βραχύ",
"sch_bad_start_date" => "Λανθασμένη ημερομηνία έναρξης",
"sch_bad_end_date" => "Λανθασμένη ημερομηνία λήξης",
"sch_no_results" => "Δεν βρέθηκαν αποτελέσματα που να ταιριάζουν",
"sch_new_search" => "Νέα αναζήτηση",
"sch_calendar" => "Επιστροφή στο ημερολόγιο",
"sch_extra_field1" => "Έξτρα πεδίο 1",
"sch_extra_field2" => "Έξτρα πεδίο 2",
"sch_sd_events" => "Single-day events",
"sch_md_events" => "Multi-day events",
"sch_rc_events" => "Recurring events",
"sch_instructions" =>
"<h3>Οδηγίες αναζήτησης κειμένου</h3>
<p>Στη βάση δεδομένων του ημερολογίου μπορεί να γίνει αναζήτηση εκδηλώσεων που ταιριάζουν με ορισμένο κείμενο.</p>
<br><p><b>Αναζήτηση κειμένου</b>: Τα επιλεγμένα πεδία (βλ. παρακάτω) κάθε εκδήλωσης θα ελεγχθούν. Η αναζήτηση δεν διακρίνει κεφαλαία και πεζά (τουλάχιστον στα λατινικά γράμματα, ίσως και στα ελληνικά ανάλογα με την εγκατάσταση PHP σας).</p>
<p>Μπορούν να χρησιμοποιηθούν δύο χαρακτήρες μπαλαντέρ:</p>
<ul>
<li>Ένα ερωτηματικό (?) στο κείμενο αναζήτησης ταιριάζει με οποιονδήποτε χαρακτήρα στο πεδίο.<br>Π.χ.: το '?έ?α' ταιριάζει στα 'δέμα', 'πέρα', 'βέρα'.</li>
<li>Ένας αστερίσκος (*) στο κείμενο αναζήτησης ταιριάζει με οποιανδήποτε συμβολοσειρά, οποιουδήποτε μήκους (δηλαδή αποτελούμενη από 0 και άνω οποιουσδήποτε χαρακτήρες).<br>Π.χ.: το 'Δ*' ταιριάζει στα 'Δ', 'Δ.', 'Δρ.', 'Δέμα', 'Δημόκριτος'.</li>
</ul>
<br><p><b>Πεδία εκδήλωσης</b>: Η αναζήτηση θα γίνει μόνο στα καθοριζόμενα πεδία.</p>
<br><p><b>User group</b>: Events in the selected user group will be searched only.</p>
<br><p><b>Κατηγορία εκδήλωσης</b>: Η αναζήτηση θα γίνει μόνο στις εκδηλώσεις της καθοριζόμενης κατηγορίας.</p>
only.</p>
<br><p><b>Η εκδήλωση πραγματοποιείται μεταξύ</b>: Η ημερομηνία έναρξης και λήξης είναι προαιρετικές. In case of a blank start / end date, the default number of days to search back and ahead will be $1 days and $2 days respectively.</p>
<br><p>To avoid repetitions of the same event, the search results will be split 
in single-day events, multi-day events and recurring events.</p>
<p>Τα αποτελέσματα της αναζήτησης εμφανίζονται με χρονολογική σειρά.</p>",

//thumbnails.php
"tns_man_tnails_instr" => "Διαχείριση Οδηγιών Thumbnails",
"tns_help_general" => "Οι παρακάτω εικόνες μπορούν να χρησιμοποιηθούν στις προβολές ημερολογίου, εισάγοντας το όνομα του αρχείου τους στο πεδίο περιγραφής της εκδήλωσης ή σε ένα από τα επιπλέον πεδία. Ένα όνομα αρχείου εικόνας μπορεί να αντιγραφεί στο πρόχειρο κάνοντας κλικ στην παρακάτω μικρογραφία · στη συνέχεια, στο παράθυρο συμβάντος, το όνομα της εικόνας μπορεί να εισαχθεί σε ένα από τα πεδία πληκτρολογώντας το CTRL-V. Κάτω από κάθε μικρογραφία θα βρείτε: το όνομα του αρχείου (χωρίς το πρόθεμα χρήστη), την ημερομηνία αρχείου και μεταξύ των παρενθέσεων τελευταία ημερομηνία η μικρογραφία χρησιμοποιείται από το ημερολόγιο.",
"tns_help_upload" => "Οι μικρογραφίες μπορούν να μεταφορτωθούν από τον τοπικό σας υπολογιστή επιλέγοντας το κουμπί Browse (Αναζήτηση) Για να επιλέξετε πολλά αρχεία, κρατήστε πατημένο το πλήκτρο CTRL ή SHIFT ενώ επιλέγετε (το πολύ 20 κάθε φορά) $ 1. Οι μικρογραφίες με μέγεθος μεγαλύτερο από $ 2 x $ 3 pixels (wxh) θα αλλάξουν αυτόματα.",
"tns_help_delete" => "Οι μικρογραφίες με κόκκινο σταυρό στην επάνω αριστερή γωνία μπορούν να διαγραφούν επιλέγοντας αυτό το σταυρό.<br>Thumbnails χωρίς κόκκινο σταυρό δεν μπορούν να διαγραφούν, επειδή εξακολουθούν να χρησιμοποιούνται μετά από $ 1. Προσοχή: Δεν είναι δυνατή η ανάκτηση των διαγραμμένων μικρογραφιών!",
"tns_your_tnails" => "Οι μικρογραφίες σας",
"tns_other_tnails" => "Άλλες μικρογραφίες",
"tns_man_tnails" => "Διαχείριση μικρογραφιών",
"tns_sort_by" => "Ταξινόμηση κατά",
"tns_sort_order" => "Σειρά ταξινόμησης",
"tns_search_fname" => "Αναζήτηση όνομα αρχείου",
"tns_upload_tnails" => "Ανέβασμα μικρογραφιών",
"tns_name" => "όνομα",
"tns_date" => "ημερομηνία",
"tns_ascending" => "αύξουσα",
"tns_descending" => "φθίνουσα",
"tns_not_used" => "δεν χρησιμοποιείται",
"tns_infinite" => "άπειρη",
"tns_del_tnail" => "Διαγραφή μικρογραφίας",
"tns_tnail" => "Μικρογραφία",
"tns_deleted" => "διαγράφηκε",
"tns_tn_uploaded" => "Ανεβασμένες μικρογραφίες",
"tns_overwrite" => "επιτρέπεται η αντικατάσταση",
"tns_tn_exists" => "η μικρογραφία υπάρχει ήδη - δεν μεταφορτώθηκε",
"tns_upload_error" => "σφάλμα φόρτωσης",
"tns_no_valid_img" => "δεν είναι έγκυρη εικόνα",
"tns_file_too_large" => "αρχείο πάρα πολύ μεγάλο",
"tns_resized" => "αλλαγή μεγέθους",
"tns_resize_error" => "σφάλμα αλλαγής μεγέθους",

//contact.php
"con_msg_to_admin" => "Μήνυμα προς τον διαχειριστή",
"con_from" => "Από",
"con_name" => "Όνομα",
"con_email" => "Email",
"con_subject" => "Θέμα",
"con_message" => "Μήνυμα",
"con_send_msg" => "Αποστολή μηνύματος",
"con_fill_in_all_fields" => "Παρακαλώ συμπληρώστε όλα τα πεδία",
"con_invalid_name" => "Μη έγκυρο όνομα",
"con_invalid_email" => "Μη έγκυρη διεύθυνση ηλεκτρονικού ταχυδρομείου",
"con_no_urls" => "Δεν επιτρέπονται συνδέσεις ιστού στο μήνυμα",
"con_mail_error" => "Πρόβλημα ηλεκτρονικού ταχυδρομείου Το μήνυμα δεν ήταν δυνατό να αποσταλεί. Δοκιμάστε ξανά αργότερα.",
"con_con_msg" => "μήνυμα επικοινωνίας από το ημερολόγιο",
"con_thank_you" => "Ευχαριστώ για το μήνυμά σας στο ημερολόγιο",
"con_get_reply" => "Θα λάβετε απάντηση στο μήνυμά σας το συντομότερο δυνατόν",
"con_date" => "Ημερομηνία",
"con_your_msg" => "Το μήνυμά σας",
"con_your_cal_msg" => "Το μήνυμά σας στο ημερολόγιο",
"con_has_been_sent" => "έχει σταλεί στον διαχειριστή ημερολογίου",
"con_confirm_eml_sent" => "Έχει σταλεί μήνυμα ηλεκτρονικού ταχυδρομείου επιβεβαίωσης",

//msglog.php
"msl_search" => "Search",
"msl_date" => "date",
"msl_text" => "text",
"msl_sent_msgs" => "Sent notification messages",
"msl_no_logs_found" => "No message logs found!",
"msl_errors" => "ERRORS OCCURRED! See luxcal log",

//alert.php
"alt_message#0" => "N συνεδρία σας σύντομα θα λήξει!",
"alt_message#1" => "Η συνεδρία PHP έληξε",
"alt_message#2" => "Κάντε επανεκκίνηση του Ημερολογίου",
"alt_message#3" => "INVALID REQUEST",

//stand-alone sidebar (lcsbar.php)
"ssb_upco_events" => "Επερχόμενες εκδηλώσεις",
"ssb_all_day" => "ολοήμερο",
"ssb_none" => "Δεν υπάρχουν εκδηλώσεις."
);
?>
