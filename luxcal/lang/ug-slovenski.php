<?php
/*
= LuxCal on-line user guide =

This file has been produced by LuxSoft and has been translated by David.

This file is part of the LuxCal Web Calendar.
*/

?>
<div style="margin:0 20px">
<div class="floatR">
<img src="lang/ug-layout.png" alt="LuxCal page layout"><br>
<span class="hired">a</span>: naslovna vrstica&nbsp;&nbsp;<span class="hired">b</span>: navigacijska vrstica&nbsp;&nbsp;<span class="hired">c</span>: dan
</div>
<br>
<h3>Kazalo vsebine</h3>
<ol>
<li><p><a href="#ov">Pregled</a></p></li>
<li><p><a href="#li">Vpisovanje</a></p></li>
<li><p><a href="#co">Možnosti koledarja</a></p></li>
<li><p><a href="#cv">Pogledi koledarja</a></p></li>
<li><p><a href="#ts">Besedilno iskanje</a></p></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li><p><a href="#ae">Dodaj / Spremeni / Zbriši dogodek</a></p></li>
<?php } ?>
<li><p><a href="#lo">Izpis</a></p></li>
<?php if ($usr['privs'] > 3) { //if manager/administrator ?>
<li><p><a href="#ca">Administracija koledarja</a></p></li>
<?php } ?>
<li><p><a href="#al">O LuxCal-u</a></p></li>
</ol>
</div>
<div class="clear">
<br>
<ol>
<li id="ov"><h3>Pregled</h3>
<p>The LuxCal calendar runs on a web server and can be viewed via your web browser.</p>
<p>The title bar shows the calendar title, the date and the name of the current user.
The navigation bar contains menus and links to navigate, log in/out, add an event, etc. Access rights determine which menus and links are displayed. The various calendar views are displayed below the navigation bar.</p>
<br></li>
<li id="li"><h3>Vpisovanje</h3>
<p>If the calendar administrator has given View rights to public access users, the calendar can be viewed without logging in.</p>
<p>Clicking Log In at the right of the navigation bar takes you to the log in screen. Enter either your username or email address and the password provided by the LuxCal administrator then click Log In. Select "Remember me" before clicking Log In to be automatically logged in the next time you visit the site. To reset your password, click the "Send new password" button to have a new one emailed to you</p>
<p>You can change your personal log-in data by selecting 'Change my data' on the log in page.</p>
<p>If you are not registered yet and the calendar administrator has enabled self-registration, you can click 'Register' on the log in page; otherwise the calendar administrator can create an account for you.</p>
<br></li>
<li id="co"><h3>Možnosti koledarja</h3>
<p>Clicking the Options button on the navigation bar will open the calendar's Options Panel. On this panel you can select:</p>
<ul style="margin:0 20px">
<li><p>The calendar view (year, month, week, day, upcoming, changes or matrix).</p></li>
<li><p>An event filter based on event owners. Events of one single owner or multiple owners can be selected.</p></li>
<li><p>An event filter based on event categories. Events in one single category or multiple categories can be selected.</p></li>
<li><p>The user interface language.</p></li>
</ul>
<p>After having made your choices, the Options button in the navigation bar should be clicked again to activate your choices.</p> 
<p>Note: The display of the event filter menus and the language menu may have been disabled by the calendar administrator.</p>
<br></li>
<li id="cv"><h3>Pogledi koledarja</h3>
<p>In all views, further details of the event will pop up when hovering over the event title. For private events the background color of the pop up box will be light green and for repeating or multi-day events the border of the pop up box will be red. In Upcoming view, URLs in the description field of events will automatically become hyperlinks.</p>
<p>In all views the day of today will have a blue border and if a new date has been selected with the date picker in the navigation bar, this date will have a red border in month and year view.</p>
<p>Events in a category with "check box" activated by the LuxCal administrator will have a check box displayed in front of the event title. This can be used to flag events as "completed," for example. Users with sufficient rights can click this box to check/uncheck it.</p>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<p>For users with sufficient accesss rights:</p>
<ul style="margin:0 20px">
<li><p>In all views, clicking an event will open the Edit Event window in which the event can be viewed, edited or deleted</p></li>
<li><p>In year, month and matrix views a new event can be added for a certain date by clicking a blank area in a day cell.</p></li>
<li><p>In week and day views, an Add Event window can be opened by dragging the cursor over a certain time span; the date and time fields will be preloaded with the selected time span.</p></li>
</ul>
<p>To move an event to a new date or time, open the Event window by clicking the event, select Edit Event and change the date and or time. Events cannot be dragged to new dates or times.</p>
<?php } ?>
<br></li>
<li id="ts"><h3>Besedilno iskanje</h3>
<p>Click the triangle on the right side of the navigation pane to open the Text Search page. This page contains detailed instructions regarding the use of the search function.</p>
<br></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li id="ae"><h3>Dodaj / Spremeni / Zbriši dogodek</h3>
<p>Adding, editing and deleting events is done via the Event window, which can be opened in several ways as explained below.</p>
<br><h6>a. Dodaj dogodek</h6>
<p>To add events an Event window can be opened in the following ways:</p>
<ul style="margin:0 20px">
<li><p>by clicking the Add Event button in the navigation bar.</p></li>
<li><p>by clicking a blank area in a day cell in year, month or matrix views. (Used most often.)</p></li>
<li><p>by dragging a certain part of the day in week or day views.</p></li>
</ul>
<p>Each way will open the Add Event window with a form to enter the event data. Certain fields of the form will be pre-filled, depending on which of the above ways is used to add an event.</p>
<h6>Title, Venue, Category, Description and Private Event fields</h6>
<p>The venue, category and description fields are optional. Selecting a category will color-code the event in all views according to the category colors. The venue and description will pop up when hovering over events in the various calendar views. URLs added in the event description will be automatically converted to hyperlinks which can be selected in various views and in notification emails.</p>
<p>A private event will only be visible to you, and not to others.</p>
<h6>Dates, Times and Repeat fields</h6>
<p>The End Date is optional and can be used for multi-day events. Dates and times can be entered manually or via the date and time picker buttons. Click the change button to open a dialogue box in which events can be defined as repeating. In this case the event will be repeated as specified from start date to 'until date'. If no 'until date' is specified, the event will repeat for ever, which is particularly useful for birthdays.</p>
<h6>Send email fields</h6>
<p>The Send email feature allows you to send an email reminder to one or more email addresses. The user can send an email 'now' if the appropriate box is checked, and can also define the number days before an event starts in order to send out an email. In the latter case, an email reminder will also be sent on the date of the event. If no number of days is specified, no email will be sent. If the number of days is set to '0' an email reminder will be sent on the event day only. For repeating events, an email reminder will be sent the defined number of days before each occurrence of the event and on the date of each occurrence of the event.</p>
<p>The email list can contain email addresses and/or the name (without file extension) of a predefined email list file, all separated by a semicolon. The predefined email list must be a text file with extension ".txt" in the "reciplists/" directory with an email address on each line. The file name may not contain the "@" character.</p>
<p>Upon completion, press Add Event.</p>
<br>
<h6>b. Spremeni / Zbriši dogodek</h6>
<p>In each of the calendar views an event can be clicked to open a window containing all event details. A user with sufficient rights can edit, duplicate or delete the event.</p>
<p>Depending on your access rights, you can view events, view/edit/delete your own events or view/edit/delete all events, including the events of other users.</p>
<p>For a description of the fields, see the description for Add Event above.</p>
<p>In the Edit Event window, the buttons at the bottom allow the user to save an edited event, save an edited event as a new event (to duplicate the event on another date, for instance) or delete the event.</p>
<p>Note: Deleting a recurring event will delete all instances of the event, not just one specific date.</p>
<br></li>
<?php } ?>
<li id="lo"><h3>Izpis</h3>
<p>To log out, click Log Out on the navigation bar.</p>
<br></li>
<?php if ($usr['privs'] > 3) { //administrator/manager only ?>
<li id="ca"><h3>Administracija koledarja</h3>
<p>- the following features require administrator/manager rights -</p>
<p>When a user logs in with administrator rights, a drop down menu, called Administration, will appear on the right side in the navigation bar. Via this menu the following administrator pages can be selected:</p>
<br>
<ol type='a'>
<?php if ($usr['privs'] == 9) { //administrator only ?>
<li><h6>Settings</h6>
<p>This page displays the current calendar settings which can be customized. All settings are explained on the Settings page by hovering over the title of each setting.</p>
<br></li>
<?php } ?>
<li><h6>Categories</h6>
<p>Adding event categories with different colors - though not required - will greatly enhance the views of the calendar. Examples of possible Categories are 'holidays', 'appointment', 'birthday', 'important', etc.</p>
<p>The Categories page shows a list of all categories, and categories can be added, edited and deleted. The initial installation has only one category, named 'no cat'.</p>
<p>When adding / editing events all categories will be shown in a drop down menu. The order in which categories are displayed in the drop down menu is determined by the Sequence field.</p>
<p>When adding / editing categories a 'repeat' value can be set; events in this category will automatically repeat as specified. The checkbox 'Public' can be used to keep events belonging to this category from being viewed by public access users (users not logged in) and exclude them from the RSS feeds.</p>
<p>A check mark can be activated which will be displayed in front of the event title for all events in this category. The user can use this check mark to flag events, for example, as "approved" or "completed".</p>
<p>The Text color and Background fields define the colors used to display events assigned to this category.</p>
<p>When deleting a category, the deleted category remains available for the events assigned to this category.</p>
<br></li>
<li><h6>User Groups</h6>
<p>This page is used to view, add and edit user groups. Per user group the rights of the users, the event categories available to the users and the group color can be specified. Possible access rights are: None, View, Post own, Post all, Manager and Admin. All users assigned to a group share the same rights, categories and color which have been defined for the group.</p>
<br></li>
<li><h6>Users</h6>
<p>This page is used to view, add and edit user accounts. For each user, the user's name, email, password and the user group to which the user is assigned must be specified. The rights of the user and the available event categories are taken from the user group. It is important to use a valid email address to allow the user to receive email reminders.</p>
<p>Via the Settings page, the administrator can enable "user self-registration" and specify to which user group self registered users will automatically be assigned. When self-registration is enabled, users can register themselves via the browser interface.</p> 
<p>Unless the calendar administrator has given View access to public access users, calendar users must log in with a valid user name or email address and password in order to view the calendar.</p>
<p>Via the log in page, the user can specify his/her default user-interface language. If no language is specified, the default calendar language specified on the Settings page will be used.</p>
<br></li>
<?php if ($usr['privs'] == 9) { //administrator only ?>
<li><h6>Database</h6>
<p>This page allows the calendar administrator to execute the following functions:</p>
<ul>
<li>Compact database, to free unused space and to avoid overhead. This function will permanently remove events which have been deleted more than 30 days ago.</li>
<li>Backup database, to produce a backup file which can be used to restore the complete calendar database.</li>
<li>Restore database, to import a previously created backup file to re-create the structure and content of the database tables.</li>
<li>Delete/undelete events: to delete/undelete events in a certain date range.</li>
</ul>
<p>The function, Compact database, could be executed once per year to clean up the database. The function, Backup database, should be executed more frequently, depending on the number of calendar updates and the function delete events can for instance be used to delete events of past years.</p>
<br></li>
<li><h6>CSV File Import</h6>
<p>This function can be used to import event data into the LuxCal Calendar which has been exported from other calendars (e.g. MS Outlook). Further instructions are provided on the CSV Import page.</p>
<br></li>
<li><h6>iCal File Import</h6>
<p>This function can be used to import events from iCal files (file extension .ics) into the LuxCal Calendar. Further instructions are given on the iCal Import page. Only events which are compatible with the LuxCal calendar will be imported. Other components, like: To-Do, Journal, Free / Busy and Alarm, will be ignored.</p>
<br></li>
<li><h6>Cal File Export</h6>
<p>This function can be used to export LuxCal events into iCal files (file extension .ics). Further instructions are given on the iCal Export page.</p>
<br></li>
<?php } ?>
</ol>
</li>
<?php } ?>
<li id="al"><h3>O LuxCal-u</h3>
<p>Produced by: <b>Roel Buining</b>&nbsp;&nbsp;&nbsp;&nbsp;Website and forum: <b><a href="https://www.luxsoft.eu/" target="_blank">www.luxsoft.eu/</a></b></p>
<p>LuxCal is freeware and may be redistributed and/or modified under the terms of the <b><a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">GNU General Public License</a></b>.</p>
<br></li>
</ol>
</div>