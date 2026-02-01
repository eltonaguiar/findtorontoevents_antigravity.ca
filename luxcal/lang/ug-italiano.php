<?php
/*
= LuxCal on-line user guide =

Tradotto in Italiano da Angelo.G. - per commenti contattare elghisa@gmail.com

This file is part of the LuxCal Web Calendar.
*/

?>
<div style="margin:0 20px">
<div class="floatR">
<img src="lang/ug-layout.png" alt="LuxCal page layout"><br>
<span class="hired">a</span>: barra del titolo&nbsp;&nbsp;<span class="hired">b</span>: barra di navigazione&nbsp;&nbsp;<span class="hired">c</span>: giorno
</div>
<br>
<h3>Indice</h3>
<ol>
<li><p><a href="#ov">Panoramica</a></p></li>
<li><p><a href="#li">Fare il Log In</a></p></li>
<li><p><a href="#co">Opzioni del Calendario</a></p></li>
<li><p><a href="#cv">Viste del Calendario</a></p></li>
<li><p><a href="#ts">Ricerca Testo</a></p></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li><p><a href="#ae">Aggiungere / Modificare / Eliminare un Evento</a></p></li>
<?php } ?>
<li><p><a href="#lo">Fare il Log Out</a></p></li>
<?php if ($usr['privs'] > 3) { //if manager/administrator ?>
<li><p><a href="#ca">Amministrazione del Calendario</a></p></li>
<?php } ?>
<li><p><a href="#al">Informazioni su LuxCal</a></p></li>
</ol>
</div>
<div class="clear">
<br>
<ol>
<li id="ov"><h3>Panoramica</h3>
<p>Il calendario LuxCal gira su un server web e pu&ograve; essere visto e gestito tramite un browser web.</p>
<p>La barra del titolo mostra il titolo del calendario, la data e il nome dell'utente corrente.
La barra di navigazione contiene molti menu a discesa e link, per navigare, fare il log in e il log out, aggiungere un evento e selezionare le funzioni di amministrazione. Il tipo di menu e di link visualizzati dipendono dai diritti d'accesso dell'utente.
Sotto la barra di navigazione ci sono le varie viste possibili del calendario</p>
<br></li>
<li id="li"><h3>Fare il Log In</h3>
<p>Per usare il calendario cliccare Log In sulla destra della barra di navigazione. Si apre la schermata di log in. Inserire il nome utente o l'indirizzo email (uno dei due) e la password ricevuta dall'amministratore e cliccare Log In. Se si seleziona "Ricordati di me" prima di cliccare Log In, la volta successiva che si lancia il calendario il login sar&agrave; automatico. In caso si dimentichi la password, cliccare Log In e poi cliccare sul link per ricevere una nuova password via email.</p>
<p>&Egrave; possibile cambiare il proprio indirizzo email e password inserendo il nome utente o l'email e la password corrente e poi il nuovo indirizzo email e/o la nuova password.</p>
<p>Se l'amministratore del calendario ha dato i diritti di Visione agli utenti con accesso pubblico, il calendario pu&ograve; essere consultato senza fare il log in.</p>
<br></li>
<li id="co"><h3>Opzioni del Calendario</h3>
<p>Cliccando il pulsante Opzioni sulla barra di navigazione si apre il Pannello Opzioni del calendario. In questo pannello, tramite le caselle di controllo, si possono selezionare le seguenti ozpioni:</p>
<ul style="margin:0 20px">
<li><p>La vista del calendario (anno, mese, settimana, giorno, eventi prossimi, modifiche o matrix).</p></li>
<li><p>Un filtro sugli eventi basato sul proprietario. Si possono selezionare gli eventi di un singolo o di pi&ugrave; proprietari.</p></li>
<li><p>Un filtro sugli eventi basato sulle categorie. Si possono selezionare gli eventi di una singola o di pi&ugrave; categorie.</p></li>
<li><p>La lingua dell'interfaccia utente.</p></li>
</ul>
<p>Nota: La visualizzazione del menu dei filtri sugli eventi e del menu della lingua pu&ograve; essere abilitata/disabilitata dall'amministratore del calendario.</p>
<p>Dopo aver fatto le proprie scelte nel Pannello Opzioni, si deve premere di nuovo il pulsante Opzioni nella barra di navigazione per rendere effettive le scelte fatte.</p> 
<br></li>
<li id="cv"><h3>Viste del Calendario</h3>
<p>In tutte le viste, appariranno ulteriori dettagli sugli eventi passandoci sopra con il mouse. Per gli eventi privati il colore di fondo della finestra di pop up sarà di colore verde chiaro. Nella vista eventi prossimi, gli URL nel campo descrizione dell'evento, diventano automaticamente collegamenti ipertestuali per i relativi siti web.</p>
<p>Se si hanno sufficienti diritti d'accesso:</p>
<p>In tutte le viste cliccando un evento si aprir&agrave; la finestra Modifica Evento relativa all'evento, che si pu&ograve; usare per vedere, modificare o eliminare l'evento.</p>
<ul>
<li><p>Nelle viste per anno e mese si pu&ograve; aggiungere un evento in una certa data cliccando nella parte superiore di una casella del giorno (sulla riga dove si vede il giorno del mese).</p></li>
<li><p>Nelle viste per settimana e per giorno, si pu&ograve; aprire una finestra Aggiungi evento trascinando il cursore sopra un certo intervallo di tempo; i campi data e ora saranno precaricati con i valori selezionati.</p></li>
<li><p>Per spostare un evento da una data ad un'altra o ad un altro orario, aprire la finestra Modifica evento cliccando l'evento e modificare la data o l'ora. Non si possono trascinare gli eventi in una nuova data o ora.</p></li>
</ul>
<p>Per spostare un evento ad una nuova data od orario, aprire la finestra Modifica Evento cliccando sull'evento e modificare la data e/o l'ora. Non si possono trascinare gli eventi su una nuova data o orario.</p>
<p>Eventi di una categoria per cui l'amministratore abbia attivato una casella ci controllo, avranno una casella visualizzata di fronte al titolo dell'evento, che si pu&ograve; usare per marcare gli eventi per es. come "completati". Avendo diritti sufficienti, si pu&ograve; cliccare sulla casella per marcarla o no.</p>
<br></li>
<li id="ts"><h3>Ricerca Testo</h3>
<p>Cliccando il pulsante con il triangolo a destra nella barra di navigazione, si apre la pagina Ricerca Testo. In questa pagina si possono inpostare i criteri di ricerca del testo. Nella pagina Ricerca Testo ci sono istruzioni specifiche.</p>
<br></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li id="ae"><h3>Aggiungere / Modificare / Eliminare un Evento</h3>
<p>Per Aggiungere / Modificare / Eliminare un Evento si deve usare la finestra Eventi, che pu&ograve; essere aperta in diversi modi, come spiegato nel seguito.</p>
<br><h6>a. Aggiungere un Evento</h6>
<p>Si possono aggiungere gli eventi in molti modi:</p>
<ul style="margin:0 20px">
<li><p>cliccando sul pulsante Aggiungi un Evento nella barra di navigazione</p></li>
<li><p>cliccando la parte superiore della casella di un giorno nelle viste per mese o per anno</p></li>
<li><p>trascinando una certa parte del giorno nelle viste per settimana o per giorno</p></li>
</ul>
<p>Cos&igrave; facendo si apre la finestra Evento con un modulo per inserire le informazioni dell'evento. Alcuni campi saranno precompilati, a seconda del modo scelto tra quelli descritti prima per aggiungere l'evento.</p>
<p>Nella prima parte del modulo si possono inserire il titolo, sede, categoria e una descrizione, e si pu&ograve; selezionare l'opzione Evento Privato. Si consiglia di tenere il titolo dell'evento breve ed usare il campo descrizione per i dettagli. La sede e la categoria dell'evento sono opzionali. La selezione di una categoria codificher&agrave; con un colore l'evento in tutte le viste, in accordo con il colore della categoria. La sede e la descrizione appariranno in un riquadro al passaggio del mouse sopra l'evento, nelle varie viste del calendario. Un evento privato sar&agrave; visibile solo al proprietario, e non agli altri utenti.</p>
<p>Gli URL aggiunti nella descrizione di un evento, nel formato [ url | nome ] (per esempio [www.miosito.com | mionome]), saranno automaticamente convertiti in collegamenti ipertestuali che potranno essere selezionati nella vista per mese, nella vista eventi futuri e nelle email di notifica.</p>
<p>Nella seconda parte del modulo, si possono specificare data e ora. Se si seleziona Evento per tutto il giorno, non sar&agrave; visualizzato un orario nelle viste del calendario. La data fine &egrave; opzionale e pu&ograve; essere usata per eventi che si svolgono su pi&ugrave; giorni. Si possono inserire date e orari manualmente o tramite i pulsanti di selezione data e ora. Seguendo i campi della data e ora, gli Eventi possono essere definiti come ricorrenti tramite una finestra di dialogo che si apre cliccando sul pulsante Cambia. In questo caso l'evento sar&agrave; ripetuto come specificato dalla data d'inizio a quella finale. Se non viene specificata una data finale (sino a), l'evento sar&agrave; ripetuto per sempre, il che &egrave; particolarmente utile nei casi di ricorrenze come i compleanni.</p>
<p>Nell'ultima parte del modulo, attraverso la funzione Notifica, &egrave; possibile deecidere di mandare un messaggio email come promemoria ad uno o pi&ugrave; indirizzi email un certo numero di giorni prima della data in cui &egrave; programmato l'evento. Inoltre, un secondo promemoria sar&agrave; inviato per email automaticamente il giorno dell'evento. Per gli eventi ricorrenti un promemoria via email sar&agrave; inviato un numero di giorni selezionato prima di ogni occorrenza dell'evento e in ogni giorno di occorrenza dell'evento.</p>
<p>Dopo aver finito cliccare Aggiungi Evento.</p>
<p>Se si seleziona la casella "Non chiudere questa finestra", la finestra degli Eventi non si chiuder&agrave; quando si preme Aggiungi Evento. In questo caso tre nuovi pulsanti appariranno in basso nella finestra, per aggiornare l'evento aggiunto, per eliminare l'evento aggiunto, o per riusare i dati correnti dell'evento per creare un nuovo evento, per esempio per duplicare l'evento in un altra data.</p>
<br>
<h6>b. Modificare / Eliminare un Evento</h6>
<p>In ogni vista del calendario si pu&ograve; cliccare un evento per vederlo, modificarlo o eliminarlo. Questo far&agrave; aprire la finestra Modifica Evento, simile alla finestra Evento descritta prima, tranne per i pulsanti in basso.</p>
<p>In funzione dei diritti d'accesso, sar&agrave; possibile vedere/modificare/eliminare i propri eventi o vedere/modificare/eliminare tutti gli eventi, inclusi gli eventi degli altri uenti.</p>
<p>Per una descrizione dei campi, vedere le descrizioni date precedentemente in Aggiungere un Evento.</p>
<p>Se si elimina un evento ricorrente verranno eliminate tutte le istanze dell'evento, non solo quello in una data specifica.</p>
<br></li>
<?php } ?>
<li id="lo"><h3>Fare il Log Out</h3>
<p>Per fare il log out, cliccare Log Out nella barra di navigazione. Se si chiude il calendario senza fare il log out, la volta successiva che si apre il calendario, potrebbe aprirsi senza chiedere di fare il log in.</p>
<br></li>
<?php if ($usr['privs'] == 9) { //administrator only ?>
<li id="ca"><h3>Amministrazione del Calendario</h3>
<p><b> Le seguenti funzioni richiedono i diritti di amministratore </b></p>
<p>Se un utente fa il log in e possiede i diritti di aministratore, un nuovo menu, Amministrazione, apparir&agrave; a destra nella barra di navigazione. Da quel menu sono accessibili le seguenti funzioni di amministrazione:</p>
<br>
<h6>a. Impostazioni</h6>
<p>Questa pagina mostra le impostazioni correnti del calendario che si possono modificare. Le inmpostazioni sono spiegate nella pagina Modifica impostazioni Calendario. La pagina fornisce una buona descrizione di tutte le possibili impostazioni.</p>
<br>
<h6>b. Categorie</h6>
<p>L'aggiunta delle categorie degli eventi in diversi colori, anche se non necessaria, aumenta la visibilit&agrave; del calendario. Esempi di possibili Categorie sono 'vacanze', 'appuntamenti', 'compleanni', 'importante', ecc.</p>
<p>L'installazione iniziale ha una sola categoria, di nome 'no cat'. Selezionando Categorie dal menu amministrazione porta ad una pagina con un elenco delle categorie, con la possibilit&agrave; di aggiungerne di nuove o di modificare/eliminare categorie esistenti.</p>
<p>Quando si aggiunge / modifica un evento si pu&ograve; selezionare una categoria gi&agrave; definita da un elenco a discesa. L'ordine in cui compaiano le categorie nell'elenco a discesa &egrave; determinato dal campo Sequenza. I campi colore testo e colore di fondo definiscono i colori utilizzati per visualizzare gli eventi di quella categoria.</p>
<p>Quando si aggiunge / modifica una categoria si pu&ograve; impostare un valore di 'ripetizione'; gli eventi in questa categoria saranno automaticamente ripetuti secondo quanto specificato. La casella di controllo 'Pubblico' pu&ograve; usata per impedire agli eventi che appartengono a questa categoria di essere visti dagli utenti con accesso pubblico (utenti non loggati) e per escluderli dai feed RSS.</p>
<p>Si pu&ograve; attivare una casella di controllo, in modo che ci sia nel calendario una casella di fronte al titolo dell'evento per tutti gli eventi di questa categoria. L'utente pu&ograve; usare questa casella per marcare gli eventi per es. come "completati". I campi Colore Testo e Sfondo definiscono i colori usati per mostrare nel calendario gli eventi di questa categoria.</p>
<p>Quando si elimina una categoria, gli eventi che appartengono a questa categoria saranno passati alla categoria 'no cat'.</p>
<br>
<h6>c. Utenti</h6>
<p>La pagina utenti consente all'amministratore del calendario di aggiungere utenti e modificare i loro diritti d'accesso. Si possono modificare due aree principali: il nome/email/password dell'utente e i diritti d'accesso dell'utente. Possibili diritti di accesso sono: Vedi, Crea solo i propri eventi, Crea eventi di tutti, Amministratore. &Egrave; importante usare un indirizzo email valido, per consentire all'utente di ricevere le notifiche via email delle date degli eventi.</p>
<p>Tramite la pagina Impostazioni, l'amministratore pu&ograve; abilitare "l'autoregistrazione degli utenti" e impostare i diritti d'accesso per gli utenti che si autoregistrano. Se l'autoregistrazione &egrave; abilitata, gli utenti si possono registrare al calendario tramite l'interfaccia del browser.</p> 
<p>A meno che l'amministratore abbia dato il diritto di Visualizare agli utenti che hanno un accesso pubblico, gli utenti devono fare il log in, usando il loro nome utente o indirizzo email e password. In funzione del tipo di utente, si possono assegnare differenti diritti d'accesso.</p>
<p>Per ciascun utente si pu&ograve; impostare la lingua predefinita per l'interfaccia utente dopo il log in. Se non si specifica una lingua, verr&agrave; usata la lingua predefinita specificata nella pagina delle impostazioni.</p>
<br>
<h6>d. Database</h6>
<p>La pagina del database consente all'amministratore del calendario di eseguire le seguenti operazioni:</p>
<ul>
<li>Verifica e Ripara il database, per trovare e risolvere incoerenze nelle tabelle del database</li>
<li>Compatta il database, per liberare spazio inutilizzato ed evitare spreco di risorse</li>
<li>Backup del database, per creare un file di backup che pu&ograve; essere usato per ricreare le tabelle, la struttura e i dati del database</li>
</ul>
<p>La prima funzione, Verifica e Ripara il database, va eseguita solo se le viste del calendario non funzionano perfettamente. La seconda funzione, Compatta il database, pu&ograve; essere eseguita una volta all'anno per ripulire il database, la terza funzione, Backup del database, dovrebbe essere eseguita pi&ugrave; frequentemente, in funzione del numero di modifiche apportate.</p>
<br>
<h6>e. Importazione dei file CSV</h6>
<p>Si usa questa funzione per importare nel Calendario Luxcal i dati di eventi esportati da altri calendari (per es. MS Outlook). Ulteriori istruzioni sono nella pagina Importazione CSV.</p>
<br>
<h6>f. Importazione dei file iCal</h6>
<p>Si usa questa funzione per importare nel Calendario Luxcal gli eventi presenti in un file iCal (estensione del file .ics). Ulteriori istruzioni sono presenti nella pagina Importazione iCal. Saranno importati solamente gli eventi compatibili con il Calendario LuxCal. Altri componenti, come: To-Do, Journal, Free / Busy, Timezone e Alarm, saranno ignorati.</p>
<br>
<h6>g. Esportazione dei file iCal</h6>
<p>Si usa questa funzione per esportare gli eventi di LuxCal in un file iCal (estensione del file .ics). Ulteriori istruzioni sono presenti nella pagina Esportazione iCal.</p>
<br>
</li>
<?php } ?>
<li id="al"><h3>Informazioni su LuxCal</h3>
<p>Prodotto da: <b>Roel Buining</b>&nbsp;&nbsp;&nbsp;&nbsp;Sito web e forum: <b><a href="https://www.luxsoft.eu/" target="_blank">www.luxsoft.eu/</a></b></p>
<p>LuxCal &egrave; gratuito (freeware) e pu&ograve; essere ridistribuito e/o modificato secondo i termini della <b><a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">GNU General Public License</a></b>.</p>
<br></li>
</ol>
</div>