<?php
/*
= LuxCal on-line user guide =

Oversat til dansk af Lars J. Helbo.
Additional Danish translations by FinnH - as is.
Additional Danish - John Schwartz last checked/edited 31-07-2020

This file is part of the LuxCal Web Calendar.
*/

?>
<div style="margin:0 20px">
<div class="floatR">
<img src="lang/ug-layout.png" alt="LuxCal page layout"><br>
<span class="hired">a</span>: titelbjælke&nbsp;&nbsp;<span class="hired">b</span>: navigationsbjælke&nbsp;&nbsp;<span class="hired">c</span>: dag
</div>
<br>
<h3>Indholdsfortegnelse</h3>
<ol>
<li><p><a href="#ov">Oversigt</a></p></li>
<li><p><a href="#li">Logge ind</a></p></li>
<li><p><a href="#ae">Tilføje begivenhed</a></p></li>
<li><p><a href="#ee">Editere / slette begivenhed</a></p></li>
<li><p><a href="#co">Kalender valgmuligheder</a></p></li>
<li><p><a href="#cv">Kalendervisninger</a></p></li>
<li><p><a href="#ts">Tekstsøgning</a></p></li>
<li><p><a href="#lo">Logge ud</a></p></li>
<li><p><a href="#ca">Kalender administration</a></p></li>
<li><p><a href="#al">Om LuxCal</a></p></li>
</ol>
</div>
<div class="clear">
<br>
<ol>
<li id="ov"><h3>Oversigt</h3>
<p>LuxCal kalenderen kører på en webserver og kan ses og administreres via en webbrowser.</p>
<p>Titelbjælken viser kalenderens titel, datoen og navnet på den aktuelle bruger.
Lige under titelbjælken findes navigationsbjælken med flere drop-down menuer og links til at navigere med, til at logge ind og ud, tilføje en begivenhed og vælge administratorfunktioner. Hvilke menuer og links, der vises, afhænger af brugerens rettigheder.
Under navigationsbjælken vises de forskellige kalendervisninger</p>
<br></li>
<li id="li"><h3>Logge ind</h3>
<p>Hvis kalender-administratoren har givet offentlig adgang til kalenderen, kan kalenderen ses uden at logge ind.</p>
<p>For at bruge kalenderen ud over hvad der er konfigureret som offentligt tilgængeligt, skal du logge ind. Klik på knappen Log ind i højre side af navigationsbjælken for at komme til log ind-skærmen. Indtast dit brugernavn eller din email-adresse (en af de to) og det password, som du fik fra administratoren og klik så på Log ind. Hvis du vælger "Husk mig" før du klikker Log ind, vil du automatisk blive logget ind næste gang du åbner kalenderen. Hvis du har glemt dit password, klik på Log ind og derefter på linket for at få tilsendt et nyt password.</p>
<p>Du kan ændre din email-adresse og dit password ved at indtaste dit brugernavn/email og aktuelle password samt en ny email-adresse og et nyt password.</p>
<br></li>
<li id="ae"><h3>Tilføj begivenhed</h3>
<p>Begivenheder kan tilføjes på flere forskellige måder:</p>
<ul style="margin:0 20px">
<li><p>ved at klikke på knappen Tilføj begivenhed ("+") i navigationsbjælken</p></li>
<li><p>ved at klikke øverst i feltet for en dag på en års- eller månedskalender</p></li>
<li><p>ved at klikke og trække hen over en del af en dag i en uge- eller dagskalender for at markere et tidsrum</p></li>
</ul>
<p>Hver metode vil åbne vinduet Begivenhed med en formular, hvor informationer om begivenheden indtastes. Nogle felter i formularen er allerede udfyldte, alt efter, hvilken af ovenstående metoder, der blev brugt.</p>
<h6>Titel, Sted, Kategori, Beskrivelse og Privat felter</h6>
<p>I øverste del af formularen indtastes titel, sted, kategori og en beskrivelse, og muligheden Privat kan vælges (hvis kalenderen er konfigureret til private begivenheder). Titlen bør være kort og detaljerne placeres under beskrivelse. Felterne sted og kategori er valgfri. Hvis der vælges en kategori, får begivenheden en farvekode i alle kalendervisninger alt efter kategorifarven. Stedet og beskrivelsen vises, når musen føres hen over begivenheden kalenderen. En privat begivenhed er kun synlig for dig selv og ikke for andre.</p>
<p>Internet-adresser tilføjet i begivenhedsbeskrivelsen, i formatet [ url | navn ] (for eksempel [www.mysite.com | mit navn]), omdannes automatisk til links, som kan vælges i månedsvisning, kommende begivenheder og påmindelses-emails.</p>
<h6>Dato, Tid og Gentagelse felter</h6>
<p>I anden halvdel af formularen kan datoer og tidspunkter angives. Hvis Hele dagen vælges, vises ingen tidspunkter i kalendervisningerne eller begivenhedsdetaljer. Slutdato er valgfri og kan bruges til begivenheder, der går over flere dage. Datoer og tider kan indtastes manuelt eller via dato- og tidsvalgsknapperne. Derudover kan der defineres gentagelse af begivenheder. Klik på knappen Ændre for at åbne den særlige dialogboks til dette. I så fald gentages begivenheden som angivet fra startdatoen til slutdatoen. Hvis der ikke anføres nogen slutdato, gentages begivenheden evigt, hvilket er særlig praktisk til fødselsdage.</p>
<h6>Send email felter</h6>
<p>I den nederste del af formularen med alarm-funktionen, kan du vælge at sende en email-påmindelse til en eller flere email-adresser, straks, hvis "nu" boksen vælges, og/eller et antal dage før selve datoen for begivenheden. Derudover sendes en email på selve dagen for begivenheden. For begivenheder der gentages, sendes en email det valgte antal dage før hver gang begivenheden gentages og på selve datoen for hver gentagelse.</p>
<p>Email listen kan indeholde email adresser og/eller navnet (uden fil extension) på en forud defineret email liste fil, adskilt med semikolonner. Den forud definerede email liste fil skal være en tekstfil med extension ".txt", som skal ligge i folderen "reciplists/" på serveren. Filen skal indeholde en email adresse pr. linje. Filnavnet må ikke indeholde tegnet "@".</p>
<p>Når alt er udfyldt, klik på Tilføj og luk for at oprette begivenheden og returnere til kalenderen, eller klik på Tilføj for at oprette begivenheden og beholde vinduet åbent, så oplysningerne kan tilrettes og/eller bruges til at oprette yderligere begivenheder.</p>
<br></li>
<li id="ee"><h3>Editere / slette begivenhed</h3>
<p>I hver kalendervisning kan du klikke på en begivenhed for at se, editere eller slette den. Dermed åbnes vinduet Editer begivenhed, der ser ud som vinduet Tilføj begivenhed beskrevet herover, bortset fra titlen og knapperne nederst i vinduet.</p>
<p>Ved ændring af en begivenhed, giver knapperne mulighed for at gemme ændringer og lukke vinduet, gemme ændringer og beholde vinduet åbent for at foretage yderligere ændringer, gemme ændringer som en ny begivenhed (fx for at oprette på en ny dato), slette begivenheden eller lukke vinduet uden at gemme ændringer foretaget efter sidste Gem.</p>
<p>Alt efter dine rettigheder kan du se begivenheder, se/editere/slette dine egne begivenheder eller se/editere/slette alle begivenheder, herunder andre brugeres begivenheder.</p>
<p>For en beskrivelse af felterne, se under Tilføj begivenhed herover.</p> 
<p>Sletning af en begivenhed, der gentages sletter alle forekomster af begivenheden, ikke bare den valgte dato.</p>
<br></li>
<li id="co"><h3>Kalender Valgmuligheder</h3>
<p>Klik på knappen Valg i venstre side af navigationsbjælken for at vise kalenderens valgmuligheder. Her kan du vælge følgende ved afkrydsning:</p>
<ul style="margin:0 20px">
<li><p>Kalender visning (År, Måned, Uge, Dag, Kommende, Ændringer eller Matrix).</p></li>
<li><p>Udvælgelse baseret på begivenhedsejer. Begivenheder oprettet af en enkelt, flere eller alle brugere kan udvælges.</p></li>
<li><p>Udvælgelse baseret på begivenhedskategorier. Begivenheder i en enkelt, flere eller alle kategorier kan udvælges.</p></li>
<li><p>Brugerinterface sprog.</p></li>
</ul>
<p>Efter afkrydsning af de ønskede valg i valgmenuerne klikkes igen på Valg (nu Udfør) knappen i navigationsbjælken for at aktivere dine valg.</p> 
<p>Bemærk: Visning af valgmenuer og sprogmenu kan være aktiveret eller deaktiveret af kalenderens administrator.</p>
<br></li>
<li id="cv"><h3>Kalendervisninger</h3>
<p>I alle visninger vil en boks med flere detaljer om en begivenhed poppe op, når musen føres hen over den. For private begivenheder vil baggrundsfarven i pop-up boksen være lys grøn. For gentagne eller flerdages begivenheder vil rammen om pop-up boksen være rød. I visningen Kommende vil URL'er i beskrivelsesfeltet automatisk blive omdannet til links til den tilhørende webside.</p>
<p>I alle visninger vil dags dato have en blå ramme, og hvis en ny dato vælges med datovælgeren i navigationsbjælken, vil denne dato have en rød ramme i måneds- og årsvisning.</p>
<p>Begivenheder i en kategori, hvor administrator har aktiveret Tjekboks, vil vise en tjekboks foran begivenhedstitlen. Den kan bruges til fx at mærke en begivenhed som "afsluttet". Hvis du har de nødvendige rettigheder kan du klikke i tjekboksen for at sætte eller fjerne tjekmærket.</p>
<p>Hvis du har tilstrækkelige rettigheder:</p>
<ul style="margin:0 20px">
<li><p>I alle visninger gælder, at når du klikker på en begivenhed, åbnes vinduet for editering af denne begivenhed, hvor du så kan se, editere og slette begivenheden.</p></li>
<li><p>I visningerne Måned og År kan en ny begivenhed tilføjes for en bestemt dato ved at klikke øverst i feltet for dagen (linien hvor datoen vises).</p></li>
<li><p>I visningerne Uge og Dag, kan et tilføj-vindue åbnes ved at trække musen hen over en del af dagen; felterne dato og tid udfyldes automatisk med den valgte periode.</p></li>
</ul>
<p>I visningen Ændringer kan en startdato specificeres. En liste med alle begivenheder tilføjet, editeret eller slettet fra og med den angivne startdato vises.</p>
<p>For at flytte en begivenhed til en ny dato eller tid, åbnes editerings-vinduet ved at klikke på begivenheden og derefter ændre dato og tid. Begivenheder kan ikke trækkes til nye dage eller tider.</p>
<br></li>
<li id="ts"><h3>Tekstsøgning</h3>
<p>Klik på knappen med trekanten i højre side af navigationsbjælken for at åbne Tekstsøgning siden. Siden indeholder detaljerede instruktioner.</p>
<br></li>
<li id="lo"><h3>Logge ud</h3>
<p>For at logge ud, klik på Log ud i højre side af navigationsbjælken. Hvis du lukker kalenderen uden at logge ud, kan det ske, at du ikke bliver bedt om at logge ind næste gang kalenderen åbnes.</p>
<br></li>
<li id="ca"><h3>Kalenderadministration</h3>
<p>- de følgende funktioner kræver administratorrettigheder -</p>
<p>Når en bruger logger ind med administratorrettigheder, vises en drop-down menu kaldet Administration i højre side af navigationsbjælken. Med denne menu er følgende funktioner tilgængelige:</p>
<br>
<h6>a. Indstillinger</h6>
<p>Siden viser de aktuelle kalenderindstillinger, som derefter kan ændres. Alle indstillinger forklares på siden i pop-up vinduer, som vises når musemarkøren holdes over titlen på hver indstilling.</p>
<br>
<h6>b. Kategorier</h6>
<p>Tilføjelse af kategorier med forskellig farve vil - selv om det ikke er nødvendigt - forbedre oversigten over kalenderen. Mulige kategorier er fx 'ferie', 'aftaler', 'fødselsdage', 'vigtigt', etc.</p>
<p>Ved installation er der kun defineret en kategori, kaldet 'ingen'. Når du vælger Kategorier fra administrationsmenuen, kommer du til en side med en liste med alle kategorier og mulighed for at tilføje nye kategorier eller editere/slette eksisterende kategorier.</p>
<p>Når der tilføjes / editeres begivenheder, kan de definerede kategorier vælges i en drop-down liste. Den rækkefølge, hvori kategorier vises i listen bestemmes af sekvens-feltet.</p>
<p>En kategori kan have gentagelse defineret. Begivenheder i denne kategori vil automatisk få sat gentagelse som angivet her.</p>
<p>Hvis "Begivenheder kræver godkendelse" markeres, vil der blive tilføjet en tjekboks til godkendelse i toppen af editeringsvinduet for begivenheder, der tilknyttes denne kategori. En begivenhed, der ikke er markeret som godkendt, vil blive vist med en rød kantlinje i kalendervisningerne.</p>
<p>Markeringen 'Offentlig' kan fjernes for at skjule begivenheder i denne kategori, så de ikke er synlige i offentlig visning, men kun kan ses af brugere der er logget ind. De vil også blive udeladt fra RSS feeds.</p>
<p>Der kan defineres en tjekboks med valgfri titel og tjekmærke for kategorien, hvilket medfører at der i kalendervisningerne (undtagen årsvisning) tilføjes en tjekboks foran titlen for alle begivenheder i denne kategori. Brugere kan (med de nødvendige rettigheder) klikke her for at sætte eller fjerne markeringen, som fx kan være 'afsluttet'.</p>
<p>Felterne tekstfarve og baggrund definerer de farver, som begivenheder i denne kategori vises med i kalenderen.</p>
<p>Når en kategori slettes, vil den stadig være tilgængelig for de begivenheder der tilhører denne kategori.</p>
<br>
<h6>c. Brugere</h6>
<p>På brugersiden kan administratoren tilføje og editere brugere samt deres kalenderrettigheder. To hovedområder kan editeres: brugerens navn/email/password og brugerens rettigheder. Mulige rettigheder er: Se, Opret + editer egne, Opret + editer alle og Admin. Det er vigtigt at bruge en gyldig email-adresse, så brugerne kan modtage email-påmindelser om kommende begivenheder.</p>
<p>I Indstillingerne kan administrator aktivere Bruger-selvregistrering og definere hvilke rettigheder, der skal tildeles selvregistrerede brugere. Hvis selvregistrering er aktiv, kan brugere registrere sig direkte på kalendersiden.</p> 
<p>Medmindre kalender-administratoren har givet Se-adgang til offentlige brugere, skal brugerne logge ind med deres brugernavn eller email og password. Alt efter typen af bruger, kan brugeren få forskellige adgangsrettigheder.</p>
<p>For hver bruger kan der angives et standardsprog. Hvis der ikke angives et sprog, vil kalenderens standardsprog fra Indstillinger blive anvendt.</p>
<br>
<h6>d. Database</h6>
<p>Databasesiden giver kalenderens administrator mulighed for at udføre følgende funktioner:</p>
<ul>
<li>Tjek og reparer database, for at finde og løse inkonsistens i database tabellerne.</li>
<li>Komprimer database, for at frigøre ubrugt plads og undgå "overhead". Denne funktion vil fjerne begivenheder permanent hvis det er mere end 30 dage siden de blev slettet.</li>
<li>Backup af database, for at oprette en backupfil, som kan bruges til at gendanne databasetabellernes struktur og indhold.</li>
</ul>
<p>Den første funktion, Tjek og reparer database, behøver kun at blive udført, hvis kalendervisningerne ikke virker korrekt. Den anden funktion, Komprimer database, kan fx udføres en gang årligt for at rydde op i databasen, og den tredje funktion, Backup af database, bør udføres oftere, afhængigt af hvor mange opdateringer der foretages i kalenderen.</p>
<br>
<h6>e. CSV fil-import</h6>
<p>Denne funktion kan bruges til at importere begivenhedsdata til LuxCal kalenderen fra andre kalendere (f.eks. MS Outlook). Nærmere vejledning findes på CSV import-siden.</p>
<br>
<h6>f. iCal fil-import</h6>
<p>Denne funktion kan bruges til at importere begivenheder fra iCal-filer (fil extension .ics) til LuxCal-kalenderen. Mere vejledning findes på iCal-importsiden. Kun begivenheder, som er kompatible med LuxCal-kalenderen importeres. Andre komponenter, så som: To-Do, Journal, Fri / optaget, Tidszone og Alarm, ignoreres.</p>
<br>
<h6>g. iCal fil-eksport</h6>
<p>Denne funktion kan bruges til at eksportere LuxCal-begivenheder til iCal-filer (fil extension .ics). Mere vejledning findes på iCal-eksportsiden.</p>
<br>
</li>
<li id="al"><h3>Om LuxCal</h3>
<p>Udviklet af: <b>Roel Buining</b>&nbsp;&nbsp;&nbsp;&nbsp;Website og forum: <b><a href="https://www.luxsoft.eu/" target="_blank">www.luxsoft.eu/</a></b></p>
<p>LuxCal er freeware og må videregives og/eller modificeres under betingelserne i <b><a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">GNU General Public License</a></b>.</p>
<br></li>
</ol>
</div>