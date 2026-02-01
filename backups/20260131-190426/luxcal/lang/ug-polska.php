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
<span class="hired">a</span>: title bar&nbsp;&nbsp;<span class="hired">b</span>: navigation bar&nbsp;&nbsp;<span class="hired">c</span>: day
</div>
<br>
<h3>Spis treści</h3>
<ol>
<li><p><a href="#ov">Przegląd</a></p></li>
<li><p><a href="#li">Logowanie</a></p></li>
<li><p><a href="#co">Opcje kalendarza</a></p></li>
<li><p><a href="#cv">Widoki kalendarza</a></p></li>
<li><p><a href="#ts">Wyszukiwanie tekstowe</a></p></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li><p><a href="#ae">Dodaj/Edytuj/Usuń wydarzenie</a></p></li>
<?php } ?>
<li><p><a href="#lo">Wylogowywanie</a></p></li>
<?php if ($usr['privs'] > 3) { //if manager/administrator ?>
<li><p><a href="#ca">Administracja kalendarzem</a></p></li>
<?php } ?>
<li><p><a href="#al">Informacje o LuxCal</a></p></li>
</ol>
</div>
<div class="clear">
<br>
<ol>
<li id="ov"><h3>Przegląd</h3>
<p>Kalendarz LuxCal działa na serwerze internetowym i można go przeglądać za pomocą przeglądarki internetowej.</p>
<p>Pasek tytułu wyświetla tytuł kalendarza, datę i nazwę bieżącego użytkownika.
Pasek nawigacyjny zawiera menu i łącza do nawigacji, logowania/wylogowywania, dodawania wydarzeń itp. Prawa dostępu określają, które menu i łącza są wyświetlane. Różne widoki kalendarza są wyświetlane poniżej paska nawigacyjnego.</p>
<br></li>
<li id="li"><h3>Logowanie</h3>
<p>Jeśli administrator kalendarza przyznał prawa do wyświetlania użytkownikom z dostępem publicznym, kalendarz można przeglądać bez logowania.</p>
<p>Kliknięcie Zaloguj się po prawej stronie paska nawigacyjnego przeniesie Cię do ekranu logowania. Wprowadź swoją nazwę użytkownika lub adres e-mail i hasło podane przez administratora LuxCal, a następnie kliknij Zaloguj się. Wybierz „Zapamiętaj mnie” przed kliknięciem Zaloguj się, aby automatycznie zalogować się przy następnej wizycie na stronie. Aby zresetować hasło, kliknij przycisk „Wyślij nowe hasło”, aby otrzymać nowe hasło e-mailem</p>
<p>Możesz zmienić swoje dane logowania, wybierając „Zmień moje dane” na stronie logowania.</p>
<p>Jeśli jeszcze nie jesteś zarejestrowany, a administrator kalendarza włączył samodzielną rejestrację, możesz kliknąć „Zarejestruj się” na stronie logowania; w przeciwnym razie administrator kalendarza może utworzyć dla Ciebie konto.</p>
<br></li>
<li id="co"><h3>Opcje kalendarza</h3>
<p>Kliknięcie przycisku Opcje na pasku nawigacyjnym spowoduje otwarcie panelu opcji kalendarza. W tym panelu możesz wybrać:</p>
<ul style="margin:0 20px">
<li><p>Widok kalendarza (rok, miesiąc, tydzień, dzień, nadchodzące, zmiany lub macierz).</p></li>
<li><p>Filtr wydarzeń oparty na właścicielach wydarzeń. Można wybrać zdarzenia jednego właściciela lub wielu właścicieli.</p></li>
<li><p>Filtr zdarzeń oparty na kategoriach zdarzeń. Można wybrać zdarzenia w jednej kategorii lub wielu kategoriach.</p></li>
<li><p>Język interfejsu użytkownika.</p></li>
</ul>
<p>Po dokonaniu wyboru należy ponownie kliknąć przycisk Opcje na pasku nawigacyjnym, aby aktywować wybór.</p>
<p>Uwaga: wyświetlanie menu filtrów wydarzeń i menu języka mogło zostać wyłączone przez administratora kalendarza.</p>
<br></li>
<li id="cv"><h3>Widoki kalendarza</h3>
<p>We wszystkich widokach po najechaniu kursorem na tytuł wydarzenia pojawią się dalsze szczegóły wydarzenia. W przypadku wydarzeń prywatnych kolor tła wyskakującego okienka będzie jasnozielony, a w przypadku wydarzeń powtarzających się lub trwających wiele dni obramowanie wyskakującego okienka będzie czerwone. W widoku Nadchodzące adresy URL w polu opisu wydarzeń automatycznie staną się hiperłączami.</p>
<p>We wszystkich widokach dzisiejszy dzień będzie miał niebieską ramkę, a jeśli nowa data została wybrana za pomocą selektora dat na pasku nawigacyjnym, ta data będzie miała czerwoną ramkę w widoku miesiąca i roku.</p>
<p>Wydarzenia w kategorii z „polem wyboru” aktywowanym przez administratora LuxCal będą miały pole wyboru wyświetlane przed tytułem wydarzenia. Może ono służyć na przykład do oznaczania wydarzeń jako „ukończone”. Użytkownicy z odpowiednimi uprawnieniami mogą kliknąć to pole, aby je zaznaczyć/odznaczyć.</p>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<p>Dla użytkowników z odpowiednimi uprawnieniami dostępu:</p>
<ul style="margin:0 20px">
<li><p>We wszystkich widokach kliknięcie zdarzenia spowoduje otwarcie okna Edytuj zdarzenie, w którym można je wyświetlić, edytować lub usunąć</p></li>
<li><p>W widokach roku, miesiąca i macierzy można dodać nowe zdarzenie na określoną datę, klikając puste miejsce w komórce dnia.</p></li>
<li><p>W widokach tygodnia i dnia można otworzyć okno Dodaj zdarzenie, przeciągając kursor nad określony przedział czasu; pola daty i godziny zostaną wstępnie załadowane wybranym przedziałem czasu.</p></li>
</ul>
<p>Aby przenieść zdarzenie na nową datę lub godzinę, otwórz okno Zdarzenie, klikając zdarzenie, wybierz Edytuj zdarzenie i zmień datę lub godzinę. Wydarzeń nie można przeciągać na nowe daty ani godziny.</p>
<?php } ?>
<br></li>
<li id="ts"><h3>Wyszukiwanie tekstowe</h3>
<p>Kliknij trójkąt po prawej stronie panelu nawigacyjnego, aby otworzyć stronę wyszukiwania tekstowego. Ta strona zawiera szczegółowe instrukcje dotyczące korzystania z funkcji wyszukiwania.</p>
<br></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li id="ae"><h3>Dodaj/Edytuj/Usuń wydarzenie</h3>
<p>Dodawanie, edytowanie i usuwanie wydarzeń odbywa się za pośrednictwem okna Wydarzenia, które można otworzyć na kilka sposobów, jak wyjaśniono poniżej.</p>
<br><h6>a. Dodaj wydarzenie</h6>
<p>Aby dodać wydarzenie, okno Wydarzenia można otworzyć w następujący sposób:</p>
<ul style="margin:0 20px">
<li><p>klikając przycisk Dodaj wydarzenie na pasku nawigacyjnym.</p></li>
<li><p>klikając pusty obszar w komórce dnia w widoku roku, miesiąca lub macierzy. (Używane najczęściej.)</p></li>
<li><p>przeciągając określoną część dnia w widoku tygodnia lub dnia.</p></li>
</ul>
<p>Każdy sposób spowoduje otwarcie okna Dodaj wydarzenie z formularzem do wprowadzania danych wydarzenia. Niektóre pola formularza zostaną wstępnie wypełnione, w zależności od tego, który z powyższych sposobów zostanie użyty do dodania wydarzenia.</p>
<h6>Pola Tytuł, Miejsce, Kategoria, Opis i Wydarzenie prywatne</h6>
<p>Pola Miejsce, Kategoria i Opis są opcjonalne. Wybranie kategorii spowoduje oznaczenie wydarzenia kolorem we wszystkich widokach zgodnie z kolorami kategorii. Miejsce i opis pojawią się po najechaniu kursorem na wydarzenia w różnych widokach kalendarza. Adresy URL dodane w opisie wydarzenia zostaną automatycznie przekonwertowane na hiperłącza, które można wybrać w różnych widokach i w wiadomościach e-mail z powiadomieniami.</p>
<p>Prywatne wydarzenie będzie widoczne tylko dla Ciebie, a nie dla innych.</p>
<h6>Pola dat, godzin i powtórzeń</h6>
<p>Data zakończenia jest opcjonalna i może być używana w przypadku wydarzeń wielodniowych. Daty i godziny można wprowadzać ręcznie lub za pomocą przycisków wyboru daty i godziny. Kliknij przycisk zmiany, aby otworzyć okno dialogowe, w którym wydarzenia można zdefiniować jako powtarzające się. W takim przypadku wydarzenie będzie powtarzane zgodnie z określonym czasem od daty rozpoczęcia do „do daty”. Jeśli nie określono „do daty”, wydarzenie będzie powtarzane w nieskończoność, co jest szczególnie przydatne w przypadku urodzin.</p>
<h6>Pola wysyłania wiadomości e-mail</h6>
<p>Funkcja wysyłania wiadomości e-mail umożliwia wysłanie przypomnienia e-mail na jeden lub więcej adresów e-mail. Użytkownik może wysłać wiadomość e-mail „teraz”, jeśli zaznaczono odpowiednie pole, a także może określić liczbę dni przed rozpoczęciem wydarzenia, aby wysłać wiadomość e-mail. W drugim przypadku przypomnienie e-mail zostanie również wysłane w dniu wydarzenia. Jeśli nie określono liczby dni, wiadomość e-mail nie zostanie wysłana. Jeśli liczba dni jest ustawiona na „0”, przypomnienie e-mail zostanie wysłane tylko w dniu wydarzenia. W przypadku wydarzeń powtarzających się przypomnienie e-mail zostanie wysłane określoną liczbę dni przed każdym wystąpieniem wydarzenia i w dniu każdego wystąpienia wydarzenia.</p>
<p>Lista e-maili może zawierać adresy e-mail i/lub nazwę (bez rozszerzenia pliku) wstępnie zdefiniowanego pliku listy e-maili, wszystkie rozdzielone średnikiem. Wstępnie zdefiniowana lista e-maili musi być plikiem tekstowym z rozszerzeniem „.txt” w katalogu „reciplists/” z adresem e-mail w każdym wierszu. Nazwa pliku nie może zawierać znaku „@”.</p>
<p>Po zakończeniu naciśnij Dodaj wydarzenie.</p>
<br>
<h6>b. Edytuj/Usuń wydarzenie</h6>
<p>W każdym z widoków kalendarza można kliknąć wydarzenie, aby otworzyć okno zawierające wszystkie szczegóły wydarzenia. Użytkownik z odpowiednimi uprawnieniami może edytować, duplikować lub usuwać wydarzenie.</p>
<p>W zależności od uprawnień dostępu możesz przeglądać wydarzenia, przeglądać/edytować/usuwać własne wydarzenia lub przeglądać/edytować/usuwać wszystkie wydarzenia, w tym wydarzenia innych użytkowników.</p>
<p>Aby uzyskać opis pól, zobacz opis Dodaj wydarzenie powyżej.</p>
<p>W oknie Edytuj wydarzenie przyciski na dole pozwalają użytkownikowi zapisać edytowane wydarzenie, zapisać edytowane wydarzenie jako nowe wydarzenie (na przykład w celu zduplikowania wydarzenia w innym dniu) lub usunąć wydarzenie.</p>
<p>Uwaga: usunięcie powtarzającego się wydarzenia spowoduje usunięcie wszystkich wystąpień wydarzenia, a nie tylko jednej określonej daty.</p>
<br></li>
<?php } ?>
<li id="lo"><h3>Wylogowywanie</h3>
<p>Aby się wylogować, kliknij Wyloguj na pasku nawigacyjnym.</p>
<br></li>
<?php if ($usr['privs'] > 3) { //tylko administrator/menedżer ?>
<li id="ca"><h3>Administracja kalendarzem</h3>
<p>- następujące funkcje wymagają uprawnień administratora/menedżera -</p>
<p>Gdy użytkownik loguje się z uprawnieniami administratora, po prawej stronie paska nawigacyjnego pojawi się menu rozwijane o nazwie Administracja. Za pomocą tego menu można wybrać następujące strony administratora:</p>
<br>
<ol type='a'>
<?php if ($usr['privs'] == 9) { //tylko administrator ?>
<li><h6>Ustawienia</h6>
<p>Ta strona wyświetla bieżące ustawienia kalendarza, które można dostosować. Wszystkie ustawienia są objaśnione na stronie Ustawienia po najechaniu kursorem na tytuł każdego ustawienia.</p>
<br></li>
<?php } ?>
<li><h6>Kategorie</h6>
<p>Dodawanie kategorii wydarzeń o różnych kolorach — choć nie jest to wymagane — znacznie poprawi wygląd kalendarza. Przykłady możliwych kategorii to „święta”, „spotkania”, „urodziny”, „ważne” itp.</p>
<p>Strona kategorii wyświetla listę wszystkich kategorii, a kategorie można dodawać, edytować i usuwać. Początkowa instalacja ma tylko jedną kategorię o nazwie „bez kota”.</p>
<p>Podczas dodawania/edytowania wydarzeń wszystkie kategorie będą wyświetlane w menu rozwijanym. Kolejność, w jakiej kategorie są wyświetlane w menu rozwijanym, jest określana przez pole Sekwencja.</p>
<p>Podczas dodawania/edytowania kategorii można ustawić wartość „powtórz”; wydarzenia w tej kategorii będą automatycznie powtarzane zgodnie ze specyfikacją. Pole wyboru „Publiczne” można wykorzystać do uniemożliwienia wyświetlania zdarzeń należących do tej kategorii użytkownikom z dostępem publicznym (użytkownikom niezalogowanym) i wykluczenia ich z kanałów RSS.</p>
<p>Można aktywować znacznik wyboru, który będzie wyświetlany przed tytułem zdarzenia dla wszystkich zdarzeń w tej kategorii. Użytkownik może użyć tego znacznika wyboru, aby oznaczyć zdarzenia, na przykład jako „zatwierdzone” lub „ukończone”.</p>
<p>Pola Kolor tekstu i Tło definiują kolory używane do wyświetlania zdarzeń przypisanych do tej kategorii.</p>
<p>Podczas usuwania kategorii usunięta kategoria pozostaje dostępna dla zdarzeń przypisanych do tej kategorii.</p>
<br></li>
<li><h6>Grupy użytkowników</h6>
<p>Ta strona służy do przeglądania, dodawania i edytowania grup użytkowników. Dla każdej grupy użytkowników można określić uprawnienia użytkowników, kategorie zdarzeń dostępne dla użytkowników i kolor grupy. Możliwe uprawnienia dostępu to: Brak, Wyświetlanie, Publikowanie własne, Publikowanie wszystkich, Menedżer i Administrator. Wszyscy użytkownicy przypisani do grupy mają takie same prawa, kategorie i kolory, które zostały zdefiniowane dla grupy.</p>
<br></li>
<li><h6>Użytkownicy</h6>
<p>Ta strona służy do przeglądania, dodawania i edytowania kont użytkowników. Dla każdego użytkownika należy określić jego nazwę, adres e-mail, hasło i grupę użytkowników, do której jest przypisany. Uprawnienia użytkownika i dostępne kategorie zdarzeń są pobierane z grupy użytkowników. Ważne jest, aby użyć prawidłowego adresu e-mail, aby umożliwić użytkownikowi otrzymywanie przypomnień e-mail.</p>
<p>Za pośrednictwem strony Ustawienia administrator może włączyć „samodzielną rejestrację użytkownika” i określić, do której grupy użytkowników zostaną automatycznie przypisani użytkownicy zarejestrowani samodzielnie. Gdy samodzielna rejestracja jest włączona, użytkownicy mogą rejestrować się sami za pośrednictwem interfejsu przeglądarki.</p>
<p>Jeśli administrator kalendarza nie przyznał dostępu do widoku użytkownikom z dostępem publicznym, użytkownicy kalendarza muszą się zalogować, podając prawidłową nazwę użytkownika lub adres e-mail i hasło, aby wyświetlić kalendarz.</p>
<p>Za pośrednictwem strony logowania użytkownik może określić swój domyślny język interfejsu użytkownika. Jeśli nie określono języka, użyty zostanie domyślny język kalendarza określony na stronie Ustawienia.</p>
<br></li>
<?php if ($usr['privs'] == 9) { //administrator only ?>
<li><h6>Baza danych</h6>
<p>Ta strona umożliwia administratorowi kalendarza wykonywanie następujących funkcji:</p>
<ul>
<li>Kompaktuj bazę danych, aby zwolnić nieużywane miejsce i uniknąć narzutu. Ta funkcja trwale usunie zdarzenia, które zostały usunięte ponad 30 dni temu.</li>
<li>Kopia zapasowa bazy danych, aby utworzyć plik kopii zapasowej, który może zostać użyty do przywrócenia całej bazy danych kalendarza.</li>
<li>Przywróć bazę danych, aby zaimportować wcześniej utworzony plik kopii zapasowej w celu ponownego utworzenia struktury i zawartości tabel bazy danych.</li>
<li>Usuń/przywróć zdarzenia: aby usunąć/przywrócić zdarzenia w określonym przedziale dat.</li>
</ul>
<p>Funkcja Kompaktuj bazę danych może być wykonywana raz w roku w celu oczyszczenia bazy danych. Funkcja Backup database powinna być wykonywana częściej, w zależności od liczby aktualizacji kalendarza, a funkcja delete events może być używana na przykład do usuwania wydarzeń z poprzednich lat.</p>
<br></li>
<li><h6>Import pliku CSV</h6>
<p>Ta funkcja może być używana do importowania danych wydarzeń do kalendarza LuxCal, które zostały wyeksportowane z innych kalendarzy (np. MS Outlook). Dalsze instrukcje znajdują się na stronie importu CSV.</p>
<br></li>
<li><h6>Import pliku iCal</h6>
<p>Ta funkcja może być używana do importowania wydarzeń z plików iCal (rozszerzenie pliku .ics) do kalendarza LuxCal. Dalsze instrukcje znajdują się na stronie importu iCal. Zostaną zaimportowane tylko wydarzenia zgodne z kalendarzem LuxCal. Inne komponenty, takie jak: To-Do, Journal, Free/Busy i Alarm, zostaną zignorowane.</p>
<br></li>
<li><h6>Eksport pliku Cal</h6>
<p>Ta funkcja może być używana do eksportowania zdarzeń LuxCal do plików iCal (rozszerzenie pliku .ics). Dalsze instrukcje są podane na stronie eksportu iCal.</p>
<br></li>
<?php } ?>
</ol>
</li>
<?php } ?>
<li id="al"><h3>Informacje o LuxCal</h3>
<p>Producent: <b>Roel Buining</b>&nbsp;&nbsp;&nbsp;&nbsp;Strona internetowa i forum: <b><a href="https://www.luxsoft.eu/" target="_blank">www.luxsoft.eu/</a></b></p>
<p>LuxCal jest darmowy i może być redystrybuowany i/lub modyfikowany na warunkach <b><a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">GNU General Public License</a></b>.</p>
<br></li>
</ol>
</div>