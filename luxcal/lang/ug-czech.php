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
<span class="hired">a</span>: titulkový pruh&nbsp;&nbsp;<span class="hired">b</span>: navigační pruh&nbsp;&nbsp;<span class="hired">c</span>: den
</div>
<br>
<h3>Obsah</h3>
<ol>
<li><p><a href="#ov">Přehled</a></p></li>
<li><p><a href="#li">Přihlášení</a></p></li>
<li><p><a href="#co">Volby kalendáře</a></p></li>
<li><p><a href="#cv">Pohledy</a></p></li>
<li><p><a href="#ts">Textové vyhledávání</a></p></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li><p><a href="#ae">Přidat / Upravit / Smazat událost</a></p></li>
<?php } ?>
<li><p><a href="#lo">Odhlášení</a></p></li>
<?php if ($usr['privs'] > 3) { //if manager/administrator ?>
<li><p><a href="#ca">Administrace kalendáře</a></p></li>
<?php } ?>
<li><p><a href="#al">O LuxCalu</a></p></li>
</ol>
</div>
<div class="clear">
<br>
<ol>
<li id="ov"><h3>Přehled</h3>
<p>Kalendář LuxCal je webová aplikace provozovaná na webovém serveru. Přístup a administrace probíhá pomocí internetového prohlížeče.</p>
<p>V titulkovém pruhu se zobrazuje název kalendáře, datum a jméno aktuálního uživatele.
Pod titulkovým pruhem se nachází navigační pruh, který obsahuje rozbalovací menu a odkazy pro pohyb v kalendáři, přihlášení/odhlášení, přidávání událostí a výběr funkcí pro administrace. Která menu a odkazu jsou zobrazena, to záleží na uživatelských oprávněních.
Hlavní část zobrazení zaujímá pohled na kalendář.</p>
<br></li>
<li id="li"><h3>Přihlášení</h3>
<p>Abyste mohli kalendář používat, přihlaste se kliknutím na pravé straně navigačního pruhu. Zobrazí se vám přihlašovací dialog. Zadejte buď uživatelské jméno, nebo e-mailovou adresu (jedno z nich) a heslo, které jste obdrželi od vašeho administrátora. Pokud zaškrtnete "Pamatovat si mě", budete při přístím otevření kalendáře automaticky přihlášeni. Když zapomenete heslo, klikněte na Přihlášení a poté na odkaz "zaslat nové heslo", čímž vám bude zasláno nové heslo e-mailem.</p>
<p>Na přihlašovací obrazovce můžete také po kliknutí na "změnit moje údaje" upravit vaše údaje pro přihlášení.</p>
<p>Pokud je administrátorem kalendáře povolena samoobslužná registrace a vy ještě nemáte vlastní přihlašovací údaje můžete se rovnou zaregistrovat. V opačném případě vám musí administrátor předem vytvořit uživatelský účet.</p>
<p>Pokud přidělil administrátor oprávnění k prohlížení kalendáře uživateli public, je obsah přístupný i bez nutnosti přihlášení.</p>
<br></li>
<li id="co"><h3>Volby kalendáře</h3>
<p>Kliknutí na tlačítko Volby na navigačním pruhu otevře panel voleb. Zaškrtáváním políček můžete nastavit následující:</p>
<ul style="margin:0 20px">
<li><p>Pohled kalendáře (rok, měsíc, týden, den, blízké události, změny, matrix).</p></li>
<li><p>Filtr událostí podle vlastníka. Můžete zvolit jednoho nebo více vlastníků najednou.</p></li>
<li><p>filtr událostí podle kategorií. Můžete zvolit zobrazení událostí patřících do jedné nebo více kategorií.</p></li>
<li><p>Jazyk uživatelského rozhraní.</p></li>
</ul>
<p>Poznámka: Zobrazení filtrů a menu pro výběr jazyka může zapínat/vypínat administrátor kalendáře.</p>
<p>Poté, co jste provedli změny na panelu voleb, klikněte opět na tlačítko Volby na navigačním pruhu aby se změny projevily.</p> 
<br></li>
<li id="cv"><h3>Pohledy</h3>
<p>U všech pohledů se zobrazují podrobnosti události v bublině při zaměření události myší. U soukromých událostí je okraj bubliny světle zelený, u opakovaných nebo vícedenních je červený. V přehledu blízkých událostí je každý URL v popisu automaticky převeden na hyperlink.</p>
<p>Events in a category for which the admin has activated a check box will have a check box displayed in front of the event title, which can be used to flag events for example as "completed". When having sufficient rights, this check box can be clicked to check/uncheck it.</p>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<p>Pokud máte dostatečná přístupová práva:</p>
<ul style="margin:0 20px">
<li><p>Ve všech pohledech se otevře okno editace události, ve kterém můžete prohlížet, upravovat a mazat událost.</p></li>
<li><p>V ročním a měsíčním pohledu můžete přidat událost na daný den kliknutím na horní část odpovídající buňky dne (řádek, ve kterém je zobrazeno označení dne nebo měsíce).</p></li>
<li><p>V týdenním a denním pohledu se okno pro přidání události otevře po označení časového rozmezí myší v kalendáři. Pole data a času jsou předvyplněna odpovídajícími údaji časového rozmezí.</p></li>
</ul>
<p>V přehledu změn můžete určit počáteční datum. Zobrazí se seznam událostí, přidaných, upravených a smazaných od tohoto data do současnosti.</p>
<p>Pro přesun události na jiný den, nebo čas otevřete okno události kliknutím na událost. Změňte údaje o datu a nebo času. Události nelze přetahovat na jiné termíny.</p>
<?php } ?>
<br></li>
<li id="ts"><h3>Textové vyhledávání</h3>
<p>Stisknutím tlačítka s obráceným trojuhelníkem na pravé straně navigačního pruhu přejdete na stránku pro textové vyhledávání, kde můžete zadat svůj dotaz. Stránka obsahuje další podrobné instrukce.</p>
<br></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li id="ae"><h3>Přidat / Upravit / Smazat událost</h3>
<p>Přidávání, úprava a mazání událostí probíhá v okně události, které lze otevřít několika způsoby jak je popsáno dále.</p>
<br><h6>a. Přidat událost</h6>
<p>Událost můžete přidat několika způsoby:</p>
<ul style="margin:0 20px">
<li><p>klikněte na tlačítko Přidat událost v navigačním pruhu (+)</p></li>
<li><p>klikněte na horní okraj vybraného dne v ročním nebo měsíčním pohledu</p></li>
<li><p>označte tažením myší určitou část dne v denním nebo týdenním pohledu</p></li>
</ul>
<p>Každá tato akce vyvolá otevření editačního okna s formulářem, kam zadáte údaje o události. Některá pole budou předvyplněna podle toho který z uvedených způsobů jste použili k vložení události.</p>
<p>Zadejte název, místo, kategorii a popis události. Název události udržujte pokud možno co nejkratší, případné podrobnosti napište dále do pole Popis. Kategorie a místo konání jsou nepovinné položky. Pokud událost zařadíte do kategorie, je jí přiřazena odpovídající barva podle nastavení kategorie. Místo konání a popis se později objeví v bublině při přejezdu myší přes událost v kalendáři. Dále můžete událost označit jako soukromou, bude se tak zobrazovat pouze vám.</p>
<p>Zadáte-li do popisu URL, bude automaticky převedeno na hyperlink, na který lze kliknout v měsíčním pohledu, zobrazení blízkých událostí a notifikačních e-mailech. Formát URL odkazů může být buď url nebo url [popis odkazu], např. https://www.google.com nebo https://www.google.com [hledej]. Pokud neuvedete popis odkazu, bude se u události zobrazovat celé URL.</p>
<p>Dále jsou v editačním okně údaje o datu a čase konání události. Zvolíte li celodenní událost, nebudou se u ní v kalendáři zobrazovat časy. Datum konce je nepovinné a může být nastaveno u vícedenních událostí. Data a časy lze zapsat přímo, nebo výběrem z menu. Následuje volba opakování události pomocí zvláštního dialogu. V tomto případě se bude událost opakovat podle zadání od počátečního do konečného data. Není-li vyplněno konečné datum bude se opakovat navždy. to je vhodné například pro narozeniny.</p>
<p>V poslední části je nastavení notifikace. Můžete si nechat poslat e-mailovou připomínku přímo na jednu, nebo více adres ihned pokud zaškrtnete volbu 'teď', a nebo určitý počet dní před konáním události. Připomínka bude zaslána také v den konání. Pokud nastavíte počet dní na '0', přijde připomínka až v den konání. U opakovaných akcí, je e-mail zasílán pokaždé podle zadaných kriterií.</p>
<p>Seznam e-mailů múže obsahovat e-mailové adresy a nebo název souboru distribučního seznamu, oddělené středníky. Distribuční seznam musí být soubor s příponou .txt v adresáři "reciplists/" obsahující adresy příjemců, na každém řádku jednu. Název souboru s distribučním seznamem nesmí obsahovat znak zavináč @.</p>
<p>Událost uložíte stiskem tlačítka Přidat.</p>
<br>
<h6>b. Upravit / Smazat událost</h6>
<p>V různých pohledech kalendáře se po rozkliknutí události otevře okno s detaily události. Máte-li dostatečné oprávnění můžete kliknout na tlačítko Upravit a pak změnit, duplikovat nebo smazat událost. Otevře se editační okno, kde lze změnit veškeré podrobnosti.</p>
<p>V závislosti na úrovni vašeho oprávnění můžete události prohlížet, prohlížet/měnit/mazat své události, nebo prohlížet/měnit/mazat všechny události, včetně těch od jiných uživatelů. Pokud nemáte oprávnění pro editaci, tlačítko Upravit bude neaktivní.</p>
<p>Význam jednotlivých polí je popsán v odstavci Přidání události výše.</p>
<p>V okně pro editaci události jsou tlačítka pro uložení změn, uložení změn jako nové události (pro duplikaci upravované události na jiné datum) a smazání události.</p>
<p>Mazání opakované události odstraní všechny výskyty této události, ne jen jednu vybranou.</p>
<br></li>
<?php } ?>
<li id="lo"><h3>Odhlášení</h3>
<p>Pro odhlášení klikněte na tlačítko Odhlásit v navigačním pruhu. Pokud uzavřete kalendář bez odhlášení, můžete při dalším otevření pokračovat bez nutnosti přihlašování.</p>
<br></li>
<?php if ($usr['privs'] == 9) { //administrator only ?>
<li id="ca"><h3>Administrace</h3>
<p>- následující činnosti vyžadují oprávnění administrátora kalendáře -</p>
<p>Po přihlášení uživatel s administrátorským oprávněním se na pravé straně navigačního pruhu objeví rozbalovací menu Administrace. Prostřednictvím tohoto menu jsou dostupné následující funkce:</p>
<br>
<h6>a) Nastavení</h6>
<p>Stránka zobrazí a umožní změnu nastavení kalendáře. Význam jednotlivých položek vysvětluje bublina, která se objeví po najetí myší na každou z nich.</p>
<p>Nastavení kalendáře se ukládá do souboru config.php na serveru. Je rozumné uložit si zálohu tohoto souboru.</p>
<br>
<h6>b) Kategorie</h6>
<p>Roztřídění jednotlivých událostí do barevně odlišených kategorií (přestože není nutné) výrazně zlepší přehlednost kalendáře. Příkladem kategorií jsou například 'prázdniny', 'schůzky', 'narozeniny', 'důležité' apod.</p>
<p>Po instalaci je vytvořena pouze jediná kategorie. Vyberte z administračního menu položku Kategorie a přejděte na stránku se seznamem kategorií, kde lze jednotlivé kategorie přidávat, editovat a mazat.</p>
<p>Pokud přidáváte nebo měníte události lze kategorii do které mají patřit vybírat z roletového menu. Pořadí v jakém se kategorie v tomto menu řadí určuje pole Pořadí.</p>
<p>Při nastavování vlastností kategorií lze nastavit i hodnotu Opakování. Události v této kategorii budou automaticky opakovány podle tohoto nastavení. Pokud odškrtnete pole Veřejné nebudou události této kategorie viditelné pro nepřihlášené uživatele a nebudou publikovány přes RSS kanál.</p>
<p>Můžete zapnout zatžítko, které se pak bude zobrazovat u názvu události pro všechny události v dané kategorii. Uživatelé tak mohou využít toto označení u událostí, které jsou "hotové".</p>
<p>Barevné rozlišení kategorií v kalendáři lze nastavit položkami Barva textu a Barva pozadí.</p>
<p>Pokud nějakou kategorii smažete, události, které do ní patřily se přesunou do výchozí kategorie (s číslem 0).</p>
<br>
<h6>c) Uživatelé</h6>
<p>Ve správě uživatelů může administrátor prohlížet, přidávat a měnit uživatele, jejich oprávnění a nastavení výchozího jazyka rozhraní, zobrazit datum prvního a posledního přihlášení. Editace zahrnuje tyto hlavní oblasti: jméno/e-mail/heslo a přístupové oprávnění a jazyk uživatelského rozhraní. Oprávnění lze nastavit na: prohlížení kalendáře, vkládat a měnit vlastní, vkládat a měnit všechny a administrátor. Je důležité zadat platnou e-mailovou adresu, aby uživatel mohl dostávat upozornění na události a termíny.</p>
<p>V Nastavení může administrátor povolit samoobslužnou registraci a nastavit přístupová práva pro samoregistrované uživatele. Pokud je samoobslužná registrace povolena, mohou se uživatelé sami registrovat přes webové rozhraní.</p> 
<p>Pokud není administrátorem povoleno prohlížení kalendáře i neregistrovaným návštěvníkům, musí se uživatelé přihlásit buď jménem nebo e-mailem a heslem. Různí uživatelé mohou mít různá oprávnění.</p>
<p>Jednotliví uživatelé mohou mít přednastaven různý jazyk uživatelského rozhraní po přihlášení. Když není uživatel přihlášen použije se výchozí jazyk kalendáře podle stránky Nastavení.</p>
<br>
<h6>d) Databáze</h6>
<p>Tato stránka umožňuje administrátorovi spouštět následující funkce:</p>
<ul>
<li>Kontrola a oprava databáze. Nalezne a vyřeší inkonzistence v tabulkách databáze.</li>
<li>Komprimace databáze. Uvolní nepoužívané místo v databázi. Tato funkce trvale vymaže události, které byly odstraněny před více jak 30ti dny.</li>
<li>Záloha databáze. Vytvoří soubor se zálohou, který může být použit pro obnovu struktury databáze a datových tabulek.</li>
</ul>
<p>První funkce, kontrola a oprava je potřeba pouze v případě, když se události v kalendáři nezobrazují správně. Druhou, pro vyčištění databáze, stačí spouštět jednou do roka. Třetí funkce by měla být spouštěna častěji v závislosti na frekvenci změn v kalendáři.</p>
<br>
<h6>e) Import CSV souboru</h6>
<p>Tuto funkci lze použít pro import dat, která byla exportována z jiných kalendářů (např. MS Outlooku). Podrobnější instrukce k této funkci jsou přímo na stránce pro import CSV souborů.</p>
<br>
<h6>f) Import iCal souboru</h6>
<p>Funkce umožňuje import událostí z iCal souborů (přípona souboru .ics) do LuxCal kalendáře. Podrobnější instrukce jsou uvedeny na stránce pro iCal import. Takto importovány jsou pouze události kompatibilní s kalendářem LuxCal. Další položky jako: úkoly, žurnál, příznaky volno/obsazeno, časové zóny a připomínky událostí budou ignorovány.</p>
<br>
<h6>g) Export iCal souboru</h6>
<p>Tato funkce exportuje události z LuxCal kalendáře do iCal souborů (přípona souboru .ics). Podrobnější instrukce jsou u vedeny na stránce pro export do iCal v administraci kalendáře.</p>
<br></li>
<?php } ?>
<li id="al"><h3>O LuxCalu</h3>
<p>Produced by: <b>Roel Buining</b>&nbsp;&nbsp;&nbsp;&nbsp;Website and forum: <b><a href="https://www.luxsoft.eu/" target="_blank">www.luxsoft.eu/</a></b></p>
<p>Tento program je svobodný software; můžete jej šířit a nebo měnit za podmínek určených <b><a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">GNU General Public License</a></b>.</p>
<br></li>
</ol>
</div>