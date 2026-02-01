<?php
/*
= LuxCal on-line user guide =

La traduction française a été réalisée par Fabiou. Mise à jour et complétée par Gérard.

This file is part of the LuxCal Web Calendar.
*/

?>
<div style="margin:0 20px">
<div class="floatR">
<img src="lang/ug-layout.png" alt="LuxCal page layout"><br>
<span class="hired">a</span> : barre du titre&nbsp;&nbsp;<span class="hired">b</span> : barre de navigation&nbsp;&nbsp;<span class="hired">c</span> : jour
</div>
<h3>Table des Matières</h3>
<ol>
<li><p><a href="#ov">Vue d’ensemble</a></p></li>
<li><p><a href="#li">Connexion</a></p></li>
<li><p><a href="#co">Options du calendrier</a></p></li>
<li><p><a href="#cv">Vues du calendrier</a></p></li>
<li><p><a href="#ts">Recherche de texte</a></p></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li><p><a href="#ae">Ajouter/Éditer/Supprimer un évènement</a></p></li>
<?php } ?>
<li><p><a href="#lo">Déconnexion</a></p></li>
<?php if ($usr['privs'] > 3) { //if manager/administrator ?>
<li><p><a href="#ca">Menu Administration du calendrier</a></p></li>
<?php } ?>
<li><p><a href="#al">À propos de LuxCal</a></p></li>
</ol>
</div>
<div class="clear">
<br>
<ol>
<li id="ov"><h3>Vue d’ensemble</h3>
<p>Le calendrier de LuxCal fonctionne sur un serveur web et peut être consulté et administré par l’intermédiaire de votre navigateur web.</p>
<p>La barre supérieure montre le titre de votre calendrier, la date du jour et le nom de l’utilisateur en cours.
	La barre de navigation contient plusieurs menus déroulants et des liens permettant de naviguer, de se connecter/déconnecter, d’ajouter un nouvel évènement et de choisir les différentes fonctions d’Administrateur. Les menus et liens sont activés en fonction des droits d’accès que possède l’utilisateur. En-dessous de la barre de navigation, les diverses possibilités de vues du calendrier seront affichées.</p>
<br></li>
<li id="li"><h3>Connexion</h3>
<p>Si l’administrateur a donné la possibilité à l’utilisateur public de voir le calendrier, il n’est pas nécessaire de
se connecter pour le consulter.</p>
<p>Pour ouvrir une session, cliquer sur “Connexion” à l’extrême droite de la barre de navigation. Entrez
soit votre nom d’utilisateur, soit votre adresse email, et le mot de passe reçu de votre administrateur et cliquez sur le bouton
“Connexion”. Si vous cocher la case “Connexion auto” avant
	de cliquer sur le bouton “Connexion”, à la prochaine visite au calendrier, vous serez automatiquement connecté.
	Si vous avez oublié votre mot de passe, saisissez votre nom d’utilisateur ou votre adresse e-mail puis
saisissez ce que vous croyez être votre mot de passe.
	Ensuite, cliquez sur le bouton “Envoyer nouveau mot de passe”. Recommencer la connexion avec le nouveau mot de passe que vous aurez reçu sur votre adresse email.</p>
<p>Vous pouvez changer votre non d’utilisateur, votre adresse email ou votre mot de passe en cliquant sur
“Modifier mes données” puis en complétant les nouveaux champs.</p>
<p>Si vous n’êtes pas encore inscrit et que l’administrateur du calendrier a
permis l’auto-inscription, Vous pouvez cliquer sur ”Inscription” sur la page de
connexion&nbsp;; sinon, l’administrateur du calendrier peut vous créer un compte.</p>
<br></li>
<li id="co"><h3>Options du calendrier</h3>
<p>Si vous cliquez sur le bouton “Options” de la barre de navigation ou sur la barre de navigation même, vous ouvrez le menu Options. Dans ce menu, vous pouvez sélectionner les options suivantes en cochant les cases&nbsp;:</p>
<ul style="margin:0 20px">
<li><p>Les vues du Calendrier (Année, Mois, Semaine, Jour, A venir, Modifications ou Matrices).</p></li>
<li><p>Un filtre basé sur l’Utilisateur. Vous pouvez afficher des évènements créés par un ou plusieurs utilisateurs.</p></li>
<li><p>Un filtre basé sur la Catégorie de l’évènement. Vous pouvez afficher des évènements liés à une ou à
plusieurs catégories.</p></li>
<li><p>La sélection du langage de l’utilisateur.</p></li>
</ul>
<p>Note&nbsp;: L’affichage des filtres et de la sélection du langage de l’utilisateur peut être rendu actif ou inactif dans les Réglages du menu Administration.</p>
<p>Après avoir fait votre choix dans le menu Options, vous devez cliquer sur le bouton “Options” de la barre de navigation ou sur la barre de navigation même pour valider vos choix.</p>
<br></li>
<li id="cv"><h3>Vues du calendrier</h3>
<p>Pour chaque vue, le détail des évènements peut être vu dans une info-bulle en passant le curseur de la souris au-dessus de l’évènement. Pour les évènements privés la couleur de fond de la info-bulle sera vert clair. Si vous avez écrit un lien URL dans le champ
“Description”, le lien sera actif dans chaque vue. Il vous suffira de cliquer dessus pour afficher le site web dans une autre fenêtre.</p>
<p>Les évènements d’une catégorie pour laquelle l’administrateur aura activé la case à cocher, auront la case à cocher affichée devant le titre de l’évènement. Cela peut
s’utiliser pour marquer des évènements en tant que
“terminé”, par exemple. Si vous avez les droits suffisants, vous pouvez cocher
ou décocher cette case.</p>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<p>Si vous avez les droits d’accès requis&nbsp;:</p>
<ul style="margin:0 20px">
<li><p>Cliquer sur un évènement dans n’importe quelle vue ouvrira une fenêtre vous permettant d’éditer, de supprimer ou de dupliquer un évènement.</p></li>
<li><p>Dans les vues “Année”, “Mois”, et “Matrice”, un nouvel évènement peut être créé en cliquant sur un espace libre dans la case de la date concernée.</p></li>
<li><p>Dans les vues “Semaine” et “Jour”, un nouvel évènement peut-être créé en sélectionnant l’heure ou la plage horaire de la ou des journée(s) concernées.
 Les dates et les heures seront automatiquement remplies par la période choisie.</p></li>
</ul>
<p>Dans la vue “Modifications”, une date de début peut être spécifiée. Une liste
sera affichée, avec tous les évènements ajoutés, modifiés ou effacés depuis la
date de début spécifiée.</p>
<p>Pour déplacer un évènement dans une nouvelle date ou heure, il faut éditer l’évènement et changer la date de début et/ou de fin et/ou l’heure dans le formulaire.
 Il n’est pas possible de déplacer les évènements en utilisant la souris.</p>
<?php } ?>
<br></li>
<li id="ts"><h3>Recherche de texte</h3>
<p>Lorsque vous cliquez sur le bouton menu latéral du côté droit de la barre de navigation et selectionnez l’option “Rechercher”, la page de recherche de texte s’ouvre. Sur cette page, vous pourrez écrire le texte à rechercher dans le calendrier. Cette page contient également les instructions détaillées pour effectuer la recherche.</p>
<br></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li id="ae"><h3>Ajouter/Éditer/Supprimer un évènement</h3>
<p>Ajouter, éditer, et supprimer un évènement se fait dans le fenêtre
“évènements”, qui s’ouvre de plusieurs manières, comme expliqué ci-dessous.</p>
<br><h6>a. Ajouter un évènement</h6>
<p>L’évènement peut être ajouté de différentes manières&nbsp;:</p>
<ul style="margin:0 20px">
<li><p>En cliquant sur le bouton “Ajouter” de la barre de navigation</p></li>
<li><p>En cliquant sur un espace libre dans la case du jour concerné dans la vue “Mois”, “Année” ou “Matrice”</p></li>
<li><p>En sélectionnant l’heure ou la plage horaire dans la vue “Semaine” ou “Jour”</p></li>
</ul>
<p>Chaque possibilité affichera une fenêtre permettant d’encoder l’évènement.</p>
<h6>Champs Titre, Lieu, Catégorie, Description et Privé</h6>
<p>Dans la 1ère partie du formulaire, vous pouvez saisir le titre, le lieu du rendez-vous, choisir la catégorie,
taper une description et cocher
 l’option “Privé” si nécessaire. Il est conseillé d’écrire un titre court et d’utiliser le champ
“Description” pour détailler l’évènement.
	Vous pouvez utiliser également le champ “Description” pour entrer un lien URL.
Ces liens seront convertis automatiquement en hyperliens qui pourront être
sélectionnés dans les différentes vues et les notifications par email. Les champs
“Lieu” et “Catégorie” sont facultatifs.
	Le choix d’une catégorie influence la couleur du texte et du fond de l’évènement et son affichage dans les différentes vues.</p>
<p>Si vous cochez la case du champ “Privé”, vous serez le seul utilisateur à voir cet évènement.</p>
<h6>Champs Dates, Heures et Répéter</h6>
<p>Dans la 2ème partie du formulaire, vous pouvez encoder les dates et les heures. Si l’évènement
concerne toute la journée, cochez la case du champ
	“Journée entière”&nbsp;; la possibilité de saisir les heures disparait et il n’y aura pas d’heures affichées dans les différentes vues.
	La date de fin est facultative et peut s’utiliser pour les évènements se déroulant sur plusieurs jours. Les dates et les heures peuvent être
	saisies manuellement ou par l’intermédiaire des boutons se trouvant à côté du champ. Vous pouvez répéter l’évènement
dans une boite de dialogue séparée
	qui s’ouvre quand on clique sur le bouton “Modifier”. Suivant le choix effectué, l’évènement sera répété en tenant compte de la date de début et de la date de fin.
	Si aucune date de fin n’est spécifiée, l’évènement sera répété à l’infini, ce qui peut être utile pour les anniversaires.</p>
<h6>Champs Envoi Rappel</h6>
<p>Dans la 3ème partie du formulaire, vous pouvez choisir de recevoir un rappel d’un évènement sur votre adresse email en choisissant le nombre de jours avant l’évènement
	puis en saisissant la ou les adresses email devant recevoir le rappel. Par défaut, votre adresse email est déjà inscrite.
	Un email sera envoyé tout de suite et/ou x jours (en fonction du choix) avant chaque occurrence de l’évènement.</p>
<p>Après avoir rempli le formulaire, cliquer sur le bouton “Sauver” pour l’enregistrer dans le calendrier.</p>
<br>
<h6>b. Éditer/Supprimer un évènement</h6>
<p>Selon vos droits d’accès, vous pouvez éditer/supprimer vos propres évènements ou éditer/supprimer les évènements de tout le monde.</p>
<p>Si vous avez les droits d’accès requis, vous pouvez voir/éditer/supprimer un évènement en cliquant sur son titre dans n’importe quelle vue.
 Une fenêtre s’ouvrira permettant l’édition des champs du formulaire. Cette fenêtre est semblable à celle utilisée pour ajouter un nouvel évènement
 excepté les boutons se trouvant à la fin de la fenêtre.</p>
<p>Pour supprimer un évènement du calendrier, cliquer sur le bouton “Supprimer”. <strong>ATTENTION :
Si vous supprimez un évènement répété, toutes ses occurrences seront également supprimées et pas uniquement la date sélectionnée.</strong></p>
<br></li>
<?php } ?>
<li id="lo"><h3>Fermer la session</h3>
<p>Pour fermer votre session, cliquer sur “Déconnexion” dans la barre de navigation.</p>
<p>Si vous fermez le calendrier sans vous déconnecter, votre session restera ouverte.
À la prochaine ouverture du calendrier, la session sera déjà ouverte avec votre nom d’utilisateur.</p>
<br></li>
<?php if ($usr['privs'] == 9) { //administrator only ?>
<li id="ca"><h3>Menu Administration du calendrier</h3>
<p><strong> — Les fonctions suivantes exigent d’avoir les droits d’administrateur.
—</strong></p>
<p>Lorsqu’un utilisateur ouvre une session avec les droits d’administrateur, le menu latéral
du côté droit de la barre de navigation contient diverses options d’administrateur.
 Par l’intermédiaire de ce menu, les fonctions suivantes seront disponibles&nbsp;:</p>
<br>
<h6>a. Réglages</h6>
<p>Cette fonction vous permet d’afficher les réglages utilisés par le calendrier. Chaque réglage
affiche une explication quand on le survole avec le curseur de la souris.
 Après avoir effectué une modification d’un ou plusieurs réglages, cliquer sur le bouton
“Enregistrer les réglages” pour les enregistrer.</p>
<br>
<h6>b. Catégories</h6>
<p>Cette fonction vous permet de gérer les types de catégorie affectés à chaque évènement. Elle permet également d’ajouter, d’éditer et de supprimer les catégories.</p>
<p>Vous pouvez donner des couleurs différentes aux catégories créées mais ce n’est pas obligatoire. Cela permet de donner une meilleure vue d’ensemble au calendrier.
 Les catégories peuvent être par exemple&nbsp;: rendez-vous, anniversaire, etc.</p>
<p>A l’installation, une seule catégorie est créée avec comme nom “Sans catégorie”.</p>
<p>Vous pouvez définir l’ordre d’affichage des différentes catégories en complétant le champ
“Ordre d’affichage”.</p>
<p>Les couleurs définies pour le texte et le fond des différentes catégories seront utilisées dans le calendrier pour
afficher les évènements appartenant à ces catégories.</p>
<p>Lorsque vous ajoutez/éditez une catégorie, une “Périodicité” peut être choisie&nbsp;; les évènements de cette catégorie seront automatiquement répétés comme
on l’a spécifié. On peut utiliser la case “Public” pour cacher des évènements
à l’utilisateur public et exclure des évènements appartenant à la catégorie du flux RSS.</p>
<p>Vous pouvez également activer une case à cocher. La case à cocher sera affichée au début du titre de tous les évènements de cette catégorie. L’utilisateur peut l’utiliser ces cases à cocher pour marquer des évènements devant être par exemple&nbsp;:
p.e. pour indiquer que l’évènement est “approuvé” ou “terminé”.</p>
<p>Lorsque vous effacez une catégorie, les évènements qui y étaient liés seront associés à la catégorie
“Sans catégorie”.</p>
<br>
<h6>c. Utilisateurs</h6>
<p>Cette fonction vous permet de gérer les utilisateurs. Vous pouvez ajouter, éditer ou supprimer des utilisateurs et attribuer ou non des droits d’accès
 pour certaines fonctions. Lorsqu’on ajoute un nouvel utilisateur, il y a deux parties distinctes
du formulaire à remplir. Dans la 1ère partie,
 on saisit le nom de l’utilisateur, son adresse email et son mot de passe et dans la 2ème partie, on active les droits d’accès qu’il
possèdera.
 Les droits d’accès possibles sont&nbsp;: Voir — Ajouter/Éditer/supprimer un évènement
— et Admin. Il est important d’employer une adresse email valide
 afin de permettre à l’utilisateur de recevoir les notifications d’évènements.</p>
<p>Dans la page des réglages, l’administrateur peut activer l’auto-inscription des utilisateurs et les utilisateurs peuvent également choisir leurs droits d’accès au calendrier.
	Quand l’auto-inscription est permise, les utilisateurs peuvent s’inscrire
eux-mêmes au calendrier par l’intermédiaire du navigateur.</p>
<p>À moins que l’Administrateur n’ait donné la possibilité à l’utilisateur public de voir le calendrier, l’utilisateur doit ouvrir une session en utilisant
 son nom d’utilisateur ou son adresse email, et son mot de passe pour consulter le calendrier. Selon le type d’utilisateur, les droits d’accès aux fonctions seront différents.</p>
<p>Il est possible de spécifier la langue qui sera utilise par utilisateur. Si aucune langue n’est spécifiée, la langue par défaut du calendrier sera utilisée.</p>
<br>
<h6>d. Base de données</h6>
<p>Cette page vous donne accès aux différentes fonctions de gestion de la base de données&nbsp;:</p>
<ul>
<li>Vérifier et réparer la base de données&nbsp;: trouver et réparer les incohérences dans les tables de la base de données</li>
<li>Compacter la base de données&nbsp;: supprimer définitivement les évènements effacés de la base de données et libérer l’espace qu’il occupait</li>
<li>Sauvegarder la base de données&nbsp;: créer un fichier de sauvegarde de la structure des tables et de leurs contenus,
qui servira à recréer la base de données.</li>
</ul>
<p>La 1ère fonction “Vérifier et réparer la base de données” doit seulement être lancée lorsque des incohérences apparaissent dans le calendrier. La 2ème fonction
“Compacter la base de données” doit être lancée une fois par an pour nettoyer la base de données, et la 3ème fonction
“Sauvegarde de la base de données”, doit être lancée régulièrement en fonction de l’utilisation du calendrier.</p>
<br>
<h6>e. Import Fichier CSV</h6>
<p>Cette fonction vous permet d’importer, dans votre calendrier LuxCal, des évènements exportés en format CSV d’un autre calendrier comme par exemple MS Outlook.
 Vous trouverez toutes les instructions pour réaliser cet import après avoir cliquer sur la fonction.</p>
<br>
<h6>f. Import Fichier iCal</h6>
<p>Cette fonction vous permet d’importer, dans votre calendrier LuxCal, des évènements exportés en format iCalendar
(extension fichier .ics) d’un autre calendrier. Vous trouverez toutes les instructions pour réaliser cet import après
avoir cliquer sur la fonction Import iCal. Seul les évènements compatibles avec le calendrier LuxCal seront importés.
Les autres composants (A faire, Journal, Libre / Occupé, Alarme et heure de zone) seront ignorés.</p>
<br>
<h6>g. Export Fichier iCal</h6>
<p>Cette fonction vous permet d’exporter de votre calendrier LuxCal des évènements
au format iCalendar
(extension fichier .ics). Vous trouverez toutes les instructions pour réaliser cet export après avoir
cliqué sur la fonction Export iCal.</p>
<br></li>
<?php } ?>
<li id="al"><h3>A propos de LuxCal</h3>
<p>Produit par&nbsp;: <b>Roel Buining</b>&nbsp;&nbsp;&nbsp;&nbsp;Site Web et forum&nbsp;: <b><a href="https://www.luxsoft.eu/" target="_blank">www.luxsoft.eu/</a></b></p>
<p>LuxCal est un logiciel libre qui peut être redistribué et/ou modifié en respectant les termes du <b><a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">GNU General Public License</a></b>.</p>
<br></li>
</ol>
</div>