<?php
/*
= LuxCal admin interface language file =

La traduction française a été réalisée par Fabiou. Mise à jour et complétée par Gérard.

This file is part of the LuxCal Web Calendar.
*/

$ax = array(

//general
"none" => "Aucun",
"no" => "non",
"yes" => "oui",
"own" => "own",
"all" => "tous",
"or" => "ou",
"back" => "Retour",
"ahead" => "Ahead",
"close" => "Fermer",
"always" => "Toujours",
"at_time" => "à", //date and time separator (e.g. 30-01-2020 @ 10:45)
"times" => "heures",
"cat_seq_nr" => "n° de séquence de la catégorie",
"rows" => "rangées",
"columns" => "colonnes",
"hours" => "heures",
"minutes" => "minutes",
"user_group" => "groupes d’utilisateurs",
"event_cat" => "la catégorie d’évènement",
"email" => "Email",
"telegram" => "Telegram",
"sms" => "SMS",
"id" => "ID",
"username" => "Nom d’utilisateur",
"password" => "Mot de passe",
"public" => "Public",
"logged_in" => "Connecté",
"pw_no_chars" => "<, > and ~ non autorisés dans le mot de passe",

//settings.php - fieldset headers + general
"set_general_settings" => "Calendrier",
"set_navbar_settings" => "Barre de navigation",
"set_event_settings" => "Évènements",
"set_user_settings" => "Utilisateurs",
"set_upload_settings" => "Fichiers joints",
"set_reminder_settings" => "Rappels",
"set_perfun_settings" => "Fonctions périodiques (applicables uniquement si cron actif)",
"set_sidebar_settings" => "Barre latérale autonome (applicable uniquement si utilisée)",
"set_view_settings" => "Vues",
"set_dt_settings" => "Dates et Heures",
"set_save_settings" => "Enregistrer les réglages",
"set_test_mail" => "Test Mail",
"set_mail_sent_to" => "Test mail envoyé à",
"set_mail_sent_from" => "Ce mail de test a été envoyé à partir de la page Réglages de votre calendrier",
"set_mail_failed" => "Sending test mail failed - recipient(s)",
"set_missing_invalid" => "Réglages manquants ou invalides (fond accentué)",
"set_settings_saved" => "Réglages enregistrés",
"set_save_error" => "Erreur Base de données - L’enregistrement des réglages du calendrier a échoué",
"hover_for_details" => "Survoler le texte pour avoir les descriptions complètes",
"default" => "défaut",
"enabled" => "actif",
"disabled" => "inactif",
"pixels" => "pixels",
"warnings" => "Avertissements",
"notices" => "Remarques",
"visitors" => "Visiteurs",
"height" => "Height",
"no_way" => "Vous n’avez pas les droits d’accès pour effectuer cette commande",

//settings.php - general Settings
"versions_label" => "Versions",
"versions_text" => "• Version du calendrier, suivie de la base de données en service<br>• version PHP<br>• version de la base de données",
"calTitle_label" => "Titre du calendrier",
"calTitle_text" => "Affiché dans la barre du haut et utilisé dans les notifications d’email.",
"calUrl_label" => "URL du calendrier",
"calUrl_text" => "Adresse du calendrier de votre site Web. Ex.: https://www.monsite.com/LuxCal/.",
"calEmail_label" => "Adresse email du calendrier",
"calEmail_text" => "Cette adresse email est utilisée pour recevoir les emails de contact et pour transmettre et recevoir les emails de notification.<br>Format&nbsp;: “adresse mail” ou “nom &#8826;adresse mail&#8827;”.",
"logoPath_label" => "Chemin et nom du fichier image logo",
"logoPath_text" => "Si spécifié, un logo s’affichera dans le coin supérieur gauche du calendrier. Si on spécifie aussi un lien vers une page parent (voir ci-dessous), alors le logo sera un hyper-lien vers cette page. L’image du logo doit avoir une hauteur et largeur maximum de 70 pixels.",
"logoXlPath_label" => "Path/name of log-in logo image",
"logoXlPath_text" => "If specified, a logo image of the specified height will be displayed on the Log In page below the Log In form.",
"backLinkUrl_label" => "Lien vers la page parent",
"backLinkUrl_text" => "URL de la page parent. Si spécifié, un bouton Retour sera affiché à gauche de la barre de navigation et pointera sur cette URL.<br>Par exemple, pour retourner à la page qui a lancé le calendrier. Si on a spécifié une adresse de logo (voir ci-dessus), alors le bouton Retour ne sera pas affiché, mais à la place le logo deviendra le lien de retour.",
"timeZone_label" => "Fuseau horaire",
"timeZone_text" => "Fuseau horaire du calendrier, utilisé pour calculer l’heure courante.",
"see" => "voir",
"notifChange_label" => "Envoyer notification des changements dans le calendrier",
"notifChange_text" => "Quand on ajoute, modifie ou supprime un évènement, un message de notification sera envoyé aux destinataires spécifiées.",
"chgRecipList" => "semicolon separated recipient list",
"maxXsWidth_label" => "Taille maxi des petits écrans",
"maxXsWidth_text" => "Pour afficher avec une taille plus petite que le nombre spécifié de pixels, le calendrier s’exécutera dans un mode spécial réactif, omettant certains éléments moins importants.",
"rssFeed_label" => "Lien flux RSS",
"rssFeed_text" => "Si activé : pour les utilisateurs ayant au moins le droit de visibilité, un lien de flux RSS sera visible dans le pied de page du calendrier et sera ajouté dans l’entête des pages HTML du calendrier.",
"logging_label" => "Données du journal",
"logging_text" => "Le calendrier peut enregistrer les erreurs, les avertissements et les remarques, ainsi que les données des visiteurs. Les messages d’erreurs sont toujours enregistrés. L’enregistrement des avertissements et des remarques ainsi que les données des visiteurs peuvent chacun être activés ou désactivés en cochant les cases appropriées. Tous les messages d’erreurs, d’avertissements et de remarques sont enregistrés dans le fichier “logs/luxcal.log” et les données visiteurs vont dans les fichiers “logs/hitlog.log” et “logs/botlog.log”.<br>Note&nbsp;: les erreurs, avertissements et remarques PHP sont enregistrés à un autre endroit, déterminé par votre hébergeur.",
"maintMode_label" => "PHP Mode maintenance",
"maintMode_text" => "Si activé, in the PHP scripts data submitted via the note (message) function and data stored in the 'note' variable seront affichées dans la barre inférieure.",
"reciplist" => "<br>La liste des destinataires peut contenir des noms d’utilisateur, des adresses e-mail, des numéros de téléphone, Telegram chat IDs et des noms de fichiers contenant des destinataires (entre crochets), séparées par des points-virgules. Les fichiers des destinataires contiennent un destinataire par ligne et doivent se trouver dans le dossier “reciplists”. Si l’extension de ces fichiers est omise, l’extension par défaut sera .txt",
"calendar" => "calendrier",
"user" => "utilisateur",
"database" => "base de données",

//settings.php - navigation bar settings
"contact_label" => "Bouton Contact",
"contact_text" => "Si activé, un bouton Contact s’affichera dans le menu latéral. Un clic sur ce bouton ouvrira un formulaire de contact destiné à envoyer un message à l’administrateur du calendrier.",
"optionsPanel_label" => "Menus du panneau Options",
"optionsPanel_text" => "Affichage des menus dans le menu Options.<br>• Le menu calendrier sert à sélectioner un des calendriers installées (applicable uniquement si plusieurs calendriers sont installés).<br>• Le menu vue sert à choisir une des vues du calendrier.<br>• Le menu groupes sert à afficher seulement les évènements créés par les utilisateurs d’un ou plusieurs groupes.<br>• Le menu utilisateurs sert à afficher seulement les évènements créés par un ou plusieurs utilisateurs.<br>• Le menu catégorie sert à afficher seulement les évènements appartenant à une ou plusieurs catégories.<br>• Le menu langue sert à sélectionner la langue de l’utilisateur. (applicable uniquement si plusieurs langues sont installées).<br>Note&nbsp;: Si aucun menu n’est sélectionné, le bouton panneau Options ne sera pas affiché.",
"calMenu_label" => "calendrier",
"viewMenu_label" => "vue",
"groupMenu_label" => "groupes",
"userMenu_label" => "utilisateurs",
"catMenu_label" => "catégories",
"langMenu_label" => "langue",
"availViews_label" => "Vues de calendriers disponibles",
"availViews_text" => "Vues de calendriers disponibles pour les utilisateurs publics ou connectés, exprimées au moyen de numéros de vue séparés par des virgules. Signification des numéros&nbsp;:<br>1 : vue par année<br>2 : vue par mois (7 jours)<br>3 : vue par mois, jours ouvrés<br>4 : vue par semaine (7 jours)<br>5 : vue par semaine, jours ouvrés<br>6 : vue par jour<br>7 : vue des évènements à venir<br>8 : vue des changements<br>9 : vue matricielle (catégories)<br>10 : vue matricielle (utilisateurs)<br>11 : vue diagramme de Gantt",
"viewButtonsL_label" => "Boutons de vues sur la barre de navigation (grand écran)",
"viewButtonsS_label" => "Boutons de vues sur la barre de navigation (petit écran)",
"viewButtons_text" => "Boutons de vues à afficher sur la barre de navigation pour les utilisateurs publics ou connectés, exprimées au moyen de numéros de vue séparés par des virgules.<br>Si un numéro apparaît dans la séquence, le bouton correspondant sera affiché. Si aucun numéro n’est spécifié, aucun bouton de vue ne sera affiché.<br>Signification des numéros&nbsp;:<br>1 : Année<br>2 : Mois complet<br>3 : Mois ouvré<br>4 : Semaine complète<br>5 : Semaine ouvrée<br>6 : Jour<br>7 : À venir<br>8 : Modifications<br>9 : Matrices-C<br>10 : Matrices-U<br>11 : Diagramme de Gantt.<br>L’ordre des numéros détermine l’ordre d’affichage des boutons.<br>Par exemple: “4,2” signifie&nbsp;: afficher les boutons “Semaine complète” et “Mois complet”.",
"defaultViewL_label" => "Vue par défaut au démarrage (grand écran)",
"defaultViewL_text" => "Vue par défaut au démarrage pour les utilisateurs publics ou connectés sur grand écran.<br>Choix recommandé&nbsp;: Mois.",
"defaultViewS_label" => "Vue par défaut au démarrage (petit écran)",
"defaultViewS_text" => "Vue par défaut au démarrage pour les utilisateurs publics ou connectés sur petit écran.<br>Choix recommandé&nbsp;: Évènement à venir.",
"language_label" => "Langue par défaut (public user)",
"language_text" => "For public (not logged in) users the language set for the browser user interface will be used for the calendar as well. If the browser language is not a valid calendar language, this default language will be used.<br>Note: Les fichiers <i>ai-{langue}.php</i>, <i>ui-{langue}.php</i>, <i>ug-{langue}.php</i> et <i>ug-layout.png</i> doivent être présents dans le répertoire <i>lang/</i>.<br>• <i>{langue}</i> = nom de la langue à utiliser.<br>Les noms des fichiers doivent être en minuscules&nbsp;!",
"birthday_cal_label" => "PDF Birthday Calendar",
"birthday_cal_text" => "If enabled, an option 'PDF File - Birthday' will appear in the Side Menu for users with at least 'view' rights. See the admin_guide.html - Birthday Calendar for further details",
"sideLists_label" => "Approve, Todo, Upcoming lists",
"sideLists_text" => "If enabled, an option to show the respective list will appear in the Side Menu. The 'Events to be approved' list will only be available for users with at least 'manager' rights.",
"toapList_label" => "To approve list",
"todoList_label" => "To do list",
"upcoList_label" => "Upcoming list",

//settings.php - events settings
"privEvents_label" => "Utiliser les évènements privés",
"privEvents_text" => "Les évènements privés sont seulement visibles à l’utilisateur qui a créé l’évènement.<br>• Actif&nbsp;: Les utilisateurs peuvent créer des évènements privés.<br>• Défaut&nbsp;: lors de l’ajout d’évènements, la case à cocher “Privé” dans la fenêtre évènements sera cochée par défaut.<br>• Toujours&nbsp;: lors de l’ajout d’évènements, ils seront systématiquement privés, la case à cocher “Privé” dans la fenêtre évènement ne sera pas affichée.",
"venueInput_label" => "Specifying venues",
"venueInput_text" => "In the Event window specifying a venue can be done either by typing the venue or by selecting a venue from a pre-defined list. If Free text is selected, the user can type the venue, if List is selected the user can select a venue from a drop-down list and when Both is selected, the user can choose between the two.<br> When a drop-down list is used, the 'files' folder must contain a file called venues.txt with one venue per line.",
"timeDefault_label" => "Ajouter évènements : défaut heure",
"timeDefault_text" => "When adding events, in the Event window the default way the event time fields appear in the event form can be set as follows:<br>• show times: The start and end time fields are shown and ready to be completed<br>• all day: The All Day check box is checked, no start and end time fields are shown<br>• no time: The No Time check box is checked, no start and end time fields are shown.",
"evtDelButton_label" => "Voir le bouton [Supprimer] dans la fenêtre évènement",
"evtDelButton_text" => "• Inactif : le bouton [Supprimer] dans la fenêtre évènement ne sera pas visible. Les utilisateurs avec un droit d’édition ne pourront pas effacer les évènements.<br>• Actif : le bouton [Supprimer] dans la fenêtre évènement sera visible à tous les utilisateurs.<br>• Gestionnaire : le bouton [Supprimer] dans la fenêtre évènement ne sera visible qu’aux utilisateurs ayant au moins un droit “Gestionnaire”.",
"eventColor_label" => "Couleur de l’évènement basé sur",
"eventColor_text" => "Chaque évènement, affiché dans les différentes vues, peut être associé à la couleur du groupe de son créateur ou à la couleur de la catégorie de l’évènement.",
"defVenue_label" => "Lieu par défaut",
"defVenue_text" => "On peut spécifier ici un lieu qui sera proposé par défaut quand on ajoutera de nouveaux évènements avec le formulaire d’évènements.",
"xField1_label" => "Champ optionnel 1",
"xField2_label" => "Champ optionnel 2",
"xFieldx_text" => "Champ optionnel de texte. Si ce champ est inclus dans le panneau d’évènement ci-dessous, le champ sera ajouté comme champ de texte de format libre dans le formulaire d’évènement et dans les évènements affichés dans toutes les vues et les pages du calendrier.<br>Nom du champ : nom du champ optionel (max. 15 caractères de long). Ex.: “Adresse email”, “Site Web”, “N° de téléphone”.<br>• Droits utilisateur minimum&nbsp;: le champ ne sera visible qu’aux utilisateurs ayant les droits sélectionnés ou au-dessus.",
"evtWinSmall_label" => "Fenêtre d’évènement réduite",
"evtWinSmall_text" => "Si cette case est cochée, quand on ajoute ou édite des évènements, la fenêtre d’évènement affichera un sous-ensemble des champs de saisie. Pour voir tous les champs, il faudra cliquer sur un flèche.",
"emojiPicker_label" => "Emoji picker in Event window",
"emojiPicker_text" => "When enabled, in the Event Add/Edit window an emoji picker can be selected to add emoji to the event title and to the description fields.",
"mapViewer_label" => "URL d’afficheur de carte",
"mapViewer_text" => " Si un URL d’afficheur de carte est spécifié, une adresse dans le champ Lieu de l’évènement, entourée par des signes « ! », sera affichée sous la forme d’un bouton Adresse dans les vues du calendrier. En survolant ce bouton, le texte de l’adresse sera affiché et si on clique, une nouvelle fenêtre s’ouvrira avec l’adresse affichée sur la carte.<br>L’URL complet d’un afficheur de carte doit être spécifié, à la fin duquel une adresse peut être ajoutée.<br>Exemples :<br> — Google Maps: https://maps.google.com/maps?q=<br> — OpenStreetMap: https://www.openstreetmap.org/search?query=<br>Si ce champ est laissé vide, les adresses dans le champ Lieu ne seront pas affichées sous la forme d’un bouton.",
"evtDrAndDr_label" => "Event drag and drop",
"evtDrAndDr_text" => "When enabled, in Year view, Month view and in the mini calendar on the side panel, events can be moved or copied from one day to an other day by means of Drag and Drop. If 'manager' is selected, only users with at least manager rights can use this feature. See the admin_guide.html for a detailed description.",
"free_text" => "Free text",
"venue_list" => "Venue list",
"both" => "Both",
"xField_label" => "Nom du champ",
"show_times" => "show times",
"check_ald" => "all day",
"check_ntm" => "no time",
"min_rights" => "Droits utilisateur minimum",
"no_color" => "sans couleur",
"manager_only" => "gestionnaire",

//settings.php - user account settings
"selfReg_label" => "Auto-inscription",
"selfReg_text" => "Permet aux utilisateurs de s’inscrire eux-mêmes et d’accéder au calendrier.<br>— Groupe d’utilisateurs auquel seront assignés ceux qui s’inscrivent eux-mêmes.",
"selfRegQA_label" => "Question/réponse en auto-inscription",
"selfRegQA_text" => "Quand l’auto-inscription est active, pendant le processus d’auto-inscription cette question sera posée à l’utilisateur, qui ne sera admis que si la réponse donnée est correcte. Si le champ question est laissé blanc, aucune question ne sera posée.",
"selfRegNot_label" => "Notification d’auto-inscription",
"selfRegNot_text" => "Envoi d’une notification à l’adresse email du calendrier pour prévenir qu’un nouvel utilisateur s’est inscrit.",
"restLastSel_label" => "Restaurer les dernières sélections de l’utilisateur",
"restLastSel_text" => "Les dernières sélections de l’utilisateur (les réglages du panneau Option) seront enregistrées et, quand l’utilisateur revisitera le calendrier, les valeurs seront restaurées. If the user does not log in during the specified number of days, the values will be lost.",
"answer" => "réponse",
"exp_days" => "jours",
"view" => "consulter",
"post_own" => "ajouter/éditer",
"post_all" => "ajouter/éditer tout",
"manager" => "ajouter/gérer",

//settings.php - view settings
"templFields_text" => "Signification des chiffres&nbsp;:<br>1 = Champ lieu<br>2 = Champ catégorie<br>3 = Champ description<br>4 = Champ optionnel 1 (voir voir ci-dessous)<br>5 = Champ optionnel 2 (voir voir ci-dessous)<br>6 = Email de notification (seulement si une notification a été requise)<br>7 = Date/heure d’ajout/modification, et le(s) utilisateur(s) associé(s)<br>8 = Fichiers pdf, image ou video affichés comme hyperliens.<br>— L’ordre des chiffres détermine l’ordre d’affichage des champs.",
"evtTemplate_label" => "Modèles d’évènement",
"evtTemplate_text" => "On spécifie, au moyen d’une suite de chiffres, les champs d’évènements à afficher dans les vues générales, les vues des évènements à venir et les info-bulles d’évènements du calendrier.<br>Si un chiffre est spécifié, le champ correspondant sera affiché.",
"evtTemplPublic" => "Utilisateur public",
"evtTemplLogged" => "Utilisateur connecté",
"evtTemplGen" => "Vue générale",
"evtTemplUpc" => "Vue À venir",
"evtTemplPop" => "Info-bulles",
"sortEvents_label" => "Trier les évènements sur l’horaire ou la catégorie",
"sortEvents_text" => "Dans les différentes vues, les évènements peuvent être triés sur les critères suivants&nbsp;:<br>• les heures des évènements<br>• le n° de séquence de la catégorie de l’évènement",
"yearStart_label" => "Mois de début dans la vue Année",
"yearStart_text" => "L’affichage de la vue Année commencera toujours par le mois dont la valeur aura été choisie (1 - 12) et le nombre de mois affiché dépendra toujours de la valeur saisie dans le nombre de colonnes et de rangées. Le changement d’affichage se fera lors du passage du 1er jour du mois choisi de l’année suivante.<br>La valeur 0 a une fonction particulière: le mois débutant l’année sera fonction de la date du jour et tombera dans la première rangée des mois.",
"YvRowsColumns_label" => "Nombre de mois et colonnes dans la vue Année",
"YvRowsColumns_text" => "Nombre de rangées de 4 mois affichées sur une année.<br>Choix recommandé : 4, ce qui permet d’afficher 16 mois d’affilée.<br>Nombre de mois affichés dans chaque rangée dans la vue Année.<br>Choix recommandé: 3 ou 4.",
"MvWeeksToShow_label" => "Semaines à afficher dans la vue Mois",
"MvWeeksToShow_text" => "Nombre de semaines à afficher par mois.<br>Choix recommandé: 10, ce qui affiche 2 mois 1/2.<br>Les valeurs 0 et 1 ont un sens spécial : 0 = afficher un mois exactement - les jours précédents et suivants restent en blanc.<br>1 = afficher un mois exactement - afficher les évènements des jours précédents et suivants.",
"XvWeeksToShow_label" => "Semaines à afficher dans la vue matricielle",
"XvWeeksToShow_text" => "Nombre de semaines à afficher dans la vue matricielle.",
"GvWeeksToShow_label" => "Semaines à afficher dans la vue Diagramme de Gantt",
"GvWeeksToShow_text" => "Nombre de semaines à afficher dans la vue Diagramme de Gantt.",
"workWeekDays_label" => "Jours ouvrables de la semaine",
"workWeekDays_text" => "Jours colorisés comme jours ouvrables dans les vues du calendrier, et par exemple dans les semaines des vues Mois ouvrables et Semaines ouvrables.<br>Entrer le n° de chaque jour ouvré.<br>Ex. : 12345 : Lundi à Vendredi<br>Les jours absents sont considérés comme des jours de week-end.",
"weekStart_label" => "Premier jour de la semaine",
"weekStart_text" => "Entrer le n° du premier jour de la semaine.",
"lookBackAhead_label" => "Jours à afficher pour les évènements à venir",
"lookBackAhead_text" => "Nombre de jour à afficher dans la vue “évènement à venir”, dans la liste “À Faire” et dans les RSS feeds.",
"searchBackAhead_label" => "Default days to search back/ahead",
"searchBackAhead_text" => "When no dates are specified on the Search page, these are the default number of days to search back and to search ahead.",
"dwStartEndHour_label" => "Heure de début et de fin dans les vues Jour et Semaine",
"dwStartEndHour_text" => "Choix de l’heure du début et du fin d’une journée d’évènements.<br>Les valeurs par défaut est de 6h à 18h, ce qui évite de perdre de la place entre minuit et 6 heures, et 18 heures et minuit.<br>La fenêtre de saisie d’heure commencera/finira elle aussi à ces heures-là.",
"dwTimeSlot_label" => "Tranche horaire dans les vues Jour et Semaine",
"dwTimeSlot_text" => "L’intervalle de temps et la hauteur de la tranche horaire pour les vues Jour et Semaine. Cette valeur, ainsi que l’heure de début et l’heure de fin (voir ci-dessus) déterminera le nombre de lignes affichées dans les vues Jour et Semaine.",
"dwTsInterval" => "Intervalle de temps",
"dwTsHeight" => "Hauteur",
"evtHeadX_label" => "Disposition des évènements dans les vues Mois, Semaine et Jour",
"evtHeadX_text" => "Gabarits avec substituts de champs d’évènements à afficher. On peut utiliser les substituts suivants&nbsp;:<br>#ts - heure de début<br>#tx - heures de début et de fin<br>#e - titre de l’évènement<br>#o - propriétaire de l’évènement<br>#v - lieu<br>#lv - lieu avec le libellé “Lieu:” devant<br>#c - catégorie<br>#lc - catégorie avec le libellé “Catégorie:” devant<br>#âge (voire la note ci-dessous)<br>#x1 - champ supplémentaire 1<br>#lx1 - champ supplémentaire 1 précédé du libellé venant de la page des Réglages<br>#x2 - champ supplémentaire 2<br>#lx2 - champ supplémentaire 2 précédé du libellé venant de la page Réglages<br>#/ - saut de ligne<br>Les champs sont affichés dans l’ordre spécifié. Les caractères autres que les substituts seront inchangés et seront affichés tels quels.<br>Les balises HTML sont permises dans le gabarit, par exemple &lt;b&gt;#e&lt;/b&gt;.<br>On peut utiliser le caractère | pour diviser le gabarit en sections. Si à l’intérieur d’une section tous les paramètres # résulte en une chaîne vide, la section entière sera invisible.<br>Note: The age is shown if the event is part of a category with 'Repeat' set to 'every year' and the year of birth in parentheses is mentioned somewhere in either the event description field or in one of the extra fields.",
"monthView" => "Vue Mois",
"wkdayView" => "Vue Semaine/Jour",
"ownerTitle_label" => "Afficher l’auteur de l’évènement devant le titre de l’évènement",
"ownerTitle_text" => "Dans les différentes vues, afficher l’auteur de l’évènement devant le titre de l’évènement.",
"showSpanel_label" => "Panneau latéral pour les différentes vues",
"showSpanel_text" => "Dans les différentes vues, à droite du calendrier principal, les éléments suivants peuvent être affichés&nbsp;:<br>• un mini-calendrier pour pouvoir regarder en arrière ou en avant sans avoir à changer la date du calendrier principal<br>• une image de décoration correspondant au mois courant<br>• une zone d’informations pour poster des messages ou annonces pour une certaine période.<br>>Per item a comma-separated list of view numbers can be specified, for which the side panel should be shown.<br>Possible view numbers:<br>0: all views<br>1 : Année<br>2 : Mois complet<br>3 : Mois ouvré<br>4 : Semaine complète<br>5 : Semaine ouvrée<br>6 : Jour<br>7 : À venir<br>8 : Modifications<br>9 : Matrices-C<br>10 : Matrices-U<br>11 : Diagramme de Gantt.<br>If 'Today' is checked, the side panel will always use the date of today, otherwise it will follow the date selected for the main calendar.<br>Voir admin_guide.html pour les détails du panneau latéral.",
"spMiniCal" => "Mini-calendrier",
"spImages" => "Images",
"spInfoArea" => "Zone d’informations",
"spToday" => "Today",
"topBarDate_label" => "Show current date on top bar",
"topBarDate_text" => "Enable/disable the display of the current date on the calendar top bar in the calendar views. If displayed, the current date can be clicked to reset the calendar to the current date.",
"showImgInMV_label" => "Afficher les images dans la vue Mois",
"showImgInMV_text" => "Active/désactive l’affichage dans la vue Mois des images ajoutées dans un des champs de description d’évènements. Si activé, des vignettes seront affichées dans les cellules Jour&nbsp;; si désactivé, elles seront affichées dans les boîtes de survol.",
"urls" => "liens URL",
"emails" => "liens email",
"monthInDCell_label" => "Nom du mois dans chaque cellule jour",
"monthInDCell_text" => "Dans la vue Mois, affiche pour chaque jour les 3 ou 4 premières lettres du mois.",
"scrollDCell_label" => "Use scrollbar in day cells",
"scrollDCell_text" => "If in month view a day cell is too small, rather than increasing the day cell height, a vertical scrollbar will appear.",

//settings.php - date/time settings
"dateFormat_label" => "Format de date (jj mm aaaa)",
"dateFormat_text" => "Format des dates d’évènements dans les vues du calendrier et les champs de saisie.<br>Caractères possibles : y = année, m = mois et d = jour.<br>Un caractère non alphabétique peut servir de séparateur et sera inséré tel quel.<br>Exemples :<br>y-m-d ► 2024-06-23<br>m.d.y ► 06.23.2024<br>d/m/y ► 23/06/2024",
"dateFormat_expl" => "par exemple y.m.d ► 2024.06.23",
"MdFormat_label" => "Format de date (jj mois)",
"MdFormat_text" => "Format des dates composées du mois et du jour.<br>Caractères possibles : M = mois en lettres, d = jour en chiffres.<br>Un caractère non alphabétique peut servir de séparateur et sera inséré tel quel.<br>Exemples :<br>d M ► 12 Avril<br>M, d ► Juillet, 14",
"MdFormat_expl" => "Exemple : d M ► 23 juin",
"MdyFormat_label" => "Format de date (dd mois aaaa)",
"MdyFormat_text" => "Format des dates composées de jour, mois et année.<br>Caractères possibles : d = jour en chiffres, M = mois en lettres, y = année en chiffres.<br>Un caractère non alphabétique peut servir de séparateur et sera inséré tel quel.<br>Exemples :<br>d M y ► 23 Juin 2024<br>M d, y ► Juillet 8, 2024",
"MdyFormat_expl" => "Exemple : d M y ► 23 Juin 2024",
"MyFormat_label" => "Format de date (mois aaaa)",
"MyFormat_text" => "Format des dates composées de mois et année.<br>Caractères possibles : M = mois en lettres, y = année en chiffres.<br>Un caractère non alphabétique peut servir de séparateur et sera inséré tel quel.<br>Exemples :<br>M y ► Juin 2024<br>y - M ► 2024 - Juillet",
"MyFormat_expl" => "Exemple : M y ► Juin 2024",
"DMdFormat_label" => "Format de date (jour jj mois)",
"DMdFormat_text" => "Format des dates composées du jour de semaine, du jour et du mois.<br>Caractères possibles : WD = jour de semaine en lettres, d = jour du mois en chiffres, M = mois en lettres.<br>Un caractère non alphabétique peut servir de séparateur et sera inséré tel quel.<br>Exemples :<br>WD d M ► Vendredi 23 Juin<br>WD, M d ► Samedi, Juillet 14",
"DMdFormat_expl" => "Exemple : WD, d M ► Mardi, 6 juin",
"DMdyFormat_label" => "Format de date (jour dd mois yyyy)",
"DMdyFormat_text" => "Format des dates composées du jour de semaine, du jour, du mois et de l’année.<br>Caractères possibles : WD = jour de semaine en lettres, d = jour du mois en chiffres, M = mois en lettres, y = année en chiffres.<br>Un caractère non alphabétique peut servir de séparateur et sera inséré tel quel.<br>Exemples :<br>WD d M y ► Vendredi 23 Juin 2024<br>WD - M d, y ► Lundi - Juillet 16, 2024",
"DMdyFormat_expl" => "Exemple : WD, d M y ► Vendredi, 23 Juin 2024",
"timeFormat_label" => "Format de l’heure (hh mm)",
"timeFormat_text" => "Format de l’heure des évènements dans les vues du calendrier et les champs de saisie.<br>Caractères possibles : h = heures, H = heures avec zéro initial, m = minutes, a = am/pm (optionnel), A = AM/PM (optionnel).<br>Un caractère non alphabétique peut servir de séparateur et sera inséré tel quel.<br>Exemples :<br>h:m ► 18:35<br>h.m a ► 6.35 pm<br>H:mA ► 06:35PM",
"timeFormat_expl" => "Exemple : h:m ► 22:35 et h:mA ► 10:35PM",
"weekNumber_label" => "Afficher les n° des semaines",
"weekNumber_text" => "Permet d’afficher ou non les numéros des semaines dans les vues pertinentes",
"time_format_us" => "12 heures AM/PM",
"time_format_eu" => "24 heures",
"sunday" => "Dimanche",
"monday" => "Lundi",
"time_zones" => "FUSEAUX HORAIRES",
"dd_mm_yyyy" => "jj-mm-aaaa",
"mm_dd_yyyy" => "mm-jj-aaaa",
"yyyy_mm_dd" => "aaaa-mm-jj",

//settings.php - file uploads settings
"maxUplSize_label" => "Taille maximum des fichiers joints",
"maxUplSize_text" => "Taille maximum permise pour téléverser des fichiers joints ou des vignettes.<br>Note : la plupart des installations php ont ce maximum établi à 2 MB (fichier php_ini) ",
"attTypes_label" => "Types des fichiers joints",
"attTypes_text" => "Liste des types de fichiers joints valides à téléverser, séparés par des virgules (Ex.&nbsp;: « .pdf,.jpg,.gif,.png,.mp4,.avi »)",
"tnlTypes_label" => "Types des fichiers vignettes",
"tnlTypes_text" => "Liste des types de fichiers vignettes valides à téléverser, séparés par des virgules (Ex.&nbsp;: « .jpg,.jpeg,.gif,.png »)",
"tnlMaxSize_label" => "Vignettes - taille maximum",
"tnlMaxSize_text" => "Taille maximum des images-vignettes. Si on envoie des vignettes plus grandes, elles seront automatiquement réduites à la taille maximum.<br>Note&nbsp;: les vignettes trop hautes étendront les cellules des jours dans la vue Mois, ce qui peut causer des effets non voulus.",
"tnlDelDays_label" => "Plage de suppression des vignettes",
"tnlDelDays_text" => "Si une vignette est utilisée depuis ce nombre de jours, on ne peut pas la supprimer.<br>La valeur 0 signifie qu’on ne peut pas supprimer la vignette.",
"days" =>"jours",
"mbytes" => "MO",
"wxhinpx" => "larg. &times; haut. en pixels",

"services_label" => "Services Messages",
"services_text" => "Services disponibles pour envoyer des rappels d’évènements. Si un service est désactivé, la section correspondente de la fenêtre des évènements sera supprimée. Si aucun service n’est sélectionné, aucun rappel d’évènement ne sera envoyé.",
"msgLogging_label" => "Notification message logging",
"msgLogging_text" => "When checked, the notification messages sent are logged in the messages.log file. The 'weeks' field specifies how long the logged messages should be kept",
"smsCarrier_label" => "Modèle SMS",
"smsCarrier_text" => "Le modèle SMS sert à compiler l’adresse email de la passerelle SMS&nbsp;: ppp#sss@carrier, dans laquelle...<ul><li>ppp : chaîne de texte facultative à ajouter devant le n° de téléphone</li><li># : substituant pour le n° de mobile du destinataire (le calendrier remplacera le # par le n° de téléphone)</li><li>sss : chaîne de texte facultative à ajouter derrière le n° de téléphone, par ex. un nom d’utilisateur et un mot de passe, exigés par certains opérateurs</li><li>@ : séparateur</li><li>carrier: adresse de l’opérateur (par ex. mail2sms.com)</li></ul>Exemples de modèles : #@xmobile.com, 0#@carr2.int, #myunmypw@sms.gway.net.",
"smsCountry_label" => "Code pays du SMS",
"smsCountry_text" => "Si la passerelle SMS est située dans un pays différent de celui du calendrier, alors il faut spécifier le code du pays où le calendrier est utilisé.<br>Cocher si le préfixe ‘+’ ou ‘00’ est exigé.",
"smsSubject_label" => "Modèle de l’objet SMS",
  "smsSubject_text" => "Si on le spécifie, le texte de ce modèle sera copié dans le champ objet des messages email SMS envoyés à l’opérateur. Le texte peut contenir le caractère #, qui sera remplacé par le n° de téléphone du calendrier ou le nom du propriétaire de l’évènement (selon le règlage ci-dessus).<br>Exemple : “DUTELEPHONE=#”.",
"smsAddLink_label" => "Ajouter lien rapport d’évènement au SMS",
"smsAddLink_text" => "Si on coche, un lien vers le rapport d’évènements sera ajouté à chaque SMS. En ouvrant ce lien sur leur mobile, les destinataires pourront voir les détails de l’évènement.",
"maxLenSms_label" => "Longueur maximum du message SMS",
"maxLenSms_text" => "Les messages SMS sont envoyés encodés en utf-8. Les messages jusqu’à 70 caractères de long se résoudront en un seul message SMS&nbsp;; les messages dépassant 70 charactères, avec beaucoup de caractères Unicode, pourront être scindés en plusieurs messages.",
"calPhone_label" => "N° de téléphone du calendrier",
"calPhone_text" => "N° de téléphone utilisé comme ID d’expéditeur lors de l’envoi des messages de notification SMS.<br>Format : libre, maxi. 20 chiffres (certains pays requièrent un n° de téléphone, d’autres acceptent les caractères alphabétiques).<br>Si aucun service SMS n’est actif ou si aucun gabarit SMS n’a été défini, ce champ peut être laissé à blanc.",
"notSenderEml_label" => "Add 'Reply to' field to email",
"notSenderEml_text" => "When selected, notification emails will contain a 'Reply to' field with the email address of the event owner, to which the recipient can reply.",
"notSenderSms_label" => "Expéditeur des SMS de notifications",
"notSenderSms_text" => "Quand le Calendrier envoie des SMS de rappel, l’ID du message SMS peut être soit le n° de téléphone du Calendrier, soit celui de l’utilisateur qui a créé l’évènement.<br>Si “utilisateur” est sélectionné et qu’un compte utilisateur n’a pas de n° de téléphone spécifié, le n° de téléphone du Calendrier sera pris.<br>Dans le cas du n° de téléphone de l’utilisateur, le destinataire peut répondre au message.",
"defRecips_label" => "Liste des destinataires par défaut",
"defRecips_text" => "Si spécifié, c’est la liste des destinataires par défaut pour les notifications par mail et/ou par SMS dans la fenêtre évènement. Si ce champ est laissé blanc, le destinataire par défaut sera le propriétaire de l’évènement.",
"maxEmlCc_label" => "Nombre maximum de destinataires par e-mail",
"maxEmlCc_text" => "Normallement, les fournisseurs limitent le nombre de destinatires par e-mail. Quand on envoie des e-mails ou des rappels SMS, si le nombre de destinataires est plus grand que le nombre spécifié ici, l’e-mail sera divisé en plusieurs e-mails, chacun ayant le nombre maximum spécifié de destinataires.",
"emlFootnote_label" => "Reminder email footnote",
"emlFootnote_text" => "Free-format text that will be added as a paragraph to the end of reminder email messages. HTML tags are allowed in the text.",
"mailServer_label" => "Serveur mail",
"mailServer_text" => "Le mail par PHP convient pour des e-mails non authentifiés en petit nombre. Pour un plus grand nombre d’e-mails, ou quand l’authentification est requise, le mail SMTP s’impose.<br>L’usage de SMTP demande un serveur mail SMTP. On doit ensuite spécifier les réglages de configuration à utiliser avec le serveur SMTP.",
"smtpServer_label" => "Nom du serveur SMTP",
"smtpServer_text" => "Si le mail par SMTP est sélectionné, le nom du serveur SMTP doit être spécifié ici. Par exemple, pour le serveur SMTP de gmail&nbsp;: smtp.gmail.com.",
"smtpPort_label" => "Numéro de port SMTP",
"smtpPort_text" => "Si le mail par SMTP est sélectionné, le numéro de port SMTP doit être spécifié ici, par exemple 25, 465 ou 587. Gmail, lui, utilise le port 465.",
"smtpSsl_label" => "SSL (Secure Sockets Layer)",
"smtpSsl_text" => "Si le mail par SMTP est sélectionné, signaler ici si le “secure sockets layer” (SSL) doit être activé. Pour gmail&nbsp;: activé.",
"smtpAuth_label" => "Authentification SMTP",
"smtpAuth_text" => "Si l’authentification SMTP est sélectionnée, le nom d’utilisateur et le mot de passe spécifiés plus loin serviront à authentifier le mail SMTP.<br>Pour gmail, par example, le nom d’utilisateur est la partie de votre adresse email avant l’ @.",
"tlgToken_label" => "Telegram token",
"tlgToken_text" => "Telegram token in the following format: &lt;bot ID&gt;:&lt;bot hash&gt;. For details see installation_guide.html, section Event Notification Messages.",
"cc_prefix" => "Le code du pays commence par le préfixe ‘+’ ou ‘00’",
"weeks" => "Weeks",
"general" => "Général",
"php_mail" => "courriel PHP",
"smtp_mail" => "courriel SMTP (compléter les champs ci-dessous)",

//settings.php - periodic function settings
"cronHost_label" => "Hôte du job cron",
"cronHost_text" => "Spécifie où se trouve le job cron qui démarre périodiquement le script “lcalcron.php”.<br>• local : le job cron s’exécute sur le même serveur que le calendrier<br>• distant : le job cron s’exécute sur un serveur distant ou lcalcron.php est démarré manuellement (tests)<br>• Adresse IP : le job cron s’exécute sur un serveur distant à l’adresse IP spécifiée.",
"cronSummary_label" => "Résumé du job cron à l’Administrateur",
"cronSummary_text" => "Envoyer un résumé du job cron à l’administrateur du calendrier.<br>L’activation est utile seulement si un job cron est activé pour le calendrier.",
"chgSummary_text" => "Nombre de jours précédents à afficher dans le résumé des modifications de calendrier.<br>Si la valeur est à 0 ou s’il n’y a pas de job cron actif, aucun résumé des modifications ne sera envoyé.",
"icsExport_label" => "Exportation journalière des évènements iCal",
"icsExport_text" => "Si activé&nbsp;: Tous les évènements dans la fourchette -1 semaine jusqu’à +1 an seront exportés au format iCalendar dans un fichier .ics dans le dossier “files”.<br>Le nom du fichier sera le nom du calendrier avec les blancs remplacés par des tirets bas. Les anciens fichiers seront écrasés par les nouveaux.",
"eventExp_label" => "Expiration des évènements, en jours",
"eventExp_text" => "Nombre de jours après la date d’expiration de l’évènement avant qu’ìl soit effacé automatiquement.<br>Si zéro ou si pas de tâche cron active, aucun évènement ne sera automatiquement effacé.",
"maxNoLogin_label" => "Nombre de jour maxi entre 2 connexions",
"maxNoLogin_text" => "Si un utilisateur ne s’est pas connecté dans l’intervalle du nombre de jours indiqués, le compte de l’utilisateur sera automatiquement supprimé sauf si la valeur est à 0.",
"local" => "local",
"remote" => "distant",
"ip_address" => "Adresse IP",

//settings.php - mini calendar / side bar settings
"popFieldsSbar_label" => "Champs évènement - info-bulle de la barre latérale",
"popFieldsSbar_text" => "Les champs d’évènement à afficher dans une info-bulle quand on survole un évènement de la barre latérale autonome se spécifient au moyen d’une suite de chiffres.<br>Si aucun champ n’est spécifié, aucune info-bulle ne sera affichée.",
"showLinkInSB_label" => "Montrer les liens dans la barre latérale",
"showLinkInSB_text" => "Afficher les URL à partir de la description d’un évènement comme hyperlien dans la prochaine barre d’évènements",
"sideBarDays_label" => "Jours à afficher dans la barre latérale",
"sideBarDays_text" => "Nombre de jours à afficher pour les évènements de la barre latérale.",

//login.php
"log_log_in" => "Connexion",
"log_remember_me" => "Connexion auto",
"log_register" => "Inscription",
"log_change_my_data" => "Modifier mes données",
"log_save" => "Modifier",
"log_done" => "Done",
"log_un_or_em" => "Nom d’utilisateur ou adresse email",
"log_un" => "Nom d’utilisateur",
"log_em" => "Adresse email",
"log_ph" => "N° de tél. mobile",
"log_tg" => "Telegram chat ID",
"log_answer" => "Votre réponse",
"log_pw" => "Mot de passe",
"log_expir_date" => "Account expiration date",
"log_account_expired" => "This account has expired",
"log_new_un" => "Nouveau nom d’utilisateur",
"log_new_em" => "Nouvel email",
"log_new_pw" => "Nouveau mot de passe",
"log_con_pw" => "Mot de passe de confirmation",
"log_pw_msg" => "Voici votre détails pour vous connecter à",
"log_pw_subject" => "Votre mot de passe",
"log_npw_subject" => "Votre nouveau mot de passe",
"log_npw_sent" => "Votre nouveau mot de passe a été envoyé",
"log_registered" => "Inscription réussie - Votre mot de passe a été envoyé par email",
"log_em_problem_not_sent" => "Problème email - votre mot de passe n’a pu être envoyé",
"log_em_problem_not_noti" => "Problème email - pux pas notifier l’administrateur",
"log_un_exists" => "Nom d’utilisateur existe déjà",
"log_em_exists" => "Adresse email existe déjà",
"log_un_invalid" => "Nom d’utilisateur non valide (minimum 2 caractères : A-Z, a-z, 0-9, et _-.) ",
"log_em_invalid" => "Adresse email non valide",
"log_ph_invalid" => "N° de tél. mobile invalide",
"log_tg_invalid" => "Invalid Telegram chat ID",
"log_sm_nr_required" => "SMS: mobile phone number required",
"log_tg_id_required" => "Telegram: chat ID required",
"log_sra_wrong" => "Réponse incorrecte à la question",
"log_sra_wrong_4x" => "Vous avez répondu incorrectement 4 fois. Réessayez dans 30 minutes",
"log_un_em_invalid" => "Nom d’utilisateur/adresse email non valide",
"log_un_em_pw_invalid" => "Nom d’utilisateur/adresse email ou mot de passe non valide",
"log_pw_error" => "Les mots de passe ne concordent pas",
"log_no_un_em" => "Entrez votre nom d’utilisateur/adresse email",
"log_no_un" => "Entrez votre nom d’utilisateur",
"log_no_em" => "Entrez votre adresse email",
"log_no_pw" => "Entrez votre mot de passe",
"log_no_rights" => "Connexion refusée&nbsp;: Vous n’avez pas les droits d’accès - Contacter l’Adminitrateur.",
"log_send_new_pw" => "Envoyer nouveau mot de passe",
"log_new_un_exists" => "Nouveau nom d’utilisateur existe déjà",
"log_new_em_exists" => "Nouvelle adresse email existe déjà",
"log_ui_language" => "Langue de l’utilisateur",
"log_new_reg" => "Inscription de nouvel utilisateur",
"log_date_time" => "Date / heure",
"log_time_out" => "Temps expiré",

//categories.php
"cat_list" => "Liste des Catégories",
"cat_edit" => "Modifier",
"cat_delete" => "Supprimer",
"cat_add_new" => "Ajouter une nouvelle catégorie",
"cat_add" => "Ajouter",
"cat_edit_cat" => "Modifier la catégorie ",
"cat_sort" => "Trier par nom",
"cat_cat_name" => "Nom de la catégorie",
"cat_symbol" => "Symbole",
"cat_symbol_repms" => "Symbole de la catégorie (remplace mini-carré)",
"cat_symbol_eg" => "Ex. : A, X, ♥, ⛛",
"cat_matrix_url_link" => "Lien URL (affiché dans vue matricielle)",
"cat_seq_in_menu" => "Ordre d’affichage dans le menu",
"cat_cat_color" => "Couleur de la catégorie",
"cat_text" => "Texte",
"cat_background" => "Fond",
"cat_select_color" => "Choix de la couleur",
"cat_subcats" => "Sous-<br>catégories",
"cat_subcats_opt" => "Nombre de sous-catégories (optionnel)",
"cat_copy_from" => "Copy from",
"cat_eml_changes_to" => "Send event changes to",
"cat_url" => "URL",
"cat_name" => "Nom",
"cat_subcat_note" => "Note that the currently existing subcategories may already be used for events",
"cat_save" => "Enregistrer les modifications",
"cat_added" => "Catégorie ajoutée",
"cat_updated" => "Catégorie mise à jour",
"cat_deleted" => "Catégorie supprimée",
"cat_not_added" => "Catégorie non ajoutée",
"cat_not_updated" => "Catégorie non mise à jour",
"cat_not_deleted" => "Catégorie non supprimée",
"cat_nr" => "N°",
"cat_repeat" => "Périodicité",
"cat_every_day" => "chaque jour",
"cat_every_week" => "chaque semaine",
"cat_every_month" => "chaque mois",
"cat_every_year" => "chaque année",
"cat_overlap" => "Chevaucht<br>permis<br>(écart)",
"cat_need_approval" => "Les évènements nécessitent<br>une approbation",
"cat_no_overlap" => "Aucun chevauchement permis",
"cat_same_category" => "même catégorie",
"cat_all_categories" => "toutes catégories",
"cat_gap" => "écart",
"cat_ol_error_text" => "Message d’erreur si chevauchement",
"cat_no_ol_note" => "Notez que les évènements déjà existants ne sont pas vérifiés et en conséquence peuvent se chevaucher",
"cat_ol_error_msg" => "chevauchement d’évènement&nbsp - choisir une autre heure",
"cat_no_ol_error_msg" => "Message d’erreur de chevauchement manquant",
"cat_duration" => "Durée <br>d’évént<br>! = fixe",
"cat_default" => "défault (pas d’heure de fin)",
"cat_fixed" => "fixe",
"cat_event_duration" => "Durée d’évènement par défaut",
"cat_olgap_invalid" => "Écart de chevauchement invalide",
"cat_duration_invalid" => "Durée d’évènement invalide",
"cat_no_url_name" => "Nom de lien URL manquant",
"cat_invalid_url" => "Lien URL invalide",
"cat_day_color" => "Couleur<br>du jour",
"cat_day_color1" => "Couleur du jour (vue année/matricielle)",
"cat_day_color2" => "Couleur du jour (vue mois/semaine/jour)",
"cat_approve" => "Les évènements nécessitent une approbation",
"cat_check_mark" => "Case à cocher",
"cat_not_list" => "Notify<br>list",
"cat_label" => "libellé",
"cat_mark" => "texte",
"cat_name_missing" => "Le nom de la catégorie est manquant",
"cat_mark_label_missing" => "Libellé manquant",

//users.php
"usr_list_of_users" => "Liste des utilisateurs",
"usr_name" => "Nom d’utilisateur",
"usr_email" => "Adresse email",
"usr_phone" => "N° de téléphone mobile",
"usr_phone_br" => "N° de téléphone<br>mobile",
"usr_tg_id" => "Telegram chat ID",
"usr_tg_id_br" => "Telegram<br>chat ID",
"usr_not_via" => "Notify via",
"usr_not_via_br" => "Notify<br>via",
"usr_language" => "Langue",
"usr_ui_language" => "Langue de l’utilisateur",
"usr_group" => "Groupe",
"usr_password" => "Mot de passe",
"usr_expir_date" => "Account expiration date",
"usr_select_exp_date" => "Select expiration date",
"usr_blank_none" => "blank: no expiration",
"usr_expires" => "Expires",
"usr_edit_user" => "Edition du profil",
"usr_add" => "Ajouter nouvel utilisateur",
"usr_edit" => "Modifier",
"usr_delete" => "Supprimer",
"usr_login_0" => "Premier login",
"usr_login_1" => "Dernier login",
"usr_login_cnt" => "Connexions",
"usr_add_profile" => "Ajouter",
"usr_upd_profile" => "Enregistrer le profil",
"usr_if_changing_pw" => "A préciser seulement si vous voulez changer de mot de passe",
"usr_pw_not_updated" => "Mot de passe pas mis à jour",
"usr_added" => "Utilisateur ajouté",
"usr_updated" => "Utilisateur mis à jour",
"usr_deleted" => "Utilisateur supprimé",
"usr_not_deleted" => "Utilisateur non supprimé",
"usr_cred_required" => "Nom d’utilisateur/adresse email et mot de passe obligatoire",
"usr_name_exists" => "Nom d’utilisateur déjà existant",
"usr_email_exists" => "Adresse email existe déjà",
"usr_un_invalid" => "Nom d’utilisateur non valide (minimum 2 caractères : A-Z, a-z, 0-9, et _-.) ",
"usr_em_invalid" => "Adresse email non valide",
"usr_ph_invalid" => "Invalid mobile phone number",
"usr_tg_invalid" => "Invalid Telegram chat ID",
"usr_xd_invalid" => "Invalid account expiration date",
"usr_cant_delete_yourself" => "Vous ne pouvez pas vous supprimer",
"usr_go_to_groups" => "Aller aux groupes",
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
"grp_list_of_groups" => "Liste des groupes d’utilisateurs",
"grp_name" => "Nom du Groupe",
"grp_priv" => "Droits des utilisateurs",
"grp_categories" => "Catégories d’évèn.",
"grp_all_cats" => "toutes",
"grp_rep_events" => "Répéter<br>évènements",
"grp_m-d_events" => "Évènements<br>multi-jours",
"grp_priv_events" => "Évènements<br>privés",
"grp_upload_files" => "Publier<br>fichiers",
"grp_tnail_privs" => "Privilèges<br>vignettes",
"grp_priv0" => "Pas de droits d’accès",
"grp_priv1" => "Voir le Calendrier",
"grp_priv2" => "Ajouter/Modifier en propre",
"grp_priv3" => "Ajouter/Modifier tout",
"grp_priv4" => "Ajouter/Modifier + gestionnaire",
"grp_priv9" => "Administrateur",
"grp_may_post_revents" => "Peut poster des évènements répétés",
"grp_may_post_mevents" => "Peut poster des évènements<br>sur plusieurs jours",
"grp_may_post_pevents" => "Peut poster des évènements privés",
"grp_may_upload_files" => "Peut téléverser des fichiers",
"grp_tn_privs" => "Privilèges sur les vignettes",
"grp_tn_privs00" => "aucun",
"grp_tn_privs11" => "voit tout",
"grp_tn_privs20" => "gère en propre",
"grp_tn_privs21" => "g. propre/v. tout",
"grp_tn_privs22" => "gère tout",
"grp_edit_group" => "Modifier Groupe",
"grp_sub_to_rights" => "Sujet aux droits d’utilisateurs",
"grp_view" => "Voir",
"grp_add" => "Ajouter",
"grp_edit" => "Modifier",
"grp_delete" => "Supprimer",
"grp_add_group" => "Ajouter Groupe",
"grp_upd_group" => "Enregistrer Groupe",
"grp_added" => "Groupe ajouté",
"grp_updated" => "Groupe mis à jour",
"grp_deleted" => "Groupe supprimé",
"grp_not_deleted" => "Groupe non supprimé",
"grp_in_use" => "Groupe en service",
"grp_cred_required" => "Nom de groupe, Droits et Categories obligatoire",
"grp_name_exists" => "Nom de groupe déjà existant",
"grp_name_invalid" => "Nom de groupe non valide (minimum 2 caractères : A-Z, a-z, 0-9, et _-.) ",
"grp_check_add" => "At least one check box in the Add column must be checked",
"grp_background" => "Couleur du fond",
"grp_select_color" => "Sélectionner la Couleur",
"grp_invalid_color" => "Format de couleur invalide (#XXXXXX - X = HEX-valeur)",
"grp_go_to_users" => "Aller aux utilisateurs",

//texteditor.php
"edi_text_editor" => "Edition Texte d'information",
"edi_file_name" => "File name",
"edi_save" => "Sauver le texte",
"edi_backup" => "Restaurer le texte",
"edi_select_file" => "Select file",
"edi_info_text" => "Information text",
"edi_pub_recips" => "Public recipients",
"edi_recips_list" => "Recipients list",
"edi_new_recips_list" => "New recipients list",
"edi_no_file_name" => "No file name specified",
"edi_no_text" => "Pas de texte",
"edi_confirm_changes" => "The text changes have not been saved\\nDo you want to continue?", //don't remove '\\n'
"edi_text_saved" => "Texte sauvé dans le fichier $1",

//database.php
"mdb_dbm_functions" => "Choix des fonctions",
"mdb_noshow_tables" => "Pas d’accès aux tables",
"mdb_noshow_restore" => "Aucun fichier de sauvegarde sélectionné ou le fichier est trop grand pour être téléchargé",
"mdb_file_not_sql" => "Source backup file should be an SQL file (extension '.sql')",
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
"mdb_compact" => "Compacter la base de données",
"mdb_compact_table" => "Compactage de la table",
"mdb_compact_error" => "Erreur",
"mdb_compact_done" => "Terminé",
"mdb_purge_done" => "Suppression définitive des évènements effacés depuis plus de 30 jours",
"mdb_backup" => "Sauvegarder la base de données",
"mdb_backup_table" => "Sauvegarde de la table",
"mdb_backup_file" => "Fichier de sauvegarde",
"mdb_backup_done" => "Terminé",
"mdb_records" => "enregistrements",
"mdb_restore" => "Restaurer la base de données",
"mdb_restore_table" => "Restaurer table",
"mdb_inserted" => "enregistrements insérés",
"mdb_db_restored" => "Base de données restaurée",
"mdb_db_upgraded" => "Base de données mise à niveau",
"mdb_no_bup_match" => "Le fichier de sauvegarde ne correspond pas à la version du calendrier.<br>Base de données non restaurée.",
"mdb_events" => "évènements",
"mdb_delete" => "supprimer",
"mdb_undelete" => "restaurer",
"mdb_between_dates" => "ayant lieu entre",
"mdb_deleted" => "évènements supprimés",
"mdb_undeleted" => "évènements restaurés",
"mdb_file_saved" => "Fichier sauvegardé.",
"mdb_file_name" => "Nom du fichier ",
"mdb_start" => "Démarrer",
"mdb_no_function_checked" => "Aucune fonction sélectionnée",
"mdb_write_error" => "Erreur d’écriture du fichier de sauvegarde.<br>Vérifier les permissions du répertoire “files”",

//import/export.php
"iex_file" => "Sélectionner un fichier",
"iex_file_name" => "Nom du fichier de destination",
"iex_file_description" => "Description du fichier iCal",
"iex_filters" => "Filtres",
"iex_export_usr" => "Export des Profils utilisateurs",
"iex_import_usr" => "Import des Profils utilisateurs",
"iex_upload_ics" => "Importer un fichier iCal",
"iex_create_ics" => "Créer un fichier iCal",
"iex_tz_adjust" => "Ajustements de fuseaux horaires",
"iex_upload_csv" => "Importer un fichier CSV",
"iex_upload_file" => "Importer le fichier",
"iex_create_file" => "Exporter le fichier",
"iex_download_file" => "Charger le fichier",
"iex_fields_sep_by" => "Champs séparés par",
"iex_birthday_cat_id" => "ID de la Catégorie",
"iex_default_grp_id" => "ID du groupe utilisateurs par défaut",
"iex_default_cat_id" => "ID de la Catégorie par défaut",
"iex_default_pword" => "Mot de passe par défaut",
"iex_if_no_pw" => "Si aucun mot de passe n’est spécifié",
"iex_replace_users" => "Remplacer les utilisateurs existants",
"iex_if_no_grp" => "si aucun groupe d’utilisateurs n’est trouvé",
"iex_if_no_cat" => "Laisser vide si la catégorie n’existe pas",
"iex_import_events_from_date" => "Importer les évènements à partir du",
"iex_no_events_from_date" => "Pas d’évènement trouvé de la date spécifiée",
"iex_see_insert" => "voir liste à droite",
"iex_no_file_name" => "Nom de fichier manquant",
"iex_no_begin_tag" => "Fichier iCal invalide (étiquette BEGIN manquante)",
"iex_bad_date" => "Bad date",
"iex_date_format" => "Format date évènement",
"iex_time_format" => "Format heure évènement",
"iex_number_of_errors" => "Nombre d’erreurs dans la liste",
"iex_bgnd_highlighted" => "fond surligné",
"iex_verify_event_list" => "Vérifier la liste des évènements, corriger les erreurs et cliquer",
"iex_add_events" => "Ajouter les évènements dans la base de données",
"iex_verify_user_list" => "Vérifier la liste des utilisateurs, corriger les erreurs possibles et cliquer",
"iex_add_users" => "Ajouter des utilisateurs à la base de données",
"iex_select_ignore_birthday" => "Cocher les cases “ID Anniversaire” et “Supprimer” comme demandé",
"iex_select_ignore" => "Cocher la case “Supprimer” pour ignorer un évènement",
"iex_check_all_ignore" => "(Dé)cocher toutes les cases Ignore",
"iex_title" => "Titre",
"iex_venue" => "Lieu",
"iex_owner" => "Utilisateur",
"iex_category" => "Catégorie",
"iex_date" => "Date début",
"iex_end_date" => "Date fin",
"iex_start_time" => "Heure début",
"iex_end_time" => "Heure fin",
"iex_description" => "Description",
"iex_repeat" => "Répéter",
"iex_birthday" => "ID Anniversaire",
"iex_ignore" => "Supprimer",
"iex_events_added" => "évènements ajoutés",
"iex_events_dropped" => "évènements sautés (déjà présents)",
"iex_users_added" => "utilisateurs ajoutés",
"iex_users_deleted" => "utilisisateurs supprimés",
"iex_csv_file_error_on_line" => "Erreur fichier CSV ligne",
"iex_between_dates" => "Occurence entre",
"iex_changed_between" => "Ajouté/modifié entre",
"iex_select_date" => "Sélectionner la date",
"iex_select_start_date" => "Sélectionner la date du début",
"iex_select_end_date" => "Sélectionner la date de fin",
"iex_group" => "Groupe utilisateurs",
"iex_name" => "Bom d’utilisateur",
"iex_email" => "Adresse e-mail",
"iex_phone" => "N° de téléphone",
"iex_msgID" => "Chat ID",
"iex_lang" => "Langue",
"iex_pword" => "Mot de passe",
"iex_all_groups" => "tous les groupes",
"iex_all_cats" => "toutes",
"iex_all_users" => "tous",
"iex_no_events_found" => "Pas d’évènement trouvé",
"iex_file_created" => "Fichier créé",
"iex_write error" => "Erreur d’écriture du fichier d’export.<br>Vérifier les permissions du répertoire “files”",
"iex_invalid" => "invalide",
"iex_no_user_profiles" => "Pas de profils utilisateurs trouvés",
"iex_in_use" => "déjà utilisé",

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
"sty_css_intro" =>  "Les valeurs spécifiées sur cette page doivent se conformer aux standards CSS",
"sty_preview_theme" => "Aperçu du Thème",
"sty_preview_theme_title" => "Aperçu du thème affiché dans le calendrier",
"sty_stop_preview" => "Arrêter l’aperçu",
"sty_stop_preview_title" => "Arrêter l’aperçu du thème affiché dans le calendrier",
"sty_save_theme" => "Enregistrer Thème",
"sty_save_theme_title" => "Enregistrer dans la base de données le thème affiché",
"sty_backup_theme" => "Sauvegarder Thème",
"sty_backup_theme_title" => "Sauvegarder le thème à partir de la base de données vers un fichier",
"sty_restore_theme" => "Restaurer Thème",
"sty_restore_theme_title" => "Restaurer le thème à partir d’un fichier pour l’afficher",
"sty_default_luxcal" => "Thème LuxCal par défaut",
"sty_close_window" => "Fermer la fenêtre",
"sty_close_window_title" => "Fermer cette fenêtre",
"sty_theme_title" => "Titre du Thème",
"sty_general" => "Général",
"sty_grid_views" => "Vues à grille",
"sty_hover_boxes" => "Info-bulles",
"sty_bgtx_colors" => "Couleurs arrière-plan/texte",
"sty_bord_colors" => "Couleurs des bordures",
"sty_fontfam_sizes" => "Famille/Taille des polices",
"sty_font_sizes" => "Taille des polices",
"sty_miscel" => "Divers",
"sty_background" => "Arrière-plan",
"sty_text" => "Texte",
"sty_color" => "Couleur",
"sty_example" => "Exemple",
"sty_theme_previewed" => "Mode aperçu — On peut maintenant naviguer dans le calendrier. Sélectionner “Arrêter l’aperçu” pour terminer.",
"sty_theme_saved" => "Thème enregistré dans la base de données",
"sty_theme_backedup" => "Thème sauvegardé à partir de la base de données dans le fichier&nbsp;:",
"sty_theme_restored1" => "Thème restauré à partir du fichier&nbsp;:",
"sty_theme_restored2" => "Presser sur “Enregistrer le Thème” pour enregistrer le thème dans la base de données",
"sty_unsaved_changes" => "ATTENTION – Changements non enregistrés !\\nSi on ferme la fenêtre, les modifications seront perdues.", //don't remove '\\n'
"sty_number_of_errors" => "Nombre d’erreurs dans la liste",
"sty_bgnd_highlighted" => "arrière-plan surligné",
"sty_XXXX" => "calendrier général",
"sty_TBAR" => "barre supérieure du calendrier",
"sty_BHAR" => "barres, entêtes et traits",
"sty_BUTS" => "boutons",
"sty_DROP" => "menus déroulants",
"sty_XWIN" => "fenêtres contextuelles",
"sty_INBX" => "dialogues insérés",
"sty_OVBX" => "boites recouvrantes",
"sty_BUTH" => "boutons - au survol",
"sty_FFLD" => "champs de formulaires",
"sty_CONF" => "message de confirmation",
"sty_WARN" => "message d’avertissement",
"sty_ERRO" => "message d’erreur",
"sty_HLIT" => "texte surligné",
"sty_FXXX" => "famille de police de base",
"sty_SXXX" => "taille de police de base",
"sty_PGTL" => "titres des pages",
"sty_THDL" => "grandes en-têtes de tables",
"sty_THDM" => "en-têtes moyennes de tables",
"sty_DTHD" => "en-têtes de dates",
"sty_SNHD" => "en-têtes de sections",
"sty_PWIN" => "fenêtres contextuelles",
"sty_SMAL" => "petit texte",
"sty_GCTH" => "haut de la cellule jour - survol",
"sty_GTFD" => "entête de cellule, 1er jour du mois",
"sty_GWTC" => "colonne n° semaine / heure",
"sty_GWD1" => "jour de semaine mois 1",
"sty_GWD2" => "jour de semaine mois 2",
"sty_GWE1" => "weekend mois 1",
"sty_GWE2" => "weekend mois 2",
"sty_GOUT" => "hors mois",
"sty_GTOD" => "cellule d’aujourd’hui",
"sty_GSEL" => "cellule du jour sélectionné",
"sty_LINK" => "liens URL et email",
"sty_CHBX" => "case à cocher “à faire”",
"sty_EVTI" => "titre de l’évènement dans les vues",
"sty_HNOR" => "évènement normal",
"sty_HPRI" => "évènement privé",
"sty_HREP" => "évènement répété",
"sty_POPU" => "info-bulle",
"sty_TbSw" => "ombre de la barre supérieure (0&nbsp;: non, 1&nbsp;: oui)",
"sty_CtOf" => "marge du contenu",

//lcalcron.php
"cro_sum_header" => "RÉSUMÉ DU JOB CRON",
"cro_sum_trailer" => "FIN DU RESUMÉ",
"cro_sum_title_eve" => "évènements PÉRIMÉS",
"cro_nr_evts_deleted" => "Nombre d’évènements supprimés",
"cro_sum_title_not" => "RAPPELS",
"cro_no_reminders_due" => "Pas de dates de notification attendues",
"cro_due_in" => "attendu dans",
"cro_due_today" => "Attendu aujourd’hui",
"cro_days" => "Jour(s)",
"cro_date_time" => "Date / heure",
"cro_title" => "Titre",
"cro_venue" => "Lieu",
"cro_description" => "Description",
"cro_category" => "Catégorie",
"cro_status" => "Statut",
"cro_none_active" => "No reminders or periodic services active",
"cro_sum_title_use" => "COMPTES UTILISATEURS EXPIRÉS",
"cro_nr_accounts_deleted" => "Nombre de comptes utilisateurs supprimés",
"cro_no_accounts_deleted" => "Pas de compte utilisateur supprimé",
"cro_sum_title_ice" => "évènementS EXPORTÉS",
"cro_nr_events_exported" => "Nombre d’évènements exportés au format iCalendar dans le fichier",

//messaging.php
"mes_no_msg_no_recip" => "Pas envoyé, aucun destinataire trouvé",

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
"<h3>Instructions d'édition - Messages d'Information</h3>
<p>Quand l'option est activée dans la page Réglages, les messages d'information 
dans la zone de texte de gauche seront affichés dans les vues du calendrier dans 
un panneau latéral juste à côté de la page principale du calendrier. 
Les messages peuvent intégrer des balises HTML et des styles en ligne. 
Des exemples avec des différentes possibilités de messages d'information peuvent 
être trouvés dans le fichier 'sidepanel/samples/info.txt'.</p>
<p>Les messages d'information peuvent être affichés en fonction d'une date de 
début et d'une date de fin.
Chaque message d'information doit être précédé d'une ligne de commande avec la 
période d'affichage spécifiée entouré du caractères ~ . Le texte placé avant la 
ligne de commande commençant par le caractère ~ peut être utilisé comme note 
personnelle (ou remarque) mais ne sera pas affiché dans la zone d'information.
</p><br>
<p>Format des dates (départ et fin): ~m1.d1-m2.d2~, ou m1 et d1 sont le mois et 
jour de départ et m2 et d2 sont le mois et le jour de fin. Si d1 est absent, le 
date commencera au 1er du mois. Si d2 est absent, le date finira le dernier jour 
de m2. Si m2 et d2 sont absents, le dernier jour de m1 est pris en compte.</p>
<p>Exemples:<br>
<b>~4~</b>: Tout le mois d'Avril<br>
<b>~2.10-2.14~</b>: 10 - 14 Février<br>
<b>~6-7~</b>: 1er Juin - 31 Juillet<br>
<b>~12.15-12.25~</b>: 15 - 25 Décembre<br>
<b>~8.15-10.5~</b>: 15 Août - 5 Octobre<br>
<b>~12.15~</b>: 15 Décembre - 31 Décembre</p><br>
<p>Suggestion: Commencez par créer une copie de sauvegarde (Backup text).</p>",

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
"<h3>Instructions pour gérer la Base de données</h3>
<p>Sur cette page, on peut choisir les fonctions suivantes&nbsp;:</p>
<h6>Compacter la base de données</h6>
<p>Lorsqu’un utilisateur efface un évènement, il est marqué comme “effacé”, mais il
n’est pas supprimé de la base de données. La fonction “Compacter la base de données”
le supprime physiquement et libére l’espace qu’il occupait.</p>
<h6>Sauvegarder la base de données</h6>
<p>Cette fonction permet de créer une sauvegarde de toute la base de données (tables,
structures et données) dans un format “.sql”. La sauvegarde est enregistrée dans le
répertoire <strong>files/</strong> avec comme nom&nbsp;:
<kbd>dump-cal-lcv-aaammjj-hhmmss.sql</kbd> (dans lequel “cal” = ID du calendrier, “lcv” =
version du calendrier et “aaaammjj-hhmmss” = année, mois, jour, heure, minutes et secondes).</p>
<p>Ce fichier de sauvegarde peut être utilisé pour recréer les tables, les structures et les données
de la base de données, grâce à la fontion de restauration décrite ci-dessous ou en utilisant par exemple l’outil
<strong>phpMyAdmin</strong>, qui est fourni par la plupart des hôtes web.</p>
<h6>Restaurer la base de données</h6>
<p>La fonction Restaurer will restore the calendar database with the contents of
the uploaded backup file (file type .sql). If your .sql file is larger than 2MB you may have to modify the <b>upload_max_filesize</b> and <b>post_max_size</b> variables in the php.ini file, or split your .sql file in several smaller files. See the admin_guide.html section 3 for a detailed explanation.</p>
<p>Quand on restaure la base de données, TOUTES LES DONNÉES PRÉSENTES SERONT PERDUES&nbsp;!</p>
<h6>évènements</h6>
<p>Cette fonction supprimera ou restaurera les évènements ayant lieu entre les
dates spécifiées. Si une date est laissée en blanc, il n’y a pas de limite&nbsp;; donc si les deux dates sont
laissées en blanc, TOUS LES évènementS SERONT SUPPRIMÉS&nbsp;!</p><br>
<p>IMPORTANT&nbsp;: quand on compacte une base de données (voir ci-dessus), les évènements sont
définitivement retirés de la base et on ne peut plus du tout les restaurer&nbsp;!</p>",

"xpl_import_csv" =>
"<h3>Instructions pour importer un fichier CSV</h3>
<p>Ce formulaire est utilisé pour importer dans votre calendrier LuxCal un fichier
<strong>CSV</strong> (Comma Separated Values, valeurs séparées par des virgules) contenant des
évènements créés par un autre calendrier comme par ex. MS Outlook.</p>
<p>L’ordre des colonnes dans le fichier CSV doit être impérativement comme suit&nbsp;:
titre, lieu, ID catégorie (voir ci-dessous), date début, date fin, heure début,
heure fin et description. La 1ère ligne du fichier CSV, utilisée par le nom des
colonnes, est ignorée.</p>
<h6>&nbsp;&nbsp;&nbsp;Exemples de fichier CSV</h6>
<p>Des exemples de fichier CSV se trouvent dans le répertoire “files” de LuxCal.</p>
<h6>&nbsp;&nbsp;&nbsp;Séparateur de champs</h6>
Le séparateur de champs peut être n’importe quel caractère, par exemple la virgule, le point-virgule, etc.
Le séparateur de champs doit être unique
et ne peut pas faire partie du texte, des nombres ou des dates dans les champs.
<h6>&nbsp;&nbsp;&nbsp;Format de date et heure</h6>
<p>Le format de la date et de l’heure de l’évènement côté gauche doit être le même
que le format de la date et de l’heure du fichier CSV.</p>
<p>If no start time (blank) is present, the event will be shown as a 'no time' event 
in the calendar. If the start time is 00:00 or 12:00am, the event will be shown as 
an 'all day' event in the calendar.</p>
<h6>&nbsp;&nbsp;&nbsp;Liste des Catégories</h6>
<p>Le calendrier utilise un numéro d’identification (ID) spécifique à chaque
catégorie. Les ID des catégories dans le fichier CSV doivent correspondre aux
catégories utilisées dans le calendrier LuxCal ou à défaut être vides.</p>
<p>Si dans la prochaine étape, vous voulez affecter des évènements en tant
qu’“anniversaire”, la catégorie <strong>ID Anniversaire</strong> doit être
identique à l’ID de la catégorie ci-dessous.</p>
<p class='hired'>Attention&nbsp;: n’importez pas plus de 100 évènements à la fois&nbsp;!</p>
<p>Voici les catégories actuellement définies dans votre calendrier&nbsp;:</p>",

"xpl_import_user" =>
"<h3>Instructions d’Import de profils utilisitateurs</h3>
<p>Ce formulaire sert à importer un fichier texte CSV (Comma Separated Values, valeurs séparées par virgules) contenant
des données de profils utilisateurs dans le calendrier LuxCal.</p>
<p>Pour traiter correctement les caractères spéciaux, le fichier CSV doit être encodé en UTF-8.</p>
<h6>Séparateur de champs</h6>
<p>Le séparateur de champ peut être n’importe quel caractère, par exemple la virgule, le point-virgule, etc.
Le caractère séparateur de champs doit être unique
et ne doit pas se trouver dans le texte des champs.</p>
<h6>ID du groupe d’utilisateurs par défaut</h6>
<p>Si dans le fichier CSV un ID de groupe d’utilisateurs a été laissé en blanc,
l’ID du groupe
d’utilisateurs par défaut sera pris.</p>
<h6>Mot de passe par défaut</h6>
<p>Si dans le fichier CSV un mot de passe utilisateur a été laissé en blanc, le mot de passe
spécifié par défaut sera pris.</p>
<h6>Remplacer les utilisateurs existants</h6>
<p>Si la case “Remplacer les utilisateurs existants” a été cochée, tous les utilisateurs existants,
sauf l’utilisateur public et l’administrateur, seront supprimés avant d’importer
le prifils utilisateurs.</p>
<br>
<h6>Exemples de fichiers de profils utilisateurs</h6>
<p>Des exemples de fichiers CSV (.csv) de profils utilisateurs se trouvent dans le dossier ”!luxcal-toolbox/” de
votre installation LuxCal.</p>
<h6>Champs du fichier CSV</h6>
<p>L’ordre des colonnes doit être celui de la liste ci-dessous. Si la première ligne du fichier contient
des en-têtes de colonnes, elle sera ignorée.</p>
<ul>
<li>ID du groupe d’utilisateurs&nbsp;: doit correspondre aux groupes d’utilisateurs utilisés dans votre calendrier (voir
la table ci-dessous). Si blanc, l’utilisateur sera mis dans le groupe spécifié par défaut.</li>
<li>Nom d’utilisateur&nbsp;: obligatoire</li>
<li>Adresse e-mail&nbsp;: obligatoire</li>
<li>Numéro de mobile&nbsp;: optionnel</li>
<li>Telegram chat ID: optionnel</li>
<li>Langue interface&nbsp;: optionnelle. Ex.&nbsp;: English, Dansk. Si blanc, la langue par défaut spécifiée
dans la page Réglages sera prise.</li>
<li>Mot de passe&nbsp;: optionnel. Si blanc, le mot de passe par défaut sera pris.</li>
</ul>
<p>Les champs vides sont à indiquer par deux apostrophes.
Les champs vides à la fin de chaque ligne peuvent être omis.</p>
<p class='hired'>Attention&nbsp;: Ne pas importer plus de 60 profils utilisateurs à la fois&nbsp;!</p>
<h6>Table des ID de groupes d’utilisateurs</h6>
<p>Dans votre calendrier, les groupes d’utilisateurs suivants sont définis&nbsp;:</p>",

"xpl_export_user" =>
"<h3>Instructions d’Export de profils utilisitateurs</h3>
<p>Ce formulaire sert à extraire et exporter les <strong>Profils Utilisateurs</strong> à partir du calendrier LuxCal.</p>
<p>Les fichiers seront créés dans le dossier “files/” sur le serveur avec le
nom spécifié et le format Comma Separated Value (.csv, Valeurs séparées par virgules).</p>
<h6>Nom du fichier destination</h6>
Si non spécifié, le nom par défaut sera
le nom du calendrier suivi du suffixe “_users”. L’extension du nom de fichier sera
automatiquement <b>.csv</b>.</p>
<h6>Groupe d’utilisateurs</h6>
Seule les profils utilisateurs du groupe sélectionné sera
exporté. Si “tous les groupes” est choisi, les profils utilisateur dans le fichier destination
seront triés sur les groupes</p>
<h6>Séparateur de champs</h6>
<p>Le séparateur de champs peut être n’importe quel caractère, par exemple la virgule, le point-virgule, etc.
Le séparateur de champs doit être unique
et ne peut pas faire partie du texte.</p><br>
<p>Les fichiers de même nom existants dans le dossier “files/” sur le serveur seront
écrasés par le nouveau fichier.</p>
<p>L’ordre des colonnes dans le fichier destination sera&nbsp;: ID du groupe, nom de l’utilisateur,
addresse e-mail, numéro de téléphone mobile, langue et mot de passe.<br>
<b>Note&nbsp;:</b> Les mots de passe des profils utilisateurs exportés sont cryptés et ne
peuvent pas être décryptés.</p><br>
<p>Quand on <b>télécharge</b> le fichier .csv exporté, la date et l’heure en cours seront
ajoutées au nom du fichier réléchargé.</p><br>
<h6>Exemples de fichiers de Profils utilisateurs</h6>
<p>Des exemples de fichiers de profils utilisateurs (extension .csv) se trouvent dans le dossier “!luxcal-toolbox/”
de votre téléchargement LuxCal.</p>",

"xpl_import_ical" =>
"<h3>Instructions pour importer un fichier iCalendar</h3>
<p>Ce formulaire est utilisé pour importer dans votre calendrier LuxCal un fichier
<strong>iCalendar</strong> contenant des évènements.</p>
<p>Le contenu du fichier à importer doit se conformer au standard d’Internet
Engineering Task Force
[<u><a href='https://tools.ietf.org/html/rfc5545' target='_blank'>RFC5545 standard</a></u>].</p>
<p>Seuls les évènements sont importés; les autres composants iCal (À faire,
Jounal, Libre/Occupé, Alarme et zone de temps) sont ignorés.</p>
<h6>Exemples de fichier iCal</h6>
<p>Des exemples de fichier iCalendar se trouvent dans le répertoire “!luxcal-toolbox/” du
téléchargement LuxCal.</p>
<h6>Ajustements de fuseaux horaires</h6>
<p>Si votre calendrier comporte des évènements d’un différent fuseau horaire at que les dates/heures
doivent être ajustées au fuseau du calendrier, alors cochez “Ajustements de fuseaux horaires”.</p>
<h6>Liste des Catégories</h6>
<p>Le calendrier utilise un numéro d’identification (ID) spécifique à chaque
catégorie. Les ID des catégories dans le fichier iCalendar doivent correspondre
aux catégories utilisées dans le calendrier LuxCal ou à défaut être vides.</p>
<p class='hired'>Attention&nbsp;: n’importez pas plus de 100 évènements à la fois&nbsp;!</p>
<p>Voici les catégories actuellement définies dans votre calendrier&nbsp;:</p>",

"xpl_export_ical" =>
"<h3>Instructions pour exporter vers un fichier iCalendar</h3>
<p>Ce formulaire est utilisé pour extraire et exporter les évènements du calendrier
LuxCal dans un fichier <strong>iCalendar</strong>.</p>
<p>Le <b>nom du fichier iCal</b> (sans extension) est facultatif. Le fichier créé est sauvegardé
dans le répertoire “files/” du serveur avec un nom de fichier spécifique
ou avec le nom du calendrier. L’extension du fichier sera <b>.ics</b>.
Si un fichier existe déjà dans le répertoire “files/” du serveur avec le même nom, il sera
écrasé par le nouveau fichier.</p>
<p>La <b>description du fichier iCal</b> (ex.: “Réunions 2024”) est facultative.
Si elle existe, elle sera ajoutée à l’en-tête du fichier iCal exporté.</p>
<p><b>Filtres : </b>Les évènements à extraire peuvent être filtrés par&nbsp;:</p>
<ul>
<li>Propriétaire</li>
<li>Catégorie</li>
<li>Date début</li>
<li>Date d’ajout/modification</li>
</ul>
<p>Chaque filtre est facultatif. Les dates “occurence entre” vides équivalent respectivement à -1 an et +1
an. Une date “ajouté/modifié entre” vide signifie&nbsp;: aucune limite.</p>
<br>
<p>Le contenu du fichier à exporter doit se conformer au standard de l’Internet
Engineering Task Force
[<u><a href='https://tools.ietf.org/html/rfc5545' target='_blank'>RFC5545 standard</a></u>]</p>.
<p>Lorsqu’on <b>télécharge</b> le fichier ical exporté, la date et l’heure sont ajoutées au nom
du fichier téléchargé.</p>
<h6>Exemples de fichier iCal</h6>
<p>Des exemples de fichier iCalendar se trouvent dans le répertoire “!luxcal-toolbox/” de
votre téléchargement de LuxCal.</p>",

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
