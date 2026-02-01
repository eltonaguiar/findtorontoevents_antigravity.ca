<?php
/*
= LuxCal on-line user guide =

This user guide has been produced by LuxSoft - please send your comments to rb@luxsoft.eu.
Traduzido para Português-Portugal (Rodrigo Pedro) - Contacto: rodrigocaetanopedro@gmail.com

This file is part of the LuxCal Web Calendar.
*/

?>
<div style="margin:0 20px">
<div class="floatR">
<img src="lang/ug-layout.png" alt="LuxCal page layout"><br>
<span class="hired">a</span>: barra de título&nbsp;&nbsp;<span class="hired">b</span>: barra de navegação&nbsp;&nbsp;<span class="hired">c</span>: dia
</div>
<br>
<h3>Tabela de conte&uacute;dos</h3>
<ol>
<li><p><a href="#ov">Resumo</a></p></li>
<li><p><a href="#li">Iniciar Sessão</a></p></li>
<li><p><a href="#ae">Adiconar Evento</a></p></li>
<li><p><a href="#ee">Editar/Eliminar Evento</a></p></li>
<li><p><a href="#co">Calendar Options</a></p></li>
<li><p><a href="#cv">Tipos de vistas</a></p></li>
<li><p><a href="#ts">Text Search</a></p></li>
<li><p><a href="#lo">Terminar Sessão</a></p></li>
<li><p><a href="#ca">Adminstrar Calendário</a></p></li>
<li><p><a href="#al">About LuxCal</a></p></li>
</ol>
</div>
<div class="clear">
<br>
<ol>
<li id="ov"><h3>Resumo</h3>
<p>O calendário LuxCal é executado num servidor de internet e pode ser visto e gerido através do navegador de internet.</p>
<p>A barra de título exibe o título do calendário, a data e o nome do utilizador que tem a sessão iniciada.
Da parte de baixo da barra de título, existe a barra de navegação que contém vários menus e hiperligações, para navegar, iniciar/terminar a sessão, adicionar eventos e selecionar as funções administrativas. Os menus e as hiperligações são visualizados dependendo dos privilégios dos utilizadores.
Abaixo da barra de navegação é exibido diferentes vistas do calendário.</p>
<br></li>
<li id="li"><h3>Iniciar Sessão</h3>
<p>Para usar o calendário clique em Iniciar a Sessão disponível do lado direito da barra de navegação. Irá ser redimensionado para a página do 'Início de Sessão'. Introduza o nome do utilizador ou o endereço de e-mail (um dos dois) e a senha recebida pelo administrador e clique em 'Iniciar Sessão'. If you select "Remember me" before clicking Log In, next times you launch the calendar you will be automatically logged in. Se esqueceu-se da senha, clique em Iniciar a Sessão e depois clique na hiperligação 'Enviar nova senha' para que receba uma nova senha no seu e-mail.</p>
<p>Pode alterar o seu endereço de e-mail e a senha, introduzindo o nome de utilizador/e-mail e a sua senha atual na hiperligação Alterar os meus dados.</p>
<p>Se o administrador do calendário permitir o acesso público, o calendário é visivel sem iniciar a sessão.</p>
<br></li>
<li id="ae"><h3>Adiconar Evento</h3>
<p>Os eventos podem ser adicionados das seguintes maneiras:</p>
<ul style="margin:0 20px">
<li><p>clicando em botão Adicionar Evento na barra de navegação</p></li>
<li><p>clicando em cima do dia, nas vistas Anual e Mensal</p></li>
<li><p>arrastando até à parte desejada do dia, nas vistas Semanal e Diária</p></li>
</ul>
<p>Cada opção irá abrir a janela de evento com um formulário para inserir as informações do evento. Alguns campos no formulário serão pré-carregadas, dependendo de qual das maneiras acima é usada para adicionar um evento.</p>
<p>Na primeira parte do formulário, podem ser adicionados o título, local, categoria e a descrição do evento. A opção Evento Privado pode ser selecionado, para que o evento não seja visível para os restantes utilizadores. É uma boa prática colocar um título curto e usar o campo de descrição para maiores detalhes. Os campos local e categoria são opcionais. Selecionando uma categoria, esta é associada a uma cor. Para que nas diferentes vistas do calendário distinga-se o tipo de evento. O local e a descrição aparecerão mais tarde quando passar com o cursor sobre o evento, nas diferentes vistas da agenda.</p>
<p>As hiperligações adicionadas na descrição do evento, no formato [ hiperligação | nome ] (por examplo [www.site.com | nome]), irão ser convertidas automaticamente para hiperligações que podem ser selecionadas na vista mensal, próximos eventos e notificação de e-mails.</p>
<p>Na segunda parte do formulário, as datas e as horas podem ser especificadas. Se a opção 'Todo o Dia' estiver selecionada, as horas não serão exibidas nas vistas do calendário. A opção 'Fim' é opcional e pode ser usado para gerir os vários eventos por dia. As datas e as horas podem ser introduzidas manualmente ou através dos botões. Após os campos de data e hora, os eventos podem ser definidos como recorrentes através de uma caixa de diálogo separada, que abre ao clicar no botão Alterar. Neste caso, o evento será repetido, conforme especificado nos campos 'Início' e 'Fim'. Se nenhuma data final (Até) for especificada, o evento irá sempre repetir, o que é particularmente útil para os aniversários.</p>
<p>Na última parte do formulário, através do recurso de notificação, pode optar por enviar um lembrete para um ou mais endereços de e-mail - se a opção 'Agora' estiver selecionada - e/ou um número de dias antes da data do evento. Além disso, um e-mail será enviado automaticamente na data do evento. Para os eventos recorrentes um lembrete será enviado o número selecionado de dias antes de cada ocorrência do evento e na data de cada ocorrência do evento.</p>
<p>Após ter concluído, carregue em 'Adicionar Evento'.</p>
<p>Se a opção 'Não Fechar esta Janela' estiver marcada, a janela do evento não irá fechar quando se carregar em 'Adicionar evento'. Neste caso, três novos botões aparecem na parte inferior da janela, para atualizar o evento que acrescentou, para eliminar o evento adicionado, ou para re-utilizar os dados do evento atual para criar um outro novo evento, por exemplo, para duplicar o evento para uma outra data.</p>
<br></li>
<li id="ee"><h3>Editar/Eliminar Evento</h3>
<p>Em cada uma das vistas do calendário um evento pode ser selecionado para visualizar, editar ou eliminar. Isso abrirá a janela de edição do evento, que é semelhante à janela do evento descrito acima, exceto para os botões na parte inferior da janela.</p>
<p>Dependendo dos seus privilégios, pode ver, ver/editar/eliminar os seus eventos ou ver/editar/eliminar todos os eventos, incluíndo os eventos dos outros utilizadores</p>
<p>Para obter uma descrição dos eventos, passe com o cursor sobre o evento.</p>
<p> Note que excluindo um evento repetitivo, irá eliminar todas as instâncias desse evento e não apenas a da data específica.</p>
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
<li id="cv"><h3>Tipos de vistas</h3>
<p>Em todas as vistas, os detalhes dos eventos irão aparecer quando passa com o rato sobre eles. Para eventos privados a cor de fundo da caixa pop-up será verde claro. Na vista 'Próximos Eventos', os endereços da internet inseridos no campo da descrição dos eventos serão automaticamente transformados em hiperligações, para que aceda automáticamente ao site.</p>
<p>Events in a category for which the admin has activated a check box will have a check box displayed in front of the event title, which can be used to flag events for example as "completed". When having sufficient rights, this check box can be clicked to check/uncheck it.</p>
<p>Quando possui privilégios suficientes:</p>
<ul style="margin:0 20px">
<li><p>Em todas as vistas ao clicar num evento abrirá a janela de edição de eventos, que pode ser usado para visualizar, editar ou eliminar um evento.</p></li>
<li><p>Nas vistas 'Anual' e 'Mensal' um novo evento pode ser adicionado para uma determinda data, clicando na primiera linha do dia. (linha onde o dia do mês é exibido).</p></li>
<li><p>Nas vistas 'Semanal' e 'Diária', a janela 'Adicionar Evento' pode ser aberta arrastando o cursor até a hora desejada; os campos data e a hora serão carregados automaticamente com a data e hora selecionados.</p></li>
</ul>
<p>Na vista 'Gerir Eventos', a data de início pode ser definida. Uma lista com todos os eventos adicionados, editados ou eliminados desde a data de início especificada será exibida</p>
<p>Para mover um evento para uma nova data ou hora, abra a janela 'Editar Evento' clicando no evento e altere a data e a hora. Os eventos não podem ser arrastados para novas datas ou horas.</p>
<br></li>
<li id="ts"><h3>Text Search</h3>
<p>When clicking the button with the triangle on the right side in the navigation bar, the Text Search page will open. On this page the text search can be defined. The Text Search page contains detailed instructions.</p>
<br></li>
<li id="lo"><h3>Terminar Sessão</h3>
<p>Para terminar a sessão, clique em 'Terminar a Sessão' na barra de navegação. Se fechar o calendário sem terminar a sessão, a próxima vez que abrir o calendário, este irá iniciar sem pedir-lhe que inicie a sessão.</p>
<br></li>
<li id="ca"><h3>Adminstrar Calendário</h3>
<p>- Os seguintes fatores requerem privilégios de administrador -</p>
<p>Quando um utilizador se autentica com direitos de administrador, um menu novo, chamado de Administração, irá aparecer do lado direito na barra de navegação. Através deste menu as funções de administrador estarão disponíveis:</p>
<br>
<h6>a. Definições</h6>
<p>Esta página exibe as configurações do calendário atual, que posteriormente poderá ser alterada. Todas as configurações são explicadas na página Alterar Definições do calendário. A página dá uma boa descrição de todas as configurações possíveis.</p>
<br>
<h6>b. Categorias</h6>
<p>Adicionar categorias de eventos com cores diferentes - embora não seja necessário - irá aumentar os pontos de vista do calendário. Exemplos de categorias possíveis são 'férias', 'nomeação', 'aniversário', 'importante', etc</p>
<p>A instalação inicial tem uma única categoria, chamada 'nenhuma categoria'. A opção 'Categorias', no menu de administração leva-o a uma página com a lista de todas as categorias. Tem ainda a possibilidade de adicionar, editar e eliminar categorias.</p>
<p>Ao adicionar/editar categorias pode selecionar a ordem como estas aparecem. A ordem em que as categorias são exibidas na lista é determinada pelo campo 'Sequência'. Os campos Cor do Texto e Fundo definem as cores usadas para exibir os eventos no calendário pertencentes a esta categoria.</p>
<p>When adding / editing categories a 'repeat' value can be set; events in this category will automatically repeat as specified. The checkbox 'Public' can be used to hide events belonging to this category from being viewed by public access users (not logged in users) and exclude them from the RSS feeds.</p>
<p>A check mark can be activated, resulting in the calendar in the display of a check mark in front of the event title for all events in this category. The user can use this check mark to flag events for example as "completed". The fields Text color and Background define the colors used to display events in the calendar belonging to this category.</p>
<p>Quando elimina uma categoria, os eventos associados a essa categoria são associados à categoria 'nenhuma categoria'.</p>
<br>
<h6>c. Utilizadores</h6>
<p>A página dos utilizadores apenas está disponível ao administrador do calendário, para que este, possa adicionar e alterar utilizadores, mas também para selecionar os seus privilégios. Duas campos podem ser editados: o nome do utilizador/e-mail/senha e os privilégios do utilizador. Os privilégios possíveis são: Visualizar, Próprio, Todos e Funções de administrador. É importante utilizar um endereço de e-mail válido, para permitir que o utilizador possa receber notificações por e-mail das datas dos eventos.</p>
<p>Através da página 'Definições', o administrador pode permitir que os utilizadores se registem e definam os seus privilégios. Quando esta opção é ativada, os utilizadores podem registar-se através da interface do navegador.</p> 
<p>A menos que o administrador do calendário tenha dado o acesso público, os utilizadores necessitam de iniciar a sessão, usando os seus nomes de utilizador ou e-mail e a sua senha. Dependendo do tipo de utilizador, um utilizador pode ter diferentes privilégios.</p>
<p>Para cada utilizador o idioma da interface do utilizador pode ser especificado na página "Iniciar Sessão". Se nenhum idioma for indicado, o idioma por defeito será o especificado na página de configurações do calendário.</p>
<br>
<h6>d. Base de Dados</h6>
<p>A página "Base de Dados" permite ao administrador executar as seguintes funções:</p>
<ul>
<li>Verificar e reparar a base de dados, para encontrar e resolver problemas com as tabelas da base de dados</li>
<li>Compactar a base de dados, para libertar espaço de maneira a não subcarregar a aplicação</li>
<li>Cópia de segurança da base de dados, para criar um ficheiro que pode ser usado para recriar a estrutura das tabelas e do conteúdo das mesmas</li>
</ul>
<p>A primeira função, verificar e repara a base de dados, só precisa de ser executado quando as vistas do calendário não funcionam corretamente. A segunda função, compacta a base de dados, pode ser executado uma vez por ano para limpar a mesma e a terceira função, deve ser executadaem função do número de actualizações do calendário.</p>
<br>
<h6>e. Importar ficheiro CSV</h6>
<p>Esta função pode ser usada para importar os dados para o calendário que foi exportado a partir de outros calendários (ex. MS Outlook). Outras instruções são dadas na página Importar CSV.</p>
<br>
<h6>f. Importar ficheiro iCal</h6>
<p>Esta função pode ser usada para importar eventos de arquivos iCal (extensão .ics) no Calendário LuxCal. Outras instruções são dadas na página Importar iCal. Apenas os eventos, que são compatíveis com o calendário LuxCal serão importados. Outros componentes, como: To-Do, Jounal, Free / Busy, fuso horário e despertador, serão ignorados.</p>
<br>
<h6>g. Exportar ficheiro iCal</h6>
<p>Esta função pode ser usada para exportar eventos LuxCal para ficheiros iCal (extensão .ics). Outras instruções são dadas na página de Exportação iCal.</p>
<br>
</li>
<li id="al"><h3>About LuxCal</h3>
<p>Produced by: <b>Roel Buining</b>&nbsp;&nbsp;&nbsp;&nbsp;Website and forum: <b><a href="https://www.luxsoft.eu/" target="_blank">www.luxsoft.eu/</a></b></p>
<p>LuxCal is freeware and may be redistributed and/or modified under the terms of the <b><a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">GNU General Public License</a></b>.</p>
<br></li>
</ol>
</div>