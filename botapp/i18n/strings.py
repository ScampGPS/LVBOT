"""Translation strings for all user-facing messages.

All strings are organized by category for easy maintenance.
Keys use dot notation for organization (e.g., 'menu.reserve_court').
"""

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
        "nav.cancel": "Cancelar",

        # Booking type selection
        "booking.reserve_within_48h": "🏃‍♂️ Reservar dentro de 48h",
        "booking.reserve_after_48h": "📅 Reservar después de 48h",
        "booking.test_queue": "🧪 TEST: Reserva en Cola",

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
        "profile.edit_profile": "✏️ Editar Perfil",
        "profile.view_profile": "👤 Ver Perfil",

        # Calendar buttons
        "calendar.add_google": "📅 Agregar a Google Calendar",
        "calendar.add_outlook": "📅 Agregar a Outlook",
        "calendar.add_apple": "📅 Agregar a Apple Calendar",

        # Reservation management
        "reservation.cancel": "❌ Cancelar Reserva",
        "reservation.modify": "✏️ Modificar Reserva",
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

        # Welcome/Start messages
        "welcome.title": "¡Bienvenido al Bot de Reservas de Tenis!",
        "welcome.message": "Puedes reservar canchas, ver tus reservas y gestionar tu perfil.",

        # Language selection
        "lang.select": "Selecciona tu idioma / Select your language",
        "lang.current": "Idioma actual: {language}",
        "lang.changed": "✅ Idioma cambiado a {language}",

        # Admin Panel
        "admin.title": "👮 **Panel de Admin**",
        "admin.access_denied": "🔐 **Acceso Denegado**\n\nNo estás autorizado para acceder al Panel de Admin.\n\nLos privilegios de administrador están restringidos solo a personal autorizado. Si crees que esto es un error, por favor contacta al administrador del sistema.",
        "admin.welcome": "🔧 **Panel de Gestión del Sistema**\n\nBienvenido a la interfaz de administración de LVBot. Usa las opciones de abajo para gestionar usuarios, monitorear el rendimiento del sistema y configurar ajustes del bot.\n\n⚠️ **Aviso**: Todas las acciones de administrador son registradas por seguridad.",
        "admin.test_mode_enabled": "🧪 Test mode habilitado!\n\nLas reservas futuras en cola omitirán la ventana de 48 horas y se ejecutarán después del retraso configurado.",
        "admin.test_mode_disabled": "🛑 Test mode deshabilitado.\n\nLas reservas en cola ahora respetarán la ventana de 48 horas y la programación normal.",
        "admin.users_list": "👥 **Seleccionar Usuario**\n\nElige un usuario para ver sus reservas:",
        "admin.no_users": "👥 **Lista de Usuarios**\n\nNo se encontraron usuarios en el sistema.",
        "admin.all_reservations": "📊 **Todas las Reservas**",
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
        "nav.cancel": "Cancel",

        # Booking type selection
        "booking.reserve_within_48h": "🏃‍♂️ Reserve within 48h",
        "booking.reserve_after_48h": "📅 Reserve after 48h",
        "booking.test_queue": "🧪 TEST: Queue Booking",

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
        "profile.edit_profile": "✏️ Edit Profile",
        "profile.view_profile": "👤 View Profile",

        # Calendar buttons
        "calendar.add_google": "📅 Add to Google Calendar",
        "calendar.add_outlook": "📅 Add to Outlook",
        "calendar.add_apple": "📅 Add to Apple Calendar",

        # Reservation management
        "reservation.cancel": "❌ Cancel Reservation",
        "reservation.modify": "✏️ Modify Reservation",
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

        # Welcome/Start messages
        "welcome.title": "Welcome to the Tennis Booking Bot!",
        "welcome.message": "You can reserve courts, view your reservations, and manage your profile.",

        # Language selection
        "lang.select": "Select your language / Selecciona tu idioma",
        "lang.current": "Current language: {language}",
        "lang.changed": "✅ Language changed to {language}",

        # Admin Panel
        "admin.title": "👮 **Admin Panel**",
        "admin.access_denied": "🔐 **Access Denied**\n\nYou are not authorized to access the Admin Panel.\n\nAdmin privileges are restricted to authorized personnel only. If you believe this is an error, please contact the system administrator.",
        "admin.welcome": "🔧 **System Management Dashboard**\n\nWelcome to the LVBot administration interface. Use the options below to manage users, monitor system performance, and configure bot settings.\n\n⚠️ **Notice**: All admin actions are logged for security purposes.",
        "admin.test_mode_enabled": "🧪 Test mode enabled!\n\nFuture queue bookings will bypass the 48-hour gate and execute after the configured delay.",
        "admin.test_mode_disabled": "🛑 Test mode disabled.\n\nQueued reservations will now respect the 48-hour window and normal scheduling.",
        "admin.users_list": "👥 **Select User**\n\nChoose a user to view their reservations:",
        "admin.no_users": "👥 **Users List**\n\nNo users found in the system.",
        "admin.all_reservations": "📊 **All Reservations**",
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
    all_keys = set()
    for lang_strings in STRINGS.values():
        all_keys.update(lang_strings.keys())
    return all_keys


def validate_translations() -> None:
    """Validate that all languages have the same keys."""
    all_keys = get_all_keys()
    for lang, lang_strings in STRINGS.items():
        missing = all_keys - set(lang_strings.keys())
        if missing:
            raise ValueError(f"Language '{lang}' is missing keys: {missing}")


# Validate on import
validate_translations()
