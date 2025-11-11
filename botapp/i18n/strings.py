"""Translation strings for all user-facing messages.

All strings are organized by category for easy maintenance.
Keys use dot notation for organization (e.g., 'menu.reserve_court').
"""
from tracking import t

from typing import Dict

# Translation dictionary: language code -> key -> translated string
STRINGS: Dict[str, Dict[str, str]] = {
    "es": {
        # Main menu buttons
        "menu.reserve_court": "🎾 Reservar Cancha",
        "menu.queued_reservations": "📋 Reservas en Cola",
        "menu.reservations": "📅 Reservas",
        "menu.profile": "👤 Perfil",
        "menu.admin_panel": "👮 Panel de Admin",
        "menu.admin_panel_pending": "👮 Panel de Admin ({count} pendientes)",

        # Navigation buttons
        "nav.back_to_menu": "🔙 Volver al Menú",
        "nav.back": "🔙 Atrás",
        "nav.back_to_year": "🔙 Volver a Año",
        "nav.back_to_month": "🔙 Volver a Mes",
        "nav.back_to_booking_type": "🔙 Volver al tipo de reserva",
        "nav.back_to_reservation": "⬅️ Volver a la reserva",
        "nav.back_to_reservations": "⬅️ Volver a Reservas",
        "nav.main_menu": "🏠 Menú Principal",
        "nav.cancel": "Cancelar",

        # Booking type selection
        "booking.reserve_within_48h": "🏃‍♂️ Reservar dentro de 48h",
        "booking.reserve_after_48h": "📅 Reservar después de 48h",
        "booking.test_queue": "🧪 TEST: Reserva en Cola",
        "booking.menu_title": "🎾 Reservar Cancha",
        "booking.menu_prompt": "Elige el tipo de reserva:",
        "booking.empty_title": "📅 **Mis Reservas**",
        "booking.empty_message": "No tienes reservas activas.",
        "booking.empty_cta": "Usa '🎾 Reservar Cancha' para crear una nueva reserva.",
        "booking.queue_empty_title": "📋 **Reservas en Cola**",
        "booking.queue_empty_message": "No tienes reservas en cola.",
        "booking.queue_empty_cta": "Usa '🎾 Reservar Cancha' → '📅 Reservar después de 48h' para agregar una reserva a la cola!",
        "booking.queue_title": "📋 **Reservas en Cola**",
        "booking.queue_count": "Tienes {count} reserva(s) en cola.",
        "booking.queue_prompt": "Haz clic en una reserva para gestionarla:",
        "queue.booking_title": "Reserva en cola",
        "queue.selected_date": "📅 Fecha seleccionada: {date}",
        "queue.select_time": "⏱️ Selecciona una hora para tu reserva en cola:",
        "queue.no_slots_title": "No hay horarios disponibles",
        "queue.no_slots_within_window": "Todos los horarios en esta fecha están dentro de la ventana de 48 horas.",
        "queue.no_slots_cta": "Por favor elige una fecha posterior para la reserva en cola.",
        "queue.confirmation_title": "Confirmación de reserva en cola",
        "queue.confirmation_notice": "Esta reserva se agregará a la cola y se enviará automáticamente cuando se abra la ventana de reservas.",
        "queue.confirmation_cta": "¿Confirmas que quieres agregar esta reserva a tu cola?",
        "queue.cancelled_title": "Reserva en cola cancelada",
        "queue.cancelled_body": "Tu solicitud de reserva se canceló. No se hicieron cambios en tu cola.",
        "queue.cancelled_cta": "Puedes iniciar una nueva reserva cuando quieras desde el menú principal.",
        "queue.select_court_prompt": "Selecciona tus canchas preferidas para la reserva:",
        "queue.date_label": "Fecha",
        "queue.time_label": "Hora",
        "queue.courts_label": "Canchas",
        "booking.checking_48h": "🔍 Revisando disponibilidad de canchas para las próximas 48 horas...",
        "booking.system_unavailable": "⚠️ **El sistema de reservas no está disponible temporalmente**\n\nEl sistema de reservas de canchas está experimentando problemas de conectividad. Normalmente se soluciona en pocos minutos.\n\nPor favor intenta de nuevo en unos momentos.",
        "booking.no_slots_48h": "😔 No hay canchas disponibles en las próximas 48 horas.\n\n💡 Intenta más tarde o usa 'Reservar después de 48h' para programar con más anticipación.",
        "booking.error_checking": "❌ Hubo un error al consultar la disponibilidad.\nPor favor intenta nuevamente más tarde.",
        "booking.future_title": "📅 Reservar Cancha (Reserva futura)",
        "booking.future_prompt": "Selecciona el año de tu reserva:",
        "booking.month_prompt": "Selecciona el mes de tu reserva:",
        "booking.date_prompt": "Selecciona la fecha de tu reserva:",
        "booking.checking_availability": "🔍 Revisando disponibilidad de canchas, por favor espera...",
        "booking.invalid_date_format": "❌ Formato de fecha inválido: {date}. Por favor intenta de nuevo.",
        "booking.select_time_title": "⏰ Reserva en cola - {date}",
        "booking.select_time_prompt": "Selecciona tu horario preferido:\n(se te notificará cuando abra la reserva)",
        "booking.no_times_for_date": "❌ No hay horarios disponibles el {date}.\nTodos los horarios están dentro de la ventana de 48 horas.\nPor favor selecciona otra fecha.",
        "booking.invalid_date_selection": "❌ Selección de fecha inválida. Por favor intenta de nuevo.",
        "booking.blocked_date_alert": "⚠️ Esta fecha está dentro de las próximas 48 horas. Redirigiendo a una reserva inmediata...",
        "booking.blocked_date_test": "🧪 Modo prueba: procediendo con reserva en cola para una fecha dentro de 48h",
        "booking.day_cycle_loading": "🔄 Cargando disponibilidad...",
        "booking.day_cycle_unavailable": "⚠️ **No se pudo cargar la disponibilidad de canchas**\n\nIntenta nuevamente en unos momentos.",
        "booking.error_processing_date": "❌ Error al procesar la selección de fecha.",
        "booking.use_immediate_prompt": "⚠️ Esta fecha está dentro de las próximas 48 horas.\n\nUsa 'Reservar dentro de 48h' para reservar de inmediato.",
        "booking.use_immediate_button": "🏃‍♂️ Usar reserva inmediata",
        "error.reservations_load": "❌ Error al cargar las reservas. Por favor intenta de nuevo.",
        "error.invalid_date": "❌ Fecha inválida. Por favor elige una fecha válida.",
        "error.invalid_time": "❌ Hora inválida. Por favor elige una hora disponible.",
        "error.invalid_court": "❌ Selección de cancha inválida. Por favor elige canchas válidas.",
        "error.no_availability": "😔 No hay canchas disponibles en este horario. Intenta con otra hora.",
        "error.booking_failed": "❌ La reserva falló. Intenta de nuevo más tarde.",
        "error.profile_incomplete": "❌ Completa tu perfil primero usando el comando /profile.",
        "error.outside_window": "⏰ Este horario está fuera de la ventana de 48 horas.",
        "error.already_booked": "🚫 Ya tienes una reserva en este horario.",
        "error.system_error": "❌ Ocurrió un error en el sistema. Contacta al administrador.",
        "error.details": "Detalles: {details}",

        # Common actions
        "action.yes": "Sí",
        "action.no": "No",
        "action.confirm": "Confirmar",
        "action.edit": "Editar",
        "action.delete": "Eliminar",
        "action.view": "Ver",

        # Notification headers
        "notif.booking_confirmed": "✅ *¡Reserva Confirmada!*",
        "notif.booking_failed": "❌ *Intento de Reserva Fallido*",
        "notif.duplicate_warning": "⚠️ *Reserva Duplicada*",
        "notif.queue_added": "✅ *¡Reserva Agregada a la Cola!*",
        "notif.queue_added_description": "Tu reserva ha sido agregada exitosamente a la cola. El bot intentará reservar automáticamente cuando se abra la ventana de reservas.",
        "notif.queue_view_hint": "Puedes ver tus reservas en cola en cualquier momento usando la opción 'Mis Reservas'.",
        "notif.queue_test_mode": "⚠️ MODO DE PRUEBA ACTIVO",
        "notif.queue_test_eta": "Esta reserva se ejecutará en {minutes} minutos!",

        # Notification fields
        "notif.court": "Cancha",
        "notif.time": "Hora",
        "notif.confirmation": "Confirmación",
        "notif.date": "📅 Fecha",
        "notif.courts": "🎾 Canchas",
        "notif.queue_id": "🤖 *ID de Cola:*",

        # Notification messages
        "notif.calendar_help": "Usa los botones de abajo para agregar a tu calendario o gestionar tu reserva.",
        "notif.duplicate_message": "Solo puedes tener una reserva por franja horaria. Por favor verifica tus reservas existentes o elige un horario diferente.",
        "notif.queue_processing": "⏳ Tu reserva será procesada automáticamente cuando se acerque la fecha.",
        "notif.queue_check_status": "Puedes verificar el estado en cualquier momento desde el menú principal.",

        # Profile fields
        "profile.name": "Nombre",
        "profile.phone": "Teléfono",
        "profile.email": "Correo",
        "profile.language": "Idioma",
        "profile.setup_title": "🧾 Configura tu perfil",
        "profile.setup_description": "Necesitamos algunos datos antes de poder reservar por ti.",
        "profile.setup_missing": "Completa estos campos:",
        "profile.setup_cta": "Usa los botones para actualizar tu perfil y regresa al menú cuando termines.",
        "profile.edit_profile": "✏️ Editar Perfil",
        "profile.view_profile": "👤 Ver Perfil",
        "profile.title": "Perfil de Usuario",
        "profile.court_preference": "Preferencia de Cancha",
        "profile.total_reservations": "Total de Reservas",
        "profile.telegram": "Telegram",
        "profile.not_set": "No configurado",
        "profile.vip_user": "⭐ *Usuario VIP* (Reserva prioritaria)",
        "profile.administrator": "👮 *Administrador*",
        "profile.premium_user": "⚡ *Usuario Premium (Hardcoded)*",
        "profile.edit_name": "✏️ Editar Nombre",
        "profile.edit_phone": "📱 Editar Teléfono",
        "profile.edit_email": "📧 Editar Correo",
        "profile.edit_language": "🌐 Cambiar Idioma",
        "profile.edit_courts": "🎾 Editar Preferencia de Canchas",
        "profile.edit_profile_title": "✏️ **Editar Perfil**",
        "profile.select_field": "Selecciona un campo para editar:",
        "profile.name_editing": "🧑‍💼 **Edición de Nombre**",
        "profile.choose_name_field": "Elige el campo de nombre que deseas editar:",
        "profile.edit_phone_title": "📱 **Editar Número de Teléfono**",
        "profile.edit_email_title": "📧 **Editar Correo Electrónico**",
        "profile.current": "Actual",
        "profile.use_keypad": "Usa el teclado a continuación para ingresar tu número de teléfono:",
        "profile.use_keyboard": "Usa el teclado a continuación:",
        "profile.phone_8_digits": "❌ El número debe tener 8 dígitos",
        "profile.phone_exactly_8": "❌ El número debe tener exactamente 8 dígitos",
        "profile.phone_updated": "✅ Número de teléfono actualizado a {phone}",
        "profile.name_updated_telegram": "✅ Nombre actualizado desde Telegram!",
        "profile.name_too_long": "❌ Nombre muy largo",
        "profile.first_name": "Nombre",
        "profile.last_name": "Apellido",
        "profile.edit_field": "**Editar {field}**",
        "profile.email_too_long": "❌ Correo muy largo",
        "profile.email_must_have_at": "❌ El correo debe contener @",
        "profile.confirm_email_title": "📧 **Confirmar Correo**",
        "profile.email_label": "Correo",
        "profile.is_correct": "¿Es correcto?",
        "profile.email_updated": "✅ Correo actualizado!",
        "profile.language_selection": "🌐 **Selección de Idioma**",
        "profile.current_language": "Idioma actual",
        "profile.select_language": "Selecciona tu idioma preferido:",
        "profile.court_preference_help": "Usa ⬆️⬇️ para reordenar, ❌ para eliminar, ➕ para agregar canchas.",
        "profile.court_order_matters": "El orden determina la prioridad de reserva.",

        # Calendar buttons
        "calendar.add_google": "📅 Agregar a Google Calendar",
        "calendar.add_outlook": "📆 Outlook/iCal",
        "calendar.add_apple": "📅 Agregar a Apple Calendar",

        # Reservation management
        "reservation.cancel": "❌ Cancelar Reserva",
        "reservation.modify": "✏️ Modificar Reserva",
        "reservation.cancel_modify": "🗑️ Cancelar/Modificar Reserva",
        "reservation.view_all": "Ver Todas las Reservas",

        # Months
        "month.january": "Enero",
        "month.february": "Febrero",
        "month.march": "Marzo",
        "month.april": "Abril",
        "month.may": "Mayo",
        "month.june": "Junio",
        "month.july": "Julio",
        "month.august": "Agosto",
        "month.september": "Septiembre",
        "month.october": "Octubre",
        "month.november": "Noviembre",
        "month.december": "Diciembre",

        # Days of week
        "day.monday": "Lunes",
        "day.tuesday": "Martes",
        "day.wednesday": "Miércoles",
        "day.thursday": "Jueves",
        "day.friday": "Viernes",
        "day.saturday": "Sábado",
        "day.sunday": "Domingo",
        "day.short.mon": "Lu",
        "day.short.tue": "Ma",
        "day.short.wed": "Mi",
        "day.short.thu": "Ju",
        "day.short.fri": "Vi",
        "day.short.sat": "Sá",
        "day.short.sun": "Do",

        # Time periods
        "time.am": "AM",
        "time.pm": "PM",

        # Court labels
        "court.label": "Cancha {number}",
        "court.all": "Todas las Canchas",

        # Status messages
        "status.processing": "⏳ Procesando...",
        "status.loading": "⏳ Cargando...",
        "status.success": "✅ Éxito",
        "status.error": "❌ Error",

        # Error messages
        "error.generic": "Ocurrió un error. Por favor intenta de nuevo.",
        "error.unauthorized": "No tienes permiso para esta acción.",
        "error.invalid_input": "Entrada inválida. Por favor intenta de nuevo.",
        "error.unknown_option": "Opción desconocida. Usa los botones del menú o /start para comenzar nuevamente.",

        # Welcome/Start messages
        "welcome.title": "¡Bienvenido al Bot de Reservas de Tenis!",
        "welcome.message": "Puedes reservar canchas, ver tus reservas y gestionar tu perfil.",

        # Language selection
        "lang.select": "Selecciona tu idioma / Select your language",
        "lang.current": "Idioma actual: {language}",
        "lang.changed": "✅ Idioma cambiado a {language}",

        # Admin Panel
        "admin.title": "👮 **Panel de Admin**",
        "admin.reservations_menu.title": "👮 **Reservas - Panel de Admin**",
        "admin.reservations_menu.prompt": "Selecciona qué reservas deseas ver:",
        "admin.access_denied": "🔐 **Acceso Denegado**\n\nNo estás autorizado para acceder al Panel de Admin.\n\nLos privilegios de administrador están restringidos solo a personal autorizado. Si crees que esto es un error, por favor contacta al administrador del sistema.",
        "admin.welcome": "🔧 **Panel de Gestión del Sistema**\n\nBienvenido a la interfaz de administración de LVBot. Usa las opciones de abajo para gestionar usuarios, monitorear el rendimiento del sistema y configurar ajustes del bot.\n\n⚠️ **Aviso**: Todas las acciones de administrador son registradas por seguridad.",
        "admin.test_mode_enabled": "🧪 Test mode habilitado!\n\nLas reservas futuras en cola omitirán la ventana de 48 horas y se ejecutarán después del retraso configurado.",
        "admin.test_mode_disabled": "🛑 Test mode deshabilitado.\n\nLas reservas en cola ahora respetarán la ventana de 48 horas y la programación normal.",
        "admin.users_list": "👥 **Seleccionar Usuario**\n\nElige un usuario para ver sus reservas:",
        "admin.view_by_user_button": "👥 Ver por usuario",
        "admin.no_users": "👥 **Lista de Usuarios**\n\nNo se encontraron usuarios en el sistema.",
        "admin.all_reservations": "📊 **Todas las Reservas**",
        "admin.view_all_reservations_button": "📊 Todas las reservas",
        "admin.no_reservations": "No se encontraron reservas activas en el sistema.",
        "admin.user_reservations": "📅 **Reservas de {user_name}**",
        "admin.no_user_reservations": "No se encontraron reservas activas.",
        "admin.error_loading_users": "❌ Error cargando lista de usuarios.",
        "admin.error_loading_reservations": "❌ Error cargando reservas.",
        "admin.back_to_admin": "⬅️ Volver al Admin",
    },

    "en": {
        # Main menu buttons
        "menu.reserve_court": "🎾 Reserve Court",
        "menu.queued_reservations": "📋 Queued Reservations",
        "menu.reservations": "📅 Reservations",
        "menu.profile": "👤 Profile",
        "menu.admin_panel": "👮 Admin Panel",
        "menu.admin_panel_pending": "👮 Admin Panel ({count} pending)",

        # Navigation buttons
        "nav.back_to_menu": "🔙 Back to Menu",
        "nav.back": "🔙 Back",
        "nav.back_to_year": "🔙 Back to Year",
        "nav.back_to_month": "🔙 Back to Month",
        "nav.back_to_booking_type": "🔙 Back to booking type",
        "nav.back_to_reservation": "⬅️ Back to reservation",
        "nav.back_to_reservations": "⬅️ Back to Reservations",
        "nav.main_menu": "🏠 Main Menu",
        "nav.cancel": "Cancel",

        # Booking type selection
        "booking.reserve_within_48h": "🏃‍♂️ Reserve within 48h",
        "booking.reserve_after_48h": "📅 Reserve after 48h",
        "booking.test_queue": "🧪 TEST: Queue Booking",
        "booking.menu_title": "🎾 Reserve Court",
        "booking.menu_prompt": "Choose booking type:",
        "booking.empty_title": "📅 **My Reservations**",
        "booking.empty_message": "You don't have any active reservations.",
        "booking.empty_cta": "Use '🎾 Reserve Court' to make a booking!",
        "booking.queue_empty_title": "📋 **Queued Reservations**",
        "booking.queue_empty_message": "You don't have any queued reservations.",
        "booking.queue_empty_cta": "Use '🎾 Reserve Court' → '📅 Reserve after 48h' to queue a booking!",
        "booking.queue_title": "📋 **Queued Reservations**",
        "booking.queue_count": "You have {count} queued reservation(s).",
        "booking.queue_prompt": "Click on a reservation to manage it:",
        "queue.booking_title": "Queue booking",
        "queue.selected_date": "📅 Selected date: {date}",
        "queue.select_time": "⏱️ Select a time for your queued reservation:",
        "queue.no_slots_title": "No time slots available",
        "queue.no_slots_within_window": "All time slots on this date are within the 48-hour window.",
        "queue.no_slots_cta": "Please choose a later date for queue booking.",
        "queue.confirmation_title": "Queue booking confirmation",
        "queue.confirmation_notice": "This reservation will be queued and automatically submitted when the booking window opens.",
        "queue.confirmation_cta": "Do you want to add this reservation to your queue?",
        "queue.cancelled_title": "Queue booking cancelled",
        "queue.cancelled_body": "Your reservation request was cancelled. Your queue was not modified.",
        "queue.cancelled_cta": "You can start a new booking anytime from the main menu.",
        "queue.select_court_prompt": "Select your preferred court(s) for the reservation:",
        "queue.date_label": "Date",
        "queue.time_label": "Time",
        "queue.courts_label": "Courts",
        "booking.checking_48h": "🔍 Checking court availability for the next 48 hours...",
        "booking.system_unavailable": "⚠️ **Court Availability System Temporarily Unavailable**\n\nThe booking system is currently experiencing connectivity issues. This usually resolves within a few minutes.\n\nPlease try again shortly.",
        "booking.no_slots_48h": "😔 No courts available in the next 48 hours.\n\n💡 Try checking again later or use 'Reserve after 48h' to schedule further in advance.",
        "booking.error_checking": "❌ Sorry, there was an error checking availability.\nPlease try again later.",
        "booking.future_title": "📅 Reserve Court (Future Booking)",
        "booking.future_prompt": "Select the year for your reservation:",
        "booking.month_prompt": "Select the month for your reservation:",
        "booking.date_prompt": "Select the date for your reservation:",
        "booking.checking_availability": "🔍 Checking court availability, please wait...",
        "booking.invalid_date_format": "❌ Invalid date format received: {date}. Please try again.",
        "booking.select_time_title": "⏰ Queue Booking - {date}",
        "booking.select_time_prompt": "Select your preferred time:\n(You'll be notified when booking opens)",
        "booking.no_times_for_date": "❌ No available times on {date}.\nAll time slots are within the 48-hour booking window.\nPlease select a different date.",
        "booking.invalid_date_selection": "❌ Invalid date selection. Please try again.",
        "booking.blocked_date_alert": "⚠️ This date is within 48 hours. Redirecting to immediate booking...",
        "booking.blocked_date_test": "🧪 Test mode: proceeding with queue booking for a within-48h date",
        "booking.day_cycle_loading": "🔄 Loading availability...",
        "booking.day_cycle_unavailable": "⚠️ **Unable to load court availability**\n\nPlease try again in a moment.",
        "booking.error_processing_date": "❌ Error processing date selection.",
        "booking.use_immediate_prompt": "⚠️ This date is within the next 48 hours.\n\nPlease use 'Reserve within 48h' for immediate booking.",
        "booking.use_immediate_button": "🏃‍♂️ Use immediate booking",
        "error.reservations_load": "❌ Error loading reservations. Please try again.",
        "error.invalid_date": "❌ Invalid date selected. Please choose a valid date.",
        "error.invalid_time": "❌ Invalid time selected. Please choose from the available times.",
        "error.invalid_court": "❌ Invalid court selection. Please choose valid courts.",
        "error.no_availability": "😔 No courts available at this time. Please try another time slot.",
        "error.booking_failed": "❌ Booking failed. Please try again later.",
        "error.profile_incomplete": "❌ Please complete your profile first using the /profile command.",
        "error.outside_window": "⏰ This time slot is outside the 48-hour booking window.",
        "error.already_booked": "🚫 You already have a reservation at this time.",
        "error.system_error": "❌ A system error occurred. Please contact an administrator.",
        "error.details": "Details: {details}",

        # Common actions
        "action.yes": "Yes",
        "action.no": "No",
        "action.confirm": "Confirm",
        "action.edit": "Edit",
        "action.delete": "Delete",
        "action.view": "View",

        # Notification headers
        "notif.booking_confirmed": "✅ *Booking Confirmed!*",
        "notif.booking_failed": "❌ *Booking Attempt Failed*",
        "notif.duplicate_warning": "⚠️ *Duplicate Reservation*",
        "notif.queue_added": "✅ *Reservation Added to Queue!*",
        "notif.queue_added_description": "Your reservation has been added to the queue. The bot will automatically attempt to book the court when the window opens.",
        "notif.queue_view_hint": "You can view your queued reservations anytime from the My Reservations option.",
        "notif.queue_test_mode": "⚠️ TEST MODE ACTIVE",
        "notif.queue_test_eta": "This reservation will be executed in {minutes} minutes!",

        # Notification fields
        "notif.court": "Court",
        "notif.time": "Time",
        "notif.confirmation": "Confirmation",
        "notif.date": "📅 Date",
        "notif.courts": "🎾 Courts",
        "notif.queue_id": "🤖 *Queue ID:*",

        # Notification messages
        "notif.calendar_help": "Use the buttons below to add to your calendar or manage your reservation.",
        "notif.duplicate_message": "You can only have one reservation per time slot. Please check your existing reservations or choose a different time.",
        "notif.queue_processing": "⏳ Your reservation will be automatically processed as the date approaches.",
        "notif.queue_check_status": "You can check the status at any time from the main menu.",

        # Profile fields
        "profile.name": "Name",
        "profile.phone": "Phone",
        "profile.email": "Email",
        "profile.language": "Language",
        "profile.setup_title": "🧾 Set Up Your Profile",
        "profile.setup_description": "We need a few details before we can book courts for you.",
        "profile.setup_missing": "Please complete these fields:",
        "profile.setup_cta": "Use the buttons below to update your profile, then return to the main menu when you're ready.",
        "profile.edit_profile": "✏️ Edit Profile",
        "profile.view_profile": "👤 View Profile",
        "profile.title": "User Profile",
        "profile.court_preference": "Court Preference",
        "profile.total_reservations": "Total Reservations",
        "profile.telegram": "Telegram",
        "profile.not_set": "Not set",
        "profile.edit_name": "✏️ Edit Name",
        "profile.edit_phone": "📱 Edit Phone",
        "profile.edit_email": "📧 Edit Email",
        "profile.edit_language": "🌐 Change Language",
        "profile.edit_courts": "🎾 Edit Court Preference",
        "profile.edit_profile_title": "✏️ **Edit Profile**",
        "profile.select_field": "Select a field to edit:",
        "profile.name_editing": "🧑‍💼 **Name Editing**",
        "profile.choose_name_field": "Choose the name field you want to edit:",
        "profile.edit_phone_title": "📱 **Edit Phone Number**",
        "profile.edit_email_title": "📧 **Edit Email**",
        "profile.current": "Current",
        "profile.use_keypad": "Use the keypad below to enter your phone number:",
        "profile.use_keyboard": "Use the keyboard below:",
        "profile.phone_8_digits": "❌ Phone number must be 8 digits",
        "profile.phone_exactly_8": "❌ Phone number must be exactly 8 digits",
        "profile.phone_updated": "✅ Phone number updated to {phone}",
        "profile.name_updated_telegram": "✅ Name updated from Telegram!",
        "profile.name_too_long": "❌ Name too long",
        "profile.first_name": "First Name",
        "profile.last_name": "Last Name",
        "profile.edit_field": "**Edit {field}**",
        "profile.email_too_long": "❌ Email too long",
        "profile.email_must_have_at": "❌ Email must contain @",
        "profile.confirm_email_title": "📧 **Confirm Email**",
        "profile.email_label": "Email",
        "profile.is_correct": "Is this correct?",
        "profile.email_updated": "✅ Email updated!",
        "profile.language_selection": "🌐 **Language Selection**",
        "profile.current_language": "Current language",
        "profile.select_language": "Select your preferred language:",
        "profile.court_preference_help": "Use ⬆️⬇️ to reorder, ❌ to remove, ➕ to add courts.",
        "profile.court_order_matters": "The order determines booking priority.",
        "profile.vip_user": "⭐ *VIP User* (Priority booking)",
        "profile.administrator": "👮 *Administrator*",
        "profile.premium_user": "⚡ *Premium User (Hardcoded)*",
        "profile.edit_phone": "📱 Edit Phone",
        "profile.edit_email": "📧 Edit Email",
        "profile.edit_language": "🌐 Change Language",
        "profile.edit_courts": "🎾 Edit Court Preference",

        # Calendar buttons
        "calendar.add_google": "📅 Google Calendar",
        "calendar.add_outlook": "📆 Outlook/iCal",
        "calendar.add_apple": "📅 Apple Calendar",

        # Reservation management
        "reservation.cancel": "❌ Cancel Reservation",
        "reservation.modify": "✏️ Modify Reservation",
        "reservation.cancel_modify": "🗑️ Cancel/Modify Reservation",
        "reservation.view_all": "View All Reservations",

        # Months
        "month.january": "January",
        "month.february": "February",
        "month.march": "March",
        "month.april": "April",
        "month.may": "May",
        "month.june": "June",
        "month.july": "July",
        "month.august": "August",
        "month.september": "September",
        "month.october": "October",
        "month.november": "November",
        "month.december": "December",

        # Days of week
        "day.monday": "Monday",
        "day.tuesday": "Tuesday",
        "day.wednesday": "Wednesday",
        "day.thursday": "Thursday",
        "day.friday": "Friday",
        "day.saturday": "Saturday",
        "day.sunday": "Sunday",
        "day.short.mon": "Mon",
        "day.short.tue": "Tue",
        "day.short.wed": "Wed",
        "day.short.thu": "Thu",
        "day.short.fri": "Fri",
        "day.short.sat": "Sat",
        "day.short.sun": "Sun",

        # Time periods
        "time.am": "AM",
        "time.pm": "PM",

        # Court labels
        "court.label": "Court {number}",
        "court.all": "All Courts",

        # Status messages
        "status.processing": "⏳ Processing...",
        "status.loading": "⏳ Loading...",
        "status.success": "✅ Success",
        "status.error": "❌ Error",

        # Error messages
        "error.generic": "An error occurred. Please try again.",
        "error.unauthorized": "You don't have permission for this action.",
        "error.invalid_input": "Invalid input. Please try again.",
        "error.unknown_option": "Unknown option. Please use the menu buttons or /start to begin again.",

        # Welcome/Start messages
        "welcome.title": "Welcome to the Tennis Booking Bot!",
        "welcome.message": "You can reserve courts, view your reservations, and manage your profile.",

        # Language selection
        "lang.select": "Select your language / Selecciona tu idioma",
        "lang.current": "Current language: {language}",
        "lang.changed": "✅ Language changed to {language}",

        # Admin Panel
        "admin.title": "👮 **Admin Panel**",
        "admin.reservations_menu.title": "👮 **Admin Reservations Menu**",
        "admin.reservations_menu.prompt": "Select which reservations to view:",
        "admin.access_denied": "🔐 **Access Denied**\n\nYou are not authorized to access the Admin Panel.\n\nAdmin privileges are restricted to authorized personnel only. If you believe this is an error, please contact the system administrator.",
        "admin.welcome": "🔧 **System Management Dashboard**\n\nWelcome to the LVBot administration interface. Use the options below to manage users, monitor system performance, and configure bot settings.\n\n⚠️ **Notice**: All admin actions are logged for security purposes.",
        "admin.test_mode_enabled": "🧪 Test mode enabled!\n\nFuture queue bookings will bypass the 48-hour gate and execute after the configured delay.",
        "admin.test_mode_disabled": "🛑 Test mode disabled.\n\nQueued reservations will now respect the 48-hour window and normal scheduling.",
        "admin.users_list": "👥 **Select User**\n\nChoose a user to view their reservations:",
        "admin.view_by_user_button": "👥 View by User",
        "admin.no_users": "👥 **Users List**\n\nNo users found in the system.",
        "admin.all_reservations": "📊 **All Reservations**",
        "admin.view_all_reservations_button": "📊 All reservations",
        "admin.no_reservations": "No active reservations found in the system.",
        "admin.user_reservations": "📅 **Reservations for {user_name}**",
        "admin.no_user_reservations": "No active reservations found.",
        "admin.error_loading_users": "❌ Error loading users list.",
        "admin.error_loading_reservations": "❌ Error loading reservations.",
        "admin.back_to_admin": "⬅️ Back to Admin",
    },
}


def get_all_keys() -> set:
    """Get all translation keys across all languages for validation."""
    t('botapp.i18n.strings.get_all_keys')
    all_keys = set()
    for lang_strings in STRINGS.values():
        all_keys.update(lang_strings.keys())
    return all_keys


def validate_translations() -> None:
    """Validate that all languages have the same keys."""
    t('botapp.i18n.strings.validate_translations')
    all_keys = get_all_keys()
    for lang, lang_strings in STRINGS.items():
        missing = all_keys - set(lang_strings.keys())
        if missing:
            raise ValueError(f"Language '{lang}' is missing keys: {missing}")


# Validate on import
validate_translations()
