"""
Constants Module - Centralized configuration values
===================================================

PURPOSE: Single source of truth for all constants used across the codebase
PATTERN: Modular constants organized by category
SCOPE: Application-wide configuration values

This module eliminates hardcoded values and provides easy configuration.
"""
from utils.tracking import t

# Browser and Frame Constants
SCHEDULING_IFRAME_URL_PATTERN = 'squarespacescheduling'
BOOKING_URL = "https://www.clublavilla.com/haz-tu-reserva"
ACUITY_EMBED_URL = "https://clublavilla.as.me/schedule"  # Base URL for direct court access
DEFAULT_TIMEOUT_SECONDS = 3.0
DEFAULT_WAIT_INTERVAL = 0.5
FAST_POLL_INTERVAL = 0.05  # 50ms for tight polling loops

# Court Configuration
AVAILABLE_COURT_INDICES = [0, 1, 2]  # 0-based indices
AVAILABLE_COURT_NUMBERS = [1, 2, 3]  # Human-readable numbers
DEFAULT_COURT_PREFERENCES = [1, 3, 2]  # Default priority order

def court_index_to_number(index: int) -> int:
    """Convert 0-based court index to human-readable court number"""
    t('infrastructure.constants.court_index_to_number')
    return index + 1

def court_number_to_index(number: int) -> int:
    """Convert human-readable court number to 0-based index"""
    t('infrastructure.constants.court_number_to_index')
    return number - 1

# Time Slot Selectors (Updated for current website structure)
TIME_SLOT_SELECTORS = [
    'button.time-selection',  # Primary selector for current Acuity site
    'button[data-time]',
    'button:has-text("AM"), button:has-text("PM")',  # Legacy - site now uses 24hr format
    'button:has-text(":")',
    '.time-slot:not(.disabled)',
    'td button:has-text(":")',
    '.appointment-time button',
    '[class*="time"] button',
    'button[class*="time"]',
    '.sqs-block-button-element',
    '[data-testid*="time"]',
    '.schedule-time button',
    'button'  # Fallback to all buttons
]

# Primary time button selector for the current website
TIME_BUTTON_SELECTOR = 'button.time-selection'

# Court Configuration with IDs
COURT_CONFIG = {
    1: {
        "appointment_id": "15970897",
        "calendar_id": "4282490",
        "direct_url": "https://clublavilla.as.me/?appointmentType=15970897",
        "full_url": "https://clublavilla.as.me/schedule/7d558012/appointment/15970897/calendar/4282490"
    },
    2: {
        "appointment_id": "16021953", 
        "calendar_id": "4291312",
        "direct_url": "https://clublavilla.as.me/?appointmentType=16021953",
        "full_url": "https://clublavilla.as.me/schedule/7d558012/appointment/16021953/calendar/4291312"
    },
    3: {
        "appointment_id": "16120442",
        "calendar_id": "4307254",
        "direct_url": "https://clublavilla.as.me/?appointmentType=16120442",
        "full_url": "https://clublavilla.as.me/schedule/7d558012/appointment/16120442/calendar/4307254"
    }
}

# No Availability Patterns
NO_AVAILABILITY_PATTERNS = {
    'es': [
        'No hay citas disponibles',
        'no hay horarios disponibles',
        'sin disponibilidad',
        'No hay disponibilidad'
    ],
    'en': [
        'no availability',
        'no available times',
        'No times available',
        'No appointments available'
    ]
}

def get_no_availability_patterns() -> list:
    """Get all no availability patterns for all languages"""
    t('infrastructure.constants.get_no_availability_patterns')
    patterns = []
    for lang_patterns in NO_AVAILABILITY_PATTERNS.values():
        patterns.extend(lang_patterns)
    return patterns

# Date Labels and Translations
DATE_LABELS_ES = {
    'HOY': 'Today',
    'MAÑANA': 'Tomorrow',
    'ESTA SEMANA': 'This Week',
    'LA PRÓXIMA SEMANA': 'Next Week',
    'PRÓXIMA SEMANA': 'Next Week'
}

DATE_LABELS_EN = {
    'TODAY': 'Today',
    'TOMORROW': 'Tomorrow',
    'THIS WEEK': 'This Week',
    'NEXT WEEK': 'Next Week'
}

# Day Names
WEEKDAYS_ES = ['LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES', 'SÁBADO', 'DOMINGO']
WEEKDAYS_EN = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']

# Court Selection Selectors
COURT_BUTTON_SELECTORS = [
    'button:has-text("RESERVAR")',
    'button:has-text("Reservar")',
    'button.consumer-button',
    '.consumer-button:has-text("RESERVAR")'
]

# Navigation Selectors
BACK_NAVIGATION_SELECTORS = [
    'button[aria-label="Volver a Seleccionar cita"]',  # Spanish primary
    'button[aria-label*="Volver"]',
    'button[aria-label*="back"]',
    'button[aria-label*="Back"]',
    'button:has(svg[data-icon="arrow-left"])',
    'button:has-text("←")',
    'a[aria-label*="back"]',
    '[class*="back-arrow"]',
    '[class*="back-button"]',
    'button.back',
    'a.back'
]

# Calendar Navigation Selectors
NEXT_DAY_SELECTORS = [
    'button:has-text(">")',
    'button:has-text("→")',
    'button:has-text("▶")',
    'button:has-text("›")',
    'button:has-text("»")',
    'button[aria-label*="siguiente"]',
    'button[aria-label*="next"]',
    'button[class*="next"]',
    '.next-day',
    '.next-arrow'
]

PREVIOUS_DAY_SELECTORS = [
    'button:has-text("<")',
    'button:has-text("←")',
    'button:has-text("◀")',
    'button:has-text("‹")',
    'button:has-text("«")',
    'button[aria-label*="anterior"]',
    'button[aria-label*="previous"]',
    'button[class*="prev"]',
    '.prev-day',
    '.prev-arrow'
]

# Form Field Selectors
FORM_FIELD_SELECTORS = {
    'first_name': [
        '[name="firstName"]', '[name="fname"]', '[name="first_name"]',
        '[placeholder*="First"]', '[placeholder*="Nombre"]',
        'input[id*="first"]', 'input[aria-label*="Nombre"]',
        'input[type="text"]:first'
    ],
    'last_name': [
        '[name="lastName"]', '[name="lname"]', '[name="last_name"]',
        '[placeholder*="Last"]', '[placeholder*="Apellido"]',
        'input[id*="last"]', 'input[aria-label*="Apellido"]',
        'input[type="text"]:nth(1)'
    ],
    'email': [
        '[name="email"]', '[type="email"]',
        '[placeholder*="Email"]', '[placeholder*="Correo"]',
        'input[id*="email"]', 'input[aria-label*="Email"]',
        'input[aria-label*="Correo"]'
    ],
    'phone': [
        '[name="phone"]', '[name="tel"]', '[type="tel"]',
        '[placeholder*="Phone"]', '[placeholder*="Teléfono"]',
        '[placeholder*="Telefono"]', '[placeholder*="Tel"]',
        'input[id*="phone"]', 'input[id*="tel"]',
        'input[aria-label*="Teléfono"]'
    ]
}

# Booking Configuration
BOOKING_WINDOW_HOURS = 48  # Can book 48 hours in advance
EARLIEST_BOOKING_HOUR = 7  # 7:00 AM
LATEST_BOOKING_HOUR = 21  # 9:00 PM
MAX_RESERVATION_ATTEMPTS = 3
RESERVATION_RETRY_DELAY = 2.0  # seconds

# Court operating hours - separate schedules for weekdays vs weekends
WEEKDAY_COURT_HOURS = [
    "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00",
    "18:15", "19:15", "20:15"
]

WEEKEND_COURT_HOURS = [
    "06:00", "07:00", "08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"
]

# Helper function to get appropriate court hours based on day of week
def get_court_hours(date=None):
    """
    Get court hours based on day of week.
    
    Args:
        date: datetime object or None (uses current date if None)
    
    Returns:
        List of available court hours for that day
    """
    t('infrastructure.constants.get_court_hours')
    from datetime import datetime
    if date is None:
        date = datetime.now()
    
    # weekday() returns 0-6 where 0=Monday, 6=Sunday
    # Weekend is Saturday (5) and Sunday (6)
    if date.weekday() >= 5:  # Saturday or Sunday
        return WEEKEND_COURT_HOURS
    else:
        return WEEKDAY_COURT_HOURS

# Backwards compatibility - defaults to weekday hours
COURT_HOURS = WEEKDAY_COURT_HOURS

# Test Mode Configuration
TEST_MODE_ENABLED = False  # Enable test mode for queue system testing
TEST_MODE_TRIGGER_DELAY_MINUTES = 0.25  # Execute reservations 15 seconds after queuing (0.25 minutes)
TEST_MODE_ALLOW_WITHIN_48H = False  # Allow testing within 48h booking window

# Browser Pool Configuration
DEFAULT_BROWSER_POOL_SIZE = 3
MAX_BROWSER_AGE_MINUTES = 60
MAX_BROWSER_USES = 20
BROWSER_HEALTH_CHECK_INTERVAL = 30  # seconds

# Browser Pool Timeout Configuration (in milliseconds)
class BrowserTimeouts:
    """Centralized timeout configuration for different browser operations"""
    FAST_NAVIGATION = 8000      # Quick redirects and simple pages
    NORMAL_NAVIGATION = 15000   # Standard page loads with redirects 
    SLOW_NAVIGATION = 25000     # Complex pages with heavy content
    HEALTH_CHECK = 5000         # Health monitoring and quick checks
    RETRY_DELAY_BASE = 2.0      # Base delay for exponential backoff (seconds)
    FORM_LOAD = 5000           # Wait for form elements to appear
    FORM_SUBMIT = 30000        # Wait for form submission to complete
    PAGE_LOAD = 15000          # General page reload timeout

class BrowserPoolConfig:
    """Configuration for browser pool resilience"""
    MIN_COURTS_REQUIRED = 1        # Accept 1+ courts (not all-or-nothing)
    MAX_RETRY_ATTEMPTS = 3         # Retry failed courts
    CIRCUIT_BREAKER_THRESHOLD = 5  # Failures before circuit opens
    PARTIAL_SUCCESS_WARNING = True # Log warnings for partial initialization

# Hardcoded VIP Users
HARDCODED_VIP_USERS = [
    125763357,  # Saul Campos (@SCamposJr)
]

# Hardcoded Admin Users
HARDCODED_ADMIN_USERS = [
    125763357,  # Saul Campos (@SCamposJr)
]

# Performance Thresholds
TARGET_AVAILABILITY_CHECK_TIME = 15.0  # Target: < 15 seconds
MAX_SINGLE_COURT_CHECK_TIME = 30.0  # Timeout per court
MAX_NAVIGATION_WAIT_TIME = 5.0  # Max time to wait for navigation