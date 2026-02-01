<?php
/*
= LuxCal on-line user guide =

This user guide has been produced by LuxSoft - please send your comments to rb@luxsoft.eu.
Translation to swedish by Christer "Scunder" Nordahl.

This file is part of the LuxCal Web Calendar.
*/

?>
<div style="margin:0 20px">
<div class="floatR">
<img src="lang/ug-layout.png" alt="LuxCal sidlayout"><br>
<span class="hired">a</span>: namnlist&nbsp;&nbsp;<span class="hired">b</span>: verktygsfält&nbsp;&nbsp;<span class="hired">c</span>: dag
</div>
<br>
<h3>Innehållsförteckning</h3>
<ol>
<li><p><a href="#ov">Översikt</a></p></li>
<li><p><a href="#li">Logga in</a></p></li>
<li><p><a href="#co">Kalenderalternativ</a></p></li>
<li><p><a href="#cv">Kalendervisningar</a></p></li>
<li><p><a href="#ts">Textsökning</a></p></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li><p><a href="#ae">Skapa/Redigera/Radera Händelse</a></p></li>
<?php } ?>
<li><p><a href="#lo">Logga ut</a></p></li>
<?php if ($usr['privs'] > 3) { //if manager/administrator ?>
<li><p><a href="#ca">Administrera kalender</a></p></li>
<?php } ?>
<li><p><a href="#al">Om LuxCal</a></p></li>
</ol>
</div>
<div class="clear">
<br>
<ol>

<li id="ov"><h3>Översikt</h3>
<p>LuxCal-kalendern körs på en webbserver och kan visas och administreras via en webbläsare.</p>
<p>I namnlisten visas kalenderns namn, dagens datum och användarnamnet på den aktuella användaren.
Strax under namnlisten finns verktygsfältet som innehåller menyer och länkar för att välja typ av
visning, logga in/ut, skapa ny händelse, etc. Vilka menyer och länkar som visas beror på
användarens rättigheter. T.ex. visas administrations-menyn endast om en administratör är inloggad.
Resten av fönstret används för att visa kalendern på olika sätt (årsvis, veckovis, etc.)</p>
<br></li>

<li id="li"><h3>Logga in</h3>
<p>Om kalenderns administratör har givit gästanvändare läsrättigheter, kan kalendern visas utan att användaren behöver logga in.</p>
<p>Klicka på 'Logga in' till höger i verktygsfältet för att komma till inloggningsskärmen. Ange antingen användarnamn eller epostadress och även ditt lösenord, och klicka sedan på 'Logga in'. Välj 'Kom ihåg mig' först om du vill bli inloggad automatiskt nästa gång du besöker kalendern. För att återställa ditt lösenord väljer du 'Skicka nytt lösenord' för att få ett nytt via epost</p>
<p>Du kan ändra dina personliga inloggningsuppgifter genom att välja 'Ändra mina uppgifter' på inloggningssidan.</p>
<p>Om du inte är registrerad användare och administratören har aktiverat alternativet självregistrering så kan du välja 'Registrera dig' på inloggningssidan, annars kan administratören skapa ett konto för dig.</p>
<br></li>

<li id="co"><h3>Kalenderalternativ</h3>
<p>Genom att klicka på knappen 'Alternativ' i verktygsfältet öppnas kalenderns inställningsmenyer. I dessa menyer kan man välja:</p>
<ul style="margin:0 20px">
<li><p>Kalendervisning (år, månad, vecka, dag, kommande, ändringar eller matrix).</p></li>
<li><p>Ett händelsefilter baserat på händelsers ägare. Man skapar ett urval av händelser genom att välja en enskild (eller ett flertal) ägare.</p></li>
<li><p>Ett händelsefilter baserat på händelsers kategori. Man skapar ett urval av händelser genom att välja en enskild (eller ett flertal) kategorier.</p></li>
<li><p>Språk för användargränssnittet.</p></li>
</ul>
<p>När valen är gjorda ska man åter klicka på knappen 'Klar' för att aktivera de nya inställningarna.</p> 
<p>Observera: Menyerna för händelsefilter och språkval visas inte om administratören har valt att dölja dem.</p>
<br></li>

<li id="cv"><h3>Kalendervisningar</h3>
<p>I alla visningar dyker en inforuta med händelsedetaljer upp när muspekaren vilar över händelsen/händelsetiteln. För privata händelser är inforutans bakgrundsfärg ljusgrön, och för repetitioner eller flerdygnshändelser är ramen röd. I Kommande-visning fungerar internetadresser (URL:er) i händelsers beskrivningsfält som hyperlänkar.</p>
<p>I alla visningar har dagens datum en blå ram, och om en ny datum har valts med datumväljaren i verktygsfältet kommer detta datum att ha en röd ram i visningar för månad och år.</p>
<p>Händelser i en kategori med "kryssruta" aktiverad av LuxCal-administratören visas med en kryssruta framför händelsetiteln. Denna kan användas för att markera händelser som t.ex. "avklarade". Användare med nödvändiga rättigheter kan markera/avmarkera denna kryssruta.</p>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<p>För användare med tillräckliga åtkomsträttigheter:</p>
<ul style="margin:0 20px">
<li><p>I alla visningar: En klickning på en händelse öppnar fönstret 'Redigera Händelse' där händelsen kan läsas, redigeras eller raderas.</p></li>
<li><p>I visningarna År/Månad: En ny händelse kan infogas ett visst datum genom att klicka på datumcellens övre del (bredvid datumet).</p></li>
<li><p>I visningarna Vecka/Dag: Genom att dra och markera ett visst tidsområde öppnas 'Ny Händelse'-fönstret där datum- och tidsfält automatiskt fyllts i enligt det markerade området.</p></li>
</ul>
<p>För att ändra en händelses datum eller tid måste händelsen redigeras. Händelser kan inte flyttas med musen.</p>
<?php } ?>
<br></li>

<li id="ts"><h3>Textsökning</h3>
<p>Klicka på 'Sök' (triangel) på höger sida i verktygsfältet för att öppna textsökningssidan. Sidan innehåller detaljerade instruktioner angående användning av sökfunktionen.</p>
<br></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>

<li id="ae"><h3>Skapa/Redigera/Radera Händelse</h3>
<p>Att skapa, redigera och radera händelser sker i Händelsefönstret som kan öppnas på ett flertal sätt beskrivet nedan.</p>
<br><h6>a. Skapa Händelse</h6>
<p>För att skapa en händelse kan Händelsefönstret öppnas på följande sätt:</p>
<ul style="margin:0 20px">
<li><p>genom att klicka överst i en datumcell (bredvid datumet) i visningarna År/Månad.</p></li>
<li><p>genom att klicka på 'Skapa händelse' (+) i verktygsfältet.</p></li>
<li><p>genom att dragmarkera en del av dagen i visningarna Vecka/Dag.</p></li>
</ul>
<p>Samtliga alternativ öppnar fönstret 'Skapa händelse' som innehåller ett formulär för att mata in händelsedata. Vissa fält är redan ifyllda, beroende på hur man öppnat fönstret.</p>
<h6>Titel, Plats, Kategori, Beskrivning och Privata händelsefält</h6>
<p>Att ange plats, kategori och beskrivning är valfritt. Val av kategori färgkodar händelsen i alla visningar enligt kategorifärgerna. Platsen och beskrivningen visas i inforutan när man pekar på händelsen i de olika visningarna. Internetadresser (URL:er) i händelsers beskrivningsfält fungerar som hyperlänkar.</p>
<p>En privat händelse visas endast för ägaren.</p>
<h6>Fält för Datum, Tider och Repetitioner</h6>
<p>Slutdatum kan användas för flerdygnshändelser. Datum och Tid kan antingen skrivas in eller väljas med knapparna för datum- och tidval. Klicka på 'Ändra' för att ställa/redigera repetition för en händelse. Händelsen repeteras från 'Start' till 'tills'. Om inget anges i fältet 'tills' kommer händelsen att repeteras tills vidare, vilket är användbart för t.ex.födelsedagar.</p>
<h6>Fält för Meddelanden</h6>
<p>Funktionen för meddelanden kan skicka påminnelser via epost till en eller flera adresser. Om rutan 'nu' markeras skickas meddelande direkt när händelsen sparas. Om användaren specificerar ett antal 'dagar före' skickas meddelande x dagar före händelsen OCH på dagen för händelsen (0 = endast på dagen för händelsen). Om rutan 'dagar före' lämnas tom skickas inget meddelande. För repeterande händelser behandlas varje enskild händelse på samma sätt.</p>
<p>Fältet för epostadresser kan innehålla flera adresser eller epost-listor, separerade med semikolon. En epostlista ska vara sparad som en textfil (.txt) i mappen 'reciplists/' och innehålla en epostadress per rad. Filnamnet får inte innehålla tecknet "@". I fältet för epostadresser ska epostlistans filnamn anges utan filändelse.</p>
<p>Avsluta med att spara händelsen.</p>
<br>
<h6>b. Redigera/Radera Händelse</h6>
<p>I alla kalendervisningar kan man klicka på en händelse för att öppna ett fönster med händelsens detaljer. En användare med tillräckliga rättigheter kan redigera, kopiera eller radera händelsen.</p>
<p>Beroende på dina rättigheter kan du visa händelser, visa/redigera/radera dina egna händelser, eller visa/redigera/radera kalenderns alla händelser.</p>
<p>För en beskrivning av de olika fälten, se 'Skapa Händelse' ovan.</p>
<p>Med knapparna längst ner i fönstret 'Redigera Händelse' kan man spara en redigerad händelse, spara en redigerad händelse som en ny händelse (för att t.ex. kopiera händelsen till ett annat datum) eller radera händelsen.</p>
<p>Viktigt! Radering av en repetativ händelse raderar <strong>samtliga</strong> återkommande händelsedatum, och inte endast ett specifikt datum.</p>
<br></li>
<?php } ?>

<li id="lo"><h3>Logga ut</h3>
<p>Klicka på 'Logga ut' i verktygsfältet för att logga ut.</p>
<br></li>
<?php if ($usr['privs'] > 3) { //administrator/manager only ?>

<li id="ca"><h3>Administrera kalender</h3>
<p>- följande funktioner kräver administratörs rättigheter -</p>
<p>När en användare med administratörs rättigheter loggar in visas rullgardinsmenyn 'Administration' till höger på verktygsfältet. Via denna meny kan följande administratörssidor väljas:</p>
<br>
<ol type='a'>
<?php if ($usr['privs'] == 9) { //administrator only ?>
<li><h6>Inställningar</h6>
<p>Denna sida visar de aktuella kalenderinställningar som är modifierbara. Alla inställningar förklaras på sidan 'Inställningar' genom att man pekar på varje inställningsrubrik.</p>
<br></li>
<?php } ?>
<li><h6>Kategorier</h6>
<p>Att skapa händelsekategorier med olika färger (helt valfritt) förtydligar kalenderns visningar. Olika kategorier kan vara t.ex. 'ledighet', 'möte', 'födelsedag', 'viktigt', etc.</p>
<p>Sidan 'Kategorier' visar en lista av alla aktuella kategorier. Användaren kan här skapa, redigera och radera kategorier. Vid nyinstallation finns bara en kategori: 'no cat' (ingen kategori).</p>
<p>Vid skapande/redigering av händelser visas alla kategorier i en rullgardinsmeny. Kategoriernas inbördes ordning avgörs av fältet 'Ordningsföljd'.</p>
<p>Vid skapande/redigering av kategorier kan ett värde för 'repetition' anges. Händelser inom denna kategori kommer då automatiskt att repeteras enligt det angivna värden. Markeringsrutan för 'Offentlig' kan användas för att förhindra att händelser i denna kategori visas för Gäst-användare (oinloggade) och exkludera dem från RSS-flöden.</p>
<p>En eller två markeringar kan aktiveras och visas framför alla händelsers titel i denna kategori. Användaren kan använda dessa markeringar för att flagga för olika funktioner, t.ex. "godkänd" eller "avklarad".</p>
<p>Textfärg och Bakgrundsfält definierar de färger som används vid visning av denna kategoris händelser.</p>
<p>När en kategori raderas finns den fortfarande kvar för de händelser som redan tillhör denna kategori.</p>
<br></li>
<li><h6>Användargrupper</h6>
<p>Denna sida används för att visa, skapa och redigera användargrupper. Varje användargrupp kan tilldelas egna rättigheter, kategorier och en egen gruppfärg. Valbara rättigheter är: Inga, Visa, Spara egna, Spara alla och Administratör. Alla användare inom samma grupp har samma rättigheter, kategorier och gruppfärg.</p>
<br></li>
<li><h6>Användare</h6>
<p>Denna sida används för att visa, skapa och redigera användarkonton. För varje användare måste namn, epost, lösenord och användargrupp anges. Användarens rättigheter och valbara händelsekategorier är samma som användargruppens. Det är viktigt att ange en giltig epostadress för att användaren ska kunna ta emot meddelanden.</p>
<p>På sidan 'Inställningar' kan administratören aktivera användares "Självregistrering" och bestämma vilken användargrupp självregistrerade användare automatiskt ska tillhöra. När självregistrering är aktiverad kan användare registrera sig själva direkt via webbläsaren.</p> 
<p>Om kalenderns administratör inte har tilldelat gästanvändare visningsrättighet måste alla användare logga in med användarnamn eller epostadress och dessutom lösenord för att kunna visa kalendern.</p>
<p>Vid inloggning kan användaren välja sitt eget förvalda språk för användargränssnittet. Om inget språk anges, används det språk som administratör angett i 'Inställningar'.</p>
<br></li>
<?php if ($usr['privs'] == 9) { //administrator only ?>
<li><h6>Databas</h6>
<p>På denna sida kan kalenderns administratör använda följande funktioner:</p>
<ul>
<li>Komprimera databas - frigör "raderat" lagringsutrymme. Händelser som raderats för mer än 30 dagar sedan kommer helt och hållet att avlägsnas ur databasen.</li>
<li>Säkerhetskopiera databas - skapar en säkerhetsfil som kan användas för att återställa hela kalenderns databas.</li>
<li>Återställ databas - exekverar en tidigare skapad säkerhetsfil som återskapar kalenderns databas-tabeller (strukturer och data).</li>
<li>Radera/Återskapa händelser - raderar/återskapar händelser som inträffar inom en angiven tidsperiod.</li>
</ul>
<p>Komprimering av databas kan göras exempelvis en gång per år för att "städa upp" i tabellerna. Säkerhetskopiering bör ske oftare (beroende på hur ofta händelser skapas/redigeras/raderas). Radera gärna gamla och oviktiga händelser från föregående år.</p>
<br></li>
<li><h6>Importera CSV-fil</h6>
<p>Händelser från andra kalenderprogram (t.ex. MS Outlook) kan importeras till LuxCal-kalendern. Vidare instruktioner finns på sidan 'Importera CSV-fil'.</p>
<br></li>
<li><h6>Importera iCal-fil</h6>
<p>Händelser från iCal-filer (med filtillägg .ics) kan importeras till LuxCal-kalendern. Vidare instruktioner finns på sidan 'Importera iCal-fil'. Endast händelser som är kompatibla med LuxCal-kalendern kommer att importeras. Andra komponenter som t.ex. Att-göra, Journal, Ledig/Upptagen, Tidszon och Alarm kommer att ignoreras.</p>
<br></li>
<li><h6>Exportera iCal-fil</h6>
<p>Kalenderhändelser kan exporteras till en iCal-fil (med filtillägg .ics). Vidare instruktioner finns på sidan 'Exportera iCal-fil'.</p>
<br></li>
<?php } ?>
</ol>
</li>
<?php } ?>

<li id="al"><h3>Om LuxCal</h3>
<p>Producerad av: <b>Roel Buining</b>&nbsp;&nbsp;&nbsp;&nbsp;Hemsida och forum: <b><a href="https://www.luxsoft.eu/" target="_blank">www.luxsoft.eu/</a></b></p>
<p>LuxCal är freeware (gratis, men donationer uppskattas) och får distribueras och/eller modifieras på villkor enligt <b><a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">GNU General Public License</a></b>.</p>
<br></li>
</ol>
</div>