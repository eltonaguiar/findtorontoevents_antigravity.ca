<?php
/*
= LuxCal on-line user guide =

This user guide has been produced by LuxSoft - please send your comments to rb@luxsoft.eu.

This file is part of the LuxCal Web Calendar.
*/

?>
<div style="margin:0 20px">
<div class="floatR">
<img src="lang/ug-layout.png" alt="LuxCal page layout"><br>
<span class="hired">a</span>: Başlık Satırı&nbsp;&nbsp;<span class="hired">b</span>: Menü&nbsp;&nbsp;<span class="hired">c</span>: Günler
</div>
<br>
<h3>Yardım İçeriği</h3>
<ol>
<li><p><a href="#ov">Özet</a></p></li>
<li><p><a href="#li">Giriş Yap</a></p></li>
<li><p><a href="#ae">Olay Ekle</a></p></li>
<li><p><a href="#ee">Olayı Düzenle / SİL</a></p></li>
<li><p><a href="#co">Calendar Options</a></p></li>
<li><p><a href="#cv">Ajanda Görünümleri</a></p></li>
<li><p><a href="#ts">Text Search</a></p></li>
<li><p><a href="#lo">ÇIKIŞ</a></p></li>
<li><p><a href="#ca">Ajanda Yönetimi</a></p></li>
<li><p><a href="#al">About LuxCal</a></p></li>
</ol>
</div>
<div class="clear">
<br>
<ol>
<li id="ov"><h3>Özet</h3>
<p>The LuxCal calendar is running on a web server and can be viewed and managed via your web browser.</p>
<p>The title bar displays the calendar title, the date and the name of the current user.
Directly below the title bar, the navigation bar contains several drop-down menus and links, to navigate, to log in / log out, to add an event and to select administrator functions. Which menus and links are displayed depends on the user's access rights.
Below the navigation bar the various calendar views are displayed</p>
<br></li>
<li id="li"><h3>Giriş Yap</h3>
<p>To use the calendar click Log In at the right of the navigation bar. This takes you to the log in screen. Enter your username or email address (one of the two) and the password received from your administrator and click Log In. If you select "Remember me" before clicking Log In, next times you launch the calendar you will be automatically logged in. If you forgot your password, click Log In and thereafter click on the link to have a new password emailed to you.</p>
<p>You can change your personal log-in data by selecting 'Change my data' on the log in page.</p>
<p>If you are not registered yet and the calendar administrator has enabled self-registration, you can click on 'Register' on the log in page; otherwise the calendar administrator can create an account for you.</p>
<p>If the calendar administrator has given View rights to public access users, the calendar can be viewed without logging in.</p>
<br></li>
<li id="ae"><h3>Olay Ekle</h3>
<p>Events can be added in several ways:</p>
<ul style="margin:0 20px">
<li><p>by clicking the Add Event button in the navigation bar</p></li>
<li><p>by clicking a blank area in a day cell in year, month or matrix views, which is most used</p></li>
<li><p>by dragging a certain part of the day in week or day views</p></li>
</ul>
<p>Each way will bring up the Add Event window with a form to enter the event data. Certain fields in the form will be pre-filled, depending on which of the above ways is used to add an event.</p>
<p>In the first part of the form the title, venue, category and a description can be entered, and the option Private Event can be selected. It is good practice to keep the title short and use the description field for details. The venue and category fields are optional. Selecting a category will color-code the event in all views according to the category colors. The venue and description will pop up onmouseover later in the various calendar views. A private event will only be visible to you, and not to others.</p>
<p>URLs added in the event description will be automatically converted to hyperlinks which can be selected in month view, upcoming events view, in the Event window and in notification emails. The format of URL links can be either 'url' or 'url [link name]', for example https://www.google.com or https://www.google.com [search]. If no link name is specified, the full URL will be the link name.</p>
<p>In the second part of the form, dates and times can be specified. If All Day Event is selected, no times will be displayed in the calendar views. The End Date is optional and can be used for multi-day events. Dates and times can be entered manually or via the date and time picker buttons. Following the date and time fields, events can be defined as recurring via a separate dialogue box, which opens when clicking the Change button. In this case the event will be repeated as specified from start to until date. If no until date is specified, the event will repeat for ever, which is particularly useful for birthdays.</p>
<p>In the last part of the form, via the Notify feature, you can select to send an email reminder to one or more email addresses directly, if the 'now' checkbox is selected, and/or a number of days before the due date of the event. In addition, an email reminder will automatically be sent on the date of the event. If the specified number of days is "0", a reminder will be sent on the event day only. For recurring events an email reminder will be sent the selected number of days before each occurrence of the event and on the date of each occurrence of the event.</p>
<p>The email list can contain email addresses and/or the name (without file extension) of a predefined email list file, all separated by a semicolon. The predefined email list must be a text file with extension ".txt" in the "reciplists/" directory with an email address on each line. The file name may not contain the "@" character.</p>
<p>Upon completion, press Add Event.</p>
<br></li>
<li id="ee"><h3>Olayı Düzenle / SİL</h3>
<p>In each of the calendar views an event can be clicked to open a window with all event details. If you have sufficient rights, you can click the 'Edit Event' button to edit, duplicate or delete the event. This will bring up the Edit Event window, which opens an editable form with all event details.</p>
<p>Depending on your access rights, you can view events, view/edit/delete your own events or view/edit/delete all events, including the events of other users. If you have no rights for the opened event, the 'Edit Event' button is greyed out.</p>
<p>For a description of the fields, see the description for Add Event above.</p>
<p>In the Edit Event window, the buttons at the bottom offer the possibility to save an edited event, to save an edited event as a new event (for instance to duplicate the event on an other date) and to delete the event.</p>
<p>Note: Deleting a recurring event will delete all instances of the event, not just one specific date.</p>
<br></li>
<li id="co"><h3>Calendar Options</h3>
<p>Clicking the Options button on the navigation bar will open the calendar's Options Panel. On this panel you can select the following via check boxes:</p>
<ul style="margin:0 20px">
<li><p>The calendar view (year, month, week, day, upcoming, changes or matrix).</p></li>
<li><p>An event filter based on event owners. Events of one single owner or multiple owners can be selected.</p></li>
<li><p>An event filter based on event categories. Events in one single category or multiple categories can be selected.</p></li>
<li><p>The user interface language.</p></li>
</ul>
<p>Note: The display of the event filter menus and the language menu can be enabled/disabled by the calendar administrator.</p>
<p>After having made your choices in the Options Panel, the Options button in the navigation bar should be clicked again to activate your choices.</p> 
<br></li>
<li id="cv"><h3>Ajanda Görünümleri</h3>
<p>In all views, further details of the event will pop up onmouseover. For private events the background color of the pop up box will be light green and for repeating or multi-day events the border of the pop up box will be red. In Upcoming view, URLs in the description field of events will automatically become hyperlinks to the related websites.</p>
<p>Events in a category for which the admin has activated a check box will have a check box displayed in front of the event title, which can be used to flag events for example as "completed". When having sufficient rights, this check box can be clicked to check/uncheck it.</p>
<p>When having sufficient access rights:</p>
<ul style="margin:0 20px">
<li><p>In all views clicking an event will open the Edit Event window for the event, which can be used to view, edit or delete the event.</p></li>
<li><p>In year, month and matrix views a new event can be added for a certain date by clicking a blank area in a day cell.</p></li>
<li><p>In week and day views, an Add Event window can be opened by dragging the cursor over a certain time span; the date and time fields will be preloaded with the selected time span.</p></li>
</ul>
<p>In changes view, a start date can be specified. A list with all events added, edited or deleted since the specified start date will be displayed</p>
<p>To move an event to a new date or time, open the Event window by clicking the event, select Edit Event and change the date and or time. Events cannot be dragged to new dates or times.</p>
<br></li>
<li id="ts"><h3>Text Search</h3>
<p>When clicking the button with the triangle on the right side in the navigation bar, the Text Search page will open. On this page the text search can be defined. The Text Search page contains detailed instructions.</p>
<br></li>
<li id="lo"><h3>ÇIKIŞ</h3>
<p>To log out, click Log Out in the navigation bar. If you close the calendar without logging out, the next time the calendar is opened, it may start without asking for a log in.</p>
<br></li>
<li id="ca"><h3>Ajanda Yönetimi</h3>
<p>- the following features require administrator rights -</p>
<p>When a user logs in with administrator rights, a drop down menu, called Administration, will appear on the right side in the navigation bar. Via this menu the following administrator functions will be available:</p>
<br>
<h6>a. Settings</h6>
<p>This page displays the current calendar settings which subsequently can be changed. All settings are explained on the Settings page by hovering the title of each setting.</p>
<br>
<h6>b. Categories</h6>
<p>Adding event categories with different colors - though not required - will greatly enhance the views of the calendar. Examples of possible Categories are 'holidays', 'appointment', 'birthday', 'important', etc.</p>
<p>The initial installation has only one category, named 'no cat'. Selecting Categories from the administration menu takes you to a page with a list of all categories, with the possibility to add new categories or to edit/delete existing categories.</p>
<p>When adding / editing events the defined categories can be selected from a drop down list. The order in which categories are displayed in the drop down list is determined by the Sequence field. </p>
<p>When adding / editing categories a 'repeat' value can be set; events in this category will automatically repeat as specified. The checkbox 'Public' can be used to hide events belonging to this category from being viewed by public access users (not logged in users) and exclude them from the RSS feeds.</p>
<p>A check mark can be activated, resulting in the calendar in the display of a check mark in front of the event title for all events in this category. The user can use this check mark to flag events for example as "completed". The fields Text color and Background define the colors used to display events in the calendar belonging to this category.</p>
<p>The fields Text color and Background define the colors used to display events in the calendar belonging to this category.</p>
<p>When deleting a category, the events belonging to this category will be reset to the category 'no cat'.</p>
<br>
<h6>c. Users</h6>
<p>The users page allows the calendar administrator to view, add and edit users and their calendar access rights, their default user-interface language, the date of first log in and the date of last log in. Two main areas can be edited: the user's name/email/password and the user's access rights and interface language. Possible access rights are: View, Post own, Post all and Admin. It is important to use a valid email address, to allow the user to receive email notifications of due dates of events.</p>
<p>Via the Settings page, the administrator can enable "user self-registration" and set the access rights for self registered users. When self-registration is enabled, users can register to the calendar via the browser interface.</p> 
<p>Unless the calendar administrator has given View access to public access users, users must log in, using their username or email and password. Depending on the type of user, a user can be given different access rights.</p>
<p>For each user the default user-interface language on log-in can be specified. If no language is specified, the default calendar language specified on the Settings page will be used.</p>
<br>
<h6>d. Database</h6>
<p>The database page allows the calendar administrator to execute the following functions:</p>
<ul>
<li>Check and Repair the database, to find and solve inconsistencies in the database tables.</li>
<li>Compact database, to free unused space and to avoid overhead. This function will permanently remove events which have been deleted more than 30 days ago.</li>
<li>Backup database, to create a backup file which can be used to recreate the database tables structure and content.</li>
</ul>
<p>The first function, Check and Repair database, only needs to be run when the calendar views don't work properly. The second function, Compact database, could be run once a year to clean up the database, and the third function, Backup database, should be run more frequently, depending on the number of calendar updates.</p>
<br>
<h6>e. CSV File Import</h6>
<p>This function can be used to import into the LuxCal Calendar event data that has been exported from other calendars (e.g. MS Outlook). Further instructions are given on the CSV Import page.</p>
<br>
<h6>f. iCal File Import</h6>
<p>This function can be used to import events from iCal files (file extension .ics) into the LuxCal Calendar. Further instructions are given on the iCal Import page. Only events which are compatible with the LuxCal calendar will be imported. Other components, like: To-Do, Journal, Free / Busy and Alarm, will be ignored.</p>
<br>
<h6>g. iCal File Export</h6>
<p>This function can be used to export LuxCal events into iCal files (file extension .ics). Further instructions are given on the iCal Export page.</p>
<br>
</li>
<li id="al"><h3>About LuxCal</h3>
<p>Produced by: <b>Roel Buining</b>&nbsp;&nbsp;&nbsp;&nbsp;Website and forum: <b><a href="https://www.luxsoft.eu/" target="_blank">www.luxsoft.eu/</a></b></p>
<p>LuxCal is freeware and may be redistributed and/or modified under the terms of the <b><a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">GNU General Public License</a></b>.</p>
<br></li>
</ol>
</div>