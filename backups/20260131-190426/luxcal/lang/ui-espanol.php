<?php
/*
= LuxCal user interface language file =
Traducido al español por Michel Trottier y su novia - Montreal, Canada.
Traducción corregida y actualizada por Pantricio - Murcia, España.
Traducción corregida y actualizada por Eutimio - Barcelona, España

This file is part of the LuxCal Web Calendar.
*/

//LuxCal ui language
$isocode = "es";

/* -- Titles on the Header of the Calendar -- */

$months = array("Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre");
$months_m = array("Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic");
$wkDays = array("Domingo","Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo");
$wkDays_l = array("Dom","Lun","Mar","Mié","Jue","Vie","Sáb","Dom");
$wkDays_m = array("Do","Lu","Ma","Mi","Ju","Vi","Sá","Do");
$wkDays_s = array("D","L","M","X","J","V","S","D");
$dhm = array("D","H","M"); //Days, Hours, Minutes


/* -- User Interface texts -- */

$xx = array(

//general
"submit" => "Enviar",
"log_in" => "Iniciar sesión",
"log_out" => "Cerrar sesión",
"portrait" => "Retrato",
"landscape" => "Paisaje",
"none" => "Ninguno.",
"all_day" => "Todo el día",
"back" => "Volver",
"restart" => "Reiniciar",
"by" => "por",
"of" => "de",
"max" => "max.",
"options" => "Opciones",
"done" => "Hecho",
"at_time" => "@", //date and time separator (e.g. 30-01-2019 @ 10:45)
"from" => "Desde", //e.g. from 9:30
"until" => "Hasta", //e.g. until 15:30
"to" => "A", //e.g. to 17-02-2020
"birthdays_in" => "Cumpleaños en",
"open_calendar" => "Abrir el calendario",
"no_way" => "No estás autorizado para realizar esta acción.",

//index.php
"title_log_in" => "Iniciar sesión",
"title_profile" => "Perfil del usuario",
"title_upcoming" => "Próximos eventos", 
"title_event" => "Evento",
"title_check_event" => "Marcar evento",
"title_dmarking" => "Marcado del día",
"title_search" => "Buscar texto",
"title_contact" => "Formulario de contacto",
"title_thumbnails" => "Imágenes en miniatura",
"title_user_guide" => "Guía del usuario de LuxCal",
"title_settings" => "Configurar el calendario", 
"title_edit_cats" => "Modificar categorías",
"title_edit_users" => "Modificar usuarios",
"title_edit_groups" => "Editar grupos de usuarios",
"title_edit_text" => "Editar texto de información",
"title_manage_db" => "Gestionar la base de datos",
"title_clean_up" => "Funciones generales de limpieza",
"title_changes" => "Eventos añadidos / modificados / suprimidos",
"title_usr_import" => "Importación Usuarios - CSV format",
"title_usr_export" => "Exportación Usuarios - CSV format",
"title_csv_import" => "Importación de archivos CSV",
"title_ics_import" => "Importación de archivos iCal",
"title_ics_export" => "Exportación de archivos iCal",
"title_msg_log" => "Notification Message Log",
"title_ui_styling" => "Diseño de la interfaz de usuario",
"title_bd_calendar" => "Calendario de cumpleaños",

//header.php
"hdr_button_back" => "Volver a la página principal",
"hdr_options_submit" => "Seleccione una opción y pulse 'Hecho'",
"hdr_options_panel" => "Panel de opciones",
"hdr_select_date" => "Ir a Fecha",
"hdr_calendar" => "Calendario",
"hdr_evt_copied_to" => "Evento copiado al calendario",
"hdr_view" => "Vista",
"hdr_lang" => "Idioma",
"hdr_all_cats" => "Todas las categorías",
"hdr_all_groups" => "Todos los Grupos",
"hdr_all_users" => "Todos los usuarios",
"hdr_go_to_view" => "Ir a ver",
"hdr_view_1" => "Año",
"hdr_view_2" => "Mes",
"hdr_view_3" => "Mes laboral",
"hdr_view_4" => "Semana",
"hdr_view_5" => "Semana laboral",
"hdr_view_6" => "Día",
"hdr_view_7" => "Próximos",
"hdr_view_8" => "Cambios",
"hdr_view_9" => "Matriz(C)",
"hdr_view_10" => "Matriz(U)",
"hdr_view_11" => "Gráfico de gantt",
"hdr_select_admin_functions" => "Seleccionar función de administración",
"hdr_admin" => "Administración",
"hdr_settings" => "Configuración",
"hdr_categories" => "Categorías",
"hdr_users" => "Usuarios",
"hdr_groups" => "Grupos de Usuarios",
"hdr_text_editor" => "Editor de texto",
"hdr_database" => "Base de datos",
"hdr_clean_up" => "Limpiar",
"hdr_import_usr" => "Importar Usuarios (CSV file)",
"hdr_export_usr" => "Exportar Usuarios (CSV file)",
"hdr_import_csv" => "Importar CSV",
"hdr_import_ics" => "Importar iCal",
"hdr_export_ics" => "Exportar iCal",
"hdr_msg_log" => "Message Log",
"hdr_styling" => "Estilo",
"hdr_back_to_cal" => "Volver a la vista calendario",
"hdr_button_print" => "Imprimir",
"hdr_print_page" => "Imprimir esta página",
"hdr_button_pdf" => "Archivo PDF - Eventos",
"hdr_button_pdf_bc" => "PDF File - Cumpleaños",
"hdr_dload_pdf" => "Descargar los próximos eventos",
"hdr_dload_pdf_bc" => "Descargar calendario de cumpleaños",
"hdr_button_contact" => "Contactar",
"hdr_contact" => "Contactar con el administrador",
"hdr_button_tnails" => "Miniaturas",
"hdr_tnails" => "Mostrar miniaturas",
"hdr_button_toap" => "Aprobar",
"hdr_toap_list" => "Eventos a aprobar",
"hdr_button_todo" => "Todo",
"hdr_todo_list" => "Lista de pendientes",
"hdr_button_upco" => "Próximo/a",
"hdr_upco_list" => "Próximos eventos",
"hdr_about_lc" => "Acerca de LuxCal",
"hdr_button_search" => "Buscar",
"hdr_search" => "Buscar",
"hdr_button_add" => "Añadir",
"hdr_add_event" => "Añadir Evento",
"hdr_button_help" => "Ayuda",
"hdr_user_guide" => "Guía de usuario",
"hdr_gen_guide" => "Guía general del usuario",
"hdr_cs_guide" => "Guía del usuario sensible al contexto",
"hdr_gen_help" => "Ayuda general",
"hdr_prev_help" => "Ayuda previa",
"hdr_open_menu" => "Abrir menú",
"hdr_side_menu" => "Menú lateral",
"hdr_dest_cals" => "Destino Calendario(s)",
"hdr_copy_evt" => "Copiar evento",
"hdr_tn_note" => "Copiado al portapapeles",
"hdr_today" => "hoy", //dtpicker.js
"hdr_clear" => "borrar", //dtpicker.js

//event.php
"evt_no_title" => "Sin título",
"evt_no_start_date" => "No hay fecha de inicio",
"evt_bad_date" => "Fecha errónea",
"evt_bad_rdate" => "Fecha final de repetición erronea",
"evt_no_start_time" => "No hay hora de inicio",
"evt_bad_time" => "Hora incorrecta",
"evt_end_before_start_time" => "Hora de finalización anterior a la hora de inicio",
"evt_end_before_start_date" => "Fecha de finalización anterior a la fecha de inicio",
"evt_until_before_start_date" => "Fecha final de repetición anterior a la fecha de inicio",
"evt_default_duration" => "Duración predeterminada del evento de $ 1 horas y $ 2 minutos",
"evt_fixed_duration" => "Duración fija del evento de $ 1 horas y $ 2 minutos",
"evt_approved" => "Evento aprobado",
"evt_apd_locked" => "Evento aprobado y bloqueado",
"evt_title" => "Título",
"evt_venue" => "Ubicación del evento",
"evt_address_button" => "Una dirección entre ! se convertirá en un botón",
"evt_list" => "Lista",
"evt_category" => "Categoría",
"evt_subcategory" => "Subcategoría",
"evt_description" => "Descripción",
"evt_attachments" => "Adjuntos",
"evt_attach_file" => "Adjuntar archivo",
"evt_click_to_open" => "Clic para abrir",
"evt_click_to_remove" => "Clic para eliminar",
"evt_no_pdf_img_vid" => "El adjunto debe ser pdf, imagen o video.",
"evt_error_file_upload" => "Error al subir el archivo",
"evt_upload_too_large" => "Archivo subido demasiado grande",
"evt_date_time" => "Fecha / hora",
"evt_date" => "Fecha",
"evt_private" => "Evento Privado",
"evt_start_date" => "Inicio",
"evt_end_date" => "Final",
"evt_select_date" => "Seleccione fecha",
"evt_select_time" => "Seleccione hora",
"evt_all_day" => "Todo el día",
"evt_no_time" => "Sin tiempo",
"evt_change" => "Cambiar",
"evt_set_repeat" => "Establecer repetición",
"evt_set" => "OK",
"evt_help" => "ayuda",
"evt_repeat_not_supported" => "La repetición solicitada no está soportada",
"evt_no_repeat" => "No repetir",
"evt_rolling" => "Repetitivo",
"evt_until_checked" => "hasta que lo revisen",
"evt_repeat_on" => "Repetir el",
"evt_until" => "hasta",
"evt_blank_no_end" => "en blanco: sin final",
"evt_each_month" => "cada mes",
"evt_interval2_1" => "primero",
"evt_interval2_2" => "segundo",
"evt_interval2_3" => "tercero",
"evt_interval2_4" => "cuarto",
"evt_interval2_5" => "último",
"evt_period1_1" => "días",
"evt_period1_2" => "semanas",
"evt_period1_3" => "meses",
"evt_period1_4" => "años",
"evt_notification" => "Notificar",
"evt_send_sms" => "SMS",
"evt_now_and_or" => "ahora y/o",
"evt_event_added" => "Evento añadido",
"evt_event_edited" => "Evento modificado",
"evt_event_deleted" => "Evento eliminado",
"evt_event_approved" => "Evento aprobado",
"evt_days_before_event" => "días antes del evento",
"evt_to" => "A",
"evt_not_help" => "Lista de direcciones de destinatarios separadas por punto y coma. La dirección de un destinatario puede ser un nombre de usuario, una dirección de correo electrónico, un número de teléfono móvil, un Telegram chat ID o, entre corchetes, el nombre (without type) de un .txt archivo con direcciones en el directorio 'reciplists ', con una dirección (un nombre de usuario, una dirección de correo electrónico, un número de teléfono móvil o un Telegram chat ID) por línea. <br> Longitud máxima del campo: 255 caracteres.",
"evt_recip_list_too_long" => "Lista de destinatarios demasiado larga.",
"evt_no_recip_list" => "Lista de destinatarios vacía",
"evt_not_in_past" => "Fecha de notificación pasada (anterior a hoy)",//
"evt_not_days_invalid" => "Fecha de notificación inválida",//
"evt_status" => "Estado",
"evt_descr_help" => "Los siguientes elementos se pueden usar en los campos de descripción ... <br> • Etiquetas HTML & lt; b & gt ;, & lt; i & gt ;, & lt; u & gt; y & lt; s & gt; para texto en negrita, cursiva, subrayado y tachado.",
"evt_descr_help_img" => "• (Miniaturas) de imágenes en el diguiente formato: 'nombre_imagen.ext'. Los archivos de miniaturas, con la extensión de archivo .gif, .jpg o .png, deben estar presentes en la carpeta 'thumbnails '. Si está habilitada, la página de miniaturas se puede usar para cargar archivos de miniaturas.",
"evt_descr_help_eml" => "• Enlaces Enviar a en el siguiente formato: 'dirección de correo electrónico' o'dirección de correo electrónico [nombre] ', donde'nombre' será el título del hipervínculo. P.ej. xxx@yyyy.zzz [Para información haga clic aquí].",
"evt_descr_help_url" => "• Los enlaces URL en el siguiente formato: 'url' o'url [nombre]', donde'nombre' será el título del enlace. If 'S:' se coloca delante de la URL, el enlace se abrirá en la misma página/pestaña; de lo contrario, el enlace se abrirá en una página/pestaña en blanco. P.ej. S:https://www.google.com [búsqueda].",
"evt_confirm_added" => "evento añadido",
"evt_confirm_saved" => "evento guardado",
"evt_confirm_deleted" => "evento eliminado",
"evt_add_close" => "Añadir y cerrar",
"evt_add" => "Añadir",
"evt_edit" => "Modificar",
"evt_save_close" => "Guardar y cerrar",
"evt_save" => "Guardar",
"evt_clone" => "Guardar como nuevo",
"evt_delete" => "Borrar",
"evt_close" => "Cerrar",
"evt_added" => "Añadido",
"evt_edited" => "Editado",
"evt_is_repeating" => "es un evento con repetición.",
"evt_is_multiday" => "es un evento multi-día.",
"evt_edit_series_or_occurrence" => "¿Quiere editar la serie completa o solo esta ocurrencia?",
"evt_edit_series" => "Editar la serie completa",
"evt_edit_occurrence" => "Editar solo esta ocurrencia",
"evt_select_from_list" => "Select recipients from list",
"evt_select_recips" => "Select Recipients",
"evt_recip_lists" => "Lists with Recipients",
"evt_regist_recips" => "Registered Recipients",
"evt_public_recips" => "Public Recipients",

//events - dmark specific
"mrk_text_and_color" => "Texto y color",
"mrk_is_repeating" => "es una marca repetida",
"mrk_is_multiday" => "es una marca de varios días",
"mrk_text" => "Texto",
"mrk_color" => "Color",
"mrk_background" => "Fondo",
"mrk_select_color" => "seleccionar color",
"mrk_start_date" => "Fecha de inicio",
"mrk_end_date" => "Fecha fin",
"mrk_dmark_added" => "Marcado de nuevo día",
"mrk_dmark_edited" => "Marcado de día cambiado",
"mrk_dmark_deleted" => "Marcado de día eliminado",
"mrk_dates" => "Fecha(s)",

//views
"vws_add_event" => "Añadir Evento",
"vws_edit_event" => "Editar Evento",
"vws_see_event" => "Ver detalles",
"vws_view_month" => "Ver mes",
"vws_view_week" => "Vista de la semana",
"vws_view_day" => "Ver día",
"vws_clic_for_full" => "para el calendario completo haga clic en mes",
"vws_view_full" => "Ver calendario completo",
"vws_prev_year" => "Año anterior",
"vws_next_year" => "Año siguiente",
"vws_prev_month" => "Mes anterior",
"vws_next_month" => "Mes siguiente",
"vws_forward" => "Adelante",
"vws_backward" => "Atras",
"vws_mark_day" => "marcar el día",
"vws_today" => "Hoy",
"vws_back_to_today" => "Volver al mes de hoy",
"vws_back_to_main_cal" => "Regresar al mes calendario principal",
"vws_week" => "Semana",
"vws_wk" => "sem",
"vws_time" => "Hora",
"vws_events" => "Eventos",
"vws_all_day" => "Todo el día",
"vws_earlier" => "Próximo",
"vws_later" => "Luego",
"vws_venue" => "Ubicación del evento",
"vws_address" => "Dirección",
"vws_events_for_next" => "Eventos para los próximos",
"vws_days" => "día(s)",
"vws_added" => "Añadido",
"vws_edited" => "Editado",
"vws_notify" => "Notificar",
"vws_none_due_in" => "No hay eventos pendientes en la próxima.",
"vws_evt_cats" => "Categorias de eventos",
"vws_cal_users" => "Usuarios del calendario",
"vws_no_users" => "No hay usuarios en el grupo/s seleccionado/s",
"vws_start" => "Inicio",
"vws_duration" => "Duración",
"vws_no_events_in_gc" => "No hay eventos en el período seleccionado.",
"vws_download" => "Descargar",
"vws_download_title" => "Descarga un archivo con estos eventos.",
"vws_send_mail" => "Enviar correo",

//changes.php
"chg_select_date" => "Seleccionar la fecha de inicio",
"chg_notify" => "Notificar",
"chg_days" => "Día(s)",
"chg_added" => "Añadido",
"chg_edited" => "Corregido",
"chg_deleted" => "Suprimido",
"chg_changed_on" => "Cambiado el",
"chg_no_changes" => "Sin cambios.",

//search.php
"sch_define_search" => "Definir búsqueda",
"sch_search_text" => "Texto buscado",
"sch_event_fields" => "Campos del evento",
"sch_all_fields" => "Todos los campos",
"sch_title" => "Título",
"sch_description" => "Descripción",
"sch_venue" => "Ubicación",
"sch_user_group" => "Grupo de usuario",
"sch_event_cat" => "Categoría del evento",
"sch_all_groups" => "Todos los grupos",
"sch_all_cats" => "Todas las categorías",
"sch_occurring_between" => "Ocurre entre",
"sch_select_start_date" => "Seleccionar fecha inicial",
"sch_select_end_date" => "Seleccionar fecha final",
"sch_search" => "Buscar",
"sch_invalid_search_text" => "El texto buscado está vacío o es demasiado corto",
"sch_bad_start_date" => "Fecha inicial erronea",
"sch_bad_end_date" => "Fecha final erronea",
"sch_no_results" => "No se han encontrado resultados",
"sch_new_search" => "Nueva búsqueda",
"sch_calendar" => "Ir al calendario",
"sch_extra_field1" => "Campo extra 1",
"sch_extra_field2" => "Campo extra 2",
"sch_sd_events" => "Eventos de un solo día",
"sch_md_events" => "Eventos de varios días",
"sch_rc_events" => "Eventos recurrentes",
"sch_instructions" =>
"<h3>Instrucciones de la búsqueda de texto</h3>
<p>Puede buscar eventos en la base de datos del calendario que contengan un texto específico.</p>
<br><p><b>Buscar texto</b>: Se buscará en los campos seleccionados (ver más adelante) de cada evento. 
La búsqueda no distingue entre mayúsculas y minúsculas.</p>
<p>Puede usar dos comodines:</p>
<ul>
<li>Un signo de interrogación (?) en el texto buscado sustituyen a cualquier carácter individual.<br>
P.ej.: 'p?t?' encuentra 'pata', 'pita', y 'poto'.</li>
<li>El signo * en el texto buscado sustituyen a cualquier combinación de carácteres.<br>
P.ej.: 'so*o' encuentra 'solp', 'sombrero', y 'sonajero'.</li>
</ul>
<br><p><b>Campos del evento</b>: Solo se buscará en los campos seleccionados.</p>
<br><p><b>Grupo de usuarios </b>: solo se buscarán los eventos del grupo de usuarios seleccionado.</p>
<br><p><b>Categoría del evento</b>: Solo se buscarán eventos de las categorías seleccionadas.</p>
<br><p><b>Ocurre entre</b>: Las fechas de inicio y final son opcionales. 
In case of a blank start / end date, the default number of days to search back and 
ahead will be $1 days and $2 days respectively.</p>
<br><p>Para evitar repeticiones del mismo evento, los resultados de la búsqueda se dividirán 
en eventos de un solo día, eventos de varios días y eventos recurrentes..</p>
<p>Los resultados se mostrarán en orden cronológico.</p>",

//thumbnails.php
"tns_man_tnails_instr" => "Instrucciones para administrar miniaturas",
"tns_help_general" => "Las siguientes imágenes se pueden usar en las vistas del calendario, insertando su nombre de archivo en el campo de descripción del evento o en uno de los campos adicionales. Un nombre de archivo de imagen se puede copiar en el portapapeles haciendo clic en la miniatura que se muestra a continuación; posteriormente, en la ventana Evento, el nombre de la imagen se puede insertar en uno de los campos escribiendo CTRL-V. Debajo de cada miniatura, encontrará: el nombre del archivo (sin el prefijo de ID de usuario), la fecha del archivo y entre corchetes la última fecha en que el calendario utiliza la miniatura.",
"tns_help_upload" => "Las miniaturas se pueden cargar desde su computadora local seleccionando el botón Examinar. Para seleccionar varios archivos, mantenga presionada la tecla CTRL o MAYÚS mientras selecciona (máx. 20 a la vez). Se aceptan los siguientes tipos de archivos: $1. Las miniaturas con un tamaño superior a $2 x $3 píxeles (W x H) cambiarán de tamaño automáticamente.",
"tns_help_delete" => "Las miniaturas con una cruz roja en la esquina superior izquierda se pueden eliminar seleccionando esta cruz. No se pueden eliminar las miniaturas sin la cruz roja, porque aún se usan después de $1. Precaución: ¡Las miniaturas eliminadas no se pueden recuperar!",
"tns_your_tnails" => "Tus miniaturas",
"tns_other_tnails" => "Otras miniaturas",
"tns_man_tnails" => "Gestionar miniaturas",
"tns_sort_by" => "Ordenar por",
"tns_sort_order" => "Orden de clasificación",
"tns_search_fname" => "Buscar nombre de archivo",
"tns_upload_tnails" => "Subir miniaturas",
"tns_name" => "nombre",
"tns_date" => "fecha",
"tns_ascending" => "ascendente",
"tns_descending" => "descendente",
"tns_not_used" => "no utilizado",
"tns_infinite" => "infinito",
"tns_del_tnail" => "Borrar miniatura",
"tns_tnail" => "Miniatura",
"tns_deleted" => "Borrado",
"tns_tn_uploaded" => "miniatura/s subida/s",
"tns_overwrite" => "permitir sobrescribir",
"tns_tn_exists" => "la miniatura ya existe, no se ha cargado",
"tns_upload_error" => "Error al Subir",
"tns_no_valid_img" => "no es una imagen valida",
"tns_file_too_large" => "archivo demasiado grande",
"tns_resized" => "redimensionado",
"tns_resize_error" => "error de cambio de tamaño",

//contact.php
"con_msg_to_admin" => "Mensaje al administrador",
"con_from" => "De",
"con_name" => "Nombre",
"con_email" => "Email",
"con_subject" => "Tema",
"con_message" => "Mensaje",
"con_send_msg" => "Enviar mensaje",
"con_fill_in_all_fields" => "Por favor rellena todos los campos",
"con_invalid_name" => "Nombre inválido",
"con_invalid_email" => "Email incorrecto",
"con_no_urls" => "No se permiten enlaces web en el mensaje.",
"con_mail_error" => "Problema de correo electrónico. El mensaje no se pudo enviar. Por favor, inténtelo de nuevo más tarde.",
"con_con_msg" => "Mensaje de contacto del calendario.",
"con_thank_you" => "Gracias por tu mensaje al calendario",
"con_get_reply" => "Recibirás una respuesta a tu mensaje lo antes posible.",
"con_date" => "Fecha",
"con_your_msg" => "Tu mensaje",
"con_your_cal_msg" => "Tu mensaje al calendario",
"con_has_been_sent" => "ha sido enviado al administrador del calendario",
"con_confirm_eml_sent" => "Un correo electrónico de confirmación ha sido enviado a",

//msglog.php
"msl_search" => "Search",
"msl_date" => "date",
"msl_text" => "text",
"msl_sent_msgs" => "Sent notification messages",
"msl_no_logs_found" => "No message logs found!",
"msl_errors" => "ERRORS OCCURRED! See luxcal log",

//alert.php
"alt_message#0" => "Su sesión expirará pronto!",
"alt_message#1" => "Sesión de PHP expirada",
"alt_message#2" => "Por favor reinicia el calendario",
"alt_message#3" => "SOLICITUD NO VÁLIDA",

//stand-alone sidebar (lcsbar.php)
"ssb_upco_events" => "Próximos Eventos",
"ssb_all_day" => "Todo el día",
"ssb_none" => "No hay eventos."
);
?>
