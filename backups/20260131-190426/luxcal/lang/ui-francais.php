<?php
/*
= LuxCal language file =

La traduction française a été réalisée par Fabiou. Mise à jour et complétée par Gérard.

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "fr";

/* -- Titles on the Header of the Calendar -- */

$months = array("Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre");
$months_m = array("Janv","Fév","Mars","Avr","Mai","Juin","Juil","Août","Sept","Oct","Nov","Déc");
$wkDays = array("Dimanche","Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche");
$wkDays_l = array("Dim","Lun","Mar","Mer","Jeu","Ven","Sam","Dim");
$wkDays_m = array("Di","Lu","Ma","Me","Je","Ve","Sa","Di");
$wkDays_s = array("D","L","M","m","J","V","S","D");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Soumettre",
"log_in" => "Connexion",
"log_out" => "Déconnexion",
"portrait" => "Portrait",
"landscape" => "Paysage",
"none" => "Aucun(e).",
"all_day" => "Journée entière",
"back" => "Retour",
"restart" => "Redémarrer",
"by" => "par",
"of" => "de",
"max" => "max.",
"options" => "Options",
"done" => "Terminé",
"at_time" => "à", //date and time separator (e.g. 30-01-2020 @ 10:45)
"from" => "De", //e.g. from 9:30
"until" => "à", //e.g. until 15:30
"to" => "au", //e.g. to 17-02-2020
"birthdays_in" => "Birthdays in",
"open_calendar" => "Ouvrir calendrier",
"no_way" => "Vous n’êtes pas autorisé à exécuter cette action",

//index.php
"title_log_in" => "Connexion",
"title_profile" => "Profil d’Utilisateur",
"title_upcoming" => "Prochains évènements",
"title_event" => "évènement",
"title_check_event" => "Cocher l’évènement",
"title_dmarking" => "Marquage du jour",
"title_search" => "Rechercher du texte",
"title_contact" => "Formulaire de contact",
"title_thumbnails" => "Images de vignettes",
"title_user_guide" => "Guide de l’utilisateur",
"title_settings" => "Gestion des réglages",
"title_edit_cats" => "Gestion des catégories",
"title_edit_users" => "Gestion des utilisateurs",
"title_edit_groups" => "Éditer les groupes d’utilisateurs",
"title_edit_text" => "Éditer le texte d'information",
"title_manage_db" => "Gérer la base de données",
"title_clean_up" => "General Clean Up Functions",
"title_changes" => "évènements Ajoutés / Modifiés / Supprimés",
"title_usr_import" => "Import d’utilisateurs - format CSV",
"title_usr_export" => "Export d’utilisateurs - format CSV",
"title_evt_import" => "Import d’évènements - format CSV",
"title_ics_import" => "Import d’évènements - format iCal",
"title_ics_export" => "Export d’évènements - format iCal",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "Styles de l’utilisateur",
"title_bd_calendar" => "Birthday Calendar",

//header.php
"hdr_button_back" => "Retour sur la page parent",
"hdr_options_submit" => "Faites votre choix puis appuyez sur “Terminé”",
"hdr_options_panel" => "Menu Options",
"hdr_select_date" => "Aller à la date",
"hdr_calendar" => "Calendrier",
"hdr_evt_copied_to" => "Event copied to calendar",
"hdr_view" => "Vue",
"hdr_lang" => "Langue",
"hdr_all_cats" => "Catégories : Toutes",
"hdr_all_groups" => "Tous Groupes",
"hdr_all_users" => "Utilisateurs : Tous",
"hdr_go_to_view" => "Aller à la vue",
"hdr_view_1" => "Année",
"hdr_view_2" => "Mois",
"hdr_view_3" => "Mois ouvré",
"hdr_view_4" => "Semaine",
"hdr_view_5" => "Semaine ouvrée",
"hdr_view_6" => "Jour",
"hdr_view_7" => "A venir",
"hdr_view_8" => "Modifications",
"hdr_view_9" => "Matrice(Cat.)",
"hdr_view_10" => "Matrice(Util.)",
"hdr_view_11" => "Diagramme de Gantt",
"hdr_select_admin_functions" => "Choisir une fonction Administrateur",
"hdr_admin" => "Administration",
"hdr_settings" => "Réglages",
"hdr_categories" => "Catégories",
"hdr_users" => "Utilisateurs",
"hdr_groups" => "Groupes d’utilisateurs",
"hdr_text_editor" => "Editeur de texte",
"hdr_database" => "Base de données",
"hdr_clean_up" => "Clean Up",
"hdr_import_usr" => "Import d’utilis. (fich. CSV)",
"hdr_export_usr" => "Export d’utilis. (fich. CSV)",
"hdr_import_csv" => "Import d’évènmts (.CSV)",
"hdr_import_ics" => "Import d’évènmts (.iCal)",
"hdr_export_ics" => "Export d’évènmts (.iCal)",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Styles",
"hdr_back_to_cal" => "Retour sur la vue Calendrier",
"hdr_button_print" => "Imprimer",
"hdr_print_page" => "Imprimez cette page",
"hdr_button_pdf" => "Fichier PDF - Evènements",
"hdr_button_pdf_bc" => "PDF File - Anniversaires",
"hdr_dload_pdf" => "Télécharger les évènements à venir",
"hdr_dload_pdf_bc" => "Download birthday calendar",
"hdr_button_contact" => "Contact",
"hdr_contact" => "Contacter l’administrateur",
"hdr_button_tnails" => "Vignettes",
"hdr_tnails" => "Affiche les vignettes",
"hdr_button_toap" => "Approuver",
"hdr_toap_list" => "évènements à approuver",
"hdr_button_todo" => "À faire",
"hdr_todo_list" => "Liste des “à faire”",
"hdr_button_upco" => "À venir",
"hdr_upco_list" => "évènements à venir",
"hdr_about_lc" => "About LuxCal",
"hdr_button_search" => "Rechercher",
"hdr_search" => "Rechercher texte",
"hdr_button_add" => "Ajouter",
"hdr_add_event" => "Ajouter un évènement",
"hdr_button_help" => "Aide",
"hdr_user_guide" => "Manuel d’utilisation",
"hdr_gen_guide" => "Guide général de l’utilisateur",
"hdr_cs_guide" => "Guide contextuel de l’utilisateur",
"hdr_gen_help" => "Aide générale",
"hdr_prev_help" => "Aide précédente",
"hdr_open_menu" => "Ouvrir Menu",
"hdr_side_menu" => "Menu latéral",
"hdr_dest_cals" => "Calendrier(s) cible(s)",
"hdr_copy_evt" => "Copier l'évènement",
"hdr_tn_note" => "Copied to clipboard",
"hdr_today" => "Aujourd’hui", //dtpicker.js
"hdr_clear" => "Effacer", //dtpicker.js

//event.php
"evt_no_title" => "Titre manquant",
"evt_no_start_date" => "Date de début manquante",
"evt_bad_date" => "Mauvaise date",
"evt_bad_rdate" => "Mauvaise date de fin de répétition",
"evt_no_start_time" => "Heure du début manquante",
"evt_bad_time" => "Mauvaise heure",
"evt_end_before_start_time" => "Heure de fin précède heure de début",
"evt_end_before_start_date" => "Date de fin précède date de début",
"evt_until_before_start_date" => "Fin de répétition précède date de début",
"evt_default_duration" => "Durée d’évènement par défaut&nbsp;: $1 heures et $2 minutes",
"evt_fixed_duration" => "Durée fixe d’évènement&nbsp;: $1 heures et $2 minutes",
"evt_approved" => "évènement approuvé",
"evt_apd_locked" => "évènement approuvé et verrouillé",
"evt_title" => "Titre",
"evt_venue" => "Lieu",
"evt_address_button" => "Une adresse entre deux ! devient un bouton `adresse`",
"evt_list" => "Liste",
"evt_category" => "Catégorie",
"evt_subcategory" => "Sous-catégorie",
"evt_description" => "Description",
"evt_attachments" => "Pièces jointes",
"evt_attach_file" => "Pièce jointe",
"evt_click_to_open" => "Cliquer pour ouvrir",
"evt_click_to_remove" => "Cliquer pour retirer",
"evt_no_pdf_img_vid" => "Le fichier doit être un pdf, une image ou une vidéo",
"evt_error_file_upload" => "Erreur en chargeant le fichier",
"evt_upload_too_large" => "Fichier à charger trop gros",
"evt_date_time" => "Date / heure",
"evt_date" => "Date",
"evt_private" => "Privé",
"evt_start_date" => "Date de début",
"evt_end_date" => "Date de fin",
"evt_select_date" => "Choisir la date",
"evt_select_time" => "Choisir l’heure",
"evt_all_day" => "Journée entière",
"evt_no_time" => "Pas d'heure",
"evt_change" => "Modifier",
"evt_set_repeat" => "Périodicité",
"evt_set" => "OK",
"evt_help" => "aide",
"evt_repeat_not_supported" => "Périodicité non supportée",
"evt_no_repeat" => "Périodicité&nbsp;: néant",
"evt_rolling" => "Rolling",
"evt_until_checked" => "until checked",
"evt_repeat_on" => "Répéter tous les",
"evt_until" => "jusqu’au",
"evt_blank_no_end" => "vide: illimité",
"evt_each_month" => "tous les mois",
"evt_interval2_1" => "premiers",
"evt_interval2_2" => "deuxièmes",
"evt_interval2_3" => "troisièmes",
"evt_interval2_4" => "quatrièmes",
"evt_interval2_5" => "derniers",
"evt_period1_1" => "jours",
"evt_period1_2" => "semaines",
"evt_period1_3" => "mois",
"evt_period1_4" => "ans",
"evt_notification" => "Notification",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "maintenant et/ou",
"evt_event_added" => "Évènement ajouté",
"evt_event_edited" => "Évènement modifié",
"evt_event_deleted" => "Évènement supprimé",
"evt_event_approved" => "Évènement approuvé",
"evt_days_before_event" => " jour(s) avant l’évènement",
"evt_to" => "À",
"evt_not_help" => "Liste de destinataires séparées par des points-virgules. Un destinataire peut être un nom d’utilisateur, une adresse email, un n° de téléphone mobile, un Telegram chat ID ou, entre crochets, le nom d’un fichier .txt dans le répertoire “reciplists”, avec une adresse (un nom d’utilisateur, une adresse email, un n° de téléphone ou un Telegram chat ID) par ligne.<br>Longueur maximum du champ : 255 caractères.",
"evt_recip_list_too_long" => "La liste des adresses contient trop de caractère.",
"evt_no_recip_list" => "La liste des adresses est vide",
"evt_not_in_past" => "Date de notification dépassée",
"evt_not_days_invalid" => "Jour de notification invalide",
"evt_status" => "Statut",
"evt_descr_help" => "On peut utiliser les éléments suivants dans les champs Description&nbsp;:<br>• Les balises HTML &lt;b&gt;, &lt;i&gt;, &lt;u&gt; et &lt;s&gt; pour du texte en gras, italique, souligné et barré.",
"evt_descr_help_img" => "• de petites images (vignettes) au format&nbsp;: “nom_d_image.ext”. Les fichiers thumbnail, avec l’extension .gif, .jpg or .png, doivent être présent dans le dossier “thumbnails”. Si elle est en service, la page Vignettes peut être utilisée pour téléverser les fichiers vignettes.",
"evt_descr_help_eml" => "• des liens mailto au format&nbsp;: “adresse email” or “adresse email [nom]”, dans lequel “nom” sera le titre du lien. Par exemple, xxx@yyyy.zzz [Envoyez email].",
"evt_descr_help_url" => "• des liens URL au format&nbsp;: “url” ou “url [nom]”, dans lequel “nom” sera le titre du lien. If 'S:' is placed in front of the URL, the link will open in the same page/tab, otherwise the link will open in a blank page/tab. Par exemple, S:https://www.google.com [recherche]",
"evt_confirm_added" => "évènement ajouté",
"evt_confirm_saved" => "évènement enregistré",
"evt_confirm_deleted" => "évènement supprimé",
"evt_add_close" => "Ajouter et fermer",
"evt_add" => "Ajouter",
"evt_edit" => "Modifier",
"evt_save_close" => "Enregistrer et fermer",
"evt_save" => "Enregistrer",
"evt_clone" => "Dupliquer",
"evt_delete" => "Supprimer",
"evt_close" => "Fermer",
"evt_added" => "Ajouté",
"evt_edited" => "Modifié",
"evt_is_repeating" => "est un évènement répété",
"evt_is_multiday" => "est un évènement multi-jours",
"evt_edit_series_or_occurrence" => "Voulez-vous éditer la série ou cette occurrence ?",
"evt_edit_series" => "Editer la série",
"evt_edit_occurrence" => "Editer l’occurrence",
"evt_select_from_list" => "Select recipients from list",
"evt_select_recips" => "Select Recipients",
"evt_recip_lists" => "Lists with Recipients",
"evt_regist_recips" => "Registered Recipients",
"evt_public_recips" => "Public Recipients",

//events - dmark specific
"mrk_text_and_color" => "Texte et couleur",
"mrk_is_repeating" => "est un marquage répété",
"mrk_is_multiday" => "est un marquage multi-jours",
"mrk_text" => "Texte",
"mrk_color" => "Couleur",
"mrk_background" => "Fond",
"mrk_select_color" => "Sélectionner la Couleur",
"mrk_start_date" => "Date de début",
"mrk_end_date" => "Date de fin",
"mrk_dmark_added" => "Marquage du jour ajouté",
"mrk_dmark_edited" => "Marquage du jour modifié",
"mrk_dmark_deleted" => "Marquage du jour supprimé",
"mrk_dates" => "Date(s)",

//views
"vws_add_event" => "Ajout de nouvel évènement",
"vws_edit_event" => "Éditer l’évènement",
"vws_see_event" => "Voir details",
"vws_view_month" => "Vue Mois",
"vws_view_week" => "Vue Semaine",
"vws_view_day" => "Vue Jour",
"vws_click_for_full" => "Cliquer sur le mois pour afficher le calendrier",
"vws_view_full" => "Voir le calendrier complet",
"vws_prev_year" => "Année précédente",
"vws_next_year" => "Année suivante",
"vws_prev_month" => "Mois précédent",
"vws_next_month" => "Mois suivant",
"vws_forward" => "En avant",
"vws_backward" => "En arrière",
"vws_mark_day" => "Marquer le jour",
"vws_today" => "Aujourd’hui",
"vws_back_to_today" => "Retour au mois courant",
"vws_back_to_main_cal" => "Retour au mois du calendrier principal",
"vws_week" => "Semaine",
"vws_wk" => "Sem",
"vws_time" => "Heure",
"vws_events" => "évènements",
"vws_all_day" => "Journée",
"vws_earlier" => "Plus tôt",
"vws_later" => "Plus tard",
"vws_venue" => "Lieu",
"vws_address" => "Adresse",
"vws_events_for_next" => "évènements à venir",
"vws_days" => "jours",
"vws_added" => "Ajouté",
"vws_edited" => "Modifié",
"vws_notify" => "Envoi d’une notification",
"vws_none_due_in" => "Pas d’évènements à venir",
"vws_evt_cats" => "Catégories d’évènements",
"vws_cal_users" => "Utlisateurs du Calendrier",
"vws_no_users" => "Pas d’utilisateur dans les groupes sélectionnés",
"vws_start" => "Début",
"vws_duration" => "Durée",
"vws_no_events_in_gc" => "Pas d’évènements dans la période sélectionnée",
"vws_download" => "Télécharger",
"vws_download_title" => "Télécharger un fichier avec ces évènements",
"vws_send_mail" => "Envoyez email",

//changes.php
"chg_select_date" => "Choisir date de début",
"chg_notify" => "Notification",
"chg_days" => "jour(s)",
"chg_added" => "Ajouté",
"chg_edited" => "Modifié",
"chg_deleted" => "Supprimé",
"chg_changed_on" => "Modifié le",
"chg_no_changes" => "Aucune modification.",

//search.php
"sch_define_search" => "Texte à rechercher",
"sch_search_text" => "Rechercher texte",
"sch_event_fields" => "Champs de l’évènement",
"sch_all_fields" => "Tous les champs",
"sch_title" => "Titre",
"sch_description" => "Description",
"sch_venue" => "Lieu",
"sch_user_group" => "Groupe d’utilisateurs",
"sch_event_cat" => "Catégorie de l’évènement",
"sch_all_groups" => "Tous Groupes",
"sch_all_cats" => "Toutes catégories",
"sch_occurring_between" => "Occurrence entre",
"sch_select_start_date" => "Sélectionner la date de début",
"sch_select_end_date" => "Sélectionner la date de fin",
"sch_search" => "Recherche",
"sch_invalid_search_text" => "Texte à rechercher invalide ou trop court",
"sch_bad_start_date" => "Mauvaise date de début",
"sch_bad_end_date" => "Mauvaise date de fin",
"sch_no_results" => "Pas de résultat pour la recherche",
"sch_new_search" => "Nouvelle recherche",
"sch_calendar" => "Retour au calendrier",
"sch_extra_field1" => "Complément 1",
"sch_extra_field2" => "Complément 2",
"sch_sd_events" => "Évenements uniques",
"sch_md_events" => "évènements sur plusieurs jours",
"sch_rc_events" => "évènements répétés",
"sch_instructions" =>
"<h3>Instructions pour rechercher du texte</h3>
<p>La base de données du calendrier peut être utilisée pour rechercher un texte spécifique.</p>
<br><p><b>Rechercher du texte&nbsp;:</b> Le texte sera recherché dans tous les champs sélectionnés
(voir ci-dessous). Pour les caractères a - z la recherche est insensible à la casse (majuscules ou miniscules).</p>
<p>Deux caractères spéciaux peuvent être utilisés&nbsp;:</p>
<ul>
<li>Un point d'interrogation (?) permet de remplacer un caractères dans le texte à rechercher.
Le résultat comportera le nombre de lettres exact dans le texte avec des nuances en fonction de l’emplacement
du (?).<br>
Ex.&nbsp;: « ?e?t » enverra les résultats “vert”, “cent”, “peut”.</li>
<li>Le caractère “asterisk” (*) permet de remplacer une série de caractère dans le texte.<br>
Ex.: « dé*r » enverra le résultat “Décembre”, “dépendre”, “développer”.</li>
</ul>
<br><p><b>Champs de l’évènement&nbsp;:</b> La recherche s’effectue uniquement dans les champs sélectionnés.</p>
<br><p><b>Groupe d’utilisateurs&nbsp;:</b> La recherche s’effectue uniquement sur le groupe d’utilisateurs sélectionné.</p>
<br><p><b>Catégorie de l’évènement&nbsp;:</b> La recherche s’effectue uniquement sur la catégorie sélectionnée.</p>
<br><p><b>Occurrence entre&nbsp;:</b> La date de début et la date de fin sont facultatives.In case of a blank start / end date, the default number of days to search back and ahead will be $1 days and $2 days respectively.</p>
<br><p>Pour éviter les répétitions du même évènement, les résultats de la recherche seront divisés en évènements simples, évènements sur plusieurs jours et évènements répétés.</p>
<p>L’affichage du résultat de la recherche sera dans l’ordre chronologique.</p>",

//thumbnails.php
"tns_man_tnails_instr" => "Instructions de gestion des Vignettes",
"tns_help_general" => "Les images ci-dessous peuvent s’utiliser dans les vues du calendrier en insérant leur nom de fichier dans le champ description de l’évènement ou dans un des compléments. Un nom de fichier image peut être copié dans le presse-papier en cliquant sur la vignette voulue ci-dessous&nbsp;; par suite, dans la fenêtre évènement, on peut insérer le nom de l’image dans un champ en tapant CTRL-V. Sous chaque vignette on trouve&nbsp;: le nom de fichier (sans le préfixe ID utilisateur), la date du fichier et entre crochets la dernière date d’utilisation de la vignette dans le calendrier.",
"tns_help_upload" => "Les Vignettes peuvent être envoyées à partir de votre ordinateur local en sélectionnant le bouton Parcourir. Pour choisir plusieurs fichiers, gardez pressées les touches CTRL ou MAJ tout en sélectionnant (maximum 20 à la fois). Les fichiers de types suivants sont acceptés&nbsp;: $1. Les vignettes de taille supérieure à $2 × $3 pixels (larg. × haut.) seront automatiquement réduites.",
"tns_help_delete" => "Les Vignettes ayant une croix rouge dans le coin supérieur gauche peuvent être supprimés en cliquant sur cette croix. Les vignettes sans croix rouge ne peuvent pas être supprimés, parce qu’elles sont encore utilisées après le $1. Attention&nbsp;: les vignettes supprimées ne peuvent être récupérées&nbsp;!",
"tns_your_tnails" => "Vos vignettes",
"tns_other_tnails" => "Autres vignettes",
"tns_man_tnails" => "Gestion des Vignettes",
"tns_sort_by" => "Trié par",
"tns_sort_order" => "Ordre de tri",
"tns_search_fname" => "Fichier à chercher",
"tns_upload_tnails" => "Ajouter des vignettes",
"tns_name" => "nom",
"tns_date" => "date",
"tns_ascending" => "ascendant",
"tns_descending" => "descendant",
"tns_not_used" => "Pas utilisé",
"tns_infinite" => "infini",
"tns_del_tnail" => "Supprimer la vignette",
"tns_tnail" => "Vignette",
"tns_deleted" => "supprimée",
"tns_tn_uploaded" => "vignette(s) publiées",
"tns_overwrite" => "écraser si existe déjà",
"tns_tn_exists" => "vignette existante – pas publiée",
"tns_upload_error" => "erreur d’envoi",
"tns_no_valid_img" => "n’est pas une image valide",
"tns_file_too_large" => "fichier trop grand",
"tns_resized" => "réduit",
"tns_resize_error" => "erreur de réduction",

//contact.php
"con_msg_to_admin" => "Message à l’Administrateur",
"con_from" => "De",
"con_name" => "Nom",
"con_email" => "Email",
"con_subject" => "Objet",
"con_message" => "Message",
"con_send_msg" => "Envoyer message",
"con_fill_in_all_fields" => "Veuillez remplir tous les champs",
"con_invalid_name" => "Nom invalide",
"con_invalid_email" => "Adresse email invalide",
"con_no_urls" => "Aucun lien web n’est permis dans le message",
"con_mail_error" => "Problème Email. Le message n’a pas pu être envoé. Veillez réessayer plus tard.",
"con_con_msg" => "Message de contact à partir du calendrier",
"con_thank_you" => "Merci pour votre message au calendrier",
"con_get_reply" => "Vous recevrez une réponse à votre message dès que possible",
"con_date" => "Date",
"con_your_msg" => "Votre message",
"con_your_cal_msg" => "Votre message au calendrier",
"con_has_been_sent" => "a été envoyé à l’administrateur du calendrier",
"con_confirm_eml_sent" => "Un email de confirmation a été envoyé à",

//msglog.php
"msl_search" => "Search",
"msl_date" => "date",
"msl_text" => "text",
"msl_sent_msgs" => "Sent notification messages",
"msl_no_logs_found" => "No message logs found!",
"msl_errors" => "ERRORS OCCURRED! See luxcal log",

//alert.php
"alt_message#0" => "Votre session expirera bientôt !",
"alt_message#1" => "EXPIRATION DE SESSION PHP",
"alt_message#2" => "Redémarrez le calendrier s.v.p.",
"alt_message#3" => "REQUÊTE INVALIDE",

//stand-alone sidebar (lcsbar.php)
"ssb_upco_events" => "évènements à venir",
"ssb_all_day" => "Journée entière",
"ssb_none" => "Pas d’évènements."
);
?>
