<?php
/*
= LuxCal admin interface language file =

This file has been produced by LuxSoft. Please send comments /improvements to rb@luxsoft.eu.

This file is part of the LuxCal Web Calendar.
*/

$ax = array(

//general
"none" => "Τίποτα",
"no" => "no",
"yes" => "yes",
"own" => "own",
"all" => "oλα",
"or" => "or",
"back" => "Πίσω",
"ahead" => "Ahead",
"close" => "Κλείσιμο",
"always" => "πάντα",
"at_time" => "@", //date and time separator (e.g. 30-01-2020 @ 10:45)
"times" => "times",
"cat_seq_nr" => "category sequence nr",
"rows" => "γραμμές",
"columns" => "στήλες",
"hours" => "ώρες",
"minutes" => "minutes",
"user_group" => "ομάδα χρηστών",
"event_cat" => "κατηγορία συμβάντων",
"email" => "Email",
"telegram" => "Telegram",
"sms" => "SMS",
"id" => "Ταυτότητα",
"username" => "Όνομα Χρήστη",
"password" => "Κωδικός",
"public" => "Δημόσια",
"logged_in" => "Συνδεδεμένος",
"pw_no_chars" => "Characters <, > and ~ not allowed in password",

//settings.php - fieldset headers + general
"set_general_settings" => "Γενικά",
"set_navbar_settings" => "Γραμμή Πλοήγησης",
"set_event_settings" => "Συμβάντα",
"set_user_settings" => "Λογαριασμό Χρηστών",
"set_upload_settings" => "Μεταφόρτωση αρχείων",
"set_reminder_settings" => "Υπενθυμήσεις",
"set_perfun_settings" => "Περιοδικές Λειτουργίες (έχει νόημα μόνο αν έχει οριστεί εργασία cron)",
"set_sidebar_settings" => "Αυτόνομη πλευρική λωρίδα (σε ισχύ αν είναι σε χρήση)",
"set_view_settings" => "Προβολές",
"set_dt_settings" => "Ημερομηνίες/Ώρες",
"set_save_settings" => "Αποθήκευση Ρυθμίσεων",
"set_test_mail" => "Δοκιμή Ηλεκτρονικού Ταχυδρομείου",
"set_mail_sent_to" => "Δοκιμή αλληλογραφίας που αποστέλλεται σε",
"set_mail_sent_from" => "Αυτό το μήνυμα δοκιμής στάλθηκε από τη σελίδα ρυθμίσεων του ημερολογίου σας",
"set_mail_failed" => "Αποστολή αποστολής δοκιμής απέτυχε - παραλήπτης (ες)",
"set_missing_invalid" => "λείπουν ή μη έγκυρες ρυθμίσεις (φωτισμένο φόντο)",
"set_settings_saved" => "Οι αποθηκευμένες ρυθμίσεις ημερολογίου",
"set_save_error" => "Σφάλμα βάσης δεδομένων - Αποτυχία αποθήκευσης ρυθμίσεων ημερολογίου",
"hover_for_details" => "Τοποθετήστε το δείκτη του ποντικιού πάνω από τις περιγραφές για λεπτομέρειες",
"default" => "προεπιλογή",
"enabled" => "ενεργοποιημένο",
"disabled" => "disabled",
"pixels" => "εικονοστοιχεία",
"warnings" => "Προειδοποιήσεις",
"notices" => "ειδοποιήσεις",
"visitors" => "Επισκέπτες",
"height" => "Height",
"no_way" => "Δεν έχετε εξουσιοδότηση για να εκτελέσετε αυτήν την ενέργεια",

//settings.php - general settings.
"versions_label" => "Εκδόσεις",
"versions_text" => "• εκδοχή ημερολογίου, ακολουθούμενη από τη βάση δεδομένων που χρησιμοποιείται <br> • PHP έκδοση <br> • έκδοση βάσης δεδομένων",
"calTitle_label" => "Τίτλος ημερολογίου",
"calTitle_text" => "Εμφανίζεται στην επάνω γραμμή του ημερολογίου και χρησιμοποιείται σε ειδοποιήσεις ηλεκτρονικού ταχυδρομείου.",
"calUrl_label" => "Διεύθυνση URL ημερολογίου",
"calUrl_text" => "Διεύθυνση ιστότοπου του ημερολογίου.",
"calEmail_label" => "Διεύθυνση ηλεκτρονικού ταχυδρομείου ημερολογίου",
"calEmail_text" => "Η διεύθυνση ηλεκτρονικού ταχυδρομείου που χρησιμοποιείται για τη λήψη μηνυμάτων επαφών και για αποστολή ή λήψη μηνυμάτων ηλεκτρονικού ταχυδρομείου ειδοποίησης.<br> Format: 'email ' ή 'name &#8826;email&#8827;'.",
"logoPath_label" => "Διαδρομή /όνομα εικόνας εικόνας",
"logoPath_text" => "Εάν έχει οριστεί, θα εμφανιστεί μια εικόνα λογότυπου στην πάνω αριστερή γωνία του ημερολογίου. Εάν έχει οριστεί επίσης ένας σύνδεσμος σε μια γονική σελίδα (δείτε παρακάτω), τότε το λογότυπο θα είναι υπερσύνδεσμος προς το Η εικόνα του λογότυπου θα πρέπει να έχει μέγιστο ύψος και πλάτος 70 pixel. ",
"logoXlPath_label" => "Path/name of log-in logo image",
"logoXlPath_text" => "If specified, a logo image of the specified height will be displayed on the Log In page below the Log In form.",
"backLinkUrl_label" => "Σύνδεση με τη γονική σελίδα",
"backLinkUrl_text" => "Διεύθυνση URL της γονικής σελίδας.Αν έχει καθοριστεί, θα εμφανιστεί ένα κουμπί Back στην αριστερή πλευρά της Γραμμής πλοήγησης που συνδέει με αυτήν τη διεύθυνση URL.Για παράδειγμα, για να συνδεθείτε πίσω στη γονική σελίδα από την οποία προέρχεται το ημερολόγιο Εάν έχει οριστεί μια διαδρομή /όνομα λογότυπου (βλ. παραπάνω), τότε δεν θα εμφανιστεί κανένα κουμπί 'Πίσω', αλλά το λογότυπο θα γίνει ο σύνδεσμος πίσω. ",
"timeZone_label" => "Ζώνη ώρας",
"timeZone_text" => "Η ζώνη ώρας του ημερολογίου, που χρησιμοποιείται για τον υπολογισμό της τρέχουσας ώρας.",
"see" => "δείτε",
"notifChange_label" => "Αποστολή ειδοποίησης αλλαγών ημερολογίου",
"notifChange_text" => "Όταν ένας χρήστης προσθέσει, επεξεργαστεί ή διαγράψει ένα συμβάν, θα σταλεί ένα μήνυμα ειδοποίησης στους συγκεκριμένους παραλήπτες.",
"chgRecipList" => "semicolon separated recipient list",
"maxXsWidth_label" => "Max. width of small screens",
"maxXsWidth_text" => "For displays with a width smaller than the specified number of pixels, the calendar will run in a special responsive mode, leaving out certain less important elements.",
"rssFeed_label" => "Σύνδεσμοι RSS feed",
"rssFeed_text" => "Αν είναι ενεργοποιημένη: Για χρήστες που έχουν τουλάχιστον δικαιώματα προβολής, ένας σύνδεσμος ροής RSS θα είναι ορατός στο υποσέλιδο του ημερολογίου και ένας σύνδεσμος ροής RSS θα προστεθεί στο κεφάλαιο HTML των σελίδων ημερολογίου. ",
"logging_label" => "Δεδομένα ημερολογίου καταγραφής",
"logging_text" => "Το ημερολόγιο μπορεί να καταγράφει σφάλματα, προειδοποιητικά μηνύματα και μηνύματα επισκεψιμότητας και μηνύματα επισκεψιμότητας.Η καταγραφή των μηνυμάτων προειδοποίησης και ειδοποιήσεων και των δεδομένων επισκεπτών μπορεί να απενεργοποιηθεί ή να ενεργοποιηθεί με τον έλεγχο των αντίστοιχων πλαισίων ελέγχου. , μηνύματα προειδοποίησης και ειδοποίησης καταγράφονται στο αρχείο 'logs/luxcal.log' και τα δεδομένα επισκεπτών καταγράφονται στα αρχεία 'logs/hitlog.log' και 'logs /botlog.log '. Σημείωση: Το σφάλμα PHP, τα μηνύματα προειδοποίησης και ειδοποίησης καταγράφονται σε διαφορετική τοποθεσία, όπως καθορίζεται από τον ISP σας. ",
"maintMode_label" => "PHP Maintenance mode",
"maintMode_text" => "When enabled, in the PHP scripts data submitted via the note (message) function and data stored in the 'note' variable will be shown in the calendar footer bar.",
"reciplist" => "Ο κατάλογος παραληπτών μπορεί να περιέχει ονόματα χρηστών, διευθύνσεις ηλεκτρονικού ταχυδρομείου, αριθμούς τηλεφώνου, Telegram chat IDs και ονόματα αρχείων με παραλήπτες (που περικλείονται από αγκύλες), χωρισμένα με ερωτηματικά. 'reciplists '. Όταν παραλειφθεί, η προεπιλεγμένη επέκταση αρχείου είναι .txt ",
"calendar" => "ημερολόγιο",
"user" => "χρήστης",
"database" => "βάση δεδομένων",

//settings.php - navigation bar settings.
"contact_label" => "Κουμπί επαφής",
"contact_text" => "Αν είναι ενεργοποιημένη: Στο παράθυρο εμφανίζεται ένα κουμπί επαφής. Κάνοντας κλικ σε αυτό το κουμπί θα ανοίξει μια φόρμα επικοινωνίας, η οποία μπορεί να χρησιμοποιηθεί για την αποστολή ενός μηνύματος στον διαχειριστή του ημερολογίου.",
"optionsPanel_label" => "Επιλογές πίνακα επιλογών",
"optionsPanel_text" => "Ενεργοποίηση /απενεργοποίηση των μενού στον πίνακα επιλογών <br> <br> • Το μενού ημερολογίου είναι διαθέσιμο στο διαχειριστή για την εναλλαγή των ημερολογίων (ενεργοποίηση μόνο χρήσιμο εάν έχουν εγκατασταθεί περισσότερα ημερολόγια) <br> <br> • Το μενού προβολής μπορεί να είναι που χρησιμοποιείται για την επιλογή μιας από τις προβολές ημερολογίου <br> <br> • Το μενού ομάδων μπορεί να χρησιμοποιηθεί για την εμφάνιση μόνο των συμβάντων που δημιουργούνται από τους χρήστες στις επιλεγμένες ομάδες .. <br> • Το μενού χρηστών μπορεί να χρησιμοποιηθεί για την εμφάνιση μόνο συμβάντων που δημιουργήθηκαν από τους επιλεγμένους χρήστες <br> <br> • Το μενού κατηγοριών μπορεί να χρησιμοποιηθεί για την εμφάνιση μόνο συμβάντων που ανήκουν στις επιλεγμένες κατηγορίες συμβάντων <br> <br> <br> Το μενού γλωσσών μπορεί να χρησιμοποιηθεί για να επιλέξει τη γλώσσα διεπαφής χρήστη (ενεργοποίηση μόνο εάν είναι εγκατεστημένες πολλές γλώσσες) < Σημείωση: Εάν δεν έχουν επιλεγεί μενού, το κουμπί του πίνακα επιλογών δεν θα εμφανιστεί. ",
"calMenu_label" => "ημερολόγιο",
"viewMenu_label" => "προβολή",
"groupMenu_label" => "ομάδες",
"userMenu_label" => "χρήστες",
"catMenu_label" => "κατηγορίες",
"langMenu_label" => "γλώσσα",
"availViews_label" => "Διαθέσιμες προβολές ημερολογίου",
"availViews_text" => "Εμφανίσεις ημερολογίου που είναι διαθέσιμες στους χρήστες του Publc και των συνδεδεμένων χρηστών που καθορίζονται με τη βοήθεια μιας διαχωρισμένης με κόμμα λίστας με αριθμούς προβολής. Σημασία αριθμών: 1: προβολή έτους 2: προβολή μήνα (7 ημέρες) <br> 3: προβολή μήνα εργασίας <br> 4: προβολή εβδομάδας (7 ημέρες) <br> 5: προβολή εβδομάδας εργασίας <br> 6: προβολή ημέρας <br> 7: επερχόμενες εκδηλώσεις προβολή <br> 8: αλλαγές προβολή σελίδας 9: προβολή μήτρας (κατηγορίες) <br> 10: προβολή πίνακα (χρήστες)<br>11: gantt Chart view",
"viewButtonsL_label" => "Κουμπιά προβολής στη γραμμή πλοήγησης (large display)",
"viewButtonsS_label" => "Κουμπιά προβολής στη γραμμή πλοήγησης (small display)",
"viewButtons_text" => "Προβολή κουμπιών στη γραμμή πλοήγησης για τους δημόσιους και τους συνδεδεμένους χρήστες, που καθορίζονται με τη βοήθεια μιας διαχωρισμένης με κόμμα λίστας αριθμών προβολής. <br> Αν ένας αριθμός έχει οριστεί στην ακολουθία, το αντίστοιχο κουμπί θα είναι Εάν δεν έχουν οριστεί αριθμοί, δεν θα εμφανιστούν κουμπιά προβολής. <br> Σημασία των αριθμών: <br> 1: Έτος 2: Πλήρης μήνας <br> 3: Μήνας εργασίας <br> 4: Πλήρης εβδομάδα <br> 5: Εβδομάδα εργασίας <br> 6: Ημέρα <br> 7: Προσεχώς 8: Αλλαγές <br> 9: Matrix-C <br> 10: Matrix-U <br> 11: Gantt Chart <br> Η σειρά των αριθμών καθορίζει τη σειρά των εμφανιζόμενων κουμπιών. <br>Για παράδειγμα: '2,4'σημαίνει: εμφάνιση πλήκτρων 'πλήρους μήνα' και 'πλήρους εβδομάδας'.",
"defaultViewL_label" => "Default view on start-up (large display)",
"defaultViewL_text" => "Default calendar view on startup for public and logged-in users using large displays.<br>Recommended choice: Month.",
"defaultViewS_label" => "Default view on start-up (small display)",
"defaultViewS_text" => "Default calendar view on startup for public and logged-in users using small displays.<br>Recommended choice: Upcoming.",
"language_label" => "Προεπιλεγμένη γλώσσα διεπαφής χρήστη (public user)",
"language_text" => "For public (not logged in) users the language set for the browser user interface will be used for the calendar as well. If the browser language is not a valid calendar language, this default language will be used.<br>Note: Τα αρχεία ui- {language} .php, ai- {language} .php, ug- {language} .php και ug-layout.png πρέπει να υπάρχουν στον κατάλογο lang/. {language} = επιλεγμένη γλώσσα διεπαφής χρήστη.Τα ονόματα αρχείων πρέπει να είναι πεζά! ",
"birthday_cal_label" => "PDF Birthday Calendar",
"birthday_cal_text" => "If enabled, an option 'PDF File - Birthday' will appear in the Side Menu for users with at least 'view' rights. See the admin_guide.html - Birthday Calendar for further details",
"sideLists_label" => "Approve, Todo, Upcoming lists",
"sideLists_text" => "If enabled, an option to show the respective list will appear in the Side Menu. The 'Events to be approved' list will only be available for users with at least 'manager' rights.",
"toapList_label" => "To approve list",
"todoList_label" => "To do list",
"upcoList_label" => "Upcoming list",

//settings.php - events settings.
"privEvents_label" => "Δημοσίευση ιδιωτικών εκδηλώσεων",
"privEvents_text" => "Τα ιδιωτικά συμβάντα είναι ορατά μόνο από το χρήστη που εισήλθε στην εκδήλωση. <br> Ενεργοποιημένο: οι χρήστες μπορούν να εισέλθουν σε ιδιωτικά συμβάντα <br> <br> Προεπιλογή: κατά την προσθήκη νέων συμβάντων, το 'ιδιωτικό \ Το παράθυρο συμβάντων θα ελέγχεται από προεπιλογή. <br> Πάντα: κατά την προσθήκη νέων συμβάντων θα είναι πάντοτε ιδιωτικά, το πλαίσιο ελέγχου 'ιδιωτικό ' στο παράθυρο συμβάντος δεν θα εμφανιστεί. ",
"venueInput_label" => "Specifying venues",
"venueInput_text" => "In the Event window specifying a venue can be done either by typing the venue or by selecting a venue from a pre-defined list. If Free text is selected, the user can type the venue, if List is selected the user can select a venue from a drop-down list and when Both is selected, the user can choose between the two.<br> When a drop-down list is used, the 'files' folder must contain a file called venues.txt with one venue per line.",
"timeDefault_label" => "Adding new events - time default",
"timeDefault_text" => "When adding events, in the Event window the default way the event time fields appear in the event form can be set as follows:<br>• show times: The start and end time fields are shown and ready to be completed<br>• all day: The All Day check box is checked, no start and end time fields are shown<br>• no time: The No Time check box is checked, no start and end time fields are shown.",
"evtDelButton_label" => "Εμφάνιση κουμπιού διαγραφής στο παράθυρο συμβάντος",
"evtDelButton_text" => "Απενεργοποιημένο: το κουμπί Διαγραφή στο παράθυρο συμβάντος δεν θα είναι ορατό, οπότε οι χρήστες με δικαιώματα επεξεργασίας δεν θα μπορούν να διαγράψουν συμβάντα. <br> Ενεργοποιημένο: Το κουμπί Διαγραφή στο παράθυρο συμβάντος θα είναι ορατό σε όλους <br> <br> <br> Διαχειριστής: το κουμπί Διαγραφή στο παράθυρο συμβάντος θα είναι ορατό μόνο στους χρήστες με δικαιώματα 'διαχειριστή '.",
"eventColor_label" => "Χρώματα συμβάντων βάσει",
"eventColor_text" => "Τα συμβάντα στις διάφορες προβολές ημερολογίου μπορούν να εμφανιστούν στο χρώμα που αντιστοιχεί στην ομάδα στην οποία ανήκει ο χρήστης που δημιούργησε το συμβάν ή το χρώμα της κατηγορίας του συμβάντος.",
"defVenue_label" => "Default Venue",
"defVenue_text" => "In this text field a venue can be specified which will be copied to the Venue field of the event form when adding new events.",
"xField1_label" => "Επιπλέον πεδίο 1",
"xField2_label" => "Επιπλέον πεδίο 2",
"xFieldx_text" => "Προαιρετικό πεδίο κειμένου Εάν το πεδίο αυτό περιλαμβάνεται σε ένα πρότυπο συμβάντος στην ενότητα Προβολές, το πεδίο θα προστεθεί ως πεδίο κειμένου ελεύθερης μορφής στη φόρμα παραθύρου συμβάντος και στα συμβάντα που εμφανίζονται σε όλες τις προβολές ημερολογίου και σελίδες <br>• ετικέτα: προαιρετική ετικέτα κειμένου για το επιπλέον πεδίο (έως και 15 χαρακτήρες). Για παράδειγμα, 'διεύθυνση ηλεκτρονικού ταχυδρομείου', 'ιστοσελίδα ', 'τηλέφωνο' <br>• Minimum user rights: the field will only be visible to users with the selected user rights or higher.",
"evtWinSmall_label" => "Μειωμένο παράθυρο συμβάντος",
"evtWinSmall_text" => "Κατά την προσθήκη /επεξεργασία συμβάντων, το παράθυρο συμβάντος θα εμφανίσει ένα υποσύνολο των πεδίων εισαγωγής.Για να εμφανίζονται όλα τα πεδία, μπορεί να επιλεγεί ένα bέλος.",
"emojiPicker_label" => "Emoji picker in Event window",
"emojiPicker_text" => "When enabled, in the Event Add/Edit window an emoji picker can be selected to add emoji to the event title and to the description fields.",
"mapViewer_label" => "Διεύθυνση URL θεατή χάρτη",
"mapViewer_text" => "Εάν έχει οριστεί μια διεύθυνση URL του προγράμματος προβολής χάρτη, μια διεύθυνση στο πεδίο του χώρου της εκδήλωσης που περικλείεται σε! -marks θα εμφανιστεί ως κουμπί Address στις προβολές ημερολογίου. Θα εμφανιστεί ένα νέο παράθυρο όπου θα εμφανιστεί η διεύθυνση στο χάρτη. <br> Η πλήρης διεύθυνση URL ενός προγράμματος προβολής χάρτη θα πρέπει να προσδιοριστεί, μέχρι το τέλος του οποίου μπορεί να ενταχθεί η διεύθυνση. Παραδείγματα: <br> Χάρτες Google: https://maps.google.com/maps?q= <br> OpenStreetMap: https://www.openstreetmap.org/search?query= <br> Εάν αυτό το πεδίο παραμείνει κενό , οι διευθύνσεις στο πεδίο Venue δεν θα εμφανίζονται ως κουμπί Address. ",
"evtDrAndDr_label" => "Event drag and drop",
"evtDrAndDr_text" => "When enabled, in Year view, Month view and in the mini calendar on the side panel, events can be moved or copied from one day to an other day by means of Drag and Drop. If 'manager' is selected, only users with at least manager rights can use this feature. See the admin_guide.html for a detailed description.",
"free_text" => "Free text",
"venue_list" => "Venue list",
"both" => "Both",
"xField_label" => "Ετικέτα",
"show_times" => "show times",
"check_ald" => "all day",
"check_ntm" => "no time",
"min_rights" => "Minimum user rights",
"no_color" => 'no color',
"manager_only" => 'διευθυντής',

//settings.php - user accounts settings.
"selfReg_label" => "Αυτόματη εγγραφή",
"selfReg_text" => "Να επιτρέπεται στους χρήστες να εγγραφούν οι ίδιοι για πρόσβαση στο ημερολόγιο. <br> Ομάδα χρηστών στην οποία θα έχουν εκχωρηθεί αυτοί καταχωρημένοι χρήστες.",
"selfRegQA_label" => "Self registration question/answer",
"selfRegQA_text" => "When self registration is enabled, during the self-registration process the user will be asked this question and will only be able to self-register if the correct answer is given. When the question field is left blank, no question will be asked.",
"selfRegNot_label" => "Γνωστοποίηση εγγραφής",
"selfRegNot_text" => "Στείλτε ένα μήνυμα ηλεκτρονικού ταχυδρομείου ειδοποίησης στη διεύθυνση ηλεκτρονικού ταχυδρομείου ημερολογίου όταν πραγματοποιηθεί μια αυτο εγγραφή.",
"restLastSel_label" => "Επαναφορά επιλογών τελευταίου χρήστη",
"restLastSel_text" => "Οι τελευταίες επιλογές χρήστη (οι ρυθμίσεις του πίνακα επιλογών) θα αποθηκευτούν και όταν ο χρήστης επανέλθει αργότερα στο ημερολόγιο, οι τιμές θα αποκατασταθούν. If the user does not log in during the specified number of days, the values will be lost.",
"answer" => "answer",
"exp_days" => "days",
"view" => "προβολή",
"post_own" => 'Δημοσίευση /επεξεργασία τα δικά του',
"post_all" => 'Δημοσίευση /επεξεργασία όλων',
"manager" => 'post /manager',

//settings.php - view settings.
"templFields_text" => "Σημασία των αριθμών: <br> 1: Πεδίο διεξαγωγής <br> 2: Πεδίο κατηγορίας συμβάντος <br> 3: Πεδίο περιγραφής <br> 4: Πρόσθετο πεδίο 1 (βλ. : Πρόσθετο πεδίο 2 (ανατρέξτε στην ενότητα Εκδηλώσεις) <br> 6: Στοιχεία ειδοποίησης μέσω ηλεκτρονικού ταχυδρομείου (μόνο αν έχει ζητηθεί ειδοποίηση) <br> 7: Ημερομηνία /ώρα προστέθηκε /τροποποιήθηκε και οι σχετικοί χρήστες 8: pdf, αρχεία εικόνας ή βίντεο ως υπερσυνδέσμους <br> <br> Η σειρά των αριθμών καθορίζει τη σειρά των εμφανιζόμενων πεδίων. ",
"evtTemplate_label" => "Πρότυπα συμβάντων",
"evtTemplate_text" => "Τα πεδία συμβάντων που θα εμφανιστούν στις γενικές προβολές ημερολογίου, στις επερχόμενες προβολές συμβάντων και στο πεδίο με τις λεπτομέρειες συμβάντος μπορούν να προσδιοριστούν με μια ακολουθία αριθμών. <br> Εάν οριστεί ένας αριθμός την ακολουθία, θα εμφανιστεί το αντίστοιχο πεδίο. ",
"evtTemplPublic" => "Public users",
"evtTemplLogged" => "Logged-in users",
"evtTemplGen" => "Γενική προβολή",
"evtTemplUpc" => "Επόμενη προβολή",
"evtTemplPop" => "Πλαίσιο με κίνηση",
"sortEvents_label" => "Sort events on times or category",
"sortEvents_text" => "In the various views events can be sorted on the following criteria:<br>• event times<br>• event category sequence number",
"yearStart_label" => "Έναρξη μήνα σε προβολή έτους",
"yearStart_text" => "Εάν έχει οριστεί ένας μήνας έναρξης (1 - 12), το ημερολόγιο θα εμφανίζεται στην προβολή Έτους πάντα με αυτόν τον μήνα και το έτος αυτού του πρώτου μήνα θα αλλάξει μόνο από την πρώτη ημέρα του ίδιου μήνα το επόμενο έτος. <br> Η τιμή 0 έχει ιδιαίτερη σημασία: ο μήνας έναρξης βασίζεται στην τρέχουσα ημερομηνία και θα πέσει στην πρώτη σειρά των μηνών. ",
"YvRowsColumns_label" => "Γραμμές και στήλες για προβολή σε προβολή έτους",
"YvRowsColumns_text" => "Αριθμός σειρών τεσσάρων μηνών για εμφάνιση στην προβολή έτους.<br>Προτεινόμενη επιλογή: 4, η οποία σας δίνει 16 μήνες για να μετακινηθείτε. <br> Αριθμός μηνών που θα εμφανίζονται σε κάθε σειρά σε προβολή έτους . <br> Συνιστώμενη επιλογή: 3 ή 4. ",
"MvWeeksToShow_label" => "Εβδομάδες για προβολή σε προβολή μήνα",
"MvWeeksToShow_text" => "Αριθμός εβδομάδων για προβολή σε προβολή μήνα.<br> Συνιστώμενη επιλογή: 10, η οποία σας δίνει 2,5 μήνες για να μετακινηθείτε. <br> Οι τιμές 0 και 1 έχουν ιδιαίτερη σημασία: <br> 0: εμφάνιση ακριβώς 1 μήνα - κενή ημέρα οδήγησης και επόμενες ημέρες <br> <br> 1: εμφάνιση ακριβώς 1 μήνα - εμφάνιση γεγονότων στις κύριες και τις τελευταίες ημέρες. ",
"XvWeeksToShow_label" => "Εβδομάδες για προβολή σε προβολή Matrix",
"XvWeeksToShow_text" => "Αριθμός εβδομάδων ημερολογίου για εμφάνιση στην προβολή Matrix.",
"GvWeeksToShow_label" => "Εβδομάδες για προβολή σε προβολή Gantt Chart",
"GvWeeksToShow_text" => "Αριθμός εβδομάδων ημερολογίου για εμφάνιση στην προβολή Gantt Chart.",
"workWeekDays_label" => "Εργάσιμες ημέρες",
"workWeekDays_text" => "Ημέρες χρωματισμένες ως εργάσιμες ημέρες στις προβολές ημερολογίου και για παράδειγμα να εμφανίζονται στις εβδομάδες στην προβολή Μήνα εργασίας και Εβδομάδα εργασίας <br> <br> Εισάγετε τον αριθμό κάθε εργάσιμης ημέρας <br> 12345: Δευτέρα - Παρασκευή <br> Οι μη καταχωρημένες ημέρες θεωρούνται ημέρες Σαββατοκύριακου. ",
"weekStart_label" => "Πρώτη ημέρα της εβδομάδας",
"weekStart_text" => "Εισάγετε τον αριθμό της ημέρας της πρώτης ημέρας της εβδομάδας.",
"lookBackAhead_label" => "Ημέρες για να κοιτάξουμε μπροστά",
"lookBackAhead_text" => "Αριθμός ημερών για να κοιτάξουμε μπροστά τα γεγονότα στην προβολή Προσεχείς εκδηλώσεις, η λίστα Todo και οι ροές RSS.",
"searchBackAhead_label" => "Default days to search back/ahead",
"searchBackAhead_text" => "When no dates are specified on the Search page, these are the default number of days to search back and to search ahead.",
"dwStartEndHour_label" => "Έναρξη και τέλος ώρας στην προβολή Ημέρα /Εβδομάδα",
"dwStartEndHour_text" => "Ώρες κατά τις οποίες ξεκινάει και τελειώνει μια κανονική ημέρα γεγονότων.Για παράδειγμα, ο καθορισμός αυτών των τιμών σε 6 και 18 θα αποφύγει τη σπατάλη χώρου στην προβολή Εβδομάδα /Ημέρα για την ήσυχη περίοδο μεταξύ των μεσάνυχτων και 6:00 και 18 : 00 και τα μεσάνυχτα. <br> Ο επιλογέας χρόνου, που χρησιμοποιείται για να εισέλθει σε μια ώρα, θα ξεκινήσει και θα τελειώσει στις ώρες αυτές. ",
"dwTimeSlot_label" => "Χρονική περίοδος προβολής ημέρας /εβδομάδας",
"dwTimeSlot_text" => "Αριθμός λεπτών για το χρονικό διάστημα στην προβολή Ημέρα /Εβδομάδα. <br> Αυτή η τιμή, μαζί με την ώρα έναρξης και την ώρα λήξης (δείτε παραπάνω), θα καθορίσει τον αριθμό των γραμμών στην προβολή ημέρας /εβδομάδας. " ,
"dwTsInterval" => "Χρονικό διάστημα",
"dwTsHeight" => "Ύψος",
"evtHeadX_label" => "Event layout in Month, Week and Day view",
"evtHeadX_text" => "Templates with placeholders of event fields that should be displayed. The following placeholders can be used:<br>#ts - start time<br>#tx - start and end time<br>#e - event title<br>#o - event owner<br>#v - venue<br>#lv - venue with label 'Venue:' in front<br>#c - category<br>#lc - category with label 'Category:' in front<br>#a - age (see note below)<br>#x1 - extra field 1<br>#lx1 - extra field 1 with label from Settings page in front<br>#x2 - extra field 2<br>#lx2 - extra field 2 with label from Settings page in front<br>#/ - new line<br>The fields are displayed in the specified order. Characters other than the placeholders will remain unchanged and will be part of the displayed event.<br>HTML-tags are allowed in the template. E.g. &lt;b&gt;#e&lt;/b&gt;.<br>The | character can be used to split the template in sections. If within a section all #-parameters result in an empty string, the whole section will be omitted.<br>Note: The age is shown if the event is part of a category with 'Repeat' set to 'every year' and the year of birth in parentheses is mentioned somewhere in either the event description field or in one of the extra fields.",
"monthView" => "Month view",
"wkdayView" => "Week/Day view",
"ownerTitle_label" => "Εμφάνιση του κατόχου της εκδήλωσης μπροστά από τον τίτλο του συμβάντος",
"ownerTitle_text" => "Στις διάφορες προβολές ημερολογίου, εμφανίζεται το όνομα του κατόχου της εκδήλωσης μπροστά από τον τίτλο της εκδήλωσης.",
"showSpanel_label" => "Side panel in calendar views",
"showSpanel_text" => "In the calendar views, right next to the main calendar page, a side panel with the following items can be shown:<br>• a mini calendar which can be used to look back or ahead without changing the date of the main calendar<br>• a decoration image corresponding to the current month<br>• an info area to post messages/announcements during specified periods.<br>Per item a comma-separated list of view numbers can be specified, for which the side panel should be shown.<br>Possible view numbers:<br>0: all views<br>1: year view<br>2: month view (7 days)<br>3: work month view<br>4: week view (7 days)<br>5: work week view<br>6: day view<br>7: upcoming events view<br>8: changes view<br>9: matrix view (categories)<br>10: matrix view (users)<br>11: gantt chart view.<br>If 'Today' is checked, the side panel will always use the date of today, otherwise it will follow the date selected for the main calendar.<br>See admin_guide.html for Side Panel details.",
"spMiniCal" => "Mini calendar",
"spImages" => "Images",
"spInfoArea" => "Info area",
"spToday" => "Today",
"topBarDate_label" => "Show current date on top bar",
"topBarDate_text" => "Enable/disable the display of the current date on the calendar top bar in the calendar views. If displayed, the current date can be clicked to reset the calendar to the current date.",
"showImgInMV_label" => "Εμφάνιση εικόνων σε προβολή μήνα",
"showImgInMV_text" => "Ενεργοποίηση /απενεργοποίηση της προβολής σε προβολή Μήνας των εικόνων μικρογραφίας που προστέθηκαν σε ένα από τα πεδία περιγραφής συμβάντων. Όταν είναι ενεργοποιημένη, οι μικρογραφίες θα εμφανίζονται στις κελιές ημέρας και όταν απενεργοποιηθούν, οι μικρογραφίες θα εμφανίζονται στο ποντίκι <br> Αντίθετα.",
"urls" => "Σύνδεσμοι URL",
"emails" => "σύνδεσμοι ηλεκτρονικού ταχυδρομείου",
"monthInDCell_label" => "Μήνας σε κάθε κελί ημέρας",
"monthInDCell_text" => "Προβολή για κάθε μέρα σε μήνα προβολή του ονόματος μήνα με 3 γράμματα",
"scrollDCell_label" => "Use scrollbar in day cells",
"scrollDCell_text" => "If in month view a day cell is too small, rather than increasing the day cell height, a vertical scrollbar will appear.",

//settings.php - date/time settings.
"dateFormat_label" => "Μορφή ημερομηνίας συμβάντος (dd mm εεεε)",
"dateFormat_text" => "Η συμβολοσειρά κειμένου που ορίζει τη μορφή των ημερομηνιών συμβάντων στις προβολές ημερολογίου και τα πεδία εισαγωγής. <br> Πιθανές χαρακτήρες: y = έτος, m = μήνας και d = ημέρα <br> Μπορεί να χρησιμοποιηθεί μη αλφαριθμητικός χαρακτήρας ως διαχωριστικό και θα αντιγραφεί κυριολεκτικά. <br> Παραδείγματα: <br> ymd: 2024-10-31 <br> mdy: 10.31.2024 <br> d /m /y: 31/10/2024 ",
"dateFormat_expl" => "π.χ. y.m.d: 2024.10.31",
"MdFormat_label" => "Μορφή ημερομηνίας (μήνας dd)",
"MdFormat_text" => "Σειρά κειμένου που ορίζει τη μορφή των ημερομηνιών που αποτελείται από μήνα και ημέρα. <br> Πιθανές χαρακτήρες: M = μήνας σε κείμενο, d = ημέρα σε ψηφία <br> <br> Μη αλφαριθμητικός χαρακτήρας μπορεί να χρησιμοποιηθεί ως διαχωριστής και θα αντιγραφεί κυριολεκτικά. <br> Παραδείγματα: d d: 12 Απριλίου <br> M, d: 14 Ιουλίου.",
"MdFormat_expl" => "π.χ., M, d: Ιούλιος, 14",
"MdyFormat_label" => "Μορφή ημερομηνίας (dd μήνας εεεε)",
"MdyFormat_text" => "Μορφή κειμένου που ορίζει τη μορφή ημερομηνιών που αποτελείται από ημέρα, μήνα και έτος.<br> Πιθανές χαρακτήρες: d = ημέρα σε ψηφία, M = μήνα σε κείμενο, y = έτος σε ψηφία. ο αλφαριθμητικός χαρακτήρας μπορεί να χρησιμοποιηθεί ως διαχωριστής και θα αντιγραφεί κυριολεκτικά. <br> Παραδείγματα: <br> d M y: 12 Απριλίου 2024 <br> M d, y: 8 Ιουλίου 2024.",
"MdyFormat_expl" => "π.χ. M d, y: 8 Ιουλίου 2024",
"MyFormat_label" => "Μορφή ημερομηνίας (μήνας εεεε)",
"MyFormat_text" => "Σειρά κειμένου που ορίζει τη μορφή ημερομηνιών που αποτελείται από μήνα και έτος.<br> Πιθανές χαρακτήρες: M = μήνας σε κείμενο, y = έτος σε ψηφία <br> <br> Μη αλφαριθμητικός χαρακτήρας μπορεί να χρησιμοποιηθεί ως διαχωριστής και θα αντιγραφεί κυριολεκτικά. <br> Παραδείγματα: <br> Μάρτιος: Απρίλιος 2024 <br> y - M: 2024 - Ιούλιος ",
"MyFormat_expl" => "π.χ. MY: Απρίλιος 2024",
"DMdFormat_label" => "Μορφή ημερομηνίας (εβδομάδα dd μηνός)",
"DMdFormat_text" => "Μορφή κειμένου που ορίζει τη μορφή των ημερομηνιών που αποτελείται από την ημέρα της εβδομάδας, την ημέρα και τον μήνα.<br> Πιθανές χαρακτήρες: WD = ημέρα της εβδομάδας σε κείμενο, M = μήνα σε κείμενο, αλφαριθμητικός χαρακτήρας μπορεί να χρησιμοποιηθεί ως διαχωριστικό και θα αντιγραφεί κυριολεκτικά. <br> Παραδείγματα: <br> WD d M: Παρασκευή 12 Απριλίου <br> WD, M d: Δευτέρα 14 Ιουλίου.",
"DMdFormat_expl" => "π.χ. WD - M d: Κυριακή - 6 Απριλίου",
"DMdyFormat_label" => "Μορφή ημερομηνίας (εβδομάδα dd μήνας εεεε)",
"DMdyFormat_text" => "Σειρά κειμένου που ορίζει τη μορφή των ημερομηνιών που αποτελείται από την ημέρα της εβδομάδας, την ημέρα, το μήνα και το έτος.<br> Πιθανά χαρακτήρες: WD = ημέρα της εβδομάδας σε κείμενο, M = μήνα σε κείμενο, d = ημέρα σε ψηφία, y = έτος σε ψηφία <br> <br> Μη αλφαριθμητικός χαρακτήρας μπορεί να χρησιμοποιηθεί ως διαχωριστής και θα αντιγραφεί κυριολεκτικά. <br> Παραδείγματα: <br> WD d M y: Παρασκευή 13 Απρίλιος 2024 <br> WD - M d, y: Δευτέρα - 16 Ιουλίου 2024 ",
"DMdyFormat_expl" => "π.χ. WD, M d, y: Δευτέρα 16 Ιουλίου 2024",
"timeFormat_label" => "Μορφή ώρας (hh mm)",
"timeFormat_text" => "Σειρά κειμένου που καθορίζει τη μορφή των χρόνων συμβάντων στις προβολές ημερολογίου και τα πεδία εισαγωγής.<br> Πιθανά χαρακτήρες: h = ώρες, H = ώρες με αρχικά μηδενικά, m = λεπτά, a = ), A = AM /PM (προαιρετικό). <br> Ο μη αλφαριθμητικός χαρακτήρας μπορεί να χρησιμοποιηθεί ως διαχωριστής και θα αντιγραφεί κυριολεκτικά. <br> Παραδείγματα: <br> h: m: 18:35 <br> hm a: 6.35 μ.μ. H: mA: 06: 35 μ.μ. ",
"timeFormat_expl" => "π.χ., h: m: 22:35 και h: mA: 10:35 μ.μ.",
"weekNumber_label" => "Εμφάνιση αριθμών εβδομάδων",
"weekNumber_text" => "Εμφανίζονται αριθμοί εβδομάδων στις σχετικές προβολές μπορούν να ενεργοποιηθούν /απενεργοποιηθούν",
"time_format_us" => "12ωρο AM /PM",
"time_format_eu" => "24ωρο",
"Κυριακή" => "Κυριακή",
"monday" => "Δευτέρα",
"time_zones" => "ΖΩΝΕΣ ΩΡΑΣ",
"dd_mm_yyyy" => "dd-mm-yyyy",
"mm_dd_yyyy" => "mm-dd-yyyy",
"yyyy_mm_dd" => "yyyy_mm_dd",

//settings.php - file uploads settings.
"maxUplSize_label" => "Μέγιστο μέγεθος μεταφόρτωσης αρχείου",
"maxUplSize_text" => "Μέγιστο επιτρεπόμενο μέγεθος αρχείου όταν οι χρήστες ανεβάζουν αρχεία συνημμένων ή μικρογραφιών.<br> Σημείωση: Οι περισσότερες εγκαταστάσεις PHP έχουν αυτή τη μέγιστη τιμή στα 2 MB (αρχείο php_ini) ",
"attTypes_label" => "Τύποι αρχείων συνημμένων",
"attTypes_text" => "Λίστα διαχωριζόμενη με κόμματα με έγκυρους τύπους αρχείων συνημμένων που μπορούν να μεταφορτωθούν (π.χ. \ '. pdf, .jpg, .gif, .png, .mp4, .avi ')",
"tnlTypes_label" => "Τύποι αρχείων μικρογραφιών",
"tnlTypes_text" => "Διαχωρισμένη με κόμματα λίστα με έγκυρους τύπους αρχείων μικρογραφιών που μπορούν να μεταφορτωθούν (π.χ. \ '. jpg, .jpeg, .gif, .png ')",
"tnlMaxSize_label" => "Μικρογραφία - μέγιστο μέγεθος",
"tnlMaxSize_text" => "Μέγιστο μέγεθος εικόνας μικρογραφίας Εάν οι χρήστες ανεβάσουν μεγαλύτερες μικρογραφίες, οι μικρογραφίες θα αλλάζουν αυτόματα στο μέγιστο μέγεθος.<br>Σημείωση: Οι μεγάλες μικρογραφίες θα τεντώσουν την ημέρα των κυττάρων στην προβολή Μήνες, πράγμα που μπορεί να οδηγήσει σε ανεπιθύμητα αποτελέσματα . ",
"tnlDelDays_label" => "Περιθώριο διαγραφής μικρογραφιών",
"tnlDelDays_text" => "Εάν χρησιμοποιείται μια μικρογραφία από τον αριθμό των ημερών πριν, δεν μπορεί να διαγραφεί.<br>Η τιμή 0 ημερών σημαίνει ότι η μικρογραφία δεν μπορεί να διαγραφεί. ",
"days" => "ημέρες",
"mbytes" => "ΜΒ",
"wxhinpx" => "W x H σε εικονοστοιχεία",

//settings.php - reminders settings.
"services_label" => "Υπηρεσίες μηνυμάτων",
"services_text" => "Οι υπηρεσίες που είναι διαθέσιμες για τις υπενθυμίσεις συμβάντων που έχουν αποσταλεί Εάν μια υπηρεσία δεν έχει επιλεγεί, η αντίστοιχη ενότητα στο παράθυρο συμβάντος θα καταργηθεί.Αν δεν έχει επιλεγεί καμία υπηρεσία, δεν θα σταλούν υπενθυμίσεις συμβάντων",
"msgLogging_label" => "Notification message logging",
"msgLogging_text" => "When checked, the notification messages sent are logged in the messages.log file. The 'weeks' field specifies how long the logged messages should be kept",
"smsCarrier_label" => "Πρότυπο φορέα SMS",
"smsCarrier_text" => "Το πρότυπο φορέα SMS χρησιμοποιείται για την κατάρτιση της διεύθυνσης ηλεκτρονικού ταχυδρομείου πύλης SMS: ppp#sss@carrier, όπου ...<br>•  ppp: προαιρετική συμβολοσειρά κειμένου που θα προστεθεί πριν από τον αριθμό τηλεφώνου.<br>• #: placeholder για τον αριθμό του κινητού τηλεφώνου του παραλήπτη (το ημερολόγιο θα αντικαταστήσει το # με τον αριθμό τηλεφώνου) <br>• sss: προαιρετική συμβολοσειρά κειμένου που θα εισαχθεί μετά τον αριθμό τηλεφώνου, π.χ. όνομα χρήστη και κωδικό πρόσβασης, φορείς εκμετάλλευσης <br> • @: διαχωριστικό χαρακτήρα <br> • μεταφορέας: διεύθυνση μεταφορέα (π.χ. mail2sms.com) <br> Παραδείγματα προτύπων:#@xmobile.com, 0#@carr2.int, #myunmypw@sms.gway.net.",
"smsCountry_label" => "Κωδικός χώρας SMS",
"smsCountry_text" => "Εάν η πύλη SMS βρίσκεται σε διαφορετική χώρα από το ημερολόγιο, τότε πρέπει να προσδιοριστεί ο κωδικός χώρας της χώρας όπου χρησιμοποιείται το ημερολόγιο. <br> Επιλέξτε εάν η \ '+ ' ή \ 00 \ 'απαιτείται πρόθεμα. ",
"smsSubject_label" => "Πρότυπο μηνύματος SMS",
"smsSubject_text" => "Αν οριστεί, το κείμενο σε αυτό το πρότυπο θα αντιγραφεί στο πεδίο των μηνυμάτων SMS που αποστέλλονται στον μεταφορέα. Το κείμενο μπορεί να περιέχει τον χαρακτήρα #, ο οποίος θα αντικατασταθεί από τον αριθμό τηλεφώνου του ημερολογίου ή τον ιδιοκτήτη συμβάντος (ανάλογα με την παραπάνω ρύθμιση). <br>Παράδειγμα: 'FROMPHONENUMBER = #'.",
"smsAddLink_label" => "Προσθήκη αναφοράς σύνδεσης συμβάντος σε SMS",
"smsAddLink_text" => "Όταν επιλεγεί, θα προστεθεί ένας σύνδεσμος προς την αναφορά συμβάντος σε κάθε SMS, ανοίγοντας αυτόν τον σύνδεσμο στο κινητό τηλέφωνο, οι παραλήπτες θα μπορούν να δουν τις λεπτομέρειες του συμβάντος.",
"maxLenSms_label" => "Μέγιστο μήκος μηνύματος SMS",
"maxLenSms_text" => "Τα μηνύματα SMS αποστέλλονται με κωδικοποίηση χαρακτήρων utf-8. Τα μηνύματα έως και 70 χαρακτήρων θα έχουν ως αποτέλεσμα ένα μήνυμα SMS, τα μηνύματα> 70 χαρακτήρες, με πολλούς χαρακτήρες Unicode.",
"calPhone_label" => "Αριθμός τηλεφώνου ημερολογίου",
"calPhone_text" => "Ο αριθμός τηλεφώνου που χρησιμοποιείται ως αναγνωριστικό αποστολέα κατά την αποστολή μηνυμάτων ειδοποίησης SMS. <br>Μορφή: δωρεάν, 20 ψηφία κατ 'ανώτατο όριο (ορισμένες χώρες απαιτούν έναν αριθμό τηλεφώνου, άλλες χώρες δεχθούν επίσης αλφαβητικούς χαρακτήρες). δεν υπάρχει υπηρεσία SMS ή εάν δεν έχει οριστεί πρότυπο μηνύματος SMS, αυτό το πεδίο μπορεί να είναι κενό. ",
"notSenderEml_label" => "Add 'Reply to' field to email",
"notSenderEml_text" => "When selected, notification emails will contain a 'Reply to' field with the email address of the event owner, to which the recipient can reply.",
"notSenderSms_label" => "Αποστολέας μηνυμάτων SMS",
"notSenderSms_text" => "Όταν το ημερολόγιο στέλνει SMS υπενθύμιση, το αναγνωριστικό αποστολέα του μηνύματος SMS μπορεί να είναι είτε ο αριθμός τηλεφώνου του ημερολογίου είτε ο αριθμός τηλεφώνου του χρήστη που δημιούργησε το συμβάν. επιλέξει και ο λογαριασμός χρήστη δεν έχει οριστεί αριθμός τηλεφώνου, θα ληφθεί ο αριθμός τηλεφώνου του ημερολογίου. <br> Στην περίπτωση του αριθμού τηλεφώνου χρήστη, ο δέκτης μπορεί να απαντήσει στο μήνυμα. ",
"defRecips_label" => "Προεπιλεγμένη λίστα παραληπτών",
"defRecips_text" => "Εάν έχει οριστεί, αυτή θα είναι η προεπιλεγμένη λίστα παραληπτών για ειδοποιήσεις μηνυμάτων ηλεκτρονικού ταχυδρομείου ή /και SMS στο παράθυρο συμβάντος.Αν το πεδίο αυτό παραμείνει κενό, ο προεπιλεγμένος παραλήπτης θα είναι ο κάτοχος της εκδήλωσης.",
"maxEmlCc_label" => "Max. no. of recipients per email",
"maxEmlCc_text" => "Normally ISPs allow a maximum number of recipients per email. When sending email or SMS reminders, if the number of recipients is greater than the number specified here, the email will be split in multiple emails, each with the specified maximum number of recipients.",
"emlFootnote_label" => "Reminder email footnote",
"emlFootnote_text" => "Free-format text that will be added as a paragraph to the end of reminder email messages. HTML tags are allowed in the text.",
"mailServer_label" => "διακομιστής αλληλογραφίας",
"mailServer_text" => "Το ταχυδρομείο PHP είναι κατάλληλο για μηνύματα που δεν έχουν ταυτοποιηθεί, σε μικρούς αριθμούς.Για μεγαλύτερο αριθμό μηνυμάτων ή όταν απαιτείται έλεγχος ταυτότητας, θα πρέπει να χρησιμοποιείται αλληλογραφία SMTP.<br>Η χρήση αλληλογραφίας SMTP απαιτεί διακομιστή αλληλογραφίας SMTP. για τον εξυπηρετητή SMTP πρέπει να διευκρινίζεται στη συνέχεια. ",
"smtpServer_label" => "Όνομα διακομιστή SMTP",
"smtpServer_text" => "Αν έχει επιλεγεί email SMTP, πρέπει να ορίσετε εδώ το όνομα του διακομιστή SMTP, για παράδειγμα το gmail SMTP server: smtp.gmail.com",
"smtpPort_label" => "Αριθμός θύρας SMTP",
"smtpPort_text" => "Εάν έχει επιλεγεί email SMTP, πρέπει να ορίσετε εδώ τον αριθμό θύρας SMTP, για παράδειγμα 25, 465 ή 587. Το Gmail χρησιμοποιεί για παράδειγμα τον αριθμό θύρας 465.",
"smtpSsl_label" => "SSL (Secure Sockets Layer)",
"smtpSsl_text" => "Εάν έχει επιλεγεί αλληλογραφία SMTP, επιλέξτε εδώ αν θα πρέπει να ενεργοποιηθεί το επίπεδο ασφαλών υποδοχών (SSL). Για το gmail: enabled",
"smtpAuth_label" => "Έλεγχος ταυτότητας SMTP",
"smtpAuth_text" => "Εάν έχει επιλεγεί έλεγχος ταυτότητας SMTP, το όνομα χρήστη και ο κωδικός πρόσβασης που καθορίζονται παρακάτω θα χρησιμοποιηθούν για τον έλεγχο ταυτότητας του μηνύματος SMTP.<br>Για παράδειγμα, το όνομα χρήστη είναι το τμήμα της διεύθυνσης ηλεκτρονικού ταχυδρομείου σας πριν από το @.",
"tlgToken_label" => "Telegram token",
"tlgToken_text" => "Telegram token in the following format: &lt;bot ID&gt;:&lt;bot hash&gt;. For details see installation_guide.html, section Event Notification Messages.",
"cc_prefix" => "Ο κωδικός χώρας ξεκινά με το πρόθεμα + ή 00",
"weeks" => "Weeks",
"general" => "Γενικά",
"php_mail" => "Ταχυδρομείο PHP",
"smtp_mail" => "Ταχυδρομείο SMTP (συμπληρώστε τα παρακάτω πεδία)",

//settings.php - periodic function settings.
"cronHost_label" => "Κεντρικός υπολογιστής εργασίας Cron",
"cronHost_text" => "Καθορίστε πού φιλοξενείται η εργασία cron η οποία εκκινεί περιοδικά τη δέσμη ενεργειών 'lcalcron.php '.<br>• τοπική: εργασία cron εκτελείται στον ίδιο διακομιστή <br>• απομακρυσμένη: η εργασία cron εκτελείται σε ένα απομακρυσμένος διακομιστής ή lcalcron.php εκκινείται με μη αυτόματο τρόπο (δοκιμή) <br> <br> IP διεύθυνση: η εργασία cron εκτελείται σε απομακρυσμένο διακομιστή με την καθορισμένη διεύθυνση IP. ",
"cronSummary_label" => "Περίληψη θέσης εργασίας admin cron",
"cronSummary_text" => "Στείλτε μια σύνοψη εργασιών cron στον διαχειριστή του ημερολογίου. <br> Η ενεργοποίηση είναι χρήσιμη μόνο αν έχει ενεργοποιηθεί μια εργασία cron για το ημερολόγιο.",
"chgSummary_text" => "Αριθμός ημερών για την επισκόπηση της περίληψης των αλλαγών του ημερολογίου. <br> Αν ο αριθμός των ημερών έχει οριστεί στο 0 ή εάν δεν λειτουργεί καμία εργασία cron, δεν θα σταλεί σύνοψη των αλλαγών.",
"icsExport_label" => "Ημερήσια εξαγωγή συμβάντων iCal",
"icsExport_text" => "Αν είναι ενεργοποιημένη: Όλα τα συμβάντα στο εύρος ημερομηνιών -1 εβδομάδα έως +1 έτος θα εξαχθούν σε μορφή iCalendar σε αρχείο .ics στο φάκελο 'files '. <br> Το όνομα του αρχείου θα είναι το όνομα του ημερολογίου με κενά αντικαθίσταται από παύλες, τα παλιά αρχεία θα αντικατασταθούν από νέα αρχεία. ",
"eventExp_label" => "Ημέρες λήξης συμβάντος",
"eventExp_text" => "Αριθμός ημερών μετά την ημερομηνία λήξης του συμβάντος όταν λήγει το συμβάν και θα διαγραφεί αυτόματα.<br>Εάν 0 ή εάν δεν εκτελείται εργασία cron, δεν θα διαγραφούν αυτόματα τα συμβάντα.",
"maxNoLogin_label" => "Μέγιστος αριθμός ημερών που δεν έχετε συνδεθεί",
"maxNoLogin_text" => "Αν ένας λογαριασμός δεν έχει συνδεθεί εδώ και πολλές ημέρες, θα διαγραφεί αυτόματα.<br>Εάν αυτή η τιμή έχει οριστεί σε 0, οι λογαριασμοί χρηστών δεν θα διαγραφούν ποτέ.",
"local" => "τοπικό",
"remote" => "απομακρυσμένη",
"ip_address" => "διεύθυνση IP",

//settings.php - mini calendar /sidebar settings.
"popFieldsSbar_label" => "Πεδία συμβάντων - πλαίσιο",
"popFieldsSbar_text" => "Τα πεδία συμβάντων που εμφανίζονται σε μια επικάλυψη όταν ο χρήστης κινείται σε ένα συμβάν στην αυτόνομη πλευρική γραμμή μπορεί να καθοριστεί με μια ακολουθία αριθμών.<br>Εάν δεν καθορίζονται καθόλου πεδία, θα εμφανιστεί το πλαίσιο Hover.",
"showLinkInSB_label" => "Εμφάνιση συνδέσμων στην πλαϊνή γραμμή",
"showLinkInSB_text" => "Εμφανίζει τις διευθύνσεις URL από την περιγραφή συμβάντος ως υπερσύνδεσμος στην επερχόμενη γραμμή επερχόμενων συμβάντων",
"sideBarDays_label" => "Ημέρες για να κοιτάξουμε μπροστά στην πλαϊνή μπάρα",
"sideBarDays_text" => "Αριθμός ημερών για να κοιτάξουμε μπροστά τα συμβάντα στην πλαϊνή μπάρα.",

//login.php
"log_log_in" => "Σύνδεση",
"log_remember_me" => "Θυμήσου με",
"log_register" => "Εγγραφή νέου χρήστη",
"log_change_my_data" => "Τροποποίηση των στοιχείων μου",
"log_save" => "Αλλαγή",
"log_done" => "Done",
"log_un_or_em" => "Όνομα Χρήστη ή Διεύθυνση Ηλεκτρονικού Ταχυδρομείου",
"log_un" => "Όνομα Χρήστη",
"log_em" => "Διεύθυνση Ηλεκτρονικού Ταχυδρομείου",
"log_ph" => "Mobile phone number",
"log_tg" => "Telegram chat ID",
"log_answer" => "Your answer",
"log_pw" => "Κωδικός",
"log_expir_date" => "Account expiration date",
"log_account_expired" => "This account has expired",
"log_new_un" => "Νέο Όνομα Χρήστη",
"log_new_em" => "Νέα Διεύθυνση Ηλεκτρονικού Ταχυδρομείου",
"log_new_pw" => "Νέος Κωδικός",
"log_con_pw" => "Επιβεβαίωση κωδικού",
"log_pw_msg" => "Εδώ είναι οι λεπτομέρειες σύνδεσης σας, για το ημερολόγιο",
"log_pw_subject" => "Ο κωδικός σας",
"log_npw_subject" => "Ο νέος σας κωδικός",
"log_npw_sent" => "Ο νέος σας κωδικός σας έχει αποσταλεί",
"log_registered" => "Η εγγραφή ολοκληρώθηκε - Ο κωδικός σας έχει αποσταλεί με ηλεκτρονικό ταχυδρομείο",
"log_em_problem_not_sent" => "Πρόβλημα ηλεκτρονικού ταχυδρομείου - ο κωδικός πρόσβασής σας δεν ήταν δυνατή",
"log_em_problem_not_noti" => "πρόβλημα ηλεκτρονικού ταχυδρομείου - δεν θα μπορούσε να ειδοποιήσει τον διαχειριστή",
"log_un_exists" => "Το όνομα χρήστη υπάρχει ήδη",
"log_em_exists" => "Η διεύθυνση ηλεκτρονικού ταχυδρομείου υπάρχει ήδη",
"log_un_invalid" => "Εσφαλμένο όνομα χρήστη (ελάχιστο μήκος 2 χαρακτήρες, γράμματα, αριθμοί και _-.) ",
"log_em_invalid" => "Η διεύθυνση ηλεκτρονικού ταχυδρομείου είναι εσφαλμένη",
"log_ph_invalid" => "Μη έγκυρος αριθμός κινητού τηλεφώνου",
"log_tg_invalid" => "Invalid Telegram chat ID",
"log_sm_nr_required" => "SMS: mobile phone number required",
"log_tg_id_required" => "Telegram: chat ID required",
"log_sra_wrong" => "Incorrect answer to the question",
"log_sra_wrong_4x" => "You have answered incorrectly 4 times - try again in 30 minutes",
"log_un_em_invalid" => "Το όνομα χρήστη/διεύθυνση ηλεκτρονικού ταχυδρομείου είναι εσφαλμένα",
"log_un_em_pw_invalid" => "Το όνομα χρήστη/διεύθυνση ηλεκτρονικού ταχυδρομείου ή ο κωδικός είναι εσφαλμένα",
"log_pw_error" => "Οι κωδικοί πρόσβασης δεν συμφωνούν",
"log_no_un_em" => "Παρακαλώ εισάγετε όνομα χρήστη/διεύθυνση ηλεκτρονικού ταχυδρομείου",
"log_no_un" => "Παρακαλώ εισάγετε το όνομα χρήστη",
"log_no_em" => "Παρακαλώ εισάγετε τη διεύθυνση ηλεκτρονικού ταχυδρομείου σας",
"log_no_pw" => "Παρακαλώ εισάγετε τον κωδικό σας",
"log_no_rights" => "Η αίτηση σύνδεσης απορρίφθηκε: Δεν έχετε δικαίωμα προβολής - Επικοινωνήστε με το διαχειριστή του ημερολογίου",
"log_send_new_pw" => "Αποστολή νέου κωδικού",
"log_new_un_exists" => "Το νέο όνομα χρήστη υπάρχει ήδη",
"log_new_em_exists" => "Η νέα διεύθυνση ηλεκτρονικού ταχυδρομείου υπάρχει ήδη",
"log_ui_language" => "Γλώσσα του γραφικού περιβάλλοντος",
"log_new_reg" => "Εγγραφή νέου χρήστη",
"log_date_time" => "Ημερομηνία /ώρα",
"log_time_out" => "Λήξη χρόνου",

//categories.php
"cat_list" => "Κατάλογος κατηγοριών",
"cat_edit" => "Επεξεργασία",
"cat_delete" => "Διαγραφή",
"cat_add_new" => "Προσθήκη νέας κατηγορίας",
"cat_add" => "Προσθήκη",
"cat_edit_cat" => "Επεξεργασία κατηγορίας",
"cat_sort" => "Ταξινόμηση με όνομα",
"cat_cat_name" => "Όνομα κατηγορίας",
"cat_symbol" => "Σύμβολο",
"cat_symbol_repms" => "Σύμβολο κατηγορίας (αντικαθιστά το minisquare)",
"cat_symbol_eg" => "π.χ., Α, Χ, ♥, ⛛",
"cat_matrix_url_link" => "Σύνδεσμος URL (εμφανίζεται στην προβολή μήτρας)",
"cat_seq_in_menu" => "Ακολουθία στο μενού",
"cat_cat_color" => "Χρώμα κατηγορίας",
"cat_text" => "Κείμενο",
"cat_background" => "Ιστορικό",
"cat_select_color" => "Επιλογή χρώματος",
"cat_subcats" => "Υπο-<br>κατηγορίες",
"cat_subcats_opt" => "Αριθμός uποκατηγορίες (προαιρετικά)",
"cat_copy_from" => "Copy from",
"cat_eml_changes_to" => "Send event changes to",
"cat_url" => "URL",
"cat_name" => "Όνομα",
"cat_subcat_note" => "Note that the currently existing subcategories may already be used for events",
"cat_save" => "Αποθήκευση",
"cat_added" => "Κατηγορία προστέθηκε",
"cat_updated" => "Κατηγορία ενημερώθηκε",
"cat_deleted" => "Κατηγορία Διαγράφεται",
"cat_not_added" => "Δεν έχει προστεθεί η κατηγορία",
"cat_not_updated" => "Η κατηγορία δεν ενημερώθηκε",
"cat_not_deleted" => "Η κατηγορία δεν διαγράφηκε",
"cat_nr" => "#",
"cat_repeat" => "Επανάληψη",
"cat_every_day" => "κάθε μέρα",
"cat_every_week" => "κάθε εβδομάδα",
"cat_every_month" => "κάθε μήνα",
"cat_every_year" => "κάθε χρόνο",
"cat_overlap" => "Επικάλυψη <br> επιτρέπεται <br>(χάσμα)",
"cat_need_approval" => "Εκδηλώσεις χρειάζονται <br>έγκριση",
"cat_no_overlap" => "Δεν επιτρέπεται επικάλυψη",
"cat_same_category" => "ίδια κατηγορία",
"cat_all_categories" => "όλες οι κατηγορίες",
"cat_gap" => "χάσμα",
"cat_ol_error_text" => "Μήνυμα σφάλματος, αν υπάρχει επικάλυψη",
"cat_no_ol_note" => "Σημειώστε ότι τα ήδη υπάρχοντα συμβάντα δεν έχουν ελεγχθεί και συνεπώς μπορεί να αλληλεπικαλύπτονται",
"cat_ol_error_msg" => "επικάλυψη συμβάντος - επιλογή άλλης ώρας",
"cat_no_ol_error_msg" => "Λείπει το μήνυμα σφάλματος επικάλυψης",
"cat_duration" => "Γεγονός <br>! = διάρκεια σταθερό",
"cat_default" => "προεπιλογή (χωρίς τελική ώρα)",
"cat_fixed" => "σταθερό",
"cat_event_duration" => "Διάρκεια συμβάντος",
"cat_olgap_invalid" => "Μη έγκυρο κενό υπερκάλυψης",
"cat_duration_invalid" => "Μη έγκυρη διάρκεια εκδήλωσης",
"cat_no_url_name" => "Λείπει το όνομα συνδέσμου URL",
"cat_invalid_url" => "Μη έγκυρος σύνδεσμος URL",
"cat_day_color" => "Χρώμα ημέρας",
"cat_day_color1" => "Χρώμα ημέρας (έτος /μήτρα)",
"cat_day_color2" => "Χρώμα ημέρας (μήνα /εβδομάδα /ημέρα)",
"cat_approve" => "Τα γεγονότα χρειάζονται έγκριση",
"cat_check_mark" => "Έλεγχος",
"cat_not_list" => "Notify<br>list",
"cat_label" => "ετικέτα",
"cat_mark" => "σημάδι",
"cat_name_missing" => "Λείπει το όνομα της κατηγορίας",
"cat_mark_label_missing" => "Δεν υπάρχει σήμα ελέγχου /ετικέτα",

//users.php
"usr_list_of_users" => "Λίστα χρηστών",
"usr_name" => "Όνομα χρήστη",
"usr_email" => "Ηλεκτρονικό ταχυδρομείο",
"usr_phone" => "Αριθμός κινητού τηλεφώνου",
"usr_phone_br" => "Αριθμός κινητού τηλεφώνου",
"usr_tg_id" => "Telegram chat ID",
"usr_tg_id_br" => "Telegram<br>chat ID",
"usr_not_via" => "Notify via",
"usr_not_via_br" => "Notify<br>via",
"usr_language" => "Γλώσσα",
"usr_ui_language" => "Γλώσσα διεπαφής χρήστη",
"usr_group" => "Ομάδα",
"usr_password" => "Κωδικός πρόσβασης",
"usr_expir_date" => "Account expiration date",
"usr_select_exp_date" => "Select expiration date",
"usr_blank_none" => "blank: no expiration",
"usr_expires" => "Expires",
"usr_edit_user" => "Επεξεργασία προφίλ χρήστη",
"usr_add" => "Προσθήκη χρήστη",
"usr_edit" => "Επεξεργασία",
"usr_delete" => "Διαγραφή",
"usr_login_0" => "Πρώτη σύνδεση",
"usr_login_1" => "Τελευταία σύνδεση",
"usr_login_cnt" => "Σύνδεση",
"usr_add_profile" => "Προσθήκη προφίλ",
"usr_upd_profile" => "Ενημέρωση προφίλ",
"usr_if_changing_pw" => "Μόνο αν αλλάξετε τον κωδικό πρόσβασης",
"usr_pw_not_updated" => "Ο κωδικός πρόσβασης δεν ενημερώθηκε",
"usr_added" => "Προστέθηκε χρήστης",
"usr_updated" => "Το προφίλ χρήστη ενημερώθηκε",
"usr_deleted" => "Ο χρήστης διαγράφηκε",
"usr_not_deleted" => "Ο χρήστης δεν διαγράφηκε",
"usr_cred_required" => "Απαιτείται η χρήση ονόματος χρήστη, ηλεκτρονικού ταχυδρομείου και κωδικού πρόσβασης",
"usr_name_exists" => "Το όνομα χρήστη υπάρχει ήδη",
"usr_email_exists" => "Η διεύθυνση ηλεκτρονικού ταχυδρομείου υπάρχει ήδη",
"usr_un_invalid" => "Μη έγκυρο όνομα χρήστη (ελάχιστο μήκος 2: A-Z, a-z, 0-9 και _-.)",
"usr_em_invalid" => "Μη έγκυρη διεύθυνση ηλεκτρονικού ταχυδρομείου",
"usr_ph_invalid" => "Μη έγκυρος αριθμός κινητού τηλεφώνου",
"usr_tg_invalid" => "Invalid Telegram chat ID",
"usr_xd_invalid" => "Invalid account expiration date",
"usr_cant_delete_yourself" => "Δεν μπορείτε να διαγράψετε τον εαυτό σας",
"usr_go_to_groups" => "Μεταβείτε στις ομάδες",
"usr_all_cats" => "All Categories",
"usr_select" => "Select",
"usr_transfer" => "Transfer",
"usr_transfer_evts" => "Transfer Events",
"usr_transfer_ownership" => "Transfer ownership of events",
"usr_cur_owner" => "Current owner",
"usr_new_owner" => "New owner",
"usr_event_cat" => "Event category",
"usr_sdate_between" => "Start date between",
"usr_cdate_between" => "Creation date between",
"usr_select_start_date" => "Select start date",
"usr_select_end_date" => "Select end date",
"usr_blank_no_limit" => "Blank date: no limit",
"usr_no_undone" => "CAUTION, THIS TRANSACTION CANNOT BE UNDONE",
"usr_invalid_sdata" => "Invalid start date",
"usr_invalid_cdata" => "Invalid creation date",
"usr_edate_lt_sdate" => "End date before start date",
"usr_no_new_owner" => "New owner not specified",
"usr_evts_transferred" => "Done. Events transferred",

//groups.php
"grp_list_of_groups" => "Λίστα ομάδων χρηστών",
"grp_name" => "Όνομα ομάδας",
"grp_priv" => "Δικαιώματα χρήστη",
"grp_categories" => "Κατηγορίες συμβάντων",
"grp_all_cats" => "Όλες οι κατηγορίες",
"grp_rep_events" => "Επαναλαμβανόμενες εκδηλώσεις",
"grp_m-d_events" => "Γεγονότα πολλαπλών ημερών",
"grp_priv_events" => "Ιδιωτικά γεγονότα",
"grp_upload_files" => "Ανεβάστε τα αρχεία",
"grp_tnail_privs" => "Προνόμια μικρογραφίας",
"grp_priv0" => "Δεν υπάρχει πρόσβαση",
"grp_priv1" => "Προβολή ημερολογίου",
"grp_priv2" => "Δημοσίευση /επεξεργασία προσωπικών εκδηλώσεων",
"grp_priv3" => "Δημοσίευση /επεξεργασία όλων των συμβάντων",
"grp_priv4" => "Δημοσίευση /επεξεργασία + διαχειριστής",
"grp_priv9" => "Διαχειριστής",
"grp_may_post_revents" => "Μπορεί να δημοσιεύσει επαναλαμβανόμενα συμβάντα",
"grp_may_post_mevents" => "Μπορεί να δημοσιεύσει συμβάντα πολλαπλών ημερών",
"grp_may_post_pevents" => "Μπορεί να δημοσιεύσει ιδιωτικά συμβάντα",
"grp_may_upload_files" => "Μπορεί να φορτώσει αρχεία",
"grp_tn_privs" => "Προνόμια Thumbnails",
"grp_tn_privs00" => "καμία",
"grp_tn_privs11" => "προβολή όλων",
"grp_tn_privs20" => "διαχείριση δικών σας",
"grp_tn_privs21" => "m. δική /v. όλα",
"grp_tn_privs22" => "διαχείριση όλων",
"grp_edit_group" => "Επεξεργασία ομάδας χρηστών",
"grp_sub_to_rights" => "Subject to user rights",
"grp_view" => "Προβολή",
"grp_add" => "Προσθήκη",
"grp_edit" => "Επεξεργασία",
"grp_delete" => "Διαγραφή",
"grp_add_group" => "Προσθήκη ομάδας",
"grp_upd_group" => "Ενημέρωση ομάδας",
"grp_added" => "Προστέθηκε ομάδα",
"grp_updated" => "Ομάδα ενημερώθηκε",
"grp_deleted" => "Διαγραφή ομάδας",
"grp_not_deleted" => "Ομάδα δεν διαγράφηκε",
"grp_in_use" => "Χρησιμοποιείται η ομάδα",
"grp_cred_required" => "Όνομα ομάδας, δικαιώματα και κατηγορίες απαιτούνται",
"grp_name_exists" => "Το όνομα ομάδας υπάρχει ήδη",
"grp_name_invalid" => "Μη έγκυρο όνομα ομάδας (ελάχιστο μήκος 2: A-Z, a-z, 0-9 και _-.)",
"grp_check_add" => "At least one check box in the Add column must be checked",
"grp_background" => "Χρώμα φόντου",
"grp_select_color" => "Επιλογή χρώματος",
"grp_invalid_color" => "Η μορφή έγχρωμης μορφής είναι άκυρη (#XXXXXX όπου X = HEX-value)",
"grp_go_to_users" => "Μετάβαση στους χρήστες",

//texteditor.php
"edi_text_editor" => "Text Editor",
"edi_file_name" => "File name",
"edi_save" => "Save text",
"edi_backup" => "Backup text",
"edi_select_file" => "Select file",
"edi_info_text" => "Information text",
"edi_pub_recips" => "Public recipients",
"edi_recips_list" => "Recipients list",
"edi_new_recips_list" => "New recipients list",
"edi_no_file_name" => "No file name specified",
"edi_no_text" => "There is no text",
"edi_confirm_changes" => "The text changes have not been saved\\nDo you want to continue?", //don't remove '\\n'
"edi_text_saved" => "Text saved to file $1",

//database.php
"mdb_dbm_functions" => "Λειτουργίες βάσης δεδομένων",
"mdb_noshow_tables" => "Δεν είναι δυνατή η λήψη τραπέζι (ων)",
"mdb_noshow_restore" => "Δεν έχει επιλεγεί αρχείο δημιουργίας αντιγράφων ασφαλείας",
"mdb_file_not_sql" => "Το αρχείο δημιουργίας αντιγράφων ασφαλείας θα πρέπει να είναι ένα αρχείο SQL (επέκταση '.sql')",
"mdb_db_content" => "Database Content",
"mdb_total_evenst" => "Total number of events",
"mdb_evts_older_1m" => "Events older than 1 month",
"mdb_evts_older_6m" => "Events older than 6 months",
"mdb_evts_older_1y" => "Events older than 1 year",
"mdb_evts_deleted" => "Total number of deleted events",
"mdb_not_removed" => "not yet removed from the DB",
"mdb_total_cats" => "Total number of categories",
"mdb_total_users" => "Total number of users",
"mdb_total_groups" => "Total number of user groups",
"mdb_compact" => "Συμπαγής βάση δεδομένων",
"mdb_compact_table" => "Συμπαγής πίνακας",
"mdb_compact_error" => "Σφάλμα",
"mdb_compact_done" => "Έγινε",
"mdb_purge_done" => "Διαγραμμένα συμβάντα που έχουν διαγραφεί οριστικά από τη βάση δεδομένων",
"mdb_backup" => "Βάση δεδομένων αντιγράφων ασφαλείας",
"mdb_backup_table" => "Πίνακας αντιγράφων ασφαλείας",
"mdb_backup_file" => "Αρχείο αντιγράφων ασφαλείας",
"mdb_backup_done" => "Έγινε",
"mdb_records" => "εγγραφές",
"mdb_restore" => "Επαναφορά βάσης δεδομένων",
"mdb_restore_table" => "Επαναφορά πίνακα",
"mdb_inserted" => "εγγραφές εισάγονται",
"mdb_db_restored" => "Η βάση δεδομένων έχει αποκατασταθεί",
"mdb_db_upgraded" => "Database upgraded",
"mdb_no_bup_match" => "Το αρχείο αντιγράφου ασφαλείας δεν ταιριάζει με την έκδοση του ημερολογίου.<br>Η βάση δεδομένων δεν έχει αποκατασταθεί.",
"mdb_events" => "Εκδηλώσεις",
"mdb_delete" => "Διαγραφή",
"mdb_undelete" => "undelete",
"mdb_between_dates" => "που συμβαίνουν μεταξύ",
"mdb_deleted" => "Διαγραμμένα συμβάντα",
"mdb_undeleted" => "Διαγραφή γεγονότων",
"mdb_file_saved" => "Το αρχείο αντιγράφων ασφαλείας αποθηκεύτηκε στο φάκελο 'αρχεία' στο διακομιστή.",
"mdb_file_name" => "Όνομα αρχείου",
"mdb_start" => "Έναρξη",
"mdb_no_function_checked" => "Δεν επιλέχθηκαν λειτουργίες",
"mdb_write_error" => "Η εγγραφή αρχείου αντιγράφων ασφαλείας απέτυχε <br> Ελέγξτε τα δικαιώματα του αρχείου 'files /' directory",

//import/export.php
"iex_file" => "Επιλεγμένο αρχείο",
"iex_file_name" => "Όνομα αρχείου προορισμού",
"iex_file_description" => "Περιγραφή του αρχείου iCal",
"iex_filters" => "Φίλτρα γεγονότων",
"iex_export_usr" => "Export User Profiles",
"iex_import_usr" => "Import User Profiles",
"iex_upload_ics" => "Ανεβάστε το αρχείο iCal",
"iex_create_ics" => "Δημιουργία αρχείου iCal",
"iex_tz_adjust" => "Ρυθμίσεις ζωνών ώρας",
"iex_upload_csv" => "Μεταφόρτωση αρχείου CSV",
"iex_upload_file" => "Ανέβασμα αρχείου",
"iex_create_file" => "Δημιουργία αρχείου",
"iex_download_file" => "Λήψη αρχείου",
"iex_fields_sep_by" => "Πεδία διαχωρισμένα από",
"iex_birthday_cat_id" => "Αναγνωριστικό κατηγορίας γενεθλίων",
"iex_default_grp_id" => "Default user group ID",
"iex_default_cat_id" => "Προεπιλεγμένο αναγνωριστικό κατηγορίας",
"iex_default_pword" => "Default password",
"iex_if_no_pw" => "If no password specified",
"iex_replace_users" => "Replace existing users",
"iex_if_no_grp" => "if no user group found",
"iex_if_no_cat" => "αν δεν βρέθηκε κατηγορία",
"iex_import_events_from_date" => "Εισαγωγή συμβάντων που συμβαίνουν από την",
"iex_no_events_from_date" => "Δεν βρέθηκαν συμβάντα από την καθορισμένη ημερομηνία",
"iex_see_insert" => "δείτε τις οδηγίες στα δεξιά",
"iex_no_file_name" => "Λείπει το όνομα του αρχείου",
"iex_no_begin_tag" => "μη έγκυρο αρχείο iCal (λείπει η ετικέτα BEGIN)",
"iex_bad_date" => "Κακή ημερομηνία",
"iex_date_format" => "Μορφή ημερομηνίας συμβάντος",
"iex_time_format" => "Χρόνος εκδήλωσης",
"iex_number_of_errors" => "Αριθμός σφαλμάτων στη λίστα",
"iex_bgnd_highlighted" => "επισημασμένο φόντο",
"iex_verify_event_list" => "Επαλήθευση λίστας συμβάντων, διορθώστε πιθανά σφάλματα και κάντε κλικ",
"iex_add_events" => "Προσθήκη γεγονότων στη βάση δεδομένων",
"iex_verify_user_list" => "Verify User List, correct possible errors and click",
"iex_add_users" => "Add Users to Database",
"iex_select_ignore_birthday" => "Επιλέξτε πλαίσια ελέγχου Παράβλεψη και γενέθλια, όπως απαιτείται",
"iex_select_ignore" => "Επιλέξτε Παράβλεψη πλαισίου ελέγχου για να αγνοήσετε το συμβάν",
"iex_check_all_ignore" => "Έλεγχος όλων των πλαισίων παραβίασης",
"iex_title" => "Τίτλος",
"iex_venue" => "Χώρος",
"iex_owner" => "Ιδιοκτήτης",
"iex_category" => "Κατηγορία",
"iex_date" => "Ημερομηνία",
"iex_end_date" => "Ημερομηνία λήξης",
"iex_start_time" => "Ώρα έναρξης",
"iex_end_time" => "Τέλος χρόνου",
"iex_description" => "Περιγραφή",
"iex_repeat" => "Επανάληψη",
"iex_birthday" => "Γενέθλια",
"iex_ignore" => "Αγνόηση",
"iex_events_added" => "προστέθηκαν γεγονότα",
"iex_events_dropped" => "γεγονότα μειώθηκαν (ήδη υπάρχουν)",
"iex_users_added" => "users added",
"iex_users_deleted" => "users deleted",
"iex_csv_file_error_on_line" => "Σφάλμα CSV αρχείο on line",
"iex_between_dates" => "Εμφανίζεται μεταξύ",
"iex_changed_between" => "Προστέθηκε /τροποποιήθηκε μεταξύ",
"iex_select_date" => "Επιλογή ημερομηνίας",
"iex_select_start_date" => "Επιλογή ημερομηνίας έναρξης",
"iex_select_end_date" => "Επιλογή ημερομηνίας λήξης",
"iex_group" => "User group",
"iex_name" => "User name",
"iex_email" => "Email address",
"iex_phone" => "Phone number",
"iex_msgID" => "Chat ID",
"iex_lang" => "Language",
"iex_pword" => "Password",
"iex_all_groups" => "all groups",
"iex_all_cats" => "όλες οι κατηγορίες",
"iex_all_users" => "όλους τους χρήστες",
"iex_no_events_found" => "Δεν βρέθηκαν συμβάντα",
"iex_file_created" => "Δημιουργήθηκε αρχείο",
"iex_write error" => "Η αποστολή του αρχείου εξαγωγής απέτυχε <br> Ελέγξτε τα δικαιώματα του αρχείου 'files /'",
"iex_invalid" => "invalid",
"iex_in_use" => "already in use",

//cleanup.php
"cup_cup_functions" => "Clean Up Functions",
"cup_fill_fields" => "Fill in the date and click Clean Up.",
"cup_found_confirm" => "If items 'to be cleaned up' are found, you will be asked asked for confirmation.",
"cup_evt" => "Events to delete",
"cup_usr" => "User accounts to delete",
"cup_att" => "Attachments to delete",
"cup_rec" => "Recipient lists to delete",
"cup_tns" => "Thumbnails to delete",
"cup_past_events" => "Past events",
"cup_past_users" => "Inactive users",
"cup_att_dir" => "Attachments folder",
"cup_rec_dir" => "Reciplists folder",
"cup_tns_dir" => "Thumbnails folder",
"cup_usr_text" => "Account of users not logged in since",
"cup_evt_text" => "Events which occurred before",
"cup_att_text" => "Attachments not used in events since",
"cup_rec_text" => "Recipients lists not used in events since",
"cup_tns_text" => "Thumbnails not used in events since",
"cup_select_date" => "Select date",
"cup_blank_date1" => "A blank date means: Never logged in.",
"cup_blank_date2" => "A blank date means: Not used at all (orphans).",
"cup_nothing_to_delete" => "Nothing to clean up",
"cup_clean_up" => "Clean Up",
"cup_cancel" => "Cancel",
"cup_delete" => "Delete",
"cup_invalid date" => "Invalid date",
"cup_events_deleted" => "Events deleted",
"cup_accounts_deleted" => "Accounts deleted",
"cup_files_deleted" => "Files deleted",
"cup_important" => "IMPORTANT:",
"cup_deleted_compact" => "Deleted events and user accounts are marked 'deleted', but still take up space.<br> On the Database page these events and accounts can be permanently removed<br>with the Compact function.",
"cup_deleted_files" => "Deleted files are permanently removed from the folders and cannot be recovered!",

//toolsaaf.php
"aff_sel_cals" =>  "Select calendar(s)",
"aff_evt_copied" =>  "Event copied",

//styling.php
"sty_css_intro" => "Οι τιμές που καθορίζονται σε αυτή τη σελίδα θα πρέπει να τηρούν τα πρότυπα CSS",
"sty_preview_theme" => "Προεπισκόπηση θέμα",
"sty_preview_theme_title" => "Προεπισκόπηση εμφανιζόμενου θέματος στο ημερολόγιο",
"sty_stop_preview" => "Διακοπή Προεπισκόπηση",
"sty_stop_preview_title" => "Διακοπή προεπισκόπησης του εμφανιζόμενου θέματος στο ημερολόγιο",
"sty_save_theme" => "Αποθήκευση θέματος",
"sty_save_theme_title" => "Αποθήκευση εμφανιζόμενου θέματος στη βάση δεδομένων",
"sty_backup_theme" => "Θέμα δημιουργίας αντιγράφων ασφαλείας",
"sty_backup_theme_title" => "Θέμα δημιουργίας αντιγράφων ασφαλείας από βάση δεδομένων σε αρχείο",
"sty_restore_theme" => "Επαναφορά θέματος",
"sty_restore_theme_title" => "Επαναφορά θέματος από αρχείο σε εμφάνιση",
"sty_default_luxcal" => "προεπιλεγμένο θέμα LuxCal",
"sty_close_window" => "Κλείσιμο παραθύρου",
"sty_close_window_title" => "Κλείσιμο αυτού του παραθύρου",
"sty_theme_title" => "Θέμα θέμα",
"sty_general" => "Γενικά",
"sty_grid_views" => "Πλέγμα /Προβολές",
"sty_hover_boxes" => "Πλαίσια με κίνηση",
"sty_bgtx_colors" => "Χρώματα φόντου /κειμένου",
"sty_bord_colors" => "Χρώματα ορίων",
"sty_fontfam_sizes" => "Οικογένεια γραμματοσειρών /μεγέθη",
"sty_font_sizes" => "Μέγεθος γραμματοσειράς",
"sty_miscel" => "Διάφορα",
"sty_background" => "Ιστορικό",
"sty_text" => "Κείμενο",
"sty_color" => "Χρώμα",
"sty_example" => "Παράδειγμα",
"sty_theme_previewed" => "Τρόπος προεπισκόπησης - μπορείτε τώρα να περιηγηθείτε στο ημερολόγιο.",
"sty_theme_saved" => "Θέμα αποθηκευμένο στη βάση δεδομένων",
"sty_theme_backedup" => "Το θέμα υποστηρίζεται από βάση δεδομένων σε αρχείο:",
"sty_theme_restored1" => "Το θέμα αποκαταστάθηκε από το αρχείο:",
"sty_theme_restored2" => "Πατήστε Save Theme για να αποθηκεύσετε το θέμα στη βάση δεδομένων",
"sty_unsaved_changes" => "ΠΡΟΕΙΔΟΠΟΙΗΣΗ - Μη αποθηκευμένες αλλαγές! \\ nΕάν κλείσετε το παράθυρο, οι αλλαγές θα χαθούν.", //μην καταργήσετε '\\ n'
"sty_number_of_errors" => "Αριθμός σφαλμάτων στη λίστα",
"sty_bgnd_highlighted" => "επισημασμένο φόντο",
"sty_XXXX" => "γενικό ημερολόγιο",
"sty_TBAR" => "κορυφαία γραμμή ημερολογίου",
"sty_BHAR" => "γραμμές, κεφαλίδες και γραμμές",
"sty_BUTS" => "κουμπιά",
"sty_DROP" => "αναπτυσσόμενα μενού",
"sty_XWIN" => "αναδυόμενα παράθυρα",
"sty_INBX" => "εισαγάγετε κουτιά",
"sty_OVBX" => "πλαίσια επικάλυψης",
"sty_BUTH" => "κουμπιά - σε αιωρούνται",
"sty_FFLD" => "πεδία φόρμας",
"sty_CONF" => "μήνυμα επιβεβαίωσης",
"sty_WARN" => "μήνυμα προειδοποίησης",
"sty_ERRO" => "μήνυμα λάθους",
"sty_HLIT" => "ένδειξη κειμένου",
"sty_FXXX" => "οικογένεια βασικών γραμματοσειρών",
"sty_SXXX" => "βασικό μέγεθος γραμματοσειράς",
"sty_PGTL" => "τίτλοι σελίδας",
"sty_THDL" => "κεφαλίδες πινάκων L",
"sty_THDM" => "κεφαλίδες πινάκων M",
"sty_DTHD" => "κεφαλίδες ημερομηνίας",
"sty_SNHD" => "κεφαλίδες ενότητας",
"sty_PWIN" => "αναδυόμενα παράθυρα",
"sty_SMAL" => "μικρό κείμενο",
"sty_GCTH" => "ημέρα κυψέλη κορυφή - hover",
"sty_GTFD" => "κυτταρική κεφαλή 1η ημέρα του μήνα",
"sty_GWTC" => "στήλη εβδομάδα /ώρα",
"sty_GWD1" => "μήνα 1 της εβδομάδας",
"sty_GWD2" => "μήνα 2 της εβδομάδας",
"sty_GWE1" => "Σαββατοκύριακο μήνα 1",
"sty_GWE2" => "μήνα 2ου Σαββατοκύριακου",
"sty_GOUT" => "εκτός μήνα",
"sty_GTOD" => "Κελί ημέρας σήμερα",
"sty_GSEL" => "ημέρα επιλογής ημέρας",
"sty_LINK" => "Σύνδεσμοι URL και ηλεκτρονικού ταχυδρομείου",
"sty_CHBX" => "το πλαίσιο ελέγχου todo",
"sty_EVTI" => "τίτλος συμβάντος στις προβολές",
"sty_HNOR" => "κανονικό συμβάν",
"sty_HPRI" => "ιδιωτικό συμβάν",
"sty_HREP" => "επαναλαμβανόμενο συμβάν",
"sty_POPU" => "αναδυόμενο παράθυρο",
"sty_TbSw" => "σκιά κορυφής μπαρ (0: όχι 1: ναι)",
"sty_CtOf" => "μετατόπιση περιεχομένου",

//lcalcron.php
"cro_sum_header" => "CRON JOB ΣΥΝΟΨΗ",
"cro_sum_trailer" => "ΤΕΛΟΣ ΤΗΣ ΠΕΡΙΛΗΨΗΣ",
"cro_sum_title_eve" => "ΕΚΤΕΛΕΣΗ ΕΚΔΗΛΩΣΕΩΝ",
"cro_nr_evts_deleted" => "Αριθμός διαγραμμένων συμβάντων",
"cro_sum_title_not" => "REMINDERS",
"cro_no_reminders_due" => "Δεν υπάρχουν μηνύματα υπενθύμισης",
"cro_due_in" => "Λήξη",
"cro_due_today" => "Λόγω σήμερα",
"cro_days" => "ημέρα (ες)",
"cro_date_time" => "Ημερομηνία /ώρα",
"cro_title" => "Τίτλος",
"cro_venue" => "Χώρος",
"cro_description" => "Περιγραφή",
"cro_category" => "Κατηγορία",
"cro_status" => "Κατάσταση",
"cro_none_active" => "No reminders or periodic services active",
"cro_sum_title_use" => "ΧΡΗΣΙΜΟΠΟΙΟΥΜΕΝΟΙ ΛΟΓΑΡΙΑΣΜΟΙ ΧΡΗΣΤΗ",
"cro_nr_accounts_deleted" => "Αριθμός λογαριασμών διαγράφηκε",
"cro_no_accounts_deleted" => "Δεν έχουν διαγραφεί λογαριασμοί",
"cro_sum_title_ice" => "ΕΞΑΓΩΓΗ ΕΚΔΗΛΩΣΕΩΝ",
"cro_nr_events_exported" => "Αριθμός συμβάντων που εξήχθησαν σε μορφή iCalendar στο αρχείο",

//messaging.php
"mes_no_msg_no_recip" => "Δεν στάλθηκε, δεν βρέθηκαν παραλήπτες",

//explanations
"xpl_edit" =>
"<h3>Edit Instructions</h3>
<p>This text editor can be used to edit the content of the following files:
<dl>
<dt>info.txt</dt><dd>The information text, which - when enabled on the Settings 
page - is visible in the side panel right next to the calendar page.</dd>
<dt>+recipients.txt</dt><dd>The file with public (not-registered) recipients, 
from which recipients can be selected for reminder messages.</dd>
<dt>&lt;list_name&gt;.txt</dt><dd>One or more lists with recipients, which can 
be added in its entirety to the recipients for reminder messages.</dd>
</dl>
</p>",

"xpl_edit_info_texts" =>
"<h3>Edit Instructions - Information Texts</h3>
<p>When enabled on the Settings page, the information messages in the text area 
on the left will be shown in the calendar views in a side panel right next to 
the calendar page. The messages may contain HTML-tags and inline styles. 
Examples of of the various possibilities of info messages can be found in the file 
'sidepanel/samples/info.txt'.</p>
<p>Information messages can be displayed from a start date till an end date.
Each info message must be preceded by a line with the specified display period 
enclosed by ~ characters. Text before the first line starting with a ~ character 
can be used for your personal notes and will not be shown in the side panel's 
info area.</p><br>
<p>Start and end date format: ~m1.d1-m2.d2~, where m1 and d1 are the start month 
and day and m2 and d2 are the end month and day. If d1 is omitted, the first day 
of m1 is assumed. If d2 is omitted, the last day of m2 is assumed. If m2 and d2 
are omitted, the last day of m1 is assumed.</p>
<p>Examples:<br>
<b>~4~</b>: The whole month of April<br>
<b>~2.10-2.14~</b>: 10 - 14 February<br>
<b>~6-7~</b>: 1 June - 31 July<br>
<b>~12.15-12.25~</b>: 15 - 25 December<br>
<b>~8.15-10.5~</b>: 15 August - 5 October<br>
<b>~12.15~</b>: 15 December - 31 December</p><br>
<p>Suggestion: Start with creating a backup copy (Backup text).</p>",

"xpl_edit_pub_recips" =>
"<h3>Edit Instructions - Public Recipients</h3>
<p>This file can contain a list with public (not registered) recipients from 
which recipients can be copied to the recipients lists for reminder messages.</p>
<p>Each recipient should be specified on a separate line.</p><br>
<p>Depending on the messaging services enabled on the settings page recipients 
can be specified by:</p>
<ul>
<li>email address,</li>
<li>Telegram chat ID,</li>
<li>mobile phone number.</li>
</ul>
<br>
<p>In the file text starting with a #-character and empty lines will be flushed 
and blanks at the start or end of specified recipients will be removed.</p>",

"xpl_edit_recips_list" =>
"<h3>Edit Instructions - Recipients List</h3>
<p>This file can contain a list with public or registered recipients. The file 
can be added in its entirety to the list of recipients for reminder messages.</p>
<p>Each recipient should be specified on a separate line.</p><br>
<p>Depending on the messaging services enabled on the settings page and the user 
account recipients can be specified by:</p>
<ul>
<li>user name,</li>
<li>email address,</li>
<li>Telegram chat ID,</li>
<li>mobile phone number.</li>
</ul>
<br>
<p>In the file text starting with a #-character and empty lines will be flushed 
and blanks at the start or end of specified recipients will be removed.</p>
<p>A new recipients list can be created by changing the file name and selecting 
the Save text button</p>",

"xpl_manage_db" =>
"<h3> Διαχειριστείτε τις οδηγίες βάσης δεδομένων </h3>
<p> Στη σελίδα αυτή μπορούν να επιλεγούν οι ακόλουθες λειτουργίες: </p>
<h6> Συμπαγής βάση δεδομένων </h6>
<p> Όταν ένας χρήστης διαγράψει ένα συμβάν, το συμβάν θα επισημανθεί ως 'διαγραμμένο', αλλά θα το κάνει
να μην αφαιρεθεί από τη βάση δεδομένων. Η λειτουργία Compact Database θα είναι μόνιμη
καταργήστε τα συμβάντα που έχουν διαγραφεί πριν από περισσότερες από 30 ημέρες από τη βάση δεδομένων και ελευθερώστε το χώρο
καταλαμβάνεται από αυτά τα γεγονότα. </p>
<h6> Δημιουργία αντιγράφων ασφαλείας βάσης δεδομένων </h6>
<p> Αυτή η λειτουργία θα δημιουργήσει ένα αντίγραφο ασφαλείας της πλήρους βάσης ημερολογίου (πίνακες,
δομή και περιεχόμενο) σε μορφή .sql. Το αντίγραφο ασφαλείας θα αποθηκευτεί στο
<strong> αρχεία /</strong> με όνομα αρχείου:
<kbd> dump-cal-lcv-yyyymmdd-hhmmss.sql </kbd> (όπου 'cal' = αναγνωριστικό ημερολογίου, lcv =
ημερολογιακή έκδοση και 'yyyymmdd-hhmmss' = έτος, μήνα, ημέρα, ώρα, λεπτά και
δευτερόλεπτα). </p>
<p> Το αρχείο αντιγράφων ασφαλείας μπορεί να χρησιμοποιηθεί για την αναδημιουργία της βάσης δεδομένων ημερολογίου (δομή και
δεδομένα), μέσω της λειτουργίας αποκατάστασης που περιγράφεται παρακάτω ή χρησιμοποιώντας για παράδειγμα το
<strong> phpMyAdmin </strong>, το οποίο παρέχεται από τους περισσότερους οικοδεσπότες ιστού. </p>
<h6> Επαναφορά βάσης δεδομένων </h6>
<p> Αυτή η λειτουργία θα επαναφέρει τη βάση δεδομένων ημερολογίου με τα περιεχόμενα του
(αρχείο τύπου .sql). </p>
<p> Κατά την επαναφορά της βάσης δεδομένων, ΟΛΑ ΤΑ ΠΑΡΟΥΣΑ ΠΑΡΟΥΣΑ ΣΤΟΙΧΕΙΑ ΘΑ ΧΡΗΣΙΜΟΠΟΙΗΘΟΥΝ! See the admin_guide.html section 3 for a detailed explanation. </p>
<h6> Εκδηλώσεις </h6>
<p> Αυτή η λειτουργία θα διαγράψει ή θα ακυρώσει τα συμβάντα που συμβαίνουν μεταξύ του
καθορισμένες ημερομηνίες. Εάν η ημερομηνία παραμείνει κενή, δεν υπάρχει όριο ημερομηνίας. έτσι εάν και οι δύο
οι ημερομηνίες παραμένουν κενές, ΟΛΑ ΤΑ ΓΕΓΟΝΟΤΑ ΘΑ ΔΙΑΓΡΑΦΟΥΝΤΑΙ! </p> <br>
<p> ΣΗΜΑΝΤΙΚΟ: Όταν η βάση δεδομένων συμπιεστεί (βλ. παραπάνω), τα συμβάντα που είναι
οριστικά αφαιρεθεί από τη βάση δεδομένων δεν μπορεί να διαγραφεί πια! </p> ",

"xpl_import_csv" =>
"<h3> Οδηγίες εισαγωγής CSV </h3>
<p> Αυτή η φόρμα χρησιμοποιείται για την εισαγωγή ενός αρχείου κειμένου CSV (Values ​​Separated Comma) που περιέχει
δεδομένα συμβάντων στην Ημερολόγιο LuxCal </p>
<p> Η σειρά των στηλών στο αρχείο CSV πρέπει να είναι: τίτλος, χώρος, αναγνωριστικό κατηγορίας (βλ
παρακάτω), ημερομηνία, ημερομηνία λήξης, ώρα έναρξης, ώρα λήξης και περιγραφή. Αν η πρώτη σειρά του
το αρχείο CSV περιέχει κεφαλίδες στηλών, θα αγνοηθεί. </p>
<p> Για σωστό χειρισμό ειδικών χαρακτήρων, το αρχείο CSV πρέπει να είναι κωδικοποιημένο με UTF-8. </p>
<h6> Δείγματα αρχείων CSV </h6>
<p> Τα αρχεία CSV δειγματοληψίας (επέκταση αρχείου .csv) μπορούν να βρεθούν στον κατάλογο 'files/'
της εγκατάστασης LuxCal. </p>
<h6> Διαχωριστής πεδίων </h6>
Ο διαχωριστής πεδίων μπορεί να είναι οποιοσδήποτε χαρακτήρας, για παράδειγμα ένα κόμμα, ένα ημικύκλιο ή α
χαρακτήρα καρτέλας (καρτέλα-χαρακτήρας: '\\t'). Ο χαρακτήρας διαχωρισμού πεδίου πρέπει να είναι μοναδικός
και μπορεί να μην είναι μέρος του κειμένου, αριθμών ή ημερομηνιών στα πεδία.
<h6> Μορφή ημερομηνίας και ώρας </h6>
<p> Η μορφή της επιλεγμένης ημερομηνίας συμβάντος και η μορφή του χρόνου εκδήλωσης στα αριστερά πρέπει να ταιριάζουν με το
μορφή ημερομηνιών και χρόνων στο αρχείο CSV που έχει μεταφορτωθεί. </p>
<p>If no start time (blank) is present, the event will be shown as a 'no time' event 
in the calendar. If the start time is 00:00 or 12:00am, the event will be shown as 
an 'all day' event in the calendar.</p>
<h6> Πίνακας κατηγοριών </h6>
<p> Το ημερολόγιο χρησιμοποιεί αριθμούς αναγνώρισης για να καθορίσετε κατηγορίες. Τα αναγνωριστικά κατηγορίας στο CSV
Το αρχείο θα πρέπει να αντιστοιχεί στις κατηγορίες που χρησιμοποιούνται στο ημερολόγιό σας ή να είναι κενό. </p>
<p> Αν στο επόμενο βήμα θέλετε να ορίσετε τα γεγονότα ως «γενέθλια», τα <strong> Γενέθλια
ID κατηγορίας </strong> πρέπει να οριστεί στο αντίστοιχο αναγνωριστικό στην παρακάτω λίστα κατηγοριών. </p>
<p class = 'hired'> Προειδοποίηση: Μην εισάγετε περισσότερα από 100 συμβάντα τη φορά! </p>
<p> Για το ημερολόγιό σας, έχουν οριστεί οι ακόλουθες κατηγορίες: </p> ",

"xpl_import_user" =>
"<h3>User Profile Import Instructions</h3>
<p>This form is used to import a CSV (Comma Separated Values) text file containing 
user profile data into the LuxCal Calendar.</p>
<p>For the proper handling of special characters, the CSV file must be UTF-8 encoded.</p>
<h6>Field separator</h6>
<p>The field separator can be any character, for instance a comma, semi-colon, etc.
The field separator character must be unique 
and may not be part of the text in the fields.</p>
<h6>Default user group ID</h6>
<p>If in the CSV file a user group ID has been left blank, the specified default 
user group ID will be taken.</p>
<h6>Default password</h6>
<p>If in the CSV file a user password has been left blank, the specified default 
password will be taken.</p>
<h6>Replace existing users</h6>
<p>If the replace existing users check-box has been checked, all existing users, 
except the public user and the administrator, will be deleted before importing the 
user profiles.</p>
<br>
<h6>Sample User Profile files</h6>
<p>Sample User profile CSV files (.csv) can be found in the '!luxcal-toolbox/' folder of 
your LuxCal installation.</p>
<h6>Fields in the CSV file</h6>
<p>The order of columns must be as listed below. If the first row of the CSV file 
contains column headers, it will be ignored.</p>
<ul>
<li>User group ID: should correspond to the user groups used in your calendar (see 
table below). If blank, the user will be put in the specified default user group</li>
<li>User name: mandatory</li>
<li>Email address: mandatory</li>
<li>Mobile phone number: optional</li>
<li>Telegram chat ID: optional</li>
<li>Interface language: optional. E.g. English, Dansk. If blank, the default 
language selected on the Settings page will be taken.</li>
<li>Password: optional. If blank, the specified default password will be taken.</li>
</ul>
<p>Blank fields should be indicated by two quotes. Blank fields at the end of each 
row may be left out.</p>
<p class='hired'>Warning: Do not import more than 60 user profiles at a time!</p>
<h6>Table of User Group IDs</h6>
<p>For your calendar, the following user groups have currently been defined:</p>",

"xpl_export_user" =>
"<h3>User Profile Export Instructions</h3>
<p>This form is used to extract and export <strong>User Profiles</strong> from 
the LuxCal Calendar.</p>
<p>Files will be created in the 'files/' directory on the server with the 
specified filename and in the Comma Separated Value (.csv) format.</p>
<h6>Destination file name</h6>
If not specified, the default filename will be 
the calendar name followed by the suffix '_users'. The filename extension will 
be automatically set to <b>.csv</b>.</p>
<h6>User Group</h6>
Only the user profiles of the selected user group will be 
exported. If 'all groups' is selected, the user profiles in the destination file 
will be sorted on user group</p>
<h6>Field separator</h6>
<p>The field separator can be any character, for instance a comma, semi-colon, etc.
The field separator character must be unique 
and may not be part of the text in the fields.</p><br>
<p>Existing files in the 'files/' directory on the server with the same name will 
be overwritten by the new file.</p>
<p>The order of columns in the destination file will be: group ID, user name, 
email address, mobile phone number, interface language and password.<br>
<b>Note:</b> Passwords in the exported user profiles are encoded and cannot be 
decoded.</p><br>
<p>When <b>downloading</b> the exported .csv file, the current date and time will 
be added to the name of the downloaded file.</p><br>
<h6>Sample User Profile files</h6>
<p>Sample User Profile files (file extension .csv) can be found in the '!luxcal-toolbox/' 
directory of your LuxCal download.</p>",

"xpl_import_ical" =>
"<h3> Οδηγίες εισαγωγής iCalendar </h3>
<p> Αυτή η φόρμα χρησιμοποιείται για την εισαγωγή ενός αρχείου συμβάντος <strong> iCalendar </strong>
το Ημερολόγιο LuxCal. </p>
<p> Το περιεχόμενο του αρχείου πρέπει να πληροί τις προδιαγραφές του [<u> <a href = 'http: //tools.ietf.org/html/rfc5545'
target = '_ blank'> πρότυπο RFC5545 </a> </u>] της Task Force Engineering Internet. </p>
<p> Θα εισαχθούν μόνο συμβάντα. άλλα στοιχεία iCal, όπως: To-Do, Εφημερίδα, Δωρεάν /
Busy και Alarm, θα αγνοηθούν. </p>
<h6> Δείγμα αρχείων iCal </h6>
<p> Δείγματα αρχείων iCalendar (αρχεία επέκτασης αρχείου .ics) βρίσκονται στον κατάλογο 'files/'
 της λήψης σας από το LuxCal. </p>
<h6> Ρυθμίσεις ζωνών ώρας </h6>
<p> Αν το αρχείο iCalendar περιέχει συμβάντα σε διαφορετική ζώνη ώρας και τις ημερομηνίες /ώρες
θα πρέπει να προσαρμόζεται στη ζώνη ώρας ημερολογίου, και στη συνέχεια να ελέγχετε τις 'Ρυθμίσεις ζώνης ώρας'. </p>
<h6> Πίνακας κατηγοριών </h6>
<p> Το ημερολόγιο χρησιμοποιεί αριθμούς αναγνώρισης για να καθορίσετε κατηγορίες. Τα αναγνωριστικά κατηγορίας στο
Το αρχείο iCalendar πρέπει να αντιστοιχεί στις κατηγορίες που χρησιμοποιούνται στο ημερολόγιό σας ή να είναι
κενό. </p>
<p class = 'hired'> Προειδοποίηση: Μην εισάγετε περισσότερα από 100 συμβάντα τη φορά! </p>
<p> Για το ημερολόγιό σας, έχουν οριστεί οι ακόλουθες κατηγορίες: </p>",

"xpl_export_ical" =>
"<h3> Οδηγίες εξαγωγής iCalendar </h3>
<p> Αυτή η φόρμα χρησιμοποιείται για την εξαγωγή και την εξαγωγή συμβάντων <strong> iCalendar </strong> από
το Ημερολόγιο LuxCal. </p>
<p> Τα αρχεία θα δημιουργηθούν στον κατάλογο 'αρχεία /' στο διακομιστή με το
καθορισμένο όνομα αρχείου (χωρίς επέκταση). (Η επέκταση αρχείου είναι <b> .ics </b> και
εάν δεν έχει οριστεί, το προεπιλεγμένο όνομα αρχείου είναι το όνομα του ημερολογίου.
Τα υπάρχοντα αρχεία στον κατάλογο 'αρχεία /' του διακομιστή με το ίδιο όνομα θα
να αντικατασταθεί από το νέο αρχείο. </p>
<p> Η περιγραφή <b> iCal αρχείου </b> (π.χ. 'Συναντήσεις 2024') είναι προαιρετική. Αν
θα εισαχθεί στην κεφαλίδα του εξαγόμενου αρχείου iCal. </p>
<p> <b> Φίλτρα συμβάντων </b>: Τα συμβάντα που εξάγονται μπορούν να φιλτραριστούν με: </p>
<ul>
<li> ιδιοκτήτης συμβάντος </li>
<li> κατηγορία συμβάντων </li>
<li> Ημερομηνία έναρξης συμβάντος </li>
<li> ημερομηνία προσθήκης /τελευταίας τροποποίησης </li>
</ul>
<p> Κάθε φίλτρο είναι προαιρετικό. Το κενό που εμφανίζεται μεταξύ των ημερομηνιών είναι προεπιλεγμένο ως -1 έτος
και +1 έτος αντίστοιχα. Ένα κενό 'προσθήκη /τροποποίηση μεταξύ' ημερομηνίας σημαίνει: χωρίς όριο. </P>
<br>
<p> Το περιεχόμενο του αρχείου με εξαγόμενα συμβάντα θα ικανοποιεί το
[<u> <a href='https://tools.ietf.org/html/rfc5545' target='_blank'> πρότυπο RFC5545 </a> </u>]
της Task Force Μηχανικών Διαδικτύου. </p>
<p> Όταν κάνετε <b> λήψη </b> το εξαγόμενο αρχείο iCal, η ημερομηνία και η ώρα θα είναι
προστέθηκε στο όνομα του ληφθέντος αρχείου. </p>
<h6> Δείγμα αρχείων iCal </h6>
<p> Δείγματα αρχείων iCalendar (αρχεία επέκτασης αρχείου .ics) βρίσκονται στα αρχεία '/'
κατάλογο της λήψης σας από το LuxCal. </p>",

"xpl_clean_up" =>
"<h3>Clean Up Instructions</h3>
<p>On this page the following can be cleaned up:</p>
<h6>Past Events</h6>
<p>Events in this calendar with an end date before the specified date will be 
deleted from the calendar. The specified date must be at least one month 
before the date of today.</p>
<h6>Inactive Users</h6>
<p>The accounts of users that have not logged in this calendar since the 
specified date will be removed from the calendar. The specified date must be 
at least one month before the date of today.</p>
<h6>Attachments folder</h6>
<p>Attachment files which are not used in events since the specified date, will 
be deleted. The date must be blank or in the past. In case of multiple calendars, the 
attachment files will be checked against all calendars.</p>
<h6>Reciplists folder</h6>
<p>Recipients list files which are not used in events since the specified date, 
will be deleted. The date must be blank or in the past. In case of multiple calendars, 
the recipients list files will be checked against all calendars.</p>
<h6>Thumbnails folder</h6>
<p>Thumbnail files which are not used in events since the specified date and are not 
used in the side panel's info.txt file, will 
be deleted. The date must be blank or in the past. In case of multiple calendars, the 
thumbnail files will be checked against all calendars.</p>"
);
?>
