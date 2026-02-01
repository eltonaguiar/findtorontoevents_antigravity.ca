<?php
/*
= LuxCal admin interface language file =

This file has been produced by LuxSoft. Please send comments / improvements to rb@luxsoft.eu.

This file is part of the LuxCal Web Calendar.
*/

$ax = array(

//general
"none" => "brak",
"no" => "nie",
"yes" => "tak",
"own" => "własny",
"all" => "wszystkie",
"or" => "lub",
"back" => "wstecz",
"ahead" => "naprzód",
"close" => "Zamknij",
"always" => "zawsze",
"at_time" => "@", // separator daty i godziny (np. 30-01-2020 @ 10:45)
"times" => "razy",
"cat_seq_nr" => "numer sekwencji kategorii",
"rows" => "wiersze",
"columns" => "kolumny",
"hours" => "godziny",
"minutes" => "minuty",
"user_group" => "grupa użytkowników",
"event_cat" => "kategoria zdarzenia",
"email" => "Email",
"telegram" => "Telegram",
"sms" => "SMS",
"id" => "ID",
"username" => "Nazwa użytkownika",
"password" => "Hasło",
"public" => "Publiczny",
"logged_in" => "Zalogowany",
"pw_no_chars" => "Znaki <, > i ~ niedozwolone w haśle",

//settings.php - fieldset headers + general
"set_general_settings" => "Ogólne ustawienia kalendarza",
"set_navbar_settings" => "Pasek nawigacji",
"set_event_settings" => "Wydarzenia",
"set_user_settings" => "Konta użytkowników",
"set_upload_settings" => "Przesyłanie plików",
"set_reminder_settings" => "Przypomnienia",
"set_perfun_settings" => "Usługi okresowe (dotyczy tylko zdefiniowanych zadań cron)",
"set_sidebar_settings" => "Samodzielny pasek boczny (ma znaczenie tylko wtedy, gdy jest używany)",
"set_view_settings" => "Widoki",
"set_dt_settings" => "Dates/Times",
"set_save_settings" => "Zapisz ustawienia",
"set_test_mail" => "Poczta testowa",
"set_mail_sent_to" => "Poczta testowa wysłana do",
"set_mail_sent_from" => "Ta wiadomość testowa została wysłana ze strony ustawień kalendarza",
"set_mail_failed" => "Wysyłanie poczty testowej nie powiodło się - odbiorca(y)",
"set_missing_invalid" => "brakujące lub nieprawidłowe ustawienia (podświetlone w tle)",
"set_settings_saved" => "Ustawienia kalendarza zapisane",
"set_save_error" => "Błąd bazy danych - Zapisywanie ustawień kalendarza nie powiodło się",
"hover_for_details" => "Opisy po najechaniu kursorem dla szczegółów",
"default" => "domyślne",
"enabled" => "włączone",
"disabled" => "wyłączone",
"pixels" => "piksele",
"warnings" => "Ostrzeżenia",
"notices" => "Powiadomienia",
"visitors" => "Odwiedzający",
"height" => "wysokość",
"no_way" => "Nie masz uprawnień do wykonania tej operacji",

//settings.php - general settings
"versions_label" => "Wersje",
"versions_text" => "• wersja kalendarza, a następnie używana baza danych<br>• wersja PHP<br>• wersja bazy danych",
"calTitle_label" => "Tytuł kalendarza",
"calTitle_text" => "Wyświetlany na górnym pasku kalendarza i używany w powiadomieniach e-mail.",
"calUrl_label" => "Adres URL kalendarza",
"calUrl_text" => "Adres witryny internetowej kalendarza.",
"calEmail_label" => "Adres e-mail kalendarza",
"calEmail_text" => "Adres e-mail używany do odbierania wiadomości kontaktowych i wysyłania lub odbierania powiadomień e-mail.<br>Format: 'email' lub 'name &#8826;email&#8827;'.",
"logoPath_label" => "Ścieżka/nazwa logo image",
"logoPath_text" => "Jeśli określono, obraz logo będzie wyświetlany w lewym górnym rogu kalendarza. Jeśli określono również link do strony nadrzędnej (patrz poniżej), logo będzie hiperłączem do strony nadrzędnej. Obraz logo powinien mieć maksymalną wysokość i szerokość 70 pikseli.",
"logoXlPath_label" => "Ścieżka/nazwa obrazu logo logowania",
"logoXlPath_text" => "Jeśli określono, obraz logo o określonej wysokości będzie wyświetlany na stronie logowania poniżej formularza logowania.",
"backLinkUrl_label" => "Link do strony nadrzędnej",
"backLinkUrl_text" => "URL strony nadrzędnej. Jeśli określono, przycisk Wstecz zostanie wyświetlony po lewej stronie paska nawigacyjnego, który łączy się z tym adresem URL.<br>Na przykład, aby połączyć się z powrotem ze stroną nadrzędną, z której uruchomiono kalendarz. Jeśli określono ścieżkę/nazwę logo (patrz powyżej), przycisk Wstecz nie zostanie wyświetlony, ale logo stanie się linkiem wstecz.",
"timeZone_label" => "Strefa czasowa",
"timeZone_text" => "Strefa czasowa kalendarza, używana do obliczania bieżącego czasu.",
"see" => "zobacz",
"notifChange_label" => "Wyślij powiadomienie o zmianach w kalendarzu",
"notifChange_text" => "Gdy użytkownik doda, edytuje lub usunie wydarzenie, wiadomość z powiadomieniem zostanie wysłana do określonych odbiorców.",
"chgRecipList" => "odbiorcy rozdzieleni średnikami list",
"maxXsWidth_label" => "Maksymalna szerokość małych ekranów",
"maxXsWidth_text" => "W przypadku wyświetlaczy o szerokości mniejszej niż określona liczba pikseli kalendarz będzie działał w specjalnym trybie responsywnym, pomijając pewne mniej ważne elementy.",
"rssFeed_label" => "Linki do kanałów RSS",
"rssFeed_text" => "Jeśli włączone: dla użytkowników z uprawnieniami co najmniej 'view' link do kanału RSS będzie widoczny w stopce kalendarza, a link do kanału RSS zostanie dodany do nagłówka HTML stron kalendarza.",
"logging_label" => "Log kalendarza",
"logging_text" => "Kalendarz może rejestrować komunikaty o błędach, ostrzeżeniach i powiadomieniach oraz dane odwiedzających. Komunikaty o błędach są zawsze rejestrowane. Rejestrowanie komunikatów o ostrzeżeniach i powiadomieniach oraz danych odwiedzających można wyłączyć lub włączyć, zaznaczając odpowiednie pola wyboru. Wszystkie komunikaty o błędach, ostrzeżeniach i powiadomieniach są rejestrowane w pliku 'logs/luxcal.log', a dane odwiedzających są rejestrowane w plikach 'logs/hitlog.log' i 'logs/botlog.log'.<br>Uwaga: komunikaty o błędach, ostrzeżeniach i powiadomieniach PHP są rejestrowane w innym miejscu, określonym przez Twojego dostawcę usług internetowych.",
"maintMode_label" => "Tryb konserwacji PHP",
"maintMode_text" => "Po włączeniu, w skryptach PHP dane przesłane za pomocą funkcji notatki (wiadomości) i dane przechowywane w zmiennej 'note' będą wyświetlane na pasku stopki kalendarza.",
"reciplist" => "Lista odbiorców może zawierać rozdzieloną średnikami listę z nazwami użytkowników, adresami e-mail, numerami telefonów, identyfikatorami czatów Telegram oraz, ujętymi w nawiasy kwadratowe, nazwami plików z odbiorcami. Pliki z odbiorcami z jednym odbiorcą na wiersz powinny znajdować się w folderze 'reciplists'. W przypadku pominięcia domyślne rozszerzenie pliku to .txt",
"calendar" => "kalendarz",
"user" => "Użytkownik",
"database" => "baza danych",

//settings.php - navigation bar settings
"contact_label" => "Przycisk Kontakt",
"contact_text" => "Jeśli włączone: Przycisk Kontakt zostanie wyświetlony w menu bocznym. Kliknięcie tego przycisku spowoduje otwarcie formularza kontaktowego, którego można użyć do wysłania wiadomości do administratora kalendarza.",
"optionsPanel_label" => "Menu panelu opcji",
"optionsPanel_text" => "Włącz/wyłącz menu w panelu opcji.<br>• Menu kalendarza jest dostępne dla administratora w celu przełączania kalendarzy. (włączenie jest przydatne tylko wtedy, gdy zainstalowano kilka kalendarzy)<br>• Menu widoku można użyć do wybrania jednego z widoków kalendarza.<br>• Menu grup można użyć do wyświetlania tylko wydarzeń utworzonych przez użytkowników z wybranych grup.<br>• Menu użytkowników można użyć do wyświetlania tylko wydarzeń utworzonych przez wybranych użytkowników.<br>• Menu kategorii można użyć do wyświetlania tylko wydarzeń należących do wybranych kategorii wydarzeń.<br>• Menu języka można użyć do wybrania języka interfejsu użytkownika. (włączenie jest przydatne tylko wtedy, gdy zainstalowano kilka języków są zainstalowane)<br>Uwaga: Jeśli nie wybrano żadnego menu, przycisk panelu opcji nie zostanie wyświetlony.",
"calMenu_label" => "kalendarz",
"viewMenu_label" => "widok",
"groupMenu_label" => "grupy",
"userMenu_label" => "użytkownicy",
"catMenu_label" => "kategorie",
"langMenu_label" => "język",
"availViews_label" => "Dostępne widoki kalendarza",
"availViews_text" => "Widoki kalendarza dostępne dla użytkowników publicznych i zalogowanych określone za pomocą listy rozdzielonej przecinkami z numerami widoków. Znaczenie liczb:<br>1: widok roku<br>2: widok miesiąca (7 dni)<br>3: widok miesiąca roboczego<br>4: widok tygodnia (7 dni)<br>5: widok tygodnia roboczego<br>6: widok dnia<br>7: widok nadchodzących wydarzeń<br>8: widok zmian<br>9: widok macierzy (kategorie)<br>10: widok macierzy (użytkownicy)<br>11: widok wykresu Gantta",
"viewButtonsL_label" => "Przyciski widoku na pasku nawigacyjnym (duży wyświetlacz)",
"viewButtonsS_label" => "Przyciski widoku na pasku nawigacyjnym (mały wyświetlacz)",
"viewButtons_text" => "Przyciski widoku na pasku nawigacyjnym dla użytkowników publicznych i zalogowanych, określone za pomocą listy numerów widoków rozdzielonych przecinkami.<br>Jeśli w sekwencji określono liczbę, zostanie wyświetlony odpowiadający jej przycisk. Jeśli nie określono żadnych liczb, nie zostaną wyświetlone żadne przyciski widoku.<br>Znaczenie liczb:<br>1: Rok<br>2: Pełny miesiąc<br>3: Miesiąc roboczy<br>4: Pełny tydzień<br>5: Tydzień roboczy<br>6: Dzień<br>7: Nadchodzące<br>8: Zmiany<br>9: Macierz-C<br>10: Macierz-U<br>11: Wykres Gantta<br>Kolejność liczb określa kolejność wyświetlanych przycisków.<br>Na przykład: '2,4' oznacza: wyświetl przyciski 'Pełny miesiąc' i 'Pełny tydzień'.",
"defaultViewL_label" => "Domyślny widok po uruchomieniu (duży wyświetlacz)",
"defaultViewL_text" => "Domyślny widok kalendarza po uruchomieniu dla użytkowników publicznych i zalogowanych korzystających z dużych wyświetlaczy.<br>Zalecany wybór: Miesiąc.",
"defaultViewS_label" => "Domyślny widok po uruchomieniu (mały wyświetlacz)",
"defaultViewS_text" => "Domyślny widok kalendarza po uruchomieniu dla użytkowników publicznych i zalogowanych korzystających z małych wyświetlaczy.<br>Zalecany wybór: Nadchodzące.",
"language_label" => "Domyślny język interfejsu użytkownika (public user)",
"language_text" => "For public (not logged in) users the language set for the browser user interface will be used for the calendar as well. If the browser language is not a valid calendar language, this default language will be used.<br>Note: Pliki ui-{language}.php, ai-{language}.php, ug-{language}.php i ug-layout.png muszą znajdować się w katalogu lang/. {language} = wybrany język interfejsu użytkownika. Nazwy plików muszą być pisane małymi literami!",
"birthday_cal_label" => "Kalendarz urodzinowy PDF",
"birthday_cal_text" => "Jeśli ta opcja jest włączona, opcja 'Plik PDF - Urodziny' pojawi się w menu bocznym dla użytkowników z uprawnieniami co najmniej 'widok'. Zobacz admin_guide.html - Kalendarz urodzinowy, aby uzyskać więcej szczegółów",
"sideLists_label" => "Zatwierdź, Todo, Nadchodzące listy",
"sideLists_text" => "Jeśli włączone, opcja wyświetlania odpowiedniej listy pojawi się w Menu bocznym. Lista 'Wydarzenia do zatwierdzenia' będzie dostępna tylko dla użytkowników z uprawnieniami co najmniej 'menedżera'.",
"toapList_label" => "Lista do zatwierdzenia",
"todoList_label" => "Lista rzeczy do zrobienia",
"upcoList_label" => "Nadchodzące listy",

//settings.php - events settings
"privEvents_label" => "Publikowanie prywatnych wydarzeń",
"privEvents_text" => "Prywatne wydarzenia są widoczne tylko dla użytkownika, który wszedł na wydarzenie.<br>Włączone: użytkownicy mogą wchodzić na prywatne wydarzenia.<br>Domyślnie: podczas dodawania nowych wydarzeń pole wyboru 'private' w oknie Wydarzenia będzie domyślnie zaznaczone.<br>Zawsze: podczas dodawania nowych wydarzeń będą one zawsze prywatne, pole wyboru 'private' w oknie Wydarzenia nie będzie wyświetlane.",
"venueInput_label" => "Określanie miejsc",
"venueInput_text" => "W oknie Wydarzenia można określić miejsce, wpisując je lub wybierając je z wstępnie zdefiniowanej listy. Jeśli wybrano opcję Tekst dowolny, użytkownik może wpisać miejsce, jeśli wybrano opcję Lista, użytkownik może wybrać miejsce z listy rozwijanej, a jeśli wybrano opcję Oba, użytkownik może wybrać między nimi.<br> Gdy używana jest lista rozwijana, Folder 'files' musi zawierać plik o nazwie venues.txt z jednym venue na wiersz.",
"timeDefault_label" => "Dodawanie nowych wydarzeń - domyślny czas",
"timeDefault_text" => "Podczas dodawania wydarzeń w oknie Wydarzenia domyślny sposób wyświetlania pól czasu wydarzenia w formularzu wydarzenia można ustawić w następujący sposób:<br>• pokaż czasy: Pola czasu rozpoczęcia i zakończenia są wyświetlane i gotowe do wypełnienia<br>• cały dzień: Pole wyboru Cały dzień jest zaznaczone, pola czasu rozpoczęcia i zakończenia nie są wyświetlane<br>• brak czasu: Pole wyboru Brak czasu jest zaznaczone, pola czasu rozpoczęcia i zakończenia nie są wyświetlane.",
"evtDelButton_label" => "Przycisk Usuń w oknie Wydarzenia",
"evtDelButton_text" => "Wyłączone: przycisk Usuń w oknie Wydarzenia nie będzie widoczny. Użytkownicy z uprawnieniami do edycji nie będą mogli usuwać wydarzeń.<br>Włączone: przycisk Usuń w oknie Wydarzenia będzie widoczny dla wszystkich użytkowników.<br>Menedżer: przycisk Usuń w oknie Wydarzenia będzie widoczny tylko dla użytkowników z uprawnieniami co najmniej 'menedżera'.",
"eventColor_label" => "Kolory wydarzeń na podstawie",
"eventColor_text" => "Wydarzenia w różnych widokach kalendarza mogą być wyświetlane w kolorze przypisanym do grupy, do której należy użytkownik, który utworzył wydarzenie, lub w kolorze kategorii wydarzenia.",
"defVenue_label" => "Domyślne miejsce",
"defVenue_text" => "W tym polu tekstowym można określić miejsce, które zostanie skopiowane do pola Miejsce formularza wydarzenia podczas dodawania nowych wydarzeń.",
"xField1_label" => "Pole dodatkowe 1",
"xField2_label" => "Pole dodatkowe 2",
"xFieldx_text" => "Opcjonalne pole tekstowe. Jeśli to pole jest zawarte w szablonie wydarzenia w sekcji Widoki, zostanie dodane jako pole tekstowe w formacie dowolnym do formularza okna Wydarzenia i do wydarzeń wyświetlanych we wszystkich widokach i stronach kalendarza.<br>• etykieta: opcjonalna etykieta tekstowa dla dodatkowego pola (maks. 15 znaków). Np. 'Adres e-mail', 'Strona internetowa', 'Numer telefonu'<br>• Minimalne uprawnienia użytkownika: pole będzie widoczne tylko dla użytkowników z wybranymi uprawnieniami użytkownika lub wyższymi.",
"evtWinSmall_label" => "Zmniejszone okno wydarzenia",
"evtWinSmall_text" => "Podczas dodawania/edytowania wydarzeń okno Wydarzenia wyświetli podzbiór pól wejściowych. Aby wyświetlić wszystkie pola, można wybrać strzałkę.",
"emojiPicker_label" => "Wybór emoji w oknie wydarzenia",
"emojiPicker_text" => "Po włączeniu, w oknie dodawania/edycji wydarzenia można wybrać selektor emoji, aby dodać emoji do tytułu wydarzenia i pól opisu.",
"mapViewer_label" => "Adres URL przeglądarki map",
"mapViewer_text" => "Jeśli określono adres URL przeglądarki map, adres w polu miejsca wydarzenia ujęty w znaki ! będzie wyświetlany jako przycisk Adres w widokach kalendarza. Po najechaniu kursorem na ten przycisk zostanie wyświetlony adres tekstowy, a po kliknięciu otworzy się nowe okno, w którym adres zostanie wyświetlony na mapie.<br>Należy określić pełny adres URL przeglądarki map, do którego można dołączyć adres.<br>Przykłady:<br>Google Maps: https://maps.google.com/maps?q=<br>OpenStreetMap: https://www.openstreetmap.org/search?query=<br>Jeśli to pole pozostanie puste, adresy w polu Miejsce nie będą wyświetlane jako przycisk Adres.",
"evtDrAndDr_label" => "Przeciąganie i upuszczanie wydarzeń",
"evtDrAndDr_text" => "Po włączeniu w widoku roku, widoku miesiąca i w mini kalendarzu na panelu bocznym wydarzenia można przenosić lub kopiować z jednego dnia na inny za pomocą funkcji Przeciągnij i upuść. Jeśli wybrano opcję 'manager', z tej funkcji mogą korzystać tylko użytkownicy posiadający co najmniej uprawnienia menedżera. Zobacz admin_guide.html, aby uzyskać szczegółowy opis.",
"free_text" => "Tekst dowolny",
"venue_list" => "Lista miejsc",
"both" => "obydwa",
"xField_label" => "Etykieta",
"show_times" => "pokaż czasy",
"check_ald" => "cały dzień",
"check_ntm" => "brak godziny",
"min_rights" => "Minimalne uprawnienia użytkownika",
"no_color" => 'brak koloru',
"manager_only" => 'tylko manager',

//settings.php - user accounts settings
"selfReg_label" => "Samodzielna rejestracja",
"selfReg_text" => "Pozwól użytkownikom na samodzielną rejestrację i uzyskanie dostępu do kalendarza.<br>Grupa użytkowników, do której zostaną przypisani użytkownicy zarejestrowani samodzielnie.",
"selfRegQA_label" => "Pytanie/odpowiedź dotyczące samodzielnej rejestracji",
"selfRegQA_text" => "Gdy samodzielna rejestracja jest włączona, podczas procesu samodzielnej rejestracji użytkownikowi zostanie zadane to pytanie i będzie mógł się samodzielnie zarejestrować tylko wtedy, gdy poda prawidłową odpowiedź. Gdy pole pytania pozostanie puste, żadne pytanie nie zostanie zadane.",
"selfRegNot_label" => "Powiadomienie o samodzielnej rejestracji",
"selfRegNot_text" => "Wyślij powiadomienie e-mail na adres e-mail kalendarza, gdy nastąpi samodzielna rejestracja.",
"restLastSel_label" => "Przywróć ostatnie wybory użytkownika",
"restLastSel_text" => "Ostatnie wybory użytkownika (opcja Ustawienia panelu) zostaną zapisane i gdy użytkownik ponownie odwiedzi kalendarz później, wartości zostaną przywrócone. Jeśli użytkownik nie zaloguje się w ciągu określonej liczby dni, wartości zostaną utracone.",
"answer" => "odpowiedź",
"exp_days" => "dni",
"view" => "widok",
"post_own" => 'wyślij własne',
"post_all" => 'wyślij wszystkie',
"manager" => 'wyślij/manager',

//settings.php - view settings
"templFields_text" => "Znaczenie liczb:<br>1: Pole miejsca<br>2: Pole kategorii wydarzenia<br>3: Pole opisu<br>4: Pole dodatkowe 1 (patrz poniżej)<br>5: Pole dodatkowe 2 (patrz poniżej)<br>6: Dane powiadomienia e-mail (tylko jeśli zażądano powiadomienia)<br>7: Data/godzina dodania/edycji i powiązani użytkownicy<br>8: Dołączone pliki PDF, obrazy lub wideo jako hiperłącza.<br>Kolejność liczb określa kolejność wyświetlanych pól.",
"evtTemplate_label" => "Szablony wydarzeń",
"evtTemplate_text" => "Pola wydarzeń, które mają być wyświetlane w ogólnych widokach kalendarza, widokach nadchodzących wydarzeń i w polu najechania kursorem ze szczegółami wydarzenia, można określić za pomocą sekwencji liczb.<br>Jeśli w sekwencji zostanie określona liczba, wyświetlone zostanie odpowiadające jej pole.",
"evtTemplPublic" => "Użytkownicy publiczni",
"evtTemplLogged" => "Zalogowani użytkownicy",
"evtTemplGen" => "Widok ogólny",
"evtTemplUpc" => "Widok nadchodzący",
"evtTemplPop" => "Pole najechania kursorem",
"sortEvents_label" => "Sortuj wydarzenia według czasu lub kategorii",
"sortEvents_text" => "W różnych widokach wydarzenia można sortować według następujących kryteriów:<br>• godziny wydarzenia<br>• numer sekwencji kategorii wydarzenia",
"yearStart_label" => "Miesiąc początkowy w widoku roku",
"yearStart_text" => "Jeśli określono miesiąc początkowy (1 - 12), w widoku roku kalendarz zawsze będzie zaczynał się od tego miesiąca, a rok tego pierwszego miesiąca zmieni się dopiero pierwszego dnia tego samego miesiąca w następnym roku.<br>Wartość 0 ma specjalne znaczenie: miesiąc początkowy jest oparty na bieżącej dacie i będzie przypadał na pierwszy wiersz miesięcy.",
"YvRowsColumns_label" => "Wiersze i kolumny do wyświetlenia w widoku roku",
"YvRowsColumns_text" => "Liczba wierszy po cztery miesiące do wyświetlenia w widoku roku.<br>Zalecany wybór: 4, co daje 16 miesięcy do przewijania.<br>Liczba miesięcy do wyświetlenia w każdym wierszu w widoku roku.<br>Zalecany wybór: 3 lub 4.",
"MvWeeksToShow_label" => "Tygodnie do wyświetlenia w widoku miesiąca",
"MvWeeksToShow_text" => "Liczba tygodni do wyświetlenia w widoku miesiąca.<br>Zalecany wybór: 10, co daje 2,5 miesiąca do przewijania.<br>Wartości 0 i 1 mają specjalne znaczenie:<br>0: wyświetl dokładnie 1 miesiąc - puste dni wiodące i końcowe.<br>1: wyświetl dokładnie 1 miesiąc - wyświetl zdarzenia na wiodącym i końcowym końcowe dni.",
"XvWeeksToShow_label" => "Tygodnie do wyświetlenia w widoku macierzy",
"XvWeeksToShow_text" => "Liczba tygodni kalendarzowych do wyświetlenia w widoku macierzy.",
"GvWeeksToShow_label" => "Tygodnie do wyświetlenia w widoku wykresu Gantta",
"GvWeeksToShow_text" => "Liczba tygodni kalendarzowych do wyświetlenia w widoku wykresu Gantta.",
"workWeekDays_label" => "Dni robocze",
"workWeekDays_text" => "Dni pokolorowane jako dni robocze w widokach kalendarza i na przykład do wyświetlenia w tygodniach w widoku Miesiąc roboczy i Tydzień roboczy.<br>Wprowadź liczbę każdego dnia roboczego.<br>np. 12345: poniedziałek - piątek<br>Niewpisane dni są uważane za dni weekendowe.",
"weekStart_label" => "Pierwszy dzień tygodnia",
"weekStart_text" => "Wprowadź numer pierwszego dnia tygodnia.",
"lookBackAhead_label" => "Dni, w których należy przejrzeć wstecz/w przód",
"lookBackAhead_text" => "Liczba dni, w których należy przejrzeć wstecz wydarzenia na liście zadań do wykonania i do przodu wydarzenia w widoku Nadchodzące wydarzenia, na liście zadań do wykonania i w kanałach RSS.",
"searchBackAhead_label" => "Domyślne dni wyszukiwania wstecz/w przód",
"searchBackAhead_text" => "Jeśli na stronie wyszukiwania nie określono żadnych dat, są to domyślne liczby dni wyszukiwania wstecz i do przodu.",
"dwStartEndHour_label" => "Godziny rozpoczęcia i zakończenia w widoku Dzień/Tydzień",
"dwStartEndHour_text" => "Godziny, o których rozpoczyna się i kończy normalny dzień wydarzeń.<br>Na przykład ustawienie tych wartości na 6 i 18 pozwoli uniknąć marnowania miejsca w widoku Tydzień/Dzień na czas ciszy między północą a 6:00 i 18:00 a północą.<br>Wybór czasu, używany do wprowadzania czasu, również rozpocznie się i zakończy w tych godzinach.",
"dwTimeSlot_label" => "Przedział czasowy w widoku Dzień/Tydzień",
"dwTimeSlot_text" => "Przedział czasowy i wysokość przedziałów czasowych w widoku Dzień/Tydzień.<br>Liczba minut, wraz z godziną rozpoczęcia i godziną zakończenia (patrz powyżej) określi liczbę wierszy w widoku Dzień/Tydzień.",
"dwTsInterval" => "Czas interval",
"dwTsHeight" => "Wysokość",
"evtHeadX_label" => "Układ wydarzenia w widoku Miesiąc, Tydzień i Dzień",
"evtHeadX_text" => "Szablony z symbolami zastępczymi pól wydarzenia, które powinny być wyświetlane. Można użyć następujących symboli zastępczych:<br>#ts - czas rozpoczęcia<br>#tx - czas rozpoczęcia i zakończenia<br>#e - tytuł wydarzenia<br>#o - właściciel wydarzenia<br>#v - miejsce<br>#lv - miejsce z etykietą 'Miejsce:' z przodu<br>#c - kategoria<br>#lc - kategoria z etykietą 'Kategoria:' z przodu<br>#a - wiek (patrz uwaga poniżej)<br>#x1 - dodatkowe pole 1<br>#lx1 - dodatkowe pole 1 z etykietą ze strony Ustawienia z przodu<br>#x2 - dodatkowe pole 2<br>#lx2 - dodatkowe pole 2 z etykietą ze strony Ustawienia w front<br>#/ - nowa linia<br>Pola są wyświetlane w określonej kolejności. Znaki inne niż symbole zastępcze pozostaną niezmienione i będą częścią wyświetlanego zdarzenia.<br>Tagi HTML są dozwolone w szablonie. Np. &lt;b&gt;#e&lt;/b&gt;.<br>Znak | może być używany do dzielenia szablonu na sekcje. Jeśli w sekcji wszystkie parametry # dają pusty ciąg, cała sekcja zostanie pominięta.<br>Uwaga: Wiek jest wyświetlany, jeśli wydarzenie jest częścią kategorii z opcją 'Powtarzaj' ustawioną na 'co roku', a rok urodzenia w nawiasach jest wymieniony gdzieś w polu opisu wydarzenia lub w jednym z pól dodatkowych.",
"monthView" => "Widok miesiąca",
"wkdayView" => "Widok tygodnia/dnia",
"ownerTitle_label" => "Pokaż właściciela wydarzenia przed tytułem wydarzenia",
"ownerTitle_text" => "W różnych widokach kalendarza pokaż nazwę właściciela wydarzenia przed tytułem wydarzenia.",
"showSpanel_label" => "Panel boczny w widokach kalendarza",
"showSpanel_text" => "W widokach kalendarza, tuż obok głównej strony kalendarza, można wyświetlić panel boczny z następującymi elementami:<br>• mini kalendarz, którego można użyć do przeglądania wstecz lub do przodu bez zmiany data kalendarza głównego<br>• obraz dekoracyjny odpowiadający bieżącemu miesiącowi<br>• obszar informacyjny do publikowania wiadomości/ogłoszeń w określonych okresach.<br>Dla każdego elementu można określić listę numerów widoków rozdzielonych przecinkami, dla których powinien być wyświetlany panel boczny.<br>Możliwe numery widoków:<br>0: wszystkie widoki<br>1: widok roku<br>2: widok miesiąca (7 dni)<br>3: widok miesiąca roboczego<br>4: widok tygodnia (7 dni)<br>5: widok tygodnia roboczego<br>6: widok dnia<br>7: widok nadchodzących wydarzeń<br>8: widok zmian<br>9: widok macierzy (kategorie)<br>10: widok macierzy (użytkownicy)<br>11: widok wykresu Gantta.<br>Jeśli zaznaczono opcję 'Dzisiaj', panel boczny zawsze będzie używał daty dzisiejszej, w przeciwnym razie będzie podążał za datą wybraną dla kalendarza głównego.<br>Panel boczny — zobacz admin_guide.html szczegóły.",
"spMiniCal" => "Mini kalendarz",
"spImages" => "Obrazy",
"spInfoArea" => "Obszar informacyjny",
"spToday" => "Dzisiaj",
"topBarDate_label" => "Pokaż bieżącą datę na górnym pasku",
"topBarDate_text" => "Włącz/wyłącz wyświetlanie bieżącej daty na górnym pasku kalendarza w widokach kalendarza. Jeśli jest wyświetlana, można kliknąć bieżącą datę, aby zresetować kalendarz do bieżącej daty.",
"showImgInMV_label" => "Pokaż obrazy w widoku miesiąca",
"showImgInMV_text" => "Włącz/wyłącz wyświetlanie w widoku miesiąca miniatur obrazów dodanych do jednego z pól opisu wydarzenia. Po włączeniu miniatury będą wyświetlane w komórkach dnia, a po wyłączeniu miniatury będą wyświetlane w polach wyświetlanych po najechaniu myszką.",
"urls" => "Linki URL",
"emails" => "Linki e-mail",
"monthInDCell_label" => "Miesiąc w każdej komórce dnia",
"monthInDCell_text" => "Wyświetlaj dla każdego dnia w widoku miesiąca 3-literową nazwę miesiąca",
"scrollDCell_label" => "Używaj paska przewijania w komórkach dnia",
"scrollDCell_text" => "Jeśli w widoku miesiąca komórka dnia jest zbyt mała, zamiast zwiększać wysokość komórki dnia, pojawi się pionowy pasek przewijania.",

//settings.php - date/time settings
"dateFormat_label" => "Format daty wydarzenia (dd mm rrrr)",
"dateFormat_text" => "Ciąg tekstowy definiujący format dat wydarzeń w widokach kalendarza i polach wprowadzania danych.<br>Możliwe znaki: y = rok, m = miesiąc i d = dzień.<br>Znak niealfanumeryczny może być używany jako separator i zostanie skopiowany dosłownie.<br>Przykłady:<br>y-m-d: 2024-10-31<br>m.d.y: 10.31.2024<br>d/m/y: 31/10/2024",
"dateFormat_expl" => "np. y.m.d: 2024.10.31",
"MdFormat_label" => "Format daty (dd miesiąc)",
"MdFormat_text" => "Ciąg tekstowy definiujący format dat składający się z miesiąca i dnia.<br>Możliwe znaki: M = miesiąc w tekście, d = dzień cyframi.<br>Znak niealfanumeryczny może być używany jako separator i zostanie skopiowany dosłownie.<br>Przykłady:<br>d M: 12 kwietnia<br>M, d: lipiec, 14",
"MdFormat_expl" => "np. M, d: lipiec, 14",
"MdyFormat_label" => "Format daty (dd miesiąc rrrr)",
"MdyFormat_text" => "Ciąg tekstowy definiujący format dat składających się z dnia, miesiąca i roku.<br>Możliwe znaki: d = dzień cyframi, M = miesiąc w tekście, y = rok cyframi.<br>Znak niealfanumeryczny może być używany jako separator i zostanie skopiowany dosłownie.<br>Przykłady:<br>d M y: 12 kwietnia 2024<br>M d, y: 8 lipca 2024 r.",
"MdyFormat_expl" => "np. M d, y: 8 lipca 2024 r.",
"MyFormat_label" => "Format daty (miesiąc yyyy)",
"MyFormat_text" => "Ciąg tekstowy definiujący format dat składających się z miesiąca i roku.<br>Możliwe znaki: M = miesiąc w tekście, y = rok cyframi.<br>Znak niealfanumeryczny może być używany jako separator i zostanie skopiowany dosłownie.<br>Przykłady:<br>M y: kwiecień 2024 r.<br>y - M: 2024 - lipiec",
"MyFormat_expl" => "np. M y: kwiecień 2024",
"DMdFormat_label" => "Format daty (dzień tygodnia dd miesiąc)",
"DMdFormat_text" => "Ciąg tekstowy definiujący format dat składających się z dnia tygodnia, dnia i miesiąca.<br>Możliwe znaki: WD = dzień tygodnia w tekście, M = miesiąc w tekście, d = dzień cyframi.<br>Znak niealfanumeryczny może być używany jako separator i zostanie skopiowany dosłownie.<br>Przykłady:<br>WD d M: piątek 12 kwietnia<br>WD, M d: poniedziałek, 14 lipca",
"DMdFormat_expl" => "np. WD - M d: niedziela - 6 kwietnia",
"DMdyFormat_label" => "Format daty (dzień tygodnia dd miesiąc rrrr)",
"DMdyFormat_text" => "Ciąg tekstowy definiujący format dat składających się z dnia tygodnia, dnia, miesiąca i roku.<br>Możliwe znaki: WD = dzień tygodnia w tekście, M = miesiąc w tekście, d = dzień cyframi, y = rok cyframi.<br>Znak niealfanumeryczny może być używany jako separator i zostanie skopiowany dosłownie.<br>Przykłady:<br>WD d M y: piątek 13 kwietnia 2024<br>WD - M d, y: poniedziałek - 16 lipca 2024",
"DMdyFormat_expl" => "np. WD, M d, r: poniedziałek, 16 lipca 2024 r.",
"timeFormat_label" => "Format czasu (hh mm)",
"timeFormat_text" => "Ciąg tekstowy definiujący format godzin wydarzeń w widokach kalendarza i polach wprowadzania danych.<br>Możliwe znaki: h = godziny, H = godziny z zerami na początku, m = minuty, a = am/pm (opcjonalnie), A = AM/PM (opcjonalnie).<br>Znak niealfanumeryczny może być używany jako separator i zostanie skopiowany dosłownie.<br>Przykłady:<br>h:m: 18:35<br>h.m a: 6.35 pm<br>H:mA: 06:35PM",
"timeFormat_expl" => "np. h:m: 22:35 i h:mA: 10:35PM",
"weekNumber_label" => "Wyświetlanie numerów tygodni",
"weekNumber_text" => "Wyświetlanie numerów tygodni w odpowiednich widokach można włączyć/wyłączyć",
"time_format_us" => "12-godzinny AM/PM",
"time_format_eu" => "24-godzinny",
"sunday" => "Niedziela",
"monday" => "Poniedziałek",
"time_zones" => "STREFY CZASOWE",
"dd_mm_yyyy" => "dd-mm-yyyy",
"mm_dd_yyyy" => "mm-dd-yyyy",
"yyyy_mm_dd" => "yyyy-mm-dd",

//settings.php - file uploads settings
"maxUplSize_label" => "Maksymalny rozmiar przesyłanego pliku",
"maxUplSize_text" => "Maksymalny dozwolony rozmiar pliku, gdy użytkownicy przesyłają pliki załączników lub miniatur.<br>Uwaga: Większość instalacji PHP ma to maksimum ustawione na 2 MB (plik php_ini) ",
"attTypes_label" => "Typy plików załączników",
"attTypes_text" => "Lista rozdzielona przecinkami z prawidłowymi typami plików załączników, które można przesłać (np. '.pdf,.jpg,.gif,.png,.mp4,.avi')",
"tnlTypes_label" => "Typy plików miniatur",
"tnlTypes_text" => "Lista rozdzielona przecinkami z prawidłowymi typami plików miniatur, które można przesłać (np. '.jpg,.jpeg,.gif,.png')",
"tnlMaxSize_label" => "Miniatura - maksymalny rozmiar",
"tnlMaxSize_text" => "Maksymalny rozmiar miniatury. Jeśli użytkownicy przesyłają większe miniatury, zostaną one automatycznie przeskalowane do maksymalnego rozmiaru.<br>Uwaga: Wysokie miniatury rozciągną komórki dnia w widoku miesiąca, co może spowodować niepożądane efekty.",
"tnlDelDays_label" => "Margines usuwania miniatury",
"tnlDelDays_text" => "Jeśli miniatura jest używana od tej liczby dni, nie można jej usunąć.<br>Wartość 0 dni oznacza, że ​​miniatury nie można usunąć.",
"days" => "dni",
"mbytes" => "MB",
"wxhinpx" => "Szer. x wys. w pikselach",

//settings.php - reminders settings
"services_label" => "Dostępne usługi wiadomości",
"services_text" => "Usługi dostępne dla wysyłanych przypomnień o zdarzeniach. Jeśli usługa nie jest wybrana, odpowiednia sekcja w oknie Zdarzenie zostanie pominięta. Jeśli żadna usługa nie jest wybrana, żadne przypomnienia o zdarzeniach nie zostaną wysłane.",
"msgLogging_label" => "Notification message logging",
"msgLogging_text" => "When checked, the notification messages sent are logged in the messages.log file. The 'weeks' field specifies how long the logged messages should be kept",
"smsCarrier_label" => "Szablon operatora SMS",
"smsCarrier_text" => "Szablon operatora SMS jest używany do kompilacji adresu e-mail bramki SMS: ppp#sss@carrier, gdzie . . .<br>• ppp: opcjonalny ciąg tekstowy, który należy dodać przed numerem telefonu<br>• #: symbol zastępczy numeru telefonu komórkowego odbiorcy (kalendarz zastąpi # numerem telefonu)<br>• sss: opcjonalny ciąg tekstowy, który należy wstawić po numerze telefonu, np. nazwa użytkownika i hasło, wymagane przez niektórych operatorów<br>• @: znak separatora<br>• carrier: adres operatora (np. mail2sms.com)<br>Przykłady szablonów: #@xmobile.com, 0#@carr2.int, #myunmypw@sms.gway.net.",
"smsCountry_label" => "Kod kraju SMS",
"smsCountry_text" => "Jeśli bramka SMS znajduje się w innym kraju niż kalendarz, należy podać kod kraju, w którym używany jest kalendarz.<br>Wybierz, czy wymagany jest prefiks '+' czy '00'.",
"smsSubject_label" => "Szablon tematu SMS",
"smsSubject_text" => "Jeśli określono, tekst w tym szablonie zostanie skopiowany do pola tematu wiadomości e-mail SMS wysyłanych do operatora. Tekst może zawierać znak #, który zostanie zastąpiony numerem telefonu kalendarza lub właściciela wydarzenia (w zależności od ustawienia powyżej).<br>Przykład: 'FROMPHONENUMBER=#'.",
"smsAddLink_label" => "Dodaj link do raportu o wydarzeniu do SMS",
"smsAddLink_text" => "Po zaznaczeniu do każdego SMS-a zostanie dodany link do raportu o wydarzeniu. Po otwarciu tego linku na telefonie komórkowym odbiorcy będą mogli wyświetlić szczegóły wydarzenia.",
"maxLenSms_label" => "Maksymalna długość wiadomości SMS",
"maxLenSms_text" => "Wiadomości SMS są wysyłane z kodowaniem znaków UTF-8. Wiadomości do 70 znaków będą skutkować jedną wiadomością SMS; wiadomości > 70 znaków, z wieloma znakami Unicode, mogą być dzielone na wiele wiadomości.",
"calPhone_label" => "Numer telefonu w kalendarzu",
"calPhone_text" => "Numer telefonu używany jako identyfikator nadawcy podczas wysyłania wiadomości SMS z powiadomieniem.<br>Format: wolny, maks. 20 cyfr (niektóre kraje wymagają numeru telefonu, inne kraje akceptują również znaki alfabetyczne).<br>Jeśli usługa SMS nie jest aktywna lub jeśli nie zdefiniowano szablonu tematu wiadomości SMS, to pole może być puste.",
"notSenderEml_label" => "Dodaj pole 'Odpowiedz do' do wiadomości e-mail",
"notSenderEml_text" => "Po zaznaczeniu, wiadomości e-mail z powiadomieniem będą zawierać pole 'Odpowiedz do' z adresem e-mail właściciela wydarzenia, na który odbiorca może odpowiedzieć.",
"notSenderSms_label" => "Nadawca wiadomości SMS z powiadomieniem",
"notSenderSms_text" => "Gdy kalendarz wysyła wiadomości SMS z przypomnieniem, identyfikator nadawcy wiadomości SMS może być numerem telefonu kalendarza lub numerem telefonu użytkownika, który utworzył wydarzenie.<br>Jeśli wybrano 'użytkownik', a konto użytkownika nie ma określonego numeru telefonu, zostanie użyty numer telefonu kalendarza.<br>W przypadku numeru telefonu użytkownika odbiorca może odpowiedzieć na message.",
"defRecips_label" => "Domyślna lista odbiorców",
"defRecips_text" => "Jeśli określono, będzie to domyślna lista odbiorców powiadomień e-mail i/lub SMS w oknie Zdarzenie. Jeśli to pole pozostanie puste, domyślnym odbiorcą będzie właściciel zdarzenia.",
"maxEmlCc_label" => "Maksymalna liczba odbiorców na e-mail",
"maxEmlCc_text" => "Zwykle dostawcy usług internetowych zezwalają na maksymalną liczbę odbiorców na e-mail. Jeśli podczas wysyłania przypomnień e-mail lub SMS liczba odbiorców jest większa niż liczba określona tutaj, e-mail zostanie podzielony na wiele wiadomości, każda z określoną maksymalną liczbą odbiorców.",
"emlFootnote_label" => "Przypis do wiadomości e-mail z przypomnieniem",
"emlFootnote_text" => "Tekst w dowolnym formacie, który zostanie dodany jako akapit na końcu wiadomości e-mail z przypomnieniem. W tekście dozwolone są znaczniki HTML.",
"mailServer_label" => "Serwer pocztowy",
"mailServer_text" => "Poczta PHP nadaje się do nieuwierzytelnianej poczty w małych ilościach. W przypadku większej liczby wiadomości lub gdy wymagane jest uwierzytelnienie, należy używać poczty SMTP.<br>Używanie poczty SMTP wymaga serwera poczty SMTP. Parametry konfiguracji, które mają być używane dla serwera SMTP, muszą zostać określone poniżej.",
"smtpServer_label" => "Nazwa serwera SMTP",
"smtpServer_text" => "Jeśli wybrano pocztę SMTP, należy tutaj określić nazwę serwera SMTP. Na przykład serwer SMTP gmail: smtp.gmail.com.",
"smtpPort_label" => "Numer portu SMTP",
"smtpPort_text" => "Jeśli wybrano pocztę SMTP, należy tutaj określić numer portu SMTP. Na przykład 25, 465 lub 587. Na przykład Gmail używa numeru portu 465.",
"smtpSsl_label" => "SSL (Secure Sockets Layer)",
"smtpSsl_text" => "Jeśli wybrano pocztę SMTP, należy tutaj wybrać, czy ma być włączona warstwa Secure Sockets Layer (SSL). Dla gmail: włączone",
"smtpAuth_label" => "Uwierzytelnianie SMTP",
"smtpAuth_text" => "Jeśli wybrano uwierzytelnianie SMTP, nazwa użytkownika i hasło określone poniżej zostaną użyte do uwierzytelnienia poczty SMTP.<br>Na przykład dla gmail nazwa użytkownika to część adresu e-mail przed znakiem @.",
"tlgToken_label" => "Token telegramu",
"tlgToken_text" => "Token telegramu w następującym formacie: &lt;id bota&gt;:&lt;hash bota&gt;. Aby uzyskać szczegółowe informacje, zobacz installation_guide.html, sekcja Wiadomości powiadomień o zdarzeniach.",
"cc_prefix" => "Kod kraju zaczyna się od prefiksu + lub 00",
"weeks" => "Tygodnie",
"general" => "Ogólne",
"php_mail" => "Poczta PHP",
"smtp_mail" => "Poczta SMTP (uzupełnij pola poniżej)",

//settings.php - periodic function settings
"cronHost_label" => "Host zadania cron",
"cronHost_text" => "Określ, gdzie hostowane jest zadanie cron, które okresowo uruchamia skrypt 'lcalcron.php'.<br>• lokalne: zadanie cron jest uruchamiane na tym samym serwerze co kalendarz<br>• zdalne: zadanie cron jest uruchamiane na serwerze zdalnym lub lcalcron.php jest uruchamiany ręcznie (testowanie)<br>• adres IP: zadanie cron jest uruchamiane na serwerze zdalnym o określonym adresie IP.",
"cronSummary_label" => "Podsumowanie zadania cron administratora",
"cronSummary_text" => "Wyślij podsumowanie zadania cron do administratora kalendarza.<br>Włączenie jest przydatne tylko wtedy, gdy zadanie cron zostało aktywowane dla kalendarza.",
"icsExport_label" => "Codzienny eksport zdarzeń iCal",
"icsExport_text" => "Jeśli włączone: Wszystkie zdarzenia w zakresie dat od -1 tygodnia do +1 roku zostaną eksportować w formacie iCalendar w pliku .ics w folderze 'files'.<br>Nazwa pliku będzie nazwą kalendarza ze spacjami zastąpionymi podkreśleniami. Stare pliki zostaną nadpisane nowymi plikami.",
"eventExp_label" => "Dni wygaśnięcia zdarzenia",
"eventExp_text" => "Liczba dni po dacie zakończenia zdarzenia, kiedy zdarzenie wygasa i zostanie automatycznie usunięte.<br>Jeśli 0 lub jeśli nie jest uruchomione żadne zadanie cron, żadne zdarzenia nie zostaną automatycznie usunięte.",
"maxNoLogin_label" => "Maks. liczba dni bez logowania",
"maxNoLogin_text" => "Jeśli użytkownik nie zalogował się przez tę liczbę dni, jego/jej konto zostanie automatycznie usunięte.<br>Jeśli ta wartość zostanie ustawiona na 0, konta użytkowników nigdy nie zostaną usunięte",
"local" => "lokalny",
"remote" => "zdalny",
"ip_address" => "adres IP",

//settings.php - mini calendar / sidebar settings
"popFieldsSbar_label" => "Pola zdarzeń - pole najechania kursorem na pasek boczny",
"popFieldsSbar_text" => "Pola zdarzeń, które mają być wyświetlane w nakładce, gdy użytkownik najedzie kursorem na zdarzenie na samodzielnym pasku bocznym, można określić za pomocą sekwencji liczb.<br>Jeśli nie określono żadnych pól, nie zostanie wyświetlone żadne pole najechania kursorem.",
"showLinkInSB_label" => "Pokaż linki na pasku bocznym",
"showLinkInSB_text" => "Wyświetl adresy URL z opisu zdarzenia jako hiperłącze na pasku bocznym nadchodzących zdarzeń",
"sideBarDays_label" => "Dni do przejrzenia na pasku bocznym",
"sideBarDays_text" => "Liczba dni do przejrzenia na pasku bocznym zdarzeń.",

//login.php
"log_log_in" => "Zaloguj",
"log_remember_me" => "Zapamiętaj mnie",
"log_register" => "Zarejestruj",
"log_change_my_data" => "Zmień moje dane",
"log_save" => "Zapisz",
"log_done" => "Zakończono",
"log_un_or_em" => "Nazwa użytkownika lub e-mail",
"log_un" => "Nazwa użytkownika",
"log_em" => "E-mail",
"log_ph" => "Numer telefonu komórkowego",
"log_tg" => "Identyfikator czatu Telegram",
"log_answer" => "Twoja odpowiedź",
"log_pw" => "Hasło",
"log_expir_date" => "Data wygaśnięcia konta",
"log_account_expired" => "To konto ma wygasł",
"log_new_un" => "Nowa nazwa użytkownika",
"log_new_em" => "Nowy adres e-mail",
"log_new_pw" => "Nowe hasło",
"log_con_pw" => "Potwierdź hasło",
"log_pw_msg" => "Oto dane logowania do kalendarza",
"log_pw_subject" => "Twoje hasło",
"log_npw_subject" => "Twoje nowe hasło",
"log_npw_sent" => "Twoje nowe hasło do przesyłki kurierskiej.",
"log_registered" => "Rejestracja zakończona sukcesem - Twoje hasło zostało wysłane pocztą elektroniczną",
"log_em_problem_not_sent" => "Problem z pocztą elektroniczną - nie udało się wysłać hasła",
"log_em_problem_not_noti" => "Problem z pocztą elektroniczną - nie udało się powiadomić administratora",
"log_un_exists" => "Nazwa użytkownika już istnieje istnieje",
"log_em_exists" => "Adres e-mail już istnieje",
"log_un_invalid" => "Nieprawidłowa nazwa użytkownika (minimalna długość 2: A-Z, a-z, 0-9 i _-.) ",
"log_em_invalid" => "Nieprawidłowy adres e-mail",
"log_ph_invalid" => "Nieprawidłowy numer telefonu komórkowego",
"log_tg_invalid" => "Nieprawidłowy identyfikator czatu Telegram",
"log_sm_nr_required" => "SMS: wymagany numer telefonu komórkowego",
"log_tg_id_required" => "Telegram: wymagany identyfikator czatu",
"log_sra_wrong" => "Nieprawidłowa odpowiedź na pytanie",
"log_sra_wrong_4x" => "Odpowiedziałeś nieprawidłowo 4 razy — spróbuj ponownie za 30 minut",
"log_un_em_invalid" => "Nazwa użytkownika/adres e-mail są nieprawidłowe",
"log_un_em_pw_invalid" => "Nazwa użytkownika/adres e-mail lub hasło są nieprawidłowe.",
"log_pw_error" => "Hasła nie pasują",
"log_no_un_em" => "Nie podano nazwy użytkownika/emaila.",
"log_no_un" => "Wprowadź nazwę użytkownika",
"log_no_em" => "Wprowadź adres e-mail",
"log_no_pw" => "Nie podano hasła.",
"log_no_rights" => "Logowanie odrzucone: nie masz uprawnień do przeglądania - skontaktuj się z administratorem",
"log_send_new_pw" => "Wyślij nowe hasło",
"log_new_un_exists" => "Nowa nazwa użytkownika już istnieje",
"log_new_em_exists" => "Nowy adres e-mail już istnieje",
"log_ui_language" => "Interfejs użytkownika język",
"log_new_reg" => "Rejestracja nowego użytkownika",
"log_date_time" => "Data / godzina",
"log_time_out" => "Przekroczono limit czasu",

//categories.php
"cat_list" => "Spis kategorii",
"cat_edit" => "Edytuj",
"cat_delete" => "Usuń",
"cat_add_new" => "Dodaj Nową Kategorię",
"cat_add" => "Dodaj Kategorię",
"cat_edit_cat" => "Edytuj Kategorię",
"cat_sort" => "Sortuj według nazwy",
"cat_cat_name" => "Nazwa kategorii",
"cat_symbol" => "Symbol",
"cat_symbol_repms" => "Symbol kategorii (zastępuje mini kwadrat)",
"cat_symbol_eg" => "np. A, X, ♥, ⛛",
"cat_matrix_url_link" => "Link URL (wyświetlany w widoku macierzy)",
"cat_seq_in_menu" => "Kolejność w menu",
"cat_cat_color" => "Kolor kategorii",
"cat_text" => "Tekstu",
"cat_background" => "Tło",
"cat_select_color" => "Wybierz Kolor",
"cat_subcats" => "Pod-<br>kategorie",
"cat_subcats_opt" => "Liczba podkategorii (opcjonalnie)",
"cat_copy_from" => "Kopiuj z",
"cat_eml_changes_to" => "Wyślij zmiany wydarzenia do",
"cat_url" => "URL",
"cat_name" => "Nazwa",
"cat_subcat_note" => "Uwaga: obecnie istniejące podkategorie mogą być już używane do wydarzeń",
"cat_save" => "Uaktualnij Kategorię",
"cat_added" => "Kategoria Dodana",
"cat_updated" => "Kategoria Uaktualniona",
"cat_deleted" => "Kategoria Usunięta",
"cat_not_added" => "Kategoria Nie Dodana",
"cat_not_updated" => "Kategoria Nie Uaktualniona",
"cat_not_deleted" => "Kategoria Nie Usunięta",
"cat_nr" => "#",
"cat_repeat" => "Powtarzaj",
"cat_every_day" => "codziennie",
"cat_every_week" => "co tydzień",
"cat_every_month" => "co miesiąc",
"cat_every_year" => "co roku",
"cat_overlap" => "Dozwolone<br>nakładanie się (gap)",
"cat_need_approval" => "Wydarzenia wymagają<br>zatwierdzenia",
"cat_no_overlap" => "Niedozwolone jest nakładanie się",
"cat_same_category" => "ta sama kategoria",
"cat_all_categories" => "wszystkie kategorie",
"cat_gap" => "luka",
"cat_ol_error_text" => "Komunikat o błędzie, jeśli nakładanie się",
"cat_no_ol_note" => "Należy pamiętać, że istniejące już zdarzenia nie są sprawdzane i w związku z tym mogą się nakładać",
"cat_ol_error_msg" => "nakładanie się zdarzeń - wybierz inny czas",
"cat_no_ol_error_msg" => "Brak komunikatu o błędzie nakładania się",
"cat_duration" => "Wydarzenie<br>czas trwania<br>! = fixed",
"cat_default" => "domyślne (brak czasu zakończenia)",
"cat_fixed" => "fixed",
"cat_event_duration" => "Czas trwania wydarzenia",
"cat_olgap_invalid" => "Nieprawidłowy odstęp nakładania się",
"cat_duration_invalid" => "Nieprawidłowy czas trwania wydarzenia",
"cat_no_url_name" => "Brak nazwy łącza URL",
"cat_invalid_url" => "Nieprawidłowy link URL",
"cat_day_color" => "Kolor dnia",
"cat_day_color1" => "Kolor dnia (widok roku/matrycy)",
"cat_day_color2" => "Kolor dnia (widok miesiąca/tygodnia/dnia)",
"cat_approve" => "Wydarzenia wymagają zatwierdzenia",
"cat_check_mark" => "Znacznik wyboru",
"cat_not_list" => "Powiadom<br>listę",
"cat_label" => "etykieta",
"cat_mark" => "oznacz",
"cat_name_missing" => "Brakuje nazwy kategorii",
"cat_mark_label_missing" => "Brakuje znacznika wyboru/etykiety",

//users.php
"usr_list_of_users" => "Spis Użytkowników",
"usr_name" => "Nazwa Użytkownika",
"usr_email" => "E-mail",
"usr_phone" => "Numer telefonu komórkowego",
"usr_phone_br" => "Numer<br>telefonu komórkowego",
"usr_tg_id" => "Identyfikator czatu Telegram",
"usr_tg_id_br" => "Identyfikator<br>czatu Telegram",
"usr_not_via" => "Powiadom przez",
"usr_not_via_br" => "Powiadom<br>przez",
"usr_language" => "Język",
"usr_ui_language" => "Język interfejsu użytkownika",
"usr_group" => "Grupa",
"usr_password" => "Hasło",
"usr_expir_date" => "Data wygaśnięcia konta",
"usr_select_exp_date" => "Wybierz datę wygaśnięcia",
"usr_blank_none" => "puste: brak daty wygaśnięcia",
"usr_expires" => "Wygasa",
"usr_edit_user" => "Edytuj Profil Użytkownika",
"usr_add" => "Dodaj Użytkownika",
"usr_edit" => "Edytuj",
"usr_delete" => "Usuń",
"usr_login_0" => "Pierwszy login",
"usr_login_1" => "Ostatni login",
"usr_login_cnt" => "Logowania",
"usr_add_profile" => "Dodaj Profil",
"usr_upd_profile" => "Uaktualnij Profil",
"usr_if_changing_pw" => "Tylko przy zmianie hasła",
"usr_pw_not_updated" => "Hasło Nie Zostało Uaktualnione",
"usr_added" => "Użytkownik dodany",
"usr_updated" => "Profil użytkownika został uaktualniony",
"usr_deleted" => "Użytkownik został usunięty",
"usr_not_deleted" => "Użytkownik nie został usunięty",
"usr_cred_required" => "Nazwa Użytkownika, Email oraz hasło są wymagane",
"usr_name_exists" => "Nazwa Użytkownika już istnieje",
"usr_email_exists" => "Adres email już istnieje",
"usr_un_invalid" => "Nieprawidłowa nazwa użytkownika (minimalna długość 2: A-Z, a-z, 0-9 i _-.) ",
"usr_em_invalid" => "Nieprawidłowy adres email adres",
"usr_ph_invalid" => "Nieprawidłowy numer telefonu komórkowego",
"usr_tg_invalid" => "Nieprawidłowy identyfikator czatu Telegram",
"usr_xd_invalid" => "Nieprawidłowa data wygaśnięcia konta",
"usr_cant_delete_yourself" => "Nie możesz usunąć siebie",
"usr_go_to_groups" => "Przejdź do grup",
"usr_all_cats" => "Wszystkie kategorie",
"usr_select" => "Wybierz",
"usr_transfer" => "Przenieś",
"usr_transfer_evts" => "Przenieś wydarzenia",
"usr_transfer_ownership" => "Przenieś własność wydarzeń",
"usr_cur_owner" => "Aktualny właściciel",
"usr_new_owner" => "Nowy właściciel",
"usr_event_cat" => "Wydarzenie kategoria",
"usr_sdate_between" => "Data rozpoczęcia pomiędzy",
"usr_cdate_between" => "Data utworzenia pomiędzy",
"usr_select_start_date" => "Wybierz datę początkową",
"usr_select_end_date" => "Wybierz datę końcową",
"usr_blank_no_limit" => "Pusta data: brak limitu",
"usr_no_undone" => "UWAGA, TEJ TRANSAKCJI NIE MOŻNA COFNĄĆ",
"usr_invalid_sdata" => "Nieprawidłowa data rozpoczęcia",
"usr_invalid_cdata" => "Nieprawidłowa data utworzenia",
"usr_edate_lt_sdate" => "Data zakończenia przed datą rozpoczęcia",
"usr_no_new_owner" => "Nie określono nowego właściciela",
"usr_evts_transferred" => "Gotowe. Wydarzenia przeniesione",

//groups.php
"grp_list_of_groups" => "Lista grup użytkowników",
"grp_name" => "Nazwa grupy",
"grp_priv" => "Prawa dostępu",
"grp_categories" => "Kategorie",
"grp_all_cats" => "wszystkie kategorie",
"grp_rep_events" => "Powtarzające się<br>wydarzenia",
"grp_m-d_events" => "Wydarzenia<br>wielodniowe",
"grp_priv_events" => "Wydarzenia<br>prywatne",
"grp_upload_files" => "Przesyłanie<br>plików",
"grp_tnail_privs" => "Uprawnienia<br>do miniatur",
"grp_priv0" => "Brak praw",
"grp_priv1" => "Podgląd Kalendarza",
"grp_priv2" => "Dodawanie/Edycja Własnych Wydarzeń",
"grp_priv3" => "Dodawanie/Edycja Wszystkich Wydarzeń",
"grp_priv4" => "Dodawanie/Edycja + manager",
"grp_priv9" => "Uprawnienia Administratora",
"grp_may_post_revents" => "Może publikować powtarzające się wydarzenia",
"grp_may_post_mevents" => "Może publikować wydarzenia wielodniowe",
"grp_may_post_pevents" => "Może publikować wydarzenia prywatne",
"grp_may_upload_files" => "Może przesyłać pliki",
"grp_tn_privs" => "Uprawnienia do miniatur",
"grp_tn_privs00" => "brak",
"grp_tn_privs11" => "zobacz wszystkie",
"grp_tn_privs20" => "zarządzaj własnymi",
"grp_tn_privs21" => "m. własne/v. all",
"grp_tn_privs22" => "zarządzaj wszystkim",
"grp_edit_group" => "Edytuj Grupę",
"grp_sub_to_rights" => "Podlega uprawnieniom użytkownika",
"grp_view" => "Wyświetl",
"grp_add" => "Dodaj",
"grp_edit" => "Edytuj",
"grp_delete" => "Usuń",
"grp_add_group" => "Dodaj Grupę",
"grp_upd_group" => "Uaktualnij Grupę",
"grp_added" => "Grupa została dodana",
"grp_updated" => "Grupa została zaktualizowana",
"grp_deleted" => "Grupa została usunięta",
"grp_not_deleted" => "Grupa nie została usunięta",
"grp_in_use" => "Grupa jest w use",
"grp_cred_required" => "Nazwa Grupy, Prawa Dostępu i Kategorie są wymagane",
"grp_name_exists" => "Nazwa grupy już istnieje",
"grp_name_invalid" => "Nieprawidłowa nazwa grupy (minimalna długość 2: A-Z, a-z, 0-9, i _-.) ",
"grp_check_add" => "Co najmniej jedno pole wyboru w kolumnie Dodaj musi być zaznaczone",
"grp_background" => "kolor tła",
"grp_select_color" => "Wybierz Kolor",
"grp_invalid_color" => "Nieprawidłowy format koloru (#XXXXXX gdzie X = wartość HEX)",
"grp_go_to_users" => "Przejdź do Użytkownicy",

//texteditor.php
"edi_text_editor" => "Edytuj tekst informacyjny",
"edi_file_name" => "File name",
"edi_save" => "Zapisz tekst",
"edi_backup" => "Tekst kopii zapasowej",
"edi_select_file" => "Select file",
"edi_info_text" => "Information text",
"edi_pub_recips" => "Public recipients",
"edi_recips_list" => "Recipients list",
"edi_new_recips_list" => "New recipients list",
"edi_no_file_name" => "No file name specified",
"edi_no_text" => "Brak tekstu",
"edi_confirm_changes" => "The text changes have not been saved\\nDo you want to continue?", //don't remove '\\n'
"edi_text_saved" => "Tekst zapisany w pliku $1",

//database.php
"mdb_dbm_functions" => "Funkcje bazy danych",
"mdb_noshow_tables" => "Nie można pobrać tabeli(tabel)",
"mdb_noshow_restore" => "Nie wybrano pliku źródłowej kopii zapasowej lub plik jest za duży, aby go przesłać",
"mdb_file_not_sql" => "Plik źródłowej kopii zapasowej powinien być plikiem SQL (rozszerzenie „.sql”)",
"mdb_db_content" => "Zawartość bazy danych",
"mdb_total_evenst" => "Łączna liczba zdarzeń",
"mdb_evts_older_1m" => "Zdarzenia starsze niż 1 miesiąc",
"mdb_evts_older_6m" => "Zdarzenia starsze niż 6 miesięcy",
"mdb_evts_older_1y" => "Zdarzenia starsze niż 1 rok",
"mdb_evts_deleted" => "Całkowita liczba usuniętych zdarzeń",
"mdb_not_removed" => "jeszcze nieusunięte z bazy danych",
"mdb_total_cats" => "Całkowita liczba kategorii",
"mdb_total_users" => "Całkowita liczba użytkowników",
"mdb_total_groups" => "Całkowita liczba grup użytkowników",
"mdb_compact" => "Kompaktuj bazę danych",
"mdb_compact_table" => "Kompaktuj tabelę",
"mdb_compact_error" => "Błąd",
"mdb_compact_done" => "Zakończono",
"mdb_purge_done" => "Usunięte zdarzenia zostały ostatecznie usunięte",
"mdb_backup" => "Kopia zapasowa bazy danych",
"mdb_backup_table" => "Kopia zapasowa tabeli",
"mdb_backup_file" => "Kopia zapasowa plik",
"mdb_backup_done" => "Zakończono",
"mdb_records" => "rekordy",
"mdb_restore" => "Przywróć bazę danych",
"mdb_restore_table" => "Przywróć tabelę",
"mdb_inserted" => "wstawione rekordy",
"mdb_db_restored" => "Baza danych przywrócona",
"mdb_db_upgraded" => "Baza danych uaktualniona",
"mdb_no_bup_match" => "Plik kopii zapasowej nie pasuje do wersji kalendarza.<br>Baza danych nie została przywrócona.",
"mdb_events" => "Wydarzenia",
"mdb_delete" => "usuń",
"mdb_undelete" => "odzyskaj",
"mdb_between_dates" => "wykluczenia między",
"mdb_deleted" => "Wydarzenia removed",
"mdb_undeleted" => "Przywrócone zdarzenia",
"mdb_file_saved" => "Plik kopii zapasowej zapisany w folderze 'files' na serwerze.",
"mdb_file_name" => "Nazwa pliku",
"mdb_start" => "Start",
"mdb_no_function_checked" => "Brak wybranych funkcji",
"mdb_write_error" => "Zapisywanie pliku kopii zapasowej nie powiodło się<br>Sprawdź uprawnienia katalogu 'files/'",

//import/export.php
"iex_file" => "Wybrany plik",
"iex_file_name" => "Nazwa pliku docelowego",
"iex_file_description" => "Opis pliku iCal",
"iex_filters" => "Filtry zdarzeń",
"iex_export_usr" => "Eksportuj profile użytkowników",
"iex_import_usr" => "Importuj profile użytkowników",
"iex_upload_ics" => "Prześlij plik iCal",
"iex_create_ics" => "Utwórz plik iCal",
"iex_tz_adjust" => "Dostosowanie strefy czasowej",
"iex_upload_csv" => "Prześlij plik CSV",
"iex_upload_file" => "Prześlij plik",
"iex_create_file" => "Utwórz plik",
"iex_download_file" => "Pobierz Plik",
"iex_fields_sep_by" => "Pola rozdzielone przez",
"iex_birthday_cat_id" => "Identyfikator kategorii urodzin",
"iex_default_grp_id" => "Identyfikator domyślnej grupy użytkowników",
"iex_default_cat_id" => "Identyfikator domyślnej kategorii",
"iex_default_pword" => "Hasło domyślne",
"iex_if_no_pw" => "Jeśli nie określono hasła",
"iex_replace_users" => "Zastąp istniejących użytkowników",
"iex_if_no_grp" => "jeśli nie znaleziono grupy użytkowników",
"iex_if_no_cat" => "jeśli nie znaleziono kategorii",
"iex_import_events_from_date" => "Importuj zdarzenia występujące od",
"iex_no_events_from_date" => "Nie znaleziono zdarzeń od określonej daty data",
"iex_see_insert" => "zobacz instrukcje po prawej stronie",
"iex_no_file_name" => "Brak nazwy pliku",
"iex_no_begin_tag" => "nieprawidłowy plik iCal (brak znacznika BEGIN)",
"iex_bad_date" => "Nieprawidłowa data",
"iex_date_format" => "Format daty zdarzenia",
"iex_time_format" => "Format czasu zdarzenia",
"iex_number_of_errors" => "Liczba błędów na liście",
"iex_bgnd_highlighted" => "podświetlone tło",
"iex_verify_event_list" => "Sprawdź listę zdarzeń, popraw ewentualne błędy i kliknij",
"iex_add_events" => "Dodaj zdarzenia do bazy danych",
"iex_verify_user_list" => "Sprawdź listę użytkowników, popraw ewentualne błędy i click",
"iex_add_users" => "Dodaj użytkowników do bazy danych",
"iex_select_ignore_birthday" => "Zaznacz pola wyboru Ignoruj ​​i Urodziny, jeśli to konieczne",
"iex_select_ignore" => "Zaznacz pole wyboru Ignoruj, aby zignorować wydarzenie",
"iex_check_all_ignore" => "Przełącz wszystkie pola wyboru Ignoruj",
"iex_title" => "Tytuł",
"iex_venue" => "Miejsce",
"iex_owner" => "Właściciel",
"iex_category" => "Kategoria",
"iex_date" => "Data",
"iex_end_date" => "Data końcowa",
"iex_start_time" => "Czas rozpoczęcia",
"iex_end_time" => "Czas zakończenia",
"iex_description" => "Opis",
"iex_repeat" => "Powtórz",
"iex_birthday" => "Urodziny",
"iex_ignore" => "Ignoruj",
"iex_events_added" => "dodane wydarzenia",
"iex_events_dropped" => "usunięte wydarzenia (już obecne)",
"iex_users_added" => "dodani użytkownicy",
"iex_users_deleted" => "usunięci użytkownicy",
"iex_csv_file_error_on_line" => "Błąd pliku CSV w linii",
"iex_between_dates" => "występujące między",
"iex_changed_between" => "Dodane/zmodyfikowane między",
"iex_select_date" => "Wybierz datę",
"iex_select_start_date" => "Wybierz datę początkową",
"iex_select_end_date" => "Wybierz datę końcową",
"iex_group" => "Grupa użytkowników",
"iex_name" => "Nazwa użytkownika",
"iex_email" => "Adres e-mail",
"iex_phone" => "Numer telefonu",
"iex_msgID" => "ID czatu",
"iex_lang" => "Język",
"iex_pword" => "Hasło",
"iex_all_groups" => "wszystkie grupy",
"iex_all_cats" => "wszystkie kategorie",
"iex_all_users" => "wszyscy użytkownicy",
"iex_no_events_found" => "Nie znaleziono wydarzeń",
"iex_no_user_profiles" => "No user profiles found",
"iex_file_created" => "Plik utworzony",
"iex_write error" => "Błąd zapisu pliku eksportu<br>Sprawdź uprawnienia katalogu 'files/'",
"iex_invalid" => "nieprawidłowo",
"iex_in_use" => "już w użyciu",

//cleanup.php
"cup_cup_functions" => "Funkcje dodatkowe",
"cup_fill_fields" => "Wypełnij pojedynczą datę i zaznacz oczyść.",
"cup_found_confirm" => "Jeśli zostaną znalezione elementy do oczyszczenia, zostaniesz poproszony o potwierdzenie.",
"cup_evt" => "Wydarzenia do usunięcia",
"cup_usr" => "Konta użytkowników do usunięcia",
"cup_att" => "Załączniki do usunięcia",
"cup_rec" => "Listy odbiorców do usunięcia",
"cup_tns" => "Miniatury do usunięcia",
"cup_past_events" => "Przeszłe wydarzenia",
"cup_past_users" => "Nieaktywni użytkownicy",
"cup_att_dir" => "Katalog załączników",
"cup_rec_dir" => "Lista katalogów odbiorców",
"cup_tns_dir" => "Katalog miniatur",
"cup_usr_text" => "Konta użytkowników, którzy nie logowali się od",
"cup_evt_text" => "Wydarzenia, które miały miejsce przed",
"cup_att_text" => "Załączniki nieużywane w wydarzeniach od",
"cup_rec_text" => "Listy odbiorców nieużywanych w wydarzeniach od",
"cup_tns_text" => "Miniatury nieużywane w wydarzeniach od",
"cup_select_date" => "Wybierz datę",
"cup_blank_date1" => "Puste dane oznaczające: Nigdy się nie logował.",
"cup_blank_date2" => "Puste dane oznaczające: Nieużywane (osierocone).",
"cup_nothing_to_delete" => "Nic do oczyszczenia",
"cup_clean_up" => "Oczyść",
"cup_cancel" => "Anuluj",
"cup_delete" => "Usuń",
"cup_invalid date" => "Nieprawidłowa data",
"cup_events_deleted" => "Wydarzenia usunięte",
"cup_accounts_deleted" => "Konta usunięte",
"cup_files_deleted" => "Pliki usunięte",
"cup_important" => "WAŻNE:",
"cup_deleted_compact" => "Usunięte zdarzenia i konta użytkowników są oznaczone jako 'usunięte', ale nadal zajmują miejsce.<br> Na stronie Bazy danych te zdarzenia i konta można trwale usunąć<br>za pomocą funkcji Kompaktuj.",
"cup_deleted_files" => "Usunięte pliki są trwale usuwane z folderów i nie można ich odzyskać!",

//toolsaaf.php
"aff_sel_cals" => "Wybierz kalendarz(e)",
"aff_evt_copied" => "Wydarzenie skopiowane",

//styling.php
"sty_css_intro" => "Wartości określone na tej stronie powinny być zgodne ze standardami CSS",
"sty_preview_theme" => "Podgląd motywu",
"sty_preview_theme_title" => "Podgląd wyświetlanego motywu w kalendarzu",
"sty_stop_preview" => "Zatrzymaj podgląd",
"sty_stop_preview_title" => "Zatrzymaj podgląd wyświetlanego motywu w kalendarzu",
"sty_save_theme" => "Zapisz motyw",
"sty_save_theme_title" => "Zapisz wyświetlany motyw w bazie danych",
"sty_backup_theme" => "Kopia zapasowa motywu",
"sty_backup_theme_title" => "Kopia zapasowa motywu z bazy danych do pliku",
"sty_restore_theme" => "Przywróć motyw",
"sty_restore_theme_title" => "Przywróć motyw z pliku do wyświetl",
"sty_default_luxcal" => "domyślny motyw LuxCal",
"sty_close_window" => "Zamknij okno",
"sty_close_window_title" => "Zamknij to okno",
"sty_theme_title" => "Tytuł motywu",
"sty_general" => "Ogólne",
"sty_grid_views" => "Siatka / Widoki",
"sty_hover_boxes" => "Pola najechania kursorem",
"sty_bgtx_colors" => "Kolory tła/tekstu",
"sty_bord_colors" => "Kolory obramowania",
"sty_fontfam_sizes" => "Rodzina/rozmiary czcionek",
"sty_font_sizes" => "Rozmiary czcionek",
"sty_miscel" => "Różne",
"sty_background" => "Tło",
"sty_text" => "Tekst",
"sty_color" => "Kolor",
"sty_example" => "Przykład",
"sty_theme_previewed" => "Tryb podglądu — teraz możesz poruszać się po kalendarzu. Wybierz opcję Zatrzymaj podgląd po zakończeniu.",
"sty_theme_saved" => "Motyw zapisany w bazie danych",
"sty_theme_backedup" => "Motyw utworzony z kopii zapasowej bazy danych do pliku:",
"sty_theme_restored1" => "Motyw przywrócony z pliku:",
"sty_theme_restored2" => "Naciśnij Zapisz motyw, aby zapisać motyw w bazie danych",
"sty_unsaved_changes" => "OSTRZEŻENIE – Niezapisane zmiany!\\nJeśli zamkniesz okno, zmiany zostaną utracone.", //nie usuwaj '\\n'
"sty_number_of_errors" => "Liczba błędów na liście",
"sty_bgnd_highlighted" => "tło wyróżnione",
"sty_XXXX" => "kalendarz ogólny",
"sty_TBAR" => "górny pasek kalendarza",
"sty_BHAR" => "paski, nagłówki i wiersze",
"sty_BUTS" => "przyciski",
"sty_DROP" => "menu rozwijane",
"sty_XWIN" => "okna pop-up",
"sty_INBX" => "wstaw pola",
"sty_OVBX" => "nakładane pola",
"sty_BUTH" => "przyciski - po najechaniu kursorem",
"sty_FFLD" => "pola formularza",
"sty_CONF" => "komunikat potwierdzający",
"sty_WARN" => "komunikat ostrzegawczy",
"sty_ERRO" => "komunikat o błędzie",
"sty_HLIT" => "podświetlenie tekstu",
"sty_FXXX" => "podstawowa rodzina czcionek",
"sty_SXXX" => "podstawowy rozmiar czcionki",
"sty_PGTL" => "tytuły stron",
"sty_THDL" => "nagłówki tabeli L",
"sty_THDM" => "nagłówki tabeli M",
"sty_DTHD" => "nagłówki dat",
"sty_SNHD" => "nagłówki sekcji",
"sty_PWIN" => "okna pop-up",
"sty_SMAL" => "mały tekst",
"sty_GCTH" => "komórka dnia - najechanie kursorem",
"sty_GTFD" => "nagłówek komórki 1. dzień miesiąca",
"sty_GWTC" => "kolumna tygodnia / godziny",
"sty_GWD1" => "dzień tygodnia miesiąc 1",
"sty_GWD2" => "dzień tygodnia miesiąc 2",
"sty_GWE1" => "weekend miesiąc 1",
"sty_GWE2" => "weekend miesiąc 2",
"sty_GOUT" => "poza miesiącem",
"sty_GTOD" => "komórka dnia dzisiaj",
"sty_GSEL" => "komórka dnia wybrany dzień",
"sty_LINK" => "URL i e-mail linki",
"sty_CHBX" => "pole wyboru „todo”",
"sty_EVTI" => "tytuł wydarzenia w widokach",
"sty_HNOR" => "normalne wydarzenie",
"sty_HPRI" => "prywatne wydarzenie",
"sty_HREP" => "powtarzające się wydarzenie",
"sty_POPU" => "okno podręczne z najechaniem kursorem",
"sty_TbSw" => "cień górnego paska (0:nie 1:tak)",
"sty_CtOf" => "przesunięcie zawartości",

//lcalcron.php
"cro_sum_header" => "STRESZCZENIE ZADANIA CRON",
"cro_sum_trailer" => "KONIEC PODSUMOWANIA",
"cro_sum_title_eve" => "WYDARZENIA WYGASŁY",
"cro_nr_evts_deleted" => "Liczba usuniętych wydarzeń",
"cro_sum_title_not" => "PRZYPOMNIENIA",
"cro_no_reminders_due" => "Brak wiadomości z przypomnieniem",
"cro_due_in" => "W równym",
"cro_due_today" => "Należy dzisiaj",
"cro_days" => "dzień/dni",
"cro_date_time" => "Data / godzina",
"cro_title" => "Tytuł",
"cro_venue" => "Miejsce",
"cro_description" => "Opis",
"cro_category" => "Kategoria",
"cro_status" => "Status",
"cro_none_active" => "Brak aktywnych przypomnień lub okresowych usług",
"cro_sum_title_use" => "WYGASŁE KONTA UŻYTKOWNIKÓW",
"cro_nr_accounts_deleted" => "Liczba usuniętych kont",
"cro_no_accounts_deleted" => "Brak usuniętych kont",
"cro_sum_title_ice" => "WYEKSPORTOWANE WYDARZENIA",
"cro_nr_events_exported" => "Liczba wydarzeń wyeksportowanych do pliku w formacie iCalendar",

//messaging.php
"mes_no_msg_no_recip" => "Nie wysłano, nie znaleziono odbiorców",

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
"<h3>Instrukcje edycji - Information Text</h3>
<p>Po włączeniu na stronie Ustawienia, wiadomości informacyjne w obszarze tekstowym
po lewej stronie będą wyświetlane w widokach kalendarza w panelu bocznym tuż obok
strony kalendarza. Wiadomości mogą zawierać znaczniki HTML i style inline.
Przykłady różnych możliwości wiadomości informacyjnych można znaleźć w pliku
'sidepanel/samples/info.txt'.</p>
<p>Wiadomości informacyjne mogą być wyświetlane od daty początkowej do daty końcowej.
Każda wiadomość informacyjna musi być poprzedzona wierszem z określonym okresem wyświetlania
ujętym w znaki ~. Tekst przed pierwszym wierszem zaczynający się od znaku ~
może być używany do osobistych notatek i nie będzie wyświetlany w
obszarze informacyjnym panelu bocznego.</p><br>
<p>Format daty początkowej i końcowej: ~m1.d1-m2.d2~, gdzie m1 i d1 to miesiąc i 
dzień początkowy, a m2 i d2 to miesiąc i dzień końcowy. Jeśli d1 zostanie pominięte, 
przyjmuje się pierwszy dzień
m1. Jeśli d2 zostanie pominięte, przyjmuje się ostatni dzień m2. Jeśli m2 i d2
zostaną pominięte, przyjmuje się ostatni dzień m1.</p>
<p>Przykłady:<br>
<b>~4~</b>: Cały miesiąc kwiecień<br>
<b>~2.10-2.14~</b>: 10-14 luty<br>
<b>~6-7~</b>: 1 czerwiec-31 lipiec<br>
<b>~12.15-12.25~</b>: 15-25 grudzień<br>
<b>~8.15-10.5~</b>: 15 sierpień-5 październik<br>
<b>~12.15~</b>: 15 grudzień-31 Grudzień</p><br>
<p>Sugestia: Zacznij od utworzenia kopii zapasowej (Tekst kopii zapasowej).</p>",

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
"<h3>Instrukcje zarządzania bazą danych</h3>
<p>Na tej stronie można wybrać następujące funkcje:</p>
<h6>Kompaktuj bazę danych</h6>
<p>Gdy użytkownik usunie zdarzenie, zostanie ono oznaczone jako „usunięte”, ale nie zostanie
usunięte z bazy danych. Funkcja Kompaktuj bazę danych trwale
usunie zdarzenia usunięte ponad 30 dni temu z bazy danych i zwolni miejsce
zajmowane przez te zdarzenia.</p>
<h6>Kopia zapasowa bazy danych</h6>
<p>Ta funkcja utworzy kopię zapasową pełnej bazy danych kalendarza (struktura tabel i zawartość) w formacie .sql. Kopia zapasowa zostanie zapisana w katalogu
<strong>files/</strong> z nazwą pliku:
<kbd>dump-cal-lcv-yyyymmdd-hhmmss.sql</kbd> (gdzie 'cal' = identyfikator kalendarza, lcv =
wersja kalendarza i 'yyyymmdd-hhmmss' = rok, miesiąc, dzień, godzina, minuty i
sekundy).</p>
<p>Plik kopii zapasowej może zostać użyty do ponownego utworzenia bazy danych kalendarza (struktura i
dane) za pomocą funkcji przywracania opisanej poniżej lub na przykład za pomocą narzędzia
<strong>phpMyAdmin</strong>, które jest udostępniane przez większość hostów internetowych.</p>
<h6>Przywróć bazę danych</h6>
<p>Ta funkcja przywróci bazę danych kalendarza z zawartością
przesłanego pliku kopii zapasowej (typ pliku .sql). Jeśli plik .sql jest większy niż 2 MB, może być konieczna modyfikacja zmiennych <b>upload_max_filesize</b> i <b>post_max_size</b> w pliku php.ini lub podzielenie pliku .sql na kilka mniejszych plików. Zobacz sekcję 3 pliku admin_guide.html, aby uzyskać szczegółowe wyjaśnienie.</p>
<p>Podczas przywracania bazy danych WSZYSTKIE AKTUALNIE OBECNE DANE ZOSTANĄ UTRACONE!</p>
<h6>Wydarzenia</h6>
<p>Ta funkcja usunie lub przywróci zdarzenia, które mają miejsce między
określonymi datami. Jeśli data pozostanie pusta, nie będzie limitu dat; więc jeśli obie
daty pozostaną puste, WSZYSTKIE ZDARZENIA ZOSTANĄ USUNIĘTE!</p><br>
<p>WAŻNE: Gdy baza danych zostanie skompaktowana (patrz powyżej), zdarzeń, które
zostaną trwale usunięte z bazy danych, nie można już odzyskać!</p>",

"xpl_import_csv" =>
"<h3>Instrukcje importu pliku CSV</h3>
<p>Ten formularz służy do importowania pliku tekstowego <strong>Comma Separated Values ​​(CSV)</strong> z danymi wydarzenia do kalendarza LuxCal.</p>
<p>Kolejność kolumn w pliku CSV musi być następująca: tytuł, miejsce, identyfikator kategorii (patrz poniżej), data, data zakończenia, godzina rozpoczęcia, godzina zakończenia i opis. Pierwszy wiersz pliku CSV, używany do opisów kolumn, jest ignorowany.</p>
<h6>Przykładowe pliki CSV</h6>
<p>Przykładowe pliki CSV można znaleźć w katalogu '!luxcal-toolbox/' pobranego pliku LuxCal.</p>
<h6>Separator pól</h6>
Separator pól może być dowolnym znakiem, na przykład przecinkiem, średnikiem itp.
Znak separatora pól musi być unikalny i nie może być częścią tekstu,
liczb ani dat w pola.
<h6>Format daty i godziny</h6>
<p>Wybrany format daty wydarzenia i format godziny wydarzenia po lewej stronie muszą odpowiadać
formatowi dat i godzin w przesłanym pliku CSV.</p>
<p>Jeśli nie podano godziny rozpoczęcia (puste pole), wydarzenie zostanie wyświetlone jako wydarzenie „bez godziny”
w kalendarzu. Jeśli godzina rozpoczęcia to 00:00 lub 12:00, wydarzenie zostanie wyświetlone jako wydarzenie
całodniowe” w kalendarzu.</p>
<h6>Tabela kategorii</h6>
<p>Kalendarz używa numerów identyfikacyjnych do określania kategorii. Identyfikatory kategorii w pliku CSV
powinny odpowiadać kategoriom używanym w kalendarzu lub być puste.</p>
<p>Jeśli w następnym kroku chcesz oznaczyć wydarzenia jako „urodziny”, <strong>Identyfikator kategorii
Urodziny</strong> musi zostać ustawiony na odpowiadający mu identyfikator na poniższej liście kategorii.</p>
<p class='hired'>Ostrzeżenie: Nie importuj więcej niż 100 wydarzeń na raz!</p>
<p>Dla kalendarza obecnie zdefiniowano następujące kategorie:</p>",

"xpl_import_user" =>
"<h3>Instrukcje importowania profilu użytkownika</h3>
<p>Ten formularz służy do importowania pliku tekstowego CSV (Comma Separated Values) zawierającego
dane profilu użytkownika do kalendarza LuxCal.</p>
<p>Aby zapewnić prawidłową obsługę znaków specjalnych, plik CSV musi być zakodowany w formacie UTF-8.</p>
<h6>Separator pól</h6>
<p>Separatorem pól może być dowolny znak, na przykład przecinek, średnik itp.
Znak separatora pól musi być unikalny
i nie może być częścią tekstu w polach.</p>
<h6>Domyślny identyfikator grupy użytkowników</h6>
<p>Jeśli w pliku CSV identyfikator grupy użytkowników został pozostawiony pusty, zostanie użyty określony domyślny
identyfikator grupy użytkowników.</p>
<h6>Domyślne hasło</h6>
<p>Jeśli w pliku CSV hasło użytkownika zostało pozostawione puste, zostanie użyty określony domyślny
hasło


<h6>Zastąp istniejących użytkowników</h6>
<p>Jeśli zaznaczono pole wyboru Zastąp istniejących użytkowników, wszyscy istniejący użytkownicy,
oprócz użytkownika publicznego i administratora, zostaną usunięci przed zaimportowaniem
profili użytkowników.</p>

<br>
<h6>Przykładowe pliki profilu użytkownika</h6>
<p>Przykładowe pliki CSV profilu użytkownika (.csv) można znaleźć w folderze '!luxcal-toolbox/'
instalacji LuxCal.</p>

<h6>Pola w pliku CSV</h6>
<p>Kolejność kolumn musi być taka, jak podano poniżej. Jeśli pierwszy wiersz pliku CSV
zawiera nagłówki kolumn, zostanie zignorowany.</p>

<ul>
<li>Identyfikator grupy użytkowników: powinien odpowiadać grupom użytkowników używanym w kalendarzu (patrz
tabela poniżej). Jeśli puste, użytkownik zostanie umieszczony w określonej domyślnej grupie użytkowników</li>
<li>Nazwa użytkownika: obowiązkowa</li>
<li>Adres e-mail: obowiązkowy</li>
<li>Numer telefonu komórkowego: opcjonalny</li>
<li>Identyfikator czatu Telegram: opcjonalny</li>
<li>Język interfejsu: opcjonalny. Np. angielski, duński. Jeśli puste, zostanie wybrany domyślny język
wybrany na stronie Ustawienia.</li>
<li>Hasło: opcjonalne. Jeśli puste, zostanie wybrane określone domyślne hasło.</li>
</ul>
<p>Puste pola należy oznaczyć dwoma cudzysłowami. Puste pola na końcu każdego
wiersza można pominąć.</p>
<p class='hired'>Ostrzeżenie: Nie importuj więcej niż 60 profili użytkowników na raz!</p>
<h6>Tabela identyfikatorów grup użytkowników</h6>
<p>Dla Twojego kalendarza obecnie zdefiniowano następujące grupy użytkowników:</p>",

"xpl_export_user" =>
"<h3>Instrukcje eksportu profilu użytkownika</h3>
<p>Ten formularz służy do wyodrębniania i eksportowania <strong>profili użytkowników</strong> z
kalendarza LuxCal.</p>
<p>Pliki zostaną utworzone w katalogu „files/” na serwerze z
określoną nazwą pliku i w formacie wartości rozdzielonych przecinkami (.csv).</p>
<h6>Nazwa pliku docelowego</h6>
Jeśli nie określono, domyślną nazwą pliku będzie
nazwa kalendarza z sufiksem '_users'. Rozszerzenie nazwy pliku
zostanie automatycznie ustawione na <b>.csv</b>.</p>
<h6>Grupa użytkowników</h6>
Zostaną
wyeksportowane tylko profile użytkowników wybranej grupy użytkowników. Jeśli wybrano 'wszystkie grupy', profile użytkowników w pliku docelowym
zostaną posortowane według grupy użytkowników</p>
<h6>Pole separator</h6>
<p>Separatorem pól może być dowolny znak, na przykład przecinek, średnik itp.
Znak separatora pól musi być unikalny
i nie może być częścią tekstu w polach.</p><br>
<p>Istniejące pliki w katalogu „files/” na serwerze o tej samej nazwie zostaną
nadpisane przez nowy plik.</p>
<p>Kolejność kolumn w pliku docelowym będzie następująca: identyfikator grupy, nazwa użytkownika,
adres e-mail, numer telefonu komórkowego, język interfejsu i hasło.<br>
<b>Uwaga:</b> Hasła w eksportowanych profilach użytkowników są zakodowane i nie można ich
odkodować.</p><br>
<p>Podczas <b>pobierania</b> eksportowanego pliku .csv bieżąca data i godzina
zostaną dodane do nazwy pobranego pliku.</p><br>
<h6>Przykładowe pliki profilu użytkownika</h6>
<p>Przykładowe pliki profilu użytkownika (rozszerzenie pliku .csv) można znaleźć w katalogu '!luxcal-toolbox/'
pobranego programu LuxCal.</p>",

"xpl_import_ical" =>
"<h3>Instrukcje importowania iCalendar</h3>
<p>Ten formularz służy do importowania pliku <strong>iCalendar</strong> ze zdarzeniami do
kalendarza LuxCal.</p>
<p>Zawartość pliku musi być zgodna ze [<u><a href='https://tools.ietf.org/html/rfc5545'
target='_blank'>standardem RFC5545</a></u>] Internet Engineering Task Force.</p>
<p>Importowane będą tylko zdarzenia; inne komponenty iCal, takie jak: To-Do, Jounal, Free /
Busy i Alarm, zostaną zignorowane.</p>
<p>Przykładowe pliki iCalendar można znaleźć w katalogu '!luxcal-toolbox/' pobranego
pliku LuxCal.</p>
<h6>Dostosowanie strefy czasowej</h6>
<p>Jeśli plik iCalendar zawiera zdarzenia w innej strefie czasowej, a daty/godziny
powinny być dostosowane do strefy czasowej kalendarza, a następnie sprawdź „Dostosowanie strefy czasowej”.</p>
<h6>Tabela kategorii</h6>
<p>Kalendarz używa numerów ID do określania kategorii. Identyfikatory kategorii w pliku
iCalendar powinny odpowiadać kategoriom używanym w kalendarzu lub być
puste.</p>
<p class='hired'>Ostrzeżenie: Nie importuj więcej niż 100 wydarzeń na raz!</p>
<p>Dla Twojego kalendarza obecnie zdefiniowano następujące kategorie:</p>",

"xpl_export_ical" =>
"<h3>Instrukcje eksportu iCalendar</h3>
<p>Ten formularz służy do wyodrębniania i eksportowania wydarzeń <strong>iCalendar</strong> z
kalendarza LuxCal.</p>
<p><b>Nazwa pliku docelowego</b> (bez rozszerzenia) jest opcjonalna. Utworzone pliki
będą przechowywane w katalogu \"files/\" na serwerze pod określoną nazwą pliku
lub w inny sposób pod nazwą kalendarza. Rozszerzeniem pliku będzie <b>.ics</b>.
Istniejące pliki w katalogu \"files/\" na serwerze o tej samej nazwie
zostaną nadpisane nowym plikiem.</p>
<p><b>Opis pliku iCal</b> (np. „Spotkania 2024”) jest opcjonalny. Jeśli
zostanie wprowadzony, zostanie dodany do nagłówka eksportowanego pliku iCal.</p>
<p><b>Filtry wydarzeń</b>: Wydarzenia do można wyodrębnić można filtrować według:</p>
<ul>
<li>właściciela zdarzenia</li>
<li>kategorii zdarzenia</li>
<li>daty rozpoczęcia zdarzenia</li>
<li>daty dodania/ostatniej modyfikacji zdarzenia</li>
</ul>
<p>Każdy filtr jest opcjonalny. Puste daty „występujące pomiędzy” domyślnie wynoszą odpowiednio -1 rok
i +1 rok. Pusta data „dodano/zmodyfikowano pomiędzy” oznacza: brak ograniczeń.</p>
<br>
<p>Zawartość pliku z wyodrębnionymi zdarzeniami będzie zgodna ze
[<u><a href='https://tools.ietf.org/html/rfc5545' target='_blank'>standardem RFC5545</a></u>]
Internet Engineering Task Force.</p>
<p>Podczas <b>pobierania</b> wyeksportowanego pliku iCal data i godzina zostaną
dodane do nazwy pobranego pliku plik.</p>
<h6>Przykładowe pliki iCal</h6>
<p>Przykładowe pliki iCalendar (rozszerzenie pliku .ics) można znaleźć w katalogu '!luxcal-toolbox/'
pobranego pliku LuxCal.</p>",

"xpl_clean_up" =>
"<h3>Instrukcje czyszczenia</h3>
<p>Na tej stronie można wyczyścić następujące elementy:</p>
<h6>Wydarzenia z przeszłości</h6>
<p>Wydarzenia w tym kalendarzu z datą końcową przed określoną datą zostaną
usunięte z kalendarza. Określona data musi być co najmniej miesiąc przed dzisiejszą datą.</p>
<h6>Nieaktywni użytkownicy</h6>
<p>Konta użytkowników, którzy nie logowali się do tego kalendarza od
określonej daty, zostaną usunięte z kalendarza. Określona data musi być
co najmniej miesiąc przed dzisiejszą datą.</p>
<h6>Folder załączników</h6>
<p>Pliki załączników, które nie są używane w wydarzeniach od określonej daty, zostaną
usunięte. Data musi być pusta lub musi być w przeszłości. W przypadku wielu kalendarzy pliki załączników zostaną
sprawdzone pod kątem wszystkich kalendarzy.</p>
<h6>Listy odbiorców folder</h6>
<p>Pliki listy odbiorców, które nie są używane w wydarzeniach od określonej daty,
zostaną usunięte. Data musi być pusta lub musi być w przeszłości. W przypadku wielu kalendarzy,
pliki listy odbiorców zostaną sprawdzone pod kątem wszystkich kalendarzy.</p>
<h6>Folder miniatur</h6>
<p>Pliki miniatur, które nie są używane w wydarzeniach od określonej daty i nie są
używane w pliku info.txt panelu bocznego,
zostaną usunięte. Data musi być pusta lub musi być w przeszłości. W przypadku wielu kalendarzy,
pliki miniatur zostaną sprawdzone pod kątem wszystkich kalendarzy.</p>"
);
?>
