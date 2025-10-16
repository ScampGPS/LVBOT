#!/usr/bin/env python3
"""
Comprehensive Logging Configuration for LVBOT
Provides detailed logging for debugging the tennis reservation bot
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Set, Callable, Any

# Global set to store unique function identifiers for runtime tracking
_tracked_functions: Set[str] = set()

# Read production mode setting
PRODUCTION_MODE = os.getenv('PRODUCTION_MODE', 'true').lower() == 'true'

# Define the log directory to be a fixed 'latest_log'
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'latest_log')

def setup_logging() -> None:
    """
    Set up comprehensive logging configuration with multiple handlers and detailed formatting.
    This version clears previous logs in the 'latest_log' directory before starting a new session.
    """
    # Clear previous logs in the directory
    if os.path.exists(LOG_DIR):
        for filename in os.listdir(LOG_DIR):
            file_path = os.path.join(LOG_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    import shutil
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f'Failed to delete {file_path}. Reason: {e}')
    
    # Ensure the log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)

    # Log file paths
    MAIN_LOG_FILE = os.path.join(LOG_DIR, 'bot.log')
    DEBUG_LOG_FILE = os.path.join(LOG_DIR, 'bot_debug.log')
    ERROR_LOG_FILE = os.path.join(LOG_DIR, 'bot_errors.log')
    RESERVATION_QUEUE_LOG_FILE = os.path.join(LOG_DIR, 'reservation_queue.log')

    # Root logger configuration - adjust based on production mode
    root_logger = logging.getLogger()
    if PRODUCTION_MODE:
        root_logger.setLevel(logging.WARNING)  # Only warnings and errors in production
    else:
        root_logger.setLevel(logging.DEBUG)    # Full debug in development
    
    # Clear existing handlers
    root_logger.handlers = []
    
    # Detailed formatter with file, line, and function information
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d in %(funcName)s()] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console formatter (less detailed for readability)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler - adjust level based on production mode
    console_handler = logging.StreamHandler()
    if PRODUCTION_MODE:
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors in production
    else:
        console_handler.setLevel(logging.INFO)     # Info and above in development
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # Main log file handler - adjust level based on production mode
    main_file_handler = logging.handlers.RotatingFileHandler(
        MAIN_LOG_FILE, 
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    if PRODUCTION_MODE:
        main_file_handler.setLevel(logging.WARNING)  # Only warnings and errors in production
    else:
        main_file_handler.setLevel(logging.INFO)     # Info and above in development
    main_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(main_file_handler)
    
    # Debug log file handler - only enabled in development mode
    if not PRODUCTION_MODE:
        debug_file_handler = logging.handlers.RotatingFileHandler(
            DEBUG_LOG_FILE,
            maxBytes=50*1024*1024,  # 50MB
            backupCount=3,
            encoding='utf-8'
        )
        debug_file_handler.setLevel(logging.DEBUG)
        debug_file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(debug_file_handler)
    
    # Error log file handler - ERROR and above
    error_file_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=5*1024*1024,  # 5MB
        backupCount=5,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(error_file_handler)
    
    # Reservation Queue log file handler - Dedicated for queue operations
    reservation_queue_handler = logging.handlers.RotatingFileHandler(
        RESERVATION_QUEUE_LOG_FILE,
        maxBytes=20*1024*1024,  # 20MB
        backupCount=5,
        encoding='utf-8'
    )
    if PRODUCTION_MODE:
        reservation_queue_handler.setLevel(logging.INFO)  # Only info and above in production
    else:
        reservation_queue_handler.setLevel(logging.DEBUG) # Full debug in development
    reservation_queue_handler.setFormatter(detailed_formatter)
    
    # Create dedicated reservation queue logger
    reservation_queue_logger = logging.getLogger('ReservationQueue')
    reservation_queue_logger.addHandler(reservation_queue_handler)
    
    # Also add handlers for related components
    booking_orchestrator_logger = logging.getLogger('BookingOrchestrator')
    booking_orchestrator_logger.addHandler(reservation_queue_handler)
    
    priority_manager_logger = logging.getLogger('PriorityManager')
    priority_manager_logger.addHandler(reservation_queue_handler)
    
    reservation_scheduler_logger = logging.getLogger('ReservationScheduler') 
    reservation_scheduler_logger.addHandler(reservation_queue_handler)
    
    # Set specific logger levels based on production mode
    if PRODUCTION_MODE:
        # Production mode - only essential logs
        logging.getLogger('TelegramBot').setLevel(logging.INFO)
        logging.getLogger('TennisBot').setLevel(logging.INFO)
        logging.getLogger('IframeHandler').setLevel(logging.WARNING)
        logging.getLogger('SpecializedBrowserPool').setLevel(logging.WARNING)
        logging.getLogger('ReservationScheduler').setLevel(logging.INFO)
        logging.getLogger('AvailabilityCheckAdapter').setLevel(logging.WARNING)
        logging.getLogger('AsyncTennisExecutor').setLevel(logging.INFO)
        logging.getLogger('UserDatabase').setLevel(logging.WARNING)
        logging.getLogger('ReservationQueue').setLevel(logging.INFO)
        logging.getLogger('BookingOrchestrator').setLevel(logging.INFO)
        logging.getLogger('PriorityManager').setLevel(logging.INFO)
        logging.getLogger('LiberationMonitor').setLevel(logging.INFO)
    else:
        # Development mode - full debug logging
        logging.getLogger('TelegramBot').setLevel(logging.DEBUG)
        logging.getLogger('TennisBot').setLevel(logging.DEBUG)
        logging.getLogger('IframeHandler').setLevel(logging.DEBUG)
        logging.getLogger('SpecializedBrowserPool').setLevel(logging.DEBUG)
        logging.getLogger('ReservationScheduler').setLevel(logging.DEBUG)
        logging.getLogger('AvailabilityCheckAdapter').setLevel(logging.DEBUG)
        logging.getLogger('AsyncTennisExecutor').setLevel(logging.DEBUG)
        logging.getLogger('UserDatabase').setLevel(logging.DEBUG)
        logging.getLogger('ReservationQueue').setLevel(logging.DEBUG)
        logging.getLogger('BookingOrchestrator').setLevel(logging.DEBUG)
        logging.getLogger('PriorityManager').setLevel(logging.DEBUG)
        logging.getLogger('LiberationMonitor').setLevel(logging.DEBUG)
    
    # Reduce noise from external libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.INFO)
    
    # Log startup message
    root_logger.info("="*80)
    root_logger.info(f"LVBOT Logging Initialized - {datetime.now()}")
    root_logger.info(f"Production Mode: {'ON' if PRODUCTION_MODE else 'OFF'}")
    root_logger.info(f"Log Level: {'WARNING+' if PRODUCTION_MODE else 'DEBUG+'}")
    root_logger.info(f"Main log: {MAIN_LOG_FILE}")
    if not PRODUCTION_MODE:
        root_logger.info(f"Debug log: {DEBUG_LOG_FILE}")
    root_logger.info(f"Error log: {ERROR_LOG_FILE}")
    root_logger.info(f"Reservation Queue log: {RESERVATION_QUEUE_LOG_FILE}")
    root_logger.info("="*80)
    
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name
    
    Args:
        name: Logger name (usually __name__ from the calling module)
        
    Returns:
        logging.Logger instance
    """
    return logging.getLogger(name)

# Utility function to log function entry/exit
def log_function_call(logger: logging.Logger) -> Callable:
    """
    Decorator to log function entry and exit with arguments and return values
    
    This decorator also tracks unique function identifiers for runtime analysis.
    Each decorated function will be recorded in the global _tracked_functions set.
    
    Args:
        logger: The logger instance to use for logging function calls
        
    Returns:
        Decorator function that wraps the target function
    
    Usage:
        @log_function_call(logger)
        def my_function(arg1, arg2):
            return result
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Construct a unique identifier for the function (module.class.function)
            function_identifier = f"{func.__module__}.{func.__qualname__}"
            _tracked_functions.add(function_identifier)
            
            # Log function entry
            logger.debug(f"Entering {func.__name__} with args={args}, kwargs={kwargs}")
            
            try:
                # Execute function
                result = func(*args, **kwargs)
                
                # Log successful exit
                logger.debug(f"Exiting {func.__name__} with result={result}")
                return result
                
            except Exception as e:
                # Log exception
                logger.error(f"Exception in {func.__name__}: {e}", exc_info=True)
                raise
                
        return wrapper
    return decorator

def save_tracked_functions() -> None:
    """
    Saves the set of unique functions that were executed during the bot's runtime
    to a file, appending to it if it already exists.
    
    This function writes all tracked function identifiers to a 'used_functions.log' file
    in the current timestamped log directory, providing insights into code execution
    patterns for debugging and optimization purposes.
    
    Returns:
        None
    """
    if not _tracked_functions:
        return

    # Define the path for the used functions log file
    # This will be in the current timestamped log directory
    used_functions_log_file = os.path.join(LOG_DIR, 'used_functions.log')

    try:
        with open(used_functions_log_file, 'a', encoding='utf-8') as f:
            for func_id in sorted(list(_tracked_functions)):
                f.write(f"{func_id}\n")
        logging.getLogger('Main').info(f"Saved {len(_tracked_functions)} unique functions to {used_functions_log_file}")
    except Exception as e:
        logging.getLogger('Main').error(f"Failed to save tracked functions: {e}", exc_info=True)


# Initialize logging when module is imported
setup_logging()
