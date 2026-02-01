<?php
/*
= LuxCal on-line user guide =

Traducido al español por Michel Trottier y su novia - Montreal, Canada.
Traducción corregida y actualizada por Pantricio - Murcia, España.

This file is part of the LuxCal Web Calendar.
*/

?>
<div style="margin:0 20px">
<div class="floatR">
<img src="lang/ug-layout.png" alt="LuxCal page layout"><br>
<span class="hired">a</span>: barra superior&nbsp;&nbsp;<span class="hired">b</span>: barra de navegación&nbsp;&nbsp;<span class="hired">c</span>: dia
</div>
<br>
<h3>Tabla de contenido</h3>
<ol>
<li><p><a href="#ov">Descripción general</a></p></li>
<li><p><a href="#li">Iniciar sesión (Entrar)</a></p></li>
<li><p><a href="#co">Opciones del calendario</a></p></li>
<li><p><a href="#cv">Vistas del calendario</a></p></li>
<li><p><a href="#ts">Buscar texto</a></p></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li><p><a href="#ae">Añadir/Editar/Borrar evento</a></p></li>
<?php } ?>
<li><p><a href="#lo">Cerrar sesión</a></p></li>
<?php if ($usr['privs'] > 3) { //if manager/administrator ?>
<li><p><a href="#ca">Administración del calendario</a></p></li>
<?php } ?>
<li><p><a href="#al">Acerca de LuxCal</a></p></li>
</ol>
</div>
<div class="clear">
<br>
<ol>
<li id="ov"><h3>Descripción general</h3>
<p>El calendario LuxCal se ejecuta en un servidor web y puede gestionarse y verse a través de un navegador web.</p>
<p>La barra superior muestra el título del calendario, la fecha, y el nombre del usuario actual. 
Justo debajo de la barra superior, la barra de navegación contiene varios menús desplegables y enlaces (para 
navegar, iniciar/cerrar sesión, para añadir un evento, etc). Los menús y enlaces que se muestran dependen de los permisos del usuario. Debajo de la barra de navegación se muestra la vista seleccionada del calendario.</p>
<br></li>
<li id="li"><h3>Iniciar sesión (Entrar)</h3>
<p>Al hacer clic en "Iniciar sesión" en la parte derecha de la barra de navegación aparecerá la pantalla de inicio de sesión. Introduzca su nombre de usuario o su correo electrónico, la contraseña que le mandó el administrador, y haga clic en "Iniciar sesión".</p> 
<p>Si activa la casilla "Recordarme" antes de hacer clic en "Iniciar sesión", las próximas veces que acceda al calendario iniciará sesión automáticamente (debe permitir el uso de cookies y no borrar la de LuxCal).</p> 
<p>Si olvidó su contraseña, haga clic en "Iniciar sesión", introduzca su nombre de usuario o dirección de correo electrónico, y a continuación haga clic en "Enviar una nueva contraseña". Recibirá una nueva contraseña por correo electrónico.</p>
<p>Puede cambiar su dirección de correo electrónico y contraseña haciendo clic sobre "Cambiar mis datos" en la pantalla de inicio de sesión.</p>
<p>Si todavía no está registrado y el administrador del calendario ha habilitado el auto-registro, podrá pulsar "Registrarse" en la página de inicio, de lo contrario solo el administrador podrá crearle una cuenta.</p>
<br></li>
<li id="co"><h3>Opciones del calendario</h3>
<p>Al hacer clic sobre el botón "Opciones" de la barra de navegación se abrirá el panel de opciones del calendario. En este panel podrá seleccionar lo siguiente:</p>
<ul style="margin:0 20px">
<li><p>La vista del calendario (anual, mensual, semanal, etc.).</p></li>
<li><p>Un filtro de eventos basado en su propietario. Pueden seleccionarse eventos de uno o varios propietarios.</p></li>
<li><p>Un filtro de eventos basado en su categoría. Pueden seleccionarse eventos de una o varias categorías.</p></li>
<li><p>El idioma del interfaz de usuario.</p></li>
</ul>
<p>Tras seleccionar las opciones que le interesen en el panel, debe pulsar nuevamente el botón "Opciones" de la barra de navegación para activarlas.</p> 
<p>Nota: Los filtros de eventos y la selección de idioma pueden ser habilitadas/deshabilitadas por el administrador del calendario.</p>
<br></li>
<li id="cv"><h3>Vistas del calendario</h3>
<p>En todas las vistas aparecerán más detalles del evento al pasar el cursor sobre su título. El fondo de los eventos privados será verde claro, y el borde de los eventos que se repiten (o son multi-día) será rojo. En la vista "Próximos" las URLs se convertirán automáticamente en hipervínculos.</p>
<p>En todas las vistas el día actual tendrá un recuadro azul, y si se ha seleccionado otra fecha en la barra de navegación, el día seleccionado tendrá un recuadro rojo en las vistas mensual y anual.</p>
<p>Los eventos de una categoría para la que el administrador ha activado la casilla de marcado mostrarán dicha casilla delante del título del evento. Pueden usarse, por ejemplo, para marcar los eventos como "completado". Si el usuario tiene los permisos necesarios podrá hacer clic sobre esta casilla para marcarlas o desamarcarlas.</p>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<p>Cuando se tienen los permisos necesarios:</p>
<ul style="margin:0 20px">
<li><p>En todas las vistas, hacer clic en un evento se abrirá la ventana del evento, desde la que podrá ver, editar o borrar el evento.</p></li>
<li><p>En las vistas anual y mensual puede añadir un nuevo evento haciendo clic en la parte superior de la celda del día (en la línea donde se muestra el día del mes).</p></li>
<li><p>En las vistas semanal y diaria puede añadir un nuevo evento pinchando y arrastrando sobre un determinado periodo de tiempo. Los campos de fecha y hora se rellenarán automáticamente con la información del intervalo de tiempo seleccionado.</p></li>
</ul>
<p>Para mover un evento haga clic sobre su título, y modifique su fecha y hora desde la ventana de edición. No se pueden pinchar y arrastrar eventos a nuevas fechas u horas.</p>
<?php } ?>
<br></li>
<li id="ts"><h3>Buscar texto</h3>
<p>Pulse el triángulo de la parte derecha de la barra de navegación para abrir la página de búsqueda. En dicha página encontrará instrucciones detalladas sobre el funcionamiento de la búsqueda.</p>
<br></li>
<?php if ($usr['privs'] > 1) { //if post rights ?>
<li id="ae"><h3>Añadir/Editar/Borrar evento</h3>
<p>Los eventos se pueden añadir, editar, y borrar desde la ventana del evento, la cual puede abrirse de varias formas como se explicará a continuación.</p>
<br><h6>a. Añadir evento</h6>
<p>Para añadir un evento puede abrirse la ventana de eventos de las siguientes formas:</p>
<ul style="margin:0 20px">
<li><p>Haciendo clic en el botón "Añadir Evento" en la barra de navegación.</p></li>
<li><p>Haciendo clic en la parte superior de la celda (la línea donde se muestra el día del mes) en la vista mensual o anual.</p></li>
<li><p>Pinchando y arrastrando sobre un determinado periodo de tiempo en las vistas semanal y diaria.</p></li>
</ul>
<p>Cualquiera de estos métodos abrirá la ventana del evento con un formulario para introducir su información. Algunos campos en el formulario estarán ya rellenos, en función de las forma utilizada para añadir el evento.</p>
<h6>Campos Título, Ubicación, Categoría, Descripción, y Privado</h6>
<p>Los campos ubicación, categoría, y descripción son opcionales. Al asignar una categoría el evento éste será coloreado del mismo color que tenga asignado esa categoría. La ubicación y descripción aparecerán al pasar el cursor sobre un evento. Las URLs serán convertidas automáticamente en hipervínculos en varias vistas así como en las notificaciones de correo electrónico.</p>
<p>Un evento privado solo podrá verlo usted, y nadie más.</p>
<h6>Campos de fecha, hora, y repetición</h6>
<p>La fecha final es opcional y puede usarse para crear eventos multi-día. Las fechas y horas pueden introducirse manualmente o mediante los botones de selección. Haga clic sobre el botón "Cambiar" para abrir una pantalla donde podrá marcar el evento como recurrente. El evento se repetirá desde su fecha inicial hasta la fecha de la casilla "hasta". Si la fecha "hasta" se deja vacía entonces el evento se repetirá indefinidamente, lo cual es particularmente útil para los cumpleaños.</p>
<h6>Campos de notificación por correo electrónico</h6>
<p>Puede enviar un recordatorio por correo electrónico a una o varias direcciones. El usuario podrá enviar un mensaje de correo "ahora" si activa la casilla correspondiente, y/o también podrá enviar un recordatorio con la antelación que indique en la casilla "días" antes del evento. Si la casilla "días" se deja en blanco no se enviará un recordatorio con anterioridad al comienzo del evento. Si en la casilla "días" se introduce "0" se enviará un recordatorio el mismo día de comienzo del evento. Para los eventos recurrentes se enviará un recordatorio por correo electrónico (con tantos días de anticipación como se indique) para cada ocurrencia del evento, y además el mismo día de comienzo del evento.</p>
<p>La lista de direcciones de correo electrónico puede contener direcciones de correo electrónico y/o el nombre (sin extensión) de un fichero predefinido con una lista de direcciones, todos separados por punto y coma. La lista predefinida debe ser un fichero con extensión ".txt" en el directorio "/reciplists", conteniendo una dirección de correo en cada línea. El nombre del fichero no puede contener el carácter "@".</p>
<p>Al terminar, pulse "Añadir".</p>
<br>
<h6>b. Editar/Borrar evento</h6>
<p>En todas las vistas del calendario puede hacer clic en un evento para abrir una ventana que contendrá los detalles del evento. Un usuario con los permisos necesarios podrá editar, duplicar, y borrar un evento.</p>
<p>Dependiendo de los permisos que le asigne el administrador, podrá ver los eventos, ver/editar/borrar sus propios eventos, o ver/editar/borrar todos los eventos, incluyendo los eventos de otros usuarios.</p>
<p>Para una descripción de los campos, consulte la descripción de "Añadir Evento" más arriba.</p>
<p>En la ventana de edición de un evento los botones inferiores permiten al usuario guardar un evento editado, guardar como nuevo un evento editado (para duplicar el evento en otra fecha, por ejemplo), y borrar el evento.</p>
<p>Si elimina un evento por error y todavía no ha cerrado la ventana de edición, puede pulsar "Añadir" para volver a crearlo.</p>
<p>Al borrar evento recurrente eliminará todas las ocurrencias del evento, no sólo la de una fecha específica.</p>
<?php } ?>
<br></li>
<li id="lo"><h3>Cerrar sesión</h3>
<p>Para salir, haga clic en "Cerrar sesión" en la barra de navegación.</p>
<br></li>
<?php if ($usr['privs'] == 9) { //administrator only ?>
<li id="ca"><h3>Administración del calendario</h3>
<p>- Las siguientes características requieren permisos de administrador -</p>
<p>Cuando un usuario inicia sesión con permisos de administrador aparecerá un menú desplegable llamado "Administración", en la parte derecha de la barra de navegación. A través de este menú podrá seleccionar las siguiente funciones de administración:</p>
<br>
<h6>a. Configuración</h6>
<p>Esta página muestra la configuración actual del calendario, y permite cambiarla. Todos los ajustes poseen una descripción que aparece al pasar el cursor sobre ellos.</p>
<br>
<h6>b. Categorías</h6>
<p>Agregar categorías de eventos con diferentes colores (aunque no es obligatorio) mejorará enormemente las vistas del calendario. Por ejemplo, puede crear categorías como "Vacaciones", "Cita", "Cumpleaños", "Importante", etc.</p>
<p>La página de categorías muestra una lista de todas las categorías, pudiendo añadir, editar, o borrar las que desee. La instalación inicial tiene una sola categoría denominada "no cat".</p>
<p>Cuando se agregan/editan eventos se muestran todas las categorías en una lista desplegable. El orden en que se muestran las categorías en la lista desplegable está determinado por el campo "Posición".</p>
<p>Al añadir/editar una categoría puede asignarse un valor al campo "Repetir", de manera que todos los eventos que se asignen a esta categoría se repetirán con la periodicidad indicada.<br>
Al desactivar la casilla "Público" no se mostrarán los eventos de esta categoría a los usuarios que no hayan iniciado sesión, ni tampoco se publicarán en las noticias RSS.</p>
<p>Pueden seleccionarse una o dos casillas de marcado, que se mostrarán delante del título del evento, pudiendo usarse por ejemplo para marcarlos como "aprobado" o "completado".</p>
<p>Los campos de color del texto y fondo definen los colores que se utilizarán para mostrar los eventos que pertenezcan a la categoría.</p>
<p>Al eliminar una categoría, ésta seguirá estando disponible para los eventos que pertenecían a ella.</p>
<br>
<h6>c. Usuarios</h6>
<p>Esta página se utiliza para ver, añadir, y editar las cuentas de usuario. Se pueden editar el nombre, correo, contraseña, permisos e idioma del usuario. Los permisos posibles son: ver calendario, publicar y editar eventos propios, publicar y editar todos los eventos, y funciones de administración.<br>
Es importante indicar una direccción de correo electrónico válida para que el usuario pueda recibir notificaciones y recordatorios.</p>
<p>A través de la página "Configuración" el administrador puede habilitar el auto-registro de usuarios, y seleccionar los permisos que tendrán los usuarios auto-registrados. Cuando se habilita el auto-registro los usuarios pueden registrarse por sí mismos en el calendario a través de su navegador.</p>
<p>A menos que el administrador del calendario le halla dado acceso de lectura al usuario "Public Access" (usuarios de acceso público), los usuarios deben iniciar sesión para poder ver los eventos (utilizando su nombre de usuario o correo electrónico, y contraseña).</p>
<p>Puede especificarse un idioma del interfaz por defecto para cada usuario. Si no se especifica ninguno se usará el idioma por defecto del calendario indicado en la página de "Configuración".</p>
<br>
<h6>d. Base de datos</h6>
<p>La página de base de datos permite al administrador ejecutar las siguientes funciones:</p>
<ul>
<li>Comprobar y arreglar la base de datos, para localizar y resolver inconsistencias en las tablas.</li>
<li>Compactar la base de datos, para liberar espacio sin utilizar y evitar sobrecargas. Esta función borrará definitivamente los eventos eliminados que tengan una antigüedad superior a 30 días.</li>
<li>Copia de seguridad de la base de datos, para crear archivos de respaldo que permitan recrear las tablas y su contenido.</li>
</ul>
<p>La primera función, "Comprobar y arreglar la base de datos", sólo necesita ser ejecutada cuando las vistas del calendario no funcionan adecuadamente. La segunda, "Compactar la base de datos", puede ejecutarse anualmente para limpiar la base de datos. La tercera función, "Copia de seguridad de la base de datos", debería ejecutarse con más frecuencia, dependiendo del número de eventos que se añadan/editen.</p>
<br>
<h6>e. Importación de archivos CSV</h6>
<p>Esta función puede utilizarse para importar al calendario LuxCal los datos de eventos que han sido exportados de otros calendarios (por ejemplo, MS Outlook). Puede consultar las instrucciones en la página Importar CSV.</p>
<br>
<h6>f. Importación de archivos iCal</h6>
<p>Esta función se utiliza para importar eventos mediante archivos iCal (extensión .ics) al calendario LuxCal. Hallará más instrucciones en la página de importación. Sólo se importarán eventos compatibles con el calendario LuxCal. Otros elementos como Tareas, Diario, Ocupado/Libre, Zona horaria y Alarmas, serán ignorados.</p>
<br>
<h6>g. Exportación de archivos iCal</h6>
<p>Esta función se utiliza para exportar eventos del calendario LuxCal mediante archivos iCal (extensión .ics) 
Hallará más instrucciones en la página de exportación.</p>
<br></li>
<?php } ?>
<li id="al"><h3>Acerca de LuxCal</h3>
<p>Producido por: <b>Roel Buining</b>&nbsp;&nbsp;&nbsp;&nbsp;Página web y foro: <b><a href="https://www.luxsoft.eu/" target="_blank">www.luxsoft.eu/</a></b></p>
<p>LuxCal es freeware y puede ser redistribuido y/o modificado bajo los términos de la <b><a href="https://www.gnu.org/licenses/gpl-3.0.en.html" target="_blank">Licencia Pública General GNU</a></b>.</p>
<br></li>
</ol>
</div>